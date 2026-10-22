# Package 03: OS image

Status: **03i acceptance met.** [Full run 39756953602](https://github.com/carlsenares/AresOS/actions/runs/39756953602) is green on `a4eaca14b2b7c8aaef8dd4b815b2abe73fce47e5`, including both fresh VM passes, canary rejection, normal updater policy, recovery, input/power and actual offline logind proof. The existing Cockpit mask needed no further code change. **1/2** authorized full runs used, preceded by green checks-only CI. [PR #3](https://github.com/carlsenares/AresOS/pull/3) remains open, non-draft and unmerged. Earlier sections are historical; hardware, installation and the deferred activation graph remain unqualified.

## 03i: verify the static audit with the Cockpit mask

### Done

- Verify the existing literal `cockpit-container.service` mask and its regression through a complete image build and two fresh KVM/UEFI guests. No production code, policy, allowlist, assertion, test or workflow changed; no additional inherited updater was exposed.
- Preserve [03i run/job metadata, logs and the original evidence archive](03i/README.md), [raw release/VM manifests and per-pass results](../../os/manifest/ci/03i/README.md), and six inspected [screenshots](03i/attempt-1/README.md#screenshots). Update this report and PR #3's description.

### Verified

Both dispatched workflows used source **`a4eaca14b2b7c8aaef8dd4b815b2abe73fce47e5`**:

- **Checks-only first:** `gh workflow run os-image.yml --ref pkg/03-os-image -f checks_only=true`, [39756899131](https://github.com/carlsenares/AresOS/actions/runs/39756899131), **success**. Printed **`Ran 39 tests in 0.783s`, `OK`** and **`Live hosted system manager passed: 437 unit files, 466 unit names`**. The image job was skipped. [Exact output and original logs](03i/checks-1/README.md).
- **Full attempt 1:** `gh workflow run os-image.yml --ref pkg/03-os-image -f checks_only=false`, [39756953602](https://github.com/carlsenares/AresOS/actions/runs/39756953602), **success**. Printed **`Ran 39 tests in 0.766s`, `OK`**. Pinned tool installation, upstream signature verification, locked RPM installation and protected kernel/NVIDIA package checks passed. The build audit printed **`Updater audit passed: 818 system/user units inspected`**. Both container lint invocations printed **10 passed / 1 skipped / 4 warnings**, unchanged inherited lint results. Release isolation printed **`Release excludes CI service and credentials; both passwords locked`**. Disk construction printed **`Build complete!`**. [Exact selected output, complete logs and artifact](03i/attempt-1/README.md).

Both workflows ran these commands on disposable hosted runners, all successfully:

```text
python3 -m unittest discover -s os/tests -v
python3 -m py_compile os/ci/*.py os/ci/overlay/*.py os/tests/audit.py os/tests/power-events.py
bash -n <each script listed below>
```

Bash syntax checks covered `os/ci/install-tools.sh`, `os/ci/parser-preflight.sh`,
`os/ci/overlay/updater-generator`, `os/build.sh`, `os/tests/guest.sh`,
`os/config/usr/bin/aresos-session` and `os/config/usr/bin/aresos-terminal`.
Python/Bash syntax checks produced no error output. The full workflow then built
both release stages and the isolated overlay, built the disk and ran
`sudo -E env ARESOS_VM_PASS="$pass" python3 os/ci/vm.py` for passes 1 and 2.

| Required guest evidence | VM pass 1 | VM pass 2 |
|---|---|---|
| Static/generated updater canaries | Both rejected; audit exit 1; `status=passed`, `mode=static-strict` | Same |
| Normal runtime audit after fixture removal | 1,088 units: 807 system / 281 user; zero offenders | Same |
| Generated Cockpit container fragment | Detected and masked; no live-manager entry | Same |
| Recovery shortcut, tty3 getty and login PAM | Pass; wrong password rejected, correct password/account accepted as UID 0 | Same |
| Lid close/open and suspend/hibernate keys | Observed and ignored; session PIDs retained | Same |
| All four direct logind sleep requests | Rejected as disabled by configuration | Same |
| QMP shutdown and console | `guest=true`, `reason=guest-shutdown`, QEMU exit 0; poweroff target reached | Same |
| Verified offline journal/logind path | `passed`, boot `b854391a357041369180be760f446df2` | `passed`, boot `2c3026bde47b4cc9b1a33718c1fa546a` |

Both raw inventories retain `/run/systemd/generator/cockpit-container.service`
and its privileged Podman command, auto-update label and mutable `:latest`
reference. The literal mask is effective. Neither inventory contains an
unreviewed suspicious unmasked unit or an unreviewed suspicious unit in an
active/activating/reloading/deactivating/running state. The canaries' generated
and static definitions are retained separately in each pass's rejection proof.

In both passes the runner's kernel mount failed; the existing read-only Btrfs
userspace path successfully extracted the primary root tree's persistent journal.
The matching release-image `journalctl` verified it and read the exact guest boot.
Each proof orders the armed marker, logind's structured **`Power key pressed short.`**,
its **`SHUTDOWN=power-off`**, then PID 1's successful logind stop. **Neither pass
used the hardware-gate contingency.** Read-only NBD disconnect succeeded in both
passes. [Raw proof and command records](../../os/manifest/ci/03i/README.md).

Both raw `bootc status` exports identify **bootc with OSTree storage**
(`store=ostreeContainer`) and test-image digest
**`sha256:cfe1029721b3680f9782870c2ea63ca8b72a2b0000aebc0725522203eba7fbda`**.
The separate release OCI digest is
**`sha256:05c27647e0b7e69d90208d99b5ff3873df71b7fa78a744f4fd50bb61349230d7`**.
[Provenance](../../os/manifest/ci/03i/provenance.json) binds the source, base and run.
The unchanged base's package inventory records kernel **6.18.56-ogc1.1.fc44** and
NVIDIA **580.178.04**; these are package checks, not GPU hardware qualification.

All six downloaded framebuffers were visually inspected. Both session images
show the AresOS terminal and recovery hints; both tty3 images show a login prompt.
The final frames are dark diagnostics with a small Bazzite label, not shutdown
proof or evidence of an interactive login. Raw PAM/getty, journal and QMP records
provide their respective assertions.

Downloaded the original artifact ZIP and expanded evidence with `gh`. Its SHA-256
matches GitHub metadata, and all **103** entries match the expanded download.
The full workflow archive redacts **two** VM-only password-hash occurrences;
the checks-only workflow archive and evidence ZIP remain byte-for-byte original.
No password hash was found in artifact text files. Local PowerShell/.NET checks
verified 63 expanded raw copies, both manifest identities, 69 relative document
links and 51 JSON files. The first `git diff --cached --check` flagged carriage
returns in expanded raw `poweroff.txt` excerpts; those excerpts are retained
unchanged in the original ZIP. Final `git diff --check` and `git diff --cached --check`
passed. No local code test/build/VM/Gradle task ran.

### Budget and measurements

**1/2 full attempts used; no second attempt or rerun.** The full workflow took
**47m32s**; checks-only took **12s**; combined elapsed **47m44s**, using GitHub
created/updated timestamps, not billing data. [Run ledger](03i/ci-runs.json).

| Measurement | Observed value |
|---|---:|
| Base / release uncompressed bytes | 13,010,242,255 / 13,195,031,848 |
| VM disk virtual / allocated bytes | 31,666,995,200 / 9,470,160,896 |
| Runner highest sampled used / total bytes | 70,696,677,376 / 76,887,154,688 |
| Runner lowest sampled free bytes | 6,173,700,096 |
| Compressed evidence artifact bytes | 3,179,160 |

Disk usage is sampled every ten seconds and includes disposable VM overlays;
these are sampled extrema. The artifact expires **2026-10-25 10:25:41 UTC** and is
now preserved in the branch. Only evidence was uploaded; no image, disk,
credential file, builder configuration or binary journal. No registry
publication, paid runner, billing change or installation was performed.

### Not verified

The deferred activation graph, transient effective commands, aliases and dependency
traversal still require [their separate follow-up](../../briefs/03-followup-activation-audit.md).
This run qualifies the authorized static/generated audit and live-state checks.
The prototype graph's passing unit tests do not qualify it in a guest.

No laptop/NVIDIA rendering, physical lid/button, battery/dock, firmware,
installation, rebase/rollback or Windows-return test was performed. Interactive
TTY login through banner/shell startup still needs a human; CI proves its active
tty3 getty plus unchanged login PAM password/account checks. Private image
delivery and independently provisioned recovery access remain release gates.
`mod/` is unchanged. The OS brief prohibits local builds; no Gradle daemon was
started, so none needs stopping. This prototype is not an installation release.

### JUDGMENT-CALL

None new. The existing Cockpit mask and 03h static split are verified unchanged.
No additional mask/removal, allowlist entry or policy choice was needed.

### PLAN-GAP

No new gap exposed by this run. The previously missing full verification now
exists with actual offline logind proof in both guests. The deferred graph and
hardware/release gates remain as documented. The builder still prints VM-only
password hashes into CI logs; retained full-run logs redact those two occurrences.

### Open questions

None specific to 03i. Existing hardware, image-delivery and recovery-account
decisions remain separate. PR #3 remains open, non-draft and unmerged.

## 03h: converge PR #3 with the authorized static split

### Done

- `.github/workflows/os-image.yml`, `os/ci/parser-preflight.sh`: first make the configured-release container preflight diagnostic and preserve manager status/journal. Full attempt 1 reached the VM, where the graph audit failed on a disappearing transient fragment. Apply brief 03h's pre-decided fallback for attempt 2. Neither workflow mode now invokes the deferred preflight; checks-only runs regressions, syntax checks and a real hosted-manager state query.
- `os/tests/audit.py`: require every suspicious installed/generated unit to be masked or literally reviewed, regardless of unit-file state. Scan static definitions/drop-ins, loaded instances' templates and system/user generator directories. Require both live managers' unit-file and active/substate snapshots. Reject unreviewed suspicious units that are active, activating, reloading, deactivating or running even if masked. Individually allowlisted local bookkeeping remains permitted.
- `os/ci/overlay/`: replace timer-activation acceptance with static strict-rule canaries. Each VM must reject an unenabled static updater and a real boot-generated updater, retain their commands/source/state evidence, then remove/regenerate the fixtures before normal-policy checks. Both conditions prevent updater execution. Add the static fixture to the release-isolation exclusions; preserve all earlier exclusions.
- Preserve `os/ci/activation_audit.py`, `activation_canaries.py`, the unused routine/timer fixtures and container parser harness for [the follow-up brief](../../briefs/03-followup-activation-audit.md). The graph implementation is outside the release build context. All earlier graph/parser tests still run against the prototype; four new static/live-state tests bring the suite from 34 to 38. No recovery, power/input, offline-journal reader/classifier, contingency, toolchain or production-policy file changed in the split.
- `os/policy/masked-system-units.txt`: after attempt 2 exposes the generated Cockpit container entry point, add its literal mask rather than allowlisting its mutable, privileged container command. A new regression detects its auto-update label, accepts the inactive mask and rejects generated/unmasked or active variants. The final correction is checks-only verified, not rebuilt/booted.
- Retain [evidence archives and exact results](03h/README.md), failed-build manifests and both failure framebuffers. Redact VM-only password hashes from the full workflow ZIPs before committing; artifact ZIPs remain original. Update the PR description and keep PR #3 open and non-draft; do not merge. **Acceptance remains unmet.**

### Verified

- **Full attempt 1:** [39742496374](https://github.com/carlsenares/AresOS/actions/runs/39742496374), source `afbb80a16116295b85cd4e985d787e32c1fa2958`, **failure**. Suite: **`Ran 34 tests in 0.773s`, `OK`**. Tool/signature/RPM/driver checks, the **817-unit** build audit, both container lint invocations (**10 passed / 1 skipped / 4 inherited warnings**), release isolation and disk construction passed. The now-diagnostic configured-release preflight actually passed: systemd **259.9-1.fc44**, **801 system / 270 user** names with real escaped-name, alias, dependency and spaced-drop-in probes. The first VM's graph inventory then raised `FileNotFoundError` reading `/run/systemd/transient/dbus-:1.4-org.fedoraproject.SetroubleshootPrivileged@0.service`. Canary rejection, normal policy, recovery, power/offline assertions and VM 2 were not reached. [Exact error, logs/artifact and diagnostics](03h/attempt-1/README.md). Its [inspected framebuffer](screenshots/03h-attempt-1-failed-boot.png) shows the AresOS labwc terminal, not completed policy/power evidence.
- **Checks-only before attempt 2:** [39748939881](https://github.com/carlsenares/AresOS/actions/runs/39748939881), source **`c5473259e537ef38621a34899e8d330e9a360e36`**, **success**. Printed **`Ran 38 tests in 0.840s`, `OK`** and **`Live hosted system manager passed: 437 unit files, 475 unit names`**. The image job was skipped; no image, container, disk or VM ran. [Exact output and original logs](03h/checks-1/README.md).
- **Full attempt 2:** [39749001395](https://github.com/carlsenares/AresOS/actions/runs/39749001395), the same source **`c5473259e537ef38621a34899e8d330e9a360e36`**, **failure**. Printed **`Ran 38 tests in 0.812s`, `OK`**; the same tool/signature/RPM/driver checks, **817-unit** build audit, both lint results (**10 passed / 1 skipped / 4 inherited warnings**), release isolation and disk construction passed. VM 1 reached labwc/foot, account restrictions, executable restrictions, desktop exclusions and all named masks, then the static audit correctly rejected **generated `cockpit-container.service`**: its command contains `io.containers.autoupdate=registry`, privileged host access and mutable `quay.io/cockpit/ws:latest`. No active/load/substate was recorded for it; no running updater is claimed. Reaching `guest.sh` implies the preceding static/generated canary check returned zero under the unchanged check order, but its detailed JSON was not exported because the whole policy action failed. Recovery, power/input, offline journal/logind proof and VM 2 were not reached. [Exact error and original evidence](03h/attempt-2/README.md), [inspected failure framebuffer](screenshots/03h-attempt-2-failed-boot.png).
- **Final correction, checks-only:** add the exact Cockpit mask. [39755103185](https://github.com/carlsenares/AresOS/actions/runs/39755103185), source `59253df`, printed **`Ran 39 tests in 0.842s`, `FAILED (errors=1)`**: the new fixture's empty user-unit tree made real rooted `systemctl --global list-unit-files` return 1. Populate it with a harmless user unit while retaining all assertions. [39755280120](https://github.com/carlsenares/AresOS/actions/runs/39755280120), final code **`9b29c0297aac6bb77dc9ed10a244f0a856e603ce`**, passed **`Ran 39 tests in 0.691s`, `OK`**, syntax checks and **`Live hosted system manager passed: 437 unit files, 465 unit names`**. Both image jobs were skipped. [Fixture failure](03h/checks-2/README.md), [final green checks-only output](03h/checks-3/README.md). **No full run of this final correction exists.**

Both full runs executed on disposable hosted runners:

```text
python3 -m unittest discover -s os/tests -v
python3 -m py_compile os/ci/*.py os/ci/overlay/*.py os/tests/audit.py os/tests/power-events.py
bash -n <each script listed below>
```

Bash checks covered `os/ci/install-tools.sh`, `os/ci/parser-preflight.sh`,
`os/ci/overlay/updater-generator`, `os/build.sh`, `os/tests/guest.sh`,
`os/config/usr/bin/aresos-session` and `os/config/usr/bin/aresos-terminal`.
Both full runs and successful checks-only runs passed Python/Bash syntax checks
without error output; the failed fixture run stopped at unittest. Downloaded
both artifacts with `gh run download <id> --name os-image-evidence`, and their
original ZIPs/logs with `gh api`. Local PowerShell/.NET SHA-256 comparison found
**46/39 matching entries** and both ZIP hashes match GitHub metadata. Both
full-run workflow ZIPs have the builder's ephemeral VM password hashes redacted
(two occurrences each); checks-only workflow ZIPs are original downloads.
The artifact ZIPs are unchanged. Both
failure framebuffers were visually inspected: each shows the AresOS terminal,
not completed policy/recovery/power checks. Local `git diff --check` and
`git diff --cached --check` passed without output; PowerShell checked all **71**
relative links in the current report section, README, follow-up and evidence
indexes and printed **`Relative document links passed: 71`**.

### Budget and measurements

**2/2 full attempts used.** One checks-only run preceded attempt 2, with two more
checks-only runs after its failure. No third full
run, rerun, local image/VM build, registry publication, paid runner or billing
change. Full attempts took **92m22s** total; checks-only took **37s**; combined
elapsed **92m59s**. [Run ledger](03h/ci-runs.json).
Times use GitHub created/updated timestamps, not billing data.

| Measurement | Attempt 1 (graph failure) | Attempt 2 (static split) |
|---|---:|---:|
| Workflow elapsed | 46m40s | 45m42s |
| Base uncompressed bytes | 13,010,242,255 | 13,010,242,255 |
| Release uncompressed bytes | 13,195,097,892 | 13,195,028,264 |
| VM raw disk virtual / allocated bytes | 31,666,995,200 / 9,362,120,704 | 31,666,995,200 / 9,521,922,048 |
| Highest sampled used / total bytes | 70,209,118,208 / 76,887,154,688 | 70,797,598,720 / 76,887,154,688 |
| Lowest sampled free bytes | 6,661,259,264 | 6,072,778,752 |
| Compressed evidence artifact bytes | 310,475 | 246,523 |

Disk samples are ten seconds apart. Evidence-only artifacts have three-day
retention and are now preserved locally; no image, disk, credential file, builder
configuration or binary journal is in those artifacts. The builder did print
VM-only password hashes into GitHub's workflow logs; committed copies redact them.
Both artifacts total **556,998
bytes**. Attempt 2's failed release digest is
**`sha256:2570db23070b56a274a057373a5d57c2572e7240d874fb6c400008d633484cab`**;
test-layer digest is
**`sha256:733559c21ab77ffa9dedf306d9f45abfa8968503b2bda0094310e5ba3527d533`**.
[Raw provenance/manifests](../../os/manifest/ci/03h/README.md) bind these to
`c547325`, not the later mask correction. No live backend JSON or successful
runtime/canary export was retrieved in either run.

### Not verified

**03h acceptance is NOT met.** Neither full run completed normal policy or VM 2;
no recovery, power/input, offline extraction/verification/logind proof or actual
hardware-gate contingency result exists for this source. The final Cockpit mask
is unit-tested but has not been rebuilt/booted. A separately authorized full
run with both fresh VMs remains necessary.

The **activation graph is deferred**, not qualified by partial static evidence:
effective transient commands, manager-reported aliases/fragment paths and
dependency traversal need the separate follow-up. Attempt 1's passing container
probe does not diagnose 03g's earlier user-manager startup failure.

No local code tests, builds, installs, containers, VMs or Gradle tasks ran,
following the OS brief's runner-only constraint. `mod/` is unchanged; no Gradle
daemon was started. Physical power/lid behavior, NVIDIA operation, interactive
recovery login, installation/rebase/rollback, Windows return and the private
image-delivery/recovery-account prerequisites remain hardware/release gates.
No offline contingency was reached in either full attempt. The narrowed reader
classifier remains unchanged and regression-tested; mock contingency messages
are not guest power-key evidence. This prototype is not an installation
release.

### JUDGMENT-CALL

Apply the integrator's explicit 03h decisions: a release-container preflight is
diagnostic only, and a VM graph-audit failure selects the static strict rule
with a separate activation-audit follow-up. The alternatives were another graph
repair cycle or silently ignoring vanished files; neither was authorized by the
pre-decided split. The split itself changes no production settings. Restoring graph acceptance
costs a separate reliability fix, canary qualification and CI budget.

Mask the newly discovered Cockpit container unit instead of treating its mutable
container/auto-update label as reviewed bookkeeping. This follows the strict
rule even though Podman's automatic updater is already masked and Cockpit was
not observed running. It disables that optional web-console service; restoring
it later is a reversible policy change requiring explicit maintenance review.

### PLAN-GAP

The graph implementation assumed every manager-reported transient fragment
survives until its later file read. Real boot disproved that assumption. The
follow-up requires evidence-preserving lifecycle-race handling, not blanket
missing-file suppression. Generated-unit coverage remains in the static form
and exposed a genuine missing mask that no build-time inventory could see before
the generator ran. Its correction arrived after the last authorized full run.
The required green full run with both fresh VMs is still missing; the checks-only
result cannot substitute for it. No unrelated assertion or allowlist was weakened.

The disk builder prints the VM account's password hash in its customization log.
The new retained workflow archives redact it; suppressing this field at the log
source belongs in the next CI verification follow-up. No actual password or
credential file is retained in the new evidence.

### Open questions

**A new verification brief/budget is needed for the final mask correction and
both complete fresh VMs.** No third full attempt was started. Existing hardware, NVIDIA-family qualification,
image-delivery and recovery-account gates remain; this run authorizes none of
their installation or publication steps.

## 03g: verify 03f in full VM runs

### Done

- `.github/workflows/os-image.yml`, `os/ci/parser-preflight.sh`, `os/ci/parser_preflight.py`: add the requested pre-boot check against real Fedora systemctl output. Start the built release's systemd at `basic.target` in a disposable, network-isolated Podman container, start its system and `ares` user managers, then drive the installed audit's complete live inventory. Temporary probes exercise literal escaped unit names, aliases, activation dependencies and a drop-in path containing spaces in both scopes; the root mount also has to be loaded. Retain exact command/stdout pairs in compressed JSON lines, systemd version and parsed probe records. This step blocks overlay/disk/VM construction on failure.
- Attempt 1 revealed that Bazzite's `/opt` resolves through an absent directory in this container. Commit `06da4b8` moves the script mount to the existing `/usr/libexec` directory. Before spending attempt 2, extend checks-only CI to run the same harness against the signature-verified, digest-pinned Bazzite base, with the current audit mounted and a disposable UID-1000 `ares` account. It builds no image or disk and starts no VM. **That base preflight passed; the built release's user-manager startup did not.**
- `os/README.md`, evidence indexes and this report document the results and budget stop. Retain all four run/job metadata sets, original workflow-log ZIPs, three original artifact ZIPs and selected exact output. The latest failed release's raw build manifests are under `os/manifest/ci/03g/`. PR #3's description is updated without merging.
- No production audit, policy, VM assertion, canary, offline-reader code or regression assertion changed from the final 03f correction. No code correction is claimed for the final failure, and no further run was started after the budget was exhausted.

### Verified

Commands run on disposable hosted runners:

```text
python3 -m unittest discover -s os/tests -v
python3 -m py_compile os/ci/*.py os/ci/overlay/*.py os/tests/audit.py os/tests/power-events.py
bash -n <each script listed below>
```

The Bash syntax checks covered `os/ci/install-tools.sh`, `os/ci/parser-preflight.sh`, `os/ci/overlay/updater-generator`, `os/build.sh`, `os/tests/guest.sh`, `os/config/usr/bin/aresos-session` and `os/config/usr/bin/aresos-terminal`. Python compilation and Bash syntax checks passed without error output in all four runs. Every regression run printed **34 tests** and **OK**; the contingency messages in mocked reader tests are not guest power-key evidence.

- **Checks-only before attempt 1:** [39736375112](https://github.com/carlsenares/AresOS/actions/runs/39736375112), source `21d64fdc07db5c1b7b665652cd7203569fa5bee5`, **success**. Suite output: **`Ran 34 tests in 1.134s`, `OK`**. The actual Ubuntu system-manager query printed **`Live hosted system manager passed: 437 unit files, 608 unit names`**. The image job was skipped. This initial checks-only mode did not yet exercise Fedora. [Output and original logs](03g/checks-1/README.md).
- **Full attempt 1:** [39736454217](https://github.com/carlsenares/AresOS/actions/runs/39736454217), the same source, **failure**. Suite: **`Ran 34 tests in 0.767s`, `OK`**. Exact pinned-tool installation, upstream signature verification, locked RPM installation, protected kernel/driver comparison, release build and **817-unit** build audit passed. Release lint printed **`Checks passed: 10`, `Checks skipped: 1`, `Warnings: 4`**, retaining the inherited warnings. Build/audit took **12m18s**. Podman then returned **127**: **`crun: creating /opt/parser_preflight.py: openat2 opt: No such file or directory`** (the original output includes backtick quoting). The preflight did not start systemd or parse any Fedora output. Overlay build, release-isolation assertions, disk construction and both VMs were skipped. This is counted as a full attempt despite failing before boot. [Exact failure, metadata and original archives](03g/attempt-1/README.md).
- **Checks-only before attempt 2:** [39738388625](https://github.com/carlsenares/AresOS/actions/runs/39738388625), source **`06da4b82fe968fa8e87c27afbdcb2559808bbb09`**, **success**. Suite: **`Ran 34 tests in 1.044s`, `OK`**. The Ubuntu query inspected **437 unit files / 598 unit names**. `bash os/ci/parser-preflight.sh --base` successfully started the pinned Bazzite base's system and user managers, and the current audit parsed real **`systemd 259 (259.9-1.fc44)`** output. It printed **`Fedora parser preflight passed: system: 799 unit names; escaped name, alias, dependency and spaced drop-in preserved`**, then the same success for **user: 276 unit names**. [Exact transcript, parsed probes and version](03g/checks-2/README.md). This proves the parser and harness on the base, not the configured release or either VM.
- **Full attempt 2:** [39739567070](https://github.com/carlsenares/AresOS/actions/runs/39739567070), the same final code source **`06da4b82fe968fa8e87c27afbdcb2559808bbb09`**, **failure**. Suite: **`Ran 34 tests in 0.728s`, `OK`**. The same tool/signature/RPM/driver/build checks and **817-unit** audit passed; release lint again printed **10 passed / 1 skipped / 4 warnings**. Build/audit took **11m43s**. The corrected container mount and `basic.target` readiness check succeeded, but **`systemctl start dbus.service user@1000.service`** returned **1** with **`Job for user@1000.service failed because the control process exited with error code.`** The initial bus-not-ready diagnostic occurred during the bounded readiness loop; that loop subsequently passed. Python inventory was never invoked in the release container. Its retained Podman console is **zero bytes**; no `systemctl status` or journal for the failing unit was exported, so the underlying cause cannot be established from this run. Overlay/isolation/disk/VM stages were skipped. [Exact output, metadata and original archives](03g/attempt-2/README.md).
- Downloaded the artifacts with `gh run download <id> --name <artifact> --dir .work/03g/<run>` and saved original ZIPs with `gh api repos/carlsenares/AresOS/actions/artifacts/<id>/zip`; saved original workflow ZIPs with the corresponding `/actions/runs/<id>/logs` endpoints. Local PowerShell/.NET SHA-256 comparisons found **31**, **16**, and **31** matching entries for attempt 1, checks-only 2 and attempt 2 respectively. Each original ZIP's SHA-256 also matches GitHub's artifact metadata. [Comparison output](03g/archive-verification.txt). Local `git diff --check` and `git diff --cached --check` passed; PowerShell checked all **49** relative links in the current report section, OS README and new evidence indexes and printed `Relative document links passed: 49`. No screenshot exists for 03g because neither full run reached QEMU.

### Budget and measurements

**2/2 full attempts used; no third full run, rerun or local image/VM build.** Each full run was preceded by a successful checks-only run on exactly the same source commit. The two full workflows took **30m41s** total; checks-only workflows took **9m29s** total, including the base pull/tool setup. Combined elapsed time is **40m10s**, using GitHub's created/updated timestamps rather than billing data. [Run ledger](03g/ci-runs.json).

| Measurement | Full attempt 1 | Full attempt 2 |
|---|---:|---:|
| Workflow elapsed | 15m27s | 15m14s |
| Base uncompressed bytes | 13,010,242,255 | 13,010,242,255 |
| Release uncompressed bytes | 13,195,099,432 | 13,195,099,944 |
| Highest sampled runner use / total bytes | 62,813,421,568 / 76,887,154,688 | 62,813,495,296 / 76,887,154,688 |
| Lowest sampled free bytes | 14,056,955,904 | 14,056,882,176 |
| Compressed evidence artifact bytes | 183,368 | 183,398 |
| VM disk / VM passes | Not built / 0 | Not built / 0 |

Disk samples are ten seconds apart. The checks-only Fedora artifact is **98,178 bytes**, making all three artifacts **464,944 bytes** combined, each with three-day retention and now retained locally in the repo. The final failed release digest is **`sha256:7634af99e2035537b50b4b3dbe4aebb775aa261436ce1ece2e24f39b54eeabed`**; [provenance](../../os/manifest/ci/03g/provenance.json) binds it to `06da4b8`. Attempt 1's digest is **`sha256:3b176a818961f58d1e028520ee337688b5d6beb25ac8ef46e0c5b2b16dc12f2c`**. Neither digest qualifies VM acceptance. No image/disk/credential/builder configuration was uploaded, no image was published, and no paid runner or billing change was used.

### Not verified

**03g acceptance is NOT met. Neither fresh guest boot ran.** Actual live canary rejection, normal system/user updater policy, session/recovery, power/input handling, offline journal verification and logind proof remain unverified on the 03f code. The successful Fedora-base parser inventory does not establish that the configured release's user manager starts in a container or that it starts in a real guest. No hardware-gate contingency was reached and no inference about guest behavior follows from this container failure.

No code tests, Gradle tasks, containers or VMs ran on the owner's laptop, following brief 03's runner-only constraint. Local work was git/gh plus repository/evidence reads and writes and archive comparisons. `mod/` is unchanged and no Gradle daemon was started. Physical power/lid behavior, NVIDIA, interactive recovery login, installation/rebase/rollback and Windows return remain hardware/release gates.

### JUDGMENT-CALL

None affecting AresOS behavior or making a hard-to-reverse choice. Container probes and disposable account provisioning remain CI-only; no release account, service, power or updater policy was changed. Both pre-boot failures are conservatively counted against the full-run budget.

### PLAN-GAP

- The new Fedora preflight itself exposed two verification-harness gaps: an invalid mount target and a release-only user-manager startup failure. The base-mode checks-only success did not reproduce the configured release's environment. The second gap remains unresolved at the budget stop.
- Diagnostics are insufficient to identify why `user@1000.service` failed: `podman logs` retained no console output and the harness removed the container without exporting service status or journal records. A separately authorized follow-up should first retain those diagnostics and qualify the configured-release container path before spending another full run. Neither weakening the audit nor substituting the base preflight for two guest passes is justified.

### Open questions

A new brief/budget is required to diagnose the configured-release container's user-manager failure and obtain the still-missing green full run with both fresh VMs. No such authorization is assumed. Existing hardware, private-delivery and recovery-account prerequisites remain.

## 03f: review fixes

### Done

- `os/ci/offline_journal.py`: limit `REPORTED_NOT_BLOCKING_FIRST_HARDWARE_BOOT_GATE` to the conjunction of an explicitly unsupported kernel Btrfs mount and an explicitly absent userspace reader. Only a missing Podman executable or the container runtime's missing `/usr/bin/btrfs` or `/usr/bin/journalctl` entrypoint qualifies. Arbitrary command errors, timeouts, filesystem integrity/extraction failures, absent journals/boots, wrong boots, missing required records and cleanup failures block CI. Verify journals before listing/selecting the exact boot.
- `os/tests/test_offline_journal.py`: drive the real reader and classifier with command-level fixtures, including failures and timeouts throughout NBD, Btrfs and journal handling, mount/cleanup failures, both contingency prerequisites, verification ordering and incomplete/wrong boot evidence. Retain the earlier event/assertion tests.
- `os/tests/audit.py`, `os/tests/guest.sh`: require every suspicious unit to be masked or individually reviewed, regardless of unit-file state. A masked but running updater also fails. VM checks require live system and `ares` user managers, inspect effective commands and actual fragment/drop-in paths, and follow `Triggers`, `Wants`, `Requires`, `Requisite`, `BindsTo` and `Upholds` activation relationships. Generated/transient units and loaded instances are included; missing manager data fails the audit.
- `os/policy/`: mask additional inherited Homebrew, Flatpak, firmware, offline-update and staged-deployment entry points exposed by the stricter rule. Extend literal-name bookkeeping reviews without changing the suspicious-content pattern. The bootc RHSM facts unit only exports local facts; systemd cache/entropy/account/device units, local database indexes, print/NFS daemons, splash root notifications, local permission/key migrations and document/environment portals do not install software. Reasons are recorded beside each allowlist name.
- `os/tests/test_audit.py`, `os/ci/overlay/`, `os/ci/vm.py`: regressions cover every unit-file state, both live managers, activation dependencies, transient commands, aliases, dash-prefixed root units, quoted escaped names and quoted drop-in paths. `systemctl show` uses `--` before unit names; string vectors use `shlex.split`, while scalar `FragmentPath` remains one path. The VM-only layer adds a static updater behind an innocently named enabled timer and a unit generated during actual boot. Both have false conditions preventing updater execution. Each fresh VM must prove the live audit rejects both, record their activation/source evidence, then remove the fixtures before auditing normal policy. The host requires the new checksum-protected regression export; release-isolation assertions explicitly exclude these fixtures. **The actual VM rejection assertions remain unverified**, because both full attempts stopped in the live inventory before writing it.
- `os/ci/toolchain.json`, `install-tools.sh`, workflow: pin exact package versions and Ubuntu snapshot `20261021T000000Z`; disable mutable/third-party sources for this transaction, require snapshot candidates to match the committed versions, and reinstall Podman, Skopeo, QEMU and OVMF/SeaBIOS/iPXE. Retain the existing image, RPM, Actions and disk-builder pins. Export exact versions, signed-archive package metadata/SHA-256 values, executable/OVMF hashes, APT policy, host platform and full dpkg inventory. [Ubuntu documents the dated archive](https://snapshot.ubuntu.com/) as a reproducible package source.
- Workflow: add an explicit manual `checks_only=true` mode, labelled **OS regressions only (no VM)**. It runs unit/syntax checks and the real hosted system-manager inventory, with the entire image job skipped. Normal push/manual image runs retain both mandatory VM passes. `docs/INSTALL.md` and `os/README.md` describe the narrowed contingency and current verification limit.

### Verified

- **Full attempt 1:** [39724835851](https://github.com/carlsenares/AresOS/actions/runs/39724835851), source `65bda4dfe5442f177343d0d9149b13bf874403fe`, **failed**: `systemctl: invalid option -- '.'` because `-.mount` lacked an argument delimiter. `python3 -m unittest discover -s os/tests -v` printed **`Ran 31 tests in 0.753s`, `OK`**. Syntax checks, signature verification, the **817-unit** build audit, image/release isolation and disk construction passed. Commit `05f6531` fixes the cause with `--` and adds a dash-unit/alias regression. It also corrects the regression-export whitelist/required-file integration found by source review before that path was reached. [Original logs, artifact, error and metadata](03f/attempt-1/README.md).
- **Full attempt 2:** [39729374555](https://github.com/carlsenares/AresOS/actions/runs/39729374555), source `cba88bb58c6bee08613fdac2ae0e7197b610a2e3`, **failed**: a shell-quoted dependency name containing literal `\x2d` unit-name escapes was passed back to systemctl with its quotes still attached. The missing-unit assertion correctly blocked the audit. The suite printed **`Ran 32 tests in 0.773s`, `OK`**; exact pinned-package installation, syntax/signature checks, driver/package preservation, the **817-unit** build audit, both container lint invocations, release isolation and disk construction all passed. Both lint invocations printed **`Checks passed: 10`, `Checks skipped: 1`, `Warnings: 4`**, retaining the inherited warnings from 03c. Disk construction printed **`Build complete!`**. [Original error, logs and artifact](03f/attempt-2/README.md).
- **Final parser correction:** commit `f3aaff1` uses shell-word decoding for string-vector properties (`Names`, activation dependencies, `DropInPaths`), matching systemd v259.9's [bus-print-properties.c](https://github.com/systemd/systemd/blob/v259.9/src/shared/bus-print-properties.c) call to `shell_maybe_quote(str, 0)`. The first [checks-only run 39734679057](https://github.com/carlsenares/AresOS/actions/runs/39734679057) exposed an error in the new regression fixture: it inspected runuser's separator rather than systemctl's. Commit `83b7c9d` corrects the argument window while retaining the exact expected escaped unit name and both-scope assertions. No production assertion was weakened, removed or skipped.
- **Checks-only success:** [39734786025](https://github.com/carlsenares/AresOS/actions/runs/39734786025), source **`83b7c9dc3d188163b6912d0177d6986ffd53c17e`**, printed **`Ran 34 tests in 0.656s`, `OK`**. `python3 -m py_compile os/ci/*.py os/ci/overlay/*.py os/tests/audit.py os/tests/power-events.py` and `bash -n` for the tool installer, updater generator, image build, guest checks and two session scripts passed without errors. A direct `live_manager('system', ['systemctl', '--no-pager', '--no-legend'])` query of the real Ubuntu hosted manager printed **`Live hosted system manager passed: 437 unit files, 596 unit names`**, including the loaded `-.mount` assertion. The image job is **skipped** in both checks-only runs: neither builds an image/disk nor starts a VM. This green run does **not** satisfy the two-VM acceptance gate.
- Downloaded both full-run artifacts with `gh run download <id> --name os-image-evidence`; SHA-256 comparison printed **`Attempt 1 artifact: 39 entries match downloaded evidence`** and the same **39** for attempt 2. Preserve their original ZIPs and original GitHub workflow ZIPs. Raw attempt-2 build manifests, signature/package/driver evidence, exact tool/firmware package metadata/hashes, full host inventories and metrics are [indexed here](../../os/manifest/ci/03f/README.md). Both [attempt-1](screenshots/03f-attempt-1-failed-boot.png) and [attempt-2](screenshots/03f-attempt-2-failed-boot.png) failed-run framebuffers were visually inspected: they show the labwc AresOS terminal, not completed policy/recovery/power checks. Their pixels are identical (SHA-256 `5b521633614e3962d47323f7dc9db35d1313692a407a75bd7de9e8faf395093e`).
- Local evidence checks: `git diff --check` and `git diff --cached --check` passed without output after retaining the host module listing and APT package metadata solely in the original lossless archive (their trailing whitespace/blank lines remain intact). All relative links in the new evidence indexes resolve. No production code changed after the green checks-only source `83b7c9d`.

**Budget: 2/2 full runs used.** No manual full rerun, third full build, local build/VM, registry publication, paid runner or billing change. Two additional checks-only runs took **13s** (fixture failure) and **12s** (success), with the image job skipped. [Run ledger](03f/ci-runs.json) uses GitHub created/updated timestamps, not a billing claim.

| Measurement | Full attempt 1 | Full attempt 2 |
|---|---:|---:|
| Workflow elapsed | 45m44s | 46m12s |
| Base uncompressed bytes | 13,010,242,255 | 13,010,242,255 |
| Release uncompressed bytes | 13,195,089,192 | 13,195,091,752 |
| VM raw disk virtual bytes | 31,666,995,200 | 31,666,995,200 |
| VM raw disk allocated bytes | 9,547,382,784 | 9,568,727,040 |
| Highest sampled runner use / total bytes | 70,839,672,832 / 76,887,154,688 | 70,443,487,232 / 76,887,154,688 |
| Lowest sampled free bytes | 6,030,704,640 | 6,426,890,240 |
| Compressed evidence artifact bytes | 244,561 | 243,471 |

Full-run elapsed total is **91m56s**; including the two checks-only workflows, **92m21s**. Disk sampling is every ten seconds. Artifact expiry is **2026-10-25 05:38:32 UTC** / **06:26:43 UTC**, with original copies now retained in the repo. No image, disk, password, credential file, binary journal or builder configuration is included. Attempt-2 release OCI digest is **`sha256:3bdf3239f51f7fd81aaee5788110a7817defe86d29b002a287142190c315af16`**; VM test-image digest is **`sha256:23362da1795197ea2d365d71ba91cf5f0842c75f65ad05f2931d05c4a0fc3f4b`**. These identify the failed `cba88bb` build, not a build of the final parser correction.

Exact committed package pins from signed snapshot `20261021T000000Z`:

| Tool | Ubuntu package version |
|---|---|
| Podman | `4.9.3+ds1-1ubuntu0.2` |
| Skopeo | `1.13.3+ds1-2ubuntu0.24.04.3` |
| QEMU system/data/common/utils/block-extra | `1:8.2.2+ds-0ubuntu1.18` |
| OVMF | `2024.02-2ubuntu0.10` |
| SeaBIOS | `1.16.3-2` |
| iPXE | `1.21.1+git-20220113.fbbdc3926-0ubuntu2` |
| Pillow | `10.2.0-1ubuntu1.3` |

### Not verified

**The required green image workflow with both VM passes was not achieved.** Both full attempts booted the session and passed the canaries' setup/state checks, then failed before the live inventory completed. The actual VM canary rejections, normal guest updater/user-manager policy, recovery, power/input events, offline extraction/verification/poweroff assertions and pass 2 were not reached. No offline hardware-gate result or logind proof is claimed for 03f. The historical 03e green run does not validate this changed code. The final parser correction is unit-tested and checked against a real hosted system manager, but has not been rebuilt/booted in the guest. A newly authorized full-run budget is needed for that acceptance gate.

No local builds, tests, containers, VMs, installs or Gradle tasks ran: brief 03's runner-only constraint applies to this OS-only follow-up. `mod/` is unchanged; no Gradle daemon was started. Hardware/NVIDIA behavior, interactive recovery login, physical lid/power behavior, installation/rebase/rollback and Windows return remain first-hardware/release gates.

### JUDGMENT-CALL

- **Mask dormant update entry points too.** Includes staged-deployment finalizers, firmware update and optional database/printer migration services. Leaving an unreviewed static/disabled unit available would violate 03f and permit activation without enablement. Masks are reversible policy symlinks; the future manual maintenance/deployment package must explicitly qualify and restore the finalizers it needs. No deployment/installer path is promised by this prototype.
- **Use the signed dated Ubuntu archive for runner tools.** This preserves the existing rootful Podman/QEMU architecture. A new nested builder environment would change storage/device isolation and add a separate integration risk. Updating the snapshot is an explicit source change followed by full VM qualification.

### PLAN-GAP

- A standard `ubuntu-24.04` hosted runner does not expose immutable image selection or our own kernel boot ([runner-images maintainers](https://github.com/actions/runner-images/discussions/8674)). GitHub's runner image, kernel/KVM/NBD and bootstrap/shared host libraries remain host inputs; exact exceptions and reasons are in `os/ci/toolchain.json`. Record `ImageOS`/`ImageVersion`, `uname`, module metadata and the installed dpkg inventory rather than claiming a hermetic hosted machine. The four requested toolchains and firmware packages come from the dated archive.
- **Verification gap in this implementation:** initial mocks missed real systemctl option parsing and shell-quoted string vectors. Added the checks-only actual-host-manager preflight for use before spending another full image run; its current green result covers the system manager on Ubuntu, not Fedora guest/user-manager qualification. The two full-run failures are implementation errors, not a reason to weaken the brief's assertions or exceed its budget.

### Open questions

- A follow-up brief/budget must authorize the full image run needed to validate the final correction in **both fresh VMs**. Stop at the current 2/2 full-run limit; no third run was started.
- Existing hardware, private image-delivery and recovery-account prerequisites remain as documented below.

## 03e: final offline power-key run

### Done

- Exercised the already-committed Podman `:r` device correction, read-only Btrfs extraction and runner `dmesg` capture against two fresh guest disks. Both journals were read and passed the unchanged marker → trusted logind short-power-key record → logind poweroff → successful logind stop assertion.
- `os/ci/offline_journal.py`, `os/ci/vm.py`: implement brief 03e's pre-authorized contingency before starting its only run. Explicit reader unavailability reports `REPORTED_NOT_BLOCKING_FIRST_HARDWARE_BOOT_GATE` in workflow output, step summary and per-pass JSON. A readable boot's missing records, wrong boot, journal verification failure, disk-isolation failure and unexpected/cleanup errors remain blocking. QEMU exit, QMP and console shutdown assertions now run before the offline reader; both fresh passes remain mandatory. Successful evidence records distinguish a proven logind path from the contingency. **Both actual VM results are `passed`; no assertion was downgraded in this run.**
- `os/tests/test_offline_journal.py`: retain all earlier tests and add a regression covering the contingency and propagation of assertion/unexpected/cleanup failures. `docs/INSTALL.md` §7 contains the 03c first-hardware-boot procedure, including interactive recovery login, physical short power press, previous logind/full-boot journals and a repeated session/recovery trial. `os/README.md` explains the conditional rule and final result. No production power setting, base, package or driver pin changed.
- Retain [raw manifests and per-pass results](../../os/manifest/ci/03e/README.md), [run](03e/run.json), [job](03e/jobs.json) and [artifact](03e/artifacts.json) metadata, selected output, lossless full workflow/journal/console archives and screenshots. Update PR #3's description and mark it ready for review; do not merge.

### Verified

- **Exactly 1/1 full run:** [39718803979](https://github.com/carlsenares/AresOS/actions/runs/39718803979), workflow attempt **1**, checkout **`dc6fcfcf7b5ae4683369ae7c5c938203ee877498`**, **success**. The branch push started this run; no manual dispatch, rerun or additional full run was used. [Run ledger](03e/ci-runs.json) records **45m32s** workflow elapsed (not a billing claim). Release build/audit: **12m13s**; isolated overlay/isolation: **11m05s**; disk construction: **15m41s**; both VM passes together: **3m57s**.
- On the disposable runner, `python3 -m unittest discover -s os/tests -v` printed **`Ran 23 tests in 0.403s`, `OK`**. `python3 -m py_compile os/ci/*.py os/ci/overlay/*.py os/tests/power-events.py` and `bash -n` on `os/build.sh`, `os/tests/guest.sh`, `os/config/usr/bin/aresos-session` and `os/config/usr/bin/aresos-terminal` passed without error output. Upstream `cosign verify`, locked-RPM/signature installation and the protected kernel/driver comparison passed. Both container lint invocations printed **`Checks passed: 10`, `Checks skipped: 1`, `Warnings: 4`**, retaining the inherited warnings documented in 03c. The build audit inspected **815 units**. Release isolation printed **`Release excludes CI service and credentials; both passwords locked`**, also checking persistence and absence of CI debug overrides. Disk builder printed **`Build complete!`**. [Selected exact output](03e/verification-output.txt); [complete output ZIP](03e/workflow-output.zip).
- The workflow ran `sudo -E env ARESOS_VM_PASS="$pass" python3 os/ci/vm.py` for **1 and 2**, creating separate QEMU processes, fresh qcow2 overlays and reset OVMF variables. Both used **`-accel kvm -cpu host`**, printed `ARESOS_GUEST_CHECKS_PASSED`, passed the **828-unit** runtime audit, exported raw bootc/updater/input evidence and printed `ARESOS_POWER_EVENTS_PASSED`. Both recovery results show wrong-password PAM **7**, correct authentication/account **0/0**, root/UID **0**, one password prompt per attempt and active tty3 `agetty`. The shortcut opened a second foot process. Each follower was ready before its ACPI press.
- Both read-only NBD attachments and read-only block-device checks passed. Both kernel mounts returned **32**; captured `dmesg` explicitly says **`btrfs: Unknown parameter 'nologreplay'`**. This resolves the previously generic mount error. With `--device /dev/nbd0p4:/dev/guest:r`, the release image's `btrfs check --readonly` returned **0**, printing **`no error found`**. Root-256 journal-only extraction returned **0** without backup-superblock fallback or ignored errors. The image's `journalctl --directory` read the exact stopped boot, exported complete boot text/JSON and logind JSON, and `--verify` returned **0** with **PASS** for both journal files in each pass. Verification writes its PASS messages to stderr: they are retained in `offline-commands.json`; the empty `offline-verify.txt` is stdout, not missing evidence. NBD disconnect returned **0** twice.

The [pass 1](../../os/manifest/ci/03e/vm-pass-1/offline-poweroff.json) and [pass 2](../../os/manifest/ci/03e/vm-pass-2/offline-poweroff.json) structured records have these monotonic timestamps, in seconds after their own boot:

| Pass / exact boot ID | Armed marker | Logind short key | Logind poweroff | PID 1 logind stop |
|---|---:|---:|---:|---:|
| 1 / `67693587f4874d7b8d561ab768b73313` | 98.564327 | 99.160112 | 99.170288 | 100.271624 |
| 2 / `4606ca97045944f79dfe9cb4470b1f3c` | 98.871931 | 99.145414 | 99.335330 | 100.590290 |

In each boot, the key record has `_SYSTEMD_UNIT=systemd-logind.service`, `MESSAGE_ID=b72ea4a2881545a0b50e200e55b9b071` and `MESSAGE=Power key pressed short.`; the following logind record has `MESSAGE_ID=98268866d1d54a499c4e98921d93bc40` and `SHUTDOWN=power-off`. PID 1 then records `JOB_TYPE=stop`, `JOB_RESULT=done` for logind. Both [poweroff results](../../os/manifest/ci/03e/vm-pass-1/poweroff.json) and their pass-2 counterpart require QEMU exit **0**, exactly one `SHUTDOWN guest=true, reason=guest-shutdown`, no reset/suspend/panic during shutdown and console `poweroff.target`. The lossless [pass 1](03e/vm-pass-1-journal-console.zip) and [pass 2](03e/vm-pass-2-journal-console.zip) archives retain the complete offline exports and console, including final clean teardown. Both invocations printed **`UEFI VM checks passed`**.

- Downloaded with `gh run download 39718803979 --name os-image-evidence` and visually inspected both [pass-1 labwc](screenshots/03e-vm-pass-1-aresos-labwc.png) / [tty3](screenshots/03e-vm-pass-1-aresos-tty3-getty.png) and [pass-2 labwc](screenshots/03e-vm-pass-2-aresos-labwc.png) / [tty3](screenshots/03e-vm-pass-2-aresos-tty3-getty.png). The screenshots show the AresOS terminal and separate getty; PAM results establish authentication separately. All seven entries of each journal/console archive were hash-compared to the original artifact. Console/dmesg whitespace is retained inside those archives; local `git diff --check` and `git diff --cached --check` pass with that evidence layout. Per brief 03's runner-only constraint, no local tests, image/container/VM or mod Gradle task ran. `mod/` is unchanged and no Gradle daemon was started.

### Run budget and measurements

**1/1 full 03e run used; no further run started.** The artifact is **2,698,262 bytes**, retained for three days (expiry **2026-10-25 04:33:13 UTC**). Only evidence was uploaded: no image, disk, password, credential file or builder configuration. No image publication, paid runner or billing change.

| Measured item | Bytes |
|---|---:|
| Base / release uncompressed image | 13,010,242,255 / 13,194,827,559 |
| VM raw disk virtual / allocated | 31,666,995,200 / 9,503,416,320 |
| Runner total / highest sampled used / lowest sampled free | 76,887,154,688 / 70,197,202,944 / 6,673,174,528 |

Samples are ten seconds apart and include both retained disposable overlays. Release OCI digest: **`sha256:4aa78987014bdbbff13c32fcb34bde46a67e85d0e95a822c0781784f8291c703`**. Separate VM image: **`sha256:7f1670edc69f51f69f341113769f4d91979d751f87f34829d09b8ec8d9fdbbdd`**, matching both raw bootc status exports. [Provenance](../../os/manifest/ci/03e/provenance.json), both OCI manifests, signature evidence and [metrics](../../os/manifest/ci/03e/metrics.json) retain the identities and measurements. Preserved kernel **6.18.56-ogc1.1.fc44** and NVIDIA **580.178.04** are package evidence, not hardware qualification.

### Not verified

No physical power/lid behavior, NVIDIA operation, interactive recovery shell, installation, Windows return, rebase or rollback was tested. Existing installation/recovery-account and hardware prerequisites remain. The real-VM reader-unavailable branch was **not** needed: its error handling was regression-tested, while both actual journals passed the full blocking assertion. No hardware-only downgrade is claimed. This prototype is not an installation release.

### JUDGMENT-CALL

No new production or hard-to-undo decision. Brief 03e already authorizes the single conditional hardware gate; it was implemented narrowly before the run so every other assertion and both passes could stay blocking within the one-run budget. Readable-journal assertion failures are never converted into a reported check. That contingency was not exercised by either real guest. The hardware procedure is retained for physical qualification.

### PLAN-GAP

The runner's kernel rejects `nologreplay`; its captured diagnostic now identifies the mount failure instead of leaving it unexplained. The existing read-only userspace extraction successfully resolves it, so no further mount-option change or run is needed for this brief. The formerly missing logind evidence is now present in both complete offline boots; no remaining 03e acceptance gap was found.

### Open questions

None for 03e CI acceptance. Existing image-delivery, qualified NVIDIA base, installer/recovery-account provisioning and hardware-release gates remain for their own packages. PR #3 is ready for review and remains unmerged.

## 03d: offline power-key journal

### Done

- `os/config/etc/systemd/journald.conf.d/90-aresos.conf`: explicitly retain `Storage=persistent`. The live configuration also revealed that the pinned base already supplies this setting through `10-persistent.conf`; this makes the existing policy explicit rather than changing its effective value. Only the CI overlay adds `SYSTEMD_LOG_LEVEL=debug` for logind and `MaxLevelStore=debug` for journald. Release isolation checks exclude both debug overrides and still require locked image passwords and no CI service/source.
- `os/ci/vm.py`, `os/ci/overlay/checks.py`: replace QEMU's deleted-on-exit snapshot with a retained, fresh qcow2 overlay per pass. Before the ACPI press, record the exact guest boot ID and an armed marker, flush/sync the journal and require on-disk journal files. Preserve follower readiness, the existing policy/input/recovery/raw-export checks, QMP/console shutdown assertions, reset firmware and the second fresh VM pass.
- `os/ci/offline_journal.py`: after QEMU exits, attach only that pass's file overlay using read-only NBD; require the partition to report read-only and attempt `ro,nologreplay,subvolid=5`. Export the complete previous guest boot, logind records, file hashes, reader commands and journal verification before asserting the ordered marker → trusted logind short-power-key message ID → logind `SHUTDOWN=power-off` → PID 1 successful logind stop. Final console `poweroff.target` and guest-initiated QMP shutdown remain mandatory.
- The follow-up adds mount diagnostics and a userspace fallback using the release image's Btrfs tools: require `btrfs check --readonly`, extract only journal paths from the primary root subvolume, reject backup-superblock fallback and ignored errors, and read the copied journals with the guest's systemd version. **This fallback has not been exercised.** The final one-character correction, commit `1501d7d`, changes Podman's device permission from invalid `:ro` to `:r`; it is also unverified in CI. Its `[skip ci]` marker was intended to prevent another build, but the combined push's documentation tip still launched a workflow; that launch was force-cancelled before any build, as recorded below. No green result is claimed.
- `os/tests/test_offline_journal.py`: four regressions cover exact boot identity, required ordered records, old/spoofed/wrong-service events, failed teardown and the narrowly bounded extraction filter. The 18 existing regressions are retained. `os/README.md` records the actual failure and budget stop.

### Verified

- [Full attempt 1: 39713129693](https://github.com/carlsenares/AresOS/actions/runs/39713129693), source **`cb07f69dc04d779ea908b2a80c00c243ffdfd7fc`**, **failed**. `python3 -m unittest discover -s os/tests -v` printed **`Ran 21 tests in 0.365s`, `OK`**. `python3 -m py_compile os/ci/*.py os/ci/overlay/*.py os/tests/power-events.py` and `bash -n` on `os/build.sh`, `os/tests/guest.sh`, `os/config/usr/bin/aresos-session` and `os/config/usr/bin/aresos-terminal` passed without error output. Upstream signature, locked RPM/driver checks, release/overlay builds and container lint passed. Both lint invocations printed `Checks passed: 10`, `Checks skipped: 1`, `Warnings: 4` (the same inherited warnings documented in 03c). Build audit: **815 units**. Release isolation printed `Release excludes CI service and credentials; both passwords locked`, after also checking persistent storage and absence of debug overrides. Build/audit took **12m03s**, overlay/isolation **10m11s**, disk construction **17m09s**, ending in `Build complete!`.
- Its first KVM/UEFI guest printed `ARESOS_GUEST_CHECKS_PASSED`, passed the **828-unit** runtime audit and `ARESOS_POWER_EVENTS_PASSED`, exported raw [bootc status](../../os/manifest/ci/03d/attempt1/vm-pass-1/backend.json), [updater inventory](../../os/manifest/ci/03d/attempt1/vm-pass-1/runtime-updaters.json) and [power-event evidence](../../os/manifest/ci/03d/attempt1/vm-pass-1/power-events.json), and opened the recovery terminal. [PAM/getty evidence](../../os/manifest/ci/03d/attempt1/vm-pass-1/recovery-result.json) records wrong-password result **7**, correct-password authentication/account results **0/0**, root/UID 0, one password prompt per attempt, and active tty3 `agetty`.
- [Preparation evidence](../../os/manifest/ci/03d/attempt1/vm-pass-1/prepare-poweroff-result.json) records boot **`f2e0d7782f7342809f243ad5d7c42f41`**, successful journal flush/sync, effective persistence/debug configuration and `system.journal` plus `user-1000.journal` under machine ID `295dc10ce4424b6293f0537e1567fae9`. The host observed follower readiness before pressing the button. [QMP](../../os/manifest/ci/03d/attempt1/vm-pass-1/qmp-events.json) captured `POWERDOWN` then `SHUTDOWN guest=true, reason=guest-shutdown`. The [lossless console archive](03d/attempt1-vm-pass-1-journal-console.zip) shows `shutdown.target`, `poweroff.target`, successful logind stop, all filesystems unmounted and `reboot: Power down`. These observations do **not** prove the missing offline logind event. Because the reader failed first, the final host QEMU-exit/QMP assertions were not reached and no successful `poweroff.json` was written.
- **Exact offline result: no journal records were read.** [Reader commands](../../os/manifest/ci/03d/attempt1/vm-pass-1/offline-commands.json) show NBD attach, partition discovery and read-only verification succeeded. [Partition layout](../../os/manifest/ci/03d/attempt1/vm-pass-1/offline-disk-layout.json) identifies `/dev/nbd0p4` as Btrfs with `ro=true`. `mount -t btrfs -o ro,nologreplay,subvolid=5 /dev/nbd0p4 .../vm-work/offline-root` returned **32**: `wrong fs type, bad option, bad superblock ... missing codepage or helper program, or other error`. NBD disconnect succeeded. The kernel-specific cause is unknown: attempt 1 did not capture runner `dmesg`. There is no offline boot/logind export or journal verification result to interpret as either receipt or non-receipt of the key. The second VM pass did not start.
- [Full attempt 2: 39717408911](https://github.com/carlsenares/AresOS/actions/runs/39717408911), source **`a798f574bb36a9be41d17bef640ec1bb109ab353`**, **cancelled**. Its tests printed **`Ran 22 tests in 0.357s`, `OK`**; the same Python compile/Bash checks and upstream signature verification passed. I noticed the incorrect Podman device permission during setup and requested cancellation. Normal cancellation did not stop the job before image building; force cancellation ended that stage after **25 seconds**. It is therefore counted as full attempt 2. No completed release/overlay/disk, VM, offline journal or second pass exists for this attempt. The later `:r` correction is not covered by these tests.
- Downloaded both small artifacts with `gh run download`. Visually inspected and retained the first attempt's [labwc session](screenshots/03d-attempt1-vm-pass-1-aresos-labwc.png) and [tty3 getty](screenshots/03d-attempt1-vm-pass-1-aresos-tty3-getty.png); these show the terminal and independent login screen, not an interactive authenticated shell. [Selected command output](03d/attempt1-verification-output.txt), [attempt 2 output](03d/attempt2-verification-output.txt), run/job/artifact metadata and [raw manifests](../../os/manifest/ci/03d/README.md) are retained. Local `git diff --check` passed. No code tests, containers, VM or Gradle tasks ran on the owner's laptop, following brief 03's runner-only constraint. `mod/` is unchanged; no Gradle daemon was started.

### Run budget and measurements

| Full attempt | Result | Workflow elapsed |
|---|---|---:|
| [39713129693](https://github.com/carlsenares/AresOS/actions/runs/39713129693) | Guest checks and clean shutdown observed; offline Btrfs mount failed before journal export | 43m03s |
| [39717408911](https://github.com/carlsenares/AresOS/actions/runs/39717408911) | Cancelled after image building began; counted conservatively | 3m03s |

**2/2 full attempts used; no third full build.** The two counted attempts' workflow elapsed totals **46m06s**, including setup/upload time, not a billing claim. The final combined code/evidence push also automatically launched [39718242619](https://github.com/carlsenares/AresOS/actions/runs/39718242619), despite the earlier correction commit's skip marker. The final check caught it and force-cancelled it during runner cleanup; [job metadata](03d/prebuild-cancelled-jobs.json) proves tool installation, signature verification, image/overlay/disk builds and VM testing were all skipped. It produced no evidence artifact and is not a full build attempt. [Run ledger](03d/ci-runs.json) retains all three workflow identities and their individual elapsed times. Combined artifact size is **395,643 bytes** (304,790 + 90,853), with three-day retention. No image, disk, credential or builder configuration was uploaded, no image was published and no paid runner/billing change was used.

| Attempt 1 measured item | Bytes |
|---|---:|
| Base / release uncompressed image | 13,010,242,255 / 13,194,820,392 |
| VM raw disk virtual / allocated | 31,666,995,200 / 9,494,355,968 |
| Runner total / highest sampled used / lowest sampled free | 76,887,154,688 / 70,061,346,816 / 6,809,030,656 |

Samples are ten seconds apart and include the retained disposable overlay. Attempt 2 did not complete an image or disk. Attempt 1's release digest is **`sha256:ad402904a8133f0f41b872ca57c4799e096888c912ab7b5420337ebe27159ed6`**; the separate VM image is **`sha256:c7e358588da54c78bc16683da569dabcd78ef31abe8d72a7f0ba928ed1aad6a4`**, matching its raw bootc status. [Provenance](../../os/manifest/ci/03d/attempt1/provenance.json), both OCI manifests and metrics retain these identities.

### Not verified

**No green 03d run, offline logind receipt/shutdown proof, exercised extraction fallback or successful second VM pass exists.** This is a reader failure, not evidence that logind did or did not handle the ACPI key. The offline assertion remains in place and the PR remains draft. No further full run is authorized by this brief. Physical power/lid behavior, NVIDIA, interactive recovery login, installation and hardware qualification remain untested. This report does not independently convert the failed VM assertion into a hardware-only gate.

### JUDGMENT-CALL

- Pin the already-effective persistent-journal setting in AresOS rather than rely on the base's drop-in. This changes no observed effective value, keeps upstream retention defaults, and can be undone by removing one configuration file. Rejected raising production logind verbosity; debug settings remain CI-only.
- Use a read-only userspace extraction fallback after the runner rejected a read-only kernel mount. Rejected a writable mount or filesystem repair. The fallback adds no release packages and changes no power behavior, but remains unverified. [Btrfs restore](https://btrfs.readthedocs.io/en/latest/btrfs-restore.html) documents that the input filesystem is not modified; journal integrity, exact boot identity and the post-marker sequence still have to pass. Any later layout change must explicitly revisit root subvolume 256.

### PLAN-GAP

The runner could build and boot the Btrfs disk but could not mount its stopped clone read-only; the available generic error does not establish why. This consumed the first full attempt without reaching the requested evidence. I then caught a Podman argument error after starting the fallback run, and cancellation reached it only after image building began. Counting that as attempt 2 leaves the reader correction unverified. No assertion was relaxed and no third run was used to hide this failure. Podman's [device-permission syntax](https://docs.podman.io/en/v4.4/markdown/podman-run.1.html) requires `r`, while `ro` applies to volume mounts.

### Open questions

Claude must decide whether to authorize a separately budgeted reader verification or make the unresolved path a documented first-hardware-boot check, as brief 03d reserves. No such decision is assumed here. The precise unresolved issue is obtaining any offline journal records; there is not yet a journal-based negative finding about logind itself.

## 03c: robust VM channels for recovery and power

### Done

- `os/ci/channel.py`, `os/ci/overlay/`, `os/ci/vm.py`: replace interactive serial commands and keyboard password entry with a fixed-check service on a dedicated virtio-serial port. Bounded JSON frames carry request IDs, check exit status and output. Raw JSON exports are base64-encoded and verified against a SHA-256 of the original guest bytes. The ordinary serial console is a passive log; kernel messages and terminal queries cannot corrupt the check channel.
- Recovery uses the guest's **unchanged `login` PAM stack**, with `/dev/tty3` as `PAM_TTY`. A wrong password must produce `PAM_AUTH_ERR` (7), the provisioned password must authenticate and pass account validation (0), and each attempt must actually request the password through the PAM conversation callback. The accepted PAM username must resolve to root/UID 0. Independently require a running `agetty` whose stdin is `/dev/tty3`, plus the Ctrl+Alt+F3 VT switch. This tests password authentication and the getty independently; it does not claim an interactively authenticated VT shell.
- `os/ci/qmp.py`: continuously retain asynchronous QMP events, including events after a command reply. `system_powerdown` must produce exactly one `SHUTDOWN` with `guest=true, reason=guest-shutdown`, no reset/suspend/panic event during shutdown, QEMU exit 0, a logind power-key record, and console evidence of `poweroff.target`. A separate CI-only transient journal unit starts from a saved cursor and is configured without ordinary shutdown dependencies; the host must observe its journal readiness record before pressing the button.
- `.github/workflows/os-image.yml`, `os/.containerignore`, `os/Containerfile`: build the release tag independently from `localhost/aresos:vm`, and retain both OCI manifests/digests. Exclude `ci/` from every release build layer and assert that exclusion before package building. Check the final release filesystem for absence of the test service, scripts and temporary source, and require both release account passwords to remain locked. Only the VM disk receives its random recovery credential. No password, image or VM disk is committed/uploaded.
- Keep `os/tests/guest.sh` and `os/tests/power-events.py` unchanged: session, updater masks/audit, no wheel or sudo for `ares`, no inherited display manager, live logind settings, masked/unentered sleep units, observed lid/sleep-key events, and rejected direct sleep requests. Preserve all 13 earlier regressions and add five framing/export/QMP regressions. Every complete workflow still requires two fresh QEMU processes, reset firmware variables and disposable disk overlays. `os/README.md` documents the new channels and evidence limits.

### Verified

- **Latest/final run:** [39707546339](https://github.com/carlsenares/AresOS/actions/runs/39707546339), exact code `70b632f2a74b085ff9c1af3566d121d2b53d61f1`, failed. `python3 -m unittest discover -s os/tests -v` printed **`Ran 18 tests in 0.392s`, `OK`**; the same Python compile and four Bash syntax checks below passed. Signature, pinned RPM/driver checks, both image builds and container lint passed. The release isolation check ran with `bash -ec` and printed `Release excludes CI service and credentials; both passwords locked`. Build/audit took **11m56s**, the separate overlay **11m13s**, and disk construction **15m47s** (`Build complete!`).
- In its KVM/UEFI guest, all checks through recovery passed again: `ARESOS_GUEST_CHECKS_PASSED`, the **828-unit** runtime audit, `ARESOS_POWER_EVENTS_PASSED`, two foot PIDs, active tty3 `agetty`, wrong-password PAM result **7**, and correct-password authentication/account results **0/0** for root/UID 0. The raw [bootc status](../../os/manifest/ci/03c/attempt3/vm-pass-1/backend.json), [runtime inventory](../../os/manifest/ci/03c/attempt3/vm-pass-1/runtime-updaters.json), [power events](../../os/manifest/ci/03c/attempt3/vm-pass-1/power-events.json) and [recovery response](../../os/manifest/ci/03c/attempt3/vm-pass-1/recovery-result.json) are exported without reconstruction. The new cursor-based journal unit started successfully and **`ARESOS_JOURNAL_READY` was observed before the ACPI button press**.
- The final [QMP capture](../../os/manifest/ci/03c/attempt3/vm-pass-1/qmp-events.json) records `POWERDOWN`, followed by `SHUTDOWN` with `guest=true, reason=guest-shutdown`. The host's QEMU exit-0 and QMP assertions passed before the logind-record assertion failed. The lossless [serial ZIP](03c/attempt3-serial.zip) contains `Reached target poweroff.target - System Power Off`, clean filesystem teardown and `reboot: Power down`, but **no `Power key pressed short.` record**. The assertion remains enforced. No successful `poweroff.json`/`poweroff.txt` or second VM pass is claimed.
- Downloaded and visually inspected the latest [labwc screenshot](screenshots/03c-attempt3-labwc.png) and [tty3 getty screenshot](screenshots/03c-attempt3-tty3-getty.png). [Selected verification output](03c/attempt3-verification-output.txt), [job metadata](03c/attempt3-jobs.json) and [all generated manifests/metrics](../../os/manifest/ci/03c/attempt3/) retain the final failure and preceding passes. Later changes contain only documentation and evidence; no untested code change is hidden behind a skipped workflow. Local `git diff --check` passed for the implementation and final evidence/documentation edits.

- [Attempt 2: 39703243372](https://github.com/carlsenares/AresOS/actions/runs/39703243372), checkout `05e8f7e79f4766f05b356cafd9bb9b6016809007`, is a **failed** workflow. `python3 -m unittest discover -s os/tests -v` printed **`Ran 18 tests in 0.404s`, `OK`**. `python3 -m py_compile os/ci/*.py os/ci/overlay/*.py os/tests/power-events.py` and the four existing `bash -n` checks passed without error output. Signature verification, locked RPM installation, driver-package comparison, release/overlay builds and disk construction passed; the builder printed `Build complete!`.
- In its first KVM/UEFI boot, `ARESOS_GUEST_CHECKS_PASSED` and `Updater audit passed: 828 system/user units inspected` were printed. Both [raw bootc status](../../os/manifest/ci/03c/attempt2/vm-pass-1/backend.json) and [runtime updater inventory](../../os/manifest/ci/03c/attempt2/vm-pass-1/runtime-updaters.json) were exported automatically, without recovery or reformatting. `bootc` identifies the separate test image, whose digest agrees with [vm-image-digest.txt](../../os/manifest/ci/03c/attempt2/vm-image-digest.txt); the release digest is recorded separately.
- [Power-event evidence](../../os/manifest/ci/03c/attempt2/vm-pass-1/power-events.json) records observed/ignored lid close/open and suspend/hibernate keys, unchanged labwc/foot PIDs, all nine sleep targets/services inactive with zero activation timestamps, and all four direct sleep requests rejected as disabled by configuration. The recovery shortcut opened a second foot process. [Recovery evidence](../../os/manifest/ci/03c/attempt2/vm-pass-1/recovery-result.json) records wrong-password rejection (7), correct-password authentication/account validation (0/0), one password prompt each, root/UID 0, and an active tty3 getty.
- Its final assertion failed because the captured output did not contain the required logind power-key record. The lossless [serial capture](03c/attempt2-serial.zip) nevertheless contains `Reached target poweroff.target - System Power Off`, filesystem teardown and `reboot: Power down`; [QMP events](../../os/manifest/ci/03c/attempt2/vm-pass-1/qmp-events.json) contain the real guest-initiated shutdown. This is diagnostic evidence, **not a passing full run**. The second VM pass did not start. The final code keeps the failed assertion and adds explicit follower readiness/lifetime controls.
- Downloaded and visually inspected the [labwc screenshot](screenshots/03c-attempt2-labwc.png) and [tty3 getty screenshot](screenshots/03c-attempt2-tty3-getty.png). The former shows the AresOS terminal; the latter shows the independent login screen, not an authenticated shell.
- The release and overlay `bootc container lint` commands each printed `Checks passed: 10`, `Checks skipped: 1`, `Warnings: 4`. These are the existing linter's reported counts, not removed/disabled AresOS assertions. Warnings concern inherited runtime/temp files, account/sysusers entries, logs and non-directory `/var` files. The build updater audit inspected 815 units successfully.

### Run budget

| Run | Result | Workflow elapsed |
|---|---|---:|
| [39702883283](https://github.com/carlsenares/AresOS/actions/runs/39702883283) | Cancelled to exclude CI source from release layers. Cancellation completed after image building had started, so conservatively counted as full attempt 1. Its 18 regressions passed. | 4m12s |
| [39703201938](https://github.com/carlsenares/AresOS/actions/runs/39703201938) | Cancelled while pending to restore existing context exclusions; no job was created. Not a full build. | 21s |
| [39703243372](https://github.com/carlsenares/AresOS/actions/runs/39703243372) | Full attempt 2: image/disk, policy, raw exports, power events, shortcut, getty and PAM passed; failed the power-key journal assertion after real clean guest poweroff. | 40m26s |
| [39707546339](https://github.com/carlsenares/AresOS/actions/runs/39707546339) | Full attempt 3: the same preceding checks passed, including the new journal readiness proof. The same logind-record assertion failed after guest-initiated clean poweroff. No second VM pass. | 44m07s |

All **3/3** full attempts are counted, including the build cancellation; the pending cancellation created zero jobs. No fourth full run was started. Observed workflow elapsed totals **89m06s** for 03c, or **346m04s** including the previously reported 256m58s. These totals include queue/setup/upload time and are not billing claims. [Run ledger](03c/ci-runs.json) and per-run job/artifact metadata retain the source and timings. No paid runner, billing change or registry upload was used.

| Final measured item | Observed value |
|---|---:|
| Base / release image uncompressed bytes | 13,010,242,255 / 13,194,818,343 |
| VM raw disk virtual / allocated bytes | 31,666,995,200 / 9,424,707,584 |
| Runner total / highest sampled used / lowest sampled free bytes | 76,887,154,688 / 69,970,849,792 / 6,899,527,680 |
| Final artifact compressed / all 03c artifacts bytes | 270,892 / 631,638 |

Across 03c runs the highest sampled used space was 70,131,851,264 bytes, leaving 6,738,526,208 bytes free. Sampling is every ten seconds and includes disposable QEMU overlays; these are sampled extrema, not an assertion about every instant. The final artifact expires **2026-10-25 02:29:52 UTC**. Images, disks, credentials and builder configuration were not uploaded. Podman reported its non-native overlay diff fallback; the three tiny test-layer COPY steps each took minutes, accounting for the observed overlay-build overhead without a storage-capacity failure.

The final release OCI manifest digest is **`sha256:0ff548500cdb7b6cf1cbea1139295489f155df90d14f5c3632176eb9d75f6d99`**. The separate test image is **`sha256:7f5a40f0bddafdb4965350d1857457a7f3557ab99a170530380670c2ad8f6b9d`**, matching the guest's raw `bootc status`. Base, source and result identities remain in [provenance](../../os/manifest/ci/03c/attempt3/provenance.json), both OCI manifests/digest files and the [evidence index](../../os/manifest/ci/03c/README.md).

### Not verified

**No green workflow or two-pass result exists. PR #3 was not marked ready because acceptance is unmet.** The unresolved automated assertion is the captured logind power-key receipt, despite observed QMP/console clean shutdown in both tested guests. The final readiness proof rules out assuming that the follower simply had not started. It does not establish why later logind output is absent, nor prove that the event traversed logind rather than another guest power path. No assertion was weakened to call this green.

**First hardware boot, after the existing installation/recovery-account prerequisites:** on AC with the plain terminal session, try an interactive Ctrl+Alt+F3 login with the independently provisioned recovery administrator, then verify the physical power button reaches logind and cleanly powers off. On the next boot, inspect the previous persistent journal (`journalctl -b -1 -u systemd-logind.service --no-pager`, plus the previous full boot journal) for the button record and orderly shutdown. Retain that evidence; merely seeing the laptop turn off is insufficient to establish the missing logind path. Also repeat a fresh boot/session/recovery trial: the required second automated fresh VM pass never ran. These are remaining checks, not performed or claimed hardware acceptance.

No hardware, NVIDIA rendering, firmware, battery/dock matrix, physical lid, installation, rebase or rollback test is claimed. The NVIDIA CDI generator fails in the GPU-less VM; this is not NVIDIA hardware qualification. CI proves the specified PAM password/account checks and running getty, rather than typing through its banner and shell startup.

Per brief 03's runner-only constraint, no local image/container/VM or mod Gradle task was run. `mod/` is unchanged. No Gradle daemon was started, so none needs stopping.

### JUDGMENT-CALL

No new production behavior or hard-to-undo owner decision. The existing recovery-provisioning and later distribution decisions remain separate. The PAM/test-layer choice is reversible CI code and does not change release authentication policy.

### PLAN-GAP

Attempt 2 demonstrated real guest poweroff while the required logind record was absent. Attempt 3 exercised cursor-based journal following in a separate transient cgroup without ordinary shutdown dependencies and proved readiness before the ACPI event; the logind assertion still failed. The evidence does **not** establish the remaining cause, so another speculative fix or removal of that assertion would be unjustified within the exhausted budget. See [systemd-run's detached service semantics](https://www.freedesktop.org/software/systemd/man/latest/systemd-run.html) and [journal cursor semantics](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html). The PAM callback follows the installed [Linux-PAM 1.7.2 ABI](https://github.com/linux-pam/linux-pam/blob/v1.7.2/libpam/include/security/_pam_types.h); wrong-password rejection prevents a privileged probe from silently bypassing authentication. No production design gap was established.

### Open questions

The logind power-button path and complete repeated-boot acceptance remain open as described above. Brief 03c's budget is exhausted; no additional run is requested or started here. Existing installer recovery-account and future distribution decisions remain outside this follow-up. The PR description is updated with this result and the PR stays draft/unmerged.

## 03b: recovery synchronization and static power acceptance

### Done

- `os/ci/vm.py`: authenticate the serial shell through a printed identity challenge, retrying across PAM's password-input flush. Upload shell commands in short heredoc lines, below the TTY canonical line limit. The recovery VT3 shell runs a CI-only script which checks UID 0 and `/dev/tty3`, creates a mode-600 root-owned proof, and prints `ARESOS_TTY_AUTHENTICATED`. The harness waits for that marker rather than any prompt format. The proof must independently contain `uid=0 tty=/dev/tty3`.
- `os/ci/serial_console.py`, `os/tests/test_serial_console.py`: answer the inherited login banner's cursor-position and dynamic-color queries. Four regressions cover queries split at every socket boundary, repeated queries, unrelated output and bounded buffering across long boot logs. Three real-PTY regressions cover a guest reading `/dev/tty`, scripts larger than the canonical line limit, and a nonzero guest exit. Completion printing is parsed in the same shell compound command before the heredoc executes, so a guest terminal reader cannot steal the completion command. Reply counts are exported in `serial-terminal.json`.
- `os/tests/power-events.py`: create a temporary Linux uinput device in the CI guest. Require logind to watch it, observe real lid-close/open state changes and journaled suspend/hibernate key presses, and retain the same labwc/foot PIDs with every sleep target/service still unentered. Reject low-level lid/sleep-key inhibitors as an alternative explanation for ignored events. Exercise all four direct logind sleep requests and require configuration-disabled errors. No image policy, base, driver or package pin changed.
- Export byte-preserved `bootc status --json` and runtime updater JSON immediately after guest-policy checks. Export event results, authenticated TTY proof, screenshots and fresh shutdown-console output. QEMU's ACPI power-button event must reach logind, then produce clean guest poweroff and QEMU exit 0. The final workflow boots the image twice, each with a new QEMU process, fresh firmware variables and a disposable disk overlay; each pass must independently satisfy every assertion. Evidence is separated under `vm-pass-1/` and `vm-pass-2/`. The workflow also compiles the changed Python files before building.
- `os/README.md`: document marker-based recovery, the runtime exports, event checks and the additional run budget.

### Verified

- Latest full attempt: [39698003724](https://github.com/carlsenares/AresOS/actions/runs/39698003724), source `5991246e5bbd5db52248432cbccff26ac1ff999b`. `python3 -m unittest discover -s os/tests -v` printed **`Ran 10 tests in 0.322s`, `OK`**, including all three real-PTY cases. `python3 -m py_compile os/ci/vm.py os/tests/power-events.py` and the four existing `bash -n` checks passed with no error output. Signature verification, locked RPM installation, protected-package comparison, both Podman build stages, container lint and the image audit passed (`Updater audit passed: 815 system/user units inspected`). Image build/audit took 10m52s; disk construction took 16m46s and printed `Build complete!`.
- In its KVM/UEFI guest, serial authentication produced the UID-0 challenge response, then `os/tests/guest.sh` printed `ARESOS_GUEST_CHECKS_PASSED`. The runtime audit printed `Updater audit passed: 828 system/user units inspected`; all five masked sleep-target starts were rejected, logind returned `s "no"`, UPower returned `s "Ignore"`, and the deployment assertion printed `Deployment backend: bootc (OSTree storage)`.
- The raw [bootc status](../../os/manifest/ci/03b/attempt3/vm-pass-1/backend.json) was successfully exported before failure. It records `kind=BootcHost`, `type=bootcHost`, `store=ostreeContainer`, a booted OSTree checksum and image digest `sha256:07d7e5fed1373fb21b6dfb43653dd25275a36034a8dcf266617527adaccdfb7e`. [Provenance](../../os/manifest/ci/03b/attempt3/provenance.json) identifies the exact tested checkout and unpublished image.
- The next export failed its one-line parsing assertion because the kernel inserted a clocksource watchdog message into the base64 payload. The complete runtime inventory remained in the saved serial log. It was recovered by removing **one** explicitly identified kernel record and decoding the remaining base64: [runtime-updaters.recovered.json](../../os/manifest/ci/03b/attempt3/vm-pass-1/runtime-updaters.recovered.json), 160,131 bytes / 828 units. This is recovered guest output, not a fabricated inventory or a successful automated export. The [recovery note](../../os/manifest/ci/03b/README.md) and lossless [serial capture](03b/attempt3/serial-console.zip) document that distinction.
- The [diagnostic framebuffer](screenshots/03b-attempt3-diagnostic.png) was downloaded and visually inspected: labwc displays the AresOS foot terminal as `ares`. It is boot/session evidence only. [Selected output](03b/attempt3/verification-output.txt), generated [manifests and metrics](../../os/manifest/ci/03b/attempt3/), and GitHub job/artifact metadata are committed.
- `git diff --check` passed for the implementation and final evidence edits. No local builds, containers, VMs, Gradle commands or daemons were started.

### Run budget and measurements

| Follow-up run | Result | Workflow elapsed |
|---|---|---:|
| [39690262586](https://github.com/carlsenares/AresOS/actions/runs/39690262586) | Cancelled during runner tool installation to correct PAM synchronization; image build never started. | 1m30s |
| [39690387240](https://github.com/carlsenares/AresOS/actions/runs/39690387240) | Full attempt 1: image/disk passed; the initial 30-second marker handshake stalled on unanswered login-banner terminal queries. | 32m18s |
| [39694232689](https://github.com/carlsenares/AresOS/actions/runs/39694232689) | Full attempt 2: seven regressions, image/disk, serial authentication and guest policy passed; a guest terminal reader consumed `pr` from the separately queued completion `printf`. | 33m31s |
| [39698003724](https://github.com/carlsenares/AresOS/actions/runs/39698003724) | Full attempt 3: ten regressions, image/disk, guest policy and raw backend export passed; an interleaved kernel record broke updater-export framing. Only the first VM pass started. | 31m54s |

All **3/3** authorized additional full runs were used, plus one pre-build cancellation. Follow-up workflow elapsed totals **99m13s**; all 13 package workflows total **256m58s**, including the original 157m45s. These are observed workflow elapsed times, not a billing claim. The [run ledger](03b/ci-runs.json), per-attempt metadata and metrics retain the evidence. No paid runner, registry upload, billing change or owner credential was used.

| Latest tested image / runner | Observed value |
|---|---:|
| Base / derived image uncompressed bytes | 13,010,242,255 / 13,194,841,858 |
| VM raw disk virtual / allocated bytes | 31,666,995,200 / 9,562,324,992 |
| Runner total / highest sampled used / lowest sampled free bytes | 76,887,154,688 / 70,608,211,968 / 6,262,165,504 |
| Latest artifact compressed / all four follow-up artifacts bytes | 223,797 / 611,130 |

The final raw disk is the builder output; guest writes use disposable QEMU overlays. Root-filesystem sampling includes temporary overlays, at ten-second intervals. The latest artifact expires 2026-10-25 00:41:39 UTC. Neither images nor VM disks were uploaded. The original maximum disk-use sample remains larger than these follow-up samples.

### Not verified

There is **no green 03b workflow**. The new authenticated VT3 marker/proof, injected lid/suspend/hibernate events, direct sleep-request tests and clean ACPI power-key shutdown were not reached. The second fresh VM pass did not start. No automated TTY success screenshot, power-event result or clean-poweroff file is claimed. PR #3 was not marked ready because acceptance is unmet.

Commit `63c206e` changes export framing to wrap base64, remove recognizable interleaved kernel records and verify a SHA-256 computed by the guest before accepting decoded bytes. Its three added regression tests cover the observed interruption at every payload boundary, wrapped CRLF output, and rejection of corruption/incomplete frames. **Neither that fix nor those three tests was run**: the CI budget is exhausted and the brief prohibits local execution. It is pushed with `[skip ci]` solely to prevent an unauthorized fourth full run; this is not evidence of a passing test. The ten-test CI result above belongs to `5991246`, not the later source fix.

No hardware, NVIDIA rendering, battery, physical lid, firmware, installation, rebase or rollback trial is claimed. The unexecuted synthetic input test is intended to exercise the guest logind path and requires all three configured lid policy values; it would not qualify the laptop's ACPI wiring or a physical battery/dock matrix.

No local Gradle, image build, container or VM command was run: brief 03 restricts execution on the owner's laptop to git/gh and reserves builds for the hosted runner. The shell mod is untouched. No Gradle daemon was started.

### JUDGMENT-CALL

No new production behavior or owner decision was introduced. The original recovery-provisioning and distribution decisions below still apply.

### PLAN-GAP

PAM restores password echo with an input flush, so immediately queuing a shell command can lose it. Serial authentication now retries its own short challenge before sending scripts; VT3 waits for the authenticated root shell process and retries its marker script during startup. See the [Linux-PAM implementation](https://github.com/linux-pam/linux-pam/blob/v1.7.0/libpam_misc/misc_conv.c). The first full follow-up attempt also exposed the inherited Bazzite banner waiting on unanswered cursor/color queries. The harness now supplies the [documented terminal replies](https://invisible-island.net/xterm/ctlseqs/ctlseqs.html) rather than changing the guest's login configuration. The second full attempt authenticated and passed the guest-policy script, but a guest program consumed the first two characters of the separately queued completion command (`intf: command not found`). The compound-command fix is covered by a real controlling-PTY regression with a guest that drains terminal input. The temporary event injector follows the [kernel uinput interface](https://docs.kernel.org/input/uinput.html) and the pinned [systemd 259.9 input handling](https://github.com/systemd/systemd/blob/v259.9/src/login/logind-button.c).

### Open questions

The owner/Claude must authorize a new CI budget before another full run can validate `63c206e` and reach the outstanding TTY and power tests. The current brief's three-full-run limit is exhausted.

The original image-distribution and installer recovery-account questions remain for later packages. Switching to `bazzite-nvidia-open` and publication remain outside 03b.

## Original package 03 results (before the follow-up)

### Done

- `os/Containerfile`, `build.sh`, `packages.lock.json`: derive the pinned Bazzite NVIDIA image, add ten exact Fedora RPMs with SHA-256 checks and RPM signature verification, retain the upstream kernel/NVIDIA package set, and export the complete package inventory. No image is published.
- `os/config/`: greetd initial auto-login as unprivileged `ares` (UID 1000), labwc and foot showing AresOS, Super+Ctrl+Escape recovery terminal, independent tty3 getty, and static logind/systemd-sleep/UPower policy. Both image account passwords are locked; CI provisions its own disposable recovery credential in the VM disk.
- `os/policy/`, `tests/`: system/user updater masks, desktop and autostart exclusions, passwordless updater grant removal, daily-user polkit restrictions and updater binary permissions. The audit scans enabled units and drop-ins and requires a reviewed allowlist for updater-like bookkeeping. Regression tests cover system/user units and updater commands hidden in drop-ins.
- `.github/workflows/os-image.yml`, `os/ci/`: pinned Actions and disk builder, standard Ubuntu runner, signed-base verification, Podman build, file-backed BIB disk, OVMF/QEMU boot and serial/QMP checks, small evidence artifacts retained for three days, and time/storage measurements. VM checks include the recovery shortcut, authenticated tty3, update/sleep exclusions and the ACPI power button.

### Verified

- Stable resolved by CI to `ghcr.io/ublue-os/bazzite-nvidia@sha256:3d13e825932cfddf73c369db7e7397bf79e8bf8881a4276b9a958b37234899e1`, Bazzite `44.20261012.1`, amd64. The [probe](https://github.com/carlsenares/AresOS/actions/runs/39665214585) passed in 1m18s. `cosign verify --key os/keys/bazzite.pub <digest-reference>` succeeded using the [upstream documented method](https://github.com/ublue-os/bazzite#verification); the verified identity is `ghcr.io/ublue-os/bazzite-nvidia`. Public key source and builder digest are recorded in `os/manifest/base.json`.
- [Package-resolution run](https://github.com/carlsenares/AresOS/actions/runs/39668611435): `dnf5 ... download --resolve --destdir=/tmp/ares-rpms ...` and signature-checked local RPM installation printed `Complete!`, installing ten packages / approximately 5 MiB, with no package removals. The kernel/NVIDIA before/after `diff -u` passed. The resulting inventory contains 2,798 RPMs.
- That inventory reports kernel `6.18.56-ogc1.1.fc44.x86_64` and NVIDIA `580.178.04` (the complete kernel/driver package subset also includes headers/tools with their own versions). This proves package preservation, not NVIDIA hardware operation.
- Local `git diff --check` passed before each implementation commit. No local builds, containers, VMs, installs or Gradle daemons were started.
- [First VM attempt](https://github.com/carlsenares/AresOS/actions/runs/39671066887): all three updater regressions passed (`Ran 3 tests in 0.012s`, `OK`), exact RPM hashes matched, container lint passed, and the audit printed `Updater audit passed: 815 system/user units inspected`. Disk builder printed `Build complete!` after 17m06s. QEMU used `-accel kvm -cpu host` and booted the intended session; the [initial framebuffer](screenshots/initial-boot.png) shows the AresOS terminal. Automated guest checks then failed because the harness matched the kernel compiler's `root@...` banner before the authenticated shell prompt; source commit `083f6c4` fixed that synchronization bug, and subsequent runs passed serial authentication.
- [Final run 39685234531](https://github.com/carlsenares/AresOS/actions/runs/39685234531), exact source `ee9ee390031bfa2d20a32129aeb0715a6af700f3`: `python3 -m unittest discover -s os/tests -v` printed `Ran 3 tests in 0.015s`, `OK`; all four `bash -n` checks passed. Signature verification, locked RPM resolution, protected-package comparison, both `podman build` stages, `bootc container lint` and the 815-unit build audit passed. Image build/audit took 11m48s and file-backed disk construction took 15m30s (`Build complete!`).
- In that KVM/UEFI guest, `os/tests/guest.sh` reached `ARESOS_GUEST_CHECKS_PASSED`: greetd/default graphical target, labwc/foot under UID 1000, no wheel/sudo access, root-only updater entry points, no inherited display manager/power agent, every explicit system/user mask, and `Updater audit passed: 827 system/user units inspected`. Each of the five sleep starts printed `Unit ... is masked`; logind returned `s "no"`, UPower returned `s "Ignore"`, and `bootc status --json` parsed successfully with a nonempty booted image, printing `Deployment backend: bootc (OSTree storage)`.
- QMP Super+Ctrl+Escape passed the assertion that at least two `ares` foot processes existed. The [final labwc screenshot](screenshots/aresos-labwc.png) was downloaded with `gh run download` and visually inspected. Ctrl+Alt+F3 reached a separate tty3, accepted the CI-only root credential, and the [diagnostic framebuffer](screenshots/tty3-authenticated-diagnostic.png) visibly shows its root shell. The automated wait then expected the serial console's bracketed prompt, while this themed TTY displays `root@bazzite:~#`; it returned `ARESOS_CMD_DONE:1`. This is the remaining failed assertion, not a green recovery test.

#### Final image and resource measurements

The [CI snapshot](../../os/manifest/ci/README.md) identifies the tested source and result. The result is unsigned, local to runner storage and unpublished.

| Item | Observed value |
|---|---|
| Result OCI manifest digest | `sha256:3867d3a4a090e25b7a2e1c49cb0dbec0466f3611511bf3b6f9bebcde7732dddd` |
| Verified base key DER SHA-256 | `efaae036a5afefcfe2c64686db0311ab64e57ae794be634d80c25286695336a6` |
| Deployment backend | bootc 1.16.13, OSTree storage; live guest assertion passed. Raw status export was after the failed TTY wait and was not reached. |
| Base / derived image uncompressed | 13,010,242,255 / 13,194,784,512 bytes |
| VM disk virtual / allocated | 31,666,995,200 / 9,601,400,832 bytes |
| Runner total / highest sampled used / lowest sampled free | 76,887,154,688 / 69,481,185,280 / 7,389,192,192 bytes |
| Final workflow / job elapsed | 32m02s / 31m58s |
| All nine workflows elapsed | 157m45s; six full attempts plus three short probe/cancel/fixture runs, below 400 minutes. |
| Final artifact / all nine artifacts | 206,513 / 1,154,644 bytes compressed; final expiry 2026-10-24 22:48:03 UTC. |

The largest sampled use across all attempts was 70,791,372,800 bytes, leaving 6,079,004,672 bytes free. The image and disk fit a standard hosted runner; the remaining blocker is test synchronization, not measured runner capacity. [Run ledger](ci-runs.json), [artifact ledger](ci-artifacts.json) and per-attempt job metadata retain the timings and sizes.

#### CI attempts

| Run | Result | Workflow elapsed | Evidence |
|---|---|---:|---|
| [39665214585](https://github.com/carlsenares/AresOS/actions/runs/39665214585) | Base/signature metadata probe passed | 1m18s | Base compressed layers: 5,667,820,697 bytes. |
| [39666023435](https://github.com/carlsenares/AresOS/actions/runs/39666023435) | Cancelled before building to include Git-ignored launch scripts | 1m35s | No image build. |
| [39666174541](https://github.com/carlsenares/AresOS/actions/runs/39666174541) | Build failed on invalid DNF5 install flag | 15m41s | `Unknown argument "--destdir=/tmp/ares-rpms" for command "install".` Last disk sample: 40,528,670,720 bytes free. |
| [39668611435](https://github.com/carlsenares/AresOS/actions/runs/39668611435) | Packages passed; updater audit rejected inherited units | 11m14s | Build peak used: 41,605,488,640 bytes; minimum free: 35,264,888,832. Base uncompressed: 13,010,242,255 bytes. |
| [39670711076](https://github.com/carlsenares/AresOS/actions/runs/39670711076) | New drop-in regression exposed an incomplete fixture; fixed | 1m31s | `Ran 3 tests in 0.017s`, `FAILED (errors=1)`; no image build. The fixture now contains both system/user unit directories and the assertion is retained. |
| [39671066887](https://github.com/carlsenares/AresOS/actions/runs/39671066887) | Image, audit, disk and visible session passed; serial harness synchronization failed | 39m24s | Peak runner/build disk use 70,523,858,944 bytes; minimum free 6,346,518,528. Image uncompressed 13,194,995,456 bytes. VM disk virtual 31,666,995,200 bytes, allocated 9,824,305,152. |
| [39676911132](https://github.com/carlsenares/AresOS/actions/runs/39676911132) | Image/disk and initial guest assertions passed; test misread sudo listing's status | 24m36s | `User ares is not allowed to run sudo on bazzite.` The successful root policy-listing exit status was incorrectly treated as an access grant; the assertion now requires the explicit policy denial. Disk conversion took 12m22s. Peak disk use 69,149,749,248 bytes; minimum free 7,720,628,224. |
| [39680828297](https://github.com/carlsenares/AresOS/actions/runs/39680828297) | Account permissions, display-manager exclusions and all named masks passed; runtime audit caught generated bootc notifications | 30m24s | Rejected `bootc-status-updated.path` and `bootc-status-updated-onboot.target` (`enabled-runtime`). Pinned bootc 1.16.13 source confirms status notification only; exact units were reviewed and added to the allowlist. Peak use 70,791,372,800 bytes; minimum free 6,079,004,672. |
| [39685234531](https://github.com/carlsenares/AresOS/actions/runs/39685234531) | Guest policy/backend and recovery shortcut passed; TTY prompt-format wait failed | 32m02s | Visible root shell on tty3 uses `root@bazzite:~#`, unlike the bracketed serial prompt expected by the harness. Identity-proof command, backend-file export and clean poweroff were not reached. |

The table uses workflow elapsed time, including setup and evidence upload, rather than claiming a billing figure. Disk usage is sampled every ten seconds across the runner's root filesystem; the reported peak is the highest observed sample. Image size is Podman's uncompressed size; sparse VM disk virtual and allocated sizes are reported separately. There were six full build attempts, plus the metadata probe, one pre-build cancellation and one fixture-only failure. No paid runner, registry upload, billing change or owner credential was used. Artifact retention is three days; neither container images nor VM disks are artifacts.

### Not verified

The workflow is not green. The automated tty3 identity-proof command and ACPI power-button clean shutdown were not reached. The framebuffer supports successful TTY authentication, but the failed automated wait remains a required fix. The harness must synchronize on authenticated TTY state or accept its actual prompt, retain the root-owned proof-file assertion, and then pass a fresh complete run before merge. This was not changed or rerun after the sixth attempt; pushing a CI-source change would automatically start another full build beyond the selected budget.

The guest's live `bootc status` assertion passed, but raw JSON export was not reached. The runtime updater inventory was written under `/run` and is not copied by this source's exporter; the committed full inventory is from the image build. [backend-observation.json](../../os/manifest/ci/backend-observation.json) records the observed backend and this evidence limit; it is not a fabricated status dump. [Selected output](verification-output.txt) retains the key results. No poweroff evidence file or successful automated TTY screenshot is claimed.

No hardware, NVIDIA rendering, Secure Boot/MOK enrollment, Windows/BitLocker return, wireless, battery event or suspend qualification is claimed. There is no installer, previous deployment, deploy/pin/rollback rehearsal, Minecraft, app helper, backup or power coordinator in this package. `mod/` is absent in this worktree, so `./gradlew build` cannot be run; no Gradle daemon needs stopping.

### Updater inventory and exact power settings

The explicit mask inventories are [system units](../../os/policy/masked-system-units.txt) and [user units](../../os/policy/masked-user-units.txt). Installed `plasma-*`, `gnome-session*` and `org.gnome.SettingsDaemon.Power*` units are also masked. The generated build inventory covers 656 system and 159 user units, including 52 system masks and 43 user masks. It records scope, effective enablement state, suspicious-name/content flag and command lines. An unknown enabled updater-like unit, including a drop-in override, fails the build. The final guest audit also passed with 827 runtime units.

| Mutation path | Configured exclusion |
|---|---|
| uupd | Timer, automatic service and manual service masked; system, Flatpak, Homebrew and Distrobox modules disabled. |
| rpm-ostree | Automatic units masked; `/etc/rpm-ostreed.conf`: `[Daemon] AutomaticUpdatePolicy=none`. |
| bootc / systemd sysupdate | Fetch/apply/update units, sysupdate timer/service/daemon and D-Bus alias masked. |
| Bootloader / first boot | `bootloader-update.service` and `bazzite-hardware-setup.service` masked. |
| Flatpak / Homebrew / containers | Setup/update/runtime-sync entry points and Podman auto-update units masked; Homebrew auto-update disabled in the session environment. |
| User entry points | Update NOPASSWD grant files removed; `ares` outside wheel with polkit denials; retained update/portal/store commands root-only; update desktop entries removed; inherited XDG autostarts hidden. |

The [reviewed allowlist](../../os/policy/updater-allowlist.json) retains utmp/initialization bookkeeping, local filename/man-page indexes, audit logging, authentication-template application, NVIDIA CDI device-description generation, DNSSEC root trust-anchor refresh and XDG user-directory initialization. These do not install OS/app/driver packages. NVIDIA CDI's path watcher mentions driver upgrades, but its [v1.20.1 commands](https://github.com/NVIDIA/nvidia-container-toolkit/blob/v1.20.1/deployments/systemd/nvidia-cdi-refresh.service) generate device nodes/descriptions from the installed driver. [Authselect](https://github.com/authselect/authselect/blob/master/systemd/authselect-apply-changes.service) applies installed authentication templates. [Unbound](https://nlnetlabs.nl/documentation/unbound/unbound-anchor/) refreshes DNSSEC trust data. [XDG user dirs](https://wiki.freedesktop.org/www/Software/xdg-user-dirs/) creates local home directories.

The runtime generator also enables [bootc 1.16.13 status notifications](https://github.com/bootc-dev/bootc/blob/v1.16.13/docs/src/man/bootc-status-updated.path.5.md): a path watcher on `/ostree/bootc` and notification targets, with no update command. These literal names are allowlisted after reviewing the matching [unit definitions](https://github.com/bootc-dev/bootc/tree/v1.16.13/systemd), not a wildcard for bootc services. The real fetch/apply/sysupdate units remain masked.

| Configuration | Exact values |
|---|---|
| logind lid | `HandleLidSwitch=ignore`, `HandleLidSwitchExternalPower=ignore`, `HandleLidSwitchDocked=ignore`. |
| logind keys | `HandlePowerKey=poweroff`; `HandlePowerKeyLongPress`, `HandleRebootKey`, `HandleRebootKeyLongPress`, `HandleSuspendKey`, `HandleSuspendKeyLongPress`, `HandleHibernateKey`, `HandleHibernateKeyLongPress` all `ignore`. |
| logind idle/recovery | `IdleAction=ignore`, `NAutoVTs=6`, `ReserveVT=6`; explicit `getty@tty3.service` enabled. |
| systemd sleep | `AllowSuspend=no`, `AllowHibernation=no`, `AllowHybridSleep=no`, `AllowSuspendThenHibernate=no`; all sleep targets and corresponding services masked. |
| UPower | `CriticalPowerAction=Ignore`, `AllowRiskyCriticalPowerAction=true` (required for Ignore). |
| Homebrew environment | `HOMEBREW_NO_AUTO_UPDATE=1`, `HOMEBREW_NO_INSTALL_FROM_API=1`. |

The guest requires logind `CanSuspend` to return `s "no"` and separately requires attempts to start all five sleep targets to fail. In the installed [systemd 259.9 implementation](https://github.com/systemd/systemd/blob/v259.9/src/login/logind-dbus.c), configuration-disabled sleep returns `no`; `na` describes other unavailable sleep support. The initial guessed expectation was corrected from `na` to `no` after reviewing that code, without removing the target-start assertions.

### JUDGMENT-CALL

- **Recovery provisioning:** chose locked image passwords and no daily-user administrator group, with a random VM-only root password supplied by CI's disk customization. Rejected a committed default password or passwordless administrator. This keeps credentials out of the image source and proves a separate authenticated console. The installer must provision an independently known recovery login before any owner boot; changing this later is an account/provisioning change, not a disk-format migration.
- **Bazzite first-boot hardware setup:** masked it after reading the pinned script. It can run `rpm-ostree kargs`, enable hibernation and reboot, so allowing it would defeat the image's static power/deployment policy. Kernel, driver and firmware packages remain intact. Rejected blindly allowlisting its name. Any required laptop quirk must be selected and qualified explicitly before hardware use; this may cost additional P2/P3 configuration/testing.
- **Distribution recommendation for P3:** subject to the owner's explicit decision, use a public, signed GHCR derivative with a digest-pinned manifest for the future safe installer to consume. This avoids large Actions artifacts and private-package assumptions. If the image must stay private, prefer an owner-approved build on a separate Linux builder and a verified offline transfer. No registry publication, visibility or billing changes were made here.

### PLAN-GAP

- The first inherited-unit audit found additional mutation paths beyond the brief's named `uupd`/bootc/rpm-ostreed units: Bazzite hardware setup, bootloader update, Homebrew setup, Flatpak setup/verification and systemd sysupdate. These were added to the explicit mask policy. The QEMU guest agent is also masked; CI uses serial/QMP instead.
- [GitHub's current billing documentation](https://docs.github.com/en/billing/concepts/product-billing/github-packages) says Container registry storage/bandwidth is currently free, whereas the brief assumes a 500 MB private-package limit. The explicit no-publication instruction was still followed; this is information for the later distribution decision, not authorization to publish now.
- This image deliberately reports UPower's critical action as `Ignore`; hardware/battery use must wait for the independent power coordinator and critical-battery tests in P2. Hiding Sleep is not treated as adequate; systemd/logind paths are blocked too.

### Open questions

- This original budget question was answered by brief 03b's additional three full attempts. Their results and the remaining budget blocker are recorded above; the PR remains draft.
- Owner decision before P3: approve public signed image distribution, or retain privacy and choose a separate Linux build/transfer route.
- Installer package: define recovery-account provisioning and offline recovery credentials before the first owner-controlled boot. Neither image account has a usable password by default.
