# Quality check: topic assignments of 200 random outlets

200 outlets drawn at random on 14.11.2026; every topic they had was checked by hand once
(config/quality_sample.csv). This report is rewritten at every data run.

## When the list was checked (14.11.2026, before the changes)

| Strength | Checked | Wrong | Share wrong |
|---|---|---|---|
| Specialist | 40 | 4 | 10 % |
| Has a section on it | 322 | 24 | 7 % |
| Reports on it | 185 | 67 | 36 % |
| **All** | 547 | 95 | **17 %** |
| **Shown by default** (without "Reports on it") | 362 | 28 | **8 %** |

## Now

| Strength | Checked | Wrong | Share wrong |
|---|---|---|---|
| Specialist | 39 | 4 | 10 % |
| Has a section on it | 303 | 9 | 3 % |
| Reports on it | 71 | 7 | 10 % |
| **All** | 413 | 20 | **5 %** |
| **Shown by default** (without "Reports on it") | 342 | 13 | **4 %** |

- Right assignments from the check that are no longer made: 48
- Assignments made now that were not there at the check (not checked yet): 0
- Of the 12 entries that are not media outlets (or whose website was taken over): 3 are now hidden or carry a warning, 9 are still shown without a warning.

## Wrong assignments still made

| Id | Name | Topic | Strength | Reason |
|---|---|---|---|---|
| pf-041843 | Harvest USA | agriculture | Specialist | name mentions "harvest" |
| pf-011234 | WYMT-TV | humanitarian | Has a section on it | website section "Flood Relief" |
| pf-014037 | Le 1 | science | Reports on it | website About page: "chercheurs", "scientifiques" |
| pf-020734 | Fort Worth Business Press | religion | Reports on it | website headlines: "catholic", "christian" |
| pf-010332 | Vallejo Times Herald | humanitarian | Reports on it | website headlines: "relief", "shelter" |
| pf-056268 | Lawrence County Record | elections | Reports on it | website headlines: "election", "vote" |
| pf-037304 | Al Iraqia Sport | work_economy | Has a section on it | website section "الأعمال الأصلية" |
| pf-069092 | tlz | science | Has a section on it | website section "Science City Jena" |
| pf-017571 | Известия высших учебных заведений. Математика | health | Has a section on it | website section "Здравоохранение" |
| pf-017571 | Известия высших учебных заведений. Математика | education | Has a section on it | website section "Образование" |
| pf-017571 | Известия высших учебных заведений. Математика | industry_innovation | Has a section on it | website section "Социальная инфраструктура" |
| pf-014742 | Imagine Showbiz | children_youth | Reports on it | Wikipedia: "youth" |
| pf-046983 | Sadhna News Madhya Pradesh/Chhattisgarh | work_economy | Has a section on it | website section "Investors" |
| pf-052464 | lutherchips.com | humanitarian | Reports on it | website headlines: "doctors without borders", "medecins sans frontieres", "msf" |
| pf-061529 | El Heraldo - Argentina - Cordoba | migration | Reports on it | website About page: "inmigrantes" |
| pf-030248 | Dadi Fm | industry_innovation | Specialist | website About page: "infrastructure", "roads" |
| pf-030248 | Dadi Fm | religion | Specialist | website About page: "cristiano", "muslim" |
| pf-011272 | Waterloo Region Record | poverty | Has a section on it | website section "Development" |
| pf-011272 | Waterloo Region Record | partnerships | Has a section on it | website section "Development" |
| pf-008135 | Kelley Blue Book | science | Specialist | description mentions "research" |

## Not media, still shown

| Id | Name | Why |
|---|---|---|
| pf-004917 | Цитология и генетика (журнал) | academic journal, not a news outlet |
| pf-002073 | News | no real name ("News"), no website |
| pf-047188 | Sensing Murder | entertainment stream on Pluto TV, not a news outlet |
| pf-023565 | Magazine of the Sidi Khrebish Excavations | academic bulletin, not a news outlet |
| pf-058131 | 公益財団法人 国家基本問題研究所 | think tank, not a media outlet |
| pf-063587 | etypeservices.com | service company (e-edition vendor), not an outlet |
| pf-017571 | Известия высших учебных заведений. Математика | academic journal, not a news outlet |
| pf-008135 | Kelley Blue Book | car price guide, not a news outlet |
| pf-019971 | Philipsburg Mail | historic newspaper (archive website), no longer published |
