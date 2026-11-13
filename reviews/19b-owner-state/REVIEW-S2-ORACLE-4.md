# 19b stage 2, fixes round 3: oracle independence re-check

**Angle:** only B1, S1 and the nit of [`REVIEW-S2-ORACLE-3.md`](REVIEW-S2-ORACLE-3.md), checked against
`git diff d2456c51..7b0e9a05` (brief [`19b-s2-fixes-3.md`](../../briefs/19b-s2-fixes-3.md) sections 1 and 2), plus
whether those fixes broke the code they touch. No fresh hunt. **Reviewed head:** `7b0e9a05`. Read-only: this file is
the only repository file written. Probes ran in memory from
`/private/tmp/claude-501/-Users-pab/5d5bbd0b-a538-400c-b84f-360fe127662f/scratchpad/oracle-review-4/probes/` (round-3
probes copied, plus the new ones named below), with the worktree venv and the same in-memory managed-policy patch.

## Findings

| # | Finding | Status | Evidence (run at `7b0e9a05`) |
| --- | --- | --- | --- |
| B1 | `onboarding` (44 keys), `folder_review` (20), `testapp_delete` (1) pinned oracle-side differences at point 0 | **Fixed** | The new `test_every_fault_free_flow_has_only_named_production_gaps` (`test_owner_state_contracts.py:13`) runs all 34 FLOWS + EXTRA through `exercise` and the unmodified `Driver.compare`: `Ran 1 test`, `OK`, 25 flows `production_gaps=0`, nine at exactly their listed counts. My separate rerun of `baseline_any.py` over all 34 flows agrees per flow: `onboarding` 44 → **0**, `folder_review` 20 → **0**, `testapp_delete` 1 → **0**, and also `filing_move`, `filing_copy`, `archive` 1 → **0**. **No flow has any semantic oracle fact.** The remaining nine are the same views as at `e43ea57c`. All nine are production-side (see below). An unlisted flow must have zero entries. A listed flow must match its views, count and SHA-256 exactly, so a new oracle-side difference in those flows also fails. |
| B1 narrowness: onboarding | Self-probe RCPT/DATA/Sent repair bound to the scripted `mail_account_add` | **Narrow** | `onb_negative.py` changes production in memory so the self-probe's compose also addresses `stranger@mail.invalid`. Result: 1 differing view `R2.context-before-command`, with fact `R2.DATA ["script.command.recipients","script.context.recipients"]`. The clean run has 0 views and no facts. The RCPT join (`model.py:126-134`) needs DATA in the same recorded `smtp_transaction`, call and account, bound to the operation with its Message-ID. The repair join (`model.py:152-155`) needs a production-bound repair row, the parent Message-ID and the account-add call and account. The repo regression (`test_owner_state_s2_effects.py:109`) also changes RCPT call/account/transaction and APPEND call/Message-ID, and it passes. |
| B1 narrowness: folder_review | Seed-history intent removal accepted | **Narrow** | `intent_result_proof` (`model.py:1320-1322`) returns early only for `seq <= seed_sequence`. `seed_sequence` is the committed head when the `Driver` is created (`driver.py:35`), so production cannot move it. The early return also requires the same action. `narrow_neg.py`: the seed removal committed by another action → `unjustified-removal`. The unit result is (seed, same action) `True` and (seed, other action) `False`. Runtime removals take the unchanged scripted-transition path. |
| B1 narrowness: testapp_delete | Account from reference scope | **Narrow** | `testapp_account` (`model.py:188-190`) accepts only exactly `testapp/<account>/items`. `narrow_neg.py` changes the op's `items[0].reference.scope` coherently. `testapp/other/items`, `testapp/fixture/items/x` and `mail/fixture/items` each give `unapproved-payload account`, `unapproved-payload items` and `R2.LOCAL_DELETE`. |
| B1 side change | Fence may repeat an unchanged/pre-removal row; destination check moved to `filing_claims` | **OK** | `records.py:94-97` compares a fence's operation that is not in this event's `set` with the row as it stood before the event. Any field that differs still errors. `dest.py`: a coherent wrong `records[0].destination` on the filing result gives `unverified-destination` intact (filing_move, filing_copy). With `filing_claims` removed, the expected set is unchanged, so the alteration matrix cannot see a slip there. |
| S1 | Coherent filing/rename result `state` change caught only by `filing_claims`, undocumented | **Fixed (documented with control)** | FORMAT.md:276 and REPORT.md item 2 now name the state change as well as row removal. The control (`test_owner_state_plants.py:86-103`) now also applies `state → 'started'` (the rename case `partial → started` from S1). It requires the intact `check` to pass, and `Silent owner-state perturbation` with only `filing_claims` disabled. `test_owner_state_plants`: `Ran 3 tests`, `OK`, printing `terminal-state caught_only_by=filing_claims` for move, copy and rename. `teeth3.py filing_claims` (every slip, not just the first): filing_move 24,201 / filing_copy 25,649 / filing_rename 4,924 alterations. Each has **exactly 2 slips: the whole-row removal and the `state` leaf**, so the documented statement is now complete. |
| Nit | `test_baseline_alone_cannot_satisfy_a_plant_assertion` compared a recording with itself | **Fixed** | `test_owner_state_plants.py:79-84` records every plant flow twice. It asserts `new_views(first, second)` is empty and that the second run adds no semantic facts over the first. The test passes. |

