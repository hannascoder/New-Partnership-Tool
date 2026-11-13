"""NGOs (phase 2, owner's decisions 10.11.2026; config/ngo.yaml).

Reads the raw NGO sources, merges entries that are the same organisation, assigns the same
categories as for media (topics with strength and sub-topics, target audience, languages,
contact) plus NGO-only values (UN status, type of work) and writes work/ngos.json in the same
shape as work/classified.json, so pipeline/build/site_data.py can write the site files.

Sources (all open, no keys):
  ECOSOC iCSO   raw/ecosoc/       lists (status, type, fields of activity, DPI/DGC) + profiles
  Wikidata      raw/wikidata_ngo/ NGOs with at least one Wikipedia page
  UN Geneva     raw/ngo/un_geneva_ngo_list.html.gz
  IATI          raw/iati/         NGOs that publish their projects
Not shown: far-right NGOs (same Wikidata ideologies as for media), government-organised NGOs
(GONGOs), entries whose name shows they are not an NGO (ministry, university, company ...).
Reports: reports/ngos.md (counts, coverage), reports/ngos_excluded.md.
"""
import gzip
import html as htmllib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "normalize"))
sys.path.insert(0, str(ROOT / "pipeline" / "classify"))
from countrymatch import to_iso3  # noqa: E402
from ngos import iati, un_geneva  # noqa: E402
from sources import COUNTRIES, LANG, norm_url  # noqa: E402
from topic_text import Matcher, norm  # noqa: E402

RAW = ROOT / "raw"
CFG = yaml.safe_load(open(ROOT / "config" / "ngo.yaml", encoding="utf-8"))
FIELDS = yaml.safe_load(open(ROOT / "config" / "sources" / "ecosoc_fields.yaml", encoding="utf-8"))
RULES = yaml.safe_load(open(ROOT / "config" / "rules.yaml", encoding="utf-8"))
TODAY = str(date.today())
GENERIC_DOMAINS = {"facebook.com", "twitter.com", "x.com", "instagram.com", "linkedin.com", "youtube.com",
                   "google.com", "sites.google.com", "wordpress.com", "blogspot.com", "gmail.com", "yahoo.com",
                   "un.org", "esango.un.org", "wikipedia.org"}


def load_gz(path, default):
    p = RAW / path
    return json.load(gzip.open(p, "rt", encoding="utf-8")) if p.exists() else default


def clean_name(s):
    return re.sub(r"\s+", " ", htmllib.unescape(s or "")).strip().strip('"').strip()


def name_key(s):
    # 11.11.2026: "Article19" = "ARTICLE 19", "Caritas Internationalis (International Confederation ...)" =
    # "Caritas Internationalis": brackets at the end (abbreviation or local name) are left out
    s = re.sub(r"\s*\([^()]*\)?\s*$", "", clean_name(s)) or clean_name(s)
    k = norm(s)
    k = re.sub(r"\b(the|of|for|and|de|la|le|les|des|du|el|los|las|et|y|e|da|do|das|dos)\b", " ", k)
    return "".join(k.split()) if len(k.split()) <= 2 else " ".join(k.split())


# ------------------------------------------------------------------ ECOSOC
STATUS_ID = {"general": "ecosoc_general", "special": "ecosoc_special", "roster": "ecosoc_roster"}


def field_label(meta):
    """the field of activity a list stands for (its link label, or the page heading)"""
    lab = (meta.get("label") or "").strip()
    if lab.lower().startswith("field of activity code"):
        h = meta.get("heading") or ""
        m = re.search(r"(?:field of activity|fields of activity|area of expertise)\s*[:\-]?\s*([A-Za-z ,/()'-]{3,80})", h, re.I)
        lab = m.group(1).strip() if m else ""
    return lab


