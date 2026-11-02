Reviewed `f13ac8e..ae90dd3`, limited to the five findings and affected code/tests. No files changed.

1. **CLOSED — USB execution before verification.** The bootstrap copies into a private directory, checks the literal manifest fingerprint, rejects unexpected/missing files and links, and verifies payload hashes before execution. Tamper tests exercise that bootstrap body. The Windows helper checks both manifests.

2. **CLOSED — abandoned layout trial.** Begin/revert now change only the running console map. Saved boot/greeter settings remain unchanged until finish. Fresh authenticated sessions can abandon trials, including from retained stock without overwriting stock’s settings. The qualification adds an actual QMP reset followed by German console/login checks, abandon and guarded reboot.

3. **CLOSED — interrupted setup.** Installation stages and atomically publishes the payload; durable journals allow matching interrupted operations to resume. Preparation records intent before mutations and validates permitted intermediate states. Failure-injection tests cover mutations, record writes and publication boundaries.

4. **NOT CLOSED — diagnostic persistence/export verification is incomplete.** The implementation now persists STOP records and includes them in checked export, but the required failure → export → reboot survival test is missing. See the finding below.

5. **CLOSED — stale status lines.** INSTALL and EMERGENCY now identify qualification 21’s completed VM scope while retaining **NOT RELEASED** and the physical gates.

**Should-fix — the new diagnostic test does not test reboot survival.**  
At [test_owner_export.py:65](C:/Users/pab/AresOS-14-owner-tools/os/tests/test_owner_export.py:65), the “reboot model” merely creates and deletes an unrelated directory, then rereads existing fixture files. It also overrides the production diagnostic path. The VM’s only [export](C:/Users/pab/AresOS-14-owner-tools/os/ci/owner_vm.py:960) precedes its deliberate STOPs, so qualification does not close this gap despite the [REPORT claim](C:/Users/pab/AresOS-14-owner-tools/reviews/14-owner-tools/REPORT.md:116).

**Fix:** generate a controlled STOP before export, export its exact diagnostic through the owner command, reboot, then verify that diagnostic’s bytes on the tools stick. Correct the qualification claim until exercised.

All 12 payload hashes, source copies, manifest fingerprint and documented bootstrap/catalog equality checked successfully. Native/VM tests were not rerun: WSL access was denied and no native Python installation was available. No additional runtime defect identified.

CHANGES-NEEDED