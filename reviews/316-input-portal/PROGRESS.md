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
| `1636ae4b` | A late notice about new screens keeps barriers that were set against the snapshot as it is now. |

### What was shown

- **Build and tests** (`evidence/step2-build.txt`, `dev/container.sh build` without `--cache`): no compiler
  warning, `cargo test --locked --offline`: **66 passed** (step 1 had 16, and upstream's 16 are all still
  there with their assertions: the 7 placement tests unchanged, the 4 transfer tests with the session argument
  added, the 5 region tests against the snapshot). Binary SHA-256
  `ce32fb675cd1db93152245e37ab78bcb05ce8ce4a54529c0f040713c768273d6`. The cached build gives the same binary
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
| A clipboard transfer goes only to its session, serial and claim | `portal.rs:224` (`take_transfer`), `:914`, `:1291` |
| Close, frontend loss, EIS death: the session is removed whole | `portal.rs:526` (`remove_session`), called from `:989`, `:1001` (watch: `:1802`), `:1019` |
| Screens: one snapshot from `zwlr_output_manager_v1`, committed at `done` | `screens.rs:113`, `:218`; `wayland/heads.rs:82`, `:141`; `wayland/state.rs:126` |
| A change of screens: capture ended, surfaces removed, barriers cleared, new EIS region, `ZonesChanged` | `wayland/state.rs:126`, `portal.rs:1234`, `eis_server.rs:408` |
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

## Step 3, the harness and tests 1 to 7: done (2026-11-20, Claude Fable 5.2)

`main` was merged in first (`82c4a589`, 36 commits).

| Commit | What |
|---|---|
| `7e846c9f` | REVIEW-1's findings 1 to 5 in the backend, with six new unit tests (72 in all). |
| `1422d60e` | Findings 6 to 9 and the new capture limits in `KNOWN-LIMITS.md`; the `UPSTREAM.md` row. |
| `1d5b4789` | The harness in its first working state; a debug line when labwc retires a head or a mode. |
| the commit after it | The harness as it ran, its evidence (`evidence/step3-harness/`, `evidence/step3-build.txt`), this file. |

### REVIEW-1, findings 1 to 5

REVIEW-1 is Codex's static review of steps 1 and 2 (gpt-6.2-astra, high). The lead's triage (2026-11-19): fix 1
to 5 with a test each; 6 to 9 are known limits (`KNOWN-LIMITS.md` has them with the reasons).

| | The fix, in `os/input-portal/src/` | Its test |
|---|---|---|
| 1 | Every arming has a number that is never used twice (`Session::arming`, `portal.rs`): `Arm` carries it and a crossing reports it back. Every crossing has a number of its own (`wayland/state.rs`). The portal accepts a crossing only for the session armed by that very arming, `AttachEis` and `EndCapture` name the crossing, and `Disarm` ends a crossing in flight and drops its buffered input (at most 256 events are held back). | Unit: `a_crossing_queued_for_a_closed_session_never_reaches_a_new_session_with_its_path`, `every_arming_has_its_own_number_and_a_crossing_of_an_earlier_one_is_refused`. The harness can't hold a crossing in the queue, so it has no test of its own for the race. |
| 2 | When the watch on the frontend's name ends, `State::bus_lost` closes every session and releases the capture, and `serve` ends the process with an error. | Unit: `losing_the_bus_closes_every_session_gives_the_input_back_and_stops_the_backend`. Harness `review1-finding2`: the bus killed while a session is armed and during a capture; the backend exits, EIS is disconnected, the next crossing stays local. |
| 3 | A crossing starts unconfirmed. `Activated` is sent only when labwc's `locked` has come for this lock and, for a session with the keyboard, the barrier's surface has keyboard focus (`confirm_if_held`). After 500 ms without that, input goes back and what was held is dropped. Losing keyboard focus later ends such a capture. | Unit: `a_crossing_is_a_capture_only_once_the_lock_and_the_granted_keyboard_are_held`. Harness test 2: the backend's log has "asked", "lock granted", "keyboard focus", "held" in that order before `Activated`, and the window receives nothing from the crossing on. The timeout itself has no test: labwc always granted the grab. |
| 4 | Signals go to the unique bus name of the frontend that made the sessions (`Inner::frontend`, `send_signal_to`), never as a broadcast. A caller that passes the frontend check under a new name first ends the old owner's sessions. | Unit: `every_signal_goes_to_the_frontend_that_made_the_session_and_to_nobody_else`. Harness `review1-finding4`: a second connection subscribed to every signal on the bus for the whole run received none of the portal's (the frontend received 55). |
| 5 | A closed layer and a seat that loses its pointer end the capture through the same path as an unlock (`lose_capture`): `CaptureLost` with the crossing's number, so EIS stops and the frontend gets `Deactivated`. | Unit: `a_lost_capture_ends_only_the_capture_it_names` (the portal's side). The harness has no trigger: labwc keeps the seat's pointer whatever devices exist (shown in `review1-finding5`) and closes a layer surface only with its output, which is a change of screens anyway. |

