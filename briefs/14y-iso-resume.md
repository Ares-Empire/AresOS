# 14y: Resume a dropped ISO download; probe 13 and qualification 3

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14x still apply, with the change below.

## Diagnosis (integrator)

Probe 12 passed 380 tests and the private registry checks. Then `os/ci/installer_inspect.py` streamed the pinned live ISO in a single `urlopen`, and the connection dropped at 2,128,609,280 of 9,068,650,496 bytes. `validate_download` correctly refused the result. This was a network drop, not our code, but one dropped connection shouldn't cost a run.

## Fix (CI harness only)

1. **Download with bounded resume:** on a short read or a connection error, continue with an HTTP `Range: bytes=<received>-` request, at most **6 attempts** in total, with a short backoff.
   - Accept a resumed response only if it is `206` with a `Content-Range` that starts exactly at the received offset and whose total equals the pinned size.
   - If the server ignores Range (`200`), restart from zero; that still counts toward the 6 attempts.
   - Keep hashing across the resumed parts, or hash the finished file.
2. **Keep the final checks:** the exact pinned length, the SHA-256 equal to the pin **and** to the fresh official checksum, and a STOP on any mismatch. A file that changes mid-download fails the SHA check, which is correct.
3. **Record the evidence:** every attempt (offset, status, bytes) goes into `iso-download.json`.
4. **Local tests:** a fake server that drops once and then honours Range must pass; one that ignores Range must restart; one that always drops must STOP after 6 attempts; a wrong `Content-Range` must STOP.
5. If `pip` or the Playwright browser download also has no retry, add bounded retries there too (`pip --retries 5 --timeout 60`), without changing any version pins.

## Budget (owner's $3 cap)

About $0.55 is used. One push (about 6) plus a probe of at most 72 plus a qualification of at most 160 fits. Settings for package `14` only:
- `minute_cap`: **750**
- `dispatch_caps.probe`: **13**
- `owner-tools`: 3, with qualification 3 not yet used

## Then

1. Pinned local gitleaks, the replay and strict checks. Exactly **one** push.
2. Fresh exact-head privacy, the ledger, billing and the budget.
3. **Probe 13**. Only if it passes, **qualification 3 on the same head**.
4. The artifact rules from 14v apply.
5. Any stop: report it, no rerun.
6. When acceptance is met, restore closing 12 and reserve 150 in a final commit, push once, mark PR #13 ready for review, and say the run is over so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
