# Package 40, review 1 (PR #71, `pkg/40-real-home` at `8607b925`)

Reviewer: a fresh Claude agent on Opus 5.5, not a builder of this package. Read only, except this file.

**Verdict: CHANGES-NEEDED** (1 blocking, 2 should-fix, 6 nits). The blocking item is privacy in the brief that this PR
adds. It is a text edit, so it needs no builder round. I found no blocking bug in the mod, the helper, `rc.xml` or
`run-hub.sh`.

## What I checked, and how

- I read the brief, REPORT.md, CLAUDE.md, AGENTS.md, docs/REVIEW.md and the three-dot diff (50 files).
- Minecraft 26.2 behaviour, checked against the deobfuscated jars in the Loom cache with `javap` (no Gradle, no game):
  - `runTick` sets `pause = hasSingleplayerServer() && Gui.isPausing() && !singleplayerServer.isPublished()`. So
    `MinecraftCoveredMixin` never pauses a world opened to LAN.
  - `MultiPlayerGameMode.canHurtPlayer` and `hasExperience` are called only by `Hud`, so `LiveHudMixin` changes nothing
    else.
  - `Window.fullscreen` is set only in the constructor (redirected), `toggleFullScreen` (cancelled), `setMode` and
    `setWindowed`.
  - `FramerateLimitTracker.getFramerateLimit` is what `runTick` throttles by.
  - `ServerPlayer.<init>` assigns `gameMode` before it calls `setGameModeForPlayer`, so `LiveMode.isLive` cannot hit a
    null there. `restoreFrom` calls the setter and then copies attribute base values, which still gives 0.15.
- Helper test modules, each run alone from `os/tests`. All OK:
  - `test_aresos_shell_home` (10), `_protocol` (21), `_windows` (33), `test_aresos_shell` (74);
  - `_review_fixes` (31), `_review_fixes_2` (16), `_review_fixes_3` (12), `_review_fixes_4` (11);
  - `_launch_hints` (13), `_hardening` (26), `_discovery` (36), `_icons` (43);
  - `test_aresos_desktop -k recovery_terminal_shortcut` (1).
- **Do the helper tests fail without the change?** I mutated a scratch copy of the helper under my scratchpad (never
  the worktree). Every mutation below made at least one test in `test_aresos_shell_home` fail:
  - no `uncover()` call;
  - no start-up guard (`previous_handle is not None`);
  - no per-screen check in `covering()`;
  - minimized windows counted as covering;
  - `emit` not checking the minor for `shell_covered`;
  - hello offering `shell_covered` to minor 0;
  - no `windows_pending` on hello;
  - no `output_gone` on unplug;
  - no binding of a screen plugged in later.

  The report's "7 errors against the old helper" came from the constructor's new `minimize=` argument. The mutations
  show the tests also catch the behaviour itself.
- **Java tests, checked by reading.**
  - `coveredReachesListenersAndALostHelperUncovers` fails without `case "shell_covered"` or without the
    `setCovered(false)` in `session()`'s `finally`.
  - The client test's focus part fails without each redirect, because it switches `HomeScreen.forTests` between the
    two rules.
  - `heartbeatsKeepSayingReadyWhileCovered` only guards, as the report says.
- **`rc.xml`.** No line is removed, and the original `aresos-desktop` line still matches the `image-checks.sh` grep
  exactly. labwc 0.9.6's man pages confirm `ToggleAlwaysOnBottom` and that one identifier can match several rules.
  The once-per-first-map claim and "the toggle cannot flip back" come from the rig, not from the man page.
- **`run-hub.sh --session`.** Every process runs in a scope of the run and is stopped by scope.
  - The nested labwc gets `-C` with only `rc.xml`, so no `autostart` or `environment` file is read.
  - Its activation-environment update is off by default when nested, and also set to 0 explicitly.
  - The helper and the game get the nested `WAYLAND_DISPLAY`, `DISPLAY` and `LABWC_PID`, checked to differ from the
    outer ones.
  - `close_game` points only at the nested socket.
  - On the owner's desktop, `preview-window.py` only sends `set_fullscreen` to a new window whose app ID is `labwc`.
- **Privacy.** The four pictures under `reviews/40-real-home/screenshots/` show only:
  - the rig's own `foot` window titled "Test app";
  - the world with a generated logo;
  - the Live HUD;
  - a black frame.

  The code, docs and PR description name none of his programs. See finding 1 for the brief.

## Findings

