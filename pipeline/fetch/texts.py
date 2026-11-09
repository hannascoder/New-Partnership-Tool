"""Short texts about each outlet, for the topic keyword lists (plan T2).

For every outlet that has a Wikidata item (cache/id_map.json, keys "wd:Q..."):
  - the Wikidata description in the 9 UN News languages
  - the introduction of its Wikipedia article (English first, otherwise the
    first of the other 8 languages that has an article), at most 1,200 characters

Output: raw/texts/data.json.gz  {qid: {"desc": {lang: text}, "wiki": lang, "intro": text}}
Open data (Wikidata CC0, Wikipedia CC BY-SA); free API, no key.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, get, save  # noqa: E402

LANGS = ["en", "fr", "es", "ar", "ru", "zh", "hi", "pt", "sw"]  # UN News languages


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def main():
    id_map = json.load(open(ROOT / "cache" / "id_map.json", encoding="utf-8"))
    qids = sorted({k[3:] for k in id_map if k.startswith("wd:Q")})
    print(f"{len(qids)} Wikidata items")
    out, titles = {}, {}  # titles: wiki lang -> {title: qid}
    t0 = time.time()
    for batch in chunks(qids, 50):
        try:
            data = json.loads(get("https://www.wikidata.org/w/api.php", {
                "action": "wbgetentities", "ids": "|".join(batch), "props": "descriptions|sitelinks",
                "languages": "|".join(LANGS), "sitefilter": "|".join(l + "wiki" for l in LANGS),
                "format": "json"}))
        except Exception as e:  # keep going; a missing batch is reported in meta
            print("batch failed:", e)
            continue
        for q, ent in (data.get("entities") or {}).items():
            desc = {l: d["value"] for l, d in (ent.get("descriptions") or {}).items()}
            links = ent.get("sitelinks") or {}
            wiki = next((l for l in LANGS if l + "wiki" in links), None)
            out[q] = {"desc": desc}
            if wiki:
                out[q]["wiki"] = wiki
                titles.setdefault(wiki, {})[links[wiki + "wiki"]["title"]] = q
    print(f"descriptions: {len(out)} items, {time.time() - t0:.0f}s")
    intros = 0
    for wiki, tmap in titles.items():
        for batch in chunks(sorted(tmap), 20):
            try:
                data = json.loads(get(f"https://{wiki}.wikipedia.org/w/api.php", {
                    "action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1, "exlimit": 20,
                    "redirects": 1, "titles": "|".join(batch), "format": "json"}))
            except Exception as e:
                print("extracts failed:", wiki, e)
                continue
            q = data.get("query") or {}
            back = {}
            for n in (q.get("normalized") or []) + (q.get("redirects") or []):
                back[n["to"]] = back.get(n["from"], n["from"])
            for page in (q.get("pages") or {}).values():
                t = page.get("title")
                qid = tmap.get(t) or tmap.get(back.get(t, ""))
                text = (page.get("extract") or "").strip()
                if qid and text:
                    out[qid]["intro"] = text[:1200]
                    intros += 1
    print(f"Wikipedia introductions: {intros}, {time.time() - t0:.0f}s")
    save("texts", out, {"languages": LANGS, "items": len(qids), "with_intro": intros,
                        "urls": ["https://www.wikidata.org/w/api.php", "https://<lang>.wikipedia.org/w/api.php"]})


if __name__ == "__main__":
    main()
