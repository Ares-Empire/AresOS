Reviewed `7ec26b84`, separating the round’s changes from the merge of main. **Changes are still needed.** The missing VM run is not itself counted as a defect.

1. **Blocking — kills before PID handoff still trigger automatic restarts.**  
   Where: [aresos-desktop-java:191](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop-java:191), [aresos-desktop:1226](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:1226).

   If Java receives SIGKILL before `jvm_started` is accepted, `poll()` can reap it, identification fails, and the wrapper reports `jvm_failed`. If the wrapper also dies, `on_wrapper_gone()` takes the same path. Both count as ordinary crashes and schedule a restart. The kill latch only protects launches whose PID was already reported.

   **Fix:** preserve and reconcile pre-handoff termination status and scope result; conservatively latch unexplained deaths. Test SIGKILL of Java and wrapper immediately after authorization, before PID acceptance. Existing kill tests wait until the supervisor has the JVM PID.

2. **Should-fix — Retry does not require 60 seconds of cleared pressure.**  
   Where: [aresos-desktop:1402](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:1402).

   One `avg60 <= 10` reading immediately permits Retry; an unavailable reading also permits it. A short pressure spike and kill can leave that average below 10. PSI averages describe trends, not a continuously clear interval. [Kernel PSI documentation](https://docs.kernel.org/accounting/psi.html)

   **Fix:** track a continuously clear 60-second interval, resetting it on pressure or unknown readings. Restarting the supervisor must not bypass that interval. The current test changes pressure from 42 to 3 without advancing time and expects success—it encodes the wrong condition.

3. **Should-fix — a lost handoff can leave an untracked JVM running indefinitely.**  
   Where: [aresos-desktop-java:202](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop-java:202).

   A socket error during `jvm_started` merely prints a message and enters `child.wait()`. If the supervisor never recorded the PID, Java remains alive holding the desktop lock. The timeout schedules a restart, but `begin()` then finds the lock held and stops in recovery. A replacement supervisor likewise cannot adopt this JVM.

   **Fix:** make the launch/PID identity recoverable across connection loss, with reconnection and reconciliation, or safely abort an unaccepted startup. Test a real connection closure between authorization and PID acceptance. Current tests cover explicit refusal and simulated timeout, not this surviving-child case.

4. **Should-fix — exactly-once accounting forgets the resulting stop/backoff decision.**  
   Where: [aresos-desktop:933](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:933), [aresos-desktop:1293](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:1293).

   After reconciling exit 0, the supervisor persists `accounted`, clears the runtime PID, and enters `RECOVERY/quit` only in memory. Restart the supervisor again: there is nothing to adopt or account for, so `start()` launches Minecraft. A pending crash backoff is similarly lost.

   **Fix:** persist the session’s disposition and pending retry deadline alongside accounting, and restore them without recounting the exit. The new adoption test actually starts a second supervisor, but checks only the failure count—not that a deliberate quit remains stopped.

5. **Should-fix — malformed exact-home data still passes validation.**  
   Where: [aresos-desktop:579](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:579).

   `home.dimension` is accepted as any string, including an invalid resource identifier. Exact-home `yaw` and `pitch` accept NaN/infinity, although the site yaw and position receive finite-number checks. Consequently, `check_world()` can report `ok` for home data that cannot provide the promised arrival behavior.

   **Fix:** validate the resource identifier against the mod’s codec requirements and require finite exact-home angles. Add malformed-dimension and non-finite-angle fixtures, checking both preflight and readiness rejection.

6. **Should-fix — the NBT reader rejects valid Minecraft strings.**  
   Where: [aresos-desktop:502](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:502).

   NBT strings are decoded as ordinary UTF-8. The cached Minecraft 26.2 `StringTag` classes use `writeUTF`/`readUTF`, whose modified UTF-8 represents NUL and supplementary characters differently. A valid string containing an emoji can therefore make an otherwise valid `level.dat` appear damaged. [Java encoding specification](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/io/DataInput.html#modified-utf-8)

   **Fix:** implement compatible decoding. Add Java-produced string fixtures; the current fixture writer also uses ordinary UTF-8 and therefore conceals this mismatch.

7. **Should-fix — corrupt DEFLATE data escapes the world-damage handler.**  
   Where: [aresos-desktop:551](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:551), [aresos-desktop:607](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:607).

   `gzip.read()` can raise `zlib.error`, which neither exception handler catches. A valid gzip header followed by corrupt compressed data therefore crashes preflight instead of trying `level.dat_old` or reporting `world_damaged`. The keeper can repeatedly encounter the same exception. [Python gzip documentation](https://docs.python.org/3.12/library/gzip.html#gzip.BadGzipFile)

   **Fix:** normalize decompression errors into `NbtError`. Test corrupt DEFLATE separately from bad headers and truncated NBT, including the valid-old-level fallback.

8. **Should-fix — late window identification defeats focus hand-back.**  
   Where: [aresos-shell:1400](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-shell:1400).

   If Minecraft first appears activated with an unknown app ID, the helper replaces `active_handle` with that window. When its desktop app ID arrives later, `previous_handle` is now Minecraft itself. The hand-back activates that same handle and consumes the flag, leaving the editor/browser behind.

   **Fix:** retain the prior foreground target across identification of newly appearing windows. Test activation followed by a later app-ID event, including split socket reads. Existing tests present an already identified desktop window.

9. **Should-fix — the VM pressure check can pass without creating memory pressure.**  
   Where: [checks.py:259](/C:/Users/pab/AresOS-23-minecraft-starts/os/ci/overlay/checks.py:259).

   Any nonzero launcher exit satisfies “pressure source stopped.” A failed `systemd-run`, rejected property, or Python startup error leaves the protected processes unchanged and passes the remaining assertions. Kernel/oomd logs are collected but never required to demonstrate a kill.

   **Fix:** require successful scope entry and allocation, then correlate termination with that scope’s OOM evidence. Verify responsiveness during pressure. Add a negative test proving that launcher failure fails this check.

Disposition of every REVIEW-1 finding:

| Previous finding | Assessment |
|---|---|
| 1 — OOM restarting | **Partial.** Post-handoff unknown exits latch correctly; findings 1–2 above remain. |
| 2 — damaged hub | **Partial.** Missing home, disabled marker and incomplete provisioning now have meaningful rejection tests; findings 5–7 remain. Reads do not rewrite the save. |
| 3 — release build prerequisite | **Fixed structurally.** The shared Containerfile builds the jar and `configure` checks its hash. Package 27 at the referenced commit invokes `check-build.sh build`. Tests inspect this wiring and exercise the source-fetch/build script with stubs; an actual build and runtime wrong-jar rejection remain unproven. |
| 4 — JVM memory scope | **Fixed at the boundary.** Wrapper-enforced scoping covers forwarded/UI launches. The real-systemd test checks the child PID’s cgroup and `memory.high`; reverting the scope would fail that assertion. |
| 5 — downtime accounting | **Partial.** Launch-bound reconciliation and single counting are present; finding 4 remains. |
| 6 — manual-launch preflight | **Fixed for the reported bypass.** Every authorization invokes validation and checks instance directory/cwd. The drift tests exercise those rejection branches. |
| 7 — endless STARTING | **Partial.** Explicit failure and the 30-second deadline exist; finding 3 remains. |
| 8 — dependency pins | **Fixed structurally.** Exact component versions and hash-checked local metadata replace permissive LWJGL resolution. Wrong/missing/duplicate-component assertions target the original defect. Authenticated Prism download remains unverified. |
| 9 — recovery protection | **Configuration added; verification incomplete.** Ancestor `MemoryLow` and session `avoid` are sensible soft protection, without a new hard game cap. Effective inherited oomd behavior remains unverified, and finding 9 weakens the proposed evidence. |
| 10 — lost readiness | **Fixed for the reported cases.** Heartbeat loss/helper exhaustion clears readiness; adoption retains a deadline. The assertions check visible recovery without killing Java. |
| 11 — foreground preservation | **Partial.** The normal identified-window case is covered; finding 8 remains. |

The reported “33 of 35 fail on old code” is not sufficient finding-by-finding regression proof: several tests fail in shared setup because old code lacks `scope` reply fields or the `keep_foreground` argument. Keep interfaces compatible when reverting each causal fix, so the relevant behavioral assertion is what fails.

**I agree with updated JUDGMENT-CALL 10.** Unexplained whole-scope deaths should latch recovery and require explicit Retry. Its pre-handoff implementation remains incomplete.

Package 21’s system PATH, absolute command paths and recovery-shell isolation remain intact. Package 24’s nonce/instance authentication and private status pipe remain coherent; the focus issue above is the identified helper regression.

Verification: production-source `git diff --check` passed for both requested comparisons; all three changed shell scripts passed separate `bash -n` checks. Python tests could not run: WSL returned `E_ACCESSDENIED`, and `py -0p` reported no installed Python. No image/VM/Gradle run or file modification occurred.

CHANGES-NEEDED