# Security re-review 5 of brief 19 (Mail): rounds 11 and 12

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-07. Reviewed `410cb8e8..9061d892`. Run by the lead; saved by the lead.

Blocking findings:

1. **Questions can still hide real addresses.** [questions.py:89](/Users/pab/AresOS-19-mail/control/aresos_control/mail/questions.py:89) applies the generic 80-character shortening to unsubscribe recipients. Through the real preparation path, a long display name produced “by sending a mail to Mom x…?” with `stranger@example.org` entirely absent. A valid 117-character bare address also lost its domain suffix.

   Separately, [person()](/Users/pab/AresOS-19-mail/control/aresos_control/mail/questions.py:22) falls back to shortening the whole header when it contains multiple mailboxes. A deletion approval for a message with two From addresses showed only the first long display name, hiding both addresses. Parse each person separately, shorten only names, and preserve complete addresses—or refuse the approval.

2. **Reordered approvals are accepted.** [require_question()](/Users/pab/AresOS-19-mail/control/aresos_control/common.py:66) checks presence, while submission uses order-insensitive hashing and dictionary equality. Furthermore, outgoing serialization silently restores question-first order, concealing the caller’s reordering.

   I submitted `{description, operation_id, question}`: testapp sent and deleted successfully; Mail send, delete and folder-delete reached their execution methods in controlled probes. This violates the explicit requirement to refuse reordered asking inputs. Reject the wrong order before serialization normalizes it, and validate it at the service boundary.

Should-fix: No additional findings. The previous notice-escaping issue is closed. No attachment-route issue is treated as blocking.

The round-10 notice blocker is closed in the exercised cases. The 20-message and 4,000-message regressions delivered bounded warnings and location pages; every stored location record reconstructed correctly. Later log, pending and Mail reads remained within the response limits. Many outstanding notices, legacy notices, escaping and cursor binding also passed.

Otherwise, question text is service-generated, included in approval equality, escaped before size measurement, and refused when changed or missing. The tested counts, folder-delete wording and whole-approval size checks passed. Replay protection remained intact; repeating the successful testapp submission produced no additional delivery.

Reviewed `410cb8e8..9061d892` in the requested paths and REPORT sections. Twenty-one existing tests passed without filesystem writes; another 21 test methods passed with storage/blob I/O substituted in memory. Additional probes established the findings above. Syntax and generated-artifact checks passed. These runs do not qualify durable storage or real providers. No files were changed and no containers were run.

CHANGES-NEEDED