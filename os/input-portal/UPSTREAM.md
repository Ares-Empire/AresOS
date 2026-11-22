# Where this code comes from

`os/input-portal/` is AresOS's copy of **niri-input-portal**, being changed to serve labwc (package 316,
`briefs/316-input-portal.md`).

| | |
|---|---|
| Upstream | https://github.com/Qingswe/niri-input-portal |
| Commit | `49f82a63ca53b0137ad4eea08f4cd9d72642a22b` ("Merge pull request #2 from Qingswe/fix/eis-region-bounds") |
| Date | 2026-10-20 16:19 UTC |
| License | MIT. `LICENSE` is upstream's file, unchanged, and ships with the binary. |
| Vendored in | commit `009b840c`, which changes nothing |

## Checking the copy

The vendor commit's folder is upstream's commit, file for file, name for name and mode for mode: both are the
same git tree.

```sh
git rev-parse 009b840c:os/input-portal     # 0b0106d81218dc0fe744812310c48f4245b522b0
git rev-parse '49f82a63^{tree}'            # the same, in a clone of upstream
```

What AresOS changed since then:

```sh
git diff 009b840c -- os/input-portal
```

For that command to keep working on `main`, the pull request is merged with a merge commit, not squashed (the
lead's decision, 2026-11-19): a squash would drop `009b840c` from `main`'s history. If the vendor commit is ever
missing all the same, the same comparison works against upstream itself:

```sh
git fetch https://github.com/Qingswe/niri-input-portal 49f82a63ca53b0137ad4eea08f4cd9d72642a22b
git diff 'FETCH_HEAD^{tree}' HEAD:os/input-portal
```

## Our changes

Every change to this folder gets a row here, with the commit that made it.

| Commit | Change |
|---|---|
| `bb596239` | Deleted `install.sh` and `uninstall.sh`. They call `sudo`, write to `/usr` and `~/.config/xdg-desktop-portal`, and restart the user's portal. AresOS installs the backend from its image (package (c)). |
| `baf97613` | Names. The package and binary are `aresos-input-portal` (`Cargo.toml`; in `Cargo.lock` only the package's own entry changes: new name, moved to its place in name order). D-Bus name `org.freedesktop.impl.portal.desktop.aresos-input` (`src/main.rs`). Variables `ARESOS_INPUT_PORTAL_IDLE_TIMEOUT` (`src/wayland/mod.rs`) and `ARESOS_INPUT_PORTAL_LOG` (`src/main.rs`). `data/`: the three files renamed to `aresos-input.portal`, `aresos-input-portal.service` and `org.freedesktop.impl.portal.desktop.aresos-input.service`, pointing at `/usr/libexec/aresos-input-portal`; the portal file gains `UseIn=AresOS`. |
| `1db141b3` | Added, no upstream file touched: `build.sh`, `toolchain.env` (the pinned builder image, compiler, Debian packages, cargo-audit and advisory database) and `dev/container.sh`. |
| `63799603` | Added this file. |
| `302f88dc` | `Cargo.lock` only: `tokio` 1.53.1 to 1.53.3, `rustix` 1.1.4 to 1.1.6, `event-listener` 5.4.1 to 5.4.2, the patch releases that fix `cargo audit`'s three "unsound" warnings (`cargo update -p <crate> --precise <version>` in the pinned container). Every other entry is upstream's. |
| `91418fc5` | Activation by `Exec=` only: `SystemdService=` removed from the D-Bus service file and the systemd user unit `data/aresos-input-portal.service` deleted (see "Activation" below). Added `data/allowed-apps`, the allow-list as shipped: comments only. |
| `5e882222` | The behaviour (brief 316, "What to build" 2 and 3). **Screens:** `src/niri.rs` deleted, with every call to `niri`; `src/screens.rs` and `src/wayland/heads.rs` read the screens from `zwlr_output_manager_v1` into one snapshot that the zones, the barrier surfaces and the EIS regions share; a change of screens ends the capture, removes the barriers and sends `ZonesChanged`; barriers between two screens are refused (`src/wayland/mod.rs`). **Trust** (`src/trust.rs`, `src/portal.rs`, `src/eis_server.rs`): the allow-list, the frontend-only caller check on every impl method, one armed session, activations and clipboard transfers bound to their session, EIS seats cut down to the grant, one teardown for close, frontend loss and EIS death. **Logs:** the `--clip-status`, `--clip-read` and `--clip-claim` commands and their D-Bus methods removed; positions, hints and clipboard types out of every message; `ARESOS_INPUT_PORTAL_LOG` is one level word, the libraries stay at warnings, and `WAYLAND_DEBUG` and `REIS_DEBUG` are removed from the environment at start (`src/main.rs`). **Names:** control interface `org.aresos.InputPortal.Control` at `/org/aresos/InputPortal/Control`, EIS seat `aresos-capture` with devices `aresos-capture-pointer` and `aresos-capture-keyboard`, keymap memfd `aresos-input-keymap`, layer-surface namespace `aresos-input-barrier`, `Cargo.toml`'s description. **tokio:** `AsyncFd::with_interest`, the constructor the advisory is about, replaced by `register_with_interest`. Failures of impl methods are D-Bus errors now, where upstream answered response code 2. |
| `0da6e78a` | `src/wayland/mod.rs`: a barrier's span includes its last pixel, as the portal specification counts it (the right edge of a 1080-high zone is `y1=0, y2=1079`). Upstream's surface ended one pixel short. |
| `1636ae4b` | `src/portal.rs`: when the report of new screens is handled, only barriers set for an older zone set are cleared. |
| `7e846c9f` | REVIEW-1's findings 1 to 5 (`src/portal.rs`, `src/wayland/mod.rs`, `src/wayland/state.rs`, `src/main.rs`). Every arming and every crossing has a number of its own: a crossing is accepted only for the session armed by the arming it names, EIS is attached only to the crossing it was accepted for, and `Disarm` ends a crossing in flight with its buffered input (upstream named a crossing by session path and barrier ID, and kept the capture). `Activated` is sent once the compositor has granted the lock and, with the keyboard, keyboard focus (upstream: when the lock was requested); a grab that doesn't come in 500 ms, a lost keyboard focus, a closed layer and a lost pointer all end the capture and are reported like an unlock. Signals are sent to the frontend's unique bus name (upstream broadcast them). When the bus connection ends, every session is closed and the process exits. |
| `1d5b4789` | `src/wayland/heads.rs`: a debug line when the compositor retires a head or a mode, so a log shows whether it ever did. Added, no upstream file touched: `harness/` (the headless harness of brief 316, "Tests"). |
| `b4e6069f` | Package 321, step 1 (`briefs/321-deskflow-image.md`, "What to build" 1): 316's five follow-ups and two of the brief's own. `src/eis_server.rs`: input is written to the receiver only between `StartEmulating` and `StopEmulating`. `src/portal.rs`, `src/main.rs`: the end of the Wayland connection closes every session and ends the process, as bus loss does; `authorize` makes the caller the sessions' frontend and closes an earlier owner's sessions first, and the name watch closes only the sessions of the owner its notice names; a Session object is removed only when no session with its path exists again; an empty application ID is refused before the allow-list is read. `src/wayland/clipboard.rs`: releasing the claim destroys the portal's own source and no longer unsets the seat's selection. `src/wayland/mod.rs`: the idle watchdog is off by default (upstream: 15 seconds); `ARESOS_INPUT_PORTAL_IDLE_TIMEOUT` still sets one. |
| `6d2c1cbf` | Package 321, step 1b (`briefs/321-deskflow-image.md`, "What to build" 1). Added `src/sharing.rs`: the sharing switch `/etc/aresos/input-portal/sharing` (on only as a root-owned regular file saying `on`, in root-owned folders nobody else can write, no symlink anywhere) and the gate the input path reads. `src/portal.rs`: the switch is read under the state's lock when a session is made, at `Enable`, at each crossing, in every clipboard method and event, again after `SelectionRead`'s wait, and every 250 ms while a session exists; Off closes the gate and every session, and the backend exits if the compositor doesn't confirm the end of the capture within a second; new control method `Revoke`; `ForceRelease` and `Disarm` answer only after the compositor's confirmation. `src/wayland/`: `forward` drops everything while the gate is closed; `WaylandCmd::Sync` answers after a `wl_display.sync`. `src/eis_server.rs`: no input is written while the gate is closed. Added `src/release.rs`: `--release` pins the backend as a pidfd and kills it through that pidfd when no confirmed answer comes within 2 s (upstream's `--release` only called the method). `src/main.rs`: `--revoke`. `Cargo.toml`: `rustix` features `process` and `event`, `tokio` feature `time` (no new crate; `Cargo.lock` unchanged). `harness/`: the switch file, and the switch's and the way out's checks (test8, test9). |
| `aa56738d` | Package 321, step 1c (`briefs/321-deskflow-image.md`, "What to build" 6). `src/wayland/state.rs`: upstream's built-in chord is gone (`is_panic_key`, Ctrl+Alt+Escape, and the modifier state only it read); during a capture every key is forwarded, and the way out is labwc's own binding, which runs `--release`. The capture surface's layer namespace, `aresos-input-barrier`, is now what labwc's second patch (`os/labwc/0002-no-bindings-for-the-capture-layer.patch`) knows it by: a test in `os/tests/test_labwc_stage.py` fails if the two differ. `harness/`: labwc's bindings with the two `allowWhenInhibited` marks, `wl-harness layer` (an exclusive layer surface with a given namespace), `CLOSE` from the probe window, and test10 (the shortcuts gate); the images are `localhost/aresos-labwc:321c` and `localhost/aresos-input-portal-harness:321c`. |
| `450c48f8` | Package 321, step 3 review fixes (`reviews/321-deskflow-image/REVIEW-3.md`, finding 1). `src/main.rs`, `src/portal.rs`: the backend starts without a Wayland connection; its Wayland thread (a worker) starts for a `CreateSession` that has passed the frontend, empty-ID, allow-list and switch checks, and stops when the switch reads off (once the compositor has confirmed the end of the capture) or the last session ends; upstream connected at start and stayed connected. `ForceRelease` without a worker answers at once. `src/wayland/mod.rs`: `start` is async with an 8-second bound; `src/wayland/state.rs`: crossing numbers come from a counter shared by every worker, and a closed command channel ends the thread. `harness/`: test8 counts the backend's Wayland connections from outside (pidfd_getfd and the peer's address). |
| Step 3 recheck | Package 321, second review round (`reviews/321-deskflow-image/REVIEW-3-RECHECK.md`, finding 1). Keep the worker in the backend from launch through process exit. Off and the last session closing share a bounded Wayland teardown with concurrent release requests. The worker rereads the switch before binding globals; the switch watcher covers blocked startup. A new D-Bus activation starts with discovery only again. |

## Activation

Upstream ships a D-Bus service file that names a systemd user unit (`SystemdService=`), so on a systemd-activated
session bus the user manager starts the backend. AresOS's session bus is not that bus: `aresos-session` starts its
own with `dbus-run-session`, which has no systemd activation (checked on the laptop on 2026-11-19: there
xdg-desktop-portal is started by the bus's own `Exec=` activation and its systemd user unit is inactive). A unit
started by the user manager would claim the name on a different bus. So the service file activates by `Exec=`
only, and there is no unit. The backend then runs with the bus daemon's environment; package (c) proves it has
`WAYLAND_DISPLAY`.

## Still upstream's

`README.md` is upstream's text, unchanged. It explains how the capture and the clipboard work, which still holds.
It also describes niri and `niri msg`, `install.sh`, `/usr/lib/niri-input-portal`, the systemd unit, the
`NIRI_INPUT_PORTAL_*` variables, `RUST_LOG`-style log filters and the `--clip-*` commands: none of those apply to
AresOS's copy. The names above are the ones that count here. Some comments in the source still say "niri" where
they mean the compositor.

`Cargo.toml` still lists `serde_json`, which only `src/niri.rs` used. Taking it out would change `Cargo.lock`
beyond the three bumps above, so it stays, unused and not linked.
