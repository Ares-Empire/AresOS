# Package 06: private image release

Status: **06e ACCEPTANCE MET — full revised guest sequence passed; rendered rollback greeter visually inspected**. [PR #10](https://github.com/carlsenares/AresOS/pull/10) remains open and is not merged. Physical installation remains gated.

The [06e record](#06e-vm-qualification-2026-10-22) below is current. Earlier sections, including 06c's passing backend rehearsal and 06d's failed qualification, are historical with separate run budgets. ISO, protected-Windows two-disk and hardware qualification remain separate gates.

## Done

- `os/Containerfile`, `manifest/base.json`: switch the flavor to signed, digest-pinned `bazzite-nvidia-open` KDE 44.20261012.1, preserving upstream kernel/NVIDIA packages and the existing exact RPM lock. Add source/revision labels.
- `os/build.sh`, image-owned `sysusers.d`, updater audits and policy: reserve UID 1000 for installer-created `ares-recovery`; daily locked `ares` is UID/GID 1001. The same native declaration runs at build and boot so the installer's persistent passwd/group files cannot hide the new account. A real sysusers regression preserves the recovery administrator and wheel membership, verifies the daily account's locked password and fixed IDs, and checks idempotence. Check the daily user's actual configured bus and generated-unit directory. Keep strict updater masks, Cockpit rejection, canaries, two fresh VM passes and offline logind proof. The two explicit user-manager allowlist entries refer to the same already-reviewed systemd manager template; no updater grant is added.
- `os/ci/publish.sh`, workflow: publish private `ghcr.io/carlsenares/aresos` only after package-03 checks, refuse tag reuse/public-package uploads, verify registry digest/private visibility, sign with GitHub OIDC and verify exact workflow identity. Only the built-in `GITHUB_TOKEN` is used. Full workflows are manually dispatched to protect the budget. A switch-only retry verifies the original successful image job, source identity and unchanged runtime payload before reusing its digest; it never rebuilds or overwrites that image.
- `os/ci/switch_vm.py`, `prepare-disk.py`, `os/release/*.sh`: construct an unmodified-upstream stock stand-in with a separate password-protected recovery administrator. Verify the release with stock cosign, pin actual stock identity, pull the published digest, switch/reboot, check session/policy/partition identities, log in and authenticate sudo on real tty3 through QMP keyboard, then roll back and require the original stock checksum. No test overlay is present in either switch-test deployment. Mask disposable passwords/hashes before builder logging; exclude all disks, credentials and raw authentication transcripts from evidence.
- `manifest/installer-isos.json`, `docs/INSTALL.md` §6, `os/README.md`: official live and legacy ISO checksum records, private credential storage, exact account/trust commands and explicitly unqualified switch/rollback candidates and remaining install gates. Preserve the guide's current-live whole-drive route; no installer was run.

## Verified

The image and failed full workflow used source **`01aae1e38ec11356677f526692783c14b89a1d4d`**. The later UART harness fix is checks-only verified, as detailed below; other later changes are documentation/evidence. No local build, VM, package installation or Gradle command ran.

- **Checks-only preflight:** `gh workflow run os-image.yml --ref pkg/06-image-release -f checks_only=true`, [39794494112](https://github.com/carlsenares/AresOS/actions/runs/39794494112), success. Printed **`Ran 50 tests in 0.711s`, `OK`**, **`Live hosted system manager passed: 437 unit files, 465 unit names`** and **`Existing release package is private`**. Official ISO metadata resolution and upstream signature verification passed. [Output](logs/preflight-final-runtime.txt), [run/jobs and release inputs](../../os/manifest/ci/06/preflight/).
- **Final full dispatch:** `gh workflow run os-image.yml --ref pkg/06-image-release -f checks_only=false`, [39796347427](https://github.com/carlsenares/AresOS/actions/runs/39796347427). Its image job succeeded, printing **`Ran 50 tests in 0.813s`, `OK`**, **`Updater audit passed: 814 system/user units inspected`**, and **`Release excludes CI service and credentials; both passwords locked`**. Both lint invocations reported **11 passed, 1 skipped, 3 warnings**; the retained warnings concern runtime-directory residue, the DNF log and `/var` tmpfiles coverage; no lint setting was changed. Exact RPM lock/content and unchanged kernel/NVIDIA checks passed. Disk construction completed within its deadline.

Runner commands included:

```text
python3 -m unittest discover -s os/tests -v
python3 -m py_compile os/ci/*.py os/ci/overlay/*.py os/tests/audit.py os/tests/power-events.py
bash -n <all os/ci/*.sh, os/release/*.sh, overlay/updater-generator,
         os/build.sh, os/tests/guest.sh, aresos-session and aresos-terminal>
cosign verify --key os/keys/bazzite.pub <pinned upstream digest>
podman build <locked packages, release and separate VM overlay>
bootc-image-builder <pinned builder, file-backed UEFI/Btrfs disk>
sudo -E env ARESOS_VM_PASS=1 python3 os/ci/vm.py
sudo -E env ARESOS_VM_PASS=2 python3 os/ci/vm.py
bash os/ci/publish.sh
python3 os/ci/verify_release.py 39796347427
sudo -E python3 os/ci/switch_vm.py
```

Python/Bash syntax checks produced no error output. The workflow contains the full arguments; the retained full workflow log records actual output. The graph implementation remains deferred even though its parser regression tests pass.

| Required original guest checks | Fresh VM 1 | Fresh VM 2 |
|---|---|---|
| Daily account | UID/GID 1001, locked password, no wheel/sudo | Same |
| Generated/static canaries | Both rejected; audit exit 1; `mode=static-strict` | Same |
| Normal updater audit, after fixture removal | 1,084 units, zero offenders; Cockpit mask effective | Same |
| Recovery shortcut/getty/login PAM | Wrong password rejected; correct password/account accepted (test-only root UID 0) | Same |
| Lid/sleep input and direct sleep requests | Events observed and ignored; session retained; requests rejected | Same |
| QMP/console shutdown | Guest shutdown, QEMU exit 0, poweroff target reached | Same |
| Offline journal/logind proof | Passed, boot `0151a944fb1743dfbfce01d5afb9e1d8` | Passed, boot `f637b8c76d81449eb6ae225cf54f4b01` |

Neither pass used the hardware-gate contingency. Each actual offline journal was verified and read through the existing read-only userspace Btrfs fallback, proving the power-key event, power-off request and orderly logind stop. [Raw per-pass results](../../os/manifest/ci/06/image-6/). The kernel/NVIDIA package inventory is **7.2.9-ogc3.1.fc44 / 615.78.08**; this is an unchanged-package comparison, not GPU rendering qualification.

The private published release is **`ghcr.io/carlsenares/aresos@sha256:25de68a75ef4534f903f7dd2d8ce1eb9e86c1b2d165c2631152fb1f1c711f91a`**, tag **`06-01aae1e38ec11356677f526692783c14b89a1d4d`**. CI checked its registry manifest hash, actual private visibility and keyless signature. Its separate local release manifest is `sha256:e3ae8482d31444b59f67c31dd19df4abe0290a1fe941c8b7544078374a6e7a6e`; the VM overlay is `sha256:93ce9885a132a85e4edf101247607b1679e61e163e68f792e7d64fca32734551`. Registry transfer changes manifest representation; only the GHCR digest is the laptop handoff. The overlay was never published. [Release receipt](../../os/manifest/release.json), [raw manifests/signatures](../../os/manifest/ci/06/image-6/).

**Full acceptance is blocked.** Stock Bazzite performed its one orderly hardware-setup reboot, then `ares-recovery` logged in on serial TTY `ttyS0` with the random password and authenticated sudo. Its actual UID was 1000 with wheel membership. Stock display-manager checks and identity-aware pinning passed. Stock cosign verified the private release signature, and `bootc switch --retain <published digest>` privately pulled and staged the exact `25de…f91a` image, returning exit 0.

The subsequent `systemctl reboot` did not make QEMU exit within the unchanged **180 seconds**. The screenshot shows systemd shutdown/unmount progress, clock/watchdog messages and a virtio-GPU vblank warning. QMP has only cleanup's `guest=false, reason=host-signal`, not a completed guest reset. **No staged-image boot, post-rebase ares session/updater audit, recovery-admin tty3 login, after-switch partition comparison or rollback was reached.** There is no passing switch `result.json`. Only the initial partition snapshot exists. [State/commands](../../os/manifest/ci/06/switch-6/), [failure output](logs/final-switch-failure.txt), [stock screenshot](screenshots/final-stock-bazzite.png), [shutdown-timeout screenshot](screenshots/final-stock-shutdown-timeout.png). Both screenshots were visually inspected.

A concrete harness flaw was found: `Guest.reboot()` waited for process exit without draining its serial socket, allowing guest UART output to fill the socket and block progress. Commit **`1745f55e4fb549e8b9110711e426f97c56f16515`** drains it, answers terminal queries, retains a secret-redacted shutdown transcript and keeps the same 180-second deadline and required exit/QMP assertions. This does **not** establish that every observed shutdown warning was caused by backpressure or that the real VM reboot is fixed.

**Post-fix checks-only:** [39809324095](https://github.com/carlsenares/AresOS/actions/runs/39809324095), success: **`Ran 52 tests in 1.522s`, `OK`**, live host **437 unit files / 465 unit names**. A real subprocess must write more than the socket capacity and receive its terminal-query reply before it can exit; a second test still rejects a process past its deadline. [Exact output](logs/reboot-drain-regressions.txt). This run built no image or VM. The six-large-run cap prevents another stock-switch rehearsal, so the correction and post-rebase account merge remain unqualified in a real guest. The signed runtime image is unchanged by this harness-only fix.

All six final image-job framebuffers were visually inspected. Both labwc images show the AresOS terminal and recovery hints; both tty3 images show a getty login prompt. The last frames are diagnostics, not shutdown proof: VM 1 still shows the terminal, VM 2 is dark with a small Bazzite label. Journal/QMP records supply the shutdown proof. [VM 1 session](screenshots/final-image-vm-1-aresos-labwc.png), [VM 2 session](screenshots/final-image-vm-2-aresos-labwc.png), [VM 1 tty3](screenshots/final-image-vm-1-aresos-tty3-getty.png), [VM 2 tty3](screenshots/final-image-vm-2-aresos-tty3-getty.png).

Original artifact ZIPs are preserved with GitHub digest/size metadata under [artifacts/](artifacts/); downloaded archive SHA-256 values were checked against that metadata. Expanded `.txt` and workflow-log display copies normalize trailing whitespace/line endings; original bytes remain in the archives. No credential, disk, builder configuration, authentication transcript or binary journal was uploaded. Artifact/log text was checked for unmasked SHA-512 password hashes and GitHub token forms before committing.

Final file verification: parsed **18 JSON files**, checked **62 relative document targets**, and passed `git diff --cached --check`. `git diff --exit-code 01aae1e38ec11356677f526692783c14b89a1d4d -- <runtime payload paths>` passed: Containerfile/build/config/policy, package lock, installed audit, base and verification key match the published source. These are Git/file checks, not a local build or guest test. No Gradle daemon was started.

### Measurements and run budget

**6/6 large dispatches used; no seventh.** Conservatively includes both canceled setups and the switch-only retry. The [run ledger](ci-runs.json) records all **24** dispatches; [job metadata](ci-jobs.json) records their actual timestamps. Completed non-skipped jobs total **15,517 seconds = 258m37s**; rounding each started job up to a minute gives **274 minutes** as a conservative quota proxy. These are elapsed-job measurements, not an invoice or claim about GitHub's billed totals. Both are below the brief's approximately 400-minute cap.

| Large attempt | Run | Result and measured job time |
|---|---|---|
| 1 | [39765871220](https://github.com/carlsenares/AresOS/actions/runs/39765871220) | Canceled before disk preparation; first-publication absence handling; 1m32s |
| 2 | [39766382296](https://github.com/carlsenares/AresOS/actions/runs/39766382296) | Canceled before disk preparation; mask disposable password/hash before builder output; 5m28s |
| 3 | [39767276468](https://github.com/carlsenares/AresOS/actions/runs/39767276468) | Image audit passed, raw-disk step exceeded its original 20-minute allocation; no VM/publish; 50m44s |
| 4 | [39774351695](https://github.com/carlsenares/AresOS/actions/runs/39774351695) | Image/two fresh VMs/private signing passed (52m46s); stock pre-login initialization reset failed harness (24m55s) |
| 5 | [39786345222](https://github.com/carlsenares/AresOS/actions/runs/39786345222) | Switch-only reuse of attempt 4; stock reboot/login/sudo passed, terminal JSON parse failed before switch; 38m02s |
| 6 | [39796347427](https://github.com/carlsenares/AresOS/actions/runs/39796347427) | Corrected image/two VMs/private signing passed (49m11s); stock private verification/pull/staging passed, reboot deadline failed (31m39s) |

Checks-only runs: **18 total: 14 successful, 2 failed, 2 canceled before a job started**; started jobs total **4m20s**. The first metadata probes hit official-site HTTP 403; switching to the official picker Git source and a declared browser-compatible User-Agent resolved that preflight, without ISO/image-layer downloads. The final 50-test preflight preceded attempt 6; the final 52-test run only verifies the later UART correction. Failed/canceled attempts remain failures, never green evidence. Disk-step allocation was increased from 20 to 30 minutes after measured output, within the declared overall budget; no assertion was weakened.

| Measurement | Final image job | Final stock-switch job |
|---|---:|---:|
| Base uncompressed bytes | 13,243,302,041 | 13,243,302,041 |
| Release uncompressed bytes | 13,428,492,892 | 13,428,492,892 |
| Disk virtual bytes | 31,666,995,200 | 53,141,831,680 |
| Disk allocated bytes | 9,788,653,568 | 10,670,039,040 |
| Highest sampled runner used bytes | 71,552,770,048 | 68,788,998,144 |
| Lowest sampled free bytes | 5,317,607,424 | 8,081,379,328 |
| Runner filesystem total bytes | 76,887,154,688 | 76,887,154,688 |
| Compressed evidence artifact bytes | 3,216,498 | 3,360,526 |

Disk sampling is every ten seconds, so extrema are sampled. [Image metrics](../../os/manifest/ci/06/image-6/metrics.json), [stock metrics](../../os/manifest/ci/06/switch-6/metrics.json). Published manifest compressed layer sizes sum to **5,702,053,153 bytes**; this is a logical layer sum, not unique account storage after deduplication. Artifact retention is three days; original final artifacts are now preserved in Git with their digest/size/expiry metadata. Earlier measured disk failures are under `attempt-3`, `attempt-4-switch` and `attempt-5-switch`; prior successful image evidence is explicitly historical under `os/manifest/ci/06/image/`.

Only standard Ubuntu hosted runners were used. No paid feature, billing setting, owner disk, Windows setting, Minecraft folder or system software was touched. The brief's supplied approximately 750 already-used monthly minutes is an input, not a newly measured billing figure. GitHub's Packages billing page was checked on 2026-10-22 before publication and explicitly exempts Container registry image storage/bandwidth; Actions minutes/artifacts remain separate. [Billing source](https://docs.github.com/en/billing/concepts/product-billing/github-packages).

## Not verified

- **Blocking:** full CI is red at stock reboot. Published-image boot after rebase, native account creation in that deployment, real tty3 administrator login, post-switch partition equality and rollback were not reached. The UART fix has regression coverage but no VM rerun. The owner classic PAT was not provisioned or tried; CI used its temporary built-in token.

- Both ISO files were identified from official metadata, not downloaded, booted or installed. Their real installed image version/account UI and selected-drive/EFI behavior require the installer rehearsal. The CI starting disk comes directly from the pinned upstream image.
- This one-file-disk switch comparison is not the protected-Windows two-disk installer/rebase/rollback/undo audit. Physical SSD fitting, firmware menus, Windows/UEFI helper trials, media/novice walkthrough and safety/followability council remain open.
- No RTX renderer, laptop display/audio/network, German physical keyboard, physical recovery TTY, power button/lid, battery, hardware GRUB interaction, encryption or offline rescue-media qualification. Minecraft and Prism are absent from the image and outside this brief.
- The deferred activation graph/transient effective-command audit remains deferred exactly as in package 03. Static/generated inspection and live manager state checks remain mandatory.
- `mod/` was unchanged. The brief prohibits local builds and excludes Minecraft; no Gradle command or daemon was started. The local general Gradle verification instruction was superseded by this OS-only brief's explicit machine/scope constraints, as in package 03.

## JUDGMENT-CALL

- **Daily UID 1001; recovery administrator UID 1000.** Preserve the installer's first ordinary UID and avoid moving the administrator's home/files. Rejected requiring installer UID overrides or renumbering an already-created admin merely to preserve package 03's provisional daily UID 1000. No deployed owner image exists to migrate. Changing this after personal use requires account/home ownership migration plus audit/fixture updates.
- **Keyless signature with public transparency metadata.** This satisfies signing without a long-lived secret. Rekor exposes workflow/repository identity and digest, while the GHCR package and layers stay private. Rejected storing a signing key/PAT and relying on digest alone when keyless signing is available. Future releases from `main` will have a different expected workflow certificate identity; retain the recorded identity for this digest.
- **Read-only classic PAT for the laptop.** GitHub currently does not support fine-grained PATs for GHCR. Document only `read:packages`, expiry and root-only storage, with no write/delete/repo scopes. This scope is not restricted to this one package. No owner PAT was created or handled. Moving to fine-grained credentials depends on GitHub support or a separately reviewed distribution mechanism.
- **Keep current-live installer route.** Identify the requested legacy ISO and its official hash without replacing the newer own-SSD guide's live installer. Both hashes are recorded; actual ISO-to-pinned-stock equivalence remains a release gate. Rejected silently releasing an untested legacy installer path or claiming the bootc-image-builder stand-in is an ISO walkthrough.

## PLAN-GAP

- Fine-grained private-pull token requirement is not implementable with GitHub's current supported registry authentication. [Official GHCR docs](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).
- The brief's frozen legacy-ISO item conflicts with the current-live route and its explicit prohibition on substitution. This package records both official checksum sources and keeps actual installer selection/qualification gated.
- Package 03's UID 1000 assumption also existed in runtime audit bus/generator paths and the exact user-manager allowlist; updating user creation alone would audit the wrong account. Those dependencies and a regression assertion are updated together.
- Package 03's report records builder password-hash logging. Password and hash masking now happen before invoking the builder. The two initial full dispatches were canceled before disk preparation while these preflight/review fixes were made; they still count against the full-run cap.
- Stock Bazzite's hardware-setup service runs before user sessions and normally reboots after changing kernel arguments. The harness now permits one orderly pre-login reset, records its console/QMP evidence, rejects panic or loop evidence, and requires completed hardware setup before testing the switch.
- `bootc status --json` can emit terminal lock-wait progress alongside kernel UART messages. State is now captured to a file and transferred through the existing SHA-256-checked base64 protocol; no terminal output is accepted as deployment JSON.
- Bootc preserves locally modified passwd/group files. Build-time user creation alone does not ensure a new account appears after rebase; the native sysusers declaration fixes that documented issue. [Bootc account guidance](https://bootc.dev/bootc/building/bootc-users-and-groups.7.html).

- Reboot must keep reading the UART while waiting for QEMU; the final attempt exposed a transport flaw and real shutdown/virtio warnings. The bounded drain is corrected and regression-tested without extending the deadline, but it is not a proven resolution of the VM failure.

## Open questions

A new large-run allowance is required to qualify the corrected harness through boot/recovery/rollback. A guarded switch-only retry can reuse run 39796347427's unchanged runtime image; none was dispatched after the cap. The owner must review the UID, classic-token and public-transparency-metadata judgment calls before merge. The separate installer package must establish the actual live ISO's installed version, account screen, protected-disk write audit and novice workflow. No physical installation is authorized by this PR.

## 06b: Switch qualification (2026-10-22)

### Done

- Executed brief 06b on `pkg/06-image-release`, testing harness source **`cc341991bb4524dc37154f80f4256d1aff0a3b24`**. Used **one of two** authorized full runs, in switch-only reuse mode. The runtime payload still matches signed image source `01aae1e38ec11356677f526692783c14b89a1d4d`; no image was rebuilt, republished or modified.
- **Stopped qualification on a product failure, as the brief requires.** In the switched deployment, the existing policy test found `/home/linuxbrew/.linuxbrew/bin/brew` executable by daily user `ares`. No workaround, permission change, test change or second full run was attempted. PR #10 stays draft; §6 cannot honestly be marked qualified.
- `os/manifest/ci/06b/`, report logs/artifacts/screenshots: retain the actual preflight and failed switch evidence. `os/manifest/release.json`, `os/README.md`, the evidence index and `docs/INSTALL.md` now identify the current blocker and distinguish verified boot/accounts from unverified recovery/rollback. Other installation gates stay open.

### Verified

Commands dispatched:

```text
gh workflow run os-image.yml --ref pkg/06-image-release -f checks_only=true
gh workflow run os-image.yml --ref pkg/06-image-release -f checks_only=false -f switch_from_run=39796347427
```

- **Checks-only [39810919917](https://github.com/carlsenares/AresOS/actions/runs/39810919917): success.** Printed **`Ran 52 tests in 0.879s`**, **`OK`**, **`Live hosted system manager passed: 437 unit files, 465 unit names`**, and **`Existing release package is private`**. Python compilation, Bash syntax checks, official release-input resolution and upstream signature verification passed. This includes both UART-drain regressions and the real native-sysusers regression; no image or VM was built. [Output](logs/06b-preflight.txt), [inputs](../../os/manifest/ci/06b/preflight/).
- **Switch-only [39811047831](https://github.com/carlsenares/AresOS/actions/runs/39811047831): failure.** The reuse guard printed **`Qualified release source 01aae1e38ec11356677f526692783c14b89a1d4d; runtime payload unchanged; testing ghcr.io/carlsenares/aresos@sha256:25de68a75ef4534f903f7dd2d8ce1eb9e86c1b2d165c2631152fb1f1c711f91a`**. The original image job was skipped. Runner tooling and an unmodified-upstream stock file disk were constructed successfully. [Workflow output](logs/06b-switch-1-workflow.txt), [failure](logs/06b-switch-1-failure.txt), [guest evidence](../../os/manifest/ci/06b/switch-1/).

| Check in the switch-only guest | Observed result |
|---|---|
| Stock first-boot hardware setup | One orderly pre-login reboot, then completed hardware-setup service |
| Recovery administrator | UID 1000, wheel; real serial password login and password-authenticated sudo on stock and AresOS |
| Private release | Stock cosign verification and exact-digest pull/staging passed |
| Reboot after staging | Passed within the unchanged 180-second bound; console ends `reboot: machine restart`; QMP records `guest=true, reason=guest-reset` |
| Actually booted deployment | Exact published `25de…f91a` reference and image digest, no staged deployment |
| Retained stock | Pinned checksum `aa669eff4ea5c1f97c6c816c8d5d2abb5314e9afa3b966c0100e3e65f8040c71` still present as rollback target |
| Native daily account/session | greetd active, graphical target, labwc and foot running as `ares`; UID/GID 1001, locked password, no wheel/sudo |
| Before/after-switch disk | Same `vda` size and all four partitions' starts, sizes, PARTUUIDs, partition types and filesystem UUIDs |
| Existing updater policy check | **Failed** at Homebrew executable access, before the full live updater audit |
| Real tty3 administrator login and rollback | Not reached |

The decisive guest trace is [aresos-policy.txt](../../os/manifest/ci/06b/switch-1/aresos-policy.txt):

```text
++ command -v brew
+ path=/home/linuxbrew/.linuxbrew/bin/brew
+ [[ -z /home/linuxbrew/.linuxbrew/bin/brew ]]
+ runuser -u ares -- test '!' -x /home/linuxbrew/.linuxbrew/bin/brew
ARESOS_CMD_DONE:1
```

The harness then printed **`AssertionError: Guest command failed: aresos-policy, exit 1`**. It did not report a UART timeout, failed boot or account error. The independent serial administrator had already authenticated in the switched deployment. `aresos-qmp.json` ends with cleanup's host-signal shutdown after the policy failure; it is not rollback or guest-shutdown proof. There is no switch `result.json` and no rollback evidence.

Both new screenshots were visually inspected: [stock Bazzite login](screenshots/06b-stock-bazzite.png) and [switched AresOS terminal at the policy failure](screenshots/06b-aresos-policy-failure.png). The latter shows the AresOS terminal/recovery hints and `aresos ~ $` prompt. It is not a tty3 authentication screenshot.

The preflight and switch evidence ZIP hashes match GitHub's SHA-256 metadata. Original workflow logs are also archived with a computed download hash; GitHub supplies no hash for that logs endpoint. [Archives and hashes](artifacts/README.md), [06b run/job metadata and measurements](ci-06b.json). Expanded text copies normalize trailing whitespace/line endings. The archive contents and retained logs were scanned for GitHub token forms and unmasked SHA-512 password hashes; no matches or forbidden disk/credential/builder-configuration/journal files were found.

Switch measurements: **53,141,831,680** virtual disk bytes; **10,664,783,872** allocated disk bytes; sampled peak runner use **70,460,051,456** bytes and minimum free **6,410,326,016** bytes on a **76,887,154,688**-byte filesystem. The switch metrics window is **1,927.844 seconds (32m07.844s)**; sampling remains every ten seconds. The compressed switch artifact is **3,368,702 bytes**; preflight artifact **31,046 bytes**; workflow-log ZIP **77,601 bytes**. These are measured evidence/disk figures, not billed quota totals. No paid feature or billing setting changed.

Final job metadata reports **32m22s** for the failed switch job and **22s** for checks-only: **32m44s total**. Rounding each started job up separately gives **34 minutes**, a conservative quota proxy rather than an invoice. The API initially lagged with an in-progress job despite a completed failed run; the retained metadata now contains its final failure and completion timestamp. No second full run was spent.

Local PowerShell file verification printed **`Parsed 17 JSON files; checked 56 local links and 6 archive hashes; booted digest and partition evidence match; runtime and harness unchanged`**. `git diff --exit-code 01aae1e38ec11356677f526692783c14b89a1d4d HEAD -- <runtime payload paths>` and the worktree comparison of runtime/harness paths passed with no output; `git diff --cached --check` also passed with no output. These are file/Git checks, not local builds. No local build, package installation, VM, Minecraft or Gradle command ran; no Gradle daemon was started. All builds/guest commands above ran on disposable hosted CI.

### Not verified

- **Blocking:** Homebrew is executable by the daily account after switching. The full normal updater audit/mask sweep, sleep checks, real tty3 administrator login/password sudo, rollback command, stock reboot after rollback and after-rollback partition comparison were not reached. The successful before/after-switch comparison does not qualify rollback or Windows-disk protection.
- No Homebrew install/update was executed. The failure proves executable access, not the complete write/ownership behavior or how the executable's permissions arose. No path `stat`, symlink or persistent-home ownership inventory was captured before stopping.
- The original ISO, protected-Windows two-disk, hardware, German keyboard, media, helper and followability gates remain open. No owner PAT or physical installation was tried.

### JUDGMENT-CALL

None added to product behavior. The stop is the brief's explicit product-failure rule, not a new permission requirement. Existing owner decisions above remain pending. The unused second run was not spent repeating a known product failure.

### PLAN-GAP

The two fresh image boots did not establish updater restrictions after switching from stock. `os/build.sh` changes executable permissions during the image build, while the installed system retains home/`/var` state across switches. The surviving stock Homebrew tree is a plausible cause, inferred from that code and the post-switch trace, **not a proven permission/ownership diagnosis**. A separately scoped product fix must account for existing state and preserve the current failing assertion, then qualify a newly built release if runtime source changes. A test-only retry cannot qualify a changed product under the old digest.

### Open questions

Product follow-up is required for Homebrew access after switching. Tty3 recovery and rollback must then be qualified within a new approved scope/budget. Brief 06b's green switch/rollback, qualified §6 and ready-for-review acceptance are **not met**; PR #10 remains draft and unmerged. No further qualification run was started after discovering the product failure.

## 06c: inherited Homebrew qualification (2026-10-22)

### Done

- `os/config/usr/lib/tmpfiles.d/aresos-inherited-homebrew.conf`: apply a named deny ACL for reserved daily UID 1001 to the inherited `/var/home/linuxbrew` directory during normal boot tmpfiles setup. Denying traversal also prevents reading the brew script through an interpreter. No Homebrew file is removed, recursively chmodded or chowned. Existing owner and ACL entries are preserved; a missing installation is not created.
- `os/build.sh`, `os/config/etc/profile.d/aresos.sh`, `aresos-session`: skip upstream Bash Homebrew initialization/completion for UID 1001, reset the daily login/session PATH to system directories and clear inherited Homebrew prefix variables. Preserve initialization for the stock owner and all existing system/user setup/update/upgrade masks.
- `os/tests/test_inherited_homebrew.py`: exercise the real tmpfiles rule with native Linux ACLs and separate UIDs. Verify denial of both execution and interpreter reads, unchanged owner/content, owner execution/write access, idempotence, preservation of an existing restrictive ACL/mask and absence handling. The fixture uses root-owned ancestors, matching the installed layout. Numeric UID 1001 avoids name resolution through the host's ACL library when testing an offline root.
- `os/tests/inherited-homebrew.sh`, `os/ci/switch_vm.py`: require the actual inherited Homebrew installation, execute `brew --version` as its stock owner before the switch, in AresOS and after rollback, and compare the script hash across boots. In AresOS, reject direct/interpreter access and prefix writes as `ares`; check both the real labwc environment and a fresh daily login shell for Homebrew PATH leakage. Keep the original policy assertion, live updater audit, real tty3 password/sudo, partition comparison and exact retained-stock checksum checks. The new script is included in both workflow Bash syntax sweeps.
- `os/ci/tty_password.py`, `os/tests/test_tty_password.py`: repair a harness observation race found in full run 1. Reopen the TTY on each password-prompt observation and retry only transient `EIO` until the existing 30-second deadline. Require a real `login` process and disabled echo. Six regressions use a native PTY, inject the observed hangup, verify reopen/close behavior, and keep persistent hangup, visible echo, absent login, unexpected errors and query failures blocking. No image payload changed for this repair.
- `docs/INSTALL.md` §6, `os/manifest/release.json`, `os/README.md`: record the new qualified private digest and tested account/trust/switch/recovery/rollback recipe. Close only the image handoff gate; keep all installer, two-disk, hardware and followability gates open. Preserve final evidence under `os/manifest/ci/06c/switch-full-2/` and the adjacent review archives/screenshots. Both authorized full runs were used; no third dispatch or second image publication occurred.

### Verified

Qualification passed on full run 2. The runtime source is `5578ab21b880091f26bfdc2eda22dd4f304a602b`; the resumed harness source is `1d4a7dec12430b67ff0a53f38ba280c8ae8f7414`. Later commits contain documentation/evidence only. The image was built and published once; the retry reused its exact digest.

Commands dispatched so far:

```text
gh workflow run os-image.yml --ref pkg/06-image-release -f checks_only=true
  # Three dispatches: 39818147832, 39818274310, 39818451208
gh workflow run os-image.yml --ref pkg/06-image-release -f checks_only=false
  # First full 06c run: 39818554327
gh workflow run os-image.yml --ref pkg/06-image-release -f checks_only=true
  # Resumed TTY regression preflight: 39832900483
gh workflow run os-image.yml --ref pkg/06-image-release -f checks_only=false -f switch_from_run=39818554327
  # Second and final full 06c run: 39833127717 (reuse; no image rebuild)
```

- **Checks-only [39818147832](https://github.com/carlsenares/AresOS/actions/runs/39818147832): failed**, printing `Ran 55 tests in 1.007s` and `FAILED (errors=2)`. Native tmpfiles rejected the fixture's non-root-owned ancestry with exit 73. Corrected fixture ancestry rather than changing the assertions. [Log](logs/06c-preflight-failed-1-workflow.txt).
- **Checks-only [39818274310](https://github.com/carlsenares/AresOS/actions/runs/39818274310): failed**, printing `Ran 55 tests in 4.150s` and `FAILED (failures=1, errors=1)`. The named `ares` ACL was not installed in the offline fixture: direct execution remained possible and the named entry was absent. Bound the product rule to the already-reserved numeric UID 1001, preserving every assertion. [Log](logs/06c-preflight-failed-2-workflow.txt).
- **Checks-only [39818451208](https://github.com/carlsenares/AresOS/actions/runs/39818451208): success**, printing `Ran 55 tests in 1.298s`, `OK`, `Live hosted system manager passed: 437 unit files, 464 unit names` and `Existing release package is private`. Python/Bash syntax checks, release-input resolution and pinned upstream signature verification passed. All three new ACL regressions ran without skips. [Log](logs/06c-preflight-workflow.txt), [inputs](../../os/manifest/ci/06c/preflight/).
- **Full [39818554327](https://github.com/carlsenares/AresOS/actions/runs/39818554327), image job: success**, source **`5578ab21b880091f26bfdc2eda22dd4f304a602b`**. Printed `Ran 55 tests in 0.973s`, `OK` and `Updater audit passed: 814 system/user units inspected`. Exact added RPM content and unchanged kernel/NVIDIA checks passed, as did release isolation (`Release excludes CI service and credentials; both passwords locked`). Both new fresh VMs passed the unchanged policy, static/generated canaries, recovery, power and offline-journal checks. The dependent switch job failed at the TTY observation described below. [Image evidence](../../os/manifest/ci/06c/image-full-1/).

**Full run 1 switch result: harness failure.** After the stock pre-login reboot, serial administrator login/sudo, signature verification, switch and reboot into the new `362a…c402` digest all passed. The switched policy printed `Updater audit passed: 1084 system/user units inspected` and `ARESOS_GUEST_CHECKS_PASSED`. The actual inherited tree retained owner UID 1000 and acquired only `user:1001:---` on its parent; owner `brew --version` printed `Homebrew 7.0.9`. Direct execution and interpreter reads as `ares` both failed with permission denied, writes were denied, the daily login shell could not find brew, and the labwc PATH was `/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin`. Before/after-switch partitions matched. No other inherited mutation path failed the policy. [Policy](../../os/manifest/ci/06c/switch-full-1/aresos-policy.txt), [Homebrew checks](../../os/manifest/ci/06c/switch-full-1/aresos-inherited-homebrew.txt).

The failure was `termios.error: (5, 'Input/output error')` at `tcgetattr(fd)` in `tty-password-ready`, after QMP typed the recovery username on real tty3. The observer had opened the TTY once before polling. The installed util-linux version is 2.41.5; its [login source](https://github.com/util-linux/util-linux/blob/v2.41.5/login-utils/login.c) calls `vhangup()` and reopens the TTY during takeover. A revoked observation descriptor explains the exact `EIO`; it is a harness diagnosis inferred from the trace and matching upstream code, not an observed product authentication rejection. Reopening per observation is covered by the new regression. No password was typed after that failed readiness check, no authentication screenshot was exported, and no rollback was reached. [Failure](../../os/manifest/ci/06c/switch-full-1/tty-password-ready.txt), [failed workflow output](logs/06c-full-1-failed.txt), [stock screenshot](screenshots/06c-full-1-stock-bazzite.png), [AresOS session screenshot](screenshots/06c-full-1-aresos-labwc.png). Both screenshots were visually inspected.

**Resumed checks-only [39832900483](https://github.com/carlsenares/AresOS/actions/runs/39832900483): success.** Printed `Ran 61 tests in 2.244s`, `OK`, `Live hosted system manager passed: 439 unit files, 474 unit names` and `Existing release package is private`. All six new TTY tests and the three native Homebrew ACL regressions ran without skips. Python compilation, Bash syntax, release-input resolution and upstream signature verification also passed. [Output](logs/06c-tty-preflight-workflow.txt), [inputs](../../os/manifest/ci/06c/tty-preflight/).

**Full run 2 [39833127717](https://github.com/carlsenares/AresOS/actions/runs/39833127717): success**, switch-only reuse of successful image job 39818554327. The reuse guard printed `Qualified release source 5578ab21b880091f26bfdc2eda22dd4f304a602b; runtime payload unchanged; testing ghcr.io/carlsenares/aresos@sha256:362af9b7d2a5573363d2cc441505dd076603d1d96c1b5c01af55589db2b6c402`. The image job was skipped. The guest test printed **`Published-image switch, real recovery-admin TTY login, unchanged partitions and stock rollback passed`**. [Workflow output](logs/06c-full-2-workflow.txt), [passing result](../../os/manifest/ci/06c/switch-full-2/result.json).

| Final switch rehearsal | Observed result |
|---|---|
| Stock initialization | One orderly pre-login reset; stock hardware setup completed |
| Administrator on all three boots | `ares-recovery`, UID 1000/wheel; real serial password login and password-authenticated sudo |
| Private release | Stock cosign verification, exact-digest pull/staging and boot into `362a…c402` passed |
| Switched session/account | labwc/foot, locked UID/GID 1001, no wheel/sudo; full policy printed `Updater audit passed: 1084 system/user units inspected` and `ARESOS_GUEST_CHECKS_PASSED` |
| Inherited Homebrew in AresOS | ACL `user:1001:---`; daily execution, interpreter read and write denied; brew absent from daily login/session PATH; original owner runs Homebrew 7.0.9 and prefix remains writable |
| Real tty3 recovery | `TTY3_LOGIN_PASSWORD_ECHO_DISABLED`; active `User=1000`, `Name=ares-recovery`, `TTY=tty3`, `Type=tty`; `RECOVERY_ADMIN_TTY3_LOGIN_AND_PASSWORD_SUDO_PASSED` |
| Partition equality | Attached `vda` size and every partition start, size, PARTUUID, type and filesystem UUID identical on stock, AresOS and rollback |
| Stock rollback | Exact original checksum `aa669eff4ea5c1f97c6c816c8d5d2abb5314e9afa3b966c0100e3e65f8040c71`; upstream digest restored; display manager active, no AresOS session binary or `ares` account |
| Homebrew after rollback | Original UID 1000 owner still executes Homebrew 7.0.9; prefix writable; UID 1001 deny entry remains reversible |

The actual inherited brew script SHA-256 is **`c9a27029eb72dab04f4595041f7670bb03b4cb467297abba817883afb23e0bf3`** at all three stages. No install/update was invoked. No additional inherited mutation path failed the unchanged policy, so no further manager neutralization was needed. Both deployment reboots completed within the unchanged 180-second bound and QMP recorded `guest=true, reason=guest-reset`. The final QMP record on rolled-back stock is cleanup's host-signal termination after all assertions, not an additional shutdown test. [TTY session](../../os/manifest/ci/06c/switch-full-2/tty-admin-session.txt), [TTY sudo](../../os/manifest/ci/06c/switch-full-2/tty-admin-login.txt), [rollback Homebrew](../../os/manifest/ci/06c/switch-full-2/rollback-inherited-homebrew.txt).

All five final screenshots were visually inspected: [stock login](screenshots/06c-full-2-stock-bazzite.png), [AresOS terminal](screenshots/06c-full-2-aresos-labwc.png), [authenticated tty3 administrator and sudo](screenshots/06c-full-2-recovery-admin-tty3.png), [rollback frame](screenshots/06c-full-2-rollback-bazzite.png), [cleanup frame](screenshots/06c-full-2-failure-rollback.png). The tty3 frame contains the expected inherited Bazzite banner and a Flatpak permission-denied profile message; login and password sudo succeeded. Both rollback captures are black (one with a cursor); they are **not visual proof of the stock graphical login screen**. The cleanup filename starts with `failure-` because `Guest.close()` captures any still-running guest, including the successful final stage. Actual booted checksum, active display manager, authenticated serial administrator and working owner Homebrew establish stock boot. Graphical rendering readiness after rollback was not asserted. Initial stock and AresOS state screenshots are rendered; no framebuffer was edited or substituted.

Both `bootc container lint` invocations printed **`Checks passed: 11`**, **`Checks skipped: 1`**, **`Warnings: 3`**. The retained warnings cover runtime-directory residue, the DNF log and `/var` tmpfiles coverage; no lint setting or test was weakened.

| Fresh-image check | VM 1 | VM 2 |
|---|---|---|
| Daily account/session | Locked UID/GID 1001, no sudo, labwc/foot | Same |
| Normal live updater audit | 1,084 units; `ARESOS_GUEST_CHECKS_PASSED` | Same |
| Generated/static updater canaries | Both rejected; audit exit 1; `mode=static-strict` | Same |
| Recovery shortcut/getty/PAM | Exit 0, wrong-password rejection/correct-password acceptance | Same |
| Power events and clean shutdown | Passed | Passed |
| Offline logind journal | Passed, boot `b1700e75317b40a688c7f584926d8a82` | Passed, boot `c7268f54f1ce48ec8eedc4c483ac0471` |

Neither offline-journal pass used the hardware contingency. Both real journals were extracted with the read-only userspace Btrfs fallback, verified, and checked for the expected boot's power-key event, poweroff request and orderly logind stop. The recovery credentials here are the overlay's VM-only root account; this table does not substitute for the switched recovery-administrator tty3 test. Both labwc screenshots were inspected ([VM 1](screenshots/06c-image-full-1-vm-pass-1-aresos-labwc.png), [VM 2](screenshots/06c-image-full-1-vm-pass-2-aresos-labwc.png)). The fresh [VM 1 tty3 screenshot](screenshots/06c-image-full-1-vm-pass-1-aresos-tty3-getty.png) shows the login prompt; [VM 2's early capture](screenshots/06c-image-full-1-vm-pass-2-aresos-tty3-getty.png) shows only the header during drawing, so it is not visual proof of a rendered prompt. Its independent manager/device/PAM assertions passed.

New release: **`ghcr.io/carlsenares/aresos@sha256:362af9b7d2a5573363d2cc441505dd076603d1d96c1b5c01af55589db2b6c402`**, tag **`06-5578ab21b880091f26bfdc2eda22dd4f304a602b`**, private, signed and verified with the same GitHub workflow identity. Local release OCI manifest: `sha256:c0cb55a3920717867c9ba88f757d9af67d2f59931e22a1d4d93cc2aa1ee2815c`; local test-overlay manifest: `sha256:479c8cf30d102880da52105a583258aa23d511ddccdfcf53d778bdeae075dc06`. Local hashes differ from the registry manifest representation; the **GHCR digest** is the handoff. Local checks recomputed all three raw manifest hashes, checked source/revision labels, actual private package visibility and the exact RPM lock. Kernel/NVIDIA remain **7.2.9-ogc3.1.fc44 / 615.78.08**; this is package preservation, not a hardware rendering test.

The successful image job took **47m01s** according to completed job metadata. Image metrics sampled peak runner use **71,909,232,640 bytes**, minimum free **4,961,144,832 bytes**, VM disk **31,666,995,200 virtual / 9,679,044,608 allocated bytes**, and an elapsed metrics window of **2,810.7728338241577 seconds**. The compressed image artifact is **3,160,132 bytes** and matches GitHub's artifact SHA-256. Full run 1's failed switch job took **31m02s**, sampled peak use **69,889,753,088 bytes**, minimum free **6,980,624,384 bytes**, and disk **53,141,831,680 virtual / 10,741,350,400 allocated bytes**. Its compressed switch artifact is **3,314,878 bytes**, also hash-verified.

Full run 2's successful switch job took **34m03s**. Its metrics window is **2,023.5600607395172 seconds**, sampled peak use **70,334,205,952 bytes**, minimum free **6,536,171,520 bytes**, disk **53,141,831,680 virtual / 10,850,902,016 allocated bytes**, on a **76,887,154,688-byte** runner filesystem. Its compressed switch artifact is **3,647,901 bytes**, hash-verified. Sampling remains every ten seconds. [Metrics](../../os/manifest/ci/06c/switch-full-2/metrics.json).

**06c budget: 2/2 full runs used**, plus four checks-only dispatches (two failed, two successful). Completed non-skipped jobs total **6,795 seconds = 113m15s**. Rounding each started job up separately gives **119 minutes**, a conservative quota proxy rather than a billed total. The two failed preflights took 10s/12s, successful preflights 23s/24s. [Final run/job/step metadata](ci-06c.json). The brief's approximately 1,100 already-used monthly minutes is a supplied input, not a new billing measurement. No paid feature or billing setting changed.

Original pre-pause archives were preserved. All evidence ZIPs match their adjacent GitHub artifact metadata; workflow-log ZIP hashes are computed locally because that endpoint supplies none. [Archive index and hashes](artifacts/README.md). Retained archives/logs were scanned for unmasked SHA-512 password hashes and GitHub token forms, and for forbidden disks, credentials, builder configurations and binary journals; no matches were found. Raw authentication transcripts remain excluded.

Local Windows verification, using the existing Java cache at `C:\Users\pab\.jdks\openjdk-25`:

```text
cd mod
gradlew.bat --no-daemon build runClientGameTest  # first invocation
gradlew.bat --no-daemon build runClientGameTest  # second invocation
gradlew.bat --stop
```

Both full invocations succeeded: first **`BUILD SUCCESSFUL in 7m 37s`**, **`19 actionable tasks: 18 executed, 1 up-to-date`**; second **`BUILD SUCCESSFUL in 7m 6s`**, **`19 actionable tasks: 4 executed, 15 up-to-date`**. The client suite ran on both invocations, including deterministic multi-world seed checks and actual rejoin/respawn. Unit XML records **45 tests, zero failures/errors/skips**; the second invocation reused the up-to-date unit task. [First output](logs/mod-pass-1.txt), [second output](logs/mod-pass-2.txt), [counts](mod-test-results.json). The first output includes Gradle deprecation notices; both clients print unauthenticated Fabric-dev profile/Realms HTTP 401 messages without failing the tests. No mod source or test changed.

Representative Live/Build screenshots from both invocations were saved here and visually inspected: [first Live](screenshots/06c-mod-pass-1-0004_09-live-hotbar.png), [first Build](screenshots/06c-mod-pass-1-0005_09-build-hotbar.png), [second Live](screenshots/06c-mod-pass-2-0004_09-live-hotbar.png), [second Build](screenshots/06c-mod-pass-2-0005_09-build-hotbar.png). Only test-generated PNG changes in the earlier packages' review directories were restored/removed after retaining these copies. `gradlew.bat --stop` printed **`No Gradle daemons are running.`** No system software was installed and the owner's Minecraft/Lunar folders were not used.

Local `python -m py_compile os/ci/switch_vm.py os/tests/test_inherited_homebrew.py`, `bash -n os/build.sh`, `bash -n os/tests/inherited-homebrew.sh` and `git diff --check` passed without error output. Generated Python caches were removed. The evidence collector initially resolved its destination one directory above the worktree; only its newly created release-input files were content/hash-verified and removed, along with empty collector-created directories. Its corrected root now requires this worktree's `AGENTS.md` and `.git` before writing. Retained evidence is inside this worktree.

Final resumed local checks: `python -m py_compile os/ci/tty_password.py os/ci/switch_vm.py os/tests/test_tty_password.py` and `git diff --check` passed. `python -X utf8 .work/verify_06c.py --final` parsed **83 JSON files**, checked **96 local document links and 17 archive hashes**, scanned retained logs/archives for secrets/forbidden files, checked actual booted/retained digests and checksum, absence of staged deployments, all three partition snapshots, tty3 evidence and owner brew hashes, and proved the runtime payload unchanged from `5578ab2`. It printed the [passing file-verification result](logs/06c-final-file-verification.txt). The local checker initially encountered Windows ANSI decoding; its explicit UTF-8 rerun passed. These are file checks, not extra guest tests. Final `mod/gradlew.bat --stop`, using the existing Java 25 cache, printed **`No Gradle daemons are running.`** [Output](logs/06c-final-gradle-stop.txt). No other Gradle version ran. Generated Python caches were removed; only ignored worktree-local evidence helpers remain.

### Not verified

- Physical installer/ISO-to-pinned-stock equivalence, protected-Windows two-disk write audit, GPU/hardware, physical German keyboard/TTY, media, helper and novice-followability gates remain open independently of this VM qualification. No owner PAT or physical installation was tried. CI used its temporary built-in token.
- Both rollback screenshots are black frames. Stock boot is verified by actual deployment/account/display-manager/Homebrew checks; graphical rendering readiness and a rendered post-rollback login screenshot were not obtained. No third full run was spent for a later capture.
- No Homebrew installation/update, exhaustive arbitrary-program confinement or future inherited owner data was tested. This tests the pinned stock image's inherited paths and the existing updater policy. The deferred activation graph remains deferred as recorded in package 03.

### JUDGMENT-CALL

The integrator pre-decided reversible inherited-manager neutralization. The implementation chooses a single named UID deny ACL rather than recursive ownership/mode changes or deletion. It remains on shared `/var` after rollback but does not deny the original UID 1000 owner. To remove it on stock, an administrator runs `sudo setfacl -x u:1001 /var/home/linuxbrew`; AresOS reapplies it on its next boot. A later policy change removes the image rule and that one ACL entry. Reserving UID 1001 remains the existing account decision; another stock account assigned that UID would need the entry removed to use this prefix. No additional owner decision is introduced. [Native tmpfiles ACL semantics](https://www.freedesktop.org/software/systemd/man/latest/tmpfiles.d.html).

### PLAN-GAP

The build-only Homebrew restriction did not cover retained `/var/home` state, as 06b demonstrated. This follow-up adds boot-time policy and actual switched-state/rollback evidence. The TTY observer also held a descriptor across login's hangup; that transport flaw is corrected and regression-tested without changing product authentication or its required assertions. Other inherited mutation checks stayed blocking and passed in both switched-state runs.

### Open questions

06c's acceptance is met and PR #10 is ready for independent review. Existing owner review items (UID allocation, classic GHCR token and public keyless-signing metadata) remain for the integrator, along with the separate physical-install release gates. Both full runs are used; no further dispatch, merge or physical installation is authorized by this report.

## 06d: review fixes (2026-10-22)

Status: **ACCEPTANCE NOT MET — both full-run allowances consumed (one failed, one cancelled), no green 06d VM result**. The code/doc fixes and regression checks are implemented, but the rendered rollback screenshot and successful revised guest sequence are missing. This section supersedes 06c's recipe and graphical-evidence claims; earlier sections remain historical. No mod source changed, and **no Gradle command, mod build, Minecraft client, local OS build or local VM ran in 06d**. No Gradle daemon was started, so no stop command was run. Physical installation remains gated and PR #10 stays open.

### Done

| Finding | Fix | Regression / evidence |
|---|---|---|
| 1. Reboot bypasses checkpoint | INSTALL §6 separates each fail-fast transaction, owner-readable status inspection and reboot. `switch_vm.py` independently exports and checks staged reference/digest or queued rollback reference/digest/checksum before reboot. | Actual guide blocks are executed with injected transaction exit 42; reboot is forbidden in those blocks. Transaction inspection rejects missing/wrong identity and queue state. Revised guest ordering has **not** completed successfully in 06d. |
| 2. GRUB boot is not persistent recovery | `release/default-stock.sh` and the identical guide block check booted stock against the owner's recorded checksum and pinned base digest/reference, resolve its current index, then use `ostree admin set-default`. Guide requires another reboot without selection and covers already-booted stock. | Index 0/1 fixtures, wrong checksum/digest/reference, staged/ambiguous deployment and failed transaction regressions. **GRUB recovery promotion remains UNTESTED and explicitly an open release gate.** CI exercises the already-default case after normal rollback, not a one-time boot with AresOS still first. |
| 3. Negated assertions silently pass | Seven original assertion sites become explicit `if …; then echo …; exit 1; fi` branches, listed below. Stock and rollback share `release/stock-session.sh`. | Real shell guards run with prohibited conditions injected; nonzero exit and specific reason required. Static regression audits shell scripts, extensionless shell config, Containerfiles/service config and Python string snippets/fragments throughout `os/`, including test fixtures except the deliberately invalid static-test inputs. |
| 4. Missing rollback graphics — **still open** | `ci/greeter_probe.py` now checks the pinned Plasma Login Manager's actual `plasma-login-greeter` executable under `plasmalogin`, graphical environment and positive active VT, then `ci/greeter.py` bounds framebuffer drawing to 120 seconds. A harmless Space wakes the theme's idle clock view. | Four framebuffer regressions plus six observer/inventory regressions cover identity, `/proc` parsing, replacement, service-only false positives, wrong VT and the actual pinned manager. The initial SDDM assumption failed and the replacement was corrected after the second dispatch. **No rendered rollback screenshot was obtained.** |
| 5. Recovery admin left logged in | Guide requires exiting root, invalidating sudo, logging out of `ares-recovery`, confirming tty3's login prompt, then returning to tty1. Harness types `sudo -k`/`exit`, requires tty3 getty and no UID 1000 tty3 process, saves the logged-out screen, then returns to tty1. | 06c's real tty3 login/sudo evidence remains historical; the new logout/getty sequence is **not guest-qualified in 06d**. |
| 6. Stale docs | `OS-BASE.md` and `os/README.md` now describe successful 06c recovery/rollback and 06d's stricter checks, preserving ISO, protected-Windows, hardware and GRUB release gates. | Documentation/source comparison and final file checks. |

Rewritten negative assertions (complete audit inventory):

1. `release/switch.sh`: pre-existing `ares` name, including a different UID while 1001 is free.
2. Original `switch_vm.py` stock snippet: unexpected `ares` account; now shared `release/stock-session.sh`.
3. Original `switch_vm.py` rollback snippet: unexpected `ares` account; same shared script.
4. `tests/guest.sh`: `ares` in wheel.
5. `tests/guest.sh`: any active SDDM/GDM/LightDM manager (all three injected separately).
6. `tests/guest.sh`: running `kwin_wayland`, `plasmashell`, `gnome-shell`, `powerdevil` or `gsd-power` (each injected separately).
7. `tests/inherited-homebrew.sh`: `brew` discoverable by a fresh daily login even on a PATH without the string `linuxbrew`.

No other bare-negation or `cmd && false` assertion was found. `test ! …` and `[[ ! … ]]` are tests whose actual status is checked, unlike shell-level `! cmd`; they remain. Optional executable lookups/diagnostic output use explicit tolerated failures, `systemctl disable … || true` is followed by enforced masks, and positive polling uses bounded loops with final failure. These are control flow rather than assertions relying on an exempt `set -e`. No corrected assertion contradicts output in the retained 06c logs, but the strengthened switched-state guards have not completed a real guest rehearsal in 06d.

The release runtime payload is unchanged from `5578ab21b880091f26bfdc2eda22dd4f304a602b`. Changed guest scripts ship only in the separate test overlay or run over the serial test transport; `os/.containerignore` excludes `ci/` and `release/`. No image rebuild/publication or digest update is needed. The handoff remains **`ghcr.io/carlsenares/aresos@sha256:362af9b7d2a5573363d2cc441505dd076603d1d96c1b5c01af55589db2b6c402`**.

### Verified

Commands dispatched:

```text
gh workflow run os-image.yml --ref pkg/06-image-release -f checks_only=true
  # 39841271340, 39841596023, 39841805145, 39843907393, 39848315296, 39849142582
gh workflow run os-image.yml --ref pkg/06-image-release -f checks_only=false -f switch_from_run=39818554327
  # full run 1: 39841946532; image job skipped, unchanged signed release reused
  # full run 2: 39848481044; final allowed full run, same image reused
```

- Checks-only [39841271340](https://github.com/carlsenares/AresOS/actions/runs/39841271340), source `5cf14b89045ca58eea1bfaf93f690765c23eb71e`: **failed**, `Ran 75 tests in 1.676s`, `FAILED (errors=3)`. All three errors were new framebuffer tests importing absent Pillow on the checks-only runner. The full VM runner already installs Pillow through its existing toolchain. Added the missing dependency only to the disposable checks runner; no test was skipped or weakened. [Log](logs/06d-preflight-1-workflow.txt).
- Checks-only [39841596023](https://github.com/carlsenares/AresOS/actions/runs/39841596023), source `cbf44a5928220f942273f70be0fbc10f8c556729`: **success**, `Ran 75 tests in 1.990s`, `OK`, `Live hosted system manager passed: 437 unit files, 477 unit names`, `Existing release package is private`; syntax, release-input and upstream signature checks passed. [Log](logs/06d-preflight-2-workflow.txt).
- Checks-only [39841805145](https://github.com/carlsenares/AresOS/actions/runs/39841805145), source `aeacffe546c5c911522e8a0ad35d02e080cbe9f5`: **success**, `Ran 76 tests in 1.900s`, `OK`, `Live hosted system manager passed: 437 unit files, 477 unit names`, `Existing release package is private`; syntax, release inputs and upstream signature passed. This includes the added actual-guide transaction regression and expanded static scan. [Log](logs/06d-preflight-3-workflow.txt), [run/job/artifact metadata](../../os/manifest/ci/06d/preflight-3/ci.json).
- Checks-only [39843907393](https://github.com/carlsenares/AresOS/actions/runs/39843907393), source `a4d1d248b88f9359528e6e4e80e8170a6ebdeda1`: **success**, `Ran 76 tests in 1.864s`, `OK`, `Live hosted system manager passed: 437 unit files, 477 unit names`. This verifies the repository-local framebuffer fixture correction. [Log](logs/06d-preflight-4-workflow.txt).
- Full run 1 [39841946532](https://github.com/carlsenares/AresOS/actions/runs/39841946532), source `aeacffe546c5c911522e8a0ad35d02e080cbe9f5`: **failed before switching**. The release reuse guard passed, the stock disk completed its normal pre-login initialization reboot, and serial administrator login/sudo, stock identity, partitions and absence of `ares` passed. The new `stock-bazzite-ready` observer exited 1 after `Stock graphical greeter never became ready`. Its [saved framebuffer](screenshots/06d-full-1-failure-stock.png), visually inspected, clearly shows the rendered stock greeter's clock/background. No release switch, policy, tty3 or rollback was reached. [Log](logs/06d-full-1-workflow.txt), [failing observer output](../../os/manifest/ci/06d/full-1/switch/stock-bazzite-ready.txt), [metadata](../../os/manifest/ci/06d/full-1/ci.json).

  This is a harness false negative, not evidence of a stock rendering failure. The initial observer combined logind metadata with an SDDM argv regex, without logging each predicate. I then replaced that with direct executable/effective-UID/environment/active-VT observation, **but retained the same incorrect SDDM assumption**. The retained [RPM inventory](../../os/manifest/ci/06c/image-full-1/packages.txt) actually contains `plasma-login-manager-6.7.5-1.fc44.x86_64` and no SDDM. Thus the original observer could not accept this rendered stock greeter, regardless of its logind metadata. This was my implementation error: I should have checked the existing inventory before the first observer and before dispatching its replacement.
- Checks-only [39848315296](https://github.com/carlsenares/AresOS/actions/runs/39848315296), source `835125a24d65a5fb6051dd2aab866a25bc903263`: **success**, `Ran 81 tests in 2.989s`, `OK`, `Live hosted system manager passed: 437 unit files, 477 unit names`, `Existing release package is private`; syntax, release inputs and signature passed. These tests still used the wrong SDDM fixture, so their green result did not qualify the actual greeter. [Log](logs/06d-preflight-5-workflow.txt), [metadata](../../os/manifest/ci/06d/preflight-5/ci.json).
- Full run 2 [39848481044](https://github.com/carlsenares/AresOS/actions/runs/39848481044), source `835125a24d65a5fb6051dd2aab866a25bc903263`: **cancelled during tool/stock-disk preparation, before guest testing**, after the actual package inventory exposed the remaining observer mismatch. `gh run cancel 39848481044` requested the cancellation; the workflow ended cancelled and retained its partial evidence. It supplies **no switch/policy/tty3/rollback evidence**. It is counted as the second full-run allowance; no third full dispatch or rerun was made. [Log](logs/06d-full-2-workflow.txt), [metadata](../../os/manifest/ci/06d/full-2/ci.json).

  The final probe is corrected against the pinned KDE 6.7.5 [daemon](https://github.com/KDE/plasma-login-manager/blob/v6.7.5/src/daemon/Greeter.cpp), [sysuser declaration](https://github.com/KDE/plasma-login-manager/blob/v6.7.5/services/plasmalogin-sysuser.conf.in), [frontend target](https://github.com/KDE/plasma-login-manager/blob/v6.7.5/src/frontend/greeter/CMakeLists.txt) and [frontend service](https://github.com/KDE/plasma-login-manager/blob/v6.7.5/src/frontend/greeter/plasma-login.service.in): `plasmalogin` owns `plasma-login-greeter`. The added inventory regression anchors the fixture to the actual pinned image. Identity and rendered-frame assertions remain strict. This correction is regression-verified only; it has **not been qualified in a VM**.
- Final checks-only [39849142582](https://github.com/carlsenares/AresOS/actions/runs/39849142582), source `5cbcfeaace2951e7f4e8fcabf480079fa1c2bd9a`: **success**, `Ran 82 tests in 3.040s`, `OK`, `Live hosted system manager passed: 437 unit files, 477 unit names`, `Existing release package is private`. The six Plasma Login observer/inventory regressions ran along with all existing native regressions, without skips. Python/Bash syntax, release-input resolution and upstream signature verification passed. This is **checks-only evidence, not a VM acceptance result**. [Log](logs/06d-preflight-6-workflow.txt), [metadata](../../os/manifest/ci/06d/preflight-6/ci.json).

The hosted checks execute `python3 -m unittest discover -s os/tests -v`, `python3 -m py_compile os/ci/*.py os/ci/overlay/*.py os/tests/audit.py os/tests/power-events.py`, and the workflow's Bash syntax sweep. Full run 1 invoked `sudo -E python3 os/ci/switch_vm.py`; full run 2 never reached that step. Both full dispatches reused successful image job 39818554327 and skipped image build/publication. No new runtime digest was published.

**Budget: 2/2 full-run allowances used**, including the cancellation, plus six checks-only runs. Non-skipped jobs total **2,845 seconds = 47m25s**; rounding each started job up separately gives **52 minutes**, a quota proxy rather than a billing measurement. Full run 1's job took **38m53s**; the cancelled second took **4m02s**. [Run/job/archive summary](ci-06d.json). Run 1 metrics sampled peak used **70,270,169,088 bytes**, minimum free **6,600,208,384 bytes**, stock disk **53,141,831,680 virtual / 10,421,899,264 allocated bytes**, elapsed metrics window **2,303.105980157852 seconds**. [Metrics](../../os/manifest/ci/06d/full-1/metrics.json). No third full dispatch or rerun was made.

Seven new evidence ZIPs are retained and match their GitHub artifact SHA-256 metadata. The first preflight produced no artifact. Expanded run/job metadata and relevant evidence are under `os/manifest/ci/06d/`; workflow display copies, archives and the failed stock screenshot remain in this review directory. The staged whitespace check initially reported carriage returns/trailing blanks in raw terminal captures. Original evidence ZIPs remain untouched; original workflow bytes are additionally preserved in eight `06d-*-workflow-raw.txt.gz` archives with locally computed hashes. Expanded text copies normalize line endings/trailing whitespace for review. Screenshots are unchanged. The collector scans archive contents/logs for unmasked token/password-hash forms and refuses disk images, credential files, builder configurations and binary journals. No such secret/file was retained. These are evidence/file checks, not extra guest tests.

Final local `python -B -X utf8 .work/verify_06d.py --final` printed `VM ACCEPTANCE NOT MET: first run failed before switch, second cancelled before guest; final 82-test checks-only success verified; original stock screenshot preserved unchanged` and `Files passed: 39 JSON files, 131 local document links, 7 artifact hashes; unchanged runtime and tested harness`. It also verified all eight original workflow gzip hashes/decompression and exact normalized display-copy equality. It checks the failed/cancelled metadata rather than treating those runs as a pass, and proves no mod changes. [Output](logs/06d-final-file-verification.txt). After normalizing expanded terminal text, `git diff --cached --check` and the source/doc whitespace check passed. The full diff from `0e9478d` still flags trailing whitespace in the captured upstream `iso-picker.js` evidence copies; those original vendor bytes are preserved. Generated worktree-local Python caches were removed after verification; `-B` avoids recreating them. The final greeter's live VM behavior is still untested; these file checks do not close the acceptance gap.

Local Windows checks used only Python, Git Bash syntax/guard fixtures, Git and `gh`. The 6 original new shell tests passed (`Ran 6 tests in 21.016s`, `OK`), the 3 default-stock fixture tests passed (`Ran 3 tests in 0.011s`, `OK`), the 4 framebuffer tests passed (`Ran 4 tests in 0.172s`, `OK`), and the transaction-inspection unit and later guide-block regression each passed. Initial local shell-test development exposed Windows text-pipe CRLF conversion and environment injection differences; the fixture now sends UTF-8 bytes and explicit shell assignments. The guide reader also now requests UTF-8. These were fixture failures, not installed-image observations. Early framebuffer fixtures used Python's default temporary directory outside the worktree and automatically removed their PNGs; corrected all three to use the repository's test directory, then reran all four framebuffer tests (`Ran 4 tests in 0.173s`, `OK`). The fourth preflight verifies that test-fixture-only correction. Local `bash -n` checks printed `Bash syntax passed: 18 scripts/configs and 2 constructed guest snippets`. After the observer repair, `python -m py_compile os/ci/greeter.py os/ci/greeter_probe.py os/tests/test_greeter_probe.py`, the static-scan unittest and `git diff --check` passed locally. The native `pwd`/`/proc` observer tests ran on Linux CI. The full Linux suite, including native ACL/sysusers/PTY/socket regressions, was not claimed as run on Windows.

### Not verified

- **No successful 06d full run.** Rendered stock greeter after rollback, strengthened actual guest policy checks, transaction identity inspections before reboot, new tty3 logout/getty confirmation and another default stock boot remain unqualified. Both full-run allowances are used; no third run was started. Finding 4 and overall 06d acceptance remain open.

- **GRUB recovery promotion remains UNTESTED**: no one-time boot of previous stock with AresOS still the default, followed by index-changing promotion and another default boot. A normal rollback plus already-default `set-default` does not establish it. This is explicitly listed in INSTALL's open release gates.
- Physical ISO/installer/account UI, protected-Windows two-disk write audit, laptop GPU/display/keyboard/TTY/power, media, helpers and novice-followability gates remain open. No physical installation, owner token, repository/package visibility change or merge occurred.
- No Gradle/mod/Minecraft checks were run, per the brief and owner's current laptop-use constraint. Prior 06c mod checks are historical only.

### JUDGMENT-CALL

Use identity-checked `ostree admin set-default` for recovered stock, covering both current index 0 and later indices, rather than guessing an index or blindly rolling back while already booted into stock. The [bootc rollback manual](https://bootc.dev/bootc/man/bootc-rollback.8.html) queues the rollback slot, while the [OSTree manual](https://github.com/ostreedev/ostree/blob/main/man/ostree-admin-set-default.xml) and [source](https://github.com/ostreedev/ostree/blob/main/src/ostree/ot-admin-builtin-set-default.c) establish reordering the chosen deployment to the front and writing that deployment list. [Bazzite](https://docs.bazzite.gg/Installing_and_Managing_Software/Updates_Rollbacks_and_Rebasing/rolling_back_system_updates/) explicitly requires promoting a GRUB-recovered deployment afterward. This changes boot ordering only, retains the stock identity, and is reversible by another identity-checked selection. The brief pre-authorizes leaving this path untested; its qualification remains a gate rather than a tested claim.

### PLAN-GAP

The review correctly exposed the Bash exemption and insufficient graphical evidence. The brief does not need weakening: the harness implementation assumed the wrong stock display manager despite an existing RPM inventory. The corrected fixture now checks that inventory, and the observer matches the pinned manager's executable/account. Pixel thresholds still cannot identify a UI alone; process/VT readiness and visual inspection remain required. Static scan covers current shell-bearing sources and Python fragments; deliberately invalid scanner fixtures and historical binary/manifest evidence are not runnable product scripts. There is no observed new product-policy failure, but the revised guest checks have not reached a passing full rehearsal.

### Open questions

Overall 06d acceptance remains unmet. A future brief/run budget must qualify the corrected Plasma Login observer and complete switch, policy, tty3 login/logout, partition equality, rendered rollback greeter and second stock boot. GRUB recovery promotion remains explicitly untested as permitted by this brief. Physical-install gates and existing owner review items remain open. PR #10 remains open; do not merge on the basis of the regression result alone.

## 06e: VM qualification (2026-10-22)

### Done

Qualified the unchanged 06d harness (`5cbcfea`) against the existing private signed release from image job [39818554327](https://github.com/carlsenares/AresOS/actions/runs/39818554327). Runtime source remains `5578ab21b880091f26bfdc2eda22dd4f304a602b`, release digest `sha256:362af9b7d2a5573363d2cc441505dd076603d1d96c1b5c01af55589db2b6c402`. No runtime, mod, harness, test or workflow changes were needed; no rebuild or publication occurred.

- `reviews/06-image-release/`: retains the full-run artifact, original workflow bytes in gzip, normalized display log, run/job metadata and screenshots. The rollback greeter and tty3 logout prompt were visually inspected.
- `os/manifest/ci/06e/full-1/`: retains the four guest states, both pre-reboot inspections, policy/authentication/logout results, greeter identity/frame measurements, partition layouts and quota measurements.
- `os/manifest/release.json`, `os/README.md`, `docs/INSTALL.md`, `docs/design/OS-BASE.md`: point the qualification record at this successful run, close the revised-VM gate and preserve the separate GRUB/physical-install gates. The signed digest and runtime source do not change.

### Before full dispatch 1: assumption audit

Recorded before dispatch, against this exact pinned stock/release pair. This is a preflight comparison, not new guest qualification. The unchanged harness/tests already passed all 82 native regressions in 06d checks-only [39849142582](https://github.com/carlsenares/AresOS/actions/runs/39849142582).

| New/changed 06d check | Image-specific evidence and checked assumptions |
|---|---|
| Stock/rollback greeter identity | [Retained RPM inventory](../../os/manifest/ci/06c/image-full-1/packages.txt) contains `plasma-login-manager-6.7.5-1.fc44.x86_64`, with no SDDM. KDE's pinned [greeter daemon](https://github.com/KDE/plasma-login-manager/blob/v6.7.5/src/daemon/Greeter.cpp) sets user `plasmalogin`, `XDG_SESSION_TYPE` and positive `XDG_VTNR`; its [sysuser declaration](https://github.com/KDE/plasma-login-manager/blob/v6.7.5/services/plasmalogin-sysuser.conf.in) supplies the account. The [frontend service](https://github.com/KDE/plasma-login-manager/blob/v6.7.5/src/frontend/greeter/plasma-login.service.in) executes `plasma-login-greeter`. UID is resolved dynamically, executable basename is checked through `/proc/PID/exe`, and effective UID/environment are read as root. The [startup program](https://github.com/KDE/plasma-login-manager/blob/v6.7.5/src/frontend/startkde/startplasmalogin-wayland.cpp) calls `syncDBusEnvironment()` before starting the frontend; [its implementation](https://github.com/KDE/plasma-login-manager/blob/v6.7.5/src/frontend/startkde/startplasma.cpp) exports the session environment. No guessed UID, process argv, logind class or fixed greeter VT is required. |
| Display manager, VT and framebuffer | Both [stock](../../os/manifest/ci/06c/switch-full-2/stock-session.txt) and [rollback](../../os/manifest/ci/06c/switch-full-2/rollback-stock-session.txt) previously reported `display-manager.service` active. The [06d failed-observer frame](screenshots/06d-full-1-failure-stock.png) shows the greeter rendered and passes the unchanged pixel thresholds. Readiness still additionally requires the real greeter process and active `/sys/class/tty/tty0/active` after `chvt`, followed by visual inspection. `util-linux` supplies VT tools; Python/procps/systemd are in the retained inventory. |
| Transaction inspections before each reboot | Applied the actual `inspect_transaction` function to JSON extracted from the prior real [switch](../../os/manifest/ci/06c/switch-full-2/switch.txt) and [rollback](../../os/manifest/ci/06c/switch-full-2/rollback.txt) outputs. Both passed: staged release reference/digest and booted stock checksum for switch; `rollbackQueued=true`, no staged entry, retained stock reference/digest/checksum for rollback. `bootc 1.16.13`, `rpm-ostree 2026.3` and `ostree 2026.4` match the inventory. New disk checksums/partition UUIDs are learned from that run, never copied from old evidence. |
| Explicit negative account/policy assertions | [Stock account evidence](../../os/manifest/ci/06d/full-1/switch/stock-account.txt) confirms password-protected `ares-recovery` UID 1000/wheel. [Prior policy output](../../os/manifest/ci/06c/switch-full-2/aresos-policy.txt) confirms locked `ares` UID/GID 1001, no wheel/sudo grant, no competing processes/managers, masked units, denied updater executables and all five sleep requests rejected. The new explicit failure branches match these actual observations; none has been weakened. Stock `ares` absence and `/usr/bin/aresos-session` absence passed in both old stock phases. A newly observed prohibited condition is a product failure and stops this brief. |
| Tty3 login/sudo, logout/getty | [Prior getty](../../os/manifest/ci/06c/switch-full-2/tty-getty-ready.txt), [session](../../os/manifest/ci/06c/switch-full-2/tty-admin-session.txt) and [sudo](../../os/manifest/ci/06c/switch-full-2/tty-admin-login.txt) show the actual `agetty`/`login`/`sudo` flow on tty3 under UID 1000. `greetd` config fixes AresOS to tty1; serial ttyS0 independently observes it. Logout uses that same shell's `sudo -k` then `exit`, requires `agetty` on tty3 and no UID 1000 tty3 process, and saves the screen for login-prompt inspection. This new logout remains to be qualified. |
| Partition equality and persistent stock boot | Applied `partition_identity` to all three prior real layouts: identical `vda` and partitions; volatile zram is excluded. [Prior rollback status](../../os/manifest/ci/06c/switch-full-2/rollback-status.json) confirms the stock identity and no staged/queued transaction. `default-stock.sh` resolves the booted checksum's actual index, invokes `ostree admin set-default`, verifies index 0, then a separate default boot repeats identities/layout/greeter checks. The new fourth boot remains to be qualified. GRUB one-time recovery/promotion stays **UNTESTED** and receives no run. |
| Inherited Homebrew and release reuse | Existing stock/AresOS/rollback Homebrew evidence verifies the real `/var/home/linuxbrew/.linuxbrew` installation, UID 1000 ownership, stable executable hash and daily denial. The existing guard compares runtime paths, key, base and package lock against the successful signed image source; local `git diff --exit-code` confirms equality. No rebuild/publication, owner token or visibility change is needed. |

Local `python -B -X utf8 .work/06e_preflight.py` passed, printing both real transaction-schema acceptance lines, the pinned inventory/frame/accounts/policy/tty3/partition comparison, and unchanged runtime/harness confirmation. No Gradle, mod build, Minecraft client, local OS build or VM was run.

### Verified

**Full run 1 passed:** [39851266266](https://github.com/carlsenares/AresOS/actions/runs/39851266266), tested checkout **`613b826777836d59f15be96547654d725e1984de`** (the pre-dispatch audit commit; harness identical to `5cbcfea`). Exact dispatch:

```text
gh workflow run os-image.yml --ref pkg/06-image-release -f checks_only=false -f switch_from_run=39818554327
```

The image and checks-only jobs were skipped as intended. The switch job's unchanged-payload guard printed `Qualified release source 5578ab21b880091f26bfdc2eda22dd4f304a602b; runtime payload unchanged; testing ghcr.io/carlsenares/aresos@sha256:362af9b7d2a5573363d2cc441505dd076603d1d96c1b5c01af55589db2b6c402`. Guest signature verification passed. No harness flaw or product failure occurred, so no fix, new regression or checks-only dispatch was needed in 06e; the unchanged harness retains 06d's 82-test regression evidence.

The final guest command, `sudo -E python3 os/ci/switch_vm.py`, exited 0 and printed:

```text
Published-image switch, policy, tty3 login/logout, partition equality, rendered stock rollback and second default boot passed; GRUB recovery promotion UNTESTED
```

[Full workflow log](logs/06e-full-1-workflow.txt), [result JSON](../../os/manifest/ci/06e/full-1/switch/result.json), [run/jobs/artifact metadata](../../os/manifest/ci/06e/full-1/ci.json).

The 06d **Not verified** guest items now verified are:

| Previously unqualified item | 06e real-guest evidence |
|---|---|
| Corrected stock greeter observer | [Ready observation](../../os/manifest/ci/06e/full-1/switch/stock-bazzite-ready.txt) identifies `/usr/libexec/plasma-login-greeter`, actual UID **967** (`plasmalogin`), Wayland, VT **1**, then `STOCK_GRAPHICAL_GREETER_READY`. [Stock screenshot](screenshots/06e-full-1-stock-bazzite.png) visibly shows the account/password UI, clock, background and controls. |
| Transaction identity inspections before reboot | [Switch inspection](../../os/manifest/ci/06e/full-1/switch/switch-inspection.json) verifies the staged release reference/digest and still-booted stock checksum. [Rollback inspection](../../os/manifest/ci/06e/full-1/switch/rollback-inspection.json) verifies queued rollback, no staged entry and exact retained-stock reference/digest/checksum. Both actual inspections passed before their separate reboot. |
| Strengthened guest policy and rewritten negative checks | [Policy output](../../os/manifest/ci/06e/full-1/switch/aresos-policy.txt) ends `ARESOS_GUEST_CHECKS_PASSED`; live updater audit printed **1,083 system/user units inspected**. Locked daily UID/GID 1001, no wheel/sudo, executable denials, no competing desktop/managers, all masks, five rejected sleep targets, logind `CanSuspend = no` and UPower `Ignore` passed. Stock account-absence guards passed before switch, after rollback and on the second stock boot. [Inherited Homebrew](../../os/manifest/ci/06e/full-1/switch/aresos-inherited-homebrew.txt) also passed the explicit fresh-login PATH rejection; the original owner ran Homebrew 7.0.9 at every stage with the same script hash. |
| Tty3 password login, sudo, logout and getty prompt | [Login/sudo result](../../os/manifest/ci/06e/full-1/switch/tty-admin-login.txt) prints `RECOVERY_ADMIN_TTY3_LOGIN_AND_PASSWORD_SUDO_PASSED`. [Logout result](../../os/manifest/ci/06e/full-1/switch/tty-admin-logged-out.txt) prints `RECOVERY_ADMIN_LOGGED_OUT_TTY3_GETTY_READY`, with `agetty` running and no UID 1000 process attached to tty3. Visually inspected [authenticated session](screenshots/06e-full-1-recovery-admin-tty3.png) and [logged-out tty3](screenshots/06e-full-1-recovery-tty3-logged-out.png): the latter clearly reads **`bazzite login:`**, with no administrator shell. |
| Partition equality | `vda` and every attached partition's start, size, PARTUUID, type and filesystem UUID match across [stock](../../os/manifest/ci/06e/full-1/switch/stock-partitions.json), [AresOS](../../os/manifest/ci/06e/full-1/switch/aresos-partitions.json), [rollback](../../os/manifest/ci/06e/full-1/switch/rollback-partitions.json) and [persistent stock](../../os/manifest/ci/06e/full-1/switch/persistent-stock-partitions.json). Only the file-backed Linux disk was attached. |
| Rendered rollback greeter — closes 06d finding 4 | [Rollback status](../../os/manifest/ci/06e/full-1/switch/rollback-status.json) returns to stock checksum **`aa669eff4ea5c1f97c6c816c8d5d2abb5314e9afa3b966c0100e3e65f8040c71`** and pinned upstream digest. [Process/VT readiness](../../os/manifest/ci/06e/full-1/switch/rollback-bazzite-ready.txt) passed. **Visually inspected [rollback screenshot](screenshots/06e-full-1-rollback-bazzite.png): fully rendered Plasma login screen, `ares-recovery`, password field, clock, Bazzite background and power controls.** [Frame metrics](../../os/manifest/ci/06e/full-1/switch/rollback-bazzite-frame.json): nonblack 0.8514375, bright 0.0375, spread 42.598633817405165. This is graphical evidence, in addition to an active service. |
| Already-default stock selection and second stock default boot | [Default-stock command](../../os/manifest/ci/06e/full-1/switch/default-stock.txt) printed `Default is the identity-checked booted stock deployment: aa669eff4ea5c1f97c6c816c8d5d2abb5314e9afa3b966c0100e3e65f8040c71`. After a separate reboot with no boot selection, [status](../../os/manifest/ci/06e/full-1/switch/persistent-stock-status.json) retains that stock identity, no staged/queued transaction, and [deployment ordering](../../os/manifest/ci/06e/full-1/switch/persistent-stock-default-inspection.json) shows it booted at index 0. The [second stock greeter](screenshots/06e-full-1-persistent-stock-bazzite.png) was also visually inspected and is fully rendered. This verifies the already-default case only; **GRUB recovery promotion remains UNTESTED**. |

The [AresOS screenshot](screenshots/06e-full-1-aresos-labwc.png), also inspected, shows the expected labwc/foot terminal session. No Minecraft is present in this image. The extra `failure-persistent-stock.png` is the unchanged harness's automatic final-close capture of the still-running last VM, not a failed assertion; the workflow and result JSON both passed.

**Budget:** **1/2 full-run allowances used**, **zero** 06e checks-only dispatches, no rerun/cancellation. The successful job took **1,854 seconds = 30m54s** (approximately **31 billed minutes** if rounded up per job; this is a duration-based quota proxy). Tool/disk preparation took **21m45s**, guest qualification **7m06s**. [Metrics](../../os/manifest/ci/06e/full-1/metrics.json): sampled peak used **70,835,429,376 bytes**, minimum free **6,034,948,096 bytes**, stock disk **53,141,831,680 virtual / 11,063,361,536 allocated bytes**, elapsed sampling window **1,838.0812108516693 seconds**. Inherited image build metrics are historical, not another build in this run.

Collected evidence with `python -B -X utf8 .work/collect_06e.py 39851266266 full-1`; it reported `conclusion: success` and retained the **5,823,826-byte** original [artifact ZIP](artifacts/06e-full-1-os-switch-evidence.zip), SHA-256 **`ffe55c371a294c89ed1bebf536d5117aeabb5a583c1643b5be470d5c4a63ab1d`**, matching GitHub metadata. The [original workflow gzip](artifacts/06e-full-1-workflow-raw.txt.gz) has SHA-256 **`ae3e6617ead4f94dc633d0035d515a7e29545ab2082409340921414a832bca3e`**. Display text normalizes line endings/trailing whitespace; original archive/log bytes and screenshots are preserved. The collector rejected secret-shaped text, credential/config files, disk images and binary journals; none was retained.

Local `python -B -X utf8 .work/verify_06e.py` passed: successful switch-only workflow, unchanged runtime/mod/harness, exact artifact/log hashes and screenshot equality to the original ZIP, all four deployment/partition/Homebrew identities, both transaction checkpoints, policy, tty3 sudo/logout and all three rendered greeter frames. [Saved output](logs/06e-final-file-verification.txt) also confirms **174 local document links**. This is an evidence consistency check, not an extra guest run. Local helper syntax checks, `git diff --check` and `git diff --cached --check` passed; whitespace checks printed no errors. The budget-record helper printed `Budget: 1854 job seconds; 31 rounded minutes; 1/2 full runs; 0 checks-only runs`. No Gradle command, mod build, Minecraft client test, local OS build or local VM ran; no Gradle daemon was started, so no stop command was issued.

### Not verified

- **GRUB recovery promotion remains UNTESTED**: no one-time previous-stock boot while AresOS remains first, followed by index-changing promotion and another default boot. The successful already-default case does not qualify this path. No run was spent on it.
- Actual ISO/installer/account UI, protected-Windows two-disk write audit, physical GRUB interaction, laptop GPU/display/keyboard/TTY/power, media, helpers and novice-followability gates remain open. This single file-backed Linux disk is not a protected-Windows or hardware qualification.
- No Gradle/mod/Minecraft checks were run, as explicitly required by the owner and brief. No physical installation, owner token, repository/package visibility change or merge occurred.

### JUDGMENT-CALL

None added; use the pre-decided 06d sequence and keep the existing release gates.

### PLAN-GAP

None added. The corrected observer was qualified against the pinned image without changing the payload or weakening any check. The normal rollback/already-default boot coverage still does not establish GRUB recovery promotion.

### Open questions

06e acceptance is met. GRUB recovery promotion and the physical-install gates remain open, along with the existing owner review items in earlier sections. PR #10 stays open and is not merged.
