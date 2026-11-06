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
- **Branch `step-4-far-right`**: exclusion of very right-wing media (owner's request). Rule in
  `config/rules.yaml` (`exclude_far_right`), code in `pipeline/classify/classify.py`, evidence in
  `raw/far_right/` (988 Wikidata items with a listed ideology, 26 Wikipedia categories / 755 articles).
  Result: **48 outlets** in `reports/excluded_far_right.md`, **sent to the owner for review on 06.11.2026
  evening — waiting for the answer.** Questionable entries flagged to the owner: Corriere Adriatico (ITA,
  regional daily), Kesari (IND, historic Marathi paper), Al-Manar / Al-Nour / Al-Ahed (LBN) and Al-Aqsa TV
  (PSE) (excluded only via the owner's ideology "antisemitism", not right-wing as such). After the answer:
  adjust rules or add `overrides.csv` lines (`<id>,far_right,no,<why>`), rebuild `site/data`
  (pipeline/README.md), open PR, merge.
- **Branch `ngo-sources`** (NGOs, phase 2, owner wants them in): fetchers for ECOSOC iCSO (slow server,
  paging with cookies, resumes), UN Geneva list (~1,500, parsed), IATI (1,338 NGOs);
  `pipeline/normalize/ngos.py`. ECOSOC: plan to use the lists by field of activity / country instead
  of 6,000 profile pages. NGO filter design: `docs/BACKLOG.md`.

## Next steps (agreed order)
1. Finish far-right exclusion (above).
2. **4d topics + UN profile** (mapping tables per source → `config/`; "Only show topic matches" switch,
   default off).
3. **Website check** (owner prefers it as the long-term core): top 50 per country first, no AI:
   reachable?, contact email/page (owner wants email contacts), social links, podcast/newsletter,
   language, owner from imprint/about text.
4. **4e**: all filters finished, "Also show outlets without this information" everywhere.
5. NGOs into the pipeline and the site (same filters + "NGO" type, "Type of work", "Events/screenings").
6. Step 5 reports, 6–7 website v1, 8 Atlas link, 9 automation **every 2 months** (see CLAUDE.md), 10 test.

## Waiting for the owner
- Covering Climate Now: CSV download from the Airtable view (guide given 06.11.2026).
- Internal SDG Media Compact list; Podcast Index key (later); Model UN scope.
