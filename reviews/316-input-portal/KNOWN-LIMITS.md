# 316 input portal: known limits

What the backend does not do, with the reason. The bar is the brief's: fix real harm (input or clipboard reaching
the wrong program, secrets in a log, a capture with no way out, a change to the owner's session); list the rest.

## Trust

- **A program of the same user can pass as the frontend.** The caller check trusts whoever owns
  `org.freedesktop.portal.Desktop` on the session bus. A program running as the user that takes that name (when
  the real frontend isn't running) can call the backend with any `app_id`, the listed one included. The session
  bus has no stronger identity than name ownership, and such a program could already read Deskflow's memory or
  the user's files. This is the brief's stated limit.
- **Properties, introspection and the control interface answer every caller.** `version` and
  `SupportedCapabilities` are constants. `org.aresos.InputPortal.Control` (`--release`, `--disarm`, `--status`)
  is the way out and must work when the frontend doesn't. None of them hands out input, clipboard data or a file
  descriptor. `--status` shows each session's object path, application ID, and whether it is armed or capturing.
- **The allow-list is read when a session is created.** Taking an ID off the list refuses new sessions; a session
  that already exists runs on until it is closed. Revoking is package (c)'s, and closing the sessions is part of
  it.
- **Any started session with clipboard access may read the selection**, armed or not. Every session belongs to a
  listed application, and the fd goes back to the frontend for that session only.
- **The keyboard is grabbed for a pointer-only session too.** The keys go nowhere (the session has no EIS
  keyboard), but they don't reach local windows during the capture either.

- **A program that asks the bus to show it everything still sees the signals.** `Activated`, `Deactivated`,
  `ZonesChanged` and the clipboard signals go to the frontend's own connection and to no subscriber (REVIEW-1,
  finding 4). The session bus lets any program of the user become a monitor (`BecomeMonitor`, or a match rule with
  `eavesdrop`), and a monitor sees every message, the frontend's method calls included. That is the bus's own rule;
  the backend can't change it, and such a program is the user's own.
- **A clipboard read that races the close of its own session can return a pipe for a newer selection** (REVIEW-1,
  finding 6). `SelectionRead` checks the session, asks the Wayland thread for the pipe and returns it without
  checking again. The pipe goes to the frontend that asked, for a session of a listed application that could read
  the clipboard a moment earlier; no other program gets it. Not fixed: low harm.
- **A receiver can get more devices than it bound, inside its grant** (REVIEW-1, finding 9). One that binds only
  relative motion gets the button and scroll interfaces too, and a later, narrower bind keeps the devices it had.
  Nothing outside what `Start` granted is ever offered, so the effect is extra events for a receiver that was
  allowed them anyway.

## Capture

- **A crossing waits up to half a second for the grab.** The client hears `Activated` only once labwc has granted
  the pointer lock and, for a session with the keyboard, given the barrier keyboard focus (REVIEW-1, finding 3).
  If that doesn't come within 500 ms the input goes back to the local screen and what was typed in between is
  dropped. At most 256 events are held back between a crossing and the handover to EIS.
- **Losing keyboard focus ends a capture with the keyboard.** If labwc gives the focus to something else while a
  session with the keyboard is capturing, the capture ends and the client gets `Deactivated`, even though the
  pointer lock is still there: keys must never go to a local window while the client believes it has them.
- **A stop of the bus stops the backend.** When the bus connection ends, every session is closed and the process
  exits with an error (REVIEW-1, finding 2). The next call from a frontend starts it again through D-Bus activation.

- **The chord's modifier keys reach the remote first.** Super and Shift are down before Escape, so the client gets
  those two presses over EIS. labwc takes Escape for its binding and runs `--release`; the two releases reach the
  client or the local window, whichever the timing gives. Whether Deskflow leaves them pressed on the other machine
  is package (c)'s to check.
