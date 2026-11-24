# Changelog

## 2026-11-24 (later): owner's feedback on "Reach & size"
- New fourth level "Mini" in "How well-known is it?" (one source and nothing else known, score below 2;
  about 16,000 outlets); "Small" is now the band above it. `config/rules.yaml` `size_tier.mini_score`.
- Scope estimate from Wikipedia now follows the languages: an article in 3 or more of the 7 world-language
  Wikipedias (English, French, Spanish, Arabic, Russian, Chinese, Portuguese) = International; articles only
  in other languages (e.g. three Indian languages) = National. Estimated scope "International" 275 -> 1,064.
  (`config/rules.yaml` `scope.estimate.international_min_world_wikipedias`.)

## 2026-11-24: "Reach & size" filter (owner's colleagues wanted to find outlets that are not yet well-known)
- New block "Reach & size", first in the filter list on both pages. Level 1: "In one country" / "Several
  countries / worldwide" (a button selects all its values); level 2: Local, Province / state (new), National,
  Several countries, International, and an "Unknown" button (replaces the "also show outlets without scope
  information" box). The scope buttons moved here out of "Region / Country".
- Media: new filter "How well-known is it?" (Well-known / Mid-size / Small / lesser-known). An estimate from
  the best-known ranking (Wikipedia versions, sources, working website, recent articles, social media), not an
  audience figure. Thresholds: `config/rules.yaml` `size_tier`. Shown on the card ("Size") and as a new
  Excel/PDF/Word column "Size" next to "Scope" (media only).
- Fewer outlets with unknown scope (36 % -> about 29 %): Radio Browser tags ("community radio", "local" ...),
  Wikidata operating area "worldwide", and clearly marked estimates ("Estimate: ..." on the card and
  "(estimate)" in the export): words in the name (9 UN languages) or a Wikipedia article in 3+ languages
  (= not a local outlet). Rules: `config/rules.yaml` `scope`.
- iptv-org broadcast areas: a province / state is now "Province / state", a city stays "Local".
- NGOs: Scope uses the same filter; for NGOs without an ECOSOC value: IATI organisation type, number of
  countries of activity (5+ = international), a word in the name, ECOSOC general status
  (`config/ngo.yaml` `scope_estimate`). Marked as estimate.



## 2026-11-24
- Page "Organisations & NGOs": box **"Include other ECOSOC organisation types"** (off by default) and new
  organisation types: Association, Indigenous peoples' organisation, Disability organisation (Foundation existed).
  Organisations that ECOSOC lists only as one of these types are shown only with the box ticked; when another
  list (UN Geneva, Global Compact) calls them an NGO they are always shown, with their exact type.
- The data of the 1,727 organisations of these types (country, website, fields of activity) follows when the
  ECOSOC database is back from maintenance (down since 17.11.2026), at the latest with the automatic update.
## 2026-11-17
- Contact search: contact pages on the same site (e.g. help.nytimes.com) count, the usual contact addresses
  (/contact, /contact-us ...) are tried, and the contact page is read for organisation e-mail addresses.
  6,865 new contact pages; outlets with an e-mail address 6,003 -> 10,114. Top 10 per country without any
  contact: 862 -> 669. Part of every automatic website check from now on.
- The e-mail address on a card opens the "Send mail" pop-up (a plain link gave an empty mail).
## 2026-11-16 (evening): "Start from a UN mail or text" - stage 1
- New box above the results on both pages (Media, Organisations & NGOs): paste the text of a UN mail
  (e.g. a UN VIDEO UPDATE), a press release or a story and press "Suggest partners". The tool reads
  country, topics, format and language from the text and switches on the normal filters. Every find is
  shown as a button that can be switched off again; "Why these suggestions?" lists the words it found.
- No AI service and nothing is sent anywhere: the text is compared in the browser with the country names,
  the topic keyword lists and a few rules (`config/dropin.yaml`).
- Media: all outlets of the country that can use the format, those that work on the topic first.
  NGOs: only organisations that work on the topic. The link "Show matching organisations & NGOs for this
  text" carries the text to the other page.
- The language (e.g. "English subtitles") is shown but not switched on by itself.
- Not yet: "is reporting on this right now" (stage 2, needs a test of the open news database GDELT).

## 2026-11-16: first automatic update checked, two corrections
- The first run of "Automatic update" (started by hand on 14.11.) went through in 5 hours and published on
  its own: all sources fetched again, 17,271 websites visited in about 1 hour, 285 new outlets (marked
  "new"), safety brake passed.
- Correction 1: an outlet that only "disappeared" because it was merged into another entry (e.g. "Welt" ->
  "Die Welt") is no longer kept as "not found in the sources" - that made duplicates.
- Correction 2: a website counts as "dead again" only when the checks are at least 30 days apart. The run
  came 5 days after the first website check and would have counted two failures within one week.
## 2026-11-16
- **Send mail**: every card with an e-mail address has a button "Send mail" (otherwise "Open contact page").
  It opens a preview with a ready-made mail (one for media, one for organisations); everything to fill in is
  highlighted yellow. Buttons open the Outlook app, Outlook on the web or Gmail; the text with the yellow marks
  is copied at the same time. The export now lists both the e-mail and the contact page.

## 2026-11-14 (night)
- "More": every box has a short explanation under it (what it does, and what you lose when you tick it).
- Fixed: a filter chosen in a folded group was missing in the "Active filters" line.

## 2026-11-14 (evening): the automatic update is built
- New workflow **"Automatic update"** (`.github/workflows/update.yml`): every 2 months (3rd of January, March,
  May, July, September, November) it downloads all sources again, visits the websites again, rebuilds the
  data and publishes it - without anybody doing anything, free of charge (public repository, open data only).
- **Safety brake:** nothing is published when more than 10 % of the outlets or organisations (or 25 % of one
  large source) disappeared at once.
- **If it fails:** an issue "Automatic update failed" is opened (GitHub e-mails the owner); the website stays as it was.
- An outlet whose website no longer exists at 3 checks in a row is hidden and comes back when the website
  answers. Websites that only block robots (many large outlets) do not count.
- An outlet that is in no source any more stays for one update with a note and is removed at the second.
- In the months in between, a small "still alive" note is saved, because GitHub switches schedules off after
  60 days without changes.
- `bash pipeline/run.sh` runs the whole pipeline in one go.
- Honest limits: ECOSOC and the UN Global Compact often do not answer GitHub's computers (their last
  download is kept); the AI reading and hand corrections are not renewed automatically.

