"""iptv-org database (https://github.com/iptv-org/database): TV channels.

channels.json = one entry per channel (country, categories, website, owners,
network, closed ...). feeds.json = broadcast feeds with languages and
broadcast areas. Kept: channels in the 195 allowed countries, not adult
content. Closed channels are kept but marked, the pipeline decides later.
"""
import json

from common import RAW, countries, get, save

API = "https://iptv-org.github.io/api"


def main():
    allowed = countries()
    channels = json.loads(get(f"{API}/channels.json", timeout=300))
    feeds = json.loads(get(f"{API}/feeds.json", timeout=300))
    categories = json.loads(get(f"{API}/categories.json"))
    feeds_by_channel = {}
    for f in feeds:
        feeds_by_channel.setdefault(f.get("channel"), []).append({
            "id": f.get("id"), "name": f.get("name"), "is_main": f.get("is_main"),
            "languages": f.get("languages"), "broadcast_area": f.get("broadcast_area"),
            "video_format": f.get("video_format")})
    kept = []
    for c in channels:
        if (c.get("country") or "").upper() not in allowed or c.get("is_nsfw"):
            continue
        rec = {k: c.get(k) for k in ("id", "name", "alt_names", "network", "owners",
                                      "country", "subdivision", "city", "categories",
                                      "launched", "closed", "replaced_by", "website")}
        rec["feeds"] = feeds_by_channel.get(c.get("id"), [])
        kept.append(rec)
    # region lists (code -> countries), used for reach (config/audience_groups.yaml)
    regions = get("https://raw.githubusercontent.com/iptv-org/database/master/data/regions.csv", accept="text/csv")
    (RAW / "iptv_org" / "regions.csv").write_text(regions, encoding="utf-8")
    save("iptv_org", kept, {
        "url": f"{API}/channels.json + feeds.json",
        "total_in_source": len(channels),
        "kept_in_195_countries": len(kept),
        "categories_in_source": [c.get("id") for c in categories],
        "licence": "iptv-org database: The Unlicense (public domain)",
    })


if __name__ == "__main__":
    main()
