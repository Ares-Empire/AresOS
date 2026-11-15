# Brief 20-popup-race: report

Brief `briefs/20-popup-race.md`, branch `pkg/20-popup-race`. Builders:
- P1 to P3: Claude Fable (2026-11-15);
- P4: the lead, `mac-aresos-control`, because it was found on main after the brief was written.

The lead made this report from the builder's `PROGRESS.md`, which follows unchanged below the summary.

## Outcome

- **P1, a replayed duplicate breakpoint no longer drops the popup** (`background.js` `prepareTarget`).
  - The fix: on V8's exact "Breakpoint at specified location already exists.", the extension re-arms once
    (`Debugger.disable` → `enable` → `setBreakpointByUrl`) and takes the returned id.
  - A second refusal or any other error fails closed exactly as before.
  - **Re-arm, not adopt.** The id may not be known yet when the refusal arrives, and adopting would rely on V8's id
    format. A pause from before the re-arm reaches the extension before `disable`'s reply, so before any id is
    known, and is resumed as foreign: the document takes the late path with the reload rule.
  - The security review verified that ordering against V8 and Chromium sources (`SECURITY-1.md`).
- **P2, the slow-load fallback says what happened.**
  - `popup_admitted` carries `owner_dialog`, and the harness's `admittedAfter` requires it false.
  - After the 5 s stall, the message says the page is still loading when Chrome's tab status is `loading` and the
    extension knows no dialog. Otherwise it keeps the dialog message.
  - The handoff, the reload rule and the error code are unchanged.
- **P3** is left to brief 28a. The click result has no popup correlation today, so naming an uncontrolled popup
  needs new plumbing.
