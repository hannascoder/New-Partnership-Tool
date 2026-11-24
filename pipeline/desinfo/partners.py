"""Disinformation monitor <-> Partner Finder: per country the local voices that are already in the Partner Finder data.

Input : site/data/outlets-*.json, site/data/ngos-1.json, site/data/config.json (built by the 2-monthly pipeline)
Output: site/data/desinfo/partners.json  {ISO2: {"iso3", "fc": {"n", "top": [...]}, "cm": ..., "nw": ..., "ngo": ...}}
Groups: fc = fact-checkers, cm = community media (e.g. community radio), nw = news outlets / agencies / public broadcasters
(not state-controlled, pure sports / music / children's / religious channels left out), ngo = organisations and NGOs.
Sorted by the Partner Finder's own prominence score. Only organisations, no persons. Nothing is invented: a country
without entries simply has none in the Partner Finder yet.
"""
import csv
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "site" / "data"
TOP = yaml.safe_load(open(ROOT / "config" / "desinfo.yaml", encoding="utf-8"))["partners"]["top_n"]


def main():
    cfg = json.load(open(DATA / "config.json", encoding="utf-8"))
    codes = cfg["codes"]
    t_of = {name: i for i, name in enumerate(codes["o"])}
    ow_state = codes["ow"].index("state_controlled")
    iso3_to_2 = {}
    with open(ROOT / "config" / "countries.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            iso3_to_2[r["iso3"]] = r["iso2"]
    groups = {}                          # iso2 -> group -> [entries]
    sizes = {}                           # Partner Finder topic / sub-topic -> number of media worldwide (for broad/narrow default)

    def put(iso3, group, entry):
        iso2 = iso3_to_2.get(iso3)
        if iso2:
            groups.setdefault(iso2, {"iso3": iso3}).setdefault(group, []).append(entry)

    for name in cfg["outlet_files"]:
        for o in json.load(open(DATA / name, encoding="utf-8")):
            if o.get("nn"):                          # pure sports / music / children's / religious channel
                continue
            seen = set()
            for e in o.get("tp") or []:
                seen.add(e[0])
                for sub in (e[3] if len(e) > 3 and isinstance(e[3], list) else []):
                    seen.add(e[0] + "/" + sub)
            for k in seen:
                sizes[k] = sizes.get(k, 0) + 1
            t = (o.get("o") or [None])[0]
            if t == t_of["fact_checker"]:
                g = "fc"
            elif t == t_of["community_media"]:
                g = "cm"
            elif t in (t_of["news_outlet"], t_of["news_agency"], t_of["public_service_broadcaster"]):
                if (o.get("ow") or [None])[0] == ow_state:
                    continue
                g = "nw"
            else:
                continue
            put(o["c"], g, [o["p"], o["n"], o.get("w", ""), o["i"], (o.get("l") or [])[:2]])
    for name in cfg["ngo_files"]:
        for o in json.load(open(DATA / name, encoding="utf-8")):
            put(o["c"], "ngo", [o["p"], o["n"], o.get("w", ""), o["i"], []])

    # UNDP iVerify country sites (config/iverify_sites.yaml): shown as links, whether or not the tool may read them
    iv = {}
    for x in yaml.safe_load(open(ROOT / "config" / "iverify_sites.yaml", encoding="utf-8")).get("sites", []):
        iv.setdefault(x["country"], []).append({"n": x["name"], "w": x["site"], "i": "", "l": []})
    out = {}
    for iso2, g in sorted(groups.items()):
        rec = {"iso3": g["iso3"]}
        for k in ("fc", "cm", "nw", "ngo"):
            rows = sorted(g.get(k, []), key=lambda e: (-e[0], e[1].lower()))
            rec[k] = {"n": len(rows), "top": [{"n": e[1], "w": e[2], "i": e[3], "l": e[4]} for e in rows[:TOP]]}
        if iso2 in iv:
            rec["iv"] = {"n": len(iv[iso2]), "top": iv[iso2]}
        out[iso2] = rec
    (DATA / "desinfo").mkdir(exist_ok=True)
    json.dump(out, open(DATA / "desinfo" / "partners.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    json.dump(sizes, open(DATA / "desinfo" / "partner_topic_sizes.json", "w", encoding="utf-8"), sort_keys=True, separators=(",", ":"))
    tot = {k: sum(r[k]["n"] for r in out.values()) for k in ("fc", "cm", "nw", "ngo")}
    print(f"{len(out)} countries; entries in the Partner Finder: {tot}")


if __name__ == "__main__":
    main()
