# 14zy: Never query key state on the counting evdev fd; prove it deterministically; probe 29, qualification 18

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14zx still apply, with the changes below.

## Integrator decision on the qualification 17 STOP

Your diagnosis is accepted, and the counts fit it exactly. Presses stayed at 46 while releases went to 47, so the Return press vanished and its release was counted. That is what an `EVIOCGKEY` on the counting fd does: `evdev_handle_get_val` flushes that client's queued key events.

1. **Fix the observer.**
   - A counting fd is only ever read; it is never used for any query.
   - Run key-state checks (`EVIOCGKEY`, and any other getter that goes through `evdev_handle_get_val`: LED, sound, switch) on a separate open of the same device, which is its own evdev client.
   - Check every counter and observer in the harness for getters on a counting fd, and list each one in the report.
   - Keep the comparison exactly as strict as now: exact press and release equality, no tolerance.
2. **Deterministic test, real kernel:**
   - Create a uinput keyboard. Queue a press for a counting client, run the state query, then read the counting client. It must see the press.
   - Write it so it fails on the 14zx observer, showing the flush, and passes on the fix.
   - Run it in the probe's native checks if the runner has `/dev/uinput`. If not, run it inside the guest at the first stage, before any hidden typing. Record which one ran. Never skip it.
3. **Small cleanup:** the stale `native569` status label; make the label come from the real count.
4. **Then, as in 14zx:** local checks, one push through the privacy hook, then the probe and qualification on that same head, then STOP and report.
   - This is the third November round. If qualification 18 stops on console typing again, add the serial-run plan for the stages still left (final stock verification and the Windows checks), and don't build it until I answer.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
