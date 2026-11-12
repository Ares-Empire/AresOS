Reviewed head `80d3d6fe` against `main`. Two findings:

1. **Blocking — fitting trials disappear from gate closure.** [INSTALL-STATUS.md:38](C:/Users/pab/AresOS-status-b/docs/INSTALL-STATUS.md:38)  
   The old row required an expendable fitting trial detecting incorrect seating/support **before tightening**, and a damaged-battery photograph causing refusal **before connector work/reconnection**. The new row marks the gate PASSED and moves those requirements into “Any later removal or refit.” The supplied healthy-battery and correctly seated SSD evidence does not demonstrate either negative trial. This silently defers existing requirements, contrary to brief 16.  
   **Fix:** retain these checks as explicitly OPEN until their results are maintainer-checked; distinguish completed fitting from outstanding trial qualification. Add assertions preserving those closure requirements.

2. **Blocking — owner-reported firmware detection does not satisfy the existing screen-check requirement.** [INSTALL-STATUS.md:22](C:/Users/pab/AresOS-status-b/docs/INSTALL-STATUS.md:22), [INSTALL-STATUS.md:38](C:/Users/pab/AresOS-status-b/docs/INSTALL-STATUS.md:38)  
   Stage B honestly identifies firmware detection as owner-reported, but the Fitting row nevertheless says the maintainer “checked … the firmware screen.” The old row and brief 16 require that screen to be checked. Windows inventory corroborates both drives’ detection in Windows; it does not establish maintainer inspection of firmware.  
   **Fix:** obtain maintainer inspection of the firmware screen, recording that privately, or explicitly approve and document a changed evidence requirement. Until resolved, avoid declaring all Stage B evidence checked and Stage C released.

Otherwise, Stage A’s recorded check, the native probe’s 38 passing checks and cleanup, and the table update support the other Stage C prerequisites. INSTALL.md’s intro and step 4 agree with the table; EMERGENCY.md delegates release authority consistently. No private identifiers, photos or real names were added.

The test changes retain existing assertions apart from the intended release-state updates and add step 4 consistency checking, but their phrase checks do not catch the evidence gaps above. `git diff --check` passed. Targeted tests could not start: `py` reported “No installed Python found!” Linux-only test absence is not a finding.

CHANGES-NEEDED