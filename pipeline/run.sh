#!/usr/bin/env bash
# Runs the whole pipeline in the right order (see pipeline/README.md): raw/ -> site/data/.
# Used by the automatic update (.github/workflows/update.yml) and by hand:  bash pipeline/run.sh
# About 10-15 minutes. Stops at the first step that fails.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p work
for step in normalize/networks normalize/rsf normalize/sources merge/merge classify/classify \
            validate/known_outlets validate/quality validate/reports ngo/build build/site_data; do
  echo "== $step"
  python3 pipeline/$step.py > "work/$(basename $step).log" 2>&1 || { echo "FAILED: $step"; tail -30 "work/$(basename $step).log"; exit 1; }
  tail -1 "work/$(basename $step).log" | cut -c1-200
done
