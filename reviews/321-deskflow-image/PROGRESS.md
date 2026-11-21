# 321 Deskflow in the image: progress

Brief: `briefs/321-deskflow-image.md`. Branch `pkg/321-deskflow-image`, draft PR133 into `main`. Limits:
`KNOWN-LIMITS.md` here (316's file stays). Evidence: `evidence/`.

## Step 1, the backend: done up to the brief's split point (2026-11-21, Claude Opus 5.5)

Built from `main` at `27169226`. The brief's split point was taken: item 9's five follow-ups with their tests are
done (and two of the brief's own small items with them); the rest of "What to build" 1 is step 1b (below).

| Commit | What |
|---|---|
| `b4e6069f` | The five follow-ups, the empty-ID refusal and the watchdog default, each with a unit test (79 in all, 72 before). |
| `535e0bba` | `UPSTREAM.md`'s row, `KNOWN-LIMITS.md`, this file. |
| `cea32bc6` | The evidence (`evidence/step1-build.txt`, `evidence/step1-harness/`), added with `-f` as 316's was (the repo ignores `evidence/` and `*.log`). |

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

## Step 1b, the rest of the backend: done (2026-11-21, Claude Opus 5.5)

Built on step 1's head with `main` merged in (`c22e4847`). Everything of "What to build" 1 that step 1 left is done:
the switch with its checks, the reread and the 2-second Off deadline, `--revoke`, the clipboard recheck after the
wait, `ForceRelease` answering after the compositor's confirmation, `--release` with its pidfd, and the harness
checks. No image file changed.

| Commit | What |
|---|---|
| `6d2c1cbf` | The switch, the gate, the Off teardown and its deadline, `--revoke`, the clipboard recheck, the confirmed `ForceRelease` and `--release`'s pidfd, each with a unit test (98 in all, 79 before); the harness's switch file and its 21 new checks. |
| the commit after `6d2c1cbf` | `UPSTREAM.md`'s row, `KNOWN-LIMITS.md`, this file, and the evidence (`evidence/step1b-build.txt`, `evidence/step1b-harness/`, added with `-f`). |

### What step 1b built (`os/input-portal/src/`)

| | Change | Its unit test |
|---|---|---|
| The switch | `sharing.rs`, `Switch::read`: `/etc/aresos/input-portal/sharing` is on only when it is a regular file of root's, not writable by group or others, at most 64 bytes, reading `on` (one line end allowed), opened with `O_NOFOLLOW` (a symlink fails) and `O_NONBLOCK` (a FIFO can't hold the read), and every folder above it up to `/` is a real folder (no symlink) of root's that group and others can't write. Anything else is off; a missing file or folder is off and not "suspicious" (logged at info, the rest at warn). | `the_switch_is_on_only_for_on`, `a_missing_switch_is_off_and_not_suspicious`, `a_switch_file_someone_else_could_have_written_is_off`, `an_unsafe_folder_above_the_switch_turns_sharing_off` |
| The checks | `portal.rs`, `State::switch_locked`, called under the state's lock: when a session is made (after the allow-list, so step 3's window can come after the ID check), at `Enable`, at each crossing before `Activated`, in every clipboard method (`RequestClipboard`, `SetSelection`, `SelectionWrite`, `SelectionWriteDone`, `SelectionRead`), and in the three clipboard events (a local copy, a local paste of a session's claim, a cancelled claim). Off refuses with `AccessDenied("sharing is off")`. | `with_sharing_off_a_listed_application_gets_no_session`, `enable_and_each_crossing_read_the_switch`, `every_clipboard_call_reads_the_switch` |
| Off ends everything | An Off read closes the gate (`sharing::Gate`, an atomic flag) first and then, under the same lock, every session: capture, barriers, EIS connection, clipboard claim and parked transfers, plus `EndCapture`/`Disarm` for anything captured. The Wayland thread's `forward` and each EIS connection's writes read the gate before every event, so forwarding stops at once, also for what is already queued. The gate opens again only on an On read under the lock, so never while a session from before the Off is left. | `turning_sharing_off_ends_everything_without_revoke` (state), `a_closed_gate_drops_input_even_inside_a_capture_run` (EIS) |
| The reread | `watch_switch`: every 250 ms (`SWITCH_INTERVAL`; the brief's bound is 500 ms) while any session exists. | `turning_sharing_off_ends_everything_without_revoke` (no `--revoke`, the timer alone) |
| The 2-second deadline | After an Off read that closed sessions, the backend asks the Wayland thread for a `wl_display.sync` behind the teardown (`WaylandCmd::Sync`, `WaylandHandle::confirm`); no `done` within 1 s (`CONFIRM_TIMEOUT`) and the backend stops (`stop_serving`), and labwc drops the grab with the connection. Budget: 250 ms + 1 s + the 150 ms grace (`SHUTDOWN_GRACE`) < 1.6 s. | `off_unconfirmed_by_the_compositor_stops_the_backend`, `off_takes_effect_within_the_two_second_deadline` |
| `--revoke` | Control method `Revoke`: reads the switch now and answers once the compositor has confirmed (or says the backend stops). With the switch on it changes nothing, so anyone may call it. `--revoke` asks the running backend's unique name and starts none (no bus activation). | `revoke_reads_the_switch_now_and_answers_after_the_compositor` |
| The clipboard recheck | `selection_read` reads the switch and checks the session again after its wait for the Wayland thread; refused, the pipe is dropped there. | `a_clipboard_read_hands_out_no_descriptor_if_sharing_went_off_while_it_waited` (off, and the session closed, during the wait) |
| `ForceRelease` confirmed | `force_release` (`ForceRelease`, `Disarm`) answers only after the compositor's `done` for a sync queued behind the `EndCapture` (the lock destroyed, the keyboard interactivity dropped, both committed); unconfirmed within 1 s it answers an error. | `force_release_answers_only_after_the_compositor_confirms` |
| `--release` | `release.rs`: the owner of the backend's name (`GetNameOwner`), pinned as a pidfd from `GetConnectionCredentials` (`ProcessFD`, or `pidfd_open` on `ProcessID` and a second `GetNameOwner` that must name the same connection); `/proc/<pid>/exe` must be `/usr/libexec/aresos-input-portal` and all four UIDs the caller's, read before the pidfd is asked whether the process still runs. `ForceRelease` goes to the pinned unique name, not the well-known one. No confirmed answer within 2 s (`DEADLINE`): SIGKILL through the pidfd; a pinned process that has ended is reported and nothing is signalled. No backend running: says so, exit 0. | `the_numbers_come_from_proc`, `a_pidfd_from_elsewhere_gives_its_pid`, `only_the_installed_program_of_this_user_passes`, `the_kill_reaches_the_pinned_process_and_no_other` |

`Cargo.toml`: `rustix` gains the `process` and `event` features and `tokio` names `time` (which it already got
through `zbus`). Neither adds a crate: `Cargo.lock` is unchanged, and the build ran `--locked --offline`.

### The harness (`os/input-portal/harness/`)

`in-container.sh` installs the switch `on` (root's, 0644, folders 0755) before the driver starts, and records the
folders' modes in `versions.txt`; a setup check confirms it. Every existing test runs with it on. `driver.py` gains
`test8` (the switch) and `test9` (the way out), run after `test1`'s output-off part:

- test8: the listed ID refused with the switch removed, saying `ON`, a symlink to a file saying `on`, and its folder
  writable by everyone; the switch removed while keys and motion flow, no `--revoke`: `Deactivated` and `Closed`
  within 2 s (seen 0.13 s after), nothing at the receiver from the 2 s mark on, EIS disconnected, input local, the
  next crossing local, the backend still running (labwc confirmed); a `SelectionRead` sent to a SIGSTOPped backend,
  the switch removed, SIGCONT: no descriptor; after Off no `SelectionTransfer` for a local paste, `SelectionWrite`,
  `SelectionRead` and `SetSelection` refused with no descriptor, a local copy announced to nobody; `--revoke` with
  the switch on changes nothing, right after the removal it answers with the session already closed; labwc
  SIGSTOPped and the switch removed: the backend exits with an error within 2 s (seen 1.37 s), and after SIGCONT the
  input is local.
- test9: the backend SIGSTOPped, the chord pressed: labwc's `--release` kills it through its pidfd after its 2 s
  (exit -9), input local; labwc SIGSTOPped, `--release` by hand: the backend's confirmation times out, `--release`
  kills it (exit -9), and after SIGCONT the input is local; a first backend SIGSTOPped, `--release` started and
  stopped right after it printed its pin, the first backend killed, a second one started on the name, `--release`
  continued: the second is neither asked (`ForceRelease requested` not in its log) nor killed, and `--release` says
  the pinned one had already ended.

### What was shown

- **Build and tests** (`evidence/step1b-build.txt`): `dev/container.sh build` without `--cache` on `6d2c1cbf`: no
  compiler warning, `cargo test --locked --offline` **98 passed, 0 failed** (79 before, 19 new). Binary SHA-256
  `48feb9e7987a199b5adfe0d2aa51438cdd9d6e810f2b03c57cc95929ed27844f`. The cached build used while working gave
  `77d0be8b…` before the last change to `--release`'s message (which way it pinned); that one is not counted.
- **Harness** (`evidence/step1b-harness/`, on that binary, with `localhost/aresos-labwc:311e` and
  `localhost/aresos-input-portal-harness:316`, both unchanged and only read): **103 passed, 0 failed**: 316's 81 checks, one setup
  check for the switch and test8's 16 and test9's 5. The removal seen 0.12 s (`Deactivated`) and 0.13 s (`Closed`) after
  the file went; with labwc stopped the backend exited 1.37 s after. The harness's bus (Fedora's `dbus-daemon`) gave a
  `ProcessFD`, so `--release` pinned through it (`labwc.log`). An earlier run on the cached build also gave 103 of
  103.
- **Not committed from the harness run:** the EIS receivers' logs (`eis-*.log`), the probe window's log
  (`window.log`), the virtual devices' logs and the signal dumps (`signals-*.json`). They hold the harness's own
  made-up keys, motion, cursor positions and clipboard text, and the lead's rule for this step keeps keys,
  coordinates and clipboard text out of every evidence file. `results.txt` is committed whole; its one INFO line about
  the chord lists the chord's own key codes (Super, Shift, Escape), as in step 1. Step 1's evidence has those files.

### What the code doesn't show

- **The Wayland thread's two new parts have no unit test.** The gate check in `forward` and the `wl_display.sync`
  for `WaylandCmd::Sync` need a compositor; the harness shows both (no input at the receiver after Off; the backend
  stays up when labwc confirms, and exits or is killed when labwc is stopped). That `done` comes only after labwc has
  handled the lock's destruction and the keyboard-interactivity commit rests on Wayland's in-order processing of one
  client's requests: the sync is queued behind them on the same connection.
- **"Within 2 seconds" is measured from the harness's side**, from the file's removal to the moment the driver read
  the signal, so it is an upper bound.
- **`--release`'s fallback pin is not run against a bus.** The harness's `dbus-daemon` gives a `ProcessFD`, so the
  harness ran that path (`labwc.log`: "pinned by the bus's ProcessFD"). The other path (`pidfd_open` on `ProcessID`,
  then a second `GetNameOwner`) has the unit tests of `Pinned::open` and the kill, not a harness run. The image's
  session bus is `dbus-run-session`'s `dbus-daemon` from the same Fedora, so the laptop should take the same path as
  the harness; step 3's VM run will show it in the journal.
- **Off seen at a check point, not by the timer, doesn't wait for the compositor in the call.** The confirmation then
  runs on a task of its own (the call is refused at once); only `--revoke` waits for it before answering.
- **The empty-ID refusal and the watchdog default** were step 1's; nothing changed there.

## Left, in order

**Step 1c** (Fable: the labwc shortcuts patch of "What to build" 6 in 311's stage, the mechanism picked and why, the
marks in the harness's `rc.xml`, the backend's side if the inhibitor is the pick, the legacy chord's removal, and the
gate in the harness). Note for it: the harness's `rc.xml` (in `harness/in-container.sh`) binds only `W-S-Escape`;
test9's chord check expects labwc's `--release` to kill a stopped backend, so its marks must keep that binding live
during a capture.

**Then** step 2 (build stage and output check), step 3 (the image: Deskflow, its ID and scope name, the allow-list,
routing, the release key, the switch's helper, polkit actions, window and desktop entry, image checks), step 4 (VM
checks 2 to 9), as the brief's "Steps" says. For step 3, from this step: the helper writes the switch as
`on\n` (the backend accepts `on` with or without one line end) in one rename, mode 0644, root's, in
`/etc/aresos/input-portal` (0755, root's), and the switch's program runs `aresos-input-portal --revoke` after `off`.

## For linux-aresos

Every commit of this package that touches `os/` outside `os/input-portal/`, or `.github/`; `os/ci/` included.
The lead sends this list when step 3 ends and at the final head.

| File | Commit | Why |
|---|---|---|
| (none in steps 1 and 1b) | | |

## For linux-hub

| File | Commit | Why |
|---|---|---|
| (none in steps 1 and 1b) | | |

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

None in steps 1 and 1b (0 of the package's 8).

## Podman, after step 1b

No image was built or removed in step 1b. The builds ran in throwaway containers (`--rm`): the cached one on the two
cache volumes 316 left, the counted one without them. The harness ran twice (once on the cached build while
iterating, once on the counted binary) on the same two images, only read. No `prune`.

## Podman, after step 1

No image was built or removed. The two builds ran in throwaway containers (`--rm`) on the existing builder image;
the cached one used the two cache volumes 316 left (`aresos-input-portal-registry`, `aresos-input-portal-target`).
The harness ran on `localhost/aresos-input-portal-harness:316` and `localhost/aresos-labwc:311e`, both only read.
No `prune`.
