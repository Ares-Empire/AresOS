# Stage 1 coverage contract

Read against Mail `d3babf1f` plus the 19b note, before implementation. IDs M01–M14 preserve **every row**, in order, of round 26b; C01–C05 preserve **every row** of round 27 inventory C. Case names below are executable oracle contracts, not claims that stages 2–3 already work. `G22-*` are initially strict expected failures, never skips. Further failures must identify one assertion, row and closing stage in `KNOWN-GAPS.json`.

The oracle consumes the ordered test script, independently recorded server events and a test-only decoder of committed disk records. It must not use `unfinished()`, pending snapshots, deferred notices, production fingerprints or production warning selection to decide expectations. Production can be imported by the driver and view reader only. Each view is compared separately, before operation status; all pages are drained, with explicit restart on `page_changed` and a progress bound. Normal clean send/move/delete must be quiet.

| Row / owner fact | Source today (files under `control/aresos_control/`) | Required source under R1–R3 | Checks and occurrences | Acknowledgement / action resolution | Oracle cases |
| --- | --- | --- | --- | --- | --- |
| M01 pending, approvals, expiry/cancellation, reasons, recipients, stages | `engine.py`: SQLite `op:`, `_last_pending`, observations | committed reservation, stages, outcome, ack and test/live clock | operation reserved/submitting/terminal; interruptions independent of action outcome | existing notice_ack; cancel/expiry only reserved, failed with notice; partial/unknown remain pending | send, cancel, expiry, delete_trash, delete_permanent; lifecycle, pages |
| M02 MOVE/COPY drift, exact messages/destinations/locations, incomplete scans | `mail/filing.py`: `mail:filing:`, location pages, notices; deferred writes | pre-command account, exact refs and hashes, target, preparation roles; committed scan results + live LIST/locations | open/clean/warning; fingerprint target + role + locations + unresolved roles; incomplete scan remains open | ack occurrence only; done/partial action does not close an unfinished check | filing_move, filing_copy, scan-incomplete, G22-evidence |
| M03 RENAME/folder move, count, roles | `mail/filing.py`: `mail:rename:`, notice and deferred result | account-qualified source/target/count/baseline before RENAME, observed role evidence and committed result | open/clean/warning; fingerprint target + observed role + unresolved roles | ack independent of check; no automatic rename back | filing_rename, review21-ack-expiry, review21-pages, G22-rename, G22-evidence |
| M04 interrupted sends, deletes, folder delete, unsubscribe, probes, repair identity and quiet period | `engine.py`, `mail/adapter.py`: approval/payload/stages/time; compact journal, live evidence | pre-command identities/roles/recipients and committed outcomes; no replay; clock controls quiet period | started/submitting unresolved until committed completion; local repairs have own identity | operation and occurrence resolve independently; never infer delivery from absence | send, repair, status, settlement, delete_trash, delete_permanent, folder_delete, unsubscribe_mailto, unsubscribe_https, onboarding |
| M05 draft APPEND, flag/create/settings/folder-review/testapp configuration interruptions | `storage.py` generic `intent:` only id/action/app/state, audit args, `active_intents` | per-attempt full context committed before mutation, outcome/resolution records | open until committed completion; exact attempted mutation identifies recovery warning | ack warning does not complete mutation or authorize retry | draft_append, folder_create, flag, settings, folder_review, testapp_config; context-order |
| M06 startup/legacy recovery | `recovery.py`: startup_intents, legacy_intents, SQLite notices, deferred RAM | derive unresolved committed sources on every read, conservative missing-context compatibility | open source yields not-yet-checked; no warning for finished legacy operation | durable per-occurrence ack; action resolution separate | restart_index, restart_tail, same-session-intent, legacy, lifecycle |
| M07 Sent duplicates | `mail/adapter.py`: SEARCH, observations, `sent_copy_check`, `warning_checks`, notice | committed message identity and registration plus observed Sent set, recorded occurrence/ack | open/clean/warning; exact account/folder/UIDVALIDITY/UID/Message-ID set, not just count | same evidence preserves id/ack; changed set or committed clean then recurrence creates id; clean retains unacked history | status, settlement, repair, review19, review21-lost-duplicates, review20-archive, lifecycle |
| M08 background storage/expiry, first cause and cleanup | `engine.py`, `results.py`: storage_cause, observations, deferred notices | current admission + committed transaction evidence; RAM wording only | live diagnostic, no historical refusal latch without unresolved transaction | storage restored clears refusal without restart; cleanup cannot overwrite first cause | maintenance, expiry, cleanup-pair, persistent, live-restored, G22-latch |
| M09 restore lock/generation/missing or newer repair evidence | `storage.py`: journal fences/commits, prepared SQLite, head/restore rows, RAM lock | independent committed/prepared evidence + generation; durable free-change projection in stage 3 | lock until confirmed; missing/newer operations unknown; no replay | confirmation changes generation, never acknowledges warnings | restore, restart_tail, restore-lifecycle, decoder |
| M10 index/physical space/history/count/byte/blob admission and cancel/repair/restore/export holds | `storage.py`, `space.py`, `retention.py`, `blobs.py`: live statvfs, DB, RAM ledger/diagnostics | recheck live capacity every call; holds justified by committed sources | no occurrence for ordinary refusal; true unfinished transaction retains latch | released on committed terminal/cancel/settle/saved; restored capacity allows next request | restart_index, send, cancel, repair, restore, attachment_export, testapp_export, password, maintenance, admission, G22-latch |
| M11 export hold/publication/caller rollback/archive manifest | `exports.py`, `files.py`, `proxy.py`, `archive.py`: export rows, saved report, caller inode, manifest/audit | committed hold + publication/report + hash-valid durable export before prune; inspect live destination | open until committed saved/refused; unknown publication explicit; archive never erases open check/unacked warning | report resolves hold; warning ack separate; verify manifest bytes/hash before trusting archived operation | attachment_export, testapp_export, export_rollback, archive, review20-archive, decoder |
| M12 account readiness/setup/probe survival/Sent caveat/folder-delete qualification/protected roles | `mail/onboarding.py`, `mail/roles.py`: account, live LIST, onboarding_id; CREATE/APPEND probe context incomplete | committed exact probe intent before each command, qualification and owner review; current complete/partial role evidence | incomplete setup remains open; negative completed qualification persists as account result; observable Trash survives missing Drafts | owner settings/review completes readiness, not warning ack; no automatic probes; historical Trash/Drafts remain protected | password, onboarding, folder_delete, folder_review, G22-rename |
| M13 every refusal family and reason | request/definition validation, Boundary.reason, policy/files, credentials/TLS, MIME/DKIM, mailbox evidence, volatile cursors | applicable current policy/content/reference/approval/capability/evidence each call | permission/boundary; approval/generation/expiry; reference/cursor/page_changed; account/capability/role; credential/TLS; MIME/DKIM/input/size; provenance/file; transport/evidence; storage/history/quota/index/transaction | refusals never become permanent authorization state; only real transaction latch survives until recovery | refusals (table-driven families), admission, G22-latch, changed-pages; existing suites retain exact input/security assertions |
| M14 ordinary reads/compositions/files/audit, counts/pages/socket/CLI/MCP/hooks disclosure | live mailbox/receiver, SQLite compositions/audit/blobs, RAM observation pages/pending/deferred envelopes | same committed owner facts for all surfaces; passive reads never contact server; bounded exact pages | no new warning from a normal read; evidence reads may open checks; observations supplement only | paged occurrence identity/ack stays stable across channels/restarts | all flows: passive envelope, control_pending, mail_filing_notices, aresos log; testapp pending/notices; pages, quiet, transport |
| C01 duplicate checks after SMTP/APPEND/repair/settlement/status including failed actions | registered `op:sent_copy_check`, live SEARCH, notice | registration before read; all observed fingerprints retained until ack | open before evidence, clean/warning only with result commit | ack never closes open check; archive protected | M07 cases, context-order, round27-mutation |
| C02 MOVE/COPY postcheck role drift/missing COPYUID | started filing source + exact records and paged locations | committed context + partial live roles/locations | open until result committed; missing destination warns | no inverse mutations; ack only occurrence | filing_move, filing_copy, scan-incomplete, G22-evidence |
| C03 RENAME destination/ancestor roles | started rename + LIST + role resolver | retain every observed role even when another unresolved | incomplete stays open; role evidence fingerprint | expiry/archive independent of ack/check | filing_rename, review21-ack-expiry, G22-rename |
| C04 location scan completeness | started/check_open filing; committed incomplete pages | complete/partial scan evidence committed separately from action end | incomplete check stays open; changed locations new occurrence | ack does not certify scan | scan-incomplete, lifecycle, G22-evidence |
| C05 owner setup/Sent-policy/nonempty DELETE probes and cleanup | incomplete account and approved probe operations | exact CREATE/APPEND/delete/send context before commands and retained qualification | open/clean/warning including negative completed qualification | only owner completes setup, never auto replay | password, onboarding, folder_delete, context-order |

