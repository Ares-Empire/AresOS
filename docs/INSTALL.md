# Install AresOS on its own SSD

**Draft checked 2026-10-22 — physical installation is NOT RELEASED.** For the Lenovo LOQ 15IRH8 (82XV), German Windows 11 Home and the ordered Crucial P310 500 GB (`CT500P310SSD801`). Read now; do not open the laptop, write installation media or install from this guide until the [release gate](#maintainer-release-gate) is complete. Agents do none of those actions.

After release: **back up → prepare two USBs → fit Crucial → install Bazzite → switch to AresOS → check Windows**. Keep this guide and the private record on another device. Read undo first.

| Drive | Identification | Allowed action |
|---|---|---|
| **New AresOS drive** | Crucial / `CT500P310SSD8…`, 500 GB ≈ **465 GiB**, initially empty; serial must match its label | Install using the whole drive |
| **Windows — KEEP** | Micron `MTFDKCD512TFK…`, 512 GB ≈ **477 GiB**, with Windows/EFI/recovery partitions | Never select for installation |

These are [owner-reported/ordered parts](../briefs/10-own-ssd-install.md), not measurements. GiB figures are decimal capacity ÷ 2³⁰; some screens show 500/512 **GB** instead. **Size or “Disk 0” alone is not identification.** Lenovo specifies one 2242 and one 2280 slot; Windows seeing one disk does not prove the other slot is empty. [L2]

No C: shrink or extension; no installer/rebase/undo writes to Micron or its boot files. Ordinary Windows use and saving records still write ordinary files. The [same-drive fallback](INSTALL-SAME-DRIVE.md) is archived and requires a separate owner decision, not something to try after a failed check.

## 1. Back up and keep a Windows recovery USB

1. Finish pending Windows updates/restarts. Back up school files, photos, recovery information and game saves independently of both internal SSDs. Open several backed-up files; disconnect the backup during installation.
2. Label **two separate sticks**: **WINDOWS RECOVERY — KEEP** and **ARESOS INSTALLER — ERASE OK**. The ordered pair is 2 × 64 GB; the recovery wizard's actual capacity requirement wins. Recovery media excludes personal-file backups. [W1] Bazzite requires at least 16 GB. [B1]
3. Search **Wiederherstellungslaufwerk** (or run `recoverydrive.exe`); approve its administrator prompt. Select **Systemdateien auf das Wiederherstellungslaufwerk sichern → Weiter**. Connect only the recovery stick, check its identity, then **Weiter → Erstellen** erases it. Finish and safely eject. [W1]
4. Search `msinfo32`: require **BIOS-Modus: UEFI**, **Sicherer Startzustand: Aus**, as previously reported. Keep Secure Boot off. Open **Start → right-click → Terminal (Administrator) → Windows PowerShell**:

   ```powershell
   manage-bde -status C:
   ```

   Require **Vollständig entschlüsselt**, **0,0%** encrypted and protection off. Protection off alone may mean suspended encryption. Encrypted, changing or unclear status means stop; independently save the matching recovery key for an owner-reviewed plan before hardware/firmware changes. Do not improvise decryption. [W2]
5. Save work, then run:

   ```powershell
   powercfg /hibernate off
   powercfg /a
   ```

   The first normally prints nothing. The second must show **Ruhezustand / Schnellstart** unavailable because hibernation is disabled. An absent checkbox is expected; no GUI hunt is required. Stop on errors/unclear output, otherwise restart. Leave these off while dual booting; never open Windows volumes in Linux. [W3]
6. Boot the recovery stick with **F12** repeatedly when the power light comes on; select its UEFI USB entry. Reach the keyboard/language or **Option auswählen** screen, then **PC ausschalten**. Do not reset/recover/reinstall. Unplug and preserve it. Failure to boot stops the guide. [L3], [W1]
7. Boot **F12 → Windows Boot Manager**, USBs removed. Save the mandatory [Windows baseline, record A](INSTALL-RECORD.md#a-save-the-windows-baseline), including all partitions and the actual Windows EFI boot target. Copy it off-device.

## 2. Prepare the installer stick

The released handoff must name one **official current Bazzite live ISO**, its SHA-256 and a rehearsed Fedora Media Writer version. Target: **`bazzite-nvidia-open`, KDE, no Steam Gaming Mode**, for RTX 4060. [B2] Do not substitute a legacy ISO or raw VM disk.

1. Download that exact ISO from the official handoff link. Compare its entire hash with the official checksum; a mismatch stops the guide. [W4]

   ```powershell
   Get-FileHash -Algorithm SHA256 -LiteralPath (Read-Host 'Full path to the downloaded ISO')
   ```

2. Unplug recovery/backup devices. Connect only **ARESOS INSTALLER — ERASE OK**. In Fedora Media Writer: **Select .iso file → Next → Select…**; choose the checked ISO. Under **USB Drive**, match the labelled stick before **Write**. Wait for write/verification to finish, then eject. Cancel Windows format prompts. Use this same ISO-file route for undo media; no ZIP or batch files. [F1]
3. Test via **F12 → UEFI USB**: expect Bazzite's boot menu, then live desktop. Do not install. Shut down through the desktop, unplug USB and return to Windows. Both sticks must pass their boot test before opening the laptop. [B1], [L3]

## 3. Fit the SSD and check both drives

Keep Lenovo's **LOQ Series HMM, March 2023**, open: it explicitly covers **15IRH8 / 82XV**. [Cover/battery: printed pp. 30–32, PDF pp. 36–38](https://download.lenovo.com/consumer/mobiles_pub/lenovo_loq_hmm.pdf#page=36); [2280 SSD: printed pp. 34–35, PDF pp. 40–41](https://download.lenovo.com/consumer/mobiles_pub/lenovo_loq_hmm.pdf#page=40). [L1]

Prepare a fitting Phillips screwdriver, plastic opening tool and screw-position organiser. Photograph the Crucial label/serial privately. If the drawings or connectors are beyond your experience, have a qualified repairer fit it.

**Battery stop rule — fitting and removal:** before opening, look for external bulging (raised case, keyboard or touchpad). Immediately after lifting the lower cover, look for swelling, cracks, dents or leakage; also stop for unusual heat or smell. Do not touch the battery to test it. Any damage, warning sign or doubt means **stop before connector/SSD work**: do not press, handle or try to remove the battery; keep AC disconnected, do not reconnect a disconnected battery or charge/power on, and contact Lenovo or a qualified repairer. [L1], [L4]

1. Save/close work; fully shut down with `shutdown /s /t 0`. Wait for power/fans to stop; unplug AC and peripherals. [W5]
2. **Check for external bulging before opening; apply the battery stop rule above.** Use a flat surface and a properly grounded ESD wrist strap, or periodically touch an unpainted grounded metal surface as Lenovo's [self-repair precautions](https://pcsupport.lenovo.com/lt/en/products/laptops-and-netbooks/gaming-series/loq-15irh8/82xv/selfrepair/removalsreplacements) prescribe (checked 2026-10-22). Handle the SSD by its edges. Upside down, remove the rear **deco cover** first: four **M2 × L8** screws, then slide in Figure 3's direction. [L1]
3. Lower cover: remove **nine** screws, five **M2 × L8** and four **M2 × L4**, in Figure 4's positions. Release clips in Figure 5's order (rear, sides, front), then lift. **Inspect the battery immediately; apply the same stop rule before touching any connector.** Keep lengths separated. [L1]
4. **Disconnect the battery cable before SSD work**, using a fingernail on the connector in the illustrated direction, never pulling wires. Lenovo's SSD procedure disconnects the cable, without removing the battery pack or prescribing BIOS battery-disable. [L1]
5. Find the **2280 position in [Figure 9's close-ups](https://download.lenovo.com/consumer/mobiles_pub/lenovo_loq_hmm.pdf#page=41)**, beside the left fan, above the Wi-Fi card in the pictured orientation. Leave Micron 2242 alone. Confirm the 2280 standoff and **M2 × L3** screw are present. Reverse Lenovo's removal: align the keyed connector and insert at about **20–30°**, without force. **Before the screw:** fully engage the connector, check that the gold contacts are barely visible and the far-end fixing notch aligns with the standoff, then lower gently onto it. Only then secure gently, without overtightening. **Never use the screw to pull the drive into place.** Lenovo supplies the location/fixing sequence; the SSD-maker guidance supplies angled insertion and gentle securing. [L1], [S1]
6. Check seating/loose parts, reconnect battery, refit lower cover and rear trim in reverse order; return every screw to its original hole. [L1]

| Before tightening | What it looks like / action |
|---|---|
| **PASS — fully seated** | Connector evenly engaged, gold contacts barely visible; notch centres over the 2280 standoff and the lowered board rests flat on it without bending. |
| **FAIL — partly inserted / wrong support** | A broad or uneven strip of contacts remains exposed, notch misses the standoff, or the board must be pushed/bent to reach it. Stop; do not tighten. Have the fit checked if uncertain. |

**Stop without powering on** for an occupied slot, missing screw/standoff, damaged clip/connector, unexpected resistance, bending board or a cover that will not sit flush. Do not borrow cover screws or disturb Micron. The HMM specifies no separate SSD shield/pad or thickness: preserve existing thermal/insulating pieces, and obtain Lenovo's unit-specific arrangement/parts if any are missing, displaced or unclear. Do not guess pad thickness, add a tall heatsink or remove the CPU/GPU cooler. These are project stop rules, not proof this unit has no pad.

7. Once closed, reconnect AC; start **F2 → More Settings**. [L3] In firmware storage/device information require **both Micron and Crucial**. Match model/serial where shown. An empty SSD need not have a boot entry, so the Boot list is insufficient. The exact storage-information screen remains a release-gate screenshot requirement; if both drives cannot be identified, stop. Exit without other settings changes. Boot Windows, cancel **Datenträger initialisieren / formatieren** for Crucial, and [compare Windows to baseline](INSTALL-RECORD.md#b-compare-windows-after-each-stage).

## 4. Install Bazzite on Crucial only

Use AC, lid open, backups/recovery stick disconnected. F12-boot the installer in UEFI mode; never click a Windows volume in the live desktop.

1. **Set the live desktop's German keyboard before opening Konsole:** open **System Settings**, search **Keyboard → Layouts → Configure layouts → Add → German**. Make German the first/active layout, choose **Global** switching if offered, and **Apply**. In a text editor (not a terminal), type `y z / - " $ ä ö ü` using the physical keys; every character must match. Otherwise stop and correct the layout. Repeat this after each live boot. [K1] Then open **Konsole** and collect [record C](INSTALL-RECORD.md#c-identify-both-drives-in-live-linux): fill the live identity/path columns and require PASS for identity, Micron unchanged and Crucial empty. Fill its installer columns/check when reaching steps 3 and 5 below.
2. Start installer: **English (United States)** interface, **German** keyboard (test again), **Europe/Berlin**. This keyboard setting is for the **installed system**; it does not replace the live-desktop check. [B1]
3. **Installation method → Change destination**: use record C's **same-session whole-disk path** to find the exact Crucial entry; copy/photograph its full text in the mapping. Deselect every other drive. **Destination** must show only this entry; choose **Use entire disk**. This erases the selected disk. [B3] A missing/ambiguous device name means stop. Do not choose alongside Windows, reclaim or manual partitioning.
4. Follow the handoff's encryption choice and exact recovery-administrator recipe. **Account/UID recipe NOT RELEASED — stop if absent.** Do not invent an `ares` account. The proposal is a disposable, unencrypted first trial; personal-data encryption needs a separate decision.
5. At **Review and install**, before **Erase data and install**, complete record C's **installer plan** check: require **only Crucial storage rows**, including a **new EFI partition at `/boot/efi`**, boot and system/data storage. [B4] Resolve every path through the same-session mapping, not example `vda` or a remembered `nvme0n1`. Photograph the whole summary privately. **Any Micron write/mount/EFI reuse, shared Windows EFI, missing new EFI or unclear target means FAIL — Quit.** Never dismiss Windows EFI wording as harmless. Every check must be PASS before continuing.
6. After all checks, install. On error, stop; do not retry with wider erase options. Reboot, remove USB and F12-select the new Linux entry. Unexpected enrollment/signature screens stop the trial; Secure Boot stays off. [B1]

The current live installer supports this whole-drive route; **its exact two-drive behaviour is not qualified here**. Release must prove all Linux boot writes, including fallback files, stay on Crucial. If it fails, the maintainer must qualify another route; the owner must not improvise legacy/manual or shared EFI.

## 5. Check installed Bazzite

Finish [record C](INSTALL-RECORD.md#c-identify-both-drives-in-live-linux): save Crucial's new GUIDs and Linux firmware entry; prove `/boot/efi` resolves to Crucial. Then **F12 → Windows Boot Manager**, run [record B](INSTALL-RECORD.md#b-compare-windows-after-each-stage). A mismatch or Windows repair/recovery prompt stops the trial. Keep records independently.

## 6. Switch to AresOS — NOT RELEASED

**[Brief 06: image release](../briefs/06-image-release.md) must supply the immutable digest, trust/private-pull steps, account/UID recipe, tested Bazzite → AresOS commands and previous-deployment rollback.** No executable rebase command is supplied here. Publishing an image alone does not open the other gates.

Retain authenticated recovery administration; keep all boot writes on Crucial and repartition neither disk. Brief 06's legacy-ISO assumption must be reconciled with this current-live-ISO route. Never flash its raw VM disk to an SSD.

## 7. First AresOS check: plain terminal, no Minecraft yet

Expect **labwc with foot terminal** after the released switch. Stay on AC, lid open: battery-critical handling and suspend are unqualified. Using handoff controls, check RTX 4060 (`nvidia-smi`), display/brightness, Wi-Fi after reboot, audible sound, German keyboard and touchpad. Test Super+Ctrl+Escape, authenticated Ctrl+Alt+F3, return to session, safe shutdown and second boot. This is the proposed P1a acceptance list, not released functionality.

Boot Windows directly with USB absent and present (select Windows explicitly), check files/sound/network and repeat record B against the **original** baseline. On failure, return to Windows and report it. Minecraft/app/save/restore and daily battery use are later milestones.

## 8. Choose the OS at startup

**F12 chooses once**: Windows Boot Manager or the recorded Linux entry (possibly still called Fedora/Bazzite). Keep Windows default for the first trial. For persistent order, after §1's encryption check: **F2 → More Settings → Boot → UEFI**, move the identified entry first using displayed controls, **Save and Exit**. Verify a no-key/no-USB restart. Preserve Windows Boot Manager. [L3]

If an update changes the order, use F12 for AresOS, then restore the preferred order as above. Missing entries, unfamiliar screens, changed Secure Boot or Windows recovery prompts mean stop with the record. Do not reset firmware defaults, clear TPM, delete entries or run Windows boot repair commands.

## 9. Undo: return to everyday Windows

**Default: stop using AresOS; leave Crucial installed.** Keep Windows backups/recovery USB. F12-boot Windows directly, USBs absent, and run record B with stage **before-undo**. Require PASS for its **original Micron EFI boot target**: a later Windows repair might have placed boot files on Crucial despite successful login. Restore **Windows Boot Manager** as default (§8), then restart without pressing keys and with no USB connected. Require Windows to start normally; repeat record B as **after-undo**. **Done.** Linux and its data remain on Crucial; no case opening, erasure or partition change is needed.

**Optional extras, only if you want removal or reuse:** first export Linux data and verify independent copies. Complete the direct-Windows/default-boot checks above immediately before proceeding (repeat **before-undo** if returning later).

- **Remove Crucial:** follow §3's full shutdown, AC/ESD/cover/battery precautions, including **external bulging before opening and the immediate battery-damage inspection after lifting the cover**. Any warning sign means stop before connector work, no pressure/handling or power reconnection; contact Lenovo or a qualified repairer. Otherwise remove only the identified Crucial using Lenovo Figure 9; retain its screw safely. Reconnect battery, close up, boot Windows and repeat record B. Removal preserves Crucial's data; store it safely.
- **Keep the SSD but erase AresOS:** write the released **GParted Live amd64 ISO**, verified against its official SHA-256, to **ARESOS INSTALLER — ERASE OK** using §2's writer. F12-boot; choose German keyboard/English interface and test `y z / - " $` in a text editor before **Terminal**. Repeat record C and [record D's live undo check](INSTALL-RECORD.md#d-before-erasing-crucial-from-live-media). In GParted select the matched Crucial, **Device → Create Partition Table → gpt**. Before that dialog's **Apply** (writes immediately), recheck its whole-disk path, require every Crucial partition disposable, neither SSD mounted and no Micron action. [G1] This clears the layout for reuse, **not secure data sanitisation**. Shut down/remove USB, boot Windows and repeat record B. Cancel Windows initialise/format prompts until separately deciding how to reuse Crucial.

Never extend C: or edit Micron for undo. An unused Linux firmware entry can stay until reviewed cleanup. If Windows does not boot independently or any identity check fails, remove/erase nothing.

## Maintainer release gate

**Closed: work still to do, not results of this package.** Before allowing physical installation:

- **Brief 06:** immutable accessible RTX image, verification, current-live-ISO name/hash, account/UID, switch/rollback and recovery controls. Explicitly reconcile its frozen legacy-ISO instruction; qualify legacy only if the current selected-drive automatic route fails safety requirements.
- **Two-disk rehearsal:** file-backed VM with protected Windows-like EFI/MSR/NTFS/recovery disk and empty Linux disk; repeat with reordered, near-equal drives. Capture full destination/review/EFI screens. Compare **whole protected-disk hashes offline**, GUIDs, boundaries and boot files through install, rebase, rollback and undo. Reject every protected-disk write/mount/swap/shared EFI, including fallback files. Allow only separate Linux NVRAM addition/order changes, preserve Windows entry; test Windows with Linux disk absent. No physical passthrough.
- **Media and followability:** pin writer/Bazzite/GParted versions/hashes, rehearse one ISO-file workflow and UEFI boots/record commands on expendable media. Unaided novice must set/test German before Konsole from an initially English session; map Crucial after renumbering; reject unexpected Crucial partitions and Micron EFI writes; start record B after reboot; and complete default undo without opening/erasing. Owner later boot-tests their preserved recovery stick.
- **Helper:** live Windows/UEFI trials for original-ESP boot, disk renumbering, partition changes, unavailable BootCurrent and Windows booting from Crucial (must refuse undo). Confirm German power-state messages. Synthetic tests are insufficient.
- **Fitting/firmware:** have Lenovo/service support qualify the fitting/thermal-parts instructions and supply a model-confirmed seating close-up, the applicable firmware storage-information screen and boot-order controls. In the novice trial, show a damaged-battery photo: the reader must stop before touching connectors/reconnecting power. On expendable hardware, require identification of fully/partly inserted and incorrectly supported SSDs **before touching the screw**. No guessed BIOS battery-disable or pad thickness. After release permits opening, the owner still must confirm actual slot vacancy, parts and both-drive detection in §3 **before installing the OS**.
- **Safety + followability council:** review this draft and [OS-BASE §8 / Appendix C](design/OS-BASE.md#8-install-targets-image-delivery-and-choosing-an-os), with uncertainties/rehearsals visible.

## Dated sources and limits

Checked **2026-10-22**; archived fallback retains its earlier dates. Hardware supplied by the owner is labelled above; stop rules, gates and trial choices are project decisions. Upstream pictures are examples, **not AresOS test screenshots**. [Record API sources](INSTALL-RECORD.md#sources-and-limits).

| ID | Primary source / evidence |
|---|---|
| L1 | [Lenovo LOQ HMM, March 2023](https://download.lenovo.com/consumer/mobiles_pub/lenovo_loq_hmm.pdf): model list p. iii, battery safety inspection/ESD p. 3, removal/reassembly pp. 29–35, Figures 3–6/9. Cached official PDF safety page and Figure 9 inspected again 2026-10-22; web PDF reader unavailable. No unit-specific thermal kit or exact insertion angle established by Lenovo. |
| L2 | [Lenovo PSREF, 2025-01-21](https://psref.lenovo.com/syspool/Sys/PDF/LOQ/LOQ_15IRH8/LOQ_15IRH8_Spec.pdf), p. 3: slots, not occupancy. |
| L3 | Lenovo [F2 setup](https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/task_start_bios_setup.html), [F12/order](https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/select_boot_devices.html); actual storage screen unverified. |
| L4 | Lenovo [conditions requiring immediate action](https://download.lenovo.com/pccbbs/pubs/t490/html_en/en/Conditions_that_require_immediate_action.html), checked 2026-10-22: battery damage/leakage, heat/odor and stop-use/disconnect/contact-support guidance. General safety guidance, not a LOQ disassembly procedure. |
| S1 | Kingston [M.2 installation, July 2021](https://www.kingston.com/en/blog/personal-storage/install-m2-ssd), step 2.7, checked 2026-10-22: 30° insertion without force, avoid overtightening; Lenovo controls LOQ disassembly/support. The visual PASS/FAIL checkpoint is a project release requirement, not a tested fit on this unit. |
| K1 | KDE [Keyboard Layouts](https://docs.kde.org/stable_kf6/en/plasma-desktop/kcontrol/keyboard/layouts.html), checked 2026-10-22: Configure layouts, Add, default ordering and Global switching. Exact released ISO menus and typing still need rehearsal. |
| W1 | [Microsoft recovery drive, German](https://support.microsoft.com/de-de/windows/experience/backup-recovery/recovery-drive). |
| W2 | [Microsoft manage-bde status](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/manage-bde-status). |
| W3 | Microsoft [powercfg](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options), [Fast Startup](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/distinguishing-fast-startup-from-wake-from-hibernation). |
| W4 | [Microsoft Get-FileHash](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/get-filehash). |
| W5 | [Microsoft shutdown](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/shutdown), `/s`, `/t` versus `/hybrid`. |
| B1 | [Bazzite current guide](https://docs.bazzite.gg/General/Installation_Guide/install-guide/): live/automatic, separate drive, USB size; no exact-ISO two-drive write audit. |
| B2 | [Bazzite FAQ](https://docs.bazzite.gg/General/FAQ/): NVIDIA family, KDE desktop. |
| B3 | [Destination screenshot](https://docs.bazzite.gg/img/live-installer-drive.png): Change destination / Use entire disk, visually checked. |
| B4 | [Review screenshot](https://docs.bazzite.gg/img/live-installer-partitions.png): EFI/boot/Btrfs on one example disk, visually checked; sizes not prescribed here. |
| F1 | [Fedora Media Writer](https://github.com/FedoraQt/MediaWriter), [file selection](https://github.com/FedoraQt/MediaWriter/blob/main/src/app/qml/MainPage.qml), [USB selection](https://github.com/FedoraQt/MediaWriter/blob/main/src/app/qml/DrivePage.qml). |
| G1 | [GParted manual](https://gparted.org/display-doc.php?name=help-manual): Create Partition Table applies immediately; [Live manual](https://gparted.org/display-doc.php?name=gparted-live-manual), [downloads](https://gparted.org/download.php). |

[L1]: https://download.lenovo.com/consumer/mobiles_pub/lenovo_loq_hmm.pdf
[L2]: https://psref.lenovo.com/syspool/Sys/PDF/LOQ/LOQ_15IRH8/LOQ_15IRH8_Spec.pdf
[L3]: https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/select_boot_devices.html
[L4]: https://download.lenovo.com/pccbbs/pubs/t490/html_en/en/Conditions_that_require_immediate_action.html
[S1]: https://www.kingston.com/en/blog/personal-storage/install-m2-ssd
[K1]: https://docs.kde.org/stable_kf6/en/plasma-desktop/kcontrol/keyboard/layouts.html
[W1]: https://support.microsoft.com/de-de/windows/experience/backup-recovery/recovery-drive
[W2]: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/manage-bde-status
[W3]: https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options
[W4]: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/get-filehash
[W5]: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/shutdown
[B1]: https://docs.bazzite.gg/General/Installation_Guide/install-guide/
[B2]: https://docs.bazzite.gg/General/FAQ/
[B3]: https://docs.bazzite.gg/img/live-installer-drive.png
[B4]: https://docs.bazzite.gg/img/live-installer-partitions.png
[F1]: https://github.com/FedoraQt/MediaWriter
[G1]: https://gparted.org/display-doc.php?name=help-manual
