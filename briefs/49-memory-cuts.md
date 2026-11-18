# 49: Measuring the home screen's memory cuts

Board #282's memory follow-up. Empire brief 300.

The owner, 2026-11-16: "1.2 gb is a lot for a homescreen. Is there any way to optimize it? It's our own OS so I think there might be a way to do it somehow? Maybe put an agent to investigate and see if other people have done it and if we can do it because that would really help."

The research is done: `reviews/49-memory-cuts/RESEARCH.md` (2026-11-16, Claude Opus with two research agents, no game runs). Its estimates:
- the world visible: from about 1.2 GiB to about **1.0 GiB**;
- covered by an app: about **0.6 to 0.8 GiB** resident;
- a floor of about **0.85 GiB** while it draws.

Most of these numbers are estimates. This package measures them with package 41's rig and says which measures to ship.

**Builder:** Codex `gpt-6.1-sol`, `xhigh`: rig scripts, long measurement runs and tables against a written plan. **Review:** a fresh Codex context, `gpt-6-astra`, `high`.

## What to measure

Follow RESEARCH.md section 7 ("Draft plan for a measuring package") and section 2's table. In short:

1. **Rig additions** (`reviews/41-home-memory/rig/`, copied to `reviews/49-memory-cuts/rig/` so package 41's record stays as it was):
   - `ENV=` and `MODS=`;
   - `PROBE=1`: trim, GC and heap info, the smaps classes, majflt;
   - `RECLAIM=` and `FREEZE=1` in the cover phase, with a 10 s wake-up frame window after the cover ends;
   - `LONG=`, and `NMT=0`;
   - `memory.swap.current` and zram's `mm_stat` in every snapshot.

   The rig's game scope is your own. `memory.reclaim` and `cgroup.freeze` only ever touch the rig's scope, never the owner's session or anything you didn't start.
2. **Step 0, two runs:** the probe run (`PROBE=1`, `COVER=300`), and a `LONG=20` run with the world visible and idle, for the NVIDIA 10-minute allocation (RESEARCH 4.3).
   - **Gate:** if the trims give back under 30 MiB at every snapshot of the probe run, skip measures 1(c) to 1(e) and say why.
3. **Single factors against a fresh v1 baseline,** two runs each, alternating with the baseline:
   - compact object headers;
   - plus string dedup;
   - `TrimNativeHeapInterval`;
   - plus LWJGL's `allocator=system`;
   - `MALLOC_ARENA_MAX=2`;
   - fewer threads.
4. **FerriteCore 9.0.0,** two runs, after the mod's client tests pass with it.
   - Download it from Modrinth into your worktree only, and record its SHA-512 and licence (MIT).
   - Shipping it in the image is not this package's decision. If it earns its place, it's a JUDGMENT-CALL in the report.
5. **Covered,** two runs each: none / GC and trim / plus `memory.reclaim` 300M / 600M / plus freeze. Record:
   - the resident memory while covered;
   - the zram use;
   - majflt;
   - the wake-up frames (worst frame, frames over 17 and 33 ms).
6. **The winners combined,** against package 41's pass line: no OOM, a GC pause of 50 ms at most after joining, no `memory.events high`, frames no worse than v1. Run:
   - flat ×3;
   - one first creation;
   - the Nether glide;
   - `LONG=20` once;
   - one `NMT=0` run for the number to report.

About 35 runs, each about 12 minutes. Stop early where the research's own stop rules say so.

## What the report gives

- **A results table** per measure: measured saving and spread, against the research's estimate.
- **The recommended set, with:**
  - the visible and covered numbers;
  - the start time;
  - the frames;
  - the wake-up after a cover.
- **What `linux-aresos` would change** in the supervisor and image:
  - JVM arguments;
  - environment variables;
  - the cover actions (when, what, and their limits).

  Their side builds it, so this package changes nothing under `os/`.
- **What the mod would change**, if anything (for example a jemalloc purge when covered). Describe it; don't build it here.
- **Which research claims held and which didn't** (RESEARCH section 8).

## Not in this package

- The laptop home's memory (RESEARCH section 6). It goes into the laptop home's build brief.
- Shipping anything: settings, mods, supervisor steps.
- The Vulkan back end and OpenJ9. Mention them only if step 0 or 3 gives a reason.

## Rules

- **Setup:** `AGENTS.md` applies. Worktree `~/AresOS-49-memory-cuts`, branch `pkg/49-memory-cuts`, from main. Merge `origin/main` into the branch before the hosted checks.
- **What changes:** only `reviews/49-memory-cuts/`. Nothing under `mod/src` or `os/`. A rig-only Gradle init script, as package 41's `jvm41.gradle`, is fine.
- **Game runs:**
  - Only through the rig under the client-test lock, or `mod/dev/client-test.sh`: one game at a time, 6 GiB free.
  - Never `./gradlew` yourself for the product, never `--force`. Never the whole `os/tests` suite.
  - Other builders share the lock; between runs, let theirs through.
  - Measurements are noisy while other programs run: record what else ran (load, free memory) with every run, as package 41 did.
- **Headless only**, never `WAYLAND_DISPLAY=wayland-0`.
- **Off limits:**
  - Never touch `~/.minecraft`, `~/.lunarclient`, Lunar Client or `~/AresOS-try`.
  - Stop only processes you started, by PID.
  - No sudo, no installs outside your worktree.
  - No `rpm-ostree`, `bootc` or `ostree`.
- **The repo is public:** no personal data, no Mojang assets, no game jars in commits (record hashes instead).
- **Report** in `reviews/49-memory-cuts/REPORT.md`.
- **Finish:** open a PR "Package 49: measuring the home screen's memory cuts". Never merge, never push to main, never `--no-verify`.
