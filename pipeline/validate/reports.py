"""Step 5: reports after every run (briefing K5), written to reports/:

  coverage.md               share of outlets with a value per filter, overall and per region,
                            plus the countries with the least information
  coverage_by_country.csv   the same for every country (open in Excel)
  sample.md                 30 random outlets with every value and its reason, to check by hand
  contradictions.md         where sources disagree or values look wrong (to check)
  changes.md                new / disappeared / changed outlets compared with the last published data

Input: work/classified.json (step 4), config/, the published website data on main (for changes).
    python pipeline/validate/reports.py
"""
import csv
import json
import random
import subprocess
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def has(o):
    """field -> True/False for one outlet (only information that a filter uses)"""
    c = o["cat"]
    topics = [t for t in c.get("topics", []) if t["method"] != "default"]
    return {
        "Language": bool(o["languages"]),
        "Channel": bool(o["channels"]),
        "Organisation type (not just 'news outlet' by default)": c["org_type"]["method"] != "default",
        "Ownership known": c["ownership"]["value"] != "unknown",
        "Scope known": c["scope"]["value"] != "unknown",
        "Reaches other countries": len(c.get("audience") or {}) > 1,
        "Topic (other than general news)": any(t["value"] != "general_news" for t in topics),
        "Topic: Specialist or own section": any(t["value"] != "general_news" and t.get("strength", 3) <= 2 for t in topics),
        "Target audience": bool(c.get("audience_groups")),
        "UN profile": bool(c.get("un_profile")),
        "Public contact (e-mail or contact page)": bool(o.get("email") or o.get("contact_page")),
        "E-mail": bool(o.get("email")),
        "Social media": bool(o.get("social") or o.get("social_urls")),
        "Website": bool(o.get("website")),
        "Website checked and answered": c.get("website_status") == "ok",
        "Active (article in the last 3 months)": bool(o.get("last_post")) and o["last_post"] >= active_since(),
        "Verified (2+ sources)": len(o["sources"]) >= 2,
    }


def active_since():
    d = date.today()
    m = d.month - 3
    return date(d.year + (m <= 0) * -1, (m - 1) % 12 + 1, min(d.day, 28)).isoformat()


def pct(n, d):
    return f"{100 * n / d:.0f} %" if d else "-"


