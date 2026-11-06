"""ECOSOC iCSO database (esango.un.org): NGOs in consultative status.

Public lists without login, by status (General, Special, Roster). The lists
are paged on the server (25 per page, the page number is kept in a session
cookie), so this script keeps cookies. For every NGO the profile page is
saved too (country, areas of expertise ...); profiles fetched less than
90 days ago are not fetched again.
Output: raw/ecosoc/list.json.gz, raw/ecosoc/profiles/<code>.html.gz
"""
import gzip
import http.cookiejar
import json
import os
import re
import time
import urllib.request

from common import RAW, USER_AGENT, save

BASE = "https://esango.un.org/civilsociety/"
STATUS = {1: "General", 2: "Special", 3: "Roster"}
MAX_PROFILES = int(os.environ.get("ECOSOC_MAX_PROFILES", "100000"))
BUDGET_MIN = float(os.environ.get("ECOSOC_MINUTES", "150"))
START = time.time()

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
opener.addheaders = [("User-Agent", USER_AGENT), ("Accept", "text/html")]


def fetch(path, tries=3):
    for attempt in range(tries):
        try:
            time.sleep(0.5)
            with opener.open(BASE + path, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            time.sleep(5 * (attempt + 1) ** 2)
    raise RuntimeError(f"failed: {path} ({last})")


ROW = re.compile(r'profileCode=(\d+)">([^<]+)</a>\s*</td>\s*<td>(.*?)</td>', re.S)


def rows(html):
    out = []
    for code, name, acc in ROW.findall(html):
        tags = [re.sub(r"\s+", " ", t).strip() for t in re.findall(r"<span[^>]*>([^<]*)</span>", acc)]
        out.append({"code": code, "name": re.sub(r"\s+", " ", name).strip(), "accreditations": [t for t in tags if t]})
    return out


def main():
    folder = RAW / "ecosoc"
    (folder / "profiles").mkdir(parents=True, exist_ok=True)
    ngos = {}
    for code, status in STATUS.items():
        html = fetch(f"withOutLogin.do?method=getOrgsByConsultativeCode&orgByConsCode={code}&orgByConsName={status}")
        pages = int((re.search(r"Page \d+ of (\d+)", html) or [0, 1])[1])
        found = rows(html)
        failed_pages = []
        for i in range(1, pages):
            try:
                found += rows(fetch(f"displayConsultativeStatusSearch.do?method=list&show=25&from=list&col=&order=&searchType=$searchType&index={i * 25}"))
            except RuntimeError:
                failed_pages.append(i + 1)  # the server is slow at times: skip, next run fills the gap
            if (time.time() - START) / 60 > BUDGET_MIN:
                print("time budget reached while reading lists")
                break
        if failed_pages:
            print(f"{status}: pages not read this time: {failed_pages}")
        for r in found:
            ngos.setdefault(r["code"], {**r, "status": status})
        print(f"{status}: {pages} pages, {len(found)} rows, total {len(ngos)}", flush=True)

        # save after every status, and keep NGOs found in earlier runs
        old = {}
        if (folder / "list.json.gz").exists():
            old = {r["code"]: r for r in json.load(gzip.open(folder / "list.json.gz", "rt", encoding="utf-8"))}
        old.update(ngos)
        with gzip.open(folder / "list.json.gz", "wt", encoding="utf-8") as f:
            json.dump(sorted(old.values(), key=lambda r: int(r["code"])), f, ensure_ascii=False)

    # profiles (country, areas of expertise, website ...)
    done = skipped = 0
    for code in sorted(ngos, key=int):
        path = folder / "profiles" / f"{code}.html.gz"
        if path.exists() and (time.time() - path.stat().st_mtime) < 90 * 86400:
            skipped += 1
            continue
        if done >= MAX_PROFILES or (time.time() - START) / 60 > BUDGET_MIN:
            print("profile budget reached: continue next run")
            break
        try:
            html = fetch(f"showProfileDetail.do?method=showProfileDetails&profileCode={code}")
            with gzip.open(path, "wt", encoding="utf-8") as f:
                f.write(html)
            done += 1
        except RuntimeError as e:
            print("profile failed", code, e)
        if done % 250 == 0 and done:
            print(f"profiles: {done} fetched", flush=True)
    save("ecosoc", [], {"url": BASE, "ngos_in_lists": len(ngos), "profiles_fetched_now": done,
                        "profiles_already_there": skipped,
                        "licence": "UN ECOSOC iCSO public database (public listing)"})


if __name__ == "__main__":
    main()
