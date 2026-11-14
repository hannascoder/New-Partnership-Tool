"""Builds the files the website reads (site/data/):
  outlets-N.json one compact entry per outlet (short keys, empty fields left out),
                 split into files of 25,000 outlets (Cloudflare limit: 25 MiB per file)
  config.json    allowed values for the filters (from config/), so the page
                 never hard-codes a category, country or language
The website only reads these two files (briefing K1)."""
import csv
import gzip
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config"
sys.path.insert(0, str(ROOT / "pipeline" / "shared"))
from org_email import org_email  # noqa: E402
SOCIAL_URL = {"youtube": "https://www.youtube.com/channel/{}", "facebook": "https://www.facebook.com/{}",
              "instagram": "https://www.instagram.com/{}", "tiktok": "https://www.tiktok.com/@{}",
              "x": "https://x.com/{}", "telegram": "https://t.me/{}"}
# Lists offered in the "Member of" filter (owner's request, 06.11.2026)
# "un_relationship" = every outlet with the UN profile "Existing UN relationship" (owner, 09.11.2026)
NETWORK_FILTER = {"un_relationship": "Existing UN relationship (SDG Media Compact)", "ebu_members": "EBU (European Broadcasting Union)",
                  "abu_members": "ABU (Asia-Pacific Broadcasting Union)", "asbu_members": "ASBU (Arab States Broadcasting Union)",
                  "cbu_members": "CBU (Caribbean Broadcasting Union)", "ifcn_signatories": "IFCN (fact-checkers)",
                  "efcsn_signatories": "EFCSN (fact-checkers)",
                  "fact_checking_sites": "Fact-checking websites (Wikipedia list)",
                  "occrp_network": "OCCRP (investigative journalism)"}
SOURCE_LABEL = {"wikidata": "Wikidata", "media_cloud": "Media Cloud", "iptv_org": "iptv-org",
                "radio_browser": "Radio Browser", "sdg_media_compact": "SDG Media Compact", "ifcn_signatories": "IFCN",
                "efcsn_signatories": "EFCSN", "news_agencies": "Wikipedia: news agencies",
                "state_media": "Wikipedia: state media", "fact_checking_sites": "Wikipedia: fact-checking websites",
                "ebu_members": "EBU", "abu_members": "ABU", "asbu_members": "ASBU", "cbu_members": "CBU",
                "occrp_network": "OCCRP", "ecosoc": "ECOSOC iCSO", "global_compact": "UN Global Compact", "wikidata_ngo": "Wikidata",
                "un_geneva": "UN Geneva NGO list", "iati": "IATI"}


def fix_text(s):
    """Repairs names whose letters were mis-read by a source ("Rock â€“ News" -> "Rock – News"):
    the text is re-read as UTF-8 if that removes the typical broken characters."""
    if not s or not any(m in s for m in ("â€", "Ã", "‚Ä", "Â", "Ð", "Ø§", "„Å", "„Ç", "„É", "„Ä")):
        return s
    for enc in ("cp1252", "latin-1", "mac_roman"):
        try:
            t = s.encode(enc).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if t != s:
            return t
    return s


