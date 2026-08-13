# Energy & Resilience Signal Dashboard — Prototype

A single-file interactive prototype of the Energy Resilience Lab signal dashboard. Built to show the shape of the production tool.

## What it shows

**Today mode** opens with the reading: which of the four scenarios today's signals are most and least consistent with, shown as a 2×2 with a consistency level per quadrant (no position marker — the room places the position). Below sit the eleven signal tiles across the two axes, then a recent-events feed.

**12 months mode** shows each signal as a time series with its threshold line and breach shading, for the ongoing-monitoring view.

Toggle between them top right.

## Hosting on GitHub Pages

1. Create a new repository.
2. Upload `index.html` (already named for GitHub) and this README.
3. Settings → Pages → Deploy from a branch → main / root.
4. Live in a minute at `https://[username].github.io/[repo-name]/`.

No build step, no dependencies.

## Important framing for the pitch

- All data is **illustrative**, calibrated to August 2026 conditions, not a live feed. The banner says so and should stay.
- The dashboard **does not calculate a position** on the 2×2. It shows which scenarios the signals are consistent with. This is the deliberate design discipline: signals are surfaced, judgement stays human.
- The scenario logic uses the "quiet does not equal calm" rule — quiet signals count for nothing, so a quiet market does not inflate the low-severity scenarios.

## Production path

This is HTML for visual impact. The production build is Power BI, reading the same signals from SharePoint, refreshed daily by the Power Automate pipeline. This prototype shows the destination; Power BI is how it gets built inside the firm.
