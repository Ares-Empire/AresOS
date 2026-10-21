# AresOS: OS base decision

AresOS will start in your Nether home, with your apps in the world.\
The home is a desktop: you cannot die, and it need not be a playable survival game.\
Normal Minecraft opens as an app, with its own worlds, servers and normal rules.\
On this laptop, the desktop saves and closes while you play, then returns afterwards.\
Bazzite is the chosen foundation; Ubuntu is the fallback if the laptop trials fail.\
Installation includes one security approval at startup, as you have agreed.\
AresOS lives on its own drive; Windows stays the normal startup choice.\
Before shutting down, it asks you to finish work in your other apps and saves the world.\
Backups, their recovery information and a repair USB must survive losing the AresOS drive.\
Graphics, Windows return, battery comfort and sleep still need real laptop tests.

Revised 2026-10-21 for [brief 02b](../../briefs/02b-os-base-revision.md), following [brief 02](../../briefs/02-os-base-design.md) and the [council verdict](../../reviews/councils/2026-10-21-os-base/VERDICT.md). The [13-finding change map](../../reviews/councils/2026-10-21-os-base/CHANGES.md) is the chair's review path. Read through section 10 and the risks; implementation details and package gates are in appendices.

**Evidence convention:** **Verified** means primary documentation/source was read, not that AresOS works. **Assumed** means unmeasured, inferred or supplied by the project. **Proposal** means a future design requirement, not an implemented capability. These labels cover the paragraph/table they introduce. Every external reference has a **2026-10-21** check date in Appendix F; inherited research is distinguished from this revision's checks. This document authorizes no installation.

**Assumed inputs:** the LOQ's i5-13500H, RTX 4060, Intel graphics and 16 GB RAM come from [AGENTS.md](../../AGENTS.md). Disk serials, BitLocker policy, firmware trust, GPU wiring and spare-slot occupancy remain unknown. No local machine inspection was performed.

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

**Decided in brief 02b:** Bazzite, one-time installation MOK enrollment, Ubuntu fallback, and a desktop world separate from normal gameplay. These supersede the earlier Ubuntu recommendation and README's playable-survival-desktop idea; the frozen briefs and README are not rewritten here.

**Proposal — remaining choices before their gates:** use an external SSD first; accept initial network/account setup and a plain recovery menu. Before personal use, choose disk encryption versus unattended boot, an independent backup destination, and acceptable power/noise limits. Suspend stays unavailable until qualified. These do not block a disposable first-boot prototype.

## 1. Base and OS as code

**Verified:** Bazzite publishes `ghcr.io/ublue-os/bazzite-nvidia:stable`, documents custom images including other window managers, and offers previous-deployment recovery. [Z1], [Z2], [Z4] **Proposal:** use that concrete desktop NVIDIA family, resolving its release to an immutable digest during P1. No digest is invented or presented as qualified by this documentation run. Keep the upstream signed kernel/modules intact; derive our session and policy in a Containerfile built in Actions.

**Proposal — concrete comparison, grounded in linked capabilities:**

| Concern | Chosen Bazzite NVIDIA derivative | Ubuntu 26.04 fallback |
|---|---|---|
| Our labwc session | Add greetd/labwc; disable the inherited display manager, desktop autostarts and power agents. Retain unused desktop packages initially if removal risks driver dependencies; never start KDE/GNOME/Steam desktop sessions alongside ours. [Z2] | Start from a minimal install and add the same session; fewer inherited desktop policies to remove. Install recipes are documented. [U3] |
| Trust | Accept Universal Blue MOK at installation, keeping Secure Boot enabled; verify signatures of the actual derivative. Image-signing trust is separate from boot trust. [Z3], [Z5] | Prefer Canonical-signed kernel and prebuilt NVIDIA modules; an exact supported pairing must work without silently substituting DKMS. [U2], [U5] |
| Update ownership | Replace Bazzite's automatic update entry points with AresOS maintenance; digest pinning alone is insufficient. [Z6], [Z7] | Disable/integrate unattended upgrades and package timers; lock complete packages and sources. [Z8], [U4] |
| Recovery effort | Boot the retained complete deployment; use independent media for broken root/ESP. Persistent state needs separate recovery. [Z4], [Z9] | Restore a verified previous system image or reinstall from a complete offline package bundle; an old kernel alone is insufficient. [U2] |

