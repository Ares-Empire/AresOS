Reviewed `60b94384`, angle D. **Four blocking findings and seven should-fix findings**, plus one should-fix outside this angle.

No files were edited, no containers or browsers were started, and nothing was pushed or posted to GitHub. The probes below used production Python methods with SQLite and journal data held in memory.

1. **Blocking — Restoring SQLite resurrects revoked permissions and removes recorded restrictions.**

   **Where:** [adapter.py:547](../../control/aresos_control/chrome/adapter.py:547), [adapter.py:337](../../control/aresos_control/chrome/adapter.py:337), [qualification.py:127](../../control/aresos_control/chrome/qualification.py:127), [storage.py:731](../../control/aresos_control/storage.py:731).

   Authorization, read-only restrictions and qualification gates read the working SQLite rows. Restore confirmation reconstructs operations, but does not reconcile these Chrome records against the newer committed journal.

   **Reproduction run:** Commit an allowed Gemini kind and passing qualification; snapshot SQLite; commit revocation, a read-only restriction and a newer qualification failure; restore the snapshot and call the real `Store.confirm_restore()`. The probe printed:

   ```text
   trusted=True; journal revoked=True
   read-only check=allowed; journal read-only=True
   held qualification entries=1; journal qualification entries=2
   ```

   This permits fresh operations under authority the owner revoked and qualification evidence the service already accepted as failing. Advancing the operation generation does not fix these configuration records.

   **Fix:** Reconcile Chrome policy and qualification state from committed history before releasing the restore lock, or make their authoritative reads use that history. Add rollback tests for revocation, read-only changes and qualification failures, including offline operation after restore.

2. **Blocking — Normal owner-state reads bypass committed Chrome history whenever SQLite remains readable.**

   **Where:** [engine.py:57](../../control/aresos_control/engine.py:57), [engine.py:146](../../control/aresos_control/engine.py:146).

   The committed projection is used for operations and pending items principally after a SQLite exception. Readable SQLite can nevertheless be older than the journal, or contain an applied update whose independent transaction has not finished.

   **Reproduction run:** Snapshot SQLite, commit a Chrome reservation, restore the older SQLite snapshot and set the restore lock. The real pending path returned:

   ```text
   items=[]; total=0; restore_required=True
   ```

   The committed projection simultaneously returned that reservation, with `total=1` and a live stale-session refusal. The owner-visible pending catalogue therefore loses committed work while the journal still contains everything needed to disclose it.

   A second probe failed the completion transaction’s journal commit-marker append. `Engine.operation()` reported `done`, while the committed projection still reported `submitting`. These views disagree about which outcome is committed.

   **Fix:** Derive Chrome operation status and pending state from the committed authority on every read, supplemented by live checks. Keep observed-but-uncommitted completion details separate. Test readable rollback states and failures between SQLite application and the journal commit marker.

3. **Blocking — Restore brings back an acknowledged cancellation as uncertain work.**

   **Where:** [storage.py:414](../../control/aresos_control/storage.py:414), [committed.py:158](../../control/aresos_control/chrome/committed.py:158), [adapter.py:161](../../control/aresos_control/chrome/adapter.py:161).

   Cancellation and expiry acknowledgements live on `op:` rows. The projection’s monotonic acknowledgement handling applies only to `notice:` rows. Restore can then append a replacement operation reconstructed from older SQLite, losing its acknowledgement and changing an already-cancelled operation to `unknown`.

   **Reproduction run:** Commit a cancelled operation, snapshot SQLite, acknowledge it, restore the snapshot and run actual restore confirmation. Before rollback, `chrome_notices` was empty. Afterwards:

   ```text
   projected operation: state=unknown, ack absent
   visible notice: recovery-g:cancel
   reason: Chrome input has an unfinished committed outcome; it may have run.
   ```

   The independent history proves that this operation was cancelled without submission and its notice acknowledged. Restore nevertheless creates new uncertainty about it. This violates the required acknowledgement and resolution lifecycle.

   **Fix:** Preserve committed terminal outcomes and acknowledgements when reconstructing Chrome operations. Cover cancellation and expiry acknowledgements, not just standalone warning rows, across rollback, restore, archival and restart.

4. **Blocking — Finished Chrome checks permanently consume the shared unfinished-change quota.**

   **Where:** [adapter.py:529](../../control/aresos_control/chrome/adapter.py:529), [adapter.py:536](../../control/aresos_control/chrome/adapter.py:536), [storage.py:653](../../control/aresos_control/storage.py:653), [retention.py:90](../../control/aresos_control/retention.py:90).

   Chrome retains completed `intent:chrome:` records. They count toward the shared 512-intent limit, but neither expiry nor the archive path removes them. Acknowledged notices linked to these sources also remain retained because their sources still exist.

   **Reproduction run:** Populate 512 completed Chrome checks, age them beyond expiry, run production `retention.expire()`, then observe another step:

   ```text
   finished checks after expiry=512
   513th check=storage_limit
   Unfinished changes limit: 512 records / 134217728 bytes.
   ```

   The suggested remedies—waiting, acknowledging notices or archiving history—do not reclaim these intent rows. Because the quota covers every `intent:`, this can also prevent Mail changes from creating their recovery intents.

   **Fix:** Add a bounded retirement/archive lifecycle for completed Chrome checks and acknowledged occurrences, preserving immutable history, deduplication and acknowledgement identities. Test more than 512 completed checks through actual public recovery paths and verify subsequent Chrome and Mail work succeeds.

