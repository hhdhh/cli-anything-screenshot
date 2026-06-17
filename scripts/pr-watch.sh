#!/usr/bin/env bash
# pr-watch.sh - quick status check for the open HKUDS PR + the new repo.
#
# Usage:
#   ./pr-watch.sh                # one-shot dump
#   ./pr-watch.sh --watch 60     # poll every 60s (Ctrl-C to stop)
set -euo pipefail

REPO="${REPO:-HKUDS/CLI-Anything}"
PR="${PR:-360}"
SCREEN_REPO="${SCREEN_REPO:-hhdhh/cli-anything-screenshot}"
INTERVAL="${1:-}"

dump() {
  echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') ==="
  echo "[HKUDS PR $PR]"
  gh pr view "$PR" --repo "$REPO" \
      --json number,title,state,mergeable,additions,deletions,changedFiles,commits \
      --jq '. | "#\(.number) \(.title)\n  state=\(.state) mergeable=\(.mergeable) +\(.additions)/-\(.deletions) (\(.changedFiles) files, \(.commits | length) commits)"'
  echo
  echo "[Checks]"
  gh pr checks "$PR" --repo "$REPO" 2>/dev/null | sed 's/^/  /' || true
  echo
  echo "[$SCREEN_REPO]"
  gh repo view "$SCREEN_REPO" --json name,visibility,stargazerCount,defaultBranchRef \
      --jq '"  \(.name) [\(.visibility)] stars=\(.stargazerCount) default=\(.defaultBranchRef.name)"'
  echo
}

dump

if [[ -n "$INTERVAL" && "$INTERVAL" =~ ^[0-9]+$ ]]; then
  echo "Watching every ${INTERVAL}s (Ctrl-C to stop)"
  while true; do sleep "$INTERVAL"; dump; done
fi
