Reviewed `669d9f8..29c558f`, excluding archived logs, ZIPs and images.

1. **Blocking — contingency: fixed at source.** [offline_journal.py:97](/C:/Users/pab/AresOS-03-os-image/os/ci/offline_journal.py:97) requires both explicit kernel-mount incompatibility and absent reader tooling. Integrity, extraction, verification, missing/wrong-boot and record failures remain blocking. Verification precedes boot selection; new regressions exercise command failures directly. **Further fix:** none.

2. **Should-fix — updater audit: acceptable authorized reduction.** [audit.py:13](/C:/Users/pab/AresOS-03-os-image/os/tests/audit.py:13) rejects suspicious unreviewed units regardless of enablement state, and rejects masked-but-active/running ones. Static/generated definitions and both live managers are checked. Graph qualification is explicitly deferred in the follow-up brief. The literal [Cockpit mask](/C:/Users/pab/AresOS-03-os-image/os/policy/masked-system-units.txt:68) correctly blocks its generated service. **Further fix:** deferred graph work only.

3. **Should-fix — toolchain: fixed with precise exceptions.** [toolchain.json](/C:/Users/pab/AresOS-03-os-image/os/ci/toolchain.json:2) pins exact tool/firmware packages to a dated snapshot; installation isolates APT sources and reinstalls them. Mutable runner, kernel and existing-library inputs are explicitly documented and inventoried. **Further fix:** none within this scope.

Release configuration excludes CI overlays/fixtures and keeps accounts locked; credentials enter only the VM disk path. Recovery, power, journal, isolation and both-VM assertions remain intact.

Source is unchanged since the reported 03i tested commit. Diff whitespace checks passed. Builds/VMs were not rerun; live PR/CI verification was unavailable because `gh` could not read its configuration.

SAFE