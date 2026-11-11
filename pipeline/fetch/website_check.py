"""Website check, part 1 (plan T3): reads the outlets' own websites.

Which outlets: those with a website and rank <= WEBSITE_MAX_RANK in their
country (default 100), best-known first (all rank-1 outlets, then rank 2 ...).
Input is the website data (site/data/outlets-N.json: id, website, rank).

Per website (home page + the "About" page if one is linked):
  title, description (meta), page language, menu/section names with their
  addresses (the "Desk" signal), headlines, About text (the "Focus" signal),
  public e-mail addresses (organisation addresses, no personal ones are
  selected here: the pipeline filters them), social media links, RSS/podcast feeds.
robots.txt is respected. One visit per site, at most 2 pages.

Output: raw/website_check/<ISO3>.json.gz  {outlet id: {...}} and meta.json.
Already checked sites are kept and skipped for WEBSITE_RECHECK_DAYS (default 50; the owner
chose all websites on 09.11.2026),
so a run that hits the time limit continues where it stopped.
"""
import gzip
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW, ROOT, USER_AGENT  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))
from org_email import org_email  # noqa: E402  only organisation addresses are stored (config/rules.yaml)

OUT = RAW / "website_check"
MAX_RANK = int(os.environ.get("WEBSITE_MAX_RANK", "100"))
MINUTES = float(os.environ.get("WEBSITE_MINUTES", "150"))
RECHECK_DAYS = int(os.environ.get("WEBSITE_RECHECK_DAYS", "50"))
WORKERS = 48
TIMEOUT = 15
MAX_BYTES = 1_500_000
SOCIAL = {"youtube.com": "youtube", "facebook.com": "facebook", "instagram.com": "instagram", "tiktok.com": "tiktok",
          "twitter.com": "x", "x.com": "x", "t.me": "telegram", "whatsapp.com": "whatsapp", "wa.me": "whatsapp",
          "linkedin.com": "linkedin"}
