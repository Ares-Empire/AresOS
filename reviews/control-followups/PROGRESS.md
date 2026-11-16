# Control follow-ups: 20-ci-noise nits and 18e's socket-mode nit

Builder: a Claude agent on Opus 5.5 (2026-11-16). Branch `fix/control-followups`, off `main` at `52d13cb7`.
Sources: `reviews/20-ci-noise/REVIEW-1.md` ("Findings") and `REPORT.md` ("Review and merge"), brief
`briefs/20-ci-noise.md`; `reviews/18e-service-fixes/RECHECK-2.md` ("Recheck of 1abf3e43", nit 1).
Unchanged: ceilings, sample counts, `latency-pair.sh`, `latency-reference.json`, `latency-targets.json`.

## Done

| Item | Commit | Change | Test |
|---|---|---|---|
| A1, `qualify.py` notify | `5fab270d` | Without `GITHUB_RUN_ID` (missing or empty), notify refuses (`SystemExit`) before any GitHub call on both paths, as the brief says. The "publication refused" issue is no longer opened with an `unknown` run link | `test_publisher` `test_failing_groups_issue_names_only_this_run_s_entries`: the missing/empty run ID now refuses with `published` True and False, with no `gh` call |
| A2, `latency-check.py` sync gate | `045df49a` | Per phase, call and counter, both `current.min <= old.min` and `current.max <= old.max`. Each row also carries `current_min` and `ab7aba92_min` | `test_ci_noise_an_added_fsync_or_sqlite_commit_fails_the_sync_gate`: old (2, 3) against current (2, 3) passes; current (3, 3) fails with `('history-4000','navigate','sqlite_commit',3,2,3,3)`. The earlier case that asserted (3, 3) against (2, 3) passes was exactly the nit, so it moved to the failing side |
| A3, `latency-profile.py` commit counter | `c7faf59d` | The trace callback on COMMIT/END statements is gone. The probe reads SQLite's file change counter (header bytes 24-27 of `control.sqlite`), which a rollback-journal database raises once per committed change, however the transaction began. It reads it whenever a request starts and ends, so a nested request's commits stay its own and work between requests isn't counted. It keeps one read-only descriptor open for the service's life (closing any descriptor of the file would drop SQLite's process-wide POSIX locks). It refuses a WAL database (header bytes 18-19 not 1) and a `control.sqlite` replaced under it | New `test_ci_noise_the_commit_count_is_what_commits_an_autocommit_write_included`: an autocommit `INSERT` counts 1, a DDL statement 1, a `BEGIN … DELETE nothing … COMMIT` 0; a nested request counts 2 and 2, not 2 and 4; a replaced file and a WAL database refuse. The real-`Store` test still counts 6 commits for 3 writes |
| A4, `latency-summary.py` | `10e06a58` | Requires `used_bytes_end` (an int ≥ 0) for both store directories, so a skipped end-of-run mount check fails the summary | `test_ci_noise_summary_carries_sync_counts_and_refuses_a_store_off_tmpfs`: no end record, or one for only either directory, refuses |
| A5, A6, comments | `b83f7822` | `run.sh`: the store used up to 77 MiB (about 81 MB) of state and 39 MiB of evidence in run 43745378252, instead of "well under 100 MB". `test_latency.py`: the store keeps its own directories, with a tmpfs mounted over them for the pair, instead of "stays on the container's disk" | none (comments) |
| A7 | none | The lead answered it in `REPORT.md` | |
| B, `SocketStart` | `283931db` | `test_the_final_path_appears_only_with_its_mode_and_listening` compares with the literal `{'act': 0o666, 'admin': 0o600, 'chrome': 0o666}`, no longer with `daemon.SOCKET_MODES` | itself |

Also in `5fab270d`: the tests that stand in for main's notify set `GITHUB_RUN_ID` themselves
(`test_publisher`'s stub calls and the two prepare-refusal cases, `test_qualification`'s `publisher_cases` run).
Before, they passed in CI only because the runner sets the variable; locally they now refused.

## Mutations

Each run with `PYTHONDONTWRITEBYTECODE=1` and `__pycache__` cleared. A same-size edit and its undo inside one second
reuse stale bytecode (`spec_from_file_location` loads through `__pycache__` too); that gave one false result here
before the caches were cleared.

| Mutation | Result |
|---|---|
| A1: `qualify.py` from `52d13cb7` | `test_publisher`: 2 failures (run ID missing and empty, `published=False`) |
| A1: no refusal at all, `unknown` link back | 4 failures |
| A2: compare the maximum only | `LatencyGate`: 1 failure |
| A3: `latency-profile.py` from `52d13cb7` (the trace callback) | 1 failure: `[0, 0, 1] != [1, 1, 0]` |
| A3: one difference from request start to end, no settling at nested boundaries | 1 failure: `[2, 4] != [2, 2]` |
| A3: no settle at request start | 1 failure |
| A3: no replaced-file check / no WAL check | 1 failure each |
| A4: `latency-summary.py` from `52d13cb7` / the new assert removed | 3 failures (each missing end record) |
| B: `daemon.SOCKET_MODES` admin 0o666, act 0o600, chrome 0o600 | `SocketStart`: fails for each. The test from `52d13cb7` passes with admin 0o666 (checked) |

## Local results (laptop, Python 3.14, SQLite 3.51.2)

- `PYTHONPATH=control:control/chrome_tests python3 -m unittest test_latency test_publisher test_qualification`:
  97 tests OK, with `GITHUB_RUN_ID` unset and set.
- Neighbours, same path: `test_build test_qualification_service test_qualification_shards test_qualification_fixture
  test_restore_lock test_open_index_timing`: 35 OK.
- In `control/`: `PYTHONPATH=.:tests python3 -m unittest tests.test_service_fixes tests.test_ingress_bounds`: 63 run,
  2 errors, both `ModuleNotFoundError: mcp_types` (no MCP SDK on the laptop, as in 18e's PROGRESS; Control base CI
  has it). `tests.test_unit tests.test_review22_protocol`: 8 OK.
- `PYTHONPATH=control python3 control/generate.py --check`: "Generated artifacts match definitions".

## CI

PR #89, one code push, head `2e4bfa22`. All green:
- Repo privacy 43878612569, Control base 43878612639 (has the MCP SDK the laptop lacks), Control boundary
  43878612556, Control Mail 43878612662: success.
- **Control Chrome qualification 43878612536: success**, 34 jobs, `qualification-tests` included (it runs
  `test_publisher` and `test_qualification`).
- **Control Chrome 43878612548: success**, 28 jobs, `python-shards` 0-3, `latency (plain)` and `latency (audit)`
  included.
  - Both profiles' `latency-check.json`: `passed: true`, no `failures`, no `sync_failures`, 36 sync comparisons.
  - Sync counts per sample, from the new probe and identical on every sample in both runtimes and both profiles:
    read 0 and 0, asking_click 2 and 2, navigate, free_click and fill 4 and 4, approval_to_done 10 and 10 (fsyncs
    and commits). These are 20-ci-noise's counts exactly (run 43745378252): the file's change counter sees the same
    commits as the COMMIT statements did on every latency call, so JUDGMENT-CALL 1's possible drop didn't happen.
  - The store at the end, current runtime: 77 MiB state and 39 MiB evidence, each on its own `tmpfs`, as the `run.sh`
    comment now says. The end record is present, so the summary's new check passed in both legs.

## JUDGMENT-CALLs (technical, for the lead)

1. **A3 counts committed changes, not COMMIT statements.** I used SQLite's file change counter instead of adding
   autocommit statements to the trace callback: a statement-based count would have to guess which statements write.
   Effect: a COMMIT that changed nothing is no longer counted. It syncs nothing (checked: the counter doesn't move),
   so it isn't a disk sync. If the product makes such commits on a latency call, CI's `sqlite_commit` counts drop
   below 20-ci-noise's (2, 4, 10 per call); CI showed they didn't. Both legs run the same probe (the pair copies `ci/` into the old tree),
   so the gate still compares like with like.
2. **A3 holds a read-only descriptor of `control.sqlite` for the service's life** and checks on every read that the
   path still names that file. Reopening per read would be simpler, but closing a descriptor drops the process's
   POSIX locks on the file, SQLite's included. The probe fails loud (a refused request) if the file is replaced or in
   WAL mode, instead of counting nothing.
3. **A1 has no fallback.** A main run without a run ID now opens no "publication refused" issue either; the failed
   notify step is the alarm. This reverses the 20-ci-noise builder's own call, as the lead's follow-up list asked.
   `attestation.py`'s `publisher_cases` in CI relies on the runner's `GITHUB_RUN_ID` (set on every GitHub runner).
   Only its unit test sets one. I didn't add a fixture ID inside the harness, so it keeps behaving like main.

## Review and merge (lead, 2026-11-16)

- `REVIEW-1.md` (fresh Opus reviewer): SAFE, two nits. CI green on `2e4bfa22` (six workflows, 48 checks).
- JUDGMENT-CALLs 1-3 accepted. The read-only handle on `control.sqlite` exists only under the latency probe.
- Nit 2 (PROGRESS said CI pending) was already fixed by `51276156`.
- Nit 1 (the probe refuses WAL mode but not `locking_mode=exclusive`, where the counter stops moving) goes to the
  Codex queue: assert `normal` at install, with a test. The store doesn't use exclusive locking today, and a
  real-Store test already fails in that case.
