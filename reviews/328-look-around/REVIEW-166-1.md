# Review 1 of PR166 (328b–328d)

**Scope.** I read `briefs/328-look-around.md`, `reviews/328-look-around/REPORT.md` and the PR's files at HEAD:
- `LookMode`, `ClickLook`, `EdgeTurn`, `PointerRules`
- `LookSetting`, `ClickToLook`, `EdgeLook`, `HomeScreen`, `HomePointer`, `WorldCapture`, `ShellFocusClient`
- the mixins `MouseAppInputMixin`, `KeyboardAppInputMixin`, `MinecraftAppInputMixin` (with the `@ModifyExpressionValue` on `isMouseGrabbed` in `handleKeybinds`) and `RenderSystemCaptureMixin`
- the new unit and client tests, `mod/dev/run-hub.sh`, `mod/dev/env.sh` and `mod/README.md`

I only had a file reader, with no shell. So I couldn't run `git diff origin/main...HEAD`, and I didn't run any build or test. Instead, for each of `classic`, `click` and `edge`, I traced every new branch in these files.

## Checks

1. **Design A holds in every mode.** Every capture and release goes through `MouseHandler.grabMouse` / `releaseMouse`, whose `grabOrReleaseMouse` calls are wrapped into `WorldCapture.grab` / `release`. That covers `ClickToLook.start` and `afterPollEvents`, the edge release in `HomeScreen.frame`, `HomePointer.enterWorld`, `ShellFocusClient.apply` and the free-pointer refusal at the head of `grabMouse`.
   - `WorldCapture.returnToCentre` sits inside `WorldCapture` and only moves the point the pointer returns to.
   - `EdgeLook` only reads from GLFW: window position and size, monitors, video mode and monitor position. It reads keys through `InputConstants.isKeyDown` and the hover test through `WorldCapture.pointerOverWorld`. It makes no cursor-mode or cursor-position call.
   - In `edge` every grab is refused before the wrap, so the XFixes hide never runs.
2. **`classic` is unchanged, and outside a session's desktop world everything is vanilla.**
   - With `look = classic`, these are all false: `ClickToLook.on` / `idle`, `EdgeLook.on` / `setting`, `clicksAct` (it equals `appInFront && !appInFront`) and `worldActs` whenever the pointer is free. The key hook returns and `afterPollEvents` returns. The new `onMove` hook only sets a flag.
   - Outside a session's connected desktop world, `PointerRules.free`, `ClickToLook.on` and `EdgeLook.on` all need `HomeScreen.active`. Every new branch is therefore off, and `LookSetting` only reads its file.
   - Tests that stand for a session are pinned to `CLASSIC` in `HomeScreen.forTests`.
3. **No blocking harm found.**
   - **`click`:** look mode always ends through 328a's release on Esc, an app taking focus, GLFW focus loss or the helper dropping. The starting press and its release are both swallowed, so a right click doesn't use or launch either. Q, E and 1–9 aren't movement keys, so they keep their vanilla meaning.
   - **`edge`:** the cursor is never hidden. Turning stops when the cursor leaves a band, leaves the world (hover test), or a screen or app is in front. A long frame is capped at 0.1 s.
   - **Live mode:** it refuses block breaking (package 327).
   - **Crashes:** a bad settings file falls back to classic, because `IOException` (including malformed encoding) and `IllegalArgumentException` are caught. Findings 1–4 below are what's left.
4. **`run-hub.sh --outputs 2`** is safe on this point.
   - `--outputs` takes only 1 or 2 and needs `--session`.
   - `env.sh` changes to `mod/`, so the symlink guard really checks `mod/run`, `mod/run/saves` and `mod/run/saves/AresHub`. The game uses the checkout's `mod/run`, not the owner's Prism home.
   - Nothing opens unless he runs it. The client tests are headless, and the rig refuses `wayland-0` and `:0`.
   - `hub-try` isn't in the repo, so its argument forwarding rests on the report.
5. **The tests mostly prove the claims.** The gaps are in item 10.

## Blocking findings

None.

## Known limits / nits

