# Pre-run assumption audits

## 11b: real Web UI continuation

11b starts with a fresh **350-minute / three-full-run** allowance. Probe and
checks jobs count toward minutes. No full run is authorized by the earlier
package-11 evidence. A full dispatch must consume a successful probe artifact
from the exact same commit, in addition to the existing signed-release guard.

The first discovery probe is deliberately not a full-run qualification: it
must first establish the real server and destination controls. Later probe
qualification must include all pre-install pages, the review, and both drive
orders before the installation driver is enabled.

| Assumption before discovery | Evidence / required observation |
|---|---|
| Start exactly `liveinst` as the live desktop user | Frozen ISO launcher calls pkexec and reconstructs `liveuser`'s user-manager environment. The probe invokes it as liveuser with that environment, without LIVECMD or kickstart. Save the actual launch log and server unit. |
| The Web UI listens on loopback HTTP port 80 | Upstream `webui-desktop` and Cockpit wrapper at `9f480b6ffeef3a6aa64fd2e0ddcd1a9632bca68f` indicate this port and `/cockpit/@localhost/anaconda-webui/index.html`. This is a hypothesis until the pinned guest's `ss`, curl and actual unit confirm it. |
| A byte-preserving relay carries HTTP and WebSockets | Guest Python TCP relay binds 8080 and connects to loopback 80. QEMU forwards host loopback 18080 to guest 8080. Curl must pass inside the guest, and Chromium must render the actual Anaconda navigation control on the host. No remote service/listener is exposed on the laptop. |
| Destination selectors | Upstream installer tests provide the `anaconda-screen-method-*` IDs as candidates. Retain every actual page's text, control IDs and screenshot. Process presence and a Portal frame cannot pass. |
| Browser dependencies | The hosted venv inherits system packages, and explicitly imports crypt, PIL and Playwright before creating disks. The initial job at `6683e19` was cancelled during runner cleanup after identifying the isolated venv's missing PIL access; it never booted a VM. |
| Disk roles and writes | Retain the actual serial/device map, make target-only selection, then shut down cleanly, require final zero protected writes, compare complete protected bytes/GPT/EFI offline and preserve/diff NVRAM. |

Browser/transport difference: host headless Chromium replaces guest Firefox;
HTTP and WebSocket traffic cross only the disposable QEMU user network and the
guest byte relay. The ISO launcher, Anaconda service, pages and backend remain
the ISO's own. The existing direct ISO-kernel boot plus serial console remains
an additional previously recorded difference from a physical USB boot.

