# 54, review fix 1: a real move ends the first build's count, and the wait is short

`reviews/54-town-one-line/REVIEW-1.md` (Codex `gpt-6-astra` `high`, head `b0dfb695`) confirmed several things:
- the cause, which the staging world's logs show;
- the unit and client scenarios;
- per-server cleanup and the bounded expiry;
- that `WAY` lines and `rebuild` still behave as before.

It found two problems.

**Builder:** Codex `gpt-6.1-sol`, `xhigh`. **Review:** a fresh Codex `gpt-6-astra` `high` context, checking only this fix.

## What changes

1. **A real move can't hide inside the first build (blocking, `TownLines.java:94`, `TownKeeper.java:434`).**
   - **The gap:** a catalogue category change can move an already built app without changing its ID. If the old logo comes down while the new place is unloaded, the pass emits neither `DOWN` nor `MOVED`. The later build then counts as `BUILT` inside the first build, so the town can say "41 logos" for 40 apps and swallow the move.
   - **The fix:** the first build's collection ends as soon as a real move or renewal begins, even when its rebuild is deferred. That operation keeps its kind (`MOVED`/`RENEWED`) across retries, so it is said as a change once it completes.
   - **The test:** a keeper regression where the ID set is unchanged and the category changed, the destination is unloaded and the move completes later. Expect a first-build line with the true count, then one "The town changed" line naming the move.
2. **The first line's wait (should-fix, `TownLines.java:100`, `TownArrivalClientGameTest.java:158`).**
   - **The lead's decision (2026-11-18):** a short wait for one true line is better than an early partial line and a second one. The brief's "no slower" is replaced by a bound.
   - **The bound:** cut the wait from 600 ticks to **200 ticks (10 s)** from the first pass that builds. When every place of the first build has been built, say the line at once. When the bound passes, say what stands and let later passes speak as they do today.
   - **Docs:** say this in the report, and update the brief's line in the report's "Rules met" or equivalent.
   - **The test:** a controlled partial-loading first start, where some places load at tick 3 and the rest at about tick 100. Assert one line with the full count by tick 200 and no "The town changed". Add a second case where some places never load: one line with what stands at about tick 200, and later builds said as changes.

## Tests and rules

- **Builds:** `mod/dev/build.sh` twice and `mod/dev/client-test.sh` once. Put other packages' pictures back as before.
- **The shared lock:** package 49b's memory measurements also use the client-test lock today, and frame timings decide their verdict.
  - Before each `mod/dev/build.sh`, check that the lock is free with `/usr/bin/flock -n ~/.cache/aresos-dev/client-test.lock true`. If it's held, check again every minute; its runs take about 12 minutes.
  - On exit 75, wait about five minutes and retry, at most six times.
- **Commits:** end each commit with the trailer line `Codex-Model: gpt-6.1-sol xhigh`.
- **Where it goes:** merge origin/main first if it has moved. Push to `pkg/54-town-one-line` and comment on PR #108.
- **Never** merge, push to main or use `--no-verify`.
