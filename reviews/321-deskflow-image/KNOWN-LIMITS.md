# 321 Deskflow in the image: known limits

What the backend and the image do not do, with the reason. The bar is the brief's ("The bar"): fix real harm
(keystrokes or clipboard reaching a program that shouldn't get them, keys in a log, a capture with no way out,
sharing that can't be turned off, a change to the owner's session outside the image); list the rest.

`reviews/316-input-portal/KNOWN-LIMITS.md` stays. A limit this package closes or changes is moved here, and the
entry there is the record of how it was.

## Closed in step 1 (316's limits)

- **A key typed in the instant another session takes over** (REVIEW-3, finding 1). Closed: the EIS connection
  writes input only between `StartEmulating` and `StopEmulating`, so a key the Wayland thread handles after the
  portal stopped the run is dropped (`src/eis_server.rs`, `input_allowed`).
- **The end of the Wayland connection doesn't stop the backend** (REVIEW-2, finding 2). Closed: it now ends as a
  lost bus does (below, "Capture").
- **The new owner of the frontend's name can briefly use the old owner's sessions** (REVIEW-3, finding 2; REVIEW-2,
  finding 3). Closed for the case the reviews describe: every method's caller check makes the caller the sessions'
  frontend and closes an earlier owner's sessions first, and the name watch closes only the sessions of the owner
  its notice names. What is left is below, "Trust".
- **A session made at a path that was just closed can lose its D-Bus object** (REVIEW-2, finding 4). Closed: the
  object is removed only when no session with that path exists again, under one lock with the export.
- **Ending a session's clipboard claim can erase a newer local copy** (REVIEW-3, finding 3). Closed: the release
  destroys the portal's own source and no longer unsets the seat's selection.

## Trust

- **A call that races a second handoff of the frontend's name can close the newest owner's sessions.** The caller
  check asks the bus who owns `org.freedesktop.portal.Desktop`, then takes the state lock. If the name changes
  hands in between and the new owner has already made sessions, the late caller's check closes them as an earlier
  owner's. That is a lost session (Deskflow connects again), never input or clipboard reaching anyone: the late
  caller is the frontend the backend trusted a moment earlier, and the sessions it reaches are closed, not used.
  The real frontend owns its name for the whole login. Not fixed: low harm.

## Capture

- **The end of the bus or of the Wayland connection stops the backend.** Either way every session is closed, the
  capture is released and the process exits with an error naming which one ended; the next call from a frontend
  starts it again through D-Bus activation. Without its Wayland connection no barrier can be placed, and the
  compositor has already dropped the grab with the connection.
- **No idle watchdog by default** (brief 321, "The trust model"). Upstream ended a capture after 15 seconds
  without input; the owner reads on the Mac for longer than that, and control would come back to the laptop
  unseen, with his next keys in a local window. A capture now ends by the release chord, `--release`, the client's
  own `Release`, its EIS connection or session ending, the frontend or bus going, or a change of screens.
  `ARESOS_INPUT_PORTAL_IDLE_TIMEOUT` still sets a watchdog (316's harness uses 3 seconds).

## The sharing switch (step 1b)

- **A clipboard pipe handed out before Off** (the lead, 2026-11-21; brief 321, "The trust model"). Its ends are held
  outside the backend (`src/portal.rs`, `src/wayland/clipboard.rs`), so it can still finish carrying the one item the
  owner's session asked for while sharing was on. No new transfer starts after Off (every clipboard call reads the
  switch, and `SelectionRead` reads it again after its wait, before the pipe goes out) and Deskflow's session is
  closed, so nothing further leaves; a revocable relay in both directions would be a new design for that one item.
- **Off and on again inside one reread goes unseen.** Without `--revoke` the backend reads the switch every 250 ms
  while a session exists (and at every check point). If the switch goes off and is back on before the next read,
  nothing is closed. The file says on by then, and only the owner's password turns it on. The switch's own program
  runs `--revoke` after `off`, which makes the read immediate.
- **A compositor slower than a second to confirm loses the session.** After Off, and for `ForceRelease`, the backend
  waits one second for labwc's answer to a `wl_display.sync`. A labwc that is busy for longer looks like a stopped
  one: after Off the backend exits, and `--release` kills it. Either way the grab goes with the connection and the
  next Deskflow session starts a fresh backend; nothing reaches the Mac that shouldn't.
- **`--release` signals only `/usr/libexec/aresos-input-portal` of the same user.** A backend run from another path,
  or whose binary was replaced under it (the kernel then names it `... (deleted)`), is refused rather than killed. On
  the image `/usr` is read-only and changes only at a reboot, and the backend is always started from that path.
- **A stopped session bus stops `--release` too.** It finds the backend through the bus (the name's owner, its
  credentials, the question), so with the bus daemon stopped it waits and kills nothing: there is no pidfd to kill
  through without the bus naming the process. Nothing else on the session works then either; the recovery is a VT
  switch or SSH, and `kill` by hand.