**Proposal:** Bazzite wins because the owner accepted enrollment and prefers less recurring repair. If signed NVIDIA, labwc, isolated installation, offline recovery or direct Windows return fails P3, investigate the failure then qualify Ubuntu against the same gates. Do not quietly relax Windows protection or change the base in an installer.

**Verified alternatives:** NixOS offers declarative generations but the evaluated Lanzaboote route enrolls firmware keys; Arch media lack Secure Boot support; Debian live-build supports image customization. [D1], [D2], [D3], [D5] **Proposal:** defer these and a standalone bootc distribution; none removes our session and recovery obligations. Actions is the primary builder; optional WSL2/Docker builds do not qualify native boot. [G2], [W1], [W2] Appendix A defines reproducibility and budget gates.

## 2. Graphics, memory and power

**Verified:** NVIDIA documents application offload and workload-dependent power management; its open modules require matching userspace. [N1], [N2], [N3] **Proposal:** qualify the image's kernel, modules, firmware and libraries together. Start with Xwayland Minecraft and per-game NVIDIA offload, never session-wide GPU environment variables. Ordinary apps launch from the helper's clean environment. Measure the actual game renderer; all-NVIDIA composition is a fallback test, Intel-only Minecraft does not pass.

**Verified:** Minecraft 26.2 has an experimental Vulkan option. [M3] **Proposal:** first qualify OpenGL explicitly, without shaders, then the pinned Iris/Sodium combination. Start at 60 foreground FPS on AC, 30 on battery, with shaders off on battery. These are hypotheses, not performance evidence.

**Proposal:** budget desktop Java heap at 3 GiB initially, with a 5 GiB whole-process working target; normal gameplay gets a 4 GiB heap and 6 GiB working target after the desktop exits. Reserve 3 GiB for OS/recovery and 4 GiB for ordinary apps, leaving roughly 3 GiB headroom in gameplay mode. Measure actual available RAM and native/GPU allocations rather than equating heap with total memory. Two resident games would budget 18 GiB before extra shader pressure, so simultaneous residency is deferred; pausing alone does not meet our release-memory requirement. Appendix B5 defines pressure handling and the GPU gate.

**Proposal:** when an app is foreground, clear game inputs, mute desktop audio, pause desktop simulation through the mod and reduce rendering to at most 5 FPS, testing zero rendering when fully hidden. At five minutes idle, blank the display without suspending; save/stop the desktop if hidden/idle power remains excessive. Before daily use, compare identical browser workloads with the world stopped, hidden and visible on AC/battery and agree measured power, temperature, noise and return-time limits. A failed limit keeps the save/stop fallback and blocks a battery-comfort claim.

## 3. Secure Boot and Windows return

**Verified:** Bazzite documents installation-time MOK enrollment while Secure Boot remains enabled. Its separate post-install method toggles Secure Boot; that is not our path. [Z5] Shim stores MOK state separately and measures trust-related state into TPM registers; Microsoft describes PCR-dependent BitLocker validation. [Z10], [Z11], [Z12] **Proposal:** record and verify the Universal Blue key fingerprint before enrollment. Allow only that accepted trust change; do not replace firmware keys, clear the TPM, disable Secure Boot or suspend Windows protection.

**Assumed:** this firmware accepts the selected boot chain and discovers the SSD through F12. Direct Windows Boot Manager return avoids intentionally chainloading Windows through Linux, but a zero-BitLocker-prompt guarantee remains unproven. **Proposal:** require an independently accessible, verified Windows recovery key before the owner-controlled trial. Preserve Windows's ESP and BootOrder; test Windows with USB present and absent after enrollment. Any unexpected recovery prompt fails acceptance and stops rollout.

## 4. Session, apps and recovery

**Verified:** labwc supplies stacking windows, decorations, actions and toplevel integration; cage targets one maximized app, sway an i3-style session, and gamescope gaming presentation. [L1], [L2], [L4], [C1], [C2], [C3] **Proposal:** keep labwc, using a borderless maximized Minecraft window below normal apps. A custom compositor adds unnecessary work; gamescope can be evaluated later for gameplay.

