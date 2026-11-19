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

## Screens and barriers

- **A barrier that partly faces another screen is refused whole**, not cut down to its free part. With the laptop
  panel under a wider monitor, the monitor's bottom edge can't be a barrier at all, though part of it is free.
  Cutting it would need two surfaces for one barrier.
- **A head counts only with a current mode and a `wl_output` of the same name.** A head the compositor describes
  without a current mode is no zone. Not checked in step 2: whether labwc gives an output without a mode list
  (a headless one) a current mode. If it doesn't, step 3's harness sees no zones, and `src/wayland/heads.rs`
  needs the size from somewhere else.
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
