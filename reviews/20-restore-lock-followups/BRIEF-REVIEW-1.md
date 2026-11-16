# Brief review 1: 20-restore-lock-followups (`c0d88bbc`)

Reviewer: a fresh Claude agent on Opus 5.5, 2026-11-16, read-only. It did not write the brief or its findings.

**Verdict:** the brief's three conclusions hold against the code. In each item the store is right and the model is
wrong, and every line reference and every count I could check is correct. Nothing is blocking. Five should-fix
items make the brief harder to misread. One closes a premise that could later make the oracle blind (S1). Four give
the builder and the second checker exact definitions instead of a guess (S2–S5). All five are text changes to the
brief, and none needs new investigation.

## What I read and ran

- **Read:** `AGENTS.md`, `docs/REVIEW.md`, `briefs/20-restore-lock.md`, `reviews/20-restore-lock/REPORT.md` and
  `REVIEW-REPIN-3.md`, `docs/control/TOOLS-HANDOFF.md` ("Restore lock merged"), the brief, `PROGRESS.md`,
  `repro.py`; the code in `storage.py`, `engine.py`, `records.py`, `driver.py`, `compare.py`, `model.py`
  (`expected`, `permitted_status`, `request_state`, `hold_facts`), `perturb.py`, `storage_faults.py`,
  `test_owner_state_sweep.py` (`OwnerScenario`, `exercise`, the sweep test), `owner_state_cases.py`,
  `control/README.md:169-182`, `FORMAT.md`.
- **`repro.py`:** `PYTHONDONTWRITEBYTECODE=1 python3 reviews/20-restore-lock-followups/repro.py`, with `TMPDIR` set
  to my scratch directory. The script reads only repo files. Its output is identical, line for line, to
  `PROGRESS.md` §1, and it shows what the brief says:
  - item 1: in both modes the store keeps its lock with `write_failed` set. The decoder says locked when the marker
    was rolled back and unlocked when the marker's bytes stayed. Both are unlocked after a restart.
  - item 2: `aresos log` is refused with `restore_required`, and its reply envelope says locked. The page the oracle
    reads has no lock field.
  - item 3: an ordinary write fails at its marker. The decoder says locked while the store is not locked, and the
    write is finished at restart.
  - `repro.py` stands in for the sweep's persistent mode by failing only the marker sync and its truncation, not
    every later disk call. `PROGRESS.md` §2 used the sweep's own `exercise` for that. Good enough for a repro.
- **The capture's lists:** `gh run download 43722918063` (read-only, 61 artifacts) into an empty scratch directory.
  - My own script (`python3 -I`) reads the 53 `owner-gaps-*.json.gz` one at a time and merges them. Peak memory was
    0.53 GB.
  - The result: **2,622,072 keys, no conflicting shared keys**, the pin's count. I then counted the classes below
    from that merged list.
- **Not run:**
  - No `test_owner_*` module. The install hold applies to them (see S5), and the local sample and the prototype both
    import `test_owner_state_sweep`. I checked the sample's predictions only against the capture's keys for the
    sample cases.
  - No workflow dispatch, container, root, or rpm-ostree/bootc/ostree command.

## 1. The code claims, checked

Every reference is right:

| Brief | Code | Check |
|---|---|---|
| last marker sync, from `_finish` | `storage.py:562` `os.fsync`, `:597` `_append({"commit"…})` | ✓ |
| never reaches `self.locked = False` | `storage.py:940-942` | ✓ the final `write` raises first |
| keeps the lock, refuses writes until restart | `storage.py:565` `write_failed = True`, `:769-777` `ensure_writable` | ✓ the lock and the write latch both hold |
| single mode: marker rolled back | `storage.py:566-567` | ✓ |
| decoder's lock | `records.py:202-203` | ✓ |
| startup finishes a staged confirm | `storage.py:235-240` (`_pending_event`, `:448-458`) | ✓ for single mode and for points 26–73. At `persistent/75` the marker is already committed, so startup has nothing to finish (`:208-212`). Either way the result is "unlocked, new generation", as the brief says. |
| startup finishes a head-ahead write | `storage.py:241-250` → `_replay` (`:460-477`) re-applies the event and appends the marker | ✓ |
| `control_log` refused under the lock | `engine.py:575-576` | ✓ |
| `control_log`'s data has no lock field | `engine.py:600-625` (`ordered_page` plus `notices`, `:96-111`) | ✓ |
| view lock read from the page | `compare.py:239-240`; stand-in page `compare.py:121` | ✓ |
| the three "differs" places | `records.py:79`, `records.py:203`, `perturb.py:484` | ✓ these are all of them (grep for `max(…committed`) |
| the driver's startup rule; the sweep's restart pokes | `driver.py:59`; `test_owner_state_sweep.py:227-228` | ✓ |
| `consistency_errors`; the term at `:81` | `records.py:71-82` | ✓ (the lock formula starts at `:78`) |
| store locks only when behind | `storage.py:208`, `README.md:176-178` | the head comparison is ✓. The store has two more lock terms; see nit N4. |

