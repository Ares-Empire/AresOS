# Security re-check 3, item 4: the group-window fix, package 20 (Chrome tools for Claude), PR #27

**Verdict: SAFE (no FIX open).** The pending FIX from re-check 3 is closed; one note on a pre-existing, by-design
tab move that the fix does not change.

Reviewed: `git diff 7c59733b ca64f23b` (fix `53ecc91b`, then preflight record, whitespace, receipts and REPORT), read
in the detached review copy at `18ff4398` (`git status --porcelain` empty before and after). Against REPORT.md's
Handover and "Group in the tab's own window". No browser was started or touched; no workflow dispatched; one one-shot
`gh run view` (metadata only). Paths are repo-relative.

## Findings

### NOTE 1 (pre-existing, by design, unchanged by the fix): joining an existing Claude group moves a tab from another window into the group's window

- `control/chrome/extension/background.js:449`: with a Claude group in place the call is `chrome.tabs.group({tabIds:[tab],groupId})`;
  Chrome holds a group in one window, so an owner tab taken from another normal window moves into the group's window.
  `admitTab` records `original.window` and `original.index` for exactly this (:438), and `restoreTab` (:401–404) moves
  the tab back and regroups it in the owner's earlier group on release. The tool text says "Take the chosen owner tab
  into the visible Claude group" (`chrome/definitions.py:49`), which is this design: one visible group, the first
  taken tab's window decides where it lives.
- The fix changes only the case with no group: the new group now goes in the taken tab's own window, so that tab never
  moves and a focused popup or app window cannot make the take fail. The residual move is reversed on release; if the
  original window is gone by then, `restoreTab`'s move throws and is swallowed, so the tab stays in the Claude window,
  ungrouped. Harm: a visible, reversible move of the owner's tab while Claude holds it; no document change, no loss.
- Class: NOTE (design, not this round's change). If the lead wants "taking a tab never moves it" to be literally
  true, that is a design change (one Claude group per window) and belongs in a follow-up, or one KNOWN-LIMITS line.

## The lead's questions

### 1. The fix itself

- **The one group-creating call.** `grep` over `background.js` for `tabs.group(`, `tabs.move(`, `tabs.ungroup(`,
  `tabGroups.`, `windows.create`, `tabs.create(`: group calls at :403 (`restoreTab`, always `groupId:original.group`,
  only when `original.group>=0`: it never creates a group, as the builder says) and :449 (`admitTab`, the fixed one);
  `tabs.move` only in `restoreTab` back to `original.window`; `tabs.create({url:'about:blank'})` at :857 (`open`, a new
  tab in the current window, then the same `admitTab`). Popups are `virtualGroup` (window type not `normal`) and make
  no group call. The CI harness makes none; the frozen feasibility checks under `control/checks/17*-chrome/` are not the
  product. No path remains that creates a group in another window.
- **`current` is fresh in the same take.** `admitTab` reads `const current = await chrome.tabs.get(tab)` at its start
  (:429), after `check()`, and uses `current.windowId` both for the `normal`-window test (:431–432), for
  `original.window` (:438) and now for `createProperties.windowId` (:449). No snapshot from an earlier call is used; a
  retake goes through the same `admitTab` (the earlier control was removed by `release`).
- **Window closed or tab moved between `get` and `group`.** A closed window closes its tabs, so `tabs.group` fails;
  `admitTab`'s catch runs `release(tab)` (or detach and `restoreTab`, both no-ops on a gone tab), and nothing moves.
  A tab the owner drags to another normal window in that interval is put back into its original window by the group
  call, the window `restoreTab` would return it to anyway; a drag into a popup window is not possible. Negligible.
- **Take, retake, `open`, popups, `restoreTab`:** covered above; all converge on `admitTab`'s one call or make no group.

### 2. The test and the probes

- `control/chrome_tests/background.test.mjs:1247–1280`: a fake `chrome.tabs` that follows Chrome's documented rule (a
  group without `createProperties.windowId` goes in the last-focused window and moves the tab there; only normal
  windows hold groups); two cases, a focused popup and another focused normal window; each runs the real `take`,
  `release` and `take` again, asserts the new group's window is the tab's, that `tabWindow[7]` stayed, that the call
  was `{tabIds:[7],createProperties:{windowId:1}}`, that a second tab joins by `groupId`, and that `windowMoves` is
  empty. Both cases pass (423 Node tests, 0 fail locally). The two probes, `group-window-drop-window-id`
  (`createProperties:{}`) and `group-window-no-create-properties` (the old call), are recorded `MUTATION REJECTED`
  in `records/group-window/final-local-53ecc91b-mutations.txt:460–461`; with the fake's rule both old shapes put the
  group in the focused window, so the test fails on the old code as claimed.

### 3. The run

- `gh run view 43626497829`: `success`, head `6e8cf12b`. The committed receipt
  (`records/group-window/chrome-43626497829-group-window.json`) lists the ten popup rows passed in both installs,
  `typed-late` "on the late path", and per typed row the install records (`late`/`document_start`, `ready`, document
  tokens hashed) with `popup_window: {type: popup, focused: true}` and `opener_window: {type: normal}`: the re-take
  with the owner's popup focused succeeded and the opener stayed in a normal window. The rows themselves assert
  `popup.window !== parent.window` (`popups.mjs`).

### 4. Nothing else changed

- The diff outside records touches `background.js` (one line plus a comment), `background.test.mjs`,
  `mutation-audit.py` and REPORT. No other tab-group behaviour (name, colour, collapse, membership, release) changed;
  `manifest.json`, `control/settings/`, `control/generated/` and `control/aresos_control/` are untouched; the service
  unit is byte-identical to `8b7e799c`; the storage grep over the extension is empty; nothing new reaches Claude.

## Verified

- Read the fix commit and the whole non-record diff; read `admitTab` from its start, `restoreTab`, and every
  `tabs.group`/`tabs.move`/`tabs.ungroup`/`tabGroups`/`windows.create`/`tabs.create` call site in `background.js`.
- Local: `node --test control/chrome_tests/*.test.mjs` 423 pass, 0 fail (both `group-window` cases among them);
  the probe rejections read from the committed mutation record.
- `gh run view 43626497829` once (metadata saved under `scratchpad/final-review/recheck-sec/`); the run's popup and
  window evidence read from the committed receipt, not from shard logs.
