# Security review 20 of brief 19 (Mail): round 27, under owner decision 24

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-09. Reviewed `8724c0b6` (round diff `ce73b0f3..8724c0b6` plus a sweep of the tools' own safety), against the refined disk bar of round 25. Run by the lead; saved by the lead.

**Blocking — archiving can still erase an unrecorded duplicate warning.** [adapter.py:723](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:723) reopens a previously clean check only after reading the duplicate evidence. If admission refuses that write, the stored check remains clean. [archive.py:22](/Users/pab/AresOS-19-mail/control/aresos_control/archive.py:22) then considers the operation eligible for removal.

Reproduced with production logic and in-memory storage:

1. Start with a completed, clean send; expose two matching Sent copies.
2. Refuse storage admission during `operation_status`. Its response reports two copies, but no warning or open check commits.
3. Discard volatile state to simulate a crash, restore healthy admission, and run owner `control_archive` with a cutoff covering that operation before another live pending read.
4. Archiving removes the operation. Both `control_pending` and `mail_filing_notices` return empty while both copies remain.

This breaks the **loss-of-owner-warning disk bar**. Inventory C therefore remains incomplete. Ensure a failed reopening cannot leave the source eligible for archival; add this sequence to the regression tests.

**Should-fix — filing recovery suppresses available evidence.** [filing.py:161](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:161) requires the entire special-folder map to resolve before inspecting locations. Reproduced an interrupted MOVE where LIST identifies Target as Trash, but an unrelated Drafts role is missing: recovery skips the location scan and reports only “not yet checked.” Report the observable role drift and available locations, keeping only genuinely unavailable evidence unresolved.

The startup classification behaved correctly in probes. The approval-test fixture changes preserve the binding assertions, and the sweep now checks the affected operation’s own warning and count before status. Inspected recovery paths perform no remote mutations. I found no additional approval, replay, credential, or free-action bypass.

Five ingress tests passed; 44 in-memory altered-approval checks passed. Generated artifacts match, and all 135 Python files parse. Broader test imports failed because `jsonschema` and `cryptography` are missing; the filesystem fault sweep was not rerun. No files changed or containers ran.

CHANGES-NEEDED