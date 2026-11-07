Checked only `cf7f7e2..a9c0cbd` against the four follow-ups and their regressions. **One blocking gap remains.**

1. **Done — 15-minute approval expiry.** Defaults agree at 900 seconds. Independent controlled-clock checks produced `done` at 899.999 seconds and `failed`, zero arrivals, and one `drop` at 900.001 seconds. The checks after adapter validation remain intact.

2. **Done — configurable 25 MiB chunked transfers.** [Transfer framing](/Users/pab/AresOS-18-control-base/control/aresos_control/protocol.py:54) checks offsets, chunk sizes, total size, and hashes. [Blob publication](/Users/pab/AresOS-18-control-base/control/aresos_control/blobs.py:24) happens only after complete verification; failed streams remove staging files. Tests cover source replacement, exact receiver/saved bytes, limits on both sides, and seven malformed streams. Saved final-head CI output records 114 frames, largest 1,398,154 bytes, below the 6 MiB limit.

3. **Not done — blocking: a crash followed by restore can silently erase an operation.** [storage.py:158](/Users/pab/AresOS-18-control-base/control/aresos_control/storage.py:158) commits the full event to SQLite **before** appending its independent record.

   I reproduced the durable state at `sqlite_prepared`, then restored the preceding SQLite backup before restarting. The prepared reservation disappeared completely: `restore_required = False`, no stored operation, and no independent entry. The service therefore cannot require confirmation or list it as `unknown`.

   The [crash helper](/Users/pab/AresOS-18-control-base/control/tests/test_crashes.py:20) immediately restarts the engine, which copies the prepared event into the record and masks this window.

   **Fix:** durably fence the operation in the separate record before the first SQLite commit. If recovery lacks its full event, require `restore_confirm` and preserve its short description as `unknown`. Test backup restoration **before the first restart** at every new write boundary.

   Otherwise, compact-record privacy, ordinary restore detection, missing send/delete descriptions, generation invalidation, and SQLite-backed logging check out. Independent ordinary-restore checks passed.

4. **Done — quiet prompt hook.** Event arguments and mismatch rejection are explicit. Independent checks confirmed quiet prompt failures, valid pending reminders, and preserved Stop behavior. The [shell guard](/Users/pab/AresOS-18-control-base/control/settings/managed-hooks.json:20) clears the environment before `/bin/sh`; Python uses `-I -S`, and the launcher validates protected code/configuration paths before loading application modules.

Generated-artifact checking passed. Both final-head CI jobs succeeded ([push](https://github.com/Ares-Empire/AresOS/actions/runs/42349346028), [PR](https://github.com/Ares-Empire/AresOS/actions/runs/42349349823)); saved logs show 51 tests passing twice. My reproductions used in-memory SQLite and mocked filesystem durability calls; I did not rerun the Linux suite. No files changed.

CHANGES-NEEDED