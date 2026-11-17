# 45: Two leftovers from 39b's review

Board #260. Package 39b (merged as `49f714df`) left two SHOULD findings in `reviews/39b-hub-tidy/REVIEW-1.md` (S1, S2). This package fixes both. Nothing else changes.

**Builder:** Codex `gpt-6.1-sol`, `xhigh`: a test restructure and three doc clauses against a tight brief. **Review:** a fresh Codex context, `gpt-6-astra`, `high`.

## S1: the no-mob test's tick-counted ground wait

`FlatHomeGameTests` (`mod/src/gametest/java/dev/aresos/test/FlatHomeGameTests.java`): the test whose `maxTicks` is `LOAD_LIMIT + CONTROL_LIMIT + TEN_MINUTES + 40` waits for the ground around home through `helper.onEachTick`, and fails with "Fixture: the ground around home did not load within 6000 ticks" once 6,000 ticks have passed. Under load, ticks can run very fast while chunk work starves (board #257), so this fails now and then for the wrong reason.

Fix it as REVIEW-1 S1 says. The report's first idea (making only the ground wait a sequence step) does not work, because `onEachTick` after it still registers one callback per tick up to the limit. Do one of these:
- make the ground wait, the control and the quiet ten minutes sequence steps (`thenWaitUntil` and the like, throwing `GameTestAssertException` until each is done); or
- a runnable that registers itself again with `runAtTickTime(tick + 1)`.

Then bound the ground wait by time on the clock (as `ChunkWaits` does elsewhere in the tests), not only by ticks, and raise the tick limit so that only the clock bound can fail it. Keep what the test proves unchanged: the control (a mob does appear where spawning is allowed) and the quiet ten minutes at home.

Check: the test passes, and it fails with its own message when you break the fixture on purpose (for example, no ground), once, locally. Say in the report how long its run takes before and after.

## S2: a third case where a logo keeps its old look

`docs/design/HUB.md` (section 2.5, "the first visit with converter 2"), the same text in the summary near the top of HUB.md, and `mod/README.md` (the renewal paragraph) say every standing logo is drawn again "with two exceptions". The code (`TownKeeper`, the renewal pass; its `rebuild` javadoc states it) has a third: a logo that something of his rests on (a torch on its doormat) stays as it was until he takes that away, and the game says so once.

Add that clause in the three places. Also change "a block of his in it" to "something of his in its place" where the code means the layer in front, the sign's space above or the way in as well. Read the code to confirm the wording before you write it.

## Rules

- `AGENTS.md` applies. Worktree `~/AresOS-45-hub-leftovers`, branch `pkg/45-hub-leftovers`, from main. Before the hosted checks, merge `origin/main` into the branch (an "OS image" fix landed on main on 2026-11-15).
- Tests on the laptop only through `mod/dev/build.sh` and `mod/dev/client-test.sh` (one game at a time, the lock, 6 GiB free). Never `./gradlew` yourself, never `--force`. Never the whole `os/tests` suite on the laptop.
- Headless only, never `WAYLAND_DISPLAY=wayland-0`. Never touch `~/.minecraft`, `~/.lunarclient` or Lunar Client. Stop only processes you started, by PID.
- The repo is public: no personal data, no names of the owner's installed programs beyond those the tests already use.
- Report in `reviews/45-hub-leftovers/REPORT.md`. Open a PR "Package 45: two leftovers from 39b's review". Never merge, never push to main, never `--no-verify`.
