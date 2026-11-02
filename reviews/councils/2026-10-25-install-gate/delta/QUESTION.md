# Install-gate council: delta check after packages 14 and 15

**What is reviewed:** commit `e077bdf` on branch `pkg/15-owner-path`. That branch contains package 14 (the owner tools, PR #13, pushed head `5156f5f`) plus package 15 (the owner path and emergency card, PR #14). Package 14's later local commits only harden a CI download step; they don't touch the owner tools or docs.

**Your earlier verdict:** [VERDICT.md](../VERDICT.md) at `6eb2d0b`: GAPS-FOUND (11), 7 blocking. The member files are in the folder above.

**Read:**
- `briefs/14-owner-tools.md` and its follow-ups `14b`–`14l`
- `briefs/15-owner-path.md` and `15b`
- `reviews/14-owner-tools/REPORT.md` and `reviews/15-owner-path/` (REPORT, REVIEW, REVIEW-2)
- `docs/INSTALL.md`, `INSTALL-REFERENCE.md`, `INSTALL-PROCEDURES.md`, `INSTALL-STATUS.md`, `INSTALL-RECORD.md`, `EMERGENCY.md`
- `docs/design/OS-BASE.md` §8 and Appendix C
- `os/owner-tools/` (commands.json, the payload) and `os/tests/test_owner_*.py`

**The question:** for each of your 11 findings, is it now CLOSED, PARTLY closed or still OPEN at this commit? Judge it against your own "Check" line, citing the files.

Did the fixes introduce any **new** problem that would mislead or endanger the owner on install day? A new finding needs a concrete scenario, as before.

**Known and accepted; don't re-raise as findings:**
- **Package 14's VM qualification is pending.** It ran up to the tools step (the offline install, hardware setup and Windows round trip passed with clean disk/NVRAM/BootNext audits), then stopped on a console prompt-timing bug that has since been fixed locally. It reruns on 1 November. Judge the code and docs; note anything the qualification must prove.
- **Physical and novice gates stay open by design:** the unaided phone trial, both FnLock states, the expendable-media trial, damaged-battery refusal, the token negative test, and live typing. Installation stays NOT RELEASED until they pass. A finding is only a gap if the docs or tools are wrong, not merely untested on hardware.
- **Owner decisions:**
  - two sticks only
  - offline until `prepare`
  - the tools stick only after Linux is up and out before every restart
  - the backup stock keeps German
  - `ares-recovery`
  - after a failed first switch: F12 → Windows → help
- **The privacy, CI-budget and release-binding fixes** (14d–14l) are CI matters, not owner-path matters.

**What depends on it:** whether, once package 14's qualification passes and both PRs merge, the guide can move to the owner's physical gates (the Windows preparation, fitting the SSD, then installing).

End with one line: **DELTA-CLEAN** or **GAPS-FOUND (n)**.
