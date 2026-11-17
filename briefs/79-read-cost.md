# Brief 79-read-cost: the qualification record's read cost (empire brief 301)

Lead: `linux-tools`, 2026-11-17. Written by a Claude agent on Fable 5.2: it changes how Chrome's rollback gate is
read. Every claim was checked against the code at `main` `d0b91522`, and the design was tried on a scratch copy
outside the repo (numbers under "Measured"). Sources: queue items 15 and 14; `reviews/79-followups/` (PROGRESS, "Not
done here", "The lead after the build" and JC3; REVIEW-1; RECHECK-1's nit); `reviews/control-followups/REVIEW-1.md`,
nit 1; commit `e2e4eedc` and its revert `36a477c7`, both on `origin/fix/79-followups`.

**Outcome.** One PR, three changes:
1. A `chrome_` request reads the qualification record in constant time. The full check runs once for each new
   record, no longer two to five times per request.
2. `Qualification.hold()` becomes `_hold()`.
3. The latency probe refuses a store that holds an exclusive lock.

The proof is the 300-entry latency leg that #93 had to revert. It comes back and must pass with every ceiling as it
is. Nothing the owner sees changes.

**Words.**
- The *held record* is the qualification record the service keeps, key `chrome:qualification`. It is one line of
  the journal `operations.jsonl`, not a file of its own. Chrome reads it through `store.chrome_state` (`Projection`,
  `control/aresos_control/chrome/committed.py`).
- The *shipped copy* is `control/chrome/qualification.json` in the image. `Chrome.__init__` reads it once, when the
  service starts (`adapter.py:118`).
- To *reconcile* is `record()`'s rollback check: one of the two must extend the other, entry for entry
  (`append_only`). If neither does, the read refuses with `qualification_rollback`.
- The *full check* is: parse the journal line, check the journal record's hash, validate the held record, reconcile.
- The journal's *signature* is its (inode, size, modification time), which `Projection.sync()` compares on every read.

## Today

One `Qualification.record()` call (`qualification.py:129`) does all of this, whatever changed:
- `Projection.get()` hashes the whole journal record and deep-copies the value;
- `validate_record` runs three times (the held record twice, the shipped copy once);
- its caller then runs `switches()`, which validates the record a fourth time.

Callers: `mode()` (`adapter.py:211-214`, with `maintenance()`, `adapter.py:234`), each reserved row in
`pending_state()` (`adapter.py:260`), and the version notice (`engine.py:764-765`).

## Measured (laptop, Python 3.14.8, fixture engine, medians)

Today:

| Entries | One `record()` | Of which |
|---|---|---|
| 1 | 0.03 ms | |
| 11 | 0.18 ms | |
| 301 | 4.6 ms | hash 0.65, copy 0.92, three validations 2.9; `switches()` adds 1.0 |
| 1,001 | 15.8 ms | |

| Request at 301 entries | Reads | Validations | Time in the record |
|---|---|---|---|
| `read`, nothing pending | 2 | 8 | 11.5 ms (the request: 0.7 ms with one entry, 12.1 ms with 301) |
| a click that asks | 5 | 20 | 32.6 ms |
| `read`, one reserved operation pending | 6 | 24 | 39.7 ms |

Each reserved operation adds four reads to every later request. The CI runner is about 1.7 times slower: run
43895214619 measured `read` at 39.8 ms (ceiling 35) and `asking_click` at 72.2 ms (ceiling 60) with 300 entries.

With this brief's design (scratch prototype, same fixture):

| Entries | A read that hits | A full check | `read` request | In the record: `read` / a click that asks |
|---|---|---|---|---|
| 1 | 0.013 ms | 0.05 ms | 0.63 ms | |
| 301 | 0.013 ms | 4.2 ms | 0.61 ms | 0.018 ms / 0.13 ms |
| 1,001 | 0.013 ms | 14.2 ms | 0.63 ms | 0.018 ms / 0.27 ms |
| 10,001 | 0.013 ms | 146 ms | 0.62 ms | |

A steady request runs no validation at all. The full check runs once per new record and once per service start.

## The design

### Decision: check once per record, keyed by the record's bytes in the journal

**Rejected: only drop the duplicate validations.** One hash, one copy and one validation per read would still
cost about 2.6 ms at 301 entries, half of today's 5.6 ms with `switches()`. The cost keeps growing with the
record, so the ceilings are reached again at about twice the entries, a few months later. A cache per request has
the same slope and needs care with writes inside the request (JC3).

**Rejected: a flag that the writer sets.** `_hold()` is not the only writer in practice. The fixtures and the CI
harness write the key with `store.write` (`chrome/ci/service.py:29` and `:64`, `chrome/ci/sites/qualification.py`,
`set_record` in `test_qualification_service.py`). A cache that waits for `_hold()` to clear it would miss those.
The cache below has one way to become invalid: the committed bytes differ.

**Chosen.** `Qualification` keeps one slot: the last record that passed the full check, with a *pin* on the journal
line it was read from. A read first asks the `Projection` whether the pin still holds. If it does, the read answers
from the slot. If not, it runs the full check on the bytes now on disk and fills the slot only when every check
has passed.

### The pin (new, in `committed.py`)

Three small methods on `Projection`. They are for keys whose value is one journal record's entry as written; refuse
`op:` and `notice:` keys with `ValueError` (their values merge acknowledgements and older rows).

- `pin(key)`: `sync()`, then read the key's journal line from disk at its committed offset (through
  `journal_reader()`, never from `record_cache`). Returns `{'offset', 'line', 'signature'}`, or `None` when the key
  has no committed value. `line` is the raw bytes including the newline.