Discovery dispatches: [cancelled 39873210999](https://github.com/carlsenares/AresOS/actions/runs/39873210999)
at `6683e19`; [corrected probe 39873265524](https://github.com/carlsenares/AresOS/actions/runs/39873265524)
at `6bfefc8`. Neither is a full run. Outcomes and final minute totals follow in
the 11b report.

### Discovery results and complete-preview dispatch

- Probe 1 (`6bfefc8`, 39873265524) launched the real Welcome page as liveuser
  (visually inspected guest screenshot), but its serial HTTP/service inventory
  command timed out before host Chromium. The missing partial-command log
  prevents attributing the stall specifically to HTTP or a pager. Cleanup
  host-terminated QEMU; protected bytes/layout/EFI and Windows NVRAM matched,
  but this VM has no final zero-write counter proof. It is a failed probe.
- Probe 2 (`a7a0a44`, 39875264662) uses bounded curl calls, noninteractive
  service output and timeout logging. The real `ss`/unit/wrapper/curl and
  Chromium evidence confirms the original loopback HTTP listener and relay.
  Actual Welcome, Date/time, destination modal and target-only page screenshots
  were captured and visually inspected. `MICRON-KEEP=vda` and
  `CRUCIAL-TARGET=vdb`; both modal rows are present, only vdb is selected.
  Its actual guest shutdown/final counters, offline full-disk/GPT/EFI and
  Windows entry checks passed. Linux printed 104 passing regressions.
- Probe 2 is explicitly **destination-only**, not full authorization. Its
  immediate final frame still shows an indeterminate/space-warning state;
  it did not wait for the scenario controls, reach review or reverse drives.
  No minimum capacity is inferred from the blank loading text, and no storage
  check is overridden. The complete probe waits for the actual erase-all
  control, or fails with a screenshot.

The next harness uses one shared UI flow for probe and full mode: German-only
keyboard, Berlin timezone, exact target-only/erase-all selection, unencrypted
disposable trial, password-protected wheel administrator `ares-recovery`, locked
root, full review text and explicit new target EFI check. Read-only backend
properties must confirm the choices. Probe tests the erase button's actionability
with Playwright's non-clicking trial mode, never starts installation, and
repeats in both drive orders. Completion/error selectors are checked against
the actual ISO-served JavaScript; their post-install rendering is necessarily
a full-run-only observation. Root serial poweroff replaces the owner's final
UI reboot only to permit the mandatory closed-image audit.

Only that complete, successful, exact-commit artifact may authorize a full
dispatch. The original unsupported-live-kickstart guard remains exercised;
neither legacy media nor a constructed stock disk is permitted.

### Probe 3 and final command/menu preflight

Probe 3 (`502676b`, 39877073155) passed 105 Linux regressions and the signed
release/runtime guard, but stopped before UI launch: direct terminal help has
Python 3.14 ANSI colors around `--kickstart`, unlike the earlier redirected
help fixture. The guard failed closed on the formatting, not on a newly
supported kickstart path. Its original colorized help is retained as a
regression fixture. The parser now removes CSI formatting and the inventory
also requests redirected, plain help; the unsupported-live rejection remains
mandatory and tested with both actual captures.

Its missing-installer diagnostic listing returned 1, which skipped the old
cleanup's poweroff. The protected offline hash/GPT/EFI and Windows entry match,
but this failed probe again has no final live-VM zero-write counters. Cleanup
now always attempts orderly poweroff after diagnostics, propagates every
shutdown/write failure, and has a regression for both failure paths.

Before any full run, the next probe additionally captures the ISO's actual
bootloader Python sources/config and serial kernel arguments. The prior
switch fixture used image-builder; serial-console propagation by this installer
must be evidenced, not silently assumed. The frozen ISO inventory confirms
14 Python source files at the inspected module path. A harmless QMP Shift
press and guest screenshot also exercise the observer's keyboard command.

The existing GRUB adapter's guessed `ostree-1-default` is replaced by the
uniquely learned nondefault BLS entry for the recorded stock checksum. Its
actual numeric index determines the QMP Down count and is recorded; OS suffix
and index are not copied from the image-builder fixture. Regressions require
the checksum and a positive index, support observed OS-name alternatives, and
reject ambiguity, index zero and unsafe IDs. Actual menu rendering/selection
and installed boots remain full-run observations, never claimed by a dry run.

### Probe 4 transport failure and remaining nondestructive branches

Probe 4 (`c4bcb1d`, 39879865566) stopped **before tools/fixture/VM creation**.
The response advertised **9,068,650,496 bytes** but ended at **452,788,224**;
the partial-file hash was `33bcbca9ca22d31fbb5b3b26228149f147212ebaf4f2a78c121611fefd0eb273`.
Its freshly downloaded official checksum still equals the frozen pin. This is
evidence of an incomplete transfer, not evidence of a complete replacement
ISO. No pin is changed and no partial payload is booted. The next probe makes
a fresh request to the same URL; the exact complete-file hash remains mandatory.
A regression on this receipt distinguishes premature EOF from a complete
hash mismatch, which continues to stop qualification.

The complete probe now also runs the full harness's target-close/reset helper
and Windows-only marker mode before either is used after installation. These
are safe on the empty disposable target and make drive detachment, media
removal, firmware-entry preservation and the file-reset commands real probe
observations. Both order previews must still pass, and the artifact must prove
these additional branches before full authorization. No NVRAM/disk assertion
is relaxed for firmware device enumeration changes. This pre-install marker
check cannot substitute for the required post-install and post-undo checks.

### Probe 5: confirmed console propagation; correct the keyboard checkpoint

Probe 5 (`60758f6`, 39880735063) re-downloaded the complete pinned ISO,
passed **111 Linux tests**, and confirmed the actual bootloader preserves
`console` arguments, including multiple consoles in order. Its effective
`Bootloader.preserved_arguments` includes `console`. The local serial-transport
boot args are present. The anonymous registry metadata check also found the
installer post-script's `stable` tag still at the exact tested stock digest;
no layers or owner registry credentials were used.

The real keyboard modal selected **only `de`**, as its screenshot and text show.
The harness then waited for `anaconda-screen-language-selected-keyboards`, an
upstream-version selector absent from this ISO, before pressing Next. The
Welcome summary still read `us`; this does not establish what Next would
commit. The next probe requires the actual modal's selected list to be exactly
`de`, saves it, presses Next, then immediately requires both D-Bus XLayouts and
VirtualConsoleKeymap to be German. The same checks remain mandatory at review
and on the installed console; no keyboard assertion is relaxed. The actual
modal capture backs a regression, and snapshots now inventory all element IDs.

Cleanup's corrected failure path ran in the real VM: orderly guest shutdown,
final zero protected writes, identical offline protected hash/GPT/EFI and
unchanged Windows boot entry. Probe 5 remains failed and cannot authorize full.

### Probe 6: the UI commits X layouts; console configuration is derived later

Probe 6 (`221ca1a`, 39882648993) passed 112 Linux regressions and reached the
Date/time page after the German modal. The real backend returned **XLayouts =
`["de"]`**, but **VirtualConsoleKeymap = `""`**. The earlier immediate console
property assertion was a lifecycle assumption. Upstream's actual
`KeyboardInstallationTask.run` resolves missing configuration with
`get_missing_keyboard_configuration`, then calls `write_vc_configuration`.
The next probe requires that call path in the pinned ISO's own source, invokes
that ISO's resolver on the exact committed UI choices, and generates the
vconsole file only under a temporary live `/tmp` directory. It requires
**resolved `de` and generated `KEYMAP=de`**, with live localed configuration
restored and Anaconda's module choices unchanged. Review repeats this proof;
the installed `/etc/vconsole.conf` and real German QMP tty3 test remain strict.
Empty console state without that conversion/file proof cannot authorize a run.
This is a keyboard-only temporary fixture, not an installed stock disk or an
alternative installer route.

The failed probe's offline protected bytes/GPT/EFI, original Windows entry and
final zero-write counters passed. A redundant Ctrl-C after an already finished
command also disrupted a diagnostic shell command. The adapter now tracks
whether a command is actually pending and interrupts only a timed-out command;
diagnostics still cannot suppress poweroff or any write/shutdown failure.

### Probe 7: investigate the exact shipped UI before more selector changes

Probe 7 (`ccb1b81`, 39884771824) passed 113 Linux regressions and the release
guard, but the expanded keyboard check no longer saw the exact German X-layout
property. It stopped before running the resolver or reaching review. This
does not qualify the keyboard, and the check is not bypassed. Protected bytes,
Windows NVRAM and final zero-write counters passed; the command-pending cleanup
correction also completed without the previous diagnostic-shell corruption.

The frozen ISO inventory contains `index.js.map` (3,566,994 bytes). The next
dispatch is source inspection only, no fixture or VM: extract this map's actual
application sources and inspect the keyboard state/Next code plus remaining
page IDs. This replaces dependence on newer upstream source assumptions. The
guest Firefox and host Chromium currently both exist; if this permits competing
state updates, browser replacement must leave only the host UI client. Any
such change requires a new complete, exact-commit probe before full dispatch.

### Exact-source inspection 8 and the next complete probe

Inspection 8 (`1fa92a0`, 39886346092) passed with the exact pinned ISO hash,
extracting 102 application sources from its shipped source map. No VM ran.
The actual `KeyboardDialog.saveAll` closes without awaiting `onSaved`, while
`handleSaved` first awaits the compositor update, then writes XLayouts. The
next probe closes only liveinst's exact liveuser Firefox profile after normal
launch, confirms the original backend remains ready, and lets host Chromium
be the sole UI client. After Save it requires five consecutive German backend
readings before Next. The cause of probe 7's change is still unproven; the
next check logs raw keyboard properties before imports and checks they survive
imports and conversion. Keyboard assertions remain strict.

The exact `StorageReview.jsx` has ordinary table cells, not `data-device`,
`data-action` or `data-mount` attributes. Its columns are device, size, action,
encryption, mount point, helper. The parser reads those actual cells, still
requiring only target parents and a newly formatted target EFI. Account,
password, timezone, scenario, encryption, review confirmation and completion
controls were checked against these frozen sources. Progress failure uses the
actual `status-danger` class. Keyboard JSON export is one quoted Python command
so its checksum-framed stdout contains only JSON; diagnostic state uses stderr.

Completed cost before the next probe is **107 rounded job minutes**, with
**zero full dispatches**. A 42-minute probe reservation leaves the 350-minute
cap intact. No full run is authorized until both complete order previews and
the detached marker/reset branches pass on that exact commit.

### Part B command export preflight

While probe 9 (`28a8d09`, 39888209565) runs, source review found the part B
BLS heredoc terminator would receive the framing helper's output redirection.
The command now passes the complete Python program as one shell-quoted `-c`
argument. A regression executes the generated program against actual temporary
BLS files, including a directory with spaces and a quote, and rejects a missing
deployment. The exact read-only export is also added to live inventory, shared
by probe and full mode. An empty live BLS list qualifies only command transport;
actual installed stock identities and menu choices remain full-run observations.
This source change requires a replacement complete probe, regardless of probe
9's eventual result. No full dispatch is made using stale evidence.

The same frozen account source asynchronously guesses a username on full-name
blur if username is empty. The driver now enters the explicit `ares-recovery`
username first, then the full name, to avoid racing that suggestion. It still
requires the exact account and wheel membership from the backend at review.

### Probe 9: browser exit tears down the installer

Probe 9 (`28a8d09`, 39888209565) passed 113 Linux regressions and the ISO/release
guards. Its exact-profile Firefox termination succeeded and immediate HTTP
readiness passed, but Anaconda then exited and removed its effective config.
The next read-only bootloader inventory failed with `KeyError: 'Bootloader'`;
diagnostics contain `Exiting due to channel error`. No host UI navigation or
installation occurred. Final zero protected writes, offline protected hash/
GPT/EFI and Windows boot-entry preservation passed. Cost is now **120 minutes**,
zero full dispatches.

The browser handoff now pauses the exact liveuser Firefox profile's entire
process tree with SIGSTOP, verifies every member stopped, and keeps its parent
launcher alive. This includes renderer processes, preventing a second active
UI client without triggering Anaconda's browser-exit cleanup. The host browser
and transport remain the only installation click-path differences; the paused
guest browser and serial audit shutdown are recorded explicitly. A fresh
complete probe must prove backend/configuration lifetime and every UI page.

### Probe 10: real review reached; qualify computed completion selectors

Probe 10 (`d8d6fa9`, 39889623330) printed `Ran 114 tests in 4.088s`, `OK`.
The paused Firefox tree kept Anaconda/config alive. Every real pre-install
page was reached: German Save showed `de`, backend XLayouts stayed German,
and the actual installation resolver produced `KEYMAP="de"` with live/module
state preserved. Berlin, explicit recovery username, encryption off and the
entire-target route reached Review. Its sole table is `vdb`, including new
formatted EFI `vdb1` at `/boot/efi`, ext4 `vdb2` `/boot`, and Btrfs `vdb3`
for `/`, `/home`, `/var`. Full review and modal/account screenshots were
visually inspected. No protected `vda` row is present.

It stopped before backend review readback and reverse order: the completion
check searched compiled JS for literal `status-success` and
`critical-error-bz-report-modal`. The exact sources assemble both dynamically
from prefixes/suffixes, so those literals are correctly absent. This was a
harness check error, not installer failure. The next check verifies the exact
served bundle SHA-256 `9e456995a4be3d09b2b81b7e55f363d09577e688b8361d90081e1484cfb4f449`
and shipped source-map SHA-256
`de301b46d770b5ce75ee3b00be8416c5b8de1a5348dfe0c4ab282f8e8b3ef36a`,
then requires the actual progress status assignments/class formula, error
prefix/modal formula, and navigation ID in that map. A regression consumes the
three original source files, proves the literals absent, and rejects changed
state names/prefixes. Full mode uses only those qualified computed selectors.

Final zero writes, offline protected bytes/GPT/EFI and unchanged Windows boot
entries passed. Probe 10 is failed and cannot authorize installation. Its
31 rounded minutes bring completed cost to **151/350**, still **0/3 full runs**.

### Probe 11: strict firmware stop; no full run authorized

Final probe 11 (`24118e1`, 39892768284) printed `Ran 115 tests in 3.284s`,
`OK`, and passed the first-order full UI preview, exact bundle/map selector
proof and backend review readback. SelectedDisks was only `vdb`; XLayouts was
`de`, the actual resolver generated `KEYMAP=de`, timezone was Europe/Berlin,
and the password-set wheel recovery account/root-lock checks passed. The target
remained empty after preview. The real QMP input/observer checkpoint passed.

The subsequent **pre-install** Windows-only marker boot succeeded through
original Boot0000, protected ESP GUID `7c0a0246-ee3e-4923-9f9d-fa9bc78c85d5`,
and `\\EFI\\Microsoft\\Boot\\bootmgfw.efi`, with both ISO and empty target
detached. Windows's entry remained byte-identical and first. All three final
counter records are zero, and initial plus three offline protected snapshots
match SHA-256 `32d28d0aee688053d36c31deb3a1288ca15defce2aeed5c4b380644fbd12c036`,
both GPT copies, partition GUIDs/bounds and EFI file hashes.

However, OVMF removed existing **Boot0002 (UEFI QEMU DVD-ROM QM00001)** and
**Boot0004 (UEFI Misc Device 2)** and removed those IDs from BootOrder. The
unmodified strict predicate raised **`PRODUCT FAILURE: existing boot entry
changed`**. Both original variable stores/JSON snapshots and a derived
`nvram-stop-analysis.json` are retained. This occurred before installation;
the evidence does not establish an Anaconda/AresOS Windows-disk write or loss
of Windows Boot Manager. It does establish a failed mandatory firmware audit.

**STOP honored.** No predicate or test was relaxed, no workaround or further
VM dispatch followed, and no full run was authorized. Target reset and reverse
order were not reached; installation/switch/tty3/rollback/undo and GRUB remain
unqualified. Final cost is **168/350 rounded job minutes, 0/3 full runs**; the
remaining allowance is unused because of the stop rule, not budget exhaustion.
Resolving the fixture's automatic entry pruning versus the strict NVRAM
contract needs a future integrator decision, not an exception made here.

## Before VM run 1 (probe)

This is the first of at most two conservatively counted VM automation runs.
It probes the actual UI and disk names before installing anything. It is not
an installation qualification. Completed inspection/check jobs used 19 rounded
minutes; even reserving the entire next job's 110-minute timeout stays below 450.

| Assumption | Evidence checked before dispatch | Run-time requirement |
|---|---|---|
| Exact ISO bytes | [Inspection 1 download](../../os/manifest/ci/11/inspect-1/installer/iso-download.json): 9,068,650,496 bytes; full SHA-256 equals the frozen live pin. Inspection 2 repeated that hash. | Re-download and require the same hash; never refresh the pin. |
| Boot arguments / kernel | [ISO GRUB](../../os/manifest/ci/11/inspect-2/installer/EFI_BOOT_grub.cfg): `root=live:CDLABEL=Bazzite-Live enforcing=0 rd.live.image`, kernel/initrd under `images/pxeboot/`. | Boot those ISO files, adding only the serial console for observation. This differs from the owner's firmware-to-ISO GRUB route. |
| Embedded stock payload | [Container store metadata](../../os/manifest/ci/11/inspect-2/installer/var_lib_containers_storage_overlay-images_images.json): the ISO's `bazzite-nvidia-open:stable` resolves to `sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151`, the tested 06e base. | Installed `bootc status` must match; metadata alone does not qualify installation. |
| Live login | [Actual livesys-main](../../os/manifest/ci/11/inspect-2/installer/usr_libexec_livesys_livesys-main): creates passwordless liveuser and deletes the live root password. | Actual serial login must succeed; no installed password is unlocked. |
| UI launcher | [Actual liveinst](../../os/manifest/ci/11/inspect-2/installer/usr_bin_liveinst): reconstructs the desktop environment from `PKEXEC_UID`; launches Anaconda Web UI/Firefox. | Start with liveuser's desktop environment, capture the actual frame, try a bounded QMP keyboard probe; never install from an unexamined screen. |
| Fallback is not ordinary liveinst kickstart | The same launcher explicitly warns that kickstart arguments are unsupported on Live ISO installs. It also documents `LIVECMD` to run an alternative Anaconda command in the same prepared environment. | Do not pretend `liveinst --kickstart` is the click path. Any direct same-ISO Anaconda fallback needs an explicit recorded difference and leaves media/followability open. |
| Partition roles | Harness creates GPT ESP/MSR/NTFS/recovery on a 50 GiB sparse file and a blank 49 GiB file. Both are writable in QEMU; tests reject read-only protection or ambiguous missing devices. | Read both GPT headers/tables, all EFI file hashes and actual guest serial/device mapping. Names are learned from that VM, never copied from the owner guide. |
| Windows-like boot | Original EFI marker source reads BootCurrent and reports loaded device/file path; `Boot0000` names the protected ESP GUID and Microsoft path. | Marker must report BootCurrent 0000, that exact ESP GUID and Microsoft path. Firmware fallback alone does not pass. |
| Offline auditing | Regressions check GPT CRC corruption, changed EFI/disk hashes, lost/changed Windows entry, writes despite restored bytes, wrong shutdown provenance and final counter ordering. Linux checks-only passed 87 tests before the later VM adapters; adapters also have local regressions and will run on Linux before VM boot. | After guest shutdown QEMU stays stopped long enough to collect final write counters, then exits. `fuser` must show the image closed before hashing. |
| NVRAM baseline | EDK2 authenticated-variable layout checked against `MdeModulePkg/Include/Guid/VariableFormat.h`; replacement/deleted-record regressions pass. | Initialize only disposable OVMF files. First marker boot establishes firmware-created device entries before installation; preserve Windows's entry payload, then diff every stage. |
| Release unchanged | Git comparison against `5578ab21b880091f26bfdc2eda22dd4f304a602b` passes for runtime/config/base/keys/lock. | Existing release guard and guest signature verification remain required before switching; no build/publication. |

GRUB entry titles/indexes are not assumed in this probe. They must be recorded
from the actually installed/switched target before any recovery selection.

## After run 1, before native fixture and the final full allowance

[Probe run 39866564466](https://github.com/carlsenares/AresOS/actions/runs/39866564466)
passed 91 Linux regressions, re-verified the complete ISO and unchanged signed
release source, and compiled the original EFI marker. Disk preparation then
failed before filesystems/VM boot: `losetup --json DEVICE` returned non-JSON.
The correct listing query is `losetup --list --json --output NAME,BACK-FILE DEVICE`.
The new regression requires those arguments and refuses a mismatched backing
file. The loop was detached by `finally`; there is no product-failure evidence
and no running VM. This failed preparation still consumes allowance 1 of 2.

The next dispatch is **native fixture only, no ISO download and no VM**. It must
exercise the real corrected listing query, filesystem creation and offline
GPT/EFI audit before the final full run. Completed job quota proxy: **29/450**
minutes; fixture timeout reservation plus the final 110-minute job remain below
the cap. No assertion is removed or weakened.

## Before full attempt 2 (final)

[Native fixture 39867994684](https://github.com/carlsenares/AresOS/actions/runs/39867994684)
passed 94 Linux regressions and then the real file-backed disk preparation and
offline audit. [Fixture result](../../os/manifest/ci/11/fixture-1/native-fixture.json)
records both valid GPT copies, four correct partition types/boundaries/GUIDs,
two identical 49,801-byte EFI marker files, and the exact original Windows
entry targeting the protected ESP. It explicitly records `vm_started: false`.
The corrected `losetup --list --json` query ran successfully; it is no longer
an unchecked device-role assumption. Each actual run generates fresh GUIDs.

All completed jobs total **39 rounded minutes** before the final checks-only
preflight. Reserving that job's 15 minutes and the full job's entire 110-minute
timeout gives **164/450**, so the cap cannot be reached by this dispatch. The
full attempt is allowance **2/2**, even though attempt 1 never reached VM boot.
There will be no third full automation attempt.

- The full script first boots the Windows marker, then probes the actual live
  graphical installer with QMP keys/screenshots, shutting down and auditing
  before installing. This bounded probe is not permission to click Erase from
  an unexamined destination/review page.
- If the UI probe cannot be qualified, the fallback invokes this ISO's own
  Anaconda via the launcher's documented `LIVECMD` hook, preserves its original
  interactive defaults/post-scripts, supplies whole-drive Btrfs selection,
  explicit only-use/clearpart/boot-drive target, German keyboard, Berlin time
  and the existing recovery-account rules. `anaconda --help`, `ksvalidator`,
  actual serial/device mapping and the embedded digest are checked before the
  installer writes. A failure is reported; no legacy ISO or different payload
  is substituted.
- This fallback bypasses the unsupported ordinary `liveinst --kickstart`
  argument, replaces the click/review/account pages with kickstart, adds serial
  console boot arguments and automatically reboots. It cannot qualify those
  UI pages or novice followability. Physical-media, keyboard and laptop gates
  remain open even if the automated path passes.
- Installed `/boot/efi` must be vfat on the serial-identified target. The actual
  Linux NVRAM entry's GPT ESP GUID/start/size must match the new target ESP;
  offline target EFI inventory is retained in addition to the protected audit.
- The keyboard adapter uses German console keys, including Shift+7 for `/`,
  the physical slash key for `-`, and swapped Y/Z. It checks the installed
  keymap and retains `dumpkeys` before the real tty3 recovery login; it never
  silently changes the installed system back to US.
- A QEMU held after guest shutdown may emit a second host-QMP-quit event when
  the observer closes it. The observer requires exactly one prior orderly
  guest reset/poweroff, takes final write counters while stopped, retains the
  complete raw event stream, and separately checks the later explicit host
  quit. Only the verified pre-quit snapshot is used for the stock first-boot
  initialization-reset predicate. Duplicate guest shutdowns/panics remain
  failures; the original predicate and its regressions remain unchanged.
- GRUB entries are learned from the installed target's actual BLS files and
  resolved OSTree symlinks. The menu is attempted with QMP; no position is
  selected unless the recorded entries are visible. Only an undrivable menu
  permits the brief's `grub2-reboot` fallback, with the actual recorded BLS ID.
  Stock must be booted at index 1 while AresOS remains first before promotion;
  another unattended stock boot and protected-disk audit are mandatory.

## Final observed outcome: no third full run

[Full attempt 2](https://github.com/carlsenares/AresOS/actions/runs/39869390172)
passed 95 native regressions and disk preparation. The original Windows-like
entry actually booted; live serial mapping was protected `vda`, target `vdb`.
All four offline protected snapshots match, and Windows's entry/order did not
change. The raw firmware/probe final write counters are zero.

Two assumptions above were wrong or insufficient. The captured inventory has
Pykickstart modules but **no `ksvalidator` executable**; I did not check that
before dispatch. The CLI preparation returned 127 before the automatic
installation command started. The actual `anaconda --help` explicitly calls
kickstart unsupported for live installation; merely finding the option and
the launcher's LIVECMD hook did not establish a qualified fallback. The UI
screenshots show Portal while backend Anaconda processes exist, so process
presence did not prove an installer page. No destination/review/EFI screen,
installation, switch, rollback, undo, reverse order or GRUB recovery was reached.

The post-run regression fix now rejects the actual unsupported-live help before
installation preparation, uses the present Python parser rather than assuming
the absent CLI utility for a future supported ISO, and rejects ambiguous BLS
identities without consuming the following line. These are regression-only
changes; no third VM/full run or live installation validation followed. The
full run's tested source remains `f32f1da`. See the report for exact evidence,
the limited counter coverage on the final failed-preflight VM, and budget.


## 11c assumptions and qualification boundary

- Firmware ownership uses bounded EFI load-option parsing: OptionalData must
  equal exactly the 16 GUID bytes. Labels never establish ownership or device
  attachment. Windows Boot0000 has no OptionalData and remains byte-identical.
- `install-tools.sh` obtains patched edk2 source for the exact installed OVMF
  version from the same authenticated Ubuntu snapshot indexes. The runner must
  verify both the GUID definition and exact-size predicate before any VM.
  `firmware-contract.json` records source/binary hashes and version; the actual
  baseline options are separately recorded and checked against that contract.
- Every boot has QMP PCI/block inventories and explicit storage addresses.
  Reverse-order protected storage stays at PCI 3.0 when the target at 2.0 is
  detached. VGA/USB occupy fixed slots 4/5, so detaching storage cannot make
  another peripheral reuse its hardware identity. ISO uses ICH9 SATA port 0.
- Every NVRAM diff names the preceding audited stage and lists each permitted
  firmware addition/removal with its exact device and reason. Existing options
  may never change; automatic options may not disappear while attached. Other
  BootOrder entries retain relative order. Unsupported hardware paths stop.
- The unchanged original signed release keeps its historical repository/source
  identities. `verify_release.py` fetches only rewritten main, pins its runtime
  Git objects, and requires unchanged runtime paths. An ephemeral job-token
  manifest read must succeed before downloading the live ISO; an access failure
  requires a blocker, never a token/visibility/image workaround.
- Fresh probe and full must use the same commit. The probe covers both serial
  mappings, actual UI/review/backend/completion selectors, detached Windows
  boots and disposable-target reset without installing. Part A then repeats
  the entire install/switch/policy/tty3/rollback/Windows-default undo sequence
  in both orders. Part B starts only after both Part A result records exist.
- Only full-run evidence can qualify those installed stages. The 11b stores
  passing narrow regression tests do not establish fresh VM qualification.


## 11d credential transport

The owner-provided Actions secret is available only to explicit dispatch
probe/full initialization. A root-owned 0700 directory and 0600 file under
RUNNER_TEMP hold package-scoped credentials for the original pinned image.
The existing org job token remains separate and handles Actions metadata only.
No owner-token API request or package-visibility change is allowed.

Host preflight requires the exact manifest digest, then pulls all layers with
preserved digests into a disposable OCI layout and removes that layout to leave
room for the installer. Both steps use the same temporary auth file. Failure
has no credential fallback and exports a fixed reason, not client diagnostics.
The original signature/identity and runtime-equivalence checks remain intact.

The guest receives a read-only virtio-9p export at fixed PCI 6.0. Its root and
file must be owned by UID 0; a runner-owned export could collide with daily
UID 1001, so the first setup probe was cancelled before credential creation and
a negative ownership regression was added. The guest mounts with cache=none,
checks read-only mode/ownership/0600, and links /etc/ostree/auth.json to that
mounted file. No credential bytes are sent as shell arguments or saved to a
Linux target file. Console output from registry clients is private; safe proof
records contain only fixed image/identity fields.

The real live ISO must prove the 9p module, mount and unchanged cosign script in
the fresh probe. No full run is authorized by host-only reads. The guard also
requires the probe's successful always-cleanup receipt. Raw artifacts are
scanned for credential patterns and encoded credentials before capture.


The complete pinned-ISO inventory retained in the probe-2 ZIP includes
`usr/lib/modules/7.2.9-201.fc44.x86_64/kernel/fs/9p/9p.ko.xz` and
`usr/lib/modules/7.2.9-201.fc44.x86_64/kernel/net/9p/9pnet_virtio.ko.xz`.
Presence alone is not runtime proof; the fresh probe must load/mount them.
The pinned installer defaults deploy the preloaded `containers-storage` stock
image through `ostreecontainer`; they do not copy the modified live root.
The CI auth symlink therefore is not part of the installed-image payload.

Probe 3 (`40038465601`, source `3187941`) loaded and mounted the read-only,
root-owned 9p share in both drive orders and passed the unchanged release
signature script in each live guest. The subsequent reverse-order detached
Windows firmware audit failed 11c's contract: Boot0004 disappeared while the
protected PCI 3.0 device remained attached, and Boot0002 changed from the DVD
to that protected device. This is a mandatory stop, not a new exemption.
No full run or installed-target credential handling is qualified.

## 11e device-set rule

Brief 11e explicitly replaces the entry-identity exception with a per-boot
attached-device set. Every exact-GUID automatic option is resolved against that
boot's actual PCI/SATA inventory, including unchanged options. The saved OVMF
baselines also contain HTTP options with MAC/IP/empty-URI nodes for the known
PCI 1.0 NIC; the hardware parser now recognizes that recorded path rather than
leaving its ownership device unknown. Other path forms still stop.

Raw option/BootOrder changes remain complete. Per-device events pair unchanged
option numbers first, then remaining numbers for that same device, recording
removal/addition/relabel/renumber. Before/after inventories and complete orders
retain positional changes. Number takeover from any non-auto entry is rejected.
Existing non-auto entries keep their relative order; target-ESP Linux recreation
retains its logical position. Linux changes require its actual partition number,
GUID, boundaries and Fedora shim/GRUB path. Windows must stay first except during
the live installer stage before the guide's Windows-default step.

The real 11d reverse stores replay as exactly three events; the 11b/11c and 11d
first-order stores replay as exactly two. Historical raw evidence is unchanged.
This is regression evidence only: no full run is permitted before a new complete
same-commit probe. The 11d auth path, ownership, private diagnostics, cleanup,
original release checks and shared 11c allowance are unchanged.

The initial 11e setup probe was cancelled before credential creation when review
found Linux recreation was classified by whether an option number existed,
rather than whether it previously held Linux. A target-ESP Linux entry may be
re-created at a former automatic number; the regression now covers that case
while preserving its relative position and rejecting takeover of fixed entries.
The corrected commit requires a new complete probe before any full dispatch.

Probe 2 (`40044393400`, source `a353042`) completed both orders, six unchanged
protected captures/final zero-write records and exactly five device events.
The same-source full `40046420672` completed the first real installation on
the target ESP and booted the detached Windows marker. The install checkpoint
took 25m08s after the baseline checkpoint, including live UI/shutdown/audit.
No complete two-order/B timing has been qualified.

The full audit then rejected the required Windows-first action: non-auto order
changed from Bazzite/Windows/UiApp/Shell to Windows/Bazzite/UiApp/Shell. Windows
and Linux entry payloads and protected bytes remained identical; all three full
final counters were zero. This conflicts with 11e's strict relative-order rule.
The run stopped; no checkpoint was moved, rule widened or additional VM run
attempted. The integrator must settle that boundary before new qualification.

## 11f amended Linux position and full-length plan

The integrator explicitly permits validated target Linux position changes,
including installer-first → Windows-first. Fixed order now excludes those Linux
entries as well as firmware-owned options; every movement records old/new index
and complete orders. Windows payload/number/default and target ESP/loader checks
stay strict. restore_windows_order is independently read back as an exact stable
move of Windows to the front, with no other boot-variable mutation.

The zero-cost stage walkthrough and measured time estimate are in the 11f REPORT
section, written before any new dispatch. Full VM/job limits 156/180 minutes
cover both complete orders plus B with approximately 30% margin; probe limits
are unchanged. The ledger starts at the same 11c timestamp with 146 minutes and
one full already spent. New cap 600, still three full total. Org billing
248/2,000 used is integrator-reported, not verified via token API.

Real 11e install→detached-Windows raw stores replay under 11f as exactly the DVD
and target auto removals plus Boot000A index 0→1. Historical 11b/11d set events
remain unchanged. These static replays do not qualify new A/B boots.

### Fresh 11f probe / full-run assumption gate (before full dispatch)

Probe `40052069600`, source `1b00581df4b9871c9880db67e3f54ed2b82fb487`,
passed both orders. Six offline protected captures match their run's baseline,
six final counters are zero; five expected device-set events, no incomplete
records. Both reviews and detached marker screenshots were visually inspected:
first target vdb / reverse target vda, new 629 MB target EFI, no protected rows;
Windows marker BootCurrent=0000 resolves the same protected ESP at PCI 2 / 3.
146 native tests passed in 2.813s. Both live guests passed the original release
signature verifier. Cleanup removed the runner-temporary owner auth file.
Full authorization must recheck the server artifact digest and all proof flags.
Local HEAD and remote branch are both the exact probe SHA.

New probe timing: tools 6.77 min, ISO 5.82, VM 9.12; job 25.17 (26 rounded).
Slower tools still fit within the full job's 24 minutes beyond the 156-minute VM
limit. No runtime harness changed after this probe. Local post-run verification
was improved to require complete A/B stages and exact Windows-order receipts.
An overbroad password-hash scanner matched accidental binary `$6$` bytes in one
PNG. It now requires ASCII crypt encoding; synthetic SHA512/rounds/yescrypt and
raw/decoded token fixtures still reject, the unchanged PNG passes. All binary
entries remain scanned and original archives remain byte-identical; no token or
actual hash was found. This collector-only correction changes no VM policy.


## 11f full result / stop assumptions

Full 40054116223 on the exact probe source completed first installation, the
Linux 0→1 move/Windows restore, detached Windows and the recognized initial
stock hardware reboot. The target auto option returned at free Boot0002.
No uncovered NVRAM behaviour appeared. Stock booted the frozen ed93 base, but
already had newer upstream d0e5 stock staged. The unchanged pin-stock no-staged
guard stopped before pin, installed signature or AresOS switch. uupd service
startup is recorded; attribution of staging to it is an inference without an
updater journal. No pending update was cleared and no updater disabled.

The failed stock command caused host-signal QEMU close. Its offline bytes/NVRAM
match, but no final stock counter exists. Strict collector exits 1; only ten
final zero-write records across eleven matching captures are established.
Complete A/B timing and later stages remain unqualified. No further dispatch
follows this stop. Integrator decision is required for pending stock handling
and failure-close counter proof; all original frozen pins/guards remain.

## 11g first-stock preparation assumptions — before dispatch

The complete zero-cost sequence and time estimate are in REPORT's 11g section.
Prepare stock before the first §5 Windows reboot; repeat at switch and B. Existing
hardware-initialization reboot remains separately audited; a newer **booted** stock
is a defined refusal, never grounds to auto-rollback. The live probe cannot emulate
an installed OSTree deployment: it verifies real tools/help and updater-unit pause
idempotency; mocked real 11f status covers pending cleanup and refusal states. The
full run must establish actual installed behavior and record whether anything was
staged/discarded. Pause timer changes should not conflict with frozen AresOS updater
masks; any observed conflict is a PLAN-GAP, not permission to alter the image.
QMP failure counters are marked separately; probe-only exercise is never treated
as the session's final counter. Unavailable failure stats leave that session
unqualified. No historical evidence is relabeled. Shared guard is 750m/4 full,
same 11c start. Owner-token scope, offline disk audit, firmware rules and release
pins are unchanged. No required foreseeable NVRAM transition conflicts with rules.

### 11g replacement tool-context assumption — before probe 3

Probe 2 proves rpm-ostree is absent from the live root, despite retained unit files.
Do not install it or infer missing tools from a PATH guess. The exact stock image is
already in the ISO's containers-storage cache: inspect its recorded digest and image
ID, run CLI help there read-only/offline/no-pull/no owner-auth mount, then exercise
unit pause twice on live systemd. Real installed pending cleanup is still a full gate;
its state logic is covered by the real 11f-status replay. No NVRAM/installer stage or
rule changes. Source `stock_probe.py` and its real-cache regressions describe this
new command before dispatch. No full dispatch after either nonpassing probe.

### 11g successful probe → full gate, before dispatch

Probe 40064206779 on source 909fe5a1d54345af550588ea926800930102c168 passed.
Both actual cache IDs/digests match; CLI help runs read-only, offline, no-pull with
no owner credentials mounted. Real system/global-user pause twice passed in each
order. Failure-counter probe receipts for boots 2 and 5 are recorded, paused and
probe-only; final live-session counters are separate. Six offline captures match,
six final counters are zero, no incomplete stage, five firmware events and no Linux
position event. Detached Windows marker and exact Windows-first action pass in both
orders. Both final reviews were visually inspected: first target vdb, reverse vda,
only that target's new EFI/boot/root rows. Signature/auth/pull/always-cleanup passed;
owner-token API calls remain zero. 162 Ubuntu regressions passed. No source push
between this probe and full; local/remote still 909fe5a. The full guard must verify
this original server artifact digest and commit again. The two first-login/pin
paths, actual cleanup occurrence, later frozen policy and all recovery/default
checks remain full-run gates, with unchanged STOP conditions.

### 11g full result — mandatory stop

Full 40066161000 on the exact same source 909fe5a as probe 40064206779 failed
`read_keyboard`: `Conversion did not restore live settings`. Both passing probe
orders executed this same check. Therefore the mandatory probe-covered full-failure
stop rule applies; no fourth full and no further probe. The failure was before the
review/erase/install action, so actual installed stock pause/cleanup/pin, later
policy, reverse full install and B were not reached. The full's two protected
captures match; its failure final counter is recorded, failure-path, non-probe-only,
paused, zero writes, followed by QMP quit and offline audit. No protected/firmware
rule failed. LocaledWrapper before/after values were not printed, so root cause is
unverified; the libbd_mpath warning also occurs in both passing probe orders.
Do not weaken the keyboard restoration assertion or guess a retry. An integrator
follow-up is needed to investigate and authorize further qualification. Current
shared usage 316/750 rounded minutes, 3/4 full, with 14 reserved for closing privacy.
Historical 11f's missing counter remains unchanged/unqualified. Physical gates stay
open and PR stays draft.


### 11h exact-source finding — stop before proof changes

Inspection 40099746381 on 6b08aa3 verified the complete frozen ISO and extracted
LocaledWrapper/resolver/task source. Conversion saves layouts and keymap, omits
options, and restores with empty options. Executing those exact AST nodes with an
immediate mock localed permanently loses nonempty options despite German resolution;
empty options pass. No timing race is necessary for that counterexample. Full 3's
actual cause remains unproven because no tuples were retained. 11h explicitly says
to stop if source shows another issue, so no settle/installed-target/guard change,
probe or full followed. Installed console/X11 paths are known but unverified.
Current ledger 336/750 plus 14 closing reserve, three of five authorized full runs;
old guard remains conservatively four until authorized continuation. Existing stock
pause/cleanup/pin and all A/B gates remain unqualified. Source assertions, frozen
inputs, firmware/offline checks and token/privacy boundaries are unchanged. PR draft.
