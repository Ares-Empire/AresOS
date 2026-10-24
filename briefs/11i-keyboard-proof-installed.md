# 11i: Read-only keyboard proof before install, real German check after, then finish A and B

Follow-up on branch `pkg/11-two-disk-rehearsal` (draft PR #11). Read the "11h" section of `reviews/11-two-disk-rehearsal/REPORT.md`. Briefs 11c–11g still apply, plus the changes below. 11h's "poll up to 15 seconds" plan is withdrawn.

## What 11h found

The pinned installer's `convert_layouts()` restores the live layouts and keymap but passes empty X11 options. Any non-empty live options are lost permanently, so no amount of waiting can make our `before == after` check reliable. Full 3's actual cause stays unproven: a race or a concurrent writer is still possible. Either way, this is a property of upstream Anaconda's **live session**, and the installer itself runs the same conversion during a real installation (`KeyboardInstallationTask`). Our pre-install proof was asserting something the product doesn't promise and we don't depend on.

## Integrator decision

1. **The pre-install keyboard proof becomes read-only.**
   - Read the module's committed `XLayouts`, `VirtualConsoleKeymap` and `LayoutSwitchingOptions` over the installer bus.
   - Read the live localed tuple (keymap, layouts/variants, options) for the record only.
   - Keep the existing source-identity checks: the installation task still uses the same resolver and writer (`get_missing_keyboard_configuration`, `write_vc_configuration`), and the source SHA matches the extracted ISO module.
   - Require `XLayouts == ['de']` and a console keymap of `''` or `'de'`, as now.
   - Don't call `get_missing_keyboard_configuration`, `convert_layouts` or any other localed setter before installation.
   - Remove the `live_configuration_restored` requirement, and record why in the REPORT (11h source finding). Keep `module_configuration_unchanged` (read the module settings before and after the proof).
2. **The real check comes after installation, in each order.** From the **installed system**, read and require:
   - `/etc/vconsole.conf` contains `KEYMAP=de` (or `KEYMAP="de"`)
   - `/etc/X11/xorg.conf.d/00-keyboard.conf` has `XkbLayout "de"`
   - its options equal the module's recorded `LayoutSwitchingOptions` (an empty list means no `XkbOptions` line, or an empty one)

   Use the target's deployed `/etc` offline, or the first installed stock boot's root shell, whichever is more direct and already audited. It must be the installed system, never the live one. Any mismatch is a **stop**: wrong keyboard on the owner's laptop is a product failure.
3. **Regressions:**
   - The proof makes no localed setter calls. Fail if one is reached (mock it).
   - Wrong module layout or keymap fails.
   - The installed check passes for German and fails for a non-German keymap, a non-German X11 layout, a missing file, and options that differ from the module's.
   - The `KEYMAP=de` and `KEYMAP="de"` forms both pass.
4. **Budget guard:** apply 11h's **5 full runs**, which 11h deferred. The cap stays **750 minutes** on the same ledger.

## Then

1. Update the stage walk-through if anything changes, before any dispatch.
2. Run a fresh probe on the new commit.
3. Run one complete full run: **Part A** in both orders, including 11g's installed stock pause/cleanup/pin and the new installed keyboard check, then **Part B**.

All stop rules hold.

## Acceptance

11c's acceptance, plus an "11i" REPORT section with:
- the read-only proof and the reason the live-restore assertion was dropped
- the installed keyboard result per order
- everything 11g's acceptance lists

Push (fast-forward only). Mark PR #11 ready for review if acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
