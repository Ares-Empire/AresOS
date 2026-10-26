# Owner references

These checkpoints support the numbered checklist. Record your calling step before opening a reference. Each checkpoint below has explicit return links; do not use browser Back. Release permission comes only from the [current gate/status table](INSTALL-STATUS.md#current-gates).

## Help

**STOP:** stop typing privileged commands. Keep an available administrator session open; do not reboot a pending layout trial. Never reset firmware/TPM, delete boot entries/deployments, widen an erase selection or run boot repair to get past a check. Battery warning signs: Lenovo/qualified repairer first, no power reconnection.

Photograph the entire error/result privately **only with secrets off-screen**. Keep step number, command name, time, booted OS/layout and exported diagnostics. Do not photograph passwords, tokens or recovery keys; do not put serials, personal data or photos in Git/issues/PRs. If uncertain what is visible, describe the error without sending a photo. Export existing records only if Linux is responsive and it is safe to do so; no new commands after an unknown STOP. Never interrupt a deployment command or retype it just because text appeared over the prompt. Press Enter once for a covered idle prompt; uncertain completion → help.

Use Windows with **F12** (or **Fn+F12**) → **Windows Boot Manager** when safe; if Windows cannot start, use your phone. Open your existing Claude conversation/app and describe the result. Keep the two sticks, original baseline and recovery password independently accessible. Once the cause is resolved, **Return to step N**, where N is the failed step recorded in your checklist: [step 1](INSTALL.md#1-backups-recovery-and-windows-preparation), [2](INSTALL.md#2-prepare-and-test-the-installer-stick), [3](INSTALL.md#3-fit-and-identify-both-drives), [4](INSTALL.md#4-install-and-prepare-corrected-stock), [5](INSTALL.md#5-prove-windows-and-corrected-stock), [6](INSTALL.md#6-switch-to-aresos), [7](INSTALL.md#7-check-the-first-aresos-session), [8](INSTALL.md#8-everyday-boot-and-recovery), [9](INSTALL.md#9-retire-access-and-return-to-windows). Step 6 always requires the step 5 completion proof, even on return.

## Console

**Ctrl = Strg**, Super = Windows-logo key. Lenovo's [LOQ FnLock documentation](https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/intro_fnlock.html), checked **2026-10-26**, says **Fn+Esc** changes FnLock; its Esc LED shows status. Off uses the top-row primary function, on the secondary; Fn reverses that choice. Use the alternative below if the plain F-key combination gives a hotkey instead. This is source verification; both states still need the laptop trial.

1. **Ctrl+Alt+F3 (Ctrl = Strg)**, alternative **Ctrl+Alt+Fn+F3 (Ctrl = Strg)** → expect a text screen ending **login:**. Enter `ares-recovery`, then its password at **Password:** (nothing echoed). AresOS uses its current layout; stock always the installer German layout.
2. Expect the recovery user's shell prompt. Run `sudo -i`; enter the same password if requested → root prompt ending **#**. Daily `ares` is not administrator. Keep this session open during preparation/layout trials.
3. To leave: `exit` from root → recovery-user prompt, `sudo -k`, then `exit` → wait for **login:**. Return with **Ctrl+Alt+F1 (Ctrl = Strg)** or **Ctrl+Alt+Fn+F1 (Ctrl = Strg)**. If F1 shows the greeter rather than the existing desktop, try **Ctrl+Alt+F2 (Ctrl = Strg)** or **Ctrl+Alt+Fn+F2 (Ctrl = Strg)**. A fresh greeter on stock requires `ares-recovery`; never log in as root. No desktop/prompt or rejected password → [Help](#help).
4. A later trial's second console uses **Ctrl+Alt+F4 (Ctrl = Strg)** or **Ctrl+Alt+Fn+F4 (Ctrl = Strg)**, same **login:/Password:** sequence. Log it out completely before returning to the retained tty3 session.

**Return to step 4** after initial entry: [step 4](INSTALL.md#4-install-and-prepare-corrected-stock). At the later checks, **Return to step 5** ([stock proof](INSTALL.md#5-prove-windows-and-corrected-stock)) or **Return to step 7** ([AresOS check](INSTALL.md#7-check-the-first-aresos-session)), according to your calling step. If called by a later procedure, return directly to its named section: [layout](INSTALL-PROCEDURES.md#later-layout), [recovery menu](INSTALL-PROCEDURES.md#recovery-menu), [rollback](INSTALL-PROCEDURES.md#rollback-from-running-aresos) or [keep-stock](INSTALL-PROCEDURES.md#keep-stock), then [Return to step 8](INSTALL.md#8-everyday-boot-and-recovery) when that procedure finishes. Any STOP → [Help](#help).

## Media checksums

Use [installer-isos.json](../os/manifest/installer-isos.json) and [media-tools.json](../os/manifest/media-tools.json). Only the live nvidia-open ISO is on the initial path; no legacy ISO/raw VM disk substitution.

| File | Download / fresh publisher check | Pinned SHA-256 |
| --- | --- | --- |
| `bazzite-nvidia-open-stable-live-amd64.iso` | [ISO](https://download.bazzite.gg/bazzite-nvidia-open-stable-live-amd64.iso), [checksum](https://download.bazzite.gg/bazzite-nvidia-open-stable-live-amd64.iso-CHECKSUM) | `776b76f3417723440ee1823d79ec02a2c22860df196d219024edb062ad00d8e6` |
| `FedoraMediaWriter-win64-5.3.2.exe` | [EXE](https://github.com/FedoraQt/MediaWriter/releases/download/5.3.2/FedoraMediaWriter-win64-5.3.2.exe), [release API assets[].digest](https://api.github.com/repos/FedoraQt/MediaWriter/releases/tags/5.3.2) | `f53e0c1108f83a99ad0d7a9aee846822093b1afe595c78f13b22ba779d9f4bd4` |

On install day require the filename and **all 64 hash characters** to match both pin and fresh official source. `stable` is mutable. Missing version/source or any difference → [Help](#help) for maintainer requalification; never replace a pin yourself. Hash each complete download before running/writing:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath (Read-Host 'Full path to the downloaded file')
```

**Return to step 2:** [installer preparation](INSTALL.md#2-prepare-and-test-the-installer-stick).

## Writer labels

Verified **2026-10-26** from **5.3.2**, not main: [German translation](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/po/mediawriter_de.po), [MainPage](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/app/qml/MainPage.qml), [DrivePage](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/app/qml/DrivePage.qml), [warning](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/app/qml/DeviceWarningDialog.qml), [cancel dialog](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/app/qml/CancelDialog.qml), [DownloadPage](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/app/qml/DownloadPage.qml), [RestorePage](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/app/qml/RestorePage.qml). `%1` below is the displayed filename/device/capacity. These are source strings, not claimed Windows screenshots.

| English source | German 5.3.2 control/result |
| --- | --- |
| Select .iso file / Next | .iso-Datei auswählen / Weiter |
| Selected file / Select... | Ausgewählte Datei / Auswählen... |
| USB Drive / Write | USB-Laufwerk / Schreiben |
| Erase confirmation / Cancel / Write | Löschbestätigung / Abbrechen / Schreiben |
| %1 Successfully Written / Finish | %1 erfolgreich geschrieben / Fertig |
| Restore <device> | <device> wiederherstellen |
| Restore Drive <device> / Restore | Laufwerk <device> wiederherstellen / Wiederherstellen |
| Your drive was successfully restored! / Finish | Das Laufwerk wurde erfolgreich wiederhergestellt! / Fertig |

After the first **Schreiben**, **Löschbestätigung** says: “Das gesamte Gerät (alles aus %1) wird gelöscht und das ausgewählte Abbild darauf geschrieben. Wollen Sie fortfahren?” (`%1` is capacity). Recheck name/capacity on the preceding screen and this warning: only the labelled disposable installer is allowed. Choose **Abbrechen** on mismatch/doubt; choose the dialog's **Schreiben** only on a match. If already writing, **Abbrechen** opens **Schreibvorgang abbrechen?**; its **Weiter** continues writing and **Schreibvorgang abbrechen** aborts (media will need restoration). During verification the dialog is **Überprüfung abbrechen?**, with **Überprüfung abbrechen** to abort. Never treat cancellation as a successful verified stick. Cancelled/failed write → [Help](#help), no boot/install from it.

Restore erases installer partitions/all saved data. Keep only that stick connected. The main page with one restorable drive shows **<name> wiederherstellen**; with several it uses **Restore a USB drive (%1 available)**, untranslated in this tag. The selector caption **Select a drive to restore** also has no German translation. Stop if multiple candidates are present; unplug others before retrying selection. Select that restore option, then **Weiter**. The selected restore-page heading must name the exact stick. The restore warning includes “Das Live-System und alle gespeicherten Daten werden gelöscht.” and asks about return to factory capacity; **Zurück** cancels before **Wiederherstellen** starts it. Restore has no second erase dialog: pressing **Wiederherstellen** starts restoration. Wait for the exact success sentence above before **Fertig**. On an error, ignore upstream's suggestion to use system tools; [Help](#help), no Format/diskpart fallback.

Writing checkpoint: **Return to step 2** ([write/boot test](INSTALL.md#2-prepare-and-test-the-installer-stick)). Windows round trip: **Return to step 4** ([restore/copy](INSTALL.md#4-install-and-prepare-corrected-stock)). Optional undo-media write: [Return to the removal/erasure procedure](INSTALL-PROCEDURES.md#optional-removal-or-erasure), then Return to step 9.

## Fitting

Keep [Lenovo LOQ HMM March 2023](https://download.lenovo.com/consumer/mobiles_pub/lenovo_loq_hmm.pdf) open: explicitly **15IRH8 / 82XV**. Cover/battery: printed pp.30–32, PDF pp.36–38; 2280 SSD: printed pp.34–35, PDF pp.40–41, Figure 9. [PSREF](https://psref.lenovo.com/syspool/Sys/PDF/LOQ/LOQ_15IRH8/LOQ_15IRH8_Spec.pdf) specifies one 2242 and one 2280 slot, not occupancy. Photograph Crucial's label/serial privately. If beyond your experience, have a qualified repairer fit it.

**Battery stop rule, fitting and removal:** inspect for external bulging/raised case, keyboard or touchpad before opening, and swelling, cracks, dents or leakage immediately after lifting the cover. Unusual heat/smell or doubt also stops work. Do not touch to test. Stop **before connector/SSD work**; do not press, handle/remove a damaged battery, reconnect disconnected battery/AC, charge or power on. Contact Lenovo/qualified repairer. For a running/charging laptop, stop use and safely disconnect external power before the already-open-case rules; see the [LOQ-linked safety sources](#battery-safety-sources). No further use/fitting before service clearance.

1. Save/close work → `shutdown /s /t 0`; wait for fans/power to stop, unplug AC/peripherals. Prepare Phillips driver, plastic opening tool and screw organiser; grounded ESD strap or Lenovo's [grounded-metal precaution](https://pcsupport.lenovo.com/lt/en/products/laptops-and-netbooks/gaming-series/loq-15irh8/82xv/selfrepair/removalsreplacements). Handle SSD edges only.
2. Battery external inspection first. Upside down: rear deco cover's four **M2 × L8** screws, slide as Figure 3. Lower cover: five **M2 × L8**, four **M2 × L4**, retain positions/lengths. Release rear/sides/front clips in Figures 4–5; lift, **inspect battery before any connector**.
3. Disconnect battery **cable**, fingernail on connector in the pictured direction; never pull wires. No battery-pack removal or guessed BIOS battery-disable.
4. Figure 9's 2280 location is beside the left fan above Wi-Fi in the drawing. Confirm vacancy, standoff and **M2 × L3** screw. Leave Micron 2242 untouched. Preserve thermal/insulating pieces; missing/unclear arrangement requires Lenovo's unit-specific parts. No guessed pads/thickness, tall heatsink or cooler removal.
5. Align keyed connector; insert about **20–30°** without force ([SSD-maker guidance](https://www.kingston.com/en/blog/personal-storage/install-m2-ssd)). **Before tightening:** PASS means evenly engaged connector, gold contacts barely visible, fixing notch centred on standoff, lowered board flat without bending. Broad/uneven contacts, missed standoff, resistance or forced bending → FAIL, do not tighten. Never use the screw to draw it into place; secure gently without overtightening. Missing parts/damaged clips/occupied slot → stop without power-on.
6. Check seating/loose parts, reconnect battery only if safe, refit cover/trim in reverse order with original screw positions. A cover that will not sit flush stops power-on.

**Record:** fit/seating/parts and safety results. **STOP → Lenovo/qualified repairer and [Help](#help)**. **Return to step 3** ([firmware/Windows checks](INSTALL.md#3-fit-and-identify-both-drives)) only after every fitting check passes. Removal uses the same safety sequence; [return to its procedure](INSTALL-PROCEDURES.md#optional-removal-or-erasure), then Return to step 9.

## Battery safety sources

Checked **2026-10-26**: the [LOQ 15/16 guide, Read this first](https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/read_first.html) requires Lenovo's [Generic Safety and Compliance Notices](https://download.lenovo.com/pccbbs/pubs/safety_compliance_notices/generic_notices_class_b_en.pdf): printed pp.3–4 (PDF pp.7–8), immediate action/service; pp.8–9 (PDF pp.12–13), battery/built-in battery; p.11 (PDF p.15), heat and flammables. They direct stopping use, unplugging power on signs of danger and obtaining service guidance. The [LOQ HMM](https://download.lenovo.com/consumer/mobiles_pub/lenovo_loq_hmm.pdf#page=9), printed p.3, requires power off/unplugged inspection and checking cracked/bulging batteries. This model manual plus its linked generic notices are the sources used here; the T490 page is not used for the revised action.

Disconnect the external charger or move the laptop only if safe without touching a hot/swollen case. If moving it is unsafe, keep clear and move nearby flammables away only if safe. These safe-access conditions and the no-battery-handling/service-clearance stop are conservative project instructions, not an instruction to move a dangerously hot product. If already open with the battery disconnected, leave it that way; no connector work or reconnection. **STOP → [Help](#help)** after Lenovo/qualified service. **Return to step 3** ([fitting](INSTALL.md#3-fit-and-identify-both-drives)) only with service clearance.

## Dated sources and limits

New label/Fn/token checks are dated **2026-10-26** above and in step 9. Hardware/source reasoning inherited from packages 10–14 retains its original dates in their reports. Source inspection never closes physical/followability gates. [Dated source review and inherited catalogue](../reviews/15-owner-path/SOURCES.md) retains the full source catalogue and earlier limitations. [Record API sources](INSTALL-RECORD.md#sources-and-limits) cover inventory comparisons. [Current status/evidence](INSTALL-STATUS.md#current-gates) links the qualification reports. **Return to step 1** ([start checklist](INSTALL.md#1-backups-recovery-and-windows-preparation)).