def compact(out):
    """Keeps outlets.json under Cloudflare's 25 MiB per-file limit: values that repeat
    (channels, sources, type, ownership, scope) become numbers, the most common
    "first seen" date is left out, social links are stored as the account name when
    they follow the usual address pattern. finder.js expand() restores everything."""
    from collections import Counter
    codes = {}
    for key, pos in (("ch", None), ("s", None), ("o", 0), ("ow", 0), ("sc", 0), ("oa", None), ("nw", None)):
        vals = sorted({(v if pos is None else e[key][pos]) for e in out if key in e
                       for v in (e[key] if pos is None else [None])} - {None})
        if pos is not None:
            vals = sorted({e[key][pos] for e in out if key in e})
        idx = {v: i for i, v in enumerate(vals)}
        codes[key] = vals
        for e in out:
            if key in e:
                if pos is None:
                    e[key] = [idx[v] for v in e[key]]
                else:
                    e[key] = [idx[e[key][0]]] + e[key][1:]
    common = Counter(e["f"] for e in out).most_common(1)[0][0]
    codes["f"] = common
    for e in out:
        if e["f"] == common:
            del e["f"]
    # links on the outlet's own website: stored without "https://www.example.org"
    import urllib.parse
    for e in out:
        base = e.get("w")
        if not base:
            continue
        host = re.sub(r"^www\.", "", urllib.parse.urlsplit(base if "//" in base else "http://" + base).netloc.lower())

        def rel(u):
            p = urllib.parse.urlsplit(u)
            if re.sub(r"^www\.", "", p.netloc.lower()) == host and p.path.startswith("/"):
                return p.path + ("?" + p.query if p.query else "")
            return u
        if e.get("cp"):
            e["cp"] = rel(e["cp"])
        for t in e.get("tp") or []:
            if len(t) >= 5:
                t[4] = rel(t[4])
    codes["so"] = SOCIAL_URL
    for e in out:
        for k, u in list((e.get("so") or {}).items()):
            tpl = SOCIAL_URL.get(k)
            if tpl:
                pre = tpl.split("{}")[0]
                if u.startswith(pre) and "/" not in u[len(pre):].rstrip("/"):
                    e["so"][k] = u[len(pre):].rstrip("/")
    return codes


