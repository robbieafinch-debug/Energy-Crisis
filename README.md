# Energy & Resilience Signal Dashboard — Prototype

A single-file HTML dashboard prototype for the Energy Resilience Lab. Built to test the design of the lab dashboard before any production build.

## What this is

An interactive prototype showing how the lab dashboard would work in two modes:

1. **Today** — a “world today” backdrop for use at the start of Act 2 (Opportunity sensing). Eleven signals as tiles across the two axes of the 2x2, plus a recent-events feed for event-based signals, plus the 2x2 scenario framework shown as context (no position marker).
1. **12 months** — a longer time-series view for use in Act 3 (Phased action plan), demonstrating what ongoing signal monitoring would look like over a rolling 12-month window. Threshold lines and breach areas are visible.

Toggle between modes using the buttons in the top right.

## What this is NOT

- Not connected to live data. All numbers are illustrative, calibrated against current (June 2026) market conditions but not pulled from any source.
- Not the production dashboard. This is a design prototype for feedback.
- Not a position calculator. The 2x2 deliberately does not show a quadrant marker. Humans place the read; the dashboard surfaces the signals.

## How to host on GitHub Pages

1. Create a new GitHub repository (public or private with a GitHub Pro account).
1. Upload `dashboard.html` and this README.
1. Rename `dashboard.html` to `index.html` so GitHub serves it as the root page.
1. In repo settings, enable Pages: Settings → Pages → Source: Deploy from branch → main / root.
1. Wait a minute. Your site will be live at `https://[username].github.io/[repo-name]/`.

No build step, no dependencies, no framework. The whole thing is one HTML file with inline CSS and JavaScript.

## What the team should react to

- **The signal selection.** Eleven signals across two axes. Are these the right ones? Anything missing that would be noticed by an executive? Anything that doesn’t earn its tile?
- **The tile design.** Sector tag, status (breached / approaching / quiet), current value, sparkline, threshold reference. Does this scan in three seconds for an executive?
- **The status colour language.** Amber for breached, soft yellow for approaching, neutral for quiet, green for positive adaptation. Right register?
- **The recent-events feed.** Event-based signals (sanctions, M&A, force majeure) live here. Does the structure work?
- **The 2x2 context.** Scenarios named, no position marker. Is the discipline of “dashboard surfaces signals; humans place position” clearly held?
- **The 12-month view.** Threshold lines and breach shading. Useful for the Act 3 demonstration? Or too detailed?

## What’s deliberately missing or open

- **Consumer goods has no tile.** No clean single-index signal exists for the sector. Decision needed: add a weak proxy (e.g. Westpac Consumer Sentiment) or leave the gap honest.
- **No production data feeds.** Going to production requires deciding which sources the firm can actually access (many of the named indices are paywalled), and how the data pipeline works.
- **Thresholds are illustrative.** The numbers in this prototype follow the v3 catalogue strawman. Real thresholds need the team working session.
- **No interactivity beyond mode toggle.** Hover states, drill-downs, filtering — all deferred to production design.

## File structure

```
/
├── index.html    (the dashboard — rename from dashboard.html)
└── README.md     (this file)
```

## Browser compatibility

Tested in current Chromium. Should work in any modern browser (Chrome, Edge, Safari, Firefox). Uses CSS Grid, inline SVG, and ES6 JavaScript — all well-supported since 2018.

## Version

v0.1 — initial prototype for design review.
