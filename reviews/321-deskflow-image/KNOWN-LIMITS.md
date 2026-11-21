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
