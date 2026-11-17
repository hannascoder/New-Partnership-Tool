"""Content-gap check, step 2: UN articles -> topics. Run after pipeline/desinfo/build.py.

Input : raw/un_content (items of the last fetch), raw/desinfo_atlas (183 topics), config/desinfo_topic_synonyms.yaml
Memory: cache/un_items.json (12 months)
Output: site/data/desinfo/un_content.json  per topic: articles in the last 12 months / 90 days, per language, newest 3 links
        reports/desinfo_sources.md (adds a section on the UN feeds)
The page compares these numbers with the number of fact-checks (config/desinfo.yaml `gap`).
"""
import hashlib
import json
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from build import CACHE, CFG, OUT, ROOT, TopicMatcher, load_gz, load_json


def write_report(st, meta, n_items):
    L = ["", "## UN feeds (content-gap check)", f"Fetched: {meta.get('fetched_at', 'not fetched in the last run')} | UN articles in the last 12 months: {n_items}",
         "", "| Source | Works | Items | Note |", "|---|---|---|---|"]
    for name, f in st.items():
        L.append(f"| {name} | {'yes' if f.get('ok') else 'NO'} | {f.get('items', '')} | {f.get('error', '')} |")
    L.append("")
    L.append("Sources marked NO: correct the address in `config/un_sources.yaml`.")
    rp = ROOT / "reports" / "desinfo_sources.md"
    base = rp.read_text(encoding="utf-8") if rp.exists() else ""
    base = re.split(r"\n## UN feeds \(content-gap check\)", base)[0]
    rp.write_text(base.rstrip("\n") + "\n" + "\n".join(L) + "\n", encoding="utf-8")


def main():
    atlas = load_gz("desinfo_atlas") or {}
    topics = (atlas.get("topics") or {}).get("topics") or []
    if not topics:
        raise SystemExit("no topic list (Atlas) - run pipeline/fetch/desinfo.py first")
    matcher = TopicMatcher(topics)
    memory = {i["id"]: i for i in load_json(CACHE / "un_items.json", [])}
    for r in load_gz("un_content") or []:
        iid = hashlib.sha1(r["url"].encode()).hexdigest()[:12]
        if iid in memory or not r.get("date"):
            continue
        memory[iid] = {"id": iid, "date": r["date"], "title": r["title"], "url": r["url"], "agency": r["agency"],
                       "lang": r["lang"], "desc": r.get("claim", "")}
    cutoff = (date.today() - timedelta(days=365)).isoformat()
    items = [i for i in memory.values() if i["date"] >= cutoff]
    for i in items:
        i["topics"] = matcher.match(i["title"] + " " + i.get("desc", ""))
    items.sort(key=lambda i: i["date"], reverse=True)
    json.dump(items, open(CACHE / "un_items.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    meta = load_json(ROOT / "raw" / "un_content" / "meta.json", {})
    st = (meta.get("status") or {})
    if not items:                        # nothing collected yet: the page must not show "no UN article" everywhere
        (OUT / "un_content.json").unlink(missing_ok=True)
        write_report(st, meta, 0)
        print("no UN articles yet - un_content.json not written")
        return
    d90 = (date.today() - timedelta(days=90)).isoformat()
    per = defaultdict(lambda: {"n12": 0, "n90": 0, "langs": defaultdict(int), "top": []})
    for i in items:                      # newest first
        for q in i["topics"]:
            t = per[q]
            t["n12"] += 1
            t["n90"] += i["date"] >= d90
            t["langs"][i["lang"]] += 1
            if len(t["top"]) < 3:
                t["top"].append({"t": i["title"], "u": i["url"], "d": i["date"], "a": i["agency"], "l": i["lang"]})
    out = {"generated": date.today().isoformat(), "articles": len(items),
           "sources_ok": sum(1 for f in st.values() if f.get("ok")), "sources": len(st),
           "languages": sorted({i["lang"] for i in items}),
           "topics": {q: {**v, "langs": dict(v["langs"])} for q, v in per.items()}}
    json.dump(out, open(OUT / "un_content.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    write_report(st, meta, len(items))
    print(f"UN articles {len(items)}, topics with UN material {len(per)} of {len(topics)}")


if __name__ == "__main__":
    main()
