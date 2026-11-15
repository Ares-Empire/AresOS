# 23d: the home screen's memory settings

Empire brief 294. The integrator (2026-11-15), from package 41's measurements (`reviews/41-home-memory/REPORT.md`,
merged as `7512c06d`: the measurements behind every number here).

**Builder:** one Claude agent on Opus (integrator's choice: a small, fully specified change to the desktop supervisor).

Read `AGENTS.md`, then `reviews/41-home-memory/REPORT.md`, `os/config/usr/libexec/aresos-desktop` (`HEAP_MB`,
`MIN_HEAP_MB`, `MEMORY_HIGH`, `RENDER_DISTANCE`/`SIMULATION_DISTANCE`, `instance_config`, `game_scope`, `provision`),
`os/tests/test_aresos_desktop.py`, `os/ci/image-checks.sh` and the package 23 VM checks that read these values (grep
for `HEAP_MB`, `MaxMemAlloc`, `MemoryHigh`, `5G`, `3072`).

## Build

1. `HEAP_MB` 3072 → **1024**; `MIN_HEAP_MB` 512 → **256**.
2. `MEMORY_HIGH` `'5G'` → **`'2560M'`** (the game scope's systemd `MemoryHigh`). Worst case measured about 1.85 GiB
   anonymous (heap 1 GiB + 869 MiB beside it), so about 0.65 GiB headroom; 1100M was shown too low.
3. JVM flags **`-XX:MaxHeapFreeRatio=30 -XX:MinHeapFreeRatio=10`** for the managed instance, written by
   `instance_config` through Prism's instance keys for JVM arguments. Find the exact key names in the pinned Prism's
   source or docs for the version the image pins (look in `os/packages.lock.json` or the Prism metadata the supervisor
   uses for the version; candidates `OverrideJavaArgs=true` and `JvmArgs=…`; verify, don't guess). Values stay plain
   (`instance_config`'s comment: no commas, quotes or semicolons; check the flags satisfy it). If the key names cannot
   be verified for the pinned version, stop and report a PLAN-GAP for item 3 and ship 1, 2 and 4 alone (they're
   independent).
4. `RENDER_DISTANCE` 8 and `SIMULATION_DISTANCE` 5 stay as they are.
5. Keep the existing rule that an existing instance is never changed (`provision` is idempotent): the laptop has no
   AresDesktop instance yet, so the next release's first start creates it with these values. Write that in the report
   and as a known limit (a later change of these values won't reach an instance that already exists), and say whether
   the supervisor should later enforce them on existing instances (`MANAGED_SETTINGS`) as a follow-up for the
   integrator; don't build that.
6. Tests: the new values in `instance_config`'s output (`MaxMemAlloc` 1024, `MinMemAlloc` 256, the JVM args keys and
   value), `game_scope`'s `MemoryHigh` 2560M, every image check or VM check that pinned the old values updated, and a
   test that the JVM args value satisfies `instance_config`'s plain-value rule.
7. Report (in `reviews/23d-home-memory/PROGRESS.md`; Claude agents cannot create `REPORT.md`): the numbers and their
   source (package 41), the Prism key names and where you verified them, what the laptop check after the release
   reads (the game scope's `memory.stat` `anon` and `memory.events` `high`, not `MemoryPeak` alone, since page cache
   from jars and assets also lands there), and the one-time world-creation freeze (2–4 s, up to 5.7 s once) package 41
   reported, as a known limit.

If you change a file bound by a rehearsal (the pending list's rule; `test_checkout_sources` tells you), run
`python3 reviews/27-first-update-release/rebind.py pending "23d: …"` after all changes.

## Rules

- The laptop is the owner's: never run the supervisor, Prism or Minecraft on its screen; no sudo, ostree, bootc,
  rpm-ostree; no disk or boot changes.
- Run only the `os/tests` modules you touch, one at a time; never `test_owner_update` locally; never a pattern-less
  discover.
- Do not dispatch workflows. Never merge, never push to main, never `--no-verify`.
- Commit, push, open a draft PR "23d: home screen memory settings".
