# 23 REPORT: Minecraft starts in AresOS

Built by a Claude agent (Opus 5.5). Brief: `briefs/23-minecraft-starts.md` (empire board brief 264).
Branch `pkg/23-minecraft-starts`, PR #36. Review: Codex gpt-6-astra (high), fresh context.

Nothing was pushed to a registry, signed or published. The release pin is unchanged.

## Review fixes 5 (REVIEW-5, 2026-11-13)

REVIEW-5 (Codex gpt-6-astra, high, on `d6aab7ab`): 1 blocking, 3 should-fix, all again at the hand-off between
the supervisor and the Java wrapper. Builder of this round: a Claude agent on Fable 5.2 (brief 5 chose it because
five reviews in a row found hand-off races), working natively on AresOS (Fedora-based, Python 3.14, systemd 259),
not in WSL. Brief: `briefs/23-review-fixes-5.md`. Only the supervisor, the wrapper and their tests changed: no
image build input and no VM check, so no CI run was started (the merge of main below changes `os/build.sh`).

**The rule this round is built on** (brief 5): restart by itself only when the end is *certain* to be an ordinary
crash. Everything uncertain latches recovery and waits for `retry`.

**What made the earlier rounds race, and what is gone now.** Rounds 2 to 4 asked "did the wrapper stop Java, or did
something else?" and answered it from where the wrapper's code was, then from the signals it had noted. That
question has no safe answer: a SIGKILL from outside can land a moment before the wrapper's own, and the exit status
is the same. So the question is no longer asked. The wrapper reports facts only (Java's real exit status, the
signals it delivered, a reason), and the supervisor decides every end in one place, `conclude()`, from the status
alone:

