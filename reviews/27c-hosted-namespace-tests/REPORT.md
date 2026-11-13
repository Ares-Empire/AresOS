Brief: `briefs/27c-hosted-namespace-tests.md` (empire board brief 284). Builder: a Claude agent (Opus 5.5). Review: a fresh Codex context.

**Note:** `reviews/27c-hosted-namespace-tests/REPORT.md` is not committed yet. The agent harness refused to let the builder subagent write a `.md` report file. The report's full text is below, ready to commit as that file.

---

# 27c report: the hosted checks run the owner tools' namespace tests

## Done

- `.github/workflows/os-image.yml`, job `regressions` only: one new step, `Allow unprivileged user namespaces on disposable runner`, right before `Run regression and syntax checks`:
  ```yaml
  - name: Allow unprivileged user namespaces on disposable runner
    run: |
      sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0
      unshare -Urm true
  ```
  A comment above it says why. The tests' `entry_run` (`os/tests/test_owner_update.py`) runs `unshare -Urm` and skips when the namespace marker never prints. The runner's message was `unshare: write failed /proc/self/uid_map: Operation not permitted`. That is Ubuntu 24.04's AppArmor restriction, which creates the namespace but takes away its capabilities. `kernel.unprivileged_userns_clone` was not the cause: when it blocks, `unshare` itself fails. So only the AppArmor sysctl is set. `unshare -Urm true` makes the step fail if a later runner image still refuses, so the tests can't go back to skipping without anyone noticing. No other job, permission, trigger, condition or timeout changed.
- `os/manifest/ci/16/pending-rebind.json`: `python3 reviews/27-first-update-release/rebind.py pending "27c: ..."` recorded the workflow's new checkout bytes (`.github/workflows/os-image.yml`, sha256 `0e2ca79188fd51b21537b59f7376780f9d6393abd0a2939eb52a8ccca0187732`, was `e85e522b…`) and added the note to `changes`. The other three waiting rows are unchanged.
- No test changed. The only test that pins the workflow's bytes is `test_checkout_sources`, which checks them against the waiting list. Its failure after the edit (`Checkout source binding mismatch: .github/workflows/os-image.yml`) was fixed by the `rebind.py pending` record, as the brief asks. No test pins the `regressions` job's step list.

## Verified

- Local (laptop, `nice -n 10 python3 -m unittest discover -s os/tests -p '<module>.py'`), before and after the change:
  - `test_ci_api_permissions` 4 OK
  - `test_ci_step_environment` 4 OK
  - `test_checkout_sources` 5 OK (1 failure after the workflow edit and before `rebind.py pending`, as expected)
  - `test_owner_step_limits` 4 OK

  `test_owner_update` was not run locally (it must not run on this laptop).
- Hosted run before: 43439396623 (`checks_only`, 27b's branch, with `test_owner_update.py`, `os/owner-tools/` and `common.py` byte-identical to this branch): **Ran 933 tests, OK (skipped=136)**. All 136 skips read `no unprivileged user and mount namespace here: unshare: write failed /proc/self/uid_map: Operation not permitted`. The brief's run 43468641559 is on 22c's branch, which has 36 more tests: 969 tests, the same 136 skipped.
- Hosted run after: **43470821960** (`gh workflow run "OS image" --ref pkg/27c-hosted-namespace-tests -f checks_only=true`, head `63158f0b`), conclusion success. The new step printed `kernel.apparmor_restrict_unprivileged_userns = 0` and `unshare -Urm true` passed. Test step: **Ran 933 tests in 613.263s, OK**: 0 skipped, 0 failures, 0 errors. **All 136 previously skipped namespace subtests now run and pass.** No test in the log says skipped, FAIL or ERROR. All 28 `ToolsUpdateTest` methods appear in both runs.

## Not verified

- Nothing needs a human in the game. The rehearsal job's own suite run (`Qualify tools, ...`) still runs on a runner without this step, so the namespace tests still skip there. That job is out of scope.

## JUDGMENT-CALL

- None for the owner. A small builder's call: the step also runs `unshare -Urm true`, so it fails loudly instead of letting the tests skip again without notice. The alternative was the sysctl alone, which would let them skip silently on a future runner image. Dropping the line later is a one-line change.

## PLAN-GAP

- The brief's acceptance says the diff shows "only the files named above". `os/manifest/ci/16/pending-rebind.json` is not named, but the `rebind.py pending` step the brief requires writes it, so it is in the diff on purpose.
- The brief's baseline run (43468641559, 969 tests) is from another branch. The same-code baseline is 43439396623 (933 tests, 136 skipped), given above.

## Open questions

- **Time limit headroom:** the `regressions` job has `timeout-minutes: 15`. With the namespace tests running, it took 10 min 47 s (17:14:35 to 17:25:22), and the test step took 613 s. Before, the job took 8 min (43439396623) and the test step 425 s. About 4 minutes are left. A slower runner or a growing suite could reach the limit. I did not change the limit, because the brief allows only the one step. Should the integrator raise it in a follow-up?
- Security note for the reviewer: the sysctl turns off the AppArmor user-namespace restriction for the rest of this disposable job, which already has `sudo` and runs only this repo's code with `contents/packages/actions: read`. The runner is thrown away after the job.

## After the build (integrator)

The job took 10 min 47 s of its 15-minute limit once the 136 tests ran, so the integrator raised the checks-only job's `timeout-minutes` from 15 to 25. Nothing else in the job changed; the workflow's row in the waiting list was refreshed.
