# 18b merge fix: boundary checks with brief 18's server list

**Goal:** brief 18 (the shared base) is on `main`, and `main` is merged into this branch (commit `57eba629`). Its
`control/settings/managed-mcp.json` lists the tool servers (`testapp`, `control`); brief 18b's own copy was empty. Two
boundary checks assumed the empty list and now fail (workflow run 42388041788, job `hostile`):

- `control/boundary/check.py`, `settings_checks()`: the `mcp-list` case expects "No MCP servers".
- `control/boundary/isolation.py`, line 44: the coding user's `claude mcp list` expects "No MCP servers".

Make the checks assert what they are for, with the real server list, and get the boundary workflow green again.

## What the checks must show

1. **Assistant user:** `claude mcp list` names exactly the servers in the installed `/etc/claude-code/managed-mcp.json`
   (read the names from that file; don't hard-code them). The rogue user and project servers the check plants never
   appear, and never start (the existing `mcp-started` marker). Keep the positive control (with the managed file
   removed, the rogue servers do appear).
2. **Coding user:** the same exact list and nothing else. Each listed server fails to connect, because the coding
   user can't reach the tool service's sockets (the socket checks already in `isolation.py` are the reason; keep
   them). A server that connects for the coding user is a failure.
3. Everything else in brief 18b's checks stays as it is. Don't change `control/settings/managed-mcp.json`.

If making the proxy (`launch.py proxy`) exit at once with a clear message when started by a user other than the
assistant is a few lines, do it and test it; otherwise name it as a follow-up in the report.

## Acceptance

- The boundary workflow and the base workflow pass twice on the final head.
- `reviews/18b-control-boundary/REPORT.md` gets a short section "Merge with brief 18" saying what changed and why,
  with the run IDs.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/18b-control-boundary`. Commit in small steps and push; PR #5 already
  exists. Never merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Keep it to about 6 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (high)` as a trailer to your commits.

**Model:** `gpt-6.1-sol` at `high`: a small, well-defined test change on code it wrote; xhigh isn't needed.
