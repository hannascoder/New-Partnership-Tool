"""Step 3 check: are the outlets in config/test_outlets.yaml each found exactly
once, in the right country? Writes reports/known_outlets.md."""
import json
from pathlib import Path

import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "merge"))
from merge import clean_name  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def main():
    tests = yaml.safe_load(open(ROOT / "config" / "test_outlets.yaml", encoding="utf-8"))["outlets"]
    outlets = json.load(open(ROOT / "work" / "outlets.json", encoding="utf-8"))
    lines = ["# 20 known outlets", "", "| Outlet | Result | Found as | Sources | Website | Channels | Languages |",
             "|---|---|---|---|---|---|---|"]
    ok_count = 0
    for t in tests:
        want = clean_name(t["name"])
        # match on the main name first; other names only if the main name finds nothing
        hits = [o for o in outlets if clean_name(o["name"]) == want] or \
               [o for o in outlets if want in {clean_name(n) for n in o["alt_names"]}]
        right = [o for o in hits if o["country"] == t["country"]]
        if len(right) == 1:
            ok_count += 1
            o = right[0]
            res = "✅ once"
        elif len(right) > 1:
            o, res = right[0], f"⚠️ {len(right)} times (duplicate)"
        elif hits:
            o, res = hits[0], f"⚠️ wrong country ({hits[0]['country']})"
        else:
            lines.append(f"| {t['name']} ({t['country']}) | ❌ not found | | | | | |")
            continue
        lines.append(f"| {t['name']} ({t['country']}) | {res} | {o['name']} [{o['id']}] | "
                     f"{', '.join(o['sources'])} | {o['website'] or ''} | {', '.join(o['channels'])} | "
                     f"{', '.join(o['languages'])} |")
    lines.insert(2, f"**{ok_count} of {len(tests)} found exactly once in the right country.**\n")
    (ROOT / "reports" / "known_outlets.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
