**FIX NEEDED (1 FIX, already ordered by the lead: the tab-group bug, item 4). This round's own changes add no FIX.**

Package re-check, round 3: `git diff f8b0d83b 7c59733b` (8 commits), REPORT.md's "Gate: old runtime at 20; popup
rows" and "Latency gate: 60 samples" and the Handover. I built none of it. I worked read-only on the review copy at
`7c59733b` and on a `git archive` export in a scratch directory. No browser, no profile, no workflow dispatched.
GitHub: about 16 one-shot calls (run metadata, artifact list, 10 artifact zips, the two latency job logs; the plain
log needed one retry after a stream error).

The gate change does what the lead decided, and nothing else in the check is looser. The popup rows now take their
expected answer from the extension's own record and force each path. The run's records match its artifacts and job
logs. The one open FIX is the product bug run `43620235847` exposed in tab-group handling; the lead has ordered it
fixed, and I count it here only because it is open on the branch until item 4 lands.

## FIX

### FIX-1 (already ordered, item 4): with no Claude group, a take creates the group in the focused window, not the tab's

- **Where:** `control/chrome/extension/background.js:446`,
  `groupId = await chrome.tabs.group({tabIds:[tab],...(groupId === null ? {} : {groupId})})`, after `:672` resets
  `groupId=null` once nothing is controlled.
- **Evidence:** in run `43620235847`, `typed-late` failed in both installs on `take_tab` of the opener (both recheck2
  `browser.txt`, line 38/51): "Tabs can only be moved to and from normal windows". The owner's popup was the focused
  window.
- **Harm:**
  - With a popup or app window focused, `take_tab` fails.
  - With another normal window focused, Chrome's default (`createProperties.windowId` is the current window) would
    move the owner's tab into that window. Taking must never move it.
  - The failed path leaves the tab where it was: `grouped` stays false, so `restoreTab` isn't needed.
