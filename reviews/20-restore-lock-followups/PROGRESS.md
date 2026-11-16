# Brief 20-restore-lock-followups: what was read and run

**For the lead:** this is the text asked for as `FINDINGS.md`. The agent's file tool refuses that file name, so it
is here, as `CLAUDE.md` describes for `REPORT.md`. Rename it if you want; the brief says "the findings in
`reviews/20-restore-lock-followups/`" and holds either way.

Claude Fable, 2026-11-16, on `main` at `5d717142`. No production or oracle code was changed. The brief is
`briefs/20-restore-lock-followups.md`.

## Outcome

1. **C5.** The store is right to keep its lock after a confirm that failed at its last disk sync. The oracle's
   model is wrong at that one point: it reads a commit marker whose sync failed as a finished confirm.
2. **The log view.** The store is right. `aresos log` is refused under the lock and says so twice. The oracle looks
   for a lock field in a data page that a refused reply does not have.
3. **"C2's mirror of C5"** (found while tracing item 1). The store is right. The oracle's decoder calls a head
   *ahead* of the last commit marker a restore lock. The store, and its README, lock only a head *behind* it.

All 31,438 keys in the pin that end in `.restore-lock` belong to these three: 16,383 + 25 + 15,030.

## What I read

- **Store:** `control/aresos_control/storage.py`: startup lock (lines 204-250), `_append` (553-569), `_finish`
  (593-599), `write` (602-739), `ensure_writable` (769-777), `confirm_restore` (905-957).
- **Engine:** `engine.py`: `LOCKED_PENDING`, `LOCKED_NOTICES` (30-32), `notice_page` and `pending` under the lock
  (82-222), `dispatch` (562-626: the lock's allow-list at 575-576, `control_log` at 600-625), `request` and the
  refusal envelopes (747-895). `cli.py`: `aresos log` is `control log` and prints the whole reply.
- **Oracle:** `control/owner_state_oracle/`: `records.py` (decoder; the lock at 202-203, `consistency_errors` at
  71-82), `driver.py` (`snapshot`, `observe`, `capture_response`, `compare`), `compare.py` (`pages` at 116-131,
  `notice_head` at 235-247, `compare_views` at 250-349), `model.py` (`expected` at 433-527, `permitted_status` at
  1467-1491, `hold_facts`), `perturb.py` (the lock recompute at 479-485, `RECORD_EXCLUSIONS`), `gaps.py`,
  `FORMAT.md`.
- **Sweep:** `control/mail_tests/test_owner_state_sweep.py` (`exercise`, 205-256), `storage_faults.py`
  (`OSWrites`), `test_review23_sweep.py` (how the restore flow is built, 93-107).
- **Notes:** `briefs/20-restore-lock.md`, `reviews/20-restore-lock/REVIEW-REPIN-3.md` and `REPORT.md`,
  `reviews/19b-owner-state/KNOWN-GAPS.md` (last section) and `REPIN-185-PROGRESS.md`,
  `docs/control/TOOLS-HANDOFF.md`, `control/README.md` (169-225).

## What I ran

Everything ran locally as an ordinary user. No container, no root, no workflow dispatched, nothing under
`os/tests`, no rpm-ostree, bootc or ostree. One read-only download from GitHub (section 4). Scripts other than
`repro.py` lived in a scratch directory and are described here, not committed.

**The one stand-in.** The engine refuses asking actions unless a root-owned `/etc/claude-code/managed-settings.json`
exists. The laptop has none, and CI installs it in its container. Every script therefore starts with:

```python
settings = json.loads(Path('control/settings/managed-settings.draft.json').read_text())
patch('aresos_control.boundary.Boundary.read', lambda self, path: settings).start()
```

This removes four read-only file closes from the start of every flow whose call checks the boundary. Their local
fault-point numbers are 4 lower than CI's (`send` has 875 points here; the capture's cases sit 4 higher). `restore`
and `cancel` do not check it: their numbers and keys equal CI's exactly (section 2). Export flows also shift with
the checkout's path length, because their audit rows hold the caller's path.

