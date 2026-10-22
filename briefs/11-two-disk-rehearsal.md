# 11: Two-disk install rehearsal, GRUB recovery promotion, pinned media

New package on branch `pkg/11-two-disk-rehearsal`. It closes the CI-testable install gates in `docs/INSTALL.md` "Maintainer release gate": **Two-disk rehearsal**, **GRUB recovery promotion**, and the pinning part of **Media and followability**. Read that section, `docs/INSTALL.md` §3–§9, `docs/design/OS-BASE.md` §8, Appendix C and item 7 of its qualification list, `docs/EMERGENCY.md`, and the 06–06e sections of `reviews/06-image-release/REPORT.md`. Reuse the existing VM harness in `os/ci/` and the signed release `ghcr.io/carlsenares/aresos@sha256:362af9b7d2a5573363d2cc441505dd076603d1d96c1b5c01af55589db2b6c402` (don't rebuild or republish the image).

**Why it matters:** the owner's Windows SSD (Micron) must never be written. This package is the proof, in disposable VMs, that the install route touches only the new drive.

## A. Two-disk rehearsal (the main job)

1. **Disks.** Use two file-backed disks of near-equal size, with no physical passthrough:
   - a **protected Windows-like disk:** GPT with an EFI system partition containing a Windows-like `\EFI\Microsoft\Boot\bootmgfw.efi` and `\EFI\Boot\bootx64.efi`, an MSR, an NTFS partition with files, and a recovery partition
   - an **empty Linux target**

   Record the protected disk's whole-disk SHA-256, GPT/partition GUIDs, boundaries and EFI file hashes. Hash **offline**: VM off, image file closed.
2. **Install with the pinned live ISO** from `os/manifest/installer-isos.json`, following the route the owner will use (§4): only the target selected, "use entire disk", a new EFI partition on the target.
   - Prefer driving the real installer UI (QMP input plus screenshots), and capture the destination, review and EFI/bootloader screens.
   - If faithful UI automation turns out infeasible, use the most faithful automated path through **the same ISO's installer** (for example kickstart limited to the target disk). Record exactly how it differs from the owner's click path; that difference stays an open item in the media/followability gate.
   - **Stop and report** rather than sink more than about 2 full runs into automation dead-ends.
3. **Then run the tested 06e path on the installed target:** the switch to AresOS, then rollback, then the documented default undo (§9's "stop using AresOS" path: restore the Windows-first order, no erasing). After **every** stage (install, switch, rollback, undo), shut down and compare the protected disk offline: the whole-disk hash, GUIDs, boundaries and EFI files. **Any** change to the protected disk is a product failure: stop and report. That includes a write, a mount that changes it, swap, a shared EFI partition, or EFI fallback files.
4. **Firmware boot entries (NVRAM):** only a separate Linux entry may be added or reordered. The Windows-like entry must stay. Keep and diff the OVMF variable store across stages.
5. **Repeat with reversed drive order** (the protected disk enumerated second instead of first), at least for install plus the protected-disk audit.
6. **"Windows" without the Linux disk:** detach the Linux disk and prove the firmware still boots the protected disk's Windows-like boot path through its own entry (a marker EFI program is fine). Do this after install and again after undo.

## B. GRUB recovery promotion

Start with AresOS booted and still the default. Select the **recorded previous stock entry once** in the real GRUB menu via QMP keys (Esc, ↓, Enter, per Bazzite's docs), with no `grub2-reboot` shortcut unless the menu can't be driven. Record which path you used. Then:
1. Run the identity-checked step in INSTALL §6 "Keep recovered stock as the default", using the checksum recorded in that run.
2. Reboot with no selection.
3. Prove stock is booted and first, and the protected disk is unchanged.

If this passes, mark the gate DONE in INSTALL.md and `docs/EMERGENCY.md`; otherwise keep it UNTESTED. Physical-keyboard interaction stays a hardware item either way.

## C. Pin the media

- **Bazzite:** the "stable" ISO URLs can change underneath us. Check whether the pinned hashes still match the live download. Find a versioned or otherwise immutable reference, or record exactly how the owner verifies the hash on install day.
- **Writer and GParted:** pin Fedora Media Writer for Windows and GParted Live amd64 (the version, official download URL and official checksum, with the checksum source) in a manifest. INSTALL §2 and §9 should reference them.
- No rehearsal on physical media (that stays a hardware item).

## Pre-decided handling

- A harness flaw gets fixed with a regression.
- A product failure (any protected-disk change, a shared or wrong EFI target, or a lost Windows entry) means stop and report. Never weaken a check.
- Before every full run, check each new assumption (device names, installer screens, partition roles, menu entries) against real evidence from this ISO and image, and record it. 06d lost two runs to an unchecked assumption.
- No mod changes, and no Gradle or Minecraft runs.
- No change to the image, repo or package visibility, and no owner token. Agents never touch the real laptop's disks.

## Budget

About **680 GitHub Actions minutes** are left in October (the quota resets on November 1). This package may use **at most 450 minutes**. Checks-only runs are cheap; spend full runs carefully. If the work needs more, stop at the cap and report what's left.

## Acceptance

- Part A green in both drive orders, with offline protected-disk hashes identical at every stage, the NVRAM diffs, screenshots (or the documented automation difference), and the Windows-like boot without the Linux disk.
- Part B green, or a clearly stated blocker.
- Part C pinned.
- `docs/INSTALL.md` release gates updated honestly. Only items actually qualified move to DONE; everything human or hardware stays OPEN.
- A `reviews/11-two-disk-rehearsal/REPORT.md` with a gate → evidence table.
- Push the branch and open a PR. Do not merge.

**Model:** gpt-6.1-sol, xhigh.
