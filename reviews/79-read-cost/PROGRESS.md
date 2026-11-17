# 79-read-cost: progress

Empire brief 301. Lead: `linux-tools`. Brief: `briefs/79-read-cost.md`.

## Status (2026-11-17)

**Brief revised after BRIEF-REVIEW-1; next: a short recheck.** No product code has changed.

## The lead's calls after BRIEF-REVIEW-1 (2026-11-17)

`BRIEF-REVIEW-1.md` (Codex `gpt-6-astra`, high, on `bbbabdc6`): **NOT READY**: one blocker, one should-fix, one nit.
The lead's calls, with the reviewer's view taken in:

1. **When the bytes are compared: on every cached read** (changed from "after every journal change"). The review's
   blocker shows the stat shortcut loses a reread that today's code does by accident: after five other committed
   reads, today's `get()` cache has dropped the qualification parse and rereads the journal, so an in-place rewrite
   with size and mtime kept is refused as `qualification_rollback`; the proposed slot would still serve the old
   record. The rollback check must not get weaker, and the cost is one journal open per read (0.04 ms at 301
   entries). The larger fault sweep (`drop` 333 to 469 pair cases) is verification work, not a reason against it.
   Add the review's unchanged-signature regression, without waiting for another write (test 9 waits, so it misses it).
2. **`maintenance()` returns nothing; O2's count test is replaced:** agreed (the review agrees; the new-record check and
   the behavioural regressions stay).
3. **`record()` returns a private copy, and so does `shipped`** (review finding 2): the public getter returns a deep
   copy, internal code uses the private baseline; test 13 mutates nested values obtained through the getter and checks
   the results before and after the slot is invalidated; one more mutation exposes `_shipped` directly.
4. **Build before #72 merges:** agreed; check the combined result after the conflicts are resolved.
5. **Builder and review:** builder Codex `gpt-6.1-sol` xhigh. Review: a fresh Codex `gpt-6-astra` xhigh (Fable is
   closed this week past the release line), which runs the rollback mutations, the new unchanged-signature case
   included.
6. **Build on this branch:** agreed.

Also from the review: narrow the constant-time claim (nit 3), and say there are six calls, not seven.

**Next:** a short recheck of the revision below.

## Revision 1 (2026-11-17)

- **Outcome; Measured; The design:** require exact-byte comparison on every cached read, retaining offset plus
  bytes as the key; state the journal-open/pinned-line-read cost, remove the rollback-equivalence claim, label the
  old stat-shortcut timings and narrow the performance claim to removing repeated whole-history work.
- **What the slot holds; The proof (tests 3, 9 and 13); Steps for the builder; Mutations for the reviewer:** require
  the public `shipped` getter to deep-copy the private baseline; test nested getter mutations before and after slot
  invalidation, and a same-length, hash-valid rewrite with restored mtime and no subsequent write. Name the
  `return self._shipped` and restored-stat-shortcut mutations and their catching tests; remove the obsolete
  signature-update mutation and recheck all test references. The eight build steps keep their order.
- **Which checks run when; Must not change (Storage); step 7:** permit the read-related sweep growth, record the
  measured `drop` change (333 to 469 pair cases), and require new counts for all seven flows and the CI aggregate.
- **Judgment calls for the lead; Rules:** mark all six calls decided; name Codex `gpt-6.1-sol` xhigh as builder and a
  fresh Codex `gpt-6-astra` xhigh reviewer running the rollback mutations, the new case included. The install hold
  has ended; boot tools and `os/tests` owner modules remain forbidden because this build needs none and Codex runs
  no boot tools on the laptop. The latency proof and PR #72 overlap table stay unchanged.

Revision checks:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control python3 .work/79-read-cost/review_probe.py`: the real `Projection`
  and `Qualification`, with an in-memory journal and fixed inode/size/mtime, served the old record before cache
  eviction and raised `qualification_rollback` after five other committed reads. The stat shortcut passed while
  exact bytes differed. This confirms BRIEF-REVIEW-1's scenario; no product mutation or disk journal was used.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_policy test_qualification.Records`:
  **27 tests, OK**.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control python3 control/generate.py --check`:
  **Generated artifacts match definitions**.
- A read-only structural check passed: the latency proof and PR #72 overlap section match the starting brief;
  only Storage's sweep allowance changes under "Must not change"; eight build steps retain their order, with
  16 test rows, six decided calls and catching-test references for all 20 mutations. `git diff --check` passed.
  Files over 500 MiB left in `.work/`: none.

No disagreement with the review's findings. The revised implementation tests and mutations belong to the build
and fresh review; they were not implemented or run in this brief revision. No workflows were dispatched.

## What the brief decides

- The qualification record is checked in full once per committed journal line, and the result is kept in one slot
  per `Qualification` object. The key is the line's offset and exact bytes. The bytes are compared with the disk
  again on every cached read, even with unchanged inode, size and modification time.
- Hot callers ask `Qualification.switches(version)` and `covers(version)`; nothing passes the whole record around.
- `hold()` becomes `_hold()`. The latency probe asserts `PRAGMA locking_mode` is `normal`.
- Proof: `e2e4eedc`'s 300-entry plain latency leg comes back, with ceilings, sample counts, `latency-pair.sh` and
  `latency-reference.json` unchanged.

## How it was checked (brief writer, a Claude agent on Fable 5.2)

All on the laptop, on `main` `d0b91522` and on a scratch copy outside the repo. Nothing was dispatched.

- **Cost today**, timed with the fixture engine: the tables under "Measured" in the brief.
- **A scratch prototype** of the design (`committed.py`, `qualification.py`, `adapter.py`, `engine.py`), with
  `e2e4eedc` cherry-picked:
  - `test_qualification`, `test_qualification_service`, `test_qualification_fixture`, `test_engine`, `test_latency`,
    `test_committed`, `test_state_fixes`, `test_bridge`, `test_sites`, `test_questions`, `test_policy`,
    `test_full_disk_reads`, `test_publisher`, `test_build`, `test_restore_lock` and six small modules pass. The one
    failure is `test_o2_mode_reads_the_record_once_per_call` (`0 != 1`), which the brief replaces.
  - `test_owner_confirm`: 14 of 15 pass; the last fails with `AF_UNIX path too long`, from the scratch folder's
    long path. It fails the same way on the unchanged scratch copy.
  - Scratch versions of the brief's 16 unit tests, its three `Service` tests and the probe test pass.
  - Every mutation in the brief's table fails the tests named there.
  - The fault sweep's surface for `qualification`, `delivery`, `readonly`, `drop`, `allow`, `trusted` and
    `stopped_submit` equals `main`'s, flow by flow.
- **The variant that compares the bytes on every read** was prototyped too: `drop` went from 333 to 469 pair cases.
- **PR #72:** its diff against `main` at `e3013438`, hunk by hunk for the files this build touches.

The prototype and the scratch tests are not in the repo. The builder writes its own from the brief.

## Left, in order

1. A short recheck of Revision 1.
2. The build, steps 1 to 8 of the brief, by Codex `gpt-6.1-sol` xhigh.
3. A fresh Codex `gpt-6-astra` xhigh review with the mutation table, running the rollback mutations including the
   new unchanged-signature case.
