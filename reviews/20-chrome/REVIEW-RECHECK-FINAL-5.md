**SAFE (no FIX open)**

Package re-check, round 5: the POST popup admission fix. Scope: `git diff 662e813a fe4f254e`, with the code in
`0347b548` and `6066468b` (`lateReader` in `control/chrome/extension/background.js`) and REPORT.md's "POST popup
admission". I built none of it and worked read-only on the review copy at `fe4f254e` and on `git archive` exports,
with no browser, no profile and no workflow dispatched.

I did not read the builder worktree's `.work/finalpair/` copies: the review rules keep that worktree untouched. I
fetched the same evidence one-shot instead, about 9 calls:
- both runs' metadata and artifact lists;
- the failed shard `control-chrome-43631476260-1-external-recheck2`;
- the push run's passing policy shard;
- the pull-request run's two passing `recheck2` shards (external and policy).

All four zips equal GitHub's SHA-256 digests, and their members are flat, with no profile directory.

The diagnosis holds against the artifacts. The fix is narrow and fails closed. Its tests fail on the code they fix,
and its three probes are killed.

## FIX

None.

## KNOWN LIMIT

None new.

## NOTE

1. **The refusal advises "take the tab again"; on one path that isn't enough.**
   - `lateReader`'s new refusal (`background.js:296`) ends in "take the tab again". On the admission paths
     (`createdTarget`, `take_tab`, `open`, `recoverOwnerDialog` through `initializeTab`), a failed admission releases
     the tab, so a re-take is the right advice.
   - On `requireTab`'s retry (`:609`, `pending.retry??=lateReader(tab)`) the tab is already controlled. A rejected
     retry stays cached in `pending.retry`, and `take_tab` of a controlled tab returns early (`:459`). So every later
     call on that tab fails until the tab is released and taken again.
   - This path is reached only when the original admission's `ready` lost its race to a dialog or the 5 s owner-dialog
     timer. Any error there behaved this way before this round, so it is not new.
   - Saying "release and take the tab again", or releasing on a rejected retry, would make the advice true on every
     path.
2. **The passing runs show the other order, but not always before `Page.enable`.**
   - In the pull-request run's external shard the POST committed before `Page.enable` (749), as REPORT says.
   - In both policy shards (push and pull-request), it committed just after `Page.enable` and before `Debugger.enable`.
   - So the discriminator is "the POST commits before `Debugger.enable`", which is REPORT's own closing sentence ("the
     race is whether `Debugger.enable` lands while the popup still shows its first document…"). The "before
     `Page.enable`" wording describes that one shard only. Wording only.
3. **Cosmetic:** the new preflight record `records/post-popup/final-local-6066468b-python-0.txt:52` has the
   trailing space again (`git diff --check 662e813a fe4f254e`), the same verbatim line as twice before.

## Verified

### 1. The event order

**Failed shard** (`43631476260`, external `recheck2`, `browser-boundary.jsonl`; popup tab `1637225932`):
- `Page.windowOpen` (18576) is followed by the `about:blank` commit (18577), then `Page.enable` 750 (18580) and
  `Debugger.enable` 752 (18587).
- `Debugger.enable` replays `context.js` in **context 7**, scriptId 29 (18588).
- `setBreakpointByUrl` 753 is dispatched (18591). The POST then commits (`form_submit`, 18592), with `context.js` in
  **context 2**, scriptId 3 (18593) and the page script in context 1 (18594).
- Then `guard.js`/`reader.js` arrive in context 2 (18603-18604).
- `Runtime.evaluate` 755 fails (18607).
- Release follows: 756 fails, then `cleanup_context` context 7 `native_context_missing` (18611), then 757 in context
  2, then `Debugger.disable` 758.
- `service.txt` 18676-18724 has the same sequence, the `released` event and
  `reader_error … Cannot find context with specified id`. `browser.txt:45` is the row's failure ("POST popup private
  group: undefined").

**No navigation or context event for the popup.** The popup tab's only protocol events are 6 `scriptParsed`,
`domContentEventFired`, `loadEventFired` and `frameStoppedLoading`. There is no `frameNavigated`,
`frameStartedNavigating` or `executionContext*` event, although the same log records `Page.frameNavigated` 140 times
and `frameStartedNavigating` 103 times for other tabs.

**No resubmission:** `receiver.jsonl` has exactly one `/post-document?case=popup-post` arrival.

**Passing shards** (the POST commits before `Debugger.enable`, whose replay then holds only context 2):
- pull-request run external: commit at 18581, before `Page.enable` 749 (18582);
- push run policy: commit at 18449, after `Page.enable` 748 (18448) but before `Debugger.enable` 750 (18456);
- pull-request run policy: commit at 18445, after `Page.enable` 748 (18443) and before `Debugger.enable` 750 (18452).

