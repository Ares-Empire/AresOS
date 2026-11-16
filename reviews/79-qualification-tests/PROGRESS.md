# 79: tests hold the qualification record from fixtures, not the shipped copy

Builder: Claude agent (Opus 5.5), 2026-11-16, for the lead `linux-tools`. Branch `test/79-qualification-fixtures` from
`origin/main` at `e33ffc46`. Unblocks #83 (the shipped-copy update from the data branch `chrome-qualification`).

## What assumed the empty shipped copy

Chrome trusts two histories (`control/aresos_control/chrome/qualification.py`): the shipped copy, which `Chrome.__init__`
reads from `RUNTIME/chrome/qualification.json` (the source tree in tests, `/workspace/control` in the browser
container), and the record held in the store. `Qualification.record()` refuses a held record that does not extend the
shipped copy (`append_only`, code `qualification_rollback`); `mode()` calls it on every Chrome action.

Every test that writes its own held record started Chrome from the source tree, so it trusted whatever the shipped
copy held:

- `test_engine.Operations.setUp` writes `{'entries': [entry(build)]}`. The other modules that failed on #83 build on
  `test_engine`, through a subclass, a borrowed `setUp` or the same record: `test_committed`, `test_questions`,
  `test_state_fixes`, `test_sites`, `test_storage`, `test_restore_lock`, `test_owner_confirm`,
  `test_open_index_timing`, `test_latency`, `test_state_crashes`, `test_state_exhaustion`, `test_full_disk_reads` and
  `test_fault_surface`. `test_qualification_service.Service.set_record`,
  `test_engine` (password failure), `test_state_fixes`, `test_fault_surface` and `test_sites` write further held
  records; `test_fault_surface`'s `qualification` and `delivery` flows "fetch" a two-entry record from the same
  fixture.
- Engine restarts inside tests (`test_state_fixes.reopen`, `test_committed`, `test_fault_surface`,
  `test_restore_lock`, `test_storage`, `test_state_crashes`) and the crash test's child process start Chrome again
  from the source tree.
- The browser harness `control/chrome/ci/service.py` writes one synthetic entry for the build and the container's
  Chrome version, then switches between it, an empty record (`conservative`) and a failed group. The qualification
  pairs, both latency legs and every fixture shard run it.

