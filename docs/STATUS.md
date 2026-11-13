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
  Owner's answers 09.11.2026:
  - Topics may always overlap. Women's sport -> Sports AND SDG 5. Gender identity -> SDG 5 too.
  - **The 169 SDG targets are the long-term reference** (owner sent the UN overview; official list:
    UN Statistics SDG API, unstats.un.org/SDGAPI, fetch via the workflow - blocked in the dev sandbox).
    Proposal: every SDG topic gets its targets as sub-topics (e.g. 5.2 violence against women),
    each with its own keyword list; owner asked about a fold-out sub-topic list and a typo-tolerant search.
  - New topic **Older persons / ageing** (to add in T1).
  - **All world languages matter** ("nothing may fall behind"); no colleague can proofread translations.
    Proposal: 9 hand-made languages + automatic labels in all languages from Wikidata (concept items).
  - Idea from the owner: a **Target audience** section (women, youth, farmers ...), see questions.
  - Done: "Existing UN relationship" is now the first value of "Member of" (not a UN profile button).
  Owner's answers 09.11.2026 (second round):
  - Sub-topics: NO bare numbers and no vague short names. Every sub-topic must say specifically what
    it is about, in plain language (away from the official wording, but complete). Keep the targets
    as the reference behind it. -> T1a: label proposal per target, owner reviews.
  - Sub-topics also for Human rights, Conflict & security, Migration, Humanitarian aid, Disasters,
    health-related beats; not for Sports, Religion, Culture.
  - Search bar: NOT now ("we develop that later"); precise filters instead. Kept in docs/BACKLOG.md.
  - LGBTQ+ (incl. sexual orientation) -> SDG 5, SDG 10, Human rights. Earlier proposals 1-36 accepted;
    no separate "Environment" button; "Member of" stays where it is.
  - **Target audience: built (first version)**, soft filter, section under Topics; replaces the UN
    profiles "Youth audience" and "Reaches underserved audiences". Owner wants it expanded long-term.
    Sources: iptv-org / Radio Browser / Wikidata (audience: tables), community media, minority languages,
    names (config/rules.yaml audience:). Later: Wikidata "intended public" (P2360), About pages (T3).
    Not yet in the export file (owner to decide: new column "Target audience"?).
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

