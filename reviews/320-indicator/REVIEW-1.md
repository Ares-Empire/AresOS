# Package 320: REVIEW-1 (Codex gpt-6.2-sol high, read-only, fresh context, at 43fa22f5, 2026-11-21)

CHANGES-NEEDED

- **BLOCKING** `os/config/usr/libexec/aresos-indicator:393` — GApplication claims the bus name before `startup` exports `Show`. A second cold press can reach the owned name in that gap, get `UnknownMethod`, and leave the plate showing the first press’s level. Export `Show` in `do_dbus_register` before name acquisition. The unit stand-in already exports in that order, so add coverage against the real startup path. [GLib registration order](https://github.com/GNOME/glib/blob/main/gio/gapplicationimpl-dbus.c#L415-L496)
- **BLOCKING** `os/config/usr/libexec/aresos-level:135` — The final ownership probe can accept a launch after the five-second deadline. The loop also uses wall-clock time and can start a one-second probe just before expiry. Use a monotonic deadline, cap each probe by the time remaining, and terminate and reap a late child under the launch lock.
- **BLOCKING** `os/tests/indicator-harness/driver.py:678` and `os/tests/indicator-harness/driver.py:708` — The cold-launch checks count a log emitted after mapping, so an extra process that exits early can go uncounted. The deadline check samples the lock and counts a log message, which can miss an early unlock and does not measure five seconds. Log each process at entry and assert elapsed time and reap-before-unlock ordering.
- **BLOCKING** `os/tests/test_aresos_level.py:216` — The second key can run before the first background read enters its hang. Both calls can still be counted and the test can pass. Have the fixture signal that the first read is blocked, then assert the second change completes while that read is still pending.
- **BLOCKING** `reviews/320-indicator/PROGRESS.md:193` — Five new Step 1 commits carry the owner’s full name in their author metadata. Re-author those commits with a role name and a noreply address before merge.

The six `rc.xml` bindings, image checks, and `test_everyday_account.py` changed together in `9e8a7d9b`. No committed bytecode or private/game hash matches were found. The documented R29 image build remains a merge gate. This was a read-only review of the committed evidence.

**For known limits**

- `reviews/320-indicator/KNOWN-LIMITS.md:13` — A timed-out read can show an unavailable-device plate because it becomes `none`. The device change has already happened.
## Lead's triage

- Findings 1 to 4: real; fixed in one Codex fix round, then a targeted recheck of those fixes.
- Finding 5 (author metadata): not a finding. 249 of main's last 300 commits carry the same author, the owner's own GitHub account with its noreply address, and the repo's privacy hook accepts it. The owner's T433 rule covers file contents and commit messages, which are clean here (no name in any file or message).
- 'For known limits': goes into KNOWN-LIMITS.md in the fix round.
