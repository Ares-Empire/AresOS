# Board #185: re-pin the optional owner-state oracle (progress)

Branch `pkg/19b-oracle-repin`, cut from main at `bdc16064`. Nothing under `control/` is changed. **Stopped before the re-pin:** the capture is not a pure renumbering of the pin (step 4 of the brief). `KNOWN-GAPS.json` and `KNOWN-GAPS.md` are unchanged. The lead decides how to go on.

## Run IDs
- Main's runs on `bdc16064` had finished before the dispatch: boundary and Control Chrome passed. Chrome qualification 43696892949 failed; that is not this item's.
- Dispatch 1 (capture): **43702462699** on `b0711d20`. 61 jobs: ledger and all 12 alteration shards pass; all 48 sweep/onboarding shards fail strictly, as designed, after writing their complete lists. One contract shard also fails `test_matrix_contracts` on a changed contract group (explained below). 1 of at most 3 dispatches used.
- Baselines (downloaded, not dispatched): pin run 43137420989 (`65070a83`, green); 18d run 43153770175 (`9bcacd84`, failed).

## Done
1. **Key format.** A sweep key is `flow/mode/point/pair/phase/view`:
   - `point` is the 1-based index of the faulted storage hit in the flow's clean run;
   - `pair` is a later cleanup hit (0 = none);
   - every hit counts, including `.close` hits, which are never faulted themselves;
   - the 377 contract, `G22-*` and channel keys carry no position.

   A code change can renumber `point` and `pair`. Several other things also move with the case number:
   - the compact groups: their ownership bucket hashes `flow/point`;
   - the export caller directory `tmpXXXXXXXX`, which encodes point and cleanup (`owner_state_oracle/identity.py`);
   - scripted UUIDs, when the fixture draws one more ID;
   - first-seen alias numbers (`:#N`).
2. **Baseline check.** The 53 lists of pin run 43137420989 reproduce `KNOWN-GAPS.json` byte for byte (`6bbcb02f…`, 924,221 bytes, 1,966,234 keys, 2,010 groups).
3. **Pin → 18d is a pure renumbering.** The mapping (per flow: failing points by rank; per point: cleanup pairs by rank) is a bijection over all 1,966,234 keys. Every row, stage and delta is equal, and the packed groups are equal after mapping (2,010 → 2,004 groups only through re-bucketing). 1,327,190 keys move.
   - In 11 flows, all failing points move by −7; onboarding moves −7 … −70 in ten steps.
   - Cause: 18d's `Boundary.require()` (it runs in `Engine()`, `reserve` and `submit`) no longer reads `managed-mcp.json` (4 descriptor closes) or walks `managed-settings.d` (3 closes).
4. **Pin → capture 43702462699 is not a renumbering.**
   - The capture has 2,439,317 keys (+473,083) in 1,997 groups; its compact list would be 921,490 bytes, SHA-256 `0a532e5e67292c91d56e0a4aa6706f102f76c0fb1b409b751549bc18282f3a4f`. **Not pinned.**
   - Cleanup-pair keys: 913,573 → 1,358,076 (+444,503).
   - Cleanup-free sweep keys: 1,052,284 → 1,080,864 (+28,580).

   The second comparison aligns failing points per flow by their cleanup-free failure signature, with export directories, 32-hex IDs and alias numbers normalised. It finds:
   - **Identity renumbering only:** all 12 changed contract keys (a different scripted UUID and one alias `#9`→`#8`). The likely cause is the new Chrome adapter drawing `uuid4()` at every Engine start. After normalisation, no fixed key differs.
   - **Renumbered and unchanged:** 6,404 failing points (612,629 cleanup-free keys) match exactly. Of their 15,985 old pair cases, 15,195 keep their signature.
   - **New failing points:** 298 (32,029 keys) with no old counterpart: new fault sites that fail.
   - **Points whose failures changed:** 3,418 old / 3,545 new points (about 437k keys each). Where these align one to one:
     - **13,288 gaps closed.** Mostly `crash-locked` `control_pending.restore-lock`/`notice-count`/`notice-head`/`total`, plus persistent `exhausted` `response.*.status`.
     - **2,130 new gaps.** 1,958 are `crash-locked` `response.control_pending.status`.
     - **14,592 changed deltas.** Mostly `crash-locked` `control_pending.complete`/`page`, and `envelope.*.notice-head` in the filing flows.
   - **New cleanup-pair cases:** pair cases at matched points 15,985 → 22,043. New close hits after a failure become new cleanup sites (for example, the Chrome projection's `operations.jsonl` reader and the adapter's `build-id.json`/`qualification.json` reads).
