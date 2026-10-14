#!/usr/bin/env bash
# Show project 5 grouped by Status and flag likely problems.
set -euo pipefail

OWNER=vitalseeds
PROJECT=5

items=$(gh project item-list "$PROJECT" --owner "$OWNER" --limit 200 --format json)

echo "## Board"
echo "$items" | jq -r '
  [.items[] | {status: (.status // "No status"), n: .content.number, t: .content.title, type: .content.type}]
  | group_by(.status)[]
  | "\n### \(.[0].status)\n" + (map("- #\(.n) \(.t)" + (if .type == "PullRequest" then " (PR)" else "" end)) | join("\n"))'

on_board=$(echo "$items" | jq -r '.items[].content.number')

echo
echo "## Flags"
flags=0
flag() { echo "- $*"; flags=1; }

# open issues/PRs referenced from #113 (the testing plan) but not on the board
related=$(gh issue view 113 --json body -q .body | grep -oE '#[0-9]+' | tr -d '#' | sort -un)
for n in $related; do
  echo "$on_board" | grep -qx "$n" && continue
  read -r state title < <(gh issue view "$n" --json state,title -q '"\(.state) \(.title|gsub("\\s+";" "))"' 2>/dev/null || true)
  [ "${state:-}" = "OPEN" ] && flag "#$n linked from #113 but not on board: $title"
done

# open PRs: item should be In Review (or beyond)
while read -r n; do
  [ -z "$n" ] && continue
  s=$(echo "$items" | jq -r --argjson n "$n" '.items[]|select(.content.number==$n)|.status // ""')
  [ -n "$s" ] && [ "$s" != "In Review" ] && flag "open PR #$n is '$s', expected In Review"
done < <(gh pr list --state open --json number -q '.[].number')

# closed/merged items not Done; open items marked Done
while IFS=$'\t' read -r n s; do
  state=$(gh issue view "$n" --json state -q .state 2>/dev/null || echo "")
  if [ "$state" = "CLOSED" ] && [ "$s" != "Done" ]; then flag "#$n is closed but '$s'"; fi
  if [ "$state" = "OPEN" ] && [ "$s" = "Done" ]; then flag "#$n is open but Done"; fi
done < <(echo "$items" | jq -r '.items[]|"\(.content.number)\t\(.status // "")"')

[ $flags -eq 0 ] && echo "none"
exit 0
