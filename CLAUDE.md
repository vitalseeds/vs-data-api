# vs-data-api

## Tests

- `make test` runs the default suite (no FileMaker or WooCommerce needed) and must pass on a clean checkout. See #113 for the testing strategy.
- Tests needing FileMaker or WooCommerce carry the `fmdb` or `wcapi` marker and are excluded by default.

## vsdata-doctor

`src/vs_doctor` is a standalone debugger for office staff (#118). It relies on
parts of the app: config keys, `/health`, the service name, log path, port and
release assets. They're listed in `src/vs_doctor/CLAUDE.md`. When a change
touches any of them, update the doctor and that list in the same change.

## Project board

Testing and related work (#113 and the issues linked from it) is tracked on project 5: https://github.com/orgs/vitalseeds/projects/5 (owner `vitalseeds`). WooCommerce HPOS work is tracked on project 15: https://github.com/orgs/vitalseeds/projects/15 (#116, #117 and the issues it needs: #111, #107).

An issue can be on several projects, and each project has its own Status. Always check (`gh issue view N --json projectItems`) and update the Status on **every** project the issue is on, not just project 5. Being on project 5 does not excuse skipping project 15, and vice versa. For testing work that is only on project 5, use it directly (`--owner vitalseeds --project 5`) without looking up others.

For any other issue you are asked to work on or spec, check which project it is on and keep its Status current in the same way. If it is on no project, say so and ask; don't add it silently.

Keep the board current as you work. Update an item's Status on a real transition, not on speculation, and say in your reply what you changed (board changes are visible to others):

| Status | When |
|---|---|
| Todo | Planned, not started |
| Planning | Being specced, or a plan or design is being written. Use this, not In Progress, when first asked to spec or plan an issue |
| In Progress | Implementation has started |
| In Review | PR open, or needs testing/review before merge |
| Merged for deployment | Merged, not yet deployed |
| Done | Complete / closed |

- Add any new related issue to the project.
- Skills: `testing-project-status` (this repo) shows project 5 and flags problems; `project-links`, `project-update` and `issue-context` (user-level, in `~/.claude/skills`) list, set and look up status. This repo is only linked to project 3 ("VS data consolidation"), so always pass `--owner vitalseeds --project N` explicitly (5 for testing, 15 for HPOS), e.g. `project-update --owner vitalseeds --project 5 "In Review" 108`.
- The `gh` token needs the `project` scope (`gh auth refresh -s project`).
