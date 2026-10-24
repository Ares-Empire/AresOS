# 11h: Make the keyboard proof wait for localed, then finish A and B

Follow-up on branch `pkg/11-two-disk-rehearsal` (draft PR #11). Read the "11g" section of `reviews/11-two-disk-rehearsal/REPORT.md`. Briefs 11c–11g still apply, except the changes below.

## What stopped 11g

Full 3 failed before installation in our own pre-install keyboard proof (`read_keyboard()` in `os/ci/installer_webui.py`), at `before == after` ("Conversion did not restore live settings"). The same check passed in both probe orders on the same source. Stopping was correct under the 11b probe rule.

That proof calls the installer's `get_missing_keyboard_configuration()`. It converts the layout through the live `systemd-localed` and then restores it. It then immediately re-reads localed through a fresh `LocaledWrapper`. If localed applies or publishes the restore with a delay, that immediate read can still show the converted value. Most likely this is a race in our diagnostic, not a product failure. The run didn't export the values, so that's unproven.

## Integrator decision

1. **Find out first, from the pinned installer source:**
   - Read the exact `LocaledWrapper` and `get_missing_keyboard_configuration` code in the ISO.
   - Say whether the conversion/restore is synchronous, and which calls it makes.
   - Compare with the full-3 transcript and say whether a race explains the failure. If the source shows something other than a timing race, stop and report a PLAN-GAP.
2. **Make the restore check settle, not loosen:**
   - After the conversion, poll localed's `(keymap, layouts/variants, options)` until it equals `before`, for at most **15 seconds**.
   - Record `before`, `after_immediate`, every polled value with timestamps, and the time to settle.
   - If it hasn't settled by the deadline, fail exactly as now, with all values in the transcript.
   - Every other assertion in the proof stays as it is: the German X layout, the console keymap `de`, the generated `KEYMAP=de`, the same resolver, the module configuration unchanged.
3. **Add the real evidence after installation**, if it isn't already there. In each order's offline target audit, read the installed `/etc/vconsole.conf` and the X11 keyboard configuration from the target's root, and require German. The pre-install proof is a prediction; this is the result.
4. **Regressions:**
   - a restore that settles after a delay passes and records its values
   - a restore that never settles fails with diagnostics
   - a wrong layout or keymap still fails
   - the installed-target check rejects a non-German keymap

## Budget

Same ledger and start. The cap stays **750 minutes**, and **full runs go to 5 in total**. 11g used about 330 minutes and 3 full runs, so this leaves room for a probe, a complete full run, and one more attempt.

## Then

As 11g:
1. Update the stage walk-through if anything changes, before any dispatch.
2. Run a fresh probe on the new commit.
3. Run one complete full run: **Part A** in both orders, including the installed stock pause/cleanup/pin from 11g, then **Part B**.

All stop rules hold. A different probe-covered failure in the full is still a stop.

## Acceptance

11c's acceptance, plus an "11h" REPORT section with:
- the installer-source finding
- the settle timings seen in the probe and the full
- the installed keyboard check
- everything 11g's acceptance lists

Push (fast-forward only). Mark PR #11 ready for review if acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
