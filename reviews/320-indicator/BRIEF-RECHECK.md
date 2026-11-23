# Brief 320: targeted Codex recheck of findings 1 to 3 (gpt-6.2-sol high, read-only, at 1eed5a08, 2026-11-21)

BLOCKED

1. **RESOLVED** — The change lock has a one-second wait limit and is released before read-back or notification. Children inherit no change-lock descriptor. The brief requires a test that changes the level with a second key while the first read-back hangs. `briefs/320-indicator.md:47,62`
2. **NOT RESOLVED** — Sequence numbers handle reordered updates, but the launch lock can be released after two seconds while the detached indicator is still starting. A waiting notifier can then start a second program. Keep the launch lock until the first child owns the bus name or, on timeout, terminate and reap that child before unlocking. Add a cold-launch test that delays bus-name ownership past the deadline. `briefs/320-indicator.md:37,73`
3. **RESOLVED** — The brief forbids the normal-window fallback used by laptop home. It requires exit before mapping if layer-shell support or passive setup fails, and tests that an importable but unsupported library produces no toplevel or keyboard leave. `briefs/320-indicator.md:41,50,62,67`, `os/config/usr/libexec/aresos-laptop-home:598`
Lead (2026-11-21): finding 2's remaining gap is fixed in the brief with the recheck's own fix (the launch lock is held until the started program owns the name, or that program is ended and reaped first), plus a test that delays the name past the deadline. Low harm with GApplication's single instance as a backstop, so no further recheck (one review, then build; brief-review rounds rule).
