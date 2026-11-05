"""Reads the members out of the saved network pages (raw/networks/*.html.gz).

Output: work/networks.json, one entry per member:
  {"list": id, "name": ..., "wikipedia": title or null, "website": url or null,
   "country_text": as written, "country": ISO alpha-3 or null}
and a short summary in reports/networks.md (members per list, unmatched
country names). Lists whose page is built by JavaScript (IFCN, Covering
Climate Now) are not readable from the saved page and are reported as such.
"""
import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from countrymatch import known, to_iso3  # noqa: E402
from htmllists import own_text, parse, walk, wiki_link  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "raw" / "networks"
SKIP_CLASSES = {"navbox", "reflist", "references", "toc", "mw-references-wrap", "sidebar",
                "hatnote", "metadata", "ambox", "mbox-small", "portalbox", "noprint"}


def page(list_id):
    path = RAW / f"{list_id}.html.gz"
    return parse(gzip.open(path, "rt", encoding="utf-8").read()) if path.exists() else None


def entry(list_id, name, country_text, wikipedia=None, website=None):
    name = re.sub(r"\s+", " ", (name or "")).strip(" ,;:-–")
    return {"list": list_id, "name": name, "wikipedia": wikipedia or None, "website": website,
            "country_text": country_text, "country": to_iso3(country_text) if country_text else None}


def sdg_media_compact():
    root = page("sdg_media_compact")
    out = []
    for li in root.find_all("li"):
        a = li.first("a")
        txt = li.text()
        m = re.match(r"^(.*),\s*([^,]+)$", txt)
        if not a or not m or not known(m.group(2)):
            continue
        out.append(entry("sdg_media_compact", a.text() or m.group(1), m.group(2).strip(),
                         website=a.attrs.get("href")))
    return out


def efcsn():
    """Cards on the page: <p class="... text-xl font-bold">Name</p>, then
    "from" + <span class="... font-bold">Country</span>."""
    root = page("efcsn_signatories")
    out, name = [], None
    for node in walk(root):
        cls = node.classes()
        if node.tag == "p" and {"text-xl", "font-bold"} <= cls:
            name = node.text()
        elif node.tag == "span" and "font-bold" in cls and name:
            out.append(entry("efcsn_signatories", name, node.text()))
            name = None
    return out


def wikipedia_list(list_id, item_must_link=False):
    """Generic reader for Wikipedia list pages organised by country: by
    headings (state media) or by a country item with a nested list (news
    agencies). Each item: first article link = the outlet."""
    root = page(list_id)
    out = []
    heading_country = None
    for node in walk(root):
        if node.tag in ("h2", "h3", "h4"):
            t = node.text()
            heading_country = t if known(t) else (None if node.tag == "h2" else heading_country)
            continue
        if node.tag != "li":
            continue
        if any(SKIP_CLASSES & a.classes() for a in node.ancestors() if hasattr(a, "classes")):
            continue
        title, link_text = wiki_link(node)
        text = own_text(node)
        if not text or (title and known(title) and node.first("ul")):
            continue  # a country item that holds a nested list
        # country: nearest parent item that is a country, else the heading
        country = None
        for anc in node.ancestors():
            if anc.tag == "li":
                t, _ = wiki_link(anc)
                if t and known(t):
                    country = t
                    break
        country = country or heading_country
        if not country:
            continue
        starts_with_link = bool(link_text) and text.startswith(link_text)
        if item_must_link and not starts_with_link:
            continue
        name = link_text if starts_with_link else re.split(r" from | \(|, | – | - ", text)[0]
        if len(name.split()) > 8:
            continue  # a sentence, not a name
        out.append(entry(list_id, name, country, wikipedia=title if starts_with_link else None))
    return out


PARSERS = {
    "sdg_media_compact": sdg_media_compact,
    "efcsn_signatories": efcsn,
    "news_agencies": lambda: wikipedia_list("news_agencies"),
    "state_media": lambda: wikipedia_list("state_media"),
    "fact_checking_sites": lambda: wikipedia_list("fact_checking_sites"),
}
NOT_READABLE = {
    "ifcn_signatories": "page is built by JavaScript; data address being looked for",
    "covering_climate_now": "directory is an Airtable embed; needs a CSV export (manual snapshot)",
}


def main():
    members, report = [], ["# Network lists: what was read", "",
                           "| List | Members read | Matched to one of the 195 | Not matched |", "|---|---|---|---|"]
    unmatched = Counter()
    for list_id, fn in PARSERS.items():
        rows = fn()
        members += rows
        ok = sum(1 for r in rows if r["country"])
        for r in rows:
            if not r["country"] and not known(r["country_text"] or ""):
                unmatched[r["country_text"]] += 1
        report.append(f"| {list_id} | {len(rows)} | {ok} | {len(rows) - ok} |")
    report += ["", "Not readable from the saved page:", ""]
    report += [f"- **{k}**: {v}" for k, v in NOT_READABLE.items()]
    report += ["", "Country names not recognised (add them to config/sources/country_names.yaml):", ""]
    report += [f"- {k} ({n})" for k, n in unmatched.most_common()] or ["- none"]
    (ROOT / "work").mkdir(exist_ok=True)
    json.dump(members, open(ROOT / "work" / "networks.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "networks.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
