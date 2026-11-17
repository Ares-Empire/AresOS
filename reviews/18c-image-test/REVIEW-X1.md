Reviewed `91487807...6234b916`, read-only. Four **should-fix** findings remain.

1. **Should-fix — installed vendor bytes are not independently bound to the locked wheels.**  
   Where: [os/build.sh:246](/var/home/ares/AresOS-18c-image/os/build.sh:246), [os/ci/check-image.sh:113](/var/home/ares/AresOS-18c-image/os/ci/check-image.sh:113).

   The build hashes whatever is present under `/usr/lib/aresos-control`; the image checks verify that self-generated inventory. Separately, they validate pip’s reported wheel hashes against `requirements.lock`. Nothing verifies that the recorded vendor files actually come from those wheels. An extra or altered file present **before manifest generation** becomes accepted inventory, including executable Python bytecode.

   **Fix:** independently derive the expected vendor tree from the hash-verified wheels, with explicit rules for pip-generated files and bytecode. Compare paths, content and modes. Add a regression that changes a vendor file and its manifest hash while leaving the wheel list valid.

2. **Should-fix — password privacy can PASS despite incomplete scanning.**  
   Where: [os/ci/control/actions.py:1534](/var/home/ares/AresOS-18c-image/os/ci/control/actions.py:1534).

   File-read errors only increment `unreadable`; directory traversal errors are silently ignored by `os.walk`. The journal export’s exit status is also ignored. The final assertion checks discovered hits, without requiring successful coverage.

   **Reproduced in memory:** the actual `passwords()` function returned `returncode: 0` with one unreadable file and journal exit status 1. Thus `CONTROL_PASSWORDS_PRIVATE_PASS` can mean “could not inspect.”

   **Fix:** fail on traversal/read errors and unsuccessful journal export. Handle genuinely disappearing transient files through a narrow, recorded retry policy.

3. **Should-fix — archive scanning silently accepts unsearched content.**  
   Where: [os/ci/control/evidence_scan.py:49](/var/home/ares/AresOS-18c-image/os/ci/control/evidence_scan.py:49), [line 57](/var/home/ares/AresOS-18c-image/os/ci/control/evidence_scan.py:57).

   Reaching `DEPTH` returns normally even when the remaining bytes are compressed. Also, a tar whose checksum is invalid fails `is_tarfile()` and is treated as ordinary bytes, rather than unreadable evidence.

   **Reproduced in memory:** four nested gzip streams containing the synthetic password produced zero hits and no error. A damaged tar containing a compressed password did likewise. This contradicts the fix-round promise that unsearchable archives fail and are withheld.

   **Fix:** raise `Unreadable` when an archive exceeds the depth limit or recognizable archive content cannot be parsed. Add both regressions.

4. **Should-fix — check 9 can PASS without its required transcripts.**  
   Where: [os/ci/control/actions.py:1437](/var/home/ares/AresOS-18c-image/os/ci/control/actions.py:1437), [line 749](/var/home/ares/AresOS-18c-image/os/ci/control/actions.py:749).

   Transcript-copy exceptions become a `"not copied: …"` summary string without adding a check failure. Finding no transcripts returns an empty list. The packer then silently skips absent folders. Consequently `CONTROL_INTERACTIVE_ASK_PASS` can print without the transcript evidence required by B2.

   **Reproduced in memory:** packing an absent transcript folder returned empty files, empty sizes and no errors.

   **Fix:** require a nonempty transcript set for every completed case, add copy failures to `errors`, and fail when required evidence folders are missing.

The failed-service logout/autologin check now requires the old runtime directory to disappear, a new greetd session, and live desktop processes while the service remains failed. I found no stale-output shortcut there. The held-work checks substantiate the recorded `held_elsewhere` numbers: **2 requests, 0 extra, 0 Stop continuations**. The listener check has both `/proc` and `ss` observations with a positive control.

I found no additional prohibited-path change. Existing-folder ownership is preserved deliberately; UID/GID conflicts on an existing deployment remain the release rehearsal’s responsibility. Sessions that never use Control still receive managed settings and `CLAUDE.md`; the current wording permits delegated instructions, and the recorded unused-session cases remain quiet.

Verification: in-memory syntax compilation passed for 20 changed Python files; `bash -n` passed for six changed shell files; `git diff --check` passed. No files changed, prohibited commands or owner modules ran, or CI/VM runs were repeated. `.work/` contains no files over 500 MB.

**Where I differ from Claude’s review**

- **#1, #3, #4, #7, #9:** closed by the current code and supplied CI evidence. I agree with Claude’s original findings.
- **#2:** Claude caught the earlier overbroad managed instruction; PR #86 fixes that wording. Owner acknowledgement remains a separate pre-merge requirement.
- **#5:** partially closed. Ordinary evidence tars are scanned and only GreenMail is redacted, but finding 3 above leaves the fail-closed promise incomplete.
- **#6:** the requested wheel-list comparison is closed; the stronger installed-byte binding in finding 1 remains missing.
- **#8:** the progress record was corrected; assembling the final Part A/B2 report remains outstanding.
- Claude’s assertion that every failed expectation prevents PASS is too strong: findings 2 and 4 are additional silent-success paths it missed.

CHANGES-NEEDED