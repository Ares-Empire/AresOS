# Package 320: REVIEW-1 recheck (Codex gpt-6.2-sol high, read-only, fresh context, at 988b7c17, 2026-11-21)

CHANGES-NEEDED

1. **RESOLVED.** `aresos-indicator` exports `Show` in `do_dbus_register` before taking the bus name. The private-bus test exercises the real GApplication startup path and reproduced `UnknownMethod` with the old code. `os/tests/test_aresos_indicator.py:270`
2. **RESOLVED.** `aresos-level` uses a monotonic deadline, caps each ownership probe to the remaining time, and terminates and reaps a late child while holding the launch lock. `os/config/usr/libexec/aresos-level:120`
3. **NOT RESOLVED.** The harness counts process-entry logs and checks elapsed time, but it inspects `/proc` after the `flock` subprocess returns. An early unlock followed by a quick reap can still pass. Trace the notifier’s reap of the delayed PID and the launch-lock release, then assert their order. `os/tests/indicator-harness/driver.py:708`
4. **RESOLVED.** The test waits for the first read’s PID to block, verifies the second key has changed the volume, and checks that the same PID is still blocked. `os/tests/test_aresos_level.py:216`

Read-only recheck. No files changed and no tests rerun.
Lead: 1, 2 and 4 resolved. 3 (the harness asserting reap-before-unlock order from a trace, not from /proc after flock returns) is left for one small Codex fix and a recheck of it before merge; aresos-level's own ordering is resolved (2).
