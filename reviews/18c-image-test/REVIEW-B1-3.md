**Findings: none.**

1. **Response handling — SAFE.** In [`test_integration.py`](</var/home/ares/AresOS-18c-build/control/tests/test_integration.py:78>), `run_user` still requires the client process to exit successfully and then JSON-decodes its stdout. If the service closes without answering, `readline()` yields an empty line; JSON decoding fails, so the test does not pass. [`validate_response`](</var/home/ares/AresOS-18c-build/control/response_checks.py:27>) checks transport framing and, for recognized calls, the output schema. It does not by itself check the expected outcome, so the callers’ assertions matter.

2. **Credential checks — SAFE.** The matrix test asserts the expected `ok` value for each UID and socket, then requires `permission_denied` for refusals ([`test_integration.py`](</var/home/ares/AresOS-18c-build/control/tests/test_integration.py:110>)). A wrong code or an improperly granted peer fails those assertions. Some other expected-refusal calls assert only `ok == False`, so they do not independently verify the refusal code; that limitation predates this commit and does not weaken the credential matrix.

3. **Race explanation — consistent.** The daemon checks `SO_PEERCRED` before calling `receive(connection)`. For a refused peer, it builds and sends an error response without reading the request ([`daemon.py`](</var/home/ares/AresOS-18c-build/control/aresos_control/daemon.py:51>)). The peer’s send can therefore lose the race with the service’s response and close. Catching `BrokenPipeError` lets the client attempt to read that response; it does not convert EOF into a valid JSON result.

4. **Additional file — informational.** The commit also adds `reviews/18c-image-test/REVIEW-B1-2.md`. It is a review note and does not affect runtime behavior.

**SAFE**