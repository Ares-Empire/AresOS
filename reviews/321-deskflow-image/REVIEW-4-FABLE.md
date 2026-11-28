# Package 321: final review (Claude Fable 5.2 on the API promo, read-only, fresh context, at eadd88c0, 2026-11-22; cost $14.94)

CHANGES-NEEDED

I had only Read (no Grep or Glob). Not opened: `clipboard.rs`, `heads.rs`, `screens.rs`, `trust.rs`, most of `wayland/state.rs`, the harness driver, `check_layers.py`, `polkit-check.js`, `polkit-review.json`, `check-resolve.sh`, most tests, REVIEW-1c-RECHECK and both REVIEW-2 files. For those I rely on the earlier reviews. I did not reach "The bar" in `docs/design/CONTROL.md` and used the brief's wording of it.

## 1. BLOCKING

**1. The package's own gate is open, and the head has never been built.**
- `reviews/321-deskflow-image/PROGRESS.md:1106-1149`: VM checks 2 to 9 were not reached and all 22 binding rows say "Unobserved".
- No installed image has yet shown a real Deskflow capture reaching only the client, either chord ending it, Off ending it, or a stranger or plain-text peer getting nothing.
- `briefs/321-deskflow-image.md:73` makes anything but "nothing, held, the client" a release blocker; `:110-112` puts this review after those checks.
- a5836aa6 changed the first command of every login (`os/config/usr/share/aresos/labwc/autostart:2`) and its image check (`os/ci/image-checks.sh:854-858`) after the last hosted run. No image at head exists.
- Fix: apply the Part 2 changes; the lead raises the dispatch cap (`PROGRESS.md:1076`, 8 of 8 used); run `check_build=deskflow` on the merge head. Merge only on `DESKFLOW_VM_GATE_PASSED` with the table filled.

