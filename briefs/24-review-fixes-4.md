# 24: review fixes, round 4

Follow-up on `pkg/24-interface-v1` (PR #33). Read `reviews/24-interface-v1/REVIEW-4.md` (CHANGES-NEEDED; three P2s, all in scope watching after a restart). Four rounds have circled this one area, so restructure it rather than patch it:

1. **One watcher, off the event loop.**
   - A single background thread checks every unresolved launch's scope with **one** batched call per pass, e.g. `systemctl --user list-units --type=scope --all --no-legend --plain` (or `show` with several unit names), never one `systemctl` per scope.
   - It posts results back to the event loop through the existing wake-up path. Socket replies and compositor events are never delayed by it.
   - Schedule the next pass from the **end** of the previous one.
2. **Three answers, not two.**
   - A scope is `active`, `gone` or `unknown`. A timeout, an execution error or unparsable output is `unknown`.
   - Unknown keeps the launch and its watch, and retries next pass.
   - Only `gone` closes, fails or settles a launch.
3. **Watch everything unresolved when tracking is unavailable.**
   - Whenever window tracking is off, every unresolved launch is watched, `focused` and `background` included, whether it came from before the restart or not.
   - When tracking is on, keep the current window-based rules.
4. **Tests:**
   - responsiveness while a scope check is slow: a reply arrives while the watcher is blocked;
   - a transient error then recovery: the launch is untouched, then closed only after a real `gone`;
   - tracking lost after a restart, then the app exits, the replay ID is retained, and capacity recovers;
   - the batched call parses `active`, `gone` and `unknown` correctly.

Same rules and resource gates as before. Add a "Review fixes 4" section to the REPORT, then push.
