"""NGO sources, first look: saves the pages in config/sources/ngo_pages.yaml
unchanged in raw/ngo/<id>.html.gz (like networks.py)."""
import gzip
import urllib.parse

import yaml

from common import RAW, ROOT, get, save


def main():
    cfg = yaml.safe_load(open(ROOT / "config" / "sources" / "ngo_pages.yaml", encoding="utf-8"))
    folder = RAW / "ngo"
    folder.mkdir(parents=True, exist_ok=True)
    status = {}
    for p in cfg["pages"]:
        url = urllib.parse.quote(p["url"], safe=":/?&=%")
        try:
            html = get(url, accept="text/html", timeout=120)
            with gzip.open(folder / f"{p['id']}.html.gz", "wt", encoding="utf-8") as f:
                f.write(html)
            status[p["id"]] = {"ok": True, "bytes": len(html)}
            print("OK  ", p["id"], len(html))
        except Exception as e:
            status[p["id"]] = {"ok": False, "error": str(e)[:300]}
            print("FAIL", p["id"], e)
    save("ngo", [], {"pages": status})


if __name__ == "__main__":
    main()
