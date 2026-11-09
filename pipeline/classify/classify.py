"""Step 4: gives every outlet its categories, following config/rules.yaml.

Input:  work/outlets.json (step 3), work/networks.json, overrides.csv
Output: work/classified.json (outlets + categories), reports/classification.md

Every value is stored as {"value": ..., "method": ..., "source": ...}
(briefing K3/K4). Methods, strongest first: override, source_field,
membership, website_check, keyword, default.
Done: 4a organisation type, 4b ownership, 4c scope/reach, 4d topics + UN profile.
"""
import csv
import gzip
import json
from collections import Counter
from pathlib import Path

import re
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
NET_LABEL = {"efcsn_signatories": "EFCSN", "ifcn_signatories": "IFCN", "fact_checking_sites": "Wikipedia list of fact-checking websites",
             "news_agencies": "Wikipedia list of news agencies", "ebu_members": "EBU membership", "asbu_members": "ASBU membership",
             "abu_members": "ABU membership", "cbu_members": "CBU membership", "sdg_media_compact": "SDG Media Compact",
             "state_media": "Wikipedia list of state media", "covering_climate_now": "Covering Climate Now"}


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
            for item in entry.get("reaches", []):
                basis = "worldwide" if item == "worldwide" else "manual"
                for c in reach.expand([item]):
                    if audience.get(c) == "worldwide" and basis == "manual":
                        audience[c] = basis  # a specific region beats "worldwide"
                    audience.setdefault(c, basis)
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


def far_right(o, rules, evidence, owners):
    """Reason string if the outlet counts as far-right (config/rules.yaml), else None."""
    if not evidence:
        return None
    ideos = set(rules["wikidata_ideologies"])
    qids = [m.split(":", 1)[1] for m in o["members"] if m.startswith("wd:")]
    for q in qids:
        hit = ideos & set(evidence["ideology"].get(q, []))
        if hit:
            return "Wikidata political ideology: " + sorted(hit)[0]
    for m in o["raw"].values():  # owners' ideology
        for q in m.get("raw", {}).get("owned_by_qid", []) + m.get("raw", {}).get("parent_qid", []):
            hit = ideos & set(evidence["ideology"].get(q, []))
            if hit:
                return f"Wikidata political ideology of the owner {(owners.get(q) or {}).get('label') or q}: " + sorted(hit)[0]
    if rules.get("wikipedia_categories") and o.get("wikipedia"):
        for cat, titles in evidence["categories"].items():
            if o["wikipedia"] in titles:
                return "Wikipedia " + cat
    return None


# ---------------------------------------------------------------- 4d
METHOD_RANK = ["override", "source_field", "membership", "rule", "website_check", "keyword", "default"]


class Evidence:
    """Collects {value, method, source} per value; the strongest method wins."""

    def __init__(self):
        self.best = {}

    def add(self, value, method, source):
        old = self.best.get(value)
        if not old or METHOD_RANK.index(method) < METHOD_RANK.index(old["method"]):
            self.best[value] = val(value, method, source)

    def result(self, order):
        return sorted(self.best.values(), key=lambda v: (order.index(v["value"]) if v["value"] in order else 999))


def raw_values(o, key, prefix=None):
    out = set()
    for k, m in o["raw"].items():
        if prefix is None or k.startswith(prefix):
            out.update(m.get("raw", {}).get(key, []) or [])
    return out


def source_mappings(o, maps, kind, ev):
    """kind = "topics" or "un_profile": adds evidence from the per-source tables
    in config/sources/ (iptv-org categories, Radio Browser tags, Wikidata)."""
    cats = raw_values(o, "categories")
    tags = raw_values(o, "tags")
    classes = wd_classes(o)
    subjects = raw_values(o, "main_subject") | raw_values(o, "genre")
    for value, lst in (maps["iptv"].get(kind) or {}).items():
        hit = cats & set(lst)
        if hit:
            ev.add(value, "source_field", f"iptv-org category \"{sorted(hit)[0]}\"")
    for value, lst in (maps["rb"].get(kind) or {}).items():
        hit = tags & set(lst)
        if hit:
            ev.add(value, "source_field", f"Radio Browser tag \"{sorted(hit)[0]}\"")
    for value, d in (maps["wd"].get(kind) or {}).items():
        hit = classes & set(d.get("classes", []))
        if hit:
            ev.add(value, "source_field", "Wikidata: " + sorted(hit)[0])
        hit = subjects & set(d.get("subjects", []))
        if hit:
            ev.add(value, "source_field", "Wikidata subject: " + sorted(hit)[0])


