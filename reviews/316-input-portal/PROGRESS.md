# 316 input portal: progress

Brief: `briefs/316-input-portal.md`. One fresh agent per step; each keeps this file true.

## Step 1, source and toolchain: done (2026-11-19, Claude Fable 5.2)

| Commit | What |
|---|---|
| `009b840c` | Upstream at `49f82a63ca53b0137ad4eea08f4cd9d72642a22b`, unchanged. `git rev-parse 009b840c:os/input-portal` is upstream's tree `0b0106d81218dc0fe744812310c48f4245b522b0`. |
| `bb596239` | `install.sh` and `uninstall.sh` deleted. They were never run. |
| `baf97613` | Names: binary and package `aresos-input-portal`, D-Bus name `org.freedesktop.impl.portal.desktop.aresos-input`, `ARESOS_INPUT_PORTAL_IDLE_TIMEOUT`, `ARESOS_INPUT_PORTAL_LOG`, the three data files. |
| `1db141b3` | `build.sh`, `toolchain.env`, `dev/container.sh`. |
| `63799603` | `os/input-portal/UPSTREAM.md`, this file, `evidence/step1-*.txt`. |

Draft PR into `main`: #124.

### What was shown

All of it ran in rootless podman containers of the pinned image, with no host folder mounted. Logs:
`reviews/316-input-portal/evidence/` (the folder is in `.gitignore`, so new files there need `git add -f`).

- **The unchanged backend builds** (`step1-unchanged-build.txt`): the tree of `009b840c`, with the same steps
  `build.sh` runs. `cargo build --release --locked --offline` finished, `cargo test --locked --offline`: 16 passed.
  One compiler warning, upstream's own: `Session.app_id` is never read.
- **`build.sh` on `1db141b3`** (`step1-build.txt`): 16 tests passed; binary SHA-256
  `d3bd619824060f329dfabecd5d6cbcedd536527f4bc9709c7fd9688064e26627`, 8,267,904 bytes. Three clean builds gave
  that same hash, so the build repeats byte for byte in this container. It needs `libxkbcommon.so.0`,
  `libgcc_s.so.1`, `libm.so.6` and `libc.so.6` at run time; the image has all four (`os/manifest/ci/packages.txt`:
  libxkbcommon 1.13.1, glibc 2.43; the build links against glibc 2.41).
- **Refusals:** `build.sh` stops with `INPUT_PORTAL_REFUSED` on wrong arguments, a missing source, an output dir
  that isn't empty, and a rustc other than the pinned commit; with no network it stops at the package install
  and builds nothing.
- **`cargo audit`** (`step1-audit.txt`): cargo-audit 0.23.0, no network, advisory database at
  `7133866a6b44d6d3e1994ae6a48a296553c3c3da` (2026-11-19 08:55 UTC, 1550 advisories), 128 crates.
  **No vulnerabilities. Six warnings:**

  | Crate | Kind | Advisory | Fix |
  |---|---|---|---|
  | `tokio` 1.53.1 | unsound: `AsyncFd::new` and related constructors violate I/O safety | RUSTSEC-2026-0386 | 1.53.3 |
  | `rustix` 1.1.4 | unsound: xattr functions with a zero-length buffer | RUSTSEC-2026-0486 | 1.1.6 |
  | `event-listener` 5.4.1 | unsound: `!Send` tags can cross threads through `StackSlot` | RUSTSEC-2026-0221 | 5.4.2 |
  | `zvariant` 5.13.1 | unmaintained | RUSTSEC-2026-0370 | none |
  | `zvariant_derive` 5.13.1 | unmaintained | RUSTSEC-2026-0372 | none |
  | `zbus_names` 4.3.4 | unmaintained | RUSTSEC-2026-0371 | none |

  A second run with the network on (the live database and crates.io index, same day) found the same six and no
  yanked crate. The pinned run can't check for yanked crates.

