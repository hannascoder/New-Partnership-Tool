# Changelog

## 2026-11-13 (evening): full review of the filter, all findings corrected
Errors fixed
- "Reset filters" really resets (the page address kept the filters and restored them).
- The hint texts no longer say "never hides an outlet" while "Only show matches" is on by default.
- "General news (Specialist)" is gone: General news has no strength.
- "Only new" is hidden until the first automatic update (everything was "new").
- The numbers on the buttons follow the other filters (with Kenya chosen they show Kenya, not the world).
- "Report an error" on every card again (opens a pre-filled report on GitHub; no e-mail address needed).
- Phone: the switch "Media | Organisations & NGOs" is no longer cut off.
- Outlet ids are stable now: at every data run about 19 outlets used to get a new id (two entries with
  the same source key swapped ids), which could empty export lists and break hand corrections.

Better matches
- "Specialist" is stricter: one word in a long description or on the About page is not enough any more
  (2 different words, or the name, or a short definition, or a source). Specialist matches: 56,670 -> 41,524;
  outlets that were "Specialist" in 4 or more topics: 1,074 -> 91; "Life below water" specialists: 28 -> 6.
- UN profile: "Solutions journalism" no longer from a menu entry "Good News" / "Solutions" (147 -> 40),
  "Development journalism" not from a menu entry "Development" (115 -> 34), "Open to partner content" not
  from "syndication / republish" (that means the outlet gives content away; 1,891 -> 1,444). The page says
  these are automatic hints to be checked.
- New box **"Only news media"** (ticked by default): 6,564 pure sports, music, children's and religious
  channels are hidden unless the box is unticked.
- **"Hide state-controlled media" is ticked by default** (1,261 outlets, e.g. RT, CCTV).
- 79 government websites and NGOs are no longer in the media list (reports/not_media.md).
- "Top 10 / Top 50": news media before special-interest outlets (France Football, Charlie Hebdo, Cartoon
  Network), points for a working website, recent articles, social media and contact (so outlets with the
  same Wikipedia value are no longer in random order), and the top 10 are counted among the outlets that
  fit the other filters (hiding state media no longer leaves "top 4").
- "My material": Video = TV or an account on YouTube / TikTok / Instagram / Facebook (was: any website;
  64,388 -> 38,810 outlets). Photo and Graphic: print, website, Instagram / Facebook / X.
- New box "Must match ALL chosen topics".
- Scope: CNN (USA + Canada) and Bild (Germany + Switzerland) are national, not regional (regional: 788 -> 466).
- Names: "ARD" was shown in Arabic letters; names in a script the outlet does not use are replaced by the
  Latin name. The New Humanitarian is in Switzerland, not Kenya.
- Organisations & NGOs: "Specialist" only when the name or 2 clear words in the organisation's own text
  say so (19,370 -> 9,832); organisations that ticked 10 or more fields count as "Reports on it" for them.

Easier to use
- Filter groups fold in and out; the heading shows how many choices are active.
- "Active filters" above the results, each removable with one click.
- Short cards (about half the height) with "Details and reasons": every topic, audience and UN profile with
  the reason in plain text (was only visible when hovering with a mouse).
- Search by name, several countries at once, "Copy link" button.

## 2026-11-13
- **UN Global Compact** on the page, now called "Organisations & NGOs": 2,300 participants that are NGOs,
  foundations, universities, cities, labour organisations or business associations (no companies), merged with
  the ECOSOC NGOs (179 are in both). "Non-communicating" participants stay in with a note.
- New filters: organisation type (show only NGOs, or universities, foundations ...), "Only existing UN partners"
  (ECOSOC status, Global Compact or UN Geneva; explained on the page) with a badge on the card, and "Must have
  all chosen statuses" (e.g. ECOSOC and Global Compact together).

## 2026-11-12
- NGO page filled with the ECOSOC "Activities" tab (11,828 profiles): topics from the NGOs' own fields of
  activity (71 % of NGOs have a topic now, was 43 %), countries of activity (2,299 NGOs), geographic scope
  (7,347 NGOs) and the NGOs' own description (mission statement).
- **NGOs have their own page.** Switch "Media | NGOs" at the top right. Same layout and export as the media
  page, with NGO filters: based in or active in a country, geographic scope, UN status, hide NGOs only
  registered in ECOSOC, type of work, topics, target audience. NGO cards show the NGO's own description.
- NGOs: all ECOSOC NGOs read (12,838 organisations, 12,845 profile pages: country, website, e-mail,
  languages). 16,536 NGOs in the tool now, 5,336 of them with ECOSOC consultative status.

## 2026-11-11
- NGOs: quality check. Schools, hospitals, clubs, museums and monasteries are no longer counted as NGOs;
  service clubs (Rotary, Lions, Zonta, Kiwanis) and all NGOs accredited by the UN stay in; the Federation for
  American Immigration Reform is hidden (right-wing, checked by hand); duplicates such as "Caritas
  Internationalis" / "Caritas Internationalis (International Confederation …)" merged. 6,961 NGOs shown,
  1,200+ with ECOSOC consultative status.
