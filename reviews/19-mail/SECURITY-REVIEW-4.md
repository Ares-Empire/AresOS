# Security re-review 4 of brief 19 (Mail): round 10

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-07. Reviewed `5c93fbe0..410cb8e8`. Run by the lead; saved by the lead.

Blocking: the new persistent notice can suppress its own delivery and break subsequent Mail results.

[Engine.notices()](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:33) repeats the entire location report without paging or a size bound. I reproduced a 20-message MOVE involving byte-identical messages with a long Message-ID: role drift after the first MOVE produced an 83,306-byte notice. Thereafter, `aresos log` and `control_pending` returned only `result_too_large`, without the warning—even with `limit=1` and an empty later-day audit page. Mail reads also returned size errors.

With 4,000 identical messages, the repeated observations produced a 7,902,785-byte response. The protocol’s 6 MiB limit rejected it, delivering zero bytes. The filing result and subsequent Mail responses therefore disappeared entirely. This defeats the required owner notice; smaller requested pages cannot fix it. Keep an always-deliverable warning and filing identifier, with exact locations available separately through bounded pages. Relevant paths: [location collection](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:20), [notice persistence](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:133), and [response-size handling](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:344).

Should-fix: structured notices bypass the existing display escaping.

The new notice reader returns stored `untrusted_content` directly. An encoded Message-ID containing a right-to-left override emerged as literal U+202E in `control_log.data.notices`; the normal audit entry escaped the same value. Apply the existing display escaping to returned notices while retaining exact internal references. The content remains labelled untrusted, and terminal JSON escapes it, but structured renderers receive active formatting controls. I did not test their presentation.

The previous destructive-undo findings are closed in the reviewed code. Through the actual Engine/Mail paths with in-memory IMAP substitutes, all three reproductions preserved the surviving messages, performed no recovery mutation, and returned exact destination references. Connection loss retained observations, marked the scan incomplete, and persisted `partial`. Stable MOVE/COPY returned `done`; COPY issued no expunge.

Additional probes refused direct Trash filing, Drafts extraction, forbidden flags, protected-folder changes and forged deletion approvals before mutation. I found no new destructive approval bypass. The report correctly documents the accepted transient-role timing window.

Reviewed exactly `5c93fbe0..410cb8e8` in the requested paths, plus the round-10 and owner report sections. All 22 unit tests runnable without file writes passed; generated artifacts matched. No files were edited, containers run, or real providers tested.

CHANGES-NEEDED