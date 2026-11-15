# 22c: review fixes, round 4 (the guides' recovery routes)

Review: `reviews/22c-ways-back-after-update/REVIEW-5.md` (gpt-6-astra high on `2312fa99`, CHANGES-NEEDED: one blocking, one should-fix). It confirms round 3's four fixes and the judgment call on `previous`. Two connected sequences remain:

1. **(Blocking) Going forward again must never stage while the tools' release is not installed.** After an unsuccessful update to a release whose tools are installed (say R28), the laptop has R27, R13 and stock. A later `previous` to R13 and then the forward-again box's `update` stages R28, and the shutdown removes R27, the system he meant to go forward to. A confirmation line does not prove the tools' release was installed. Integrator's decision: when the tools' release is not among the installed systems, the forward-again route is the two-step path the tools already support (choose the newer installed AresOS's row in the boot menu, then `update`, which only reorders there); the box says how to tell which case he is in from `check`'s or `title`'s lines, never from memory of earlier steps. Add the connected regression: stock return, `previous`, forward again.
2. **(Should-fix) Entering the failed-update card right after a check keeps that check's result.** The "not applied" message is printed once; a second check no longer shows it. The card says: if you came here from a check you just ran, use that result; otherwise run `check` now. Every result the card does not name leads to Help. Add the linked-entry sequence as a test.

No rule of the owner tools changes. Hosted checks-only must stay at 0 failures, 0 errors, 0 skipped with the full model green; a section "Review fixes 4" in the report.

**Model:** a Claude agent on Opus. Fix check: Codex if any is left, otherwise a Claude reviewer on Opus replaying both sequences.
