# Test decoder contract (Mail format at d3babf1f)

No expectation module imports `aresos_control` or the driver. `records.py`, `model.py` and `compare.py` use the standard library only. The test driver is allowed to invoke production APIs and record their replies; a reply never supplies its own expected warnings.

`evidence/operations.jsonl` is ASCII canonical JSON (sorted keys, separators comma/colon), one LF per record. A format-2 fence has format, seq, previous, time, generation, operations and hash. Hash is SHA-256 over the canonical object without hash; previous is the preceding fence hash (initially the empty string). A commit marker has commit=seq and matching hash. The decoder rejects corruption and unsupported versions; only an unterminated final line can be ignored. Format 1 is accepted with the same hash-chain contract.

`state/control.sqlite` contains events(seq,value), head(id,seq,hash), kv(k,v), retained(k,created), operation_versions(id,seq). The decoder reads events and head, **never kv or the production index**. Each event contains seq/time/action/summary/outcome/operation_id/set/record and optional space/untrusted_content. Its record must equal the independent fence. Only a matching commit marker makes set's values committed (null deletes a key). Prepared events are separate evidence, never completed actions. Immutable events recover state without relying on working warning selection. Archives are JSONL `aresos-history-1` exports containing event or key/value entries; only a manifest in committed history, with matching SHA-256, authorizes reading their events. Projection format will be added in stage 3 without changing old records.

Server trace entries carry call correlation, command, account, selected folder, exact message identities (including raw-byte hash/Message-ID where applicable), roles, attempted/accepted and reply delivered/lost. The script carries ordered action/arguments, clock, fault number/label/mode/cleanup point and delivered/lost caller reply. Traces stay in memory outside fault injection; optional JSON exports are written after faults end. Credentials and AUTH arguments are excluded. The oracle retains evidence independently of whether the service commits its warning. Occurrence UUIDs are opaque: the decoder binds them to independently selected evidence; changing or deleting a notice cannot delete an expected occurrence. Unknown UUID binding is explicit `uncommitted:…` and fails comparison.
Pre-command snapshots include the committed sequence, the creation sequence of each source and the scenario call's start sequence. Explicit approved operation IDs bind exact operations; repairs follow only their own `repair_of` link. Free filing/rename intents must belong to the current call, account and target. New generic contexts use command/account/identities/source/destination/roles/recipients plus command-specific flags, wire hash or POST body. `context.py` also decodes the existing Mail payloads. A historical row with matching strings cannot satisfy another attempt.

Occurrence fingerprints use the documented current encoding: Sent evidence hashes the sorted set of canonical reference strings; filing/rename hash their target, observed role, unresolved roles when recorded, and normalized scan evidence. The opaque UUID is bound only to the matching source/kind/evidence fingerprint. Public app/state, intent and operation/filing identity, count, folder summary and warning semantics are checked separately from UUID binding.

A committed production `clean` bit is not independent clean evidence. Epoch changes after a warning require a matching raw clean read and a result commit after that read, within that exact scripted call's commit interval. A false clean claim is an oracle violation and cannot resurrect an acknowledged occurrence. Check state, occurrence, acknowledgement and action outcome remain separate.

The decoder recovers a byte copy of SQLite and its hot rollback journal under the test worktree, outside injected faults. It never repairs the production store as a side effect of observing it. A separate crash branch copies bytes before any view or orderly close, reopens those bytes, compares a restore lock before confirmation and then compares the confirmed generation. Ordinary audit paging uses the documented five-item default; pending is also stressed at one item, and all pages and duplicates are checked.

CI uses separate Python processes for the owner sweep because raw-I/O injection and SQLite VFS hooks are process-global. Primary fault ownership partitions across four shards and three workers using one stable SHA-256 of flow/primary-point: value modulo shard count, then its quotient modulo worker count. This breaks alignment with periodic syscall patterns; all modes, cleanup pairs and crash phases stay with the primary. Clean cases run on every worker. Each worker checks its exact ledger scope. The parent preserves every inherited test, captures child output separately, checks every exit status and terminates unfinished children on failure.

