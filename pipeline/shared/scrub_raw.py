"""Removes personal e-mail addresses from the raw data before it is saved (config/rules.yaml org_email).
Run by pipeline/fetch/commit_raw.sh; can also be run by hand: python pipeline/shared/scrub_raw.py"""
import gzip
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from org_email import org_email  # noqa: E402

RAW = Path(__file__).resolve().parents[2] / "raw"
EM = re.compile(r"(?:mailto:)?[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")


def main():
    total = 0
    for f in RAW.rglob("*"):
        if not f.is_file() or f.suffix not in (".gz", ".json", ".html", ".csv", ".txt"):
            continue
        gz = f.suffix == ".gz"
        try:
            s = gzip.open(f, "rt", encoding="utf-8").read() if gz else f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        n = [0]

        def rep(m):
            if org_email(m.group(0).replace("mailto:", "")):
                return m.group(0)
            n[0] += 1
            return ""
        s2 = EM.sub(rep, s)
        if n[0]:
            total += n[0]
            if gz:
                with gzip.open(f, "wt", encoding="utf-8") as g:
                    g.write(s2)
            else:
                f.write_text(s2, encoding="utf-8")
    print(f"personal e-mail addresses removed from raw data: {total}")


if __name__ == "__main__":
    main()
