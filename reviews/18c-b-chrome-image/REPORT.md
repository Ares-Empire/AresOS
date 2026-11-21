# 18c-b step 6b image check follow-up

## Done

Commit `6d610587` puts Fedora's labwc install and its verified replacement in the same
container layer. The labwc stage wiring test enforces this. The final image still has to pass
the full RPM verification.

Run 44888933298 verified the rebuilt RPM at installation (2992) and then reported
`..5......    /usr/bin/labwc` in the committed image (4704–4706). The likely cause is the
layer differ overlooking new bytes when the old and rebuilt binaries have identical file
metadata. The same rebuilt-RPM check passed in package 311's merge evidence (4531–4534)
and package 25's hosted check (4531–4534). Main has no direct image build since package 311.
The published release 28 comparison passed on Fedora's original RPM (2329 and 4298).
[Failed Control run](https://github.com/Ares-Empire/AresOS/actions/runs/44888933298) ·
[Package 311 run](https://github.com/Ares-Empire/AresOS/actions/runs/44511434325) ·
[Package 25 run](https://github.com/Ares-Empire/AresOS/actions/runs/44617007417) ·
[Release 28 run](https://github.com/Ares-Empire/AresOS/actions/runs/44590446680)

## Verified

The labwc stage, desktop and Control image modules ran 126, 189 and 48 tests respectively,
with one desktop skip. [Local commands](PROGRESS.md#labwc-image-check-follow-up)

Both follow-ups passed at `6d610587`, attempt 1 in each run.

| Control run | Labwc PASS line | 18c VM total | 18c-b VM total |
|---|---:|---:|---:|
| [44893168374](https://github.com/Ares-Empire/AresOS/actions/runs/44893168374) | 4704 | 531.2 s (5751) | 383.0 s (5803) |
| [44900848938](https://github.com/Ares-Empire/AresOS/actions/runs/44900848938) | 4705 | 624.1 s (5752) | 418.9 s (5804) |

The daily-profile reconnect timeouts from 44621559332 attempt 1 did not recur. Both guests
passed the C4, C5 and C9 checks and completed C7 and C8. [Every PASS line and VM timing](PROGRESS.md#follow-up-control-runs)

## Not verified

The live sitting with the owner's Chrome profile and the probe-free release update and rollback
remain separate. [Existing review record](PROGRESS.md#not-verified)

## JUDGMENT-CALL

The single layer preserves Fedora's RPM metadata and both reviewed binary hash pins. Using a
different packaged timestamp could also break a metadata tie, but would change the package
contents and need its own reproducibility check. The layer fix can be moved independently of
the RPM build if the image recipe changes later.

## PLAN-GAP

The published release 28 image predates the rebuilt labwc, so its green image check cannot
serve as the baseline for the package 311 verification.

## Open questions

Which release rollback source will be used for the shared-list hash comparison and browser-side
installation checks? [Release handoff](PROGRESS.md#for-linux-aresoss-release-brief)
