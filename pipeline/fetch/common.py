"""Shared helpers for the fetchers: downloading politely and saving raw data.

Every fetcher writes to raw/<source>/:
  data.json.gz   the records, already cut down to the fields we use
  meta.json      when it ran, how many records, which URLs, status
If a fetch fails, the previous files stay untouched (briefing K6:
"source fails -> keep the last good version").
"""
import csv
import gzip
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "raw"
USER_AGENT = ("UN-Partner-Finder/0.1 (internal research tool of the UN DGC "
              "Partnerships unit; https://github.com/hannascoder)")


def fresh(source, days):
    """True if raw/<source> was fetched less than `days` days ago.
    Lets slow sources (Wikidata takes about an hour) skip a re-run.
    Set FORCE_FETCH=1 to fetch anyway."""
    import os
    if os.environ.get("FORCE_FETCH") == "1":
        return False
    try:
        meta = json.load(open(RAW / source / "meta.json", encoding="utf-8"))
        when = datetime.strptime(meta["fetched_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - when).days < days
    except (OSError, KeyError, ValueError):
        return False


def countries():
    """The 195 allowed countries: {iso2: row}, from config/countries.csv."""
    with open(ROOT / "config" / "countries.csv", encoding="utf-8") as f:
        return {r["iso2"]: r for r in csv.DictReader(f)}


def get(url, params=None, accept="application/json", tries=4, timeout=120, data=None):
    """Download a URL and return the body as text. Retries with growing pauses."""
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={
                "User-Agent": USER_AGENT, "Accept": accept})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return body.decode("utf-8")
        except Exception as e:  # network error, timeout, HTTP 429/5xx ...
            last = e
            time.sleep(5 * (attempt + 1) ** 2)
    raise RuntimeError(f"failed after {tries} tries: {url[:200]} ({last})")


def save(source, records, meta):
    """Write raw/<source>/data.json.gz and meta.json."""
    folder = RAW / source
    folder.mkdir(parents=True, exist_ok=True)
    with gzip.open(folder / "data.json.gz", "wt", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, sort_keys=True, indent=0)
    meta = {"source": source,
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "records": len(records), **meta}
    with open(folder / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"{source}: saved {len(records)} records")
