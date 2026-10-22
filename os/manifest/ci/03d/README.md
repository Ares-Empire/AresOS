# 03d CI evidence

Acceptance remains unmet. Both allowed full attempts are counted; no third
full build ran. See the [03d report](../../../../reviews/03-os-image/REPORT.md#03d-offline-power-key-journal).

`attempt1/` is the small evidence artifact from failed run
[39713129693](https://github.com/carlsenares/AresOS/actions/runs/39713129693),
checkout `cb07f69dc04d779ea908b2a80c00c243ffdfd7fc`, with PNGs and console logs
retained separately under `reviews/03-os-image/`. Its first guest passed the
policy, raw exports, input-event, recovery PAM/getty and readiness checks.
QMP/console show guest-initiated shutdown, but read-only Btrfs mounting failed
before any journal records could be exported. `offline-commands.json` and
`offline-disk-layout.json` are reader diagnostics, not offline journal proof.
No offline boot/logind file, successful poweroff result or second pass exists.

`attempt2/` is the artifact from cancelled run
[39717408911](https://github.com/carlsenares/AresOS/actions/runs/39717408911),
checkout `a798f574bb36a9be41d17bef640ec1bb109ab353`. Its 22 regressions passed;
cancellation completed after image building began, so it counts as attempt 2.
It produced no completed image/disk or guest evidence. The final Podman `:r`
correction is not covered by a CI run. The extraction fallback is unverified.

The combined final push automatically launched workflow `39718242619` despite
the earlier correction commit's skip marker. It was force-cancelled during
runner cleanup, before tool installation or any build. Its separate run/job
metadata and the ledger under `reviews/03-os-image/03d/` prove that it produced
no artifact, image or guest and does not add a full build attempt.

The release OCI manifest/digest and separate CI-image manifest/digest are in
`attempt1/`; the raw guest bootc status identifies the latter. Guest JSON bytes
are unchanged and their original export checksums remain in `export-result.json`.
Screenshots show the labwc terminal and independent tty3 getty; PAM acceptance
is recorded separately, not established by the getty image. Neither images,
disks, credentials nor builder configuration are included.
