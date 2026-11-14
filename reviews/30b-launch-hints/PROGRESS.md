# Package 30b: a hint says how a program must be started

Brief: `briefs/30b-launch-hints.md` (empire board brief 288). Built by a Claude agent (Opus 5.5) in one step,
2026-11-14, on branch `pkg/30b-launch-hints` from package 30's `0156d727` (plus the brief commit `2096b538`). This file
holds the full report text: the builder's file tool refuses `REPORT.md`.

Status: built, verified on the laptop, pushed. The hosted checks-only run is under "Hosted run" below. No pull request
(the orchestrator opens it after package 30 is merged).

## Every file touched

- `os/config/usr/libexec/aresos-shell`: `Hint` gets `gpu` and `environment`; `parse_hint` checks them; `load_hints`
  refuses a JSON key given twice; `App` gets `environment`; `apply_hints` gives both to the program the hint names;
  `ScopeLauncher.environment` adds the values.
- `os/config/usr/share/aresos/apps/hints/lunarclient.json`: `"gpu": "discrete"` and
  `"environment": {"SDL_VIDEO_DRIVER": "wayland"}` beside its window identity. `steam.json` unchanged.
- `os/ci/image-checks.sh`: the hint check expects the new Lunar hint. Nothing else there changed.
- Tests: new `os/tests/test_aresos_shell_launch_hints.py` (12 tests); `os/tests/check_aresos_shell_launch.py` (2 new
  tests, the launch code moved unchanged into a shared `LaunchBase`); one existing test changed (below).
- Nothing under `mod/` (`git diff --stat 2096b538 -- mod/` prints nothing); the examples under
  `mod/src/test/resources/shell-1.1/` are unchanged.

## Done

- **Two optional keys in a hint file.** `"gpu"` takes only `"discrete"`, the registry entry's value and check (any
  other value, `null` included, refuses the file). `"environment"` is an object of at most 8 entries; a name must match
  `HINT_ENVIRONMENT_NAME = SDL_[A-Z0-9_]{1,60}` (one pattern, one place in the helper); a value is a string of 1 to
  128 printable ASCII characters (`[ -~]{1,128}`), kept exactly as written and never expanded (the launcher already
  passes `--expand-environment=no`, and the values go into the process environment, not the command). A hint may hold
  start settings alone: it needs at least one window identity, `gpu` or a non-empty `environment`. Anything else
  refuses the whole file, window identities included, with one log line, as before.
- **Applied to the program the hint names**, only to a discovered program, as before. `apply_hints` sets
  `gpu = hint.gpu or entry's gpu` (a hint can add the NVIDIA wish, never remove it) and the hint's `environment`.
  `ScopeLauncher.environment` builds every start as before (the session's environment minus the private and GPU keys),
  then adds the program's hint values, then the three NVIDIA values when the program wants the card and the helper's
  NVIDIA check finds one. `spawn` is the only start route, so a `Terminal=true` entry (Foot wrapping the program) gets
  them too; Foot passes its environment to the program inside.
- **Nothing new on the socket.** `app_row` lists named fields only; neither `gpu` nor `environment` is among them, so
  `list_apps` (1.0 and 1.1, with app details) answers with the same rows. A 1.0 client still sees the registry alone.
  The catalogue's revision is a digest of every `App` field, so it changes when a hint's start settings change (as it
  already did for `gpu`); the rows do not.

### Hints file format (the new part)

```json
{"schema": 1, "desktop_id": "lunarclient.desktop", "app_ids": ["com.mojang.minecraft"],
 "gpu": "discrete", "environment": {"SDL_VIDEO_DRIVER": "wayland"}}
```

Besides package 30's keys: `gpu` (optional) must be `"discrete"`: start the program on the NVIDIA card where the driver
lists one, as a registry entry's `gpu` does; it adds to the desktop entry's own wish (`PrefersNonDefaultGPU`, a game
category) and never removes it. `environment` (optional) is an object of at most 8 names matching `SDL_[A-Z0-9_]{1,60}`,
each with a value of 1 to 128 printable ASCII characters, passed as written. A hint needs at least one window identity,
`gpu` or a non-empty `environment`. A key given twice anywhere in the file refuses it.

**`schema` stays 1.** Hint files ship in the same image as the helper that reads them, so a helper always knows every
key its image's hints use. A helper that does not know a key (package 30's, reading this Lunar hint) skips that file with
a log line ("unknown keys: environment, gpu"), as it does today; it would lose Lunar's window identity too, which can
only happen with a helper and hints from different images.

## Verified

On the laptop, 2026-11-14, each with `TMPDIR="$PWD/.work/30b-launch-hints/tmp"` (only the helper's modules, never the
whole `os/tests` suite):

