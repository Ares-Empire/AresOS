# Control follow-ups: review 1

Fresh reviewer: Claude agent on Opus 5.5 (2026-11-16), not the builder. PR #89, branch `fix/control-followups`.
Range `52d13cb7...2e4bfa22` (code `5fab270d..283931db`; `2e4bfa22` adds only `PROGRESS.md`). Read-only: no file
changed but this one. Main has moved since (`a46ffe44`), but only in `qualification.json` and docs, so nothing
conflicts.

## What I ran

- `PYTHONPATH=control:control/chrome_tests python3 -m unittest test_latency test_publisher test_qualification`:
  97 OK, both with `GITHUB_RUN_ID` unset and with it set to `12345`.
- In `control/`: `PYTHONPATH=.:tests python3 -m unittest tests.test_service_fixes` (CI runs it through
  `control/ci/base.py`'s discover). 55 run, and the only error is `ModuleNotFoundError: mcp_types` in
  `StartWithoutService`: the laptop has no MCP SDK, and Control base CI is green. `SocketStart`: 4 OK.
- 15 mutations on a `git archive` copy of the head in my scratch folder, with `PYTHONDONTWRITEBYTECODE=1` and the
  caches cleared:

| Mutation | Result |
|---|---|
| `daemon.SOCKET_MODES` admin 0o666 / chrome 0o660 / act 0o600 | `SocketStart` fails 1 / 1 / 2 |
| Gate: compare max only / min only / `>=` / never append a failure | `LatencyGate` fails 1 / 6 / 16 / 13 |
| Summary: `get('used_bytes_end',0)` / check only the first directory | `LatencySummary` fails 3 / 1 |
| Probe: counter offset 28 (page count) / no header check | `MainFixStorageStages` fails 3 / 1 |
| Probe: settle at the end only when a sample is active | passes: in practice the same behaviour (commits from an unmarked request are dropped at the next start anyway) |
| `qualify.py`: refuse only when the run ID is `None` (empty passes) / refuse only on the published path | `test_publisher` fails 2 / 2 |
| `storage.py` adds `PRAGMA locking_mode=EXCLUSIVE` | the probe counts 0. Only the real-Store test fails (nit 1) |

- SQLite 3.51.2 by hand, with the store's pragmas (`journal_mode=DELETE`, `synchronous=FULL`):
  - each of these moves the change counter by exactly the number of commits: a `with db:` insert, a 2,000-row
    transaction that spills the cache, two transactions in a row, `SAVEPOINT … RELEASE` in autocommit mode, and an
    `executescript` of two statements;
  - a rollback and a read move it 0.
- CI artifacts of `latency (plain)` and `latency (audit)` in run 43878612548 (all four legs):
  - `sqlite_commit` gives 2, 4 and 10 per call and 0 for `read`, the same in both legs. These are 20-ci-noise's
    trace-callback counts, so the new probe counts real commits in CI and doesn't come out at zero;
  - `latency-store.json` has `used_bytes_end` for both directories in all four legs;
  - the store used 77.5 MiB of state and 39.4 MiB of evidence, which matches the new `run.sh` comment.
- `delivery-attestation`'s log: `publisher_cases` reaches `notify(None, False, …)` with the runner's run ID, and
  both refusal cases print PASS.

## Each item

- **A1, `qualify.py:330-341`.** Done as described.
  - `this_run` is read and refused (missing or empty) before `report()`, so neither path makes a `gh` call without
    a run ID.
  - The refused-publication link now uses `this_run`, and `unknown` is gone.
  - The published path still filters by `entry['run']!=this_run` (`test_failing_groups…` with ID `42`).
  - The test now covers `published` True and False. My two mutations each fail it.
  - The stubs that set `GITHUB_RUN_ID` (`test_publisher` :90, :96, :123, :144, :484-493 and
    `test_qualification:358`) are needed. Without them the tests passed only because CI's runner sets the
    variable.
  - The 403 test checks `startswith('gh api ')`, so it can't pass on the run-ID refusal.
- **A2, `latency-check.py:97-100`.** Compares both min and max, per phase, call and counter. The test case that
  passed (3,3) against (2,3) was exactly the nit, and it now fails with the expected row.
  - Every gate mutation is caught.
  - Nothing else reads the row keys (grep).
  - The policy text is updated to match.
- **A3, `latency-profile.py:51-78, 117, 123`.**
  - The change counter is the right signal for a rollback-journal store. My checks above match the builder's
    test: an autocommit write counts 1, DDL 1, a no-op `COMMIT` 0, and a nested request gives 2 and 2.
  - `settle()` runs before `active` changes at a start and before `active=previous` at an end, so the commits
    belong to the right sample. Commits between requests (expiry, the history seed) go to `active=None`, as the
    trace callback's did.
  - Keeping the descriptor open is right: POSIX locks are per process, and closing any descriptor of the file
    would drop SQLite's.
  - A replaced file or a WAL header raises inside the request, so the sample's rows go missing and the summary
    refuses: it fails loud.
  - The daemon is a single-threaded selector loop, so `settle()` never runs in the middle of an SQLite call.
  - One mode slips through (nit 1).
- **A4, `latency-summary.py:80-83`.** Requires an int ≥ 0 `used_bytes_end` per directory.
  `latency-store.py end` writes it only after the mount check passes, and run.sh calls it only once the service
  has stopped. The test checks for the specific `end-of-run` message.
- **A5, A6.** Both comments are now accurate (numbers above; `service.py` keeps `'state_dir':'/var/lib/aresos-tools'`).
- **B, `test_service_fixes.py:1078-1104`.** It compares against the literal
  `{'act': 0o666, 'admin': 0o600, 'chrome': 0o666}` and no longer imports `SOCKET_MODES`. Changing any mode in
  `daemon.py` fails the test (table above).
- **Unchanged:** `latency-pair.sh`, `latency-reference.json` and `latency-targets.json` (`git diff --name-only`).
  Ceilings and sample counts are untouched. `run.sh` changes only a comment.

## Findings

No blocking and no should-fix findings.

1. **nit: the probe refuses WAL mode but not exclusive locking, where it counts nothing without a sign.**
   - Where: `control/chrome/ci/latency-profile.py:62-66`.
   - Why: under `PRAGMA locking_mode=EXCLUSIVE` the store still uses a rollback journal, and header bytes 18-19
     stay `1 1`. But SQLite raises the change counter only when it gives up the lock, so the counter stops moving.
     Measured: 5 commits move it 0, for every rollback journal mode.
   - What that would do: the current leg would report 0 commits against the old leg's 2/4/10, and the gate would
     pass, including any commit the change added. Exclusive mode is a plausible tuning for a single-process store.
   - Today: the store runs NORMAL (`storage.py:185-186`), and the real-Store test (`test_latency.py:813-830`)
     fails on that change. But it fails as `[('fresh:0', 0)] != [('fresh:0', 6)]`, which reads like "fewer
     commits", not "the probe can't count". JC2 says the probe fails loud for what it can't count, and this is
     the one mode it misses. It is the same class as 20-ci-noise's nit 3: not used today.
   - Fix: at install,
     `assert store.db.execute('PRAGMA locking_mode').fetchone()[0]=='normal','control.sqlite holds an exclusive lock; its commits cannot be counted'`.
     This only queries the connection's setting and touches no transaction. Add a test that sets EXCLUSIVE on the
     fixture database and expects `install` to refuse.
2. **nit: bookkeeping.**
   - Where: `reviews/control-followups/PROGRESS.md` "CI".
   - Why: it still says "Pending: the PR's first push".
   - Fix: the lead fills in the run IDs. When this merges, the lead can also mark 20-ci-noise's "Nits for later"
     done in `docs/control/TOOLS-HANDOFF.md:160-161`.

Not verified independently: the builder's claim (JC1) that a `COMMIT` which changed nothing doesn't sync. The
laptop has no `strace`. It is consistent with how SQLite works (no dirty page, no journal, no sync), and CI's
counts match the old statement-based count exactly, so no latency call makes such commits today.

## CI (head `2e4bfa22`)

All green, and `gh pr checks 89` shows 48 passed:
- Control Chrome (43878612548) passed, including `latency (plain)`, `latency (audit)`, `python-shards` 0-3 and all
  fixtures.
- Control Chrome qualification (43878612536) passed, including `qualification-tests`, `delivery-attestation`, every
  pair and `qualification-combine`.
- Control base (43878612639), Control boundary (43878612556), Control Mail (43878612662) and Repo privacy
  (43878612569) passed.

SAFE
