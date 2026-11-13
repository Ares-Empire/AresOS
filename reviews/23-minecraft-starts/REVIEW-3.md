Reviewed `e69b16a0`. **One blocking and two should-fix findings remain.**

1. **Blocking — a SIGKILL can still become an automatic restart after PID acceptance.**  
   Where: [aresos-desktop:1368](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:1368), [aresos-desktop-java:239](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop-java:239).

   If the supervisor accepts `jvm_started`, its answer is lost, and Java receives SIGKILL before the wrapper handles that loss, the wrapper correctly reports `status=-9`, with `stopped=False` in its exit record. But `on_jvm_failed()` ignores the supplied status once `launch.reported` is true and unconditionally sets `stopped_reason`. `finish_jvm()` then prioritizes that reason over SIGKILL and schedules an ordinary crash restart.

   **Fix:** carry an explicit wrapper-initiated-stop indicator through the socket protocol and reconcile it with the exit record. Preserve actual termination status when the wrapper did not stop Java. Add an accepted-PID/lost-answer/SIGKILL regression requiring latched `RECOVERY/killed`, zero counted failures and no restart. The existing accepted-answer-loss test covers only wrapper-initiated termination.

2. **Should-fix — the lost-handoff deadline expires before the wrapper’s permitted stop finishes.**  
   Where: [aresos-desktop:1537](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:1537), [aresos-desktop-java:147](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop-java:147).

   When the connection closes before PID acceptance, the supervisor waits **2 seconds** before classifying the start as an unexplained kill. Meanwhile, the wrapper allows Java **10 seconds** to terminate before writing its failure record and reconnecting. A child taking more than two seconds to stop therefore triggers a persistent kill latch. Its subsequent explanatory report is discarded because `launch.failed` is already true.

   **Fix:** coordinate the bounded stopping/reporting phase with the supervisor’s deadline, while retaining conservative handling of genuinely unexplained deaths. Test connection loss with a child that delays or ignores SIGTERM; require eventual termination and exactly-once failed-start accounting. Current connection-loss tests use promptly terminating children.

3. **Should-fix — missed pressure samples count toward the continuously-clear minute.**  
   Where: [aresos-desktop:1581](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:1581).

   `sample_pressure()` overwrites `pressure_checked` without checking the elapsed sampling gap. One clear sample, a supervisor stall exceeding 60 seconds, and another clear sample permit Retry immediately. Pressure during that unobserved interval is unknown; it has nevertheless been counted as continuously clear.

   **Fix:** reset the clear interval when the sampling gap exceeds the allowed cadence plus a defined tolerance. Add a test that advances the clock beyond 60 seconds without running sampling ticks, then verifies Retry remains refused.

Disposition of every REVIEW-2 finding:

| Finding | Assessment | Recorded isolated-revert evidence |
|---|---|---|
| 1. Pre-handoff kills | Fixed before acceptance; blocking acceptance-boundary gap above | Kill/reconciliation assertions fail; loop restarts |
| 2. Clear-pressure minute | Normal sampling and supervisor-restart cases fixed; sampling-gap defect above | Immediate Retry incorrectly succeeds |
| 3. Lost handoff | Child termination implemented; reporting deadline remains inconsistent | Surviving-child timeout; accepted-answer classification fails |
| 4. Persisted disposition/backoff | Fixed: saved with accounting, deadline restored, runtime-session binding permits a new boot | Quit restarts and backoff disappears |
| 5. Identifiers/finite angles | Fixed; identifier rules match the inspected Minecraft bytecode | Malformed fixtures pass incorrectly |
| 6. Modified UTF-8 | Fixed, including Java-written emoji/NUL fixtures | Ordinary UTF-8 decoding errors |
| 7. Decompression errors | Fixed, including old-level fallback | `zlib.error` escapes |
| 8. Late window identification | Fixed for the reported event sequences and split reads | Expected editor activation is missing |
| 9. VM pressure proof | Fixed; allocation, scope, kill evidence and responsiveness required | Six invalid cases incorrectly pass |

The source/mod stages address the missing-`curl` cause, and the resolve path now uses those same stages. CI run `42865819198` records a built, hash-matching jar and an OOM-killed pressure source with surviving recovery processes. Only the report changed between that tested revision and this head. Package 21’s command/PATH isolation and package 24’s nonce, instance and private status-pipe contract remain intact.

I inspected the tests and supplied revert evidence but could not independently rerun Python: WSL returned `E_ACCESSDENIED`, and no Windows Python is installed. Production diffs passed `git diff --check`; all three changed shell scripts passed `bash -n`. No files were modified.

CHANGES-NEEDED