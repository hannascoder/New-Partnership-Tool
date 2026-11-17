"""Data for "Start from a UN text" (the box above the results).

    python pipeline/build/dropin.py

Reads  config/dropin.yaml, config/topic_keywords.yaml, config/categories.yaml,
       config/countries.csv, config/languages.csv
Writes site/data/dropin.json  (loaded by site/assets/finder-dropin.js only when
       someone uses the box)

Also called by pipeline/build/site_data.py, so the automatic update keeps the
file in step with the keyword lists. Stops with a clear message when
config/dropin.yaml names a topic, format or country that does not exist.
"""
import csv
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config"


def words(by_lang):
    """{"en": [...], "fr": [...]} -> one list without repeats"""
    out = []
    for lst in (by_lang or {}).values():
        for w in lst or []:
            w = str(w).strip()
            if w and w not in out:
                out.append(w)
    return out


def build():
    rules = yaml.safe_load(open(CFG / "dropin.yaml", encoding="utf-8"))
    cats = yaml.safe_load(open(CFG / "categories.yaml", encoding="utf-8"))
    kw = yaml.safe_load(open(CFG / "topic_keywords.yaml", encoding="utf-8"))["topics"]
    countries = list(csv.DictReader(open(CFG / "countries.csv", encoding="utf-8")))
    errors = []

    topic_ids = {t["id"] for t in cats["topics"]}
    merged = {t["id"]: t["merged_into"].split("/")[0] for t in cats["topics"] if t.get("merged_into")}
    topics, exclude = {}, []
    for tid, t in kw.items():
        target = merged.get(tid, tid)
        entry = topics.setdefault(target, {"strong": [], "context": []})
        for sub in t.get("subtopics") or []:
            entry["strong"] += [w for w in words(sub.get("strong")) if w not in entry["strong"]]
        entry["context"] += [w for w in words(t.get("context")) if w not in entry["context"]]
        ex = t.get("exclude")
        exclude += [w for w in (words(ex) if isinstance(ex, dict) else (ex or [])) if w not in exclude]
    for tid, extra in (rules.get("extra_topic_words") or {}).items():
        if tid not in topic_ids:
            errors.append(f"extra_topic_words: topic '{tid}' is not in categories.yaml")
            continue
        entry = topics.setdefault(merged.get(tid, tid), {"strong": [], "context": []})
        entry["strong"] += [str(w) for w in extra if str(w) not in entry["strong"]]

    material_ids = {m["id"] for m in cats["material"]}
    for f in rules.get("formats") or {}:
        if f not in material_ids:
            errors.append(f"formats: '{f}' is not a material in categories.yaml")

    iso = {c["iso3"] for c in countries}
    places = {}
    for c in countries:
        names = [c["name"], c["name"].split(" (")[0]] + [a.strip() for a in c["aliases"].split(";")]
        names += [str(p) for p in (rules.get("places") or {}).get(c["iso3"], [])]
        places[c["iso3"]] = list(dict.fromkeys(n for n in names if n))
    for code in rules.get("places") or {}:
        if code not in iso:
            errors.append(f"places: '{code}' is not a country code in countries.csv")
    seen = {}
    for code, names in places.items():
        for n in names:
            if seen.setdefault(n.casefold(), code) != code:
                errors.append(f"places: '{n}' is listed for {seen[n.casefold()]} and {code}")

    # language names: the buttons plus every language with a 2-letter code (the widely used ones)
    langs = {}
    for row in csv.DictReader(open(CFG / "languages.csv", encoding="utf-8")):
        if row.get("button") or row.get("iso639_1") or row.get("part1"):
            langs[row["name"]] = row.get("code") or row.get("iso639_3") or row.get("id")

    if errors:
        sys.exit("config/dropin.yaml:\n  " + "\n  ".join(errors))
    out = {
        "limits": {k: rules[k] for k in ("max_topics", "min_topic_score", "topic_share", "max_countries", "country_share")},
        "apply_language": bool(rules.get("apply_language")),
        "only_matches": rules.get("only_matches") or {},
        "weak_matches": rules.get("weak_matches") or {},
        "skip_lines": rules.get("skip_lines") or [],
        "technical_markers": rules.get("technical_markers") or [],
        "ignore_phrases": rules.get("ignore_phrases") or [],
        "formats": rules.get("formats") or {},
        "shapes": [str(s) for s in rules.get("shapes") or []],
        "language_words": rules.get("language_words") or [],
        "languages": langs,
        "topics": topics,
        "exclude": exclude,
        "places": places,
    }
    target = ROOT / "site" / "data" / "dropin.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(target, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"site/data/dropin.json: {len(topics)} topics, {sum(len(v) for v in places.values())} place names, "
          f"{len(langs)} languages, {target.stat().st_size / 1e3:.0f} kB")


if __name__ == "__main__":
    build()