With #83's record (six entries now) the held record `[entry(build)]` is shorter than the shipped copy and not its
prefix, so `record()` refuses it. Run 43756578941 (Control Chrome on #83) shows exactly that path: traceback
`adapter.mode` → `Qualification.record` → `append_only` → `Refused('qualification_rollback')`, in 15 modules of the
four Python shards. Every fixture shard fails in its first Python step (`test_questions`, `test_sites`, same refusal).
Both latency legs fail at the browser driver's first call (`rpc('tabs')` never answers ok: "extension native
connection"), which goes through `mode()` in the harness's service; main's identical code passed every job in run
43756528673, so the shipped copy is the only difference. The qualification run on #83 (43756578999) fails its tests
job and pairs the same way.

Not affected: `test_qualification` (`Records`, `Delivery` and the recorded-attestation cases build `Qualification`
with their own baseline), `ci/attestation.py` (its baseline is the candidate's first entry), `test_build` (only checks
that `qualification.json` is no build input), `qualify.py` (its baseline is `origin/main`'s shipped copy by design),
and the mail tests (`mail_tests/support.py` copies the shipped copy into its runtime, but no mail test writes a held
record or acts through Chrome; Control Mail passed on #83).

## What changed and why

- **`control/chrome_tests/qualification_fixture.py` (new), the one shared helper.** `fixture_runtime(directory)`
  writes an installed runtime: the source runtime's build identity (`build-id.json`, measured the way Chrome does)
  beside an empty shipped copy (`BASELINE`). `install(directory)` points `aresos_control.chrome.adapter.RUNTIME` at it,
  so every Chrome the process starts from then on (restarts included) trusts the fixture baseline. The folder is named
  after the build: the crash test's child shares its parent's runtime, a changed tree gets its own, and files are
  rewritten atomically only when they differ.
- **`test_engine.py`** installs it on import (`.work/20-chrome/fixture-runtime/<build>`). Every module that starts an
  Engine imports `test_engine`, and so does the crash test's child, so no test site changes: each test still builds
  its held record from its own fixture entries.
- **`control/chrome/ci/service.py`** installs it before its first Engine (`tempfile.mkdtemp()`, since the service user
  cannot write under `/workspace`). It appends `control/chrome_tests` to its path; both directories are what the
  qualification pairs and the latency leg copy from the driver, and the historical latency runtime (`ab7aba92`) has the
  same `RUNTIME` and `build-id.json` seam.
- **`test_qualification_fixture.py` (new), the proof.** It builds an image runtime whose shipped copy holds history,
  this build's own Chrome pair with every group failed among it. Five fixture tests (acting, a two-entry held record,
  a failed patch, an uncovered-major refresh that expects conservative mode, a restore with restarts) fail with
  `qualification_rollback` when Chrome starts from that image, and pass from a fixture runtime made over it. It also
  checks that this process runs from the fixture runtime, the folder reuse, that the real shipped copy is a valid record
  a Chrome from the source runtime trusts (the coverage the fixtures no longer give), and that the harness installs the
  runtime before its first Engine.
- **No product change.** `append_only`, `Qualification.record()` and the adapter are untouched; the new proof shows the
  unchanged refusal against a non-empty shipped copy.

## What ran and what it printed

Each module in its own process: `PYTHONPATH=control:control/chrome_tests python3 -m unittest <module>`. No Node here,
so no `.mjs` tests and no browser.

**Before the change, with the data branch's record in place** (`git show origin/chrome-qualification:control/chrome/qualification.json`,
six entries, 2026-11-16): `test_engine test_qualification_service` → `Ran 49 tests`, `FAILED (failures=52, errors=35)`,
the refusal of run 43756578941.

**After the change, with the data branch's record in place** (restored with `git checkout` afterwards):

| Module | Result |
|---|---|
| test_qualification_fixture (new) | Ran 6 tests, OK |
| test_engine | Ran 32 tests, OK |
| test_qualification_service | Ran 17 tests, OK |
| test_committed | Ran 15 tests, OK |
| test_questions | Ran 34 tests, OK |
| test_state_fixes | Ran 21 tests, OK |
| test_sites | Ran 17 tests, OK |
| test_restore_lock | Ran 5 tests, OK |
| test_owner_confirm | Ran 15 tests, OK |
| test_open_index_timing | Ran 1 test, OK |
| test_latency | Ran 39 tests, OK |
| test_state_crashes | Ran 1 test, OK ("Chrome actual process cuts: 9"; the child processes start from the fixture runtime) |
| test_storage | Ran 16 tests, OK (17 minutes) |
| test_state_exhaustion | Ran 1 test, OK |
| test_full_disk_reads | Ran 10 tests, OK |
| test_qualification | Ran 31 tests, OK |
| test_build | Ran 3 tests, OK |
| test_publisher | Ran 26 tests, OK |
| test_policy | Ran 18 tests, OK |
| test_state_mutations | Ran 1 test, OK (24 "STATE MUTATION KILLED"; with the old fixtures and a non-empty shipped copy these would have been killed by the rollback refusal, not by the regression) |
| test_fault_surface | Ran 16 tests, OK in 690 s; "Chrome full writer surface {'single': 2130, 'persistent': 2130, 'pairs': 8488}", all 19 flows, `qualification` 54/54/98, `delivery` 109/109/259 and `restore` 76/76/290 among them |

test_fault_surface ran in a copy of the tracked `control/` tree with the data branch's record (a first run in the
worktree passed its first three flows and then hit my 25-minute limit while another session's install loaded the
disk; it had no failure).

