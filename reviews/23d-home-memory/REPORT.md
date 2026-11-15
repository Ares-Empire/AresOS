# Package 23d: the home screen's memory settings (report)

Brief: `briefs/23d-home-memory.md` (empire brief 294). Branch `pkg/23d-home-memory` from main `7512c06d`. Builder: one
Claude agent on Opus 5.5 (a small, fully specified change to the supervisor). Claude agents cannot create
`REPORT.md`, so the full report is here; the integrator commits it as `REPORT.md`.

## Done

- `os/config/usr/libexec/aresos-desktop`:
  - `HEAP_MB` 3072 → **1024**, `MIN_HEAP_MB` 512 → **256**, `MEMORY_HIGH` `'5G'` → **`'2560M'`**, with a comment
    giving package 41's reasons.
  - New `JVM_ARGS = '-XX:MaxHeapFreeRatio=30 -XX:MinHeapFreeRatio=10'`. `instance_config` writes it as
    `OverrideJavaArgs=true` and `JvmArgs=-XX:MaxHeapFreeRatio=30 -XX:MinHeapFreeRatio=10`, right after the memory
    keys. Its comment now names the Prism source of the keys, says why `=` and spaces inside a value are fine, and
    says that `JvmArgs` must never set the heap.
  - `RENDER_DISTANCE` 8 and `SIMULATION_DISTANCE` 5 are unchanged. `provision` and `MANAGED_SETTINGS` are unchanged:
    an existing instance is never touched.
- `os/tests/test_aresos_desktop.py`:
  - The first-start test now reads `MinMemAlloc` 256, `MaxMemAlloc` 1024, `OverrideJavaArgs` true and the `JvmArgs`
    value from the provisioned `instance.cfg`.
  - `game_scope` and the hand-off check now expect `--property=MemoryHigh=2560M`. The real-scope test expects
    `memory.high` 2684354560 (2560 × 1024²).
  - New `test_the_jvm_arguments_are_a_plain_value_that_never_sets_the_heap`. Every value in `instance_config`'s output
    is plain (no `,` `;` `"` or `'`). `JvmArgs` equals `JVM_ARGS` and splits at spaces into exactly the two flags. It
    holds none of the strings that Prism's launch check refuses: `-Xms`, `-Xmx`, `-XX:PermSize=`,
    `-XX-MaxHeapSize`, `-XX:InitialHeapSize` and `-version:`.
  - New `test_an_existing_instance_keeps_the_memory_settings_it_was_created_with`. An instance with package 23's
    values (3072 / 512, no JVM arguments) is neither changed by `provision` nor reported by `check_instance`. This
    test pins the known limit below, so the follow-up has to change it on purpose.
- `os/ci/overlay/checks.py` (the package 23 VM check `desktop_jvm`): the game scope's `memory.high` must be
  `2560 * MIB` (it was `5 * GIB`).
- `os/ci/image-checks.sh` pinned none of these values (its provisioning check runs `check_instance`), so it is
  unchanged. `-Xmx3072m` in `WrapperTest` is just an argument the wrapper passes through, not the supervisor's value,
  so it stays too.

## The numbers and where they come from

All of them come from package 41 (`reviews/41-home-memory/REPORT.md`, merged as `7512c06d`, and REVIEW-3's
correction of the margin):

