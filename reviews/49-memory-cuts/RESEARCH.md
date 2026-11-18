# Home-screen memory: what others did, what we can do (research, 2026-11-16)

Research and reading only. No game was run: another builder held the game lock. Claude Opus 5.5 did the work, with two research agents (memory mods; WebKitGTK and native drawing). The baseline is package 41 (`reviews/41-home-memory/REPORT.md`, `REVIEW-3.md`) and the settings going out with 23d: `HEAP_MB 1024`, `MIN_HEAP_MB 256`, `-XX:MaxHeapFreeRatio=30 -XX:MinHeapFreeRatio=10`, `MEMORY_HIGH 2560M`, render 8 / simulation 5.

Every number carries a label:
- **measured (pkg 41):** package 41's runs and snapshots, re-read here.
- **measured (study 44):** the laptop-home study.
- **measured (here):** a read-only check on this laptop, or the WebKit agent's headless measurement.
- **published:** a source in section 9.
- **estimate:** my reasoning, which is given with it.

## 1. Bottom line

- **The world while visible.** Today's settings measured RSS 1194 MiB settled, 1304 after the flight and 1282 covered (pkg 41, v1). The safe measures (2.1 to 2.6 below) should bring it to **about 1.0 GiB visible**, 0.95 to 1.05 (estimate). The biggest single item is uncertain: memory the game already freed and the allocators keep, 50 to 200 MiB. One probe run settles it.
- **The world while covered.** This is where the OS can do more than the game. A GC, a native trim and `memory.reclaim` on the game's scope while an app covers it: **about 0.6 to 0.8 GiB resident**, plus 0.1 to 0.15 GiB in zram (estimate). Freezing the covered world goes further, to **0.2 to 0.4 GiB resident**, but needs supervisor work.
- **The floor.** While it draws, a Minecraft home cannot go much below **about 0.85 GiB** (section 5). It is a whole Minecraft (all its classes, registries, every block model, the integrated server), a JVM and a GPU driver; the flat world itself is cheap. Getting under that would mean changing how Minecraft loads its models (ModernFix's "dynamic resources"), and there is no maintained Fabric build of that for 26.x.
- **The laptop home.** The 335 MiB is mostly the NVIDIA libraries that every process loads, not WebKit:
  - Pinning EGL and Vulkan to Mesa/Intel takes the bare engine from 356 to about 150 MiB PSS (anon 181 to 85; measured here).
  - Keep WebKit for the companions, with the pinning. A native street (37 MiB PSS measured here) pays only if the companions never run on Linux.

## 2. Ranked measures for the world

Baseline: v1-recommended (pkg 41), at RSS 1194 settled, 1304 after the flight, 1282 covered for 5 min. "Rig" means package 41's `rig/run.sh`. Today it takes JVM flags through `GC=` (comma-separated). The new keys this plan needs are in section 7.

| # | Measure | Expected saving (MiB) | Source / reasoning | Confidence | Effort | Risks | How to measure with the rig |
|---|---|---|---|---|---|---|---|
| 1 | **Give back native memory the game already freed.** Trim glibc (`-XX:TrimNativeHeapInterval=60000`, or `jcmd <pid> System.trim_native_heap` once after joining and on cover). Then either LWJGL's allocator on glibc (`-Dorg.lwjgl.system.allocator=system`) or a jemalloc purge on cover (`je_mallctl("arena.4096.purge")` from the mod). Optionally `MALLOC_ARENA_MAX=2`. | 50 to 200 visible, mostly after flying | Section 3: v1's native part outside NMT went 285 → 379 after the flight and was still 369 after 5 min covered. f1 at the same settings had 138 to 158. NMT shows a malloc peak of 140 against 90 now, and compiler arenas that peaked at 91 MB. | low-medium | low (flags, wrapper env, a few mod lines) | `malloc_trim` locks arenas for milliseconds. glibc instead of jemalloc may mesh a little slower under contention. Start-up unchanged. | Step 0: run the jcmd trim inside a v1 run (it prints the RSS change) and classify smaps. Then single-factor runs: `GC=-XX:TrimNativeHeapInterval=60000`, plus `-Dorg.lwjgl.system.allocator=system`, plus `ENV=MALLOC_ARENA_MAX=2`, 2 runs each. Compare "anon minus NMT" and its spread. |
| 2 | **Compact object headers** (`-XX:+UseCompactObjectHeaders`) | 30 to 60 | JEP 519: 10 to 20 % heap; Amazon 22 % on SPECjbb (published). Mojang's own launcher adds it since 26.1 (published, minecraft.wiki). Live heap 250 to 410. | medium | one `JVM_ARGS` word; check that the image has `classes_coh.jsa` | Low: Mojang ships it to everyone on 26.x. Without the COH CDS archive: slower start and about 14 MiB more. | `GC=...,-XX:+UseCompactObjectHeaders`, 2 runs plus one creation (f1-like). Compare live heap after GC (gc.txt) and committed heap. |
| 3 | **Reclaim a covered world**: after about 30 s covered, `jcmd GC.run`, the trims from #1, then `memory.reclaim` with `swappiness=max` on the game's scope | 300 to 600 resident while covered; 200 to 450 net after zram (3 to 4 : 1) | cgroup-v2 docs; Meta TMO 20 to 32 % (published). What a paused world touches at 10 fps is small (estimate). | medium-low | medium (supervisor step on cover; writable by the user, measured here) | Wake-up: faults on return, est. 0.1 to 0.3 s of uneven frames. A G1 concurrent cycle pulls the heap back. The full GC pause is invisible while covered. | New `RECLAIM=` in the cover phase: snapshot every minute with `memory.swap.current`, zram `mm_stat` and majflt. After the cover ends, a 10 s frame window (worst frame, frames over 17/33 ms). Variants: none / GC+trim / plus reclaim 300M / 600M; 2 runs each. |
| 4 | **FerriteCore 9.0.0** (26.1 to 26.3, MIT) | 15 to 45 | Only modpack figures are published (All of Fabric 3: heap 1792 → 984 MB). On 26.x it no longer touches models: block-state neighbour table, property map, shape dedup, data-component patch (published). Vanilla has far fewer states (estimate). | low | low-medium: pin the jar plus its hash in `desktop.lock.json`, run the mod's tests | Mods that read state internals crash. Opt-outs per option go in `fabric.mod.json`. | New `MODS=` (`-Dfabric.addMods`), 2 runs, live heap; the client tests with it. |
| 5 | **Fewer threads** (`-XX:ParallelGCThreads=4 -XX:ConcGCThreads=1 -Dmax.bg.threads=4`, or `-XX:ActiveProcessorCount=4`) | 10 to 40 | 64 threads in v1. 13 + 3 GC and 12 compiler threads (measured here, JDK 25 ergonomics). Each brings queues, malloc and jemalloc caches (estimate). | low | low | GC pauses about 2× (today ≤ 14 ms). Slower meshing of new ground. | `GC=` single factor, 2 runs; check GC pauses and the flight's p99 and worst frames. |
| 6 | **String deduplication** (`-XX:+UseStringDeduplication`, Mojang's default too) | 0 to 20 | Mojang's 26.1 launcher flags (published); no number. | low | one word | One more concurrent thread. | Pair with #2 as "Mojang's flags without the two that raise footprint". |
| 7 | **Freeze a covered world** (`cgroup.freeze` after #3) | 700 to 1000 resident while frozen (200 to 300 of it in zram); plus the covered world's 8 to 10 % of a core and its GPU use | cgroup-v2 docs; Android's cached-apps freezer (published). Estimate. | low | high: supervisor heartbeat (`HEARTBEAT_GAP` 20 s), helper messages, Wayland pings and buffer, PipeWire underrun, time jump | Wake-up est. 0.3 to 1 s uneven. A missed thaw looks like a hung world. | Rig only: `FREEZE=` freezes the rig's own game scope after the reclaim, thaws at cover end, measures frames and majflt. The supervisor side is a design for the OS lead. |
| 8 | **Prism Launcher's own memory**: it stays resident as the game's parent for the whole session | unknown; est. 60 to 150 RSS | Never measured: the rig uses Gradle's dev client. | — | measure only | — | Product check on the laptop (section 7, step 5): PSS of `prismlauncher` in its scope. |
| 9 | Shenandoah, `compact` heuristic | -50 to +50 | Uncommit after 1 s and a guaranteed cycle every 30 s (measured here in JDK 25's flags). More GC CPU (published). | low | low | The 30 s guaranteed cycle touches the whole heap: it works against #3. Frame effect unknown. | `GC=-XX:+UseShenandoahGC,-XX:ShenandoahGCHeuristics=compact`; one exploratory run. |
| 10 | C1 only (`-XX:TieredStopAtLevel=1`) | 30 to 70 | Code cache 61 and C2 arena peaks of 75 to 91 MB in NMT (pkg 41). | low | low | Slower code: standing CPU (36 % of a core) rises, frame headroom falls. | A probe run only. |
| 11 | OpenJ9 (Semeru 25) | 100 to 300 | Vendor claims 31 to 66 %; an independent test 28 %. Minecraft guides say less memory but slower and more stutter (published). | low | high: a second Java in the image; no NMT, so the rig changes | Untested with Fabric/LWJGL 26.x. | Only after 1 to 7; one exploratory run. |
| — | Rejected or no gain | | | | | | |
| | Render distance 5 (40 apps) | 0 to 50 | 6 measured = 8; 4 saved 50 to 130 (pkg 41); his 61 programs need 7. | | | The town does not fit. | — |
| | World on the Intel chip | RAM worse: +200 to +500 | An iGPU keeps buffers in system RAM (shmem GEM objects, published). The world holds 306 MiB (flat) to 604 (Nether) on the RTX 4060 (pkg 41); about 60 to 80 MiB of NVIDIA library pages would go (estimate). | | | A power question, not a memory one. | — |
| | ZGC, Serial, Parallel | worse / freezes | ZGC: no compressed oops and needs headroom. Serial and Parallel: full GCs of 300 to 400 MiB take hundreds of ms. | | | | — |
| | AOT cache / CDS (JEP 483/514/515) | 0 to 15 | Only built-in-loader classes; Fabric's Knot loader excluded (published). | | | | — |
| | ModernFix | n/a | No official Fabric 26.x. The unofficial mVUS fork (LGPL-3.0) is unverified, and its dynamic resources are unknown (published). | | | | — |
| | Sodium | not a RAM mod | No RSS-vs-vanilla data. Replaces the block and fluid renderers; vanilla rendering mixins break. PolyForm Shield (published). | | | | — |
| | Entity Culling | — | Its licence forbids redistributing the jar (published). | | | | — |
| | KSM | < 20 | One JVM has few identical pages; ksmd costs CPU (published docs; estimate). | | | | — |
| | Smaller textures, `mipmapLevels:0`, sounds, particles | ~0 RAM | Atlases live in GPU memory after upload; sounds load on demand (estimate). | | | Looks worse. | — |
| | Removing the unifont font | ~10 | ModernFix's figure (published). | | | Breaks non-Latin glyphs in app names. | — |

Calibration: the rig runs with `-XX:NativeMemoryTracking=summary`, whose own bookkeeping is 10 MiB (pkg 41's NMT). The product does not, so its numbers sit about 10 MiB lower than the rig's for the same settings.

## 3. Where the 1.2 GiB sits, and what package 41's data shows that its report did not use

v1-recommended, settled (measured, pkg 41: `runs/v1-recommended/snap-settled.json`, `nmt-settled.txt`):
- Java heap committed: 385 (live after GC: 250 to 410).
- Metaspace 119, class space 23, code cache 61 (47 + 14 malloc), G1 structures 68 (28 malloc + 40 mmap).
- Symbols 23, CDS 14, threads 7 (64 threads), NMT itself 10, other about 10.
- Anonymous memory outside NMT: **about 285**.
- Mapped files 143 (`RssFile`) and shared memory 54 (`RssShmem`).
  - The shared memory is probably the NVIDIA driver's `/dev/nvidiactl` mappings. A running dev client showed 59 MiB resident in 31 `nvidiactl` maps (measured here, read-only, another builder's test client); this is an inference.

**The native part grows and does not come back.** Anonymous RSS minus NMT committed (CDS excluded), from pkg 41's snapshots:

| Run (23d settings) | Settled | After the flight | Covered 5 min |
|---|---|---|---|
| v1 | 285 | 379 | 369 |
| c4 | 302 | 365 | 357 |
| f1 (world created in that game) | 155 | 158 | 138 |

- **After the flight about 85 to 95 MiB stays.** He is back over home with the same chunks in view, and 5 paused minutes give none of it back.
- **NMT itself shows freed C-heap that glibc may keep.** Malloc peaked at 140 MB against 90 now, and the compiler's arena chunks peaked at 91 MB.
- **Minecraft 26.2 allocates its vertex buffers through LWJGL's `MemoryUtil`.** Measured here: `ByteBufferBuilder` holds `MemoryUtil.getAllocator`.
  - LWJGL's default allocator is its bundled jemalloc (published).
  - 26.2 lists `lwjgl-jemalloc 3.4.1`, and the running dev client maps `libjemalloc.so` (measured here).
- **jemalloc gives dirty pages back by a decay that runs only on allocation activity.** A quiet arena keeps them (published: jemalloc issue 1398). Its default is 4 arenas per CPU, so 64 here.
- **This fits package 41's run-to-run native spread** of about 150 MiB. It is a hypothesis; step 0 of the plan tests it in one run.

**Checked: the game loads no Mesa.** The running dev client draws through GLX with only NVIDIA's libraries mapped: no `libgallium`, no EGL vendor library, no Vulkan driver (measured here). So the vendor pinning that halves the laptop home has nothing to remove in the game, at least on this path.

## 4. The areas in detail

### 4.1 Memory mods (agent report; every claim has its URL in section 9)

**FerriteCore**
- The only maintained Fabric memory mod for 26.2: `9.0.0-fabric`, 2026-03-24, tagged 26.1 to 26.3. Fabulously Optimized 14.1.2 ships it on 26.2.
- Since 8.0.0 (1.21.5) every model optimisation is gone: "the model system has been rewritten entirely".
- What is left:
  - the block-state neighbour table and the property map;
  - deduplicated shape caches;
  - the data-component patch;
  - two opt-ins: a small `ThreadingDetector` (10 to 15 MB, doubled in singleplayer, off because of rare races) and `compactFastMap`.
- Published savings are for modpacks only: All of Fabric 3, heap 1792 → 984 MB. No vanilla figure exists. Savings scale with the number of block states, so on vanilla expect tens of MiB at most (agent's and my estimate).
- MIT: bundling is allowed with the notice.
- Conflicts: a mod that reads the state neighbour table directly crashes, and custom StateHolder classes broke once (issues 152, 211). Ordinary `getValue`/`setValue` is fine. A mod can opt out per option with `"custom": {"ferritecore:disabled_options": [...]}`.

**ModernFix**
- No official Fabric build for 26.x. The author, 2026-05-03: "I do not have time and energy to maintain support for two loaders anymore."
- An unofficial mVUS fork has 26.2 Fabric (LGPL-3.0-only). The author can't vouch for it, and whether its dynamic resources work is unverified.
- Its big saving, `dynamic_resources`, is from a modded pack: 1.7 GB → 945 MB. Its unihex font fix saves 10 MB. Not for us now.

**Others**
- Sodium:
  - no RSS figures against vanilla;
  - replaces vanilla's block and fluid renderers, so mixins there break (lead dev, issue 3810);
  - replaces the video settings screen;
  - PolyForm Shield licence.
- Dynamic FPS (MIT) does what the AresOS mod's covered pause already does.
- No memory effect: ImmediatelyFast, Lithium, C2ME, Krypton.
- Obsolete: LazyDFU, Memory Leak Fix (leaks fixed by Mojang in 1.20.5+), Smooth Boot, Starlight.
- Entity Culling's licence forbids redistribution.

**Low-RAM setups**
- ModernFix's "Ultra-Low Memory Footprint" guide (1.18.2, author-tested): Fabric, FerriteCore, Sodium and ModernFix with dynamic resources and other options, render ≤ 4. Singleplayer at a **192 MB heap**. That is what a model-loading rewrite buys.
- Raspberry Pi 4 (1.16/1.18): 1500 MB heap, Sodium, render 2 to 3, mipmaps 0, clouds off, 10 to 15 fps; no RSS measured.
- Steam Deck and kiosk guides: nothing on memory.
- No sourced idle RSS for a vanilla 1.20+/26.x client exists.

**Mojang's own defaults (26.1)**
- The official launcher allocates 4 GB. It uses ZGC "for compatible computers" and adds `-XX:+UseCompactObjectHeaders -XX:+AlwaysPreTouch -XX:+UseStringDeduplication` (minecraft.wiki; 26.2's version JSON carries none of these, so Prism never passes them).
- For us: take compact headers (and maybe string dedup). Avoid AlwaysPreTouch (it commits all of `-Xms`) and ZGC.
- 26.1 also added a `detailed_memory` debug entry (F3), useful for checking by eye.

### 4.2 The JVM on Java 25

**Compact object headers**
- A product flag in 25 and the default from JDK 27 (JEP 534). Headers go from 12 to 8 bytes.
- Published savings: 10 to 20 % (JEP), 22 % heap and 8 % CPU (Amazon, SPECjbb2015), 5 to 10 % (Alibaba).
- No Minecraft measurement exists, but Mojang's launcher turns it on, which settles compatibility for vanilla 26.x.
- Needs `classes_coh.jsa` for CDS. Temurin 25.0.5 has it (measured here). Fedora's `java-25-openjdk` is not verified: run `ls /usr/lib/jvm/java-25-openjdk/lib/server/` in the image. If it is missing, the Containerfile can create it with `java -XX:+UseCompactObjectHeaders -Xshare:dump` (JDK-8357881).

**Trimming native memory**
- `TrimNativeHeapInterval` has been a product flag since 22.0.1 (JDK-8325496) and is `{product}` in JDK 25 (measured here).
- `jcmd System.trim_native_heap` (since JDK 18) trims once and prints the RSS change.
- Stuefe's motivating case: 8.5 GB → 900 MB. malloc_trim locks each arena while it runs; it took 800 ms only with over 32 GB to reclaim (published).

**`MALLOC_ARENA_MAX=2`** (or `GLIBC_TUNABLES=glibc.malloc.arena_max=2`)
- The classic fix for JVM native bloat: Heroku, Presto, several write-ups. Results vary, and one Ruby benchmark used more memory with it.
- It is an environment variable, so it goes in `aresos-desktop-java`, not in Prism's `JvmArgs`.

**LWJGL's allocator**
- `org.lwjgl.system.allocator` = `jemalloc` | `rpmalloc` | `system` (LWJGL `Configuration`).
- With `system`, the trims cover the chunk buffers too.
- Keeping jemalloc: purge all arenas through LWJGL's `JEmalloc.je_mallctl` when the world is covered.
- The bundled jemalloc is built with the `je_` prefix, so a config variable would be `JE_MALLOC_CONF`. That is unverified for LWJGL's build.

**Threads**
- Minecraft 26.2's `Util` reads `max.bg.threads` (measured here, string in the class; Paper's patches show the logic).
- JVM on 16 threads: CICompilerCount 12, ParallelGCThreads 13, ConcGCThreads 3 (measured here).
- `-Xss` is no lever: 64 threads commit 7 MiB.

**AOT cache (JEP 483/514/515)**
- Classes from user-defined loaders are a non-goal. Custom-loader support was a January 2026 leyden-dev design discussion, not shipped.
- Fabric's Knot loads Minecraft and all mods, so only the JDK and the class path would be cached. Start-up only; memory roughly neutral.
- Creating the cache needs twice the heap (inside.java).

**Garbage collectors**
- G1's automatic heap sizing is a draft JEP, and G1 `SoftMaxHeapSize` was withdrawn in January 2026: neither is in 25.
- ZGC uncommits after 300 s by default and does not compress oops; Minecraft guides warn it raises RAM.
- Shenandoah `compact`: uncommit delay 1000 ms, guaranteed GC 30 s, garbage threshold 10 (measured here in JDK 25 flags).

**OpenJ9**
- Semeru 25 (OpenJ9 0.55) has been GA since 2025-09.
- Footprint claims: 31 to 38 % (DayTrader8) up to 66 % (vendor); an independent small test found 28 %.
- Minecraft guides: less memory, much slower at chunk generation (over 30 %), more frame swings.

### 4.3 Game settings

- **Little RAM to gain.**
  - Render 6 measured the same as 8, and 4 doesn't fit the town (pkg 41).
  - A superflat chunk is a few single-value sections, so the world's chunks are small even twice over (client and server; estimate).
  - The live heap is the game's registries and every baked model, which no option drops.
- **Graphics API option** (`preferredGraphicsBackend` in 26.2's Options, measured here).
  - Default means OpenGL in 26.2; Vulkan is "experimental" and becomes the default in 26.4 (secondary sources).
  - Vulkan's memory with NVIDIA is unknown: a separate experiment.
- **Risk to check: NVIDIA 610/615 `CPMMListener`.**
  - On Linux, a thread in `libnvidia-glcore` wakes exactly 10 minutes after launch and mallocs 250 MB (vanilla Unity game) to many GB (heavily modded), on 610.57.04 and 615.71.09.
  - Vulkan avoided it; `__GL_THREADED_OPTIMIZATIONS=0` did not; NVIDIA has not answered (forum).
  - Ours is 615.78.08 (measured here). Package 41's runs were about 10 minutes, so they may have missed it. One 20-minute run settles it.

### 4.4 The OS side

**Measured here (read-only)**
- zram0: 7.8 GiB, zstd, priority 100. It comes from the image's `/usr/etc/systemd/zram-generator.conf` (`min(ram / 2, 16384)`, Bazzite's); OS-BASE B5 proposed 4 GiB.
  - At the check it held 4.6 GiB in 1.33 GiB: **3.4 : 1**.
- `swappiness` 60, `page-cluster` 3 (defaults).
- MGLRU on (0x0007), `min_ttl_ms` 0.
- KSM off, THP `madvise`, zswap off.
- In a user game scope, `memory.reclaim`, `cgroup.freeze` and `memory.high` are owned by the user, so the supervisor needs no root.

**`memory.reclaim`**
- Reclaims from that cgroup only. `swappiness=max` takes anonymous memory only. `EAGAIN` if less was reclaimed. It is "not meant to indicate memory pressure" (kernel docs).
- Precedents:
  - Meta's Senpai/TMO saves 20 to 32 % fleet-wide.
  - Android compacts cached apps with `process_madvise(MADV_PAGEOUT)` before freezing them: 15 % fewer kills in dogfood, no warm-start penalty (LWN/LPC).
- Wake-up: informal zram numbers give about 5.7 µs (zstd) and 1.7 µs (lz4) per fault at page-cluster 0 (a 2021 benchmark its author calls rough). Faulting in 200 MiB is about 51,000 faults, so 0.1 to 0.3 s spread over the first frames (estimate).
- Do the GC and the trims first, so dead memory is freed rather than swapped.

**`cgroup.freeze`**
- Processes stop until thawed; a fatal signal still kills them (kernel docs).
- Android freezes cached apps 10 s after they become cached, keeps them in RAM, and then may compact them into zram (published).
- Android's docs warn that `scheduleAtFixedRate` timers burst after a thaw. Here the analogue is Minecraft's tick catch-up and the supervisor's heartbeat.

**Lowering `MemoryHigh` while covered**: worse than one reclaim. It keeps throttling, as v2 showed (322 events, 31.7 ms worst frame).

**zram, MGLRU and KSM**
- zram sysctls save nothing by themselves. Swappiness 180, page-cluster 0, watermark scale 125 and boost 0 are Pop!_OS's zram defaults. The kernel docs say swappiness above 100 suits in-memory swap.
- lz4 against zstd: faster wake-up, ratio 3.0 against 4.4 (informal).
- zram can recompress idle pages with a second algorithm.
- `min_ttl_ms=1000` protects the working set and prefers an OOM kill to thrashing (kernel docs). It touches B5's kill handling: the OS lead's call.
- KSM: skip.

**GPU**
- The NVIDIA libraries are large on disk (gpucomp 116 MiB, glcore 40, eglcore 38; measured here). Only touched pages are resident: clean and shared.
- Intel for the world moves GPU buffers into RAM. Not a memory saving.

## 5. What a home screen in Minecraft cannot go below, and why

The floor while drawing is about 0.83 to 0.99 GiB of RSS, about **0.85 GiB** in round numbers (estimate, built from pkg 41's breakdown):

| Part | Floor (MiB) | Why |
|---|---|---|
| Classes, metadata and JIT code (metaspace, class space, code, symbols, CDS, misc) | ~230 | Every class of Minecraft, Fabric and the mod, compiled |
| Live heap, after COH and FerriteCore | ~250 to 330 | Registries, every block state and baked model, the integrated server's data |
| Heap headroom at the 30 % free ratio | +50 to 100 | G1 needs room to allocate |
| G1's structures | ~40 to 60 | |
| Driver and native buffers, without retained garbage | ~120 to 160 | Includes about 55 of `nvidiactl` shared memory |
| Mapped files | ~140 | Clean and shared; the kernel drops them first |

- **While covered** the floor is lower: the OS can push nearly all of it to zram (about 0.2 GiB resident when frozen, estimate). The cost moves into the wake-up.
- **Below 0.85 GiB visible** needs a ModernFix-class lazy model loader (192 MB heap in its 1.18.2 guide). That is large work with no 26.x Fabric base, or a different program altogether.
- **The rest of the session is on top:** Prism (unmeasured, est. 60 to 150), the helper, the supervisor and the laptop home.

## 6. The laptop home

The question was: is ~335 MiB a lot for a simple screen? Yes, and most of it is not WebKit.

Measured here (WebKit agent): WebKitGTK 2.54.1, GTK 4.22.5, Mesa 26.2.4, headless cage at 1920 x 1080, 10 s idle, no layer-shell (not installed).
- **anon** is working memory.
- **alone** is anon plus each mapped file once: the cost if nothing else shared it.
- PSS was noisy (±40) because other sessions were running WebKit at the same time.

| Setup | anon | alone | PSS |
|---|---|---|---|
| Bare engine, system default GPU choice | 181 | 404 | 356 (study 44: ~335) |
| Bare engine, EGL and Vulkan pinned to Mesa/Intel (`__EGL_VENDOR_LIBRARY_FILENAMES=…/50_mesa.json`, `VK_DRIVER_FILES=…/intel_icd.x86_64.json`) | **85** | **242** | **~150** |
| + `HARDWARE_ACCELERATION_POLICY_NEVER` (or `WEBKIT_DISABLE_DMABUF_RENDERER=1`) | −17 | −26 | ~−30 |
| `WEBKIT_DISABLE_COMPOSITING_MODE=1` | −7 | −11 | |
| `JSC_useJIT=0` | −2 | | |
| Cache model `DOCUMENT_VIEWER`, memory-pressure limit, Skia CPU, `GSK_RENDERER=cairo` | 0 | 0 | |
| Python + GTK 4 drawing area, pinned (Vulkan renderer) | 25 | 77 | 37 |
| … NVIDIA libraries loaded | 53 | 179 | 106 |
| foot (C, pixman, no GTK), for scale | 3 | 14 | 9 |

- **Why pinning matters.** libglvnd's EGL loads every vendor library by default, so NVIDIA's libraries land in the UI process and the web process even when Intel draws. With the pin, the web process alone drops from 84 to 32 anon.
- **Fixed costs you can't switch off.**
  - The network process: 10 anon, 16 to 22 PSS. WebKitGTK 6 always has one, and no API avoids it (not verified further).
  - The sandbox: 1 to 2 PSS.
  - The GPU process is built but disabled for GTK (WebKit bug 307065).
- **Update to 2.54.2:** it releases suspended pages and idle processes under memory pressure and fixes a leak of prewarmed web processes.

**When the companions come** (measured here, pinned; whole combination):

| Setup | anon | alone | PSS |
|---|---|---|---|
| One WebKitGTK 6 page with home and companion canvas | 88 | 259 | 155 |
| Native GTK 4 home + separate WebKitGTK 6 companion program | 110 | 267 | 172 |
| Native GTK 4 home + Tauri companion (webkit2gtk-4.1, GTK 3: different library files, nothing of WebKit shared) | 132 | 308 | 234 |
| WebKit 6 home + Tauri companion | 192 | 419 | 330 |

- Tauri v2 on Linux needs `webkit2gtk-4.1`, and its move to webkitgtk-6.0 is still an open issue. A Tauri companion therefore brings a second copy of WebKit and JavaScriptCore.

**Answer**
- **Keep WebKit for the companions, and do two things:**
  - Pin the window program's EGL/Vulkan vendor to Mesa/Intel (it must draw on the compositor's chip anyway, section 4 of LAPTOP-HOME). That takes it from about 335 to **about 150 to 180 MiB PSS** (~90 anon, ~260 alone).
  - Ship WebKitGTK ≥ 2.54.2.
- **`NEVER` acceleration:** another ~20 to 30, but only if the moving companions' CPU cost on the CPU-drawn canvas is acceptable; not measured.
- **Going native** (Python GTK 4, ~37 PSS / 77 alone) saves about 110 to 120 MiB PSS more, but only while no companion runs on Linux.
  - Native home plus Tauri companions costs about 50 MiB (PSS) more than one shared page (234 vs 155), and native plus a WebKit 6 companion costs about 17 more (172 vs 155).
  - Since the plan is companions in this home, one shared engine is the cheapest end state.
- **Caveat:** layer-shell was not loaded, and his real two-screen session may differ by tens of MiB. Re-measure in the build package.

## 7. Draft plan for a measuring package

**Rig additions** (development aid only; `rig/run.sh` and `java-wrapper.sh`):
- `ENV=` (variables for the game, through the wrapper's `systemd-run --setenv`).
- `MODS=` (extra jars in `-Dfabric.addMods`).
- `PROBE=1`: at each snapshot, run `jcmd System.trim_native_heap` and record its RSS change, run `jcmd GC.run` and `GC.heap_info` for the live heap, classify `/proc/<pid>/smaps` (jemalloc / glibc arenas / `nvidiactl` / heap / files), and read `/proc/<pid>/stat` majflt.
- `RECLAIM=<amount>` and `FREEZE=1` in the cover phase, plus a 10 s `wake` frame window after the cover ends.
- `LONG=<minutes>` for an idle run.
- `NMT=0` for product-like absolute numbers.
- Snapshots add `memory.swap.current` and zram's `mm_stat`.

**Order** (one game at a time under the client-test lock; about 12 minutes a run):

0. **Probe, 2 runs.**
   - One v1 run with `PROBE=1` and `COVER=300`. It shows how much a trim gives at each moment, how the native part splits, and the live heap.
   - One `LONG=20` run with the world visible and idle, for the NVIDIA 10-minute step.
   - This decides whether item 1's allocator work is worth the steps after.
1. **Single factors against a fresh v1 baseline**, 2 runs each, alternating with the baseline so run order doesn't confound (package 41's lesson). About 16 runs:
   - (a) compact headers;
   - (b) (a) plus string dedup;
   - (c) `TrimNativeHeapInterval=60000`;
   - (d) (c) plus `allocator=system`;
   - (e) `ENV=MALLOC_ARENA_MAX=2`;
   - (f) fewer threads.
2. **FerriteCore 9.0.0**, 2 runs, after the mod's client tests pass with it.
3. **Covered**, 2 runs each, with wake-up frames and majflt:
   - none (baseline) / GC + trim / plus reclaim 300M / plus reclaim 600M / plus freeze.
4. **The combination of winners** against the brief's pass line (no OOM, GC pause ≤ 50 ms after joining, no `high` events, frames no worse than v1):
   - flat ×3;
   - one first creation (f1-like);
   - the Nether glide (n1-like);
   - `LONG=20` once;
   - one `NMT=0` run for the number to report.
5. **Product check on the laptop after release.** PSS of the game, Prism, the helper, the supervisor and the laptop home in his session. Decide about Prism only then.

That is about 35 runs, roughly 7 to 8 hours of rig time. Steps 0 to 2 can stop early if step 0 shows the native part is the driver's and not the allocators'.

## 8. Not verified

- Every saving marked "estimate" above, above all items 1, 3 and 7 and FerriteCore on vanilla 26.2.
- That Fedora's `java-25-openjdk` ships `classes_coh.jsa`.
- `JE_MALLOC_CONF` for LWJGL's jemalloc build.
- Prism's resident memory.
- Whether the NVIDIA 10-minute allocation hits Minecraft on 615.78.08.
- The Vulkan backend's memory.
- OpenJ9 with Fabric 26.x.
- Laptop home with gtk4-layer-shell loaded, in his real two-screen session, and the CPU cost of `NEVER` with moving companions.
- Whether WebKit's network process can be avoided.
- The game was checked to load no Mesa only on the dev client's GLX path, not in the product session.

## 9. Sources

**JVM**
- https://www.happycoders.eu/java/compact-object-headers/
- https://openjdk.org/jeps/519 (403 to fetching; cited through secondary sources)
- https://www.happycoders.eu/java/java-27-features/ (JEP 534)
- https://cleanroommc.com/wiki/end-user-guide/args
- https://bugs.openjdk.org/browse/JDK-8357881
- https://bugs.openjdk.org/browse/JDK-8325612
- https://mail.openjdk.org/pipermail/jdk-updates-dev/2024-February/030122.html
- https://mail.openjdk.org/pipermail/hotspot-dev/2021-August/054323.html
- https://mail.openjdk.org/pipermail/serviceability-dev/2021-June/038181.html
- https://mail.openjdk.org/pipermail/hotspot-dev/2023-July/076605.html
- https://devcenter.heroku.com/articles/tuning-glibc-memory-behavior
- https://github.com/prestodb/presto/issues/8993
- https://poonamparhar.github.io/dynamic_compiler_threads/
- https://blog.lwjgl.org/memory-management-in-lwjgl-3/
- https://javadoc.lwjgl.org/org/lwjgl/system/Configuration.html
- https://github.com/jemalloc/jemalloc/issues/1398
- https://fuchsia.googlesource.com/third_party/github.com/jemalloc/jemalloc/+/54eaed1d8b56b1aa528be3bdd1877e59c56fa90c/INSTALL.md
- https://morling.dev/blog/jep-483-aot-class-loading-linking
- https://mail.openjdk.org/pipermail/leyden-dev/2026-January/002900.html
- https://inside.java/2026/01/09/run-aot-cache/
- https://openjdk.org/jeps/8359211
- https://mail.openjdk.org/pipermail/hotspot-dev/2026-January/117925.html
- https://docs.oracle.com/en/java/javase/21/gctuning/z-garbage-collector.html
- https://mail.openjdk.org/pipermail/shenandoah-dev/2018-March/005239.html
- https://mail.openjdk.org/pipermail/shenandoah-dev/2019-October/010728.html
- https://github.com/brucethemoose/Minecraft-Performance-Flags-Benchmarks
- https://eclipse.dev/openj9/performance/
- https://eclipse.dev/openj9/performance/benchmark17/daytrader8_java17.html
- https://herongyang.com/JVM/OpenJ9-Footprint-Comparison-with-HotSpot.html
- https://community.ibm.com/community/user/blogs/paul-arockiam/2025/09/26/ibm-semeru-runtime-open-edition-25-is-ga
- https://ayakael.net/mirrors/papermc/src/commit/86e20be366a0f834f58026e6b0cc8b929f1b038a/patches/server/Improve-Server-Thread-Pool-and-Thread-Priorities.patch

**Minecraft and mods**
- https://minecraft.wiki/w/Java_Edition_26.1
- https://piston-meta.mojang.com/v1/packages/f28ad96ed5d65e2438da836144a3de15bb9cafe7/26.2.json
- https://patchbot.io/games/minecraft/articles/48-minecraft-261-snapshot-8
- https://minecraft.wiki/w/Spawn_chunk
- https://fabricmc.net/2026/03/14/261.html
- https://github.com/malte0811/FerriteCore/blob/26.1/summary.md
- https://github.com/malte0811/FerriteCore/blob/26.1/changelog/8.0.0.md
- https://github.com/malte0811/FerriteCore/blob/26.1/Common/src/main/java/malte0811/ferritecore/mixin/config/FerriteConfig.java
- https://github.com/malte0811/FerriteCore/blob/26.1/LICENSE
- https://modrinth.com/mod/ferrite-core
- https://github.com/malte0811/FerriteCore/issues/152
- https://github.com/malte0811/FerriteCore/issues/96#issuecomment-1278544397
- https://github.com/malte0811/FerriteCore/issues/211
- https://modrinth.com/modpack/fabulously-optimized
- https://github.com/embeddedt/ModernFix/issues/653#issuecomment-4365112388
- https://github.com/embeddedt/ModernFix/issues/547
- https://github.com/embeddedt/ModernFix/issues/563
- https://github.com/embeddedt/ModernFix/issues/640
- https://modrinth.com/mod/modernfix-mvus
- https://modrinth.com/mod/modernfix
- https://github.com/embeddedt/ModernFix/wiki/Dynamic-Resources-FAQ
- https://github.com/embeddedt/ModernFix/wiki/1.20-Summary-of-Patches
- https://github.com/embeddedt/ModernFix/commit/6300dd6737788886b1f37b8bf2c77a980effe481
- https://github.com/embeddedt/ModernFix/commit/82535da8618a740d4173ed9040fbff8e1d9db65b
- https://github.com/embeddedt/ModernFix/wiki/Ultra%E2%80%90Low-Memory-Footprint
- https://github.com/CaffeineMC/sodium/releases
- https://github.com/CaffeineMC/sodium/blob/dev/LICENSE.md
- https://github.com/CaffeineMC/sodium/issues/3810
- https://github.com/CaffeineMC/sodium/issues/3690
- https://modrinth.com/mod/dynamic-fps
- https://modrinth.com/mod/immediatelyfast
- https://github.com/tr7zw/EntityCulling
- https://modrinth.com/mod/lazydfu
- https://modrinth.com/mod/memoryleakfix
- https://modrinth.com/mod/starlight
- https://www.sevarg.net/2022/04/23/aarch64-minecraft-on-the-pi-4-and-others/
- https://raspberrytips.com/install-minecraft-java-raspberry-pi/
- https://pimylifeup.com/steam-deck-minecraft-java/
- https://modrinth.com/mod/preferopengl
- https://www.playnews.gg/en/guides/minecraft-snapshot-26-4-vulkan-rendering-how-to-enable-it-and-check-it-with-f3
- https://forums.developer.nvidia.com/t/opengl-driver-thread-cpmmlistener-allocates-large-amounts-of-ram-exactly-10-minutes-after-launch-rimworld-unity/385727

**OS**
- https://docs.kernel.org/admin-guide/cgroup-v2.html
- https://docs.kernel.org/admin-guide/mm/multigen_lru.html
- https://docs.kernel.org/admin-guide/mm/ksm.html
- https://docs.kernel.org/admin-guide/sysctl/vm.html
- https://docs.kernel.org/admin-guide/blockdev/zram.html
- https://docs.kernel.org/gpu/drm-mm.html
- https://source.android.com/docs/core/perf/cached-apps-freezer
- https://lwn.net/Articles/790005/
- https://lpc.events/event/4/contributions/404/attachments/326/550/Handling_memory_pressure_on_Android.pdf
- https://engineering.fb.com/2022/06/20/data-infrastructure/transparent-memory-offloading-more-memory-at-a-fraction-of-the-cost-and-power/
- https://par.nsf.gov/servlets/purl/10332477
- https://github.com/pop-os/default-settings/pull/163
- https://www.reddit.com/r/Fedora/comments/mzun99/new_zram_tuning_benchmarks/

**WebKit and native drawing**
- https://github.com/NVIDIA/libglvnd/blob/master/src/EGL/icd_enumeration.md
- https://github.com/KhronosGroup/Vulkan-Loader/blob/main/docs/LoaderDriverInterface.md
- https://webkitgtk.org/reference/webkitgtk/stable/enum.HardwareAccelerationPolicy.html
- https://webkitgtk.org/reference/webkitgtk/stable/migrating-to-webkitgtk-6.0.html
- https://webkitgtk.org/2026/04/17/webkitgtk2.53.1-released.html
- https://webkitgtk.org/reference/webkitgtk/stable/environment-variables.html
- https://lists.webkit.org/pipermail/jsc-dev/2018-September/000221.html
- https://webkitgtk.org/reference/webkitgtk/stable/enum.CacheModel.html
- https://webkitgtk.org/reference/webkitgtk/stable/struct.MemoryPressureSettings.html
- https://webkitgtk.org/reference/webkitgtk/stable/property.WebView.related-view.html
- https://discourse.gnome.org/t/web-app-resource-usage-separate-processes-performance-and-efficiency-implications/17765
- https://bugs.webkit.org/show_bug.cgi?id=307065
- https://webkitgtk.org/2025/04/08/webkitgtk-2.48.html
- https://webkitgtk.org/2026/10/23/webkitgtk2.54.2-released.html
- https://github.com/tauri-apps/tauri/issues/5889
- https://github.com/tauri-apps/tauri/issues/12562
- https://v2.tauri.app/start/prerequisites/
- https://lists.gnome.org/archives/epiphany-list/2016-October/msg00016.html
- https://planet.igalia.com/webkit
- https://github.com/gtk-rs/gtk4-rs/issues/1732
- https://forum.endeavouros.com/t/how-to-significantly-reduce-memory-usage-memory-usage-in-gtk4-and-libadwaita-apps/79360
- https://snowarch.github.io/iNiR/docs/faq
- https://github.com/deepu105/eww
- https://grigio.org/is-systemd-bloat-real-dinit-vs-systemd-which-session-uses-less-memory-with-labwc/
