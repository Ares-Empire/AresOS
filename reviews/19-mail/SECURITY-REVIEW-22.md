# Security review 22 of brief 19 (Mail): round 29, under owner decision 24

Reviewer: Codex `gpt-6-astra`, xhigh, read-only, fresh context, 2026-11-09. Reviewed `4fc165eb` (round diff `0ba7870e..4fc165eb` plus a sweep of the tools' own safety), against the refined disk bar of round 25 and round 29's recorded restore limit. Run by the lead; saved by the lead.

Three blocking findings remain, reproduced with in-memory probes:

1. **Live RENAME can lose its Trash warning on healthy storage.** After RENAME succeeds, return a folder listing where Target is Trash and Drafts is unresolved. [rename_folder](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:74) discards the observed Trash role when role resolution fails, records “an unverified role,” and leaves the source partial without an open check. Acknowledge that warning, restore Drafts, then advance 24 hours. Recovery performs zero evidence reads and expiry removes the source. The specific Trash warning never appears. **Breaks owner-warning preservation and incomplete-check retention.**

2. **A refused recovery-result write discards newly observed warning evidence.** Start an interrupted RENAME with Drafts unresolved; acknowledge its ordinary-folder warning. Change Target to Trash and refuse the next filing-check write with storage_limit. [resolve_checks](/Users/pab/AresOS-19-mail/control/aresos_control/mail/filing.py:216) catches the refusal without preserving the observed evidence in deferred notices or response observations. Restore space and make Target ordinary before rechecking: the check completes, with no retained Trash occurrence. Keeping the check open cannot recover evidence that has changed. **Breaks the disk bar’s prohibition on losing an owner warning.**

3. **A transient journal failure permanently refuses healthy writes until restart.** Inject ENOSPC before the journal writes any bytes, allowing truncation and cleanup to succeed. Remove the fault and retry a harmless local write. [ensure_writable](/Users/pab/AresOS-19-mail/control/aresos_control/storage.py:656) repeatedly returns the saved storage error without attempting another write. **Breaks the explicit healthy-disk recovery requirement without restart.** The raw-write sweep restarts before checking recovery; its separate live-recovery tests cover admission refusals, missing this case.

Should-fix: paging descriptions still direct callers to handle stale_reference, although changed catalogues now return page_changed with a restarted first page. Document that behavior.

The two original review-21 sequences passed in-memory replays. Additional probes passed for occurrence identity, acknowledgements, paging, archive selection, and 40 altered-approval refusals. Five ingress tests passed; generated artifacts match; all 141 Python files parse. The changed test assertions preserve the earlier checks while adopting explicit page restarts.

Full filesystem suites and the fault sweep were not rerun under the read-only environment and missing dependencies. No files changed or containers ran. The accepted free-change backup limitation is not a blocker here.

CHANGES-NEEDED