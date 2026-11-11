"""One rule for e-mail addresses (config/rules.yaml org_email): only organisation addresses are kept."""
import re
from pathlib import Path

import yaml

_CFG = yaml.safe_load(open(Path(__file__).resolve().parents[2] / "config" / "rules.yaml", encoding="utf-8"))["org_email"]
_STARTS = tuple(w.lower() for w in _CFG["starts"])
_CONTAINS = [w.lower() for w in _CFG["contains"]]
_FORM = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


def org_email(e):
    """the address in lower case when it is an organisation address, else None"""
    e = (e or "").replace("mailto:", "").strip().strip(".").lower()
    if not _FORM.match(e) or e.endswith((".png", ".jpg", ".gif", ".webp")):
        return None
    local = e.split("@")[0]
    return e if local.startswith(_STARTS) or any(w in local for w in _CONTAINS) else None