## Execution contract

The 22 inherited sweep flows are send, repair, delete_trash, delete_permanent, unsubscribe_mailto, unsubscribe_https, status, settlement, cancel, restore, attachment_export, testapp_export, password, filing_move, filing_copy, filing_rename, expiry, maintenance, restart_index, restart_tail, export_rollback, archive. Additional mutation flows: draft_append, folder_create, folder_delete, onboarding, flag, settings, folder_review and testapp send/delete/configuration. Modes: clean, every discovered single fault, persistent exhaustion, primary/cleanup pairs, crash/restart, and restored space without restart. The driver records any undelivered call reply before a restart. Each mode must compare equality (extras also fail), not union the views or use subset assertions.

Warning lifecycle in the oracle: check state, occurrence identity/fingerprint, acknowledgement and action outcome are four independent facts. A committed clean result starts a new evidence epoch; it never erases unacknowledged occurrences. Repeated identical evidence retains an occurrence and its acknowledgement. Acknowledged occurrences must not return after expiry, archive, rollback, restore or restart. Unknown on-disk versions fail decoding explicitly rather than silently treating the store as empty.

## Initial assertion-specific gaps (stage 3)

1. G22-rename (M03/M12, C03): live post-RENAME LIST observes Target=Trash with Drafts unresolved; its warning must retain Trash and its check remain open after ack/expiry.
2. G22-evidence (M02/M03, C02–C04): a refused recovery-result commit must retain the newly observed Trash occurrence even if Target becomes ordinary before the next read.
3. G22-latch (M08/M10/M13): ENOSPC before any journal bytes, successful truncation/cleanup, then restored space must allow the next harmless write without restart.

