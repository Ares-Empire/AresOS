# Package 18: control base

## Done

**run — [42345618339](https://github.com/Ares-Empire/AresOS/actions/runs/42345618339),
[42345624053](https://github.com/Ares-Empire/AresOS/actions/runs/42345624053)**:
the product tree at `9cf8a11397d6e5d68963d593e9f28403269d6299` passed twice.
This report is the only change after that product commit. The draft
[PR #6](https://github.com/Ares-Empire/AresOS/pull/6) records the final report-inclusive
head and both of its completed workflow runs in its validation section. Those ids
are recorded there after the final push so recording evidence does not change the
commit being tested.

- `control/aresos_control/definitions.py`, `generate.py`, `generated/`,
  `settings/ask-rules.json` and `docs/control/TOOLS.md`: one catalogue for action
  names, effects, closed input schemas, per-action result schemas, descriptions,
  owner-only status, wire tool lists, CLI help and ask rules. Generation validates
  the supported schema subset. Tests compare every committed generated artifact
  and validate successful result contracts with the SDK's JSON Schema dependency.
- `daemon.py`, `protocol.py`, `engine.py`, `storage.py`, `blobs.py`: serialized
  Unix-only service, kernel peer credentials, operation state machine, independently
  retained fsynced event/commit record, SQLite full-sync mirror, generation/restore
  handling, immutable blobs, audit outcomes, pending catalogue, cancellation/expiry,
  adapter submission/evidence/drop/repair hooks. No automatic submission or retry.
- `files.py`, `proxy.py`, `cli.py`, `hooks.py`, `launch.py`: caller-side file
  movement, official SDK stdio MCP server, definition-driven terminal interface,
  both reminder hooks, isolated root-owned executable/import/config chain.
- `testapp.py`: exact item references and revisions, read/flag/send/delete,
  preparation returning the full authoritative approval, status and local repair.
  A separate durable fixture receiver records **every** arrival without deduplication,
  recipient refusals, lost answers, and later Sent-copy/answered-flag failures.
- `control/packaging/` and `control/settings/`: explicitly marked drafts for
  systemd, sysusers, tmpfiles, fixed launchers, MCP, hooks and the generated ask
  list. Draft owner UID zero deliberately prevents unconfigured service startup.
- `.github/workflows/control-base.yml`, `control/ci/`, `control/tests/`:
  disposable Fedora container verification on branch pushes and PRs. No image
  build, model, real account, or changes to `os/` or `mod/`.

The protocol, backup boundary, installation layout, adapter contract and extended
builder guide are in [control/README.md](../../control/README.md).

## Verified

**run — 42345618339 and 42345624053:** GitHub Linux runners, pinned Fedora 45
x86_64 manifest
`sha256:79dd6556b8fe1a559051fad5159d4987ead218f1914e7a5bd20350d9ea0f9e52`.
The container printed:

```text
Python 3.15.0
Fedora release 45 (Forty Five)
Generated artifacts match definitions
Ran 33 tests in 14.544s
OK
Control base suite PASS
```

The PR run printed `Ran 33 tests in 10.416s`, `OK` and `Control base suite PASS`.
Each test's exact output is retained in the runs and their
`control-base-<run-id>-1` artifacts. The workflow runs this command with `pipefail`:

```sh
docker run --rm -v "$PWD:/workspace" -w /workspace registry.fedoraproject.org/fedora:45-x86_64@sha256:79dd6556b8fe1a559051fad5159d4987ead218f1914e7a5bd20350d9ea0f9e52 bash control/ci/test.sh
```

Inside that disposable container, `control/ci/test.sh` installs Python/pip and
util-linux, copies the root-owned executable/configuration drafts to the test
prefix, installs the entire locked dependency closure using
`python3 -m pip install --no-cache-dir --require-hashes --only-binary=:all: --target /usr/lib/aresos-control/vendor -r control/requirements.lock`,
then runs `python3 control/generate.py --check` and
`python3 -m unittest discover -s control/tests -v`. The container is removed afterward.

**run — earlier iterations:** 42344886399 and 42344901796 failed the same MCP
attachment test: traversal opened search-only ancestor directories for reading.
The correction uses `O_PATH` on intermediate directories, retaining `O_NOFOLLOW`
and the restricted user permissions. No assertion was weakened. Runs 42345190445
and 42345195539 then passed 29 tests; 42345359611 and 42345362883 passed 32 tests.
The final product pair above passed 33 tests. The final report-inclusive pair is
recorded on PR #6. Total expected workflow executions for this package: ten,
including the two initial failures and final pair; no model executions.

**read — local completion checks:** `git diff --check` printed nothing and exited
zero. All pushes used normal `git push origin pkg/18-control-base`; no verification
bypass or force push was used. Commit trailers name the required model. No Gradle
process was started. A Python walk of `.work/`, selecting files over 500,000,000
bytes, printed `Remaining .work files over 500 MB: []`. No ISO, image layer or
extracted system image remains there. These are local inspections, not container
test claims.

## Rule → code → test mapping

All test names below are methods in `control/tests/`. **run — 42345618339,
42345624053** applies to every row. Provider/browser-specific semantics remain
adapter qualification, as explained under Not verified.

| Design rule | Code | Executed evidence |
| --- | --- | --- |
| §3: single definition; name/app/effect; input/result schemas; descriptions; generated tools/help/reference/ask list; owner-only | `definitions.py`, `generate.py`, `cli.py`, `proxy.py`, `engine.dispatch` | `Generated.test_artifact_drift_effects_ask_rules_and_owner_only_absent`; result-schema validation in `support.EngineCase.data`; `Integration.test_cli_generated_help_admin_and_today_log`; `test_all_socket_peer_credentials_even_permissive_modes`; real MCP tool listing |
| §4.1: authoritative full asking input, account/all recipients/Bcc/full written text/immutable file references, exact target metadata; state binding; escaping; size refusal | `common.approval_input/visible`; `Engine.reserve/submit`; `TestApp.prepare/revalidate`; `Blobs.read` | `Operations.test_truthful_escape_full_text_size_refusal_and_far_side_evidence`; `test_runtime_revalidates_metadata_even_without_revision`; `test_service_refuses_caller_paths_and_descriptions_do_not_authorize_reuse`; `Files.test_import_immutable_hash_bytes_even_after_source_replacement`; oversize preparation leaves no new reservation |
| §4.2: exact references, stale failures | `TestApp.reference/item/listing`; snapshot-bound cursors in `Engine.page` | `Operations.test_exact_references_metadata_and_delete_targets`; `test_runtime_revalidates_metadata_even_without_revision`; `test_read_is_unchanged_bounded_untrusted_and_errors_actionable` |
| §4.3: reserved before act, hash binding, per-target/stage durability, truthful outcomes, idempotency, cancellation/expiry boundary | `Store.write`; `Engine.reserve/submit/stage/expire`; `TestApp.execute`; separate `Receiver` | `Operations.test_idempotency_hash_and_restart`; `test_cancel_expire_only_reserved_and_notices`; `test_partial_refused_recipients_lost_answer_and_failures`; `Integration.test_simultaneous_same_id_calls_submit_once`; `Crashes.test_kill9_every_send_boundary_never_resubmits`; `test_kill9_reservation_boundaries_never_sends`; `test_kill9_every_delete_target_and_stage_no_resume` |
| §4.3: restart, separate restore record, owner confirmation, generation invalidation, missing operations unknown with descriptions, history/evidence readable | `Store._read_journal/_apply/confirm_restore`; restart transition to unknown; owner-only `control_restore_confirm` | `Operations.test_restore_older_log_rejects_earlier_ids_missing_ops_unknown`; `Crashes.test_kill9_during_restore_confirmation_can_be_confirmed_again`; submitting restart in `test_cancel_expire_only_reserved_and_notices` |
| §4.3: new repair operation points to old; no resubmission; far-side identity/evidence hook and preflight guard | `adapters.py`; `Engine.repair`; `TestApp.evidence/has_submission_evidence/repair/repaired_outcome`; receiver's operation-derived Message-ID | `Operations.test_repair_new_operation_never_submits`; `test_truthful_escape_full_text_size_refusal_and_far_side_evidence`; `Crashes.test_kill9_repair_no_submit_after_restart`; receiver arrival counts unchanged after repair/restart |
| §4.4: caller-side allowlisted imports/exports, no dotfiles/config/credentials, descriptor walk without links, regular/single-link files, size cap, real path, immutable hash bytes, exclusive saves and races | `FilePolicy`; private byte framing in `Proxy.call/Engine.request`; `Blobs` | All seven `Files` tests: regular/size/path, forbidden paths/symlinks/hard links/FIFO, source/parent races, immutable import after replacement and corruption refusal, exclusive saves/config/traversal, destination/link races, hash/metadata checks; `Integration.test_real_mcp_stdio_list_prepare_send_attachment_save_and_hooks` |
| §4.5: reading changes nothing | `TestApp.listing/evidence`; `Engine.pending/page`; no read audit writes | `Operations.test_read_is_unchanged_bounded_untrusted_and_errors_actionable` compares flags, complete item state and event head before/after reads |
| §4.6: structured bounded results, paging/cursors | action result schemas; `Engine.request/page`; `TestApp.listing` | `Operations.test_read_is_unchanged_bounded_untrusted_and_errors_actionable`; `test_result_cap_refuses_instead_of_truncating`; stale cursor test; official SDK end-to-end output validation |
| §4.7: actionable errors | `Refused`; catalogue descriptions; adapter/proxy/protocol error messages | Invalid bounds/unknown fields/stale metadata/reused id/file refusal/partial/unknown cases across `Operations`, `Files`, `Integration`; assertions inspect codes and recovery text |
| §4.8: app content is untrusted data; effects still gate asking names | `untrusted_content` in `TestApp.listing`; descriptions in `definitions.py`; generated ask rules | Read test asserts the marker; drift test checks descriptions and exact equality of ask set with every public send/delete |
| §4.9: changes logged with time/action/input summary/outcome; today's terminal log | `Store.write`; `Engine.dispatch(control_log)`; CLI `log` alias; export intent/completion | `Operations.test_changes_logged_and_pending_in_every_result_and_hooks`; `Integration.test_cli_generated_help_admin_and_today_log`; flag/import/export/repair/send stages exercise audit events |
| §4.10: pending in following app results; Stop and next-prompt reminders; bounded waiting, drop without send, retained expiry notices | `Engine.pending/expire`; cancellation/drop hook; `hooks.py`; managed hooks draft | `Operations.test_changes_logged_and_pending_in_every_result_and_hooks`; `test_expiry_and_cancel_drop_only_reserved_never_release`; `test_cancel_expire_only_reserved_and_notices`; real hook subprocesses, independent service expiry and next-prompt notice in `Integration.test_real_mcp_stdio_list_prepare_send_attachment_save_and_hooks` |

**run — the same pair:** §2's socket identities are tested with genuine separate
processes for owner, another UID, root and service UID on all three sockets. Tests
also deliberately make every socket mode 0666 to prove that the peer check is
independent of path modes. Admin is refused on act and ordinary actions refused
on admin; chrome always refuses. The real MCP server fetches its tool catalogue
from act, transfers an attachment, prepares/sends once, saves bytes and refuses a
save collision. Its fixed launcher ignores planted current-directory modules,
`PYTHONPATH`, `PYTHONHOME`, user-site and vendor `.pth`/customization files; writable
code or missing `-S` is refused.

## Adding a Mail or Chrome adapter

**read — implementation at the tested product commit:**

1. Define its actions/schemas/effects/descriptions, then implement and register
   the `Adapter` interface. Public app names derive from the definitions. Run
   `python3 control/generate.py` and commit the artifacts. Keep secrets and bridge
   configuration on the service side, never in caller files.
2. Implement `prepare` to store immutable payloads and return a service-built
   description. Use `Engine.reserve` for send/delete preparations and late holds.
   `revalidate` must check every approval-relevant fact before irreversible work.
   Use exact provider/browser references; refuse on stale state or unqualified
   concurrent-change protection.
3. Implement `execute` with a stage call after each recipient/target and later
   step. Only an adapter that proves nothing left may raise `NothingLeft`; all
   unqualified uncertainty becomes unknown. Every send/delete effect goes through
   the shared submission engine, regardless of verb name.
4. Implement evidence and local-only repair. Mail derives Message-ID from the id
   and checks Sent before submission; not finding it proves nothing. Chrome binds
   the description to the actual held request bytes and the relevant browser state.
   Repairs create a new operation referencing the old one and must contain no
   submission transport. The adapter decides whether local repairs can resolve
   partial; never infer that unknown delivery is done from missing evidence.
5. Reuse caller-side file framing, pending hooks and expiry. Chrome's bridge must
   itself fail closed and discard holds on timeout, disconnect or restore lockout;
   implement `drop`, never release traffic from it. Add fixtures and kill points
   for every adapter-specific stage, then qualify its actual provider/bridge.

See the longer guide in `control/README.md` before building briefs 19/20.

## Not verified

- **assumed, not claimed run:** actual desktop or phone permission-prompt rendering
  at the chosen 16 KiB limit, the managed permission prompt itself, skip-permissions
  behavior, and resistance to disabling an ask rule. This package never starts
  Claude Code or a model. These remain owner/image qualification gates.
- **assumed, not claimed run:** actual Bazzite installation, systemd hardening,
  backup-tool exclusions, power-loss/storage-controller durability, the sandbox,
  hostile programs outside it, egress/approval surfaces, plugins/LSP/helpers and
  final managed policy. Container tests prove the implemented service/import
  contracts, not the complete §7 security boundary; that is brief 18b.
- **assumed, not claimed run:** real Mail/Chrome semantics, accounts, IMAP/SMTP,
  browser sessions/holds, remote server evidence, and compatibility with other
  architectures/Python versions/filesystems. Python 3.14 has locked wheels but
  this package's executed suite is Python 3.15.0 only. The fake adapter's independent
  local SQLite receiver is not evidence about any real provider.
- No screenshots: this package creates no visual application or model session.
  The future owner phone check must supply actual display evidence.

## JUDGMENT-CALL

- **read / assumed:** defaults are 120 seconds for reserved approval expiry,
  16 KiB canonical asking input, 1 MiB per file, 48 KiB model-facing result, 6 MiB
  transfer frame, and at most ten entries per requested page. Chosen as bounded,
  conservative fake-app defaults; rejected unbounded prompts/transfers and silent
  truncation. The owner must qualify phone display and useful file/hold sizes
  before real deployment. Raising hard caps changes constants/schema bounds and
  requires regeneration/retesting; lowering configured file limits or changing
  TTL needs only root-owned configuration.
- **read:** act mode 0666 with strict peer credentials, inside a service-owned
  0711 directory. A non-root service cannot chown a socket to the owner; rejected
  adding service privileges merely for socket ownership. Tests prove identity
  refusal even with permissive modes. Changing to an ACL or owner group later is
  a packaging choice, with peer checking retained.
- **read:** use `-I -S`, and explicitly add a root-owned vendor tree instead of
  normal site loading. `-I` alone still permits system `.pth` execution. This
  changes installation layout, not the action protocol; packaging must preserve it.
- **read:** hard-linked source files, unusual save basenames, and unsupported
  `O_TMPFILE` filesystems are refused. Rejected permissive link following and
  check-then-overwrite saves. ASCII basenames and one-link imports may inconvenience
  the owner; relaxing them needs equivalent race/credential protections and tests.
- **read:** torn/corrupt independent records fail startup instead of being
  discarded, and the append-only journal has no compaction yet. Rejected recovery
  that could lose operation tombstones or create a replay window. Owner recovery
  tooling and safe retention/compaction would be separate follow-up work.
- **read:** the Stop hook blocks once, then honors `stop_hook_active`, allowing
  Claude to report an unknown outcome rather than looping indefinitely. Persistent
  pending records, the next-prompt hook and service/adapter expiry remain in effect.
  Changing this later is a hook policy change; hooks never authorize submission.
- **read:** CLI inputs use the definition's JSON object with `--input`, instead of
  inventing flags for nested recipient/reference/attachment structures. The command
  tree, help and schemas still come from the catalogue. Friendlier generated flags
  can be added later without changing service actions or their approval contract.

## PLAN-GAP

- **read:** draft 5 §8 calls for the owner to inspect a fake send prompt on his
  phone in brief 18, while this brief forbids running Claude Code/models and requires
  unattended container work. Therefore the base supports the full asking input and
  refuses oversized preparation, but actual terminal/phone display remains an
  explicit unrun owner gate. No rendering or permission-enforcement claim is made.
- **read:** the design's §7 still attributes some boundary checks to brief 18;
  this brief explicitly moves sandbox/hostile-program work to 18b. Only the protected
  proxy/hook launch chain, socket identities and settings drafts are implemented
  here. Exact managed policy still follows owner decision 3.
- **read:** there is no defined backup program or retention policy yet. The separate
  directory and restore fence are implemented and tested, but packaging must exclude
  the independent record from database/data rollback. Restoring both together is
  outside this guarantee. Journal corruption recovery/compaction needs a separate
  design that preserves operation tombstones.

## Open questions

- **assumed / owner qualification:** what prompt cap renders completely on both
  the actual terminal and phone, and what TTL/file cap suits normal use?
- **assumed / owner decision 3:** actual owner UID/home/allowed folders and final
  managed settings, plus the image's policy and backup integration in 18b.
- **assumed / future adapters:** exact provider and bridge capabilities must be
  established by briefs 19/20; no account information is needed or stored here.

No mid-run answer is needed to review this base. PR #6 remains a draft and is not
merged.

## Review fixes

**run — regressions observed before fixes:** test-only commit `dca0785` ran the
implementation from reviewed head `a684496`. `git diff --exit-code a684496 dca0785
-- control/aresos_control control/launch.py .github/workflows/control-base.yml`
printed nothing and exited zero. Workflows
[42346954191](https://github.com/Ares-Empire/AresOS/actions/runs/42346954191) and
[42346958869](https://github.com/Ares-Empire/AresOS/actions/runs/42346958869)
each printed `Ran 37 tests` and `FAILED (failures=10)`. I saw every finding fail:
cleanup deleted the replacement, the outside alias retained `b'exported'`, all four
deadline cases returned `done`, both evidence cases remained `reserved`, and both
large hook inputs raised `JSONDecodeError`.

| Finding | Fix and regression evidence |
| --- | --- |
| 1: failed-save cleanup | `files.py` truncates/fsyncs the pinned inode, clearing renamed/hard-linked aliases without unlinking any pathname. Refusals identify the empty inode, link count, original path and current pinned folder; rollback I/O failure is explicitly `save_incomplete`. `Files.test_failed_save_cleanup_preserves_a_racing_replacement` preserves replacement bytes and metadata; `test_failed_save_clears_hardlink_alias_outside_allowed_folders` requires the outside alias to be empty. `test_failed_save_reports_rollback_storage_failures_honestly` injects truncation/sync failures. |
| 2: expiry after adapter checks | `Engine.submit` checks the deadline after both checks, immediately before recording `submitting`; expiry records `failed`, calls `drop`, and executes nothing. `Operations.test_deadline_crossed_during_adapter_checks_never_submits` covers both checks for send/delete, no arrivals or deletions, one drop, repeated approval and restart. |
| 3: positive preflight evidence | `Engine.submit` durably records `unknown` and the positive finding before fetching evidence details, then persists those details. Extended `test_truthful_escape_full_text_size_refusal_and_far_side_evidence` covers cancellation, expiry, restart and replay without another arrival. `test_positive_preflight_finding_survives_evidence_detail_failure` also checks failed detail retrieval. |
| 4: large hook input | `hooks.main` reads complete input inside error handling. `Integration.test_large_hook_inputs_still_remind_about_pending_work` runs both installed hooks with over 190 KiB of valid input and a pending reservation. `test_malformed_hook_input_gives_explicit_failure_feedback` checks exit 2/stderr feedback without a traceback. |

**run — after fixes:** product head `35a05d5` passed twice in the unchanged pinned
Fedora container: [42347178528](https://github.com/Ares-Empire/AresOS/actions/runs/42347178528)
printed `Ran 40 tests in 16.358s`; [42347182054](https://github.com/Ares-Empire/AresOS/actions/runs/42347182054)
printed `Ran 40 tests in 11.912s`. Both printed `Generated artifacts match definitions`,
`OK` and `Control base suite PASS`, using the Docker command and test script recorded
above. All 33 existing test methods remain; no tests were skipped or deleted.
This appended section is the only change after that product head. The final
report-inclusive head and both completed workflow IDs are recorded in PR #6's
validation section after its final push, preserving the exact tested commit.
Six workflow executions for this follow-up: the regression pair, fixed-product
pair and final-head pair.

**JUDGMENT-CALL — read/run:** failed published saves leave reported zero-byte
directory entries. Linux's pathname unlink cannot condition deletion on inode
identity; deleting after a stat can remove a replacement. The old race assertions
that checked only name removal now require empty output/aliases and explicit
residue reporting. Retrying unsafe unlink was rejected; clearing the pinned inode
protects every alias. Arbitrarily renamed/hard-linked paths cannot be enumerated,
so feedback identifies the inode and known original/current folder locations and
states that limit. Later automatic removal needs a separately qualified publication
design; empty remnants can be removed manually. README describes this behavior.

**read / not verified:** rechecked the [Anthropic hook reference](https://code.claude.com/docs/en/hooks)
for long prompt/final-message inputs and exit-2 feedback; the target remains Claude
Code 2.1.319. No Claude/model or physical storage-failure test was run. Existing
owner/image qualification gates above remain. Locally, syntax parsing printed
`Python syntax OK`, artifact checking printed `Generated artifacts match definitions`,
and `git diff --check` printed nothing. Docker's local daemon was unavailable;
container evidence comes from GitHub. The `.work/` size scan printed
`Remaining .work files over 500 MB: []`. Pushes used the normal pre-push hook, with
no bypass or force push. No additional PLAN-GAP or open question.

## Follow-ups

- **Approval lifetime:** `engine.py`, `daemon.py` and `settings/service.json`
  default to configurable **900 seconds**. `Operations.test_default_approval_lasts_fifteen_minutes_at_boundary`
  uses a controlled clock at 899.999/900.001 seconds, requiring acceptance before
  expiry and `failed`, no arrival and one adapter `drop` afterward. The existing
  adapter-check regression now advances to the actual approval deadline plus one,
  replacing its old hard-coded time 221, which assumed the 120-second default.
- **Files:** `common.py`, `files.py`, `blobs.py`, `engine.py`, `daemon.py`,
  `protocol.py`, `proxy.py` and both settings default to configurable **26,214,400
  bytes**. Upload/download streams acknowledge raw-byte offsets, use at most
  1 MiB per chunk, and verify complete size/hash before publishing or saving.
  The integration tests transfer a 25 MiB-minus-one file through the real proxy
  and service, replace its source immediately after reading, compare receiver and
  saved bytes, reject 25 MiB-plus-one on both sides, and check configured limits.
  Seven malformed streams (cut-off, incomplete, reordered, wrong hash, extra
  bytes, oversized chunk, invalid base64) leave neither a blob nor staging file.
  `Files` also verifies matching defaults and raising the configured limit.
  Existing file tests now use chunk framing and download metadata; their exact
  byte/hash, immutable-mode, replacement and corruption assertions remain.
- **Small restore record:** `storage.py` stages full events durably in SQLite
  before the compact record, then commits SQLite's applied head and the record's
  commit marker. `operations.jsonl` holds only restore metadata, short descriptions
  and timestamped states, with chain/sequence framing. `control_log` reads SQLite.
  `test_record.py` checks absent bodies/attachment data, constant record size,
  SQLite audit history, and missing send/delete descriptions after restore.
  `test_crashes.py` adds `sqlite_prepared` kill points to reservation, submission
  and restore tests, checks that every logged operation remains in the record,
  and fences an uncommitted record whose full staged event was lost to restore.
  All existing kill-9, generation, earlier-id refusal and no-double-send tests pass.
- **Quiet prompt hook:** `hooks.py`, `launch.py` and `managed-hooks.json` name
  each event in its launcher argument and reject mismatched input. Prompt failures
  return 0 without output; a fixed shell guard also discards failed interpreter
  output before Python can run. Integration tests execute the actual managed
  commands with malformed/mismatched/large input, directory stdin, broken config
  and unavailable service. Valid pending-work reminders and Stop's existing
  behavior pass. The old prompt-malformation exit-2 assertion intentionally becomes
  exit 0 with empty stdout/stderr; Stop still requires exit 2 and feedback.

**run — record growth:** at controlled time 1000 and two-digit sequences, the tiny
one-recipient send and a send filling the **16,384-byte approval limit** with a
**25 MiB attachment** each append exactly **4,078 bytes**: six state/stage records
including commit markers, averaging **679.7 bytes** each. The typical three-recipient
send appends **5,560 bytes** across eight records, averaging **695 bytes** each.
Longer descriptions, timestamps and sequence numbers add their actual encoded
lengths; bodies and attachments add nothing. No compaction was added.

**run — verified product `c7ee50b2236e2eab59c99b1b453fb78fed9f3ad0`:**
[42349183171](https://github.com/Ares-Empire/AresOS/actions/runs/42349183171)
printed `Ran 51 tests in 24.179s`;
[42349186335](https://github.com/Ares-Empire/AresOS/actions/runs/42349186335)
printed `Ran 51 tests in 20.145s`. Both printed `Generated artifacts match definitions`,
`OK` and `Control base suite PASS` using the unchanged Docker command/test script
above, Fedora 45 and Python 3.15.0. Transfer instrumentation printed `114 frames,
largest=1398154 bytes (wire limit=6291456)`. All 40 previous methods remain,
with 11 additional methods; no tests were skipped or deleted. README and generated
schemas/reference were updated. This appended report is the only later change;
PR #6 records the final report-inclusive head and its two completed workflow IDs
without changing the tested commit. Ten workflow executions total for this run,
including that final pair.

**run — failed iterations:** 42348857680 / 42348860853 printed `Ran 50 tests`,
`FAILED (failures=4)` because the existing clock fixture still assumed 120 seconds;
42348996859 / 42349000841 printed `Ran 51 tests`, `FAILED (failures=1)` because
Python rejected directory stdin before executing the launcher; 42349152826 /
42349156713 printed `Ran 51 tests`, `FAILED (failures=4)` because the first shell
guard emitted a newline for empty output. The implementation/fixture causes were
fixed while preserving the assertions, apart from the intentional behavior changes
listed above. Local syntax checking printed `Python syntax OK`, generation checking
printed `Generated artifacts match definitions`, and `git diff --check` was empty.
Docker was unavailable locally; full test evidence is from GitHub's containers.
The final size scan printed `Remaining .work files over 500 MB: []`. Pushes used
normal pre-push verification, without bypass or force.

**JUDGMENT-CALL — record format:** this pre-deployment compact format is version 2.
An earlier full-event record fails closed rather than being reset or automatically
migrated; retaining a legacy installation would require a qualified migration or
owner recovery. No existing record was discarded. **Not verified:** legacy migration,
physical storage failures, real accounts, phone rendering and image deployment.
The existing owner qualification gates remain. No additional PLAN-GAP or open question.

## Follow-up fix

**Done — record before SQLite:** `Store.write` now appends/fsyncs the compact
record (`journal_appended`) before committing the full SQLite event
(`sqlite_prepared`), applying it (`sqlite_committed`), and syncing the commit
marker (`journal_committed`). No new boundary or record format was introduced.
Bodies and app data remain only in SQLite/blobs; the existing privacy, constant-size
record and SQLite audit tests still pass. `control/README.md` describes the order.

**JUDGMENT-CALL — ordinary-crash cost:** a record without its matching full event
cannot distinguish a crash from a restored backup. Existing recovery therefore
locks all app access until the owner runs
`sudo aresos admin control restore_confirm --input '{"confirm":"invalidate earlier approvals"}'`.
Confirmation advances the generation, invalidates earlier approvals and retains
every affected operation as `unknown` with its short description, even an
unacknowledged reservation. This is also the cost of an ordinary power loss between
the record sync and the full-event commit. Automatic classification as harmless
was rejected: the compact record cannot reconstruct the lost payload or prove
there was no restore. Removing this confirmation later would need additional
durable proof and corresponding crash/restore tests.

**read/run — recovery with a full event:** when SQLite is not behind any committed
record and its staged event exactly matches the single uncommitted record, startup
can finish that local log transaction. A write cannot return to app work before
its commit marker is synced; no later irreversible work can follow this unfinished
write under the filesystem durability contract. Earlier irreversible work can
already have happened before a stage/outcome write. Recovery never executes app
work, and any recovered `submitting` state becomes `unknown`. No record-only case
is recovered without the owner.

**Tests:** `crash_worker.py` can target each occurrence of a write boundary and
take a SQLite backup immediately before that write. The five new
`Crashes.test_backup_before_first_restart_at_every_*_write` methods run **80 cases**:
all four boundaries in send/delete reservations, submission, every recipient,
target and local stage, outcomes, all three repair writes, and restore confirmation
with both a committed history and an uncommitted tail. The parent copies the backup
before constructing any engine; it never edits the independent record. Assertions
require the fence, restore lockout, owner confirmation, `unknown` descriptions,
earlier-id refusal, durable restart state and no repeated sends/deletes. A sixth
method adds **68 ordinary-crash cases** across every send/delete/repair write and
delete reservation, verifying both automatic local recovery and record-only lockout.

**run — failures observed before the fix:** test-only commit `3cf0e09` retains the
implementation from `a9c0cbd`; `git diff --exit-code a9c0cbd 3cf0e09 --
control/aresos_control control/launch.py .github/workflows/control-base.yml` printed
nothing and exited zero. I saw workflows
[42350144207](https://github.com/Ares-Empire/AresOS/actions/runs/42350144207) and
[42350147384](https://github.com/Ares-Empire/AresOS/actions/runs/42350147384) fail:
`Ran 56 tests in 22.586s` / `Ran 56 tests in 39.653s`, both
`FAILED (failures=20)`. Every `sqlite_prepared` case found the separate record one
write behind, including missing reservations and repairs. Those five tests and
their assertions are unchanged after the fix.

**run — passing after the fix:** product `91c46a34fface5f3d5e1bc5b7cddb51e7be05a95`
passed in [42350285675](https://github.com/Ares-Empire/AresOS/actions/runs/42350285675)
and [42350289160](https://github.com/Ares-Empire/AresOS/actions/runs/42350289160):
`Ran 57 tests in 37.074s` / `Ran 57 tests in 30.099s`, both `OK`,
`Generated artifacts match definitions` and `Control base suite PASS`. These used
the unchanged Docker command/test script above, Fedora 45 and Python 3.15.0.
All 51 previous methods remain, with six additions; none skipped or deleted.
Intentional existing-test changes: ordinary `journal_appended` reservation/send
crashes now require confirmation; reservations are found by their retained
description and become `unknown`, and replay is refused after generation change.
The synthetic missing-staged-event test now kills at `sqlite_prepared`, the new
boundary where both the compact record and full event exist, preserving its
original missing-event assertions. Other replay responses retain schema checks.
The only subsequent changes restore those replay schema checks and append this
report. PR #6 records the final head and its two completed workflow IDs after the
final push; six workflow executions total for this fix, including that final pair.

**run / not verified:** local AST parsing printed `Python syntax OK`, generation
checking printed `Generated artifacts match definitions`, and `git diff --check`
printed nothing. Docker's local daemon was unavailable; full suite evidence is
from GitHub containers. The size scan printed
`Remaining .work files over 500 MB: []`. Pushes used normal pre-push verification,
without bypass or force. Physical power loss, storage-controller guarantees,
real accounts, phone rendering and image deployment remain unverified as above.
No additional PLAN-GAP or open question; no review files changed.