### 1. `repro.py`: all three, without the sweep

`PYTHONDONTWRITEBYTECODE=1 python3 reviews/20-restore-lock-followups/repro.py` (about 2 s). It builds a real
restore lock (an older SQLite copy under a newer journal), then fails the journal's second sync of one write, which
is the commit marker's. Output, shortened (`d.rr` is `data.restore_required`, `p.rr` the envelope's):

```
== Item 1: the confirm fails at its last disk sync; the marker is rolled back (the sweep's single mode)
 confirm                 ok=False error=storage_limit d.rr=no data p.rr=True
 journal ends with       a record, no marker
 oracle decodes          locked=True (head 4, last commit marker 3, prepared [4])
 running store           locked=True write_failed=True
 control_pending         ok=True d.rr=True p.rr=True
 aresos log              ok=False error=restore_required d.rr=no data p.rr=True
 confirm again, disk ok  ok=False error=storage_limit d.rr=no data p.rr=True
   its message           Disk full or storage quota exhausted; free storage and check the recorded request or
                         operation before retrying.
 after a restart         locked=False; ok=True d.rr=False p.rr=False
== Item 1: … the rollback of the marker fails too (the sweep's persistent mode)
 journal ends with       a commit marker
 oracle decodes          locked=False (head 4, last commit marker 4, prepared [])
 running store           locked=True write_failed=True
 (every other line as above)
== Item 2: the log view under a restore lock
 aresos log              ok=False error=restore_required d.rr=no data p.rr=True
   its message           Older log refused; owner must confirm restore before any app access.
 page the oracle reads   {'items': [], 'total': 0, 'cursor': None, 'unavailable': 'restore_required'}
 oracle: expected locked= True  observed locked= False
 aresos log, confirmed   ok=True d.rr=no such key p.rr=False data keys ['cursor', 'items', 'notices', 'total']
== Item 3: an ordinary write fails at its last disk sync (no restore anywhere)
 prepare                 ok=False error=storage_limit d.rr=no data p.rr=False
 oracle decodes          locked=True (head 3, last commit marker 2, prepared [3])
 running store           locked=False write_failed=True
 after a restart         locked=False; ok=True d.rr=False p.rr=False
```

### 2. The sweep's own `exercise`, case by case

With `PYTHONPATH=control:control/mail_tests` and the stand-in:

```python
import test_owner_state_sweep as sweep
from owner_state_oracle.gaps import Gaps
gaps = Gaps(recording=True)
sweep.exercise('restore', 75, 'persistent', gaps=gaps)                 # exhausted, live-restored
sweep.exercise('restore', 75, 'persistent', gaps=gaps, phase='crash')  # crash-locked, crash-restart
```

- **The restore flow's clean run has 76 fault points.** 4-5 write and sync the final record, 6-9 the index, 10-25
  stage the event in SQLite, 26-73 apply it, 74-75 write and sync the commit marker, 76 is a read-only close and is
  never a primary point.
- **All 70 primary points, both modes (140 cases):** the confirm answers `storage_limit` and the running store
  stays locked with `write_failed` set, every time. A restart is still locked for points 4-25 and unlocked for
  26-75. The oracle's decoded lock differs from the running store's in exactly one case, `restore/persistent/75`.
- **C5's keys** at `restore/persistent/75/0` (121 keys recorded, 26 of them the disagreement): `exhausted` and
  `live-restored` each have `control_pending.restore-lock`, `passive.restore-lock` and the envelopes'
  `restore-lock` (expected `False`, observed `True`), four `response.*.status` (expected `allowed`, observed
  `restore_required`) and `recovery-holds`; `crash-restart` has the failed confirm's own envelope. The pair case
  `restore/single/75/76` has 14 of the same kind. `aresos log.restore-lock` is *not* a gap there: the oracle
  expects "not locked" and item 2's blind reader observes "not locked".
