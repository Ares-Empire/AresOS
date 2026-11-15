# Package 40, review 2 (PR #71, `pkg/40-real-home` at `2cdca28d`)

Reviewer: a fresh Claude agent on Opus 5.5. I did not build this package or write review 1. I only read, apart from
this file. This review covers review fixes 1 (`de64e47d..2cdca28d`) and what those fixes touch.

**Verdict: CHANGES-NEEDED** (0 blocking, 1 should-fix, 2 nits). Every REVIEW-1 finding this round answers (2, 4 to 9)
and every item of the fix brief (1 to 8) is done, and I found no regression. The should-fix is a gap in item 7: a drag
can still open an app instead of picking up its item. The fix is a few lines and one test.

## What I checked, and how

- **Read:** both briefs, REVIEW-1, the REPORT's "Review fixes 1" section, CLAUDE.md, AGENTS.md, docs/REVIEW.md, the
  round's diff (34 files) and, where I needed context, the whole package diff.
- **Minecraft 26.2 behaviour,** checked with `javap` against the Loom cache jars (no Gradle, no game):
  - `runTick` calls `Gui.isPausing()` once, and only after `hasSingleplayerServer()` is true. `covered(client)` needs a
    singleplayer server (`acceptsAppCommands`), so `HomeScreen.pausing()` runs at every covered frame.
  - Closing or joining a world goes through `updateLevelInEngines(level, true)`, which calls `SoundManager.stop()`.
    Only `ConnectScreen` (multiplayer) disconnects without stopping sounds. So a sound paused for the cover cannot
    outlive the world, and the `silenced` flag left over from a closed world only causes a harmless `resume()` later.
  - `Channel.pause` and `unpause` act only on a playing or a paused source. `tickMusicWhenPaused` removes only stopped
    music channels, so a paused song stays and goes on where it was.
  - `MouseHandler.onButton` sends a press and a release to the screen at once, at the current pointer position.
    Movement reaches the screen only once per frame (`handleAccumulatedMovement`), and only while a button is still
    held and `isWindowActive()` is true. Finding 1 rests on this.
  - `AbstractContainerScreen.skipNextRelease` is set only in the constructor, `mouseClicked` and `mouseReleased`, never
    in `init()`. So the accessor's `false` survives `setScreen(parent)`. A release outside the panel with an app item on
    the cursor is refused by `AppInventory.keepsOnClick`, so the item is not thrown into the world.
- **The helper,** in a scratch copy (`git archive` of `2cdca28d`, never the worktree):
  - `test_aresos_shell_home` (13), `test_aresos_shell` (74), `_windows`, `_protocol` and `_review_fixes` 1 to 4: all OK,
    each module run alone.
  - Six mutations of the helper:
    - without the `aresos.cover` exclusion, the cover test fails;
    - without the hand-back guard, without its time limit, or without `self.kept` being set, the hand-back test fails;
    - with `uncover()` back on plain `covering()`, the known-screen test fails;
    - only `<= KEEP_WINDOW` turned into `<` passes, which is fine at the boundary.
- **23b's supervisor** (`origin/pkg/23b-startup-cover`): the cover uses app ID `aresos.cover`, the same as the helper's
  constant. When a cover is up, the supervisor never sets `ARESOS_SHELL_KEEP_FOREGROUND`, so the hand-back cannot target
  the cover.
- **The preview:**
  - In a scratch copy with `XDG_RUNTIME_DIR` pointing to a scratch folder, `preview-window.py` exits 2 for each of
    these: `--close … --display wayland-0`, a path ending in `/wayland-0/`, `--outputs --display wayland-0`,
    `../x/wayland-0`, and both bad usages.
  - I never set `WAYLAND_DISPLAY=wayland-0`. The environment variable goes through the same check, which I read.
- **2cdca28d:**
  - `os-image.yml`, `rehearsal-packages.json` and `test_ways_back_model.py` are byte-identical to 23b's `38815762`.
    Main has not touched them since the base.
  - I ran `rebind.changed()` read-only. It lists exactly the four rows in `pending-rebind.json`:
    - this PR's two bound files: `os-image.yml` and `rehearsal-packages.json`;
    - the two test files that were already waiting.
  - The helper, `rc.xml`, `test_aresos_desktop.py`, `test_aresos_shell_home.py` and `test_ways_back_model.py` are not
    bound.
  - `python3 -B -m unittest discover -s os/tests -p test_checkout_sources.py`: 6 tests, OK.
- **Privacy:**
  - I matched the added lines and commit messages of the round and of the whole package against the names of the
    programs installed on the laptop (user desktop entries and Flatpak exports). Matches:
    - Discord and Lunar Client, which are allowed;
    - Okular, which comes from the system Flatpak installation (the image's own Flatpaks, listed in
      `os/manifest/ci/14`) and has been a test fixture on main since package 34.
  - PDF Arranger, Ark, Xournal and `org.kde.kwrite` are older fixtures on main and are not installed.
  - This round adds no pictures and no personal data.

## Findings

### 1. should-fix: a drag whose movement arrives with the release opens the app

**Where:** `mod/src/client/java/dev/aresos/client/AppsScreen.java:226` to `235` (`mouseReleased`). Only
`mouseDragged` (`:214` to `223`) tells a drag apart.

**What happens:** `mouseReleased` opens `pressed` without looking at where the button was let go. Minecraft sends the
press and the release to the screen straight from GLFW's callbacks. Movement goes to the screen only in
`handleAccumulatedMovement`, once per frame, and only while the button is still held. So when the move and the release
are in the same event poll, the screen gets `mouseClicked`, then `mouseReleased` at a point far away, and never
`mouseDragged`. The program opens and nothing is picked up. The same happens on every drag while `isWindowActive()` is
false, which is the case in the tests' compositor (the report says so).

