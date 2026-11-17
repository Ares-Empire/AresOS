# 79-read-cost: qualification record read cost

Codex `gpt-6.1-sol`, 2026-11-17. Empire brief 301; lead `linux-tools`.
Branch `briefs/79-read-cost`; draft [PR #98](https://github.com/Ares-Empire/AresOS/pull/98).

## Done

Steps 1 to 5 were built in `f16546c9`, `7fb283e0`, `a8babcfa`, `042be077`, `bad2dc77`, with
their evidence committed in `1beec6c7`. This run started there after `git fetch origin`.
Main had advanced from the brief's `d0b91522` to `26425160`; its diff contains no changes in
any file this build touches. A later fetch advanced it to `a2d9b6ee`, again with no
changes in this build's files. Main was not merged. Its latest Control Chrome run remained
`44093263185` when rechecked.

- `chrome/qualification.py`: private `_hold`, one object-local reconciled slot, private baseline
  and copies, `switches`/`covers`, and the shared switches core. Validation and reconciliation
  finish before filling the slot. `record()` still copies the complete record.
- `chrome/committed.py`: pins read the committed journal line from disk; every held-line cache
  use compares exact bytes, including when inode, size and mtime are unchanged. Failed reads
  do not authorize reuse. `get`, `sync` and the existing parse cache are unchanged.
- `chrome/adapter.py` and `engine.py`: hot callers read switches directly, after maintenance.
  The brief-authorized O2 count test is replaced; its three scenarios, refresh transport count,
  new-record validation and both #93 behavioral regressions remain covered.
- `chrome/ci/latency-profile.py`: refuses exclusive SQLite locking on the store's own connection.
- Step 6, `abe81184`: cherry-picked `e2e4eedc` with `-x` and added the two required edits.
  Plain/current measures 300 shipped entries and 301 held entries; efficiency probes keep one
  held entry. The pair-script assertion accepts either revision variable name. No ceiling,
  sample count, reference, pair script, summary or checker changed.
- CI correction, `48dcb513`: retargeted the existing S1 qualification removal mutation from the removed
  projection `get` call to `pinned_value`, substituting the same unsafe SQLite-cache read.
  Its catching regression and every assertion are unchanged. No product change was needed.
- Step 7, `aba7ca5a`, and step 8: recorded writer surfaces, latency evidence, local timings and mutations here
  and in [PROGRESS.md](PROGRESS.md). Evidence commits carry `[skip ci]` to avoid starting an
  additional code-test round; the tested code commits and run IDs are identified below.

## Verified

### Local tests

Commands ran from the repo root. Each unittest command used
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest`
followed by these modules. Every successful run printed `OK`, exited 0 and skipped no tests.

| Pass | Modules | Output |
|---|---|---|
| Part 1, step 1 | `test_qualification test_qualification_service` | 54 tests, 7.055s |
| Part 1, step 2 | `test_latency` | 41 tests, 5.089s |
| Part 1, step 3 | `test_committed` | 24 tests, 4.177s |
| Part 1, step 4 | `test_qualification test_qualification_service test_qualification_fixture test_engine` | 109 tests, 19.113s |
| Part 1, step 5 | `test_qualification test_qualification_service test_qualification_fixture test_engine test_committed test_state_fixes test_bridge test_owner_confirm test_questions test_sites test_full_disk_reads` | 246 tests, 145.639s |
| Part 2, step 6 | `test_latency test_qualification_fixture` | 52 tests, 8.906s |
| Part 2, second full module pass | `test_qualification test_qualification_service test_qualification_fixture test_engine test_latency test_committed test_state_fixes test_bridge test_owner_confirm test_questions test_sites test_full_disk_reads` | 290 tests, 129.449s |
| Part 2, CI mutation correction | `test_state_mutations` | 1 test, 69.073s; all 24 removal mutations caught |

The part-1 runs are recorded in [the handoff](PROGRESS.md#build-part-1-steps-1-to-5), not
claimed as rerun individually here. The required combined second pass ran here after restoring
the leg. `test_owner_confirm` ran all 15 tests in both passes. Synthetic HTTP fixture
`ResourceWarning`s and the latency tests' expected synthetic background/storage diagnostics
were printed; they did not fail the local runs.

Also ran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control python3 control/generate.py --check`:
`Generated artifacts match definitions`, exit 0. `git diff --check` passed. Byte comparisons
against `16b7ba68` confirmed all 18 protected latency, definition, generated, tool-document and
shipped-data files unchanged. Artifact consistency checks also matched build identities, fixture sizes,
all history phases, 60/20 samples, sync ranges, writer-surface sums and mutation results.
AST comparisons confirmed `Projection.get`/`sync` and qualification's
`version`, `validate_record`, `append_only`, `verified` unchanged. Chrome instructions remain
4,093 characters; the native CLI length test passed in `test_questions`.

Ran `bash .work/79-read-cost/part2/repo-privacy.sh` after staging the evidence files:
`No file holds a home path with a real user name.`, exit 0. This is the repository's privacy
workflow script with only its temporary-output path relocated under `.work/`.

### CI runs and latency

Both code pushes started the PR's normal workflows; every run below is attempt 1. Watched
Chrome, qualification and the final base/Mail/boundary runs with
`gh run watch <id> --exit-status --interval 60`. The final watchers exited 0; the two first
Chrome/qualification watchers exited 1. No workflow was dispatched and no selective or whole-run
rerun was used. **Round two is green across all six workflows; stopped after those two rounds.**

| Workflow | Round 1, `abe81184` | Round 2, `48dcb513` |
|---|---|---|
| Control Chrome | [44120119006](https://github.com/Ares-Empire/AresOS/actions/runs/44120119006) **FAIL** | [44121122119](https://github.com/Ares-Empire/AresOS/actions/runs/44121122119) **PASS** |
| Control Chrome qualification | [44120118648](https://github.com/Ares-Empire/AresOS/actions/runs/44120118648) **FAIL** | [44121121888](https://github.com/Ares-Empire/AresOS/actions/runs/44121121888) **PASS** |
| Control base | [44120118739](https://github.com/Ares-Empire/AresOS/actions/runs/44120118739) **CANCELLED** | [44121122010](https://github.com/Ares-Empire/AresOS/actions/runs/44121122010) **PASS** |
| Control boundary | [44120118046](https://github.com/Ares-Empire/AresOS/actions/runs/44120118046) **PASS** | [44121121873](https://github.com/Ares-Empire/AresOS/actions/runs/44121121873) **PASS** |
| Control Mail | [44120119804](https://github.com/Ares-Empire/AresOS/actions/runs/44120119804) **CANCELLED** | [44121121982](https://github.com/Ares-Empire/AresOS/actions/runs/44121121982) **PASS** |
| Repo privacy | [44120118501](https://github.com/Ares-Empire/AresOS/actions/runs/44120118501) **PASS** | [44121121943](https://github.com/Ares-Empire/AresOS/actions/runs/44121121943) **PASS** |

Round one failed because S1's removal mutation still searched for
`self.store.chrome_state.get('chrome:qualification'`, which the planned pin implementation
removed (`0 != 1`). The same anchor failed Chrome Python shard 2 and both qualification repeats.
Their aggregate/combine logs first reported every browser shard, all **999 word cases** and
native **group 12 PASS**, then refused to combine the failed Python shard. `48dcb513` retargets
the unsafe SQLite-read substitution to `projection.pinned_value(...)`, with the same rollback
regression and unchanged assertions. Final Chrome and both final qualification repeats pass.
The first base/Mail runs were cancelled by their configured concurrency policy when the correction
push replaced them; the final replacements passed. No unrelated flaky failure was encountered.
[ci-runs.json](records/ci-runs.json) retains each run's head, URL, event and conclusion.


Main's comparison is its latest successful Control Chrome run at the initial fetch:
[44093263185](https://github.com/Ares-Empire/AresOS/actions/runs/44093263185), scheduled on
`04aef030`, attempt 1. Both baseline latency jobs passed. The paired historical runtime remains
`ab7aba92`; current takes 60 samples per call/phase, historical takes 20 at the frozen reference's
positions. The unchanged ceilings are `read` 35/60 ms and `asking_click` 60/100 ms median/p95.
The gate scales ceilings by `max(1, runner_factor)`; raw factors are reported for every phase.

The table uses the final code round, Control Chrome `44121122119`, attempt 1, compared with
main `44093263185`. Each timing cell is **median / p95 in ms**. Both profiles passed all
18 call/phase checks, with no latency or sync failures; every final runner factor is below 1,
so all six call kinds meet the unchanged **base** ceilings, without a slowdown allowance.

| Profile | History | Runner factor main / build | read main ms | read build ms | asking_click main ms | asking_click build ms |
|---|---|---|---|---|---|---|
| plain | fresh | 0.815518 / 0.921082 | 7.972 / 9.227 | 8.873 / 10.131 | 11.084 / 11.662 | 13.323 / 14.814 |
| plain | history-1000 | 0.870545 / 0.941338 | 9.017 / 9.909 | 11.671 / 12.646 | 14.285 / 15.495 | 16.462 / 17.436 |
| plain | history-4000 | 0.852490 / 0.911306 | 19.313 / 20.343 | 20.137 / 21.402 | 24.924 / 26.526 | 26.311 / 27.729 |
| audit | fresh | 0.762568 / 0.811359 | 7.971 / 9.221 | 8.142 / 10.090 | 11.513 / 12.202 | 11.659 / 12.434 |
| audit | history-1000 | 0.928865 / 0.992341 | 8.914 / 9.579 | 9.593 / 10.563 | 14.532 / 15.231 | 14.758 / 15.954 |
| audit | history-4000 | 0.925459 / 0.996286 | 19.148 / 19.852 | 19.612 / 20.585 | 24.405 / 25.304 | 25.280 / 26.576 |

Exact gate measurements for all six call kinds, counts, runner factors and build identities are
in [latency.json](records/latency.json). Both profiles also passed in round one; that earlier
measurement is retained in [latency-round1.json](records/latency-round1.json). Both rounds
measure product build `a22c040ebb45ef7f2c0a3f9e897cd3e146f9b02e6884b61a64c6d495ef803fd4`,
on Chrome `157.0.8103.78`; the round-two code change affects only a test's mutation anchor.

The plain current artifact's `service.txt` prints exactly
`FIXTURE_QUALIFICATION {"shipped_entries": 300, "held_entries": 301}`. Audit/current and both
historical legs print zero shipped and one held entry. The historical control therefore
continues measuring the same one-entry workload as the frozen reference.

In every history phase and both final profiles, per-sample minimum and maximum are equal for
current and historical runtimes, for each of `journal_fsync` and `sqlite_commit`: `read` **0**,
`asking_click` **2**, `navigate`, `free_click`, `fill` **4**, `approval_to_done` **10**. No write
was added. Samples remain **60 current / 20 historical** for every call and phase.

### Writer surfaces

Local command:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 .work/79-read-cost/part2/sweep.py`.
The exact runner is retained as [writer-sweeps.py](records/writer-sweeps.py). It invokes
`state_sweeps.isolated_flows` with `test_fault_surface.Writers`, preserving single, persistent,
cleanup-pair, restored-space and restart verification. Main's comparison counts come from
run `44093263185`, Python shard 1; main was not rerun locally.

All seven local flows passed, exit 0, in **3,365.962s**. The selected total printed
`Selected writer surface {"single": 1165, "persistent": 1165, "pairs": 5833}`.
Counts below are **single / persistent / cleanup pairs**; main's selected total is
1,165 / 1,165 / 5,167. All 666 added selected cleanup-pair cases were exercised.

| Flow | Main | Local build | Added pairs |
|---|---|---|---|
| qualification | 54 / 54 / 98 | 54 / 54 / 98 | 0 |
| delivery | 109 / 109 / 259 | 109 / 109 / 259 | 0 |
| readonly | 52 / 52 / 202 | 52 / 52 / 202 | 0 |
| drop | 68 / 68 / 333 | 68 / 68 / 469 | 136 |
| allow | 52 / 52 / 202 | 52 / 52 / 202 | 0 |
| trusted | 437 / 437 / 2148 | 437 / 437 / 2438 | 290 |
| stopped_submit | 393 / 393 / 1925 | 393 / 393 / 2165 | 240 |

CI Control Chrome `44120119006`, Python shard 1, printed
`Chrome full writer surface {'single': 2130, 'persistent': 2130, 'pairs': 9434}`,
versus main `44093263185`'s **2,130 / 2,130 / 8,488**: **946 additional full-surface
cleanup pairs** verified. That shard ran **84 tests in 1,252.065s**, `OK`, including
`test_fault_surface` and `test_storage`. Its seven requested flow counts match the local
results exactly. Growth is the expected verification surface from the extra journal reads;
no new write or weakened assertion accounts for it.

The exact local output is in [local-writer-sweeps.txt](records/local-writer-sweeps.txt).
[writer-surfaces.json](records/writer-surfaces.json) records all nineteen hosted writer
flows, the aggregate and the seven local results with their run IDs.
Round two `44121122119` independently printed the same **2,130 / 2,130 / 9,434** full
surface and the same seven flow counts; that shard printed `Ran 84 tests in 1242.767s` / `OK`.
Both hosted runs' complete writer inventories are retained in the JSON.

### Local read cost

Ran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 .work/79-read-cost/part2/timings.py`.
The exact script and results are retained as [local-timings.py](records/local-timings.py) and
[local-timings.json](records/local-timings.json). Python 3.14.8 (`python3 --version`) on this
laptop; real disposable
`Store`, 300/1,000 synthetic earlier-build entries plus this build's entry, shipped prefix
reconciled with the held record; 101 samples for each row. Measurements call
`Qualification.switches(version)` after warming. A full check clears only the private slot
before the clock starts. Store writes, constructor validation, mock instrumentation and public
`record()` copying are outside the timed interval. A separate wrapped call confirmed zero
validations per hit and one per cold check. Timings ran before the fault sweep.

| Entries | Cache hit median/p95 ms | Full check median/p95 ms |
|---|---|---|
| 301 | 0.083045 / 0.094252 | 2.184075 / 2.699435 |
| 1,001 | 0.154594 / 0.177963 | 7.174058 / 7.684178 |

These are local qualification costs, not browser-request timings. Exact-line reads still scale
with byte length; switches still process this build's entries. No constant-time claim.

### Mutations actually run

Part 1 ran all 20 brief-table categories, including alternatives: **23 mutations, 58 selected
target executions, no uncaught targets**. Its positive baseline passed all 28 selected tests,
with no skips. [part1-mutations.json](records/part1-mutations.json) preserves test identities,
exit codes, failures/errors and empty `missed` lists. [PROGRESS.md](PROGRESS.md#mutations-run-after-step-5)
maps every mutation to its catching tests, including repeated rollback refusals, the immediate
unchanged-signature rewrite, premature slot filling, private getter leakage and the new probe.
They ran only in a disposable copy with bytecode disabled and caches cleared between mutations.

Here, [leg-mutations.json](records/leg-mutations.json) records a passing targeted baseline and
two caught mutations: omit the efficiency guard; remove realistic history. Each failed
`RealisticRecord.test_only_the_plain_leg_s_current_runtime_starts_from_several_hundred_entries`
with an assertion, exit 1. The scratch copy was deleted. The state-mutation module then ran
all 24 S1–S12 mutations; every `STATE MUTATION KILLED` line was printed, including the repaired
S1 cache-authority mutation; the exact output is retained in
[state-mutations.txt](records/state-mutations.txt). No regression assertion was removed or weakened.

## Not verified

The fresh `gpt-6-astra` xhigh review, including rollback mutations and the immediate
unchanged-signature case, remains for the lead. So does the lead's merge. PR #72's two conflict
resolutions and combined-result checks remain for its integration; the source guard rejects
reintroduced `qualification.record(` callers. No human game check or screenshot applies to
this browser-control read optimization. No Gradle or mod test was run.

No laptop boot tools, OS owner modules, mount, system installation, real browser profile or
owner-desktop input was used. The closing recursive check found **no files over 500 MB in `.work/`**
(and therefore none over 500 MiB). All disposable mutation copies and local Store directories
were cleaned up; small logs, scripts and CI artifacts remain for the lead.

## JUDGMENT-CALL

None added. The lead's six decided calls were followed, including exact bytes on every cached
use, private copies, maintenance returning nothing and the O2 assertion replacement.

## PLAN-GAP

The brief leaves `test_state_mutations` to CI but does not list its S1 source anchor among the
required updates. Round one exposed that stale anchor after the planned read-path replacement.
Retargeting it to `pinned_value` preserves the same removal fault and catching rollback test;
the full mutation suite passes locally. This is test-harness maintenance, not a changed
qualification or rollback rule.

## Open questions

None. Next: the fresh review, then the lead's merge.