### 1. blocking: the brief added by this PR names his installed programs

**Where:** `briefs/40-real-home.md:5`, `:27` and `:28`. Line 5 quotes him with "at least [one app] didnt" (an installed program by name). Lines 27
and 28 name a second installed program twice.

**Why it matters:**
- The repo is public, and the brief's own rule says "Never name his programs in the repo".
- The first name is already on main (`STATE.md:155`). The second is not, so merging publishes it there.
- The branch history has the same problem. Commit `4f387f44` added that second name to PROGRESS.md and `41fffbfe` removed
  it. A squash merge keeps that out of main, but PR #71's commit list keeps showing it.

**Fix:**
1. Before merging, redact the three lines. For example: "at least one app didn't" (keep the rest of his quote), and
   "three apps only (Terminal, Discord and a single-copy file-sharing program)".
2. Optionally, rewrite the branch to drop the `4f387f44`/`41fffbfe` pair and force-push before the squash merge. That
   is the owner's call; GitHub may still serve the old SHAs.

### 2. should-fix: a second activation of a restored desktop minimizes the app in front

**Where:** `os/config/usr/libexec/aresos-shell:3559` to `3574`.

**What happens:** package 23's `keep_foreground` hands focus back once and then turns itself off (`:3563`). If the
restored game window is activated a second time while the app is still in front, the new branch at `:3572` to `:3574`
handles it:
- `previous_handle` is the app the hand-back just activated;
- so `uncover()` runs and minimizes that app when it is maximized or fullscreen on the world's screen.

**Scenario:** the game crashes while he works in a maximized app. The supervisor restarts the game with
`ARESOS_SHELL_KEEP_FOREGROUND=1`. labwc focuses the new window as it maps, and the helper gives the focus back to the
app. Then GLFW's focus-on-show request (`glfwShowWindow` sends `_NET_ACTIVE_WINDOW`, which labwc honours for a mapped
view) arrives. The app is minimized and the world comes to the front, which is exactly what B2 exists to prevent.

**Evidence and confidence:**
- I reproduced the code path with the package's own `Screens` harness in a scratch copy: hand-back, then the app
  activated, then the desktop activated again 0.5 s later. The helper sends `set_minimized` for the app.
- Not verified: whether the second activation really happens under labwc. It depends on whether GLFW's request
  arrives after the view maps; for an unmapped view labwc ignores it.