**Scenario:** he presses on a program and pulls it towards the hotbar while the game hitches for a moment. A garbage
collection, a logo being built in the town, or the first frames of a 157-row list are enough. The press, the movement
and the release arrive in one poll, and the program opens instead of its item landing on the cursor. The decision says
a drag must never open an app. A quick flick has the same effect.

**Fix:** in `mouseReleased`, open only when the release is within `DRAG` of where the press began. Further away, it is
a drag that ended before a frame saw it: call `pickUp(id)` (the item waits on the cursor, as the report already
describes for an early release), or at least open nothing. For example:

```java
if (Math.max(Math.abs(event.x() - pressedX), Math.abs(event.y() - pressedY)) > DRAG) pickUp(id); else open(id);
```

**Test:** in `MyAppsClientGameTest`, send `mouseClicked` at a row and then `mouseReleased` 8 pixels lower, with no
`mouseDragged` in between. Nothing opens, and the item ends up on the cursor (or nothing happens).

### 2. nit: after the hand-back guard, the world keeps the keyboard behind the app

**Where:** `os/config/usr/libexec/aresos-shell:3587` to `3605`.

**What happens:** when the guard fires (`kept`), the helper skips only `uncover()`. It still does what it does for a
deliberate return to the world:
- `cancel_returns()`;
- `shell = 'foreground'` and `shell_focus foreground`, so the mod captures the mouse.

**Scenario:** the restored game window is activated a second time (GLFW's focus-on-show). The world then has the
keyboard while his maximized app hides it, and stays paused and silent behind it until he clicks the app. That is
B2's gap from before package 40, not a regression, and it is not "covered for good", because one click on the app ends
it. But the code now knows this activation was not his choice.

**Fix (optional, linux-aresos's call):** in the `kept` case, call `activate_window(self.kept[0])` once more and leave
`shell` as it is. Then the app keeps the focus as B2 intended. Clear `self.kept` afterwards so this can never loop.

### 3. nit: the pending-rebind note names files that are not bound

**Where:** `os/manifest/ci/16/pending-rebind.json:8`.

**What it says now:** the note reads "40: the home screen (helper covered/minimize, rc.xml always-on-bottom rule, one
test assertion) and the checks timeout from 22d/23b".

**Why it is wrong:** none of the home-screen files are bound. The files this note stands for are `os-image.yml` and
`rehearsal-packages.json`. The other notes in the list say which bound files changed and add "no tool, guide or image
file changed".

**Suggested note:** "40: the checks-only job's 40 minutes, as 22d step 2 and 23b (os-image.yml, the 22c ledger's
checks bound and the test that pins both); no tool, guide or image file changed".

**At merge:** 22d and 23b carry the same three-file change. Whichever of them merges before this PR, this file will
conflict on the `changes` and `files` lists. Resolve it with `rebind.py pending` on the merged tree, as their merges do.

## Not findings (checked and fine)

### The helper

- **The cover never covers and is never minimized:**
  - `covering()` skips it on both paths;
  - `uncover()` minimizes only what `covering(known_screen=True)` returns;
  - `report_covered()` uses `covering()`.

  So the cover is never minimized and never pauses the world, whether it is active, the previous window, or maps after
  the game's window. Nothing else in the helper minimizes. While the cover is up it counts as an unowned window, which
  only holds back a return to the world that the cover itself would hide.
- **The hand-back guard:**
  - It is keyed on the hand-back target and on 3 s from the hand-back.
  - It skips one `uncover()` per activation and touches nothing else.
  - It still works when the target's activation and the second activation of the game arrive in one read, because the
    keep branch sets `active_handle` itself.
- **Minimize only on a known screen:**
  - A world with no known output minimizes nothing.
  - A window with no known output still pauses the world, as JUDGMENT-CALL 7 now says.
  - labwc reports outputs from the first list on, because the helper binds outputs first. So this rule only matters for
    a moment.

### The mod

- **Silence while covered:**
  - Every frame pauses all sounds while covered.
  - When the cover ends, `resume()` runs, and if a pausing screen is open, Minecraft's own pause is put back.
  - The music manager stands still while covered and runs again afterwards.
  - Nothing stays muted after a lost helper: `active()` needs CONNECTED, so the next frame resumes.
  - Nothing stays muted after a closed world or a rejoin, because `stop()` clears every channel.
- **The Apps screen, apart from finding 1:**
  - A drag never reaches `mouseReleased`, because the screen switches to the inventory during the drag.
  - A click within 3 pixels never picks anything up.
  - Right-click removes, and the second press of a double click is ignored.
  - The search box gets the focus back after a click, and number keys type into it.
  - The scroll bar still drags, because `pressed` is null there.
  - Rows under All programs open, and a drag adds a program that is not his first. The server handles add and take in
    order, and `take` finds the item that `add` just placed.
  - The double click's second press lands in the world after the screen closes, which is a refused punch in Live.
    The app opens only once.
- **Tests:**
  - The click test fails against the old screen ("A click on Okular opened []").
  - The silence test fails without `pauseAllExcept()` (music keeps playing) and without `MusicCoveredMixin` (the
    countdown runs).
  - The `active()` and saved-fullscreen checks fail with each condition removed.

### The preview

- `--outputs` only reads the nested labwc's registry. `--close` acts only on `--display`, which `run-hub.sh` sets to
  the nested socket.
- Both refuse `wayland-0`. Neither kills a process.
- The nested labwc and both watchers start without the launch identity, and the nested labwc also without
  `LABWC_FALLBACK_OUTPUT`.

### The rig and the docs

- The rig labels are in place, and `load.sh` checks the PID it is given.
- HUB.md, OS-BASE and the README match the code.

CHANGES-NEEDED
