**SAFE (no FIX open)**

Package re-check, round 3, item 4: the group-window fix. Scope: `git diff 7c59733b ca64f23b`. The fix is in
`53ecc91b`; the rest is the preflight record, the trailing-space cleanup, run receipts and REPORT.md's "Group in the
tab's own window". The review copy is at `18ff4398`, whose last commit adds only the round-3 review files. I built
none of it and worked read-only, with no browser, no profile and no workflow dispatched. GitHub: about 12 one-shot
calls (run metadata, artifact list, 8 artifact zips, one run list). I did not use the builder's downloads in its
worktree; the review rules keep that worktree untouched, so I fetched my own.

The fix closes round 3's FIX-1 with exactly one changed product line. The new test fails on the old code, both
probes are killed, and run `43626497829` passed all 28 jobs, with the forced `typed-late` row covering the
popup-focused case in both installs.

## FIX

None. Round 3's FIX-1 is closed.

## KNOWN LIMIT

None new.

## NOTE

1. **A short race remains.** `current` is read at the start of `admitTab` (`background.js:433`), and the group call
   comes after `chrome.debugger.attach`. If the owner dragged the tab to another window inside that span, the new
   group would be made in the window the tab just left, and Chrome would move the tab back there. That is the same
   window `restoreTab` returns it to (`original.window`). The window is milliseconds long and the outcome harmless;
   no action.
2. **A pre-existing behaviour remains, outside this fix.** With a Claude group already in window W1, taking a tab
   from W2 still adds it by `groupId` and so moves it into W1. That is the single-global-group design ("Take the
   chosen owner tab into the visible Claude group"), which `restoreTab` undoes at release, and the lead's
   "tab groups frozen" rule keeps it. I mention it only because REPORT's round-3 text said "taking a tab must never
   move it"; that sentence holds for the no-group case this fix closes.

## Verified

### The fix and the call sites

- **The changed line:** `control/chrome/extension/background.js:449`.
  - With no Claude group (`groupId === null`), it calls
    `chrome.tabs.group({tabIds:[tab],createProperties:{windowId:current.windowId}})`. `current` is the taken tab's
    own `chrome.tabs.get(tab)` at `:433`, the same value recorded as `original.window`.
  - With a group in place, the call is unchanged (`{groupId}`).
  - Only normal windows reach this line: a non-normal window is a `virtualGroup` and makes no group call, and it
    needs a controlled opener.
- **It is the only product call that can create a group:** `grep` finds two `chrome.tabs.group` calls in
  `control/chrome/extension/`.
  - `restoreTab` (`:403`) passes `groupId:original.group`, only when `>=0`, so it rejoins the owner's earlier group
    and can't create one.
  - `open` (`:857`) creates its tab with `chrome.tabs.create` and takes it through the same `admitTab`.
  - Popups make no group call.
  - `control/chrome/ci/` has no group call.
  - The `control/checks/17{b,c,d}-chrome/` CHECK-ONLY extensions still group without a window. They are frozen
    experiments: `build.py` hashes only `chrome/extension` and the other runtime dirs, and they aren't packaged.
- **Nothing else changed:** the whole `control/` diff from `7c59733b` to `18ff4398` is this one line plus its test.
  `tabGroups.update` (name, colour, collapse), the `release` reset at `:675`, `restoreTab` and membership are
  byte-identical.

### The test and the probes

- **The test:** `background.test.mjs` `group-window …` runs the real `take` → `release` → `take` against a fake
  `chrome.tabs`. The fake follows Chrome's rule: a new group without `createProperties.windowId` goes in the
  last-focused window and moves the tab there, and only normal windows hold groups. It has two cases, a focused
  popup and another focused normal window.
  - **The fixed call:** it is asserted exactly, a second tab joins by `groupId`, and no tab moves window.
- **It fails on the old code:** with the old line restored in a scratch copy, both cases fail. The popup case gives
  "Tabs can only be moved to and from normal windows". The normal-window case fails its assertion that the new group
  is in the tab's own window.
- **The probes:** `group-window-drop-window-id` (the lead's) and `group-window-no-create-properties` are both
  rejected in my local mutation audit.

### Run `43626497829`

- **Jobs:** one `gh run view`: head `6e8cf12b` (`53ecc91b` plus preflight records), 28/28 succeeded. The longest
  job was `fixtures (external, core)` at 30.2 min. `latency (plain)` took 12.3 min and `latency (audit)` 11.2.
- **Artifacts:** the two aggregates, two `recheck2` shards and four latency artifacts all equal GitHub's SHA-256
  digests. Their members are flat, with no profile directory.
- **Independent audit:** I re-ran `reviews/20-chrome/audit-review-evidence.mjs` on both aggregates. Both passed:
  98 named passes, group 12, 96 destination cases, 305 Python and 423 Node tests, Chrome 157.0.8103.78. My output
  equals the committed `…-independent-audit-ci.json` and the artifact's own `independent-audit.json`, apart from the
  folder name.
- **Popup rows:** both `recheck2` `browser.txt` logs show GROUP 8 PASS with no FAIL line.
  - `typed-clean` ran on the late path.
  - `typed-early` ran on the document_start path.
  - `typed-late` ran on the late path, each with its guarded 0/1/1, in both installs.
- **Latency:** both gates `passed:true`, no failures, at 60 / 20 samples. The clients hold 1,080 and 360 rows.
  - **REPORT's table:** every plain and instrumented median/p95 in the table, and the worst of both, equal the
    artifacts.
  - **Runner factors:** plain 1.293 / 1.122 / 1.081 and instrumented 0.868 / 0.990 / 0.993, as REPORT says.
- **Budget:** `gh run list` gives 266 `control-chrome.yml` runs on `pkg/20-chrome`, and this run is the latest.

### The rules held

- `git diff 8b7e799c 18ff4398 -- control/packaging/aresos-toold.service` is empty.
- `7c59733b..18ff4398` touches nothing in `control/aresos_control/`, `control/chrome/ci/`, `control/checks/`,
  `control/chrome/packaging/`, `build.py`, `manifest.json`, `docs/`, `README.md`, `os/`, `mod/`, `.github/`,
  `STATE.md` or `HANDOFF.md`.
- No extension storage.
- No other tab-group line changed.
- `git diff --check a4143586 18ff4398` is now empty, so my trailing-space note is closed.
- No absolute user path in the round's files.

### Local preflight on `18ff4398`

These are the same commands as the earlier rounds. They ran on a `git archive` export of `18ff4398` in a scratch
directory, with CPython 3.14.6, SQLite 3.50.4, jsonschema 4.26.0 and Node 26.4.0, and wrote nothing to the review copy.

- **Python shards:** 53 / 56 / 49 / 147 = **305 tests, all OK**. One skip: the Linux-only spoofing-socket case,
  which ran `ok` in CI.
- **Node:** **428 / 428 pass**, two more than round 3: the two `group-window` cases.
- **Mutation audit:** **461 rejected, 0 survived, every baseline passed**, including `group-window-drop-window-id`
  and `group-window-no-create-properties`.
- **Generator:** `control/generate.py --check`: "Generated artifacts match definitions".

These equal the builder's record `records/group-window/final-local-53ecc91b.json`: 305 Python, 428 Node, 461
mutations.

**Scratch evidence** (outside the repo): `final-review/recheck-pkg/round4/`, with `api/`, `zips/`, `x/`, `out/` and
the audit outputs.
