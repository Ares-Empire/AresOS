# 20, restore lock: no stale app state while a restore waits, and the owner oracle re-pinned

The optional owner-state oracle (`control-owner-oracle.yml`, board #185) was re-captured on main after PR #27 (the
Chrome tool) and PR #68. Two analysis steps traced every difference between its pin and the capture to a commit.
Their record is `reviews/19b-owner-state/REPIN-185-PROGRESS.md`, sections "Done" and "Trace (step 2)". Most
differences are intended. Two are owner-visible regressions from PR #27, both only during a restore lock, and two
are oracle-model problems that must be fixed before a re-pin.

**What a restore lock is.** When the service finds that its log is older than the committed state (after a crash, or
after the owner restored an older state), it refuses every app action until the owner confirms the restore
(`control_restore_confirm`). Since PR #27, `control_pending`, `control_notices` and `chrome_notices` are answered
during the lock, so Chrome's warnings stay visible. Chrome's rows come from the committed journal; other apps' rows
don't.

**Rules.** `briefs/20-final-fixes.md` and `briefs/20-main-fix.md` still apply:
- the files not to touch, and no persistent extension storage;
- never name the owner's mail provider; repo-relative paths only;
- no force-push, no `--no-verify`; agents never push to main.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac.** Browser and oracle runs happen
only on GitHub's Linux runners. Locally, run only plain-Python and Node tests that start no browser.

## R1. During the lock, no app's old state is shown as current

**The bugs (trace classes C3, C4 and the side note).**
- **C3.** `control_pending` lists Mail operations from the pre-restore working state. For example it says "reserved:
  Awaiting exact approval; nothing submitted" although the committed journal is newer; after
  `control_restore_confirm` the same operation shows `unknown`. The reply carries `restore_required: true` and every
  action stays refused, so nothing unsafe can follow, but the owner and Claude are told something untrue. Before
  PR #27 the owner saw only the refusal. #27's security review D called this hazard blocking for Chrome, which is
  why Chrome's rows moved to the committed journal.
- **C4.** During the lock, the reply's continuation says "N more notices: read `mail_filing_notices`", and that
  call is refused with `restore_required`.
- **Side note.** During the lock, `control_pending` runs Mail's live read-only server checks
  (`resolve_checks`, `resolve_sent_checks`) against the pre-restore state. The lock is meant to refuse app access;
  the checks' result writes are already refused.

**Fix.** While `store.locked`:
- `control_pending` and `control_notices` show no row or notice from an app other than Chrome as current.
  - Preferred: such apps are reported as unavailable until the restore is confirmed. That is the state before PR #27,
    plus Chrome's current warnings. Reuse the wording and shape of the existing `unavailable` replies in
    `engine.py`.
  - Deriving Mail's rows from the committed journal is acceptable only if it is small and as well proven as Chrome's
    (`control/aresos_control/chrome/committed.py`). Say which you chose and why.
- No reply points to a refused route. Any continuation must name a call the lock allows, or be left out.
- No Mail server check runs.
- Chrome's committed-journal rows and notices are unchanged, and so is everything outside the lock.

**Tests.** For each of the three calls under the lock, with stale Mail rows and notices present:
- nothing stale is shown;
- every continuation names an allowed call;
- no IMAP or SMTP call happens (use the existing fake transports);
- Chrome's rows are still shown;
- after `control_restore_confirm`, the normal reply comes back.

Removal probes in `reviews/20-chrome/mutation-audit.py` (prefix `restorelock-`), all rejected.

## R2. The oracle's model, then a capture and a re-pin (completes board #185)

1. **C2, oracle drift.** Under the lock, the oracle (`control/owner_state_oracle/`, `permitted_status`) must allow
   `allowed` for `control_pending`, `control_notices` and `chrome_notices`, and `restore_required` when such a read
   tries a write.
2. **D, a hidden gap.** In the oracle's full-disk simulation, a failed close of a read-only file (the Chrome reader's
   journal close) must not make `storage_limit` an allowed answer for that call. Today it hides 83 real gaps from the
   pin. Fix it in `permitted_status` or in the exhaustion injector, whichever is narrower. Say which.
3. **Keep the expectations for C3 and C4 as they are.** With R1 in, those cases must match the expectation, as the
   pin's M14 "rows missing" gaps did, or close.
4. **Capture.** Dispatch `control-owner-oracle.yml` on this branch. Regenerate the compact ledger as
   `reviews/19b-owner-state/KNOWN-GAPS.md` shows.
   - Re-run the trace's classification. The scripts are in the ignored `.work/185/` of the
     `pkg/19b-oracle-repin` worktree; copy them, don't commit them.
   - **Only intended classes may remain:**
     - A: new fault sites at the new index;
     - B: more cleanup cases;
     - C1: pending answered during the lock;
     - E: renumbering from the new ID draw;
     - C3, C4, C2 and D, each matching its new expectation.
   - Anything else stops the step and goes to the lead.
5. **Re-pin.** Write the new `KNOWN-GAPS.json`. Add a section to `KNOWN-GAPS.md` with the counts, SHA-256, the
   classes and their commits.
6. **Prove it.** Dispatch once more on this branch: it must be green.
7. **Dispatch limit:** at most 3 dispatches in all.

## Runs and order

- **Order:** R1 (step 1), then R2 (step 2). Each step is a fresh agent.
  - Each fix comes with tests and probes and the full local preflight.
  - The driver is `.work/20-restore-lock/preflight.py` (repo-relative paths in its record). Record it in
    `reviews/20-restore-lock/records/`.
- **Builders:** step 1 on Claude Fable, because it changes what the restore lock shows: a safety mechanism. Step 2
  on Claude Opus, because the oracle change is narrow and the trace already names it.
- **Branch and PR:**
  - Work on `pkg/20-restore-lock` and push it. Every commit carries `[skip ci]`.
  - **Don't open the pull request.** The lead opens it after the reviews, and that starts `Control Chrome`, Mail,
    base and boundary on the PR.
  - Pull-request path filters see the whole PR's diff, so every later push without `[skip ci]` starts them again.
- **Runs:** `control-chrome.yml` at most 2 on the PR, preferably 1. `control-owner-oracle.yml` as in R2.
  - If a run fails, diagnose it and report. Don't retry.
  - Latency jobs are a special case. If the only red job is a latency p95 miss, report the H5 stages of its slowest
    samples (see `reviews/20-main-fix/REPORT.md`). The lead decides.
- **Before "ready":** a fresh package review and a fresh security review (the restore lock is a safety mechanism).
  The lead merges.
