"""Step 3a: brings every source into one common record format.

Output: work/records.json, one record per entry in a source:
  key            stable source key: wd:Q123, rb:<uuid>, iptv:<id>, mc:<id>
  source         wikidata | radio_browser | iptv_org | media_cloud
  name, alt_names, website, domain, country (ISO alpha-3), languages (ISO 639-3)
  channels       channel evidence from this source (ids from categories.yaml)
  include        True / False / "needs_confirmation" (+ include_reason)
  raw            the source's own classes / tags / categories, for the classifier
  ... plus source-specific fields (wikipedia title, social accounts, owner, ...)
Records outside the 195 countries are dropped here (reported).
"""
import csv
import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from countrymatch import to_iso3  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "raw"
CFG = ROOT / "config"


def load_gz(path):
    return json.load(gzip.open(path, "rt", encoding="utf-8"))


# ------------------------------------------------------------------ helpers
COUNTRIES = {r["iso3"]: r for r in csv.DictReader(open(CFG / "countries.csv", encoding="utf-8"))}
ISO2 = {r["iso2"]: r["iso3"] for r in COUNTRIES.values()}


class Languages:
    def __init__(self):
        rows = list(csv.DictReader(open(CFG / "languages.csv", encoding="utf-8")))
        extra = yaml.safe_load(open(CFG / "sources" / "language_names.yaml", encoding="utf-8"))
        self.codes = {r["code"] for r in rows}
        self.macro = extra.get("into_macrolanguage") or {}
        self.by_name = {r["name"].lower(): r["code"] for r in rows}
        self.by_name.update({k.lower(): v for k, v in (extra.get("names") or {}).items()})
        self.by_two = {r["iso639_1"]: r["code"] for r in rows if r["iso639_1"]}
        self.ignore = {x.lower() for x in extra.get("ignore") or []}
        self.unmatched = Counter()

    def code(self, value):
        v = (value or "").strip()
        if not v or v.lower() in self.ignore:
            return None
        low = v.lower()
        c = (low if low in self.codes and len(low) == 3 else None) or self.by_two.get(low) or self.by_name.get(low)
        if not c:
            self.unmatched[v] += 1
            return None
        return self.macro.get(c, c)

    def codes_of(self, values):
        out = []
        for v in values:
            c = self.code(v)
            if c and c not in out:
                out.append(c)
        return out


LANG = Languages()


def norm_url(url):
    url = (url or "").strip()
    if not url:
        return None, None
    if "://" not in url:
        url = "http://" + url
    try:
        parts = urlsplit(url)
    except ValueError:
        return None, None
    host = (parts.hostname or "").lower()
    if not host or "." not in host:
        return None, None
    host = re.sub(r"^(www\d?|m|mobile|amp)\.", "", host)
    path = parts.path.rstrip("/")
    return url, host + (path if path else "")


def tags_of(text):
    return [t.strip().lower() for t in (text or "").split(",") if t.strip()]


# ------------------------------------------------------------------ Wikidata
WD_CHANNELS = {"Q14350": "radio", "Q1616075": "tv", "Q2001305": "tv", "Q11032": "print",
               "Q41298": "print", "Q1153191": "website", "Q17232649": "website", "Q24634210": "podcast"}


ONLINE_ONLY = {"online newspaper", "news website", "online magazine", "digital newspaper", "news portal",
               "online publication", "website", "blog", "news aggregation website", "web portal",
               "publication by electronic means", "Internet television", "web broadcaster", "YouTube channel"}


