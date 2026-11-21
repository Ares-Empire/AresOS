# 320: progress

Brief: `briefs/320-indicator.md`. Branch `pkg/320-indicator` from main at `6a19b642`. Draft PR #131 into main.

## Done

### Step 1: the keys and the settings (a fresh Claude Opus builder, 2026-11-21)

- `c8f195da`: `os/config/usr/libexec/aresos-level` (bash) and `os/config/usr/libexec/aresos-settings` (Python), both
  git mode 755; their unit tests `os/tests/test_aresos_level.py` (25 tests) and `os/tests/test_aresos_settings.py`
  (20 tests) with the shared sandbox `os/tests/level_sandbox.py`; the one COMPONENTS.md 4.7 line (`settings.json`).
- `9e8a7d9b`: the six `rc.xml` key lines, their image check and `test_everyday_account.py`, in one commit.

Tests run on the laptop (all OK):

- `python3 -B -m unittest discover -s os/tests -p 'test_aresos_level.py'`: 25 tests OK (about 30 s; the two cold-launch
  tests with a program that never takes its name wait out the 5 s deadline).
- `python3 -B -m unittest discover -s os/tests -p 'test_aresos_settings.py'`: 20 tests OK.
- `python3 -B -m unittest discover -s os/tests -p 'test_everyday_account.py'`: 34 tests OK.
- `python3 -B -m unittest discover -s os/tests -p 'test_shell_assertions.py'`: 9 tests OK.
- `python3 -B -m unittest discover -s os/tests -p 'test_release28.py' -k MainSmokeTest`: 13 tests OK (the release
  diff's view of new `os/config` files and the changed `rc.xml`).
- `bash -n` on `os/config/usr/libexec/aresos-level` and `os/ci/image-checks.sh`: OK.
- Mutation checks (not committed): keeping the change lock open into the background fails the "second key while the
  first read-back hangs" and "inherits neither lock" tests; releasing the launch lock before the program owns its name
  fails three cold-launch tests.

Not run: the image check itself (it runs in the image build, step 2's `check_build=build`), the full `os/tests` suite
(the hosted `checks_only` run gives the count; see "Left").

The public and private check before the first push: see the last section.

### Step 2 (the program and the image)

- `aresos-indicator` serves `aresos.Indicator.Show(tss)` through GApplication and uses the cold-launch arguments from
  `aresos-level`. It drops older requests, rereads the settings and pack for each showing, and creates a fresh passive
  overlay with an empty input region before mapping. It draws Look A at 2x, 3x or 4x with Cairo and Pango, and
  exits after 60 s idle. The plate hides after 1.5 s and the last step flashes for 150 ms on an up request at 100 %.
- `os/look/make_pack.py` generates the 17 sprites and `look.json` from the public component study. Jersey 10 and
  its SIL Open Font License 1.1 came unchanged from google/fonts commit
  [`6e4b84c976cadb3c49a40fd9a1c203e4f7fcf2da`](https://github.com/google/fonts/tree/6e4b84c976cadb3c49a40fd9a1c203e4f7fcf2da/ofl/jersey10).
  The font is 77,732 bytes and its SHA-256 is `db9cbd091617048a145d249daa2b815fe7083be6ab66ac26626e21a4e01c3e82`.
  README credits the font.
- The image checks cover the three programs' ownership and modes, the indicator's GTK 4 layer loader as the everyday
  account, Jersey 10 and its licence, fontconfig, the pack's file names and combined SHA-256, and the commands
  called by `aresos-level` through the startup-commands scan.

Local verification ran each unittest module separately using
`python3 -m unittest discover -s os/tests -p '<module>'` with `PYTHONPYCACHEPREFIX` under the worktree's `.work/`.
`test_everyday_account.py`'s existing subids loader created a cache under `os/config` on the first run. Its file
was removed and the rerun confirmed there was no `__pycache__` under `os/config`.

| Module | Result |
|---|---|
| `test_aresos_indicator.py` | 23 tests, OK. Offscreen checks compared all plate and bar sprite pixels at 2x, 3x and 4x for the 100 % and flash states, plus six Jersey 10 glyphs at each scale and a Cyrillic fallback. |
| `test_aresos_look_pack.py` | 1 test, OK. All 17 sprites and the manifest regenerated. |
| `test_aresos_level.py` | 25 tests, OK. |
| `test_aresos_settings.py` | 20 tests, OK. |
| `test_everyday_account.py` | 34 tests, OK. |
| `test_shell_assertions.py` | 9 tests, OK. |

- `bash -n os/ci/image-checks.sh` and the staged diff's whitespace check excluding the upstream OFL exited 0.
  The verbatim upstream licence has a trailing space on line 21. The image asset check passed with its share
  path pointed at the checkout, and `fc-match` with a scratch Fontconfig file found the bundled
  `Jersey10-Regular.ttf`.
- The display-free loader check used Fedora's `gtk4-layer-shell-1.3.0-1.fc44.x86_64.rpm` extracted under `.work/`
  after `rpm -K` printed `digests signatures OK`. The loader printed
  `INDICATOR_GTK 4 22 cairo 1.28.0 gtk4-layer-shell 1 3 0`.
- A private `dbus-run-session` smoke check with a stand-in GUI and real Gio showed `Show` returning `()`, a second
  instance yielding to the primary, and `NameHasOwner` returning `(false,)` after the shortened idle deadline.
- No file over 500 MB remained under `.work/`.
- Hosted check build (`gh workflow run os-image.yml --ref pkg/320-indicator -f check_build=build`) dispatched once
  for `25533a6e`. Run [44895737105](https://github.com/Ares-Empire/AresOS/actions/runs/44895737105) was handed
  over without waiting for a result. The image loader gate requires R29's layer library.

## Left, in order

1. **Hosted evidence.** The lead checks step 1's `checks_only` run 44886308040 for the sandbox tests and reviews the
   step 2 check build. The layer-loader gate is expected to fail until R29 supplies gtk4-layer-shell.
2. Once R29 lands, rebase onto main and get a green `check_build=build` with the layer library. The lead
   gets the `linux-aresos` OK before merge, then arranges the release and the real laptop checks with the owner.

## What the code doesn't show

1. **The contract with step 2's program.** `aresos-level` calls `aresos.Indicator.Show(t sequence, s action,
   s reading)` on `aresos.indicator` at `/aresos/indicator`, and a cold launch runs
   `/usr/libexec/aresos-indicator <sequence> <action> <reading>`. The action words are the script's own:
   `brightness-up`, `brightness-down`, `volume-up`, `volume-down`, `mute`, `mic-mute`, and `show-volume` (the seventh,
   which changes nothing; `aresos-settings set indicator-place|indicator-size` sends it). The reading is a whole
   percentage (`62`, `150` above 100 %), `<percentage> muted` for a muted output, `on` or `off` for the microphone, or
   `none` when there is no backlight, no sound output or no microphone. "Laptop screen / is off" is the program's to
   decide (a backlight exists, so the reading is a number, but no `eDP` output is active). The program must drop a
   `Show` whose sequence is lower than the last one shown, take its first request from its arguments, own the name, and
   drop `LD_PRELOAD` from its environment first (`take_token()` in `aresos-laptop-home`). It must re-read the settings
   on `show-volume` even while visible (COMPONENTS.md 4.7, "when told by set").
2. **brightnessctl 0.5.1 takes `--min-value` in raw units only.** Read from its source at tag 0.5.1
   (`brightnessctl.c`: `p.min = atol(optarg)`), not by running the image's binary (the real tool never runs here). So
   the script computes the floor: `max` first, then `--min-value=<ceil(max / 100)>` (at least 1). `--class=backlight`
   is accepted by 0.5.1 (`-c, --class`) and fails with "Failed to read any devices of class 'backlight'." when there is
   none, so an LED is never selected. Brightness up keeps one command (`set 5%+`); only brightness down reads the
   maximum first.
3. **wpctl's formats** (WirePlumber 0.5's `wpctl.c`): `get-volume` prints `Volume: %.2f` with ` [MUTED]`, and with no
   default node prints a "Translate ID error" on stderr and still exits 0, so the script parses stdout. The stand-ins
   copy these formats and brightnessctl's `-m info` line (`id,class,current,percent%,max`).
4. **gdbus on an unowned name** prints `GDBus.Error:org.freedesktop.DBus.Error.ServiceUnknown` (checked on a private
   bus); only that error leads to the launch lock. A `timeout` (exit 124) or any other error never starts a program.
5. **Choices inside the brief's limits:**
   - Every notifier waits for the launch lock with `flock -w 6`. The brief's Decision 1 first says `flock -w 3`, then
     "Waiting notifiers use `flock -w 6`" after the recheck's fix (the lock is held up to 5 s); `-w 6` is the one that
     lets a waiter outlast a slow start, and a shorter wait would only drop that waiter's update.
   - Each device command runs under `timeout 3`, so a hung `wpctl` cannot hold the change lock for ever (later keys
     wait 1 s at most in any case). The commands themselves are unchanged.
   - `LD_PRELOAD` is set only when `/usr/lib64/libgtk4-layer-shell.so.0` exists, so main's image (without the image
     package) gets no loader warning per launch; the program then finds no layer library and exits (Decision 5).
   - The program starts under `setsid` with stdin and stdout on `/dev/null` and stderr inherited: under labwc that is
     the session's journal.
   - No `XDG_RUNTIME_DIR` means the change runs without the lock and without a plate (one log line); no
     `DBUS_SESSION_BUS_ADDRESS` means no plate, and gdbus never gets to autolaunch a bus.
   - `aresos-settings` treats a file whose `version` is not the integer 1, or that is not a JSON object, as broken;
     unknown names and bad values fall back one by one, with one journal line per run for all problems.
6. **`build.sh`'s `chmod 0755` line is unchanged.** `test_release28.py` pins that line to release 28's set
   (`release_diff.CHMOD_0755_28`). The two programs keep git's mode 755 through the Containerfile's `cp -a`, as
   `aresos-laptop-home` does, and the image check asserts `root:root 755`.
7. **The unit tests use `unshare`, not bwrap.** GitHub's Ubuntu runner may lack bubblewrap
   (`test_aresos_shell_hardening.py` says so), while `os-image.yml` turns AppArmor's user-namespace switch off before
   the suite. Each run is a private user, mount and PID namespace: an overlay on `/usr/bin` with the stand-in
   `brightnessctl` and `wpctl`, a tmpfs on `/usr/libexec` with the branch's programs and a stand-in indicator, tmpfs
   over `/run` and `/sys/class`, a scratch `HOME` and `XDG_RUNTIME_DIR`, and its own `dbus-run-session`. The setup
   refuses to go on unless both device tools are the stand-ins, and every leftover process ends with the namespace.
   The stand-in indicator serves the bus with PyGObject's Gio.
8. **Not yet seen on CI.** Under `GITHUB_ACTIONS=true` the sandbox tests fail instead of skipping when the namespace or
   Gio is missing, so a hosted run proves they ran: run 44886308040, still queued when step 1 ended.
   `test_aresos_settings.OwnershipTest` fails if any other file in `os/config` names `settings.json`, comments
   included: step 2's indicator reads the settings through `aresos-settings` only.
9. **The PipeWire label lookup.** The indicator runs the base image's `/usr/bin/pw-dump -N` read-only with a 300 ms
   deadline. WirePlumber's default metadata names the sink. The indicator matches its `device.id` and
   `card.profile.device` to the active output `Route` to distinguish speakers from headphones on the same sink.
   Bluetooth takes the device name from BlueZ properties and uses Pango's plain-text ellipsis. The harness can put
   a `pw-dump` stand-in at that path for named-output cases, or use `Volume` when it supplies no graph.
   [WirePlumber's default metadata](https://github.com/PipeWire/wireplumber/blob/0.5.12/src/scripts/default-nodes/apply-default-node.lua)
   [PipeWire's ALSA routes](https://github.com/PipeWire/pipewire/blob/1.6.9/spa/plugins/alsa/alsa-acp-device.c)
   [PipeWire's JSON tool](https://github.com/PipeWire/pipewire/blob/1.6.9/src/tools/pw-dump.c)
10. **Step 3's entry points.** Set `ARESOS_INDICATOR_TEST_EDP` to a named headless output,
    `ARESOS_INDICATOR_TEST_IDLE_MS` to an idle interval in milliseconds, and
    `ARESOS_INDICATOR_TEST_START_DELAY_MS` to a delay before taking the bus name. A successful first surface
    request logs `aresos-indicator: started`, a colliding launch logs `started while another indicator owns the name`,
    and the delay override logs `waiting before taking the bus name (test)`. Layer shell protocol v1 has the requests
    the indicator uses. [gtk4-layer-shell's protocol](https://github.com/wmww/gtk4-layer-shell/blob/v1.3.0/protocol/wlr-layer-shell-unstable-v1.xml)
11. **The laptop remains unverified.** The headless compositor results are in the last section. The owner and
    lead check the actual game GUI scale, bottom clearance, real output names, brightness on the real eDP, and how
    holding the keys feels. The offscreen painter skips where Pango 1.56, PyGObject, pycairo or Pillow is missing.

## For linux-aresos

The lead sends this list to `linux-aresos` before merge.

- **`os/config/usr/share/aresos/labwc/rc.xml`, the six key lines** (commit `9e8a7d9b`). Nothing else in `rc.xml`
  changes (`<theme>`, Ares-Crown and the comment above the keys stay):
  ```xml
  <keybind key="XF86MonBrightnessUp"><action name="Execute" command="/usr/libexec/aresos-level brightness-up" /></keybind>
  <keybind key="XF86MonBrightnessDown"><action name="Execute" command="/usr/libexec/aresos-level brightness-down" /></keybind>
  <keybind key="XF86AudioRaiseVolume"><action name="Execute" command="/usr/libexec/aresos-level volume-up" /></keybind>
  <keybind key="XF86AudioLowerVolume"><action name="Execute" command="/usr/libexec/aresos-level volume-down" /></keybind>
  <keybind key="XF86AudioMute"><action name="Execute" command="/usr/libexec/aresos-level mute" /></keybind>
  <keybind key="XF86AudioMicMute"><action name="Execute" command="/usr/libexec/aresos-level mic-mute" /></keybind>
  ```
- **`os/ci/image-checks.sh`, the six-keys block** (commit `9e8a7d9b`): asserts each binding equals
  `/usr/libexec/aresos-level <action>` exactly (was: the first word executable), keeps the keysym and recovery-terminal
  checks, asserts `/usr/libexec/aresos-level` and `/usr/libexec/aresos-settings` are `root:root 755`, runs `bash -n` on
  `aresos-level`, checks `aresos-settings get` as ares with no settings file prints
  `{"indicator-place": "top", "indicator-size": "medium", "look": "B"}`, and adds `gdbus`, `flock`, `timeout` and
  `setsid` to the `command -v` loop. The pass line now reads "brightness, volume, mute and mic-mute keys run
  aresos-level (package 320); aresos-settings gives the defaults (…); recovery terminal kept".
- **`os/tests/test_everyday_account.py`** (commit `9e8a7d9b`):
  `test_brightness_volume_and_mic_keys_use_tools_in_the_image` asserts the six new bindings and that `aresos-level` is
  executable in `os/config`.
- **`os/tests/test_aresos_level.py`** (commit `c8f195da`): the former six command strings now live in its `COMMANDS`,
  as the script's commands, with brightness changed by Decision 7 (`--class=backlight`, and brightness down's
  `max` read and raw `--min-value` floor) and volume up's added `set-mute @DEFAULT_AUDIO_SINK@ 0`.
- **`os/ci/image-checks.sh`, step 2** (commit `6dac8928`). The startup-commands scan now reads `aresos-level`
  and requires finding `/usr/libexec/aresos-indicator`. The ownership loop adds `aresos-indicator` to the
  two earlier programs. The new block requires executable `/usr/bin/pw-dump`, checks Jersey 10's exact byte count
  and SHA-256, checks the OFL copyright and version text, and checks that `fc-match 'Jersey 10'` resolves the
  installed TTF as the everyday account. It checks the pack's exact file list and SHA-256
  `386d46534f4c38d5b0d53688628095e47a707bb60be2f902e0b861b447617ede`. It requires the
  `libgtk4-layer-shell.so.0` file and preloads it for the indicator's GTK 4/Pango/Cairo loader as the everyday
  account. The loader check requires GTK 4, a layer library major version of at least 1 and the Cairo-only
  environment. R29 must supply the layer library. The release VM pass should include `fc-match 'Jersey 10'`
  in the booted guest.

## The public and private check

- Step 1, before the first push (`c8f195da`, `9e8a7d9b` and this file's commit): checked 11 staged files against the
  list: no match. Every file in the push is text written in this step; no binary is staged.
- Step 2, before its first push, compared 28 staged files by SHA-256. No matches. The 17 PNGs are generated from the
  public Look A study and the TTF matches the pinned Google Fonts download. The check read the digest field only
  and kept its comparison in memory. The first push attempt hit the Git email privacy hook. The three local commits
  were re-authored with a GitHub noreply address and all 28 file versions were checked again before retrying.
- Step 2, before pushing the run ID, compared the one staged file (`PROGRESS.md`) by SHA-256. No match.
- Step 3, before pushing, compared all nine staged harness source files and all 77 staged report and evidence files
  by SHA-256. Zero matches. The nine incoming file versions from the `origin/main` merge were also checked, with
  zero matches. Every staged binary is a `grim` capture from the private headless test, with only the fullscreen
  colour stand-in, empty headless output and public Look A assets. The comparison used the digest field in memory.

## Step 3 report

**Done.** Commit `35fd330c` adds the rootless harness under `os/tests/indicator-harness/` and extends
package 316's `wl-harness window` with the optional persistent pointer lock and relative-motion listener from
package 311. The original window invocation still builds with package 316's own Containerfile and client
compiler flags. The new image uses the labwc RPM from `localhost/aresos-labwc:311e` and Fedora 44's
`gtk4-layer-shell-1.3.0-1.fc44.x86_64`. The driver and each private labwc inherited one `dbus-run-session`
address. labwc used the branch's `rc.xml` and the tools at their image paths. The devices and PipeWire graph
were fixtures written to a scratch home inside the container.

### Verified

- `free -g` showed 7 GiB available before the first build. One container ran at a time.
- `os/tests/indicator-harness/run.sh image` built both package 316 clients with `-Wall -Werror`; the labwc
  executable and labnag matched their loaded SHA-256 pins. The labwc RPM was
  `labwc-0.9.6-1.fc44.aresos1.x86_64`, SHA-256
  `8f9f4ea2ab3163ee2a760624cd10d7ceb105a3c84f1d980ed73cbea7aba565c6`.
- `os/tests/indicator-harness/run.sh run .work/320/trial6` exited 0 with 25 isolation checks and 51 checks
  across the nine tests. The driver also verified the private bus socket and each labwc and client environment.
  `os/tests/indicator-harness/run.sh run .work/320/confirmation` exited 0 with the same counts. It measured
  24.4 actions/s with a 608 ms first interval and the plate disappeared 1.552 s after release. Cold latency was
  at most 290 ms for the pair and 293 ms for the hold.
  [Results](evidence/results.txt), [confirmation](evidence/confirmation-results.txt) and [package versions](evidence/versions.txt).
- Ran `python3 -m unittest discover -s os/tests -p '<module>' -v` separately for the three requested modules,
  without `-B`, against the tracked configuration in disposable rootless containers.
  `test_aresos_indicator.py` ran 23, OK. `test_aresos_settings.py` ran 20, OK.
  `test_aresos_level.py` ran 25 in the GTK image, with the no-layer case skipped because the library was installed.
  The full level module then ran separately in the base client image without the library, with all 25 passing. The nested
  namespace tests needed the unit containers' `seccomp=unconfined`, `unmask=/proc/*` and `label=disable` options
  for their private proc and mounts. Both unit containers kept isolated PID and network namespaces and had no
  devices or host directories passed in. The compositor harness used the regular container settings.
  [Unit output](evidence/units-with-layer.txt) and [output without the layer library](evidence/units-level-no-layer.txt).
- `bash -n` passed for the harness shell scripts and the staged diff passed `git diff --cached --check`.

| Test | Result |
|---|---|
| 1. Pointer lock | 4/4. The locked fullscreen stand-in received nine relative deltas totalling (90, 45), nine key presses and nine releases. Zero unlocks, absolute motions or input-focus leaves while the 65% and 70% plates appeared, then disappeared. [Capture](evidence/01-pointer-lock-update.png) |
| 2. Pass-through and stacking | 2/2. After releasing the lock, the fullscreen stand-in received the click at (500, 69) through the visible plate. [Capture](evidence/02-above-fullscreen.png) |
| 3. Failure paths | 7/7. All 24 key actions changed the fixtures with the indicator removed, nonexecutable, crashing or missing the layer library. The real library reported no layer protocol under private Xwayland. The indicator logged once and exited 1. Zero new toplevels or keyboard leaves. [Xwayland log](evidence/03-xwayland-indicator.log) |
| 4. Held key | 5/5. Thirteen volume-down actions took the fixture from 100% to 35%. After a 604 ms first interval, observed cadence was 24.1 changes/s. The bar followed the hold and finished at 35%. One process and start line, all key scripts and notifiers drained, plate gone 1.575 s after release. [Final frame](evidence/04-final-repeat-level.png) |
| 5. Unavailable devices | 6/6. All four messages and their grey icons matched. The LED stayed unchanged. Disabling the laptop output, with its backlight still present, showed “Laptop screen / is off” while the backlight changed. [Screen-off capture](evidence/05-screen-off.png) |
| 6. Placement | 5/5. Volume and microphone followed the pointer on both headless outputs. Brightness used named `HEADLESS-2` with the pointer on `HEADLESS-1`. [Brightness capture](evidence/06-brightness-edp.png) |
| 7. Settings | 7/7. Defaults were 525 × 90 px, top-centred with a 24 px margin. Both bottom sizes matched, broken JSON restored defaults and logged once, both settings commands previewed the current volume once, and A, B and C produced identical pixels. [Large bottom preview](evidence/07-preview-indicator-size.png) |
| 8. Pixels | 9/9. Both 62% route labels matched the study at 2x, 3x and 4x, including the bar's partial step and every opaque sprite pixel outside the text overlay. Jersey 10 needed zero glyph shifts. The fallback glyph's 294, 675 and 1,219 foreground pixels used the pack's ink colour. [4x route capture](evidence/08-4x-headphones.png) |
| 9. Launch and order | 6/6. One start line and one process for both the cold pair and the cold hold. The first frame was seen within 279 ms and 292 ms of the first press respectively. The newer 65% survived a later stale 25% call. Two delayed attempts ended at the 5 s deadline, the first PID was reaped before the lock passed, and the device changes happened before the wait. The shortened idle interval ended the program and the next key brought it back. [Deadline log](evidence/09-labwc.log) |

### The four open checks in COMPONENTS.md section 8

1. **Unnamed layer placement.** With this patched labwc, the unnamed volume and microphone layers landed on
   the pointer's output on both sides, even with the fullscreen stand-in on the other output. The named
   brightness layer appeared on the simulated laptop output.
2. **Empty input region and pointer lock.** The overlay left the persistent constraint, pointer focus and keyboard
   focus in place across appearance, update and disappearance. The probe still received input during each phase.
3. **Held-key repeat.** labwc repeated the virtual keyboard's key itself. The roughly 600 ms delay and roughly 25
   actions/s followed its normal repeat configuration. The result required no injected repeat presses.
4. **Session bus and launch.** The checked-in session wrapper provides the bus. Under the same
   `dbus-run-session` arrangement headlessly, the key changed its level, started the program on an unowned name,
   and subsequent notifications reached that name over the same bus. The program started from the key, without
   bus activation.

### Fixes and limits

- The first two runs stopped at the mount gate until it accounted for Podman's standard pseudo-devices and
  verified the container secrets mount was empty. The first runtime image lacked Cairo's typelib. Adding
  `gobject-introspection` supplied it. The later trials corrected the sound fixture's `media.class`, waited for
  the new probe's own announcement after restarting labwc, and included the fallback font's ascent in the colour
  comparison. The nine tests passed using the same checked-in level, settings and indicator programs as step 2.
- [Known limits](KNOWN-LIMITS.md) records the fallback glyph near the top border and the PyGObject bus registration
  deprecation warning with their reasons.
- The headless captures establish no physical-panel brightness, real hardware audio labels, game GUI scale, hotbar
  or hearts clearance, or feel of holding the keys. Those remain the lead's checks with the owner. R29 still gates
  the image library check. No workflow was dispatched in this step. No file over 500 MB remained under `.work/`.
- **Open questions.** No placement decision arose. The lead still coordinates R29, the image check and the real laptop pass.

## REVIEW-1 fixes

1. `2d09774c` exports `aresos.Indicator.Show` in `do_dbus_register` before the name is acquired. The new
   `test_show_is_callable_before_the_startup_handler` sent a second request on a private bus during real
   GApplication startup. It passed with the fix and returned `UnknownMethod` with the pre-fix indicator.
2. `41445100` uses monotonic uptime for the five-second ownership deadline, caps each probe to the time left,
   and ends and waits for a late child under the launch lock. The level module's timeout and serialized retry
   tests passed, as did harness test 9.
3. `2d09774c` logs each indicator process at entry. Harness test 9 counted one entry for the cold pair and one
   for the cold hold. For the delayed launch, a sole blocking waiter acquired the launch lock after 5.176 s
   and found the child already reaped. The harness checks for handoff between 5.0 and 5.5 s after the key press.
4. `11eea916` makes the `wpctl` fixture publish the first blocked read's PID. The level test waits for that
   read to sleep and verifies the second key changed the volume while the same read was still pending.

The timed-out read is recorded in [KNOWN-LIMITS.md](KNOWN-LIMITS.md). The lead's real laptop checks with the
owner are still pending.

- `python3 -m unittest discover -s os/tests -p '<module>' -v`, run separately without `-B` in disposable
  rootless containers, reported 24 indicator, 25 level and 20 settings tests, all OK. The level module used the
  clients image without the layer library so all 25 ran. No `__pycache__` directories were left under `os/config`.
- `os/tests/indicator-harness/run.sh run .work/320/review-1/harness` and the repeat run with `confirmation` as
  the evidence folder both exited 0 with 25 isolation checks and 51 checks across nine tests. The private D-Bus
  check passed both times. The confirmation measured lock handoff at 5.175 s. Both runs reused the existing
  rootless test image, one container at a time.
- `bash -n os/config/usr/libexec/aresos-level` and `git diff --cached --check` passed. No file over 500 MB remained
  under `.work/`.
- Before pushing, every staged file version in the four commits was compared by SHA-256 against the private
  digest list. Eight text files were compared, with zero matches.
