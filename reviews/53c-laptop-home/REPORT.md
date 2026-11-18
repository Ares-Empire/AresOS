# 53c laptop home

## Done

- **Run A.** `aresos-laptop-home` opens a GTK 4 WebKitGTK 6.0 background surface on the eDP output with
  on-demand keyboard focus. Its fallback is a fullscreen `aresos.laptop-home` window that refuses to close.
  The program removes the view token and `LD_PRELOAD` before creating WebKit, retains the Mesa/Intel vendor
  pins, and serves packaged resources and validated PNG icons from a restricted, ephemeral view.
- The 1.2 view reads every page of the town and catalogue, joins display names, and atomically saves complete
  towns. It replays the initial running apps and power state to the page. A helper restart keeps the last
  complete town, disables opening while disconnected, and reenables it on a null-revision reconnect with fresh
  running IDs. A published empty town clears the saved town. The [bridge contract](../../os/config/usr/share/aresos/laptop-home/BRIDGE.md)
  describes the fields, events and geometry.
- The shell helper excludes the fallback window from covering, focus returns and unknown windows. Desktop
  launches still cancel pending returns. View launches leave them in place.
- **Run B.** The packaged HTML, CSS and JavaScript draw the four day terraces and the night street from the
  same bridge. Houses use published blocks and places, including holes. The page implements the finder, arrow
  navigation, the nine-slot hotbar, launch feedback, running lights, clock, date and battery. Street-end signs
  count hidden matches while typing. The geometry snapshot reads the current transform as houses and roofs
  slide. Day roads stay fixed.
- The paged stand-in and headless harness drive both looks of the packaged page and record the actual
  `open_app` requests. The image script adds the WebKitGTK 6.0 Python import check for R29.
- **Review 1 fixes.** The shell helper clears the foreground app when no app toplevel has focus and preserves the
  short close handoff. The laptop home reads and writes a cache sized for 200 houses with maximum-width names and
  sends authenticated running IDs to the page while the initial catalogue read is pending. The day grid test now
  checks painted slabs and turf and compares the rendered house bounds across all four streets after a slide.

## Verified

Each OS test module ran by name. The tests ran one engine at a time in a private home, state, runtime directory
and D-Bus session. The environment set `TMPDIR="$PWD/.work/tmp"`. The following commands are from the worktree
root.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_shell_views.py'` | 26 tests, `OK` |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home.py'` | 9 tests, `OK` |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_webkit.py'` | 2 tests, `OK` in the fullscreen fallback |
| `LAPTOP_HOME_TEST_LAYER_DIR=.work/layer-test/extracted/usr/lib64 LAPTOP_HOME_TEST_PSS=1 python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_webkit.py'` | 2 tests, `OK` on the background layer |
| `LAPTOP_HOME_TEST_LAYER_DIR=.work/layer-test/extracted/usr/lib64 LAPTOP_HOME_TEST_PSS=1 LAPTOP_HOME_TEST_PICTURES=1 python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_page.py' -v` | 3 tests, `OK` on the background layer in two runs |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_page.py' -v` | 3 tests, `OK` in the fullscreen fallback |
| `bash -n os/ci/image-checks.sh` | Exit 0 |
| WebKit import block from `os/ci/image-checks.sh`, run locally with `env -i HOME="$PWD/.work/tmp" PATH=/usr/bin /usr/bin/python3 -` | `LAPTOP_HOME_WEBKIT 2 54 1` |
| `git diff --check origin/main...HEAD` | Exit 0 |
| Repo privacy workflow's shell check, run locally | `No file holds a home path with a real user name.` |

The bridge checks cover startup replay, the kept town and null/empty revisions, the fallback window and real
layer properties, resource policy, and seeded environment variables. Python and libc lose the token and
`LD_PRELOAD`. WebKit child environments contain the vendor pins. The program and engine process maps showed
zero NVIDIA libraries. The layer library and typelib were extracted inside `.work/` from Fedora's
`gtk4-layer-shell-1.3.0-1.fc44.x86_64.rpm`. `rpm -K` printed `digests signatures OK`.

The page checks cover click, hotbar keys and clicks, finder ranking and catalogue pictures, arrow navigation,
failure feedback, running lights and offline launches. Both looks preserve places around a removal, reveal a far
house, report the hidden counts, and expose intermediate slide geometry. The day grid checks 1, 24 and 45 houses,
verifies each side's exact plot count, and samples all four terraces' road, turf and bank pixels. At rest over
13 seconds, the page checks observed zero animation starts, canvas draws, frame callbacks or unexpected DOM
changes. Night changes one star every four seconds. The clock can tick once a minute in either look.

### Review 1 verification

The modules ran one at a time with `TMPDIR="$PWD/.work/tmp"`. The page tests used private headless labwc and the
fullscreen fallback. The helper tests cover the layer surface's lack of a foreign toplevel and the filtered fallback
window. Closing the foreground editor returned to the world. Closing the editor after either home focus transition
left the keyboard at home, and a later app activation did not renew an expired handoff.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_page.py' -v` | 4 tests, `OK` |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home.py'` | 11 tests, `OK` |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_shell_views.py'` | 27 tests, `OK` |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_shell.py'` | 75 tests, `OK`. Python 3.14 emitted unclosed-socket `ResourceWarning`s in the shell test module. |
| `git diff --check` | Exit 0 |

The maximum-width UTF-8 fixture round-tripped at 181,615 bytes. The 161,904-byte headless fixture kept all 200
houses on screen after a null revision. Its running house was lit on the first draw with the final catalogue page
held back. The bridge refused an open during that read and enabled opening when the last page arrived.

