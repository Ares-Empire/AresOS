# Pre-run assumption audits

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