**Proposal:** closing the foreground app's last window returns to the world; closing a background window preserves the active app's typing focus. Dialog closure returns to its parent. Alt+Tab switches apps, Super+Home returns to the desktop, Alt+F4 requests ordinary app close. Clear held keys/buttons at transitions, and capture the pointer only after confirmed game focus. Track actual windows, including existing processes; process exit alone is not closure. Appendix B1 specifies the versioned mod/helper boundary.

**Proposal:** Super+Ctrl+Escape opens a recovery terminal; an authenticated Ctrl+Alt+F3 TTY survives compositor failure. Apps live independently of the game process. Restart a crashed desktop underneath the active app, using both a short-window limit and a persistent consecutive-failure budget; never repeatedly reopen a broken world. Authentication, deliberate stops and memory pressure suppress restart. See B2.

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

## 8. Install targets and choosing an OS

**Verified:** Lenovo documents F12 selection and the model-family 2242/2280 slots, not this unit's free slot. [H1], [H2] **Proposal:** external SSD first, provisioned with the Windows drive inaccessible to the installer. Require unique stable target identity, protected-drive refusal, independent ESP/root/data and no Windows mounts or swap. Reject ambiguous USB identifiers. Never select by size or device order.

**Proposal:** use the target's removable boot path, preserve BootOrder, and audit installer and later bootloader hooks for firmware writes. The documented MOK enrollment is the only accepted persistent trust change. No Windows chainload menu, shared ESP, BCD edits or opportunistic firmware entry. If F12 discovery fails, stop and review. An internal NVMe install is a later reinstall/restore package, after physical slot confirmation. Appendix C retains fail-closed install and recovery safeguards.

## 9. Updates, backups and recovery

**Verified:** Bazzite's desktop updates automatically; `uupd` includes automatic/manual services and can drive OS and app updates. [Z6], [Z7] **Proposal:** AresOS maintenance is the sole mutation authority for managed OS/apps/game components. Disable inherited automatic installers and bypass entry points from the first image. Initially the maintainer follows a manual maintenance checklist; later automation uses the same gates. Review security advisories at least weekly and urgent fixes within 48 hours; a stale unsafe prototype stays offline until safely serviced.

**Proposal:** verified signed image + manifest → close-app checkpoint → clean world stop/backup → preserve recovery set → controlled deployment/migration → explicit reboot → health checks. Downloading into an inert cache may happen earlier; staging a bootable deployment counts as maintenance. No live package layering, surprise reboot or unreviewed game upgrade. A fresh release B and A→B must converge on managed packages/configuration/services, including removals. A1 defines updater exclusions and migration checks.

**Verified:** Bazzite supports selecting/pinning a previous deployment; persistent data is separate. [Z4], [Z9] **Proposal:** before *any* update, retain a complete known-good OS/kernel/NVIDIA set, matching game inputs and compatible state checkpoint; prepare an independently bootable offline recovery USB. Manual rollback is the initial policy, not automatic failed-boot healing. Rehearse broken-root and damaged-ESP recovery separately. A2 assigns Wi-Fi and other state outside home explicit restore/reprovision rules.

**Verified:** restic needs repository credentials to retrieve/decrypt backups. [Z15] **Proposal:** before valuable saves, retain the repository address, password, backend/second-factor recovery access, instructions and matching game manifest independently of the AresOS drive, outside Git. Prove restore with that drive unavailable. Clean local copies alone are not drive-loss protection; B6 defines off-device backup and restoration.

## 10. Testing and the first real boot

**Verified:** QEMU supports virtual devices and Windows WHPX/TCG. [T1] **Proposal:** use file-backed VM disks for destructive installer/recovery tests; no physical Windows passthrough. Use existing acceleration or hosted Linux, without changing this laptop's settings. VM success cannot qualify real Secure Boot trust, NVIDIA, BitLocker return, wireless, battery or sleep.

**Proposal:** Appendix E puts the decisive trial third: minimal image/safe installer → one integrated session/Prism/mod/app/save/backup milestone → **F12 → Nether hub on NVIDIA → open/close one app → clean shutdown → ordinary Windows boot**, USB present and absent. Restore a deliberately changed world. Only then build update automation and polish. Appendix D includes each council failure scenario; all trials remain unexecuted in this docs-only revision.

