"""Media Cloud directory snapshot on Zenodo (record 18189311, licence CC0).

Three files: all news sources, all geographic collections (one or more per
country, e.g. national / state & local), and which source is in which
collection. Saved unchanged (gzipped); matching collections to our 195
countries happens in step 3. Needs no API key.
"""
import gzip
import json

from common import RAW, get, save

RECORD = "https://zenodo.org/api/records/18189311"


def main():
    record = json.loads(get(RECORD))
    folder = RAW / "media_cloud"
    folder.mkdir(parents=True, exist_ok=True)
    files = {}
    for f in record.get("files", []):
        text = get(f["links"]["self"], accept="*/*", timeout=300)
        with gzip.open(folder / (f["key"] + ".gz"), "wt", encoding="utf-8") as out:
            out.write(text)
        files[f["key"]] = {"bytes": f.get("size"), "rows": text.count("\n")}
        print(f["key"], files[f["key"]])
    meta = record.get("metadata", {})
    save("media_cloud", [], {  # records live in the CSV files
        "url": RECORD,
        "title": meta.get("title"),
        "version_date": meta.get("publication_date"),
        "licence": (meta.get("license") or {}).get("id"),
        "files": files,
    })


if __name__ == "__main__":
    main()
