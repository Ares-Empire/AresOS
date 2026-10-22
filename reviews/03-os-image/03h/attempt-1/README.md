# Full attempt 1: graph audit race; authorized split selected

[Run 39742496374](https://github.com/carlsenares/AresOS/actions/runs/39742496374),
source `afbb80a16116295b85cd4e985d787e32c1fa2958`, failed in the first VM's
activation-canary check. `inventory(live=True)` tried to read the vanished
`/run/systemd/transient/dbus-:1.4-org.fedoraproject.SetroubleshootPrivileged@0.service`
fragment and raised `FileNotFoundError`. The canary rejection, normal policy,
recovery, power and second VM were not reached. The inspected
[failure framebuffer](../../screenshots/03h-attempt-1-failed-boot.png) shows labwc
with the AresOS terminal; it is not policy/power evidence.

Before that, all 34 regressions, syntax/tool/signature/RPM/driver checks, the
817-unit build audit, both container lint invocations (10 passed / 1 skipped /
4 inherited warnings), release isolation and disk construction passed. The
release-container preflight was diagnostic but actually passed on this run:
systemd 259.9, 801 system / 270 user names, including the escaped-name, alias,
dependency and spaced-drop-in probes. Its
[stdout](fedora-parser-preflight.txt), [service status](fedora-container-status.txt)
and [user-manager journal](fedora-container-user-journal.txt) are retained.
The original artifact contains the exact compressed systemctl transcript.

Brief 03h explicitly selects the static strict rule after this kind of failure.
The graph implementation, activation canaries and container preflight are
deferred in [the follow-up brief](../../../../briefs/03-followup-activation-audit.md).
Generated-unit rejection remains covered in static form. No unrelated assertion
was weakened, and no missing-file exception was silently ignored.

[Selected exact output](verification-output.txt), [guest error](policy-result.json),
[metrics](metrics.json), [run](run.json), [jobs](jobs.json),
[artifact metadata](artifacts.json), [credential-redacted workflow ZIP](workflow-logs.zip),
[original evidence ZIP](evidence.zip), [SHA-256 comparison](archive-verification.txt).
All 46 artifact entries match the expanded download; its ZIP hash matches GitHub.
No image, disk, credentials or builder configuration is retained.
The workflow ZIP redacts two occurrences of the VM-only password hash printed
by the disk builder; [redaction record](log-redaction.txt). The artifact ZIP is unchanged.
