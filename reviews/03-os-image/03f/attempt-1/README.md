# 03f attempt 1: failed live-audit invocation

[Run 39724835851](https://github.com/carlsenares/AresOS/actions/runs/39724835851),
source `65bda4dfe5442f177343d0d9149b13bf874403fe`, failed in the first VM.
The live manager inventory passed `-.mount` without `--`, so systemctl parsed
the root mount unit as an option. [policy-result.json](policy-result.json)
preserves the complete nested error. Commit `05f6531` fixes the invocation and
adds a dash-prefixed-root/alias regression. It also fixes and requires the new
canary export, found by source review before that path was reached.

All 31 regressions passed (`Ran 31 tests in 0.753s`, `OK`), along with syntax
checks, exact snapshot tool installation, upstream signature verification,
the 817-unit build audit, image/release isolation and disk construction.
The live activation assertions, normal guest policy, recovery, power events,
offline journals and second VM pass were not reached. This is failed diagnostic
evidence, not a successful VM result.

- [evidence.zip](evidence.zip): original, unaltered Actions evidence artifact,
  including manifests, tool/firmware versions and hashes, host inventory,
  metrics and first-VM diagnostic console/framebuffer/QMP results.
- [workflow-logs.zip](workflow-logs.zip): original GitHub workflow log download.
- `run.json`, `jobs.json`, `artifacts.json`: GitHub API metadata.
- `metrics.json`: unchanged copy of the artifact's measurement summary.

No image, VM disk, password, credential file, binary guest journal or builder
configuration is included. This is full attempt **1 of the 03f limit of 2**.