- Before this package a second activation only left the world focused under the app (B2's existing gap). Now it also
  minimizes his app.

**Fix:** do not uncover while a hand-back is fresh. For example:
- in the keep branch, remember `self.kept = (target.handle, now)`;
- in the SHELL branch, skip `uncover()` when `previous_handle == self.kept[0]` and `now - self.kept[1] <= KEEP_WINDOW`.

Add a `CoveredTest` case: a restored desktop activated twice within `KEEP_WINDOW` minimizes nothing. This is under
`os/`, so linux-aresos should see it.

### 3. should-fix: no hosted OS regression run for the `os/` changes

**Where:** PR #71's checks. The PR shows only "Build, test and reproduce jar" (mod.yml). `os-image.yml` runs only when
dispatched.

**Why it matters:**
- The helper, `rc.xml` and `test_aresos_desktop.py` changed.
- AGENTS.md says the full `os/tests` count comes from the hosted run.
- The report lists four helper modules. I ran all thirteen helper modules locally (all OK), but that is not the full
  suite, and `image-checks.sh` is not run.

**Fix:** run `gh workflow run "OS image" --ref pkg/40-real-home -f checks_only=true`, wait with
`gh run watch <id> --exit-status --interval 60`, and put the result in the report.

### 4. nit: uncovering minimizes windows whose screen is not known yet

**Where:** `aresos-shell:2533` (`not t.outputs`), used by `uncover()` at `:3428`.

JUDGMENT-CALL 7 errs toward "same screen", which is harmless for the pause. For a minimize it errs toward hiding a
window that may be on the other screen: one that labwc mapped a moment before the world was activated.

**Fix:** in `uncover()`, minimize only windows whose known outputs overlap the world's. Or accept it and say so in
JUDGMENT-CALL 7.

### 5. nit: the nested labwc inherits the launch identity

**Where:** `mod/dev/run-hub.sh:220` exports `ARESOS_DESKTOP_INSTANCE` and `ARESOS_LAUNCH_NONCE`; `:223` then starts the
watcher (`:150`) and the nested labwc (`:162`) with them.

Anything labwc starts by itself inherits the nonce: labwc's default root menu "Terminal", or a keybind's `Execute`.
The helper keeps the nonce from apps on purpose (`PRIVATE_ENVIRONMENT`). A dev client started from such a terminal
would also take itself for a session (`HomeScreen.session()`).

**Fix:** add `-u ARESOS_DESKTOP_INSTANCE -u ARESOS_LAUNCH_NONCE` to both `env` calls.

### 6. nit: `preview-window.py --close` relies only on `run-hub.sh`'s check

**Where:** `mod/dev/preview-window.py:149` to `:160` and `:170`.

Once package 23 is installed, the owner's real game window has the same app ID, `aresos-desktop`. Today only the
`$wayland != $WAYLAND_DISPLAY` check in `start_session` keeps `--close` off his session.

**Fix:** have `--close` refuse `wayland-0` itself, as the rig tools do, so the guarantee does not depend on a check in
another file.

### 7. nit: smaller gaps in the preview and the rig

- **Closing the preview may not end the run.** If the watcher never matches the nested window (an outer desktop
  without foreign-toplevel v2, or another app ID), it keeps running (`preview-window.py:198`). Closing the preview
  window then does not end the run: the game goes on in a labwc with no output until Ctrl+C. Say so in the "cannot
  show" list, or end the run when that labwc's output goes away.
- **The rig breaks two of the scripts' rules.** `reviews/40-real-home/rig/inner.sh` calls `gradlew --no-daemon
  runClient` directly, against AGENTS.md's "use the scripts". `load.sh` finds the game with
  `pgrep -f 'net.fabricmc.devlaunchinjector.Main' | head -1`, which may sample another builder's client or `hub-try`'s.
  Both are committed development aids: label them as such, or pass the PID in.

### 8. nit: paths that matter and have no automated test

- **The real `active()` condition.** `HomeScreen.active()` checks a session, a desktop world and a CONNECTED helper.
  Every client test forces it with `forTests`; only the rig ran it. A mistake there would silently turn the home
  screen off in the session while every test stays green.
- **A saved `fullscreen:true`.** The constructor redirect that ignores it was also checked only in the rig.
- A small unit or client check would cover both: `HomeScreen.active` against a real `ShellClient` status, and a
  `Window` built with `fullscreen:true` in a session.

### 9. nit: the docs and an open question

- **Music while covered.** HUB.md says "The sounds come back when the pause ends". Music in fact keeps playing while
  covered: vanilla pauses all sounds except music and UI. Say so, or decide whether the home screen should be silent
  behind a maximized app.
- **The likeliest cause of B is still silent.** PLAN-GAP 1's best explanation for his "didn't open" is a click on an
  app in the Apps screen, which picks the item up and opens nothing, without a word. Point 5 does not list that
  screen, but "Nothing happens silently" is the point. Worth a decision before the try-out: open on click, or one line
  such as "put it in the hotbar to open it".

## Not findings (checked and fine)

- **Covered always ends:**
  - a lost or hung helper: the `finally` in `ShellClient.session()` sets it false, and `active()` needs CONNECTED;
  - a world closed while covered: `active()` needs a player and the singleplayer server, and the pause is computed
    only with one;
  - leaving and joining again: the flag mirrors the helper, which still knows the truth.
- **Heartbeats while paused:** they come from the shell client's timer, and `readyWorld` does not look at the pause.
- **No loop with labwc:** minimizing a window that is not active does not move the focus in labwc. After the minimize
  the active window is unchanged, so `uncover` does not run again.
- **Covered only to clients that offered it:**
  - `emit` checks the client's own list and minor ≥ 1;
  - the hello reply drops `shell_covered` for minor 0;
  - an event read during the first `list_apps` is dispatched by `call()`, not lost.
- **A non-desktop world is untouched** on join, respawn (`AFTER_RESPAWN` is guarded), every mode switch (the mixin
  returns at the marker check), and when the marker is off or was never set (`enabled || was`). The HUD is untouched
  too (`acceptsAppCommands`).
- **Malformed compositor messages:** a short payload in an `output_enter` or `output_leave` raises `struct.error`
  outside `connect()`, the same as the existing `state` and `parent` handlers. Nothing new in kind. The wl_output
  events of bound outputs are ignored. Output object IDs are never reused, because the client's IDs only grow.
- **Sound after the pause:** `pausing()` resumes sounds only for a pause that was its own.
