# Security review 18 of brief 19 (Mail): round 25, under owner decision 24

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-08. Reviewed `d8a7f21b` (round diff `de1098d7..d8a7f21b` plus a sweep of the tools' own safety), against the refined disk bar of round 25. Run by the lead; saved by the lead.

Blocking findings at `d8a7f21b`, reproduced with in-memory probes:

1. **Error responses can still exceed the transport limit.** [adapter.py:566](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:566) embeds every rejected reference in the error; [results.py:79](/Users/pab/AresOS-19-mail/control/aresos_control/results.py:79) only bounds responses containing observations. Reproduction: prepare deletion of ten messages with malformed From headers and Message-IDs ending in 100,000 tabs each. The schema-valid request is **2,001,685 bytes**; the escaped refusal, including one pending filing warning, is **9,001,604 bytes**. Production transport rejects the entire response. This breaks **(3), robust input handling**, and drops the owner warning. Bound error details while preserving the warning envelope.

2. **Startup admission still causes refusal after disk recovery.** [storage.py:208](/Users/pab/AresOS-19-mail/control/aresos_control/storage.py:208) saves an index-admission refusal; `require_index()` keeps rejecting without rechecking space. Reproduction: start an existing store with insufficient index-building space, then restore ample space. With `write_failed=False` and no incomplete transaction, repeated writes still return `storage_limit`; neither retries admission. This breaks the **refusal persisting on a healthy disk without restart** bar. Retry index admission/reconstruction when space returns.

3. **A filing warning disappears across restart.** [filing.py:273](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:273) retains failed warning writes only in `deferred_notices`. Reproduction: MOVE one message, change the destination’s role to Trash, then refuse all post-MOVE writes for insufficient space. Crash before delivering the response and restart with healthy storage. The committed intent remains `started`, but both `control_pending` and `mail_filing_notices` return empty lists; the message remains in Trash. This breaks **loss of an owner warning**, including crash/restart handling. Unfinished durable intents must produce recovery warnings.

Should-fix:

- **Implicit cleanup still replaces the first cause.** At [blobs.py:80](/Users/pab/AresOS-19-mail/control/aresos_control/blobs.py:80), ENOSPC during writing followed by EIO from the stream’s implicit close returns only “Storage I/O failed,” without a cleanup note. This is should-fix under the refined multiple-fault wording bar.
- **Sweep assertions remain incomplete.** Recovery always restarts and does not assert filing-warning survival. Cleanup pairs cover only helper-tagged operations. The send-completion assertion also accepted `done` with one DATA attempt and only an unrelated old message in Sent; it needs matching delivery/copy evidence.

Four ingress tests passed; generated artifacts match. Observation paging reconstructed 7,054,896 characters across 1,176 bounded, transport-checked pages with repeated warnings, unchanged journal sequence and foreign-cursor rejection. No additional approval, replay, credential or free-action bypass was found in inspected paths. No files changed or containers ran; the filesystem fault sweep was not rerun.

CHANGES-NEEDED