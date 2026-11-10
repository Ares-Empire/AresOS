# 19b stage 2, fixes round 2: oracle independence re-check

**Angle:** only N1, S-N2 and S-N3 of [`REVIEW-S2-ORACLE-2.md`](REVIEW-S2-ORACLE-2.md), checked against
`git diff 3486bec8..e43ea57c` (brief [`19b-s2-fixes-2.md`](../../briefs/19b-s2-fixes-2.md) section 1), whether those
fixes broke the code they touch, and whether any fault-free flow's point-0 group in `KNOWN-GAPS.json` still carries an
oracle-side difference. No fresh hunt. **Reviewed head:** `e43ea57c` on `pkg/19b-owner-state`. Read-only: this file is
the only repository file written. Probes ran in memory from
`/private/tmp/claude-501/-Users-pab/5d5bbd0b-a538-400c-b84f-360fe127662f/scratchpad/oracle-review-3/probes/` (round-2
probes copied and adapted, plus the new ones named below), with the worktree venv and the same in-memory managed-policy
patch. Old-head runs used `git archive` copies of `3486bec8` and `ce718024` in that scratch folder.

## Findings

| # | Finding | Status | Evidence (rerun at `e43ea57c`) |
| --- | --- | --- | --- |
| N1 | Oracle refused correct completions in fault-free `testapp_send`, `repair`, `settlement`, `status` | **Fixed** | `baseline_any.py`: `testapp_send` 35 → **0** views, `repair` 41 → **0**, `status` 2 → **0**, all with no semantic facts; `settlement` 41 → **1** view, no semantic facts (see below). `local_stage.py`: `completion_errors → []`. KNOWN-GAPS point-0 shared groups changed exactly as REPORT.md's table says (`repair` M06 11→0, M14 30→0; `settlement` M06 11→0, M14 30→1; `status` M14 2→0; `testapp_send` M06 9→0, M14 26→0); no other fault-free group count changed. The four flows are in the quiet contracts (`owner_state_cases.py:27-28`) with a direct "no differing views" assertion (`:72-73`), and no `contract/quiet-*` key is pinned, so strict mode also fails on any new difference there. `test_owner_state_contracts` OK. |
| N1 narrowness | Stage/flags in the multiplicity signature; seed DATA join | **Narrow enough** | `dup_narrow.py` (one recorded effect duplicated in the server log): identical LOCAL_STAGE `sent_copy` twice, `answered_flag` twice, Sent APPEND twice, DATA twice → each still `duplicate-effect call:/intent:` + `unsupported-resolution completion`. A second Sent APPEND with **different** flags is not a multiplicity duplicate any more, but is caught by `R2.APPEND ["script.command.append-flags"]` (flags are script-authorised, so only an identical, already-rejected repeat could carry authorised flags). `seed_narrow.py` on `repair`/`settlement`/`status`: a runtime re-send DATA bound to the operation → `R2.DATA` + `false-completion "Accepted SMTP recipients differ…"` (status: `R2.DATA`); the seed DATA moved past the seed boundary → `R2.DATA` (status also `No matching accepted SMTP DATA`); the seed DATA moved into the runtime call → `R2.DATA` + `duplicate-effect call:DATA`. The repo's `test_fixture_delivery_requires_matching_script_and_message_identity` covers wrong call, wrong Message-ID, post-seed and runtime-call. The new `fixture` skip on the sent-copy close (`model.py:1080`) applies only to seed history and scripted `fixture_input` commits (`model.py:830-831`). |
| S-N2 | Single-validator controls could not fail; alteration slips without `stage_claims`/`filing_claims` | **Fixed, except one undocumented slip (S1)** | `test_owner_state_plants` now reruns baseline **and** plant through unmodified `Driver.compare` with one validator disabled. My run prints the table in REPORT.md/FORMAT.md exactly: `transition` 34/0 and `local.errors` 18/0 (comparison-level controls; `assertFalse(remaining)` can fail); `script_differences` 41/40, `stage_claims` 40/40, `completion_errors` 40/1, `payload_claims` 41/41, `filing_claims` 11/10, each stated plainly as "redundant with …" in REPORT.md and FORMAT.md, which also explain that an ignored field cannot be seen by the alteration test. The two slips are reported as caught only by the named validator, with a real control (`test_terminal_and_filing_result_removal_are_caught_only_by_the_named_validator` runs `perturb.check` intact, then requires `Silent owner-state perturbation` with the validator removed): passes for `send`/`stage_claims` and `filing_move`/`filing_copy`/`filing_rename`/`filing_claims`. `teeth3.py` (`teeth2.py` adapted to collect **every** slip, not just the first; 19 fault-free recordings, 256,393 alterations per run): with `stage_claims` removed, **13 slips in 11/19 recordings, every one a coherent whole-row removal of an `op:` row** (send, repair ×2, delete_trash, delete_permanent, unsubscribe_https/mailto, folder_delete, testapp_send, testapp_delete, send_duplicate, settlement ×2), so the documented statement is complete. With `filing_claims` removed, **6 slips in 3/19**: the documented whole-row removal of the filing/rename result row (×3) **and** an undocumented coherent change of that row's `state` (×3), see S1. |
| S-N3 | Plant assertions not relative to the plant-free run | **Fixed** | `test_owner_state_plants.py:33-45`: each plant's flow is recorded once without the plant; the plant must add both new/changed `Driver.compare` views (`new_views`, value comparison per key, so a changed delta on an already-failing view counts) and new non-structural facts. `noise.py`: two independent plant-free recordings of every plant flow (`delete_permanent`, `draft_append`, `filing_rename` (10 baseline entries), `local_flag`, `repair`, `send`, `testapp_send`) give **0** new views and **0** new semantic facts, so run-to-run noise cannot satisfy the relative assertions. All 21 plants pass. Nit below. |
| Point-0 groups | No fault-free point-0 group carries an oracle-side difference | **Not confirmed** | Three fault-free point-0 groups still carry oracle-side differences: `onboarding` (44 keys), `folder_review` (20) and `testapp_delete` (1 key, one of its two facts). See B1. `settlement`'s remaining key is production-side (see below). |

