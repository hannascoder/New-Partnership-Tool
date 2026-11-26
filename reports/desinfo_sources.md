# Disinformation monitor: sources of the last run

Fetched: 2026-11-26T14:47:30Z  |  items in the site data: 8222

## Google Fact Check Tools API
- {'items': 191, 'requests': 1742, 'errors': [], 'max_age_days': 14}

## Fact-checker feeds
| Feed | Works | Items | Note |
|---|---|---|---|
| AFP Fact Check | NO |  | failed after 2 tries: https://factcheck.afp.com/rss.xml (HTTP Error 403: Forbidden) |
| Full Fact | yes | 10 |  |
| Africa Check | NO |  | failed after 2 tries: https://africacheck.org/feed (HTTP Error 403: Forbidden) |
| Maldita.es | yes | 50 |  |
| Newtral | yes | 10 |  |
| Aos Fatos | NO |  | failed after 2 tries: https://www.aosfatos.org/noticias/feed/ (HTTP Error 404: Not Found) |
| BOOM | yes | 4 |  |
| Vera Files | NO |  | syntax error: line 1, column 0 |
| Teyit | yes | 10 |  |
| PolitiFact | yes | 20 |  |
| FactCheck.org | yes | 10 |  |
| Snopes | yes | 20 |  |
| Lead Stories | yes | 15 |  |
| Correctiv | yes | 1 |  |
| Les Surligneurs / AFP Factuel | NO |  | failed after 2 tries: https://factuel.afp.com/rss.xml (HTTP Error 403: Forbidden) |
| PesaCheck | NO |  | failed after 2 tries: https://pesacheck.org/feed (HTTP Error 403: Forbidden) |
| Dubawa | NO |  | failed after 2 tries: https://dubawa.org/feed/ (HTTP Error 415: Unsupported Media Type) |
| Fatabyyano | yes | 10 |  |
| Colombiacheck | NO |  | failed after 2 tries: https://colombiacheck.com/feed (HTTP Error 403: Forbidden) |
| Chequeado | yes | 50 |  |
| Cekfakta / Mafindo | yes | 10 |  |

Feeds marked NO: correct or remove the address in `config/factcheck_sources.yaml`.

## UN feeds (content-gap check)
Fetched: 2026-11-26T14:53:06Z | UN articles in the last 12 months: 2218