Stage 1 stops with these production failures exposed. Context deficiencies belong to stage 2; projection/read/refusal/restore deficiencies belong to stage 3. Stage 1 changes only the required notice-paging description; production behavior is unchanged.

## Executable stage-1 map

The shared expectation code is `control/owner_state_oracle/{records,context,local,model,compare,gaps}.py`. It has a standard-library-only import test. The production-facing recorder is `driver.py`; `owner_state_cases.py` supplies focused fixtures. Diagnostic gap collection is removed before stage-1 verification; final `KNOWN-GAPS.json` records exact deltas, every page on which each occurs, its matrix row and closing stage. A changed delta, unexpected pass, missing per-case view or unexecuted suite entry fails. The four new-sweep shards partition primary fault numbers across every flow; three isolated test processes per shard divide that work further. Each primary keeps all its modes, cleanup pairs and crash cases. Clean cases run in every worker, and a partition test checks exhaustive, unique ownership. Child failures make the CI job fail; inherited sweeps remain in the parent process. Implicit calendar reads follow the effective scenario clock, including retention advancement; installed real-process log checks handle midnight with a bounded restart.

| Contract | Executable evidence |
| --- | --- |
| All 22 inherited flows plus the ten extra flows above, single/persistent/cleanup-pair/live-restored/immediate-crash modes | `test_owner_state_sweep.OwnerStateSweep`; each public view is checked independently. Crash bytes are captured before owner reads or close; locked startup is compared before confirmation, then again after confirmation. |
| M01 reasons, approval recipients and stages | `compare.pending_facts` compares state/reason; `Driver.compare` checks exact saved approval/stages/state only after warning views, and `Oracle.completion_errors` checks raw delivery/recipient/target evidence. |
| M02/C02/C04 exact references, COPYUID, scan completeness and fragments | Raw command/response logs, `Oracle.locations`, `Driver.compare` location traversal; focused `scan-incomplete` and `missing-copyuid` cases. |
| M03/C03 quiet ordinary rename, role drift and historical-source isolation | Focused `quiet-filing_rename`, `review21-ack-rename-expiry`, `review21-four-renames-all-pages`; oracle mutation tests reject binding an older same-target attempt. |
| M04/M05/M12 exact R2 context and order | Every mutation carries an independent decoded pre-command snapshot and call-start sequence. `context.bind/required/decode/differences` bind one current attempt and compare exact fields; unrelated history cannot supply missing context. Local testapp deletion, settings and role-review effects are replayed against prior committed context and exact scripted arguments; Receiver CONFIGURE is logged before its separate-database effect. Protected-root loss and extra local deletion have breaking-mutation tests. |
| M06 old records | `legacy-open-intent`, `legacy-ack`, `legacy-finished-send`, `legacy-new-reservation` and `legacy-new-cancel`; reopened old-record stores accept new work, and production storage remains Mail's format throughout stage 1. |
| M07/C01 lifecycle | `lifecycle-first/ack/changed-set/clean-retains-unacked/recurrence/archive/expiry/restart`; self-tests require independent raw clean evidence before a committed clean result can reset an occurrence epoch. |
| M08/M10/M13 live refusals and holds | Persistent exhaustion and restored-space phases; decoded holds versus actual ledger; focused admission restoration; named G22-latch and table-driven permission/cursor/account/reference/role/input/file/transport/credentials/TLS/DKIM/provenance/capability cases. |
| M09 restore | `restore` flow; pre-confirm crash-locked comparisons; `restore-before/after-False/True` retain independently witnessed warnings/acks through an older SQLite backup. |
| M11 publication/rollback/manifests | Export/rollback/archive flows; caller bytes/hash/report comparison, committed export holds, hash-valid archive decoder before accepting pruned events. |
| M12/C05 qualification | Full onboarding flow and `qualification-probes`, `qualification-protected-roles`, account refresh and incomplete-setup disclosures. |
| M14 channels and paging | Each page's identities, totals, duplicate detection and advertised continuations; `test_owner_state_channels` uses the installed socket, CLI, actual MCP process and both hooks. The envelope's own pending cursor is tested separately. Every read also retains exact advertised-schema failures as separate strict assertions; a focused testapp status storage-error case verifies the failure and restored response. |
| Reviews 20/21/22 | Named regressions in `test_owner_state_regressions`; independent `review20-refused-reopen-archive`, review-21 focused cases and three `G22-*` ledger assertions. |
| Quiet normal use | Clean send, move, copy, ordinary rename and both delete modes; these fixtures do not create delayed duplicate Sent copies or role races. |

