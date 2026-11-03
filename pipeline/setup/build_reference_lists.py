"""Build config/countries.csv and config/languages.csv from the reference files.

Run only when a reference file changes:
    python pipeline/setup/build_reference_lists.py

Inputs (raw/reference/):
  un-membership.csv       193 UN member states + 2 observer states (ISO alpha-3)
  iso3166-m49_lukes.csv   ISO 3166 codes with UN M49 regions
                          (github.com/lukes/ISO-3166-Countries-with-Regional-Codes)
  iso639-3.json           ISO 639-3 language codes (SIL, via the npm package
                          iso-639-3 3.0.1 by wooorm, MIT)
Settings read from config/categories.yaml are not needed here; the 9 language
buttons are listed below because they are part of languages.csv.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "raw" / "reference"
CONFIG = ROOT / "config"

# ISO "X, Y of" names rewritten in the word order the UN uses.
UN_NAMES = {
    "COD": "Democratic Republic of the Congo",
    "KOR": "Republic of Korea",
    "PRK": "Democratic People's Republic of Korea",
    "MDA": "Republic of Moldova",
    "TZA": "United Republic of Tanzania",
    "PSE": "State of Palestine",
    "BOL": "Bolivia (Plurinational State of)",
    "IRN": "Iran (Islamic Republic of)",
    "FSM": "Micronesia (Federated States of)",
    "VEN": "Venezuela (Bolivarian Republic of)",
    "NLD": "Netherlands (Kingdom of the)",
}

# Everyday names people type into the search box.
ALIASES = {
    "COD": "DR Congo; DRC; Congo-Kinshasa",
    "COG": "Republic of the Congo; Congo-Brazzaville",
    "KOR": "South Korea",
    "PRK": "North Korea",
    "MDA": "Moldova",
    "TZA": "Tanzania",
    "PSE": "Palestine",
    "BOL": "Bolivia",
    "IRN": "Iran",
    "FSM": "Micronesia",
    "VEN": "Venezuela",
    "GBR": "United Kingdom; UK; Britain",
    "USA": "United States; USA; US",
    "RUS": "Russia",
    "SYR": "Syria",
    "LAO": "Laos",
    "VNM": "Vietnam",
    "CIV": "Ivory Coast",
    "TUR": "Turkey",
    "CZE": "Czech Republic",
    "SWZ": "Swaziland",
    "CPV": "Cape Verde",
    "TLS": "East Timor",
    "MMR": "Burma",
    "MKD": "Macedonia",
    "NLD": "Holland",
    "VAT": "Vatican",
    "BRN": "Brunei",
}

# The 9 language buttons (briefing section E), in display order.
BUTTONS = [
    ("ara", "Arabic"),
    ("zho", "Chinese (Mandarin)"),
    ("eng", "English"),
    ("fra", "French"),
    ("rus", "Russian"),
    ("spa", "Spanish"),
    ("hin", "Hindi"),
    ("por", "Portuguese"),
    ("swa", "Kiswahili"),
]


def build_countries():
    status = {r["iso3"]: r["status"] for r in csv.DictReader(open(REF / "un-membership.csv"))}
    m49 = {r["alpha-3"]: r for r in csv.DictReader(open(REF / "iso3166-m49_lukes.csv", encoding="utf-8"))}
    rows = []
    for iso3, st in status.items():
        r = m49[iso3]
        rows.append({
            "iso3": iso3,
            "iso2": r["alpha-2"],
            "m49": r["country-code"],
            "name": UN_NAMES.get(iso3, r["name"]),
            "aliases": ALIASES.get(iso3, ""),
            "status": st,
            "region": r["region"],
            "subregion": r["sub-region"],
            "intermediate_region": r["intermediate-region"],
        })
    rows.sort(key=lambda x: x["name"])
    members = sum(1 for x in rows if x["status"] == "member")
    observers = sum(1 for x in rows if x["status"] == "observer")
    assert members == 193 and observers == 2, (members, observers)
    with open(CONFIG / "countries.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"countries.csv: {members} members + {observers} observers")


def build_languages():
    langs = json.load(open(REF / "iso639-3.json", encoding="utf-8"))
    # Living languages only, individual languages and macrolanguages
    # (e.g. Arabic, Chinese and Kiswahili are macrolanguages).
    keep = [l for l in langs if l["type"] == "living" and l["scope"] in ("individual", "macrolanguage")]
    order = {code: i + 1 for i, (code, _) in enumerate(BUTTONS)}
    label = dict(BUTTONS)
    rows = [{
        "code": l["iso6393"],
        "iso639_1": l.get("iso6391", ""),
        "name": label.get(l["iso6393"], l["name"]),
        "scope": l["scope"],
        "button": order.get(l["iso6393"], ""),
    } for l in keep]
    assert all(any(r["code"] == c for r in rows) for c, _ in BUTTONS)
    rows.sort(key=lambda r: (r["button"] == "", r["button"] or 0, r["name"]))
    with open(CONFIG / "languages.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"languages.csv: {len(rows)} living languages, {len(BUTTONS)} buttons")


if __name__ == "__main__":
    build_countries()
    build_languages()
