# UN Partner Finder

Internal tool for the UN unit **DGC Partnerships**: find media partners worldwide for a UN media product (for example a video on women's rights in DR Congo), by material, language, country, channel and topic.

**Status:** Step 0 of the action plan (placeholder page "coming soon").
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
docs/            Documentation (briefing, decisions)
wrangler.jsonc   Cloudflare settings: publish the folder site/
```

## How publishing works
Every change on the `main` branch is published automatically by Cloudflare (Workers & Pages → project `new-partnership-tool`). No manual step needed.
