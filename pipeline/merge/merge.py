"""Step 3b: merges the records of all sources into outlets (one per organisation).

Input:  work/records.json (step 3a), work/networks.json, cache/id_map.json
Output: work/outlets.json, cache/id_map.json (updated), reports/merge.md

Two records are the same outlet when
  (a) they have the same website (host + path), or
  (b) the same website host and similar names, or
  (c) the same name (after cleaning) and the same country, and their
      websites do not contradict each other.
Two records from the SAME source are only merged when they have the same
cleaned name, the same country and no different website (duplicate radio
streams of one station, for example). Two Wikidata items are never merged.

Whether a merged outlet is included follows docs/KATEGORIEN.md, decision 1.
Every outlet gets a stable id (pf-000001 ...) kept in cache/id_map.json, so
corrections and "first seen" dates survive later runs.
"""
import json
import re
import urllib.parse
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "normalize"))
from countrymatch import to_iso3  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ORDER = ["wikidata", "media_cloud", "iptv_org", "radio_browser", "network"]  # who wins for name/website
NAME_STOP = {"the", "la", "le", "el", "les", "los", "las", "de", "del", "du", "des", "of", "a", "an",
             "and", "et", "y", "e", "und", "di", "da", "do", "das", "dos"}
GENERIC_TOKENS = {"radio", "tv", "television", "televisión", "fm", "am", "hd", "news", "online",
                  "channel", "canal", "live", "official", "station", "stereo", "web", "en", "vivo"}
NEWS_CLASSES = {"newspaper", "daily newspaper", "news agency", "news website", "online newspaper",
                "weekly newspaper", "local newspaper", "regional newspaper", "news magazine",
                "news media", "news portal", "digital newspaper", "free newspaper", "business newspaper",
                "community newspaper", "magazine", "weekly magazine", "monthly magazine", "public broadcaster",
                "community radio", "international broadcasting", "news broadcasting", "state media",
                "legislature broadcaster", "fact-checking organisation", "campus radio", "public radio station"}


def clean_name(name):
    """Lower case, accents removed, punctuation removed; letters of every script
    (Arabic, Chinese, Cyrillic ...) are kept."""
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", " ", s)
    s = re.sub(r"\b\d{2,3}([.,]\d)?\s*(fm|mhz)\b", " ", s)  # frequencies "98.5 fm"
    s = "".join(ch if ch.isalnum() else " " for ch in s)
    return " ".join(t for t in s.split() if t not in NAME_STOP)


def tokens(name):
    return {t for t in clean_name(name).split() if t not in GENERIC_TOKENS} or set(clean_name(name).split())


def similar(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / min(len(ta), len(tb)) >= 0.6


def site_stem(domain):
    """'bbc.co.uk/x' -> 'bbc', 'news.bbc.com' -> 'bbc': the name part of a site."""
    parts = host(domain).split(".")
    while len(parts) > 1 and (parts[-1] in ("com", "org", "net", "co", "uk", "info", "gov", "edu", "ac", "or", "ne", "go")
                              or len(parts[-1]) == 2):
        parts = parts[:-1]
    return parts[-1] if parts else ""


def host(domain):
    return (domain or "").split("/", 1)[0]


class Groups:
    """Union-find that refuses to join two groups holding different records of
    the same source (unless allowed: same-source duplicates)."""

    def __init__(self, records):
        self.parent = list(range(len(records)))
        self.sources = [Counter([r["source"]]) for r in records]
        self.rejected = 0

    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, i, j, same_source_ok=False):
        a, b = self.find(i), self.find(j)
        if a == b:
            return
        if not same_source_ok and set(self.sources[a]) & set(self.sources[b]):
            self.rejected += 1
            return
        if same_source_ok == "no-wd" and (self.sources[a]["wikidata"] and self.sources[b]["wikidata"]):
            self.rejected += 1
            return
        self.parent[b] = a
        self.sources[a] += self.sources[b]


