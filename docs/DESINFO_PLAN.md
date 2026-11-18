# Disinformation & fake news monitor - plan (owner's answers 17.11.2026)

New, separate page `site/desinfo.html` (own page, same design as the Atlas, new switch next to "Media | NGOs").
Status: PLAN ONLY. Nothing built yet. One step per session, continue only after the owner confirms "done when".

## Decisions (owner, 17.11.2026)
- Purpose: show worldwide trends in disinformation / fake news by topic and country; check if the UN already
  has accurate material (content gap = "data void"); later link to local fact-checkers / community radio /
  trusted outlets of the Partner Finder (stage 2, owner: "yes please, second stage").
- Scope: both "UN-related" and "general trending claims" with a switch "All topics | UN-related only".
- Users: internal only for now. Access stays behind Cloudflare Access (same as the rest).
- Do NOT show the Partner-Finder lists/cards on this page at first. (The owner's "gelbe Seiten" = the yellow
  loading screen; leave it out for now.)
- Daily update (own small workflow, not the 2-monthly one), with error mail. Archive as time series (per topic
  and country, per day); single items older than 12 months deleted.
- Timeline on top with a from/to date; values are summed over the chosen range (cumulated).
- Red marker for strongly rising topics. E-mail alert later.
- Topics: same 38 topics as the Partner Finder (`config/topic_keywords.yaml`) + a few UN topics; cover ALL topics
  from the start. Keyword matching, no AI.
- Country = country of the fact-checker (publication); plus the country talked about, where it can be read.
- Only fact-checks by recognised fact-checkers (IFCN members etc.); no own judgement. Short neutral summary +
  link, no verbatim quotes of harmful claims. Notice "automatic evaluation, please check the original".
- Translation: automatic English translation next to the original (open source: Argos Translate / OPUS-MT);
  original always shown first.
- UN name list in `config/` (UN, agencies, peacekeeping ... in the 9 UN languages) for "UN-related".
- UN material "already available" = UN News, UN Verified, UN agency websites (public). Three levels: available /
  partial / gap. Suggestions for filling gaps are wanted (see open questions).
- Priority: where disinformation is strongest (not only crisis countries).
- Owner will create a free Google API key (Fact Check Tools) -> store as GitHub secret. TO-DO for the owner.

## Sources (all free/open)
Google Fact Check Tools API (key), ClaimReview markup, IFCN list (already in repo), fact-checker RSS feeds
(AFP, Full Fact, Africa Check, Maldita, Aos Fatos, Boom, Vera Files ...), EDMO, GDELT, Wikipedia pageviews,
Reuters Institute Digital News Report (background layer per country), EUvsDisinfo / DFRLab (optional).
Not used: Media Bias/Fact Check, Washington Post Fact Checker (US only).
- **Google Trends:** the owner wants it. Official API is still in alpha (application required, no known price,
  unclear if free). pytrends/scraping is unofficial and unstable. Plan: apply for the alpha; until then use
  Wikipedia pageviews + GDELT as free trend signals; build a Google Trends fetcher only when access is free.
- **Reuters Misinformation Monitor:** launched 17.09.2026 as a weekly newsletter (page could not be opened from
  the dev sandbox; format/licence to be checked). Plan: link it; read it automatically only if an open feed
  or terms allow it.

## Planned steps
- D0 (this session): plan + questions. Done when the owner answered the open questions below.
- D1 fetch fact-checks (Google, ClaimReview, RSS, IFCN), map to topic + country, report.
- D2 pages: world map page + trends page (see layout proposal), timeline, filters (region, country, topic).
- D3 UN check ("do we have something?") + gap list + suggestions to fill gaps.
- D4 daily workflow, error mail, archive, red marker.
- D5 link to the Partner Finder (local fact-checkers, community radio, trusted outlets per country).
- D6 Reuters Institute layer, Google Trends (if free), further sources.

