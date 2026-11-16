# Brief 20-restore-lock-followups: what was read and run

## Build (2026-11-16, Claude agent on Opus 5.5)

Builder of the brief on this branch. **Outcome:** all three items built as the brief and review 1 say; the capture
falls entirely inside the brief's classes (16,383 + 40 keys close, every difference at H, 2,512,704 keys byte for
byte, no `.restore-lock` key left); the new pin is 2,576,083 keys, and the proof's 48 strict shards and 12
alteration shards pass. **For the lead:** the proof's ledger job is red, in the installed-channel test, from #69
(18e), not from this package (section "The ledger job"); and N7's named class needs its decision on the board.

No production code changed: `git diff 5d717142 HEAD -- control ':!control/owner_state_oracle' ':!control/tests'
':!control/mail_tests'` shows only main's `control/chrome/qualification.json`, brought in by the merge.

### What changed, per item

- **Items 1 and 2** (commit `1d6b1d43`):
  - `records.py`: the record field `interrupted_confirm`, and `service_lock(record)`: the lock a running
    service holds beyond its bytes (the startup rule, or a confirm that met a fault). `consistency_errors`
    uses it; so do the alteration recompute (`perturb.py`, the field listed in `RECORD_EXCLUSIONS`) and the
    driver. One formula in three places.
  - `driver.py`: `interrupted_confirm(calls)`: the most recent scripted `control_restore_confirm` with
    `restore_precondition` true met a fault (its trace only, never its reply), counted from the last
    restart. `Driver.apply_service_lock` assigns it, the startup rule and the lock on every snapshot (N2:
    recomputed, not `|=`). It holds when the failed confirm's own reply is captured: the sweep's `scripted`
    entry gets its trace before `observer(index, reply)` (N1), and that entry is the most recent confirm.
    A cached record whose lock changes is copied, so an envelope keeps the lock it was captured with.
    `Driver.restarted()` replaces only the two pokes in `exercise` (N3).
  - `test_owner_state_sweep.py`, `exercise`: S1's harness check. Any scripted confirm on a locked store with a
    fault trace that was answered `ok` stops the sweep with "revisit the oracle's rule for an interrupted
    confirm".
  - `compare.py`, `pages`: a refused read's stand-in page has `restore_required: code == 'restore_required'`.
- **Item 3** (commit `b61b982b`): `records.behind(sequence, committed)`, the head *behind* the last commit
  marker, used by the decoder, `consistency_errors` and the alteration recompute (S3). Its docstring names
  the lock's other terms, which stay (N4).
- **Merge of `main`** (`590f96bf`, S4): main changed nothing under `control/aresos_control` or
  `control/owner_state_oracle` since `5d717142`.

### Tests and mutations

- `control/tests/test_owner_state_oracle.py` (`OwnerOracle`):
  `test_refused_read_page_says_locked_only_when_the_lock_refused_it` (item 2),
  `test_interrupted_confirm_is_a_term_of_the_lock` and `test_interrupted_confirm_holds_until_the_next_restart`
  (item 1: the rule, the locked precondition, "most recent", the restart, the copy),
  `test_only_a_head_behind_the_last_marker_is_a_restore` (item 3: ahead, equal and behind through the decoder,
  `consistency_errors` and `coherent_change`; helper `history()` beside `disk()`).
- `control/tests/test_restore_batches.py`, no oracle: the confirm's last marker sync fails, with a working and
  with a failing rollback. Both: `storage_limit`, the lock kept, `control_pending` says `restore_required:
  true`, `control_log` refused; after a restart unlocked with the confirm's generation. The lock is made with
  a direct store write (no `testapp_prepare_send`, which needs the managed-settings file locally).
- `control/mail_tests/test_owner_state_sweep.py`:
  `test_confirm_failed_at_its_last_point_keeps_the_lock_until_the_restart` (item 1: the restore flow's last
  fault point from the clean run, persistent live and crash, every pair case of that point, live and crash;
  no key ends in `.restore-lock` or `.status`, none is `recovery-holds`),
  `test_harness_refuses_a_confirm_answered_ok_after_a_fault` (S1's mutation as a standing test: the store
  answers the faulted confirm `ok`; single mode, since in persistent mode every later disk call fails and the
  reply is refused anyway), `test_refused_log_under_the_lock_is_seen_as_locked` (item 2: `cancel` 2,
  persistent, crash-locked), `test_write_unfinished_at_its_marker_is_not_a_restore` (item 3: `cancel`'s last
  fault point, single, live).