### The pins (`os/input-portal/toolchain.env`)

- Builder: `docker.io/library/rust@sha256:f6c4a35d21dbb3c89d7a8d056c193e94fc09037f2b58dd858b09c39a47dd02d7`
  (`rust:1.99.1-slim-trixie`; its linux/amd64 image is
  `sha256:e97df055c54a05160e7c67ba3b2963de6ddb95903911baf8922dbcd1b394f698`), rustc commit
  `58cf8f9c35b355199727627d07ae34a4e2846d67`.
- Debian packages `libxkbcommon-dev=1.7.0-2` and `pkgconf=1.8.1-4` from snapshot `20261104T212339Z`.
- cargo-audit 0.23.0, SHA-256 `4f01c74ed84b2dffd0b1d37012a62cdf2a92c96e25bdf8eec7fcc0d4d3eb7811` (the digest
  GitHub records for that release file).

### Decisions

- **Rust 1.99.1, not 1.100.0.** 1.100.0 was a week old; 1.99.1 is the last point release of the line before it.
  The slim image (928 MB) is enough.
- **Two Debian packages the brief didn't foresee.** smithay-client-toolkit links libxkbcommon and finds it with
  pkg-config, and the Rust image has neither. `build.sh` installs exact versions from the Debian snapshot the image
  itself was built from; apt checks the archive's signature. The library is linked dynamically, so none of it is in
  the binary.
- **`toolchain.env`, not a `.lock.json`.** The builder image has no Python and no jq; bash reads this file
  directly, in `build.sh` and in `dev/container.sh`.
- **The package is renamed, not only the binary.** `Cargo.lock` changes in one entry (its name and its place in
  the order); `--locked` proves the rest still matches.
- **`ARESOS_INPUT_PORTAL_LOG` too.** One renamed variable next to one `NIRI_` variable would be a trap.
- **No host mount in `dev/container.sh`.** SELinux is enforcing on the laptop and denies a plain `-v` mount of
  the repo. Instead of switching labels off, the source goes in and the result comes out as tar streams.
- **cargo-audit as RustSec's release binary**, pinned by SHA-256, instead of compiling about 300 more crates.
- **The audit's findings are listed, not fixed:** the brief asks for the list, and `Cargo.lock` stays upstream's.
- **`README.md` stays upstream's text**; `UPSTREAM.md` says which parts no longer apply.
- **`build.sh` also writes `LICENSE`** to the output: MIT asks for it next to the binary.

### What the code doesn't show

