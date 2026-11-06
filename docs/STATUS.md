# Status and next steps (handover, 06.11.2026 evening)

Read this together with `CLAUDE.md`, `docs/BRIEFING.md`, `docs/KATEGORIEN.md`, `docs/BACKLOG.md`.

## Live
https://new-partnership-tool.hannacstevens.workers.dev (Cloudflare Access login). Every merge to `main`
is published automatically (only the PR *preview* builds fail; harmless).

## Done (all merged to main)
- Step 0–3: repo + login, config, fetchers (Wikidata, Radio Browser, iptv-org, Media Cloud, network
  pages, Wikidata owners, Atlas country data), merge with stable ids (`cache/id_map.json`).
- Step 4a org type, 4b ownership, 4c scope/reach/international broadcasters
  (`config/international_broadcasters.yaml`, `config/audience_groups.yaml` = proposal, owner may still review).
- Website preview + export list (PDF/Excel/Word, landscape/portrait), approved by the owner.
- Pipeline run order: `pipeline/README.md`. Raw data is committed by the "Fetch sources" workflow
  (`.github/workflows/fetch.yml`, runs on pushes to `step-*` / `ngo-*` branches and by hand).

## In progress
- **Far-right exclusion: done (merged 06.11.2026).** Rule `exclude_far_right` in `config/rules.yaml`,
  evidence `raw/far_right/` (Wikidata political ideology incl. the owner's, Wikipedia far-right media
  categories). 46 outlets not shown, list with reasons in `reports/excluded_far_right.md`. Brought back by
  hand (`overrides.csv`): Corriere Adriatico, Kesari (historic categories). Hezbollah/Hamas outlets stay
  excluded (owner's ideology "antisemitism"); the owner can still reverse any entry.
- **Branch `ngo-sources`** (NGOs, phase 2, owner wants them in): fetchers for ECOSOC iCSO (slow server,
  paging with cookies, resumes), UN Geneva list (~1,500, parsed), IATI (1,338 NGOs);
  `pipeline/normalize/ngos.py`. ECOSOC: plan to use the lists by field of activity / country instead
  of 6,000 profile pages. NGO filter design: `docs/BACKLOG.md`.

## Next steps (agreed order)
1. **4d topics + UN profile** (mapping tables per source → `config/`; "Only show topic matches" switch,
   default off).
2. **Website check** (owner prefers it as the long-term core): top 50 per country first, no AI:
   reachable?, contact email/page (owner wants email contacts), social links, podcast/newsletter,
   language, owner from imprint/about text.
3. **4e**: all filters finished, "Also show outlets without this information" everywhere.
4. NGOs into the pipeline and the site (same filters + "NGO" type, "Type of work", "Events/screenings").
5. Step 5 reports, 6–7 website v1, 8 Atlas link, 9 automation **every 2 months** (see CLAUDE.md), 10 test.

## Waiting for the owner
- Covering Climate Now: CSV download from the Airtable view (guide given 06.11.2026).
- Internal SDG Media Compact list; Podcast Index key (later); Model UN scope.
