# 18d main merge: integrate Mail and 19b with the slim base

**Goal:** Mail (brief 19) and 19b (owner-visible state, stage 2) are on `main` (PR #9, squash `25528195`). Their
exact content is now merged into `pkg/18d-base-slim`. Make sure the combined head is right: nothing 19b added relies on
something 18d removed or relaxed, every asking action still has its generated managed ask rule, and the shared MCP
instructions keep what 19b's tools need. Fix what isn't right, regenerate, and verify on the combined head. Asked by
the lead (`mac-aresos-control`), 2026-11-12.

## Already done (don't redo)

The package lead merged in two steps, because the squash leaves `main` without `d3babf1f`:

- `44ee2a84` merges Mail's head `ad777f5e` (the content that went to `main`). Its conflicts were only the
  Control workflows (main's trigger tidy-up kept: no push trigger on base, a newer PR run cancels the older one,
  boundary still runs on push to `main`; 18d's job changes and path filters kept; `pkg/19-mail` dropped from the PR
  branch filters) and two generated files, regenerated with `control/generate.py`.
- `1ec69134` merges `main` with `ad777f5e` as the merge base; it brings in only `HANDOFF.md`, `README.md` and
  `STATE.md`. `git diff origin/main HEAD --stat` shows only 18d's scope and generated files.

Don't merge anything else, and don't redo or rewrite these merges.

## Read first

`AGENTS.md`; `briefs/18d-base-slim.md`, `briefs/18d-parallel-start.md` and `briefs/18d-review-fixes.md`;
`reviews/18d-base-slim/REPORT.md`; `reviews/19b-owner-state/REPORT.md` (top, "Done", "Re-scope (owner,
2026-11-12)" and "Final fix round"); `docs/design/CONTROL.md` section 7 and `docs/control/PLAN.md` entry
"2026-11-11, 08:10" (the normal-MCP bar). After the merge, the design and plan files on this branch are current.

## What to check, and fix where needed

1. **Nothing 19b added relies on what 18d removed.** 18d removed or relaxed: the exact-equality comparison and its
   `differences` report, `managed_mcp()` / `managed_servers()` and `managed-mcp.json`, the `managed-settings.d` walk
   (`absent_or_empty`), every managed key other than `permissions.ask` and `hooks`, the boundary launcher
   (`control/boundary/launch.py`, `launcher.c`, `env-load.c`), the coding user (`coding-settings.json`,
   `isolation.sh`, the coding part of `isolation.py`) and its workflow step. Search all of 19b's code, tests, CI
   scripts and workflows, including `control/owner_state_oracle/`, `control/ci/` (`base.py`, `test.sh`,
   `setup.sh`, `mail/run.sh`, `mail/tests.py`), `.github/workflows/control-owner-oracle.yml` and the test-selection
   lists, for anything that calls, imports, installs or asserts one of these, or that expects the old managed
   settings. A test that only pinned the old behaviour is updated to the slim behaviour; never weaken an assertion
   that protects an asking tool.
2. **Every send, delete and unsubscribe still asks.** List the asking actions on the combined head (effect `send` or
   `delete`, not owner-only, not trusted) and confirm each has its rule in the generated managed settings and is
   required by the boundary check, including any action 19b added or changed. The generator and
   `test_slim_policy.py` must still fail on a missing or misnamed rule.
3. **19b's engine paths and 18d's checks fit together.** In `Engine.reserve` and `Engine.submit`, 18d's boundary
   check and its trusted-send guard now sit next to 19b's action context and its R2 commits before each mutation.
   Confirm that a refusal by either (missing ask rule, no matching owner-only trusted entry) happens before any
   mutation or far-side effect, and leaves a truthful record (no claimed submission, nothing that a later recovery
   could replay). Add a regression test if one is missing.
4. **The shared instructions keep what 19b's tools need.** 19b changed Mail's paging behaviour and descriptions
   (`page_changed` restarts the first page; stale and invalid cursors). Check that the shared text in
   `COMMON_INSTRUCTIONS` and `MAIL_INSTRUCTIONS` doesn't contradict 19b's results, that rules an action needs at the
   moment of use stay in its description, and that no shared block is repeated in a description.
5. **Regenerate** every generated file (`python3 control/generate.py`, then `--check`). Report the description
   character totals: Mail's 28 exposed descriptions on `main` (`18168c6c`), and on the combined head with its
   instructions sent once; the same for `control` and `testapp`.

If something here needs a design or plan change, or an owner decision, don't build it: record it as a
**PLAN-GAP** or **JUDGMENT-CALL**.

## Tests and runs

- Locally: `python3 control/generate.py --check` and the plain-Python tests that run on macOS. The managed settings
  path check refuses `/etc` on macOS (it is a symlink there), so tests that need the installed settings run in CI.
- On GitHub (Fedora containers, no model, no real account), on the final head: **Control base, Control Mail and
  Control boundary twice each** (the pull-request run, then `gh run rerun <id>` for the second pass; a new push
  cancels the older run, so never push again to get a second pass), and the **optional owner oracle once**
  (`gh workflow run control-owner-oracle.yml --ref pkg/18d-base-slim`), since 18d touches the engine and the storage
  checks it reads.
- Pull-request runs already started on `1ec69134` (the merge alone): use their results as an early signal. Any push to
  the PR starts all three pull-request workflows again and cancels the older runs (their path filters compare the
  whole PR), so commit in small steps locally (this brief's own commit is local too) and push once, when everything
  is done and green locally, including the report section below.
- If a run fails, fix the cause, never the assertion, and say how many executions you used.

## Report

Add a section "Main merge and 19b integration" to `reviews/18d-base-slim/REPORT.md`: what you checked for each item
above and what you found (marked **read** or **run**, with files and lines), what you changed and why, the description
totals, the owner oracle's result, and any **PLAN-GAP** or **JUDGMENT-CALL**. Record the final run IDs and attempts in
the PR #25 description, as before, to avoid a report/head loop.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/18d-base-slim`. The draft PR #25 exists. Never merge anything, never push
  to `main`, never force-push.
- Don't edit the design or plan files (`docs/design/`, `docs/control/PLAN.md`, `docs/control/FEATURES.md`),
  `README.md`, `STATE.md`, `HANDOFF.md`, anything under `os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, or the
  review files the reviewers wrote (`reviews/18d-base-slim/*REVIEW*.md`, `SECURITY.md`).
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a careful cross-check of 19b's new engine, storage and CI code against 18d's removals,
the same kind of work it did well in 18d's build; Astra stays for the security review.