def parse_activities(t):
    """'Activities' tab of an ECOSOC profile (fetched since 12.11.2026), cells separated by "|":
    Areas of expertise & Fields of activity: | <group> | : | <field> | ... | Geographic scope: | International |
    Country of activity: | <country> | ... | Millennium Development Goals: | ... | Mission statement: | <text>"""
    cells = [c.strip() for c in (t or "").split("|")]
    out = {"fields": [], "scope": None, "countries": [], "mission": ""}
    part = None
    for c in cells:
        if not c or c == ":":
            continue
        low = c.lower()
        if low.startswith("areas of expertise"):
            part = "fields"
        elif low.startswith("geographic scope"):
            part = "scope"
        elif low.startswith("country of activity"):
            part = "countries"
        elif low.startswith("millennium development goals") or low.startswith("year established") or low.startswith("view "):
            part = None
        elif low.startswith("mission statement"):
            part = "mission"
        elif part == "fields":
            out["fields"].append(c)
        elif part == "scope" and not out["scope"]:
            out["scope"] = c
        elif part == "countries":
            out["countries"].append(c)
        elif part == "mission" and (c.endswith(":") or low.startswith("civil society database")):
            part = None  # next field ("Funding structure:", "Membership:" ...) or the page menu
        elif part == "mission":
            out["mission"] = (out["mission"] + " " + c).strip()
            if len(out["mission"]) > 1500:
                part = None
    return out


def parse_profile(p):
    """ECOSOC profile page (short text version, cells separated by "|"), checked 10.11.2026:
    ... Headquarters address | Address: | <street> | <city> | <Country> | Phone: | ... | Email: | x |
    Web site: | x | Organization type: | x | Languages: | a | b | Civil Society Database ..."""
    t = p.get("text") or ""
    cells = [c.strip() for c in t.split("|")]
    out = {}

    def after(label):
        for i, c in enumerate(cells):
            if c == label and i + 1 < len(cells):
                return i + 1
        return None
    i = after("Phone:") 
    if i:  # the country is the cell just before "Phone:"
        out["country"] = cells[i - 2]
    else:
        j = after("Address:")
        if j:
            k = next((n for n in range(j, min(j + 8, len(cells))) if cells[n].endswith(":")), None)
            if k:
                out["country"] = cells[k - 1]
    for label, key in (("Web site:", "website"), ("Organization type:", "type"), ("Email:", "email")):
        j = after(label)
        if j and not cells[j].endswith(":"):
            out[key] = cells[j]
    j = after("Languages:")
    if j:
        langs = []
        for c in cells[j:j + 12]:
            if c.endswith(":") or c.startswith("Civil Society"):
                break
            langs.append(c)
        out["languages"] = ", ".join(langs)
    if not out.get("website"):
        out["website"] = next((u for u in p.get("links") or [] if not any(g in u for g in GENERIC_DOMAINS)), None)
    out["email"] = out.get("email") or (p.get("emails") or [None])[0]
    return out


def ecosoc():
    lists = load_gz("ecosoc/lists.json.gz", {})
    orgs = load_gz("ecosoc/orgs.json.gz", {})
    profiles = load_gz("ecosoc/profiles.json.gz", {})
    if not orgs:
        return []
    member = defaultdict(lambda: {"status": None, "types": set(), "fields": set(), "dgc": False})
    for m in lists.values():
        kind, label = m.get("kind"), (m.get("label") or "")
        for code in m.get("codes") or []:
            r = member[code]
            if kind == "status":
                r["status"] = STATUS_ID.get(label.lower().split()[0] if label else "", r["status"])
            elif kind == "type":
                r["types"].add(label)
            elif kind == "field":
                f = field_label(m)
                if f:
                    r["fields"].add(f)
            elif kind == "dpi":
                r["dgc"] = True
    ngo_type = set(FIELDS.get("types_included") or [])
    type_lists_known = any(m.get("kind") == "type" and m.get("complete") for m in lists.values())
    out = []
    for code, o in orgs.items():
        r = member[code]
        prof = parse_profile(profiles.get(code) or {})
        if type_lists_known and not (r["types"] & ngo_type):
            continue  # not of type "Non-governmental organization" (owner: classic NGOs first)
        if prof.get("type") and prof["type"] not in ngo_type:
            continue
        status = r["status"]
        if not status:  # accreditations column, e.g. "Special 2016"
            for a in o.get("accreditations") or []:
                s = STATUS_ID.get(a.split()[0].lower())
                if s:
                    status = s
                    break
        website, domain = norm_url(prof.get("website"))
        country = to_iso3(prof["country"]) if prof.get("country") else None
        act = parse_activities((profiles.get(code) or {}).get("activities"))
        active_in = sorted({x for x in (to_iso3(c) for c in act["countries"]) if x})
        us = [status or "ecosoc_registered"] + (["dgc_associated"] if r["dgc"] else [])
        out.append({
            "key": f"ecosoc:{code}", "source": "ecosoc", "name": clean_name(o["name"]), "alt_names": [],
            "website": website, "domain": domain, "country": country,
            "languages": LANG.codes_of(re.split(r"[,;/]| and ", prof.get("languages") or "")),
            "email": prof.get("email"), "social": {},
            "fields": sorted(set(r["fields"]) | set(act["fields"])), "un_status": us,
            "description": act["mission"] or prof.get("mission") or "",
            "active_in": active_in, "geo_scope": act["scope"],
            "profile_url": f"https://esango.un.org/civilsociety/showProfileDetail.do?method=showProfileDetails&profileCode={code}",
        })
    return out


