"""Wikidata: media outlets in the 195 allowed countries.

1. checks the root classes in config/sources/wikidata.yaml (label must match)
2. finds the Wikidata item of each allowed country (by ISO alpha-3, P298)
3. per country: all items that are an instance of a root class (or sub-class)
4. downloads the details of each item (labels, website, language, owner,
   social media accounts, ...) and the English names of all linked items
"""
import json
import time

import yaml

from common import ROOT, countries, fresh, get, save

SPARQL = "https://query.wikidata.org/sparql"
API = "https://www.wikidata.org/w/api.php"
LANGS = "en|fr|es|ar|ru|zh|pt|hi|sw|de|it|ja|ko|id|tr|fa|ur|bn|vi|th|pl|uk|nl"

# Properties we keep, by name. Values are Wikidata ids or plain strings.
PROPS = {
    "P31": "instance_of", "P17": "country", "P495": "country_of_origin",
    "P159": "headquarters", "P131": "located_in", "P2541": "operating_area",
    "P1001": "applies_to_jurisdiction",
    "P407": "language_of_work", "P364": "original_language",
    "P856": "website", "P968": "email",
    "P127": "owned_by", "P749": "parent_organization", "P463": "member_of",
    "P1454": "legal_form", "P921": "main_subject", "P136": "genre",
    "P101": "field_of_work", "P452": "industry",
    "P571": "inception", "P576": "dissolved", "P3999": "date_of_closure",
    "P2397": "youtube_channel_id", "P2013": "facebook_id", "P2003": "instagram_username",
    "P7085": "tiktok_username", "P2002": "x_username", "P3789": "telegram_username",
    "P1813": "short_name",
}
ITEM_VALUED = {"P31", "P17", "P495", "P159", "P131", "P2541", "P1001", "P407", "P364",
               "P127", "P749", "P463", "P1454", "P921", "P136", "P101", "P452"}


def sparql(query):
    time.sleep(1)  # be polite: at most one query per second
    for attempt in range(2):
        body = get(SPARQL, {"query": query, "format": "json"},
                   accept="application/sparql-results+json", timeout=90, tries=3)
        try:
            return json.loads(body)["results"]["bindings"]
        except ValueError:
            # Wikidata stopped mid-answer (query too slow): retry once, then give up
            time.sleep(10)
    raise RuntimeError("query result was cut off twice")


def entities(ids, props="labels|claims|sitelinks"):
    out = {}
    ids = sorted(ids)
    for i in range(0, len(ids), 50):
        body = get(API, {"action": "wbgetentities", "ids": "|".join(ids[i:i + 50]),
                         "props": props, "languages": LANGS, "format": "json"})
        out.update(json.loads(body).get("entities", {}))
        time.sleep(0.2)
    return out


def value_of(snak):
    dv = snak.get("datavalue", {}).get("value")
    if isinstance(dv, dict):
        return dv.get("id") or dv.get("time") or dv.get("text")
    return dv


def slim(entity):
    labels = {k: v["value"] for k, v in entity.get("labels", {}).items()}
    claims = {}
    for pid, name in PROPS.items():
        vals = []
        for st in entity.get("claims", {}).get(pid, []):
            if st.get("rank") == "deprecated":
                continue
            v = value_of(st.get("mainsnak", {}))
            if v is not None and v not in vals:
                vals.append(v)
        if vals:
            claims[name] = vals
    sitelinks = entity.get("sitelinks", {})
    wikipedias = sorted(k for k in sitelinks if k.endswith("wiki") and k not in
                        ("commonswiki", "specieswiki", "metawiki", "wikidatawiki", "mediawikiwiki"))
    return {"qid": entity["id"], "labels": labels, **claims,
            "wikipedia_languages": len(wikipedias),
            "wikipedia_titles": {k: sitelinks[k]["title"] for k in wikipedias
                                 if k in ("enwiki", "frwiki", "eswiki", "arwiki", "ruwiki", "zhwiki", "ptwiki")}}