5. **Should-fix — An ordinary stopped submission creates a false permanent interruption warning.**

   **Where:** [recovery.py:62](../../control/aresos_control/recovery.py:62), [storage.py:542](../../control/aresos_control/storage.py:542), [adapter.py:528](../../control/aresos_control/chrome/adapter.py:528).

   `recovery_notices()` now includes every live Chrome check in `started`, including checks still being processed normally. `Store.write()` automatically materializes those notices during subsequent writes. Reserving the stopped submission is such a write.

   Completing the check does not remove the resulting unacknowledged recovery occurrence.

   **Reproduction run:** Execute production `Chrome.steps()` for a `native_submit`, then approve through production `Engine.submit()` using a synthetic extension peer. The operation finished `done`, but `chrome_notices` retained:

   ```text
   state=unknown
   A change was interrupted before its completion was recorded.
   It may already have changed the server.
   ```

   No interruption or storage failure occurred.

   **Fix:** Keep live open checks distinct from durable interruption occurrences. Materialize a recovery occurrence only when its evidence warrants one. Add a clean stopped-submission test that checks the final warning set is empty after successful completion.

6. **Should-fix — Open checks cannot resolve after their browser queue disappears.**

   **Where:** [adapter.py:206](../../control/aresos_control/chrome/adapter.py:206), [adapter.py:492](../../control/aresos_control/chrome/adapter.py:492), [adapter.py:500](../../control/aresos_control/chrome/adapter.py:500).

   Check processing is driven by steps returned by the extension. There is no reconciliation pass over committed unfinished checks. After a Chrome restart loses the in-memory queue, an old check remains `started` indefinitely—even when its original document can no longer exist.

   **Reproduction run:** Commit an observed stopped submission, replace the browser session with a readable new session whose queued-step list is empty, read, acknowledge the recovery occurrence and read again:

   ```text
   source state=started
   remaining notice=check-…; check_open=True
   acknowledging remaining notice=stale_reference
   ```

   Keeping the check open until a result commits is correct. Having no path to commit that result leaves permanent unresolved state.

   **Fix:** Reconcile committed open checks against live session/document identity independently of the extension queue. Commit a non-resumable stale result for vanished stopped submissions; preserve and separately acknowledge any uncertain-activation occurrence. Never replay input.

7. **Should-fix — `chrome_drop` cannot use the recovery admission available to cancellation.**

   **Where:** [engine.py:657](../../control/aresos_control/engine.py:657), [engine.py:538](../../control/aresos_control/engine.py:538), [retention.py:52](../../control/aresos_control/retention.py:52).

   Dispatch treats `chrome_drop` as cancellation, but admission recognizes `_operation_cancel`, not `chrome_drop`. Consequently, dropping a reservation first requires the ordinary 128 MiB history reserve instead of following cancellation’s recovery path.

   **Reproduction run:** Make ordinary history admission refuse while leaving recovery admission available. Through production `_admitted_request()`:

   ```text
   chrome_drop: storage_limit; dispatch not reached
   mail_operation_cancel: successful; dispatch reached
   ```

   Chrome reservations already hold cancellation capacity. The public cancellation action should remain usable when ordinary work cannot be admitted.

   **Fix:** Give `chrome_drop` consistent cancellation semantics throughout admission, recovery classification and storage accounting. Test it at both history-quota and physical-space boundaries.

8. **Should-fix — Exceeding the projection index bound blocks the archive command needed to recover.**

   **Where:** [committed.py:99](../../control/aresos_control/chrome/committed.py:99), [committed.py:136](../../control/aresos_control/chrome/committed.py:136), [engine.py:635](../../control/aresos_control/engine.py:635).

   Every request begins with a pending-state read. If the projection exceeds `MAX_KEYS`, it raises `owner_state_unavailable` before request admission. That includes `control_archive`, which the error explicitly recommends.

   **Reproduction run:** Lower the bound to three, retain four projected keys and issue an owner archive request through production `Engine.request()`:

   ```text
   owner_state_unavailable:
   Chrome current owner-state index exceeds its bound; inspect and archive finished history.
   archive admission reached=False
   ```

   The existing bound-recovery test appends tombstones directly through `Store.write()`, bypassing the blocked public route.

   **Fix:** Preserve access to owner recovery commands when disclosure exceeds its index bound. Return an explicit bounded unavailable disclosure, then allow safe archival and rebuild. Test recovery through `Engine.request()`, including after restart.

