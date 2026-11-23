# 54: the town arrives in one line after New home too

Board brief 307. Found in package 48's rig (`reviews/48-home-menu/REPORT.md`, the "Not verified" list).

On his first start the town says one line: "The town is built: 40 logos. /apps lists them." After New home (Flat) in the rig, the same 40 logos arrived in two lines:
- "The town is built: 32 logos";
- and 5 s later, "The town changed: 8 logos built".

All 40 stand in the end, so this is cosmetic. Still, he sees two lines for one event, and the second reads as if something changed.

**The guess in 48's report:** the staging world had generated the chunks around the start, which load at once, while the farther logos' places are generated only after the world opens. The first pass then builds only what is loaded.

**Builder:** Codex `gpt-6.1-sol`, `xhigh`: a small rule fix with a client test. **Review:** a fresh Codex `gpt-6-astra` `high` context.

## What changes

1. **Find the real cause first** and write it in the report. It may be the guess above, or something else.
2. **The rule:** a fresh home's first build says one line, as `TownLines` intends: "A first build (no logo stood, and the pass only built) is always one line, whatever the count". It must hold even when the build needs more than one pass, because places load later. Two ways to get there:
   - the first build's line waits until no place of the first build is still waiting to load, within a bound such as about 30 s, then says the total;
   - or a follow-up pass that only builds the rest of a first build adds to that build's count instead of saying "The town changed".
   - Either way: once the first build is complete, or the bound has passed, later passes speak as today.
3. **Nothing else changes:**
   - lines about something of his in the way (`WAY`) are still said one by one;
   - `/aresos hub rebuild` still says its one line;
   - ordinary changes in an existing town still say "The town changed".
   - The first start must not get slower to show its line than it is today.

## Tests

- **Unit tests** for the rule: a first build in one pass; a first build across two passes; a first build whose second pass also has a `WAY` line; a real change after the first build is complete.
- **A client game test:** New home (Flat) with the fake helper's 40 test apps gives exactly one "The town is built: 40 logos" line and no "The town changed" line. The first start's single line still holds.
- **The whole build:** `mod/dev/build.sh` twice and `mod/dev/client-test.sh` once. Put other packages' pictures back as before (`git checkout -- reviews/` for files that aren't this package's).

## Rules

- **AGENTS.md** applies.
- **The lock:** the client-test lock is shared. On exit 75, wait about five minutes and retry, at most six times.
- **Owner's files:** never touch the owner's `.minecraft`, Lunar Client or `~/AresOS-try`.
- **Commits:** end each commit with the trailer line `Codex-Model: gpt-6.1-sol xhigh`.
- **The report:** write `reviews/54-town-one-line/REPORT.md` with the cause, the fix, and the test results.
- **The PR:** push `pkg/54-town-one-line` and open a PR titled "Package 54: the town arrives in one line after New home". End its body with:

  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  https://claude.ai/code/session_015ffFyQnMDXVxFaVyNCKSXH
  ```

- **Never** merge, push to main or use `--no-verify`.
