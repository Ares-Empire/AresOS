# 20, popup race: cross-site popups that Chrome sets up twice, and the slow-load fallback

Two product bugs in the Chrome tool (PR #27, on main since 2026-11-14). A diagnosis agent found them from
`Control Chrome` run 43671248371 (`fixtures (policy, recheck2)`, "GROUP 8 closing or releasing an opener ends popup
control and clears badges"). Its evidence is in this brief's review folder, `reviews/20-popup-race/DIAGNOSIS.md`.
Both bugs fail safe: nothing is sent, and no popup is left half under control. One costs Claude a popup it should
control; the other shows the owner a misleading message.

**Rules.** `briefs/20-final-fixes.md` and `briefs/20-main-fix.md` still apply: the files not to touch, no persistent
extension storage, never naming the owner's mail provider, repo-relative paths, no force-push, no `--no-verify`.
Agents never push to main. **Never start, read or touch Chrome, Chromium or any browser profile on this Mac.**
Browser tests run only on GitHub's Linux runners. Locally run only plain-Python and Node tests that start no browser.
Tab groups, the hold window, the ceilings and the sample counts stay unchanged.

## P1. A duplicate breakpoint from Chrome's replay no longer drops the popup

**The bug.** Claude's click opens a popup to another site. While the extension sets it up, the site's first document
can commit in a new renderer while `Debugger.setBreakpointByUrl` still has no reply. Chrome then re-sends that
unanswered command to the new renderer, and the breakpoint also travels there with the session's state. V8 refuses
the second copy with "Breakpoint at specified location already exists."
- `prepareTarget` throws (`background.js` about :90), `admitTab` releases the popup, and `createdTarget` logs
  `reader_error`.
- The popup stays open and uncontrolled, and Claude is not told. In that job it happened to 1 of 7 cross-site popup
  admissions.

**Fix.** In `prepareTarget`, handle only V8's exact duplicate-breakpoint error, on a session the extension has just
attached, where `prepareTarget` is the only thing that sets breakpoints. Re-arm once: `Debugger.disable`, then
`Debugger.enable`, then `Debugger.setBreakpointByUrl`, so the breakpoint id is one the extension knows. Any other
error, or a second failure, fails closed as today. This is a single fixed response to a named Chrome behaviour, not a
retry loop.

**The point that matters most: the path must match what the page actually did.** In the failing run the new document
loaded with no `Debugger.paused`. So by the time the duplicate error arrives, the page's scripts may already have run
without the guard.
- After the re-arm, admission must take the late path (the reload rule before Claude's first act) whenever the
  document may have run past the breakpoint location.
- It may take the early (`document_start`) path only when the extension holds that document paused at the breakpoint
  it set.
- Show in the tests that a document which ran before the re-arm never counts as early.

**Weigh one alternative before you build.** The breakpoint id may be adoptable instead of re-armed. The diagnosis
(section 4) rejects keeping an unknown id because later pages would pause on an orphan breakpoint. But the new
renderer reports the id in `Debugger.breakpointResolved`, and `setBreakpointByUrl` ids are fixed by URL and line.
- Pick whichever gives the correct path and leaves no orphan breakpoint, and write down why in `PROGRESS.md`.
- Don't rely on V8's id format unless a test pins it.

**Tests.**
- Extend `swappedPopupFixture` (`control/chrome_tests/background.test.mjs`) with a one-time duplicate reply.
  - With one duplicate, the popup is admitted, on the late or early path as the order gives, and there is no
    `reader_error`.
  - With a second duplicate, admission fails closed with nothing left behind: debugger detached, guard disposed,
    no badge, no `popup_admitted`.
  - Any other error text fails closed as today.
- Add removal probes, all rejected.

## P2. The slow-load fallback says what happened and isn't logged as an admission

**The bug.** When a popup's first `Page.enable` stalls for more than 5 s, which happens when the debugger attached
while a cross-document navigation was pending, `initializeTab`'s fallback (`background.js` about :437):
- treats the stall as an owner dialog: it sets the dialog handoff and needs-reload, detaches, and returns normally;
- lets `admitTab` write `popup_admitted` and show the opener's `POP` badge although no debugger or guard is attached;
- makes a later act say "Please answer the dialog yourself" although no dialog exists.

Acting stays safe: `recoverOwnerDialog` re-attaches on the late path, and the reload rule applies before the first
act.

**Fix.**
- The `popup_admitted` line records `owner_dialog: true` when the fallback ran, or gets a separate line for the
  handoff. The harness's `admittedAfter` (`control/chrome/ci/popups.mjs`) requires it false.
- When no JavaScript dialog is actually open (check `Page.javascriptDialogOpening` state or the extension's own dialog
  record), the message says the page is still loading and Claude should try again, not that the owner should answer
  a dialog.
- Keep the fail-closed behaviour exactly as it is.

**Tests.** Node tests for both the stall without a dialog and the stall with a dialog, the message for each, and the
log flag. Add removal probes.

## P3. Claude learns when a popup it opened isn't under control

**Optional, only if small.** After P1 this should be rare. Where a click opened a popup that ended up uncontrolled
(admission failed or refused), the click's result names it, so Claude can `take_tab` it rather than not knowing. If
this is more than a few lines in the click path, leave it to `linux-tools`' brief 28a and say so.

## Runs and order

- **Order:** P1, then P2, then optionally P3. Each comes with tests and probes and the full local preflight
  (`reviews/20-main-fix/records/final-local-496018a5.json` shows the driver and its parts). Record yours in
  `reviews/20-popup-race/records/`.
- **Builder:** Claude Fable. P1 changes the fail-closed admission path, and choosing between re-arming and adopting
  the id needs a careful reading of Chrome's behaviour.
- **Branch and PR:** work on `pkg/20-popup-race` and push it. Commit messages carry `[skip ci]` until the lead says
  otherwise. **Don't open the pull request: the lead opens it after the reviews, and that starts the first runs.**
- **Runs:** at most 2 `control-chrome.yml` runs and 2 `control-chrome-qualification.yml` runs, on the PR. The whole
  `control-chrome` budget is about 280; about 277 are used after PR #68 and its run on main.
  - **Pull-request path filters see the whole PR's diff.** So every push to an open PR without `[skip ci]` starts
    both Chrome workflows again, even a docs-only push.
  - All `recheck2` shards and every popup row must pass in both installs.
  - If a run fails, diagnose it and report. Don't retry.
  - Latency jobs are a special case. If the only red job is a latency p95 miss, report the H5 stages of its slowest
    samples (`store_write`, `journal_fsync`, `bridge_round_trip`, from the artifact's `latency-service.jsonl`; see
    `reviews/20-main-fix/REPORT.md`). The lead decides on a re-run of that one job.
- **Before "ready":** a fresh package review and a fresh security review (P1 touches popup admission, the fail-closed
  path). The lead merges.
