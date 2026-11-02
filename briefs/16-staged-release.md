# 16: Staged physical release (owner decision) and a native mounted-protected-child refusal check

New package on branch `pkg/16-staged-release` (from `main` at `dd0cf67`, after packages 14 and 15 merged). Read `AGENTS.md`, `docs/INSTALL-STATUS.md`, `docs/INSTALL.md`, the council delta `reviews/councils/2026-10-25-install-gate/delta/RECHECK.md`, and `reviews/15-owner-path/REVIEW-3.md` / `REVIEW-4.md`.

## Owner decision (2026-11-02): staged release

As written, `INSTALL-STATUS.md` keeps the physical install NOT RELEASED until physical and novice gates close "before opening the laptop, writing installation media or installing". Most of those gates can only close on the laptop. The owner chose a **staged release, with the owner as first reader and the maintainer (Claude) checking each stage's records before the next**:

- **Stage A, RELEASED now:** checklist steps 1–2: Windows preparation, backups, the recovery stick, record A, and writing and test-booting the installer stick without installing. Neither SSD is written.
- **Stage B, RELEASED after the maintainer has checked stage A's records:** step 3, fitting. The owner fits the SSD using the fitting checkpoint. The maintainer checks the seating and battery photos, the firmware screen showing both drives, and record B after-fit. This replaces "Lenovo/service must qualify fit/parts"; a battery warning still means qualified repairer first. Target: about 2026-11-09, the SSD return deadline.
- **Stage C, NOT RELEASED until all three hold:**
  1. the maintainer has checked stages A and B
  2. this package's native mounted-child check has passed
  3. the maintainer has updated the table

  Then come steps 4 onward. The owner sends each step's record to the maintainer before continuing.
- **How the other gates close:**
  - The unaided-reader/phone trial becomes the owner as first reader, with the maintainer on call.
  - Each physical gate closes when the owner performs that step and the maintainer has checked the evidence: LOQ shortcuts, live KDE keyboard, tools-stick lifecycle, NVIDIA, the Windows record helper, token retirement, early hardware.
  - No gate is silently dropped. Each row says how it closes now.

## Do

1. **Status and guide:**
   - Rewrite the "Physical installation" row and the affected gate rows in `INSTALL-STATUS.md` to the staged model above. Quote the owner decision and date. Each stage gets its status, what it covers, and exactly what closes it.
   - Adjust INSTALL.md's opening "release authority" sentence, and add a short stage marker at steps 1, 3 and 4, so the owner sees where each stage ends: "stop here and send your records to the maintainer".
   - Update the owner-path tests that encode the old wording. Keep every other test as strict as it is.
2. **Native mounted-child check:** close the council RECHECK condition that is still OPEN.
   - Extend the native loop checks (`os/ci/owner_devices.py`, or a new native test that the probe runs) with a real loop fixture. The protected disk has a child partition (the NTFS or ESP stand-in) **mounted** read-only.
   - Run the real owner bootstrap/helper path that must refuse. Require the refusal with zero mutations: protected-image hash unchanged, no new mounts, no partition changes, no file written to the target. Then confirm cleanup: unmount, detach, and nothing left mounted.
   - Make it fail without the tools' mounted-child refusal. Show this with an injected stand-in that skips the check.
3. **Dispatch wiring:** keep it minimal, and don't disturb package 14's records.
   - Map `pkg/16-staged-release` in `os-image.yml` and `rehearsal_guard.py` so it can dispatch **only the owner-tools probe**.
   - Give it its own `rehearsal-packages.json` entry: `minute_cap` 120, `dispatch_caps` probe 2, nothing else; organization reserve 150; push and closing privacy reservations 0 (14zw local-hook policy).
   - Where a guard assertion is package-14-only but concerns the owner-tools probe, allow package 16 too, and test it. Everything else stays package-14-only.
4. **Local checks:**
   - the affected and owner suites in WSL, with and without `-B`
   - the pinned gitleaks
   - the checkout-byte bindings as in 14zze
5. **One push** through the privacy hook (never `--no-verify`). Open a PR. Then run **one probe** on that head and watch it to the end.
   - In the REPORT, quote the mounted-child check's real native result and the cleanup proof.
   - If it passes, mark the INSTALL-STATUS row for the mounted-child condition as met, with the run link, in a **local** commit. Push it as a second, final commit. That push starts no workflow.
   - Then STOP and report. Don't merge.

**Model:** gpt-6.1-sol, xhigh.
