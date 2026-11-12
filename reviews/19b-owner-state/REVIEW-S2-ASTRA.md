Stage 2 needs changes. I found one production regression and three defects in the oracle or its coverage.

Reviewed `9eb193f2..31eeb030`, the requested briefs, coverage, compact ledger, reports and security reviews. I have kept the explicitly deferred stage-3 gaps—including `G22-evidence`, `G22-latch` and `G22-rename`—separate from these findings.

1. **Blocking: renaming an ordinary folder now refuses on a healthy disk because of a message’s MIME contents.**

   **Where:** [filing.py:73](/Users/pab/AresOS-19b-state/control/aresos_control/mail/filing.py:73), especially the full-message fetch and parse at lines 78–80.

   Stage 2 obtains RENAME context by fetching and parsing every message in the source folder. This introduces the message-reading limits from [transport.py:203](/Users/pab/AresOS-19b-state/control/aresos_control/mail/transport.py:203) and [codec.py:39](/Users/pab/AresOS-19b-state/control/aresos_control/mail/codec.py:39) into folder renaming.

   **Reproduction run:** I called the production `rename_folder` using an in-memory store and IMAP fixture. The source was an ordinary folder with one UID, unchanged UIDVALIDITY, and normal Inbox/Sent/Drafts/Trash roles. Its small message contained 45 nested `message/rfc822` parts. There were no storage faults.

   I also loaded the baseline function from `9eb193f2` into memory and ran it against the same fixture:

   ```text
   baseline: state=done; commands=['RENAME']; commits=2
   HEAD: refused mime_limit; commands=['FETCH', 'FETCH']; commits=0
   ```

   An oversized message takes the analogous refusal path through `mail_too_large`; that follows directly from the code, rather than a separately executed large-message probe.

   **Rule broken:** the healthy-disk bar—nothing may refuse without cause—and the fold requirement to preserve what existing tools do. MIME body complexity is not a reason to prohibit renaming its containing folder. Restoring space or restarting cannot cure this refusal.

   **Fix:** construct the exact folder/message identity context without parsing message bodies. Retain UIDVALIDITY and UID identities; obtain any required Message-ID through bounded header-only handling. Add successful healthy-disk rename cases containing deeply nested, excessive-part-count and oversized messages, alongside the context-commit failure/crash tests.

2. **Blocking acceptance defect: the oracle silently drops an unfinished RENAME warning when LIST does not contain the destination.**

   **Where:** [model.py:530](/Users/pab/AresOS-19b-state/control/owner_state_oracle/model.py:530), the check-closing gate at [model.py:824](/Users/pab/AresOS-19b-state/control/owner_state_oracle/model.py:824), and evidence selection at [model.py:1232](/Users/pab/AresOS-19b-state/control/owner_state_oracle/model.py:1232).

   `result_proof()` accepts a delivered LIST with unique Sent, Drafts and Trash roles as sufficient corroboration to close a filing/rename check. It does not require the rename destination to exist.

   **Reproduction run:**

   - Seed a committed, interrupted `mail:rename:r`: source `Source`, destination `MissingTarget`, state `started`.
   - Script a subsequent `control_pending`.
   - Supply a successful, delivered LIST containing normal special folders but no `MissingTarget`.
   - Supply the subsequent decoded filing-check commit.
   - Perturb only that committed row’s `state` from `started` to `done`, leaving the independent script and server evidence unchanged.

   The unperturbed case requires three recovery facts. The changed case requires none, and `compare_proofs` reports no difference. Passing this scenario to the existing perturbation checker produces:

   ```text
   AssertionError: ('Silent owner-state perturbation', ...,
                   'events/2/mail:rename:r/state', 'missing', [...])
   ```

   Thus the perturbation machinery detects the problem when given this scenario; the exercised corpus does not establish the claimed closure of this class.

   **Rule broken:** structure S’s independently corroborated resolution requirement and prohibition on silent expectation shrinkage; round 27’s requirement to keep a warning-producing check open until its actual result is committed. This permits an owner-warning loss to pass acceptance.

   **Important distinction:** current production correctly leaves this particular check open when the target is absent, at [filing.py:192](/Users/pab/AresOS-19b-state/control/aresos_control/mail/filing.py:192). This finding concerns the oracle accepting a planted violation, not an observed production loss.

   **Fix:** require evidence of the actual source-specific check result. A LIST with healthy account roles is insufficient to resolve an absent destination. Preserve the recovery obligation and report an unjustified close. Add this interrupted/restarted scenario to the perturbation corpus, including subsequent acknowledgement, repeated reads and expiry/archive attempts.