## Top risks

**Proposal — release gates:**

| Risk | Required reduction |
|---|---|
| Windows damage or lockout | Isolated target, own ESP, unchanged BootOrder, independently verified recovery key and tested Windows return. |
| Save loss despite “successful” backup | Independent credentials, fresh-system restore, clean-save acknowledgement and one writer. |
| Unsaved app work or unsafe power event | Cancellable close-app checkpoint; independent saving; fault-injected lid/key/battery tests. |
| Bad image or state migration | Complete retained deployment, offline repair media, selective state restoration, A→B and rollback trials. |
| Unusable performance or heat | Stop desktop during gameplay; pressure isolation; owner-accepted measured daily-use limits. |
| Base-specific work before feasibility | Early hardware gate before updater UI, splash, sleep and internal-drive work. |

## Appendix A — Build, maintenance and state contracts

### A1. Image and sole maintenance authority

**Proposal:** these are future repository areas; no OS code/config is created by this brief.

| Area | Required definition |
|---|---|
| `os/Containerfile`, `os/config/` | Bazzite NVIDIA base digest, exact added/removed packages, labwc session, safe power defaults, update exclusions and managed service state. |
| `os/manifest/` | Base and resulting image digests, architecture, package inventory, upstream signature identity, kernel/NVIDIA versions, config/state schemas and interface-v1 compatibility. |
| `os/installer/` | Pinned installer tooling, explicit target/ESP policy, dry run, refuse tests, recovery-only mode. |
| `os/game/` | Desktop and separate gameplay templates, exact runtime/mod hashes and download references; no entitled game assets or tokens. |
| `os/tests/`, CI | Pinned Actions/build tools; build, install, migration, rollback and fault trials; publish signed image and manifest only after checks. |

**Verified:** the Universal Blue template documents Containerfile derivation, Actions builds and container signing. [Z3] **Proposal:** publish the derivative in the repository owner's controlled registry and its signed release manifest in GitHub Releases. Pin the base as `ghcr.io/ublue-os/bazzite-nvidia@sha256:<resolved digest>`; the notation is a design placeholder, forbidden in a release. P1 records the real digest and signature verification without trusting a mutable tag at build/boot. Lock added package repositories/versions/hashes too: a base digest cannot freeze later network package resolution. Fail if a pinned input disappears. Keep signing secrets and private registry credentials out of Git, images and logs; the client receives only minimum read access and public verification material.

**Proposal:** use one documented deployment backend for the qualified image. Bazzite's researched recovery path uses rpm-ostree/OSTree; the current image template also describes bootc. [Z4], [Z3] P1 must record which backend the selected digest actually uses and demonstrate its deploy/pin/rollback operations; never let both independently manage the installation. Automatic rollback requires separate health policy and remains deferred; manual previous-deployment selection is mandatory.

**Proposal — remove competing mutation paths from the first image:**

- Mask `uupd.timer`, `uupd.service` and `uupd-manual.service`; remove their passwordless invocation grants for the daily account. Upstream publishes these units and describes `AutomaticUpdatePolicy=none` for rpm-ostreed. [Z7], [Z16], [Z17], [Z18]
- Set rpm-ostreed automatic installation/staging to none; disable any bootc automatic update unit present in the selected image. Inventory system and user timers, services, autostarts and package hooks rather than assuming this name list is exhaustive.
- Disable inherited Bazzite Updater/Portal update, rebase and reset shortcuts, `ujust update`/topgrade automation, desktop software-center installation and automatic Flatpak/Homebrew/container updates. Do not launch inherited desktop setup/power agents. Managed apps and Prism/game updates use the same maintenance gate; personal data/saves remain writable.
- The daily account gets named maintenance requests, not general passwordless OS mutation. A separate recovery administrator can deliberately repair the system; record such changes and require reconvergence before ordinary use. Do not claim protection against an administrator intentionally bypassing policy.
- Scan the exact image inventory in CI. An unknown updater or unreviewed enabling change fails promotion. Outside maintenance, fire inherited timers and UI/manual entry points with a newer release available; installed versions, staged deployments, boot files and managed service state must remain unchanged.

