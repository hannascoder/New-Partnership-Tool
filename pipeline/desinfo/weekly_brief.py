"""Weekly brief of the disinformation monitor (owner 19.11.2026: "weekly short report for the team, automatic").

Reads the data that the daily run has built (site/data/desinfo/*.json) and writes
  reports/weekly_brief.md        the brief as text (for e-mail, issue or chat)
  site/brief.html                the same as a small web page (open from the monitor page)
  site/data/desinfo/brief.json   numbers behind it
Nothing is invented: every sentence is a rule applied to the numbers. Settings: config/desinfo.yaml (red_marker, gap) and config/desinfo_gap_suggestions.yaml.
Run: python pipeline/desinfo/weekly_brief.py            (the workflow .github/workflows/weekly-brief.yml does this every Monday)
"""
import collections
import datetime
import html
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "site" / "data" / "desinfo"
CFG = yaml.safe_load(open(ROOT / "config" / "desinfo.yaml", encoding="utf-8"))
SUG = yaml.safe_load(open(ROOT / "config" / "desinfo_gap_suggestions.yaml", encoding="utf-8"))
E = html.escape
PAGE = "https://new-partnership-tool.hannacstevens.workers.dev/desinfo.html"


def load(name, default=None):
    try:
        return json.load(open(D / name, encoding="utf-8"))
    except OSError:
        return default