- `holds(key, pin)`: `sync()`, then:
  - no committed value now: true only if `pin` is `None`;
  - the key's offset differs from the pin's: false;
  - the journal's signature equals the pin's: true, with no read;
  - else read the line again and compare the bytes. Equal: store the new signature in the pin and return true.
    Different: false.
- `pinned_value(key, pin)`: parse `pin['line']`, check the journal record's hash exactly as `get()` does (same
  `evidence_corrupt` refusal), return `record['chrome'][key]`. The value comes from the very bytes that are pinned.

`get()`, `sync()` and `record_cache` stay as they are.

### What the slot holds, and who reads it (`qualification.py`)

- The slot: `{'pin', 'record', 'own'}`. `record` is the reconciled record. `own` is this build's entries of it, in
  record order. Both are private: nothing hands these objects out.
- `_current()` returns the slot, after `holds()` or after a full check. It is the only place that writes the slot,
  and it writes it after the last check has passed. With no held record the pin is `None` and the held value is
  the shipped copy, as today.
- `record()`: a deep copy of the slot's record. Today it returns the shipped object itself when the shipped copy
  wins; a private copy is safer. It is for `verified()`, the tests and CI's `attestation.py`.
- `switches(chrome_version)` (new method): the switches for this build, computed from `own`. It parses the version
  first, as the module function does, so a bad version still gives `invalid_input`.
- `covers(chrome_version)` (new method): whether `own` has an entry for exactly this version. It replaces the scan
  in `maintenance()`.
- The module function `switches(record, build, chrome_version)` keeps its behaviour for every input: it validates,
  filters by build, then calls the same core the method calls. Split that core out as `own_switches(own, current)`.
- `shipped` becomes a read-only property over a private deep copy taken in `__init__`. Nobody can swap or change
  it under the slot. No test assigns it today.

Callers (`adapter.py`, `engine.py`) stop passing records around:
- `mode()`: `self.maintenance()`, then `mode = self.qualification.switches(self.bridge.version)`.
- `maintenance()`: the same guards as today, then
  `force = not self.qualification.covers(self.bridge.version) and getattr(self, '_refresh_attempted', None) != identity`,
  then `self.qualification.refresh(force=force)`. It returns nothing.
- `pending_state(projection=True)`: `mode = self.qualification.switches(self.bridge.version)`.
- The version notice: `chrome.qualification.switches(chrome.bridge.version)['notice']`.

After the build, `qualification.record(` appears in `control/aresos_control/` only inside `qualification.py`.

### The cache key, and what invalidates it

The key is the pin: the key's journal offset and the exact bytes of that journal line. The journal's signature
only decides when the bytes are compared again.