Each continues to `popup_admitted`.

### 2. A real product race, and every path covered

- **The race is in the product:** the steps are all the extension's own: `createdTarget` → `take` → `admitTab` →
  `initializeTab` → `prepareTarget` → `lateReader`. A popup opened by Claude's click starts as `about:blank` in the
  opener's renderer and swaps renderer when its cross-site document commits. Because the Runtime domain isn't
  subscribed, no event reports the dead context. The harness only supplied the timing.
- **Every path is covered:** every admission or re-reading path evaluates contexts only in `lateReader`:
  - popup auto-attach (`createdTarget`), `take_tab` and `open` go through `admitTab` → `initializeTab` (`:434`);
  - re-take and `recoverOwnerDialog` go through `initializeTab`;
  - `requireTab`'s retry (`:609`) and `facts` (`:744`) call `lateReader` directly.
- **The other loops over recorded contexts tolerate a dead one:**
  - `linkPrivateDocuments` catches per call (`:61-75`);
  - release's cleanup already maps `Cannot find context` to `native_context_missing` (`:678` and on);
  - the dialog boundary looks contexts up by `uniqueId` and fails closed.

### 3. The fix and fail-closed

- **The rule:** only `Cannot find context with specified id` (`nativeContextMissing`, `:48`), for the very context
  object still in the map (`:279`), forgets the context. Its documents are dropped and its frame is added to
  `forgotten`. Any other error still throws.
- **The coverage check:** after the loop, each forgotten frame must be covered by a recorded document whose isolated
  context is in the map with that frame id (`:295-296`). Otherwise the `refused: … replacement is unread` error ends
  the admission.
- **How a live context is learned:** only from `Debugger.scriptParsed` for the extension's own `context.js`,
  `guard.js` or `reader.js` in an isolated world (`preloadEvent`, `:124-129`). `lateReader` injects `guard.js` and
  `reader.js` into every live frame first, which gives the second, independent report.
- **A wrongly forgotten live context is still safe:** its frame stays uncovered and fails closed. A document whose
  context stays unknown is `!isPreloaded` → `needs_reload`, so input waits for the guarded reload, and popups for
  `popupNeedsReload`.
- **Nothing is left behind on the admission paths:** a throw rejects `initializeTab`, and `admitTab`'s catch runs
  `release(tab)` because `controlled.set` came first. The Node test checks the result: not controlled, no admission,
  target or install record, the reader cleared, `Debugger.disable` and detach, no group, `released`, no
  `popup_admitted`.

### 4. Tests and probes

I ran `background.test.mjs`'s four `post-popup` tests with `fe4f254e`'s test file against each version of
`background.js`:

| `background.js` from | Pass | Fail |
|---|---|---|
| `662e813a` | 1 ("any other … error still ends the admission", a regression guard that holds on the old code too) | 3, including "a dead context … is admitted late" |
| `0347b548` | 3 | 1: "no live context after forgetting … fails the admission closed" |
| `fe4f254e` | 4 | 0 |

The three probes (`post-popup-dead-context-ends-admission`, `post-popup-any-error-forgotten` and the lead's
`post-popup-empty-contexts-count-as-read`) are rejected in my local mutation audit.

### 5. Unchanged

- The `control/` diff is `background.js` (27 lines, all in `lateReader` and the one helper) plus its test.
- The harness, tab groups (no group line in the diff), Python, the generated files and the packaging are unchanged.
- `git diff 8b7e799c fe4f254e -- control/packaging/aresos-toold.service` is empty.
- No extension storage.
- No absolute user path in the round's files.
- REPORT's "POST popup admission" matches the code and the artifacts, apart from NOTE 2's wording.

### 6. Local preflight on `fe4f254e`

These are the same commands as the earlier rounds. They ran on a `git archive` export of `fe4f254e` in a scratch
directory, with CPython 3.14.6, SQLite 3.50.4, jsonschema 4.26.0 and Node 26.4.0, and wrote nothing to the review copy.

- **Python shards:** 53 / 56 / 49 / 147 = **305 tests, all OK**. One skip: the Linux-only spoofing-socket case.
- **Node:** **432 / 432 pass**, the four `post-popup` tests among them.
- **Mutation audit:** **464 rejected, 0 survived, every baseline passed**, including the three `post-popup-*` probes.
- **Generator:** `control/generate.py --check`: "Generated artifacts match definitions".

These match the lead's expected 305 Python, 432 Node and 464 mutations. `b2d7705c` and `fe4f254e` change only
REPORT.md and records after `6066468b`.

**Scratch evidence** (outside the repo): `final-review/recheck-pkg/round5/`, with `api/` (both runs' metadata and
artifact lists), `zips/` and `x/` (the four `recheck2` shards), `demo-*` (the per-commit test runs) and `out/`
(preflight logs).
