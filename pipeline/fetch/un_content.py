"""Disinformation monitor, content-gap check: fetch the public news feeds of the UN and its agencies.

Feeds: config/un_sources.yaml. If a feed address does not work, the feed that the site announces on its home page
is used (standard feed autodiscovery, robots.txt respected). Raw result: raw/un_content/ (items of this run).
The memory of 12 months and the topic assignment are built by pipeline/desinfo/build_un.py.
"""
import time

import yaml

from common import ROOT, save
from desinfo import feed_items
from desinfo_discover import allowed, feed_links, home_page

SOURCES = yaml.safe_load(open(ROOT / "config" / "un_sources.yaml", encoding="utf-8"))["feeds"]


COMMON_PATHS = ["/feed", "/feed/", "/rss", "/rss.xml", "/news/rss.xml", "/rss/news"]


def candidate_feeds(src):
    """The configured address, then the feed the site announces on its pages (section page, then home page),
    then the usual feed locations on the site's own domain. All politely (robots.txt), in this order."""
    seen, out = set(), []

    def add(u):
        if u not in seen:
            seen.add(u)
            out.append(u)

    add(src["url"])
    root = "/".join(src["site"].split("/")[:3])
    for page in dict.fromkeys([src["site"], root + "/"]):
        html, st = home_page(page)
        if st == "ok":
            for link in feed_links(html, page)[:2]:
                add(link)
    for path in COMMON_PATHS:
        add(root + path)
    return out


def fetch_source(src):
    feed = {"url": src["url"], "lang": src["lang"], "name": src["agency"], "domain": "", "country": ""}
    try:
        return feed_items(feed), src["url"], ""
    except Exception as e:  # noqa: BLE001 - try the feeds the site announces
        err = str(e)[:120]
    for link in candidate_feeds(src)[1:]:
        if not allowed(link):
            continue
        try:
            got = feed_items({**feed, "url": link})
            if got:
                return got, link, "(address found automatically)"
        except Exception as e:  # noqa: BLE001
            err = str(e)[:120]
    return [], src["url"], err


def main():
    items, status = [], {}
    for src in SOURCES:
        got, used, err = fetch_source(src)
        for g in got:
            g["agency"] = src["agency"]
        items += got
        status[f'{src["agency"]} ({src["lang"]})'] = {"ok": bool(got), "items": len(got), "url": used, "error": err}
        time.sleep(1)
    if not items:
        print("no UN items fetched - keeping the previous raw data")
        return
    save("un_content", items, {"status": status})


if __name__ == "__main__":
    main()
