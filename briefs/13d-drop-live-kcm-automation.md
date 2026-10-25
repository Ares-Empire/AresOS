# 13d: Qualify the installed system without automating the live KDE settings

Follow-up on branch `pkg/13-keyboard-layout` (PR #12, draft). Read the 13c section of the REPORT. Briefs 13 to 13c still apply, plus the changes below.

## Where 13c stopped

The new private release is built, signed and published, with only the two keyboard files different. The native suite passed. Probe 40159515328 then stopped in the live-session KDE settings automation, `live-kde-select` (`KDE normal settings control unavailable: German`), with the Bazzite Portal window in front. That is a UI-fixture failure: nothing was installed and every disk and firmware audit stayed clean.

## Integrator decision

1. **Drop the live-desktop KDE settings automation, and the live KWrite typing test, from the VM qualification.** That step only sets the layout the owner types with while installing. It doesn't decide the installed system's layout; the installer's keyboard choice does. It stays where it belongs: an owner step on the real laptop, already in INSTALL §4 step 1 ("type `y z / - " $ ä ö ü` in a text editor"), and on the release gate's physical/followability list. Record that change in the REPORT and the release gate. Don't delete the fixture code; leave it unused and say so.
2. **Everything else stays.**
   - The installer's keyboard choice in the real Web UI.
   - The fix for both starting states, `de` and an injected `us`.
   - The diagnostic at the argument-writing boundary.
   - On stock, AresOS and the backup after rollback: `/proc/cmdline` and the loaded console map.
   - tty3 login and password sudo with the layout-sensitive password.
   - Physical-key typing in foot.
   - The layout change and back.
   - Every disk, NVRAM and BootNext audit.
3. **Budget.** Same ledger (104/380 used). Allow **one fresh probe** and then **one qualification run**, and a second qualification only if a fresh guard shows it fits. No image dispatch or publication (the single publication is used). If the guard can't fit the plan, stop and report.

## Acceptance

13c's acceptance, minus the live-desktop automation, plus the release-gate note moving it to the laptop checklist.

Push (fast-forward only). Mark PR #12 ready for review if acceptance is met. Don't merge. Never make anything public.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