## Shortcuts during a capture (step 1c)

- **A labwc without the second patch would still capture, with its bindings live.** The gate is in labwc alone
  (`os/labwc/0002-no-bindings-for-the-capture-layer.patch`): it knows the capture surface by its layer namespace,
  and the backend asks for nothing and so cannot tell whether the gate is there. What stands in for that: the labwc
  stage, the image check and every harness run compare both binaries' loaded-image and normalized SHA-256 pins
  with the lock; the harness runs the gate on those binaries (test10); and a unit test holds the namespace in the
  patch and the one in `src/wayland/state.rs` together
  (`os/tests/test_labwc_stage.py`). The other mechanism (keyboard-shortcuts-inhibit, with `Activated` only after
  labwc's `active`) would refuse to capture instead; why it was not picked is in `PROGRESS.md`, step 1c.
- **Any program that may use layer-shell can claim the namespace.** An overlay surface named `aresos-input-barrier`
  that holds the keyboard exclusively switches labwc's unmarked bindings off for as long as it has it. Such a
  surface already gets every key that is not a binding; what it gains is that Alt+F4, Alt+Tab and the media keys
  come to it too. Super+Shift+Escape, Super+Ctrl+Escape (the recovery terminal) and the VT switch still work, and
  a sandboxed program gets no layer-shell from labwc at all. The same would hold for the inhibitor mechanism (any
  exclusive layer surface could ask). Checking the peer's executable is a possible later hardening.
- **A session lock taken during a capture.** The image has no screen locker. Revisit when one is added.
- **A window with `ToggleKeybinds` on could veto the two marked chords.** Nothing in the image binds
  `ToggleKeybinds`.
- **A crossing already sent when the switcher or a menu opens.** There is a window of milliseconds between
  the pointer's enter and the backend's commit, and the result is a raised laptop window or a menu row. No new
  crossing starts in those modes.
- **A pointer-only capture forwards no keys.** Laptop shortcuts acting on the laptop is right there. Deskflow's
  sessions ask for the keyboard, and those end on keyboard leave (316).
- **An input-method grab.** No input-method program runs in the session. Modifier state reaching unfocused
  clients leaks which modifiers are held. Revisit if an input method is ever started.
- **Touch and tablet-pen taps still run labwc's mouse bindings during a capture** (focus and raise for the window
  tapped; the keyboard stays with the capture surface). The patch gates keyboard and mouse bindings, which is what
  the backend forwards. The laptop has no touchscreen and no pen, and a tap on the laptop's own screen is not
  input meant for the Mac.
- **A binding's key held when the capture starts never reaches the Mac.** Its press was labwc's (the binding ran
  before the capture), so labwc keeps the release too and runs neither a release action nor repeats. The Mac sees
  neither event, so nothing sticks there.