**Proposal:** the maintainer reviews upstream/security changes weekly, urgent fixes within 48 hours. Before automation, apply approved releases manually using the same app/save/backup/AC/space/recovery gates. A pinned prototype with a known unresolved urgent issue is taken offline. No update may run before recovery readiness; rebuilding disposable media is the fallback until then.

**Proposal:** updates reconcile additions AND removals, renamed services, managed configuration, user overrides and private-state schema. Keep policy defaults in image-owned locations; migrate selected writable overrides explicitly. Archive conflicting overrides with a visible explanation. A failure stops activation. Compare fresh B with used A→B, including a removed package, obsolete enabled unit and config rename; allow only enumerated private differences. Rollback must restore compatible writable state too, because OSTree shares `/var` and merges `/etc`. [Z9] Never rely on atomic `/usr` alone to remove an old user unit.

**Proposal:** CI produces a rebuildable, auditable image, not a promise of byte-identical disks. No game account in CI. Measure runner time/storage for a single image and VM trial before scheduling builds; private Actions allowance is limited and the owner's remaining budget is unknown. [G1], [G2] Use on-demand large artifacts and short log retention; stop at budget, without enabling paid runners. WSL2/Docker are optional future development tools, not installation prerequisites on the owner's laptop. [W1], [W2]

### A2. Complete recovery and private machine state

**Verified:** deployment retention does not restore all persistent application state; NetworkManager's keyfiles can contain credentials outside home. [Z4], [Z9], [Z19] **Proposal:** before any manual or automatic update, pin the currently proven deployment by recorded identity, not an assumed index, and keep it until its successor passes boot, renderer, app, power and restore checks. Retain its kernel, initramfs, NVIDIA module/userspace/firmware, system libraries and AresOS components together, plus the corresponding game manifest and clean pre-conversion world. One old kernel or only an OCI reference is insufficient.

**Proposal:** require a second, independently bootable recovery USB with signed boot components, tools, offline copies of the known-good OS/driver payload and required dependencies, integrity manifest and instructions. Before the first update, the initial qualified release is this previous-system recovery baseline. Include legally obtained game/runtime files in private owner recovery storage when needed for offline launch, never in Git/shared CI. Verify the kit under the laptop's accepted trust and with network disabled. Registry access is not an offline recovery plan.

**Proposal:** AresOS owns an ESP, boot/root storage and a distinct home-data partition mounted at the base's supported home backing path (qualify `/var/home` with `/home` compatibility in P1). Absent/wrong data UUID stops launch. Shared `/var` outside that data partition is not assumed to survive root replacement. Inventory all installed services' persistent state; an unclassified directory blocks recovery sign-off.

| State | Proposed recovery policy |
|---|---|
| Worlds, gameplay saves, app documents and mod appearance/pins | Preserve data partition; encrypted off-device backup; restore a matching manifest/world pair after conversion. |
| `/etc/NetworkManager/system-connections` and referenced VPN/certificate files | Selective encrypted machine-state backup; restore correct ownership/permissions and labels. Keep a separate manual Wi-Fi credential/instruction fallback. [Z19] |
| Recovery account/password, UID/GID, groups | Reprovision the same required IDs using recovery instructions and an independently held recovery secret; do not blindly copy `/etc/shadow` or `/etc/passwd`. Test login before finishing recovery. |
| `/etc` managed policy, mounts, locale, keyboard, hostname | Rebuild managed policy from release; restore only allowlisted owner preferences. Regenerate mounts from verified AresOS UUIDs; never import Windows mounts. |
| `/var/lib` AresOS migration/launch journals and app catalogue overrides | Schema-versioned encrypted checkpoint; reconcile with live processes before replay. Restore overrides selectively; stale in-flight launch records cannot spawn duplicates. |
| Bluetooth pairing, printer setup | Reprovision/pair explicitly; document loss of pairings. These do not gate basic offline recovery. |
| Machine ID and SSH host identity if SSH is later enabled | Regenerate on replacement installation; explain any changed host fingerprint. SSH is not a recovery prerequisite. |
| Prism/Microsoft tokens and private registry credentials | Reauthenticate/reissue; excluded from world backups. Offline prepared profile is tested separately, never reconstructed by editing tokens. |
| Backup location/password/backend and second-factor access; disk-unlock recovery | Independent recovery kit/password manager accessible without AresOS; secrets never in Git. Test access with the original SSD absent. |
| ESP/boot files and MOK trust | Repair only the identified AresOS ESP from the kit. Record accepted key fingerprint; verify enrollment, not automatic firmware reconfiguration. |

