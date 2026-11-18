"""Writes docs/desinfo_topic_mapping.xlsx: every Atlas topic with its Partner Finder topic and sub-topic, for the owner to review.
The owner picks other values in the yellow columns (drop-downs); pipeline/desinfo/import_topic_mapping.py reads them back."""
import json
from pathlib import Path

import yaml
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[2]


def head(ws, n):
    for c in range(1, n + 1):
        cell = ws.cell(1, c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="003D6B")
        cell.alignment = Alignment(wrap_text=True, vertical="center")


def main():
    topics = json.load(open(ROOT / "site" / "data" / "config.json", encoding="utf-8"))["categories"]["topics"]
    pf = {t["id"]: t for t in topics}
    sub_name = {s["id"]: s["label"] for t in topics for s in t.get("subtopics", [])}
    atlas = json.load(open(ROOT / "site" / "data" / "desinfo" / "topics.json", encoding="utf-8"))["topics"]
    d = yaml.safe_load(open(ROOT / "config" / "desinfo_partner_topics.yaml", encoding="utf-8"))
    mp, sb, al = d["map"], d.get("sub") or {}, d.get("also") or {}

    wb = Workbook()
    info = wb.active
    info.title = "How to use"
    for line in ["Disinformation monitor: which Partner Finder topic and sub-topic belongs to each Atlas topic?", "",
                 "Why: when you choose a topic on the Disinformation page and click 'Open all ... in the Partner Finder', the link takes the topic along.",
                 "The Atlas list has 183 topics, the Partner Finder 38 topics with 64 sub-topics. Columns C to E show my proposal (E = an optional second topic).", "",
                 "What to do: go through sheet 'Mapping'. Where a topic belongs somewhere else, pick the right id in the yellow columns with the drop-down:",
                 "F = topic, G = sub-topic, H = second topic, I = sub-topic of the second topic. Leave the yellow cells empty to keep my proposal.",
                 "A sub-topic must belong to its topic (see sheet 'Partner Finder topics'). Column J is for comments.",
                 "Without a sub-topic the link selects the whole topic; with one, only that sub-topic (small sub-topics start on 'broad' automatically).",
                 "With a second topic the link selects the first OR the second topic (a broader list).", "",
                 "Then send the file back (or tell me the changes): the tool reads the yellow columns and updates config/desinfo_partner_topics.yaml."]:
        info.append([line])
    info.column_dimensions["A"].width = 150
    info["A1"].font = Font(bold=True, size=14, color="003D6B")

    ws = wb.create_sheet("Mapping")
    cols = ["Atlas topic (English)", "Atlas group", "Partner Finder topic now", "Partner Finder sub-topic now", "Second topic now (optional)",
            "Your topic (id)", "Your sub-topic (id)", "Your second topic (id)", "Your sub-topic of the second topic (id)", "Comment"]
    ws.append(cols)
    head(ws, len(cols))
    for t in sorted(atlas, key=lambda x: (x["group"], x["label"])):
        tp, sb_id = mp.get(t["label"], ""), sb.get(t["label"], "")
        a = al.get(t["label"]) or {}
        second = (f"{pf[a['topic']]['label']} ({a['topic']})" + (f" / {sub_name.get(a.get('sub'), '')}" if a.get("sub") else "")) if a.get("topic") in pf else ""
        ws.append([t["label"], t["group"], f"{pf[tp]['label']} ({tp})" if tp in pf else "(none)",
                   f"{sub_name[sb_id]} ({sb_id})" if sb_id in sub_name else "(whole topic)", second, "", "", "", "", ""])
    for i, w in enumerate([32, 15, 34, 56, 46, 22, 24, 22, 24, 30], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for r in range(2, ws.max_row + 1):
        for c in (6, 7, 8, 9):
            ws.cell(r, c).fill = PatternFill("solid", fgColor="FFF8DC")
        ws.cell(r, 4).alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:J{ws.max_row}"

    ref = wb.create_sheet("Partner Finder topics")
    ref.append(["Topic id", "Topic", "SDG", "Sub-topic id", "Sub-topic"])
    head(ref, 5)
    topic_rows = 0
    for tid, t in pf.items():
        ref.append([tid, t["label"], t.get("sdg") or "", "", ""])
        topic_rows += 1
        for s in t.get("subtopics", []):
            ref.append([tid, "", "", s["id"], s["label"]])
    for i, w in enumerate([22, 28, 6, 26, 110], 1):
        ref.column_dimensions[get_column_letter(i)].width = w
    # drop-downs: topic ids (column A of the reference sheet; only the first row of each topic has a name) and sub-topic ids
    n = ref.max_row
    topic_ids = ",".join(pf)                      # 38 ids fit into one list string (< 255 characters is not guaranteed): use ranges instead
    dv_t = DataValidation(type="list", formula1=f"='Partner Finder topics'!$A$2:$A${n}", allow_blank=True)
    dv_s = DataValidation(type="list", formula1=f"='Partner Finder topics'!$D$2:$D${n}", allow_blank=True)
    for dv in (dv_t, dv_s):
        dv.error = "Please pick an id from the sheet 'Partner Finder topics'."
        ws.add_data_validation(dv)
    for col in ("F", "H"):
        dv_t.add(f"{col}2:{col}{ws.max_row}")
    for col in ("G", "I"):
        dv_s.add(f"{col}2:{col}{ws.max_row}")
    wb.save(ROOT / "docs" / "desinfo_topic_mapping.xlsx")
    print("saved", ws.max_row - 1, "rows")


if __name__ == "__main__":
    main()
