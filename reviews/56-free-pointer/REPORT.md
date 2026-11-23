# Package 56: free pointer, taskbar and flight

## Done

- **Cause:** focus was reported only as transitions. If an app took focus before the desktop connected, the helper sent no current-focus snapshot after hello. The common initializer could also receive an event before the client initializer subscribed, and loading/reconnect frames could erase it. In the ordinary headless session preview, the compositor showed the small app activated while Minecraft reported `helperFocus=null`, `front=false`, `grabbed=true`; mouse callback replay changed the view. Ordinary steady-state app focus did not reproduce it. Details and the distinction between native seat input and callback replay are in [rig/README.md](rig/README.md).
- **Helper and delivery:** the helper now reports existing background focus after hello, once per connection, using the existing negotiated capability even for minor 0. `ShellClient` caches and serializes replay to late listeners with subsequent events, clears old focus on disconnect, and marks every attempt STARTING. `ShellFocusClient` queues initialization-safe focus application and resets on actual loss. Loading and delayed reconnect handshakes retain the new focus.
- **Mouse/taskbar:** capture, turning, use and attack guards keep the app's pointer free; an existing load-time capture is released immediately. `HomePointer` resolves app-slot versus world clicks before capture in either helper/click ordering, swallowing the entry click. A new press clears a stale release-suppression bit, so a release delivered to an app cannot leave the next world attack/use held. App slots use the existing launch/error path. Hover reuses the game's border and item-name rendering without changing selection; number keys and scrolling retain their behavior.
- **Flight:** `LiveMode.DESKTOP_FLYING_SPEED = 0.075f` is the single tuning value for both Live and Build, 1.5 times vanilla. Walking remains 0.15; marker-off restores vanilla flight. Server checks cover speed on joining, switches, respawns and marker changes.
- **Tests/docs:** `FreePointerClientGameTest` is last in the suite. `client-test.sh --session` uses headless labwc with the image rules, no autostart, and the existing lock, room checks and cleanup. It drives two small native stand-ins and restores its temporary mouse callbacks. Native coordinates use GLFW's actual dimensions, including after earlier fullscreen tests. Added input-rule, ordered replay, late subscription, reconnect and helper-negotiation tests. Updated HUB sections 1, 2.2, 3.8, 5 and 7 and the mod README.

## Verified