**After the change, with main's empty shipped copy** (the file as committed): the same 20 modules, each OK, with the
same test counts: test_qualification_fixture 6, test_engine 32, test_qualification_service 17, test_committed 15,
test_questions 34, test_state_fixes 21, test_sites 17, test_restore_lock 5, test_owner_confirm 15,
test_open_index_timing 1, test_latency 39, test_state_crashes 1, test_state_exhaustion 1, test_full_disk_reads 10,
test_qualification 31, test_build 3, test_publisher 26, test_policy 18, test_state_mutations 1 (24 mutations killed),
test_storage 16. Instead of the whole test_fault_surface, I ran its 15 tests other than the sweep (OK) and the sweep's
qualification-writing flows `qualification`, `delivery` and `restore` (239/239/647, the same counts as with the data
branch's record).

## What CI must still show

- **On this PR (#87), with main's empty shipped copy:** every job green as on main, in particular the four Python
  shards (they now include `test_qualification_fixture`). They also need the browser parts I could not run here: the
  fixture shards and the latency legs (the harness's `install()` inside the container, run by the service user, and
  the historical `ab7aba92` runtime under the current `service.py`), the aggregates, and the qualification workflow's
  tests, pairs and combine.
  **State on 2026-11-16, 09:45 UTC** (Control Chrome run 43831972611, qualification run 43831972629):
  - **Green:**
    - All four Python shards: 86, 79, 106 and 82 tests, each OK. Shard 1 includes the six new tests.
    - Both latency legs, so the harness's `install()` works for the current and the `ab7aba92` runtime.
    - `native-precedence`, the five fixture shards finished so far, and the qualification workflow's
      `qualification-tests`, `qualification-plan`, `delivery-attestation` and the first 12 pair shards.
  - **Still running:** the rest of the fixture and pair shards, the aggregates, combine and publish.
  - **Control boundary** (run 43831972645) failed in `hostile`: "approval changed native full mount tree", on a new
    mount `/tmp/claude-10001/bash-edit-diff` that the Claude client in that container made. This branch changes
    nothing under `control/boundary`, and the same workflow passed on other branches 20 minutes earlier, so I take it
    for an environment flake and re-ran the failed job once.
  - **Other workflows:** Control base and Repo privacy green; Control Mail still running.
- **Shard balance:** the new test file moves the sorted file partition by one, so shard 1 now holds both long modules,
  `test_fault_surface` and `test_storage`, and took 29 minutes (17 on main). The job limit is 120 minutes.
- **On #83 once this is on main:** #83's checks run on its merge ref, main plus the data branch's record. That is the
  real proof for the browser harness with a non-empty shipped copy: every Control Chrome and qualification job green.
  Its latest runs (head `0a285b24`) are waiting for approval (`action_required`). Merge #83 with a merge commit, never
  a squash (see `docs/control/TOOLS-HANDOFF.md`).
- The data branch has grown: #83 now copies six entries, not four. Its two newest entries cover main's current build
  `145753b8…` (stable `157.0.8103.78`, beta `159.0.8154.6`). This change leaves the build hash unchanged, because
  `chrome_tests/` and `chrome/ci/` are no build inputs.

## JUDGMENT-CALLs

1. **The fixture baseline is empty; fixtures don't extend the shipped copy.** The shipped copy now holds entries for
   main's own build (`145753b8…`, stable `157.0.8103.78`, the container's Chrome). Extending it would give the harness's
   synthetic entry the same key (`Repeated qualification key`), would make its `conservative` mode not conservative,
   and would break the tests that expect conservative mode for Chrome 158 as soon as main's build is qualified on 158.
   With an empty baseline the tests run exactly as they did before the shipped copy had entries.
2. **One process-wide seam (`adapter.RUNTIME`) instead of a call at each Engine.** It is the installed-runtime seam
   `mail_tests/support.py` already uses, it covers restarts and the child process, and new tests get it by importing
   `test_engine`. Side effect: Chrome tests read `build-id.json` instead of hashing `build.py` at every Engine start
   (the same hash, computed once per process; faster). The hashing path stays covered by `mail_tests/test_build_identity`
   and the new real-shipped-copy test.
3. **The helper lives in `control/chrome_tests`**, and `service.py` appends that directory to its path. Putting it in
   `control/chrome/ci` would put names like `admin`, `call` and `service` on the tests' path.
4. **`mail_tests/support.py` is left alone.** It still copies the real shipped copy into the mail tests' runtime; that
   is harmless while no mail test writes a held record or acts through Chrome. Moving it onto this helper would make
   the mail suite import from `chrome_tests`.
5. **The fixture runtime folder under `.work/20-chrome/fixture-runtime/` stays between runs** (ignored, one small folder
   per build), so the crash test's child, which exits with `os._exit`, never leaves temporary folders behind.
