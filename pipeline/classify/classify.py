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


def iptv_owner_names(o):
    names = []
    for m in o["raw"].values():
        names += m.get("raw", {}).get("owners", []) or []
    return names


def owner_index(owners, outlets_known):
    """name of an organisation -> (classes, label) from Wikidata owners, and
    name -> ownership of outlets/companies already classified, for matching the
    owner NAMES that iptv-org gives (step 4b-a)."""
    import sys
    sys.path.insert(0, str(ROOT / "pipeline" / "merge"))
    from merge import clean_name
    idx = {}
    for q, v in owners.items():
        if v.get("label"):
            idx.setdefault(clean_name(v["label"]), (set(v["classes"]), v["label"]))
    return idx, clean_name


def ownership(o, rules, owners, rsf, org, owner_idx=None):
    info = owner_info(o, owners)
    if owner_idx:  # iptv-org owner names matched to Wikidata organisations
        idx, clean = owner_idx
        for n in iptv_owner_names(o):
            hit = idx.get(clean(n))
            if hit:
                info.append((f"{hit[1]} (named by iptv-org)", hit[0], 1))
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


SCOPE_ORDER = ["international", "regional", "national", "local"]


class Reach:
    """Country groups (config/audience_groups.yaml + iptv-org regions) and the
    international broadcasters list."""

    def __init__(self):
        groups = yaml.safe_load(open(ROOT / "config" / "audience_groups.yaml", encoding="utf-8"))["groups"]
        countries = {r["iso2"]: r["iso3"] for r in csv.DictReader(open(ROOT / "config" / "countries.csv", encoding="utf-8"))}
        self.all = set(countries.values())
        self.iptv = {}
        regions = ROOT / "raw" / "iptv_org" / "regions.csv"
        if regions.exists():
            for r in csv.DictReader(open(regions, encoding="utf-8")):
                self.iptv[r["code"]] = {countries[c] for c in r["countries"].split(";") if c in countries}
        self.groups = {}
        for name, g in groups.items():
            if g.get("all"):
                self.groups[name] = set(self.all)
            elif g.get("iptv"):
                self.groups[name] = self.iptv.get(g["iptv"], set())
            else:
                self.groups[name] = {c for c in g["countries"] if c in self.all}
        self.iso2 = countries
        cfg = yaml.safe_load(open(ROOT / "config" / "international_broadcasters.yaml", encoding="utf-8"))
        self.broadcasters = cfg["broadcasters"]

    def expand(self, items):
        out = set()
        for it in items:
            out |= self.groups.get(it, {it} if it in self.all else set())
        return out


def iptv_areas(o):
    areas = set()
    for m in o["raw"].values():
        areas.update(m.get("raw", {}).get("broadcast_area", []))
    return areas


def mc_collections(o):
    cols = []
    for m in o["raw"].values():
        cols += m.get("raw", {}).get("collections", [])
    return cols


def scope_and_reach(o, rules, reach, intl, org):
    """Returns (scope value-dict, {country: basis})."""
    home = o["country"]
    audience = {home: "home_country"} if home else {}
    evidence = []  # (scope, method, source)
    # 1. international broadcasters list (language services)
    for entry, service, own_outlet in sorted(intl, key=lambda x: x[1] is None):  # services first
        if service:
            for c in reach.expand(service["reaches"]):
                audience.setdefault(c, "language_service:" + service["name"])
        if not service:
            for c in reach.expand(entry.get("reaches", [])):
                audience.setdefault(c, "manual")
        label = (service or {}).get("name") or entry["match"][0]
        evidence.append(("international", "override", f"list of international broadcasters ({label})"))
    # 2. iptv-org broadcast areas
    areas = iptv_areas(o)
    if areas:
        regions = {a[2:] for a in areas if a.startswith("r/")}
        cs = {reach.iso2.get(a[2:]) for a in areas if a.startswith("c/")} - {None}
        for r in regions:
            cs |= reach.iptv.get(r, set())
        if "WW" in regions or len(regions) >= 2:
            evidence.append(("international", "source_field", "iptv-org broadcast area " + ", ".join(sorted(regions))))
        elif regions or len(cs - {home}) >= 1 and len(cs) >= 2:
            evidence.append(("regional", "source_field", "iptv-org broadcast area " + ", ".join(sorted(regions) or sorted(cs))))
        elif cs == {home}:
            evidence.append(("national", "source_field", "iptv-org broadcast area: whole country"))
        elif any(a.startswith(("s/", "ct/")) for a in areas):
            evidence.append(("local", "source_field", "iptv-org broadcast area: city / region"))
        if len(cs) <= 60:  # worldwide feeds do not list every country as "reached"
            for c in cs:
                audience.setdefault(c, "broadcast_area")
    # 3. Media Cloud collections
    for col in mc_collections(o):
        if col.endswith(" - National"):
            evidence.append(("national", "source_field", f"Media Cloud collection \"{col}\""))
        elif col.endswith(" - State & Local"):
            evidence.append(("local", "source_field", f"Media Cloud collection \"{col}\""))
    # 4. Wikidata classes, organisation type
    classes = wd_classes(o)
    for sc, cl in rules["wikidata_classes"].items():
        hit = classes & set(cl)
        if hit:
            evidence.append((sc, "source_field", "Wikidata: " + sorted(hit)[0]))
    for sc, types in rules.get("org_types", {}).items():
        if org in types:
            evidence.append((sc, "rule", "organisation type " + org.replace("_", " ")))
    if not evidence:
        return val("unknown", "default", "no scope information in the sources"), audience
    methods = ["override", "source_field", "membership", "rule"]
    evidence.sort(key=lambda e: (SCOPE_ORDER.index(e[0]), methods.index(e[1])))
    best = evidence[0]
    return val(best[0], best[1], best[2]), audience