### The harness (`os/input-portal/harness/`)

```sh
os/input-portal/dev/container.sh build <backend dir>            # the backend, as before
os/input-portal/harness/run.sh image                            # once, and after a change to clients/
os/input-portal/harness/run.sh run <backend dir> <new evidence dir>
```

About two minutes. Exit 0 when every check passed, 1 when one failed, 2 when the setup could not be used.

- **Isolation.** One throwaway rootless container: `--network=none` (its own network namespace, so no abstract
  socket of the host either), no `-v`, no `--device`, no host environment, a 15-minute limit. The harness and the
  backend go in as a tar stream and the evidence comes back as one. `in-container.sh` checks before anything
  starts: no display, bus or runtime variable; only the loopback interface; no `/dev/input`, `/dev/uinput`,
  `/dev/dri`, X11 folder, `/run/user`, system bus or home folder; no socket anywhere (20 checks,
  `isolation.txt`). Then it makes a scratch `HOME` and `XDG_RUNTIME_DIR`. `driver.py` starts every process with
  an environment it builds itself, and checks each one's `/proc/<pid>/environ` and every socket in the container
  before the first test. labwc is told not to update an activation environment. The backend and its allow-list are
  installed into the container's own `/usr`. Cleanup stops the driver's own processes and removes that one
  container.
- **The compositor.** Package 311's RPM from the local image `localhost/aresos-labwc:311e` (311's own build of
  2026-11-19; nothing was rebuilt): `labwc-0.9.6-1.fc44.aresos1.x86_64.rpm`, SHA-256
  `8f9f4ea2ab3163ee2a760624cd10d7ceb105a3c84f1d980ed73cbea7aba565c6`. The image build refuses a labwc whose
  loaded bytes differ from `os/labwc/labwc.lock.json` on this branch (`main`'s, merged as `67e1e60c`): both
  binaries match. Headless, two outputs, pixman, wlroots 0.19.3. Its `rc.xml` binds `W-S-Escape` to
  `/usr/libexec/aresos-input-portal --release` and nothing else.
- **The test clients** (`clients/`, compiled into the image): `eis-receiver` (libei; binds every capability and
  prints what it receives), `wl-harness window` (a full-screen window that prints its input), `wl-harness input
  pointer|keyboard` (`zwlr_virtual_pointer_v1` and `zwp_virtual_keyboard_v1` with real evdev codes and the
  default keymap), `wl-harness outputs` (only for the control below). `driver.py` is the frontend: one bus
  connection owns `org.freedesktop.portal.Desktop` and calls in the real order, a second one makes the refused
  calls and listens. 311's `lock-probe.c` was read for the virtual pointer and the window; the clients are new
  because the tests need them to stay alive and to be driven step by step.

### Results: 81 checks, all passed

`evidence/step3-harness/results.txt` has every line; the same folder has the backend's logs (`backend-1.log` to
`backend-7.log`), each EIS receiver's log, the window's, labwc's, and the signals each bus connection received.
The run that counts used the build without the cache (`evidence/step3-build.txt`): binary SHA-256
`f4b3fbdd7bd00a6ca00b508634f6d99b5a910f1bfe07aa469211f417245928c8`, the same file as the cached build.

