"""Network and member lists: saves each page from config/sources/networks.yaml
unchanged (gzipped HTML) in raw/networks/<id>.html.gz. A page that fails keeps
its previous saved copy."""
import gzip
import json

import yaml

from common import RAW, ROOT, get, save

WIKI_API = "https://en.wikipedia.org/w/api.php"


def main():
    cfg = yaml.safe_load(open(ROOT / "config" / "sources" / "networks.yaml", encoding="utf-8"))
    folder = RAW / "networks"
    folder.mkdir(parents=True, exist_ok=True)
    status = {}
    for item in cfg["lists"]:
        try:
            if "wikipedia" in item:
                data = json.loads(get(WIKI_API, {"action": "parse", "page": item["wikipedia"],
                                                 "prop": "text|revid", "redirects": 1,
                                                 "format": "json", "formatversion": 2}))
                if "error" in data:
                    raise RuntimeError(data["error"].get("info"))
                html = data["parse"]["text"]
                where = f"wikipedia:{item['wikipedia']} (revision {data['parse'].get('revid')})"
            else:
                accept = "application/json" if item.get("format") == "json" else "text/html"
                html = get(item["url"], accept=accept, timeout=120)
                where = item["url"]
            ext = "json" if item.get("format") == "json" else "html"
            with gzip.open(folder / f"{item['id']}.{ext}.gz", "wt", encoding="utf-8") as f:
                f.write(html)
            status[item["id"]] = {"ok": True, "source": where, "bytes": len(html)}
            print("OK  ", item["id"], len(html))
        except Exception as e:
            status[item["id"]] = {"ok": False, "error": str(e)[:300]}
            print("FAIL", item["id"], e)
    save("networks", [], {"pages": status})


if __name__ == "__main__":
    main()
