"""Disinformation monitor: find fact-checkers worldwide and their feeds, without hand work.

1. Wikidata (open): organisations that are instances of "fact-checking organization/website" with official website and country.
2. For each website: read the home page and look for the feed the site itself announces
   (<link rel="alternate" type="application/rss+xml">). This is the standard, intended way to find a feed.
3. The feed is tested (must contain items). Result is saved in cache/desinfo_feeds.json; the daily run
   (pipeline/fetch/desinfo.py) then reads every feed that works.

Rules of politeness: our own honest user agent only; robots.txt is respected; a site that answers 403 / refuses is
NOT retried for 90 days and never worked around; at most `discover_max_sites` sites per run, one request per second.
Settings: config/desinfo.yaml section `discovery`.
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import date, datetime, timedelta, timezone

import yaml

from common import ROOT, USER_AGENT, get
from desinfo import fetch_feed_text, feed_items  # noqa: E402 - same folder

CFG = yaml.safe_load(open(ROOT / "config" / "desinfo.yaml", encoding="utf-8"))["discovery"]
KNOWN = {f["domain"] for f in yaml.safe_load(open(ROOT / "config" / "factcheck_sources.yaml", encoding="utf-8"))["feeds"]}
CACHE = ROOT / "cache" / "desinfo_feeds.json"
SPARQL = "https://query.wikidata.org/sparql"
QUERY = """
SELECT DISTINCT ?item ?itemLabel ?site ?iso ?iso2 WHERE {
  VALUES ?lbl { %s }
  ?class rdfs:label ?lbl .
  ?item wdt:P31 ?class .
  ?item wdt:P856 ?site .
  OPTIONAL { ?item wdt:P17 ?c . ?c wdt:P297 ?iso . }
  OPTIONAL { ?item wdt:P495 ?c2 . ?c2 wdt:P297 ?iso2 . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,es,fr,pt,ar,ru,zh,hi,sw". }
}
"""


def domain_of(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    return host.removeprefix("www.")


def wikidata_sites():
    labels = " ".join(f'"{l}"@en' for l in CFG["wikidata_class_labels"])
    body = get(SPARQL, {"query": QUERY % labels, "format": "json"}, accept="application/sparql-results+json",
               timeout=120, tries=3)
    out = {}
    for r in json.loads(body)["results"]["bindings"]:
        site = r["site"]["value"]
        d = domain_of(site)
        if not d or d in KNOWN or d in out:
            continue
        out[d] = {"name": r["itemLabel"]["value"], "site": site,
                  "country": (r.get("iso") or r.get("iso2") or {}).get("value", "")}
    return out


_robots = {}


def allowed(url):
    host = urllib.parse.urlparse(url)
    key = host.scheme + "://" + host.netloc
    if key not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(key + "/robots.txt", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as r:
                rp.parse(r.read().decode("utf-8", "replace").splitlines())
        except Exception:  # noqa: BLE001 - no robots.txt or unreachable: treat as allowed
            rp = None
        _robots[key] = rp
    rp = _robots[key]
    return True if rp is None else rp.can_fetch(USER_AGENT, url)


def home_page(url):
    """(html, status). status: ok / blocked / error"""
    if not allowed(url):
        return "", "blocked"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read(600_000).decode("utf-8", "replace"), "ok"
    except urllib.error.HTTPError as e:
        return "", "blocked" if e.code in (401, 403, 429) else "error"
    except Exception:  # noqa: BLE001
        return "", "error"


def feed_links(html, base):
    links = []
    for tag in re.findall(r"<link\b[^>]*>", html, flags=re.I):
        if re.search(r'rel=["\']?alternate', tag, re.I) and re.search(r'type=["\']?application/(rss|atom)\+xml', tag, re.I):
            m = re.search(r'href=["\']([^"\']+)["\']', tag, re.I)
            if m:
                links.append(urllib.parse.urljoin(base, m.group(1).replace("&amp;", "&")))
    # prefer the main feed over comment feeds
    links.sort(key=lambda u: ("comment" in u.lower(), len(u)))
    return links


def main():
    cache = json.load(open(CACHE, encoding="utf-8")) if CACHE.exists() else {}
    try:
        sites = wikidata_sites()
    except Exception as e:  # noqa: BLE001
        print("Wikidata query failed:", e)
        sites = {}
    print(f"Wikidata: {len(sites)} fact-checking websites (not in the hand list)")
    today = date.today()
    todo = []
    for d, info in sites.items():
        c = cache.get(d)
        if c and c.get("retry_after", "") > today.isoformat():
            continue
        if c and c.get("status") == "ok":
            continue
        todo.append((d, info))
    todo.sort(key=lambda x: (x[1]["country"] == "", x[1]["country"]))   # countries first, then unknown
    n_ok = 0
    for d, info in todo[:CFG["discover_max_sites"]]:
        html, st = home_page(info["site"])
        rec = {"name": info["name"], "site": info["site"], "country": info["country"], "checked": today.isoformat(),
               "feed": "", "lang": "", "status": st, "fails": 0}
        if st == "ok":
            m = re.search(r"<html[^>]*\blang=[\"']?([a-zA-Z]{2})", html)
            rec["lang"] = m.group(1).lower() if m else ""
            rec["status"] = "no_feed"
            for link in feed_links(html, info["site"])[:2]:
                if not allowed(link):
                    continue
                try:
                    got = feed_items({"url": link, "lang": rec["lang"] or "en", "name": info["name"], "domain": d,
                                      "country": info["country"]})
                except Exception:  # noqa: BLE001
                    got = []
                if got:
                    rec.update(feed=link, status="ok")
                    n_ok += 1
                    break
        if rec["status"] != "ok":
            days = 90 if rec["status"] == "blocked" else 30
            rec["retry_after"] = (today + timedelta(days=days)).isoformat()
        cache[d] = rec
        time.sleep(1)
    CACHE.parent.mkdir(exist_ok=True)
    json.dump(dict(sorted(cache.items())), open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    ok_total = sum(1 for c in cache.values() if c["status"] == "ok")
    print(f"checked {min(len(todo), CFG['discover_max_sites'])} sites, new feeds {n_ok}, feeds in total {ok_total}")


if __name__ == "__main__":
    main()