| Test | Checks | What was shown |
|---|---|---|
| Setup, isolation | 5 (and 20 in `isolation.txt`) | labwc offers the seven protocols; every process has the private bus and display only. |
| 1 | 18 | GetZones equals `wlr-randr`; the EIS region is the zones' bounding box; four outer barriers placed and each crossing activates the right one at the right edge, the edge between the outputs is refused; a scale change and disabling an output each bring `ZonesChanged`, a new zone set, refusal of the old one, no capture on the old edge, new EIS devices with the new region, and new barriers that capture without another `Enable`. |
| 2 | 8 | `Activated` after lock and keyboard focus; motion, button, scroll and keys over EIS with the activation's number; the window receives none of it, and receives input before and after. |
| 3 | 9 | `Release`, `--release`, `--disarm`, **Super+Shift+Escape through the virtual keyboard under the grab**, SIGKILL and the idle watchdog (3 s here) each end the capture, and pointer and keyboard are local again. |
| 4 | 8 | After `Close`, after the EIS connection dies (before a crossing and during a capture) and after the frontend's connection drops: session closed, EIS disconnected, a new crossing stays local. |
| 5 | 3 | `wl-copy` text is offered with its types and read through the fd; a session's write is what `wl-paste` prints. |
| 6 | 8 | An unlisted and an empty `app_id` refused; all 15 methods refuse the second bus name, with no fd; of two sessions only the armed one is activated and receives input; the other session's `SelectionWrite` for the owner's serial is refused; a pointer-only session's receiver gets no keyboard and no key. |
| 7 | 15 | A run at `trace` with `WAYLAND_DEBUG` and `REIS_DEBUG` set: no clipboard marker or type, key code, button code, motion value, crossing coordinate or release hint in the log, in any error text or in `--status`/`--release` output; no wire dump. |
| REVIEW-1 | 7 | Findings 2, 4 and the part of 5 that can be reached (above). |

**The chord works.** With the backend holding the exclusive keyboard grab, Super_L, Shift_L and Escape pressed
through `zwp_virtual_keyboard_v1` made labwc run `--release`; the capture ended (`Deactivated`) and input was
local again. The EIS receiver saw Super and Shift go down (and, in this run, up again); Escape never reached it.

### What the tests found

- **In the backend: nothing after the REVIEW-1 fixes.** Every failure of the first runs was the harness's own
  (an EIS region expected at the layout's origin, a session path with a `-`, a second copy of a clipboard fd kept
  open by the test frontend, a mark taken before the pointer was in place).
- **labwc aborts when a headless output is switched off and on again while any client stays connected to
  `zwlr_output_manager_v1`.** `labwc: types/wlr_output_management_v1.c:777: head_send_state: Assertion 'found'
  failed`, at the first `--on` after an `--off`. The control at the end of the run (three fresh labwcs, `results.txt`):
  with nobody else connected labwc keeps running; with `wl-harness outputs` connected (it binds the manager and
  only listens) it aborts; with the backend connected it aborts the same way. The backend released nothing and
  was sent no `finished` (it logs both: 0 and 0). So this is labwc's or wlroots' own fault, but the backend is
  such a client and runs for the whole session. **Not known: whether a real output does it too.** A headless
  output has no list of modes, and the assertion is in the mode lookup, so a real monitor may well be fine. It
  has to be tried on real outputs before package (c) ships: a labwc abort ends the session. The harness therefore
  leaves the output off after its test.

### Decisions

- **`Activated` waits for keyboard focus too**, as the review asked, and a capture with the keyboard ends when the
  focus goes. A session with the pointer only needs just the lock.
- **Bus loss ends the process.** A backend without its bus can serve nobody and nobody can stop it.
- **`EndCapture` names its crossing** (the way out and shutdown name none and end whatever is there), so a late
  command can't end a newer capture, and an EIS handle for a crossing that is over is answered with
  `CaptureLost`, so the portal never counts a session as capturing that isn't.
- **The harness tools are written here, not taken from packages** (`wlrctl`, `wtype`, `wev`): the keys had to be
  real evdev codes pressed one after the other, and the devices had to stay alive (labwc's seat changes with
  them). Fedora ships no copy of the virtual-keyboard protocol's XML, so its wire format is written out in
  `clients/virtual-keyboard-unstable-v1.xml`.
- **`cargo audit` was not run again:** `Cargo.lock` is unchanged since step 2.

### What the tests don't show

