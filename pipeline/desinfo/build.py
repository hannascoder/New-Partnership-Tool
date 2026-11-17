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
    """Topic titles (all languages in the Atlas list) found as whole words in a text."""

    def __init__(self, topics):
        self.entries = []   # (qid, [normalised phrase])
        for t in topics:
            phrases = set()
            for title in list((t.get("titles") or {}).values()) + [t.get("label_en", "")]:
                title = re.sub(r"\s*\(.*?\)\s*", " ", title or "").strip()   # drop "(disambiguation)"
                if len(title) >= 4 or (title.isupper() and len(title) >= 3):
                    phrases.add(norm(title))
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
    domain_map = {f["domain"]: f["country"] for f in FEEDS if f["country"]}

    memory = {i["id"]: i for i in load_json(CACHE / "desinfo_items.json", [])}
    fresh = load_gz("desinfo") or []
    new = 0
    for r in fresh:
        iid = hashlib.sha1(r["url"].encode()).hexdigest()[:12]
        if iid in memory or not r.get("date"):
            continue
        text = r["title"] + " " + r.get("claim", "")
        cc, how = country_of(r, domain_map, valid)
        memory[iid] = {"id": iid, "date": r["date"], "title": r["title"], "url": r["url"],
                       "publisher": r["publisher"], "country": cc, "country_from": how, "lang": r["lang"],
                       "rating": r.get("rating", ""), "topics": matcher.match(text), "un": un_flag(text),
                       "src": r["src"]}
        new += 1
    cutoff = (date.today() - timedelta(days=CFG["keep_days"])).isoformat()
    items = sorted((i for i in memory.values() if i["date"] >= cutoff), key=lambda i: i["date"], reverse=True)

    # daily counts are kept for good: rows [date, topic_qid ('' = all topics), iso2, un(0/1), n]
    series = defaultdict(int)
    for i in items:
        for q in (i["topics"] or [""]) + ([""] if i["topics"] else []):
            series[(i["date"], q, i["country"], 1 if i["un"] else 0)] += 1
    old = load_json(CACHE / "desinfo_series.json", [])
    window = {i["date"] for i in items}
    merged = [r for r in old if r[0] not in window]           # days no longer in the window stay as they were
    merged += [[d, q, c, u, n] for (d, q, c, u), n in sorted(series.items())]
    json.dump(merged, open(CACHE / "desinfo_series.json", "w"), separators=(",", ":"))
    json.dump(items, open(CACHE / "desinfo_items.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    # site files
    topics_site = [{"qid": t["qid"], "label": t["label_en"], "group": t["category"]} for t in topics]
    json.dump({"generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "topics": topics_site,
               "languages": (atlas.get("topics") or {}).get("languages")},
              open(OUT / "topics.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    json.dump(items, open(OUT / "items.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(merged, open(OUT / "series.json", "w"), separators=(",", ":"))
    json.dump({r["iso2"]: {"name": r["name"], "region": r["region"],
                           "sub": r["intermediate_region"] or r["subregion"]} for r in valid.values()},
              open(OUT / "countries.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump({"red_marker": CFG["red_marker"], "keep_days": CFG["keep_days"]},
              open(OUT / "config.json", "w"), indent=1)
    cs = (atlas.get("country_searches") or {})
    json.dump(cs, open(OUT / "trends.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    # reports
    by_country = Counter(i["country"] for i in items)
    unassigned = by_country.pop("", 0)
    by_topic = Counter(q for i in items for q in i["topics"])
    summary = {"items": len(items), "new_this_run": new, "countries_with_items": len(by_country),
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
