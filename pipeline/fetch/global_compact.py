"""UN Global Compact participants (owner 13.11.2026), config/sources/global_compact.yaml.

1. the public participant list, page by page (/what-is-gc/participants?page=N): name, type, sector,
   country, joined; robots.txt forbids only the search pages, which are never used.
2. the profile page of each participant of an included type: website, status, participant since.
Resumes where the last run stopped (raw/global_compact/progress.json.gz). Saves often.
Environment: GC_MINUTES (time budget, default 600)."""
import gzip
import html as htmllib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW, ROOT, USER_AGENT, save  # noqa: E402

CFG = yaml.safe_load(open(ROOT / "config" / "sources" / "global_compact.yaml", encoding="utf-8"))
FOLDER = RAW / "global_compact"
STATE = FOLDER / "progress.json.gz"
START = time.time()
BUDGET = float(os.environ.get("GC_MINUTES", "600"))
ROW = re.compile(r"<tr>\s*<th class='notranslate name'><a href=\"([^\"]+)\">(.*?)</a></th>\s*<td class='type'>(.*?)</td>\s*"
                 r"<td class='sector'>(.*?)</td>\s*<td class='country'>(.*?)</td>\s*<td class='joined-on'>(.*?)</td>", re.S)


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def minutes():
    return (time.time() - START) / 60


def fetch(path, tries=3):
    url = CFG["base"] + path
    for i in range(tries):
        time.sleep(CFG.get("delay_seconds", 3))
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410):
                return None
            err = e
        except Exception as e:  # noqa: BLE001
            err = e
        time.sleep(10 * (i + 1))
    raise RuntimeError(f"failed: {url} ({err})")


def clean(s):
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def store(state):
    FOLDER.mkdir(parents=True, exist_ok=True)
    tmp = FOLDER / "progress.tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    tmp.replace(STATE)


def profile(html):
    """website, status, participant since from a profile page"""
    t = clean(re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html))
    out = {}
    m = re.search(r"Global Compact Status:\s*([A-Za-z\- ]+?)\s+(Participant Since|Letter|Next|Expelled|Delisted|$)", t)
    if m:
        out["status"] = m.group(1).strip()
    m = re.search(r"Participant Since\s+(\d{1,2} \w+ \d{4})", t)
    if m:
        out["since"] = m.group(1)
    m = re.search(r"Company Information\s+\S.*?\s+([a-z0-9.-]+\.[a-z]{2,}(?:/\S*)?)\s+Share Profile", t)
    if m:
        out["website"] = m.group(1)
    return out


def main():
    state = json.load(gzip.open(STATE, "rt", encoding="utf-8")) if STATE.exists() else {"pages": {}, "last_page": None, "profiles": {}}
    # 1. list pages
    first = fetch(CFG["list_path"])
    last = max([int(x) for x in re.findall(r"participants\?page=(\d+)", first)] or [1])
    state["last_page"] = last
    print(f"list: {last} pages", flush=True)
    for n in range(1, last + 1):
        if str(n) in state["pages"]:
            continue
        if minutes() > BUDGET:
            break
        html = first if n == 1 else fetch(f"{CFG['list_path']}?page={n}")
        rows = [{"path": a, "name": clean(b), "type": clean(c), "sector": clean(d), "country": clean(e), "joined": clean(f)}
                for a, b, c, d, e, f in ROW.findall(html or "")]
        state["pages"][str(n)] = rows
        if n % 25 == 0:
            store(state)
            print(f"list: page {n} of {last} ({minutes():.0f} min)", flush=True)
    store(state)
    rows = {r["path"]: r for p in state["pages"].values() for r in p}
    print(f"list: {len(state['pages'])} of {last} pages, {len(rows)} participants", flush=True)
    # 2. profile pages of the included types
    want = set(CFG["types_included"])
    todo = [p for p, r in rows.items() if r["type"] in want and p not in state["profiles"]]
    print(f"profiles to read: {len(todo)}", flush=True)
    for i, p in enumerate(todo, 1):
        if minutes() > BUDGET:
            break
        try:
            html = fetch(p)
        except RuntimeError as e:
            print("profile failed", p, e)
            continue
        state["profiles"][p] = {**(profile(html) if html else {"not_found": True}), "fetched": now()}
        if i % 50 == 0:
            store(state)
            print(f"profiles: {i} of {len(todo)} ({minutes():.0f} min)", flush=True)
    store(state)
    done_list = len(state["pages"]) >= last
    left = sum(1 for p, r in rows.items() if r["type"] in want and p not in state["profiles"])
    records = [{**r, **state["profiles"].get(p, {})} for p, r in rows.items() if r["type"] in want]
    save("global_compact", records, {"url": CFG["base"] + CFG["list_path"], "participants_in_list": len(rows),
                                     "list_complete": done_list, "profiles_still_to_fetch": left,
                                     "types_included": sorted(want), "licence": "UN Global Compact public participant list"})
    print(f"done: list {'complete' if done_list else 'incomplete'}, {len(records)} participants of the included types, "
          f"{left} profiles still to fetch", flush=True)


if __name__ == "__main__":
    main()
