# Review 1 of #87: the Chrome tests hold the qualification record from fixtures (#79)

Reviewer: a fresh Claude agent (Opus 5.5), not the builder, 2026-11-16. Head `22566446` on
`test/79-qualification-fixtures`, base `e33ffc46`. `origin/main` is now at `9c6a3345`, but nothing under `control/` or
`.github/` has changed since the base. I worked read-only. The only file I wrote is this one; the tests wrote only
ignored caches and `.work/20-chrome/`.

## What I read and ran

- `AGENTS.md`, `PROGRESS.md`, and `git diff origin/main...HEAD` (5 files; nothing under `control/aresos_control`,
  `control/chrome/build.py`, `control/chrome/qualification.json`, packaging or `.github`).
- `adapter.py` (the `RUNTIME` seam at :23; build identity and shipped copy at :109-119; `mode()` and `maintenance()`
  at :204-229; the projection path at :245), `qualification.py`, `test_engine.py`, `ci/service.py`, `ci/run.sh`,
  `ci/latency-pair.sh`, `ci/Dockerfile`, `ci/admin.py`, `ci/python-shard.py`, the qualification workflow,
  `state_sweeps.py`, `test_state_crashes.py`, `test_state_mutations.py`, `mail_tests/support.py` and
  `mail_tests/test_build_identity.py`.