3. **Should-fix: the oracle accepts a second draft APPEND under the same intent, including after a simulated storage failure.**

   **Where:** per-command validation in [context.py:220](/Users/pab/AresOS-19b-state/control/owner_state_oracle/context.py:220), generic intent completion in [model.py:967](/Users/pab/AresOS-19b-state/control/owner_state_oracle/model.py:967), and completion checks restricted to terminal `op:` rows at [model.py:1303](/Users/pab/AresOS-19b-state/control/owner_state_oracle/model.py:1303).

   Context validation checks each APPEND independently. Generic intent completion accepts all delivered replies without enforcing the permitted number of effects. Draft APPEND uses a generic intent rather than an `op:` row, so the operation completion checks do not supply the missing constraint.

   **Reproduction run:** Script one `mail_draft_save`, commit one exact APPEND intent, and log either one or two accepted APPENDs with the same call, intent, account, destination, Message-ID, wire hash and flags. Then commit completion:

   ```text
   APPENDs 1 comparison_differences [] expected []
   APPENDs 2 comparison_differences [] expected []
   ```

   I also retained the started intent instead of completing it and supplied a `journal.write` fault trace. One and two accepted APPENDs both produced the same three recovery facts with no comparison difference. Keeping the outcome uncertain therefore does not make the duplicate detectable.

   **Rule implicated:** the disk bar explicitly prohibits a second APPEND. The independent effect checks must enforce that restriction even when the final outcome cannot be recorded. Checking that both effects have valid context does not establish that both were authorized.

   I did not reproduce production issuing the duplicate; this is a demonstrated acceptance gap.

   **Fix:** independently enforce mutation multiplicity per scripted attempt and intent, regardless of terminal state. A single draft-save attempt must not produce two accepted APPENDs. Add a planted retry after failed result storage, and exercise it through persistent exhaustion, cleanup pairs, restart and space restoration. A separately scripted new attempt should remain distinguishable.

4. **Should-fix: the new local flag mutation lacks an independent effect model and full owner-state fault coverage.**

   **Where:** the production addition at [testapp.py:104](/Users/pab/AresOS-19b-state/control/aresos_control/testapp.py:104); local validation at [local.py:40](/Users/pab/AresOS-19b-state/control/owner_state_oracle/local.py:40); completion corroboration at [model.py:984](/Users/pab/AresOS-19b-state/control/owner_state_oracle/model.py:984); and sweep selection at [test_owner_state_sweep.py:22](/Users/pab/AresOS-19b-state/control/mail_tests/test_owner_state_sweep.py:22).

   Production now commits a `LOCAL_FLAG` intent before changing the test-app item. The independent local validator recognizes deletion and account changes, but not `testapp_flag`. Generic intent completion likewise has no local-flag proof.

   **Reproductions run:**

   - Script an exact flag change and commit the item’s changed flag/revision **without any preceding context**. The oracle reports no difference.
   - Supply the correct preceding `LOCAL_FLAG` intent, then atomically commit the item change and intent removal. The oracle reports `lifecycle-proof / unjustified-removal` and retains recovery obligations.

   It therefore accepts the missing-context violation and rejects the valid lifecycle.

   `local_flag` does appear in [test_action_context.py:326](/Users/pab/AresOS-19b-state/control/mail_tests/test_action_context.py:326), but that fence test validates server mutation events and, after crashes, receiver database tables. Those assertions do not establish the local item’s effect or owner-visible warning lifecycle. The full owner-state sweep omits `local_flag`, leaving persistent exhaustion, cleanup pairs and recovery without restart uncovered for this addition.

   **Rule implicated:** R2 applies before every mutation in both apps. The comparison contract requires independently derived owner state across the specified fault modes.

   **Fix:** model `LOCAL_FLAG` explicitly: verify its exact reference, revision, requested value and prior committed context; corroborate completion with the matching committed item change. Add both probes above as regressions, then include this flow in the full owner-state sweep.

Outside this angle, the new RENAME loop also introduces two FETCH requests and full-body processing per message. That creates a folder-size-dependent latency and bandwidth regression even when every message passes parsing.

Verification performed: 36 selected plain-Python tests passed—30 oracle/stage regression tests (`Ran 30 tests … OK`) and six CI-selection/compact-ledger tests (`Ran 6 tests … OK`). The commands were:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests \
.work/venv/bin/python -m unittest \
test_owner_state_oracle.StageTwoPartA \
test_owner_state_oracle.StageOneFixMutations \
test_owner_state_oracle.StageOneRoundTwo.test_expiry_notice_false_cannot_erase_obligation \
test_owner_state_oracle.StageOneRoundTwo.test_archive_cannot_remove_unacknowledged_expiry_including_first_read \
test_owner_state_oracle.StageOneRoundThree.test_rollback_to_existing_reserved_row_does_not_erase_unknown_recovery \
test_owner_state_oracle.OwnerOracle.test_expectation_imports_are_standard_library_only
```

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests \
.work/venv/bin/python -m unittest \
test_mail_ci_selection \
test_owner_state_oracle.OwnerOracle.test_compact_ledger_pins_delta_keys_groups_and_execution \
test_owner_state_oracle.OwnerOracle.test_every_pinned_gap_belongs_to_an_executed_suite
```

The in-memory probes produced the results described above. `git diff --check 9eb193f2..HEAD` reported no whitespace errors. Targeted ledger inspection found the compact file below 1 MB and no stage-2 groups; that does not compensate for the demonstrated oracle gaps. I did not rerun the full filesystem fault sweep or CI. No files were edited and no containers were run.

CHANGES-NEEDED