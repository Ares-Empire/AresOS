# 316 input portal: progress

Brief: `briefs/316-input-portal.md`. One fresh agent per step; each keeps this file true.

## Step 1, source and toolchain: done (2026-11-19, Claude Fable 5.2)

| Commit | What |
|---|---|
| `009b840c` | Upstream at `49f82a63ca53b0137ad4eea08f4cd9d72642a22b`, unchanged. `git rev-parse 009b840c:os/input-portal` is upstream's tree `0b0106d81218dc0fe744812310c48f4245b522b0`. |
| `bb596239` | `install.sh` and `uninstall.sh` deleted. They were never run. |
| `baf97613` | Names: binary and package `aresos-input-portal`, D-Bus name `org.freedesktop.impl.portal.desktop.aresos-input`, `ARESOS_INPUT_PORTAL_IDLE_TIMEOUT`, `ARESOS_INPUT_PORTAL_LOG`, the three data files. |
| `1db141b3` | `build.sh`, `toolchain.env`, `dev/container.sh`. |
| the next commit | `os/input-portal/UPSTREAM.md`, this file, `evidence/step1-*.txt`. |

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

## Left, in order

### Step 2, behaviour (next)

The screens module with one snapshot, the whole trust model, unit tests. Brief: "What to build" 2 and 3, "Tests".

- **Build and test:** `os/input-portal/dev/container.sh build --cache <a new empty dir>`. With the cache a rebuild
  after an edit takes seconds (4 s when nothing changed; a clean build takes 70 s). The two podman volumes
  (`aresos-input-portal-registry`, `aresos-input-portal-target`) already exist. Before a result counts, run it
  once without `--cache`. `CARGO_BUILD_JOBS` defaults to 4.
- **Unit tests run inside the build** (`cargo test` in a container with no Wayland display and no bus), so they
  can't need either.
- **`Session.app_id` is stored and never read** at the pin (`src/portal.rs:111`): the allow-list is new code.
- **Names left as upstream's**, for when you are in those places anyway: the control interface
  `io.github.niri_input_portal.Control` and its path (`src/main.rs:18-19`, `src/portal.rs:925`), the EIS names
  `niri-capture*` (`src/eis_server.rs:347,395,409`), the memfd name (`src/eis_server.rs:233`), the layer-surface
  namespace `niri-input-barrier` (`src/wayland/state.rs:177`), `Cargo.toml`'s description, and the comments.
- **No new crate and no manifest change is needed for the screens:** `wayland-protocols-wlr` 0.3.12 is in
  `Cargo.lock` with its `client` feature, and smithay-client-toolkit 0.21.1 re-exports it, so
  `smithay_client_toolkit::reexports::protocols_wlr::output_management::v1::client` is there today (read in the
  crates' sources). If you add the crate to `Cargo.toml` anyway, the package's own entry in `Cargo.lock` needs that
  one dependency line, and `--locked` fails until it is right.
- **The three unsound warnings** have patch-level fixes (table above). If the lead wants them, it is one commit
  that changes `Cargo.lock` only (`cargo update -p tokio --precise 1.53.3`, and the same for `rustix` 1.1.6 and
  `event-listener` 5.4.2, in a container with a writable copy), a row in `UPSTREAM.md`, and a new
  `dev/container.sh audit`.
- **`data/` is copied whole** by `build.sh`: an `allowed-apps` file put there ships with the rest.
- Add a row to `UPSTREAM.md` for every change.

### Step 3, the harness and tests 1 to 7

- Merge `main` first (311's `os/labwc/` and probe).
- The binary for the harness: `dev/container.sh build <dir>` leaves `<dir>/aresos-input-portal` and `<dir>/data/`.
- A plain `-v` mount of a repo or scratch folder into a rootless container is denied by SELinux on the laptop.
  Send files in as a tar stream, as `dev/container.sh` does, or build them into the harness image.
- `podman run` from an agent's shell needs `--cgroups=disabled`.

### Step 4

Only if step 3 leaves something. The last step writes the report here.

## Podman, after step 1

Kept: the builder image (`7cc1f85e641d`, 928 MB) and the two cache volumes (1.3 GB together). No container is
left. Nothing that was there before was removed or changed.