def keyword_patterns(rules):
    out = []
    for topic, words in (rules.get("name_keywords") or {}).items():
        for w in words:
            out.append((topic, w, re.compile(r"(?<!\w)" + re.escape(w.casefold()) + r"(?!\w)")))
    return out


def apply_list_overrides(ev, ov, field, label):
    """overrides.csv: <id>,<field>_add,climate;health,<why>  /  <id>,<field>_remove,general_news,<why>"""
    add = (ov.get(field + "_add") or {})
    for v in [x.strip() for x in (add.get("value") or "").split(";") if x.strip()]:
        ev.best[v] = val(v, "override", add.get("note") or "hand correction")
    rem = (ov.get(field + "_remove") or {})
    for v in [x.strip() for x in (rem.get("value") or "").split(";") if x.strip()]:
        ev.best.pop(v, None)


def topics(o, cat, rules, maps, kw, order, ov, texts=None):
    ev = Evidence()
    source_mappings(o, maps, "topics", ev)
    for topic, nets in (rules.get("networks") or {}).items():
        hit = [n for n in nets if n in o["networks"]]
        if hit:
            ev.add(topic, "membership", NET_LABEL.get(hit[0], hit[0]))
    types = {cat["org_type"]["value"]} | set(cat.get("org_type_also") or [])
    for topic, ts in (rules.get("org_types") or {}).items():
        if types & set(ts):
            ev.add(topic, "rule", "organisation type " + sorted(types & set(ts))[0].replace("_", " "))
    for topic, scs in (rules.get("scopes") or {}).items():
        if cat["scope"]["value"] in scs:
            ev.add(topic, "rule", "scope " + cat["scope"]["value"])
    # every value so far comes from a source / network / rule: strength FOCUS
    for v in ev.best.values():
        v["strength"] = 1
    # keyword lists (config/topic_keywords.yaml) on name, descriptions, website
    name = o["name"] or ""
    if name.count(",") > rules.get("name_keywords_max_commas", 99):
        name = ""  # a tagline listing sections, not a name
    texts = dict(texts or {})
    base = texts.pop("base_url", None)
    hits = kw.match(name=name, **texts)
    for topic, h in hits.items():
        old = ev.best.get(topic)
        method = "website_check" if h["why"].startswith("website") else "keyword"
        if not old or h["s"] < old.get("strength", 9):
            ev.best[topic] = {**val(topic, method, h["why"]), "strength": h["s"]}
        if h["subs"]:
            ev.best[topic]["subs"] = sorted(h["subs"])
        if h.get("url") and base and ev.best[topic].get("strength") == 2:
            import urllib.parse
            ev.best[topic]["url"] = urllib.parse.urljoin(base, h["url"])
    apply_list_overrides(ev, ov, "topics", "topic")
    for v in ev.best.values():
        v.setdefault("strength", 1)
    if not ev.best:
        ev.add("general_news", "default", "no topic in the sources: general news")
        ev.best["general_news"]["strength"] = 3
    return ev.result(order)


def add_website_channels_language(o, w, rules, iso1):
    """Podcast / newsletter from the website menu or feeds; page language if no source has one."""
    from topic_text import norm
    words = {ch: {norm(x) for x in lst} for ch, lst in (rules.get("website_channels") or {}).items()}
    texts = [norm(t) for t, _ in (w.get("nav") or [])] + [norm(f) for f in (w.get("feeds") or [])]
    for ch, ws in words.items():
        if ch in o["channels"]:
            continue
        if any(t in ws or any((" " + x + " ") in (" " + t + " ") for x in ws) for t in texts):
            o["channels"].append(ch)
            o.setdefault("channel_source", {})[ch] = "website"
    if rules.get("website_language") and not o["languages"] and w.get("lang"):
        code = iso1.get(w["lang"].split("-")[0].split("_")[0].lower())
        if code:
            o["languages"] = [code]
            o["language_source"] = "website"


