"""Disinformation monitor, content-gap check: fetch the public news feeds of the UN and its agencies.

Feeds: config/un_sources.yaml. If a feed address does not work, the feed that the site announces on its home page
is used (standard feed autodiscovery, robots.txt respected). Raw result: raw/un_content/ (items of this run).
The memory of 12 months and the topic assignment are built by pipeline/desinfo/build_un.py.
"""
import json
import time
from datetime import date

import yaml

from common import ROOT, save
from desinfo import feed_items
from desinfo_discover import allowed, feed_links, home_page

SOURCES = yaml.safe_load(open(ROOT / "config" / "un_sources.yaml", encoding="utf-8"))["feeds"]


COMMON_PATHS = ["/feed", "/rss.xml", "/rss"]
MEMORY = ROOT / "cache" / "un_feeds.json"        # per source: address that worked / when the search was last made
RETRY_DAYS = 30                                  # a source that cannot be found is searched again only this often
SEARCH_BUDGET_SECONDS = 300                      # all searches of one run together


def candidate_feeds(src):
    """The feed the site announces on its pages (section page, then home page), then the usual feed locations
    on the site's own domain. All politely (robots.txt), in this order."""
    out = []
    root = "/".join(src["site"].split("/")[:3])
    for page in dict.fromkeys([src["site"], root + "/"]):
        html, st = home_page(page)
        if st == "ok":
            out += [l for l in feed_links(html, page)[:2] if l not in out]
    out += [root + p for p in COMMON_PATHS if root + p not in out]
    return out


def try_feed(feed, url):
    try:
        got = feed_items({**feed, "url": url})
        return got
    except Exception as e:  # noqa: BLE001
        return str(e)[:120]


def fetch_source(src, memory, budget):
    key = f'{src["agency"]}|{src["lang"]}'
    feed = {"url": src["url"], "lang": src["lang"], "name": src["agency"], "domain": "", "country": ""}
    mem = memory.get(key, {})
    got = try_feed(feed, mem["url"]) if mem.get("ok") else try_feed(feed, src["url"])
    if isinstance(got, list) and got:
        return got, feed["url"] if not mem.get("ok") else mem["url"], ""
    err = got if isinstance(got, str) else "no items"
    if mem.get("ok") and src["url"] != mem["url"]:               # remembered address stopped working: try the configured one
        got = try_feed(feed, src["url"])
        if isinstance(got, list) and got:
            memory[key] = {"ok": False}
            return got, src["url"], ""
    today = date.today()
    recent = mem.get("checked") and (today - date.fromisoformat(mem["checked"])).days < RETRY_DAYS and not mem.get("ok")
    if recent or time.time() > budget["until"]:
        return [], src["url"], err + " (searched on " + str(mem.get("checked", "-")) + ", next search later)"
    for link in candidate_feeds(src):
        if link == src["url"] or not allowed(link):
            continue
        got = try_feed(feed, link)
        if isinstance(got, list) and got:
            memory[key] = {"ok": True, "url": link, "checked": today.isoformat()}
            return got, link, "(address found automatically)"
        err = got if isinstance(got, str) else err
    memory[key] = {"ok": False, "checked": today.isoformat()}
    return [], src["url"], err


def main():
    items, status = [], {}
    memory = json.load(open(MEMORY, encoding="utf-8")) if MEMORY.exists() else {}
    budget = {"until": time.time() + SEARCH_BUDGET_SECONDS}
    for src in SOURCES:
        got, used, err = fetch_source(src, memory, budget)
        for g in got:
            g["agency"] = src["agency"]
        items += got
        status[f'{src["agency"]} ({src["lang"]})'] = {"ok": bool(got), "items": len(got), "url": used, "error": err}
        time.sleep(1)
    MEMORY.parent.mkdir(exist_ok=True)
    json.dump(memory, open(MEMORY, "w", encoding="utf-8"), indent=0, sort_keys=True)
    if not items:
        print("no UN items fetched - keeping the previous raw data")
        return
    save("un_content", items, {"status": status})


if __name__ == "__main__":
    main()