**2. A check that passes by construction.**
- `os/ci/deskflow/actions.py:225-226` publishes `WAYLAND_DISPLAY` and `XDG_CURRENT_DESKTOP` to the bus itself. `:233-234` then asserts the bus-started backend has them. `:279` replaces the session's frontend. `:518-519` repeats the publishing in the daily boot.
- So what `briefs/321-deskflow-image.md:61` asks to be proven "on the real session" is proven only for a session the fixture arranged.
- The login path the laptop will use (the session's own frontend, backend and start hook) has passed in no run, and failed in the only one that tried (VM 7).
- Fix: on both lines publish `ARESOS_INPUT_PORTAL_LOG` alone. The assertions at `:233-234` and `:711` then test the image.

**3. The laptop test no longer tests labwc with the output manager bound.**
- `PROGRESS.md:863-865` (step 1) runs monitor off/on, replug, lid, suspend and VT switch with sharing Off.
- Since the step 3 fix the backend then holds no Wayland connection (`os/input-portal/src/main.rs:159-162`). That is the control case, not the case item 1 exists for.
- With "start it by itself" the worker is bound from every login while On. Lid, suspend/resume and a real monitor's replug with the binding are then first met in daily use, where a labwc abort ends the owner's session.
- The VM showed off/on, hotplug and VT switch with the binding; it cannot show lid, suspend or real monitors.
- The lead's triage of REVIEW-3 finding 1 stands; this is its side effect on the test.
- Fix (text only): after laptop step 3, with sharing On, work saved and `aresos-input-portal --status` showing the armed session, repeat step 1's operations. labwc's PID must stay before steps 4 to 10.

**Read and found sound, no change asked:**
- The root helper refuses anything but `on` or `off` before touching a file, checks every folder from `/`, and writes in one rename.
- The two polkit actions each carry path and verb; the maintenance rules leave them alone.
- The backend's switch read matches the helper's.
- The launcher forces TLS and peer checking, trusts at most one fingerprint, and rejects by default when pairing.
- The labwc patch gates everything but the two marked chords, and the image check requires exactly those two marks.
- `--release` pins by pidfd.
- The check-build job is read-only.

**Not blocking, correct before the list goes to `linux-aresos`:** `PROGRESS.md:1051-1053` names pin `ef3d0978…` and a worker that "disconnects". The pin is `00e8ff02…` (`os/manifest/input-portal.sha256:1`) and the process exits.

## 2. For known limits

- Any error in the login hook leaves Deskflow unstarted at login with no message; open it from the hub. This includes the hub catalogue scan running over its 2 s budget (`os/config/usr/libexec/aresos-deskflow-login:19-29`, `os/config/usr/libexec/aresos-shell:747-763`).
- Opened while Off, the core has about 5 s to ask the portal before the launcher stops it (`os/config/usr/libexec/aresos-deskflow:253`). If it is slower, the sharing window does not appear.
- After "Turn on" in the sharing window Deskflow is not running, and the window does not say so (only the docs do).
- A session asked for while the backend is exiting after its last session is refused as "sharing is off" (`os/input-portal/src/portal.rs:747-749`). It can open the switch window once while On; open Deskflow again.
- The forced release sends key-ups only. A mouse button held at the chord stays down on the Mac until Deskflow's own leave (`os/input-portal/src/eis_server.rs:140`, `:232-241`).
- While On and unpaired, every login runs the pairing server. Anyone who reaches the port can raise the fingerprint window (reject is the default).
- A program of the same user can delete the once-per-login marker and raise the switch window again (`portal.rs:646-647`).
- If the launcher dies, its lock goes with it while its core may live; a second launch then starts a second core (`aresos-deskflow:286-294`).

## 3. Diagnosis

**VM 2: the cause is the check's own search text. This is certain from the code.**
- At `bcea0dad` the check waited for `refused: sharing is off` (`.work/ci-45025378331/check-build-evidence/deskflow/daily-use/operations.jsonl`, line 2).
- The backend never writes that for a session refused while Off. `create_session` goes to `ensure_worker`, which returns the refusal at `os/input-portal/src/portal.rs:565-566` without logging.
- That warning exists only at `portal.rs:791`, which this path does not reach. What is written is the debug line at `:1076`.
- So the wait had to time out on a correct image too.
- Whether the core really asked the portal in that boot is not in the artifact: daily boots export no session log (`os/ci/deskflow/actions.py:449-451`). Nothing contradicts it.
- 147a61f5 fixes exactly this (`actions.py:472`, `:552-553`, `:1162-1166`). It needs the backend at debug or trace, which this boot sets (`:515-522`, `:678`). No further change is needed for this assertion.
- Possible next stop, which I could not check: `actions.py:533-534` compares window titles for equality, and kdialog may append " — KDialog". Matching with `startswith` avoids another failure that is not the product's.

**VM 7: the artifact cannot say. I did not find the cause.**
- What it shows (`deskflow/reboot-on/operations.jsonl`): On was read after reboot; the backend ran with no Wayland connection once prepare returned; `--status` never showed one armed Deskflow session in 30 s; the diagnostics returned only `{"daily": true}`.
- What it does not show: whether the hook ran, whether the core started, whether `CreateSession2` arrived, or what the backend answered.
- I ruled out the status matcher: `portal.rs:1723` prints what `actions.py:489-494` expects.
- The boot was not in the state the check was written for. VM 2's abort made the fixture seed On (`os/ci/deskflow/daily_vm.py:430-432`) with no paired Mac, so the hook took the pairing path.
- It was also the first boot in any run that needed the session's own path. Every passing boot kills the login backend, publishes the variables itself, and (in the DRM boot) replaces the frontend (`actions.py:219-227`, `:279`).

**a5836aa6 is a guess, and a weak one.**
- It assumes the backend was started before labwc published `WAYLAND_DISPLAY`.
- labwc 0.9.6 spawns `dbus-update-activation-environment` with both variables before it starts autostart (`.work/labwc-src/src/src/config/session.c:23-33`, `:232-235`, `:316-322`).
- The polkit agent needs far longer than that to reach the portal.
- The change is harmless but closes a window of milliseconds. Do not expect it to turn VM 7 green. It has not been built into any image.

**147a61f5 only reports for VM 7, and its report has three gaps.**
- `actions.py:558` adds `server.log`, which in the reboot boots is the first boot's file (`:654`, `:621-623`). Three of its ten facts would come from the wrong boot.
- It has no fact for the refusals that are not "Off": no ID (`portal.rs:1054`), not on the allow-list (`:1062`), not the frontend (`:695`). It has none for a hook traceback or the launcher's "Could not start Deskflow".
- Only two waits call it.

**Smallest fix, all in `os/ci/deskflow/`:**
1. `actions.py:225-226` and `:518-519`: publish `ARESOS_INPUT_PORTAL_LOG` only (blocking item 2).
2. `actions.py:679-680`: add to the prepare result whether the running backend's environment has `WAYLAND_DISPLAY`. This one value confirms or refutes a5836aa6's theory.
3. `actions.py:556-567`: use `server.log` only if a `server` probe was started in this boot. Add a count per `refused:` reason, whether the log holds `Traceback` or `Could not start Deskflow`, and the raw `--status` text.
4. `actions.py:449-451`: return those facts for daily boots. `daily_vm.py:45-52`: ask for them when any step fails.

**The one piece of logging that would settle VM 7:** the last 40 lines of `deskflow-ci-session.log` on any failed daily request, with every line matching `LOG_DATA` blanked. A login launch writes the hook's, launcher's, core's, frontend's and backend's own lines there.

Nothing after `actions.py:1162` has ever run hosted. Budget more than one dispatch.

## Lead's triage

- **1, fix:** the head is built and the daily-use gate run on CI. The dispatch budget was the brief's own count (8); the lead raises it to 12 for this reason (the gate was never reached, VM 7's cause is unknown and needs logging, the head has never been built), recorded in PROGRESS "CI dispatches".
- **2, fix:** the VM fixture publishes `ARESOS_INPUT_PORTAL_LOG` only, so the assertions test the image's own login path.
- **3, fix (text):** the laptop test repeats step 1's operations with sharing On and the worker bound, after pairing and before steps 4 to 10.
- **Not blocking, fixed:** PROGRESS's pin and "disconnects" wording.
- **Known limits:** all eight go into KNOWN-LIMITS.md.
- **Diagnosis:** VM 2's cause is the check's search text (147a61f5 fixes it; match the dialog title by prefix). VM 7: add the facts and the session-log tail the review names, then run.
- Note: the reviewer reports it had only Read, not Grep or Glob, so it relied on earlier reviews for the files it lists as not opened.
