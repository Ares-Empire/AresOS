Reviewed head `8ee4aefa` read-only. `bash -n` and `git diff --check` pass. I did not run Gradle, Minecraft, or a compositor.

1. **Blocking — helper cleanup can kill an unrelated process.**  
   [run-hub.sh:103](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/run-hub.sh:103): cleanup remembers only the helper’s PID. If the helper dies during the game and Bash reaps it, that PID can belong to another process by cleanup time. `kill -0` then accepts that unrelated process, and cleanup sends it TERM and KILL. KILL is also unconditional after the polling loop, including when TERM successfully ended the helper.  
   **Fix:** retain process identity for shutdown, use a pidfd or an owned helper scope, and reap the child. Send KILL only to the same helper if it remains alive.

2. **Blocking — GPU probes escape cleanup and can retain the client-test lock.**  
   [client-test.sh:99](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/client-test.sh:99): probe cage/Xwayland processes run inside command substitutions, outside `aresos_scoped`, with no cleanup registration. TERM to the script can leave it waiting for the substitution; cancellation does not explicitly stop those children. Furthermore, `timeout 30` sends TERM without a KILL deadline. A wedged probe can therefore remain running and retain the inherited lock descriptor. [Coreutils’ timeout implementation](https://github.com/coreutils/coreutils/blob/master/src/timeout.c) confirms both its separate process group and optional KILL escalation.  
   **Fix:** supervise probes from the outer shell through owned scopes and asynchronous `wait`, capture output separately, and enforce a bounded TERM/KILL shutdown.

3. **Blocking — signals during startup can leave an unregistered child running.**  
   [env.sh:107](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/env.sh:107) and [run-hub.sh:128](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/run-hub.sh:128): each starts a background process before saving `$!`. A signal between those commands invokes cleanup with an empty PID. For the scope, `systemctl stop` can run before the child creates the unit; the child can subsequently start Gradle/cage after cleanup has finished. The helper has the equivalent launch/capture window; its parent-death signal does not cover a parent that disappears before `setpriv` installs it.  
   **Fix:** defer signal-triggered exit across launch/PID capture, then process any pending signal. Ensure children cannot proceed beyond startup until their ownership is registered.

4. **Should-fix — helper readiness and reuse do not identify the socket’s server.**  
   [run-hub.sh:77](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/run-hub.sh:77), [run-hub.sh:89](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/run-hub.sh:89), and [run-hub.sh:137](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/run-hub.sh:137): `serving` establishes only that something listens at the path. `own_helper` separately establishes that the recorded process exists. It never proves that process owns that socket. During startup, another session’s helper can claim the socket after the initial check; the script then treats that listener as its new helper and launches Minecraft with mismatching credentials.  
   **Fix:** verify socket peer credentials against the expected PID/start identity and complete an authenticated hello with the intended instance/nonce before launching the game. Refuse an unrelated listener without modifying it.

5. **Should-fix — the refusal checks can be stale by launch time.**  
   [client-test.sh:51](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/client-test.sh:51): the last check occurs before GPU probing, which can involve three 30-second attempts. Lunar can start, or available memory can drop below 6 GiB, during that interval. Even the post-lock check runs only when contention was observed.  
   **Fix:** acquire the lock, check conditions, and check again immediately before starting Gradle after probing. Preserve `--force` as the explicit override.

6. **Should-fix — Lunar detection matches every executable under its directory.**  
   [env.sh:56](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/env.sh:56): the scan does not require a Java executable. A launcher, updater, or other executable under `.lunarclient` produces the “Minecraft is running” refusal even when no game is running. Working around that with `--force` also disables the memory protection.  
   **Fix:** restrict the `/proc/<pid>/exe` match to Lunar’s Java executable, as the brief specifies.

7. **Should-fix — forwarded Gradle options can defeat process containment.**  
   [env.sh:88](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/env.sh:88) and [client-test.sh:149](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/client-test.sh:149): user arguments follow `--no-daemon`, so `--daemon` overrides it. Gradle explicitly selects the last conflicting boolean option. A reused daemon and its children can consequently live outside this invocation’s scope; conversely, a daemon created inside the scope can become available to another session before cleanup kills it. Forwarding `--stop` also reaches other sessions’ same-version daemons. See [Gradle’s option parser](https://github.com/gradle/gradle/blob/master/platforms/core-runtime/cli/src/main/java/org/gradle/cli/CommandLineParser.java) and [daemon documentation](https://docs.gradle.org/current/userguide/gradle_daemon.html).  
   **Fix:** enforce the daemon policy after argument parsing and reject lifecycle options that operate on shared daemons.

8. **Should-fix — screenshot preservation reports success after failure.**  
   [client-test.sh:124](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/client-test.sh:124): copy errors are suppressed, yet cleanup always prints “Copied this run’s screenshots”. Because cleanup is invoked with `|| true`, its `mkdir` failure also does not stop execution. An unwritable destination can therefore produce a successful run and a false preservation message; following the checkout reminder then loses the screenshots.  
   **Fix:** validate the destination before the heavy run, check copy results, and clearly report preservation failure.

The normal display routing looks correct: cage receives forced headless backends with the real display variables removed, and there are no real-session input-injection commands. The fixed flock file is never unlinked, and `--force` does not bypass locking.

The six OS skips cover Windows-specific discovery/path behavior. The changed client test preserves the click-count and selection checks: no launch is `[]`, one empty-command launch is `[[]]`, and its uniqueness assertion distinguishes Notepad from other configured apps.

CHANGES-NEEDED