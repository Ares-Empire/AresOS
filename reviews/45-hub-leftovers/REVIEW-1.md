No blocking, should-fix, or nit findings identified at `83ab68da`.

- **Control and quiet interval remain meaningful.** [FlatHomeGameTests.java:429](/var/home/ares/AresOS-45-hub-leftovers/mod/src/gametest/java/dev/aresos/test/FlatHomeGameTests.java:429) requires a recorded mob addition before applying the home rules and resetting the counter. It then checks cumulative additions for 12,000 ticks—ten minutes of game time—and retains the final fixture checks. Mobs removed between callbacks still count.
- **Scheduling is bounded in memory.** Each callback schedules one fresh wrapper. That avoids the framework deleting the next invocation when it removes the current callback. The wrappers call the original runnable; they do not form an accumulating call chain.
- **The ground wait uses the clock.** The 120-second `System.nanoTime()` deadline replaces the 6,000-tick deadline. Failure restores state and passes the fixture message to `helper.fail`. The retained negative-run log confirms that exact failure at 644,985 ticks, below the framework ceiling. As with `ChunkWaits`, checking the deadline requires the server to keep ticking.
- **All three documentation edits match the requested behavior.** Unloaded logos wait; rebuild obstructions preserve the owner’s objects and move the logo onward; objects preventing removal leave the old logo standing, with a deduplicated message. The broader “something … in its place” wording covers the front layer, sign space, and entrance.

The retained logs corroborate both successful runs and the deliberate broken-fixture failure recorded in the report. I ran no build, Gradle, client test, or game, and changed no files.

SAFE