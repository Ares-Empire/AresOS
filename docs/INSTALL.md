# Install AresOS on its own SSD

**Draft checked 2026-10-24 — physical installation is NOT RELEASED.** For the Lenovo LOQ 15IRH8 (82XV), German Windows 11 Home and the ordered Crucial P310 500 GB (`CT500P310SSD801`). Read now; do not open the laptop, write installation media or install from this guide until the [release gate](#maintainer-release-gate) is complete. Agents do none of those actions.

After release: **back up → prepare two USBs → fit Crucial → install Bazzite → switch to AresOS → check Windows**. Keep this guide and the private record on another device. Read undo first. **Emergency card:** [If something goes wrong](EMERGENCY.md). Put it on your phone before you start.

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

The media pins are in [installer-isos.json](../os/manifest/installer-isos.json) and [media-tools.json](../os/manifest/media-tools.json). Use **Bazzite `bazzite-nvidia-open-stable-live-amd64.iso`**, SHA-256 **`776b76f3417723440ee1823d79ec02a2c22860df196d219024edb062ad00d8e6`**, and **Fedora Media Writer for Windows x64 5.3.2**, SHA-256 **`f53e0c1108f83a99ad0d7a9aee846822093b1afe595c78f13b22ba779d9f4bd4`**. [Official writer download](https://github.com/FedoraQt/MediaWriter/releases/download/5.3.2/FedoraMediaWriter-win64-5.3.2.exe); the publisher's `assets[].digest` in the [release API](https://api.github.com/repos/FedoraQt/MediaWriter/releases/tags/5.3.2) supplies its checksum. The writer download was hash-checked; its physical USB workflow remains **OPEN**. Target: **KDE, no Steam Gaming Mode**, for RTX 4060. [B2] Do not substitute a legacy ISO or raw VM disk.

1. On install day, open the [official live ISO checksum](https://download.bazzite.gg/bazzite-nvidia-open-stable-live-amd64.iso-CHECKSUM). Require its entire hash and filename to equal the pin above, then [download the live ISO](https://download.bazzite.gg/bazzite-nvidia-open-stable-live-amd64.iso). The `stable` URL is mutable; no immutable download reference is qualified. Hash the complete downloaded file using the command below and compare all 64 characters with **both** the pin and the fresh official checksum. Also hash the writer EXE before running it and compare with its pin and publisher digest. Missing files, a new release or any mismatch means **stop for a new maintainer qualification; never update the pin yourself**. [W4]

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

Use AC, lid open, backups/recovery stick disconnected. Stay offline: no live Wi-Fi profile and no network cable until prepare passes. F12-boot the installer in UEFI mode; never click a Windows volume in the live desktop.

1. **Set the live desktop's German keyboard before opening Konsole:** open **System Settings**, search **Keyboard → Layouts → Enable (accessible name “Configure Layouts”) → Add → German → OK**. Make German the first/active layout, choose **Global** switching if offered, and **Apply**. In a text editor (not a terminal), type `y z / - " $ ä ö ü` using the physical keys; every character must match. Otherwise stop and correct the layout. Repeat this after each live boot. [K1] Then open **Konsole** and collect [record C](INSTALL-RECORD.md#c-identify-both-drives-in-live-linux): fill the live identity/path columns and require PASS for identity, Micron unchanged and Crucial empty. Fill its installer columns/check when reaching steps 3 and 5 below.
2. Start the installer with **English (United States)**. On **Welcome → Change system keyboard layout**, add **German**, remove the initial US layout so the selected list contains only **de**, then **Save**. Require **de** in the Welcome keyboard summary before **Next**. This is the installed-system choice; keep the live-desktop physical-key test from step 1. On **Date and time**, turn off **Automatically set timezone**, then choose **Europe → Berlin**. These pages were previewed on the pinned ISO in [11b](../reviews/11-two-disk-rehearsal/REPORT.md); a preview does not release installation. [B1]
3. **Installation method → Change destination**: use record C's **same-session whole-disk path** to find the exact Crucial entry; copy/photograph its full text in the mapping. Deselect every other drive. **Destination** must show only this entry; choose **Use entire disk**. This erases the selected disk. [B3] A missing/ambiguous device name means stop. Do not choose alongside Windows, reclaim or manual partitioning.
4. At **Storage configuration**, leave **Encrypt my data** unchecked for the proposed disposable first trial; personal-data encryption needs a separate decision. At **Create Account**, keep **Use local account** checked; its description promises administrator access. Enter **ares-recovery** as **User name** first, then the full name and a strong unique passphrase twice. Do not create `ares` or enable root. The actual screen was previewed in 11b; **installed UID/group, encryption and two-drive qualification remain OPEN; do not install yet**. The required account checks are in [§6](#accounts-before-switching).
5. At **Review and install**, before **Erase data and install**, complete record C's **installer plan** check: require **only Crucial storage rows**, including a **new EFI partition at `/boot/efi`**, boot and system/data storage. [B4] Resolve every path through the same-session mapping, not example `vda` or a remembered `nvme0n1`. Photograph the whole summary privately. **Any Micron write/mount/EFI reuse, shared Windows EFI, missing new EFI or unclear target means FAIL — Quit.** Never dismiss Windows EFI wording as harmless. Every check must be PASS before continuing.
6. After all checks, install. On error, stop; do not retry with wider erase options. Reboot, remove USB and press nothing: **Linux is the firmware default at this point**. Let stock Bazzite finish its one-time hardware setup, including its possible automatic reboot, then sign in while still offline and follow the tools-stick round trip below. Unexpected enrollment/signature screens stop the trial; Secure Boot stays off. [B1]

The pinned live installer's whole-drive route passed the automated two-disk VM rehearsal in **both drive orders**: Linux EFI/boot/root stayed on the selected target and the protected disk stayed unchanged. See [11k](../reviews/11-two-disk-rehearsal/REPORT.md#11k-bounded-read-only-guard-retry-and-final-qualification-2026-10-24). Physical media, the laptop and unaided followability still need qualification before release. Do not improvise legacy/manual or shared EFI.

### Let the system keyboard setting decide before retaining stock

Keep **all networking off** from the live session until `prepare` passes below:
no Wi-Fi profile and no network cable. Anaconda copies network profiles. The
pinned installer uses its local image cache and works offline; stock hardware
setup uses local files and can reboot once before login. Its installer keymap
value is untrusted (`de` and `us` have both been observed). `prepare` removes
all console keymap overrides from **only the booted deployment**; normal system
settings then decide. It accepts one or two unpinned stock serials with the
qualified checksum, repairs that exact booted identity and pins it. The older
serial stays untouched until switch finalization removes it. Never select or
remove it yourself.

An NVIDIA Flatpak runtime notification while offline is expected. Leave its
sync enabled: it retries after networking comes up and only changes the system
Flatpak installation. `prepare` records its state without waiting. An unfinished
sync is not a deployment STOP. Its real NVIDIA completion is a physical gate.

### Pause and retain stock before the Windows comparison

The tools stick is made from the now-unused **ARESOS INSTALLER — ERASE OK**;
keep WINDOWS RECOVERY untouched. After stock finishes its offline hardware
setup and reaches login, shut down normally **while still offline**. Remove the
installer USB first. In **F2**, put the recorded **Windows Boot Manager first**,
Save and Exit, and press nothing: require Windows to start unattended. Windows
stays the firmware default from here onward; **F12 → the recorded Linux entry**
selects just one Linux start.

In Windows, plug in only the former installer stick. Open the pinned **Fedora
Media Writer 5.3.2**, use **Wiederherstellen (Restore)** for that exact stick,
confirm, wait for completion and choose **Fertig (Finish)**. This destroys the
installer partitions and creates a normal exFAT stick. Source verification is
in the [14 report](../reviews/14-owner-tools/REPORT.md); the German click path
still needs the expendable-media gate. Cancel Windows format prompts; no Disk
Management, diskpart, Format or third-stick fallback. Stop on any difference.

From the reviewed repository copy used for the record helper, open PowerShell
7 in that repository. Substitute the restored stick's actual D–Z drive letter
for T (check its identity in Explorer; never use C:):

```powershell
Import-Module ./docs/install-tools/OwnerTools.psm1 -Force
Copy-AresOwnerTools -Source ./os/owner-tools/payload -DriveLetter T
```

Require `PASS tools manifest SHA256 118212ec60844043856b5531be95cf2319f9943319679fa6149f999db89bf6ba` and `PASS ARESTOOLS ready`.
The copy checks removable/USB/exFAT/boot/system identity before writing,
verifies every copied file, and labels it **ARESTOOLS**. A STOP means preserve
it and get help. Safely eject and **unplug** it before [record B](INSTALL-RECORD.md#b-compare-windows-after-each-stage), shutdown or restart. Record B must pass with
both USBs absent; Windows must boot from its original Micron EFI target.

Use **F12 → the recorded Linux entry**, sign in as **ares-recovery** using the
installer's German layout, then **Ctrl+Alt+F3**, sign in there with the same
password and run `sudo -i`. Keep that administrator console open. **Only now**
plug in ARESTOOLS. Type this first bootstrap command exactly:

```bash
sudo bash -c 'set -e; mount -o ro LABEL=ARESTOOLS /mnt; trap "umount /mnt" EXIT; bash /mnt/ares-tools/at install'
```

At its prompts enter the independently photographed Crucial serial and record
A's Micron serial. Require `PASS install` with that manifest fingerprint. It
checks the label, removable USB, complete manifest and both internal identities
before installing root-only tools in shared `/var/lib/ares`; the frozen AresOS
image does not shadow that path. The read-only bootstrap unmounts even on STOP.
A failed bootstrap means stop and preserve the screen, not another mount path.

```bash
sudo /var/lib/ares/at prepare
```

Require `PASS prepare`, the exact corrected stock checksum/serial/stateroot,
`pin yes; pending none; updaters paused`. This one implementation pauses every
reviewed OS updater, waits for idle, cancels at most one leftover transaction,
discards only a permitted upstream staged update, repairs booted stock, then
pins it. A manual deployment client/transaction or unknown state refuses before
mutation. A five-minute idle failure names the blocker in saved diagnostics;
do not reboot, reconnect or guess a repair. Get help. Rerun that same command:
require `Already prepared; no OS mutations`. Leave updaters paused throughout.

Now enable networking using stock's normal controls. Then type:

```bash
sudo /var/lib/ares/at title
sudo /var/lib/ares/at records
sudo /var/lib/ares/at export
```

Require PASS for each. `title` first proves the **entire deployment list, pin,
pending state and BLS list unchanged since prepare**, and records Flatpak state.
`records` saves post-install record C: disk/partition GUIDs, target EFI mapping
and firmware entries. Compare those values with the private record; Micron
must still match record A. Each command saves full dated diagnostics under
`/var/lib/ares/records`; export finds the unique labelled manifest-matching
stick, mounts it itself, copies only those JSON records with SHA256 readback,
and unmounts. Require **SAFE TO REMOVE ARESTOOLS**, then **unplug it**. Never
remove a mounted/busy stick. No stick is needed across any reboot.

Save the current exact stock title and invalidate every earlier title. Then:

```bash
sudo /var/lib/ares/at reboot
```

Require the guarded reboot; press nothing and require unattended Windows, then
repeat record B with both USBs absent and copy the exported records off-device.
If you need to inspect them in Windows, plug ARESTOOLS in only for that copy,
then eject/unplug before comparisons or restarting. Return via **F12 → Linux**.

**Stick rule at every later boot:** plug it in only after Linux is up and you
are signed in; export/unmount and unplug before every shutdown or restart.
The tool refuses reboot while it is attached. If forgotten at power-on,
**nothing breaks: never pick the stick in F12, unplug it and continue**; Windows
stays first. A data-only stick present at power-on is physically untested, not
an accepted USB firmware-audit rule. Never delete a firmware entry to hide it.

## 5. Check installed Bazzite

After **F12 → Linux**, sign in as **ares-recovery** using the installer layout;
Ctrl+Alt+F3 → fresh password login → `sudo -i`:

```bash
sudo /var/lib/ares/at check
sudo /var/lib/ares/at title
sudo /var/lib/ares/at records
```

Require PASS and override-free loaded German console keys. Prove `yz-/!ü` by
physical typing; the same password must work with password-authenticated sudo.
Check stock's rendered greeter, network and hardware. Compare record C's target
EFI identity and record B's untouched Windows before switching. Every STOP
means keep diagnostics, stop this trial and get help. Windows remains first.

## 6. Switch to AresOS

The frozen private release is
`ghcr.io/ares-empire/aresos@sha256:9b19b7942bc131934eac3733a7f8a1c1de488659075897f60c006bc88c77f3eb`.
It keeps the qualified base and packages; this package builds no image. Signature
identity, issuer and exact digest are checked by the shared release script.

### Accounts, before switching

Use **ares-recovery**, UID1000 in wheel, for administration. The daily `ares`
account (UID1001 without wheel) must not exist on stock; the image creates it.
`login`, `verify` and `switch` recheck those accounts, the complete saved stock
state, paused updaters and disk identities before doing their work. A STOP is
not permission to create/delete an account or use root as the everyday user.

### Retain stock Bazzite and authenticate the private pull

Stock is already corrected/pinned by prepare. Do not pin again or select the
older serial. Full diagnostics and the compact current title are your record.

### Refresh the recorded stock title before reboot

**Every reorder immediately invalidates the old title**, including cleanup,
staging a switch, queuing rollback and making stock default. Both entries may
say Bazzite. Never infer a title from a remembered position or checksum alone.

```bash
sudo /var/lib/ares/at title
```

Require PASS with the saved **checksum, serial, stateroot and pin**, no active
transaction, exact pending state and resolved BLS title. Record all of it with
the time; mark previous titles INVALID. A staged switch title is provisional:
refresh after the first successful AresOS boot, before relying on recovery.
A stale or missing title, failed first switch boot or unexpected list means
**F12 → Windows and help**, never guess a GRUB row. `reboot` checks freshness.

### Authenticate the private pull

From the open tty3 **ares-recovery → sudo -i** session, type:

```bash
sudo /var/lib/ares/at login
sudo /var/lib/ares/at verify
```

Enter the GitHub username at its prompt and the approved **read:packages-only,
unexpired token only at the hidden prompt**. Never type it in a command, paste
it into chat, photograph it or save it in records. It is accepted only for the
exact private release pull, written only to root-owned mode0600
`/etc/ostree/auth.json`; no owner-token GitHub API call or secret fallback.
Require PASS login, then PASS verify for the exact digest/signature. Otherwise
stop and get help; do not make the package public or bypass a signature check.

### Switch, reboot, and check recovery

```bash
sudo /var/lib/ares/at switch
```

Require PASS, the exact staged signed release, retained corrected pin and the
new identity-resolved stock title. Save it as provisional; invalidate the old
one. The shared `switch.sh` retains stock and refuses pending transactions.
With all sticks absent:

```bash
sudo /var/lib/ares/at reboot
```

**F12 → Linux**, then let AresOS start. Windows remains the default. On tty3
sign in as **ares-recovery** with German and run `sudo -i`; then run `check`
and `title` as in §5. Require the final pair (AresOS + corrected pinned stock),
no old serial, exact release, loaded German console map and no overrides in
any retained boot entry. Save the refreshed stock title before any later reboot.
Test physical typing and password sudo; §7 covers the daily foot terminal.

### Change the AresOS layout later; recovery keeps the installer layout

**Backup Bazzite keeps the installer's layout (German here)**. Later changes
apply only to AresOS; no mechanism writes the new layout into stock. A US-then-
rollback run was not performed; source verification of per-deployment `/etc`
is not a runtime result. Qualification returns AresOS to German before rollback.

Keep the original **tty3 ares-recovery → sudo -i** administrator session OPEN.
For the safe successful trial use US International so the unchanged umlaut
password remains typeable (plain US is deliberately the failure/revert trial):

```bash
sudo /var/lib/ares/at layout begin us-intl
```

Require PASS; **do not reboot**. Ctrl+Alt+F4 → fresh **ares-recovery password
login** in US International. Type `sudo -k` to clear authentication, then:

```bash
sudo -k; sudo /var/lib/ares/at layout proof
```

Supply the unchanged password to sudo, then physically type `yz-/!ü` as prompted
(US International ü is AltGr+y). Require PASS. Exit that second login completely,
return Ctrl+Alt+F3 to the original open root session, then:

```bash
sudo /var/lib/ares/at layout finish
```

Require PASS and the refreshed title. If typing or login failed, return to that
original tty3 session immediately instead and run:

```bash
sudo /var/lib/ares/at layout revert
```

Require restored settings; log out tty4 and prove a **fresh** password login,
sudo and `layout proof` with the old layout, then original tty3 `layout finish`.
Never reboot with an unfinished trial. For returning to German the same sequence
starts with `sudo /var/lib/ares/at layout begin de`. Plain US's failure trial
starts with `sudo /var/lib/ares/at layout begin us`: a failed second login must
be reverted from the original session, never by changing the password.
After a completed trial use `title` then `reboot` → **F12 → Linux**; sign in
on tty3 using the new layout, run `check`, prove physical console/password sudo
and foot typing. Return to German with the same second-console proof and reboot
before the rollback trial. The VM does not automate live KDE/KWrite settings.

### Roll back to the retained stock deployment

On booted AresOS: **Ctrl+Alt+F3 → ares-recovery** with the current AresOS layout
→ `sudo -i`, then:

```bash
sudo /var/lib/ares/at rollback
sudo /var/lib/ares/at title
```

Require PASS rollback: exact saved stock checksum/serial/stateroot, origin,
digest and pin, idle before queuing; then PASS title with rollback queued.
Invalidate the old title and save the new one **before reboot**. Booted stock
refuses rollback with a keep-stock direction and makes zero deployment changes.

```bash
sudo /var/lib/ares/at reboot
```

**F12 → Linux**, let stock start. At its rendered greeter sign in as
**ares-recovery using the installer layout**, then tty3 → password login →
`sudo -i` → `check` and `title`. Require the corrected pinned stock booted,
AresOS retained, loaded German and the full refreshed record. Windows stays first.

### Keep recovered stock as the default

If GRUB recovery was needed, select only the fresh identity-resolved stock
title, then **ares-recovery with the installer layout → tty3 → sudo -i**:

```bash
sudo /var/lib/ares/at keep-stock
sudo /var/lib/ares/at title
```

Require PASS, saved corrected stock identity and pin, no pending work, and
stock first. Invalidate/record the title again. Then with all sticks absent:

```bash
sudo /var/lib/ares/at reboot
```

**F12 → Linux**, no GRUB selection: require stock again. Sign in as
**ares-recovery with installer layout → tty3 → sudo -i → check and title**.
Compare Windows record B again afterward. Leave updaters paused until the
owner chooses stock permanently and its second default boot passes.

To leave an administrator console, exit root, run `sudo -k`, then `exit` and
wait for the login prompt before Ctrl+Alt+F1. Keep full diagnostics privately;
plug the tools stick in only after sign-in, use `export`, require SAFE TO REMOVE,
unplug before every restart. A STOP never authorizes a wider write/repair.

## 7. First AresOS check: plain terminal, no Minecraft yet

Expect **labwc with foot terminal** after the released switch and **F12 → the
recorded Linux entry**. Stay on AC, lid open: battery-critical handling and
suspend are unqualified. Using handoff controls, check RTX4060 (`nvidia-smi`),
display/brightness, Wi-Fi after reboot, audible sound, the selected AresOS
keyboard layout and touchpad. For a restart during these checks, press
**Ctrl+Alt+F3 → sign in as `ares-recovery` using the current AresOS layout →
`sudo /var/lib/ares/at reboot` → F12 → the recorded Linux entry**. Let AresOS start;
Windows stays the firmware default. Test Super+Ctrl+Escape, authenticated tty3,
return to session, safe shutdown and a second Linux boot selected with F12.
This is the proposed P1a acceptance list, not released functionality.

**First-hardware-boot logind gate (03c procedure, authorized by brief 03e):** after
the installation and recovery-account prerequisites, on AC with the plain
terminal session, use **Ctrl+Alt+F3 → `ares-recovery`** with the current AresOS
layout. Log out using §6's supplied steps, return to the session, then verify a
short physical power-button press reaches logind and cleanly powers off. Power
on, press **F12 → the recorded Linux entry**, let AresOS start, then use
**Ctrl+Alt+F3 → sign in as `ares-recovery` → `sudo -i`**. Collect the previous
persistent journal in that root shell (PASS means collected; inspect the saved logind and full journal for the actual button/shutdown evidence):

```bash
sudo /var/lib/ares/at logs
```

Retain both outputs, the image digest and pass/fail privately. Require the button
record and orderly shutdown; merely seeing the laptop turn off is insufficient
to establish the logind path. Repeat the fresh boot/session/recovery trial as
`ares-recovery`: run `sudo /var/lib/ares/at reboot` in that root shell, then **F12 → the
recorded Linux entry**, let AresOS start and sign in on tty3 as `ares-recovery`
with its current layout. Keep Windows first in firmware. Missing records or an
unreadable journal leave this hardware gate unmet. CI may label its offline
logind check **REPORTED, NOT BLOCKING: first hardware boot required** only when
the kernel Btrfs mount is explicitly unsupported **and** its userspace reader
tooling is explicitly absent (03f). That path remains a hardware gate; CI still
requires QMP guest shutdown, `poweroff.target` and two fresh VM passes.
Filesystem/extraction/verification errors, absent journals or expected boots,
wrong boots and missing required logind records remain blocking CI failures.

Boot Windows directly with USB absent and present (select Windows explicitly), check files/sound/network and repeat record B against the **original** baseline. On failure, return to Windows and report it. Minecraft/app/save/restore and daily battery use are later milestones.

## 8. Choose the OS at startup

**F12 chooses once**: Windows Boot Manager or the recorded Linux entry (possibly
still called Fedora/Bazzite). After §4's round trip, **Windows Boot Manager stays first** for
every step of this trial. If that order needs restoring, after §1's encryption
check use **F2 → More Settings → Boot → UEFI → Windows Boot Manager first →
Save and Exit**, then verify a no-key/no-USB restart starts Windows. Do not make
Linux first to avoid F12. The initial installer/hardware-setup Linux-default
phase ends before §4's Windows/tools round trip. Preserve Windows Boot Manager. [L3]

If an update changes the order, use F12 for AresOS, then restore Windows Boot Manager first as above. The laptop may drop automatic F12 entries for unplugged devices, such as the installer USB; that is normal. Missing Windows Boot Manager or the Linux entry while its SSD is attached, unfamiliar screens, changed Secure Boot or Windows recovery prompts mean stop with the record. Do not reset firmware defaults, clear TPM, delete entries or run Windows boot repair commands.

## 9. Undo: return to everyday Windows

**Default: stop using AresOS; leave Crucial installed.** Keep Windows backups/recovery USB. F12-boot Windows directly, USBs absent, and run record B with stage **before-undo**. Require PASS for its **original Micron EFI boot target**: a later Windows repair might have placed boot files on Crucial despite successful login. Restore **Windows Boot Manager** as default (§8), then restart without pressing keys and with no USB connected. Require Windows to start normally; repeat record B as **after-undo**. **Done.** Linux and its data remain on Crucial; no case opening, erasure or partition change is needed.

**Optional extras, only if you want removal or reuse:** first export Linux data and verify independent copies. Complete the direct-Windows/default-boot checks above immediately before proceeding (repeat **before-undo** if returning later).

- **Remove Crucial:** follow §3's full shutdown, AC/ESD/cover/battery precautions, including **external bulging before opening and the immediate battery-damage inspection after lifting the cover**. Any warning sign means stop before connector work, no pressure/handling or power reconnection; contact Lenovo or a qualified repairer. Otherwise remove only the identified Crucial using Lenovo Figure 9; retain its screw safely. Reconnect battery, close up, boot Windows and repeat record B. Removal preserves Crucial's data; store it safely.
- **Keep the SSD but erase AresOS:** the pinned undo medium is **GParted Live 1.8.1-6 amd64**, [official ISO download](https://downloads.sourceforge.net/project/gparted/gparted-live-stable/1.8.1-6/gparted-live-1.8.1-6-amd64.iso), SHA-256 **`d789c38779f0d6f7026c12f44c2c52a04f66e28a1aea7d51f3045ad1bbf28411`**. Its [official checksum source](https://gparted.org/gparted-live/stable/CHECKSUMS.TXT) and release directory are recorded in [media-tools.json](../os/manifest/media-tools.json). On install day require the fresh official checksum and the complete downloaded file hash to match this pin; a mismatch or missing version means stop. The ISO/physical-media boot workflow remains **OPEN**. After release, write it to **ARESOS INSTALLER — ERASE OK** using §2's pinned writer and ISO-file workflow. F12-boot; choose German keyboard/English interface and test `y z / - " $` in a text editor before **Terminal**. Repeat record C and [record D's live undo check](INSTALL-RECORD.md#d-before-erasing-crucial-from-live-media). In GParted select the matched Crucial, **Device → Create Partition Table → gpt**. Before that dialog's **Apply** (writes immediately), recheck its whole-disk path, require every Crucial partition disposable, neither SSD mounted and no Micron action. [G1] This clears the layout for reuse, **not secure data sanitisation**. Shut down/remove USB, boot Windows and repeat record B. Cancel Windows initialise/format prompts until separately deciding how to reuse Crucial.

Never extend C: or edit Micron for undo. An unused Linux firmware entry can stay until reviewed cleanup. If Windows does not boot independently or any identity check fails, remove/erase nothing.

## Maintainer release gate

- **OPEN — package 14 physical gates:** Fedora Media Writer 5.3.2 restore German click path, reviewed bundle copy/eject, novice offline round trip, root-only shared tools across stock/AresOS, and tools-stick hotplug/export/unplug. A forgotten data-only stick at power-on is physically untested; it is never an accepted firmware-audit exception.
- **OPEN — NVIDIA deferred runtime (14b):** after first network, confirm the enabled sync finishes for the real GPU and the entire deployment/pin/pending/BLS state stays unchanged. Virtio graphics cannot exercise its NVIDIA condition. Never mask or delay it.
- **STOP — Package 14 automated owner-tools qualification:** privacy and native tests pass, but the release-source ancestry check rejects the package13 squash history. The single probe dispatch stopped before the VM; qualification is unrun. See [REPORT](../reviews/14-owner-tools/REPORT.md). No image rebuilt or published. Installation stays NOT RELEASED.


- **OPEN — 14b NVIDIA Flatpak sync on the real GPU:** after the qualified
  first-login preparation and then network connection, confirm the stock sync
  finishes, both matching NVIDIA GL/GL32 runtimes are installed, and the complete
  prepared deployment list, pins, pending/transaction state and BLS entries are
  unchanged. The source permits this Flatpak-only deferred work; virtual graphics
  makes its NVIDIA condition false, so a VM cannot close this physical gate.
- **STOP — package 14 owner tools:** 14b accepts NVIDIA's Flatpak-only retry;
  14c keeps the tools stick absent at firmware startup, preserving every audit.
  The release verifier stops before the VM because its historical source is
  not an ancestor after the package13 squash; a fresh passing probe and
  qualification remain required for this route.
  The new commands are not released for physical installation. Existing laptop
  and followability gates remain open; see the [14 report](../reviews/14-owner-tools/REPORT.md).

- **OWNER DECISION / guide-only (13g, 2026-10-25) — recovery layout exception:**
  later AresOS layout changes affect only its running deployment. Retained
  backup Bazzite keeps the installer layout; recovery passwords use that layout.
  No mechanism writes later settings into stock. The VM proved de → us → de
  **before** rollback; **US-then-rollback was not performed**. The exception is
  source-verified from bootc's per-deployment `/etc`, not runtime-verified.
  Guides now resolve stock's title by checksum/serial after every reorder and
  before reboot, invalidate stale records even on queued rollback, and spell
  out `ares-recovery` → command → reboot → F12 → Linux while Windows stays the
  firmware default after §5. These guide revisions have no new VM qualification;
  physical installation/followability remains **NOT RELEASED**. See the
  [13g REPORT](../reviews/13-keyboard-layout/REPORT.md#13g--review-fixes-for-recovery-steps-2026-10-25).

- **DONE — 06e revised recipe and graphical rollback qualification:** [run 39851266266](https://github.com/carlsenares/AresOS/actions/runs/39851266266) passed the corrected Plasma Login observer, switch/rollback identity checkpoints, explicit negative assertions, real tty3 login/sudo/logout with the getty prompt confirmed, partition equality across four states, a visually inspected rendered rollback greeter and another stock default boot. The unchanged signed image and harness were used; one of two 06e full-run allowances was consumed. [Evidence](../reviews/06-image-release/REPORT.md#06e-vm-qualification-2026-10-22).

- **PARTIAL — GRUB recovery promotion (VM passed 11n; physical OPEN):** [11n report](../reviews/11-two-disk-rehearsal/REPORT.md#11n-safe-switch-test-prerequisites-and-continued-qualification-2026-10-24), [Part B 40139324523](https://github.com/Ares-Empire/AresOS/actions/runs/40139324523). Checksum-only bare-ID selection, stable ordered menu OCR, QMP Home/Down/Enter, stock booted at the previous index with AresOS still default, identity-checked promotion and a second unattended stock boot passed. No fallback. All reached protected/NVRAM/BootNext audits passed with final zero writes. The selected-highlight snapshot is inconclusive and is not claimed as proof of row1 highlight. Physical menu and actual German typing still require the laptop gate.

**Physical installation remains CLOSED.** The image switch/normal rollback and earlier-timing both-order automated Part A gates are complete; 11n passed protected-second VM GRUB recovery/promotion and revised Windows-first timing. Physical menu/typing, media, hardware and followability remain open:

- **DONE — Brief 06/06c image handoff:** §6 records the private signed RTX image, both official ISO hashes and the tested account/switch/rollback recipe. Two fresh AresOS boots, the full switched updater policy, inherited Homebrew denial for `ares` with owner access preserved, real tty3 administrator password/sudo and rollback to the retained stock checksum passed. Attached-disk partitions matched at all three stages; see the [06c report](../reviews/06-image-release/REPORT.md#06c-inherited-homebrew-qualification-2026-10-22). Legacy is identified only. The subsequent 11k rehearsal below qualifies the pinned live ISO route in disposable VMs; physical media and laptop checks remain open.
- **PARTIAL — Two-disk rehearsal (11k Part A passed both orders; Part B passed 11n protected-second):** [11k report](../reviews/11-two-disk-rehearsal/REPORT.md#11k-bounded-read-only-guard-retry-and-final-qualification-2026-10-24), [full 40119526154](https://github.com/Ares-Empire/AresOS/actions/runs/40119526154). Both complete installations, actual installed German console/X11/options read before pause, pause/pin, signed switch, policy, real tty3 login/sudo/logout, normal rollback, persistent/second default stock, Windows-default undo and detached Windows-like boots passed. Every reached protected-disk capture matched with a final zero-write record. All seven pauses were idle with the real daemon correctly excluded; no transaction needed cancellation and no staged update was present at the five pin checkpoints, so actual cancellation/discard remains unexercised. Part B stopped at the entry selector before menu selection, promotion or its second stock boot; that historical blocker is resolved by 11n's VM result; physical interaction stays open. Historical 11f's missing counter and 11i's missing decision values remain unqualified. Physical installation remains NOT RELEASED.
- **RESOLVED IN VMs by 11n — revised timing/BootNext/GRUB:** [11n report](../reviews/11-two-disk-rehearsal/REPORT.md#11n-safe-switch-test-prerequisites-and-continued-qualification-2026-10-24). Linux-default first/init stock starts without BootNext, installed German file checks before pause/pin, exact Windows-first restoration afterward, attached unattended Windows and detached markers passed in protected-second. All four recorded Linux BootNext writes were consumed. This does not qualify the new timing in protected-first; 11k's both-order evidence used the earlier timing.
- **RESOLVED by 11n — native switch fixture:** [11n report](../reviews/11-two-disk-rehearsal/REPORT.md#11n-safe-switch-test-prerequisites-and-continued-qualification-2026-10-24). Safe test stand-ins and five negative cases preserve the exact owner block. Complete native discovery passed 201 tests before the fresh probe, and again in probe/B. One fresh probe and one protected-second B passed on the same head. All16 new protected captures matched with16 final zero-write records. No normal rollback/default undo/policy/tty3 repetition this round.
- **VM PASSED / physical OPEN — loaded keyboard and physical typing (13f):** [Probe 40182972546](https://github.com/Ares-Empire/AresOS/actions/runs/40182972546) and [qualification 40184846815](https://github.com/Ares-Empire/AresOS/actions/runs/40184846815) passed on the same head. Both native suites passed all 237 tests, no skips. Actual installer de, injected de and injected us repairs preserved the whole stock identity list and old-entry arguments; only corrected serial1 was pinned. Corrected stock, all three AresOS boots (de/us/de), and rollback passed loaded maps, override-free booted command lines, physical tty3 login/password sudo/public text and inherited Homebrew. All three AresOS foot checks and policy checks passed. Finalization removed old serial0; every final pair entry was override-free, and rollback reached corrected pinned stock and a rendered greeter. All 13 protected captures, 14 zero-write/unmap counters, 13 BootNext checks and 12 NVRAM replays passed. The [13f REPORT](../reviews/13-keyboard-layout/REPORT.md#13f--physical-typer-coverage-and-one-final-qualification) records the minor preliminary sudo-cache-clear typing race; actual password sudo and public readbacks passed. No new Part B/manual GRUB qualification is claimed. Physical installation and the separate live-desktop KDE/KWrite laptop/followability gate remain OPEN / NOT RELEASED; 13c's image construction still requires owner review before merge.
- **OPEN — live-desktop keyboard on the laptop / followability (13d):** §4 step 1 remains an owner step: use the normal KDE setting and verify `y z / - " $ ä ö ü` in a text editor before Konsole, after every live boot. The VM qualification does not automate live KDE settings or KWrite; `os/ci/live_keyboard_ui.py` remains unused. A successful installed-system VM run cannot close this physical/followability gate. The real installer's German choice and all installed cmdline/map, tty3/password-sudo, foot typing, layout-change and rollback checks remain mandatory in CI.
- **OPEN — Media and followability; pinning DONE (11):** [media-tools.json](../os/manifest/media-tools.json) pins Fedora Media Writer Windows x64 5.3.2 and GParted Live 1.8.1-6 amd64 with official URLs/checksum sources; full downloads matched their publisher hashes. Both Bazzite ISO downloads also matched [installer-isos.json](../os/manifest/installer-isos.json); §2 defines the fail-closed install-day check for mutable `stable` URLs. **Still OPEN:** one physical ISO-file writer workflow, UEFI boots/record commands on expendable media, and the unaided novice trial. The novice must set/test German before Konsole from an initially English session; map Crucial after renumbering; reject unexpected Crucial partitions and Micron EFI writes; start record B after reboot; and complete default undo without opening/erasing. Owner later boot-tests their preserved recovery stick. A same-ISO automated installer path does not close the click-path or physical-media items.
- **OPEN — Helper:** live Windows/UEFI trials for original-ESP boot, disk renumbering, partition changes, unavailable BootCurrent and Windows booting from Crucial (must refuse undo). Confirm German power-state messages. Synthetic tests are insufficient.
- **OPEN — Fitting/firmware:** have Lenovo/service support qualify the fitting/thermal-parts instructions and supply a model-confirmed seating close-up, the applicable firmware storage-information screen and boot-order controls. In the novice trial, show a damaged-battery photo: the reader must stop before touching connectors/reconnecting power. On expendable hardware, require identification of fully/partly inserted and incorrectly supported SSDs **before touching the screw**. No guessed BIOS battery-disable or pad thickness. After release permits opening, the owner still must confirm actual slot vacancy, parts and both-drive detection in §3 **before installing the OS**.
- **OPEN — Safety + followability council:** review this draft and [OS-BASE §8 / Appendix C](design/OS-BASE.md#8-install-targets-image-delivery-and-choosing-an-os), with uncertainties/rehearsals visible.

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