def main():
    if fresh("wikidata", 7):
        print("Wikidata was fetched less than 7 days ago: skipped (set FORCE_FETCH=1 to force)")
        return
    cfg = yaml.safe_load(open(ROOT / "config" / "sources" / "wikidata.yaml", encoding="utf-8"))
    report = {"class_check": [], "class_search": {}, "countries_missing": [], "timeouts": []}

    # 1. check root classes
    roots = []
    ents = entities([c["qid"] for c in cfg["root_classes"]], props="labels")
    for c in cfg["root_classes"]:
        label = ents.get(c["qid"], {}).get("labels", {}).get("en", {}).get("value", "")
        ok = label.lower() == c["expected_label"].lower()
        report["class_check"].append({**c, "wikidata_label": label, "ok": ok})
        if ok:
            roots.append(c["qid"])
        print(("OK  " if ok else "SKIP"), c["qid"], c["expected_label"], "->", label)
    for name in cfg.get("search_classes", []):
        hits = json.loads(get(API, {"action": "wbsearchentities", "search": name,
                                    "language": "en", "type": "item", "limit": 5,
                                    "format": "json"})).get("search", [])
        report["class_search"][name] = [{"qid": h["id"], "label": h.get("label"),
                                         "description": h.get("description")} for h in hits]

    # 2. country items
    allowed = {r["iso3"]: r for r in countries().values()}
    rows = sparql("SELECT ?c ?iso WHERE { ?c wdt:P298 ?iso . "
                  "FILTER NOT EXISTS { ?c wdt:P576 ?end } }")
    country_qid = {}
    for r in rows:
        iso = r["iso"]["value"]
        if iso in allowed and iso not in country_qid:
            country_qid[iso] = r["c"]["value"].rsplit("/", 1)[1]
    report["countries_missing"] = sorted(set(allowed) - set(country_qid))
    print(f"countries found in Wikidata: {len(country_qid)} of {len(allowed)}")

    # 3. outlets per country
    found = {}  # qid -> {"countries": set(), "roots": set()}
    values = " ".join(f"wd:{q}" for q in roots)
    for n, (iso, cq) in enumerate(sorted(country_qid.items()), 1):
        try:
            res = sparql(f"SELECT DISTINCT ?item ?root WHERE {{ VALUES ?root {{ {values} }} "
                         f"?item wdt:P17 wd:{cq} . ?item wdt:P31/wdt:P279* ?root . }}")
        except RuntimeError:
            res = []
            for q in roots:  # too big at once: one class at a time
                try:
                    res += sparql(f"SELECT DISTINCT ?item ?root WHERE {{ VALUES ?root {{ wd:{q} }} "
                                  f"?item wdt:P17 wd:{cq} . ?item wdt:P31/wdt:P279* ?root . }}")
                except RuntimeError:
                    report["timeouts"].append({"country": iso, "class": q})
        for r in res:
            q = r["item"]["value"].rsplit("/", 1)[1]
            f = found.setdefault(q, {"countries": set(), "roots": set()})
            f["countries"].add(iso)
            f["roots"].add(r["root"]["value"].rsplit("/", 1)[1])
        print(f"[{n}/{len(country_qid)}] {iso}: {len(res)} rows, total items {len(found)}")

    # 4. details
    details = entities(found.keys())
    records = []
    linked = set()
    for q, f in found.items():
        e = details.get(q)
        if not e or "missing" in e:
            continue
        rec = slim(e)
        rec["matched_countries"] = sorted(f["countries"])
        rec["matched_classes"] = sorted(f["roots"])
        records.append(rec)
        for name in (PROPS[p] for p in ITEM_VALUED):
            linked.update(v for v in rec.get(name, []) if isinstance(v, str) and v.startswith("Q"))
    names = {q: e.get("labels", {}).get("en", {}).get("value")
             for q, e in entities(linked, props="labels").items()}
    records.sort(key=lambda r: int(r["qid"][1:]))
    save("wikidata", records, {
        "url": SPARQL + " + " + API,
        "root_classes_used": roots,
        "country_items": country_qid,
        "licence": "Wikidata: CC0 (public domain)",
        **report,
    })
    with open(ROOT / "raw" / "wikidata" / "linked_labels.json", "w", encoding="utf-8") as fh:
        json.dump(names, fh, ensure_ascii=False, sort_keys=True, indent=0)


if __name__ == "__main__":
    main()
