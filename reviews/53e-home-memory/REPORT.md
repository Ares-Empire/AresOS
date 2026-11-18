# 53e — Laptop home memory

## Done

- The installed laptop-home program uses Cairo for its GTK window and sets a memory-pressure policy for the WebKit page process. The packaged page, its scheme and request filter, the vendor pins, and the token handoff use the 53c implementation.
- The software fixture measures the real background layer and every WebKit process. It also runs a one-minute companion-canvas workload and a separate native GTK 4/Cairo comparison.
- The local acceptance test takes the median of three fresh software fixtures and fails if it exceeds the reference plus its allowed spread. The test is opt-in on AresOS.

## Verified

**The shipped WebKit home measured 418.1 MiB PSS at rest**, down 105.9 MiB from the matched unforced 53c baseline. The result exceeds the 150 MiB target. The native block-town prototype measured **46.6 MiB PSS** on the same size and layer.

## Method

The baseline is the program and page from `88d5afe6`. The fixture starts with 45 houses across four streets (9, 7, 9, 20), 47 catalogue entries, and the study's Space Grotesk and JetBrains Mono files. Fontconfig matched both files by content. Every run creates a new helper, home, XDG runtime, data, cache and state directories, and private D-Bus and Wayland sockets. It waits for the populated day page, loaded fonts and settled layout, then samples after 15 seconds without any launch or input. The window's GTK layer-shell properties were checked in every measured run, including four anchors, background layer and on-demand keyboard on the 1920 × 1080 headless output.

Set-up S used labwc 0.9.6 with a headless backend and pixman, GTK 4.22.5, Mesa 26.2.4, WebKitGTK 2.54.1 and `LIBGL_ALWAYS_SOFTWARE=1`. The layer shell and typelib came from Fedora's `gtk4-layer-shell-1.3.0-1.fc44.x86_64.rpm` extracted in `.work/`. `rpm -K` printed `digests signatures OK`. [Fedora 44 layer-shell RPM](https://dl.fedoraproject.org/pub/fedora/linux/releases/44/Everything/x86_64/os/Packages/g/gtk4-layer-shell-1.3.0-1.fc44.x86_64.rpm)

The experiment retained the Mesa EGL and Intel Vulkan vendor files named by 53c. The private labwc fixture requests Wayland and omits GTK accessibility bus integration in its minimal session. The final fixture leaves `GSK_RENDERER` and `WEBKIT_DISABLE_DMABUF_RENDERER` unset. It calls the shipped `run()` with only the in-tree page path, headless output selector and stand-in battery substituted. The readiness probe reads the page and renderer before the rest interval.

A preflight with the 53c renderer overrides reproduced the same surface and fixture under its historical software environment. A subsequent unforced preflight showed Mesa inspecting a DRM fd even with software rendering selected. The NVIDIA function was already runtime-active before the experiment. After that observation all matched comparisons ran with Bubblewrap replacing `/dev`, so none could open the host's GPU device nodes. The harness checked the private device view and NVIDIA libraries. The final sampler also verified the WebKit web child’s separate PID namespace and seccomp filter. The old preflight samples are reported separately from the matched suite.

Set-up I was unavailable. As in `mod/dev/client-test.sh`, sysfs identified Intel vendor `0x8086` on `/dev/dri/renderD128`. The NVIDIA vendor `0x10de` function remained runtime-active throughout the read-only checks of `power/runtime_status`, `runtime_active_time` and `runtime_suspended_time`. The suspended counter did not advance. This prevents establishing the asleep-NVIDIA prerequisite. No Intel compositor or GPU probe was started.

The sampler reads `Pss_Anon`, `Pss_File` and `Pss` from `smaps_rollup` and the ten highest-PSS mappings from `smaps` for the GTK program and each WebKit child. The total is summed within each run before taking the median. Shared memory accounts for the difference between total PSS and the two requested PSS categories, with rounding at KiB granularity. These numbers exclude compositor, helper, kernel and GPU allocations. System-wide sharing of library pages can move PSS over time.