Local effects are audited from ordered decoded event sets, including prepared effects, against preceding committed rows. Testapp deletion requires a prior submitting operation and exact scripted approval/references; only approved subsets may disappear, survivors stay unchanged, and done requires the full approved set removed. Settings and folder review require a current intent with context.account, context.arguments and context.roles matching the script and prior account; effects must match those arguments. Folder review retains the exact historical/previous/current Trash/Drafts root union, resolving legacy delimiters only from same-call LIST evidence. Receiver CONFIGURE has its own pre-effect snapshot and exact raw arguments, since its database is separate. Ordinary reads cannot create new local mutation events; finishing a previously known prepared marker is allowed.

The actual-response reader still executes the existing transport and advertised-schema validator. A schema ValidationError from that exact validator invocation becomes an assertion-specific actual defect with every schema path, constraint and missing/extra key; the strict gap comparator sees it on every call, including repaired replies. Unrelated exceptions and transport assertions remain hard failures. This actual-view reader imports the public schema machinery; no owner-state expectation module imports it or any production module. Owner facts are still compared against the actual returned reply.

The scenario clock also drives no-argument localtime calls; explicit timestamp conversion delegates to the saved real function. Retention/expiry clock overrides remain effective. Calendar patches and request hooks restore on normal close and constructor failure. Installed CLI audit paging filters the independently decoded current day and uses the same bounded restart counter for midnight and page_changed.

Fixture UUIDs use a scenario-seeded pseudo-random stream, with unique version-4 values and nonmonotonic ordering. Recovery sorts opaque IDs, so an uncontrolled UUID stream would change which operation an injected boundary interrupts. The stream resets for each fault replay, continues across Engine restarts, and is restored with the clock hooks. Nanosecond timestamps follow the effective scenario clock too, so notice ordering cannot depend on the wall date. Expectations still compare exact source/occurrence identities and every fault/mode; no ordering or failure assertion is relaxed. A focused test checks repair binding with both parent/repair ID orders.

Notice pages sort newest first by creation time and the independently decoded public notice ID. Operation recovery uses `recovery-OP`; an unchecked Sent check uses `sent-check-` plus the first 32 hex digits of the canonical operation-ID digest. Export recovery uses `recovery-EXPORT`; account/legacy recovery hashes the full source key. Generic and filing/rename recovery use the committed source ID; an acknowledged filing/rename base occurrence with an open check uses `check-` plus the canonical source-key digest. Bound warning occurrences retain their own ID. These distinct IDs order recovery and unchecked groups even when their source/time is identical; Python set iteration never selects a page slot.


Stage-1 fixes round 1 validates lifecycle claims against the script and raw evidence before selecting owner obligations. A scripted acknowledgement and its matching committed transition acknowledge exactly that occurrence; acknowledgement cannot close a check. Closing a check requires an independently observed result and a later commit in the same call. Archive removal cannot resolve a live reservation. Unjustified transitions produce explicit lifecycle-proof differences and leave the obligation visible. Installed-channel scenarios record their actions too.

Semantic occurrence identity is `(source, kind, canonical evidence, committed-clean epoch)` and remains stable while its public handle is unknown. A later matching committed occurrence binds that handle without changing semantic identity; a changed handle after binding is a discrepancy. Recovery and unchecked notices carry separately compared public handles on every page/read/restart. Background-storage warnings use the script's maintenance phase and first injected cause (cleanup never replaces it), and remain expected across failed persistence and restart.

Read success/error status is checked even for an empty view. Permitted refusals come from current fault traces, admission/capacity and decoded transaction/restore evidence, plus raw failed reads. Returned error codes never select expectations. Every recorded response, including original action/error replies and continuation replies, has its own frozen passive-envelope comparison before subsequent reads. Completed qualification is derived from the bounded onboarding probe logs plus its result commit and subsequent scripted owner settings; readiness, Sent policy/caveat and negative DELETE qualification are compared after reads and restarts. Public audit equality includes sequence/time/action/outcome/operation identity, explanations and structured evidence, preserving the documented untrusted wrapper and bounded historical filing projection.

The compact format-3 gap ledger hashes canonical newline-delimited `[assertion-key,{row,stage,delta}]` entries, sorted by exact key. Groups bind suite, one fixed ownership bucket, matrix row and closing stage. Twelve buckets map wholly to four CI shards × three workers; point-zero groups are shared. Counts, samples, digests and owned-group completeness are all strict. Full actual lists are generated under `.work/` and uploaded by the existing artifact steps; see `KNOWN-GAPS.md` for merge/regenerate/diff commands.

