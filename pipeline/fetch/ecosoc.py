"""ECOSOC iCSO database (esango.un.org): civil society organisations known to the UN.

Owner's decision 10.11.2026: ALL NGOs of the database go in (also those only registered,
without consultative status; they get a small note and there is an "ECOSOC status" filter).

How (no login needed, public "withOutLogin" lists):
  1. the search pages (consultative status search, DPI/DGC search) are read and every
     public list link on them is collected: lists by consultative status, by type of
     organisation, by field of activity, by region ... (codes are taken from the pages,
     not typed in by hand)
  2. every list is read page by page (25 per page; the server keeps the page in a session
     cookie, so the "Next" link is followed). Which organisation is in which list gives
     status, type and fields of activity without opening every profile.
  3. profile pages (country, languages, website, e-mail, areas of expertise) of the
     organisations of type "Non-governmental organization" are read step by step; only a
     short text version is kept (not the whole page).
The server is slow: the script works within a time budget, saves often and continues
where it stopped in the next run. Lists are read again after LIST_DAYS, profiles after
PROFILE_DAYS (automatic update every 2 months).

Output: raw/ecosoc/lists.json.gz   {list_id: {"label", "kind", "url", "codes", "fetched", "complete"}}
        raw/ecosoc/orgs.json.gz    {code: {"name", "accreditations"}}
        raw/ecosoc/profiles.json.gz {code: {"text", "links", "emails", "fetched"}}
        raw/ecosoc/samples/        3 full pages per kind, to check the page structure
"""
import gzip
import html as htmllib
import http.cookiejar
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

from common import RAW, USER_AGENT, save

BASE = "https://esango.un.org/civilsociety/"
INDEX_PAGES = {
    "status_search": "displayConsultativeStatusSearch.do?method=search",
    "dpi_search": "displayDPISearch.do?method=search",
}
NGO_TYPE = "Non-governmental organization"
BUDGET_MIN = float(os.environ.get("ECOSOC_MINUTES", "300"))
LIST_DAYS = int(os.environ.get("ECOSOC_LIST_DAYS", "50"))
PROFILE_DAYS = int(os.environ.get("ECOSOC_PROFILE_DAYS", "170"))
MAX_PROFILES = int(os.environ.get("ECOSOC_MAX_PROFILES", "100000"))
START = time.time()
FOLDER = RAW / "ecosoc"

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
opener.addheaders = [("User-Agent", USER_AGENT), ("Accept", "text/html")]


def minutes():
    if GIVE_UP["yes"]:  # server silent for a long time: end this run early (saves GitHub minutes)
        return float("inf")
    return (time.time() - START) / 60


# 11.11.2026: after a few minutes the server stopped answering for 5 hours. Ask slowly (one request
# every 3 seconds) and stop the run when nothing has worked for 20 minutes; the next run continues.
DELAY_S = float(os.environ.get("ECOSOC_DELAY", "3"))
SILENT_STOP_MIN = 20
GIVE_UP = {"yes": False}
LAST_OK = {"t": time.time()}


FAILS = {"row": 0}  # failures in a row: the server is often down for a while (10.11.2026: most requests timed out)


class NotAvailable(Exception):
    """the page exists for the server but is not public (HTTP 403/404): not retried"""


def fetch(path, tries=2):
    url = path if path.startswith("http") else BASE + path.lstrip("/").replace("civilsociety/", "", 1)
    url = urllib.parse.quote(htmllib.unescape(url), safe=":/?&=%$+,;@")
    last = None
    if GIVE_UP["yes"] or (time.time() - LAST_OK["t"]) / 60 > SILENT_STOP_MIN:
        if not GIVE_UP["yes"]:
            print(f"server silent for {SILENT_STOP_MIN} minutes: stop this run, continue next run", flush=True)
        GIVE_UP["yes"] = True
        raise RuntimeError("server silent: run stopped")
    if FAILS["row"] >= 10:  # many failures in a row: wait for the server instead of burning the time budget
        print(f"server not answering ({FAILS['row']} failures in a row): pause 5 minutes", flush=True)
        time.sleep(300)
        FAILS["row"] = 5
    for attempt in range(tries):
        try:
            time.sleep(DELAY_S)
            with opener.open(url, timeout=40) as r:
                body = r.read().decode("utf-8", "replace")
            FAILS["row"] = 0
            LAST_OK["t"] = time.time()
            return body
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410):  # 11.11.2026: some profiles are not public (403): the server did answer
                FAILS["row"] = 0
                LAST_OK["t"] = time.time()
                raise NotAvailable(f"{e.code}: {url}")
            last = e
            time.sleep(5)
        except Exception as e:
            last = e
            time.sleep(5)
    FAILS["row"] += 1
    raise RuntimeError(f"failed: {url} ({last})")


def load(name, default):
    p = FOLDER / name
    if p.exists():
        return json.load(gzip.open(p, "rt", encoding="utf-8"))
    return default


