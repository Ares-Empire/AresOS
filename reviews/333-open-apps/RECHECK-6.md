# Recheck 6 of PR150

1. **Item 1 holds: the live-launch cap counts systemd scopes per principal.** `launch()` lists scopes at each admission and calls `remember_scope` before the record is saved and the process is spawned. If the spawn fails, the unit name is dropped from the map again. `spawn_room` counts only `ACTIVE` `app-aresos-*` scopes, using `(owner == DESKTOP) == desktop`. A name missing from the map therefore counts toward the views' 32 and never toward the desktop's 256.
   - **The map is bounded.** It holds at most `SCOPE_OWNER_LIMIT` = 576 names, is saved with the journal, and is loaded back within that bound. When it is full, it drops the oldest name that isn't in the current listing. If the listing can't be read, it drops a view's name, which already counts as a view's.
   - **An unreadable list is handled the way the lead asked.** This covers a non-zero exit, unparsable output, `OSError`, a timeout, or any app scope in a state the helper doesn't recognise. In each case a view's launch is refused with the existing `journal_full` reply and "too many launches" text, and the refusal isn't recorded. The desktop's launch is never refused for this.
   - Code: `os/config/usr/libexec/aresos-shell:146`, `:2293`, `:2308`, `:2403`, `:4003`, `:4017`, `:4125`, `:4210`, `:4227`, `:4233`
   - Tests: `os/tests/test_aresos_shell_views.py:286`, `:329`, `:363`, `os/tests/test_aresos_shell.py:614`, `:639`

2. **Item 2 holds, and RECHECK-5's first finding is fixed.** Joining has one rule, in `still_starting`. A launch is joined only if all of these are true:
   - its state is `starting` and it isn't settled;
   - it has no window yet;
   - its launcher hasn't exited;
   - its original deadline hasn't passed;
   - its process is alive (or, for a launch recovered after a restart, its scope isn't `GONE`).

   The only other join is to a pending executable check. A failed, closed or ended launch is never joined, whatever its scope state. The 899cabbb grace period for discovered apps uses a separate `window_retry`. Joins still read the original `deadline`, so that grace makes nothing joinable.

   The new test runs RECHECK-5's exact first sequence: a failed laptop launch with an `UNKNOWN` scope, no scope poll in between, and the list still unreadable at the desktop's admission. The desktop's `activate_app` starts its own launch, and the laptop's replay still answers `launch_failed`. Separate tests cover an expired start, a launcher that exited cleanly, and a closed tray app.
   - Code: `os/config/usr/libexec/aresos-shell:2508`, `:4038`, `:4048`, `:4446`, `:4468`
   - Tests: `os/tests/test_aresos_shell_open_apps.py:444`, `:466`, `:480`, `:505`, `:523`

3. **Item 3 holds, and RECHECK-5's second finding is fixed.** At reconciliation, a saved `launching` or `starting` launch whose scope isn't `ACTIVE` (`GONE` or `UNKNOWN`) is marked failed with `launch_uncertain`. It can't be joined, and its saved reply, and any joined reply, replay that failure. The test runs RECHECK-5's second sequence:
   - After the restart the unit isn't watched, and the desktop starts a fresh launch.
   - When the unit then appears beside 31 scopes missing from the map, the next view open is refused.
   - After the unit ends, the same open is admitted.
   - Code: `os/config/usr/libexec/aresos-shell:3415`
   - Tests: `os/tests/test_aresos_shell_open_apps.py:540`, `os/tests/test_aresos_shell.py:792`, `:853`

4. **Item 4 holds: no admission decision reads launch-table states.** Admission now rests on three things: each client's own journal tables plus the room reserved for pending-check joins (`launch_room`), the check slots, and `spawn_room` (the listing plus the owner map). The launch table is read only to replay a request ID and to decide a join. Together with findings 1–3, the tests prove items 1–3, apart from the small gaps under nits 7 and 8.
   - Code: `os/config/usr/libexec/aresos-shell:3952`, `:3998`, `:4017`

5. **Item 5: both stated limits are low harm, not real harm.**
   - **Burst during registration.** The excess lasts only between spawning `systemd-run` and its scope appearing in the list. Each admission's listing is itself a subprocess, so a back-to-back burst can pass the cap by only a few launches. The next admission sees them.
     - It can't become a storm. View launches are still bounded by the replay tables: 32 per name per 10 minutes, at most 8 names, 4 connected.
     - No AresOS view bursts: the laptop home opens once per click and never resends.
     - The desktop's own room isn't affected.
   - **Stalled listing.** It only happens when `systemctl --user` doesn't answer within 5 s, and then `systemd-run` can't start apps either. The timeout's answer is safe for both sides: the desktop launches, a view is refused.
     - The hotbar can still open apps. A second desktop click on the same app joins the pending start and doesn't list again.
     - No launch storm results, and the helper carries on after each timeout.
     - The stated wording ("can delay helper replies") understates it; see nit 6.
   - Code: `os/config/usr/libexec/aresos-shell:135`, `:2613`, `:4210`

## Known limits / nits

6. **A stalled listing's delay adds up, and can trip the heartbeat checks.** Each admission blocks the serving loop for up to 5 s. Before this change, the loop made no systemd calls while serving; the watcher thread did them.
   - The 1.2 laptop home's `open_app` never joins, and a refused open leaves nothing to join. So each of its clicks pays the full 5 s during a stall.
   - Three or four queued admissions hold back the desktop's heartbeats for 15–20 s. The supervisor then shows RECOVERY `unready` (a message window) until heartbeats return, and resets its healthy-time count. The mod reconnects after 20 s without hearing from the helper; its resends replay and don't launch again.
   - The game isn't touched and nothing latches, so this is a transient false alarm under an already broken session, not real harm.
   - Suggested: reword the PLAN-GAP to say the delay is per admission and can delay heartbeat relay. Optionally give the admission listing a shorter timeout (about 1 s): both timeout answers are already safe.
   - Code: `reviews/333-open-apps/REPORT.md:199`, `os/config/usr/libexec/aresos-desktop:194`, `:2500`, `:2560`, `mod/src/main/java/dev/aresos/shell/ShellClient.java:73`, `:799`

7. **Test gap: the desktop side of the per-principal split.** No test shows that view-owned or unmapped scopes never count toward the desktop's 256. Every desktop-side test stays far below 256 foreign scopes. The code at `os/config/usr/libexec/aresos-shell:4023` is correct. One test with a patched `JOURNAL_LIMIT` and a desktop launch beside a full set of view and unmapped scopes would pin I6 at the cap.

8. **Test gap: the unreadable-list eviction branch.** `remember_scope`'s branch for an unreadable list (drop a view's name first) is untested. `os/tests/test_aresos_shell.py:639` covers only the readable branch.

9. **A launcher that exits 0 counts as ended for joins.** This covers a single-instance handoff such as Discord or a background Chrome. A second click before the handed-over window appears starts another launcher, which usually just brings up the running instance again. This is a reasonable reading of the lead's "ended", and the harm is low. `os/config/usr/libexec/aresos-shell:2509`

Read-only review. I couldn't run `git show`: my tools could only read files, and the worktree's git directory was outside what I could read. I reviewed the branch's current code and tests where REPORT.md says 6e7bbe29 and 899cabbb landed. No tests ran.

SAFE
