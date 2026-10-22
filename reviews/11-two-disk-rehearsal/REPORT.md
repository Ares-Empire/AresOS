# Package 11: two-disk install rehearsal and pinned media

Status: **STOPPED — A NOT QUALIFIED; B UNTESTED; C PINNING DONE.** Both full
automation allowances were consumed. [Final run 39869390172](https://github.com/carlsenares/AresOS/actions/runs/39869390172)
stopped before installation at an absent `ksvalidator`. The actual Anaconda
help also documents kickstart as unsupported for live installations. No third
full run was started. Physical installation remains **NOT RELEASED**.

## Done

- `os/ci/disk_audit.py`: offline full protected-image SHA-256; validated primary
  and backup GPT headers/tables; partition GUID/type/boundary inventory; all EFI
  file hashes including the fallback path; EDK2 variable-store parsing and full
  variable/boot-entry diffs. Zero protected QEMU write bytes/operations are
  required, including shutdown writes. Linux entry GUID/bounds must target the
  new Linux ESP; the original Windows entry must remain byte-identical.
- `prepare_two_disks.py`, `windows_marker.c`: writable, sparse 50/49 GiB files,
  protected ESP/MSR/NTFS-with-files/recovery layout, and an original EFI marker
  at both Microsoft and fallback paths. A verified loop backing file is required
  before filesystem creation on the disposable hosted runner. The marker
  reports BootCurrent and its actual loaded device/file path.
- `two_disk_vm.py`, `switch_vm.py`: reuse the 06e switch/policy/real tty3/rollback
  checks, add drive-order adapters, offline shutdown hooks, EFI-target checks,
  Windows-first non-erasing undo, detached-target marker checks and the GRUB
  recovery/promotion path. Installed German console input is translated rather
  than changing the keyboard layout. The original one-disk behavior and all
  existing tests remain available.
- `installer_inspect.py`, workflow: verify complete pinned ISO bytes, inspect
  its actual boot/installer/defaults/container metadata, and provide separate
  inspection, native-fixture, probe and full modes. Rehearsal modes cannot enter
  the image-build/publication jobs and have only package-read permissions.
- `os/manifest/media-tools.json`, INSTALL §2/§9: official Windows writer 5.3.2
  and GParted Live 1.8.1-6 amd64 URLs, versions, full SHA-256 and publisher
  checksum sources; fail-closed install-day checks. Both complete Bazzite ISO
  downloads and the writer/GParted downloads match their publisher pins.
- New regressions exercise corrupt GPTs, lost/changed Windows entries, exact
  EFI target parsing, restored-byte write detection, final counter ordering,
  German input, reversed target selection, kickstart scope and the loop-query
  correction. Evidence, original archives, workflow logs and minute ledger are
  retained here and under `os/manifest/ci/11/`.

## Verified

The tested release remains
`ghcr.io/carlsenares/aresos@sha256:362af9b7d2a5573363d2cc441505dd076603d1d96c1b5c01af55589db2b6c402`,
source `5578ab21b880091f26bfdc2eda22dd4f304a602b`. No image build, republish,
visibility change, owner registry token, local VM or physical disk operation
was performed. Runtime/config/base/key/lock paths match that signed source.

| Gate | Current result | Evidence |
|---|---|---|
| A: two-disk install, both drive orders | **OPEN — not reached** | [Failure log](logs/full-2-workflow.txt); target remained empty; no reversed installation |
| A: offline protected disk through switch/rollback/undo | **OPEN — not reached** | [Baseline](../../os/manifest/ci/11/full-2/two-disk/protected-baseline.json), [after firmware](../../os/manifest/ci/11/full-2/two-disk/baseline-firmware-protected.json), [after live probe](../../os/manifest/ci/11/full-2/two-disk/live-ui-probe-protected.json), [after failed preflight](../../os/manifest/ci/11/full-2/two-disk/protected-first-install-protected.json) are identical; these are pre-install stages only |
| A: original Windows entry and detached-target boot | **Baseline entry boot proved; required independence tests OPEN** | [Actual BootCurrent/device/file](../../os/manifest/ci/11/full-2/two-disk/baseline-firmware-marker.txt), [screenshot](screenshots/full-2-baseline-firmware-windows-marker.png); Linux target was still attached |
| B: one-time stock recovery, index-changing promotion, unattended stock boot | **UNTESTED — no installed target** | Installation, switch and GRUB were not reached; INSTALL and EMERGENCY retain the open gate |
| C: Bazzite pins | DONE | [Live download](../../os/manifest/ci/11/inspect-2/installer/iso-download.json), [legacy download](media/additional-downloads.json); both complete hashes match |
| C: writer/GParted pins | DONE | [Manifest](../../os/manifest/media-tools.json), [official writer receipt](media/fedora-media-writer-release.json), [GParted checksum](media/gparted-CHECKSUMS.TXT), [GParted download](media/additional-downloads.json) |
| Physical media / click path / novice / hardware | OPEN | No physical-media rehearsal; automated installation cannot qualify the click path |

Commands dispatched (all on this branch):

```text
gh workflow run os-image.yml --ref pkg/11-two-disk-rehearsal -f rehearsal=inspect
  39864229155, 39865512476
gh workflow run os-image.yml --ref pkg/11-two-disk-rehearsal -f checks_only=true
  39865338296, 39869231221
gh workflow run os-image.yml --ref pkg/11-two-disk-rehearsal -f rehearsal=probe
  39866564466  # failed preparation; conservatively full allowance 1/2
gh workflow run os-image.yml --ref pkg/11-two-disk-rehearsal -f rehearsal=fixture
  39867994684  # explicitly no VM
gh workflow run os-image.yml --ref pkg/11-two-disk-rehearsal -f rehearsal=full
  39869390172  # final full allowance 2/2
```

- Inspection 1 passed: full live download **9,068,650,496 bytes**,
  `776b76f3417723440ee1823d79ec02a2c22860df196d219024edb062ad00d8e6`.
  Inspection 2 repeated the hash and captured actual ISO configuration. Its
  embedded `bazzite-nvidia-open:stable` is exactly the tested stock digest
  `sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151`.
- Checks 1 printed **`Ran 87 tests in 3.212s`, `OK`**; checks 2 printed
  **`Ran 95 tests in 3.021s`, `OK`**. Host checks printed **437 unit files /
  475 names**, then **437 / 473**. Both confirmed the package remains private,
  Python/Bash syntax, official release metadata and upstream signature.
- Probe 1 printed **`Ran 91 tests in 2.589s`, `OK`** and the unchanged-release
  guard. The original marker compiled. Preparation failed at JSON decoding of
  `losetup --json DEVICE`, before any VM boot. Fixed the missing `--list` with
  a regression; no product check was weakened. This failure still counts as
  full allowance 1/2. [Exact log](logs/probe-1-workflow.txt).
- Native fixture printed **`Ran 94 tests in 3.257s`, `OK`**, then
  **`Created 50 GiB protected GPT/ESP/MSR/NTFS/recovery disk and empty 49 GiB
  target; file backing verified`** and **`Native file-backed GPT/EFI/MSR/NTFS/
  recovery and offline audit passed; no VM started`**. [Result](../../os/manifest/ci/11/fixture-1/native-fixture.json)
  contains whole-image hash `71ec6fffe12a691f6ed080588b83ee65a912f38e662aa86eace56e8cc791737d`,
  four correct partition types, all GUIDs/boundaries and two identical EFI file
  hashes. These are fresh fixture identities, not owner/install records.
- Local Windows checks ran only Python/Git/gh and public download hashing.
  The focused suites printed **6 disk-audit tests / 10 VM-adapter tests,
  OK**, and Python AST syntax checks passed. Linux native sysusers/ACL/PTY and
  real filesystem checks are evidenced by the hosted jobs, not claimed as
  locally executed.

### Final full attempt and stop

Run 39869390172 used checkout **`f32f1da`**, passed **`Ran 95 tests in 3.260s`,
`OK`**, re-verified the exact live ISO, and printed the unchanged-release guard.
The corrected real disk preparation passed. No build/publication job ran.

The firmware booted **Boot0000 Windows Boot Manager** from protected ESP GUID
`e6f6beec-8511-40c2-9af8-e3c746fb04ff`, Microsoft loader path
`\EFI\Microsoft\Boot\bootmgfw.efi`. The marker text and screenshot were
visually inspected. This proves the initial fixture's original entry/path,
not post-install Windows independence or a real Windows OS boot.

The live ISO booted twice and exposed the real serial identities:
**protected `vda` / MICRON-KEEP**, **empty target `vdb` / CRUCIAL-TARGET**.
The embedded stock digest matched. Root live login and orderly live-probe
shutdown passed. Both final firmware/probe counter records show protected
**`wr_bytes=0`, `wr_operations=0`**. The four offline snapshots (initial plus
three checks) have identical whole-disk SHA-256:

```text
3dd5715e983a3c8cbe2e243273142b12ba00ce507e9907a8e043833ae3f0a519
```

Both GPT copies, every GUID/boundary and EFI file hash matched too. Windows's
boot entry/order did not change; boot-entry diffs are empty. Full variable
diffs retain only the firmware's `MTC` variable change. Original OVMF stores and
all raw events are retained in the [full-run evidence](../../os/manifest/ci/11/full-2/two-disk/).
The last failed-preflight VM was host-terminated by cleanup, then hashed
offline; it has **no final write-counter snapshot**, so byte equality alone
does not prove zero transient writes in that last VM.

All four screenshots were visually inspected. The purported UI frame and
keyboard-probe frame show **Bazzite Portal**, not the installer. Backend
Anaconda processes existed, but that is not graphical-installer readiness.
The [first frame](screenshots/full-2-live-installer-ui.png) and
[after keys](screenshots/full-2-live-installer-keyboard-probe.png) provide no
destination, review or EFI plan proof. The [failure frame](screenshots/full-2-failure-protected-first-install.png)
shows the live desktop wallpaper, not a completed install.

The automatic transaction never started. `prepare-kickstart` returned **127**
because the ISO lacks `ksvalidator`; I had failed to check that executable in
the already captured inventory before dispatch. That was a harness error.
The actual [Anaconda help](../../os/manifest/ci/11/full-2/two-disk/protected-first-install-cli.txt)
also explicitly marks `--kickstart` unsupported for live installations. The
presence of its option is not proof of supported live behavior.

After stopping full runs, regressions now consume that actual help and the
frozen ISO inventory: unsupported live kickstart is rejected before preparing
or starting an installation. The absent standalone utility is replaced by
strict installed-Pykickstart parsing for any future separately qualified
supported ISO; **that replacement is not live-VM-qualified here**. Code review
also corrected BLS parsing so an `ostree=` option cannot consume the next line;
malformed/ambiguous BLS data is rejected. None of this closes A/B, and no
missing check was skipped to get a pass.

### Media verification and automation differences

The complete legacy ISO stream was **8,079,671,296 bytes**, hash
`85e701c0f53189b0fa32797ffe8144202dcaa8db6c7692fd4677f615537b24b8`.
Writer EXE bytes matched the publisher's API `assets[].digest`:
`f53e0c1108f83a99ad0d7a9aee846822093b1afe595c78f13b22ba779d9f4bd4`.
GParted's short download URL returned HTML to the automated client; it was
rejected, not mistaken for an ISO mismatch. The versioned official project URL
then yielded **720,371,712 bytes**, hash
`d789c38779f0d6f7026c12f44c2c52a04f66e28a1aea7d51f3045ad1bbf28411`.
The manifest uses that versioned URL. Original failed-page metadata is retained
alongside the successful download observation. No downloaded executable/ISO
was installed or written to physical media.

No immutable Bazzite download URL is qualified. On install day the owner must
compare the pinned filename/hash, freshly fetched official checksum and the
entire downloaded ISO hash; every mismatch/missing release stops the guide.
The same policy applies to the versioned writer/GParted pins. A versioned URL
alone is not a cryptographic immutability guarantee.

The actual ISO launcher and Anaconda help warn that live kickstart is
unsupported. The launcher's `LIVECMD` hook permits an alternate command in the
same prepared environment; it does **not** establish live kickstart support.
The unqualified prototype fallback preserves the ISO's
original defaults/post-scripts but supplies the whole-drive selection and
account/localization answers through kickstart. It bypasses destination,
review, EFI and account UI pages, adds a serial console and automatic reboot,
and boots the ISO's actual kernel/initrd directly. These differences remain
open media/followability items, regardless of VM safety results. Details and
per-dispatch evidence are in [ASSUMPTIONS.md](ASSUMPTIONS.md).
The serial transport also bypasses the owner's live-desktop German-layout and
typing check; it does not qualify those steps. The unexecuted reversed-fixture
code would reset only the closed disposable Linux file after the recorded
non-erasing undo. That fixture reset is not part of §9 undo.

### CI budget

[Ledger](ci-ledger.json) records every dispatch, actual job timestamps and
archive digests. Through the final full job: **3,217 job seconds = 53m37s**,
**58 minutes** when each started job is rounded up separately, within the
**450-minute package cap**. A final checks-only regression job is recorded
below when complete; it starts no VM. This is a duration-based quota proxy,
not an invoice. Both full allowances are spent, including failed preparation;
the remaining quota does not authorize a third run.

## Not verified

**A and B acceptance are not met.** No storage installation transaction,
installed target ESP/bootloader audit, actual-ISO AresOS switch/policy/recovery/
rollback, default undo, reversed-order install, post-install/post-undo Windows
boot without Linux, one-time GRUB recovery or promotion was reached. No
destination/review/EFI/account screen was qualified. The same-ISO kickstart
prototype and later harness fixes have no passing live installation evidence.
There is no passing two-disk result JSON.

No physical USB workflow, unaided novice walkthrough, real Windows/BitLocker/
UEFI helper trial, Lenovo fitting/firmware review, RTX rendering, laptop input/
TTY/power/battery test or physical GRUB keyboard trial was performed. No mod,
Gradle or Minecraft command ran; no Gradle daemon was started.

## JUDGMENT-CALL

No runtime/product-feel decision added. Use the pre-decided isolated file disks,
existing signed image, recovery identity checks and non-erasing undo. The
automated installer differences above do not release the owner's click path.

## PLAN-GAP

The pinned launcher **and Anaconda's own help** document live kickstart as
unsupported. The brief's example therefore is not a qualified fallback for
this exact ISO. A future scoped run must faithfully drive the actual UI or
establish another same-ISO installer path; neither a legacy ISO nor a directly
constructed stock disk may silently substitute. The current data does not
establish whether an unsupported direct invocation could technically work.
Both failures were harness assumptions (losetup JSON mode, then validator
availability); no protected-disk change was observed and no product repair
was attempted. The initial backend-only UI probe also did not prove an
installer screen, as the saved Portal frames make clear.

## Open questions

Installation/GRUB qualification needs a new scoped continuation. Human,
hardware, media/followability and safety-council gates remain open. This PR is
a draft stop/report handoff, not an installation release. Do not merge.
