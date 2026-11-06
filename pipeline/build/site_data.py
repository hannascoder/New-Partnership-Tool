"""Builds the files the website reads (site/data/):
  outlets.json   one compact entry per outlet (short keys, empty fields left out)
  config.json    allowed values for the filters (from config/), so the page
                 never hard-codes a category, country or language
The website only reads these two files (briefing K1)."""
import csv
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config"
SOCIAL_URL = {"youtube": "https://www.youtube.com/channel/{}", "facebook": "https://www.facebook.com/{}",
              "instagram": "https://www.instagram.com/{}", "tiktok": "https://www.tiktok.com/@{}",
              "x": "https://x.com/{}", "telegram": "https://t.me/{}"}
SOURCE_LABEL = {"wikidata": "Wikidata", "media_cloud": "Media Cloud", "iptv_org": "iptv-org",
                "radio_browser": "Radio Browser", "sdg_media_compact": "SDG Media Compact",
                "efcsn_signatories": "EFCSN", "news_agencies": "Wikipedia: news agencies",
                "state_media": "Wikipedia: state media", "fact_checking_sites": "Wikipedia: fact-checking websites",
                "ebu_members": "EBU", "abu_members": "ABU", "asbu_members": "ASBU", "cbu_members": "CBU"}


def main():
    outlets = json.load(open(ROOT / "work" / "classified.json", encoding="utf-8"))
    countries = list(csv.DictReader(open(CFG / "countries.csv", encoding="utf-8")))
    langs_all = {r["code"]: r for r in csv.DictReader(open(CFG / "languages.csv", encoding="utf-8"))}
    cats = yaml.safe_load(open(CFG / "categories.yaml", encoding="utf-8"))

    # prominence and rank within the country (briefing J)
    for o in outlets:
        o["_prom"] = (o.get("wikipedia_languages") or 0) + len(o["sources"])
    by_country = defaultdict(list)
    for o in outlets:
        by_country[o["country"]].append(o)
    for lst in by_country.values():
        lst.sort(key=lambda o: (-o["_prom"], (o["name"] or "").lower()))
        for i, o in enumerate(lst, 1):
            o["_rank"] = i

    out, used_langs = [], set()
    for o in outlets:
        e = {"i": o["id"], "n": o["name"], "c": o["country"], "p": o["_prom"], "r": o["_rank"]}
        alt = [a for a in o["alt_names"] if a.isascii()][:3]
        if alt:
            e["a"] = alt
        if o.get("website"):
            e["w"] = o["website"]
        if o["languages"]:
            e["l"] = o["languages"]
            used_langs.update(o["languages"])
        if o["channels"]:
            e["ch"] = o["channels"]
        social = {k: SOCIAL_URL[k].format(v) for k, v in (o.get("social") or {}).items() if k in SOCIAL_URL}
        if social:
            e["so"] = social
        if o.get("email"):
            e["em"] = o["email"]
        e["s"] = o["sources"]
        if "sdg_media_compact" in o["sources"]:
            e["un"] = ["un_relationship"]
        e["f"] = o["first_seen"]
        cat = o.get("cat", {})
        if cat.get("org_type"):
            e["o"] = [cat["org_type"]["value"], cat["org_type"]["source"]]
        out.append(e)
    out.sort(key=lambda e: (e["n"] or "").lower())

    regions = {}
    for c in countries:
        regions.setdefault(c["region"], set()).add(c["intermediate_region"] or c["subregion"])
    config = {
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "data_date": max(o["first_seen"] for o in outlets) if outlets else str(date.today()),
        "countries": [{"iso3": c["iso3"], "name": c["name"], "aliases": c["aliases"], "status": c["status"],
                       "region": c["region"], "subregion": c["intermediate_region"] or c["subregion"]}
                      for c in countries],
        "regions": {k: sorted(v) for k, v in sorted(regions.items())},
        "language_buttons": sorted(({"code": r["code"], "name": r["name"], "order": int(r["button"])}
                                    for r in langs_all.values() if r["button"]), key=lambda x: x["order"]),
        "languages": sorted(({"code": c, "name": langs_all[c]["name"]} for c in used_langs if c in langs_all),
                            key=lambda x: x["name"]),
        "categories": {k: cats[k] for k in ("material", "org_type", "channel", "ownership", "scope",
                                             "topic_groups", "topics", "un_profile", "size", "checkboxes", "sort")},
        "size_note": cats.get("size_note"),
        "source_labels": SOURCE_LABEL,
        # filters that get values in step 4 (classification)
        "pending": ["ownership", "scope", "topics", "reach", "website_check"],
    }
    data = ROOT / "site" / "data"
    data.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(data / "outlets.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(config, open(data / "config.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"site/data/outlets.json: {len(out)} outlets, {(data / 'outlets.json').stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
