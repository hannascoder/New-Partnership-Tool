"""Step 4: gives every outlet its categories, following config/rules.yaml.

Input:  work/outlets.json (step 3), work/networks.json, overrides.csv
Output: work/classified.json (outlets + categories), reports/classification.md

Every value is stored as {"value": ..., "method": ..., "source": ...}
(briefing K3/K4). Methods, strongest first: override, source_field,
membership, website_check, keyword, default.
Done so far: 4a organisation type.
"""
import csv
import gzip
import json
from collections import Counter
from pathlib import Path

import re

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


def owner_info(o, owners):
    """Owners and parents of the outlet (Wikidata), plus their owners: [(label, classes)]."""
    out, seen = [], set()
    todo = []
    for m in o["raw"].values():
        r = m.get("raw", {})
        todo += r.get("owned_by_qid", []) + r.get("parent_qid", [])
    for depth in (1, 2):
        nxt = []
        for q in todo:
            if q in seen or q not in owners:
                continue
            seen.add(q)
            out.append((owners[q]["label"] or q, set(owners[q]["classes"]), depth))
            nxt += owners[q]["owners"]
        todo = nxt
    return out


def ownership(o, rules, owners, rsf, org):
    info = owner_info(o, owners)
    classes = wd_classes(o)
    for r in rules:
        v = r["value"]
        nets = [n for n in r.get("networks", []) if n in o["networks"]]
        if nets:
            return val(v, "membership", NET_LABEL.get(nets[0], nets[0]) + " (State Media Monitor)")
        psb_exempt = v == "state_controlled" and org == "public_service_broadcaster"
        hit = classes & set(r.get("wikidata_classes", []))
        if hit and not psb_exempt:
            return val(v, "source_field", "Wikidata: " + sorted(hit)[0])
        for label, oc, depth in ([] if psb_exempt else info):
            hit = oc & set(r.get("owner_classes", []))
            if hit:
                who = "owner" if depth == 1 else "owner's owner"
                return val(v, "source_field", f"Wikidata: {who} {label} ({sorted(hit)[0]})")
        cats = r.get("public_broadcaster_in_rsf_categories")
        if cats and org == "public_service_broadcaster" and (rsf.get(o["country"]) or {}).get("category") in cats:
            x = rsf[o["country"]]
            return val(v, "rule", f"public broadcaster in a country RSF {x['year']} rates \"{x['label']}\"")
        if org in r.get("org_types", []):
            return val(v, "rule", "organisation type " + org.replace("_", " "))
        if r.get("default"):
            return val(v, "default", "no ownership information in the sources")
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
    owners_file = ROOT / "raw" / "wikidata_owners" / "data.json.gz"
    owners = json.load(gzip.open(owners_file, "rt", encoding="utf-8")) if owners_file.exists() else {}
    rsf = json.load(open(ROOT / "work" / "rsf.json", encoding="utf-8"))
    for o in outlets:
        cat = {"org_type": org_type(o, rules["org_type"], media_classes)}
        cat["ownership"] = ownership(o, rules["ownership"], owners, rsf, cat["org_type"]["value"])
        if cat["ownership"]["value"] == "state_controlled" and cat["org_type"]["value"] == "public_service_broadcaster":
            # state-controlled broadcasters are not public service (decision 3): plain broadcaster
            cat["org_type"] = val("news_outlet", "rule", "public broadcaster that is state-controlled (" + cat["ownership"]["source"] + ")")
        also = []
        if rules.get("also_news_outlet_if_private_psb") and cat["org_type"]["value"] == "public_service_broadcaster" \
                and cat["ownership"]["value"] == "private":
            also.append("news_outlet")
        cat["org_type_also"] = also
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
    lines += ["", "## 4b Ownership", "", "| Value | Outlets | Main sources |", "|---|---|---|"]
    for v in ["state_controlled", "public_service", "community_nonprofit", "private", "unknown"]:
        rows = [o for o in outlets if o["cat"]["ownership"]["value"] == v]
        src = Counter(re.sub(r"(owner's owner|owner) .*\(", r"\1 (", o["cat"]["ownership"]["source"]) for o in rows).most_common(4)
        lines.append(f"| {v} | {len(rows)} | " + "; ".join(f"{k} {n}" for k, n in src) + " |")
    lines.append(f"\nListed as public service broadcaster AND news outlet (private owner): "
                 f"{sum(1 for o in outlets if o['cat']['org_type_also'])}")
    (ROOT / "reports" / "classification.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
