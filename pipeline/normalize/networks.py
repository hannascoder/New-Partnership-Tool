"""Reads the members out of the saved network pages (raw/networks/*.html.gz).

Output: work/networks.json, one entry per member:
  {"list": id, "name": ..., "wikipedia": title or null, "website": url or null,
   "country_text": as written, "country": ISO alpha-3 or null}
and a short summary in reports/networks.md (members per list, unmatched
country names). Lists whose page is built by JavaScript (IFCN, Covering
Climate Now) are not readable from the saved page and are reported as such.
"""
import gzip
import html as htmllib
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


MEMBER_SECTIONS = {"full members", "additional full members", "associate members", "participating members",
                   "ancillary members", "approved participant members", "institutional members"}


def union_members(list_id):
    """Broadcasting unions on Wikipedia: tables under "Full members",
    "Associate members" ... (former / past / suspended members are skipped).
    Row = country cell (flag + link) and one or more member links; a row
    without a country cell belongs to the country above (rowspan)."""
    root = page(list_id)
    if root is None:
        return []
    out, section, country = [], None, None
    for node in walk(root):
        if node.tag in ("h2", "h3", "h4"):
            t = node.text().strip().lower()
            section = t if t in MEMBER_SECTIONS else None
            continue
        if section is None or node.tag != "tr":
            continue
        cells = [c for c in node.children if not isinstance(c, str) and c.tag in ("td", "th")]
        if not cells or all(c.tag == "th" for c in cells):
            continue
        first_title, first_text = wiki_link(cells[0])
        has_flag = any("flagicon" in n.classes() for n in walk(cells[0]))
        if has_flag or (first_title and known(first_title)) or known(cells[0].text()):
            country = cells[0].text() or first_title  # may be a place outside the 195 -> no country
            rest = cells[1:]
        else:
            rest = cells
        for c in rest:
            for a in c.find_all("a"):
                href = a.attrs.get("href") or ""
                title = htmllib.unescape(a.attrs.get("title") or "")
                if not href.startswith("/wiki/") or ":" in href[6:] or known(title):
                    continue
                out.append({**entry(list_id, a.text() or title, country, wikipedia=title),
                            "membership": section})
    return out


def ifcn():
    """IFCN signatories from the list's own data address (raw/networks/ifcn_signatories_api.json.gz).
    Kept: "Verified Signatory" and "In Renewal" (still listed by IFCN); "Expired Signatory" is left out.
    Countries are UN M49 numbers."""
    path = RAW / "ifcn_signatories_api.json.gz"
    if not path.exists():
        return []
    import csv
    m49 = {int(r["m49"]): r for r in csv.DictReader(open(ROOT / "config" / "countries.csv", encoding="utf-8"))}
    out = []
    for o in json.load(gzip.open(path, "rt", encoding="utf-8"))["organizations"]:
        if o.get("expired") or o.get("signatory_status") not in ("Verified Signatory", "In Renewal"):
            continue
        own = o.get("organization_owner") or {}
        country = next((m49[c] for c in own.get("countries") or [] if c in m49), None)
        web = (own.get("website") or "").strip() or None
        if web and not web.lower().startswith("http"):
            web = "https://" + web
        e = entry("ifcn_signatories", o.get("name"), country["name"] if country else None, website=web)
        if country:
            e["country"] = country["iso3"]
        out.append(e)
    return out


def occrp():
    """OCCRP member centres: COUNTRY heading (upper case), then outlet name, then a description.
    Region headings and the "regional partners" part (networks, not outlets) are skipped."""
    path = RAW / "occrp_network.html.gz"
    if not path.exists():
        return []
    raw = gzip.open(path, "rt", encoding="utf-8").read()
    raw = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S)
    lines = [htmllib.unescape(" ".join(t.split())) for t in re.sub(r"<[^>]+>", "\n", raw).split("\n")]
    lines = [t for t in lines if t]
    out, country = [], None
    for i, t in enumerate(lines):
        if "REGIONAL PARTNERS" in t:
            break
        if t.isupper() and known(t.title()):
            country = t.title()
            continue
        if t.isupper():
            country = None if not known(t.title()) else country
            continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if country and len(t) <= 80 and len(nxt) > 120 and not t.endswith("."):
            out.append(entry("occrp_network", t, country))
    return out


PARSERS = {
    "occrp_network": occrp,
    "sdg_media_compact": sdg_media_compact,
    "ifcn_signatories": ifcn,
    "efcsn_signatories": efcsn,
    "news_agencies": lambda: wikipedia_list("news_agencies"),
    "state_media": lambda: wikipedia_list("state_media"),
    "fact_checking_sites": lambda: wikipedia_list("fact_checking_sites"),
    "ebu_members": lambda: union_members("ebu_members"),
    "abu_members": lambda: union_members("abu_members"),
    "asbu_members": lambda: union_members("asbu_members"),
    "cbu_members": lambda: union_members("cbu_members"),
}
NOT_READABLE = {
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
