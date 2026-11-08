# Security review 19 of brief 19 (Mail): round 26, under owner decision 24

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-08. Reviewed `ce73b0f3` (round diff `d8a7f21b..ce73b0f3`, control/ identical to `ec6cafcb`, plus a sweep of the tools' own safety), against the refined disk bar of round 25. Run by the lead; saved by the lead.

**Blocking — duplicate warnings can still disappear.** In [adapter.py:707](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:707), a failed duplicate-warning write survives only in the current response.

Reproduced in memory: start with a completed send, expose two matching Sent copies, then reject storage admission for `mail_sent_copy_check` during `operation_status`. The response reports “2 copies,” but no notice is stored or deferred. After space returns, both `control_pending` and `mail_filing_notices` are empty—even after restart. Recovery excludes the operation because it remains `done`. Only explicitly checking that particular operation again recreates the warning. A crash before delivering the original response therefore loses the owner warning entirely.

This breaks the **loss-of-owner-warning disk bar** and leaves inventory C incomplete. Preserve a recoverable warning source without requiring the caller to rediscover the affected operation.

**Should-fix:**

- **The sweep masks that loss.** [test_review23_sweep.py:431](/Users/pab/AresOS-19-mail/control/mail_tests/test_review23_sweep.py:431) calls `operation_status` before asserting warning survival, thereby recreating the missing notice. It then accepts any nonempty notice catalogue. Assert the affected operation’s warning before another live evidence read.
- **Successful submissions acquire misleading recovery notices.** Reproduced: prepare a send, restart while it is merely reserved, then submit successfully before expiry. The operation finishes `done`, but pending contains an “unfinished” recovery warning mentioning possible duplicates. [storage.py:540](/Users/pab/AresOS-19-mail/control/aresos_control/storage.py:540) uses the row’s creation timestamp to classify its later submitting state as startup recovery work. Capture which intents were actually unfinished at startup; this submission was never interrupted.

Five ingress tests passed; generated artifacts match. Memory-only probes verified exact oversized-error reconstruction across 334 bounded transport pages, index-admission recovery without restart, and recovery notices for unfinished filing/draft intents. No additional approval, replay, credential or free-action bypass was found in inspected paths. The filesystem fault sweep was not rerun. No files changed or containers ran.

CHANGES-NEEDED