| Java's end, as its wrapper saw it | Outcome |
|---|---|
| any status but 0 and SIGKILL (also 143 after the wrapper's own SIGTERM) | a crash or failed start: counted once, restarted after its backoff |
| Java never ran (the wrapper says why) | a failed start: counted once, restarted |
| exit 0 | his quit: never counted, never restarted |
| SIGKILL, whoever sent it | `killed`: latched, never counted, never restarted |
| no report and no record | `killed`, saved as unresolved until a late report or the record explains it |

`stopped_by_wrapper` (one copy in each program, kept equal by a test) and the `stopped` flag in reports, records
and four supervisor functions are deleted. The two programs now share one format for "how Java ended"
(`end_report()` in the wrapper, `End` and `end_facts()` in the supervisor) and nothing they have to agree on.

1. **Confirmed sends only (blocking finding 1).**
   - The wrapper's `send()` looks at Java without reaping it (`waitid` with `WNOWAIT`), sends with `kill`, and
     notes the signal only when Java had not ended and the kernel took it. A skipped or failed send is never
     noted; `stop()` has no early return. The forwarded signals (SIGTERM from Prism) go the same way.
   - The supervisor never restarts a SIGKILLed Java, whoever sent the signal (the table). So REVIEW-5's case, an
     outside SIGKILL after the stop window and before the wrapper's own, latches: by the report and by the record.
     So does the one case no bookkeeping can settle: the outside SIGKILL lands between the wrapper's look and its
     `kill`, and the wrapper truthfully notes a SIGKILL that reached a Java already dead.
   - Tests: `WrapperTest.test_a_kill_from_outside_at_each_point_of_the_wrappers_stop` (the real wrapper, hooks at
     four exact points, no sleeps: before its SIGTERM, between its look and its SIGTERM, after the stop window and
     before its SIGKILL, between its last look and its SIGKILL; report and record say the same),
     `test_a_signal_counts_as_sent_only_when_a_running_java_took_it` (running, ended but not reaped, reaped);
     `RestartPolicyTest.test_a_sigkilled_java_never_restarts_whoever_sent_the_signal` (12 cases) and
     `test_no_decision_hangs_on_the_signals_the_wrapper_sent` (9 statuses by 4 signal sets); through the real loop
     and wrapper `LoopTest.test_a_kill_from_outside_before_the_wrappers_sigkill_latches`,
     `..._latches_by_the_record_alone`, `test_a_kill_from_outside_right_after_the_wrappers_last_look_latches`, and
     `test_a_lost_hand_off_with_a_java_that_ignores_sigterm` (now latched, see JUDGMENT-CALL 10).
2. **Exit 0 is his quit whenever it comes (finding 2).** `conclude()` no longer asks whether the PID had been
   accepted. Tests: `RestartPolicyTest.test_exit_zero_is_his_quit_whenever_it_comes` (before the PID was delivered,
   after a refusal, during a lost hand-off by report and by record, with a lost answer after acceptance: no failure
   counted, no restart after an hour), `LoopTest.test_a_java_that_exits_zero_before_the_hand_off_is_his_quit` (real
   loop and wrapper).
3. **Facts survive a reboot (finding 3).**
   - The exit record moved from `$XDG_RUNTIME_DIR/aresos/` to `~/.local/state/aresos/desktop-exit.json`. The
     supervisor names the file and the session in its `jvm_start` reply; the wrapper writes it (temporary file,
     fsync, rename, fsync of the folder) before it reports. It carries the launch, the session, the PID and start
     time, the status, the confirmed signals and the reason. Without a usable file name the wrapper refuses to
     start Java.
   - After a reboot the supervisor restores the unresolved launch as before and now finds its record: a kill stays
     latched, a crash is counted once and the latch lifted, his quit lifts the latch. What the old session would
     have done next is not carried over: the record's session differs from the new one, so the new session starts
     its hub (`new_session()`), and only a latch holds it back (call 12).
   - Tests: `RestartPolicyTest.test_an_explanation_written_before_a_reboot_is_applied_after_it` (crash, the
     wrapper's SIGTERM, quit, kill, kill with the wrapper's SIGKILL; exactly once over a third supervisor),
     `test_a_reboot_keeps_a_latch_nothing_explains`, `test_his_quit_holds_in_its_own_session_only`;
     `WrapperTest.test_the_exit_record_is_written_durably`, `test_without_a_place_for_the_exit_record_java_never_
     runs`; `LoopTest.test_an_explanation_the_wrapper_could_not_deliver_survives_a_reboot` (REVIEW-5's own order
     through the real loop and wrapper: latched as unexplained, the supervisor stops, the wrapper writes and finds
     nobody to tell, the runtime folder is cleared, the next supervisor counts one failed start and starts the hub).
4. **A model that cannot agree with the code by accident (finding 4).** `HandOffRun` and `HandOffModelTest` are
   rewritten.
   - **Separate events.** The wrapper's steps are single events: its wait for the answer times out; one look and
     SIGTERM (Java exits 143, or ignores it, or is SIGKILLed from outside right after the look); the stop window
     and SIGKILL (again with the outside kill right after the look); the record write; the report; its death.
     Between any two of them the supervisor can handle `jvm_started` (answered or not), lose the connection,
     restart, let 40 s pass, and Java can quit, crash or be killed.
   - **The real code at each step.** The model talks to the real supervisor through the real `Loop.handle`, in the
     JSON lines the wrapper sends. The wrapper's steps are its real `send()` (the module's `os` is replaced, so
     `waitid` and `kill` act on the model's Java), `end_report()` and `write_exit()`.
   - **A reboot** after every order: every process is gone, the whole runtime folder is cleared, a new session
     starts.
   - **Its own ledger.** The model writes down what ended Java (itself, the wrapper's SIGTERM or SIGKILL, a kill
     from outside, the wrapper's death, the reboot) and whether the wrapper wrote that down. The expected outcome
     comes from this ledger alone (`truth()`); no return value of the supervisor and no rule of the wrapper is in
     it. The supervisor's answers are used only as the wrapper uses them (to go on or to stop Java), and its
     latch right before a reboot is compared with the one after it.
   - **Invariants.** At every step: nothing is counted twice; **an end that is not a certain crash is never
     counted and never restarts** (new; it contains round 4's "a kill never restarts" and "his quit never
     restarts"); a signal is noted exactly when Java had not ended at the wrapper's look; no supervisor latches a
     start while its wrapper is inside the stop-and-report window after a seen loss. Settled: a certain crash is
     counted exactly once and nothing stays latched; his quit leaves nothing; a kill or an end nobody wrote down
     is latched. After a reboot: a latch survives unless the record explains it; a crash is counted exactly once
     if a supervisor knew of it or had latched it; the new session starts its hub exactly once unless latched, so
     his old quit never keeps it closed.
   - **Size.** 41,984 orders (every order that can happen, with one supervisor restart, one 40 s stretch,
     and a loss early or 25 s into the authorization window), each run twice, without and with a reboot: about
     80 s natively. The test also asserts that the orders reach every kind of end, the restart and both
     sides of a reboot, so it cannot pass by losing its orders.
5. **Simplify (item 5).** Done inside the current protocol: the question the two programs raced on is removed
   (above), and both report channels carry one format. **A smaller protocol, proposed and not built:**
   - Run Java as a transient systemd *service* of the user manager instead of as the wrapper's child
     (`systemd-run --user --wait --pipe --service-type=exec --unit=aresos-game-<launch>.service
     -p MemoryHigh=5G … java`). systemd is then the one witness of Java's end. The supervisor reads `Result`,
     `ExecMainCode` and `ExecMainStatus` whenever it wants, also after its own restart. There is no PID hand-off,
     no report that can be lost, no exit record, and a memory kill is named by systemd (`Result=oom-kill`).
   - The brief's example, reading the *scope's* result and cgroup events, does not get there: systemd keeps no
     exit status for a scope, so quit and crash would still need the wrapper's report. It would add a second
     witness for memory kills and remove no message. Not added: a SIGKILL already latches without it.
   - Cost of the service: Java is no longer Prism's grandchild, so Prism's Kill button, its log window and the
     "launch" line it writes to Java's stdin must be tried with the real Prism; the desktop lock can no longer be
     inherited; the nonce must reach the service without appearing on a command line (`--setenv=NAME`); the
     hand-off's tests would need a real user manager, which the hosted runner lacks, so the proof moves into the
     VM; `desktop_jvm` in the VM changes, with a check build. About a rewrite of the wrapper, of the supervisor's
     JVM tracking and of their tests: several times this round, and it cannot be proven without CI and a real
     game.
   - Advice: not now. Take it up if a further review still finds hand-off defects that matter under the owner's
     bar, or with package 25 (clean shutdown), which has to change how the game is stopped anyway.

### Known limits (under the owner's review bar of 2026-11-11)

None of these can loop under memory pressure, touch the world, or make recovery unreachable. Each costs at most
a `retry` or one crash in the count.

1. **A start the wrapper had to SIGKILL latches.** The message says so (JUDGMENT-CALL 10). Costs a `retry`.
2. **A crash recorded right before a reboot** that no supervisor had counted or latched before the reboot is not
   counted (one too few). The new session starts the hub once, as after any boot.
3. **A start whose Java never ran** (it could not be executed, for example for lack of memory) still counts as a
   failed start and restarts, at most twice before the latch. Unchanged, and not a kill of a running game.
4. **A SIGTERM from outside** (exit 143 or signal 15 without the wrapper's stop) counts as a crash and restarts.
   Unchanged. At the end of a session this can count one crash, if the supervisor still runs when Java is stopped;
   the next session ignores the pending restart, and 30 healthy minutes clear the count. Package 25 (clean
   shutdown) is the place for it.
5. **The noted signals can include one that reached a Java already dead** (between the wrapper's look and its
   `kill`). That gap cannot be closed from outside the kernel, which is why nothing is decided from them.
6. **No record and no report** (a full disk and a dead supervisor at once): the end is unexplained and latches.
7. **A supervisor that stalls for more than 10 s** without closing the connection: the wrapper gives up, stops
   Java and reports. If that passes 30 s after the authorization, the start is latched first and the report then
   replaces the latch with one failed start (the recovery window opens and closes again).
8. **A power cut** (not a reboot): the wrapper syncs its record and its folder; the supervisor syncs its state file
   but not the folder (`write_atomic`, unchanged), so a latch written in the last seconds can be lost. The hub
   then starts once at the next boot.
9. **The model plays the wrapper's order of steps itself.** It calls the wrapper's real functions at each step but
   does not run `main()`. That the real wrapper takes these steps in this order is shown by the real-wrapper and
   real-loop tests, with hooks at the same points. Each order has at most one supervisor restart, one 40 s
   stretch and one reboot.

### Regression proof (each fix reverted alone)

Each fix was put back alone on a copy of the tree at `2a658f5b` (interfaces kept), then the model and that fix's
tests ran. The model names its shortest failing orders (letters: `HandOffRun`'s docstring).

| Fix reverted | Model | Its own tests |
|---|---|---|
| 1, wrapper: a signal is noted before it is sent, sent or not (round 4) | 1,188 failing orders, e.g. `RkS` (the supervisor restarts, Java is killed from outside, then the wrapper's SIGTERM step): `a signal was noted that no running Java took` | The real wrapper at REVIEW-5's point: `('jvm_failed', -9, [15, 9]) != ('jvm_failed', -9, [15])`; the record through the real loop the same; `send()` to a reaped Java: `True is not false`. The two outcome tests still pass: no decision hangs on the notes. |
| 1, supervisor: a SIGKILL the wrapper sent is its own stop, counted and restarted (round 4) | 2,832 failing orders, e.g. `RseF` (restart, Java ignores SIGTERM, a SIGKILL from outside right after the wrapper's last look, the record): `counted or restarted an end that is not a certain crash` | `('STARTING', 'restarting', False) != ('RECOVERY', 'killed', True)` in four policy tests; the real loop restarts in both real-loop tests |
| 2: exit 0 is his quit only after the PID was accepted (round 4) | 2,989 failing orders, e.g. `qF` (Java exits 0 before the hand-off, the wrapper records it): counted and restarted | `('STARTING', 'restarting', False) != ('RECOVERY', 'quit', False)`; the real loop runs into `RECOVERY crashes` |
| 3: the exit record in the runtime folder again (round 4) | 3,974 failing orders, e.g. `TcFZ` (latched after 30 s, Java crashes, the record is written, reboot): still latched | `('RECOVERY', 'killed', True) != ('STARTING', None, False)`; the real loop stays in `RECOVERY killed` after the reboot |
| 3: the old session's decision is carried into the new one | 1,828 failing orders, e.g. `TqFZ`: his old quit keeps the new session's hub closed | `('RECOVERY', 'quit', False) != ('STARTING', None, False)`; a crash waits for a backoff of the old session |
| round 4's fix 2 put back (an unresolved end is not restored) | 7,619 failing orders, e.g. `TRSF` | both round 4 tests, and this round's reboot tests |
| round 4's fix 3 put back (two deadlines, the earliest wins) | 52 failing orders, all with the loss 25 s into the window, e.g. `B`: `latched while the wrapper may still be stopping Java` | `('RECOVERY', True) != ('STARTING', False)` |

No fix's tests passed with that fix reverted. Output: `runs/native-review-fixes-5/revert-proof.txt` (the script is
not committed).

### Merge of main

The integrator asked for the head that will merge: `origin/main` (`1b39db6b`: packages 27 and 27b and the state
commits since `bbe167e5`) is merged into the branch as `3fd0bc1c`, a merge commit, no rebase.

- **Conflicts: none.** Both sides had changed four files, and git merged each by itself: `os/build.sh` (main adds
  four lines: owner and mode of `/etc/sudoers.d`), `os/ci/image-checks.sh` (one line), `os/tests/test_aresos_shell.py`
  (three lines) and `os/tests/test_everyday_account.py` (15 lines). Their tests pass on the merged tree
  (`test_aresos_shell` 74, `test_everyday_account` 34, `test_build_tools` 3).
- **Image build inputs changed through the merge: yes.** `os/build.sh` and `os/ci/image-checks.sh` as above, and
  `.github/workflows/os-image.yml` (175 lines). `os/Containerfile`, `os/minecraft/` (the pins, the mod jar pin
  included) and `mod/` did not change through the merge. So a check build is the integrator's to start.
- **Package 27's bound files:** none of this branch's 71 changed files is among the 250 paths in
  `os/manifest/ci/27/source-bindings.json`; `test_checkout_sources` passes (5 tests). `os/manifest/ci/16/pending-
  rebind.json` was not touched.

### Checks of this round

Natively on AresOS itself (Fedora-based, Linux 7.2, Python 3.14.8, systemd 259), the owner's running laptop, not
WSL. Never two suites at once; temporary files in a work folder outside the repo, removed afterwards.

- **Targeted, from the worktree:** `test_aresos_desktop` 144 tests OK, 1 skipped, 194 s, with
  `-W error::ResourceWarning` (before this round, same machine: 132 OK, 1 skipped, 142 s; the model is about 80 s of
  the difference). The skip is the real-scope test (PLAN-GAP below). After the merge: `test_aresos_shell` 74 OK,
  `test_everyday_account` 34 OK, `test_build_tools` 3 OK, `test_checkout_sources` 5 OK.
- **Full suite: RUNNING when this was written (hand-over note, replaced by the numbers when both runs are done).**
  A detached driver (`/var/home/ares/pkg23-work/suite.sh`, logs in `/var/home/ares/pkg23-work/suite/`) runs plain and
  then `-B` from a full clone of `88ac79fd`; it writes `suite/DONE` and removes its clone at the end. Left to do:
  classify both logs (`classify.py` next to it), put the numbers here, remove the work folder.
  A first plain run from a shallow clone of `3fd0bc1c` gave `Ran 1087 tests`, `FAILED (failures=101, errors=32,
  skipped=1)`, none of it in package 23's tests: `test_owner_update` 99 (its real entry expects a host without
  `rpm-ostree`; on AresOS it goes one step further and stops at `Read failed: rpm-ostree status --json`),
  `test_inherited_homebrew` 8 and `test_sysusers` 2 (need root; the known WSL failures), 12 from Python 3.14
  (`glob()` stand-ins without `case_sensitive`), 3 owner-tool checks that want a root-owned folder, and 9 only
  because the clone was shallow (hence the full clone now). `test_greeter` (3 known WSL failures) passes here.
- **How the full suite ran here.** From a fresh `git clone --depth 1` of the pushed branch, `python3 -m unittest
  discover -s os/tests -v`, plain and then `-B`, one at a time, under `nice -n 10`, detached (`setsid`, stdin from
  `/dev/null`), with at least 4.5 GB available before each. Because this is a live machine, the suite also ran under
  `setpriv --no-new-privs` (no test can become root: `sudo` and `pkexec` cannot elevate) and in a clean environment
  (`env -i`): a scratch `HOME` and `XDG_RUNTIME_DIR`, no display, no session bus, and a system bus address that
  leads nowhere. Tests that need root or a user manager therefore fail or skip here by design.
- CI: none started by this round.

### Not proven

- A real Prism and Minecraft, and a real systemd-oomd kill: as before, tests kill by hand.
- The VM's `desktop_jvm` check has not run against this round's wrapper (no CI run; the check itself is unchanged).
- `WrapperTest.test_the_real_jvm_runs_in_its_own_scope_with_the_memory_target` is skipped natively (see the
  checks): the changed wrapper was not run against a real user manager in this round.

### PLAN-GAP and judgment calls of this round

- **JUDGMENT-CALL 10 is widened** (its text below, in the JUDGMENT-CALL section): a SIGKILL latches whoever sent
  it; exit 0 is his quit also before the hand-off; a reboot does not carry the old session's quit or restart.
  Owner-facing in one rare case (known limit 1). The integrator decides whether it goes back to the owner.
- **PLAN-GAP: the real-scope test cannot run on AresOS itself.** With systemd 259, `systemd-run --user` finds the
  user manager through `$XDG_RUNTIME_DIR` only; the test gives the wrapper a temporary runtime folder and the real
  bus address, which was enough for WSL's systemd 255. So it skips here, as on the hosted runner. Putting
  `/usr/bin/env XDG_RUNTIME_DIR=/run/user/<uid>` in front of the scope command in that test would make it run. Not
  done in this round: it then creates a real scope in the owner's running session, which this round's rules for
  the live machine rule out. The image's own session is not affected (there the wrapper has the real folder, and
  the VM check passed on it).
- **PLAN-GAP: "no CI" and the merge.** This round's own changes need no CI by the brief's rule, but the merge of
  main changes build inputs (above), and the VM's `desktop_jvm` has not seen this round's wrapper.
- **Seen, not changed (outside the brief):** known limits 3 and 4 (a start whose Java never ran, and a SIGTERM
  from outside, still restart); the message text `failed_start` in `message()` is not used by any state.
- **Tests removed with what they tested:** `test_both_programs_decide_stopped_by_the_same_rule` and
  `test_a_kill_after_the_wrappers_check_is_not_its_stop` tested `stopped_by_wrapper`, which no longer exists.
  Their cases live on in `test_no_decision_hangs_on_the_signals_the_wrapper_sent` (every status with every set of
  signals) and the outside-kill tests. Two expectations changed with JUDGMENT-CALL 10: a Java the wrapper had to
  SIGKILL now latches (`test_a_lost_hand_off_with_a_java_that_ignores_sigterm`, one case each in two policy tests).

**What a reviewer should look at hardest:** `Supervisor.conclude()` (the table above is all of it), and in it the
one new path, `earlier` and `new_session()`: a new session that settles an old launch and then starts its hub;
`reconcile()` (it lifts a latch only for the unresolved launch and only a `killed` one); the wrapper's `ended()`
and `send()` with the signal handler that now calls them (nothing reaps Java except the wrapper's own `wait`);
and the model's `truth()` and `enabled()`: whether an order that matters cannot be played (two supervisor
restarts, or a stalled supervisor with several queued messages, are not in it).

## Review fixes 4 (REVIEW-4, 2026-11-11)

REVIEW-4 (Codex gpt-6.1-sol, high, on `8420eba2`): 1 blocking, 2 should-fix, all at the hand-off between the
supervisor and the Java wrapper, the place rounds 2 and 3 also patched. This round settles the hand-off by
construction and checks it over every order of events at the race points. No image build input or VM check
changed, so no CI run.

**Status at hand-back:** code, tests, the model and the revert proof are pushed. Not yet run: the full suite from a
fresh clone, because C: had only about 0.35 GB free and a clone is about 500 MB in WSL's disk image. The desktop and
helper modules ran (below).

1. **Each end is classified from facts (blocking finding 1).**
   - The wrapper's `stop(child, sent)` records every signal before it sends it. "Stopped by the wrapper" holds only
     when Java's real end matches a signal it sent: Java died of it, or exited 143 after its SIGTERM
     (`stopped_by_wrapper`, the same rule in both programs; a test keeps them equal over every status and signal
     set). The report and the exit record carry Java's real status, the signals sent and the derived flag, and the
     supervisor derives the flag again from those facts.
   - One `conclude()` decides every end, before or after the hand-off: stopped by the wrapper or a failed start
     (counted once), a SIGKILL nobody sent (`killed`, latched, never counted or restarted), exit 0 after acceptance
     (his quit), any other end (a crash, counted once), or no explanation at all (`killed`, saved as unresolved).
   - So a kill or an exit between the wrapper's check and its signal (REVIEW-4's case), or at any other point, is
     classified by what happened.
2. **Unresolved ends are persisted (finding 2).** An unexplained end is saved as `unresolved` (launch, PID, start
   time, whether it was accepted) in the same write as the accounting. A restarted supervisor restores it; a
   matching late `jvm_failed`, a late `jvm_exited`, or the exit record (checked every 5 s while unresolved) settles
   it exactly once: an explained end replaces the latch with its real outcome, and a kill confirms it. The wrapper
   also retries `jvm_exited` on a new connection when the first one is gone.
3. **One deadline rule (finding 3).** Once a lost hand-off is seen (the wrapper's connection closed, or a restarted
   supervisor finds a start in flight), the wrapper gets its whole stop-and-report window (`LOST_HANDOFF_WAIT`,
   20 s) from that moment, past the 30 s authorization limit. Without a seen loss the 30 s limit stands.

**The model test** (`HandOffModelTest.test_every_order_keeps_the_invariants`) drives the real supervisor (fake
clock and runner) and the wrapper's real `stop()` and `stopped_by_wrapper()` through every order of every subset of
these events: the supervisor handles `jvm_started`, the wrapper gets the answer, the connection breaks, Java ends
by itself (exit 0, crash, SIGKILL), the supervisor restarts, the wrapper stops Java and reports (Java exits after
SIGTERM or ignores it and is SIGKILLed after the window), the wrapper dies, time passes in 5 s steps. Java may also
end right after the wrapper's own check. Losses come early or late (25 s) in the authorization window. That is about
6,000 runs, in a few seconds. For every run it asserts, against the model's own record of what happened:
- a kill the wrapper did not send never restarts and counts nothing;
- his quit never restarts;
- a crash or failed start counts exactly once, and nothing is counted twice at any point;
- nothing stays latched when a full explanation exists;
- no supervisor latches a start while its wrapper is still inside the stop-and-report window after a seen loss;
- after a normal reboot (a new session) the hub starts, unless a kill latch holds.
Building it found one more gap, fixed above: a game's own exit report or record arriving after its end had been
latched as unexplained (for example across a supervisor restart) was never read.

**Targeted tests:** `RestartPolicyTest.test_a_kill_after_the_wrappers_check_is_not_its_stop` (the real `stop()` with
Java ending right after its check, then the accepted-JVM case: latched, nothing counted, no restart),
`test_both_programs_decide_stopped_by_the_same_rule`, `test_an_unresolved_end_survives_a_supervisor_restart`
(report, record, kill; exactly once over a third start), `test_a_loss_late_in_the_authorization_window_gets_the_
whole_wait`. With the real wrapper, run in the test process so a hook acts at the exact point, no sleeps:
`WrapperTest.test_a_kill_between_the_wrappers_check_and_its_signal_is_reported_as_a_kill`; through the real loop
and real wrapper: `LoopTest.test_a_kill_between_the_wrappers_check_and_its_signal_latches` and
`test_an_unexplained_end_is_settled_after_a_supervisor_restart` (events gate each step).

### Regression proof (each fix reverted alone)

| Fix reverted | Model | Its own tests |
|---|---|---|
| 1: "stopped" again means "the wrapper's stop() ran" (both programs) | 232 failing orders, e.g. Java exits 0 right after the wrapper's check: `(1, 2) != (0, 1)` (a quit counted as a failure, and restarted) | the real `stop()` cases `True is not False`; the accepted-JVM kill `('STARTING', 'restarting', False) != ('RECOVERY', 'killed', True)`; the real wrapper reports `stopped True` for a kill; the real loop does not latch |
| 2: nothing restored after a supervisor restart | 536 failing orders, e.g. `TRW` (a crash left latched) | all three restart cases; the real loop stays in `RECOVERY killed` |
| 3: both deadlines, the earliest wins | 138 failing orders, e.g. a loss 25 s after authorization: `latched while the wrapper may still be stopping Java` | `('RECOVERY', True) != ('STARTING', False)` |

Output: `runs/wsl-review-fixes-4/revert-proof.txt`. Each run used a copy of the tree without `os/manifest` (400 MB,
not read by these tests), removed right after.

### Checks of this round

- WSL (Ubuntu 24.04, Python 3.12), never in parallel with another suite, at 4.5 GB or more available, under
  `setsid` with stdin from `/dev/null`: `test_aresos_desktop` 132 tests OK (the model test about 10 s),
  `test_aresos_shell` 74 OK.
- **Not run yet: the full suite from a fresh clone** (disk, see the status above).
- CI: none.

## Review fixes 3 (REVIEW-3, 2026-11-10)

REVIEW-3 (Codex gpt-6-astra, high, on `e69b16a0`) found all 9 REVIEW-2 findings fixed and three problems left at
the hand-off's edges: 1 blocking, 2 should-fix. Each fix is at its cause, with a test that fails with only that fix
reverted (below). Only the supervisor, the wrapper and their tests changed: no image build input and no VM check,
so no CI run.

1. **Blocking: a SIGKILL after the PID was accepted latches, never restarts.**
   - Cause: when the supervisor accepted `jvm_started` but its answer was lost, and Java was SIGKILLed before the
     wrapper acted on the loss, the wrapper's report (`status=-9`) set `stopped_reason` anyway. `finish_jvm()`
     preferred that reason, so the kill restarted as a plain crash.
   - Fix: the wrapper's `jvm_failed` always says who ended Java (`stopped`), and sends the real status whenever it
     knows it; the exit record carries the same flag. For an accepted JVM the supervisor uses the reason only when
     the wrapper stopped Java; otherwise Java's own status is its exit status, and a SIGKILL latches `killed` like
     any game's end.
   - Tests: `RestartPolicyTest.test_a_sigkill_after_acceptance_with_a_lost_answer_latches` (by the report and by
     the exit record: latched, nothing counted, never restarted); `WrapperTest.test_java_killed_after_a_lost_answer_
     reports_its_own_end` (the real wrapper: no answer, Java SIGKILLed, reported with `status -9, stopped false`);
     `LoopTest.test_a_kill_after_acceptance_with_a_lost_answer_latches` (the real loop accepts the PID, then drops the
     connection while Java is SIGKILLed).
2. **The supervisor's wait covers the wrapper's stop; a late report still counts.**
   - Cause: after the connection closed before acceptance, the supervisor waited 2 s, but the wrapper may take 10 s
     to stop Java (SIGTERM, then SIGKILL) before reporting. A slow stop became a false kill latch, and its report
     was then dropped.
   - Fix: the supervisor waits `LOST_HANDOFF_WAIT` = the wrapper's `STOP_WAIT` (10 s) + its `REPORT_TIMEOUT` (5 s) +
     5 s margin = 20 s (still below the 30 s hand-off limit). A test keeps the supervisor's copies of the wrapper's
     numbers equal. If a report still comes after an unexplained latch, it is applied: an explained end replaces
     the latch with one failed start (counted once); a kill stays latched. A JVM that the wrapper SIGKILLed after
     its stop window counts as stopped by the wrapper, not as a kill.
   - Tests: `RestartPolicyTest.test_the_wait_for_a_lost_hand_off_covers_the_wrappers_stop`,
     `test_a_late_report_still_explains_an_unexplained_start`; `WrapperTest.test_java_that_ignores_sigterm_is_killed_
     and_reported_as_stopped`; through the real loop `LoopTest.test_a_lost_hand_off_with_a_java_that_delays_sigterm`
     (Java stops 3 s after SIGTERM) and `test_a_lost_hand_off_with_a_java_that_ignores_sigterm` (killed after
     10 s): each ends with Java gone, the lock free and exactly one failed start, not latched.
3. **A gap in pressure sampling starts the clear minute again.**
   - Fix: a gap between two samples longer than `PRESSURE_GAP` (the 5 s cadence + 5 s tolerance) resets the
     interval: unobserved time is unknown, not clear.
   - Test: `RestartPolicyTest.test_a_gap_in_sampling_starts_the_clear_minute_again` (70 s without sampling ticks,
     then Retry is refused; after a sampled minute it works).

### Regression proof (each fix reverted alone)

| Finding (fix reverted) | Its tests | What fails |
|---|---|---|
| 1 (any report after acceptance sets the stopped reason) | `test_a_sigkill_after_acceptance_with_a_lost_answer_latches`, the real-loop test | The report case: `('STARTING', 'restarting', False) != ('RECOVERY', 'killed', True)`, the kill restarts as a crash. The real loop runs into `RECOVERY crashes` after three restarts. (The exit-record case passes either way: that path already used the status.) |
| 2 (the old 2 s wait, late reports dropped) | all four | `2.0 not greater than 15.0`; a late explained report leaves `('RECOVERY', 'killed', True)`; both real-loop tests (Java delays or ignores SIGTERM) time out in `RECOVERY killed`. |
| 3 (no gap check) | `test_a_gap_in_sampling_starts_the_clear_minute_again` | `True is not false`: Retry is allowed right after 70 unobserved seconds. |

No fix's tests passed with that fix reverted. Output: `runs/wsl-review-fixes-3/revert-proof.txt`.

### Checks of this round

- WSL (Ubuntu 24.04, Python 3.12), never in parallel with package 27's suites (a slot script waited for theirs to
  end), under `setsid` with stdin from `/dev/null`:
  - From the worktree: `test_aresos_desktop` 124 tests OK, `test_aresos_shell` 74 OK.
  - Full suite from a fresh `git clone --depth 1` of `pkg/23-minecraft-starts` at `7cb21e76`, plain and `-B`: in
    both, exactly the known WSL-only failures that also fail on main (`test_greeter` 3, `test_inherited_homebrew`
    8, `test_sysusers` 2) and nothing else. The clone and its logs were removed right after (the laptop's disk had
    about 2 GB free), so the `Ran` line was not kept; the same commit's run from the worktree ran 987 tests. That
    worktree run is not used as evidence: on the Windows-mounted folder, Linux file modes don't hold, so 150 owner-
    tool tests fail there for that reason alone.
  - Memory: the machine had 3.3 to 4.7 GB available (the brief asks for 5 GB). WSL's own page cache counts as used
    on Windows, and inside WSL about 7 GB was available. The runs waited for no other suite and at least 4.5 GB.
- CI: none. Only the supervisor, the wrapper and their tests changed; the image build and the VM checks are as in
  run 42865819198.

## Review fixes 2 (REVIEW-2, 2026-11-10)

REVIEW-2 (Codex gpt-6-astra, high, on `7ec26b84`) found 1 blocking and 8 should-fix problems. It agrees with the
updated JUDGMENT-CALL 10, which the owner accepted (board #170: "Yes"); these fixes complete it and change nothing
in it. Each fix is at its cause. Under "Regression proof" each finding's tests run with only that fix reverted
(interfaces kept, so shared setup still works), and the failing assertion is recorded. The mod is unchanged, so no
Gradle run was needed and the jar pin stays.

1. **Blocking: a kill before the PID hand-off latches like a kill after it.**
   - Cause: between authorizing a JVM and accepting its PID, a dead Java or a dead wrapper ended as `jvm_failed` or
     "wrapper gone", and both counted as a plain crash with an automatic restart.
   - Fix: the wrapper reports Java's own exit status when Java ends before the hand-off (also when the supervisor
     refused it because it had already died), and writes it to `desktop-exit.json` with the launch ID. The
     supervisor classifies every unreported start with the same rule as a game's end (`start_ended`): a SIGKILL,
     or an end nobody explains (the wrapper's connection closed and no report followed within 2 s, or no JVM and
     no report within the 30 s hand-off limit), latches `killed` with the scope's systemd result, uncounted and
     never restarted by itself. Only a start that failed for a stated reason (Java could not start, the scope was
     unusable, the supervisor refused it, Java exited by itself) counts as a failed start. A supervisor restart
     accounts for a start the previous one authorized: by the wrapper's failure record, or as unexplained, or it
     waits for a wrapper that still holds the lock.
   - Tests: `RestartPolicyTest.test_a_death_before_the_hand_off_latches_like_a_kill` (Java killed, wrapper gone,
     hand-off timeout, killed by the record), `test_a_failed_start_is_reported_and_counted_never_left_open` (what
     still counts), `AdoptionTest.test_a_start_authorized_before_a_supervisor_restart_is_accounted_for`,
     `WrapperTest.test_java_killed_before_the_hand_off_is_reported_with_its_status`, and through the real loop and
     wrapper `LoopTest.test_java_killed_before_the_hand_off_latches` and
     `test_java_and_wrapper_killed_before_the_hand_off_latch`: a stand-in for `systemd-run` SIGKILLs Java (and
     the wrapper) right after authorization, before the PID is accepted. Recovery latches `killed`, there is one
     launch, and nothing is counted.
2. **Retry needs a whole minute of clear memory pressure.**
   - Cause: one `avg60` reading at or below 10 % allowed Retry, and an unreadable reading allowed it too.
   - Fix: while the `killed` latch holds, the supervisor samples PSI `some avg10` every 5 s. Any sample above 10 %,
     and any unreadable one, starts the minute again; Retry works only after 60 s of clear samples without a
     break, and its message says how far along that is. The interval lives only in the running supervisor, so a
     restarted supervisor starts the minute again and never skips it.
   - Tests: `RestartPolicyTest.test_a_kill_waits_for_a_whole_clear_minute_before_retry` (the old test that dropped
     pressure from 42 to 3 without time passing is gone: 3 % right after 42 % is refused; a spike and an
     unreadable value each restart the minute), `test_a_supervisor_restart_never_skips_the_clear_minute`.
3. **A lost hand-off never leaves an untracked JVM.**
   - Cause: if the connection broke during `jvm_started`, the wrapper only printed a message and waited for Java,
     which then ran untracked, holding the desktop lock.
   - Fix: the wrapper aborts the unaccepted start. It stops Java (SIGTERM, then SIGKILL after 10 s), records the
     failed start, and reports it on a new connection, naming the launch (the supervisor accepts `jvm_failed` from
     a new connection only for the launch it is waiting for, like `jvm_exited`). If the supervisor had already
     accepted the PID and only the answer was lost, the wrapper's report or record marks the JVM as stopped by
     its wrapper, so its end is a failed start, not his quit and not a kill.
   - Tests: `WrapperTest.test_a_lost_hand_off_stops_java_and_reports_on_a_new_connection` (a real closure during
     `jvm_started` with Java alive: Java is gone, the lock is free, the report comes on a second connection),
     `LoopTest.test_a_lost_hand_off_never_leaves_java_running` (the real loop drops the wrapper's connection while
     handling `jvm_started`), `RestartPolicyTest.test_a_lost_hand_off_answer_after_acceptance_is_a_failed_start`.
4. **The decision after an end survives a supervisor restart.**
   - Cause: only `accounted` was saved. After his quit, a restarted supervisor found nothing to adopt or account
     for and started Minecraft; a pending crash restart lost its deadline.
   - Fix: the state file keeps the session's disposition next to `accounted`, written in the same save: a stop
     that waits for his retry (his quit, the setup ends, Prism failures, sign-in), or a pending restart with its
     wall-clock deadline (capped at the longest backoff). A restarted supervisor restores it and counts nothing
     again. It is bound to the session's instance ID: a new session (after a reboot) starts the hub as before;
     only the crash latch outlives the session (call 12).
   - Tests: `AdoptionTest.test_the_decision_after_an_end_survives_supervisor_restarts` (his quit across two
     restarts, a pending backoff that keeps its deadline, a new session that starts normally), and
     `test_a_game_that_ended_while_no_supervisor_ran_is_accounted_for_once` now also checks the second
     supervisor's state.
5. **Exact-home data must be valid, not only present.**
   - Fix: `home.dimension` must parse as Minecraft 26.2's `Identifier` (checked in its bytecode:
     `[namespace:]path`, namespace `[a-z0-9_.-]` and not `..`, path `[a-z0-9_./-]`), and an exact home's yaw and
     pitch must be finite.
   - Tests: `WorldCheckTest.test_exact_home_data_must_be_valid_by_the_mods_codecs` (valid and malformed
     identifiers, NaN and infinite angles) and
     `RestartPolicyTest.test_malformed_exact_home_data_is_refused_before_the_start_and_at_readiness`.
6. **NBT strings are read as Java writes them.**
   - Fix: strings are decoded as Java's modified UTF-8 (`DataInput.readUTF`): NUL as `C0 80`, characters outside
     the BMP as two three-byte surrogates, joined into one character; 4-byte UTF-8 is malformed, as in Java.
   - Tests: `WorldCheckTest.test_strings_are_read_as_java_writes_them` with `fixtures/desktop-world/
     level-modified-utf8.dat`, written by the JDK's own `writeUTF` (`JavaStrings.java` next to it): a world name
     with an emoji and a string with a NUL.
7. **Corrupt compressed data is damage, not a crash.**
   - Fix: `read_saved` turns every decompression error (`zlib.error`, `EOFError`, `OSError` from `gzip`) into
     `NbtError`, so it is world damage, and a damaged `level.dat` falls back to `level.dat_old`.
   - Tests: `WorldCheckTest.test_corrupt_compressed_data_is_damage_never_a_crash`: corrupt DEFLATE, a bad header, a
     cut-off stream, a wrong checksum and truncated NBT, each separately; the fallback to a valid `level.dat_old`;
     and the supervisor's own gate ending in RECOVERY `world_damaged` instead of an exception.
8. **The focus hand-back survives late identification.**
   - Fix: the helper remembers the window that last lost focus (`keep_target`), apart from the active window. When
     Minecraft's window takes focus before it names its app ID, the editor is still the one that gets focus back.
   - Tests: `KeepForegroundTest.test_a_desktop_identified_after_it_took_focus_still_gives_focus_back`, and
     `test_late_identification_gives_the_same_result_at_every_split`, which runs the compositor's events through
     the Wayland parser split at every byte.
9. **The VM pressure check proves pressure.**
   - Fix: the pressure source prints its PID and cgroup first, then each 64 MiB it holds. The check requires that
     it ran in `aresos.slice/aresos-ci-pressure.scope`, reached at least 1 GiB, was killed by SIGKILL, and that the
     kernel log (`Killed process <pid>` or an `oom-kill` line naming the scope) or systemd-oomd's log names it, or
     its scope ended with `Result=oom-kill`. The supervisor must answer a status request within 30 s every half
     second while the pressure lasts. Then the protected processes must still be the same.
   - Tests: `PressureCheckTest` runs the real check function with stand-in sources: a launcher failure, another
     scope, a Python error at start, a source that ends by itself, a kill without OOM evidence and a supervisor that
     does not answer each fail it; real pressure passes.

### Regression proof (each fix reverted alone)

From a copy of the working tree per finding, in WSL. The script is not committed; the summary is in
`runs/wsl-review-fixes-2/revert-proof.txt`.

| Finding (fix reverted) | Its tests | What fails |
|---|---|---|
| 1, supervisor (`start_ended` counts every pre-hand-off death) | all 4 cases of `test_a_death_before_the_hand_off_latches_like_a_kill`, 2 cases of `test_a_start_authorized_before_a_supervisor_restart_is_accounted_for`, both real-loop tests | `('STARTING', 'restarting', False) != ('RECOVERY', 'killed', True)`: counted and restarted. The real loop runs into `RECOVERY crashes` after three automatic restarts. |
| 1, wrapper (no check that Java already ended) | `WrapperTest.test_java_killed_before_the_hand_off_is_reported_with_its_status` | `137 != 78`: the wrapper hands over a dead Java and exits with its status. The real-loop test still passes: the supervisor refuses the dead PID and the wrapper then reports Java's status, a second guard. |
| 2 (one clear reading allows Retry) | both | `True is not false : pressure that just dropped is not a clear minute`; after a supervisor restart, Retry is allowed at once. |
| 3, wrapper (old: print and wait for Java) | both | The wrapper test ends in `TimeoutExpired` after 60 s (the wrapper waits for the untracked Java). The real loop times out in `RECOVERY killed` while Java keeps running. |
| 3, supervisor (a lost answer after acceptance ignored) | `test_a_lost_hand_off_answer_after_acceptance_is_a_failed_start` | `('RECOVERY', 'killed', True) != ('STARTING', 'restarting', False)` |
| 4 (`restore()` removed) | both | `('STARTING', None, False) != ('RECOVERY', 'quit', False)`: Minecraft starts again after his quit; for a crash, `('STARTING', None, False) != ('STARTING', 'restarting', False)`: the backoff is skipped. |
| 5 (dimension and angles unchecked) | both | All 11 malformed cases give `'ok' != 'damaged'`; the gate test gives `('STARTING', None) != ('RECOVERY', 'world_damaged')`. |
| 6 (plain UTF-8) | `test_strings_are_read_as_java_writes_them` | `NbtError: 'utf-8' codec can't decode byte 0xed in position 8`: the JDK-written level reads as damaged. |
| 7 (no error mapping) | `test_corrupt_compressed_data_is_damage_never_a_crash` | `zlib.error: Error -3 while decompressing data: invalid block type` escapes, in `check_world` and in the supervisor's start. |
| 8 (target = the previous active window) | both | `[] != [2]`; through the parser `[] != [4278190083]` for every split after the new window's first `done` (splits 72 to 107). Earlier splits deliver the app ID in the same batch, which the old code handled. |
| 9 (old check: any nonzero exit passes) | `test_anything_short_of_proven_pressure_fails` | All six cases: `AssertionError not raised`. |

No fix's tests passed with that fix reverted. Full output: `runs/wsl-review-fixes-2/revert-proof.txt`.

### Checks of this round

- WSL (Ubuntu 24.04, Python 3.12), fresh `git clone` of `pkg/23-minecraft-starts` at `53ef1faf`, run under
  `setsid` with stdin from `/dev/null`, no other suite running: the full suite plain and `-B`, both `Ran 976
  tests`, `FAILED (failures=1, errors=12)`, exactly the known WSL-only set that also fails on main
  (`test_greeter` 3, `test_inherited_homebrew` 8, `test_sysusers` 2). `test_aresos_desktop` (113) and
  `test_aresos_shell` (74) pass, including the real user-systemd scope test and the real-loop kill and hand-off
  tests.
- The suite showed one `ResourceWarning` from the new pressure check (its output pipe stayed open); `d13e0477`
  closes it, and `PressureCheckTest` passes with `-W always::ResourceWarning`.
- Memory: Windows showed 4.6 to 4.9 GB free (WSL's page cache counts as used there; inside WSL 7.1 GB was
  available) for the focused runs and the revert proof; the full suite waited for 5.0 GB.
- CI: 42854477440 (`check_build=build` on `e159a29e`, dispatched once the mirror answered 200 at 0.3 to 2.2 MB/s)
  failed in the image build: the mod stage's `curl` does not exist in the pinned JDK image. See "Run 42854477440
  and its fix" below.
- **CI: 42865819198 (`check_build=build` on `953bf892`, with the VM boot): success.** Dispatched after the mirror
  answered 200 at 2.1 to 2.8 MB/s twice in a row. Evidence: `runs/build-42865819198/`.
  - The jar from the image's own stages: `MOD_SOURCE 953bf892… dc88704b…` (the fetched archive),
    `MOD_JAR_BUILT 8b04c511…65386743 from 953bf892…` and `MOD_JAR_PINNED 8b04c511…`: the same bytes as the pin, so
    no `check_build=resolve` was needed. `IMAGE_CHECKS_PASSED`, `POLKIT_CHECK_PASSED`, `CHECK_BUILD_PASSED`, the
    UEFI VM pass and `CHECK_BUILD_VM_PASSED`.
  - `memory_protection` (review 1, finding 9): `memory.low` 1073741824 on `user.slice`, `user-1001.slice` and
    `session-1.scope` (the drop-ins apply to logind's session scope); `user.oomd_avoid=1` on the session scope;
    systemd-oomd active. labwc, the keeper, the supervisor and the recovery terminal all run in `session-1.scope`.
  - `desktop_jvm` (review 1, findings 1 and 4): the image's real Java 25, started through the real wrapper from
    outside any desktop scope, ran in `user@1001.service/aresos.slice/aresos-game-<launch>.scope` with
    `memory.high` 5368709120. After `systemctl --user kill --signal=SIGKILL` of that scope: wrapper exit 137, the
    supervisor in RECOVERY `killed`, latched, consecutive 0, no JVM 12 s later.
  - `memory_pressure` (review 2, finding 9): the source ran in `aresos.slice/aresos-ci-pressure.scope` (PID
    2947), reached 5376 MiB and exited 137. The kernel's global OOM killer logged `oom-kill:...task_memcg=/user.
    slice/user-1001.slice/user@1001.service/aresos.slice/aresos-ci-pressure.scope,task=python3,pid=2947` and
    `Out of memory: Killed process 2947 (python3)`, and the scope ended with `Result=oom-kill`. The supervisor
    answered all 24 status requests during the pressure (slowest 2.2 s). labwc, the keeper, the supervisor and the
    recovery terminal kept their PIDs.

### Run 42854477440 and its fix

The first real image build through review fixes 1's `mod` stage stopped there:

```
[2/3] STEP 4/4: RUN bash /tmp/aresos-mod/build.sh mod "$ARESOS_SOURCE_REVISION" /out
/tmp/aresos-mod/build.sh: line 16: curl: command not found
```

- Cause: `build.sh mod` downloaded the commit with `curl`, but the pinned `eclipse-temurin:25.0.5_8-jdk-noble`
  image has neither curl nor wget (its Dockerfile installs wget to fetch the JDK, then purges it). The test ran
  `build.sh mod` with a stand-in curl on PATH, so it could not see that; round 0 built from a mounted checkout, and
  `check_build=resolve` had not run since.
- Fix (`os/Containerfile`, `os/build.sh`): a `source` stage on the pinned Bazzite base, which has curl (`build.sh
  packages` uses it too), fetches exactly the commit with the same curl flags and the exact-commit check, keeps only
  `mod/`, and prints `MOD_SOURCE <commit> <sha256 of the archive>`. The JDK stage copies only `mod/` and runs only
  Gradle (`build.sh mod <source> /out <commit>`). The first `FROM` and `os-image.yml` are unchanged.
  `check-build.sh build` also requires the `MOD_SOURCE` line.
- `build-mod.sh --twice` (the resolve path) now builds exactly those two stages with `podman build --no-cache
  --target mod` of the same Containerfile and copies the jar out, so it has no second way to build the jar.
- Test against the image's real contents: `os/ci/builder-tools.py` reads the pinned JDK image straight from its
  registry (manifest by digest, every layer, whiteouts applied) and writes `os/minecraft/builder-tools.txt`: its
  PATH, JAVA_HOME and the 512 executables in its PATH folders (no curl, no wget). A test keeps the list bound to
  the lock's builder pin, and `build-mod.sh` checks it against the image (`--check`).
  `ImageBuildTest.test_the_jdk_stage_needs_only_what_the_builder_image_has` runs the real `build.sh mod` and the
  real `gradlew` with a PATH of exactly those executables (only Java is a stand-in, in JAVA_HOME). With a curl
  fetch put back into the `mod` mode (interface unchanged) the test fails with exactly the CI error: `127 != 0 :
  build.sh: line 36: curl: command not found`. The same sandbox refuses `build.sh source` with `curl: command not
  found`.

### Not proven yet

- The pre-hand-off kill with a real Minecraft and systemd-oomd (the tests kill Java and the wrapper by hand; the
  VM's memory kill came from the kernel, not from systemd-oomd).
- The hand-back under labwc with a real game window (finding 8; the VM has no game).

## Review fixes 1 (REVIEW-1, 2026-11-10)

REVIEW-1 (Codex gpt-6-astra, high) found 3 blocking and 8 should-fix problems. Each is fixed at its cause, with
tests that fail on round 0's code (proof under "Before the fixes"). The owner accepted all 14 JUDGMENT-CALLs (board
#168 and #169); finding 1 changes call 10, updated below. The mod itself did not change, so no Gradle run was
needed and the jar pin (`8b04c511…65386743`) stays.

**Update (review fixes 2): these VM checks ran and passed in run 42865819198; see "Review fixes 2".** At the time:
both `check_build=build` runs (the budget) stopped before building,
in the runner's tool install, because Ubuntu's snapshot mirror (`snapshot.ubuntu.com`) answered 502 and 503. So
the jar built inside the image build, `desktop_jvm`, `memory_protection` and `memory_pressure` are written and
unit-tested but have not run in an image yet. One more `check_build=build` needs the integrator's OK.

1. **Memory kills never restart the game (blocking).**
   - Cause: Java ran in its wrapper's scope. When systemd-oomd or the kernel killed that scope, nobody reported an
     exit, and "no report" counted as a crash: a restart after 5 s.
   - Fix: the JVM now runs in its own scope (`aresos-game-<launch>.scope`, finding 4). A SIGKILL and an exit nobody
     reported are handled alike: the supervisor reads the scope's systemd `Result` (for example `oom-kill`; the
     scope is not collected, so the result stays readable until the supervisor resets it), latches RECOVERY
     `killed` with that detail, counts nothing and never restarts by itself. Prism killed by SIGKILL before the game
     started latches too. After a kill, `retry` waits until the last minute's memory pressure
     (`/proc/pressure/memory`, `some avg60`) is at most 10 %, and says so otherwise.
   - Tests: `RestartPolicyTest.test_a_whole_scope_death_without_a_report_latches_like_a_kill`,
     `test_a_kill_waits_for_cleared_memory_pressure_before_retry`, `test_prism_killed_before_the_game_latches`;
     `LoopTest.test_a_whole_scope_kill_latches_and_nothing_restarts` (the real loop: wrapper and JVM killed
     together, recovery latched, still one launch 1.5 s later with a 0.2 s backoff). VM: `desktop_jvm` kills a real
     JVM's game scope with `systemctl --user kill --signal=SIGKILL` and requires RECOVERY `killed`, latched, and
     nothing started 12 s later.
   - Not proven: systemd-oomd itself killing a real Minecraft. The VM sends the same SIGKILL to the scope by hand.
2. **A damaged hub never passes and is never declared ready (blocking).**
   - Cause: `check_world()` only checked that `level.dat` was gzip, and the "valid world" fixtures were plain text.
   - Fix, in the supervisor only (the mod is unchanged): a small bounded NBT reader (gzip, at most 16 MiB, depth
     64, trailing bytes refused). The hub passes only with `level.dat` or `level.dat_old` readable with its `Data`,
     `data/aresos/desktop.dat` with `enabled` = 1, `data/aresos/nether_home.dat` with its seed, position and yaw
     (and, when present, a `home` with a dimension, three numbers, yaw and pitch), `aresos-home.provisioned`
     exactly `complete`, and the hub manifest. Anything else is RECOVERY `world_damaged`, naming the file and the
     problem; nothing is rewritten. A `world_ready` from a hub that fails these checks latches recovery instead of
     IN_WORLD.
   - Tests: `WorldCheckTest` (the mod's real files pass; every damage case; malformed NBT; the `level.dat_old`
     fallback; checking leaves every byte), `RestartPolicyTest.test_a_damaged_hub_is_never_declared_ready`.
     Fixtures: `os/tests/fixtures/desktop-world/` holds the two saved-data files the mod's own client test wrote
     (`SOURCE.txt` says how); the damaged variants come from a small NBT writer in the test.
   - Not proven: a hub created by the mod on AresOS itself (the P3 trial).
3. **Every image build builds and checks the mod jar (blocking).**
   - Cause: only `check_build` ran `os/ci/build-mod.sh`; every other build needed a jar put in place by hand.
   - Fix, in the shared build path only (`.github/workflows/os-image.yml` is untouched): `os/Containerfile` has a
     `mod` stage on the lock's digest-pinned JDK image. It runs `build.sh mod <ARESOS_SOURCE_REVISION> /out`, which
     downloads exactly that commit from GitHub, builds `mod/` and prints `MOD_JAR_BUILT <sha256> from <commit>`.
     The image stage copies the jar in, and `build.sh configure` installs it only when its SHA-256 equals the pin
     (`MOD_JAR_PINNED`); otherwise the build stops. A build without a full commit stops with "pass --build-arg
     ARESOS_SOURCE_REVISION=<full commit>". The first `FROM` stays the pinned Bazzite base (the workflow checks it).
     `check-build.sh build` no longer builds the jar on its own; it requires both lines in the build log.
     `build-mod.sh --twice` (resolve) runs the same `build.sh mod` to set or renew the pin.
   - Which builds use it: `check-build.sh build`, and the release job package 27 is adding: it runs `bash
     os/ci/check-build.sh build` (branch `pkg/27-first-update-release` at `8fc6e350`). `build_tools.py` passes
     `ARESOS_SOURCE_REVISION=$GITHUB_SHA` as well. Main's `release_13` job builds `Containerfile.keyboard` (an
     overlay on release 13, only from `pkg/13-keyboard-layout`), not this tree's image.
   - Tests: `ImageBuildTest`: the stage order and pinned builder, the configure step's pin check, `check-build.sh`
     on the same path, and `build.sh mod` with stand-in curl and Gradle (it fetches exactly
     `codeload.github.com/Ares-Empire/AresOS/tar.gz/<commit>`, extracts only `mod/`, and refuses `unrecorded`,
     `main`, short and upper-case revisions).
   - Not proven yet: a real image build through the new stage (the next `check_build=build`; it must print
     `MOD_JAR_BUILT 8b04c511… from <commit>` and `MOD_JAR_PINNED`, or a `resolve` run renews the pin), and package
     27's release job on the merged tree (it runs once both are merged).
4. **The memory limit holds for the real JVM.**
   - Cause: `MemoryHigh` sat on Prism's scope. A Prism that was already running (Prism hands `--launch` to it) or
     Prism's own Launch button gave a JVM outside it.
   - Fix: the supervisor's answer to the wrapper names the game's scope. The wrapper starts Java through
     `systemd-run --user --scope --slice=aresos.slice --unit=aresos-game-<launch>.scope --property=MemoryHigh=5G`,
     waits (at most 10 s) until the JVM is in that cgroup, and only then reports it. The supervisor reads
     `/proc/<pid>/cgroup` and refuses a JVM outside its scope. Prism's own scope no longer carries the limit.
   - Tests: `WrapperTest.test_the_real_jvm_runs_in_its_own_scope_with_the_memory_target` (a real user systemd: the
     reported PID is the JVM, in `aresos.slice/aresos-game-<launch>.scope` with `memory.high` 5368709120; ran in
     WSL; it skips itself only where no user manager answers), `test_the_game_waits_for_its_scope_and_is_reported_only_inside_it`,
     `test_a_scope_that_is_not_usable_is_refused_before_java_runs`,
     `RestartPolicyTest.test_a_jvm_outside_its_memory_scope_is_refused`. VM: `desktop_jvm` starts the image's real
     Java 25 through the real wrapper from outside any desktop scope, as Prism's own window or an already-running
     Prism would, and requires the JVM in `…/user@1001.service/aresos.slice/aresos-game-<launch>.scope` with
     `memory.high` 5 GiB, the pinned Java executable and the launch's nonce.
   - Not proven: Prism's own window and an already-running Prism with a real Minecraft (no account in CI). Every
     Prism launch of this instance goes through the wrapper, which applies the scope.
5. **A game that ended while the supervisor was down is accounted for once.**
   - Fix: before anything starts, the supervisor finishes the last launch from its runtime record exactly once
     (`accounted` is saved): exit 0 is a quit, a crash counts and backs off, a SIGKILL or a missing record latches
     `killed`. Exit records carry the launch ID, the PID and the process's start time; only a record matching all
     three counts.
   - Tests: `AdoptionTest.test_a_game_that_ended_while_no_supervisor_ran_is_accounted_for_once`,
     `test_a_crash_accounted_after_downtime_restarts_after_its_backoff`,
     `RestartPolicyTest.test_an_exit_record_of_another_launch_or_process_is_ignored`; `WrapperTest` checks the
     record's fields.
6. **One gate for every new JVM.**
   - Fix: every JVM passes the same `validate()`, whether the supervisor started Prism or the owner pressed Launch
     in Prism: the image pins, the managed instance and the world. A damaged hub, or one missing after it existed,
     latches recovery instead of falling back to setup. The wrapper also sends Prism's `INST_DIR` and the working
     directory; only the managed `AresDesktop` folder passes.
   - Tests: `RestartPolicyTest.test_every_new_jvm_passes_the_same_gate` and the refused-request cases (another
     instance, Java, folder or working directory).
7. **No endless STARTING.**
   - Fix: the wrapper reports `jvm_failed` when Java cannot start or the supervisor refuses it (and then stops that
     JVM). The supervisor waits at most 30 s from authorizing a JVM to its PID, and a wrapper connection that closes
     before the PID arrives is a failed start. Each counts like a crash (B2's backoff and latch); during setup it
     shows the setup message.
   - Tests: `RestartPolicyTest.test_a_failed_start_is_reported_and_counted_never_left_open` (spawn failure, a
     refused JVM, a lost connection, the hand-off timeout), `WrapperTest.test_a_start_that_fails_is_reported`.
8. **The game's full component set is pinned.**
   - Fix: `desktop.lock.json` has `components`: Prism's metadata for `net.minecraft` 26.2 and `org.lwjgl3` 3.4.1
     from meta.prismlauncher.org, with SHA-256 and size. They ship in the image as local patches, so Prism never
     resolves other versions; they list every library and native with the hash Prism checks on download. The
     instance check requires exactly Minecraft 26.2, LWJGL 3.4.1 and Fabric Loader 0.19.5, nothing else and
     nothing twice; the image check refuses unpinned files in `patches/`. Mojang's files still come from Mojang
     through Prism.
   - Tests: `test_any_other_lwjgl_or_a_missing_or_doubled_component_is_drift`,
     `VerifyInputsTest.test_the_pinned_component_metas_are_inputs_too`, the component pack test.
   - Not proven: Prism downloading through these metas (no account in CI).
9. **Recovery stays usable under memory pressure.**
   - Fix: drop-ins give `user.slice`, `user-1001.slice` and every login session scope `MemoryLow=1G` (protection
     needs every ancestor), and session scopes `ManagedOOMPreference=avoid`. labwc, the supervisor and the recovery
     terminal run in the session scope. The game runs under `user@1001.service/aresos.slice` without protection, so
     reclaim and kills go there first.
   - Tests: `MemoryProtectionFilesTest`. VM: `memory_protection` reads the effective `memory.low` of the three
     cgroups, checks that the supervisor and the recovery terminal share labwc's session scope and that systemd set
     the oomd avoid flag; `memory_pressure` runs a memory hog in `aresos.slice` (no swap) until it is killed, then
     requires labwc, the supervisor, its keeper and the recovery terminal alive with the same PIDs and the
     supervisor answering.
   - Not proven: the 16 GB laptop with a real Minecraft and zram.
10. **Lost readiness shows.**
    - Fix: no heartbeat for 20 s clears "ready" and shows RECOVERY `unready`; the game keeps running and the window
      closes by itself when heartbeats return. A helper that keeps failing (5 times in a minute) clears "ready" and
      shows `helper`. An adopted JVM gets the same 120 s readiness window as a new one.
    - Tests: `RestartPolicyTest.test_lost_heartbeats_show_without_touching_the_game`,
      `test_an_exhausted_helper_after_the_hub_was_ready_shows`,
      `AdoptionTest.test_an_adopted_game_that_never_becomes_ready_shows_after_the_timeout`.
11. **A restarted desktop waits below the app in front.**
    - Fix: when the supervisor restarts Minecraft by itself, it starts package 24's app helper with
      `ARESOS_SHELL_KEEP_FOREGROUND=1`. If the new desktop window takes focus within 3 s of appearing while another
      window was in front, the helper activates that window again, once, through the same labwc window activation it
      uses to return to the desktop. A later switch to the desktop is the owner's and stays. The flag never reaches
      launched apps.
    - Tests: `KeepForegroundTest` (5 tests in `test_aresos_shell.py`); `RestartPolicyTest` checks that only an
      automatic restart sets the flag.
    - Not proven: the VM has no game window, so the real hand-back under labwc is for the P3 trial. The desktop may
      flash in front for a moment before the app is back on top.

Tidy-ups found on the way: the level check names both level files' problems; on shutdown the supervisor closes its
ends of the game's pipes and waits for its message window; `LoopTest` reaps its Prism stand-ins (the suite no longer
leaves processes or `ResourceWarning`s behind).

### Before the fixes

The new tests and fixtures (`5c250720`) against round 0's code (`939bc259`: the supervisor, wrapper, helper,
Containerfile, `build.sh`, `check-build.sh`, `build-mod.sh` and `checks.py` put back, the drop-ins removed), in a
fresh clone in WSL: 33 of the 35 new tests fail (FAIL or ERROR). The two that pass guard what was already right: a
valid hub passes, and `level.dat_old` stands in for a damaged `level.dat`. In `test_aresos_shell` every helper test
errors on round 0's helper, because the shared fixture now passes `keep_foreground`. Per test:
`runs/wsl-review-fixes-1/summary.txt`.

### Checks of this round

- WSL (Ubuntu 24.04, Python 3.12), fresh `git clone` of `pkg/23-minecraft-starts` at `5c250720`, no other suite
  running: the full suite plain and `-B`, both `Ran 958 tests`, `FAILED (failures=1, errors=12)`, exactly the
  known WSL-only set that also fails on main (`test_greeter` 3, `test_inherited_homebrew` 8, `test_sysusers` 2).
  `test_aresos_desktop` (97, including the real user-systemd scope test) and `test_aresos_shell` (72) pass. The
  suite runs under `setsid` with stdin from `/dev/null`: with a terminal attached, `test_everyday_account`'s
  interactive `bash -i` stops on job control and the suite hangs until its timeout.
- During the work, focused from the worktree: `test_aresos_desktop` 96 OK twice (once with `-X tracemalloc`: no
  `ResourceWarning` left from its own processes; two leaked stand-ins from round 0's loop tests were found and
  killed; the reaping now prevents that).
- CI:
  - 42827288649 and 42829696745 (`check_build=build` on `5c250720`): both failed in "Install pinned tools on
    disposable runner" before any build (`snapshot.ubuntu.com` 502 Bad Gateway, then 503 Service Unavailable).
    Not caused by this branch; no image was built.
  - **42830860249** (`checks_only=true` on `5c250720`, the full suite natively on the hosted runner): `Ran 958
    tests`, `OK (skipped=136)`, the same skips as main's leak-fix run (42819274873: `Ran 853 tests`,
    `OK (skipped=136)`); the 105 package 23 tests all ran and passed. Evidence: `runs/checks-42830860249/`.
  - Evidence for the two stopped builds: `runs/builds-42827288649-42829696745/summary.txt`.
  - 42834907206 (`check_build=build` on `7ec26b84`, the integrator's extra run): also stopped before any build.
    The mirror answered again but slowly: "Install pinned tools on disposable runner" fetched the indexes in
    12 min 17 s (59.7 MB at 81 kB/s) and hit its 20-minute limit while downloading packages (round 0's run needed
    4 min 18 s for this step).
- Not rerun: `check_build=resolve`. The jar pin did not change (the mod is unchanged); the next `build` shows
  whether the image's own `mod` stage gives the same bytes.

## What the owner will see

- **First start after the update:** a small terminal says "AresOS: first start" with three steps, and Prism
  Launcher opens on its own sign-in page. He signs in with his Microsoft account in Prism. Prism downloads
  Minecraft 26.2 (a few minutes, once) and starts it on the title screen. He clicks **AresOS**, keeps seed 49 (or
  picks another) and clicks **Create**: the existing mod builds the hub exactly as on Windows. The terminal closes
  by itself once he is in the hub.
- **Every later start:** labwc comes up and Minecraft opens straight into the AresHub world, borderless and
  maximized, on the NVIDIA GPU. No terminal opens at login any more; the hub's Terminal app and Super+Ctrl+Escape
  still give one.
- **If Minecraft crashes:** it starts again after 5 s, then after 10 s. A third crash within five minutes, or a
  third in a row without 30 healthy minutes in between, stops the restarts: a terminal says what happened, where
  the logs are, and to type `retry`. That stop survives a reboot. A restarted hub opens below the app he is using.
- **If the system stops Minecraft to free memory:** it is not restarted. A terminal says Minecraft was stopped
  from outside and to close apps he doesn't need; `retry` works once memory is free again.
- **If he quits Minecraft himself:** nothing restarts; a terminal says "Minecraft was closed" and `retry` opens the
  hub again.
- **If Prism needs him to sign in again** (or the network is down): Prism shows its own dialog. If Prism ends
  without starting the game, a terminal says so and waits for `retry`.
- **If something is wrong with the world or the files:** a missing hub (one that existed before), a damaged hub, a
  changed desktop instance or an image file that doesn't match its pin each stop into a terminal that names the
  problem and the fix. AresOS never makes a replacement world and never changes the instance or the world.

## Done

### A. Prism and Java 25 in the image

- **Java 25:** Fedora's `java-25-openjdk-headless-1:25.0.4.1.1-1.1.fc44` and its three new dependencies
  (`java-25-openjdk-crypto-adapter`, `javapackages-filesystem`, `tzdata-java-2026f-1.fc44`) join
  `os/packages.lock.json` through the existing lock (resolved by run 42803572026; no other package in the lock
  moved). The game uses `/usr/lib/jvm/java-25-openjdk/bin/java`, a real file of that package.
- **Prism Launcher:** not in Fedora (checked: no `prismlauncher*` in `fedora`/`updates`; only a COPR side
  repository exists, which the brief rules out). The image takes Prism's official Linux bundle
  `PrismLauncher-Linux-Qt6-Portable-11.1.1.tar.gz` (Prism 11.1.1, 2026-09-28, the newest release) from its pinned
  GitHub URL, accepted only with its pinned SHA-256 and size (`e21949a8…e09e823`, equal to GitHub's own asset
  digest). `os/build.sh` unpacks it into `/usr/lib/prismlauncher` (Python's `data` filter: root-owned, no
  setuid/setgid, no group/world write; the archive records its files as UID 1001, which is `ares`), removes
  `portable.txt` and both `prismlauncher_updater` files, and links `/usr/bin/prismlauncher`. Prism's own log
  confirms the result: `Updates Enabled: No` (its updater turns on only when `bin/prismlauncher_updater` exists)
  and `Adjusted by: "Persistent data path"` (data in `~/.local/share/PrismLauncher`, not next to the binary). Every
  unpacked file's hash is recorded in `/usr/share/aresos/manifest/prism-files.sha256`. No desktop entry or MIME
  handler is installed (the bundle's would make Prism the handler for every `.zip`). Prism's UI stays available as
  `prismlauncher` for setup and re-login.

### B. The managed `AresDesktop` instance (`os/minecraft/desktop.lock.json`)

- **Pinned inputs** (`/usr/share/aresos/minecraft`, all from their pinned URLs and SHA-256, checked again at every
  desktop start):
  - Fabric Loader 0.19.5 and its six libraries (asm 9.10.1 ×5, sponge-mixin 0.17.4+mixin.0.8.7) from
    `maven.fabricmc.net`; each hash equals Maven's published `.sha256` and Fabric's own launcher profile for 26.2.
  - Fabric API 0.161.0+26.2 (Modrinth; byte-identical to Fabric's Maven copy), the newest for 26.2.
  - The AresOS mod jar, built from this repository's `mod/` (below), SHA-256 `8b04c511…65386743`.
  - `patches/net.fabricmc.fabric-loader.json`: a Prism component for Fabric Loader whose libraries are all
    `"MMC-hint": "local"`, so Prism loads the loader only from the image and never fetches it. It is generated
    from the lock (`loader_patch`) and a test keeps the shipped file equal to it. Like Fabric's own launcher profile
    for 26.2, it needs no intermediary mappings (26.x is not obfuscated).
- **The mod jar is reproducible and pinned:** `mod/build.gradle` turns off archive timestamps and fixes the entry
  order (no other mod change). Since review fixes 1 every image build builds it: the Containerfile's `mod` stage
  runs `build.sh mod <commit>` in the digest-pinned `eclipse-temurin:25.0.5_8-jdk-noble` image, and `build.sh
  configure` installs the jar only with its pinned hash. `check_build=resolve` builds it twice through the same
  `build.sh mod` and requires equal bytes (run 42803572026: both `8b04c511…`).
- **Provisioning** (`provision()` in `/usr/libexec/aresos-desktop`, at every start, as `ares`):
  - Creates `~/.local/share/aresos/worlds` and, only if no instance exists yet,
    `~/.local/share/PrismLauncher/instances/AresDesktop`. It is assembled in a hidden staging folder and renamed
    into place, so it appears whole or not at all. An existing instance, complete or not, is never touched; nor is
    an existing `prismlauncher.cfg`.
  - The instance: `instance.cfg` (wrapper command `/usr/libexec/aresos-desktop-java`, Java 25 pinned, heap
    512 MiB to 3 GiB (B5), console never shown, maximized window, Prism's own GPU switch off),
    `mmc-pack.json` (Minecraft 26.2, Fabric Loader 0.19.5), `minecraft/options.txt` (render 8 and simulation 5
    chunks (B5), no exclusive fullscreen, no first-launch accessibility screen).
  - `patches`, `libraries` and `minecraft/mods` are links into `/usr/share/aresos/minecraft`, so they are read-only
    and an AresOS update or rollback changes them with the image. `minecraft/saves` links to
    `~/.local/share/aresos/worlds`: the world lives there and is linked into this instance only (section 5).
  - A first-start `prismlauncher.cfg` (only if none exists) keeps Prism's first-run wizard to its sign-in page
    (English, system theme, our Java, no automatic Java download or switching).
  - **A pin mismatch stops into recovery:** a changed image input (`verify_inputs`), or an instance whose links,
    wrapper command, Java path, Minecraft or Fabric Loader version or components differ (`check_instance`), opens
    recovery with the exact difference. Prism's own rewrites (`lastLaunchTime`, the LWJGL component it adds) are
    not drift. `aresos-desktop reset-instance` moves a drifted instance aside (dated, nothing deleted, and the old
    copy loses only its link to the worlds); the next start makes a fresh one with the same world.
- **No Sodium or Iris.** Minecraft itself is never in the image; Prism downloads it after he signs in. Nothing reads
  or edits Prism's account file.

### C. The world

- First start: the hub is created by the mod's existing code, the way Windows does it today: the title screen's
  **AresOS** button, then `HomeCreateScreen` (seed 49 prefilled, placeholder hub), then `NetherHome` writes the
  manifest, `DesktopWorld` marks the save and the hub is built on the first server start (packages 04/04c). Because
  `minecraft/saves` is the worlds folder, the save lands in `~/.local/share/aresos/worlds/AresHub`. No mod code
  changed for this (JUDGMENT-CALL 1).
- Later starts: `--world AresHub` (Prism's quick play), checked first by `check_world`: `level.dat` (or
  `level.dat_old`), the desktop marker `data/aresos/desktop.dat` (switched on), the saved Nether home and a
  finished hub build must all read as the mod writes them (NBT, review fixes 1, finding 2); anything else counts
  as damaged.
- Missing (after the hub has been seen once, recorded in the state file), damaged or interrupted: RECOVERY,
  latched. Never a replacement: `aresos-desktop forget-hub` (only while `AresHub` is absent) is the explicit way
  back to first-start creation.

### D. The supervisor (`/usr/libexec/aresos-desktop`, Python standard library)

- **Start:** labwc's autostart now runs the polkit agent and `/usr/libexec/aresos-desktop session` (no terminal).
  `session` is a small keeper that runs `aresos-desktop supervise` and restarts it after a failure, up to 5 times in
  10 minutes, then shows a terminal with the reason.
- **States (B2):** SETUP (no hub yet: Prism's sign-in, then the title screen), STARTING, IN_WORLD, AUTH_REQUIRED,
  RECOVERY. SETUP, AUTH_REQUIRED and RECOVERY open a foot terminal (`app_id aresos.desktop`) with the message and a
  `retry` command. It is set up like the recovery terminal (system PATH, never his `~/.bashrc`) and closes when the
  hub is reached or a new launch starts.
- **Launch:** `systemd-run --user --scope --quiet --collect --slice=aresos.slice
  --unit=aresos-desktop-<launch>.scope -- /usr/bin/prismlauncher --launch AresDesktop --world AresHub` (no
  `--world` in SETUP). B5: since review fixes 1 the JVM itself runs in `aresos-game-<launch>.scope` with the 5 GiB
  soft target, started there by the wrapper (finding 4); apps stay in the helper's `app.slice` scopes; no hard
  limit yet. Prism gets the session's
  environment with the system PATH and no launch secrets.
- **The real JVM:** Prism runs `aresos-desktop-java <java> <args>` (its wrapper command) instead of Java. The
  wrapper
  - takes the desktop lock (`$XDG_RUNTIME_DIR/aresos/desktop.lock`); Java inherits it, so it is held from loading to
    the JVM's final exit (B2), and a second desktop cannot start;
  - asks the supervisor for the launch over its socket (peer UID and PID checked; only the `AresDesktop` instance
    and the pinned Java are accepted; refused while recovery is latched or a desktop already runs);
  - starts Java as its child with the launch nonce, desktop instance and GPU variables, reports the JVM's PID (the
    supervisor checks it is the wrapper's child, records its start time and watches it with a pidfd) and its exact
    exit status (first in `~/.local/state/aresos/desktop-exit.json`, which outlives a supervisor restart and, since
    review fixes 5, a reboot);
  - makes Java die with it (PR_SET_PDEATHSIG) and forwards termination signals. Prism's stdin (its launch script),
    stdout and stderr pass straight through.
  A restarted supervisor adopts a JVM that still runs (PID and start time) and never starts a second one.
- **Package 24's helper (brief item 6, first branch):** the supervisor starts `/usr/libexec/aresos-shell` for every
  launch with `ARESOS_DESKTOP_INSTANCE` (one per session) and a fresh `ARESOS_LAUNCH_NONCE`, and the wrapper gives the
  game the same two (B1). A helper that exits is restarted with the same nonce after 2 s (at most 5 times a minute).
  Readiness reaches the supervisor on a new one-way **status pipe** (`ARESOS_SHELL_STATUS_FD`): the helper writes
  `desktop_connected`, `world_ready` and `heartbeat` lines for the authenticated desktop only, drops a line rather
  than block, and never passes the descriptor to apps. This answers package 24's open question about where
  readiness lives.
- **Restart policy (B2):**
  - An unexpected exit (non-zero) restarts after 5 s, then 10 s; three failures within five minutes or three
    consecutive failures (ready-then-crash cycles four minutes apart included) latch RECOVERY.
  - The consecutive count, the failure times, the latch and whether the hub has been seen persist in
    `~/.local/state/aresos/desktop.json` (atomic writes); an unreadable file stops into recovery instead of losing a
    latch.
  - Reset only by 30 continuous healthy minutes in the world (heartbeats at most 20 s apart; leaving the world or a
    gap restarts the period) or the owner's `retry`.
  - Never restarted automatically: exit 0 (he quit), a kill by SIGKILL (memory pressure or force; latched, not
    counted), auth states (Prism ending before the game), setup, and the 120-s prepared-start timeout, which shows
    recovery but never kills the game (if the hub appears later, the terminal closes).
- **Logs:** `~/.local/state/aresos/desktop.log` (rotated at 512 KiB). Recovery texts point there and to Minecraft's
  `latest.log` and `crash-reports/`.

### E. The GPU

The wrapper gives only the game `__NV_PRIME_RENDER_OFFLOAD=1`, `__GLX_VENDOR_LIBRARY_NAME=nvidia` and
`__VK_LAYER_NV_optimus=NVIDIA_only`, and only when `/proc/driver/nvidia/gpus` lists a GPU. These are the variables
switcheroo-control and Prism's own discrete-GPU switch use: NVIDIA's PRIME render offload renders this one process
on the RTX 4060 for GLX (Xwayland), EGL and Vulkan, while Intel keeps driving the session and every other app
(OS-BASE section 2: per-game offload, never session-wide). Variables that Prism's bundle set for Prism itself, any
other GPU variables and `LD_PRELOAD`/`LD_LIBRARY_PATH` are removed from the game's environment, and its PATH is the
system PATH. OpenGL, no shaders (Minecraft's default renderer; no Sodium or Iris). JUDGMENT-CALL 5 covers a machine
without the NVIDIA driver.

### F. Session files

- `labwc/autostart`: the polkit agent, then the supervisor (no terminal).
- `rc.xml`: a window rule makes the hub window (`app_id aresos-desktop`, set by package 24's mixin) borderless and
  maximized. Super+Ctrl+Escape is unchanged.
- `/usr/share/aresos/desktop-view.bashrc`: the message terminal's rcfile.
- `/usr/bin/aresos-desktop` links to the supervisor for his commands (`status`, `retry`, `forget-hub`,
  `reset-instance`).
- `os/README.md` describes the desktop and the mod-jar step.

### G. Verification code

- `os/tests/test_aresos_desktop.py` (71 tests):
  - pinned inputs and the shipped loader patch;
  - provisioning: exact layout, idempotent byte for byte, an existing instance and Prism config never overwritten,
    a failed provisioning leaves nothing, drift reported but not repaired, Prism's own rewrites tolerated;
  - world checks;
  - the exact `systemd-run`/Prism command and the environments (Prism without secrets; the game with nonce, system
    PATH and NVIDIA only with the driver; the wrapper's scrubbing);
  - the restart policy;
  - the supervisor's states with a fake runner: first start, hub creation, crash backoff and latch, the latch
    surviving a restart and refusing the wrapper, retry, ready-then-crash cycles, the 30-minute reset and
    heartbeat gaps, quit, kill, unknown exits, the exit file, slow start without a kill, AUTH_REQUIRED, early Prism
    failure, refusals, a held lock, adoption, the helper's restart budget, every message's instruction;
  - on Linux, the real wrapper (environment, stdin, exit status, refusal, no supervisor, the lock held until the
    JVM ends, the game dying with a killed wrapper, signal forwarding) and the real event loop with stand-ins for
    Prism, the helper and Java (crash, restart, latch and `retry` over the real socket; AUTH_REQUIRED; malformed and
    foreign requests; an internal error answered without stopping the supervisor).
- `os/tests/test_aresos_shell.py`: three tests for the status pipe (only authenticated desktop events; never blocks;
  a closed pipe switches it off; apps never inherit it).
- `os/tests/test_everyday_account.py`: two assertions pinned the old autostart line (`aresos-terminal &`); they now
  pin the new one, which is the decision the brief changes. Nothing was deleted or skipped.
- `os/ci/check-resolve.sh`: a package 23 inventory (Java in the base and in Fedora, Prism not in Fedora, the pinned
  bundle's hash, layout, `--version`, `--help` and a headless start as an unprivileged user); `check-build.sh
  resolve` builds the mod jar twice.
- `os/ci/image-checks.sh` (inside the built image): Java 25 is the locked package and runs as `ares`; Prism is the
  pinned version, its files match the recorded hashes, are root-owned and not group/world-writable, with no
  updater, portable marker or setuid file, and its own log says updates off and data in his home; every
  provisioning input matches its pin; the autostart and window rule; provisioning as `ares` from the real inputs is
  idempotent and reports a changed instance; no system unit starts the desktop; the supervisor, wrapper, view and
  Prism join the absolute-startup-command check. `check-image.sh` also compares the image's `desktop.lock.json`
  with the repository's.
- `os/ci/overlay/checks.py` (VM): the first terminal is now the desktop's message window; the shortcut check
  requires a recovery terminal next to it (both recovery-style), and a new `desktop_session` check requires the
  keeper, supervisor, helper and Prism to run as `ares` and nothing of the desktop as root, state SETUP, the helper
  holding the session's instance and the launch's nonce, Prism without the nonce, Prism in
  `aresos.slice/aresos-desktop-<launch>.scope`, the instance's four links, and Prism's log (updates off, launching
  `AresDesktop`). Review fixes 1 adds `memory_protection`, `desktop_jvm` and `memory_pressure` (findings 1, 4, 9). `shadow-names.txt` adds `prismlauncher`, `java`, `systemd-run`,
  `systemctl`, `aresos-desktop`, `aresos-desktop-java`, `aresos-shell` and `cat`.
- Bound sources: no file bound by the package 16 walk changed (`os-image.yml` and `vm.py` are untouched), so
  `os/manifest/ci/16/pending-rebind.json` is unchanged (`test_checkout_sources` passes).

## Verified

CI runs on this branch (`https://github.com/Ares-Empire/AresOS/actions/runs/<id>`):

| Run | What | Result |
|---|---|---|
| 42803572026 | `check_build=resolve` on `a2e6c997` | Success. Java 25 resolves to four new packages and nothing else moves; no Prism in Fedora; the Prism bundle matches its pin, `--version` prints `PrismLauncher 11.1.1`, a headless start logs `Updates Enabled: No` and `Persistent data path`; the mod jar built twice from clean copies: both `8b04c511…65386743` (`MOD_JAR_REPRODUCIBLE`). Evidence: `runs/resolve-42803572026/`. |
| 42807403559 | `check_build=build` on `92f03f2e` | Failed at the new Prism version check: Prism prints its version and then an empty line, and the check took the last line. Everything before it passed (image built, mod jar pinned, Java 25, Prism files, ownership, hashes). Fixed in `36f6dcc4` (exact line match). |
| **42809824712** | **`check_build=build` on `36f6dcc4`, with the VM boot** | **Success.** `MOD_JAR_PINNED 8b04c511…`; 39 in-image PASS lines and `IMAGE_CHECKS_PASSED`, including Java 25 (`java-25-openjdk-headless-1:25.0.4.1.1-1.1.fc44`, `openjdk version "25.0.4.1"` as `ares`), `Prism Launcher PrismLauncher 11.1.1 from its pinned bundle`, the pinned inputs, the autostart, provisioning as `ares` and no system unit; `all 30 absolute startup commands exist`; `polkit: 21 rule files, 401 actions, 0 change with wheel, 73 denied to ares, 132 reviewed passwordless, 0 cached defaults`, `POLKIT_CHECK_PASSED`; `Image manifest locks equal the reviewed locks` (now including `desktop.lock.json`); `CHECK_BUILD_PASSED`. VM pass: guest policy, power events, the recovery shortcut, tty3 login and `PASS: offline logind power-key path`; `UEFI VM checks passed`; `CHECK_BUILD_VM_PASSED`. The new `desktop_session` check, in the real labwc session: keeper, supervisor, helper and `/usr/bin/prismlauncher --launch AresDesktop` all UID 1001, state `SETUP`, the helper with the session's instance and the launch's nonce, Prism in `/user.slice/user-1001.slice/user@1001.service/aresos.slice/aresos-desktop-<launch>.scope` with `memory.high` 5368709120, the four instance links, Prism's log `Version 11.1.1`, `Updates Enabled: No`, `Persistent data path`, `Application root path "/usr/lib/prismlauncher"`, `ID of instance to launch "AresDesktop"`; both terminals (the desktop's message window and the recovery terminal) recovery-style; none of the 25 shadowing programs in `~/.local/bin` ran. Evidence: `runs/build-42809824712/`. |
| 42809903934 | `checks_only=true` on `36f6dcc4` (full suite natively) | `Ran 927 tests`, `FAILED (failures=7, errors=111, skipped=27)`: all 118 in package 22's `test_owner_update`, exactly as on main (run 42815704308 on `6978dc3c`: `Ran 853 tests`, the same 118; PLAN-GAP 5). Every package 23 test passed natively. The step stops at that unittest command, so its compile and syntax sweeps did not run there (they ran locally: `py_compile` and `bash -n` on every changed file). Summary: `runs/checks-42809903934/summary.txt`. |

Laptop (Windows, `mod\gradlew.bat build runClientGameTest`; the mod changed only in `build.gradle`; no Lunar Client,
no other Minecraft or Gradle running, no WSL suite during them):

- **Run 1** (6.4 GB free): `BUILD SUCCESSFUL in 7m 41s`. Unit tests: 62 `PASSED`, none failed or skipped. Server
  game tests: `All 38 required tests passed :)`. Client game tests: all passed (`01c`, `04`, `04b`, `04c`, `04d`,
  `07`, `07b`, `08`, `08b`, `09`, `09b`, `09c`, `09d`, `24`).
- **Run 2** (6.3 GB with run 1's daemon): `BUILD SUCCESSFUL in 7m 14s`, the same 38 server game tests and all client
  game tests passed again (unit tests up to date from run 1).
- After each run: `git checkout -- reviews/` and `git clean -f -- reviews/` (the client tests rewrite other
  packages' screenshots; package 23 adds none). Then `gradlew --stop`: `1 Daemon stopped`.
- The laptop's jar (`a86c2cf3…`, Temurin 25.0.4) differs from the pinned CI build (Temurin 25.0.5 container), as
  expected (JUDGMENT-CALL 14).

WSL (Ubuntu 24.04, Python 3.12, fresh `git clone --depth 1 -b pkg/23-minecraft-starts` into `/tmp` at `36f6dcc4`,
no other suite running, 5.0 GB free):

- Full suite, plain and `-B`: both `Ran 927 tests`, `FAILED (failures=1, errors=12)`. Every failure is in the known
  WSL-only set that also fails on main: `test_greeter` 3 errors, `test_inherited_homebrew` 1 failure + 7 errors,
  `test_sysusers` 2 errors. Everything else passes, including `test_aresos_desktop` (71), `test_aresos_shell` (67),
  `test_everyday_account`, `test_shell_assertions` and `test_checkout_sources`.
- Focused from the worktree during the work: `test_aresos_desktop` 71 OK (several times, also after the last
  supervisor change), `test_aresos_shell` 67 OK, `test_shell_assertions` 8 OK, `test_checkout_sources` 4 OK.

Other:

- Every Fabric jar's SHA-256 was computed from a fresh download and equals Maven's published `.sha256`; asm and
  sponge-mixin also equal Fabric's launcher profile for 26.2; Fabric API is byte-identical on Modrinth and Maven.
- Prism's behaviour was read in its 11.1.1 source: command-line options, `updaterEnabled()`, the data path and
  portable markers, the setup wizard's pages, `--launch` quitting when the game ends, the wrapper invocation
  (`LauncherPartLaunch::executeTask`: wrapper, then Java and its arguments, launch script on stdin), local
  libraries (`MMC-hint: local`, looked up in `instance/libraries/<artifact>-<version>.jar`) and custom patches.
- `.work/` holds only run evidence (under 1 MB); nothing over 500 MB is left.

## Not verified (needs the laptop, the owner or a later package)

- **The real boot into the hub on the laptop** (the P3 trial, after a release with the owner's OK). Everything
  below is part of it.
- Prism's real hand-off to the wrapper with a real Minecraft. The wrapper is tested with Prism's exact argument
  shape and stdin from Prism 11.1.1's source, and the VM shows Prism starting for `AresDesktop`, but no JVM was
  launched: CI has no Microsoft account and must not download Minecraft without one.
- The owner's sign-in in Prism's wizard (device code or browser through `xdg-open` and Chrome), Prism's re-login
  dialogs, and how long the first Minecraft download takes.
- The mod's `world_ready` and heartbeats reaching the supervisor through the real helper in a real session (both
  sides are tested separately; the VM has no game).
- NVIDIA PRIME offload actually rendering Minecraft on the RTX 4060 (check F3 or the game log's renderer line);
  whether GLFW picks Xwayland or Wayland; the borderless maximized window rule; pointer capture and
  Super+Ctrl+Escape while the game has focus.
- Memory: the 3 GiB heap and the 5 GiB soft target under real use (B5 asks for measurement).
- Restart behaviour with a real crash, and the 30-minute reset with real heartbeats.

## JUDGMENT-CALL

Owner-facing ones first (1 to 6); 7 to 14 are technical.

1. **First start: he creates the hub with the mod's AresOS button, as on Windows.** (Owner-facing.)
   - Chosen: on first start Minecraft opens on its title screen (no `--world`) and the SETUP terminal tells him to
     click AresOS and Create. The mod's existing create screen offers seed 49 with the placeholder hub, the quick
     picks 50 and 26, or his own seed. No mod code changed.
   - Rejected: the mod creating AresHub by itself with seed 49 (STATE.md: he explores seeds and nothing is locked
     until he says so; it would pick for him), or the mod opening its create screen automatically on AresOS (a mod
     change with its own client test, for one click less).
   - Cost of changing later: a small mod change (open `HomeCreateScreen` when the session asks) plus a client test.
2. **No terminal at login.** (Owner-facing.) The session used to open foot at login; now the supervisor opens a
   terminal only when there is something to read or do (first start, sign-in, recovery). In the hub, the Terminal
   app and Super+Ctrl+Escape give a terminal. Rejected: keeping the login terminal behind the hub (one more window
   to Alt+Tab past, and it would sit in front until Minecraft is up). Reversal: one autostart line.
3. **Quitting Minecraft yourself does not restart it.** (Owner-facing.) Exit code 0 is his own Quit: a terminal
   says "Minecraft was closed" and `retry` opens the hub again; nothing is counted as a failure. Rejected:
   restarting it at once (the hub would come back every time he tries to leave it, and before package 25 there is
   no shut-down button in the hub). Reversal: a few lines in `finish_jvm`.
4. **A slow start never kills the game.** (Owner-facing.) If the hub is not ready 120 s after the JVM started
   (B2's prepared-start timeout), a recovery terminal says so, but Minecraft keeps running, and the terminal closes
   by itself if the hub appears. Rejected: killing and restarting it (a world being generated or loaded must not
   be killed; B2 forbids destructive automatic repair). The first start (SETUP) has no timeout: download, sign-in
   and world creation take as long as they take.
5. **Without the NVIDIA driver the hub still starts, on the default GPU.** (Owner-facing in a failure.) The
   offload variables are set only when `/proc/driver/nvidia/gpus` lists a GPU; otherwise the game runs on Intel and
   the log says so. Rejected: refusing to start (no hub at all after a driver problem; recovery would be harder,
   not easier). OS-BASE's "Intel-only Minecraft does not pass" is a qualification rule for the P3 trial, which
   should check the renderer.
6. **The desktop instance is strictly managed.** (Owner-facing if he tinkers in Prism.) Its mods, libraries and
   loader patch are read-only links into the image, so no extra mod can be added to the hub (the gameplay instance,
   P5, is for his mods), and AresOS updates change them with the image. A changed wrapper command, Java path,
   Minecraft or Fabric version or link stops into recovery with the exact difference; `aresos-desktop
   reset-instance` moves the instance aside (dated, nothing deleted) and the next start makes a fresh one with the
   same world. Rejected: copying the jars into the instance (stale after an update, and "never overwrite" would
   then mean recovery after every update) or repairing drift automatically (the brief: never overwrite).
7. **Prism comes from its official Linux bundle, without its updater.** Prism is not in Fedora; the only Fedora
   route is a COPR side repository, which the brief rules out. Of the official Linux downloads I took the extracted
   "Qt6 Portable" bundle (the AppImage needs FUSE or extraction, and portable mode would keep his data next to the
   binary). Removing `portable.txt` and `bin/prismlauncher_updater` is exactly how Prism decides (its source,
   `Application.cpp`): updates off and data in `~/.local/share/PrismLauncher`; its own startup log confirms both.
   It brings its own Qt 6.10 and libraries (about 200 MB under `/usr/lib/prismlauncher`). No desktop entry or MIME
   registration (the bundle's would claim every `.zip`).
8. **Java is the headless JRE** (`java-25-openjdk-headless`): Minecraft and Prism's launcher part need no AWT, and
   it adds three small packages instead of the full JRE's GUI stack. Changing it later: one package in the lock.
9. **Fabric Loader stays 0.19.5** although 0.20.1 (2026-10-19) exists: the mod builds and its client tests run on
   0.19.5. Moving the image to 0.20.x belongs with a mod change that also moves `gradle.properties`. Fabric API
   0.161.0+26.2 is already the newest for 26.2.
10. **Only a certain ordinary crash restarts by itself (updated in review fixes 1 and accepted by the owner, board
    #170; review fixes 2 applies it before the PID hand-off too; widened in review fixes 5, see below).**
    - The supervisor decides every end from Java's real exit status, as its wrapper saw it:
      - any status other than 0 and SIGKILL: a crash, counted, restarted after its backoff (three latch, as before);
      - exit 0: his quit, whenever it comes. Never counted, never restarted;
      - SIGKILL (the kernel's OOM killer, systemd-oomd, any forced kill): latches recovery `killed`;
      - no report and no record (the wrapper ended too, as when a whole scope is killed or with Prism's Kill
        button): latches `killed` as well.
      A latch is never counted as a crash and never restarts by itself (B5: no automatic restart under memory
      pressure). The message names the scope's systemd result when there is one, and `retry` waits until memory
      pressure has stayed clear for a minute.
    - **New in review fixes 5** (brief 5's rule: restart only when the end is certain to be an ordinary crash; the
      integrator decides whether this goes back to the owner):
      - A SIGKILL latches **whoever sent it**, also the wrapper's own SIGKILL of a Java that ignored SIGTERM for
        10 s while a start was being aborted. Until round 4 that counted as a failed start and restarted. The exit
        status cannot tell whose SIGKILL landed first, and a Java that cannot stop within 10 s may itself be a sign
        of memory pressure. The message then also says that the launcher wrapper sent a SIGKILL and that the cause
        is not certain.
      - Exit 0 before the hand-off (or after a refused or lost one) is his quit, no longer a failed start.
      - After a reboot, an end that was latched as unexplained is settled from the wrapper's exit record, which
        now survives the reboot. What the old session would have done next (wait after his quit, restart after a
        crash) is not carried into the new session; only a latch is.
    - Rejected: counting an unexplained exit as a crash (round 0's choice), because a memory kill would then come
      back after 5 s into the same pressure. Rejected in round 5: keeping "the wrapper stopped Java itself" as a
      reason to restart. It needs to know who ended Java, and five reviews in a row found a race in exactly that.
    - Cost: these ends need his `retry` instead of restarting by themselves: a crash that also takes the wrapper
      down (as before; rare, since the wrapper is a separate process outside the game's scope), and an aborted
      start whose Java had to be SIGKILLed (new; rare: the hand-off must break or be refused, and Java must then
      ignore SIGTERM for 10 s). A Java that exits 0 right at its start shows "Minecraft was closed" and is not
      tried again. Changing any of it later: a few lines in `Supervisor.conclude` and the model's `truth()`.
11. **One nonce per launch, one instance ID per session.** Every game launch gets a fresh `ARESOS_LAUNCH_NONCE`, so
    the helper is restarted with it before each launch (the game is not running then; the helper reconciles its app
    journal on restart, package 24). The instance ID stays for the session so the helper keeps its journal.
12. **The latch survives reboots, not only supervisor restarts.** It lives in `~/.local/state/aresos`. B2 says
    "survives restarts"; a crash loop that a reboot silently cleared would come back at every boot.
13. **The supervisor's keeper** restarts a failed supervisor up to 5 times in 10 minutes, then shows a terminal. The
    game survives a supervisor restart; the new supervisor adopts it by PID and start time.
14. **The mod jar pin is the CI container's build.** `build-mod.sh` builds in `eclipse-temurin:25.0.5_8` pinned by
    digest. A jar built on the laptop (Temurin 25.0.4) has other bytes (`a86c2cf3…`), so only the container build
    matches the pin; any change to `mod/` needs the pin renewed (`check_build=resolve` prints it).

## PLAN-GAP

1. **Every later image build must build the mod jar first.** Resolved in review fixes 1 (finding 3): the
   Containerfile's `mod` stage builds it from the build's own commit in every image build, and `build.sh configure`
   requires its pin. A build must pass `--build-arg ARESOS_SOURCE_REVISION=<full commit>` (check-build.sh and
   `build_tools.py` do); without it the build stops with that message.
2. **Pins expire.** Fedora `updates` drops superseded builds: `java-25-openjdk-headless` (25.0.5 already waits in
   updates-testing) and especially `tzdata-java` (time-zone updates) will vanish, as `xdg-desktop-portal-wlr` did
   for package 21. Renew with `check_build=resolve` and record it. Prism's, Fabric's and Modrinth's files are
   versioned and stay.
3. **Minecraft or Fabric upgrades need a migration.** An existing instance keeps `net.minecraft 26.2` in its
   `mmc-pack.json` (Prism's file; provisioning never rewrites it). An image that pins 26.3 stops into recovery
   ("Minecraft is 26.2, this AresOS pins 26.3") until `reset-instance`. The package that moves the mod to 26.3
   should add a reviewed migration, or accept that one reset.
4. **Readiness depends on the app helper.** Resolved in review fixes 1 (finding 10): a helper that is down for
   good now shows its own message (`helper`), apart from a slow start or lost heartbeats.
5. **Main's hosted regression job failed since package 22 (not caused here; fixed on main by PR #37,
   `d5d5c447`, merged into this branch).** `checks_only` on main `6978dc3c`
   (run 42815704308): `Ran 853 tests`, `FAILED (failures=7, errors=111, skipped=27)`, all in `test_owner_update`
   (for example `owner.Stop: Wrong or ambiguous target disk serial` where a test expects its own refusal). This
   branch gives exactly the same 118 failures and adds 74 passing tests (run 42809903934, `Ran 927 tests`). The
   same suite passes in WSL, where package 22 ran it; it was never run on the hosted runner. Package 22's area.
6. **Not in this package:** B2's APP_FOCUSED, STOPPING and DESKTOP_STOPPED_FOR_GAME (guardian 25, gameplay P5), a
   clean save at shutdown or logout (25: until then the session's end stops the game without a save request), and
   backups (26).

## Open questions

- None blocking. The owner-facing judgment calls (1 to 6) go to the owner before merge; the main one is whether the
  first start should create the hub by itself with seed 49 instead of waiting for his click on AresOS (1).
