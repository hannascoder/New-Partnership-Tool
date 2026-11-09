"""Excel file for the owner to review the topic keyword lists:
docs/topic_keywords_review.xlsx (made from config/topic_keywords.yaml + current matches).
    python pipeline/build/keyword_review.py
Sheet 1 Overview: topic | sub-topic | SDG targets behind it | outlets found
Sheet 2 English words: strong words, section names, context words, exclusions
Sheet 3 All 9 languages: one row per sub-topic and language
The website never shows these words; this file is only for checking and suggesting changes."""
import json
from collections import Counter
from pathlib import Path

import yaml
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

ROOT = Path(__file__).resolve().parents[2]
LANGS = [("en", "English"), ("fr", "French"), ("es", "Spanish"), ("pt", "Portuguese"), ("ar", "Arabic"),
         ("ru", "Russian"), ("zh", "Chinese"), ("hi", "Hindi"), ("sw", "Kiswahili")]


def main():
    kw = yaml.safe_load(open(ROOT / "config" / "topic_keywords.yaml", encoding="utf-8"))["topics"]
    cats = yaml.safe_load(open(ROOT / "config" / "categories.yaml", encoding="utf-8"))
    label = {t["id"]: ((f"SDG {t['sdg']} " if t.get("sdg") else "") + t["label"]) for t in cats["topics"]}
    order = [t["id"] for t in cats["topics"]]
    topic_n, sub_n = Counter(), Counter()
    cf = ROOT / "work" / "classified.json"
    if cf.exists():
        for o in json.load(open(cf, encoding="utf-8")):
            if o["cat"].get("excluded"):
                continue
            for t in o["cat"]["topics"]:
                if t["method"] == "default":
                    continue
                topic_n[t["value"]] += 1
                subs = t.get("subs") or ([kw[t["value"]]["general_subtopic"]] if kw.get(t["value"], {}).get("subtopics") else [])
                for s in subs:
                    sub_n[(t["value"], s)] += 1
    wb = Workbook()
    head_font, head_fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="009EDB")
    wrap = Alignment(wrap_text=True, vertical="top")

    def sheet(ws, headers, widths, rows):
        ws.append(headers)
        for c in ws[1]:
            c.font, c.fill = head_font, head_fill
        for r in rows:
            ws.append(r)
        for i, w in enumerate(widths):
            ws.column_dimensions[chr(65 + i)].width = w
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = wrap
        ws.freeze_panes = "A2"

    ids = sorted(kw, key=lambda t: order.index(t) if t in order else 999)
    ov, en, al = [], [], []
    for tid in ids:
        t = kw[tid]
        subs = t.get("subtopics") or [{"id": None, "label": "(no sub-topics)", "strong": t.get("strong") or {}}]
        sec = ", ".join((t.get("sections") or {}).get("en", []))
        ctx = ", ".join((t.get("context") or {}).get("en", []))
        exc = ", ".join(w for ws in (t.get("exclude") or {}).values() for w in ws)
        for s in subs:
            n = sub_n[(tid, s["id"])] if s["id"] else topic_n[tid]
            gen = " (general: matches without more detail count here)" if s["id"] and s["id"] == t.get("general_subtopic") else ""
            ov.append([label.get(tid, tid), s["label"] + gen, ", ".join(s.get("targets") or []), n])
            en.append([label.get(tid, tid), s["label"], ", ".join((s.get("strong") or {}).get("en", [])), sec, ctx, exc])
            for code, lname in LANGS:
                al.append([label.get(tid, tid), s["label"], lname, ", ".join((s.get("strong") or {}).get(code, [])),
                           ", ".join((t.get("sections") or {}).get(code, []))])
    ws = wb.active
    ws.title = "Overview"
    sheet(ws, ["Topic (button)", "Sub-topic", "SDG targets behind it", "Outlets found"], [34, 70, 22, 14], ov)
    sheet(wb.create_sheet("English words"), ["Topic", "Sub-topic", "Strong words (count on their own)",
          "Section names (menu -> 'own section')", "Context words (only together with a strong word)", "Exclusions"],
          [28, 40, 80, 40, 40, 40], en)
    sheet(wb.create_sheet("All 9 languages"), ["Topic", "Sub-topic", "Language", "Strong words", "Section names"],
          [28, 40, 12, 90, 40], al)
    out = ROOT / "docs" / "topic_keywords_review.xlsx"
    wb.save(out)
    print(f"{out.relative_to(ROOT)}: {len(ov)} sub-topics")


if __name__ == "__main__":
    main()
