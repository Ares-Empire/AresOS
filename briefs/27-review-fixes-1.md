# 27: review fixes, round 1 (the update's timeout path)

Follow-up to `briefs/27-rehearsal-fixes-1.md`. Review: `reviews/27-first-update-release/REVIEW-1.md` (gpt-6-astra high on `5335f8a4`, CHANGES-NEEDED: 1 blocking, 1 should-fix). **Builder: the same Claude agent (Opus).** Next: a fresh reviewer checks only these fixes and what they touch.

## 1. Blocking: a timeout or Ctrl+C skips the mask restore

`Host.script()` (`os/owner-tools/owner.py`) runs `os/release/update.sh` with `subprocess.run(..., timeout=1800)`. On a timeout, Python SIGKILLs the shell, so its `EXIT` trap never runs and `bootc switch` keeps running on its own. The tool says STOP, but both finalizers stay unmasked and staging may finish, so the update could still apply at the next restart. R13 stays as rollback; nothing is destroyed, but it breaks the all-or-nothing behaviour the owner accepted (JUDGMENT-CALL 11, board #175). A slow download on his Wi-Fi is a realistic way to reach 30 minutes. Ctrl+C has a similar race: Python kills the shell 0.25 s after the interrupt.

Fix it so the guarantee no longer depends on the shell surviving:
- **Run the update in its own process group** (`start_new_session=True`). On a timeout or KeyboardInterrupt: SIGTERM the group, wait a bounded time, SIGKILL the group, and reap it. No `bootc` may outlive the tool.
- **Reconcile from the real state afterwards, in Python.** Read `bootc status` / `rpm-ostree status`.
  - If staging didn't complete, or the tool is stopping anyway, **no staged deployment may remain**: remove it (`rpm-ostree cleanup --pending` or bootc's equivalent), and check that it's gone.
  - **Restore exactly the masks this run removed**, and check `systemctl is-enabled` says `masked`.
  - Then STOP with a plain message about what was cleaned up. Keep the shell's own trap for its ordinary failure paths; the Python step is the backstop and must be idempotent.
- If cleanup itself fails, say so plainly ("get help; do not reboot") and leave diagnostics, like the existing STOP messages.
- The booted deployment, the retained R13 and the pinned stock never change on this path. Assert it, as the success path does.
- **Tests through the real runner**, with a fake `bootc` that (a) hangs past the timeout, (b) finishes staging just as the timeout hits, (c) gets interrupted by Ctrl+C. Each must end with the masks restored, no staged deployment, no stray process and a STOP. Use a short test timeout, not 1800 s. Revert proof: with the fix reverted, (a) and (b) fail on the assertion you name.
- Update JUDGMENT-CALL 11's text: the restore now also covers a timeout and Ctrl+C. This fulfils what the owner accepted; it is not a new call.

## 2. Should-fix: util-linux suffixes

`os/ci/owner_login.py:41` accepts `2.41.6-rc1` or `2.41.6-custom` as 2.41.6. Match the whole version token (allowing only the documented trailing feature-list format), and add tests that refuse those suffixes.

## Then

1. Regenerate the tools bundle, the fingerprint and every pin and record that names it. The `daa31228…` fingerprint gets replaced; find every place.
2. Pending list, host walk, the changed modules, then the focused WSL set (fully detached, `pkg27-` names, ≥ 4.5 GB).
3. **Don't push or dispatch until run 7 (43148798803) has a result.** Run 7 is evidence for the route and the terminal_path fix either way.
   - If run 7 passes: push the fix, raise the update cap to 9, and dispatch **run 8** on the fixed head (the rehearsal must bind the new bundle). Step 6 of `27-rehearsal-fixes-1.md` then runs on run 8, not run 7. Run 7 goes into the report as a passing run of the previous bundle.
   - If run 7 stalls at R27's first boot again: stop and report with option B's diagnostics ready; don't dispatch.
4. Message the integrator at push, at dispatch and at the result.

`AGENTS.md` applies. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