- **No custom display mode while the backend runs** (step 2's DRM gate, runs 45001307065 and 45004171828).
  The VM verified the initial `wlr-randr --custom-mode` and off operations. Re-enabling the output in that mode
  made labwc abort in wlroots' `wlr_output_management_v1.c` (`head_send_state`) with the backend or the listen-only
  client bound to `zwlr_output_manager_v1`. Listed modes, off and on, hotplug and VT switches all keep labwc
  running. A custom mode requires a manual command. The brief's alternative (the backend reads screens from
  `wl_output` and `xdg-output` and never binds the protocol) removes the backend's share of it; the compositor's
  fault for other clients is to be reported upstream (an outward step, for the owner's OK).

## Deskflow in the image (step 3)

- **The input portal's bus side can run while sharing is Off** (changed by the step 3 review fixes, finding 1).
  The bundled polkit agent requests the desktop portal at login (run 45009968432), and the frontend activates the
  backend while it initializes Clipboard and InputCapture. That bus side answers discovery and refuses capture
  sessions. An authorized request while sharing is On starts the only Wayland worker in the process. Off or the
  last session closing starts teardown and exits the process. D-Bus can then activate a fresh backend, which
  answers discovery while Off without reaching Wayland. The custom-mode compositor limit above applies during
  worker startup, live sessions and the short teardown. Harness test8 checks the exit and fresh activation from
  outside. The final hosted result is in `PROGRESS.md` under “CI dispatches”.
- **Flathub's Deskflow shares the native ID.** The portal sees `org.deskflow.deskflow` for both. A caller
  with that ID can request capture once the owner has turned sharing On. The lead accepted the collision
  on 2026-11-21 because sharing starts Off and the matching Flathub entry is the same application.
- **Pairing rests on the owner's comparison** (step 3 review fixes, finding 3). With no saved Mac, or with
  `aresos-deskflow --enroll`, the guarded launcher shows each TLS peer's fingerprint and saves only one the owner
  confirms; a stranger on the network that connects during pairing gets its own dialog with another fingerprint,
  and Enter selects rejection. The owner still has to compare the fingerprints before selecting “It matches.”
  The brief's laptop test 3 is exactly this comparison. The launcher
  refuses a saved list with more than one or a malformed entry and points to `--enroll`. Edits to the original
  profile or its trust list take effect on the next guarded launch. With sharing On and the old server stopped,
  `/usr/libexec/aresos-deskflow-login --enroll` opens the guarded pairing path in the correct scope. The hub
  starts pairing by itself when no Mac is saved.
- **Deskflow's own window, run by hand, keeps its own settings.** The desktop ID's one entry in the image opens
  the guarded launcher (finding 2), so the hub, a desktop launcher or `gtk-launch` all get it. `deskflow` typed
  in a terminal still opens the stock window with the user's TLS settings; its core then has the terminal's scope,
  so its ID is empty and the backend refuses it (VM gate, "terminal launch refused"). A per-user entry in
  `~/.local/share/applications` could point the ID elsewhere: a program of the same user, as 316's limit says.
- **Manually replacing Deskflow can restore Fedora's desktop entry.** If the owner runs `dnf reinstall` or
  `rpm-ostree override replace` for Deskflow, the replacement transaction can restore `Exec=deskflow` under the
  allow-listed desktop ID. The image build excludes that entry from each locked RPM install and ships the
  guarded entry. Ordinary image updates repeat the exclusion.
- **Rust dependency notices are pending.** The backend's own MIT license ships. The exact notice and license
  texts for its linked Rust crates still need to be collected and reviewed before publication.

## Login, release and logging (step 4)

- The autostart hook runs once at login. After switching On during a running login, open Deskflow from the
  hub. After switching Off, the guarded core exits. The launcher serializes launches, so stop the existing
  server before replacing a paired Mac.
- Deskflow's saved screen layout still needs the configured Mac's exact screen name. Trusting a certificate
  authorizes the peer. The layout controls where a crossing can go.
- Forced release with sharing On sends key-up events for previously forwarded keys before StopEmulating.
  Off closes the forwarding gate and tears down the session. A prior network delivery is already outside the
  backend, and client behavior after losing the connection is Deskflow's.
- The guarded launcher uses Deskflow's ordinary Info level unless the owner raises it in the saved
  profile. It removes coordinates from the pinned RPM's crossing and disconnect messages and relays logs
  through one stream. Higher Deskflow levels can include keys, buttons and other positions. The guarded
  profile disables Deskflow's direct log file option so it cannot bypass coordinate filtering.
- An error in the login hook leaves Deskflow stopped and shows no message. This includes the hub's
  catalogue scan taking more than two seconds. Open Deskflow from the hub to start it manually.
- When Deskflow is opened while sharing is Off, the core has about five seconds to ask the portal before
  the launcher stops it. A slower core leaves no sharing window.
- **Turn on** in the sharing window enables sharing. Deskflow still needs to be opened from the hub, and
  the window gives no reminder.
- A session requested while the backend is exiting after its last session may receive a sharing-Off
  refusal and open the sharing window even while sharing is On. Open Deskflow again.
- Forced release sends key-up events. A mouse button held at the chord can stay held on the Mac until
  Deskflow leaves the screen.
- While captured, the microphone-mute key does nothing on either computer. labwc leaves it to the capture,
  and Deskflow 1.27 maps `XF86AudioMicMute` (`0x1008ffb2`) to zero in `XDGKeyUtil::s_map1008FF` when converting
  EIS keys. The next ordinary key still goes to the client. Release the capture to mute the laptop microphone.
- While sharing is On and no Mac is paired, each login starts the pairing server. Anyone who can reach
  the port can open a fingerprint dialog. The dialog defaults to rejection.
- A program running as the same user can delete the once-per-login marker and open the sharing window again.
- After Off closes a live session, Deskflow can retry once before it exits. In a fresh login this refusal can
  open the once-per-login sharing dialog and take focus. The keyboard and pointer are local and sharing is Off.
- If the launcher exits unexpectedly, its lock is released while the Deskflow core may still be running.
  A subsequent launch can then start a second core.
- Hosted dispatch 14 passed the full daily-use gate and both reboot checks. The physical display, keyboard
  and Mac rehearsal remains for the owner. See `PROGRESS.md` under “CI dispatches” and “Laptop test for the owner”.
- **The emergency release trusts a record the owner's own programs can change.** When `--release` has to kill a
  frozen backend, it first stops the guarded Deskflow launcher and core named in a record in the private runtime
  folder. A program running as the owner could replace or remove that record, so the kill would aim at another of
  the owner's processes or leave the core to re-arm. Such a program can already kill the owner's processes or change
  labwc's settings itself; sandboxed programs cannot reach the folder; PID reuse is caught by start-time checks and
  pidfds. Later hardening: a launch supervisor that holds the pair's pidfds (final recheck, REVIEW-4-RECHECK.md).