| Setting | Before | Now | Package 41's reason |
|---|---|---|---|
| `HEAP_MB` | 3072 | 1024 | The live heap after GC was 250 to 375 MiB in the flat home and up to about 410 in the Nether. G1 never committed more than about 620 MiB in the flat home. At 1024 there was no `OutOfMemoryError`, the longest GC pause after joining was about 14 ms, and frame times matched 3072. |
| `MIN_HEAP_MB` | 512 | 256 | With the flags this is the floor the heap can shrink to; G1 never goes below `-Xms`. |
| JVM flags | none | `-XX:MaxHeapFreeRatio=30 -XX:MinHeapFreeRatio=10` | The committed heap stays near the live data (about 390 MiB instead of 510 to 620). RSS is about 50 MiB lower settled, about 95 after flying and about 85 while covered. The cost: about four times as many short GC pauses while flying fast over new ground. |
| `MEMORY_HIGH` | `5G` | `2560M` | The worst case is about 1.85 GiB anonymous, a computed bound: a full 1 GiB heap (no run reached it) plus the most measured beside the heap, 869 MiB (n2, package 41's REVIEW-3, finding 1). That leaves about 0.65 GiB of room. 1100M was shown too low (v2: 322 `high` events, 165 MiB pushed into swap, worst frame 31.7 ms). |
| `RENDER_DISTANCE` / `SIMULATION_DISTANCE` | 8 / 5 | 8 / 5 | There is no RAM to gain: render 6 used the same memory as 8, his full program list needs render 7, and simulation 2 measured the same as 5. |

## Prism's key names, and where they were verified

The image pins Prism **11.1.1** (`os/minecraft/desktop.lock.json`, `prism.version`, not `os/packages.lock.json`). I
checked its source at tag `11.1.1` (commit `7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4`, fetched with `gh api`):

- `launcher/minecraft/MinecraftInstance.cpp:187,192` (`loadSpecificSettings`):
  `registerSetting("OverrideJavaArgs", false)` and
  `registerOverride(global_settings->getSetting("JvmArgs"), argsOverride)`. So the instance keys are
  **`OverrideJavaArgs`** (the gate) and **`JvmArgs`** (the value), and `JvmArgs` counts only while the gate is true
  (`OverrideSetting::get`, `launcher/settings/OverrideSetting.cpp:36`).
- `launcher/Application.cpp:748`: the global `JvmArgs` that the instance key overrides.
- `launcher/BaseInstance.cpp:487`: `extraArguments()` is `Commandline::splitArgs(JvmArgs)`, which splits at spaces
  and takes `"` and `'` as quotes (`launcher/Commandline.cpp:47`).
  `MinecraftInstance::javaArguments()` puts these first, before `-Xms<MinMemAlloc>m -Xmx<MaxMemAlloc>m`.
- `launcher/LaunchController.cpp:71` with `launcher/JavaCommon.cpp:42` (`checkJVMArgs`): a launch whose `JvmArgs`
  contain `-Xm[sx]`, `-XX:PermSize=`, `-XX-MaxHeapSize`, `-XX:InitialHeapSize` or `-version:` is refused with a modal
  dialog. The new flags contain none of them, and the new test keeps it that way.
- `launcher/settings/INIFile.cpp` (`loadFile`): an `instance.cfg` with `ConfigVersion=1.3` is read with plain
  `QSettings` values.

I also read the generated `instance.cfg` back with real `QSettings` (PySide6 6.11.2, the laptop's Qt; not the
bundle's own Qt):

- All 31 keys read the same as the supervisor's `parse_ini` reads them, and `JvmArgs` is
  `-XX:MaxHeapFreeRatio=30 -XX:MinHeapFreeRatio=10`.
- Saved again the way Prism's `INIFile::saveFile` saves (a `QSettings` `setValue` per key), the line becomes
  `JvmArgs="-XX:MaxHeapFreeRatio=30 -XX:MinHeapFreeRatio=10"` (Qt quotes a value that contains `=`). Both
  `QSettings` and `parse_ini` read it back unchanged.

## Verified

- `python3 -m unittest discover -s os/tests -p 'test_aresos_desktop.py'`: **Ran 154 tests, OK (skipped=1)** in
  169 s.
  - The skipped test is `test_the_real_jvm_runs_in_its_own_scope_with_the_memory_target`: no user systemd manager
    can be reached from this sandbox. It runs where one exists (WSL, the image), and the VM check `desktop_jvm` asserts
    the same `memory.high` in the VM.
  - The two new tests and the updated ones pass (run again verbosely).
- The JVM accepts the flags: `java -Xms256m -Xmx1024m -XX:MaxHeapFreeRatio=30 -XX:MinHeapFreeRatio=10
  -XX:+PrintFlagsFinal -version` on the laptop's Temurin 25.0.5 shows both ratios `{command line}`, a 256 MiB initial
  and 1024 MiB maximum heap, and G1. This is the development JDK, not the image's Fedora `java-25-openjdk`; package
  41 ran the same flags on Java 25.
- Rehearsal bindings: none of the changed files is bound. A read-only `rebind.changed()` lists the same four files
  the pending list already holds (`os-image.yml`, `rehearsal-packages.json`, `test_owner_path.py`,
  `test_ways_back_probe.py`), so I did not run `rebind.py pending`.
- Not run, per the brief: the hosted checks-only run and the check build with VM (no workflow dispatch). They run the
  whole suite and `checks.py`'s `memory.high` check.

## Not verified

- **Prism actually starting Java with the flags.** This is proven from the source and the `QSettings` read only. CI
  has no Minecraft account, and the laptop rules forbid running Prism. The first start on the laptop proves it (next
  section).
- The values in hours-long sessions and a world he has built in (package 41's own Not verified).

## What the laptop check after the release reads

On the first start, the instance is new. While the game runs:

- **The JVM's command line:** `tr '\0' ' ' < /proc/<java pid>/cmdline` holds `-XX:MaxHeapFreeRatio=30
  -XX:MinHeapFreeRatio=10` and `-Xms256m -Xmx1024m`. `jcmd <pid> VM.flags` shows the same. This is the one proof that
  Prism read `OverrideJavaArgs`/`JvmArgs`.
- **The game scope:**
  `/sys/fs/cgroup/user.slice/user-1001.slice/user@1001.service/aresos.slice/aresos-game-<launch>.scope/`, where
  `<launch>` comes from `/run/user/1001/aresos/desktop-runtime.json`.
  - `memory.high` reads `2684354560`.
  - **`memory.stat` `anon`** is the game's own memory. Expect it well under 2 GiB: package 41 measured the scope at
    about 1.1 to 1.3 GiB in the flat home, and 1.85 GiB as the worst case with a full heap.
  - **`memory.events` `high`** should stay 0. A count alone can mean the kernel only trimmed clean page cache; the game was throttled when it counts together with a high `memory.stat` `anon` and the scope's `memory.pressure` showing stalls. Read `memory.stat` `file` beside it.
  - **Not `memory.peak` / `MemoryPeak` alone.** After a boot the game is the first to read its jars, libraries, assets
    and world, and that page cache is charged to this scope too. So the peak reads higher than package 41's numbers
    (up to about RSS plus what it read) without anything being wrong. Clean cache is the first thing reclaimed under
    `MemoryHigh`.
- RSS: `ps -o rss= -p <pid>`. Package 41 measured about 1.2 GiB standing at home and about 1.3 GiB after flying.

## Known limits

- **An existing instance keeps the values it was created with.** `provision` never changes an existing instance. The
  memory keys are not in `MANAGED_SETTINGS`, so `check_instance` does not report them either. The laptop has no
  AresDesktop instance yet, so the next release's first start creates it with 1024 / 256 and the flags. A later
  change of `HEAP_MB`, `MIN_HEAP_MB` or `JVM_ARGS` won't reach an instance that already exists (pinned by
  `test_an_existing_instance_keeps_the_memory_settings_it_was_created_with`).
- **`MEMORY_HIGH` behaves differently.** `game_scope()` applies it at every launch, so it reaches every instance at
  once, including any instance made with package 23's values. There, a 3 GiB heap ceiling would sit under a 2.5 GiB
  target. Package 41 measured that combination's scope at up to 1605 MiB (n2, the Nether glide), so only abnormal
  growth would be throttled. No such instance exists on the laptop.
- **Creating a world freezes the picture once.** At the Create click the screen stands still for about 2 s (flat
  home) or about 4 s (Nether). It was the same at the old settings, and once, in two Nether creations at these
  settings, it took 5.7 s (package 41's n0: not GC, cause not found). It is a one-time wait when a home is made, not a
  stall in daily use.
- The flags cost more CPU while flying fast over new ground: about four times as many GC pauses and about a fifth to
  a quarter of a core more for that minute. Standing, walking and covered cost the same (package 41, JUDGMENT-CALL 1,
  taken by the integrator in the brief).

## Follow-up for the integrator: enforcing these values on existing instances

Recommended, but **not by adding the keys to `MANAGED_SETTINGS`**, and only before the first release that changes
these values again (nothing needs it now):

- `MANAGED_SETTINGS` only reports drift. `validate()` turns any drift into the `instance` recovery, so an update that
  changed a value would stop the desktop from starting at all.
- Instead, a narrow repair step at session start, before Prism runs (Prism rewrites `instance.cfg` when it saves):
  rewrite only the tuned keys (`OverrideMemory`, `MinMemAlloc`, `MaxMemAlloc`, `OverrideJavaArgs`, `JvmArgs`) to the
  image's values, atomically, keeping every other key and Prism's own additions (`lastLaunchTime` and so on). It must
  accept Prism's quoted form (`JvmArgs="…"`) and log what it changed.
- It would overwrite anything the owner set in Prism's Java tab. He never sees Prism in normal use, but that is a
  design call for the lead.

## JUDGMENT-CALL

- None new. Taking the free-ratio flags was package 41's JUDGMENT-CALL 1, and the integrator decided it in the brief.

## PLAN-GAP

1. **`rebind.py pending --help` is not a help call.** `pending` takes any argument as its note: the brief's
   suggested command appended `"--help"` to `os/manifest/ci/16/pending-rebind.json`'s `changes` and rewrote the file.
   I reverted it with `git checkout` before any commit, and it is not in this branch. The module docstring (`head -20
   reviews/27-first-update-release/rebind.py`) is the help, and `rebind.changed()` is a read-only way to see what
   differs.
2. The Prism version is in `os/minecraft/desktop.lock.json` (`prism`), not in `os/packages.lock.json`.
3. `docs/design/OS-BASE.md` section 2 and B5 still give package 23's starting budget: a 3 GiB desktop heap and a 5 GiB
   working target. The doc calls them initial values to be measured, and I left it unchanged because it is outside
   the brief. A dated note pointing at packages 41 and 23d would keep it true.

## Open questions

- None that block.
