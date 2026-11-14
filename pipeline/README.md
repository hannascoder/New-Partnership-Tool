# Pipeline

Run in this order (from the repository root):

```
python pipeline/normalize/networks.py      # members of network lists   -> work/networks.json
python pipeline/normalize/rsf.py           # RSF press freedom index    -> work/rsf.json
python pipeline/normalize/sources.py       # all sources, one format    -> work/records.json
python pipeline/merge/merge.py             # duplicates merged, ids     -> work/outlets.json
python pipeline/classify/classify.py       # categories (step 4)        -> work/classified.json, reports/topics.md
python pipeline/validate/known_outlets.py  # check: 20 known outlets    -> reports/known_outlets.md
python pipeline/validate/quality.py        # 200 hand-checked outlets  -> reports/quality.md
python pipeline/validate/reports.py        # step 5 reports            -> reports/coverage.md, sample.md, contradictions.md, changes.md
python pipeline/ngo/build.py               # NGOs (phase 2)            -> work/ngos.json, reports/ngos.md
python pipeline/build/site_data.py         # website data               -> site/data/
```

- `fetch/` downloads the sources (run by the "Fetch sources" workflow), raw data in `raw/`.
- `work/` holds intermediate files; they are rebuilt on every run and not stored in git.
- `cache/id_map.json` gives every outlet a stable id (pf-000001 ...): never delete it,
  corrections and "first seen" dates depend on it. `cache/first_seen.json` stores when
  an outlet was found the first time.
- `reports/` explains every run in plain words.

Reference lists (run only when a reference file in `raw/reference/` changes):
`pipeline/setup/build_reference_lists.py` (countries, languages) and
`pipeline/setup/build_official_languages.py` (official languages per country, from Unicode CLDR).
