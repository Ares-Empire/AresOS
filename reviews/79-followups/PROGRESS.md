# 79 follow-ups: REVIEW-1's nits N1-N4 and observations O1, O2

Builder: Claude agent (Opus 5.5), 2026-11-16, for the lead `linux-tools`. Branch `fix/79-followups` from `main` at
`68dde093` (#87's fixtures and #83's eight-entry shipped copy). Source: `reviews/79-qualification-tests/REVIEW-1.md`.

## What changed, per item

### O1: pending rows use the reconciled record (`control/aresos_control/chrome/adapter.py`)

- **Before:** `pending_state(projection=True)` computed the switches from
  `committed.get('chrome:qualification', shipped)`, the held record (or the shipped copy) as stored, skipping
  `Qualification.record()`'s reconcile. With the shipped copy ahead of the held record, a row showed `current` while
  `mode()` refused.
- **Now:** it uses `self.qualification.record()`, the value `mode()` trusts. `record()` reads the same committed
  projection (`store.chrome_state` is `self.committed`), so the projection still works when SQLite reads fail. A
  refusal from `record()` (`qualification_rollback`, `qualification_invalid`) is a `Refused`, so the row shows it as
  `refused` with that code.
- **Test:** `test_qualification_service.Service.test_o1_a_pending_row_refuses_where_acting_refuses_when_the_shipped_copy_is_ahead`.
  The service restarts from an image whose shipped copy holds a later patch of this Chrome that failed binding. An
  action is prepared while a fetched patch passes again, then the held record falls behind the shipped copy (subtest
  1) or diverges from it (subtest 2). The row, `mode(acting=True)` and `chrome_submit` must all refuse with the same
  code, and nothing is dispatched.
- **Mutation:** the old projection line back → both subtests fail with `('current', None) != ('refused', 'qualification_failed')`
  and `!= ('refused', 'qualification_rollback')`.

### O2: `mode()` reads the record once per call (`adapter.py`, `qualification.py`)

- **Before:** `mode()` called `maintenance()`, which (with a real Bridge and refresh on, i.e. in the service) read
  `record()` to decide whether an uncovered version forces a refresh, and then read `record()` again for the switches.
- **Now:**
  - `maintenance()` returns the record it read, or `None` when it read none (no Bridge, refresh off, no version).
  - `mode()` reads `record()` only when it got `None`.
  - When the refresh accepted a verified update, `maintenance()` reads the record again, so that call already uses the
    new record.
  - `Qualification.refresh()` now returns whether it accepted a record. It returned nothing before, and no caller used
    the value. `accepted` is set right after `accept()` returns, so a failing unlink of the temporary file can't hide
    an accepted write.
- **Unchanged for the daemon:** its `maintenance()` calls (on connect and every maintenance tick) ignore the return
  value. They read the record in exactly the cases they did before. So a serve loop with no Chrome connected still
  never reads it, and can't start raising `qualification_rollback` into `background_error`.
- **Tests (`test_qualification_service.Service`):**
  - `test_o2_mode_reads_the_record_once_per_call`: one `record()` per `mode()` call, with the fixture peer, and with a
    real Bridge both when the daily refresh is due and when it is gated.
  - `test_o2_mode_trusts_the_record_its_own_refresh_accepted`: an uncovered Chrome forces a refresh inside `mode()`;
    the fetched, verified record covers it, and that same call is not conservative and shows the record's failed
    adapter.
  - `test_o2_refresh_says_whether_it_accepted_a_record`: True after an accepted fetch; False when gated, when the
    fetch fails, and when the fetch is not append-only.
- **Mutations:**
  - `mode()` reads again after `maintenance()` → the once-per-call test fails.
  - No re-read after an accepted refresh → the trusts-its-refresh test fails.
  - `accepted` never set → the trusts and says-whether tests fail.
  - `refresh()` always returns True → the says-whether test fails.

### O2: one latency leg measures a realistic record

Files: `control/chrome/ci/service.py`, `control/chrome_tests/qualification_fixture.py`.

- **Before:** both latency legs and both runtimes ran with an empty shipped copy and a one-entry held record.
- **Now:** the plain profile's current runtime (`LATENCY_PROBE=true`, `LATENCY_PRIVACY=plain`,
  `LATENCY_BASELINE=current`) starts from:
  - a shipped copy of 300 entries of earlier builds (`qualification_fixture.history`: a stable and a beta entry per
    build, other builds only, so this build's switches are the one synthetic entry's);
  - a held record of those 300 plus the synthetic entry.

  Everything else keeps the empty baseline and the one entry, byte for byte as before: the old runtime, the audit
  leg, the fixture shards and the qualification pairs.
- **Shared definition:** `harness_shipped(environ)` and `harness_record(shipped, build, version)` in
  `qualification_fixture`, so the decision is unit-tested.
