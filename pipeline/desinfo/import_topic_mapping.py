"""Reads docs/desinfo_topic_mapping.xlsx (sheet "Mapping", yellow columns E "Your topic" and F "Your sub-topic") and updates
config/desinfo_partner_topics.yaml. Usage: python pipeline/desinfo/import_topic_mapping.py [path-to-xlsx]
Only rows with a choice change. A topic must be a Partner Finder topic id; a sub-topic must belong to the topic (the chosen one,
or the current one). Rows that do not fit are skipped and listed."""
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
    mp, sb = d["map"], d.get("sub") or {}
    ws = load_workbook(path, data_only=True)["Mapping"]
    changed = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        label, new_t, new_s = row[0], (row[4] or "").strip(), (row[5] or "").strip()
        if not label or not (new_t or new_s):
            continue
        topic = new_t or mp.get(label)
        if topic not in subs:
            print(f"skipped {label}: '{topic}' is not a Partner Finder topic id")
            continue
        if new_s and new_s not in subs[topic]:
            print(f"skipped {label}: sub-topic '{new_s}' does not belong to '{topic}'")
            continue
        if new_t and mp.get(label) != new_t:
            mp[label] = new_t
            changed += 1
            if not new_s:                      # topic changed: the old sub-topic no longer fits
                sb.pop(label, None)
        if new_s and sb.get(label) != new_s:
            sb[label] = new_s
            changed += 1
    text = open(YAML, encoding="utf-8").read().split("\nmap:\n")[0] + "\nmap:\n"
    text += "".join(f'  "{k}": {v}\n' for k, v in sorted(mp.items()))
    text += ("# Sub-topic (optional) of the Partner Finder topic above: the link then selects only this sub-topic\n"
             "# (a sub-topic id from config/categories.yaml; it must belong to the topic of the same label).\nsub:\n")
    text += "".join(f'  "{k}": {v}\n' for k, v in sorted(sb.items()))
    open(YAML, "w", encoding="utf-8").write(text)
    print(f"{changed} changes")


if __name__ == "__main__":
    main()
