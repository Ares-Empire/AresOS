# 14c: The tools stick goes in after Linux is up and out before every restart

Follow-up on branch `pkg/14-owner-tools` (PR #13, draft). Read the 14b PLAN-GAP in `reviews/14-owner-tools/REPORT.md`. Briefs 14 and 14b still apply, with the change below.

## Integrator decision

The gate was right: a stick that is present while the firmware starts gets an automatic boot option, and widening the firmware audit for it isn't allowed. **Don't widen it. Change the route so the firmware never sees the stick.**

1. **The owner's route:**
   - The tools stick goes in only after Linux has started and the owner is signed in.
   - It comes out before every shutdown or restart, once the tool says it's safe to remove.
   - In Windows, the stick is plugged in only for the restore and the copy, then ejected and unplugged before any Windows comparison (record B already requires the USBs to be absent).
   - Where the tool needs the stick, have it find and mount the stick itself by its label and the bundle manifest, and unmount it when done. That way nothing depends on KDE's automounter, and the same steps work later on AresOS (labwc).
2. **If the owner forgets** and restarts with the stick in: the guide says nothing breaks. Never pick the stick in the F12 menu; unplug it and continue. The firmware may list the stick, but Windows stays first.
   - On the laptop, a data-only stick present at power-on is physically untested. Mark it so, and add it to the laptop-side gate items.
   - Don't add any rule that accepts a USB firmware entry.
3. **CI matches the route:**
   - **Attach:** after the guest has booted and signed in, the harness hot-plugs the virtual tools stick by QMP (`device_add` of USB storage on the controller that is already present). Before attaching, it checks the backing image's hash against the bundle the Windows step produces.
   - **Detach:** after the tool has unmounted the stick, and before any reboot, the harness removes it (`device_del`).
   - **Audits:** the firmware audit at every boot then sees no USB storage. All NVRAM, BootNext, Windows-first, protected-disk and detached-device rules stay exactly as they are.
   - **Proof:** record evidence that the guest saw the hot-plugged stick, and that it was gone before each reboot.
4. **If any stage needs the stick across a reboot,** stop with a PLAN-GAP before dispatch. Don't widen a rule.

## Then

Continue brief 14 from your prototype. Finish and ship:
- the bundle, the Windows copy step and the Linux commands
- every-refusal shim tests (zero mutations)
- `prepare` with its rerun, plus the record export
- the guarded `layout`, and command/bundle equality

Then run the local whole suite, the native CI suite and the remaining host walk. Then the ledger checks, the probe and the qualification, as brief 14 says. For the layout trial, use your proposal: plain `us` for the failure and revert, and US International for the successful change with the unchanged umlaut password. Record which map each step loads.

Everything else in briefs 14 and 14b stands. Mark PR #13 ready for review when acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