- `mutations.py` (N8; why not `reviews/20-chrome/mutation-audit.py` is in its docstring): 14 probes, each
  rejected by every test it names, run one by one; every baseline passed. Record: `mutations.json`.
  - Item 1: `self.locked = False` in a `finally` (2 tests); the rule removed (oracle and sweep tests); the rule
    kept after the restart (both); the locked precondition dropped; the rule accumulated (`|=`); the captured
    record changed in place; the term dropped from `consistency_errors`; the harness check removed.
  - Item 2: the field dropped (oracle and sweep tests); the field set for every refusal.
  - Item 3: `!=` restored in the decoder (oracle and sweep tests), `<=` in `behind`, `!=` restored in
    `consistency_errors`, `!=` restored in the recompute.

### Local results

All as an ordinary user, with the findings' managed-settings stand-in for the Mail suite; nothing under
`os/tests`, no rpm-ostree, bootc or ostree, no container.

- `control/tests`: `test_owner_state_oracle` 124 OK; `test_restore_batches` 4 OK; `test_mail_ci_selection` and
  `test_owner_state_fixes_s2` OK; `test_owner_state_channels` needs root (`os.chown`), as at the base: CI's
  ledger job runs it.
- `control/mail_tests` (after item 3): the sweep module's unit tests (11, all but the full sweep),
  `test_owner_state_quiet`, `_regressions`, `_s2_effects`, `_plants`, `_contracts`: 37 OK.
  `test_owner_state_perturb` shard 0 of 12: 9 scenarios, 230,298 alterations, slipped=0 (the same totals as
  that shard in capture 43722918063), 16 minutes.
- The local sample (`restore` 0, 26, 73, 74, 75, 75:76; `cancel` 0, 2, 2:3, 30, 67, 68, 69; every phase):
  - base `5d644ba1`: 1,234 keys, the same set and byte-identical deltas as capture 43722918063;
  - items 1 and 2: 1,182 keys. 52 close, nothing else differs: `restore` 10 `aresos log.restore-lock`, 25 other
    lock views, 12 read statuses, 3 `recovery-holds`; `cancel` 2 `aresos log.restore-lock`. All 52 are in the
    item 1 or item 2 class;
  - item 3 on top: 1,048 keys. 134 close and 62 change, all at `cancel` 68 and 69 (`persistent/68/0`,
    `single/68/0`, `single/69/0`), all three in H; `restore` unchanged; no key ends in `.restore-lock`;
  - after the merge of `main`: the same 1,048 keys.
  - Clean-run point counts: `restore` 76, `cancel` 70, as at the capture.

### The runs

Dispatches of `control-owner-oracle.yml` on this branch: 2 of 3 used.

| Run | Commit | What | Result |
|---|---|---|---|
| 43893138937 | `590f96bf` (items 1-3, main merged) | capture | 48 sweep and onboarding shards fail only the strict sweep test against the old pin, after writing their lists; 12 alteration shards pass (2,080,049, none slipped); ledger fails in `test_owner_state_channels` (below) |
| 43919136534 | `accf2eb0` (the new pin) | proof | 48 strict sweep and onboarding shards and 12 alteration shards pass; its 53 lists reproduce the pin byte for byte; ledger fails as in the capture, so the run is red |