def wikidata():
    cfg = yaml.safe_load(open(CFG / "sources" / "wikidata.yaml", encoding="utf-8"))
    exclude = {c["qid"]: c["label"] for c in cfg.get("exclude_classes", [])}
    labels = json.load(open(RAW / "wikidata" / "linked_labels.json", encoding="utf-8"))
    out = []
    for r in load_gz(RAW / "wikidata" / "data.json.gz"):
        names = r.get("labels", {})
        name = names.get("en") or next(iter(names.values()), None)
        if not name:
            continue
        classes = r.get("instance_of", [])
        if r.get("dissolved") or r.get("date_of_closure"):
            include, why = False, "dissolved / closed (Wikidata)"
        elif set(classes) & set(exclude):
            include, why = False, "class excluded: " + ", ".join(exclude[c] for c in classes if c in exclude)
        else:
            include, why = True, "media class in Wikidata"
        countries = [c for c in r.get("matched_countries", []) if c in COUNTRIES]
        website, domain = norm_url((r.get("website") or [None])[0])
        channels = sorted({WD_CHANNELS[c] for c in r.get("matched_classes", []) if c in WD_CHANNELS})
        direct = {labels.get(c) for c in classes}
        if direct & ONLINE_ONLY:
            channels = sorted((set(channels) - {"print"}) | {"website"})  # online-only: not print
        social = {k: r[f] for k, f in (("youtube", "youtube_channel_id"), ("facebook", "facebook_id"),
                                       ("instagram", "instagram_username"), ("tiktok", "tiktok_username"),
                                       ("x", "x_username"), ("telegram", "telegram_username")) if r.get(f)}
        lang_names = [labels.get(q) or q for q in r.get("language_of_work", []) + r.get("original_language", [])]
        out.append({
            "key": f"wd:{r['qid']}", "source": "wikidata", "qid": r["qid"],
            "name": name, "alt_names": sorted({v for v in names.values() if v != name})[:10],
            "website": website, "domain": domain,
            "country": countries[0] if countries else None, "other_countries": countries[1:],
            "languages": LANG.codes_of(lang_names),
            "multiple_languages": any((labels.get(q) or "") == "multiple languages" for q in r.get("language_of_work", [])),
            "channels": channels, "social": social,
            "email": (r.get("email") or [None])[0],
            "wikipedia": (r.get("wikipedia_titles") or {}).get("enwiki"),
            "wikipedia_languages": r.get("wikipedia_languages", 0),
            "raw": {"classes": [labels.get(c) or c for c in classes],
                    "owned_by": [labels.get(c) or c for c in r.get("owned_by", [])],
                    "parent": [labels.get(c) or c for c in r.get("parent_organization", [])],
                    "member_of": [labels.get(c) or c for c in r.get("member_of", [])],
                    "main_subject": [labels.get(c) or c for c in r.get("main_subject", [])],
                    "genre": [labels.get(c) or c for c in r.get("genre", [])],
                    "operating_area": [labels.get(c) or c for c in r.get("operating_area", [])],
                    "owned_by_qid": r.get("owned_by", []), "parent_qid": r.get("parent_organization", []),
                    "class_qids": classes},
            "include": include, "include_reason": why,
        })
    return out


# ------------------------------------------------------------- Radio Browser
def radio_browser():
    cfg = yaml.safe_load(open(CFG / "sources" / "radio_browser.yaml", encoding="utf-8"))
    inc = set(cfg["include_tags"])
    out = []
    for s in load_gz(RAW / "radio_browser" / "data.json.gz"):
        tags = tags_of(s.get("tags"))
        hit = sorted(inc & set(tags))
        if hit:
            include, why = True, "information tag: " + ", ".join(hit[:3])
        elif not tags:
            include, why = "needs_confirmation", "no tags: kept only if another source confirms it"
        else:
            include, why = False, "no information tag"
        website, domain = norm_url(s.get("homepage"))
        out.append({
            "key": f"rb:{s['stationuuid']}", "source": "radio_browser",
            "name": (s.get("name") or "").strip(), "alt_names": [],
            "website": website, "domain": domain,
            "country": ISO2.get((s.get("countrycode") or "").upper()), "other_countries": [],
            "region_text": s.get("state") or None,
            "languages": LANG.codes_of((s.get("languagecodes") or "").split(",")),
            "channels": ["radio"], "social": {},
            "popularity": {"votes": s.get("votes"), "clicks": s.get("clickcount")},
            "stream_ok": bool(s.get("lastcheckok")),
            "raw": {"tags": tags},
            "include": include, "include_reason": why,
        })
    return out


