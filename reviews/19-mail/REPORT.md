# 19 — Mail tools

Builds on draft PR #6. No merge, force push, real account or model run.

Review records: [REVIEW.md](REVIEW.md), [REVIEW-2.md](REVIEW-2.md),
[REVIEW-3.md](REVIEW-3.md), [REVIEW-4.md](REVIEW-4.md),
[REVIEW-5.md](REVIEW-5.md), [REVIEW-6.md](REVIEW-6.md),
[REVIEW-7.md](REVIEW-7.md), [SECURITY-REVIEW.md](SECURITY-REVIEW.md),
[SECURITY-REVIEW-2.md](SECURITY-REVIEW-2.md),
[SECURITY-REVIEW-3.md](SECURITY-REVIEW-3.md),
[SECURITY-REVIEW-4.md](SECURITY-REVIEW-4.md),
[SECURITY-REVIEW-5.md](SECURITY-REVIEW-5.md),
[SECURITY-REVIEW-6.md](SECURITY-REVIEW-6.md),
[SECURITY-REVIEW-7.md](SECURITY-REVIEW-7.md),
[SECURITY-REVIEW-8.md](SECURITY-REVIEW-8.md),
[SECURITY-REVIEW-9.md](SECURITY-REVIEW-9.md),
[SECURITY-REVIEW-10.md](SECURITY-REVIEW-10.md),
[SECURITY-REVIEW-11.md](SECURITY-REVIEW-11.md),
[SECURITY-REVIEW-12.md](SECURITY-REVIEW-12.md),
[SECURITY-REVIEW-13.md](SECURITY-REVIEW-13.md), and
[SECURITY-REVIEW-14.md](SECURITY-REVIEW-14.md).

## For the owner: decisions before merge

**Decided by the owner on 2026-11-08; kept as built:**

The owner answered: “Agree on 8, names etc are enough. Agree on everything else too.” All JUDGMENT-CALLs and PLAN-GAPs listed here are settled, including folder moves under brief 15b.

- **Owner archive, rounds 17–19 — follows the safety rule:** when retained-history admission refuses, run `sudo aresos admin control archive --input '{"before":PAST_UNIX_SECONDS,"confirm":"archive finished history"}'` with your chosen past cutoff. It exports private finished audit history for reading with sudo and compacts SQLite while retaining open work, unacknowledged notices and the independent restore record; repeat for further batches of at most 100 operations. The 1 GiB admission cap now counts SQLite only; the permanent independent journal, rebuildable disk index and private exports use separate physical disk space. Keep those records and leave sufficient disk space for maintenance. The command and confirmation text are unchanged. This explicit owner confirmation follows the safety rule and changes no mailbox.
- **Working storage caps, round 16 — follows the safety rule, not a new choice:** unused compositions expire after 24 hours (128 / 4 MiB current-state cap); private files cap at 256 / 512 MiB per store. Open operations and unresolved warnings stay protected; reaching a cap refuses cleanly with instructions, and retained audit history requires owner archiving at its admission limit. These limits prevent free actions from filling storage and forcing restore confirmation.
- **Installed approval boundary, round 15 — not a separate choice:** this follows the owner's rule that the tool layer enforces asking. Asking tools refuse preparation and submission until the managed Claude Code settings and MCP files are installed and verified; free reads and changes remain available. Letting sends and deletes run where that boundary is missing would break the rule, so no alternative was put to the owner (lead, 2026-11-08).
- **Draft revisions and deletion — owner decided 2026-11-08; kept as built:** editing or sending keeps the old draft, so revisions can accumulate. This keeps every deletion behind its own named approval; silently replacing or removing drafts was rejected.
- **Conservative draft protection — owner decided 2026-11-08; kept as built:** draft text, including quoted history, must fit wholly in approval; any part of a draft, even a binary file, refuses attachment, and older marked Sent copies get the same protection. A narrower policy could allow more attachments and long threads, but would need a reliable way to distinguish who wrote each part; Drafts now also refuses move/copy, while sending itself, forwarding inline and approved deletion remain the routes out.
- **Saving draft attachments — owner decided 2026-11-08; kept as built:** Claude cannot save any draft part or its source to your folders, even a PDF. Save draft attachments in your mail program, or have Claude send the draft itself with `mode=draft`; allowing exports would require reliable provenance on decoded files and full disclosure on reimport.
- **Required special folders — owner decided 2026-11-08; kept as built:** Sent, Drafts and Trash must each be marked on exactly one selectable folder; if one is missing, duplicated or changes, mail changes stop until you fix the server roles and review/record them with `sudo aresos admin mail account_folders`. Earlier Trash and Drafts folders stay protected after that refresh, so a free move cannot become deletion or let drafts escape.
- **Optional Junk and Archive — owner decided 2026-11-08; kept as built:** either can be absent; only filing by that missing role refuses, with instructions to mark the folder in your mail server settings and run the setup step. Duplicated or changed optional roles stop changes involving their current or recorded folders until setup is reviewed; other actions and reads keep working, and search/thread defaults leave out current and recorded Junk folders.
- **Forwarded mail is a file — owner decided 2026-11-08; kept as built:** attached forwarding sends a rebuilt `.eml` file that recipients may need to save and open, and drops private or unlisted headers while preserving decoded binary files. Native inline attached-mail presentation and original header bytes were rejected to keep the approved bytes exact and private recipients protected; recipient-program presentation remains untested.
- **Saved mail files — owner decided 2026-11-08; kept as built:** attaching a saved `.eml` or `.msg` from your folders is refused, even if harmless; forward the mail itself or use its exact mail reference. Allowing local saved mail would need a different provenance and disclosure policy.
- **Ordinary local files and timestamps — owner decided 2026-11-08; kept as built:** settled. Attachments show path, name, size, hash and last change time, not their text. The time does not prove authorship; text Claude wrote may travel in attachments. Showing text-like files wholly in approval was the rejected alternative. Findings that Claude-written text reaches an attachment are accepted behaviour, not a should-fix.
- **Strict content refusals — owner decided 2026-11-08; kept as built:** malformed or unsupported mail and even a literal `Bcc:` line in a text file can refuse attachment. Guessing encodings, trusting file labels or silently editing that text was rejected; support for additional cases needs tests for both the builder and the final check.
- **Size and performance limits — owner decided 2026-11-08; kept as built:** very large messages, threads and folders may refuse: files cap at 25 MiB, encoded mail at 64 MiB, approvals at 16 KiB and history scans at 10,000 messages, with bounded pages and nesting. Smaller selected folders are the current choice over unlimited scans; a durable incremental index and large-account performance work remain deferred.
- **Sent setup — owner decided 2026-11-08; kept as built:** when a short probe finds no Sent copy, setup asks you to confirm whether the client or server saves it rather than guessing from absence. Automatic negative detection would need a proven time bound for the real account.
- **Folder deletion — owner decided 2026-11-08; kept as built:** deletion only runs where the server refuses to delete a folder that holds mail, so no mail can be lost. If another mail program renames the approved empty folder and creates a new empty one with the same name in the same instant, the new empty one is deleted instead; the alternative is to remove folder deletion from the tools. Neither test server qualifies on its own, so the real account's guard still needs your check.
- **Repair after uncertainty — owner decided 2026-11-08; kept as built:** without a recorded final server acceptance, you must inspect an uncertain send yourself even if a Sent copy appears. Automatic repair from that copy alone was rejected because it cannot prove which recipients were accepted; repair never sends again.
- **Rare uncertain Sent-copy repair (round 20):** an empty Sent search keeps an uncertain APPEND unknown until 15 minutes after its attempt ended; the reply names when to try again. Presence can settle it sooner. This is the brief's fixed quiet period. Multiple observed Sent copies produce a persistent warning; nothing is deleted automatically.
- **Approval prompt — owner decision, round 12 — owner decided 2026-11-08; kept as built:** Claude Code keeps its own approval prompt. It now starts with one plain sentence written by the service; the full details follow below it. The shared base format is `{question, operation_id, description}` in that order, passed unchanged through submission; Chrome will use it too. Altering or removing the question refuses the approval. Long summaries say “and N more”; the full fields remain visible, and oversize approvals refuse rather than being cut. Every recipient and sender in the sentence appears with its complete real address (“Mom <stranger@example.org>”); only display names can be shortened. Multiple mailboxes are counted separately. Malformed or missing addresses refuse approval, and complete addresses or folder names that exceed the question cap refuse instead of being cut. Reordered or extra/missing approval fields now refuse with `stale_approval` in both the proxy and service, before any submission or adapter call (round 13); an asking input with a repeated field is refused (round 14).
- **Filing after a folder-role race (rounds 10–11, folder moves in 15b) — owner decided 2026-11-08; kept as built:** messages and folders stay where the move, copy or rename put them; nothing is moved or renamed back or deleted. Folder renames can move between parents. Durable intent records the folder, destination, message count and roles before RENAME; LIST and fresh roles check its new location and ancestors afterward. A newly protected location or assigned special role returns partial with a short warning, filing id, message count and bounded escaped folder names until acknowledged. Following Mail results and `aresos log` repeat the newest three warnings and count the rest; `mail_filing_notices` pages every warning, and `mail_filing_locations` returns exact message-filing locations on request. Cleaning up copies still requires ordinary delete approval. A special role that moves to the target and back between the command and post-check may escape detection: the result can say done in the intended ordinary destination. Refusing free filing or cross-parent folder moves was rejected by the owner; changing this later affects filing/rename policy and its views, with no mailbox migration.
- **Stopping rule from the lead — owner decided 2026-11-08; kept as built:** closed by the owner’s attachment-disclosure decision. Claude-written text reaching an attachment, by any route, is accepted behaviour and no longer a should-fix; approvals show the file’s path, name, size, hash and change time. Blocking findings of other kinds still count.
- **Control-character refusal — owner decided 2026-11-08; kept as built:** malformed mailboxes with non-printable control characters refuse rather than displaying a repaired address; valid bidi/backslash names retain escaped presentation.

**assumed / needs your own check with the real account:**

- Complete onboarding with your aliases, authentication, TLS trust, special folders, delayed Sent behavior and folder-deletion guard; the tests use synthetic accounts only.
- Check complete approvals on both terminal and phone, then try the seven everyday Claude mail tasks; automated protocol tests do not establish how usable those flows feel.
- Send a forwarded `.eml` to recipients using Apple Mail, Outlook, Thunderbird, Gmail on the web and iOS Mail, and check how each opens or saves the exact attachment; the round-5 documentation does not establish its presentation.

## Review fixes, round 22

**Done:** implements `briefs/19-review-fixes-22.md` and the two blocking
findings plus the timeout should-fix in
[SECURITY-REVIEW-14.md](SECURITY-REVIEW-14.md), reviewed head `99280cd0`.
The lead's local `b8aaca68` (review and brief) was included with the first
code push. Last code/test commit: `952c6924db83ff5acb43faa5f3611cb894fad353`.
Every later commit in this run changes only files under `reviews/`.

- **Blocking — short journal writes:** `storage.py` checks the complete byte
  count for each unbuffered record and commit-marker write. A short write is
  treated as disk full immediately; an exception or short count truncates the
  incomplete line and syncs the remaining complete records. The failure latch
  prevents another transaction until restart recovery; replay clears it only
  after its complete commit marker succeeds. A short commit leaves the full
  event/prepared transaction available for replay. A short event leaves no
  partial fence. Startup removes a torn final line and preserves every complete
  fence, including an uncommitted record that still needs prepared replay or
  owner restore. Corrupt complete records, middle corruption, whole-suffix
  loss and a complete commit marker with damaged newline framing still refuse.
- **Storage classification:** `common.py`, `engine.py` and `daemon.py` classify
  ENOSPC/EDQUOT as `storage_limit` with a plain disk-full message, EIO as
  `storage_error`, and SQLite FULL/IOERR by their primary code. Journal failures
  are classified at the writer. Request admission, dispatch and streamed
  transfers preserve those errors instead of calling them Mail transport
  failures. A failed cleanup remains an error and leaves the latch set.
- **Blocking — observed duplicates:** `mail/adapter.py` builds a Sent
  observation before recording its warning. Storage exceptions while recording
  cannot erase the observed copies or warning. The reply includes
  `warning_storage_error` with the disk-full/storage error. `engine.py` returns
  this observation from status, completed repair, new repair admission and
  unresolved-repair settlement; failed warning persistence prevents settlement
  or a new attempt. A separate settlement-write failure returns the copies,
  warning and `settlement_storage_error`. If SQLite applied the prepared event
  before its commit marker failed, the response retains the prior unresolved
  operation until restart replay completes it. Nothing is deleted or sent.
- **Should-fix — changing-request replies:** `requests.py` supplies one
  changing-request classification to both the engine and `protocol.py`.
  Changing calls, saved acknowledgements, uploads, downloads and account setup
  all use a 30-second socket window; archive retains its explicit 600-second
  window and reads retain ten seconds. Loss/timeout/EOF after connection can
  mean a commit, so the client returns `error.code=unknown`, `data.state=unknown`,
  a password-free request reference/hash (operation ID when known), and an
  explicit instruction to check status, pending/log or account state without
  automatically repeating the request. `ok=false` means success is unconfirmed;
  it does not claim the operation failed. `proxy.py` keeps that uncertainty and
  the already-saved file metadata, and does not issue a refusal acknowledgement
  for an uncertain download. The eleven-second save succeeds under the normal
  policy; with an intentionally ten-second client deadline it reports unknown,
  and the committed save is visible in the subsequent log. A streamed upload
  with a lost final acknowledgement also remains unknown while its import
  commits.
- **Generated artifacts:** no tool schema/description changes were needed;
  `python3 control/generate.py --check` prints `Generated artifacts match definitions`.

**Tests (19 additions; no earlier assertion weakened, skipped or deleted):**

| Area / file | Exact test names |
| --- | --- |
| Journal — `control/tests/test_review22_storage.py`, `Journal22` | `test_review22_short_commit_prepare_fails_and_full_replay_clears_latch`; `test_review22_short_event_then_enospc_discards_partial_and_syncs`; `test_review22_zero_and_short_event_writes_are_not_success`; `test_review22_startup_truncates_torn_event_or_commit_and_replays_prepared`; `test_review22_corrupt_committed_record_and_middle_tail_still_rejected`; `test_review22_storage_errno_and_sqlite_errors_never_become_mail_transport` |
| Observations — `control/mail_tests/test_review_fixes_22.py`, `Duplicates22` | `test_review22_status_returns_two_copies_warning_and_enospc`; `test_review22_completed_repair_returns_two_copies_warning_and_enospc`; `test_review22_settlement_returns_two_copies_warning_and_enospc_without_false_done`; `test_review22_observation_survives_every_storage_exception_while_recording`; `test_review22_new_repair_returns_observation_before_admitting_another_attempt`; `test_review22_settlement_write_failure_preserves_observation_and_recorded_state`; `test_review22_short_settlement_commit_does_not_report_done_before_replay` |
| Actual delayed writes — `control/tests/test_review22_protocol.py`, `Timeouts22` | `test_review22_save_held_eleven_seconds_receives_committed_ack`; `test_review22_save_after_client_timeout_is_unknown_and_committed_log_is_visible`; `test_review22_upload_lost_final_ack_is_unknown_and_import_commits` |
| Reply policy/proxy — same file, `ReplyPolicy22` | `test_review22_one_policy_for_calls_saves_uploads_downloads_and_setup`; `test_review22_connection_loss_names_operation_and_setup_never_exposes_password`; `test_review22_proxy_preserves_unknown_save_ack_and_does_not_cancel_unknown_download` |

The only earlier-test edit is the connection substitute in
`ApprovalQuestions.test_round13_client_serializes_caller_order_without_result_presentation`
(`control/tests/test_approval_questions.py`): it now accepts the optional request
parameter supplied by the client. Its caller-order assertion is unchanged.
The existing streaming test's assertions for committed framing, middle
corruption and suffix loss are also unchanged.

**Verified — failures on the reviewed source:** archived `99280cd0 control`
under this worktree's `.work/round22-before/` and ran the new tests against
that production code. The short-commit test returned `ok=true`; partial-event
ENOSPC returned `transport_error`; the torn final event was rejected as
`evidence_corrupt`; the actual save delayed at `sqlite_prepared` for eleven
seconds raised `transport_error` after ten seconds. The three duplicate tests
(status, completed repair and settlement) all lacked the `evidence` field after
the actual journal-write ENOSPC injection. The current-source versions pass.
The old-source batch printed `Ran 4 tests in 11.075s; FAILED (failures=2, errors=3)`
(the torn-event subtest leaves its engine closed, causing the second tail
subtest to error too); the duplicate batch printed `Ran 3 tests in 0.076s;
FAILED (errors=3)`. These are behavioral regressions, not syntax-only checks.

**Verified — local gates before each push:**

```sh
python3 control/generate.py --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest test_operations test_record test_crashes test_approval_questions test_strict_json test_boundary test_boundary_exact test_ingress_bounds test_journal_closed test_policy_sources test_archive test_journal_capacity test_journal_streaming test_restore_batches test_review21_pending test_review21_storage test_review22_storage test_review22_protocol
```

First-push gates printed `Generated artifacts match definitions`, `Ran 111 tests in 84.835s; OK` and `Ran 100 tests in 94.671s; OK`.
The plain-Mail output also printed `Review20 archives admitted before ledger refusal (2150 attempted maximum): 2150`; the base output retained the record/memory metrics and showed no failed tests.

The initial local base batch, before the final fixes, printed `Ran 100 tests in 88.294s; FAILED (failures=1, errors=1)`: the old socket substitute accepted no request argument, and the complete-commit-marker newline assertion detected overly broad tail recovery. Both were fixed before the first push, preserving all existing assertions. No failing workflow was triggered for these local failures.

Report-push gates printed `Generated artifacts match definitions`, `Ran 111 tests in 84.529s; OK` and `Ran 100 tests in 93.849s; OK`. The same record/memory metrics were printed; no failed or skipped tests were reported.

**Verified — last code/test head and both workflow passes:**

Code/test head: `952c6924db83ff5acb43faa5f3611cb894fad353`.

| Workflow / attempt | Exact output |
| --- | --- |
| [Mail 42472339218, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42472339218/attempts/1) | `Ran 130 tests in 195.594s`; `Control base suite PASS`; `Ran 232 tests in 791.160s`; `Control Mail suite PASS`; `OK` |
| [Mail 42472339218, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42472339218/attempts/2) | `Ran 130 tests in 196.550s`; `Control base suite PASS`; `Ran 232 tests in 800.651s`; `Control Mail suite PASS`; `OK` |
| [Independent base 42472339198, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42472339198/attempts/1) | `Ran 130 tests in 165.281s`; `Control base suite PASS`; `OK` |
| [Independent base 42472339198, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42472339198/attempts/2) | `Ran 130 tests in 173.175s`; `Control base suite PASS`; `OK` |

