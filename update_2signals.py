#!/usr/bin/env python3
"""Daily signal updater for the Energy & Resilience dashboard."""

import json
import os
import datetime
import urllib.request
import xml.etree.ElementTree as ET
import csv
import io

HERE = os.path.dirname(os.path.abspath(__file__))
SIGNALS_PATH = os.path.join(HERE, "signals.json")
NEWS_PATH = os.path.join(HERE, "news.json")
ALPHA_KEY = os.environ.get("ALPHAVANTAGE_KEY", "")


def log(msg):
    print(f"[updater] {msg}", flush=True)

def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "energy-resilience-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

def find_signal(signals, sid):
    for axis in ("vertical", "horizontal"):
        for s in signals.get(axis, []):
            if s.get("id") == sid:
                return s
    return None

def push_series(s, new_value):
    for key in ("spark", "twelve"):
        arr = s.get(key, [])
        if arr:
            s[key] = arr[1:] + [round(new_value, 2)]

def compute_status(s, value):
    thr = s.get("thresholdLine")
    if thr is None:
        return s.get("status", "quiet")
    direction = s.get("thresholdDirection", "above")
    if direction == "below":
        if value <= thr:
            return "breached"
        if value <= thr * 1.15:
            return "approaching"
        return "quiet"
    else:
        if value >= thr:
            return "breached"
        if value >= thr * 0.85:
            return "approaching"
        return "quiet"

def pct_change(old, new):
    try:
        old_f = float(str(old).replace(",", "").replace("−", "-"))
        if old_f == 0:
            return "+0.0%"
        p = (new - old_f) / abs(old_f) * 100
        sign = "+" if p >= 0 else "−"
        return f"{sign}{abs(p):.1f}%"
    except Exception:
        return ""


def fetch_brent():
    if not ALPHA_KEY:
        log("No Alpha Vantage key set; skipping Brent.")
        return None
    url = f"https://www.alphavantage.co/query?function=BRENT&interval=daily&apikey={ALPHA_KEY}"
    try:
        data = json.loads(http_get(url))
        for point in data.get("data", []):
            val = point.get("value")
            if val not in (None, ".", ""):
                return float(val)
        log(f"Brent: no usable value. Response keys: {list(data.keys())}")
        return None
    except Exception as e:
        log(f"Brent fetch failed: {e}")
        return None

def fetch_gpr():
    url = "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.csv"
    try:
        raw = http_get(url).decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(raw))
        rows = list(reader)
        cols = reader.fieldnames or []
        gpr_col = None
        for c in cols:
            if c and c.strip().upper() in ("GPR", "GPRD", "GPRH"):
                gpr_col = c
                break
        if gpr_col is None:
            for c in cols:
                if c and "GPR" in c.strip().upper():
                    gpr_col = c
                    break
        if gpr_col is None:
            log(f"GPR: no index column found in {cols[:8]}")
            return None
        for row in reversed(rows):
            v = (row.get(gpr_col) or "").strip()
            if v not in ("", "NA", "."):
                return float(v)
        return None
    except Exception as e:
        log(f"GPR fetch failed: {e}")
        return None


RSS_FEEDS = [
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("OilPrice.com", "https://oilprice.com/rss/main"),
]
CORE = ["energy", "oil", "gas", "lng", "crude", "fuel", "power grid", "electricity",
        "opec", "refinery", "pipeline"]
THEME = ["sovereignty", "energy security", "supply chain", "disruption", "resilience",
         "sanctions", "blackout", "shortage", "price cap", "embargo", "outage"]

def classify_event(text):
    t = text.lower()
    return any(k in t for k in CORE) and any(k in t for k in THEME)

def fetch_news():
    items = []
    for source, url in RSS_FEEDS:
        try:
            root = ET.fromstring(http_get(url, timeout=20))
            for item in root.iter("item"):
                title_el = item.find("title")
                title = (title_el.text or "").strip() if title_el is not None else ""
                if not title or not classify_event(title):
                    continue
                low = title.lower()
                if any(k in low for k in ["sanction", "attack", "blockade", "shortage", "outage", "cut", "strike"]):
                    direction, lbl = "up", "Severity \u2191"
                elif any(k in low for k in ["ceasefire", "reopen", "eased", "resume", "restored"]):
                    direction, lbl = "down", "Severity \u2193"
                elif any(k in low for k in ["invest", "commission", "signed", "agreement", "reshoring", "battery"]):
                    direction, lbl = "fast", "Adaptation \u2192"
                else:
                    direction, lbl = "up", "Severity \u2191"
                items.append({
                    "date": datetime.datetime.now().strftime("%d %b"),
                    "sector": "All",
                    "text": f"{title} ({source})",
                    "direction": direction,
                    "dirLabel": lbl,
                })
        except Exception as e:
            log(f"News fetch failed for {source}: {e}")
    return items[:6]


def main():
    signals = load_json(SIGNALS_PATH)
    news = load_json(NEWS_PATH)
    updated_any = False

    brent = fetch_brent()
    if brent is not None:
        s = find_signal(signals, "brent")
        if s:
            s["change"] = pct_change(s.get("value"), brent)
            s["value"] = f"{brent:.2f}"
            s["status"] = compute_status(s, brent)
            s["statusLabel"] = s["status"].capitalize()
            push_series(s, brent)
            updated_any = True
            log(f"Brent updated to {brent:.2f} ({s['status']}).")

    gpr = fetch_gpr()
    if gpr is not None:
        s = find_signal(signals, "gpr")
        if s:
            s["change"] = pct_change(s.get("value"), gpr)
            s["value"] = f"{gpr:.0f}"
            s["status"] = compute_status(s, gpr)
            s["statusLabel"] = s["status"].capitalize()
            push_series(s, gpr)
            updated_any = True
            log(f"GPR updated to {gpr:.0f} ({s['status']}).")

    fresh = fetch_news()
    if fresh:
        news["events"] = fresh
        news.setdefault("meta", {})["lastUpdated"] = datetime.datetime.now().isoformat()
        updated_any = True
        log(f"News updated with {len(fresh)} items.")
    else:
        log("News: no fresh items; keeping previous.")

    now = datetime.datetime.now()
    signals.setdefault("meta", {})
    signals["meta"]["readingWindow"] = now.strftime("%a %d %b %Y")
    signals["meta"]["lastUpdated"] = now.isoformat()
    signals["meta"]["dataMode"] = "partial-live"

    save_json(SIGNALS_PATH, signals)
    save_json(NEWS_PATH, news)
    log("Done. Files updated." if updated_any else "Done. No live data returned; date refreshed.")


if __name__ == "__main__":
    main()
