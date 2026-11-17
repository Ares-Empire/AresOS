# Review 1: 20-restore-lock-followups (PR #95, `5d644ba1...f31ef5c2`)

Reviewer: a fresh Claude agent on Opus 5.5, 2026-11-16. I did not build this. I reviewed read-only; this file is the
only thing I wrote, and I left it uncommitted.

**Verdict in one line:** all three items do what the brief and the lead's decisions say. The model now matches the
store's lock in every case the sweep reaches, and no production code changed. The tests catch the regressions they
claim to catch, plus three more that I tried. The four findings below are all NITs.

## What I read

- `AGENTS.md`; the brief with S1-S5 and N1-N9; `BRIEF-REVIEW-1.md`; `PROGRESS.md` (build, JUDGMENT-CALLs, runs,
  classification, Fable's findings); `mutations.py` and `mutations.json`; the new section of
  `reviews/19b-owner-state/KNOWN-GAPS.md`.
- The code diff `5d644ba1 f31ef5c2` under `control/owner_state_oracle/` (`driver.py`, `records.py`, `perturb.py`,
  `compare.py`), `control/mail_tests/test_owner_state_sweep.py`, `control/tests/test_owner_state_oracle.py`,
  `control/tests/test_restore_batches.py`.
- The store code it models:
  - `storage.py`: the startup lock at 204-250, `_pending_event`/`_replay` at 448-477, `_append` at 553-569, `_finish`
    at 593-599, `write`'s lock refusal at 620-621, `ensure_writable` at 769-777, `confirm_restore` at 905-957;
  - `engine.py`: `request` and `_admitted_request` at 747-800, `dispatch` at 562-626;
  - `results.Observations.finish`; `archive.py:11-15`.
- The oracle around it: `model.permitted_status`, `request_state`, `hold_facts`, `projection`'s identity cache
  (`model.py:1226-1229`); `compare.notice_head` and `compare_views`; the driver's `observe`, `reply`,
  `capture_response` and `compare`; the sweep's `scripted` wrapper and `exercise`; `ci/mail/tests.py` (which CI job
  runs the new sweep tests).

## What I ran

All of it ran as an ordinary user, with no container, root or mount. I ran no rpm-ostree, bootc or ostree command
and no `os/tests` module. My scripts live in my scratch directory and are not committed.

- `cd control && PYTHONPATH=.:mail_tests:tests python3 -m unittest tests.test_owner_state_oracle`: **124 tests OK**.
- `PYTHONPATH=.:tests python3 -m unittest -v tests.test_restore_batches`: **4 OK**, including both new store-level
  tests.
- The sweep module's 11 unit tests (every test except the full sweep), from the repo root with
  `PYTHONPATH=control:control/mail_tests` and the managed-settings stand-in from `repro.py`/`mutations.py`: **11 OK**
  in 7.5 s. These include the four new ones: item 1, S1's harness test, item 2 and item 3.
- Mutation probes in a scratch copy of `control/` (plus the pin, which `test_every_pinned_gap_belongs_to_an_executed_suite`
  reads). The worktree was never edited. Every baseline passed first. `git status` and `git diff` are empty at the end.

| Probe | Change | Result |
|---|---|---|
| builder's `item1-rule-removed` | `interrupted_confirm` returns `False` | caught by the sweep test (`restore/persistent/75/0/exhausted/envelope…restore-lock` keys) |
| builder's `item2-lock-field-dropped` | stand-in page without the field | caught by the sweep test (`cancel/persistent/2/0/crash-locked/aresos log.restore-lock`) and the oracle test |
| builder's `item3-recompute-differs` | `!=` back in `coherent_change` | caught (`head='ahead'`) |
| builder's `item3-decoder-differs` | `!=` back in `decode` | caught by the sweep test (`cancel/single/69/0/live-restored/…restore-lock`) |
| mine: lock applied only on decode | `snapshot()` calls `apply_service_lock` only when it re-decodes | **caught** by the sweep test: the failed confirm's own envelope is captured with no new bytes, so this is exactly the "must hold when its reply is captured" requirement (N1). The oracle unit test alone does not catch it. |
| mine: lock accumulated | `record.locked = record.locked or service_lock(record)` | caught (`(True, False) != (False, False)`) |
| mine: N2's rejected rule | any faulted confirm since the start, not the most recent | caught |
| mine: restart forgets the script start | `restart_index = 0` | caught by the sweep test (`restore/persistent/75/0/crash-restart/…`) |
| mine: harness checks only the first entry | `for call in d.oracle.script[:1]` | caught by S1's standing test (`AssertionError not raised`) |
| mine: recompute without `service_lock` | `coherent_change` keeps only the startup term, or neither | **survives** all 124 oracle tests (finding 1) |

