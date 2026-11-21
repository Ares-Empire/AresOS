# 42 step 1: cross-review (Codex gpt-6-astra high, 2026-11-17)

Independent second-model review of step 1 at `8792c274` (diff against `e33ffc46`), after REVIEW-1 (Fable) and REVIEW-2 (fix check). Read-only sandbox, so `test_release28` could not create temporary files there (40 errors from that, not from the code). Paths below point at the review worktree; read them relative to the repo.

The diff still accepts incorrect images. I found five should-fix issues and one nit at `8792c274`.

1. **Should-fix — missing RPM files pass. New failure case related to REVIEW-1 S5/N5.**  
   [os/ci/release_diff.py:1409](os/ci/release_diff.py:1409), [1456](os/ci/release_diff.py:1456). A newly packaged file absent from both images never enters `changed`; RPM verification cannot stop publication. An in-memory execution of `main()` with `/usr/lib/jvm/java-25-openjdk/bin/keytool` missing returned **`status: passed`**, no problems, and `rpm_verify.exit_code: 1`. The Java version check uses the separate `java` executable.  
   **Fix:** require every expected non-ghost RPM path to exist and match its record; make unexpected RPM verification failures fatal. Test missing files using RPM records independent of the image fixture.

2. **Should-fix — generated-file exceptions remain broader than their explanations. New residual beyond REVIEW-1 S1.**  
   [os/ci/release_diff.py:417](os/ci/release_diff.py:417), [1265](os/ci/release_diff.py:1265). The retained globs accept arbitrary descendants, ownership, permissions and file types. Probes accepted `usr/lib/sysimage/libdnf5/unreviewed.sh` with mode `04755`, a repository file named `not-countme`, and deletion of `var/cache/ldconfig/aux-cache`. None establishes the claimed regeneration. The test checks dropped patterns, leaving these cases uncovered.  
   **Fix:** restrict exceptions to the observed filenames or tightly defined filename patterns, enforce reviewed metadata and allowed addition/removal behavior, and test neighboring paths.

3. **Should-fix — alternatives links need not select the correct executable. New.**  
   [os/ci/release_diff.py:1128](os/ci/release_diff.py:1128). The rule checks membership in the union of added-package paths, losing the association between each alternative and its target. `/etc/alternatives/java → …/bin/keytool` passes. Users invoking `java` would run the wrong program; image checks invoke Java through its pinned absolute path.  
   **Fix:** preserve master/slave target associations when parsing records, validate the complete record structure, and require each link to match its corresponding reviewed target. Add swapped-target tests.

4. **Should-fix — Prism’s pinned manifest excludes links and modes. New; distinct from REVIEW-1 N4.**  
   [os/ci/release_diff.py:1022](os/ci/release_diff.py:1022), [1092](os/ci/release_diff.py:1092). Only regular-file hashes are pinned. Any relative symlink staying lexically inside the bundle passes, including a dangling link to `nonexistent.so`. Missing expected symlinks are invisible because release 27 never contained them. This can break functionality outside the startup smoke test while the bundle remains “explained.”  
   **Fix:** pin and compare the complete typed bundle inventory, including symlink targets, directory/file modes and expected path presence.

5. **Should-fix — schema comparison ignores runtime lookup metadata. New.**  
   [os/ci/release_diff.py:561](os/ci/release_diff.py:561). The GVDB reader skips bucket/bloom contents and discards item hashes, then enumerates entries directly. Flipping the stored hash of `org.gnome.desktop.wm.preferences` in `after.compiled` still produced exactly the accepted package-31 change. That corruption affects hash-based lookup without changing the values this reader reports.  
   **Fix:** validate lookup structure using GLib, or compare against a deterministically rebuilt expected compiled file. Add corrupted-hash/bucket negative tests.

6. **Nit — the jar-pin exception also permits file-mode changes. New.**  
   [os/ci/release_diff.py:504](os/ci/release_diff.py:504). `source_changes()` checks changed filenames and blob contents, ignoring Git modes. Making `desktop.lock.json` executable is accepted and attributed to a jar-pin renewal, exceeding “only the jar’s sha256 may differ.”  
   **Fix:** require unchanged Git entry type/mode before applying `jar_pin_only`.

I formed these findings before reading REVIEW-1/REVIEW-2. Current publish caps correctly refused publishing, including with only the dispatch cap raised. Evaluation of 84,480 input combinations found no write-capable job enabled by `dry_run_28`.

Verification: `test_ci_api_permissions.py` and `test_ci_step_environment.py` each passed four tests. `test_release28.py` reported 59 tests with 40 errors because temporary-file creation is blocked by the read-only environment; it is not verified green here. The probes used memory and stand-ins, with no containers or prohibited commands. The worktree remains unchanged.

CHANGES-NEEDED