- **Diagnostics:** `service.py` prints
  `FIXTURE_QUALIFICATION {"shipped_entries": …, "held_entries": …}` into `service.txt`, which is in the artifact, so
  each run shows what it measured.
- **Guard:** the synthetic qualification modes (`conservative`, a failed group) rewrite the one entry, so they now
  refuse a non-empty baseline instead of silently giving the wrong mode. Only the fixture shards use them, and they
  have the empty baseline.
- **Untouched:** ceilings, sample counts, `latency-pair.sh`, `latency-reference.json`, `latency-summary.py` (the
  reference pins its hash) and `latency-check.py`.
- **Tests (`test_latency.RealisticRecord`):**
  - Only the plain leg's current runtime gets the 300 entries, and every other leg the exact old record.
  - A Chrome started from the realistic runtime trusts the held record and has the same switches as with one entry; an
    action is prepared, approved and dispatched once.
  - `service.py` starts from the shared records, prints the sizes, and the modes refuse a long baseline.
  - `latency-pair.sh` passes `LATENCY_BASELINE` into the container.
- **`test_qualification_fixture`'s harness check** follows the new `install(..., baseline=shipped)` call.
- **Mutations:**
  - History for every leg → fails.
  - `LATENCY_HISTORY = 0` → fails.
  - A failing history entry for this build on the browser's major → the qualifies-like-one-entry test fails with
    `qualification_failed`. A first variant on another major survived, rightly: other majors don't change the switches.
  - `service.py` installing without the baseline → both harness checks fail.

### N1: an Engine-level case with a held record that extends shipped history (`test_qualification_fixture.py`)

