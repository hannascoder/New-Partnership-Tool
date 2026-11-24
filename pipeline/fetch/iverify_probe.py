"""One-off look at how far public sources lead to UNDP iVerify country sites (owner's request 18.11.2026).

Reads the UNDP iVerify page(s) and the Digital Public Goods registry entry, collects every link that points to an iVerify
site, visits each site's home page (honest user agent, robots.txt respected) and looks for the feed it announces.
Result: reports/iverify_probe.md. Nothing else is changed. Start: Actions -> "Probe iVerify" -> Run workflow.
"""
import re
import time
import urllib.parse
from datetime import date

from common import ROOT
from desinfo import feed_items
from desinfo_discover import allowed, feed_links, home_page

START = ["https://www.undp.org/digital/iverify", "https://digitalpublicgoods.net/registry/iverify.html",
         "https://digitalx.undp.org/iverify_1.html", "https://www.undp.org/latin-america/digitalhub4/projects/iverify-undps-tool-fact-checking-and-information-integrity"]
KEY = re.compile(r"i-?verify", re.I)
SKIP = ("facebook.com", "twitter.com", "x.com", "linkedin.com", "youtube.com", "instagram.com", "t.me")


def links(html, base):
    out = {}
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', html, flags=re.I | re.S):
        u = urllib.parse.urljoin(base, m.group(1).replace("&amp;", "&"))
        txt = re.sub(r"<[^>]+>", " ", m.group(2))
        txt = re.sub(r"\s+", " ", txt).strip()[:80]
        if u.startswith("http"):
            out[u] = txt
    return out


def main():
    L = ["# UNDP iVerify: what the public sources lead to", "", f"Run: {date.today().isoformat()} (GitHub Actions, honest user agent)", ""]
    found = {}                                     # url -> (text, found on)
    for page in START:
        html, st = home_page(page)
        L.append(f"- {page}: {st} ({len(html)} bytes)")
        if st != "ok":
            continue
        for u, t in links(html, page).items():
            host = urllib.parse.urlparse(u).netloc.lower()
            if any(host.endswith(s) for s in SKIP):
                continue
            if KEY.search(u) or KEY.search(t):
                found.setdefault(u, (t, page))
        time.sleep(1)
    # one level further: pages on undp.org that are about iVerify
    for u in [u for u in found if "undp.org" in u][:25]:
        html, st = home_page(u)
        if st == "ok":
            for u2, t2 in links(html, u).items():
                host = urllib.parse.urlparse(u2).netloc.lower()
                if not any(host.endswith(s) for s in SKIP) and (KEY.search(u2) or KEY.search(t2)):
                    found.setdefault(u2, (t2, u))
        time.sleep(1)
    L += ["", f"## Links that mention iVerify ({len(found)})", "", "| Link | Text | Found on |", "|---|---|---|"]
    for u, (t, src) in sorted(found.items()):
        L.append(f"| {u} | {t} | {src} |")
    # candidate sites: any host that is not undp.org / the registry
    hosts = {}
    for u in found:
        p = urllib.parse.urlparse(u)
        if not p.netloc.endswith("undp.org") and "digitalpublicgoods" not in p.netloc:
            hosts.setdefault(p.netloc.lower(), u)
    L += ["", f"## Sites outside undp.org ({len(hosts)})", "", "| Site | Home page | Feed announced | Items |", "|---|---|---|---|"]
    for host, u in sorted(hosts.items()):
        root = f"https://{host}/"
        html, st = home_page(root)
        feed, n = "", ""
        if st == "ok":
            for fl in feed_links(html, root)[:2]:
                if not allowed(fl):
                    continue
                try:
                    got = feed_items({"url": fl, "lang": "en", "name": host, "domain": host, "country": ""})
                except Exception:  # noqa: BLE001
                    continue
                if got:
                    feed, n = fl, str(len(got))
                    break
        L.append(f"| {host} | {st} | {feed or '-'} | {n or '-'} |")
        time.sleep(1)
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "iverify_probe.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
