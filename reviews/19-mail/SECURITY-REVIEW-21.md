# Security review 21 of brief 19 (Mail): round 28, under owner decision 24

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-09. Reviewed `0ba7870e` (round diff `8724c0b6..0ba7870e` plus a sweep of the tools' own safety), against the refined disk bar of round 25. Run by the lead; saved by the lead.

Two blocking findings at `0ba7870e`, reproduced with production logic and in-memory storage.

1. **Acknowledgement followed by expiry loses an unfinished filing check.** After RENAME succeeds and its result write is refused, simulate restart with IMAP unavailable. Acknowledge the recovery warning: the source becomes `partial, check_open=True`. Pending now shows nothing because [recovery.py](/Users/pab/AresOS-19-mail/control/aresos_control/recovery.py:31) recognizes only `started`. After 24 hours, [retention.py](/Users/pab/AresOS-19-mail/control/aresos_control/retention.py:96) deletes the source because its warning was acknowledged, ignoring `check_open`.

   In the reproduction, Target had become Trash. After expiry and restored connectivity, pending remained empty and recovery performed zero evidence reads. The specific drift warning could never emerge. This breaks the **loss-of-owner-warning bar**. An open check must remain discoverable and exempt from expiry independently of acknowledgement.

2. **Incomplete filing checks make older warnings unreachable through pagination.** Create four interrupted RENAME checks with Drafts unresolved; put the Trash drift on the oldest. `mail_filing_notices` returns three warnings and a cursor. Following that cursor returns `items=[]`, `total=4`, `cursor=null`.

   [filing.py](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:202) replaces every incomplete notice’s timestamp on each recheck, moving every entry ahead of the cursor. The cursor fingerprint includes IDs but excludes timestamps, so it silently accepts the invalid page. Acknowledging the visible three does not help: rechecking resets their acknowledgements, and the same three return. This breaks **owner-warning preservation** despite healthy storage. Preserve stable ordering and acknowledgements for unchanged results, with pagination that cannot silently omit warnings.

**Should-fix:** No separate findings. Add both sequences to regression coverage; the existing archive tests and fault sweep miss them.

The original Sent/archive reproduction passed: refused reopening skipped evidence, archive retained a late duplicate warning, and a healthy clean send archived. MOVE/COPY recovery correctly reported observable Trash drift and locations with only Drafts unresolved. Archive’s inspected rechecks perform no remote mutations. I found no additional approval, replay, credential or free-action bypass.

Five ingress tests and 44 altered-approval probes passed; generated artifacts match and all 137 Python files parse. The filesystem fault sweep and broader suites were not rerun under the read-only environment and missing dependencies. No files changed or containers ran.

CHANGES-NEEDED