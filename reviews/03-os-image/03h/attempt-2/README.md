# Full attempt 2: static audit catches generated Cockpit entry point

[Run 39749001395](https://github.com/carlsenares/AresOS/actions/runs/39749001395),
source `c5473259e537ef38621a34899e8d330e9a360e36`, failed in VM 1's normal-policy
audit. The strict scanner found `/run/systemd/generator/cockpit-container.service`
with `io.containers.autoupdate=registry` and mutable `quay.io/cockpit/ws:latest`
in its privileged Podman command. It was generated, unmasked and not allowlisted;
active/load/substate were absent, so no running updater is claimed. The strict
rule requires a mask even for dormant entry points.

All 38 regressions, syntax/tool/signature/RPM/driver checks, the 817-unit build
audit, both lint invocations (10 passed / 1 skipped / 4 inherited warnings),
release isolation and disk construction passed. VM 1 reached labwc/foot,
unprivileged-account, updater-executable, desktop-exclusion and all named mask
checks. Reaching `guest.sh` implies the static/generated canary check returned
zero under the unchanged `checks.py` ordering; its detailed JSON was not exported
because the host exports only after the whole policy action succeeds.

Recovery, power/input, offline journal/logind proof and VM 2 were not reached.
The [inspected framebuffer](../../screenshots/03h-attempt-2-failed-boot.png)
shows the AresOS terminal only.

After the **2/2 full-run stop**, add the literal `cockpit-container.service` mask
and a regression for generated container-auto-update content, masked acceptance
and masked-but-active rejection. [Final checks-only CI](../checks-3/README.md)
passes; **the corrected mask has not been rebuilt or booted**. No third full run.

[Exact selected output](verification-output.txt), [complete guest error](policy-result.json),
[run](run.json), [jobs](jobs.json), [artifact metadata](artifacts.json),
[credential-redacted workflow ZIP](workflow-logs.zip), [original evidence ZIP](evidence.zip),
[SHA-256 comparison](archive-verification.txt),
[raw failed-build manifests](../../../../os/manifest/ci/03h/README.md).
All 39 artifact entries match the expanded download; its ZIP hash matches GitHub.
The workflow ZIP redacts two occurrences of the VM-only password hash printed
by the disk builder; [redaction record](log-redaction.txt). The artifact ZIP is unchanged.
