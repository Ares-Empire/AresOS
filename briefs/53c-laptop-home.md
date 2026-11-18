# 53c: the laptop home, the window program and the page

Board #335, brief 306, step 3 of `docs/design/LAPTOP-HOME.md` section 9. OS package: a new program and its page in
the image tree, tested against a stand-in helper. The lead's handoff for the whole build is
`briefs/53-laptop-home-build.md`.

**Builder:** Codex `gpt-6.2-sol` `xhigh`, in **two runs** (CLAUDE.md, "Builders work in steps"): run A the window
program, run B the page. Each run commits, pushes and keeps `reviews/53c-laptop-home/PROGRESS.md` true (done, left in
order, what the code doesn't show); run B deletes it. The look is already designed and drawn: this ports the study's
day street and checks it against its pictures, which suits Sol. If the page fails review twice, the lead moves it to
a Fable agent.
**Review:** a fresh Codex `gpt-6.2-astra` `high`, read-only, with one focused security pass on the token, `LD_PRELOAD`,
the `aresos-home:` scheme and what the page can reach.

## Why

With the monitor in, the world runs on the monitor and the laptop's own screen shows only the plain background. The
owner chose a home for that screen (section 10): his town from the side, by day, on terraces, apps dimmed until used
and lit while open, only the clock, date and battery besides, a typing line to find and open an app. 53a gave the
helper what such a view needs. This package builds the program and the page. Nothing starts it yet: starting and
stopping it is package 23c's (`linux-aresos`).

## Read first

`docs/design/LAPTOP-HOME.md` sections 1 to 6 and 11 (11.6 is the layout he chose), section 9 step 3 and its "For the
build brief" list. The study: `reviews/44-laptop-home/prototypes/street/` and `prototypes/shared/` (the page to port),
`reviews/44-laptop-home/tools/shots.sh` and `webkit-shot.py` (pictures and checks), `reviews/44-laptop-home/pictures/`
(the `day2-*` set is the target), and its `REPORT.md`, `REVIEW-2.md` and `REVIEW-3.md`. The 1.2 contract is section 5
with the example messages in `mod/src/test/resources/shell-1.2/`. `os/config/usr/libexec/aresos-shell` for the two
helper changes below and for how `aresos.cover` is left out of window tracking.

## Run A: the window program

1. **The program** `os/config/usr/libexec/aresos-laptop-home` (Python, GTK 4, WebKitGTK 6.0, `gtk4-layer-shell`),
   following section 4's rules and section 6's "A layer surface, not a window":
   - the background layer on the output whose connector starts with `eDP`, anchored to all four edges, keyboard
     "on demand";
   - the fallback without the layer library: a normal window with app ID `aresos.laptop-home`, full screen on that
     monitor, refusing to close.
2. **The secrets.** It reads `ARESOS_VIEW_TOKEN`, then removes it and `LD_PRELOAD` from its own environment
   (`os.environ` and the C environment) **before** the web view exists, so the engine's processes never inherit
   them. `__EGL_VENDOR_LIBRARY_FILENAMES` and `VK_DRIVER_FILES` stay. Nothing it logs or gives the page holds the
   token, a path to the socket or a command.
3. **The scheme.** The page loads from `aresos-home:` served from `/usr/share/aresos/laptop-home/` only (no `..`,
   no symlinks out). Register it as secure and CORS-enabled, with `text/javascript`, `text/css`, `application/json`
   and the font and image types the page uses. `aresos-home://icon/<app id>` serves only the file the helper gave
   as that app's `icon`, with the size and type limits the mod uses for icons (a regular file, at most 1 MiB, PNG
   or SVG). Every other address is refused. Ephemeral network session, no developer tools, no context menu, no
   downloads, no new windows.
4. **The connection** as a 1.2 view (section 5): `hello` with `instance`, `token`, `"role": "view"` and the view
   name `laptop-home`. Then `get_home` (all pages), `list_apps`, and the events. Reconnects after 0.5, 1 and 2
   seconds, then every 2 seconds; in between the page keeps the last town, with opening switched off. The last
   complete home is kept in `$XDG_STATE_HOME/aresos/laptop-home/home.json` (written atomically, mode 0600) and shown
   at start until the helper answers. On `apps_changed` it reads `list_apps` **and** `get_home` again (catalogue
   changes can change which houses the home shows).
5. **`window.aresosHome`**, exactly as section 4's table: `home()`, `programs()`, `open(id)`, `status()` and the
   events `home`, `programs`, `running`, `status`, `helper`. The battery comes from UPower over D-Bus, or
   `/sys/class/power_supply` when UPower is missing. Missing battery: `status()` says so and the page shows none.
6. **The helper's two changes** (53a's REVIEW-2, `reviews/53a-shell-views/REVIEW-2.md`):
   - leave app ID `aresos.laptop-home` out of covering, the return of focus and the unknown windows, as
     `aresos.cover` is left out;
   - a view's `open_app` does not call `cancel_returns()`: only the desktop's opens cancel a pending return.
