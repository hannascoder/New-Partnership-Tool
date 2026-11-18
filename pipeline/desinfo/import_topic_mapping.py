"""Reads docs/desinfo_topic_mapping.xlsx (sheet "Mapping", yellow column F "Your choice") and updates
config/desinfo_partner_topics.yaml. Usage: python pipeline/desinfo/import_topic_mapping.py [path-to-xlsx]
Only rows with a choice in column F change; a choice must be an id of the Partner Finder topics (checked)."""
import json
import sys
from pathlib import Path

import yaml
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
YAML = ROOT / "config" / "desinfo_partner_topics.yaml"


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "desinfo_topic_mapping.xlsx"
    ids = {t["id"] for t in json.load(open(ROOT / "site" / "data" / "config.json", encoding="utf-8"))["categories"]["topics"]}
    mp = yaml.safe_load(open(YAML, encoding="utf-8"))["map"]
    ws = load_workbook(path, data_only=True)["Mapping"]
    changed = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        label, choice = row[0], (row[5] or "").strip()
        if not label or not choice:
            continue
        if choice not in ids:
            print(f"skipped {label}: '{choice}' is not a Partner Finder topic id")
            continue
        if mp.get(label) != choice:
            mp[label] = choice
            changed += 1
    text = open(YAML, encoding="utf-8").read().split("\nmap:\n")[0] + "\nmap:\n"
    text += "".join(f'  "{k}": {v}\n' for k, v in sorted(mp.items()))
    open(YAML, "w", encoding="utf-8").write(text)
    print(f"{changed} topics changed")


if __name__ == "__main__":
    main()
