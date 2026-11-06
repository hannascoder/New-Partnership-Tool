"""Step 4: gives every outlet its categories, following config/rules.yaml.

Input:  work/outlets.json (step 3), work/networks.json, overrides.csv
Output: work/classified.json (outlets + categories), reports/classification.md

Every value is stored as {"value": ..., "method": ..., "source": ...}
(briefing K3/K4). Methods, strongest first: override, source_field,
membership, website_check, keyword, default.
Done so far: 4a organisation type.
"""
import csv
import json
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
NET_LABEL = {"efcsn_signatories": "EFCSN", "ifcn_signatories": "IFCN", "fact_checking_sites": "Wikipedia list of fact-checking websites",
             "news_agencies": "Wikipedia list of news agencies", "ebu_members": "EBU membership", "asbu_members": "ASBU membership",
             "abu_members": "ABU membership", "cbu_members": "CBU membership", "sdg_media_compact": "SDG Media Compact",
             "state_media": "Wikipedia list of state media"}


def val(value, method, source):
    return {"value": value, "method": method, "source": source}


def wd_classes(o):
    out = set()
    for m in o["raw"].values():
        out.update(m.get("raw", {}).get("classes", []))
    return out


def rb_tags(o):
    out = set()
    for m in o["raw"].values():
        out.update(m.get("raw", {}).get("tags", []))
    return out


def org_type(o, rules, media_classes):
    classes = wd_classes(o)
    is_media = bool(classes & (media_classes - {"fact-checking organisation"})) or any(s in o["sources"] for s in ("media_cloud", "iptv_org", "radio_browser"))
    for r in rules:
        t = r["type"]
        hit = classes & set(r.get("wikidata_classes", []))
        if hit and not classes & set(r.get("unless_wikidata_classes", [])):
            return val(t, "source_field", "Wikidata: " + sorted(hit)[0])
        hit = classes & set(r.get("wikidata_classes_if_no_media_class", []))
        if hit and not is_media:
            return val(t, "source_field", "Wikidata: " + sorted(hit)[0])
        nets = [n for n in r.get("networks_full_members", [])
                if (o.get("network_membership") or {}).get(n) in ("full members", "additional full members")]
        if nets:
            return val(t, "membership", NET_LABEL.get(nets[0], nets[0]) + " (full member)")
        nets = [n for n in r.get("networks_if_no_media_class", []) if n in o["networks"]]
        if nets and not is_media:
            return val(t, "membership", NET_LABEL.get(nets[0], nets[0]))
        tags = rb_tags(o) & set(r.get("radio_browser_tags_with_second_source", []))
        if tags and len(o["sources"]) >= 2:
            return val(t, "source_field", f"Radio Browser tag \"{sorted(tags)[0]}\" + second source")
        if r.get("default"):
            return val(t, "default", "no evidence for another type")
    return None


def load_overrides():
    out = {}
    path = ROOT / "overrides.csv"
    for row in csv.DictReader(open(path, encoding="utf-8")):
        if row.get("outlet_id") and row.get("field"):
            out.setdefault(row["outlet_id"], {})[row["field"]] = row
    return out


def main():
    rules = yaml.safe_load(open(ROOT / "config" / "rules.yaml", encoding="utf-8"))
    media_classes = set(rules["media_classes"])
    outlets = json.load(open(ROOT / "work" / "outlets.json", encoding="utf-8"))
    overrides = load_overrides()
    for o in outlets:
        cat = {"org_type": org_type(o, rules["org_type"], media_classes)}
        for field, row in overrides.get(o["id"], {}).items():
            if field in cat:
                cat[field] = val(row["value"], "override", row.get("note") or "hand correction")
        o["cat"] = cat
    json.dump(outlets, open(ROOT / "work" / "classified.json", "w", encoding="utf-8"), ensure_ascii=False)
    report(outlets)


def report(outlets):
    lines = ["# Step 4: classification", "", "## 4a Organisation type", "",
             "| Type | Outlets | of which by membership | by Wikidata class | by Radio Browser tag | default |", "|---|---|---|---|---|---|"]
    by = Counter((o["cat"]["org_type"]["value"], o["cat"]["org_type"]["method"], o["cat"]["org_type"]["source"].startswith("Radio Browser")) for o in outlets)
    for t in ["fact_checker", "news_agency", "public_service_broadcaster", "community_media", "news_outlet"]:
        total = sum(n for (tt, _, _), n in by.items() if tt == t)
        mem = sum(n for (tt, m, _), n in by.items() if tt == t and m == "membership")
        rb = sum(n for (tt, m, r), n in by.items() if tt == t and r)
        wd = sum(n for (tt, m, r), n in by.items() if tt == t and m == "source_field" and not r)
        de = sum(n for (tt, m, _), n in by.items() if tt == t and m == "default")
        lines.append(f"| {t} | {total} | {mem} | {wd} | {rb} | {de} |")
    (ROOT / "reports" / "classification.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