- **A squash merge drops the vendor commit.** 311 was squash-merged (#119). If this PR is too, `009b840c` leaves
  `main`'s history and `git diff <vendor commit>` no longer works there. Merge this PR with a merge commit, or use
  the second recipe in `UPSTREAM.md`, which compares against upstream itself.
- **311 has merged** (`67e1e60c` on `main`, its branch is gone). This branch starts at `023fe9a6`, before that, so
  `os/labwc/` and `reviews/311-labwc-pointer-lock/` are not in it. Step 3 needs them: merge `main` in first.
- **The backend reads `ARESOS_INPUT_PORTAL_LOG`, never `RUST_LOG`.** The brief's log test says `RUST_LOG=trace`;
  the verbose run has to set `ARESOS_INPUT_PORTAL_LOG=trace`, or step 2 makes it read both.
- **The systemd user unit may never run under AresOS.** `aresos-session` starts its own bus with
  `dbus-run-session`. That bus isn't systemd's, so it starts the backend through the D-Bus service file's `Exec=`
  line and ignores `SystemdService=`; a unit started by the user manager would claim the name on the wrong bus.
  The backend then gets the bus daemon's environment, which may lack `WAYLAND_DISPLAY`. Package (c) proves which
  path starts it (already on its list: "activation and `--release` on the same bus and display as labwc").
- **The licenses of the crates compiled into the binary** (`Cargo.lock` lists 127 dependencies, not all of them
  linked on Linux; MIT, Apache-2.0 and similar) ask for their notices too. Nothing collects them yet. For (c) or
  the lead to decide.
- **The image reference in (c)'s `Containerfile`** must be `BUILDER_IMAGE` from `toolchain.env`. `build.sh` only
  checks the compiler's commit, which another image of the same Rust release would also pass.

## Step 2, behaviour: done (2026-11-19, Claude Fable 5.2)

`main` was merged in first (`32050773`; 311's `os/labwc/` and its probe are in the branch now).

| Commit | What |
|---|---|
| `302f88dc` | `Cargo.lock`: `tokio` 1.53.3, `rustix` 1.1.6, `event-listener` 5.4.2. |
| `91418fc5` | Activation by `Exec=` only (the systemd unit is gone); `data/allowed-apps`, shipped with comments only. |
| `5e882222` | The screens module, the trust model, the log scrub, the diagnostics removed, 65 unit tests. |
| `0da6e78a` | A barrier covers its last pixel, as the specification counts it; its example is the 66th test. |

### What was shown

- **Build and tests** (`evidence/step2-build.txt`, `dev/container.sh build` without `--cache`): no compiler
  warning, `cargo test --locked --offline`: **66 passed** (step 1 had 16, and upstream's 16 are all still
  there with their assertions: the 7 placement tests unchanged, the 4 transfer tests with the session argument
  added, the 5 region tests against the snapshot). Binary SHA-256
  `f5710d99f7590db053f5633cecdccc7355629d96c0fc70c7df7d217c3697902e`. The cached build gives the same binary
  and ran the tests three more times, all green.
- **`cargo audit`** (`evidence/step2-audit.txt`, same cargo-audit and advisory database as step 1): **no
  vulnerabilities, and the three "unsound" warnings are gone.** Left: the three "unmaintained" warnings
  (`zvariant`, `zvariant_derive`, `zbus_names`), listed in `KNOWN-LIMITS.md`. The tokio fix deprecates the
  constructor the advisory is about, and upstream used it (`AsyncFd::with_interest`): replaced in
  `src/eis_server.rs` by `register_with_interest`, so the fix is in the code and not only in the lock.

### Each rule, in the code (`os/input-portal/src/`)

| Rule | Where |
|---|---|
| Allow-list: exact, default deny, empty ID denied, missing file denies; the file must be a root-owned plain file nobody else can write | `trust.rs:45` (`allows`), `trust.rs:51` (`load`); read for every session in `portal.rs:569` |
| Only the frontend may call: the bus is asked who owns `org.freedesktop.portal.Desktop` for every call | `portal.rs:438` (`authorize`), first line of each of the 15 methods; the D-Bus methods pass the header's sender (`portal.rs`, `sender_of`) |
| One armed session; the other is disarmed and gets `Disabled` | `portal.rs:772` (`enable`), `portal.rs:492` |
| A crossing goes only to the session its barrier was armed for; otherwise the capture ends at once | `wayland/state.rs:307` (the surface's session), `portal.rs:1137` (`activated`) |
| Barriers are checked against the snapshot's zone set, twice | `portal.rs:674`, `wayland/state.rs:185` |
| EIS offers only what `Start` granted, whatever is bound | `eis_server.rs:73`, `:87`, `:544`; `ConnectToEIS` needs `Start` (`portal.rs:732`) |
| A clipboard transfer goes only to its session, serial and claim | `portal.rs:224` (`take_transfer`), `:914`, `:1284` |
| Close, frontend loss, EIS death: the session is removed whole | `portal.rs:526` (`remove_session`), called from `:989`, `:1001` (watch: `:1795`), `:1019` |
| Screens: one snapshot from `zwlr_output_manager_v1`, committed at `done` | `screens.rs:113`, `:218`; `wayland/heads.rs:82`, `:141`; `wayland/state.rs:126` |
| A change of screens: capture ended, surfaces removed, barriers cleared, new EIS region, `ZonesChanged` | `wayland/state.rs:126`, `portal.rs:1230`, `eis_server.rs:408` |
| Logs: names only in `{:?}`; one level word; libraries at warnings; wire dumps off | `eis_server.rs:52`, `wayland/mod.rs:137`, `portal.rs:304`, `main.rs:35`, `:48`, `:65` |

### Decisions

- **Failures are D-Bus errors.** A refused caller has to get an error "and nothing else", so every impl method
  now returns one; the methods that answered response code 2 for other failures do the same. The success replies
  are unchanged.
- **The bus is asked for the frontend's owner at every call**, not remembered: a remembered owner is wrong for a
  moment whenever the frontend restarts. The backend exports its interfaces and sets up the frontend watch
  before it asks for its bus name, and asks with "do not queue".
- **Closing is the one teardown.** When an EIS connection ends, the session is closed (`Closed` on its impl
  Session object), not kept half alive: that is what makes "can never take the pointer again" simple to hold.
  The backend also disconnects the EIS receiver when its session goes; upstream left the connection open.
- **A refused crossing ends the capture.** Upstream locked the pointer at the crossing and, when no session
  wanted it, left it locked until the 15-second watchdog.
- **Barriers between two screens are refused.** The specification (the image's own
  `org.freedesktop.portal.InputCapture.xml`, 1.22.1): "A pointer barrier must be situated at the outside
  boundary of the union of all zones." Upstream placed them, so moving between two of the user's own screens
  started a capture. A barrier that faces another screen for part of its length is refused whole.
- **A barrier covers its last pixel** (`0da6e78a`). The specification's right edge of a 1080-high zone is
  `y1=0, y2=1079`; upstream ended the surface one pixel short.
- **`Disable` and a stranger's `Release` now really end things:** `Disable` ends a running capture (upstream
  only removed the surfaces), and `Release` from a session that isn't capturing does nothing (upstream ended
  whoever's capture it was).
- **A paste is tied to the claim it was asked of** (`claim_id`), so a paste that raced a second session's claim
  is dropped, not answered by the wrong session.
- **`ARESOS_INPUT_PORTAL_LOG` is one word** (`error`, `warn`, `info`, `debug`, `trace`), not a filter
  expression, and applies to this crate only. The libraries stay at warnings whatever it says: zbus at trace
  prints every message's header, and no setting should be able to turn a library's debug output on. `RUST_LOG`
  is not read.
- **`WAYLAND_DEBUG` and `REIS_DEBUG` are removed from the backend's environment at start.** Read in the crates'
  sources: each makes its library print every protocol message, key codes and motion included, to stderr.
- **The allow-list's path can't be changed**, by a variable or an argument: an override would be a way around it.
  The file may hold `#` comments, so the shipped file can say what it is.
- **`Deactivated` no longer carries a made-up cursor position** (upstream sent 0, 0), and it carries the real
  activation ID (upstream's forced release sent 0).
- **`--disarm` tells the armed session** (`Disabled`) and marks it disarmed; upstream left it marked armed.
- **`serde_json` stays in `Cargo.toml`, unused:** removing it would change `Cargo.lock` beyond the three bumps.

### What the code doesn't show

- **Nothing here ran against a compositor, a bus or an EIS receiver.** The unit tests cover the rules
  (`portal.rs`, with a recorded Wayland thread and recorded signals) and the arithmetic. Not covered, and step
  3's to show: the output-manager dispatch and the wait for the first `done` (`wayland/heads.rs`,
  `wayland/state.rs` `run`), the order of `wl_output` and head events on hotplug, the real `GetNameOwner` call
  and the `NameOwnerChanged` watch, the seat and device behaviour on the EIS wire (capabilities, devices made
  again after `SetRegion`, the disconnect on close), and the environment scrub.
- **The D-Bus methods are tested by calling them** with a built message header (stranger, and no sender), not
  through a connection: zbus's peer-to-peer mode needs a feature that would add crates.
- **Whether labwc gives a headless output a current mode** is not known (see `KNOWN-LIMITS.md`). If GetZones is
  empty in the harness, start there.
- **The log test installs a process-wide subscriber** (`portal.rs`, the last test): with a per-thread one,
  tracing switches off lines that another test's thread reaches first. It is the only test that does.

## Left, in order

### Step 3, the harness and tests 1 to 7 (next)

- `main` is merged in (`32050773`). The binary: `dev/container.sh build <dir>` leaves `<dir>/aresos-input-portal`
  and `<dir>/data/` (the portal file, the service file, `allowed-apps`).
- **The allow-list** is read from `/usr/share/aresos/input-portal/allowed-apps` and nowhere else. In the harness
  container write it there, owned by root (the container's), mode 0644, with the test client's `app_id`. A file
  with another owner or a group/world write bit allows nobody.
- **The frontend client** must own `org.freedesktop.portal.Desktop` on the private bus before its first call.
  Every other caller gets `org.freedesktop.DBus.Error.AccessDenied`, on InputCapture, Clipboard and
  `Session.Close`. When that connection drops, every session is closed.
- **The order is enforced:** `CreateSession2`, `RequestClipboard` (only before `Start`), `Start`, `ConnectToEIS`
  (only after `Start`), `GetZones`, `SetPointerBarriers` with that zone set, `Enable`. Out of order is a D-Bus
  error.
- **With two outputs side by side** the edge between them is refused (`failed_barriers`); use an outer edge for
  the crossing. Barrier ends are inclusive, as in the specification (`y2 = y + h - 1`); `y2 = y + h` is accepted
  too and cut to the output.
- **After an output change:** `ZonesChanged`, every barrier gone, `SetPointerBarriers` with the old zone set
  fails. The armed session stays armed: new barriers with the new zone set are placed at once, without another
  `Enable`. The EIS receiver sees its devices removed and new ones with the new region.
- **After `Close`, frontend loss or EIS death** the backend emits `Closed` on the impl Session object, removes
  it, and disconnects the EIS receiver.
- **Logs:** `ARESOS_INPUT_PORTAL_LOG=trace` (test 7). `RUST_LOG` does nothing. The backend's own
  `WAYLAND_DEBUG`/`REIS_DEBUG` are removed at start; the harness's clients can still use them for themselves.
- **Names:** control interface `org.aresos.InputPortal.Control` at `/org/aresos/InputPortal/Control`
  (`--release`, `--disarm`, `--status`); layer namespace `aresos-input-barrier`; EIS seat `aresos-capture`,
  devices `aresos-capture-pointer` and `aresos-capture-keyboard`.
- **The backend needs `zwlr_output_manager_v1`** and waits up to five seconds at start for its first `done`.
- **Build and test:** `os/input-portal/dev/container.sh build --cache <a new empty dir>`; before a result counts,
  once without `--cache`. Unit tests run inside the build, with no Wayland display and no bus.
- A plain `-v` mount of a repo or scratch folder into a rootless container is denied by SELinux on the laptop.
  Send files in as a tar stream, as `dev/container.sh` does, or build them into the harness image.
- `podman run` from an agent's shell needs `--cgroups=disabled`.
- Add a row to `UPSTREAM.md` for every change, and new limits to `KNOWN-LIMITS.md`.

### Step 4

Only if step 3 leaves something. The last step writes the report here.

## Podman, after step 2

Kept, as after step 1: the builder image (`7cc1f85e641d`, 928 MB) and the two cache volumes
(`aresos-input-portal-registry`, `aresos-input-portal-target`). Step 2 made no image and no volume, ran no
`rmi` and no `prune`, and left no container (every run used `--rm`).
