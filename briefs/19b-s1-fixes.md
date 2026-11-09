# 19b stage 1, fixes round 1

**Against:** the fresh sol high stage-1 review [`reviews/19b-owner-state/REVIEW-S1.md`](../reviews/19b-owner-state/REVIEW-S1.md)
(reviewed head `f26322fd`, CHANGES-NEEDED), plus the lead's decisions below. Read `briefs/19b-owner-state.md`,
`briefs/19b-on-mail.md` (the note wins where they differ), `reviews/19b-owner-state/COVERAGE.md`, `REPORT.md` and
`KNOWN-GAPS.md` first. Everything in the brief and the note still stands. This round fixes **stage 1 only**: the
oracle, the comparison and the known-gap ledger. Do not start stage 2. No production change except where a finding
says so (none does).

## Lead decisions, 2026-11-09 (lead `mac-aresos-control`)

- **D1, workflow runs.** The ~25-run target is relaxed (public repo, CI is free), but run every local check first and
  push for CI only at this round's finished head, then rerun for the second pass. Report the total run count.
- **D2, the ledger** (L1 below): compact and equally strict, before any other commit of this run touches it.
- **D3, for stage 3 (record only; don't build it now).** Review 22 case 2 (`G22-evidence`, this run's REPORT
  PLAN-GAP): reserve the space for an open check's evidence record through `space.py`'s reservations **before** the
  remote evidence is read, so the write that matters can't be refused for lack of space. If the write still fails
  (a failing disk, not a full one), the check stays open (round 27's rule) and carries a durable generic warning,
  already committed or computed from the open check, such as "evidence was seen but couldn't be recorded; check
  Trash". A less specific warning is acceptable; a lost one is not. Stage 3 builds this; the oracle's `G22-evidence`
  expectation should accept exactly that (the specific occurrence, or the committed generic warning while the check
  is open), and nothing weaker.

## L1. A compact, equally strict known-gap ledger (D2)

`reviews/19b-owner-state/KNOWN-GAPS.json` is 52 MB. Every committed version stays in history (no force-push), one
growth step would hit GitHub's 100 MB push limit, and no reviewer can read it. Replace it first, and never commit
the full list again.

- **Committed form**, under about 1 MB (for example `KNOWN-GAPS.json` in a new format 3). Per group:
  - a group id, and the matrix row or named case (`G22-*`, `review20-*`, ...) it belongs to;
  - the stage that closes it;
  - the count of exact assertion keys;
  - the sha256 of the sorted, normalised list of those exact assertion keys **each together with its pinned row,
    stage and exact delta** (calls, missing and extra facts, page numbers), so a changed delta still fails exactly
    as today;
  - a few sample keys for humans.
- **Same strictness.** The checker computes the same digests from the actual failures and fails on any difference:
  an unexpected pass, an unlisted failure, a changed delta, a key moved between groups, a missing or extra group, an
  owned group not executed. Name the group in every failure, and keep "unexpected pass", "known gap changed" and
  "unlisted gap" distinguishable where the scheme allows (for example by also comparing counts and sample keys).
- **Sharding.** Each CI worker sees only the keys it owns. Choose groups so that each is verified wholly by one worker
  (or identically by every worker, as the clean point-0 cases are today), for example by grouping on a fixed
  ownership bucket of `flow/point` that the shard/worker split then assigns. Test that the union of all
  shards × workers verifies every group exactly once (shared clean groups by all), for the CI split in use.
- **The full list** is generated on demand by one documented command writing under `.work/`, and in CI each worker
  writes its actual full list (gzip is fine) under `.work/mail-ci/` (and `.work/control-ci/` if the base suite checks
  ledger entries). Adding those paths to the **existing** `upload-artifact` steps of `control-mail.yml` /
  `control-base.yml` is allowed; no other workflow change. The full list is never committed.
- **Conversion proof.** Convert the current format-2 ledger with a script and show in the report that digests
  computed from the old full list equal the committed ones, with the per-stage counts, before the oracle fixes below
  change any expectation.
- **Self-tests:** a flipped delta, a removed key, an added key, an unexpected pass and a key moved to another group
  each fail; the unchanged list passes; the expectation-import AST test still covers `gaps.py`.

## Review findings to fix (numbers from REVIEW-S1.md)

All nine. The common rule: the oracle's expectations come from the script, the server logs and the independently
decoded committed record, and are **validated** against them; a production flag, row, reply or refusal is never
accepted as its own justification.

1. **Blocking: production flags erase lifecycle expectations** (`model.py:97`). Replay lifecycle transitions
   (acknowledgement, check close, archive/expiry removal) against scripted actions and evidence. An `ack=True` with
   no scripted acknowledgement of that occurrence, a check closed by an acknowledgement, or an unresolved reservation
   deleted by archive must each show as a difference, not an empty expectation. Add a breaking-mutation self-test
   for each of the three.
2. **Blocking: matching context can authorise the wrong command** (`context.py:124`). Compare the script/approval,
   the committed context and the actual command independently: exact targets, UIDs, recipients, flags, folders and
   repair stage. Self-test: script UID 1, context and command UID 2 must fail.
3. **Blocking: production refusals shape their own expectations** (`model.py:204`, `compare.py:78`). Derive which
   refusals are permitted from the injected faults and the transaction/capacity evidence, never from the returned
   error. Compare success/error status on every read, even when the expected catalogue is empty. Self-test: a healthy
   empty notice catalogue returning `storage_limit` must fail.
4. **Blocking: required background warnings pinned as unexpected extras** (`model.py:131`, `compare.py:23`). Derive
   the background-storage warning and its first cause from the fault/script history, and expect its survival through
   failed writes and restart. Correct the affected ledger entries (for example
   `expiry/persistent/1/0/exhausted/control_pending.notice-head`). Self-tests: the warning lost, and the warning
   present, must each be judged correctly.
5. **Should-fix: most response envelopes not compared** (`driver.py:298`). Check each response's own passive
   envelope, including the original action's reply, error replies and every continuation page, before later reads
   can recreate evidence. Self-test: a live warning removed from one envelope must fail.
6. **Should-fix: completed qualification caveats unmodelled** (`model.py:149`, `owner_state_cases.py:205`). Model and
   compare readiness, Sent caveats and negative qualification reasons of an onboarded account after faults, reads and
   restarts.
7. **Should-fix: recovery notice identities can change undetected** (`compare.py:13`, `:25`). Compare the expected
   public handle on every page, read and restart, including acknowledgement behaviour.
8. **Should-fix: audit equality too narrow** (`compare.py:255`). Compare the documented public audit projection:
   operation identity, explanation and relevant structured evidence, with untrusted marking preserved.
9. **Should-fix: unbound occurrences become unrepairable** (`model.py:66`). Keep an independent semantic occurrence
   identity whose unknown durable/public handle can bind later. Test failed write, then successful persistence, then
   acknowledgement.

New gaps these fixes expose in production go into the ledger as exact entries naming their matrix row and closing
stage (2 or 3), as today. A fix must never make the oracle accept less.

## Verification and report

- Local first: the oracle self-tests, the focused contracts and regressions, `python3 control/generate.py --check`,
  `git diff --check`. Then the Linux capture for the new ledger, then the strict runs.
- At the finished head: Control base, Control Mail (every job within 45 minutes) and Control boundary each pass
  twice. Record run IDs, attempts and log lines.
- Do **not** run your own stage review; the lead's package lead runs the fresh review of this round.
- Add a "Stage 1, fixes round 1" section to `reviews/19b-owner-state/REPORT.md`: per finding what changed and its
  self-test; the ledger format, its size, the conversion proof and the regenerate/diff command; the new per-stage
  counts and why they changed; the run count. Update `COVERAGE.md` and `KNOWN-GAPS.md` where they change. Mark each
  claim run, read or assumed.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/19b-owner-state`. Commit in small steps and push this branch; draft PR
  #26 targets `pkg/19-mail`. Never merge, never push to `main` or `pkg/19-mail`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- No real accounts, addresses, personal names or mail-provider names; tests use synthetic accounts only.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.
- Stop after this round. Do not start stage 2.
