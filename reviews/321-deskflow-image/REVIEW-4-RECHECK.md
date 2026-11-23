# Package 321: final recheck (Codex gpt-6.2-sol high, read-only, fresh context, at bc2f0a81, 2026-11-23)

CHANGES-NEEDED

1. **RESOLVED — CI gate.** The saved artifacts for dispatch 14, run `45089791226`, confirm the image build at `453a4f83` and `DESKFLOW_VM_GATE_PASSED`. All 59 daily-use records passed, both reboot checks passed, and all six DRM boots had their expected outcomes. The binding table has 22 observed rows. The two later commits through `bc2f0a81` change only review records. `reviews/321-deskflow-image/PROGRESS.md:1122`

2. **RESOLVED — Login fixture.** Both activation-environment updates publish only `ARESOS_INPUT_PORTAL_LOG`. The DRM routing probe still replaces the frontend for observation. The reboot checks use the image’s own login, frontend, and Deskflow autostart. `os/ci/deskflow/actions.py:219`, `os/ci/deskflow/actions.py:531`, `os/ci/deskflow/deskflow_vm.py:333`

3. **RESOLVED — Laptop procedure.** After pairing, the procedure keeps sharing On, confirms an armed session, and repeats step 1’s display, replug, lid, suspend, and VT operations. It requires the same labwc PID, recovered outputs, and an armed session after each operation. The physical rehearsal is pending. `reviews/321-deskflow-image/PROGRESS.md:874`

4. **NOT RESOLVED — Emergency kill targets.** Dispatch 14 proves the intact-record case. The fallback stops the recorded pair before killing the backend, leaves sharing On, and a hub launch restores capture. Start-time checks screen out stale PIDs, and pidfds keep signals bound to the pinned processes. There is no system-wide name scan. But any process running as the owner can replace or remove the record. The core’s executable check does not establish that it belongs to the guard, and the launcher’s command line is forgeable. A forged record can therefore direct the kill at an unrelated process. A missing or invalid record can leave the real core free to re-arm after the backend is killed. `os/config/usr/libexec/aresos-deskflow:306`, `os/input-portal/src/release.rs:107`, `os/input-portal/src/release.rs:220`

   **Smallest fix:** Have a trusted launch supervisor retain the actual pair’s pidfds at spawn in a registration the session UID cannot replace or remove. Use that registration to stop the pair before killing the backend. Extend check 5 to cover a replaced or missing PID file and verify that an unrelated core survives.

**Known limits confirmed.** All eight Fable limits are recorded, including the held mouse button on normal release, as is the Deskflow 1.27 microphone-mute limit. `reviews/321-deskflow-image/KNOWN-LIMITS.md:159`

Read-only review. No files changed and no tests rerun.
## Lead's triage

1 to 3 resolved. **4 is a known limit, not real harm under the bar:** only a process running as the owner can replace or remove the runtime record, and such a process can already signal or kill any of the owner's processes directly, or rewrite labwc's settings; the record gives it nothing new. Sandboxed programs cannot reach the private runtime folder. PID reuse is covered by the start-time checks and pidfds. The record is written before any capture, so without tampering it exists whenever there is a capture to release. Recorded in KNOWN-LIMITS.md. A launch supervisor holding the pair's pidfds is a possible later hardening.
