# Package 11: two-disk install rehearsal and pinned media

Latest 11h outcome: **PLAN-GAP STOP after checking the exact pinned installer source. A NOT QUALIFIED, B UNTESTED, C pins retained.** The resolver can permanently clear X11 options; a 15-second wait cannot restore that field. The actual cause of full 3 remains unproven because its tuples were not retained. Inspection-only run passed 162 Ubuntu regressions; no 11h VM, probe or full was dispatched. Shared ledger **336/750 measured + 14 closing privacy minutes reserved, 3/5 authorized full runs used**. PR #11 remains draft. See [11h](#11h-pinned-keyboard-source-investigation-2026-10-24).

Latest 11f outcome: **STOPPED before switch — stock has a newer upstream deployment staged; the unchanged pin guard refused it. A NOT QUALIFIED, B UNTESTED, C pins retained.** The fresh probe and 146 native tests passed; first install, Windows-default restoration/detached marker and pinned stock boot passed. Eleven offline protected captures match; ten final counters are zero and the failed stock session lacks its final counter. Shared ledger **229/600 measured + at most 14 closing privacy minutes, 2/3 full runs**. See [11f](#11f-linux-position-rule-and-full-length-qualification-2026-10-24).

Latest 11e outcome: **STOPPED after first real install — Windows-default restoration violates the strict non-firmware relative-order rule. A NOT QUALIFIED, B UNTESTED, C pins retained.** The fresh both-order probe passed; 140 native regressions passed in probe and full. All nine reached protected captures/counters were unchanged/zero, but the full audit failed. Shared cost: **142/330 measured + at most 14 closing privacy minutes, 1/3 full runs**. See [11e](#11e-firmware-device-set-rule-and-continued-installation-qualification-2026-10-24).

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

## 11e: firmware device-set rule and continued installation qualification (2026-10-24)

**STOPPED after the first real install and detached Windows marker — required
Windows-default restoration conflicts with the strict non-firmware order rule.
A NOT QUALIFIED, B UNTESTED, C pins retained.** The fresh both-order probe passed.
Full run [40046420672](https://github.com/Ares-Empire/AresOS/actions/runs/40046420672)
on the exact same source **`a353042e6f996d26a9ad746b616dce1a6394e1ae`** completed
the first real Web UI install on the target's own ESP. The protected disk and
Windows entry stayed unchanged; the detached Windows marker booted. The ensuing
audit rejected the Windows/Bazzite relative-order change. No check was widened,
no further VM/probe/full/checks-only job followed, and PR #11 stays draft.

### Done

- `os/ci/disk_audit.py`: implements the explicit 11e device-set decision. Every
  exact-GUID automatic option, including unchanged options, must resolve to
  hardware attached in its own per-boot QMP record. The saved MAC/IP/empty-URI
  HTTP options resolve to their NIC PCI address; unsupported paths fail. Number,
  description, position and the presence of an option for each attached device
  are not identity requirements. Taking a non-auto option's number still fails.
- Stage records retain raw option changes, both complete BootOrders and ownership
  inventories. Device events record removals/additions/relabels/renumbers. Pairing
  prefers unchanged numbers, then remaining options on the same physical device;
  original stores stay authoritative when one NIC has multiple options. The real
  reverse transition is exactly DVD removal, target removal and protected-option
  relabel/renumber Boot0004 → Boot0002. Historical evidence is unchanged.
- Windows entry bytes/number/default, protected bytes/GPT/EFI/counters and
  non-auto relative order stay strict. Linux additions/changes/recreation require
  the actual target ESP number, GUID/bounds and Fedora shim/GRUB loader. A
  recreation may use a former auto number but retains its logical fixed-order
  position. Wrong ESP/loader, standalone Linux removal and GUID-plus-extra fail.
- `two_disk_vm.py`, `rehearsal_guard.py`: fresh records use the set audit, and the
  same-source complete probe proof requires `firmware_rule=11e-device-set`.
  The original 330-minute/three-full allowance, 11d token boundary, original
  signature identity, digest and runtime-equivalence checks are unchanged.
- Tests and `replay-11e-firmware.py` cover the real before/after stores and all
  required rejection cases. Capture/verifier helpers retain API digest receipts,
  exact original ZIPs, raw stores, per-boot QMP and screenshots. The verifier's
  post-stop change only records the original strict rejection and its inputs;
  it still exits **1**. No VM policy or test was relaxed after the stop.
- INSTALL and EMERGENCY describe the latest blocker and leave installation and
  GRUB gates open. Protected audit/raw-store functions are byte-identical to
  the pre-11e source. Owner auth, workflow, fixture, runtime, image/base/key/lock,
  release/media pins, mod and historical evidence are unchanged. Privacy files
  remain identical to main. No image rebuild, publish or visibility change.

### Verified

First commands `git fetch` and `git pull --ff-only` completed; pull printed
`Already up to date.` All pushes are normal fast-forward branch pushes. No
force-push, pre-rewrite ref push, main push, merge or rebase was used.

| Gate | Result and evidence |
|---|---|
| Historical set rule and negatives | **PASS** [replay receipt](../../os/manifest/ci/11e/firmware-set-replays.json): 11b/11c first order and 11d first order each two removals; 11d reverse exactly three device events. 58 focused tests cover detached/unknown devices, takeover of Windows/Linux/fixed numbers, Windows mutation/renumber/default, other non-auto mutation/addition/order, wrong Linux ESP/loader and GUID-plus-extra. |
| Fresh probe before full | **PASS** [40044393400](https://github.com/Ares-Empire/AresOS/actions/runs/40044393400), [complete proof](../../os/manifest/ci/11e/probe-2/two-disk/probe-result.json), source `a353042e6f996d26a9ad746b616dce1a6394e1ae`. Both actual reviews, backend/keymap choices and detached markers passed; full used this exact source and probe ID. |
| Native/source/firmware checks | **PASS** probe: 140 tests in 3.545s; full: 140 in 4.269s, both `OK`. Python compilation/Bash syntax, unchanged runtime-equivalence checks and exact OVMF GUID source predicate/baselines passed in both jobs. |
| Owner-token reads/signature/cleanup | **PASS reached stages** original pinned manifest/all layers/digest, original signature verifier in both probe guests and full live guest; root-only read-only 9p auth mount. [Probe cleanup](../../os/manifest/ci/11e/probe-2/owner-auth-cleanup.json) and [full cleanup](../../os/manifest/ci/11e/full-1/owner-auth-cleanup.json) removed the host file before upload. Zero owner-token API calls. Visibility metadata explicitly unverified from the org. |
| Complete pinned live ISO | **PASS twice**, 9,068,650,496 bytes match existing SHA-256 `776b76f3417723440ee1823d79ec02a2c22860df196d219024edb062ad00d8e6` and fresh official checksum. No media/image substitution. |
| Real installation, protected first | **PASS installation checkpoint only** [result](../../os/manifest/ci/11e/full-1/two-disk/protected-first-install-result.json), [new target ESP/EFI files](../../os/manifest/ci/11e/full-1/two-disk/protected-first-install-target-efi.json), [completed UI](screenshots/11e-full-1-two-disk-installation-complete.png). New Bazzite Boot000A targets only target ESP `8f0f45ad-95be-4c15-a55b-9ed0352ea077`, partition 1, start 2048, 1,228,800 sectors, `\EFI\fedora\shimx64.efi`. Protected disk unchanged, zero writes. |
| First post-install Windows without Linux | **Marker PASS, combined NVRAM gate FAIL** [frame](screenshots/11e-full-1-two-disk-after-install-without-linux-windows-marker.png), [raw before](../../os/manifest/ci/11e/full-1/two-disk/protected-first-install-vars.fd), [raw after](../../os/manifest/ci/11e/full-1/two-disk/after-install-without-linux-vars.fd), [failure analysis/QMP/hash bindings](../../os/manifest/ci/11e/full-stop-analysis.json). Windows entry unchanged and first afterward; non-auto relative order changed. |
| Protected disk/counters through reached stages | **PASS all nine reached captures** [verification](../../os/manifest/ci/11e/evidence-verification.json): six probe + three full captures match their own run's baseline, nine final counters `wr_bytes=0`, `wr_operations=0`, no missing final counter. Full protected baseline SHA-256 `a63253537257b6c2ad856b77cff43506940b0457e1d3605e5fc9014bb0a2b652`; probe baseline `a11e6ce1947615205b4d4a95d4d10951a57c7a6fdd00651aa56b53316c3dea34`. Independent fixtures have independent baseline GUIDs/hashes. |
| A: both full drive-order sequences | **NOT QUALIFIED**: stopped before the first installed Linux boot/switch/policy/tty3/rollback/default undo. Reverse installation and both post-undo detached boots were not reached. Preview/marker subsets do not satisfy A. |
| B: GRUB stock selection/promotion/unattended stock | **UNTESTED / BLOCKED** by A's non-auto-order PLAN-GAP and absent qualified installed-target sequence. No menu/promotion proof claimed. |
| C: media pins | **RETAINED**; fresh complete live ISO verified twice. Physical media/writer/followability remain OPEN. |
| Privacy | Both source `a353042` [push](https://github.com/Ares-Empire/AresOS/actions/runs/40044245505) / [PR](https://github.com/Ares-Empire/AresOS/actions/runs/40044249975) scans green. Final closing scan results/URLs and exact actual cost are recorded in PR #11 after the final push. |

The original 11d token exception remains narrow: Actions secret `GHCR_READ_TOKEN`,
username `carlsenares`, owner-declared classic `read:packages`, 30-day expiry,
only `ghcr.io/carlsenares/aresos@sha256:362af9b7d2a5573363d2cc441505dd076603d1d96c1b5c01af55589db2b6c402`
and its associated signature reads. Only dispatch probe/full creation receives
the secret in env; the file stays under RUNNER_TEMP, root-owned 0600 in a 0700
directory outside workspace/artifacts. No other package, owner API, credential
fallback or mutation. Client diagnostics are private; artifact capture and
verification scan raw bytes and encoded credential patterns, including binary
entries. No value is retained. Original old-source signature identity and
issuer stay as recorded in release.json; no image/key/runtime change.

### Set-rule changes and rejection per stage

| Run / order / stage | Protected bytes / final writes | Recorded device/entry changes |
|---|---|---|
| Probe 2 / first / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline exact-GUID ownership and QMP binding established. |
| Probe 2 / first / live-ui-probe | MATCH; 0 / 0 | No firmware changes. |
| Probe 2 / first / detached Windows | MATCH; 0 / 0 | DVD Boot0002 removed (`pci:00:1f.2/sata:0:65535:0`); empty target Boot0004 removed (`pci:00:03.0`). |
| Probe 2 / reverse / baseline-firmware | MATCH; 0 / 0 | Baseline established; target PCI 2.0, protected PCI 3.0. |
| Probe 2 / reverse / live-ui-probe | MATCH; 0 / 0 | No firmware changes. |
| Probe 2 / reverse / detached Windows | MATCH; 0 / 0 | Target Boot0003 removed (`pci:00:02.0`); protected PCI 3.0 relabeled/renumbered Boot0004 → Boot0002; DVD Boot0002 removed. Exactly three events. |
| Full 1 / first / baseline-firmware | MATCH; 0 / 0 | Baseline established. |
| Full 1 / first / protected-first-install | MATCH; 0 / 0 | No firmware-owned changes. Separate Bazzite Boot000A added on target ESP, before Windows in BootOrder. Existing non-auto relative order preserved. |
| Full 1 / first / after-install-without-linux | MATCH; 0 / 0 | **REJECTED**. Raw DVD Boot0002 and target Boot0004 removals fit the device set, but required Windows-first restoration swaps Windows/Bazzite relative order. No accepted NVRAM diff or exemption for the rejected stage. Complete raw stores/QMP retained. |

Every accepted event records device, old/new option numbers/descriptions and
exact 16-byte GUID. Both ownership inventories and entire BootOrders are retained;
each remaining auto option names attached hardware. Nothing is ignored silently.
The rejected stage has derived failure analysis, not a fabricated passing diff.

The runner's actual failure was:

```text
AssertionError: PLAN-GAP: relative order of non-firmware entries changed
```

After installation the non-auto order was
`[Boot000A Bazzite, Boot0000 Windows, Boot0001 UiApp, Boot0009 Shell]`.
The guide's `restore_windows_order()` step made it
`[Boot0000 Windows, Boot000A Bazzite, Boot0001 UiApp, Boot0009 Shell]`.
Windows and Bazzite option payloads did not change. Windows booted independently
from protected ESP `a3411a72-39f2-44cc-9cc1-5e18ecd9f26b`, BootCurrent=0000,
through `\EFI\Microsoft\Boot\bootmgfw.efi`. This is a file-backed marker fixture,
not a real Windows OS test. Full before/after orders and raw hashes are in the
failure analysis. No record was reordered or rewritten to pass the policy.

### Commands and retained evidence

```text
git fetch; git pull --ff-only
  Already up to date.
python -X utf8 -m unittest discover -s os/tests -p test_disk_audit.py -v
  18 in 0.367s, OK; after Linux recreation correction 18 in 0.278s, OK
Focused discovery: test_two_disk_vm.py, test_installer_webui.py,
test_firmware_contract.py, test_rehearsal_budget.py, test_rehearsal_auth.py
  20 in 0.258s, 9 in 0.004s, 1 in 0.000s, 1 in 0.000s, 9 in 0.076s; all OK
Python compilation of os/ci/*.py: passed
python -X utf8 reviews/11-two-disk-rehearsal/replay-11e-firmware.py
  11b-first-order: 2 changes; 11d-first-order: 2; 11d-reverse: 3; all passed
Ubuntu probe and full (exact source a353042):
  python3 -m unittest discover -s os/tests -v
    140 in 3.545s / 140 in 4.269s; both OK
  python3 -m py_compile os/ci/*.py os/ci/overlay/*.py; Bash syntax checks
    exit 0 in both jobs
  python3 os/ci/verify_release.py 39818554327
    Qualified original release source; runtime payload unchanged
  sudo -E python3 os/ci/rehearsal_auth.py create / preflight / pull
    separate steps: temporary file created; exact digest verified; layers pulled
  python3 os/ci/installer_inspect.py
    complete ISO pin/checksum matched, both jobs
  sudo -E .work/browser-env/bin/python os/ci/two_disk_vm.py probe
    PROBE PASSED: both serial mappings, real UI through review, backend choices
    and zero protected writes; no installation
  sudo -E .work/browser-env/bin/python os/ci/two_disk_vm.py full
    installation checkpoint passed; detached Windows marker booted
    exit 1: PLAN-GAP: relative order of non-firmware entries changed
  sudo -E python3 os/ci/rehearsal_auth.py cleanup (always)
    runner-temporary auth file removed before artifact upload, both jobs
python -X utf8 reviews/11-two-disk-rehearsal/verify-11e-evidence.py
  exit 1; 9 matching offline captures, 9 zero-write records, 821 archive entries
  original receipts/contents and raw/encoded credential scans verified
  five accepted probe events; original full-stage policy rejection retained
  only explicit probe proof qualifies; no full-result proof exists
Local privacy before the report commit:
  .work/11c/privacy-tool/unpacked/gitleaks.exe git . --pre-commit --staged --redact --no-banner --log-level info
    exit 0; no leaks found
  .work/11c/privacy-tool/unpacked/gitleaks.exe git . --log-opts HEAD --redact --no-banner --log-level info
    exit 0; 99 rewritten-HEAD commits scanned, no leaks found
```

[Local logs](logs/11e/local-regressions.txt),
[recreation regression](logs/11e/linux-recreation-regressions.txt),
[probe log](logs/11e/probe-2.txt), [full log](logs/11e/full-1.txt),
[verifier output](logs/11e/evidence-verification.txt),
[unchanged-checks proof](logs/11e/scope-check.txt).
No test or protected assertion was weakened/skipped/deleted. Only the explicit
11e automatic-option semantics changed. No Gradle/Minecraft command or daemon
was started; no daemon stop command was needed.
The portable gitleaks 8.21.2 was already checksum-verified under ignored `.work/`;
no system installation was made. The final report commit is scanned again before
push, then the unchanged GitHub privacy workflow must pass on the final PR head.

Original ZIPs (API digest receipts retained):

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| [Probe 2](artifacts/11e-probe-2-two-disk-evidence.zip) | 6,354,011 | `38eaac306a33795cde41e58b9d6ec1e0ff08c54583c281d50b492c999840130e` |
| [Full 1](artifacts/11e-full-1-two-disk-evidence.zip) | 4,745,571 | `1570ab5cf82aa6af88f3e2763fba0d66f81dcc41659078cb817e9f5fec319854` |

Original archive/log bytes are unchanged. Expanded display text alone normalizes
line endings/trailing whitespace; the verifier compares its complete normalized
content. Large squashfs inventories remain in original ZIPs. API identities use
the rewrite's placeholders. Visually inspected both probe reviews/markers and
the full [completed install](screenshots/11e-full-1-two-disk-installation-complete.png)
and [post-install detached marker](screenshots/11e-full-1-two-disk-after-install-without-linux-windows-marker.png).
Probe frames: [first review](screenshots/11e-probe-2-two-disk-review-full.png),
[reverse review](screenshots/11e-probe-2-two-disk-protected-second-review-full.png),
[first marker](screenshots/11e-probe-2-two-disk-probe-windows-without-linux-windows-marker.png),
[reverse marker](screenshots/11e-probe-2-two-disk-protected-second-probe-windows-without-linux-windows-marker.png).
Every page/transport difference remains recorded: original liveuser liveinst,
unmodified pages driven by host Chromium over loopback relay, with live Firefox
paused to preserve the installer lifecycle; root serial shutdown for offline
audits. No D-Bus installation fallback or unsupported kickstart was used.

### Minute ledger

The allowance **never reset**: shared 11c/11d/11e start
**2026-10-23T16:21:00Z**, **330 rounded minutes / 3 full runs**. Costs are ceilings
per executed job, including privacy and cancelled jobs; skipped jobs count zero.
[Full machine-readable ledger](../../os/manifest/ci/11e/final-budget.json)
lists every branch run/source/conclusion/cost. This is the brief's quota proxy,
not an invoice.

| Run(s) | Outcome | Rounded minutes |
|---|---|---:|
| Prior 11c/11d through closing 40041843056 / 40041848828 | Actual carry-forward, including closing privacy pair | 68 |
| 40042782486 / 40042788594 | New 11e brief push / PR privacy, green | 2 |
| 40043521223 / 40043526075, source 0aa50ca | First set-rule source push / PR privacy, green | 2 |
| 40043692406, source 0aa50ca | Cancelled setup after Linux-recreation source review; credentials/ISO/VM skipped, cleanup/upload passed | 7 |
| 40044245505 / 40044249975, source a353042 | Recreation-fix push / PR privacy, green | 2 |
| 40044393400, source a353042 | Complete same-source both-order probe, passed | 22 |
| 40046420672, source a353042 | Full 1: first install/marker reached; non-auto order assertion failed; mandatory stop; cleanup/upload passed | 39 |
| **Measured before closing push** | **1/3 full runs** | **142/330** |
| Closing push + PR privacy pair | Reserved: five-minute watchdog plus two-minute cleanup allowance per job | **at most 14** |
| **Bound including closing checks** | Final exact actual total and scan URLs in PR #11 | **at most 156/330** |

The final PR description closes this reservation with actual completed check
minutes, avoiding another evidence-only push/scan loop. At least 174 minutes
remain unused inside this bound; the contract stop, not budget exhaustion,
prevented continuation. No later VM/full/checks-only dispatch occurred. The guard
initially refused a reservation while a source privacy job was active; no run
was dispatched until that cost was known.

### Not verified

No installed Linux boot, installed UID/groups/keymap/encryption verification,
AresOS switch/policy/real tty3 recovery, rollback or default undo was reached.
Reverse actual installation, complete A in either order, post-undo Windows
independence and Part B remain unqualified. Live auth/signature proof does not
qualify installed-target transport. Hardware, physical keyboards/USBs, writer,
novice followability, Lenovo fitting and real Windows/BitLocker/firmware helpers
remain human release gates. **Physical installation is NOT RELEASED.**

### JUDGMENT-CALL

Set semantics are the integrator's explicit decision. Event pairing on one
device is presentation only; both raw stores and every option/order/device
inventory remain available. No new product-feel or hard-to-undo choice was made.
The Windows-default requirement and strict non-auto order were both preserved;
their observed conflict is left for the integrator, not silently resolved here.

### PLAN-GAP

11e says: “Entries that aren't firmware-owned keep their relative order in
BootOrder.” The actual installer prepends the new Bazzite entry, making Linux
first. Briefs 11/11c and the guide require restoring Windows-first; doing so swaps
the relative positions of two non-auto entries. The marker boots and protected
bytes/Windows entry are correct, but the combined transition violates that
explicit rule. This is a conflict between the required guide action/checkpoint
and the strict order rule, not another unrecognized auto-option renumbering.
The run therefore stops. Removing Linux from that comparison, hiding the
post-install store or moving a checkpoint to conceal the change is not an
authorized fix. No such change or retry was made.

### Open questions

Should Windows-default restoration have an explicit permitted Linux-order
transition, or should the installation/checkpoint contract establish Windows-
first at a different defined boundary? This needs an integrator decision and
fresh same-source qualification under the still-shared allowance. This run
chooses neither. Acceptance is not met; PR #11 stays draft and nothing is merged.

## 11f: Linux position rule and full-length qualification (2026-10-24)

### Done / zero-cost stage walk-through — BEFORE ANY DISPATCH

Read 11c/11d/11e/11f, the previous 11e result, both harnesses and the guide.
Initial fetch and `git pull --ff-only` fast-forwarded to integrator brief
`60b20e1a611240efa4583b36f69b0cf371a85531`; no force-push or merge.
This section was written locally before dispatch or source push.

11f explicitly replaces the overly broad fixed-order rule: remove all validated
target-ESP Fedora-loader Linux entries and exact-GUID firmware options before
comparing fixed-entry order. Windows, UiApp and Shell retain their relative order.
Every Linux position change (including addition/recreation) records old/new zero-based
indices and complete before/after BootOrder. Windows payload/number/default remain
strict. The host's Windows-first action is read back and must produce EXACTLY
Windows + previous BootOrder without Windows, without any other boot-variable change.

The following applies independently to **protected-first AND protected-second**.
Only these disposable file-backed disks and the closed OVMF store are manipulated.
The second order starts with an empty target and pristine initial vars; it uses the
same protected fixture and must match the first order's protected baseline.

| Stage still to execute | Expected NVRAM transition | Rule / required check |
|---|---|---|
| Baseline Windows, ISO + empty target attached | OVMF adds automatic DVD, both storage and NIC options; numbering/labels differ by enumeration. Windows Boot0000 first; no BootNext required. | Source-verified exact 16-byte auto GUID; every auto path resolves to attached per-boot QMP device. Original Windows payload pinned. |
| Real live installation | Same devices remain attached. Anaconda adds target-only Bazzite/Fedora shim entry, typically first. Auto options may refresh/relabel/renumber; Linux-first is expected here. | 11e device-set/takeover checks; 11f Linux position freedom; target GPT ESP GUID/number/start/length + exact Fedora shim/GRUB path; fixed order unchanged. Windows-first intentionally not required in live mode. |
| Restore Windows after install | Move Windows from its previous index to index zero, shifting Linux behind it. | 11f exact stable Windows move, read back before continuing. No other variable may change in this host action. |
| Windows after install, target + ISO detached | Set BootNext=0000, firmware consumes it; DVD/target auto options disappear. In reverse order the protected auto option can relabel/renumber (previously Boot0004→0002); Linux option may remain even though its target is absent. | Same three 11e device-set events in reverse, two in first order (or other device-set changes within explicit rule); Windows unchanged/first and marker BootCurrent=0000 on protected ESP. A retained validated Linux entry is permitted; an unpaired Linux removal is not. |
| First installed stock boot / optional orderly hardware-setup reboot | Reattach target (no ISO), automatic target option may return/recycle a former auto number. Set BootNext to the validated Linux entry; consumed on each boot. Shim fallback/bootupd may recreate/change a target-only Linux entry or move it. | 11e auto set + non-auto number protection; 11f validated Linux recreation/position. Only the known first stock pre-login initialization reboot is accepted and separately audited. Windows remains default at all installed checkpoints; a Linux move ahead of Windows there would STOP, not be excused. |
| Stock → staged AresOS switch | BootNext Linux consumed; bootc/bootupd may update the separate Linux option or its position. Attached devices unchanged. | Same target ESP/loader, GUID/device-set, Windows-first/fixed-order checks; signature and staged image identity unchanged. Offline audit after shutdown. |
| AresOS policy + actual tty3 password/sudo/logout → rollback queued | BootNext Linux consumed; same permitted Linux/auto refresh. bootc rollback changes OSTree/GRUB deployment state, not authority to change fixed firmware entries. | Full inherited policy, UID, Homebrew, partition and transaction identity checks plus offline protected/NVRAM checks. |
| Rolled-back stock → persistent stock default | BootNext Linux consumed; stock set-default changes GRUB deployment order. Firmware may refresh/recreate only validated Linux/auto options. | Recorded stock checksum/digest, first deployment, no staged/queued state; Windows still first in firmware. Offline audit. |
| Second unattended stock boot | Only firmware BootNext selects Linux; no GRUB selection. Auto/Linux updates subject to same checks. | Same recorded stock checksum/digest remains booted and first. Protected disk/NVRAM audit. |
| Windows before undo (both drives, no ISO) | Set BootNext=0000, consumed; auto options remain device-bound. | Original Microsoft path/ESP marker; Windows first; all disk/NVRAM checks. |
| Default undo | Read back exact Windows + previous BootOrder without Windows. Boot Windows without BootNext or keys, both drives attached. | Strict restoration assertion, marker and offline audit. No deployment or partition erase. |
| Windows after undo, target detached | Target auto option may disappear; reverse protected auto option may relabel/renumber. Linux entry may remain. | Same 11e device-set, 11f fixed/Windows order, original Windows marker and zero-write/offline comparisons. |

**Part B uses the reverse installed target after successful Part A:**

| Stage | Expected transition | Rule / required check |
|---|---|---|
| Re-switch stock → AresOS | Reattach target, auto option may return at a recyclable auto/free ID; BootNext Linux consumed; Linux EFI changes/moves remain target-only. | Identical strict device-set, target ESP, Windows default and fixed-entry order checks; inspect switch identity before reboot. |
| AresOS / prepare actual BLS menu | BootNext Linux consumed; record actual BLS stock checksum/index; reboot without changing the firmware default. | AresOS first in GRUB, retained stock identified from real BLS ostree= resolution; offline audit. |
| QMP Esc / actual stock menu selection | BootNext selects Linux firmware entry once, then GRUB one-time stock choice. Firmware auto refresh/validated Linux movement only. | Select only if OCR shows recorded real menu entries. No guessed stock identity. If undrivable, the brief-authorized grub2-reboot fallback is recorded. A menu failure never exempts protected/NVRAM checks. |
| Optional fallback boot / one-time stock | BootNext Linux consumed. grub2-reboot affects GRUB environment, not firmware BootOrder. | Stock booted at previous nonzero deployment index while AresOS remains default; validate checksum and pinned digest; audit any extra shutdown. |
| Promote recorded stock | Identity-checked ostree admin set-default; normal Linux BootNext consumed on next boot. | Confirm recovered stock identity BEFORE promotion, retain target-only Linux entry and Windows firmware default; offline audit. |
| Unattended stock | No GRUB selection; firmware BootNext selects Linux only. Stock must remain booted and deployment zero. | Same stock checksum/digest, no staged/queued state, rendered stock greeter, all protected/NVRAM checks. |

No **required** foreseeable transition conflicts with the amended rules. Unknown
paths/GUID-plus-extra, non-Linux fixed-entry changes/removal/addition, automatic
takeover of non-auto IDs, a Linux entry on the protected ESP or non-Fedora loader,
an unpaired Linux disappearance, Windows payload/default loss or any protected
write still STOP immediately. A future bootupd move before Windows at an installed
Windows-default checkpoint would also STOP; 11f does not authorize ignoring it.
No broader allowance was inferred from this walk-through.

### Time estimate / continuing ledger — BEFORE ANY DISPATCH

Integrator-reported org billing: **248 / 2,000 October included Actions minutes used
on 2026-10-24**, resets 1 November. This was read by the integrator, not verified by
job/owner token API. Same 11c start `2026-10-23T16:21:00Z`, **600 rounded minutes,
3 full dispatches total**, no reset. Initial read-only ledger: **146 minutes, 1 full**
(144 through 11e closure + two brief-11f privacy jobs).

Observed step timings from retained probe 2 / full 1 jobs: tools 2.40 / 2.68 min,
cleanup-software 0.80 / 1.60, pinned layer pull 0.57 / 0.55, pinned ISO inspection
5.75 / 5.45, VM/fixture step 11.55 / 27.77. Full first install alone took about
25.1 minutes from baseline through final install audit. Thus:

| Remaining complete-full work | Estimated minutes |
|---|---:|
| Fixture preparation, initial Windows baselines, fresh reverse target/vars | 4–5 |
| Two real ISO UI installations including install audit | 50–54 |
| Two complete switch/policy/tty3/rollback/second-stock sequences (06e 7.1 min lower bound; real installer path plus audits slower) | 22–26 |
| Windows markers after install, before/default/detached undo, including full offline hash each | 8–10 |
| Part B re-switch, recorded menu attempt/possible fallback, promotion, second stock, offline audits | 17–23 |
| Remaining per-stage hashes/EFI inventories and ordinary initialization variation | 4–5 |
| **Complete VM step** | **105–123 (planning upper bound approximately 120)** |
| Setup/ISO/auth/collection outside VM, observed about 11 | **11–13** |

Full VM limit **156** = 120 × 1.30; full job **180** covers VM + about 14 setup +
cleanup/upload with margin (and is the brief's maximum). The high endpoint 123
still has 27% VM margin. Full budget reservation **182** includes the full job
bound plus 2 minutes cleanup/accounting contingency. Probe job **40**, VM **80**,
reservation **42** remain unchanged. One job covers both orders + B; no splitting.
The unchanged 30-minute Web UI installation deadline already reached successful
completion in full 1; it is distinct from the previously insufficient full VM limit.

### Verified / gate → evidence — pre-dispatch

- `python -X utf8 -m unittest discover -s os/tests -p test_disk_audit.py -v`:
  **21 tests, 0.239s, OK**.
- Same command with `test_two_disk_vm.py`: **21 tests, 0.260s, OK**.
- With `test_rehearsal_budget.py`: **3 tests, 0.017s, OK**.
- With `test_rehearsal_auth.py`: **9 tests, 0.078s, OK**.
- `python -X utf8 reviews/11-two-disk-rehearsal/replay-11f-firmware.py`:
  11b-first-order **2**, 11d-first-order **2**, 11e-full-install **2 firmware +
  Boot000A 0→1**, 11d-reverse-order **3** events; all passed. Raw inputs and
  QMP context are SHA-bound in [new derived replay](../../os/manifest/ci/11f/firmware-set-replays.json).
- Targeted `python -X utf8 -m py_compile` on the changed CI and new evidence helpers
  passed. Local logs: [11f](logs/11f/).
- AST source comparison confirms 13 protected/ownership/loader helpers unchanged;
  auth, installer, switch, release identity and frozen manifests unchanged;
  privacy workflow/config identical to origin/main. [Scope check](logs/11f/scope-check.txt).

Fresh CI native regressions, same-source probe and full are pending. No new
dispatch has occurred; the zero-cost walkthrough above precedes them.

### Not verified

Complete A/B and hardware gates remain open until new evidence establishes them.

### JUDGMENT-CALL

No new product decision; the integrator explicitly authorized Linux position
freedom and the new cap. The full timeout/reservation follows measured timings.

### PLAN-GAP / Open questions

None newly established by this zero-cost walkthrough; all original stop rules remain.

### Fresh probe gate before full dispatch

[Probe 40052069600](https://github.com/Ares-Empire/AresOS/actions/runs/40052069600)
passed on `1b00581df4b9871c9880db67e3f54ed2b82fb487`: 146 native tests in
2.813s, six matching protected captures and six zero-write records, five firmware
device events, both real reviews and detached Windows markers visually inspected.
Original signature and owner auth cleanup passed. The artifact ZIP is 6,352,166
bytes, SHA-256 `4e80723ebfd36baa6e277cdffb50b5d1e7c1929f3ab43b8e1597c3cdf8d4e9d3`.
[Collector verification](../../os/manifest/ci/11f/evidence-verification.json) had
no incomplete records before full dispatch. Local and remote HEAD match the
probe source. Full-stage assumptions and updated measured timing are in
[ASSUMPTIONS](ASSUMPTIONS.md#fresh-11f-probe--full-run-assumption-gate-before-full-dispatch).

A local collector initially mistook non-ASCII compressed PNG bytes following
an accidental `$6$` for a password hash. The scanner now requires ASCII crypt
encoding; regression specimens still detect SHA512/rounds/yescrypt and raw/decoded
tokens. It still scans every binary archive entry; no artifact bytes/exclusions,
privacy workflow or VM policy changed. [Regression output](logs/11f/archive-scanner-regression.txt).

### Final 11f outcome — STOP before AresOS switch

**A NOT QUALIFIED; B UNTESTED; C pins retained.** One fresh full dispatch was
made, on the exact successful probe source. No further probe/full/checks-only VM
dispatch followed its failure. PR #11 stays draft. Physical installation stays
NOT RELEASED.

#### Done

- `disk_audit.py` applies only the integrator's 11f Linux-position exception;
  complete orders and old/new Linux indices are retained. Fixed non-Linux order,
  Windows identity/default, firmware device-set, takeover and Linux ESP/loader
  checks stay strict. Real-store and negative regressions passed.
- `two_disk_vm.py` reads back and checks the exact Windows-first stable move,
  saving a dedicated receipt. The full run exercised the real assertion after
  install. `rehearsal_guard.py`, workflow and budget regressions apply 600 minutes,
  the original start and 3 total full dispatches, full job/VM 180/156, reserve 182.
  Probe 40/80/42 is unchanged.
- New 11f capture/replay/verification/tabulation helpers retain original ZIPs,
  raw FD stores/QMP context, exact artifact digest receipts, safe command logs,
  screenshots and per-stage events. Collector-only changes require complete A
  checkpoint files and exact Windows-order receipts and distinguish ASCII crypt
  hashes from accidental compressed PNG bytes. No binary scan/exclusion was removed.
- INSTALL and EMERGENCY retain the installation/recovery gates and replace the
  resolved order-rule blocker with the real pending-stock blocker and missing
  final failure-session counter. Frozen image/base/source/signature/media pins,
  credential code and the stock no-pending-update guard were not changed.

#### What stopped / PLAN-GAP

[Full 40054116223](https://github.com/Ares-Empire/AresOS/actions/runs/40054116223),
source `1b00581df4b9871c9880db67e3f54ed2b82fb487`, completed the first real
installation, exact Windows-first restoration, detached Windows marker and
stock's recognized orderly hardware-setup reboot. The first authenticated stock
boot had the pinned base **ed93…5151**, OSTree checksum
`aa669eff4ea5c1f97c6c816c8d5d2abb5314e9afa3b966c0100e3e65f8040c71`,
booted at serial 1. The actual greeter, UID 1000 wheel administrator, target ESP
and inherited Homebrew pre-switch checks passed.

However, stock already had a **staged newer upstream Bazzite deployment**:

- reference `ghcr.io/ublue-os/bazzite-nvidia-open:stable`
- digest `sha256:d0e5e105ebf43c7ddbe3c4a5dfecac1628b0e0dcf152bbd2aee0eda3e4b4cdd4`
- checksum `278edb6798de01c7c090d25e058f3754c2cd6585d930634d7f5abeb90a362487`
- version `44.20261023`, image timestamp `2026-10-23T16:36:04Z`.

The boot console records `uupd.timer` and `uupd.service` starting. Automatic
updating is the supported inference from those startup records and the newer
staged stock state; no updater journal was collected to identify the exact writer.
Both bootc and the failing rpm-ostree status confirm the staged deployment.

`os/release/pin-stock.sh` correctly failed its unchanged assertion that there is
one booted deployment and **no staged deployment**. Exact failure:
`AssertionError: Guest command failed: pin-stock, exit 1`.
The guard failed before `ostree admin pin`, installed signature verification or
`bootc switch`. No switch, policy/tty3, rollback, undo, reverse installation or B
was attempted afterward. No image was rebuilt/repinned, update cleared, updater
disabled or guard weakened. This is a new recipe PLAN-GAP: stock's ordinary
updater can stage a mutable-tag update before the frozen release's retain/pin
step. The guide already says to stop for pending/mismatched state; it provides
no authorized recovery from this case.

The failure-close path host-terminated QEMU (`host-signal` event). The resulting
last offline protected capture and NVRAM comparison pass, but there is **no final
`stock-blockstats.json`**. The evidence verifier therefore returns **exit 1** and
keeps that session's zero-write proof unqualified. This is an additional failure
path evidence gap, not a claimed zero. Ten earlier final records prove zero
writes; all eleven actual offline captures match their run's baseline.

[Compact stop analysis and SHA-bound inputs](../../os/manifest/ci/11f/full-stop-analysis.json),
[actual bootc state](../../os/manifest/ci/11f/full-2/two-disk/stock-status.json),
[pin refusal](../../os/manifest/ci/11f/full-2/two-disk/pin-stock.txt),
[host close event](../../os/manifest/ci/11f/full-2/two-disk/stock-qmp.json).
A local replay feeds that real rpm-ostree status into the **unchanged** pin script,
with subprocesses mocked: it raises at the same guard, and no pin command is
executed. It does not simulate a successful guest switch.

#### Gate → evidence

| Gate | Evidence / result |
|---|---|
| Amended order rule + strict negatives | **PASS** 21 disk tests, 21 harness tests, 3 budget tests, 9 auth tests; [four raw-store replays](../../os/manifest/ci/11f/firmware-set-replays.json), including old full's exact 2 removals + Boot000A 0→1. Earlier 11b/11d events remain identical. |
| Zero-cost walk and time sizing before dispatch | **DONE** tables above were committed in source `1b00581` before dispatch. Full 180/156, probe unchanged; same ledger/cap regressions. Complete-run timing remains unqualified because full stopped early. |
| Same-source fresh probe | **PASS** [40052069600](https://github.com/Ares-Empire/AresOS/actions/runs/40052069600), [all proof flags](../../os/manifest/ci/11f/probe-1/two-disk/probe-result.json), server artifact digest rechecked by full's guard. Both orders, real destination/review, exact backend/German choices, detached Windows. |
| Firmware source/ownership | **PASS reached stages** [full contract](../../os/manifest/ci/11f/full-2/firmware-contract.json), raw source checked in collector, GUID exactly 16 bytes; every auto option bound to its boot's QMP device set, Windows unchanged and first at all Windows-default checkpoints. |
| Owner-token limits | **PASS reached uses** pinned manifest/all-layer pull and live signature in probe/full; exact one-image auth key, runner-temp root-600 file, RO root-only 9p. Installed stock auth mount passed; installed signature and switch reads were not reached. Both always-cleanups removed the file before upload ([probe](../../os/manifest/ci/11f/probe-1/owner-auth-cleanup.json), [full](../../os/manifest/ci/11f/full-2/owner-auth-cleanup.json)). Zero owner-token GitHub API calls; visibility metadata explicitly unverified from org. |
| First real install / own target ESP | **PASS checkpoint** [completed install](../../os/manifest/ci/11f/full-2/two-disk/protected-first-install-result.json), [target EFI](../../os/manifest/ci/11f/full-2/two-disk/protected-first-install-target-efi.json), [UI](screenshots/11f-full-2-two-disk-installation-complete.png). |
| Exact Windows restore / detached boot after install | **PASS checkpoint** [stable-move receipt](../../os/manifest/ci/11f/full-2/two-disk/after-install-windows-order.json), [accepted NVRAM diff](../../os/manifest/ci/11f/full-2/two-disk/after-install-without-linux-nvram-diff.json), [marker](screenshots/11f-full-2-two-disk-after-install-without-linux-windows-marker.png). |
| First installed stock | **PARTIAL** pinned base booted, recognized hardware-setup reboot, admin/greeter/Homebrew checks passed; newer stock already staged, so no-pending pin guard stopped. [Greeter](screenshots/11f-full-2-two-disk-stock-bazzite.png), [stock state](../../os/manifest/ci/11f/full-2/two-disk/stock-status.json). |
| Protected bytes / zero writes | **11 matching offline captures, 10 final zero-write records, 1 missing final counter**. [Strict verification](../../os/manifest/ci/11f/evidence-verification.json) exits 1, names missing stock record and qualifies only the probe. Full protected baseline `21b8bd6297cb98c5a470f81d141010bdb5bc96407182e45d2b63e21bd888156c`; probe baseline `2214f732ad8dd74811ee5b071e82e8b2ceb3966c644137a85383c7b17123c5ae`. These are independent fixtures; comparisons are within each run. |
| Complete Part A, both orders | **NOT QUALIFIED** no switch/policy/tty3/rollback/default undo or reverse full sequence; post-undo Windows independence untested. |
| Part B / physical-media followability | **UNTESTED / OPEN** blocked by incomplete A. No hardware/laptop-disk test. |
| Privacy | Source push [40051917073](https://github.com/Ares-Empire/AresOS/actions/runs/40051917073) and PR [40051921449](https://github.com/Ares-Empire/AresOS/actions/runs/40051921449) green; private-term step actually ran. First report push [40058505932](https://github.com/Ares-Empire/AresOS/actions/runs/40058505932) / PR [40058509349](https://github.com/Ares-Empire/AresOS/actions/runs/40058509349) also passed with private terms checked. Final receipt push/PR pair is reserved below; exact closing results/total are recorded on [PR #11](https://github.com/Ares-Empire/AresOS/pull/11). |

#### Per-stage firmware and Linux position events

All accepted NVRAM records include the entire BootOrder before/after and raw
option changes. Linux indices below are zero-based; `None→0` is creation.
The stock failure-stage NVRAM diff passed independently of the missing counter.
| Run / order / stage | Protected bytes / final writes | Firmware and Linux position events |
|---|---|---|
| full-2 / first / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| full-2 / first / protected-first-install | MATCH; 0 bytes / 0 operations | Linux Boot000A: index None → 0 |
| full-2 / first / after-install-without-linux | MATCH; 0 bytes / 0 operations | pci:00:03.0: Boot0004 → absent<br>pci:00:1f.2/sata:0:65535:0: Boot0002 → absent<br>Linux Boot000A: index 0 → 1 |
| full-2 / first / boot-4-pre-login-reset | MATCH; 0 bytes / 0 operations | pci:00:03.0: absent → Boot0002 |
| full-2 / first / switch-sequence-stock | MATCH; missing counter | None |
| probe-1 / first / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| probe-1 / first / live-ui-probe | MATCH; 0 bytes / 0 operations | None |
| probe-1 / first / probe-windows-without-linux | MATCH; 0 bytes / 0 operations | pci:00:03.0: Boot0004 → absent<br>pci:00:1f.2/sata:0:65535:0: Boot0002 → absent |
| probe-1 / reverse / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| probe-1 / reverse / live-ui-probe | MATCH; 0 bytes / 0 operations | None |
| probe-1 / reverse / probe-windows-without-linux | MATCH; 0 bytes / 0 operations | pci:00:02.0: Boot0003 → absent<br>pci:00:03.0: Boot0004 → Boot0002; relabel<br>pci:00:1f.2/sata:0:65535:0: Boot0002 → absent |

#### Commands and outputs / Verified

- Local four focused commands and source checks are listed above with [logs](logs/11f/).
- Fresh probe CI: `python3 -m unittest discover -s os/tests -v`:
  **Ran 146 tests in 2.813s; OK**. Full: **Ran 146 tests in 3.724s; OK**.
  Both CI jobs also passed Python compilation, shell syntax and unchanged release
  source/runtime-equivalence verification. No mod/Gradle/Minecraft command ran;
  no Gradle daemon was started.
- Actual probe: `sudo -E .work/browser-env/bin/python os/ci/two_disk_vm.py probe`:
  **PROBE PASSED: both serial mappings, real UI through review, backend choices
  and zero protected writes; no installation**.
- Actual full used `full` and explicit probe ID `40052069600`; native checks
  passed, then **Guest command failed: pin-stock, exit 1**. Always-cleanup and
  upload passed. [Full log](logs/11f/full-2.txt), [probe log](logs/11f/probe-1.txt).
- `python -X utf8 reviews/11-two-disk-rehearsal/verify-11f-evidence.py`:
  **11 matching offline stages; 10 zero-write records; 809 archived entries
  scanned; 1 incomplete (No final write counter); exit 1**. This is the expected
  strict rejection of incomplete full evidence, not a green full result.
- `python -X utf8 reviews/11-two-disk-rehearsal/regress-11f-archive-scanner.py`: valid ASCII SHA512/rounds/yescrypt and raw/decoded token fixtures detected; real compressed PNG has no credential match.
- `python -X utf8 reviews/11-two-disk-rehearsal/replay-11f-stock-stop.py`:
  **same real rpm-ostree status triggers AssertionError; no ostree pin command
  executed**. [Replay log](logs/11f/stock-stop-replay.txt).
- `python -X utf8 reviews/11-two-disk-rehearsal/tabulate-11f-stages.py`:
  **Stage rows: 11**. The reproducible table is also [stored with evidence](../../os/manifest/ci/11f/stage-table.md).

Original ZIPs are unmodified; collector checks API artifact SHA-256, original
log ZIP SHA-256, every retained FD/JSON/PNG byte, display-text normalization,
raw/decoded credential patterns, source ownership, all reached audits and
signature/cleanup receipts. The 33 MB ISO file inventory remains inside original
ZIPs, with its expanded copy ignored as in earlier rounds.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| [Probe](artifacts/11f-probe-1-two-disk-evidence.zip) | 6,352,166 | `4e80723ebfd36baa6e277cdffb50b5d1e7c1929f3ab43b8e1597c3cdf8d4e9d3` |
| [Full 2](artifacts/11f-full-2-two-disk-evidence.zip) | 5,585,886 | `b77bed201bc41f768b13edb8d825c39b42308c56f93077a0cb0d5b03a8c55a08` |

Visually inspected: both probe reviews and detached markers, full installation
completion, the full detached Windows marker and actual installed stock greeter.
Browser/transport differences remain host Chromium versus paused guest Firefox
using the original served pages, and loopback forwarding. This does not qualify
physical keyboard/menu/media use or a novice's unaided click path.

#### Minute ledger

Same start, nothing reset: **2026-10-23T16:21:00Z**, cap **600 rounded minutes**,
**3 full dispatches total**. Integrator-reported org October usage 248/2,000 is
recorded above; it is not a token-verified billing fact.

| Work | Rounded minutes |
|---|---:|
| Through actual 11e closure | 144 |
| Integrator's 11f brief push + PR privacy | 2 |
| New source push + PR privacy | 2 |
| Probe 40052069600 (25.167 actual minutes) | 26 |
| Full 40054116223 (52.450 actual minutes) | 53 |
| First report push/PR privacy 40058505932 / 40058509349, green | 2 |
| **Measured before final receipt push** | **229 / 600** |
| Final receipt push + PR privacy, five-minute watchdog + two-minute cleanup reserve each | **at most 14** |
| **Conservative closing bound** | **243 / 600; 2 / 3 full runs** |

[Complete machine-readable ledger](../../os/manifest/ci/11f/final-budget.json).
Pre-probe reserved 42 at 148 measured; pre-full reserved 182 at 174 measured;
CI guard rechecked source/proof and budget. Full setup/tools took 8.6 minutes,
ISO 5.283, VM 34.367 before stopping; neither full timeout was reached. Complete
105–120-minute VM timing is still an estimate, not measured qualification.
The actual closing pair URLs, their cost and final total are recorded in PR #11
without another report-only push triggering another pair.

#### Not verified

Complete A in either order; switched policy, tty3 recovery and rollback from the
actual installer target; full default undo and Windows after undo; reverse full
installation; B's previous-deployment promotion and unattended stock boot; final
write count of the host-terminated failed stock session. All physical/human gates
remain open. Installed stock's auth mount worked, but installed release signature
and bootc reads were not reached.

#### JUDGMENT-CALL

No new product decision taken. The authorized Linux/order/time/cap changes are
implemented. The pending-update guard and frozen stock/release identities were
kept. Clearing the staged update, changing stock's updater policy or changing
pins would require an integrator decision; no such action was inferred.

#### Open questions

The integrator must define how the pinned stock retain/switch recipe handles a
normal upstream update already staged on first boot, preserving the frozen
release identity and pending-state safety checks. A later harness follow-up
should also define final counter collection on a failed command's host-close
path. No remaining full allowance was spent guessing either answer.

Local closing privacy verification: staged evidence, scanner regression and
final documentation scans used gitleaks 8.21.2 with redaction and found no leaks.
Rewritten HEAD history was scanned without local pre-rewrite refs; no-reply
email validation passed. The final push/PR privacy pair is monitored and its
exact final ledger is recorded in PR #11 as described above.

Final receipt check: three derived text input hashes originally used working-tree
CRLF. The stock-stop replay now hashes the normalized LF display representation
that Git stores. Every stock-stop and firmware-replay input SHA-256 was checked
against the committed Git blobs and matched. Original ZIP/FD/JSON/PNG bytes and
all VM results are unchanged. The extra receipt/privacy commit costs another
push/PR pair; the measured ledger above includes the first pair, and the final
pair remains within the new 14-minute reserve. [Receipt proof](logs/11f/input-receipt-check.txt).

## 11g: stock updater preparation and failure counters (2026-10-24)

### Zero-cost stage walk-through — BEFORE ANY DISPATCH

Initial `git fetch` and `git pull --ff-only` printed `Already up to date.`;
HEAD was integrator brief `0bb2b3f`. Read 11c–11g, the 11f outcome, guide,
updater audit and harness. This walkthrough is written before any 11g dispatch.
The 11f walkthrough above still applies to every firmware transition, independently
in **both protected-first and protected-second** orders, with the following complete
sequence and the new first-login step explicitly included.

| Stage, in each order | Expected event / governing rule |
|---|---|
| Baseline Windows, ISO + empty target attached | Auto DVD/storage/NIC entries use exact source-verified 16-byte ownership GUID and each boot's QMP device set. Numbers and descriptions may differ by enumeration. Windows Boot0000 bytes/number remain pinned and Windows is first. |
| Real live UI install | Same devices. Installer creates target-ESP-only Fedora shim/GRUB Linux entry, possibly first. 11e auto device-set / number-takeover checks and 11f validated Linux position freedom; fixed entries retain relative order. Live checkpoint permits Linux first. |
| Restore Windows | Read back exactly Windows + prior BootOrder without Windows; no other boot-variable change. |
| **First stock login before Windows comparison** | Remove ISO, keep both disks; DVD auto option may disappear, remaining auto options may relabel/renumber. BootNext selects validated Linux and is consumed. Existing known pre-login hardware-initialization reboot, if needed, is separately audited. Shim/bootupd may recreate/move only the validated target Linux entry. Windows stays byte-identical and first at installed checkpoints. |
| **Pause, pending cleanup and pin, before any post-install Windows reboot** | Stop/mask OS updater services for this boot, persistently disable their timers, wait for no updater/deployment transaction. Require booted ISO digest; discard at most one identified upstream-Bazzite pending deployment, re-read unchanged booted checksum/no staged state, then pin and re-read. These are deployment/unit operations on the target, with no authorized NVRAM change. Power off normally, final zero-write counter then offline byte/GPT/EFI/NVRAM audit. |
| Windows comparison after install, target detached | Set BootNext=0000, consume it. Target auto option may disappear; protected auto option may relabel/renumber, particularly reverse order. Retained validated Linux option may remain. 11e per-boot attached-device set and non-auto number protection; 11f fixed order and Windows-first; original protected ESP marker must boot. |
| Stock → signed AresOS | Reattach target, auto option may return at a free/former-auto number; Linux BootNext consumed. Repeat pause/pin before signature/switch; require no staged state before switching. Only target Linux loader/position changes and attached-device auto refresh are allowed. Preserve signature, release and staged identity checks, normal shutdown/audit. |
| AresOS policy / tty3 / rollback | Linux BootNext consumed; same device/target-only Linux rules. Frozen updater policy and actual password/sudo/logout checks remain unchanged. Deployment rollback authorizes no fixed firmware changes. Audit after shutdown. |
| Rolled-back stock / persistent stock / second stock | BootNext consumed each time, permitted auto refresh/Linux recreation only. Validate original recorded stock checksum/digest, set deployment default, require no staged/queued state, then confirm a second unattended GRUB boot. Timers stay paused through this trial. |
| Windows before undo, both disks | BootNext=0000 consumed, unchanged Microsoft loader/ESP marker, Windows first, all offline/counter/NVRAM checks. |
| Default undo, both disks | Exact Windows-first stable move verified, boot Windows with no BootNext or keys; no disk/deployment erase. |
| Windows after undo, target detached | Target auto removal and possible protected auto relabel/renumber under the same device-set rule. Retained target Linux entry permitted. Original marker, zero writes and full offline comparisons. |
| Fresh reverse-order installation | Closed target-only reset plus pristine vars. Repeat **all rows above**, including early pause/pin, complete switch/policy/tty3/recovery/default undo and both detached markers. Same protected fixture must match its original baseline. |

**Part B, only after both Part A orders pass:** reattach the reverse target;
Linux BootNext consumed, auto target option may return/recycle an auto/free ID.
Repeat pause/pin and require original stock identity before re-switch. Boot AresOS,
record real BLS entry checksum and menu index, then try actual GRUB stock selection.
Only rendered recorded entries may be selected; the existing authorized `grub2-reboot`
fallback records its use and any extra boot/audit. Stock must first boot at its recorded
nonzero index while AresOS is default, then identity-checked promotion sets it first,
then a second unattended stock boot must preserve checksum/digest and no staged/queued
state. At **every** shutdown: final QMP counter, closed-file protected audit, raw vars,
QMP device context and accepted NVRAM diff. Windows firmware default/fixed-entry order
remain strict; all Linux changes must name the target's own ESP/Fedora loader.

The new order avoids finalizing a known pending stock update during §5. Do not stop
hardware setup, `ostree-finalize-staged`, bootc finalization or bootloader maintenance:
they have separate roles and remain unchanged. If a stock update is **already booted**
before the first successful login, the specified digest check deliberately STOPs;
there is no permission to auto-rollback, repin or reboot past that refusal. No required
transition conflicts with the rules. Uncovered firmware, protected writes, wrong
booted stock, unreviewed deployment updater, signature/auth rejection or a later
frozen policy conflict means STOP and report, without widening rules or rebuilding.

### Updater inventory and preparation

[Inventory](../../os/manifest/ci/11g/updater-inventory.json) reuses the frozen-image
updater audit and its retained vendor commands (SHA bound): system uupd/manual,
rpm-ostreed-automatic, bootc fetch/apply and update, systemd-sysupdate/reboot/daemon
and its D-Bus alias, dnf/dnf5 automatic and offline, PackageKit/offline, their timers,
and global-user uupd. Optional masked placeholders are distinguished from actual
stock units in the fresh live/installed inventories. Unknown OS deployment commands
fail closed. Hardware setup/finalizers, app-only updaters and cleanup bookkeeping
are explicitly excluded, with reasons. No payload or policy allowlist changes.

`pause-stock-updates.sh` stops selected services, runtime-masks them against current
session reactivation, persistently disables timers and inspects active user managers;
it waits for inactive updater units, null rpm-ostree transaction and no bootc/rpm-ostree
client. `pin-stock.sh` repeats that exact self-contained block, prints the one pending
upstream identity before `rpm-ostree cleanup -p`, re-reads stock/no-pending state, pins,
and re-reads again. The official [rpm-ostree manual](https://raw.githubusercontent.com/coreos/rpm-ostree/main/man/rpm-ostree.xml)
documents pending-only cleanup separately from rollback cleanup. INSTALL copies this
block before §5 and repeats it before switching; EMERGENCY explains STOP/help.
Returning permanently to stock has one explicit `sudo systemctl enable --now uupd.timer`
line, after Part B's second stock boot. Runtime masks disappear on reboot.

### Time estimate and shared allowance — BEFORE ANY DISPATCH

Same start **2026-10-23T16:21:00Z**, new **750 rounded minutes / 4 total full runs**.
11f's final measured ledger was **231 minutes / 2 full runs**, rather than its
conservative 229 + 14 closing reserve; brief 11g privacy jobs add their actual rounded
cost: initial guard measured **233/750 minutes, 2/4 full** (42 reserved for probe). The integrator-reported org bill remains 248/2,000 October minutes, reset
1 November; this is not verified using the owner read token.

Use the prior measured 11f table: two installations 50–54m, two switch/recovery
sequences 22–26m, Windows markers 8–10m, Part B 17–23m, fixture/other hashes 8–10m.
The early stock preparation adds about **3–5m per order** (one extra boot plus audit),
while reusing the already required first hardware-setup boot. Central VM estimate
is now approximately **120m**, upper planning range **111–133m**. Existing full VM
**156m** gives 30% on the central estimate (17% at the conservative high endpoint);
job **180m** covers observed 11–18m setup plus cleanup/upload. This is the authorized
job maximum, one complete job for both orders and B. Probe limits **40m job / 80m
VM step** and reservations **42 probe / 182 full** stay unchanged. Guard now enforces
750/4, includes all branch privacy jobs, and requires new stock/counter probe flags
on the exact same commit. No ledger reset; next full is number **3 of 4**.

### Native regressions before dispatch

- `test_stock_prepare.py`: **7 tests passed**: 11f's actual staged d0e5 status discards
  exactly that deployment, pins unchanged aa669 stock, clean-stock pin, four refusal
  classes including checksum changing after cleanup, pause twice, transaction wait,
  and exact owner-block/script synchronization. No real cleanup ran on the laptop.
- `test_two_disk_vm.py`: **24 tests passed**, including failed-command final counter
  before termination, explicit unavailable-QMP receipt, and protected writes still
  raising PRODUCT FAILURE while QEMU closes. Normal-shutdown counter test retained.
- `test_rehearsal_budget.py`: **3 tests passed**, fourth full permitted/fifth rejected,
  shared 750-minute cap, unchanged probe/full timeout reservation checks.

Fresh probe and full outcomes, per-stage events, gate table and final ledger are
pending. Historical 11f's missing counter remains unqualified and unchanged.

### Pre-full close-path correction / replacement probe

During setup-only probe 40061143698, a source audit found the unexpected-QEMU-exit
branch could skip the explicit unavailable-counter receipt. Cancel requested before
any VM/installation; preserve that run's actual cost, artifacts and credential
cleanup receipt. Fixed close to attempt/query/record on an unexpected exited process
as well as a live failed session; verified ordinary shutdowns keep their existing
final record. Added regression: exited QEMU + unavailable QMP creates the explicit
unavailable receipt without a redundant terminate. **25 harness tests passed**.
A replacement same-source probe is required before any full dispatch. This is a
harness correction with a regression; no firmware/offline/payload rule changed.

The final verifier also rejects an unpaused failure counter or an earlier stale
counter when the final QMP query was unavailable. Part B's recovered-stock audit
uses its actual promotion-reboot counter filename; no historical record is created
or relabeled. Corrected a stale INSTALL sentence about automatic updater resumption.
The earlier broad Windows discovery printed `Ran 137 tests ... FAILED (failures=1,
errors=10)` because it requires Linux symlink privileges, os.getuid, termios and
pass_fds; retained its log, no tests skipped or changed. The first Ubuntu probe's
complete regression step passed; its exact count will be retained from the log.
Replacement probe will repeat the complete suite on the corrected source.

Cancelled probe receipt: **11 rounded minutes**, 04:08:17–04:18:47 UTC. Native
`Ran 156 tests in 5.003s / OK`; cancellation occurred in ISO inspection, no VM
fixture or installation. Owner manifest/layer reads passed and always-cleanup
removed the runner-temp credentials before artifact upload. Original artifact
47,869 bytes SHA-256 `0e09722b1df39769098cf591e920ee2e3c18dd640ee79d5da1345e1b4db42d8e`;
[retained metadata](../../os/manifest/ci/11g/probe-1/), [log](logs/11g/probe-1.txt).
Archive verifier passed with **zero qualifications** for this cancelled run.

### Probe 2 caught live/installed tool split — before another dispatch

[40062047055](https://github.com/Ares-Empire/AresOS/actions/runs/40062047055), source
`6902c0455ca53d1a2b63c6899450dd097bac3b35`, failed **before installation** at
`stock-recipe-tools`: `command -v rpm-ostree` returns 1 in the live root. The actual
SquashFS list confirms no `/usr/bin/rpm-ostree` executable (only a dangling build-ID
reference and unit files); stock's installed 11f deployment ran that executable.
The ISO's recorded containers-storage cache contains exactly the original base
manifest `ed93…5151`, image ID `0e4c3c1f2339438b7dc7e88d93ad8aa5f77663e04490fcb875549f4f062a5431`.
It is the existing installer payload, not a new image or replacement install route.

Before the next dispatch, amend the probe assumption: require real live systemctl,
podman and process/account tools; inspect the cached image by digest and ID, then
run **only tool discovery and CLI help** inside it with `--pull=never --network=none
--read-only --rm`, entrypoint Bash, no host/owner-auth mounts and auth lookup pointed
at `/dev/null`. Actual unit pause twice remains on the real live system and its
retained stock unit files. Pending cleanup still uses the mocked real 11f status;
actual installed behavior remains a full-run gate. [Podman run documentation](https://docs.podman.io/en/latest/markdown/podman-run.1.html)
defines these no-pull/network/read-only options; [image inspect](https://docs.podman.io/en/latest/markdown/podman-image-inspect.1.html)
returns the ID and manifest digest. A cache mismatch or execution failure stops the
probe; there is no registry, alternate image, package installation or install fallback.

This adds no NVRAM stage or transition to the zero-cost table above. Probe's target
is still empty. Both full orders and B, exact Windows-first and target-only Linux
rules, signature/policy checks, the 180/156 limits and shared 750m/4-full ledger stay
unchanged. The first genuine probe failure also exposed that graceful cleanup kept
the final zero counter but lacked the failure-path label. New command-failure flag
and active-exception handling mark/sample it **before QMP quit**, or explicitly cite
the already verified shutdown final sample for a later assertion. The known,
strictly recognized stock initialization reboot remains a normal event. Added
regressions for graceful failed-command cleanup and that normal reboot distinction.
Historical 11f and probe-2 originals remain unchanged, including their counter labels.

Probe 2 retained **2 matching offline captures and 2 final zero counters**, with no
firmware or protected-disk failure; it has **no probe qualification**. Owner cleanup
passed. Native Ubuntu: `Ran 157 tests in 3.223s / OK`. Source correction: **27 harness
regressions / 3 cached-image regressions passed**. The extra local `test_switch.py`
command printed `Ran 13 tests in 0.134s / FAILED (failures=1)` for the same Windows
`pass_fds` limitation documented above; Ubuntu will repeat it unchanged.

After probe 2, the guard measured **269/750 rounded minutes, 2/4 full runs**.
No full dispatch has occurred during 11g. Probe 3 must pass on the next source commit.

### Fresh probe 3 / full authorization — before full dispatch

[40064206779](https://github.com/Ares-Empire/AresOS/actions/runs/40064206779), source
`909fe5a1d54345af550588ea926800930102c168`: **PASS**, 28 rounded minutes.
`Ran 162 tests in 3.735s / OK`. Both cached-stock CLI contexts, real unit pause twice,
paused QMP counter exercise, final review, German/backend choices, detached Windows
and Windows-order read-back passed. Six original offline captures match and all six
final counters are zero; the two probe-only counter receipts are separate. The
collector totals eight matched/zero captures including failed probe 2; only probe 3
has explicit qualification. Archive scan: 769 records, no incomplete stage or
credential pattern. Original artifact 6,379,229 bytes, SHA-256
`219a53fca2def89d852e51e941c45370a2cf09b731fb8d40cd439b7f9d22c043`.
Owner cleanup removed the file before upload. Visually inspected both final review
screens: first vdb, reverse vda, only target EFI/boot/root rows. Initial transient
selection frames are preserved too; the final destination/review proofs govern.

The complete zero-cost stage/NVRAM walk above still applies. No additional device,
firmware rule, payload, signature/policy or timeout change. Local and remote source
still match; retain these artifacts locally and **do not push** before the full's
same-source guard. Next full is global run **3/4**, one complete job for both A
orders then B. Actual installed pause/cleanup/pin and later policy remain gates.

### Final 11g outcome — mandatory STOP on a probe-covered keyboard check

**Done:**

- Added self-contained stock updater pause and pending-only cleanup/pin scripts,
  synchronized owner block before §5, repeated preparation before AresOS switch
  and B, explicit permanent-stock update resumption, and emergency STOP/help text.
  The SHA-bound 24 scoped audit entries and fresh live inventory are retained.
- Added actual 11f staged-status replay, refusal/idempotency regressions, cached
  exact-stock CLI probe, shared 750-minute/4-full guard and unchanged full/probe
  timeout tests. No image build, frozen payload/pin change or policy exception.
- Added live/terminated/unavailable/graceful-failure counter handling. Actual full
  failure now has its final counter before QMP quit, marked failure-path; historical
  11f's missing record remains unqualified. The offline audit is unchanged.

**Verified — actual full stop:** [40066161000](https://github.com/Ares-Empire/AresOS/actions/runs/40066161000)
used source `909fe5a1d54345af550588ea926800930102c168`, exactly the successful probe's
source, with explicit probe ID 40064206779 and original server-artifact digest
verification in the full guard. The full job used **17 rounded minutes**;
`Ran 162 tests in 3.837s / OK`. Manifest/pull, source-equivalence, signature/identity,
frozen ISO and firmware-source preconditions passed. Before installation, the real
UI's committed module layout was `de`, explicit console keymap empty (the previously
tested resolver path), but `read_keyboard()` failed at:

```text
AssertionError: Conversion did not restore live settings
Guest command failed: webui-keyboard-proof, exit 1
```

This is the exact assertion that passed in **both** probe orders. Brief 11b's
mandatory [probe rule](../../briefs/11b-webui-install.md#probe-before-every-full-run-mandatory)
says: “If a full run then fails on something the probe should have covered, that's
the stop signal.” **No fourth full, further probe, assertion relaxation or UI fix
was attempted.** The full failed before destination/review completion and before
“Erase data and install”; the artifact stage name `protected-first-install` is the
failed attempt's cleanup checkpoint, **not a completed installation**.

The `libbd_mpath.so.3` warning also appears in both passing probe orders. It does
not establish the cause. The LocaledWrapper `before`/`after` values were not exported,
so which field changed and whether timing was involved remain **unverified**.
[Failure transcript](../../os/manifest/ci/11g/full-3/two-disk/webui-keyboard-proof.txt),
[same-source passing first-order proof](../../os/manifest/ci/11g/probe-3/two-disk/webui-keyboard-proof.json),
[reverse proof](../../os/manifest/ci/11g/probe-3/two-disk/protected-second/webui-keyboard-proof.json),
[SHA-bound stop analysis](../../os/manifest/ci/11g/full-stop-analysis.json).

**Failure-path counter:** boot 2's
[receipt](../../os/manifest/ci/11g/full-3/two-disk/protected-first-install-failure-counter.json)
is `recorded`, `failure_path:true`, `probe_only:false`, `vm_paused:true`;
[QMP blockstats](../../os/manifest/ci/11g/full-3/two-disk/protected-first-install-blockstats.json)
show **0 bytes / 0 operations** for protected. Raw events retain guest shutdown,
STOP and later host QMP quit. Both offline captures equal baseline
`4719373f658598eca85c0103d1d443a77d74f845c1463fb812383ad06aa6fa13`;
Windows entry and BootOrder are unchanged, with zero firmware/Linux-position events.
This closes the observed 11f counter-loss defect for a real failed guest command
through orderly cleanup, independently of the still-failed install qualification.

**Whether CI discarded a staged update:** **NOT REACHED on installed stock.** There
is no installed stock pin result, staged observation or discard in this full run.
Do not treat the successful mocked d0e5 replay or cached CLI help as that evidence.
The replay removes exactly the previously captured pending deployment and pins the
unchanged aa669 booted stock; negative cases refuse before pin. Actual first-login
pause/cleanup/pin, both complete A orders, switch/policy/tty3/rollback/default undo,
post-install/post-undo Windows independence and B remain unqualified.

### Gate → evidence / final qualification

| Gate | Result / evidence |
|---|---|
| Zero-cost walkthrough before any dispatch | **DONE** complete two-order and B tables above; updated tool context and full gate recorded before their dispatches. No firmware/offline rule widened. |
| Stock updater inventory / owner recipe | **IMPLEMENTED, installed behavior NOT QUALIFIED** [inventory](../../os/manifest/ci/11g/updater-inventory.json), [pause](../../os/release/pause-stock-updates.sh), [pin](../../os/release/pin-stock.sh), INSTALL/EMERGENCY updated. |
| Pending cleanup replay / refusal / idempotency | **PASS** [7 tests and actual-fixture replay](../../os/manifest/ci/11g/stock-prepare-replay.json); clean stock, wrong booted digest, two pending, non-Bazzite/evil suffix, checksum change after cleanup, pause twice and transaction wait. |
| Probe CLI and real unit pause | **PASS** [probe 3](../../os/manifest/ci/11g/probe-3/two-disk/probe-result.json); exact existing cached base, offline/read-only/no-pull/no owner mount; real pause twice in both orders. 3 cache regressions reject wrong/ambiguous cache and prevent registry fallback. |
| Failure counters | **PASS reached actual path** 27 harness tests include failed-command host close, graceful close before QMP quit, unavailable QMP, unexpected exited QEMU, protected writes still PRODUCT FAILURE and recognized normal initialization reboot. Real full failed command retains marked zero counter. |
| Same-source full authorization | **PASS precondition** [full guard](../../os/manifest/ci/11g/full-3/11c-dispatch-authorization.json), probe 40064206779, source 909fe5a, original artifact digest checked. |
| Native Linux / unchanged rules | **PASS** 162 in probe and full, including existing 21 disk-audit / strict firmware negatives, auth limits and budget regressions. Local focused logs under [11g](logs/11g/). Windows broad/switch failures are documented above, not hidden or skipped. |
| Full installer keyboard qualification | **FAIL / mandatory STOP** same probe-covered restoration assertion; [full log](logs/11g/full-3.txt). No install began. |
| Protected disk / NVRAM reached stages | **PASS reached safety checkpoints only** 10 matching offline captures / 10 final zero-write records across probe 2, probe 3 and full 3. All Windows entries/defaults preserved; 5 allowed auto events only in probe 3, 0 Linux moves. No full qualification inferred. |
| Owner-token limits | **PASS reached uses** one pinned private manifest/layer/signature read scope; no owner-token API calls, visibility metadata explicitly unverified from org. All four always-cleanups removed root-0600 runner-temp auth outside artifacts. Cached public stock CLI has no owner auth mount and no network/pull. Installed switch reads were not reached. |
| A: both complete orders / actual installed stock preparation | **NOT QUALIFIED** full stopped before first install; source recipe remains unverified on installed stock. |
| B: one-time stock recovery / promotion / second unattended boot | **UNTESTED** not reached. INSTALL/EMERGENCY keep gate open. |
| C: media pins | **RETAINED** new complete ISO download still matches frozen bytes and official checksum; writer/GParted pins unchanged. Physical media and unaided followability stay OPEN. |
| Privacy / branch state | 8 source push/PR checks **GREEN** [receipts](../../os/manifest/ci/11g/source-privacy-checks.json); final report push must pass the same unchanged privacy workflow. PR #11 remains **DRAFT**, no merge. Closing cost reserved below. |

### Per-stage firmware and Linux-position events

[Recomputed table](../../os/manifest/ci/11g/stage-table.md), reproduced below. Each
row retains raw vars, QMP hardware context, full protected capture and final stats.
A stage named `protected-first-install` here is an **aborted attempt**. Probe-only
counter snapshots do not replace final session counters.

| Run / order / stage | Protected bytes / final writes | Firmware and Linux position events |
|---|---|---|
| full-3 / first / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| full-3 / first / protected-first-install | MATCH; 0 bytes / 0 operations; failure path recorded | None |
| probe-2 / first / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| probe-2 / first / live-ui-probe | MATCH; 0 bytes / 0 operations | None |
| probe-3 / first / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| probe-3 / first / live-ui-probe | MATCH; 0 bytes / 0 operations | None |
| probe-3 / first / probe-windows-without-linux | MATCH; 0 bytes / 0 operations | pci:00:03.0: Boot0004 → absent<br>pci:00:1f.2/sata:0:65535:0: Boot0002 → absent |
| probe-3 / reverse / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| probe-3 / reverse / live-ui-probe | MATCH; 0 bytes / 0 operations | None |
| probe-3 / reverse / probe-windows-without-linux | MATCH; 0 bytes / 0 operations | pci:00:02.0: Boot0003 → absent<br>pci:00:03.0: Boot0004 → Boot0002; relabel<br>pci:00:1f.2/sata:0:65535:0: Boot0002 → absent |

The five exemptions are exactly probe 3's first-order DVD/target removals, and
reverse-order DVD/target removals plus protected PCI 3.0 auto relabel/renumber
Boot0004→Boot0002. Every one retains exact-GUID ownership and per-boot device context;
Windows remains byte-identical/first. Current full has no boot-variable change.
Historical 11c–11f events/counter shortcomings are not relabeled by this table.

### Commands and evidence integrity

- `python -X utf8 reviews/11-two-disk-rehearsal/verify-11g-evidence.py`: **exit 0**, 10
  matching offline stages, 10 final zero records, 997 archived records scanned,
  `incomplete: []`, **only probe-3 qualified**. Passing collection verifies reached
  records; absence of `full-result.json` and failed full conclusion keep A/B unqualified.
- `python -X utf8 reviews/11-two-disk-rehearsal/replay-11g-full-stop.py`:
  `PROBE-COVERED STOP CONFIRMED: no install; failure counter recorded before QMP quit; zero protected writes.`
- `python -X utf8 reviews/11-two-disk-rehearsal/tabulate-11g-stages.py`: `Stage rows: 10`.
- Fresh probe/full each ran full unittest discovery, Python compilation and all CI/
  release shell syntax checks. Local stock/harness/cache/budget/disk/auth logs and
  archive-credential regression are retained. Broad Windows discovery failed on
  Linux-specific APIs/privileges as recorded; it is not evidence of Linux success.
- Original server ZIPs and their digests are retained, scanned for raw and decoded
  token/ASCII crypt patterns. Only display text is whitespace/LF normalized; FD,
  PNG, JSON artifact bytes and original ZIPs are unchanged. Metadata email/name
  redaction follows the existing collection convention. Replay input hashes are
  checked against committed Git blob bytes. Privacy configs equal origin/main,
  frozen manifests/Containerfile and `disk_audit.py` unchanged. No Gradle daemon started.

| Original artifact | Bytes | SHA-256 |
|---|---:|---|
| Cancelled probe 1 | 47,869 | `0e09722b1df39769098cf591e920ee2e3c18dd640ee79d5da1345e1b4db42d8e` |
| Failed probe 2 | 4,653,078 | `45c547ea2f0dd5366690d1612b47e0bfe10e766f9b4497efd4f2a808b5ffa0c5` |
| Passed probe 3 | 6,379,229 | `219a53fca2def89d852e51e941c45370a2cf09b731fb8d40cd439b7f9d22c043` |
| Stopped full 3 | 3,528,476 | `550704e62003ee9cfc63a9a83333c2614c4fef6162ac6206aeb7ba04ee5583f1` |

### Continuing minute ledger / stop

Same allowance start **2026-10-23T16:21:00Z**, cap **750**, **4 total full runs**.
Integrator-reported org usage was 248/2,000 October minutes, resets 1 November;
not independently queried with the owner token. Counts below are measured per-job
round-up, skipped jobs zero. No reset and no hidden retry.

| Cost | Rounded minutes |
|---|---:|
| 11f final actual closure | 231 |
| Integrator's 11g brief push/PR privacy | 2 |
| Four 11g source pushes / eight privacy jobs | 8 |
| Cancelled setup-only probe 1 | 11 |
| Failed live-tool probe 2 | 19 |
| Successful both-order probe 3 | 28 |
| Same-source full 3, mandatory stop | 17 |
| **Measured before closing report push** | **316 / 750; 3 / 4 full** |
| Closing privacy allowance reserved (no further VM) | **14** |

[Full measured ledger](../../os/manifest/ci/11g/after-full-3-budget.json) and all
pre-dispatch reservations are retained. Last report commit necessarily precedes its
own privacy job costs; final PR body/checks carry the measured closing total. **This
is a stop-rule boundary, not budget exhaustion.** The remaining fourth full is not
used to retry a probe-covered failure. PR stays draft, with all unmet gates open.

**Not verified:** actual installed updater pause/cleanup/pin in 11g, both complete A
orders, frozen AresOS policy after this new preparation, real tty3/rollback/default
undo on the two-disk install, all B, physical laptop/media/German-key interaction,
Windows itself beyond the marker fixture, real RTX/display/network/battery/logind
and unaided novice followability. No mod/Gradle/Minecraft or physical disk action.

**JUDGMENT-CALL:** put the combined pause/cleanup/pin block before the first §5
Windows reboot and repeat before switch; pause alone would leave a staged update
available to finalize. Runtime service masks avoid permanent service changes while
timers remain persistently disabled; permanent-stock update resumption is explicit.
Self-contained pause duplication in pin/owner block is enforced by a synchronization
test; adding a runtime file dependency would make the owner block incomplete. These
are reversible script/guide choices, no payload rebuild or broader firmware rule.

**PLAN-GAP:** the existing keyboard-resolver proof passed the same-source probe and
failed the full; the reason is unverified. Its assertion is retained; missing before/after
LocaledWrapper diagnostics limit root-cause analysis. No protected-disk, firmware,
registry-auth or timeout failure was observed in this full. A further integrator
brief is needed to investigate this probe-covered check and authorize continuation.

**Open questions:** which LocaledWrapper field changed, and what synchronization the
pinned installer uses for restoration; actual installed pause/pending cleanup and
later policy compatibility remain qualification questions. No question was sent
mid-run and no automatic rollback/repin or extra full attempt was made.

Closing local checks: `gitleaks git . --log-opts HEAD --redact` scanned **111 commits**
and printed `no leaks found`; the final staged scan also printed `no leaks found`.
`git diff --cached --check` passed. Both replay/stop-analysis input maps matched
staged Git blob SHA-256 values before committing. The final report push's privacy
checks and exact measured closing total are recorded in PR #11 after they finish;
there is no further VM dispatch.


## 11h: pinned keyboard-source investigation (2026-10-24)

### Zero-cost stage walk-through — BEFORE ANY DISPATCH

Initial `git fetch` and `git pull --ff-only` completed with `Already up to date.`;
`git log -5` showed integrator brief `2cbbe2f` above the completed 11g report.
Read AGENTS, README, briefs 11c–11h and the 11g outcome. No keyboard assertion has
been changed. Earlier local localization captures have no retained ISO provenance;
they cannot establish the exact installed code. The retained ISO listing names
`usr/lib64/python3.14/site-packages/pyanaconda/modules/localization/{localed,utils,installation}.py`.
Add only extraction of these three original files and their SHA-256 receipt to the
existing whole-ISO-verified inspector. An **inspection-only** dispatch comes first:
no VM, fixture, installation, owner-token use, image build or publish. Existing
regressions, release equivalence and privacy checks remain enabled.

The complete remaining walk-through below applies independently in **both disk
orders**. It preserves 11g's first-login stock preparation and every 11c–11f rule.
No dispatch for a probe or full is authorized until the exact-source finding is
recorded; 11h explicitly requires STOP if it shows something other than timing.

| Stage, each order unless stated | Expected transition / accepting rule |
|---|---|
| Baseline Windows, ISO and empty target attached | Exact-GUID auto options for attached QMP devices only; enumeration may change numbers/descriptions. Windows bytes/number/default fixed. 11e device-set and takeover rules. |
| Live keyboard prediction / UI review / install | Keyboard diagnostic itself authorizes no firmware change. Proposed strict 15-second restore equality and German resolver assertions depend on source finding first. Installer may add/recreate only the target-ESP Fedora loader and put it first. 11f permits that Linux position; other fixed entries keep relative order. |
| Closed target audit after install | Proposed installed console/X11 German check reads the target root only; no boot-variable or protected-disk writes. Original protected byte/GPT/EFI and final-counter checks remain absolute. |
| Exact Windows-first restoration | Read back Windows + previous order without Windows, unchanged entry bytes. 11f stable-move check. |
| First stock login, before Windows comparison | ISO detached, both disks attached. DVD auto removal; remaining auto relabel/renumber allowed by exact ownership and attached-device set. Linux BootNext consumed. Known hardware-initialization reboot separately audited. Shim/bootupd target-only Linux recreation/moves allowed; Windows first at installed checkpoints. |
| Pause / cleanup / pin before first Windows reboot | Runtime-mask selected OS updater services, persistently disable timers, wait for no transaction. Require ISO booted digest; remove at most one identified upstream pending deployment, unchanged booted checksum, then pin. No authorized NVRAM change. Booted newer stock STOPs. Hardware setup/finalizers unchanged. |
| Detached Windows after install | BootNext=0000 consumed; target auto removal and possible protected auto relabel/renumber, with only free/former-auto number takeover. Validated target Linux entry may remain. Windows bytes/default strict; original protected marker and zero writes required. |
| Reattach / stock-to-signed-AresOS | Target auto option may return/recycle auto/free ID. Linux BootNext consumed. Repeat pause/pin, no staged state, frozen signature and identity checks. Only target Linux/attached auto changes permitted. |
| AresOS policy / tty3 / rollback | Linux BootNext consumed each boot. Target-only Linux and attached-auto refresh allowed; fixed order and Windows-first strict. Frozen policy, real password/sudo/logout and rollback identity checks unchanged. |
| Rolled-back / persistent / second stock | BootNext consumed, same allowed auto/Linux refresh. Original pinned checksum/digest, no pending/queued deployment, promotion then second unattended stock boot. Timers remain paused. |
| Windows before undo, both disks | Consume Windows BootNext; original marker, Windows first, exact bytes and complete audits. |
| Default undo, both disks | Exact Windows-first stable move; unattended Windows with no BootNext/keys. No disk erasure. |
| Detached Windows after undo | Target auto removal and possible protected auto relabel/renumber under same set/takeover rules. Retained target Linux entry allowed; original marker and zero writes. |
| Fresh reverse order | Closed target-only reset and pristine vars; repeat every preceding stage, including first-login pause/pin, all recovery and detached markers. Original protected baseline remains binding. |
| B, only after both A orders pass | Reattach target; Linux BootNext consumed, permitted auto return/renumber. Repeat pause/pin before re-switch. Record real BLS entry and menu index, select recorded stock through GRUB or already-authorized recorded one-time fallback. Verify stock nonzero-index boot, promote identity-checked recorded stock, confirm second unattended stock. All raw vars/device/final-counter/offline audits retained, same Windows/fixed-order and target-only Linux rules. |

At each shutdown, read the final QMP protected counter before termination (explicit
failure-path receipt on errors), then closed-file byte/GPT/EFI/NVRAM audit. QMP
unavailability leaves a session unqualified. No foreseeable new firmware transition
requires a wider rule. Unknown firmware, protected writes, auth/signature rejection,
wrong booted stock, updater/policy conflict or a different probe-covered full failure
means STOP. Source investigation may itself require STOP before these stages.

Shared allowance still starts **2026-10-23T16:21:00Z**, **750 minutes**, now **5 total
full runs** by 11h. The ledger does not reset. Three full runs have already been
used; inspection does not consume a full slot. Reserve 42 minutes for inspection,
42 for a future probe, 182 for a future full and closing privacy cost before their
respective dispatches. Existing estimate remains 111–133 VM minutes (central 120),
156-minute full VM step / 180-minute job; two 15-second polls and target read audits
fit existing margin. No probe/full dispatch until source finding, then fresh
same-SHA successful probe before one complete both-order A + B full.


### Exact-source finding — mandatory PLAN-GAP STOP

**Done:** inspection-only source `6b08aa30251da875481b4af0c646e508d245d935`,
[run 40099746381](https://github.com/Ares-Empire/AresOS/actions/runs/40099746381),
completed successfully. Fresh official checksum and all **9,068,650,496 ISO bytes**
match frozen SHA-256 `776b76f3417723440ee1823d79ec02a2c22860df196d219024edb062ad00d8e6`.
The inspector extracts the original localization files from that ISO's SquashFS,
with [path/length/SHA receipt](../../os/manifest/ci/11h/inspect-1/installer/localization-source.json).
These are the actual Python 3.14 installed modules, not the earlier upstream capture.

| Original ISO module | Bytes | SHA-256 |
|---|---:|---|
| `localed.py` | 17,659 | `f0f8eb597455f88e656c81c9bcb3f3636418a6d92883b2c9ef4f9c012292a8af` |
| `utils.py` | 3,498 | `9131865a34cb8e978d34083f9c981e84401fbf9852f7ca4f213b2dc9abb001e1` |
| `installation.py` | 9,483 | `f3a348993523390c757aeab826a86110f9c92f817372173f91af2b06c34381db` |

Read the full extracted [LocaledWrapper](../../os/manifest/ci/11h/inspect-1/installer/usr_lib64_python3.14_site-packages_pyanaconda_modules_localization_localed.py),
[resolver](../../os/manifest/ci/11h/inspect-1/installer/usr_lib64_python3.14_site-packages_pyanaconda_modules_localization_utils.py)
and [installation task](../../os/manifest/ci/11h/inspect-1/installer/usr_lib64_python3.14_site-packages_pyanaconda_modules_localization_installation.py).
For the recorded module choice `XLayouts=['de']`, `VirtualConsoleKeymap=''`:

1. `get_missing_keyboard_configuration` calls `_resolve_missing_by_conversion`,
   then `LocaledWrapper.convert_layouts(['de'])`.
2. `convert_layouts` reads original layouts/variants and console keymap. It **does
   not save options**. It calls `set_and_convert_layouts`, which invokes
   `SetX11Keyboard('de', 'pc105', '', '', True, False)`, then reads VConsoleKeymap.
3. Restoration calls `set_layouts(orig_layouts_variants)` and
   `set_keymap(orig_keymap)`. The omitted `options` argument defaults to `None`,
   producing **empty options**, not the saved value. Calls are
   `SetX11Keyboard(original_layouts, 'pc105', original_variants, '', False, False)`
   and `SetVConsoleKeyboard(original_keymap, '', False, False)`.
4. These are sequential ordinary synchronous proxy invocations. The function returns
   after the restore calls; there is no deferred restore callback, poll or waiting
   for the original tuple. The [dasbus client implementation](https://dasbus.readthedocs.io/en/latest/_modules/dasbus/client/handler.html)
   documents the ordinary synchronous call path; [localed's API](https://www.freedesktop.org/software/systemd/man/259/org.freedesktop.locale1.html)
   describes the conversion flags and configuration properties. Those current API
   references provide context, not proof of exact dependency bytes or live timing.
5. The source itself therefore demonstrates an **options-preservation defect**,
   independent of any possible property-publication delay. By comparison,
   `write_x_configuration` in this same ISO explicitly saves `saved_options` and
   supplies them when restoring. Conversion does not. The exact pinned wrapper
   also lacks the newer upstream capture's conversion lock.

**Verified counterexample, without a VM or host bus:**
`python -X utf8 reviews/11-two-disk-rehearsal/analyze-11h-keyboard-source.py` executes
unmodified AST class/function nodes extracted from the original artifact. Only the
bus/property storage, logging and plain-layout parser/formatter are mocked. Calls
apply immediately, with no callbacks/external writer. Input matches the observed
module choice (`de`, empty console model):

| Synchronous mocked live state | Resolver output | State after all calls |
|---|---|---|
| `('us', ['de'], [])` | `(['de'], 'de')` | `('us', ['de'], [])`, strict tuple equality PASS |
| `('us', ['de'], ['caps:escape'])` | `(['de'], 'de')` | `('us', ['de'], [])`, strict tuple equality FAIL |

Thirty-one repeated state reads at **simulated** 0–15 seconds remain unequal in the
second case. They are a deterministic counterexample, **not measured localed/VM
settle timings**. Every recorded call supplies empty options. There is no operation
that could restore `caps:escape`, however long the diagnostic waits. Output:
`PLAN-GAP reproduced from exact ISO AST: German result, original keymap/layout restored, nonempty options lost permanently; no VM or host bus used.`
[SHA-bound analysis and all calls/values](../../os/manifest/ci/11h/keyboard-source-analysis.json).

**Comparison with full 3:** the retained failed transcript proves module `de` /
empty console model and failure at exact live tuple equality; it contains no before/
after tuple. Both passing probe orders used the same resolver, and their recorded
installation source SHA equals this exact ISO module's SHA. Empty options can pass
and nonempty options can fail without a timing race, as the counterexample shows.
This does **not** establish which field actually differed in full 3 or that this
options defect caused that failure. A race/concurrent writer remains possible;
claiming a race as the established explanation would exceed the evidence. Also,
the harness uses one wrapper instance for both reads, rather than the fresh wrapper
suggested in 11h's introductory explanation. The harmless mpath warning remains
present in both passing probe orders; no new causal claim is made.

11h requires: **“If the source shows something other than a timing race, stop and
report a PLAN-GAP.”** The permanent options loss meets that condition. Therefore:
**no settling implementation, installed-target audit change, probe or full dispatch
followed the source finding**. The existing assertions remain intact; no installer,
image, firmware rule or offline audit was patched to bypass the source result.
The installed file paths are now known from the task: `/etc/vconsole.conf` and
`/etc/X11/xorg.conf.d/00-keyboard.conf`. Reading/asserting them in both target roots
remains explicitly blocked work, not evidence already obtained.

### Gate → evidence and remaining acceptance

| Gate | 11h result / evidence |
|---|---|
| Fetch / FF pull / source first | **DONE**, initial fetch/pull already current; exact pinned source extracted and read before keyboard changes. |
| Walk-through before any dispatch | **DONE**, complete both-order/B table above; only inspection dispatched. |
| Source timing premise | **PLAN-GAP STOP**, exact methods can permanently lose options; actual full-3 cause still unproven. |
| Strict 15-second equality and delayed/never-restored regressions | **NOT IMPLEMENTED / NOT RUN**, blocked by source-first STOP. Existing nine local keyboard/review/probe/download tests pass, including wrong layout/keymap and restoration-flag rejection. |
| Probe/full settle timings | **NONE**, no 11h VM run. Mock simulated observations are labeled as such. |
| Installed console/X11 German proof and non-German target rejection test | **NOT IMPLEMENTED / NOT RUN**, stop preceded installation and these changes. No installed result claimed. |
| 11g updater inventory / pause / cleanup / pin | Existing inventory, real-status mocked replay and negative/idempotency regressions retained unchanged. Actual installed preparation, pending observation/discard and later frozen-policy compatibility **NOT REACHED** in 11h. No newer booted stock was accepted. |
| 11g failure-path counters | Existing real full-3 receipt and 27 harness regressions retained. Inspection starts no QEMU and produces no new disk counter. Historical 11f missing record stays unqualified. |
| Per-stage firmware/Linux events / protected checks | **No new VM stages/events** in 11h. Prior ten matching 11g captures/ten final zero counters and five allowed probe auto events retain their original limited qualification; no historical evidence relabeled. |
| A, both complete orders | **NOT QUALIFIED**; no new install/switch/policy/tty3/rollback/default undo or detached Windows markers. |
| B, one-time recorded stock, promotion, second unattended boot | **UNTESTED**, still open, not a passed/clearly resolved recovery path. |
| C, media inputs | Frozen pins retained; fresh whole ISO verified again. Physical media and unaided novice followability remain open. |
| Owner-token boundaries | All three owner credential/preflight/pull steps **SKIPPED** in inspect mode; VM step and image/build/publish jobs skipped. Always cleanup passed. No owner token read locally or used in inspection, **zero owner-token API calls**. Normal logged-in `gh` / ephemeral job token read only workflow/equivalence metadata. |
| Privacy | Both source push/PR checks **GREEN**, all three steps success, actual missing-PRIVATE_TERMS warning absent. Configs unchanged; final report push must pass the same checks. |
| PR / physical install gate | Keep **DRAFT**, INSTALL/EMERGENCY reflect source STOP and unqualified installed recipe/recovery. Physical installation remains NOT RELEASED; no merge. |

### Commands, retained evidence and privacy

- Inspection Ubuntu job: **`Ran 162 tests in 3.900s` / `OK`**, Python compilation,
  shell syntax and frozen release-equivalence verification passed. ISO verification
  printed the frozen SHA and 9,068,650,496 bytes. [Completed transcript](logs/11h/inspect-1.txt).
- Local `python -m py_compile os/ci/installer_inspect.py` passed.
  `python -m unittest discover -s os/tests -p test_installer_webui.py -v` printed
  **`Ran 9 tests in 0.110s` / `OK`**; [log](logs/11h/local-webui.txt).
- Source-analysis command above passed; it verifies the server ZIP digest, original
  module lengths/SHA and expanded bytes, same installation-source SHA as probe 3,
  skipped owner/VM steps, cleanup, native count and both synchronous cases.
- [Original evidence ZIP](artifacts/11h-inspect-1-two-disk-evidence.zip): **3,004,373
  bytes**, SHA-256 `9d6a008214721977c3609758d88bd4441d5c8a7b0c18358e58886c8b5e73a7df`.
  Original workflow ZIP and its hash receipt are retained. Collector scans all archive
  entries for raw/base64-decoded credentials and refuses auth-file paths before
  extraction. Original ZIPs and exact Python sources are unmodified. Only display
  text is normalized; the large listing stays inside the original ZIP, as before.
- [Source privacy proof](../../os/manifest/ci/11h/source-privacy-checks.json) verifies
  push 40099639559 and PR 40099645938, all three checks and no actual skipped-term
  warning. [Unchanged input hashes](../../os/manifest/ci/11h/unchanged-inputs.json)
  bind frozen Containerfile/manifests, disk audit, keyboard proof and privacy configs.
  First local comparison tried `.gitleaksignore` against origin/main, which has no
  such file; corrected comparison against the brief head passed. The ignore is
  unchanged, and no privacy exclusion was added. No Gradle daemon was started.

### Continuing ledger and stop boundary

Same **2026-10-23T16:21:00Z** start; **750-minute / 5-full authorization** under 11h.
No allowance reset. The unchanged guard still enforces the stricter four-full
ceiling during this inspection; updating it and its regression to five is deferred
with the other implementation after the source-first STOP. Three total full runs
have been used, none newly dispatched. This is not budget exhaustion.

| Cost | Rounded minutes |
|---|---:|
| Actual 11g closure | 318 |
| Integrator brief 11h push/PR checks | 2 |
| Source-extraction push/PR privacy checks | 2 |
| Inspection-only 40099746381 (13:48:49–14:02:28 UTC) | 14 |
| **Measured before closing report push** | **336 / 750; 3 / 5 authorized full runs** |
| Reserved closing privacy allowance | **14** |

[Inspection guard](../../os/manifest/ci/11h/inspect-1/11c-dispatch-authorization.json)
measured 322 + 42 reserved; [after-inspection ledger](../../os/manifest/ci/11h/after-inspect-budget.json)
measures 336 + 14 closing reserve. Report necessarily precedes its own privacy jobs;
the final PR body/checks will carry the measured closing total. Integrator-reported
org usage remains 248/2,000 October minutes, reset 1 November; owner token was not
used to query billing or package visibility.

**Not verified:** actual full-3 differing tuple/causality, real settle timings,
installed console/X11 German configuration, installed stock pause/pending discard/
pin, both complete A orders, later frozen updater policy, all B and all physical
laptop/media/typing/hardware checks. The mocked options counterexample cannot
substitute for any of these. No mod/Gradle/Minecraft or laptop disk action.

**JUDGMENT-CALL:** use the existing inspection-only path to obtain exact ISO bytes
before spending a probe/full or changing the diagnostic. No product behavior
changed. Preserve strict tuple equality and follow the explicit source-first STOP.

**PLAN-GAP:** polling alone cannot restore X11 options that the pinned conversion
never saved or passed back. The brief's pure timing premise is insufficient. A
follow-up must decide how to make the diagnostic preserve live state without
changing the pinned installer/image or weakening equality, then implement the
remaining settle/target checks, cap regression, fresh probe and full. No option was
silently discarded or normalized to get green.

**Open questions:** what actually differed in full 3; the authorized handling of
this source defect; actual installed keyboard/updater/recovery behavior once the
source blocker is resolved. No question or approval request was sent mid-run.


Final local closure checks: staged gitleaks printed `no leaks found`; history scan
of **114 commits** printed `no leaks found`. `git diff --cached --check` passed.
All analysis input hashes and three exact ISO sources matched staged Git blob bytes
across 165 expected paths. Final report/privacy outcome is recorded on PR #11 after
this commit's checks complete. No additional dispatch, force-push or merge.
