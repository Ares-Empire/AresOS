Reviewed PR #70 at `38815762` (23b).

Reviewer: a fresh Claude agent on Opus 5.5, read-only; committed by the integrator from its final message (abridged only where it repeats the PR's own description; every finding is kept as written).

**Verdict: CHANGES-NEEDED.** Nothing blocks, and the core change is sound: the state machine, the failure handling and the "never waits" rule are right. Three should-fixes need a short step first. Each is a few lines.

## Findings

### 1. should-fix: the cover draws in Noto Sans, not Space Grotesk, in the real image, but the image check reports it as Space Grotesk
- **Where:** `os/ci/image-checks.sh:623-625` (the `fc-match` check and its PASS line). The root cause is in `os/build.sh` (`configure`, near line 231): no `fc-cache` runs after `config/` is copied.
- **What I saw:** I downloaded run 43673448694's `aresos-cover.png` and rendered "AresOS / Starting your home screen…" next to it with the repo's `SpaceGrotesk-Variable.ttf` and with Noto Sans Bold/Regular. The VM picture matches Noto Sans glyph for glyph (y, g, t and S differ clearly from Space Grotesk). labwc's title bar in `aresos-cover-stopped.png` also looks like Noto Sans, so package 31's titles are probably hit too. Yet `checks.txt` prints "PASS … draws in Space Grotesk".
- **Why:** this is the "tests pass, the screen is wrong" case.
  - On an ostree deployment `/usr/share/fonts` has mtime 0 (checked read-only on this laptop).
  - fontconfig 2.17 treats a cache for a directory with mtime 0 as valid. I reproduced this in a scratch fontconfig: a cache built at mtime 1600000000, a font subdirectory added, the directory set to mtime 0, and `fc-match` still returned the old font. With a newer non-zero mtime the new font was found.
  - So the base image's system cache for `/usr/share/fonts`, built before `aresos/` existed, hides the font at runtime.
  - The image check runs in the build container, where mtimes are real, so the cache is rebuilt there and the font is found.
- **Fix:**
  - In `build.sh configure`, after the config copy, run `fc-cache --system-only --really-force`.
  - Move or add the font check to the VM: in `checks.py`'s `cover` step (`cover_start`, line 364), run `fc-match -f '%{file}' 'Space Grotesk:bold'` as ares and require the aresos file.
  - Until a VM run proves it, make the PASS text say "fontconfig finds" rather than "draws in".
  - `/usr/lib/fontconfig/cache` will change in the image, so the release diff may need a rule for it, as package 31 needed one for `gschemas.compiled`.
  - Tell package 31's owner (the OS lead) about the title-bar font.

### 2. should-fix: a retry from AUTH_REQUIRED hides Prism's sign-in for 25 s
- **Where:** `aresos-desktop:1848` (`retry()` → `self.begin(cover=COVER_AGAIN)`).
- **Why:** the brief says never cover AUTH_REQUIRED, "where his sign-in in Prism must be visible". AUTH_REQUIRED's own text says "Usually it needs you to sign in again (Prism shows its own sign-in) … Type retry. Prism opens again". The retry from that view is exactly the sign-in moment. As built he sees "Starting again…" for 25 s while the sign-in dialog waits underneath with the keyboard focus. This repeats on every retry in a sign-in loop.
- **Fix:** don't cover a retry that leaves AUTH_REQUIRED (`self.state` is still AUTH_REQUIRED at that line). Add a CoverTest for it.

### 3. should-fix: JUDGMENT-CALL 2's side effect is probably wrong; the restarted hub may open behind Minecraft's pause menu
- **Where:** `aresos-desktop:1360-1362` (`ARESOS_SHELL_KEEP_FOREGROUND` for every automatic launch) and PROGRESS JUDGMENT-CALL 2.
- **Why:** a crash under the cover, then the automatic restart. When the crashed game window closes, labwc focuses the topmost window, which is the cover. The restarted helper has `keep_foreground` set: when the new hub window takes the focus, it gives the focus back to the window that had it before, the cover (`aresos-shell` ~3451). Minecraft enters the world without the focus; vanilla's lost-focus pause (`pauseIfInactive`) opens the pause menu, and main's mod closes only pause menus its own launches caused. So when the cover closes he sees the hub behind a pause menu. Nothing of his can be in front under the cover (the recovery terminal already removes it), so B2's reason for `keep_foreground` does not apply here.
- **Fix:** (a) `if launch.automatic and not self.cover:` in `ensure_helper`, plus a test that a restart under the cover gets no `KEEP_FOREGROUND`; or (b) stop the cover in `schedule_restart`. Either way, correct JUDGMENT-CALL 2's text. Confidence is moderate: it rests on labwc's focus order after a window closes, which no test here exercises.

### 4. nit: JUDGMENT-CALLs missing for the owner
- (a) A retry from any terminal, including Claude's terminal on the laptop, covers every open window until the hub is ready. Keys typed meanwhile go to hidden windows: in the first 25 s an Enter can answer a hidden Prism dialog.
- (b) Minecraft's own prompts during world load (backup / newer-version / experimental-settings screens, for example after a pinned version bump) stay hidden until START_TIMEOUT, 120 s; then the slow-start view appears over them. PROGRESS "What the code doesn't show" should say this.
- (c) The font (finding 1), if it is not fixed before the release.
- (d) The 25 s Prism wait itself, as the outcome of PLAN-GAP 1.

### 5. nit: merge order with 22d and 40
- **22d:** `os-image.yml`, `rehearsal-packages.json` and `test_ways_back_model.py` are byte-identical to 22d's head `3c09cf3a`. Whoever merges second only merges `pending-rebind.json`: drop the duplicate rows (same sha). If 22d's VM rehearsal rebinds first, drop the 23b rows whose files then equal their walk bytes, and re-record `vm.py` if 22d changed it.
- **Package 40:** its `Windows.covering()` drives both `uncover()` and `shell_covered`. It must exclude app-id `aresos.cover` in `covering()` itself. Whichever merges second should carry a test that `aresos.cover` is never counted as covering.

### 6. info (package 23, not 23b): the supervisor reacts to SIGTERM late
The loop has no signal wakeup (no `set_wakeup_fd`, and PEP 475 retries `select`). A SIGTERM is noticed only at the loop's next deadline, up to 30 s, so "the cover ends when the supervisor stops" is that late. At logout the cover dies with labwc's display anyway. PDEATHSIG covers a crashed supervisor.

## Answers (short)

- **Q1, when it appears and stops:** correct as specified apart from finding 2 (appears only through `start_launch` with `cover=` in hub mode, not automatic; never for a restart, setup, an adopted game, a latch, a restarted supervisor or `new_session()`; stops on every non-STARTING state before its view opens, after 25 s without `jvm_start`, on `hide_cover`, on `Loop.close`, by its own 600 s limit; SIGTERM then SIGKILL at +2 s).
- **Q2, hiding or blocking:** message views never; Prism dialogs at most 25 s (finding 2 aside); the recovery terminal only until `hide-cover` runs; an app after a crash never. The supervisor never waits on it except at shutdown (≤ 2 s). Focus after it closes: finding 3.
- **Q3, failure isolation:** yes, each failure is one log line; it runs with `session_environment()` as a plain child in the supervisor's cgroup, never in the game's scope; its fds are closed, so it cannot carry the desktop lock.
- **Q4, the flaky test:** the explanation is right (the wrapper releases its flock only at exit, after the supervisor's reply; a scripted retry within milliseconds correctly gets `RECOVERY locked`). The fix mirrors a human's delay. 15/15 passed here.
- **Q5, labwc:** `ToggleFullscreen` and `ToggleAlwaysOnTop` are valid 0.9.6 rule actions; two Execute actions in one keybind run in order (the VM log shows the second ran). The `aresos-desktop` line is byte-identical.
- **Q6, image and VM checks:** proven: the cover runs as ares in the real labwc session, borderless, fullscreen, above the SETUP view; SIGTERM ends it in 0.061 s; the keybind reaches the supervisor. Not proven: the font (disproved, finding 1), a supervisor-started cover in the image, stacking over a real Minecraft, focus hand-over, the `--again` text.
- **Q7, the time-limit commit:** consistent (pending rows equal checkout bytes; `job_bounds.checks` 40; byte-identical to 22d; run 43678242876 was cancelled at 25 min 14 s).

## What I ran (no display: `WAYLAND_DISPLAY`/`DISPLAY` unset)
- `test_aresos_desktop.py`: 180 OK (skipped=1). `test_aresos_cover.py`: 9 OK (its own headless labwc). `test_checkout_sources.py`: 6 OK. `test_ways_back_model.py -k ScopeTest`: 4 OK. The probe host-walk test: OK. The flaky test ×15: 15 passed.
- `gh run download 43673448694` (then removed); font comparisons; a scratch fontconfig experiment; read-only `stat` and `fc-match`; diffs against 22d's and 40's branches.

CHANGES-NEEDED
