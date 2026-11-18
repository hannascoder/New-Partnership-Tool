"""One-off: give the content-gap check a deeper UN archive by reading OLD copies of the UN feeds from the Internet Archive
(Wayback Machine, public and free; honest user agent, 1 request per second, capped).

Why: an RSS feed only shows its newest ~30 items, so our own archive starts on the day we began collecting (30.09.2026).
The Wayback Machine kept copies of the same feeds; every copy lists the items of that day. Items older than 12 months are ignored.
Feeds: config/un_sources.yaml (UN News in 6 languages, topic feeds, WHO). Result: raw/un_archive/ (read by pipeline/desinfo/build_un.py).
Start: Actions -> "UN archive backfill" -> Run workflow.
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

import yaml

from common import ROOT, USER_AGENT, save
from desinfo import feed_items_from_text

LANGS = {"en", "es", "fr", "pt", "ar", "hi"}
MAX_FETCHES = 2000
PAUSE = 1.1
FEEDS = [f for f in yaml.safe_load(open(ROOT / "config" / "un_sources.yaml", encoding="utf-8"))["feeds"]
         if f["lang"] in LANGS and (f["agency"].startswith("UN News") or f["agency"] == "WHO")]


def http(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def snapshots(feed_url, step_days):
    """Timestamps of the saved copies of a feed over the last 12 months, thinned to one every `step_days` days."""
    today = date.today()
    q = urllib.parse.urlencode({"url": feed_url, "output": "json", "fl": "timestamp", "filter": "statuscode:200",
                                "from": (today - timedelta(days=365)).strftime("%Y%m%d"), "to": today.strftime("%Y%m%d"),
                                "collapse": "timestamp:8"})
    rows = json.loads(http("https://web.archive.org/cdx/search/cdx?" + q))[1:]
    out, last = [], None
    for (ts,) in rows:
        d = date(int(ts[:4]), int(ts[4:6]), int(ts[6:8]))
        if last is None or (d - last).days >= step_days:
            out.append(ts)
            last = d
    return out


def main():
    items, status, fetches = {}, {}, 0
    for f in FEEDS:
        key = f'{f["agency"]} ({f["lang"]})'
        step = 6 if f["agency"] == "WHO" or "topic" not in f["url"] else 12      # the all-news feed spans ~1-2 days, topic feeds weeks
        try:
            snaps = snapshots(f["url"], step)
        except Exception as e:  # noqa: BLE001
            status[key] = {"ok": False, "copies": 0, "items": 0, "error": str(e)[:100]}
            time.sleep(PAUSE)
            continue
        got = 0
        for ts in snaps:
            if fetches >= MAX_FETCHES:
                break
            fetches += 1
            try:
                body = http(f"https://web.archive.org/web/{ts}id_/{f['url']}")
                for it in feed_items_from_text(body, {"url": f["url"], "lang": f["lang"], "name": f["agency"], "domain": "", "country": ""}):
                    it["agency"] = f["agency"]
                    if it["url"] not in items:
                        items[it["url"]] = it
                        got += 1
            except Exception:  # noqa: BLE001 - a missing copy is normal
                pass
            time.sleep(PAUSE)
        status[key] = {"ok": got > 0, "copies": len(snaps), "items": got, "error": ""}
        print(key, len(snaps), "copies,", got, "new items", flush=True)
    if items:
        save("un_archive", list(items.values()), {"status": status, "fetches": fetches})
    else:
        print("nothing found")


if __name__ == "__main__":
    main()
