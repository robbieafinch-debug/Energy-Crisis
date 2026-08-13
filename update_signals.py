#!/usr/bin/env python3
"""
Daily signal updater for the Energy & Resilience dashboard.

Reads the existing signals.json and news.json, refreshes the signals it can
fetch live, recomputes each signal's status against its threshold, and writes
the files back. Sources it cannot reach are left at their previous values so
the dashboard always stays complete.

Live sources in this version:
  - Brent crude          (Alpha Vantage)
  - Caldara-Iacoviello GPR Index (public CSV download)
  - News                 (RSS feeds)

Everything else keeps its previous value and is clearly still shown.
"""

import json
import os
import sys
import datetime
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import csv
import io

HERE = os.path.dirname(os.path.abspath(__file__))
SIGNALS_PATH = os.path.join(HERE, "signals.json")
NEWS_PATH = os.path.join(HERE, "news.json")

ALPHA_KEY = os.environ.get("ALPHAVANTAGE_KEY", "")

# ------------------------------------------------------------------ helpers

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
    """Append the new value to the 12-week sparkline and 12-month series,
    dropping the oldest point so lengths stay stable."""
    for key in ("spark", "twelve"):
        arr = s.get(key, [])
        if arr:
            arr = arr[1:] + [round(new_value, 2)]
            s[key] = arr

def compute_status(s, value):
    """Status against the threshold, with a 15% 'approaching' band.
    Honours thresholdDirection ('below' means lower values are the breach)."""
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
        return s.get("change", "")

# ------------------------------------------------------------------ fetchers

def fetch_brent():
    """Brent crude via Alpha Vantage. Returns a float price or None."""
    if not ALPHA_KEY:
        log("No Alpha Vantage key set; skipping Brent.")
        return None
    url = f"https://www.alphavantage.co/query?function=BRENT&interval=daily&apikey={ALPHA_KEY}"
    try:
        raw = http_get(url)
        data = json.loads(raw)
        series = data.get("data", [])
        for point in series:  # most recent first
            val = point.get("value")
            if val not in (None, ".", ""):
                return float(val)
        log(f"Brent: no usable value in response. Keys: {list(data.keys())}")
        return None
    except Exception as e:
        log(f"Brent fetch failed: {e}")
        return None

def fetch_gpr():
    """Caldara-Iacoviello GPR Index. Public data file.
    Returns the latest monthly GPR value as a float, or None.
    NOTE: the exact file URL/format can change; if this fails, the signal
    simply keeps its previous value and the dashboard stays intact."""
    url = "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.csv"
    try:
        raw = http_get(url).decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(raw))
        rows = list(reader)
        if not rows:
            return None
        # find a column that looks like the headline GPR index
        cols = reader.fieldnames or []
        gpr_col = None
        for c in cols:
            if c and c.strip().upper() in ("GPR", "GPRD", "GPRH"):
                gpr_col = c
                break
        if gpr_col is None:
            # fall back to a column literally named GPR-ish
            for c in cols:
                if c and "GPR" in c.strip().upper():
                    gpr_col = c
                    break
        if gpr_col is None:
            log(f"GPR: could not find index column in {cols[:8]}")
            return None
        # last non-empty value
        for row in reversed(rows):
            v = row.get(gpr_col, "").strip()
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
    core_hit = any(k in t for k in CORE)
    theme_hit = any(k in t for k in THEME)
    return core_hit and theme_hit

def fetch_news():
    """Pull recent items from RSS feeds, keep those matching CORE + THEME,
    return a list of event dicts. Falls back to empty list on failure
    (caller then keeps previous news)."""
    items = []
    for source, url in RSS_FEEDS:
        try:
            raw = http_get(url, timeout=20)
            root = ET.fromstring(raw)
            for item in root.iter("item"):
                title_el = item.find("title")
                title = (title_el.text or "").strip() if title_el is not None else ""
                if not title or not classify_event(title):
                    continue
                # crude direction guess from keywords
                low = title.lower()
                if any(k in low for k in ["sanction", "attack", "blockade", "shortage", "outage", "cut", "strike"]):
                    direction, lbl = "up", "Severity ↑"
                elif any(k in low for k in ["ceasefire", "reopen", "eased", "resume", "restored"]):
                    direction, lbl = "down", "Severity ↓"
                elif any(k in low for k in ["invest", "commission", "signed", "agreement", "reshoring", "battery"]):
                    direction, lbl = "fast", "Adaptation →"
                else:
                    direction, lbl = "up", "Severity ↑"
                items.append({
                    "date": datetime.datetime.now().strftime("%d %b"),
                    "sector": "All",
                    "text": f"{title} ({source})",
                    "direction": direction,
                    "dirLabel": lbl,
                })
        except Exception as e:
            log(f"News fetch failed for {source}: {e}")
    return items[:6]  # keep the panel tidy

# ------------------------------------------------------------------ main

def main():
    signals = load_json(SIGNALS_PATH)
    news = load_json(NEWS_PATH)

    updated_any = False

    # --- Brent ---
    brent_val = fetch_brent()
    if brent_val is not None:
        s = find_signal(signals, "brent")
        if s:
            old = s.get("value")
            s["change"] = pct_change(old, brent_val)
            s["value"] = f"{brent_val:.2f}"
            s["status"] = compute_status(s, brent_val)
            s["statusLabel"] = s["status"].capitalize()
            push_series(s, brent_val)
            updated_any = True
            log(f"Brent updated to {brent_val:.2f} ({s['status']}).")

    # --- GPR Index ---
    gpr_val = fetch_gpr()
    if gpr_val is not None:
        s = find_signal(signals, "gpr")
        if s:
            old = s.get("value")
            s["change"] = pct_change(old, gpr_val)
            s["value"] = f"{gpr_val:.0f}"
            s["status"] = compute_status(s, gpr_val)
            s["statusLabel"] = s["status"].capitalize()
            push_series(s, gpr_val)
            updated_any = True
            log(f"GPR updated to {gpr_val:.0f} ({s['status']}).")

    # --- News ---
    fresh_news = fetch_news()
    if fresh_news:
        news["events"] = fresh_news
        news.setdefault("meta", {})["lastUpdated"] = datetime.datetime.now().isoformat()
        updated_any = True
        log(f"News updated with {len(fresh_news)} items.")
    else:
        log("News: no fresh items; keeping previous.")

    # --- meta / reading window ---
    now = datetime.datetime.now()
    signals.setdefault("meta", {})
    signals["meta"]["readingWindow"] = now.strftime("%a %d %b %Y")
    signals["meta"]["lastUpdated"] = now.isoformat()
    # data is partially live now
    signals["meta"]["dataMode"] = "partial-live"

    save_json(SIGNALS_PATH, signals)
    save_json(NEWS_PATH, news)

    if updated_any:
        log("Done. Files updated.")
    else:
        log("Done. No live sources returned data; files still refreshed with today's date.")

if __name__ == "__main__":
    main()
