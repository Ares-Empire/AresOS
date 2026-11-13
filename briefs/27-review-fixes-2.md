# 27: review fixes, round 2 (one stop routine, uninterruptible and bounded)

Follow-up to `briefs/27-review-fixes-1.md`. Review: `reviews/27-first-update-release/REVIEW-2.md` (gpt-6-astra high on `f708c53f`, CHANGES-NEEDED: 1 blocking, 2 should-fix). **Builder: the same Claude agent (Opus).** Next: a fresh reviewer checks only these fixes and what they touch.

Settle the stop path by construction this round. **One stop routine**, entered from every way the update step can end without success. Once it starts, it runs to the end, and every wait in it has a bound.

## 1. Blocking: the stop routine can be cut short

- **Repeated Ctrl+C** (REVIEW-2 #1). `stop_group()` runs before SIGINT is ignored, so a second Ctrl+C during the 15 s TERM grace skips SIGKILL and the group check. Then `abandon_update()` meets the surviving bootc in `idle()` and exits before restoring the masks.
  - From the first interruption (or timeout, or failure) until the stop routine ends, defer or ignore SIGINT, SIGTERM and SIGHUP.
  - Print one line first, for example "Stopping the update safely; this takes up to N seconds. Don't close this window." N is the real worst case.
- **Closing the window** (integrator). The update now runs in its own session, so a terminal hangup no longer reaches bootc. If the tool dies of SIGHUP or SIGTERM, bootc stages on alone with the masks removed. During the update step, SIGHUP and SIGTERM to the tool must start the stop routine, like Ctrl+C. Write output so that a closed terminal doesn't crash the routine (EPIPE/EIO on stdout).
- **A failed shell** (#1). A non-zero exit skips `stop_group()`. Run the routine on every unsuccessful end: a non-zero exit, a timeout, an interrupt, an exception. Prove the group is empty before reconciling (`os.killpg(pgid, 0)` → ESRCH, or a /proc scan). `communicate()` returning doesn't prove it.

## 2. Should-fix: restore the masks even when reconciling fails (#2)

Attempt and verify the mask restore independently of reconciling deployments (status reads, `cleanup --pending`, comparisons), in a `finally` or the equivalent. Report both errors when both fail. Claim a clean stop only when every check passed.

## 3. Should-fix: delete only what this update staged (#3)

Before `rpm-ostree cleanup --pending`, all of these must hold:
- both status views agree;
- the booted, retained and pinned deployments are unchanged;
- there is exactly one new, unpinned staged deployment, and it matches this update's target digest.

Otherwise don't delete anything. Still restore the masks (a foreign staged deployment then can't finalize), then STOP with "get help; do not reboot" and diagnostics.

## Tests and proof

- Through the real runner (`Host.script()`, real bash and update.sh, fixture commands):
  - a second and a third Ctrl+C during the TERM grace;
  - SIGHUP and SIGTERM to the tool mid-update;
  - a shell that fails while a real background child survives;
  - a status read that fails after a kill (the masks still come back);
  - a foreign staged deployment (refused, nothing deleted, masks restored).
- Make the surviving-group case a real process, not an injected `Unstoppable`.
- Revert proof that reverts the behaviour, not the constants the tests patch, and names the failing assertion for each fix.
- Keep REVIEW-1's three cases passing.

## Then

1. Regenerate the bundle, the fingerprint and every pin and record that names it (replacing `e4dedbb6…`), then the pending list, the walk and the focused WSL set (detached, `pkg27-` names, ≥ 4.5 GB).
2. **Don't push until run 8 (43160633763, head `f708c53f`) has a result.** Run 8 still proves every other step.
   - If run 8 passes: push, cap 10, dispatch **run 9** on the fixed head. Step 6 of `27-rehearsal-fixes-1.md` runs on run 9.
   - If run 8 fails on a new step: stop and report with the evidence and your proposed fix; don't dispatch.
3. Message the integrator at push, at dispatch and at the result.

`AGENTS.md` applies. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
