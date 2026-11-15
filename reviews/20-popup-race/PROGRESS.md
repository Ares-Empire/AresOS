# 20-popup-race: progress

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
    `owner_dialog`, do what its message says (answer the dialog, or try again when the page is still loading), then
    read the tab again. Without this the instruction would still tell Claude to ask for a dialog answer in the loading
    case.
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
  record ignored, the message kept after recovery, the act's error with the old text.

## Left, in order

1. Full local preflight (`python3 -B .work/20-popup-race/preflight.py`), copy its `final-local.json` to
   `reviews/20-popup-race/records/final-local-<head>.json` with a `note`, commit and push.
2. The lead: fresh package review and fresh security review, the pull request, at most 2 + 2 Chrome runs.

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