| What changes on disk | What notices | Result |
|---|---|---|
| A committed write of the key (`_hold()`, or a fixture's `store.write`) | `sync()` indexes the new journal record; the offset differs | full check of the new record |
| Any other committed write (the journal grows) | the signature changed; the line is read and compared: equal | the slot stays; no full check |
| The journal is replaced by another file with the same bytes at that offset | new inode; compared: equal | the slot stays |
| The journal is replaced or rewritten with other bytes at that offset (size or time changed) | compared: different | full check on the new bytes: `evidence_corrupt` if the record's hash fails, `qualification_invalid`, `qualification_rollback`, or the new record if it passes everything. Exactly what `get()` plus `record()` give today |
| The journal is rolled back to an older copy (shorter than what was read) | `sync()` | `evidence_corrupt` on every read, as today |
| The line is rewritten in place and inode, size and modification time all stay the same | nothing, until the journal next changes or the service restarts; then the compare runs | until then the checked record stays in use |
| The shipped copy file is replaced, rewritten or rolled back | nothing in a running service: it reads the file once at start, today too | the restart that comes with an image update builds a new `Qualification` with an empty slot; its first read reconciles against the new copy |

The same-signature row is today's rule, not a new gap. `sync()` returns at once on an unchanged signature, and
`get()` then serves its cached parse. Today's code reads the line again in that state only by accident, when five
other journal records have pushed it out of `record_cache`. Reading the journal on every read would close the row.
It was tried: it adds a journal open to every read, and the fault sweep's `drop` flow grew from 333 to 469 pair
cases. The row needs a program that rewrites the journal at the same size and resets its time (or lands in the
clock tick of the journal's last write), as the service user or root. A restore or an update never does that. See
judgment call 1.

### Which checks run when

- **Every read:** `sync()` (one `stat`; after a journal change also the truncation check, the hash chain of the
  appended records and the index), the offset compare, the signature compare, the version parse, and the switches
  over this build's entries.
- **Every read after the journal changed:** one read of the held line from disk and a byte compare (0.04 ms at 301
  entries, 0.13 ms at 1,001).
- **Only when the bytes differ, and on the first read after a start:** the parse, the journal record's hash,
  `validate_record`, the reconcile against the shipped copy, and the filter for this build.
- **Once per object:** validation of the shipped copy.

The build adds no disk operation to a read: the held line is read from disk when the journal changed, which is
when `get()` reads it today. (One exception: when the bytes at the pinned offset turn out different, the line is
read a second time for the full check.) Measured on the prototype: the fault sweep's surface is the same as on
`main` for all seven flows tried: `qualification` (54/54/98), `delivery` (109/109/259), `readonly` (52/52/202),
`drop` (68/68/333), `allow` (52/52/202), `trusted` (437/437/2148) and `stopped_submit` (393/393/1925).

### Every failure stays closed

- `sync()` raises (truncated journal, broken chain, a failing `stat` or read): the read raises. The slot is not
  consulted.
- The bytes differ and the full check fails at any step: the read raises with that step's refusal
  (`evidence_corrupt`, `qualification_invalid`, `qualification_rollback`) or its error (a line that is not JSON).
  The slot is not written. The next read finds the same mismatch and refuses again, until the committed bytes pass.
- The slot is used only when `holds()` has returned true in this very read. There is no path from a failed check
  to an answer, and no time-based reuse.
- A slot left from before a failure is pinned to other bytes. It can serve again only if the disk holds exactly
  those bytes again, which is then the right answer.

### `refresh()`'s `written` flag and `maintenance()`'s second read

- `refresh()` does not change, except that it calls `_hold()`. It still returns `written`, and `written` still
  chooses the fetch result's text ("may have been updated" or "held record retained").
- `maintenance()` no longer hands a record to `mode()`, so there is no record that could be stale across the
  write. `mode()` asks `switches()` after `maintenance()` has returned, and that answer follows the journal as
  committed at that moment. A write that raised after its commit is in the journal, so it is seen. A write refused
  before its commit is not, so the old record rightly stays.
- #93's two tests stay unchanged and must pass: `test_o2_mode_trusts_the_record_its_own_refresh_accepted` and
  `test_o2_mode_refuses_by_a_fetched_record_whose_write_raised_after_its_commit`.
- The daemon's two `maintenance()` calls (`daemon.py:122`, `:267`) ignore the return value today. They read the
  record in the same cases as before: only with a connected Chrome and refresh on.

### Threads and processes

- The service is one thread: a selector loop, no threads anywhere in `aresos_control`. The slot has no per-request
  state, so a nested `engine.request` (`owner_request`) needs no care.
- One process holds the store. `Store` takes an exclusive, non-blocking `flock` on the journal
  (`storage.py:181`); a second store on the same directories fails to open. The helpers (`aresos admin`, the MCP
  proxy, Chrome's native host) talk to the service over its sockets and never open the store.
- So the only product writer of the record is the service itself, in `_hold()`.
- The slot is memory of one `Qualification` object. A restart, or a second object over the same store, starts
  empty. It must not move to the store, the projection or a module global: two objects with different shipped
  copies share one store in `test_qualification.py`.
- A write by another process that ignores the lock still changes the journal's size or time, so the next read
  compares the bytes. The slot never depends on the writer telling it.

## Also in this package

**`hold()` becomes `_hold()`** (RECHECK-1's nit). It writes what it is given, so only `verified()`'s output may
reach it. Its callers are `accept()` (`qualification.py:138`) and `refresh()` (`:180`), nothing else in `control/`,
`.github/` or `docs/`. No test calls it. Add a test that `Qualification` has no `hold`.

**The probe refuses exclusive locking** (queue item 14). In `control/chrome/ci/latency-profile.py`, `install()`,
beside the header check:
`assert store.db.execute('PRAGMA locking_mode').fetchone()[0]=='normal','control.sqlite holds an exclusive lock; its commits cannot be counted'`.
Ask the store's own connection: the mode belongs to a connection, and the query opens no transaction. Test in
`test_latency.MainFixStorageStages`: set `PRAGMA locking_mode=EXCLUSIVE` on the fixture's connection, and `install`
raises `AssertionError` matching `exclusive`; set it back to `NORMAL`, and `install` succeeds. The real-`Store`
test beside it shows the product's store still installs. The old runtime `ab7aba92` runs this probe too, so the
latency job proves it there.

## The proof

**The 300-entry leg.** `git cherry-pick -x e2e4eedc` (it applies cleanly on `d0b91522`). Then two edits:
- `realistic_leg()` also requires `environment.get('EFFICIENCY_PROBE') != 'true'`, with a test line. #72 starts its
  efficiency run in the same image with the same three variables; it keeps its one-entry record this way.
- `test_the_harness_starts_from_the_shared_records_and_says_which` checks the pair script with
  `assertRegex(pair, r'-e LATENCY_PRIVACY -e LATENCY_BASELINE="\$(latency_)?revision"')`. #72 renames that shell
  variable; the literal from `e2e4eedc` would fail once #72 is in.

Unchanged, byte for byte: `latency-targets.json` (ceilings and sample counts), `latency-pair.sh`,
`latency-reference.json`, `latency-summary.py` (the reference pins its hash) and `latency-check.py`.

The PR's Control Chrome run must be green, with both latency jobs. In the plain job's current artifact,
`service.txt` says `FIXTURE_QUALIFICATION {"shipped_entries": 300, "held_entries": 301}`. Report `read` and
`asking_click` per history phase beside their ceilings and beside main's last run. Expect them within noise of
main (about 20 ms and 30 ms at history-4000). The sync counts stay 0, 2, 4 and 10: the build adds no write.

**Unit tests.** New class in `test_qualification.py` (a `Store` and `Qualification`, as `Delivery` does), unless
another file is named. Count full checks by wrapping `q.validate_record`.

| # | Test | It proves |
|---|---|---|
| 1 | A repeat read checks nothing: `switches`, `covers`, `record`, three times | the slot is used |
| 2 | Another key's committed write: the next read checks nothing | the key is not the journal's signature |
| 3 | A read opens the journal only after the journal changed: count `journal_reader` calls; 0 while nothing changed, 2 on the first read after another key's write (`sync()` and the compare), 0 after | no disk operation is added per read |
| 4 | A newly committed record is used by the very next read (a later patch that failed `binding`) | invalidation by offset |
| 5 | A held record that diverges from the shipped copy: `switches`, `covers` and `record` each raise `qualification_rollback`, twice in a row; the same with an invalid record and `qualification_invalid`; then a good record reads again | a rolled-back record is refused on every read, and a refusal fills no slot |
| 6 | A held record shorter than the shipped copy gives the shipped copy, also for `switches` and `covers` | `own` comes from the reconciled record |
| 7 | The held line rewritten in place at the same length, hash recomputed, a shipped entry's `run` changed, time moved one second: `qualification_rollback`, twice | bytes are compared, not offsets or lengths |
| 8 | The same with the newest entry changed and the hash not recomputed: `evidence_corrupt`, twice | the journal record's hash check still runs |
| 9 | The same rewrite with the time set back (same inode, size and time), then another key's committed write: `qualification_rollback` | the compare runs at the next journal change |
| 10 | The journal replaced by a copy of itself (new inode): the next read checks nothing | equal bytes stay valid |
| 11 | The journal truncated at the held line: `evidence_corrupt`, twice | `sync()` still guards every read |
| 12 | Changing what `record()` and `switches()` returned changes no later read | the slot is private |
| 13 | Changing the dict given to `Qualification(...)` afterwards changes nothing; assigning `shipped` raises `AttributeError` | the shipped copy is fixed |
| 14 | Two objects on one store: one with a diverged shipped copy refuses, one with a longer shipped copy returns it, after the first object filled its slot | the slot belongs to one object |
| 15 | `switches(v)` equals `q.switches(record, build, v)` and `covers(v)` equals the scan, for versions below, at, between and above the entries, with another build's failing entry in the record; a bad version gives `invalid_input` | the method is the function |
| 16 | `Qualification` has no `hold` | the nit |

In `test_committed.py`: `pin`, `holds` and `pinned_value` directly, for rows 2, 4, 7, 8, 9, 10 and 11's cases
at the journal level, plus `ValueError` for an `op:` key.

In `test_qualification_service.Service`:
- **One assertion changes, and it is the only one in the package.** `test_o2_mode_reads_the_record_once_per_call`
  counts `record()` calls per `mode()` call and expects one. `mode()` no longer calls `record()`. Replace it with
  `test_o2_mode_checks_the_record_only_when_it_changed`: the same three situations (the fixture peer; a real Bridge
  with the daily refresh due; the same with the refresh gated), each a second `mode()` call with zero
  `validate_record` calls, and `transport.call_count == 1` as before. Then a newly held record is checked on the
  next `mode()` and not on the one after. Say so in the report.
- New, the steady-request test: after one warm-up request, a `chrome_read`, a click that asks and its
  `chrome_submit` run zero `validate_record` calls, and the action is dispatched once.
- New, source guard: no file under `control/aresos_control/` except `chrome/qualification.py` contains
  `qualification.record(`. It makes a wrong merge with #72 fail loudly.
- Every other test in the module passes unchanged, O1's two subtests included.

## Steps for the builder

One commit per step, pushed. Every commit before step 6's carries `[skip ci]`. Run with
`PYTHONDONTWRITEBYTECODE=1` from the repo root:
`PYTHONPATH=control:control/chrome_tests python3 -m unittest <modules>`.

1. **`_hold()`.** Rename, test 16. Run `test_qualification test_qualification_service`.
2. **The probe's assert** and its test. Run `test_latency`.
3. **The pin** in `committed.py` with its `test_committed.py` tests. Nothing calls it yet. Run `test_committed`.
4. **The slot** in `qualification.py`: `_current()`, `record()`, `switches()`, `covers()`, `own_switches`, the
   `shipped` property; tests 1 to 15. The callers still pass records, so every existing test passes unchanged,
   the O2 count included. Run `test_qualification test_qualification_service test_qualification_fixture test_engine`.
5. **The callers** in `adapter.py` and `engine.py`; the three `Service` test changes. Run step 4's modules plus
   `test_committed test_state_fixes test_bridge test_owner_confirm test_questions test_sites test_full_disk_reads`
   and `PYTHONPATH=control python3 control/generate.py --check`. If a session's permission check refuses
   `test_owner_confirm` by its name, say so and leave it to CI.
6. **The leg:** the cherry-pick and its two edits. Run `test_latency test_qualification_fixture`. Then run all
   modules named above a second time; a test that passes once and fails once is a failure. Push without
   `[skip ci]` and wait with `gh run watch <id> --exit-status --interval 60`.
7. **The sweep surface.** Locally, through `state_sweeps.isolated_flows` with `test_fault_surface.Writers` (as
   #93's builder did), the flows `qualification`, `delivery`, `readonly` and `drop` give the counts under "Which
   checks run when". In CI, the line `Chrome full writer surface` is not larger than in main's last Control
   Chrome run (#93 saw 2130, 2130 and 8488). A larger surface means a read gained a disk operation: stop and
   report.
8. **The report** (`reviews/79-read-cost/REPORT.md`, AGENTS.md's format; a Claude builder leaves the text in
   `PROGRESS.md`): the runs, the latency numbers, the local timings of a hit and a full check at 301 and 1,001
   entries, and the mutations it ran.

Left to CI: `test_storage`, `test_fault_surface`, `test_state_mutations`.

## Mutations for the reviewer

Each row was run on the scratch prototype, with scratch versions of the tests above, and failed the tests named.
Clear `__pycache__` and set `PYTHONDONTWRITEBYTECODE=1` between runs.

| Mutation | Must be caught by |
|---|---|
| Never invalidate: use the slot without `holds()` | tests 4, 5, 6, 7, 8, 9, 11; O1; both #93 tests; `test_image_upgrade_reconciles_older_held_history_and_can_fetch_again`; `test_each_failed_core_group_refuses_acting_with_reason_and_password_group_refuses_reads` |
| Key on the journal's signature or time only: `holds()` returns false when the signature changed | tests 2 and 10 (safe but slow; the latency leg is the backstop) |
| Key on the offset only: `holds()` never compares bytes | tests 7, 8, 9 |
| Compare the line's length only | tests 7, 8, 9 |
| Skip the rollback check on a hit, the dangerous way: fill the slot before `validate_record` and the reconcile | test 5 (the second read), test 7, O1 |
| No reconcile at all: the held record is the record | tests 5, 6, 7, 9, 14; O1; `test_fixture_records_meet_the_rollback_refusal_on_a_shipped_copy_with_history` |
| One slot for every object on the store (on the store, the projection or a module) | test 14; `test_image_upgrade_reconciles_older_held_history_and_can_fetch_again` |
| `record()` hands out the slot's record | test 12 |
| `pinned_value` without the hash check | test 8 |
| `holds()` never stores the new signature | test 3 |
| No slot: a full check on every read | tests 1, 2, 3, 10; the new O2 test; the steady-request test; the latency leg |
| `own` from the held record, not the reconciled one | test 6; O1's first subtest |
| `own` holds every build's entries | test 15; `test_installed_build_id_is_used_and_shared_code_new_build_pass_cannot_enable_old_build` |
| `covers()` always false, or always true | test 15; `test_runtime_connection_refresh_for_uncovered_version_once_and_daily_caller`; `test_failed_forced_refresh_for_an_uncovered_version_is_attempted_once_per_connection` |
| `mode()` asks `switches()` before `maintenance()` | both #93 tests |
| `__init__` keeps the given shipped dict | test 13 |
| `refresh()` holds the fetched JSON without `verified()` (RECHECK-1's M2) | `test_o2_refresh_says_whether_the_held_record_may_have_changed`; `test_bad_signature_rollback_malformed_and_oversized_downloads_keep_held` and two more `Delivery` tests |
| The probe's assert removed, or asked of a new connection | the new `MainFixStorageStages` test |
| A caller reads `qualification.record()` again (`pending_state()` or the notice, as a wrong merge would leave it) | the source guard; the steady-request test |

## Must not change

- **Replies.** Every code and text: `qualification_failed`, `qualification_rollback`, `qualification_invalid`,
  `evidence_corrupt`, `chrome_unavailable`, the version notice, the three fetch-result sentences.
- **Qualification and rollback semantics.** `validate_record`, `append_only`, the module `switches()` for every
  input, the direction of the reconcile, `verified()` (verifier, then append-only on the reconciled record),
  `accept()`'s signature and result, `refresh()`'s gate, return value and texts, one forced refresh per connection
  and version.
- **Storage.** No new write, journal record, key or file. `Projection.get()`, `sync()` and `record_cache` as they
  are. The fault sweep's surface not larger.
- **Latency.** The files listed under "The proof".
- **Instructions.** Chrome's server instructions are at 4,093 of Claude Code's 4,096 characters. The build adds no
  instruction or tool text: no change to `control/aresos_control/definitions.py`,
  `control/aresos_control/chrome/definitions.py`, `control/generated/` or `docs/control/TOOLS.md`.
  `generate.py --check` and `test_fixes_b_server_instructions_fit_the_native_cli_limit` pass.
- **Data.** `control/chrome/qualification.json` is not touched. The tree gets a new build hash, as with every
  product change; the data branch qualifies it as usual.
- **Tests.** None deleted or weakened. One assertion is replaced, named above.

## Overlap with PR #72 (package 28, `pkg/28-chrome`, in flight)

Checked with `git diff origin/main...origin/pkg/28-chrome` at `e3013438`.

| File | #72 | This build | Result |
|---|---|---|---|
| `control/aresos_control/chrome/adapter.py` | re-indents `pending_state()` under a `with`; adds code after `__init__`; adds imports around line 20 | changes `mode()`, `maintenance()` and one line in `pending_state()` | **conflict in `pending_state()`**, one line. Take #72's block with `mode=self.qualification.switches(self.bridge.version)`. `mode()` and `maintenance()` merge cleanly (four unchanged lines lie between them and #72's hunk) |
| the same file, line 20 | `from .qualification import Qualification, switches` sits between two lines #72 adds | leave the line alone; `switches` stays imported and unused | no conflict. Any later change to the file drops the name |
| `control/aresos_control/engine.py` | re-indents `request()`'s body under `with ... call_time(request):` | changes the two notice lines | **conflict**, two lines. Take #72's block; drop the local `switches` import; the notice line becomes `notice = chrome.qualification.switches(chrome.bridge.version)['notice']` |
| `control/chrome/ci/service.py` | changes the end of `request()` | the cherry-pick changes lines 17 to 30 and adds two lines near 59 | merges cleanly |
| `control/chrome/ci/latency-pair.sh` | rewritten (a function, an `efficiency` mode) | untouched | no text conflict. Two hidden ones are handled under "The proof" |
| `latency-profile.py`, `test_latency.py`, `qualification_fixture.py`, `qualification.py`, `committed.py`, `test_qualification*.py`, `test_committed.py` | untouched | changed | none |

**Sequence.** Build now, on `main`. The change is small, and Codex is available until 2026-11-21. #72 then merges
`main` and resolves the two conflicts above; the source guard fails if a resolution keeps `qualification.record()`.
The lead tells the package 28 session when this merges. If #72 merges first, the builder merges `main` and makes
the same two edits inside #72's blocks; #72 adds no other reader of the record.

## Judgment calls for the lead

1. **When the bytes are compared.** Chosen: after every journal change. Stronger: on every read, which also catches
   a rewrite that keeps inode, size and time. Cost of the stronger form: a journal open per read, 0.04 ms at 301
   entries, and a larger fault sweep (`drop`: 333 to 469 pair cases; `qualification`, `delivery` and `readonly`
   unchanged; the others not tried). Changing later is one line in `holds()` and tests 3 and 9.
2. **`maintenance()` returns nothing, and the O2 count test is replaced.** The alternative keeps the returned record
   and pays a copy of the whole record per `mode()` call.
3. **`record()` always returns a private copy.**
4. **Build before #72 merges** (above).
5. **Builder and review.** Builder: Codex `gpt-6.1-sol`; the steps name every line and test. Review: a fresh
   reviewer with the mutation table. This sits on the rollback gate, so a Fable reviewer is defensible.
6. **Branch.** The build can go on this branch, so brief, build and proof reach `main` in one PR, as the restore
   lock follow-ups did.

**Questions for the owner:** none. These are technical calls, and nothing the owner sees changes.

## Rules

- Worktree `~/AresOS-read-cost`, branch `briefs/79-read-cost`. Never merge, never push to `main`, never force-push,
  never `--no-verify`. Follow `AGENTS.md`.
- Public repo: no personal data, repo-relative paths only.
- Do not run `rpm-ostree`, `bootc`, `ostree` or `os/tests`' owner modules (an install hold is active). Mount
  nothing. No sudo. Stop processes only by PID. Control's own tests, `test_owner_confirm` included, are in-process
  and fine.
- Do not dispatch workflows. The PR's pushes start Control Chrome and Control Chrome qualification.
- `gh` polls with `--interval 60`. On HTTP 403, wait for the reset and try once.
