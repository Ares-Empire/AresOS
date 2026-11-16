# Package review 1: step 1 (`a350cc8b..801dad9a`, Claude Opus, 2026-11-15)

**Verdict: FIX.** The code fix is right on the normal paths. Two things need changing: the "no IMAP" test proves nothing, and one error branch still shows stale Mail notices and names a route the lock refuses.

## FIX 1: the "no IMAP" test can't fail for the reason it states
`control/chrome_tests/test_restore_lock.py:164-171`, `test_locked_reads_open_no_mail_server_session`.
- **Why it can't fail:** the unlocked `control_pending` at :164 runs the Sent-copy check and records it as `checked`. Only then does `lock()` (:166) take the backup. Under the lock, a Sent-copy check that runs again stops at `register_sent_check`'s write, which the lock refuses, before `sent_matches` opens IMAP.
- **Shown:** with probe `restorelock-sent-check-runs` applied, `self.sessions` stays `[]`. The probe is rejected only by `assertTrue(result['ok'])` at :170, because the refused write makes the reply `ok:false`.
- **The realistic crash case:** the older database still has the check `open`. In a scratch variant set up that way, HEAD's `engine.py` and the probe both open IMAP (`['imap'] != []`). The fix opens none, and the variant passes on it.
- **Smallest fix:** drop :164-165, so the backup holds the open check. The after-confirm `assertIn('imap', …)` already proves the fake transport is wired. Then assert `self.sessions == []` before `result['ok']`, so the probe is rejected by the session counter.

## FIX 2: `Engine.pending`'s storage-failure branch ignores the lock
`control/aresos_control/engine.py:142-189`. This code is older than the diff, but the brief's rule covers it, and PROGRESS doesn't analyse it.
- **The trigger:** a storage error (for example EIO) inside `_pending` while the lock holds. Lines 159-165 then add `store.deferred_notices`. At a locked start these hold Mail recovery notices built from the pre-restore database by `recover_intents(persist=False)`; flushing them is refused while locked.
- **Reproduced (one EIO on `chrome.notice_page`):**
  - With a stale `submitting` Mail send, `control_pending` lists `recovery-…:stale-send` (app `mail`) beside Chrome's rows.
  - With 3 stale sends, a `background-storage` notice and no Chrome warnings, line 187 returns `notices_more: {count: 1, action: 'mail_filing_notices'}`. Calling that route is refused with `restore_required`.
- **Severity:** low. It needs an I/O error during the lock, and the notices are cautious "unfinished, inspect" warnings labelled as a storage snapshot. But if the oracle injects read faults in its crash-locked cases, leftover C3/C4 keys could stop R2's classification.
- **Smallest fix:** when `self.store.locked`, skip the deferred-notice loop and set `other_total = 0`. Tried in scratch as `if self.store.locked: other_total, notices = 0, {}` with the loop over `() if self.store.locked else self.store.deferred_notices.values()`. The Mail notices disappear, the route can only be `chrome_notices` or `control_notices`, and the 4 tests still pass. Add one test with an injected EIO.
- You can downgrade this to a NOTE if you accept the double-fault risk.

## NOTEs
- **Probes:** four are rejected for their stated reason (Mail in the app set, or the missing "until the owner confirms the restore"). `restorelock-mail-route-continued` reuses the `stale-warnings-listed` change and is rejected by `ok` (:130) and `total 6 != 0` (:136), never by the route check. That is acceptable, because the route can only go wrong by listing Mail warnings again.
- **PROGRESS is wrong about the cursor.** A cursor taken under the lock does not give `stale_reference` after confirmation. It gives `ok:true` with `page_changed: "Page changed; restarted from the first page."` and the first page. That behaviour is fine and matches "changed sets restart explicitly"; only the text needs correcting.
- **`owner_state_unavailable` branch (`engine.py:135`):** it overwrites `LOCKED_PENDING` with Chrome's error. `restore_required: true` stays and no route is named. Fine.
- **`results.bound_result`:** an oversize reply points to `control_observations` and names `mail_filing_notices`, both refused under the lock. This is older generic code and in practice unreachable under the lock, so outside R1.
- **Judgment calls, all fine:**
  - Tool descriptions: the MCP instructions don't include them (control instructions still 1,652 characters), `generate.py --check` passes, and the oracle doesn't capture them.
  - `ok:true` for `control_pending` with an open Sent-copy check is better than before. R2's C2 change must allow `allowed`.
  - The cursor change is covered above.
- **Unchanged as required:** Chrome's `reconcile_open_checks()` still runs before the lock branch and can return `ok:false`/`restore_required` (class C2), as before. Chrome's rows and notices under the lock are the same set and order; only the cursor scope differs. Code outside the lock and `control_restore_confirm` are unchanged.

## Checked
- The diff `a350cc8b..801dad9a` and every lock path:
  - in `engine.py`: `notice_page`, the `notices` route, `_pending`, all three branches of `pending`, `dispatch` for `control_notices` including its storage branch, the reply envelopes in `request`, `_admitted_request` and `_request`;
  - elsewhere: `daemon.error_result` and `chrome_notices`.
- The lock is set only when the store opens and cleared at confirm. I traced where `deferred_notices` come from.
- All IMAP and SMTP goes through `transport.imap`/`transport.smtp`, so the fake's counter covers every connection.
- `test_restore_lock`: 4/4 pass on the fix. With HEAD's `engine.py`, all 4 fail on assertions (8 failures).
- The 6 probes ran through the audit's own harness: all rejected, and I read each failure.
- `test_committed`, `test_engine`, `test_state_fixes` and `test_questions` pass. `test_fault_surface` was too slow on this Mac (3 of about 12 flows in 9 minutes), so I stopped it and rely on the builder's preflight record and the PR's CI. `control/tests` was not run (needs `jsonschema` and Linux).
- `generate.py --check` passes. Paths are repo-relative, the only data is synthetic (`example.invalid`), and the diff stays within R1.

Probe scripts are in the reviewer's scratch directory (not committed).

While checking processes I found two sets that aren't mine; I left both alone:
- multiprocessing workers orphaned about a day ago from an old worktree (pids 26103-26105);
- a running `python-shard.py` in the build worktree (pid 47791).