- **Findings 1 and 5 and finding 3's timeout have unit tests only** (the table above says why).
- **The real frontend.** `driver.py` receives the unicast signals through GDBus, as xdg-desktop-portal would,
  but xdg-desktop-portal itself was not run. Its routing, and that it gets every signal, is package (c)'s.
- **Real outputs, real input devices, fractional scale on a real panel, Deskflow.** All (c)'s.
- **`trace` has no lines of its own:** the backend logs nothing at that level, so the verbose log is its debug
  log (52 lines in the run).

## Report (for the lead; agents can't write `REPORT.md`)

- **Done:** steps 1 to 3 of `briefs/316-input-portal.md`. The vendored backend reads the screens from labwc,
  holds the trust model, has REVIEW-1's five fixes, 72 unit tests, and a headless harness whose 81 checks pass on
  package 311's labwc.
- **Verified:** `dev/container.sh build` without the cache (72 tests, no warning); `harness/run.sh run`
  (`evidence/step3-harness/results.txt`: 81 passed, 0 failed); the two tables above.
- **Not verified:** everything under "What the tests don't show", and the labwc abort on real outputs.
- **JUDGMENT-CALL:** none that changes how AresOS feels. The decisions above are technical.
- **PLAN-GAP:** the brief's test 7 says `RUST_LOG=trace`; the backend reads `ARESOS_INPUT_PORTAL_LOG` (step 2's
  decision) and the harness sets both. The brief's harness outline has no word on what the compositor does when
  an output comes back; that is where labwc aborted.
- **Open questions:** does labwc abort on a real output that is switched off and on while the backend runs? If
  it does, either labwc is patched (package 311's stage) or the backend stops holding `zwlr_output_manager_v1`
  open (reads the screens when it needs them, which is a change to step 2's design).

### What package (c) must do, from this package

1. **First: the output check on real hardware (VM with a real or virtual DRM output, then the laptop).** With the
   backend running, `wlr-randr --output <external> --off`, then `--on`, and unplug and replug the monitor. labwc
   must keep running. Do it before anything else of (c) is built on this backend.
2. Install the binary to `/usr/libexec/aresos-input-portal`, the portal file and the D-Bus service file, and the
   allow-list to `/usr/share/aresos/input-portal/allowed-apps`: root-owned, mode 0644, with Deskflow's proven
   `app_id` and nothing else.
3. Bind `W-S-Escape` to `/usr/libexec/aresos-input-portal --release` in `rc.xml`, as the harness's `rc.xml` does
   (`evidence/step3-harness/labwc-rc.xml`). labwc must have the session bus's address in its environment for that
   command to reach the backend; prove it on the real session.
4. Check with the real xdg-desktop-portal that it receives the backend's signals (they are addressed to its
   unique bus name) and closes its copy of every clipboard fd it passes on.
5. Check what the Mac sees of the chord: Super and Shift go down on the remote before Escape releases the capture.
   Deskflow should let them go when it is deactivated; if they stick, pick another way to release them.
6. When the bus goes away the backend exits; the next call activates it again. Check that with the real session's
   bus and `WAYLAND_DISPLAY`.
7. How sharing is turned on and off, and closing the sessions when it is turned off (the allow-list is read only
   when a session is made).

## Left, in order

### Step 4

Nothing of step 3 is left. A step 4 is needed only if the reviews (a fresh Fable reviewer, then Codex) ask for
changes, or if the lead wants the labwc abort looked at before (c): then start from the control at the end of
`harness/driver.py` (`control_output_cycle`), which reproduces it in about ten seconds.

## Podman, after step 3

Kept: the builder image and the two cache volumes, as after step 2; `localhost/aresos-labwc:311e` (311's, only
read); and one new image, `localhost/aresos-input-portal-harness:316` (the harness; remove it with
`podman rmi localhost/aresos-input-portal-harness:316` when the package is merged). The two earlier builds of
that image were removed by their IDs. No container is left (every run used `--rm`), and no `prune` was run.

- **(c), from step 3's labwc abort (lead, 2026-11-20):** with the backend running, unplug and replug the external monitor and switch each output off and on with `wlr-randr`, in the VM and on the laptop; see `KNOWN-LIMITS.md`, "labwc aborts on an output off/on cycle". Never set a custom mode on his session with the backend running until this passes.
