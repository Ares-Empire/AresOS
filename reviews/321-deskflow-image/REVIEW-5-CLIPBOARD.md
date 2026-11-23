# Package 321: clipboard review (Codex gpt-6.2-sol high, read-only, at 52c99893, 2026-11-23)

CHANGES-NEEDED

`os/input-portal/src/portal.rs:2340` fixes the `RequestClipboard`/`Start` race, but introduces a D-Bus deadlock. An inline Clipboard handler awaits `GetNameOwner` on the serving connection (`os/input-portal/src/portal.rs:673`). If the incoming method queue fills, zbus stops reading the socket before it reaches that reply, while the dispatcher waits for the reply before draining the queue. The 500 ms timeout starts after authorization, so it cannot break the deadlock.

This can stall `--revoke` and the normal `--release` request. The independent Off watcher and the pidfd fallback still provide recovery. I found no new path to arm two sessions, bypass the forwarding gate, or send clipboard data outside the existing trust boundary. Keep negotiation ordered without the unbounded lookup on the serving connection.

The saved harness evidence matches `PROGRESS.md`. Test 5 recorded `clipboard_enabled=false` on the dispatch 15 binary. Both runs on the new pin passed all 137 checks, and both saved binaries match `os/manifest/input-portal.sha256`. The harness reproduces the negotiation failure. Deskflow relogin on the corrected image remains unverified. I reviewed the deadlock in source and did not rerun the harness.

Lead: fixed in clipboard fix 2.
