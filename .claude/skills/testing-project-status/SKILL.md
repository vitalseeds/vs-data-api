---
name: testing-project-status
description: Show the vitalseeds project 5 board (testing/refactor work) grouped by Status, and flag open issues or PRs missing from it or whose status looks stale. Use when asked about project status or before updating the board.
---

Run the script and show its output:

```
.claude/skills/testing-project-status/scripts/status.sh
```

It prints the board grouped by Status, then flags: open issues linked from #113 that are not on the board, open PRs not In Review, closed items not Done, and open items marked Done. Takes about a minute (one `gh` call per item).

Only report. Suggest fixes, and use `project-update` to apply them if asked.