def store(name, data):
    FOLDER.mkdir(parents=True, exist_ok=True)
    tmp = FOLDER / (name + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    tmp.replace(FOLDER / name)


def sample(kind, html):
    d = FOLDER / "samples"
    d.mkdir(parents=True, exist_ok=True)
    have = sorted(d.glob(kind + "_*.html.gz"))
    if len(have) < 3:
        with gzip.open(d / f"{kind}_{len(have) + 1}.html.gz", "wt", encoding="utf-8") as f:
            f.write(html)


LINK = re.compile(r'href="(/civilsociety/withOutLogin\.do\?[^"]+|/?civilsociety/[A-Za-z]+\.do\?method=getOrgs[^"]*)"[^>]*>(.*?)</a>', re.S)
ROW = re.compile(r'profileCode=(\d+)"[^>]*>(.*?)</a>\s*</td>\s*<td[^>]*>(.*?)</td>', re.S)
NEXT = re.compile(r'<a href="([^"]+)">\s*Next\s*</a>')
PAGES = re.compile(r"Page \d+ of (\d+)")


def text(s):
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def kind_of(url):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(htmllib.unescape(url)).query)
    m = (q.get("method") or [""])[0]
    for k in ("Consultative", "TypesCode", "FieldsOfActivity", "Region", "Country", "DPI", "Accred", "Geo"):
        if k.lower() in m.lower():
            return {"Consultative": "status", "TypesCode": "type", "FieldsOfActivity": "field", "DPI": "dpi"}.get(k, k.lower())
    return m or "other"


def discover():
    found = {}
    for pid, path in INDEX_PAGES.items():
        try:
            html = fetch(path)
        except RuntimeError as e:
            print("index page failed", pid, e)
            continue
        sample("index_" + pid, html)
        for href, label in LINK.findall(html):
            href = htmllib.unescape(href)
            lid = re.sub(r"[^a-z0-9]+", "_", urllib.parse.urlparse(href).query.lower())[:120]
            found.setdefault(lid, {"label": text(label), "kind": kind_of(href), "url": href, "from": pid})
    # fallback when the search pages offer no list links: the public list addresses known
    # from 06.11.2026 (status 1-3, type codes of the advanced search, field of activity codes)
    w = "/civilsociety/withOutLogin.do?method="
    seeds = [("status", f"getOrgsByConsultativeCode&orgByConsCode={c}&orgByConsName={n}", n)
             for c, n in ((1, "General"), (2, "Special"), (3, "Roster"))]
    seeds += [("type", f"getOrgsByTypesCode&orgTypeCode={c}&orgTypName={n}", n)
              for c, n in ((6, "Non-governmental organization"), (1, "Association"), (2, "Foundation"),
                           (12, "Indigenous Peoples Organizations"),
                           (13, "Disability, Development and Rights Organizations"))]
    if not any(v["kind"] == "field" for v in found.values()):
        seeds += [("field", f"getFieldsOfActivityCode&orgByFieldOfActivityCode={c}&orgByFieldOfActivityName=",
                   f"field of activity code {c}") for c in range(1, 61)]
    for kind, q, label in seeds:
        lid = re.sub(r"[^a-z0-9]+", "_", q.lower())[:120]
        if not any(v["kind"] == kind and v["label"] == label for v in found.values()):
            found.setdefault(lid, {"label": label, "kind": kind, "url": w + q, "from": "seed"})
    print(f"{len(found)} list links found:", {k: sum(1 for v in found.values() if v['kind'] == k)
                                             for k in sorted({v['kind'] for v in found.values()})}, flush=True)
    return found


def rows(html):
    out = []
    for code, name, acc in ROW.findall(html):
        tags = [text(t) for t in re.findall(r"<span[^>]*>(.*?)</span>", acc, re.S)] or [text(acc)]
        out.append((code, text(name), [t for t in tags if t]))
    return out


def read_list(meta, orgs):
    """reads a list page by page; a long list that did not finish continues at the page where the
    last run stopped (meta["resume_index"]), the server keeps the list in the session"""
    html = fetch(meta["url"])
    sample("list_" + meta["kind"], html)
    i = html.find("Search results")
    if i > 0:  # the heading names the list (e.g. the field of activity), kept to label code-only lists
        meta["heading"] = text(re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html[i:i + 3000]))[:300]
    pages = int((PAGES.search(html) or [0, 1])[1])
    codes, seen_next = list(meta.get("codes") or []), set()
    m0 = NEXT.search(html)
    if meta.get("resume_index") and m0:  # jump to where the last run stopped
        try:
            html = fetch(re.sub(r"index=\d+", f"index={meta['resume_index']}", m0.group(1)))
        except RuntimeError:
            return codes, False, pages
    while True:
        for code, name, acc in rows(html):
            codes.append(code)
            o = orgs.setdefault(code, {"name": name, "accreditations": []})
            o["name"] = name or o["name"]
            for a in acc:
                if a not in o["accreditations"]:
                    o["accreditations"].append(a)
        m = NEXT.search(html)
        if not m or m.group(1) in seen_next:
            return codes, True, pages
        if minutes() > BUDGET_MIN:
            return codes, False, pages
        seen_next.add(m.group(1))
        idx = re.search(r"index=(\d+)", m.group(1))
        if idx:
            meta["resume_index"] = int(idx.group(1))
        try:
            html = fetch(m.group(1))
        except RuntimeError as e:
            print("  page failed, list stays incomplete:", e)
            return codes, False, pages


