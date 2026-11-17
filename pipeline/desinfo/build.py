"""Disinformation monitor, step D1b: raw fact-checks -> items, topics, countries, daily counts.

Input : raw/desinfo (items of the last fetch), raw/desinfo_atlas (183 topics, Google Trends per country)
Memory: cache/desinfo_items.json (single items, kept `keep_days`), cache/desinfo_series.json (daily counts, kept for good)
Output: site/data/desinfo/items.json, series.json, topics.json, trends.json, summary.json
        reports/desinfo_sources.md, reports/desinfo_coverage.md
No AI: topics are found by the topic titles in many languages (Atlas topic list), countries by the
fact-checker's country (config/factcheck_sources.yaml, else the country code of its web address).
The text of a claim is only used for matching and is NOT published (owner's decision 17.11.2026).
"""
import csv
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CFG = yaml.safe_load(open(ROOT / "config" / "desinfo.yaml", encoding="utf-8"))
FEEDS = yaml.safe_load(open(ROOT / "config" / "factcheck_sources.yaml", encoding="utf-8"))["feeds"]
OUT = ROOT / "site" / "data" / "desinfo"
CACHE = ROOT / "cache"


def load_gz(name):
    p = ROOT / "raw" / name / "data.json.gz"
    if not p.exists():
        return None
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return json.load(f)


def load_json(p, default):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def countries():
    with open(ROOT / "config" / "countries.csv", encoding="utf-8") as f:
        return {r["iso2"]: r for r in csv.DictReader(f)}


# ---------- matching ----------
def norm(s):
    return " " + re.sub(r"[^\w]+", " ", (s or "").lower()).strip() + " "


class TopicMatcher:
    """Topic titles (all languages in the Atlas list) plus the extra words of
    config/desinfo_topic_synonyms.yaml, found as whole words (word* = word start) in a text."""

    def __init__(self, topics):
        syn = yaml.safe_load(open(ROOT / "config" / "desinfo_topic_synonyms.yaml", encoding="utf-8"))["synonyms"]
        self.entries = []   # (qid, [normalised phrase])
        for t in topics:
            phrases = set()
            for title in list((t.get("titles") or {}).values()) + [t.get("label_en", "")]:
                title = re.sub(r"\s*\(.*?\)\s*", " ", title or "").strip()   # drop "(disambiguation)"
                if len(title) >= 4 or (title.isupper() and len(title) >= 3):
                    phrases.add(norm(title))
            for w in syn.get(t.get("label_en"), []):
                core = norm(w.rstrip("*"))
                if len(w.rstrip("*").strip()) >= 2:
                    phrases.add(core.rstrip() if w.endswith("*") else core)
            self.entries.append((t["qid"], sorted(phrases)))

    def match(self, text):
        n = norm(text)
        return [qid for qid, phrases in self.entries if any(p in n for p in phrases)]


def un_flag(text):
    for a in CFG["un_acronyms"]:
        if re.search(r"(?<![\w])" + re.escape(a) + r"(?![\w])", text):
            return True
    low = text.lower()
    return any(n.lower() in low for n in CFG["un_names"])


class CountryMatcher:
    """Countries MENTIONED in a text: English names and aliases (config/countries.csv), local spellings
    (config/desinfo.yaml about_aliases). Longest names first and removed after matching, so "Equatorial Guinea"
    is not also "Guinea". Short upper-case aliases (USA, UK, UAE ...) are matched case-sensitively."""

    def __init__(self, valid):
        skip = {norm(x) for x in CFG.get("about_skip_names", [])}
        names = []                                   # (normalised name, iso2)
        self.acr = dict(CFG.get("about_acronyms", {}))
        for iso, r in valid.items():
            cand = [re.sub(r"\s*\(.*?\)", "", r["name"]).strip()] + [a.strip() for a in r["aliases"].split(";") if a.strip()]
            cand += [str(a) for a in (CFG.get("about_aliases", {}).get(iso) or [])]
            for c in cand:
                if c.isupper() and len(c) <= 4:
                    self.acr.setdefault(c, iso)
                elif len(c) >= 4 and norm(c) not in skip:
                    names.append((norm(c), iso))
        self.names = sorted(set(names), key=lambda x: -len(x[0]))
        self.acr_re = [(re.compile(r"(?<![\w.])" + re.escape(a) + r"(?![\w])"), iso) for a, iso in self.acr.items()]

    def match(self, text):
        found = set()
        for rx, iso in self.acr_re:
            if rx.search(text):
                found.add(iso)
        n = norm(text)
        for name, iso in self.names:
            if name in n:
                found.add(iso)
                n = n.replace(name, " ")
        return sorted(found)[:6]


