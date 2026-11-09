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
         "ownership", "topic_groups", "topics", "audience", "un_profile", "size", "checkboxes", "sort", "methods"]
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
if not isinstance(rules, dict) or not isinstance(rules.get("org_type"), list):
    errors.append("rules.yaml: must contain 'org_type:' followed by a list")
else:
    for r in rules["org_type"]:
        if r.get("type") not in known.get("org_type", set()):
            errors.append(f"rules.yaml: unknown organisation type '{r.get('type')}'")

# step 4d: every topic / UN profile named in a mapping table must exist in categories.yaml
topic_ids, un_ids = known.get("topics", set()), known.get("un_profile", set())
aud_ids = {a["id"] for a in cats.get("audience", [])}
for f in ("iptv_org.yaml", "radio_browser.yaml", "wikidata.yaml"):
    m = yaml.safe_load(open(CONFIG / "sources" / f, encoding="utf-8")) or {}
    for t in (m.get("topics") or {}):
        if t not in topic_ids:
            errors.append(f"sources/{f}: unknown topic '{t}' under 'topics:'")
    for a in (m.get("audience") or {}):
        if a not in aud_ids:
            errors.append(f"sources/{f}: unknown target audience '{a}' under 'audience:'")
    for u in (m.get("un_profile") or {}):
        if u not in un_ids:
            errors.append(f"sources/{f}: unknown UN profile '{u}' under 'un_profile:'")
if isinstance(rules, dict):
    tr, ur = rules.get("topics") or {}, rules.get("un_profile") or {}
    for part in ("networks", "org_types", "scopes", "name_keywords"):
        for t in (tr.get(part) or {}):
            if t not in topic_ids:
                errors.append(f"rules.yaml: unknown topic '{t}' in topics -> {part}")
    for part in ("networks", "org_types", "topics"):
        for u in (ur.get(part) or {}):
            if u not in un_ids:
                errors.append(f"rules.yaml: unknown UN profile '{u}' in un_profile -> {part}")
        if part == "topics":
            for lst in (ur.get("topics") or {}).values():
                errors += [f"rules.yaml: unknown topic '{t}' in un_profile -> topics" for t in lst if t not in topic_ids]
    ar = rules.get("audience") or {}
    for part in ("org_types", "topics", "name_keywords"):
        for a in (ar.get(part) or {}):
            if a not in aud_ids:
                errors.append(f"rules.yaml: unknown target audience '{a}' in audience -> {part}")
    for lst in (ar.get("topics") or {}).values():
        errors += [f"rules.yaml: unknown topic '{t}' in audience -> topics" for t in lst if t not in topic_ids]
    if ar.get("minority_language") and ar["minority_language"] not in aud_ids:
        errors.append("rules.yaml: unknown target audience in audience -> minority_language")
    if ur.get("minority_language") and ur["minority_language"] not in un_ids:
        errors.append(f"rules.yaml: unknown UN profile '{ur['minority_language']}' in un_profile -> minority_language")

# topic keyword lists (config/topic_keywords.yaml)
kwf = yaml.safe_load(open(CONFIG / "topic_keywords.yaml", encoding="utf-8")) or {}
for tid, t in (kwf.get("topics") or {}).items():
    if tid not in topic_ids:
        errors.append(f"topic_keywords.yaml: unknown topic '{tid}'")
    subs = [x.get("id") for x in t.get("subtopics") or []]
    for x in t.get("subtopics") or []:
        if not x.get("id") or not x.get("label") or not x.get("strong"):
            errors.append(f"topic_keywords.yaml: sub-topic in '{tid}' needs id, label and strong words")
    if subs and t.get("general_subtopic") not in subs:
        errors.append(f"topic_keywords.yaml: '{tid}' needs general_subtopic, one of {subs}")
    if not subs and not t.get("strong"):
        errors.append(f"topic_keywords.yaml: '{tid}' has no strong words")

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
