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