- **Fix (the lead's order):** when no group exists, create it in the tab's own window
  (`createProperties:{windowId:current.windowId}`), with a background test and a removal probe. `typed-late` then
  covers it in the browser. I'll check it as item 4.

## KNOWN LIMIT

None new.

## NOTE

1. **A verbatim CI log record again carries a trailing space:**
   `records/gate60/final-local-b3d6e4f2-python-0.txt:52` (`git diff --check f8b0d83b 7c59733b`). It's the same
   `test_s1_to_s12…` line fixes b cleaned once. Harmless; a preflight check run on committed records would stop it
   coming back.
2. **`typed-clean` still depends on timing for which path it takes.** It now always asserts the right answer for the
   path the record names, so it can no longer fail on the race or pass against the record. Run `43620235847` gave it
   the late path in both installs. Kept on purpose (REPORT: the only row where Claude's own click opens a popup with a
   text field). No action.

## Verified

### 1. The latency gate

**The constants** (`control/chrome/ci/latency-targets.json:31-36`):
- `samples_per_call: 60`, `old_runtime_samples_per_call: 20` and `measurement_samples_per_call: 20`.
- The lead's lines: `samples_basis` "Set by mac-aresos-control, 2026-11-14, after run 43603381599" and
  `old_runtime_samples_basis` "… after run 43613647256", each with its reason.
- The client (`latency-probe.mjs` `samplesFor`, picking by `LATENCY_BASELINE`, which `latency-pair.sh` sets per
  container), the summary (`samples_for`) and the check (`sample_counts`, `latency-check.py:13`) read them from that
  one file.
- The check also asserts that the old runtime's count equals the reference's (`:21`) and that every count is a whole
  number of at least 20.

**The old runtime matches the reference:**
- **Positions:** `positions(baseline)==positions(reference['baseline'])` (`:88`) pins the old runtime's input samples
  to the reference's exact positions.
- **Every call:** the summary requires every call at positions 0 to count−1.
- **Ratio:** the runner factor is computed old-at-20 over reference-at-20 (`:110`).
- **Tests:** `test_gate60b_the_runner_factor_reads_the_old_runtime_at_the_reference_positions`. The real reference's
  own old runtime gives exactly 1. Positions 40-59, an old runtime at 60, or a count other than the reference's all
  refuse.

**The arithmetic:**
- `test_gate60_three_slow_samples_of_sixty_pass_and_a_fourth_fails` runs the production summary and check, and pins
  60 / 20 and the lead's line.
- At 60 samples, 3 slow samples pass and 4 fail on p95 alone (`target_miss`, no regression). At 20, 1 passes and 2
  fail.
- `p95()` (`:29`) is ⌈0.95·n⌉−1: index 18 at 20, as the old fixed `[18]`, and index 56 at 60.

**Nothing else loosened:**
- These are unchanged: the ceilings, `target_miss=any(…)` against ceiling×allowance, the reference thresholds
  (`×1.5+10`, `×1.75+20`, both must cross), the `.25-2.5` runner bound, `allowance=max(1,noise)` and the 520-750 ms
  wait check.
- Each measurement is validated at its own count (current 60, old 20, reference 20); a 20-sample current run now
  fails.
- The same percentile rule applies on both sides of the reference comparison.

**Probes:** all rejected in my local audit:
- `gate60-*` (5);
- `gate60b-old-runtime-back-to-60` (the lead's);
- `gate60b-check-{old-at-current-count,ratio-at-current-count,positions-unchecked}`;
- `gate60b-summary-*` (2), `gate60b-client-*` (2);
- the re-aimed `final-f4-median-or-p95-ceiling` and `post18d-sparse-expiry-diagnostic`.

### 2. The popup rows

**Each row forces its path** (`control/chrome/ci/popups.mjs:65-104`):
- **`typed-early`:** `fixture.hold(id)` holds the popup's document until the extension's own `popup_admitted` audit
  line appears. That line comes at the end of `admitTab` (`background.js:454`), after `initializeTab` → `prepareTarget`
  has set the startup breakpoint, so the released document always pauses for a document-start install.
- **`typed-late`:** the owner opens the popup from an uncontrolled opener (`ownerOpenPopup(tab,{id,mode})`). The row
  asserts `controlled:false` and waits for the load, then Claude takes the opener and the popup: a late reader.
- **Both forced rows** also assert that the record names the path they force (`firstAnswer`, `:25`, against
  `FORCED_PATHS`, `:19`). If forcing ever failed, the row fails; it can't pass on the wrong path.

**The expectation comes only from the extension:**
- `recordedPath` (`:10`) reads `installs` from `control_status`, matches the popup's tab and the reader document id
  of the clicked reference, and needs exactly one record.
- A `document_start` record counts only when `ready`.
- `install` is set only by the extension's own code paths: `install:'document_start'` in the startup-breakpoint
  install (`background.js:199`), `install:'late'` in `lateReader` (`:270`).
- The document id is the reader's isolated-world token. Nothing a page sets reaches either value.

**`installs` is safe:**
- `installRecord()` (`background.js:228`) computes from `preloadTargets` on demand, only for tabs whose control epoch
  still matches. It returns tab, document id, path and `ready`.
- It sits in background memory only, with no extension storage (grep is empty).
- No decision reads `install`; its only reader is `installRecord`.
- `control_status` is a background command that only the CI service wrapper sends. The service's adapter never calls
  it and no Claude tool reaches it, so nothing new reaches Claude.

**Probes:** `gate60b-popup-either-answer` (the lead's "accepts either answer") is rejected, along with
`-path-by-mode`, `-forced-path-unchecked`, `-early-no-hold`, `-early-no-admission-wait`, `-late-by-claude-click`,
`-record-any-tab`, `gate60b-record-{late-as-start,not-in-status,past-control}` and `gate60b-fixture-hold-ignored`.

**In run `43620235847`:**
- Both recheck2 `browser.txt` logs show `typed-clean` "on the late path" and `typed-early` "on the document_start
  path", each with its guarded 0/1/1, in both installs.
- Then `typed-late` hit FIX-1 before its popup was taken.

### 3. The other changes in the diff

- **Every app's instructions within 4,096:** the test iterates `sorted(APPS)` (control 1,652, testapp 1,652,
  mail 2,426, chrome 4,052). Probe `gate60-instructions-every-app`.
- **Index rebuild in one transaction:** `BEGIN` before `DROP`/`CREATE` (`storage.py:308-309`), so a failed rebuild
  rolls back to the old index. Covered by `test_a_rebuild_that_fails_after_its_drop_keeps_the_old_index` and probe
  `fixesb-recheck-index-one-transaction`. `OPEN_OPERATIONS` is unchanged and still the one definition.
- **Typing record symbol:** it is now `aresos.chrome.typing.v2` (`guard.js:128`), with a test and probe
  `gate60-typing-symbol-v1`. This closes my round-2 NOTE 1.
- **REPORT wording:** the two nits are corrected (3,999 characters; the medians are close, not equal), closing my
  round-2 NOTE 4. The bytes-versus-characters point is stated as the rule.

### 4. Run `43620235847` against its artifacts

- **Jobs:** one `gh run view`: head `07c05de0`, 28 jobs. 24 succeeded. Four failed: `fixtures (external, recheck2)`
  and `fixtures (policy, recheck2)`, each 4.2 min, plus `aggregate (external)` and `aggregate (policy)`.
- **Artifacts:** all 10 downloads equal GitHub's SHA-256 digests. Their members are flat, with no profile directory.
- **Python shards:** 53 / 56 / 49 / 147 = 305, all OK.
- **Latency gates:** both `passed:true` with no failures. Each reports 60 / 20 / 20 for current, old and reference.
  - **Samples:** the clients hold 1,080 rows (60 per call and phase, positions 0-59) for the current runtime and 360
    (20, positions 0-19) for `ab7aba92`, in both profiles.
  - **REPORT's table:** every plain and instrumented median/p95 in the table, and the worst of both, equal the
    artifacts.
  - **No runner credit:** I recomputed both gates at allowance 1, and no call is over a ceiling or crosses the
    reference.
- **Runner factors** (from the gates): plain 1.074 / 1.076 / 1.039, instrumented 1.243 / 1.475 / 1.439 (fresh /
  1,000 / 4,000), as REPORT says.
- **Durations:**
  - The jobs took 11.9 (plain) and 12.9 (audit) minutes, against 19.8 and 20.6 in `43613647256` per the committed
    receipt.
  - In the job logs, the current runtime's container ran 5.8 min (plain, 17:18:20 → 17:24:07) and 6.0 min (audit,
    17:18:19 → 17:24:20). The old runtime's ran 4.9 min (17:24:10 → 17:29:05) and 5.6 min (17:24:23 → 17:30:01).
  - The logs print "1080 calls, 60 per category … current" and "360 calls, 20 per category … ab7aba92".
  - The longest job was `fixtures (external, core)` at 38.0 min.
- **Budget:** `gh run list` gives 265 `control-chrome.yml` runs on the branch; the last three are `43603381599`,
  `43613647256` and `43620235847`.

### 5. The rules held

- `git diff 8b7e799c 7c59733b -- control/packaging/aresos-toold.service` is empty.
- `f8b0d83b..7c59733b` touches none of these: `docs/control/CONTROL.md`, `docs/design/`, `docs/control/PLAN.md`,
  `docs/control/FEATURES.md`, `README.md`, `os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`,
  `HANDOFF.md`, `.github/`, `build.py`, `manifest.json`, `control/chrome/packaging/` and
  `control/aresos_control/chrome/`.
- No tab-group line changed; the round's `background.js` diff is the install record and `control_status`.
- The hold window and its gate check are unchanged.
- No renames or deletions.
- No extension storage.
- No absolute user path in the round's files.

### 6. Local preflight on `7c59733b`

These are the same commands as rounds 1 and 2. They ran on a `git archive` export of `7c59733b` in a scratch
directory, with CPython 3.14.6, SQLite 3.50.4, jsonschema 4.26.0 and Node 26.4.0, and wrote nothing to the review copy.

- **Python shards:** 53 / 56 / 49 / 147 = **305 tests, all OK**. One skip: the Linux-only spoofing-socket case.
- **Node:** **426 / 426 pass**. With `4d0a3f6c`, the popup test's stand-in prints no `POPUP` evidence lines.
- **Mutation audit:** **459 rejected, 0 survived, every baseline passed**. That covers the 27 new probes of this
  diff, among them the lead's `gate60b-popup-either-answer` and `gate60b-old-runtime-back-to-60`, plus the re-aimed
  `final-f4-median-or-p95-ceiling` and `post18d-sparse-expiry-diagnostic`.
- **Generator:** `control/generate.py --check`: "Generated artifacts match definitions".

These match REPORT's "305 Python, 426 Node and 459 mutations" for `07c05de0`. `4d0a3f6c` changes test output only,
and `7c59733b` changes only REPORT.md and records.

**Scratch evidence** (outside the repo): `final-review/recheck-pkg/round3/`, with `api/` (run metadata, artifact
list, the two latency job logs, run list), `zips/` and `x/` (artifacts) and `out/` (preflight logs).
