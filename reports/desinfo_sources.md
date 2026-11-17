# Disinformation monitor: sources of the last run

Fetched: 2026-11-17T17:48:01Z  |  items in the site data: 558

## Google Fact Check Tools API
- {'items': 242, 'requests': 1800, 'errors': [], 'max_age_days': 14}

## Fact-checker feeds
| Feed | Works | Items | Note |
|---|---|---|---|
| AFP Fact Check | NO |  | failed after 2 tries: https://factcheck.afp.com/rss.xml (HTTP Error 403: Forbidden) |
| Full Fact | yes | 10 |  |
| Africa Check | NO |  | failed after 2 tries: https://africacheck.org/feed (HTTP Error 403: Forbidden) |
| Maldita.es | yes | 50 |  |
| Newtral | yes | 10 |  |
| Aos Fatos | yes | 20 |  |
| BOOM | yes | 2 |  |
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
| Colombiacheck | yes | 20 |  |
| Chequeado | yes | 50 |  |
| Cekfakta / Mafindo | yes | 10 |  |

Feeds marked NO: correct or remove the address in `config/factcheck_sources.yaml`.

## UN feeds (content-gap check)
Fetched: 2026-11-17T17:54:53Z | UN articles in the last 12 months: 333

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
| UN Verified (en) | NO | 0 | failed after 2 tries: https://shareverified.org/feed/ (<urlopen error [Errno -2] Name or service not known>) |
| UN Press (en) | yes | 10 |  |
| WHO (en) | yes | 83 |  |
| WHO (es) | yes | 25 |  |
| WHO (fr) | yes | 25 |  |
| UNICEF (en) | NO | 0 | failed after 2 tries: https://www.unicef.org/press-releases/rss.xml (HTTP Error 404: Not Found) |
| UNHCR (en) | NO | 0 | failed after 2 tries: https://www.unhcr.org/rss/news.xml (HTTP Error 404: Not Found) |
| FAO (en) | NO | 0 | failed after 2 tries: https://www.fao.org/newsroom/rss-feed/en/ (HTTP Error 404: Not Found) |
| WFP (en) | NO | 0 | failed after 2 tries: https://www.wfp.org/rss.xml (HTTP Error 404: Not Found) |
| UNEP (en) | NO | 0 | failed after 2 tries: https://www.unep.org/rss.xml (HTTP Error 404: Not Found) |
| UNESCO (en) | NO | 0 | failed after 2 tries: https://www.unesco.org/en/rss.xml (<urlopen error _ssl.c:994: The handshake operation timed out>) |
| OHCHR (en) | yes | 10 |  |
| UNDP (en) | NO | 0 | failed after 2 tries: https://www.undp.org/rss.xml (HTTP Error 403: Forbidden) |
| UN Women (en) | NO | 0 | failed after 2 tries: https://www.unwomen.org/en/rss-feeds/news (HTTP Error 403: Forbidden) |
| IOM (en) | NO | 0 | failed after 2 tries: https://www.iom.int/rss.xml (HTTP Error 404: Not Found) |
| UNFPA (en) | yes | 10 |  |

Sources marked NO: correct the address in `config/un_sources.yaml`.
