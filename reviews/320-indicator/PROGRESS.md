# 320: progress

Brief: `briefs/320-indicator.md`. Branch `pkg/320-indicator` from main at `6a19b642`. Draft PR into main.

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

## Left, in order

1. **Step 2, the program and the image:** `aresos-indicator`, Jersey 10 with its licence and README line, the pack and
   its generator, their unit tests and image checks (including `aresos-indicator` root-owned 755 beside the two step 1
   checks), and `aresos-level` in the startup-commands file list (`os/ci/image-checks.sh`, about line 419). Then the
   PR's check build (`os-image.yml`, `check_build=build`).
2. **Step 3:** the harness and tests 1 to 9, fixes, and the report in this file's last section.
3. **A hosted `checks_only` run** to show the sandbox tests run (not skip) on CI's runner (see "What the code doesn't
   show", 8). Not dispatched in step 1.
4. After the three steps and the image package on main: rebase, `check_build=build` green with the layer library, the
   `linux-aresos` OK on the list below, then merge.

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
   Gio is missing, so a hosted run proves they ran. That run has not been dispatched yet.
9. **What step 1 cannot show:** the plate itself, the older-`Show` drop, the layer checks and everything on screen are
   steps 2 and 3. Whether labwc's repeat delivers 25 presses a second through `aresos-level` without piling up is step
   3's harness test 4 (the unit test holds a key at 25 a second for 12 presses and sees one program and the last level).

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
- **Still to come in step 2:** `aresos-level` joins the startup-commands file list (about line 419), so every
  absolute path it names must exist in the image, `/usr/libexec/aresos-indicator` included.

## The public and private check

- Step 1, before the first push (`c8f195da`, `9e8a7d9b` and this file's commit): checked 11 staged files against the
  list: no match. Every file in the push is text written in this step; no binary is staged.