# ------------------------------------------------------------------ Wikidata
def wikidata():
    recs = load_gz("wikidata_ngo/data.json.gz", [])
    lab_file = RAW / "wikidata_ngo" / "linked_labels.json"
    labels = json.load(open(lab_file, encoding="utf-8")) if lab_file.exists() else {}
    out = []
    for r in recs:
        names = r.get("labels") or {}
        name = names.get("en") or next(iter(names.values()), None)
        if not name:
            continue
        if r.get("dissolved") or r.get("date_of_closure"):
            continue
        countries = [c for c in r.get("matched_countries", []) if c in COUNTRIES]
        website, domain = norm_url((r.get("website") or [None])[0])
        social = {k: r[f][0] if isinstance(r.get(f), list) else r.get(f) for k, f in (
            ("youtube", "youtube_channel_id"), ("facebook", "facebook_id"), ("instagram", "instagram_username"),
            ("tiktok", "tiktok_username"), ("x", "x_username"), ("telegram", "telegram_username")) if r.get(f)}
        lab = lambda qs: [labels.get(q) or q for q in qs or []]  # noqa: E731
        out.append({
            "key": f"wd:{r['qid']}", "source": "wikidata_ngo", "name": name,
            "alt_names": sorted({v for v in names.values() if v != name})[:10],
            "website": website, "domain": domain, "country": countries[0] if countries else None,
            "languages": LANG.codes_of(lab(r.get("language_used")) + lab(r.get("language_of_work"))),
            "email": (r.get("email") or [None])[0], "social": social,
            "fields": [], "un_status": [],
            "description": "", "short": lab(r.get("field_of_work")),  # Wikidata "field of work": a short label each
            "wd_classes": lab(r.get("instance_of")), "wd_ideology": lab(r.get("political_ideology")),
            "wd_member_of": lab(r.get("member_of")),
            "wikipedia_languages": r.get("wikipedia_languages", 0),
        })
    return out


def geneva():
    out = []
    for r in un_geneva():
        out.append({**r, "fields": [], "un_status": ["un_geneva"], "description": "", "social": {}})
    return out


def iati_ngos():
    out = []
    for r in iati():
        out.append({**r, "fields": [], "un_status": ["iati_publisher"],
                    "description": (r.get("raw") or {}).get("description") or "", "social": {}})
    return out


# ------------------------------------------------------------------ UN Global Compact (owner 13.11.2026)
GC = yaml.safe_load(open(ROOT / "config" / "sources" / "global_compact.yaml", encoding="utf-8"))


def global_compact():
    out = []
    for r in load_gz("global_compact/data.json.gz", []):
        if r.get("status") and r["status"] not in GC["status_shown"]:
            continue  # e.g. expelled / delisted
        website, domain = norm_url(r.get("website"))
        code = (re.search(r"/participants/(\d+)", r["path"]) or [None, r["path"]])[1]
        since = (re.search(r"(\d{4})", r.get("since") or r.get("joined") or "") or [None, None])[1]
        out.append({
            "key": f"gc:{code}", "source": "global_compact", "name": clean_name(r["name"]), "alt_names": [],
            "website": website, "domain": domain, "country": to_iso3(r["country"]) if r.get("country") else None,
            "languages": [], "email": None, "social": {}, "fields": [], "un_status": ["un_global_compact"],
            "description": "", "gc": {"since": since, "status": r.get("status") or "Active", "sector": r.get("sector") or "",
                                      "type": r["type"], "url": GC["base"] + r["path"]},
        })
    return out