def link(records):
    g = Groups(records)
    # same-source duplicates first (radio streams, TV feeds): same name + country + compatible site
    by_src_name = defaultdict(list)
    for i, r in enumerate(records):
        if r["source"] in ("radio_browser", "iptv_org"):
            by_src_name[(r["source"], r["country"], clean_name(r["name"]))].append(i)
    for idx in by_src_name.values():
        # same name in the same country: one station with several streams, as
        # long as the websites belong to the same site ("bbc.co.uk" = "bbc.com")
        for x in range(len(idx)):
            for y in range(x + 1, len(idx)):
                a, b = records[idx[x]], records[idx[y]]
                if not a["domain"] or not b["domain"] or site_stem(a["domain"]) == site_stem(b["domain"]):
                    g.union(idx[x], idx[y], same_source_ok="no-wd")
    # (a) exact website
    by_domain = defaultdict(list)
    for i, r in enumerate(records):
        if r["domain"]:
            by_domain[r["domain"]].append(i)
    for idx in by_domain.values():
        if len(idx) <= 6:  # a site shared by many entries is a platform, not one outlet
            for j in idx[1:]:
                a, b = records[idx[0]], records[j]
                site_item = "." in a["name"] and " " not in a["name"] or "." in b["name"] and " " not in b["name"]
                g.union(idx[0], j, same_source_ok=site_item and a["source"] == b["source"] == "wikidata")
    # (e) same English Wikipedia article (network lists <-> Wikidata)
    by_wiki = defaultdict(list)
    for i, r in enumerate(records):
        if r.get("wikipedia"):
            by_wiki[r["wikipedia"]].append(i)
    for idx in by_wiki.values():
        for j in idx[1:]:
            g.union(idx[0], j)
    # (b) same host + similar name
    by_host = defaultdict(list)
    for i, r in enumerate(records):
        if r["domain"]:
            by_host[host(r["domain"])].append(i)
    for idx in by_host.values():
        if 1 < len(idx) <= 40:
            for x in range(len(idx)):
                for y in range(x + 1, len(idx)):
                    a, b = records[idx[x]], records[idx[y]]
                    if a["source"] != b["source"] and similar(a["name"], b["name"]):
                        g.union(idx[x], idx[y])
    # (c) same cleaned name + same country, websites not contradicting
    by_name = defaultdict(list)
    for i, r in enumerate(records):
        cn = clean_name(r["name"])
        if len(cn) >= 3:
            by_name[(r["country"], cn)].append(i)
    for idx in by_name.values():
        if len(idx) <= 8:
            for x in range(len(idx)):
                for y in range(x + 1, len(idx)):
                    a, b = records[idx[x]], records[idx[y]]
                    netpair = a["source"].startswith("net:") or b["source"].startswith("net:")
                    if len(clean_name(a["name"])) < 4 and not netpair:
                        continue  # very short names ("ABC") only with a network list
                    if a["source"] != b["source"] and (netpair or not a["domain"] or not b["domain"]
                                                       or host(a["domain"]) == host(b["domain"])):
                        g.union(idx[x], idx[y])
    # (d) similar names in the same country when at least one has no website
    #     ("Radio Top Congo" / "Top Congo FM 88.4 Kinshasa")
    by_token = defaultdict(list)
    for i, r in enumerate(records):
        if r["include"] is not False:
            for t in tokens(r["name"]):
                if len(t) >= 4:
                    by_token[(r["country"], t)].append(i)
    for idx in by_token.values():
        if 1 < len(idx) <= 30:
            for x in range(len(idx)):
                for y in range(x + 1, len(idx)):
                    a, b = records[idx[x]], records[idx[y]]
                    if a["source"] != b["source"] and (not a["domain"] or not b["domain"]):
                        ta, tb = tokens(a["name"]), tokens(b["name"])
                        if min(len(ta), len(tb)) >= 2 and len(ta & tb) / min(len(ta), len(tb)) >= 0.99:
                            g.union(idx[x], idx[y])
    groups = defaultdict(list)
    for i in range(len(records)):
        groups[g.find(i)].append(records[i])
    return list(groups.values()), g.rejected


