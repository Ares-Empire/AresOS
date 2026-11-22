# Package 328 — Look around without holding a button

## Done

**328a — The world keeps the pointer.** Minecraft and GLFW warped the visible X pointer to the centre of the world window during capture. Xwayland translated those warps into short-lived pointer locks with centre hints. When labwc dropped a lock, it moved the cursor to its hint. The camera could turn while an app over the world's centre received clicks and scroll. `WorldCapture` hides the cursor through XFixes before capture and uses GLFW's focus handling to finish release, including after focus moves or the helper disconnects. A new capture requires compositor focus and the pointer over the visible world, and release clears held attack, use and movement. Classic remains the default. [Merged PR #148](https://github.com/Ares-Empire/AresOS/pull/148) · [Before trace](traces/before-fix-capture-trace.txt) · [After trials](traces/after-fix-trials.txt) · [Final recheck](RECHECK-2.md)

**328b — Click to look.** `LookMode`, `ClickLook` and the client input hooks keep the pointer free until a world click or a movement key starts looking. The first click and its release are consumed, and a primary click on a hotbar app still opens the app. The capture ends after 800 ms of mouse and movement stillness, on Esc, or when an app takes focus. A click start restores the pointer to the starting point when possible, and a key start uses the centre of the world's output. The 250 ms focus grace lets a world click complete capture if GLFW gets focus just after the press. The stillness timer runs after input polling so queued movement counts even after a slow frame.

**328c — Edge turning.** `EdgeTurn` and `EdgeLook` keep the pointer free and turn the camera in the left, right and top 48-pixel bands, up to 120 degrees per second. A shared stretch uses GLFW's output layout and lets the pointer cross. A leave event stops turning from the last cursor position. Left and right arrows turn at the same top speed. Movement, Q and E keep their usual bindings, and world clicks act at the crosshair after hotbar app clicks get priority. Turning is disabled over a covered part of the world and while a menu or app has focus.

**328d — Trial and handover.** The mod README gives the settings file for the installed Prism home and the try checkout. `mod/dev/run-hub.sh --session --outputs 2` gives nested labwc `WLR_WL_OUTPUTS=2` and two movable windows. Labwc adds the outputs to wlroots' horizontal layout. The preview uses the checkout's disposable `mod/run/saves/AresHub`, a private helper socket and its own compositor. The two-output option refuses a symlink at `mod/run`, `mod/run/saves` or the trial's `AresHub`. The existing `hub-try` wrapper supplies `--session` and forwards `--outputs 2`. [Mod README](../../mod/README.md) · [Labwc output setup](https://github.com/labwc/labwc/blob/0.9.6/src/output.c) · [wlroots output layout](https://github.com/swaywm/wlroots/blob/master/types/wlr_output_layout.c)

## Verified

The 328a rig used private headless labwc with two side-by-side 1280×720 outputs, the image's window rules, private D-Bus, virtual input and an inert Wayland probe over the native dev client's centre. The client ran on a disposable save. The original capture leaked click and scroll even with zero motion. With the fix, the game registered click and hotbar scroll, the camera turned 46.8 degrees, and probe counters stayed at `[1, 0, 2, 0]`. The final focused and full runs checked 75 focus-race cycles, all settling with the cursor visible and the X grab free. They also checked Esc, app focus, helper death and world exit. Returning focus with the pointer on the probe left it free. [Rig](rig/) · [Builder notes and earlier runs](https://github.com/Ares-Empire/AresOS/blob/b7f8129a7782e0bd46d774181fe98ad2ce87e75b/reviews/328-look-around/PROGRESS.md)

Earlier steps recorded these successful full passes. The client commands all exited 0. Each build passed all 106 required server game tests.

| Step | Pass | Build | Headless client suite |
| --- | --- | --- | --- |
| 328a (`edff64d5`) | 1 | `mod/dev/build.sh --rerun-tasks` in 2m 46s | `mod/dev/client-test.sh --session` in 15m 51s |
| 328a | 2 | `mod/dev/build.sh --rerun-tasks` in 2m 51s | `mod/dev/client-test.sh --session` in 15m 56s |
| 328b (`ac48a3a1`) | 1 | `mod/dev/build.sh` in 1m 49s | `mod/dev/client-test.sh --session` in 16m 6s |
| 328b | 2 | `mod/dev/build.sh` in 1m 50s | `mod/dev/client-test.sh --session` in 16m 4s |
| 328c (`37f23912`) | 1 | `mod/dev/build.sh` in 2m 38s | `mod/dev/client-test.sh --session` in 16m 25s |
| 328c | 2 | `mod/dev/build.sh --rerun-tasks` in 2m 50s | `mod/dev/client-test.sh --session` in 16m 26s |

- 328a ran 339 unit cases with 333 passing and six Windows-only skips. The full client suite ran 30 entrypoints in each pass. The race test verified visible cursor restoration, independent X grab availability and capture on the next click.
- 328b ran `mod/dev/build.sh test --rerun`. It printed `BUILD SUCCESSFUL` with 352 unit cases, zero failures and six Windows-only skips, including `ClickLookTest` and `LookModeTest`. The full client runs checked click and key starts, stillness, Esc, app focus and regrabs. The native test turned the camera 22.8 degrees, returned the pointer to the click and crossed to output 2. A key start returned the pointer to the centre of the world's output.
- 328c ran 360 unit cases in each build with zero failures and six Windows-only skips, including `EdgeTurnTest`, `LookModeTest` and `PointerRulesTest`. The full client runs passed the 328a and 328b tests and checked edge turning, pass-through, pointer leave, arrows, Q and E, walking, hotbar app clicks, world clicks and app focus. The native left edge turned about 45 degrees in each run, and the shared edge let the pointer reach output 2. The client checked that the shipped key mappings leave both arrows free.
- 328d ran `mod/dev/build.sh` once after checking that 8,812 MiB were available and there were zero active Gradle JVMs. It printed `All 106 required tests passed :)`, `:test UP-TO-DATE` and `BUILD SUCCESSFUL in 1m 49s` (exit 0). Step 328d changes only the script and docs, so the recorded client runs are from the earlier steps.
- 328d ran `bash -n mod/dev/run-hub.sh`, 14 dry checks and `git diff --check`. With the display and runtime variables unset, valid forms reached the missing-runtime guard (exit 1). Invalid counts, a count without `--session`, forwarded `--daemon` and three simulated save symlinks were refused (exit 2). A source check of the installed `hub-try` wrapper confirmed its argument order and forwarding. No compositor or preview was started. There are no new screenshots. Earlier runs restored the unchanged review screenshots and removed transient copies. No files over 500 MB were left in `.work/`.

## Known limits

- **Classic and capture.** Returning focus with the pointer over another app or output leaves it free. Movement still works with keyboard focus. A release can finish at the next event poll, and a click during that interval may need a second press. Focus loss can put the cursor where labwc left it, often at the centre. A held movement key may need a fresh press after closing the menu, and holding Escape across release can emit an extra press. A helper that stops sending focus events can leave capture in place until the frame check detects the loss. The native release uses the 64-bit Linux X event layout. Outside the X11/XFixes path, vanilla release can restore to the window centre. On X11 without XFixes the stale grab is still possible.
- **Click.** Toggle sneak counts as held until toggled back, Esc, or app focus. A click that the capture guard refuses is consumed and a later click can try again. In click and edge modes, scrolling a free pointer over the world can still change the hotbar slot.
- **Edge.** Clicks use the crosshair. Away from the bands the mouse moves the pointer without turning the view, and resting in an unshared band keeps turning. Layout changes can take up to 500 ms to register. Scaling that leaves a reported one-pixel gap, or a panel that pulls the maximized world away from an output edge, can make a shared edge turn. A personal arrow binding would fire alongside turning.
- **Preview.** The outer desktop handles its own shortcuts. An already-running single-instance app can open outside the preview, as can D-Bus prompts and file choosers.

## Not verified

The live two-window launch, the feel of both prototypes on the owner's laptop and monitor, scaled physical outputs, Chrome, the installed helper and Prism, the owner's arrow bindings, and dead-key restoration during X11 release remain untested. The headless client runs used test input and the development client.

## JUDGMENT-CALL

- Click treats a held mouse button as activity so a long attack can finish. Counting stationary holds as idle would release the pointer during a continuous action. The activity rule and 800 ms threshold are local to the click prototype.
- Edge uses crosshair picking and the initial 48-pixel and 120-degree-per-second values. Cursor-based picking would require a separate targeting path. The edge width and speed can each be tuned at a named constant.
- The two-output preview leaves both outer windows movable and reuses the dev save between trials. Auto-fullscreen would leave placement to the outer compositor. A fresh save each run would reset the trial world and require separate save lifecycle handling. Placement policy is confined to the launcher.

## PLAN-GAP

- A part-screen app stayed above the world in the 328a rig. The helper minimized the probe only when it was maximized, on the world's output, and the world regained focus. The code also accepts fullscreen in that condition. The reason Chrome disappeared on the owner's laptop remains open.
- Native Wayland would avoid the specific Xwayland centre-warp sequence because GLFW can request a pointer lock directly. It also changes focus semantics, window position reporting and the GPU rendering path. It would require a separate launcher or mod change and its own verification.

## Open questions

- Which mode feels right when crossing to the monitor, and should the chosen prototype's timing or turning speed be tuned?
- Can the original part-screen Chrome disappearance be reproduced with the window's maximized/fullscreen state and the helper journal available?

## How to try it

**Classic.** Once the trial checkout is on this branch, put `look = classic` in `~/AresOS-try/mod/run/config/aresos/settings.properties` or leave the line out. Start `hub-try`. The world holds the pointer to look around when it has focus and the pointer is over it. Press Esc to free it. Restart the preview after each setting change.

**Click.** Set `look = click`, then click open world or press a movement key to look around. The first click just starts looking. Let the mouse and movement keys rest for 0.8 seconds and the pointer is free to cross to the monitor. Esc or focusing an app also frees it.

**Edge.** Set `look = edge` and run `hub-try --outputs 2`. Put the two preview windows on the laptop and monitor in left-to-right order with their shared edge lined up. In the dev world, try the left, right or top edges or the arrow keys to turn, then move across the shared edge. The pointer should cross without turning there. You can use the same two-screen command to compare all three modes.
