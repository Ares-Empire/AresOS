# Codex gpt-6.2-sol high, read-only, at f1d4a025, 2026-11-22

CHANGES-NEEDED

1. **NOT RESOLVED** — If SetUIInfo removes a previously connected DRM status node while labwc retains the output, (c) can still report `unverified`. Track the baseline connector and count its disappearance as a DRM transition. The fallback result already names the required rehearsal before publication: with the owner’s direct OK, run the check backend by hand without installing it and unplug and replug the external monitor three times. `os/ci/deskflow/deskflow_vm.py:173`
2. **RESOLVED** — The listener exits with status 2 on `finished`. The regular checks verify listener liveness and the original backend’s unique D-Bus owner after operations, including both VT transitions. `os/input-portal/harness/clients/wl-harness.c:576`, `os/ci/deskflow/actions.py:83`
3. **RESOLVED** — Custom mode verifies and records each transition, identifies the aborting operation, and reports incomplete evidence separately. The expected `head_send_state` abort stays non-blocking. `os/ci/deskflow/deskflow_vm.py:282`
4. **NOT RESOLVED** — The relocated-and-hidden `.rs` fixture is present, but a relocated Cargo proc-macro `.so` or `build-script-build` still passes the scan. Reject those Cargo artifact names at any depth and extend the hidden-layer fixture. `os/ci/deskflow/check_layers.py:7`, `os/tests/test_input_portal_layers.py:32`

Read-only mocks reproduced both remaining gaps. Dispatch 6 of 8, run `45004171828`, recorded three regular SetUIInfo passes, the expected custom aborts on re-enable, and a pass across nine added layers. `reviews/321-deskflow-image/PROGRESS.md:592`

Lead: 2 and 3 resolved; 1 and 4 are fixed first in step 3 and covered by step 3's check build and review.
