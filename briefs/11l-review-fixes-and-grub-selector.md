# 11l: Fix the review findings and the GRUB selector, then qualify Part B

Follow-up on branch `pkg/11-two-disk-rehearsal` (PR #11). Read `reviews/11-two-disk-rehearsal/REVIEW.md` (fresh review of `d7f0ac4`: CHANGES-NEEDED, four should-fix findings) and the "11k" section of `REPORT.md`. Briefs 11c–11k still apply, plus the changes below.

## What 11k showed

Part A passed in both orders. Part B stopped before the menu selection:
- The harness's `stock_bls_entry()` (`os/ci/two_disk_vm.py`) requires ids `ostree-N-<name>`. Anaconda wrote bare `ostree-1` / `ostree-2` (`version 1` / `version 2`).
- The id digit isn't the menu position: `ostree-2` is titled `Bazzite (ostree:0)`.
- The owner's GRUB step names the entry by its title, not its file name, so it doesn't share this bug. But it gives no way to tell which title is stock, and both say "Bazzite".

## Integrator decisions

1. **The GRUB stock entry (review finding 2).**
   - **Verify first**, from the pinned stock image's own ostree and grub2 (versions from the retained inventory, source at those tags):
     - how ostree writes the BLS `title … (ostree:N)`, the `version` line and the file name
     - how the pinned `blscfg` orders the menu
     - that the pinned grub accepts a bare BLS id for `grub2-reboot`

     Record versions and source links. If they contradict "menu position = the N in `(ostree:N)` = the deployment's index in `rpm-ostree status`", stop and report a PLAN-GAP before any dispatch.
   - **Find stock only by checksum.** Resolve each real entry's `ostree=` target to the recorded stock checksum. Exactly one match, otherwise stop.
   - **Position from the verified rule, then confirmed on screen.** Apply the verified ordering to the real entries to get the expected position. Before sending any menu key, OCR the rendered menu and require the stock entry's title on that line and the AresOS title on line 0. A disagreement stops. Never guess.
   - Keep the fallback (`grub2-reboot <real id>`) only for the cases 11c already authorized, with the real id.
   - The blocked message names what actually failed (no checksum match, several matches, or position disagreement), not "not unique".
   - **Regressions:**
     - the retained 11k bare-id entries select stock at position 1
     - an id digit that differs from the title number never decides the position
     - zero or two checksum matches stop
     - a menu OCR that disagrees stops before any key
   - **Owner guide** (INSTALL §6 rollback, EMERGENCY): add a short, plain way to tell which GRUB entry is the stock copy, based on the verified rule, and say both entries are called Bazzite. The owner notes it down before the switch reboot.

2. **When Windows becomes the default (review finding 1).** The owner's guide is the product, so the harness follows the guide, and the guide becomes explicit:
   - After installation, the laptop starts Linux by default. The first stock start, including stock's one-time hardware-setup reboot, happens with Linux still first, then the first-login pause/pin.
   - Then, in §5: **F2 → put Windows Boot Manager first → Save and Exit → restart pressing nothing → Windows must start**, then record B. This proves the F2 step.
   - EMERGENCY: Windows is the default from that step on, not before.
   - **Harness:**
     - Move `restore_windows_order('after-install')` to after the first stock pause/pin.
     - Boot that first stock start without BootNext.
     - Make the next Windows marker an unattended boot (no BootNext) that requires Windows first in BootOrder.
   - All 11e/11f rules stay strict. If the new timing shows a firmware change they don't cover, stop and report.

3. **BootNext is checked, not skipped (review finding 3).**
   - The harness records every BootNext it writes: the value, and which boot it's for. After that boot, BootNext must be gone (consumed).
   - Each of these is a failure:
     - any other BootNext appearing
     - a malformed value
     - an unknown destination
     - a BootNext still present at a Windows-default checkpoint
   - **Replay** the new check over every retained 11k capture (probe and full, both orders); it must pass there.
   - **Negative tests:** an unknown destination, a leftover BootNext at a Windows-default checkpoint, and a malformed length.

4. **The owner's switch block is `switch.sh` (review finding 4).**
   - The INSTALL switch block becomes exactly `os/release/switch.sh` with the release reference filled in, including its account checks and the pending-deployment guard.
   - Add a test that the two match, like the existing pin block test.
   - CI already runs `switch.sh`, so the owner then runs the rehearsed script.

5. **Budget.**
   - 11k closed at 611/750 minutes and 5/5 full runs. Raise the cap to **900 minutes** on the same ledger (same start).
   - The org had about 1,200 of its 2,000 October minutes left on 2026-10-24; the other repos only run short privacy checks.
   - Allow exactly **one Part B qualification run** (below), after one fresh probe on the same head. No other full run.
   - Plan: probe 42 + B run (reserve its job timeout, at most 130) + closing 14, so at most 797. If the guard can't fit it, stop and report. Keep the 11k retry unchanged.

## Then

1. Update the stage walk-through before any dispatch: the new restore timing, the unattended Windows marker, the BootNext rule and the selector.
2. Run a fresh probe on the new head.
3. Run one **Part B qualification run**, in one drive order (protected disk second, as in 11k's B):
   - install
   - the first stock start with Linux as default (including the init reboot), the installed keyboard, and pause/pin
   - Windows first in firmware, then an unattended Windows marker and a detached marker
   - then B: pin, signed switch, AresOS booted, menu selection of the recorded stock entry (or the authorized fallback), recovered stock, promote, and a second unattended stock boot

   Every protected-disk, NVRAM and BootNext audit applies at every stage. It doesn't repeat rollback or Windows-default undo, which passed in both orders in 11k.

All stop rules hold.

## Acceptance

11c's acceptance, plus an "11l" REPORT section with:
- the item 1 verification results (versions and source links)
- each of the four fixes with its regressions, and the BootNext replay over the 11k evidence
- the B run's rendered menu frames, OCR and selection, visually inspected
- Part B green, or a clearly stated blocker
- the budget table
- what this round did not re-rehearse: the new Windows-first timing ran in one drive order only, while 11k's both-order evidence used the earlier timing

Push (fast-forward only). Mark PR #11 ready for review if acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