D3 (recorded for stage 3): reserve evidence-record capacity through `space.py` before a remote evidence check. A failing disk must leave the check open and retain either the specific observed occurrence or a committed generic “evidence was seen but couldn't be recorded; check Trash” warning. `retained_role` accepts the generic alternative only with a matching committed notice and an open check. An ordinary “not yet checked” notice alone does not meet this obligation. This stage implements only the oracle contract.


Full audit comparison includes caller paths. Owner fixtures therefore use fixed-width, injective caller directory names from flow/mode/primary/cleanup/live-or-crash, with advisory locking until cleanup when cases overlap across workers. Their width matches tempfile's original `tmp` + eight characters, preserving serialized record lengths and fault-boundary layouts. Production tempfiles and inherited sweep defaults are unchanged. The offline `caller_capture.py` tool can replay that declared input in historical full captures and rejects conflicting targets within one script. It is never used by expectations or the strict checker: runtime audit equality and deltas retain every complete literal path.

Stage-1 fixes round 2 keeps expiry/cancellation notice obligations independently
of `notice` and protects them through archive/restore until an exact scripted,
committed acknowledgement. New terminal/stage claims, incomplete-account flags,
intent/export removals, restore/archive markers and notice metadata are validated
before they can end an obligation. The complete field-by-field audit is in the
round-2 section of `reviews/19b-owner-state/REPORT.md`.

A scripted trash deletion selects the unique Trash role from independent role
evidence. Flag authority is the complete scripted add/remove plan, including a
separate check for omitted commands. Public responses are captured from their
scripted request, including `method=mail_account_add`, even without `pending`;
envelope presence is itself an assertion. Only explicitly named synthetic
maintenance/restart results are excluded. Qualification validates probe results
against exact delivered replies and command/commit/fault order; a production
failure state cannot justify a matching public failure reason by itself.

The decoder validates event times and compact/full operation fields against the
independent fence. Missing current-head history must be explained by qualified
archives or explicit restore history (whose transition is validated against the
script). The owner archive fixture ages its actual commits by advancing the test
clock. It never rewrites their timestamps. The pre-fault fixture history is an
explicit starting-state input; post-seed stage/outcome claims need raw evidence.

## Stage 1 round 3: obligations and resolution authority

The script's approvals select the full effect plan, including every target,
recipient, flag operation and destination. Raw pre-command message identities
carry the source byte hashes. Production payloads, hashes, states, flags and
presence/absence are claims to compare, never a smaller plan. Fixture history
before `Driver.seed_sequence` is an explicit, frozen starting-state input;
changing that input is a difference. Runtime commits are validated against the
script, fault trace, raw server evidence and independent fence order.

`Oracle.obligations` retains each open source and obligation kind with its
establishment sequence. `retain_obligations` requires a corroborated resolution
from the table below before removing a kind, including through rollback to an
older *present* row. Unsupported resolutions report lifecycle differences and
preserve the obligation's fields. Occurrences and qualification observations
remain separate retained evidence; action completion and clean checks cannot
acknowledge occurrences. The table is `resolutions.RESOLUTIONS`; its `ends`
column is also executable, so adding a new production state cannot silently
resolve an obligation.

| Resolution kind | Independent corroboration required | Obligations it may end |
| --- | --- | --- |
| acknowledgement | Exact scripted occurrence/operation identity; matching acknowledgement commit within that call | That occurrence, terminal operation notice, or explicitly acknowledged generic intent |
| submission | Scripted full approval; matching submission commit order | Reservation cancellation hold |
| completion | Scripted approval; every approved effect accepted with the exact identities/recipients; result committed after effects | Approved work, operation recovery, cancellation/settlement holds |
| failure | Fresh submission in the same call, no accepted or lost effect, and a correlated fault or delivered negative reply; result commit order | Approved work, operation recovery and associated holds |
| uncertainty | Correlated attempt/fault; commit order | Cancellation hold; recovery remains |
| clean_check | Independently clean raw evidence; matching result committed after the read in the same call | Open check / unchecked notice; occurrences remain |
| check_result | Raw server result; matching result commit order | Open check / unchecked notice; occurrences remain |
| cancellation | Exact scripted operation; previously reserved; cancellation commit order | Approved work and cancellation hold; creates an acknowledgement obligation |
| expiry | Scripted clock reaches validated reservation expiry; previously reserved; expiry commit order | Approved work and cancellation hold; creates an acknowledgement obligation |
| settlement | Exact scripted repair identity; read-only absence evidence; settlement commit order | Approved work, operation recovery, settlement hold |
| restore | Scripted confirmation after an independently decoded restore precondition; bounded rollback interval; independent commit order | None |
| archive | Scripted archive; no remaining obligation; qualified archive manifest; commit order | None (already resolved history only) |
| onboarding_completion | Scripted account identity; delivered probe evidence; onboarding completion commit order | Incomplete-account recovery |
| intent_completion | Scripted action; correlated effect/reply; result commit order | Generic intent recovery |
| export_publication | Scripted saved export identity; publication evidence or correlated refusal; commit order | Export recovery and publication hold |