An advertised Mail-notice continuation belongs to its original view: its head, total, action and every continuation page are validated. It never replaces an unchecked head. Pending envelopes likewise follow their own token; a token that only restarts a different scope is an exposed stage-3 gap, not accepted pagination.


## Stage 1, fixes round 1 additions

**Read — source:** lifecycle transitions now require scripted acknowledgement/resolution and independent result evidence; no production `ack`, closed-check or archive-removal flag is its own justification (M01/M02/M03/M06/M07). Command authorization compares script/approval → context and script/approval → command independently, including exact UID, folder, recipient, flag and repair stage (M04/M05/M12). Every read compares permitted success/error status from faults and transaction evidence, including empty catalogues (M08/M10/M13). Background-storage expectations preserve the script's first maintenance fault through failed writes and restart (M08). Every recorded action/error/continuation response has a frozen envelope comparison (M14). Completed qualification and Sent caveats are independently checked on the onboarding result, account reads and restart (M12/C05; `qualification-probes-restart`). Recovery/unchecked handles are compared explicitly; semantic occurrences may bind a later persisted handle without losing acknowledgements (M06/M07). Audit projection equality includes operation identity, explanations, structured evidence and untrusted marking (M14).

**Read — executable mutations:** `StageOneFixMutations` in `test_owner_state_oracle.py` covers all nine findings, including spontaneous acknowledgement, acknowledgement closing a check, unresolved reservation removal, coherent wrong UID, empty healthy `storage_limit`, lost/present background warning and first cause, missing original/error/page envelope warning, readiness/Sent/negative qualification, changed recovery handles, audit field/marking loss, and failed persistence → binding → acknowledgement. D3's generic alternative requires a committed matching warning and an open check; tests reject uncommitted, closed or merely unchecked alternatives.

