# Package 321 step 3: review (Codex gpt-6.2-sol high, read-only, fresh context, at 9181b331, 2026-11-22)

CHANGES-NEEDED

- **REVIEW-2-RECHECK point 1 — RESOLVED.** A connected DRM node disappearing now counts as a transition. The read-only mock confirmed the check fails if labwc retains the output. `os/ci/deskflow/deskflow_vm.py:173`
- **REVIEW-2-RECHECK point 4 — RESOLVED.** Read-only mocks confirmed the layer scan rejects relocated Rust source, Cargo proc-macro libraries, and build scripts. `os/ci/deskflow/check_layers.py:8`

- **BLOCKING — The capture backend runs at login while sharing is Off.** Dispatch 7 recorded frontend activation in both regular control boots. Startup immediately binds Wayland output management and clipboard data control. The switch still denies capture sessions, but the live output binding exposes an Off session to the known custom-mode compositor crash. Keep the Wayland worker stopped while Off. A D-Bus responder can handle frontend discovery and the sharing prompt, then start the worker after an authorized On request. Verify first boot and the transition back to Off with normal activation enabled. `os/input-portal/src/main.rs:142`, `os/input-portal/src/wayland/state.rs:1240`, `reviews/321-deskflow-image/PROGRESS.md:514`
- **BLOCKING — The shipped Deskflow desktop entry bypasses the guarded launch.** The extracted Fedora entry still has `Exec=deskflow`. The hub substitutes the wrapper only in its own catalogue. A desktop launcher that assigns the native app scope can give the stock GUI’s core the allow-listed ID while it uses the original TLS settings and trust list. Point the installed desktop entry at the guarded launcher and have the image check assert its `Exec`. `os/config/usr/share/aresos/apps/org-deskflow-deskflow.json:5`, `os/ci/image-checks.sh:705`
- **BLOCKING — First-use pairing has no guarded enrollment path.** The hub starts the core without the GUI that displays the incoming peer fingerprint. It copies an existing certificate and trust entry, so a fresh profile gives the owner no way to complete the brief’s compare-and-accept step from that launch. Add guarded enrollment that displays the connecting peer’s fingerprint and saves it only after the owner confirms the match. Verify enrollment from an empty profile. `os/config/usr/libexec/aresos-deskflow:25`, `os/config/usr/libexec/aresos-deskflow:59`, `briefs/321-deskflow-image.md:93`

**For known limits**

Dispatch 7 proves the hub-scoped native identity. The isolated DRM controls added after that dispatch still need the scheduled hosted rerun. `reviews/321-deskflow-image/PROGRESS.md:767`
## Lead's triage

All three BLOCKING findings are real under the bar and are fixed in one fix round (a Claude Opus agent; Codex is kept for step 4 and the reviews):
1. The backend's Wayland worker stays stopped while sharing is Off: no Wayland connection, no output-management and no data-control binding. It starts only after an authorized On request and stops when sharing goes Off. The brief's laptop item 1 ("the backend running and sharing still off") then means the D-Bus side only.
2. Every way of opening Deskflow by its desktop entry goes through the guarded launcher; the image check asserts the effective entry's `Exec`.
3. A guarded first-use enrollment: show the connecting Mac's fingerprint, save it to the trust list only after the owner confirms the match, verified from an empty profile.
REVIEW-2-RECHECK's points 1 and 4 are resolved.