| Source | Works | Items | Note |
|---|---|---|---|
| UN News (en) | yes | 30 |  |
| UN News (fr) | yes | 30 |  |
| UN News (es) | yes | 30 |  |
| UN News (ar) | yes | 30 |  |
| UN News (ru) | yes | 30 |  |
| UN News (zh) | yes | 30 |  |
| UN News (pt) | yes | 30 |  |
| UN News (hi) | yes | 30 |  |
| UN News (sw) | yes | 30 |  |
| UN Verified (en) | NO | 0 | failed after 2 tries: https://shareverified.org/feed/ (<urlopen error [Errno -2] Name or service not known>) (searched on 2026-11-17, next search later) |
| UN Press (en) | yes | 10 |  |
| WHO (en) | yes | 83 |  |
| WHO (es) | yes | 25 |  |
| WHO (fr) | yes | 25 |  |
| UNICEF (en) | NO | 0 | failed after 2 tries: https://www.unicef.org/press-releases/rss.xml (HTTP Error 404: Not Found) (searched on 2026-11-17, next search later) |
| UNHCR (en) | NO | 0 | failed after 2 tries: https://www.unhcr.org/rss/news.xml (HTTP Error 403: Forbidden) (searched on 2026-11-17, next search later) |
| FAO (en) | NO | 0 | failed after 2 tries: https://www.fao.org/newsroom/rss-feed/en/ (HTTP Error 404: Not Found) (searched on 2026-11-18, next search later) |
| WFP (en) | NO | 0 | failed after 2 tries: https://www.wfp.org/rss.xml (HTTP Error 404: Not Found) (searched on 2026-11-18, next search later) |
| UNEP (en) | NO | 0 | failed after 2 tries: https://www.unep.org/rss.xml (HTTP Error 404: Not Found) (searched on 2026-11-18, next search later) |
| UNESCO (en) | NO | 0 | failed after 2 tries: https://www.unesco.org/en/rss.xml (Remote end closed connection without response) (searched on 2026-11-18, next search later) |
| OHCHR (en) | yes | 10 |  |
| UNDP (en) | NO | 0 | failed after 2 tries: https://www.undp.org/rss.xml (HTTP Error 403: Forbidden) (searched on 2026-11-18, next search later) |
| UN Women (en) | NO | 0 | failed after 2 tries: https://www.unwomen.org/en/rss-feeds/news (HTTP Error 403: Forbidden) (searched on 2026-11-18, next search later) |
| IOM (en) | NO | 0 | failed after 2 tries: https://www.iom.int/rss.xml (HTTP Error 404: Not Found) (searched on 2026-11-19, next search later) |
| UNFPA (en) | yes | 10 |  |
| UN News: climate-change (en) | yes | 30 |  |
| UN News: health (en) | yes | 30 |  |
| UN News: humanitarian-aid (en) | yes | 30 |  |
| UN News: migrants-and-refugees (en) | yes | 30 |  |
| UN News: peace-and-security (en) | yes | 30 |  |
| UN News: human-rights (en) | yes | 30 |  |
| UN News: women (en) | yes | 30 |  |
| UN News: economic-development (en) | yes | 30 |  |
| UN News: law-and-crime-prevention (en) | yes | 30 |  |
| UN News: culture-and-education (en) | yes | 30 |  |
| UN News: un-affairs (en) | yes | 30 |  |
| UN News: sdgs (en) | yes | 30 |  |
| UN News: climate-change (es) | yes | 30 |  |
| UN News: health (es) | yes | 30 |  |
| UN News: humanitarian-aid (es) | yes | 30 |  |
| UN News: migrants-and-refugees (es) | yes | 30 |  |
| UN News: peace-and-security (es) | yes | 30 |  |
| UN News: human-rights (es) | yes | 30 |  |
| UN News: women (es) | yes | 30 |  |
| UN News: economic-development (es) | yes | 30 |  |
| UN News: law-and-crime-prevention (es) | yes | 30 |  |
| UN News: culture-and-education (es) | yes | 30 |  |
| UN News: un-affairs (es) | yes | 30 |  |
| UN News: sdgs (es) | yes | 30 |  |
| UN News: climate-change (fr) | yes | 30 |  |
| UN News: health (fr) | yes | 30 |  |
| UN News: humanitarian-aid (fr) | yes | 30 |  |
| UN News: migrants-and-refugees (fr) | yes | 30 |  |
| UN News: peace-and-security (fr) | yes | 30 |  |
| UN News: human-rights (fr) | yes | 30 |  |
| UN News: women (fr) | yes | 30 |  |
| UN News: economic-development (fr) | yes | 30 |  |
| UN News: law-and-crime-prevention (fr) | yes | 30 |  |
| UN News: culture-and-education (fr) | yes | 30 |  |
| UN News: un-affairs (fr) | yes | 30 |  |
| UN News: sdgs (fr) | yes | 30 |  |
| UN News: climate-change (pt) | yes | 30 |  |
| UN News: health (pt) | yes | 30 |  |
| UN News: humanitarian-aid (pt) | yes | 30 |  |
| UN News: migrants-and-refugees (pt) | yes | 30 |  |
| UN News: peace-and-security (pt) | yes | 30 |  |
| UN News: human-rights (pt) | yes | 30 |  |
| UN News: women (pt) | yes | 30 |  |
| UN News: economic-development (pt) | yes | 30 |  |
| UN News: law-and-crime-prevention (pt) | yes | 30 |  |
| UN News: culture-and-education (pt) | yes | 30 |  |
| UN News: un-affairs (pt) | yes | 30 |  |
| UN News: sdgs (pt) | yes | 30 |  |

Sources marked NO: correct the address in `config/un_sources.yaml`.
