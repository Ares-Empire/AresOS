# 27: review fixes, round 3 (the stop routine survives its own errors)

Follow-up to `briefs/27-review-fixes-2.md`. Review: `reviews/27-first-update-release/REVIEW-3.md` (gpt-6-astra high on `976d0334`, CHANGES-NEEDED: 1 blocking, 2 nits). **Builder: the same Claude agent (Opus).** Next: a fresh reviewer checks only these fixes and what they touch.

Review 3 confirmed the rest of round 2: signal deferral, closed-window output, mask restore independent of reconciling, the ownership check before `cleanup --pending`, the unchanged success path, the terminal tests and the `f85084b6…` pins.

## 1. Blocking: an error while stopping the step skips the stop and the mask restore (REVIEW-3 #1)

`Step.members()` decodes every `/proc/PID/stat` with `read_text()` and catches only `OSError` and `IndexError`. A process name is up to 15 raw bytes and can cut a multibyte character, so one such process anywhere on the laptop raises `UnicodeDecodeError`. `Step.stop()` builds its target list from `members()` before the first `killpg()`, and `stop_update()` calls `step.stop()` outside its protected blocks. The update then ends with bootc possibly still staging and both finalizers unmasked: the failure from reviews 1 and 2, reached through an exception instead of a signal. `wait()`'s final `members()` check can raise the same way.

Fix it so no error inside the stop routine can skip a later part of it:
- **Parse `/proc` as bytes.** Read `stat` as bytes and split after the last `b')'`. A process that vanished (`FileNotFoundError`, `ProcessLookupError`, empty read) is gone. Any other read or parse failure means the scan can't prove the step empty; it never raises out of the routine.
- **Signal first, scan after.** `stop()` sends TERM, and later KILL, to the step's process group before scanning for other members, so a scan problem can't delay the first signal.
- **Every part of `stop_update()` is protected:** stopping the step, reconciling, restoring the masks. An unexpected exception in any part (catch `Exception` there, not a list of types) is recorded and the routine goes on. A stop that can't be proved complete means no reconciling (nothing deleted). The masks are still restored and checked. Then STOP with every error and "Do not reboot; export records and get help".
- **Tests through the real runner:**
  - a real process with an undecodable name (for example, write invalid UTF-8 bytes to its `/proc/self/comm`), both outside the step and inside it, during a time limit, a Ctrl+C and a failed shell. The step is still stopped, the masks come back, and the outcome is right: a clean stop when everything was proved, otherwise a STOP with "do not reboot".
  - an exception injected into the scan and into `stop()` itself: nothing deleted, masks restored and checked, both errors reported.
- **Revert proof:** with the text decoding back, or with `step.stop()` back outside the protection, name the assertion that fails (expected: "the masks this run removed are not back").

## 2. Nit: the real-survivor test leaks its process (REVIEW-3 #2)

The cleanup gets a PID-file path inside `run_stopped()`'s temporary directory, which is gone before the cleanup runs, so the loop keeps running. Capture the PID before the directory goes and kill it after the survivor assertions. Check that no test leaves a process behind: after the module, nothing from it remains.

## 3. Nit: JUDGMENT-CALL 11 promises too much (REVIEW-3 #3)

In `REPORT-draft.md` (and wherever the text is copied): the masks are restored *and checked*, and "nothing changes at the next start" holds **only when every stop check passed**. Otherwise the tool says so and says not to reboot. This corrects the wording; it doesn't widen what the owner accepted.

## Then

1. Regenerate the bundle, the fingerprint and every pin and record that names it (replacing `f85084b6…`). Then the pending list, the walk and the focused WSL set (detached, `pkg27-` names, ≥ 4.5 GB).
2. Shake-out: UpdateStopTest with the new cases, 10 times in a row, all passing, once under parallel CPU load.
3. **Don't push until run 9 (43173190284, head `976d0334`) has a result.** Run 9 still proves every other step.
   - If run 9 passes: pull the branch first (the integrator pushed REVIEW-3 and this brief), then push, raise the update cap to 11, and dispatch **run 10** on the fixed head (pre-approved by the integrator). Step 6 of `27-rehearsal-fixes-1.md` runs on run 10. Run 9 goes into the report as a passing run of the previous bundle.
   - If run 9 fails on a new step: stop and report with the evidence and your proposed fix; don't dispatch.
4. With the dispatch, give the package's minute total against its 1200-minute cap.
5. Message the integrator at push, at dispatch and at the result. Don't mark PR #35 ready until the integrator sends review 4's verdict.

`AGENTS.md` applies. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
