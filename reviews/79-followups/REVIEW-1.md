# 79 follow-ups: review 1

Reviewer: a fresh Claude agent (Opus 5.5), 2026-11-16. I did not build this. PR #93, branch `fix/79-followups`, head
`9aab4fe1`, range `68dde093...HEAD`. Read-only: every mutation below was undone with `git checkout`, and `git diff`
was empty for code files at the end.

## What I checked

### 1. The rollback gate (O1, O2)

- **Every caller, before and after:**
  - `Qualification.record()`: `accept()` (unchanged), the engine's version notice (`engine.py:765`, unchanged, JC3),
    `maintenance()`, `mode()` only when `maintenance()` returns `None`, and the pending-row projection (O1).
    `control/chrome/ci/attestation.py` reads it only to assert.
  - `maintenance()`: `mode()`, and the daemon on connect (`daemon.py:267`) and every maintenance tick
    (`daemon.py:122`). Both daemon calls ignore the return value. Test doubles (`test_bridge`, `test_owner_confirm`)
    use `lambda: None`, which makes `mode()` read the record itself.
  - `refresh()`: one product caller, `maintenance()` (`adapter.py:239`).
  - `mode()`: every Chrome verb, `facts()`, and `pending_state(projection=False)`. All still go through the one
    reconciled read.
- **O1 is right.** `self.committed` is `store.chrome_state` (`adapter.py:99`), the same `Projection` that `record()`
  reads, so the row still reads only committed journal records after `sync()`. Both `qualification_rollback` and
  `qualification_invalid` are `Refused`, so the row shows them as `refused` with that code. A row can no longer show
  `current` where `mode()` refuses.
- **The record `maintenance()` returns is always the output of `record()`,** so it is reconciled and validated. A
  rolled-back or invalid record still raises before any switch is computed, as on main.
- **Stale reuse within one call:** nothing writes the record between `maintenance()`'s read and `switches()` except
  `refresh()` → `accept()`. One path through that write leaves the old read in use: finding 1. The service is
  single-threaded (no threads in `aresos_control`), so no other writer can interleave.

### 2. `refresh()`'s return value, path by path (`qualification.py:143-175`)

