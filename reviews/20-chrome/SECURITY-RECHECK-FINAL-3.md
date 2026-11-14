# Security re-check 3: gate at 20/60 and the popup rows, package 20 (Chrome tools for Claude), PR #27

**Verdict: SAFE (no FIX open in this diff).** One pre-existing product bug is outside the diff and already in
hand as the lead's item 4 (noted below so SAFE is not read as covering it); one note.

Reviewed: `git diff f8b0d83b 7c59733b` (nine commits), read in the detached review copy at `7c59733b`
(`git status --porcelain` empty before and after). Against REPORT.md's Handover, "Gate: old runtime at 20; popup rows"
and "Latency gate: 60 samples". No browser was started or touched; no workflow dispatched; one one-shot `gh run view`
(metadata only). Paths are repo-relative.

## Findings

### Outside this diff, pending as item 4: a re-take with no Claude group can move or fail on the owner's tab

- `control/chrome/extension/background.js:403` (`admitTab`): `chrome.tabs.group({tabIds:[tab], …groupId})` with no
  `createProperties.windowId` when `groupId` is `null`, which `release` sets once no controlled tab is left (:672).
  Chrome creates the new group in the current (last-focused) window and moves the tab there; a popup or app window
  refuses the move. Run `43620235847` (`gh run view`: failure, head `07c05de0`) showed the refusal in both installs
  (`take_tab` → `unknown`, "Tabs can only be moved to and from normal windows").
- Scenario: Claude has released its last tab; the owner has two normal windows and is working in the second; Claude
  takes a tab of the first. The tab moves into the owner's second window. Harm: the owner's tab moves (breaking his
  normal use); in the popup case the take fails with `unknown`, which is noisy but safe.
- Class: FIX, pre-existing (not introduced by `f8b0d83b..7c59733b`; `admitTab` is unchanged in this diff) and already
  the lead's item 4. Smallest fix, as the report recommends: `createProperties:{windowId:current.windowId}` on the
  new-group call, a background test and a removal probe; `typed-late` then covers it in CI. I will check that diff
  when it arrives.

### NOTE 1: `installs` is a CI-only view, and it should stay one

- `background.js:228–230` (`installRecord`) and :837 (`control_status`). Nothing in `control/aresos_control/` calls
  `control_status` (grep: zero hits); only the CI service wrapper (`control/chrome/ci/service.py:66–68`, through a
  fixture file) and the CI admin shim issue it, so `installs` never reaches Claude in production. Its rows are tab id,
  the reader's random document token (`reader.js:20`, `randomToken()`), `install` and `ready`, for documents of
  currently controlled tabs only (`controlled.get(state.tab)?.epoch===state.epoch`): no URL, no title, nothing of an
  owner tab Claude does not control. If a later package exposes `control_status` to Claude, this row set is the thing
  to review again; today nothing to trim or mark.

## The lead's questions

### 1. The latency gate

