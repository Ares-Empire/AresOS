# 11f: Let the Linux entry move, give the full run enough time, then finish A and B

Follow-up on branch `pkg/11-two-disk-rehearsal` (draft PR #11). Read the "11e" section of `reviews/11-two-disk-rehearsal/REPORT.md`. Briefs 11c, 11d and 11e still apply, except the two changes below.

## 1. The 11e order rule was the integrator's mistake

11e rule 5 said "entries that aren't firmware-owned keep their relative order in BootOrder". That was too broad. It contradicts 11c rule 2 ("an OS-made change may only add **or reorder** a separate Linux entry on the target's own ESP") and the guide's own step: the installer puts the new Bazzite entry first, and the guide then puts Windows first again (`restore_windows_order()`). Moving Windows ahead of the Linux entry is the intended behaviour, not a regression. Stopping on it was correct.

**Integrator decision: replace 11e rule 5's order bullet with this.**

1. **The Linux target entry's BootOrder position is not judged.** This covers every entry that qualifies under the existing Linux rule (names only the target's own ESP and the Fedora shim/GRUB loader). The installer, shim's fallback, bootupd, or the guide's Windows-first step may each move it. Record every move in the stage record (old index → new index, full BootOrder before and after).
2. **All other entries that aren't firmware-owned keep their relative order.** Windows, UiApp, the EFI Shell and any other fixed entry: comparing their order with Linux and firmware-owned entries removed must give the same sequence before and after.
3. **Windows-first stays strict.** Windows stays byte-identical, keeps its number, stays in BootOrder, and is **first** at every checkpoint where the guide says Windows is the default (after each `restore_windows_order()`). Where the guide expects Linux first (right after installation, before the owner's step), Linux-first is fine.
4. **`restore_windows_order()` itself is checked:** its output must be exactly Windows followed by the previous BootOrder without Windows. Add a unit test.
5. Everything else from 11c/11d/11e is unchanged: the firmware device-set rule, Linux ESP/loader checks, takeover rules, protected-disk bytes/GPT/EFI/zero-write checks, token rules.

**Regressions:**
- Replay full run 1's real stores (`protected-first-install` → `after-install-without-linux`). They must pass with exactly: the DVD auto removal, the target auto removal, and the Bazzite entry `Boot000A` moving behind Windows (recorded as a Linux position change).
- The 11e replays (11b/11c first order, 11d both orders) must still pass with the same events.
- Each of these must fail:
  - Windows not first at a Windows-default checkpoint
  - UiApp or the Shell moved ahead of Windows, or swapped with each other
  - a non-auto, non-Linux entry added, removed or changed
  - a "Linux" entry that names the protected disk's ESP or a non-Fedora loader, including one that also moved
  - `restore_windows_order()` producing anything other than Windows + the old order without Windows

## 2. The full run doesn't fit its time limit

Full run 1 needed about 11 minutes of setup and about 27 minutes for one installation alone. A complete full run is both orders (install, switch, policy, tty3, rollback, undo, three Windows markers each) plus Part B: roughly 105 to 120 VM minutes. The VM step allows 80 and the job 110, so a complete run would time out partway.

- From the probe 2 and full 1 step timings, estimate each remaining stage and write the estimate into the REPORT.
- Raise the **full** job's and VM step's `timeout-minutes` to cover that estimate with about 30% margin, at most **180** for the job. Leave the probe's limits as they are.
- Keep it **one** full job. Don't split the orders across dispatches.

## 3. Budget: corrected premise, new cap

The 330-minute cap assumed the user account's remaining minutes. Since the move, this repo bills to the **Ares-Empire organisation's** own allowance. On 2026-10-24 the owner's org billing page showed **248 of 2,000** included Actions minutes used for October, resetting on 1 November. (The integrator read this page; the job token can't read org billing, so record it as integrator-reported.)

**New allowance:** the same ledger (same start, nothing resets) with a cap of **600 rounded minutes** and still **3 full runs** in total. Update the guard constants and the budget regression. That leaves room for one probe and one complete full run, plus one more attempt if needed, while keeping over 1,000 org minutes for the other repos.

## 4. Before spending minutes: walk the remaining stages

Before any dispatch, do a zero-cost walk-through and put it in the REPORT. For every stage still to come (both orders and Part B), list the NVRAM transitions you expect: firmware auto options added, removed or relabeled as disks attach and detach; shim fallback or bootupd creating or moving Linux entries; `BootNext` set and consumed; the Windows-first steps. Also list the rule that accepts each one.

If a transition you can foresee would fail the rules, **stop and report it as a PLAN-GAP before dispatching.** Don't widen any rule yourself.

## Then

1. Run a fresh probe on the new commit (the probe-before-full rule still holds).
2. Run one complete full run: **Part A** in both drive orders (switch, policy, tty3, rollback, default undo, detached Windows after install and after undo, audits and NVRAM diffs at every stage), then **Part B**.
3. All stop rules still hold. Firmware or OS behaviour the rules don't cover means stop and report a PLAN-GAP.

## Acceptance

11c's acceptance, plus an "11f" REPORT section with:
- the order-rule change and its regressions
- the stage walk-through and time estimate
- the per-stage firmware and Linux-position events
- the gate → evidence table
- the minute ledger

Push (fast-forward only). Mark PR #11 ready for review if acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