def main():
    outlets = json.load(open(ROOT / "work" / "classified.json", encoding="utf-8"))
    outlets = [o for o in outlets if not (o.get("cat") or {}).get("excluded")  # far-right: not shown (rules.yaml)
               and not (o.get("cat") or {}).get("hidden")  # AI reading: not media / closed (reports/hidden_ai.md)
               and re.search(r"[^\W_]", fix_text(o.get("name") or "") or "")
               and "\ufffd" not in (o.get("name") or "")]  # no real name ("-", "|", broken characters): left out
    countries = list(csv.DictReader(open(CFG / "countries.csv", encoding="utf-8")))
    langs_all = {r["code"]: r for r in csv.DictReader(open(CFG / "languages.csv", encoding="utf-8"))}
    cats = yaml.safe_load(open(CFG / "categories.yaml", encoding="utf-8"))
    # sub-topics (config/topic_keywords.yaml) shown under a chosen topic; the words stay hidden
    kw = yaml.safe_load(open(CFG / "topic_keywords.yaml", encoding="utf-8"))["topics"]
    general = {k: v["general_subtopic"] for k, v in kw.items() if v.get("subtopics")}
    topic_merge = {t["id"]: t["merged_into"].split("/")[0] for t in cats["topics"] if t.get("merged_into")}
    cats["topics"] = [t for t in cats["topics"] if not t.get("merged_into")]  # merged topics are no buttons
    for t in cats["topics"]:
        subs = (kw.get(t["id"]) or {}).get("subtopics") or []
        if subs:
            t["subtopics"] = [{"id": s["id"], "label": s["label"]} for s in subs]

    rules = yaml.safe_load(open(CFG / "rules.yaml", encoding="utf-8"))
    ngo_file = ROOT / "work" / "ngos.json"
    ngos = json.load(open(ngo_file, encoding="utf-8")) if ngo_file.exists() else []

    # not media (config/rules.yaml not_media): government websites and NGOs listed as "media"
    def host_of(u):
        u = (u or "").strip().lower()
        if not u:
            return ""
        h = re.sub(r"^https?://", "", u).split("/")[0].split(":")[0]
        return re.sub(r"^(www\d?|m)\.", "", h)
    nm = rules.get("not_media") or {}
    gov = re.compile(nm["government_host"]) if nm.get("government_host") else None
    ngo_hosts = {}
    if nm.get("ngo_website"):
        cnt = defaultdict(int)
        for g in ngos:
            cnt[host_of(g.get("website"))] += 1
        for g in ngos:  # a host used by one organisation only (not facebook.com, blogspot ...)
            h = host_of(g.get("website"))
            if h and cnt[h] == 1:
                ngo_hosts[h] = g["name"]
    # automatic update: an outlet whose website was dead at N checks in a row is not shown
    # (rules.yaml automation; counted by pipeline/automation/website_state.py)
    auto = rules.get("automation") or {}
    ff = ROOT / "cache" / "website_fails.json"
    fails = json.load(open(ff, encoding="utf-8")) if ff.exists() else {}
    dead_limit = auto.get("hide_after_dead_checks", 3)
    dead_ids = {k for k, v in fails.items() if v[0] >= dead_limit}
    dead_rows = [o for o in outlets if o["id"] in dead_ids]
    outlets = [o for o in outlets if o["id"] not in dead_ids]
    ngos_dead = [g for g in ngos if g["id"] in dead_ids]
    ngos = [g for g in ngos if g["id"] not in dead_ids]
    (ROOT / "reports" / "hidden_websites.md").write_text("\n".join(
        ["# Not shown: the website was dead at the last " + str(dead_limit) + " checks in a row", "",
         f"{len(dead_rows)} outlets and {len(ngos_dead)} organisations. They come back on their own as soon as the website answers.",
         f"Counting towards it: {sum(1 for v in fails.values() if v[0] < dead_limit)} websites that were dead at the last check(s).", "",
         "| Id | Name | Country | Website |", "|---|---|---|---|"]
        + [f"| {o['id']} | {(o['name'] or '')[:70]} | {o['country']} | {o.get('website') or ''} |"
           for o in sorted(dead_rows + ngos_dead, key=lambda x: (x["country"] or "", x["name"] or ""))]) + "\n", encoding="utf-8")
    dropped, kept = [], []
    for o in outlets:
        h = host_of(o.get("website"))
        why_out = None
        if h and any(h == x or h.endswith("." + x) for x in nm.get("archive_hosts") or []):
            why_out = "historic newspaper: its only website is a newspaper archive"
        elif nm and h and set(o["sources"]) <= set(nm.get("only_sources", [])) and not set(o["channels"]) & set(nm.get("not_channels", [])):
            if gov and gov.search(h):
                why_out = "government website"
            elif h in ngo_hosts:
                why_out = "organisation on the Organisations & NGOs page: " + ngo_hosts[h]
        (dropped if why_out else kept).append((o, why_out))
    (ROOT / "reports" / "not_media.md").write_text("\n".join(
        ["# Not shown in the media list: government websites, NGOs, historic papers (config/rules.yaml not_media)", "",
         f"{len(dropped)} entries that a media list names but that are not media. To bring one back: tell Claude the id.", "",
         "| Id | Name | Country | Website | Reason |", "|---|---|---|---|---|"]
        + [f"| {o['id']} | {(o['name'] or '')[:70]} | {o['country']} | {o.get('website') or ''} | {y} |"
           for o, y in sorted(dropped, key=lambda x: (x[0]["country"] or "", x[0]["name"] or ""))]) + "\n", encoding="utf-8")
    outlets = [o for o, _ in kept]

    # prominence and rank within the country (briefing J; config/rules.yaml prominence)
    pr = rules.get("prominence") or {}
    bonus = pr.get("bonus") or {}
    special = set(pr.get("special_interest_classes") or [])
    sys.path.insert(0, str(ROOT / "pipeline" / "classify"))
    from classify import not_news, wd_classes  # the rule itself: pipeline/classify/classify.py
    data_date = max(o["first_seen"] for o in outlets) if outlets else str(date.today())
    y, m_ = int(data_date[:4]), int(data_date[5:7]) - cats.get("active_months", 3)
    while m_ < 1:
        y, m_ = y - 1, m_ + 12
    active_since = f"{y:04d}-{m_:02d}-{data_date[8:10]}"
    for o in outlets:
        cat = o.get("cat") or {}
        wl = (pr.get("wikipedia_languages_fix") or {}).get(o["id"], o.get("wikipedia_languages") or 0)
        o["_prom"] = wl + len(o["sources"])
        score = float(o["_prom"])
        cat["not_news"] = not_news(o, cat, rules.get("not_news") or {}) if cat.get("org_type") else None
        tps = [t for t in cat.get("topics", []) if t["method"] != "default" and t["value"] != "community_local"]
        is_general = any(t["value"] == "general_news" for t in tps)
        declared = any(t["method"] == "source_field" and t.get("strength", 1) == 1 for t in tps)
        if cat.get("not_news"):
            score *= pr.get("not_news_factor", 1)
        elif (cat.get("org_type") or {}).get("value") == "news_outlet" and (
                (not is_general and declared) or (special and wd_classes(o) & special)):
            score *= pr.get("special_interest_factor", 1)
        if (o.get("last_post") or "") >= active_since:
            score += bonus.get("active", 0)
        if cat.get("website_status") == "ok":
            score += bonus.get("website_ok", 0)
        if o.get("social") or o.get("social_urls"):
            score += bonus.get("social_media", 0)
        if o.get("contact_page") or org_email(o.get("email")):
            score += bonus.get("public_contact", 0)
        o["_score"] = score
    by_country = defaultdict(list)
    for o in outlets:
        by_country[o["country"]].append(o)
    for lst in by_country.values():
        lst.sort(key=lambda o: (-o["_score"], -o["_prom"], (o["name"] or "").lower()))
        for i, o in enumerate(lst, 1):
            o["_rank"] = i

    # a name in another script than the outlet's languages -> a name in Latin letters (rules.yaml name_scripts)
    SCRIPT_RX = {"Arabic": r"[\u0600-\u06FF]", "Cyrillic": r"[\u0400-\u04FF]", "CJK": r"[\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]",
                 "Hebrew": r"[\u0590-\u05FF]", "Greek": r"[\u0370-\u03FF]", "Devanagari": r"[\u0900-\u097F]", "Thai": r"[\u0E00-\u0E7F]"}
    scripts = rules.get("name_scripts") or {}
    official = {r["iso3"]: set(filter(None, r["official_languages"].split(";")))
                for r in csv.DictReader(open(CFG / "official_languages.csv", encoding="utf-8"))}

    def latin_name(o):
        name = fix_text(o["name"])
        if re.search(r"[A-Za-z]", name or ""):
            return name
        for sc, langs in scripts.items():
            if re.search(SCRIPT_RX[sc], name or ""):
                own = set(o.get("languages") or []) | official.get(o["country"], set())
                if own & set(langs):
                    return name
                alt = [a for a in o.get("alt_names") or [] if re.search(r"[A-Za-z]{2}", a) and not re.search(r"[^\u0000-\u024F]", a)
                       and "@" not in a and "." not in a]
                if alt:
                    o["alt_names"] = [name] + [a for a in o["alt_names"] if a != min(alt, key=len)]
                    return min(alt, key=len)
        return name

    out, used_langs = [], set()
    why = {}  # repeated "source of a value" texts stored once (keeps outlets.json small)

    def w(text):
        return why.setdefault(text, len(why))
    def build_entry(o):
        e = {"i": o["id"], "n": latin_name(o), "c": o["country"], "p": round(o["_score"], 2), "r": o["_rank"]}
        alt = [a for a in o["alt_names"] if a.isascii() and "@" not in a][:3]
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
        for k, u in (o.get("social_urls") or {}).items():  # from the website check
            if k in SOCIAL_URL or k == "linkedin":
                e.setdefault("so", {}).setdefault(k, u)
        if o.get("owner_names"):
            e["on"] = o["owner_names"][:3]
        if o.get("contact_page"):
            e["cp"] = o["contact_page"]
        if o.get("last_post"):
            e["lp"] = o["last_post"]
        if org_email(o.get("email")):  # only organisation addresses (config/rules.yaml org_email)
            e["em"] = org_email(o["email"])
        e["s"] = o["sources"]
        e["f"] = o["first_seen"]
        if (o.get("cat") or {}).get("website_status") == "error":
            e["wd"] = 1  # website did not answer at the last website check
        if (o.get("cat") or {}).get("website_warning"):
            e["ww"] = o["cat"]["website_warning"]  # website seems to belong to someone else now
        cat = o.get("cat", {})
        if cat.get("not_news"):
            e["nn"] = 1  # pure sports / music / children's / religious channel (rules.yaml not_news)
        # topics (step 4d): ids in "tp", the reason of each in "tw" (same order).
        # Left out when the only topic is the default "general news" (no evidence).
        # [topic, strength (1 focus, 2 desk, 3 covers), reason, [sub-topics]]
        tps = [t for t in cat.get("topics", []) if t["method"] != "default"]
        if tps:
            # 5th value: link to the website section ("own section" only)
            e["tp"] = [[t["value"], t.get("strength", 1), w(t["source"])]
                       + ([t.get("subs") or [general[t["value"]]]] if t["value"] in general else [[]])
                       + ([t["url"]] if t.get("url") else [])
                       for t in tps]
            for x in e["tp"]:
                if len(x) == 4 and x[3] == []:
                    x.pop()
        if cat.get("audience_groups"):
            e["au"] = [a["value"] for a in cat["audience_groups"]]
            e["aw"] = [w(a["source"]) for a in cat["audience_groups"]]
        if cat.get("un_profile"):
            e["un"] = [u["value"] for u in cat["un_profile"]]
            e["uw"] = [w(u["source"]) for u in cat["un_profile"]]
        if cat.get("org_type"):
            e["o"] = [cat["org_type"]["value"], w(cat["org_type"]["source"])]
        if cat.get("org_type_also"):
            e["oa"] = cat["org_type_also"]
        if cat.get("ownership"):
            e["ow"] = [cat["ownership"]["value"], w(cat["ownership"]["source"])]
        if cat.get("scope"):
            e["sc"] = [cat["scope"]["value"], w(cat["scope"]["source"])]
        aud = {c: b for c, b in (cat.get("audience") or {}).items() if c != o["country"]}
        if aud:
            e["rc"] = {c: w(b) for c, b in aud.items()}
        if cat.get("service_languages"):
            e["l"] = (e.get("l") or []) + cat["service_languages"]
            used_langs.update(cat["service_languages"])
        if cat.get("services"):
            e["sv"] = cat["services"]
        nets = (["un_relationship"] if any(u["value"] == "un_relationship" for u in cat.get("un_profile", [])) else []) \
            + [n for n in o.get("networks", []) if n in NETWORK_FILTER and n != "sdg_media_compact"]
        if nets:
            e["nw"] = nets

        return e

    for o in outlets:
        out.append(build_entry(o))
    out.sort(key=lambda e: (e["n"] or "").lower())

    # NGOs (phase 2, config/ngo.yaml): own files, loaded by the page only when
    # "Include NGOs in this search" is ticked. Same entry format + NGO fields:
    # ng 1, us UN status ids, nt [[type of work, reason]], ro 1 = only registered in ECOSOC, pu profile link
    ngo_cfg = yaml.safe_load(open(CFG / "ngo.yaml", encoding="utf-8"))
    by_c = defaultdict(list)
    for o in ngos:
        o["_prom"] = o.get("prominence", 0)
        by_c[o["country"]].append(o)
    for lst in by_c.values():
        lst.sort(key=lambda o: (-o["_prom"], (o["name"] or "").lower()))
        for i, o in enumerate(lst, 1):
            o["_rank"] = i
    ngo_out = []
    for o in ngos:
        o.setdefault("alt_names", [])
        o.setdefault("_score", o["_prom"])
        e = build_entry(o)
        e["ng"] = 1
        e["us"] = o["ngo"]["un_status"]
        if o["ngo"]["type_of_work"]:
            e["nt"] = [[t, w(r)] for t, r in o["ngo"]["type_of_work"]]
        if o["ngo"].get("registered_only"):
            e["ro"] = 1
        if o.get("profile_url"):
            e["pu"] = o["profile_url"]
        if o.get("active_in"):
            e["ca"] = o["active_in"]  # countries of activity (ECOSOC "Activities" tab)
        if o.get("geo_scope"):
            e["gs"] = o["geo_scope"]
        e["ok"] = o.get("org_kind") or "ngo"  # organisation type (config/ngo.yaml org_kind)
        if o.get("un_partner"):
            e["up"] = 1  # existing UN partner (config/ngo.yaml un_partner)
        if o.get("global_compact"):
            g = o["global_compact"]
            e["gc"] = [g.get("since") or "", g.get("status") or "", g.get("sector") or "", g.get("url") or ""]
        if o.get("description"):
            e["ds"] = fix_text(o["description"])[:600]
        if set(e["us"]) & {"ecosoc_general", "ecosoc_special", "ecosoc_roster", "dgc_associated", "un_geneva", "desa_cosp"}:
            e["nw"] = ["un_relationship"]  # "Member of: Existing UN relationship" also finds these NGOs
        ngo_out.append(e)
    ngo_out.sort(key=lambda e: (e["n"] or "").lower())
    # automatic update: an outlet that is in no source any more stays for one update, with a note
    # (rules.yaml automation.remove_after_missing_runs). Only counted in the scheduled update
    # (PF_SCHEDULED=1), so a data run by hand never changes the counters.
    import os
    if os.environ.get("PF_SCHEDULED") == "1":
        all_ids = {o["id"] for o in json.load(open(ROOT / "work" / "classified.json", encoding="utf-8"))}
        mf = ROOT / "cache" / "missing.json"
        missing = json.load(open(mf, encoding="utf-8")) if mf.exists() else {}
        keep_runs = auto.get("remove_after_missing_runs", 2)
        carried, removed = [], []
        old_cfg_file = ROOT / "site" / "data" / "config.json"
        if old_cfg_file.exists():
            old_cfg = json.load(open(old_cfg_file, encoding="utf-8"))
            oc, ow_ = old_cfg.get("codes") or {}, old_cfg.get("why") or []
            for fn in old_cfg.get("outlet_files") or []:
                for e in json.load(open(ROOT / "site" / "data" / fn, encoding="utf-8")):
                    if e["i"] in all_ids:
                        continue
                    n_ = missing.get(e["i"], 0) + 1
                    if n_ >= keep_runs:
                        removed.append(e)
                        continue
                    missing[e["i"]] = n_
                    for k in ("ch", "s", "oa", "nw"):  # undo the short codes of the old file
                        if k in e:
                            e[k] = [oc[k][v] if isinstance(v, int) else v for v in e[k]]
                    for k in ("o", "ow", "sc"):
                        if k in e:
                            e[k] = [oc[k][e[k][0]] if isinstance(e[k][0], int) else e[k][0], w(ow_[e[k][1]])]
                    for t in e.get("tp") or []:
                        t[2] = w(ow_[t[2]])
                    for k in ("aw", "uw"):
                        if k in e:
                            e[k] = [w(ow_[x]) for x in e[k]]
                    if "rc" in e:
                        e["rc"] = {c: w(ow_[x]) for c, x in e["rc"].items()}
                    e.setdefault("f", oc.get("f"))
                    origin = re.sub(r"^(https?://[^/]+).*$", r"\1", e.get("w") or "")
                    if e.get("cp", "").startswith("/"):
                        e["cp"] = origin + e["cp"]
                    for t in e.get("tp") or []:
                        if len(t) >= 5 and str(t[4]).startswith("/"):
                            t[4] = origin + t[4]
                    for k, u in list((e.get("so") or {}).items()):
                        if (oc.get("so") or {}).get(k) and not u.startswith("http"):
                            e["so"][k] = oc["so"][k].replace("{}", u)
                    e["ms"] = 1  # not found in the sources at the last update
                    out.append(e)
                    carried.append(e)
        shown_ids = {e["i"] for e in out}
        missing = {k: v for k, v in missing.items() if k in shown_ids and k not in all_ids}
        json.dump(missing, open(mf, "w", encoding="utf-8"), sort_keys=True, indent=0)
        (ROOT / "reports" / "missing_outlets.md").write_text("\n".join(
            ["# Outlets that are no longer in any source", "",
             f"Still shown with a note (first update without them): {len(carried)}. Removed now (update no. {keep_runs} without them): {len(removed)}.", "",
             "| Id | Name | Country | State |", "|---|---|---|---|"]
            + [f"| {e['i']} | {e['n'][:70]} | {e['c']} | still shown |" for e in carried]
            + [f"| {e['i']} | {e['n'][:70]} | {e['c']} | removed |" for e in removed]) + "\n", encoding="utf-8")
        out.sort(key=lambda e: (e["n"] or "").lower())
    from collections import Counter as _Counter
    stats = {"outlets": len(out), "ngos": len(ngo_out), "sources": dict(sorted(_Counter(s_ for e in out for s_ in e["s"]).items()))}
    codes = compact(out)  # repeated values -> short codes; the page expands them (finder.js expand())

    atlas_file = ROOT / "raw" / "atlas" / "data.json.gz"
    atlas = json.load(gzip.open(atlas_file, "rt", encoding="utf-8")) if atlas_file.exists() else {}
    regions = {}
    for c in countries:
        regions.setdefault(c["region"], set()).add(c["intermediate_region"] or c["subregion"])
    config = {
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "data_date": data_date,
        "countries": [{"iso3": c["iso3"], "name": c["name"], "aliases": c["aliases"], "status": c["status"],
                       "region": c["region"], "subregion": c["intermediate_region"] or c["subregion"],
                       "freedom": atlas.get(c["iso3"])}
                      for c in countries],
        "regions": {k: sorted(v) for k, v in sorted(regions.items())},
        "language_buttons": sorted(({"code": r["code"], "name": r["name"], "order": int(r["button"])}
                                    for r in langs_all.values() if r["button"]), key=lambda x: x["order"]),
        "languages": sorted(({"code": c, "name": langs_all[c]["name"]} for c in used_langs if c in langs_all),
                            key=lambda x: x["name"]),
        "categories": {k: cats[k] for k in ("material", "org_type", "channel", "ownership", "scope",
                                             "topic_groups", "topics", "audience", "un_profile", "social_platform", "size", "checkboxes", "sort")},
        "size_note": cats.get("size_note"),
        "new_months": cats.get("new_months", 4),
        "active_months": cats.get("active_months", 3),
        "feedback_email": cats.get("feedback_email"),
        "feedback_url": cats.get("feedback_url"),
        "topic_merge": topic_merge,  # old shared links: a merged topic id opens its new topic
        "topic_strength": cats.get("topic_strength"),
        "topic_strength_note": cats.get("topic_strength_note"),
        "source_labels": SOURCE_LABEL,
        # filters that get values in step 4 (classification)
        "networks": [{"id": k, "label": v} for k, v in NETWORK_FILTER.items()],
        "why": [t for t, _ in sorted(why.items(), key=lambda x: x[1])],
        "codes": codes,
        "ngo": {k: ngo_cfg[k] for k in ("un_status", "only_ecosoc_label", "hide_registered_label", "hq_only_label",
                                        "geo_scope", "page_hint", "page_title", "all_status_label", "un_partner", "org_kind")}
               | {"gc_status_note": yaml.safe_load(open(CFG / "sources" / "global_compact.yaml", encoding="utf-8"))["status_note"]}
               | {"type_of_work": [{"id": t["id"], "label": t["label"]} for t in ngo_cfg["type_of_work"]],
                  "count": len(ngo_out)},
    }
    data = ROOT / "site" / "data"
    data.mkdir(parents=True, exist_ok=True)
    # split into several files of at most 25,000 outlets (Cloudflare: max 25 MiB per file)
    for f in data.glob("outlets*.json"):
        f.unlink()
    files = []
    for i in range(0, len(out), 25000):
        name = f"outlets-{i // 25000 + 1}.json"
        json.dump(out[i:i + 25000], open(data / name, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        files.append(name)
    config["outlet_files"] = files
    for f in data.glob("ngos*.json"):
        f.unlink()
    nfiles = []
    for i in range(0, len(ngo_out), 25000):
        name = f"ngos-{i // 25000 + 1}.json"
        json.dump(ngo_out[i:i + 25000], open(data / name, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        nfiles.append(name)
    config["ngo_files"] = nfiles
    json.dump(config, open(data / "config.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    # numbers for the safety brake of the automatic update (pipeline/automation/safety_brake.py)
    json.dump({**stats, "built": config["built"]}, open(data / "stats.json", "w", encoding="utf-8"), indent=1)
    # scripts and styles get the build time as version, so browsers load the new ones after an update
    import re as _re
    ver = config["built"].replace(" ", "").replace(":", "")
    for idx in (ROOT / "site" / "index.html", ROOT / "site" / "ngos.html"):  # media page and NGO page
        if not idx.exists():
            continue
        html = idx.read_text(encoding="utf-8")
        html = _re.sub(r'(assets/[a-z\-]+\.(?:js|css))(\?v=[^"]*)?"', lambda m: f'{m.group(1)}?v={ver}"', html)
        idx.write_text(html, encoding="utf-8")
    sizes = ", ".join(f"{f} {(data / f).stat().st_size / 1e6:.1f} MB" for f in files)
    print(f"site/data: {len(out)} outlets in {len(files)} files ({sizes}); {len(ngo_out)} NGOs in {len(nfiles)} files")


if __name__ == "__main__":
    main()
