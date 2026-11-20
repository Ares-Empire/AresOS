# 53f review fix 1

Fixes for `reviews/53f-native-home/REVIEW-1.md` (fresh Codex `gpt-6.2-sol` `high` review of PR #120, CHANGES-NEEDED).
**Builder:** a Claude Opus agent, on the same branch. Read AGENTS.md, `briefs/53f-native-home.md`,
`reviews/53f-native-home/REPORT.md` and REVIEW-1 first.

## Fix

1. **The icon decoder runs sandboxed** (REVIEW-1 finding 1, blocking; `aresos-laptop-home:195`). Follow the helper's
   icon-worker sandbox (`os/config/usr/libexec/aresos-shell` around line 1859): expose only the decoder's runtime and
   its pipes, hide the host runtime folder and the process view, no network, and enforce the output cap (512 × 512 ×
   4 bytes) **before** buffering the reply. If the sandbox tool is missing, show no icons rather than decode
   unsandboxed. Test: the child cannot open the helper socket, a file under the runtime folder, or `/proc/<parent>`.
2. **Clicks and hover only where something is painted** (finding 2). Use the painted bounds and stacking order for
   both: reject points outside the stage, let the finder's header and padding take clicks without opening anything
   behind them, and size each sign's hit box to its painted width. Tests: a click on the finder header, on a margin of
   a 2304 × 1080 window, and beside a short group sign opens nothing.
3. **Icon work is bounded** (finding 3): one worker with a bounded queue for the rows now shown; obsolete results are
   dropped; recorded failures are forgotten when the catalogue changes. Test: ten result changes start one worker and
   decode only what is shown at the end.
4. **Logo caches are pruned** (finding 4) against the current houses and hotbar slots on every town change. Add a
   memory check that types, slides, rotates finder results, clears the query and samples again at rest; the rest
   number must stay within 2 % of the first.
5. **Finder text is safe** (finding 5): no exception on any Unicode digit (`2²` searched with `2`); numeric collation
   compatible with 53c's for ties (accented names); both columns ellipsized to bounded widths as 53c did. Tests for
   each.
6. **Checks that can fail** (finding 8): the grid check requires both plot sides; the idle colour is checked against
   independent reference pixels, not the production function; the rest check counts tick callbacks; a real pointer
   click on a house makes the stand-in helper receive that house's ID; focus and reconnect run explicitly in both
   surface modes.
7. **The harness hides the host's `/run`** (finding 9): mask it before labwc starts, bind back only the fixture paths,
   and check that the private display and the stand-in helper remain reachable while the owner's sockets do not.

REVIEW-1's findings 6 (Tab and focused-button activation) and 7 (night slides at about 65 ms a frame in software)
go to the report's Known limits, one line each; the day look is the default. Carry step A's paint-break results
(commit `a58b608a`) into the report.

## Verify

Run the touched test modules by name (never the whole `os/tests`, never `test_owner_update`), headless and isolated as
before. Remeasure memory after one redraw (three runs) and update the report; the guard is `LIMIT_KIB = 64000`. After
the last push start one hosted run (`gh workflow run "OS image" --ref pkg/53f-native-home -f checks_only=true`) and
put its ID in the report. Push, then stop: never wait for or watch CI. Do not merge.
