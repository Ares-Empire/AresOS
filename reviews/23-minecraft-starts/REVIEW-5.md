Reviewed `d6aab7ab` against `9ba37be7`. Four findings remain.

1. **Blocking — an unsent SIGKILL can still become an automatic restart.**  
   Where: [aresos-desktop-java:162](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop-java:162).

   Java ignores SIGTERM; `wait(STOP_WAIT)` times out; an external SIGKILL ends Java before the wrapper’s next `send_signal()`. The wrapper nevertheless appends `9` to `sent`. Python’s `send_signal()` polls first and can return without sending anything. Consequently, `status=-9, sent=[15,9]` becomes “wrapper stopped it,” counting a failure and restarting. [CPython implementation](https://raw.githubusercontent.com/python/cpython/v3.12.0/Lib/subprocess.py).

   **Fix:** distinguish attempted signals from confirmed sends; a suppressed or failed send must not establish ownership of Java’s death. Treat ambiguous outcomes conservatively. Add a deterministic external-kill hook between the timeout and SIGKILL delivery, checking both record and socket paths.

2. **Should-fix — exit zero still depends on handoff ordering.**  
   Where: [aresos-desktop:1560](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:1560).

   An authorized Java that exits zero before its PID is accepted is classified as a failed start and automatically restarted in hub mode. The same exit after acceptance is a quit. This contradicts round 4’s rule that Java’s real status decides when the wrapper did not stop it. A delayed handoff can therefore undo the owner’s quit.

   **Fix:** classify an unstopped exit zero as a quit regardless of `launch.reported`. Test zero before PID delivery, after refusal, and during lost-handoff recovery; require zero failures and no automatic restart.

3. **Should-fix — reboot can permanently discard an explanation while retaining its unresolved latch.**  
   Where: [aresos-desktop:1517](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:1517), [aresos-desktop-java:220](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop-java:220).

   The unresolved latch survives in `~/.local/state`, but its explanation exists only in `$XDG_RUNTIME_DIR/aresos/desktop-exit.json`. Consider: an end is latched as unresolved; the supervisor stops; the wrapper writes a complete non-kill explanation but cannot deliver it; the owner reboots. Reboot removes the explanation, while the unresolved kill latch survives indefinitely and prevents the hub starting.

   **Fix:** durably retain terminal facts until reconciliation is committed, bound to launch and original session. Reconciliation after reboot must update accounting without applying the previous session’s quit disposition to the new session. Test reboot between writing the explanation and consuming it.

4. **Should-fix — the model does not establish the claimed event coverage or independent quit invariant.**  
   Where: [test_aresos_desktop.py:1676](/C:/Users/pab/AresOS-23-minecraft-starts/os/tests/test_aresos_desktop.py:1676), [test_aresos_desktop.py:1727](/C:/Users/pab/AresOS-23-minecraft-starts/os/tests/test_aresos_desktop.py:1727).

   `W` executes stopping, timeout escalation, record creation and report delivery as one indivisible event. Restarts and Java deaths cannot occur between those steps; the injected race covers only the initial poll. This excludes findings 1 and 3.

   Signal-caused death has an independent model flag, but quit classification uses `self.accepted`, obtained from the supervisor’s actual return value, and repeats its acceptance-dependent rule. Thus finding 2 is asserted as correct. The reboot check runs after settlement and removes only the runtime record, leaving the exit record behind.

   **Fix:** expose the actual send/wait/write/report boundaries as schedulable events, derive expected outcomes from an independent event ledger, and model reboot by clearing the entire runtime directory. The supplied revert proof demonstrates detection of those three selected reversions; it does not prove completeness.

The replacement deadline correctly gives an **unreported** launch the full window after observed loss. Same-session unresolved reconciliation retains its once-only accounting guard. I found no additional package 21 or package 24 contract regression in this diff.

`git diff --check` passed; no files changed. I could not independently execute Python tests: WSL returned `E_ACCESSDENIED`, and Windows reported no installed Python runtime. The full suite remains unverified as disclosed.

CHANGES-NEEDED