- **Local equals CI.** For `restore` 0, 26, 73, 74, 75, 75:76 and `cancel` 0, 2, 2:3, 30, 67, 68, 69, every phase:
  1,234 recorded keys, the same set and byte-identical deltas as capture 43722918063. So nothing merged since
  moved these cases.

### 3. A lock census of every fault point

For each primary fault point and both modes: run the faulted call, read the oracle's decoded lock and the running
store's lock, then start a new engine on a copy of the same bytes and read its lock. No views are compared.
All 34 flows: 10,865 primary fault points, 21,730 cases, no harness error. Every faulted call was answered
`storage_limit`. About 50 minutes on 7 processes.

| Oracle's decoded lock | Running store | After a restart | Cases |
|---|---|---|---|
| not locked | not locked | not locked | 14,732 |
| not locked | not locked | locked | 6,375 |
| **locked** | **not locked** | not locked | 483 (322 single, 161 persistent; item 3) |
| locked | locked | not locked | 97 (restore flow, points 26-75) |
| locked | locked | locked | 42 (restore flow, points 4-25) |
| **not locked** | **locked** | not locked | 1 (`restore/persistent/75`; item 1) |

- All 483 "model locked, store not" cases have the head ahead of the last commit marker, with a matching staged
  event. None is locked after a restart. Per flow their number equals the capture's cases with a
  `passive.restore-lock` gap (483 = 483); the point numbers are equal too, or shifted by the stand-in's 4 points.
- The only "store locked, model not" case is `restore/persistent/75`.
- The second row is the `crash-locked` phase: 6,375 cases, the capture's number for item 2 outside the restore
  flow. There the running store is not locked and the restarted one is.
