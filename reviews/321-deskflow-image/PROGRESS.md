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
- The first hosted attempt left the **DRM output gate unverified**. It stopped during the shared Cosign install.
  Its bootstrap download of Cosign v2.5.2 timed out with curl exit 28 before the image-build step. The
  queued standard build was cancelled under the stop rule for failures outside this package. Run
  45001307065 later passed the gate. See CI dispatches and the step 2 review fixes.

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
  before launching a client after the hosted failure. The two later full passes are recorded below.

### What the code doesn't show

- The check layer enables geometry logging through the guest session's D-Bus activation environment and saves
  its compositor output. Step 3 still has to demonstrate activation and routing through the real frontend in
  the image without that test setup.
- The upstream MIT license is installed. The linked-crate notices still need a license inventory before
  release. The build fetches target-specific and build-time crates as well, so the fetch alone does not
  identify which notices are required for the shipped binary.
- The physical monitor, lid, suspend and VT behavior need the owner's laptop rehearsal. If the VM cannot
  verify a second connector, the brief requires the physical hotplug rehearsal before publication.

## Step 2 review fixes

See [REVIEW-2.md](REVIEW-2.md) for the lead's record.

| Finding | Fix | Commit | Test |
|---|---|---|---|
| 1. DRM hotplug could hide a labwc failure | Poll DRM status and labwc's output list separately. Fail (c) on an unreflected DRM transition. If neither SetUIInfo nor PCI drives the connector, record the laptop rehearsal with the owner's direct OK as a publication requirement. | `db4d0b14` | `test_deskflow_vm.py` covers mismatches in both directions and the unverified branch. The hosted regular cases exercise the actual connector. |
| 2. A client could disappear during the run | Exit the listener with status 2 on the output manager's `finished` event. Check the listener and the original backend's unique D-Bus owner through the compositor check, including both VT transitions and hotplug polling. | `db4d0b14` | `test_deskflow_vm.py` checks client loss on both VT transitions. The rebuilt input-portal harness ran twice. |
| 3. Custom-mode evidence could be incomplete | Verify and record the initial set, off, and re-enable. Identify the operation that hits `head_send_state`. Report a failed readiness or unverified operation separately in the log and `result.json`. Custom cases remain outside the pass rule. | `db4d0b14` | `test_deskflow_vm.py` covers ignored operations, the expected abort, and the separate report for incomplete evidence. |
| 4. A shipped layer could hide Rust material | Scan every added layer for Rust source and artifact names and `target/` directories at any destination. | `f4c52a3c` | `test_input_portal_layers.py` includes a relocated `main.rs` hidden by a later opaque directory, plus each artifact kind. |

- `python3 -m unittest discover -s os/tests -p <file>` ran separately for `test_deskflow_vm.py` (5 passed),
  `test_input_portal_layers.py` (3 passed), and `test_shell_assertions.py` (9 passed). No `__pycache__`
  directory was created under `os/config/`.
- `os/input-portal/harness/run.sh image` rebuilt the listener on the checked labwc. Two sequential runs of
  `os/input-portal/harness/run.sh run .work/step2/backend <evidence-dir>` each reported
  `SUMMARY 129 passed, 0 failed, exit 0`. Tests 1 through 10 passed 18, 8, 9, 8, 3, 8, 15, 16, 5, and 26
  checks respectively, plus 13 setup, isolation and review checks. The backend's SHA-256 matched the manifest.
- A private Wayland fixture in the rebuilt rootless harness container sent `finished` on bind.
  The listener logged that the compositor ended `zwlr_output_manager_v1` and exited 2.
- Replaying the three regular cases' artifacts from run 45001307065 against the updated host VM
  driver passed for all three states. `mod/dev/build.sh` finished with `BUILD SUCCESSFUL` and all 106
  required server game tests passed.
- Two full `mod/dev/client-test.sh --keep-screenshots <evidence-dir> build` runs completed
  `runClientGameTest` with exit 0. Each also passed all 106 required server game tests and printed
  `BUILD SUCCESSFUL` (15m 55s and 15m 53s). The preliminary attempt with a 15-minute outer timeout
  reached the client after waiting for the shared lock and timed out before completing the suite.
  Screenshots from both full passes are in `.work/step2-review-fixes/mod-client-complete-{1,2}/`.

## Step 3, Deskflow in the image

- The initial pull confirmed that `origin/main` at `c2e94551` was already an ancestor. Main gained package
  328a (`92cf365a`) during dispatch 7. Step 4 starts with that merge and retests the combined branch.
- Saved the lead's read-only recheck verbatim in `REVIEW-2-RECHECK.md`. Before the image edits, the VM gate
  began treating loss of a previously connected DRM status node as a DRM transition, and layer scanning began
  rejecting relocated Cargo proc-macros, hashed executables and build scripts. Both have regression coverage.
- The Fedora lock adds only `deskflow-0:1.27.0-1.fc44.x86_64` and `libportal-0.10.0-1.fc44.x86_64`.
  The gate's Deskflow SHA-256, `21a404d8bd0488fdc7ec635ed26447d623b132dc4ae3d12e5f944991ab76484b`, is
  checked before install. While the exact RPM is absent from stable, throwaway resolve and build allow that
  NEVRA alone from `updates-testing`. Release mode resolves against Fedora and updates.
- The real frontend proved the native ID `org.deskflow.deskflow` in run 45009968432. The allow-list has that one
  line. The guarded native hub entry uses `app-aresos-org.deskflow.deskflow-<launch_id>.scope` and continues to send
  `org-deskflow-deskflow` in the hub protocol. D-Bus mapped the real `CreateSession2` sender `:1.105` to
  PID 2880, executable `/usr/bin/deskflow-core` and scope
  `app-aresos-org.deskflow.deskflow-3213213213213213.scope`. The backend kept the same session, enabled
  Clipboard on it and completed the EIS handshake. The identical launch outside the hub scope had an
  empty ID and was refused.
- The sharing window, desktop entry, root helper and two per-verb polkit actions are installed. The helper
  checks the root-owned path, writes `on\n` atomically with mode 0644 and removes that file for Off. The
  user entry follows Off with `--revoke`. The backend can offer the window once per session bus after an
  authorized request from the listed ID while Off. The image contains no switch file.
- A local regression after dispatch showed that a reader's advisory lock on the switch directory could stall
  Off. Commit `938a4deb` removes the dependency on a lock. Atomic replacement and removal still order concurrent
  changes in the root-owned directory. The test failed with a timeout before the fix and passed after it.
- Run 7's raw logs showed the polkit agent starting the frontend, which activated the backend during both
  regular control boots. Commit `0ce12ae3` suppresses frontend bus activation in the DRM test layer and
  checks that the backend stays absent in the two controls. The native ID check explicitly starts the real
  frontend after the DRM comparison. The production image keeps its normal activation.
- The two image bindings marked `allowWhenInhibited="yes"` are Super+Shift+Escape and Super+Ctrl+Escape.
  The recovery command waits for release and starts the terminal, with its existing separate hide-cover action.
  Package 329's theme, window switcher, title-bar scrolls and Root actions are present.

### Portal routing

The real Fedora 44 `xdg-desktop-portal-1.22.1` ran in a private `dbus-run-session` on the pinned base plus
the locked portal packages, using `XDG_CURRENT_DESKTOP=AresOS`. Before, both new files were absent. After,
the verbose log loaded `/usr/share/xdg-desktop-portal/aresos-portals.conf` for `aresos` and selected
`aresos-input.portal` for both new interfaces. The table records frontend selection. The headless routing
probe had no display, so backend operation through the real AresOS session is checked separately in the VM.
The raw observations are in `.work/step3/rootless-image-inputs.log`.

| Interface | Before | After |
|---|---|---|
| Access | gtk | gtk |
| Account | gtk | gtk |
| AppChooser | gtk | gtk |
| Background | none | none |
| Clipboard | none | aresos-input |
| DynamicLauncher | gtk | gtk |
| Email | gtk | gtk |
| FileChooser | gtk | gtk |
| GlobalShortcuts | none | none |
| Inhibit | gtk | gtk |
| InputCapture | none | aresos-input |
| Lockdown | none | none |
| Notification | gtk | gtk |
| Print | gtk | gtk |
| RemoteDesktop | none | none |
| ScreenCast | none | none |
| Screenshot | none | none |
| Secret | none | none |
| Settings | gtk | gtk |
| Usb | none | none |
| Wallpaper | none | none |

### Verified locally

