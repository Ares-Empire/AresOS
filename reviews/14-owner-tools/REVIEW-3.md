**Finding 4: CLOSED.** The [new test](/C:/Users/pab/AresOS-14-owner-tools/os/tests/test_owner_export.py:89) now:

- Runs the unchanged owner `__main__` in isolated subprocesses and triggers a controlled `records unexpected` STOP.
- Requires the diagnostic under mapped `/var/lib/ares/diagnostics`, with no diagnostic JSON under mapped `/run`.
- Exports through the real owner command to a manifest-built fixture stick.
- Deletes the entire mapped `/run` tree after the processes exit, then exports again in a fresh process.
- Compares the persistent and exported diagnostic bytes exactly against the original, before and after that boundary.

The fixture preserves production path constants, recording, manifest checks and export logic; filesystem-root mapping and host-operation stand-ins are explicit.

The pre-14zzc negative control records the expected failure at the persistent-path assertion, after proving the STOP diagnostic was actually written. Its source and log hashes match the committed receipts. The corrected REPORT accurately separates local sequence coverage from existing VM export-route and `/var` persistence evidence.

`git diff 3fd7916..77d2f73 -- os/owner-tools docs/install-tools .github` is empty; all three Git tree IDs match. Payload fingerprint remains `3e2c78ebedf7789b0616e7a4f21ad791d76784667344e76e97a1fbd95115a6fd`.

**New defects: none identified within scope.** Tests were not rerun in this read-only review; code and committed results were checked. No files changed.

SAFE