- With both rules of the brief ("behind" only, plus item 1's rule) the model's lock equals the running store's in
  every census case.

### 4. The capture's own lists

`gh run download 43722918063` into an empty scratch directory (61 artifacts, 12 MB), read as data with
`python3 -I`, one of the 53 `owner-gaps-*.json.gz` lists in memory at a time (about 3 s, under 1 GB). They hold
2,622,072 keys, the pin's count. Keys ending in `.restore-lock`:

| Phase | View | Expected / observed | Restore flow | Other flows |
|---|---|---|---|---|
| `crash-locked` | `aresos log` | True / False | 42 + 51 pair | 6,375 + 9,514 pair |
| `exhausted` | `aresos log` | True / False | 69 | 161 |
| `live-restored` | `aresos log` | True / False | 139 + 193 pair | 483 + 903 pair |
| `exhausted` | `control_pending`, `passive`, envelopes | True / False | - | 161 + 161 + 929 |
| `live-restored` | `control_pending`, `passive`, envelopes | True / False | - | (483 + 903) × 2 + 2,619 + 5,271 |
| `crash-restart` | envelopes built before the crash | True / False | - | 510 + 1,060 pair |
| `exhausted`, `live-restored`, `crash-restart` | all of the above | False / True | 25 (C5) | - |

- Item 2: 15,982 + 69 + 332 = 16,383. Item 1: 25. Item 3: 15,030 (every "other flows" cell except the first
  row). Together 31,438, which is all of them.
- The 644 single-fault cases of item 3 are 322 points: each in single mode at the marker's write and at its sync,
  and in persistent mode at its write (322 single, 161 persistent; the 161 are also the `exhausted` cases).

### 5. A prototype of the three model changes

In scratch copies of `control/` (never committed), about 20 lines:

- `compare.py:121`: the stand-in page of a refused read gets `'restore_required': code == 'restore_required'`.
- `records.py`: a record field `interrupted_confirm`; `consistency_errors` adds it to its formula; both lock
  formulas use `<` instead of `!=`. `perturb.py`: the same two edits, and the field in `RECORD_EXCLUSIONS`.
- `driver.py`, `snapshot()`: the field is true when a scripted `control_restore_confirm` with a locked
  precondition has a non-empty fault trace since the last restart, and it is OR-ed into `locked`. The sweep's
  crash branch marks the restart.
- A first version set the flag after the faulted call returned. That is too late: the sweep captures the failed
  confirm's own reply inside the call. The rule has to hold at that capture.

Three trees at paths of equal length (unchanged; items 1 and 2; all three), the same cases in each: per flow the
clean run, every head-ahead point and the first three points whose restart is locked (for `onboarding` its first
12 head-ahead points). All 34 flows, 1,657 cases with recorded keys, 41,987 keys in the unchanged tree.
`control/tests/test_owner_state_oracle.py` (120 tests) passes on all three.

| Step | Closed | Changed | New |
|---|---|---|---|
| Items 1 and 2 | 185 lock views, 8 read statuses, 2 `recovery-holds` | 0 | 0 |
| Then item 3 | 4,686 lock views, 1,244 read statuses, 508 `recovery-holds`, 2,982 row and notice keys | 624 read statuses (expected set), 1,705 row and notice keys, 290 more by alias numbers only | 107 count keys |

- Not counted as changed, in either step: 40 export-flow keys whose text differs only by the scratch tree's
  directory name.
- After all three, **no key ending in `.restore-lock` is left** in any flow.
- Every key that item 3 closes, changes or adds is at a head-ahead case.
- The 107 new keys are counts (`notice-count`, `total`, `pending-total`) in `archive`, `onboarding`, `repair` and
  `status`. Example: `repair/single/69/0/crash-restart/envelope.mail_operation_repair.pending-total`: the store
  counts 2 pending (it shows the repair operation its unfinished write applied), the model now counts 1 (committed
  rows only). With the old formula the model's "restored" rows happened to give 2.

**The local sample for the builder** (brief, "Re-pin"): `restore` 0, 26, 73, 74, 75, 75:76 and `cancel` 0, 2, 2:3,
30, 67, 68, 69.
- Items 1 and 2: 52 keys close, nothing else differs. `restore`: 10 `aresos log.restore-lock`, 25 other lock
  views, 12 read statuses, 3 `recovery-holds`. `cancel`: 2 `aresos log.restore-lock` (the `crash-locked` phase of
  `persistent/2/0` and `single/2/3`).
- Item 3 on top: `restore` unchanged; `cancel` 68 and 69: 134 keys close and 62 change.

## Where the existing notes were wrong or incomplete

- **"The `aresos log` view says not locked"** (`REVIEW-REPIN-3.md` NOTE 5, the report and the handoff). The
  service's log reply says locked twice. The oracle's reader cannot see either. And `control_log`'s data has no
  such field even when answered, so this check can never observe "locked".
- **"6,375 points."** That is the number of single-fault `crash-locked` cases outside the restore flow (3,268
  points, most in both modes). The same key is pinned on 9,514 pair cases there and 93 restore-flow cases, and the
  same reader causes 401 more keys in the restore flow's live phases: 16,383 in all.
- **"C2's mirror of C5"** (`KNOWN-GAPS.md`, last section). It is not C5 reversed. C5 is the running store holding
  a lock the bytes no longer show. The "mirror" is the decoder's formula flagging an unfinished write as a restore:
  neither the running store nor a restarted one is locked there. `control/README.md:176-178` and `storage.py:208`
  both say "behind".
- **C5 itself** is described correctly ("the running store keeps its lock until restart"). Two things were not
  said: the single-mode twin agrees only because the decoder's "differs" rule also fires there (head 6, marker 5),
  and a restart ends unlocked in both modes.
- `REVIEW-REPIN-3.md` NOTE 4 and section 5, and the C5 row's "44 + 2 + 2" (a difference between two pins, not the
  size of the disagreement), match what I measured.

## Limits

- The census reads lock flags only. It compares no view.
- The prototype comparison covers the cases listed (1,657 of the sweep's cases), not the whole sweep. The
  capture decides.
- I did not run the alteration suite (`test_owner_state_perturb`) against the prototype; it is 12 shards in CI.
- Item 3's exact counts of changed row keys are not predicted; only their class and where they may occur.
