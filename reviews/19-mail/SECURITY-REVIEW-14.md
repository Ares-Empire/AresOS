# Security review 14 of brief 19 (Mail): round 21, under owner decision 24

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-08. Reviewed `99280cd0` (round diff `53a2d391..99280cd0` plus a sweep of the tools' own safety), against the fail-closed disk bar of round 21. Run by the lead; saved by the lead.

Reviewed `99280cd0`. Two blocking findings reproduced with production code and memory-only I/O substitutes:

1. **Blocking — disk-full short writes corrupt the journal.** [storage.py:406](/Users/pab/AresOS-19-mail/control/aresos_control/storage.py:406) ignores the byte count returned by the unbuffered journal write. Reproduction: let a commit-marker write accept only 13 bytes. Preparation returns `ok=true`, clears the failure latch, and leaves a journal that startup rejects as `evidence_corrupt`, even after space becomes available. Separately, shortening the event write and raising ENOSPC on the next write returns “Mail transport failed,” rather than a disk-full message. Check complete writes, safely recover interrupted tails, and classify storage errors explicitly.

2. **Blocking — actual ENOSPC still suppresses observed Sent duplicates.** [adapter.py:730](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:730) preserves the warning only for selected `Refused` exceptions. Reproduction: complete a send, expose two Sent copies with its Message-ID, then inject ENOSPC into the journal write that records the duplicate warning. `operation_status` returns `ok=true`, the recorded `done` operation, and a generic “Live evidence unavailable” error—with no copy list, duplicate warning or notice. The evidence read already found both copies. Return that observation even when persisting it fails, together with the disk-full error.

**Should-fix — the longer reply window misses changing requests.** [protocol.py:51](/Users/pab/AresOS-19-mail/control/aresos_control/protocol.py:51) extends only `method=call`. Save acknowledgements, uploads, downloads and account setup retain ten seconds. Holding a save acknowledgement at `sqlite_prepared` for eleven seconds reproduced `transport_error` at ten seconds followed by successful commit. Apply the intended timeout policy consistently; increasing a timeout alone cannot guarantee receipt.

Forty-three selected Python tests passed, using memory substitutes where needed; generated artifacts match. Focused probes passed for export admission, cancellation replay and the unchanged-history restore budget. Three identical approved submissions produced one receiver arrival. I found no additional approval bypass or replay path in the sweep. No files changed or containers ran; physical durability and native approval presentation were not exercised.

CHANGES-NEEDED