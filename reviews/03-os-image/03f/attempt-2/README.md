# 03f attempt 2: failed quoted dependency parsing

[Run 39729374555](https://github.com/carlsenares/AresOS/actions/runs/39729374555),
source `cba88bb58c6bee08613fdac2ae0e7197b610a2e3`, failed in the first VM.
systemctl shell-quoted a dependency name containing literal unit-name escapes;
the inventory passed those quotes back as part of the name. Its missing-unit
assertion correctly failed. [policy-result.json](policy-result.json) retains
the complete nested error. Commit `f3aaff1` fixes string-vector parsing with
`shlex.split`; `83b7c9d` fixes the new test fixture's runuser argument window.
That final code passes the separate checks-only run, but has not been rebuilt
or booted in this guest.

All 32 regressions passed (`Ran 32 tests in 0.773s`, `OK`), along with exact
snapshot version checks/reinstallation, syntax/signature checks, preserved
kernel/NVIDIA packages, the 817-unit build audit, image/release isolation and
disk construction. Actual canary rejection, normal guest policy, recovery,
power events, offline journals and pass 2 were not reached.

- [evidence.zip](evidence.zip): original, unaltered Actions evidence artifact.
  All 39 entries were hash-compared to the `gh run download` result.
- [workflow-logs.zip](workflow-logs.zip): original GitHub workflow log download.
- `run.json`, `jobs.json`, `artifacts.json`: original API metadata.
- `metrics.json`: unchanged measurement summary from the artifact.
- [Build manifest index](../../../../os/manifest/ci/03f/README.md): raw
  build/tool/firmware evidence from this failed build.

No image, VM disk, credential, binary guest journal or builder configuration is
included. This is full attempt **2 of 2**. Both permitted attempts failed; no
third full run was started. The screenshot in the report establishes a visible
terminal only, not passed policy/recovery/power assertions.
