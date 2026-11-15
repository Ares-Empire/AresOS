# 20-ci-noise: review 1

Fresh reviewer: Claude agent on Opus 5.5 (2026-11-15), not the builder. Range `a142e2c9...2ac3e1a9` (code), head
`ffa850cf`. Read-only. Local: `PYTHONPATH=control:control/chrome_tests python3 -m unittest test_latency test_publisher`,
65 tests OK. CI on `2ac3e1a9`: Control Chrome 43745378252 and qualification 43745378358 green, and boundary, base and Mail.

## What was checked

- **Item 1, notify.**
  - Matching this run's entries is an exact string comparison: `validate_record` requires `run` to be a non-empty
    `str`, and `prepare` writes `str(GITHUB_RUN_ID)`.
  - A run that published nothing new sends no failing-groups write. A re-run attempt keeps its run ID, and
    `report` skips text it already posted.
  - On the publishing path, the refusal without a run ID comes before any `gh` call.
  - Split into separate tests against the old `qualify.py`, three of the four fail as they should; the fourth is the
    positive case.
- **Item 2, the tmpfs.**
  - The mounts are made only under `LATENCY_PROBE=true` (only `latency-pair.sh` sets it), before anything writes
    the store.
  - Both legs and both profiles had each directory on its own tmpfs in run 43745378252.
  - It fails closed: `set -e`, the summary's assert, and the end record's assert.
  - Nothing is hidden by the mounts, and state persists across the run's phases.
- **Item 2, the count gate.**
  - It covers 36 phase and call combinations.
  - Four mutations were each caught: ignoring `sync_failures`, comparing min instead of max, dropping the tmpfs
    assert, and a probe that counts no commits.
  - The commit counter lives only in `latency-profile.py`, which loads only under the probe.
  - Missing counts stop the check.
- **Unchanged:** ceilings, sample counts, `latency-pair.sh` and `latency-reference.json`.

## Findings (all nits; none blocks)

1. `qualify.py:330-341`: without a run ID, only the publishing path refuses; the "publication refused" issue is
   still written with an `unknown` link. On main the variable is always set.
2. `latency-check.py:95`: the gate compares the highest count per sample only. That is equivalent while counts are
   uniform, as today. Also require `current.min <= old.min`, or fail when the old leg's min and max differ.
3. `latency-profile.py:53-55`: the commit counter sees only `COMMIT`/`END`. A statement in autocommit mode commits
   without either, and fsyncs outside `storage.py` aren't counted. The store doesn't write that way today.
4. `latency-summary.py:77-79`: the summary doesn't require the end record (`used_bytes_end`), so a skipped
   end-of-run check would still pass.
5. `run.sh:37`: the comment says "well under 100 MB"; CI measured about 81 MB for state.
6. `test_latency.py:798`: the comment "The store stays on the container's disk" is out of date.
7. Not recorded as PLAN-GAPs:
   - the frozen `latency-reference.json` was measured with the store on disk, so the regression allowance is
     somewhat looser now;
   - a deliberate new sync (a durability change the lead approves) fails the gate until the gate changes.

SAFE