def verdict(members, nets=()):
    """Inclusion of a merged outlet (docs/KATEGORIEN.md, decision 1).
    Content evidence (a news class, a Radio Browser tag, an iptv-org category,
    Media Cloud, a network list) includes; an excluded tag/category excludes.
    Radio/TV known only from Wikidata, without any content information, counts
    like an entry "without category": only kept with a second source."""
    if any(m["source"] == "wikidata" and str(m["include_reason"]).startswith("dissolved") for m in members):
        return False, "closed according to Wikidata"
    positive = [m for m in members if m["include"] is True and (
        m["source"] in ("radio_browser", "iptv_org", "media_cloud")
        or set(m["raw"].get("classes", [])) & NEWS_CLASSES)]
    if nets and not any(m["include"] is False and m["source"] == "wikidata" for m in members):
        positive.append({"include_reason": "member of " + ", ".join(nets)})
    if positive:
        return True, positive[0]["include_reason"]
    negative = [m for m in members if m["include"] is False and m["source"] in ("radio_browser", "iptv_org")]
    if negative:
        return False, negative[0]["include_reason"]
    if any(m["include"] is False for m in members if m["source"] == "wikidata"):
        return False, next(m["include_reason"] for m in members if m["source"] == "wikidata")
    wd = [m for m in members if m["source"] == "wikidata" and m["include"] is True]
    if wd and not set(wd[0]["channels"]) <= {"radio", "tv"}:
        return True, wd[0]["include_reason"]
    if len({m["source"] for m in members}) >= 2:
        return True, "confirmed by two sources"
    if wd:
        return False, "radio/TV only in Wikidata, no content information"
    return False, members[0]["include_reason"]


def src_kind(m):
    return "network" if m["source"].startswith("net:") else m["source"]


def pick(members, field):
    for src in SOURCE_ORDER:
        for m in members:
            if src_kind(m) == src and m.get(field):
                return m[field]
    return None


def nets_in(members):
    return sorted({m["source"][4:] for m in members if m["source"].startswith("net:")})


def networks_of(members, country, networks_by):
    nets = []
    keys = [("wikipedia", m.get("wikipedia")) for m in members if m.get("wikipedia")] + \
           [("domain", host(m["domain"])) for m in members if m["domain"]] + \
           [("name", (country or m["country"], clean_name(m["name"]))) for m in members]
    for k in keys:
        for n in networks_by.get(k, []):
            if n["list"] not in nets:
                nets.append(n["list"])
    return nets


def build(members, networks_by):
    members = sorted(members, key=lambda m: SOURCE_ORDER.index(src_kind(m)))
    countries = Counter(m["country"] for m in members if m["country"])
    country = pick(members, "country")
    langs, chans, social = [], [], {}
    for m in members:
        langs += [l for l in m["languages"] if l not in langs]
        chans += [c for c in m["channels"] if c not in chans]
        for k, v in m.get("social", {}).items():
            social.setdefault(k, v)
    if any(m["website"] for m in members) and "website" not in chans:
        chans.append("website")
    if social and "social_media" not in chans:
        chans.append("social_media")
    nets = nets_in(members)
    return {
        "name": pick(members, "name"),
        "alt_names": sorted(({m["name"] for m in members} | {a for m in members for a in m.get("alt_names", [])})
                            - {pick(members, "name")})[:25],
        "website": pick(members, "website"),
        "country": country,
        "country_conflict": sorted(countries) if len(countries) > 1 else None,
        "languages": langs, "channels": chans, "social": social,
        "email": pick(members, "email"),
        "wikipedia": pick(members, "wikipedia"),
        "qid": pick(members, "qid"),
        "wikipedia_languages": max((m.get("wikipedia_languages") or 0) for m in members),
        "networks": nets,
        "network_membership": {m["source"][4:]: m["raw"].get("membership") for m in members
                               if m["source"].startswith("net:") and m["raw"].get("membership")},
        "sources": sorted({m["source"] for m in members if not m["source"].startswith("net:")} | set(nets)),
        "members": [m["key"] for m in members],
        "raw": {m["key"]: {k: v for k, v in m.items() if k in ("raw", "include_reason", "region_text",
                                                                  "city", "stream_ok", "other_countries",
                                                                  "multiple_languages", "popularity",
                                                                  "stories_per_week", "channels")}
                for m in members},
    }


