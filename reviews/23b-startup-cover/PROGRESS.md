# 23b: the AresOS startup cover — progress and report

Builder: Claude agent (Opus 5.5), step 1, 2026-11-15. Branch `pkg/23b-startup-cover`, draft PR #70.
Status: **built as the brief says; stopped on two PLAN-GAPs** (below) that need the integrator's call before review.
Nothing here was run on the owner's screen: every graphical run was a headless labwc of its own.

## Done

- **`os/config/usr/libexec/aresos-cover`** (new, 0755): Python, GTK 4 through `gi` (Gtk 4.22 here), drawn with
  cairo and PangoCairo; no new package. One undecorated window, app-id `aresos.cover` (GLib program name; no
  GApplication, so no D-Bus needed), title `AresOS`. It draws only: a vertical gradient `#1a191e` (top) to
  `#0d0d10` (bottom), `AresOS` centred in Space Grotesk bold `#f3f1ea` at 1/12 of the window height, and under it
  `Starting your home screen…` (or `Starting again…` with `--again`) in Space Grotesk regular `#a6a39a` at half
  that. The family is `Space Grotesk,sans-serif`, so Pango falls back to the default sans when the font is missing
  (it is missing on this laptop's image: the headless screenshot shows the fallback). No focusable widget; a close
  request (Alt+F4) is refused. It ends on SIGTERM (exit 0) and by itself after 600 s (`--limit`, hidden, only
  shortens it, for tests). Without a display it exits 1 at once.
- **The supervisor (`aresos-desktop`)**:
  - Starts the cover in `start_launch`, after the state is entered and **before Prism**, only for a hub launch that
    is not automatic and was asked for with `cover=`: `start()` asks for it (`COVER_FIRST`) only when the
    session's runtime file does not exist yet (the session's first supervisor); `retry()` asks with `COVER_AGAIN`
    (`--again`). Never: an automatic restart (`restart_launch`, `automatic=True`), setup mode, a launch Prism
    started by hand, an adopted game, a supervisor restarted mid-session, the late `new_session()` start.
  - Stops it in `enter()` whenever the state is not STARTING, before any message window opens: `world_ready`
    (IN_WORLD), SETUP, AUTH_REQUIRED, RECOVERY (the slow-start view is RECOVERY `slow_start`). These are exactly
    the brief's events: the only states besides STARTING. And in `Loop.close()` when the supervisor stops.
  - Stop = SIGTERM now, SIGKILL after `COVER_STOP_WAIT` (2 s) through the supervisor's own timer (`pending()`),
    never a wait; only shutdown waits (at most 2 s, like the view's 5 s).
  - The cover is a plain child of the supervisor (its scope; never `systemd-run`, never the game's scope) with
    `session_environment()` (the views' cleaned environment: no launch secrets, the system PATH), stdin/out/err
    to /dev/null, and PDEATHSIG SIGTERM like the views.
  - Failure is one log line: a cover that cannot start (`OSError`, `SubprocessError`) or that ends by itself
    (`on_cover_exit`) changes nothing else. `status` shows `cover`.
- **labwc** (`rc.xml`): one new rule after the hub's, which is unchanged byte for byte:
  `<windowRule identifier="aresos.cover" serverDecoration="no"><action name="ToggleFullscreen" /><action name="ToggleAlwaysOnTop" /></windowRule>`.
  The cover itself does not ask for fullscreen: labwc runs the rule's ToggleFullscreen at first map, which would
  toggle a fullscreen request of its own off again (labwc has no plain "Fullscreen" action and no fullscreen
  query for `If`).
- **Focus (brief point 4):** package 23 does nothing of its own at a start: labwc focuses the new Minecraft window
  when it maps, and the helper (aresos-shell) follows the active window. With the cover: labwc still focuses
  Minecraft on map (the cover stays above it, always on top); if the cover held the focus when it closes, labwc
  focuses the topmost remaining window, the hub. So the hub has the focus after `world_ready` either way. The
  cover's window has no reviewed identity in the helper, so it is "nobody's" (OS-BASE B1 window ownership): it
  confirms no launch and forces no return. Not proven with a real game (no game in the VM); see Not verified.
- **`os/build.sh`**: `/usr/libexec/aresos-cover` joins the chmod 0755 list.
- **Image checks** (`os/ci/image-checks.sh`): the cover is in the required startup commands (and the supervisor's
  absolute paths are checked as before); present, executable, `root:root 755`; its rule is in rc.xml (the hub's
  line is still grepped as before); as ares it loads GTK 4, Pango and cairo and parses its arguments; `fc-match
  'Space Grotesk:bold'` gives package 31's `/usr/share/fonts/aresos/SpaceGrotesk-Variable.ttf`.
- **VM check** (`os/ci/overlay/checks.py`, `os/ci/vm.py`): new guest steps `cover` and `cover-stop` after the
  `aresos-labwc.png` screenshot. The guest starts the real cover as ares in the labwc session (the supervisor's
  `WAYLAND_DISPLAY`), waits with `grim` until both screen corners carry the cover's colours, the host takes
  `aresos-cover.png` and checks the same corners, then the guest sends SIGTERM and requires exit 0 within 2 s, and
  the host takes `aresos-cover-stopped.png`.

## Verified (on the laptop, 2026-11-15)

- `python3 -m unittest discover -s os/tests -p 'test_aresos_desktop.py' -k CoverTest -k SessionFilesTest`:
  `Ran 18 tests … OK`. `-k LoopTest`: `Ran 23 tests in 68.2s OK` (6 new).
- Whole module `test_aresos_desktop.py`, first run: `Ran 172 tests in 167.9s FAILED (failures=1, skipped=1)`.
  The failure was `RestartPolicyTest.test_deadlines_never_spin_after_their_action`: it requires `pending() == []`
  right after a slow start and a quit, but the slow-start view now stops the session's cover, whose SIGKILL is
  legitimately due 2 s later. The test now also checks that timer (exactly one item, due at +2 s, fires once,
  then `pending() == []` and `deadline() == 30.0`); nothing it checked before was removed. Second whole run: see
  the PR description.
- `test_aresos_cover.py` (new), twice: `Ran 9 tests in 6.0s OK`, then `OK` again, nothing skipped here.
- Modules that read files changed here, one at a time: `test_everyday_account` 34 OK, `test_journal_ready` 6 OK,
  `test_aresos_shell_icons` 43 OK, `test_owner_path` 47 OK, `test_release27` 41 OK.
- Headless labwc by hand with the repo's rc.xml (`WLR_BACKENDS=headless`, own `XDG_RUNTIME_DIR`): corners
  `(26,25,30)` top and `(13,13,16)` bottom, the word in `(243,241,234)`; a red foot window started afterwards stays
  hidden under it; SIGTERM ends it with exit 0 in 0.07 s and the foot window shows. Screenshot:
  `reviews/23b-startup-cover/screenshots/cover-headless-labwc.png` (fallback sans: the laptop's image has no Space
  Grotesk yet).

Tests added:
- `CoverTest` (13, fakes): first hub launch covered before Prism; stays over the game's start; `world_ready` stops
  it with SIGKILL due exactly 2 s later; retry covers with `--again` before Prism; retry while the game runs starts
  none; an automatic restart is never covered (and still gets `ARESOS_SHELL_KEEP_FOREGROUND`); setup never; a
  restarted supervisor never; entering SETUP, AUTH_REQUIRED, RECOVERY (`prism_failed`) and the slow-start view each
  stop it before their window opens; a cover that fails to start (ENOENT, EACCES, preexec failure) leaves a whole
  session (start, hub, crash, restart, hub: states, counts, Prism commands, helpers, views) identical; a cover that
  dies changes nothing.
- `LoopTest` (6, the real loop and a shell stand-in): the cover is the supervisor's child in its cgroup with the
  cleaned environment and no arguments, ends when the hub is ready while the game goes on; one that ignores
  SIGTERM is SIGKILLed about 2 s later while the supervisor answers at once; it ends when the supervisor stops; a
  missing or crashing cover leaves the start as it was; retry through the socket starts one with `--again`.
- `SessionFilesTest`: the rule's attributes and actions, the hub's line byte for byte, the cover executable and in
  build.sh, `COVER` absolute.
- `test_aresos_cover.py`: arguments, limit, look (colours, darker bottom, sizes, font fallback), loads without gi;
  no display → exit 1 at once; in a headless labwc with the image's rc.xml: fullscreen, borderless (both corners),
  word and line in their colours, above a later window, SIGTERM → exit 0 within 2 s and gone from the screen;
  `--again` changes only the line; `--limit 1.5` ends by itself with exit 0. The display tests skip where GTK 4,
  labwc or grim are missing (the hosted runner, most likely).

## What the VM check build can show (dispatch needed: yes)

The brief's two screenshots (the cover during STARTING, the world after `world_ready`) **cannot be taken in the
VM**: a fresh VM has no Microsoft account and no hub world, so the supervisor is in SETUP, where the cover is
never shown, and no Minecraft runs there at all (package 23's report: "the VM has no game window"). What the VM
can show, and now checks: the real cover from the image in the real labwc session, fullscreen above the SETUP
view, Prism's sign-in window and the recovery terminal (`aresos-cover.png`), and the session again after SIGTERM
(`aresos-cover-stopped.png`). The image checks run there too. Image build inputs changed (new file, build.sh,
rc.xml, image-checks.sh, VM scripts), so the integrator should dispatch a check build with VM
(`check_build=build`) and a `checks_only=true` run for the hosted suite. Neither has run yet.

## Not verified

- A real start with the cover: Minecraft's window under it, the hand-over of focus when it closes, the time from
  login to the cover. Needs the P3 trial on the laptop (or a VM with an account and a hub, which CI has not).
- Space Grotesk in the drawing (the laptop's current image lacks the font; the image check proves fontconfig
  finds it in the new image, not the picture).
- GTK's renderer on the NVIDIA laptop (the cover uses the default GPU; headless it used software).

## JUDGMENT-CALLs (for the owner)

1. **Gradient direction.** As the brief says: `#1a191e` at the top, `#0d0d10` at the bottom, so it is darker at
   the bottom as `linux-hub` described; its colour order said the opposite. Changing it: swap two constants.
2. **A crash during the covered start keeps the cover through the automatic restart.** The brief's stop list
   has no "crash"; the cover is not *started* for the restart, it is still up from the session start (the state
   stays STARTING, reason `restarting`). He sees one calm screen until the hub is ready, or the recovery window
   after the third crash. Side effect: the restarted hub's helper keeps the window that was in front before the
   new hub window (`ARESOS_SHELL_KEEP_FOREGROUND`), which is then the cover; the hub gets the focus when the cover
   closes (labwc focuses the topmost window). Alternative: stop the cover on `schedule_restart` (one line); then the
   restart shows Mojang's loading screen again.
3. **Only the session's first supervisor covers.** A supervisor restarted by its keeper mid-session, and the late
   start after an earlier session's end is explained (`new_session`), show no cover: neither is "session start",
   and both may come while he uses an app. Changing it: one condition in `start()`.

## PLAN-GAPs (the step stops here; nothing below is built)

1. **Prism's own dialogs during a hub launch are hidden under the cover.** The brief keeps the cover away from
   SETUP and AUTH_REQUIRED "where his sign-in in Prism must be visible", but in the code a hub launch's sign-in
   happens while the state is STARTING: AUTH_REQUIRED starts only after Prism has *ended* without a game
   (`prism_gave_up`), and START_TIMEOUT counts from Java's start. Prism refreshes the Microsoft account at every
   launch; when that fails (Wi-Fi not connected yet right after login, an expired account) it shows a dialog and
   waits for him: "Account refresh failed", the offline player name, "Continue launch?", or the refresh progress
   with "Play Offline". Package 23's report promised "Prism shows its own dialog". With the cover on top (and the
   keyboard focus in that hidden dialog) he would see "Starting your home screen…" for up to the cover's 10 minutes.
   Options:
   - (a) accept it as built;
   - (b) **recommended:** also stop the cover when the start has not reached the hand-off (the wrapper's
     `jvm_start`) within about 20–30 s of Prism's start (one more `pending()` item and its tests). A normal hub
     start reaches it in seconds; a Prism that waits for him is then visible;
   - (c) start the cover at the hand-off instead of before Prism (Prism's dialogs are never covered; its small
     launch dialog is no longer covered either);
   - (d) a labwc rule that keeps Prism's windows on top too (its launch dialog then shows above the cover).
2. **Super+Ctrl+Escape's recovery terminal opens under the cover.** The cover is always on top, so the terminal
   the shortcut opens is hidden until the cover ends (the hub ready, a message window, START_TIMEOUT, or 10
   minutes). OS-BASE section 6 says "Keep errors and terminal access visible"; Ctrl+Alt+F3 still works. Options:
   accept; or let the shortcut also end the cover (a second `Execute` in the same keybind, for example a new
   `aresos-desktop` op that calls `hide_cover()`; the image checks and `SessionFilesTest` grep the keybind and
   would follow). Recommended: the shortcut ends the cover; small.

## Left, in order

1. The integrator decides the two PLAN-GAPs (and whether the JUDGMENT-CALLs go to the owner as they are).
2. Build the chosen fixes (a fresh step), dispatch the check build with VM and `checks_only`.
3. A fresh review (Opus, or Codex from 2026-11-17). The last step deletes this file; the report text goes to
   `REPORT.md` through the integrator.

## What the code doesn't show

- Which starts are "the session's first": the runtime file in `XDG_RUNTIME_DIR` (tmpfs, gone at logout and
  reboot) decides; a supervisor that crashed before writing it once is treated as the first.
- The hand-over of focus relies on labwc focusing a newly mapped window under an always-on-top one, and focusing
  the topmost window when a focused one closes (labwc 0.9.6); seen headless only for stacking, not for a game.
- Retry is impossible to type while the cover is up (no visible terminal); a retry during a covered start (from a
  TTY) replaces the cover with an `--again` one.