9. **Should-fix — The new storage fallback removes Mail’s warning continuation, even without Chrome warnings.**

   **Where:** [engine.py:122](../../control/aresos_control/engine.py:122).

   The fallback unconditionally removes `notices_more`, then restores it only from Chrome’s current catalogue. Existing Mail continuation information is lost.

   **Reproduction run:** Seed the last pending snapshot with three Mail warnings and `notices_more={count:1, action:mail_filing_notices}`. Make the live SQLite read raise `SQLITE_FULL`, with no Chrome warnings. Production `Engine.pending()` returned the three Mail warnings but no continuation or remaining count.

   With Chrome warnings present, the final three-item truncation can also displace cached Mail warnings without accounting for them.

   **Fix:** Preserve the distinction between current Chrome disclosures and unavailable Mail snapshots without discarding known additional-warning counts and routes. Add Mail-only and mixed-app storage-failure regressions. Mail’s behavior is not unchanged here.

10. **Should-fix — Chrome and Mail notice ordering use different timestamp units.**

    **Where:** [adapter.py:154](../../control/aresos_control/chrome/adapter.py:154), [filing.py:264](../../control/aresos_control/mail/filing.py:264).

    Chrome supplies journal creation times in seconds to the shared pager. Mail supplies `created_at` values in nanoseconds. Thus an old Mail warning sorts ahead of a newly committed Chrome warning.

    **Reproduction run:** Commit three Mail warnings dated in 2020 and one new Chrome warning. The shared “newest three” page returned:

    ```text
    mail2, mail1, mail0
    total=4
    ```

    The Chrome warning was reachable through continuation, but absent from the compact disclosure despite being newest.

    **Fix:** Normalize ordering keys to one timestamp unit, with consistent fallback timestamps for synthesized notices. Test mixed-app chronological ordering and page boundaries.

11. **Should-fix — The storage sweeps do not establish the claimed complete fault-mode coverage.**

    **Where:** [test_fault_surface.py:61](../../control/chrome_tests/test_fault_surface.py:61), [test_storage.py:26](../../control/chrome_tests/test_storage.py:26), [chrome_oracle.py:30](../../control/chrome_tests/chrome_oracle.py:30).

    The sweeps disable injection before restarting and comparing state. They therefore do not systematically compare every public view while exhaustion persists, or after space returns without restart. Restart uses a normal close/reopen rather than independently cutting every durable boundary. The writer sweep compares only the Chrome notice catalogue; it does not assert equality separately for pending, log and passive envelopes.

    The oracle imports no production code, which is good, but its expectations are derived primarily from whichever notice and intent rows production wrote. It does not consume the scenario and receiver history to independently establish whether a warning should exist. For example, it accepts finding 5’s false recovery warning simply because production committed that notice.

    **Evidence read:** The retained [Python log](./records/integrate-42773242428-external/python.txt:65) confirms the advertised sweep counts ran successfully. Those counts do not cover the missing comparisons above.

    **Concrete test:** Add the preceding probes to the sweep scenarios. In particular, compare all public views immediately after a failed commit-marker append, before restart; restore older policy and acknowledgement snapshots; and exercise recovery through public actions at quota limits.

    **Fix:** Extend the scenario-driven oracle and fault matrix accordingly. Keep actual persistent-fault, restored-space-without-restart and crash-cut evidence distinct in the report.

Outside angle D, I also found:

12. **Should-fix — Chrome page text loses its untrusted-content marking in the audit log.**

    **Where:** [adapter.py:397](../../control/aresos_control/chrome/adapter.py:397), [engine.py:245](../../control/aresos_control/engine.py:245), [engine.py:495](../../control/aresos_control/engine.py:495).

    Chrome passes page observations into the generic stage summary. `control_log` wraps Mail summaries as untrusted, but does not do the same for Chrome.

    **Reproduction run:** Record a Chrome page stage containing a synthetic dialog text, then call production `control_log`. It returned this ordinary summary field, without an `untrusted_content` wrapper:

    ```json
    {"summary":"stage page: {\"dialog\":{\"text\":\"UNTRUSTED PAGE TEXT\"}}"}
    ```

    Escaping text does not mark it as untrusted data.

    **Fix:** Store and expose Chrome page-derived stage details inside structured `untrusted_content`, keeping the ordinary summary service-authored. Add coverage for dialog text and held-step labels.

The service-unit change is correctly limited to adding `AF_INET`/`AF_INET6` and removing `IPAddressDeny`; the complete service-section pinning test passes. The journal fallback itself reads committed records without creating a side file, and Chrome uses the shared warning and paging modules. I found the expected operation commits before ordinary free and approved dispatches; the findings above concern disclosure, recovery, lifecycle and verification.

Independently run: **12 browser-free Python tests passed**, **72 Node VM tests passed**, and the retained receiver auditor passed all four combinations of runs `42773242428` and `42773249076` with external/policy installation. Runtime and workflow files have no differences between reported verified source `ab7aba92` and reviewed head `60b94384`. I did not rerun suites that create filesystem fixtures under this read-only review.

CHANGES-NEEDED