# 19b stage 2: what comes first (lead decision, 2026-11-10 03:10)

Read with `briefs/19b-owner-state.md`, `briefs/19b-on-mail.md` (the note wins) and the stage-1 fix briefs
`19b-s1-fixes.md`, `-2.md`, `-3.md` (their decisions D1–D3, L1, the field-audit rule and structure S hold). Stage 1
closed with three findings still open in [`reviews/19b-owner-state/REVIEW-S1-4.md`](../reviews/19b-owner-state/REVIEW-S1-4.md).
The lead chose to fold them into the start of stage 2 instead of a fourth stage-1 round.

## Part A, committed on its own before any stage-2 production change

The review must be able to see this part alone, so commit and push it (local checks green) before the first commit
that touches production code. It changes test code, the ledger and the report only.

1. **Pre-command evidence closes a filing check** (`model.py:529`, `:798`). A filing check may close only on a
   successful, delivered result correlated with this check and ordered after its mutation. A pre-MOVE LIST, a MOVE
   without COPYUID, no post-MOVE LIST and a committed `done/check_open=False` must keep recovery and report a
   difference.
2. **Another operation's POST justifies completion** (`model.py:1334`, `:869`). Completion of an unsubscribe needs
   this operation's exact approved request, its correlated call, a successful response and the commit order. An
   earlier unsubscribe's HTTP 200 followed by this one's HTTP 500 committed as `done` must fail.
3. **The alteration test misses list entries and fields** (`perturb.py:40`, `:52`). Make it field-level and complete:
   - mutate every scalar element of every list independently (each recipient, each flag, each target, each
     location), not only by dropping the last one; cover every flag representation, including `append_flags`;
   - derive the set of fields to perturb from the decoded records themselves, and fail when a field present in a
     recorded scenario is neither perturbed nor on an explicit, justified exclusion list;
   - a perturbation counts as caught only when its difference reaches the comparison (the checker that the sweep
     uses), not merely when a helper reports an error;
   - **planted-fault self-test:** for each field kind (flag, state, removed row, dropped sequence, target, recipient,
     flag list entry, `append_flags`, hash, destination, restore marker, account, role), plant one known-bad
     production change in a recorded scenario and show the oracle reports it through the comparison. Also plant a
     deliberately broken oracle (one that ignores that field) and show the alteration test fails on it, so the test
     is proved to have teeth.
4. Update the compact ledger, the field-audit table and a "Stage 2, part A" section of `REPORT.md`.

## Part B: stage 2 as briefed

Then build stage 2 of `briefs/19b-owner-state.md` (action context, R2) with its tests, removing stage-2 ledger
entries as their assertions pass.

## Mail CI runtime

The Mail `containers` job reached 43m34s against its 45-minute cap at `e8d269ad`. Bring every Mail job back with a
clear margin (aim under about 35 minutes in both passes) by sharding or speed. Do not drop or skip cases, and do not
raise the cap. Changing the job layout of `control-mail.yml` for this (for example a matrix for the suite job, with
its artifacts still uploaded) is allowed; no other workflow change.

## Runs and reviews

- Local checks first; push for CI only at part A's head if it needs Linux evidence, and at stage 2's finished head
  (then the second pass). Report the run count.
- Do not run your own stage review. The package lead runs three reviewers in parallel on the stage head: the stage
  review, a storage-fault/owner-state review, and an oracle-independence review.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/19b-owner-state`. Commit in small steps and push this branch; draft PR
  #26 targets `pkg/19-mail`. Never merge, never push to `main` or `pkg/19-mail`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- No real accounts, addresses, personal names or mail-provider names; tests use synthetic accounts only.
- Never commit the full gap list; the committed ledger stays compact (format 3, under about 1 MB).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.
- Stop after stage 2. Do not start stage 3.
