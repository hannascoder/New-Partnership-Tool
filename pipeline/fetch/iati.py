"""IATI registry: organisations that publish development data. Keeps the NGO
types (IATI organisation type 21 international NGO, 22 national NGO,
23 regional NGO, 24 partner-country-based NGO) in the 195 countries.
Licence of the registry metadata: open (IATI)."""
import json

from common import countries, get, save

API = "https://iatiregistry.org/api/3/action/organization_list"
NGO_TYPES = {"21": "international NGO", "22": "national NGO", "23": "regional NGO",
             "24": "partner country based NGO"}
FIELDS = ["name", "title", "publisher_country", "publisher_organization_type", "publisher_iati_id",
          "publisher_description", "publisher_first_publish_date", "package_count", "state",
          "publisher_url", "publisher_contact_email"]


def main():
    allowed = countries()
    orgs, offset = [], 0
    while True:
        batch = json.loads(get(API, {"all_fields": "true", "limit": 1000, "offset": offset}))["result"]
        orgs += batch
        if len(batch) < 1000:
            break
        offset += 1000
    kept = [{k: o.get(k) for k in FIELDS} for o in orgs
            if o.get("publisher_organization_type") in NGO_TYPES
            and (o.get("publisher_country") or "").upper() in allowed and o.get("state") == "active"]
    # the list does not include website and e-mail: read them from each organisation's page
    SHOW = "https://iatiregistry.org/api/3/action/organization_show"
    for o in kept:
        if o.get("publisher_url") and o.get("publisher_contact_email"):
            continue
        try:
            r = json.loads(get(SHOW, {"id": o["name"]}, tries=2, timeout=60))["result"]
        except Exception:
            continue
        extras = {e.get("key"): e.get("value") for e in r.get("extras") or [] if isinstance(e, dict)}
        for k in ("publisher_url", "publisher_contact_email"):
            o[k] = o.get(k) or r.get(k) or extras.get(k)
    save("iati", kept, {"url": API, "total_in_source": len(orgs), "ngo_types": NGO_TYPES,
                        "licence": "IATI Registry metadata (open)"})


if __name__ == "__main__":
    main()