def org_kind(name, members):
    """organisation type for the filter (config/ngo.yaml org_kind): from the Global Compact type, else from
    words in the name (config/sources/global_compact.yaml kind_words), else NGO"""
    for m in members:
        t = (m.get("gc") or {}).get("type", "")
        if t == "Labour Organization":
            return "labour"
        if t == "Business Association":
            return "business_association"
    # only for Global Compact entries: ECOSOC, UN Geneva and IATI list these organisations as NGOs already
    if any(m.get("gc") for m in members) and not any(m["source"] in ("ecosoc", "un_geneva", "iati") for m in members):
        for kind, words in GC["kind_words"].items():
            if contains_word(name or "", words):
                return kind
    return "ngo"


# ------------------------------------------------------------------ merge
def merge(records):
    """same website (not a social network or blog host) or same name in the same country = same NGO"""
    groups, by_domain, by_name, by_name_only = [], {}, {}, {}
    # records with a country first; ECOSOC entries without a profile yet (no country) are then
    # matched by name alone, when exactly one NGO has that name
    records = sorted(records, key=lambda r: r.get("country") is None)
    for r in records:
        d = (r.get("domain") or "").split("/")[0]
        dk = d if d and not any(d == g or d.endswith("." + g) for g in GENERIC_DOMAINS) else None
        nk = (name_key(r["name"]), r.get("country")) if r.get("country") else None
        g = (by_domain.get(r.get("domain")) if dk else None) or (by_name.get(nk) if nk else None)
        if g is None and not r.get("country"):
            cand = by_name_only.get(name_key(r["name"]))
            g = cand if cand not in (None, "ambiguous") else None
        if g is None:
            g = {"members": []}
            groups.append(g)
        g["members"].append(r)
        if dk:
            by_domain.setdefault(r["domain"], g)
        if nk:
            by_name.setdefault(nk, g)
        if r.get("country"):
            k = name_key(r["name"])
            by_name_only[k] = g if by_name_only.get(k) in (None, g) else "ambiguous"
        for a in r.get("alt_names") or []:
            if r.get("country"):
                by_name.setdefault((name_key(a), r["country"]), g)
    return groups


ORDER = ["ecosoc", "global_compact", "wikidata_ngo", "un_geneva", "iati"]
PREF = {"ecosoc": 0, "gc": 1, "wd": 2, "ungva": 3, "iati": 4}


def nid_guess(keys):
    """stable id of a merged NGO: the key of its best source (ECOSOC > Wikidata > UN Geneva > IATI)"""
    main_key = min(keys, key=lambda k: (PREF.get(k.split(":")[0], 9), k))
    return "ngo-" + re.sub(r"[^a-z0-9]+", "-", main_key.lower()).strip("-")


def first(members, key):
    for m in sorted(members, key=lambda m: ORDER.index(m["source"]) if m["source"] in ORDER else 9):
        if m.get(key):
            return m[key]
    return None


sys.path.insert(0, str(ROOT / "pipeline" / "shared"))
from org_email import org_email  # noqa: E402  (one rule for all: config/rules.yaml org_email)


def contains_word(text, words):
    t = " " + norm(text) + " "
    for w in words:
        k = norm(w)
        if k and (" " + k + " ") in t:
            return w
    return None


def website_data():
    """results of the website check (pipeline/fetch/website_check.py also checks NGO websites)"""
    web = {}
    for f in sorted((RAW / "website_check").glob("*.json.gz")):
        for i, v in json.load(gzip.open(f, "rt", encoding="utf-8")).items():
            if i.startswith("ngo-"):
                web[i] = v
    return web


UN_ACCREDITED = {"ecosoc_general", "ecosoc_special", "ecosoc_roster", "un_geneva", "dgc_associated", "desa_cosp",
                 "un_global_compact"}  # also: Global Compact participants (owner 13.11.2026: universities, cities ... all in)


UN_PARTNER = set()  # filled from config/ngo.yaml un_partner (owner 13.11.2026)


