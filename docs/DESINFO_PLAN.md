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
