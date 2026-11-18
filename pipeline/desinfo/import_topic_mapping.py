"""Reads docs/desinfo_topic_mapping.xlsx (sheet "Mapping", yellow columns F "Your topic", G "Your sub-topic", H "Your second topic",
I "Your sub-topic of the second topic") and updates config/desinfo_partner_topics.yaml.
Usage: python pipeline/desinfo/import_topic_mapping.py [path-to-xlsx]
Only rows with a choice change. A topic must be a Partner Finder topic id; a sub-topic must belong to its topic (the chosen one,
or the current one). Rows that do not fit are skipped and listed. Second topic: enter "none" in column H to remove it."""
import json
import sys
from pathlib import Path

import yaml
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
YAML = ROOT / "config" / "desinfo_partner_topics.yaml"


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "desinfo_topic_mapping.xlsx"
    topics = json.load(open(ROOT / "site" / "data" / "config.json", encoding="utf-8"))["categories"]["topics"]
    subs = {t["id"]: {s["id"] for s in t.get("subtopics", [])} for t in topics}
    d = yaml.safe_load(open(YAML, encoding="utf-8"))
    mp, sb, al = d["map"], d.get("sub") or {}, d.get("also") or {}
    ws = load_workbook(path, data_only=True)["Mapping"]
    changed = 0
    cell = lambda row, i: (str(row[i]).strip() if len(row) > i and row[i] else "")  # noqa: E731
    for row in ws.iter_rows(min_row=2, values_only=True):
        label, new_t, new_s, new_t2, new_s2 = row[0], cell(row, 5), cell(row, 6), cell(row, 7), cell(row, 8)
        if not label or not (new_t or new_s or new_t2 or new_s2):
            continue
        topic = new_t or mp.get(label)
        if topic not in subs:
            print(f"skipped {label}: '{topic}' is not a Partner Finder topic id")
            continue
        if new_s and new_s not in subs[topic]:
            print(f"skipped {label}: sub-topic '{new_s}' does not belong to '{topic}'")
            continue
        topic2 = None if new_t2.lower() == "none" else (new_t2 or (al.get(label) or {}).get("topic"))
        if new_t2.lower() != "none" and (new_t2 or new_s2):
            if topic2 not in subs:
                print(f"skipped {label}: second topic '{topic2}' is not a Partner Finder topic id")
                continue
            if new_s2 and new_s2 not in subs[topic2]:
                print(f"skipped {label}: sub-topic '{new_s2}' does not belong to the second topic '{topic2}'")
                continue
        if new_t and mp.get(label) != new_t:
            mp[label] = new_t
            changed += 1
            if not new_s:                      # topic changed: the old sub-topic no longer fits
                sb.pop(label, None)
        if new_s and sb.get(label) != new_s:
            sb[label] = new_s
            changed += 1
        if new_t2.lower() == "none":
            if al.pop(label, None):
                changed += 1
        elif new_t2 or new_s2:
            entry = {"topic": topic2}
            sub2 = new_s2 or ((al.get(label) or {}).get("sub") if not new_t2 else "")
            if sub2:
                entry["sub"] = sub2
            if al.get(label) != entry:
                al[label] = entry
                changed += 1
    text = open(YAML, encoding="utf-8").read().split("\nmap:\n")[0] + "\nmap:\n"
    text += "".join(f'  "{k}": {v}\n' for k, v in sorted(mp.items()))
    text += ("# Sub-topic (optional) of the Partner Finder topic above: the link then selects only this sub-topic\n"
             "# (a sub-topic id from config/categories.yaml; it must belong to the topic of the same label).\nsub:\n")
    text += "".join(f'  "{k}": {v}\n' for k, v in sorted(sb.items()))
    text += ("# Second Partner Finder topic (and optional sub-topic) for Atlas topics that belong to two topics (owner 18.11.2026).\n"
             "# The link selects the first OR the second topic (broader). Format: label: {topic: <id>, sub: <id, optional>}\nalso:\n")
    text += "".join(f'  "{k}": {{topic: {v["topic"]}' + (f', sub: {v["sub"]}' if v.get("sub") else "") + "}\n" for k, v in sorted(al.items()))
    open(YAML, "w", encoding="utf-8").write(text)
    print(f"{changed} changes")


if __name__ == "__main__":
    main()
