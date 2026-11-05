"""Turns a country name as written in a source ("Japan", "DR Congo",
"Côte d'Ivoire", "UK") into our ISO alpha-3 code, or None.

Uses config/countries.csv (UN names and the `aliases` column) plus the extra
spellings in config/sources/country_names.yaml. Names that are not one of
the 195 (e.g. "Hong Kong", "Kosovo") return None on purpose."""
import csv
import re
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _key(name):
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)|\bthe\b", " ", s)
    return re.sub(r"[^a-z]+", " ", s).strip()


_TABLE = None


def table():
    global _TABLE
    if _TABLE is None:
        t = {}
        for r in csv.DictReader(open(ROOT / "config" / "countries.csv", encoding="utf-8")):
            names = [r["name"], r["iso3"], r["iso2"]] + [a for a in r["aliases"].split(";") if a.strip()]
            full = re.sub(r"\s*\((.*?)\)", r" \1", r["name"])  # "Iran (Islamic Republic of)" -> "Iran Islamic Republic of"
            names.append(full)
            for n in names:
                t[_key(n)] = r["iso3"]
        extra = yaml.safe_load(open(ROOT / "config" / "sources" / "country_names.yaml", encoding="utf-8"))
        for iso3, names in (extra.get("names") or {}).items():
            for n in names:
                t[_key(n)] = iso3
        for n in extra.get("not_allowed") or []:
            t[_key(n)] = None
        _TABLE = t
    return _TABLE


def to_iso3(name):
    if not name:
        return None
    return table().get(_key(name))


def known(name):
    """True if the name is recognised at all (as allowed or as not allowed)."""
    return _key(name) in table()
