Codex gpt-6-astra, 2026-11-17. Fresh reviewer, not the builder. Reviewed PR #98 at `6d3aaff4`, code head `48dcb513`, against `d0b91522`.

I read AGENTS.md, the full brief, both brief reviews, PROGRESS, REPORT and its records, DESIGN, REVIEW, the complete control diff, and the relevant implementation, tests, storage, daemon and fault-injection code.

I ran the following in disposable scratch copies, with bytecode disabled:

```text
PYTHONPATH=control:control/chrome_tests python3 -m unittest \
  test_qualification test_qualification_service test_qualification_fixture \
  test_engine test_latency test_committed test_state_fixes test_bridge \
  test_owner_confirm test_questions test_sites test_full_disk_reads
```

- **Twice:** 290 tests in 35.963s and 36.806s. Both printed `FAILED (failures=1, errors=24)`: this sandbox denies socket sends/binds in `test_bridge` and `test_owner_confirm`. Running those two unchanged modules from `d0b91522` reproduced the **same failure/error identities and counts**.
- The remaining ten modules, separately twice: **261 tests, OK**, in 30.356s and 30.324s.
- `test_latency test_qualification_fixture`: **52 tests, OK**.
- `test_state_mutations`: **1 test, OK; all 24 mutations killed**.
- `PYTHONPATH=control python3 control/generate.py --check`: **Generated artifacts match definitions**.
- Four additional scratch tests covering warm/cold read failures, malformed journal bytes and mutation of `accept()`’s return value: **OK**.
- Protected-file/AST comparisons, original-leg replay, instruction length, CI artifact/log comparisons, and scratch three-way merge checks against current PR #72 head `35193bd9`.

Only scratch files were written. No commit or push. Tracked status is clean; the pre-existing untracked `reviews/79-read-cost/REVIEW-1.md` remains untouched. No files over 500 MB remain in `.work/`.

Mutation results follow. Numbered tests refer to `test_qualification.Slot.test_01_*` through `test_15_*`; O1, O2 and “both #93 tests” refer to the Service tests named in the brief. I cleared bytecode caches between mutations. The positive baseline passed all **34 selected tests**.

| Mutation | Named catching tests exercised | My result | Builder |
|---|---|---|---|
| Never invalidate | 4–9, 11; O1; both #93 tests; image-upgrade Delivery; each-failed-core-group Service | **Killed by every target** | Killed |
| Invalidate on journal signature/time | 2, 10 | **Killed** | Killed |
| Offset only | 7, 8, 9 | **Killed** | Killed |
| Line length only | 7, 8, 9 | **Killed** | Killed |
| Restore unchanged-stat shortcut | 3, 9 | **Killed** | Killed |
| Fill slot before validation/reconciliation | 5, 7, O1 | **Killed** | Killed; builder omitted O1 |
| No reconciliation | 5, 6, 7, 9, 14; O1; fixture rollback-refusal test | **Killed** | Killed |
| Share slot across objects | 14; image-upgrade Delivery | **Killed** | Killed |
| Return slot record directly | 12 | **Killed** | Killed |
| Omit pinned-value hash check | 8 | **Killed** | Killed |
| No slot; full check every time | 1, 2, 10; new O2; steady-request test | **Killed** | Killed |
| Build `own` from held history | 6; O1 | **Killed** | Killed |
| Include every build in `own` | 15; installed-build-id Service test | **Killed** | Killed |
| `covers()` always false / always true | 15; both named refresh Service tests | **Both killed**; one individual target survives false, discussed below | Both killed by 15 |
| Read switches before maintenance | Both #93 tests | **Killed** | Killed |
| Retain constructor argument | 13 | **Killed** | Killed |
| Getter returns `self._shipped` | 13 | **Killed** | Killed |
| Refresh accepts JSON without `verified()` | Refresh-result Service test; bad-signature/rollback Delivery; daily-fetch Delivery; rate-limit/error Delivery | **Killed by all four** | Killed by first two |
| Remove locking assertion / query new connection | Exclusive-lock `MainFixStorageStages` test | **Both killed** | Both killed |
| Restore record caller in pending state / notice | Source guard; steady-request test | **Both killed** | Both killed |
| Remove efficiency exclusion | Named `RealisticRecord` test | **Killed** | Killed |
| Remove realistic history | Named `RealisticRecord` test | **Killed** | Killed |
| Retargeted S1 reads SQLite instead of pinned evidence | `test_s1_readable_policy_rollback_cannot_hide_committed_qualification` | **Killed** | Killed |