S4: before the capture `git diff 5d717142 origin/main -- control/aresos_control control/owner_state_oracle` was
empty (main had changed only `control/chrome/qualification.json`); merged as `590f96bf`. Before the proof, main had
moved again (#89 and others), still nothing under those two folders; not merged, so the proof runs the captured code.

### The classification

My own scripts in a scratch directory, not committed: `merge.py` (merges a run's 53 lists one at a time, refuses
conflicting shared keys, about 0.5 GB), `packcheck.py` (packs a merged list like `gaps.py` and compares it with the
pin), `points.py` (clean-run point counts from the sweep logs), `classify.py` (the classes below; under 1 GB).
- Baseline: the 53 lists of 43722918063 reproduce the old pin byte for byte (2,622,072 keys, `ee326914…`).
- The capture: 2,576,083 keys, 1,930 groups, 892,234 bytes, SHA-256 `8b27b116…`; `gaps.py`'s documented
  commands and my packer give the same bytes.
- Point counts: equal in all 34 flows.
- Against the brief's numbers:

| Class | Brief | Capture |
|---|---|---|
| Item 2 closes | 16,383 | 16,383 |
| Item 1 closes | 26 + 14 (25 lock views, 12 statuses, 3 holds) | 26 + 14 (25, 12, 3) |
| H (S2) | 1,386 cases (322, 161, 903), 92,945 keys | the same; 30,291 close, 9,316 change, 725 appear, 53,338 stay |
| Item 3's lock-view keys close | 15,030 | 15,030 |
| Outside H and the 16,423: byte for byte | 2,512,704 | 2,512,704, none added |
| Keys ending `.restore-lock` afterwards | 0 | 0 (from 31,438) |

- At H, read statuses: 1,779 changed their expected set only (`restore_required` → `allowed`/`journal_incomplete`;
  their pages observed `allowed` now pass), 157 by alias numbers only, 3,939 closed. `recovery-holds`: 1,547 closed,
  274 (`crash-restart`) unchanged. Rows and notices: 9,775 closed, 1,156 changed by alias numbers only, 6,224
  changed otherwise, 725 new counts.
- N7's named class, the rows left at H: 6,949 keys (6,224 + 725) at 870 cases in 16 flows; in `KNOWN-GAPS.md`.
- Also unchanged: every failing point (10,247) and case (53,066), the 377 fixed keys, the 544,801 other
  `crash-locked` keys, the restore flow's 22,915 other keys.

### The ledger job (both dispatches)

`test_owner_state_channels.test_paged_committed_pending_through_every_installed_channel` fails at line 109: the
Stop hook prints nothing and `json.loads('')` raises. Not this package's: no oracle code takes part in the hook's
output, and this package changed no production code. The test's hook part was changed by 18e (`139a9696`), merged
with #69 on 2026-11-16 after the last run of this workflow (43738332693, 2026-11-15), so this optional workflow had
not run it since. `hooks.main` returns silently when `usage.used()` finds no mark for its session; the test marks
its own process first (`mark_session`). It needs root (`os.chown` in `Integration.setUp`), so I could not reproduce
it on the laptop. Main's later #89 does not touch it.

### JUDGMENT-CALLs (technical, for the lead)

- **Where item 1's rule lives.** `driver.interrupted_confirm(calls)` reads the script; the record carries the
  result; `records.service_lock(record)` is the one formula that `consistency_errors`, the alteration recompute and
  the driver share (it also holds the startup rule they already shared). To change: move the rule into
  `records.py`; about 10 lines, no key changes.
- **Which script entries count.** Both entries of the confirm (the driver's `observe` entry and the sweep's
  `scripted` entry) are confirms; the rule takes the most recent, which is the `scripted` one during the call. To
  change: filter on `request_method`; no key changes today.
- **Copy, not change in place.** When the rule flips on a record the driver has already handed out, the driver
  copies it, so an envelope captured earlier keeps its lock and the oracle's identity cache cannot return a stale
  projection. The startup rule now goes through the same path (recomputed each snapshot instead of `|=`); same
  results, since its inputs change only with a re-decode. To change back: one line, and N2's "assigned on every
  snapshot" would then rely on monotonic rules again.
- **S1's harness check** looks at every scripted confirm in the run, not only the faulted call, and its mutation
  is a standing test (`test_harness_refuses_a_confirm_answered_ok_after_a_fault`) in single mode: in persistent
  mode every later disk call fails, so the reply is refused even when the confirm itself is made to succeed.
- **Mutation records** in `reviews/20-restore-lock-followups/mutations.py`, not `reviews/20-chrome/mutation-audit.py`
  (N8's first option): that harness cannot import `control/tests`' `support` or `control/mail_tests`, and the Mail
  suite needs the managed-settings stand-in. To move the four base-suite-only probes there: about 10 lines.
- **The store-level test** makes the lock with a direct store write and fails the confirm's first commit-marker
  sync (found by reading the journal's tail), instead of `repro.py`'s `testapp_prepare_send` and "second sync":
  the former needs the managed-settings file locally, the latter depends on how many syncs a write does.
- **The proof's ledger job** is red for the reason above; I treated the proof as the pin's proof (the 48 strict
  shards and 12 alteration shards) and opened the PR. If the lead wants a fully green proof first, the channel
  test needs a fix on main and then one more dispatch (the third).

### PLAN-GAPs

- The brief and review 1 checked drift on main only since this branch's base (S4). Between the old pin's capture
  (`065275ff`) and the base, #69 (18e) changed production code under `control/aresos_control` (engine, daemon,
  protocol, hooks, usage, files). The classification shows no sweep key moved by it, but #69 broke the optional
  workflow's ledger job, which nothing had run since.
- "Mutation caught: the term dropped from `records.py:81`": with one shared `service_lock`, the probe drops the term
  from `consistency_errors`' use only (`item1-term-dropped-from-consistency`); dropping it from `service_lock`
  itself is caught too, by every item-1 test.
- The brief's sweep test for item 3 runs one case (`cancel`'s last point); the census-level claim rests on the
  capture.

## Findings (Claude Fable, before the build)

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