ABOUT = re.compile(r"about|who-we-are|qui-sommes|a-propos|apropos|quienes-somos|qui[eé]nes somos|sobre|nosotros|"
                   r"quem-somos|chi-siamo|о нас|о-нас|o-nas|من نحن|عن |关于|हमारे बारे|kuhusu|mission|our-story", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
NAV_HINT = re.compile(r"nav|menu|header|topbar|sections?", re.I)
VERSION = 2  # 2 = also contact page, partner-content hints, date of the latest article (09.11.2026)
CONTACT = re.compile(r"contact|kontakt|contacto|contato|contactez|nous joindre|cont[aá]ctenos|fale conosco|"
                     r"контакт|اتصل بنا|联系我们|संपर्क|wasiliana", re.I)
# links that may show the outlet takes content from others (rules.yaml: open_to_partner_content)
INTEREST = re.compile(r"republish|syndicat|creative ?commons|creativecommons|submit|contribut|write for us|"
                      r"pitch|press release|partner|tip|send us|soumettre|proposer|envoyez|republier|communiqu|"
                      r"colabor|env[ií]a|publica tu|comunicado|envie|seja|投稿|прислать|предложить|стать автором|"
                      r"أرسل|शेयर|भेजें|tuma habari", re.I)
DATE_TAGS = re.compile(r"<(?:pubDate|updated|published|dc:date)>\s*([^<]{8,40})\s*<", re.I)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.desc, self.lang = "", "", ""
        self.nav, self.heads, self.links, self.feeds, self.paras = [], [], [], [], []
        self.stack = []  # (tag, is_nav)
        self.cur_a, self.cur_text, self.in_title, self.skip = None, [], False, 0
        self.cur_h, self.cur_p = None, None
        self.dates = []  # <time datetime="..."> on the page

    def in_nav(self):
        return any(n for _, n in self.stack)

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag in ("script", "style", "noscript", "svg"):
            self.skip += 1
        if tag == "html" and a.get("lang"):
            self.lang = a["lang"][:10]
        if tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower()
            if name in ("description", "og:description") and not self.desc:
                self.desc = a.get("content", "")[:600]
        if tag == "link" and "alternate" in a.get("rel", "").lower() and ("rss" in a.get("type", "") or "atom" in a.get("type", "")):
            self.feeds.append(a.get("href", ""))
        if tag == "title":
            self.in_title = True
        if tag == "time" and a.get("datetime"):
            self.dates.append(a["datetime"][:10])
        if tag == "meta" and (a.get("property") or a.get("name") or "").lower() in ("article:published_time", "article:modified_time"):
            self.dates.append(a.get("content", "")[:10])
        if tag not in ("br", "img", "meta", "link", "input", "hr"):
            is_nav = tag in ("nav", "header") or bool(NAV_HINT.search(a.get("class", "") + " " + a.get("id", "") + " " + a.get("role", "")))
            self.stack.append((tag, is_nav))
        if tag == "a":
            self.cur_a, self.cur_text = a.get("href", ""), []
        if tag in ("h1", "h2", "h3"):
            self.cur_h = []
        if tag == "p":
            self.cur_p = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self.skip:
            self.skip -= 1
        if tag == "title":
            self.in_title = False
        if tag == "a" and self.cur_a is not None:
            text = " ".join("".join(self.cur_text).split())[:80]
            self.links.append((text, self.cur_a, self.in_nav()))
            self.cur_a = None
        if tag in ("h1", "h2", "h3") and self.cur_h is not None:
            t = " ".join("".join(self.cur_h).split())
            if 8 <= len(t) <= 160:
                self.heads.append(t)
            self.cur_h = None
        if tag == "p" and self.cur_p is not None:
            t = " ".join("".join(self.cur_p).split())
            if len(t) >= 40:
                self.paras.append(t)
            self.cur_p = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self.skip:
            return
        if self.in_title:
            self.title += data
        if self.cur_a is not None:
            self.cur_text.append(data)
        if self.cur_h is not None:
            self.cur_h.append(data)
        if self.cur_p is not None:
            self.cur_p.append(data)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.5",
                                               "Accept-Language": "en,fr,es,ar,ru,zh,hi,pt,sw;q=0.8,*;q=0.5"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        ctype = r.headers.get("Content-Type", "")
        if "html" not in ctype and ctype:
            raise ValueError("not html: " + ctype[:40])
        body = r.read(MAX_BYTES)
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        cs = r.headers.get_content_charset()
        if not cs:
            m = re.search(rb"charset=[\"']?([A-Za-z0-9_-]+)", body[:3000])
            cs = m.group(1).decode() if m else "utf-8"
        try:
            text = body.decode(cs, errors="replace")
        except LookupError:
            text = body.decode("utf-8", errors="replace")
        return r.geturl(), text


def allowed(url):
    p = urllib.parse.urlsplit(url)
    rp = urllib.robotparser.RobotFileParser()
    try:
        req = urllib.request.Request(f"{p.scheme}://{p.netloc}/robots.txt", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as r:
            rp.parse(r.read(200_000).decode("utf-8", errors="replace").splitlines())
    except Exception:
        return True  # no robots.txt (or unreachable): allowed
    return rp.can_fetch(USER_AGENT, url)


def host(u):
    return re.sub(r"^www\d?\.", "", urllib.parse.urlsplit(u).netloc.lower())


def check(outlet):
    """never raises: a problem with one site is stored as status "error" """
    try:
        return _check(outlet)
    except Exception as e:  # e.g. a malformed link on the page
        return outlet["i"], {"url": outlet["w"], "checked": date.today().isoformat(), "status": "error",
                             "error": ("parse: " + str(e))[:120]}


def _check(outlet):
    url = outlet["w"] if outlet["w"].startswith("http") else "http://" + outlet["w"]
    res = {"url": url, "checked": date.today().isoformat()}
    try:
        if not allowed(url):
            res["status"] = "robots"
            return outlet["i"], res
        final, html = fetch(url)
    except Exception as e:
        res["status"] = "error"
        res["error"] = str(e)[:120]
        return outlet["i"], res
    p = Page()
    try:
        p.feed(html)
    except Exception:
        pass
    home = host(final)
    res.update({"status": "ok", "final_url": final, "lang": p.lang, "title": " ".join(p.title.split())[:200],
                "desc": " ".join(p.desc.split())})
    nav, seen, social, emails, about = [], set(), {}, [], None
    extra, contact = [], None
    for text, href, is_nav in p.links:
        try:
            full = urllib.parse.urljoin(final, href)
        except ValueError:
            continue
        h = host(full)
        if href.startswith("mailto:"):
            e = href[7:].split("?")[0].strip()
            if EMAIL.fullmatch(e) and org_email(e) and org_email(e) not in emails:
                emails.append(org_email(e))
            continue
        for dom, name in SOCIAL.items():
            if h == dom or h.endswith("." + dom):
                social.setdefault(name, full)
        if (INTEREST.search(text or "") or INTEREST.search(full)) and len(extra) < 25 \
                and (h == home or "creativecommons.org" in h):
            extra.append([" ".join((text or "").split())[:60], full[:200]])
        if h != home:
            continue
        path = urllib.parse.urlsplit(full).path
        if is_nav and text and (text, path) not in seen and len(nav) < 120:
            seen.add((text, path))
            nav.append([text, path])
        if about is None and (ABOUT.search(text) or ABOUT.search(path)) and path not in ("", "/"):
            about = full
        if contact is None and (CONTACT.search(text or "") or CONTACT.search(path)) and path not in ("", "/"):
            contact = full
    for e in EMAIL.findall(" ".join(p.paras[-30:])):
        if org_email(e) and org_email(e) not in emails:
            emails.append(org_email(e))
    res.update({"nav": nav, "heads": p.heads[:60], "emails": emails[:8], "social": social,
                "feeds": [urllib.parse.urljoin(final, f) for f in p.feeds[:5]], "home_text": " ".join(p.paras[:6])[:800],
                "v": VERSION, "extra": extra})
    if contact:
        res["contact_url"] = contact
    dates = [d for d in p.dates if re.match(r"\d{4}-\d{2}-\d{2}$", d)]
    if res["feeds"]:  # date of the latest article from the RSS / Atom feed
        try:
            req = urllib.request.Request(res["feeds"][0], headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as r:
                xml = r.read(600_000).decode("utf-8", errors="replace")
            from email.utils import parsedate_to_datetime
            for raw in DATE_TAGS.findall(xml)[:50]:
                try:
                    d = parsedate_to_datetime(raw.strip()).date().isoformat()
                except Exception:
                    d = raw.strip()[:10]
                if re.match(r"\d{4}-\d{2}-\d{2}$", d):
                    dates.append(d)
        except Exception:
            pass
    today = date.today().isoformat()
    dates = [d for d in dates if "2000-01-01" <= d <= today]
    if dates:
        res["last_post"] = max(dates)
    if about:
        try:
            if allowed(about):
                _, html2 = fetch(about)
                a = Page()
                a.feed(html2)
                res["about_url"] = about
                res["about"] = " ".join(a.paras)[:1500] or a.desc
                for e in EMAIL.findall(" ".join(a.paras)):
                    if org_email(e) and org_email(e) not in res["emails"] and len(res["emails"]) < 8:
                        res["emails"].append(org_email(e))
        except Exception as e:
            res["about_error"] = str(e)[:80]
    return outlet["i"], res


def save_shards(shards):
    for c, s in list(shards.items()):
        with gzip.open(OUT / f"{c}.json.gz", "wt", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main():
    outlets = []  # website data files (site/data/outlets-N.json, older: outlets.json)
    for f in sorted((ROOT / "site" / "data").glob("outlets*.json")) + sorted((ROOT / "site" / "data").glob("ngos*.json")):
        outlets += json.load(open(f, encoding="utf-8"))  # NGO websites too (phase 2): language, contact, social
    todo = sorted((o for o in outlets if o.get("w") and o["r"] <= MAX_RANK), key=lambda o: (o["r"], o["i"]))
    OUT.mkdir(parents=True, exist_ok=True)
    shards = {}
    for f in OUT.glob("*.json.gz"):
        shards[f.name[:3]] = json.load(gzip.open(f, "rt", encoding="utf-8"))
    cutoff = (date.today() - timedelta(days=RECHECK_DAYS)).isoformat()
    done = {i for s in shards.values() for i, v in s.items() if v.get("checked", "") >= cutoff and v.get("v", 1) >= VERSION}
    todo = [o for o in todo if o["i"] not in done]
    country = {o["i"]: o["c"] for o in outlets}
    print(f"to check: {len(todo)} websites (rank <= {MAX_RANK}), already done: {len(done)}")
    t0, n, ok = time.time(), 0, 0
    with ThreadPoolExecutor(WORKERS) as ex:
        futures = []
        for o in todo:
            futures.append(ex.submit(check, o))
        for fut in as_completed(futures):
            try:
                oid, res = fut.result()
            except Exception as e:
                print("unexpected:", e)
                continue
            shards.setdefault(country[oid], {})[oid] = res
            n += 1
            ok += res.get("status") == "ok"
            if n % 500 == 0:
                print(f"{n} checked, {ok} answered, {time.time() - t0:.0f}s")
            if n % 3000 == 0:
                save_shards(shards)  # keep progress if the run stops
            if time.time() - t0 > MINUTES * 60:
                print("time limit reached: stopping, the next run continues")
                for f in futures:
                    f.cancel()
                break
    save_shards(shards)
    total = sum(len(s) for s in shards.values())
    answered = sum(1 for s in shards.values() for v in s.values() if v.get("status") == "ok")
    meta = {"source": "website_check", "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "max_rank": MAX_RANK, "checked_this_run": n, "answered_this_run": ok, "sites_total": total,
            "answered_total": answered}
    json.dump(meta, open(OUT / "meta.json", "w", encoding="utf-8"), indent=2)
    print(meta)


if __name__ == "__main__":
    main()