Every pass prints `Generated artifacts match definitions`. The Mail logs include
all 19 new round-22 methods; the independent base logs include all 12 new base
methods. The Mail workflow also confirms distinct fixture isolation.
The unchanged [boundary workflow 42472339206](https://github.com/Ares-Empire/AresOS/actions/runs/42472339206)
passed 16 fixture tests (`Ran 16 tests in 0.014s`), both confinement modes
(`BOUNDARY_OK`, 127 attacks each), policy-source checks and `ISOLATION_OK` for
the separate coding user. Attempt API records identify this code head and
`success`; these are automatic `pull_request` runs. No workflow has failed
in this run.

All later commits in this run change only files under `reviews/`. Final-head
workflow runs belong in PR #9's body. Second passes rerun the same automatic
pull-request run IDs with `gh run rerun`; no manual workflow dispatch is used.

**Not verified:** physical disk exhaustion/power loss, external disk consumers,
real-account timing, installed-host approval presentation and terminal/phone
usability. These tests run production journal/SQLite and protocol paths with
synthetic accounts and controlled faults; they do not establish physical
power-loss durability. No visual UI changed; no new screenshots are needed.
No Gradle daemon, Minecraft client, host install, real account or model session
was started. No protected OS/mod/workflow files changed.

**JUDGMENT-CALL:** none beyond the brief's explicit choices. Short writes fail
immediately instead of attempting to conceal a partial write by continuing;
unacknowledged evidence stays visible, and possibly committed replies remain
unknown. Existing owner decisions and the round-21 fail-closed disk bar remain.

**PLAN-GAP:** none added. Finite reply windows cannot guarantee receipt; the
unknown result and status/request check are necessary even with the longer
window. Complete uncommitted fences remain retained for restore/replay safety.

**Open questions:** none for this brief. Owner checks listed above remain.

**Workspace cleanup:** `.work/` inventory contains **0 files over 500 MiB**.
No large downloads, duplicate images or extracted images were created this run.


## Review fixes, round 21

**Done:** implements `briefs/19-review-fixes-21.md` and the four blocking
findings plus the pending-memory should-fix in
[SECURITY-REVIEW-13.md](SECURITY-REVIEW-13.md), reviewed head `53a2d391`.
The lead's local `34f09a7a` (review and brief) was included with the first
code push. Last code/test commit: `79b3ef1e399c1ad80f2cd9ba71d0efa55914907e`.

**Lead decision, 2026-11-08 (not an owner decision):** cancellation applies
only to a prepared, reserved operation that has never submitted. Such an
approval expires within 15 minutes, and submission still asks the owner.
A full disk preventing cancellation is an availability failure. No ledger
can hold physical space against other programs on the laptop sharing the
filesystem. Under full or nearly full storage, the safety promise is to
fail closed: no send, delete or unsubscribe without its approval, repeated
or different from that approval; no false done result; no lost or corrupted
record; and a plain disk-full error. Cancel and restore reservations protect
against the service's own writes only; protection against other programs
is best effort. On a normal disk, work must have a cause to refuse. This
bar is stated in the generated cancel/export descriptions and common
storage-limit guidance.

- **Blocking — history-sized restore holds:** `storage.py` uses one streaming
  reconstruction iterator for both admission and confirmation. Only missing,
  newer, submitting or invalidated reserved operations enter the work budget;
  unchanged closed operations and matching archive tombstones do not. The
  fixed 256 KiB batch/final-marker allowance is independent of history size.
  The hold is loaded before startup bookkeeping or index writes can spend
  its capacity. Confirmation still uses bounded batches and releases the
  hold when it ends. One hundred unchanged completed operations plus a
  metadata rollback confirm at 8 MiB free; 10,000 retained operations with
  three changed records fund and reconstruct exactly those three.
- **Blocking — replay double counting:** prepared events now carry the
  admission plan that was accepted before their fence was written.
  Startup replaces spent rights with the remaining SQLite/commit-marker
  replay work. Cancellation, restore confirmation and repair settlement
  spend that existing capacity, including when the optional index cannot
  fit. Prepared owner confirmation replays without asking for a second
  confirmation. Older prepared events without a saved plan can use an
  existing cancel/settlement right.
- **Blocking — caller exports:** new `exports.py`, plus `storage.py`,
  `mail/adapter.py`, `blobs.py`, `requests.py`, `protocol.py`, `proxy.py` and
  `files.py`, admit both private bytes and caller bytes before creating the
  private export. A durable export ID retains the caller-write and completion
  budget across requests and service restart. Caller admission checks the
  actual destination filesystem too. Completion spends only that export's
  hold; refusal removes its newly created private blob and origin metadata.
  Partial blob writes discard private staging inodes; caller writes use
  the existing unnamed inode and publish only after a complete synced write.
  ENOSPC during blob bytes, origin publication or caller bytes reports
  `storage_limit` with disk-full wording and leaves no output, orphaned blob,
  staging file or export reservation in these fault tests. Other laptop
  programs can still exhaust shared space; reservations are not filesystem
  quotas. Existing destination-race rules still clear a pinned published
  inode and report empty remnants rather than unlink an unrelated replacement.
- **Blocking — late Sent duplicates:** `mail/adapter.py` applies copy-count
  detection to status, repair and settlement evidence, including the
  original send's evidence when reading its Sent-copy repair ID.
  `engine.py` constructs status after evidence so its first reply includes
  the warning. Completed repairs also check for late arrivals. One stable
  notice ID per send is updated only when the detected count changes;
  repeated observations do not append history or reset acknowledgement.
  Warnings survive subsequent stage/outcome writes. Nothing is deleted and
  repairs never submit SMTP. If warning persistence cannot fit, status
  includes the observed warning and the storage refusal in evidence.
- **Should-fix — pending memory:** `engine.py` streams the page and the
  canonical cursor hash, keeping only returned summaries. It never reads
  approval descriptions for pending responses. Cursor bytes remain compatible
  with the earlier canonical `[scope, summaries]` digest. Unknown operations,
  including restored operations, use this same path. Measured peak for
  1,000/10,000 unknowns is `18,865 / 17,760 bytes`, below one fixed 1 MiB
  bound after one-time notice-module imports.
- **Descriptions/artifacts:** `definitions.py`, `mail/definitions.py`, the
  three generated tool catalogues and `docs/control/TOOLS.md` explain the
  lead's full-disk bar, caller export limit and continuing late-duplicate
  checks. `control/generate.py --check` reports matching artifacts.

**Regression tests (14 additions; none weakened, skipped or deleted):**

| Area | Exact test names |
| --- | --- |
| Restore actual work | `RestoreWork21.test_review21_100_completed_metadata_rollback_at_8mib_has_no_reconstruction`; `test_review21_10000_completed_hold_matches_only_three_changed_operations` |
| Reserved replay | `ReservedReplay21.test_review21_cancel_prepared_replay_spends_original_hold_and_status_serves`; `test_review21_prepared_restore_confirmation_replays_from_its_existing_hold`; `LateDuplicates21.test_review21_prepared_repair_settlement_replays_from_its_original_hold` |
| Exports | `Exports21.test_review21_5mib_uncached_export_at_12mib_refuses_before_either_copy_and_cancel_works`; `test_review21_enospc_during_blob_bytes_or_origin_publication_retains_nothing`; `test_review21_enospc_during_caller_write_cleans_download_and_new_private_blob`; `test_review21_export_hold_survives_restart_and_blocks_other_service_writes_until_completion` |
| Late duplicates | `LateDuplicates21.test_review21_duplicate_landing_after_successful_retry_warns_on_next_status_and_completed_repair`; `test_review21_unknown_repair_settlement_counts_duplicates_and_preserves_warning` |
| Slow durable reply | `DurableReply21.test_review21_durable_write_sync_beyond_read_deadline_returns_its_committed_result` |
| Pending streaming | `Pending21.test_review21_1000_and_10000_unknowns_correct_pages_cursor_and_fixed_memory`; `test_review21_pending_never_reads_approval_description_and_keeps_canonical_cursor` |

The tests live in `control/tests/test_review21_storage.py`,
`control/tests/test_review21_pending.py` and
`control/mail_tests/test_review_fixes_21.py`. The earlier base-test schema edit
is `Files.test_download_hash_and_private_transfer_metadata_checks`: it keeps
its exact hash/size equality assertion over those fields and adds assertions
for the required durable export ID/hold. All its other assertions remain.
`Integration.test_cli_generated_help_admin_and_today_log` also keeps its
assertion and adds the actual returned JSON to its failure message.
The shared streaming fixture predates `operation_versions`; the new restore
fixture supplies the versions real `Store.write` commits, so unchanged means
unchanged. Caller ENOSPC runs actual FilePolicy write/cleanup code with only
Linux unnamed-inode creation substituted on macOS; real Linux transfers,
races and framing remain covered by the complete container suites.

**Verified — failures on the reviewed source:** isolated `git archive
53a2d391 control` under this worktree's `.work/round21-before/`, loading
that production code with the new regression tests, reproduced the missing
export admission (5 MiB exported at 12 MiB free), blob ENOSPC mislabeled
`transport_error`, caller ENOSPC mislabeled `file_refused`, late duplicates
without warning, cancelled prepared replay refusing with a 144,656-byte
hold plus an additional 159,312-byte charge, and prepared confirmation still
locked after restart. The pending test peaked at 1,621,851 bytes already
at 1,000 unknowns (over its fixed bound), and its approval-access trap failed.
The separate unchanged-history probe printed `100 unchanged operations,
restore hold: 15962944` and `Confirmation: False storage_limit` at 8 MiB
free. These are behavioral failures on the reviewed source, not passing
syntax/import checks. The corresponding new-source tests pass.

**Verified — local before each push:**

```sh
python3 control/generate.py --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest test_operations test_record test_crashes test_approval_questions test_strict_json test_boundary test_boundary_exact test_ingress_bounds test_journal_closed test_policy_sources test_archive test_journal_capacity test_journal_streaming test_restore_batches test_review21_storage test_review21_pending
```

Output: `Generated artifacts match definitions`; `Python syntax OK: 114 files`.
All local suites below printed `OK`:

| Push | Plain Mail output | Selected base/new output |
| --- | --- | --- |
| First code batch (`ba18efa6`) | `Ran 104 tests in 84.020s` | `Ran 87 tests in 59.467s` |
| Deadline correction (`79b3ef1e`) | `Ran 104 tests in 83.691s` | `Ran 88 tests in 70.757s` |
| Reviews-only report | `Ran 104 tests in 83.688s` | `Ran 88 tests in 70.659s` |

The plain-Mail run includes all seven new Mail regressions; the final base
command includes all seven new storage/pending/reply regressions. The first
code batch precedes the additional delayed-reply regression. Existing round-20 archive
output remains `Review20 archives admitted before ledger refusal (2150
attempted maximum): 2150`; streamed journal verification remains below its
fixed 2 MiB bound at both history sizes. `git diff --check` prints nothing.
No changes under the excluded OS/mod/owner/design/workflow paths.

**CI correction:** initial Mail run [42464896027](https://github.com/Ares-Empire/AresOS/actions/runs/42464896027)
on `ba18efa6` stopped in its shared base suite: `Ran 117 tests in 166.689s`;
`FAILED (failures=1)`. `test_cli_generated_help_admin_and_today_log` received
`ok=false` from the root admin CLI; the existing assertion printed only
stderr, omitting the returned error. That same test passed in the independent
base run [42464895981](https://github.com/Ares-Empire/AresOS/actions/runs/42464895981),
and boundary [42464895990](https://github.com/Ares-Empire/AresOS/actions/runs/42464895990)
passed. The failed case took about ten seconds longer, consistent with the
client's ten-second response deadline; the original error payload is unavailable,
so this timing diagnosis is an inference. A deterministic new regression
holds a real transaction at `sqlite_prepared` for 11 seconds: reviewed
production `Client.request` fails with `TimeoutError` / `transport_error`,
while the fixed client returns the committed result with exactly the two
expected fixture audit records. `protocol.py` now gives mutating calls a
30-second reply window (archive retains 600 seconds), with no retry. The
existing integration assertion now includes stdout for a future failure.
This fixes the reproduced deadline failure without weakening an assertion;
the final full runs below cover the installed CLI as well. No Mail protocol
tests ran in that initial failed workflow because its shared base step stopped.

**Verified — last code/test head `79b3ef1e399c1ad80f2cd9ba71d0efa55914907e`:**

| Workflow | Run / attempts on this code head | Result |
| --- | --- | --- |
| Control Mail | [42465513705 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42465513705/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42465513705/attempts/2) | Both PASS: `Ran 118 tests` shared base and `Ran 225 tests` Mail; `OK`; `Control base suite PASS`; `Control Mail suite PASS`; fixture isolation confirmed. |
| Control base | [42465513707 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42465513707/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42465513707/attempts/2) | Both PASS: `Ran 118 tests`; `OK`; `Control base suite PASS`. |
| Control boundary | [42465513734](https://github.com/Ares-Empire/AresOS/actions/runs/42465513734) | PASS: 16 native fixture tests, both confinement modes (127 attacks each), policy-source/drop-in checks and coder isolation. |

Mail runs `bash control/ci/mail/run.sh`, including the shared base suite via
`bash control/ci/test.sh`, followed by isolated real-mail fixtures and
`python3 -m unittest discover -s control/mail_tests -v`. Base runs the pinned
Fedora container with `bash control/ci/test.sh`. Boundary runs its unchanged
Docker build, hostile programs in both filter modes and isolation script.

Both base/Mail second passes rerun their existing automatic pull-request IDs
with `gh run rerun`; no manual dispatch or validation-only push. All later
commits in this run change only files under `reviews/`. Final-head workflow
IDs/attempts and results are recorded in draft PR #9's body after the report
push, avoiding another report/head update cycle. Three pushes total (one
necessary CI correction); normal push verification was kept on all three,
with no hook bypass. No merge, rebase, force push or push to main. All new
commits carry the requested model trailer.

**Not verified:** no real account/provider timing, native terminal/phone
approval presentation, recipient-program presentation, physical power-loss
durability or race against arbitrary external disk consumers. No model
session, host installation or real delivery ran. Minecraft/Gradle checks
are outside this brief's overridden rules; no Gradle daemon was started.
No screenshots are needed for these storage/protocol changes.

**JUDGMENT-CALL:** follows the lead's explicit bar above. No additional owner
choice or irreversible mailbox action. Export rights persist when a caller
fails to report completion; this conservatively protects a possibly active
write across service restart. Normal proxy completion/refusal releases them.

**PLAN-GAP / open questions:** none added within this brief's scope. Existing
owner/provider qualification gates still apply. Final `.work/` scan for files
over 500 MB: `[]`.


## Review fixes, round 20

**Done:** implements `briefs/19-review-fixes-20.md` and all five findings in
[SECURITY-REVIEW-12.md](SECURITY-REVIEW-12.md), reviewed head `d5a0b24a`.
The owner's local `bf717f6a` (review and brief) went with the first code batch.
Implementation commits: `eec78cfb`, `61552457`, `22b5bb6d` and
`33a7f9e05613c8dce257dc263634405bebf41e04`, followed by
`1786c9a0af1b96adf68df81f13ff76a7a9f5822f` (last test change). The last
commit keeps the round-18 archive fixture under `HISTORY_BYTES=0` as well as
restore confirmation; only the physical-free-space patch ends after confirmation.

- **Blocking — index growth and inconsistent maintenance/cancel floors:** new
  `control/aresos_control/space.py` owns physical admission and the existing
  logical audit-quota check. In plain words: a pending approval holds the bytes
  needed to cancel it; an unresolved repair holds the bytes needed to settle it;
  a detected restore holds the bytes needed for confirmation. Every write leaves
  all other held bytes plus one fixed 4 MiB safety floor. The named recovery
  write spends its own hold and needs no second reserve. Holds are admitted
  before the independent fence, published after durable completion, rebuilt from
  retained operations/verified evidence at startup, and released when the right
  ends. `retention.py` removes the old physical floor selector; the removed
  64/20/16/4 MiB physical floors have no remaining callers.
  The existing compactable SQLite audit quota/headroom is a separate logical
  bound; it is checked by the same admission function.
- `storage.py` applies the ledger to transactions, startup schema/retention
  bookkeeping, prepared replay, restore confirmation and index creation.
  Verification itself can stream without writing an index. Index admission uses
  a conservative estimate before creating its SQLite file. If refused, the
  service starts without it: asking actions explain `storage_limit`; cancel,
  operation status and owner confirmation work using journal scans. Latest
  evidence fallback holds at most 32 IDs per scan window. `archive.py` admits
  export, pruning and VACUUM through the same ledger; `blobs.py`,
  `mail/transport.py`, `mail/adapter.py`, `engine.py` and the local test receiver
  share that ledger for blob/wire/password writes and expiry, including directory
  initialization. Optional retention bookkeeping can defer on low disk without
  blocking service recovery.
- **Blocking — restored repair identity:** `storage.py` retains each Mail
  repair's `repair_of`, stage and attempt end time in its compact description,
  separate from escaped untrusted content. Reconstruction restores its lookup
  identity and settlement hold. `engine.py` reuses it after confirmation.
  Older evidence that retained only the send ID but omitted the stage blocks
  another repair for either stage of that send. If even the relationship is
  unavailable, the unresolved legacy record conservatively blocks new Mail
  repairs rather than guessing. Status explains missing identity.
- **Blocking — an APPEND can still land after an empty search:** `engine.py`
  permits negative Sent settlement only for an ended unknown attempt after the
  fixed 900-second quiet period. Earlier absence keeps that attempt unknown and
  returns its UTC retry time; missing end-time evidence remains uncertain.
  Restart starts a conservative new interval for an interrupted running attempt.
  `mail/adapter.py` searches on a new IMAP session, validates roles on that
  session, and selects Sent read-only. It records Sent APPEND attempt boundaries,
  refuses an immediate retry of an earlier unfinished/recent APPEND, and performs
  a fresh read-only copy count after every Sent APPEND, including a lost answer.
  Multiple copies add an operation warning and a bounded persistent notice that
  repeats in following Mail results/logs. Nothing is automatically deleted;
  repair never invokes SMTP. `mail/definitions.py`, the generated Mail tool JSON
  and `docs/control/TOOLS.md` describe these semantics.
- **Should-fix — restore memory:** `storage.py` reconstructs at most 32
  operations per batch, with at most a 64 KiB permanent record. Intermediate
  batches retain `restore_pending`; only the last batch advances generation and
  clears the lock. Small restores keep one atomic final record and all earlier
  crash assertions. Confirmation returns at most 100 unknown IDs plus an omitted
  count and `control_pending` for the rest, so completing a large restore does
  not then fail the result-size limit. `definitions.py` and the generated
  reference document the bounded response. `control/README.md` explains the
  ledger, streaming fallback, identity, quiet period and bounded confirmation.

**Tests by name:** new `control/mail_tests/test_review_fixes_20.py` uses production
Engine/Store/Mail code, synthetic free-space accounting charged for real private
file growth, and offline IMAP/SMTP substitutes. No physical disk is filled.

- `Ledger20.test_review20_2000_real_delete_records_index_at_30mib_preserves_cancel_and_streamed_status`
  creates 2,000 distinct closed records based on a real service-generated delete
  approval, removes the disposable index, starts at 30 MiB free, refuses index
  creation/asking, then successfully serves status and cancel by streaming.
- `Ledger20.test_review20_2150_archive_attempts_at_20mib_preserve_pending_cancel`
  admits all 2,150 production archives from 20 MiB and still cancels the pending
  approval. `test_review20_38_uncertain_repairs_and_archives_at_20mib_preserve_cancel`
  repeats round 19's 38-attempt sequence with the same physical budget.
- `Ledger20.test_review20_all_writers_preserve_live_rights_and_cancel_uses_only_its_own`
  refuses ordinary writes, expiry, blob/wire/password/receiver writes and archive
  at the held-bytes boundary; cancellation succeeds without changing any other
  hold. `test_review20_rights_release_on_send_expiry_cancel_and_repair_settlement_and_survive_restart`
  checks holds across restart and their release for submission, expiry,
  cancellation and repair settlement. `test_review20_restore_confirmation_owns_and_releases_its_reservation_without_an_index`
  actually restarts with index admission refused, confirms using only its hold,
  releases it, and refuses the old approval.
- `RepairIdentity20.test_review20_restore_unknown_repair_retains_original_and_stage_and_reuses_one_attempt`
  replays the review's backup/unknown-repair/restore/confirm/repair sequence and
  ends with one unresolved attempt. `test_review20_older_evidence_without_repair_stage_refuses_both_new_stages`
  covers older permanent evidence, both stage refusals and unchanged durable
  state.
- `Append20.test_review20_late_append_inside_quiet_period_keeps_one_attempt_names_time_then_settles_one_copy`
  leaves the remotely pending APPEND unknown after empty evidence, names the
  retry time, lets the old APPEND finish, then settles the same attempt with one
  copy. `test_review20_late_append_after_quiet_period_never_duplicates_silently_and_warning_repeats`
  deliberately completes an earlier APPEND beyond the quiet period during a new
  append: two copies stay intact, with the warning in the result, operation
  status and persistent notice. `test_review20_negative_settlement_uses_new_readonly_imap_connection_after_quiet_period`
  exercises production Transport session construction/logout, fresh sessions and
  read-only selection at the 900-second boundary.

New `control/tests/test_restore_batches.py` adds
`RestoreBatches.test_review20_1000_and_10000_restored_operations_have_fixed_verification_peak_and_bounded_records`
and `test_review20_crash_after_first_restore_batch_keeps_lock_until_confirmation_finishes`.
Both use real journals/SQLite: each reconstructed record respects the count/byte
bound, both history sizes must verify below the same 2 MiB Python peak bound,
and a crash after a committed batch must retain the lock and finish on a later
owner confirmation. All reconstructed operations remain available.

**Earlier test changes — assertions retained:** round 16's
`test_review16_low_disk_space_refuses_blobs_and_journal_before_fence` and round
17's `test_review17_free_limit_and_physical_reserve_preserve_owner_restore_confirmation`
use the ledger's actual holds plus its safety floor. Round 18's
`test_review18_restore_confirms_above_every_quota_and_can_archive_afterward`
spends the confirmation hold at that boundary, then archives with unheld space,
while keeping the audit quota exhausted (`HISTORY_BYTES=0`) for both calls;
`test_review18_repairs_and_ordinary_recovery_cannot_consume_restore_room` checks
the ledger boundary. Round 19's
`test_review19_cancel_works_above_history_cap_and_other_paths_leave_its_physical_room`
uses the actual cancel hold and checks the shared admission function instead of
the deleted floor selector. Its negative Sent-settlement test advances the
synthetic clock by the required 900 seconds and retains every old assertion.
Round 16's restart helper reconnects wire/password writers to the new shared
ledger. No earlier file under `control/tests/` changed; no test was weakened,
skipped or deleted. Existing compact-record size and small-restore crash
assertions initially caught implementation mistakes; the implementation was
corrected and those assertions remain unchanged.

**Verified locally on the code/test head:**

```text
python3 control/generate.py --check
Generated artifacts match definitions

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py
Python syntax OK: 110 files
Ran 97 tests ... OK
Review20 archives admitted before ledger refusal (2150 attempted maximum): 2150

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest test_operations test_record test_crashes test_approval_questions test_strict_json test_boundary test_boundary_exact test_ingress_bounds test_journal_closed test_policy_sources test_archive test_journal_capacity test_journal_streaming test_restore_batches
Ran 81 tests ... OK
Record growth: tiny send=4078 bytes; maximum body + 25 MiB send=4078 bytes
Review20 restored journal verification (retained, peak bytes), 1k/10k missing operations: [(13785, 216714), (13785, 216717)]
```

The new restore class was also run explicitly: `python3 -m unittest
test_restore_batches -v` with the same base `PYTHONPATH` passed both tests.
The required three pre-push checks and new tests are repeated before the report
push. Outputs are private scratch under `.work/round20-*-corrected.txt`,
`.work/round20-*-report.txt` and `.work/round20-restore-local.txt`, not credentials or provider data.

**Reviewed-source replays:** exported only `control/` from `d5a0b24a` into this
worktree's `.work/round20/baseline/`; no other checkout was touched. Four
plain-Python behavioral probes against that source reproduced each blocking
finding: index growth left 13,082,624 bytes and cancel returned `storage_limit`;
2,150 production archives from 20 MiB also blocked cancel; the backup/restore
sequence allocated two unresolved repairs; immediate negative settlement allowed
two Sent copies with no warning. A separate baseline memory probe measured
2,842,018 versus 27,033,730 peak bytes after 1,000/10,000 missing operations.
The reproductions ran with:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.work/round20/baseline/control:.work/round20/baseline/control/mail_tests:.work/round10/vendor python3 .work/round20/baseline-probes.py
Ran 4 tests ... OK (assertions reproduce the four bad outcomes)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.work/round20/baseline/control:.work/round20/baseline/control/tests:.work/round10/vendor python3 .work/round20/baseline-memory.py
Ran 1 test ... OK (assertions reproduce history-sized verification memory)
```

The fixed regressions pass. Both fixed verification peaks stay below the same
2 MiB bound. Round 19's original 38-attempt regression still passes, as it
also did in the review. Baseline probes are scratch reproductions, not claims
that absent ledger APIs were behavioral failures. No real server was contacted.

**GitHub verification of the last code/test commit:** `1786c9a0af1b96adf68df81f13ff76a7a9f5822f`.

| Workflow | Runs on that code/test commit | Result |
| --- | --- | --- |
| Control Mail | [42458103855 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42458103855/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42458103855/attempts/2) | Both PASS: 111 shared-base + 218 Mail tests; fixture isolation confirmed; all 2,150 archive attempts admitted and cancellation succeeded. |
| Control base | [42458103848 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42458103848/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42458103848/attempts/2) | Both PASS: 111 tests; generated artifacts match. |
| Control boundary | [42458103857 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42458103857/attempts/1) | PASS: 16 native fixture tests and both confinement modes (127 attacks each), policy-source/drop-in checks and coder isolation. |

The superseded first batch on `33a7f9e0` has base
[42456846835 attempts 1 and 2](https://github.com/Ares-Empire/AresOS/actions/runs/42456846835)
both passing (111 tests), boundary
[42456846833 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42456846833)
passing, and Mail
[42456846886 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42456846886/attempts/1)
passing (111 shared-base + 218 Mail tests). GitHub automatically cancelled that
Mail run's second attempt when the corrective test push arrived. It is not
passing evidence for the corrected head. The correction restores the quota
patch around archive; no failed workflow result prompted it.

Both second base/Mail passes rerun the same automatic pull-request run IDs with
`gh run rerun`; no workflow was manually dispatched. Any later commit changes
only files under `reviews/`. The PR body records both base/Mail passes and the
boundary result on the final report head. Three pushes total: the first code/test
batch including the owner's local commit, a test-only correction, then the report; nine automatic workflow IDs,
with reruns on the same IDs for second passes. The additional test push was
necessary because the initial floor-fixture edit ended its logical history-quota
patch before archive. The final fixture preserves that exhausted-quota coverage;
no runtime code changed after the first code batch. The pre-push privacy check runs
normally; no bypass, force push, new PR, merge or push to `main`.

**Not verified:** real provider completion/visibility timing, physical power loss
and filesystem durability, host service confinement, terminal/phone prompts,
recipient-program presentation and the existing real-account owner checklist.
The 15-minute policy is the brief's chosen quiet period, not a measured bound for
the owner's server; the deliberately later-completing fixture proves duplicate
warnings instead of silent duplicate success. No model session, real account,
host installation, screenshot or Minecraft/Gradle run applies to this round.

**JUDGMENT-CALL:** the required quiet period is 15 minutes. The shared fixed
safety cushion is 4 MiB, with separately sized holds (`16 × serialized bytes +
128 KiB` per recovery record, including the original operation for settlement).
This replaces guessing which writer gets a different floor. Changing the cushion
or quiet period later is a constant/policy change, without history migration.
The bounded confirmation reply retains the first 100 IDs and gives a count and
existing pending-page action for the rest; returning every ID would hit the
existing result-size cap after a successful large recovery.

**PLAN-GAP:** the brief requires bounded restore records but does not spell out
the previously unbounded confirmation reply; its optional `unknown_more` count
and existing pending pages close that mechanical gap. No unrelated feature was
added. **Open questions:** none added; the owner's existing qualification checks
remain. **Large scratch files:** no file over 500 MiB remains in `.work/`.


## Review fixes, round 19

**Done:** implements `briefs/19-review-fixes-19.md`, addressing both findings in
[SECURITY-REVIEW-11.md](SECURITY-REVIEW-11.md), reviewed head `88c83ef7`.
The owner's previously local `795c41ce` (review and brief) went with the first
code push. Implementation commits: `ef16da8d`, `f9f39f03`, `8b889abd`, `fe0c3d01`
and `e77b1c40d577a8262700f3c996f4cfcb0a791575` (last code/test change).

- **Blocking — repair traffic exhausting recovery:** `engine.py` reuses the
  retained unresolved repair for the same original operation and local stage,
  including reserved/submitting attempts. Repeating the repair is the explicit
  read-then-settle action: `mail/adapter.py` searches Sent by the original send's
  Message-ID, or reads flags from the exact reply reference with UIDVALIDITY and
  Message-ID checks. Presence marks that repair done and updates the original
  stage; a successful absent check marks the repair failed, leaving the original
  stage eligible for a later request. A transport failure or inconclusive/refused
  check returns the existing attempt unchanged, without allocation or writes.
  Settlement itself does not APPEND, STORE or submit SMTP. `operation_status`
  remains read-only. `mail/definitions.py`, the generated Mail tool JSON and
  `docs/control/TOOLS.md` describe this behavior.
- **Blocking — cancellation capacity:** `engine.py` exempts cancellation from
  request-wide history admission; `storage.py` exempts its durable write from
  the SQLite quota. `retention.py` gives cancellation its own 4 MiB physical
  reserve. Ordinary work leaves 64 MiB; ordinary recovery leaves 20 MiB (16 MiB
  restore plus 4 MiB cancel); restore/archive leave cancel's 4 MiB; cancellation
  leaves restore's 16 MiB. Repairs, acknowledgements, expiry and owner
  maintenance cannot consume cancel's reserve. This protects tool traffic;
  external disk exhaustion and actual I/O failures still require freeing space.
- **Should-fix — permanent journal RAM growth:** `storage.py` verifies one line
  at a time and rebuilds an untrusted, disposable `journal-index.sqlite` outside
  the backup tree. Record sequence/hash/offset and latest compact operation
  evidence live on disk, with a 1 MiB SQLite index page cache. The resident journal
  state is its sequence/head; `events` is now a lazy disk-backed sequence, so
  existing crash/archive assertions still inspect the same records without
  retaining them. Restore reads latest evidence from the disk index, audit
  verification compares hashes, and production log pagination streams with
  bounded page storage. Old or corrupt derived indexes are discarded on restart;
  only the unchanged permanent journal is authority. `engine.py` and `storage.py`
  also stream retained operation scans (startup, pending, prepare reuse, expiry
  and repair lookup), avoiding a transient list of all completed operations.
  `control/README.md` documents the lifecycle and recovery semantics. Archive
  needs no command or format change: its existing lazy reads still retain the
  entire permanent record.

**Tests by name — additions only; no earlier tests changed, weakened, skipped or
deleted:**

`control/mail_tests/test_review_fixes_19.py`, class `Recovery19`:

- `test_review19_38_uncertain_repairs_with_archives_keep_one_and_cancel_works`
- `test_review19_unknown_sent_repair_settles_done_by_original_message_id_after_restart`
- `test_review19_unknown_sent_repair_proved_absent_fails_then_allows_new_attempt`
- `test_review19_each_stage_reuses_reserved_running_unknown_without_writes_when_inconclusive`
- `test_review19_two_failed_stages_each_keep_their_own_single_unresolved_repair`
- `test_review19_answered_evidence_uses_readonly_pinned_reference_and_flags`
- `test_review19_cancel_works_above_history_cap_and_other_paths_leave_its_physical_room`

`control/tests/test_journal_streaming.py`, class `JournalStreaming`:

- `test_review19_startup_retained_and_peak_memory_bounded_for_1000_and_10000_unique_operations`
  includes both journal records and retained completed SQLite operation rows,
  and measures startup, lazy historical iteration, verified audit iteration and
  paged log reads. Each population must stay below fixed 512 KiB retained / 2 MiB
  peak Python allocations. The unrelated fixed 6 MiB boundary-file read is
  excluded by reusing the existing Boundary instance; all Store startup runs.
- `test_review19_stream_verification_detects_middle_corruption_torn_tail_and_whole_suffix_truncation`
- `test_review19_large_restart_rebuilds_untrusted_index_detects_restore_and_refuses_replay`
- `test_review19_streamed_log_pages_keep_all_entries_and_refuse_cursor_after_change`

**Verified — local, before every push:**

```text
python3 control/generate.py --check
Generated artifacts match definitions
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py
Python syntax OK: 107 files
Ran 86 tests; OK
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest test_operations test_record test_crashes test_approval_questions test_strict_json test_boundary test_boundary_exact test_ingress_bounds test_journal_closed test_policy_sources test_archive test_journal_capacity test_journal_streaming
Ran 79 tests; OK
Record growth: tiny send=4078 bytes; maximum body + 25 MiB send=4078 bytes; 6 state/stage records, mean=679.7 bytes per record including commit
Record growth: typical three-recipient send=5560 bytes across 8 state/stage records
```

The two required suites above were repeated before each push; the initial push
had the first streaming test version, and the corrective code push and report
push include its retained-row coverage. Additional commands:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 -m unittest test_review_fixes_19
Ran 7 tests; OK
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest test_journal_streaming
Ran 4 tests; OK
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control/boundary:control:.work/round10/vendor python3 -m unittest test_native
Ran 16 tests; OK
```

The Mac harness supplies disposable generated policy fixtures and simulated root
ownership; Linux workflows provide real installed ownership and container tests.
Initial local fixture failures (metadata-only FETCH handling and replay returning
the recorded cancelled state) were corrected; no product assertion was removed.
The first memory probe included the unrelated fixed 6 MiB policy read, so its
scope was corrected as explained above. The final memory test also includes
retained SQLite operations: representative `(retained, peak)` bytes were
`(34080, 193152)` at 1,000 operations and `(23639, 181705)` at 10,000.
These are Python allocations, not whole-process RSS; the index cache is separately
fixed at 1 MiB, and other SQLite caches retain their existing fixed limits.

**Verified — baseline:** exported `88c83ef7` under `.work/round19/baseline` and
overlaid only the new tests. Commands used the same unittest names above with
`PYTHONPATH=.work/round19/baseline/control:.work/round19/baseline/control/mail_tests:.work/round10/vendor`
and the corresponding `control/tests` path. The seven recovery tests printed
`FAILED (failures=7)`: new ids instead of reuse/settlement, growing unresolved
attempts, and cancellation returning `storage_limit`. The four streaming tests
printed `FAILED (failures=1, errors=1)`: the old journal retained about 2.35 MB of
Python objects already at 1,000 operations, above the fixed 512 KiB bound. The
error is the new disposable-index test encountering no `latest` table in the
old implementation; it is not behavior evidence. Corruption/truncation and
restore/replay invariants retain their earlier assertions and pass now.

**Verified — Linux workflows at the last code/test commit**
`e77b1c40d577a8262700f3c996f4cfcb0a791575`:

| Workflow | Exact-code-head runs | Result |
| --- | --- | --- |
| Control Mail | [42451163980 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42451163980/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42451163980/attempts/2) | Both PASS: 109 shared-base tests + 207 Mail tests; `Control base suite PASS`, `Control Mail suite PASS` and fixture isolation confirmed. |
| Control base | [42451163952 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42451163952/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42451163952/attempts/2) | Both PASS: 109 tests; generated artifacts match. Linux journal memory at 1k/10k operations: `(11495, 161982)` / `(10906, 161267)` retained/peak bytes in the first pass. |
| Control boundary | [42451163968 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42451163968/attempts/1) | PASS: 16 native fixture tests, installed boundary precondition, both confinement modes (127 attacks each), `SOURCES_OK`, `LAUNCHER_POLICY_SOURCES_OK`, `ISOLATION_OK`. |

Both second passes use `gh run rerun` on those same automatic pull-request run
IDs. Any later commit changes only files under `reviews/`; final report-inclusive
head run IDs and both passes are recorded in draft PR #9's body. No manual
workflow dispatch, new PR, merge, force push or push to main occurred.

**Push discipline:** one initial code push included the owner's local commit. A
second code push was necessary after finding the remaining transient startup
operation list: it adds streaming scans and strengthens the memory fixture with
retained SQLite rows. The report is the third and final push. This produced
nine automatic workflow IDs, rather than the intended six; no push was made
just to obtain a second pass. The ordinary pre-push hook was never bypassed.
The initial-head runs are recorded as historical only below; final code and
final PR-head evidence use their exact own heads.

| Initial code head `fe0c3d01` | Run | Result |
| --- | --- | --- |
| Control base | [42450966466](https://github.com/Ares-Empire/AresOS/actions/runs/42450966466) | PASS; superseded by the retained-row correction. |
| Control Mail | [42450966308](https://github.com/Ares-Empire/AresOS/actions/runs/42450966308) | Cancelled on superseding push; not passing evidence. |
| Control boundary | [42450966329](https://github.com/Ares-Empire/AresOS/actions/runs/42450966329) | Cancelled on superseding push; not passing evidence. |

**Not verified:** real providers, real delivery or accounts, delayed server Sent
copies, physical power-loss/controller durability, and native owner approval
presentation. No UI changed; screenshots are not applicable. A successful absent
Sent check proves absence at that read, not that a delayed copy cannot arrive
later; every later Sent repair still searches before APPEND. There is no SMTP
retry. Permanent journal/index/export disk use and linear startup verification
time still grow with retained history; this round bounds resident journal memory.

**JUDGMENT-CALL:** repeated `operation_repair` is the proof-only settlement path,
because it is already an explicit change action and reuses the stage's attempt.
A read-only status call does not silently mutate history; a separate tool would
add a recovery surface without resolving any additional state. Changing this
later affects tool descriptions and dispatch, not journal format or mailbox
migration. The disk index was chosen over keeping every operation/hash in a
Python map, which would still grow indefinitely; it is rebuildable and has no
backup/restore authority.

**PLAN-GAP:** none beyond the stated storage/largest-record and real-provider
limits. **Open questions:** none new; the existing owner qualification checks
above remain. Final `.work/` scan: no regular file over 500,000,000 bytes; no
large downloads or extracted images were created in this round. No Gradle daemon
or container was started locally.

## Review fixes, round 18

**Done:** implements `briefs/19-review-fixes-18.md`, closing the blocking repair/
restore lockout and both should-fixes in
[SECURITY-REVIEW-10.md](SECURITY-REVIEW-10.md), reviewed head `eead1eb5`.
The first push includes the lead's previously local `e767f1d1` together with three
complete implementation commits: `d3209179` (repairs and owner recovery),
`0278e621` (journal accounting), and `b77154cd8874ff7c46b38111c6e3b0a91c040d7b`
(cache/login removal; last code/test change).

- `control/aresos_control/mail/adapter.py` now checks repair eligibility separately
  from acting: only accepted sends/mailto unsubscribe with a composition and final
  DATA acceptance qualify; only `sent_copy` and `answered_flag` qualify; an
  explicitly failed stage is required. `done` and answered `not_needed` are reads.
  `engine.py` performs that check before allocating any repair id or writing any
  transaction. A completed stage returns its existing successful repair when
  retained, otherwise the original operation, plus the current original status.
  Repeated repair writes no SQLite, journal or audit data and still works at full
  quota. Invalid repairs refuse before recording. Eligible repairs retain their
  durable reserved/submitting/outcome protocol and never invoke SMTP.
- `engine.py`, `storage.py`, `retention.py` and `archive.py` give owner restore
  confirmation and archival a quota-exempt maintenance path. Ordinary calls,
  repairs, cancellation, acknowledgement, expiry and restart recovery cannot
  consume it. Their history admission still stops at their respective limits.
  Ordinary work leaves 64 MiB of physical disk headroom; recovery calls now leave
  16 MiB for owner maintenance. Owner confirmation/archival may use that last
  reserve and still check their actual conservative disk requirement before a
  journal fence. Restore can confirm even when the configured working-history
  quota is already exceeded, then archive without the former deadlock. This is
  separate logical capacity, not a claim that finite physical storage is unlimited.
- `storage.py` now applies the 1 GiB working-history cap to allocated SQLite pages
  only (`history_bytes` returned by archive has this meaning). The independent
  journal has separate physical capacity accounting through the existing
  per-write disk checks; it and private exports remain on disk outside that cap.
  Archive exports and compacts SQLite exactly as before, so the retained journal
  cannot permanently block ordinary work at the SQLite admission threshold.
  No journal bytes, hash links, commit markers or replay evidence are discarded;
  no format migration is needed. The owner runs the same command above and keeps
  the independent record intact. This uses the brief's separate-accounting option;
  rotating closed segments was rejected because it would add checkpoint/backup
  compatibility and crash-atomic migration work. The remaining cost is physical
  disk growth of the independent record/exports; actual disk shortage still needs
  the owner to provide space, and an owner archive is not a journal deletion tool.
- `control/aresos_control/boundary.py` no longer touches the remote-settings cache
  or owner home. `control/boundary/launch.py` no longer runs `auth status` or limits
  subscriptions/authentication types. Generated-file equality, managed drop-in
  checks, environment clearing, fixed CLI arguments, pinned executable hashes,
  plugin check and both seccomp canaries remain. `control/boundary/check.py`
  expects an existing cache to permit launch and retains every drop-in check.
  `control/boundary/native.py` removes the synthetic bypass of the deleted login
  check; its generated policy fixture remains. `control/boundary/test_native.py`
  now checks that the launcher stays unchanged, retaining all policy/restoration
  assertions. No other brief-18b path changes and no managed-settings slimming.

**Named regressions (new plain-Python tests):**

| Test | Evidence |
| --- | --- |
| `Recovery18.test_review18_completed_repairs_leave_journal_sqlite_audit_and_sizes_unchanged_at_full_capacity` | Completed initial send and successful repaired stage: 100 repeated calls at zero history quota preserve complete snapshots, file sizes and audit count; restart preserves the result. |
| `Recovery18.test_review18_ineligible_repairs_refuse_before_recording_or_adapter_action` | Wrong action, absent DATA acceptance, unknown/missing/unfinished stage and reserved original refuse without growth or local-stage execution. |
| `Recovery18.test_review18_review_sequence_redundant_repairs_cancel_and_preceding_backup_restore` | Completed send, pending approval, preceding SQLite backup and 100 redundant repairs at the review's current-size + 1 MiB + 1 byte cap: no growth; cancel and restore confirm succeed, archive remains available and replay refuses. |
| `Recovery18.test_review18_restore_confirms_above_every_quota_and_can_archive_afterward` | Real older-store restore with zero history quota and only the physical owner reserve confirms, archives and restarts; prior approval cannot submit. |
| `Recovery18.test_review18_repairs_and_ordinary_recovery_cannot_consume_restore_room` | Repair and ordinary recovery hit their quota before a fence; physical owner reserve cannot be consumed by repair. |
| `JournalCapacity.test_review18_archive_cycle_frees_capacity_despite_larger_independent_journal_and_old_restore_replay` | 800 completed free-work events exhaust reduced SQLite capacity; archive restores ordinary work while the unchanged journal alone exceeds the cap. Older backup still locks; confirmation invalidates old ids; no second delivery, valid full chain and restart. |
| `PolicySources.test_review18_private_home_and_remote_cache_are_never_traversed` | Permission-error private home does not block service admission; cache and dangling cache symlink also do not block. |
| `PolicySources.test_review18_launcher_has_no_auth_restriction_and_keeps_boundary_and_canaries` | Launcher runs exactly two canaries, supplies fixed arguments and performs no authentication preflight; failed managed-policy check never launches. |

New files: `control/mail_tests/test_review_fixes_18.py` and
`control/tests/test_journal_capacity.py`. Existing test changes forced by the new
rules are named here: `PlainQuestions12.test_round12_onboarding_and_mail_repair_questions_first`
and `Recovery17.test_review17_free_limit_preserves_cancel_both_ack_paths_repair_and_expiry`
now mark synthetic repair stages explicitly failed; all their assertions remain.
`Outcomes.test_dropped_final_answer_is_unknown_and_never_retried` now asserts an
immediate `refused` response instead of a newly recorded failed repair; its no-
second-arrival assertion remains. The two removed round-17 expectations in
`control/tests/test_policy_sources.py` are
`test_review17_remote_cache_and_any_symlink_refuse` and
`test_review17_launcher_refuses_unknown_or_remote_eligible_authentication`;
the two round-18 tests above replace them. Native fixture and installed-launcher
expectations change only for the two deleted checks, as described above. No other
earlier test assertion is weakened, skipped or deleted. Round 17's report text and
policy-source table above/below have been updated to name both removals.

**Verified — local, before the code push (and repeated before the report push):**

```text
python3 control/generate.py --check
Generated artifacts match definitions
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py
Python syntax OK: 105 files
Ran 79 tests; OK
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest test_operations test_record test_crashes test_approval_questions test_strict_json test_boundary test_boundary_exact test_ingress_bounds test_journal_closed test_policy_sources test_archive test_journal_capacity
Ran 75 tests; OK
Record growth: tiny send=4078 bytes; maximum body + 25 MiB send=4078 bytes; 6 state/stage records, mean=679.7 bytes per record including commit
Record growth: typical three-recipient send=5560 bytes across 8 state/stage records
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control/boundary:control:.work/round10/vendor python3 -m unittest test_native
Ran 16 tests; OK
```

The non-root Mac harness models root ownership for disposable generated policy
files; Linux workflows supply the actual root ownership and socket evidence.
One initial local syntax scan overlapped the native fixture's temporary Python
source and returned `FileNotFoundError` when that fixture removed its directory;
the sequential rerun above passes. No test or product check was changed for this.
Initial new-test fixture failures were corrected before pushing (synthetic local
stage support and owner archive disk admission); no failed CI push was used.

**Verified — failing baseline:** isolated source export of reviewed `eead1eb5`
under `.work/round18/baseline`, overlaid with only the new tests. The five Mail
tests returned `FAILED (failures=6, errors=2)`; the new journal test plus the two
replacement policy tests returned `FAILED (failures=1, errors=2)` across three
tests. Failures expose redundant repair writes/quota refusal, ineligible repair
recording, blocked restore, archive failing to restore ordinary capacity, private
home permission refusal and the launcher auth restriction. Current source passes
these same tests. The initial Mail overlay's two errors were the old module lacking the newly
introduced `RESTORE_RESERVE` constant. A second baseline run supplies only that
16 MiB test constant (unused by the old product): all five tests still fail,
`FAILED (failures=7, errors=1)`; restore returns `storage_limit`, and repair uses
the physical reserve instead of refusing (the remaining error is the test
expecting an error result from that accepted call). These are failing-baseline
evidence, not passing-test claims.
A direct baseline probe reproduces the review sequence with production engine/
SQLite/journal logic and synthetic transports: `Redundant repair: True history
bytes added: 14819`, `Cancel: storage_limit`, `control_restore_confirm:
storage_limit`, `control_archive: restore_required`. The current-head named
sequence regression instead completes cancellation, confirmation and archival.

**Verified — last code/test commit** `b77154cd8874ff7c46b38111c6e3b0a91c040d7b`:

| Workflow | Run and attempts | Exact output |
| --- | --- | --- |
| Control base | [42446521836 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42446521836/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42446521836/attempts/2) | Both PASS: `Generated artifacts match definitions`, `Ran 105 tests`, `OK`, `Control base suite PASS`. |
| Control Mail | [42446521874 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42446521874/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42446521874/attempts/2) | Both PASS: `Ran 105 tests`, `Control base suite PASS`; `Mail fixture isolation PASS: internal network, one test network, no published ports`; `Ran 200 tests`, `OK`, `Control Mail suite PASS`. |
| Control boundary | [42446521817 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42446521817/attempts/1) | PASS: `Ran 16 tests`, `Installed boundary precondition PASS`; `NATIVE_BOUNDARY_OK` in both modes, 127 attacks each, AF_UNIX/AF_VSOCK EPERM, zero hostile arrivals and unchanged approval mount tree; `SOURCES_OK`, `LAUNCHER_POLICY_SOURCES_OK`, `ISOLATION_OK`. |

Both second passes use `gh run rerun` on these same run ids; no push was made to
obtain another pass. Any later commit changes only files under `reviews/`. The PR
body records the final report-inclusive head, both base/Mail passes on that exact
head and the boundary workflow result.

**Not verified:** real providers/accounts, live organization policy, physical
power-loss durability, terminal/phone approval UI, recipient-program presentation
and model-driven tasks. No host installation, Minecraft/Gradle, OS/mod/workflow
change or UI screenshot applies to this round. The existing real-account owner
checks remain.

**JUDGMENT-CALL:** separate journal accounting and quota-exempt owner maintenance
use the brief's approved options; no new decision is requested. Rotating the
journal later would require a checkpoint-format migration with older-backup and
crash tests. **PLAN-GAP:** none added; physical disk capacity is finite and the
journal/export space must be retained/provided by the owner. **Open questions:**
none new; existing account/approval/presentation qualification remains.

**Workspace hygiene:** no `.work/` file exceeds 500 MB. Only this worktree and
`pkg/19-mail` changed; no protected path or workflow changed. No new PR, merge or
force push. PR #9 remains draft.

## Review fixes, round 17

**Done — read:** implements `briefs/19-review-fixes-17.md` for both findings in
[SECURITY-REVIEW-9.md](SECURITY-REVIEW-9.md), reviewed head `9278b000`.
The lead's previously unpushed `f8744ffe` was included in the first push.
Code commits: `17df2398` (managed sources), `5f090543` (native launcher regressions),
`c22831ad` (recovery/archive), and
`a5516bddc485d9fe6b168f69103a52f493433b80` (native fixture policy; last code/test change).
This section supersedes round 16's statement that owner archive tooling is absent.

### Finding 1: every managed policy source

`control/aresos_control/boundary.py` checks the drop-in directory as well as the
existing exact generated settings/MCP files. The directory must be absent or a
real, root-owned directory without group/world write permission and with zero
entries. The error names the first unexpected entry, including `99-open.json`;
non-JSON files, hidden entries and subdirectories also refuse. Component-wise
`O_NOFOLLOW` opens reject symlinked parents and directories, including dangling
links. The main-file checks retain their earlier diagnostics and assertions.

**Round-18 update, named removals:** `control/aresos_control/boundary.py` no
longer checks `~/.claude/remote-settings.json` or traverses the owner's home.
`control/boundary/launch.py` no longer calls `auth status` or restricts subscription
and authentication types. Its complete generated-file/drop-in check remains.
`control/boundary/check.py` now asserts that an existing remote cache permits
launch; all empty/nonempty/symlink drop-in assertions remain.
`control/boundary/native.py` still installs and restores the generated synthetic
policy, but no longer edits the launcher to omit the removed login check.
`control/boundary/test_native.py` now asserts that the launcher stays unchanged
through the fixture and retains its exact-policy, sandbox, grants and restoration
assertions. These changes implement decision 24; managed-settings slimming is not
part of this round. No production fixture switch or fixture-path option exists.

**read — 2026-11-08, end to end:** [Managed settings](https://code.claude.com/docs/en/managed-settings),
[Settings](https://code.claude.com/docs/en/settings), and
[Server-managed settings](https://code.claude.com/docs/en/server-managed-settings).
Also read the source-location/exclusive-control portions of
[Managed MCP](https://code.claude.com/docs/en/managed-mcp).
The Linux policy-source inventory and its disposition are:

| Source (read, date above) | Check or disposition |
| --- | --- |
| `/etc/claude-code/managed-settings.json` | Exact generated canonical JSON, protected root-owned ancestors/file. |
| `/etc/claude-code/managed-settings.d/*.json` | Main file precedes alphabetically ordered drop-ins; all directory entries now refuse. |
| `/etc/claude-code/managed-mcp.json` | Separate exclusive server source; exact generated JSON and protected path. |
| `managedMcpServers` in managed settings | Absent from the generated object; adding it refuses equality. |
| Remote policy from the organization or a signed-in gateway; `~/.claude/remote-settings.json` cache | Round 18 removes cache admission and the subscription/login restriction under decision 24. The service never traverses the owner home for this cache; remote policy is outside the generated local-file check. |
| `policyHelper` executable/output | Absent from the generated settings, so configuring a helper refuses. |
| SDK/embedding-host parent settings | Fixed terminal launcher supplies no host settings; generated policy does not opt into parent merging. |
| macOS managed preferences; Windows HKLM/HKCU and WSL inheritance | Not applicable to the native Linux deployment; this Mac is only the development host. |

The source mechanisms, helper and parent behavior above are documented in
[Managed settings](https://code.claude.com/docs/en/managed-settings#how-claude-code-combines-managed-sources);
MCP file handling is documented separately in
[Managed MCP](https://code.claude.com/docs/en/managed-mcp#exclusive-control-with-managed-mcp-json).

**read — 2026-11-08:** user `~/.claude/settings.json`, project
`.claude/settings.json`, local `.claude/settings.local.json` (including the Git-root
local file), and session `--settings` are additional settings scopes.
`CLAUDE_CONFIG_DIR` relocates user state; `~/.claude.json` also contains global/MCP
state. See [Settings](https://code.claude.com/docs/en/settings).
**implementation:** the static launcher clears inherited environment/arguments,
fixes HOME/working directory and starts with `--setting-sources ''`, supplying no
`--settings`. Managed-only locks and the existing round-16 caller-write denials
remain. `managed-hooks.json` is a draft companion, not another independently
loaded policy source; any actual `hooks` entry would differ from the generated
policy. Arbitrary SDK/IDE/Desktop/headless launches are not the supported central
session.

**read — 2026-11-08:** remote delivery is documented for Team/Enterprise settings;
eligible credentials include their saved OAuth logins, OAuth tokens, direct API
keys and specified profiles; gateways have their own delivery. The cache can
apply before a fresh fetch. Noninteractive settings requiring approval can apply
without being cached. See
[Server-managed settings](https://code.claude.com/docs/en/server-managed-settings#platform-availability).
**implementation, updated in round 18:** the subscription-only login restriction
and service remote-cache refusal described by round 17 were removed under
decision 24. The static launcher's existing environment clearing, fixed arguments,
managed-file/drop-in checks, native hashes and canaries remain. No real account or
remote policy server was contacted. This report no longer claims remote-policy
exclusion through subscription status or cache absence.

**Design-ready:** decision 22 will later add vetted additions, possibly as drop-ins;
then the check must compute the merged policy in Claude Code's documented order
and compare it with the generated policy plus the vetted additions.

### Finding 2: usable recovery capacity and owner archive

**Historical round-17 accounting below is superseded by round 18:** the current
cap covers SQLite only; owner restore/archival bypass it, and ordinary recovery
retains 16 MiB of physical space for owner maintenance.

`control/aresos_control/retention.py`, `storage.py` and `engine.py` reserve 64 MiB
of the 1 GiB combined SQLite/independent-history quota for recovery. Ordinary
requests also retain their existing 128 MiB request headroom (initial admission
therefore stops above 832 MiB); each ordinary durable write must still leave the
64 MiB recovery reserve. Cancel, both notice-ack paths, local repair, owner restore
confirmation, expiry and restart-to-unknown writes may use that reserve. Recovery
requests use 1 MiB admission headroom plus each write's actual conservative cost.
They can also use the physical 64 MiB disk reserve that ordinary work must leave.
Unrelated opportunistic expiry does not run ahead of a recovery request. Reads
remain available. Actual disk exhaustion and the recovery hard quota still refuse
before the journal fence; the reserve is finite, not a promise of unlimited disk.

Repeated `mail_prepare_send` reuses the exact existing approval/id/expiry while
that same composition remains reserved, unexpired and in the current generation.
The normal preparation/role/MIME checks run first. Changed compositions, cancelled
operations, expiry or a new generation do not reuse it. Reusing preserves the
question-first presentation after storage canonicalization and writes no history,
even at the ordinary admission limit. This was chosen over a pending-count cap
because rereading one pending approval needs no new operation. Repeated notice
acknowledgement also avoids redundant writes.

New `control/aresos_control/archive.py` implements the explicit owner-only
`control_archive` action. `definitions.py` owns its schema; generated CLI help and
`docs/control/TOOLS.md` describe it. `protocol.py` gives this maintenance call a
600-second response timeout. The existing peer-credential/admin routing is reused;
the action is absent from MCP catalogues and denied over `act.sock`.

The owner supplies a past Unix-seconds cutoff and the exact confirmation string.
The service creates a private `0600` JSONL file in its independent evidence
`archives/` directory, exports eligible old SQLite events and up to 100 old finished
operation snapshots, fsyncs the file and directories, and records its SHA-256 and
manifest durably before pruning the exported rows and running SQLite `VACUUM`.
The returned path can be read with `sudo cat`; ordinary assistant tools cannot read
that service-private directory. Repeat for further batches of finished operations.
The export contains private audit content and references, not a standalone backup
of mailbox/blob bytes. Unused blob expiry retains its existing rules.

Open operations, the original operations needed by open repairs, unacknowledged
operation/filing notices, unresolved filing intents and their location pages stay
in the live store. Finished-operation tombstones identify the independent sequence
that archived them. The entire independent journal, its hash chain and commit
markers remain; archival never resets the restore fence or changes generation.
Restoring older SQLite still locks access until the owner confirms and invalidates
old approvals. Missing archived operations cannot be submitted again. Archive may
temporarily exceed the history quota only after its export is durable, so it can
recover an older installation already at quota; disk checks and failed-journal
latching remain. Interrupted export leaves source rows intact; interruption later
leaves either exported source rows or their durable archival tombstones.

### Named regressions and scope

| Test | What it proves |
| --- | --- |
| `PolicySources.test_review17_drop_in_reproduction_names_file_and_all_entries_refuse` | Exact review payload names `99-open.json`; any entry refuses; empty and absent directories pass. |
| `PolicySources.test_review17_drop_in_symlink_and_unsafe_directory_refuse` | Real/dangling symlink, wrong ownership, group/world write each refuse. |
| `ExactBoundary.test_review16_ancestor_owner_group_world_and_symlink_each_refuse` (unchanged) | Symlinked main-file parent and every unsafe ancestor still refuse, with existing assertions. |
| `PolicySources.test_review18_private_home_and_remote_cache_are_never_traversed` | Replaces the removed round-17 remote-cache refusal expectation; private home, cache and cache symlink do not block admission. |
| `PolicySources.test_review18_launcher_has_no_auth_restriction_and_keeps_boundary_and_canaries` | Replaces the removed round-17 subscription restriction; both canaries and fixed CLI arguments remain, and failed managed checks never launch. |
| `Recovery17.test_review17_unchanged_prepare_reuses_exact_approval_and_no_history_even_at_free_limit` | Repetition/restart reuse; changed/cancelled/expired preparations do not. |
| `Recovery17.test_review17_free_limit_preserves_cancel_both_ack_paths_repair_and_expiry` | Ordinary work refuses without a write; recovery succeeds; SMTP is forbidden in the recovery probe. |
| `Recovery17.test_review17_free_limit_and_physical_reserve_preserve_owner_restore_confirmation` | Real older-SQLite restore confirms at the free-work and physical-reserve boundary; old approval remains unusable. |
| `Recovery17.test_review17_free_writes_cannot_consume_recovery_bytes_and_recovery_still_obeys_hard_cap` | Reserved bytes are inaccessible to ordinary writes; recovery still refuses before a fence at its hard cap. |
| `Archive.test_review17_archive_is_owner_only_explicit_and_not_offered_to_claude` | Owner routing, confirmation and past cutoff. |
| `Archive.test_review17_archive_exports_then_compacts_keeps_open_notices_and_journal_valid_after_restart` | Private export/hash, measurable compaction, open/notices preserved, complete journal and no redelivery. |
| `Archive.test_review17_archive_remains_available_over_old_quota_and_restore_stays_detectable` | Archive at an already-full old quota, older-backup detection and invalidated approvals. |
| `Archive.test_review17_archive_export_failure_never_removes_source_rows` | Injected fsync failure leaves source DB/journal unchanged. |
| `Archive.test_review17_archive_preserves_unresolved_filing_and_open_repair_dependencies` | Unresolved warning/location rows and an uncertain repair's original stay live. |
| `Archive.test_review17_archive_kill_at_every_durable_boundary_restarts_without_corruption_or_resubmission` | SIGKILL at export, four journal/SQLite stages, pruning and vacuum; valid restart and one original delivery. |
| `NativePolicyFixture.test_review17_synthetic_policy_is_exact_and_sources_restore_on_session_exception` | Synthetic expected/installed policy agree; no sandbox field changes; both root fixture sources restore after an exception. |
| `Integration.test_review17_archive_uses_admin_socket_and_installed_owner_cli` | Real Linux peer credentials, denied owner over both sockets, privileged installed CLI, private export, live pending operation and no replay. |

New base test files are `control/tests/test_policy_sources.py`, `test_archive.py`
and `archive_worker.py`; the only existing base test edit is the added integration
method above. Every earlier assertion is kept. `control/mail_tests/test_review_fixes_17.py`
adds the four Mail quota/preparation tests. Native source checks are additions to
`control/boundary/check.py`; the existing native session fixture is adapted as
described above. No earlier assertion is changed, skipped or deleted.

### Verification

**run — initial code batch** `c22831ad`: [base 42441710937](https://github.com/Ares-Empire/AresOS/actions/runs/42441710937)
passed (`Ran 104 tests`, `Control base suite PASS`).
[Boundary 42441710940](https://github.com/Ares-Empire/AresOS/actions/runs/42441710940)
failed: its existing native session adds a synthetic `env` entry, and the new
launcher correctly returned `generated policy differs at env`; its baseline
assertion then failed. [Mail 42441711002](https://github.com/Ares-Empire/AresOS/actions/runs/42441711002)
was cancelled by the next push's workflow concurrency rule, so no Mail pass is
claimed for that batch. The correction in `a5516bdd` changes only the native test
fixture and adds restoration coverage, as described above. Production checks and
every earlier native assertion remain.

**run — last code/test commit** `a5516bddc485d9fe6b168f69103a52f493433b80`:

| Workflow | Run and attempts | Result / exact evidence |
| --- | --- | --- |
| Control base | [42442191164 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42442191164/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42442191164/attempts/2) | Both PASS: `Generated artifacts match definitions`, `Ran 104 tests`, `OK`, `Control base suite PASS`. Attempt 1 log lines 286/393–399; attempt 2 uploaded `results.txt` lines 126/233–239. |
| Control Mail | [42442191282 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42442191282/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42442191282/attempts/2) | Both PASS: `Ran 104 tests`, `Control base suite PASS`, `Mail fixture isolation PASS: internal network, one test network, no published ports`; `Ran 195 tests`, `OK`, `Control Mail suite PASS`. Attempt 1 log lines 394–400/468/768–774; attempt 2 lines 394–400/469/769–775. |
| Control boundary | [42442191370 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42442191370/attempts/1) | PASS: 16 native fixture unit tests; `Installed boundary precondition PASS`; `NATIVE_BOUNDARY_OK` in both modes (127 attacks, AF_UNIX/AF_VSOCK EPERM, unchanged mount tree, zero hostile arrivals); `SOURCES_OK`; `LAUNCHER_POLICY_SOURCES_OK`; `ISOLATION_OK`. Log lines 877/880, 1157/1965, 1248, 1654 and 2451. |

The second base/Mail passes use `gh run rerun` on these same IDs. The run API
identifies the exact code/test head above; PR jobs may check out a synthetic merge
ref. No push was used merely to obtain a second pass.


**run — local checks before the code push and repeated before the report push:**

```text
python3 control/generate.py --check
Generated artifacts match definitions
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py
Python syntax OK: 103 files; Ran 74 tests; OK
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest test_operations test_record test_crashes test_approval_questions test_strict_json test_boundary test_boundary_exact test_ingress_bounds test_journal_closed test_policy_sources test_archive
Ran 74 tests; OK
Record growth: tiny send=4078 bytes; maximum body + 25 MiB send=4078 bytes; 6 state/stage records, mean=679.7 bytes per record including commit
Record growth: typical three-recipient send=5560 bytes across 8 state/stage records
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control/boundary:control:.work/round10/vendor python3 -m unittest test_native
Ran 16 tests; OK
```

The Mac harness models root ownership only for disposable generated fixtures,
including their empty drop-in directory, and maps the remote-cache constant inside
this worktree. Linux CI provides the real ownership/launcher/socket evidence.
Early local failures exposed fixture ownership modeling, question ordering on a
reused stored approval, and the earlier main-parent diagnostic; those were fixed.
The new interrupted-archive test was corrected to respect the existing replay
contract: an already-done operation can return its done status; delivery count
must remain unchanged. No earlier test changed for these corrections.

**run — baseline regression overlay:** new plain tests against an isolated copy of
reviewed `9278b000` in `.work/round17/baseline` fail (Mail: 4 tests, 4 errors for the
missing recovery API; base/source/archive: 10 tests, 11 failing assertions and 5
errors). Drop-in refusals and archive availability fail on that head; missing new
APIs also account for errors. This is failing-baseline evidence, not a passing test
claim. The current source passes the same new plain tests in the local suites above.
A direct probe on that overlay additionally prints: `five repeated prepares added
5 journal events and 5 distinct operation ids`; at its reduced ordinary threshold,
`operation_cancel`, `notice_ack` and `operation_repair` each return `storage_limit`.

Any later commit changes only files under `reviews/`. The PR body records the
final report-inclusive head's Mail/base runs and both attempts, plus boundary
success; second passes use `gh run rerun` on the same IDs, never an extra push.

**Not verified / assumed:** no real account, live organization/gateway policy,
phone/terminal approval UI, recipient program or model-driven task session was
used. Existing owner qualification remains. Native CLI tests use offline synthetic
fixtures without a model; no host installation, Minecraft or Gradle ran. No UI
change or screenshot claim applies.

**JUDGMENT-CALL:** refusing unknown/additional policy, reserving recovery capacity
and requiring explicit owner archival implement the approved safety rule. There
is no new owner decision. The archive retains the independent fence instead of
rotating it, preserving the existing restore guarantees; it compacts SQLite only.
Independent metadata and private exports therefore still occupy disk, and the
owner must keep sufficient space for maintenance. Rotating or dropping that fence
was rejected here because it would require a checkpoint-format migration and
compatibility tests against older backups; that is the cost of changing this
choice later. **PLAN-GAP:** none added beyond
these stated physical storage/deployment qualification limits. **Open questions:**
no new implementation question; the existing real-account/approval checks remain.

**run — workspace hygiene:** no `.work/` file exceeds 500 MB at closing inventory.
Only this worktree and `pkg/19-mail` changed; no protected scope path or workflow
file changed. No merge, force push or new PR. PR #9 stays draft.

## Review fixes, round 16

**Done — read:** implements `briefs/19-review-fixes-16.md` for the blocking finding
and all three should-fixes in [SECURITY-REVIEW-8.md](SECURITY-REVIEW-8.md).
The pending lead commit `5fc6416a` was pushed together with the first code batch.
Code commits: `a7412f99` (installed policy) and
`0fcec015` (MIME/storage), and
`bab9009646237734c59f8e87e2a2ab3088b3eb03` (protected container fixtures;
last code/test change).

### Installed policy and settings scopes

- `aresos_control/boundary_policy.py` is the single complete policy definition.
  `generate.py` emits the managed settings and MCP JSON from it; `boundary.py`
  compares the installed documents as canonical JSON, including extra keys,
  removed keys, list order, value types and the MCP companion's comment.
  Differences name their key paths (and differing list entries). No selected-key
  acceptance list remains. The generated asking rules and MCP command allowlist
  derive from the action/server definitions.
- `boundary.py` opens from `/`, walks every ancestor with descriptor-relative
  `O_DIRECTORY | O_NOFOLLOW`, and checks root ownership and no group/world write
  bits on every opened directory and the regular final file. Production paths
  remain `/etc/claude-code/managed-settings.json` and `managed-mcp.json`.
  `Engine`/`Daemon` no longer accept/pass service configuration overrides for
  these paths; direct tests patch constants, and subprocess fixtures install
  at the fixed paths in their disposable root-run Linux containers. Direct root-run
  fixtures live beneath `/etc/claude-code/fixtures`, with real protected ancestors
  and process-exit cleanup, rather than the runner-owned `/workspace` bind mount.
- The generated settings add `allowManagedMcpServersOnly: true` and an exact
  `allowedMcpServers` command allowlist, plus explicit empty Unix-socket and Mach
  service lists. Existing managed-only read/domain/permission/hook locks remain.
  `managed-hooks.json` is still an inactive draft companion. The 18b image
  copies the settings directory (including that draft), but neither the service
  nor Claude Code loads it as separate hook configuration. Adding even an empty `hooks`
  key to the installed policy refuses. A future hooks deployment must change the
  shared generated definition and pass equality, rather than merge extra hooks.

**read — official rolling documentation, 2026-11-08; not a versioned enforcement
claim:** [settings precedence](https://code.claude.com/docs/en/settings#lists-merge-instead-of-overriding)
says lists normally combine across user, project and local files.
[Sandbox scope locks](https://code.claude.com/docs/en/sandboxing#keep-developers-from-widening-the-policy)
distinguish managed scalars, managed-only lists and remaining user-scope lists.
The [settings reference](https://code.claude.com/docs/en/settings-reference),
[permissions](https://code.claude.com/docs/en/permissions#read-and-edit),
[managed MCP](https://code.claude.com/docs/en/managed-mcp), and
[hooks reference](https://code.claude.com/docs/en/hooks#hook-locations) were also read.

| Setting/source | Scope result and implemented protection (**read**) |
| --- | --- |
| Permission allow/ask/deny lists | Normally merge; `allowManagedPermissionRulesOnly` selects managed rules. Edit denies cover configuration writes. |
| Hooks | Normally merge; `allowManagedHooksOnly` excludes lower-scope hooks. No plugin is force-enabled. |
| MCP definitions and allowlist | `managed-mcp.json` supplies the exclusive server set; `allowManagedMcpServersOnly` also pins the exact command allowlist. Account and built-in Chrome exceptions remain false. |
| Filesystem read paths; network domains | `allowManagedReadPathsOnly` and `allowManagedDomainsOnly` pin allowances. Denial lists can still tighten policy. |
| Command exclusions; filesystem write paths; Unix/Mach socket paths | No general managed-only lock. Admin-required sandboxing excludes repository/local allowances, while user allowances can remain. The launcher excludes lower setting sources; the write-path proof below prevents control tools planting those files. |
| Filesystem disabling and sandbox escape booleans already defined | Managed values prevail; exact comparison refuses changes/additions in installed policy. |

**run — write-path proof:** `CallerWrites16.test_review16_every_caller_write_refuses_all_claude_and_shell_startup_paths`
passes `~/.claude/**`, `~/.claude.json`, nested project `.claude/**`, nested
`.mcp.json`, and all six requested shell startup paths (plus `.bash_login`) to
`testapp_file_save` and `mail_attachment_save`. Both reach the shared `FilePolicy`
refusal before opening a destination. `mail_file_save` is absent from the action
catalogue and refuses with `permission_denied`. `mail_compose` local attachments
and both import actions only read caller paths. Other service writes target its
private state/evidence/blob/password directories, not caller-selected paths.
Existing Linux file tests retain their symlink, hard-link and rename assertions.
The managed Bash sandbox/write denials and Edit denials protect the remaining
native write routes; this is an installation precondition plus the existing 18b
qualification, not proof about an arbitrary external Claude session.

Tests in `test_boundary_exact.ExactBoundary`:
`test_review16_review_reproduction_and_every_extra_or_changed_setting_refuses_with_paths`
(exact review reproduction, disabled filesystem, extra allow/excluded command,
extra MCP server and unknown keys),
`test_review16_every_policy_leaf_mutation_refuses_and_formatting_order_is_canonical`,
`test_review16_ancestor_owner_group_world_and_symlink_each_refuse`,
`test_review16_service_configuration_cannot_supply_fixture_paths`, and
`test_review16_generated_source_locks_present_and_no_managed_hooks_file_is_loaded`,
and `test_review16_root_fixture_uses_protected_container_prefix_and_reuses_path`.
The existing generated-file/package-output acceptance test remains.

**Brief 18b change:** only `control/boundary/check.py` changes: the unmanaged MCP
positive control temporarily removes the new managed allowlist/lock along with
its absent managed MCP file, then restores both documents. Its assertions that
both rogue servers execute without policy, and neither executes with policy,
remain. The boundary package installs the generated files verbatim.

**Brief 18 test changes forced by fixed production paths:**
`control/tests/test_boundary.py` patches constants instead of passing fixture
configuration and checks that the removed constructor option raises `TypeError`;
all prior policy/file/server assertions remain. `test_integration.py` installs the
fixed-path fixture and reads its test path separately from service configuration;
all prior socket/CLI assertions remain. The new `test_boundary_exact.py` is an
addition. Mail subprocess fixtures in `test_proxy.py`, `test_review_fixes.py`,
`test_review_fixes_2.py`, `test_review_fixes_13.py`, `test_review_fixes_14.py`, and
the direct fixtures in `test_review_fixes_15.py` receive the same forced update.
`boundary_test_support.py` no longer adds socket paths or accepts that option,
and provides a protected direct-test prefix in root-run containers.
No earlier assertion is weakened, skipped or deleted.

### Bounded parsing and request failures

`mail/codec.py` uses a streaming `BytesFeedParser` subclass that checks depth
(maximum 40 descendants) and total parts (1,000 including root/implicit digest
children) before creating each node; bytes remain capped at 64 MiB. Every server
mail parse in `mail/adapter.py` uses this function with account/folder/UID identity.
A bound or parser recursion/allocation refusal returns `mime_limit` naming that
message. Other messages remain readable. Header-only evidence uses the same bound.

`Engine.request` and `Daemon.serve` contain unexpected request exceptions,
including `RecursionError` and `MemoryError`, and return a generic `internal_error`
without exposing exception content. Transport/error-response failures and expiry
maintenance cannot end the serving loop. Incomplete journal writes still latch
`write_failed`; no handler clears it or writes through it.

Tests in `test_review_fixes_16.Review16`:
`test_review16_nested_mail_refuses_read_search_thread_and_both_forward_styles_then_reads_other_mail`
(1,200 nested entities through read/search/thread/attachment-save and both forward
styles, message named and next healthy read succeeds),
`test_review16_parser_part_count_depth_edges_and_implicit_digest_children`,
`test_review16_unexpected_request_errors_keep_next_request_and_journal_valid`, and
`test_review16_daemon_contains_unexpected_exception_and_serves_next_connection`.
The parser test uses the production parser and the request tests use the real
Engine/store with in-memory IMAP; the daemon test supplies two accepted connection
substitutes. These are not real hostile-server or model sessions.

### Storage admission and expiry

`retention.py` defines bounds shared by `storage.py`, `blobs.py`, Engine and Mail.
Store checks projected collection usage, history capacity and a 64 MiB free-space
reserve **before** setting the journal latch. Request admission reserves 128 MiB
of history headroom; each event also checks a conservative allocation estimate.
The immutable SQLite/audit history is capped separately, so repeated small free
changes and expired data cannot grow an unlimited historical copy. Quota refusals
use `storage_limit`, name the limit and explain expiry/acknowledgement/owner
archiving. Actual interrupted I/O still fails closed and requires normal recovery.

`mail/adapter.py` stages derived parts in memory, checks the complete composition
result including pending warnings, checks composition/blob capacity, then publishes
blobs and journals the composition. Oversized new or derived compositions leave
no composition, blob, origin metadata or audit row. `blobs.py` checks aggregate
bytes/count before staging an upload; generated parts use aggregate batch
admission. The old per-file and wire limits remain. Store records creation times
in a separate table so imported-reference metadata remains the exact public shape.

| Caller-created retained data | Limit and release rule (**read**, exercised by tests) |
| --- | --- |
| Current compositions | 128 and 4 MiB canonical JSON; unused data expires after 24 hours. An open reserved/submitting/partial/unknown operation pins its composition. |
| Caller-import metadata | 256 references and 1 MiB; expires after 24 hours unless used by a live composition/open operation. |
| Imported/export bytes, quoted mail, local draft bodies/HTML and composition attachments | Shared private blob store: 256 distinct hashes and 512 MiB. Unreferenced blobs expire after 24 hours; composition and operation references pin bytes. |
| Wire/Sent wire evidence | Separate store: 256 hashes and 512 MiB, with 64 MiB per wire. Retained operations pin their evidence, including completed ones. |
| Filing/rename intents | Combined 512 and 128 MiB; completed or acknowledged partial records expire after 24 hours. Started/unresolved records remain. Admission reserves 48 MiB of intent and location capacity before the server mutation. |
| Exact filing-location pages | 128 MiB and 10,240,000 rows; removed with an expired resolved filing intent. |
| Persistent filing notices | 512 and 2 MiB; admission reserves a 16 KiB warning slot before filing. Only acknowledged notices expire after 24 hours. |
| All other free-change audit rows, draft-save records, save reports, cancelled/expired approval records, and historical copies of expired working data | Combined SQLite allocation plus independent journal admission cap: 1 GiB. Never automatically pruned; reaching admission headroom refuses new mutations until owner archiving. Reads remain available. |

Draft-save still appends the owner-approved retained revision on the mail server;
there is no additional local draft archive. These caps govern local persistence,
not mailbox quotas. No automatic remote deletion, recovery filing or log truncation
was added. Expiry frees current-state/blob caps; it does not erase immutable audit
history or pretend to free its capacity. Owner archive/reset tooling remains
outside this brief, and long-lived operation evidence can deliberately keep a cap
occupied until owner maintenance.

Storage tests in `test_review_fixes_16.Review16`:
`test_review16_oversized_composition_has_no_persisted_effect_repeated_or_derived`,
`test_review16_composition_count_and_bytes_caps_expire_but_pin_open_operation`,
`test_review16_blob_count_and_bytes_caps_cover_import_export_generated_and_wire`,
`test_review16_import_reference_count_and_bytes_cap_before_upload_then_expiry`,
`test_review16_filing_notice_count_caps_refuse_before_remote_action_then_ack_expiry`,
`test_review16_filing_notice_location_bytes_caps_refuse_before_journal_fence`,
`test_review16_low_disk_space_refuses_blobs_and_journal_before_fence`, and
`test_review16_audit_admission_covers_repeated_free_changes_before_fence`.
Tests lower constants to fill caps cheaply; they assert no journal latch/durable
change on refusal, restart without corruption/restore, and work after eligible
expiry. Historical-cap relief requires owner maintenance rather than expiry.
Round 15's full journal-failure tests remain passing.

### Verification and remaining checks

**run — initial CI, transparently retained:** code head `0fcec015` started
[base 42436252621](https://github.com/Ares-Empire/AresOS/actions/runs/42436252621/attempts/1)
and [Mail 42436252636](https://github.com/Ares-Empire/AresOS/actions/runs/42436252636/attempts/1).
Both stopped in the base suite (`Ran 92 tests`, `FAILED (failures=106, errors=3)`):
the correctly protected verifier rejected direct fixtures beneath the runner-owned
`/workspace` ancestor. Mail's real-server suite did not run in that attempt.
The correction moves only those fixtures to protected container ancestors and
adds a regression for that fixture choice; no assertion or production check was
relaxed. [Boundary 42436252617](https://github.com/Ares-Empire/AresOS/actions/runs/42436252617/attempts/1)
passed on the same initial code head.

**run — last code/test commit** `bab9009646237734c59f8e87e2a2ab3088b3eb03`:

| Workflow | Run and attempts | Result / exact evidence |
| --- | --- | --- |
| Control base | [42436551284 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42436551284/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42436551284/attempts/2) | Both PASS. `bash control/ci/test.sh` inside Fedora: Python 3.15.0, `Generated artifacts match definitions`, `Ran 93 tests`, `OK`, `Control base suite PASS` (attempt 1 log lines 207/271/367–373; attempt 2 lines 384–390). |
| Control Mail | [42436551286 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42436551286/attempts/1), [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42436551286/attempts/2) | Both PASS. `bash control/ci/mail/run.sh`: `Mail fixture isolation PASS: internal network, one test network, no published ports`; `Ran 93 tests`, `Control base suite PASS`; `Ran 191 tests`, `OK`, `Control Mail suite PASS` (attempt 1 lines 367–373, 442, 738–744; attempt 2 exact counts/results confirmed in its saved log). |
| Control boundary | [42436551301 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42436551301/attempts/1) | PASS. `Installed boundary precondition PASS` (line 883), `SOURCES_POSITIVE_OK` (1224), `MANAGED_MCP_OK user=assistant names=["control", "mail"]` in both modes (1671/2386), and separate coder isolation (2429). |

The second base/Mail passes use `gh run rerun` on the same IDs. GitHub's PR
workflow checks out its synthetic merge ref; the run API's `headSha` is the
code/test commit above. Any later commit changes only files under `reviews/`.
Final-head run IDs and both completed base/Mail attempts are recorded in the PR
body after the report push; no extra push is used merely to create a second pass.

**run — local checks before both code pushes and again before the report push:**

```text
python3 control/generate.py --check
Generated artifacts match definitions
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py
Python syntax OK: 98 files; Ran 70 tests; OK
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest test_operations test_record test_crashes test_approval_questions test_strict_json test_boundary test_ingress_bounds test_journal_closed test_boundary_exact
Ran 63 tests; OK (first push); Ran 64 tests; OK (fixture correction and report push)
Record growth: tiny send=4078 bytes; maximum body + 25 MiB send=4078 bytes; 6 state/stage records, mean=679.7 bytes per record including commit
Record growth: typical three-recipient send=5560 bytes across 8 state/stage records
```

The local non-root macOS harness models root ownership only for its generated
fixture files/ancestors; all real ownership/isolation claims come from Linux CI.
The local Mail runner selects plain-Python classes, not the real-server classes.
An isolated `.work/round16/baseline` overlay of reviewed `9e4b1375` source with the
new tests fails both suites (Mail: 13 tests, 9 failing assertions plus 21 subtest
errors; boundary: 6 tests, 2 failing assertions plus 60 subtest errors). Missing
new admission APIs account for some errors; the oversized-composition snapshot,
MIME crash containment, policy equality and ancestor/configuration assertions
also fail on that old code. This is regression evidence, not a passing baseline.

**Not verified / assumed:** no real account, provider, phone/terminal approval UI,
model-driven task session, or installed owner machine was exercised. Existing
owner qualification checks above remain. No screenshots: this round changes
service policy/parsing/storage, not UI. No Minecraft/Gradle work was started.

**JUDGMENT-CALL:** caps and refusals implement the lead's safety rule, as stated in
the owner section; they are not new owner choices. **PLAN-GAP:** none added to the
brief; maintaining/archiving a full audit store is still owner maintenance, not
an automatic destructive cleanup. **Open questions:** no new implementation
question; real-account and native approval qualification remain as above.

**run — workspace hygiene:** no `.work/` file exceeds 500 MiB at closing inventory.
Only the current worktree/branch was changed; protected scope paths and workflow
files are untouched. PR #9 stays draft and unmerged.

## Review fixes, round 15

**Done — read:** closes findings 1–3 and the decoder-bounds should-fix in
[SECURITY-REVIEW-7.md](SECURITY-REVIEW-7.md), following
`briefs/19-review-fixes-15.md` with the owner correction in `briefs/19-review-fixes-15b.md`. The owner settled attachment disclosure on 2026-11-08 as recorded above. The original round-15 code/test head was `cf1426bd4615c67917e9375990a4515ea5215233`; the 15b verification below supersedes it for folder moves.

- **Installed boundary:** new shared-base `aresos_control/boundary.py` reads the
  installed managed settings and MCP files at startup and before every asking
  preparation/submission, including direct CLI/socket use and owner setup probes.
  It requires regular root-owned files without symlinks or group/world write
  bits, the specified sandbox/source/bypass gates, socket-directory denial,
  every generated asking rule, no exact or wildcard allow grant for those tools,
  and exactly the generated production MCP server commands. Missing paths default
  to `/etc/claude-code`; `service.json` may supply `managed_settings` and
  `managed_mcp` for fixtures. Faults name the path/key/tool/server with
  `boundary_not_installed`. Reads and free changes still work. `engine.py` owns
  the service-side gate; `daemon.py` passes its protected configuration;
  `mail/onboarding.py` checks before setup and again before recording readiness.
- **One source of truth:** `generate.py` derives asking rules and managed MCP
  commands from the catalogue through the shared boundary helpers. It also writes
  the MCP ask rules into `settings/managed-settings.draft.json`, retaining its
  other content and non-MCP ask rules; `--check` detects drift. The generated
  `managed-mcp.json` has the same contents as before. The only changes under
  `control/boundary/` are two Dockerfile lines: copy the shared Python package,
  then execute the actual precondition check against the installed files after
  the image's existing COPY/cp steps. It prints
  `Installed boundary precondition PASS` during the build.
- **Folder moves under the filing policy (15b):** `mail/adapter.py` accepts an
  exact new path under another parent again. A bare last name still retains the
  current parent; pre-action fresh roles, leaf-only and protected source/destination
  checks remain. The final checked roles go into the durable `mail:rename:` intent
  with source, new name and message count before RENAME. `mail/filing.py` LISTs the
  destination and resolves current roles afterward. Trash, Drafts, Sent, Junk or
  Archive on the new location or an ancestor, a new special-use flag assigned by
  name (including Flagged/All/Important), or an unverifiable result returns
  `partial` and a bounded escaped persistent warning. A stable ordinary target
  returns `done`. Intent/outcome audit states are started/done/partial as appropriate.
  The same filing-notice path repeats warnings in later Mail results and owner
  log, lists them with `mail_filing_notices`, and acknowledges via `mail_notice_ack`.
  Role flags stay normalized and deduplicated. Nothing is renamed back or deleted;
  restart never replays an unfinished rename. `mail/definitions.py`, generated
  Mail tools, `docs/control/TOOLS.md` and `control/README.md` describe this policy.
- **Input and journal integrity:** shared `common.py` rejects non-finite floats
  including exponent overflow, constants, integers with absolute value greater
  than `2**63 - 1`, more than 64 nesting levels, more than 6 MiB, initial BOMs,
  invalid UTF-8 and non-scalar Unicode. A nonrecursive pre-scan bounds the decoder;
  the error-classification pairs tree uses the same bounds. `requests.py` supplies
  closed version/method envelopes for all six socket methods, including the
  typed `saved` outcome, and explicit upload/download chunk schemas; tool
  payloads still use their catalogue schemas. `engine.py` validates before
  dispatch. `proxy.py` bounds binary MCP lines before decoding/SDK dispatch,
  drains an oversize line in bounded pieces and refuses its entire contents;
  it validates JSON-RPC and tool-call envelopes. `hooks.py` bounds stdin and
  validates its event payload before reading pending work. CLI/configuration
  ingress inherits the shared decoder without another parser.
- **Fail closed:** `storage.py` validates and serializes the complete event before
  appending the independent fence or writing SQLite. An incomplete durable write
  latches `journal_incomplete` until restart recovery; later state changes,
  submissions, expiry, restore confirmation and file transfers cannot write past
  it. `blobs.py`, and both blob stores wired by `engine.py`/`mail/adapter.py`,
  check the same latch before writing bytes or metadata. Requests are validated
  before adapter/blob work. Tests include a failed submission-stage write that
  stops before the next recipient.

**Existing fixture changes, with every assertion retained:**
`control/ci/test.sh` installs actual root-owned generated managed files for the
whole base and Mail container suites. New `control/boundary_test_support.py`
installs the same files with a fixture's temporary socket directory denied.
The only edits to the existing brief-18 tests are that fixture installation and
one new integration test in `control/tests/test_integration.py`. Existing Mail
fixtures in `test_proxy.py`, `test_review_fixes.py`, `test_review_fixes_2.py`,
`test_review_fixes_13.py` and `test_review_fixes_14.py` each receive the same two-line
policy installation before starting their daemon. No assertion was changed,
removed or skipped.

**New tests by name — run:**

- `InstalledBoundary.test_each_required_setting_missing_and_wrong_refuses_preparation_and_submission`
- `InstalledBoundary.test_all_generated_asking_rules_required_and_never_allowed_even_wildcards`
- `InstalledBoundary.test_both_files_require_root_regular_nonwritable_nonsymlink`
- `InstalledBoundary.test_exact_managed_servers_and_commands_and_default_paths`
- `InstalledBoundary.test_boundary_image_generated_files_pass_and_restored_policy_enables_submission`
- `JournalClosed.test_complete_event_serialized_before_any_durable_change`
- `JournalClosed.test_every_envelope_and_payload_validated_before_dispatch_including_saved`
- `JournalClosed.test_incomplete_transaction_blocks_requests_blobs_expiry_and_restore_until_restart`
- `JournalClosed.test_incomplete_submission_stage_stops_before_next_recipient`
- `IngressBounds.test_strict_and_error_classification_decoders_share_all_bounds`
- `IngressBounds.test_socket_raw_bounds_refuse_before_engine_dispatch`
- `IngressBounds.test_cli_raw_bounds_refuse_before_proxy_or_admin_password_prompt`
- `IngressBounds.test_hook_raw_bounds_refuse_before_pending_read`
- `IngressBounds.test_hook_explicit_payload_schema_refuses_wrong_types_and_unknown_fields`
- `IngressBounds.test_real_mcp_binary_stdio_bounds_refuse_without_dispatch_and_stream_recovers`
- `Integration.test_round15_same_uid_socket_and_installed_cli_require_policy_then_execute_once`
- `Review15.test_review15_cross_parent_reproduction_and_separator_use_exact_target` (updated by 15b)
- `Review15.test_review15_leaf_rename_retains_parent_and_all_messages`
- `Review15.test_review15_role_assigned_by_rename_persists_bounded_warning_and_ack`
- `Review15.test_review15_repeated_special_role_flags_keep_notice_bounded`
- `Review15.test_review15_exact_saved_overflow_then_composition_restart_keeps_valid_evidence`
- `Review15.test_review15_mail_preparations_submissions_and_onboarding_require_boundary`
- `Review15.test_review15_onboarding_rechecks_policy_before_marking_account_ready`

The raw-input matrix exercises socket, both CLI paths, real binary MCP stdio,
Stop and UserPromptSubmit with `1e400`, oversized integers, NaN, 1,200 arrays,
escaped lone surrogates, surrogate-encoded UTF-8, invalid UTF-8/surrogateescape
bytes, BOM and oversize input. Guards prove no dispatch, adapter call, password
prompt or pending request occurs; MCP continues with a valid request afterward.
The exact review `saved` frame is refused, a later Mail composition succeeds,
and real Store restart validates the journal without `evidence_corrupt`.

**Local verification — run before each push:**

```text
python3 control/generate.py --check
Generated artifacts match definitions
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py
Python syntax OK: 93 files
Ran 53 tests in 2.400s
OK
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest test_operations test_record test_crashes test_approval_questions test_strict_json test_boundary test_journal_closed test_ingress_bounds
Ran 58 tests in 15.517s
OK
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s control/boundary -p test_native.py -v
Ran 15 tests in 0.005s
OK
git diff --check
(no output; exit 0)
```

All pre-push local runs passed. The report-push repetition printed
`Ran 53 tests in 2.392s`, `Ran 58 tests in 15.432s` and
`Ran 15 tests in 0.004s`, each followed by `OK`.

The first base invocation exposed a missing local MCP dependency in the round-10
vendor directory; the already downloaded round-14 vendor copy supplies it through
an ignored local bootstrap. The Mac is not root: that bootstrap models root
ownership only for generated fixture copies, while the content/mode/type/symlink
checks execute normally. Linux CI installs and checks real root-owned files;
local ownership modeling is not evidence of Linux confinement. Early new-test
runs also exposed a too-narrow socket exception expectation and a missing dummy
MCP socket configuration; both test harnesses were corrected before the push.
The complete-event test additionally led to validation of untrusted content
before display escaping. Subsequent local commands above pass.

Eight selected new tests were also run using reviewed `6a2e0e36` production
modules extracted inside `.work/round15/baseline`: four base tests and four Mail
tests all fail at the relevant missing refusal, silent rename or unsafe durable
write. The new boundary module was supplied only so the current fixture imports
could load; the reviewed Engine never invokes it. These are regression probes,
not a baseline-suite pass. The repeated-role regression separately failed on
`35ea98a9` with `result_too_large`, then passed after deduplicating the role
flags. That correction required a second code push before the report push; no
GitHub workflow failed.

**Code/test-head Linux verification — run:**

| Workflow / pass | Exact relevant output |
| --- | --- |
| [Mail 42427029339, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42427029339/attempts/1) | `Ran 87 tests in 70.630s`; `Control base suite PASS`; `Ran 171 tests in 522.238s`; `Control Mail suite PASS` |
| [Mail 42427029339, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42427029339/attempts/2) | `Ran 87 tests in 71.634s`; `Control base suite PASS`; `Ran 171 tests in 528.149s`; `Control Mail suite PASS` |
| [Independent base 42427029387, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42427029387/attempts/1) | `Ran 87 tests in 61.449s`; `Control base suite PASS` |
| [Independent base 42427029387, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42427029387/attempts/2) | `Ran 87 tests in 82.250s`; `Control base suite PASS` |

Both Mail passes include all 171 Mail tests and the complete 87-test base suite;
both independent base passes run all 87 tests. Every pass prints generated
artifact agreement and its suite PASS lines. The [boundary run 42427029336](https://github.com/Ares-Empire/AresOS/actions/runs/42427029336)
also passed, including `Installed boundary precondition PASS` during image
build, and `NATIVE_BOUNDARY_OK`, `BOUNDARY_OK`, `LAUNCHER_OK`, `SETTINGS_OK` and
`ISOLATION_OK` in the existing hostile checks. The native absent-helper
standalone VSOCK fallback remains explicitly unqualified, as in 18b's report.


**Not verified / PLAN-GAP:** this is an installation **precondition check**.
Whether Claude Code honours the files and confines Bash is established by brief
18b's hostile tests and brief 18c, not by this check. It is not an independent
proof that a human approved a particular same-UID request. `os/` installs these
files later, owned by another session; this round does not edit `os/`. Real
providers, owner setup, terminal/phone prompt presentation and the existing
real-account checks remain owner work. No screenshots are needed for these
protocol/service changes. The owner settled folder moves and attachment
disclosure on 2026-11-08; neither remains an open decision.

**Repository discipline:** the pre-existing local review/brief commit was pushed
with the two code commits. The third push contains only this review report;
second passes use `gh run rerun`, never a push just to trigger CI. Both ordinary
pre-push privacy checks remain enabled. No merge, rebase, force push, protected
review edit, workflow change or OS/mod change. No `.work` file exceeds 500 MB
(the closing scan returned `[]`).

### Round 15b — owner correction and verification

**Done:** implements `briefs/19-review-fixes-15b.md` on top of its existing local
brief commit `16cc38e7`. The owner’s answers above apply to all listed decisions;
the three real-account checks are unchanged. The attachment stopping rule is closed:
Claude-written text in attachments is accepted behaviour, not a should-fix.
No base/boundary implementation, tests, settings or workflow changed in this batch.

**Tests:** seven new methods in `control/mail_tests/test_review_fixes_15b.py`:

- `Review15b.test_review15b_review7_trash_parent_race_preserves_three_messages_and_repeats_notice`
  reproduces Source (three messages) → Parent/Subfolder through Engine/Mail and
  the scripted TLS IMAP frontend over real Dovecot. Parent becomes Trash immediately
  before RENAME, after the last check. A separate SQLite connection observes the
  committed started intent before the wire action. The test checks partial and the
  exact warning, current Trash role, notice listing/repetition in Mail and control_log,
  restart, acknowledgment, exact server bytes for all three messages, no old source,
  zero approval operations and precisely one RENAME with no recovery mutations.
- `Review15b.test_review15b_ordinary_cross_parent_move_done_without_warning`
- `Review15b.test_review15b_same_parent_rename_done_without_warning`
  use the same real adapter/frontend and three server messages; they check done,
  exact destination, durable role snapshot and message count, no warnings and no recovery.
- `RenamePolicy15b.test_review15b_protected_ancestors_warn_with_bounded_escaped_names`
  covers Trash, Drafts, Sent, Junk and Archive races with long bidi folder names.
- `RenamePolicy15b.test_review15b_crash_after_rename_keeps_started_intent_and_never_replays`
- `RenamePolicy15b.test_review15b_special_source_and_destination_subtrees_still_refuse`
- `RenamePolicy15b.test_review15b_unverifiable_postcheck_warns_without_recovery`
  are portable real-adapter tests using an IMAP command substitute. They cover
  durable unfinished intent in owner log after restart, protected prechecks and
  interrupted post-check preservation.

**Earlier test changes:** only
`Review15.test_review15_cross_parent_reproduction_and_separator_refused_before_rename`
becomes `test_review15_cross_parent_reproduction_and_separator_use_exact_target`.
Its four separator-bearing inputs (`Parent/Subfolder`, `Source/Child`, `/Other`,
`Other/`) now test exact command targets through the command substitute, with
message/whole-mailbox preservation, zero approval operations and no notices.
Server-specific name validity is still the server’s decision. Assertions requiring
refusal and no mutation change because the owner explicitly restored these moves.
The same-parent, role-by-name, repeated-role bounds, boundary and journal tests in
round 15 retain every assertion. No other earlier test was weakened, skipped or deleted.

**Local verification — run before the implementation push:**

```text
python3 control/generate.py --check
Generated artifacts match definitions
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py
Python syntax OK: 94 files
Ran 57 tests in 2.312s
OK
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest test_operations test_record test_crashes test_approval_questions test_strict_json test_boundary test_journal_closed test_ingress_bounds
Ran 58 tests in 15.492s
OK
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s control/boundary -p test_native.py -v
Ran 15 tests in 0.005s
OK
git diff --check
(no output; exit 0)
```

The ignored mutation probe replaces only rename execution with a durable-intent
implementation accepting cross-parent moves but doing no post-check. The protected
ancestor regression fails at `AssertionError: 'done' != 'partial'`; the same test
passes with production code. Output ends `Mutation probe PASS: cross-parent
acceptance without the post-check fails on done versus partial`. This is an
in-memory mutation probe; the exact three-message server reproduction runs in Linux CI.

Docker’s CLI exists locally but its daemon is unavailable
(`Cannot connect to the Docker daemon`); no host software or settings were changed.
The existing ignored round-10/14 dependencies and non-root Mac fixture bootstrap
are reused. Its root-ownership model is not evidence of Linux confinement.

**Not verified / JUDGMENT-CALL / PLAN-GAP / Open questions:** no new decision or
gap. The owner approved folder moves and all listed policies on 2026-11-08, kept
as built. Real-account, terminal/phone and recipient-program checks above remain.
No real account, provider, delivery or screenshot is claimed.

**Repository discipline:** the existing local brief commit is included with this
batch; normal pre-push privacy verification remains enabled. No merge, rebase,
force-push, protected review edit, OS/mod or workflow change. No large download or
extraction was made. Code/test-head workflow evidence follows.

Before the report-only push, the same local commands pass again: generated
artifacts match; `Python syntax OK: 94 files`; `Ran 57 tests in 2.440s`, `OK`;
`Ran 58 tests in 15.599s`, `OK`; and `Ran 15 tests in 0.005s`, `OK`.
`git diff --check` is silent. The explicit scope check prints
`Scope check PASS: no protected path changed`; the owner-check comparison prints
`Owner decisions recorded; real-account checklist unchanged`.

**Linux verification — last code/test commit `52e10c6fb227d8767b4e05fb68012817cd9406a6`:**

| Workflow / pass | Exact relevant output |
| --- | --- |
| [Mail 42431033063, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42431033063/attempts/1) | `Ran 87 tests in 68.772s`; `Ran 178 tests in 526.814s`; `Control base suite PASS`; `Control Mail suite PASS` |
| [Mail 42431033063, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42431033063/attempts/2) | `Ran 87 tests in 55.012s`; `Ran 178 tests in 506.442s`; `Control base suite PASS`; `Control Mail suite PASS` |
| [Independent base 42431033233, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42431033233/attempts/1) | `Ran 87 tests in 69.642s`; `Control base suite PASS` |
| [Independent base 42431033233, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42431033233/attempts/2) | `Ran 87 tests in 57.958s`; `Control base suite PASS` |

Both Mail passes run `bash control/ci/mail/run.sh`: generated artifacts, all 87
base tests and all 178 Mail tests, including the three scripted TLS/Dovecot rename
regressions. Both independent base passes run all 87 tests through
`bash control/ci/test.sh` in pinned Fedora. Every new method passes in both Mail
logs. Both workflows pass twice on this exact code/test head.
The [boundary run 42431033183](https://github.com/Ares-Empire/AresOS/actions/runs/42431033183)
also passes: installed precondition, hostile checks with/without seccomp, launcher,
settings and coding-policy isolation. The previously unqualified standalone
absent-helper VSOCK fallback is unchanged; no new qualification is claimed.

**Any later commit changes only files under `reviews/`.** The final report head’s
run IDs and both passes are recorded in [draft PR #9](https://github.com/Ares-Empire/AresOS/pull/9).
Second passes use `gh run rerun` on these same IDs. No push is made solely to
trigger another pass. The implementation push included code, tests, report and
the pre-existing brief commit. A report-only follow-up is necessary to record
the run IDs created by that push; it changes no code or test. Each push receives
the required local checks and ordinary privacy verification. No failed workflow
has been treated as success. The closing scan prints
`Remaining .work files over 500 MB: []`.

## Review fixes, round 14

**Done — read:** addresses the blocking duplicate-key bypass and the cleanup
feedback finding in [SECURITY-REVIEW-6.md](SECURITY-REVIEW-6.md), following
`briefs/19-review-fixes-14.md` on top of `99b15db3` (reviewed code `3058c256`).

- Shared base `common.py`: `strict_json_loads()` checks decoded keys with an
  `object_pairs_hook` before constructing each dictionary, at every depth, and
  rejects `NaN`/`Infinity`/`-Infinity`. On refusal, a separate lossless pairs-only
  tree recovers action/id candidates solely to classify and answer the refusal;
  it never becomes an executable request. Asking inputs return `stale_approval`;
  other inputs return `invalid_input`.
- Shared base `protocol.py`, both CLI input paths in `cli.py`, hook stdin in
  `hooks.py`, and configuration reads in `daemon.py` now use that decoder before
  validation, hashes, reservation, submission or adapter work. `control/launch.py`
  also uses it: the installed launcher reads both proxy/service configuration
  before dispatching to those modules, so leaving it permissive would miss an
  actual configuration entrance. Internal storage reads in `storage.py`,
  `blobs.py` and `testapp.py` deliberately remain unchanged.
- Shared base `proxy.py`: the SDK's explicit stdin stream checks each raw line
  before SDK JSON-RPC parsing. Refused lines never reach `call_tool` or the
  service. A JSON-RPC error goes through the SDK's output stream, with the
  caller's id and refusal code in `error.data.code`; repeated ids receive an
  error for every distinct string/integer id candidate. Valid lines reach the
  SDK unchanged; result ordering, approval equality and replay protection stay.
- `mail/adapter.py::check_items()` keeps the original mailbox check, collects
  offending references, escapes them in the refusal and says: “Leave these out
  of the selection and delete them in your mail program.” Healthy messages can
  still be prepared together without the offending message.

**Tests — run:** shared raw-text builders and a real stdio client are in
`control/raw_json_test_support.py`. New base tests in `control/tests/test_strict_json.py`:

- `StrictJSON.test_decoder_refuses_duplicate_decoded_keys_at_every_depth_and_nonfinite`
- `StrictJSON.test_config_and_hook_refuse_before_daemon_or_pending_call`
- `StrictJSON.test_cli_nonasking_and_admin_config_refuse_before_proxy`
- `RawApprovalJSON.test_raw_testapp_socket_and_cli_refuse_before_any_operation_work`
- `RawApprovalJSON.test_raw_mcp_process_refuses_duplicates_before_service_then_executes_once`

The only change to an existing brief-18 test file is the addition of
`Integration.test_round14_raw_duplicates_real_proxy_socket_cli_no_effects_then_once`
in `test_integration.py`. No earlier test or assertion changed. New Mail tests in
`control/mail_tests/test_review_fixes_14.py`:

- `PlainJSON14.test_round14_raw_mail_socket_and_cli_refuse_before_validation_and_execution`
- `PlainJSON14.test_round14_delete_refusal_names_only_bad_references_and_healthy_batch_prepares`
- `ServerJSON14.test_round14_real_proxy_socket_cli_duplicates_no_arrival_or_deletion_then_once`

Raw cases cover duplicate `question` (plain and `\u0071uestion`),
`operation_id`, `description`, a field inside `description`, and the transport
request envelope (socket `action`, MCP `params`; CLI's approval is its envelope).
Testapp send/delete and Mail send/delete/folder-delete each use socket, CLI and
a real MCP proxy process. Refusals keep operations `reserved`, stages empty and
fixtures unchanged. Portable guards prove no request/validation/hash/reservation/
submission/stage/evidence/execution work, and the portable real MCP process
asserts no outbound service call at all. The Mail server check uses Dovecot
through the existing test-only serialized folder-deletion policy and scripted
TLS SMTP: no IMAP command/SMTP arrival on refusal, one send/expunge/folder-delete
on correct raw approval, and no effects from replays through all three routes.
The cleanup test checks Trash and permanent deletion, exactly the bad reference
including its escaped control, no reservation on refusal, and a healthy batch
preparing successfully. It does not qualify a real provider's folder policy.

**Verified — run, last code/test head `2fd2fcadfd326692b46dceb174c2da748c1161fd`:**

| Workflow / pass | Exact relevant output |
| --- | --- |
| [Mail 42419938878, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42419938878/attempts/1) | `Ran 71 tests in 57.381s`; `Control base suite PASS`; `Ran 164 tests in 491.096s`; `Control Mail suite PASS` |
| [Mail 42419938878, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42419938878/attempts/2) | `Ran 71 tests in 60.282s`; `Control base suite PASS`; `Ran 164 tests in 530.157s`; `Control Mail suite PASS` |
| [Independent base 42419938827, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42419938827/attempts/1) | `Ran 71 tests in 55.340s`; `Control base suite PASS` |
| [Independent base 42419938827, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42419938827/attempts/2) | `Ran 71 tests in 62.888s`; `Control base suite PASS` |

Both Mail passes run all 164 Mail tests and the complete 71-test base suite;
both independent base passes run all 71 tests. Every pass prints generated-artifact
agreement and its suite PASS lines. The automatic [boundary run 42419938819](https://github.com/Ares-Empire/AresOS/actions/runs/42419938819)
also passed; no boundary test or workflow changed.


Local commands, repeated before each push:
`python3 control/generate.py --check` → `Generated artifacts match definitions`;
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py`
→ `Python syntax OK: 86 files`, `Ran 46 tests`, `OK`;
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest test_operations test_record test_crashes test_approval_questions`
→ `Ran 38 tests`, `OK`, unchanged record-growth evidence;
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round14/vendor python3 -m unittest test_strict_json -v`
→ `Ran 5 tests`, `OK`. The last uses worktree-local official MCP SDK 2.3.0 on
Python 3.14.6; CI uses the unchanged Linux dependency lock and Python 3.15.
The untracked `.work/round14/check-baseline.py` and `check-mail-baseline.py`
substitute the relevant reviewed `3058c256` implementations; they print that
all five new portable base and both portable Mail regressions fail as expected.
The MCP baseline check launches the actual reviewed proxy sources in a process.
The additional untracked `.work/round14/check-envelope-only.py` prints
`Envelope-only duplicate PASS`: isolated socket `action` and MCP `params`
duplicates, with otherwise correct approvals, refuse for testapp send/delete and
Mail send/delete/folder-delete; every operation stays reserved with no stages,
and neither real MCP proxy forwards a refused request.
No container or system software was installed on this Mac.

**Not verified:** real-account onboarding, provider policy and terminal/phone
presentation still need the owner's checks above. No new screenshots apply.
**JUDGMENT-CALL / PLAN-GAP / Open questions:** none added; existing owner decisions
remain. No fresh security hunt, workflow change or boundary-policy work.

Two pushes: code/tests together with the already-local review/brief commit, then
this report. Any later commit after the code/test head above changes only files
under `reviews/`; final-head results are recorded in draft PR #9. Second passes
rerun the same run ids. Four required Mail/base workflow ids across the two
heads, with automatic boundary runs additional; no push solely for a rerun.
Normal pre-push verification retained; no merge, rebase or force push. Closing
size scan: `Remaining .work files over 500 MB: []`.

## Review fixes, round 13

**Done — read:** closes both blocking findings in
[SECURITY-REVIEW-5.md](SECURITY-REVIEW-5.md), following
`briefs/19-review-fixes-13.md` on top of `578bfc8c`.

- `mail/questions.py`: one `people()` helper parses every recipient/sender header
  into individual mailboxes for send, delete and unsubscribe. Only display names
  keep the 80-visible-character shortening; complete addresses have no shortening
  limit. Summaries count mailboxes, show the first three and the exact remainder.
  Missing/empty addresses and parse defects refuse with a clear `invalid_input`
  reason. The original incoming From header is also checked in
  `mail/adapter.py::check_items`, because converting a header to a string can
  repair its syntax and discard defects. Folder names stay whole. The existing
  4,096-character question and whole 16-KiB caps refuse before reservation.
- Shared base `common.py::require_question()` now requires exactly `question`,
  `operation_id`, `description`, in that order. The existing proxy and dispatcher
  calls check the received dictionaries before validation, hashes, submission,
  evidence or adapter execution. `proxy.py` and `cli.py` need no changes.
- Shared base `protocol.py::send()` preserves request order by default; only
  explicit `result=True` uses question-first presentation. Base `daemon.py` and
  `engine.py` mark their response frames accordingly. `receive()` passes the
  socket JSON order straight to the dispatcher. Canonical storage/hashes and
  all result presentation remain unchanged. No definitions or generated output
  changed; generated artifacts still match.

**Tests — run:** new `control/mail_tests/test_review_fixes_13.py` methods:

- `PlainApprovals13.test_round13_unsubscribe_long_name_and_117_character_address_real_preparation`
- `PlainApprovals13.test_round13_delete_multiple_long_named_senders_and_exact_mailbox_count`
- `PlainApprovals13.test_round13_unparsable_and_original_defective_from_refuse_with_reason`
- `PlainApprovals13.test_round13_addresses_and_folder_names_over_question_cap_refuse_without_cutting`
- `PlainApprovals13.test_round13_mail_all_wrong_orders_stop_before_submit_stage_evidence_or_adapter`
- `ServerApprovals13.test_round13_real_mcp_socket_cli_wrong_orders_no_arrival_or_imap_then_once`

The five portable methods use production preparation/Engine with in-memory IMAP;
all five fail when the relevant implementations from `9061d892` are substituted
in memory. The server method uses real MCP stdio, raw sockets and CLI against the
production daemon, Dovecot through the existing serialized test-only deletion
policy, and scripted TLS SMTP. It covers all five wrong key orders for Mail
send, permanent delete and folder delete: no SMTP arrivals or IMAP commands;
correct order executes once and replay through every route has no further effect.
This fixture does not qualify the real account's folder-deletion policy.

New base tests in `test_approval_questions.py`:
`ApprovalQuestions.test_round13_wrong_orders_and_extra_or_missing_keys_stop_before_submission`
and `ApprovalQuestions.test_round13_client_serializes_caller_order_without_result_presentation`.
They check send/delete, extra and missing keys, no proxy forwarding of invalid
approvals, and zero submit/stage/revalidate/evidence/execute calls. New
`Integration.test_round13_all_wrong_orders_refused_by_real_mcp_socket_and_cli_then_execute_once`
checks all five wrong orders on every route, no arrival/deletion/stage, and one
correct execution with replay protection.

**Existing tests changed — read:** base `Integration.request()` now uses
order-preserving `json.dumps` instead of canonical hash serialization; all earlier
assertions remain. This is forced by rejecting canonical JSON's alphabetic field
order at the boundary. No other earlier base test changed.
Round 12's `test_round12_controls_bidi_and_backslashes_escape_once_without_cutting_escapes`
now asserts refusal of its original non-printable defective mailbox, then checks
escaping with a syntactically valid bidi/backslash name; the escaped-control
assertion uses the existing subject's NUL. Escape-boundary, full-description,
folder-control and bidi checks remain. The round-12 lookalike test is unchanged.
No test was skipped or deleted.

**Verified — run, last code/test head
`0c37452177a45968e82539b62933fabc380ed5b5`:**

| Workflow / pass | Exact relevant output |
| --- | --- |
| [Mail 42415050224, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42415050224/attempts/1) | `Ran 65 tests in 56.088s`; `Control base suite PASS`; `Ran 161 tests in 507.454s`; `Control Mail suite PASS` |
| [Mail 42415050224, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42415050224/attempts/2) | `Ran 65 tests in 66.656s`; `Control base suite PASS`; `Ran 161 tests in 589.811s`; `Control Mail suite PASS` |
| [Independent base 42415050201, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42415050201/attempts/1) | `Ran 65 tests in 44.266s`; `Control base suite PASS` |
| [Independent base 42415050201, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42415050201/attempts/2) | `Ran 65 tests in 56.084s`; `Control base suite PASS` |

Both Mail passes run all 161 Mail methods and the complete 65-test brief-18 base
suite; both independent base passes run all 65 methods too. Generated artifacts
match in every pass. The corrected-head [boundary run 42415050276](https://github.com/Ares-Empire/AresOS/actions/runs/42415050276)
also passed; no boundary assertion or workflow changed.

**Initial failure and fixture correction — run:** first code head `dc1aa6ed`
had two successful independent base passes
([42414074339](https://github.com/Ares-Empire/AresOS/actions/runs/42414074339),
`Ran 65 tests in 56.762s` / `57.071s`, `Control base suite PASS`) and a successful
[boundary run 42414074323](https://github.com/Ares-Empire/AresOS/actions/runs/42414074323).
Its [Mail run 42414074382](https://github.com/Ares-Empire/AresOS/actions/runs/42414074382)
printed `Ran 161 tests in 478.347s`, `FAILED (failures=1)`:
`test_round13_delete_multiple_long_named_senders_and_exact_mailbox_count` saw
only the final mailbox. All other Mail methods, including the real MCP/socket/CLI
non-effect regression, passed. These runs are not substituted for the corrected
head's verification above.

A local reproduction with the official [CPython 3.15 header parser](https://github.com/python/cpython/blob/3.15/Lib/email/_header_value_parser.py)
and [header registry](https://github.com/python/cpython/blob/3.15/Lib/email/headerregistry.py)
source showed the fixture generator turning two mailboxes into one: the first
address became encoded display-name text for the last address. Fixture-only
commit `0c374521` writes the exact incoming From header with CRLF continuations
and adds an assertion that all expected source mailboxes survive before checking
the approval. Every original assertion remains. The five portable round-13
methods then passed with those 3.15 modules substituted locally; this is source
substitution under the Mac's Python 3.14.6, not a Linux/Python-3.15 runtime claim.
No system software was installed. The initial failure requires one extra push
and three workflow IDs beyond the planned code/report pair.

Local pre-push commands (also repeated before the report push):
`python3 control/generate.py --check` → `Generated artifacts match definitions`;
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py`
→ `Python syntax OK: 83 files`, `Ran 44 tests`, `OK`;
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest test_operations test_record test_crashes test_approval_questions`
→ `Ran 38 tests`, `OK`, unchanged record-growth evidence. The untracked
`.work/round10/round13-baseline-check.py` prints
`Baseline 9061d892: all 5 new portable Mail regressions fail as expected`.
The corresponding `.work/round10/round13-base-baseline-check.py` prints
`Baseline 9061d892: both new portable base regressions fail as expected`.
Containers cannot run on this Mac; durable Linux/provider evidence comes from CI.

**Not verified:** real-account setup and terminal/phone presentation still need
the owner's checks above. No new screenshot or Minecraft/Gradle claim applies.
**JUDGMENT-CALL / PLAN-GAP:** no new owner decision; refusal and ordering follow
the brief. No fresh security hunt or boundary-policy work was undertaken.
**Open questions:** none added; earlier owner decisions remain open.

Three pushes: code with the pre-existing local review/brief commit, the fixture
correction, then the report. Any later commit after the code/test head above
changes only files under `reviews/`; final-head
workflow results are recorded in draft PR #9. Second passes use reruns of the
same run IDs. Normal pre-push checks remain enabled; no merge, rebase, force push
or protected-path edit. The closing scan prints
`Remaining .work files over 500 MB: []`.

## Owner decision: plain question first (round 12)

**Done — read:** implements `briefs/19-review-fixes-12.md`. Every new approval
starts with the service's plain-English `question`, then `operation_id` and the
complete, unchanged `description`. Claude passes all three unchanged. This lives
in brief 18's shared `common.approval_input()` and `definitions.APPROVAL`, so
Chrome (brief 20) will use the same format. No Chrome implementation is claimed.

- Base `engine.py` stores/hashes the complete approval and rejects an altered or
  missing question with `stale_approval` before any send/delete. Adapter preparation
  now returns `(question, description, payload)`; `adapters.py`, `testapp.py` and
  the adapter instructions document it. Local repair operations also get a question.
- Base `common.py`, `protocol.py`, `proxy.py` and `cli.py` preserve question-first
  presentation in socket JSON, MCP text/structured results and CLI output, including
  stored approvals after restart. Canonical hashing/storage serialization stays
  unchanged. The proxy also preserves `stale_approval` for a removed question.
- Mail `questions.py` and `adapter.py` build the question from preparation facts:
  each recipient as name plus real address (address alone when there is no name);
  To/Cc/hidden Bcc; subject as written; caller
  text line count; quote/forward indicators; attachment names; named deletions in
  both modes; empty-folder deletion; both unsubscribe methods; setup probes and
  repairs. Control/bidi/backslash escaping happens once through shared `visible()`.
  Full recipient lists, text, targets and attachment facts remain below it.
- Tool definitions, generated Mail/testapp MCP catalogues and `docs/control/TOOLS.md`
  explain unchanged submission including `question`; generated-artifact check passes.

**JUDGMENT-CALL — read, within the approved owner decision:** questions list the
first three recipients per group, attachments and deletion targets, then `and N more`.
Individual summary names retain up to 80 visible characters, delete subjects 120,
then an ellipsis; escapes remain whole. For people, only the display name is
shortened: the real address always follows it whole, so a long lookalike name
can't push the address out of the sentence (added by the package lead at the
lead's request after round 12). The send subject is never shortened. A
4,096-visible-character question cap and the existing whole 16 KiB cap refuse the
entire approval before reservation. Unlimited summaries or cutting the subject/body
were rejected. Changing these bounds later costs a constant/helper, regeneration
and regression expectations. Line counts use `splitlines()` on caller text only;
quotes, forwards, saved draft text and signatures remain separate disclosed facts.

**Tests — run:** new Mail `PlainQuestions12` methods in `test_review_fixes_12.py`:

- `test_round12_send_many_groups_names_fallback_and_attachments_keep_full_fields`
- `test_round12_lookalike_names_always_show_their_real_address` (added after round 12: "Mom" with a stranger's address, a 200-character lookalike name, a bidi name; send, delete and unsubscribe sentences show the real address)
- `test_round12_controls_bidi_and_backslashes_escape_once_without_cutting_escapes`
- `test_round12_reply_quotes_and_both_forwards_describe_generated_content`
- `test_round12_delete_both_modes_many_messages_and_empty_folder`
- `test_round12_unsubscribe_mailto_and_one_click_list_or_sender`
- `test_round12_mail_changed_and_missing_question_never_execute`
- `test_round12_complete_question_and_description_share_limit_no_reservation_on_overflow`
- `test_round12_onboarding_and_mail_repair_questions_first`

New `ServerQuestions12.test_round12_real_servers_tampered_or_removed_question_no_send_or_delete`
checks Dovecot message survival and zero scripted-SMTP arrivals. New shared-base
`ApprovalQuestions` methods in `test_approval_questions.py`:

- `test_question_required_first_escaped_and_counts_toward_exact_limit`
- `test_testapp_changed_and_removed_question_never_send_or_delete`
- `test_question_first_after_restart_socket_cli_and_mcp_text_serialization`
- `test_repair_question_is_stored_first_without_resubmission`

The baseline had no question field/schema or presentation support; these assertions
would fail there. Existing header guards still refuse caller-written controls/bidi;
helper tests cover their escaping and real incoming MIME tests cover derived bidi.

**Existing base tests changed, and why — read:**
`Record.test_record_size_is_independent_of_body_and_attachment` adds the question
bytes to its exact-16-KiB template; all size/privacy assertions remain.
`Operations.test_service_refuses_caller_paths_and_descriptions_do_not_authorize_reuse`
adds the question to its hand-built mismatched approval, retaining both no-arrival
assertions. `Integration.test_real_mcp_stdio_list_prepare_send_attachment_save_and_hooks`
keeps all earlier assertions and additionally checks the new field order in actual
MCP structured content, text content and the advertised input schema. No earlier
test is weakened, skipped or deleted. All 145 earlier Mail methods remain.

**Verified — run, last commit changing code/tests `aa706568a377ed080cc170e32a2f53f019007846`:**

| Workflow / pass | Exact relevant output |
| --- | --- |
| [Mail 42407620884, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42407620884/attempts/1) | `Ran 62 tests in 51.532s`; `Ran 154 tests in 502.872s`; `OK`; `Control base suite PASS`; `Control Mail suite PASS` |
| [Mail 42407620884, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42407620884/attempts/2) | `Ran 62 tests in 41.726s`; `Ran 154 tests in 467.777s`; `OK`; `Control base suite PASS`; `Control Mail suite PASS` |
| [Independent base 42407620899, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42407620899/attempts/1) | `Ran 62 tests in 37.072s`; `OK`; `Control base suite PASS` |
| [Independent base 42407620899, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42407620899/attempts/2) | `Ran 62 tests in 40.012s`; `OK`; `Control base suite PASS` |

The complete base suite (62 tests) and Mail suite (154 tests) pass; both workflows
print `Generated artifacts match definitions`. Mail retains all prior crash/kill-9
cases. Boundary also passed [Boundary 42407620887](https://github.com/Ares-Empire/AresOS/actions/runs/42407620887); its workflow and
policy were not edited, and brief 18b remains outside this run's work.

Local checks before each push:
`python3 control/generate.py --check` → `Generated artifacts match definitions`;
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py`
→ `Python syntax OK: 82 files`, `Ran 38 tests`, `OK`. This reused helper parses
all `control/**/*.py` and runs every direct plain-Python Mail TestCase class.
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest test_operations test_record test_crashes test_approval_questions -v`
→ `Ran 36 tests`, `OK`; record growth remains 4,078 bytes for both tiny and
maximum-body/25-MiB sends, and 5,560 bytes for the typical three-recipient send.
`git diff --check` passed. Local Python was 3.14.6 with the existing worktree vendor
cache; Linux/socket/MCP and real-server qualification comes from CI, not the Mac.

**Push discipline / scope — read:** the first push includes the pre-existing brief
commit `33b5ae8d` and code/tests. Any later commit in this round changes only files
under `reviews/`; final-head run IDs and both attempts are recorded in PR #9 after
the report push. Second passes use `gh run rerun`, not another push. After this
round the package lead changed `questions.py` and its tests at the lead's request
(names always with their real address); that commit's runs, both workflows and both
passes, are recorded in PR #9, and its local checks (39 plain-Python Mail tests,
`test_operations test_record test_crashes test_approval_questions`, generated-artifact
and syntax checks) passed before the push. Normal push
verification is retained; no `--no-verify`, force push, rebase or merge. No workflow,
protected review, OS, mod or protected design/plan file was edited. No file left
in `.work/` exceeds 500 MB; no large download or extraction was made this round.

**Not verified / PLAN-GAP / open questions:** no new plan gap. Real phone/terminal
approval rendering and the account/provider gates listed below still need the owner;
no Claude session, real account or real delivery was used. The owner decision keeps
Claude Code's own approval prompt, now with a plain question first and details below.

## Review fixes, round 11

**Done:** implements `briefs/19-review-fixes-11.md` against
[SECURITY-REVIEW-4.md](SECURITY-REVIEW-4.md). Round 10's preservation rule stays:
no recovery MOVE, STORE or EXPUNGE, no approval operation, and no automatic retry.

- **Blocking — undeliverable filing notices:** `mail/filing.py` now persists a
  compact warning with filing id, affected-message count, at most three folder
  names of 64 characters (ellipsis for a longer name), and an `and N more` count.
  It contains no message references or location arrays. The immediate partial
  result adds only the first bounded location page and its cursor. New
  `mail_filing_locations` returns every stored source, last-known destination,
  observed reference and scan-completeness value through immutable pages bound
  to the filing id. Normal records stay structured. A record larger than a page
  uses ordered, lossless JSON fragments; concatenate by message_index/offset,
  then JSON-decode once. Location content is at most 12 KiB per page, leaving
  room under the shared 48 KiB result and 6 MiB wire limits.
- **Many outstanding notices:** only the newest three are repeated. The response
  counts the rest and points to `mail_filing_notices`, which pages all outstanding
  notices without dropping or acknowledging any. Its cursor binds the current
  notice set; acknowledgment invalidates it. Acknowledgment keeps exact location
  pages available, including after restart.
- **Should-fix — display escaping:** returned notices, acknowledgment results,
  structured location records and reconstructed oversized records use the audit
  log's `visible()` escaping. Raw internal references remain unchanged. The
  encoded Message-ID containing U+202E and a bidi-bearing destination both have
  regressions. Old full-detail notices remain readable as compact summaries;
  their exact details are available through the same location read.
- **Bounded audit delivery:** filing audit events now carry the filing id, state
  and count instead of copying the whole intent. Adapter start/end events keep
  bounded filing metadata instead of repeating large input references. Exact
  references and scan results remain durable in the intent. Historical filing
  audit rows get the same compact display without rewriting their stored data.
- **Base changes and scope:** `engine.py` changes only the shared bounded notice
  section, the escaped compact acknowledgment return, and the display of legacy
  filing audit payloads that could otherwise hide those notices behind a size
  error. `definitions.py` bounds and documents the notice section and paging routes.
  Mail definitions, generated CLI/MCP artifacts, `docs/control/TOOLS.md` and
  `control/README.md` document both new reads and fragment reconstruction. No
  workflow, `control/tests/`, OS, mod or protected design/plan file changed.

**Tests:** six new plain-Python methods in
`control/mail_tests/test_review_fixes_11.py`; the large-case tests invoke real
Engine/Mail adapter, role resolution, selection, fetch and MIME parsing with an
in-memory IMAP command substitute. The full Linux suite also retains all existing
scripted TLS frontend / real Dovecot and GreenMail regressions.

| Finding / behavior | Regression method (`FilingNotices11`) |
| --- | --- |
| Twenty identical messages with long Message-IDs: immediate result, notice, every audit page, later-day empty log, pending and Mail read fit; following all pages returns every stored record and observation exactly once | `test_review11_twenty_identical_messages_long_ids_deliver_and_page_exactly_once` |
| Same through 4,000 identical messages, including the complete per-message observation reports | `test_review11_four_thousand_identical_messages_deliver_and_page_exactly_once` |
| Encoded bidi Message-ID: raw value stays internal, pages escape it; bidi destination escaped in log notices, pending, following Mail results and acknowledgment; COPY preserves originals and copies | `test_review11_encoded_bidi_id_is_escaped_in_notices_and_location_pages` |
| 150 unacknowledged notices with long Unicode names: newest three plus accurate remainder, all 150 reachable once, errors remain bounded, acknowledgment invalidates the notice-set cursor, restart loses none | `test_review11_many_notices_are_bounded_newest_first_and_all_remain_reachable` |
| Old oversized notice and audit payloads display compactly; detail remains paged and escaped, raw intent unchanged after acknowledgment | `test_review11_legacy_large_notice_is_compact_escaped_and_details_stay_readable` |
| Oversized Unicode/bidi references survive restart and fragment reconstruction; cross-filing, negative, past-end and malformed cursors refuse | `test_review11_location_cursors_are_filing_bound_and_jumbo_references_survive_restart` |

**Changed earlier expectation:** `ReviewFixes10.assert_notice`, used by its four
partial-filing server regressions, selects the notice by filing id instead of
assuming that the newest notice is the last UUID-sorted entry. Every equality,
exact-location, preservation, audit-outcome, zero-approval and no-recovery assertion
remains. No test is weakened, skipped or deleted. The small existing cases still
receive their complete structured locations in the first page; their location
assertions did not change.

**Verified / run — local:** before each accepted push,
`python3 control/generate.py --check` prints `Generated artifacts match definitions`;
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py`
AST-parses every `control/**/*.py` (`Python syntax OK: 79 files`) and runs every
direct plain-Python Mail TestCase class (`Ran 30 tests in 2.053s`, `OK` on the code
batch). The existing ignored round-10 portable dependencies are reused; nothing
was installed. `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/tests:.work/round10/vendor python3 -m unittest test_operations test_record test_crashes -q`
runs the portable base classes: `Ran 32 tests`, `OK`. Linux-only file-policy,
installed-service and integration coverage is provided by the full workflows.
`git diff --check` is silent.

Two early local development invocations failed before pushing: the initial new
fixture checked the control-only envelope instead of `data.notices` (four errors
in five tests), and a 28-test invocation lacked cryptography on its PYTHONPATH
(one import error). Corrected fixture channel assertions and reuse of the existing
workspace vendor directory resolved these; they are not counted as passing runs.

The local compatibility probe executes the reviewed `410cb8e8` filing and Engine
notice methods from `git show`, without switching the worktree. With twenty long-ID
messages it reports `ok=False, error=result_too_large, response_bytes=630785`;
with 4,000 identical messages it reports
`ok=False, error=result_too_large, response_bytes=8222814, exceeds_wire=True`.
The same current adapter probes reconstruct and compare every stored location,
with maximum serialized response sizes:

| Probe | Filing result | Exact-location page | Owner log | Pending | Mail read |
| --- | ---: | ---: | ---: | ---: | ---: |
| 20 long-ID identical messages | 7,484 bytes | 6,900 bytes | 2,838 bytes | 653 bytes | 5,521 bytes |
| 4,000 identical messages | 8,367 bytes | 7,779 bytes | 2,841 bytes | 653 bytes | 1,348 bytes |

These are in-memory adapter-path measurements; the test does not claim a real
provider run. Both cases preserve all mail and issue only the first requested
MOVE before role drift stops the batch. Fragmented observation detail takes 120
and 1,380 pages respectively, including the first page returned by the action.

**Verified / run — last code/test commit `bb39b3009961fb6ae21a1b14788017442ea78cdc`:**

| Workflow / pass | Exact relevant output |
| --- | --- |
| [Mail 42403060003, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42403060003/attempts/1) | `Ran 58 tests in 51.934s`; `Ran 145 tests in 507.784s`; `OK`; `Control base suite PASS`; `Control Mail suite PASS` |
| [Mail 42403060003, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42403060003/attempts/2) | `Ran 58 tests in 37.498s`; `Ran 145 tests in 455.488s`; `OK`; `Control base suite PASS`; `Control Mail suite PASS` |
| [Independent base 42403059976, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42403059976/attempts/1) | `Ran 58 tests in 50.730s`; `OK`; `Control base suite PASS` |
| [Independent base 42403059976, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42403059976/attempts/2) | `Ran 58 tests in 59.661s`; `OK`; `Control base suite PASS` |

Both Mail passes run `bash control/ci/mail/run.sh`: artifact check, all 58 base
tests and all 145 Mail methods. Each new method prints `... ok`; both passes also
print `Mail delete kill-9 cases: 26; unnamed Deleted messages survive`,
`Mail send kill-9 cases: 45; no repeated SMTP DATA`, and
`Mail reservation/repair kill-9 cases: 16; no SMTP during repair/restart`.
The independent base workflow runs the whole `bash control/ci/test.sh` in pinned
Fedora twice. All four attempts report this exact code head and success through
the GitHub run-attempt API. Every pass prints `Generated artifacts match definitions`.

Any commit after `bb39b300` changes only files under `reviews/`. Both passes on
the final report head are recorded in [draft PR #9](https://github.com/Ares-Empire/AresOS/pull/9).
The code-head [boundary run 42403059923](https://github.com/Ares-Empire/AresOS/actions/runs/42403059923)
also passed. Boundary policy and its intermittent vsock issue remain the lead's;
no boundary files or assertions were changed or investigated.

**JUDGMENT-CALL / read:** the owner bullet above now describes a short warning
with exact locations on request. Bounded pages and JSON fragments preserve every
old observation instead of dropping detail; identical wire bytes can still produce
large, repetitive reports and many page reads. Unlimited repeated reports were
rejected because they suppress their own warning. Changing the display/paging
choice later affects only filing views and descriptions. The accepted round-10
transient-role timing window and all earlier owner decisions remain unchanged.
**PLAN-GAP:** none added. **Not verified / assumed:** real-provider behavior,
terminal/phone rendering, practical use of very large observation reports, and the
earlier owner checks still need the owner. No screenshot is claimed: this is
protocol/adapter coverage, not a rendered application. **Open questions:** the
existing owner decisions; no new mid-run answer required.

**Push discipline / run:** the two existing lead commits (`49a5baec`, `bf00fc37`)
went with the first accepted code/test batch. The first push command was rejected
remotely with `fatal error in commit_refs_rules`; it started no workflows. Normal
retry succeeded, including the legacy-audit display fix. The second accepted push
changes only this report. Second passes use `gh run rerun`, without extra pushes.
The two accepted pushes create six distinct workflow IDs (Mail, base, boundary per
head), plus the required Mail/base rerun attempts; final-head results belong to
the PR body. Every push keeps normal privacy verification; no force push, rebase,
merge, host installation, Gradle daemon or real-account access. Scope check prints
`Scope check PASS: no protected path, base test or workflow changed`.
The closing worktree scan prints `Remaining .work files over 500 MB: []`.

## Review fixes, round 10

**Done:** implements `briefs/19-review-fixes-10.md` against
[SECURITY-REVIEW-3.md](SECURITY-REVIEW-3.md). This section supersedes round 9's
filing rollback behavior and judgment call; its other fixes remain unchanged.

- **Finding 1 — unsafe MOVE recovery:** `mail/filing.py` retains the prechecks,
  durable pre-action intent, exact COPYUID mapping and post-command role check.
  Role drift stops the batch with `partial`. There is no return MOVE, recovery
  STORE or EXPUNGE. All batch members, including untouched messages, are included
  in the location report. New destination UIDs come from COPYUID; observed
  references include folder, UIDVALIDITY and UID. Missing COPYUID or a failed
  scan remains partial and distinguishes observations from last-known locations.
- **Finding 2 — last surviving COPY:** copies stay where the server put them.
  The service never expunges a copy, even if another client removed the original.
  The warning says the original could not be verified rather than claiming it
  remained present. Cleanup is ordinary named `mail_delete` with owner approval.
- **Owner notice:** the same plain-language warning appears in the result and
  `pending.notices` on each following Mail result. The owner's `aresos log` also
  repeats outstanding notices, including on later days. Notices survive restart;
  `mail_notice_ack` takes the filing_id as operation_id and acknowledges only the
  warning. No approval operation is created. Acknowledgment cannot resolve a
  partial/unknown approved operation or move/delete anything.
- **Should-fix — interrupted reporting:** `locations()` catches production
  transport `Uncertain` as well as IMAP errors, retains all observations collected
  so far with `scan_complete=false`, and persists the final partial outcome and
  notice together. A handled connection loss leaves no started intent. The
  existing deliberate process-crash test still leaves visible started intent;
  restart never retries or recovers it automatically.
- **Descriptions:** `mail/definitions.py`, generated tools and `docs/control/TOOLS.md`
  describe preservation, notices, acknowledgment and approved cleanup.
  `control/README.md` describes the same behavior and remaining timing window.

**Tests:** new methods are in `control/mail_tests/test_review_fixes_10.py`.
All server regressions invoke Engine/Mail through the existing scripted TLS IMAP
frontend over pinned real Dovecot storage. No real account or provider is used.

| Finding / behavior | Regression method |
| --- | --- |
| Trash reassigned to emptied source after MOVE; source replaced before the former recovery point; COPY original externally removed before post-check. Each preserves the surviving message in the exact destination, preserves unrelated Deleted mail, reports partial with matching notice/log text, and uses zero approval operations or recovery commands | `ReviewFixes10.test_review10_review_reproductions_preserve_survivors_with_exact_locations_and_notices` (three cases) |
| Drafts reassigned after COPY: both original and new copy remain, exact references and plain-language text identify both; no EXPUNGE | `ReviewFixes10.test_review10_copy_race_reports_preserved_original_and_copy_without_expunge` |
| Frontend sends BYE during location scan after the first exact observation; production abort becomes Uncertain, partial observations and final outcome persist | `ReviewFixes10.test_review10_connection_loss_during_location_scan_persists_partial_observations` |
| Batch stops after its first race; both moved and untouched members have exact observed locations; only one MOVE issued | `ReviewFixes10.test_review10_batch_stops_after_race_and_reports_untouched_messages` |
| Transient Trash designation before command and removed before post-check; intended target remains, state done and no recovery or notice | `ReviewFixes10.test_review10_transient_role_round_trip_is_done_without_recovery` (MOVE and COPY) |
| Plain-Python context-manager connection loss preserves observations and last-known COPYUID reference | `FilingReporting10.test_review10_scan_retains_observations_when_transport_raises_uncertain` |
| Durable notices have no approval operation, survive restart and later-day log paging, are scoped to Mail and disappear only after acknowledgment | `FilingReporting10.test_review10_notices_are_separate_from_approval_operations_and_survive_next_day` |

**Changed earlier expectations:** only
`ReviewFixes9.test_review9_role_races_undo_move_and_copy_for_trash_drafts_archive`
changes existing assertions: all twelve Trash/Drafts/Archive × MOVE/COPY × before/after
command cases now expect partial and preserved target messages, with originals
remaining for COPY, rather than refused and automatic recovery. The plain-language
warning and intent state expectations change accordingly. Exact bytes, unrelated
Deleted preservation, source/target intent and zero approval assertions remain,
and every case now also checks the persistent warning. The historical method
name is retained for traceability. No other earlier assertion changes. In particular,
`test_review9_failed_undo_and_missing_copyuid_are_partial_with_exact_observed_locations`,
`test_review9_stable_roles_complete_and_uidplus_is_required_before_mutation`, and
`test_review9_filing_crash_leaves_visible_intent_and_restart_never_repeats_or_undoes`
are unchanged; the first now verifies partial preservation without reaching its
old failure hooks. Stable ordinary moves/copies still end done.

**Base files changed and why:** `engine.py` extends the existing pending/log and
notice_ack paths with durable non-approval filing notices in `notice:` records;
this avoids inventing an approval for a free action. `definitions.py` adds optional
notice output to owner pending/log schemas; Mail notice_ack accepts its notice
result as well as the original operation result. Generated control/Mail tool schemas
and tool documentation stay in sync. The scripted frontend adds an opt-in BYE hook
for actual connection-loss tests. No `control/tests/`, workflow, OS or mod file changed.

**Verified — last code/test head `58391d9ed5c85f6e502294afe0fe94eb63517c40`:**

| Workflow / pass | Exact relevant output |
| --- | --- |
| [Independent base 42397927553 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42397927553/attempts/1) | `Ran 58 tests in 50.395s`; `OK`; `Control base suite PASS` |
| [Independent base 42397927553 attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42397927553/attempts/2) | `Ran 58 tests in 49.369s`; `OK`; `Control base suite PASS` |
| [Mail 42397927554 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42397927554/attempts/1) | `Ran 58 tests in 39.201s`; `Control base suite PASS`; `Ran 139 tests in 470.541s`; `OK`; `Control Mail suite PASS` |
| [Mail 42397927554 attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42397927554/attempts/2) | `Ran 58 tests in 51.752s`; `Control base suite PASS`; `Ran 139 tests in 503.196s`; `OK`; `Control Mail suite PASS` |

Both base passes run the whole brief-18 suite from the merged starting head,
now 58 tests. Mail also runs this whole suite before its 139 Mail methods
(132 earlier plus seven round-10 methods). The corrected-head [boundary run 42397927555](https://github.com/Ares-Empire/AresOS/actions/runs/42397927555)
also passes (hostile programs with and without seccomp, and coding policy/user isolation).
Both Mail passes print `Generated artifacts match definitions` and every new
round-10 method plus all twelve revised round-9 cases print `... ok`. Both retain
`Mail delete kill-9 cases: 26; unnamed Deleted messages survive`,
`Mail send kill-9 cases: 45; no repeated SMTP DATA`, and
`Mail reservation/repair kill-9 cases: 16; no SMTP during repair/restart`.
No cancelled or failed run counts as green evidence. Workflow second passes are
reruns of their original run IDs, with no additional push.

**Initial container failure, fixed without changing the assertion:** on
`8381156b48d19906123d01ff3ce83dce00f9ae8e`,
[Mail 42397016202 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42397016202/attempts/1)
printed `Ran 58 tests in 51.646s`, `Control base suite PASS`, then
`Ran 139 tests in 500.887s`, `FAILED (failures=1)`. The COPY-original-removed
fixture had opened the external client's source read-only, so it never removed
the original. The empty-source preservation assertion caught it. Commit
`58391d9e` changes only that new fixture to select read-write and adds an immediate
server UID-absence assertion; the existing assertions and all production code
remain unchanged. All other 138 methods passed, including the other two
reproductions, the actual BYE scan and all twelve revised round-9 cases.
Earlier base [42397016189 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42397016189/attempts/1)
(`Ran 58 tests in 46.378s`) and
[attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42397016189/attempts/2)
(`Ran 58 tests in 50.826s`) both printed `OK`, `Control base suite PASS`;
[boundary 42397016219](https://github.com/Ares-Empire/AresOS/actions/runs/42397016219)
also passed. These earlier passes are not substituted for the corrected-head
checks above. The fixture failure costs one extra push and three workflow IDs
beyond the planned two-push/six-ID batch.

**Local checks:** `python3 control/generate.py --check` prints
`Generated artifacts match definitions`. AST parsing every `control/**/*.py`
prints `Python syntax OK: 78 files`. All direct `unittest.TestCase` classes in
`control/mail_tests/test*.py` run locally with
`PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/check-local.py`:
`Ran 24 tests in 0.241s`, `OK` (timing from the first complete local pass).
`git diff --check` prints nothing. These commands run again before the report push.
An initial local invocation reported two errors: missing host cryptography and a
new test looking for Mail notices in the control-only result envelope. Both were
resolved before the first push: test dependencies live only in ignored
`.work/round10/vendor`, and the test checks the Mail envelope and owner log output.
No system software or runtime dependency changed. Linux workflows use the unchanged
pinned dependency lock; local cryptography 46.0.3/jsonschema 4.25.1 are only portable
pre-push checks, not container qualification.

The local baseline check
`PYTHONPATH=control:control/mail_tests:.work/round10/vendor python3 .work/round10/baseline-check.py`
loads only `filing.py` from `5c93fbe0` into an isolated module and runs the new
interrupted-scan regression: it prints `FAILED (errors=1)` with the uncaught
`Uncertain`, then `Baseline 5c93fbe0 reproduction confirmed: Uncertain escapes locations()`.
The same regression passes on this code. This is deliberate red/green evidence,
not a passing baseline claim. A first scratch invocation omitted PYTHONPATH and
failed at import; the command above is the corrected, actually executed check.

**JUDGMENT-CALL:** if a role moves to the target and back between MOVE/COPY and the
post-check, equal snapshots cannot detect it. The result can be done with mail in
the intended target; the target has no protected role at the end and nothing is
lost. Preserve-and-report replaces automatic undo: an undo has its own uncloseable
identity/role race and can lose the last copy. Disabling free filing was rejected
by the lead's explicit rule. Changing the choice later is confined to filing and
its reference/notice contract. This replaces round 9's undo judgment call above.

**Not verified:** real-account setup and owner/recipient-program presentation remain
the checks listed above. Automated protocol tests establish message preservation,
not how the warnings feel in daily use. No screenshots apply to this service change.

**PLAN-GAP:** none new. Source disappearance by another client is reported honestly;
this service cannot claim that an external client kept the original. A hard process
crash still leaves the deliberate unfinished audit record, as before. The lead's
merge of main was already in the starting head; the earlier merge-conflict note is
historical, not a current blocker.

**Open questions:** no new question; the owner decisions above remain for merge.
No file in `.work/` exceeds 500 MB. This round batches the two pre-existing local
lead commits with the code/test push. Later commits in this round change only files
under `reviews/`; final-head runs are recorded in draft PR #9 after the report push.

## Review fixes, round 9

Historical verification below; round 10 replaces its automatic-undo behavior.

**read — Done:** implements `briefs/19-review-fixes-9.md` against
[SECURITY-REVIEW-2.md](SECURITY-REVIEW-2.md). The original security review's
closed header/audit findings remain covered by their earlier tests.

- **Finding 1 — role race:** `mail/filing.py` records durable intent before remote
  work, retains the prechecks and reads SPECIAL-USE roles after every forward
  MOVE/COPY. Any role-map change rolls back the attempted batch using only exact
  one-message COPYUID mappings: MOVE back to the original source folder and
  UIDVALIDITY, or STORE Deleted plus UID EXPUNGE on only the created copies.
  Returned moves have newly assigned source UIDs, verified by fetching their exact
  bytes; IMAP cannot restore the original UID. Both actions require live UIDPLUS;
  moving also requires MOVE. Missing COPYUID, missing/changed source or destination,
  failed undo or unavailable live verification returns partial, never done.
  Partial/refused results carry observed folder/UID references, per-message source,
  and scan completeness under untrusted_content. Reporting searches never authorize
  undo. Intent and final outcome remain in SQLite/audit; interrupted intents remain
  visibly started, with no restart undo or retry.
- **Finding 2 — root separators:** `mail/roles.py` records each required and optional
  root's actual LIST separator. Required names and separators bind fresh checks;
  Drafts/Trash ancestry and folder protections use that root's separator. Owner
  account_folders refresh retains old protected roots with their own separators.
  Pre-round-nine setups without required-root metadata refuse changes until owner
  refresh; that refresh resolves each old root from LIST or refuses if it is gone.
  `mail_tests/support.py` now builds Dovecot accounts through the production role
  resolver; bare GreenMail remains deliberately incomplete for the existing raw
  server-qualification probes. `test_changes.py` resolves the guard frontend roles
  after it adds them. Existing tests exercise recorded per-root metadata; no earlier
  assertion changed. Legacy remembered roots are also corrected from each root's
  LIST row during owner refresh, rather than retaining previously stamped separators.
- **Finding 3 — private blob download:** `blobs.py` durably records service-assigned
  origins beside hash-verified immutable bytes. Publication/crash without origin
  metadata grants no export permission. Every app's download path requires an
  explicit export; caller imports, composition/rebuilt parts, draft body/HTML,
  quotes and private wire copies cannot be downloaded by hash. Mail composition
  still accepts hashes only with caller-import origin plus recorded caller metadata.
  Ordinary non-draft attachment_save explicitly exports the original bytes.
  Hash deduplication retains each trusted origin grant; only a service export path
  can add export rights, never a caller-supplied hash or metadata object.
- **Should-fix — historical status:** live evidence errors now appear separately as
  evidence_error; recorded operation, approval, outcome and stages remain available.
- **Should-fix — approved headers:** composition strips surrounding spaces/tabs
  from subjects and parsed display names before freezing approval. Inner controls,
  encoded-word attacks and the independent final decoded-wire equality checks keep
  their existing strict checks. The low-level strict header/address validation
  tests remain unchanged.

**read — regression mapping:** all new methods are in
`control/mail_tests/test_review_fixes_9.py`; prefixes below name their classes.

| Finding / behavior | Regression method |
| --- | --- |
| Trash, Drafts, Archive reassigned immediately before command and immediately after it; MOVE and COPY; real source restored or exact copies removed; unrelated Deleted survives; no approval operation | `ReviewFixes9.test_review9_role_races_undo_move_and_copy_for_trash_drafts_archive` (12 boundary cases) |
| Failed MOVE undo, failed copy expunge, omitted COPYUID, source gone, destination gone; partial with actual observed folder/UID locations | `ReviewFixes9.test_review9_failed_undo_and_missing_copyuid_are_partial_with_exact_observed_locations` |
| Ordinary filing done; both actions refuse without live UIDPLUS before any mutation | `ReviewFixes9.test_review9_stable_roles_complete_and_uidplus_is_required_before_mutation` |
| Crash immediately after remote MOVE leaves durable started intent; reopen neither repeats nor undoes | `ReviewFixes9.test_review9_filing_crash_leaves_visible_intent_and_restart_never_repeats_or_undoes` |
| INBOX `/`, Trash/Drafts `.`; Trash.Child free filing refused, unmarked/unflagged Drafts.Child source/all parts cannot export/attach/forward/move; same after owner refresh; delimiter drift refuses | `ReviewFixes9.test_review9_per_root_separators_protect_trash_and_unmarked_draft_children_after_refresh` |
| Every internal origin and caller imports refuse download across apps and restart; missing old metadata refuses; export lacks import rights; shipped settings exclude testapp | `BlobOrigins9.test_review9_all_internal_origins_refuse_download_across_apps_and_restart` |
| Long saved draft → mode=draft → generated_parts[0].sha256 → real testapp Proxy.file_save notes.txt: refused, no file/SMTP; ordinary Mail part saves exact binary bytes | `ReviewFixes9.test_review9_long_draft_hash_cannot_be_saved_by_testapp_and_ordinary_export_is_exact` |
| Send, remove Trash role, status still returns identical approval/stages and separate evidence_error | `ReviewFixes9.test_review9_operation_status_retains_approval_and_stages_when_trash_role_is_removed` |
| Leading/trailing spaces and tabs, normalized display names and long folded subject: approved decoded values equal received wire values | `ReviewFixes9.test_review9_header_whitespace_normalizes_before_approval_and_long_folded_subject_sends` |

**read — server qualification:** scripted TLS LIST/command timing runs through the
existing test-only `imap_guard_fixture.py` frontend over real pinned Dovecot
storage; namespace separators/role flags are explicitly scripted LIST data, not a
claim about Dovecot's default namespaces. Command hooks run under its frontend lock.
Copy removal/return, source UIDVALIDITY, exact bodies and unrelated Deleted messages
are checked on the server. SMTP checks use the isolated non-relaying TLS sink.
The shared-store regression is plain Python; the download reproduction uses the
actual Proxy/Client/Engine transfer framing on a private Unix socket. Existing
base and Mail proxy tests still qualify distinct OS users and the installed daemon.
No real account or model was used.

**read — base files changed and why:**

- `control/aresos_control/blobs.py`: origin metadata publication, fail-closed legacy
  behavior and origin-gated reads; default writes are internal.
- `control/aresos_control/engine.py`: mark streamed imports as caller imports; gate
  both download authorization and actual streaming on export; preserve historical
  status separately from failing live evidence.
- `control/aresos_control/testapp.py` and `definitions.py`: imported-file provenance
  at attachment/revalidation boundaries; an explicit fixture-only export_file
  action promotes only a recorded caller-import snapshot for file-transfer tests.
  It cannot promote a private service hash. file_save describes export-only bytes.
- `control/settings/managed-mcp.json`: remove testapp, leaving control and mail.
  The fixture catalogue remains generated for tests, not a shipped MCP server.
- `control/tests/test_files.py`: the download fixture now explicitly creates an
  export; its original size/hash/download/refusal assertions remain intact.
- `control/tests/test_integration.py`: both existing successful download flows first
  call the fixture's explicit imported-file export. Original 25 MiB framing,
  immutable-byte, MCP, collision and permission assertions remain intact.
- `control/tests/test_record.py`: its preloaded attachment is tagged caller_import
  instead of internal; the independent-record size/privacy assertions are unchanged.
- `control/generated/testapp-tools.json`, `control/generated/cli-help.txt`,
  `control/generated/mail-tools.json`, `docs/control/TOOLS.md`: regenerate from the
  changed descriptions/results and fixture export action. Ask rules remain identical.
  `control/README.md` documents origins, filing outcomes, old setup refresh and status.
- `.github/workflows/control-base.yml`: add only workflow_dispatch. PR #9 currently
  conflicts with main, which prevents GitHub pull_request jobs from starting;
  manual dispatch permits exact-branch verification without merging or rebasing.
  All base job steps and assertions stay the same.

**run — last code/test head `d5164a8652278ead9e3c9c4722641f2fbed01f60`:**

| Workflow / pass | Exact relevant output |
| --- | --- |
| [Mail 42389443350 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42389443350/attempts/1) | `Ran 57 tests in 40.642s`; `OK`; `Control base suite PASS`; `Ran 132 tests in 428.924s`; `OK`; `Control Mail suite PASS` |
| [Mail 42389443350 attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42389443350/attempts/2) | `Ran 57 tests in 49.988s`; `OK`; `Control base suite PASS`; `Ran 132 tests in 465.309s`; `OK`; `Control Mail suite PASS` |
| [Independent base 42389466380 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42389466380/attempts/1) | `Ran 57 tests in 49.222s`; `OK`; `Control base suite PASS` |
| [Independent base 42389466380 attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42389466380/attempts/2) | `Ran 57 tests in 47.685s`; `OK`; `Control base suite PASS` |

Both Mail passes run `bash control/ci/mail/run.sh`: pinned containers, generated
artifact check, `bash control/ci/test.sh` (all 57 base tests), then isolated
`python3 -m unittest discover -s control/mail_tests -v` (all 132 Mail methods:
123 earlier plus nine new). Both independent base passes run
`bash control/ci/test.sh` in pinned Fedora 45. Every new round-nine method prints
`... ok`. Existing outputs remain `Mail delete kill-9 cases: 26; unnamed Deleted
messages survive`, `Mail send kill-9 cases: 45; no repeated SMTP DATA`, and
`Mail reservation/repair kill-9 cases: 16; no SMTP during repair/restart`.
No earlier assertion was weakened, skipped or deleted.

Any later commit changes only files under `reviews/`; final-head workflow runs are
recorded in draft PR #9 after that report-only push. One exception, made by the
package lead at the lead's request after this round: `.github/workflows/control-mail.yml`
no longer runs on `push` (only on the pull request and by manual dispatch) and cancels
superseded runs, so each change runs once; a second pass is a rerun of the same run.
It changes no code or test.

**run — local checks:** `python3 control/generate.py --check` printed
`Generated artifacts match definitions`; AST parsing every control Python source
printed `Python syntax OK`; `git diff --check` printed nothing. The portable command
`PYTHONPATH=control:control/mail_tests python3 -m unittest test_review_fixes_7.HeaderRules7 test_review_fixes_8.RoleResolution8 test_review_fixes_9.BlobOrigins9 -v`
printed `Ran 6 tests in 0.017s`, `OK` on the last code/test head.
An earlier `PYTHONPATH=control:control/tests python3 -m unittest test_files test_operations test_record -q`
on the Mac printed `Ran 31 tests in 0.196s`, `FAILED (errors=37)` because Linux
O_PATH and the container's jsonschema dependency are unavailable locally. It is not
green evidence; the complete Linux container runs above are authoritative. No host
software was installed and no Linux-only assertion was changed for this Mac.

**JUDGMENT-CALL — superseded by round 10:** automatic undo was removed because it
has its own role/identity race and can delete the last copy. See the round-10
judgment call and the owner decision above. Origin restrictions mean old
hashes without origin metadata cannot download; make a new explicit export or
caller import rather than guessing old provenance.

**PLAN-GAP / Not verified — read:** merge-conflict resolution against current main
is left to the lead under the explicit no-merge/no-rebase rule. The one-line
workflow_dispatch addition is necessary to verify the independent base job on this
branch. No wider issue hunt or protected-path change was performed. Reports of
concurrent external message disappearance identify observed locations, including an
empty result when the server no longer contains it; they do not invent an exact
location when transport prevents a complete scan. Real-provider role propagation,
crash durability and rollback permission remain owner qualification; no automated
restart recovery is claimed. Earlier owner questions, including the lead's stopping
rule for Claude-written attachments, remain in the owner list above.

**run — earlier iterations (not final-head evidence):**
[42388505712](https://github.com/Ares-Empire/AresOS/actions/runs/42388505712)
on `00d48db7` printed `Ran 57 tests in 45.538s`, `OK`,
`Control base suite PASS`, then `Ran 132 tests in 441.747s`,
`FAILED (failures=1, errors=3)`. All 12 role-race cases, the five partial-undo
cases, mixed separators, normalized headers and historical status passed. The
failures were fixture setup: strict resolve on deliberately incomplete bare
GreenMail (two existing qualification tests), the new proxy's hidden `.work`
caller home, and the new crash test's log limit 20 (maximum is 10). Corrected
fixtures and valid input without changing any assertion. The subsequent migration
regression adds previously remembered roots whose old separator was wrong.

On `698565ee`, base
[42388752113 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42388752113/attempts/1)
printed `Ran 57 tests in 47.899s`, `OK`, `Control base suite PASS`;
[attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42388752113/attempts/2)
printed `Ran 57 tests in 37.794s`, `OK`, `Control base suite PASS`.
Mail push 42388746808 was automatically superseded while pending by manual
42388754581 in the same GitHub concurrency group; that obsolete run was then
cancelled after the known fixture failures. On `b83b8455`, base
[42389329145](https://github.com/Ares-Empire/AresOS/actions/runs/42389329145)
passed; Mail 42389299032 was cancelled when the remembered-root migration fix
superseded it. None of these cancelled runs is claimed as passing evidence.

**run — cleanup and budget:** `git diff --check` printed nothing. The scope check
against starting head `587a50ef` found no change to os/, mod/, frozen review files,
owner/install/emergency/design/plan/feature paths. The only added workflow setting
is the necessary base manual-dispatch trigger described above. The closing size
scan printed `Remaining .work files over 500 MB: []`. No Gradle daemon or host
container was started; no host software was installed. All pushes used normal
verification, with no force push or --no-verify.

Eleven workflow executions were used through code verification, including the
initial fixture failure and three superseded/cancelled runs. This exceeds the
approximate ten-run target; the final report head still requires four full checks,
whose actual IDs/results and total are recorded in the PR body. No assertion or
required repeat was weakened to reduce the run count.

## Review fixes, round 8

**read — Done:** implements `briefs/19-review-fixes-8.md`. This section supersedes
round 7's all-five-role requirement and whole-account optional-role refusal.
`mail/roles.py` requires unique selectable Sent, Drafts, Trash and INBOX, records
optional Junk/Archive roots (including absence or ambiguity), and compares them
independently. Existing accounts use their recorded folder names without guessing.
Onboarding accepts absent or duplicated optional roles; the owner's two-step
`account_folders` records the reviewed mapping without sending a new probe.
`mail_accounts.optional_roles` shows each as `present`, `absent` or `needs_setup`,
with current/recorded roots; an unavailable fresh listing reports `needs_setup`.

`adapter.py` scopes optional-role refusal to actions needing the role or involving
its current/recorded roots and descendants. This includes complete mixed batches,
flags, deletes, folder changes, exports, composition sources, draft saves, send
preflight and local stages. Immutable compositions retain their source reference
so a later role change cannot evade the check. Required-role and historical
Trash/Drafts protection, full draft approval, named deletion and send replay rules
remain. Move/copy accepts exactly one exact `target` folder or explicit
`target_role=junk|archive`; the latter gives the missing-role/server-settings/setup
reason without inferring roles from mailbox names. The catalogue, generated Mail
JSON and `docs/control/TOOLS.md` describe the new behavior.

Reads never require valid optional roles. Default search, thread and correspondent
history exclude every current/recorded Junk root (and Trash as before); explicit folder
search and direct reads remain available. A thread seeded in excluded Junk returns
an empty page, rather than refusing the read.

**read — regression tests** (`control/mail_tests/test_review_fixes_8.py`):

| Test | Evidence |
| --- | --- |
| `test_review8_no_optional_roles_onboard_and_all_ordinary_mail_actions_work` | Owner-only synthetic onboarding with no Junk/Archive; setup records absence; missing-role move/copy gives clear reasons with unchanged server state; ordinary folder create/rename, copy/move, flags, Trash/permanent delete, reply with Sent copy/Answered and saved-draft send work. SMTP receives exactly two messages; replay adds none and the draft stays. |
| `test_review8_duplicate_optional_role_onboards_without_disabling_other_actions` | Duplicate Archive at initial onboarding reports needs_setup; affected filing refuses while the same ordinary actions, deletes, sends and drafts work. |
| `test_review8_duplicate_archive_refuses_only_affected_changes_and_allows_ordinary_actions` | Both Archive roots refuse move/copy in/out and mixed batches, flags, export, composition, deletion and folder changes; existing send/delete approvals and derived-source draft/send preparation refuse with unchanged UID/bytes/flags and no DATA. Drift injected between reference check and UID-command preflight also refuses. Ordinary actions still work; recording a still-duplicate role cannot bypass refusal. |
| `test_review8_moved_archive_refuses_old_and_new_until_owner_records_then_role_move_works` | Same refusal and positive checks after actual Archive reassignment; owner review/record restores explicit Archive filing and ordinary use of the former root. |
| `test_review8_optional_appearance_disappearance_needs_setup_only_for_affected_folder` | Disappearance and later appearance affect only Archive-root changes; statuses change through needs_setup/absent/present and ordinary flags keep working. |
| `test_review8_junk_reads_defaults_exclude_all_current_and_recorded_roots_without_refusing` | Real moved, duplicate and disappeared Junk: search/thread exclude all roots and children, direct/explicit reads work without changing flags/bytes, Junk-seeded threads return zero, correspondents exclude Junk, affected changes refuse and ordinary operations still work. |
| `test_review8_each_missing_duplicate_required_role_still_blocks_setup_and_changes` | All three required roles, each missing and duplicated: onboarding/setup and compose/draft/send/move/flag/delete preflights refuse before mutation; existing send approval stays reserved. |
| `test_review8_optional_absence_duplicates_and_unselectable_do_not_hide_required_errors` | Local resolver checks optional absence/ambiguity/unselectability and retains required-role missing/duplicate/unselectable assertions. |
| `test_review8_legacy_recorded_roots_scope_changes_and_missing_role_reason` | Local compatibility with earlier account records, both changed roots/children, unaffected similarly named folders and precise missing-role instructions. |

**read — earlier test changes:** the round-7
`test_review7_roles_reject_missing_ambiguous_unselectable_and_casefold_flags`
invalid fixture now removes Sent instead of optional Archive; its rejection,
ambiguity, unselectability and casefold assertions remain. Its shared
`configure_roles` helper recognizes the additional actual Dovecot configurations
and sorts duplicate expectations. `onboard_with_frontend` in `test_review_fixes.py` now persists the synthetic
fixture CA before its fresh `mail_accounts` lookup; its full-account equality
assertion and every qualification/cleanup assertion remain. This affects
`test_review_4_missing_exact_probe_or_failed_cleanup_never_qualifies`,
`test_review_4_positive_guard_qualifies_only_after_verified_cleanup` and
`test_review_4_transient_permission_and_generic_refusals_never_qualify`. All other
earlier test methods and all `control/tests/` remain unchanged; the existing Trash/Drafts protection tests run
unchanged. Runner configuration adds only synthetic optional/required role modes,
with readiness still proven by actual LIST responses.

**JUDGMENT-CALL / read:** the replacement role rule is recorded in round 7's
updated judgment call and the owner list above. When source classification is
uncertain, refuse the affected action; never bypass draft, approval, exact-delete
or replay protection. **PLAN-GAP:** none added; earlier owner decisions remain.
**Not verified / assumed:** real account/server settings, terminal/phone approvals,
the seven Claude tasks and recipient `.eml` presentation still need owner checks.
**Open questions:** the existing owner decisions; no new mid-run answer needed.

**run — local checks:**
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests python3 -m unittest test_review_fixes_8.RoleResolution8 test_review_fixes_7.HeaderRules7 test_review_fixes_5.DraftAndTextGuard test_review_fixes_4.RebuildAndGuard test_review_fixes_3.HeaderAndEncoding test_review_fixes_2.LocalMailDetection -q`
(the two new local role tests and 17 earlier codec/guard/header tests) printed `Ran 19 tests in 0.141s` / `OK`.
`python3 control/generate.py --check` printed `Generated artifacts match definitions`;
AST parsing and constructing all fixture configurations printed
`Python syntax and 17 Dovecot fixture configurations OK`; `git diff --check` was
silent. An in-memory comparison loaded the actual `8e0c7bdd` role resolver and
printed `8e0c7bdd refuses required-only roles; current records Junk and Archive absent`
and `Current changed-Archive check permits ordinary folders and refuses both role roots`.
This is local decision evidence, not a server run. Docker printed
`Cannot connect to the Docker daemon`; no host/container installation was attempted.

**run — initial executions / correction:** code/test head `de894c5d9b0ed6db240442a39f1e71ba7c03c66c`:
Mail push [42384373464](https://github.com/Ares-Empire/AresOS/actions/runs/42384373464)
printed `Ran 57 tests in 47.422s` / `OK` / `Control base suite PASS`, then
`Ran 123 tests in 333.345s` / `FAILED (failures=7, errors=7)`.
Mail PR [42384377428](https://github.com/Ares-Empire/AresOS/actions/runs/42384377428)
printed `Ran 57 tests in 65.429s` / `OK` / `Control base suite PASS`, then
`Ran 123 tests in 408.029s` / `FAILED (failures=7, errors=7)`.
The seven new server-test bodies reached their assertions successfully but their
reused round-7 teardown had a class-bound `super()` and failed cleanup. Round 8 now
owns its teardown, resetting actual Dovecot roles before closing its engine/temp
state. Seven existing qualification subtest comparisons also found the new live
account-role lookup lacked the fixture CA after onboarding's temporary TLS patch;
the shared fixture now persists that synthetic trust before comparing the full
account results. No assertion was weakened, skipped or deleted. The initial base
workflow [42384377435 attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42384377435/attempts/1)
printed `Ran 57 tests in 49.415s` / `OK` / `Control base suite PASS`; its
[attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42384377435/attempts/2)
printed `Ran 57 tests in 50.037s` / `OK` / `Control base suite PASS`.

**run — last code/test commit `eb3f7dd2411bbfe87afe1ff03bfdd99f2a16c091`:**

| Workflow / pass | Exact relevant output |
| --- | --- |
| [Mail push 42385029196](https://github.com/Ares-Empire/AresOS/actions/runs/42385029196) | `Ran 57 tests in 50.046s`; `OK`; `Control base suite PASS`; `Ran 123 tests in 346.531s`; `OK`; `Control Mail suite PASS` |
| [Mail PR 42385033899](https://github.com/Ares-Empire/AresOS/actions/runs/42385033899) | `Ran 57 tests in 50.590s`; `OK`; `Control base suite PASS`; `Ran 123 tests in 348.366s`; `OK`; `Control Mail suite PASS` |
| [Independent base 42385033981, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42385033981/attempts/1) | `Ran 57 tests in 44.257s`; `OK`; `Control base suite PASS` |
| [Independent base 42385033981, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42385033981/attempts/2) | `Ran 57 tests in 49.239s`; `OK`; `Control base suite PASS` |

Both Mail passes ran `bash control/ci/mail/run.sh`: generated-artifact verification,
all 57 unchanged base tests via `bash control/ci/test.sh`, isolated pinned servers
and all 123 Mail methods (114 earlier plus nine new; every new method printed
`... ok`). Both printed `Mail delete kill-9 cases: 26; unnamed Deleted messages survive`,
`Mail send kill-9 cases: 45; no repeated SMTP DATA`, and
`Mail reservation/repair kill-9 cases: 16; no SMTP during repair/restart`.
The independent base workflow ran `bash control/ci/test.sh` twice in pinned Fedora.

Any commit after `eb3f7dd2` changes only files under `reviews/`; the final-head
workflow IDs and both passes are recorded in [draft PR #9](https://github.com/Ares-Empire/AresOS/pull/9)
after its report-only push. Twelve workflow executions total (four initial, four
corrected code, four final report) exceed the approximate eight-run target because
of the initial fixture failures. No test was bypassed to meet that target.
Scope check printed `Scope check PASS: no protected path or base test changed`.
The final worktree scan printed `Remaining .work files over 500 MB: []`.
All pushes used normal verification; no force push, merge or host installation.


## Review fixes, round 7

**read — Done / scope:** implements `briefs/19-review-fixes-7.md`, findings
1, 2, 3 and 5 of [SECURITY-REVIEW.md](SECURITY-REVIEW.md). Finding 4 remains
an owner decision below, as the brief directs; no attempt is made to close its
identity race with another non-atomic check. The security review and all earlier
`REVIEW*.md` files are untouched.

1. **Fresh special folders:** `mail/roles.py` resolves unique, selectable current
   Sent, Drafts, Trash, Junk and Archive roles plus INBOX. `adapter.py` compares
   those roles and the delimiter with owner setup before moves/copies, deletes,
   draft save, folder changes, each draft-protection decision and send preflight,
   including Sent evidence, the last pre-DATA check and Sent repair/copy. A
   missing, ambiguous, unselectable or different mapping refuses with the owner
   setup command. `mail_account_folders` is owner-only on `admin.sock`: first
   inspect escaped current roles, then repeat with their `roles_hash`; changed
   proposals refuse, no account re-add or probe mail occurs, and old Trash/Drafts
   roots and their original delimiters stay protected. Onboarding also requires
   complete roles rather than recording an ambiguous/partial configuration.
2. **No draft export:** `mail_attachment_save` refuses every draft part and its
   source before storing export bytes or writing a caller file, using fresh roles,
   the marker and exact-reference IMAP Draft flags. Nested/ancestor provenance is
   inspected too. The error names saving in the owner's mail program and sending
   the draft itself with `mode=draft`. Ordinary received/sent exports retain their
   original bytes after safe inspection. This closes the exact decoded-body route,
   without implementing the deferred ordinary-local-file policy.
3. **Approved headers are sent headers:** `codec.py` refuses encoded-word syntax,
   C0/C1 controls and the brief's listed bidi/invisible characters in authored
   subjects and names; original parsed headers are decoded Unicode before storage,
   and derived formatting characters remain escaped in approval. Names appear
   beside explicit addresses. `guard.py` independently parses the exact wire
   Subject/From/To/Cc, compares decoded subject, display names and addresses against
   the immutable composition, and compares the full SMTP envelope with approved
   To/Cc/Bcc. It shares no builder decisions or helpers. Checks run at composition
   and on the bytes immediately before DATA; mismatch fails without submission and
   cannot submit on replay. Threading headers also reject controls.
4. **Audit trust:** Mail change summaries are fixed service text, with references,
   folder/file names and other external values in structured escaped
   `untrusted_content`. The shared `Store.write` accepts that optional metadata;
   Mail's compact independent-record descriptions also mark external values.
   Brief 18's `engine.py` needs the small stage/file-save/log changes because those
   common paths otherwise turn recipient stage keys, caller paths and historical
   Mail summaries into trusted free text. `control_log` and the CLI preserve the
   marking, including on historical Mail summaries; other apps' stage behavior is
   unchanged. No base test is edited.

**read — tests proving each rule** (`control/mail_tests/test_review_fixes_7.py`):

| Test | Coverage |
| --- | --- |
| `test_review7_real_dovecot_trash_role_change_blocks_old_new_destinations_then_owner_refresh` | Dovecot changes its actual LIST Trash role over the same user storage; move/copy into new and old Trash refuses, server UID/byte/flag state stays unchanged and zero approvals are reserved; owner hash review/record restores ordinary moves; both protected Trash roots refuse free entry; approved delete alone reaches NewTrash. |
| `test_review7_real_dovecot_drafts_role_change_protects_both_sources_and_exports` | Actual LIST Drafts reassignment; old/new unmarked drafts refuse move/copy, attaching source/parts and export, with unchanged server state; old/new roots stay protected after owner refresh and ordinary moves work. |
| `test_review7_missing_ambiguous_roles_and_sent_change_refuse_all_change_preflights` | Missing/duplicate Trash and changed Sent refuse move/copy, compose, draft-save, export, folder create/rename/delete and approved delete/send before mutation/DATA; owner setup cannot record incomplete roles. |
| `test_review7_exact_draft_decoded_body_export_route_real_proxy_no_file_no_smtp` | Compose long draft → save → real proxy export part 1/source refuses and writes no file; reattach missing path fails; no operation or SMTP delivery. |
| `test_review7_draft_html_pdf_marker_flag_and_received_parts_through_proxy` | Every MIME path, HTML, PDF and source refuses for Drafts, a flagged INBOX message and a marked Archive message; no caller file; ordinary received PDF saves byte-exactly and server flags/bytes remain unchanged. |
| `test_review7_headers_reject_security_review_inputs_and_show_derived_names_exactly` | Review's Base64 subject, encoded CR/LF subject/name, RLO authored name and encoded sender/Bcc refuse; reply subject/name decode, derived RLO is escaped, homoglyph name appears with its address and arrives unchanged; derived C0/C1 subjects refuse. |
| `test_review7_wire_subject_bypass_fails_compose_and_before_data_without_replay` | Builder bypass with decoded subject different from approval refuses compose/prepare, fails the send and replay without DATA; bypassing the first check also fails the independent final boundary. |
| `test_review7_hostile_message_id_is_structured_escaped_in_control_and_cli_log` | A hostile Message-ID with instruction text, C0, C1 and RLO is flagged through the real proxy; actual CLI log and cross-app control log show it only in marked escaped fields, never a free-text summary. |
| `HeaderRules7.test_review7_written_headers_refuse_encoded_words_controls_and_formatting` | Every prohibited control/formatting code point in subjects and display names, encoded words, derived-control refusal and literal homoglyph preservation. |
| `HeaderRules7.test_review7_independent_guard_compares_decoded_headers_and_exact_envelope` | Exact decoded Subject, From/To/Cc names and addresses; wrong, missing, extra and reordered SMTP envelope recipients refuse independently. |
| `HeaderRules7.test_review7_roles_reject_missing_ambiguous_unselectable_and_casefold_flags` | Missing, duplicate and Noselect roles refuse; flag matching is case-insensitive. |

The Dovecot fixture reloads fixed disposable-server configurations for role
changes, missing roles and duplicates against the same persisted user mailbox
storage, then restores the default configuration after each such test.
The tests assert Dovecot's LIST flags and actual UIDs/bytes/flags, rather than
mocking the adapter's folder resolver. The GreenMail nonempty guard remains a
test-only serialized frontend over real GreenMail storage; that frontend now
supplies explicit roles for its role-less backend.

**read — required earlier-test setup changes:**
`ReviewFixes2.test_review2_1_saved_draft_and_bcc_sent_refused_through_real_proxy_even_renamed`
and `ReviewFixes3.test_review3_1_export_punctuation_malformed_and_mbox_refused_by_real_proxy`
now assert that draft export refuses/no file exists, then seed an owner-created
file with those exact draft bytes to retain every local-import detection check.
Sent exports and all their original byte/Bcc checks remain.
`ReviewFixes3.test_review3_2_received_two_level_encoded_messages_in_all_composition_modes`
now asserts nested-draft source export refuses and still checks exact original
bytes through raw read; received source exports still check original bytes.
`Changes.test_greenmail_nonempty_guard_and_delivery_during_folder_approval`
keeps its GreenMail backend and every assertion, adding explicit selectable
server-frontend roles at setup. `Changes.test_both_upstream_servers_allow_nonempty_delete_and_are_not_qualified`
seeds the probe directly through owner IMAP because role-less GreenMail now
refuses tool folder creation; all upstream deletion/guard assertions stay.
No test is weakened, skipped or deleted; these are the setup/behavior changes
forced by the new export and complete-role requirements.

**JUDGMENT-CALL / read — folder identity race (finding 4):** folder deletion only
runs where the server refuses to delete a folder that holds mail, so no mail can
be lost. If another mail program renames the approved empty folder and creates a
new empty one with the same name in the same instant, the new empty one is
deleted instead. The alternative is to remove folder deletion from the tools.
This round retains it as the brief directs; removing the action later would
change the catalogue and generated docs and retire its approval path.

**JUDGMENT-CALL / read — draft attachments cannot be saved by Claude:** even a PDF
or other binary attachment of a draft refuses export. The owner uses his mail
program to save it, or Claude sends the draft itself with `mode=draft` under the
existing draft rules. Allowing exports would require reliable decoded-file
provenance and a disclosure policy for reimport; checking names or extensions
was rejected because the review's exact plain-text route defeats them.

**JUDGMENT-CALL / read — required safety roles, optional filing roles (updated round 8):**
Sent, Drafts and Trash remain required and must match owner setup. Earlier Trash
and Drafts folders remain protected after refresh. Junk and Archive can be absent;
only actions needing a missing role refuse. A duplicated, unselectable or changed
optional role refuses changes involving its current or recorded folders and their
children; other actions and reads keep working. Search/thread defaults exclude
current and recorded Junk roots. Requiring all five roles and stopping the whole
account for optional-role drift was rejected by the round-8 brief; silently accepting drift
was rejected because it changes which folder an action affects. Revising the
scope later needs caller descriptions and regression updates; removing remembered
Trash/Drafts protection still needs an explicit migration/provenance decision.
Recording roles does not enable incomplete onboarding.

**PLAN-GAP / read:** the ordinary caller-file authorship question remains open,
as listed for the owner. Finding 4 is deliberately retained as a JUDGMENT-CALL;
no other feature/design gap is pursued in this round.

**Not verified / assumed:** real-account onboarding and role setup, approvals on
terminal/phone, the seven everyday tasks and recipients' `.eml` presentation need
the owner's checks listed above. No real account or model was used.

**Open questions:** the owner decisions above, especially retaining folder
deletion and refusing all draft exports, remain before merge.

**run — local verification:**
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests python3 -m unittest test_review_fixes_7.HeaderRules7 test_review_fixes_5.DraftAndTextGuard test_review_fixes_4.RebuildAndGuard test_review_fixes_3.HeaderAndEncoding test_review_fixes_2.LocalMailDetection -q`
printed `Ran 17 tests in 0.140s` / `OK`. `python3 control/generate.py --check`
printed `Generated artifacts match definitions`; syntax parsing and the six
Dovecot fixture configuration checks printed
`Python syntax and all Dovecot role configurations OK`; `bash -n control/ci/mail/run.sh`
and `git diff --check` were silent. Docker locally printed `Cannot connect to
the Docker daemon`; real server/container evidence comes only from GitHub.

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control python3 .work/round7/baseline-check.py`
loaded `ec4a8bba`'s actual codec and adapter in memory and compared current decisions.
It printed `Baseline accepts concealed encoded-word subject; current refuses`,
`Baseline exports 23002 draft-body bytes; current refuses before writing a blob`,
and `Baseline promotes a hostile Message-ID into audit summary; current keeps structured metadata`.
These are local decision comparisons, not real-proxy/server evidence.

**run — initial executions and corrections:** last initial test commit `cecf6ff8`:
Mail push [42381322641](https://github.com/Ares-Empire/AresOS/actions/runs/42381322641)
printed `Ran 57 tests in 38.582s` / `OK` / `Control base suite PASS`, then
`Ran 118 tests in 312.232s` / `FAILED (failures=14, errors=1)`;
Mail PR [42381328230](https://github.com/Ares-Empire/AresOS/actions/runs/42381328230)
printed `Ran 118 tests in 316.016s` / the same failures and error. Independent base
[42381328212](https://github.com/Ares-Empire/AresOS/actions/runs/42381328212)
printed `Ran 57 tests in 47.787s` / `OK` / `Control base suite PASS`.
The new SNI fixture did not change Dovecot's storage roles, caught by three new
role-test methods (14 assertion/subtest failures); it now reloads real fixture
configuration and proves readiness with fresh LIST, then restores default LIST
before teardown. The earlier restore test found that structured compact Mail
records had hidden its historical top-level recipient field: restore now preserves
that status shape while retaining marked compact evidence. The existing crash
assertions were not changed. Importing a TestCase directly also accidentally
rediscovered four earlier methods; using its module-qualified helper removes
those duplicate executions, keeping all 103 original methods plus 11 new methods.
Derived attachment filename formatting is now escaped in approval, with a new
assertion; derived subject formatting is checked too.

**run — last code/test commit `41b781fa4f281cd906247bca385fc34edae8b8bc`:**

| Workflow / pass | Exact relevant output |
| --- | --- |
| [Mail push 42382284217](https://github.com/Ares-Empire/AresOS/actions/runs/42382284217) | `Ran 57 tests in 47.971s`; `OK`; `Control base suite PASS`; `Ran 114 tests in 308.269s`; `OK`; `Control Mail suite PASS` |
| [Mail PR 42382289517](https://github.com/Ares-Empire/AresOS/actions/runs/42382289517) | `Ran 57 tests in 43.168s`; `OK`; `Control base suite PASS`; `Ran 114 tests in 297.569s`; `OK`; `Control Mail suite PASS` |
| [Independent base 42382289552, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42382289552/attempts/1) | `Ran 57 tests in 42.503s`; `OK`; `Control base suite PASS` |
| [Independent base 42382289552, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42382289552/attempts/2) | `Ran 57 tests in 36.897s`; `OK`; `Control base suite PASS` |

Both Mail passes run `bash control/ci/mail/run.sh`: generated-artifact verification,
all 57 unchanged brief-18 base tests, isolated pinned real servers and all 114 Mail
tests (103 earlier methods and 11 new ones). Both print
`Mail delete kill-9 cases: 26; unnamed Deleted messages survive`,
`Mail send kill-9 cases: 45; no repeated SMTP DATA`, and
`Mail reservation/repair kill-9 cases: 16; no SMTP during repair/restart`.
Both independent base attempts run `bash control/ci/test.sh` in pinned Fedora.

Any later commit changes only files under `reviews/`; this run's closing commit
changes only `reviews/19-mail/REPORT.md`. The PR body records both workflows and
both passes on the final head. The three initial executions and four corrected-code
executions are listed above; correcting the initial run accounts for going slightly
beyond the approximate ten-run target when the final report head is checked too.

**run — closing checks:** syntax-tree comparison printed
`All 103 earlier Mail test methods retained; 11 new methods`.
The scope check printed `Protected-path and review-file check PASS`;
`git diff --check` was silent. The size scan printed
`Remaining .work files over 500 MB: []`; no large download or extracted image was
created. Every push used the normal privacy hook, without force push or
`--no-verify`, and every run commit includes the required model trailer.

## Review fixes, round 6

**read — scope / Done:** closes REVIEW-6's unmarked-owner-draft move/copy escape.
`adapter.py` checks the complete move/copy source set before any server mutation:
messages in SPECIAL-USE Drafts or its subfolders refuse regardless of marker or
flags, with `mail_compose mode=draft` and approved `mail_delete` named as alternatives.
Ordinary messages can still enter Drafts; named deletion can still move drafts to
Trash. The folder protections in `safe_folder` remain unchanged.

Draft classification now also uses the IMAP `\Draft` flag returned by the existing
fresh exact-reference `FLAGS BODY.PEEK[]` fetch, with UIDVALIDITY, UID and Message-ID
validation. No read sets/removes flags. Attachments from flagged sources, including
all descendant parts, refuse before reconstruction; draft/reply/reply-all/inline
text is fully disclosed or its approval refuses as oversized. Only draft-save
writes the marker. Tool definitions, generated Mail tools and `TOOLS.md`, and the
control README describe the current rules.

**read — tests proving each rule** (`control/mail_tests/test_review_fixes_6.py`):

| Test in `ReviewFixes6` | Coverage |
| --- | --- |
| `test_review6_unmarked_marked_flagged_drafts_and_subfolders_refuse_move_copy_atomically` | Exact REVIEW-6 unmarked owner draft; marked/flagged variants; root/subfolder; move/copy refused with both alternatives; real server UIDs, bytes and flags unchanged, even with an ordinary message first in the batch; source/part/attached forwarding refusal. |
| `test_review6_flagged_inbox_archive_and_deep_parts_refuse_and_allowed_moves_keep_flag` | Unmarked flagged sources in INBOX/Archive; every MIME descendant; both attach forms and attached forwarding; allowed copy/move between ordinary folders preserves bytes/flags and refusal. |
| `test_review6_flagged_literal_text_fully_disclosed_or_oversized_in_all_inline_modes` | INBOX/Archive flagged drafts in draft/reply/reply-all/inline-forward modes; exact whole header-like text in approval and SMTP receipt, or refusal at 23,100 characters without reservation. |
| `test_review6_flagged_draft_differing_html_is_disclosed_whole` | Flag-only draft accepts mode=draft; entire plain and differing readable HTML/link text disclosed; server unchanged. |
| `test_review6_flag_is_fresh_after_another_client_changes_it_without_read_side_effects` | Same reference was previously read/attachable; another client sets Draft; all attach paths now refuse and all inline modes disclose; full server bytes/flags unchanged by reads/composition/preparation. |
| `test_review6_flagged_sources_still_validate_uidvalidity_identity_and_existence` | Changed UIDVALIDITY, wrong identity and expunged UID refuse as stale rather than using the flag or a replacement message; server unchanged. |
| `test_review6_ordinary_move_copy_into_drafts_allowed_and_named_delete_still_works` | Ordinary messages move/copy into Drafts with bytes/flags intact; unmarked/flagged drafts go to Trash only through exact named deletion approval. |
| `test_review6_mail_flag_cannot_add_or_remove_draft_even_in_mixed_flags` | Draft addition/removal refuses in INBOX/Archive, already-flagged/unflagged sources, with otherwise permitted flags; no partial flag changes. |

**read — earlier-test setup alignment:** two earlier methods explicitly used a
move/copy out of Drafts as setup, which cannot succeed under point 1. The fixtures
in `ReviewFixes.test_review_1_moved_and_copied_draft_reply_and_both_forwards_keep_provenance`
and `ReviewFixes5.test_review5_header_like_saved_draft_source_and_parts_refused_even_after_move_copy`
now append the exact saved draft bytes to INBOX as a pre-existing marked draft
before exercising allowed ordinary-folder moves/copies. Every earlier assertion,
case and test method is retained unchanged; none is weakened, skipped or deleted.
The new first test covers the now-forbidden Drafts exit and its unchanged server
state. This necessary fixture-only adjustment resolves the literal conflict
between “every earlier test unchanged” and the new mandatory refusal rule.

**run — local verification:**
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests python3 -m unittest test_review_fixes_5.DraftAndTextGuard test_review_fixes_4.RebuildAndGuard test_review_fixes_3.HeaderAndEncoding test_review_fixes_2.LocalMailDetection -v`
printed `Ran 14 tests in 0.139s` / `OK`. `python3 control/generate.py` printed
`Generated tools, help, reference and ask rules`; `--check` printed
`Generated artifacts match definitions`; AST parsing printed `Python syntax OK`;
`git diff --check` was silent. A local decision check loaded `614c0e0a`'s actual
adapter and current adapter: only current classifies an unmarked flagged INBOX
message as a draft and refuses Drafts move/copy before reading/mutating messages;
it printed `Baseline differs on both round-6 rules; local decision check only, not server evidence`.
Docker printed `Cannot connect to the Docker daemon`; all container checks run
on GitHub's Linux runners, without installing software on the host.

**run — last code/test commit `807f2b9d41d5f5aba7d9f8001ab65cb1e971c115`:**

| Workflow / pass | Exact relevant output |
| --- | --- |
| [Mail push 42377205761](https://github.com/Ares-Empire/AresOS/actions/runs/42377205761) | `Ran 57 tests in 47.293s`; `OK`; `Control base suite PASS`; `Ran 103 tests in 236.747s`; `OK`; `Control Mail suite PASS` |
| [Mail PR 42377210353](https://github.com/Ares-Empire/AresOS/actions/runs/42377210353) | `Ran 57 tests in 36.413s`; `OK`; `Control base suite PASS`; `Ran 103 tests in 217.018s`; `OK`; `Control Mail suite PASS` |
| [Independent base 42377210379, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42377210379/attempts/1) | `Ran 57 tests in 47.594s`; `OK`; `Control base suite PASS` |
| [Independent base 42377210379, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42377210379/attempts/2) | `Ran 57 tests in 47.293s`; `OK`; `Control base suite PASS` |

Both Mail passes execute `bash control/ci/mail/run.sh`, including the generated
check, all 57 brief-18 base tests, isolated pinned Dovecot/GreenMail containers,
all 103 Mail tests (all 95 earlier methods plus eight new ones), and the existing
crash coverage. Both logs print `Mail delete kill-9 cases: 26; unnamed Deleted messages survive`,
`Mail send kill-9 cases: 45; no repeated SMTP DATA` and
`Mail reservation/repair kill-9 cases: 16; no SMTP during repair/restart`;
the additional remote-boundary tests also pass. The independent base workflow
executes `bash control/ci/test.sh` in pinned Fedora and passes both attempts.

Any later commit changes only files under `reviews/` (this run changes only
`reviews/19-mail/REPORT.md`); the PR body records both workflows and both passes
on the final head. Four initial executions plus four corrected-code executions
and four final-report executions total twelve, above the approximate eight-run
target because of the fixture correction; no required pass is omitted.

**run — closing scope/size checks:** syntax-tree comparison printed
`All 95 earlier Mail test methods and 628 assertion expressions unchanged`.
`Protected-path check PASS`; `git diff --check` was silent; the size scan printed
`Remaining .work files over 500 MB: []`. No large downloads or extracted layers
were created. Normal pushes used verification, without force push or `--no-verify`;
all run commits include the required model trailer.


**run — initial fixture corrections:** code head `7541e338` Mail push
[42376740905](https://github.com/Ares-Empire/AresOS/actions/runs/42376740905)
printed `Ran 103 tests in 238.512s` / `FAILED (failures=2)`: all 95 earlier tests
and six new tests passed. The PR pass [42376745468](https://github.com/Ares-Empire/AresOS/actions/runs/42376745468)
printed `Ran 103 tests in 231.436s` / `FAILED (failures=2)` with the same two failures.
The two new setup errors were creating a Drafts
subfolder through a tool that intentionally forbids that, and comparing flags
across a successful reply's writable selection without first settling the
session-only `\Recent` flag. The test now seeds the owner-created subfolder
through real IMAP and establishes the writable baseline before taking any
expected flags; every assertion remains unchanged. The independent base passed
both attempts ([42376745475](https://github.com/Ares-Empire/AresOS/actions/runs/42376745475));
its logs printed `Ran 57 tests in 37.845s` / `Ran 57 tests in 47.949s`, both
`Control base suite PASS`. These superseded runs are not final code evidence.


**Not verified / assumed:** the real-account and owner usability/presentation
checks are listed above, as are all still-open decisions. No new product
JUDGMENT-CALL or PLAN-GAP is introduced; the earlier test-instruction conflict is
resolved by rounds 5 and 6. **Open questions:** the owner decisions above remain
for the lead before merge. No real account, recipient program or model was used;
no merge performed.

## Review fixes, round 5

**read — scope:** implements `briefs/19-review-fixes-5.md` against REVIEW-5's
`4316545`, superseding attachment disclosure/marker and text-reparsing policies
in the historical sections below. No base implementation/tests, protected paths
or `REVIEW*.md` files change. Only synthetic addresses/accounts were used.

- **Finding 1; points 1 and 5 — draft text cannot hide in an attachment:**
  `adapter.py` refuses an original marked or SPECIAL-USE Drafts source before
  reconstruction, including explicit source/part attachments and attached forwards.
  `codec.py` refuses original marked ancestors/containers/decoded descendants
  before dropping headers, including folded markers with CR, LF or CRLF endings.
  The refusal names `mode=draft` and forwarding inline.
  Those body/quote paths preserve literal header-like text in full; oversized
  approvals refuse without reserving. A moved marked draft also accepts
  `mode=draft`, so the advertised alternative remains usable. Tests:
  `ReviewFixes5.test_review5_header_like_saved_draft_source_and_parts_refused_even_after_move_copy`,
  `ReviewFixes5.test_review5_special_use_drafts_and_nested_draft_ancestors_refused_before_rebuild`,
  `ReviewFixes5.test_review5_header_like_draft_sent_itself_discloses_whole_body_and_long_body_refuses`.
  They cover the free compose/save round trip, 23,100 Subject characters originally
  written as body text, saved/moved/copied markers, unmarked Drafts, nested encoded
  containers and extracted text/binary descendants. No approval truncation.
- **Point 2 — draft-only marker:** only `draft_save` writes the marker; the MIME
  builder emits no private headers on outgoing mail or attachments. Sending a
  draft creates a new unmarked message, and the Sent copy is unmarked too.
  Received and newly sent mail can still be forwarded as `.eml` attachments.
  `ReviewFixes5.test_review5_all_modes_smtp_and_sent_have_no_private_headers_and_sent_can_forward`
  independently decodes sink/Sent bytes for new plain, new formatted, reply,
  reply-all, inline forward, attached forward and draft, then forwards the owner's
  new Sent copy as an attachment. Move/copy marker persistence is covered above.
- **Finding 2; point 3 — independent guard:** `guard.py` imports nothing from the
  builder. Every actual header block rejects a marker, whatever the container or
  child type; every decoded non-body leaf rejects marker lines even if a caller
  supplies supposedly disclosed text. Only a saved draft's root header (during
  draft-save validation) and fully disclosed literal main-body text are allowed.
  `DraftAndTextGuard.test_review5_markers_on_containers_and_decoded_leaves_always_refuse`
  and `ReviewFixes5.test_review5_builder_bypass_marked_containers_fail_compose_and_send_no_data_or_replay`
  exercise marked multipart/opaque children, marked message/rfc822/opaque children
  and a base64 leaf, bypassing the builder at compose, prepare, both send checks
  and replay. Exact-before-DATA rejection leaves `failed`, no DATA and no receipt.
  `DraftAndTextGuard.test_review5_literal_main_body_marker_needs_full_disclosure_and_no_header_marker`
  retains the distinction between by-reference body integrity and full disclosure.
- **Finding 3; point 4 — literal text:** text leaves are decoded and line-scanned,
  never parsed as nested mail in either implementation. Non-text bytes are walked
  as an entity only after a complete well-formed header block ending at a truly
  empty line. Declared containers, digest defaults and transfer encodings retain
  strict validation/bounds. Tests:
  `DraftAndTextGuard.test_review5_text_payloads_never_become_nested_mail`,
  `DraftAndTextGuard.test_review5_opaque_bytes_need_complete_well_formed_headers`,
  `ReviewFixes5.test_review5_prose_colon_first_line_new_plain_formatted_reply_and_text_attachment`.
  FYI/Status prose goes through compose, prepare and the SMTP sink in both formats
  and new/reply modes; header-like text attachments retain their bytes. A literal
  Bcc text-file line still refuses with round 4's clear explanation. Existing
  binary, implicit digest, malformed encoding and pre-DATA Bcc tests remain.

**read — earlier marker expectation changed (point 2):**
`ReviewFixes2.test_review2_1_saved_draft_and_bcc_sent_refused_through_real_proxy_even_renamed`
and `ReviewFixes3.test_review3_1_export_punctuation_malformed_and_mbox_refused_by_real_proxy`
now assert the marker on the draft export only, and its absence on the Sent export.
Their exact-export, Bcc-presence and proxy refusal checks remain.

**RESOLVED / read — conflicting test instructions:** rounds 5 and 6 replace
“shown in full inside an attachment” with “refused as an attachment,” and round 6
forbids moving/copying from Drafts. These approved rules settle the superseded
expectations below; this is no longer an open PLAN-GAP or owner question. All 85
earlier Mail test methods and their original cases remained in round 5; ten methods
were added. No test was skipped or deleted. The historical expectation changes were:

- `ReviewFixes.test_review_1_moved_and_copied_draft_reply_and_both_forwards_keep_provenance`:
  attached forward refuses immediately; inline/reply full-text and size checks stay.
- `HeaderAndEncoding.test_review3_2_recursive_encoding_and_provenance_before_text_classification`:
  marked containers refuse; unmarked versions still prove recursive Bcc removal;
  declared text stays byte-exact literal text, as point 4 requires.
- `ReviewFixes3.test_review3_2_received_two_level_encoded_messages_in_all_composition_modes`:
  all 24 marked combinations refuse, while 24 unmarked received-source combinations
  still submit and verify recursive Bcc removal, body presence and approved hashes.
  The draft-mode source itself is a saved draft without inherited attachments;
  its explicit attachments come from the unmarked received mail.
- `ReviewFixes3.test_review3_2_large_encoded_marked_draft_is_not_approved_by_hash`:
  compose refuses instead of waiting for the oversized-approval refusal.
- `ReviewFixes3.test_review3_guard_extracted_marked_body_keeps_ancestor_provenance`:
  all original extracted text/HTML/PDF paths refuse instead of being disclosed/sent;
  the encoded phantom-path refusal remains.
- `RebuildAndGuard.test_review4_allowlist_all_nested_headers_and_original_provenance`:
  marked/Drafts sources refuse before rebuild; unmarked versions retain every
  allowlist, private-address-removal and payload-presence check.
- `RebuildAndGuard.test_review4_guard_checks_every_decoded_leaf_and_literal_private_lines`:
  even a purportedly disclosed folded attachment marker refuses.
- `RebuildAndGuard.test_review4_guard_parses_literals_and_approved_inline_forward_text`:
  the valid outgoing fixture has no root marker. A defective speculative non-text
  header block stays opaque and byte-exact under point 4; real declared encodings
  remain checked by the unchanged broken-structure tests.

**JUDGMENT-CALL / read — forwarded mail is a file:** a received or sent message
forwarded as an attachment reaches recipients as `forward.eml`, of type
`application/octet-stream`, rather than a `message/rfc822` attached-mail object
that their program can render inline. This freezes the rebuilt bytes and approved
hash without reserializing binary leaves. Native attached-mail presentation was
rejected because it reintroduces the earlier byte-preservation problem; changing
this needs matching exact-byte tests and recipient-program qualification. These
are recipient programs, not assumptions about the owner's account. Documentation
read on 2026-11-07; none of these clients was run, and none of these sources
promises presentation for this exact MIME type:

| Recipient program | Evidence and practical expectation |
| --- | --- |
| Apple Mail on Mac | **read:** [Apple's attachment guide](https://support.apple.com/guide/mail/mlhlp1123/mac) documents Open With, preview and saving. **assumed:** this `.eml` is a file the recipient opens/saves, possibly opening a separate message through a suitable app; inline mail rendering is unqualified. |
| Outlook | **read:** [Microsoft's `.eml` guide](https://support.microsoft.com/en-us/outlook/mail/open-eml-msg-and-oft-files-in-new-outlook-and-outlook-on-the-web) documents opening a saved `.eml` in new Outlook by double-click/Open With or dropping it in the reading pane, including Outlook on the web. **assumed:** recipients can save this attachment then use that route; exact attachment-chip/preview behavior is unqualified. |
| Thunderbird | **read:** [Mozilla's attachment guide](https://support.mozilla.org/en-US/kb/how-use-attachments) documents Save and Open with the default application for the file type. **assumed:** an `.eml` association can open the downloaded message; exact octet-stream preview and inline rendering are unqualified. |
| Gmail on the web | **read:** [its `.eml` guide](https://support.google.com/mail/answer/9261412?hl=en) says downloaded EML files require a desktop mail client. **assumed:** recipients can download this file and use that route; this guide does not establish web preview for our exact MIME. |
| iOS Mail | **read:** [Apple's download guide](https://support.apple.com/guide/iphone/iph7fe7a50a7/ios) documents touch-and-hold, Save to Files and Share to another app. **assumed:** this is the fallback for our `.eml`; installed-app handling and inline preview are unqualified. |

**JUDGMENT-CALL / read — draft boundary:** any marked mail, including an older
Sent copy produced before round 5, is conservatively a draft for attachment refusal.
No free tool strips the marker. Forwarding inline shows its complete text or
refuses the oversized approval. Likewise any extracted part of a marked/Drafts
source refuses, including an ordinary binary attachment; no exception silently
releases draft-derived material. Relaxing this needs an explicit provenance policy.

**run — local verification:**
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests python3 -m unittest test_review_fixes_5.DraftAndTextGuard test_review_fixes_4.RebuildAndGuard test_review_fixes_3.HeaderAndEncoding test_review_fixes_2.LocalMailDetection -v`
printed `Ran 14 tests` / `OK`.
`python3 control/generate.py --check` printed `Generated artifacts match definitions`;
AST parsing printed `Python syntax OK`; `git diff --check` was silent. The local
`.work/round5/adapter-check.py` and `earlier-adapter-check.py` each printed
`Ran 6 tests` / `OK` with in-memory transport substitutes (no JSON-schema oracle);
these are not server evidence. `.work/round5/baseline-check.py` loads `4316545`:
all four new guard test methods fail there (10 failed subcases / 3 errors), then
it prints `All four new unit regressions fail on 4316545 as expected`. The current
four pass. No Docker daemon was available locally; no host installation ran.

**run — last code/test commit `451d353c605747e6c35060a9f70c045aff1b991a`:**

| Workflow / pass | Exact relevant output |
| --- | --- |
| [Mail push 42374466907](https://github.com/Ares-Empire/AresOS/actions/runs/42374466907) | `Ran 57 tests in 44.247s`; `OK`; `Control base suite PASS`; `Ran 95 tests in 223.546s`; `OK`; `Control Mail suite PASS` |
| [Mail PR 42374471965](https://github.com/Ares-Empire/AresOS/actions/runs/42374471965) | `Ran 57 tests in 43.609s`; `OK`; `Control base suite PASS`; `Ran 95 tests in 235.887s`; `OK`; `Control Mail suite PASS` |
| [Independent base 42374471710, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42374471710/attempts/1) | `Ran 57 tests in 52.977s`; `OK`; `Control base suite PASS` |
| [Independent base 42374471710, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42374471710/attempts/2) | `Ran 57 tests in 47.726s`; `OK`; `Control base suite PASS` |

Both Mail passes run `bash control/ci/mail/run.sh`: generated verification, all
57 unchanged brief-18 tests, isolated pinned servers, all 95 Mail tests (ten new
round-5 methods, including folded-marker subcases) and the original crash/kill
coverage. The independent base workflow executes `bash control/ci/test.sh` in
pinned Fedora. Any later commit changes only `reviews/19-mail/REPORT.md`; the PR
body records both workflows and both passes on the final report-inclusive head.

**run — superseded executions:** initial `5bba9bfe` Mail
[42373773375](https://github.com/Ares-Empire/AresOS/actions/runs/42373773375) and
[42373777624](https://github.com/Ares-Empire/AresOS/actions/runs/42373777624)
each printed `Ran 95 tests` / `FAILED (failures=39, errors=11)`. All ten new tests
passed; failures were confined to the ten earlier methods enumerated above with
superseded marker/disclosure/text expectations. Initial base
[42373777605](https://github.com/Ares-Empire/AresOS/actions/runs/42373777605) passed.
After aligning those expectations, interim `a46f0895` Mail
[42374008406](https://github.com/Ares-Empire/AresOS/actions/runs/42374008406) and
[42374011747](https://github.com/Ares-Empire/AresOS/actions/runs/42374011747)
printed `Ran 95 tests` / `Control Mail suite PASS`; independent base
[42374011744](https://github.com/Ares-Empire/AresOS/actions/runs/42374011744)
passed both attempts. Original folded marker lines needed the same CR/LF/CRLF
handling as the guard, so `451d353c` tightened original/ancestor checks and added
subcases, requiring a fresh verification head. These earlier passes are not final
code evidence. Eleven workflow executions were used through code verification;
final report-head verification adds four, exceeding the approximate ten-run
budget to retain coverage under the changed policy and verify the correction.

**run — closing scope/size checks:** all 85 earlier Mail test methods remain and
ten were added; base tests, protected paths and `REVIEW*.md` are untouched.
Generated artifacts match. Normal pushes used verification, with no force push or
`--no-verify`; every run commit has the required model trailer. No `.work` file
is over 500 MiB; no large downloads, images or extracted layers were created.


**Not verified / assumed:** real recipient-client `.eml` presentation, real-account
qualification and tool-user/approval usability still need owner testing. Ordinary
local-file authorship remains the deferred design question. **Open questions:**
the lead should review the recipient-file presentation judgment call before merge;
the historical test-instruction conflict is resolved by rounds 5 and 6. No merge performed.

## Review fixes, round 4

**read — scope:** closes the three findings in `REVIEW-4.md` on `1aaa8ff`.
This section supersedes earlier descriptions of copied/sanitized attachment headers
and of the guard sharing codec helpers. Earlier review tests and `control/tests/`
are unchanged. Generated tools/reference remain synchronized.

- **Finding 1 — saved mail and the final check:** the detector stops only on a
  genuinely empty protocol line. The independent guard imports nothing from
  `codec.py`: it parses raw headers/boundaries itself, decodes all supported
  transfer encodings, carries digest defaults, reparses every decoded leaf as a
  possible MIME entity, and scans every decoded level for private header-shaped
  lines or undisclosed authored markers, including continuation text. Exact body
  integrity and actual full disclosure are separate checks: a quote approved by
  reference cannot authorize literal marker text. Literal
  `Bcc:`/`Resent-Bcc:` lines in ordinary files are refused with an explicit
  false-positive explanation. Compose and prepare refuse unsafe bytes; both
  send checks, including the one on the exact bytes immediately before DATA,
  leave a durable `failed` operation with no DATA and no submission on replay.
  Tests: `ReviewFixes4.test_review4_saved_sent_whitespace_continuation_refused_through_proxy`,
  `RebuildAndGuard.test_review4_guard_checks_every_decoded_leaf_and_literal_private_lines`,
  `ReviewFixes4.test_review4_guard_bypassing_builder_fails_compose_prepare_and_final_data_without_replay`,
  `RebuildAndGuard.test_review4_guard_parses_literals_and_approved_inline_forward_text`.
- **Finding 2 — attached mail rebuilt:** every outgoing mail source is created
  anew with only the brief's message/MIME header allowlists, recursively.
  Implicit digest children get their effective `message/rfc822` type preserved;
  enclosed mail without From is handled. Unknown headers, all Resent headers and
  the original authored marker are dropped. Provenance is decided on original
  bytes/ancestors and Drafts first; rebuilt authored text gets the reserved
  allowed `Content-Description: AresOS authored text; full approval required`.
  That description preserves disclosure on another inspection without copying
  the source marker. Approval lists the allowed headers, the transformation,
  full authored text, and the SHA256 of the bytes actually attached. Broken or
  ambiguous structures, unsupported encodings and depth/size excess refuse.
  Tests: `RebuildAndGuard.test_review4_allowlist_all_nested_headers_and_original_provenance`,
  `RebuildAndGuard.test_review4_implicit_digest_default_is_preserved_at_every_depth`,
  `RebuildAndGuard.test_review4_rebuild_and_guard_refuse_depth_size_and_broken_structures`,
  `ReviewFixes4.test_review4_digest_without_content_type_sent_clean_in_both_forward_styles_and_explicit_parts`.
- **Finding 3 — byte-exact binaries:** outgoing extraction and reconstruction
  slice original MIME bytes, decode each leaf without serializing it, and retain
  those decoded bytes. Binary/bare-line-ending payloads use base64 when emitted.
  Original read/source-save exports remain unchanged. The PDF/PNG test covers
  binary and base64 sources through attached/inline forward and explicit parts,
  asserting received decoded bytes and approved hashes exactly. Its TLS IMAP
  frontend supplies explicit original literals over the real backend, because
  BODY[] normalization by a backend must not silently normalize the fixture.
  The non-relaying TLS SMTP sink records actual DATA bytes independently.
  Test: `ReviewFixes4.test_review4_raw_binary_and_base64_pdf_png_are_byte_equal_after_all_send_paths`.
  The original package's exact-forward fixture assertion now expects the exact
  independently constructed allowlisted bytes (part-level MIME-Version removed)
  and additionally checks unchanged original source export. No review assertion
  was weakened, skipped, deleted or changed.

**read — JUDGMENT-CALL, local attachment change time:** the caller captures
`max(mtime, ctime)` from the same stable descriptor used to import bytes. Mail
approvals show that instant as `last_changed`, with caller-local offset and zone,
next to path/name/size/hash, and freeze it with the imported bytes. Backdating
mtime cannot backdate ctime. This is a hint, not proof of who wrote the file;
showing all ordinary files' text remains an owner question for the lead at merge.
Omitting the hint or trusting mtime alone was rejected. A different policy later
requires changing import metadata/approval and owner qualification, not transport.
Test: `ReviewFixes4.test_review4_local_last_changed_is_max_mtime_ctime_in_caller_zone_and_frozen_in_approval`
uses the real distinct-UID proxy, backdated/future mtimes, an explicit caller zone,
then changes the paths and verifies the approved immutable bytes still send.
The base schema only gains optional metadata; its default file-read contract and
all 57 base tests are unchanged. Mail requires reimport for blobs lacking the hint.

**read — JUDGMENT-CALL, strict decoded-content checks:** refuse even literal
private-header lines; do not silently alter a text file or treat a MIME type/name
as proof that it contains no mail. Rebuild/check bounds are 40 nested levels,
64 MiB per entity/wire and 256 MiB cumulative inspection work; the existing
25 MiB transferred-file and 16 KiB approval bounds still apply. Unsupported cases
need qualified decoder/guard regressions before they can be supported.

**run — local verification:** `PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=control:control/mail_tests python3 -m unittest
test_review_fixes_4.RebuildAndGuard test_review_fixes_3.HeaderAndEncoding
test_review_fixes_2.LocalMailDetection -v` printed `Ran 10 tests` / `OK`.
`.work/round4-regressions.py` loaded `1aaa8ff` and reproduced the whitespace
bypass, implicit-digest private-header leak, unlisted-header retention and raw
binary PDF/PNG corruption, then printed current detector/rebuild PASS and exact
binary/base64 × explicit/inline/attached-forward PDF/PNG bytes PASS.
`.work/round3-regressions.py` printed all 24 adapter mode/encoding combinations
PASS and injected-MIME refusal PASS. These local substitutes are not real-server
evidence. `python3 control/generate.py --check` printed `Generated artifacts match
definitions`; AST parsing printed `Python syntax OK`; `git diff --check` was silent.
Docker reported `Cannot connect to the Docker daemon`; no host installation ran.

**run — last code/test commit `b9a4e77368323683de356bf063b6108e86801463`:**

| Workflow / pass | Exact relevant output |
| --- | --- |
| [Mail push 42371333726](https://github.com/Ares-Empire/AresOS/actions/runs/42371333726) | `Ran 57 tests in 48.687s`; `Control base suite PASS`; `Ran 85 tests in 228.628s`; `OK`; `Control Mail suite PASS` |
| [Mail PR 42371337726](https://github.com/Ares-Empire/AresOS/actions/runs/42371337726) | `Ran 57 tests in 56.694s`; `Control base suite PASS`; `Ran 85 tests in 246.482s`; `OK`; `Control Mail suite PASS` |
| [Independent base 42371337719, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42371337719/attempts/1) | `Ran 57 tests in 39.124s`; `OK`; `Control base suite PASS` |
| [Independent base 42371337719, attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42371337719/attempts/2) | `Ran 57 tests in 48.059s`; `OK`; `Control base suite PASS` |

Both Mail runs execute `bash control/ci/mail/run.sh`, including the unchanged base
suite (`bash control/ci/test.sh`), generated verification, isolated pinned real
servers, all ten new round-4 regressions (`... ok`) and all 89 existing kill cases.
The independent workflow executes the same base script in pinned Fedora 45.
Any later commit changes only `reviews/19-mail/REPORT.md`; the PR body records
both workflows and both passes on that final, report-inclusive head.

**run — earlier round-4 results:** initial head `a80e1db` Mail runs
[42370336851](https://github.com/Ares-Empire/AresOS/actions/runs/42370336851) and
[42370339915](https://github.com/Ares-Empire/AresOS/actions/runs/42370339915)
printed `Ran 84 tests` / `FAILED (failures=5)`: the guard mistook embedded
From/Subject prose in four inline-forward cases and one ordinary file for a
malformed MIME entity. The implementation was corrected; the earlier review
assertions remain unchanged. All nine initial new tests passed in both runs.
Interim head `cae2d1b` passed Mail
[42370827591](https://github.com/Ares-Empire/AresOS/actions/runs/42370827591) and
[42370832173](https://github.com/Ares-Empire/AresOS/actions/runs/42370832173)
(`Ran 85 tests` / `Control Mail suite PASS`) and both attempts of base
[42370832198](https://github.com/Ares-Empire/AresOS/actions/runs/42370832198).
It was superseded to tighten the distinction between an exact by-reference body
and actually disclosed literal-marker text. Initial independent base
[42370339914](https://github.com/Ares-Empire/AresOS/actions/runs/42370339914)
also passed. These are not counted as final-code evidence. The extra verification
head exceeds the approximate ten-run budget; no check or assertion was bypassed.

**read / assumed — remaining owner gates:** no real account, provider, client or
model was used. Actual recipient-client presentation and approval usability still
need owner qualification. Local-file authorship remains unproven by timestamps.
No additional PLAN-GAP or open question beyond those gates. **read — protocol:**
[RFC 2046 §5.1.5](https://www.rfc-editor.org/rfc/rfc2046#section-5.1.5)
specifies the implicit digest type used by both implementations. **run — final scope/size
checks:** protected paths and review files untouched; no `.work` file over 500 MB.

## Review fixes, round 3

**read — scope:** closes findings 1–2 in `REVIEW-3.md` on `5180db3` and adds
the independent final guard required by `briefs/19-review-fixes-3.md`.
Only Mail implementation/tests and this report change. `control/tests/`, the
review files and all other protected paths remain untouched.

- **Finding 1 — saved-mail detection:** `codec.is_mail` accepts the full printable
  ASCII field-name range except colon, including whitespace before the colon.
  It scans past malformed lines and an initial mbox envelope until the first
  empty line, requiring From plus an identifying header (now also Bcc,
  Resent-Bcc or X-AresOS-Authored). Uncertain mail-like files are refused.
  Tests: `HeaderAndEncoding.test_review3_1_full_field_syntax_scan_past_damage_and_mbox`
  covers every allowed field-name character and each new identifying header;
  `ReviewFixes3.test_review3_1_export_punctuation_malformed_and_mbox_refused_by_real_proxy`
  exports a marked 21,000-character draft and a Bcc-bearing Sent copy through
  the actual distinct-UID daemon/proxy, adds punctuation/malformed/mbox headers,
  renames them `.txt`, and checks refusal. Ordinary PDF/text files still send
  unchanged. The round-2 detector test's two ordinary-file fixtures now put
  their example headers after an empty line; their exact old bytes are asserted
  to be mail-like in the new test, as the new scan-past-damage rule requires.
- **Finding 2 — decoded nested mail:** `codec._outgoing` strictly decodes each
  encapsulated RFC822/global message before parsing, sanitizing or inspecting
  provenance. It also enters mail and frozen MIME entities inside opaque or
  text parts, removes Bcc/Resent-Bcc recursively, normalizes encoded wrappers,
  and freezes the resulting attachment bytes before hashing. Approval text is
  collected from that normalized content. Ancestor markers survive extraction
  of individual plain/HTML parts, including an explicit marker on the emitted
  attachment. Source read/save exports retain their original bytes.
  Tests: `HeaderAndEncoding.test_review3_2_recursive_encoding_and_provenance_before_text_classification`;
  `ReviewFixes3.test_review3_2_received_two_level_encoded_messages_in_all_composition_modes`
  sends all 24 type/encoding/mode combinations (new, reply, reply-all, both
  forwards, draft), independently decodes every received level, checks both
  private headers/addresses are absent, checks full marked text is approved,
  and compares received attachment hashes with the approved bytes;
  `ReviewFixes3.test_review3_2_large_encoded_marked_draft_is_not_approved_by_hash`
  checks all four 21,000-character encoded sources exceed the approval limit;
  `ReviewFixes3.test_review3_guard_extracted_marked_body_keeps_ancestor_provenance`
  covers extracted plain/HTML bodies, refuses missing disclosure and keeps an
  ordinary PDF from the same marked source attachable without a text marker.
- **Independent final guard:** `guard.py` walks the actual wire bytes with a
  header-only parser, its own transfer decoding and raw multipart-boundary
  traversal. It does not call the sanitizer, its tree traversal, `decoded`,
  `parts` or `approval_texts`. It enters declared messages, detected mail,
  frozen MIME containers and mail-named files. It refuses any private header
  or undisclosed marked text. Generated body text is checked against the exact
  composition, including immutable quoted bytes; ordinary incoming quotes
  retain their existing approval-by-reference rule. HTML line endings are
  normalized before readable-text comparison. Checks run after compose builds
  MIME, during prepare, before send stages and immediately before SMTP DATA
  on the same bytes. A send-time refusal becomes `NothingLeft` and durable
  `failed`, without DATA or retry. Local draft storage permits its root Bcc
  for draft recipients; nested private headers remain forbidden, and SMTP
  never uses that exception.
  Tests: `ReviewFixes3.test_review3_guard_bypassed_sanitizer_refuses_compose_prepare_and_send_without_data`
  injects hand-built MIME with encoded Bcc or undisclosed marked text directly
  through the MIME builder. Compose/prepare refuse; send records failed and
  replay stays failed. Bypassing the earlier check too still reaches the
  independent guard at the real TLS SMTP envelope boundary: the SMTP DATA
  method is never called and the non-deduplicating fixture has zero arrivals.
  `HeaderAndEncoding.test_review3_guard_frozen_mime_container_and_headerless_eml_are_checked`
  additionally covers mail without From and frozen multipart containers.

**read — refusal coverage / JUDGMENT-CALL:** malformed or ambiguous MIME/header
blocks, unknown/broken encodings, encoded multipart containers, unsupported
`message/*` subtypes, undecodable text and nesting beyond 40 levels are refused
instead of guessed. Parser-exposed descendants inside encoded messages are not
stable decoded paths, so callers attach the enclosing part or whole source.
Tests: `HeaderAndEncoding.test_review3_2_unknown_broken_ambiguous_and_defective_mail_refused`,
`ReviewFixes3.test_review3_2_broken_encoding_and_nested_header_defects_refuse_compose`
and the extracted-body regression above. Supporting more cases later requires
matching decoder/guard changes and received-byte regressions. Keeping encoded
wrappers opaque or passing unsupported subtypes through was rejected because
it repeats the review's disclosure failure. Normalizing encoded messages may
change folding and wrapper bytes even without a private header; their approved
hashes always bind the emitted bytes. Client presentation remains an owner gate.

**run — local checks:** `PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=control:control/mail_tests python3 -m unittest
test_review_fixes_3.HeaderAndEncoding test_review_fixes_2.LocalMailDetection -v`
printed `Ran 5 tests` and `OK`. `python3 control/generate.py --check` printed
`Generated artifacts match definitions`; AST parsing all `control/**/*.py`
printed `Python syntax OK`; `git diff --check` printed nothing.
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests python3
.work/round3-regressions.py` loaded `5180db3`'s codec/adapter and reproduced
the punctuation bypass and encoded Bcc/provenance failures for both types and
encodings, then printed current detector/recursive-codec PASS, all 24 adapter
mode/encoding combinations PASS, empty/plain/formatted guard PASS and injected
MIME refusal PASS. These use synthetic local message lookup, not real servers.
A separate local extracted-body check printed `Extracted plain/HTML bodies
retain ancestor provenance; missing disclosure refused PASS`. Earlier local
checks exposed an obsolete-From parser ambiguity, the boundary's own CRLF and
HTML CRLF differences; the implementation was corrected. The QP fixture now
encodes header names as well, so it actually reproduces the opaque parser case.
Docker reported `Cannot connect to the Docker daemon`; no host software was
installed. The scope check printed `Protected-path check PASS`; the size scan
printed `Remaining .work files over 500 MB: []`.

**read — final-head validation location:** final report-inclusive head, both
Mail workflow IDs and both independent base attempts are recorded in
[draft PR #9's validation section](https://github.com/Ares-Empire/AresOS/pull/9)
after the final push. That stable link records subsequently allocated run IDs
without changing the tested commit to insert its own IDs. Each final Mail
execution includes the whole base suite and all ten new round-3 tests; no
passing result is inferred from the initial runs below.

**run — initial head `ce4eea96d126b4b194c2d358c471653cae2e3d4b`:**

| Workflow | Exact relevant output |
| --- | --- |
| [Mail push 42367538434](https://github.com/Ares-Empire/AresOS/actions/runs/42367538434) | `Ran 57 tests in 48.435s`; `Control base suite PASS`; `Ran 74 tests in 176.756s`; `FAILED (failures=5)` |
| [Mail PR 42367542355](https://github.com/Ares-Empire/AresOS/actions/runs/42367542355) | `Ran 57 tests in 46.707s`; `Control base suite PASS`; `Ran 74 tests in 170.272s`; `FAILED (failures=5)` |
| [Independent base 42367542361](https://github.com/Ares-Empire/AresOS/actions/runs/42367542361) | `Ran 57 tests in 50.876s`; `OK`; `Control base suite PASS` |

**read — corrections after those runs:** four failures were the unchanged
round-1 moved/copied-draft inline-forward regression: the conservative detector
recognized the displayed forwarding header block as a file-like mail. The
guard now checks constructed body text exactly against the composition and
quote blobs before interpreting attachment contents. The fifth was the new
export-byte assertion: base64 fixture lines used LF while IMAP APPEND normalizes
them to CRLF. The fixture now emits CRLF before APPEND; the exact-byte assertion
remains. The new attachment-only codec fixture explicitly names its attachment
disposition. No assertion was removed or relaxed. The final head additionally
tests ancestor provenance for extracted parts and refuses ambiguous boundary
suffixes; these are within the same nested-message/disclosure class.
The interim `5e8118d` Mail runs were superseded and canceled after a local check
found that inherited markers also marked non-text PDFs. The marker is now
emitted only when text disclosure exists; the extracted-body regression also
checks that PDF's unchanged decoded bytes. Its base run completed successfully;
neither it nor the canceled Mail runs count as final-head evidence.

**read — protocol references, 2026-11-07:**
[RFC 5322 §3.6.8](https://www.rfc-editor.org/rfc/rfc5322#section-3.6.8)
defines the field-name range;
[RFC 2045 §6.4](https://www.rfc-editor.org/rfc/rfc2045#section-6.4)
restricts multipart transfer encodings;
[RFC 2046 §5.1.1](https://www.rfc-editor.org/rfc/rfc2046#section-5.1.1)
assigns the delimiter's preceding CRLF to the boundary. Compatibility evidence
is the pinned container suite, not an assumption about every recipient client.

**read — PLAN-GAP:** the deliberately deferred ordinary local-file class and
the round-2 saved-mail JUDGMENT-CALL remain unchanged. No additional feature or
design-gap implementation is included. **assumed / owner gate:** real-account,
mail-client presentation and tool-user qualification below remain unverified.

## Review fixes, round 2

**read — scope:** closes only findings 1–3 in `REVIEW-2.md` on `300cd06`,
following `briefs/19-review-fixes-2.md`. The five added tests are in
`control/mail_tests/test_review_fixes_2.py`; `control/tests/`, the review files
and the brief's other protected paths are untouched.

- **Finding 2 — every outgoing mail source:** compose uses one attachment path
  for explicit sources, nested RFC822 messages, multipart containers, automatic
  forwards and draft attachments. It recursively removes Bcc/Resent-Bcc before
  hashing, names the transformation in approval and freezes the approved bytes.
  Opaque mail parts are recognized by bytes even when renamed. Original read/save
  bytes are retained. Test:
  `ReviewFixes2.test_review2_2_explicit_sent_source_nested_message_and_container_in_every_mode`
  sends a Bcc-bearing client-saved Sent copy, explicitly attaches its source plus
  nested RFC822/container/renamed parts in new, reply, reply-all, both forward
  styles and draft modes, then checks received decoded bytes and approved hashes.
  It also compares source read/save bytes with the untouched Sent original.
- **Finding 1 — local mail round trip:** composition refuses caller-imported
  `.eml`/`.msg` names case-insensitively, or bytes with a leading RFC822 header
  block containing From plus any specified identifying header. Detection tolerates
  a UTF-8 BOM and leading whitespace; headers after the first empty line do not
  count. The error directs the caller to forward or attach by exact reference.
  Tests:
  `ReviewFixes2.test_review2_1_saved_draft_and_bcc_sent_refused_through_real_proxy_even_renamed`
  exports a marked 21,000-character draft and a Bcc-bearing Sent source with the
  actual daemon/proxy under distinct Linux UIDs. Imports are refused for the
  originals, renamed `.txt` copies, BOM/blank-line/whitespace variants, and mail
  extensions containing ordinary text. Ordinary PDF/text attachments still reach
  the recipient unchanged through compose, prepare-send and send.
  `LocalMailDetection.test_review2_1_header_detection_bom_whitespace_case_and_first_empty_line`
  covers every identifying header and negative header/body cases.
- **Finding 3 — exact typed evidence:** the minimal base-engine change delegates
  Mail stage validation to the adapter. Known stage keys, recipient/reference
  keys, numeric outcomes, hashes and Message-IDs stay exact; invalid stage text
  is refused before storage. Only the explicit diagnostic field and other
  free-text error messages are credential-scrubbed. Existing transport category
  handling and password/AUTH-encoding guards remain in force.
  Tests:
  `ReviewFixes2.test_review2_3_password_collisions_preserve_acceptance_hashes_and_repair`
  uses `accepted:250` and a deterministic substring shared by the stored
  composition/wire hashes as passwords. Successful sends and failed-Sent repairs
  preserve exact acceptance/hash evidence and produce exactly one SMTP arrival.
  `ReviewFixes2.test_review2_3_only_diagnostics_are_scrubbed_and_server_text_is_not_evidence`
  also collides with keys, ids, Message-IDs and addresses, rejects diagnostic text
  as typed evidence, and checks diagnostic redaction. Round 1's four password-echo
  tests still check results, act/MCP/CLI, SQLite, the independent record and output.

**read — regression basis:** `300cd06` attached explicit sources unchanged, accepted
the exported caller blobs, and scrubbed stage names/values indiscriminately. The
new received-byte, refusal and exact-evidence/repair assertions fail those paths;
no old assertion was weakened, skipped or deleted.

**read — JUDGMENT-CALL, saved mail files:** the owner cannot attach a saved `.eml`
or `.msg` from his folders, even when harmless. He forwards the mail itself or
attaches its exact source reference instead. Tracking local-file authorship by
hash was rejected in favor of the brief's explicit refusal rule: renamed mail
and leading preambles cannot bypass the authored-text/Bcc paths. Relaxing this
later needs a provenance/disclosure design and new regression expectations.

**read — PLAN-GAP for the lead, no implementation:** other local files Claude
writes with its own file tools (`.txt`, `.md`, `.csv`, PDF, etc.) still attach by
name, size, real path and sha256 as design §5 specifies. Claude-authored text can
therefore travel without being read in the prompt. Closing that requires an owner
design decision, such as full disclosure of text-like attachments or showing each
local file's modification time in approval.

**run — local checks:** `python3 control/generate.py` printed
`Generated tools, help, reference and ask rules`; `--check` printed
`Generated artifacts match definitions`; AST parsing printed `Python syntax OK`;
`git diff --check` printed nothing. The isolated `LocalMailDetection` unittest
printed `Ran 1 test` and `OK`. A local attempt at the typed-evidence test with a
synthetic account fixture stopped with `ModuleNotFoundError: No module named
'jsonschema'`; it is not counted as passing evidence. Docker reported
`Cannot connect to the Docker daemon`; no host software was installed.
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control python3 .work/round2-regressions.py`
loaded `300cd06`'s adapter/engine with in-memory substitutes, reproduced each
reported defect, then checked current sanitized source bytes, renamed-mail
refusal and exact acceptance evidence. It printed `Finding 2: 300cd06
explicit-source Bcc leak reproduced; current sanitized bytes PASS`, `Finding 1:
300cd06 exported-mail blob bypass reproduced; current renamed-mail refusal PASS`,
and `Finding 3: 300cd06 acceptance evidence corruption reproduced; current exact
evidence PASS`. These local substitutes do not count as real-server/proxy tests.
The protected-path check printed `Protected-path check PASS`; the worktree size
scan printed `Remaining .work files over 500 MB: []`.

**run — implementation head `7f3bac52919c2704a39921113c17fa826aae9aa9`:**

| Workflow | Exact relevant output |
| --- | --- |
| [Mail push 42365438930](https://github.com/Ares-Empire/AresOS/actions/runs/42365438930) | `Ran 57 tests in 47.474s`; `Control base suite PASS`; `Ran 65 tests in 156.655s`; `OK`; `Control Mail suite PASS` |
| [Mail PR 42365441676](https://github.com/Ares-Empire/AresOS/actions/runs/42365441676) | `Ran 57 tests in 37.949s`; `Control base suite PASS`; `Ran 65 tests in 141.729s`; `OK`; `Control Mail suite PASS` |
| [Independent base 42365441680](https://github.com/Ares-Empire/AresOS/actions/runs/42365441680) | `Ran 57 tests in 47.792s`; `OK`; `Control base suite PASS` |

Both Mail runs printed `Generated artifacts match definitions`; each new
`test_review2_*` and each round-1 password-echo test printed `... ok`.
Original Mail crash output remained `Mail delete kill-9 cases: 26; unnamed Deleted
messages survive`, `Mail send kill-9 cases: 45; no repeated SMTP DATA`, and
`Mail reservation/repair kill-9 cases: 16; no SMTP during repair/restart`; the two
other remote-boundary cases also passed (89 total). Logs are workflow artifacts.

**read — final-head validation location:** this report is the only change after
the implementation head. The final report-inclusive head, its two Mail run
IDs, and both attempts of its independent base run are recorded in
[draft PR #9's validation section](https://github.com/Ares-Empire/AresOS/pull/9)
after the final push. That stable link supplies the final-head run IDs without
changing the tested commit merely to insert subsequently allocated IDs here.
Each Mail execution includes all unchanged brief 18 tests, the complete Mail
suite, generated-artifact verification and the original kill-9 cases.

**assumed / owner gate:** real-account qualification and approval/mail-client
presentation remain unverified; the owner-facing gates below still apply.

## Review fixes

**read — scope:** fixes findings 1–5 of `REVIEW.md` on `bc38016`, following
`briefs/19-review-fixes.md`. All new tests are in
`control/mail_tests/test_review_fixes.py` (`ReviewFixes`); the base tests are untouched.

- **Finding 1:** saved draft bodies appear in full in approval, with differing
  readable HTML and links. Every service-built MIME message carries
  `X-AresOS-Authored`; native IMAP moves/copies preserve it and no free tool edits
  headers. Marked sources and SPECIAL-USE Drafts sources disclose their quoted or
  attached text in full. Oversized approvals are refused without reservation.
  Tests: `test_review_1_draft_reload_full_text_and_21000_characters_refused`,
  `test_review_1_owner_draft_plain_and_differing_readable_html_with_links`, and
  `test_review_1_moved_and_copied_draft_reply_and_both_forwards_keep_provenance`.
- **Finding 2:** automatic forwards remove Bcc and Resent-Bcc recursively from
  nested RFC822 messages and frozen `.eml` attachments before hashing. Approval
  identifies that transformation and binds the bytes actually sent. Reply and
  inline-forward header blocks never derive Bcc recipients.
  Tests: `test_review_2_forward_service_sent_bcc_copy_and_reply_headers` and
  `test_review_2_nested_rfc822_and_frozen_eml_bcc_removed`.
- **Finding 3:** transport errors carry controlled messages and numeric SMTP
  refusal evidence. Engine submission/repair no longer persist exception text;
  refusal diagnostics additionally scrub passwords and AUTH encodings. Typed
  stage scrubbing was superseded by round 2's validation above.
  Connection loss still produces an uncertain outcome, including loss after an
  actual UID EXPUNGE. The small base-engine change is necessary because it catches
  adapter failures before the outer request sanitizer sees them.
  Tests: `test_review_3_echoed_imap_password_after_preflight_and_mid_delete_is_never_persisted`,
  `test_review_3_smtp_credential_echo_during_auth_envelope_and_final_data`,
  `test_review_3_second_guard_scrubs_password_and_auth_base64_before_stage_storage`,
  and `test_review_3_act_socket_mcp_cli_and_daemon_log_hide_execution_failure`.
  These inspect results, operation status, SQLite events and bytes, the independent
  record and output; the last test uses the real daemon, act socket, MCP and CLI.
- **Finding 4:** only a nonempty-specific NO with no unrelated response code can
  become a candidate. The exact probe reference must survive, exact UID EXPUNGE
  must finish, and empty-folder DELETE and absence must be verified before
  qualification is recorded. Every failure leaves deletion disabled, with a
  controlled reason in `mail_accounts`; unresolved cleanup names the owner check.
  Tests: `test_review_4_transient_permission_and_generic_refusals_never_qualify`,
  `test_review_4_missing_exact_probe_or_failed_cleanup_never_qualifies`, and
  `test_review_4_positive_guard_qualifies_only_after_verified_cleanup`.
- **Finding 5:** repair's generated description requires recorded final
  `smtp_data=accepted:250` and owner inspection otherwise, even when Sent evidence
  exists. Check: `python3 control/generate.py --check`.

**read — JUDGMENT-CALL, provenance:** use the persistent marker plus the conservative
SPECIAL-USE Drafts fallback. The owner's unmarked drafts in Drafts also show their
whole body, including differing readable HTML. All text in a marked service-built
source is treated conservatively as authored, including pre-existing quotes; a
long saved thread can therefore exceed the approval limit. Loosening this later
would require durable finer-grained provenance, rather than dropping the marker.

**run — local checks:** `python3 control/generate.py` printed
`Generated tools, help, reference and ask rules`; `--check` printed
`Generated artifacts match definitions`; AST parsing printed `Python syntax OK`;
`git diff --check` printed nothing. `docker version --format '{{.Server.Version}}'`
reported that the Docker daemon is unavailable; no local container tests were run.
Container results and exact final-head run IDs are recorded in
[draft PR #9's validation section](https://github.com/Ares-Empire/AresOS/pull/9)
after the report-inclusive head is pushed. This avoids changing that tested head
merely to insert its subsequently allocated workflow IDs. Earlier runs below are
historical evidence only, not review-fix acceptance.

**run — initial review-fix head `b2a2cee3a6a71921b205416f8742fd01f99c16c8`:**
Mail runs [42363705470](https://github.com/Ares-Empire/AresOS/actions/runs/42363705470)
and [42363709223](https://github.com/Ares-Empire/AresOS/actions/runs/42363709223)
both printed `Generated artifacts match definitions`, `Ran 57 tests`, `OK`,
`Control base suite PASS`, `Ran 60 tests`, `OK`, and `Control Mail suite PASS`.
Independent base run
[42363709447](https://github.com/Ares-Empire/AresOS/actions/runs/42363709447)
printed `Ran 57 tests in 36.604s`, `OK`, and `Control base suite PASS`.
The final changes additionally preserve uncertainty after a lost IMAP answer,
exercise actual expunge-before-disconnect and an unsafe server after INUSE clears,
and treat peer disconnects as normal fixture EOF. Final acceptance uses the PR's
report-inclusive head and its two successful executions of each workflow.

**assumed / owner gate:** the real account, server-specific qualification and
approval/mail-client presentation still require the owner's checks listed below.

## Done

- **read — implementation:** `control/aresos_control/mail/` contains the catalogue,
  MIME/HTML/Markdown codec, verifying TLS transports, owner onboarding, DKIM gate and
  shared `Adapter` implementation. All design §5 actions are present, with base-style
  preparation, cancel and notice actions. MCP, CLI help, tool reference and ask rules
  are generated from these definitions. The draft managed MCP file includes `mail`.
- **read — base changes:** `Engine` registers Mail, routes private admin password
  onboarding and sanitizes transport failures. The proxy adds only Mail's caller-side
  path import/save plumbing; CLI reads setup passwords from the terminal. The common
  public outcome schema now includes design's `refused`. Compact restore descriptions
  retain folder and unsubscribe targets. The base operation/approval/file contracts
  are otherwise reused. No lock or new runtime package was added: RFC 8058 verification
  uses already pinned `cryptography` **50.0.2**, because stdlib cannot verify DKIM keys.
- **read — tests:** `control/mail_tests/` covers synthetic real-server reads, writes,
  MIME, sending, stages, files, onboarding, TLS, explicit guard qualification and
  kill-9/restore recovery. `.github/workflows/control-mail.yml` runs the base suite
  plus these tests. `control/README.md` documents setup, recovery and concrete limits.

## Feature → tool → test

Tests below are in `control/mail_tests`; short class/method names are exact. All use
Dovecot IMAP and GreenMail SMTP unless a different fixture is stated.

| Mail *first* feature | Tool(s) | Test(s) |
| --- | --- | --- |
| Accounts, addresses, capabilities, special folders | `mail_accounts` | `Reading.test_multiple_accounts_contacts_and_special_use_names`; `AccountAdmin.test_owner_only_admin_setup_tls_special_use_private_password_and_sent_confirmation` |
| Folders and counts | `mail_folders` | `Reading.test_multiple_accounts_contacts_and_special_use_names`; `test_every_read_action_preserves_flags` |
| Create/rename folders | `mail_folder_create`, `mail_folder_rename` | `Changes.test_move_copy_flags_junk_folder_create_rename` |
| Delete empty leaf, conditional on safe server | `mail_prepare_folder_delete`, `mail_folder_delete` | `Changes.test_greenmail_nonempty_guard_and_delivery_during_folder_approval` (explicit guarded GreenMail); `test_both_upstream_servers_allow_nonempty_delete_and_are_not_qualified` (both upstreams) |
| Search sender/recipient/subject/text/dates/flags/attachments | `mail_search` | `Reading.test_filters_and_large_folder_cursors_bind_full_state_and_query`; `test_no_condstore_or_qresync_fallback_rereads_flags_and_references` |
| Read headers/body/HTML/attachment list | `mail_read` | `Reading.test_html_plain_non_utf8_calendar_and_nested_forward_fixtures`; `test_every_read_action_preserves_flags` |
| Raw source | `mail_read part=source` | `Reading.test_long_body_source_and_parts_are_paged_and_state_bound`; `CallerTransfers.test_real_proxy_caller_import_save_permissions_immutable_bytes_and_full_cli_flow` |
| Conversation across folders | `mail_thread` | `Reading.test_thread_across_folders_missing_duplicate_ids_no_subject_guess` |
| Save attachment / whole mail | `mail_attachment_save` | `CallerTransfers.test_real_proxy_caller_import_save_permissions_immutable_bytes_and_full_cli_flow` (real sockets, distinct Linux uids, actual file policy) |
| New/reply/reply-all/forward inline/attached | `mail_compose`, `mail_prepare_send`, `mail_send` | `Composing.test_new_send_exactly_once_bcc_bytes_encoding_sent_and_no_receipts`; `test_reply_to_list_aliases_threading_own_sent_and_answered`; `test_forward_inline_and_as_attachment_preserve_original_bytes` |
| Plain/formatted mail | `mail_compose` | `Composing.test_formatted_defaults_signature_no_raw_html_and_invalid_links` |
| Signature and default habit | `mail_compose` from owner config | Same test; owner settings covered by `AccountAdmin.test_owner_only_admin_setup_tls_special_use_private_password_and_sent_confirmation` |
| Local / other-mail attachments | `mail_compose` | `CallerTransfers.test_real_proxy_caller_import_save_permissions_immutable_bytes_and_full_cli_flow`; `Composing.test_new_send_exactly_once_bcc_bytes_encoding_sent_and_no_receipts` |
| Save/edit/delete/send draft | `mail_draft_save`, `mail_compose mode=draft`, send/delete pairs | `Composing.test_save_edit_send_and_delete_draft_with_explicit_approval` |
| Move/copy | `mail_move`, `mail_copy` | `Changes.test_move_copy_flags_junk_folder_create_rename` |
| Read/unread/flag/answered/custom keyword | `mail_flag` | Same test; `Reading.test_filters_and_large_folder_cursors_bind_full_state_and_query` |
| Trash/permanent/empty Trash (named pages) | `mail_prepare_delete`, `mail_delete` | `Changes.test_trash_and_permanent_only_named_uids_others_deleted_survive`; `test_delete_without_uidplus_refused_and_all_items_checked_before_any` |
| Junk/not junk | `mail_move` | `Changes.test_move_copy_flags_junk_folder_create_rename` |
| Send status / repair | `mail_operation_status`, `mail_operation_repair` | `Outcomes.test_failure_at_each_later_stage_repairs_without_smtp`; `test_dropped_final_answer_is_unknown_and_never_retried` (scripted TLS SMTP + Dovecot) |
| Header unsubscribe | `mail_prepare_unsubscribe`, `mail_unsubscribe` | `Unsubscribe.test_header_mailto_exact_address_body_and_approval`; `test_https_one_click_post_exact_no_cookies_no_redirect_no_get` (scripted SMTP/HTTPS + Dovecot); both `DKIM` tests |
| Several accounts | account configuration / all tools | `Reading.test_multiple_accounts_contacts_and_special_use_names` |
| Contacts from history | `mail_contacts` | Same test |
| Read calendar invitation (answering deferred) | `mail_read` | `Reading.test_html_plain_non_utf8_calendar_and_nested_forward_fixtures` |

Owner rows are excluded from feature acceptance, except the explicit onboarding
requirement. CardDAV, calendar responses, scheduled sends, notices, filters, PDF and
read receipts were not added. Normal reads never send receipts.

## Tool descriptions for Claude

**read:** the exact generated [reference](../../docs/control/TOOLS.md) and
[Mail MCP tool list](../../control/generated/mail-tools.json) contain every description,
input and result schema. No hand-written duplicate list is maintained. Descriptions
state effects, PEEK/no receipt behavior, exact approval transfer, immutable sources,
per-recipient/stage outcomes, stale/error recovery and no retries. Mail-derived data
remain explicitly untrusted when repeated in composition/approval descriptions.

**assumed / tool-user review:** the extra preparation call, `operation_id` versus the
design's `request_id`, omitting `text` to keep a draft body, literal backslash IMAP
flags, thread summaries followed by individual reads, and path/blob/MIME-part attachment
alternatives are the parts most likely to need wording changes after fresh Claude use.
They have protocol tests; their usability has not been measured with a model.

## Design §5 fixtures and checks

| Required fixture/check | Exact evidence test |
| --- | --- |
| Thread with archived part; missing/duplicate ids | `Reading.test_thread_across_folders_missing_duplicate_ids_no_subject_guess` |
| List Reply-To, own sent reply, aliases, threading headers | `Composing.test_reply_to_list_aliases_threading_own_sent_and_answered` |
| HTML/plain, nested forwarded mail, non-UTF-8 | `Reading.test_html_plain_non_utf8_calendar_and_nested_forward_fixtures` |
| PDF/image/program-like/non-ASCII attachment names | `Composing.test_new_send_exactly_once_bcc_bytes_encoding_sent_and_no_receipts`; `CallerTransfers.test_real_proxy_caller_import_save_permissions_immutable_bytes_and_full_cli_flow` |
| Large folder cursor/query invalidation | `Reading.test_filters_and_large_folder_cursors_bind_full_state_and_query` (240 items, twelve pages); production scan bound documented below |
| Folder recreated with new UIDVALIDITY | `Reading.test_stale_uidvalidity_after_folder_recreated_never_hits_replacement` |
| Every read leaves flags unchanged | `Reading.test_every_read_action_preserves_flags` (accounts/folders/search/read body/source/part/thread/contacts/status; compares full flags) |
| Exactly one arrival, recipients, no Bcc, exact bytes, Sent, answered | `Composing.test_new_send_exactly_once_bcc_bytes_encoding_sent_and_no_receipts`; `test_reply_to_list_aliases_threading_own_sent_and_answered` |
| Client saves Sent / server saves Sent | New-send test (client); `Outcomes.test_server_saves_sent_client_never_appends_duplicate` (scripted SMTP server saves into real Dovecot) |
| Refused recipient is partial | `Outcomes.test_refused_recipient_is_partial_not_done_and_replay_does_not_submit` |
| Failure at each later stage; repair without SMTP | `Outcomes.test_failure_at_each_later_stage_repairs_without_smtp` (Sent, answered; pre-stage injection, real protocol repair) |
| Dropped final SMTP answer is unknown | `Outcomes.test_dropped_final_answer_is_unknown_and_never_retried` |
| Send/delete crash at every log write; never repeat | `MailCrashes.test_kill_every_send_log_write_and_every_remote_stage_never_sends_twice`; `test_kill_every_delete_log_write_and_each_uid_stage_preserves_unnamed` |
| Trash MOVE / answered flag remote boundaries | `MailCrashes.test_trash_move_and_answered_flag_crashes_never_repeat_remote_work` |
| Reservation / every repair log write | `MailCrashes.test_reservation_and_every_repair_write_crashes_never_submit_again` |
| Restore remains locked until owner confirms; old ids refused | `MailCrashes.test_restore_older_sqlite_keeps_lock_until_owner_confirms_and_rejects_old_approval`; whole base crash/restore suite |
| Changed composition/attachment refused | `Composing.test_composition_and_attachment_corruption_refused`; real caller source replacement in `CallerTransfers` |
| Moving to Trash not free | `Changes.test_move_copy_flags_junk_folder_create_rename` (move and copy refused) |
| Explicit per-item refusal is partial; remaining targets untouched | `Changes.test_explicit_per_item_refusal_reports_partial_and_does_not_touch_later_targets` |
| Mandatory STARTTLS, no password before verification / no plaintext fallback | `Outcomes.test_required_starttls_success_and_no_plaintext_auth_fallback` |
| Astral Unicode body fits serialized result cap | `Reading.test_astral_unicode_body_pages_fit_the_actual_result_byte_cap` |
| New mail during folder approval / final boundary | `Changes.test_greenmail_nonempty_guard_and_delivery_during_folder_approval` (test-only guard; upstream gap below) |
| Unnamed Deleted survives / no CLOSE | `Changes.test_trash_and_permanent_only_named_uids_others_deleted_survive`; `test_unsafe_folder_delete_refused_subfolders_and_close_never_called` |
| Certificate mismatch before password | `Outcomes.test_tls_hostname_or_untrusted_certificate_fails_before_password_sent` (actual IMAP and scripted SMTP TLS; password access assertion, no AUTH received) |
| Long quote, Bcc, attachments, odd characters, 16 KiB/no truncation | `Composing.test_long_quotes_by_reference_and_asking_size_never_cut_escaped`; `Changes.test_delete_prompt_metadata_escaped_bounded_and_cannot_be_forged` |
| Encoded mail above per-file cap; summaries/header-only history work | `Composing.test_large_encoded_mail_keeps_per_attachment_cap_and_search_retains_only_summaries` |
| Encoded words/names, CRLF, decoded hashes, SMTPUTF8/IDNA | `Composing.test_new_send_exactly_once_bcc_bytes_encoding_sent_and_no_receipts`; `test_smtputf8_refused_and_idna_domains_converted` |
| Generated catalogue/settings in sync; base intact | `python3 control/generate.py --check`; all 57 original base tests unchanged |

## Verified — original package runs

**run — product head `9f4dbbd5dc7664e2f5696432fff3e3cc770c1933`:** both
[42361618095](https://github.com/Ares-Empire/AresOS/actions/runs/42361618095)
(push) and [42361622331](https://github.com/Ares-Empire/AresOS/actions/runs/42361622331)
(PR) succeeded. Each executes `bash control/ci/mail/run.sh`, which runs:

```sh
docker exec mail-tests bash control/ci/test.sh
# after disconnecting external bridge and connecting only the internal fixture network:
docker exec -e PYTHONPATH=/workspace/control:/usr/lib/aresos-control/vendor -e PYTHONDONTWRITEBYTECODE=1 -e MAIL_CERT_DIR=/workspace/.work/mail-ci/certs mail-tests python3 control/ci/mail/ready.py
docker exec -e PYTHONPATH=/workspace/control:/usr/lib/aresos-control/vendor -e PYTHONDONTWRITEBYTECODE=1 -e MAIL_CERT_DIR=/workspace/.work/mail-ci/certs mail-tests python3 -m unittest discover -s control/mail_tests -v
```

The full Docker invocations, synthetic TLS generation, cleanup and pinned images are
in `control/ci/mail/run.sh`; the workflow's artifacts retain exact base/Mail output
and upstream logs. Important output, verbatim:

| Output | Push run 42361618095 | PR run 42361622331 |
| --- | --- | --- |
| Runtime | `Python 3.15.0`; `Fedora release 45 (Forty Five)` | same |
| Catalogue | `Generated artifacts match definitions` | same |
| Existing base | `Ran 57 tests in 40.250s`; `OK`; `Control base suite PASS` | `Ran 57 tests in 58.490s`; `OK`; `Control base suite PASS` |
| Mail | `Ran 48 tests in 72.040s`; `OK`; `Control Mail suite PASS` | `Ran 48 tests in 85.174s`; `OK`; `Control Mail suite PASS` |
| Send crashes | `Mail send kill-9 cases: 45; no repeated SMTP DATA` | same |
| Delete crashes | `Mail delete kill-9 cases: 26; unnamed Deleted messages survive` | same |
| Reservation/repair crashes | `Mail reservation/repair kill-9 cases: 16; no SMTP during repair/restart` | same |

**run:** two additional remote boundary kills (Trash MOVE and answered flag) passed
in their named test, making **89 Mail kill-9 cases** per full Mail suite. Every
required check in the tables above passed in both runs. The independent existing
base workflow [42361622291](https://github.com/Ares-Empire/AresOS/actions/runs/42361622291)
also succeeded on this head. No original base tests were changed, skipped or deleted.
No failing assertion was weakened: invalid fixture assumptions/setup were corrected,
and implementation/schema defects were fixed.

**read — server versions:** GreenMail **2.1.15**, manifest
`sha256:309ba544ea482e5d4265d09921cdab07c8dad2cc4481d715c9b8ff5d3f0a149f`;
Dovecot **2.3.21.1**, manifest
`sha256:547d28f9a893c93a1d2f6dc164880cd7bfa74009106dfa46b36a6a2ee636d921`;
Fedora **45 x86_64**, manifest
`sha256:79dd6556b8fe1a559051fad5159d4987ead218f1914e7a5bd20350d9ea0f9e52`.
Digests were resolved from the registry before pinning. Dovecot supplies real
SPECIAL-USE/UIDPLUS/MOVE, GreenMail supplies real SMTP delivery and independent
recipient mailboxes. Failures use a non-relaying scripted TLS SMTP server with a
SQLite arrival log that does not deduplicate. The guarded IMAP frontend is separately
identified in PLAN-GAP; it is not represented as upstream server behavior.

**run — earlier iterations, all retained for audit:**

| Workflow ids | Result and correction |
| --- | --- |
| [42359465452](https://github.com/Ares-Empire/AresOS/actions/runs/42359465452) | Initial 57 base + 15 Mail tests passed. |
| [42359769672](https://github.com/Ares-Empire/AresOS/actions/runs/42359769672) | `Ran 30 tests`; `FAILED (failures=1)`: upstream GreenMail accepted nonempty DELETE. Added an explicit guard fixture and real upstream refusal-of-qualification checks; retained the positive guard assertion. |
| [42360229227](https://github.com/Ares-Empire/AresOS/actions/runs/42360229227) | `Ran 36 tests`; `FAILED (errors=1)`: base schema omitted `refused`. Extended the schema to the design's outcome. |
| [42360489687](https://github.com/Ares-Empire/AresOS/actions/runs/42360489687) | `Ran 41 tests`; `FAILED (errors=39)`: capability bytes broke stdlib ENABLE. Restored stdlib string capability types and consistent checks. |
| [42360763279](https://github.com/Ares-Empire/AresOS/actions/runs/42360763279), [42360879730](https://github.com/Ares-Empire/AresOS/actions/runs/42360879730) | `Ran 43 tests` / `Ran 44 tests`; both `FAILED (failures=2)`: reservation fixture created an unrelated earlier reservation invalidated by restore, and the distinct-user daemon lacked a writable socket directory. Removed the unrelated fixture reservation and pre-created the service-owned directory; assertions preserved. |
| [42361010616](https://github.com/Ares-Empire/AresOS/actions/runs/42361010616) | All 57 base + 44 Mail tests passed. |
| [42361308196](https://github.com/Ares-Empire/AresOS/actions/runs/42361308196) | All 57 base + 46 Mail tests passed, including partial targets and STARTTLS. |
| [42361409975](https://github.com/Ares-Empire/AresOS/actions/runs/42361409975), [42361466528](https://github.com/Ares-Empire/AresOS/actions/runs/42361466528) | Both 57 base + 47 Mail tests passed, including 240-item paging and Unicode byte bounds. |

**run — local read-only checks:** `python3 control/generate.py --check` printed
`Generated artifacts match definitions`; AST parsing every `control/**/*.py` printed
`Python syntax OK`; `git diff --check` printed nothing. The scope check printed no
changes under `os/`, `mod/`, the excluded owner/install files, or `control/tests/`.
The worktree size scan printed `Remaining .work files over 500 MB: []`.
All pushes used normal verification, no `--no-verify` or force push.
Local Docker was unavailable; no container/build installation was attempted on this Mac.

The report-inclusive commit additionally clarifies untrusted-data wording in the
generated descriptions and asserts actual Docker internal-network/no-published-port
configuration before Mail tests. It changes no Mail transport/operation code. Its
**two completed Mail workflow executions and exact final head** are recorded in
[draft PR #9](https://github.com/Ares-Empire/AresOS/pull/9)'s validation section after
this commit is pushed, avoiding an endless report/head update cycle. Both final
executions include the whole base suite; the independent base workflow also runs.
Fourteen workflow executions preceded this final report push; the final push adds
three (push Mail, PR Mail, PR base), within the brief's approximate twenty-run budget.

## JUDGMENT-CALL

- **read — draft updates:** new revisions retain old drafts, and sending retains the
  source draft. Silent replacement/removal would be a delete through a change tool.
  Exact old-draft deletion asks separately. Replacing in one free call was rejected;
  changing this later needs an explicitly approved deletion operation.
- **read — asking shape (updated round 12):** reuse brief 18's shared `{question, operation_id, description}` envelope
  instead of a second incompatible root schema. `operation_id` is design's service-
  issued `request_id`; description repeats the composition id/hash and all approval
  facts. Preparation is a separate change action. Altering any displayed field is
  refused. Changing the shape later affects both base callers and managed ask tests.
- **read — Sent detection:** missing evidence in a bounded window cannot prove the
  server will never save a delayed copy. Negative probes leave onboarding unready
  until owner-only `account_settings` confirms client/server policy. No probe retries.
  The alternative was silently treating absence as proof. Owner confirmation is a
  one-time setup cost; later automatic detection needs a provider-qualified bound.
- **read — repairs:** require the durable final DATA acceptance before repairing a
  local stage. A Sent copy alone does not identify all accepted/refused recipients.
  Unknown without that proof remains for owner inspection; no new SMTP path exists
  in repair. Relaxing this requires qualified per-recipient server evidence.
- **read — exact attached mail bytes (updated round 5):** received and sent
  mail attachments are rebuilt from the brief's message/MIME header allowlists,
  recursively, including implicit digest messages. Original Bcc, all Resent and
  unlisted headers cannot survive. Marked/Drafts sources, ancestors and nested
  messages refuse before reconstruction; no attachment disclosure exception remains.
  Original decoded binary leaves stay byte-exact; headers, folding and transfer
  encoding may change even without Bcc. The frozen octet-stream `.eml` binds the
  approved hash to sent bytes. Read/source-save exports remain original. Passing
  original blocks through or deleting only selected headers was rejected after
  repeated bypasses. Native recipient attached-mail presentation is unqualified;
  see round 5's sourced recipient-program/file presentation judgment call. Changing
  this needs exact-byte tests and owner qualification of the new MIME behavior.
- **read — bounds:** 25 MiB per transferred file, 64 MiB per encoded source/outgoing mail,
  6,000-character body pages, 20 summary items/page maximum and a 10,000-message full
  history scan bound. Search retains summaries rather than all fetched bodies;
  contact/thread indexing uses headers only. The first implementation deliberately rereads authoritative
  state even with synchronization extensions. A durable incremental history index
  and large-account tuning are follow-up work; unbounded memory/time was rejected.

## PLAN-GAP

- **run/read — positive folder guard:** GreenMail 2.1.15's store rejects nonempty
  deletion, but its IMAP host first removes the messages. Dovecot 2.3.21.1 also allows
  nonempty deletion. Both are truthfully left unqualified by onboarding. The positive
  race check uses an explicit test-only serialized IMAP frontend over real GreenMail:
  STATUS+DELETE and all frontend writers share one command lock. It covers adapter
  behavior, not an upstream feature or the real provider's atomicity. No production
  shim was added. A genuinely qualifying provider remains an owner onboarding gate;
  elsewhere the owner deletes empty folders in his mail program, as design requires.
- **read — updates versus delete approval:** design calls replacing drafts a change
  while also requiring every deletion to ask. This implementation keeps both
  revisions until a separate named delete, as described above.
- **read — aggregation and performance:** the brief gives a per-file cap but no whole
  encoded-mail/history-work cap. The explicit limits above avoid unbounded service
  memory/work. Accounts beyond the scan bound need smaller selected folders or later
  incremental indexing; only the stated synthetic folder size is claimed tested.

## Protocol references read

**read — 2026-11-07:** official Python
[imaplib](https://docs.python.org/3/library/imaplib.html) and
[smtplib](https://docs.python.org/3/library/smtplib.html) contracts; IMAP
[RFC 9051](https://www.rfc-editor.org/rfc/rfc9051.html); one-click
[RFC 8058 §§3–4](https://www.rfc-editor.org/rfc/rfc8058.html#section-3.2) and DKIM
[RFC 6376](https://www.rfc-editor.org/rfc/rfc6376.html). These informed PEEK/UID use,
explicit verifying contexts, SMTP answer handling, consent/no-context POST and the
DKIM coverage check. Executed compatibility is the pinned Python/server versions
above, rather than an assumption about all versions or providers.

## Not verified / open questions

- **assumed / owner gate:** the real account's aliases, TLS roots, authentication,
  special roles, delayed Sent behavior and server-enforced folder guard; no endpoint
  or provider details were used. No real delivery, account or inbox was accessed.
- **assumed / owner gate:** real mail-client presentation of formatted mail/attached
  `.eml`, terminal/phone approval rendering and the seven fresh Claude tool-user
  rounds. No model or Claude Code ran in CI. The fixed test workflows prove protocol
  behavior, not a usability/model judgment or deployment boundary qualification.
- **read / unrun:** public DNS DKIM interoperability, physical power loss and storage
  controller durability. DKIM tests use independently signed synthetic mail and TXT
  fixtures; unknown/unsupported signatures refuse POST. The base's existing image,
  sandbox and backup integration gates remain.
- No mid-run answer requested. Final workflow ids for the report-inclusive head are
  recorded in the draft PR validation section after the final push, so this report
  need not be changed after the final head passes twice.
