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


def fetch_source(src):
    feed = {"url": src["url"], "lang": src["lang"], "name": src["agency"], "domain": "", "country": ""}
    try:
        return feed_items(feed), src["url"], ""
    except Exception as e:  # noqa: BLE001 - try the feed announced on the site
        err = str(e)[:120]
    html, st = home_page(src["site"])
    if st == "ok":
        for link in feed_links(html, src["site"])[:2]:
            if allowed(link):
                try:
                    return feed_items({**feed, "url": link}), link, ""
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