### At-rest PSS

Each cell is the median and [minimum–maximum] in MiB of five fresh runs. Each single-change result uses the second row as its before measurement. The first row retains both renderer overrides from the published 53c harness for reference. Set-up I was unavailable for all rows. [Per-run PSS and ten largest mappings](measurements.jsonl)

| Set-up S | GTK window | Web process | Network process | Total |
| --- | ---: | ---: | ---: | ---: |
| 53c with legacy harness renderer settings | 156.2 [155.8–156.3] | 98.0 [97.7–98.6] | 20.7 [20.4–21.1] | 275.1 [274.7–275.6] |
| 53c with renderer overrides cleared | 191.0 [189.9–194.2] | 312.2 [307.5–314.5] | 20.6 [20.2–20.8] | 524.0 [517.6–529.3] |
| GTK disable OpenGL and Vulkan | 105.6 [105.4–106.1] | 97.9 [95.0–98.9] | 20.4 [20.4–20.6] | 224.4 [220.9–224.9] |
| WebKit hardware acceleration policy NEVER | 218.4 [218.1–218.9] | 97.7 [96.3–98.8] | 20.7 [20.5–21.1] | 337.1 [335.7–337.6] |
| JavaScriptCore JIT off | 196.2 [186.8–196.7] | 304.9 [303.8–306.8] | 20.6 [20.0–20.8] | 522.0 [510.5–523.1] |
| GTK Cairo | 138.5 [136.9–138.9] | 319.8 [318.3–320.7] | 20.9 [20.6–21.1] | 479.4 [476.3–479.8] |
| WebKit disable accelerated 2D canvases | 196.3 [191.9–197.7] | 315.9 [311.8–317.3] | 21.0 [20.5–21.1] | 533.2 [524.2–535.9] |
| WebKit DOCUMENT_VIEWER | 192.3 [183.4–192.4] | 311.9 [310.3–313.8] | 20.6 [20.5–20.7] | 524.8 [515.6–526.4] |
| WebKit back-forward page cache off | 191.7 [191.3–192.5] | 312.1 [311.0–313.6] | 20.6 [20.5–20.9] | 524.3 [522.7–526.8] |
| WebKit web and network pressure | 192.2 [191.8–192.7] | 261.8 [260.0–262.3] | 20.5 [20.3–20.7] | 474.5 [472.7–475.3] |
| WebKit web process pressure only | 192.0 [191.0–192.1] | 261.4 [260.1–262.8] | 20.4 [20.2–20.8] | 473.6 [471.5–475.3] |
| WebKit network process pressure only | 191.9 [191.7–192.3] | 313.4 [310.9–314.1] | 20.5 [20.5–20.8] | 525.7 [523.3–526.5] |
| WebKit unused capabilities off | 192.2 [191.3–192.7] | 313.0 [312.3–313.7] | 20.6 [20.2–20.7] | 525.7 [524.3–526.4] |
| GTK process mallopt(M_ARENA_MAX, 2) | 191.0 [190.6–191.5] | 311.0 [308.1–312.0] | 20.4 [20.4–20.7] | 522.4 [519.5–523.2] |
| Python defer asyncio, drop secrets import | 197.0 [195.9–197.3] | 317.0 [315.4–319.0] | 20.9 [20.5–21.0] | 535.0 [533.2–536.5] |
| Page software hint on block-logo canvases | 195.6 [191.1–197.7] | 315.1 [312.3–318.2] | 20.6 [20.4–21.0] | 531.5 [523.8–536.4] |
| WebKit disable Skia compositing | 189.5 [186.9–191.9] | 361.0 [357.8–363.9] | 20.7 [20.5–20.9] | 570.2 [567.1–574.1] |
| WebKit disable accelerated drawing | 196.4 [191.7–198.1] | 316.0 [310.4–318.1] | 20.7 [20.6–20.9] | 533.2 [522.8–537.2] |
| Mesa cap llvmpipe workers at four | 194.9 [183.2–197.2] | 313.3 [312.1–318.7] | 20.7 [20.3–20.8] | 528.9 [517.2–536.6] |
| Launch environment MALLOC_ARENA_MAX=2 | 196.4 [191.0–197.8] | 314.6 [312.1–316.6] | 20.9 [20.3–21.0] | 529.9 [528.2–534.1] |
| Final shipped settings | 132.7 [132.6–132.7] | 264.7 [264.0–266.1] | 20.6 [20.3–20.8] | 418.1 [417.1–419.5] |
| Native GTK 4/Cairo prototype | 46.6 [45.8–46.6] | — | — | 46.6 [45.8–46.6] |