The builder's 14 recorded probes (`mutations.json`) all name tests that fail on an assertion. I re-ran the four in
the table above and got the same results.

## Check 1: each item against the brief, and the model against the store

**Item 1 (C5).**
- `driver.interrupted_confirm` (`driver.py:19-29`) returns true when the most recent `control_restore_confirm`
  with `restore_precondition is True` since the last restart has a fault trace. It reads the trace only, never the
  reply.
- `records.service_lock` (`records.py:62-70`) is the one formula. It covers the old startup rule plus
  `interrupted_confirm`. The driver uses it (`driver.py:100`), and so do `consistency_errors` (`records.py:106`) and
  the alteration recompute (`perturb.py:485`). `interrupted_confirm` is listed in `RECORD_EXCLUSIONS`.
- `Driver.restarted()` (`driver.py:102-111`) replaces only the two pokes at the crash restart (N3). The `restart_`
  rebind and the other `_snapshot_key` pokes stay as they were. None of those runs a faulted confirm.
- The lock already holds when the failed confirm's own reply is captured. In `scripted`, the post-call
  `snapshot()` runs before the trace is set. The trace is then set, and `observer(index, reply)` →
  `capture_response` → `snapshot()` sees it, finds the bytes unchanged, copies the record and sets it locked. My
  "only on decode" probe confirms that this path is the one that matters.

**Item 2.** `compare.pages` (`compare.py:121-125`) adds `restore_required: code == 'restore_required'` to a refused
read's stand-in page.
- In production every `restore_required` refusal is gated on `store.locked`: `engine.py:576`, `:824`, `:837`,
  `storage.py:620-621` and `archive.py:13-15`. So the stand-in cannot say locked for an unlocked store.
- The opposite case (locked, but refused with another code, for example when `Observations.finish` overrides the
  refusal with a storage error) shows as a gap. It is not hidden, and the capture has none.
- Answered pages pass through unchanged. `control_log`'s data never carries the field, so a regression that answers
  the log under the lock also shows. This change creates no blind spot.

**Item 3.** `records.behind` (`records.py:48-59`) is the one shared rule (S3). It is used at `records.py:105`
(`consistency_errors`), `records.py:228` (`decode`) and `perturb.py:485`, and tested through each of the three callers
with a mutation for each. Its docstring names the lock's other terms, which stay (N4).

**The model against the store.**

| Store (running, then after a restart) | Model |
|---|---|
| Startup: `seq < committed or restore_pending` (`storage.py:208`) | `decode`: `behind(head, committed)` or `restore_pending`. Now equal; it was "differs". |
| Startup: an uncommitted tail record without a matching staged event locks (`:209-212`, `:245-248`) | The startup rule over `unprepared_fences`, through `service_lock` |
| Head hash not matching its record → `evidence_mismatch`, the store refuses outright (`:206-207`) | The hash term says locked. Unchanged, and not reached in the sweep. |
| Head ahead with a matching staged event → replay at startup, unlocked (`:241-250`) | Unlocked (`behind` is false). The restart's replay appends the marker, so the bytes then show equal. |
| A staged confirm (`space.restoring`) → replay, then `locked = restore_pending` (`:235-240`) | After a restart the decoder sees the replayed bytes; `restart_index` drops the old confirm |
| Running: any exception in `confirm_restore` before `self.locked = False` (`:942`) keeps the lock, and `write_failed` holds until a restart | `interrupted_confirm` until `restarted()` |
| Running: an ordinary write that fails at its marker does not lock; it only latches writes | Unlocked (`behind` is false; the startup rule covers only fences ≤ the last start) |

