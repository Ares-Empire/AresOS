# Checks-only 2: real Fedora base parser passed

[Run 39738388625](https://github.com/carlsenares/AresOS/actions/runs/39738388625)
on `06da4b82fe968fa8e87c27afbdcb2559808bbb09` passed all 34 regressions,
syntax checks and the Ubuntu manager query (437 files / 598 names). It also
ran `bash os/ci/parser-preflight.sh --base`, using the signature-verified pinned
Bazzite base, the current audit and a disposable UID-1000 `ares` account.
No image/disk was built and no VM ran.

Real systemd `259.9-1.fc44` parsed inventory: **799 system / 276 user unit names**.
Both scopes preserved escaped unit names, aliases, activation dependencies and
a drop-in path with spaces. This base result does not qualify the configured
release, whose user-manager startup subsequently failed in full attempt 2.

- [Exact command/stdout transcript](fedora-systemctl-transcript.jsonl.gz),
  [parsed probes](fedora-parser-preflight.json), [systemd version](fedora-systemd-version.txt).
- [Selected output](verification-output.txt), [original workflow ZIP](workflow-logs.zip),
  [original 16-entry evidence ZIP](evidence.zip).
- [Run](run.json), [jobs](jobs.json), [artifact metadata](artifacts.json).
