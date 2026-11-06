# UN Partner Finder

Internal tool for the UN unit **DGC Partnerships**: find media partners worldwide for a UN media product (for example a video on women's rights in DR Congo), by material, language, country, channel and topic.

**Status:** Step 4 (classification) in progress. Live preview behind login: organisation type, ownership, scope, reach and the export list work; topics follow in step 4d.
The full plan and all decisions are in [`docs/BRIEFING.md`](docs/BRIEFING.md).

## Important
- This repository is **private** and must stay private: it will contain contact data.
- The website is protected by **Cloudflare Access**: only approved email addresses can open it.

## Folder map
```
site/            Everything that is published (and nothing else)
  index.html       The page
  assets/          Design (atlas.css, the same design system as the Atlas) and the UN emblem
  robots.txt       Tells search engines not to index the site
config/          All allowed values: categories, countries, languages, rules (see config/README.md)
overrides.csv    Hand corrections for single outlets (always win)
raw/reference/   Reference lists the config is built from (UN members, M49 regions, ISO 639-3)
pipeline/        Code: setup/ builds the reference lists, validate/ checks the config
docs/            Documentation (briefing, decisions, export specification)
CHANGELOG.md     What changed when
.github/         Automatic checks
wrangler.jsonc   Cloudflare settings: publish the folder site/
```

## Export list
On the results page every card has an **Export** checkbox, and **Add all N to export list** adds every
outlet that matches the current filters. The list is kept when the filters change (combine several
searches) and is stored in the browser. The bar at the bottom downloads it as **PDF**, **Excel** or
**Word** (PDF and Word in landscape or portrait). The file header lists the date, the data date, every
filter combination used and the number of outlets; the list has two sections, *Best UN fit* and
*By country & rank*. Everything runs in the browser (`site/assets/finder-export.js`); the libraries are
stored in `site/assets/vendor/` (versions and licences in its README). Specification: `docs/EXPORT_SPEC.md`.

## How publishing works
Every change on the `main` branch is published automatically by Cloudflare (Workers & Pages → project `new-partnership-tool`). No manual step needed.
