# 79-read-cost: progress

Empire brief 301. Lead: `linux-tools`. Brief: `briefs/79-read-cost.md`.

**Status: Build part 1 done; next: steps 6 to 8**

## Build part 1 (steps 1 to 5)

Codex `gpt-6.1-sol`, 2026-11-17. Started at `16b7ba68` on `briefs/79-read-cost`; draft PR
[#98](https://github.com/Ares-Empire/AresOS/pull/98) remains open and draft. Read AGENTS, the entire READY brief,
both brief reviews, the lead's calls below, DESIGN, WORKFLOW, REVIEW and the existing implementation/tests.
`git fetch origin` was the first command. `origin/main` is now `26425160`, past the brief's `d0b91522`, but
`git diff d0b91522..origin/main` has no changes in any file touched by steps 1 to 5. Main was not merged.

### Done (one commit per step)

All five commits carry `[skip ci]`, end with `Built-by: gpt-6.1-sol`, and were normally pushed immediately after
that step's checks. No force push, merge, workflow dispatch or instruction-text change.

| Step | Commit | Built |
|---|---|---|
| 1 | `f16546c9` | Renamed `hold()` and its two callers to `_hold()`; test 16 rejects the public name. |
| 2 | `7fb283e0` | The latency probe asserts `normal` locking on the store's own connection. The new test refuses `EXCLUSIVE`, then installs with `NORMAL`; the existing real-Store test passes. |
| 3 | `a8babcfa` | `Projection.pin`, `holds`, `pinned_value`; exact bytes on every held-line comparison, without a stat shortcut. Nine direct pin tests include unchanged-signature rewrites, hash refusals, replacements, truncation and merged-key refusals. |
| 4 | `042be077` | Per-Qualification slot, validation/reconciliation before filling it, private build entries, `switches`/`covers`, shared `own_switches`, deep-copying `record` and `shipped`, private constructor baseline. Tests 1 to 15 include immediate unchanged-signature rollback refusal and nested getter mutations before/after invalidation. |
| 5 | `bad2dc77` | Adapter and engine callers use the methods; maintenance refreshes before mode reads switches. Replaced O2's record-call count with full-check counts; added steady-request and source-guard tests. |

### Local runs

Every unittest command below ran from the repo root with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest` followed by the listed
modules. Every run exited 0, printed `OK`, and skipped no tests.

| Step | Modules | Output |
|---|---|---|
| 1 | `test_qualification test_qualification_service` | `Ran 54 tests in 7.055s` / `OK` |
| 2 | `test_latency` | `Ran 41 tests in 5.089s` / `OK` |
| 3 | `test_committed` | `Ran 24 tests in 4.177s` / `OK` |
| 4 | `test_qualification test_qualification_service test_qualification_fixture test_engine` | `Ran 109 tests in 19.113s` / `OK`; all existing assertions, including O2's original count, still unchanged at this step. |
| 5 | `test_qualification test_qualification_service test_qualification_fixture test_engine test_committed test_state_fixes test_bridge test_owner_confirm test_questions test_sites test_full_disk_reads` | `Ran 246 tests in 145.639s` / `OK` |

The final step-5 module counts, in the order above: **47, 24, 8, 32, 24, 21, 14, 15, 34, 17, 10**.
`test_owner_confirm` ran all 15 tests; no permission refusal or socket-path failure. O1's two subtests and both
#93 refresh regressions pass unchanged. The only replaced existing test is the brief-authorized O2 count test:
the new test checks zero validations on the second mode call for the fixture peer, due daily refresh and gated
refresh, retains `transport.call_count == 1`, then checks one validation for a newly committed record and zero
on its next read. The steady read/click/submit test checks zero validations and one dispatch.

The qualification suites printed `ResourceWarning` messages while cleaning up synthetic HTTP-error fixtures.
`test_latency` also printed its expected synthetic background-maintenance failure/storage diagnostics; no run
failed. These fixture messages are not a live network or disk failure.

Also ran:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control python3 control/generate.py --check`: **Generated artifacts match definitions**, exit 0.
- `git diff --check`: clean at each commit and on the completed code.
- An AST comparison against `16b7ba68`: `Projection.get` and `sync`, and qualification's `version`, `validate_record`, `append_only`, `verified` are unchanged. The existing record-cache code remains unchanged.
- Byte comparisons against `16b7ba68`: all five protected latency files, both definitions files, generated artifacts, `docs/control/TOOLS.md` and shipped `qualification.json` unchanged.
- Direct instruction-length check: **Chrome server instruction characters: 4093**. The existing native CLI bound test also passed in `test_questions`.
- `gh pr view 98 --json state,isDraft,headRefName,headRefOid,url`: OPEN, draft, branch `briefs/79-read-cost`, code head `bad2dc77`.

### Mutations run after step 5

Ran `PYTHONDONTWRITEBYTECODE=1 python3 .work/79-read-cost/mutations.py`. The runner copied `control/` into
`.work/rc/`, changed only that scratch copy, cleared its `__pycache__` between runs, and set
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests` for each subprocess. Each subprocess loaded
the named tests with unittest, ran them and recorded both their identities and results. No mutation was committed.

Positive baseline: **28 selected catching tests, OK, no skips**. All **20 applicable table rows**, including
alternatives, were exercised: **23 mutations, 58 target-test executions, zero uncaught targets**. Each mutated
process exited 1 and every selected named target failed or raised from the changed behavior. Numbers below
refer to `test_qualification.Slot.test_XX_*`, matching the brief. Other names are from Service unless qualified.

| Mutation | Catching tests actually run | Result |
|---|---|---|
| Never invalidate | 4, 5, 6, 7, 8, 9, 11; O1; both #93 tests; Delivery image-upgrade test; each-failed-core-group test | All 12 targets caught it. |
| Invalidate on journal signature | 2, 10 | Both caught it. |
| Offset only | 7, 8, 9 | All three caught it. |
| Line length only | 7, 8, 9 | All three caught it. |
| Restore unchanged-stat shortcut | 3, 9 | Both caught it, with no intervening write/cache eviction in 9. |
| Fill slot before validation/reconciliation | 5, 7 | Both caught it on repeated reads. |
| No reconciliation | 5, 6, 7, 9, 14; O1; ShippedHistory fixture rollback-refusal test | All seven caught it. |
| Share slot on store | 14; Delivery image-upgrade test | Both caught it. |
| Return slot record directly | 12 | Caught: leaked nested adapter mutation caused `KeyError` on the next switches read. |
| Omit pinned-value hash check | 8 | Caught it. |
| No slot; always fully check | 1, 2, 10; new O2; steady request | All five caught it. |
| Own entries from held record | 6; O1 | Both caught it. |
| Own entries from every build | 15; installed-build-id test | Both caught it. |
| `covers()` always false | 15 | Caught it. |
| `covers()` always true | 15 | Caught it. |
| Read switches before maintenance | Both #93 tests | Both caught it. |
| Retain constructor argument | 13 | Caught: the subsequent read raised `qualification_rollback` after the argument mutation. |
| Public getter exposes `_shipped` | 13 | Caught it. |
| Refresh holds fetched JSON without `verified()` | refresh-written/result test; Delivery bad-signature/rollback/malformed/oversized test | Both caught it. |
| Remove probe assert | New exclusive-lock probe test | Caught it. |
| Ask locking mode of a new connection | New exclusive-lock probe test | Caught it. |
| Restore record caller in pending state | Source guard; steady request | Both caught it. |
| Restore record caller in version notice | Source guard; steady request | Both caught it. |

The scratch product files were restored after the mutations, then `.work/rc/` was deleted. The uncommitted
runner, sanitized logs and machine-readable results remain under `.work/79-read-cost/` for the lead. No files
over **500 MB** remain in `.work/` (checked recursively; none over 500 MiB either).

### Left, in order

1. **Step 6:** restore the 300-entry latency leg and its two specified edits; run its checks and the required second module pass, then push without `[skip ci]` and wait for both latency jobs.
2. **Step 7:** verify and record the seven local sweep counts and CI aggregate beside main.
3. **Step 8:** write REPORT.md with latency artifacts, per-phase comparisons, 301/1,001-entry hit/full-check timings and mutation evidence.
4. **Fresh `gpt-6-astra` xhigh review**, including rollback mutations and the unchanged-signature case.

### What the code doesn't show

This part proves the specified local behavior and mutation sensitivity. It has not restored or measured the
300-entry latency leg, run CI, measured real-browser latency, or verified the enlarged fault surface. In
particular it makes no constant-time claim: byte comparisons scale with line size, `record()` copies the
record, and switches process this build's entries. No human game check or screenshot applies to these
browser-free control changes. No Gradle, boot tool, OS owner test, mount or system installation was run.

### JUDGMENT-CALLs

None added. Implemented the lead's six decisions below, including every-read byte comparison, private copies,
maintenance returning no record and replacing only O2's count assertion.

### PLAN-GAPs

None encountered. As explicitly staged by this run's instruction, REPORT.md and steps 6 to 8 remain for the
next run; the build evidence for part 1 is recorded here.

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

## Remaining work

The current sequence is in **Build part 1 (steps 1 to 5)** above: steps 6, 7, 8, then the fresh astra xhigh review.
