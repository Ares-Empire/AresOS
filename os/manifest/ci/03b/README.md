# 03b evidence: acceptance not met

`attempt3/` contains generated evidence downloaded with `gh run download` from
[run 39698003724](https://github.com/carlsenares/AresOS/actions/runs/39698003724),
source `5991246e5bbd5db52248432cbccff26ac1ff999b`. Its `provenance.json` records
the verified base and resulting unsigned, unpublished image. `jobs.json` and
`artifacts.json` came from the GitHub API. Earlier follow-up attempts' metadata
and metrics are under `reviews/03-os-image/03b/`.

The image build and first guest's static policy checks passed, but export framing
failed before injected power events or authenticated VT3 recovery. The second
guest pass never started. There is no successful TTY proof, power-event result,
poweroff file or green workflow in this snapshot.

- `attempt3/vm-pass-1/backend.json` is the raw `bootc status --json` file that CI
  successfully exported. Its SHA-256 is
  `83b9cd3a9ecb7d04c5b343d1da3cdb0c3c84dd3dd81eb21219f6ec16b677333e`.
- `attempt3/updaters.json` is the **image-build** inventory (815 units).
- `attempt3/vm-pass-1/runtime-updaters.recovered.json` is **recovered runtime
  output**, not a successful automated export. It contains 828 units: 669 system,
  159 user; 52 system and 43 user units have state `masked`. The complete base64
  payload was present between the second pair of `ARESOS_EXPORT_START/END`
  markers in the raw serial capture. Removing the one inserted kernel record
  below, joining whitespace and decoding base64 produced 160,131 bytes of valid
  JSON, matching the guest audit's 828-unit count. No unit entry was edited or
  inferred. The recovered file's local SHA-256 is
  `c49761edd10c74a379e32e9544a36757906bc72b5d177ad1ba6b14e0acdca59c`;
  **this was not a checksum transmitted by the guest**.

The removed kernel record, including its line ending, was:

```text
[   63.397535] clocksource: Long readout interval, skipping watchdog check: cs_nsec: 2683950338 wd_nsec: 2683949311
```

The lossless, password-redacted source is
[`serial-console.zip`](../../../../reviews/03-os-image/03b/attempt3/serial-console.zip),
containing the artifact's unmodified `serial.log`. Recovery used the exact regex
`\[\s*\d+\.\d+\][^\r\n]*(?:\r?\n|\r)` to remove that single record, removed
remaining whitespace, and decoded with PowerShell's
`[Convert]::FromBase64String`; `ConvertFrom-Json` parsed all 828 records.

The subsequent source fix adds wrapped base64, the same narrowly recognized
kernel-record removal and a **guest-computed SHA-256** before accepting exports.
That fix and its three new regressions have not run. It is deliberately committed
with `[skip ci]` because the brief's three additional full attempts are exhausted.
It must pass a newly authorized full run before this PR can be made ready.

The diagnostic screenshot is under `reviews/03-os-image/screenshots/` and shows
only the labwc/AresOS terminal. No image, VM disk, credentials or builder
configuration is committed. All generated source and result references remain
separate from the later, unverified framing fix.
