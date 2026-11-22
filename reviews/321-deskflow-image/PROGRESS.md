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
| `92916a6b` | `UPSTREAM.md`'s row, `KNOWN-LIMITS.md`, this file, and the evidence (`evidence/step1b-build.txt`, `evidence/step1b-harness/`, added with `-f`). |

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

## Step 1c, shortcuts during a capture: done (2026-11-21, Claude Fable 5.2)

Built on step 1b's head with `main` merged in (`73f72d23`: B323's one-layer labwc swap and PR136, no conflict).
"What to build" 6 is done: the second labwc patch, the marks in the harness's `rc.xml`, the backend's own chord
removed, and the gate in the harness. Fable because it is compositor code on the keyboard path (the brief's call).

Two Fable agents built it. The first wrote the patch, the stage, the harness and this section's plan, ran two pin
builds and was stopped by its usage limit with nothing committed. The second read that diff against the brief and
labwc 0.9.6's source before trusting it ("The second agent's read", below), wrote the pins, and ran everything
under "What was shown".

| Commit | What |
|---|---|
| `fc81fccf` | `os/labwc/`: the second patch, the lock (two patches, `aresos2`, new pins), `stage.py` for a list of patches; `os/tests/test_labwc_stage.py`. |
| `0ae53900` | `os/ci/image-checks.sh`: the image check names both patches and the new NEVRA. |
| `aa56738d` | The backend's Ctrl+Alt+Escape chord removed; the harness's bindings and marks, its layer-surface test client and test10. |
| `0b1f9339` | `UPSTREAM.md`'s row, `KNOWN-LIMITS.md`, this file, the evidence. |

### The mechanism: layer focus, by the capture surface's namespace

**Picked: the layer-focus gate.** While a layer-shell surface whose namespace is `aresos-input-barrier` holds the
keyboard exclusively, labwc runs only keybinds marked `allowWhenInhibited="yes"`.

**Why, against the inhibitor** (`keyboard-shortcuts-inhibit-unstable-v1` offered only to an exclusive layer
surface, `Activated` only after labwc's `active`):

- **Smaller, and nothing new on the keyboard path of either program.** The patch is 58 added lines in six files of
  labwc, and one test (`seat_bindings_inhibited`) that reads the state at each key or button and keeps none of its
  own. The inhibitor needs a new global in labwc, a listener per inhibitor, `active`/`inactive` sent from every
  place layer focus changes (focus, unmap, a higher layer, the session lock), and in the backend a new protocol
  object, two more states in the grab and the handling of `inactive`: about twice the compositor code plus backend
  code that sees every keystroke, each with its own races to review.
- **The gate cannot be out of step with the focus.** It is true exactly while labwc's seat says the capture surface
  has the keyboard: the same fact that sends the keys there. It starts with the `enter` the backend waits for before
  `Activated` (step 1's "the grab is held"), and ends with the commit that gives the keyboard back or with the
  surface. An inhibitor's `active` is a second piece of state that labwc would have to keep in step with it.
- **What the inhibitor would add is a refusal to capture on a labwc without the patch.** Here the backend cannot
  see the patch, so that guarantee comes from the build instead, four times over: the stage refuses a binary that
  is not the lock's pins, the image check names both patches and finds the patch's strings in the binary, the
  harness refuses another labwc and runs the gate, and a unit test ties the namespace in the patch to the backend's.
  The first patch (311's pointer lock) is already carried on the same terms. Recorded in `KNOWN-LIMITS.md`.
- **Who can switch bindings off is the same either way:** a program that can put an exclusive layer surface on
  screen (by claiming the namespace here, by asking there). Windows cannot, sandboxed programs get no layer-shell
  from labwc, and the two marked chords and the VT switch stay (`KNOWN-LIMITS.md`).

Not picked up: making the namespace a setting in `rc.xml`. It would make the patch easier to offer upstream, but
the gate would then depend on a second file that `linux-aresos` owns and a user's own `rc.xml` could drop.

### The second agent's read

The diff was read against "What to build" 6 and against labwc 0.9.6 with both patches applied, before any of it was
run. The layer-focus gate is kept, and the patch, the stage, the lock's new shape, the tests and the harness are the
first agent's, unchanged. What was checked in labwc's source:

- **Every place a binding's action can start from a key or a button** (`actions_run`'s callers): the keybind match,
  the on-release branch and the repeat timer in `keyboard.c`; press, release, drag and scroll in `cursor.c`. All
  are behind `seat_bindings_inhibited()`. The others are menus and window rules (no key reaches them: the menu and
  switcher keys are skipped) and the touch and tablet taps (`KNOWN-LIMITS.md`). The gate sits where bindings are
  matched, not in `src/action.c` as the brief's note has it: `actions_run` also serves menus and window rules.
- **The gate follows the focus in every way the focus can go:** `seat->focused_layer` is cleared on unmap and
  destroy, a change away from exclusive turns the gate off by the test on `current.keyboard_interactive`, another
  exclusive layer surface of the same or a higher layer replaces it, and under a session lock the seat's keyboard
  is on the lock surface, which the gate compares.
- **Keys across the two edges of a capture.** Held before, released during: labwc keeps the last matched keybind
  until the next press, so without the patch's drop any release during a capture could run a stale on-release
  action; with it none can. Pressed during, released after: the press matched nothing, so nothing is pending.
  A repeat timer started before finds no match and runs nothing.
- **No new crossing starts in menu, switcher or move mode:** `cursor_update_common` gives no surface the pointer
  then. An enter already sent can still start a capture (review finding 4).

Changed by the second agent: two comments in the backend that still listed the removed chord among the ways a
capture is lost (`src/wayland/state.rs`, `src/portal.rs`). Added: the control run on `aresos1` and the comparison of
the two RPMs (both under "What was shown").

### What step 1c built

**`os/labwc/0002-no-bindings-for-the-capture-layer.patch`** (labwc 0.9.6, applied after 0001; code only: no man
page or example file, so every other file of the RPM stays Fedora's).

| Where | Change |
|---|---|
| `src/seat.c`, `include/labwc.h` | `seat_bindings_inhibited()`: the focused layer surface has the namespace, asks for the keyboard exclusively, and is the surface the seat's keyboard is really on (labwc sets `focused_layer` also when a session lock kept the keyboard). |
| `src/config/rcxml.c`, `include/config/keybind.h` | The keybind attribute `allowWhenInhibited` (default no), beside `allowWhenLocked`. Mouse bindings have no mark: none runs. |
| `src/input/keyboard.c` | Unmarked keybinds are skipped where a key is matched, so the key is not "bound": press and release go to the surface, and no repeat timer starts. A keybind pressed before the capture loses its pending release action (labwc keeps the release, as it kept the press), and its repeat finds nothing to run. Menu and window-switcher keys are not handled. The VT switch is checked before all of this, as before. |
| `src/input/cursor.c` | No mousebind on press, release, scroll or drag; the event goes to the surface under the pointer. A drag begun before the capture is dropped. |

**`os/labwc/stage.py` and `labwc.lock.json`.** The lock's `patch` object became the list `patches` (in the order
applied; the file names must sort that way), and a `.patch` file in the folder that the lock does not name stops
the build. The spec gets one `Patch<n>:` line each. `os/tests/test_labwc_stage.py`: 131 tests (126 before).

**The release tag moved: `aresos1` to `aresos2`** (`labwc-0.9.6-1.fc44.aresos2.x86_64`). One tag names one set of
patches: `aresos1` (311's patch alone) is on main today, and `rpm -q labwc` must tell which labwc runs. (Release
plan, 2026-11-21: this package rides R29 and gates its cut, so R29 ships `aresos2` and the laptop goes from R28's
Fedora labwc straight to `aresos2`; `aresos1` never reaches the laptop.) The image check, the stage and R29's release rule all compare the NEVRA, so a second build under the old tag
would pass checks written for the first. Fedora's package notes put the NEVRA into both binaries
(`.note.package`), so `labnag`'s pins changed too although its code did not (checked against `aresos1`'s
`labnag`: only `.note.package` and `.note.gnu.build-id` differ, every other section is the same bytes;
`evidence/step1c-labwc-rpm-compare.txt`).

**The new pins** (two `--no-cache` builds of the `labwc` stage printed the same four hashes, then written by hand,
as `stage.py`'s `PIN_RENEWAL` says; a third build passed them and is `localhost/aresos-labwc:321c`):

| | `/usr/bin/labwc` | `/usr/bin/labnag` |
|---|---|---|
| normalized SHA-256 | `93d6d36f91442438131843ddbfca4d050052038256509c129f88ce1756a9e0cb` | `b8958beab24f41e21cbdf2e052d45c93cf95454a2c06c11bd03578c12c049505` |
| loaded-image SHA-256 | `52cd76e644e8cec4922959648e4096e5fbcc4643b0d8db8d8fa335cee709a402` | `5538d4c5a6989c2c4ec826c76c1e7901ea0b4fc8f4bcc5e7e76472480d7bff49` |

The RPM of the third build: `ee6257dbbeff0bf07e9205cf02a2cb4e1da9568e8d6c6f16c1c15e57c243055c` (not reproducible, as 311's: build time, host and build ID).

**The backend** (`os/input-portal/src/wayland/state.rs`): `is_panic_key` and the modifier state it read are gone.
During a capture Ctrl+Alt+Escape is forwarded like every key; the way out is labwc's binding. No new unit test
(the key handlers need a compositor): test10 shows the chord at the client and the capture still held.

**The harness** (`os/input-portal/harness/`):

- `in-container.sh`: `rc.xml` marks `W-S-Escape` and `W-C-Escape` (`--release`, then a stand-in for the recovery
  terminal) and binds, unmarked, what the image binds: `A-F4` Close, `A-Tab` NextWindow, volume, mute and brightness
  keys, a lone `Super_L` that acts on release, and two mouse bindings in the `All` context (`A-Middle` press,
  `A-Down` scroll), since only those apply over a layer surface. Each test command writes one line to
  `bindings.log`. The default mouse bindings stay (`<default />`).
- `clients/wl-harness.c`: `wl-harness layer NAMESPACE`, an overlay layer surface that asks for the keyboard
  exclusively; the probe window prints `CLOSE` when labwc asks it to close.
- `driver.py`, test10 (26 checks), in "What was shown" below.
- `run.sh`, `Containerfile`: the images are `localhost/aresos-labwc:321c` and
  `localhost/aresos-input-portal-harness:321c`; `HARNESS_IMAGE` names another harness image.

### What was shown

- **The labwc stage** (`evidence/step1c-build.txt`): two `--no-cache` builds with `aresos1`'s pins still in the lock
  applied both patches, printed the same four hashes and stopped (`LABWC_REFUSED`); with the hashes written by hand
  a third `--no-cache` build passed (`LABWC_BUILT labwc-0.9.6-1.fc44.aresos2.x86_64`, 10 min 35 s) and is
  `localhost/aresos-labwc:321c`. Against `aresos1`'s RPM (`evidence/step1c-labwc-rpm-compare.txt`): the same 64
  paths but the two `.build-id` links, and only `/usr/bin/labwc` and `/usr/bin/labnag` have other bytes.
- **The stage's tests:** `test_labwc_stage.py` **131 passed** (126 before); `test_shell_assertions.py` 9 passed. The
  image check's two `grep` lines were tried on both binaries: `aresos1`'s has neither string, `aresos2`'s has both.
  The whole of `image-checks.sh` runs only in the hosted check build ("CI dispatches").
- **The backend:** `dev/container.sh build` without `--cache` on `aa56738d`: no compiler warning,
  `cargo test --locked --offline` **98 passed, 0 failed** (unchanged). Binary SHA-256
  `569d2a26582cc85eefbda463db32765a50419380c748fa0b32e5ac941177c0b4`.
- **The harness** (`evidence/step1c-harness/`, on that binary, `localhost/aresos-labwc:321c` and
  `localhost/aresos-input-portal-harness:321c`): **129 passed, 0 failed**, twice with the same PASS lines: step 1b's
  103 and test10's 26. Test10:
  - outside a capture (5, the controls): the media keys and a lone Super run their commands, so do Alt+Middle and
    Alt+scroll, Alt+F4 asks the probe window to close, Alt+Tab starts the window switcher, Super+Ctrl+Escape runs
    the terminal's stand-in;
  - the capture starts (1);
  - during it (6): Alt+F4; Alt+Tab, then Tab and Down; a lone Super; volume, mute and brightness; Ctrl+Alt+Escape;
    Alt+Middle and Alt+scroll. Each time no test command ran, the window was not asked to close, the client got
    every key and button, and the key typed right after reached the client;
  - the capture held through all of them, Ctrl+Alt+Escape included (no `Deactivated`), and the local window got
    nothing (1);
  - Super+Ctrl+Escape released it and ran the terminal's stand-in, and input was local again (2);
  - a lone Super held as a capture starts ran no release action; a held volume key repeated outside a capture
    (the control) and ran nothing in 1.5 s when held as a capture started; the next key reached the client each
    time; input was local after (4);
  - a layer surface named `harness-other-layer` got the keyboard exclusively and under it the media keys, the lone
    Super, the mouse bindings and Alt+F4 all acted; one named `aresos-input-barrier` got the same keys with nothing
    run, and Super+Ctrl+Escape still ran there; with both gone the bindings act (7).
- **Super+Shift+Escape under the gate** is test3's and test9's (both pass with the marked binding): the capture
  ends, and test3's INFO line shows the client got Super and Shift and never Escape.
- **The control: test10 fails on a labwc without the patch** (`evidence/step1c-harness-control-aresos1/`). The same
  driver, `rc.xml` and binary on `localhost/aresos-labwc:311e` (`aresos1`, main's labwc then; in a harness image built
  against `aresos1`'s lock and removed after): 120 passed, **9 failed**, all of them test10's gate. Alt+F4 asked
  the local window to close; the switcher took Tab and Down; the lone Super, the media keys and both mouse
  bindings ran their commands and those keys and buttons never reached the client; the held Super ran its release action; the
  held volume key kept repeating; the layer surface named `aresos-input-barrier` kept the bindings. Test10's other
  17 pass there too: the controls, the marked chord, and Ctrl+Alt+Escape (that one is the backend's change).
- **Not committed from the harness runs:** as in step 1b, the EIS receivers' logs, the probe window's log, the
  virtual devices' logs and the signal dumps, and now the two layer clients' logs: they hold the harness's made-up
  keys. `bindings.log` (the names of the test commands that ran) is committed. The control's `results.txt` is
  committed whole: its nine FAIL lines list the probes' own key codes (the constants in `driver.py`).

### What the code doesn't show

- **The VT switch during a capture is read, not run.** labwc checks it before the gate, in code the patch does not
  touch; the harness's labwc is headless and has no VT. Step 2's VM runs switch a VT; step 4's table should press
  Ctrl+Alt+F3 during a real capture.
- **No new crossing starts while a menu, the window switcher or a window move is active.** In those modes labwc
  gives no surface pointer focus (`cursor_update_common`). A crossing already sent can still activate after a
  mode change (review finding 4, in `KNOWN-LIMITS.md`).
- **Media keys go to the Mac** (the owner's answer T459): `rc.xml` gets no mark for them, and test10 shows volume,
  mute and brightness at the client with nothing run on the laptop.
- **The marks are only in the harness's `rc.xml`.** The image's `rc.xml` gets its two bindings' marks in step 3
  (`linux-aresos`'s file); until then the image's labwc would gate everything, the recovery terminal included.
  Step 3's image check should require exactly those two marks.
- **For the release rule (`linux-aresos`):** R29's rule for 311 compared the NEVRA `aresos1`, the pins and "every
  other file byte-exact". R29 carries this package, so its rule takes `aresos2` and the pins above; the file list (64 paths) and every
  file but `/usr/bin/labwc`, `/usr/bin/labnag` and the two `.build-id` links are unchanged by this patch.
- **`os/Containerfile`'s comment on the labwc stage still says "one upstream fix".** The file is `linux-aresos`'s
  and the stage needs no new line, so it was not touched ("For linux-aresos").
- **The patch is not offered upstream yet.** As it stands it names AresOS's namespace; an upstream version would
  take the namespace from `rc.xml` or be the inhibitor protocol. For the lead to decide after the final review.

## Step 1c review fixes

| Finding | Fix or triage | Commit | Test |
|---|---|---|---|
| 1. A program can claim the capture namespace | Recorded checking the Wayland peer's executable as possible later hardening. | `2afd7585` | Test10 still shows that a different namespace keeps its bindings and the capture namespace gates them. |
| 2. Session lock during capture | Recorded the limit and when to revisit it. The image has no screen locker. | `2afd7585` | Lead's triage, documentation only. |
| 3. Previous window can veto the marked chords | Recorded the `ToggleKeybinds` limit. The image has no binding for that action. | `2afd7585` | Lead's triage, documentation only. |
| 4. Already-sent crossing can activate in the switcher or menu | Recorded the gap between pointer enter and capture commit. | `2afd7585` | Lead's triage, documentation only. |
| 5. Pointer-only capture can outlive the gate | Recorded that it forwards no keys and Deskflow asks for the keyboard. | `2afd7585` | Lead's triage, documentation only. |
| 6. Input-method grab and modifier state | Recorded the limit and when to revisit it. The session starts no input-method program. | `2afd7585` | Lead's triage, documentation only. |
| 7. Recovery chord needs a working terminal | One `sh -c` waits for release to return and then opens a new Wayland probe window. Labwc 0.9.6's `Execute` calls `spawn_async_no_shell`, which uses `g_shell_parse_argv` and `execvp`. The image's XML is under “For step 3” below. | `e2236fa5` | Test10 saw the new window receive the next key press and release during both runs. A separate rootless shell control printed `release exited 17` followed by `recovery launched`. |
| 8. Harness and image need to prove binary identity | Both check the installed `/usr/bin/labwc` and `/usr/bin/labnag` against the loaded-image and normalized pins with `stage.py check-installed`. The harness sends the checkout lock on each run. CI sends the checker and reads the manifest lock, whose equality with the checkout lock is still checked. | `5b6c14da` | All four hashes matched in both harness runs and the stage image check. A scratch lock with a zeroed loaded-image pin for `/usr/bin/labwc` gave `LABWC_REFUSED` and exit 1 before any harness test started. |

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p test_labwc_stage.py` reported
  `Ran 131 tests` and `OK`. The same discovery command with `test_shell_assertions.py` reported `Ran 9 tests`
  and `OK`. No `__pycache__` remained under `os/config`.
- `bash -n` exited 0 for each of `os/input-portal/harness/run.sh`, `os/input-portal/harness/in-container.sh`,
  `os/ci/check-image.sh` and `os/ci/image-checks.sh`.
- `os/input-portal/harness/run.sh run .work/backend-1c <evidence-dir>` on the existing
  `localhost/aresos-input-portal-harness:321c` printed `SUMMARY 129 passed, 0 failed, exit 0` twice with
  identical PASS lines. Each run included 26 test10 checks and also passed the 20 outer isolation checks.
- The new image-check command printed two `LABWC_NORMALIZED` and two `LABWC_LOADED` lines and exited 0
  against the RPM from `localhost/aresos-labwc:321c`. The bare build stage lacks `xdg-desktop-portal-wlr`,
  so its `rpm -V labwc` reports that missing dependency. The full labwc block emitted its new PASS line in
  the harness image, which has that dependency and the same RPM (SHA-256
  `ee6257dbbeff0bf07e9205cf02a2cb4e1da9568e8d6c6f16c1c15e57c243055c`).
- The local logs are under `.work/step1c-review-fixes/`. There are no files over 500 MB in `.work`.
  The finished-image run and the actual recovery terminal remain for the image and VM steps.

## Step 2, the image stage and output gate (2026-11-22, Codex)

- Merged package 329 from `origin/main` in `266b2469`. Its window client still closes by default. Package 321's
  probe uses `--keep-open` to observe repeated Close actions on the same window. The layer-surface probe and
  package 329's window options and protocol generation are both retained. The image uses package 329's `rc.xml`.
- The exact-revision source stage takes the backend's manifests, script, pinned toolchain settings, sources,
  data and upstream license. The Rust stage builds and tests offline after the pinned fetches. The Fedora
  image installs its binary, D-Bus service and upstream license. The layer check scans each overlay directory
  added to the base so that a later deletion cannot hide a copy of the source, toolchain or harness.
- The throwaway Deskflow layer adds `wlr-randr`, the listen-only client and guest checks. The VM pass uses the
  standard q35 and virtio-vga setup with a private QEMU display bus and fresh disk overlays for the three
  client states and three custom-mode controls. It records the DRM connector and labwc state, compositor PID,
  regular mode cycles, VT switches and backend geometry. The lead's `os/ci/vm.py` was unchanged.
- The signed Deskflow RPM gate **passed again**. `rpmkeys -Kv` against a separate keyring with Fedora 44's key
  returned OK for signature, header and payload. `rpm -qp` gave `deskflow-0:1.27.0-1.fc44.x86_64`, SHA-256 was
  `21a404d8bd0488fdc7ec635ed26447d623b132dc4ae3d12e5f944991ab76484b`, and `readelf --dyn-syms --wide`
  showed both undefined imports `xdp_session_selection_read` and `xdp_session_selection_write`.
- The **DRM output gate is unverified**. The hosted Deskflow run stopped during the shared Cosign install.
  Its bootstrap download of Cosign v2.5.2 timed out with curl exit 28 before the image-build step. The
  queued standard build was cancelled under the stop rule for failures outside this package. Step 3 has
  no DRM gate result to proceed on.

### Verified locally

- Two fresh `os/input-portal/dev/container.sh build` runs, without cache volumes: **98 passed, 0 failed** in
  each. `cmp` found identical binaries at SHA-256
  `31bb05de96bad26264d2466e486b82cc95e5b994d0c6a230d63a82568d43b0f4`. The release check requires this pin.
- A clean rootless `podman build --no-cache --target input-portal` from the pushed revision `bd5082dd`
  successfully fetched the exact tree, ran all **98** backend tests and printed the same binary hash.
- Rebuilt the merged client with `os/input-portal/harness/run.sh image` and ran `harness/run.sh run` twice with
  `localhost/aresos-input-portal-harness:321-step2` and the checked `aresos2` labwc. Both runs returned
  **129 passed, 0 failed**. Checks for tests 1 through 10 were **18, 8, 9, 8, 3, 8, 15, 16, 5, 26** each time,
  plus 13 setup, isolation and review checks. The headless control still aborts at `--on` with the listen-only
  client and with the backend, and survives with no persistent output-manager client. This is the existing
  custom-mode failure that the hosted DRM gate tests separately.
- `python3 -m unittest discover -s os/tests -p test_input_portal_layers.py`: **3 passed**. The test confirms
  that a leaked source or toolchain file is found even when it is hidden by a later layer.
- The same discovery command for `test_aresos_desktop.py`: **189 run, 1 skipped**. The initial run found the
  old expected stage list. The updated assertion requires the pinned Rust stage. `test_labwc_stage.py`:
  **131 passed**. `test_shell_assertions.py`: **9 passed** after making the dependency failure an explicit
  exit. `test_ci_api_permissions.py` and `test_ci_step_environment.py`: **4 passed** each.
- Shell syntax checks passed on the modified scripts. A Python fixture of the VM's mode check accepted
  the requested 59.998 Hz mode and rejected a same-size 60 Hz mode. No Python cache directory was created
  under `os/config/`.
- `mod/dev/build.sh` reported **BUILD SUCCESSFUL** and **106 required server game tests passed**.
  The first `mod/dev/client-test.sh … build` attempt waited for the shared client-test lock. It was stopped
  before launching a client after the hosted failure. The two full client passes remain outstanding.

### What the code doesn't show

- The check layer enables geometry logging through the guest session's D-Bus activation environment and saves
  its compositor output. Step 3 still has to demonstrate activation and routing through the real frontend in
  the image without that test setup.
- The upstream MIT license is installed. The linked-crate notices still need a license inventory before
  release. The build fetches target-specific and build-time crates as well, so the fetch alone does not
  identify which notices are required for the shipped binary.
- The physical monitor, lid, suspend and VT behavior need the owner's laptop rehearsal. If the VM cannot
  verify a second connector, the brief requires the physical hotplug rehearsal before publication.

## Left, in order

1. Once the shared Cosign bootstrap is available, run the hosted `deskflow` and `build` modes at the
   final step 2 head, record the regular, hotplug, VT and custom-mode outcomes, and record the DRM gate
   decision. Confirm the installed backend hash in both hosted builds and verify the scan of the image layers.
2. When the gate permits, step 3 installs Deskflow, proves its ID and changes its scope name, allow-list and
   routing, then adds the release key, switch, helper, polkit actions, window, desktop entry and image checks.
   The helper writes `on\n` atomically, root-owned and mode 0644, in root-owned `/etc/aresos/input-portal` (0755).
   The switch program runs `aresos-input-portal --revoke` after `off`.
3. Step 4 runs VM checks 2 to 9 and records the laptop rehearsal, as the brief's "Steps" says.

### For step 3

Mark exactly `W-S-Escape` and `W-C-Escape` with `allowWhenInhibited="yes"` in the image's `rc.xml` and require
exactly those two marks in the image check. Use one `Execute` for release and terminal launch, and keep the
separate hide-cover action. labwc executes each action asynchronously. Inside `sh -c`, `;` waits for release to
return and then opens the terminal regardless of the release status.

```xml
<keybind key="W-C-Escape" allowWhenInhibited="yes">
  <action name="Execute" command="/usr/bin/sh -c '/usr/libexec/aresos-input-portal --release; exec /usr/bin/aresos-terminal --recovery'" />
  <action name="Execute" command="/usr/libexec/aresos-desktop hide-cover" />
</keybind>
```

Use `/usr/bin/sh` by its absolute path, as every other command in the image's `rc.xml` is named (image-checks.sh's
startup-commands scan reads absolute paths). Then update the assertions that still expect the recovery chord's
command as a direct `Execute` of `/usr/bin/aresos-terminal --recovery`: `os/tests/test_everyday_account.py` (about
lines 112 and 232), `os/tests/test_aresos_desktop.py` (about line 3495) and `os/ci/image-checks.sh` (about lines 579
and 908). Package 329 (the window frame) takes this exact XML as its baseline once it is on main (its brief review,
`reviews/329-window-frame/`).

## For linux-aresos

Every commit of this package that touches `os/` outside `os/input-portal/`, or `.github/`; `os/ci/` included.
The lead sends this list when step 3 ends and at the final head.

| File | Commit | Why |
|---|---|---|
| (none in steps 1 and 1b) | | |
| `os/labwc/0002-no-bindings-for-the-capture-layer.patch` (new) | `fc81fccf` | Step 1c: the second labwc patch. While the backend's capture surface (layer namespace `aresos-input-barrier`) holds the keyboard exclusively, only keybinds marked `allowWhenInhibited="yes"` run and no mousebind. Code only (`src/`, `include/`). |
| `os/labwc/labwc.lock.json` | `fc81fccf` | `patch` became the list `patches` (both files with their SHA-256); `result.nevra` is `labwc-0.9.6-1.fc44.aresos2.x86_64`; all four pins are new (table in step 1c above). Base, source and the 306 build dependencies are unchanged. |
| `os/labwc/stage.py` | `fc81fccf` | Reads the list of patches (order by file name, one `Patch<n>:` line each), refuses a `.patch` file the lock does not name, release suffix `.aresos2`, the reviewed NEVRA. Nothing else changed: fetch, the environment check, the pins and the install are as 311 left them. |
| `os/tests/test_labwc_stage.py` | `fc81fccf` | The stage's tests for the above (131, 126 before), and two for the lock: the patch's namespace equals the backend's, and the second patch touches code only. |
| `os/ci/image-checks.sh` | `0ae53900` | The labwc check: NEVRA `aresos2`, the manifest lock names exactly the two patches in order, and `/usr/bin/labwc` holds the second patch's two strings (`allowWhenInhibited`, `aresos-input-barrier`). |
| `os/labwc/stage.py` | `5b6c14da` | Reuses the stage's hash check for installed binaries through `check-installed`. |
| `os/ci/check-image.sh`, `os/ci/image-checks.sh` | `5b6c14da` | Sends the pin checker into the CI container and verifies both binaries against the manifest lock before reporting PASS. |
| `os/config/usr/share/aresos/labwc/rc.xml`, `os/ci/image-checks.sh` | `266b2469` | Merge package 329's window frame and frame checks while keeping package 321's labwc checks. |
| `os/build.sh`, `os/tests/test_aresos_desktop.py` | `8ccf806b` | Extract only the backend's build inputs from the exact source revision. |
| `os/.containerignore` | `5c2d8ae0` | Keep the portal tree out of the layer inherited from the package stage. |
| `os/manifest/input-portal.sha256` | `ae27ebdf` | Pin the binary from the two byte-identical local builds. |
| `os/Containerfile` | `d93198bd` | Build the backend on its pinned Rust image, install the binary, service and license, and enforce the release hash. |
| `os/ci/image-checks.sh` | `1da81ea8` | Verify installed ownership, modes, exact service and license, runtime libraries and recorded binary digest. |
| `os/ci/check-image.sh`, `os/ci/deskflow/check_layers.py`, `os/tests/test_input_portal_layers.py` | `32baca1f` | Compare the Rust builder to its pin and scan every added image layer, with tests for concealed files. |
| `os/ci/toolchain.json` | `d01a7d36` | Pin the Ubuntu package carrying QEMU's `ui-dbus.so` at the existing QEMU version. |
| `os/ci/deskflow/{Containerfile,actions.py,deskflow_vm.py,session}` | `68b42c7a` | Build the isolated check layer and run the six DRM output scenarios in fresh boots. |
| `os/ci/check-build.sh` | `270aa6f8` | Build the Deskflow test disk and run its dedicated pass. |
| `.github/workflows/os-image.yml` | `bd5082dd` | Add `check_build=deskflow` to the read-only throwaway build job. |
| `os/tests/test_aresos_desktop.py` | `663009fb` | Require the locked Rust stage in the image wiring test. |
| `os/ci/image-checks.sh` | `2b67a00c` | Fail explicitly if the runtime linker reports missing libraries. |
| `os/ci/deskflow/deskflow_vm.py` | `e4668391` | Verify the mode's advertised refresh rate and restore the virtual connector before falling back to PCI. |

Not touched in step 1c: `os/Containerfile` (the stage copies the whole `labwc/` folder, so the second patch needs no
new line; its comment above the stage still says "one upstream fix" and should name both patches when the file is
next changed), `os/ci/vm.py`, `os/packages.lock.json`, the image's `rc.xml`. **For `linux-aresos`'s release rule:** the
lock's shape changed (`patch` to `patches`) and the NEVRA and pins moved; a rule written for `aresos1` must be
re-aimed at `aresos2`: R29 carries this package (release plan, 2026-11-21) and gates its cut.

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

- **labwc (step 1c):** the RPM is `labwc-0.9.6-1.fc44.aresos2.x86_64` (R28 has Fedora's `labwc-0.9.6-1.fc44`; `aresos1` is
  on main only and never ships), built with both patches.
  Changed files: `/usr/bin/labwc` (the patch; pins in step 1c above), `/usr/bin/labnag` (only the NEVRA in its
  `.note.package`), and so the two `.build-id` links. Same 64 paths; every other file is Fedora's, byte for byte.
  New behaviour: bindings are off while the input portal's capture surface holds the keyboard, except keybinds
  marked `allowWhenInhibited="yes"` (a new `rc.xml` attribute; step 3 marks two). Without a capture nothing changes.
  The image check names both patches. Real hardware first at the release's laptop install, as 311's rule says.
- **Input portal (step 2):** `/usr/libexec/aresos-input-portal` (0755) and
  `/usr/share/dbus-1/services/org.freedesktop.impl.portal.desktop.aresos-input.service` (0644), owned by root.
  The image also gains `/usr/share/licenses/aresos-input-portal/LICENSE` and
  `/usr/share/aresos/manifest/input-portal.sha256`. Release builds require the backend's binary pin.
- The Rust toolchain and `os/input-portal/` source tree stay in the builder path. The listener, `wlr-randr`
  and the session log capture are part of the throwaway check layer.
- Deskflow's start hook in the session (step 4, the owner's answer T455): not built yet.

## CI dispatches

None in steps 1 and 1b.

| # | Step | Run | What |
|---|---|---|---|
| 1 of 8 | 1c | `44935351683`, on `0b1f9339` (dispatched 2026-11-21 19:24) | `check_build=build` on the step's head: it builds the labwc stage (the pins must hold on the hosted runner too) and the image, and runs the image checks, the labwc one included. **Green** (the lead, 2026-11-21 20:22). |
| 2 of 8 | 1c review fixes | `44937064135`, on `7d38fa7b` (dispatched by the lead 2026-11-21 19:44) | `check_build=build` after fix 8: image-checks.sh now runs `stage.py check-installed` against the manifest lock, piped in by check-image.sh. **Green** (2026-11-21 21:25). |
| 3 of 8 | 2 | [45000469287](https://github.com/Ares-Empire/AresOS/actions/runs/45000469287), on `bd5082dd` (2026-11-22 08:56 CET) | `check_build=deskflow`. **Failed before image build**. Pinned tools installed, then the common `sigstore/cosign-installer` timed out downloading its v2.5.2 bootstrap binary (curl exit 28). `gh run watch 45000469287 --exit-status --interval 60` returned 1. |
| 4 of 8 | 2 | [45000755789](https://github.com/Ares-Empire/AresOS/actions/runs/45000755789), on `a04a693c` (2026-11-22 09:00 CET) | `check_build=build`. **Cancelled before any workflow steps** after run 3's external failure. `gh run watch 45000755789 --exit-status --interval 60` returned 1 and GitHub reports `cancelled`. |

## Podman, after step 2

Rootless throughout, with one container at a time. Kept the merged harness image
`localhost/aresos-input-portal-harness:321-step2` (`f82ab04e39ea`). Removed the first step 2 harness image
(`2db7970a522d`) and the locally verified Rust-stage image (`9163afe8d485`) by name or ID with
`podman rmi --no-prune`. Reused the existing `localhost/aresos-labwc:321c` with both pinned binaries.
No file under `.work/` is larger than 500 MB.

## Podman, after step 1c

Built and kept: `localhost/aresos-labwc:321c` (`936d94a84d10`, the third build; the harness and step 2 need it) and
`localhost/aresos-input-portal-harness:321c` (`d1b0057d999c`). Built and removed: the control's harness image
(`localhost/aresos-input-portal-harness:321c-control`, with its one own layer). `localhost/aresos-labwc:311e` was
only read (the control and the RPM comparison); `localhost/aresos-input-portal-harness:316` was not used.

Dangling layers of the builds that are kept, as build cache: the third build's `labwc-inputs` stage
(`f1d2de0dc8d6`, `64aa955d5af5`, `bc7acf20d33a`, `61397b12d036`), the two parents of `321c` (`3bdf42b1cb0c`,
`c8f538d7c56a`) and the harness image's (`24bb1a939ee9`, `5da4ff03b446`, `58839b6909b3`, `6847eafc8677`).

Left for the lead, not touched: the dangling layers of the two refused pin builds (the first agent's). Build 1:
`4e0e27c2256a`, `ec6d0a541cee`, `445d4ac8a064`, `43c03b4be1fb`, `34725236915e`, `6f8170a691fa`. Build 2:
`5ca13dcd314f`, `1a47c49af60d`, `f61cf7553362`, `e13e4809f0b9`, `47bda253d393`, `ce83cfb38b9e`. Nothing uses them:
the third build ran with `--no-cache`.

Everything ran in throwaway containers (`--rm`), the harness without a network. The counted backend build used no
cache volume (316's two are untouched). No `prune`. Nothing in `.work/` is over 500 MB; `.work/backend-1c/` is the
counted backend build, `.work/backend-cached/` the first agent's cached one from before the comment change.

## Podman, after step 1b

No image was built or removed in step 1b. The builds ran in throwaway containers (`--rm`): the cached one on the two
cache volumes 316 left, the counted one without them. The harness ran twice (once on the cached build while
iterating, once on the counted binary) on the same two images, only read. No `prune`.

## Podman, after step 1

No image was built or removed. The two builds ran in throwaway containers (`--rm`) on the existing builder image;
the cached one used the two cache volumes 316 left (`aresos-input-portal-registry`, `aresos-input-portal-target`).
The harness ran on `localhost/aresos-input-portal-harness:316` and `localhost/aresos-labwc:311e`, both only read.
No `prune`.