- **Test:** `test_a_held_record_extending_shipped_history_acts_and_an_uncovered_major_stays_conservative`. It starts
  from the `image` runtime (shipped history with this build's 157.0.1.0 pair failed in every group) and holds
  `shipped + [entry(build, '157.0.1.1')]`. Chrome 157.0.1.1 is then qualified: an action is prepared, approved and
  dispatched once. With a real Bridge on Chrome 160 (no major covered), three `mode()` calls are conservative and
  force exactly one fetch, and the held record stays.
- **Mutations:**
  - `record()` reconciling one way only (always `append_only(held, shipped)`) → fails with the rollback refusal.
  - The refresh forced on every call → the fetch count is 3, and the test fails.

### N2: the "not rewritten" check compares inodes too

- **Change:** `test_a_fixture_runtime_is_shared_by_build_and_rewritten_only_when_it_differs` compares
  `(st_ino, st_mtime_ns)`. `os.replace` of a new temporary file always gives a new inode, so the check holds even on
  coarse timestamps.
- **Mutation:** `fixture_runtime` always rewriting → fails.

### N3: import guard

- **Test:** `test_every_chrome_test_module_that_starts_a_chrome_imports_test_engine`. It parses every
  `chrome_tests/test_*.py` with `ast`. A module that calls `Engine(`, `Chrome(` or `Daemon(` (by name or as an
  attribute) must import `test_engine` itself. The detectors are checked on small snippets first, and the scan must
  find `test_storage`, so a broken detector can't pass vacuously.
- **Mutation:** the `test_engine` import removed from `test_restore_lock.py` → fails.

### N4: shard numbers in `reviews/79-qualification-tests/PROGRESS.md`

- **Change:** the shard lines now use the job names: `python-shards (0)` 86 tests, `(1)` 82, `(2)` 79, `(3)` 106.
  `python-shards (1)` holds the new tests and both long modules.
- **The review's premise was off.** `test_qualification_fixture` is in `python-shards (1)`, not `(0)`:
  - the sorted partition puts it at position 13, and 13 % 4 = 1;
  - job 133214910741's log, `python-shards (1)` of run 43842657082, ran its six tests.

  So both old lines were true. What read as a contradiction was the count list "86, 79, 106 and 82", which was in
  job order (0, 2, 3, 1), not shard order.

## Local results

All on 2026-11-16, in the worktree. The shipped copy is main's: eight entries, none for this branch's build, since the
product change gives it a new build hash. No Node here, so no `.mjs` tests and no browser.

- `PYTHONPATH=control python3 control/generate.py --check`: "Generated artifacts match definitions".
- **The lead's list, in one process:**
  `PYTHONPATH=control:control/chrome_tests python3 -m unittest test_qualification test_qualification_fixture test_build test_fault_surface test_engine test_latency test_publisher test_restore_lock`.
  - Result: `Ran 163 tests in 4045.049s`, `OK`. It took 67 minutes because other sessions loaded the laptop.
  - The fault sweep's write surface is unchanged from #87's builder run: full `{'single': 2130, 'persistent': 2130, 'pairs': 8488}`,
    `qualification` 54/54/98, `delivery` 109/109/259, `restore` 76/76/290. So `refresh()`'s return value added no write.
- **Extra modules the adapter change touches, each in its own process, all OK:**

  | Module | Tests |
  |---|---|
  | `test_qualification_service` | 21 |
  | `test_committed` | 15 |
  | `test_state_fixes` | 21 |
  | `test_questions` | 34 |
  | `test_sites` | 17 |
  | `test_full_disk_reads` | 10 |
  | `test_state_crashes` | 1 |
  | `test_open_index_timing` | 1 |
  | `test_state_exhaustion` | 1 |
  | `test_policy` | 18 |
- **Not run here; left to CI:**
  - `test_storage` (17 minutes).
  - `test_state_mutations`.
  - `test_owner_confirm`: the session's permission check refused it by its `test_owner_` name.
- **Mutations:** each change undone in turn, its guarding tests run, the file restored from git, 13 in all. Each
  failed for the intended reason, as listed per item above.

### What a realistic record costs (local, for the latency leg)

Measured with the fixture engine while other work loaded the laptop (load 10 to 12 on 16 threads), median of 30 to 50.

**One `record()` call.** It validates the held record twice and the shipped copy once, and the committed projection
deep-copies and hashes the stored value:

| Entries | ms per call |
|---|---|
| 100 | 1.5 |
| 300 | 4.6 |
| 500 | 7.7 |
| 1,000 | 15.4 |

REVIEW-1's "about 6 ms at 1,000" was likely the validation alone.

**`record()` calls per request kind,** with refresh off as in the harness:

| Request | Calls |
|---|---|
| `read`, `navigate` | 2 (`mode()` plus the engine's version notice) |
| `click`, `fill`, `submit` | 3 |

In the service, `mode()` added one more before this change.

**Added time per request against one entry:**

| Entries | `read` | `navigate` |
|---|---|---|
| 300 | +12 ms | +18 ms |
| 500 | +19 ms | +26 ms |

**What that means for the ceilings.** #87's plain run (43842657082) measured `read` at history-4000 with a median of
20.3 ms, against a ceiling of 35 ms. So:
- 300 entries should land near 30 to 32 ms on the runner, under the ceiling but with little room;
- about 400 to 500 entries would reach it.

The CI result of this PR replaces this estimate (see the PR's runs).

## JUDGMENT-CALLs (technical, for the lead)

1. **O1's test builds the disagreement inside one process.**
   - **How:** it prepares under a passing record, then makes the held record fall behind (or diverge from) the
     shipped copy.
   - **Why:** in the service the shipped copy only changes with an image update, which restarts the service, and a
     restart already makes earlier rows `stale_approval`. A held record written by `accept()` always extends
     `record()`. So the disagreement isn't reachable today. The fix makes it impossible by construction, as asked.
2. **`maintenance()` returns the record or None,** instead of always reading one.
   - **Why:** the daemon calls it every maintenance tick and on connect, often with no Chrome connected. Reading
     there would add a read, and could turn a bad held record into a background error every tick.
   - **The re-read:** it happens only when `refresh()` reports an accepted record, which is why `refresh()` now
     returns a bool.
3. **The engine's version notice still reads the record separately.** It runs on every `chrome_` request
   (`engine.request`), so a `read` still reads it twice. That is outside "once per `mode()` call"; sharing one read
   across a request would need a per-request cache and care with writes in between.
4. **Which leg, and which runtime, measures the 300-entry record.**
   - **Leg:** the plain one, because it is closer to the installed service (the audit stream is a test harness
     feature).
   - **Runtime:** only the current one. With the long record, the old runtime `ab7aba92` would count the record's
     cost as runner noise and loosen every ceiling by the same factor.
   - **Unchanged:** the audit leg stays like for like with the frozen reference.
5. **300 entries, not more.** That is the low end of "several hundred": the data branch's rate so far (8 entries in
   three days) gives it in a few months. The local estimate puts 500 entries at or over the 35 ms `read` ceiling. If
   CI shows 300 already misses it, I stop and report, per the brief.
6. **The fixtures' history uses other builds only.** It adds the record's cost without changing this build's
   switches, so the leg's behaviour (which calls ask, which go free) stays the same and only the timings move.
7. **N3's guard also covers `Daemon(`.** It builds an Engine and so a Chrome. No Chrome test calls it today.
8. **N4: the review's premise was off,** see N4 above. I still changed the text to name jobs, since the count list
   was ambiguous.

## Not done here

- **The cost itself.** It grows linearly per call: about three validations plus a deep copy and a hash of the whole
  record, in each of two or three reads per request. A design fix would be one of:
  - validate once when the record is written or the service starts, and cache it keyed by its journal offset;
  - or drop the duplicate validations inside `record()` and `switches()`.

  This touches the rollback check, so it should be its own brief. Going by the estimate above, it will be needed
  before the record reaches about 400 to 500 entries.
