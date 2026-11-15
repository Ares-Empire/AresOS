# 20-ci-noise: progress

Brief: `briefs/20-ci-noise.md`. Builder: a Claude agent on Opus. Branch `ci/20-ci-noise`.

## Done

**Item 1: the failing-groups issue names only this run's entries** (`d562567f`)
- `control/chrome/qualify.py` `notify`: "Chrome qualification has failing groups" lists only entries whose
  `run` equals `GITHUB_RUN_ID`. With the run ID missing or empty, a publishing notify refuses
  (`SystemExit`) before any GitHub call. "Update shipped Chrome qualification record" still lists every entry
  on the data branch. Validation, attestation and publishing are untouched.
- `control/chrome_tests/test_publisher.py`, new test `test_failing_groups_issue_names_only_this_run_s_entries`:
  - an earlier run's failing entry is not reported, and this run's is;
  - the shipped-copy issue still lists all three entries;
  - with no failing entry from this run, the failing-groups issue gets no new issue and no new comment
    (an open one is listed by the workflow, and nothing is created or commented on it);
  - a missing or empty run ID refuses, with no GitHub call.
- The test fails against the old `notify` (it reports the earlier build's `binding`).
- The existing stub test now sets `GITHUB_RUN_ID` to its fixture entry's run.

**Item 2: the latency store on a tmpfs, and a sync-count gate** (`6268dde8`)
- Where the store lives: `control/chrome/ci/service.py` runs the service with `state_dir`
  `/var/lib/aresos-tools` (`control.sqlite`, blobs) and `evidence_dir` `/var/lib/aresos-operation-evidence`
  (the journal `operations.jsonl` and its index). The Dockerfile only creates both directories, so before this
  change they were on the container's overlay disk.
- `control/chrome/ci/run.sh`: under `LATENCY_PROBE=true` it mounts a tmpfs over each of the two directories
  (`size=512m,mode=0755,uid=<aresos-tools>`, the image directories' own mode and owner). This happens before
  the harness, `prepare.mjs` or the service write anything. `latency-pair.sh` copies `ci/` into the old tree,
  so both runtimes (current and `ab7aba92`) get the same mounts.
- Sizing: main's run 43726046014 had a journal of 19 MB (current) and 30 MB (`ab7aba92`) after the
  4000-entry history. `control.sqlite` keeps every event plus the state, so it holds roughly the journal's size
  again. 512 MB per directory is several times that. The storage ledger's free-space check
  (`space.py`: cost + held + 4 MiB) has plenty of room. tmpfs only uses memory for what is written.
- `control/chrome/ci/latency-store.py` (new) writes `/out/latency-store.json`:
  - at the start, each directory's mount as `/proc/self/mountinfo` reports it (mount point, fstype, source,
    super options) and the mount's size and use;
  - at the end (after the service stops), the space used, and a refusal if the mount changed.
- `latency-summary.py` carries that record as `store` in `latency-summary.json` and refuses unless both
  directories were on a `tmpfs`. Both legs' artifacts state it.
- The sync counts:
  - `journal_fsync`'s `count` was already counted by H5's probe (every `os.fsync` in the storage module).
  - SQLite commits were not. `latency-profile.py` counts them with a trace callback on the store's
    `control.sqlite` connection: it sees each `COMMIT` the sqlite3 module issues and only counts it, so the
    product is unchanged. It emits a count-only row, stage `sqlite_commit`, per marked request.
  - Checked locally against the real `Store`: one write is 2 fsyncs and 2 commits.
- `latency-summary.py` sums both counts per sample over its requests and keeps them out of the timing
  percentiles. It writes `sync_counts[phase][call][counter] = {samples, min, max}` and refuses a sample
  without both counts.
- `latency-check.py` has a new `sync_gate`. Per history phase and call, the current runtime's highest
  per-sample count of each counter must not exceed the old runtime's (`ab7aba92`, the pair's other leg).
  Failures go to `sync_failures`, and `passed` needs both lists empty. `latency-check.json` lists every
  comparison under `sync_counts`.
