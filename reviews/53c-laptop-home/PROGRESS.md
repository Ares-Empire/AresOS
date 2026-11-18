# 53c Run A progress

## Done

- The laptop-home program selects the eDP output, creates the background layer surface, or uses a close-resistant
  fullscreen GTK window with app ID `aresos.laptop-home`. The view takes its credentials before loading WebKit
  and keeps the Mesa/Intel environment pin. The resource filter, CSP and navigation policy limit the ephemeral
  view to packaged resources and validated catalogue PNGs.
- The 1.2 view reads both paged lists, joins the house names, saves complete published towns and preserves them
  across helper restarts. The page gets an initial replay and subsequent updates through the
  [bridge contract](../../os/config/usr/share/aresos/laptop-home/BRIDGE.md).
- The shell helper excludes the laptop-home fallback from covering, unknown windows and focus-return decisions.
  Only a desktop launch cancels a pending return at launch time.
- `os/tests/laptop_home_helper.py` supplies generated towns, paging, launch outcomes and helper events.
  `os/tests/laptop-home-page/` is the runnable bridge fixture in the named WebKit test.
  `Headless(root, helper.path, page=page_directory)` runs the real program in an isolated compositor and
  `evaluate(body)` returns the result of a JavaScript function body, including asynchronous ones.

## Verified

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_shell_views.py'` | 26 tests, `OK` |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home.py'` | 9 tests, `OK` |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_webkit.py'` | 2 tests, `OK` using the real fullscreen fallback |
| `LAPTOP_HOME_TEST_LAYER_DIR=.work/layer-test/extracted/usr/lib64 LAPTOP_HOME_TEST_PSS=1 python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home_webkit.py'` | 2 tests, `OK` using the real background layer and on-demand keyboard mode |
| `git diff --check` | Clean |

The layer run used the Fedora 44 `gtk4-layer-shell-1.3.0-1.fc44.x86_64.rpm`. `rpm -K` printed
`digests signatures OK`. Its library and GTK typelib were extracted under `.work/` for the test and removed
afterwards. No files over 500 MB remained there.

## Left in order for Run B

1. Port the day terraces and the night look into the packaged `index.html` and its assets. Use the bridge's
   startup replay before the first draw. Move the study's inline JavaScript into external modules and resolve
   the installed fonts by their local names.
2. Drive the real page through the headless harness and stand-in. Use `streets=(9, 7, 9, 20)` for a 45-position
   town with twenty Tools positions, plus `holes` and `unpinned` as needed. Check visible behavior and
   `helper.opens`. Carry over the study's interaction, grid, fade and rest checks and add the requested pictures.
3. Add the pending WebKit import check for R29. Measure the finished page, write `REPORT.md` and remove this
   handoff. Follow the brief's hosted-check handoff after the final push.

## What the code doesn't show

- Pinned rest PSS in the real layer run was **244 MiB** after eight idle seconds with 43 houses, a 44-program
  catalogue and the bridge fixture. `smaps_rollup` reported 155,184 KiB for the GTK program, 23,036 KiB for the
  network process and 71,906 KiB for the web process. The compositor used pixman, GTK used Cairo and WebKit's
  DMA-BUF renderer was disabled. The result is above the design's 150–180 MiB estimate. It excludes the
  compositor and GPU allocations and does not measure Run B's finished page.
- The tests checked the Python and libc environments and the live WebKit child environments. Both vendor
  pins reached the children. The program and engine process maps contained no NVIDIA libraries. The laptop
  trial still needs to check the actual compositor and renderer chips, a click from the world, and the
  monitor plugged and unplugged.
- The bridge's startup lookup gives the first helper snapshot up to 500 ms once the resource filter is ready.
  It shows the kept town sooner if the helper is already known to be away. Battery branches use a stand-in UPower
  call and synthetic sysfs entries in the tests. The 23c supervisor will supply the production runtime environment.
