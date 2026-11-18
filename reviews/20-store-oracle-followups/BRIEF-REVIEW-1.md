Codex gpt-6-astra, 2026-11-18. Fresh review of draft PR #105 at `88681cc0`.

I read `AGENTS.md`, the complete brief and its progress file, the previous REVIEW-1, CLASSIFICATION-CHECK and RECHECK-1, KNOWN-GAPS’ final sections and N7, relevant design documentation, and the cited production/oracle code. I also checked current main and PR #72’s current engine diff.

I ran, in disposable exports with the documented managed-settings stand-in:

- Oracle, storage and restore modules: **134 tests OK**.
- Sweep unit tests, excluding the full matrix: **11 OK**.
- Owner-state regressions: **6 OK**, including the currently pinned G22 failure.
- Results and S2 model tests: **30 OK**.
- Mail result/error tests: **8 OK**.
- Independent probes of failed confirms, startup recovery, cancellation/onboarding at H, the proposed latch clearing, and removal of the CLI shortcut.

The initial export runs encountered missing-directory and path-policy fixture errors; corrected runs passed. Evidence is under `.work/review-302/`. No workflows, installed-channel tests, OS tests or host changes were performed. Final Git status has **no tracked changes**; the pre-existing untracked review remains untouched. No file over 500 MiB remains under `.work/`.

The central verified facts hold:

- Failed confirms repeat `storage_limit` after faults end; restart unlocks without changing the already-applied generation.
- At restore points **26, 40 and 73**, bypassing the special startup replay leaves both store and oracle locked, with **zero lock disagreements**. The proposed independent startup obligation addresses a real blind spot.
- At cancel **69/single** and **68/persistent**, SQLite head is 6, last marker 5, the store and audit show `failed`, and the oracle expects `reserved`. Restart retains the cancellation. Onboarding’s clean trace has **2,570 points**; at 61/62, the public catalogue discrepancy is **0 versus 1**, as stated.

1. **BLOCKER — “next explicit request” is not enforced by the proposed latch change.**  
   [briefs/20-store-oracle-followups.md:56](../../briefs/20-store-oracle-followups.md#L56), [control/aresos_control/engine.py:747](../../control/aresos_control/engine.py#L747).

   The durability predicate itself is sound and sufficiently narrow: **this invocation’s first fence append in `Store.write` failed; truncation to that invocation’s original offset actually succeeded; its subsequent journal fsync actually succeeded; indexing, SQLite staging and application were never reached.** Under the existing ordering, neither journal bytes from that attempt nor a partial SQLite event can survive that condition. Returning from the `cleanup` context is insufficient evidence because it suppresses cleanup exceptions ([common.py:64](../../control/aresos_control/common.py#L64)). The brief correctly requires actual truncate-and-fsync success and consumption only around the first append.

   However, clearing the latch there does not restrict recovery to a new request. `Engine.request` catches a deferred-notice flush failure and then continues into `_admitted_request`.

   I reproduced this with a scratch implementation that reports rollback success from `_append` and clears the latch **only around `Store.write`’s first append**. A zero-byte failure while flushing a deferred notice was completely rolled back. Nevertheless, the same approved Mail send request subsequently issued **one SMTP DATA**, ended `unknown`, and returned the original `storage_limit`. Baseline issued no DATA and left the operation reserved. See `latch-exact.log` in the reviewer's scratch folder `.work/review-302/` (not committed).

   Require a request-local barrier preventing further app effects after this failure, while allowing the next explicit request to proceed without restart. Specify how it interacts with caught failures and deferred flushing; changing the final error envelope alone cannot enforce it. Add a named regression and mutation: failed pre-dispatch flush → zero app effects; faults removed → a new explicit request succeeds; removing the request barrier must fail that assertion.

2. **SHOULD-FIX — Add package 43’s concrete CLI overlap before the re-pin.**  
   [briefs/20-store-oracle-followups.md:411](../../briefs/20-store-oracle-followups.md#L411), [control/tests/test_owner_state_channels.py:125](../../control/tests/test_owner_state_channels.py#L125).

   The installed-channel oracle test invokes `['cli', 'log', ...]`. Removing Control’s top-level shortcut makes that call exit **2 before contacting the service**; `['cli', 'control', 'log', ...]` still succeeds. I reproduced both with a stubbed proxy, without running installed-channel tests.

   Therefore package 43 can break the mandatory ledger job even though the storage/model changes are correct. Name the integration dependency and require the channel test to use the canonical command when the shortcut disappears. Keep the oracle’s historical `aresos log` comparison label stable unless a separately classified label migration is intended: [compare.py:325](../../control/owner_state_oracle/compare.py#L325) already calls `control_log` directly.

   The other overlap guidance remains substantively correct. #98 and #97 were already included in the brief’s baseline. #58 has now merged as `beb42ec8`; its changes do not alter the cited storage, engine or oracle logic. PR #72 still wraps the entire request, including reply finishing, in `call_time`. Update the dated table and preserve that scope.

3. **NIT — Disposable exports under `.work/` cannot run every named baseline unchanged.**  
   [briefs/20-store-oracle-followups.md:313](../../briefs/20-store-oracle-followups.md#L313).

   `test_export_repeated_fault_uses_same_caller_path_and_exact_delta` fails before its assertion when the source export is beneath `.work/`. Its synthetic caller home is derived from the source location ([test_review23_sweep.py:269](../../control/mail_tests/test_review23_sweep.py#L269)), and FilePolicy rejects dot-prefixed path components ([files.py:19](../../control/aresos_control/files.py#L19)). The same unchanged suite passed from a temporary export without that component.

   Document an executable-export location without dot-prefixed ancestors—such as an appropriate ignored directory under `control/test-work/`—while retaining logs under `.work/`. Do not weaken FilePolicy to accommodate the review harness.

Item 3 is the correct model correction, not concealment of a store bug. SQLite commits rows and head before the independent marker; ordinary reads, pending replies and the audit log expose that applied state ([storage.py:579](../../control/aresos_control/storage.py#L579), [storage.py:798](../../control/aresos_control/storage.py#L798), [engine.py:203](../../control/aresos_control/engine.py#L203)). Recovery completes it. The brief correctly keeps marked history separate, requires lifecycle/effect validation of the applied tail, preserves restore-lock hiding, and leaves Chrome’s committed projection alone.

Apart from finding 1’s missing request-boundary test, the mutation table names a relevant rejecting test purpose for every mutation. Final test IDs appropriately belong to the builder. The re-pin shape is checkable: G22 closes through healthy retry; startup and restore-lock discrepancies stay zero; N7’s false row differences disappear without indiscriminately deleting H’s other defects; unrelated semantic deltas remain. I verified the pin’s hash, size, group count and total; I did not independently re-download and reclassify the historical 53 lists.

The owner question is appropriate and **“yes” is sound**, subject to fixing finding 1. Replace “the first journal append was fully undone” with “the failed save was completely undone,” and give a concrete example: a saved cancellation remains visible even when the request reports a storage error. Make clear that fixing storage and restarting the tool service is the recovery action; it does not resend anything.

NOT READY