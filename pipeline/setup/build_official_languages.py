"""Build config/official_languages.csv: the official languages of every country.

Used by the UN profile "Reaches underserved audiences" (docs/KATEGORIEN.md 7):
an outlet in a language that is NOT official in its country (and not one of
the 9 language buttons) serves a minority-language audience.

Run only when the reference file changes:
    python pipeline/setup/build_official_languages.py

Input:  raw/reference/cldr_official_languages.json
        (Unicode CLDR 48, npm package cldr-core 48.0.0, file
        supplemental/territoryInfo.json, Unicode License v3; only the
        "officialStatus" of each language per country is kept)
Output: config/official_languages.csv  iso3, languages (ISO 639-3, ";"-separated)

Every official status counts: national ("official", "de_facto_official")
and regional ("official_regional", e.g. Catalan in Spain, Tamil in India).
So "minority language" means: no official status anywhere in the country.
The file can be corrected by hand; a hand edit is lost when this script runs again.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# ISO 639-3 codes the outlets use for the same language as the CLDR code
SAME = {"fil": ["tgl"], "nep": ["npi"], "ori": ["ory"], "srp": ["cnr"], "nob": ["nor"], "ckb": ["kur"], "kmr": ["kur"], "nno": ["nor"], "msa": ["zsm"], "fas": ["pes", "prs"], "zho": ["cmn", "yue"]}


def main():
    cldr = json.load(open(ROOT / "raw" / "reference" / "cldr_official_languages.json", encoding="utf-8"))["official_status"]
    langs = list(csv.DictReader(open(ROOT / "config" / "languages.csv", encoding="utf-8")))
    two = {r["iso639_1"]: r["code"] for r in langs if r["iso639_1"]}
    three = {r["code"] for r in langs}
    rows = []
    for c in csv.DictReader(open(ROOT / "config" / "countries.csv", encoding="utf-8")):
        out = []
        for code in cldr.get(c["iso2"], {}):
            base = code.split("_")[0]  # "sd_Deva" -> "sd"
            iso3 = two.get(base) or (base if base in three else None)
            for x in [iso3] + SAME.get(iso3, []):
                if x and x not in out:
                    out.append(x)
        rows.append({"iso3": c["iso3"], "name": c["name"], "official_languages": ";".join(sorted(out))})
    with open(ROOT / "config" / "official_languages.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["iso3", "name", "official_languages"])
        w.writeheader()
        w.writerows(rows)
    print(f"config/official_languages.csv: {len(rows)} countries, {sum(1 for r in rows if not r['official_languages'])} without data")


if __name__ == "__main__":
    main()
