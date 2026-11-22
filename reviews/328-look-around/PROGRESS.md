# Package 328: progress

Brief: [briefs/328-look-around.md](../../briefs/328-look-around.md). One fresh agent per step; this file carries what the
code doesn't show. The last step turns it into the report text.

## 328a second review fix stopped at step 1

**The lead ruled on 2026-11-22 at 08:12** that F2 applies to capture bookkeeping only. The unfocused cursor-image update is harmless because XFixes shows the cursor right after it. Resume design A at step 2 and stop at step 3 if either race control fails to reproduce stale capture.

**Status remains NOT SAFE.** The step 1 source check in [Analysis 1](ANALYSIS-1.md#26-order-of-work-for-the-builder)
failed on F2. The release path still has the risk described in [Recheck 1](RECHECK-1.md).

- Minecraft 26.2's Loom metadata names `org.lwjgl:lwjgl-glfw:3.4.1:natives-linux`. `sha1sum` of the cached JAR
  matched the metadata (`23cdf7655ce9f3b27ad90f08e73345e0d5b46362`). `unzip -p` extracted the x64 `libglfw.so` and
  its source revision (`9352d8fe93cd443be18157abe81f16500549aec03`). A display-free Python `ctypes` probe printed
  `glfwGetVersion: 3.5.0` and `glfwGetVersionString: 3.5.0 Wayland X11 GLX Null EGL OSMesa monotonic shared`.
- **F2 fails as written in both the bundled revision and the 3.5.1 tag.** `glfwSetInputMode` does return early for
  an unchanged mode. On a changed mode it queries cursor position before calling `_glfwSetCursorModeX11`. The
  backend gates grabs, raw motion and changes to `disabledCursorWindow` on X focus. It always calls
  `updateCursorImage` and `XFlush` after that check. Switching to NORMAL with `disabledCursorWindow` already
  cleared still sends `XDefineCursor` or `XUndefineCursor`, even when unfocused. The narrower claim about capture
  bookkeeping holds in the source.
  [Bundled `glfwSetInputMode`](https://github.com/glfw/glfw/blob/9352d8fe93cd443be18157abe81f16500549aec03/src/input.c#L589-L621),
  [bundled cursor-mode setter](https://github.com/glfw/glfw/blob/9352d8fe93cd443be18157abe81f16500549aec03/src/x11_window.c#L2888-L2925),
  [bundled cursor-image update](https://github.com/glfw/glfw/blob/9352d8fe93cd443be18157abe81f16500549aec03/src/x11_window.c#L455-L475),
  [3.5.1 cursor-mode setter](https://github.com/glfw/glfw/blob/3.5.1/src/x11_window.c#L2888-L2925).
- **F1, F3, F4 and F5 match by inspection.** A normal FocusOut in DISABLED calls `enableCursor`, which disables raw
  motion when enabled, clears the disabled-cursor window, and ungrabs. FocusIn in NORMAL restores the input context
  and calls the callback. The event pump drains the Xlib queue in order and only re-centres while the disabled-cursor
  window is set. FocusOut iconification requires a GLFW monitor and auto-iconify. The session starts windowed, blocks
  F11 and disables auto-iconify.
  [Focus events](https://github.com/glfw/glfw/blob/9352d8fe93cd443be18157abe81f16500549aec03/src/x11_window.c#L1743-L1787),
  [cursor enable](https://github.com/glfw/glfw/blob/9352d8fe93cd443be18157abe81f16500549aec03/src/x11_window.c#L541-L554),
  [event pump](https://github.com/glfw/glfw/blob/9352d8fe93cd443be18157abe81f16500549aec03/src/x11_window.c#L2808-L2840).

Design A would queue every covered release as `letGo`, put a FocusOut at the head of Xlib's queue at the next
`RenderSystem.pollEvents`, and let GLFW clear its capture. The mod would then set NORMAL, show its XFixes-hidden
cursor and cancel `Window.onFocus`. If Minecraft still recorded focus, a queued FocusIn would restore GLFW's input
context and would also be cancelled before reaching Minecraft. The lead chose to include vanilla captures within
`HomeScreen.session()` and omit deferred recapture.

The stop rule ended the work before the call-site check, both GLFW control runs, the lever trials, the 75 in-game
race cycles and the release-cause checks. Neither full headless pass ran. There were no generated screenshots and
no files over 500 MB in `.work/`. Section 2.8's one-poll delay, same-frame refusal, held-key and Escape behavior,
pointer placement, stalled-helper behavior, vanilla fallbacks and 64-bit Linux event layout remain design notes.
Dead-key restoration also remains unverified. No mod or rig files changed in this round.

## 328b: prototype A, "click to look"

**Done** (branch `pkg/328b-click-to-look`). The product keeps classic as the default.

- **The setting:** `mod/src/main/java/dev/aresos/config/LookMode.java` reads one line in `config/aresos/settings.properties`
  in the game's config folder: `look = click`. No file, no line or an empty value means `classic`. An unknown value
  (also `edge`, until 328c adds it) logs a warning and stays classic. The game reads the file once at start. 328d
  documents the line in `mod/README.md`; for `hub-try` the folder is the try checkout's `mod/run/config/aresos/`.
- **The rules without the game:** `mod/src/main/java/dev/aresos/focus/ClickLook.java` holds the stillness timer, the short
  grace for a click that arrives before GLFW's focus, when the pointer is free, and which key starts look mode.
- **The glue:** `mod/src/client/java/dev/aresos/client/ClickToLook.java`, with small hooks in `HomeScreen`
  (`freePointer`, `frame`), `HomePointer.enterWorld`, `WorldCapture.returnToCentre`, `MouseAppInputMixin` (motion,
  buttons and the wheel count as activity) and `KeyboardAppInputMixin` (movement-key start).
- **Tests:** `ClickLookTest` and `LookModeTest` (unit), and `ClickToLookClientGameTest`, last in the client suite.

**The tunables**, each one named constant in `ClickLook`:

| Constant | Value | What it does |
| --- | --- | --- |
| `LOOK_RELEASE_MS` | 800 | Look mode ends after the mouse and every movement key have been still this long. |
| `START_GRACE_MS` | 250 | A click on the world that reaches the game before GLFW's focus still starts look mode if the focus follows within this time. |

**What the code doesn't show:**

- **Look mode is the capture itself.** In the click setting, "looking" means `MouseHandler.mouseGrabbed`. No second
  state can drift from it. A capture that look mode did not start is let go at the next frame. That is vanilla's grab
  when the loading screen closes, before the desktop world is active (the first client run caught it), and it goes
  through 328a's release like any other.
- **One gate refuses every other grab.** Outside look mode `HomeScreen.freePointer` is true, as it is behind an app in
  package 56. The existing head of `grabMouse` then refuses vanilla's grab when a screen closes, the helper's regrab,
  GLFW's focus regrab and `AresOsClient.regainedFocus`. Only `ClickToLook.start` gets through: it clears the free state
  for its own call, and 328a's `WorldCapture.allowed` (the safe fallback) still decides. Capture and release stay 328a's.
  The mod adds no GLFW cursor call and no second release path. `returnToCentre` only changes the point that
  `WorldCapture.finish` restores.
- **Package 56 decides the press.** Because the pointer is free, `HomePointer.button` handles a press first: a primary
  click on an app slot opens the app. Anything else (open world, an empty slot, a right click) starts look mode. The
  press and its release are swallowed, so the starting click never attacks, uses or breaks.
- **Activations without a click don't start look mode.** Alt+Tab, Super, an app closing or the helper's
  `desktop_activated` set the world in front and leave the cursor free. Only a press (`enterWorld(client, true)`) or a
  movement key starts it.
- **Held mouse buttons count as activity,** as do motion and the wheel. Holding attack to break a block doesn't end look
  mode halfway. The brief says "the mouse ... still"; this reads a held button as a mouse in use. It's a judgment call
  for the report.
- **A key start** happens at the first press of walk, jump or fly up, or sneak or fly down (not repeats). The key still
  walks. The capture keeps 328a's rule: with the pointer on another output or an app, keys walk but nothing captures.
- **Not tried:** the owner's real mouse and monitor, Chrome and the installed helper. The feel of 800 ms is his to
  judge in `hub-try`.

**Known limits (328b):**

- With toggle sneak on, a toggled sneak counts as held and look mode lasts until Esc or an app takes the focus.
- Without libXfixes, or off X11, the release is vanilla's: the cursor reappears at the window's centre, not at the click.
- A click start that the safe fallback refuses (the pointer is not over the world's visible part) does nothing, and
  the next click tries again.
- While the free pointer rests on the world, Minecraft still selects hotbar slots with the wheel (vanilla's scroll
  needs no capture). That is the same as behind an app in package 56.

**Left:** 328c (prototype B, edge turning; add `EDGE` to `LookMode`), then 328d (the README line, `run-hub.sh --outputs 2`,
the report and the PR).

## Done

### 328a design A after the lead ruling

- The **step 2 call-site check** scanned every class in both Loom-remapped Minecraft 26.2 JARs for `grabOrReleaseMouse`. Only
  `InputConstants.class` and `MouseHandler.class` contain the name. Java 25 `javap -p -c` found calls only in
  `MouseHandler.grabMouse` and `releaseMouse`. Both already pass through the mod.
- For **step 3**, Java 25 compiled the rig's `GlfwProbe.java` against the cached LWJGL 3.4.1 JARs. The probe ran under
  `rig.sh` and `in-rig.sh` with the shared client-test lock. In both controls, moving the virtual pointer to
  90,70 and 140,110 returned 640,360 in cursor mode `34001`. `state.sh` printed
  `X pointer grab: held by another client` for both controls before any lever trial. The control with an intervening
  poll logged both the real FocusOut and the pointer FocusIn before `normal`.

| GLFW release | Sequence after capture | Observation |
| --- | --- | --- |
| Control, focus left unseen | `away;normal` | Both moves snapped to the centre. Grab held. |
| Control, real events handled | `away`, poll, `normal` | Both moves snapped to the centre. Grab held. |
| Lever, focused | `lever` | Both requested positions held. Grab free. |
| Lever, focus left unseen | `away;lever` | Both requested positions held. Grab free. |
| Lever, real events handled | `away`, poll, `lever` | Both requested positions held. Grab free. |
| Lever, focus moves inside the callback | `lever away`, `lever root`, `away;lever back` on fresh captures | Both positions held in all three trials. Grab free. |
| Lever from stale mode | `lever` after each control | Both requested positions held. Grab free. |

**Design implemented.** The existing capture still hides through XFixes before Minecraft moves the cursor. A covered
release records `letGo`. Before the next event poll, the mod puts a FocusOut at the head of GLFW's Xlib queue.
GLFW releases its capture, and the mod's focus hook sets NORMAL, restores the pointer position where possible, and
pairs its XFixes hide with a show. The hook also queues a FocusIn if Minecraft still records focus. Minecraft
does not receive either of these two events. This covers vanilla captures inside `HomeScreen.session()` and
refuses capture while a release is pending. There is no deferred recapture.

The early focused client runs exposed a test harness dependency. A queue trace showed the correct FocusOut at
the head and a native GLFW focus callback, but Fabric's test mixin cancelled `Window.onFocus` first, leaving
the mod's hook uncalled. The native 328a fixture enables the actual focus callback for its own run. The other
client tests keep Fabric's focus suppression. This required no adjustment to the release code from Design A.
The probe checks run before the cleanup instrument moves or grabs the pointer.

**Minecraft race matrix.** The focused `mod/dev/client-test.sh --session` run with a local Gradle init script
selecting only `WorldKeepsPointerClientGameTest` ended with `BUILD SUCCESSFUL in 2m 1s` after the fixture
adjustment below. Each cell ran the five focus moves `away`, `root`, `back`, `away,back` and `back,away`.

| Focus at release | `asked` | `queued` | `normal` | `show` | `polled` |
| --- | --- | --- | --- | --- | --- |
| Focused | 5 | 5 | 5 | 5 | 5 |
| Away, real events queued | 5 | 5 | 5 | 5 | 5 |
| Away, real FocusOut and pointer FocusIn handled | 5 | 5 | 5 | 5 | 5 |

All 75 cycles settled in NORMAL with the XFixes cursor shown and the X grab free. The pointer stayed at both
test positions and the next real click recaptured. Capture was refused during the pending release. Escape,
helper background, helper SIGKILL and world exit each released with a focus move before NORMAL. World exit
started with a vanilla capture in the session after helper death and ended on the title screen. The game log
contained no `did not hand back` line. The captured click and scroll reached Minecraft, and camera motion turned
46.836567 degrees with probe counters steady at `[1, 0, 2, 0]`.

The first full client attempt exited 1 after 14m 54s. In `AWAY_QUEUED / polled / back`, the first position
check read 427,240 after the release had settled and the X grab check had passed. That is the centre of the
Fabric fixture's virtual screen, which Minecraft uses for its capture warp. labwc can already be at the
capture's starting point, so asking it for that same position need not send Xwayland a motion. The rig now moves
to a distinct point before 90,70 and 140,110, confirms delivery of each move, and still checks that both positions
hold through three ticks. It probes the X grab after the motion checks.

The next full pair passed its first session in 15m 41s. The second session exited 1 after the pointer failed
to enter the Wayland probe following the second Escape case. The test now uses `rig/xside.py`, an inert X11
window on the second output. The second X11 surface lets Xwayland observe motion outside the game even when
the eventual destination is a native Wayland window. The test confirms that Minecraft has keyboard focus,
GLFW sees the X pointer outside the game, and the Wayland probe sees the pointer inside it before closing the
menu. For the matrix, the same surface keeps the pointer outside the game during focus restoration so
HomeScreen's ordinary focus-return capture does not interfere with the release measurements.
The last four client entrypoints also passed in suite order with a local init script
(`BUILD SUCCESSFUL in 3m 35s`). Both focused runs passed the 75 cycles and all four release causes.

**Full verification on `edff64d5`.** Both builds ran 339 unit test cases with 333 passing and six Windows-only
skips. Each printed `All 106 required tests passed :)`. Both sessions ran all 30 client entrypoints with headless
labwc, two outputs and the NVIDIA renderer. Each passed all 75 race cycles, all four release causes, and the
next-click recapture check. Both game logs were free of `did not hand back`.

| Pass | Command | Result |
| --- | --- | --- |
| 1 | `mod/dev/build.sh --rerun-tasks` | `BUILD SUCCESSFUL in 2m 46s`, exit 0 |
| 1 | `mod/dev/client-test.sh --session` | `BUILD SUCCESSFUL in 15m 51s`, exit 0 after 15m 52s |
| 2 | `mod/dev/build.sh --rerun-tasks` | `BUILD SUCCESSFUL in 2m 51s`, exit 0 |
| 2 | `mod/dev/client-test.sh --session` | `BUILD SUCCESSFUL in 15m 56s`, exit 0 after 15m 57s |

Each command started with at least 6 GiB available and no other worktree's Gradle build running. The second
client run waited about 32 minutes for those conditions. The four verification commands needed no exit-75 retries.
`git checkout -- reviews/` restored 65 tracked screenshots, and cleanup removed 35 generated untracked screenshots.
There were no files over 500 MB in `.work/`. The source check under the lead's F2 ruling and the failing standalone
controls both cleared the stop rule.

**Known limits.** GLFW releases held keys and buttons on the injected FocusOut. A still-held movement key needs
a fresh press after the menu closes. In the standalone rig, holding Esc for 1.5 seconds across the previous
focused release sequence produced one press, repeats, and a release. Across the lever it produced a synthetic
release and an extra press on the first repeat. The cursor can remain hidden until the next poll, and a capture
in that interval waits for a new click. With X focus on another window, the pointer reappears where labwc left
it. A live helper that stops sending focus events can leave the hide in place until the normal frame check
detects the loss. The native release uses the 64-bit Linux X event layout. Systems without X11 or libXfixes
and games outside an AresOS session use the vanilla cursor path. Dead-key restoration and the owner's hardware
and live session remain unverified.

### 328a: the world keeps the pointer (step 1 of 4)

- **The cause is proven** in the native development client, with real capture, in the isolated rig (below).
- **The fix is in the mod** (`WorldCapture`, `PointerRules.mayCapture`, hooks in `MouseAppInputMixin`, `ShellFocusClient`,
  `HomePointer`, `HomeScreen`). No `os/` change is needed.
- **Tests:** a unit test for the rule; `WorldKeepsPointerClientGameTest`, last in the suite, with real capture, the
  rig's probe app and virtual pointer under `client-test.sh --session`.
- **The session preview has two outputs:** `client-test.sh --session` now runs labwc with two 1280x720 outputs side by
  side, the game on the left one, and exports `ARESOS_POINTER_LAYOUT=2560x720`; package 56's `pointer.py` maps its
  absolute moves onto that layout (it assumed one 1280x720 output).
- **Finding 5 is answered** below. Nothing changed for it.
- **Review 1 fixes:** native capture is scoped to a connected desktop world. The helper's disconnect releases any
  capture the mod owns, including held input, and cleanup can complete after the connected-world gate closes.
  A release from a GLFW callback waits for Minecraft's event pump. The synthetic FocusOut re-checks real X focus
  before Minecraft stores the result. The headless regression checks all three paths and verifies delivery of the
  captured click and scroll to Minecraft.

## Left, in order

1. **328c:** prototype B, "edge turning" (`look = edge`).
2. **328d:** the README line for the `look` setting, `run-hub.sh --outputs 2`, the report and the PR.

328b is done (above).

## The proven cause of the click leak (owner's finding 4)

**In one sentence:** when the world takes the mouse, Minecraft and GLFW warp the X pointer to the window's centre while
the cursor is still visible; Xwayland answers each warp with a pointer lock whose position hint is that centre and
drops it at once; labwc moves its real cursor to the hint of every active lock that is dropped; so the hidden cursor
ends at the world window's centre, over the app standing there, and the next click or scroll goes to that app.

The steps, each observed in the rig:

1. `MouseHandler.grabMouse` (Minecraft 26.2) calls `InputConstants.grabOrReleaseMouse(window, DISABLED, centre)`, which
   is `glfwSetCursorPos(centre)` and then `glfwSetInputMode(GLFW_CURSOR_DISABLED)`. The first call warps the X pointer
   while the cursor is still visible.
2. GLFW 3.5 (LWJGL 3.4.1) on X11 then warps to the centre once more, grabs the pointer confined to the window
   (`XGrabPointer` without checking the result), and only then defines its hidden cursor.
3. Xwayland emulates each X warp with `zwp_pointer_constraints_v1.lock_pointer` plus
   `set_cursor_position_hint(centre)`, and destroys the lock right away while the cursor is visible. The game's trace
   (`WAYLAND_DEBUG=client` on the rig's Xwayland) shows, inside the click that enters the world:
   `lock_pointer` + hint 640,360 + `destroy`, again `lock_pointer` + hint + `destroy`, `confine_pointer` + `destroy`,
   and the final `lock_pointer`, which labwc grants (`locked`).
4. labwc moves its cursor to the position hint when an active lock is destroyed; a lock that is held does not move it.
   `rig/locker.py` shows this without Xwayland or the game: a plain Wayland window with the pointer at 100,100 locks
   with a hint at its centre and drops the lock; the next click, with no motion at all, lands in the probe at 640,360
   and activates it. With the lock held instead, the click stays in the window.
5. The final lock keeps pointer focus on the game, so relative motion still turns the camera. But labwc picks the
   window under its cursor for a button press: the probe (Chrome in the owner's case) gets the focus and the click,
   and a scroll too.

**Reproduced with the real game** (`rig/trial.py click`): the probe in front, a click on the world beside it at 100,100,
then 40 small moves: the camera turned on 81% of the picture and the probe got no motion, yet the next click and
scroll went to the probe and it took the focus. With no motion at all (`MOVES=0`) the same happened: the capture alone
puts the cursor at the centre.

**Reproduced without the game** (`rig/xmimic.py` with `ORDER=prewarp,centre,grab,hide`, GLFW 3.5's order as the
trace shows it): the same lock/destroy sequence and the same leak, with no motion. Hiding the cursor before the warps
stops it only if Xwayland takes the cursor for hidden: GLFW's own hidden cursor, a transparent Xcursor ARGB image
(`rig/argbcursor.py` makes the same one), does not count, and hiding it first still leaked
(`ARGB_CURSOR=… ORDER=here,ungrab,hide,prewarp,centre,grab,hide`). With `XFixesHideCursor` first
(`ORDER=here,ungrab,xfhide,hide,prewarp,centre,grab,hide`), Xwayland keeps its first lock, labwc never moves the
cursor, and neither the click nor the scroll reaches the probe. (A core pixmap cursor with an empty mask also counts as
hidden, which first misled the stand-in.)

**A second GLFW gap: an app's click leaves GLFW capturing.** When an app takes the focus with a click while the world
holds the pointer, X takes the focus away from the game (GLFW lets go) and then hands it a pointer focus (GLFW captures
again). The mod's release comes after that, without the X focus, and GLFW 3.5 skips it: it keeps its X grab and keeps
warping the pointer to the window's centre after every move over the world. The rig showed an X pointer grab still
held with the game's cursor normal, and Xwayland lock/confine pairs at every move. Once the world is clicked again,
labwc follows one of those warps before the capture starts, and the capture then holds the cursor at the centre: the
same leak on the second try. `rig/GlfwProbe.java` (GLFW 3.5 alone, the game's own LWJGL, no Minecraft) reproduces all
of it: the capture's lock churn, the focus-out and focus-in on the app's click, the skipped release and the
re-centring.

**Two more ways in, found with the stand-in** (`xmimic.py keyboard` and `over`): if the capture starts while another
window has labwc's keyboard focus, labwc never grants the lock and the pointer moves freely over the apps; if it starts
while the pointer rests on another window, Xwayland asks only for `confine_pointer`, which keeps the pointer inside the
world's rectangle but not off the windows above it. Both leaked motion, clicks and scrolls to the probe. The safe
fallback closes them: the world takes the mouse only with the compositor's focus and the pointer on its window.

**Not the cause:** the mod's own capture order. A diagnostic run showed one capture per click: the helper's
`desktop_activated` arrives, then the press reaches `HomePointer.button`, which calls `grabMouse` once, while the
button is down. The X-level GLFW sequence alone produces the lock churn.

## The fix

- **Hidden first** (`WorldCapture.grab`, wrapping Minecraft's call in `MouseHandler.grabMouse`): in the AresOS session
  the mod calls `XFixesHideCursor` on the game's window, on GLFW's own X connection (LWJGL's `JNI` and
  `GLFWNativeX11`), before Minecraft's capture runs. Every warp is then made with a cursor X does not draw: Xwayland
  keeps its first lock and labwc never moves the cursor. Without `libXfixes` or off X11 the capture stays Minecraft's
  own (logged once).
- **A clean release** (`WorldCapture.release`): XFixes ownership is independent of the helper's state. When the helper
  disconnects, the client releases the mouse and clears held input. Releases requested during callbacks, or after X
  focus has moved, wait for Minecraft's normal event pump. If X focus is still away before that poll, the mod
  queues a FocusOut for the game's X window so GLFW can clear its internal capture. The window callback sets the
  cursor mode to normal before a later FocusIn can re-grab it, then reads the actual X focus so a synthetic
  FocusOut cannot overwrite a real FocusIn.
  Once the poll returns, the mod asks GLFW to restore the pointer, ungrabs it and pairs its XFixes hide with a
  show. A focused release outside the event pump can finish immediately. New captures wait until cleanup completes.
- **The safe fallback** (`PointerRules.mayCapture`, checked at the head of `grabMouse`): in a session's connected
  desktop world the world takes the mouse only when the compositor has given it the focus (the helper's `shell_focus`,
  or a press that reached the world: labwc focuses a window before it hands it the press) and GLFW says the pointer is
  over its window (`GLFW_HOVERED`: under Xwayland true only over the world's visible part, false over an app and on
  the other output, checked in the rig). Otherwise the capture is refused and the pointer stays a normal pointer; keys
  still walk if the world has the keyboard; a click on the world captures. This covers every capture path: vanilla's
  click and screen close, the helper's return, the GLFW focus regrab and `HomePointer`.
- **Released means released:** every release of the capture in a desktop world clears held keys (attack, use,
  movement) and the app-use state. Vanilla does it for screens; helper focus changes and GLFW focus loss did it
  already.

## Finding 5: does a click on the world hide a part-screen app?

**The helper's covered-minimize cannot fire for a part-screen window.** `Helper.uncover()`
(`os/config/usr/libexec/aresos-shell`) minimizes only `Windows.covering(known_screen=True)`: windows that are ready,
not the desktop's own, not a cover or the laptop home, not minimized, and **maximized or fullscreen** (labwc's
foreign-toplevel state), and on an output the world's window is on. It runs only when the world becomes the active
window after another window was (a click, Alt+Tab, a return): not at start-up, not for the restored desktop's
focus bounce, not during Super's own activation. A part-screen window is neither maximized nor fullscreen, so it is
never in that list.

**labwc does not raise the world over it either.** In the rig, with the image's `rc.xml`, the checkout's helper and the
native client: a click on the world beside the part-screen probe activated the world, the probe stayed drawn above it
(checked on the screenshot), and the helper logged no minimize. `ToggleAlwaysOnBottom` holds for the game's window.
The same rig with the probe maximized: when the world then got the focus, the helper logged "the desktop got the
focus; minimized 1 window(s) that covered it" and the probe was minimized, exactly the condition above.

**So what the owner saw is not reproduced in the rig,** and the difference must be on his laptop. The likeliest: his
Chrome window was maximized or fullscreen in labwc's state while it looked part-screen to him; the helper then
minimizes it by design (package 40). Two checks there tell it: the helper's journal line "the desktop got the focus;
minimized 1 window(s) that covered it" at the moment the window disappeared, and the window's foreign-toplevel state
(`reviews/40-real-home/rig/tl.py`-style listing: `maximized` or `fullscreen` on Chrome). If neither shows, the world's
window was not the always-on-bottom one at the time (its rule applies once, when the window first maps). The click
leak does not explain it: a click that lands in Chrome brings Chrome forward. `linux-desktop` and the hub act on this
answer; the owner's decision stands (the world stays below, a part-screen app stays visible).

## Running the game natively on Wayland (out of scope)

It would remove this cause: GLFW's Wayland backend locks the pointer directly through `zwp_pointer_constraints_v1`
and has no warps, so there is no lock churn and no hint to warp to. The safe fallback would still matter (labwc
grants a lock only to the focused window). It would also change: GLFW's focus would be the true focus (package 40's
"GLFW says focused behind an app" quirk goes away, and the code built around it would need a second look); no window
position (`glfwGetWindowPos` is unsupported, which package 56's test coordinates use); EGL instead of GLX for the
NVIDIA offload; Minecraft 26.2 itself asks GLFW for X11, so it needs a launch option or a mixin, untested here.

## Known limits (328a)

- **When an app takes the focus while the world steers,** the pointer reappears at the centre of the world's window:
  labwc ends the lock at its last hint, which GLFW's re-centring keeps at the centre. It is visible and over the app that
  now has the focus, so nothing leaks; it is just not where the hand left it.
- **The safe fallback changes one thing in classic mode:** when the world gets the focus without a click (Alt+Tab,
  Super, an app closing, the first join) while the pointer rests on an app or the other output, the world no longer
  takes the mouse; keys still walk, and the next click on the world takes it. Today it captured at once (and leaked).
- **Review finding 4:** the traces support the centre-warp diagnosis, and the rig covers classic capture under steady
  focus and focus returns with the pointer over another window or output.
- **Review finding 5:** without `libXfixes`, on a non-X11 backend, or with no X display, the native path is skipped.
  The missing-library fallback uses vanilla X11 release, where the stale-grab behavior is still possible. A server
  without cursor hiding can silently omit the XFixes request. XFlush does not acknowledge it, and a rejected X
  request can reach Xlib's fatal default handler.
- **Review finding 6:** the native test now checks Minecraft's captured left press and hotbar scroll as well as camera
  motion, probe exclusion and helper loss. World exit while captured has no dedicated native check. The pointer layout
  retains the one-output default outside the two-output session. The duplicate World Search test registration was
  removed in `2a817d4b`, before the review-fix passes below.
- **Review finding 7:** covered-minimize requires a ready, non-minimized, maximized or fullscreen app on a known
  desktop output. The rig confirmed that the desktop stays below a part-screen window. Why Chrome disappeared on
  the owner's laptop remains undetermined.
- **Not tried:** the owner's real mouse, Chrome itself, the real monitor, Prism's game and the installed helper. The rig
  used the native development client, the checkout's helper, an inert Wayland test app and virtual input on a
  headless labwc.

## Notes for 328b to 328d

- **Every capture goes through `MouseHandler.grabMouse`, so through `WorldCapture.grab` and the safe fallback**; look mode
  should start captures there too, never with its own GLFW calls. A refused capture leaves `mouseGrabbed` false.
- **The pointer already reappears where the capture began** (`WorldCapture.release` warps back to `startX/startY`). For a
  key start, 328b can set that point to the centre of the world's output before capturing.
- **`client-test.sh --session` has two outputs side by side** (`HEADLESS-1` at 0,0 with the game, `HEADLESS-2` at 1280,0,
  1280x720 each; `ARESOS_POINTER_LAYOUT=2560x720`). `WorldKeepsPointerClientGameTest.Rig` shows how a client test gets
  real capture (`WorldCapture.forTests(null, true)`), native mouse callbacks, the probe and the virtual pointer.
- **Under Xwayland, GLFW's focus is not the compositor's:** X focus is PointerRoot while a Wayland app has the focus, so
  the game gets pointer focus-ins whenever the pointer crosses the world (package 40's "GLFW says focused behind an
  app"). The helper's focus is the one to trust.

## The rig (reviews/328-look-around/rig)

Everything is headless and private: never the owner's `wayland-0` or `:0`, never his session's helper or D-Bus.

- `rig.sh <run folder>`: a private headless labwc (`WLR_HEADLESS_OUTPUTS=2`, the image's `rc.xml`, no autostart) on a
  private D-Bus (`dbus-run-session`), in a systemd scope `pkg328-rig-*`. `inner.sh` arranges the outputs side by side
  (1280x720 each), starts the virtual input and writes `<run folder>/env`. `TRACE=1` turns on Xwayland's
  `WAYLAND_DEBUG` into `labwc.log`.
- `in-rig.sh <run folder> <name> <command...>`: runs a command against the rig's displays and D-Bus only, in a scope
  `pkg328-<name>-*`. `stop.sh` stops every `pkg328-*` scope.
- `probe.py <run folder>`: the inert test app, a 640x400 magenta window (labwc centres it over the world's centre); it
  counts pointer and keyboard events into `probe.json`.
- `vinput.py <run folder> [command]`: a virtual pointer and keyboard (`abs`, `rel`, `click`, `button`, `scroll`, `key`).
- `game.sh`: the native client (`runClient`) through `mod/dev/run-hub.sh` with the checkout's own helper under a
  wrapper (an empty home folder, a registry with only the probe), holding the client-test lock and waiting for 6 GB
  and no other worktree's Gradle. The save is `mod/run/saves/AresHub` of this worktree. `super.sh` sends Super
  (SIGUSR1) to that helper only.
- `open-home.sh <run folder>`: after `game.sh`, opens AresHub from the title screen and puts the probe back.
- `trial.py <run folder> click|alttab|super|menu`: the leak scenarios against the running game (capture is read from
  Xwayland's trace: a lock labwc granted and still holds); `xmimic.py`, `argbcursor.py`, `locker.py` and
  `GlfwProbe.java`: the stand-ins above; `state.sh`: windows, probe counts, X pointer, whether an X grab is held.

Typical run: `TRACE=1 rig.sh .work/328/r1 &`, then `in-rig.sh .work/328/r1 game rig/game.sh &` and
`open-home.sh .work/328/r1`, then `trial.py`. The very first start of a fresh `mod/run` shows Minecraft's accessibility
screen: click Continue (`vinput.py <run folder> abs 638 671` and `click left`). `GlfwProbe.java` runs with
`java -cp <lwjgl, lwjgl-glfw and their natives-linux jars from ~/.gradle> GlfwProbe.java` through `in-rig.sh`, reading
commands on stdin (a FIFO kept open).

## Test results

**Native client in the rig, after the fix** (`traces/after-fix-trials.txt`; before the fix:
`traces/before-fix-capture-trace.txt`):

- The owner's scenario (`trial.py click`), four runs: each time the world captured, 40 moves across the probe turned the
  camera (32% to 89% of the picture changed), and the probe counted no enter, motion, click or scroll. Before the fix
  the same scenario leaked the click and the scroll every time, also with no motion at all.
- Alt+Tab's result and Super with the pointer resting on the probe, two and one runs: the world got the focus but not
  the mouse; the pointer stayed a normal pointer and reached the probe; a click on the world then captured.
- The menu (Esc) closed with the pointer on the probe: no capture; a later click on the world captured, and its scroll
  went to the world.
- After an app took the focus while the world steered, moving over the world gave no Xwayland lock at all (before: one
  lock with the centre hint per move), and no X pointer grab was left.
- One timing seen in the diagnostics: when the press reaches Minecraft before GLFW has seen the focus, Minecraft's own
  check skips the capture at the press; the helper's `desktop_activated`, a few milliseconds later, captures. Both
  paths were clean.

**Builds**, on commit `2b1b3a7f` (only docs changed after it, `[skip ci]`), through the dev scripts with no `--force`, no exit-75
refusal and no other worktree's Gradle running at the start:

- Pass 1: `mod/dev/build.sh` BUILD SUCCESSFUL in 2m 42s: 335 unit tests, 0 failures, 6 Windows-only skips; all 106
  server game tests passed. `mod/dev/client-test.sh --session` (two outputs) BUILD SUCCESSFUL in 14m 1s, exit 0: the
  whole client suite, package 56's native checks included, and `WorldKeepsPointerClientGameTest` ("328a native capture:
  probe [1, 0, 2, 0] -> [1, 0, 2, 0], camera turned 46.8 degrees"; "328a world-keeps-pointer checks passed").
- Pass 2: `mod/dev/build.sh` BUILD SUCCESSFUL in 1m 50s with the same counts. `mod/dev/client-test.sh --session`
  BUILD SUCCESSFUL in 13m 52s, exit 0, the same tests and the same two 328a lines.
- Before these, two full client runs failed at the new test's last check (the XFixes hide/show pairing above, found
  by the full suite; alone the test passed) and were fixed before the passes counted. The tracked screenshots the runs
  rewrote were put back, and the ones written under new numbers removed.

## Review 1 fix verification

Both builds ran 339 unit test cases with 333 passing and six Windows-only skips, and all 106 required server game
tests passed. Both client runs used the full 30-entry suite with headless labwc, two outputs and the NVIDIA renderer.
Every run started with at least 6 GiB available and no other Gradle build. No run needed an exit-75 retry.

| Pass | Command | Result |
| --- | --- | --- |
| 1 | `mod/dev/build.sh` | BUILD SUCCESSFUL in 2m 56s |
| 1 | `mod/dev/client-test.sh --session` | BUILD SUCCESSFUL in 14m 15s, exit 0 after 14 min 17 s |
| 2 | `mod/dev/build.sh --rerun-tasks` | BUILD SUCCESSFUL in 2m 46s |
| 2 | `mod/dev/client-test.sh --session` | BUILD SUCCESSFUL in 14m 17s, exit 0 after 14 min 18 s |

The native regression checked the following in both client passes.

- While the camera turned 46.8 degrees, Minecraft registered the captured left press and changed the selected
  hotbar slot when scrolled. The probe counters stayed at [1, 0, 2, 0].
- A virtual Escape arrived through GLFW and Minecraft's keyboard callback. The test changed real X focus just
  before Minecraft handled the key. The menu opened inline and the native release finished after the callback.
- The test restored real X focus immediately before the mod queued the synthetic FocusOut. Minecraft still recorded
  the window as focused, and clicking exposed world captured again.
- SIGKILL of the separate fake helper process closed the real Unix socket. The game stayed focused without a menu
  while its cursor returned to the starting position. XFixes confirmed the hide was gone, another X client could
  grab the pointer, and the pointer reached the probe. The held movement key was cleared.

An initial build flagged an unavailable LWJGL JNI overload in the test fixture. After correcting it, a focused
`mod/dev/client-test.sh --session` run using a temporary Gradle init script passed the 328a test before the two
full client runs. Tracked review screenshots were restored and only newly generated untracked screenshots were
removed. No files larger than 500 MB remained in `.work/`.
