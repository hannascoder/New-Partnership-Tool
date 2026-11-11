"""Wikidata: media outlets (or, with WIKIDATA_KIND=ngo, NGOs) in the 195 allowed countries.

WIKIDATA_KIND=ngo (phase 2, owner 10.11.2026): classes from config/sources/wikidata_ngo.yaml,
only items with at least one Wikipedia/Wikimedia page (known NGOs, not every registered
association), output raw/wikidata_ngo/.

1. checks the root classes in config/sources/wikidata.yaml (label must match)
2. finds the Wikidata item of each allowed country (by ISO alpha-3, P298)
3. per country: all items that are an instance of a root class (or sub-class)
4. downloads the details of each item (labels, website, language, owner,
   social media accounts, ...) and the English names of all linked items
"""
import gzip
import json
import time
from datetime import datetime, timezone

import yaml

from common import ROOT, countries, fresh, get, save  # noqa: F401

KIND = __import__("os").environ.get("WIKIDATA_KIND", "media")
SOURCE = "wikidata_ngo" if KIND == "ngo" else "wikidata"
CONFIG = "wikidata_ngo.yaml" if KIND == "ngo" else "wikidata.yaml"
# NGOs: only items that have a page in at least one Wikipedia (sitelinks > 0)
EXTRA = " ?item wikibase:sitelinks ?sl . FILTER(?sl > 0) " if KIND == "ngo" else ""

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
    "P1813": "short_name", "P1142": "political_ideology", "P2936": "language_used",
}
ITEM_VALUED = {"P31", "P17", "P495", "P159", "P131", "P2541", "P1001", "P407", "P364",
               "P127", "P749", "P463", "P1454", "P921", "P136", "P101", "P452", "P1142", "P2936"}


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


START = time.time()
BUDGET_MIN = float(__import__("os").environ.get("WIKIDATA_MINUTES", "200"))
FRESH_DAYS = 7


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def out_of_time():
    return (time.time() - START) / 60 > BUDGET_MIN


def is_fresh(stamp):
    if not stamp or __import__("os").environ.get("FORCE_FETCH") == "1":
        return False
    when = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - when).days < FRESH_DAYS


def checkpoint_fresh(path):
    try:
        return is_fresh(json.load(open(path, encoding="utf-8")).get("fetched_at"))
    except (OSError, ValueError):
        return False


def checkpoint_fresh_record(rec):
    return bool(rec) and is_fresh(rec.get("_fetched_at"))


def write_cache(path, cache):
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    tmp.replace(path)


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def main():
    if fresh(SOURCE, FRESH_DAYS):
        print("Wikidata was fetched less than 7 days ago: skipped (set FORCE_FETCH=1 to force)")
        return
    cfg = yaml.safe_load(open(ROOT / "config" / "sources" / CONFIG, encoding="utf-8"))
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

    # 3. outlets per country (checkpoint per country in raw/wikidata/items/)
    items_dir = ROOT / "raw" / SOURCE / "items"
    items_dir.mkdir(parents=True, exist_ok=True)
    found = {}  # qid -> {"countries": set(), "roots": set()}
    values = " ".join(f"wd:{q}" for q in roots)
    complete = True
    for n, (iso, cq) in enumerate(sorted(country_qid.items()), 1):
        cp = items_dir / f"{iso}.json"
        rows = None
        if checkpoint_fresh(cp):
            rows = json.load(open(cp, encoding="utf-8"))["rows"]
        elif out_of_time():
            complete = False
            print(f"time budget used up before {iso}: continue next run")
            break
        else:
            res, failed = [], []
            try:
                res = sparql(f"SELECT DISTINCT ?item ?root WHERE {{ VALUES ?root {{ {values} }} "
                             f"?item wdt:P17 wd:{cq} . ?item wdt:P31/wdt:P279* ?root . {EXTRA}}}")
            except RuntimeError:
                for q in roots:  # too big at once: one class at a time
                    try:
                        res += sparql(f"SELECT DISTINCT ?item ?root WHERE {{ VALUES ?root {{ wd:{q} }} "
                                      f"?item wdt:P17 wd:{cq} . ?item wdt:P31/wdt:P279* ?root . {EXTRA}}}")
                    except RuntimeError:
                        failed.append(q)
                        report["timeouts"].append({"country": iso, "class": q})
            rows = [[r["item"]["value"].rsplit("/", 1)[1], r["root"]["value"].rsplit("/", 1)[1]] for r in res]
            if not failed:  # only complete countries are kept as checkpoint
                json.dump({"fetched_at": now(), "rows": rows}, open(cp, "w", encoding="utf-8"))
        for q, root in rows:
            f = found.setdefault(q, {"countries": set(), "roots": set()})
            f["countries"].add(iso)
            f["roots"].add(root)
        print(f"[{n}/{len(country_qid)}] {iso}: {len(rows)} rows, total items {len(found)}", flush=True)

    # 4. details (cache in raw/wikidata/details_cache.json.gz, slimmed per batch)
    cache_file = ROOT / "raw" / SOURCE / "details_cache.json.gz"
    cache = json.load(gzip.open(cache_file, "rt", encoding="utf-8")) if cache_file.exists() else {}
    todo = sorted(q for q in found if not checkpoint_fresh_record(cache.get(q)))
    print(f"details: {len(found) - len(todo)} from cache, {len(todo)} to fetch", flush=True)
    for i in range(0, len(todo), 50):
        if out_of_time():
            complete = False
            print("time budget used up during details: continue next run")
            break
        for q, e in entities(todo[i:i + 50]).items():
            if e and "missing" not in e:
                cache[q] = {**slim(e), "_fetched_at": now()}
        if i % 5000 == 0:
            print(f"details {i}/{len(todo)}", flush=True)
            write_cache(cache_file, cache)
    write_cache(cache_file, cache)

    records, linked = [], set()
    for q, f in found.items():
        rec = cache.get(q)
        if not rec:
            continue
        rec = {k: v for k, v in rec.items() if k != "_fetched_at"}
        rec["matched_countries"] = sorted(f["countries"])
        rec["matched_classes"] = sorted(f["roots"])
        records.append(rec)
        for name in (PROPS[p] for p in ITEM_VALUED):
            linked.update(v for v in rec.get(name, []) if isinstance(v, str) and v.startswith("Q"))
    if not complete:
        print("INCOMPLETE run: checkpoints saved, data.json.gz not replaced")
        return
    names = {}
    for i, chunk in enumerate(chunks(sorted(linked), 50)):
        for q, e in entities(chunk, props="labels").items():
            names[q] = e.get("labels", {}).get("en", {}).get("value")
    records.sort(key=lambda r: int(r["qid"][1:]))
    save(SOURCE, records, {
        "url": SPARQL + " + " + API,
        "root_classes_used": roots,
        "country_items": country_qid,
        "licence": "Wikidata: CC0 (public domain)",
        **report,
    })
    with open(ROOT / "raw" / SOURCE / "linked_labels.json", "w", encoding="utf-8") as fh:
        json.dump(names, fh, ensure_ascii=False, sort_keys=True, indent=0)


if __name__ == "__main__":
    main()
