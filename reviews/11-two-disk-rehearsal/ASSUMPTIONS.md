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
