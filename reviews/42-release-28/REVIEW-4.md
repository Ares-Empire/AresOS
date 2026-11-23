# 42 step 3: review (Codex gpt-6-astra high, 2026-11-17)

Review of step 3 at `841de8d1` (`git diff 75a83393 HEAD`). Read-only sandbox, so some tests could not create temporary files there. Paths below point at the review worktree; read them relative to the repo.

CHANGES-NEEDED: the route is substantially wired, but several checks can validate the stand-in while missing differences in the owner’s route.

1. **Blocking — byte-identity checking can be skipped by the mismatch it should catch.** [release28_walk.py:234](os/ci/release28_walk.py:234)  
   `real_commit()` treats *any* different newest reference as “not cut yet” and skips `matches()`. A version-5 payload accidentally naming another digest therefore escapes comparison while the VM installs the correctly generated stand-in.  
   **Fix:** permit deferral only for the explicitly verified, unchanged v4 baseline. Require equality for any new bundle, and require a successful real-commit comparison before accepting final release qualification.

2. **Should-fix — the fingerprint comparison never checks the real guide.** [release28_walk.py:272](os/ci/release28_walk.py:272)  
   `compare()` reads the generated stand-in guide; `matches()` binds only the tools tree and release record. If the real payload is correct but `OWNER-TOOLS.md` still displays v4’s fingerprint, the rehearsal passes while the owner’s phone comparison correctly refuses the password window.  
   **Fix:** compare the real announced commit’s first line and full fingerprint with the rehearsed values. Other guide text can remain unbound.

3. **Should-fix — Control’s runner assumes a checker that is not installed there.** [release28_walk.py:407](os/ci/release28_walk.py:407)  
   It executes `/usr/share/aresos/control/release_checks.py`. The available 18c implementation provides `os/ci/control/release_checks.py` as a rehearsal script, supporting execution through stdin; its build does not install the assumed path. Turning `CONTROL_RIDES` on will therefore stop the VM, although the synthetic Control walk passes. The surrounding probe also neither asserts its collected folder metadata nor proves the required absence of login dependencies.  
   **Fix:** execute the bound checker through its supported interface, retain and validate its results, and add the login-ordering check. Recheck Control after the final R28 boot as well.

4. **Should-fix — R28 omits package 27’s runtime privilege and terminal-PATH checks.** [release28_walk.py:584](os/ci/release28_walk.py:584)  
   `release_rules()` checks sudo, the compositor’s system PATH and the terminal’s configured argv. Unlike package 27’s route, this walk does not run `polkit_sweep()` or `terminal_path()`. An additional passwordless polkit authorization, or a broken terminal bashrc that drops the owner’s directories, can pass these checks.  
   **Fix:** restore the relevant package-21 checks on R28, with the desktop session active and the reopened terminal available.

5. **Should-fix — the home-file marker cannot prove usable home-screen state.** [release28_walk.py:340](os/ci/release28_walk.py:340), [release28_walk.py:638](os/ci/release28_walk.py:638)  
   The planted `apps.json` has no `schemaVersion`; the real `AppsConfig` loader rejects it. After `forward`, the walk checks its bytes and the instance directory’s existence, but merely records the new instance-tree hash. Permission changes are also invisible to its content-only hashes. Thus preserved but unusable configuration can PASS.  
   **Fix:** plant a valid representative configuration owned by the daily user, check accessibility as that user, and compare stable instance files and metadata with explicit allowances for Prism’s mutable files. Describe actual Minecraft loading as unverified.

6. **Should-fix — the host receipt silently forces Control off.** [walk-host.py:29](reviews/42-release-28/walk-host.py:29), [test_owner_walk.py:1047](os/tests/test_owner_walk.py:1047)  
   The receipt generator calls `walk()` with its default `control=False`; that function overwrites `CONTROL_RIDES`. Following the report’s instruction to enable Control and regenerate the receipt still records a walk with Control disabled. Hash freshness does not detect this configuration mismatch.  
   **Fix:** pass the production setting explicitly, record it in the receipt, and require the VM driver to match it—or record both variants separately.

7. **Should-fix — the new probe tests supply their own expected answers.** [test_owner_walk.py:504](os/tests/test_owner_walk.py:504)  
   Most session probes return success according to the stage name without evaluating the submitted program. For example, a broken Control checker path still receives `release_checks.status=0`; an ineffective `END_FOOT` program still produces the expected no-foot STOP. These tests exercise sequencing, but do not validate the new probe implementations or their rejection paths.  
   **Fix:** test the probe programs with controlled filesystem/process interfaces, and inject failures for retained foot processes, changed sites hashes, wrong ownership, missing instance files and incorrect memory limits. Each must stop qualification.

8. **Should-fix — the local installer model rejects an operation the real tools accept.** [test_owner_walk.py:470](os/tests/test_owner_walk.py:470)  
   The model refuses every same-version invocation. The real `update_tools()` first recognizes an identical fingerprint and returns “Tools already installed; nothing changed”; only different bundles reach the version refusal. Repeating the same routine therefore behaves differently locally and on the laptop.  
   **Fix:** model the identical-fingerprint no-op before comparing versions, and separately test identical bundle, same-version/different bundle, downgrade and newer bundle.

The builder’s JUDGMENT-CALLs: **1** is reasonable subject to finding 1; **2** is reasonable subject to checking the real guide; **3** is acceptable for preparing the persistence fixture—root’s `tee` performs the intended write, but does not qualify the interactive `sudo tee` experience; **4** is an acceptable SETUP workaround, not proof of clicking the Terminal app; **5** needs finding 5 fixed; **6** is reasonable for testing the wrapper’s scope and memory limit, but does not prove a real Minecraft world starts.

I found no cap-0 bypass in the inspected dispatch path. R27’s starting reference is pinned, every boot reaches the protected-disk audit through `finally`, and the VM no-foot check requires an actual stopped command with the expected error.

Verification: `test_rehearsal_budget.py` passed all 4 tests. `test_release28_rehearsal.py` reported 22 tests and 4 errors because the read-only sandbox prevented temporary-directory creation; it was not green. All 267 host-receipt source hashes match. No standalone `test_owner_*` module ran after the preflight matched the sandbox wrapper. No files were edited or VM/dispatch commands run.

CHANGES-NEEDED