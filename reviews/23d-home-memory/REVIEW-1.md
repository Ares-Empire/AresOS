Reviewed PR #78 at `530c0577` (23d).

Reviewer: a fresh Claude agent on Opus 5.5 that did not build this; read-only. Committed by the integrator from its final message (shortened; every finding kept).

**SAFE.** The values match package 41's recommendation exactly (HEAP_MB 1024, MIN_HEAP_MB 256, `-XX:MaxHeapFreeRatio=30 -XX:MinHeapFreeRatio=10`, MEMORY_HIGH 2560M = 2684354560, render 8 / simulation 5 unchanged). The headroom is conservative: 869 MiB beside the heap was measured at a 3072 MiB heap (G1's own structures shrink with a smaller maximum), no run committed more than 726 MiB of heap, so a realistic worst case is about 1.5 GiB against a 2.5 GiB soft target; MemoryHigh throttles, it never kills.

- **Prism's keys confirmed** in Prism 11.1.1 (the pinned tag): `OverrideJavaArgs` gates the instance's `JvmArgs` (`MinecraftInstance.cpp:187,192`, `OverrideSetting.cpp:18,36`); `BaseInstance.cpp:487` splits `JvmArgs` with `Commandline::splitArgs`; `javaArguments()` places them before `-Xms256m -Xmx1024m`; `QProcess::start(program, args)` hands each flag to the wrapper as its own argument; `JavaCommon.cpp:42`'s refusal patterns match neither flag. QSettings reads the generated `instance.cfg` and Prism's quoted re-save unchanged; Temurin 25.0.5 accepts the flags in Prism's order.
- **The wrapper** passes the arguments through unchanged (`Popen([*scope, *argv[1:]])`, pinned by WrapperTest); `systemd-run --scope` expands `$VAR` (nit 3).
- **Scopes:** MemoryHigh is set only on `aresos-game-<id>.scope` (Java alone); Prism, the wrapper and his apps are outside it. A normal session sits around 1.2–1.3 GiB anon. The laptop has no PrismLauncher data and no package 23 yet (checked read-only). Side effect: Prism's "Low free memory" dialog threshold drops from 2765 to 922 MiB.
- **Old pins:** only `checks.py:175` pinned the target and is updated; nothing else in code or checks pins the old values; none of this package's files is bound by a rehearsal.
- **Follow-up advice:** agreed, not through MANAGED_SETTINGS (drift latches the `instance` recovery). A repair step only lands while no Prism runs; a launch-time alternative (the `jvm_start` reply carries the options and the wrapper inserts them; HotSpot takes the last `-Xmx`) reaches every instance with no file rewrite, at the cost of Prism's Java tab showing values not in effect. Decide when a value next changes.

## Findings
1. **nit:** "the most anonymous memory measured was about 1.85 GiB" overstates: it is a computed bound (a full heap no run reached, plus the most measured beside it, 869 MiB from package 41's REVIEW-3 finding 1; package 41's REPORT.md still says 839 MiB). Fix the comment and report wording and cite REVIEW-3.
2. **nit:** `memory.events high` > 0 alone doesn't mean throttling (clean page cache trimmed at the target also counts). Also read `memory.stat file` and the scope's `memory.pressure`.
3. **nit:** the plain-value test could also refuse `$` (expanded by the wrapper's systemd-run) and `\` (a QSettings escape).
4. **nit (docs):** `docs/design/OS-BASE.md:66,341` still give the 3 GiB heap / 5 GiB target; add a dated note pointing to packages 41 and 23d.

## Before merge (conditions)
- The checks-only run and the check build with VM must pass; the VM's `desktop_jvm` is the real-systemd proof of the 2684354560 target.
- 23d must ship with or before package 23 on the laptop: a release with package 23's values would create the instance with 3072/512 and no flags, and that instance keeps them.

SAFE
