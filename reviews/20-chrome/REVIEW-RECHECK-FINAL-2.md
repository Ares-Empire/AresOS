**SAFE (no FIX open)**

Package re-check, round 2, of fixes b only (`briefs/20-final-fixes-b.md`, G1–G4 and the lead's three additions):
`git diff 88c34297 f8b0d83b` and its five commits, REPORT.md's "Fixes b" section and Handover. I built none of it.
I worked read-only on the review copy at `f8b0d83b` and on `git archive` exports in a scratch directory. No browser,
no profile, no workflow dispatched. GitHub: about 18 one-shot calls (run metadata, the artifact list, 11 artifact
zips, the failed-job logs, one run list).

The round closes the package FIX (G1) as the brief says. It also hardens the lost-finish corner (G2) in the direction
of asking, adds the narrow page-action line (G3) and closes the cheap notes (G4), each with tests and removal probes.
The records I checked match the run's artifacts. The latency gate's p95-only failure is outside this scope, as the
lead asked; I only checked the records.

## FIX

None.

## KNOWN LIMIT

None new. The three KNOWN-LIMITS entries this round changed or added are judged under Verified, item 3.

## NOTE

1. **The typing record changed shape but kept its name.** The record in the document's isolated world
   (`guard.js:126`) went from `{fields,gap}` to `{fields,releases}`, but its symbol is still
   `aresos.chrome.typing.v1`. If a document ever outlived an extension update in the same isolated world, the new
   guard would read the old shape: `releases` undefined, `++` gives `NaN`, and `typingGap` is false. Releases are
   then not counted for that document. The image updates the extension at reboot, so this can't happen in normal
   use. Bumping the symbol to `…typing.v2` is the cheap way to rule it out.
2. **The 4,096 test counts characters, not bytes.**
   - `test_fixes_b_server_instructions_fit_the_native_cli_limit` uses Python's `len`.
   - All three apps' instructions are ASCII today (testapp 1,652, mail 2,426, chrome 4,052), so characters, UTF-16
     units and bytes agree.
   - A later non-ASCII character such as "…" would make them differ. Measuring `len(s.encode())` would bound all
     three.
   - Chrome's margin is 44 characters.
3. **G2 also turns Claude's own typing into the owner's when a page dialog interrupts it.** Answering a dialog
   re-arms the guards with a new nonce (`background.js:152`). `arm` then settles the typing dispatch that opened the
   dialog as the owner's, because that dispatch can no longer finish. The cost is one extra question before
   discarding typing Claude did in such a flow. That is the direction G2 intends, and normal typing is unaffected:
   the run's `final-discard-editor-typed-by-claude` and `final-discard-react-typed-by-claude` rows still get "(typed
   by Claude)" and "All of it is Claude's own typing" in both installs.
4. **Small wording in REPORT:**
   - "From 4,000 to 4,149 characters": the length before fixes b was 3,999.
   - "The medians are unchanged and equal the plain profile's": the instrumented medians are close, not equal (fresh
     `navigate` 39.0 against 36.4, 1,000 `navigate` 38.7 against 37.6).

   Neither changes a conclusion.

## Verified

### 1. G1: a release cancels Claude's earlier marks

- **Release count:** the typing record counts releases. `dispose` does `typing.releases++` (`guard.js:521`), and
  `typingGap` is `releases>0`.
- **Per-mark count:** `noteTyping(node,true)` stamps `marks.release=typing.releases` (`guard.js:133`). The reader's
  `typedByClaude` goes through the same function.
- **`typist`** (`reader.js:524`) calls a field Claude's only when all of these hold: `claude`, no `owner`,
  `release===typingReleases`, and the mark is confirmed. A missing getter fails toward the owner. The rule is the
  same for fields, editors and design mode.
- **Demonstration:** my round-1 scenario now comes out right. Claude marks, the tab is released, the owner edits,
  and the tab is retaken: "(typed by the owner)", `claude_only:false`.