- **P4, the qualification publisher**, found by main's first full run 43696892949:
  - `pair` reads the version after the browser's name. Reading the last word had turned every passing beta pair into
    an all-false entry (issue #74).
  - `notify` writes issues only, and the job drops `pull-requests: write`. It keeps one open issue per title,
    counting only `github-actions[bot]`'s own issues and comments, because the repository is public. It comments only
    on new text, and shows gh's own error.

## Reviews

Each review was by a fresh agent that didn't build the code.

| File | Reviewer | Range | Verdict |
|---|---|---|---|
| `REVIEW-1.md` | package, Claude Opus | `bdc16064..b6d223fa` | FIX 1: notify trusted same-title issues from anyone. FIX 2: absolute paths in a record. Both fixed. |
| `SECURITY-1.md` | security, Claude Fable | `bdc16064..b6d223fa` | SAFE. NOTE 3, the same as FIX 1, is fixed. NOTEs 1 and 2 are below. |
| `REVIEW-RECHECK-2.md` | package | `b6d223fa..2d27248c` | SAFE |

## Accepted residuals

- **Ordering between two message paths** (security NOTE 1, package review's "theoretical leftover risk").
  - Chrome delivers the pause event and the command reply to the extension by two different paths. They are ordered
    in practice (same browser thread, same worker) but not formally guaranteed.
  - The harm: a stale pause delayed past two further round trips would count a document that already ran as
    `document_start`. For popups that does no harm, because `popupNeedsReload` holds until the guarded reload. For an
    owner tab taken during a cross-process navigation, it would skip the reload.
  - **Why not the suggested hardening:** it would give the re-armed breakpoint a different id (`urlRegex`). But
    Chrome keeps the URL breakpoint in a browser-side store that `Debugger.disable` doesn't clear. So a different id
    would leave the original to pause every later page of that tab, which is the orphan problem the diagnosis warned
    about.
  - Left to brief 28a, which reworks admission, as a possible "pause still live" check before installing.
- **A dialog opened by a still-loading page** gets the loading message on each 5 s retry. The text also says to ask
  the owner if a dialog shows.
- **An unhandled rejection** (security NOTE 2): a foreign `Debugger.resume` after `disable` has ended the pause is
  rejected in the event listener. The same pattern exists elsewhere in the extension, with no effect on state.

## Left for others

- P3 → brief 28a (`linux-tools`).
- An identity mismatch in a qualification pair is recorded all-false forever → `linux-tools`, as a design question
  (`docs/control/TOOLS-HANDOFF.md`, "Main fix merged").

## Local preflight

On the final head `2d27248c` (`records/final-local-2d27248c.json`): 336 Python tests (shards 68/57/49/162, the Linux-only socket case skipped), 435 Node tests, 546 removal mutations rejected with every baseline passing, generator, whitespace and service-unit checks. No browser was started on the Mac. The pull-request runs are in the PR.

---

# The builder's record (P1 to P3)

Builder: a Claude agent on Fable 5.1 (the brief names Fable: P1 changes the fail-closed admission path). Lead:
`mac-aresos-control`. Branch `pkg/20-popup-race`, cut from main at `bdc16064`. Every commit says `[skip ci]`; no pull
request is open and no workflow was started. No browser was started on this Mac.

## Done

- **P1, the duplicate breakpoint** (`control/chrome/extension/background.js`, `prepareTarget`). When
  `Debugger.setBreakpointByUrl` fails with V8's exact text "Breakpoint at specified location already exists."
  (`duplicateBreakpoint`), the extension re-arms once: `Debugger.disable`, `Debugger.enable`,
  `Debugger.setBreakpointByUrl`. The id the re-armed command returns is the one `state.breakpoint` holds. A second
  refusal or any other error propagates as before, so `initializeTab` rejects, `admitTab` releases, and
  `createdTarget` reports `reader_error`. While recording, a `breakpoint_rearmed` audit line names the tab, target and
  session (CI evidence in the boundary log).
- **P2, the slow-load fallback** (`initializeTab`, `takenTab`, `requireTab`, `admitTab`).
  - The `popup_admitted` line carries `owner_dialog:!!original.modalHandoff`. The harness's `admittedAfter`
    (`control/chrome/ci/popups.mjs`) counts only a line that says `owner_dialog:false`: the fallback (no debugger, no
    breakpoint) no longer releases typed-early's gate, and a line without the field does not count.
  - After the 5 s stall the fallback detaches exactly as before, then stores `owner.handoffMessage` from
    `stallMessage(tab)`: the dialog message when the extension's own dialog record has the tab, or when Chrome's tab
    `status` is not `loading`; otherwise a message that says the page did not answer within 5 s and is still loading,
    that no dialog is known, to try again once it has loaded, and to ask the owner only if a dialog is showing. Both
    `takenTab`'s `ask_owner` and `requireTab`'s `owner_dialog:` error use that message; a successful setup deletes it.
    The result flag and error code stay `owner_dialog`, so the service and its fail-closed handling are unchanged.
  - The MCP instruction (`control/aresos_control/chrome/definitions.py`, regenerated into
    `control/generated/chrome-instructions.txt` and `docs/control/TOOLS.md` by `control/generate.py`) now says: on
    `owner_dialog`, do as its message says (the owner answers the dialog, or try again while the page loads), then
    read the tab again. Without this the instruction would still tell Claude to ask for a dialog answer in the loading
    case. The whole Chrome instruction text must stay within the native CLI's 4096 characters
    (`test_fixes_b_server_instructions_fit_the_native_cli_limit`); a first, longer wording was 10 over, so the
    sentence is kept short.
- **P3: left to brief 28a.** The popup is admitted by `onCreatedNavigationTarget` → `createdTarget`, after the
  click's dispatch has returned or in parallel with it; naming an uncontrolled popup in the click's result would mean
  holding the click result for the admission and threading its outcome through `dispatch`, which is more than a few
  lines in the click path. `createdTarget`'s `reader_error` is unchanged and the service still ignores it, so Claude
  learns of such a popup only through `tabs` (`controlled:false`) and can `take_tab` it.
- **Tests** (`control/chrome_tests/background.test.mjs`, `swappedPopupFixture` extended with `breakpointErrors`,
  `pauseOn`, a bootstrap-capable `Runtime.evaluate` and a renderer-aware `Debugger.enable` replay; and
  `stalledPopupFixture`), seven `popuprace` tests, 435 Node tests in all:
  - one duplicate: admitted late, the exact Debugger command order (`enable, set, disable, enable, set`), the known
    id, one `breakpoint_rearmed`, no `reader_error`, no release;
  - a pause on the orphan id before the re-armed id is known (with the error, and during `Debugger.disable`) is
    resumed as foreign and the document is recorded late, never `document_start`;
  - a pause on the re-armed breakpoint with its id known installs at `document_start` (`ready:true`);
  - two duplicates fail closed with nothing left behind (not controlled, released, disabled, detached, no injection,
    no admission line, opener badge `ON`);
  - any other error text, including the same message without its final full stop, fails closed with no re-arm;
  - a stalled popup still loading: `owner_dialog:true`, the loading message in the result and in the later act's
    error, the admission line with `owner_dialog:true`, detached, and a clean recovery once the page answers;
  - a stalled popup that has loaded, or has a dialog on record, keeps the dialog message.
  - `control/chrome_tests/popups.test.mjs`: the stand-in's admission line says `owner_dialog:false`; `admittedAfter`
    rejects the handoff line and a line without the field, and accepts a real admission after a handoff.
- **Probes** (`reviews/20-chrome/mutation-audit.py`, prefix `popuprace-`, 14, all rejected): the old behaviour
  (every error ends the admission), re-arm on any error, re-arm without disable, re-arm that only sets again, a
  swallowed second refusal, the adopt-by-pause mistake (a pause while the id is unknown counts as startup); the line
  without the flag, the flag never true, the gate accepting a handoff, one message for both cases (twice), the dialog
  record ignored, the message kept after recovery, the act's error with the old text. Two existing probes are
  re-pointed to the changed lines and still remove the same thing: `P1-preexisting-detach` (the fallback's detach,
  now followed by the message) and `P1-preexisting-recover` (`requireTab`'s handoff, now with `handoffMessage(owner)`).
  All 537 probes apply to the current source (checked with a script before the preflight; a probe whose `before`
  text no longer exists stops the whole audit).

- **Preflight:** all green on `ab13b2f3` (`records/final-local-ab13b2f3.json`): 335 Python tests in four shards
  (68, 57, 49, 161; one Linux-only case skipped on the Mac), 435 Node tests, 537 mutations rejected with every
  baseline passing, generator, whitespace and service-unit checks. Two earlier runs stopped early: on `da0fb019` the
  Chrome instruction text was 10 characters over the CLI limit and the moved detach line broke a probe; on `b5894de6`
  a second probe's text had moved. Both are fixed and the third run is the record.

## Left, in order

1. The lead: fresh package review and fresh security review, the pull request, at most 2 + 2 Chrome runs. The
   `breakpoint_rearmed` audit line in the boundary log will show whether the replay happened in a run, and the
   `popup_admitted` lines' `owner_dialog` field whether any popup took the fallback.

## What the code doesn't show

### Re-arm, not adopt: the decision and its evidence

The brief asked to weigh adopting the id that `Debugger.breakpointResolved` reports against re-arming. Re-arm.

- **What the two have in common.** The breakpoint in the new renderer is the extension's own: nothing else sets
  breakpoints on a session `prepareTarget` has just attached, and it arrived there with the session's state. Both
  choices end with one breakpoint whose id the extension knows, so neither leaves an orphan that later documents pause
  on (the diagnosis's objection to keeping an unknown id).
- **Why adopt is incomplete.** `breakpointResolved` comes only when a script with the breakpoint's URL is parsed. In
  run 43671248371 it came (line 18129) before the error (18134), but Chrome replays the unanswered command when the
  session attaches to the new renderer, which happens before the new document commits; if the refusal reaches the
  extension before `context.js` is parsed there, there is no id to adopt, and adopt needs a re-arm anyway, or a wait
  for an event that may never come. Computing the id instead would rely on V8's id format (`<type>:<line>:<column>:<url>`,
  `generateBreakpointId` in `v8-debugger-agent-impl.cc`), which no test of ours pins. Adopt would also have to match
  the resolved breakpoint to the extension's URL through its `location.scriptId`, one more moving part in a path that
  decides between early and late.
- **Why re-arm gives the correct path.** `Debugger.disable` removes every breakpoint of the session in that renderer
  (`V8DebuggerAgentImpl::disable` clears `m_breakpointIdToDebuggerBreakpointIds` and the agent state) and ends a pause
  if the renderer was paused (`V8Debugger::disable` quits the pause loop when no agent accepts pauses). `Debugger.enable`
  replays `scriptParsed` for the new renderer's scripts, which `preloadEvent` records as it does for the first enable.
  The re-armed `setBreakpointByUrl` returns the id. Ordering on the one channel then settles the path: a pause the
  renderer generated before it processed `Debugger.disable` reaches the extension before `disable`'s reply, so before
  `state.breakpoint` is set, and the paused handler treats a pause without the known id as foreign and resumes it (the
  document is then read late, with the reload rule); after `disable` no breakpoint exists until the re-armed one, so
  any later pause with the id is a genuine pause at `context.js` line 1 of a document whose page scripts have not run.
  So a document that ran before the re-arm never counts as early, and `document_start` comes only while the extension
  holds the document paused at its own breakpoint. The tests pin both orders with the same id string for the orphan
  and the re-armed breakpoint, since V8 would give both the same id.
- **Why it is not a retry loop.** One fixed response to one named Chrome behaviour, on one exact error text, once; a
  second refusal fails closed as today. The brief's and the diagnosis's recommendation, kept.
- **Chromium sources relied on** (read from memory and the diagnosis, not re-fetched): `devtools_session.cc`
  (`AttachToAgent` re-sends unanswered commands after a cross-process navigation of the main frame),
  `devtools_interrupt_methods.h` (`Debugger.setBreakpointByUrl` is dispatched during a navigation), V8's
  `v8-debugger-agent-impl.cc` (`setBreakpointByUrl` refuses an id already in `m_breakpointIdToDebuggerBreakpointIds`
  with "Breakpoint at specified location already exists."; `disable` clears them; `restore` and `didParseSource`
  re-create breakpoints from the agent state) and `v8-debugger.cc` (`disable` ends a pause). What the log cannot show
  (which internal path delivered the first copy) the fix does not depend on: it reacts to the refusal alone.

### P2: how a loading page is told from a dialog

The brief says to check `Page.javascriptDialogOpening` state or the extension's own dialog record. The record
(`dialogs`) can only hold a dialog whose opening event arrived, which needs `Page.enable` to have been answered; a
dialog that opened before the debugger attached, the case the fallback was built for, sends no event, so at the
fallback the record is always empty for a fresh take. Used alone it would turn every handoff into the loading message,
including the real dialog case. So `stallMessage` also reads Chrome's tab `status`: `loading` means a document is
still arriving (the H6 case: the debugger attached while a cross-document navigation was pending, and DevTools held
the session's commands until it ended); anything else, for a renderer that answers nothing for 5 s, is read as blocked
by a dialog, as before. The one case this gets wrong is a dialog that opens during the load (an `alert` in an inline
script): the message then says loading and adds "if a dialog is showing, ask the owner to answer it first". The lead
may prefer the record alone; it is one line to change (`stallMessage`), and the probes `popuprace-loading-says-dialog`
and `popuprace-dialog-says-loading` would then need the fixture's `status` replaced by a `dialogs` entry.

### Local environment

- The Node tests `signed CRX3 …` and the two `QUALIFICATION …` tests need `.work/20-chrome/` to exist (they
  `mkdtemp` inside it); a fresh worktree lacks it. The preflight's mutation audit creates `.work/20-review-mutations`
  only, so `mkdir -p .work/20-chrome` before the preflight. Not a product matter.