**Proposal:** rehearse (1) an unusable root with intact data and (2) a damaged AresOS ESP independently, offline. Preserve the named data partition, restore selected machine state, verify NVIDIA rendering, Wi-Fi, recovery login, player identity and world access. Require unchanged protected dummy-disk hashes and BootOrder; then repeat the appropriate owner-controlled hardware gate. Ubuntu fallback must meet this same contract using a complete previous-system image/offline dependency set, not a kernel-only recovery claim.

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

**Proposal — wire contract `aresos-shell/1.0`:** local newline-delimited JSON on a private Unix socket under `$XDG_RUNTIME_DIR/aresos/`. Same-user peer validation, launch nonce and instance ID bind a connection to the supervised desktop. This is a local session protocol, not a security boundary against all programs of the same user. Root operations use separately authorized named methods, never caller-provided commands/paths/environment.

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

**Proposal:** keep repository location, decryption password, recoverable backend/second-factor access, restore instructions and manifest off the AresOS drive. An independently accessible password manager or secured offline copy is acceptable; credentials encrypted only by a key on AresOS are not. Keep private machine-state backups separate from ordinary world snapshots and omit refresh tokens. Before valuable saves, disconnect the original SSD, restore on a fresh system using only the independent kit, and verify known builds, inventory, UUID, marker and app IDs. Never substitute a successful backup command for this restore test.

**Proposal:** unavailable remote backup queues clean local staging with visible pending status. A failed local checkpoint blocks maintenance. Ordinary shutdown may offer an explicit saved-but-not-backed-up choice; it never waits indefinitely for network. Emergency battery saving skips backup transfer. Never prune the last proven restore point to fit an update. Restoring an older game requires its pre-conversion world copy; OS rollback alone is not world rollback.

## Appendix C — Installer safety specification

**Proposal:** these requirements bind both Bazzite and the Ubuntu fallback before physical provisioning.

1. Default to inspection/dry run. Require the owner's named expendable target; identify model, capacity, serial/WWN, transport and stable path. Resolve exactly one whole disk and recheck before each write. Deny the known Windows identity and all backed partitions/mapper aliases. Reject mounted/in-use targets and the installer medium.
2. A Micron/512 GB match is only an additional deny heuristic. Missing/duplicate USB identifiers, ambiguous topology or changing identity mean stop. Never fall back to `/dev/sda`, largest disk, enumeration order or an unattended destructive default.
3. First provision in an isolated Linux installer environment seeing only the target physical SSD. No Windows-drive passthrough, host filesystem shares or automatic mount helpers. If isolation cannot be established, stop. A later installation brief must authorize its tooling; this research run does not install/administer anything.
4. Keep ESP, `/boot`, OS deployments and data entirely on the target. Disable OS probing and automatic BootOrder/boot-entry writes. Audit the actual Bazzite installer and update/recovery bootloader hooks; do not assume Ubuntu's Curtin flags apply. Test firmware-variable diffs. Use signed removable-path boot files without an entry-creating fallback helper. Preserve Windows Boot Manager and its priority.
5. The accepted installation MOK enrollment is a documented exception to unchanged firmware state, limited to the verified Universal Blue key and its enrollment variables. Record before/after trust state separately from BootOrder. No automatic Secure Boot toggle, TPM clear, firmware-key replacement or BitLocker suspension. A later unexpected trust change fails qualification.
6. At runtime, provide no Windows mounts/swap, suppress protected-disk discovery in file/removable-media UI and deny user mounting/unlocking it. Never supply the Windows recovery key to Linux. Privileged code remains capable of damage; isolation, limited authority and tests are still required.
7. Recovery is a separate mode using recorded AresOS partition UUIDs. Reinstall only the identified boot/root area; preserve the home-data partition and restore selected machine state under A2. Repair the AresOS ESP only when requested as that specific mode. Require off-device backup verification; uncertain layouts fail closed. No generic “erase disk” recovery button.
8. VM tests compare complete protected-disk/partition hashes and BootOrder before/after install, update and both recovery modes. Real trials require owner-confirmed ordinary Windows boot with USB present and absent. Removal of AresOS media must leave Windows independent. Internal NVMe migration waits for slot confirmation and its own reviewed brief.