def main():
    items = load("items.json", [])
    topics = {t["qid"]: t for t in load("topics.json", {"topics": []})["topics"]}
    cn = load("countries.json", {})
    un = load("un_content.json") or {"topics": {}, "articles": 0, "sources_ok": 0, "sources": 0, "languages": []}
    if not items:
        raise SystemExit("no items")
    end = datetime.date.fromisoformat(max(i["date"] for i in items))
    age = lambda i: (end - datetime.date.fromisoformat(i["date"])).days  # noqa: E731
    week = [i for i in items if age(i) < 7]
    prev = [i for i in items if 7 <= age(i) < 35]               # the 4 weeks before
    # Comparisons only with sources that already delivered in the 4 weeks before: new sources (the tool keeps adding fact-checkers)
    # would otherwise make every week look like an explosion.
    old_pubs = {i["publisher"] for i in prev}
    week_c = [i for i in week if i["publisher"] in old_pubs]
    new_pubs = sorted({i["publisher"] for i in week} - old_pubs)
    prev_week_avg = len(prev) / 4
    bc = CFG["brief"]
    start = bc["daily_collection_start"] if isinstance(bc["daily_collection_start"], datetime.date) else datetime.date.fromisoformat(str(bc["daily_collection_start"]))
    reliable_from = start + datetime.timedelta(weeks=bc["min_weeks_for_comparison"])
    reliable = end >= reliable_from            # before that the weeks of the archive are incomplete and every comparison would mislead
    en = lambda i: i.get("title_en") or i["title"]  # noqa: E731
    cname = lambda c: cn.get(c, {}).get("name", c).split(" (")[0].replace("United States of America", "USA").replace("United Kingdom of Great Britain and Northern Ireland", "UK")  # noqa: E731

    # numbers
    delta = (len(week_c) - prev_week_avg) / prev_week_avg * 100 if prev_week_avg else None
    cw = collections.Counter(q for i in week for q in i["topics"])
    cwc = collections.Counter(q for i in week_c for q in i["topics"])          # same sources only: used for "rising"
    cp = collections.Counter(q for i in prev for q in i["topics"])
    rm = CFG["red_marker"]
    rising = []
    for q, n in cwc.items():
        if q not in topics or n < rm["min_items"] or not prev or not week_c:
            continue
        share_now, share_prev = n / len(week_c), cp[q] / len(prev)
        ratio = share_now / share_prev if share_prev else None
        if ratio is None or ratio > rm["factor"]:
            rising.append((q, n, ratio))
    rising.sort(key=lambda r: (-(r[2] or 99), -r[1]))
    top_topics = [(q, n) for q, n in cw.most_common(8) if q in topics][:5]
    pub = collections.Counter(i["country"] for i in week if i["country"]).most_common(5)
    about = collections.Counter(c for i in week for c in i.get("about", [])).most_common(5)
    langs = collections.Counter(i["lang"][:2] for i in week).most_common(5)
    unw = sum(1 for i in week if i["un"])

    # gaps this week: many fact-checks, almost no UN article
    g = CFG["gap"]
    gaps = []
    for q, n in cw.items():
        t = topics.get(q)
        if not t or n < g["red_min_factchecks"]:
            continue
        u = un["topics"].get(q, {"n12": 0, "langs": {}})
        if u["n12"] <= g["red_max_un"]:
            lc = collections.Counter(i["lang"][:2] for i in week if q in i["topics"])
            sug = (SUG.get("groups") or {}).get(t["group"]) or SUG["default"]
            gaps.append((t["label"], n, u["n12"], lc.most_common(3), sug["agencies"][:3]))
    gaps.sort(key=lambda x: -x[1])

    # spotlight: the strongest rising topic with three example fact-checks
    spot = None
    if rising:
        q = rising[0][0]
        ex = [i for i in week_c if q in i["topics"]][:3]
        spot = (topics[q]["label"], rising[0][1], rising[0][2], ex)

    # data health
    meta_f = json.load(open(ROOT / "raw" / "desinfo" / "meta.json", encoding="utf-8")) if (ROOT / "raw" / "desinfo" / "meta.json").exists() else {}
    feeds = (meta_f.get("status") or {}).get("feeds") or {}
    disc = (meta_f.get("status") or {}).get("discovered_feeds") or {}
    health = [f"fact-checker feeds from the list: {sum(1 for v in feeds.values() if v.get('ok'))} of {len(feeds)} work; discovered feeds working: {disc.get('ok', 'n/a')}",
              f"UN sources: {un['sources_ok']} of {un['sources']} feeds work; {un['articles']} UN articles in the archive",
              f"last fact-check in the data: {end.isoformat()}; fact-checks in the last 7 days: {len(week)} ({len(week_c)} from sources that also delivered before; average of the 4 weeks before: {prev_week_avg:.0f})",
              f"new sources this week: {len(new_pubs)}" + (" (" + ", ".join(new_pubs[:6]) + (", ..." if len(new_pubs) > 6 else "") + ")" if new_pubs else "")]
    warn = []
    if reliable and prev_week_avg and len(week_c) < 0.4 * prev_week_avg:
        warn.append("The number of fact-checks this week is less than 40 % of the usual number: a data source may have stopped working. Please check reports/desinfo_sources.md.")
    if (datetime.date.today() - end).days > 3:
        warn.append(f"The newest fact-check is from {end.isoformat()}: the daily update may not have run. Please check the workflow 'Disinformation monitor'.")

    # ---- text
    d0 = (end - datetime.timedelta(days=6)).isoformat()
    L = [f"# Disinformation monitor: weekly brief {d0} to {end.isoformat()}", ""]
    L.append(f"**{len(week)} fact-checks** this week, {unw} of them UN-related. Open the monitor: {PAGE}")
    if not reliable:
        L.append(f"A comparison with earlier weeks is not shown yet: the archive before {start.isoformat()} is incomplete. It becomes reliable from {reliable_from.isoformat()}.")
    elif delta is not None:
        L.append(f"Against the usual week ({prev_week_avg:.0f} fact-checks a week from the same sources): {len(week_c)} this week ({delta:+.0f} %)."
                 + (f" {len(new_pubs)} new sources delivered this week and are not compared." if new_pubs else ""))
    L += ["", "## Headlines"]
    L.append("- Most fact-checked topics: " + ", ".join(f"{topics[q]['label']} ({n})" for q, n in top_topics) + ".")
    if rising:
        L.append("- **Rising" + ("" if reliable else " (early indication only, the archive of earlier weeks is incomplete)") + "** (share of all fact-checks more than " + f"{rm['factor']:g}x higher than in the 4 weeks before): " + ", ".join(f"{topics[q]['label']} ({n}" + (f", x{r:.1f}" if r else ", new") + ")" for q, n, r in rising[:5]) + ".")
    else:
        L.append("- No topic is rising strongly this week.")
    L.append("- Where: " + ", ".join(f"{cname(c)} ({n})" for c, n in pub) + " (country of the fact-checker); named in the text: " + ", ".join(f"{cname(c)} ({n})" for c, n in about) + ".")
    L.append("- Languages: " + ", ".join(f"{l} {n}" for l, n in langs) + ".")
    if spot:
        L += ["", f"## In focus: {spot[0]}", f"{spot[1]} fact-checks this week" + (f", {spot[2]:.1f} times its usual share." if spot[2] else ", new compared with the 4 weeks before.")]
        for i in spot[3]:
            L.append(f"- {i['date']} {i['publisher']}: [{en(i)}]({i['url']})")
    L += ["", "## Content gaps this week", "Many fact-checks, almost no UN article in the last 12 months:"]
    if gaps:
        for lab, n, u12, lc, ag in gaps[:6]:
            L.append(f"- **{lab}**: {n} fact-checks, {u12} UN articles; languages: " + ", ".join(f"{l} {k}" for l, k in lc) + "; possible UN contacts: " + ", ".join(ag) + ".")
    else:
        L.append("- None this week.")
    L += ["", "## Data health"] + [f"- {h}" for h in health] + [f"- **Warning:** {w}" for w in warn]
    L += ["", "_Automatic evaluation of fact-checks by independent fact-checkers; please check the originals before using it. Topics and countries are assigned by rules. Weekly numbers come from the monitor's own archive, which started on 17 November 2026._"]
    md = "\n".join(L) + "\n"
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "weekly_brief.md").write_text(md, encoding="utf-8")

    # ---- html (very small markdown: headings, bullets, bold, links)
    import re

    def inline(t):
        t = E(t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"_(.+?)_", r"<i>\1</i>", t)
        return re.sub(r"\[(.+?)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', t)
    body, in_ul = [], False
    for line in L:
        if line.startswith("- "):
            if not in_ul:
                body.append("<ul>")
                in_ul = True
            body.append(f"<li>{inline(line[2:])}</li>")
            continue
        if in_ul:
            body.append("</ul>")
            in_ul = False
        if line.startswith("# "):
            body.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.strip():
            body.append(f"<p>{inline(line)}</p>")
    if in_ul:
        body.append("</ul>")
    page = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><meta name='robots' content='noindex'>"
            "<title>Weekly brief</title><style>body{font:15px/1.5 system-ui,Segoe UI,Arial,sans-serif;max-width:820px;margin:24px auto;padding:0 16px;color:#0F1A2B}"
            "h1{color:#003D6B;font-size:22px}h2{color:#003D6B;font-size:16px;border-bottom:2px solid #009EDB;padding-bottom:2px;margin-top:22px}a{color:#0072BC}</style></head><body>"
            + "".join(body) + "</body></html>")
    (ROOT / "site" / "brief.html").write_text(page, encoding="utf-8")
    json.dump({"from": d0, "to": end.isoformat(), "week": len(week), "prev_avg": round(prev_week_avg, 1), "rising": [[topics[q]["label"], n, r] for q, n, r in rising[:8]],
               "gaps": [[g_[0], g_[1], g_[2]] for g_ in gaps[:10]], "warnings": warn}, open(D / "brief.json", "w", encoding="utf-8"), indent=1)
    print(md)


if __name__ == "__main__":
    main()
