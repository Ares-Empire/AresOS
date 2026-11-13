# 19b re-scope: stage 2 is the end; the strict oracle becomes optional (owner, relayed by the lead, 2026-11-12)

The owner answered the re-scope (it reaches `docs/control/PLAN.md` later through the lead's own PR; don't edit that
file):

- **★1** "Database crash recovery is not needed haha": 19b stops at stage 2; **stage 3 is dropped**. The branch's
  code is already back at the SAFE stage-2 head `7b0e9a05` (commit `dec6903b`); the stage-3 work is kept only as
  patches under `reviews/19b-owner-state/` and `.work/19b-s3-uncommitted.patch`. Don't re-apply any of it.
- **★2** Retire the strict known-gap ledger and the full fault-matrix owner-state oracle from **required** CI, but
  keep the code and the compact ledger in the repo as an **optional, manually started** check ("very cool it exists
  so I wouldn't throw it away"). Normal-use-is-quiet checks and the targeted regression tests stay required.
- **★3** The review bar is a normal MCP tool: the tools' questions stay whole (exact bound content; Claude can't
  answer or replay them), credentials never reach Claude, untrusted content is marked, no double send after a crash.
  A flaw with real harm potential gets fixed, especially system-operator harm (installs, system damage,
  credentials). Low-harm edge cases become documented known limits.

Read `AGENTS.md`, `briefs/19b-owner-state.md`, `briefs/19b-on-mail.md` and this file. This run does ★2 only.

## What to build

1. **An optional workflow** (for example `.github/workflows/control-owner-oracle.yml`) with **only** a
   `workflow_dispatch` trigger. It runs what is retired from required CI: the strict owner-state sweep
   (`test_owner_state_sweep` in every mode, with the compact ledger), the alteration test (`test_owner_state_perturb`
   and its planted controls) and any test that exists only as a pinned expected failure in the ledger (for example
   the `G22-*` cases). Keep its sharding so a manual run fits GitHub's job limits. Keep the code, the compact ledger
   and `KNOWN-GAPS.md` in the repo; say at the top of `KNOWN-GAPS.md` that the ledger is an optional check now.
2. **Required CI** (`control-base.yml`, `control-mail.yml`, `control-boundary.yml` on pull requests) keeps:
   Mail's and the base's own suites as before 19b, Mail's inherited storage-fault sweep (`test_review23_sweep`,
   `test_review24_io`), the normal-use-is-quiet checks (the fault-free point-0 case of every flow and the quiet
   contracts), the targeted regression tests (reviews 20–22 named regressions that pass, `test_action_context`,
   the stage-2 fix regressions, the oracle self-tests that run in seconds) and the import-independence test. Remove
   the strict-ledger owner sweep and the alteration jobs from the required workflows, and simplify the Mail job
   layout accordingly (fewer jobs, each under about 35 minutes). The `pkg/19-mail` pull-request trigger stays.
3. **Tests that are now orphaned:** a required test must pass on its own; no required test may depend on the
   ledger. If a required test only passed because the ledger pinned its failure, move it to the optional job and
   list it in the report as a known limit.
4. **Report:** add a "Re-scope (owner, 2026-11-12)" section to `reviews/19b-owner-state/REPORT.md`:
   - what moved from required to optional, and why (★2);
   - what stays required, by test module;
   - the **known limits** under ★3: every behaviour the dropped stage 3 would have closed (for example the SQLite-read
     fallback, the durable owner-state projection, restore re-deriving free-change warnings, so round 29's restore
     sentence stays true; the review-22 cases `G22-rename`, `G22-evidence`, `G22-latch`; the first-write full-disk
     background warning), each with one line on its effect for the owner, so the security review can judge whether
     any has real harm potential;
   - a note that the owner's storage decision of 2026-11-11 (board #176) applied to the dropped stage-3 candidate
     and is moot now; stage 2 adds no permanent journal bytes;
   - the run count, and every change to `warnings.py` and `paging.py` since `d3babf1f` (expected: none in production;
     confirm).
5. **Verify:** one manual dispatch of the optional workflow on the finished head, to show it runs and the strict
   ledger still matches (report its result; it isn't part of required CI). Required CI (Control base, Control Mail,
   Control boundary) passes **twice** on the finished head. Wait on CI with one blocking shell call per run
   (`gh run watch <id> --exit-status --interval 60`, or one loop over the named runs); never poll run status one turn
   at a time.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/19b-owner-state`. Commit in small steps and push; draft PR #26 targets
  `pkg/19-mail`. Never merge, never push to `main` or `pkg/19-mail`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- No production code change, and no change to what any tool asks or does. Only workflows, CI selection
  (`control/ci/`), test organisation and documents change. Never weaken or delete a test to get green; moving it to
  the optional job is allowed only as item 3 says.
- No real accounts, addresses, personal names or mail-provider names.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.
- Don't run your own review; the package lead runs the package and security reviews. Stop when this is done.
