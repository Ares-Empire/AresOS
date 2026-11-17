# 79-read-cost: progress

Empire brief 301. Lead: `linux-tools`. Brief: `briefs/79-read-cost.md`.

## Status (2026-11-17)

**Brief reviewed (NOT READY); the lead's calls below; next: the brief's revision.** No product code has changed.

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

**Next:** a revision of the brief (Codex `gpt-6.1-sol` xhigh), then a short recheck of the revision.

## What the brief decides

- The qualification record is checked in full once per committed journal line, and the result is kept in one slot
  per `Qualification` object. The key is the line's offset and exact bytes. The bytes are compared with the disk
  again whenever the journal's inode, size or modification time changed.
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

1. Brief review (a fresh reviewer).
2. The lead's calls: the six under "Judgment calls for the lead".
3. The build, steps 1 to 8 of the brief.
4. A fresh review with the mutation table.