def previous_site_data():
    """the website data last published (branch main), for the change report"""
    out = {}
    try:
        files = subprocess.run(["git", "ls-tree", "--name-only", "origin/main", "site/data/"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.split()
        cfg = {}
        if "site/data/config.json" in files:
            cfg = json.loads(subprocess.run(["git", "show", "origin/main:site/data/config.json"], cwd=ROOT,
                                            capture_output=True, text=True, check=True).stdout)
        codes = cfg.get("codes") or {}
        for f in files:
            if f.split("/")[-1].startswith("outlets") and f.endswith(".json"):
                data = json.loads(subprocess.run(["git", "show", f"origin/main:{f}"], cwd=ROOT,
                                                 capture_output=True, text=True, check=True).stdout)
                for e in data:
                    for k in ("o", "ow", "sc"):
                        if k in e and codes.get(k) and isinstance(e[k][0], int):
                            e[k][0] = codes[k][e[k][0]]
                    out[e["i"]] = e
    except Exception as e:  # no git history (e.g. first run): no change report
        print("no previous data:", e)
    return out


def main():
    outlets = [o for o in json.load(open(ROOT / "work" / "classified.json", encoding="utf-8"))
               if not o["cat"].get("excluded") and not o["cat"].get("hidden")]
    countries = {r["iso3"]: r for r in csv.DictReader(open(ROOT / "config" / "countries.csv", encoding="utf-8"))}
    rep = ROOT / "reports"
    n = len(outlets)
    flags = {o["id"]: has(o) for o in outlets}
    fields = list(next(iter(flags.values())).keys())

    # ------------------------------------------------------------ coverage
    total = {f: sum(flags[o["id"]][f] for o in outlets) for f in fields}
    by_region = defaultdict(list)
    by_country = defaultdict(list)
    for o in outlets:
        k = countries.get(o["country"]) or {}
        by_region[k.get("region") or "?"].append(o)
        by_country[o["country"]].append(o)
    regions = sorted(by_region)
    lines = ["# Coverage: how complete is the information? (step 5)", "",
             f"{n:,} outlets shown on the website, {len(by_country)} countries. Data date: {date.today()}.", "",
             "Share of outlets that have this information. A filter only finds outlets with a value",
             "(soft filters like topics never hide anyone; \"Also show outlets without this information\" helps for the others).", "",
             "| Information | All | " + " | ".join(regions) + " |", "|---|---|" + "---|" * len(regions)]
    for f in fields:
        row = [f, f"**{pct(total[f], n)}** ({total[f]:,})"]
        for r in regions:
            lst = by_region[r]
            row.append(pct(sum(flags[o["id"]][f] for o in lst), len(lst)))
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "Outlets per region: " + " · ".join(f"{r} {len(by_region[r]):,}" for r in regions), ""]
    # countries with the least information (at least 20 outlets)
    key = ["Topic (other than general news)", "Language", "Public contact (e-mail or contact page)", "Ownership known"]
    score = []
    for c, lst in by_country.items():
        if len(lst) >= 20:
            s = sum(sum(flags[o["id"]][f] for o in lst) / len(lst) for f in key) / len(key)
            score.append((s, c, len(lst)))
    score.sort()
    lines += ["## Countries with the least information (20+ outlets)", "",
              "Average of: topic, language, public contact, ownership known.", "",
              "| Country | Outlets | Topic | Language | Contact | Ownership known |", "|---|---|---|---|---|---|"]
    for s, c, cnt in score[:20]:
        lst = by_country[c]
        lines.append(f"| {countries.get(c, {}).get('name', c)} | {cnt:,} | " +
                     " | ".join(pct(sum(flags[o['id']][f] for o in lst), cnt) for f in key) + " |")
    small = sorted((len(lst), c) for c, lst in by_country.items())[:15]
    missing = [countries[c]["name"] for c in countries if c not in by_country]
    lines += ["", "## Countries with the fewest outlets", "",
              " · ".join(f"{countries.get(c, {}).get('name', c)} ({k})" for k, c in small),
              "", "Countries without any outlet: " + (", ".join(missing) or "none"), ""]
    (rep / "coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with open(rep / "coverage_by_country.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["country", "iso3", "region", "outlets"] + fields)
        for c in sorted(by_country, key=lambda c: countries.get(c, {}).get("name", c)):
            lst = by_country[c]
            w.writerow([countries.get(c, {}).get("name", c), c, countries.get(c, {}).get("region", ""), len(lst)] +
                       [f"{100 * sum(flags[o['id']][f] for o in lst) / len(lst):.0f}" for f in fields])

    # ------------------------------------------------------------ sample
    rnd = random.Random(date.today().isoformat())
    names = {1: "Specialist", 2: "Has a section on it", 3: "Reports on it"}
    sm = ["# Random sample: 30 outlets to check by hand (step 5)", "",
          "A new sample is drawn every day. For each value: what the tool says and why.",
          "Wrong? Tell Claude the id, or note it in overrides.csv.", ""]
    for o in rnd.sample(outlets, min(30, n)):
        c = o["cat"]
        k = countries.get(o["country"]) or {}
        tp = "; ".join(f"{t['value']} ({names.get(t.get('strength'), '')}: {t['source']})" for t in c["topics"])
        sm += [f"## {o['name']} — {k.get('name', o['country'])} · {o['id']}", "",
               f"- Website: {o.get('website') or '-'} (check: {c.get('website_status') or 'not checked'})",
               f"- Sources: {', '.join(o['sources'])}",
               f"- Type: {c['org_type']['value']} ({c['org_type']['source']})",
               f"- Ownership: {c['ownership']['value']} ({c['ownership']['source']})",
               f"- Scope: {c['scope']['value']} ({c['scope']['source']})",
               f"- Languages: {', '.join(o['languages']) or '-'} · Channels: {', '.join(o['channels']) or '-'}",
               f"- Topics: {tp}",
               f"- Target audience: {'; '.join(a['value'] + ' (' + a['source'] + ')' for a in c.get('audience_groups') or []) or '-'}",
               f"- UN profile: {'; '.join(u['value'] + ' (' + u['source'] + ')' for u in c.get('un_profile') or []) or '-'}",
               f"- Contact: {o.get('email') or '-'} · contact page: {o.get('contact_page') or '-'} · latest article: {o.get('last_post') or '-'}",
               ""]
    (rep / "sample.md").write_text("\n".join(sm) + "\n", encoding="utf-8")

    # ------------------------------------------------------------ contradictions
    con = ["# Contradictions and things to check (step 5)", ""]
    cc = [o for o in outlets if o.get("country_conflict")]
    con += [f"## Sources disagree on the country ({len(cc)})", "",
            "The tool uses Wikidata's country (KATEGORIEN 4). The other source's country is listed.", "",
            "| Id | Name | Used | Sources say |", "|---|---|---|---|"]
    con += [f"| {o['id']} | {o['name']} | {o['country']} | {', '.join(o['country_conflict'])} |" for o in cc[:300]]
    hint = [o for o in outlets if o["cat"].get("country_hint")]
    con += ["", f"## AI reading: probably in another country ({len(hint)})", "",
            "The tool keeps the country from Wikidata / the sources; tell Claude if one should change.", "",
            "| Id | Name | Country now | AI reading says |", "|---|---|---|---|"]
    con += [f"| {o['id']} | {o['name']} | {o['country']} | {o['cat']['country_hint']} |" for o in hint]
    dom = defaultdict(list)
    import re
    for o in outlets:
        if o.get("website"):
            d = re.sub(r"^https?://(www\d?\.)?", "", o["website"].lower()).split("/")[0]
            if d and not any(x in d for x in ("facebook.com", "youtube.com", "blogspot", "wordpress.com", "instagram.com")):
                dom[d].append(o)
    dup = [(d, lst) for d, lst in dom.items() if len(lst) > 1]
    con += ["", f"## Possible duplicates: same website, several entries ({len(dup)})", "",
            "Often fine (a TV channel and its radio share a website), sometimes a duplicate.", "",
            "| Website | Entries |", "|---|---|"]
    con += [f"| {d} | " + "; ".join(f"{o['name']} ({o['id']})" for o in lst[:5]) + " |" for d, lst in sorted(dup)[:300]]
    psb_state = [o for o in outlets if o["cat"]["org_type"]["source"].startswith("public broadcaster that is state-controlled")]
    con += ["", f"## Public broadcasters listed as state-controlled ({len(psb_state)})", "",
            "Shown as 'news outlet' + 'state-controlled' (State Media Monitor). Check if one looks wrong.", ""]
    con += [f"- {o['name']} ({o['country']}, {o['id']})" for o in psb_state[:200]]
    spec_gen = [o for o in outlets if o["cat"]["org_type"]["value"] == "fact_checker"
                and not any(t["value"] == "fact_checking" for t in o["cat"]["topics"])]
    con += ["", f"## Fact-checkers without the fact-checking topic ({len(spec_gen)})", ""]
    con += [f"- {o['name']} ({o['id']})" for o in spec_gen[:100]]
    down_active = [o for o in outlets if o["cat"].get("website_status") == "error" and o.get("last_post")]
    con += ["", f"## Website did not answer, but an article date is known ({len(down_active)})", ""]
    con += [f"- {o['name']} ({o['id']})" for o in down_active[:100]]
    (rep / "contradictions.md").write_text("\n".join(con) + "\n", encoding="utf-8")

    # ------------------------------------------------------------ changes
    prev = previous_site_data()
    ch = ["# Changes compared with the published website (branch main) (step 5)", ""]
    if not prev:
        ch.append("No published data to compare with.")
    else:
        now = {o["id"]: o for o in outlets}
        new = [o for i, o in now.items() if i not in prev]
        gone = [e for i, e in prev.items() if i not in now]
        changed = Counter()
        examples = defaultdict(list)
        for i, o in now.items():
            e = prev.get(i)
            if not e:
                continue
            for k, cur in (("o", o["cat"]["org_type"]["value"]), ("ow", o["cat"]["ownership"]["value"]),
                           ("sc", o["cat"]["scope"]["value"])):
                if k in e and e[k][0] != cur:
                    label = {"o": "type", "ow": "ownership", "sc": "scope"}[k]
                    changed[label] += 1
                    if len(examples[label]) < 10:
                        examples[label].append(f"{o['name']} ({i}): {e[k][0]} → {cur}")
        ch += [f"- New outlets: {len(new):,}", f"- No longer shown: {len(gone):,} (merged into another entry, excluded, or gone from all sources)",
               "- Changed values: " + (", ".join(f"{k} {v:,}" for k, v in changed.items()) or "none"), ""]
        for k, ex in examples.items():
            ch += [f"### Examples: {k}", ""] + [f"- {x}" for x in ex] + [""]
        ch += ["### Examples: new", ""] + [f"- {o['name']} ({o['country']}, {o['id']})" for o in new[:15]]
        ch += ["", "### Examples: no longer shown", ""] + [f"- {e.get('n')} ({e.get('c')}, {e['i']})" for e in gone[:15]]
    (rep / "changes.md").write_text("\n".join(ch) + "\n", encoding="utf-8")
    print("\n".join(lines[:len(fields) + 9]))


if __name__ == "__main__":
    main()