In this table the model now matches the store in every case the sweep reaches. Fable's census (prototype, 21,730
cases) said so for the rules. The capture says so for the final code: 0 keys end in `.restore-lock`, down from 31,438.
The remaining differences are the hash term (unreachable) and the uncommitted-head `restore_pending` inside a running
confirm. Brief review 1 §2 already explains both, and item 1's rule covers the second.

## Check 2: no production code changed

`git diff 5d644ba1...f31ef5c2 -- control/aresos_control` is empty, and so is the two-dot diff. Excluding the oracle
and the tests, the only change under `control/` is `control/chrome/qualification.json`, which the merge of `main`
(`590f96bf`, second parent `af314a74`) brought in. `HANDOFF.md` and `docs/control/TOOLS-HANDOFF.md` came in with that
merge too. `accf2eb0` (the pin) and `f31ef5c2` (docs) touch nothing under `control/`. The proof therefore ran the
captured code.

S4 at the capture: `git diff 5d717142 af314a74` under `control/aresos_control`, `control/owner_state_oracle`,
`control/tests` and `control/mail_tests` is empty. Main has moved since then; see finding 4.

## Check 3: tests and mutations

- Every test the brief lists exists and checks what the brief says, with the mutations it names.
- S1 and S3 are covered. The extra S1 option (the locked precondition dropped from the rule) is covered too.
- N1-N3 are covered: the `scripted` entry is the most recent one at capture time; the rule is recomputed on every
  snapshot; every pair case of the last point is exercised.
- The new sweep tests run in CI's required Mail suite. `select_cases('suite')` excludes only `OPTIONAL_CASES`, the full
  sweep among them (`ci/mail/tests.py:59-66`, `:82-90`). The oracle and store tests run in Control base.
- The one hole I found is finding 1.

## Check 4: the JUDGMENT-CALLs, N2 and S1's standing test

`PROGRESS.md` lists seven JUDGMENT-CALL bullets. The four that concern code are the first four:

1. **Where the rule lives** (the driver reads the script, the record carries the result, `records.service_lock`
   is the shared formula): **agree**. The decoder module stays free of the oracle's script, and the three users
   share one formula.
2. **Which script entries count** (both the driver's `observe` entry and the sweep's `scripted` entry; the most
   recent wins): **agree**.
   - The `scripted` entry is appended after the `observe` entry and gets its trace first, so it decides during the
     capture. Both carry the same precondition.
   - Every other confirm site (`owner_state_cases.py:408` and `:435`, the crash branch's confirm at
     `test_owner_state_sweep.py:245`) runs with no fault active, so it has no trace.
3. **Copy, not change in place**: **agree, and it is needed**. `Oracle.projection` caches by identity
   (`model.py:1227`), so flipping `locked` in place on a record that was already handed out would return a stale
   projection and rewrite an envelope's captured lock. Routing the startup rule through the same recompute gives the
   same results: its inputs change only with a re-decode or with `startup_sequence`, and both now go through
   `apply_service_lock`.
4. **S1's harness check scans every scripted confirm in the run**: **agree**.
   - `test_harness_refuses_a_confirm_answered_ok_after_a_fault` is a real standing test of S1. It makes the store
     tolerate the fault and answer `ok` while keeping the lock, which is exactly S1's scenario.
   - Running it in single mode only is justified, because the persistent-mode reply is refused anyway.
   - My "first entry only" probe shows that the test depends on the scan.

The other three are fine:
- the mutation record lives in `mutations.py`, with the reason in its docstring;
- the store-level test makes its lock with a direct write and fails the first commit-marker sync (sound, and it
  does not depend on how many syncs a write does);
- the ledger job (known; not mine to judge).

