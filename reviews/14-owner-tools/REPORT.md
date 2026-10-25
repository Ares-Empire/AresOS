# 14: owner tools — STOP / PLAN-GAP before dispatch

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

The owner must decide the permitted handling of NVIDIA's deferred first-boot
network setup before this package resumes. No user question or permission
prompt was issued mid-run, and no fallback was selected. No merge, force push,
visibility change, image dispatch or publication occurred. No token was printed
or retained in the evidence.
