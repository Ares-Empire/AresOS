# AresOS: OS base decision

AresOS will start in your Nether home, with your apps in the world.\
The home is a desktop: you cannot die, and it need not be a playable survival game.\
Normal Minecraft opens as an app, with its own worlds, servers and normal rules.\
On this laptop, the desktop saves and closes while you play, then returns afterwards.\
Bazzite is the chosen foundation; Ubuntu is the fallback if the laptop trials fail.\
Secure Boot stays off; this installation needs no MOK enrollment.\
AresOS takes its own Crucial SSD; Micron Windows stays intact. Linux starts first during offline setup; Windows becomes default in the tools round trip and is proved in INSTALL step 5.\
Before shutting down, it asks you to finish work in your other apps and saves the world.\
Backups, their recovery information and a repair USB must survive losing either internal SSD.\
Graphics, Windows return, battery comfort and sleep still need real laptop tests.

**Revised 2026-11-09 for [brief 21](../../briefs/21-everyday-account-and-chrome.md) (owner decision in session: admin rights "Like Windows"; browser Google Chrome).** This supersedes the locked daily account below (the account split in the section 8 handoff and the daily-account rules of the A1 updater policy). The everyday account `ares` is in `wheel`: it gets admin rights behind its own password, like Windows' Yes prompt, and Flatpak apps and Homebrew work. Claude, running as `ares`, can't use admin rights unless the owner types that password. `ares-recovery` stays as a spare administrator. What still holds: the OS image and firmware change only through the signed release route or an explicit `sudo` by the owner, so `rpm-ostree`/bootc, systemd-sysupdate, `fwupd`, the Bazzite updater/portal actions, `uupd`, `ujust` and `topgrade` stay out of the daily account's polkit and executable reach, and automatic updaters stay masked. Google Chrome is built into the image under `/usr`, without Google's repository or cron job, so its updates arrive with AresOS releases. Earlier statements in this file record the reasoning of their time.

Revised 2026-10-22 for [brief 10](../../briefs/10-own-ssd-install.md): the owner chose a dedicated internal Crucial P310 500 GB SSD. This replaces brief 05's same-drive primary route; [that guide](../INSTALL-SAME-DRIVE.md) remains an archived fallback requiring separate authorisation. Bazzite, Secure Boot off, session/save contracts and the early plain-session hardware gate remain. The single [current gate/status table](../INSTALL-STATUS.md#current-gates) governs every installation claim in this design; historical qualification belongs in its linked reports.

**Evidence convention:** **Verified** means primary documentation/source was read, not that AresOS works. **Assumed** means unmeasured, inferred or supplied by the project. **Proposal** means a future design requirement, not an implemented capability. These labels cover the paragraph/table they introduce. External references retain their dated checks in Appendix F; the own-SSD revision has **2026-10-22** sources in the install guide and record. Inherited research is not presented as newly rechecked. This document authorizes no installation.

**Assumed / owner-reported inputs (2026-10-21):** LOQ 15IRH8, i5-13500H, RTX 4060, Intel graphics, 16 GB RAM, German Windows 11 Home, UEFI, Secure Boot **off**, one Micron 512 GB NVMe with about 168 GB free on C:, F12 boot selection. Device encryption is only believed off; require an explicit fully-decrypted status check. Disk serial, exact partition boundaries, GPU wiring and spare-slot occupancy remain unknown. No local machine inspection was performed.

## Recommended stack

**Proposal — choices, not qualified combinations:**

| Layer | Choice |
|---|---|
| Base | Custom image derived from Bazzite desktop NVIDIA, pinned by digest; Ubuntu 26.04 LTS fallback. [Z1], [Z2], [U1] |
| OS as code / build | Repository Containerfile, configuration, manifests and tests; GitHub Actions Linux build using the Universal Blue image template approach. [Z3] |
| Session | greetd → labwc + Xwayland, recovery UI, app helper and independent game/power supervision. [S1], [L1] |
| Graphics | Base image's complete signed NVIDIA stack; NVIDIA renders Minecraft, Intel drives the session where wiring permits. [Z1], [N1] |
| Desktop | Native Prism, Java 25, Minecraft 26.2, Fabric, shell mod; Sodium/Iris after qualification. [P2], [M1] |
| Gameplay | Separate Prism instance without the shell mod; desktop normally stopped during play. |
| State / recovery | Separate home data; clean world backups; retained complete OS deployment and independent repair media. [Z4], [B1] |
| Maintenance | One AresOS authority; inherited automatic installation disabled; reviewed images and explicit restart. |

## Owner decisions

**Decided (2026-10-22):** install on the ordered Crucial P310 500 GB in the believed-empty 2280 slot; never resize or install onto the Micron Windows disk. Bazzite, Ubuntu fallback, separate gameplay and Secure Boot off/no MOK remain. Fit/slot/thermal parts must be confirmed; seeing one disk in Windows is not proof of vacancy. Turning Secure Boot on later remains a separate decision.

**Proposal — qualification before installation:** current live ISO with selected-Crucial whole-drive automatic partitioning and its own EFI, brief 06's private image/account/rebase handoff, Windows-first/F12 selection, and independent backup/recovery media. No shrink/extension exceptions apply. The first disposable, unencrypted trial stays on AC; before personal use, decide encryption, backups and power/noise limits. Suspend remains unqualified.

## 1. Base and OS as code

**Verified:** Bazzite documents custom images and previous-deployment recovery. [Z2], [Z4] Its current FAQ assigns RTX cards to **`bazzite-nvidia-open`**, distinguishing the older-GPU `bazzite-nvidia` family. [DB4] **Repository evidence:** package 03 at `7ae41a73c7e01f871b6426a34903cde13519d110` pins a `bazzite-nvidia` digest. That was brief 05's historical **PLAN-GAP**; the later frozen release and remaining hardware limits are recorded in the [current table](../INSTALL-STATUS.md#current-gates). Preserve the qualified upstream stack; build our session/policy in a Containerfile.

**Proposal — concrete comparison, grounded in linked capabilities:**

| Concern | Chosen Bazzite NVIDIA derivative | Ubuntu 26.04 fallback |
|---|---|---|
| Our labwc session | Add greetd/labwc; disable the inherited display manager, desktop autostarts and power agents. Retain unused desktop packages initially if removal risks driver dependencies; never start KDE/GNOME/Steam desktop sessions alongside ours. [Z2] | Start from a minimal install and add the same session; fewer inherited desktop policies to remove. Install recipes are documented. [U3] |
| Trust | Leave Secure Boot off; no MOK. Still verify base and derivative image provenance. Container signatures are separate from boot enforcement. [DB3], [Z3] | Same firmware policy; qualify matching kernel/NVIDIA packages. [U2] |
| Update ownership | Replace Bazzite's automatic update entry points with AresOS maintenance; digest pinning alone is insufficient. [Z6], [Z7] | Disable/integrate unattended upgrades and package timers; lock complete packages and sources. [Z8], [U4] |
| Recovery effort | Boot the retained complete deployment; use independent media for broken root/ESP. Persistent state needs separate recovery. [Z4], [Z9] | Restore a verified previous system image or reinstall from a complete offline package bundle; an old kernel alone is insufficient. [U2] |

**Proposal:** Bazzite remains the owner's choice for less recurring repair. If NVIDIA, labwc, partition-safe installation, offline recovery or direct Windows return fails P1a/P3, investigate, then qualify Ubuntu against the same gates. Do not relax Windows protection or change the base inside an installer.

**Verified alternatives:** NixOS offers declarative generations but the evaluated Lanzaboote route enrolls firmware keys; Arch media lack Secure Boot support; Debian live-build supports image customization. [D1], [D2], [D3], [D5] **Proposal:** defer these and a standalone bootc distribution; none removes our session and recovery obligations. Actions is the primary builder; optional WSL2/Docker builds do not qualify native boot. [G2], [W1], [W2] Appendix A defines reproducibility and budget gates.

## 2. Graphics, memory and power

**Verified:** NVIDIA documents application offload and workload-dependent power management; its open modules require matching userspace. [N1], [N2], [N3] **Proposal:** qualify the image's kernel, modules, firmware and libraries together. Start with Xwayland Minecraft and per-game NVIDIA offload, never session-wide GPU environment variables. Ordinary apps launch from the helper's clean environment. Measure the actual game renderer; all-NVIDIA composition is a fallback test, Intel-only Minecraft does not pass.

**Verified:** Minecraft 26.2 has an experimental Vulkan option. [M3] **Proposal:** first qualify OpenGL explicitly, without shaders, then the pinned Iris/Sodium combination. Start at 60 foreground FPS on AC, 30 on battery, with shaders off on battery. These are hypotheses, not performance evidence.

**Proposal:** budget desktop Java heap at 3 GiB initially, with a 5 GiB whole-process working target; normal gameplay gets a 4 GiB heap and 6 GiB working target after the desktop exits. Reserve 3 GiB for OS/recovery and 4 GiB for ordinary apps, leaving roughly 3 GiB headroom in gameplay mode. Measure actual available RAM and native/GPU allocations rather than equating heap with total memory. Two resident games would budget 18 GiB before extra shader pressure, so simultaneous residency is deferred; pausing alone does not meet our release-memory requirement. Appendix B5 defines pressure handling and the GPU gate.

**Proposal:** when an app is foreground, clear game inputs, mute desktop audio, pause desktop simulation through the mod and reduce rendering to at most 5 FPS, testing zero rendering when fully hidden. At five minutes idle, blank the display without suspending; save/stop the desktop if hidden/idle power remains excessive. Before daily use, compare identical browser workloads with the world stopped, hidden and visible on AC/battery and agree measured power, temperature, noise and return-time limits. A failed limit keeps the save/stop fallback and blocks a battery-comfort claim.

## 3. Secure Boot and Windows return

**Owner-reported:** `msinfo32` shows UEFI and Secure Boot off. **Verified:** Bazzite says to skip MOK setup when Secure Boot is disabled. [DB3] **Policy:** keep it off; no enrollment, firmware-key replacement, TPM clear or storage-mode change. A later enablement is a separate owner decision, including image/driver trust and Windows-return tests. Signed-container verification remains required even with firmware enforcement off.

**Verified:** Microsoft exposes encryption conversion status separately from protection status. [DW1] **Policy:** before fitting the SSD or changing firmware, back up and confirm C: is fully decrypted, 0% encrypted, protection off; a missing Settings page or Secure Boot off is insufficient evidence. If encrypted/suspended/unknown, stop for an owner-reviewed encryption plan and independently saved matching recovery key. Never supply that key to Linux. Where no protector/key exists because the disk is decrypted, record that fact rather than demanding enrollment just to create one.

**Verified:** Fast Startup uses hibernation; Windows supplies commands to disable hibernation and report available states. [DW2] **Policy:** disable both before the installation trial, restart Windows and verify. Use F12 → **Windows Boot Manager** for direct return. Preserve its partition and boot files; the installer may add a separate Linux NVRAM entry/change order, which the owner records and restores to Windows-first if necessary. Test Windows with USB absent and present. Unexpected recovery/repair prompts stop rollout; no zero-prompt guarantee is claimed.