def profile_text(html):
    """short text version of a profile page (menu and footer cut off)"""
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    cut = s.find("unless such affiliation is expressly indicated")
    if cut > 0:
        s = s[cut:]
    end = s.find("footer")
    if end > 0:
        s = s[:end]
    s = re.sub(r"(?i)<br\s*/?>|</(td|tr|p|div|li|h\d)>", " | ", s)
    t = text(s)
    t = re.sub(r"(\s*\|\s*)+", " | ", t)
    links = sorted({u for u in re.findall(r'href="(https?://[^"]+)"', html) if "un.org" not in u})[:20]
    emails = sorted(set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", t)))[:10]
    return {"text": t[:6000], "links": links, "emails": emails}


def fresh(stamp, days):
    try:
        return (datetime.now(timezone.utc).replace(tzinfo=None) - datetime.fromisoformat(stamp)).days < days
    except Exception:
        return False


def main():
    lists = load("lists.json.gz", {})
    orgs = load("orgs.json.gz", {})
    profiles = load("profiles.json.gz", {})
    for lid, meta in discover().items():
        old = lists.get(lid, {})
        lists[lid] = {**old, **meta}
    # 1. lists: status and type first (small, most important), then fields of activity, then the rest
    order = {"status": 0, "dpi": 1, "type": 2, "field": 3}
    skip = set(os.environ.get("ECOSOC_SKIP_KINDS", "").split(","))  # e.g. "field" when those lists fail (HTTP 500)
    todo = sorted((lid for lid, m in lists.items()
                   if not (m.get("complete") and fresh(m.get("fetched", ""), LIST_DAYS)) and m["kind"] not in skip),
                  key=lambda lid: (order.get(lists[lid]["kind"], 9), lid))
    print(f"lists to read: {len(todo)} of {len(lists)}", flush=True)
    for i, lid in enumerate(todo):
        if minutes() > BUDGET_MIN * 0.5:
            print("time for lists used up: continue next run")
            break
        m = lists[lid]
        try:
            codes, complete, pages = read_list(m, orgs)
        except RuntimeError as e:
            print("list failed", m["label"], e)
            continue
        if complete:
            m.pop("resume_index", None)
        if complete or len(set(codes)) >= len(m.get("codes") or []):
            m.update({"codes": sorted(set(codes), key=int), "complete": complete, "pages": pages,
                      "fetched": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")})
        print(f"[{i + 1}/{len(todo)}] {m['kind']}: {m['label'][:60]} - {len(set(codes))} orgs,"
              f" {pages} pages, {'complete' if complete else 'INCOMPLETE'} ({minutes():.0f} min)", flush=True)
        store("lists.json.gz", lists)
        store("orgs.json.gz", orgs)
    # 2. profiles of NGOs (type list "Non-governmental organization"; all orgs if that list is missing)
    ngo_codes = set()
    for m in lists.values():
        if m["kind"] == "type" and NGO_TYPE.lower() in m["label"].lower():
            ngo_codes |= set(m.get("codes") or [])
    targets = sorted(ngo_codes or set(orgs), key=int)
    done = 0
    for code in targets:
        if fresh(profiles.get(code, {}).get("fetched", ""), PROFILE_DAYS):
            continue
        if done >= MAX_PROFILES or minutes() > BUDGET_MIN:
            print("profile budget reached: continue next run")
            break
        try:
            html = fetch(f"showProfileDetail.do?method=showProfileDetails&profileCode={code}")
        except NotAvailable:
            profiles[code] = {"not_public": True, "fetched": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")}
            continue
        except RuntimeError as e:
            print("profile failed", code, e)
            continue
        sample("profile", html)
        profiles[code] = {**profile_text(html), "fetched": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")}
        done += 1
        if done % 50 == 0:  # save often: a run can be stopped any time
            store("profiles.json.gz", profiles)
            print(f"profiles: {done} fetched now, {len(profiles)} in total ({minutes():.0f} min)", flush=True)
    store("profiles.json.gz", profiles)
    complete = sum(1 for m in lists.values() if m.get("complete"))
    left = sum(1 for c in targets if not fresh(profiles.get(c, {}).get("fetched", ""), PROFILE_DAYS))
    save("ecosoc", [], {"url": BASE, "lists": len(lists), "lists_complete": complete, "organisations": len(orgs),
                        "ngo_type_codes": len(ngo_codes), "profiles": len(profiles), "profiles_fetched_now": done,
                        "profiles_still_to_fetch": left, "date": str(date.today()),
                        "licence": "UN ECOSOC iCSO public database (public listing)"})
    print(f"done: {complete}/{len(lists)} lists complete, {len(orgs)} organisations, "
          f"{len(profiles)} profiles ({left} still to fetch)")


if __name__ == "__main__":
    main()