def partner_content(w, words):
    """Reason text if the website shows the outlet takes content from others, else None."""
    if not w or w.get("status") != "ok" or not words:
        return None
    from topic_text import norm
    for text, url in w.get("extra") or []:
        hay = " " + norm(text) + " " + norm(url) + " "
        for x in words:
            if " " + x + " " in hay:
                return f'website link "{text or url}"'
    about = " " + norm(w.get("about") or "") + " "
    for x in words:
        if " " + x + " " in about:
            return f'website About page mentions "{x}"'
    return None


ORG_MAIL = re.compile(r"^(info|contact|contacto|contato|kontakt|redac|redaction|redaccion|redacao|newsroom|news|noticias|"
                      r"editor|editors|editorial|desk|hello|hola|office|admin|press|presse|prensa|imprensa|mail|"
                      r"communication|comunicacion|media|secretariat|reception|support|webmaster|tips|letters|studio|"
                      r"programs|programmes|radio|tv|online)", re.I)


def outlet_texts(o, wd_texts, web):
    """texts for the keyword lists: Wikidata/Wikipedia (raw/texts) + website check"""
    desc, abouts, menu, heads = [], [], [], []
    for q in [m[3:] for m in o["members"] if m.startswith("wd:")]:
        t = wd_texts.get(q) or {}
        desc += list((t.get("desc") or {}).values())
        if t.get("intro"):
            abouts.append(("Wikipedia", t["intro"]))
    w = web.get(o["id"]) or {}
    if w.get("status") == "ok":
        desc += [x for x in (w.get("desc"), w.get("title")) if x]
        if w.get("about"):
            abouts.append(("website About page", w["about"]))
        menu = [tuple(x) for x in w.get("nav") or []]
        heads = (w.get("heads") or []) + ([w["home_text"]] if w.get("home_text") else [])
    return {"descriptions": desc, "abouts": abouts, "menu": menu, "headlines": heads,
            "base_url": w.get("final_url") if w.get("status") == "ok" else None}


def audience_groups(o, cat, rules, maps, kw, order, ov, official, buttons, lang_names, topic_ids, aud_matcher=None, texts=None):
    """Target audience (owner's idea, 09.11.2026): who the outlet is made for."""
    ev = Evidence()
    source_mappings(o, maps, "audience", ev)
    types = {cat["org_type"]["value"]} | set(cat.get("org_type_also") or [])
    for aud, ts in (rules.get("org_types") or {}).items():
        if types & set(ts):
            ev.add(aud, "rule", "organisation type " + sorted(types & set(ts))[0].replace("_", " "))
    for aud, ts in (rules.get("topics") or {}).items():
        hit = topic_ids & set(ts)
        if hit:
            ev.add(aud, "rule", "topic " + sorted(hit)[0].replace("_", " "))
    off = official.get(o["country"])
    if rules.get("minority_language") and off:
        minority = [l for l in o["languages"] if l not in buttons and l not in off]
        if minority:
            names = ", ".join(lang_names.get(l, l) for l in minority[:3])
            ev.add(rules["minority_language"], "rule", f"in {names}: not an official language of the country")
    name = (o["name"] or "").casefold()
    if name.count(",") <= 1:
        for aud, word, rx in kw:
            if aud not in ev.best and rx.search(name):
                ev.add(aud, "keyword", f"name contains \"{word}\"")
    if aud_matcher and texts:  # config/audience_keywords.yaml on name, descriptions, About texts
        hits = aud_matcher.match(name=o["name"] or "", descriptions=texts.get("descriptions") or [],
                                 abouts=texts.get("abouts") or [])
        for aud, h in hits.items():
            if aud not in ev.best:
                ev.add(aud, "website_check" if "website" in h["why"] else "keyword", h["why"])
    apply_list_overrides(ev, ov, "audience", "target audience")
    return ev.result(order)


