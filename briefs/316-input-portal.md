# 316: Deskflow (b), an InputCapture and Clipboard portal backend for labwc

**Status:** brief written Thursday 2026-11-19 by `linux-desktop`. Reviewed by Codex (gpt-6.2-sol high, `reviews/316-input-portal/BRIEF-REVIEW.md`: CHANGES-NEEDED with four blocking findings, all folded in below), then a targeted Codex recheck of those four. Builders: one Fable agent per step (it sees every keystroke: security-sensitive, per the owner's model rule; OpenAI's filter also stopped a Codex run on 311d). Reviews: a fresh Fable reviewer, then a Codex cross-review (if OpenAI's filter stops Codex, a fresh Claude Opus reviewer instead).

## Why

Patrik uses Deskflow every day and wants it on AresOS with a shared clipboard (board #366: the clipboard is "very helpful"; Lan Mouse never worked well for him). The laptop under AresOS is the Deskflow **server**: its mouse and keyboard move over to the Mac. Deskflow as a server on Wayland needs two portals, InputCapture and Clipboard, and labwc has neither. This package builds the backend that provides them. Package 311 (labwc's pointer lock on layer-shell surfaces) is the compositor fix it needs; the image integration is package (c), after this one.

## What it is

[niri-input-portal](https://github.com/Qingswe/niri-input-portal) (MIT, one author, about 4,000 lines of Rust) does this for the niri compositor; its README describes how. On each screen edge the client asks for, it places a transparent `wlr-layer-shell` surface on the overlay layer: the armed input strip is one logical pixel, and the surface extends further (64 logical pixels) for the release hint. When the pointer crosses, the backend locks the pointer (`zwp_locked_pointer_v1`), switches the surface to exclusive keyboard interactivity, hides the cursor, and forwards relative motion, buttons, scroll and keys to the client over EIS (libei). The clipboard goes through `ext-data-control-v1`; on the portal path it moves as file descriptors.

Its niri-specific part is `src/niri.rs`, which runs `niri msg --json outputs` to learn the screens. labwc 0.9.6 on the laptop offers every protocol the rest uses (checked with `wayland-info` on 2026-11-19): `zwlr_layer_shell_v1` 4, `zwp_pointer_constraints_v1`, `zwp_relative_pointer_manager_v1`, `ext_data_control_manager_v1`, and `zwlr_output_manager_v1` 4. The image's xdg-desktop-portal is 1.22.1, new enough for clipboard on an InputCapture session (1.21.1 and later). The harness re-checks this list in its own labwc.

## Where

- Branch `pkg/316-input-portal`, worktree `~/AresOS-316-input-portal`, draft PR into `main`. Never merge or push to `main`.
- The source: `os/input-portal/` (following `os/labwc/` from package 311).
- The headless harness and its evidence: `os/input-portal/harness/` (scripts and test clients) and `reviews/316-input-portal/evidence/` (logs and results).
- Progress: `reviews/316-input-portal/PROGRESS.md`.

## The trust model

The backend may hand Patrik's keystrokes and clipboard to one program only: the Deskflow that package (c) installs, after he has turned sharing on. Everything below serves that.

- **Who may start a capture.** xdg-desktop-portal passes the backend only an `app_id` string, and that string can't prove where an app came from: a host app can get an empty ID or an ordinary desktop ID, and a Flatpak's ID lives in the same namespace. So the rule is an **exact allow-list, default deny**: the backend reads the allowed IDs from one root-owned file in the image (`/usr/share/aresos/input-portal/allowed-apps`, one ID per line; the package ships it empty), and refuses every session whose `app_id` isn't on it, including the empty ID. Package (c) installs Deskflow natively, proves through the real frontend which `app_id` that Deskflow gets when AresOS starts it, and puts exactly that ID in the file. A Flatpak Deskflow stays out until its identity is tested. What remains (another program of the same user faking that exact identity) is a known limit, with the reason.
- **Who may call it.** Every `org.freedesktop.impl.portal.*` method, on InputCapture, Clipboard and the session objects (including `Close`), answers only the current owner of `org.freedesktop.portal.Desktop` on its bus. Any other caller gets an error and nothing else, and above all no file descriptor.
- **One session at a time.** Only one session may be enabled (armed) at once; enabling a second one disarms the first and tells its client. Each barrier belongs to the session that set it, and an activation goes only to that session. EIS devices get only the capabilities the session was granted, whatever the receiver asks to bind. A clipboard transfer (read or write file descriptor) goes only to the session that owns the selection or asked for it, and its serial is checked against that session.
- **Teardown.** When a session closes, the frontend leaves the bus, or the session's EIS connection dies (before or during a capture), the backend ends any capture, removes that session's barriers and drops its clipboard claim. A dead session can never take the pointer again: the next crossing stays local.
- **The way out.** Upstream's escapes stay: the `--release` and `--disarm` commands (open to the user's own session bus, since they only end a capture or report state), `--status`, the 15-second idle watchdog, and release when the output disappears or the lock is dropped. Package (c) binds Super+Shift+Escape to `--release` (free in `os/config/usr/share/aresos/labwc/rc.xml`; Super+Ctrl+Escape is the recovery terminal, and Super alone is reserved for the search over the world). This package proves that exact chord works while the backend holds the exclusive keyboard grab. If it doesn't, stop and report: (c) can't ship without a working way out.
- **Nothing secret leaves.** Remove the clipboard diagnostic commands (`--clip-read`, `--clip-claim`, `--clip-status`) and their D-Bus methods: they read the whole clipboard into the daemon and print it. Tests use the guarded portal path instead. No key codes, key names, typed text, cursor coordinates or hints, motion values or clipboard contents in any log or error at any level, including formatted errors and dependencies' tracing. Sizes and counts are fine.
- **Turning it on and off** is package (c)'s: what Patrik does to enable sharing and to revoke it. This package makes sure the allow-list and the session rules above can't be bypassed in the meantime.

## What to build

1. **Vendor the source, pinned.** Copy upstream at commit `49f82a63ca53b0137ad4eea08f4cd9d72642a22b` (2026-10-20 UTC) into `os/input-portal/` in one commit that changes nothing, with its `LICENSE` and `Cargo.lock`. Add `os/input-portal/UPSTREAM.md`: the URL, the commit, the date, and a list of our changes with the commit that made each. Our changes go in later commits, so `git diff <vendor commit>` shows exactly what we changed. Delete upstream's `install.sh` and `uninstall.sh` in the first change commit (they use `sudo` and restart the user's portal); never run them.
2. **Screens from labwc, one snapshot.** Replace `src/niri.rs` with a module that reads the screens from `zwlr_output_manager_v1`: enabled heads, position, current mode, scale and transform. Upstream has two layout sources (the portal's on-demand query and the Wayland side's own logical layout for barrier placement); make them one committed snapshot that the zones, the barrier surfaces and the EIS device regions all use, with the heads matched to `wl_output` names. Logical sizes must match labwc's own at fractional scale. When a screen is plugged in, unplugged or changed, the snapshot changes: send `ZonesChanged`, reject barriers against the old zone set, remove stale surfaces, and give EIS the new geometry. Remove every call to `niri`.
3. **The trust model above:** allow-list, caller check, one armed session, capability and clipboard binding, teardown, log scrub, diagnostics removed.
4. **Names.** Binary `/usr/libexec/aresos-input-portal`, D-Bus name `org.freedesktop.impl.portal.desktop.aresos-input`, idle variable `ARESOS_INPUT_PORTAL_IDLE_TIMEOUT`. Data files in `os/input-portal/data/`: the D-Bus activation service and the systemd user unit `aresos-input-portal.service`, and the portal file `aresos-input.portal`. AresOS's session sets `XDG_CURRENT_DESKTOP=AresOS` and runs its own `dbus-run-session` (`os/config/usr/bin/aresos-session`), so the portal file says `UseIn=AresOS`, and (c) routes explicitly in an `AresOS-portals.conf`. Installing them is (c)'s.
5. **Build script.** `os/input-portal/build.sh <source dir> <output dir>`: runs inside a Rust container pinned by digest, `cargo fetch --locked`, then `cargo build --release --locked --offline` and `cargo test --locked --offline`, and writes the binary and the data files to the output dir. (c)'s image stage calls it as is. Check `Cargo.lock` with `cargo audit` in a pinned container; record the advisory database's commit and list what it finds. Add no crates unless the output-manager module needs one (`wayland-protocols-wlr`, already pulled in by `smithay-client-toolkit`, has the bindings).

## Tests

- **Unit (`cargo test`):** zones from output-manager heads (scale, fractional scale, transforms that swap width and height, a disabled head, side by side and stacked, stable order); the allow-list (listed, unlisted, empty ID, missing file = deny); the caller check on every method; one armed session; capability intersection; clipboard serial binding.
- **Headless harness: isolation first.** Everything runs in a disposable rootless podman container: a scratch `HOME`, `XDG_RUNTIME_DIR` and config; no host Wayland, X11, D-Bus or input devices mounted; no activation-environment updates; every client pointed at the container's own private bus and labwc socket, checked before the first test. Each command has a timeout, and cleanup touches only the harness's own processes. Nothing runs on Patrik's session: no install to `/usr`, no change to `~/.config/xdg-desktop-portal/`, never `XDG_DESKTOP_PORTAL_DIR`, nothing with `sudo`.
- **The compositor:** package 311's patched labwc, the RPM `labwc-0.9.6-1.fc44.aresos1` built by 311's stage (`os/labwc/stage.py`) from 311's branch at `40e6c248` (or main once 311 has merged; say which you used and the RPM's SHA-256). 311's probe (`reviews/311-labwc-pointer-lock/lock-probe/` on that branch) already installs it in a disposable Fedora container and moves a virtual pointer; extend it. Run labwc headless with two outputs (`WLR_BACKENDS=headless`, `WLR_HEADLESS_OUTPUTS=2`), with a test `rc.xml` that binds Super+Shift+Escape to `aresos-input-portal --release`.
- **The test clients:** one persistent connection owns `org.freedesktop.portal.Desktop` on the private bus and acts as the frontend, in the real order: `CreateSession2`, optionally `RequestClipboard`, `Start`, `ConnectToEIS`, wait for the EIS receiver's devices, then `GetZones`, `SetPointerBarriers`, `Enable`. A second connection makes the calls that must be refused. A small local window (a probe client) records the input it receives. Move the pointer with `zwlr_virtual_pointer_manager_v1` and type with `zwp_virtual_keyboard_manager_v1`.
- **Show:**
  1. GetZones, the barrier surfaces and the EIS regions all match the two outputs (as `wlr-randr` reports them); changing or disabling an output brings `ZonesChanged`, rejects the old zone set, removes stale surfaces, and gives EIS the new geometry.
  2. Crossing a barrier: labwc grants the lock, `Activated` arrives, motion, a button, scroll and a key arrive over EIS, and the local window receives none of them. Before and after the capture, the local window does receive input.
  3. Release, `--release`, `--disarm`, Super+Shift+Escape (the exact chord, pressed through the virtual keyboard while the grab is held), killing the process, and the idle watchdog each end the capture, and the pointer moves locally again.
  4. Teardown: after `Close`, after the frontend connection drops, and after the EIS connection dies (once before a crossing, once during a capture), a new crossing stays local.
  5. Clipboard: text copied with `wl-copy` is offered to the session (`SelectionOwnerChanged` with its MIME types), and a real read through the session's transfer file descriptor gets the text; a write through the session lands on the selection (`wl-paste` shows it).
  6. Refusals: an `app_id` not on the allow-list, the empty ID, a call from a bus name that isn't the frontend, a second session trying to receive the first one's activation or clipboard transfer, and an EIS receiver binding capabilities it wasn't granted: each refused, and no file descriptor handed out.
  7. Logs: a verbose run (`RUST_LOG=trace`) with synthetic keys and a marked clipboard text: no marker, key or coordinate appears in any log or error.