## 4. Session, apps and recovery

**Verified:** labwc supplies stacking windows, decorations, actions and toplevel integration; cage targets one maximized app, sway an i3-style session, and gamescope gaming presentation. [L1], [L2], [L4], [C1], [C2], [C3] **Proposal:** keep labwc, using a borderless maximized Minecraft window below normal apps. A custom compositor adds unnecessary work; gamescope can be evaluated later for gameplay.

**Proposal:** closing the foreground app's last window returns to the world; closing a background window preserves the active app's typing focus. Dialog closure returns to its parent. Alt+Tab switches apps, Super+Home returns to the desktop, Alt+F4 requests ordinary app close. Clear held keys/buttons at transitions, and capture the pointer only after confirmed game focus. Track actual windows, including existing processes; process exit alone is not closure. Appendix B1 specifies the versioned mod/helper boundary.

**Proposal:** Super+Ctrl+Escape (Ctrl = Strg) opens a recovery terminal; an authenticated Ctrl+Alt+F3 (Ctrl = Strg), or Ctrl+Alt+Fn+F3 (Ctrl = Strg), TTY survives compositor failure. Apps live independently of the game process. Restart a crashed desktop underneath the active app, using both a short-window limit and a persistent consecutive-failure budget; never repeatedly reopen a broken world. Authentication, deliberate stops and memory pressure suppress restart. See B2.

## 5. Starting the desktop and playing Minecraft

**Verified:** Prism implements instance/account selection, Microsoft authentication/refresh, wrapper hooks, and world/offline arguments in the researched release source. Minecraft metadata specifies Java 25; Quick Play identifies a save folder. [P1], [P2], [P3], [P4], [P5], [M1], [M2] **Proposal:** choose native Prism over a custom account/download implementation; retain its UI for setup/re-login. The official launcher remains a manual alternative, without a qualified unattended-world contract here.

**Proposal:** provision a managed `AresDesktop` instance and marked `AresHub` save, then launch it through Prism's `--launch <instance-id> --world AresHub`. Pin all game/runtime/mod inputs and hashes as a tested manifest. Missing data, corrupt worlds or authentication failures open recovery, never a replacement world. A prepared offline launch must preserve the same UUID/inventory; first-run downloads/login require network. No account-file edits or authentication bypass.

**Proposal:** the app `minecraft` opens a separate gameplay instance without the AresOS mod, desktop marker, app inventory or desktop rules. Survival worlds and multiplayer servers such as Hypixel belong there. Save/stop the desktop before gameplay starts; when the actual game exits, load the desktop once and return to the hub. Keep other apps alive. Super+Home during play offers “Return to desktop” and asks the owner to save/quit gameplay normally; it never kills an unsaved game. Failed launch or crash returns to recovery/desktop with a clear error, not an automatic gameplay restart. B4 specifies locks, identity, focus and optional Lunar qualification.

**Proposal:** desktop worlds live under `/home/ares/.local/share/aresos/worlds/`, linked into only the desktop instance. Gameplay uses a separate directory and manifest. Only marked desktop saves receive no-death/Live/Build rules, as required by [01b](../../briefs/01b-first-app-fixes.md). The first Nether hub needs a small additional mod package; package 01 did not build it.

## 6. Boot look

**Verified:** Plymouth provides early graphical splash; greetd provides initial auto-login. [S1], [S2] **Proposal:** firmware → signed boot chain → simple splash → labwc loading/recovery view → controllable hub. Start with original placeholder art; later allow a locally supplied logo overlay excluded from Git and CI artifacts. Never copy the owner's Minecraft directory or modify firmware artwork. Keep errors and terminal access visible.

**Assumed planning range:** roughly 22–60 seconds after selection for a prepared boot, potentially longer with shaders/USB; this is inherited estimation, not a measured promise. **Proposal:** measure ten cold boots to accepted input, separately reporting firmware, session and game time. Downloads and first login are setup, not ordinary boot. Art and timing polish follow the early hardware gate.

## 7. Everyday controls and safe power

**Proposal:** minimum out-of-game controls include NetworkManager/network login and captive-portal browser, terminal, files, clock/keyboard setup, audio, brightness, battery alerts, notifications, a polkit agent and file/URL portals. Existing tool interfaces support these roles. [E1], [E2], [E4], [E5], [E6], [E7] Bluetooth pairing through BlueZ and polished in-game settings follow the first trial. [E3] Fallback controls must work before Minecraft loads.

**Verified:** logind has automatic lid/key actions and a default five-second delay-inhibitor limit; UPower exposes critical-battery action/status. [Z13], [Z14] **Proposal:** a small system power coordinator and independent game guardian own saving even if the app helper fails. Disable automatic sleep at system level. Lid closure saves/stops the desktop and blanks the panel, leaving apps running; reopening offers a desktop return. A short power press requests normal shutdown. The first-run screen explains that closing the lid is not sleep and the laptop remains on.

**Proposal:** ordinary shutdown first displays a cancellable “close your apps first” screen, including gameplay and browser/editor windows. Until these are closed and the owner confirms any background work is finished, do not stop Minecraft or request power-off. Then stop/save the world, make its clean local checkpoint, and power off; failure leaves recovery. Critical battery instead starts saving early, has a bounded emergency deadline and skips network backup. Exact event defaults, helper-failure paths and unavoidable hard-power-loss limits are in B3; they gate the first hardware trial.

**Proposal:** suspend/hibernate remain disabled. Enabling suspend requires a later choice of retained-process versus stop/relaunch behavior, explicit resume transition, position/focus semantics, no duplicate game, measured wake-to-input time and repeated hardware tests. A hidden Sleep button alone is insufficient.

## 8. Install targets, image delivery and choosing an OS

**Owner decision, 2026-10-22:** Crucial P310 500 GB (`CT500P310SSD801`) gets the whole AresOS installation; Micron `MTFDKCD512TFK` 512 GB retains Windows. Expected capacities are approximately 465/477 GiB, calculated from the stated decimal sizes, not measured. Identify by model **and serial**, then GUIDs once created, never by size or enumeration alone. [Brief 10](../../briefs/10-own-ssd-install.md) supplies this configuration. Lenovo's model-family specification confirms a 2280 slot, not its occupancy; fitting/parts/firmware details and dated sources are in [INSTALL §3](../INSTALL.md#3-fit-and-identify-both-drives).

