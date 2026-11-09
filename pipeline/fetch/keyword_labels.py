"""Keyword lists for ALL languages (owner's request 09.11.2026: "no language may fall behind").

The topic and audience word lists (config/topic_keywords.yaml, config/audience_keywords.yaml)
are written by hand in the 9 UN News languages. For every other language this script takes
the names of the same concepts from Wikidata (open, CC0; names written by people, often
native speakers):
  1. every English strong word is looked up on Wikidata (exact name or alias, English)
  2. unclear words are skipped: a single short word, or an item that is a person, place,
     work (film, song, book ...), company or disambiguation page
  3. the names and aliases of the item in every language are saved

Output: raw/keyword_labels/data.json.gz
  {"terms": {english word: {"qid": ..., "topic": ..., "sub": ..., "labels": {lang: [names]}}},
   "skipped": {english word: reason}}
Hits from these words count at most as "Reports on it" (decision 09.11.2026), because
nobody checks them by hand.
"""
import json
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, get, save  # noqa: E402

HAND = {"en", "fr", "es", "pt", "ar", "ru", "zh", "hi", "sw"}  # written by hand already
API = "https://www.wikidata.org/w/api.php"
# descriptions that show the item is NOT the concept we mean
BAD = ("disambiguation", "family name", "given name", "surname", "album", "film", "song", "single by", "band",
       "television series", "tv series", "novel", "book", "village", "city", "town", "river", "municipality",
       "commune", "company", "magazine", "newspaper", "journal", "video game", "painting", "episode",
       "human settlement", "racehorse", "species of", "genus", "football club", "politician", "actor", "singer")


def words():
    out = {}
    for f, kind in (("topic_keywords.yaml", "topic"), ("audience_keywords.yaml", "audience")):
        cfg = yaml.safe_load(open(ROOT / "config" / f, encoding="utf-8"))["topics"]
        for tid, t in cfg.items():
            subs = t.get("subtopics") or [{"id": None, "strong": t.get("strong") or {}}]
            for s in subs:
                for w in (s.get("strong") or {}).get("en", []):
                    w = str(w).strip()
                    if w.endswith("*") or w.startswith("#"):
                        continue
                    out.setdefault(w.lower(), {"kind": kind, "topic": tid, "sub": s.get("id")})
    return out


def main():
    terms = words()
    print(f"{len(terms)} English words")
    found, skipped = {}, {}
    t0 = time.time()
    for w, meta in sorted(terms.items()):
        if len(w.split()) == 1 and len(w) < 7:
            skipped[w] = "single short word (too ambiguous)"
            continue
        try:
            data = json.loads(get(API, {"action": "wbsearchentities", "search": w, "language": "en", "type": "item",
                                        "limit": 5, "format": "json"}))
        except Exception as e:
            skipped[w] = f"search failed: {e}"[:80]
            continue
        pick = None
        for hit in data.get("search") or []:
            label = (hit.get("label") or "").lower()
            aliases = [a.lower() for a in (hit.get("aliases") or [])]
            match = (hit.get("match") or {}).get("text", "").lower()
            if w not in [label, match] + aliases:
                continue
            desc = (hit.get("description") or "").lower()
            if any(b in desc for b in BAD):
                continue
            pick = hit
            break
        if not pick:
            skipped[w] = "no exact Wikidata match"
            continue
        found[w] = {**meta, "qid": pick["id"], "description": pick.get("description")}
    print(f"matched {len(found)}, skipped {len(skipped)}, {time.time() - t0:.0f}s")
    qids = sorted({v["qid"] for v in found.values()})
    labels = {}
    for i in range(0, len(qids), 50):
        try:
            data = json.loads(get(API, {"action": "wbgetentities", "ids": "|".join(qids[i:i + 50]),
                                        "props": "labels|aliases", "format": "json"}))
        except Exception as e:
            print("labels failed:", e)
            continue
        for q, ent in (data.get("entities") or {}).items():
            per = {}
            for lang, l in (ent.get("labels") or {}).items():
                per.setdefault(lang.split("-")[0], set()).add(l["value"])
            for lang, lst in (ent.get("aliases") or {}).items():
                for a in lst[:3]:
                    per.setdefault(lang.split("-")[0], set()).add(a["value"])
            labels[q] = {lang: sorted(v) for lang, v in per.items() if lang not in HAND}
    for w, v in found.items():
        v["labels"] = labels.get(v["qid"], {})
    langs = {lang for v in found.values() for lang in v["labels"]}
    save("keyword_labels", {"terms": found, "skipped": skipped},
         {"matched": len(found), "skipped": len(skipped), "languages": len(langs), "url": API})


if __name__ == "__main__":
    main()
