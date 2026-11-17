# Disinformation monitor: sources of the last run

Fetched: 2026-11-17T19:09:07Z  |  items in the site data: 6032

## Google Fact Check Tools API
- {'items': 5750, 'requests': 1520, 'errors': ["HTTP 503 for 'تضليل'", "HTTP 503 for 'تعليم عن بعد'", "HTTP 503 for 'Éducation des filles'", "HTTP 503 for 'Flood'", "HTTP 503 for 'Transporte público'", "HTTP 503 for 'Vaccine'"], 'max_age_days': 365}

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
| Dubawa | yes | 10 |  |
| Fatabyyano | yes | 10 |  |
| Colombiacheck | yes | 20 |  |
| Chequeado | yes | 50 |  |
| Cekfakta / Mafindo | yes | 10 |  |

Feeds marked NO: correct or remove the address in `config/factcheck_sources.yaml`.
