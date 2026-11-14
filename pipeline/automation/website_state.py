"""Automatic update: counts how often in a row a website was DEAD at the website check.

"Dead" = the web address no longer exists (config/rules.yaml automation.dead_errors: the name is not
found, no address, connection refused). A website that only refuses automatic visits (HTTP 403, 429),
is slow or has a certificate problem is NOT dead: many large outlets block robots.
Owner's rule (06.11.2026): hidden after 3 failed checks in a row, back as soon as the website answers.

Input:  raw/website_check/*.json.gz, cache/website_fails.json
Output: cache/website_fails.json  {outlet id: [failed checks in a row, date of the last counted check]}
Every check is counted once (by its date), so running this twice changes nothing.
"""
import gzip
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def main():
    auto = (yaml.safe_load(open(ROOT / "config" / "rules.yaml", encoding="utf-8")).get("automation") or {})
    dead = [x.lower() for x in auto.get("dead_errors") or []]
    f = ROOT / "cache" / "website_fails.json"
    fails = json.load(open(f, encoding="utf-8")) if f.exists() else {}
    seen = set()
    for shard in sorted((ROOT / "raw" / "website_check").glob("*.json.gz")):
        for oid, w in json.load(gzip.open(shard, "rt", encoding="utf-8")).items():
            seen.add(oid)
            n, last = fails.get(oid, [0, ""])
            checked = w.get("checked") or ""
            if checked <= last:
                continue  # this check was counted already
            is_dead = w.get("status") == "error" and any(d in str(w.get("error") or "").lower() for d in dead)
            if is_dead:
                fails[oid] = [n + 1, checked]
            elif oid in fails:
                del fails[oid]  # it answered (or only blocked the visit): the count starts again
    for oid in [k for k in fails if k not in seen]:
        del fails[oid]
    with open(f, "w", encoding="utf-8") as out:  # one outlet per line: small, readable changes in git
        out.write("{\n" + ",\n".join(f"{json.dumps(k)}: {json.dumps(v)}" for k, v in sorted(fails.items())) + "\n}\n")
    limit = auto.get("hide_after_dead_checks", 3)
    by = {}
    for n, _ in fails.values():
        by[n] = by.get(n, 0) + 1
    print(f"websites dead at the last check(s): {len(fails)} ({', '.join(f'{k}x: {v}' for k, v in sorted(by.items()))}); "
          f"hidden from {limit} in a row: {sum(1 for n, _ in fails.values() if n >= limit)}")


if __name__ == "__main__":
    main()
