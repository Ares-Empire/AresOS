Reviewed `5e53ca2f`, limited to the requested fixes and their dependencies. No files changed. Syntax checks on all four scripts and `git diff --check` passed. I did not run Gradle, Minecraft, or a compositor.

The eight original findings:

1. **CLOSED — helper PID reuse.** Helper shutdown now targets its scope; remembered-PID TERM/KILL operations are gone.
2. **CLOSED — GPU probes escaped cleanup.** Probes now use registered scopes, asynchronous waits, file output, and a 30-second runtime limit followed by a 5-second KILL deadline.
3. **CLOSED — signal gap during launch.** Signals are deferred across launch and registration until the scope becomes active or the launcher ends. Startup failure handling still has the separate issue below.
4. **CLOSED — helper/socket mismatch.** Each run creates a fresh private socket directory, starts its own helper, and supplies that socket and matching credentials to the game. Helper reuse is gone.
5. **CLOSED — stale resource checks before Gradle.** Both client scripts repeat Lunar and memory checks after their preparation, before Gradle. `--force` retains its intended effect.
6. **CLOSED — overly broad Lunar match.** Detection now requires an executable matching Lunar’s `*/bin/java`, including the resolved home path.
7. **OPEN — Gradle daemon policy remains bypassable.** [env.sh:99](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/env.sh:99) rejects only double-dash spellings. Gradle also accepts `-daemon`, `-stop`, `-status`, and `-foreground`; its [9.8.0 parser explicitly supports single-dash long options](https://raw.githubusercontent.com/gradle/gradle/v9.8.0/platforms/core-runtime/cli/src/main/java/org/gradle/cli/CommandLineParser.java). These still permit shared-daemon interaction. **Fix:** reject those equivalent spellings in the shared guard.
8. **CLOSED — false screenshot-copy success.** The destination is checked before the run, copy failures are reported, and cleanup changes an otherwise successful exit to 1.

Additional findings introduced by the fixes:

- **Should-fix — systemd query failures are treated as confirmed absence.**  
  [env.sh:149](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/env.sh:149) suppresses stop failures, and the following state query treats empty output from a failed command as “gone.” A temporary manager/bus failure can therefore let cleanup finish with scopes still running and retaining the lock. Likewise, [run-hub.sh:89](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/run-hub.sh:89) can remove an old run’s directory when `list-units` failed. If only the initial stop fails, subsequent TERM repetitions never arm systemd’s stop/KILL deadline.  
  **Fix:** check command status separately from output, retry unacknowledged stop requests, and require confirmed absence before completing cleanup or deleting stale directories.

- **Should-fix — startup cancellation has no deadline.**  
  [env.sh:132](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/env.sh:132) defers every INT/TERM/HUP while waiting for activation, without a startup deadline. A launcher stuck awaiting scope activation keeps cancellation deferred and can retain the client-test lock. The probe’s runtime limit applies only after activation.  
  **Fix:** bound scope startup and provide a cancellation protocol that prevents a late command launch before releasing ownership and exiting.

- **Should-fix — a registered name is not proof this run created the unit.**  
  [env.sh:128](/var/home/ares/AresOS-29-linux-dev-rig/mod/dev/env.sh:128) registers the generated name before creation succeeds. If that name already exists, `is-active` can accept the existing scope; after `systemd-run` fails, cleanup stops that other scope. PID plus random suffix makes this unlikely, but does not establish ownership.  
  **Fix:** acknowledge successful creation from inside the new scope before treating it as owned; creation failures must never authorize stopping an existing unit.

With a responsive manager and successful creation, the blocking `flock` shares the parent’s open-file description, avoids the previous polling disadvantage, and adds no lasting lock holder. Repeated TERM stays confined to recorded scopes. Normal private-directory creation uses mode 0700 and does not address `$XDG_RUNTIME_DIR/aresos`.

CHANGES-NEEDED