**Read — ledger:** the format-3 groups pin exact assertion keys with rows/stages/deltas using counts and SHA-256. The fixed twelve ownership buckets match the CI split; self-tests verify every group is owned exactly once, with shared clean/suite groups checked by every eligible worker. Full lists remain in `.work/` artifacts, never in Git.

**Read — audit repeatability:** caller fixture directory names encode flow/mode/fault/cleanup/live-or-crash without changing the original path width. Identical shared cases hold an advisory lock until cleanup. The inherited sweep keeps its original caller factory; only owner scenarios opt into the deterministic one. `OwnerStateSweep.test_export_repeated_fault_uses_same_caller_path_and_exact_delta` verifies fresh-scenario trace/delta equality, and the public-audit self-test still rejects a different literal target. The offline historical capture converter never participates in runtime comparisons.

### Stage 1, fixes round 2

M14 expiry/cancellation obligations survive a false `notice` flag, archive and
restore until the matching scripted committed acknowledgement. M04/M05 command
authority includes the independent Trash destination and the complete requested
flag plan. Every public original/error/continuation response requires its own
envelope, including onboarding's special request method. M12/C05 probe outcomes
and qualification reasons require correlated delivered replies and ordered
commands/commits/faults. `StageOneRoundTwo` adds breaking mutations and positive
controls for these cases, terminal/stage claims, metadata and decoder history.
The exhaustive production-field audit is in REPORT.md's round-2 table.

## Stage 1 round 3 structural checks

All rows also run through the monotonic source/kind obligation registry and the
single `resolutions.RESOLUTIONS` allowlist (`FORMAT.md` lists required proofs
and permitted discharges). The systematic test records all 53 focused contract
states, all named review-20/21/22 regressions, and sweep samples covering every
mode. It mutates every boolean/state/outcome/stage-result/effect/hash field, every row/version and
committed sequence, and restore markers, requiring a new difference or exactly
unchanged expectations (including holds and qualification).

| Coverage | Added direct protection |
| --- | --- |
| M04, M05, C02 | Initial payload and completion against every scripted approved effect; exact deletion targets, recipients, folder and repair stage |
| M06, M10 | Total state transition gate; unsupported `reserved → refused` and `unknown → reserved`; holds/recovery survive rollback to an existing older row |
| M09, M14 | Bounded restore intervals, independently observed historical presence/content, explicit scripted legacy fixture inputs, and later missing-sequence rejection |
| M12/C05 | Incomplete-account recovery through restore/deletion, including a restore in the first reply, until corroborated onboarding completion |
| M02/C02/C04/M14 | Source hashes from pre-command message bytes and independently logged destinations; coherent false-hash/false-location disclosure rejected |
| C01–C05, all warning rows | Latest raw evidence and a matching result commit select clean epochs; warning/clean flags are compared claims. Acknowledgements and unrelated commits cannot close checks |

Quiet send, move, copy, rename and delete contracts additionally require zero
oracle lifecycle, clean-result and completion-proof errors. Direct positive and
negative tests bind legacy/current generic intent handles once and corroborate
the real Sent-check opener; a false checked flag cannot suppress enrollment.


## Stage 2 R2 implementation

**Read — source `2eb79db6`, CI source `82902fd8`:** M02/C02, M03/C03,
M04, M05 and M12 now use the shared `aresos_control/action_context.py` commit
boundary. Mail records exact command context on its started filing/rename row
or submitting operation; other free changes have their own started intent and
full arguments. SMTP DATA, APPEND (draft/Sent/probe), MOVE, COPY, STORE, EXPUNGE,
CREATE, DELETE, RENAME, HTTPS POST, receiver configuration/delivery/local stages,
and local test-app deletion/flagging are covered. Repairs use their own identity
with the original message/stage binding. Role baselines and command flags,
recipients, Message-IDs, hashes and destinations remain internal.

