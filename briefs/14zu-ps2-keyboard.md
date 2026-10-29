# 14zu: Move the VM's typing keyboard off xHCI (i8042/PS-2); watch xHCI health; local now, CI on 1 November

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zt still apply, with the change below.

## Integrator decision on the 14zt PLAN-GAP

Qualification 15's screen shows the xHCI controller declared dead (`not responding; assume dead`, `HC died`) and USB `1-1`, the QEMU USB keyboard, disconnecting. So the keyboard could no longer type, and strict readiness rightly refused. Why the controller died is unproven: a CI host under load can make emulated xHCI commands time out.

Typing must not depend on the controller that also carries the hot-plugged tools stick. A laptop's internal keyboard is normally i8042 (PS/2). So:

1. **Typing keyboard:** use the guest's **i8042 / PS/2 AT keyboard** for all physical typing (QMP `send-key`/`input-send-event`), and remove `usb-kbd` from the VM.
   - Verify that the machine type provides i8042, and that the guest sees "AT Translated Set 2 keyboard".
   - Confirm the qcode-to-keycode mapping is identical for the VT keymaps (de, us, us-intl). If any key differs, map it explicitly and test it.
   - The tools stick stays on xHCI.
2. **Counters and observers:** point the 14zo event counter and every keyboard-device check at the AT keyboard's `/dev/input/event*`, identified by name and bus, never by a fixed number.
3. **xHCI health:** at every stage boundary, and on any readiness timeout, check the guest's kernel log for xHCI death or disconnect messages since the stage began (counts and message classes only). If the controller died while the tools stick was attached or needed, STOP immediately with a clear message, instead of waiting out a readiness deadline.
4. **Typing timing:** keep the 30 ms holds and gaps of at least 120 ms. Re-check against the PS/2 queue (record QEMU's queue size from its source).
5. **Local tests:**
   - device selection
   - counter on the AT device
   - xHCI-death detection from the retained qualification 15 lines
   - the healthy walk through every remaining stage
6. Commit locally, with the pinned local gitleaks. **No push and no dispatch before 1 November.** On 1 November, I'll resume you with fresh budget settings (free minutes, the reserve back to 150).

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
