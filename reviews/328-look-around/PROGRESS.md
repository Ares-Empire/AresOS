# Package 328: progress

Brief: [briefs/328-look-around.md](../../briefs/328-look-around.md). One fresh agent per step; this file carries what the
code doesn't show. The last step turns it into the report text.

## Done

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

## Left, in order

1. **328a:** two full passes of build and client tests (see "Test results"), then this file's results.
2. **328b:** prototype A, "click to look".
3. **328c:** prototype B, "edge turning".
4. **328d:** the `look` setting, `run-hub.sh --outputs 2`, the README line, the report and the PR.

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
- **A clean release** (`WorldCapture.release`): if GLFW really captured and the game no longer has the X focus, the
  release first sends the window a FocusOut event (`XSendEvent`, then `XSync` so the event is queued before the poll)
  and lets GLFW handle it (`glfwPollEvents`): GLFW's own focus-out
  handling lets go of everything, as when the focus leaves for good. Its focus callback (`Window.onFocus`, hooked in
  `WindowHomeScreenMixin`) then turns the cursor mode normal at once, inside that same poll: GLFW's ungrab and warp can
  make X send a pointer focus-in that the poll reads next, and a focus-in in the disabled mode makes GLFW capture
  again (GLFW's `FocusIn` case calls `disableCursor` whenever the mode is disabled; read from GLFW's x11_window.c).
  Then Minecraft's release runs; the X pointer goes
  back to where the capture began while the cursor is still hidden, so Xwayland's last lock is hinted there and labwc
  leaves the pointer in place (this also covers Minecraft letting go and taking the mouse again within one frame, which
  `HomeScreen.frame`'s GLFW focus check did right after a click); the game's X grab is dropped and the cursor shown.
  The pointer reappears where the world was clicked; after an app took the focus it appears at the world window's
  centre, where labwc put it when the lock ended (visible, over the app that has the focus).
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
not the desktop's own, not a cover or the laptop home, **not minimized, maximized or fullscreen** (labwc's
foreign-toplevel state), and on an output the world's window is on. It runs only when the world becomes the active
window after another window was (a click, Alt+Tab, a return): not at start-up, not for the restored desktop's
focus bounce, not during Super's own activation. A part-screen window is neither maximized nor fullscreen, so it is
never in that list.

**labwc does not raise the world over it either.** In the rig, with the image's `rc.xml`, the checkout's helper and the
native client: a click on the world beside the part-screen probe activated the world, the probe stayed drawn above it
(checked on the screenshot), and the helper logged no minimize. `ToggleAlwaysOnBottom` holds for the game's window.
The same rig with the probe maximized: when the world then got the focus, the helper logged "the desktop got the
focus; minimized 1 window(s) that covered it" and the probe was minimized, exactly the condition above.

**So what the owner saw needs one of these, which only his laptop can tell:** his Chrome was maximized or fullscreen
in labwc's state while looking part-screen (then the helper minimizes it, as designed in package 40), or the click
never reached the world: with the leak above, a click "on the world" can land in Chrome instead. The second one ends
with this fix. A check on his laptop: the helper's log line "the desktop got the focus; minimized 1 window(s) that
covered it" at the moment the window disappeared means the first. `linux-desktop` and the hub act on this answer; the
owner's decision stands (the world stays below, a part-screen app stays visible).

## Running the game natively on Wayland (out of scope)

It would remove this cause: GLFW's Wayland backend locks the pointer directly through `zwp_pointer_constraints_v1`
and has no warps, so there is no lock churn and no hint to warp to. The safe fallback would still matter (labwc
grants a lock only to the focused window). It would also change: GLFW's focus would be the true focus (package 40's
"GLFW says focused behind an app" quirk goes away, and the code built around it would need a second look); no window
position (`glfwGetWindowPos` is unsupported, which package 56's test coordinates use); EGL instead of GLX for the
NVIDIA offload; Minecraft 26.2 itself asks GLFW for X11, so it needs a launch option or a mixin, untested here.

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

**Builds** (`mod/dev/build.sh`, `mod/dev/client-test.sh --session`): filled in below as they finish.
