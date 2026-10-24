# Package 11: two-disk install rehearsal and pinned media

11e continuation: the integrator's device-set rule passes the retained first-
and reverse-order stores and 58 focused regressions. Fresh probe/full evidence
is pending; no installation gate is released. The shared ledger starts this
continuation at 70/330 minutes, including the new brief's two privacy jobs.

Latest 11d outcome: **STOPPED at reverse-order detached firmware audit — automatic entry changed and an attached-device entry disappeared. A OPEN, B UNTESTED, C pins retained.** The owner token closed the release-access blocker; 133 native regressions passed. Protected bytes and Windows entry stayed unchanged, with six zero-write records, but the failed probe authorizes no full run. Shared 11c/11d measured cost is **66/330 minutes**, plus at most 14 reserved for closing privacy checks; **0/3 full runs**. See [11d](#11d-owner-read-only-token-and-continued-qualification-2026-10-24).

Latest 11c outcome: **STOPPED before any VM — pinned private image returned manifest unknown. A OPEN, B UNTESTED, C pins retained.** Native regressions and exact firmware-rule regressions pass; no full run was authorized. See [11c](#11c-firmware-contract-and-fresh-install-qualification-2026-10-23).

Latest 11b outcome: **STOPPED at the pre-install firmware audit; A NOT QUALIFIED, B UNTESTED, C pins unchanged.** No installation or full run was authorized. Follow-up cost: **168/350 minutes, 0/3 full runs**. See the 11b section below; earlier sections retain the original package-11 history.

Original package-11 outcome: **STOPPED — A NOT QUALIFIED; B UNTESTED; C PINNING DONE.** Both full
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
  39865338296, 39869231221, 39872316944
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

**Final regression-only run:** [39872316944](https://github.com/carlsenares/AresOS/actions/runs/39872316944),
checkout **`bf5c98d`**, passed **`Ran 98 tests in 3.137s`, `OK`**. The live host
query printed **437 unit files / 475 names**, package visibility remained
private, and Python/Bash syntax, release metadata and signature verification
passed. [Exact output](logs/checks-3-workflow.txt). It built no image and started
no VM. The final harness fixes are regression-qualified only; the failed full
run remains failed. No runtime/mod source changed afterward.

Final [file verification](logs/final-file-verification.txt) checked all archive
hashes, screenshot/OVMF byte equality to the original ZIP, the four matching
protected records, the original Windows entry, both final zero-write snapshots,
all minute totals and document links. It explicitly reports installation and
GRUB qualification as unmet. `git diff --check` and the runtime/mod Git
comparisons passed. These are evidence checks, not another guest test.

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
archive digests. Final total across **8 dispatches**: **3,247 job seconds =
54m07s**, **59 minutes** when each started job is rounded up separately, within
the **450-minute package cap**. The final checks-only job took 30 seconds and
started no VM. This is a duration-based quota proxy, not an invoice. Both full
allowances are spent, including failed preparation; the remaining quota does
not authorize a third run.

| Dispatch | Result | Job duration | Rounded minutes |
|---|---|---:|---:|
| inspect-1 | success | 9m29s | 10 |
| checks-1 | success | 35s | 1 |
| inspect-2 | success | 7m08s | 8 |
| probe-1 (full allowance 1) | failed before VM | 9m18s | 10 |
| fixture-1 | success, no VM | 9m24s | 10 |
| checks-2 | success | 41s | 1 |
| full-2 (full allowance 2) | failed before installation | 17m02s | 18 |
| checks-3 | success, no VM | 30s | 1 |

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

## 11b: real Web UI continuation — 2026-10-23

### Done

- `installer_webui.py` drives the pinned ISO's own Anaconda pages from host
  Chromium. It launches ordinary `liveinst` as liveuser, preserves its backend
  and original HTTP listener, and relays bytes through guest 8080 and host
  loopback 18080. It records each page's screenshot, text, controls and IDs.
  The exact guest Firefox profile's process tree is paused, because terminating
  Firefox tears down Anaconda. No page/backend code is replaced.
- The shared preview/install flow selects German only, Europe/Berlin,
  serial-identified target only, entire disk, an unencrypted trial, and a
  password-protected wheel administrator `ares-recovery` with root locked.
  Save must reach stable backend German state. The ISO's own keyboard resolver
  must generate `KEYMAP=de` in a temporary live directory while restoring live
  settings and preserving module choices. Installed German/TTY checks remain
  separate, strict requirements. Review must contain only target storage and
  a newly formatted target EFI. Probe tests actionability without clicking
  Erase; only full mode can click it.
- `rehearsal_guard.py` enforces 350 rounded hosted job minutes, at most three
  full dispatches, and a successful complete probe artifact on the exact same
  commit. Complete proof requires both orders, review, detached Windows marker
  and target reset. Artifact SHA-256 is checked against GitHub's receipt.
- Harness changes preserve partial redacted timeout evidence, always attempt
  orderly shutdown despite diagnostic failure, require final stopped-guest
  write counters, reject unsupported live kickstart, and learn actual BLS IDs.
  The same quoted read-only BLS export runs in live preflight and recovery.
  Generated Python caches are ignored. Regression coverage includes unsafe disk/review/EFI choices, missing probe
  evidence, short ISO transfers, real captured help/modal fixtures, salted
  password redaction, BLS export and cleanup failure paths.
- The workflow installs pinned browser tooling only on disposable runners.
  Rehearsal paths cannot rebuild/publish the image. Complete-file ISO pins,
  runtime identity/signature checks, original Windows entry checks and every
  protected-write assertion remain mandatory. Exact UI sources were extracted
  from the pinned ISO's shipped source map before further selector changes.

### Verified dispatch history

Each dispatch below used `gh workflow run os-image.yml --ref
pkg/11-two-disk-rehearsal -f rehearsal=probe`, except inspection 8 (`inspect`).
The original artifact and workflow-log ZIPs, their API receipts, expanded
evidence and screenshots are retained under `artifacts/`, `logs/11b/`,
`screenshots/11b-*` and `os/manifest/ci/11b/`. Failed suites remain failed;
passing regression tests alone do not qualify a probe.

| Label / run | Source | Rounded minutes | Exact native tests / result |
|---|---|---:|---|
| [0](https://github.com/carlsenares/AresOS/actions/runs/39873210999) | `6683e19` | 2 | Cancelled during setup, before ISO/VM; browser venv lacked system PIL |
| [1](https://github.com/carlsenares/AresOS/actions/runs/39873265524) | `6bfefc8` | 16 | `Ran 98 tests in 3.086s`, `OK`; real guest Welcome, serial inventory timeout; no host UI |
| [2](https://github.com/carlsenares/AresOS/actions/runs/39875264662) | `a7a0a44` | 16 | `Ran 104 tests in 3.078s`, `OK`; destination-only success, explicitly not authorization |
| [3](https://github.com/carlsenares/AresOS/actions/runs/39877073155) | `502676b` | 23 | `Ran 105 tests in 2.753s`, `OK`; ANSI-colored unsupported-live help failed the guard |
| [4](https://github.com/carlsenares/AresOS/actions/runs/39879865566) | `c4bcb1d` | 3 | Premature EOF: 452,788,224 of 9,068,650,496 advertised bytes; no tools/VM; pin unchanged |
| [5](https://github.com/carlsenares/AresOS/actions/runs/39880735063) | `60758f6` | 15 | `Ran 111 tests in 3.076s`, `OK`; real German modal, absent upstream summary selector |
| [6](https://github.com/carlsenares/AresOS/actions/runs/39882648993) | `221ca1a` | 12 | `Ran 112 tests in 2.528s`, `OK`; X layout de, raw console property empty; derived-console lifecycle not yet checked |
| [7](https://github.com/carlsenares/AresOS/actions/runs/39884771824) | `ccb1b81` | 13 | `Ran 113 tests in 4.000s`, `OK`; expanded keyboard proof saw wrong X layout; stopped before resolver |
| [8](https://github.com/carlsenares/AresOS/actions/runs/39886346092) | `1fa92a0` | 7 | Exact ISO verified; 102 actual application sources extracted; no VM |
| [9](https://github.com/carlsenares/AresOS/actions/runs/39888209565) | `28a8d09` | 13 | `Ran 113 tests in 3.220s`, `OK`; terminating Firefox removed runtime config before host UI navigation |
| [10](https://github.com/carlsenares/AresOS/actions/runs/39889623330) | `d8d6fa9` | 31 | `Ran 114 tests in 4.088s`, `OK`; every first-order pre-install page/review passed; dynamic completion-selector literal check failed before backend review readback/reverse order |
| [11](https://github.com/carlsenares/AresOS/actions/runs/39892768284) | `24118e1` | 17 | `Ran 115 tests in 3.284s`, `OK`; first-order complete preview/readback passed; pre-install detached marker boot failed strict existing-entry preservation |

The [assumption ledger](ASSUMPTIONS.md#11b-real-web-ui-continuation) records
each preflight hypothesis, actual observation and resulting correction. In
particular, source inspection established that keyboard Save does not await
its async backend write, review has ordinary cells rather than guessed data
attributes, and full-name blur can asynchronously suggest a username. The
original unsupported-live-kickstart rejection is still exercised; no legacy
ISO or hand-built installed stock disk substitutes for this installer.

Probe 10's [review screenshot](screenshots/11b-probe-10-two-disk-review-full.png)
and [full text](../../os/manifest/ci/11b/probe-10/two-disk/review-full.txt) show
only `vdb1` new EFI, `vdb2` boot, and `vdb3` Btrfs subvolumes. Its
[German conversion proof](../../os/manifest/ci/11b/probe-10/two-disk/webui-keyboard-proof.json)
records the actual installation task source/hash, German module state,
generated `KEYMAP="de"`, restored live configuration and unchanged choices.
The [destination modal](screenshots/11b-probe-10-two-disk-destination-selection-before-confirming.png),
[encryption page](screenshots/11b-probe-10-two-disk-configuration-00-answered.png)
and [account page](screenshots/11b-probe-10-two-disk-configuration-01-answered.png)
were also visually inspected. These are preview evidence, not installation.

The completion check now verifies the exact served bundle/source-map hashes
and derives the progress/error selectors from the actual source formulas.
A regression consumes those three frozen original sources and rejects changed
state names/prefixes. Searching the minified bundle for dynamically assembled
full names was the incorrect assumption; no status check is discarded.

Browser/transport differences from the owner: headless Chromium on the host,
the TCP relay, and a paused guest Firefox process tree after ordinary launch.
Direct ISO kernel boot adds serial consoles; the actual pinned installer
source/config confirms they are preserved. Serial poweroff replaces the final
UI reboot solely to close images for offline auditing. Physical USB boot,
physical keyboard interaction and novice followability remain separate gates.

The anonymous public manifest metadata check at 2026-10-23T02:29:55Z found the
installer post-script's `bazzite-nvidia-open:stable` still exactly at qualified
stock digest `ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151`.
No image layer or owner registry credential was used for this check.

### Remaining result, gates and final budget

Final probe 11 used **`24118e1e4a4b2ef1b1806afe5131b029c2de81f4`**. It passed
all first-order pre-install choices, completion-source qualification and
[backend readback](../../os/manifest/ci/11b/probe-11/two-disk/webui-probe-backend-readback.txt).
The target remained empty after preview. It then booted the original Windows-like
entry with **both ISO and empty Linux target detached**. The marker screenshot
was visually inspected: BootCurrent=0000 and the original Microsoft loader path
on protected ESP GUID `7c0a0246-ee3e-4923-9f9d-fa9bc78c85d5`.

**The mandatory NVRAM audit failed, and work stopped.** OVMF deleted existing
**Boot0002 (UEFI QEMU DVD-ROM QM00001)** and **Boot0004 (UEFI Misc Device 2)**,
removing their IDs from BootOrder. `compare_nvram` raised
**`PRODUCT FAILURE: existing boot entry changed`**. Windows Boot0000 was
byte-identical and remained first. This happened **before installation**, so
it does not demonstrate an Anaconda/AresOS write to the Windows-like disk or
loss of Windows Boot Manager. It does demonstrate failure of the brief's strict
existing-entry preservation contract. No entry deletion was exempted, no
predicate/test weakened, and no VM/full dispatch followed.

The initial protected capture and all three final-run offline stage captures
match the same SHA-256, GPTs, partition identities/bounds and EFI files:

```text
32d28d0aee688053d36c31deb3a1288ca15defce2aeed5c4b380644fbd12c036
```

All three final-run shutdown counter records have **wr_bytes=0,
wr_operations=0**. Byte equality and zero writes are separate evidence; neither
makes the failed NVRAM audit green. The failed detached stage saved raw NVRAM
JSON and the original variable store before the assertion; it could not save
the normal computed diff after that assertion. The derived
[stop analysis](../../os/manifest/ci/11b/nvram-stop-analysis.json) retains both
changed entries, labels and BootOrder arrays without altering those originals.

| Gate | 11b result | Evidence |
|---|---|---|
| Real first-order Web UI pages/review | **Preview passed; installation not qualified** | [Latest review screenshot](screenshots/11b-probe-11-two-disk-review-full.png), [text](../../os/manifest/ci/11b/probe-11/two-disk/review-full.txt), [target-only/new-EFI proof](../../os/manifest/ci/11b/probe-11/two-disk/review-proof.json) |
| German and backend choices | **Preview passed** | [German proof](../../os/manifest/ci/11b/probe-11/two-disk/webui-keyboard-proof.json), [readback](../../os/manifest/ci/11b/probe-11/two-disk/webui-probe-backend-readback.txt), [served bundle/map qualification](../../os/manifest/ci/11b/probe-11/two-disk/completion-selector-source.json) |
| Complete same-commit probe / full authorization | **FAILED; no full authorized** | [Run 39892768284](https://github.com/carlsenares/AresOS/actions/runs/39892768284), [failure log](logs/11b/probe-11.txt); no passing complete probe-result JSON |
| Existing firmware entries | **FAIL — stop** | [Baseline](../../os/manifest/ci/11b/probe-11/two-disk/baseline-firmware-nvram.json), [after detached boot](../../os/manifest/ci/11b/probe-11/two-disk/probe-windows-without-linux-nvram.json), [derived diff](../../os/manifest/ci/11b/nvram-stop-analysis.json); original `.fd` stores beside JSON |
| Protected bytes/GPT/EFI and writes | **Passed at reached pre-install stages only** | [Initial](../../os/manifest/ci/11b/probe-11/two-disk/protected-baseline.json), [final detached](../../os/manifest/ci/11b/probe-11/two-disk/probe-windows-without-linux-protected.json), [final counters](../../os/manifest/ci/11b/probe-11/two-disk/probe-windows-without-linux-blockstats.json) |
| Original Windows-like path without Linux | **Pre-install boot passed; post-install/post-undo OPEN** | [Marker text](../../os/manifest/ci/11b/probe-11/two-disk/probe-windows-without-linux-marker.txt), [screenshot](screenshots/11b-probe-11-two-disk-probe-windows-without-linux-windows-marker.png) |
| A: both installs, switch/policy/tty3/rollback/default undo | **NOT REACHED / OPEN** | Probe stopped before target reset/reverse order; target remained empty; no installation or full run |
| B: one-time GRUB stock, promotion, unattended stock boot | **UNTESTED; blocked by missing installed target** | No GRUB/menu transaction started; INSTALL/EMERGENCY retain the open gate |
| C: media pins | **DONE, unchanged** | Original package-11 evidence above; repeated complete live ISO hashes still match the frozen pin |
| Physical media, novice, Windows OS and laptop | **OPEN** | File-backed marker and host Chromium are not a physical Windows/USB/keyboard/hardware rehearsal |

Final [minute ledger](../../os/manifest/ci/11b/final-budget.json): **168/350
rounded GitHub Actions job minutes, 0/3 full dispatches**. All 12 follow-up
dispatches are included, including cancelled setup and source-only inspection;
other image/switch jobs were skipped. **182 minutes remain unused because the
stop rule fired, not because the budget was exhausted.** The original package-11
allowances above are historical and separate. No new checks-only or VM job was
started after the stop.

Local commands actually run during 11b:

```text
python -m unittest discover -s os/tests -p test_installer_webui.py -v
  latest source: Ran 9 tests in 0.003s; OK
python -m unittest discover -s os/tests -p test_two_disk_vm.py -v
  latest affected source: Ran 18 tests in 0.220s; OK
python -m unittest discover -s os/tests -p test_disk_audit.py -v
  Ran 6 tests in 0.158s; OK
python -m py_compile os/ci/installer_webui.py os/ci/two_disk_vm.py
  exit 0
python reviews/11-two-disk-rehearsal/verify-11b-evidence.py
  artifact/log receipt hashes and expanded contents checked; display whitespace normalized
  19 matching offline stages; 17 zero-write records; 2 missing final records
  685 expanded text/JSON credential-pattern checks passed
  1337 raw archived UTF-8 credential-pattern checks passed
  1 strict NVRAM failure; REHEARSAL NOT QUALIFIED; exit 1
git diff --cached --check
  exit 0; no whitespace errors
```

The [verification log](logs/11b/evidence-verification.txt) deliberately remains
non-green. Probes 1 and 3 have byte/layout/EFI equality but no final live-VM
counter record after host termination; those missing records are never used as
zero-write evidence. Each fresh fixture has its own initial hash, so comparison
is within a run, not between unrelated random GPT/NTFS fixtures. Original ZIPs
are byte exact. Display text has line endings/trailing whitespace normalized,
including four extracted live-script/defaults filenames; the verifier compares
the complete normalized contents against their raw archived originals. Other
expanded files must be byte-identical.
The repeated 33 MB complete ISO file inventories remain in each original ZIP;
their optional expanded display copies are ignored to keep the review usable.
The [capture helper](capture-11b-evidence.py) and
[verification script](verify-11b-evidence.py) are retained for review.

The signed release/base/runtime/config/key/lock inputs and `mod/` are unchanged.
No image rebuild/publication, visibility change, owner registry token, local VM,
physical disk/firmware/Windows-setting operation, system install, Gradle or
Minecraft command occurred. No Gradle daemon was started. PR #11 remains draft;
acceptance is not met. Physical installation remains **NOT RELEASED**.

### Not verified

No target installation, reversed-order live preview/install, installed UID or
console, switch/policy/real tty3/rollback/default undo, installed/undone Windows
independence, one-time GRUB stock selection or recovery promotion was reached.
The only detached Windows-like boot is pre-install and uses our marker, not
Windows itself. No D-Bus installation fallback was used. Physical media,
physical keyboards/GRUB, novice followability, Windows/BitLocker/UEFI helpers,
Lenovo fitting and laptop hardware/safety gates remain open.

### JUDGMENT-CALL

No runtime/product-feel change. The browser-tree pause preserves ordinary
liveinst/backend lifetime while replacing the active browser; it is recorded
as a browser difference. The strict NVRAM contract is applied even to automatic
firmware-created entries. Exempting those deletions or silently reconstructing
entries would change the agreed qualification rule, so neither was done.

### PLAN-GAP

Detaching the ISO and empty target makes this OVMF fixture prune their existing
boot options, while the current contract permits only a separate Linux entry
addition/reordering. The probe exposed this conflict before installation or a
full allowance. This is a fixture/firmware-contract blocker; it must not be
misreported as evidence that installed AresOS changed Windows. A future scoped
continuation needs an integrator decision on a faithful fixture or explicit
NVRAM contract before further qualification, with the Windows entry/disk/write
checks preserved.

### Open questions

How should the fixture meet the existing-entry contract when devices are
removed and OVMF prunes their automatic options? This run makes no exception.
Parts A/B and the human/hardware gates remain open; do not merge or install.


## 11c: firmware contract and fresh install qualification (2026-10-23)

History note: the owner rewrote history at 09:34 UTC. The original 11/11b
run IDs, archives and source SHAs above remain historical evidence. The
[old-to-new source map](../../os/manifest/history-rewrite-11c.json) matches
all 19 captured harness source commits by exact subject; for example
`24118e1` -> `ce661cb`, `f32f1da` -> `b9f028c`, `bf5c98d` -> `aed3d3e`.
The original release source `5578ab2` belongs to the squashed package-06
history: rewritten `f5bb5d3` has identical runtime payload trees. The release
manifest, signed image and original CI evidence retain their original IDs.
The canonical repository is now `Ares-Empire/AresOS`; only the rewritten
package branch is pushed, without force. No `pre-rewrite/*` ref is pushed.

### Done

- `disk_audit.py`: parse bounded EFI load options and accept firmware ownership
  only for exactly the 16-byte EDK2 GUID. Resolve Q35 PCI/SATA hardware, require
  actual per-boot attachment evidence, reject existing-option mutations and
  preserve other entries' relative order. Windows byte identity, BootOrder
  membership/default, protected bytes/GPT/EFI and zero-write requirements remain
  mandatory. Linux additions must name the target's new ESP and Fedora loader.
- `two_disk_vm.py`, `switch_vm.py`: record raw QMP PCI/block inventories for each
  boot, bind explicit storage addresses before detaching devices, preserve empty
  PCI slots, compare each audited stage to its predecessor, and list every
  exemption with device/reason. Both drive orders now contain the full Part A
  sequence, including both detached-Windows checkpoints; Part B follows both.
  **These fresh VM paths were not reached and are not qualified.**
- `install-tools.sh`, `firmware_contract.py`: obtain patched edk2 source for the
  exact installed Ubuntu OVMF package from authenticated snapshot indexes.
  Verify the GUID and exact-size predicate before VM work; retain the version,
  source/firmware hashes and predicate excerpt. Native regressions consume the
  original 11b raw stores and all requested negative mutations.
- `verify_release.py`: preserve the original signed image/run identity while
  fetching only rewritten main and pinning its equivalent runtime Git objects.
  Preflight the private manifest with the ephemeral job token before the ISO.
  `rehearsal_guard.py` has a separate 330-minute/three-full-run ledger, counts
  privacy jobs, and requires a complete passing same-commit probe for full runs.
- Copied main's privacy workflow/config, added API identity redaction to the
  11c capture helper, retained original artifact/log ZIP receipts, and added an
  independent evidence verifier. Main's privacy workflow is kept byte-identical so both additions merge cleanly.
  Closing scans have a fourteen-minute reservation and a five-minute per-job
  cancellation watchdog, plus cleanup allowance; no VM retry is made.
- INSTALL/EMERGENCY explain that unplugged devices' automatic F12 entries can
  disappear normally. Their installation/recovery gates remain closed/open as
  appropriate; neither a native regression nor an earlier preview is called an
  installation rehearsal.

### Verified and stop

First ran `git fetch` and `git log` as requested. Pushes used only the
rewritten package branch, fast-forward only. No merge or pre-rewrite ref push.

Fresh probe [39989739478](https://github.com/Ares-Empire/AresOS/actions/runs/39989739478)
used commit **`3babb48359291853a48f9f668c01810476a78d17`**. The runner printed:

```text
OVMF exact 16-byte auto-option GUID predicate verified against installed package source
Ran 123 tests in 3.113s
OK
Qualified release source 5578ab21b880091f26bfdc2eda22dd4f304a602b; runtime payload unchanged
AssertionError: BLOCKED: existing private release is inaccessible to the ephemeral job token; no owner token or visibility change permitted
```

The [registry preflight](../../os/manifest/ci/11c/probe-1/private-registry-preflight.json)
records the actual error: **`reading manifest sha256:362af9b7d2a5573363d2cc441505dd076603d1d96c1b5c01af55589db2b6c402 in ghcr.io/carlsenares/aresos: manifest unknown`**.
This establishes that the pinned reference could not be resolved with that job's
credentials. It does **not** distinguish removal from an access/namespace issue.
No image layer was pulled. ISO inspection, disk preparation and VM steps were
skipped. No complete probe proof exists; no full run was dispatched. The exact
[failed-step log](logs/11c/probe-1.txt) and original artifact/workflow ZIPs under
[artifacts](artifacts/) are retained with API digests/receipts.

The [build contract](../../os/manifest/ci/11c/probe-1/firmware-contract.json)
binds `ovmf`/`edk2` **2024.02-2ubuntu0.10**, patched `BmBoot.c` SHA-256
`e961d1bc0ad7df99156a030dee92585fb2608ad5722f34d494459c2f74e6f3c6`
and installed OVMF code SHA-256
`ad23261d43116abc3747d59a7837fbf578c9586a8993f4eeba064cd07eccb083`.
Its [predicate excerpt](../../os/manifest/ci/11c/probe-1/firmware-contract-source.txt)
requires both GUID equality and `OptionalDataSize == sizeof(EFI_GUID)`.
The upstream [EDK2 implementation](https://github.com/tianocore/edk2/blob/edk2-stable202402/MdeModulePkg/Library/UefiBootManagerLib/BmBoot.c)
also documents the predicate; runner qualification used the exact Ubuntu source.
The historical baseline's ownership bytes were checked from the original raw
stores; **no new VM baseline was reached**.

| Gate | 11c result | Evidence |
|---|---|---|
| Exact firmware ownership / requested regressions | **Native PASS** | [Raw-store regression](../../os/manifest/ci/11c/probe-11-regression.json), `test_disk_audit.py`; exactly Boot0002 and Boot0004 removals. Windows loss/change/OptionalData, attached removal, wrong hardware, non-auto removal, unknown addition, GUID-plus-extra bytes and auto mutation remain failures |
| GUID against installed runner build | **PASS; fresh baseline OPEN** | [Source/binary contract](../../os/manifest/ci/11c/probe-1/firmware-contract.json), [excerpt](../../os/manifest/ci/11c/probe-1/firmware-contract-source.txt), original raw-store regression |
| Rewritten runtime equivalence | **PASS** | Successful fetch of `f5bb5d3`, pinned runtime objects and unchanged payload diff in [probe log](logs/11c/probe-1.txt) |
| Existing private signed release access | **BLOCKED — stop** | [Exact manifest response](../../os/manifest/ci/11c/probe-1/private-registry-preflight.json); no token, visibility or image workaround |
| Fresh complete probe / full authorization | **FAIL; no full authorized** | [Probe run](https://github.com/Ares-Empire/AresOS/actions/runs/39989739478); UI and VM steps skipped; no probe-result file |
| A: complete installs/switch/policy/tty3/rollback/undo in both orders | **OPEN — not reached** | No disposable disks or VM boot in 11c; no fresh offline snapshots or zero-write records |
| A: Windows detached after install and undo, both orders | **OPEN — not reached** | Only historical pre-install marker evidence exists; no installed target |
| B: QMP one-time stock / identity promotion / unattended stock | **UNTESTED; clear blocker** | No installed target; pinned release unresolved; guide gate remains open |
| C: media pins | **DONE previously, no new download** | Original package-11 receipts and manifests retained |
| Privacy | **Harness HEAD PASS; closing HEAD required** | [Push scan 39989537420](https://github.com/Ares-Empire/AresOS/actions/runs/39989537420), [PR scan 39989544924](https://github.com/Ares-Empire/AresOS/actions/runs/39989544924). Final HEAD scan URLs/status are recorded on [PR #11](https://github.com/Ares-Empire/AresOS/pull/11) after the closing push |
| Physical media / novice / real Windows / laptop | **OPEN** | No physical or owner-system qualification performed |

Exempted firmware changes, listed per stage:

| Stage | Option | Hardware and reason |
|---|---|---|
| Historical 11b probe 11 baseline -> detached boot, **regression only** | Boot0002 | `pci:00:1f.2/sata:0:65535:0`; exact-GUID firmware option removed after DVD detachment |
| Same historical stage, **regression only** | Boot0004 | `pci:00:03.0`; exact-GUID firmware option removed after empty-target detachment |
| Fresh 11c probe | **None** | No VM stage was reached; no new exemption or protected-disk result is claimed |

The [derived regression record](../../os/manifest/ci/11c/probe-11-regression.json)
identifies both original raw-store hashes and its historical topology context.
Fresh runs require QMP evidence rather than these historical fixture facts.
No historical evidence file was edited.

Actual local checks are saved in [local-regressions.txt](logs/11c/local-regressions.txt):

```text
python -X utf8 -m unittest discover -s os/tests -p test_disk_audit.py -v
  Ran 11 tests in 0.233s; OK
python -X utf8 -m unittest discover -s os/tests -p test_two_disk_vm.py -v
  Ran 19 tests in 0.229s; OK
python -X utf8 -m unittest discover -s os/tests -p test_installer_webui.py -v
  Ran 9 tests in 0.003s; OK
python -X utf8 -m unittest discover -s os/tests -p test_firmware_contract.py -v
  Ran 1 test in 0.000s; OK
python -X utf8 -m unittest discover -s os/tests -p test_rehearsal_budget.py -v
  Ran 1 test in 0.000s; OK
Python compilation of every os/ci/*.py: exit 0
python -X utf8 reviews/11-two-disk-rehearsal/verify-11c-evidence.py
  Original archive receipts/expanded contents and source predicate verified
  76 archived UTF-8 credential-pattern checks passed
  0 fresh offline stages, 0 zero-write records, 0 fresh exemptions
  Evidence consistency verified; no VM qualification claimed
```

An earlier local negative regression matched the wrong error-message substring;
that new test was corrected to require the actual detached-device rejection.
An initial PowerShell wildcard `py_compile os/ci/*.py` invocation failed because
Python received a literal wildcard; the explicit file iteration above passed.
The full native suite and Bash syntax checks ran on Ubuntu in the probe.
No Gradle/Minecraft command or daemon was started, as the brief requires.

The first new privacy push/PR scans each found one false positive: the Git tree
ID of the verification-key directory, assigned under the path `os/keys` in
`verify_release.py`. `.gitleaksignore` names **only that historical commit/file/
rule/line fingerprint**. New pins put object IDs before paths. No file, rule or
credential category was broadly excluded. A checksum-verified portable gitleaks
8.21.2 under ignored `.work/` passed locally; it was not installed system-wide.
Captured API author/committer identities use the rewrite's placeholders; original
ZIP receipts stay byte exact. Display text normalizes line endings and trailing
whitespace; the verifier compares the complete normalized expanded contents.
Final GitHub scans must pass before this run ends.

### Minute ledger

[Separate 11c ledger](../../os/manifest/ci/11c/final-budget.json), rounded up
**per executed job**, includes all branch workflows since 16:21 UTC:

| Run | Result | Rounded minutes |
|---|---|---:|
| 39986075815, initial PR privacy | success | 1 |
| 39989148428, first push privacy | false-positive failure | 1 |
| 39989156330, first PR privacy | false-positive failure | 1 |
| 39989537420, corrected push privacy | success | 1 |
| 39989544924, corrected PR privacy | success | 1 |
| 39989739478, fresh probe | blocked at manifest preflight | 7 |
| 39991834967, first closing push privacy | success; workflow timeout line conflicted with main | 1 |
| **Measured before final closing push** | **0/3 full dispatches** | **13/330** |
| Closing push + PR privacy pair | reserved; five-minute watchdog plus two-minute cleanup allowance per job | **at most 14** |
| **Bound including closing checks** | final actual total/scan URLs recorded in PR description | **at most 27/330** |

The closing reservation avoids another evidence-only push creating an unrecorded
scan pair. The final PR description records the completed closing runs and exact
actual total. At least 303 minutes of the cap remain unused: the release blocker
stopped work, not budget exhaustion. No additional VM, full or checks-only run
followed the failed preflight. The timeout line initially added to the independently
created privacy workflow produced an add/add conflict with main and prevented a
new PR-context scan. Restoring main's exact file resolves that conflict through a
normal follow-up commit; no merge, rebase or force-push was used.

### Not verified

No fresh baseline/device-path classification in OVMF, either-order Web UI preview,
installation, target ESP, installed account/keymap, switch/policy/tty3 recovery,
rollback/default undo, or post-install/post-undo Windows independence was reached.
The expanded complete reverse-order sequence and per-boot QMP inventories remain
regression-qualified source only. Part B is blocked before GRUB/menu/promotion.
Physical USBs, keyboard, novice followability, real Windows/BitLocker/UEFI helpers,
Lenovo fitting and laptop hardware remain open. Physical installation is NOT RELEASED.

### JUDGMENT-CALL

The ownership exception implements the integrator's exact 11c decision. The
fixture now fixes PCI identities so removing storage cannot make VGA/USB occupy
its address; automatic reassignment would make a label-independent comparison
ambiguous. This is a disposable harness choice, not a product/firmware change;
changing it later requires adapter regression updates and a new probe. No new
product-feel or hard-to-undo decision was made.

### PLAN-GAP

The brief assumes the recorded signed private image is available. GHCR returned
`manifest unknown` to the ephemeral `packages:read` job token after the history/
repository transition. The response does not establish the cause. Rebuilding,
republishing, changing visibility, substituting another image or obtaining an
owner token is outside this brief. Restoring access to the exact recorded signed
reference, or an explicit new release decision, is required before a new scoped
qualification. The firmware rule is not widened and no full allowance is spent
trying installation without a complete probe.

### Open questions

Does the exact pinned manifest still exist under its recorded GHCR reference,
and can the repository's ephemeral job token read it? This needs a maintainer
registry/access decision outside the run. Parts A/B require fresh qualification
after that blocker is resolved. Acceptance is not met: PR #11 remains draft,
the branch is pushed fast-forward only, and nothing is merged.


## 11d: owner read-only token and continued qualification (2026-10-24)

**STOPPED — firmware-contract PLAN-GAP in the fresh probe. A OPEN, B UNTESTED,
C pins retained.** [Probe 40038465601](https://github.com/Ares-Empire/AresOS/actions/runs/40038465601)
on source **`31879417304d2ca584fe7e5f6b0de9555f4dd0ae`** reached the live Web UI
review and pre-install detached Windows boot in both drive orders. Reverse-order
OVMF then removed an automatic option for a still-attached protected device and
changed an existing automatic option. Both are explicitly forbidden by 11c.
The unchanged guard failed; no exemption was widened, no full run was authorized,
and no further VM or checks-only dispatch followed. PR #11 remains draft.

### Done

The owner authorized Actions secret `GHCR_READ_TOKEN` solely for reading the
original pinned `ghcr.io/carlsenares/aresos` image, its layers and associated
signature, using username `carlsenares`. The declared scope is classic
`read:packages`, expiring after 30 days. No owner-token GitHub API call is made.
The org job token remains separate for CI/run metadata.

Only an explicit workflow-dispatch probe/full step receives the secret in its
environment. It writes one root-owned, package-scoped mode-0600 auth file under
`RUNNER_TEMP/aresos-11d-ghcr`, outside the workspace and all artifact paths.
The VM reads that same host file over a read-only 9p share at fixed PCI 6.0;
its `/etc/ostree/auth.json` is a symlink to the mounted temporary file, so no
credential value is sent through a console command or written to a guest disk.
Registry-client output is private; exported proofs contain fixed image/identity
fields only. An always-cleanup step deletes the host auth file before artifacts.
Missing/rejected credentials fail closed with no job-token or anonymous fallback.

The probe now qualifies the exact layer pull as well as the manifest and the
same signature/identity script used for switching. Full authorization also
requires the probe artifact's passing manifest/pull proofs and cleanup receipt.
The old user-package metadata step records that visibility cannot be queried
with the org job token; it no longer treats a 404 as success or absence.

Parts A/B remain OPEN after the firmware stop. The allowance is shared with
11c: 17 rounded minutes were already consumed at entry, including the two
checks on the new brief. The final measured cost before closing privacy checks
is 66/330; no full run has been dispatched.


The first 11d probe was cancelled during setup when source review identified
that a runner-owned 9p export could have the same UID as future `ares` (1001).
No full run was authorized. Credential creation/read/cleanup now execute as
root on the disposable runner; the guest requires root ownership of both share
root and file, in addition to read-only mode and 0600. A negative regression
rejects UID 1001 and relaxed permissions. A new same-commit probe was required.


Probe 2 (`40036342487`, source `a8c77f7`) passed 132 native tests in 3.296s,
verified the OVMF source contract, resolved/pulled the exact private digest,
removed the OCI cache, and verified the complete pinned ISO (9,068,650,496 bytes).
It then stopped in the QMP inventory adapter before establishing the first
firmware baseline: IDE reports `qdev=installer-cd-device`, while the guard had
expected a path suffix. This is a harness schema mistake, not an observed EFI
option mutation. The guard now requires the exact real IDE ID; all PCI/SATA/file
binding checks remain. A replay regression consumes the original raw QMP record
and rejects a different ID. Cleanup passed; no full run is authorized and no
fresh firmware/disk stage is claimed for probe 2. The fresh same-source probe 3
then reached the real firmware behavior described below and triggered the stop.

Nine `test_rehearsal_auth.py` regressions cover dispatch-only secret scope,
outside-workspace/artifact paths, always-cleanup ordering, UID/mode protection,
fail-closed contexts/reads, and suppressed credential diagnostics. Workflow/tool
setup includes the YAML parser for these checks. The QMP replay regression
preserves all PCI/SATA/file bindings and rejects a different IDE identifier.
No mod/runtime payload, image/base/key/lock, release signature script or
disk-audit contract was changed in 11d. No rebuild, publication, visibility
change, Gradle/Minecraft or real-disk operation occurred.

Captured API identities use the rewrite's placeholders. Original ZIPs stay byte
exact with API digest receipts; readable text alone normalizes line endings and
trailing whitespace. The capture helper scans uncompressed bytes, including
encoded token patterns, and rejects auth-file contents before retention.
`verify-11d-evidence.py` independently checks receipts, raw stores, QMP context,
the original contract, disk/counter proofs, review and keyboard data. It records
the strict firmware failure and exits **1**, never qualifying it. INSTALL and
EMERGENCY now describe this firmware stop; installation/GRUB gates stay open.
Original 11/11b/11c evidence is retained.

### Verified

The required first commands, `git fetch` and `git pull --ff-only`, completed;
pull printed `Already up to date.` Pushes use the normal branch ref: no
force-push, pre-rewrite ref, main push, merge or rebase was used.

| Gate | Result and evidence |
|---|---|
| Pinned release access | **PASS** [manifest](../../os/manifest/ci/11d/probe-3/private-registry-preflight.json) and [all-layer pull](../../os/manifest/ci/11d/probe-3/owner-release-pull.json), preserved digest `sha256:362af9b7d2a5573363d2cc441505dd076603d1d96c1b5c01af55589db2b6c402`; OCI cache removed. Metadata visibility explicitly unverified. |
| Original signed identity/runtime | **PASS** unchanged release checks on old source `5578ab21b880091f26bfdc2eda22dd4f304a602b`, equivalent rewritten source `f5bb5d35dac73e95ce2bc6680ae61f20d042f5b7`. Original `os/release/verify.sh` succeeds in [first order](../../os/manifest/ci/11d/probe-3/two-disk/live-release-signature-proof.json) and [reverse order](../../os/manifest/ci/11d/probe-3/two-disk/protected-second/live-release-signature-proof.json); identity stays `https://github.com/carlsenares/AresOS/.github/workflows/os-image.yml@refs/heads/pkg/06-image-release`, issuer `https://token.actions.githubusercontent.com`. |
| Credential boundary/cleanup | **PASS reached live stages**: [first mount](../../os/manifest/ci/11d/probe-3/two-disk/boot-2-owner-auth-mount.txt), [reverse mount](../../os/manifest/ci/11d/probe-3/two-disk/protected-second/boot-5-owner-auth-mount.txt), [always-cleanup receipt](../../os/manifest/ci/11d/probe-3/owner-auth-cleanup.json); removed before upload. Zero owner-token API calls; installed-target transport unqualified. |
| Exact firmware contract | **PASS source/baselines** [OVMF receipt](../../os/manifest/ci/11d/probe-3/firmware-contract.json): `2024.02-2ubuntu0.10`, exact 16-byte auto GUID checked against patched package source and both actual baseline stores. CODE SHA-256 `ad23261d43116abc3747d59a7837fbf578c9586a8993f4eeba064cd07eccb083`; BmBoot.c SHA-256 `e961d1bc0ad7df99156a030dee92585fb2608ad5722f34d494459c2f74e6f3c6`. |
| Native regressions | **PASS** 133 tests in 3.463s, `OK`; Python compilation and Bash syntax checks exit 0 in [same-source probe log](logs/11d/probe-3-native-and-auth.txt). |
| Complete pinned live ISO | **PASS** [9,068,650,496-byte download](../../os/manifest/ci/11d/probe-3/installer/iso-download.json), SHA-256 `776b76f3417723440ee1823d79ec02a2c22860df196d219024edb062ad00d8e6`, unchanged pin and fresh official checksum. |
| Real two-order Web UI preview | **PASS preview only** [first review](../../os/manifest/ci/11d/probe-3/two-disk/review-proof.json), [reverse review](../../os/manifest/ci/11d/probe-3/two-disk/protected-second/review-proof.json). Only target rows: new 629 MB EFI `/boot/efi`, 2.15 GB ext4 `/boot`, Btrfs `/`, `/home`, `/var`. No protected row or install click. Backend selection, Europe/Berlin, recovery account wheel/password/root lock and German keyboard resolver proofs retained. |
| Protected disk/Windows through reached stages | **PASS reached stages only** [verification](../../os/manifest/ci/11d/evidence-verification.json): six identical offline captures, six final write records `wr_bytes=0`, `wr_operations=0`, no missing counter. Windows Boot0000 remains byte-identical and first. Both pre-install detached Windows markers boot the original Microsoft path. |
| Reverse detached firmware entries | **FAIL / STOP** [raw before](../../os/manifest/ci/11d/probe-3/two-disk/protected-second/live-ui-probe-vars.fd), [raw after](../../os/manifest/ci/11d/probe-3/two-disk/protected-second/probe-windows-without-linux-vars.fd), [derived changes + full per-boot QMP contexts](../../os/manifest/ci/11d/firmware-stop-analysis.json). See stage table below. |
| A: both installations/switch/policy/tty3/rollback/default undo; Windows detached after install/undo | **OPEN**: no complete passing probe, no full run, no installed target. Pre-install markers are not these gates. |
| B: actual GRUB stock selection/promotion/unattended stock | **UNTESTED / BLOCKED** by failed probe and absent installed target. No menu/identity/promotion proof claimed. |
| C: media pins | **RETAINED**, fresh complete live ISO verified; no media substitution. Physical USB/writer operation remains OPEN. |
| Privacy | Captured source scans green: [push](https://github.com/Ares-Empire/AresOS/actions/runs/40038275064), [PR](https://github.com/Ares-Empire/AresOS/actions/runs/40038279622). Main's privacy workflow/config remain byte-identical. Final closing scan URLs/results and exact shared minutes go in PR #11 after the final push. |

All six offline records retain protected SHA-256
`3f45ca070eaeda0e059af7e7b505aac9b549a097134243a21c8995f01767e111`,
validated primary/backup GPT, partition GUIDs/bounds and complete EFI hashes.
Both detached marker frames show `BootCurrent=0000`, original ESP GUID
`638D3069-A6B2-4FCB-9D97-01ABA3ECC83A`, and
`\EFI\Microsoft\Boot\bootmgfw.efi`; only PCI address differs (2.0 versus 3.0).
This is file-backed VM fixture evidence, not a real Windows boot test.

Visually inspected [first full review](screenshots/11d-probe-3-two-disk-review-full.png),
[reverse full review](screenshots/11d-probe-3-two-disk-protected-second-review-full.png),
and [first](screenshots/11d-probe-3-two-disk-probe-windows-without-linux-windows-marker.png)
and [reverse](screenshots/11d-probe-3-two-disk-protected-second-probe-windows-without-linux-windows-marker.png)
detached marker frames. Target is `vdb` first and `vda` in reverse; these are
same-session identities, never physical-guide device assumptions. Destination
frames include transient loading/disabled states; the complete validated review
is the final preview evidence.

### Firmware exemptions and failure per stage

Every auto option below has exactly GUID bytes
`4eac0881119f594d850ee21a522c59b2`; labels do not decide attachment.

| Order / stage | Exemption or result |
|---|---|
| Protected first / baseline firmware | Baseline established, original Windows Boot0000 unchanged, actual QMP ownership saved. No transition exemption. |
| Protected first / live-ui-probe | Diff `{}`, exemptions `{}`. |
| Protected first / detached Windows | **Exactly two accepted removals:** Boot0002 for detached DVD `pci:00:1f.2/sata:0:65535:0`, Boot0004 for detached empty target `pci:00:03.0`. Each stage record names its device and reason. BootOrder otherwise preserves fixed order, Windows first. |
| Protected second / baseline firmware | Baseline established, original Windows unchanged, target at PCI 2.0 and protected at PCI 3.0. No transition exemption. |
| Protected second / live-ui-probe | Diff `{}`, exemptions `{}`. |
| Protected second / detached Windows | **FAIL, no accepted exemption record:** Boot0004 removed while protected `pci:00:03.0` is still attached. Boot0002 changed from DVD/SATA to protected PCI 3.0 (forbidden existing-entry mutation/ID reuse). Boot0003 removed for detached target PCI 2.0 would individually fit the rule, but cannot make the stage pass. Raw stores, JSON and QMP context were saved before the assertion. |

The actual runner printed
`AssertionError: PRODUCT FAILURE: auto option removal does not match a detached device`.
Independent raw decoding also shows the forbidden Boot0002 change. Reverse
BootOrder changed from `0000,0001,0002,0003,0004,0005,0006,0007,0008,0009` to
`0000,0001,0005,0006,0007,0008,0009,0002`. Windows remains first, but this
renumbering/recycling is outside the authorized rule. No entry was reconstructed
or renumbered by the harness to pass the audit.

Actual commands/results (full output in retained logs/ZIPs):

```text
Windows focused unittest discovery, os/tests (local-regressions.txt):
  test_rehearsal_auth.py: initially 8 in 0.075s, OK; after UID fix 9 in 0.065s, OK
  test_disk_audit.py, test_two_disk_vm.py, test_installer_webui.py,
  test_firmware_contract.py, test_rehearsal_budget.py: all OK
  after QMP replay fix, test_two_disk_vm.py: 20 in 0.274s, OK
  Python compilation of every os/ci/*.py: exit 0
Ubuntu probe 40038465601:
  python3 -m unittest discover -s os/tests -v
    Ran 133 tests in 3.463s; OK
  python3 -m py_compile os/ci/*.py os/ci/overlay/*.py
    exit 0
  for script in os/ci/*.sh os/release/*.sh; do bash -n "$script"; done
    exit 0
  python3 os/ci/verify_release.py 39818554327
    Qualified release source 5578ab21b880091f26bfdc2eda22dd4f304a602b;
    runtime payload unchanged; testing the original pinned image
  sudo -E python3 os/ci/rehearsal_auth.py create / preflight / pull
    separate steps: temporary file created; pinned digest verified;
    exact layers pulled with preserved digest
  python3 os/ci/installer_inspect.py
    exit 0; complete ISO matched original pin
  sudo -E .work/browser-env/bin/python os/ci/two_disk_vm.py probe
    exit 1; PRODUCT FAILURE: auto option removal does not match a detached device
  sudo -E python3 os/ci/rehearsal_auth.py cleanup (always)
    Runner-temporary GHCR_READ_TOKEN auth file removed; success before upload
Retained-evidence verification:
  python -X utf8 reviews/11-two-disk-rehearsal/verify-11d-evidence.py
    exit 1; 6 matching offline stages, 6 zero-write records, no missing counters
    2 accepted first-order exemptions; reverse firmware failure retained
    648 archived UTF-8 records checked, raw/encoded credential checks passed
    STOP: retained firmware contract failure; probe/full qualification is absent.
  python -X utf8 os/ci/rehearsal_guard.py ledger 0
    66 consumed minutes, full_dispatched=0, cap=330, full_cap=3
  gitleaks.exe git . --pre-commit --staged --redact --no-banner --log-level info
    exit 0; no leaks found in staged evidence
  gitleaks.exe git . --log-opts HEAD --redact --no-banner --log-level info
    exit 0; 94 rewritten-HEAD commits scanned, no leaks found (before report commit)
```

[Local regressions](logs/11d/local-regressions.txt),
[native/auth log](logs/11d/probe-3-native-and-auth.txt),
[failed VM step](logs/11d/probe-3.txt),
[verifier output](logs/11d/evidence-verification.txt).
No test was weakened, skipped or deleted. No Gradle/Minecraft command or daemon
was started, as this brief explicitly prohibits them.
The checksum-verified portable gitleaks 8.21.2 stayed under ignored `.work/`;
no system software was installed locally. The final report commit is scanned
again before the push, then GitHub runs the unchanged privacy workflow.

Original [probe-3 artifact ZIP](artifacts/11d-probe-3-two-disk-evidence.zip):
6,341,568 bytes, API SHA-256
`c71cf2ff3a741640124629d212d52a7708d30e3d845a1b54065a71dfbf671799`.
The [receipt](../../os/manifest/ci/11d/probe-3/artifacts.json), raw stores,
QMP/serial logs, screenshots and workflow-log ZIPs are retained. Large full
squashfs inventories stay inside original ZIPs instead of duplicated expanded
text. The verifier explicitly lists probe 2's unreached baseline; absent evidence
is not a zero-write or qualification result.

### Minute ledger

The allowance **never reset**: 11c + 11d share start **2026-10-23 16:21 UTC**,
**330 rounded minutes / 3 full runs**. Every executed branch workflow job counts,
including privacy/cancelled jobs (ceil per job; skipped jobs cost zero).
[Shared machine-readable ledger](../../os/manifest/ci/11d/final-budget.json)
lists every run, source SHA, conclusion and minute value.

| Run(s) | Result | Rounded minutes |
|---|---|---:|
| Prior 11c, including final 39992290220 / 39992295958 privacy pair | 7-minute blocked probe + 8 privacy jobs; actual carry-forward | 15 |
| 40034559047 / 40034568137 | Owner brief push / PR privacy, success | 2 |
| 40035578181 / 40035585755 | First 11d source push / PR privacy, success | 2 |
| 40035777911 / 40035784085 | OCI-cache source push / PR privacy, success | 2 |
| 40035950604, source `727d1e8` | Cancelled during setup after UID review; credential creation skipped; cleanup passed; no VM | 3 |
| 40036158941 / 40036169351 | Root-ownership source push / PR privacy, success | 2 |
| 40036342487, source `a8c77f7` | 132 native tests in 3.296s, host manifest/layers/ISO pass; IDE identifier guard fails before baseline; cleanup passed | 16 |
| 40038275064 / 40038279622 | QMP-replay source push / PR privacy, success | 2 |
| 40038465601, source `3187941` | Both-order previews/signatures/markers; reverse firmware contract fails; cleanup passed; mandatory stop | 22 |
| **Measured before closing push** | **0/3 full dispatches** | **66/330** |
| Closing push + PR privacy pair | Reserved: five-minute watchdog plus two-minute cleanup allowance per job | **at most 14** |
| **Bound including closing checks** | Final exact actual total and scan URLs in PR description | **at most 80/330** |

The reservation avoids an endless evidence-only push/scan loop. Final actual
accounting is updated in PR #11 after final checks, without another commit
creating checks. At least 250 minutes stay unused within this bound: firmware,
not budget exhaustion, stopped installation. Zero full runs were attempted.
No VM, full or checks-only dispatch followed the firmware failure; only required
closing privacy checks run afterward.

### Not verified

No installation, installed UID/group/keymap/encryption result, post-install
target ESP, switch/policy/real tty3 recovery, rollback/default undo, or Windows
boot with Linux detached after install/undo was reached in either order.
Installed-target token mount/switch/cleanup paths remain unqualified. Part B has
no actual installed GRUB menu, selected stock identity, promotion or unattended
stock boot. No complete passing probe result exists. Physical USB/writer use,
novice/physical-keyboard tests, Lenovo fitting, laptop firmware/Windows/BitLocker
helpers and hardware remain human gates. **Physical installation is NOT RELEASED.**

### JUDGMENT-CALL

Root-owned read-only 9p transport was selected instead of copying a token into a
guest file or encoding it in serial commands. It adds one fixed disposable PCI
6.0 device, keeping protected/target addresses stable. This reversible CI choice
costs adapter/security regressions and a fresh probe if replaced. No new
product-feel or hard-to-undo product decision was made. Firmware ownership rules
remain exactly as the integrator set.

### PLAN-GAP

11d resolves the org-to-personal-package access gap under the explicit owner
exception. The new blocker is reverse-order OVMF automatic-option ID recycling:
an attached protected-device option disappears, and an existing DVD option is
reused for that protected device. Although Windows bytes/entry and write counters
remain correct, 11c explicitly forbids both operations. The run stops. Treating
this as an allowed rename, manipulating the store or changing fixtures to
conceal it would widen/bypass the decision and is not authorized.

### Open questions

The integrator must address the real reverse-order firmware behavior before a
new scoped qualification: a faithful fixture approach satisfying the existing
contract, or a separately authorized contract decision with exact regressions
and evidence. This run makes neither change. Parts A/B still need fresh
qualification; spare minutes do not bypass the stop. PR #11 stays draft,
branch pushes are fast-forward only, and nothing is merged.