- `origin/main` was current at the initial fetch. It advanced during work; merged `bda5d2a2` in `687fa5dc` (nine handoff/planning commits, no code conflicts). The closing fetch found seven more planning commits; merged `5c3457b5` in `a2bb88ed`. That final merge changes only HANDOFF, STATE and brief 53, so it does not change the tested source.
- `mod/dev/build.sh` passed, and `mod/dev/build.sh --rerun-tasks` passed with all 17 tasks executed. The latest startup build passed in **2m 44s**: **305 unit passes**, six existing Windows-only skips (311 discovered, zero failures/errors), and **all 106 server game tests passed**.
- The targeted native client run with the complete startup/reconnect fix passed in **55s**. It receives background focus before subscribing and loading, and delays the reconnect list reply while focus and client frames occur. It also covers each edge slowly/quickly, native Alt+Tab and close, both activation/click orders, launch/failure chat, lost releases for all three buttons, empty/non-app/world entry without item use, normal/session/helper gates, and unchanged scrolling/number keys.
- **Final complete fix, `81b1018e`:** `mod/dev/client-test.sh --session build` passed twice: **BUILD SUCCESSFUL in 15m 43s** and **BUILD SUCCESSFUL in 16m 1s**. Both completed the full client suite and all **106** server tests. The source and generated manifests contain all **27** client entrypoints; no assertions were weakened. Final unit XML totals: 311 discovered, 305 passed, six existing Windows-only skips, zero failures/errors.
- **Measured in both Live and Build:** 16.308910 blocks/s flying, 32.617820 sprinting, versus vanilla 10.872929 / 21.745213 (1.5 times). FOV 1.1 plain and 1.265 sprint, matching vanilla within 0.0001. No Speed effect; the server tests also check unchanged walking speed.
- **Ordinary preview, actual GLFW capture:** `run-hub.sh --session` inside headless labwc with the checkout helper and a small app already focused. Before and after attempted `grabMouse` plus motion replay: `front=true active=true glfwFocused=true grabbed=false`, yaw/pitch `180/-8`. Closing the app returned `front=false grabbed=true` with the same view. See [native-capture.txt](verification/native-capture.txt). Fabric masks native capture, so this was verified separately from its game tests.
- `python3 -m unittest discover -s os/tests -p 'test_aresos_shell_home.py'`: **15 tests, OK**. No full OS suite or `test_owner_update` was run on the laptop. Hosted full checks on `81b1018e`, dispatched with `gh workflow run 'OS image' --ref pkg/56-free-pointer -f checks_only=true` and watched with `--exit-status --interval 60`, **passed**: [44417752912](https://github.com/Ares-Empire/AresOS/actions/runs/44417752912). The regression job took 22m 47s and printed `Ran 1797 tests in 1277.089s`, `OK (skipped=4)`: 1,793 passes and four existing labwc/GTK availability skips. Nothing was filtered from discovery. Image/VM/publish jobs were intentionally excluded by checks-only mode. Hosted Mod build/reproducibility and Repo privacy checks also passed on the source commit.
- Fabric screenshot [0095_56-taskbar-hover.png](screenshots/0095_56-taskbar-hover.png) shows the hover border/name with the selected stone slot unchanged. [56-session-hover.png](screenshots/56-session-hover.png) shows the small focused app and normal arrow on the hovered slot. Both were visually inspected. Earlier packages' pictures were restored and their newly generated pictures removed; only package 56 evidence is included.
- Fresh independent review is **SAFE**, including the lost-release and reconnect fixes: [REVIEW.md](REVIEW.md). Exact development commands/results, including failed iterations and explicitly filtered diagnostic runs, are in [commands.txt](verification/commands.txt). Earlier complete passes preceded the startup fix and are development evidence only.
- `bash -n mod/dev/client-test.sh`, `python3 -m py_compile reviews/56-free-pointer/rig/pointer.py`, `git diff --check`, and the repository's home-path privacy check: exit 0. No `--force` or Gradle `--stop` was used; no exit-75 refusal occurred. All ordinary-preview scopes were stopped and no Java process from this worktree remains. Other builders' processes were left alone.
- Closing `.work/` inventory: **99 MB total; no file over 500 MB**, no large downloads or extracted images. The remaining files are ignored diagnostic logs, preview fixtures and small testing tools.

## Not verified

- The owner's physical mouse, actual Chrome/Terminal windows, external monitor and installed hub-try binary were not exercised. All windows and input belonged to private headless compositors; the owner's Minecraft folders and session were untouched.
- The owner still needs to judge the flight pace.

## JUDGMENT-CALL

- “Click” means the primary button, as on a regular desktop. Secondary/middle clicks enter the world without using an item; no context menu was added. Opening on every button was rejected because it changes ordinary secondary-button use. This is one input predicate to change later.
- Desktop activation is deferred for two client frames to let an accompanying mouse-down choose an app or the world first. Immediate capture was rejected because the compositor activates the desktop before delivering that click. This is local input timing, with no save-format change.

## PLAN-GAP

- The brief's ordinary small-app path did not cover focus before hello, the common/client initializer order, or frames during reconnect app listing. The original fake-helper setup subscribed earlier than production. The tests now deliberately reproduce production's ordering, and the helper needed a small protocol-compatible change as well as the mod change.
- AGENTS.md requires two complete build/client runs although the brief lists one client run. The final pair is on the complete startup fix; earlier passes are not substituted for it.

## Known limits

- Startup with an app already focused needs **both the helper and mod from this PR**. An older helper sends later transitions but cannot supply the missing initial state. No helper was installed on the owner's system; the preview used the checkout helper.
- A failed taskbar launch leaves the normal pointer available; another world click captures it. Failure uses the same persistent chat message as item use.
- The helper remains the authority on focus. Without it the new pointer rules stop and the existing vanilla input behavior applies.
- Native window verification uses `--session`; ordinary cage runs cover game callbacks and flight but cannot establish the native small-window behavior.

## Open questions

- Does the owner prefer another `DESKTOP_FLYING_SPEED` after trying Live and Build?
