# 18d review fixes (round 1)

**Goal:** fix the two findings of the package review (`reviews/18d-base-slim/PACKAGE-REVIEW.md`, `gpt-6.1-sol` high,
CHANGES-NEEDED, on `f3d2f895`) and one gap the package lead found checking the result. Nothing else changes. The
brief `briefs/18d-base-slim.md` and the note `briefs/18d-parallel-start.md` still apply; design and plan are read on
`origin/main` as before (`git show origin/main:docs/design/CONTROL.md`, section 7).

## What to fix

1. **Push triggers (review finding 1).** The brief asks that `control-base.yml` and `control-boundary.yml` run "on
   pushes to this branch (path filter) and on its pull request". While PR #25 conflicts with `main`, its
   pull-request checks don't start, so a push to this branch gets no automatic run. Add a path-filtered `push`
   trigger for `pkg/18d-base-slim` to both workflows, beside `pull_request` and `workflow_dispatch`, with the same
   paths as the pull-request filter. Also restore the boundary workflow's `push` trigger for `main` (main's own
   version keeps it: "Main keeps its check after each merge"; this branch dropped it), and keep a concurrency group
   that never cancels a run on `main`, as main's version does. Say in the report that, once `main` is merged in and
   the PR runs again, the `pkg/18d-base-slim` push trigger doubles runs and can be dropped at that merge.

2. **Boundary path filter (review finding 2).** The native check now imports the definitions and checks that the
   generated server instructions, descriptions and schemas reach the model's request, but the boundary workflow
   doesn't run when `control/aresos_control/**` or `control/generated/**` change. Add both to every boundary filter
   (push and pull request), or use `control/**`.

3. **The test app's ask rules (package lead's check).** The shipped service still serves `testapp`
   (`Engine.adapters` always holds it, `Proxy` accepts any app in `APPS`, and the shipped `service.json` has no switch
   to turn it off), but the shipped managed settings no longer carry `mcp__testapp__send` and `mcp__testapp__delete`,
   and `Boundary.require()` no longer requires them (`asking_rules()` defaults to `APPS - {'testapp'}`). So once
   anyone installs the test app's proxy at user scope, its send and delete run without asking. Before this package
   both rules were shipped and required. Fix it so every asking action of every app the service serves has its rule
   in the generated managed settings and is required by the boundary check:
   - `asking_rules()` and `managed_settings()` by default cover every app the service serves (all of `APPS`, the
     same definitions the engine's adapters serve), so the shipped settings again hold the test app's two rules;
     `user-mcp.json` still installs only `control` and `mail`.
   - The generator check and `test_slim_policy.py` still fail on a misnamed rule: every rule must name an exposed
     tool of a served app, under the server name `user-mcp.json` installs it with; the test app, which only the
     harness installs (with the same server name `testapp`), is the one named exception, and any other app missing
     from `user-mcp.json` fails.
   - Add a test that the service refuses `testapp_send` with `boundary_not_installed` when the installed managed
     settings lack `mcp__testapp__send` but hold every Mail rule (and the same for `testapp_delete`), and a test that
     every app in the engine's adapters is covered by `asking_rules()`.
   - Regenerate every generated file (`ask-rules.json`, `managed-settings.draft.json`, `managed-settings.draft.comments.md`,
     `docs/control/TOOLS.md` if it shows rules) and update `REPORT.md` (the slim settings as generated, the test app's
     place, and what Chrome must do).
   If you find the shipped service does not in fact serve the test app (a switch this check missed), don't change
   anything for item 3; quote the line in the report instead.

## Tests and runs

- Base suite, boundary workflow and Mail suite pass on the final head: base and boundary twice (the push-triggered
  run plus `gh run rerun <id>`), Mail once (`gh workflow run control-mail.yml --ref pkg/18d-base-slim`).
- **Budget: five workflow executions in all for this round.** Commit in small steps locally, then push once, when
  everything is done and green locally, so each workflow starts once. Don't dispatch base or boundary by hand when the
  push already started them. If a run fails, fix the cause (never the assertion) and push again; say in the report
  how many executions the round used.
- Record the round's run IDs and attempts in the PR description, as for the first round, and add a short
  "Review fixes, round 1" section to `REPORT.md` naming each finding and its fix.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/18d-base-slim`. Commit in small steps and push this branch; the draft PR
  #25 already exists. Never merge, never merge `main` or another branch in, never push to `main`, never force-push.
- Don't edit `reviews/18d-base-slim/PACKAGE-REVIEW.md` or any design, plan, `os/`, `mod/`, install, state or handoff
  file.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.
