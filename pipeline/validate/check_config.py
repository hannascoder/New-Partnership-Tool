"""Check the configuration files for mistakes.

    python pipeline/validate/check_config.py

Stops with a clear message if, for example, an id is used twice, a material
points to a channel that does not exist, or a country is missing.
Runs automatically on every pull request (.github/workflows/check-config.yml).
"""
import csv
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
errors = []


def ids(name, cats):
    values = [entry["id"] for entry in cats[name]]
    for value, n in Counter(values).items():
        if n > 1:
            errors.append(f"categories.yaml: id '{value}' appears {n} times in '{name}'")
    return set(values)


cats = yaml.safe_load(open(CONFIG / "categories.yaml", encoding="utf-8"))
lists = ["scope", "audience_basis", "material", "org_type", "channel", "social_platform",
         "ownership", "topic_groups", "topics", "un_profile", "size", "checkboxes", "sort", "methods"]
known = {}
for name in lists:
    if name not in cats:
        errors.append(f"categories.yaml: list '{name}' is missing")
        continue
    for entry in cats[name]:
        if "id" not in entry or "label" not in entry:
            errors.append(f"categories.yaml: an entry in '{name}' has no id or no label: {entry}")
    known[name] = ids(name, cats)

for m in cats.get("material", []):
    for ch in m.get("channels", []):
        if ch not in known.get("channel", set()):
            errors.append(f"material '{m['id']}' points to unknown channel '{ch}'")
    for ot in m.get("also_org_types", []):
        if ot not in known.get("org_type", set()):
            errors.append(f"material '{m['id']}' points to unknown org_type '{ot}'")
for t in cats.get("topics", []):
    if t.get("group") not in known.get("topic_groups", set()):
        errors.append(f"topic '{t['id']}' has unknown group '{t.get('group')}'")
sdgs = sorted(t["sdg"] for t in cats.get("topics", []) if "sdg" in t)
if sdgs != list(range(1, 18)):
    errors.append(f"topics: SDGs 1-17 must each appear exactly once, found {sdgs}")
if sum(1 for t in cats.get("topics", []) if t.get("default")) != 1:
    errors.append("topics: exactly one topic must be the default")

countries = list(csv.DictReader(open(CONFIG / "countries.csv", encoding="utf-8")))
status = Counter(c["status"] for c in countries)
if status != Counter(member=193, observer=2):
    errors.append(f"countries.csv: expected 193 members + 2 observers, found {dict(status)}")
for col in ("iso3", "iso2", "m49", "name"):
    for value, n in Counter(c[col] for c in countries).items():
        if n > 1:
            errors.append(f"countries.csv: {col} '{value}' appears {n} times")
regions = {"Africa", "Americas", "Asia", "Europe", "Oceania"}
for c in countries:
    if c["region"] not in regions:
        errors.append(f"countries.csv: {c['iso3']} has unknown region '{c['region']}'")

languages = list(csv.DictReader(open(CONFIG / "languages.csv", encoding="utf-8")))
for value, n in Counter(l["code"] for l in languages).items():
    if n > 1:
        errors.append(f"languages.csv: code '{value}' appears {n} times")
buttons = sorted(int(l["button"]) for l in languages if l["button"])
if buttons != list(range(1, 10)):
    errors.append(f"languages.csv: expected buttons 1-9, found {buttons}")

rules = yaml.safe_load(open(CONFIG / "rules.yaml", encoding="utf-8"))
if not isinstance(rules, dict) or not isinstance(rules.get("rules"), list):
    errors.append("rules.yaml: must contain 'rules:' followed by a list")

header = open(ROOT / "overrides.csv", encoding="utf-8").readline().strip()
if header != "outlet_id,field,value,note":
    errors.append(f"overrides.csv: first line must be 'outlet_id,field,value,note', found '{header}'")

if errors:
    print("Problems found:")
    for e in errors:
        print("  -", e)
    sys.exit(1)
print(f"Config OK: {len(countries)} countries, {len(languages)} languages, "
      f"{len(cats['topics'])} topics, {len(cats['un_profile'])} UN profiles, "
      f"{len(cats['channel'])} channels, {len(cats['org_type'])} organisation types.")