`test_action_context` proves command order and failed-commit prevention by kind,
separate free attempts, invalid finished-source rejection, and old/new format
coexistence. The old-store fixture was written by the pre-stage-2 production
code (`fda0d164`); unfinished approved and free work says “not yet checked”,
finished old work stays quiet, and new operations complete. The actual fault
sweep uses the same independent script/server/commit comparison on every call,
mode and fault boundary; stage-2 known gaps must be empty at this stage's head.

**Read — scope:** the implementation covers the R2 portion of these rows; the authorized fold cleared the storage stop and the complete Linux re-pin is recorded below. Their owner-state
read/fallback, occurrence/acknowledgement, restore and current-refusal portions
remain assigned to stage 3. D3 and all three G22 cases remain open; the durable
projection and common owner-state read path are not built in stage 2.

**Run — stage 2 pin:** `LEDGER-S2.json` records 2,200,009 exact stage-3 failures and **zero stage-2 failures** (1,952 groups / 898,329 bytes). Local complete 32-flow captures and all 68 final-source alteration scenarios passed; Linux diagnostics and the required storage stop are recorded in REPORT.md. No final Linux strict pair is claimed.


## Stage 2 fold verification

**Run:** M04/M05/M06/context-order retain their original obligations. Exact
context now joins existing pre-command commits; dispatch independently reads
and checks the unfinished committed source, including current admission.
`ContextWriteFences` covers 129 writes in 20 flows, 1,161 entry/fence failure or
real process-kill cases. The frozen old store and public-audit privacy checks
remain in `test_action_context`; no approval or question field changes.

`LEDGER-CAPTURE-S2-FOLD.json` pins all 53 fresh complete Linux actual lists:
**1,849,228 stage-3 keys / zero stage-2 keys, 1,936 groups, 890,087 bytes**.
All owned/shared groups strictly verify. The inherited direct archive and real
HTTPS test fixtures were corrected without changing these independent inputs;
REPORT.md records their diagnostic failures and fixes. Final Linux strict-pair
evidence follows there. Stage 3 is not built or claimed complete.


**Run — final R2 acceptance evidence:** Control base `42764959121`, Control Mail
`42764959165` (all 56 jobs), and Control boundary `42764999307` each pass attempts
1 and 2 on `be8ea4ca20064d403702e81e323a9a2bd731f6dd`. Both complete actual-list
merges reproduce the stage-2 fold pin exactly, with zero R2 gaps. Every Mail job
is below 35 minutes. `LEDGER-STRICT-S2-FOLD.json` records exact hashes, output
lines and timings. The lead's stage reviews are still separate from these runs;
R1/R3/projection/lifecycle work remains stage 3.

### Stage 2 fixes round 1 refinements

The full owner sweep now has 34 flows: the original 22, the ten stage-2
additions, LOCAL_FLAG and a separate send_duplicate race. Every existing fault
mode/site/cleanup pair/crash/restart remains selected. Clean send creates one
Sent copy and no warning; the explicit duplicate race retains warning coverage.
M02/M04/M05 require full scripted effect plans, exact role/flag/byte authority
and mutation multiplicity independently of terminal state. M03/C03 check
resolution requires the actual correlated check result, target existence and
complete source-specific scans. RENAME's exact identities are its enumerated
UID namespace, without message-body admission. M10/M13 retain interrupted free
changes, including local flags. The field audit now includes the production
rows copied into server logs; coherent alterations propagate through all copies
and require semantic detection. REPORT.md and FORMAT.md contain the updated
field-audit/resolution tables and validator-specific controls.

The finished local pass and all twelve Linux capture alteration shards agree:
94 recordings, 2,003,694 alterations (257,524 coherent), 14,904 owner-set changes,
zero slipped; all 13 production field-kind controls and seven separate
validator-disable controls are exercised in every shard. The complete fresh
53-list Linux pin has 2,057,880 exact stage-3 keys and zero R2 keys in 928,878
bytes. REPORT.md and LEDGER-CAPTURE-S2-FIXES.json record the diagnostic capture
failures separately from the final strict pair.