## Appendix D — Acceptance trials, not executed results

**Proposal — all rows are future gates.** Save logs/screenshots in each implementing package's review folder, redact secrets, and distinguish VM evidence from hardware evidence. Fabric tests exercise the mod; session tests must exercise the actual mod/helper path too.

| Gate | Trial | Pass condition |
|---|---|---|
| P1 image | Resolve/pin Bazzite NVIDIA digest, inspect signatures/inventory, build/install/boot twice | Exact declared image and backend; only our session/power policy active; no placeholder pins. Secure Boot VM results are not Lenovo evidence. |
| P1 installer | Absent/reordered/duplicate target, mounted disk, dummy Windows ESP, install/recovery | Unsafe cases refused; protected image hashes and BootOrder identical; only separately documented MOK enrollment variables may change. |
| P2 interface (finding 7) | Existing package-01 config and saved items through mod→v1→helper→editor; repeat click, restart helper, reject wrong major | Stable `notepad` ID/pins/look/name, no direct Linux launch or duplicate uncertain retry; actionable incompatibility. |
| P2 focus (10) | Continuous browser typing while background terminal closes; then foreground close, dialogs, Alt+Tab, held keys | No focus theft or stuck input; foreground final close returns to world. |
| P2 crash (9) | Fast failures and ready-then-crash every four minutes; restart supervisor during sequence | Finite persistent recovery after three consecutive failures; no ready-event reset or lost latch. |
| P2 normal shutdown (3) | Unsaved editor and browser form; Cancel, then safe completion; helper dead too | Cancel preserves both and usable world. No OS power-off until manual app closure/confirmation and clean desktop save. |
| P2 power (2) | Inject lid, key and critical battery during loading, >5-second saving and maintenance; kill helper and separately coordinator | No unqualified sleep; guardian save succeeds within measured budget; no early Java termination, emergency update activation or network-backup wait. Reopen world and verify new edits. |
| P2 backup (1) | Alter world, back it up, remove original SSD, restore on fresh system with independent credentials | Known builds, player inventory/UUID, desktop marker and app IDs restored with matching manifest. |
| P2 setup | Missing data/world/assets, offline, expired/revoked account and clock skew | Visible setup/recovery, same identity when offline is supported, no new empty world or restart loop. |
| P2/P5 pressure (8) | Browser tabs/call/editor + desktop, then gameplay; controlled memory pressure | Responsive recovery, ordinary app work intact, explicit unclean/OOM status if injected, no relaunch loop. Record whole-system RAM/swap/VRAM. |
| P3 hardware (6, 11) | F12→Nether on NVIDIA→open/close app→save/shutdown→direct Windows, USB present/absent | Correct actual renderer, clean saved changes, unchanged Windows boot priority/ESP, no recovery prompt; repeat altered-world restore. |
| Before any update (4) | Offline previous-deployment boot; separately break root and AresOS ESP, use independent media | Complete matching OS/driver set, NVIDIA renderer, Wi-Fi, recovery login and world restored; data/protected disk/BootOrder preserved. |
| P4 maintenance (5) | Fresh B vs used A→B; removed package, renamed service, config migration; trigger inherited timers/manual updater UI outside maintenance | Equal managed inventory/services/config; no unmanaged mutation/staged deployment; rollback restores compatible state. |
| P5 gameplay | Separate normal survival/multiplayer instance, failed launch, crash, cancelled close, restart supervisor mid-transition | Normal rules, no desktop mod/items/marker leakage, one game by default, preserved saves, correct focus and one desktop return. Lunar separately gated. |
| P5 daily comfort (13) | Same browser workload with world stopped/hidden/visible, AC/battery, idle and charger changes; ten cold boots | Owner-accepted measured power/heat/noise and return-time limits recorded; otherwise retain save/stop fallback. |
| P7 suspend (12) | Chosen retain/relaunch policy; sleep away from hub and with browser foreground; twenty AC/battery/display cycles | Defined position/focus restored, no duplicate game, measured acceptable wake-to-input, no black screen/corrupt save. Until then sleep remains disabled. |

