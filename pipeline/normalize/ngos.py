"""Phase 2: NGO sources in the common record format (like sources.py for media).

Sources: UN Geneva accredited NGO list, IATI NGO publishers, ECOSOC iCSO
(lists + profile pages). Output: work/ngo_records.json + reports/ngo_records.md.
Every record has org_type "ngo"; topics, UN profile etc. are assigned later by
the classifier, from the evidence kept in "raw".
"""
import gzip
import html as htmllib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from countrymatch import to_iso3  # noqa: E402
from sources import COUNTRIES, ISO2, norm_url  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "raw"


def un_geneva():
    path = RAW / "ngo" / "un_geneva_ngo_list.html.gz"
    if not path.exists():
        return []
    s = gzip.open(path, "rt", encoding="utf-8").read()
    out = []
    for block in re.findall(r'<div class="un-box ngo-item"(.*?)</div></div></li>', s, re.S):
        name = re.search(r'class="ngo-title"[^>]*>(.*?)</a>', block, re.S)
        hq = re.search(r'class="ngo-headquarter">(.*?)</strong>', block, re.S)
        loc = re.search(r'data-location="([a-z]{2})"', block)
        mail = re.search(r'mailto:([^"]+)"', block)
        year = re.search(r"Accreditation year: <b>(\d{4})</b>", block)
        if not name:
            continue
        country = ISO2.get(loc.group(1).upper()) if loc else None
        if not country and hq:
            country = to_iso3(htmllib.unescape(hq.group(1)))
        num = re.search(r'aria-controls="ngo-(\d+)"', block)
        out.append({
            "key": f"ungva:{num.group(1) if num else len(out)}", "source": "un_geneva",
            "name": htmllib.unescape(re.sub(r"\s+", " ", name.group(1))).strip(), "alt_names": [],
            "website": None, "domain": None, "country": country, "other_countries": [],
            "languages": [], "channels": [], "social": {},
            "email": mail.group(1).strip() if mail else None,
            "raw": {"accreditation_year": year.group(1) if year else None},
            "org_type": "ngo", "include": True, "include_reason": "accredited NGO at UN Geneva",
        })
    return out


IATI_TYPES = {"21": "international NGO", "22": "national NGO", "23": "regional NGO",
              "24": "partner country based NGO"}


def iati():
    path = RAW / "iati" / "data.json.gz"
    if not path.exists():
        return []
    out = []
    for o in json.load(gzip.open(path, "rt", encoding="utf-8")):
        website, domain = norm_url(o.get("publisher_url"))
        t = o.get("publisher_organization_type")
        out.append({
            "key": f"iati:{o['name']}", "source": "iati",
            "name": (o.get("title") or o["name"]).strip(), "alt_names": [],
            "website": website, "domain": domain,
            "country": ISO2.get((o.get("publisher_country") or "").upper()), "other_countries": [],
            "languages": [], "channels": ["website"] if website else [], "social": {},
            "email": o.get("publisher_contact_email"),
            "raw": {"iati_type": IATI_TYPES.get(t), "description": (o.get("publisher_description") or "")[:2000],
                    "iati_id": o.get("publisher_iati_id")},
            "scope_hint": "international" if t == "21" else "regional" if t == "23" else "national" if t in ("22", "24") else None,
            "org_type": "ngo", "include": True, "include_reason": f"IATI publisher ({IATI_TYPES.get(t)})",
        })
    return out


def ecosoc():
    """ECOSOC iCSO: list (status, accreditations) + profile pages (parsed in
    ecosoc_profile, written once the page structure is known)."""
    path = RAW / "ecosoc" / "list.json.gz"
    if not path.exists():
        return []
    out = []
    for r in json.load(gzip.open(path, "rt", encoding="utf-8")):
        prof = ecosoc_profile(r["code"])
        out.append({
            "key": f"ecosoc:{r['code']}", "source": "ecosoc",
            "name": htmllib.unescape(r["name"]), "alt_names": [],
            "website": prof.get("website"), "domain": norm_url(prof.get("website"))[1],
            "country": prof.get("country"), "other_countries": prof.get("other_countries", []),
            "languages": [], "channels": ["website"] if prof.get("website") else [], "social": {},
            "email": prof.get("email"),
            "raw": {"ecosoc_status": r["status"], "accreditations": r["accreditations"],
                    "fields": prof.get("fields", []), "type": prof.get("type")},
            "org_type": "ngo", "include": True, "include_reason": f"ECOSOC consultative status ({r['status']})",
        })
    return out


def ecosoc_profile(code):
    path = RAW / "ecosoc" / "profiles" / f"{code}.html.gz"
    if not path.exists():
        return {}
    return {}  # filled in once the profile page structure has been checked


def main():
    recs, lines = [], ["# NGO records", "", "| Source | Records | With a country of the 195 |", "|---|---|---|"]
    for name, fn in (("ecosoc", ecosoc), ("un_geneva", un_geneva), ("iati", iati)):
        r = fn()
        ok = [x for x in r if x["country"] in COUNTRIES]
        lines.append(f"| {name} | {len(r)} | {len(ok)} |")
        recs += r
    json.dump(recs, open(ROOT / "work" / "ngo_records.json", "w", encoding="utf-8"), ensure_ascii=False)
    (ROOT / "reports" / "ngo_records.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(Counter(r["country"] for r in recs).most_common(5))


if __name__ == "__main__":
    main()