A restore interval ends strictly before its restore commit, and begins after the
last present preceding event. It explains only missing sequences within that
interval. A marker at sequence 1 cannot explain a later missing sequence 2.
The decoder checks this even at the current head; the model additionally checks
scripted restore authority. Archives remain hash-qualified, including recursive
manifests. Decoded projections, compact fences and full event operation fields
are compared; an arbitrary decoded flag cannot justify a different lock.

`perturb.py` applies one mutation at a time to recorded contracts, all named
review regressions, and sweep samples covering clean, single fault, persistent
exhaustion, restored space, cleanup pairs and crash/restart. It flips every
boolean, substitutes every other state in the state vocabulary, removes each
row/version, drops each committed sequence, changes every effect identity,
recipient, flag, hash and destination, and inserts a restore marker before each
sequence. Projection-only and coherent event/projection lies both execute.
Each mutation must introduce a specific difference or preserve the exact
expected owner set (including holds and qualification). Existing baseline gaps
cannot excuse a changed expectation: the test subtracts baseline differences.
A deliberate broken-oracle self-test proves that this check can fail. Counts
and scenario labels are printed in the Mail suite log, with `slipped=0` required.

Explicit legacy/interrupted fixture writes made after driver construction use
`Driver.fixture_input`: the test supplies and records their changes before the
write. They are script inputs, not permission for arbitrary production `fixture`
events. The model compares each such input to its correlated commit. Historical
content is also compared against decoded observations captured before server
commands; an observed row cannot subsequently vanish from its own history.

Clean epochs are selected from the latest correlated raw evidence and a later
source commit, once per read/result pair. `warning_checks[*].warning` and
`sent_copy_check.clean` are compared claims; flipping them cannot select a new
epoch or close a retained check. A later clean result still preserves every
unacknowledged occurrence.

The driver establishes initial obligations before the first action or reply. Its
script records the independently decoded restore precondition before each call;
a confirmation request alone cannot authorize a restore marker. A new local
fault cannot settle earlier unknown work, and a failed action cannot hide an
already accepted or lost effect. Generic-intent/export scope comes from the
script and remains immutable. Stage-event metadata is compared to its full
committed stage. Filing clean results use post-command LIST evidence; an outcome
label never selects a clean epoch.

The systematic state vocabulary is the union of the documented states and all
observed state/outcome/stage-result values in the corpus. Generic intent and export app scopes are compared to their scripted action and remain immutable. Event metadata is
mutated too. Fault samples are discovered immediately after an accepted command,
so single, persistent, cleanup and restart samples contain live obligations.
Full location details and permitted request statuses join notices, pending work,
holds and qualification in the exact expected-set comparison.

Expiry/cancellation notices have separate `operation-notice` facts. Their
validated reason survives a later recovery state; a generic restore reason
cannot replace it. Pending pages compare that notice fact with the independently
retained obligation while continuing to count one operation row. A scripted,
committed acknowledgement is the only notice discharge.

Generic intent handles accept the documented legacy suffix or current
`recovery-`-prefixed suffix on first observation, then bind that identity across
history and rollback. Neither form may switch after binding. A Sent check opens
on the actual `mail_sent_copy_check_open` event, correlated with a scripted read
or its raw Sent observation. That event establishes an unchecked obligation even
if its recorded state flag falsely says checked. Ordinary clean send, move,
copy, rename and delete contracts assert that no lifecycle, clean-result or
completion-proof error was introduced by the oracle itself.
