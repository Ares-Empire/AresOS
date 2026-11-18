# 49b: the arena cap, measured again with the pass line fixed first

Board #351. A follow-up of package 49 (`reviews/49-memory-cuts/REPORT.md`, PR #107).

**Why.** In package 49, `MALLOC_ARENA_MAX=2` in the game JVM's environment was the best candidate:
- it saved about 167 MiB settled, 295 MiB after flight and 281 MiB covered;
- but its first flat trial added one 19.948 ms flight frame, while the three v1 controls stayed under 17 ms.

The data cannot tell whether that was noise or a real cost. This package answers that with an independent repeat, judged against a pass line written down before the first run.

`linux-aresos` sets the cap in `aresos-desktop-java` only if this package says QUALIFIED.

**Builder:** Codex `gpt-6.1-sol`, `xhigh`: a measurement run with a known rig and a fixed plan. **Review:** a fresh Codex `gpt-6-astra` `high` context.

## Steps

1. **Repair the rig before any measurement.**
   - Copy `reviews/49-memory-cuts/rig/` to `reviews/49b-arena-rerun/rig/`. Package 49's record stays as it is.
   - Apply the fix that 49's REPORT gives under "Before the rig is reused":
     - a bounded input helper for every command, instead of the blocking FIFO open in `measure.sh`'s `vin()`;
     - prompt failure when the input reader or the compositor is lost;
     - the exit goes through the owned-process cleanup, which frees the lock.
   - Validate it without a real game, using stand-ins: the reader dies before a standing command, the reader dies mid-flight, and the compositor dies. In each case expect a bounded non-zero exit, no process or scope of the run left, and the lock free.
   - Commit this before step 2.
2. **Write the pass line into `REPORT.md` and commit it before the first run.** Any change to it afterwards is a PLAN-GAP, and the result is then judged against the committed line, not the changed one.
   - **Safety:** package 41's line. No OOM, no `memory.events high`, and no GC pause over 50 ms after joining.
   - **Memory:** the median settled-RSS saving over the flat pairs is at least 100 MiB.
   - **Frames, flight:**
     - summed over the flat pairs, the candidate's flight frames over 17 ms number at most the controls' sum plus 2;
     - no candidate flight frame is over 33 ms.
   - **Frames, start:** in the first 30 s of a first creation, the candidate's gaps over 33 ms number at most the controls' sum plus 1.
   - **Frames, Nether glide:** no worse than the control by the same two flight rules.
3. **The runs.** The candidate is v1 plus `MALLOC_ARENA_MAX=2` in the game JVM's environment only. Everything else stays v1: heap 1024/256 MiB, G1 free ratios 30/10, MemoryHigh 2560M, distances 8/5.
   - Six flat pairs in ABBA order (control first in pairs 1, 4 and 5).
   - Two first-creation pairs.
   - One Nether-glide pair.

   That makes 18 runs of about 12 minutes each.
4. **The verdict.** Judge each rule of the committed line.
   - **QUALIFIED:** give `linux-aresos` the exact change, as 49's JUDGMENT-CALL describes it. It goes in the game wrapper's environment only, as a fixed default or through an allowlist change. Say which you'd choose and why.
   - **NOT QUALIFIED:** say which rule failed and by how much.
   - **Either way:** report the spread, and whether 49's 19.948 ms frame recurred.

## Rules

- **Package 49's rules apply** (`briefs/49-memory-cuts.md`, "Rules"). Only `reviews/49b-arena-rerun/` and this brief change, and nothing under `mod/src` or `os/`.
- **Game runs:**
  - only through the rig, under the client-test lock;
  - with 6 GiB free;
  - headless only;
  - never `./gradlew` yourself for the product, never `--force`.
- **A quiet machine matters here:** frames decide the verdict.
  - Record load, free memory and what else ran with every run, as 49 did.
  - If another builder's Gradle build or game ran during a measurement, mark that run and repeat it. Never drop a run silently.
  - Between your runs, let other lock holders through.
  - On exit 75, wait about five minutes and retry, at most six times per run.
- **Off limits:**
  - never touch `~/.minecraft`, `~/.lunarclient`, Lunar Client or `~/AresOS-try`;
  - stop only what you started, by PID or by the unit you created;
  - no sudo, and no writes under `/sys`, `/proc` or `/etc`. The arena cap needs no cgroup writes; the cover actions are not part of this package.
- **The repo is public:**
  - no personal data;
  - no Mojang assets;
  - no jars in commits;
  - keep the committed data proportionate. Package 49's size was judged reasonable at 65 attempts, and this one has 18.
- **Commits:** end each commit with the trailer line `Codex-Model: gpt-6.1-sol xhigh`.
- **The PR:** push `pkg/49b-arena-rerun` and open a PR titled "Package 49b: the arena cap, measured again". End its body with:

  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  https://claude.ai/code/session_015ffFyQnMDXVxFaVyNCKSXH
  ```

- **Never** merge, push to main or use `--no-verify`.
