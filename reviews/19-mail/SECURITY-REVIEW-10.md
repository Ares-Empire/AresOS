# Security review 10 of brief 19 (Mail): round 17, under owner decision 24

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-08. Reviewed `eead1eb5` (round diff `9278b000..eead1eb5` plus a sweep of the tools' own safety) against decision 24: normal Claude Code plus tools that are safe in themselves. Run by the lead; saved by the lead.

Reviewed `eead1eb5` against the owner’s revised boundary. **One blocking recovery issue remains.**

**Blocking — repeated repairs can exhaust recovery capacity and deadlock restore.** In [engine.py:174](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:174), calling `mail_operation_repair` with `stage="sent_copy"` on an already completed send creates another operation and three journal transactions, although nothing needs repairing. These calls consume the recovery reserve.

Concrete reproduction: complete one send, keep another approval pending, then repeatedly repair the completed send’s Sent copy. Eventually cancellation returns `storage_limit`. Restore a SQLite backup taken immediately before the last repair: restore confirmation also returns `storage_limit`, while archive returns `restore_required`. Neither supported recovery command can proceed.

I reproduced this with real engine, SQLite and journal logic in memory, using a reduced quota. With the cap set to current history plus 1 MiB plus one byte, one redundant repair added 14,806 bytes; restoring the preceding backup reproduced both refusals. The journal remained valid—this is recovery lockout, not corruption.

Make completed repairs idempotent before allocating records, reject ineligible repairs before recording them, and preserve restore capacity that ordinary tool calls cannot consume.

**Should-fix:**

- **Archive eventually stops restoring usable capacity.** [storage.py:208](/Users/pab/AresOS-19-mail/control/aresos_control/storage.py:208) counts the permanently retained independent journal toward the same 1 GiB limit. Archive compacts SQLite but never reduces that journal. Once the journal alone approaches 832 MiB, ordinary work cannot resume through archiving. Provide a supported lifecycle for this record that preserves restore and replay guarantees, or explicitly handle its separate capacity.

- **The remote-cache check rejects private home directories.** [boundary.py:81](/Users/pab/AresOS-19-mail/control/aresos_control/boundary.py:81) traverses `/home/assistant/.claude` as the separate service user. A private home or `.claude` directory produces `boundary_not_installed` even when no cache exists; an in-memory permission-error probe confirmed this. Remove this dependency during the planned simplification; do not require exposing the owner’s private directory.

I found no additional prompt-path approval bypass, credential-return route, or destructive free action outside the accepted filing policy. Altered, reordered and duplicate approvals refused; replay caused no second delivery. One hundred identical preparations reused the same approval without history growth. The ordinary archive probe preserved open work, rejected archived approvals, and retained valid journal/restore checks.

**Verification:** 33 selected Python tests passed, with in-memory substitutes where needed; generated artifacts matched. Additional probes covered recovery, archive, expiry, cancellation and replay. Native Claude prompts, real providers and physical crash durability were not exercised. DKIM tests could not run because `cryptography` is unavailable. No files changed; no containers ran.

CHANGES-NEEDED
