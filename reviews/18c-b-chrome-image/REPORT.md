# 18c-b Chrome image package

## Done

Review fix round 1 preserves the newest shipment for a given Chrome build, checks the two CI-only payload
roots for absence in the release image, pins the signature error in container case 4, and checks and records
the mode of `control.json` in C1. The signing test catches a temporary named-file write even when the file is
deleted before return. The C2 evidence distinguishes successful capture from visual inspection.
[Fixes and mutations](PROGRESS.md#findings-and-mutations)

The package review requested changes. The security review gave a SAFE verdict with six NITs.
[Package review](REVIEW-1.md) · [Security review](SECURITY-REVIEW-1.md)

## Verified

The install and records Python suites passed 30 and 23 tests. The excluded-sites selections passed 9 and 3,
and the two named OS modules passed 49 and 98. The Node cross-check, the checkout records check and
`git diff --check` passed. Each source mutation was detected by its regression test.
[Commands and counts](PROGRESS.md#verified-locally)

The final pre-fix eight PR workflows passed on `6d610587`. OS regressions run 44908983067 passed on `b5091f42`
with 2,461 regressions, 23 skips and one separate ways-back test. The final pre-fix C2 artifact read shows the
square A button pinned in the toolbar and “Managed by your organization” in the menu. C2 requires successful
capture. The container install proof separately checks the pin.
[CI receipts](PROGRESS.md#final-head-verification) · [C2 artifacts](https://github.com/Ares-Empire/AresOS/actions/runs/44900848938/artifacts/14708622963)

## Not verified

- Before release and the owner's first Chrome tool use, show the full C8 question at his actual terminal
  size. Yes must submit the exact approved contents once and No must send nothing. Check this first in the
  live sitting with a synthetic form. 28b's combined profile proof is also required.
  [Guide](PROGRESS.md#for-his-guide) · [Release handoff](PROGRESS.md#for-linux-aresoss-release-brief)
- The real deployment switch with Chrome open, the probe-free update and rollback rehearsal, the owner's
  profile and excluded sites, and his polkit agent still need evidence. Keep the real list and its hash out
  of public evidence. [Live and release checks](PROGRESS.md#not-verified)

## JUDGMENT-CALL

The records tool keeps the existing row when equal-build shipment times tie. A commit-hash tie-break could
displace the row named by the current release manifest. Changing this later takes a comparator and test edit
and a review of any affected release row.

**Lead decisions, linux-tools, 2026-11-21.**

- **Reviews 3 and 6.** The helper remains barred from update-service traffic, which can carry its ID in a
  request body. The probe-only fallback compares deduplicated addresses and named IDs for Chrome's own
  background traffic. Count comparisons would be flaky, and a missed repeat risks exposing a random per-build
  ID without owner data. The pinned signer and one accepted C11 refresh suffice. The unit tests pin wrong-signer
  refusal and the no-published-record path fails closed with CI red.
- **Reviews 4 and 5.** Gate release and the live sitting on full C8 question visibility and exact Yes/No at the
  owner's actual terminal size, alongside the 28b proof. Record the standalone final-head build receipt once
  the run is green, including its guardian boots.
- **Review 8.** Approved the step 1b `prepare.mjs` runtime path lookup (`32f1126c`) for the older latency leg.
  The lead also approved the step 6b labwc change (`6d610587`) covering `os/Containerfile`, `os/labwc/stage.py`,
  `os/tests/test_aresos_desktop.py` and `os/tests/test_labwc_stage.py`. linux-aresos read it on 2026-11-21 at
  14:50 and wants it on `main` before R29's release build.
- **Security NITs 1, 4, 5 and 6.** Record one pseudonymous `gh` usage ping per refresh as a known limit.
  Add `GH_TELEMETRY=false` and an `XDG_STATE_HOME` under the cache when the hashed qualification file is next
  touched. The modulus tripwire lacks colon-separated hex, decimal and compressed forms, and the key stays in
  memory. The root-written list's format check accepts `true` and `1.0`. Keep the real list's hash private.
  [Package known limits](PROGRESS.md#known-limits)

## PLAN-GAP

The original negative check overlooked the two CI payload roots. The new check runs against the unlayered
image in both build modes. The normal C5 guest launch lacks the container's explicit stderr logging, and its
final log had no signature diagnostic. The guest retains its existing behavior checks. The container proof
now pins the reason. [Image and C5 evidence](PROGRESS.md#findings-and-mutations)

The two green step 6b Control runs did not exercise the standalone build's two guardian boots. The round's
standalone build 44912662660 did (**run**): both `GUARDIAN_VM_PASSED` lines and `CHECK_BUILD_VM_PASSED` (log 5697).
Both Control runs of the round (44912649303, 44927047698) and the eight PR checks are green, and recheck 1 said
SAFE. [Recheck and CI](PROGRESS.md#recheck-1-and-the-rounds-ci-2026-11-21-the-lead-linux-tools) ·
[Recheck 1](RECHECK-1.md)

## Open questions

Which release rollback source will be used for the shared-list hash comparison and browser-side install
checks, and when will the lead schedule 28b's combined proof? [Release handoff](PROGRESS.md#for-linux-aresoss-release-brief)

## Step 6b image check follow-up

### Done

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

### Verified

The labwc stage, desktop and Control image modules ran 126, 189 and 48 tests respectively,
with one desktop skip. [Local commands](PROGRESS.md#labwc-image-check-follow-up)

Both follow-ups passed at `6d610587`, attempt 1 in each run.

| Control run | Labwc PASS line | 18c VM total | 18c-b VM total |
|---|---:|---:|---:|
| [44893168374](https://github.com/Ares-Empire/AresOS/actions/runs/44893168374) | 4704 | 531.2 s (5751) | 383.0 s (5803) |
| [44900848938](https://github.com/Ares-Empire/AresOS/actions/runs/44900848938) | 4705 | 624.1 s (5752) | 418.9 s (5804) |

The daily-profile reconnect timeouts from 44621559332 attempt 1 did not recur. Both guests
passed the C4, C5 and C9 checks and completed C7 and C8. [Every PASS line and VM timing](PROGRESS.md#follow-up-control-runs)

### Not verified

The live sitting with the owner's Chrome profile and the probe-free release update and rollback
remain separate. [Existing review record](PROGRESS.md#not-verified)

### JUDGMENT-CALL

The single layer preserves Fedora's RPM metadata and both reviewed binary hash pins. Using a
different packaged timestamp could also break a metadata tie, but would change the package
contents and need its own reproducibility check. The layer fix can be moved independently of
the RPM build if the image recipe changes later.

### PLAN-GAP

The published release 28 image predates the rebuilt labwc, so its green image check cannot
serve as the baseline for the package 311 verification.

### Open questions

Which release rollback source will be used for the shared-list hash comparison and browser-side
installation checks? [Release handoff](PROGRESS.md#for-linux-aresoss-release-brief)