**N2.** "The most recent scripted confirm on a locked store since the last restart met a fault, assigned on every
snapshot" is what `interrupted_confirm` and `apply_service_lock` do. The value is recomputed, never `|=`, and the
recompute does not depend on the record already having the flag; the "lock accumulated" probe is caught. When the
latch package lets a second confirm succeed, the rule will end on its own, as N2 intended.

## Findings

1. **NIT: `control/owner_state_oracle/perturb.py:485`. The recompute's `service_lock(changed)` term has no test
   and is never exercised.**
   - Replacing it with only the startup term, or dropping it entirely, passes all 124 oracle tests.
   - The alteration corpus (`control/mail_tests/test_owner_state_perturb.py:90-130`) records no restore scenario,
     so `interrupted_confirm` is false in every altered record.
   - Today this changes no key. Brief review 1's S3 asked for "tested once through each caller" for `behind`, and
     PROGRESS's PLAN-GAP covers dropping the term from `consistency_errors` only.
   - Fix (about 5 lines, in `test_interrupted_confirm_is_a_term_of_the_lock`, `test_owner_state_oracle.py:135`):
     `record = decode(*self.history(2, 2, 2))`, set `interrupted_confirm = locked = True`, take
     `coherent_change(Oracle(), record, 'fixture:2')`, and assert that `changed.locked` is true.

2. **NIT: `records.py:104-105`, `records.py:227-228`, `perturb.py:484-485`. Only `behind` is shared; the decoded-lock
   formula is still written out three times.**
   - The `restore_pending`, head-hash and "has fences" terms can still drift apart, which is how "differs" survived
     in three places.
   - The lead chose a shared `behind` for S3, and the tests cover each caller, so this is not for this PR.
   - When one of those places changes next, a `decoded_lock(rows, fences, committed, head)` in `records.py` would
     make the three one.

3. **NIT: `control/owner_state_oracle/driver.py:24-26`. The docstring says more than the harness checks.** It says
   every such fault aborts the confirm "before the lock is released, which the sweep's harness asserts". The harness
   (`test_owner_state_sweep.py:216-223`) asserts only that no such confirm is answered `ok`. A confirm that released
   the lock and then failed would show up through the lock-view comparisons (the oracle expects locked, the store
   reports unlocked), not through the harness. Suggested wording: "the sweep's harness asserts that no such confirm
   is answered ok; one that released its lock and then failed shows as a lock gap."

4. **NIT (for the lead): main has changed `control/aresos_control` since the capture and the proof.**
   - #91 (`91487807`, merged 2026-11-16 18:16 UTC, after the proof run 43919136534 started at 17:30 UTC) changed
     `hooks.py`, `usage.py`, `boundary_policy.py` and the managed-settings draft's Stop hook command.
   - None of these is on the sweep's path: `engine.py` imports neither `hooks` nor `usage`; `boundary.py` imports
     only `asking_rules` from `boundary_policy`, which #91 did not change; the fault points come from closes, not
     from the settings file's size. So I expect no sweep key to move.
   - Still, the pin has not been proven against main plus #91. The PR's required checks run on the merge ref; the
     optional oracle workflow does not.
   - Either record this reasoning in the merge note, or run `control-owner-oracle.yml` on main after the merge. #91
     is the Stop hook fix, so that run should also show whether the ledger job's channel test is green again.

## Not checked

- The pin's key-by-key classification: a second agent re-checks it. I checked only the pin's file: SHA-256
  `8b27b116…`, 892,234 bytes, 1,930 groups whose counts sum to 2,576,083, against 2,622,072 and 1,997 at `5d644ba1`.
  I also checked the arithmetic of `KNOWN-GAPS.md`'s new table (closed, changed, new and unchanged add up, and N7's
  6,949 matches its parts).
- The CI runs themselves (capture, proof, ledger job). I made no dispatch.
- The alteration suite locally (16 minutes a shard); CI's 12 shards passed in both runs.
- PR #95's own checks: Control base and part of Control Mail (containers and sweep shards) were still queued or in
  progress when I finished. Merge only once they are green.

SAFE