**Verified upstream capability, 2026-10-22:** the current [Bazzite guide][DB1] documents installing to a separate drive with automatic storage selection. Its [destination screen](https://docs.bazzite.gg/img/live-installer-drive.png) offers whole-drive installation; the [review example](https://docs.bazzite.gg/img/live-installer-partitions.png) shows EFI, boot and Btrfs on the selected example drive. **This is not a two-drive write audit.** Our release must establish a new Crucial ESP and zero installer/rebase/undo writes anywhere on Micron, including its EFI/fallback files. We do not infer safety from an unchecked disk alone.

| Route | Status / consequence |
|---|---|
| **Current live ISO, automatic, only Crucial selected** | Primary proposal. Removes C: shrinking, interval arithmetic and manual subvolume creation. New EFI must be on Crucial; review every storage row before erase/install. |
| Legacy ISO, explicit Crucial-only layout | Maintainer fallback only if the current installer cannot satisfy the exclusive-target contract. Requires a new qualified walkthrough; no spontaneous owner switch. |
| Same-drive legacy/manual | [Archived fallback](../INSTALL-SAME-DRIVE.md), not authorised by current hard rule 1; a new owner decision/exception and refreshed qualification are required. |
| Shared Windows EFI or Windows disk in any install target | Rejected. A separate disk must not silently retain the shared-ESP write boundary of the old automatic alongside-Windows route. |

**Proposal:** preserve two labelled USB sticks; fit the new SSD using Lenovo's sequence, confirm both drives in firmware, and leave it uninitialised in Windows. Boot official live `bazzite-nvidia-open` KDE media, identify both disks, select only empty Crucial and automatic whole-drive installation. Let the qualified ISO supply its own layout; this revision does not impose the historical 1/2/93 GiB sizes. Brief 06 must validate that layout with the rebase/rollback recipe. Secure Boot stays off; agents do no physical fitting, disk queries or boot operations.

**Qualification and uncertainty:** an offline two-disk VM audit must compare the entire protected disk byte-for-byte through installation, rebase, rollback and undo, including GPT and EFI, and test reversed disk order. Fitting parts, two-drive firmware inventory and actual NVIDIA boot remain hardware checks. If exclusive EFI targeting cannot be demonstrated, stop before physical installation; do not borrow Windows' ESP or ask the novice to repair boot files. Disconnecting/removing the Micron is not part of this guide. Backups must survive losing either internal drive.

### Image delivery decision

**Verified, checked 2026-10-21:** GitHub Free lists 500 MB for general Packages storage, **but Container registry image storage and bandwidth are currently free**, with notice before a policy change. The brief's 500 MB premise alone does not rule out private GHCR. [DG1] An OS image's several-GB size is a planning assumption until measured. Keep Actions artifact/minute quotas separate; the free registry exception does not make CI free without limits.

| Option | Consequence for this project | Recommendation |
|---|---|---|
| Public OCI registry (for example public GHCR) | Public image pulls need no private credentials; image layers/configuration are public even if Git stays private. Audit redistribution/content and secrets first. [DG2] | Viable only after explicit owner approval to publish; not necessary merely to avoid the stated 500 MB limit. |
| Local Podman build inside installed Bazzite from this private repo | Avoids hosted image publication; needs private repo access, verified base/locked RPMs, CPU/time and substantial temporary disk space. Podman builds Containerfiles; bootc supports local-image transport. [DP1], [DR2] | Fallback if registry policy changes; measure peak use before adopting even on the dedicated SSD. A build alone does not prove the rebase works. |
| GitHub Release assets | Each asset must be under 2 GiB; several-GB payloads need splitting/reassembly plus hashes and a tested OCI import path. A release download is not an OCI registry endpoint. [DG3] | Good for small manifests/instructions; avoid as the first OS delivery channel. |
| **Private GHCR OCI image** | Retains privacy under today's container-registry exception; needs scoped authentication and image-signature verification on the installed system. [DG1], [DG2] | **Recommended owner decision for the first trial.** Recheck terms before publication; no paid usage or visibility changes in this package. |

**Repository evidence, not a hardware qualification:** `origin/pkg/03-os-image` was inspected at `7ae41a73c7e01f871b6426a34903cde13519d110`. `os/README.md`, `os/Containerfile`, `.github/workflows/os-image.yml` and `os/tests/guest.sh` show rootful Podman → `bootc-image-builder` → file-backed UEFI VM; the guest assertion names **bootc (OSTree storage)**. Only small evidence is uploaded, not an image. Bazzite documents rpm-ostree rebase and cautions about desktop changes. [DR1] This is historical construction evidence; the current handoff and its release limits are in the [status table](../INSTALL-STATUS.md#current-gates).

**Required handoff before fitting/installing:** qualified NVIDIA family/ISO pair, immutable accessible signed image, tested stock migration/rollback, inherited policy reconciliation, authenticated recovery and account split. `ares-recovery` owns UID1000/wheel; daily `ares` is UID1001 and, since the owner's 2026-11-09 decision (package 21), also in wheel behind its own password, which the owner sets after updating (no image password). ESP writes must stay on Crucial. The [current gate/status table](../INSTALL-STATUS.md#current-gates) distinguishes retained 06/11/13 VM results, package 14's pending qualification and the open physical gates. It links all qualification chronology, audit counts and historical screenshots in the reports. Do not treat the original package 03 inspection as the latest result.

**Media and followability requirements:** preserve the two labelled sticks; recovery boot test, pinned ISO/writer/GParted hash and expendable-media tests, complete destination/review records and novice live Windows/UEFI trials. Only the current table records their status; source/VM evidence cannot close physical trials.

### Boot choice

**Binding sequence:** Linux is first for live installation, stock one-time hardware setup/automatic reboot and offline login. In INSTALL step 4's Windows/tools round trip, restore Windows Boot Manager first, Save and Exit and observe unattended Windows. [Step 5](../INSTALL.md#5-prove-windows-and-corrected-stock) then proves no-key/no-USB Windows, original Micron EFI and corrected stock before any authentication/switch. Windows remains default afterward; F12 (or Fn+F12) selects one Linux start. [INSTALL step 8](../INSTALL.md#8-everyday-boot-and-recovery) supplies setup/order recovery. A changed order after an update can be restored there; do not delete Windows Boot Manager. Missing entries/trust changes/recovery prompts stop the procedure, not trigger boot-repair commands. GRUB remains for Linux deployments, not a prerequisite for Windows.

**Default undo:** revoke the dedicated private-pull token through GitHub from Windows/phone on permanent abandonment, including unbootable Linux and leaving/removing/erasing Crucial. Local/partition deletion is not revocation; the current table retains the fresh-authentication negative trial. Prove a fresh direct Windows boot still uses its original Micron ESP, restore Windows Boot Manager as default and verify an unattended restart. Leave Crucial installed; Linux and its data remain. Removal or erasure are optional extras after exporting Linux data and repeating the Windows checks. No Windows extension, EFI file surgery or shared-disk interval calculation. A stale Linux firmware entry may remain unused. Details and immediate-write warnings are in [INSTALL step 9](../INSTALL.md#9-retire-access-and-return-to-windows).

## 9. Updates, backups and recovery

**Verified:** Bazzite's desktop updates automatically; `uupd` includes automatic/manual services and can drive OS and app updates. [Z6], [Z7] **Proposal:** AresOS maintenance is the sole mutation authority for managed OS/apps/game components. Disable inherited automatic installers and bypass entry points from the first image. Initially the maintainer follows a manual maintenance checklist; later automation uses the same gates. Review security advisories at least weekly and urgent fixes within 48 hours; a stale unsafe prototype stays offline until safely serviced.

**Proposal:** verified signed image + manifest → close-app checkpoint → clean world stop/backup → preserve recovery set → controlled deployment/migration → explicit reboot → health checks. Downloading into an inert cache may happen earlier; staging a bootable deployment counts as maintenance. No live package layering, surprise reboot or unreviewed game upgrade. A fresh release B and A→B must converge on managed packages/configuration/services, including removals. A1 defines updater exclusions and migration checks.

**Verified:** Bazzite supports selecting/pinning a previous deployment; persistent data is separate. [Z4], [Z9] **Proposal:** before *any* update, retain a complete known-good OS/kernel/NVIDIA set, matching game inputs and compatible state checkpoint; prepare an independently bootable offline recovery USB. Manual rollback is the initial policy, not automatic failed-boot healing. Rehearse broken-root and damaged-ESP recovery separately. A2 assigns Wi-Fi and other state outside home explicit restore/reprovision rules.

**Verified:** restic needs repository credentials to retrieve/decrypt backups. [Z15] **Proposal:** before valuable saves, retain the repository address, password, backend/second-factor recovery access, instructions and matching game manifest independently of the AresOS drive, outside Git. Prove restore with that drive unavailable. Clean local copies alone are not drive-loss protection; B6 defines off-device backup and restoration.

## 10. Testing and the first real boot

**Verified:** QEMU supports virtual devices and Windows WHPX/TCG. [T1] **Proposal:** use file-backed VM disks for destructive installer/recovery tests; no physical Windows passthrough. Use existing acceleration or hosted Linux, without changing this laptop's settings. VM success cannot qualify real Secure Boot trust, NVIDIA, BitLocker return, wireless, battery or sleep.

**Proposal:** Appendix E now orders **P1 image → P1a early hardware boot → P2 Minecraft milestone → P3 full trial**. P1a installs/rebases through the reviewed handoff and tests plain labwc/terminal, `nvidia-smi`, display, Wi-Fi, audible sound, keyboard/touchpad, authenticated recovery and direct Windows return, before Minecraft exists. Keep it short, on AC and with the lid open; the prototype's critical-battery policy is not safe for unattended/battery use. P3 still requires **F12 → Nether on NVIDIA → app → save/shutdown → Windows**, USB present/absent, plus changed-world restore. A driver listing at P1a does not prove the game's renderer or daily comfort. All trials remain unexecuted in this docs-only package.

## Top risks

**Proposal — release gates:**

| Risk | Required reduction |
|---|---|
| Windows damage or lockout | Crucial-only selection and EFI, offline whole-Micron write audit, encryption/identity/boot-target checks, preserved recovery media and direct Windows-return tests. Wrong-device selection remains dangerous despite separate drives. |
| Save loss despite “successful” backup | Independent credentials, fresh-system restore, clean-save acknowledgement and one writer. |
| Unsaved app work or unsafe power event | Cancellable close-app checkpoint; independent saving; fault-injected lid/key/battery tests. |
| Bad image or state migration | Complete retained deployment, offline repair media, selective state restoration, A→B and rollback trials. |
| Unusable performance or heat | Stop desktop during gameplay; pressure isolation; owner-accepted measured daily-use limits. |
| Base-specific work before feasibility | Plain-session hardware gate immediately after the image, before Minecraft integration, updater UI, splash or sleep. |

## Appendix A — Build, maintenance and state contracts

### A1. Image and sole maintenance authority

**Proposal:** these are future repository areas; no OS code/config is created by this brief.

| Area | Required definition |
|---|---|
| `os/Containerfile`, `os/config/` | Bazzite NVIDIA base digest, exact added/removed packages, labwc session, safe power defaults, update exclusions and managed service state. |
| `os/manifest/` | Base and resulting image digests, architecture, package inventory, upstream signature identity, kernel/NVIDIA versions, config/state schemas and interface-v1 compatibility. |
| Install/rebase handoff | Official legacy ISO/checksum, manual gap/ESP policy, VM rehearsal and reviewed rebase/account/recovery recipe; no custom physical-disk installer in this package. |
| `os/game/` | Desktop and separate gameplay templates, exact runtime/mod hashes and download references; no entitled game assets or tokens. |
| `os/tests/`, CI | Pinned Actions/build tools; build, install, migration, rollback and fault trials; publish signed image and manifest only after checks. |

**Verified:** the Universal Blue template documents Containerfile derivation, Actions builds and container signing. [Z3] **Proposal:** use section 8's owner-approved delivery channel and a signed release manifest. Resolve the qualified NVIDIA family to an immutable digest; no placeholder is permitted in a release. Record signature verification, lock added package repositories/versions/hashes and fail if an input disappears. Keep signing secrets and private registry credentials out of Git, images and logs; the client receives minimum read access and public verification material. Nothing in this design authorizes public publication.

**Proposal:** use one documented deployment backend for the qualified image. Package 03 chooses bootc/OSTree for its fresh VM, whereas the stock Bazzite rebase instructions use rpm-ostree. [DR1] Before P1a, demonstrate the transition and retained-deployment recovery on the actual installed layout; never let both manage subsequent deployments independently. Automatic rollback remains deferred; manual previous-deployment selection is mandatory.

**Proposal — remove competing mutation paths from the first image:**

- Mask `uupd.timer`, `uupd.service` and `uupd-manual.service`; remove their passwordless invocation grants for the daily account. Upstream publishes these units and describes `AutomaticUpdatePolicy=none` for rpm-ostreed. [Z7], [Z16], [Z17], [Z18]
- Set rpm-ostreed automatic installation/staging to none; disable any bootc automatic update unit present in the selected image. Inventory system and user timers, services, autostarts and package hooks rather than assuming this name list is exhaustive.
- Disable inherited Bazzite Updater/Portal update, rebase and reset shortcuts, `ujust update`/topgrade automation, desktop software-center installation and automatic Flatpak/Homebrew/container updates. Do not launch inherited desktop setup/power agents. Managed apps and Prism/game updates use the same maintenance gate; personal data/saves remain writable.
- The daily account gets named maintenance requests, not general passwordless OS mutation. A separate recovery administrator can deliberately repair the system; record such changes and require reconvergence before ordinary use. Do not claim protection against an administrator intentionally bypassing policy.
- **Revised 2026-11-09 (owner, "Like Windows"; package 21):** the daily account is now an administrator behind its own password, and installs apps itself: Flatpak (system-wide installs ask for the password; Flatpak's on-demand helpers are unmasked and reviewed), Homebrew (run as the inherited prefix's owner after `sudo` asks for his password) and unit files (polkit asks). Upstream rules that let `wheel` act without a password give `ares` each action's own default instead, no polkit authorization is cached (every installed default is made uncached), and sudo asks for the password every time and keeps no ticket, so another program of his, such as Claude Code, cannot use admin rights unasked. Still excluded from the daily path, even with the password: polkit actions of `rpm-ostree`, systemd-sysupdate, `fwupd` and Bazzite, logind's next-boot and firmware-setup actions, modem firmware, TuneD profile changes (a profile can change kernel arguments), and the `uupd`/`ujust`/`topgrade`/Bazzite updater and store executables. Automatic Flatpak/Homebrew/container/OS updates stay masked. The owner changes the OS only through the signed release route or an explicit `sudo`.
- Scan the exact image inventory in CI. An unknown updater or unreviewed enabling change fails promotion. Outside maintenance, fire inherited timers and UI/manual entry points with a newer release available; installed versions, staged deployments, boot files and managed service state must remain unchanged.

**Proposal:** the maintainer reviews upstream/security changes weekly, urgent fixes within 48 hours. Before automation, apply approved releases manually using the same app/save/backup/AC/space/recovery gates. A pinned prototype with a known unresolved urgent issue is taken offline. No update may run before recovery readiness; rebuilding disposable media is the fallback until then.

**Proposal:** updates reconcile additions AND removals, renamed services, managed configuration, user overrides and private-state schema. Keep policy defaults in image-owned locations; migrate selected writable overrides explicitly. Archive conflicting overrides with a visible explanation. A failure stops activation. Compare fresh B with used A→B, including a removed package, obsolete enabled unit and config rename; allow only enumerated private differences. Rollback must restore compatible writable state too, because OSTree shares `/var` and merges `/etc`. [Z9] Never rely on atomic `/usr` alone to remove an old user unit.

**Proposal:** CI produces a rebuildable, auditable image, not a promise of byte-identical disks. No game account in CI. Measure runner time/storage for a single image and VM trial before scheduling builds; private Actions allowance is limited and the owner's remaining budget is unknown. [G1], [G2] Use on-demand large artifacts and short log retention; stop at budget, without enabling paid runners. WSL2/Docker are optional future development tools, not installation prerequisites on the owner's laptop. [W1], [W2]

### A2. Complete recovery and private machine state

**Verified:** deployment retention does not restore all persistent application state; NetworkManager's keyfiles can contain credentials outside home. [Z4], [Z9], [Z19] **Proposal:** before any manual or automatic update, pin the currently proven deployment by recorded identity, not an assumed index, and keep it until its successor passes boot, renderer, app, power and restore checks. Retain its kernel, initramfs, NVIDIA module/userspace/firmware, system libraries and AresOS components together, plus the corresponding game manifest and clean pre-conversion world. One old kernel or only an OCI reference is insufficient.

**Proposal:** require a second, independently bootable recovery USB with signed boot components, tools, offline copies of the known-good OS/driver payload and required dependencies, integrity manifest and instructions. Before the first update, the initial qualified release is this previous-system recovery baseline. Include legally obtained game/runtime files in private owner recovery storage when needed for offline launch, never in Git/shared CI. Verify the kit under the laptop's accepted trust and with network disabled. Registry access is not an offline recovery plan.

**JUDGMENT-CALL — first layout:** follow Bazzite's documented single Btrfs partition with separate `root`, `var` and `home` subvolumes mounted at `/`, `/var`, `/var/home`. [DB5] This replaces the earlier distinct home-partition requirement: fixed partition quotas waste scarce space on this SSD. Subvolumes are **not** independent backups; formatting the Btrfs partition destroys all three. Recovery must identify the filesystem UUID and subvolume paths, preserve home where selective repair is proven, or restore from independent backup. Never claim a generic root reformat preserves home. Inventory all persistent state and test selective recovery before valuable data.

| State | Proposed recovery policy |
|---|---|
| Worlds, gameplay saves, app documents and mod appearance/pins | Preserve home subvolume during qualified selective repair; encrypted off-device backup; restore matching manifest/world pair after conversion. |
| `/etc/NetworkManager/system-connections` and referenced VPN/certificate files | Selective encrypted machine-state backup; restore correct ownership/permissions and labels. Keep a separate manual Wi-Fi credential/instruction fallback. [Z19] |
| Recovery account/password, UID/GID, groups | Reprovision the same required IDs using recovery instructions and an independently held recovery secret; do not blindly copy `/etc/shadow` or `/etc/passwd`. Test login before finishing recovery. |
| `/etc` managed policy, mounts, locale, keyboard, hostname | Rebuild managed policy from release; restore only allowlisted owner preferences. Regenerate mounts from verified AresOS UUIDs; never import Windows mounts. |
| `/var/lib` AresOS migration/launch journals and app catalogue overrides | Schema-versioned encrypted checkpoint; reconcile with live processes before replay. Restore overrides selectively; stale in-flight launch records cannot spawn duplicates. |
| Bluetooth pairing, printer setup | Reprovision/pair explicitly; document loss of pairings. These do not gate basic offline recovery. |
| Machine ID and SSH host identity if SSH is later enabled | Regenerate on replacement installation; explain any changed host fingerprint. SSH is not a recovery prerequisite. |
| Prism/Microsoft tokens and private registry credentials | Reauthenticate/reissue; excluded from world backups. Offline prepared profile is tested separately, never reconstructed by editing tokens. |
| Backup location/password/backend and second-factor access; disk-unlock recovery | Independent recovery kit/password manager accessible without AresOS; secrets never in Git. Test access with the original SSD absent. |
| ESP/boot files and firmware state | Repair only the identified AresOS ESP from the kit; preserve Windows ESP/entry. Record Secure Boot off and Linux entry/order; no MOK or automatic trust reconfiguration. |

**Proposal:** rehearse (1) unusable root with intact home subvolume and (2) damaged AresOS ESP independently, offline, using file-backed test disks. Preserve home or explicitly restore its backup, restore selected machine state, and verify NVIDIA rendering, Wi-Fi, recovery login, player identity and world access. Require unchanged protected Windows partition hashes/boundaries and no unexpected boot-entry/order changes; repeat the appropriate hardware checks without deliberately damaging either real SSD. Ubuntu fallback must meet the same contract, not a kernel-only recovery claim.

## Appendix B — Mod, session and lifecycle contracts

### B1. Mod and OS interface v1 and package-01 migration

**Proposal:** keep a small platform adapter in the mod. Windows uses local implementations; AresOS Linux requires the OS helper. The Linux mod never falls back to executing `command` when the helper is missing or incompatible. Standalone Linux development can explicitly select the legacy direct adapter, but that mode is never enabled in the AresOS image.

| Responsibility | Windows | AresOS Linux |
|---|---|---|
| App catalogue/launch definition | Existing `config/aresos/apps.json`; `command` argv launched directly by the Windows adapter | Helper registry: stable ID, default display name, argv/desktop entry, allowed environment/GPU policy, working directory, single/multi-window identity and lifecycle class |
| Name, item `look`, `pinned`, saved item/door IDs | Mod-owned | Mod-owned appearance and owner name override; helper supplies a fallback name, availability and status |
| Launch and return | Local adapter and existing per-launch focus token; no claim of new Windows window-management support | Helper owns real window association, activation/close tracking, independent app scope and GPU environment |
| Desktop rules, world save, hub, Iris | Mod, gated by desktop world marker | Same mod; guardian requests named save/stop operations, never writes Minecraft world files itself |
| OS shutdown/update | Not an app launch; unsupported by the Windows development adapter | Named system-coordinator request after safety checks; Java never runs as root |

**Wire contract `aresos-shell/1.1` (backward compatible with 1.0):** local newline-delimited JSON on a private Unix socket under `$XDG_RUNTIME_DIR/aresos/`. Same-user peer validation, launch nonce and instance ID bind a connection to the supervised desktop. This is a local session protocol, not a security boundary against all programs of the same user. Root operations use separately authorized named methods, never caller-provided commands/paths/environment.

| Message | Required input/output and behavior |
|---|---|
| `hello` | Client sends protocol major/minor, capabilities, desktop instance and launch nonce. Reply selects major 1 and supported minor/capabilities or `incompatible_version`; required missing capabilities block launch. Unknown optional fields are ignored, unknown operations rejected. |
| `list_apps` | Reply returns catalogue revision and `{id, name, available, reason}` entries. No commands or GPU environment are sent to Minecraft. |
| `open_app` | Request `{request_id, app_id}`; reply `{request_id, launch_id, state}` with `starting`, `focused` or `failed`, plus a stable error such as `unknown_app`, `unavailable`, `launch_failed`. Async updates use the same IDs. |
| `app_state`, `shell_focus` | Helper reports launch/window transitions and `foreground`/`background`. Mod releases/captures pointer and clears held input on the corresponding transition. Closing a background app never emits a shell-focus request. |
| `world_ready`, `heartbeat` | Mod reports instance, world marker/identity and launch nonce. Readiness requires loaded world and usable input, not just a launcher PID. |
| `request_power` | Mod requests `shutdown` or later qualified `sleep`; system coordinator owns cancellation, app checkpoint and authorization. Normal Save and Quit alone is not OS shutdown intent. |
| `prepare_stop`, `save_complete` | Guardian sends stop ID, launch nonce, reason (`shutdown`, `lid`, `gameplay`, `maintenance`, `critical_battery`) and deadline. Mod replies only after integrated-server clean close; guardian also waits for the real JVM exit and world-lock release. Failure/timeout is never clean success. |

**Proposal:** every envelope includes protocol version and request/event ID. No raw shell-string operation exists. Duplicate `open_app` request IDs return the same result; retain pending/results in the supervisor journal across helper restart, reconcile windows/scopes, and never blindly retry an uncertain launch. A new deliberate click gets a new request ID. Limit message size, reject malformed input and display failure without crashing the game. The guardian exposes the lifecycle subset on a separate authenticated channel so app-helper death cannot remove saving. Windows implements list/open locally behind the same Java interface and preserves its existing focus semantics.

**Installed programs (package 30):** the unprivileged helper merges its reviewed starters with visible, usable desktop entries from the XDG user applications folder, user and system Flatpak exports, then `/usr/local/share/applications` and `/usr/share/applications`. Earlier desktop IDs and hidden overrides win; reviewed IDs and window identities always win. Discovered IDs are stable, sanitized desktop-file IDs. Commands are parsed without a shell and launched in independent user scopes under `app.slice`; terminal entries use an app-specific Foot identity. GPU hints opt into the supervisor's NVIDIA policy when the driver is present. The helper polls folder/file times at most every three seconds (also on list requests), preserves running window/scope transitions across rescans, and normalizes pictures asynchronously in a bounded, network-isolated converter. Discovery scans run off the serving loop within hard bounds (entries looked at, folders, bytes, time); a scan that fails or hits a bound keeps the last good catalogue. Desktop-file and icon links must stay inside their folders or a Flatpak deployment; the converter runs under an address-space ceiling and refuses SVGs that refer to pictures; the icon cache has a budget. Only the normalized PNG cache path leaves the helper.

**Window ownership (package 30, review fixes 1):** a window belongs to a program only by a reviewed identity, never by which programs happen to run: a registry entry's, a discovered program's own candidates (`StartupWMClass`, desktop ID, Flatpak app ID, program file name), or a reviewed hint's. Hints ship in the image as `/usr/share/aresos/apps/hints/<name>.json` (`schema` 1, `desktop_id`, `app_ids` and/or `app_id_prefixes`), are validated as strictly as registry entries, beat discovered guesses and never a registry or desktop identity; hints that could claim the same window are all refused. Shipped: Lunar Client's game window `com.mojang.minecraft`, Steam's games by the prefix `steam_app_`. A window nobody owns is nobody's: it confirms no launch, keeps no program open and forces no return; the hub then gets the focus only when the compositor gives it. With a 1.0 desktop only the registry's identities own windows, as before package 30. Closing the last discovered window returns to the hub after the short hand-over interval even if its scope remains alive, unless a window nobody owns is open or he chose another window or a launch after the compositor's own pick; an early clean process exit may hand over to a resident instance. The three registry apps keep their immediate return.

- **Version.** The helper's minor version becomes 1. `hello` works as today: the reply's `minor` is the lower of the two sides. A 1.1 helper also offers the capabilities `app_details`, `apps_changed` and `list_paging`. The mod requires none of them, so it keeps working with a 1.0 helper (three apps, no pictures, as today).
- **An older mod (1.0) with a 1.1 helper** gets exactly what it gets today: the starter apps with `id`, `name`, `available`, `reason`, in one reply. Programs found through desktop entries are listed and opened only for a client that negotiated 1.1.
- **`list_apps` in 1.1.**
  - The request may carry `"cursor"` (a string of at most 64 characters that the helper handed out; no cursor means the first page).
  - The reply carries `revision`, `apps` (one page, ordered by `id`) and, when more follow, `next` (the cursor for the next page). Every message stays within the 64 KiB limit.
  - The client asks again with `cursor` until a reply has no `next`. If a page's `revision` differs from the first page's, it starts over; after three such starts it keeps the list it had and tries again at the next `apps_changed`.
- **An entry in 1.1** has `id`, `name`, `available`, `reason` as today, and these optional fields. A missing field means "not known"; unknown fields are ignored by both sides.

  | Field | Value |
  |---|---|
  | `source` | where it came from: `image` (a starter from the reviewed list), `system` (`/usr/share/applications`, `/usr/local/share/applications`), `flatpak-system`, `flatpak-user`, `user` (his own folder) |
  | `icon` | absolute path of a PNG with transparency, at least 64 pixels wide (the helper writes 128 x 128), readable by him |
  | `categories` | the entry's categories, at most 16, each `[A-Za-z0-9-]{1,32}` |
  | `generic_name` | at most 64 characters |
  | `keywords` | at most 16, each at most 32 characters |
  | `desktop_id` | the desktop file ID, at most 128 characters |
  | `exec_name` | the base name of the program file that runs; for a Flatpak, its app ID |
  | `terminal` | true when it runs inside the terminal |

  A starter that stands for desktop entries (Chrome for `google-chrome.desktop`) is listed once, as the starter, with `source` `image`, and takes `icon`, `categories`, `generic_name`, `keywords` and `desktop_id` from the first of those entries that is installed.
- **`apps_changed`.** When the list or a picture changes while the helper runs, a client that negotiated 1.1 gets the event `{"event": "apps_changed", "revision": "<new revision>"}` (in the usual envelope). The client then lists again, at most once every two seconds.
- **Never sent to the game:** a command, arguments, an environment, or a path other than `icon`.
- **Example messages.** The mod package commits one example file per message kind under `mod/src/test/resources/shell-1.1/` (a first page with `next`, a last page, an entry with every field, an entry with none, `apps_changed`). The helper package's tests read the same files and check that the helper produces and accepts that shape.


**Proposal — migration:** package 01's fields are `id`, `name`, `command`, `look`, `pinned`, including the default `notepad` ID. Before editing, copy the original file to a versioned backup. Write schema 2 atomically with an explicit `schemaVersion` and app list, retaining all IDs, names, looks and pins; retain Windows argv unchanged. Existing item/door IDs are never renumbered. On Linux, import appearance/pins only: preserve legacy commands in the backup but never execute or automatically translate them. Supply an explicit registry entry with ID `notepad` for the chosen Linux text editor, and a new `minecraft` entry for gameplay. An unknown/custom ID stays visible but unavailable until its OS launch definition is reviewed. Duplicate/invalid IDs stop migration with a diagnostic; never drop entries silently.

**Proposal:** old Windows configs remain readable; schema migration must be idempotent. Downgrading the mod restores the original config with a visible warning about later edits, not a destructive overwrite. An old direct-launch mod is refused by the AresOS image's manifest/handshake gate before the desktop is marked ready. Test the real migrated item → v1 → helper → existing/new app window, one launch per click, old saved IDs, helper absence/restart and incompatible versions. Do not invent a second-theme implementation to pass this gate.

### B2. Supervision and focus

**Proposal:** distinguish SETUP, STARTING, IN_WORLD, APP_FOCUSED, AUTH_REQUIRED, STOPPING, DESKTOP_STOPPED_FOR_GAME and RECOVERY. A wrapper observes actual Java process start/exit; Prism PID exit is not game exit. A per-instance lock spans loading through final exit. Start with a 120-second prepared-start timeout, revised from measurement; auth/download/setup have separate UI states. Missing world or heartbeat never triggers an automatic destructive repair.

**Proposal:** unexpected desktop failures use backoff and stop after either three failures in five minutes OR three consecutive failures, including ready-then-crash cycles four minutes apart. Persist the consecutive count and recovery latch across helper/supervisor restart; reset only after 30 continuous healthy minutes with valid heartbeat or explicit owner Retry. Pressure/OOM, intentional stops, failed saves and auth states suppress automatic restart. A crash during saving leaves an unclean marker and recovery. Greetd/compositor failure enters login/TTY recovery rather than repeated autologin. Service restart support is documented, but these policies require implementation. [S3], [S1]

**Proposal:** the helper tracks active interaction and parent dialogs before closure. Return to Minecraft only when the foreground app's final relevant window closed; background closure preserves focus. A restored desktop waits below a foreground editor/browser. Show launch failure if no matching toplevel appears; a launcher PID or localized window title alone cannot identify the app. Keep ordinary app processes outside the game's resource/lifetime group.

### B3. Power events, app checkpoint and helper failure

**Proposal:** power saving is a first-boot dependency. A system power coordinator starts before the desktop, monitors lid/key events and battery, and communicates directly with a separately supervised game guardian. The app helper handles windows only; the guardian retains the mod connection, save state, JVM identity and instance lock. Losing the helper does not close the guardian's channel. New desktop launch requires both power readiness and guardian readiness.

**Proposal — system defaults, independent of helper inhibitors:** set logind lid handling (ordinary, external-power and docked), power/reboot/suspend/hibernate key handling (including software long-press variants) and idle action to `ignore`; the coordinator explicitly handles the supported events. Mask suspend, hibernate, hybrid-sleep and suspend-then-hibernate targets/services until qualified; remove inherited desktop power agents. Reject ordinary direct logind power requests except from the coordinator through polkit; recovery admin remains an explicit emergency path. These knobs and block/delay inhibitor differences are documented. [Z13], [Z20]

**Proposal:** hold a shutdown block inhibitor while a writable desktop or unresolved app checkpoint exists. Do not begin native shutdown and then hope a five-second delay will save it. Only the coordinator releases the block and calls logind after completion. A separate shutdown ordering guard uses the guardian's save-and-wait routine before stopping the user session, storage or Java, covering an authorized native shutdown path; it is defense in depth, not a cancellable UI once system teardown begins. The initial 120-second stop allowance must exceed measured slow saves; normal coordinator timeout cancels before native shutdown, retaining recovery rather than killing Java. Service stop ordering/timeouts must be tested on the actual image. [S3], [S4]

| Trigger | Proposed action, including app-helper failure |
|---|---|
| Menu shutdown / short power press / reboot | Show “close your apps first” outside Minecraft; list all non-shell windows and active jobs, including gameplay. Ask the owner to save/close them normally and confirm background work is finished. Cancel preserves the desktop, editor document and browser form. After helper failure, freeze new launches and use the recovery screen/TTY; if window enumeration is unavailable, require explicit manual closure/confirmation instead of assuming an empty list. Only then request desktop save/exit, checkpoint and power-off. |
| Lid closed on AC, battery or dock | Guardian cleanly saves/stops the desktop; blank the internal panel without sleep/power-off, preserving other apps. If already loading, finish/abort loading through the mod's safe close path. On lid-open, keep the foreground app or offer one desktop reload to the hub. Gameplay is an ordinary app: show save/quit request on reopening, never forcibly terminate it merely for lid closure. |
| App helper dead | Coordinator uses the guardian's independent lifecycle channel. Saving still works; app closure uses recovery fallback above. A failed helper is never permission to suspend or kill the world. |
| Power coordinator lost | Static defaults prevent automatic key/lid sleep or shutdown. Guardian detects the missing power heartbeat, saves/stops the desktop and disables relaunch until supervision is restored; independently observes battery as a fallback. Recovery terminal remains available. |
| Critical battery | Enter the emergency sequence below even if helper/UI is dead; skip remote transfer, prune and update activation. |

**Proposal — bounded emergency:** choose an early reserve from worst-case measured save time plus shutdown margin. Initial trial values: warn at 15%; initiate save at 10% OR estimated three minutes remaining, whichever occurs first, and immediately on a critical battery signal. Reserve 60 seconds for save/clean exit, up to 30 seconds for app save/closure, then power-off within a 120-second total budget. Repeated events join one operation; AC restoration cancels pending power-off only after the in-flight save finishes. If measured saves exceed the budget, raise the reserve/deadline before allowing battery trials, rather than shortening saving to meet the test.

**Proposal:** UPower's automatic critical action must be neutralized or routed into this coordinator, never a second independent suspend/power-off path. Its API reports the configured action, including `Ignore`; P1 must verify a supported configuration in the selected package and P2 must force the critical event to prove no bypass. [Z14] If that cannot be done, the image fails the gate. The guardian's independent battery check must still save with the app helper absent. Power and maintenance share a transaction lock/journal: critical battery cancels downloads, stops new staging and disarms an unactivated deployment, preserving the known-good boot default. Do not kill a deployment commit halfway through; complete its safe boundary then cancel activation. Since OSTree can finalize staging during shutdown, P4 must prove the selected backend's cancellation path before enabling updates; emergency shutdown must not accidentally activate a pending release. [Z9]

**Proposal:** a responsive world must save cleanly for every supported event, including a save exceeding five seconds with a dead helper. If saving hangs, normal power requests remain cancelled. At an unavoidable emergency deadline, record “unclean”, preserve the last clean backup and perform best-effort shutdown rather than falsely report success; require recovery before reopening the affected world. Exhausted batteries, kernel freezes, detached SSDs and hardware forced power cuts cannot have an unconditional clean-save guarantee. The gate tests the defined single-fault cases; this limitation does not excuse helper-failure bypasses. Other apps' unsaved work cannot be guaranteed at emergency exhaustion, so warn early and never silently describe emergency termination as a normal clean shutdown.

### B4. Normal gameplay and return

**Proposal:** the `minecraft` registry entry has lifecycle class `exclusive_game`. Select/authenticate its separate Prism instance first; cancel setup without stopping the desktop. Then record the transition, obtain desktop save/exit acknowledgement, release its process/GPU resources and lock, and launch gameplay. Maintain a transition journal so supervisor restart reconciles live processes and never starts both inadvertently. Desktop and gameplay have distinct game directories, saves, options/mods, instance locks and window identities, even when using the same legitimate account. Ordinary worlds remain unmarked and get no shell mod; online authentication/server compatibility must be tested, not inferred from offline desktop success.

**Proposal:** focus the real gameplay window, clear the desktop's held inputs and associate child launcher/login dialogs. Alt+Tab and recovery shortcuts work. A game's close/cancel prompt keeps its focus; do not interpret a launcher window closing as gameplay completion. On actual game exit/crash, verify no JVM/world lock remains, clear the exclusive state and launch the desktop once; foreground app focus still wins. Super+Home presents return controls while gameplay runs; after the owner quits safely, the desktop reloads to its hub, with ordinary apps intact. Show loading and recovery if desktop restoration fails; no duplicate or automatic gameplay relaunch.

**Proposal:** Lunar is an optional later launch definition, with its own instance/data and a qualified actual-game tracking path. No claims about Linux/server support or simultaneous account behavior are made here. Its automatic updater, graphics use and clean-close behavior must fit maintenance and lifecycle policy before enabling it. Never inspect or reuse the owner's existing Windows Lunar/Minecraft directories. The first gameplay milestone uses Prism; an unsupported client leaves the app unavailable with a reason.

### B5. Memory, GPU and restart pressure

**Proposal:** use the section-2 budgets and initially 8-chunk render / 5-chunk simulation distance in the desktop. Keep game, ordinary apps, recovery UI/compositor and power/guardian in separate resource groups; configure recovery memory protection through all relevant ancestors. Set an initial 5 GiB desktop / 6 GiB gameplay soft-pressure target, with measured hard limits only after testing clean-save headroom. Systemd documents memory protection/limits and warns that oomd kills selected cgroups; do not make the whole user session a kill unit. [Z21], [Z22]

**Proposal:** qualify a 4 GiB zram swap target, counting its actual RAM cost; any disk-backed overflow must use only AresOS storage. Do not use Windows swap or treat swap as permission for two games. Prefer saving/stopping the desktop under sustained pressure; a killed game is an unclean stop. Suppress relaunch until pressure clears for 60 seconds and the owner retries. No automatic repeated kills/restarts to rescue capacity.

**Proposal:** both games use NVIDIA when running; exclusive mode releases the desktop before allocating gameplay GPU resources. Measure VRAM capacity, resident use and return latency on this unit rather than assuming a GPU-memory size. Two-instance mode stays deferred until a representative browser/call/editor + two-game trial leaves at least 2 GiB measured RAM headroom, at least 20% measured VRAM headroom, responsive recovery and acceptable frametimes/power. Shader disabling and stop/reload remain the fallback. These are proposed acceptance budgets, not measured hardware facts.

### B6. Backups that survive losing the drive

**Proposal:** after confirmed save and writer exit, copy immutable clean staging data, then restic it off-device. Keep seven daily, four weekly and pre-update snapshots; include world, player identity, mod appearance/pins and matching manifest. Gameplay saves get their own post-exit snapshots. An unclean crash copy is labelled and never replaces the last clean copy. Offer a scheduled daily clean desktop restart at an owner-selected idle time for long sessions. Restic provides the backup mechanism; this consistency protocol is ours. [B1]

**Proposal:** keep repository location, decryption password, recoverable backend/second-factor access, restore instructions and manifest independently of both internal SSDs. An independently accessible password manager or secured offline copy is acceptable; credentials encrypted only by a key on AresOS are not. Keep private machine-state backups separate from ordinary world snapshots and omit refresh tokens. Before valuable saves, restore on a fresh file-backed system with the original installation unavailable to that test, using only the independent kit; verify known builds, inventory, UUID, marker and app IDs. Do not disconnect or damage the owner's Windows SSD for this rehearsal. Never substitute a successful backup command for a restore test.

**Proposal:** unavailable remote backup queues clean local staging with visible pending status. A failed local checkpoint blocks maintenance. Ordinary shutdown may offer an explicit saved-but-not-backed-up choice; it never waits indefinitely for network. Emergency battery saving skips backup transfer. Never prune the last proven restore point to fit an update. Restoring an older game requires its pre-conversion world copy; OS rollback alone is not world rollback.

## Appendix C — Own-SSD safety specification

**Binding project requirements, revised 2026-10-22.** Agents never run physical disk/boot tools. The owner guide is [INSTALL](../INSTALL.md); dated external evidence is indexed there and in the [record](../INSTALL-RECORD.md#sources-and-limits). These requirements do not claim a qualified installation.

1. **Micron is outside the write boundary.** No partition/format/resize/mount/swap/boot-file operation from Linux, its installer, rebase, repair or undo may touch it. Normal Windows use and ordinary record files are not covered by a false byte-identical-runtime promise. There are no owner C: shrink/extension exceptions on this route.
2. **Prepare independent recovery.** Verified off-device file backups, two distinct labelled sticks, successful preserved Windows recovery boot, fully decrypted C:, Secure Boot off, hibernation/Fast Startup disabled. Unknown/encrypted status stops for a separate owner plan and independently saved matching recovery key. No TPM/key/storage-mode change or automatic encryption disablement.
3. **Fit according to the exact model manual.** Shut down/unplug, ESD protection, deco cover then lower case, disconnect battery cable, 2280 fixing/thermal arrangement confirmed, correct screws, reconnect and close. Stop for occupied slot, missing parts, damage or resistance; do not disturb Micron. Firmware must list both drives before installation. The actual storage-information screen remains to qualify.
4. **Record and identify.** Preserve the original Windows model/serial/disk GUID, every partition GUID/type/boundary and active Windows boot target. The pure record comparison allows renumbering/free-space changes, not geometry/identity changes. Match Crucial's physical serial before first install; it must have no partitions. After install save its GPT/partition GUIDs and Linux boot target independently. Disk numbers/labels/size/filesystem UUID are not replacements for identity. Missing/ambiguous information stops the sequence.
5. **Select only Crucial.** Current official live ISO with whole-drive automatic storage; review every row and new `/boot/efi` on Crucial before the final write. No Windows EFI reuse or Micron row, regardless of reassuring installer wording. ISO-provided sizes/subvolumes must be qualified with brief 06. A failure does not authorise a legacy/manual/shared-ESP fallback.
6. **Boot and rebase.** Permit a separate Linux NVRAM entry/order change; preserve Windows entry/files. F12 (or Fn+F12) direct Windows remains available. Linux-first is required through initial offline stock setup; restore Windows-first in the step 4 tools round trip and complete step 5's unattended Windows/original-ESP proof before authentication/switch. Keep Windows-first afterward. No MOK, BCD repair, raw CI disk flashing or physical bootc whole-disk command. Rebase must retain authenticated recovery administration and a known-good deployment without repartitioning. Runtime must deny Windows mounts/unlocks and suppress its volumes in the shell; privileged code still needs the same boundary.
7. **Prove actual writes in disposable VMs.** Two independent file-backed disks, protected Windows-like GPT/EFI/MSR/NTFS/recovery layout, near-equal sizes, swapped enumeration and ambiguous/wrong-target cases. Compare complete protected-disk hashes offline before/after install, rebase, rollback, repair and undo; compare GUIDs/boundaries and audit EFI fallback files. Verify Windows boots with Linux disk absent. No physical passthrough or breaking the owner's disks. BootCurrent-unavailable and Windows-on-Crucial fixtures must refuse undo. Real helper/USB/firmware and novice trials remain distinct from synthetic tests.
8. **Recovery only on Crucial.** Preserve home during selective repair; formatting its Btrfs parent destroys data. Unqualified repair requires independent backup restore, not Windows storage. Before any update, retain the complete recovery set specified in A2.
9. **Undo proves independence first.** A fresh direct Windows boot must target the original Micron ESP GUID/bounds and Microsoft loader, not merely show a Windows-looking name. Default undo restores Windows as default, checks an unattended restart and leaves Crucial/data in place. Optional removal/erasure requires exported Linux data and fresh Windows checks; a changed/unreadable target stops both. Before live erasure, re-resolve both disks by serial/GUID, require all recorded Crucial partitions disposable and unmounted, and match the saved Windows entry again. Only Crucial's partition table may be cleared; GParted's Create Partition Table dialog writes on Apply immediately. Alternatively remove only Crucial with the fitting precautions, including the battery-damage stops. Verify Windows again; no C: expansion or Windows boot-file edits. Keep stale Linux entries until separately reviewed.

**Fallback boundary:** the [preserved same-drive guide](../INSTALL-SAME-DRIVE.md) and [record](../INSTALL-RECORD-SAME-DRIVE.md) are historical proposals with their own unfinished gates. They require a new owner decision and explicit exception to the current no-Windows-resize rule. A missing SSD or failed check is not that decision.

## Appendix D — Acceptance trials, not executed results

**Acceptance requirements; current results live only in the [status table](../INSTALL-STATUS.md#current-gates).** Save logs/screenshots in each implementing package's review folder, redact secrets, and distinguish VM evidence from hardware evidence. Fabric tests exercise the mod; session tests must exercise the actual mod/helper path too.

| Gate | Trial | Pass condition |
|---|---|---|
| P1 image | Resolve RTX-family discrepancy, pin digest/locks, inspect signatures/inventory, build/boot twice | Exact image/backend; our session/power policy only; authenticated recovery; no placeholder pins. VM results are not Lenovo evidence. |
| Before P1a: install/rebase | Two separate file-backed disks with Windows-like partitions and empty Linux target, near-equal capacities, reversed enumeration; novice automatic-install walkthrough; stock Bazzite→AresOS and rollback | Only Linux disk/ESP writes and recorded Linux entry/order change; whole protected-disk offline hash and layout unchanged; account/UID reconciliation proven. |
| Before P1a: media/undo checks | Exact Fedora Media Writer workflow with both ISOs; UEFI boots; Windows boot from original ESP versus AresOS ESP; unavailable BootCurrent | Separate recovery media preserved; all inventory commands work; only original-ESP/Microsoft-path case passes the deletion gate. Source review and synthetic helper tests are not physical-media/VM evidence. |
| P1a early hardware | Official USB install→reviewed rebase→plain labwc/terminal; NVIDIA, panel, Wi-Fi, audible sound, keyboard/touchpad, TTY; Windows return | `nvidia-smi` lists RTX 4060; all controls work; direct Windows boot with USB absent/present, original layout/boot files intact. AC only, no Minecraft or suspend. |
| P2 interface (finding 7) | Existing package-01 config and saved items through mod→v1→helper→editor; repeat click, restart helper, reject wrong major | Stable `notepad` ID/pins/look/name, no direct Linux launch or duplicate uncertain retry; actionable incompatibility. |
| P2 focus (10) | Continuous browser typing while background terminal closes; then foreground close, dialogs, Alt+Tab, held keys | No focus theft or stuck input; foreground final close returns to world. |
| P2 crash (9) | Fast failures and ready-then-crash every four minutes; restart supervisor during sequence | Finite persistent recovery after three consecutive failures; no ready-event reset or lost latch. |
| P2 normal shutdown (3) | Unsaved editor and browser form; Cancel, then safe completion; helper dead too | Cancel preserves both and usable world. No OS power-off until manual app closure/confirmation and clean desktop save. |
| P2 power (2) | Inject lid, key and critical battery during loading, >5-second saving and maintenance; kill helper and separately coordinator | No unqualified sleep; guardian save succeeds within measured budget; no early Java termination, emergency update activation or network-backup wait. Reopen world and verify new edits. |
| P2 backup (1) | Alter world, back it up, restore on a fresh file-backed system unable to access the original installation | Known builds, player inventory/UUID, desktop marker and app IDs restored using independent credentials and matching manifest. |
| P2 setup | Missing data/world/assets, offline, expired/revoked account and clock skew | Visible setup/recovery, same identity when offline is supported, no new empty world or restart loop. |
| P2/P5 pressure (8) | Browser tabs/call/editor + desktop, then gameplay; controlled memory pressure | Responsive recovery, ordinary app work intact, explicit unclean/OOM status if injected, no relaunch loop. Record whole-system RAM/swap/VRAM. |
| P3 hardware (6, 11) | F12→Nether on NVIDIA→open/close app→save/shutdown→direct Windows, USB present/absent | Correct actual renderer, clean saved changes, Windows-first order and intact Windows ESP, no recovery prompt; repeat altered-world restore. |
| Before any update (4) | Offline previous-deployment boot; in file-backed VMs separately break root and AresOS ESP and recover with independent media | Complete matching OS/driver set and state restored; protected partition bytes/boundaries and recorded boot policy preserved. Real hardware confirms renderer, Wi-Fi and recovery login without destructive fault injection. |
| P4 maintenance (5) | Fresh B vs used A→B; removed package, renamed service, config migration; trigger inherited timers/manual updater UI outside maintenance | Equal managed inventory/services/config; no unmanaged mutation/staged deployment; rollback restores compatible state. |
| P5 gameplay | Separate normal survival/multiplayer instance, failed launch, crash, cancelled close, restart supervisor mid-transition | Normal rules, no desktop mod/items/marker leakage, one game by default, preserved saves, correct focus and one desktop return. Lunar separately gated. |
| P5 daily comfort (13) | Same browser workload with world stopped/hidden/visible, AC/battery, idle and charger changes; ten cold boots | Owner-accepted measured power/heat/noise and return-time limits recorded; otherwise retain save/stop fallback. |
| P7 suspend (12) | Chosen retain/relaunch policy; sleep away from hub and with browser foreground; twenty AC/battery/display cycles | Defined position/focus restored, no duplicate game, measured acceptable wake-to-input, no black screen/corrupt save. Until then sleep remains disabled. |

## Appendix E — Phase 2 packages in build order

**Proposal:** these are planning gates, not authority for agents to install. The short path is **P1 → reviewed install/rebase handoff → P1a → P2 → P3**. P1a is the new hardware first boot immediately after the image package; it does not wait for Minecraft. The release handoff is part of making P1 installable, not a new large feature milestone.

| Order | Package and exit condition |
|---|---|
| P1 | **Minimal image (package 03) and installable handoff.** Pin a qualified NVIDIA base, locked Containerfile build, bootc backend, labwc/terminal, updater exclusions and safe power defaults; measure CI cost. Before hardware: owner-approved image delivery, qualified current live ISO/checksum, two-disk/Crucial-only EFI VM rehearsal, tested stock-Bazzite rebase/rollback and account/recovery provisioning. See the current table for the retained handoff evidence and remaining gates. |
| P1a | **Early hardware first boot, no Minecraft.** Owner backs up, checks encryption/hibernation, fits the dedicated Crucial SSD, installs Bazzite only there and rebases per [INSTALL.md](../INSTALL.md). On AC, boot labwc/foot; test `nvidia-smi`, screen, Wi-Fi, audible sound, German keyboard, touchpad and authenticated recovery. Reboot once, then direct Windows with USB present/absent. A failure blocks P2 hardware rollout; do not wait until the Nether exists to find driver/network failures. |
| P2 | **Minecraft milestone.** Add native Prism, exact marked world, interface v1 with one migrated app, guardian/clean shutdown and independently credentialed backup/restore. Include the small Nether hub/spawn dependency; pass power/helper-failure and app-cancel tests before the full hardware trial. |
| P3 | **Full hardware trial.** F12→controllable Nether hub on NVIDIA→open/close one app→clean save/shutdown→normal Windows, USB present/absent. Restore a deliberately changed world. No enrollment. On qualification failure investigate and evaluate Ubuntu before more base-specific investment. |
| P4 | **Controlled releases and offline recovery.** Finish/test complete previous deployment, independent recovery media, broken-root/ESP repair and state restoration before enabling any update. Then add signed release deployment, A→B convergence and security maintenance automation; the prototype used only the same controlled manual procedure when its recovery gates were already met. |
| P5 | **Gameplay and daily use.** Add exclusive normal-Minecraft app and return, broader peripherals/portals/audio, representative study workload and resource/comfort measurements; optional Lunar and simultaneous games require their own qualification. |
| P6 | **Presentation and controls.** Original Plymouth/loading polish, local-only artwork input, Bluetooth pairing polish, in-game settings and optional updater UI. Keep existing recovery paths. |
| P7 | **Suspend, only if qualified.** Choose retain-process or stop/relaunch, define resume/focus/position behavior and acceptable latency, then pass repeated hardware trials before exposing Sleep/lid suspend. Hibernate remains separate. |
| Later, optional | **Shops/themes** remain separate packages. The second SSD is now the primary route prerequisite, not a later migration. |

**Proposal:** P1–P3 use disposable Linux data and no automatic updates; Windows data is never disposable. Any manual update still requires A2's recovery contract; otherwise remain on the known-good system or return to Windows. Rebuilding or resizing the Windows SSD is not a fallback. The maintainer reviews advisories from P1 onward. P1a does not qualify battery, sleep, Minecraft or daily use, and does not wait for their implementation.

## Appendix F — Evidence index and remaining uncertainty

**Own-SSD revision, checked 2026-10-22:** [INSTALL source index](../INSTALL-REFERENCE.md#dated-sources-and-limits) covers the Lenovo HMM/PSREF, current Bazzite installer/screenshots, Windows preparation, writer and GParted. [Record sources](../INSTALL-RECORD.md#sources-and-limits) cover read-only identity/firmware queries. Use the [current table](../INSTALL-STATUS.md#current-gates) for slot/thermal/firmware/media/handoff status; this inherited source index is not a current qualification summary.

**Inherited research:** the sources below retain their **2026-10-21** checks. U1–T1 retain brief 02's research evidence in its [report](../../reviews/02-os-base-design/REPORT.md); Z1–Z22 were read for brief 02b. The DB/DW/DG/DP/DR/DU sources below were read for brief 05. Documentation is evidence of upstream capability, not a qualified AresOS package. “Latest” documentation does not establish availability in our pinned image.

| Brief 05 source, checked 2026-10-21 | Evidence used |
|---|---|
| [DB1 — Current Bazzite installer][DB1] / [DB3 — Legacy installer][DB3] | Manual-partitioning legacy ISO route; no MOK when Secure Boot is off. |
| [DB2 — Same-drive dual boot][DB2] / [DB5 — Manual partitioning][DB5] | Windows preparation; new EFI/boot/Btrfs layout and optional GRUB Windows selection. |
| [DB4 — Bazzite FAQ][DB4] | RTX cards assigned to `bazzite-nvidia-open`; conflicts with package 03's pinned family. |
| [DW1 — Encryption status][DW1] / [DW2 — Powercfg][DW2] / [DW6 — Fast Startup][DW6] | Fully decrypted versus suspended protection; hibernation/fast-start preparation. |
| [DW3 — Shrink][DW3] / [DW4 — Extend][DW4] / [DW5 — Partition inventory][DW5] | Owner Windows operations, exact boundaries and adjacency needed for undo. |
| [DG1 — Packages billing][DG1] / [DG2 — Container registry][DG2] | General quota versus current free container-image exception, visibility/authentication. |
| [DG3 — Releases][DG3] | Under-2-GiB asset limit; unsuitable as a direct OCI registry. |
| [DP1 — Podman build][DP1] / [DR2 — Local bootc image transport][DR2] | Local-build alternative; capability, not an AresOS migration test. |
| [DR1 — Bazzite rebase][DR1] | rpm-ostree recipe and desktop-change caveat. |
| [DU1 — GParted manual][DU1] | Review queued deletion of only positively identified new Linux partitions. |

**Repository evidence:** package 03 was read from Git objects, without accessing its worktree, at [commit 7ae41a7](https://github.com/carlsenares/AresOS/tree/7ae41a73c7e01f871b6426a34903cde13519d110/os). Its README, Containerfile, base manifest, build script, workflow and guest checks support section 8's implementation claims. CI/hardware success is not inferred from source code.

| Revision source, checked 2026-10-21 | Evidence used |
|---|---|
| [Z1 — Bazzite upstream README][Z1] | Concrete desktop NVIDIA image family; inherited updater and desktop stack. |
| [Z2 — Custom Bazzite images][Z2] | Supported derivation route and other window-manager customization. |
| [Z3 — Universal Blue image template][Z3] | Containerfile base selection, GitHub Actions, image signing and bootc-oriented template. |
| [Z4 — Bazzite rollback][Z4] | Manual previous-deployment selection and pinning; personal state is not OS rollback. |
| [Z5 — Bazzite Secure Boot][Z5] | Installation-time MOK enrollment; distinct post-install procedure toggles Secure Boot. |
| [Z6 — Bazzite updates][Z6] | Desktop automatic update policy and manual entry points. |
| [Z7 — uupd upstream][Z7] | OS/app updater scope, timer integration and rpm-ostreed automatic-policy note. |
| [Z8 — Ubuntu automatic updates][Z8] | Package timer/install controls for fallback comparison. |
| [Z9 — OSTree deployments][Z9] | Complete deployment structure, shared `/var`, merged `/etc`, staged finalization. |
| [Z10 — shim MOK variables][Z10] / [Z11 — shim TPM measurements][Z11] | Persistent MOK state and PCR measurements; not a Lenovo/BitLocker test. |
| [Z12 — Microsoft BitLocker configuration][Z12] | Platform validation policy/PCR dependence; actual owner policy unknown. |
| [Z13 — logind configuration][Z13] / [Z20 — inhibitor modes][Z20] | Lid/key defaults, ignore policy, bounded delay versus blocking. |
| [Z14 — UPower interface][Z14] | Battery/lid status and reported critical action; selected package configuration still a gate. |
| [Z15 — restic repository preparation][Z15] | Password and backend access required for recovery. |
| [Z16 — uupd timer][Z16] / [Z17 — service][Z17] / [Z18 — manual service][Z18] | Concrete inherited update entry points to exclude. |
| [Z19 — NetworkManager keyfiles][Z19] | System connection locations, credentials and permission requirements. |
| [Z21 — systemd resource control][Z21] / [Z22 — oomd][Z22] | Memory protection through ancestors, pressure/limit controls and cgroup kill scope. |

The remaining entries document inherited research, also checked on **2026-10-21** during brief 02:

| Link | Evidence used |
|---|---|
| [U1 — Ubuntu lifecycle][U1] | 26.04 LTS release/support listing. |
| [U2 — Ubuntu NVIDIA installation][U2] | Prebuilt signed modules versus DKMS; matching kernel ABI. |
| [U3 — Subiquity reference][U3] | Install recipe, storage serial selection and early/late commands. |
| [U4 — Ubuntu snapshots][U4] | Dated archive contents. |
| [U5 — Ubuntu Secure Boot][U5] | shim/kernel/module trust and MOK. |
| [U6 — Curtin configuration][U6] | Boot targets, NVRAM defaults and OS probing. |
| [D1 — NixOS manual][D1] / [D2 — Lanzaboote setup][D2] | Images/generations; documented firmware-key enrollment. |
| [D3 — Arch Secure Boot][D3] / [D5 — Debian Live manual][D5] | Arch media limitation; live-build customization. |
| [D4 — bootc introduction][D4] | Transactional image updates; use upstream because Fedora docs were blocked. |
| [G1 — Actions billing][G1] / [G2 — runners][G2] | Private-repository quotas and hardware limits. |
| [G3 — Releases][G3] / [G4 — asset API][G4] | Asset limits and private read authentication. |
| [W1 — WSL comparison][W1] / [W2 — Docker Windows backend][W2] | Build environments on Windows. |
| [N1 — PRIME][N1] / [N2 — open modules][N2] | Offload variables; matched driver components. |
| [N3 — runtime power][N3] / [N4 — suspend][N4] | Workload/platform limitations and VRAM preservation. These versioned examples do not pin our driver. |
| [L1 — labwc][L1] / [L2 — actions][L2] / [L3 — configuration][L3] / [L4 — integration][L4] | Stacking, Xwayland, window controls and toplevel protocol. |
| [C1 — cage][C1] / [C2 — sway][C2] / [C3 — gamescope][C3] | Upstream scope of compositor alternatives. |
| [P1 — Prism CLI][P1] / [P2 — 11.0.3 CLI source][P2] | Wiki documents core CLI; source confirms world/offline flags. |
| [P3 — hooks][P3] / [P4 — login source][P4] / [P5 — refresh source][P5] | Game lifecycle integration and account handling. |
| [P6 — Java setup][P6] / [P7 — Prism 11.0.3 notes][P7] | Linux package differences and offline/auth fixes. |
| [M1 — Mojang 26.2 metadata][M1] / [M2 — Quick Play][M2] | Metadata read as JSON: Java major 25; Quick Play world-folder semantics. |
| [M3 — Minecraft 26.2 release notes][M3] | Experimental Vulkan and selectable graphics backend. |
| [S1 — greetd][S1] / [S2 — Plymouth][S2] | Auto-login lifecycle and boot splash interface. |
| [S3 — systemd services][S3] / [S4 — logind][S4] | Restart supervision and power/session interfaces. |
| [E1 — NetworkManager][E1] / [E2 — WirePlumber][E2] / [E3 — BlueZ][E3] | Network, audio and Bluetooth fallbacks. |
| [E4 — brightnessctl][E4] / [E5 — UPower][E5] | Brightness and power status interfaces. |
| [E6 — Dunst][E6] / [E7 — Thunar][E7] / [B1 — restic][B1] | Notifications, files and backup facilities. |
| [H1 — Lenovo specifications][H1] / [H2 — Lenovo boot selection][H2] | Model-family slots and F12; not this unit's configuration. |
| [MS1 — BitLocker FAQ][MS1] / [MS2 — countermeasures][MS2] | Recovery triggers; reason no zero-prompt guarantee is offered. |
| [T1 — QEMU introduction][T1] | WHPX/TCG, virtual machine/device model. |

**Historical research limits (2026-10-21/22):** the original design-only run did not inspect disks, download/boot an image or qualify the laptop. Its source catalogue records capability, not current acceptance; the Fedora installation page was access-blocked. Later release/ISO/VM results and all remaining limits are recorded only in the [current table](../INSTALL-STATUS.md#current-gates) and its linked reports. Owner-reported inputs and proposed contracts above remain distinct from measured hardware evidence.

[U1]: https://ubuntu.com/about/release-cycle
[U2]: https://ubuntu.com/server/docs/how-to/graphics/install-nvidia-drivers/
[U3]: https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html
[U4]: https://snapshot.ubuntu.com/
[U5]: https://documentation.ubuntu.com/security/security-features/platform-protections/secure-boot/
[U6]: https://curtin.readthedocs.io/en/latest/topics/config.html
[D1]: https://nixos.org/manual/nixos/unstable/
[D2]: https://github.com/nix-community/lanzaboote/blob/master/docs/getting-started/enable-secure-boot.md
[D3]: https://wiki.archlinux.org/title/Unified_Extensible_Firmware_Interface/Secure_Boot
[D4]: https://bootc.dev/bootc/
[D5]: https://live-team.pages.debian.net/live-manual/html/live-manual/customization-overview.en.html
[G1]: https://docs.github.com/en/billing/concepts/product-billing/github-actions
[G2]: https://docs.github.com/en/actions/reference/runners/github-hosted-runners
[G3]: https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
[G4]: https://docs.github.com/en/rest/releases/assets?apiVersion=2022-11-28
[W1]: https://learn.microsoft.com/en-au/windows/wsl/compare-versions
[W2]: https://docs.docker.com/desktop/setup/install/windows-install/
[N1]: https://download.nvidia.com/XFree86/Linux-x86_64/580.95.05/README/primerenderoffload.html
[N2]: https://github.com/NVIDIA/open-gpu-kernel-modules
[N3]: https://download.nvidia.com/XFree86/Linux-x86_64/580.95.05/README/dynamicpowermanagement.html
[N4]: https://download.nvidia.com/XFree86/Linux-x86_64/570.124.04/README/powermanagement.html
[L1]: https://labwc.github.io/
[L2]: https://labwc.github.io/labwc-actions.5.html
[L3]: https://labwc.github.io/labwc-config.5.html
[L4]: https://labwc.github.io/integration.html
[C1]: https://raw.githubusercontent.com/cage-kiosk/cage/master/README.md
[C2]: https://raw.githubusercontent.com/swaywm/sway/master/README.md
[C3]: https://raw.githubusercontent.com/ValveSoftware/gamescope/master/README.md
[P1]: https://prismlauncher.org/wiki/getting-started/command-line-interface/
[P2]: https://raw.githubusercontent.com/PrismLauncher/PrismLauncher/11.0.3/launcher/Application.cpp
[P3]: https://prismlauncher.org/wiki/help-pages/custom-commands/
[P4]: https://raw.githubusercontent.com/PrismLauncher/PrismLauncher/11.0.3/launcher/minecraft/auth/steps/MSADeviceCodeStep.cpp
[P5]: https://raw.githubusercontent.com/PrismLauncher/PrismLauncher/11.0.3/launcher/minecraft/auth/steps/MSAStep.cpp
[P6]: https://prismlauncher.org/wiki/getting-started/installing-java/
[P7]: https://prismlauncher.org/news/release-11.0.3/
[M1]: https://piston-meta.mojang.com/v1/packages/bdfd9856166b7171857c491f15479762f3abda99/26.2.json
[M2]: https://www.minecraft.net/en-us/article/minecraft-snapshot-23w14a
[M3]: https://www.minecraft.net/en-us/article/minecraft-java-edition-26-2
[S1]: https://manpages.debian.org/trixie/greetd/greetd.5.en.html
[S2]: https://manpages.debian.org/trixie/plymouth/plymouth.1.en.html
[S3]: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
[S4]: https://www.freedesktop.org/software/systemd/man/latest/org.freedesktop.login1.html
[E1]: https://networkmanager.dev/docs/api/latest/nmcli.html
[E2]: https://pipewire.pages.freedesktop.org/wireplumber/man/wpctl.html
[E3]: https://manpages.debian.org/trixie/bluez/bluetoothctl.1.en.html
[E4]: https://github.com/Hummer12007/brightnessctl
[E5]: https://upower.freedesktop.org/docs/
[E6]: https://dunst-project.org/documentation/
[E7]: https://docs.xfce.org/xfce/thunar/start
[B1]: https://restic.readthedocs.io/en/stable/040_backup.html
[H1]: https://psref.lenovo.com/Product/LOQ_15IRH8?tab=spec
[H2]: https://support.lenovo.com/ee/en/solutions/YTV104507
[MS1]: https://learn.microsoft.com/en-us/windows/security/information-protection/bitlocker/bitlocker-key-management-faq
[MS2]: https://learn.microsoft.com/en-gb/windows/security/operating-system-security/data-protection/bitlocker/countermeasures
[T1]: https://www.qemu.org/docs/master/system/introduction.html

[Z1]: https://raw.githubusercontent.com/ublue-os/bazzite/main/README.md
[Z2]: https://docs.bazzite.gg/Advanced/creating_custom_image/
[Z3]: https://raw.githubusercontent.com/ublue-os/image-template/main/README.md
[Z4]: https://docs.bazzite.gg/Installing_and_Managing_Software/Updates_Rollbacks_and_Rebasing/rolling_back_system_updates/
[Z5]: https://docs.bazzite.gg/General/Installation_Guide/secure_boot/
[Z6]: https://docs.bazzite.gg/Installing_and_Managing_Software/Updates_Rollbacks_and_Rebasing/updating_guide/
[Z7]: https://github.com/ublue-os/uupd
[Z8]: https://ubuntu.com/server/docs/how-to/software/automatic-updates/
[Z9]: https://ostreedev.github.io/ostree/deployment/
[Z10]: https://raw.githubusercontent.com/rhboot/shim/main/MokVars.txt
[Z11]: https://raw.githubusercontent.com/rhboot/shim/main/README.tpm
[Z12]: https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/configure
[Z13]: https://www.freedesktop.org/software/systemd/man/latest/logind.conf.html
[Z14]: https://upower.freedesktop.org/docs/UPower.html
[Z15]: https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html
[Z16]: https://raw.githubusercontent.com/ublue-os/uupd/main/uupd.timer
[Z17]: https://raw.githubusercontent.com/ublue-os/uupd/main/uupd.service
[Z18]: https://raw.githubusercontent.com/ublue-os/uupd/main/uupd-manual.service
[Z19]: https://networkmanager.dev/docs/api/latest/nm-settings-keyfile.html
[Z20]: https://www.freedesktop.org/software/systemd/man/latest/systemd-inhibit.html
[Z21]: https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html
[Z22]: https://www.freedesktop.org/software/systemd/man/latest/systemd-oomd.service.html

[DB1]: https://docs.bazzite.gg/General/Installation_Guide/install-guide/
[DB2]: https://docs.bazzite.gg/General/Installation_Guide/dual_boot_setup_guide/
[DB3]: https://docs.bazzite.gg/General/Installation_Guide/legacy-install/
[DB4]: https://docs.bazzite.gg/General/FAQ/
[DB5]: https://docs.bazzite.gg/General/Installation_Guide/manual_partitioning/
[DW1]: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/manage-bde-status
[DW2]: https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options
[DW3]: https://learn.microsoft.com/en-us/windows-server/storage/disk-management/shrink-a-basic-volume
[DW4]: https://learn.microsoft.com/en-us/windows-server/storage/disk-management/extend-a-basic-volume
[DW5]: https://learn.microsoft.com/en-us/powershell/module/storage/get-partition
[DW6]: https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/distinguishing-fast-startup-from-wake-from-hibernation
[DG1]: https://docs.github.com/en/billing/concepts/product-billing/github-packages
[DG2]: https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
[DG3]: https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
[DP1]: https://docs.podman.io/en/latest/markdown/podman-build.1.html
[DR1]: https://docs.bazzite.gg/Installing_and_Managing_Software/Updates_Rollbacks_and_Rebasing/rebase_guide/
[DR2]: https://developers.redhat.com/articles/2025/08/13/deploy-image-mode-update-offline-and-air-gapped-environments
[DU1]: https://gparted.org/display-doc.php?name=help-manual