# ------------------------------------------------------------------ iptv-org
def iptv_org():
    cfg = yaml.safe_load(open(CFG / "sources" / "iptv_org.yaml", encoding="utf-8"))
    inc = set(cfg["include_categories"])
    out = []
    for c in load_gz(RAW / "iptv_org" / "data.json.gz"):
        cats = c.get("categories") or []
        if c.get("closed"):
            include, why = False, f"closed {c['closed']} (iptv-org)"
        elif inc & set(cats):
            include, why = True, "category: " + ", ".join(sorted(inc & set(cats)))
        elif not cats:
            include, why = "needs_confirmation", "no category: kept only if another source confirms it"
        else:
            include, why = False, "category not included: " + ", ".join(cats)
        langs, areas = [], []
        for f in c.get("feeds", []):
            langs += f.get("languages") or []
            areas += f.get("broadcast_area") or []
        website, domain = norm_url(c.get("website"))
        out.append({
            "key": f"iptv:{c['id']}", "source": "iptv_org",
            "name": c.get("name") or c["id"], "alt_names": c.get("alt_names") or [],
            "website": website, "domain": domain,
            "country": ISO2.get((c.get("country") or "").upper()), "other_countries": [],
            "city": c.get("city"),
            "languages": LANG.codes_of(langs),
            "channels": ["tv"], "social": {},
            "raw": {"categories": cats, "broadcast_area": sorted(set(areas)),
                    "owners": c.get("owners") or [], "network": c.get("network")},
            "include": include, "include_reason": why,
        })
    return out


# --------------------------------------------------------------- Media Cloud
MC_CHANNELS = {"print_native": ["print", "website"], "digital_native": ["website"],
               "video_broadcast": ["tv", "website"], "audio_broadcast": ["radio", "website"]}


def media_cloud():
    folder = RAW / "media_cloud"
    collections = {r["id"]: r["name"] for r in csv.DictReader(gzip.open(folder / "geographic_collections.csv.gz", "rt", encoding="utf-8"))}
    member = {}
    for r in csv.DictReader(gzip.open(folder / "geographic_collection_to_media_source.csv.gz", "rt", encoding="utf-8")):
        member.setdefault(r["source_id"], []).append(collections.get(r["collection_id"], ""))
    out = []
    for s in csv.DictReader(gzip.open(folder / "media_sources.csv.gz", "rt", encoding="utf-8")):
        cols = member.get(s["id"], [])
        country = s["pub_country"] if s["pub_country"] in COUNTRIES else None
        if not country:  # fall back to the country named in its collections ("Kenya - National")
            names = {re.sub(r"^.*?,\s*", "", c.rsplit(" - ", 1)[0]) for c in cols}
            isos = {to_iso3(n) for n in names} - {None}
            country = isos.pop() if len(isos) == 1 else None
        website, domain = norm_url(s.get("homepage") or ("http://" + s["name"] if "." in s["name"] else ""))
        out.append({
            "key": f"mc:{s['id']}", "source": "media_cloud",
            "name": s.get("label") or s["name"], "alt_names": [s["name"]] if s.get("label") else [],
            "website": website, "domain": domain,
            "country": country, "other_countries": [],
            "region_text": s.get("pub_state") or None,
            "languages": LANG.codes_of([s.get("primary_language")]),
            "channels": MC_CHANNELS.get(s.get("media_type"), ["website"]), "social": {},
            "stories_per_week": int(s["stories_per_week"]) if (s.get("stories_per_week") or "").isdigit() else None,
            "raw": {"collections": cols, "media_type": s.get("media_type")},
            "include": True, "include_reason": "news source in Media Cloud",
        })
    return out


def main():
    all_records, report = [], ["# Step 3a: records per source", "",
                               "| Source | In file | Outside the 195 / no country | Included | Needs confirmation | Excluded |",
                               "|---|---|---|---|---|---|"]
    for name, fn in (("wikidata", wikidata), ("radio_browser", radio_browser),
                     ("iptv_org", iptv_org), ("media_cloud", media_cloud)):
        recs = fn()
        kept = [r for r in recs if r["country"]]
        inc = Counter(str(r["include"]) for r in kept)
        report.append(f"| {name} | {len(recs)} | {len(recs) - len(kept)} | {inc['True']} | "
                      f"{inc['needs_confirmation']} | {inc['False']} |")
        all_records += kept
    report += ["", "Language values not recognised (top 30; add to config/sources/language_names.yaml):", ""]
    report += [f"- {k} ({n})" for k, n in LANG.unmatched.most_common(30)] or ["- none"]
    (ROOT / "work").mkdir(exist_ok=True)
    json.dump(all_records, open(ROOT / "work" / "records.json", "w", encoding="utf-8"), ensure_ascii=False)
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "records.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
