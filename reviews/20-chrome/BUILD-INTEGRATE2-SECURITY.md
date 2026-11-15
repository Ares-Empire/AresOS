# Fresh integration security review

Reviewer: gpt-6-astra, xhigh; read-only sub-agent required by brief20. Reviewed the
integrate-2 working delta that became e264873e/5b3fd1a2. These notes retain the
reviewer's findings and verification; this is not the later package security review.

**Finding repaired:** manual `take_tab` of a native popup could admit an unrelated
popup without parentTab/parentEpoch, put ON on its hidden action area, and leave it
controlled when its real opener closed. A browser-free VM reproduction confirmed
that orphan admission. The final admission path requires a currently controlled
native opener before attaching, validates its membership and binds its epoch. The
existing recursive release then revokes its children. The reviewer verified the fix.

**Finding repaired:** the fixture's close-opener backup creation now selects the
normal opener before creating the backup and again before closing the opener.
This is a source-level setup correction, not a claimed native browser observation.

**Read:** exact extension-popup sender checks, epoch-bound Stop, synchronous
revocation before cleanup, recursive opener revocation, serialized badge updates,
text-only rendering and no companion-window creation/focusing path were inspected.
No unresolved security finding remains in this delta.

**Run:** `node --test --test-name-pattern='manual popup taking' control/chrome_tests/background.test.mjs`:
1 passed, 0 failed,37.099ms. The builder separately ran all144 Node cases.

**Not run:** actual cross-world/window behavior; final container CI remains required.
No Mac browser or profile, real account or external mutation was accessed.
No full-package SAFE claim.

**Follow-up read/run:** the later stale-Stop UI correction reports changed control
instead of claiming that a refused stale request stopped the replacement epoch.
It refreshes the list and presents an enabled Stop for current control.
`node --test control/chrome_tests/popup.test.mjs`:3 passed,0 failed.
No findings; no browser/profile access.