For the negative grid check, I removed the `.day .plots` background declaration from a temporary copy of `home.css`
and ran `LaptopHomePageTest.test_day` with that copy in headless WebKit. It exited 1 with `FAILED (failures=1)` at
the first `empty plot slab` sample. The pixel at `(1170, 309)` was turf `(138, 178, 84)` and the test expected the
slab's `(185, 199, 162)`.

### Pinned memory at rest

These are summed PSS from `/proc/<pid>/smaps_rollup` for the GTK program and WebKit's web and network processes.
The second packaged-page pass measured after the 13-second idle check, with 44 houses in the 45-place town and
47 catalogue entries. The earlier pass measured 319 MiB by day and 314 MiB by night on the same setup.

| View | GTK program (KiB) | Network (KiB) | Web (KiB) | Total (MiB) |
| --- | ---: | ---: | ---: | ---: |
| Run A bridge fixture, repeated in Run B | 155,859 | 22,817 | 72,413 | 245 |
| Packaged day page | 187,708 | 22,068 | 124,365 | 326 |
| Packaged night page | 187,698 | 22,416 | 118,374 | 321 |

Run A originally measured 244 MiB after eight idle seconds with 43 houses and 44 catalogue entries.
Both runs used headless labwc 0.9.6 with pixman, GTK with Cairo, WebKitGTK 2.54.1, `LIBGL_ALWAYS_SOFTWARE=1`,
`WEBKIT_DISABLE_DMABUF_RENDERER=1`, and the Mesa EGL/Intel Vulkan vendor files named in the design.
The finished page ran at 1920 × 1080 with the layer-shell library loaded. The totals exceed the design's
150–180 MiB estimate and exclude the compositor and GPU allocations. These are memory samples. The motion
checks counted browser activity and did not measure CPU load.

### Pictures

I inspected all ten 1920 × 1080 WebKit snapshots from the headless compositor. The day page keeps the
study's shared grid, horizon at the top tread, equal full-width roads, turf, banks and spacing.
The generated logos and counts come from the test town. The page uses the live clock and the stand-in's
68% charging battery, and the opened pictures show the running door, sign and hotbar mark with the whole town
visible. The typing pictures use `tool19` to show the frame after a slide. The helper-away pictures show the
retained town and running light with the offline message. The day end fade is narrower so the framed house
stays clear. The night captures keep the stars, short roads, gaps between houses and glowing open doors.
The capture home had the study's fonts, including a Space Grotesk file identical to the image's.

| State | Day | Night |
| --- | --- | --- |
| Home | [Day](pictures/day-home.png) | [Night](pictures/night-home.png) |
| Forty-five houses | [Day](pictures/day-forty-five.png) | [Night](pictures/night-forty-five.png) |
| Typing | [Day](pictures/day-typing.png) | [Night](pictures/night-typing.png) |
| Running app lit | [Day](pictures/day-opened.png) | [Night](pictures/night-opened.png) |
| Helper away | [Day](pictures/day-helper-away.png) | [Night](pictures/night-helper-away.png) |

The comparison used the study’s [day home](../44-laptop-home/pictures/day2-1-home.png),
[day grid with 45 houses](../44-laptop-home/pictures/day2-8-forty-five-apps.png),
[day finder](../44-laptop-home/pictures/day2-2-finding.png),
[day opened](../44-laptop-home/pictures/day2-4-opened.png) and
[night far house](../44-laptop-home/pictures/street-9-far-house.png).

No files over 500 MB remained in `.work/`.

## Not verified

- The laptop trial with the game and external monitor still needs to check which chips GTK and labwc draw on,
  a click from the world and keyboard focus, Alt+Tab, a maximized app over the home, plugging and unplugging,
  a game restart, and memory and motion cost in the real session.
- The WebKit import block ran on the local machine. The image-level check is pending R29.
- The checks-only workflow was dispatched for `74ec9b3f`. The lead will collect the result.
  [OS image run 44362345145](https://github.com/Ares-Empire/AresOS/actions/runs/44362345145)
- The Review 1 fixes dispatched checks-only at `4098b4a5`. The result is for the lead to collect.
  [OS image run 44365447042](https://github.com/Ares-Empire/AresOS/actions/runs/44365447042)

## Known limits

- Mapping the fullscreen fallback can take focus from the world during an unattended start. Package 23c's restart rule must account for this.
- A launch that fails after the helper reports `starting` leaves the page without a reason for the failure.

## JUDGMENT-CALL

- The packaged page selects day in its entry point and keeps night in the same modules. A theme picker would add
  a visible control before the laptop trial. A later preference can select the existing look with one startup setting.
- When a cut end hides houses but none match, the sign shows zero and still lets the owner pan. Hiding the sign
  would remove that route through the street during search. Changing this later is limited to the end-sign rendering.
- The first draw waits for the bridge replay and gives the initial lookup up to 500 ms after the resource filter is
  ready. A longer wait would also hold back the kept town when the helper is away. Changing the wait costs one
  startup policy change.
- The compositor can report deactivation before a real close, and focus on a layer surface also leaves no active
  app toplevel. The helper retains the existing half-second handoff for that ambiguity. Dropping the handoff would
  break genuine closes delivered across compositor reads. Distinguishing the two within the interval would require
  a compositor focus signal for the home.

## PLAN-GAP

- The study's 150–180 MiB estimate needs a real-session measurement. The pinned, software-rendered totals above
  are the current headless measurements.
- Package 23c provides the supervisor's token, environment, start/stop and screen moves. R29 provides layer-shell,
  JetBrains Mono and their image checks. The page resolves system fonts by name and has a monospace fallback.

## Open questions

- Does real-session PSS leave enough room alongside Minecraft during the dual-monitor trial?