def main():
    UN_PARTNER.update(CFG["un_partner"]["statuses"])
    recs = ecosoc() + global_compact() + wikidata() + geneva() + iati_ngos()
    web = website_data()
    import csv
    iso1 = {r["iso639_1"]: r["code"] for r in csv.DictReader(open(ROOT / "config" / "languages.csv", encoding="utf-8")) if r["iso639_1"]}
    print("records:", Counter(r["source"] for r in recs))
    groups = merge(recs)
    # Wikidata alone counts only with a classic NGO class (config/ngo.yaml wikidata_classes_included)
    ok_cls = {x.lower() for x in CFG.get("wikidata_classes_included") or []}
    kept = []
    for g in groups:
        srcs = {m["source"] for m in g["members"]}
        if srcs == {"wikidata_ngo"} and not any(c.lower() in ok_cls for m in g["members"] for c in m.get("wd_classes") or []):
            continue
        kept.append(g)
    print(f"groups: {len(groups)}, kept {len(kept)} (Wikidata-only items without a classic NGO class left out)")
    groups = kept
    topics = Matcher()
    audience = Matcher(ROOT / "config" / "audience_keywords.yaml")
    field_map = {k.lower(): v for k, v in FIELDS["fields"].items()}
    sector_map = {k.lower(): v for k, v in GC["sector_topics"].items()}
    aud_fields = {k.lower(): v for k, v in CFG["audience_from_fields"].items()}
    weight = {s["id"]: s["weight"] for s in CFG["un_status"]}
    ideos = {x.lower() for x in RULES["exclude_far_right"]["wikidata_ideologies"]}
    gongo = {x.lower() for x in CFG["exclude"]["wikidata_classes"]}
    right = {x.lower() for x in CFG["exclude"].get("wikidata_ideologies_right") or []}
    not_ngo = {x.lower() for x in CFG["exclude"].get("wikidata_not_ngo_classes") or []}
    not_ngo_words = [x.lower() for x in CFG["exclude"].get("wikidata_not_ngo_class_words") or []]
    keep_cls = {x.lower() for x in CFG["exclude"].get("wikidata_class_words_keep") or []}
    first_seen_file = ROOT / "cache" / "ngo_first_seen.json"
    first_seen = json.load(open(first_seen_file, encoding="utf-8")) if first_seen_file.exists() else {}
    out, excluded = [], []
    for g in groups:
        ms = g["members"]
        name = first(ms, "name")
        country = first(ms, "country")
        keys = sorted(m["key"] for m in ms)
        nid = nid_guess(keys)
        # exclusions
        why_out = None
        # 11.11.2026: NGOs accredited by the UN (ECOSOC consultative status, UN Geneva) count as NGOs even when
        # Wikidata calls them a club, professional association ... (Rotary, Lions, Zonta, bar associations)
        accredited = any(s in UN_ACCREDITED for m in ms for s in m.get("un_status") or [])
        for m in ms:
            hit = [i for i in m.get("wd_ideology") or [] if i.lower() in ideos]
            if hit:
                why_out = "far-right (Wikidata political ideology: " + hit[0] + ")"
            hit = [i for i in m.get("wd_ideology") or [] if i.lower() in right]
            if hit and not why_out:
                why_out = "right-wing (Wikidata political ideology: " + hit[0] + ")"
            cls = [c for c in m.get("wd_classes") or [] if c.lower() in gongo]
            if cls:
                why_out = "government-organised NGO (Wikidata: " + cls[0] + ")"
            cls = [c for c in m.get("wd_classes") or [] if c.lower() in not_ngo
                   or (c.lower() not in keep_cls
                       and any(re.search(r"\b" + re.escape(w) + r"\b", c.lower()) for w in not_ngo_words))]
            if cls and not why_out and not accredited:
                why_out = "not a classic NGO (Wikidata: " + cls[0] + ")"
        man = next((x["reason"] for x in CFG["exclude"].get("manual") or [] if x["name"].lower() == (name or "").lower()), None)
        if man and not why_out:
            why_out = man + " (checked by hand)"
        w = contains_word(name, CFG["exclude"]["name_words"])
        if w and not why_out and not accredited:
            why_out = f'not a classic NGO (name contains "{w.strip()}")'
        if why_out:
            excluded.append((nid, name, country, why_out))
            continue
        if not country or country not in COUNTRIES:
            excluded.append((nid, name, country or "-", "no country of the 195 in the sources"))
            continue
        fields = sorted({f for m in ms for f in m.get("fields") or []})
        desc = " | ".join(dict.fromkeys(m["description"] for m in ms if m.get("description")))
        # topics: ECOSOC fields (the NGO named them itself) = Specialist; words in name / description
        tps = {}

        def add(topic, sub, strength, source):
            t = tps.setdefault(topic, {"value": topic, "method": "source_field", "strength": 9, "source": "", "subs": set()})
            if sub:
                t["subs"].add(sub)
            if strength < t["strength"]:
                t["strength"], t["source"] = strength, source
        # topic strength (owner 12.11.2026): ECOSOC fields of activity = "Desk" (2); "Focus" (1) when the topic is
        # also in the NGO's name or own description; topics only from the website = "Covers" (3)
        for f in fields:
            for x in field_map.get(f.lower(), []):
                tp, _, sub = x.partition("/")
                add(tp, sub or None, 2, f"ECOSOC field of activity: {f}")
        from_fields = set(tps)
        shorts = [x for m in ms for x in m.get("short") or []]
        abouts = [("description", desc)] if desc else []
        own = topics.match(name=name, descriptions=shorts, abouts=abouts, menu=[], headlines=[])
        for tp, r in own.items():
            if tp in from_fields:
                tps[tp]["strength"], tps[tp]["source"] = 1, tps[tp]["source"] + "; also " + r["why"]
                tps[tp]["subs"] |= set(r["subs"] or [])
            else:
                for sub in r["subs"] or [None]:
                    add(tp, sub, r["s"], r["why"])
        wsite = web.get(nid_guess(keys)) or {}
        if wsite.get("status") == "ok":
            wshort = [x for x in (wsite.get("desc"), wsite.get("title")) if x]
            wabout = [("website About page", wsite["about"])] if wsite.get("about") else []
            menu = [tuple(x) for x in wsite.get("nav") or []]
            heads = (wsite.get("heads") or []) + ([wsite["home_text"]] if wsite.get("home_text") else [])
            for tp, r in topics.match(name="", descriptions=wshort, abouts=wabout, menu=menu, headlines=heads).items():
                for sub in r["subs"] or [None]:
                    add(tp, sub, 3 if tp not in tps else r["s"], r["why"])
        cat_topics = [{**t, "subs": sorted(t["subs"]), "method": "source_field" if t["source"].startswith("ECOSOC") else "keyword"}
                      for t in tps.values()]
        aud = {}
        for f in fields:
            a = aud_fields.get(f.lower())
            if a:
                aud.setdefault(a, f"ECOSOC field of activity: {f}")
        for a, r in audience.match(name=name, descriptions=shorts, abouts=abouts).items():
            aud.setdefault(a, r["why"])
        # Global Compact sector -> topics, "Has a section on it" (config/sources/global_compact.yaml sector_topics)
        gcs = [m["gc"] for m in ms if m.get("gc")]
        for g in gcs:
            for x in sector_map.get(g["sector"].lower(), []):
                tp, _, sub = x.partition("/")
                add(tp, sub or None, 2, f"UN Global Compact sector: {g['sector']}")
        tow = []
        for t in CFG["type_of_work"]:
            f = next((f for f in fields if f.lower() in [x.lower() for x in t["fields"]]), None)
            word = None if f else contains_word(name, t["words"])  # name only: descriptions mention too much
            if f or word:
                tow.append([t["id"], f"ECOSOC field of activity: {f}" if f else f'name: "{word}"'])
        us = sorted({s for m in ms for s in m.get("un_status") or []}, key=lambda s: -weight.get(s, 0))
        if any(s.startswith("ecosoc_") and s != "ecosoc_registered" for s in us):
            us = [s for s in us if s != "ecosoc_registered"]
        social = {}
        if wsite.get("status") == "ok":
            for k, u in (wsite.get("social") or {}).items():
                social.setdefault(k, u)
        for m in ms:
            for k, v in (m.get("social") or {}).items():
                social.setdefault(k, v)
        wl = max([m.get("wikipedia_languages") or 0 for m in ms])
        first_seen.setdefault(nid, TODAY)
        out.append({
            "id": nid, "name": name, "country": country, "kind": "ngo",
            "alt_names": sorted({a for m in ms for a in [m["name"]] + (m.get("alt_names") or []) if a != name})[:5],
            "website": first(ms, "website"),
            "languages": sorted({l for m in ms for l in m.get("languages") or []})
            or ([iso1[wsite["lang"].split("-")[0].split("_")[0].lower()]] if wsite.get("lang") and wsite["lang"].split("-")[0].split("_")[0].lower() in iso1 else []),
            "contact_page": wsite.get("contact_url") if wsite.get("status") == "ok" else None,
            "last_post": wsite.get("last_post"),
            "channels": (["website"] if first(ms, "website") else []) + (["social_media"] if social else []),
            "social": social, "email": next((x for x in [org_email(m.get("email")) for m in ms] + [org_email(e) for e in wsite.get("emails") or []] if x), None), "sources": sorted({m["source"] for m in ms}),
            "members": keys, "first_seen": first_seen[nid], "wikipedia_languages": wl,
            "profile_url": first(ms, "profile_url"),
            "description": (desc or "")[:600],
            "active_in": sorted({c for m in ms for c in m.get("active_in") or []} - {country}),
            "geo_scope": next((g["id"] for m in ms if m.get("geo_scope") for g in CFG.get("geo_scope") or []
                               if m["geo_scope"].lower().startswith(g["id"][:6])), None),  # config/ngo.yaml geo_scope
            "org_kind": org_kind(name, ms),
            "global_compact": ({"since": min((g["since"] for g in gcs if g["since"]), default=None),
                                "status": gcs[0]["status"], "sector": next((g["sector"] for g in gcs if g["sector"]), ""),
                                "url": gcs[0]["url"]} if gcs else None),
            "un_partner": any(s in UN_PARTNER for s in us),
            "ngo": {"un_status": us, "type_of_work": tow, "fields": fields,
                    "registered_only": us[:1] == ["ecosoc_registered"] and len(ms) == 1},
            "prominence": max([weight.get(s, 0) for s in us] or [0]) * 10 + wl + len({m["source"] for m in ms}),
            "cat": {"topics": cat_topics,
                    "audience_groups": [{"value": a, "source": s} for a, s in aud.items()],
                    "website_status": wsite.get("status"),
                    "org_type": {"value": "ngo", "source": "NGO list: " + ", ".join(sorted({m['source'] for m in ms}))}},
        })
    json.dump(first_seen, open(first_seen_file, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    json.dump(out, open(ROOT / "work" / "ngos.json", "w", encoding="utf-8"), ensure_ascii=False)
    # reports
    n = len(out) or 1
    pct = lambda f: f"{sum(1 for o in out if f(o)) / n * 100:.0f} %"  # noqa: E731
    lines = ["# NGOs (phase 2)", "", f"Built {TODAY}. Sources: " + ", ".join(f"{k} {v}" for k, v in Counter(r['source'] for r in recs).items()), "",
             f"**{len(out):,} NGOs** shown on the NGO page, {len(excluded):,} not shown "
             "(reports/ngos_excluded.md).", "",
             "| Information | Share |", "|---|---|",
             f"| Topic | {pct(lambda o: o['cat']['topics'])} |",
             f"| Topic from ECOSOC fields of activity | {pct(lambda o: o['ngo']['fields'])} |",
             f"| Target audience | {pct(lambda o: o['cat']['audience_groups'])} |",
             f"| Language | {pct(lambda o: o['languages'])} |",
             f"| Website | {pct(lambda o: o['website'])} |",
             f"| E-mail | {pct(lambda o: o['email'])} |",
             f"| ECOSOC consultative status | {pct(lambda o: any(s in ('ecosoc_general', 'ecosoc_special', 'ecosoc_roster') for s in o['ngo']['un_status']))} |",
             f"| Only registered in ECOSOC (note on the card) | {pct(lambda o: o['ngo']['registered_only'])} |",
             "", "## UN status", ""]
    for s, c in Counter(s for o in out for s in o["ngo"]["un_status"]).most_common():
        lines.append(f"- {s}: {c:,}")
    lines += ["", "## Countries with most NGOs", ""]
    for c, k in Counter(o["country"] for o in out).most_common(20):
        lines.append(f"- {c}: {k:,}")
    (ROOT / "reports" / "ngos.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    ex = ["# NGOs not shown", "", "| Id | Name | Country | Reason |", "|---|---|---|---|"]
    ex += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in sorted(excluded, key=lambda x: (x[3], x[2] or "", x[1] or ""))]
    (ROOT / "reports" / "ngos_excluded.md").write_text("\n".join(ex) + "\n", encoding="utf-8")
    print(f"{len(out)} NGOs, {len(excluded)} not shown")


if __name__ == "__main__":
    main()
