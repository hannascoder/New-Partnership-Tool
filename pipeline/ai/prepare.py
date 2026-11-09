"""AI classification (step 5b), prepared without any paid service (owner, 09.11.2026):
writes a short profile per outlet that Claude reads in a chat session and classifies.

    python pipeline/ai/prepare.py COD KEN ...   (default: all countries) [--top 50]

Output: work/ai_input/<ISO3>.json  [{id, name, country, rank, website, languages, text...}]
Outlets already in cache/ai_classification.json are skipped.
The answers are stored in cache/ai_classification.json (see pipeline/ai/README.md)."""
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "classify"))


def main():
    args = sys.argv[1:]
    top = 50
    if "--top" in args:
        i = args.index("--top")
        top = int(args[i + 1])
        args = args[:i] + args[i + 2:]
    from classify import outlet_texts  # same texts as the keyword lists use
    outlets = {o["id"]: o for o in json.load(open(ROOT / "work" / "classified.json", encoding="utf-8"))
               if not o["cat"].get("excluded")}
    site = []
    for f in sorted((ROOT / "site" / "data").glob("outlets*.json")):
        site += json.load(open(f, encoding="utf-8"))
    rank = {e["i"]: e["r"] for e in site}
    tf = ROOT / "raw" / "texts" / "data.json.gz"
    wd = json.load(gzip.open(tf, "rt", encoding="utf-8")) if tf.exists() else {}
    web = {}
    for f in sorted((ROOT / "raw" / "website_check").glob("*.json.gz")):
        web.update(json.load(gzip.open(f, "rt", encoding="utf-8")))
    cf = ROOT / "cache" / "ai_classification.json"
    done = json.load(open(cf, encoding="utf-8")) if cf.exists() else {}
    out_dir = ROOT / "work" / "ai_input"
    out_dir.mkdir(parents=True, exist_ok=True)
    countries = args or sorted({o["country"] for o in outlets.values()})
    total = 0
    for c in countries:
        lst = sorted((o for o in outlets.values() if o["country"] == c and rank.get(o["id"], 9999) <= top
                      and o["id"] not in done), key=lambda o: rank[o["id"]])
        rows = []
        for o in lst:
            t = outlet_texts(o, wd, web)
            about = " | ".join(x for _, x in t["abouts"])[:700]
            desc = " | ".join(dict.fromkeys(t["descriptions"]))[:300]
            menu = ", ".join(x for x, _ in t["menu"] if len(x.split()) <= 4)[:400]
            heads = " | ".join(t["headlines"][:6])[:400]
            rows.append({"id": o["id"], "name": o["name"], "rank": rank[o["id"]], "website": o.get("website"),
                         "languages": o["languages"], "channels": o["channels"],
                         "type": o["cat"]["org_type"]["value"], "desc": desc, "about": about, "menu": menu,
                         "headlines": heads,
                         "found": [t["value"] for t in o["cat"]["topics"] if t["method"] != "default"]})
        if rows:
            json.dump(rows, open(out_dir / f"{c}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
            total += len(rows)
    print(f"{total} outlets prepared in {len(countries)} countries -> work/ai_input/")


if __name__ == "__main__":
    main()
