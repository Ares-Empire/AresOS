# Independent repair review — CHANGES NEEDED

Reviewer: fresh `gpt-6.1-sol`, high, as brief 20 requests. Reviewed
`55fdc5b6..55cdee6a` against `briefs/20-continue.md`, the preceding build and
security reviews, and section 6 of `origin/main:docs/design/CONTROL.md`.
Evidence below is **run** or **read** as marked. No local browser,
container, profile, owner data or system configuration was accessed.
Only this review file was edited.

1. **P1 — Excluded hosts have an unchecked absolute-DNS spelling.**
   **Run:** `allowed_url('https://approval.test./', ['approval.test'])`
   and the same call with `https://sub.approval.test./` both return the
   address. The undotted host refuses. Executing the actual `safeURL`
   function extracted from `background.js` in a Node VM gives the same
   results. **Read:** `policy.py:36` and `background.js:14` compare raw
   hostnames without removing a terminal DNS dot. An absolute DNS spelling
   names the same host, so it must not get a different exclusion verdict.
   This affects the newly configured owner list as well as vendor entries.
   Normalize the hostname consistently before both exact/subdomain checks
   and rule generation, or refuse terminal-dot addresses. Add these cases
   to group 6. Confidence is high for both policy bypasses; whether Chrome's
   separate DNR/content-script matchers prevent a particular navigation is
   **not verified** here. Their possible protection does not establish the
   required independent refusal before every read/action.

2. **P2 — A rejected replacement handshake leaves the old selector entry.**
   **Read:** `daemon.py:67–75` unregisters `previous` only after
   `bridge.accept()` succeeds. If the old peer has closed and its EOF has
   not yet been handled, `Bridge.accept()` closes that descriptor before
   checking the replacement hello. An invalid hello then raises, skipping
   the unregister. The new exception handler keeps the daemon alive but
   leaves its selector map stale. **Run:** actual `Bridge`,
   `DefaultSelector` and socketpairs reproduced old FD `4`, next valid FD
   `4`, stale selector entries `[4]`, followed by `KeyError: ... (FD 4) is
   already registered`. The daemon subsequently closes the newly accepted
   connection while the bridge still refers to it. Save/unregister the old
   descriptor whenever it is retired, including failed replacement paths;
   clear bridge state if registration fails. Add invalid-replacement then
   valid-reconnect coverage. Confidence is high for descriptor/map recovery;
   full Linux daemon/peer-credential behavior remains CI-only.

The targeted repairs otherwise have useful direct evidence. **Read/run:**
external `aria-labelledby` and associated labels now use the reader's name
ordering and pass both wrappers plus capture fallback; prepared sends,
uploads, native dialogs and resumed submissions recheck current top/frame
read-only entries; acting qualification now includes password exclusion
before a binding read. The engine fixture verifies those refusals without
dispatch. Trusted submission reaches the same revalidation path by source
inspection; the added test does not separately exercise a real trusted
submission. The owner setting is loaded through the base protected-file
walk and failure is translated to a plain refusal; dynamic script
registration and session DNR configuration are wired into `mode()`.
Actual Chrome registration, changes to the configured list, and the group 6
route matrix still need container evidence. The setting tests mock the
protected-file reader; they are not a real filesystem-permission test.

**Checks run:**

- `node --test control/chrome_tests/*.test.mjs`: **12 passed, 0 failed**.
- `PYTHONPATH=control python3 -m unittest discover -s control/chrome_tests -v`:
  **41 tests, OK**, 39.456 seconds. Durable-write output:
  `{'single': 442, 'persistent': 442, 'pairs': 829}`.
- Browser-free socketpair/selector probe: reproduced finding 2 as above.
- Python URL-policy and Node actual-`safeURL` probes: reproduced finding 1
  as above; no DNS request or page load was made.
- `git diff --check 55fdc5b6..55cdee6a`: clean.

The public MAIN-world control API/page-forgery issue remains a **known
blocking finding**, not a newly fixed guarantee. Commit `55cdee6a` adds a
receiver-backed regression that still runs after an owner-input failure;
its Linux CI result was not inspected in this review. The owner-input
decision in the continuation brief likewise still needs its complete
strict browser tests. The prior review's qualification delivery runtime
caller, live pending validity and exact covered confirmations were not
repaired in this commit range. This is an interim repair review, not SAFE
or evidence that the full Now stage has passed twice.

## Follow-up: working-tree repairs

Reviewed only the follow-up changes to `daemon.py`, `bridge.py`, the URL
policy and runtime exclusions, and audit bootstrap, after the review above.
**Both findings above are addressed at the browser-free/source level. No
new related regression was found in this limited follow-up.** This does
not clear the separately recorded MAIN-world/page-forgery blocker.

- **Finding 1:** Python now applies IDNA encoding and removes terminal DNS
  dots before comparing; the extension uses URL's parsed hostname and
  removes terminal dots. **Run:** the dotted parent, dotted subdomain and
  fullwidth-dot owner host all refuse. **Run/read:** the actual background
  functions emit both ordinary and dotted DNR domains and content-script
  exclusions. A Node stub recorded `approval.test`, `approval.test.` and
  `https://*.approval.test./*`. Chrome's acceptance and enforcement of
  these generated rules remain **not verified** locally.
- **Finding 2:** `register_chrome_host()` saves the old FD and unregisters
  it in `finally` when the bridge retires that peer, including rejected
  replacement handshakes. The new socketpair test covers EOF, invalid
  replacement, valid reconnection, and rejection of another live host.
  **Run:** all pass. A further injected selector-registration failure
  cleared the new bridge connection/session/version and kept the socket
  descriptor open for the caller's refusal. **Run:** a duplicate host
  while the original socket has its production 15-second timeout refused
  in `0.00001` seconds and retained the original peer; the readiness check
  avoids the previous timeout-mode polling delay.
- **Audit startup:** the private `audit` command now precedes the mandatory
  owner-setting check. **Run:** enabling recording before configuration
  succeeds, while `tabs` still refuses without configuration. **Read:**
  the audit command only changes the recording flag; it does not read a
  page or dispatch input.

Follow-up commands **run**:

- `node --test control/chrome_tests/background.test.mjs control/chrome_tests/page.test.mjs`:
  **9 passed, 0 failed**.
- `PYTHONPATH=control python3 -m unittest discover -s control/chrome_tests -p 'test_bridge.py' -v`:
  **3 tests, OK**.
- `PYTHONPATH=control python3 -m unittest discover -s control/chrome_tests -p 'test_exclusions.py' -v`:
  **3 tests, OK**.
- Additional socketpair timing/registration-failure and actual-background
  Node probes: results recorded above; no browser or DNS request started.
- `git diff --check`: clean.

The complete Python/storage suite was not repeated for this follow-up;
its earlier result remains tied to the preceding head. Real Linux daemon
peer credentials, extension registration and navigation enforcement still
require the designated CI workflows.
