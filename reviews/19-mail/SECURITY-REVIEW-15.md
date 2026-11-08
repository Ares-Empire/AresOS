# Security review 15 of brief 19 (Mail): round 22, under owner decision 24

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-08. Reviewed `2be76104` (round diff `99280cd0..2be76104` plus a sweep of the tools' own safety), against the fail-closed disk bar of round 21. Run by the lead; saved by the lead.

Reviewed `2be76104`. Two blocking gaps remain:

1. **Blocking — live Sent repair still loses observed duplicates on disk full.** In [adapter.py:866](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:866), reproduce by repairing a failed Sent copy, allowing the APPEND plus a delayed earlier copy to produce two matches, then injecting ENOSPC into the journal write for `mail_sent_copy_check`. The response contains only `journal_incomplete`: no observed copies, duplicate warning, or persistent notice. Both copies remain. Reproduced during sending too. Round 22 protects status and settlement, but this execution path still discards the observation. Return it with the storage error even when persistence fails.

2. **Blocking — execution errors still hide the disk-full diagnosis.** In [engine.py:183](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:183), approve a send, let `submitting` commit, then inject journal ENOSPC while recording its first stage. The original disk-full error is swallowed; the attempted outcome write hits the failure latch and returns “A journal transaction did not finish.” Submission remains nonrepeatable, but this violates the explicit plain-disk-full requirement. Preserve the original storage error through execution and outcome handling.

**Should-fix — new responses violate the declared output schema.** [mail/definitions.py:104](/Users/pab/AresOS-19-mail/control/aresos_control/mail/definitions.py:104) permits only `operation` and `original`, while repaired responses now include `evidence`. Validating a reproduced response against its advertised schema fails with “unknown fields are refused.” Update the schema and validate these responses in regression tests.

Sixty selected Python tests passed with in-memory storage and Mail substitutes; generated artifacts match. Journal recovery probes preserved complete records. Lost-reply retries and older-backup recovery retained one delivery and refused resubmission. I found no additional approval bypass, credential exposure, or free-send/delete path in the sweep.

No files changed or containers ran. Physical durability and native approval/MCP presentation were not exercised.

CHANGES-NEEDED