## 2026-11-14 (later): fewer, clearer filters and a measured quality check
- **Quality is measured now.** 200 outlets drawn at random were checked by hand once
  (config/quality_sample.csv); `reports/quality.md` is rewritten at every data run. Wrong topic assignments
  in that list: **17 % -> 5 %** (shown by default: 8 % -> 4 %). The price: about 1 in 10 right assignments
  of the check is no longer made.
- "Reports on it" (the weak matches; 36 % of them were wrong) only count when the new box "Also count weak
  matches" is ticked. They now need 2 different words (the same word in two headlines was enough before).
- Menu entries that are legal notices or widgets ("Non-Discrimination", "Modern Slavery Statement",
  "Older polls") and entries made of the outlet's own name ("planet" on "planet radio") are no sections.
- Websites that many outlets share (Pluto TV, zeno.fm, Facebook ...) no longer give topics.
- **Websites taken over by others** (betting, adult content: 400+ found by their title) get a warning, are
  not linked any more (card and export) and their texts are not used.
- Historic papers whose only website is a newspaper archive, academic journals and second entries of
  excluded outlets are no longer shown.
- **Duplicate buttons removed:** topic "Community & local" (= Scope "Local"), UN profile "Public service
  mandate" / "Fact-checking (IFCN)" / "Multilingual", box "Has social media", and on the media page the
  target audiences that were the same list as a topic. The values still show on the cards.
- **"Business & economy" merged into SDG 8** ("Decent work, business & economy", with its own sub-topic).
- "My material" and "Channel" are one group, "Format & channel". Media page: 13 -> 10 filter groups.
- Outlets whose website now belongs to someone else are hidden by default (new box under "More").
- Scheduled automation: see docs/STATUS.md (built next).

## 2026-11-14
- Organisations & NGOs: **"Existing UN partner" is narrower** (owner's decision): ECOSOC consultative status or
  accreditation at the UN in Geneva. Taking part in the UN Global Compact alone no longer counts
  (7,780 -> 5,633 organisations, 42 % -> 30 %). Global Compact participants keep their own button and note.

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