- **Under labwc two of the losses can't happen on their own** (REVIEW-1, finding 5): labwc keeps the seat's pointer
  whatever devices exist, and closes a layer surface only with its output, which is a change of screens. The code
  reports both; only the portal's side of it is tested.

## Screens and barriers

- **A barrier that partly faces another screen is refused whole**, not cut down to its free part. With the laptop
  panel under a wider monitor, the monitor's bottom edge can't be a barrier at all, though part of it is free.
  Cutting it would need two surfaces for one barrier.
- **With overlapping screens a barrier on an inner edge is accepted** (REVIEW-1, finding 8). The outer-edge check
  finds a neighbour only when its edge touches the barrier's edge exactly. If one screen covers part of another
  (x 0 to 1920 next to x 1600 to 3520), the first one's right edge lies inside the desktop and a barrier there is
  still placed. Screens overlap only in a mirrored or hand-made layout, and Deskflow sets its barriers on the
  outer edges of the whole desktop. Not fixed: low harm.
- **labwc aborts when a headless output is switched off and on again while a client stays connected to
  `zwlr_output_manager_v1`** (wlroots 0.19.3: `head_send_state: Assertion 'found' failed`). The backend is such a
  client; one that only listens does the same, and with nobody connected labwc keeps running
  (`evidence/step3-harness/results.txt`, the control lines). Not known for a real output, which has a list of
  modes where a headless one has none. Package (c) must try it on real outputs before it ships; the fix, if one is
  needed, is in labwc or in how long the backend keeps that protocol open.
- **The EIS region is the size of the screens' bounding box, at (0, 0)** (upstream's). With a layout that doesn't
  start at (0, 0) the region and the zones' coordinates differ by that offset.
- **A head counts only with a current mode and a `wl_output` of the same name.** A head the compositor describes
  without a current mode is no zone. Not checked in step 2: whether labwc gives an output without a mode list
  (a headless one) a current mode. Step 3's harness shows it does: both headless outputs are zones.
- **Logical sizes are computed, not asked for:** mode, transform and scale through wlroots' own arithmetic. The
  protocol carries the scale in 1/256 steps. labwc's scales are set through that same protocol, so they are on
  that grid; a compositor scale off the grid could differ from the computed size by a pixel.
- **A change of screens always ends the capture**, even when the capture's own screen didn't change.
- **New geometry reaches an EIS receiver as new devices** (the old ones are removed): a receiver reads a device's
  region once.

## Logs

- **The libraries' warnings and errors are not audited line by line.** Their output is capped at warnings, their
  wire dumps (`WAYLAND_DEBUG`, `REIS_DEBUG`) are switched off at start, and nothing in their warnings is known to
  carry input. Other variables of other libraries (`XKB_LOG_LEVEL` logs keymap compile problems, not keys) are
  left alone.
- **A library's warning can carry scroll values** (REVIEW-1, finding 7). The libraries log at warnings, and the
  Wayland toolkit's warning for a pointer event that arrives without an entered surface prints the whole event:
  for a scroll, its axis values. It is an error path, and it can carry motion and scroll numbers, never a key or
  clipboard text. Not fixed: low harm.
- **Barrier IDs, serials, activation IDs, session paths, application IDs, bus names and screen geometry are
  logged.** None of them is a key, a cursor position or clipboard content.

## Dependencies

- **`cargo audit` still warns about three unmaintained crates:** `zvariant` 5.13.1 (RUSTSEC-2026-0370),
  `zvariant_derive` 5.13.1 (RUSTSEC-2026-0372) and `zbus_names` 4.3.4 (RUSTSEC-2026-0371). No release fixes them,
  and `zbus` 5.18 depends on all three. No vulnerability is known in them.
- **Yanked crates are not checked** by the pinned audit (it has no network).

## Bounds

16 sessions, 64 barriers per session, 64 clipboard types of at most 255 bytes, 16 parked clipboard transfers.
More is refused (or, for transfers, the oldest is dropped). Deskflow needs one session and four barriers per
screen.