`settlement`'s one remaining point-0 key (`settlement/single/0/0/live-restored/operation-stages`, M14) compares
production's public stages with production's own committed stages: `missing ["op:#4","stages","","committed"]`,
`extra ["op:#4","stages.mismatch","","[\"/sent_copy_warning\"]"]`. It has no oracle proof fact. That is a production
public/committed disagreement (stage-3 durable disclosure), as REPORT.md says.

## Blocking

### B1. Three fault-free flows still pin oracle-side differences as stage-3 production gaps (same class as N1)

This is not a regression: the same facts are present at `3486bec8` and at `ce718024` (`onboarding` 42 there, 44 since
round 1). N1 named four flows, and this round fixed exactly those. But the rule behind N1 ("nothing extra in normal
use"; the ledger lists production gaps that stage 3 closes) also fails here, and these flows are not in the quiet
contracts, so nothing stops it.

- **`onboarding`, 44 keys** (M06 11, M10/M11 1, M12/C05 2, M12/C05/M14 1, M14 29; samples
  `onboarding/single/0/0/live-restored/{aresos log.notice-head, recovery-holds, qualification.mail_account_add, completion}`).
  `onboarding.py` probe, fault-free run:

  ```text
  completion     op:…:990b… false-completion  Approved repair stage lacks delivered effect or read-only settlement evidence  [completion_errors]
  lifecycle-proof op:…:2577… unjustified-stage rcpt:owner@mail.invalid       [stage_claims]
  lifecycle-proof op:…:2577… unjustified-stage recipient:owner@mail.invalid  [stage_claims]
  lifecycle-proof op:…:2577… unjustified-check-close 40 / unsupported-resolution check_result
  lifecycle-proof op:…:990b… unjustified-resolution / unsupported-resolution completion  [transition]
  clean-result-proof op:…:2577… unverified-clean sent_copies
  ```

  The server log shows the self-probe send is complete and correct: `RCPT owner@mail.invalid` accepted, `DATA` accepted
  with the operation's Message-ID, the internal repair's Sent `APPEND` with that Message-ID, and a SENT check confirming
  it. `onb_bind.py`: production committed context for both mutations (DATA binds to `op:…2577…`, the Sent APPEND to the
  repair `op:…990b…`; no R2 fact). The oracle refuses because the only scripted call is `mail_account_add`:
  `operation_events` (`model.py:96-122`) joins seed DATA only for a scripted `mail_send`/`mail_unsubscribe` call and
  repair effects only for a scripted `mail_operation_repair` call (`model.py:118-120`), and RCPT is not a mutation, so it
  is never bound (`stage_claims`, `model.py:1200-1201, 1211-1214`). The oracle therefore expects recovery notices, holds,
  a qualification difference and an incomplete send after a clean account add.
- **`folder_review`, 20 keys** (M06 10, M14 10; samples `folder_review/single/0/0/live-restored/{aresos log.notice-head,
  control_pending.notice-count, …}`): fact `intent:… unjustified-removal`. The scenario's setup review call
  (`test_owner_state_sweep.py:175-177`) runs before observation; its intent is written at seq 4 and removed at seq 5,
  both inside the seed history (`seed_sequence` 5). `intent_result_proof` (`model.py:1249-1253`) checks
  `scripted_transition` first, which fails for the untimed setup call, so the seed shortcut on the next line is never
  reached; the removal is called unjustified and recovery notices are expected. `cause.py`: accepting seed-history
  intent removals in memory takes the flow from 20 differing views to **0**.
- **`testapp_delete`, 1 key** (`testapp_delete/single/0/0/live-restored/lifecycle-proof`, M14): delta
  `changed-fenced-operation 6` and `unapproved-payload account`. The approval names `account: fixture`; production's
  payload has only `items`, whose references carry `scope: testapp/fixture/items` and no `account`, and
  `payload_claims` (`model.py:167-171`) derives the account only from `account`/`reference.account`/`items[].reference.account`.
  `cause.py`: deriving it from the testapp scope removes `unapproved-payload` (facts become
  `[('changed-fenced-operation', '6')]`). I did not classify the structural fence fact.
- **Why it matters:** the same as N1. The pin records oracle defects as stage-3 production gaps; stage 3 cannot close
  them by changing production (only by showing false notices), and until then these flows compare production against
  a wrong expectation. `onboarding` is the account-setup path, so its 44 keys are the largest remaining set.
- **Fix:** join the onboarding self-probe operation's effects through its scripted `mail_account_add` call (the
  operation row committed inside that call's window, matching Message-ID for DATA/APPEND, RCPT of the same SMTP
  transaction) and its internal repair the same way; treat seed-history intent removals as input in
  `intent_result_proof` before the scripted-transition check (as `resolution_proof`, `model.py:1157`, already does);
  derive the testapp payload account from the reference scope, or record why a missing payload account is a production
  gap. Add fault-free `onboarding`, `folder_review` and `testapp_delete` to the quiet contracts with the same "no
  differing views" assertion (or name in REPORT.md exactly which pinned key is production-side, as for `settlement`),
  then re-pin and list the group changes.