1. **In `edge`, the view can look up but never back down.** `EdgeTurn.edges` only ever lowers pitch, through the top band. `EdgeTurn.keys` only turns left and right. `aresos$ignoreBackgroundMotion` cancels mouse turning while the pointer is free.
   - The report's "How to try it" sends the owner to the top edge, and after that the sky stays put. Only H or `/home` (home arrival sets the saved facing) or restarting the preview brings the view level again.
   - Nothing is lost, but it will skew how he judges this prototype.
   - **Suggested fix:** before the trial, let Up and Down tilt the view, or ease the pitch back toward level outside the top band. At the least, add "H levels the view" to "How to try it".
2. **In `edge`, clicks act at the crosshair, not under the visible pointer.** This is what the brief asked for, it's already listed under Known limits, and the trial uses a disposable world.
   - In Build mode, one left click instantly breaks the block at the crosshair, and a town block broken that way becomes the owner's and is never rebuilt.
   - In Live mode, a right click with an app selected launches it, and hits on entities (item frames, paintings) aren't covered by 327.
   - **Suggested fix:** say this in the Edge paragraph of "How to try it" and in the README table.
3. **In `click`, a stuck button flag can keep look mode on.** `ClickToLook.held` trusts `MouseHandler`'s `isLeftPressed` / `isRightPressed` / `isMiddlePressed`.
   - If an app takes focus while a button is held in look mode, `HomePointer.button` swallows both the real release and GLFW's own release on the mod's FocusOut, because the pointer is free at that moment. The flag stays set.
   - Every later look mode then ignores stillness until he clicks once inside look mode or presses Esc.
   - **Suggested fix:** use `options.keyAttack` / `keyUse` / `keyPickItem.isDown()` instead, which `KeyMapping.releaseAll()` clears on every release and focus change. Alternatively, clear the three flags in `aresos$releaseHeld`.
4. **The two-window preview probably can't hold the real pointer.** As far as I know, wlroots' Wayland backend doesn't pass a nested client's pointer lock to the outer desktop; I couldn't check this here.
   - If so, while `classic` or `click` has the mouse in `--outputs 2`, the owner's real pointer keeps moving. Turning stops at the preview window's edge, and the pointer can leave onto his real desktop, where a click reaches his real apps or his running home.
   - The two windows also open at default size, so the real desktop shows between them unless he maximizes them.
   - `edge` doesn't capture, so it is faithful in the preview.
   - **Suggested fix:** check this in a headless nested run. Add it to the Preview known limits, and tell him to maximize both windows.
5. **In `click`, `HomePointer.enterWorld` calls `AresOsClient.returnedFromApp()` on every click that starts look mode,** not only when an app was in front. A click between walking into a logo and the app's window appearing ends the visit early: he is moved to the logo's exit before the app opens.
   - **Suggested fix:** only call it when an app was in front.
6. **`aresos$edgeHeldAttack` has no ordinal,** so it changes every `isMouseGrabbed()` call in 26.2's `handleKeybinds`. It's only active in `edge` with the world in front.
   - **Suggested fix:** pin it to the `continueAttack` argument, or add a comment naming the call.
7. **`ClickToLook.key` does work on every key event, even outside the home.** Java evaluates all its arguments, so `client.gui.screen()` / `overlay()` and six `KeyMapping.matches` calls run each time. The behaviour is unchanged.
   - **Suggested fix:** check `on(client)` first so the rest is skipped.
8. **The README points at the installed Prism home's config.** That invites trying the prototypes in his running home, which ignores the line until a release includes package 328.
   - **Suggested fix:** scope that line to "after a release with package 328", or keep the trial to `hub-try`.
9. **Smaller limits:**
   - The symlink guard only covers `--outputs 2`. The Classic and Click paragraphs use plain `hub-try` on the same `AresHub`, so the guard should cover every `--session` run.
   - In `click`, any one-count mouse movement restarts the 800 ms, so a jittery mouse can keep look mode on (Esc still works).
10. **Test gaps:**
    - The native 328b test has no probe app over the window's centre, although the brief's session setup has one. It also doesn't check that the native starting click attacked nothing.
    - Nothing covers an empty hotbar slot starting look mode, a start from jump or sneak, a right-click start not launching, or item 3.
    - `--outputs 2` was only dry-checked. It could have been smoke-tested nested inside a private headless compositor.
    - The arrow-key check covers the default mappings only.
    - "Classic unchanged" rests on the report's recorded full-suite runs, which I couldn't rerun.

SAFE
