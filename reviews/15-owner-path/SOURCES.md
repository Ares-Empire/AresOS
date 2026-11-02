# Source review for package 15

Checked 2026-10-26. New owner labels come from primary sources; no software or USB writer was installed/run and no hardware setting was changed to verify labels. Source strings do not prove physical rendering.

- GitHub's [current personal-access-token deletion instructions](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#deleting-a-personal-access-token): profile picture → Settings → Developer settings → Personal access tokens → Tokens (classic) → Delete. The documentation does not specify an additional confirmation label; the guide says to complete confirmation if shown, without inventing one.
- Lenovo [FnLock](https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/intro_fnlock.html), [F12](https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/select_boot_devices.html) and [F2](https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/task_start_bios_setup.html): Fn+Esc and Esc LED, primary/secondary reversal and Fn-modified alternatives. Linux login/TTY/desktop-return expectations come from the repository's session recipe, not a claim that Lenovo documents Linux gettys. Both FnLock states on this laptop remain untested.
- Fedora Media Writer **5.3.2 tag**: German PO plus QML selection, drive, warning, cancellation, write completion and restore pages. The warning uses capacity; selection screen supplies device identity. Restore is a selected option followed by Weiter; pressing Wiederherstellen starts the restore directly. Untranslated multi-drive/selector captions and fuzzy generic restore heading are not claimed as verified German rendering. The owner connects exactly one stick, producing the translated device-specific heading. A full German Windows/expendable-media trial remains open.

The seven downloaded tag sources were read locally under ignored `.work/15/sources/`. Complete-file SHA-256 receipts (hash first):

| SHA-256 | Tag source |
| --- | --- |
| `39592326b536358a4071232d9d1aa8a3153b7c52422f2fdaf3f17b6dbb9bf4bc` | [CancelDialog.qml](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/app/qml/CancelDialog.qml) |
| `e7cc0442e7f797bc4badd93916f57c92e922c2732c847696c62be8b01303420d` | [DeviceWarningDialog.qml](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/app/qml/DeviceWarningDialog.qml) |
| `ab127591dea03b19012f507756df41add2ffee2eb12c59f87476c2fa5fa6ae65` | [DownloadPage.qml](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/app/qml/DownloadPage.qml) |
| `bc90d800433992b830103131e406e5d623708fc738a01c5ac327c464a403f978` | [DrivePage.qml](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/app/qml/DrivePage.qml) |
| `48a7ebd10cc7401cf6b4c331af1337ca3880beb93a5db970876ac93652975136` | [MainPage.qml](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/app/qml/MainPage.qml) |
| `0a2eebbf1eccd9ac47b18ffe5ebc3921179a598d66908db81161f85878283ce3` | [mediawriter_de.po](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/po/mediawriter_de.po) |
| `563f83cc2eabede8a82afc147072f433b0442790389a5554ee77cf4420cfa0db` | [RestorePage.qml](https://github.com/FedoraQt/MediaWriter/blob/5.3.2/src/app/qml/RestorePage.qml) |

The following catalogue is preserved verbatim from package 14 head `5156f5f` for its **dated source limits**, not as current status. Its main-branch writer references are superseded by the 5.3.2 checks above. Qualification history/results remain in the linked package reports.

## Dated sources and limits

Checked **2026-10-22**; archived fallback retains its earlier dates. Hardware supplied by the owner is labelled above; stop rules, gates and trial choices are project decisions. Upstream pictures are examples, **not AresOS test screenshots**. [Record API sources](../../docs/INSTALL-RECORD.md#sources-and-limits).

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

## 15b battery source review

Checked **2026-10-26** using the actual LOQ 15/16 [Read this first](https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/read_first.html) → [Generic Safety and Compliance Notices](https://download.lenovo.com/pccbbs/pubs/safety_compliance_notices/generic_notices_class_b_en.pdf) chain, rather than the T490 page. Downloaded generic notices: sixteenth edition, August 2026. Read printed pp.3–4 (PDF pp.7–8), immediate action/service; pp.8–9 (PDF pp.12–13), battery/built-in battery; p.11 (PDF p.15), heat/flammables. Also read the [LOQ HMM](https://download.lenovo.com/consumer/mobiles_pub/lenovo_loq_hmm.pdf#page=9) printed p.3/PDF p.9 powered-off/unplugged inspection and cracked/bulging-battery check. The guide supplies safe-access/movement conditions and retains the no-handling/service-clearance rule as conservative project instructions. The archived T490 citation above is superseded for the revised battery action.

Full-file download receipts (hash first); PDFs stay in ignored local scratch:

| SHA-256 | Source |
| --- | --- |
| `5d802f895529f1283e1668f1f804023dc11f591b9a7b2f976f337f5b6f13e61e` | lenovo_loq_hmm.pdf |
| `51c5c8b33733c9b00e7e2d19188151b6f5023c871c763c867da78f2105e67a05` | generic_notices_class_b_en.pdf |