7. **The stand-in helper** for tests: a small 1.2 view server in `os/tests/` that answers from the example files
   and can drop and come back, publish a new home, change `apps_running`, and refuse.
8. **The vendor pin from the first run.** Every run of the program in tests sets `__EGL_VENDOR_LIBRARY_FILENAMES`
   and `VK_DRIVER_FILES` as section 4 gives them, so the NVIDIA card is never woken. A test runs the program in a
   headless compositor and checks that neither it nor any of the engine's processes maps a library with `nvidia` in
   its name (`/proc/<pid>/maps`).

**Run A's tests** (new modules `os/tests/test_aresos_laptop_home*.py`, run by name, never the whole `os/tests`):
the token and `LD_PRELOAD` are gone from the program's environment and from every engine process's
`/proc/<pid>/environ`; the scheme serves the page with the right types, refuses `..`, a symlink out, other schemes,
`http(s):` and `file:`; the icon address serves only the helper's path for that ID; reconnect timing, opening off
while the helper is away, the kept home at start; the vendor pin; the helper's two changes, in its own test modules.

## Run B: the page

1. **The page** `os/config/usr/share/aresos/laptop-home/`: plain HTML, CSS and JavaScript modules, no build step.
   Port the study's day street on terraces (11.6) with night as the second look in the same page (section 10
   question 2): the town from section 3 (houses from places, gaps, the sliding street), the finder with generic names
   and keywords, the hotbar, opening, the dimmed and lit houses (by day paler, section 11.3), the clock, date and
   battery, "Opening is back in a moment" while the helper is away. Its data comes only from `window.aresosHome`.
   Fonts: Space Grotesk from the image, JetBrains Mono from `/usr/share/fonts/aresos/` (in the image from R29,
   `linux-aresos`); until then the page falls back to a monospace font without breaking its layout.
2. **The checks**, carried over from `shots.sh check` into the build's tests, with the review findings section 9
   lists:
   - every check of the study, Night street's own included;
   - the day's grid check, plus REVIEW-3 finding 6's two breaks: each street's plot count equals `cols` unless that
     street has a house past `cols`; and the terraces' turf and bank sit on their streets (derive the stops from the
     same numbers, or sample the picture's pixels at each street's turf and road rows);
   - a failed check fails the test (the study's `shots.sh check` exited 0 on a non-empty `wrong`);
   - the rest check: at rest no animation runs and nothing changes but the clock (and at night the one star); also
     count frame callbacks, so a canvas drawn again every frame is caught;
   - a framed house beside a cut end fades from `EDGE/2` to `EDGE`, not inside the day's fade;
   - REVIEW-2 nit 7: while typing, an end sign counts how many of its hidden houses match; the page gives the street's
     current offset each frame for the companions later.
3. **Pictures** from a headless compositor, as the study's tool takes them, under `reviews/53c-laptop-home/pictures/`:
   day and night each, home, forty-five apps, typing, an open app lit, the helper away. Test apps have generic names
   ("Test Web 1") and generated pictures; never a real app icon or a picture of the owner's screen. Look at every
   picture yourself and compare with the study's `day2-*` set.
4. **Motion set-ups** (REVIEW-2 should-fix 3): if you measure motion, record each set-up's full environment and what
   its numbers leave out, next to the numbers.
5. **Image check:** a test that WebKitGTK 6.0 and its Python binding (`gi` with `WebKit` 6.0) are in the image.
   gtk4-layer-shell and JetBrains Mono get their checks in `linux-aresos`'s R29 image package, not here.

## Acceptance

- Run A's and run B's tests pass, each module run by name. One hosted run for the full count: `gh workflow run "OS
  image" --ref pkg/53c-laptop-home -f checks_only=true`, then `gh run watch <id> --exit-status --interval 60`.
- The pictures exist, match the study's day look, and the report says where they differ and why.
- `reviews/53c-laptop-home/REPORT.md` in the AGENTS.md format: the memory measured at rest with the pin (section 4
  expects about 150 to 180 MiB), and what only the laptop trial can check (the real chips, a click from the world,
  the monitor plugged and unplugged).

## Machine rules

- **Headless compositors only** (`cage` as `shots.sh` does, or a headless `labwc` for the layer surface; remove
  `DISPLAY`, `WAYLAND_DISPLAY` and `WAYLAND_SOCKET` first). Never open a window in, reconfigure or send input to the
  owner's session (`wayland-0`). Never touch his `.minecraft`, Lunar Client or `~/AresOS-try`.
- No client-test lock is needed. No Gradle, no game.
- Keep memory light: one engine at a time, and stop every compositor and engine process you start.

## Out of scope

The supervisor (`aresos-desktop`): starting and stopping the program, its scope and `MemoryHigh`, the token's making,
the restart rule (23c). `rc.xml`. The mod. Super's search (53d). The image packages (R29, `linux-aresos`). The
companions (section 7).
