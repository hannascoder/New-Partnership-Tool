"""RSF World Press Freedom Index (rsf.org/en/index, saved in raw/networks/rsf_index.html.gz):
category per country, newest year. Category 5 = "very serious situation".
Output: work/rsf.json {iso3: {"category": 1-5, "label": ..., "score": ..., "rank": ..., "year": ...}}"""
import gzip
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LABELS = {1: "good", 2: "satisfactory", 3: "problematic", 4: "difficult", 5: "very serious"}
ITEM = re.compile(r'country-list-item js-country-name ([A-Z]{3})" data-pays-name="([^"]+)" '
                  r'data-fiche-pays-url="[^"]*/(\d{4})"><div><span class="country-list-item__color general '
                  r'bg-color-(\d)"></span>\s*<span class="country-list-item__position">(\d+)</span>\s*'
                  r'<span class="country-list-item__name">[^<]*</span>\s*<span class="country-list-item__score">([\d.]+)')


def main():
    s = gzip.open(ROOT / "raw" / "networks" / "rsf_index.html.gz", "rt", encoding="utf-8").read()
    out = {}
    for iso, name, year, cat, rank, score in ITEM.findall(s):
        out.setdefault(iso, {"name": name, "category": int(cat), "label": LABELS[int(cat)],
                             "rank": int(rank), "score": float(score), "year": int(year)})
    json.dump(out, open(ROOT / "work" / "rsf.json", "w", encoding="utf-8"), indent=0)
    very = sorted(v["name"] for v in out.values() if v["category"] == 5)
    print(f"RSF {next(iter(out.values()))['year'] if out else '?'}: {len(out)} countries, "
          f"{len(very)} 'very serious': {', '.join(very)}")


if __name__ == "__main__":
    main()
