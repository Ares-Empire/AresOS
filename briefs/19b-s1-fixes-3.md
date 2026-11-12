# 19b stage 1, fixes round 3 (the last for stage 1)

**Against:** the sol high fix check [`reviews/19b-owner-state/REVIEW-S1-3.md`](../reviews/19b-owner-state/REVIEW-S1-3.md)
(reviewed `d1290e13..627fba12`, CHANGES-NEEDED). Read `briefs/19b-owner-state.md`, `briefs/19b-on-mail.md` (the note
wins), `briefs/19b-s1-fixes.md` and `-2.md` (D1–D3, L1 and the field-audit rule still hold), and all three stage-1
reviews first. Stage 1 only (oracle, comparison, ledger). No production change. Do not start stage 2.

## Why this round is different

Three reviews in a row found the same class in new places: a value production wrote into the committed record
(a payload, a state transition, a restore marker, a missing row, a hash) used to drop, narrow or choose an
expectation. Patching each case is not converging. This round changes the structure so the class is closed by
construction and tested systematically, then fixes the five cases as instances of it.

## S. Structure: monotonic obligations and an allowlisted resolution table

1. **Obligations come from independent inputs only.** Every owner-visible obligation (warning, occurrence, expiry or
   cancellation notice, recovery notice, unchecked check, hold, qualification caveat, incomplete account, pending
   approved work) is derived from the script (calls, approvals, arguments, clock), the server logs and the fault
   trace. The required effects of an approved action (every target, recipient, flag, destination) come from the
   scripted approval, not from a committed payload.
2. **The committed record may end an obligation only through an explicit allowlist.** Write one table in code and in
   `FORMAT.md`: resolution kind (acknowledgement, completion, clean check result, cancellation, expiry, settlement,
   restore, archive, onboarding completion, ...) → the independent corroboration it requires (the scripted call, the
   server-log evidence, the fault trace, the decoded commit order). A resolution not in the table, or without its
   corroboration, leaves the obligation in place and reports a lifecycle difference.
3. **Everything else the record says is compared, never trusted.** Committed values are checked against the
   independent derivation (payload against approval, hashes against logged message bytes, transitions against the
   allowed state machine plus corroboration). A restore explains only the sequences it is shown to roll back; any
   other missing committed sequence is a difference.
4. **Systematic perturbation self-test.** Add a test that takes recorded scenarios (the focused contracts and named
   regressions at least, plus a sample of sweep cases in every mode) and perturbs the decoded committed record one
   change at a time: flip each boolean flag, change each state to every other state, remove each row, drop each
   committed sequence, change each target/recipient/flag/hash/destination, add a restore marker before each
   sequence. For every perturbation, the oracle must either report a difference or keep exactly the same expected
   owner-visible set. A perturbation that makes the expected set smaller (or changes it) with no difference
   reported fails the test, naming the field and scenario. Report how many perturbations ran and that none slipped.
   This test, not a hand-picked list, is how the next review checks the class.

## Review findings to fix (numbers from REVIEW-S1-3.md), as instances of S

1. **Blocking: completion trusts the initial payload** (`model.py:420`, `:877`). Required effects come from the
   approval; a committed payload with one of two approved targets and one EXPUNGE must fail.
2. **Blocking: unsupported transitions erase obligations** (`model.py:454`). `reserved → refused` with no fault,
   cancellation or acknowledgement, plus `notice=False`, and `unknown → reserved`, must each keep the obligation and
   report a difference.
3. **Blocking: any restore disables missing-history validation** (`records.py:111`). A restore at sequence 1 cannot
   explain a missing sequence 2 that followed it; that must fail.
4. **Blocking: incomplete-account recovery disappears through restore** (`model.py:504`). Retain the incomplete-account
   obligation until corroborated onboarding completion; test rollback and explicit row deletion.
5. **Should-fix: filing hashes justify themselves** (`model.py:797`). Bind each source/hash to independently logged
   pre-command message bytes; a coherent false hash with a matching false disclosure must fail.

New production gaps these expose go into the compact ledger as exact entries naming row and closing stage.

## Verification and report

- Local first (oracle self-tests including the perturbation test, focused contracts and regressions,
  `python3 control/generate.py --check`, `git diff --check`), then the Linux capture, then the strict runs.
- At the finished head: Control base, Control Mail (every job within 45 minutes; watch shard 0, which reached 36
  minutes last round) and Control boundary each pass twice. Record run IDs, attempts and log lines.
- Do not run your own stage review; the package lead runs the fresh fix check.
- Add a "Stage 1, fixes round 3" section to `REPORT.md`: the obligation derivation, the resolution table, the
  perturbation test (scenarios, perturbation kinds, count, result), per finding the change and its test, the updated
  field-audit table, the new ledger counts and size, the run count. Mark claims run, read or assumed.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/19b-owner-state`. Commit in small steps and push this branch; draft PR
  #26 targets `pkg/19-mail`. Never merge, never push to `main` or `pkg/19-mail`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- No real accounts, addresses, personal names or mail-provider names; tests use synthetic accounts only.
- Never commit the full gap list; the committed ledger stays compact (format 3, under about 1 MB).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.
- Stop after this round. Do not start stage 2.
