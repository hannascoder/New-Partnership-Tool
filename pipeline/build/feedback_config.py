"""Writes site/data/feedback-config.json from config/feedback.yaml (no private data in it)."""
import json, pathlib, yaml
root = pathlib.Path(__file__).resolve().parents[2]
cfg = yaml.safe_load((root / "config/feedback.yaml").read_text(encoding="utf-8"))
out = root / "site/data/feedback-config.json"
out.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", out)
