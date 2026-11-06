"""Evidence for very right-wing (far-right) media (owner's request 06.11.2026).

1. Wikidata: the political ideology (P1142) of media items, per country, with labels.
2. Wikipedia: members of the categories whose title contains "far-right" or "alt-right"
   and a media word (newspapers, websites, magazines, ...), plus one level of subcategories.
Output: raw/far_right/data.json.gz {"ideology": {qid: [labels]}, "categories": {category: [article titles]}}
Which ideologies/categories actually exclude an outlet is decided in config/rules.yaml."""
import json
import time

from common import get, save

SPARQL = "https://query.wikidata.org/sparql"
WIKI = "https://en.wikipedia.org/w/api.php"
MEDIA_WORDS = ("newspaper", "website", "magazine", "media", "publication", "periodical", "television",
               "radio", "podcast", "news", "blog", "YouTube", "channel")


def sparql(q):
    time.sleep(1)
    return json.loads(get(SPARQL, {"query": q, "format": "json"}, accept="application/sparql-results+json",
                          timeout=90))["results"]["bindings"]


def wiki(params):
    time.sleep(0.3)
    return json.loads(get(WIKI, {**params, "format": "json", "formatversion": 2}))


def main():
    import yaml
    from common import ROOT
    cfg = yaml.safe_load(open(ROOT / "config" / "rules.yaml", encoding="utf-8"))["exclude_far_right"]
    # 1. the Wikidata items of the ideologies named in config/rules.yaml (by English label)
    ideo_q = {}
    for label in cfg["wikidata_ideologies"]:
        try:
            for r in sparql(f'SELECT ?i WHERE {{ ?i rdfs:label "{label}"@en . ?i wdt:P31|wdt:P279 ?x . }} LIMIT 5'):
                ideo_q.setdefault(r["i"]["value"].rsplit("/", 1)[1], label)
        except RuntimeError as e:
            print("label lookup failed", label, e)
    print("ideology items:", ideo_q)
    # 2. one query: every item whose political ideology (P1142) is one of them
    ideology = {}
    values = " ".join("wd:" + q for q in ideo_q)
    for r in sparql(f"SELECT ?item ?ideo WHERE {{ VALUES ?ideo {{ {values} }} ?item wdt:P1142 ?ideo . }}"):
        q = r["item"]["value"].rsplit("/", 1)[1]
        ideology.setdefault(q, []).append(ideo_q[r["ideo"]["value"].rsplit("/", 1)[1]])
    print("Wikidata items with one of these ideologies:", len(ideology))

    cats = set()
    for term in ("far-right", "alt-right", "neo-Nazi", "white nationalist", "fascist"):
        res = wiki({"action": "query", "list": "search", "srsearch": f'intitle:"{term}"', "srnamespace": 14, "srlimit": 200})
        for h in res.get("query", {}).get("search", []):
            t = h["title"]
            if any(w.lower() in t.lower() for w in MEDIA_WORDS):
                cats.add(t)
    members = {}
    todo = sorted(cats)
    for depth in (1, 2):
        nxt = []
        for c in todo:
            res = wiki({"action": "query", "list": "categorymembers", "cmtitle": c, "cmlimit": 500, "cmtype": "page|subcat"})
            for m in res.get("query", {}).get("categorymembers", []):
                if m["ns"] == 0:
                    members.setdefault(c, []).append(m["title"])
                elif m["ns"] == 14 and depth == 1:
                    nxt.append(m["title"])
        todo = nxt
    print("Wikipedia categories:", len(members), "articles:", sum(len(v) for v in members.values()))
    save("far_right", {"ideology": ideology, "categories": members},
         {"url": SPARQL + " + " + WIKI, "licence": "Wikidata CC0; Wikipedia category titles"})


if __name__ == "__main__":
    main()