- The pinned base downloaded and compared all 32 RPMs against the reviewed lock. Signature checks held when
  installing just Deskflow, libportal, grim and xdg-desktop-portal-wlr in the throwaway container.
  Both new packages were absent from the base. The existing `UPGRADES-BASE` candidates are libblkid (both
  architectures), libfdisk, liblastlog2, libmount (both), libsmartcols, libuuid (both), util-linux and
  util-linux-core, all from 2.41.5-1.fc44 to 2.41.6-1.fc44.
- The gated `deskflow-core` imports `xdp_portal_create_input_capture_session2_sync`,
  `xdp_session_selection_read` and `xdp_session_selection_write`. The check layer adds `wlr-randr` and the
  existing Wayland listener. Step 4's client and clipboard fixtures still need to demonstrate the traffic path.
- Two clean, rootless `os/input-portal/dev/container.sh build` runs each passed 98 backend tests and produced
  byte-identical binaries with SHA-256 `931b3dc54e1797209b08980eca8e256bfe9599b9de32c80890468547f8ea1247`.
  Two sequential `os/input-portal/harness/run.sh run` runs on the existing `321-step2` harness image
  each reported `SUMMARY 129 passed, 0 failed, exit 0`. Tests 1 through 10 passed 18, 8, 9, 8, 3, 8,
  15, 16, 5 and 26 checks, plus 13 isolation, setup and review checks.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p <file>` ran once per module at
  the dispatched code. `test_deskflow_vm.py` passed 6, `test_input_portal_layers.py` 3, `test_input_sharing.py` 4,
  `test_shell_assertions.py` 9, `test_everyday_account.py` 36, `test_aresos_shell.py` 76,
  `test_aresos_shell_discovery.py` 37, `test_aresos_shell_icons.py` 43, and
  `test_aresos_shell_protocol.py` 21. `test_aresos_desktop.py` ran 189 and passed 188, with one skip
  because the environment supplied no reachable user systemd manager. After `938a4deb`,
  `test_input_sharing.py` passed 5 and `test_shell_assertions.py` passed 9. No `__pycache__` under `os/config/`.
- A temporary profile built with `QSettings` showed TLS and peer checking enabled despite both source
  values saying false. It kept one valid fingerprint and refused a second. `mod/dev/build.sh` reported
  `BUILD SUCCESSFUL` and all 106 required server game tests passed.
- Two full runs of `mod/dev/client-test.sh --keep-screenshots <evidence-dir> build` completed
  `runClientGameTest` and passed all 106 required server game tests each. Both returned 0 and printed
  `BUILD SUCCESSFUL` (15m 58s and 16m 29s). Each evidence directory under
  `.work/step3/mod-client-{1,2}/` holds 105 screenshots. The worktree's generated snapshots were cleaned up.
- The extracted Fedora image rules with the new policy passed `polkit-check.js` in a rootless throwaway
  container (403 actions). Replacing Off's `exec.argv1` with `on` failed the same check.
- The final switch helper ran at its installed path inside the rootless harness. It wrote root:root 0644
  in a root:root 0755 directory. Off finished while an unprivileged fixture still held an advisory lock on
  that directory. Both verbs refused a symlink and a writable parent. The fixture printed
  `INPUT_SHARING_REAL_PATH_PASSED`.
- After `0ce12ae3`, `test_deskflow_vm.py` passed 7 and `test_shell_assertions.py` passed 9. A rootless pinned-base
  probe removed the frontend activation file from its container, got `ServiceUnknown` on bus activation,
  and then ran the frontend directly to acquire its bus name. It printed `DESKFLOW_FRONTEND_ISOLATION_PASSED`.
  The corrected layer still needs a hosted rerun.

### Judgment call

The hub runs the native server core with a private runtime copy of the Deskflow profile. It uses Qt's
`QSettings` from the pinned base, sets TLS and peer checking in the copy and refuses a trust list with
multiple or malformed fingerprints. An empty list leaves the server with no trusted peer. The normal
Deskflow GUI can edit the source profile and configure the server layout. The guarded hub launch uses the
saved layout and certificate. The other approach was a check when launching the GUI, where the security
checkboxes could still change before the GUI starts its core. A guarded GUI would need an explicit server
launch hook or a change to Deskflow itself.

### What the code doesn't show

- The owner must compare and enrol the Mac's fingerprint. The launch code can enforce the count and syntax
  of trusted fingerprints. The laptop rehearsal verifies which peer the one fingerprint belongs to.
- The start hook, end-to-end password prompts, real input and clipboard transfers, capture and release keys,
  restart behaviour, Flatpak control, logging and TLS negative controls are step 4's real-session evidence.
- The upstream MIT license is in the image. The linked Rust crates' notice inventory is open before
  publication.

## Step 3 review fixes (2026-11-22, Claude Opus 5.5)

The three BLOCKING findings of `REVIEW-3.md`, as the lead triaged them. Started 12:22 CET at `18e224b2`
(`origin/main` was not merged in this round: step 4 starts with that merge, see "Left, in order"). No CI dispatch.

| Commit | What |
|---|---|
| `450c48f8` | Finding 1: the backend's Wayland worker starts only for an authorized session while sharing is On (`os/input-portal/src/`). |
| `8da79ac5` | Finding 1: harness test8 counts the backend's Wayland connections from outside; `UPSTREAM.md`'s row. |
| `121ee33b` | The backend's new pin (two byte-identical clean builds). |
| `d01f335d` | Finding 3: pairing through the guarded launcher, with its tests (`os/tests/test_aresos_deskflow.py`). |
| `67f69117` | Finding 2: the image's own `org.deskflow.deskflow.desktop`, opening the guarded launcher. |
| `6dbb7a89` | Finding 2: `os/build.sh` keeps Fedora's copy of that entry out (RPM net shared). |
| `313aba4c` | Finding 2: the image check asserts the effective entry, its `Exec` and a clean `rpm -V deskflow`. |
| `05cf9f05` | Finding 1: the VM gate with normal activation, the worker started by the real Deskflow, and the return to Off. |

### Finding 1: the Wayland worker stays stopped while sharing is Off

- **Fix.** `serve` no longer connects to the compositor. The bus side (InputCapture, Clipboard, Control) answers
  the frontend's discovery and the control commands and refuses sessions while Off, as before. `CreateSession` and
  `CreateSession2` start the worker (`wayland::start`, the same thread as before: output management, layer shell,
  pointer constraints, clipboard data control) only after the frontend, empty-ID and allow-list checks, and only
  when a read of the switch under the state's lock says On; the session is then stored under a second read. The
  worker stops (its handle dropped: `Shutdown` after the commands already sent, then the thread returns and its
  connection closes with every binding) when a read of the switch says Off (the 250 ms timer now also runs while
  only a worker exists, `--revoke`, and every place that already read the switch), and when no session needs it
  (`Close`, the frontend leaving or changing owner, a dead EIS connection, a refused or failed `CreateSession`).
  Off keeps step 1's order: sessions closed, `EndCapture` and `Disarm` sent, then the worker is taken out and the
  compositor's confirmation awaited on it within 1 s; unconfirmed, the backend exits as before. Only then is the
  worker dropped. Kept: one armed session, teardown, `--revoke`, `--release` with its pidfd fallback (with no worker
  `ForceRelease` answers at once: no connection can hold anything), the forwarding gate, an unexpected end of the
  running worker's connection still ends the process. Events of a stopped worker are dropped (generation check in
  the pump), and crossing numbers come from one counter shared by all workers, so a late event can't name a later
  crossing. A worker that isn't ready within 8 s fails the session and holds nothing else.
- **Tests.** 4 new unit tests (102 in all): no worker for a refused, unlisted, empty-ID or stranger's request or
  while Off; Off/On/Off (timer Off: worker taken out at once, stopped after the confirmation; On: a new worker;
  `--revoke` Off: stopped again); the worker stops when no session needs it (teardown first, then `Shutdown`; also
  on the frontend leaving and on a new frontend owner); a stopped worker's events reach no later session. Six
  existing tests were re-aimed where the last session's teardown now stops the worker (a crossing on its way finds
  nothing to send to; `stop_serving` now releases before it closes).
- **Harness** (`os/input-portal/harness/run.sh`, image `localhost/aresos-input-portal-harness:321-step2`), on the
  counted binary: see "Verified locally" below for the two counts. New test8 checks, read from outside the backend
  (each socket descriptor copied with `pidfd_getfd` and asked for its peer): no Wayland connection with the switch On
  and no session, nor while Off after four refused requests; one while an authorized session runs; none within 1 s
  after the switch is removed; one again for the next session after On, none after Off. The output control now
  opens a session so the backend is bound (it showed `1 Wayland connection`, and labwc aborted at step 2 as before).
- **VM gate** (`os/ci/deskflow/`, not dispatched in this round). The test layer keeps the frontend's activation
  file, as the image ships it (0ce12ae3's removal is undone), so every boot is a first boot with normal activation:
  `ready` records `first_boot_backend` (the backend's Wayland connections if the frontend started it, else none)
  and fails on any connection; the DRM controls' check changed from "no backend" to "no backend on Wayland". The
  backend state stops a login-activated backend (it ran at the default log level), turns sharing On with the
  helper, checks no connection without a session, then starts the real frontend, a `CreateSession2` monitor and
  Deskflow under the hub scope and keeps them for the boot: the worker has one connection, and `check_compositor`
  requires it through every DRM operation. The identity check reuses that caller (sender, PID, executable, scope),
  then turns sharing Off with Deskflow connected: `--revoke` answers, the session is gone, the backend keeps its bus
  name and has no Wayland connection (`off` in the result). Then the terminal launch is refused for its empty ID.
  `test_deskflow_vm.py`: 9 (7 before; the control test re-aimed, two new).
- **What the code doesn't show.** The VM gate's new paths have run only as unit tests: the hosted run is step 4's.
  In the backend state Deskflow now pairs (empty fixture trust list): it makes a certificate with `openssl` and opens
  the core's IPC channel; nobody connects, so no dialog appears. If the real core in the VM did not open its IPC
  socket, the launcher would stop it and the backend state would fail at readiness: read the core log in the
  evidence first. The custom-mode limit now needs Deskflow's live session with sharing On.

### Finding 2: every desktop-entry launch of Deskflow uses the guarded launcher

- **The way chosen.** The desktop ID must stay `org.deskflow.deskflow` with an existing `<ID>.desktop`, `/usr/local`
  is not in a bootc image, and editing Fedora's file in place shows in `rpm -V` (`S.5....T.`, tried). So
  `os/build.sh` sets, for the locked install alone, the rpm macro `%_netsharedpath` to that one path: RPM installs
  no copy and records the file as `net shared`, which `rpm -V` skips (tried with rpm 6.0.2 and dnf5 in a throwaway
  Fedora 44 container: dnf5 honours the macro, state `net shared`, `rpm -V` rc 0). The macro file is removed right
  after; the build fails if a `_netsharedpath` was already set or if anything else is net shared. The image's own
  entry (`os/config/usr/share/applications/org.deskflow.deskflow.desktop`: Fedora's text, translations included,
  with `Exec=/usr/libexec/aresos-deskflow`) takes the path from `config/`. The hub's catalogue entry is unchanged.
- **Image check.** `image-checks.sh` (with `check-image.sh` sending the repo's entry in): root 0644 and identical to
  the repo's; the only `org.deskflow.deskflow.desktop` under `/usr`, `/etc` and `/var`; every `Exec`, actions
  included, is the launcher; no other `TryExec`, no D-Bus activation; exactly that one file net shared and
  `rpm -V deskflow` empty; `/usr/bin/openssl` present. Its parser passed on the repo's entry and failed on
  Fedora's (`Exec=deskflow`) locally.
- **What the code doesn't show.** Not yet run in a built image (step 4's dispatch). A per-user entry in
  `~/.local/share/applications` and `deskflow` typed in a terminal stay possible; the latter's core has an empty ID
  and is refused (KNOWN-LIMITS).

### Finding 3: a guarded first-use pairing

- **Fix.** `aresos-deskflow` pairs when no Mac is saved, or with `--enroll`. It starts the server with TLS and the
  peer check on and an empty trust list (also with `--enroll`: the saved Mac is not trusted meanwhile), connects to
  the core's own IPC channel (Deskflow 1.27's `deskflow-core` socket; it answers a hello with its version and then
  replays what it queued) and reads `peerFingerprint=`, which the core sends for every TLS peer before it checks the
  trust list. For each new peer a `kdialog --yesno` shows its fingerprint as Deskflow's own window shows one (byte
  pairs with colons, eight to a line) and this laptop's, for the Mac to check: "It matches" / "It doesn't match".
  Only a confirmed fingerprint is saved, as the single `v2:sha256:` entry (0600, one rename), and copied into the
  running server's profile, which the core rereads at every connection, so the Mac's next try gets in; a refused
  peer isn't asked about again in that run; nothing else is ever written. A profile that never ran Deskflow's window
  gets a server certificate made as Deskflow's window makes one (RSA 2048, self-signed, `CN=Deskflow`, 365 days, key
  and certificate in one PEM, 0600) with `openssl`. The core's `TMPDIR` is now the private runtime folder, so its IPC
  socket (Deskflow opens it to everyone, `WorldAccessOption`) is the owner's alone. A core that doesn't open its
  channel within 10 s is stopped and the launcher reports it. A saved list with two or malformed entries is refused
  with a pointer to `--enroll`.
- **Tests.** `os/tests/test_aresos_deskflow.py`, 6, with a stand-in core (it opens the IPC socket in the TMPDIR it
  is given, answers the hello as 1.27 does, reports fingerprints, records what the running server trusts) and a
  stand-in dialog, the real `openssl`: from an empty profile whose settings turn TLS and the peer check off, only the
  confirmed Mac is saved and trusted by the running server, asked once, the stranger never asked after it; the
  certificate is made and its fingerprint shown; TLS and the peer check on in the core's copy, `TMPDIR` private,
  Wayland only. Nothing is trusted without a confirmation; `--enroll` replaces the saved Mac only when confirmed and
  trusts nobody meanwhile; a saved Mac starts the server without a dialog or channel; two entries are refused; a core
  without its channel is stopped.
- **What the code doesn't show.** The real core's IPC replies were read from Deskflow 1.27's source
  (`src/lib/deskflow/ipc/`, `src/lib/net/SecureSocket.cpp`), not observed: step 4 runs the real core against a
  Deskflow client in the VM. The Mac's side (its own dialog for the laptop's fingerprint) is the owner's, laptop
  test 3.

### Verified locally (step 3 review fixes)

- Backend: `os/input-portal/dev/container.sh build` (as the image stage builds it) passed 102 unit tests cached and
  in two clean rootless builds, whose binaries are byte-identical, SHA-256
  `ef3d09781e34e82fcd2a3db2cb025a8d9fef3f295eea6f177813a26479da23df` (pinned in `121ee33b`).
- Harness, twice in a row on that binary (`HARNESS_IMAGE=localhost/aresos-input-portal-harness:321-step2
  os/input-portal/harness/run.sh run`): each `SUMMARY 132 passed, 0 failed, exit 0` (129 before). Tests 1 to 10
  passed 18, 8, 9, 8, 3, 8, 15, 19, 5 and 26 checks, plus 13 setup, isolation and review checks; test8's three new
  checks are the Wayland-connection ones. The output control printed `the backend is connected (1 Wayland
  connection, a session open)` and the expected labwc abort, as before. An earlier run on the cached build: 132, 0.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p <file>`, once each: `test_aresos_deskflow.py`
  6, `test_deskflow_vm.py` 9, `test_input_portal_layers.py` 3, `test_input_sharing.py` 5, `test_shell_assertions.py`
  9, `test_everyday_account.py` 36, `test_aresos_desktop.py` 189 (OK, 1 skip: no reachable user systemd manager).
  No `__pycache__` under `os/config/`.
