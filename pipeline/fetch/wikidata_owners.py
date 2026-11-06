"""Wikidata: what kind of organisation owns each outlet (step 4b, ownership).

Takes the owners and parent organisations of all outlets in
raw/wikidata/data.json.gz and downloads their own classes (P31) and country
(P17), plus the owners of the owners (one level up), with English labels.
Output: raw/wikidata_owners/data.json.gz  {qid: {label, classes:[labels], country, owners:[qid]}}
"""
import gzip
import json
import time

from common import RAW, get, save

API = "https://www.wikidata.org/w/api.php"


def entities(ids):
    out = {}
    ids = sorted(ids)
    for i in range(0, len(ids), 50):
        body = get(API, {"action": "wbgetentities", "ids": "|".join(ids[i:i + 50]),
                         "props": "labels|claims", "languages": "en", "format": "json"})
        out.update(json.loads(body).get("entities", {}))
        time.sleep(0.2)
    return out


def claim_ids(e, pid):
    vals = []
    for st in e.get("claims", {}).get(pid, []):
        v = st.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(v, dict) and v.get("id") and st.get("rank") != "deprecated":
            vals.append(v["id"])
    return vals


def main():
    items = json.load(gzip.open(RAW / "wikidata" / "data.json.gz", "rt", encoding="utf-8"))
    owners = {q for r in items for q in r.get("owned_by", []) + r.get("parent_organization", [])}
    result, level = {}, owners
    for depth in (1, 2):  # owners, then owners of owners
        ents = entities(level - set(result))
        nxt = set()
        for q, e in ents.items():
            if "missing" in e:
                continue
            result[q] = {"label": e.get("labels", {}).get("en", {}).get("value"),
                         "class_qids": claim_ids(e, "P31"), "country": claim_ids(e, "P17")[:1],
                         "owners": claim_ids(e, "P127") + claim_ids(e, "P749")}
            nxt.update(result[q]["owners"])
        print(f"level {depth}: {len(ents)} organisations")
        level = nxt
    classes = {c for v in result.values() for c in v["class_qids"]}
    labels = {q: e.get("labels", {}).get("en", {}).get("value") for q, e in entities(classes).items()}
    for v in result.values():
        v["classes"] = [labels.get(c) or c for c in v.pop("class_qids")]
    folder = RAW / "wikidata_owners"
    folder.mkdir(parents=True, exist_ok=True)
    save("wikidata_owners", result, {"url": API, "owners": len(result),
                                     "licence": "Wikidata: CC0 (public domain)"})


if __name__ == "__main__":
    main()