| Command | Printed |
|---|---|
| `python3 -m unittest discover -s os/tests -p 'test_aresos_shell*.py'` | **Ran 283 tests, OK** (271 before: 12 new) |
| `python3 -m unittest discover -s os/tests -p 'check_aresos_shell_launch.py'` (real `systemd-run --user --scope`) | **Ran 4 tests, OK** (2 before: 2 new) |
| `python3 -m unittest discover -s os/tests -p 'check_aresos_shell_icons.py'` | **Ran 7 tests, OK** |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_shell_launch_hints.py' -v` | Ran 12 tests, OK |
| `bash -n os/ci/image-checks.sh` | OK |
| the image check's hint assertion (its Python block, paths pointed at the repo's helper and hint folder) | OK |
| `shell.nvidia_present()` on the laptop | `True` (the RTX 4060's driver lists a GPU) |
| `systemctl --user list-units --all 'app-aresos-org*'` after the real-route runs | no units left |

**The real start route** (`check_aresos_shell_launch.py`, `HintedLaunchRouteTest`): two stand-in desktop entries in the
test's own temporary folders, one with a hint in the test's own registry folder (`gpu` and
`SDL_VIDEO_DRIVER=wayland`), each a small Python stand-in that writes its environment to a private file and exits (no
window, no display variable passed). The session given to the launcher carries `SDL_VIDEO_DRIVER=x11` and
`DRI_PRIME=inherited`. Started through the real `systemd-run --user --scope`: the hinted stand-in got
`SDL_VIDEO_DRIVER=wayland` and, on this laptop, the three NVIDIA values (`__NV_PRIME_RENDER_OFFLOAD=1`,
`__GLX_VENDOR_LIBRARY_NAME=nvidia`, `__VK_LAYER_NV_optimus=NVIDIA_only`), and no `DRI_PRIME`; on a machine without a
card the test expects none of the three. The control stand-in without a hint got the session's `x11` and no GPU key.
Lunar Client was never started, and `~/.lunarclient` and `~/.minecraft` were never read or touched.

### Which tests fail without the change, which are controls

Each new test was run against `os/` at `2096b538` (the helper and hint file without this change; the new test module
copied in; scratch copy under `.work/`, deleted after), and against single changes made to a scratch copy of the new
helper (never in the worktree):

| Test (`test_aresos_shell_launch_hints.py` unless named) | Without the change | Also fails when |
|---|---|---|
| `HintFormatTest.test_each_accepted_form` | fails | identities required again |
| `HintFormatTest.test_each_refusal_refuses_the_whole_file_with_a_log_line` (46 cases) | **control** (the old helper refuses these as unknown keys) | the name pattern is widened (10 cases), the value check dropped (14), the 8-entry limit dropped (1), a key given twice allowed (2), any `gpu` value allowed (5), an empty `environment` counted as a setting (1) |
| `HintFormatTest.test_a_hint_with_start_settings_only` | fails | identities required again; the hint's gpu or environment not applied |
| `HintFormatTest.test_a_hint_asks_for_the_nvidia_card_and_never_takes_the_entrys_wish_away` | fails (the plain entry; the own-wish half is a control) | the hint's gpu replaces the entry's wish; the hint's gpu ignored |
| `HintFormatTest.test_lunars_shipped_hint_loads_with_both_settings` | fails | the hint's gpu or environment not applied |
| `HintFormatTest.test_a_registry_app_never_gets_a_hints_start_settings` | **control** | hints applied to registry entries through `replaces` |
| `LaunchEnvironmentTest.test_the_start_environment_with_and_without_an_nvidia_card` | fails (both subtests) | environment not applied (both), gpu ignored (with card) |
| `LaunchEnvironmentTest.test_another_program_started_next_gets_neither` | fails at Lunar's start; Discord, a terminal entry, Terminal, Notepad, Chrome are the control | the launcher writes the values into the helper's own environment (all five others fail) |
| `LaunchEnvironmentTest.test_a_terminal_entry_gets_its_hints_start_settings` | fails | environment or gpu not applied |
| `LaunchEnvironmentTest.test_the_nvidia_values_come_after_the_hints` | fails | the hint's values added after the NVIDIA values |
| `LaunchEnvironmentTest.test_nothing_new_on_the_socket` | **control** | the start settings put into the socket rows |
| `LegacyClientTest.test_a_1_0_client_is_untouched` | **control** | (pins the 1.0 path; no single change made it fail) |
| `check_aresos_shell_launch.py` `HintedLaunchRouteTest.test_the_hints_values_arrive_...` | fails (`'x11' != 'wayland'`) | |
| `check_aresos_shell_launch.py` `HintedLaunchRouteTest.test_control_a_program_without_a_hint_...` | **control** | |

Without the change: 8 of the 12 unit tests fail (4 of them as errors, since the old `Hint` and `App` lack the new
fields), the 4 controls pass. With it all 12 pass. Each of the 15 single changes listed was caught.

**Existing test changed** (all others unchanged): `test_aresos_shell_review_fixes.py`
`HintTest.test_the_image_ships_exactly_the_lunar_and_steam_hints` now expects Lunar's hint with its two start settings
(the brief changes that file).

### Hosted run

`gh workflow run "OS image" --ref pkg/30b-launch-hints -f checks_only=true` on `63a28d96`:
https://github.com/Ares-Empire/AresOS/actions/runs/43535791471 — **still running when the builder stopped.** One
blocking `gh run watch 43535791471 --exit-status`, capped at 9 minutes, ran out (exit 124) while the job "Regression
checks only (no image build or VM)" was in its step "Run regression and syntax checks" (setup and checkout passed; the
image, VM and release jobs are skipped by `checks_only`, as expected). The orchestrator records its result.

