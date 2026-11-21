# 321 Deskflow in the image: progress

Brief: `briefs/321-deskflow-image.md`. Branch `pkg/321-deskflow-image`, draft PR133 into `main`. Limits:
`KNOWN-LIMITS.md` here (316's file stays). Evidence: `evidence/`.

## Step 1, the backend: done up to the brief's split point (2026-11-21, Claude Opus 5.5)

Built from `main` at `27169226`. The brief's split point was taken: item 9's five follow-ups with their tests are
done (and two of the brief's own small items with them); the rest of "What to build" 1 is step 1b (below).

| Commit | What |
|---|---|
| `b4e6069f` | The five follow-ups, the empty-ID refusal and the watchdog default, each with a unit test (79 in all, 72 before). |
| the commit after it | `UPSTREAM.md`'s row, `KNOWN-LIMITS.md`, this file, the evidence (`evidence/step1-build.txt`, `evidence/step1-harness/`). |

### What step 1 built (`os/input-portal/src/`)

| | Change | Its unit test |
|---|---|---|
| REVIEW-3, 1 | EIS writes input (keys, buttons, motion, scroll, frames) only between `StartEmulating` and `StopEmulating` (`eis_server.rs`, `input_allowed`, called first in `Devices::apply`). The next run's first keys are not lost: the portal sends `StartEmulating` on the EIS channel before `AttachEis` to the Wayland thread, which writes what it held only after `AttachEis`. | `input_reaches_the_receiver_only_inside_a_capture_run` |
| REVIEW-2, 2 | When the Wayland thread ends (its connection failed), `pump_wayland_events` closes every session, releases the capture and stops the process, as bus loss does (`portal.rs`, `wayland_lost`, `stop_serving`; `main.rs` exits with the reason). | `losing_the_wayland_connection_closes_every_session_and_stops_the_backend` |
| REVIEW-3, 2; REVIEW-2, 3 | `authorize` makes the caller the sessions' frontend (`adopt_frontend`): a new owner of the frontend's name closes the old owner's sessions before its call touches anything. The name watch closes only the sessions of the owner its notice names (`frontend_left`). `create_session`'s own comparison moved there. | `a_new_owner_of_the_frontend_name_gets_nothing_of_the_old_owner_s_sessions` |
| REVIEW-2, 4 | A closed session's object is removed only when no session with that path exists again; the check and the removal hold one lock with the export (`remove_session_object`, `export_session_object`). An object already at the path serves the new session (a `SessionObject` finds its session by path). | `a_session_made_at_a_path_just_closed_keeps_its_object` |
| REVIEW-3, 3 | Releasing the clipboard claim destroys only the portal's own source and no longer sends `set_selection(None)` (`wayland/clipboard.rs`, `release`). | `giving_up_a_claim_destroys_only_the_portal_s_own_source` (see "What the code doesn't show") |
| Brief: empty ID | `create_session` refuses an empty application ID before it reads the allow-list (the list refused it already). | `an_empty_id_is_refused_whatever_the_list_holds` |
| Brief: watchdog | The idle watchdog is off by default (`wayland/mod.rs`, `DEFAULT_IDLE_TIMEOUT`); `ARESOS_INPUT_PORTAL_IDLE_TIMEOUT` still sets one, `0` and garbage mean off. | `the_idle_watchdog_is_off_unless_a_timeout_is_set` |

### What was shown

- **Build and tests** (`evidence/step1-build.txt`): `dev/container.sh build` without `--cache` on `b4e6069f`: no
  compiler warning, `cargo test --locked --offline` **79 passed, 0 failed** (316's 72 unchanged, 7 new). Binary
  SHA-256 `8f1e4e6360264ee055afab232de3d5352b0a8c6e4bb5339a7043181764ef639c`; the cached build of the same tree gave
  the same file and the same 79.
- **Harness rerun** (`evidence/step1-harness/`, 316's harness unchanged, on that binary, with
  `localhost/aresos-labwc:311e` and `localhost/aresos-input-portal-harness:316`): **81 passed, 0 failed**, the same
  check list as 316's (`results.txt`). Test 3's watchdog check still passes: it sets the timeout (3 s) itself.
- **The Wayland-loss fix ran for real once, unplanned:** in the harness's closing control (the headless output
  switched off and on with the backend connected) labwc aborts as in 316, and the backend now ends:
  `backend-7.log` has "the Wayland connection ended: closing every session and stopping", then
  "Error: the Wayland connection ended". In 316's run that backend stayed up until the harness stopped it.
  Four "Wayland thread is gone, dropping a command" warnings follow it (the shutdown's release goes to a thread that
  has already ended); harmless, left.
- **The new frontend-handoff code is quiet in the harness:** no "new owner of the frontend's name" line in any
  backend log (the harness's second bus connection is refused before it).

### The Deskflow RPM gate ("What to build" 3): PASSED

Read-only, nothing installed. The RPM is kept once in the ignored `.work/deskflow-gate/` of this worktree (1.1 MB).

- **Bodhi:** `FEDORA-2026-614dafa1ba`, release F44, status `testing` (submitted 2026-11-20 14:22, pushed to testing
  2026-11-21 02:30, not stable yet), one build `deskflow-1.27.0-1.fc44`, `signed: true`.
- **The RPM:** from Koji's signed copy,
  `https://kojipkgs.fedoraproject.org/packages/deskflow/1.27.0/1.fc44/data/signed/6d9f90a6/x86_64/deskflow-1.27.0-1.fc44.x86_64.rpm`.
- **NEVRA:** `deskflow-0:1.27.0-1.fc44.x86_64` (source `deskflow-1.27.0-1.fc44.src.rpm`, built 2026-11-20 15:14
  CET).
- **SHA-256:** `21a404d8bd0488fdc7ec635ed26447d623b132dc4ae3d12e5f944991ab76484b` (1,114,961 bytes).
- **Signature:** `rpmkeys -Kv` with a private keyring holding only Fedora 44's key
  (`/etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-44-primary`, the same file as `-x86_64`): "Header OpenPGP V4 RSA/SHA256
  signature, key fingerprint: 36f612dcf27f7d1a48a835e4dbfcf71c6d9f90a6: OK", header and payload SHA256 digests OK.
  Signed 2026-11-20 15:23 CET with key ID `dbfcf71c6d9f90a6`. The same check with an empty keyring says `NOKEY`.
- **Imports of `/usr/bin/deskflow-core`** (`readelf --dyn-syms`, SHA-256 of the binary
  `adf57629e7fe3495bbff47726c396f98fb3afadf76e943069ddbff8d4d327711`): `xdp_session_selection_read` and
  `xdp_session_selection_write`, the two the brief names, and with them `xdp_session_selection_write_done`,
  `xdp_session_set_selection`, `xdp_session_request_clipboard` and `xdp_session_is_clipboard_enabled`; the input
  capture calls (16 imports: `xdp_portal_create_input_capture_session`, its `_finish`, and the
  `xdp_input_capture_session_*` calls). It links
  `libportal.so.1` and `libei.so.1`, and the RPM requires both. No `wl-copy` or `wl-paste` string in the binary.
- **For step 3, seen in passing (not a proof of the ID):** the RPM ships
  `/usr/share/applications/org.deskflow.deskflow.desktop`, and the binaries `deskflow`, `deskflow-core`,
  `deskflow-server`, `deskflow-client`.

Step 3 may be dispatched as far as this gate goes. A release build still waits for this build to reach `updates`
with the same SHA-256 ("What to build" 3).

### What the code doesn't show

- **Item REVIEW-3, 3's test is a model.** The release's requests are spelled out as data (`RELEASE_REQUESTS`) and
  the test checks there is only the destruction of the portal's own source. That the compositor then clears its
  own selection and keeps a newer local one is wlroots' rule for a destroyed source, read, not run: the race needs
  the backend to handle its release before labwc's `cancelled`, which the harness can't arrange. The harness's
  clipboard test (test 5) shows the clipboard still works both ways.
- **REVIEW-3, 1 is shown by the unit test and the ordering argument**, not by a harness run: the harness can't hold
  a key between the portal's `StopEmulating` and the Wayland thread's teardown.
- **The Wayland-loss path has no harness check of its own.** It is the unit test plus the control run above, where
  it happened as a side effect of labwc's abort; that the next frontend call starts a fresh backend is VM test 6's.
- **The object-removal lock can't be raced in a unit test**: the tests have no bus, so the object server is a
  recorded set, and the test runs the problem order (new session stored before the old `Closed` goes out) in
  sequence. `zbus` does not hold its object-server lock while a method runs (today's `Close` already removes its own
  object from inside the call), which is what makes the new lock safe from deadlock.

### Left, in order

**Step 1b** (the rest of "What to build" 1; Opus, fresh agent):
1. The switch: `/etc/aresos/input-portal/sharing`, `on` or off, checked like `trust.rs` checks the allow-list plus:
   not a symlink, regular file, and no folder above it a symlink, not root's or writable by someone else. Checked
   when a session is made, at `Enable`, at each crossing before `Activated`, at each clipboard call and again after
   every wait in one before a descriptor is handed out (`selection_read` waits for the Wayland side today).
2. While any session exists, the switch reread at least every 500 ms; Off: the input path's flag stops forwarding
   at once (the Wayland thread's `forward` and the EIS task), the capture ends, every session closes, no new
   clipboard transfer starts; within 2 s of the change everything is over, and the backend exits if the Wayland side
   hasn't confirmed the capture's end within 1 s of seeing Off. `--revoke` (a new control method) makes it
   immediate. Into `KNOWN-LIMITS.md` with the switch: the brief's limit "a clipboard pipe handed out before Off".
3. `ForceRelease` answers only after the Wayland side's confirmation (the brief's own pointer is `wl_display.sync`
   after the lock is destroyed and the keyboard interactivity is dropped and committed: its `done` comes once the
   compositor processed both). `--release` pins the backend first: the bus name's owner via
   `GetConnectionCredentials` (`ProcessFD`, or `pidfd_open` on `ProcessID` and a second look that the same unique
   name still owns the name), executable `/usr/libexec/aresos-input-portal`, user the caller's; no confirmed answer
   in 2 s: SIGKILL through the pidfd. Today `--release` is `call_control("ForceRelease")` in `main.rs`.
4. The harness checks the brief lists (switch off refuses a listed ID; the file removed while input flows and no
   `--revoke`; the same with a clipboard read in flight; no new transfer after Off; the backend SIGSTOPped and the
   chord; labwc SIGSTOPped and `--release` by hand; a process that takes the name after the pidfd isn't killed),
   with the harness installing its own switch file in its container. Note that with the switch in, every existing
   harness test needs the switch file `on` first.
5. The harness rerun, and `UPSTREAM.md`'s row for 1b.

**Then** step 1c (Fable: the labwc shortcuts patch and the legacy chord's removal), step 2 (build stage and output
check), step 3 (the image), step 4 (VM checks 2 to 9), as the brief's "Steps" says.

## For linux-aresos

Every commit of this package that touches `os/` outside `os/input-portal/`, or `.github/`; `os/ci/` included.
The lead sends this list when step 3 ends and at the final head.

| File | Commit | Why |
|---|---|---|
| (none in step 1) | | |

## For linux-hub

| File | Commit | Why |
|---|---|---|
| (none in step 1) | | |

## Rules from `linux-aresos` for the later steps (2026-11-21)

- Keep the "For linux-aresos" list above complete (every commit touching `os/` outside `os/input-portal/`, and
  `os/ci/`).
- Don't touch `os/ci/vm.py` unless the step needs it. When a later step does, run
  `python3 -B reviews/27-first-update-release/rebind.py pending "<B321 note>"` after that commit, and never check out
  `pending-rebind.json` first.
- Keep the list "Image differences" below complete as the image work lands.

## Image differences (for later steps to complete)

What the image gains or changes through this package, for `linux-aresos`'s release notes and checks.

- The Rust build stage and its output (step 2): not built yet.
- The installed binary `/usr/libexec/aresos-input-portal` and its service file (step 2): not built yet.
- `os/input-portal/` kept out of the layer the final image inherits (`os/.containerignore`, step 2): not done yet.
- Deskflow's start hook in the session (step 4, the owner's answer T455): not built yet.

## CI dispatches

None in step 1 (0 of the package's 8).

## Podman, after step 1

No image was built or removed. The two builds ran in throwaway containers (`--rm`) on the existing builder image;
the cached one used the two cache volumes 316 left (`aresos-input-portal-registry`, `aresos-input-portal-target`).
The harness ran on `localhost/aresos-input-portal-harness:316` and `localhost/aresos-labwc:311e`, both only read.
No `prune`.