- **Pinned tests flipped:** `reader.test.mjs` step 6 and step 7 now expect the owner after a release. The comment
  at `reader.js:564` now matches the code.
- **New tests:** `fixes b G1 …` in `reader.test.mjs` (field, editor and design mode; voided again by the next
  release) and in `page.test.mjs` (the real guard; the retake's guard shares the record).
- **Probes:** `fixesb-g1-*` (4); `step5-guard-gap` and `step5-typist-claude-only` follow the new text.
- **"No mark after a retake sits on unseen typing" holds in the code:**
  - `release` deletes the tab's `preloadTargets` (`background.js:657`), and only a document-start install sets
    `ready` (`:219`).
  - So a retaken document is not preloaded, `facts` gives `needs_reload` (`:723`), and `input`/`resume` refuse until
    the guarded reload (`:964`).
  - That reload runs `requireDiscard` first (`:939-944`). The reload brings a new document with a new record.

### 2. G2: a lost finish leaves its marks the owner's

- **What it does:**
  - Claude's marks from the dispatch in flight go into the guard's `unconfirmed` set (`guard.js:143`).
  - The matching `finish` clears them (`:513`).
  - The next `arm` turns anything left into owner marks (`settleUnconfirmed`, `:503`).
  - `typist` treats an unconfirmed mark as the owner's.
- **It can't misattribute in the risky direction:**
  - The only new path converts Claude marks into owner marks, never the reverse.
  - Marks the reader stamps for `select`/`check` never enter `unconfirmed`.
  - A late `finish` from an earlier dispatch can't clear a newer one's set, because the nonce must match.
  - A release drops the set, but G1 then voids those marks anyway.
- **Owner attribution can't block work:** it only changes the report's wording to "Tell the owner…". The real-
  browser rows show normal finishes confirm Claude's typing (NOTE 3).
- **Lost-finish paths:** I checked both against `background.js:497-512`:
  - `dialogPauseFailed`;
  - a `finish_input` message failing on an unchanged document.

  The re-finish after a non-managed dialog uses the original nonce (`:1209`) and still clears the set.
- **Tests and probes:** `fixes b G2 …` (reader and page); probes `fixesb-g2-*` (4).
- **KNOWN-LIMITS line 24** states the span as "from arming the page until the dispatch's finish", and the lost-finish
  corner as it now behaves.

### 3. G3 and KNOWN-LIMITS

- **The code-path claim holds:**
  - The first act after every take or retake is checked: input and resume refuse while `needs_reload`, and
    `prepare_control` reports before reloading.
  - `navigate` (address, reload, back, forward) and `close_tab` each call `requireDiscard`.
  - Reads, `stage_file`, `release_tab` and `stop` drop no document.
- **The new line is as narrow as the lead asked:**
  - only "while he holds the tab";
  - the first act after every take and retake "is still checked";
  - Claude's `fill` over a field the owner typed into is "the narrower case".
- **Each changed entry states what it is, the harm and why it's accepted:**
  - the typing-mark line (24);
  - the retake line (27, now only the cost of one extra question);
  - the page-action line;
  - the word-heuristic line (API-key names; no bare `token`, with the CSRF reason);
  - the browsing-target line (now also cites the passing run `43593989287`).

  None hides a FIX. The stray blank line is gone; the remaining blank lines at 2 and 28 are the file's own.

### 4. G4

1. **Index after recovery.**
   - `_index_open_operations()` now runs after the last `recover_intents(self)` (`storage.py:278-280`), with the old
     rule's comment back.
   - `test_the_index_is_added_after_recovery_and_spends_only_unheld_space` spies the ledger at the call: the
     reservation's `cancel:` hold is present, and the holds equal the final ones.
   - Probe `fixesb-g41-index-before-recovery`. The full-disk open test passes unchanged.
2. **Index identity.**
   - At open, `sqlite_master.sql` is compared with `OPEN_INDEX` (`storage.py:297-298`). A mismatch is admitted, then
     `DROP` and `CREATE` run inside the same storage-tolerant `try`.
   - On a full disk, `DROP` itself fails, so the old index stays. Either way the reads keep working through the
     primary key, and the next open replaces it.
   - `test_an_index_from_another_definition_is_replaced_at_open_and_a_full_disk_only_defers_it` covers it:
     - the planner skips the stale index for every selective shape;
     - a full-disk open keeps it and returns the same rows for all 48 shapes;
     - the next open rebuilds it, and every plan uses it again.
   - It passed on SQLite 3.45.1 in CI and 3.50.4 locally. Probes `fixesb-g42-name-only` and `-no-drop`.
3. **API-key names.**
   - `api[\s_-]?keys?` and `api[\s_-]?schl(?:ü|ue)ssel` are whole tokens.
   - Tests cover seven names in label, `name` and `id` form, watched and unwatched. Ten ordinary or token names stay
     readable: `Rapid key`, `Keyword`, `csrf_token`, `_token`, `Token`, and others.
   - There is no bare `token`; the reason is in the reader comment and in KNOWN-LIMITS.
   - Probes `fixesb-g43-api-key-{label,name,id}`.
4. **Probe aim.**
   - `post18d-malformed-state-expiry` hits the `states` filter's own clause again (the `'{'))")` form).
   - The new `fixesb-malformed-state-index-clause` hits the copy in `OPEN_OPERATIONS`.
   - Both are rejected.
5. **Cosmetic:** `git diff --check a4143586 f8b0d83b` is empty, and the KNOWN-LIMITS blank line is gone.

### 5. The six security notes

REPORT's table lists all six with what happened to each:
- 1, labels are page text: done, pinned, probe `fixesb-note1-labels-are-page-text`.
- 2, `fill` over owner text: done, inside the G3 line.
- 3, the allow dialog's account text: left, with its reason.
- 4, the browsing-target line cites a passing run: done.
- 5, CI stands in for the seat: left to 18c-b.
- 6, a left-behind `operation_headers` index: left, with its reason.

The reasons are true to the code.

### 6. The instructions limit and `native-precedence`

- **The cause, from run `43603381599`'s `chrome-precedence` artifact** (`version-claude.txt`: 2.1.319):
  - At `e654baff`, chrome's instructions were 4,149 characters.
  - In the recorded request, the `## chrome` section shares exactly 4,096 characters with them and then reads
    "… [truncated]".
  - `control/boundary/precedence.py:40` then failed with "Server instructions shortened or absent: chrome". The
    failed-job log has the same line.
- **The fix:** NOTE 1's short wording brings chrome to 4,052. The new test holds testapp, mail and chrome within
  4,096, and probe `fixesb-instructions-cli-limit` puts the long wording back and is rejected.
- **The aggregates:** both failed-job logs end with `ENOENT … .work/native-precedence/chrome-precedence.json`, as
  REPORT says.

### 7. The records

- **Run `43603381599`:**
  - **Jobs:** one `gh run view`: head `e654baff`, 28 jobs. 24 succeeded. Four failed: `native-precedence`,
    `latency (audit)`, `aggregate (external)` and `aggregate (policy)`.
  - **Artifacts:** the 11 I downloaded all have SHA-256 equal to GitHub's digests. Their members are flat, with no
    profile directory.
  - **Shards:** the Python shards are 53 / 56 / 48 / 142, all `OK`, head `e654baff`, and the Linux-only spoofing
    case reports `... ok`. The two review shards pass 23 checks each, GROUP 8 included, with no failure.
  - **Latency gates:**
    - **Plain:** `passed:true`.
    - **Audit:** `passed:false`, with exactly three `target_miss` and no regression: fresh `fill`, fresh
      `navigate` and 1,000 `navigate`.
    - **REPORT's table:** every plain and instrumented median/p95 and the `ab7aba92` plain column equal the
      artifacts. So do the "worst of both at 4,000" numbers.
  - **The spike samples match REPORT:**
    - **Fresh `navigate`:** 18 samples at 34-105 ms, plus 227 and 725.
    - **Fresh `fill`:** 17 samples at 558-668 ms, plus 934, 971 and 1,383.
    - **Old runtime, same audit job:** at 1,000 `free_click`, six samples of 946-1,141 ms against a median of
      759.0.
    - **Plain profile:** its maxima stay low.
  - **Spread:** in the instrumented profile the outliers are spread over most calls at fresh and 1,000, including
    `asking_click` (64 and 233 ms), which involves no typing. That fits runner noise rather than fixes b's code.
    Fixes b's per-call additions are a Set and two getters, and the storage changes run only at open. Whether the
    gate changes is the lead's call, and out of scope here.
- **Budget:** `gh run list` gives 263 `control-chrome.yml` runs on `pkg/20-chrome`, which matches.
- **Head:** `25fe7aaa..f8b0d83b` changes only REPORT.md and records.

### 8. The rules held

- `git diff 8b7e799c f8b0d83b -- control/packaging/aresos-toold.service` is empty.
- `88c34297..f8b0d83b` touches none of these: `docs/control/CONTROL.md`, `docs/design/`, `docs/control/PLAN.md`,
  `docs/control/FEATURES.md`, `README.md`, `os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`,
  `HANDOFF.md`, `.github/`, `build.py`, `manifest.json`, `control/chrome/packaging/` and `control/chrome/ci/`.
- No renames or deletions.
- No extension storage.
- No absolute user path in the round's added or changed files.
- `OPEN_OPERATIONS` is untouched and is still the one definition. `OPEN_INDEX` is built from it, the identity check
  compares against `OPEN_INDEX`, and the plan and one-definition tests pass.

### 9. Local preflight on `f8b0d83b`

These are the same commands as round 1 (those in `records/post18d/final-local-a4143586.json`). They ran on a
`git archive` export of `f8b0d83b` in a scratch directory, with CPython 3.14.6, SQLite 3.50.4, jsonschema 4.26.0 and
Node 26.4.0, and wrote nothing to the review copy.

- **Python shards:** 53 / 56 / 48 / 143 = **300 tests, all OK**. One skip: the Linux-only spoofing-socket case,
  which ran `ok` in CI.
- **Node:** every `control/chrome_tests/*.test.mjs` plus `audit-streams.test.mjs`: **415 / 415 pass**.
- **Mutation audit:** **432 rejected, 0 survived, every baseline passed**, including all 18 of this round's probes:
  - `fixesb-g1-*` (4), `fixesb-g2-*` (4);
  - `fixesb-g41-index-before-recovery`, `fixesb-g42-name-only`, `fixesb-g42-no-drop`;
  - `fixesb-g43-api-key-{label,name,id}`;
  - `fixesb-note1-labels-are-page-text`, `fixesb-instructions-cli-limit`;
  - `fixesb-malformed-state-index-clause` and the re-aimed `post18d-malformed-state-expiry`.
- **Generator:** `control/generate.py --check`: "Generated artifacts match definitions".
- **Unit pin:** the unit is unchanged since `8b7e799c`, as in item 8.

These match REPORT's "300 Python, 415 Node and 432 mutations" for `25fe7aaa`; `f8b0d83b` adds only REPORT.md and
records.

**The retake demonstration from round 1, rerun on `f8b0d83b`'s reader:**

```
before release: {"unsaved":true,"fields":["field \"Draft\" (typed by Claude)"],"claude_only":true,...}
after retake:   {"unsaved":true,"fields":["field \"Draft\" (typed by the owner)"],"claude_only":false,...}
```

**Scratch evidence** (outside the repo): `final-review/recheck-pkg/round2/`, with `api/` (run metadata, artifact
list, failed-job log, run list), `zips/` and `x/` (artifacts) and `out/` (preflight logs).