Every count I could check is exact:
- **Lock keys:** 31,438 keys end in `.restore-lock`.
- **Item 2:** 16,383 keys. That is 15,982 in `crash-locked` (6,375 single, 9,514 pair, 42 + 51 in the restore flow),
  plus 69 + 332 in the restore flow's live phases.
- **Item 1:** 26 keys at `restore/persistent/75/0` (16 lock views, 8 statuses, 2 holds) and 14 at
  `restore/single/75/76` (9, 4, 1), which gives 25 + 12 + 3.
- **Item 3:** 15,030 keys.
- **The other 2,605,649 keys:** this follows by arithmetic.
- **Local sample:** the sample cases hold 1,234 keys in the capture, and the 52 keys items 1 and 2 close (50 in
  `restore`, 2 in `cancel`) are there.
- **Census:** the head-ahead cases (H, defined in S2 below) are 483 cases (322 single, 161 persistent) plus 903 pair
  cases, which matches the census.

**One premise of "items 1 and 2 only close keys", confirmed.** The only keys where the store refuses `control_log`
with `restore_required` while the oracle expects an answer are the three `response.control_log.status` keys at the
two item-1 cases. So item 2's change creates no new `aresos log.restore-lock` gap once item 1 is in. That is why the
two items must ship in one commit, and the brief has them in one.

## 2. The owner's side

- **Item 1: right.** Both modes are one situation for him: his confirm failed on a full disk. Keeping the lock
  shows nothing stale, refuses every app call, and a restart ends both modes unlocked with the new generation.
  - Releasing the lock would gain nothing, because the write latch (`storage.py:774-777`) refuses every write until
    the restart anyway.
  - Releasing it would also mean trusting bytes whose sync failed.
- **Item 2: right.** The refusal carries `restore_required` both as its code and in its envelope. Answering the log
  would show the older database's audit as current.
- **Item 3: right, and "behind" cannot hide stale data.**
  - A confirm is needed only when the database is older than the journal's committed high-water mark. That is
    exactly "behind".
  - A head *ahead* means the database holds every committed write plus one whose record was already synced. The
    restart finishes that write (`storage.py:241-250`).
  - The hash term stays in place: `records.py:203`, `head[1] != expected_head`. A head that doesn't match its record
    is still locked.
  - A head past the last record has no record, so it is also locked. The store refuses that case outright
    (`evidence_mismatch`, `storage.py:206-207`).
  - The decoder cannot see one working-state term: a `restore_pending` set by an uncommitted head
    (`storage.py:208`). That only happens inside a confirm. While the service runs, item 1's rule covers it. After a
    restart, the replay commits that head, so the decoder sees the term again.
- **Item 3 also removes a blind spot.** Suppose a regression made startup lock on a head-ahead tail instead of
  finishing it. Today the "differs" decoder agrees with that broken store. With "behind", the oracle expects the
  store unlocked, so the regression shows up as a gap.

## 3. Findings

### Should-fix

**S1. Item 1's rule triggers on any fault in the confirm, not on a failed confirm. Its premise is observed, not
checked.**
- **Where:** brief :47-55, `PROGRESS.md` §5 ("a non-empty fault trace").
- **Why:** the rule says locked whenever a confirm on a locked store meets any injected fault.
  - Today that is right only because every such fault aborts the confirm before `storage.py:942`: 140 of 140 cases,
    and closes are never primary points (`test_owner_state_sweep.py:438`).
  - Suppose a later change tolerates a fault after the final marker, such as a read in `recover_intents` or in the
    reply's envelope. Suppose a bug in the same change answers `ok` but keeps the lock. The owner would see
    "restore confirmed" and still have every call refused.
  - The oracle would accept that silently: it expects locked, and nothing compares the confirm's `ok` against the
    lock.