All **26 variants** were killed across **68 target executions**. I reproduced all 23 variants and 58 targets in `part1-mutations.json`, without disagreement. The two leg mutations agree with `leg-mutations.json`; the complete state-mutation run agrees with `state-mutations.txt`. Results and individual logs are under `.work/review-1/mutations/` (the reviewer's scratch, not committed).

1. **NIT — Clarify the catching-test mapping for constant-false `covers()`.**  
   [briefs/79-read-cost.md:343](../../briefs/79-read-cost.md#L343).

   `test_failed_forced_refresh_for_an_uncovered_version_is_attempted_once_per_connection` survives `covers() → False`: its version is already uncovered, so false is the correct answer throughout that scenario. Test 15 and `test_runtime_connection_refresh_for_uncovered_version_once_and_daily_caller` both kill this variant. Constant true is killed by all three.

   Clarify which tests catch each alternative. This is a precision issue in the mutation table, not a missing product safeguard; the builder’s recorded results are accurate.

No BLOCKER or SHOULD-FIX findings.

The implementation follows the required design. [committed.py:183](../../control/aresos_control/chrome/committed.py#L183) calls `sync()` and compares the exact pinned line on every cached held-record read, without a stat shortcut. The unchanged-signature regression preserves inode, size and mtime, recomputes hashes and fences, performs no intervening write, and repeatedly gets `qualification_rollback` through all three readers. Restoring the shortcut makes it fail.

[qualification.py:141](../../control/aresos_control/chrome/qualification.py#L141) publishes the slot only after successful parsing, hash checking, validation and reconciliation. Failed checks cannot authorize the previous slot. Constructor input, `shipped`, `record()` and returned switches cannot mutate the private baseline or cached entries. `_hold()` has the intended two verified callers; the locking assertion queries the store’s own connection.

The protected behavior checks passed:

- All **18 protected files** are byte-identical, including ceilings, sample counts, pair script, reference, summary/checker, definitions, generated files, tool documentation and shipped qualification data.
- `Projection.get()`, `sync()`, its cache initialization, `validate_record`, `append_only` and `verified()` have unchanged ASTs. Replies, refresh-result sentences and approval boundaries are preserved.
- Chrome instructions remain **4,093 characters**; the existing bound test passes.
- Replaying `e2e4eedc` onto the pre-leg tree leaves exactly the brief’s two adaptations: efficiency exclusion with its test, and the revision-variable regex.
- S1 still substitutes stale SQLite state for committed journal evidence. Its catching regression and the mutation harness’s assertions are unchanged; the substituted implementation fails the rollback regression.

The final latency evidence matches REPORT, retained artifacts and freshly fetched hosted logs exactly. Both profiles pass all six calls in every phase, with **60 current / 20 historical samples**, unchanged **0/2/4/10** sync counts and runner factors below 1. These are the reported current median/p95 values, in milliseconds:

| Profile / history | Read — ceiling 35/60 | Asking click — ceiling 60/100 |
|---|---:|---:|
| Plain / fresh | 8.873 / 10.131 | 13.323 / 14.814 |
| Plain / 1000 | 11.671 / 12.646 | 16.462 / 17.436 |
| Plain / 4000 | 20.137 / 21.402 | 26.311 / 27.729 |
| Audit / fresh | 8.142 / 10.090 | 11.659 / 12.434 |
| Audit / 1000 | 9.593 / 10.563 | 14.758 / 15.954 |
| Audit / 4000 | 19.612 / 20.585 | 25.280 / 26.576 |

Main’s comparison measurements also match its hosted logs. Plain/current confirms **300 shipped / 301 held entries**; audit/current and both historical legs confirm **0 / 1**. All six workflows on `48dcb513` are successful. I inspected this hosted evidence; I did not rerun browser latency locally.

The writer inventory retains all **19 flows**. Single and persistent counts remain **2130/2130**; cleanup pairs grow **8488 → 9434**. The complete increase is:

- `drop`: +136
- `trusted`: +290
- `stopped_submit`: +240
- `compose_reask`: +136
- `compose_stop`: +144

Thus growth extends beyond the seven locally selected flows, within the brief’s explicit allowance for aggregate growth. The unchanged injector counts additional journal-reader closes as cleanup opportunities. No flow or injection-class count shrank, and no sweep assertion changed. Hosted logs verify the full inventory; I did not repeat the exhaustive sweep locally.

Merging #98 first **does not leave #72 conflict-free**. Scratch three-way merges against `35193bd9` reproduce exactly one conflict region in each of [adapter.py](../../control/aresos_control/chrome/adapter.py) and [engine.py](../../control/aresos_control/engine.py). Preserve #72’s timing/context-manager blocks and use this PR’s `qualification.switches(...)` calls inside them; remove the engine’s local module-function import. `service.py` merges cleanly. The efficiency exclusion and variable regex address the harness interactions. The combined result still requires testing after resolution.

The supported service has one selector thread; the engine and adapter read the same per-object slot sequentially. The CI bootstrap also serves through that daemon. A hypothetical shared instance used concurrently by two threads is **not thread-safe**, nor is the existing Store/Projection designed for that use. No such path was introduced. Cooperating processes are excluded by the journal lock; different Qualification objects retain separate slots.

Security: I found no new route to accept stale, divergent or hash-corrupt qualification evidence, bypass verification, or widen Chrome actions without the owner’s approval. Exact-byte checks strengthen the specified rewrite detection. Existing limits remain: this does not revalidate the entire consumed journal prefix after arbitrary external replacement, and it is not synchronization against hostile concurrent writers.

SAFE