5. **Main cause found in production code.**
   - `994b6e8f` (PR #27, "Keep Chrome warnings current and pageable through committed-state recovery") changed `Engine` (`control/aresos_control/engine.py`, the `self.store.locked` check): while a restore is required, `control_pending`, `control_notices` and `chrome_notices` are now answered instead of refused with `restore_required`.
     - Example new gap: `attachment_export/persistent/3/0/crash-locked/response.control_pending.status`. Expected `permitted: restore_required`, observed `allowed`.
     - Example closed gap: `archive/persistent/2/0/crash-locked/control_pending.restore-lock`. The pin had `locked: False` observed against `True` expected.
   - The closed `exhausted` `response.*.status` gaps fit `b72c81fa` ("Read retained operations in key order so a full disk never fails a read"). **Corrected in step 2 (class D): not `b72c81fa`; an oracle permission artefact.**
   - The other classes (new failing points, the `notice-head` changes in the filing flows) were not traced to single commits.

## Trace (step 2)

Classified, not pinned. No code changed, no workflow dispatched, no browser started. Every one of the 1,966,234 → 2,439,317 keys falls into exactly one class below.

### Method
- **Alignment.** Fact lists are compared after normalising export directories, 32-hex IDs and *all* alias numbers, then sorting each fact list. Points are aligned per flow by their cleanup-free signature, leaving out the restore-lock views and the five exhausted read statuses (classes C and D). This aligns every point: 9,822 matched, 425 inserted, none unaligned. The narrower step-1 alignment left 3,418 / 3,545 points in replace blocks.
- **Local runs.** Single cases were run locally with the sweep's own `exercise()` on exported trees at `65070a83` and `b0711d20`. The setup: CPython 3.14 with jsonschema; the managed-settings read is stubbed as in `reviews/20-chrome/records/post18d/mail-sweep/hostenv.py`; the pin tree's boundary returns its generated policy. No browser, mail server or container is started.
  - Reproduced: `expiry` 3 and `maintenance` 2 (persistent), `cancel` 3 (crash) and `cancel` 10 (persistent).
  - Cleanup-pair sites with call sites for all of `status`.
  - Clean-run hit sites for `archive`, `expiry`, `restore`, `cancel` and `send`.
- **Scripts and outputs:** `.work/185/step2/` (ignored), listed under "Local analysis".

### Classes

| Class | Keys (pin → capture) | Cause | Verdict |
|---|---|---|---|
| A. Index-page fault sites | +425 failing points: 43,624 cleanup-free keys and 1,316 pair cases (51,468 keys) | `c5810bb0` (partial index `operation_open`) | Intended. No owner-visible change. |
| B. Chrome journal close after each fault | Pair cases equal to their point's own single-fault result: 19,090 → 28,530 | `3bf1b0d2` / `f3cfd5b1` (projection read in every result), `4d80ea38` (close error absorbed) | Intended. No owner-visible change. |
| C1. Restore-lock reads answered | 18,962 closed | `f3cfd5b1`, `994b6e8f` | Intended (owner sees more and more correctly) |
| C2. `response.control_pending.status` under lock | 3,827 new | same | Oracle drift |
| C3. Stale Mail rows during the lock | 12,120 changed | same (Mail side effect) | Regression, low severity |
| C4. Notice continuation to a refused route | 172 new + 43 changed | `3389d862` with `f3cfd5b1` | Regression, minor |
| C5. Restore flow, last point | 2 new, 1 closed | same | Existing gap reshaped |
| C-pairs | 995 pair cases (43,861 keys) changed only in C views | same | Follows C1–C5 |
| D. Exhausted reads after a background storage failure | 83 closed (`expiry` 51, `maintenance` 32) | `3bf1b0d2` / `4d80ea38` read-only close under the injector | Oracle drift that hides a pin gap still present (not a fix) |
| E. Identity renumbering | 12 contract keys; 4,459 cleanup-free keys (`filing_move` 4,418, `repair` 41) | `baed6679` (`uuid4()` per Engine start) | No behaviour change |

Positions also move without any content change:
- −7 per `Boundary.require()` (18d);
- +1 per Chrome journal close in a clean run;
- +4 per index page.

**A. Index-page fault sites.**
- The new points come in 104 blocks of 4, plus 2 single points (one SQLite page: three rollback-journal writes and one database write).
- All 425 points have exactly the signature of an existing fault site in the same transaction, within 12 points.
- Local clean runs show the only new primaries:
  - `sqlite.main.write @ storage.py:_apply`: +4 per changed unresolved operation row (status +8, send +48, cancel +4, expiry +4, restore +4);
  - `sqlite.main.write @ archive.py:archive`: +4 in archive.
- Recorded as intended in `967ef7e8` (`reviews/20-chrome/records/final-step7/mail-sweep-after-step7.md`): "+268 each, one index page per changed unresolved operation row". These are the "298 new failing positions" of step 1.
- Example: `status/single/55/0/live-restored/*` duplicates `status/single/54/0/...`.

**B. Chrome journal close after each fault.**
- `status`, locally: pair cases 272 → 439.
  - +151: one `journal.close @ chrome/committed.py:journal_reader` after every primary fault (151 primaries). The `Projection` re-reads the grown journal while the result builds its warning list.
  - +16: SQLite close/unlink cleanups of the 8 new index-page primaries (class A).
- At all 9,822 matched points, every new pair case either equals the point's own single-fault result or differs only in class C views. The EIO at that close is caught by `journal_reader` and reported as a generic storage observation, and the primary fault's error is reported first.
- The pair cases that differ from their point's own single-fault result are 3,010 old and 3,010 new, matching one to one. 3 settlement cases differ only through class C4.
- Totals:
  - Pair cases at matched points: 22,105 → 31,545.
  - Pair keys at matched points: 913,573 → 1,306,608.
  - Pair keys whose result exactly equals the point's own single-fault result: 695,270.
- The harness fix `2e5eb35e` (production-like journal stamp) had already cut the re-reads from about 26 per request to one. Step 1's guess was right: PR #27 adds file closes after a failure.

**C. The restore lock** (`crash-locked`, plus the restore flow's live and exhausted phases).
- Since `f3cfd5b1`, and `994b6e8f` for `control_notices`, `Engine.dispatch` answers `control_pending`, `control_notices` and `chrome_notices` while `store.locked`.
- Why: `reviews/20-chrome/SECURITY-REVIEW-D.md`, blocking finding 2. The pending path returned `items=[]; restore_required=True` while the journal held committed Chrome work.

- **C1. More is now visible, and correctly.** `restore-lock` 6,613, `notice-count` 4,220, `total` 4,017, `notice-head` 3,947, `page` 123, `complete` 41, `status` 1.
  - Example: `archive/persistent/2/0/crash-locked/control_pending.restore-lock`. The pin had expected `locked True`, observed `False`; the capture has no gap.
- **C2. Oracle drift.** `Oracle.permitted_status` (`model.py`, `if record.locked: return {'restore_required'}`) still expects the refusal.
  - Example: `attachment_export/single/3→4/0/crash-locked/response.control_pending.status`. Expected `["restore_required"]`; observed `allowed`; the pin had no gap.
  - When the read tries a write, the reply is `ok:false`, `restore_required`, with the data attached, and no gap. For example `cancel` 3: `resolve_sent_checks` reaches `Store.write`'s lock refusal.
- **C3. Stale Mail rows** (`page`/`complete` 8,034; `notice-head`/`notice-count` 2,959; `envelope.control_pending.*` 1,045; `total` 82).
  - The page now lists Mail operations from the working SQLite as it was before the restore. The oracle expects the restored-evidence state (`unknown`, "Restored log: … newer or missing evidence").
  - Example: `cancel/single/3/0/crash-locked/control_pending.page`.
    - Pin: missing `{"state":"unknown","reason":RESTORED_EVIDENCE}`, nothing shown.
    - Capture: the same missing row, plus an extra `{"state":"reserved","reason":"Awaiting exact approval; nothing submitted."}`.
    - Reproduced locally: the reply carries `restore_required: true` and the reserved row. After `control_restore_confirm` the same operation reads `unknown`.
  - Mix of stale states: 2,937 `submitting` ("do not cancel or retry"), 606 `reserved` ("nothing submitted"), the rest `partial`/repair rows.
- **C4. Continuation to a refused route.** Under the lock, `control_pending` advertises `notices_more.action = mail_filing_notices`, which refuses with `restore_required`. The route open under the lock is `control_notices`.
  - Cause: `Engine.notices` keeps Mail's old route when every current notice is Mail (`3389d862`).
  - Keys: 43 × `advertised.page`/`advertised.total`/`advertised.complete`/`notice-continuation` (the step-1 "172 new gaps"), plus 43 changed `envelope.mail_filing_notices.pending-head`. Three of these are settlement pair cases.
  - Example: `settlement/persistent/79→83/0/crash-locked/control_pending.notice-continuation`, extra `action mail_filing_notices`. `advertised.total` gives count 0 against 3.
- **C5. Restore flow, last point.** At the restore flow's last point (pin 68, capture 75), the store and the oracle already disagreed about the lock.
  - The pin's status gap closed (1).
  - The same disagreement now shows as `control_pending.restore-lock`: expected `False`, observed `True` (2, live and exhausted).

**D. Exhausted reads after a background storage failure.**
- Example: `expiry/persistent/2/0/exhausted/response.control_log.status` and four other read statuses; `maintenance` 2–6, 21, 22, 62.
- Reproduced on both trees: every read returns `storage_limit` at the pin and now; the replies are identical.
- At the pin no hit failed during those reads, so `storage_limit` was a gap; it comes from the latched deferred `background-storage` notice flush.
- Now the first read's Chrome projection opens the journal. Its close counts as a hit, and the exhaustion injector fails every hit, read-only closes included (`journal.close @ chrome/committed.py:journal_reader`). `fault.failed` makes `active_exhaustion` true, so the oracle permits `storage_limit` and the gap disappears.
- Step 1 attributed this to `b72c81fa`; that is wrong. The owner sees the same refusal as at the pin.

**E. Identity renumbering.**
- `Chrome.__init__` draws `uuid4()` (`process_session`, `baed6679`) at every Engine start, so the scripted UUID stream shifts.
- Repeated occurrence IDs (`base[:47]-uuid`) then sort differently, and `Gaps.facts` gives aliases in sorted raw-ID order.
- Examples:
  - `filing_move/single/165→166/0/live-restored/aresos log.notice-head`: occurrences `#7`/`#8` swap roles `Trash`/`ordinary`; the multiset is equal.
  - `repair/persistent/2/0/crash-restart/lifecycle-proof`: `notice-creation-time` moves from `#35` to `#36`.
- These were step 1's "`notice-head` deltas in the filing flows" and its 116-point and 21-point replace blocks.

### Regressions (owner-visible)
1. **C3, stale Mail state during the restore lock.** High confidence it happens (data and local reply); low severity.
   - Scenario: after a crash, or after the owner restores an older state, `control_pending` shows a Mail send as "reserved: Awaiting exact approval; nothing submitted" (or "partial … repair without SMTP") although the committed journal is newer.
   - The response flags `restore_required: true`, and every other action is still refused until `control_restore_confirm`, which then shows `unknown`.
   - Before PR #27 the owner saw only the refusal (the M14 gap "rows missing").
   - It is the hazard security review D called blocking for Chrome. Chrome rows were moved to the committed journal; Mail rows were not.
2. **C4, continuation to a refused route during the lock.** High confidence; minor.
   - The owner or Claude sees "N more notices: read `mail_filing_notices`" and is refused.
   - Production fix: advertise `control_notices` while `store.locked`.
3. **Side note, no gap class; medium confidence it matters.** Under the lock, `control_pending` now runs Mail's live read-only checks against the pre-restore working state: `resolve_checks` (IMAP LIST/FETCH) and `resolve_sent_checks` (Sent SEARCH). Before, the lock refused "any app access". These checks are read-only, and their result writes are refused by the lock.

### What a later oracle update needs
- **A, B, E:** nothing in the oracle; a re-pin accepts them. Optional:
  - give occurrences aliases by creation order instead of raw-ID order, so a UUID shift stops renumbering;
  - skip read-only closes as cleanup sites, to save CI time.
- **C2:** `permitted_status` must allow `allowed` (and `restore_required` when the read attempts a write) for `control_pending`, `control_notices` and `chrome_notices` under the lock.
- **C3:** keep expecting the restored-evidence rows, so the stale rows stay a recorded M14 gap until production derives Mail rows from the committed journal or marks them as a pre-restore snapshot.
- **C4:** keep the gap until production routes to `control_notices`; the oracle's expectation is already right.
- **D:** a failed *read-only close* must not permit `storage_limit` for the call, either in `permitted_status` or by not failing read-only closes in the exhaustion injector. Otherwise the pin's 83 gaps stay hidden.
- **Before a re-pin:** a capture of the current code would bake in C2's 3,827 drift gaps and drop D's 83 still-real gaps. Change the oracle (C2, D) first, then capture again and re-pin.

## Left (the lead decides)
- Whether the PR #27 behaviour is intended. If it is, the oracle's model (`control/owner_state_oracle/`) expects `restore_required` from `control_pending` under a restore lock; changing it is oracle code, outside this re-pin.
- A re-pin of the current capture would accept new gaps, closed gaps and changed deltas. It needs the lead's decision, plus a new capture after any oracle change. Dispatches left in this item: 2.

## Local analysis (ignored `.work/185/`, this worktree only)
- `map.py`: the strict rank mapping and bijection check.
- `align.py`: signature alignment; `ALIGN_LOOSE=1` normalises IDs and aliases.
- `classify.py`: closed, new and changed keys at aligned points.
- `contracts.py`, `flowdiff.py`, `histogram.py`, `overview.py`: helpers.
- `regen.sh <run>`: regenerates the lists from `.work/185/capture/<run>/`.
- `step2/` (Trace, step 2):
  - `index2.py`: run from the repo root; it writes `step2/idx2.pkl`.
  - `account.py`: the per-class key accounting; run in `step2/`.
  - `align3.py`, `inserted.py`, `pairs2.py`, `fdiff.py`: helpers.
  - `probe.py`, `probe_pin.py`: one sweep case with replies and failing hits; `PIN=1` for the pin tree.
  - `pairsites.py`: cleanup-pair sites with call sites (`CLEAN_ONLY=1` for the clean run only).
  - `*-pin.json`, `*-new.json`: their outputs for `status` and five flows.
- Full lists:
  - `old-43137420989-full.json`
  - `d18-43153770175-full.json`
  - `43702462699-full.json`
