# Fresh integration review

Reviewer: gpt-6.1-sol, high; read-only sub-agent required by brief20. Reviewed the
integrate-2 working delta that became e264873e/5b3fd1a2. These notes retain the
reviewer's findings and verification; this is not the later package review.

**Read:** opener POP badges, epoch-bound individual Stop, immediate authority
revocation during pending cleanup and opener close/group departure are consistent
with integrate-2. No companion-window creation/focusing path remains.

**Finding repaired:** the close-opener fixture created its backup while the native
page popup still owned focus. Since open uses Chrome's current normal window,
select the opener before creating that backup, then select it again to close it.
The final driver does so. The finding was a source-level setup risk; no native
browser reproduction is claimed by this reviewer.

**Run:** `node --test control/chrome_tests/background.test.mjs control/chrome_tests/fixture.test.mjs control/chrome_tests/owner-ui.test.mjs`:
65 passed, 0 failed. This preceded the security review's additional manual-popup
admission regression; the builder's final complete144-case Node suite includes it.

**Not run:** native Chrome window/focus behavior; Linux-container CI must prove it.
No Mac browser, profile, real account or external mutation was accessed.

No outstanding findings in the reviewed delta. No full-package SAFE claim.

**Follow-up read/run:** native source95946 external completed61 cases,59 passed.
The two new driver failures compared focus before the owner's action-popup opening,
and read the replacement tab from the wrong response field. The revised stopPopup
helper snapshots after the owner opens the toolbar UI, retains exact window equality
and adds native focus identity equality. closeOpener validates the wrapped tab before
closing and updates both driver/matrix state.
`node --test control/chrome_tests/owner-ui.test.mjs`:7 passed,0 failed.
Targeted `git diff --check` passed. No findings; no browser/profile access.
