# 14: owner tools — STOP / PLAN-GAP before dispatch

**Current status after 14b:** the integrator resolved the NVIDIA-only source
blocker. The subsequent zero-cost stage walk found that the tools USB's expected
automatic firmware entry is unsupported by the inherited device-path audit.
The 11f stop rule applies before dispatch. No probe or qualification ran; PR #13
stays draft and physical installation stays **NOT RELEASED**. See the
[14b section](#14b--accepted-flatpak-deferral-and-tools-usb-stage-walk) for the
current evidence, local whole-suite result and remaining work.

## Original prerequisite stop, before 14b

**The zero-cost offline first-boot prerequisite fails its explicit prohibition
on deferred first-boot network work.** The pinned stock enables NVIDIA Flatpak
runtime setup; the ISO does not contain either required matching runtime. With
the NVIDIA module loaded, setup attempts a Flathub installation and retries on
failure. No owner-tools implementation, probe, qualification, image build or
publication followed. This report does **not** claim that an offline VM was run
or that stock cannot reach its greeter offline. Physical installation remains
**NOT RELEASED**; the PR is draft because package acceptance is unmet.

## Done

Ran `git fetch` first in this new worktree. Verified clean
`pkg/14-owner-tools` at brief commit
`362d0770033b5146940f696ee2a9a40a70b6283a`. Read AGENTS, README, brief 14, the
install-gate council's question/verdict/member reports, the relevant existing
preparation/recovery scripts and harness paths, and retained 11k/11n/13f
evidence. No retired worktree was accessed.

Performed source/data verification before any dispatch. Retained
[53 original source/data files with complete hashes](../../os/manifest/ci/14/zero-cost/README.md)
and a [read-only replay](verify-zero-cost.py). The complete pinned ISO was freshly
downloaded and hashed in this worktree; two exact public base-image layers were
also downloaded, hashed and read as archives. No image/container, root command,
mount, hardware query, firmware operation or application on the laptop ran.

No installer bundle, Windows copy command, short Linux command, new guard,
harness change or guide replacement is presented as implemented. The existing
guides/card and their open council findings remain unchanged. There is no
hand-typed-block or third-stick fallback.

## PLAN-GAP — offline stock retains NVIDIA setup for the later network

Brief 14 requires offline first boot to finish hardware setup/reboot/login and
leave no pending first-boot service waiting for a later network. It explicitly
requires stopping before dispatch if that prerequisite fails.

The concrete counterexample is the laptop's expected installed NVIDIA module:

1. The exact ISO's local cached image is the qualified stock digest
   `sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151`.
   The raw retained OCI manifest hashes to that same digest. The image's RPM
   [inventory](../../os/manifest/ci/06/image-6/kernel-nvidia.txt) pins NVIDIA
   **615.78.08**.
2. The frozen image enables
   `ublue-nvidia-flatpak-runtime-sync.service` in `multi-user.target.wants`.
   Its conditions require an installed OSTree boot and
   `/sys/module/nvidia/version`; this is a relevant path when the laptop's
   NVIDIA driver works. Its exact bytes match the
   [pinned upstream unit](https://github.com/ublue-os/bazzite/blob/2fab72cbc9a3257d80c607e173f22527aea3b39b/system_files/nvidia/shared/usr/lib/systemd/system/ublue-nvidia-flatpak-runtime-sync.service).
3. The [exact sync script](https://github.com/ublue-os/bazzite/blob/2fab72cbc9a3257d80c607e173f22527aea3b39b/system_files/nvidia/shared/usr/libexec/ublue-nvidia-flatpak-runtime-sync)
   skips work only when **both** versioned GL and GL32 runtimes are installed.
   The complete ISO filesystem inventory has **27 installed runtime IDs** and
   contains neither `org.freedesktop.Platform.GL.nvidia-615-78-08` nor
   `org.freedesktop.Platform.GL32.nvidia-615-78-08`. It contains no versioned
   NVIDIA runtime at all. The 20 other NVIDIA-named Flatpak paths are generic
   VA-API/Mesa files, not those runtime IDs.
4. The missing-runtime branch calls a Flathub `flatpak install`. The enabled
   unit has `Restart=on-failure`, `RestartSec=30`, and `TimeoutStartSec=600`.
   Thus an offline failure leaves network-dependent setup retrying; a later
   connection can complete that work. The paired verify/notification unit is
   also present. This is a source-derived consequence, not a new runtime result.
5. The current stock pause scripts target OS updater units, not this NVIDIA
   sync service. Pausing those units does not establish that NVIDIA setup is
   quiescent before reconnecting. No new `prepare` implementation was added to
   silently resolve or exempt this prerequisite.

This finding does **not** assert that a Flatpak installation stages an OSTree
deployment, or that the missing runtime necessarily prevents login. It
contradicts the separate, explicit **no deferred first-boot network work**
condition. A VM with virtual graphics would not establish this NVIDIA-dependent
condition merely by completing an offline login. Spending a probe to bypass
the failed source gate would not answer it.

The owner must settle how this deferred setup is handled within the two-stick,
offline-until-paused plan before package implementation/dispatch resumes. No
image change, new release, third stick, pre-pause network access, or manual
long-block workaround was chosen.

## Verified

### Pinned versions and zero-cost results

| Area | Source/data result |
| --- | --- |
| ISO | Full **9,068,650,496 bytes**, SHA-256 **`776b76f3417723440ee1823d79ec02a2c22860df196d219024edb062ad00d8e6`**, matching both the repository pin and a fresh [official checksum](https://download.bazzite.gg/bazzite-nvidia-open-stable-live-amd64.iso-CHECKSUM). |
| Anaconda | **44.30-2.fc44**; ISO network modules match [44.30 installation.py](https://github.com/rhinstaller/anaconda/blob/anaconda-44.30/pyanaconda/modules/network/installation.py) and [network.py](https://github.com/rhinstaller/anaconda/blob/anaconda-44.30/pyanaconda/modules/network/network.py) byte-for-byte. `NetworkInstallationTask` copies NetworkManager connection files into the target. The rule to avoid connecting in the live session is justified. |
| Local install payload | Actual ISO kickstart selects `containers-storage`; [pinned container-source code](https://github.com/rhinstaller/anaconda/blob/anaconda-44.30/pyanaconda/modules/payloads/source/rpm_ostree_container/rpm_ostree_container.py) does not require network for that transport. Actual post-install Flatpak script copies the ISO's local `/var/lib/flatpak` with rsync; it matches the pinned Bazzite source. These paths support offline installation at source level; a new complete offline install was not runtime-tested. |
| Origin change | ISO `%post` uses `bootc switch --mutate-in-place`; **bootc 1.16.13** [switch code](https://github.com/bootc-dev/bootc/blob/v1.16.13/crates/lib/src/cli.rs) takes the local origin-change branch and returns before the normal storage/pull path. `registry` in this command is not evidence of an install-time pull. |
| Stock/hardware setup | Bazzite **44.20261012.1**, revision **`2fab72cbc9a3257d80c607e173f22527aea3b39b`**; exact hardware setup is version **83** and equals the retained 13e source. OSTree **2026.4**, rpm-ostree **2026.3**, systemd **259.9** remain the pinned versions. Retained 11k, 11n and 13f each record the hardware-setup automatic reboot. Those runs are historical, not a new offline qualification. |
| Homebrew setup | The exact frozen service extracts `/usr/share/homebrew.tar.zst` locally; it does not download Homebrew at first boot. Its update/upgrade timers are separate. No brew command was executed in this run. |
| First later network | **Blocked:** enabled NVIDIA Flatpak setup can retry a network install, as detailed above. The no-deferred-work prerequisite is false; no complete new post-pause/network qualification is claimed. |
| Media Writer | **5.3.2**, the repository's pinned Windows release. [RestorePage.qml](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/app/qml/RestorePage.qml), [Windows restore helper](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/helper/win/restorejob.cpp), and [WinDiskManagement](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/lib/libwindisk/windisk.cpp) provide restore, clear the selected drive's old partitions/table, create a partition, assign/mount a drive letter and format exFAT, including the Windows API/CIMV2 fallback. This is a destructive stick restore, not preservation of its ISO/data. No writer or restore operation ran here. |

Media Writer's [5.3.2 German catalogue](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/po/mediawriter_de.po)
and system-locale selection were read, not translated from current `main`:
restore uses **Wiederherstellen**, finish uses **Fertig**, the drive-specific
heading uses **Laufwerk … wiederherstellen**, and success is **Das Laufwerk wurde
erfolgreich wiederhergestellt!** The multi-drive main selector and the
drive-selection prompt have empty translations; the generic heading is fuzzy.
Do not invent German rendering for those strings. The warning says the live
system and saved data are deleted. The Windows/German UI and expendable-media
trial remain unperformed. No guide tells the owner to use Disk Management,
diskpart or Windows Format as a fallback.

### Commands and actual outcomes

- `.work/14/fetch-sources.py` plus the additional pinned-source reads: retained
  **27 source files**, with URLs/byte counts/SHA-256 values in the source index.
- `.work/14/read-base-layer.py` and its `homebrew` invocation: verified complete
  public layer hashes **`1af49583…f96962` /324,644,312 bytes** and
  **`89d10b98…0b89` /156,741,603 bytes**. Read selected data only. The initial
  reader needed correction for OSTree archive hardlinks/symlink objects; the
  corrected reader preserved their content/targets as data, then reran.
- `.work/14/fetch-iso.py`, followed by `.work/14/complete-iso.py`: transferred the
  initial prefix and disjoint checked HTTP ranges, then hashed the **whole**
  ISO. Printed `PINNED_ISO_VERIFIED` with the exact hash and byte count above.
- Existing WSL `unsquashfs -ll -o 314167296` on that ordinary ISO: complete
  **1,439,437-line** listing. `unsquashfs -cat` read the **10** retained actual
  ISO files. No mounting, installation, sudo or software installation.
- `python -X utf8 reviews/14-owner-tools/verify-zero-cost.py --listing .work/14/squashfs-files.txt --record`:
  checked all **53** retained source/data hashes, the exact base manifest,
  matching source/ISO bytes, enabled unit, runtime inventory and source branch;
  printed **`STOP-PLAN-GAP`**, `source_integrity: passed`,
  `full_listing_replayed: true`, and zero dispatches. Native exit **2** denotes
  the failed prerequisite; this is not a passing owner-tools test.
- `.work/14/preclose-ledger.py`: read-only complete branch history and current
  org billing; results in [BUDGET.json](BUDGET.json). No dispatch API call.
- `git diff --check` and unchanged-path checks against `362d077` cover the
  existing harness, tests, owner scripts, guide/card, record helper, frozen
  Containerfile/context/locks/config/policy/base/keys/audit and release manifest.
  No runtime or qualified safety check was changed.

No new screenshots exist because no new VM or physical UI ran. All reported
observations are source/data verification or clearly identified old evidence.

## Budget

[Per-package ledger](BUDGET.json), measured before this closing push:

| Item | Actual / reservation |
| --- | ---: |
| Package cap | 350 minutes |
| First dispatch / ledger start | **Not started** |
| Probes | **0 /1** |
| Qualifications | **0 /2** |
| VM, image, release or publication minutes | **0** |
| Reserved VM minutes | **0** |
| Owner's initial branch privacy run, before first dispatch | 3 minutes |
| Closing push/PR privacy reservation | 8 minutes |

The complete pre-push branch history has **1 unique ID / total_count 1**,
completed push privacy run **40216222435**, no workflow_dispatch and no active
job. Per brief, the package dispatch clock has not started; pre-dispatch privacy
is separately recorded, not described as free org usage. Even charging its
3 minutes and the full 8-minute closing reservation conservatively gives only
11/350. No probe/qualification is authorized while the source gate is blocked.

Read-only org billing at **2026-10-25T17:49:28Z** reported **1,421 /2,000 used**,
**579 free**. Reserving 8 leaves **571**, above the **150-minute** reserve.
Known Linux-minute/storage SKUs, current period and zero paid net usage passed
the existing parser. The existing local gh login performed only GETs; no CI
billing credential or token scope was introduced. Closing privacy results,
actual minutes and final history are recorded in the PR body after the push,
avoiding a report-only push loop.

## Not verified

The owner bundle/copy step/commands and their refusal tests are **not built**;
the local whole suite and native preflight were **not run**. No offline VM,
tools-stick round trip, network-after-prepare, umlaut layout failure/revert,
successful change/back, guarded rollback or keep-stock qualification ran.
Existing 13f results do not fill those package 14 requirements. No Gradle build
or game/client tests ran; no mod changed, no green product claim is made, and
no Gradle daemon was started.

All physical, laptop, Windows/firmware, media, live-desktop and unaided
followability gates remain open. Package 14 acceptance is unmet; draft PR only.

## JUDGMENT-CALL

No new owner decision was made. Stopped at the brief's explicit source gate
instead of assuming virtual graphics proves the NVIDIA path, changing the
frozen image, suppressing a first-boot service without a settled plan, allowing
early network access, or inventing another stick/manual bootstrap. The owner's
two-stick/offline route remains the required design until revised by the owner.

## For package 15

Do not build the new owner path on unimplemented package 14 commands. After the
offline prerequisite and tools qualification are resolved, package 15 still
needs to address council findings **1, 4 and 8–11**: checkpoint return routes and
the mandatory Windows gate, permanent token retirement from Windows/phone,
symptom-first emergency navigation, German/Fn-mode shortcuts, exact localized
writer confirmations/cancellation, and one current status/boot-order table.
Include the checked stick restore/copy and explicit STOP/return destinations.
Physical/novice gates remain separate; no source check closes them.

## Open questions

At the original stop the owner needed to decide the handling of NVIDIA's
deferred first-boot network setup; **14b has now resolved that question**.
The rest of this paragraph records the original close. No user question or permission
prompt was issued mid-run, and no fallback was selected. No merge, force push,
visibility change, image dispatch or publication occurred. No token was printed
or retained in the evidence.

## 14b — accepted Flatpak deferral and tools USB stage walk

### Done

Ran `git pull --ff-only` first: **Already up to date**, on
`pkg/14-owner-tools` at `11728c531a6930a348bdaa2ae831a216d1f4d130`.
Read 14b and the inherited brief, council, guide, scripts and safety rules in
this worktree. Neither retired worktree was accessed.

Applied the integrator's NVIDIA decision to the source verifier, preserving
the original failed result as history. The new
[classification](../../os/manifest/ci/14/zero-cost/deferred-work-14b.json) and
[accepted source result](../../os/manifest/ci/14/zero-cost/verification-14b.json)
cover the retained scripts and known updaters:

| Work | Classification / handling |
| --- | --- |
| NVIDIA GL/GL32 sync and notification | Accepted deferred Flatpak-only work; never mask, disable, delay or replace it. Record its unit, check exit/result and runtime IDs without waiting. |
| Bazzite Flatpak manager 36 | Remotes, overrides, runtime cleanup, Firefox defaults and manager stamps; no deployment/BLS/disk operation in its complete script. |
| Homebrew setup/update/upgrade | Setup uses the local archive; mutable-prefix updates run as UID1000. Preserve the frozen AresOS Homebrew restrictions. |
| User setup 57 and its privileged helper | Desktop configuration/stamps, NTP and Tailscale operator settings; no network-dependent deployment path. |
| Hardware setup 83 | Local mandatory kargs/reboot before the round trip; not a deferred network job. Its one/two-serial result remains identity-checked. |
| OS updaters | Deployment-capable: pause before network, inspect system/global-user/active-manager units and transactions, and catch rpm-ostree/bootc/ostree clients. Never infer OS idleness from Flatpak's state. |

INSTALL and EMERGENCY now explain the expected offline notification. INSTALL's
release gate explicitly requires real-NVIDIA completion and unchanged complete
deployments/pins/pending/transactions/BLS after the network comes up. Virtio's
false NVIDIA condition cannot qualify that physical path. No stock service,
image policy or frozen runtime changed.

Read the actual ISO's XKB-derived console maps as data and retained them under
[keyboard-sources](../../os/manifest/ci/14/keyboard-sources/README.md). German
keycode26 includes U+00FC; US International includes U+00FC at AltGr+keycode21.
This supports a future plain-US failure/revert and US-International successful
trial with the unchanged umlaut password. No map was loaded; no physical trial
is claimed.

Drafted the bundle, copy checks, guarded commands and offline virtio-serial
WebUI transport locally before the stage walk reached the USB issue. **They
are not shipped or qualified.** The draft and its candidate patch are retained
only under ignored `.work/14/prototype/`; the active release scripts, harness,
workflow and test suite were restored exactly to the reviewed head. The
candidate's 11 pure preflight/bundle tests and eight PowerShell destination
refusals passed, but are development observations, not acceptance evidence for
an owner route. In particular, all-refusal shim coverage, full prepare/rerun,
stick diagnostics export and end-to-end layout proof still need completion.
No generated bundle/fingerprint or new owner command appears in the guide.

### PLAN-GAP: the virtual tools USB creates an unsupported firmware path

The expected attach transition is source-verifiable before spending minutes:

1. **OVMF 2024.02-2ubuntu0.10** enumerates whole BlockIo devices, fixed or
   removable, and creates missing automatic options from their device paths.
   This branch has **no filesystem or EFI boot-file test**. A data-only exFAT
   tools stick does not avoid enumeration.
2. The retained **whole BmBoot.c hash matches exactly** the hash recorded with
   that installed runner binary: `e961d1bc0ad7df99156a030dee92585fb2608ad5722f34d494459c2f74e6f3c6`.
   The tagged USB driver appends a USB messaging node, with port/interface;
   multi-LUN storage can add a logical-unit node. The latter driver/header
   files are upstream tagged source, not separately attested Ubuntu binaries.
3. The unchanged `disk_audit.firmware_hardware` only recognizes the retained
   PCI/SATA/NIC paths. Three source-derived USB path fixtures all produce
   **`PLAN-GAP: unsupported firmware device path`**, even with the exact
   16-byte automatic-option ownership GUID. These are synthetic fixtures,
   **not** a new observed VM store, and no exact future option number is assumed.
4. Reducing the USB identity to PCI controller `00:05.0` would be unsafe: the
   keyboard/controller remain present after removing the stick. It would hide
   the required detached-device failure. That shortcut was not implemented.

Pinned sources, hashes and scope are in
[firmware-walk](../../os/manifest/ci/14/firmware-walk/README.md). Primary sources:
[BmBoot.c](https://github.com/tianocore/edk2/blob/edk2-stable202402/MdeModulePkg/Library/UefiBootManagerLib/BmBoot.c),
[UsbEnumer.c](https://github.com/tianocore/edk2/blob/edk2-stable202402/MdeModulePkg/Bus/Usb/UsbBusDxe/UsbEnumer.c),
[device-path definitions](https://github.com/tianocore/edk2/blob/edk2-stable202402/MdePkg/Include/Protocol/DevicePath.h).

The applicable [11f stop rule](../../briefs/11f-linux-order-and-full-length.md#4-before-spending-minutes-walk-the-remaining-stages)
is explicit: **“If a transition you can foresee would fail the rules, stop and
report it as a PLAN-GAP before dispatching. Don't widen any rule yourself.”**
Stopped here. No controller-only exemption, USB-entry filtering, hotplug/media
substitution or other workaround was selected. The integrator must settle the
USB identity contract (exact port/interface/LUN, per-boot QMP attachment and
verified image backing), while keeping exact GUID ownership, detached-device
refusal, number takeover, fixed-entry order, Windows-first, Linux ESP/loader,
BootNext and protected-disk checks intact.

### Zero-cost stage walk, updated before any dispatch

All rows below are **planned**, not newly executed evidence.

| Stage | Expected NVRAM transition / existing rule |
| --- | --- |
| Baseline and live probe/install, protected second | Attached target/protected/DVD/NIC auto set; exact GUID and per-boot QMP ownership. Full disk/GPT/EFI/zero-write audits unchanged. |
| Installer completion | Target-only Fedora ESP/loader entry may be created/moved; Linux-first is permitted before the Windows-first step (11f). DVD removal recorded at next boot. |
| Offline first stock / hardware reboot | Local kargs initialization, at most the recognized orderly reboot; full audits at each reached stop. No external NIC traffic or copied live Wi-Fi profile is permitted. |
| Shutdown / detached Windows round trip | Target auto removal and any firmware relabel/number recycling under 11e; Windows entry byte-identical and first, no BootNext left over. |
| **Tools stick attached, next Linux start** | **Expected USB auto entry has an unsupported device path: STOP here before dispatch.** Existing one-time Linux BootNext must still be exact, recorded and consumed. |
| Install/prepare/network/title/records | Once unblocked, bundle copy/install equality and physical commands; pause/cleanup/repair/pin; complete deployment/BLS equality after network. Flatpak completion is diagnostic only. |
| Signed switch and AresOS boots | Exact staged target; pinned corrected stock preserved; expected final pair; title refreshed after each reorder; Windows remains firmware default. |
| Plain-US failure, revert, successful change/back | Original administrator session remains open; fresh second-console password/physical proof before every permitted reboot; no deployment/NVRAM change from localectl. |
| Rollback, stock, keep-stock and next default boot | Exact saved checksum/serial/stateroot/ref/digest/pin, no unrelated pending work; refreshed titles; all protected/NVRAM/BootNext checks at every stage. |
| Final Windows and detached Windows | Exact Windows default/entry and unchanged protected data; permitted auto-set removals/relabels only. |

For later scheduling only, 13f's full job took about **69 rounded minutes**.
A preliminary allowance of 42 for the probe plus 130 per qualification and 12
for closing privacy would total **314/350**, leaving 248 of the currently 562
free org minutes, above the 150 reserve. This is an estimate, **not a dispatch
authorization**; the USB contract, complete host walk, local checks, fresh
complete-history/org guard and same-head probe must all pass first. No timeout
or budget constant was changed while blocked.

### Verified

Actual receipts and the full unchanged-suite log are in
[local-verification](../../os/manifest/ci/14/local-verification/result.json).

| Command | Actual result |
| --- | --- |
| `python -X utf8 reviews/14-owner-tools/verify-zero-cost.py --14b --listing .work/14/squashfs-files.txt --record` | Exit 0; `SOURCE-GATE-PASSED-14b`; all 53 retained hashes and the complete 1,439,437-line listing replay passed. Original result preserved. |
| `python -X utf8 reviews/14-owner-tools/verify-firmware-walk.py --record` | Expected native script exit **2**; `STOP-PLAN-GAP`; four source hashes and pinned whole-file binding passed; all three USB fixtures rejected. A subprocess readback independently confirmed returncode2. |
| WSL `python3 -m unittest discover -s os/tests -v` | **237 tests /169.476s**, exit1, **2 failures +9 error records in eight distinct cases**, 229 passed; no skips or weakened tests. Repo TMPDIR; denying `sudo` shim returned126 before privileged commands. |
| Targeted exact owner keyboard/switch blocks, `test_disk_audit`, `test_firmware_contract` | **26 tests /0.301s, OK**, after the guide additions; current owner blocks still exactly match the release scripts. |
| `pwsh -NoProfile -File reviews/10b-own-ssd-fixes/test-install-record.ps1` | **78 checks passed**, PowerShell7.6.8. Synthetic inventory/decoder guards and unelevated pre-check; no disk/firmware query or setting change. |
| `git diff --check` | Passed. |
| Unchanged-path comparison with `11728c5` | Active `os/ci`, `os/tests`, `os/release`, workflow and release manifest unchanged. |
| Frozen runtime comparison with `2abc12e8aa6089f7576143d1fbccb6648a3291bd` | Containerfile/context/lock/config/policy/base/keys/audit unchanged; no image build/publication. |

Local limitations are explicit: three greeter cases lack WSL Pillow; three
Homebrew cases require forbidden privileged tmpfiles/ownership/ACL operations
(including duplicate cleanup errors); the sysusers case requires privilege;
one auth-file mode case sees DrvFS0777 rather than0600. Nothing was installed
or elevated to make these pass. Native CI must run the whole suite successfully
before a future probe VM. **No new native CI or VM run happened.** No Gradle
build/client test ran, no mod changed, no product-green claim is made and no
Gradle daemon was started.

### Ledger and privacy

[BUDGET.json](BUDGET.json) continues the same package ledger; it does not reset.
Fresh complete history: **5 unique IDs /total_count5**, one page, all completed
privacy runs, **17 rounded pre-dispatch privacy minutes**. **0/1 probes, 0/2
qualifications, 0 VM/image/publication minutes**, first dispatch/start still
null. Closing privacy reserves **12** minutes; even charging all pre-dispatch
privacy conservatively gives **29/350**. No POST dispatch was sent.

Read-only org billing at **2026-10-25T18:40:40Z** reports **1,438/2,000 used**,
**562 free**; reserving12 leaves **550**, above150. Current-period SKU/zero-paid
checks passed. Repo remains private; PR13 is open/draft against main. Closing
head privacy results, actual minutes and log hashes will be recorded in the PR
body after this push, without a report-only push loop.

### Not verified / remaining acceptance

The owner bundle, Windows copy route, short commands, every-refusal fake-tool
trace coverage, prepare/rerun/record exports, guarded layout and command/bundle
equivalence are **not shipped or accepted**. No offline install, first stock
boot, tools USB boot, network-after-prepare comparison, token login, signed
switch, umlaut failure/revert, successful change/back, rollback/keep-stock or
next-default VM evidence was produced for package14. All physical/followability
gates remain open. PR13 must remain draft; acceptance is not met.

### JUDGMENT-CALL and open decision

No new device-path exception was chosen. Resuming the deferred-Flatpak work is
authorized by14b; extending the firmware path contract independently would
contradict11f's explicit stop instruction. The needed integrator decision is
the narrow USB identity/evidence rule above. The physical owner route remains
two sticks, offline until the checked pause; no third stick or manual-block
fallback was substituted.

For package15, the council findings1,4,8–11 listed in the original section still
stand. Add the tools round-trip acquisition/return checkpoints and the expected
NVIDIA notification when the tool route is actually qualified; do not present
the ignored development prototype as an available command. Physical installation
remains **NOT RELEASED**. No merge, force push, visibility change, real-laptop
operation or secret printing/storage occurred.