## Appendix E — Phase 2 packages in build order

**Proposal:** these labels replace the previous P1–P12 order; they are planning packages, not authorization to install. The short path is P1→P2→P3. Safety and tested backup stay on that path; updater UI and presentation do not.

| Order | Package and exit condition |
|---|---|
| P1 | **Minimal image plus safe installer.** Pin Bazzite NVIDIA, Containerfile/Actions, one deployment backend, our session entry/recovery terminal, updater exclusions and system power defaults. Pass isolated-target, own-ESP, protected-disk refusal, BootOrder and recovery-layout VM tests; measure CI cost. |
| P2 | **One end-to-end milestone.** Integrate labwc, terminal, network/login, native Prism, exact marked world, interface v1 with one migrated app, guardian/clean shutdown and independently credentialed backup/restore. Include the small Nether hub/spawn mod dependency excluded from 01/01b; pass power/helper-failure and app-cancel trials before hardware. |
| P3 | **Early hardware trial.** After one-time setup/enrollment and recovery-key checks: F12→controllable Nether hub on NVIDIA→open/close one app→clean shutdown→normal Windows boot, USB present and absent. Restore a deliberately changed test world; on qualification failure evaluate Ubuntu before further base-specific investment. |
| P4 | **Controlled releases and offline recovery.** Finish/test complete previous deployment, independent recovery media, broken-root/ESP repair and state restoration before enabling any update. Then add signed release deployment, A→B convergence and security maintenance automation; the prototype used only the same controlled manual procedure when its recovery gates were already met. |
| P5 | **Gameplay and daily use.** Add exclusive normal-Minecraft app and return, broader peripherals/portals/audio, representative study workload and resource/comfort measurements; optional Lunar and simultaneous games require their own qualification. |
| P6 | **Presentation and controls.** Original Plymouth/loading polish, local-only artwork input, Bluetooth pairing polish, in-game settings and optional updater UI. Keep existing recovery paths. |
| P7 | **Suspend, only if qualified.** Choose retain-process or stop/relaunch, define resume/focus/position behavior and acceptable latency, then pass repeated hardware trials before exposing Sleep/lid suspend. Hibernate remains separate. |
| P8 | **Internal NVMe migration.** After owner/council review and slot confirmation, safe reinstall/restore with Windows-return checks. Shops and other themes get separate briefs after this foundation. |

**Proposal:** P1–P3 use disposable data and no automatic updates. Any manual update still requires A2's full recovery contract; otherwise rebuild expendable media. Pinning is not indefinite security maintenance: the named maintainer reviews advisories from P1 onward. The earliest hardware test does not wait for a custom updater, artwork, Bluetooth polish, suspend or internal-drive work.

## Appendix F — Evidence index and remaining uncertainty

**Verified:** the primary sources below have a check date of **2026-10-21**, applying to every entry and reference link. U1–T1 retain the original design's research evidence, recorded in its [report](../../reviews/02-os-base-design/REPORT.md); Z1–Z22 were read for this revision, with Ubuntu's driver page also rechecked. Documentation is evidence of upstream capability, not a qualified AresOS package. “Latest” systemd/UPower documentation does not establish availability in our future pinned image; P1 must check it.

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

**Assumed / unresolved:** exact Bazzite digest/backend and added package lock, this machine's trust/BitLocker policy, GPU routing, memory/VRAM measurements, sleep reliability, USB identity, CI quota, offline player continuity and acceptable daily comfort. Bazzite is the owner's choice; Ubuntu is the fallback if qualification fails. Encryption and backup destination await the personal-use gate. Research did not download/boot an image or inspect disks. Original Fedora/RPM Fusion pages were inaccessible; this revision's guessed UPower configuration URLs also failed, so the design cites its readable API and makes the actual configuration a qualification gate, not a verified setting.

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
