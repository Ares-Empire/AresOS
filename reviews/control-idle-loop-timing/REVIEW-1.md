Codex gpt-6-astra, 2026-11-17. Reviewed head `2e39ddc1` against local `origin/main` (`3a5eea14`).

Read `AGENTS.md`, the PR description, PR #96 review Findings 1–2, `docs/design/DESIGN.md`, the requested diff, and the relevant daemon, engine, storage, retention, Chrome maintenance, session-walking and CI code. `gh pr view 97` and `gh pr checks 97` failed to connect; the connected GitHub tool supplied the description and confirmed six successful workflows at this head.

Ran:

- From `control/`, `PYTHONPATH=.:tests python3 -m unittest test_service_fixes`, twice, with bytecode writing disabled. Both encountered sandbox socket denials and stalled; both were terminated. A diagnostic watchdog run also stalled at `FixRoundProxy.test_call_tool_marks_the_session_read_at_start`. **These are not successful full-suite runs.**
- The MCP startup test separately on both revisions: identical `ModuleNotFoundError: No module named 'mcp_types'`.
- All nine `IdleLoop` tests on scratch copies of both revisions, then against each mutation below. Because the sandbox denies Unix socket binding, the scratch runner substitutes inert pipe listeners. The selector, wakeup pipe, engine, SQLite and journal remain real. Both unmutated classes passed; mutation kills below were assertion failures, not setup errors.
- Slow-fsync runs at 0.05, 0.15 and 0.5 seconds per `os.fsync`. New tests passed the first two; old tests failed both. At 0.5 seconds, the new class failed its idle-budget assertion.
- `QuietUnlessUsed`: 27 tests passed. Both `mark_session` failure-message branches and success branches passed isolated probes. Clock cleanup after an intentional assertion failure passed. Shell and changed Python syntax checks passed.

Scripts and logs are under `.work/review-97/`.

| Behaviour broken in scratch product code | New tests | `origin/main` tests |
|---|---|---|
| Ignore the pending deadline in `Daemon.timeout` | Killed | Killed |
| Remove the idle loop’s `engine.expire()` call | Killed | Killed |
| Add 250 ms to the calculated future-deadline timeout | Killed | Killed |
| Select the latest reservation instead of the earliest | Killed | Killed |
| Leave expired operations reserved | Killed | Killed |
| Let deferred notices replace an earlier reservation deadline | Killed | Killed |
| Include finished operations in `next_deadline` | Killed | Killed |
| Change `DEADLINE_MARGIN` from 5 ms to 250 ms | **Survived** | Killed |
| Sleep 250 ms before expiry whenever a deadline exists | **Survived** | Killed |
| Sleep 250 ms before expiry on every loop iteration | Killed by confirmation test; pending-expiry test passed | Killed by both tests |

