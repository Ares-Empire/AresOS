# 42 step 3: fix check of REVIEW-4 (Codex gpt-6-astra high, 2026-11-17)

Checks `9d41a9e1` (REVIEW-4 fixes, notes in FIXES-4.md) at merged head `3fad2829`. Read-only sandbox: test errors from temporary-file creation are environmental.

The commit/guide checks are fixed, but the home-state changes introduce two VM blockers and leave a persistence blind spot.

| Original finding | Verdict |
|---|---|
| **1. Real-commit comparison** | **Fixed.** Only the verified v4 baseline can defer locally. Any changed bundle must match; the VM caller does not enable deferral. A wrong newest reference no longer bypasses comparison. |
| **2. Real guide fingerprint** | **Fixed.** Both the real guide’s first line and full fingerprint are compared. |
| **3. Control checker** | **Not fixed—explicitly deferred to step 2.** The invalid checker invocation is removed. Results report `control_checked: false`; enabling Control blocks VM qualification. No current executable result claims Control was checked. |
| **4. Polkit and terminal PATH** | **Fixed.** Both checks run after reopening the terminal, with results retained. |
| **5. Usable home-state persistence** | **Partly fixed.** The schema-4 fixture, metadata comparison and daily-user checks improve coverage, but have the three problems below. |
| **6. Receipt’s Control setting** | **Fixed.** Generation passes and records the production setting; the VM rejects missing, malformed or mismatching settings. |
| **7. Tests supplying expected answers** | **Partly fixed.** Submitted Python probes now execute, with meaningful fault injections and a kill-removal mutation test. However, the invented filesystem layout hides actual VM failures and contains no saved-world data to protect. |
| **8. Identical installer invocation** | **Fixed.** Identical fingerprints return the no-op before version comparison; separate tests cover all four version/fingerprint cases. |

Remaining problems:

1. **Blocking — the required libraries path does not exist in the real instance.**  
   [os/ci/release28_walk.py:92](os/ci/release28_walk.py:92), [os/tests/test_owner_walk.py:545](os/tests/test_owner_walk.py:545).  
   The probe requires `minecraft/libraries`, while the [real provisioner](os/config/usr/libexec/aresos-desktop:425) creates `libraries` directly under the instance. A correctly provisioned R28 therefore stops at its first home check. The test creates the same incorrect path, so it passes. **Fix:** require the real layout, including `patches`, and construct the fixture from the provisioner’s layout rather than duplicating the mistaken assumption.

2. **Blocking — rollback requires R28 image files to remain available on R27.**  
   [os/ci/release28_walk.py:384](os/ci/release28_walk.py:384), [os/ci/release28_walk.py:657](os/ci/release28_walk.py:657).  
   `home()` runs the same accessibility requirements on R27. The retained `minecraft/mods` link points into R28’s `/usr/share/aresos/minecraft`, which R27 lacks. Its `exists()` check fails even when every home file and symlink survived correctly. Correcting issue 1 also exposes this for `libraries`. The model keeps `/shared/*` available across every boot, masking the failure. **Fix:** on R27 compare retained links and home data without requiring R28 image targets; require those targets again after forward. Model their absence on the rollback boot.

3. **Should-fix — losing saved-world contents remains invisible.**  
   [os/ci/release28_walk.py:364](os/ci/release28_walk.py:364), [os/ci/release28_walk.py:385](os/ci/release28_walk.py:385).  
   `minecraft/saves` links to the separate home worlds directory. The snapshot uses `followlinks=False`, while the daily-user reader checks only the target directory’s accessibility. Deleting or corrupting its world files leaves the recorded link and accessibility unchanged. Once the blockers above are corrected, that loss can still pass qualification. **Fix:** seed representative persistent save data and compare its resolved home-directory contents and metadata across the round trip; add deletion, corruption and access-denial cases.

Verification: the permitted `test_release28_rehearsal.py` command reported **24 tests, 6 errors**, all caused by read-only filesystem restrictions; these are not counted as code failures. The preflight found no `ksshaskpass`, but the second `pgrep` matched the sandbox wrapper, so no standalone `test_owner_*` module ran. All **267 receipt source hashes match**, and `git diff --check` passed. No files were edited.

CHANGES-NEEDED