- **Fix:** keep the model reading only the fault trace (the reply is never an input), but turn the premise into a
  harness check. In `exercise`, after `s.call()`: when the scripted call is `control_restore_confirm` with a
  locked precondition and `fault.failures` is non-empty, `assert not reply['ok']`, with a message saying that item
  1's rule must be revisited.
  - Add one mutation for it: the store answers the faulted confirm `ok`, and the harness check must fail.
  - Optionally, also add a mutation that drops the "locked precondition" term. Nothing in the brief catches that
    today.

**S2. The re-pin's item-3 class needs an operational definition and its own numbers.**
- **Where:** brief :122-135.
- **Why:** "cases where the old decoder said locked with the head ahead" cannot be computed from the ledgers. The
  checker cannot run the old decoder on CI's cases.
  - The class is also wider than the wording suggests. Item 3 changes the expectation before a crash, so alias
    numbers can shift in later keys of the same run. `PROGRESS.md` §5 saw 290 keys change by alias numbers alone.
    Those can include keys read after the restart in `crash-restart`, which the "replies built before a crash"
    wording seems to exclude.
  - "With items 1 and 2 alone, 2,605,649 stay byte for byte" holds only for the local sample after the first
    commit. The one capture contains all three items, and the brief gives no byte-for-byte number for it.
- **Fix:** define the class as follows. I measured these numbers on capture 43722918063.
  - **H** = the cases (flow/mode/point/cleanup) outside the `restore` flow whose pin has `passive.restore-lock` or
    `control_pending.restore-lock` with expected `True`, observed `False`, in `exhausted` or `live-restored`.
    - That is **1,386 cases** (322 single, 161 persistent, 903 pair) in 31 flows.
    - They hold **92,945 keys** today: 7,015 `exhausted`, 59,726 `live-restored`, 26,204 `crash-restart`, and none
      in `crash-locked`.
    - All 15,030 item-3 lock keys are at H, and all 1,374 cases with a `crash-restart` lock key are in H.
  - At H, any key may close, change or appear, in any phase.
  - Outside H and the 16,423 closing keys of items 1 and 2, **2,512,704 keys** (the 377 fixed keys included) stay
    byte for byte, and no key appears.
  - Use the same predicate for the first commit's local sample.

**S3. "Behind" is changed in three places but tested in one.**
- **Where:** brief :97-98 and :111-113.
- **Why:** the unit tests cover the decoder (`records.py:203`) only.
  - If `records.py:79` were left at `!=`, `consistency_errors` would report `unjustified-lock` at every H case.
    That would only show in a 2.5 h capture.
  - If `perturb.py:484` were left at `!=`, the alteration suite's coherent recompute would quietly disagree with
    the decoder, and nothing in the brief would catch it.
