# Security review 1 (`bdc16064..b6d223fa`, Claude Fable, 2026-11-15)

**Verdict: SAFE.** No FIX. Notes below, none blocking.

## P1, re-arm path

The safety argument holds; I verified it against current V8/Chromium sources (fetched, not from memory):

- `V8DebuggerAgentImpl::disable` clears `m_urlBreakpoints`, calls `m_debugger->removeBreakpoint` for every debugger breakpoint, clears both id maps, sets `kDisabled`, then `m_debugger->disable()`. `V8Debugger::disable` quits the pause loop when no agent still accepts pauses. So after the renderer processes `disable`, no orphan breakpoint exists and a pause in progress ends.
- `Debugger.paused` is emitted (`didPause`) **before** `runMessageLoopOnPause`; `disable` is processed inside that loop, and Blink's `SendProtocolResponse` calls `flushProtocolNotifications()` before every response on the same `host_remote_`. So the orphan pause always precedes `disable`'s reply renderer→browser, and the browser's `DevToolsSession` dispatches to the client in order. The paused handler sees `state.breakpoint===undefined`, takes the foreign branch, resumes, and the document is read late. No order exists in which a document that ran unguarded gets `document_start`, given ordered delivery (see NOTE 1).
- Id equality: the id is deterministic in both layers (`br:1:1:0:<url>` browser side, `1:1:0:<url>` in V8), so orphan and re-armed ids are equal; the tests using one string is correct. It does not matter because matching depends on *when* the id becomes known, not on the string.
- Mechanism nuance the builder didn't have: in today's Chromium the URL breakpoint lives in browser-side `BrowserOriginatingSessionState::url_breakpoints` (`DebuggerHandler::SetBreakpointByUrl` records it at dispatch, then `FallThrough`); every new renderer's agent is constructed with it, which is how the breakpoint "travels". `Debugger.disable` falls through and does not clear that store. Effect: harmless for the re-arm (same id; `enableImpl` doesn't re-seed), but a second renderer swap *during* the re-arm gives a second refusal → fail closed (flake, not a hole).
- Other errors and a second refusal propagate unchanged: `initializeTab` rejects, `admitTab` releases (controlled is `original`), `createdTarget` reports `reader_error`. Tests pin `enable, set, disable, enable, set, disable, detach`, no `preloadTargets` entry, no admission line, badge `ON`. `admissions` is cleared by `take`'s `finally`; no new listener. `assertTarget` inside each re-arm command fails closed if control ends mid-way. All four Debugger methods are in `POLICY.cdpMethods`.

**NOTE 1 (hardening, optional).** Browser→extension, the pause event and the command reply travel by two different paths (`EventRouter` vs the pending `DebuggerSendCommandFunction`'s response, `debugger_api.cc:927ff`). In practice ordered (same browser thread, same worker), but not formally guaranteed across mojo interfaces. A paused event delayed past two further round trips (`enable`, `set`) would match the known id and install `document_start` on a document that ran. If you want zero dependence on ordering: give the re-armed breakpoint a different id, e.g. set it by `urlRegex` (type 2 → `br:2:1:0:…`), so no orphan pause can ever equal `state.breakpoint`. A few characters in `startupBreakpoint`/the re-arm call plus a test.

**NOTE 2.** Foreign-branch `Debugger.resume` can reject if `disable` quit the loop first ("Can only perform operation while paused"); it becomes an unhandled rejection in the `onEvent` listener. Pre-existing pattern, no state effect.

## P2

Reload rule, handoff and `recoverOwnerDialog` are unchanged; `owner_dialog` flag and error code are the same, only the text differs; message strings are fixed, never page-derived. A page can hold tab `status` at `loading` (never-finishing resource) and so get the "still loading" text while a dialog is open: Claude retries instead of asking; each retry is the same bounded attach→5 s→detach, and the text also says to ask the owner if a dialog shows. Not a weakening; the builder documented it. `handoffMessage` is deleted on every successful setup; `popup_admitted` carries `owner_dialog:true` so the harness gate can't be released by the fallback.

## P4

- Version parse: `re.fullmatch(r'Google Chrome (\d+(?:\.\d+){3})(?: [a-z]+)?')` is stricter than `split()[-1]` (rejects `Chromium …`, `Google Chrome beta`, extra words). Version is still compared exactly to `identity['version']`, build to `runtime_identity`; channel was never measured before or now. No pair can pass that failed before on identity; only the false negative for beta goes away.
- GitHub writes: `issue list`/`issue view` (reads), `issue create`/`issue comment` (within `issues: write`); `pull-requests: write` dropped, PR path removed. Bodies use fixed strings, `GITHUB_SERVER_URL`/`GITHUB_RUN_ID` (workflow env), and validated-record fields (`build` hex64, `channel` ∈ {stable,beta}, `version` via `version()`, group names from fixed sets). `verify`, `verify_held`, `publish`, `prepare`, attestation steps untouched.

**NOTE 3.** The repo is public and `report()` picks the lowest-numbered open issue with the exact title, regardless of author. Anyone can open an issue with that title (the run then comments there) or post the predictable body as a comment (the run then stays silent). Informational only, trust path unaffected. Smallest fix: `--author app/github-actions` on the `issue list` call.

## Tests run (scratch copy, no browser)
`background.test.mjs` 143 pass, `popups.test.mjs` pass, `test_publisher`+`test_qualification` OK.

## Sources checked
- V8 `src/inspector/v8-debugger-agent-impl.cc` (main): ctor 480-489, `enableImpl` 494-515, `disable` 538-580, `restore` 582-616, `setBreakpointByUrl` 685-806 (refusal 736-739), `generateBreakpointId` 99-111, `didParseSource` 2115-2250, `didPause` 2314-2400.
- V8 `src/inspector/v8-debugger.cc`: `disable` 116-146, `handleProgramBreak` 490-585.
- Chromium `content/browser/devtools/devtools_session.cc`: `MayCauseJavascriptExecution` 61-71, `AttachToAgent` 191-262, `FallThrough` 414-444, `DispatchProtocolResponse` 600-617. `content/browser/devtools/protocol/debugger_handler.cc` 22-87.
- Chromium `third_party/blink/renderer/core/inspector/devtools_session.cc`: `ConvertEmbedderState` 54-85, `IOSession::DispatchProtocolCommand` 134-156, `SendProtocolResponse` 396-416, `FlushProtocolNotifications` 444-470. `third_party/blink/public/common/devtools/devtools_interrupt_methods.h` 26-34.
- Chromium `chrome/browser/extensions/api/debugger/debugger_api.cc`: `DispatchProtocolMessage` 927ff.
- Worktree: `control/chrome/extension/background.js` 46-117, 119-250, 276-300, 455-532, 635-720, 1220-1240; `control/chrome/qualify.py` 285-336, 417-438; `control/aresos_control/chrome/qualification.py` `validate_record`; `control/chrome/ci/attestation.py` 249-275; the test diffs.
