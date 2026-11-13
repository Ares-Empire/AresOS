# Security review 11 of brief 19 (Mail): round 18, under owner decision 24

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-08. Reviewed `88c83ef7` (round diff `eead1eb5..88c83ef7` plus a sweep of the tools' own safety). Run by the lead; saved by the lead.

**Blocking — uncertain repairs can still exhaust cancellation capacity.** In [engine.py:184](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:184), every eligible repair allocates another operation. If IMAP disconnects, that repair becomes `unknown`, while the original stage remains `failed` and eligible for another attempt. Archive permanently protects these unresolved records.

Concrete reproduction:
1. Complete SMTP delivery with a failed Sent-copy stage; leave another send approval pending.
2. Repeatedly repair the Sent copy while IMAP returns an uncertain outcome.
3. When admission refuses, archive finished history and repeat.

With real engine, SQLite and journal logic in memory, and the history cap reduced to current SQLite size plus 1 MiB plus 256 KiB, **38 attempts accumulated 38 unknown repairs**. Repeated owner archives could not reclaim them; cancellation still returned `storage_limit`. Restore confirmation refused because no restored log was pending.

Completed-stage idempotence and the new restore exemption work, but this alternative recovery lockout remains. Reuse or bound unresolved repair attempts, provide a safe resolution path, and protect cancellation capacity from repair traffic.

**Should-fix — permanent journal retention also means permanent RAM growth.** [storage.py:105](/Users/pab/AresOS-19-mail/control/aresos_control/storage.py:105) loads every historical record into `self.events`; archive never releases them. Small Mail compose/prepare/send sequences measured approximately **8–12 KB on disk and 32–45 KB of parsed journal objects**. At 100 sends/day, that projects to 0.30–0.44 GB of journal and 1.2–1.7 GB of journal objects per year, excluding other storage. Keeping the disk record indefinitely is reasonable under the owner’s space policy; keeping it all in RAM is not a sound long-term lifecycle. Stream verification and maintain a bounded index.

Separate accounting otherwise preserved archive capacity, restore detection and replay protection in my probes. The remote-cache/login removals introduce no identified regression. I found no additional approval bypass, credential-return route, destructive free action outside the accepted filing policy, or regression against decision 24. Ask coverage, bound questions, replay refusal, untrusted-content marking and malformed-input handling held.

**Verification:** 58 selected Python test methods passed with in-memory substitutes where needed, plus targeted probes; generated artifacts matched and 105 Python files parsed. Native prompts, real providers and physical crash durability were not exercised; DKIM tests lacked `cryptography`. No files changed; no containers ran. Reviewed HEAD `88c83ef7`.

CHANGES-NEEDED