- **Nothing loosens what the gate enforces.** `control/chrome/ci/latency-check.py`: the ceilings
  (`latency-targets.json`, unchanged) are applied per call and phase with "median or p95 over the ceiling fails"
  (:124), and the reference comparison keeps "both must cross" (:123). The sample counts come from one constant each
  (`samples_per_call: 60`, `old_runtime_samples_per_call: 20`, `measurement_samples_per_call: 20`), `sample_counts`
  refuses anything under 20 and an old-runtime count different from the frozen reference's, `positions()` requires the
  old runtime at exactly the reference's sample positions, and `validate_pairs` requires the full sample set for each
  runtime at its count. The runner factor is therefore like-for-like (old runtime at 20, positions 0–19, against the
  reference's 20 at the same positions); in run `43613647256` the 60-sample old runtime had inflated it to 1.22 and
  so the allowance, which this change removes. More samples with the same ceilings tighten, not loosen: the p95 is the
  57th of 60 (`p95()`, same rule as the summary's), so a ceiling miss needs four slow samples instead of two.
- **The 525 ms safety wait stays checked separately** (:100): for every runtime at its own count,
  `wait['samples']==count` and `520<=median<=p95<=750` per input call per phase; the paired-wait subtraction before
  percentiles is unchanged. `test_latency` (77 Python tests pass locally) pins the constants, the positions rule, the
  factor of exactly 1 on the reference's own old runtime, and refuses the old runtime at 60 or at positions 40–59.
- The client (`latency-probe.mjs`) picks the count by the container's runtime (`LATENCY_BASELINE`) and asserts
  `samples>=20`; the summary (`latency-summary.py`) requires positions 0..count−1 per call and phase. Harness only.

### 2. The popup rows

- **A page cannot influence the recorded path.** `install:'document_start'` is written only in `preloadEvent`
  (`background.js:199`), the extension's own Debugger-breakpoint path on its `context.js` before page scripts, and
  `ready` only after that install completed (:219); `install:'late'` only in `lateReader` (:270). Both run in the
  background from CDP results, never from page values; a page can only be a document that loads (document start) or
  that already loaded (late). Nothing the page sets is read into the record.
- **A late install cannot look early.** The product decision does not read `install` at all: `needs_reload` comes
  from `isPreloaded` (:231), which requires `ready===true`, and `ready` is set only on the document-start path; a
  late document keeps `ready:false` for its lifetime (grep: the only `ready=true` is :219). So `reload_required` for
  a late or owner-touched popup is unchanged product behaviour, which run `43620235847` confirmed for `typed-clean`
  (late → `reload_required`, one guarded reload) and `typed-early` (document start → `stale_reference`) in both
  installs. The rows' `recordedPath` (`popups.mjs:10–16`) requires exactly one record for the popup's tab and
  reader document and accepts `document_start` only with `ready===true`; `firstAnswer` asserts the forced path and the
  exact answer; the lead's "either answer" variant is a rejected probe.
- **`installs` is read-only and in background memory**: a fresh array per call, no `chrome.storage` or any other
  storage (grep over the extension: zero hits), no new permission. Leakage: NOTE 1 (none today).
- **The early path's `stale_reference` is safe.** On the document-start path the guard listened from before page
  scripts, so an untouched field (value equal to default, no trusted input, no mark) is known untouched; the first act
  reloads without a report and every reference is stale, so Claude must read again before acting. Any owner typing in
  that popup before the click produces trusted input marks and the report (`reload_required`), as the `dirty` row
  shows.

### 3. The two round-2 notes

- `test_questions.py:456–466`: iterates `sorted(APPS)` and asserts the four known apps are in `APPS`.
- `storage.py:309–315`: `BEGIN` unless a transaction is open, then `DROP`/`CREATE`/`commit`, `rollback()` on a
  storage error, so a failed rebuild keeps the old index; `test_full_disk_reads` has the case and passes.
- Also in the diff: the typing record moved to `aresos.chrome.typing.v2` (`guard.js:128`) so a record left by an
  earlier build's guard in the same isolated world is never read with the new shape. Correct and harmless.

### 4. The rules

- Service unit byte-identical to `8b7e799c` (empty diff; pin tests pass). `manifest.json`, `control/settings/` and
  `control/generated/` unchanged in this diff; no `key`; storage grep empty. What reaches Claude is unchanged:
  `installs` is on `control_status`, which no service action exposes.

## Verified

- Read the whole non-record diff: `background.js`, `guard.js`, `storage.py`, `latency-check.py`,
  `latency-probe.mjs`, `latency-summary.py`, `latency-targets.json`, `popups.mjs`, `browser.mjs`, `fixture.mjs`,
  the test files, and the three report sections; checked `admitTab`, `release`, `isPreloaded` and the `control_status`
  callers in the unchanged code.
- Local runs, no browser, `PYTHONDONTWRITEBYTECODE=1`: `node --test control/chrome_tests/*.test.mjs` 421 pass, 0
  fail (the popup stand-in rows, the install-record and hold tests, the gate60b client test among them);
  `python3 -m unittest test_latency test_full_disk_reads test_questions test_unit` 77 OK.
- `gh run view 43620235847` once (failure, head `07c05de0`, as REPORT says; metadata saved under
  `scratchpad/final-review/recheck-sec/`).
- Not run or read: the run's shard logs (REPORT's `installs` receipts taken as its claim, consistent with the code);
  the item-4 fix (not pushed).