**The nine listed production gaps** (`owner_state_quiet_gaps.json`) are all production-side:

- **`settlement` (1):** compares production's public stages with production's own committed stages
  (`stages.mismatch ["/sent_copy_warning"]` vs `committed`). There is no oracle fact. Unchanged since ORACLE-3.
- **`cancel` (4), `expiry` (4), `restore` (6 envelope views):** `views.py` shows that production's own
  `control_pending.page`/`.complete`, `passive.pending-head` and the `mail_accounts`, `mail_filing_notices` and
  `mail_operation_status` envelopes all show the pending item. Only the `control_pending` and `control_log` envelopes
  (and `control_restore_confirm` for restore) omit it. Production disagrees with itself here.
- **`restore` `lifecycle-proof` (1):** the extra facts are `missing-committed-history` (`records.py:84`) and
  `missing-obligation-source` on production's own decoded record. There is no oracle expectation fact.
- **`password` (19):** `intent:…` is committed `started` at seq 5 and never resolved (the server refuses). Production
  discloses `mail:account:new` but not the intent. R2 says "an intent left `started` is itself a warning".
- **`attachment_export` (4), `testapp_export` (2), `export_rollback` (4):** `export:…` is committed `started` (seq 5,
  or 4 for testapp_export) and resolved by `saved` (seq 7, or 5). The `mail_attachment_save` and `download` reply
  envelopes are produced inside that window and omit it. By R2 as written, this is production-side.
  *Observation for the stage-3 lead:* `attachment_export` and `testapp_export` are successful normal saves. Closing
  these gaps as specified means each normal save shows a recovery notice in its own reply and download envelopes. That
  is R2 against "nothing extra in normal use", a stage-3 product decision rather than an oracle defect.
- **`filing_rename` (10):** production's retained warning says `role: ordinary`. The oracle's role is
  `Trash`, taken from the server's independently logged roles in the seeded role race.

## New problems

No blocking or should-fix finding.

**Nit (not blocking):** `qualification` (`model.py:1489-1490`) now counts a `mail_account_add` `done` commit as the
account-add completion only if it touches **no** `intent:` key. Choosing completion by a key that must be absent
means a production that closes its action intent in the same commit as the account result silently turns off the
`qualification.*` comparison. `qual_merge.py` tests this with production patched in memory so that the
"onboarding complete" write also closes an intent:

- Without the merge, a false `sent_policy: server, ready: true` shows `qualification.mail_accounts`.
- With the merge, the oracle's qualification map is `{}` and that view disappears.

No slip results: the merged run still differs (`unjustified-removal`), and the lie is still caught through
`unjustified-resolution`/`unsupported-resolution failure` and the notice/pending views. **Fix (optional):** choose the
completion commit by what it must contain (the `done` commit that writes `mail:account:<id>` with `onboarded`),
rather than by the absence of intent keys.

## What I ran

- Repo tests through my runner (policy patched in memory, temp files in the scratch folder):
  `test_owner_state_contracts.…test_every_fault_free_flow_has_only_named_production_gaps` → `Ran 1 test`, `OK`.
  `test_owner_state_plants` → `Ran 3 tests`, `OK`. `test_owner_state_contracts` + the three new onboarding
  regressions in `test_owner_state_s2_effects` → `Ran 5 tests`, `OK`.
- Probes: `baseline_any.py` (all 34 flows), `entries.py` (the nine listed flows), `views.py`, `events.py`,
  `onb_negative.py`, `narrow_neg.py`, `dest.py`, `teeth3.py filing_claims` (3 filing flows), `qual_merge.py`,
  `crash_one.py`.
- KNOWN-GAPS group comparison `d2456c51` vs `7b0e9a05`: the bucket-0 groups that changed are onboarding, folder_review,
  testapp_delete, filing and archive, with fault-mode keys moving between rows. One spot check
  (`onboarding/persistent/1055/0/crash-restart`) shows only `missing-obligation-source`/`notice-creation-time` on
  production notices, not the new join code.
- Not run: containers, Linux workflows (CI results in REPORT.md read, not verified), the full alteration matrix and the
  strict pin check. The repository's fixtures create temporary stores under the git-ignored `control/test-work/`; no
  tracked file changed.

SAFE
