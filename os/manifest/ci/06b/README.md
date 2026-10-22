# 06b switch qualification evidence

Harness source: `cc341991bb4524dc37154f80f4256d1aff0a3b24`.
Unchanged published image source: `01aae1e38ec11356677f526692783c14b89a1d4d`.

- `preflight/`: inputs from successful checks-only run
  [39810919917](https://github.com/carlsenares/AresOS/actions/runs/39810919917),
  including 52 passing regressions and upstream signature verification.
- `switch-1/`: actual guest evidence and quota measurements from switch-only run
  [39811047831](https://github.com/carlsenares/AresOS/actions/runs/39811047831).
  Reboot into the exact published digest, native daily account, labwc/foot and
  unchanged attached-disk partitions passed. The existing policy assertion then
  failed: Homebrew is executable by `ares`. Real tty3 recovery, the full updater
  audit and rollback were not reached. There is no passing `result.json`.

Brief 06b requires stopping on a product failure. One of its two full runs was
used; no workaround, test change or second full run was attempted. This remains
a failed qualification. The raw stock QMP guest reset proves reboot; the AresOS
host-signal event is cleanup after the policy failure.

Original ZIPs, metadata, exact workflow output and visually inspected PNGs are
under [the package report](../../../../reviews/06-image-release/REPORT.md#06b-switch-qualification-2026-10-22).
The switch ZIP repeats the earlier successful image evidence; that repeated
image evidence is not a successful switch. No disks, credentials, raw
authentication transcripts, builder configuration or binary journals are kept.
Expanded text normalizes line endings and trailing whitespace; archives retain
the original bytes.
