# Status and next steps (handover, 06.11.2026 late evening)

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
- **Step 4d topics + UN profile: built, waiting for the owner's check** (branch `claude/nice-bell-ois6qp`).
  Mapping tables per source in `config/sources/*.yaml` (`topics:` / `un_profile:`), rules in
  `config/rules.yaml` (section 4d), minority languages via `config/official_languages.csv` (Unicode CLDR).
  IFCN list is now read. Website: topic buttons, "Matches", switch "Only show topic and UN profile
  matches" (default off). Numbers and reasons: `reports/topics.md`.
  Honest result: 28 % of outlets have no topic in any source ("General news"); most SDG topics have
  0-150 outlets; "Solutions", "Development journalism", "Open to partner content" have no open source.
  The website check (next) and Covering Climate Now (CSV) are the main ways to fill this.
  Confirmed by the owner (06.11.2026): LGBTQ / African American media -> "Reduced inequalities";
  student newspapers / campus radio -> "Children & youth" + "Youth audience"; diaspora-language media
  (e.g. Vietnamese in the USA) -> "Reaches underserved audiences".
  outlets.json is now 21 MB (Cloudflare limit per file: 25 MiB) - watch this when NGOs are added.
- **Far-right exclusion: done (merged 06.11.2026).** Rule `exclude_far_right` in `config/rules.yaml`,
  evidence `raw/far_right/`. 46 outlets not shown (`reports/excluded_far_right.md`).
- **Branch `ngo-sources`** (NGOs, phase 2, owner wants them in): fetchers for ECOSOC iCSO (slow server,
  paging with cookies, resumes), UN Geneva list (~1,500, parsed), IATI (1,338 NGOs);
  `pipeline/normalize/ngos.py`. ECOSOC: plan to use the lists by field of activity / country instead
  of 6,000 profile pages. NGO filter design: `docs/BACKLOG.md`.

## Topic keywords (owner's decision 09.11.2026) - replaces "website check" as next step
The owner wants EVERY topic button to work: clicking e.g. SDG 5 must find media and NGOs connected
to the topic. Plan agreed, one step per session:
- **T1** keyword lists for all 38 topics in `config/topic_keywords.yaml` (hidden, not shown on the site),
  broad but specific, with exclusion words; only the **9 UN News languages** (Arabic, Chinese, English,
  French, Russian, Spanish, Hindi, Portuguese, Kiswahili). Owner reviews the English list.
  Status: questions to the owner asked 09.11.2026, waiting for answers before writing the lists.
- **T2** Wikipedia intro + Wikidata description for ~13,500 outlets, matched with the lists.
- **T3** website check part 1 (top 50 per country): menu/sections, About page, meta description
  -> keywords; also email contacts, social links, podcast, newsletter.
- **T4** specialist network lists (Covering Climate Now CSV, Earth Journalism Network, women in
  journalism, health, solutions journalism ... only open lists).
- **T5** NGOs: ECOSOC / IATI fields of work -> topics, same lists for NGO websites.
- **T6** website: order by strength, card shows the reason ("Climate section: .../environment").
Three strengths (agreed): **Focus** (topic is the main subject: name, About text), **Desk / section**
(own section in the menu), **Covers** (topic appears repeatedly in the text). One single word somewhere
does not count. Honest limits told to the owner: only coverage can be measured, not interest;
~20-30 % of websites block or need JavaScript; small topics (water, oceans, SDG 17) stay small.

## Next steps (agreed order)
1. ~~4d topics + UN profile~~ (built, owner checks it).
2. **Topic keywords T1-T6** (above); the website check is part T3. **Website check** (owner prefers it as the long-term core): top 50 per country first, no AI:
   reachable?, contact email/page (owner wants email contacts), social links, podcast/newsletter,
   language, owner from imprint/about text.
3. **4e**: all filters finished, "Also show outlets without this information" everywhere.
4. NGOs into the pipeline and the site (same filters + "NGO" type, "Type of work", "Events/screenings").
5. Step 5 reports, 6–7 website v1, 8 Atlas link, 9 automation **every 2 months** (see CLAUDE.md), 10 test.

## Waiting for the owner
- Covering Climate Now: CSV download from the Airtable view (guide given 06.11.2026).
- Internal SDG Media Compact list; Podcast Index key (later); Model UN scope.