- Ceilings, sample counts, positions and the timing gate are unchanged.
- Tests (`control/chrome_tests/test_latency.py`):
  - `test_ci_noise_an_added_fsync_or_sqlite_commit_fails_the_sync_gate`: one more fsync or commit than
    the old runtime fails the gate, on every sample or on one, in three phase/call pairs. All timings stay
    nominal. Fewer or equal passes, and missing or malformed counts on either side refuse. Without the gate
    the test fails.
  - `test_ci_noise_summary_carries_sync_counts_and_refuses_a_store_off_tmpfs`: counts are summed over a
    sample's requests and stay out of the timing stages. A missing count, or a store on `ext4` or `overlay`,
    refuses.
  - `test_ci_noise_the_profile_counts_a_real_store_write_s_fsyncs_and_commits`: the probe over the real
    `Store` counts 6 and 6 for three writes inside a sample, and nothing outside one.
  - `test_ci_noise_the_store_is_on_a_tmpfs_for_both_runtimes_and_the_artifact_says_so`: covers the mount
    line, its directories matching `service.py`, the order before the harness and service, and the
    start/end records.
  - `test_ci_noise_the_store_record_reads_the_kernel_s_mount_table`: mountinfo parsing (octal escapes,
    stacked mounts), and the refusal when the mount changed mid-run.
  - The H5 profile stub now has a real SQLite connection and asserts the `sqlite_commit` rows.
  - The existing gate fixtures carry uniform counts: the frozen reference predates them.

## Runs

- Local, Python 3.14: `PYTHONPATH=control:control/chrome_tests python3 -m unittest test_latency test_publisher`
  ran 65 tests, OK.
- CI on `2ac3e1a9` (the pull request's first and only CI push):
  - **Control Chrome 43745378252: success**, every job, `latency (plain)` and `latency (audit)` included.
    - Both legs' `latency-store.json`, read from the kernel: `/var/lib/aresos-tools` and
      `/var/lib/aresos-operation-evidence` were each their own `tmpfs`
      (`rw,size=524288k,mode=755,uid=1001,inode64`).
    - Used at the end: current 77 MiB (state) and 39 MiB (evidence), `ab7aba92` 51 and 25 MiB. 512 MiB
      leaves about 6.6 times room.
    - `store_write` p95 fell from 66 to 210 ms (main's run 43726046014, plain) to 1.1 to 6.1 ms in every
      phase. The slowest client p95 was `approval_to_done` at history-4000: 581 ms against its 850 ms
      ceiling.
    - Sync counts per sample: read 0 and 0, asking_click 2 and 2, navigate, free_click and fill 4 and 4,
      approval_to_done 10 and 10 (fsyncs and commits). They were identical on every sample, in every phase,
      in both runtimes and both profiles.
    - `latency-check.json`: `passed: true`, no `failures`, no `sync_failures`, 36 sync comparisons.
  - Control boundary 43745378210, Control base 43745378325, Control Mail 43745378331: success.
  - **Control Chrome qualification 43745378358: success**. Every job passed: `qualification-tests` (it runs
    `test_publisher` in CI), the pairs, combine and the local publish.

## What the code doesn't show

- Item 1 runs live only on main. `notify` is main-only, so the pull request's run skips it. The first
  main run after the merge is the first real one. It should then add nothing to #74's failing-groups issue,
  because no entry from that run fails. After that, the lead closes #74.

- The counts were already deterministic before this change. In main's run 43726046014 every sample of a
  phase/call had the same `journal_fsync` count in both legs: read 0, asking_click 2; navigate, free_click
  and fill 4; approval_to_done 10. The two runtimes agreed exactly. So the gate compares the maximum, and a
  sync added on only some samples is caught too.
- "Reference" in the gate is the pair's old runtime (`ab7aba92`), the leg measured on the same runner. The
  frozen `latency-reference.json` predates the counts and has none.
- Only `control.sqlite`'s commits are counted. The journal index (`journal-index.sqlite`) runs
  `synchronous=OFF` and `journal_mode=OFF`, so its commits don't sync. If that ever changed, neither count
  would see it.
- `journal_fsync` counts the storage module's `os.fsync` only, as H5 defined it. Blobs, uploads and archives
  sync through their own modules, and the latency calls don't use those.
- The mount is done inside the container (root, `--cap-add SYS_ADMIN`, seccomp and AppArmor unconfined, as
  the pair already runs it), not with `docker run --tmpfs`. That leaves `latency-pair.sh` untouched, so
  PR #72 (which moves its docker command into a function) and PR #76 merge without conflict, and #72's
  efficiency mode gets the same store.

## JUDGMENT-CALLs

- None that change how AresOS feels. Two small technical calls:
  - Without a run ID, notify refuses only on the publishing path. The "publication refused" issue still opens
    (its link then says `unknown`), because it is the alarm that nothing new is trusted. On main the variable
    is always set.
  - Two separate tmpfs mounts, one per store directory, at the product's own paths, instead of redirecting
    the service's paths. On the laptop both directories share one file system. Nothing in the store renames
    or links across the two, so this doesn't change behaviour.

## PLAN-GAPs

- None so far.
