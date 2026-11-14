"""Quality check: how many topic assignments are right?

config/quality_sample.csv holds 200 randomly drawn outlets whose topics were checked by hand once
(14.11.2026): every topic an outlet had then is marked "ok" or "wrong", and every outlet "ok" or
"not_media". This script compares that list with the current data at every pipeline run and writes
reports/quality.md, so the effect of every rule change shows as a number.

It needs no manual work: assignments that are new since the check are listed as "not checked yet".
Input: work/classified.json. Output: reports/quality.md
"""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAMES = {1: "Specialist", 2: "Has a section on it", 3: "Reports on it"}


def main():
    rows = list(csv.DictReader(open(ROOT / "config" / "quality_sample.csv", encoding="utf-8")))
    cats = __import__("yaml").safe_load(open(ROOT / "config" / "categories.yaml", encoding="utf-8"))
    merged = {t["id"]: t["merged_into"].split("/")[0] for t in cats["topics"] if t.get("merged_into")}
    verdict, entries, then = {}, {}, Counter()
    for r in rows:
        if r["topic"] == "_entry":
            entries[r["outlet_id"]] = (r["verdict"], r["evidence_when_checked"], r["name"])
            continue
        key = (r["outlet_id"], merged.get(r["topic"], r["topic"]))
        # two checked topics merged into one: wrong only if both were wrong
        verdict[key] = "ok" if "ok" in (verdict.get(key), r["verdict"]) else r["verdict"]
        then[(int(r["strength_when_checked"]), r["verdict"])] += 1
    outlets = {o["id"]: o for o in json.load(open(ROOT / "work" / "classified.json", encoding="utf-8"))}
    now, unchecked, still_wrong, lost_ok = Counter(), [], [], 0
    shown_bad, gone_bad = [], []
    for oid, (v, why, name) in entries.items():
        o = outlets.get(oid)
        shown = bool(o) and not o["cat"].get("excluded") and not o["cat"].get("hidden")
        if v == "not_media":
            (shown_bad if shown and not (o["cat"].get("website_warning")) else gone_bad).append((oid, name, why))
        if not shown:
            continue
        have = set()
        for t in o["cat"]["topics"]:
            if t["method"] == "default" or t["value"] in ("general_news", "community_local"):
                continue
            have.add(t["value"])
            v2 = verdict.get((oid, t["value"]))
            if v2 is None:
                unchecked.append((oid, name, t["value"], t.get("strength", 1), t["source"]))
                continue
            now[(t.get("strength", 1), v2)] += 1
            if v2 == "wrong":
                still_wrong.append((oid, name, t["value"], t.get("strength", 1), t["source"]))
        lost_ok += sum(1 for (i, tp), v2 in verdict.items() if i == oid and v2 == "ok" and tp not in have)

    def table(c):
        out = ["| Strength | Checked | Wrong | Share wrong |", "|---|---|---|---|"]
        tot = [0, 0]
        for s in (1, 2, 3):
            n, w = c[(s, "ok")] + c[(s, "wrong")], c[(s, "wrong")]
            tot[0] += n
            tot[1] += w
            out.append(f"| {NAMES[s]} | {n} | {w} | {100 * w / n:.0f} % |" if n else f"| {NAMES[s]} | 0 | 0 | - |")
        strong = [c[(1, "ok")] + c[(1, "wrong")] + c[(2, "ok")] + c[(2, "wrong")], c[(1, "wrong")] + c[(2, "wrong")]]
        out.append(f"| **All** | {tot[0]} | {tot[1]} | **{100 * tot[1] / max(tot[0], 1):.0f} %** |")
        out.append(f"| **Shown by default** (without \"Reports on it\") | {strong[0]} | {strong[1]} | **{100 * strong[1] / max(strong[0], 1):.0f} %** |")
        return out

    lines = ["# Quality check: topic assignments of 200 random outlets", "",
             "200 outlets drawn at random on 14.11.2026; every topic they had was checked by hand once",
             "(config/quality_sample.csv). This report is rewritten at every data run.", "",
             "## When the list was checked (14.11.2026, before the changes)", ""] + table(then) + [
             "", "## Now", ""] + table(now) + ["",
             f"- Right assignments from the check that are no longer made: {lost_ok}",
             f"- Assignments made now that were not there at the check (not checked yet): {len(unchecked)}",
             f"- Of the {len(shown_bad) + len(gone_bad)} entries that are not media outlets (or whose website was taken over): "
             f"{len(gone_bad)} are now hidden or carry a warning, {len(shown_bad)} are still shown without a warning.", ""]
    if still_wrong:
        lines += ["## Wrong assignments still made", "", "| Id | Name | Topic | Strength | Reason |", "|---|---|---|---|---|"]
        lines += [f"| {i} | {n} | {t} | {NAMES.get(s, s)} | {src[:100]} |" for i, n, t, s, src in still_wrong]
    if shown_bad:
        lines += ["", "## Not media, still shown", "", "| Id | Name | Why |", "|---|---|---|"]
        lines += [f"| {i} | {n} | {w} |" for i, n, w in shown_bad]
    if unchecked:
        lines += ["", "## New assignments, not checked yet", "", "| Id | Name | Topic | Strength | Reason |", "|---|---|---|---|---|"]
        lines += [f"| {i} | {n} | {t} | {NAMES.get(s, s)} | {src[:100]} |" for i, n, t, s, src in unchecked[:80]]
    (ROOT / "reports" / "quality.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:26]))


if __name__ == "__main__":
    main()