The shipped floor includes about 238.6 MiB anonymous memory, 148.6 MiB file-backed PSS and 31.7 MiB shared memory. The web process accounts for most of it. Its prominent mappings include anonymous drawing allocations, its heap, WebKitGTK code and LLVM used by Mesa's software GL stack. The GTK window also holds two roughly 8 MiB Wayland buffers. The native sample draws 45 coloured blocks with Cairo on an equivalent background surface and has no WebKit processes.

The legacy renderer preflight before the device mask was added measured 263.8 MiB total (261.0–264.2 MiB). Its results are excluded from the matched table. The first GTK OpenGL/Vulkan-off run's mapping parser overwrote its role labels. The table uses a corrected five-run PSS repeat with the same settings. Its original motion counters, which use a separate process-role lookup, are below.

### What shipped

- **Cairo in the GTK window.** Setting `GSK_RENDERER=cairo` before GTK initializes cut the window program's memory and CPU load in set-up S. The program supplies the default itself and honors an explicit renderer choice. WebKit acceleration stayed on. GTK's documentation describes the renderer setting. [GTK 4 runtime options](https://docs.gtk.org/gtk4/running.html#gsk_renderer)
- **Pressure handling in the web process.** The context checks every three seconds against a 96 MiB reference, with the default 33% conservative threshold and an 85% strict threshold. WebKit's kill threshold retains its default of zero. The reference drives trimming and is separate from the measured PSS. A network-only trial used 32 MiB with the same intervals and fractions. The measured reduction came from the web process. [WebKit memory-pressure settings](https://webkitgtk.org/reference/webkit2gtk/2.42.3/struct.MemoryPressureSettings.html)

### Other trials

- Disabling GTK OpenGL and Vulkan together drove WebKit to its software-compositing policy. That and setting WebKit's hardware policy to `NEVER` each fell beyond the allowed frame-rate loss. The GTK-only Cairo choice left WebKit's acceleration available.
- `DOCUMENT_VIEWER` and `enable_page_cache=False` showed no PSS saving on the single local document. The unused-capability trial disabled WebGL, WebAudio, spatial navigation, media source, media capabilities, encrypted media, fullscreen, local and session storage, IndexedDB, Cache API, asynchronous clipboard, gamepads, speech synthesis, notifications, WebCodecs, media session and recording, and offscreen canvas APIs. The installed 2.54.1 introspection API exposes no plugin setting. 53c already disables media, media streams and WebRTC.
- Decoding catalogue images only happens on finder results. The settled fixture uses no catalogue images, 45 block canvases of 90 × 90 pixels, seven 48 × 48 hotbar canvases, and both variable fonts (316 KiB on disk). Keeping the two fonts preserves the page typography. Giving just the logo canvases a software readback hint showed no PSS saving. The entire WebKit 2D-canvas acceleration toggle, Skia composition toggle, and accelerated-drawing toggle also showed no savings. The masked street edge is part of the scene's appearance.
- Disabling JIT showed a small PSS change within the spread of the control. The environment reached the web child. The Python trial deferred `asyncio` to the helper's startup and used `os.urandom().hex()` to avoid importing `secrets`. The helper needs `asyncio` for the fixture and while the home stays connected.
- `mallopt(M_ARENA_MAX, 2)` in the window process and `MALLOC_ARENA_MAX=2` at exec were separate trials. The exec-time result is evidence for 23c’s launcher. Both allocator changes showed no material saving.

### Motion

The test clears and redraws a transparent 1920 × 1080 overlay with an 80 × 80 moving figure every frame for one minute after the fifth rest sample. FPS counts requestAnimationFrame callbacks. P95 is the 95th-percentile interval between callbacks. CPU figures are percentages of one logical core summed over each process's threads. The limit uses the unforced control. The final build had to reach 90% of its FPS and stay within 125% of CPU use for each measured process. The combined build passed both.

| Set-up S | FPS | P95 interval (ms) | GTK CPU | Web CPU | Total CPU |
| --- | ---: | ---: | ---: | ---: | ---: |
| 53c with legacy harness renderer settings | 37.34 | 27.0 | 14.1% | 100.4% | 114.5% |
| 53c with renderer overrides cleared | 61.50 | 18.0 | 378.2% | 391.8% | 770.0% |
| GTK disable OpenGL and Vulkan | 37.19 | 27.0 | 14.2% | 100.3% | 114.5% |
| WebKit hardware acceleration policy NEVER | 35.39 | 29.0 | 136.9% | 100.0% | 236.9% |
| JavaScriptCore JIT off | 61.56 | 18.0 | 305.8% | 298.4% | 604.3% |
| GTK Cairo | 62.04 | 17.0 | 26.4% | 322.1% | 348.5% |
| WebKit disable accelerated 2D canvases | 61.56 | 18.0 | 288.7% | 415.3% | 704.0% |
| Page software hint on block-logo canvases | 61.29 | 19.0 | 381.6% | 397.6% | 779.1% |
| WebKit disable Skia compositing | 61.83 | 17.0 | 288.1% | 451.2% | 739.4% |
| WebKit disable accelerated drawing | 61.49 | 18.0 | 343.6% | 348.8% | 692.4% |
| Mesa cap llvmpipe workers at four | 61.98 | 17.0 | 218.0% | 231.7% | 449.7% |
| Final shipped settings | 62.02 | 17.0 | 26.2% | 287.9% | 314.1% |

### Reproduction and checks

The measurement commands ran from the worktree root with the signed RPM extracted under `.work/`.

```sh
export LAPTOP_HOME_TEST_LAYER_DIR=.work/layer-test/extracted/usr/lib64
git show 88d5afe6:os/config/usr/libexec/aresos-laptop-home > .work/53c-home
python3 os/tests/laptop_home_memory.py --program .work/53c-home --legacy-renderers --motion
python3 os/tests/laptop_home_memory.py --program .work/53c-home --motion
python3 os/tests/laptop_home_memory.py --motion
python3 os/tests/laptop_home_memory.py --native
```

Each run command printed five per-process samples followed by the KiB median, minimum and maximum. The first pressure trials attempted to set a conservative fraction above the then-current strict fraction. WebKit rejected that call, so those samples used its 33% conservative default. I removed the ineffective call and repeated all five final shipped-path runs. Each single-change trial used `--program` with a copy of the 53c program containing its named change. The isolated page trial used `--page` with `willReadFrequently: true` on the logo canvases. The exec allocator trial put the variable in the private launch environment before Python started.

The following commands ran each module independently. The bridge tests exercised the ephemeral session, deny-by-default requests, scheme, vendor pins, stripping the helper token and preload, focus, and reconnect.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s os/tests -p test_aresos_laptop_home.py -v` | `Ran 11 tests in 6.148s`, `OK` |
| `LAPTOP_HOME_TEST_CURRENT_RENDERERS=1 python3 -m unittest discover -s os/tests -p test_aresos_laptop_home_webkit.py -v` | `Ran 3 tests in 3.989s`, `OK` |
| `env -u LAPTOP_HOME_TEST_LAYER_DIR LAPTOP_HOME_TEST_CURRENT_RENDERERS=1 python3 -m unittest discover -s os/tests -p test_aresos_laptop_home_webkit.py -v` (fullscreen fallback) | `Ran 3 tests in 3.676s`, `OK` |
| Page and picture command below | `Ran 4 tests in 56.757s`, `OK` |
| `python3 -m unittest discover -s os/tests -p test_aresos_laptop_home_memory.py -v` | `Ran 1 test in 0.000s`, `OK (skipped=1)` |
| `LAPTOP_HOME_TEST_MEMORY=1 python3 -m unittest discover -s os/tests -p test_aresos_laptop_home_memory.py -v` | `Ran 1 test in 49.137s`, `OK` |
| Opt-in guard with `LAPTOP_HOME_TEST_LAYER_DIR=.work/missing-layer` | `FAILED (errors=1)` with the required layer library and typelib error |

Guard output `S background layer: PSS [426188, 426810, 428535] KiB, median 426810 KiB, limit 492342.6 KiB`. The pinned KiB reference is 428,124 [427,104–429,545]. The limit is 492,342.6 KiB, with the increment set by the larger of 15% of the median and three times the measured spread.

The page command uses 53c’s renderer environment inside the private device view. It exercises the same day, night, finder, launch, panning, rest, reconnect and pixel checks.

```sh
bwrap --die-with-parent --ro-bind / / --bind "$PWD" "$PWD" --dev /dev --proc /proc --tmpfs /tmp -- \
  env -u LAPTOP_HOME_TEST_CURRENT_RENDERERS LAPTOP_HOME_TEST_PICTURES=1 \
  LAPTOP_HOME_TEST_PICTURES_DIR=reviews/53e-home-memory/pictures \
  python3 -m unittest discover -s os/tests -p test_aresos_laptop_home_page.py -v
```

| Picture | Day | Night |
| --- | --- | --- |
| Home | [Day](pictures/day-home.png) | [Night](pictures/night-home.png) |
| 45 houses | [Day](pictures/day-forty-five.png) | [Night](pictures/night-forty-five.png) |
| Typing | [Day](pictures/day-typing.png) | [Night](pictures/night-typing.png) |
| Running app | [Day](pictures/day-opened.png) | [Night](pictures/night-opened.png) |
| Helper away | [Day](pictures/day-helper-away.png) | [Night](pictures/night-helper-away.png) |

I compared all ten pictures with 53c's references. The street geometry, terrace colours, house lights, finder, and offline state matched visually. Six pairs match pixel-for-pixel outside the clock. The remaining differences include night star and caret frames and small colour shifts in the offline transition.

The repo privacy script printed `No file holds a home path with a real user name.` and `git diff --check` exited zero. `find .work -type f -size +500M -print` printed nothing. The checks-only workflow dispatch follows the final push.

## Not verified

The live two-screen session, Intel rendering and its real motion cadence remain for the laptop trial. The native comparison exercises only a stationary block town.

## JUDGMENT-CALL

- Use Cairo for the GTK window while WebKit keeps accelerated page rendering. Turning off WebKit acceleration or both GTK graphics APIs saved more memory, but the test lost about 40% of its frame cadence. Changing the renderer later is a change to the launch default and needs the page and motion checks again.
- Enable cache trimming only for the web process. The network setting gave no material reduction. Retuning the limits affects the next launch and needs a new reference series and guard threshold.

## PLAN-GAP

- The 326 MiB cited in the brief came from 53c's legacy renderer environment, a different town state and prior interaction. On the exact fresh fixture, the matched legacy baseline is 275.1 MiB and the unforced baseline is 524.0 MiB. Removing the harness overrides for the shipped-path comparison changes the drawing pipeline.
- With the renderer overrides cleared, opening animations stalled in the headless pixel checks under unchanged 53c, Cairo alone, and web pressure alone. Granting real focus to the test's background layer did not resolve it. The pixel checks use 53c's renderer environment and their original assertions. The bridge and companion-canvas measurements use the shipped renderer defaults. The live compositor's animation behavior remains for the laptop trial.

## Open questions

- Is the measured WebKit floor acceptable for the home and future companions, given the 46.6 MiB native block-town comparison?
