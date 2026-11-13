# 22: review fixes, round 5: tools self-update, recovery first

Follow-up on `pkg/22-update-route` (PR #32). Five review rounds (`reviews/22-update-route/REVIEW.md` to `REVIEW-5.md`) keep finding gaps in one step: the tools updating themselves. Read all five reviews and the REPORT's review-fix sections first, to see the history.

**Builder:** a fresh Claude agent on **Fable 5.2**. The owner's rule: Fable for hard problems that resist normal attempts.

**Goal:** make the two invariants of round 4 hold by construction, not by covering cases one at a time.
1. Always exactly one working toolset.
2. Broad legacy detection; false positives only refuse.

**Required structure:**
- **Recovery first.** Every entry into the tools (the bootstrap and every installed command) begins with trusted journal recovery, before **any** fallible check (`disk_record`, resume identity, staged-bundle validation, preflights). If the journal shows a pre-publication state, or no toolset is in place, restore the verified held copy, or finish publication if and only if it was already decided and verified. Only then run checks. A refusal at any later point before publication goes through one restore path.
- **One place decides.** Keep a single small function that, from the journal and the filesystem alone, says which toolset is current and what to restore. Every refusal and exception before publication ends there.
- **Unreadable means in use.** In detection, any `/proc` read error other than a confirmed process disappearance (ENOENT/ESRCH on the process itself) counts as "in use". That includes descriptor `readlink`, cwd and cmdline.

**Tests** (extend `test_owner_update.py`):
- For every interruption point, follow the cut with refusals from **every** fallible check, not only layout or transaction ones: `disk_record` failure, resume-identity mismatch, an invalid staged bundle, a preflight error and an unexpected exception. After each, `bash /var/lib/ares/at` runs a verified toolset.
- Descriptor, cwd and cmdline read failures (EACCES, EIO) count as in use and refuse.

If a simpler design reaches the same guarantees, choose it, and say why in the REPORT. Keep everything else in PR #32 as reviewed: the update/previous intent journal, the lock, history.json and the guide. Keep the fingerprint, the pins and `pending-rebind.json` exact. Rerun the focused owner suites and one full WSL suite, plain and `-B` (package-unique names, at least 4 GB free, one suite at a time). Add a "Review fixes 5" section to the REPORT, then push.
