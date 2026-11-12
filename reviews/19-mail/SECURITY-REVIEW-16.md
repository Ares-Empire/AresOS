# Security review 16 of brief 19 (Mail): round 23, under owner decision 24

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-08. Reviewed `dd8ea4f6` (round diff `2be76104..dd8ea4f6` plus a sweep of the tools' own safety), against the fail-closed disk bar of round 21. Run by the lead; saved by the lead.

Reviewed `dd8ea4f6`. Three blocking findings remain, reproduced with in-memory probes:

1. **Free filing still loses observed results on disk full.** In [filing.py:286](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:286), let MOVE succeed, have the destination acquire the Trash role, then inject ENOSPC into the post-MOVE journal write. The service observes the exact COPYUID destination and changed role, but returns only `storage_limit`, with empty pending items and no observations or warning. The retained intent still has `destination: null`; no notice survives. A free action has moved mail into Trash without the promised disclosure. Preserve filing observations and warnings through the shared result layer before attempting persistence.

2. **Background expiry hides the first disk-full error.** Inject journal ENOSPC while `Engine.expire()` expires a reservation. [daemon.py:42](/Users/pab/AresOS-19-mail/control/aresos_control/daemon.py:42) swallows the exception; [engine.py:493](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:493) clears its stored diagnosis on the next request. Subsequent changes return only `journal_incomplete`: “A journal transaction did not finish.” The owner never receives the disk-full explanation. Retain the original storage cause with the failure latch. This finding concerns the required diagnosis, not cancellation availability.

3. **An export failure after publication also hides disk full.** In [files.py:159](/Users/pab/AresOS-19-mail/control/aresos_control/files.py:159), let an attachment save publish its destination, then inject ENOSPC into the directory fsync. With successful rollback, the response becomes `file_refused`, explaining that the exported inode was emptied but omitting disk full entirely. Preserve the original storage error alongside the rollback outcome.

**Should-fix — the sweep’s coverage and recovery assertions are overstated.** [test_review23_sweep.py:31](/Users/pab/AresOS-19-mail/control/mail_tests/test_review23_sweep.py:31) misses the index connection, SQLite statement/internal writes, file creation/link/rename/truncation failures, and flows including exports, password storage, filing, and background maintenance. Restart runs without injected failures. Recovery compares status with the same recovered database rather than independently expected outcomes; it skips replay when recovery returns `reserved`, so an unsafe regression back to reserved could escape detection. Assert expected actions and states independently, including that any attempted remote action remains nonrepeatable.

The live-send duplicate fix retained both copies, the warning, and the storage error in my probe. Five plain-Python ingress tests passed; generated artifacts match. I found no additional approval-binding, credential-disclosure, or replay bypass in the inspected paths.

No files changed or containers ran. The full sweep was not rerun; its filesystem-writing fixtures and required dependencies were unavailable here.

CHANGES-NEEDED