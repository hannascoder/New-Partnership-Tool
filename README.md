# UN Partner Finder

Internal tool for the UN unit **DGC Partnerships**: find media partners worldwide for a UN media product (for example a video on women's rights in DR Congo), by material, language, country, channel and topic.

**Status:** Step 1 of the action plan (configuration: all allowed values). The website is still the placeholder page.
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
docs/            Documentation (briefing, decisions)
.github/         Automatic checks
wrangler.jsonc   Cloudflare settings: publish the folder site/
```

## How publishing works
Every change on the `main` branch is published automatically by Cloudflare (Workers & Pages → project `new-partnership-tool`). No manual step needed.
