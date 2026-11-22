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

- **Flathub's Deskflow shares the native ID.** The portal sees `org.deskflow.deskflow` for both. A caller
  with that ID can request capture once the owner has turned sharing On. The lead accepted the collision
  on 2026-11-21 because sharing starts Off and the matching Flathub entry is the same application.
- **The trusted-peer list depends on enrolment.** The image launch refuses multiple fingerprints and forces
  TLS and peer checking in the running server's profile. The owner must compare the single fingerprint with
  the one displayed on the Mac. Edits to the original profile or its trust list take effect on the next
  guarded Deskflow launch.
- **Rust dependency notices are pending.** The backend's own MIT license ships. The exact notice and license
  texts for its linked Rust crates still need to be collected and reviewed before publication.
