Reviewed `46c68e4` and both member reports. **Six distinct findings: three BLOCKING, three NON-BLOCKING.** Physical installation remains unreleased. No files changed; no hardware operations or installation trials performed.

1. **BLOCKING — Battery damage has no explicit inspection or stop condition.** [INSTALL §3](/C:/Users/pab/AresOS-10-own-ssd-install/docs/INSTALL.md:61)

   **Scenario and impact:** The opened laptop reveals a swollen or cracked battery, but normal-looking connectors and screws. The owner continues fitting, reconnects power and worsens an existing hazard. Lenovo explicitly requires stopping use for battery damage. [Lenovo safety guidance](https://download.lenovo.com/pccbbs/pubs/t490/html_en/en/Conditions_that_require_immediate_action.html)

   **Fix:** Check for external bulging before opening and visible battery damage immediately after lifting the cover. Damage means stop, avoid pressure or further handling, keep power disconnected and contact Lenovo or a qualified repairer. Apply this to removal too.

   **Check:** Given a damaged-battery photograph with otherwise normal components, a novice stops before connector work or power reconnection.

2. **BLOCKING — The safety-critical mapping from physical SSD to installer destination is insufficiently explained.** [INSTALL-RECORD C](/C:/Users/pab/AresOS-10-own-ssd-install/docs/INSTALL-RECORD.md:63)

   **Scenario and impact:** With near-equal drives and reversed enumeration, the owner must infer partition relationships from long key/value lines, then match installer paths. A mistaken mapping can erase Windows. `--pairs` disables the displayed tree; the command supplies no parent-device column, and the comparison sheet has no current-device-path field. Dependency ordering remains, but is not a novice explanation. [util-linux implementation](https://github.com/util-linux/util-linux/blob/master/lsblk-cmd/lsblk.c)

   **Fix:** Retain complete records; add an annotated disk tree and a same-session **model + serial → whole-disk path → installer destination** mapping. Make detailed comparisons produce clear pass/fail results.

   **Check:** An unaided novice must identify Crucial after renumbering, reject unexpected Crucial partitions and reject a proposed Micron EFI write.

3. **BLOCKING — SSD seating is not verified before the screw is tightened.** [INSTALL §3, step 5](/C:/Users/pab/AresOS-10-own-ssd-install/docs/INSTALL.md:62)

   **Scenario and impact:** A novice inserts the SSD flat or uses its screw to pull a partly engaged board into position, damaging the connector, board or fixing. “Align/seat” and a subsequent seating check do not explain correct engagement. Manufacturer guidance explicitly describes angled insertion without force and warns against overtightening. [M.2 installation guidance](https://www.kingston.com/en/blog/personal-storage/install-m2-ssd)

   **Fix:** Add a model-confirmed close-up and sequence: angled insertion, full engagement, fixing-notch alignment, lowering, then gentle securing. Never use the screw to force alignment.

   **Check:** On expendable hardware, the novice distinguishes fully seated, partly inserted and incorrectly supported examples before touching the screw.

4. **NON-BLOCKING — “Simplest” undo unnecessarily directs the owner back inside the laptop.** [INSTALL §9](/C:/Users/pab/AresOS-10-own-ssd-install/docs/INSTALL.md:108)

   **Scenario and impact:** The owner only wants normal Windows startup, yet chooses removal or erasure because those are the offered outcomes. This adds avoidable physical handling or destructive disk work.

   **Fix:** Offer “Stop using AresOS; leave Crucial installed” first: verify direct Windows boot and its original boot target, restore Windows as default, verify an unattended restart, then stop. Explain that Linux and its data remain.

   **Check:** A novice returns to everyday Windows use without opening the case or changing disk layouts.

   Removal remains a legitimate, explicitly requested option; its existence is not itself a blocker.

5. **NON-BLOCKING — German keyboard setup occurs after the first Linux commands.** [INSTALL §4](/C:/Users/pab/AresOS-10-own-ssd-install/docs/INSTALL.md:73)

   **Scenario and impact:** Reading from a phone, the owner types record C into an English-layout live desktop and mistypes punctuation. The checks fail before documented keyboard setup.

   **Fix:** Configure and test the live desktop’s German layout before Konsole, including `y z / - " $`. Distinguish this from the installer’s target-system keyboard setting.

   **Check:** Complete the commands from a second device with a German physical keyboard and initially English live session.

   The documented error-stop rule prevents this from authorizing installation.

6. **NON-BLOCKING — Record B omits reopening an administrator terminal after reboot.** [INSTALL-RECORD B](/C:/Users/pab/AresOS-10-own-ssd-install/docs/INSTALL-RECORD.md:29)

   **Scenario and impact:** Following the direct link after fitting, the owner opens ordinary PowerShell. Firmware collection fails for insufficient privilege, making a healthy installation appear broken.

   **Fix:** Repeat **right-click Start → Terminal (Administrator) → Windows PowerShell**, and provide an elevation precheck with a corrective message.

   **Check:** Begin directly at B after a fresh Windows boot with no terminal open.

   Collection errors stop the procedure; they do not silently certify an unsafe layout.

**Safety:** Not ready for owner execution. Literal compliance with the draft currently means stopping at its release gate. Fix the three blockers and complete the existing qualification requirements. A separate SSD and an unchecked Micron checkbox do not prevent installer writes by themselves. The required two-disk audit, independent Crucial EFI and original Windows boot-target checks remain necessary; successful Windows login alone does not establish safe undo.

**Followability:** The most consequential mistakes are battery handling, SSD seating and translating drive identity into installer selections. Those steps need visible acceptance checkpoints. The exact firmware storage screen, installer screenshots and unaided walkthrough are already declared release requirements; their absence is not counted again as a new finding.

**Proportionality and minimal safe version:** Remove shrink/free-space calculations, donated-sector arithmetic, manual EFI/Btrfs construction, deletion between Windows partitions and C: extension. The draft already removes these. Simplify repeated transcription into clear comparisons, while retaining the underlying checks.

The minimal safe route is verified independent backups; two labelled, boot-tested USBs; encryption/power checks; a saved Windows baseline; model-specific fitting with the corrected checkpoints; positive same-session Crucial identification; a rehearsed whole-drive installation with its own EFI; a released AresOS switch/rollback recipe; and direct Windows-return verification. Default undo should leave Crucial installed. Maintainer qualification stays outside the owner’s routine steps, but remains a prerequisite.

GAPS-FOUND (6)