## 09.11.2026 (evening): all topic buttons active (owner: "goal: all buttons active today")
- `config/topic_keywords.yaml`: 39 topics, 63 sub-topics in plain language (the SDG targets are only the
  reference, owner's decision: merged, no numbers), ~4,700 words in the 9 UN News languages, exclusions.
  Matcher `pipeline/classify/topic_text.py`: strengths main focus / own section / covers it.
- Texts: `raw/texts/` (Wikidata descriptions + Wikipedia intros, 28,409 items, 16,537 intros) and
  `raw/website_check/` (top 100 per country, ~11,500 sites; menu, About page, headlines, e-mails,
  social links, feeds). Workflow "Fetch texts" (`.github/workflows/texts.yml`).
- Website: button "SDG 5 Gender equality"; choosing it opens its sub-topics, all included until
  unticked; best match counts strength (focus 3, section 2, covers 1). Export: column "Target audience".
- Checking: `reports/topics.md` (numbers) and `reports/topics_sample.md` (random examples per topic).
- Older persons & ageing added as a topic. Search bar: later (BACKLOG).
- Result (website check of 11,457 sites, 8,359 answered): every topic button has matches; outlets
  without any topic down from 28 % to 22 %. Smallest: Life below water ~90, SDG 6 / SDG 12 ~120.
  Strength rule: "main focus" only from name, description, first sentence of Wikipedia / About page,
  or a source/network; menu entries of max. 4 words = "own section"; headlines need 2+ hits.
- Checkboxes "Hide outlets whose website did not answer" and "Only new" now work (all buttons active).
- Website data split into files of 25,000 outlets (site/data/outlets-N.json, listed in config.json), so the 25 MiB limit per file is no longer a problem.
- Known limits: mojibake names from Media Cloud (e.g. "â€“"); website check only top 100 per
  country so far (next runs: raise WEBSITE_MAX_RANK); audience groups do not use the texts yet.

## 09.11.2026 (late): owner's answers + built
- Ranking: equal match -> outlets based in the chosen country first (owner: yes).
- "Report an error" link on every card -> e-mail to the owner's own address (config: feedback_email).
- Built (owner: "go", order 1 -> 7 -> 4 -> 3 -> 2): "Open to partner content" from website hints
  (rules.yaml open_to_partner_content), contact page as fallback, shareable link (filters in the
  page address), error link, "Only active" checkbox (latest article from RSS/page dates).
  Website check v2 (contact page, partner-content links, latest article) runs for all ~59,000 sites.
- Owner chose option A for the strengths: Specialist / Has a section on it / Reports on it (+ note).
- 6 done: keyword names in 403 languages from Wikidata (raw/keyword_labels/, workflow keywords.yml);
  at most "Reports on it", needs 2 different words or a menu section; everyday words dropped by frequency.
- 8 done as far as open data allows: OCCRP network read (61 outlets); no open member lists for
  Solutions Journalism Network / GFMD / Earth Journalism Network (JavaScript pages or no list), so
  "Solutions" and "Development journalism" come from how outlets describe themselves (rules.yaml).
- 4e done: social media platform fold-out, "Also show outlets without channel information",
  no "step 4" notices left on the site; every filter button has data except WhatsApp.

## Step 5 (reports): built 09.11.2026, owner's decision pending
- `pipeline/validate/reports.py` -> reports/coverage.md (+ coverage_by_country.csv), sample.md,
  contradictions.md, changes.md. Owner decides which filters stay in v1 and whether AI (5b) is needed.
  Owner 09.11.2026: keep all filters (ownership: explained again, decision open). AI (5b): allowed NOW
  ("until February it may cost money, long-term it must be free") -> build with AI now, results stored
  in the repo so nothing costs after February; new outlets later get keyword matching only.
  Owner's answers: ownership buttons removed (only "Hide state-controlled" + owner names on cards);
  AI with Claude Opus 5.5, for ALL outlets, classifying topics/sub-topics, audiences, open to partner
  content, owner from imprint, each with a short reason. Open: owner asked whether it can run "over this
  account" (the Claude chat subscription) -> explained it needs an API account (console.anthropic.com),
  cost estimate ~300-500 $ for all with Opus 5.5 (batch); test with 100 outlets first.
- Owner thought buttons did not work: soft filters did not change the counter -> counter + divider added;
  owner: "Only show matches" ON by default.
- Owner (09.11.2026, later): no paid API for now ("erstmal nichts zahlen"; maybe another plan later).
  Instead Claude classifies the top 50 per country IN THE CHAT, country by country (pipeline/ai/README.md,
  cache/ai_classification.json). Done: COD (DR Congo, 50). Next: continue country by country (~9,750
  outlets in total; several sessions). Finds websites taken over by others (casino, travel guides).
- Full website check v2 in (59,436 sites): public contact 37 %, active 24 %, open to partner content 1,713,
  outlets without topic 13 %.
- Organisation types renamed (owner, 09.11.2026): "Newspaper, TV, radio or news site", "News agency
  (supplies other media)", "Public broadcaster (independent)", "Community radio & local media", "Fact-checker".
- AI reading order (owner): countries with the most outlets first. Done: COD, USA, BRA, ARG, CAN, ESP, DEU, MEX, FRA, CHN, IND, AUS, GBR, RUS, ITA, JPN, COL, IDN, NGA, POL, UKR, CHL, GRC, ZAF, ROU, TUR, NOR, FIN, SWE, CHE, NLD, PER, BEL, BGD, VEN, KOR, HUN, DOM, AUT, PRT, KEN, URY, GHA, PAK, VNM, BOL, CZE, BGR, PHL, ECU, DNK, KWT, THA, SRB, ISR, IRN, UGA, ALB, DZA (3,000 outlets).
  Next: TUR ... (order of outlet count).
- Right-wing media (owner, 10.11.2026: "ausblenden und rechte Medien wie Junge Freiheit auch"): the AI reading
  of the Wikipedia text marks far-right outlets ("far_right", 29 hidden, e.g. Junge Freiheit, OAN, Newsmax,
  Valeurs actuelles) and right-wing populist / party-aligned ones ("right_populist", 23, e.g. GB News, Aaj Tak,
  Die Weltwoche). Owner, 10.11.2026: "alles raus was rechts ist, auch die größeren" -> hide_right_wing_populist: true,
  plus 45 more found in the Wikipedia texts or well known (Fox News, Estadão, Veja, Jovem Pan, Epoch Times, Sky News
  Australia, Magyar Nemzet, Origo, Okdiario ...; reasons marked "general knowledge" where the text does not say it).
  Mainstream conservative media (Le Figaro, FAZ, Telegraph, Daily Mail, Bild, NY Post ...) stay for now - asked owner.
  List: reports/excluded_far_right.md. Country corrections (owner, 10.11.2026): UPI, Fox News Radio, Univision,
  Mexicanal -> USA; Gamereactor -> DNK; Azteca Guatemala -> GTM; i24NEWS -> ISR (overrides.csv).
- Platforms and non-media (Reddit, Google News, official gazettes ...) stay hidden (owner, 10.11.2026).
  The AI reading also hides entries that are not media or no longer published (reports/hidden_ai.md)
  and lists outlets that are probably in another country (reports/contradictions.md).
  Country corrections confirmed by the owner go into overrides.csv (field "country"): Miramar MOZ,
  Runner's World USA, Space ARG. Owner asked WHY non-media are hidden (answer: KATEGORIEN 0) - decision open.
- PR #15 merged 20:34 (everything up to the keyword labels). Not yet on main: menu entries in other
  languages = "Has a section on it", step 5 reports, data of the full website check (still running).

## NGOs (phase 2) - in progress since 10.11.2026
Owner's decisions 10.11.2026: box "Include NGOs in this search" under Organisation type (off by default);
NGO filters fold out (UN status incl. "Associated with UN DGC", "Only NGOs with ECOSOC status", type of work);
same filters as media (country, language, topics/SDGs, audience, contact, Top 10/50); classic NGOs only;
ALL ECOSOC NGOs also without status (note on the card); far-right NGOs and GONGOs not shown; mixed with
media on the site, separate section in the export; updated every 2 months (step 9); no national registers
(country filter works with the NGOs' own country). Config: config/ngo.yaml, config/sources/ecosoc_fields.yaml.
- Built: pipeline/ngo/build.py -> work/ngos.json -> site/data/ngos-N.json (loaded only when the box is ticked),
  finder.js (box, fold-out filters, NGO cards, export section "NGOs"). Reports: reports/ngos.md, ngos_excluded.md.
- Sources: UN Geneva (1,471) and IATI (1,339) in; ECOSOC iCSO (all lists + profiles, slow server, resumes;
  workflow "Fetch NGOs", re-run by hand until complete) and Wikidata NGOs (with a Wikipedia page) running.
  DESA COSP list refuses automatic downloads (HTTP 403): not worked around; owner may save it by hand.
- ECOSOC server mostly times out (10.11.2026: 1,607 orgs, 78 profiles in 5 h; 11.11.2026 run 4: server silent
  after 2 minutes for 5 hours). Fetcher now asks slowly (3 s between requests), stops a run after 20 minutes of
  silence, 2 h budget (repo is PRIVATE: GitHub free plan = 2,000 Actions minutes/month, owner to check usage).
  State 11.11.2026: 4,257 ECOSOC organisations listed, 191 profiles (~4,000 still to fetch). ECOSOC entries
  without a profile have no country and are not shown until their profile is read (or matched by unique name).
- Quality check 11.11.2026 (samples): schools, hospitals, clubs, museums, monasteries left out by Wikidata class
  words (config/ngo.yaml wikidata_not_ngo_class_words; service clubs like Rotary/Lions/Zonta kept); NGOs with UN
  accreditation (ECOSOC status, UN Geneva) are never left out as "not a classic NGO" (bar associations,
  Rotary ...); hand-checked exclusions (exclude.manual, e.g. FAIR); duplicates merged when names differ only by
  a bracket at the end ("Caritas Internationalis (…)"). Result: 6,961 NGOs shown.
- 11.11.2026: GitHub Actions minutes for the month are USED UP (private repo, 2,000 min). Workflows do not
  start until the monthly reset. Fetching continues from the cloud session (environment "New-Partnership-Tool"
  allows esango.un.org and unglobalcompact.org). UN Global Compact: owner wants it as an extra box like the
  NGOs; questions to the owner still open (ask again later), list readable page by page (robots.txt forbids
  only the search pages): ~25,700 participants, 12 per page.
- Owner 11.11.2026: ECOSOC type "Non-governmental organization" only for now (other types later, reminder);
  ECOSOC organisations without a readable profile (no country) are left out completely; raw data keeps all
  e-mail addresses (repository is public since 11.11.2026, owner's decision). ECOSOC is now fetched from the
  cloud session (server answers there; from GitHub it was silent for hours).
- 12.11.2026: ECOSOC COMPLETE (local run in the cloud session; GitHub runners get no answers after ~5 min):
  12,838 organisations of type NGO, 12,845 profiles read (some not public: HTTP 403, skipped). 16,536 NGOs shown
  (5,336 with ECOSOC consultative status, 5,858 only registered). The 60 lists by field of activity answer HTTP 500
  (skipped with ECOSOC_SKIP_KINDS=field); the fields are on the profile's "Activities" tab, not read yet.
- 12.11.2026: own NGO page (site/ngos.html, same script finder.js with <body data-mode="ngo">), switch Media | NGOs,
  NGO export layout (finder.js NGO_LAYOUT). ECOSOC "Activities" tab COMPLETE (12.11.2026, 11,828 profiles) - fetched in the cloud session
  (ECOSOC_ACTIVITIES=1; fields of activity -> topics, countries of activity, geographic scope, mission statement);
  rebuild NGOs when it is complete.
- 13.11.2026: UN Global Compact merged (pipeline/fetch/global_compact.py, list pages + profiles; search pages are
  forbidden by robots.txt, so initiatives cannot be read; sector is empty for almost all non-business participants).
  Page renamed "Organisations & NGOs"; filters org type, sector (hidden while < 50 entries), UN partner, all statuses.
- Known gaps: some state-close Russian organisations have no GONGO class in Wikidata; NGOs from Wikidata
  without an English label show their local name.
- Next: keep running 'Fetch NGOs' (gently) until ECOSOC is complete; AI reading of top NGOs per country later.

## 13.11.2026 (evening): full review of the filter ("prüfe den Filter komplett ... berichtige alles")
The owner asked for a complete critique and then for all findings to be corrected in one session
(exception to "one step per session"). Details in CHANGELOG.md (2026-11-13 evening). Summary:
- Owner's decisions 13.11.2026: box "Only news media" (default ON; pure sports / music / children's /
  religious channels hidden, rules.yaml `not_news`); "Hide state-controlled media" default ON; name search
  NOW (only names; the big search stays in the backlog); government websites and NGOs out of the media list
  (rules.yaml `not_media`, reports/not_media.md).
- Rules changed: topic strength (pipeline/classify/topic_text.py, rules.yaml `max_text_specialist`),
  UN profile words, scope (`regional_min_other_countries`), prominence / rank (rules.yaml `prominence`),
  name scripts (`name_scripts`), NGO strength (config/ngo.yaml `many_fields`), material (categories.yaml
  `platforms`). Stable ids fixed in pipeline/merge/merge.py (duplicate source keys get "#2").
- Website: site/assets/finder.js largely rewritten (one test per filter group -> live numbers on the buttons;
  foldable groups; active-filter bar; short cards with details; name search; several countries; copy link;
  "Top N" counted among the outlets that fit the other filters).
- The whole pipeline runs in the cloud session in about 10 minutes (classify.py ~8 min); no GitHub Actions needed.
- Owner 14.11.2026: "Existing UN partner" = ECOSOC status or UN Geneva only, WITHOUT the UN Global Compact
  (config/ngo.yaml un_partner; 7,780 -> 5,633 organisations).
- NOT changed (later): ~8,400 outlets are named like their web address (Media Cloud); ~11,600 outlets
  share a website with another entry (many are real network stations, some duplicates); scope unknown for
  37 % of outlets; e-mail only for 9 %; the UN status boxes on the NGO page overlap.
- Next: owner checks the live site; then continue with the agreed order (AI reading of further countries,
  step 5 decisions, step 8 Atlas link, step 9 automation).

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
