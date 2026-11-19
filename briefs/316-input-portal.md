# 316: Deskflow (b), an InputCapture and Clipboard portal backend for labwc

**Status:** brief written Thursday 2026-11-19 by `linux-desktop`. Builders: one Fable agent per step (it sees every keystroke: security-sensitive, per the owner's model rule). Reviews: a fresh Fable reviewer, then a Codex cross-review (if OpenAI's filter stops Codex, as it did for 311d, a fresh Claude Opus reviewer instead).

## Why

Patrik uses Deskflow every day and wants it on AresOS with a shared clipboard (board #366: the clipboard is "very helpful"; Lan Mouse never worked well for him). The laptop under AresOS is the Deskflow **server**: its mouse and keyboard move over to the Mac. Deskflow as a server on Wayland needs two portals, InputCapture and Clipboard, and labwc has neither. This package builds the backend that provides them. Package 311 (labwc's pointer lock on layer-shell surfaces) is the compositor fix it needs; the image integration is package (c), after this one.

## What it is

[niri-input-portal](https://github.com/Qingswe/niri-input-portal) (MIT, one author, about 4,000 lines of Rust) does this for the niri compositor, and its README describes how: a one-pixel transparent `wlr-layer-shell` surface on each screen edge the client asks for. When the pointer crosses it, the backend locks the pointer (`zwp_locked_pointer_v1`), switches the surface to exclusive keyboard interactivity, hides the cursor, and forwards relative motion, buttons, scroll and keys to the client over EIS (libei). The clipboard goes through `ext-data-control-v1` as file descriptors, never copied through the process.

Its only niri-specific part is `src/niri.rs`, which runs `niri msg --json outputs` to learn the screens. labwc 0.9.6 on the laptop already offers every protocol the rest uses (checked with `wayland-info` on 2026-11-19): `zwlr_layer_shell_v1` 4, `zwp_pointer_constraints_v1`, `zwp_relative_pointer_manager_v1`, `ext_data_control_manager_v1`, and `zwlr_output_manager_v1` 4. The image's xdg-desktop-portal is 1.22.1, new enough for clipboard on an InputCapture session (1.21.1 and later).

## Where

- Branch `pkg/316-input-portal`, worktree `~/AresOS-316-input-portal`, draft PR into `main`. Never merge or push to `main`.
- The source goes into `os/input-portal/`, following `os/labwc/` from package 311 (on branch `pkg/311-labwc-pointer-lock`, PR #119).
- Progress: `reviews/316-input-portal/PROGRESS.md`.

## What to build

1. **Vendor the source, pinned.** Copy upstream at commit `49f82a63ca53b0137ad4eea08f4cd9d72642a22b` (2026-10-21) into `os/input-portal/` in one commit that changes nothing, with its `LICENSE` and `Cargo.lock`. Add `os/input-portal/UPSTREAM.md`: the URL, the commit, the date, and a list of our changes with the commit that made each. Our changes go in later commits, so `git diff <vendor commit>` shows exactly what we changed.
2. **Screens from labwc.** Replace `src/niri.rs` with a module that reads the screens from `zwlr_output_manager_v1`: enabled heads only, position, the current mode's size, scale and transform, giving the same logical zones (`Zone`, `OutputZone`) the rest of the code expects. Keep upstream's stable order (by x, y, name). Plugging or unplugging a screen must update the zones (the manager's `done` event), as niri's re-query did. Remove every call to `niri`.
3. **Names.** It is ours on labwc, so it loses "niri": binary `/usr/libexec/aresos-input-portal`, D-Bus name `org.freedesktop.impl.portal.desktop.aresos-input`, portal file `aresos-input.portal` (`UseIn=labwc`), unit `aresos-input-portal.service`, idle variable `ARESOS_INPUT_PORTAL_IDLE_TIMEOUT`. Provide the data files in `os/input-portal/data/`. Installing them is package (c)'s.
4. **Who may capture.** Upstream accepts every request. Ours refuses sandboxed apps: a session whose `app_id` is a Flatpak or Snap id is refused unless it is on a short allow-list (empty today; package (c) adds Deskflow's id if it installs Deskflow as a Flatpak). Host apps (the `app_id` xdg-desktop-portal gives a program that isn't sandboxed) are allowed, because a host program of the same user is already inside the trust boundary. Find out what `app_id` xdg-desktop-portal 1.22.1 actually passes for a host program and for a Flatpak, and write the rule against that, with tests.
5. **Who may call it.** The `org.freedesktop.impl.portal.*` methods answer only the current owner of `org.freedesktop.portal.Desktop` (the xdg-desktop-portal frontend); any other caller gets an error. The control commands (`--release`, `--disarm`, `--status`) stay open to the user's own session bus, since they only end a capture or report state. The clipboard commands (`--clip-read`, `--clip-claim`, `--clip-status`) are for diagnosis: keep them only if they add nothing a same-user program can't already do with `wl-paste`/`wl-copy`, and say so in `UPSTREAM.md`.
6. **Nothing secret in logs.** No key codes, key names, typed text, motion values or clipboard contents at any log level. Sizes and counts are fine (upstream logs the keymap's size). Check every `tracing` call in the vendored code.
7. **The way out.** Keep upstream's escapes: the `--release` and `--disarm` commands, the 15-second idle watchdog, release when the EIS connection dies, release when the output disappears or the lock is dropped. Package (c) adds a labwc key for `--release`: Super+Shift+Escape (free in `os/config/usr/share/aresos/labwc/rc.xml`; Super+Ctrl+Escape is the recovery terminal, and Super alone is reserved for the search over the world). Prove here that a labwc keybind still runs while the backend's layer surface holds the exclusive keyboard grab (test 4 below). If it doesn't, stop and report: (c) can't ship without a working way out.
8. **Build.** In a Rust container pinned by digest (`podman`), `cargo fetch --locked`, then `cargo build --release --locked --offline` and `cargo test --locked --offline`. Write the build as a script in `os/input-portal/` that package (c)'s image stage can call. Check `Cargo.lock` against the RustSec advisory database (`cargo audit` in the same container) and list what it finds. Don't add crates unless the output-manager module needs one; `wayland-protocols-wlr` (already a dependency of `smithay-client-toolkit`) has the output-manager bindings.

## Tests

- **Unit (`cargo test`):** zones from output-manager heads (scale, the transforms that swap width and height, a disabled head skipped, two screens side by side and stacked, stable order); the sandbox rule; the caller check.
- **Headless labwc:** run package 311's patched labwc (the local podman image `localhost/aresos-labwc:311e`, or 311's stage) headless with two outputs (`WLR_BACKENDS=headless`, `WLR_HEADLESS_OUTPUTS=2`), a private D-Bus session bus, and the backend. Drive the backend's D-Bus interface as the frontend would (CreateSession2, GetZones, SetPointerBarriers, Enable) with a small test client, and receive events through EIS (a small `reis` receiver or libei's `ei-debug-events`). Move the pointer with `zwlr_virtual_pointer_manager_v1` and type with `zwp_virtual_keyboard_manager_v1` (both offered by labwc). Show:
  1. GetZones matches the two outputs' layout (as `wlr-randr` reports it).
  2. Crossing a barrier locks the pointer and sends `Activated`; motion, a button, scroll and a key arrive over EIS; nothing reaches a local window behind it while captured.
  3. Release, `--release`, `--disarm`, killing the process, and the idle watchdog each end the capture, and the pointer moves locally again.
  4. A labwc keybind (in the test's own `rc.xml`, running `aresos-input-portal --release`) ends a capture while the keyboard grab is active.
  5. Clipboard: text copied with `wl-copy` is offered to the session (`SelectionOwnerChanged` with its MIME types) and read through it; a write through the session lands on the selection.
  6. A sandboxed `app_id` is refused; a call from a bus name that isn't the frontend is refused.
- Running Deskflow itself, the real portal frontend's routing, the image build and the laptop are package (c)'s.

Run nothing on Patrik's real session: no install to `/usr`, no change to `~/.config/xdg-desktop-portal/`, and never `XDG_DESKTOP_PORTAL_DIR` (upstream's README explains how it breaks screen sharing). Run nothing with `sudo`.

## Steps

One fresh agent per step. Each step commits, pushes, and keeps `PROGRESS.md` up to date (done, left in order, what the code doesn't show). Stop after your step.

1. Vendor (one commit), names, the screens module, the sandbox rule, the caller check, the log scrub, the build script, unit tests, `cargo audit`. Open the draft PR.
2. The headless labwc harness and tests 1 to 6. Fix what they find.
3. Only if step 2 ran out of room: the rest of step 2. The last step writes the report into `PROGRESS.md`'s final section (agents can't create `REPORT.md`; the lead commits it), and lists what package (c) must do.

## The bar

Safe the way a good command-line tool or MCP is, not every edge case (decision 24, `docs/design/CONTROL.md`, "The bar"). Fix real harm: keystrokes or clipboard reaching a program that shouldn't get them, keys or clipboard text in a log, a capture with no way out, a change to the running system. Low-harm edge cases go into `reviews/316-input-portal/KNOWN-LIMITS.md` with the reason, not into another fix round.

## Not in this package

The image's build stage, `portals.conf` routing, the D-Bus and unit files in the image, the Super+Shift+Escape key, Deskflow itself, the VM test, and the laptop test are package (c). Its notes so far: route both `InputCapture` and `Clipboard` to `aresos-input` (routing only InputCapture makes Deskflow loop on new sessions, per upstream's README); the Mac's Deskflow client points at 192.168.178.22 (the Windows side) and must point at the laptop under AresOS, 192.168.178.30; the real-laptop test checks where the cursor lands after returning from the Mac, with and without the external monitor.

## Read first

`CLAUDE.md`, `AGENTS.md`, upstream's `README.md` (in the vendored copy), `os/labwc/` and `reviews/311-labwc-pointer-lock/` on 311's branch for how a vendored build is pinned and checked, and `docs/design/CONTROL.md` "The bar".