- The net-shared exclusion with rpm 6.0.2 and dnf5 in a throwaway Fedora 44 container (above), and the image
  check's entry parser on both entries (above). `bash -n` on `os/build.sh`, `os/ci/image-checks.sh` and
  `os/ci/check-image.sh`.
- Not run: any image build, the image checks in an image, the VM gate (step 4's dispatch).

## Step 3 review fixes, round 2

Followed the lead's triage in [REVIEW-3-RECHECK.md](REVIEW-3-RECHECK.md) on the draft PR #133 branch. This
round ran locally. The hosted gate belongs to step 4.

| Finding | Commit | Fix and verification |
|---|---|---|
| 1. Worker startup and shutdown | `0aab2216` | The process keeps its sole worker from launch through exit. The worker reads the switch just after connecting, before binding globals. The watcher sees a worker blocked in startup. Off closes the forwarding gate and every session. Off and the last session closing both end the capture and disarm, then exit after labwc's confirmation, with a one-second confirmation deadline. Concurrent release and revoke wait for that outcome. On an unconfirmed release the existing pidfd fallback still applies. The unit races used an in-process recorded Wayland worker. In harness test8, real labwc and D-Bus showed the old process exiting and an Off discovery call activating a fresh backend with zero Wayland connections. The harness frontend and input are fixtures. |
| 1. VM gate | `dad6e205` | A vanished descriptor can be ignored. Other `pidfd_getfd` errors fail the check. The identity action checks the original process's exit via its pidfd and then checks a fresh bus-only backend. `test_deskflow_vm.py` exercises real socket counting and injects the error returns. The hosted gate is pending. |
| 1. Backend pin | `ca6be85f` | Two clean builds each passed 102 unit tests and produced byte-identical binaries, SHA-256 `0c609b6a9571bb0c14d7e9dc8710c691be49e9e3a718c54cbd6c3282fb8e11fb`. Both harness runs used that binary. |
| 2. Image RPM verification | `a7fadb4e` | The image runs `rpm -V deskflow` directly with errexit. The shell regression substitutes RPM returning 0 or 42 without output and verifies that the latter stops the image check. The manual package replacement limit is in [KNOWN-LIMITS.md](KNOWN-LIMITS.md). |
| 3. Default pairing decision | `ece7b993` | The pairing prompt is a Qt message box whose default and Escape buttons both reject. The acceptance button has auto-default disabled. The unit tests drive the real offscreen prompt with Qt Test and a stand-in core. The isolated integration below used both real cores and the real prompt. |

KDialog assigns the same Yes/No buttons to the question and warning forms, and Qt lets a focused auto-default
button take over Enter. An explicit reject default and a deliberately selected acceptance button keep the existing
wording and make the decision independent of KDialog's button ordering. [KDialog button setup](https://github.com/KDE/kdialog/blob/v26.08.1/src/kdialog.cpp#L431)
[Qt dialog key handling](https://github.com/qt/qtbase/blob/v6.11.2/src/widgets/dialogs/qdialog.cpp#L758)

### Verified locally

- `os/input-portal/dev/container.sh build`, twice without `--cache`, in the pinned rootless Rust image.
  Both printed `102 passed; 0 failed` and the SHA-256 above. `cmp` succeeded and the duplicate output was removed.
- `HARNESS_IMAGE=localhost/aresos-input-portal-harness:321-step2 os/input-portal/harness/run.sh run`, twice.
  Both printed `SUMMARY 133 passed, 0 failed, exit 0`. Tests 1 through 10 passed 18, 8, 9, 8, 3, 8, 15, 20,
  5 and 26 checks, with 13 setup, isolation and review checks. Both runs reproduced the known labwc custom-mode
  control abort with the listen-only client and the connected worker. The no-client control survived.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p <file>`, one module at a time.
  `test_aresos_deskflow.py` 6, `test_deskflow_vm.py` 10, `test_shell_assertions.py` 10,
  `test_everyday_account.py` 36, and `test_aresos_desktop.py` 189 (one existing skip for an unreachable user
  systemd manager). No `__pycache__` under `os/config`. `bash -n` passed for the image check and both harness
  shell scripts.
- Pairing integration, `podman run --rm --network=none` on a throwaway rootless image with the locked Fedora
  Deskflow RPM (1.27.0-1.fc44) and PySide6 6.11.2. The fixture files and log are in `.work/step3-round2/`.
  A private D-Bus session, two private Xvfb displays and isolated loopback supported real `deskflow-core server`
  and `deskflow-core client` processes. The server began with an empty source profile. Three client profiles
  used distinct real certificates. `QT_QPA_PLATFORM=offscreen` and Qt Test drove the actual pairing prompt.
  Enter and clicking “It doesn't match” each left both trust files absent. Clicking “It matches” saved exactly
  the approved fingerprint to each file. The approved certificate was accepted on reconnect and another
  certificate was refused, with the trust files unchanged. The fixture printed `PAIRING_SUMMARY 5 passed 0 failed`.
  Xvfb stood in for the display and input transport, and Qt Test for the owner's actions. The cores, TLS,
  fingerprint IPC, launcher, dialog and trust-file writes were real.
- Removed the throwaway pairing image. There were no files over 500 MB in this worktree's `.work/`.

## Step 4 — Login, daily-use VM checks and handoff (2026-11-22, Codex)

- Merged `origin/main` at `92cf365a` into the package branch as `6bb9f0d2`. Preserved the round-2 review verbatim in
  `REVIEW-3-RECHECK-2.md`. Harness test8 pins the reactivated process before Off and waits for pidfd readability.
  Its revoke result records completed teardown.
- labwc's login hook reads the root-owned switch and uses the hub's `ScopeLauncher` for the image catalogue's
  Deskflow entry. The scope is `app-aresos-org.deskflow.deskflow-<hex>.scope` and runs the guarded server without
  opening Deskflow's settings window. Both launch paths share the same single-server lock. A live core normally
  stops on portal Closed, with a watchdog for Off when the signal cannot arrive.
- The guarded core still uses Deskflow's default Info level. Deskflow 1.27's Info messages for a crossing and an
  active peer disconnect include coordinates. The launcher removes those coordinates before relaying the messages
  and disables direct file logging in the private snapshot so the same messages cannot bypass the filter.
- The backend sends releases for keys it has forwarded and still holds when emulation ends while sharing is On.
  The recovery chord takes the keyboard back before physical key-up events, and Deskflow 1.27 ignores EIS
  StopEmulating for keyboard state. The new frame is sent before StopEmulating. Off closes the existing forwarding
  gate and the EIS connection.
- `check_build=deskflow` retains all six DRM controls. The daily-use pass uses the real greetd session,
  xdg-desktop-portal, polkit and guarded Deskflow server plus a loopback TLS Deskflow client under Xvfb. It records
  each completed check and binding in `daily-checks.jsonl`, and retains only summaries from the input recorders
  and privacy scanner. Two further boots reuse the throwaway disk to check persistence.
- **Judgment call.** The login hook follows T455 at login. A switch change to On in an existing login takes effect
  on the next hub launch or login. Using a persistent autostart supervisor would add a process that relaunches apps
  during the login; this version can adopt that later through the same scoped entry.
- **Plan gap.** The brief expected default Info to omit input coordinates. The pinned RPM emits them on both
  crossing and disconnect, so the guard filters those messages. Keep the format review with future RPM changes.
  [Deskflow 1.27 server source](https://github.com/deskflow/deskflow/blob/v1.27.0/src/lib/server/Server.cpp)

### Verified locally

- Ran each package-touched Python module with `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p <file>`.
  The final summaries total 574 tests across 12 modules, with one existing user-systemd skip.

  | Module | Tests | Result |
  |---|---:|---|
  | `test_aresos_deskflow.py` | 12 | OK |
  | `test_aresos_desktop.py` | 189 | OK, 1 skip |
  | `test_aresos_shell.py` | 76 | OK |
  | `test_aresos_shell_discovery.py` | 37 | OK |
  | `test_aresos_shell_icons.py` | 43 | OK |
  | `test_aresos_shell_protocol.py` | 21 | OK |
  | `test_deskflow_vm.py` | 11 | OK |
  | `test_everyday_account.py` | 36 | OK |
  | `test_input_portal_layers.py` | 3 | OK |
  | `test_input_sharing.py` | 5 | OK |
  | `test_labwc_stage.py` | 131 | OK |
  | `test_shell_assertions.py` | 10 | OK |

  The first layer run carried a rejected directory into later subtests. Each artifact now has a fresh layer.
  The labwc stage test still expected the pre-Deskflow package invocation. It now also requires the current build
  kind and the absence of the Rust source in the installed stage. No `__pycache__` directories under `os/config`.
- Two clean rootless builds with `os/input-portal/dev/container.sh build` printed `102 passed; 0 failed` each.
  `cmp` confirmed both binaries were byte-identical. The digest is
  `00e8ff021c7978c6ed7548e050f23734d4e198bcbcebebe8d51157545d28cb57`.
- Before the EIS fix, the previous pinned binary ran the new test10 and printed `SUMMARY 134 passed, 1 failed, exit 1`.
  The one failing check had both modifier presses followed by StopEmulating and no key-up events.
- `mod/dev/build.sh` passed in 2m 43s and 1m 55s. Gradle recorded 339 unit tests (333 passed, 6 platform
  skips) and both builds printed `All 106 required tests passed`. The full 30-entry `mod/dev/client-test.sh`
  passed in 14m 15s and 14m 11s. The two native pointer checks have a separate headless-labwc run below.
- `bash -n`, Python syntax checks and `git diff --check` passed. The round-2 recheck body matches the lead's
  original file byte for byte.

- With the previous backend before the EIS change, the repaired 133-check harness passed twice. With the final
  backend, `HARNESS_IMAGE=localhost/aresos-input-portal-harness:321-step2 os/input-portal/harness/run.sh run`
  printed `SUMMARY 135 passed, 0 failed, exit 0` twice. Tests 1 to 10 passed 18, 8, 9, 8, 3, 8, 15, 20, 5 and 28
  checks per run, with 13 setup, isolation and review checks. Both runs reproduced the known custom-mode
  compositor limit with a listener or worker attached.
- Two focused `mod/dev/client-test.sh --session --keep-screenshots … -I …` passes selected the merged
  Free Pointer and World Keeps Pointer entrypoints under the native headless labwc fixture. Both passed
  (2m 39s and 2m 48s), including the native pointer probe and actual Escape/focus transitions. Their
  screenshots are saved in `.work/step4/native-1/` and `.work/step4/native-2/`. Generated changes to the
  other reviews' screenshots and the standalone native test's bytecode were cleared from the worktree.

### Laptop test for the owner

After the final review and release, get the owner's direct OK and have the owner save work before the first test.

1. Start with sharing Off. Record labwc's PID. With the portal available for discovery, switch the external
   display off and on in a listed mode. Unplug and replug it three times, close and open the lid, suspend and
   resume, and switch to a VT and back. Confirm the same labwc PID and that the displayed outputs recover.
2. Find **Mouse and keyboard sharing** in the hub. Turn it On using the password prompt. Open Deskflow from the
   hub for this login. A subsequent login while On should start the guarded server by itself.
3. Configure the server layout with the Mac's exact Deskflow screen name if the setup has no layout yet. Leave
   TLS enabled on both ends. Clear the server's saved client list for the first pairing. Point the Mac at the
   laptop's AresOS address and check the laptop's displayed fingerprint on the Mac if prompted. Compare the
   fingerprint in the AresOS pairing window with the Mac's own fingerprint. Select **It matches** only after the
   comparison. Confirm the saved list holds that one entry.
4. Cross to the Mac and back with and without the external display. Check where the laptop pointer lands.
5. Type on the Mac, including Cmd shortcuts. Press Super+Shift+Escape and verify that input is back on the
   laptop and no modifier is still held on the Mac.
6. Copy and paste text both ways.
7. Stay on the Mac without input for at least 20 seconds. Verify the next key still goes to the Mac.
8. While captured, try Alt+Tab, Alt+F4, a lone Super, volume, mute and brightness. Confirm no laptop window
   action, that the keys reach the Mac, and that Super+Ctrl+Escape releases and opens a usable recovery terminal.
9. Try the Minecraft world and another game with the game holding the pointer. Check that the pointer stays in
   the game, then record what happens in the menus.
10. Turn sharing Off while the Mac is connected. Verify local input, no crossing and no new clipboard transfer.
    Turning On again must ask for the password. Restart once with On and once with Off to confirm persistence and
    the corresponding login behavior.

## Left, in order

1. A fresh Fable final review of the whole package, the local fixes and the missing hosted daily-use evidence.
2. The lead sends the final heads for `linux-aresos` and `linux-hub` to read. Both give their read verdicts.
3. Merge the PR after both reads and resolution of the outstanding hosted VM evidence and review findings.
4. `linux-aresos` prepares the release after R29.
5. The owner approves and runs the laptop test above.

### For step 3 (done in step 3)

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
| `os/ci/deskflow/{actions.py,deskflow_vm.py}`, `os/tests/test_deskflow_vm.py` | `db4d0b14` | Check DRM transitions, output-client liveness, and each custom-mode operation. |
| `os/ci/deskflow/check_layers.py`, `os/tests/test_input_portal_layers.py` | `f4c52a3c` | Reject relocated Rust material in every shipped layer. |
| `os/ci/deskflow/deskflow_vm.py`, `os/tests/test_deskflow_vm.py` | `4e04191c` | Count loss of a connected DRM status node as a transition. |
| `os/ci/deskflow/check_layers.py`, `os/tests/test_input_portal_layers.py` | `99b0929a` | Reject relocated Cargo artifacts by filename in every shipped layer. |
| `os/packages.lock.json` | `ff8c842e` | Lock the gated Deskflow RPM and its one new dependency, libportal. |
| `os/build.sh`, `os/deskflow-rpm.sh` | `0d73c4ef` | Limit testing to the exact Deskflow RPM in throwaway builds and check the NEVRA and SHA-256. |
| `os/ci/check-resolve.sh` | `ff2865b5` | Resolve the exact Deskflow candidate and fail on a different RPM. |
| `os/Containerfile` | `193f2109` | Pass the build kind to package resolution and install the portal and allow-list. |
| `os/manifest/input-portal.sha256` | `8b16cf82` | Pin both byte-identical builds of the backend with the sharing-window prompt. |
| `os/config/usr/share/xdg-desktop-portal/aresos-portals.conf` | `7a09287f` | Preserve each existing route and add InputCapture and Clipboard. |
| `os/config/usr/libexec/aresos-shell` | `d5ea344f` | Deskflow scope only. See the `linux-hub` review below. |
| `os/config/usr/libexec/aresos-deskflow`, `os/config/usr/share/aresos/apps/org-deskflow-deskflow.json` | `dfee4a41` | Guard the image's native Deskflow launch with a TLS and peer-checking profile. |
| `os/config/usr/{bin/aresos-input-sharing,libexec/aresos-input-sharing-set,share/applications/org.aresos.InputSharing.desktop,share/polkit-1/actions/org.aresos.input-sharing.policy}`, `os/tests/test_input_sharing.py` | `8059f338` | Add and test the switch, GUI and per-verb policy. |
| `os/ci/polkit-review.json` | `673736cf` | Review executable, verb and each session's decision for both sharing actions. |
| `os/ci/polkit-check.js` | `7e1ff13d` | Audit both exec annotations and detect unreviewed actions for the helper. |
| `os/config/usr/share/aresos/labwc/rc.xml` | `378224cb` | Mark the two release bindings and keep the recovery terminal and cover actions. |
| `os/ci/owner_vm.py` | `fe4e8191` | Accept the Deskflow registry alongside the historical registry when auditing an update. |
| `os/ci/check-image.sh` | `54ceedb8` | Supply the reviewed definitions for image ownership and content checks. |
| `os/ci/image-checks.sh` | `c0020bc6` | Verify package, routes, sharing files, policy, TLS profile and bindings in the image. |
| `os/ci/deskflow/{actions.py,deskflow_vm.py}` | `fd1a979d` | Prove the real frontend route, Deskflow caller and stable session in the regular backend VM. |
| `os/tests/test_aresos_desktop.py`, `os/tests/test_everyday_account.py`, `os/tests/test_aresos_shell{,_discovery,_icons,_protocol}.py` | `dccb0f1d` | Update release-mode, recovery and registry assertions, including the scope regression. |
| `os/config/usr/libexec/aresos-input-sharing-set`, `os/tests/test_input_sharing.py` | `938a4deb` | Keep Off independent of an advisory lock any reader could hold. Locally verified after dispatch 7. |
| `os/ci/deskflow/{Containerfile,actions.py}`, `os/tests/test_deskflow_vm.py` | `0ce12ae3` | Isolate the DRM controls from frontend auto-activation and fail a contaminated control. Locally verified after dispatch 7. |
| `os/manifest/input-portal.sha256` | `121ee33b` | Step 3 review fixes: pin the backend whose Wayland worker starts only for an authorized session while sharing is On (two byte-identical clean builds). |
| `os/config/usr/libexec/aresos-deskflow`, `os/tests/test_aresos_deskflow.py` | `d01f335d` | Step 3 review fixes, finding 3: pairing through the guarded launcher; the core's IPC socket in the private runtime folder. |
| `os/config/usr/share/applications/org.deskflow.deskflow.desktop` (new) | `67f69117` | Finding 2: the image's own entry for the desktop ID, opening the guarded launcher. |
| `os/build.sh` | `6dbb7a89` | Finding 2: for the locked install alone, `%_netsharedpath` keeps Fedora's copy of that entry out; `rpm -V deskflow` stays clean. |
| `os/ci/image-checks.sh`, `os/ci/check-image.sh` | `313aba4c` | Finding 2: assert the effective Deskflow entry, every `Exec`, the net-shared state and a clean `rpm -V deskflow`; `openssl` present. |
| `os/ci/deskflow/{Containerfile,actions.py,deskflow_vm.py}`, `os/tests/test_deskflow_vm.py` | `05cf9f05` | Finding 1: normal frontend activation in the test layer (undoes `0ce12ae3`'s removal), the backend's Wayland connections read from outside in every boot, the backend state's worker started by the real Deskflow and kept, and the return to Off. Not yet run hosted. |
| `os/ci/deskflow/actions.py`, `os/tests/test_deskflow_vm.py` | `dad6e205` | Round 2: fail on descriptor inspection errors and check original process exit plus fresh bus-only activation. |
| `os/ci/image-checks.sh`, `os/tests/test_shell_assertions.py` | `a7fadb4e` | Round 2: require `rpm -V deskflow` to exit 0, including when RPM prints nothing. |
| `os/config/usr/libexec/aresos-deskflow`, `os/tests/test_aresos_deskflow.py` | `ece7b993` | Round 2: set an explicit reject default in the pairing dialog and drive it with Qt Test. |
| `os/manifest/input-portal.sha256` | `ca6be85f` | Round 2: pin the backend that exits after teardown, from two byte-identical clean builds. |
| `os/Containerfile`, `os/ci/{check-resolve.sh,guardian_host.py,image-checks.sh}`, `os/labwc/stage.py`, `os/packages.lock.json`, `os/config/usr/{libexec/aresos-shell,share/fonts/aresos/}`, `os/tests` | `73f72d23` | Earlier integration of R29 from main. |
| `os/config/usr/libexec/{aresos-deskflow,aresos-deskflow-login}`, `os/tests/test_aresos_deskflow.py` | `4fca2753` | Reuse the hub's guarded scope and stop the guarded server on Off. |
| `os/config/usr/share/aresos/labwc/autostart`, `os/tests/test_{everyday_account,aresos_desktop}.py` | `f5f6e195` | Invoke the gated hook in the real labwc login. |
| `os/ci/image-checks.sh` | `86991324` | Verify the installed hook and exact autostart line. |
| `os/config/usr/libexec/aresos-deskflow`, `os/tests/test_aresos_deskflow.py` | `69610c4f` | Redact Info-level crossing coordinates at the guard and route output through the filter. |
| `os/config/usr/libexec/aresos-deskflow`, `os/tests/test_aresos_deskflow.py` | `54c9203c` | Give deliberate fingerprint acceptance a keyboard mnemonic. |
| `os/config/usr/libexec/aresos-deskflow`, `os/tests/test_aresos_deskflow.py` | `d9ab0526` | Close the modal timer cleanly, filter disconnect coordinates and test the login and log behavior. |
| `os/ci/deskflow/{Containerfile,actions.py,session,session-agent,window-state.py}` | `641fe941` | Add disposable VM-only polkit, clipboard, TLS and input probes. |
| `os/ci/deskflow/{daily_vm.py,deskflow_vm.py}` | `75840989` | Run the daily-use and persistence checks and report each completed check. |
| `os/ci/check-build.sh` | `7cf8854c` | Require the installed backend to match the source pin in this check build. |
| `os/ci/deskflow/{actions.py,daily_vm.py}` | `4f625db6` | Use a read-only sandbox fixture and prove input started reaching the client before Off. |
| `os/ci/deskflow/{actions.py,daily_vm.py}` | `3bd08acf` | Wait for the frontend's descriptors to settle and check On from a real remote PAM session. |
| `os/config/usr/libexec/{aresos-deskflow,aresos-deskflow-login}`, `os/tests/test_aresos_deskflow.py` | `99d57cbb` | Run explicit fingerprint re-enrollment in the same native scope. |
| `os/ci/deskflow/{actions.py,daily_vm.py}` | `a77df9de` | Check the client receives its modifier releases before QEMU sends physical key-up. |
| `os/ci/deskflow/deskflow_vm.py` | `e6b54d0d` | Record Off and On Wayland worker counts for every output boot. |
| `os/ci/deskflow/deskflow_vm.py`, `os/tests/test_deskflow_vm.py` | `ce22c034` | Keep separate custom-mode and daily-use results and test gate failure. |
| `os/tests/test_input_portal_layers.py` | `58a1bb5e` | Give every leak probe a fresh layer so an earlier forbidden directory cannot mask the one under test. |
| `os/tests/test_labwc_stage.py` | `550efbbc` | Verify the guarded package installation invocation after the merged build changes. |
| `os/ci/deskflow/actions.py` | `cf07d7ea` | Drive the clipboard round trip through the real Deskflow return crossing. |
| `os/manifest/input-portal.sha256` | `bcea0dad` | Pin the two byte-identical builds with explicit key-up events on release. |
| `os/config/usr/share/aresos/labwc/autostart`, `os/ci/image-checks.sh`, `os/tests/test_{everyday_account,aresos_desktop}.py` | `a5836aa6` | Publish the compositor environment to the private bus before either login app can activate the portal. |
| `os/ci/deskflow/actions.py`, `os/tests/test_deskflow_vm.py` | `147a61f5` | Observe the actual app-ID-specific Off log and record safe facts about failed startup. |

Not touched in step 1c: `os/Containerfile` (the stage copies the whole `labwc/` folder, so the second patch needs no
new line; its comment above the stage still says "one upstream fix" and should name both patches when the file is
next changed), `os/ci/vm.py`, `os/packages.lock.json`, the image's `rc.xml`. **For `linux-aresos`'s release rule:** the
lock's shape changed (`patch` to `patches`) and the NEVRA and pins moved; a rule written for `aresos1` must be
re-aimed at `aresos2`: R29 carries this package (release plan, 2026-11-21) and gates its cut.

## For linux-hub

| File | Commit | Why |
|---|---|---|
| (none in steps 1 and 1b) | | |
| `os/config/usr/libexec/aresos-shell` | `d5ea344f` | Only the image Deskflow entry gets the native ID as its scope component. The launch suffix and hub protocol ID keep their existing form. |
| `os/config/usr/libexec/aresos-shell` | `73f72d23` | Earlier integration of R29 from main. |
| `os/config/usr/libexec/aresos-deskflow-login` | `4fca2753` | The login hook reads the same image catalogue and uses `ScopeLauncher.command` and `environment`. The only package change to `aresos-shell` itself is `d5ea344f`. |
| `os/tests/test_aresos_deskflow.py` | `d9ab0526` | Exercise the login hook's call to the hub launcher and its exact argv. |
| `os/config/usr/libexec/aresos-deskflow-login` | `99d57cbb` | An explicit re-enrollment uses the guarded command in the same scope. |

## Rules from `linux-aresos` for the later steps (2026-11-21)

- Keep the "For linux-aresos" list above complete (every commit touching `os/` outside `os/input-portal/`, and
  `os/ci/`).
- Don't touch `os/ci/vm.py` unless the step needs it. When a later step does, run
  `python3 -B reviews/27-first-update-release/rebind.py pending "<B321 note>"` after that commit, and never check out
  `pending-rebind.json` first.
- Keep the list "Image differences" below complete as the image work lands.

## Image differences

What the image gains or changes through this package, for `linux-aresos`'s release notes and checks.

- **labwc (step 1c):** the RPM is `labwc-0.9.6-1.fc44.aresos2.x86_64` (R28 has Fedora's `labwc-0.9.6-1.fc44`; `aresos1` is
  on main only and never ships), built with both patches.
  Changed files: `/usr/bin/labwc` (the patch; pins in step 1c above), `/usr/bin/labnag` (only the NEVRA in its
  `.note.package`), and so the two `.build-id` links. Same 64 paths; every other file is Fedora's, byte for byte.
  New behaviour: bindings are off while the input portal's capture surface holds the keyboard, except keybinds
  marked `allowWhenInhibited="yes"`. Step 3 marks only Super+Shift+Escape and Super+Ctrl+Escape.
  The image check names both patches. Real hardware first at the release's laptop install, as 311's rule says.
- **Input portal (step 2):** `/usr/libexec/aresos-input-portal` (0755) and
  `/usr/share/dbus-1/services/org.freedesktop.impl.portal.desktop.aresos-input.service` (0644), owned by root.
  The image also gains `/usr/share/licenses/aresos-input-portal/LICENSE` and
  `/usr/share/aresos/manifest/input-portal.sha256`. Release builds require the backend's binary pin.
- The Rust toolchain and `os/input-portal/` source tree stay in the builder path. The listener, `wlr-randr`
  and the session log capture are part of the throwaway check layer.
- **Deskflow (step 3, review fixes):** Fedora's reviewed Deskflow 1.27.0 RPM and libportal are added, except
  Fedora's `/usr/share/applications/org.deskflow.deskflow.desktop`, which RPM records as net shared (not installed;
  `rpm -V deskflow` is clean). In its place the image's own entry with the same desktop ID (root, 0644) opens
  `/usr/libexec/aresos-deskflow` (0755), which the hub also runs from the reviewed registry under the native ID scope.
  Its private runtime profile enables TLS and peer checking and trusts at most one fingerprint; with none saved
  (or `--enroll`) it pairs: a dialog shows the connecting peer's fingerprint and saves it only when the owner
  confirms. It makes a server certificate with `openssl` for a profile that has none, and keeps the core's IPC socket
  in its private runtime folder.
- **Input portal behaviour (review fixes):** the backend runs on the bus without a Wayland connection; its worker
  connects only for an authorized session while sharing is On and disconnects at Off or when no session is left.
  The backend's pin is `ef3d09781e34e82fcd2a3db2cb025a8d9fef3f295eea6f177813a26479da23df`.
- **Routing and switch (step 3):** `aresos-input.portal`, `aresos-portals.conf`, the one-ID `allowed-apps`,
  `org.aresos.InputSharing.desktop` and `org.aresos.input-sharing.policy` are root-owned, mode 0644.
  `/usr/bin/aresos-input-sharing` and `/usr/libexec/aresos-input-sharing-set` are root-owned, mode 0755.
  The image and its defaults carry no sharing file. The owner's release key and the combined release and
  recovery binding are in `rc.xml`.
- **Login and logging (step 4):** the labwc autostart runs `/usr/libexec/aresos-deskflow-login` (root, 0755).
  Autostart publishes the Wayland and desktop variables to the private bus before portal-activating apps.
  The hook starts the hub's guarded Deskflow server at login while sharing is On (T455). The guard lets one
  server hold the runtime profile, shuts it down on Off and relays default Info logs with crossing and disconnect
  coordinates removed. The core's direct file logging is disabled in the private profile.
- The daily-use test layer's Xvfb client, input probes, clipboard tools and loopback SSH test stay on the
  check-build path. The shipped image includes the native Deskflow RPM, guarded desktop entry, launcher and
  polkit switch across steps 2 to 4.

**Summary for the owner.** The image adds Deskflow and a Mouse and keyboard sharing switch that starts Off.
Turning it on asks for the owner's password. While sharing is On, Deskflow starts by itself at login.
Super+Shift+Escape brings the pointer back, and Super+Ctrl+Escape
also opens the recovery terminal. The first time the Mac connects, a window shows its fingerprint, and the
laptop trusts it only after the owner confirms it matches what the Mac's Deskflow shows.

## CI dispatches

None in steps 1 and 1b or the step 3 review fixes. Step 4 used dispatch 8 of 8.

| # | Step | Run | What |
|---|---|---|---|
| 1 of 8 | 1c | `44935351683`, on `0b1f9339` (dispatched 2026-11-21 19:24) | `check_build=build` on the step's head: it builds the labwc stage (the pins must hold on the hosted runner too) and the image, and runs the image checks, the labwc one included. **Green** (the lead, 2026-11-21 20:22). |
| 2 of 8 | 1c review fixes | `44937064135`, on `7d38fa7b` (dispatched by the lead 2026-11-21 19:44) | `check_build=build` after fix 8: image-checks.sh now runs `stage.py check-installed` against the manifest lock, piped in by check-image.sh. **Green** (2026-11-21 21:25). |
| 3 of 8 | 2 | [45000469287](https://github.com/Ares-Empire/AresOS/actions/runs/45000469287), on `bd5082dd` (2026-11-22 08:56 CET) | `check_build=deskflow`. **Failed before image build**. Pinned tools installed, then the common `sigstore/cosign-installer` timed out downloading its v2.5.2 bootstrap binary (curl exit 28). `gh run watch 45000469287 --exit-status --interval 60` returned 1. |
| 4 of 8 | 2 | [45000755789](https://github.com/Ares-Empire/AresOS/actions/runs/45000755789), on `a04a693c` (2026-11-22 09:00 CET) | `check_build=build`. **Cancelled before any workflow steps** after run 3's external failure. `gh run watch 45000755789 --exit-status --interval 60` returned 1 and GitHub reports `cancelled`. |
| 5 of 8 | 2 | [45001307065](https://github.com/Ares-Empire/AresOS/actions/runs/45001307065), on `0c948087` (dispatched by the lead 2026-11-22 09:07 CET) | `check_build=deskflow` on step 2's final head. **Green** (2026-11-22 09:31): image build and checks, then the DRM output gate. Regular runs (a) to (d) **passed in all three states** (`regular-none`, `regular-listener`, `regular-backend`), the second screen's hotplug by `SetUIInfo`. Custom mode (e): `custom-none` passed; `custom-listener` and `custom-backend` hit the compositor assertion (`head_send_state`), as 316's analysis expected. **The gate passes** (brief item 2's rule): step 3 may start, and (e) is the known limit "no custom mode while the backend runs". |
| 6 of 8 | 2 review fixes | [45004171828](https://github.com/Ares-Empire/AresOS/actions/runs/45004171828), verified at `f4c52a3ca122ee75798c32f9505920c0c03d7d60` (2026-11-22 09:43 CET) | `check_build=deskflow`. **Passed** (10:10 CET). `gh run watch 45004171828 --exit-status --interval 60` returned 0. The image checks passed, the layer scan passed on 9 added layers, and the installed backend SHA-256 matched the pin. The DRM gate passed with the six case results below. |
| 7 of 8 | 3 | [45009968432](https://github.com/Ares-Empire/AresOS/actions/runs/45009968432), verified at `dccb0f1da264fff6b092f77238ee6ff20c49917b` (2026-11-22 10:56 CET) | `check_build=deskflow`. **GitHub passed** at 12:11 CET and `gh run watch 45009968432 --exit-status --interval 60` returned 0. Image and polkit checks passed, all 11 added layers passed, and the installed backend SHA-256 matched the pin. The real frontend proved the native ID. The table below accounts for unexpected backend activation in the DRM controls. |
| 8 of 8 | 4 | [45025378331](https://github.com/Ares-Empire/AresOS/actions/runs/45025378331), verified at `bcea0dadb2fc143ae6bd06c73776615da459e725` (2026-11-22 14:02 CET) | `check_build=deskflow`. **Failed in the daily-use VM** at 14:28 CET. The image build and checks passed. The six DRM boots finished with the expected results. The daily-use boot proved the initial Off state, then the scoped refusal assertion timed out. The reboot-On boot read the persisted On setting and timed out waiting for an armed server. The first `gh run watch 45025378331 --exit-status --interval 60` lost its GitHub API connection, and reattaching returned 1 with the completed failure. This was the final dispatch. |

The hosted job checked out `bcea0dadb2fc143ae6bd06c73776615da459e725`. See
[run 45025378331 and its check-build-evidence artifact](https://github.com/Ares-Empire/AresOS/actions/runs/45025378331#artifacts).
The detailed records are `image/checks.txt`, `image/polkit.txt`, `image/input-portal-layers.txt`,
`deskflow/result.json`, each boot's `operations.jsonl`, and `deskflow/daily-use/daily-checks.jsonl`.

| Run 45025378331 image or DRM check | Result |
|---|---|
| Effective Deskflow desktop entry | **Passed.** `DESKFLOW_ENTRY_GUARDED` named the installed entry and `Exec=/usr/libexec/aresos-deskflow`. The required `rpm -V deskflow` exited 0. |
| Image, input portal layers and polkit rules | **Passed.** `IMAGE_CHECKS_PASSED`, 11 added layers passed, `POLKIT_CHECK_PASSED`. |
| Input portal pin | **Passed.** Build and installed binary matched `00e8ff021c7978c6ed7548e050f23734d4e198bcbcebebe8d51157545d28cb57`. |
| `regular-none` | **Passed.** Initial backend absent. No backend held a Wayland connection during the control. Three preferred and alternate-mode cycles, both VT transitions and SetUIInfo hotplug passed. |
| `regular-listener` | **Passed.** Initial backend absent. The listener kept its connection, and no backend reached Wayland. The same listed modes, VT transitions and SetUIInfo checks passed. |
| `regular-backend` | **Passed.** Initial backend absent. The real native caller `org.deskflow.deskflow` held one worker through the listed modes, VT transitions and SetUIInfo. Geometry and the original bus owner held. Off closed one session, the original pidfd became readable, and fresh owner `:1.376` held zero Wayland connections. The terminal launch was refused with an empty ID. |
| `custom-none` | **Passed.** Initial backend absent. Custom mode, disable and re-enable passed. |
| `custom-listener` | **Known limit reproduced.** Initial backend had zero Wayland connections. Setting the custom mode and disabling passed. Re-enable hit `head_send_state` with the listener bound. |
| `custom-backend` | **Known limit reproduced.** Initial backend absent. The On worker had one Wayland connection. Setting the custom mode and disabling passed. Re-enable hit the same compositor assertion. |

| Run 45025378331 brief check | Hosted result |
|---|---|
| 2. First login while Off | **Passed.** The switch was Off, Deskflow was absent and the backend had zero Wayland connections. |
| 2. Refused scoped launch, one window and local crossing | **Failed at the assertion.** The test waited 30 s for a later-method log message after the CreateSession request. No dialog count or crossing result was recorded. |
| 2. Password, cancellation, passwordless Off, invalid arguments, inactive/remote subjects and unsafe switch paths | **Not reached.** The image's static polkit decisions passed. The interactive decisions and switch assertions were pending when the daily boot stopped. |
| 3. Real-client motion, buttons, wheel, keys and frontend signals | **Not reached.** |
| 3. 20 clipboard transfers each way, portal read/write counts and frontend fd count | **Not reached.** |
| 4. Both modifiers released at the client after Super+Shift+Escape | **Not reached.** The local EIS harness proved the release sequence. |
| 5. A 60-second idle capture and release against a stopped backend | **Not reached.** The stopped-backend fallback passed in each local harness run. |
| 6. Backend death, frontend restart and logout/login while sharing is On | **Not reached.** The separate DRM boot proved a fresh bus-only activation after Off. |
| 7. Off while typing, manual file removal within two seconds, and password required to re-enable | **Not reached.** The DRM identity check proved Off tore down an armed session. |
| 7. Persistence across reboot | **Partial.** The test seeded On and the next boot read On. It timed out waiting for an armed scoped server with zero worker connections at readiness. Off reboot was not reached. |
| 8. Bindings, Flatpak refusal and trace/log privacy | **Not reached.** The image verified both marked bindings. The hosted run recorded no live binding, sandbox or log privacy results. |
| 9. Real Wayland-session pairing, different certificate and plaintext refusal, stale and disabled peer-check settings | **Not reached.** |

#### Binding table for the installed capture

The hosted boot stopped before entering a capture. Window/focus action, capture state and the next key's
destination are unobserved for each row below. The local harness has separate compositor checks.

| Binding | Laptop windows and focus | Capture | Next key |
|---|---|---|---|
| Alt+F4 | Unobserved | Unobserved | Unobserved |
| Alt+Tab | Unobserved | Unobserved | Unobserved |
| Alt+Shift+Tab | Unobserved | Unobserved | Unobserved |
| Brightness up | Unobserved | Unobserved | Unobserved |
| Brightness down | Unobserved | Unobserved | Unobserved |
| Volume up | Unobserved | Unobserved | Unobserved |
| Volume down | Unobserved | Unobserved | Unobserved |
| Audio mute | Unobserved | Unobserved | Unobserved |
| Microphone mute | Unobserved | Unobserved | Unobserved |
| Ctrl+Alt+Escape | Unobserved | Unobserved | Unobserved |
| Lone Super | Unobserved | Unobserved | Unobserved |
| Left button | Unobserved | Unobserved | Unobserved |
| Middle button | Unobserved | Unobserved | Unobserved |
| Right button | Unobserved | Unobserved | Unobserved |
| Scroll up | Unobserved | Unobserved | Unobserved |
| Scroll down | Unobserved | Unobserved | Unobserved |
| Alt+left drag | Unobserved | Unobserved | Unobserved |
| Alt+right drag | Unobserved | Unobserved | Unobserved |
| Alt+middle | Unobserved | Unobserved | Unobserved |
| Alt+scroll | Unobserved | Unobserved | Unobserved |
| Super+Shift+Escape | Unobserved | Unobserved | Unobserved |
| Super+Ctrl+Escape | Unobserved | Unobserved | Unobserved |

### Local follow-up after dispatch 8

- `147a61f5` observes the backend's actual app-ID-specific CreateSession denial. The generic
  `refused: sharing is off` log belongs to later methods. A confined rootless extension of the harness used
  the installed backend binary, an allow-listed Deskflow ID from the harness frontend, and the VM's exact
  matcher. It printed `SUMMARY 8 passed, 0 failed, exit 0` including AccessDenied, the matching log, no sessions
  and no Wayland connection. The VM now reports safe startup facts if it cannot reach the server.
- `a5836aa6` publishes the Wayland socket and desktop synchronously on the private session bus before the
  authentication agent or Deskflow can trigger normal activation. labwc starts its own activation-environment
  updater asynchronously. A private `dbus-run-session` test exercised the autostart command and an immediately
  activated fixture service received both variables. The hosted artifact does not contain the reboot's startup
  diagnosis, so it cannot establish which component caused its timeout or prove the new login ordering in the image.
- Reran discovery on `test_deskflow_vm.py` (12 passed), `test_everyday_account.py` (36 passed),
  `test_shell_assertions.py` (10 passed), and `test_aresos_desktop.py` (189 including one existing skip).
  With the prior module results, the current count is 575 tests, 574 passed and one skipped. The post-fix
  Bash syntax and whitespace checks passed.
- An additional isolated reproduction of the paired profile could not install its Fedora test dependencies.
  DNF exhausted the mirror list on DNS timeouts before Deskflow ran. The earlier step 3 loopback pairing
  and the current Qt launcher tests remain the available local evidence. No file larger than 500 MB
  remained in `.work/`.

| Run 45009968432 VM case | Result |
|---|---|
| `regular-none` | Passed the output operations with SetUIInfo. The frontend activated the backend during the run, leaving the no-client control unverified. |
| `regular-listener` | Passed the output operations with SetUIInfo. The frontend activated the backend during the run, leaving the listener-only control unverified. |
| `regular-backend` | Passed (a) to (d), including SetUIInfo, geometry and original backend liveness. The native identity proof passed and the terminal control was refused with an empty ID. |
| `custom-none` | Passed initial custom mode, off and re-enable. The backend never acquired its name in the log. |
| `custom-listener` | Initial custom mode and off passed. Re-enable hit the expected `head_send_state` assertion. The frontend requested backend activation, which failed during compositor teardown. |
| `custom-backend` | Initial custom mode and off passed. Re-enable hit the expected `head_send_state` assertion. |

The artifact reported `gate: passed` with an empty `custom_incomplete`. Dispatch 8 used normal activation and verified from outside that no backend worker joined the controls. The raw checks and operation traces are in the
[check-build-evidence artifact](https://github.com/Ares-Empire/AresOS/actions/runs/45009968432/artifacts/14752141095).

| Run 45004171828 VM case | Result |
|---|---|
| `regular-none` | Passed (a) to (d), with three unplug and replug cycles via SetUIInfo and both VT transitions. |
| `regular-listener` | Passed (a) to (d), with SetUIInfo hotplug and the original listener still running. |
| `regular-backend` | Passed (a) to (d), with SetUIInfo hotplug, matching geometry and the original backend keeping its bus name. |
| `custom-none` | Passed initial custom mode, off, and re-enable. |
| `custom-listener` | Initial custom mode and off passed. Re-enable hit the expected `head_send_state` assertion. |
| `custom-backend` | Initial custom mode and off passed. Re-enable hit the expected `head_send_state` assertion. |

The evidence's `deskflow/result.json` recorded `gate: passed` and an empty `custom_incomplete` result.

## Podman, after the step 3 review fixes

Rootless, one container at a time, all throwaway (`--rm`): cached and two clean backend builds
(`os/input-portal/dev/container.sh`, the cached one on 316's two cache volumes), three harness runs on the kept
`localhost/aresos-input-portal-harness:321-step2`, and three short netshared/`rpm -V` probes in that image with
networking off (the gated Deskflow RPM from `.work/deskflow-gate/` sent in as a tar stream). No image was built or
removed; no `prune`. The builds and harness evidence are in the session's scratch folder, not in `.work/`.

## Podman, after step 3

The locked-base RPM/routing and polkit checks, two backend builds and two counted harness runs used
throwaway rootless containers, sequentially. The additional switch-helper fixture used the same cached
harness with networking disabled. This step built or removed no Podman images. No file under `.work/`
exceeds 500 MB.

## Podman, after step 2

Rootless throughout, with one container at a time. Kept the merged harness image
`localhost/aresos-input-portal-harness:321-step2` (`f82ab04e39ea`). Removed the first step 2 harness image
(`2db7970a522d`) and the locally verified Rust-stage image (`9163afe8d485`) by name or ID with
`podman rmi --no-prune`. Reused the existing `localhost/aresos-labwc:321c` with both pinned binaries.
No file under `.work/` is larger than 500 MB.

The review fixes built `localhost/aresos-input-portal-harness:321-step2-fix1` (`32c68fe827e9`),
used it for both harness runs and the `finished` fixture, and removed only that image with
`podman rmi --no-prune`. All three runs used throwaway rootless containers.

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