- ECOSOC download asks the UN server more slowly and stops early when the server does not answer.

## 2026-11-10
- AI reading (in the chat, no paid API) for the top 50 outlets of DR Congo, USA, Brazil, Argentina, Canada,
  Spain, Germany, Mexico, France, China, India, Australia, the UK, Russia, Italy, Japan, Colombia, Indonesia, Nigeria, Poland, Ukraine, Chile, Greece, South Africa, Romania, Turkey, Norway, Finland, Sweden, Switzerland, the Netherlands, Peru, Belgium, Bangladesh, Venezuela, South Korea, Hungary, Dominican Republic, Austria, Portugal, Kenya, Uruguay, Ghana, Pakistan, Vietnam, Bolivia, Czechia, Bulgaria, the Philippines, Ecuador, Denmark, Kuwait, Thailand, Serbia, Israel, Iran, Uganda, Albania and Algeria (3,000 outlets): topics, target audience, UN profile, owner.
- Far-right media hidden also by reading the Wikipedia text (29 more, e.g. Junge Freiheit); right-wing
  populist and partisan right-wing media hidden as well (owner: "alles raus was rechts ist"), e.g. Fox News,
  GB News, Aaj Tak, Die Weltwoche; 143 in total, each with its reason in reports/excluded_far_right.md.
- 7 outlets moved to their real country (UPI, Fox News Radio, Univision, Mexicanal, Gamereactor, Azteca
  Guatemala, i24NEWS).
- Entries that are not media (platforms, official gazettes) or no longer published are hidden.

## 2026-11-09 (evening)
- **All topic buttons work.** Hidden keyword lists per topic (`config/topic_keywords.yaml`, 9 UN News
  languages) compared with outlet names, Wikidata descriptions, Wikipedia introductions and the
  outlets' own websites (menu sections, About page, headlines). Three strengths: main focus, own
  section, covers it. Sub-topics (based on the SDG targets, in plain language) open under a chosen
  topic and can be unticked to be more specific.
- Website check (top 100 per country): also public organisation e-mail addresses and social media links.
- New topic "Older persons & ageing"; export column "Target audience".

## 2026-11-09
- **Target audience** (new filter section, soft like topics): women, youth & students, children, older
  persons, rural communities & farmers, local communities, persons with disabilities, indigenous peoples,
  minority-language speakers, ethnic & minority communities, diaspora & migrants, LGBTQ+, religious
  communities, business & professionals, policy makers. Replaces the UN profiles "Youth audience" and
  "Reaches underserved audiences".
- "Existing UN relationship" is now the first value of "Member of".

## 2026-11-06 (evening): step 4d topics + UN profile
- **Topics** (several per outlet) from the sources' own categories, tags and subjects
  (mapping tables in `config/sources/iptv_org.yaml`, `radio_browser.yaml`, `wikidata.yaml`),
  network lists (fact-checkers), organisation type / scope, and clear words in the outlet's name
  (`config/rules.yaml`). No evidence = "General news". Every topic shows its reason as a tooltip.
- **UN profile** from SDG Media Compact, IFCN, organisation type, iptv-org / Radio Browser /
  Wikidata, minority languages (`config/official_languages.csv`, from Unicode CLDR) and 2+ languages.
- **IFCN signatories** are now read (from the list's own data address): 183 fact-checkers;
  new filter value "IFCN" under "Member of".
- Website: topic buttons work (with counts), "Matches: ..." shows topics and UN profiles,
  switch **"Only show topic and UN profile matches"** (default off), export lists the chosen topics.
- Report `reports/topics.md`: how many outlets have each topic / profile and why.
- `check_config.py` also checks the topic / UN profile names in the mapping tables.

## 2026-11-06
- **Export list (PDF, Excel, Word).** Tick "Export" on any result card, or "Add all N to export list"
  for every outlet matching the current filters. The list is kept when filters change, so several
  searches can be combined; every filter combination used is remembered and printed in the file.
  A bar at the bottom shows the list and offers PDF / Excel / Word (PDF and Word in landscape or
  portrait) and "Clear list". Files are built in the browser (`site/assets/finder-export.js`,
  libraries in `site/assets/vendor/`). Replaces the earlier CSV export.
- **"Also show worldwide broadcasters"**: reach by default only counts broadcasters with a service
  aimed at the chosen country (e.g. BBC Afrique for DR Congo); broadcasters listed only as
  "worldwide" are added with this box.
- Ownership: state-owned is no longer treated as state-controlled (France 24, TV5 Monde).
- Stable ids: an id is never given to two outlets.

## 2026-11-06 (earlier)
- Step 4c: scope, reach, international broadcasters, press freedom from the Atlas.
- Step 4b: ownership, "Member of" filter.
- Step 4a: organisation type.
- Website preview with the step 3 data.

## 2026-11-03 – 2026-11-05
- Steps 0–3: private repository and login, configuration, data sources, merging.