## Should-fix

### S1. A coherent `state` lie on a filing/rename result row is also caught only by `filing_claims`, and REPORT.md/FORMAT.md don't say so

- **Where:** `control/owner_state_oracle/FORMAT.md` ("coherent removal of a move/copy/rename result row is caught only
  by filing_claims on this corpus"), REPORT.md "Stage 2, fixes round 2" (same sentence), and the dedicated control
  `test_terminal_and_filing_result_removal_are_caught_only_by_the_named_validator` (`test_owner_state_plants.py:85-98`),
  which tests whole-row removal only.
- **Reproduction (`teeth3.py filing_claims`, `state_slip.py`):** with only `filing_claims` removed, `filing_move`
  slips at `coherent/8/mail:filing:…/state`, `filing_copy` at `coherent/8/mail:filing:…/state`, and `filing_rename` at
  `coherent/6/mail:rename:…/state`, besides the documented whole-row removals. For the rename, the coherent lie
  `state 'partial' → 'started'` is caught intact by `uncommitted-check-result 6` (filing_claims); with it removed, the
  oracle's expected set gains `recovery`, `recovery-context` and `recovery-handle` for the rename, and no difference is
  reported.
- **Why it matters:** the brief asked that each slip be caught by another validator or reported as caught only by the
  one named. Round 2 measured only the first slip per recording, so this second slip was hidden behind the row removal.
  The documentation and the control now state the limitation as smaller than it is.
- **Fix:** add the result-row `state` change to the sentence in FORMAT.md and REPORT.md and to the dedicated control
  (require `Silent owner-state perturbation` with `filing_claims` removed for it too), or let another validator catch a
  coherent filing-result state that disagrees with the server evidence.

**Nit (not blocking):** `test_baseline_alone_cannot_satisfy_a_plant_assertion` (`test_owner_state_plants.py:79-83`)
compares one recording with itself (`new_views(deltas, deltas)`, `semantic(o, d) - semantic(o, d)`), which is empty by
construction and cannot fail. Recording the flow twice, as `noise.py` does, would make it a real control. The property
it means to show does hold (0/0 on all seven plant flows above).

## What I ran

- `baseline_any.py` on all 34 fault-free flows at `e43ea57c`, and on the remaining flows at `3486bec8` and
  `ce718024` (per-flow view counts equal the KNOWN-GAPS point-0 shared-group sums at each head).
- KNOWN-GAPS point-0 group comparison `3486bec8` vs `e43ea57c` (all shared groups, every flow).
- `local_stage.py`, `entries.py settlement`, `onboarding.py`, `onb_bind.py`, `cause.py`, `td.py`, `dup_narrow.py`,
  `seed_narrow.py`, `noise.py`, `state_slip.py`, `teeth3.py stage_claims|filing_claims` (19 flows each; outputs
  `teeth3-stage_claims.txt`, `teeth3-filing_claims.txt` in the scratch folder).
- Repo tests through my runner (policy patched in memory, temp files in the scratch folder):
  `test_owner_state_plants test_owner_state_contracts` → `Ran 4 tests in 10.853s`, `OK`, printing the seven
  `Owner validator=…` lines quoted above and the four `Owner alteration control=…` lines.
- Not run: containers, Linux workflows, the full alteration matrix, the strict pin check. The repository's fixtures
  create temporary stores under the git-ignored `control/test-work/` and `.work/mail-tests/`; no tracked file changed.

CHANGES-NEEDED