The check build (`check_build=build`, which runs `image-checks.sh` in the image) is the orchestrator's, after review.

## Not verified

- **A real Lunar Client start** from the hub: that the game then runs on the RTX 4060 in a native Wayland window under
  labwc. Only the stand-in proves the values arrive; whether Lunar's launcher passes them on to the game and Minecraft
  26.3's SDL then opens a working Wayland window is the owner's "try this" below. It rests on the OS lead's finding that
  the owner's `lunar` command, which sets these values, works.
- `image-checks.sh` inside a built image (root ownership of the hint files): only its Python assertion ran here,
  against the repo's files; the check build runs the rest.
- The hosted run's result: it was still running when the builder stopped (above). So the full `os/tests` count on
  GitHub's runner (no NVIDIA card) is not known yet; the new tests inject the card check, so they should not depend
  on it.

## JUDGMENT-CALL

- **A key given twice refuses the whole hint file.** JSON's default keeps the last value silently, so a reviewer could
  read `"SDL_VIDEO_DRIVER": "wayland"` while a second line further down decided. Applies to every key of a hint file
  (registry entries are unchanged). Rejected: the default. Undoing it is one line.
- **An empty `"environment": {}` beside a window identity is accepted** (the brief's "at most 8 entries") but counts
  as no start setting: a hint of nothing but `{}` is refused. Rejected: refusing any empty object. Either way no program
  starts with an unreviewed value.
- **Printable ASCII includes the space** (0x20 to 0x7E); tab, newline, DEL, NUL and anything outside ASCII refuse the
  file. Rejected: excluding the space (a reviewed value such as a list may need it).
- **A hint's value replaces the session's value of the same name**: with `SDL_VIDEO_DRIVER=x11` in the helper's own
  environment, Lunar still gets `wayland` (the brief's order: after the filter, before the NVIDIA values). The NVIDIA
  values would win over a hint's, but the allowlist cannot name them.
- **The start settings are part of the catalogue's revision**, as `gpu` already was: a changed hint makes the desktop
  list again and get the same rows. Rejected: leaving them out of the digest (one more special case).
- The log line keeps its wording "window hint ... is invalid: <reason>" ("as today"), although a hint now also covers
  starts.

## PLAN-GAP

- The brief points at a section "Open after this package" in `reviews/30-installed-programs/REPORT.md`; that report (at
  `2096b538`) has no such section. Its "Known limits", "Open questions" and "Review fixes 2" sections were read instead.
- `docs/design/OS-BASE.md` ("Window ownership (package 30, review fixes 1)") describes the hint format as `schema` 1,
  `desktop_id`, `app_ids` and/or `app_id_prefixes`, and is now incomplete. It is outside the brief's files, so left
  for the orchestrator. A sentence that would fit: "A hint may also say how its program starts: `gpu` (`discrete`) and
  `environment` (at most 8 `SDL_` names with printable ASCII values), applied to that program's start alone; Lunar
  Client's asks for the NVIDIA card and `SDL_VIDEO_DRIVER=wayland`."

## Known limits

- A hint names a program by its desktop file ID. If Lunar's launcher rewrites its desktop entry under another ID, the
  hint no longer applies (nothing breaks; Lunar starts as before this package).
- The values go to the program the helper starts (Lunar's launcher). They reach the game only if the launcher passes
  its environment on, as it does for the owner's `lunar` command.

## Open questions

None that block review. The judgment calls above go to the owner with the package.

## Try this (owner, after review)

1. From this worktree on your desktop: `mod/dev/run-hub.sh --helper "$PWD/os/config/usr/libexec/aresos-shell"
   --registry "$PWD/os/config/usr/share/aresos/apps"` (it reads this worktree's hint files; wait if it refuses for the
   game or memory, never force).
2. Walk into Lunar Client's logo (or click it in My apps) and start the game. It should open as it does from your
   `lunar` command; in the game, F3 should name the GeForce RTX 4060 on the right.
3. Open Discord or Chrome from the hub as well: they should start exactly as before.

## Housekeeping

No Gradle, no game client, no window. The real-route scopes ended with their stand-ins (none left). `.work/` holds only
the empty `30b-launch-hints/tmp` folder; `find .work -size +500M` prints nothing. **Files left in `.work/` over 500 MB:
none.**

## Commits

- `1cde6995` 30b: a hint can say how a program must be started (gpu, SDL environment)
- `63a28d96` 30b: tests run alone against the old helper; the real route carries the hint
- `ec9cd047` 30b: report text in PROGRESS.md (hosted run pending)
- this file's update with the hosted run's state