def country_of(item, domain_map, valid):
    if item.get("country") in valid:
        return item["country"], "feed"
    d = item.get("domain", "")
    if d in domain_map and domain_map[d] in valid:
        return domain_map[d], "feed"
    tld = d.rsplit(".", 1)[-1].upper() if "." in d else ""
    tld = {"UK": "GB"}.get(tld, tld)
    if len(tld) == 2 and tld in valid:
        return tld, "domain"
    return "", ""


# ---------- main ----------
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    valid = countries()
    atlas = load_gz("desinfo_atlas") or {}
    topics = (atlas.get("topics") or {}).get("topics") or []
    if not topics:
        raise SystemExit("no topic list (Atlas) - run pipeline/fetch/desinfo.py first")
    matcher = TopicMatcher(topics)
    cmatch = CountryMatcher(valid)
    domain_map = {f["domain"]: f["country"] for f in FEEDS if f["country"]}
    found = load_json(CACHE / "desinfo_feeds.json", {})
    domain_map.update({d: r["country"] for d, r in found.items() if r.get("status") == "ok" and r.get("country")})
    pub_map = {k.lower(): v for k, v in yaml.safe_load(
        open(ROOT / "config" / "factcheck_publishers.yaml", encoding="utf-8"))["publishers"].items()}

    memory = {i["id"]: i for i in load_json(CACHE / "desinfo_items.json", [])}
    translations = load_json(CACHE / "desinfo_translations.json", {})   # item id -> automatic English title
    fresh = load_gz("desinfo") or []
    new = 0
    for r in fresh:
        iid = hashlib.sha1(r["url"].encode()).hexdigest()[:12]
        cc, how = country_of(r, domain_map, valid)
        if not cc and pub_map.get(r["publisher"].lower()) in valid:
            cc, how = pub_map[r["publisher"].lower()], "publisher"
        if iid in memory:               # seen before: keep it, add what is new
            m = memory[iid]
            if not m["country"]:
                m["country"], m["country_from"] = cc, how
            m["claim"] = r.get("claim", "")
            m["qt"] = sorted(set(m.get("qt", [])) | set(r.get("qtopics", [])))
            m["unq"] = bool(m.get("unq") or r.get("unq"))
            continue
        if not r.get("date"):
            continue
        memory[iid] = {"id": iid, "date": r["date"], "title": r["title"], "url": r["url"],
                       "publisher": r["publisher"], "country": cc, "country_from": how, "lang": r["lang"],
                       "rating": r.get("rating", ""), "claim": r.get("claim", ""),
                       "qt": r.get("qtopics", []), "unq": bool(r.get("unq")), "topics": [], "un": False,
                       "src": r["src"]}
        new += 1
    # topics and UN flag are derived again at EVERY run from title + claim (+ topics the search engine found),
    # so a better rule in config/ improves the whole archive. The claim text stays in cache/ only, never on the site.
    for m in memory.values():
        text = m["title"] + " " + m.get("claim", "") + " " + translations.get(m["id"], "")
        m["topics"] = sorted(set(matcher.match(text)) | set(m.get("qt", [])))
        m["un"] = un_flag(text) or bool(m.get("unq"))
        m["about"] = cmatch.match(text)
    cutoff = (date.today() - timedelta(days=CFG["keep_days"])).isoformat()
    items = sorted((i for i in memory.values() if i["date"] >= cutoff), key=lambda i: i["date"], reverse=True)

    # daily counts are kept for good: rows [date, topic_qid ('' = all topics), iso2, un(0/1), n]
    # two views: by the country of the fact-checker ("publisher") and by the country the fact-check is about ("about")
    window = {i["date"] for i in items}

    def make_series(name, countries_of):
        series = defaultdict(int)
        for i in items:
            for q in (i["topics"] + [""]):
                for c in countries_of(i):
                    series[(i["date"], q, c, 1 if i["un"] else 0)] += 1
        old = load_json(CACHE / name, [])
        merged = [r for r in old if r[0] not in window]          # days no longer in the window stay as they were
        merged += [[d, q, c, u, n] for (d, q, c, u), n in sorted(series.items())]
        json.dump(merged, open(CACHE / name, "w"), separators=(",", ":"))
        return merged

    merged = make_series("desinfo_series.json", lambda i: [i["country"]])
    merged_about = make_series("desinfo_series_about.json", lambda i: i["about"] or [""])
    json.dump(items, open(CACHE / "desinfo_items.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    # site files
    topics_site = [{"qid": t["qid"], "label": t["label_en"], "group": t["category"]} for t in topics]
    json.dump({"generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "topics": topics_site,
               "languages": (atlas.get("topics") or {}).get("languages")},
              open(OUT / "topics.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    public = [{**{k: v for k, v in i.items() if k not in ("claim", "qt", "unq")}, **({"title_en": translations[i["id"]]} if translations.get(i["id"]) else {})} for i in items]
    json.dump(public, open(OUT / "items.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(merged, open(OUT / "series.json", "w"), separators=(",", ":"))
    json.dump(merged_about, open(OUT / "series_about.json", "w"), separators=(",", ":"))
    json.dump({r["iso2"]: {"name": r["name"], "region": r["region"],
                           "sub": r["intermediate_region"] or r["subregion"]} for r in valid.values()},
              open(OUT / "countries.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump({"red_marker": CFG["red_marker"], "keep_days": CFG["keep_days"], "gap": CFG["gap"],
               "suggestions": yaml.safe_load(open(ROOT / "config" / "desinfo_gap_suggestions.yaml", encoding="utf-8"))},
              open(OUT / "config.json", "w"), indent=1)
    # Google Trends per country (Atlas data, attribution "Data source: Google Trends"): only the query text and Google's bucket
    iso3 = {r["iso3"]: r["iso2"] for r in valid.values()}
    cs = (atlas.get("country_searches") or {}).get("countries") or {}
    trends = {iso3[k]: {"date": v.get("date"), "queries": [{"q": x["query"], "t": x.get("traffic", "")} for x in v.get("queries", [])[:6]]}
              for k, v in cs.items() if k in iso3 and not v.get("unsupported")}
    json.dump(trends, open(OUT / "trends.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    # reports
    by_country = Counter(i["country"] for i in items)
    unassigned = by_country.pop("", 0)
    by_topic = Counter(q for i in items for q in i["topics"])
    about_n = Counter(c for i in items for c in i["about"])
    summary = {"countries_mentioned": len(about_n), "items": len(items), "new_this_run": new, "countries_with_items": len(by_country),
               "unassigned_country": unassigned, "topics_with_items": len(by_topic), "topics_total": len(topics),
               "un_related": sum(1 for i in items if i["un"]),
               "first_date": items[-1]["date"] if items else None, "last_date": items[0]["date"] if items else None}
    json.dump(summary, open(OUT / "summary.json", "w"), indent=1)
    write_reports(valid, by_country, by_topic, topics, summary)
    print(json.dumps(summary))


def write_reports(valid, by_country, by_topic, topics, summary):
    meta = load_json(ROOT / "raw" / "desinfo" / "meta.json", {})
    st = meta.get("status") or load_json(ROOT / "raw" / "desinfo" / "last_failed_status.json", {})
    L = ["# Disinformation monitor: sources of the last run", "",
         f"Fetched: {meta.get('fetched_at', 'unknown')}  |  items in the site data: {summary['items']}", ""]
    g = st.get("google", {})
    L += ["## Google Fact Check Tools API", f"- {g}", "", "## Fact-checker feeds",
          "| Feed | Works | Items | Note |", "|---|---|---|---|"]
    for name, f in (st.get("feeds") or {}).items():
        L.append(f"| {name} | {'yes' if f.get('ok') else 'NO'} | {f.get('items', '')} | {f.get('error', '')} |")
    L += ["", "Feeds marked NO: correct or remove the address in `config/factcheck_sources.yaml`.", ""]
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "desinfo_sources.md").write_text("\n".join(L), encoding="utf-8")

    pop_rank = sorted(valid.values(), key=lambda r: r["name"])
    L = ["# Disinformation monitor: country coverage", "",
         f"Countries with at least one fact-check: **{summary['countries_with_items']} of {len(valid)}**. "
         f"Items without a country: {summary['unassigned_country']}. "
         f"Topics with items: {summary['topics_with_items']} of {summary['topics_total']}.", "",
         "## Countries WITHOUT data (to be covered: add fact-checker feeds in `config/factcheck_sources.yaml`)", ""]
    L += [", ".join(r["name"] for r in pop_rank if r["iso2"] not in by_country), "", "## Items per country", ""]
    L += [f"- {valid[c]['name']}: {n}" for c, n in by_country.most_common()]
    L += ["", "## Topics without any item", ""]
    L += [", ".join(t["label_en"] for t in topics if t["qid"] not in by_topic), ""]
    (ROOT / "reports" / "desinfo_coverage.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
