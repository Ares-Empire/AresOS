# 53e: the laptop home's memory

Board #335, package 53. Follows 53c (PR #114, the window program and the page), which this branch starts from. The
lead's handoff for the whole build is `briefs/53-laptop-home-build.md`.

**Builder:** Codex `gpt-6.2-sol` `xhigh` (builds stay on Codex Sol until Sat, `mac-capacity` 2026-11-18 21:50): it is
measurement and tuning against a clear target, not new design. **Review:** a fresh Codex `gpt-6.2-sol` `high`.

## Why

The owner, 2026-11-18 (through `linux-hub`): "on memory: all I remember was 1.2GB when I said try optimize and
alternative screen was 300mb … both seems crazy much for a homescreen. imagine working and 1.5gb of ur memory is used
just by doing literally nothing. thats not a good OS is it?" The game's side is `linux-hub`'s. The laptop home is ours:
53c measured **326 MiB PSS at rest** (`reviews/53c-laptop-home/REPORT.md`, "Pinned memory at rest"): the GTK program
about 183 MiB, the web process 121 MiB, the network process 22 MiB, with software rendering (`LIBGL_ALWAYS_SOFTWARE=1`).

**Target: under 150 MiB PSS in total at rest** (the program and every WebKit process), and aim for 100. The page must
look and behave as 53c built it.

## Read first

`docs/design/LAPTOP-HOME.md` section 4 ("Memory", "Motion"), `reviews/49-memory-cuts/RESEARCH.md` section 6 (on main
or on branch `pkg/49-memory-cuts`) for what was learned about WebKit and the vendor pin, 53c's REPORT, and
`os/config/usr/libexec/aresos-laptop-home` with `os/tests/test_aresos_laptop_home*.py` and `laptop_home_headless.py`.

## Do

1. **Measure honestly first.** A repeatable measurement (a test helper or a small script under `os/tests/`) that
   prints, per process, `Pss_Anon`, `Pss_File` and `Pss` from `smaps_rollup`, and the ten largest mappings by PSS.
   - **The fixture:** a fresh, settled day town of exactly 45 houses (with 47 catalogue entries), 1920 × 1080, the
     page's fonts, on a real background layer with the layer-shell library verified as 53c loaded it (its extracted
     RPM). Measure after the page has rested 15 seconds, with no interaction before. Results from the fullscreen
     fallback are labelled as such and never mixed in.
   - **Five matched runs per set-up;** report the median and the spread (min, max).
   - **First, the baseline:** unchanged 53c in this fixture.
   - **Set-up S (software, gating):** software rendering, as 53c measured. **The target is judged here.**
   - **Set-up I (Intel, reported):** a headless labwc drawing on the Intel render node, chosen as `mod/dev/client-test.sh`
     does (around line 72: the sysfs vendor check and an explicit render node), and GTK and WebKit restricted to the
     Intel device. Before each run, verify the renderer in use and that the NVIDIA card stays asleep, with the
     read-only method of `reviews/47-gpu-awake/REPORT.md` (around line 46). If isolation or device access cannot be
     established, do not run it: report set-up I as unavailable and why. Its absence does not block acceptance.
2. **Cut, one change at a time**, measuring each alone and keeping only what helps without breaking the page, its
   checks or its pictures. Use only switches the installed WebKitGTK (2.54.1) API offers. **A kept change takes effect
   in the shipped program** (`aresos-laptop-home` itself, not the test harness): the final measurement runs the
   shipped launch path without harness overrides that would mask it (53c's harness forces Cairo and turns off
   DMA-BUF; keep only what headless running truly needs, and say which). A saving that would need the supervisor's
   launch environment is reported as evidence for 23c, not built.
   - WebKit: the cache model (`DOCUMENT_VIEWER`), memory-pressure settings (`WebKitMemoryPressureSettings`) for the
     web and network processes, no page or back-forward cache, every unused feature off (WebGL, WebAudio, media,
     plugins, spatial navigation, and anything else the page does not use), the hardware-acceleration policy;
   - JavaScriptCore options such as turning the JIT off (the page rests, so its speed matters little);
   - the GTK program: the GSK renderer, what Python imports, `MALLOC_ARENA_MAX`, anything the UI process maps but does
     not need;
   - the page: decoded image sizes, layers and canvases it keeps alive, the fonts it loads.
   - **Motion check for renderer and JIT changes:** a test-only version of the study's one-minute companion canvas
     (section 4, "Motion": an 80 × 80 figure walking on a see-through canvas over the town, redrawn every frame) run
     in the packaged view, in set-up S (and I when available). Measure frame cadence and the processor use of the
     program and the web process, before and after. A renderer or JIT change is kept only if the frame rate drops by
     at most 10 % and the processor use rises by at most 25 %.
3. **Never relax a security rule** for memory: the web process sandbox, the scheme rules, the deny-by-default request
   filter, the token removal and the vendor pin all stay.
4. **If the median in set-up S stays at 150 MiB or higher** after the cuts: report the floor and what it is made of, and measure a small
   native prototype for comparison: a GTK 4 program without a web engine that draws a 45-house town of plain
   coloured blocks with Cairo or GSK at rest, the same layer surface. Do not replace the page. The lead puts the
   choice to the owner with both numbers.
5. **Guard the result:** a local acceptance test (run by name on AresOS, behind an explicit environment switch,
   not in hosted CI) that runs the set-up S fixture three times and fails when the median is above the final median
   plus the larger of 15 % and three times the spread you measured. It fails, never skips, when a prerequisite (the
   compositor, the layer library, WebKitGTK) is missing while the switch is on.

## Acceptance

- The touched test modules pass, each run by name (never the whole `os/tests`, never `test_owner_update`). 53c's page
  checks and pictures still pass and look the same; new pictures go to `reviews/53e-home-memory/pictures/`, never into
  53c's folder.
- `reviews/53e-home-memory/REPORT.md` in the AGENTS.md format with a table: each change, the total before and after,
  per process, for both set-ups; what was kept and why; the floor if above target; the native prototype's number if
  measured.
- Commit in small commits on `pkg/53e-home-memory`, push, and open a PR against main (draft until 53c is merged; the
  lead rebases). Start one hosted run (`gh workflow run "OS image" --ref pkg/53e-home-memory -f checks_only=true`) after
  the last push. Push, then stop: never wait for or watch CI. Do not merge.

## Machine rules

53c's apply: headless compositors only, every run private (own `HOME`, `XDG_*`, session bus, stand-in helper), never
the owner's session (`wayland-0`), his `.minecraft`, Lunar Client or `~/AresOS-try`. Never wake the NVIDIA card. One
engine at a time; stop every process you start. No game, no Gradle, no client-test lock.

## Out of scope

The game's memory (`linux-hub`). The supervisor's scope and `MemoryHigh` (23c). A change to how the page looks.
