# Security re-review 6 of brief 19 (Mail): round 13

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-07. Reviewed `9061d892..3058c256`. Run by the lead; saved by the lead.

Blocking finding: Duplicate JSON keys still bypass the approval check. [protocol.py:22](/Users/pab/AresOS-19-mail/control/aresos_control/protocol.py:22) and [cli.py:58](/Users/pab/AresOS-19-mail/control/aresos_control/cli.py:58) use ordinary JSON decoding before `require_question()`. An input containing question “Do nothing?”, operation_id, description, then a second question containing the genuine service question is accepted. Python keeps the first key’s position but the last value, concealing both the extra field and the changed question.

I reproduced testapp sends and deletes through socket decoding and the CLI, including a duplicate spelled `\u0071uestion`. Mail send, delete and folder-delete also reached their execution methods in controlled probes. Finding (b) therefore remains open.

Reject duplicate decoded keys before constructing dictionaries at socket, CLI and MCP ingress, including duplicates inside descriptions or request envelopes. Add raw-JSON regressions proving refusal before submission, staging, evidence checks or execution. Dictionary-permutation tests cannot detect this problem.

Should-fix: The control-character refusal creates a limited cleanup obstacle. In [adapter.py:529](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:529), one attacker-controlled From display name containing a control character prevents both Trash and permanent-delete preparation for the entire selected batch. I reproduced this; healthy messages prepared successfully when selected separately. Identify the offending message reference in the refusal and explain how to exclude it and delete it through the owner’s mail program. This does not lock the account or justify weakening address validation.

The address-shortening finding appears closed within the explicitly approved first-three-and-count summary behavior. Named mailboxes retain complete addresses; malformed headers and oversized questions refuse before operation reservation. Send To/Cc/Bcc, multi-mailbox delete senders, unsubscribe, reply/forward and whole folder names were covered by inspection and the exercised tests.

Ordinary reordered, extra and missing fields were refused. Whitespace and Unicode escapes did not bypass those checks without duplicate keys. Approval equality and replay protection remained intact for decoded inputs; correct submissions executed once. I found no other regression in the requested diff.

Reviewed `9061d892..3058c256` and REPORT’s round-13 section. Twenty existing approval tests passed with filesystem storage substituted in memory; additional raw-input probes established the findings above. Syntax and generated-artifact checks passed. These checks do not establish durable-storage, real MCP or provider integration behavior. No files were edited, no containers ran, and no attachment-route issue is blocking.

CHANGES-NEEDED
