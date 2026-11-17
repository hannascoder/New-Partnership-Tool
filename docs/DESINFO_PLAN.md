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

## Open questions
See the chat of 17.11.2026 (layout, Google Trends, UN article meaning, gap suggestions, E-mail alert, etc.).
