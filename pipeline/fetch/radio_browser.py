"""Radio Browser (https://www.radio-browser.info/): all radio stations.

Keeps every station in one of the 195 allowed countries, with the fields we
use. No filtering on tags yet: which stations count as news/talk/community is
decided in step 4 (classification), based on what the data really contains.
"""
import json

from common import countries, get, save

SERVERS = ["https://de1.api.radio-browser.info", "https://de2.api.radio-browser.info",
           "https://fi1.api.radio-browser.info", "https://all.api.radio-browser.info"]
FIELDS = ["stationuuid", "name", "homepage", "countrycode", "state", "language",
          "languagecodes", "tags", "votes", "clickcount", "lastcheckok",
          "lastchangetime_iso8601", "geo_lat", "geo_long"]


def main():
    allowed = countries()
    stations, used = None, None
    for server in SERVERS:
        try:
            stations, offset, page = [], 0, 20000
            while True:  # the API returns at most `limit` stations per call
                batch = json.loads(get(f"{server}/json/stations", {
                    "hidebroken": "false", "limit": page, "offset": offset,
                    "order": "stationuuid"}, timeout=300))
                stations += batch
                print(f"{server}: {len(stations)} stations")
                if len(batch) < page:
                    break
                offset += page
            used = server
            break
        except RuntimeError as e:
            print("server failed:", e)
            stations = None
    if not stations:
        raise SystemExit("Radio Browser: no server answered")
    kept = [{k: s.get(k) for k in FIELDS} for s in stations
            if (s.get("countrycode") or "").upper() in allowed]
    save("radio_browser", kept, {
        "url": f"{used}/json/stations",
        "total_in_source": len(stations),
        "kept_in_195_countries": len(kept),
        "licence": "Radio Browser data is public domain / free to use (radio-browser.info)",
    })


if __name__ == "__main__":
    main()
