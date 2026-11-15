# 18c-review-fixes-1: the "don't ask again" case proves each send by itself

**Goal:** close the three findings of `reviews/18c-image-test/REVIEW-B1.md` (package review, `gpt-6.1-sol`, on
`122f5eee`). The security review (`SECURITY-REVIEW-B1.md`) said SAFE with no fix. Nothing else changes.

**Read:** both reviews, `briefs/18c-image-test.md` section B1, and your own `reviews/18c-image-test/REPORT.md`.

## Fixes

1. **Each send of the "don't ask again" (DAA) case is judged by itself** (`control/boundary/interactive_suite.py`,
   both modes). Today the case checks one arrival after sends 1 and 2 together, and only counts the tool results. A
   run where send 1 never arrives and send 2 goes out after "No" would pass. Assert the receiver's arrivals after each
   turn (1, then 0 more, then 0 more), assert that send 1's tool result is the success and that the results of sends
   2 and 3 are the permission refusal, and match them by tool-use id. Give `reviews/18c-image-test/verify-evidence.py`
   the same per-send check.
2. **The suite itself proves that DAA was written and kept.** When Claude Code offers the option and the driver
   picks it, require, before the case's PASS line: the grant for `mcp__testapp__send` is in the settings file the
   option writes (your report names `.claude/settings.local.json` in the work folder), and it is still there after
   the new `claude` process of send 3 has started. If Claude Code doesn't offer the option, the case records that and
   fails as today. Then apply the review's wider point to every case: wherever only `verify-evidence.py` checks
   something a PASS line claims, move that check into the suite, so CI fails without the separate script.
3. **The VSOCK comment says only what the evidence shows** (`control/boundary/hostile.py`, the comment above the
   `connect:vsock` classification). A timeout and a reset are both "no established connection", and the row stays
   unqualified; the receiver has no VSOCK listener, so its arrival count proves nothing about VSOCK. Reword the
   comment accordingly. The classification line itself stays as it is.

## Must not change

Everything `briefs/18c-image-test.md` lists under "Paths the builder must not touch", the pinned `PermissionRequest`
outcomes, the unit and its pin test, the other sixteen cases' expectations, and the workflow's permissions. Nothing
under `os/`. No Part A, B2 or C.

## Acceptance

- A unit test in `control/boundary/test_interactive.py` for fix 1: recorded evidence in which the arrival belongs to
  send 2 and the results are swapped fails the per-send check (the review reproduced exactly this false pass).
- `control-boundary` green twice on the final head, all 17 cases; `control-base` green.
- `REPORT.md` gains a short section "Review fixes 1": what changed, the run ids, and the PASS lines.

## Rules for this run

As in the first run: you are on AresOS itself, user `ares`; no containers, virtual machines or root locally, only
quick unit tests; iterate through the workflow on GitHub's runners; commit in small steps with the trailer
`Codex-Model: gpt-6.1-sol`; push; never merge, never push to `main`, never force-push, never `--no-verify`.

**Model:** `gpt-6.1-sol`, xhigh: small fixes in the harness it wrote in the first run.