- **Fix:** either put the decoded-lock formula in one function in `records.py` and call it from all three places
  (cleaner: the brief already wants "one formula" for item 1's field), or add a head-ahead test for each place:
  - `consistency_errors` on a head-ahead record reports no `unjustified-lock`;
  - the perturbation recompute leaves that record unlocked.
  - Mutation for each test: `!=` restored in that one place.

**S4. No guard against drift from main.**
- **Where:** brief :131 ("drift from another merge").
- **Why:** the plan relies on "no production code changes". The branch is on `5d717142`. Main has moved since then
  (#83), but only `control/chrome/qualification.json` changed, which is harmless. The handoff, though, lists
  PRs #58, #69 and #72 bringing `engine.py` changes.
  - If main is merged before the capture, production changes can land inside H's "may change" class, where nothing
    can tell them from item 3.
- **Fix:** name the base. Before each dispatch, require that
  `git diff <base> HEAD -- control ':!control/owner_state_oracle' ':!control/tests' ':!control/mail_tests'` be empty.
  Merge main only after the proof run, or else capture again.

**S5. The `test_owner_*` hold versus the oracle's own test modules.**
- **Where:** brief "Rules"; `HANDOFF.md:59` (`linux-tools` holds `test_owner_*` until the lead's "done").
- **Why:** the builder's local checks are all named `test_owner_*`:
  - `control/tests/test_owner_state_oracle.py` (item 2 and item 3 tests);
  - `control/mail_tests/test_owner_state_sweep.py` (item 1 and item 3 sweep tests);
  - the local sample, which imports the sweep module.

  Read literally, the hold forbids all three. A builder must either stop or guess. I did not run them for that
  reason.
- **Fix:** add one line saying whether the `control/…/test_owner_state_*` modules are outside the hold. They never
  reach rpm-ostree; the hold's purpose is `os/tests/test_owner_*`. Also say what local run is required before the
  capture: the base oracle module, the touched Mail-suite modules, and the sample. The previous brief named its
  preflight driver; this one names none.

### Nits

- **N1. Where the rule reads the trace.**
  - The trace that already exists when the failed confirm's reply is captured belongs to the `scripted` entry. It
    is set at `test_owner_state_sweep.py:100-102`, before `observer(index, reply)` at `:103`.
  - The `Driver.observe` entry gets its trace only at `driver.py:355`, after the call.
  - Name the `scripted` entry and its `restore_precondition` (`:88`), so the builder doesn't repeat the "too late"
    first version that `PROGRESS.md` §5 describes.
- **N2. "Since it started" versus the latch package.**
  - The model already expects a healthy write after a failed one (the `G22-latch` gap). In the model's own terms,
    "the most recent scripted confirm on a locked store since the last restart met a fault" is therefore the
    consistent rule.
  - "Any confirm since start" would turn into false gaps once the latch package lets a second confirm succeed. Both
    rules pin the same keys today.
  - Whichever rule is chosen, the field must be assigned on every snapshot. A one-way `|=` on the cached record
    (`driver.py:56-59`) works only while the rule is monotonic until restart.
- **N3. Which pair cases, and which restarts.**
  - **Pair cases:** `restore/single/75` has three, at 76, 77 and 78, and only 76 carries keys today. Have the item 1
    sweep test check every pair case of the last point.
  - **Restarts:** say that `Driver.restarted()` replaces only `:227-228`. The `restart_` rebind at `:245` and the
    `_snapshot_key` pokes at `:366` and at `owner_state_cases.py:433` stay as they are. Moving `startup_sequence` in
    those places would change other keys.
- **N4. "The store locks only when the head is behind" is too strong** (brief :98).
  - The store has two more lock terms:
    - `restore_pending` in the working rows (`storage.py:208`);
    - an uncommitted record whose staged event is missing (`:209-212`, `:245-248`, `README.md:178-181`).
  - The oracle already models the second with its startup rule (`driver.py:59`). The first is covered as described
    in §2.
  - Say so, so a builder doesn't "fix" those terms too.
- **N5. Counting units.** "644 single-fault cases" means case × phase: 483 cases, of which the 161 persistent ones
  also have an `exhausted` phase. The table in `PROGRESS.md` §4 is clear about this; the brief's sentence (:95-96)
  is not.
- **N6. Clean-run point counts.** The ledger has none. They are in the sweep job logs, in the
  `Owner oracle flow=… points=…` lines (`test_owner_state_sweep.py:453`). Say that there.
- **N7. The rows left at H.**
  - After item 3 the model expects the committed rows at H, while the store shows the write it applied. Item 3
    therefore adds new pinned keys: `PROGRESS.md` §5 saw 107 count keys appear, plus changed row keys.
  - In the new `KNOWN-GAPS.md` section, name this as its own class, with its count and an owner for the decision,
    and leave it on the board. Otherwise it becomes the next unexplained "pre-existing" class.
- **N8. Where the mutations are recorded.** Either as `reviews/20-chrome/mutation-audit.py` probes (with a prefix)
  for base-suite tests, or ad hoc and written down for the Mail-suite tests, as package 20-restore-lock did.
- **N9. The "Cut line" paragraph** (brief :108-109) reads as an open choice, but the lead has already decided it
  (:19-22). Mark it "not taken".

### Note (outside this brief)

- **A blind spot that predates this brief.**
  - Suppose startup failed to finish a staged confirm (`storage.py:235-240`) at points 26–73. The bytes would still
    show the head behind, so the decoder says locked and agrees with the stuck store. The owner would be asked to
    confirm twice, and the oracle would not notice.
  - The oracle models only the opposite startup rule (an unprepared record locks).
  - A possible queue item; not needed here.

READY
