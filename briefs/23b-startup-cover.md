# Brief 23b: the AresOS startup cover

Empire brief 293. Integrator: the OS lead (`linux-aresos`), 2026-11-15. Branch `pkg/23b-startup-cover`. Builder: a
Claude agent on Opus (a small, fully specified change to the reviewed supervisor); review: Opus, or Codex from
2026-11-17.

## Why

The owner tried the town (2026-11-15) and said: "Its genuinely a homescreen. technically its a minecraft world but it
doesnt "behave" like one. I dont start it via a launcher or game … its the actual homescreen of this OS, like the
homescreen of windows." Today, between login and the world, he sees Minecraft's own startup: possibly Prism's small
"launching" dialog, Mojang's loading screen, the "joining world" screen. A mod cannot cover those (the early loading
screen draws before mods run), so the supervisor covers them.

## What to build

1. **`/usr/libexec/aresos-cover`**, a small Python program (GTK 4 through `gi`, which R27 has: Gtk 4.22; no new
   package). One borderless fullscreen window, app-id `aresos.cover`, title `AresOS`, on the output labwc gives it.
   It draws only (`linux-hub`'s look, from the Ares-Crown theme):
   - background: a vertical gradient from `#0d0d10` (top) to `#1a191e` (bottom). As written by `linux-hub`: "darker
     at the bottom". The two colours contradict that wording (`#1a191e` is the lighter one). Use `#1a191e` at the top
     and `#0d0d10` at the bottom, so it is darker at the bottom, and say so in the report;
   - the word `AresOS`, centred, Space Grotesk bold, `#f3f1ea`, height about 1/12 of the window's height;
   - one line under it, Space Grotesk regular, half that size, `#a6a39a`: `Starting your home screen…`, or
     `Starting again…` when started with `--again`;
   - nothing else: no spinner, no buttons. It takes no input and never closes on a key or a click.
   The font is package 31's `/usr/share/fonts/aresos/SpaceGrotesk-Variable.ttf`, in the image from the next release;
   if fontconfig cannot find it, use the default sans and go on (never fail for a font).
   It exits on SIGTERM, and by itself after 10 minutes, so a stuck cover can never outlive the session's need for
   it.
2. **The supervisor** (`os/config/usr/libexec/aresos-desktop`) starts the cover:
   - at session start, before Prism, for the first launch in hub mode;
   - on the owner's `retry` (with `--again`);
   - **never** for an automatic restart after a crash (package 23's B2: the new hub window must not take focus from
     an app in front; a cover on top would hide that app), and never in SETUP or AUTH_REQUIRED, where his sign-in in
     Prism must be visible.
   It stops the cover (SIGTERM, then SIGKILL after 2 s) on `world_ready`, on entering SETUP, AUTH_REQUIRED or RECOVERY
   (their foot views must be visible), when the slow-start view appears (`START_TIMEOUT`, so its message is seen),
   and when the supervisor stops. A cover that fails to start, crashes or is missing changes nothing else: the
   launch goes on exactly as today, with one log line. The cover runs in the supervisor's own scope or a scope of its
   own under `aresos.slice`, never in the game's scope, and gets the same cleaned environment as the views.
3. **labwc** (`os/config/usr/share/aresos/labwc/rc.xml`): one new window rule for `aresos.cover`: no server
   decoration, fullscreen, always on top. Do not change the existing `aresos-desktop` line (image checks grep it byte
   for byte, `os/ci/image-checks.sh` ~602, and `test_aresos_desktop.py` ~2860). Package 40 (`linux-hub`) adds a second
   `aresos-desktop` rule in the same block; whoever merges second rebases.
4. **Focus:** when the cover closes, the hub window has focus as it does today after `world_ready`. Check how
   package 23 hands focus over and keep it working with the cover in front during the start.
5. **The SETUP text** stays as it is. A hub package after 40 will make the mod create AresHub by itself; the
   SETUP message changes with that package or after it, not here.

## Tests

- Unit tests in `os/tests/test_aresos_desktop.py` (fakes, as the module does today): the cover starts at session
  start and on `retry`; not on an automatic restart, not in SETUP or AUTH_REQUIRED; it stops on each event in point 2;
  a cover that fails to start or dies leaves the launch and the state machine exactly as without it; the cover gets
  the cleaned environment; the supervisor never waits on the cover.
- The cover program alone: it parses `--again`, exits on SIGTERM, exits by itself after its limit (a short limit
  under test), and needs no input. Run it headless under the tests only if that is possible without a display; do not
  open windows on the owner's screen.
- Image checks (`os/ci/image-checks.sh`): the program is present and executable; the window rule is present; the
  existing `aresos-desktop` line is unchanged.
- The check build with VM (package 23 ran one): a screenshot during STARTING shows the cover, and one after
  `world_ready` shows the world. Say so in the report if the VM cannot show it, and why.

## Rules

- The laptop is the owner's: never run the supervisor, the cover, Prism or Minecraft on its screen, no `sudo`, no
  ostree, bootc or rpm-ostree, no disk or boot changes. Run only the `os/tests` modules you touch, one at a time;
  never `test_owner_update` locally; never a pattern-less discover. Watch runs with `--interval 60`. The integrator
  dispatches VM runs.
- The repo is public: no personal data, never `--no-verify`. Never merge, never push to main.
- A `JUDGMENT-CALL` goes in the report for the owner; a `PLAN-GAP` stops the step.

## Acceptance

Tests and hosted checks green; the check build with VM shows the cover during the start and the world after it; a
fresh review SAFE. It reaches the laptop with the next release if it is merged before the release branch is cut.
