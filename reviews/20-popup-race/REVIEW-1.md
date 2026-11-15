# Package review 1 (`bdc16064..b6d223fa`, Claude Opus, 2026-11-15)

**Verdict: FIX.** Two small fixes, both outside the browser code. P1 to P3 are sound, and I found nothing blocking in the popup admission code.

## FIX

**1. `control/chrome/qualify.py:310–315` (P4 notify): the title match picks up issues that strangers open.**
- **Why it matters:** the repo is public with issues enabled (I checked with `gh repo view`). `report()` takes the lowest-numbered open issue with a matching title, whoever opened it. It also skips its comment when any comment, from anyone, already has the same text. Before P4, every notice was a new issue opened by the workflow.
- **Failure scenario:** the title "Update shipped Chrome qualification record" is already public on the pushed branch. Before the first main run after the merge, a stranger opens an issue with that title. Its text gives a different `gh pr create --head <fork>:<branch>` command. Notify finds it, never opens its own issue, and only adds comments under the stranger's post. The session told to act on that issue reads the stranger's instruction first, and the shipped record decides which Chrome builds get adapters and trusted sends.
- **Smallest fix:**
  - List with `--json number,title,author` and keep only issues whose `author.login == 'app/github-actions'`. That is gh's exact form; issue #74 shows `{"is_bot":true,"login":"app/github-actions"}`.
  - When deciding whether the text is new, count only the workflow's own issue body and comments.
  - Add one test row: a same-title issue opened by someone else, and a matching comment by someone else.

**2. `reviews/20-popup-race/records/final-local-ab13b2f3.json:51–79`: absolute paths in the record.**
- The node command lists 29 absolute paths (`<worktree>/control/chrome_tests/...`). The reference record `20-main-fix/records/final-local-496018a5.json` uses repo-relative paths.
- This breaks the brief's repo-relative rule and puts the owner's Mac account name in a public repo. Main already has such absolute paths in a few files, so the privacy guard won't catch it.
- **Fix:** strip the prefix, or regenerate the record.

## NOTEs (non-blocking)

**P1 ordering argument.**
- It holds against the code. The paused handler decides synchronously when the event arrives, before any `await`, and `state.breakpoint` is only set after the re-armed set's reply.
- The tests cover both real orders: a pause arriving with the duplicate error, and one arriving while `disable` is in flight. Both use the same id string for the leftover and the re-armed breakpoint. They also cover the failing run's order, where no pause came at all.
- The argument depends on Chrome delivering `onEvent` and `sendCommand` replies to the worker in protocol order. There are two round trips of margin after `disable`.
- **Theoretical leftover risk:** if a stale pause from the leftover breakpoint were delivered after the re-arm completed, the document would count as `document_start`. For popups this does no harm, because `popupNeedsReload` stays true until the guarded reload. For an owner tab taken during a cross-process navigation, it would skip the reload. That needs three unlikely things together.
- Optional hardening: confirm a startup pause is still live before installing.

**P2, tab status.** I see no concrete harm, so I accept the judgment call.
- One soft spot: a page whose inline script opens an `alert` while loading gets the loading message on every retry, and each retry costs 5 s.
- Possible wording: "if this repeats, ask the owner whether a dialog is showing".
- The instruction is 4,081 of 4,096 characters. The generated files match their definitions.

**P4, smaller points.**
- `--limit 200` lists newest first. With more than 200 open issues, an older workflow issue drops out and a duplicate gets created. Unlikely in this repo.
- The version regex `(?: [a-z]+)?` accepts any lowercase word after the version. That does no harm, because the version must equal the plan's. It accepts the real stable line (trailing space) and beta line, and refuses `Google Chrome beta`, `Chromium …`, three-part versions and extra words.
- A stale comment at `qualify.py:429` still says notify writes "issues and pull requests".

**Rejected resume (harmless).** In the "pause during `disable`" order, the foreign resume reaches the renderer after `disable` and is refused. The async listener then logs an unhandled rejection. This pattern already exists elsewhere in the extension, and no CI check scans for it.

## Answers to your questions
- **P1:** only V8's exact text triggers the re-arm, once. A second refusal or any other error fails closed through `admitTab`'s release, which disables and detaches, so no leftover breakpoint stays behind. Re-arm over adopt is well argued.
- **P2:** `owner_dialog` is in the admission line and `admittedAfter` requires it false. The handoff, needs-reload, detach and error code are unchanged, and the reload rule is untouched.
- **P3:** leaving it to 28a is sound. The click result has no popup correlation today, so it can't name an uncontrolled popup without new plumbing.
- **P4:** the version parse is right. Notify writes issues only (no `gh pr` call), comments only on new text, shows gh's own error, and names its run in a refusal. The title-matching problem is FIX 1.
- **Scope:** no change to tab groups, the hold, the ceilings, the sample counts or storage.

## Checked
- **Read:** the brief, `DIAGNOSIS.md`, `PROGRESS.md`, the full diff `bdc16064..b6d223fa`, and the surrounding code. In `background.js` that was `prepareTarget`, `preloadEvent` and its paused paths, `lateReader`, `initializeTab`, `admitTab`, `requireTab`, `release`, the `onEvent` listener and the reload decision. Also `context.js`, the content-script registration, the CI fixtures `popups.mjs` and `review-matrices` GROUP 8 (the latter still expects the dialog message, and its 300 ms dialog fires after the tiny page has loaded), and the qualification workflow and `run.sh` version source.
- **Ran, in my scratch copy** (the reviewer's scratch directory (not committed)):
  - `background.test.mjs` and `popups.test.mjs`: 150 of 150 pass.
  - `test_publisher`, `test_qualification`, `test_questions`: 90 OK.
  - `generate.py --check`: OK.
  - 25 probes through the audit's own harness: all 14 `popuprace-*`, all 6 `qualifyfix-*`, and the 5 `P1-preexisting-*`. All were rejected, and I checked each failing assertion against its stated reason. `P1-preexisting-detach` still fails on `attached` staying true, and `P1-preexisting-recover` on recovery never re-attaching, so both are still the same removal.
- **Read-only gh calls:** repo visibility and the author fields on issue #74.
- No browser was started, and nothing in the worktree changed.
