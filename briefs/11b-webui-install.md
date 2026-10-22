# 11b: Drive the real installer pages, then finish parts A and B

Follow-up on branch `pkg/11-two-disk-rehearsal` (draft PR #11). Read `reviews/11-two-disk-rehearsal/REPORT.md` and `ASSUMPTIONS.md`.

**Where 11 stopped:** part C (media pins) is done. The protected-disk audit tooling, two-disk fixture and Windows marker all work. Parts A and B weren't reached: both full allowances went to harness assumptions (the `losetup` flag, then the missing `ksvalidator`). The pinned live ISO's own launcher and Anaconda's help both say kickstart is **unsupported for live installs**, so the kickstart route is closed. Keep the guard that rejects it.

## Integrator decision: how to install

The live ISO's installer is **Anaconda Web UI** (`liveinst` serves the Web UI and shows it in Firefox).

1. **Primary path: drive the real Web UI pages.** In the live VM, launch the installer the way the owner will (from the live session, as `liveuser`). Make the Web UI's local server reachable from the CI host, for example a QEMU `hostfwd` plus a guest-side forward started from the root serial shell. Then drive the **same pages** with a headless browser on the host (Playwright, Chromium or CDP):
   - destination: select **only** the target and choose "use entire disk"
   - review: save its full text and a screenshot, requiring only target rows and a new EFI partition on the target
   - "Erase data and install"

   Save a screenshot of every page. The only differences from the owner's click path should be the browser (host Chromium instead of guest Firefox) and the transport; record both.
2. **Fallback, only if the pages can't be reached or driven:** call Anaconda's own D-Bus modules (the backend the Web UI uses: storage disk selection, the clear-all initialization mode, partitioning apply, then the installation task) from the root serial shell, with the same choices. Record exactly how it differs from the UI, and leave that difference open in the media/followability gate.
3. Neither the legacy ISO nor a hand-built stock disk may stand in for the live ISO's installer.

## Probe before every full run (mandatory)

Add or extend a cheap **probe** mode that boots the pinned live ISO with both disks attached and exercises **every** tool, command, port, page and selector the full run will use, **without installing**. It must reach at least the destination page, list both disks by serial, and capture the screenshots. Record each assumption with its evidence. A full run may only be dispatched after a probe on the same harness commit passed. If a full run then fails on something the probe should have covered, that's the stop signal.

## Then finish A and B as in brief 11

Install in **both drive orders**. Then run the switch, policy, tty3 recovery, rollback, default undo and the Windows-like boot without the Linux disk. Do the offline protected-disk audit after every stage and the NVRAM diffs. For part B, do the one-time GRUB selection via QMP keys, the identity-checked promotion, and an unattended stock boot. Every rule from brief 11 still holds: any protected-disk change is a product failure (stop and report), never weaken a check, no image rebuild, no visibility change, no token, no mod/Gradle/Minecraft.

## Budget

About **620 GitHub Actions minutes** remain in October. This follow-up may use **at most 350 minutes**, with at most **3 full runs** (probes and checks-only don't count toward the 3 but do count toward the minutes). If the cap is reached, stop and report what's left.

## Acceptance

- Part A green in both orders, with real Web UI page screenshots (or the documented D-Bus difference).
- Part B green, or a clearly stated blocker.
- INSTALL.md gates and `docs/EMERGENCY.md` updated honestly.
- An "11b" section in the REPORT with a gate → evidence table and the probe assumption records.
- Push, mark PR #11 ready for review if acceptance is met (otherwise keep it draft), and don't merge.

**Model:** gpt-6.1-sol, xhigh.
