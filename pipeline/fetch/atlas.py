"""The Audience Intelligence Atlas (public, hannascoder/UN-Media-Consumption-Map-copy-2):
country context shown on the Partner Finder cards, the same way the Atlas shows it
(press freedom RSF, political and internet freedom Freedom House, each with its source).
The Atlas updates itself; the Partner Finder only reads its public data file."""
import json

from common import get, save

URL = "https://raw.githubusercontent.com/hannascoder/UN-Media-Consumption-Map-copy-2/main/data/countries.json"
KEEP = ["press_freedom_rank", "press_freedom_score", "press_freedom_source", "press_freedom_edition",
        "press_freedom_rank_prev", "political_freedom_status", "political_freedom_score", "political_freedom_source",
        "internet_freedom_status", "internet_freedom_score", "internet_freedom_source"]


def main():
    data = json.loads(get(URL, timeout=180))
    out = {iso: {k: (c.get("information_freedom") or {}).get(k) for k in KEEP}
           for iso, c in data.items() if len(iso) == 3 and isinstance(c, dict)}
    save("atlas", out, {"url": URL, "fields": KEEP,
                        "licence": "Audience Intelligence Atlas data (public); sources named per value"})


if __name__ == "__main__":
    main()
