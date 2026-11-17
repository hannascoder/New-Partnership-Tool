"""Disinformation monitor, step D1: fetch fact-checks and the Atlas's public trend data.

Sources (all free; plan in docs/DESINFO_PLAN.md):
  1. Google Fact Check Tools API (free key in the secret GOOGLE_FACTCHECK_API_KEY; skipped without it)
  2. RSS/Atom feeds of fact-checkers listed in config/factcheck_sources.yaml
  3. Public Atlas data: topic list (183 topics) and Google Trends per country
Raw results go to raw/desinfo/ (fact-check items of THIS run) and raw/desinfo_atlas/.
One broken source never stops the run: its status is written to raw/desinfo/meta.json and
reports/desinfo_sources.md (built by pipeline/desinfo/build.py).
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime

import yaml

from common import ROOT, USER_AGENT, get, save

CFG = yaml.safe_load(open(ROOT / "config" / "desinfo.yaml", encoding="utf-8"))
FEEDS = yaml.safe_load(open(ROOT / "config" / "factcheck_sources.yaml", encoding="utf-8"))["feeds"]


def to_date(text):
    """Any common date format -> 'YYYY-MM-DD' (or '')."""
    text = (text or "").strip()
    if not text:
        return ""
    try:
        return parsedate_to_datetime(text).astimezone(timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        pass
    m = re.match(r"(\d{4}-\d{2}-\d{2})", text)
    return m.group(1) if m else ""


def clean(text, n=300):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()[:n]


# ---------- 1. Google Fact Check Tools API ----------
def google_queries(topics):
    """(query, language) pairs: every topic title in the chosen languages + UN terms."""
    seen, out = set(), []
    for t in topics:
        for lang in CFG["google_factcheck"]["topic_languages"]:
            title = (t.get("titles") or {}).get(lang) or (t.get("label_en") if lang == "en" else "")
            if title and (title.lower(), lang) not in seen:
                seen.add((title.lower(), lang))
                out.append((title, lang, t["qid"]))
    out += [(q, "en", "UN") for q in CFG["google_factcheck"]["un_queries"]]
    return out


def google_items(topics, key):
    g = CFG["google_factcheck"]
    items, errors, requests_made = {}, [], 0
    for query, lang, qid in google_queries(topics):
        if requests_made >= g["max_requests"]:
            errors.append("request limit reached")
            break
        params = {"query": query, "languageCode": lang, "maxAgeDays": g["max_age_days"],
                  "pageSize": g["page_size"], "key": key}
        url = g["endpoint"] + "?" + urllib.parse.urlencode(params)
        requests_made += 1
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403):       # key wrong / not enabled: stop at once, do not hammer
                errors.append(f"HTTP {e.code}: key invalid or Fact Check Tools API not enabled")
                break
            if e.code == 429:
                errors.append("HTTP 429: quota reached, stopped")
                break
            errors.append(f"HTTP {e.code} for '{query}'")
            continue
        except Exception as e:  # noqa: BLE001 - any network problem: skip this query
            errors.append(f"{type(e).__name__} for '{query}'")
            continue
        for c in data.get("claims", []):
            for rv in c.get("claimReview", []):
                url_ = rv.get("url")
                if url_ in items:                 # same fact-check found by another query: add its topic
                    if qid != "UN" and qid not in items[url_]["qtopics"]:
                        items[url_]["qtopics"].append(qid)
                    items[url_]["unq"] = items[url_]["unq"] or qid == "UN"
                    continue
                if not url_:
                    continue
                pub = rv.get("publisher") or {}
                items[url_] = {
                    "src": "google", "url": url_, "date": to_date(rv.get("reviewDate") or c.get("claimDate")),
                    "title": clean(rv.get("title"), 200), "claim": clean(c.get("text"), 200),
                    "rating": clean(rv.get("textualRating"), 60), "lang": rv.get("languageCode") or lang,
                    "publisher": pub.get("name", ""), "domain": (pub.get("site") or "").lower().removeprefix("www."),
                    # the search engine found it for this topic / UN query (extra evidence for the topic)
                    "qtopics": [] if qid == "UN" else [qid], "unq": qid == "UN",
                }
        time.sleep(g["pause_seconds"])
    return list(items.values()), {"requests": requests_made, "errors": errors[:20]}


# ---------- 2. RSS / Atom feeds ----------
def local(tag):
    return tag.rsplit("}", 1)[-1]


def feed_items(feed):
    body = get(feed["url"], accept="application/rss+xml, application/atom+xml, application/xml, text/xml",
               tries=2, timeout=40)
    root = ET.fromstring(body.encode("utf-8"))
    out = []
    for el in root.iter():
        if local(el.tag) not in ("item", "entry"):
            continue
        f = {local(c.tag): c for c in el}
        link = ""
        if "link" in f:
            link = f["link"].get("href") or (f["link"].text or "")
        title = clean(f["title"].text if "title" in f else "", 200)
        date = to_date(next((f[k].text for k in ("pubDate", "published", "updated", "date") if k in f), ""))
        if link and title:
            out.append({"src": "rss", "url": link.strip(), "date": date, "title": title,
                        "claim": clean(f["description"].text if "description" in f else "", 200),
                        "rating": "", "lang": feed["lang"], "publisher": feed["name"],
                        "domain": feed["domain"], "country": feed["country"]})
    return out


# ---------- 3. Atlas (public) ----------
def atlas():
    out = {}
    for name in CFG["atlas_files"]:
        try:
            out[name] = json.loads(get(CFG["atlas_base"] + "/" + name, timeout=180))
        except Exception as e:  # noqa: BLE001
            out[name] = None
            print(f"Atlas {name}: {e}")
    return out


def main():
    status = {}
    a = atlas()
    topics = (a.get("topics.json") or {}).get("topics") or []
    if a.get("topics.json"):
        save("desinfo_atlas", {"topics": a["topics.json"],
                               "country_searches": a.get("trends/country_searches.json")},
             {"url": CFG["atlas_base"], "licence": "Audience Intelligence Atlas data (public); Google Trends: "
              "Data source: Google Trends"})
    status["atlas"] = {"topics": len(topics), "country_searches": bool(a.get("trends/country_searches.json"))}

    items = []
    key = os.environ.get("GOOGLE_FACTCHECK_API_KEY", "").strip()
    if key and topics:
        got, info = google_items(topics, key)
        items += got
        status["google"] = {"items": len(got), **info}
    else:
        status["google"] = {"skipped": "no key" if not key else "no topic list"}

    status["feeds"] = {}
    for feed in FEEDS:
        try:
            got = feed_items(feed)
            items += got
            status["feeds"][feed["name"]] = {"ok": True, "items": len(got), "url": feed["url"]}
        except Exception as e:  # noqa: BLE001
            status["feeds"][feed["name"]] = {"ok": False, "error": str(e)[:160], "url": feed["url"]}
        time.sleep(1)

    if not items:
        print("no fact-check items fetched - keeping the previous raw data")
        (ROOT / "raw" / "desinfo").mkdir(parents=True, exist_ok=True)
        json.dump(status, open(ROOT / "raw" / "desinfo" / "last_failed_status.json", "w"), indent=1)
        return
    save("desinfo", items, {"status": status})


if __name__ == "__main__":
    main()
