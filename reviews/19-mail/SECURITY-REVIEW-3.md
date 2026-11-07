# Security re-review 3 of brief 19 (Mail): round 9 and the merge with main

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-07. Reviewed `5b0a0fb7..adcc8620` (round 9) and the merge `adcc8620..5c93fbe0`. Run by the lead; saved by the lead.

Reviewed `5c93fbe0`. The merge preserved round-9 Mail code, tests, generated artifacts and server-list changes. **Blocking problems remain.**

1. **Earlier role-race finding: partly closed. Undo can itself move mail into Trash or the wrong folder.**  
   After an ordinary MOVE succeeds, reassign Trash to the now-empty original source. The post-check detects drift, but rollback blindly moves the message into that newly designated Trash and reports `refused` with “messages were returned.” I reproduced this with **zero approval operations**. [filing.py:101](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:101)

   Source identity also remains vulnerable: replace the source folder after its UIDVALIDITY check but before undo. The service moves the message into the replacement, then detects the mismatch and returns `partial`. Detection happens after the wrong move. [filing.py:94](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:94), [filing.py:104](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:104)

   The post-check can also finish `done` when Trash changes to the target immediately before MOVE and changes back before LIST. I reproduced that too: equal snapshots do not establish unchanged roles during the action. [filing.py:71](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:71)

   Safe recovery needs an enforceable destination identity/role guarantee. Where unavailable, preserve the message and report incomplete recovery instead of issuing an unsafe undo; additional snapshot checks alone cannot close these windows.

2. **New blocking finding: COPY rollback can permanently delete the last surviving copy without approval.**  
   Rollback marks and expunges the created copy **before checking whether the original still exists**. I reproduced: COPY succeeds; another client removes the original; role drift triggers rollback; the service expunges the remaining copy, then discovers the missing original and reports `partial` with no observed locations. [filing.py:111](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:111), [filing.py:115](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:115)

   Exact COPYUID targeting preserved unrelated Deleted messages, but did not prevent this loss. Do not destructively undo without a guarantee that the original remains preserved; otherwise retain the copy and require owner-approved cleanup. Merely moving the source check earlier leaves another race.

The other earlier findings are:

- **Per-root hierarchy separators — closed.** Resolution records each root’s separator; ancestry checks use it; owner refresh preserves or reconstructs remembered roots individually. [roles.py:67](/Users/pab/AresOS-19-mail/control/aresos_control/mail/roles.py:67), [adapter.py:132](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:132), [adapter.py:935](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:935)
- **Shared draft-blob downloader bypass — closed for the reported route.** Both download authorization and streaming require export origin. Mail reimport requires caller-import origin plus recorded metadata. Missing origin grants no permission. [engine.py:266](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:266), [engine.py:321](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:321), [adapter.py:422](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:422). `testapp` is absent from the shipped [server list:3](/Users/pab/AresOS-19-mail/control/settings/managed-mcp.json:3); its fixture-only export requires an imported file.
- **Historical operation status after role drift — closed.** Recorded approval and stages remain available alongside `evidence_error`. [engine.py:205](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:205)
- **Subject whitespace — closed.** Composition normalizes surrounding spaces/tabs before freezing approval; display names receive corresponding normalization. Actual composition/decoded-wire checks passed. [adapter.py:404](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:404), [codec.py:56](/Users/pab/AresOS-19-mail/control/aresos_control/mail/codec.py:56)
- The older header and audit findings remain **closed**. The empty-folder replacement race remains **open as the documented owner judgment call**, unchanged by round 9. [guard.py:214](/Users/pab/AresOS-19-mail/control/aresos_control/mail/guard.py:214), [engine.py:191](/Users/pab/AresOS-19-mail/control/aresos_control/engine.py:191), [adapter.py:838](/Users/pab/AresOS-19-mail/control/aresos_control/mail/adapter.py:838)

**Should-fix — connection loss during location reporting loses the final filing result.**  
`locations()` catches IMAP errors but not `Uncertain`, which the production transport raises on connection loss. That exception escapes before the final outcome is persisted, leaving the intent `started` and withholding the promised partial result and locations. Catch it, preserve collected observations with `scan_complete=false`, and persist the outcome. [filing.py:36](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:36), [filing.py:122](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:122)

Verification: **19 existing plain-Python tests passed**; `python3 control/generate.py --check` printed `Generated artifacts match definitions`. Additional checks used actual implementation paths with in-memory storage and protocol substitutes. No files changed, containers ran, or real providers were tested. No attachment-route finding is being promoted to blocking contrary to the owner’s stopping rule.

CHANGES-NEEDED