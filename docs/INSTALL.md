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

Use AC, lid open, backups/recovery stick disconnected. F12-boot the installer in UEFI mode; never click a Windows volume in the live desktop.

1. **Set the live desktop's German keyboard before opening Konsole:** open **System Settings**, search **Keyboard → Layouts → Configure layouts → Add → German**. Make German the first/active layout, choose **Global** switching if offered, and **Apply**. In a text editor (not a terminal), type `y z / - " $ ä ö ü` using the physical keys; every character must match. Otherwise stop and correct the layout. Repeat this after each live boot. [K1] Then open **Konsole** and collect [record C](INSTALL-RECORD.md#c-identify-both-drives-in-live-linux): fill the live identity/path columns and require PASS for identity, Micron unchanged and Crucial empty. Fill its installer columns/check when reaching steps 3 and 5 below.
2. Start the installer with **English (United States)**. On **Welcome → Change system keyboard layout**, add **German**, remove the initial US layout so the selected list contains only **de**, then **Save**. Require **de** in the Welcome keyboard summary before **Next**. This is the installed-system choice; keep the live-desktop physical-key test from step 1. On **Date and time**, turn off **Automatically set timezone**, then choose **Europe → Berlin**. These pages were previewed on the pinned ISO in [11b](../reviews/11-two-disk-rehearsal/REPORT.md); a preview does not release installation. [B1]
3. **Installation method → Change destination**: use record C's **same-session whole-disk path** to find the exact Crucial entry; copy/photograph its full text in the mapping. Deselect every other drive. **Destination** must show only this entry; choose **Use entire disk**. This erases the selected disk. [B3] A missing/ambiguous device name means stop. Do not choose alongside Windows, reclaim or manual partitioning.
4. At **Storage configuration**, leave **Encrypt my data** unchecked for the proposed disposable first trial; personal-data encryption needs a separate decision. At **Create Account**, keep **Use local account** checked; its description promises administrator access. Enter **ares-recovery** as **User name** first, then the full name and a strong unique passphrase twice. Do not create `ares` or enable root. The actual screen was previewed in 11b; **installed UID/group, encryption and two-drive qualification remain OPEN; do not install yet**. The required account checks are in [§6](#accounts-before-switching).
5. At **Review and install**, before **Erase data and install**, complete record C's **installer plan** check: require **only Crucial storage rows**, including a **new EFI partition at `/boot/efi`**, boot and system/data storage. [B4] Resolve every path through the same-session mapping, not example `vda` or a remembered `nvme0n1`. Photograph the whole summary privately. **Any Micron write/mount/EFI reuse, shared Windows EFI, missing new EFI or unclear target means FAIL — Quit.** Never dismiss Windows EFI wording as harmless. Every check must be PASS before continuing.
6. After all checks, install. On error, stop; do not retry with wider erase options. Reboot, remove USB and F12-select the new Linux entry. Unexpected enrollment/signature screens stop the trial; Secure Boot stays off. [B1]

The current live installer supports this whole-drive route; **its exact two-drive behaviour is not qualified here**. Release must prove all Linux boot writes, including fallback files, stay on Crucial. If it fails, the maintainer must qualify another route; the owner must not improvise legacy/manual or shared EFI.

## 5. Check installed Bazzite

Finish [record C](INSTALL-RECORD.md#c-identify-both-drives-in-live-linux): save Crucial's new GUIDs and Linux firmware entry; prove `/boot/efi` resolves to Crucial. Then **F12 → Windows Boot Manager**, run [record B](INSTALL-RECORD.md#b-compare-windows-after-each-stage). A mismatch or Windows repair/recovery prompt stops the trial. Keep records independently.

## 6. Switch to AresOS

**06e VM qualification passed for the revised 06d recipe.** [Full switch-only run 39851266266](https://github.com/carlsenares/AresOS/actions/runs/39851266266) reused the unchanged signed image and verified the rendered stock greeter, transaction identity inspections before reboot, daily session/account, strengthened updater policy, inherited Homebrew restrictions, real tty3 administrator password login/sudo/logout with the getty prompt confirmed, unchanged attached-disk partitions across four states, exact-stock rollback with a visually inspected rendered greeter, and another stock default boot. The [image job](https://github.com/carlsenares/AresOS/actions/runs/39818554327) passed two fresh AresOS boots before private publication/signing. See the [06e report](../reviews/06-image-release/REPORT.md#06e-vm-qualification-2026-10-22). **GRUB recovery promotion remains UNTESTED.** Physical installation remains NOT RELEASED until every [maintainer gate](#maintainer-release-gate) is closed, including the real ISO and protected-Windows two-disk rehearsals. This changes an existing Bazzite deployment; it does not install or partition a disk. The image contains labwc and a terminal, without Minecraft or Prism.

Release: **`ghcr.io/carlsenares/aresos@sha256:362af9b7d2a5573363d2cc441505dd076603d1d96c1b5c01af55589db2b6c402`**, private GHCR, immutable tag **`06-5578ab21b880091f26bfdc2eda22dd4f304a602b`**. [Release manifest](../os/manifest/release.json), [verification and screenshots](../reviews/06-image-release/REPORT.md). Base: signed `bazzite-nvidia-open` KDE **44.20261012.1**, digest `ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151`; no Steam Gaming Mode. CI constructs its stock starting disk directly from this upstream image. An actual installer/ISO walkthrough and the two-drive safety rehearsal remain separate open gates.

Official ISO metadata and complete download hashes, checked **2026-10-23** (the `stable` download names can change; a different hash means stop):

| Role | Official ISO | Official SHA-256 |
|---|---|---|
| Current live route retained by this guide | [bazzite-nvidia-open-stable-live-amd64.iso](https://download.bazzite.gg/bazzite-nvidia-open-stable-live-amd64.iso) | `776b76f3417723440ee1823d79ec02a2c22860df196d219024edb062ad00d8e6` |
| Legacy ISO identified as requested by brief 06; not substituted for §2–§4 | [bazzite-nvidia-open-stable-amd64.iso](https://download.bazzite.gg/bazzite-nvidia-open-stable-amd64.iso) | `85e701c0f53189b0fa32797ffe8144202dcaa8db6c7692fd4677f615537b24b8` |

The [live checksum](https://download.bazzite.gg/bazzite-nvidia-open-stable-live-amd64.iso-CHECKSUM), [legacy checksum](https://download.bazzite.gg/bazzite-nvidia-open-stable-amd64.iso-CHECKSUM) and official picker sources are recorded in [installer-isos.json](../os/manifest/installer-isos.json). Package 11 verified the complete [live download](../os/manifest/ci/11/inspect-2/installer/iso-download.json) and [legacy download](../reviews/11-two-disk-rehearsal/media/additional-downloads.json). The live ISO's [embedded container metadata](../os/manifest/ci/11/inspect-2/installer/var_lib_containers_storage_overlay-images_images.json) identifies the exact tested upstream digest. That metadata is not installation qualification: the installed deployment must still pass the two-disk gate below. Raw CI disks are never installation media.

### Accounts, before switching

In Bazzite's **Create Account** page, keep **Use local account** checked and use **`ares-recovery`**, with a strong unique passphrase held independently of AresOS. The actual pinned screen describes this as an account with administrator access; no separate administrator checkbox appeared in the 11b preview. Set the username before full name to avoid the page's automatic name suggestion. It must be the first ordinary account: **UID 1000**, member of **`wheel`**, verified after installation. Do not name it `ares`, enable root/passwordless administrator login, or reuse a game/Windows password. The real account page and backend wheel/password/root-lock state passed the 11b preview, but installed-account qualification on this ISO remains OPEN; the earlier 06e image-builder stand-in's UID proof is separate. Finish stock Bazzite's first-boot hardware setup before proceeding; upstream can reboot once to apply kernel arguments before allowing login.

The image supplies **`ares`, UID/GID 1001**, a locked password and no `wheel`/sudo rights. Its `sysusers.d` declaration creates this account at boot even when the installer's local passwd/group files survive the rebase. greetd automatically starts its labwc session on tty1. It is the daily account; keep it out of administrative groups. UID 1001 must be unused on stock Bazzite before switching. If the expected account/UID/group checks fail, stop rather than renumbering existing users or files.

Finish §5 and its Windows comparison first. In installed Bazzite, sign into `ares-recovery`, open Konsole and check:

```bash
id -u ares-recovery
id -nG ares-recovery
getent passwd ares
getent passwd 1001
sudo -v
```

Require `1000`, a group list containing `wheel`, **no output from either `getent`**, and successful sudo authentication with the recovery password. To perform the following maintenance, open a root shell with **`sudo -i`**. Root's direct login remains locked. Run each block separately and stop on any error. Keep AC connected, lid open, and all boot writes on Crucial; repartition neither disk.

### Retain stock Bazzite and authenticate the private pull

First identify and pin the actually booted stock deployment. This is the same checksum/index selection used by CI; it refuses a pending staged deployment:

```bash
python3 - <<'PY'
import json, subprocess
status = json.loads(subprocess.check_output(['rpm-ostree', 'status', '--json']))
booted = [(i, d) for i, d in enumerate(status['deployments']) if d.get('booted')]
assert len(booted) == 1 and not any(d.get('staged') for d in status['deployments']), status
index, deployment = booted[0]
assert 'bazzite-nvidia-open' in deployment.get('container-image-reference', ''), deployment
subprocess.run(['ostree', 'admin', 'pin', str(index)], check=True)
print('Pinned booted stock deployment:', deployment['checksum'])
PY
bootc status --json
```

Record the printed stock checksum, its image reference and current GRUB entry privately with record C. Require **`status.booted.image.imageDigest`** to equal the upstream SHA-256 above, with no layered packages or local OS modifications. Its origin reference may end in `:stable`; the payload digest, rather than that mutable tag, identifies the tested stock contents. An older/newer ISO deployment is outside this tested recipe. Do not discard the pinned deployment after this switch.

GitHub currently supports **personal access tokens (classic)** for private GHCR pulls; a fine-grained PAT cannot do this. Create a **classic token with only `read:packages`**, an expiry and no `repo`, write or delete scope, from [GitHub's token settings](https://github.com/settings/tokens/new?scopes=read:packages). This classic scope is not restricted to this one package. The account must have read access to this private package; the owner is `carlsenares`. Keep the token in the owner's password manager, never Git, the install record, screenshots or shell command arguments. CI uses only its temporary built-in `GITHUB_TOKEN`.

In the root shell:

```bash
install -d -m 0700 /etc/ostree
podman login --authfile /etc/ostree/auth.json --username carlsenares ghcr.io
chmod 0600 /etc/ostree/auth.json
```

Paste the read-only token only at the hidden **Password** prompt; require **Login Succeeded**. `/etc/ostree/auth.json` is root-owned mode 0600 and contains reusable, base64-encoded credentials, not encrypted storage. Bootc reads this persistent file across reboots. Exclude it from shared evidence and world backups; reissue the token during recovery. To rotate, repeat the login with the replacement token and then revoke the old token in GitHub. An expired/revoked token blocks new pulls; the installed and retained deployments remain bootable.

Verify the exact release using Bazzite's installed cosign and this workflow certificate identity:

```bash
install -d -m 0700 /run/aresos-registry
ln -sfn /etc/ostree/auth.json /run/aresos-registry/config.json
DOCKER_CONFIG=/run/aresos-registry cosign verify \
  --certificate-identity 'https://github.com/carlsenares/AresOS/.github/workflows/os-image.yml@refs/heads/pkg/06-image-release' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  'ghcr.io/carlsenares/aresos@sha256:362af9b7d2a5573363d2cc441505dd076603d1d96c1b5c01af55589db2b6c402'
```

Require successful verification and the exact release digest in the signed payload. A failure stops the switch. The signature uses GitHub OIDC and an ephemeral certificate, with no stored signing key. Sigstore's public transparency log exposes the signing repository/workflow identity and image digest; image layers remain private. Signature trust is separate from firmware Secure Boot, which stays off.

### Switch, reboot, and check recovery

Run the transaction in its own block. The subshell stops on failure and returns to your root prompt:

```bash
(
set -euo pipefail
bootc switch --retain ghcr.io/carlsenares/aresos@sha256:362af9b7d2a5573363d2cc441505dd076603d1d96c1b5c01af55589db2b6c402
)
```

**If the transaction prints an error, stop and don't reboot.** After success, run the inspection separately:

```bash
bootc status --json
```

Read the output before continuing: require **`status.staged.image.image.image`** to equal the full release reference above and **`status.staged.image.imageDigest`** to equal its `sha256:362a…c402` digest. The booted deployment must still have your recorded stock checksum; `status.rollbackQueued` must be false. Stop on missing/mismatched identity or pull, authentication, signature, disk-space or staging errors; do not try a mutable tag, change signature policy, remove the pinned stock deployment or alter partitions. CI uses this same transaction → identity inspection → reboot order.

Only after reading and accepting that checkpoint, reboot as its own step:

```bash
systemctl reboot
```

After reboot, expect **labwc with foot**, automatically running as `ares`. In that terminal, `id -u` must print **1001**. CI verified labwc/foot, GID 1001, the locked password and absence of wheel/sudo rights. **Super+Ctrl+Escape** opens another recovery terminal as the same daily user. **Ctrl+Alt+F3** opens an independent TTY: log in as **`ares-recovery`** with its password, then run **`sudo -v`** to test password-authenticated administration. CI performed an actual QMP-keyboard login on tty3 and password-authenticated sudo there. Maintenance happens from that account with `sudo`, or `sudo -i` when a root shell is required. When finished, **exit any root shell** with `exit`, then run `sudo -k` as `ares-recovery` and **log out of `ares-recovery`** with `exit`. Confirm tty3 shows the **login prompt** again. Only then press **Ctrl+Alt+F1** to return to labwc. Do not unlock `ares` or add it to `wheel`. Physical keyboard and hardware TTY behavior remain laptop checks.

In the administrator TTY, `sudo bootc status --json` must show the release digest under **`status.booted.image`**, the recorded stock deployment under **`status.rollback`**, and no unexpected pending update. CI verified these deployment identities and compared the attached Linux disk before switch, after switch and after rollback. That comparison covers one file-backed Linux disk; protection of a real Windows disk remains the two-disk/hardware gate. Continue with §7 only after those release gates permit the trial, then repeat record B in Windows.

The daily account cannot execute or read inherited Homebrew in `/var/home/linuxbrew`, write its prefix, or find brew on its session/login PATH. Boot tmpfiles applies a deny ACL only to reserved UID 1001 on that parent; existing owner UID 1000, files and other ACL entries are preserved. Brew setup/update/upgrade services remain masked alongside the other inherited updaters. CI ran the unchanged full updater audit and verified the original owner could run `brew --version` and write the prefix in all three deployments; it requested no install/update.

### Roll back to the retained stock deployment

If AresOS is usable enough for tty3, log in as `ares-recovery`, run `sudo -i`, and inspect `bootc status --json`. Require the rollback deployment to have the recorded stock checksum and Bazzite reference, with **`status.rollback.image.imageDigest`** equal to `sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151`. A `:stable` origin still rolls back to the retained local deployment; it does not fetch the tag again. If already booted into stock, use the identity-checked default step below instead of blindly running `bootc rollback`, which could select AresOS. Otherwise run the rollback transaction alone:

```bash
(
set -euo pipefail
bootc rollback
)
```

**If the transaction prints an error, stop and don't reboot.** After success, inspect separately:

```bash
bootc status --json
```

Read the output: require **`status.rollbackQueued: true`**, no staged deployment, and the same recorded stock checksum/reference/digest under `status.rollback`. AresOS remains booted until the restart. If any identity differs, stop. Only then reboot in a separate step:

```bash
systemctl reboot
```

06c booted the exact retained stock checksum again, verified its display manager and password-protected administrator, and compared every attached-disk partition identity/boundary across stock, AresOS and rollback. The original owner still ran Homebrew 7.0.9 with the same brew script hash. Rollback restores that deployment's `/etc`; shared `/var` and home data are not rolled back or erased. The UID 1001 deny ACL remains on `/var/home/linuxbrew` without restricting owner UID 1000. To reverse it on stock if that UID later needs Homebrew, an administrator runs `sudo setfacl -x u:1001 /var/home/linuxbrew`; AresOS reapplies its rule on its next boot. Stock Bazzite's normal updater policy returns too. This OS rollback does not replace a data backup.

If the new deployment cannot reach a TTY, use Bazzite's [GRUB previous-deployment recovery](https://docs.bazzite.gg/Installing_and_Managing_Software/Updates_Rollbacks_and_Rebasing/rolling_back_system_updates/): select the recorded stock/backup entry, normally `ostree:1` immediately after this single switch. Bazzite documents **Esc once, then ↓** if the menu is hidden. Match the recorded deployment, rather than assuming an index after further transactions. **Selecting stock in GRUB recovers that boot only. Complete the default step below before another unattended boot.** Do not format, repair Windows boot files or delete deployments to recover. F12 → Windows Boot Manager remains the everyday Windows return path.

### Keep recovered stock as the default

**GRUB recovery promotion: UNTESTED; open release gate.** 06e passed this command after normal `bootc rollback`, where stock was already first, followed by another default boot. That CI path does not select the previous GRUB entry once with AresOS still first; neither the index-changing recovery transaction nor physical menu interaction is qualified. The fixture regressions are not a boot rehearsal.

After booting the recorded stock entry from GRUB, **or if already booted into stock**, sign into `ares-recovery` and run `sudo -i`. Substitute your privately recorded stock checksum for `REPLACE_WITH_RECORDED_STOCK_CHECKSUM` below; do not copy one from CI. This transaction checks the booted stock reference/digest/checksum, resolves its current index, refuses a staged update, and makes that deployment first. An already-default stock deployment is handled safely:

```bash
(
set -euo pipefail
python3 - <<'PY'
import json, re, subprocess
expected = 'REPLACE_WITH_RECORDED_STOCK_CHECKSUM'
assert re.fullmatch(r'[0-9a-f]{64}', expected), 'Supply the privately recorded stock checksum'
status = json.loads(subprocess.check_output(['bootc', 'status', '--json']))['status']
stock = status['booted']
assert stock['ostree']['checksum'] == expected, stock
assert stock['image']['imageDigest'] == 'sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151', stock
assert stock['image']['image']['image'].startswith(('ghcr.io/ublue-os/bazzite-nvidia-open@sha256:', 'ghcr.io/ublue-os/bazzite-nvidia-open:')), stock
deployments = json.loads(subprocess.check_output(['rpm-ostree', 'status', '--json']))['deployments']
assert not any(d.get('staged') for d in deployments), deployments
booted = [(i, d) for i, d in enumerate(deployments) if d.get('booted')]
assert len(booted) == 1 and booted[0][1]['checksum'] == expected, deployments
index, deployment = booted[0]
subprocess.run(['ostree', 'admin', 'set-default', str(index)], check=True)
after = json.loads(subprocess.check_output(['rpm-ostree', 'status', '--json']))['deployments']
assert after[0]['booted'] and after[0]['checksum'] == expected, after
print('Default is the identity-checked booted stock deployment:', expected)
PY
)
```

**If the transaction prints an error, stop and don't reboot.** Inspect in a separate block:

```bash
rpm-ostree status --json
bootc status --json
```

Read both outputs. Require the **first `deployments` entry** to be booted stock with your recorded checksum, the expected stock digest under `status.booted.image.imageDigest`, no staged deployment and `status.rollbackQueued: false`. Only then perform a **second reboot with no GRUB selection**:

```bash
systemctl reboot
```

Require the stock greeter again, then sign in and repeat the two status commands (using `sudo` for bootc if needed). Require the recorded stock identity to remain booted and first. Stop if AresOS returns or the identity differs. Stock's normal automatic updates return after recovery; a later stock update can intentionally change its checksum.

Semantics checked against the [bootc rollback manual](https://bootc.dev/bootc/man/bootc-rollback.8.html), [OSTree set-default manual](https://github.com/ostreedev/ostree/blob/main/man/ostree-admin-set-default.xml) and [implementation](https://github.com/ostreedev/ostree/blob/main/src/ostree/ot-admin-builtin-set-default.c): rollback queues the rollback slot; set-default persistently moves the selected deployment to the front and writes the deployment list. This is why a blind rollback after booting stock from GRUB is not this recipe.

**If the owner later chooses public visibility:** no such change is made here. Public pulls can omit the token/login/auth-file steps; the digest, signature check, account rules, switch and rollback stay the same. Remove local registry credentials and revoke the private-pull token only after verifying anonymous access. Changing visibility exposes every published image layer and remains an owner decision. [Current GHCR authentication/visibility docs](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry), [free container-storage/bandwidth policy checked 2026-10-22](https://docs.github.com/en/billing/concepts/product-billing/github-packages).

## 7. First AresOS check: plain terminal, no Minecraft yet

Expect **labwc with foot terminal** after the released switch. Stay on AC, lid open: battery-critical handling and suspend are unqualified. Using handoff controls, check RTX 4060 (`nvidia-smi`), display/brightness, Wi-Fi after reboot, audible sound, German keyboard and touchpad. Test Super+Ctrl+Escape, authenticated Ctrl+Alt+F3, return to session, safe shutdown and second boot. This is the proposed P1a acceptance list, not released functionality.

**First-hardware-boot logind gate (03c procedure, authorized by brief 03e):** after the existing installation and recovery-account prerequisites, on AC with the plain terminal session, try an interactive Ctrl+Alt+F3 login with the independently provisioned recovery administrator. Return using the supplied session steps, then verify a short physical power-button press reaches logind and cleanly powers off. On the next boot, inspect the previous persistent journal with journal-reading privileges:

```bash
journalctl -b -1 -u systemd-logind.service --no-pager
journalctl -b -1 --no-pager
```

Retain both outputs, the image digest and pass/fail privately. Require the button record and orderly shutdown; merely seeing the laptop turn off is insufficient to establish the logind path. Also repeat a fresh boot/session/recovery trial. Missing records or an unreadable journal leave this hardware gate unmet. CI may label its offline logind check **REPORTED, NOT BLOCKING: first hardware boot required** only when the kernel Btrfs mount is explicitly unsupported **and** its userspace reader tooling is explicitly absent (03f). That single path then remains a hardware gate; CI still requires QMP guest shutdown, `poweroff.target` and two fresh VM passes. Filesystem/extraction/verification errors, absent journals or expected boots, wrong boots and missing required logind records remain blocking CI failures.

Boot Windows directly with USB absent and present (select Windows explicitly), check files/sound/network and repeat record B against the **original** baseline. On failure, return to Windows and report it. Minecraft/app/save/restore and daily battery use are later milestones.

## 8. Choose the OS at startup

**F12 chooses once**: Windows Boot Manager or the recorded Linux entry (possibly still called Fedora/Bazzite). Keep Windows default for the first trial. For persistent order, after §1's encryption check: **F2 → More Settings → Boot → UEFI**, move the identified entry first using displayed controls, **Save and Exit**. Verify a no-key/no-USB restart. Preserve Windows Boot Manager. [L3]

If an update changes the order, use F12 for AresOS, then restore the preferred order as above. The laptop may drop automatic F12 entries for unplugged devices, such as the installer USB; that is normal. Missing Windows Boot Manager or the Linux entry while its SSD is attached, unfamiliar screens, changed Secure Boot or Windows recovery prompts mean stop with the record. Do not reset firmware defaults, clear TPM, delete entries or run Windows boot repair commands.

## 9. Undo: return to everyday Windows

**Default: stop using AresOS; leave Crucial installed.** Keep Windows backups/recovery USB. F12-boot Windows directly, USBs absent, and run record B with stage **before-undo**. Require PASS for its **original Micron EFI boot target**: a later Windows repair might have placed boot files on Crucial despite successful login. Restore **Windows Boot Manager** as default (§8), then restart without pressing keys and with no USB connected. Require Windows to start normally; repeat record B as **after-undo**. **Done.** Linux and its data remain on Crucial; no case opening, erasure or partition change is needed.

**Optional extras, only if you want removal or reuse:** first export Linux data and verify independent copies. Complete the direct-Windows/default-boot checks above immediately before proceeding (repeat **before-undo** if returning later).

- **Remove Crucial:** follow §3's full shutdown, AC/ESD/cover/battery precautions, including **external bulging before opening and the immediate battery-damage inspection after lifting the cover**. Any warning sign means stop before connector work, no pressure/handling or power reconnection; contact Lenovo or a qualified repairer. Otherwise remove only the identified Crucial using Lenovo Figure 9; retain its screw safely. Reconnect battery, close up, boot Windows and repeat record B. Removal preserves Crucial's data; store it safely.
- **Keep the SSD but erase AresOS:** the pinned undo medium is **GParted Live 1.8.1-6 amd64**, [official ISO download](https://downloads.sourceforge.net/project/gparted/gparted-live-stable/1.8.1-6/gparted-live-1.8.1-6-amd64.iso), SHA-256 **`d789c38779f0d6f7026c12f44c2c52a04f66e28a1aea7d51f3045ad1bbf28411`**. Its [official checksum source](https://gparted.org/gparted-live/stable/CHECKSUMS.TXT) and release directory are recorded in [media-tools.json](../os/manifest/media-tools.json). On install day require the fresh official checksum and the complete downloaded file hash to match this pin; a mismatch or missing version means stop. The ISO/physical-media boot workflow remains **OPEN**. After release, write it to **ARESOS INSTALLER — ERASE OK** using §2's pinned writer and ISO-file workflow. F12-boot; choose German keyboard/English interface and test `y z / - " $` in a text editor before **Terminal**. Repeat record C and [record D's live undo check](INSTALL-RECORD.md#d-before-erasing-crucial-from-live-media). In GParted select the matched Crucial, **Device → Create Partition Table → gpt**. Before that dialog's **Apply** (writes immediately), recheck its whole-disk path, require every Crucial partition disposable, neither SSD mounted and no Micron action. [G1] This clears the layout for reuse, **not secure data sanitisation**. Shut down/remove USB, boot Windows and repeat record B. Cancel Windows initialise/format prompts until separately deciding how to reuse Crucial.

Never extend C: or edit Micron for undo. An unused Linux firmware entry can stay until reviewed cleanup. If Windows does not boot independently or any identity check fails, remove/erase nothing.

## Maintainer release gate

- **DONE — 06e revised recipe and graphical rollback qualification:** [run 39851266266](https://github.com/carlsenares/AresOS/actions/runs/39851266266) passed the corrected Plasma Login observer, switch/rollback identity checkpoints, explicit negative assertions, real tty3 login/sudo/logout with the getty prompt confirmed, partition equality across four states, a visually inspected rendered rollback greeter and another stock default boot. The unchanged signed image and harness were used; one of two 06e full-run allowances was consumed. [Evidence](../reviews/06-image-release/REPORT.md#06e-vm-qualification-2026-10-22).

- **OPEN — GRUB recovery promotion (06d, UNTESTED):** boot the recorded previous stock entry once while AresOS remains the default, run the identity-checked `ostree admin set-default` step in §6, then reboot with no selection and prove stock stays first and booted. CI's normal rollback/default-stock repetition does not qualify this path. Physical menu/keyboard interaction also remains open.

**Physical installation remains CLOSED.** The image switch/recovery/rollback gate is complete; every other gate below remains OPEN:

- **DONE — Brief 06/06c image handoff:** §6 records the private signed RTX image, both official ISO hashes and the tested account/switch/rollback recipe. Two fresh AresOS boots, the full switched updater policy, inherited Homebrew denial for `ares` with owner access preserved, real tty3 administrator password/sudo and rollback to the retained stock checksum passed. Attached-disk partitions matched at all three stages; see the [06c report](../reviews/06-image-release/REPORT.md#06c-inherited-homebrew-qualification-2026-10-22). Legacy is identified only. The current-live ISO/selected-drive walkthrough and protected-Windows write audit are still required below.
- **OPEN — Two-disk rehearsal (11d STOPPED at reverse-order firmware audit):** [11d report](../reviews/11-two-disk-rehearsal/REPORT.md#11d-owner-read-only-token-and-continued-qualification-2026-10-24), [probe 40038465601](https://github.com/Ares-Empire/AresOS/actions/runs/40038465601). The owner's narrowly authorized read token resolved/pulled the original signed digest; its signature and unchanged runtime identity passed, and the complete live ISO matched its existing pin. The runner passed 133 native regressions. Both drive orders reached the real Web UI review with only the target selected and a new target EFI partition planned. Pre-install detached Windows markers booted in both orders; all six reached protected-disk captures stayed identical and all six write counters were zero. However, reverse-order OVMF removed an automatic entry for the still-attached protected drive and reused the DVD entry's ID for that drive. Brief 11c explicitly forbids these changes: the probe failed and work stopped without widening the rule. No full run or installation was authorized. Both complete install/switch/policy/tty3/rollback/default-undo sequences and post-install/post-undo Windows independence remain unqualified. GRUB promotion is **UNTESTED**, blocked by the missing installed target and firmware-contract PLAN-GAP. No physical installation is released.
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