def match_international(outlets, reach):
    """outlet id -> [(entry, service or None)] from config/international_broadcasters.yaml"""
    import sys
    sys.path.insert(0, str(ROOT / "pipeline" / "merge"))
    from merge import clean_name
    by_name = {}
    for o in outlets:
        for n in [o["name"]] + o["alt_names"]:
            by_name.setdefault(clean_name(n), []).append(o)
    found, missing = {}, []
    for e in reach.broadcasters:
        hit = False
        for n in e["match"]:
            cands = [o for o in by_name.get(clean_name(n), []) if not e.get("country") or o["country"] == e["country"]]
            for o in cands[:1]:
                found.setdefault(o["id"], []).append((e, None, False))
                for s in e.get("services", []):
                    found[o["id"]].append((e, s, False))
                hit = True
        for s in e.get("services", []):  # a separate outlet for the language service: only its own reach
            for o in by_name.get(clean_name(s["name"]), [])[:1]:
                found.setdefault(o["id"], []).append((e, s, True))
        if not hit:
            missing.append(e["match"][0])
    return found, missing


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
    reach = Reach()
    oidx = owner_index(owners, None)
    intl, intl_missing = match_international(outlets, reach)
    for o in outlets:
        cat = {"org_type": org_type(o, rules["org_type"], media_classes)}
        cat["ownership"] = ownership(o, rules["ownership"], owners, rsf, cat["org_type"]["value"], oidx)
        ov = overrides.get(o["id"], {}).get("ownership")
        if ov:
            cat["ownership"] = val(ov["value"], "override", ov.get("note") or "hand correction")
        if cat["ownership"]["value"] == "state_controlled" and cat["org_type"]["value"] == "public_service_broadcaster":
            # state-controlled broadcasters are not public service (decision 3): plain broadcaster
            cat["org_type"] = val("news_outlet", "rule", "public broadcaster that is state-controlled (" + cat["ownership"]["source"] + ")")
        also = []
        if rules.get("also_news_outlet_if_private_psb") and cat["org_type"]["value"] == "public_service_broadcaster" \
                and cat["ownership"]["value"] == "private":
            also.append("news_outlet")
        cat["org_type_also"] = also
        cat["scope"], audience = scope_and_reach(o, rules["scope"], reach, intl.get(o["id"], []), cat["org_type"]["value"])
        cat["audience"] = audience
        extra_langs = [l for e, s, _ in intl.get(o["id"], []) if s for l in s["languages"]]
        cat["service_languages"] = sorted(set(extra_langs) - set(o["languages"]))
        cat["services"] = sorted({s["name"] for e, s, _ in intl.get(o["id"], []) if s})
        for field, row in overrides.get(o["id"], {}).items():
            if field in cat:
                cat[field] = val(row["value"], "override", row.get("note") or "hand correction")
        o["cat"] = cat
    json.dump(outlets, open(ROOT / "work" / "classified.json", "w", encoding="utf-8"), ensure_ascii=False)
    report(outlets, intl_missing)


def report(outlets, intl_missing=()):
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
    lines += ["", "## 4c Scope and reach", "", "| Scope | Outlets | Main sources |", "|---|---|---|"]
    for v in SCOPE_ORDER + ["unknown"]:
        rows = [o for o in outlets if o["cat"]["scope"]["value"] == v]
        src = Counter(re.sub(r"\".*\"|\(.*\)|broadcast area .*", "", o["cat"]["scope"]["source"]).strip() for o in rows).most_common(4)
        lines.append(f"| {v} | {len(rows)} | " + "; ".join(f"{k} {n}" for k, n in src) + " |")
    multi = [o for o in outlets if len(o["cat"]["audience"]) > 1]
    lines.append(f"\nOutlets that reach more than their home country: {len(multi)}")
    lines.append("International broadcasters not found in the data: " + (", ".join(intl_missing) or "none"))
    (ROOT / "reports" / "classification.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
