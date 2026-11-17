# 79 follow-ups: recheck 1

Rechecker: a fresh Claude agent (Opus 5.5), 2026-11-16. I built none of this. PR #93, branch `fix/79-followups`,
head `20b69088`, fix range `38f9520c..20b69088`, against REVIEW-1 (NOT SAFE: finding 1 FIX, findings 2 and 3 NITs).
Read-only: every mutation below was undone with `git checkout`, and `git diff` and `git status --short` were empty at
the end. My probes lived in the session scratchpad, outside the repo.

## What I checked

### 1. Finding 1 is closed (`qualification.py:150-193`, `adapter.py:239-243`)

- **The only product writer of `chrome:qualification` is `hold()`** (`qualification.py:147`). `storage._restore_chrome`
  skips the key. So the flag only has to cover `hold()`.
- **Nothing before `written = True` writes.** Between the daily gate and the flag, `refresh()` reads the fetch time,
  unlinks obsolete temporaries, fetches, admits on the ledger (a check, no journal write), writes the temporary file
  and calls `verified()`. `verified()` runs the verifier, reads `record()` and checks `append_only`. None of these
  touches the held record, so the flag is never False with the held record changed.
- **Every raise from `hold()` comes after `written = True`** (`qualification.py:179-180`), wherever it happens:
  - after the commit inside `store.write`: `checkpoint('journal_committed')` in `_finish`, `ledger.finish`
    (`storage.py:732-734`);
  - after the commit in `recorded_write`: `flush_notices()` (`results.py:176`);
  - before the commit: the ledger's admission, the journal append.

  `refresh()` then writes the fetch result and returns True, or raises if that write fails too (a `write_failed`
  store always does), so `mode()` raises. A `BaseException` propagates the same way. On True, `maintenance()` reads
  the record again (`adapter.py:239-242`).
- **Probes at head** (a `test_qualification_service.Service` subclass, Chrome 157.0.1.2 on a real `Bridge`, a fetched
  record whose 157.0.1.1 failed `binding`):

  | Probe | Head | `38f9520c`'s `qualification.py` |
  |---|---|---|
  | REVIEW-1's probe: `flush_notices` raises `storage_limit` once after the commit | refuses, `qualification_failed` | `Refused not raised` |
  | `ledger.finish` raises `OSError` after the commit | refuses, `qualification_failed`; result says `(OSError)`, no message | `Refused not raised` |
  | `checkpoint('journal_committed')` raises | `mode()` raises (`Refused storage_error` from the fetch-result write) | not run |
  | Ledger admission refuses the held-record write before its commit | True, record unchanged, `mode()` acts on it (`binding: True`), "may have been updated" | not applicable (no `verified()`) |
  | The temporary unlink fails after a clean `hold()` | refuses, `qualification_failed`; "may have been updated" | text says "held record retained" |

- **True with the record unchanged** (a write refused before its commit) is acceptable. It is not even fail closed:
  `maintenance()` reads the committed record again and `mode()` acts on the record that is really held. The cost is
  one extra validated read on a path that runs at most once per refresh attempt, and a fetch result that says "may
  have been updated", which is all `refresh()` can know.
- **The builder's deviation** (flag after `verified()`, not before `accept()`) is right. `verified()` writes nothing,
  so the later flag covers every write. An earlier flag would make verifier refusals (403, 429, 5xx, a bad signature)
  say "may have been updated", which `test_qualification.py:485` refuses.

### 2. The `accept()` → `verified()` + `hold()` split

- `accept()` is `hold(verified(path, verifier))` (`qualification.py:137-138`). Its signature, its order (verifier,
  then `append_only` against `record()`, then the same `store.write` call) and its return value are unchanged.
- **Callers:** CI `control/chrome/ci/attestation.py:62` and `:162`, the `accept()` tests in `test_qualification.py`
  (`:406-431`), and the fault sweep's `qualification` flow (`test_fault_surface.py:45`, `accept(path, verifier=...)`)
  all still go through `verified()`. `test_qualification.py`'s `Held.accept` classes are duck-typed doubles for
  `attestation.py`'s helpers, still consistent with its `.accept` calls.
- **`hold()` has two callers,** `accept()` and `refresh()`, and both call `verified()` right before it. No path writes
  the held record without the verifier and the append-only check. No BLOCKER.

### 3. The fetch-result text

- `reason` is still `exc.code` for a `Refused`, else `type(exc).__name__` (`qualification.py:187`). Both new and old
  texts carry only that. No exception message, remote content or transport output.
- Guarded: the new test asserts `'Notice flush'` absent, the says-whether test asserts `'Fixture'` absent. My
  mutation M3 below put `{exc}` into the new text, and both tests failed.

### 4. Nits 2 and 3

- **Nit 2** is done as REVIEW-1's first option: N1 records a fetch an hour ago before the three `mode()` calls
  (`test_qualification_fixture.py:158-161`). I reran `force = False` in `maintenance()`: N1 fails with `0 != 1`.
- **Nit 3** is done: `PROGRESS.md:38-40` now says the daemon reads the record once more after a refresh that wrote a
  verified record, also when that write raised, and why that is harmless. That is REVIEW-1's "after an attempted
  accept", adjusted to the flag's position.

### 5. Local runs (2026-11-16, at head, load about 1.8)

- `PYTHONPATH=control:control/chrome_tests python3 -m unittest test_qualification_service test_qualification_fixture test_qualification test_engine`:
  `Ran 93 tests in 20.576s`, `OK` (22 + 8 + 31 + 32).
- **Mutations,** each restored with `git checkout`:

  | Mutation | Caught by |
  |---|---|
  | M1: `written = True` after `self.hold(candidate)` | the new test (`Refused not raised`) and says-whether (`False is not True`) |
  | M2: `refresh()` holds the fetched JSON without `verified()` | says-whether (`True is not False`) and 8 `test_qualification.Delivery` failures (bad signature, rollback, 403/429/5xx, timeouts) |
  | M3: the new text carries `{exc}` | the new test (`'Notice flush'` found) and says-whether (`'Fixture'` found) |
  | `force = False` in `maintenance()` | N1: `0 != 1` |

- CI on `20b69088` is green per the lead; I didn't re-run it. The fault sweep (`test_fault_surface`) is covered there.
  `hold()` issues the same `store.write` call `accept()` did, so its write surface can't change.

## Findings

1. **NIT** `control/aresos_control/chrome/qualification.py:145-148`
   - **Problem:** `hold()` is a public method that writes whatever it is given. "Only `verified()`'s output may be
     held" is a docstring, not a check. Today both callers verify first, so nothing is wrong.
   - **Fix (optional):** name it `_hold` so a later caller doesn't reach for it, or leave it. Not needed for SAFE.

SAFE