def main():
    records = json.load(open(ROOT / "work" / "records.json", encoding="utf-8"))
    # Media Cloud keeps outdated duplicates of a source, labelled "(old domain)": not separate outlets
    records = [r for r in records if not (r["source"] == "media_cloud" and "old domain" in (r["name"] or "").lower())]
    networks = json.load(open(ROOT / "work" / "networks.json", encoding="utf-8"))
    networks_by = defaultdict(list)
    for n in networks:
        if n.get("wikipedia"):
            networks_by[("wikipedia", n["wikipedia"])].append(n)
        if n.get("website"):
            h = re.sub(r"^(www\d?|m)\.", "", (re.sub(r"^https?://", "", n["website"]).split("/")[0]).lower())
            networks_by[("domain", h)].append(n)
        if n.get("country"):
            networks_by[("name", (n["country"], clean_name(n["name"])))].append(n)

    # network members become records too: members not found in any other
    # source are kept as outlets of their own (e.g. small fact-checkers)
    for i, n in enumerate(networks):
        if not n.get("country") or not n.get("name"):
            continue
        url = n.get("website")
        m_safe = re.search(r"safelinks\.protection\.outlook\.com/\?url=([^&]+)", url or "")
        if m_safe:  # links pasted from Outlook: unwrap the real address
            url = urllib.parse.unquote(m_safe.group(1))
        dom = None
        if url:
            dom = re.sub(r"^(www\d?|m)\.", "", re.sub(r"^https?://", "", url).split("?")[0].rstrip("/").lower())
        records.append({"key": f"net:{n['list']}:{clean_name(n['name'])[:60]}:{n['country']}", "source": f"net:{n['list']}",
                        "name": n["name"], "alt_names": [], "website": url, "domain": dom, "country": n["country"],
                        "other_countries": [], "languages": [], "channels": [], "social": {},
                        "wikipedia": n.get("wikipedia"), "raw": {"membership": n.get("membership")},
                        "include": True, "include_reason": f"member of {n['list']}"})
    groups, rejected = link(records)

    id_file = ROOT / "cache" / "id_map.json"
    id_map = json.load(open(id_file, encoding="utf-8")) if id_file.exists() else {}
    next_no = 1 + max((int(v[3:]) for v in id_map.values()), default=0)
    today = date.today().isoformat()
    first_seen_file = ROOT / "cache" / "first_seen.json"
    first_seen = json.load(open(first_seen_file, encoding="utf-8")) if first_seen_file.exists() else {}

    outlets, excluded, used_ids = [], Counter(), set()
    for members in groups:
        ok, why = verdict(members, nets_in(members))
        if not ok:
            excluded[re.sub(r":.*", "", why)] += 1
            continue
        # keep an existing id, but never give the same id to two outlets: when a
        # group split up, the part with the most members known under that id keeps it
        known = Counter(id_map[m["key"]] for m in members if m["key"] in id_map)
        oid = next((i for i, _ in known.most_common() if i not in used_ids), None)
        if not oid:
            oid = f"pf-{next_no:06d}"
            next_no += 1
        used_ids.add(oid)
        for m in members:
            id_map[m["key"]] = oid
        first_seen.setdefault(oid, today)
        o = {"id": oid, **build(members, networks_by), "include_reason": why, "first_seen": first_seen[oid]}
        outlets.append(o)
    outlets.sort(key=lambda o: o["id"])

    (ROOT / "cache").mkdir(exist_ok=True)
    json.dump(id_map, open(id_file, "w", encoding="utf-8"), sort_keys=True, indent=0)
    json.dump(first_seen, open(first_seen_file, "w", encoding="utf-8"), sort_keys=True, indent=0)
    json.dump(outlets, open(ROOT / "work" / "outlets.json", "w", encoding="utf-8"), ensure_ascii=False)
    write_report(outlets, excluded, rejected, len(records))


def write_report(outlets, excluded, rejected, n_records):
    combos = Counter(" + ".join(s for s in SOURCE_ORDER if s in o["sources"]) or "network list only" for o in outlets)
    dupes = Counter((o["country"], clean_name(o["name"])) for o in outlets)
    dup_list = [(k, n) for k, n in dupes.most_common() if n > 1][:40]
    lines = ["# Step 3b: merged outlets", "",
             f"- Records read: {n_records}",
             f"- **Outlets after merging and inclusion rules: {len(outlets)}**",
             f"- in 2+ sources (verified): {sum(1 for o in outlets if len(o['sources']) >= 2)}",
             f"- merges refused because two different entries of the same source would have been joined: {rejected}",
             f"- with a country conflict between sources: {sum(1 for o in outlets if o['country_conflict'])}",
             "", "## Which sources each outlet comes from", "", "| Sources | Outlets |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in combos.most_common(15)]
    lines += ["", "## Merged groups that were left out", "", "| Reason | Groups |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in excluded.most_common(15)]
    lines += ["", "## Possible duplicates still left (same cleaned name, same country)", "",
              "Often different outlets with the same name (e.g. local stations); checked by hand.", ""]
    lines += [f"- {c}: {n} × \"{name}\"" for (c, name), n in dup_list] or ["- none"]
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "merge.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:12]))


if __name__ == "__main__":
    main()
