# Diagnosis: popup admission race (run 43671248371)

Written 2026-11-15 by a diagnosis agent for `mac-aresos-control`; read-only, from the run's artifacts and the code at `pkg/20-main-fix`.

The `typed-early` fix does not cover this one. Page.enable did not stall and the 5 s fallback never ran. This is a different race, in the same class as the earlier POST-popup race in `reviews/20-chrome/REPORT.md`: the popup's first cross-site load lands in a new renderer while the extension is still setting it up. It is a product robustness bug, and it fails safe.

## 1. Event order (run 43671248371, `fixtures (policy, recheck2)`; popup tab …227, opener …211)

Boundary log lines:
- **18108–18111:** Claude's click, then `Page.windowOpen` to `popup.test:8766`. PR #58's head has no H6 fix, but this row is untouched by it.
- **18114–18121:** `Page.enable`, `Page.getFrameTree` and `Debugger.enable` all answer at once. They are answered by the popup's initial empty document, which lives in the opener's renderer (the frame tree's origin is `"://"`). So the session was not paused, unlike H6.
- **18123:** `Debugger.setBreakpointByUrl` (id 678) is sent.
- **18124:** the cross-site document commits in a new renderer.
- **18128–18129:** `context.js` is parsed and `Debugger.breakpointResolved br:1:1:0:…/context.js` arrives. The breakpoint already exists in the new renderer before 678 gets its reply. The page then loads (18130–18133), with no `Debugger.paused`.
- **18134:** 678 fails. `service.txt:18243` holds the error: `reader_error … "Breakpoint at specified location already exists."`
- The whole sequence took 78 ms (rules timestamps …647 → …725), so the 5 s fallback was never involved.

What the code did with that error:
- `prepareTarget` throws at `background.js:90`, the race in `initializeTab` rejects, and `admitTab`'s catch calls `release` (`:484`).
- `release` finishes: `released` event, guard cleanup returns `true` (18136–18139), `Debugger.disable` (18140), detach, network rules recomputed for the opener only (18135/18143).
- `createdTarget` reports `reader_error` (`:493`). No `popup_admitted` line is written.
- The harness then waits 15 s at `popups.mjs:134` for the opener badge `POP`, which never comes. The `undefined` in the error is only `eventually`'s empty error text (`browser.mjs:30`). `control-status.json` confirms: opener badge `ON`, `popups: []`, popup debugger `attached:false`.

The same row passing, for comparison:
- **43669130757:** `Page.enable` waited until after the commit, so every command reached the new renderer. The popup was admitted on the late path (line 18191).
- **43663583962:** the commit came before `Page.enable`; same result.
- **The release row in the failing run itself** took the waiting order (17847 → 17854) and was admitted.
- **`typed-early` in the failing run** (16473–16494): the breakpoint was set in the old renderer and answered before the commit, carried over into the new renderer, and the page paused there (`document_start`).

The failing order is a fourth one: the commit lands while the breakpoint command's reply is still outstanding.

**Why it fails.** I read current Chromium source for this:
- `devtools_session.cc` `AttachToAgent` re-sends unanswered commands to the new renderer after "cross-process navigation in the main frame".
- `Debugger.setBreakpointByUrl` is on Blink's interrupt list (`devtools_interrupt_methods.h`), so it is never held back during a navigation.
- It is not in `MayCauseJavascriptExecution`, so on a renderer change it is re-sent rather than failed.
- The breakpoint also travels into the new renderer with the session's saved state, as `typed-early` shows.

So Chrome ran the extension's one command twice against the same state, and V8 refuses the second copy because breakpoint ids are fixed by URL and line. The log proves the outcome (the breakpoint resolved before the reply, then the duplicate error). It cannot show which internal path delivered the first copy.

The earlier POST-popup fix only made `lateReader` tolerate a dead context. A failure at this breakpoint command is a second failure point in the same window, and nothing handles it.

## 2. Rows exposed

**This class** (opener controlled, popup's first load is cross-site, no hold). Worktree `control/chrome/ci/popups.mjs`:
- `:91` loop, rows `clean`, `dirty`, `typed-clean`: the opener script (`:67`) opens `popupChild` (`:46`, `popup.test` from `fixture.test`); the click is at `:110`.
- `:131–135` `popup-stop`.
- `:155–159` `popup-opener-release` and `popup-opener-close` (the failing row).
- `:170–175` `popup-post` (`about:blank`, then a cross-site POST; this is the earlier race).

**Not exposed:**
- `typed-early` after H6 (`:60`, `:71–74`, `:107–112`): admission finishes before the cross-site navigation starts.
- `typed-late` (`:93–99`): the extension attaches only after the page has loaded.
- `popup-outside` (`:177`): never admitted.
- `recheck2-matrices.mjs` `blank` and `form-blank` (`:32–45`, `fixture.test` → `fixture.test`) and the recheck2b popups (`:71–96`, `localhost` → `localhost`): same-site or same-origin, so the first load stays in its renderer. This relies on Chrome keeping the initial document's renderer for a same-site first load. It matches every run, but I have not proven it from source.
- The review popups use relative URLs (same origin).

**The H6 class** (a navigation still pending after 5 s while Chrome holds the session): no row on PR #68 after H6, since the fixture now holds only `/popup-gate`. On PR #58's head, `typed-early` (`popups.mjs:82` there) is still exposed; it happened to pass in this run.

## 3. Product view

**This race:** the owner can hit it. Any popup or new tab Claude's click opens to another site (a sign-in provider, a payment page) can commit inside the few milliseconds the breakpoint command takes. In this job it hit 1 of 7 cross-site popup admissions.
- **It fails safe.** The popup stays open and uncontrolled, nothing was sent to it, the cleanup ran fully, and no `popup_admitted` is written. The only in-between state is the 78 ms admission itself, which `admissions` already dedups.
- **The cost:** Claude is never told. The service ignores `reader_error` (`REPORT.md:958`) and the click result says nothing. Claude only sees the popup as `controlled:false` in `tabs`. It can `take_tab` it (`background.js:461–465`), which takes the late path with the reload rule.

**H6 (a real first navigation slower than 5 s):** the owner can hit it too. The fallback at `background.js:437` fires on any `Page.enable` stall, not just a dialog. It sets the dialog handoff and "needs reload", detaches (`:439–443`) and returns normally.
- **Product bug, plainly:** `admitTab` then sets rules and badge, writes `popup_admitted` (`:482`) and returns `owner_dialog:true` (`:483`), which `createdTarget` throws away (`:490–494`). The popup counts as controlled and the opener shows `POP`, but there is no debugger and no guard.
- **Still safe for actions:** every later act goes through `recoverOwnerDialog` (`:602`), which re-attaches on the late path, and the reload rule applies before the first act.
- **Misleading part 1:** the `popup_admitted` line at `:482` is written even after the fallback detached. The harness reads it as "breakpoint set" (`popups.mjs:34–35`), which is what released H6's hold early. This line only goes to the CI log, not to production.
- **Misleading part 2:** if Claude acts while the slow page is still loading, it gets "Please answer the dialog yourself" (`:430`, `:602`) although no dialog exists.

## 4. Smallest correct fix

- **Product, for this race (recommended):** in `prepareTarget` (`background.js:90–91`), handle only V8's exact duplicate-breakpoint error. On a session the extension just attached, where `prepareTarget` is the only thing that sets breakpoints, that error can only be Chrome's replay. Re-arm once to get a known breakpoint id: `Debugger.disable` → `Debugger.enable` → `Debugger.setBreakpointByUrl`. Any other error, or a second failure, fails closed as today.
  - It is a single fixed response to a named Chrome behavior, not a test retry, and no assertion changes. You decide whether it counts as a retry under the rule; without it, the status quo stays fail-closed and flaky.
  - The alternative of keeping an unknown breakpoint id is worse: every later page of that popup would pause on the orphan breakpoint, be resumed as foreign (`:165–174`) and land on the late path.
  - Tests: extend `swappedPopupFixture` (`control/chrome_tests/background.test.mjs:1294`) with a one-time duplicate reply. One case must be admitted late with no `reader_error`; a second duplicate must fail closed with nothing left behind. Add a removal probe.
- **Product, for H6's log line (small):** at `:482`, add `owner_dialog: !!original.modalHandoff` (or write a separate line for the handoff), and have `admittedAfter` (`popups.mjs:36–38`) require it false. Optionally, make the fallback's message say "page still loading" when no dialog is open.
- **Harness:** the H6 gate is enough for H6. Gating every exposed row would make this flake go away in CI, but `typed-clean` is meant to be the natural-race row (`popups.mjs:17–19`), and gating would hide a bug real popups hit. With the product fix, no further harness change is needed.

The `latency (audit)` failure in the same run is unrelated: target misses in `history-1000` (`asking_click`, `navigate`) with `regression:false`. I didn't look into it further.

Nothing in the worktree changed. I kept only the failure's `browser-boundary.jsonl`, `service.txt`, `control-status.json` and `browser.txt` in the main-fix worktree's `.work/h7/fail/` (not committed) and deleted the passing runs' downloads.