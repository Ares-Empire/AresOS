Reviewed PR #46 at `f3369b8d`, limited to `e051dd59..HEAD`.

1. **Blocking — check the actual update outcome before running `previous`.** [EMERGENCY.md:20](/var/home/ares/AresOS-22c-review/docs/EMERGENCY.md:20)  
   In the brief’s R28 update example, the provisional menu predicts `[R28,R27,stock]`. If finalization is lost, the actual list remains `[R27,R13,stock]`: choosing predicted row 1 boots R13, and the instructed `previous` accepts and makes R13 default—one release further back than intended. The “was not applied” protection at line 22 covers only an automatic return.  
   **Fix:** run `check` after the recovery-menu boot, before `previous`; apply the not-applied/STOP branches regardless of how Linux started, and verify the running release against the intended recovery destination.

2. **Blocking — the “no new release” return route can initiate an update.** [INSTALL.md:330](/var/home/ares/AresOS-22c-review/docs/INSTALL.md:330)  
   With this head’s R27 tools but only R13 and stock installed, returning from stock prints “The release of these tools is newer still … restart, then run … update again.” The guide says to follow it. That second command stages R27, despite this box promising an installed-system return without a new-release announcement.  
   **Fix:** finish after returning to the installed release. Route any subsequent staging through the announcement-gated new-release procedure; explicitly exclude it from “follow it.”

3. **Should-fix — a successful no-op return cannot produce the required confirmation.** [INSTALL.md:330](/var/home/ares/AresOS-22c-review/docs/INSTALL.md:330), [INSTALL-PROCEDURES.md:168](/var/home/ares/AresOS-22c-review/docs/INSTALL-PROCEDURES.md:168)  
   Boot stock manually from `[R27,R13,stock]` with no journal, then run `update`. R27 already starts next, so the tools write no journal. After restarting, `check` passes but cannot print “Update to … confirmed after the restart.” The guide nevertheless requires it, leaving a successful recovery without its documented completion.  
   **Fix:** distinguish an actual selection from a no-op. For the latter, require `PASS check` and the intended system running and starting next, without a change-confirmation line.

4. **Should-fix — changed tools can receive only the model slice.** [os-image.yml:145](/var/home/ares/AresOS-22c-review/.github/workflows/os-image.yml:145), [os-image.yml:605](/var/home/ares/AresOS-22c-review/.github/workflows/os-image.yml:605)  
   The full-model job runs only for `checks_only`. A direct 22c rehearsal runs the slice, and [rehearsal_guard.py:445](/var/home/ares/AresOS-22c-review/os/ci/rehearsal_guard.py:445) accepts its own native step without any passing checks-only run on that head. Thus the comment asserting prior full-model coverage is not enforced.  
   **Fix:** require same-head full-model qualification when dependencies changed, or run the conditional model job for those dispatches too. Test the direct-dispatch case.

Verified: all bundle hashes and fingerprint pins match; retained scripts are unchanged; all 34 waiting rows, both removals and 255 host-walk hashes match. Start-block structure, namespace prerequisites, budget change and existing permissions/triggers/secrets check out. Part F’s table, real injection and revert proof match the code. Status preserves the rehearsal/laptop limitations.

Seven selected read-only tests passed. Pure-ledger traces corroborated the guide cases; no owner tools, start blocks or prohibited tests ran. No files changed.

CHANGES-NEEDED