- Running Deskflow itself, the real portal frontend's routing, the image build and the laptop are package (c)'s.

## Steps

One fresh agent per step. Each step commits, pushes, and keeps `PROGRESS.md` up to date (done, left in order, what the code doesn't show). Stop after your step.

1. **Source and toolchain:** vendor (one commit), delete the install scripts, `UPSTREAM.md`, the build script with its pinned container, `cargo audit`, names and data files. The unchanged backend builds. Open the draft PR.
2. **Behaviour:** the screens module with one snapshot, and the whole trust model, with unit tests.
3. **The harness and tests 1 to 7.** Fix what they find, or list it for step 4 if the step runs out of room.
4. **Only if needed:** the rest of step 3. The last step writes the report into `PROGRESS.md`'s final section (agents can't create `REPORT.md`; the lead commits it), with what package (c) must do.

## The bar

Safe the way a good command-line tool or MCP is, not every edge case (decision 24, `docs/design/CONTROL.md`, "The bar"). Fix real harm: keystrokes or clipboard reaching a program or session that shouldn't get them, keys or clipboard text in a log, a capture with no way out, a change to Patrik's running session or system. Low-harm edge cases go into `reviews/316-input-portal/KNOWN-LIMITS.md` with the reason, not into another fix round.

## Not in this package: package (c)'s list

The image's build stage (calling `build.sh`), installing the data files, `AresOS-portals.conf` routing both `InputCapture` and `Clipboard` to `aresos-input` while keeping every other portal's route (upstream's README saw Synergy loop on new sessions when only InputCapture was routed; check Deskflow does the same), Deskflow installed natively and its proven `app_id` in the allow-list, the Super+Shift+Escape key, how Patrik turns sharing on and off, activation and `--release` on the same bus and display as labwc, the VM test, and the laptop test. Its notes so far: the Mac's Deskflow client points at 192.168.178.22 (the Windows side) and must point at the laptop under AresOS (192.168.178.30; confirm both addresses then); the laptop test checks where the cursor lands after returning from the Mac, with and without the external monitor.

## Read first

`CLAUDE.md`, `AGENTS.md`, upstream's `README.md` (in the vendored copy), `os/labwc/` and `reviews/311-labwc-pointer-lock/` (`PROGRESS.md` and `lock-probe/`) on 311's branch, `os/config/usr/bin/aresos-session`, and `docs/design/CONTROL.md` "The bar".
