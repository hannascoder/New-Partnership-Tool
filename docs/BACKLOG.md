# Backlog (later phases)

## Phase 2: NGOs as a new organisation type (`org_type: ngo`)
Same filters as media (country, region, topics, language); NGOs only get a new organisation type.

| Source | Assessment (06.11.2026) |
|---|---|
| ECOSOC iCSO database (https://esango.un.org/civilsociety/login.do) | Main source: NGOs with UN consultative status, country and areas of expertise (map to our topics). Has a search form, no simple download: needs a careful fetcher. |
| UN Geneva NGO list (https://www.ungeneva.org/en/engage/civil-society/ngo-list) | Good addition. |
| UN DESA COSP list (disability) (https://social.desa.un.org/issues/disability/cosp/list-of-non-governmental-organization-accredited-to-the-conference-of-states) | Narrow: use as label "Disability & inclusion", not as main source. |
| National NGO registers | Not recommended: 193 formats/languages, often no interface, unfiltered (sports clubs etc.). |
| Suggested: DGC list of NGOs associated with DGC | Ask internally (owner). |
| Suggested: IATI registry of publishing organisations | Open data, good for development NGOs. |
| Suggested: Wikidata (NGO / non-profit classes) | Same technique as for media; gives stable ids. |

## Waiting for the owner
- Internal SDG Media Compact member list (DGC Campaigns).
- Podcast Index API key (free sign-up) – later.

## Other
- Misinformation Monitor.
- Briefing section O (describe your product with AI, similar outlets, pitch tracking, reach data, material details).

### NGO filters (proposal agreed in principle, 06.11.2026)
- Organisation type gets "NGO / civil society"; choosing it shows NGOs only (or media + NGOs).
- Shared filters: country, region, scope, language, topics (5 Ps + beats), UN profile, verified, has contact.
- Topics for NGOs come from: ECOSOC iCSO "areas of expertise / fields of activity", IATI sector codes
  (OECD DAC, e.g. women's rights organisations -> gender_equality), Wikidata "field of work", DESA COSP list
  (-> disability), later the website "About" text. Mapping table per source in config/sources/, like the radio tags.
  NGOs are specialists, so topics will be filled far more often than for general news media.
- UN profile: ECOSOC consultative status -> "Existing UN relationship".
- Material -> channels for NGOs: Video -> social media, website, events/screenings; Audio -> podcast;
  Photo/Graphic -> website, social media, newsletter; Text -> website, newsletter. New channel "Events / screenings".
- Instead of Ownership: NGO filter "Type of work" (advocacy, humanitarian/service delivery, research,
  network/umbrella, grassroots/community, youth organisation, faith-based); media-only filters greyed out.
