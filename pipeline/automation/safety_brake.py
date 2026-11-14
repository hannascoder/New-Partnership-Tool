"""Automatic update: safety brake (owner's rule 06.11.2026).

Compares the freshly built website data with the published one (the last commit) and stops the
update (exit code 1: nothing is published, the owner gets a message) when too much has disappeared -
a sign that a source failed or changed its format, not that thousands of outlets closed.

Limits: config/rules.yaml automation (max_drop, max_source_drop).
Input: site/data/stats.json (new) and the same file in the last commit.
"""
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def main():
    if "--numbers" in sys.argv:  # one line for the commit message of the automatic update
        st = json.load(open(ROOT / "site" / "data" / "stats.json", encoding="utf-8"))
        print(f"{st['outlets']:,} outlets, {st['ngos']:,} organisations")
        return
    auto = (yaml.safe_load(open(ROOT / "config" / "rules.yaml", encoding="utf-8")).get("automation") or {})
    new = json.load(open(ROOT / "site" / "data" / "stats.json", encoding="utf-8"))
    try:
        old = json.loads(subprocess.run(["git", "show", "HEAD:site/data/stats.json"], cwd=ROOT, capture_output=True,
                                        text=True, check=True).stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        print("safety brake: no earlier numbers to compare with - passed")
        return
    problems = []

    def check(label, a, b, limit):
        if a and (a - b) / a > limit:
            problems.append(f"{label}: {a:,} -> {b:,} (minus {100 * (a - b) / a:.0f} %, limit {100 * limit:.0f} %)")
    check("outlets shown", old.get("outlets", 0), new.get("outlets", 0), auto.get("max_drop", 0.10))
    check("organisations shown", old.get("ngos", 0), new.get("ngos", 0), auto.get("max_drop", 0.10))
    for src, n in (old.get("sources") or {}).items():
        if n >= auto.get("min_source_size", 1000):
            check(f"outlets from source '{src}'", n, (new.get("sources") or {}).get(src, 0), auto.get("max_source_drop", 0.25))
    print(f"safety brake: outlets {old.get('outlets', 0):,} -> {new.get('outlets', 0):,}, "
          f"organisations {old.get('ngos', 0):,} -> {new.get('ngos', 0):,}")
    if problems:
        print("STOPPED - too much disappeared, nothing is published:")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    print("passed")


if __name__ == "__main__":
    main()
