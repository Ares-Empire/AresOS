**FIX NEEDED (1 FIX)**

Package re-check of the final fixes round of package 20 (draft PR #27, `pkg/20-chrome`): `git diff a4143586 b698d68e`
and its commits, against `reviews/20-chrome/REVIEW-FINAL.md` (5 FIX), `reviews/20-chrome/SECURITY-FINAL.md` (3 FIX),
`briefs/20-final-fixes.md` and the lead's later decisions recorded in REPORT.md's step sections. I built none of it.
I worked read-only on the review copy at `b698d68e` and on `git archive` exports in a scratch directory. No browser,
no profile, no workflow dispatched. GitHub: one-shot `gh run view` / artifact downloads only (about 20 calls). F7's
depth (polkit) belongs to the parallel security re-check; I checked its records, tests, probes and packaging.

The round closes all eight findings as the brief and the lead decided, every one with a test that fails without its
fix and a removal probe. The records I checked are true, including run `43593989287` (28/28 jobs) re-audited from
its artifacts. One gap remains, in the lead's retake rule: it counts the right fields but lets a mark from before the
release call the owner's edit Claude's own typing, which the tool then says may be discarded without asking.

## FIX

### FIX-1: After a release and a retake, a field Claude typed before the release is still "typed by Claude", even when the owner edited it during the release, and the report then says it may be discarded without asking

**Where:**
- `control/chrome/extension/reader.js:519` (`typist`): a field is Claude's when its record says `claude && !owner`;
  nothing asks whether that record predates the gap.
- `control/chrome/extension/guard.js:123-125` (the document-lifetime typing record, `noteTyping`) and `:508`
  (`dispose` only sets `typing.gap=true`; Claude's earlier marks stay as they were).
- `control/chrome/extension/background.js:607-609`: when every field is Claude's, the report ends "All of it is
  Claude's own typing, so it may be discarded without asking: repeat with discard_unsaved=true", and the shipped
  instruction (`DISCARD_NOTICE`, `control/aresos_control/chrome/definitions.py`) says "Typing marked as typed by Claude
  may be discarded without asking."
- `control/chrome_tests/reader.test.mjs:656-657` pins this behaviour ("Claude's own typing seen before the release
  stays his"), and `reviews/20-chrome/KNOWN-LIMITS.md:27` accepts it.

**Evidence:** the retake rule itself works: after `typing.gap` every non-empty text field counts (`reader.js:528`,
`:559`). But the gap makes the guard blind, and the record still trusts what it saw before. I ran the package's own
reader fixture in a scratch copy: Claude fills "Draft" (mark `{claude:true}`), the guard is released (`gap=true`), the
value changes with no guard listening (the owner's edit), then the reload state is read as at a retake:

```
before release: {"unsaved":true,"fields":["field \"Draft\" (typed by Claude)"],"claude_only":true,...}
after retake:   {"unsaved":true,"fields":["field \"Draft\" (typed by Claude)"],"claude_only":true,...}
```

With `claude_only:true`, `requireDiscard` tells Claude the loss is its own typing. The same holds for an editor and
for a design-mode frame (one `typist` for all three). The code contradicts its own comment at `reader.js:558`
("typing in the gap was unseen, and whoever typed, it's the owner's") and the step-7 test's name ("… counts as the
owner's").

**Scenario:** Claude drafts a post in a tab it opened. The owner presses Stop (or Claude releases the tab) to review
the draft and rewrites a paragraph in that field. Later Claude takes the tab back and navigates away or closes it.
The report reads `field "Draft" (typed by Claude)` and "may be discarded without asking", so Claude repeats with
`discard_unsaved=true`, following the tool. The owner's edit is gone, and nobody asked him.

**Harm:** the owner's typing is lost silently, which is the exact harm `discard_unsaved` exists to prevent (security
FIX 1, the lead's one-flag decision). KNOWN-LIMITS.md:27 accepts it "with the typing-mark case above", but the two
aren't alike. Line 24's case needs the owner's keystroke to land inside the milliseconds of Claude's own dispatch.
Line 27's case is the ordinary hand-back flow: a release exists so the owner can use the tab, and editing Claude's
draft is the likeliest thing he does with it. The entry hides a FIX.

**Smallest fix that closes the class:** a gap voids Claude's earlier marks.
- `guard.js`: keep a gap count in the typing record (`dispose` increments it); `noteTyping(node,true)` stores the
  current count with Claude's mark.
- `typist`: Claude's only when `claude && !owner` and the mark's count equals the record's current count. Otherwise
  the field is the owner's. This keeps Claude's typing after the retake as his, and it covers fields, editors and
  design mode in one place.
- **Tests:**
  - Node (`reader.test.mjs`): a field and an editor Claude marked before a gap report "(typed by the owner)" with
    `claude_only:false`; Claude's typing after the retake is his again.
  - `page.test.mjs`: the guard's count moves at dispose.
- **Removal probe:** the old `typist`.
- **KNOWN-LIMITS.md:27:** rewrite it. The cost is one extra question when Claude's own untouched draft is retaken;
  that errs toward asking, as the rest of the report does.

## KNOWN LIMIT

None new. The entries this round added are judged under Verified, item 8.

## NOTE

1. **The partial index is now created before reservations are loaded**
   (`control/aresos_control/storage.py:196`, before `_load_reservations()` at `:214` and recovery at `:278`).
   - Its `ledger.admit(max(64 KiB, 128 B × rows))` runs while `ledger.holds` is still empty, so the admission ignores
     the held recovery space.
   - The comment F1 deleted with the old index recorded the opposite rule: "Optional speed indexes may spend only
     unheld space, after every prepared recovery and reservation has been reconstructed."
   - The index's real size is a page or two, and creation happens once per store, so the harm is negligible.
   - Suggestion: call it after `recover_intents(self)` (the old place), or record why it must run first.
2. **`_index_open_operations` recognises the index by name only** (`storage.py:289`).
   - If a later build changes `OPEN_OPERATIONS` or `retention.OPEN`, existing stores keep the old index.
   - The planner can't match its WHERE, so every selective shape silently becomes a full walk: correct, but slow.
   - The CI latency fixture builds fresh stores, so it wouldn't notice.
   - Comparing the stored `sql` with `OPEN_INDEX` and rebuilding on a difference closes it. Nothing has been released
     yet, so this is a hazard for later, not a harm today.
3. **Free input that navigates is outside the report.** A free click on a link (or any free input that navigates or
   reloads) in a Claude tab drops the owner's unsaved typing without the `reload_required` report. The lead's list
   (the first act, reload, an address, back, forward, `close_tab`) doesn't include it. If the lead means it to stay
   outside, KNOWN-LIMITS could say so.
4. **Page-supplied labels in the report.** The report's field labels come from the page and sit in the error text,
   not under `untrusted_content`. They are quoted, capped at 80 characters, `"`-free and `visible()`-escaped
   (`bridge.py:111`), and the closing sentence comes from the extension, so a label can't forge it. It is the usual
   page-text residual (KNOWN-LIMITS "Marking page text untrusted…"); I mention it for the security re-check.
5. **The credential word list** has no `token` or `api key` (`reader.js` `credentialTokens`). KNOWN-LIMITS line 8's
   "unknown abbreviation" class covers it; it's a cheap addition if wanted.
6. **The step 6 latency table bolds values over the raw ceiling** that the gate, with its runner allowance, didn't
   count as misses, for example 1,000 `free_click` 680.1/685.7 (`latency-43566651314-plain-gate.json`:
   `target_miss:false`). "Most miss" is still true for that failed run. Historical; no action needed.
7. **One probe changed its aim.** `post18d-malformed-state-expiry` replaces the first occurrence of the
   malformed-state clause. Since step 7 that is inside `OPEN_OPERATIONS` (`storage.py:144`), no longer the `states`
   filter (`:859`). Both clauses are still guarded: I removed only the `:859` one in a scratch copy, and
   `test_malformed_state_still_refuses_expiry_before_deleting_old_files` failed. A second probe aimed at `:859` would
   keep that on record.
8. **Cosmetic:**
   - `KNOWN-LIMITS.md:25` is a stray blank line that splits the list.
   - `git diff --check a4143586 b698d68e` flags one trailing space in a verbatim CI log record
     (`records/final-step7/python-shard-43584711126-0-python.txt:52`).

## Verified

### 1. Every FIX of both reviews is closed

| Finding | Closed by | Test that fails without it | Removal probes |
|---|---|---|---|
| Package FIX-1 / security FIX 3 (F1, full-disk Mail reads) | Primary-key range + unary `+`, forced index gone; then the lead's partial index `operation_open` | `test_full_disk_reads` (48 plans × 4 index states; 1,200-op full-disk Mail read/search/`control_pending`; full-disk open) | `final-f1-*` (4), `step7-*` (11) |
| Package FIX-2 (F2, credential names) | `credentialStems`/`credentialTokens`, `cc-csc` token and history, split labels | `reader.test.mjs` `final F2 …` (56 names × label/name/id × watched/unwatched; 22 ordinary words stay readable) | `final-f2-*` (8) |
| Package FIX-3 / security NOTE 1 (F3, browsing target) | HTML `<base>` only, HTML sanitising, `xlink:show="new"`; `target=""` follows Chrome (the lead's decision, observed on Chrome 157 in 4 rows) | reader and destination-evidence Node rows; 96 browser rows (`GROUP 3 POST18D …`) | `final-f3-*` (8) |
| Package FIX-4 (F4, median-only breach) | `target_miss=any(…)`; the reference keeps `all(…)`; the policy string is updated | `test_latency.LatencyGate` (median-only, p95-only, reference both-cross) | `final-f4-*` (2) |
| Package FIX-5 (F5, absolute paths) | The three records are repo-relative; no new record has a user path (grep of all 208 added/changed files) | Tidiness only per the brief; no preflight grep added (the review's optional suggestion) | none |
| Security FIX 1 (F6, reload report) | `requireDiscard` shared by the first act, reload, address, back, forward, `close_tab`; one flag `discard_unsaved` (the lead's decision) | `background.test.mjs` `final F6 …`/`final discard_unsaved …`/`step 5 …`; `test_questions` schema pass-through; GROUP 8 browser rows | `final-f6-*` (2), `final-discard-*` (11), `step5-*` (12) |
| Security FIX 2 (F7, polkit) | `confirm.py`, policy file, `Daemon.accept_chrome` peer, one dialog, connection binding | `test_owner_confirm` (stub `pkcheck`), real polkitd runs `43556395889`/`43561341511` | `final-f7-*` (21) |
| Notes (withheld-form text, typed-read labels, `visible()` errors, unit pins, stale docs/receipt, dead code) | All folded in | `test_questions`, `test_bridge.ExtensionErrors`, both `test_unit` pins | `final-notes-*` (9) |

All of these probes ran in my local mutation audit and were rejected (see 5).

### 2. The lead's explicit items

1. **The partial index.** `OPEN_OPERATIONS` (`storage.py:143-147`) is both `OPEN_INDEX`'s WHERE and the one term
   `iter_operations` appends to every selective shape (`unresolved`, `legacy_open`, `states ⊆ OPEN`). The test pins:
   - the stored SQL is `OPEN_INDEX`;
   - the set names exactly `retention.OPEN`;
   - every selective shape's SQL carries the term exactly once, and no broad shape carries it.

   The 48 shapes in fresh / old-index / analyzed states give exactly one `SEARCH kv USING INDEX operation_open
   (k>? AND k<?)` for the 36 selective shapes and `sqlite_autoindex_kv_1` for the 12 broad ones. None has a
   `TEMP B-TREE`. I checked the SQL truth tables by hand: notice/ack test every Python-falsy spelling, and a malformed
   state stays in, so the index is a superset of each caller's Python predicate. The callers are `_pending`,
   `_expire`, `retention.expire`, recovery's legacy notices and `unresolved_sent_checks`. The CI step-7 timing record
   (run `43593989287`, shard 0) shows SQLite 3.45.1, indexed 0.009 ms against scans of 5-78 ms.
2. **Full disk at open.** `_index_open_operations` catches `storage_refusal` and `storage_limit`, rolls back and
   records the observation. `test_a_store_without_the_index_opens_and_reads_on_a_full_disk_and_gets_it_later` covers
   it: the main database's page writes fail, every shape returns the same rows through the primary key, and the next
   open adds the index. Probe `step7-full-disk-fatal-at-open`. See NOTE 1 for the order.
3. **The retake rule.** After `typing.gap`, every non-empty `typedField` counts, and empty or non-text fields don't
   (`reader.js:559`; probes `step7-retake-*`). The attribution is FIX-1.
4. **The React rule and the drop-down.**
   - **Plain field:** it counts when `value!==defaultValue`, or when it got input since load (any guard mark) and
     still holds text. A field emptied again isn't reported.
   - **Drop-down:** it compares with HTML's reset state: the marked options, the last for a single choice, or with
     none marked a display-size-1 list's first enabled option. `:disabled` covers disabled optgroups, and a list box
     or multiple select starts with nothing chosen. That matches the HTML selectedness algorithm.
   - **Tests and probes:** Node tests; probes `step6-react-*`, `step6-list-reset-state`.
5. **The CI service wrapper** (`control/chrome/ci/service.py`):
   - It forwards `*peer` and still accepts the old single argument.
   - It exits unless it runs on Linux, under GitHub Actions and in Docker.
   - `control/chrome/ci/` is outside `build.py`'s inputs and outside the packaging README's copy list.
     `test_final_f7_only_the_real_policy_reaches_the_install_tree` pins exactly one polkit file in the hashed tree,
     no CI rule, and `polkit-check.py` unhashed.
   - Probes: `step6-ci-service-accept-peer`, `final-f7-install-tree-*`.
6. **`audible` and `muted`:**
   - They are booleans copied from Chrome's own tab (`tab.audible===true`, `tab.mutedInfo?.muted===true`). They need
     no new permission and are read-only.
   - The `tabs` purpose text, `chrome-tools.json` and `TOOLS.md` match, and `generate.py --check` passes.
   - Node test; probes `step8-tabs-*`.
7. **Step 8's harness fix and the audit pin:**
   - **Product unchanged:** between the red run's head `c1173b0b` and `f4a3fba9`, the only product change is the
     `collection()` line. Discard, report and close code are byte-identical, so the red row was the harness.
   - **The row still proves the claim:**
     - the owner loads and plays in the row's own tab;
     - the row asserts that tab's URL;
     - it logs `audible:true, muted:false` for that tab;
     - it requires `reload_required` with "media that is playing" and the tab still open and controlled;
     - only then does it close with the flag.
   - **From the review artifacts of `43593989287`:** the close-tab rows ran in tabs 1105440317 (external) and
     454827887 (policy), distinct from the navigate row's tabs, both `audible:true`. GROUP 8 passed in both installs.
   - **The audit pin** now matches the current withheld-form text and still asserts the refusal and zero arrivals.
8. **KNOWN-LIMITS changes since `a4143586`.** Each of these states what it is, the harm and why it's accepted:
   - line 5 (an observation appended; not a limit, and it hides no FIX: other rows click and fill in Claude-opened
     tabs);
   - line 8 (credential heuristic);
   - line 9 (target resolved in script);
   - line 21 (polkit sentence);
   - line 22 (nuisance dialog);
   - line 23 (first connector refuses the real host, availability only);
   - line 24 (dispatch-instant typing mark);
   - line 26 (audible tail).

   Line 27 hides FIX-1.

### 3. The records are true

- **Run `43593989287`:**
  - **Jobs:** one `gh run view`: head `f4a3fba9`, 28 jobs, 28 `success`. The longest job is (external, core) at
    1,712 s.
  - **Artifacts:** I downloaded the 2 aggregates, 4 latency, 4 Python and 2 review artifacts as zips. Their SHA-256
    equal GitHub's digests and the receipts. All members are flat, with no profile directory.
  - **Independent audit:** I re-ran `reviews/20-chrome/audit-review-evidence.mjs` on both aggregates. Both passed:
    98 named passes, group 12, 96 destination cases, 297 Python tests (53/56/46/142, all `OK`, the Linux-only
    spoofing-socket case ran) and 402 Node tests. The output equals the committed `…-independent-audit-ci.json`
    except for the folder name.
  - **Latency:** both gates `passed:true` with no failures. Every plain and instrumented median/p95 in REPORT's
    step-8 table, and the `ab7aba92` column, equals the artifacts. The worst values against the ceilings (read
    20.2/20.9 against 35/60 … approval 613.2/616.6 against 700/850) match the Handover.
- **Step 7 and step 6 latency tables:** they match the committed gate records of `43584711126` and `43566651314`.
  `latency-targets.json` matches the lead's ceilings.
- **Mail re-measure and sweep counts:** the step-7 table equals `mail-sweep-after-step7.json` (plain medians), and
  every call is at or below main, the fresh store included (read 0.513 → 0.508). The counts add up: 6,527×2+23,436
  = 36,490; 6,259×2+22,540 = 35,058; 6,259×2+92,817 = 105,335; 6,259×2+15,803 = 28,321.
- **Polkit runs:** one `gh run view` each. `43556395889` (`5f18ff60`) and `43561341511` (`529d5fe8`) succeeded in
  the `polkit` job. In the downloaded `result.json` of `43561341511`, all six cases come out as REPORT says,
  including the two dialog texts naming the change, the refusals and `NoNewPrivs: 1` with an empty bounding set.
- **Budget:** `gh run list` shows 262 `control-chrome.yml` runs on `pkg/20-chrome`, which matches.
- **Workflows:**
  - `control-chrome-polkit.yml` has `pull_request` on `main` with the five paths, plus `workflow_dispatch`.
  - `git diff b424f60a b698d68e -- .github/workflows/control-chrome-check.yml` is empty.
- **Other REPORT claims:**
  - The REPORT correction on "native browsing targets" and the destination-rows sentence are made.
  - `f4a3fba9..b698d68e` changes only records, REPORT.md and the deletion of PROGRESS.md.

### 4. The rules held

- `git diff 8b7e799c b698d68e -- control/packaging/aresos-toold.service` is empty.
- These are unchanged since `a4143586`: `docs/control/CONTROL.md`, `docs/design/`, `docs/control/PLAN.md`,
  `docs/control/FEATURES.md`, `README.md`, `os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md` and
  `HANDOFF.md`.
- Tab groups and the hold window:
  - The diff touches no group handling.
  - The guard's `until=…+config.holdMs` line only gains `typingTarget=null`.
  - The gate still asserts the 520-750 ms wait.
- `git diff -M --name-status` shows no rename or deletion under `control/aresos_control/chrome/` or its tests.
- No `chrome.storage`, IndexedDB, localStorage or sessionStorage in the extension, and no `key`, `update_url` or
  storage permission in `manifest.json`. The typing record is a document-lifetime isolated-world symbol.
- `build.py`, `manifest.json`, `native-host.json`, `policy.json` and `update.xml` are unchanged. `EXTENSION_ID`,
  `UPDATE_URL` and `CRX_URL` are in place.
- No absolute user path appears in the 208 added or changed files. The two `/home/owner` hits are pre-existing
  container fixture paths.
- `reviews/20-chrome/PROGRESS.md` is deleted (`b698d68e`).
- `generate.py --check`: see 5.

### 5. Local preflight

`.work/post18d/final-local.py` exists only in the builder's worktree, which I didn't touch. I ran the same commands
its committed record lists (`records/post18d/final-local-a4143586.json`). They ran on a `git archive` export of
`b698d68e` in a scratch directory, with CPython 3.14.6, SQLite 3.50.4, jsonschema 4.26.0 and Node 26.4.0, and wrote
nothing to the review copy:

- **Python shards:** 53 / 56 / 46 / 142 = **297 tests, all OK**. One skip: the Linux-only
  `test_final_f7_a_real_spoofing_process_on_the_socket_gets_nothing`, which ran `ok` in CI.
- **Node:** every `control/chrome_tests/*.test.mjs` plus `reviews/20-chrome/audit-streams.test.mjs`: **407 / 407
  pass**.
- **Mutation audit:** **415 rejected, 0 survived, every baseline passed**. By family:
  - `final-f1` 4, `final-f2` 8, `final-f3` 8, `final-f4` 2, `final-f6` 2, `final-f7` 21;
  - `final-discard` 11, `final-notes` 9;
  - `step5` 12, `step6` 6, `step7` 13, `step8` 4.
- **Generator:** `control/generate.py --check`: "Generated artifacts match definitions".
- **Unit pin:** `git diff 8b7e799c -- control/packaging/aresos-toold.service` is empty.

These match REPORT's "297 Python, 407 Node and 415 mutations".

**Mail, not counted:** `test_review25_outgoing_wire_enospc_then_unlink_eio_preserves_primary_and_note` and
`test_review25_password_enospc_then_unlink_eio_preserves_primary_and_note` fail identically on exports of main
`b2b51107` and of `b698d68e`. In both, `boundary_not_installed` replaces the expected `storage_limit`: this Mac has
no `/etc/claude-code/managed-settings.json`. That is environmental, as REPORT says. The Mail workflow runs them in
its container.

**Scratch evidence** (outside the repo): `final-review/recheck-pkg/`, with `api/` (run and job metadata), `zips/`
and `x/` (artifacts), `out/` (preflight logs) and `audit-*.txt`.
