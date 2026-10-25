# 13g: Review fixes — recovery layout, recovery title and the F12 steps

Follow-up on branch `pkg/13-keyboard-layout` (PR #12). Read `reviews/13-keyboard-layout/REVIEW.md` (head `1c4a249`, CHANGES-NEEDED). This is a **guide-only** follow-up: no harness, owner-script, image or VM change, and no Actions run beyond the normal privacy checks.

## 1. Recovery keeps the install-time layout (owner decision, 2026-10-25)

The review is right: a later layout change in AresOS writes only the running deployment's `/etc`, so the retained stock deployment keeps the layout chosen during installation. The owner decided **not** to make the backup follow: it stays frozen exactly as tested, which matches the earlier "backup Bazzite stays frozen" decision, and the laptop's keyboard is German anyway.

- INSTALL's layout-change section and EMERGENCY must say this plainly. The backup Bazzite always uses the keyboard layout chosen in the installer. Changing the layout in AresOS doesn't change the backup. At a recovery login, type the password as for that installer layout.
- Record the decision in the release gate and in a 13g REPORT section.
- Say honestly what the VM proved. It restored German before the rollback, so a "US in AresOS, then roll back" run was not performed. This behavior follows from bootc's per-deployment `/etc` and is source-verified, not runtime-verified.
- Don't add a mechanism that writes into the stock deployment.

## 2. Re-record the recovery title after any reorder

After the switch, the owner records stock as `Bazzite (ostree:1)`. Queuing a rollback swaps the titles before the reboot.

- At every step that reorders deployments (the switch, a queued rollback, anything else in the guides), add a step that resolves and records the stock title again, by checksum and serial, **before** rebooting.
- EMERGENCY must say that any reorder invalidates a previously recorded title.
- Keep the 13e/13f caution the owner approved: F12 → Windows on a failed first switch boot.

## 3. Spell out the F12 → Linux step

After §5, Windows is the firmware default, and the VM harness supplies the one-time Linux selection itself.

- At every affected step (switch, layout change, rollback, and any other "reboot and expect Linux" step), write the full sequence: sign in as `ares-recovery`, run the command, reboot, press F12, choose Linux.
- Windows stays the firmware default.
- The layout-change command needs the `ares-recovery` context, because daily `ares` can't use sudo.

## Checks

- Rerun the exact-block equality tests and `git diff --check`.
- Confirm `os/ci`, `os/tests`, `os/release` and the frozen runtime paths are unchanged against `1c4a249` and `2abc12e`.
- The privacy checks must pass on the pushed head.

Push fast-forward only. Keep PR #12 ready for review. Don't merge, and never make anything public.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