## Second round of owner's answers (17.11.2026)
- Layout: ONE page first, with a switch "Worldwide trends | Global map" (the owner may later split it).
- Timeline: a small bar chart (items per day) where you pick from/to, plus fields "from / to / Apply" and
  quick buttons "Daily view | 1 day | 7 days | 30 days" (owner's screenshot from the Atlas).
- Map colour = number of fact-checks; countries without fact-checkers grey ("no data", not "no disinformation").
  Long-term goal: EVERY country covered (see "Coverage plan").
- Wikipedia/GDELT as substitute signal for uncovered countries: yes, shown separately.
- Red marker: more than 2x the average of the last 4 weeks and at least 5 items.
- E-mail alert: NO (not in v1).
- UN-related: mark items that name UN organisations automatically; owner agrees to a name list.
- Only UN office holders by name; no private persons.
- UN sources: UN News, UN Verified, agency sites, press-release archive, UN photo/video, campaign sites.
- Topics: ALL topics of the Atlas Topic Explorer (183 topics in 10 groups: climate, development, education,
  health, humanitarian, infrastructure, institutions, peace, rights, technology) - source:
  repository hannascoder/UN-Media-Consumption-Map-copy-2, `data/topics.json` (Wikidata ids + titles in 22 languages).
  Replaces the 38 Partner-Finder topics for this page. Region filter: UN M49.
- Archive with per-source counts: yes (report in `reports/`).
- Page name: as fast as possible; working name "Disinformation monitor" (rename any time).
- Google key: owner needs a step-by-step guide (given 17.11.2026).

## Findings 17.11.2026 (Atlas repo is public and already runs a daily trend engine)
- Atlas `data/trends/` (daily): `country_searches.json` = **Google Trends "Trending Now" RSS per country, free, no key,
  ~122 countries**; `wiki_pageviews.json`, `attention_archive.json` (topic attention since 2024), `gdelt_coverage.json`,
  `bluesky_trends.json`, `topic_intelligence.json`, `country_reading.json`, `ooni_censorship.json`.
  => Google Trends is solved without the alpha API: read the Atlas files (public) instead of building our own
  fetchers. Google sets no history (the Atlas keeps its own archive). Attribution "Data source: Google Trends".
- The dev sandbox cannot reach most hosts (Google Trends, GDELT, Wikimedia, Poynter, UN News all blocked);
  every fetch therefore runs in GitHub Actions, as for the rest of the tool.
- Google Fact Check API answers 403 without a key (as expected).

## Coverage plan (every country, long-term)
1. Start: Google Fact Check API + ClaimReview + IFCN list -> shows which countries have fact-checkers.
2. Per country without data: look up fact-checkers in open directories (Duke Reporters' Lab database, EDMO hubs,
   IFCN, Wikidata) and add their RSS feeds to `config/factcheck_sources.yaml` (list of feeds, one line each).
3. Report `reports/desinfo_coverage.md` after each run: countries with 0 items, with the reason, ranked by
   population / UN relevance -> next countries to work on (self-maintaining list).
4. Substitute signals for uncovered countries: Wikipedia pageviews on misinformation-related articles (per language),
   GDELT, OONI censorship (Atlas), clearly labelled.
5. Languages: fact-check feeds in the 22 Atlas languages first.

## Open questions
Answered by the owner on 17.11.2026 (see above). Remaining: see chat.

## Built 17.11.2026 (second half): all of the owner's answers implemented
- Backfill run (workflow input "backfill": Google, last 12 months, 3 pages per query) and rotating languages (9 fixed +
  3 of the other 13 Atlas languages per day).
- Automatic search for fact-checkers: Wikidata (class labels in `config/desinfo.yaml` `discovery`) -> home page ->
  the feed the site announces; robots.txt respected, 403 never worked around, result in `cache/desinfo_feeds.json`;
  weekly (Mondays) or workflow input "discover". Feeds that fail 10 days in a row rest for 30 days.
- "Country the fact-check is about" (`about`): country names in title + claim, English names + local spellings
  (`config/desinfo.yaml` about_aliases / about_acronyms / about_skip_names); second series `series_about.json`; switch on the page.
- Search trends (Atlas, Google Trends per country) shown for a chosen country as a substitute signal, marked as such.
- Content gaps (D3): UN feeds (`config/un_sources.yaml`, own feed discovery as fallback) -> topics with the same
  synonyms -> `site/data/desinfo/un_content.json`; traffic light in `config/desinfo.yaml` `gap`; suggestions per topic
  group in `config/desinfo_gap_suggestions.yaml`; language check (languages of the fact-checks vs UN articles).
- Known limits: demonyms (Bangladeshi, Venezuelan) are not read as countries; UN feed addresses were guessed and are
  checked at every run (reports/desinfo_sources.md); "about" and topics are rule based.

## Built 17.11.2026 (evening): translation and link to the Partner Finder (D5)
- Automatic English translation of titles: `pipeline/desinfo/translate.py` (Argos Translate, open source, models cached
  between runs; memory `cache/desinfo_translations.json`; report `reports/desinfo_translation.md`). Translations also feed
  topic and country detection.
- Local voices per country (owner: fact-checkers, community media, well-known news outlets, AND organisations & NGOs):
  `pipeline/desinfo/partners.py` -> `site/data/desinfo/partners.json` (top 6 per group, `config/desinfo.yaml` `partners`);
  box on the page for a chosen country with links that open the Partner Finder pre-filtered (`#c=ESP&ot=fact_checker`,
  `ngos.html#c=ESP`). Country ranking list "Countries with the most fact-checks" on the trends view.
- Idea left for later: Partner Finder cards could show "much disinformation in this country (topic X)"; topic mapping between
  the Atlas topics (183) and the Partner Finder topics (38) would be needed for topic-specific links.

## Built 18.11.2026: export, topic links, AFP country, iVerify (owner: "a ok, b sehr gut, c ok, iVerify einbauen")
- **Export (c):** buttons PDF / Word / Excel on the page (`site/assets/desinfo-export.js`, same look as the Partner Finder export,
  runs in the browser): topics, countries, content gaps with suggestions and UN links, fact-checks (newest 300, English translation),
  local voices of a chosen country, filters, data date, disclaimer. In the PDF, titles in scripts the font lacks (Arabic, Hindi,
  Chinese ...) show the English translation; Word and Excel keep the original.
- **Topic links (a):** `config/desinfo_partner_topics.yaml` maps 182 of the 183 Atlas topics to a Partner Finder topic (first proposal, owner to review);
  "Open all ... in the Partner Finder" adds `&tp=<topic>`.
- **Country of international services (b):** `international_publishers` in `config/desinfo.yaml` (AFP): when the text names exactly one country it is
  used as the fact-checker's country (countries by fact-checker: 34 -> 67).
- **UNDP iVerify:** each country runs its own instance (open source, digital public good). `config/iverify_sites.yaml` lists the instances
  (so far Malawi and Zambia, from public sources); the weekly discovery looks for the feed the site announces; items from these sites get the badge
  "iVerify (UNDP)" and the instance's country. Open: the UNDP iVerify team knows which instances are live and public; every line added
  there is picked up without code. No RSS or API for iVerify is documented in public sources (checked 18.11.2026; UNDP and DPG registry pages
  were not reachable from the dev sandbox).

## 18.11.2026 (evening): topic mapping down to sub-topics
- `config/desinfo_partner_topics.yaml` now has `map` (Atlas topic -> Partner Finder topic, 182 of 183) and `sub` (130 of them also a sub-topic).
  The link on the page selects only that sub-topic (`&tp=<topic>&off=<topic>:<other sub-topics>`; checked: the Partner Finder takes it).
  The build checks that a sub-topic belongs to its topic and writes `site/data/desinfo/partner_topics.json`.
- Excel for the owner: `python pipeline/desinfo/make_topic_mapping_xlsx.py` -> `docs/desinfo_topic_mapping.xlsx` (yellow columns E/F with drop-downs);
  `python pipeline/desinfo/import_topic_mapping.py [file]` reads the choices back.
- Owner's remark: the five Partner Finder groups (People, Planet, ...) are too coarse, so the Excel no longer shows them; topics and sub-topics are shown instead.

## 18.11.2026 (night): owner's answers on the topic mapping
- Narrow/broad default by size: a sub-topic with fewer than `partners.narrow_min_outlets` (150) media in the Partner Finder worldwide starts on
  "broad" (`site/data/desinfo/partner_topic_sizes.json`, written by `partners.py`); the user can switch.
- Second topic (`also:` in `config/desinfo_partner_topics.yaml`, 13 entries, e.g. Air pollution = climate + health/pollution_health; Deepfake also fact_checking;
  LGBTQ rights and Same-sex marriage also gender_equality/gender_identity): the link selects the first OR the second topic (`&tp=a,b&off=a:...;b:...`).
- "Population growth" -> cities. UN institution topics (WHO, UNICEF ...) stay on the subject topic (owner: no UN-profile filter).
- Excel has columns F-I (topic, sub-topic, second topic, sub-topic of the second topic; "none" removes the second topic); importer updated and tested.

## 18.11.2026 (late): health and climate second topics (owner: "alles ja", also COVID-19 and Pandemic)
- 24 more second topics in `config/desinfo_partner_topics.yaml` (37 in total): vaccines/COVID-19/pandemic also "Access to health care",
  contraception/family planning also SRHR, obesity also nutrition, malnutrition also maternal/child health; extreme weather, floods, wildfire,
  water scarcity also climate adaptation; renewable energy, solar, wind, EV also climate change; plastic, recycling, e-waste, biodiversity,
  deforestation, desertification also environment in general; ocean acidification also climate change.
- Data model: a topic's Partner Finder selection is now a list `[[topic, [sub-topics]], ...]`; two sub-topics of the SAME topic are merged
  (COVID-19 = health / infectious diseases + health systems).
- Data check (18.11.2026): COVID-19, pandemic and vaccine topics = 317 of 6,174 fact-checks in 12 months (5 %), 18 of 1,084 in the last 30 days (1.7 %);
  election is by far the top topic. Caveat: topic detection is by key words and the archive before 17.11.2026 is incomplete.

## 18.11.2026 (late): topic groups as a view
- A whole topic group can be chosen ("All health topics" at the top of each group in the topic list). The series has an extra row per group
  (`q = "g:<group>"`, a fact-check counts ONCE per group, built in `build.py` `make_series`). Trends, map, content gaps (only the group's topics)
  and the export (PDF/Word/Excel) work for the group. The UN box and partner links need one topic and are hidden for a group.
