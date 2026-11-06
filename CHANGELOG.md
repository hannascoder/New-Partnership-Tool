# Changelog

## 2026-11-06
- **Export list (PDF, Excel, Word).** Tick "Export" on any result card, or "Add all N to export list"
  for every outlet matching the current filters. The list is kept when filters change, so several
  searches can be combined; every filter combination used is remembered and printed in the file.
  A bar at the bottom shows the list and offers PDF / Excel / Word (PDF and Word in landscape or
  portrait) and "Clear list". Files are built in the browser (`site/assets/finder-export.js`,
  libraries in `site/assets/vendor/`). Replaces the earlier CSV export.
- **"Also show worldwide broadcasters"**: reach by default only counts broadcasters with a service
  aimed at the chosen country (e.g. BBC Afrique for DR Congo); broadcasters listed only as
  "worldwide" are added with this box.
- Ownership: state-owned is no longer treated as state-controlled (France 24, TV5 Monde).
- Stable ids: an id is never given to two outlets.

## 2026-11-06 (earlier)
- Step 4c: scope, reach, international broadcasters, press freedom from the Atlas.
- Step 4b: ownership, "Member of" filter.
- Step 4a: organisation type.
- Website preview with the step 3 data.

## 2026-11-03 – 2026-11-05
- Steps 0–3: private repository and login, configuration, data sources, merging.