| Path | Returns | Record changed? | Right? |
|---|---|---|---|
| Gated for the day | `False` | no | yes |
| Fails before `accept()` (unlink, fetch, size, ledger, temporary file) | `False` | no | yes |
| `accept()` refuses in the verifier or `append_only` | `False` | no | yes |
| `store.write` fails before its commit | `False` | no | yes |
| `store.write` commits, then raises (`recorded_write`'s `flush_notices`) | `False` | **yes** | **no**, finding 1 |
| `accept()` returns, then the temporary unlink raises | `True` | yes | yes |
| The final fetch-result write raises | raises | either | yes: `mode()` raises too |

### 3. Do the tests fail on the old code?

- **Main's `adapter.py` and `qualification.py` under the new tests:** `test_qualification_service` plus
  `test_qualification_fixture`, 29 tests, 5 failures:
  - O1, both subtests: `('current', None) != ('refused', 'qualification_failed')`, and the same for
    `qualification_rollback`;
  - `test_o2_mode_reads_the_record_once_per_call`, both subtests: `2 != 1`;
  - `test_o2_refresh_says_whether_it_accepted_a_record`: `None is not True`.

  `test_o2_mode_trusts_the_record_its_own_refresh_accepted` passes on main, as it should: main always read again.
  It guards the new re-read.
- **My own mutations,** each restored with `git checkout` afterwards:

  | Mutation | Caught by |
  |---|---|
  | No re-read after an accepted refresh | `test_o2_mode_trusts…`: `True is not false` |
  | `mode()` always reads again | `test_o2_mode_reads…`: `2 != 1`, both subtests |
  | `accepted = True` before `accept()` | `test_o2_refresh_says…`: `True is not False` |
  | `accepted` never set | `test_o2_mode_trusts…` and `test_o2_refresh_says…` |
  | `record()` reconciles one way only | N1 (error) and `test_the_same_fixtures_pass…` |
  | `force = False` always | **not** N1, see finding 2; `test_failed_forced_refresh…` and `test_runtime_connection_refresh…` catch it |
  | `fixture_runtime` always rewrites | N2: inode and mtime both differ |
  | `test_restore_lock` without its `test_engine` import | N3: `['test_restore_lock'] != []` |

### 4. N1 to N4 against REVIEW-1's asks

- **N1** does what was asked. It starts from the `image` runtime, holds `shipped + [entry(build, '157.0.1.1')]`,
  and an action is prepared, approved and dispatched once. An uncovered major stays conservative over three calls
  with one fetch. The refresh is not proven to be *forced*, though: finding 2.
- **N2** is exact. `mkstemp` creates the new file while the old one still exists, so a rewrite always gets a
  different inode for that path, whatever the timestamp granularity.
- **N3** does what was asked, and also covers `Daemon(`. The detectors are checked on snippets, and the scan must
  find `test_storage`, so an empty scan can't pass. `import test_engine as fixture` (`test_restore_lock`) is matched.
- **N4:** checked with `python-shard.py`'s own sort. `test_qualification_fixture` is at position 13, so it runs in
  `python-shards (1)`, and the builder is right that REVIEW-1's premise was off. The lines now name the jobs.

### 5. The revert of e2e4eedc

Clean. `git diff 68dde093 HEAD` is empty for `control/chrome/ci/service.py`,
`control/chrome_tests/qualification_fixture.py` and `control/chrome_tests/test_latency.py`. In
`test_qualification_fixture.py`, the harness check is back to main's `install(tempfile.mkdtemp(...))` line, and
the file differs from main only by 8b71693c's N1-N3 hunks. Nothing in `control/` or `.github/` mentions
`harness_shipped`, `harness_record`, `LATENCY_HISTORY`, `FIXTURE_QUALIFICATION` or `RealisticRecord`. The
`LATENCY_BASELINE` uses that remain are main's.

### 6. Local runs (2026-11-16, at head, laptop idle)

`PYTHONPATH=control:control/chrome_tests python3 -m unittest <module>`, one process each, all OK:
`test_qualification_service` (21), `test_qualification_fixture` (8), `test_qualification` (31), `test_bridge` (14),
`test_owner_confirm` (15), `test_committed` (15), `test_state_fixes` (21), `test_engine` (32).
`test_owner_confirm` was one that the builder couldn't run.

## Findings

1. **FIX** `control/aresos_control/chrome/qualification.py:163-165`, `control/aresos_control/chrome/adapter.py:234-242`
   - **Problem:** `refresh()` returns `True` only when `accept()` returns, but `accept()` can raise after its write
     has committed. `store.write` is wrapped by `recorded_write` (`results.py:165-177`), which calls
     `store.flush_notices()` once the write has committed. A deferred notice that fails there (a `storage_limit`,
     say) makes `accept()` raise. `refresh()` swallows the error and returns `False`, so `maintenance()` hands
     `mode()` the record it read *before* the fetch. The fetched record is committed by then, and it may add a
     failure for this Chrome. `mode()` then lets one acting call through that the committed record refuses. Main
     read the record again after `maintenance()` and refused. This is the "stale record outlives a write in the
     same call" case, and it fails open.
   - **Reproduced:** Held: this build passes 157.0.1.0. Fetched: the same entry plus a stable 157.0.1.1 that
     failed `binding`. A real `Bridge` on 157.0.1.2. `store.flush_notices` raises `Refused('storage_limit')` once,
     right after the fetched record is committed:
     - **This head:** `mode(acting=True)` returns `binding: True`, while `record()` already equals the fetched
       record.
     - **Main's code:** the same call raises `qualification_failed`.
     - On both, the next call refuses.

     The probe is below; it subclasses `test_qualification_service.Service`.
   - **Reachability:** narrow. Deferred notices exist after a background storage refusal, and the fetch-result write
     that follows retries the same flush. A persistent failure therefore makes `refresh()` raise, which is safe. A
     transient one (free space coming back between the two writes) gets through. The window is one call, but the
     record exists to fail closed.
   - **Fix:** make `True` mean "the held record may have changed": set the flag immediately *before*
     `self.accept(...)`. I checked this variant: the probe refuses. `maintenance()` then reads again after any
     attempted accept, which happens at most once a day plus forced refreshes, so O2's saving is kept.
     `test_o2_refresh_says…`'s not-append-only case flips to `True`; rename it and the docstrings to match. Add the
     probe as a regression test.
   - **Also in this case, already on main:** the fetch result says "held record retained" although the record was
     replaced. It could say what happened.

   ```python
   def test_post_commit_raise_in_accept(self):  # in a Service subclass
       failed = entry(build=self.build, version='157.0.1.1', run='fetched'); failed['core']['binding'] = False
       fetched = {'format': 1, 'entries': [entry(build=self.build), failed]}
       self.connected('157.0.1.2'); store = self.engine.store; original = store.flush_notices; raised = []
       def flush():
           if not raised and store.chrome_state.get('chrome:qualification') == fetched:
               raised.append(1); raise q.Refused('storage_limit', 'notice flush failed after commit')
           return original()
       refresh = self.chrome.qualification.refresh
       with patch('aresos_control.chrome.uploads.prune'), \
               patch.object(self.chrome.qualification, 'refresh', side_effect=lambda **a: refresh(verifier=lambda p: None, **a)), \
               patch.object(store, 'flush_notices', side_effect=flush), \
               patch.object(q.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(fetched).encode())):
           with self.assertRaises(q.Refused) as refused:
               self.chrome.mode(acting=True)
       self.assertTrue(raised); self.assertEqual(refused.exception.code, 'qualification_failed')
   ```

2. **NIT** `control/chrome_tests/test_qualification_fixture.py:155-165` (N1)
   - **Problem:** the store is fresh, so the daily refresh is due anyway. "Forces one refresh" holds even with
     `force = False` hard-coded; I ran that mutation and N1 still passed. Other `Service` tests do catch it, so
     nothing is unguarded.
   - **Fix:** record a recent `chrome:qualification_fetch` time before the three calls, so only the force can
     fetch. Or reword the comment and PROGRESS to "one fetch".
3. **NIT** `reviews/79-followups/PROGRESS.md:38-40`
   - **Problem:** "They read the record in exactly the cases they did before" is not quite true. After an accepted
     refresh, the daemon's `maintenance()` now reads the record a second time. This is harmless: the new record
     extends the old, so the read can't raise `qualification_rollback`. But the sentence is wrong as written.
   - **Fix:** add "plus one read after an accepted refresh". After finding 1's fix, that becomes "after an attempted
     accept".

NOT SAFE