def un_profile(o, cat, rules, maps, order, ov, official, buttons, lang_names, topic_ids):
    ev = Evidence()
    source_mappings(o, maps, "un_profile", ev)
    for prof, nets in (rules.get("networks") or {}).items():
        hit = [n for n in nets if n in o["networks"]]
        if hit:
            ev.add(prof, "membership", NET_LABEL.get(hit[0], hit[0]))
    types = {cat["org_type"]["value"]} | set(cat.get("org_type_also") or [])
    for prof, ts in (rules.get("org_types") or {}).items():
        if types & set(ts):
            ev.add(prof, "rule", "organisation type " + sorted(types & set(ts))[0].replace("_", " "))
    for prof, ts in (rules.get("topics") or {}).items():
        hit = topic_ids & set(ts)
        if hit:
            ev.add(prof, "rule", "topic " + sorted(hit)[0].replace("_", " "))
    off = official.get(o["country"])
    if rules.get("minority_language") and off:
        minority = [l for l in o["languages"] if l not in buttons and l not in off]
        if minority:
            names = ", ".join(lang_names.get(l, l) for l in minority[:3])
            ev.add(rules["minority_language"], "rule", f"in {names}: not an official language of the country")
    langs = set(o["languages"]) | set(cat.get("service_languages") or [])
    if rules.get("multilingual_min_languages") and len(langs) >= rules["multilingual_min_languages"]:
        ev.add("multilingual", "rule", f"{len(langs)} languages")
    apply_list_overrides(ev, ov, "un_profile", "UN profile")
    return ev.result(order)


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
    fr_file = ROOT / "raw" / "far_right" / "data.json.gz"
    fr_evidence = json.load(gzip.open(fr_file, "rt", encoding="utf-8")) if fr_file.exists() else None
    reach = Reach()
    oidx = owner_index(owners, None)
    intl, intl_missing = match_international(outlets, reach)
    cats_cfg = yaml.safe_load(open(ROOT / "config" / "categories.yaml", encoding="utf-8"))
    topic_order = [t["id"] for t in cats_cfg["topics"]]
    un_order = [u["id"] for u in cats_cfg["un_profile"]]
    aud_order = [a["id"] for a in cats_cfg["audience"]]
    aud_kw = keyword_patterns(rules["audience"])
    src = ROOT / "config" / "sources"
    maps = {k: yaml.safe_load(open(src / f, encoding="utf-8")) for k, f in
            (("iptv", "iptv_org.yaml"), ("rb", "radio_browser.yaml"), ("wd", "wikidata.yaml"))}
    sys.path.insert(0, str(ROOT / "pipeline" / "classify"))
    from topic_text import Matcher
    kw = Matcher(auto_kind="topic")
    aud_matcher = Matcher(ROOT / "config" / "audience_keywords.yaml", auto_kind="audience")
    tf = ROOT / "raw" / "texts" / "data.json.gz"
    wd_texts = json.load(gzip.open(tf, "rt", encoding="utf-8")) if tf.exists() else {}
    web = {}
    for f in sorted((ROOT / "raw" / "website_check").glob("*.json.gz")):
        web.update(json.load(gzip.open(f, "rt", encoding="utf-8")))
    print(f"texts: {len(wd_texts)} Wikidata items, {len(web)} websites checked")
    official = {r["iso3"]: set(filter(None, r["official_languages"].split(";")))
                for r in csv.DictReader(open(ROOT / "config" / "official_languages.csv", encoding="utf-8"))}
    lang_rows = list(csv.DictReader(open(ROOT / "config" / "languages.csv", encoding="utf-8")))
    buttons = {r["code"] for r in lang_rows if r["button"]}
    lang_names = {r["code"]: r["name"] for r in lang_rows}
    iso1 = {r["iso639_1"]: r["code"] for r in lang_rows if r["iso639_1"]}
    from topic_text import norm
    partner_words = [norm(x) for x in rules.get("open_to_partner_content") or []]
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
        fr = far_right(o, rules["exclude_far_right"], fr_evidence, owners)
        if fr and (overrides.get(o["id"], {}).get("far_right") or {}).get("value") == "no":
            fr = None
        cat["excluded"] = fr
        cat["scope"], audience = scope_and_reach(o, rules["scope"], reach, intl.get(o["id"], []), cat["org_type"]["value"])
        cat["audience"] = audience
        extra_langs = [l for e, s, _ in intl.get(o["id"], []) if s for l in s["languages"]]
        cat["service_languages"] = sorted(set(extra_langs) - set(o["languages"]))
        cat["services"] = sorted({s["name"] for e, s, _ in intl.get(o["id"], []) if s})
        ov = overrides.get(o["id"], {})
        txt = outlet_texts(o, wd_texts, web)
        cat["topics"] = topics(o, cat, rules["topics"], maps, kw, topic_order, ov, txt)
        w = web.get(o["id"]) or {}
        if w.get("status") == "ok":  # contacts and social links from the website (owner's to-do 6)
            mails = [e for e in w.get("emails") or [] if ORG_MAIL.match(e)]
            if mails and not o.get("email"):
                o["email"] = mails[0]
                o["email_source"] = "website"
            for k, u in (w.get("social") or {}).items():
                o.setdefault("social_urls", {}).setdefault(k, u)
            if w.get("social") and "social_media" not in o["channels"]:
                o["channels"].append("social_media")
        cat["website_status"] = w.get("status")
        if w.get("contact_url"):
            o["contact_page"] = w["contact_url"]
        if w.get("last_post"):
            o["last_post"] = w["last_post"]
        if w.get("status") == "ok":
            add_website_channels_language(o, w, rules, iso1)
        cat["un_profile"] = un_profile(o, cat, rules["un_profile"], maps, un_order, ov, official, buttons, lang_names,
                                       {t["value"] for t in cat["topics"]})
        hint = partner_content(w, partner_words)
        if hint and not any(u["value"] == "open_to_partner_content" for u in cat["un_profile"]):
            cat["un_profile"].append(val("open_to_partner_content", "website_check", hint))
            cat["un_profile"].sort(key=lambda v: un_order.index(v["value"]) if v["value"] in un_order else 999)
        cat["audience_groups"] = audience_groups(o, cat, rules["audience"], maps, aud_kw, aud_order, ov, official, buttons,
                                          lang_names, {t["value"] for t in cat["topics"]}, aud_matcher, txt)
        for field, row in overrides.get(o["id"], {}).items():
            if field in cat and isinstance(cat[field], dict):
                cat[field] = val(row["value"], "override", row.get("note") or "hand correction")
        o["cat"] = cat
    json.dump(outlets, open(ROOT / "work" / "classified.json", "w", encoding="utf-8"), ensure_ascii=False)
    report(outlets, intl_missing)
    report_4d(outlets, cats_cfg)
    ex = sorted((o for o in outlets if o["cat"].get("excluded")), key=lambda o: (o["country"] or "", o["name"] or ""))
    lines = ["# Excluded as far-right (not shown on the website)", "",
             f"{len(ex)} outlets. Reason = the open evidence used (config/rules.yaml, exclude_far_right).",
             "To bring one back: add a line to overrides.csv: `<id>,far_right,no,<why>`.", "",
             "| Id | Name | Country | Reason |", "|---|---|---|---|"]
    lines += [f"| {o['id']} | {o['name']} | {o['country']} | {o['cat']['excluded']} |" for o in ex]
    (ROOT / "reports" / "excluded_far_right.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"excluded as far-right: {len(ex)}")


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


def report_4d(outlets, cats_cfg):
    shown = [o for o in outlets if not o["cat"].get("excluded")]
    n = len(shown)
    by_strength = Counter(v.get("strength") for o in shown for v in o["cat"]["topics"] if v["method"] != "default")
    lines = ["# Step 4d: topics, target audience and UN profile", "",
             f"Topic matches by strength: main focus {by_strength[1]:,} · own section {by_strength[2]:,} · covers it {by_strength[3]:,}", "",
             f"{n:,} outlets shown on the website. An outlet can have several topics and profiles.",
             "Topics and UN profiles never hide an outlet; they only change the order (unless the user",
             "switches on \"Only show topic matches\").", "",
             "Methods: **source** = the source's own category/tag/subject (config/sources/*.yaml), "
             "**network** = member of a list, **rule** = from organisation type / scope / language, "
             "**name** = a clear word in the name (config/rules.yaml), **hand** = overrides.csv.", "",
             "## Topics", "", "| Topic | Outlets | source | network | rule | name | hand | Most frequent reasons |",
             "|---|---|---|---|---|---|---|---|"]
    for t in cats_cfg["topics"]:
        vs = [v for o in shown for v in o["cat"]["topics"] if v["value"] == t["id"]]
        by = Counter(v["method"] for v in vs)
        why = Counter(re.sub(r"\d+ languages", "N languages", v["source"]) for v in vs).most_common(3)
        label = t["label"] + (f" (SDG {t['sdg']})" if t.get("sdg") else "")
        lines.append(f"| {label} | {len(vs):,} | {by['source_field']:,} | {by['membership']:,} | {by['rule']:,} | "
                     f"{by['keyword']:,} | {by['override']:,} | " + "; ".join(f"{k} ({c:,})" for k, c in why) + " |")
    only_default = sum(1 for o in shown if [v["method"] for v in o["cat"]["topics"]] == ["default"])
    lines += ["", f"Outlets with no topic in any source (shown as \"General news\" by default): {only_default:,} "
              f"({100 * only_default / max(n, 1):.0f} %)", "",
              "## UN profile", "", "| Profile | Outlets | source | network | rule | hand | Most frequent reasons |",
              "|---|---|---|---|---|---|---|"]
    for u in cats_cfg["un_profile"]:
        vs = [v for o in shown for v in o["cat"]["un_profile"] if v["value"] == u["id"]]
        by = Counter(v["method"] for v in vs)
        why = Counter(re.sub(r"in .*: not an official", "in X: not an official", re.sub(r"\d+ languages", "N languages", v["source"]))
                      for v in vs).most_common(3)
        lines.append(f"| {u['label']} | {len(vs):,} | {by['source_field']:,} | {by['membership']:,} | {by['rule']:,} | "
                     f"{by['override']:,} | " + ("; ".join(f"{k} ({c:,})" for k, c in why) or "no open source yet") + " |")
    lines.append(f"\nOutlets with at least one UN profile: {sum(1 for o in shown if o['cat']['un_profile']):,}")
    lines += ["", "## Target audience", "", "| Audience | Outlets | source | rule | name | hand | Most frequent reasons |",
              "|---|---|---|---|---|---|---|"]
    for a in cats_cfg["audience"]:
        vs = [v for o in shown for v in o["cat"]["audience_groups"] if v["value"] == a["id"]]
        by = Counter(v["method"] for v in vs)
        why = Counter(re.sub(r"in .*: not an official", "in X: not an official", v["source"]) for v in vs).most_common(3)
        lines.append(f"| {a['label']} | {len(vs):,} | {by['source_field']:,} | {by['rule']:,} | {by['keyword']:,} | "
                     f"{by['override']:,} | " + ("; ".join(f"{k} ({c:,})" for k, c in why) or "no open source yet") + " |")
    lines.append(f"\nOutlets with at least one target audience: {sum(1 for o in shown if o['cat']['audience_groups']):,}")
    (ROOT / "reports" / "topics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    # sample for checking by hand: per topic up to 6 random outlets, with strength and reason
    import random
    rnd = random.Random(42)
    names = {1: "main focus", 2: "own section", 3: "covers it"}
    sm = ["# Topics: random sample to check by hand", "",
          "Per topic up to 6 random outlets (2 per strength where possible). Wrong? Tell Claude the id,",
          "or add a line to overrides.csv: `<id>,topics_remove,<topic id>,<why>`.", ""]
    for t in cats_cfg["topics"]:
        if t["id"] == "general_news":
            continue
        rows = [(o, v) for o in shown for v in o["cat"]["topics"] if v["value"] == t["id"]]
        pick = []
        for s in (1, 2, 3):
            grp = [r for r in rows if r[1].get("strength") == s]
            pick += rnd.sample(grp, min(2, len(grp)))
        sm += [f"## {t['label']}" + (f" (SDG {t['sdg']})" if t.get("sdg") else "") + f" — {len(rows):,} outlets", "",
               "| Id | Name | Country | Strength | Reason |", "|---|---|---|---|---|"]
        sm += [f"| {o['id']} | {(o['name'] or '')[:60]} | {o['country']} | {names.get(v.get('strength'), '')} | {v['source'][:120]} |"
               for o, v in pick] or ["| | none yet | | | |"]
        sm.append("")
    (ROOT / "reports" / "topics_sample.md").write_text("\n".join(sm) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
