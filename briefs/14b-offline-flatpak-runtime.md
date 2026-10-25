# 14b: The NVIDIA Flatpak runtime sync is accepted deferred work; continue package 14

Follow-up on branch `pkg/14-owner-tools` (PR #13, draft). Read the PLAN-GAP in `reviews/14-owner-tools/REPORT.md`. Brief 14 still applies, with the change below.

## Integrator decision

The 14 gate was right to stop: brief 14 said no first-boot service may wait for a later network, and `ublue-nvidia-flatpak-runtime-sync.service` does. That wording was stricter than its purpose.

**The offline rule protects the OS deployments, the boot entries and the disks.** The retained unit and script show that the sync only adds the Flathub remote and installs `org.freedesktop.Platform.GL{,32}.nvidia-<version>` into the system Flatpak installation (`/var/lib/flatpak`). Flatpak keeps its own repository, separate from the system's OSTree repository. The sync can't stage, finalize, reorder or pin a deployment, change a BLS entry or touch a disk. Online, stock would do the same during the first boot. Offline, it retries every 30 seconds and finishes once the network comes up after `prepare`. Flatpak apps (later Prism and Minecraft) need it for the NVIDIA GPU.

So:
1. **Accept it as deferred work.** Don't mask, disable or delay it, and don't install the runtime some other way.
2. **`prepare` records its state** (unit state, the `check` result, the installed runtime IDs) in its diagnostics, but doesn't wait for it. The idle check must not treat it as deployment work. It must still catch every rpm-ostree/bootc/ostree transaction and updater exactly as today.
3. **After the network comes up,** `title` (or `records`) must show the deployment list, pin and pending state unchanged from `prepare`'s record. Report whether the runtime sync has finished; an unfinished sync isn't a STOP.
4. **The guide** tells the owner that a notification about the NVIDIA Flatpak runtime may appear while offline, that it's expected, and that it goes away after the network is on.
5. **Classify any other deferred first-boot network work by the same rule.** If it can't change a deployment, boot entry or disk, record it and accept it. If it can, stop with a PLAN-GAP before any dispatch.
6. **Testing the sync:** the CI VM uses virtual graphics, so the unit's `/sys/module/nvidia/version` condition is false there and the VM can't exercise it. Mark this source-verified and physically untested. Add it to the laptop-side release-gate items: after the network comes up, confirm the sync ran and the deployments are unchanged.

## Then

Continue brief 14 from where the gate stopped:
- the bundle, the Windows copy step and the Linux commands
- the unit tests (zero mutations on every refusal)
- the minimal guide and card changes
- the ledger and the VM qualification

Everything else in brief 14 stands. Mark PR #13 ready for review when acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
