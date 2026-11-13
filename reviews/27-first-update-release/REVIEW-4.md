Reviewed **5f3fd6b1**, limited to the seven commits and requested follow-ups. **The blocking update-recovery defect is fixed. One harness-only nit remains.** No files changed.

**Nit — the injected-stop-failure test can still leave an untracked child.**  
**Where:** [test_owner_update.py:1833](C:/Users/pab/AresOS-27-review/os/tests/test_owner_update.py:1833), [cleanup registration:2007](C:/Users/pab/AresOS-27-review/os/tests/test_owner_update.py:2007).

`stage-then-run` launches `sleep 3600`. When the injected `stop()` raises before signalling anything, cleanup kills only the recorded shell and fake-bootc PIDs; it does not capture or kill that sleep. The class check examines only those recorded identities, so it cannot prove no descendants remain. The original survivor-loop leak is fixed, and d90d2f4a correctly waits for SIGKILL to take effect, but neither addresses this child.

**Laptop impact:** none; this affects test cleanup. **Fix:** retain the fixture session identity, clean up all its members after assertions, and verify that session is empty.

The requested checks:

1. **Stop recovery passes for the update path.** [Step.members():332](C:/Users/pab/AresOS-27-review/os/owner-tools/owner.py:332) parses bytes, skips vanished/empty entries and records other inspection failures as unknown. Those failures cannot become proof of termination. `stop()` signals the process group before scanning, for both TERM and KILL.

   [stop_update():1525](C:/Users/pab/AresOS-27-review/os/owner-tools/owner.py:1525) independently protects stopping, diagnostics, reconciliation and mask restoration with `except Exception`. An unproved stop skips reconciliation; restoration is still attempted and checked. Collected failures produce **“Do not reboot; export records and get help.”** Exceptions from `wait()` also enter this routine through `update()`’s enclosing handler. The successful staging branch remains unchanged.

   One qualification: [Host.script():264](C:/Users/pab/AresOS-27-review/os/owner-tools/owner.py:264) catches exceptions from its **stop calls**, but is not generally exception-proof around `wait()` or diagnostics. An unrelated `wait()` exception can still bypass its shutdown handling. The reviewed `/proc` name failure is removed, and production update staging uses the separately protected `Host.start()`/`Step` route, so this does not reopen the update blocker.

2. **The new regressions exercise the real staging runner.** They use real Bash, `Host.start()`, `Step`, and the rendered `update.sh`, with fixture commands. Deployment observations and reconciliation remain modelled. The invalid names cover timeout, Ctrl+C and failed-shell cases; the injected failures check no deletion, mask restoration and combined error reporting.

   Static revert tracing supports the assertions: restoring the old unprotected stop makes the injected-stop case fail **“the masks this run removed are not back”**; restoring the old scan/shutdown implementation breaks the invalid-name cases. Reverting only byte handling while retaining conservative error handling still breaks their clean-stop expectations. **I did not execute these revert experiments.**

3. **JUDGMENT-CALL 11 now matches the recovery contract.** It says restoration is attempted and checked, and makes “nothing changes at the next start” conditional on every check passing. It does not widen the accepted finalizer change.

4. **The password-rule change is adequate in this harness.** Field 2 starting with `$` rejects empty, `*`, and every `!…` locked value. Those lock meanings match [shadow-utils’ documentation](https://github.com/shadow-maint/shadow/blob/master/man/shadow.5.xml). The prefix alone is not a complete hash-validity or authentication test, but the rehearsal first runs `sudo passwd ares`, then logs in using that password and exercises password-authenticated sudo. Those checks remain intact. The new rule does not weaken the required proof.

5. **Fingerprint consistency passes.** Recomputed fingerprint:
   `851eb742bfe20bd4b47370b9f2558494edf4b74056d7023cc0d412e32fee6f33`.

   All 15 payload/source hashes match; source and payload `owner.py` are identical. All 16 SHA256SUMS entries, INSTALL pins, commands.json, INSTALL-STATUS, report and both source-record lists agree. All **46 pending-list** and **250 host-walk** hashes match. `test_release27` has no stale fingerprint pin. `f85084b6…` remains only in the historical review and follow-up brief.

6. **The builder’s safety claims hold, with a scope correction.** `deployment_processes()` decodes argv only after selecting a `bootc`, `rpm-ostree` or `ostree` executable. An arbitrary unrelated process with invalid argv does **not** necessarily refuse the update.

   For a selected process, decoding failure during preflight reaches the outer **STOP** handler and no-reboot guidance, rather than an uncaught traceback: `UnicodeDecodeError` inherits from the caught `ValueError`. [Python exception hierarchy](https://docs.python.org/3/library/exceptions.html#exception-hierarchy). During unsuccessful-update reconciliation, that same failure is caught **after step termination**, prevents deletion and cannot skip mask restoration.

   Package 22’s argv inspection already uses replacement decoding; its remaining text-decoding exposure is principally the `/proc/stat` helpers. These checks are not part of the active update-step shutdown path.

Verification was static tracing, hash checks and `git diff --check`—which passed. Python is unavailable locally and WSL returned `E_ACCESSDENIED`; Linux tests and run 10’s eventual records are not verified here. This is the scoped code-safety verdict, not rehearsal sign-off.

SAFE