- **In the worktree (main's empty shipped copy):** `test_qualification_fixture`: Ran 6 tests, OK.
- **In a scratch copy with the data branch's record** (`origin/chrome-qualification` at `0a285b24`, six entries,
  among them main's build `145753b8…` on 157.0.8103.78 stable and 159.0.8154.6 beta), each module in its own process:
  - `test_qualification_fixture`, `test_engine` and `test_qualification_service` together: Ran 55 tests, OK.
  - Each OK on its own: `test_questions` 34, `test_sites` 17, `test_committed` 15, `test_state_fixes` 21,
    `test_restore_lock` 5, `test_state_crashes` 1 (nine real child processes), `test_latency` 39,
    `test_open_index_timing` 1, `test_full_disk_reads` 10, `test_state_exhaustion` 1.
  - `test_owner_confirm` 15: OK in a copy at a shorter path. The first copy's two errors came from that copy itself:
    the socket path was too long for AF_UNIX, and `.github` was missing.
- **The same scratch setup, but with the `install` line removed from `test_engine.py` (the fix taken out):**
  `test_engine` and `test_qualification_service` fail again with the refusal, and
  `test_qualification_fixture.test_this_process_starts_chrome_from_the_fixture_runtime` fails. That one test also
  fails with main's empty copy, so it guards the fix on every run.
- **Not rerun:** `test_storage` (17 min), the whole of `test_fault_surface`, the `.mjs` tests and anything in a
  container. The fault-sweep workers and the browser harness rest on the builder's runs and on CI.

## 1. Product behaviour: unchanged

- No product file changes. `append_only`, `Qualification.record()`, `switches()` and `Chrome.__init__` are
  byte-identical to main, so the rollback rule is untouched.
- **Who sets the seam.** `adapter.RUNTIME` is a plain module global. The diff adds no environment variable or
  config that reads into it, and the adapter reads none. Only three places set it, all outside the installed
  runtime:
  - `chrome_tests/qualification_fixture.py`;
  - `mail_tests/support.py`;
  - `chrome/ci/service.py`, which exits unless it runs on Linux with `GITHUB_ACTIONS=true` inside a container
    (`/.dockerenv`).
- **Why the installed service can't reach it.**
  - The packaging README lists what gets installed: `aresos_control`, `generated/`, `settings/`, `launch.py`,
    `requirements.lock` and `chrome/{extension,native_host.py,build.py,packaging,qualification.json}`. Neither
    `chrome_tests/` nor `chrome/ci/` is on that list.
  - The installed service starts as `env -i … python3 -I -S launch.py`, so `PYTHONPATH` can't inject a module.
  - `os/Containerfile` doesn't install `control/` yet.
- **The build hash is unchanged.** `chrome_tests/` and `chrome/ci/` are not build inputs (`build.py:inputs`). The PR's
  qualification pair runs on build `145753b8…`, the same as main's.

## 2. Coverage

- **JC1 (the baseline is empty instead of extending the shipped copy): I agree.** An empty baseline is exactly what
  every Engine-level test ran against on main, so nothing they covered is lost. Extending the shipped copy would fail
  in three ways:
  - The harness's synthetic entry `(build, container Chrome version, stable)` would repeat a key the shipped copy
    already holds for main's build: `145753b8…` on `157.0.8103.78` stable, which I checked in the data branch's
    record.
  - The harness's `conservative` mode would stop being conservative.
  - Every test's outcome would come to depend on which builds the data branch happens to cover.
- **JC2 (the tests read `build-id.json`): I agree.** Both identity paths stay covered:
  - The hashing path: `mail_tests/test_build_identity` and the new `test_the_real_shipped_copy_is_a_valid_record_chrome_trusts`.
    The latter starts Chrome from the source tree, so the identity is hashed, and asserts that it equals the fixture's
    `build_identity`. That also cross-checks the helper's copy of the identity logic against Chrome's own.
  - The installed path is now what every Chrome test exercises, and it is closer to the installed service.
- **Behaviour on a non-empty shipped copy.** At the record level, `test_qualification.Delivery` still covers it with a
  non-empty baseline: restart, image upgrade, a divergent baseline refused, and a dropped or changed fetch refused.
  At the Engine level, two things now run against a shipped copy with history:
  - the new refusal proof;
  - the check that the real shipped copy is valid. That check takes over what the browser harness did implicitly
    before: load the real copy at service start.

  No Engine-level test has a held record that extends a non-empty shipped copy and then acts (nit N1). Main never had
  one either, since its copy was empty.
- **The proof (`test_qualification_fixture.py`).** It does what it claims:
  - Five tests from three modules all fail with `qualification_rollback` when started from an image whose shipped
    copy holds history (:57). They pass from a fixture runtime built over that same image (:67).
  - The guard at :75 fails as soon as `test_engine` stops installing the fixture runtime (checked above).
  - The harness check at :106 is only a match on the source text. That's acceptable: the latency legs and fixture
    shards are the real proof for the harness.

## 3. The harness

- `service.py` behaves the same apart from four changes:
  - the baseline;
  - the identity is read from a `build-id.json` holding the same hash, where before every Engine start hashed the
    tree (two per service start, plus each `start_service` restart);
  - `chrome_tests/` is appended to `sys.path`; it goes last, so it can't shadow `sites`, the script's own folder or
    the standard library;
  - a temporary folder that `mkdtemp` makes in the disposable container, owned by `aresos-tools`.
- Each restart that `admin.py start_service` triggers installs the same baseline again, while the held record persists
  in `/var/lib/aresos-tools`, so restarts are consistent. The record switching (`qualified`, `conservative`, a failed
  group) gives the same modes as on main.
- **Latency with `ab7aba92`: still like-for-like.**
  - Both legs run the driver's `service.py` and `chrome_tests/`; `latency-pair.sh` copies both into the historical
    tree.
  - `ab7aba92`'s adapter has the same `RUNTIME` and `build-id.json` seam (`adapter.py:22`, `:58-66` at that commit).
    The seam dates from the first Chrome commit `414eb1df`, so any older qualification runtime has it too.
  - Both legs start from an empty baseline, the same as before (both shipped copies were empty).
  - The only start-up difference is one fewer hash, before the socket appears and outside the timed phases.
  - `runtime-build.txt` is still `build.py`'s own output.

## 4. Robustness

- **One folder per build in `.work`.** Its name comes from the build hash, so a changed tree gets a new folder. Files
  are rewritten only when their content differs, by `mkstemp` in the same folder plus `os.replace`, so a reader sees
  either no file or a complete one. Two processes writing the same content can't corrupt anything.
- **Stale state across builds** is limited to small leftover folders, one per build (JC5). One case is new: a tree
  edited during a run now gives one identity per process instead of one per Engine start. That is no worse than
  before.
- **The crash test's child** imports `test_engine` through the absolute `PYTHONPATH` its parent sets. It resolves the
  same `WORK`, so it gets the same build folder and its build matches the held record its parent wrote. I ran it:
  OK, 9 cuts.
- **The fault-sweep workers** use `spawn`. Each one imports `test_fault_surface`, which imports `test_engine` and
  installs the fixture runtime. Two workers plus the parent writing the same files is the safe case above.
- **Python shards.** `python-shard.py` loads every module before running any test, so `RUNTIME` is installed before
  the first test. Every module that starts an Engine or a Chrome imports `test_engine`; modules that don't import it
  start neither. That coverage holds by convention only (nit N3).
- **`test_state_mutations` copies** each get their own `ROOT/.work` inside the temporary copy, which is cleaned up
  afterwards.

## 5. CI (`gh pr checks 87`, read once, about 10:30 UTC)

These runs are for head `22566446` (the PROGRESS push), not the runs PROGRESS.md names.

- **Control Chrome (run 43842657082):**
  - Green: `package`, all four `python-shards` (0 to 3), `native-precedence`, `latency (plain)`, `latency (audit)`,
    and four fixture shards: external `recheck2`, `recheck3`, `word-3`, and policy `review`.
  - Still running: 5 fixture shards. Queued: 9.
- **Control Chrome qualification (run 43842657141):** `qualification-tests`, `qualification-plan` and
  `delivery-attestation` are green. `qualification-pairs` is running for build `145753b8…`.
- **Control Mail (run 43842657031):** 10 green; `containers (0)` and `sweep (0)` are running.
- **Control base, Control boundary, Repo privacy:** green. Boundary's earlier `hostile` flake doesn't recur in this
  run.
- **Nothing has failed.** Merging still has to wait for the remaining fixture shards, the pairs, combine and publish,
  and the Mail jobs. The real proof with a non-empty shipped copy is #83's run on its merge ref once this is on main,
  as PROGRESS.md says.

## Findings

**Blocking:** none.

**Should-fix:** none.

**Nits:**

- **N1** `control/chrome_tests/test_qualification_fixture.py`
  - **Gap:** the proof shows only the refusal and the empty-baseline pass. No Engine-level case has a held record
    that extends a non-empty shipped copy, the state the laptop will be in after #83.
  - **Fix:** add one positive case. Start from the `image` runtime, hold `shipped + [entry(build, '157.0.1.1')]`,
    and assert that an action works. Then assert that an uncovered major is still conservative and forces one
    refresh.
- **N2** `control/chrome_tests/test_qualification_fixture.py:83-85`
  - **Problem:** "not rewritten" is detected through `st_mtime_ns`. On a file system with coarse timestamps, a rewrite
    in the same tick goes unseen, so the test can pass falsely.
  - **Fix:** compare `st_ino` as well. `os.replace` always gives the file a new inode, so the check becomes exact.
- **N3** `control/chrome_tests/test_engine.py:21`
  - **Problem:** a Chrome test gets the fixture runtime only by importing `test_engine`. A future module that starts
    an Engine without that import would trust the real shipped copy. That fails loudly with `qualification_rollback`,
    not silently, so it is low risk.
  - **Fix (optional):** a one-line AST or text guard in `test_qualification_fixture`: every `chrome_tests/test_*.py`
    that calls `Engine(` or `Chrome(` imports `test_engine`.
- **N4** `reviews/79-qualification-tests/PROGRESS.md:128` and `:138`
  - **Problem:** the shard numbers disagree. In the 0-based job names, `test_qualification_fixture` sits in
    `python-shards (0)`, while `test_fault_surface` and `test_storage` sit in `python-shards (1)`. ":128 Shard 1
    includes the six new tests" and ":138 shard 1 now holds both long modules" can't both hold.
  - **Fix:** use the job names.

**Outside this PR** (product side, for the Chrome lead; nothing #87 should change):

- **O1** `control/aresos_control/chrome/adapter.py:245`
  - **What:** the pending-row projection computes switches from `committed.get('chrome:qualification', shipped)`
    directly, skipping `record()`'s reconcile. Once an image ships a copy longer than the held record, a pending row
    can show as current while `mode()` refuses the action.
  - **Impact:** it only affects the validity shown; the action itself still goes through `mode()`. It matters once
    #83 makes the shipped copy non-empty.
- **O2** Latency budget
  - **What:** neither latency leg measures a realistic record. Both validate an empty baseline plus one held entry,
    as on main. `mode()` calls `record()` twice, and each call validates both histories: about 6 ms per call at 1000
    entries on this laptop.
  - **Why it matters:** the record is append-only and never trimmed, so that cost grows unseen by the latency
    budget.

SAFE