1. **SHOULD-FIX — The rewritten test loses an independent lateness bound.**  
   [control/tests/test_service_fixes.py:436](../../control/tests/test_service_fixes.py#L436), [control/tests/test_service_fixes.py:440](../../control/tests/test_service_fixes.py#L440).

   Both expected times now incorporate the production `DEADLINE_MARGIN`. Increasing that constant to 250 ms makes a 400 ms reservation wait approximately 650 ms, yet all nine new tests pass. The original test rejects this mutation: `0.647838… not less than or equal to 0.41`.

   Keep the frozen clock, but retain an independent simulated-time limit—for example, require the first timeout to remain within 410 ms for this fixture, alongside the exact formula assertion. This restores coverage without reintroducing disk-speed dependence.

   The conditional blocking-delay mutation additionally demonstrates that the new test proves requested scheduling, not actual elapsed-time responsiveness. Freezing time intentionally removes storage latency from that measurement; it should not be described as preserving every previous timing guarantee.

2. **NIT — The idle assertions retain a reproducible slow-runner failure.**  
   [control/tests/test_service_fixes.py:437](../../control/tests/test_service_fixes.py#L437), also [control/tests/test_service_fixes.py:421](../../control/tests/test_service_fixes.py#L421) and [control/tests/test_service_fixes.py:453](../../control/tests/test_service_fixes.py#L453).

   At 0.5 seconds per fsync, the new pending-expiry test failed with `58.992410… not greater than 59`. Two journal flush delays consume the real maintenance budget despite correct expiry scheduling.

   This is an explicitly documented, pre-existing limitation, acceptable for the narrowly scoped fix to the observed shorter stalls. It does mean the class is not generally independent of runner speed. A follow-up should control monotonic time too and advance both clocks together during simulated selects.

The clock audit found no hidden real-time source deciding these reservations:

| Wall-clock source | Effect under this patch |
|---|---|
| `engine.py:299` reservation creation, `:280` expiry, `:264` notice retry; `daemon.py:187` deadline subtraction | All use the patched `time.time` |
| `retention.py:95` working-data expiry | Patched |
| `storage.py:680` journal timestamp | Patched; event timestamps and retained-row timestamps derive from that value |
| Storage migration/recovery timestamps (`storage.py:227`, `:266`, `:268`) and fallback `retained_at` (`:743`) | Use `time.time`; fixture initialization occurs before the patch, without an existing reservation |
| Chrome upload pruning and qualification refresh | Their `time.time` reads are patched; these fixtures have no retained uploads or connected browser requiring refresh |
| `time.time_ns` notice timestamps | Unpatched, but not used to schedule reservation expiry |
| `datetime.now`, SQL `CURRENT_TIMESTAMP`, SQL `julianday('now')` | No such reads found in the relevant product code |
| Filesystem timestamps and argumentless `time.localtime()` in audit-summary code | Unpatched; neither determines the tested reservation deadlines |

`patch.object(time, 'time', …)` changes the shared module attribute, so these modules see the same clock. `addCleanup(patcher.stop)` restores it on assertion failure; the nested overdue-clock patch also restores correctly. No frozen-clock test starts the daemon thread used by the separate stop test.

The simulated wall-clock advance does not advance monotonic maintenance time. That differs from ordinary elapsed time, although wall-clock adjustments can produce such divergence in production. It is adequate for these short reservation-ordering checks, but does not verify maintenance cadence or elapsed execution time. The second simulated idle advance occurs immediately before stopping the loop, so no subsequent maintenance pass is tested.

No other reservation in `test_service_fixes` retains the same “must still be open after disk work” dependency: the failing-expiry test deliberately waits until overdue, and slower storage only strengthens that condition; the deadline-floor test patches time before measuring. Other real-time connection and shutdown assertions remain separate timing sensitivities.

The `--init` change preserves test selection, root execution and identity switching. `base.py` and its optional-test exclusions are unchanged; permissions, secrets, triggers, image and mounts are unchanged. Init becomes PID 1, forwards signals to its immediate child and reaps adopted zombies; ordinary child exit status remains propagated through the existing `pipefail` pipeline. It does not guarantee signal forwarding to every descendant. These semantics match [Docker’s documentation](https://docs.docker.com/reference/cli/docker/container/run/#specify-an-init-process) and [Tini’s documentation](https://github.com/krallin/tini#understanding-tini). The Mail comment is correct: `control/ci/mail/run.sh:27` starts the container with `sleep infinity`, and `:32` invokes `test.sh` through `docker exec`.

The revised `mark_session` explanation matches `usage._session`: it examines at most four process levels, passes the recognized shell-wrapper names, stops at the first non-shell and never considers PID 1. The precondition checks the test process’s mark, not the intervening hook ancestry. The new conditional init hint is appropriate.

Final `git diff` and staged diff were empty. `git status` showed only the same pre-existing untracked `reviews/control-idle-loop-timing/` directory. No tracked files were changed, committed or pushed; no files over 500 MB remain in `.work/`.

CHANGES-NEEDED