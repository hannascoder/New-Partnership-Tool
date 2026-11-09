#!/usr/bin/env bash
# Saves new raw data (raw/) as a commit on the current branch. Used by the
# "Fetch sources" workflow. Argument: a short label for the commit message.
set -e
git config user.name "partner-finder-bot"
git config user.email "partner-finder-bot@users.noreply.github.com"
git add raw/
if git diff --cached --quiet; then echo "nothing new"; exit 0; fi
git commit -q -m "Raw data: $1, $(date -u +%Y-%m-%d)"
for i in 1 2 3 4; do
  # on a clash in raw/ (e.g. two runs saved the same files) the data of this run wins: it is newer
  git pull -q --rebase -X theirs origin "$GITHUB_REF_NAME" && git push -q origin "HEAD:$GITHUB_REF_NAME" && exit 0
  git rebase --abort 2>/dev/null || true
  sleep $((i * 10))
done
echo "could not push raw data" >&2
exit 1
