# Step 1d, part 2, fix 2: verification

## Local checks

Scratch and logs: `.work/28a-fix2/`; portable Node from `.work/pkg28a-0a/`.
Suites ran one at a time; no local browser or owner-profile access.

```sh
.work/pkg28a-0a/node-v22.15.0-linux-x64/bin/node --test control/chrome_tests/*.test.mjs
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/.work/28a-fix2/tmp" PYTHONPATH=control:control/chrome_tests python3 -m unittest \
  test_questions test_policy test_engine test_doing test_going test_operation_projection \
  test_field_descriptions test_efficiency test_acting_references
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/.work/28a-fix2/tmp" PYTHONPATH=control:control/chrome_tests python3 -m unittest \
  test_qualification_fixture.ShippedHistory.test_this_process_starts_chrome_from_the_fixture_runtime \
  test_qualification_fixture.ShippedHistory.test_a_fixture_runtime_is_shared_by_build_and_rewritten_only_when_it_differs \
  test_qualification_fixture.ShippedHistory.test_the_real_shipped_copy_is_a_valid_record_chrome_trusts \
  test_qualification_fixture.ShippedHistory.test_the_browser_harness_installs_the_fixture_runtime_before_its_first_engine \
  test_qualification_fixture.ShippedHistory.test_a_held_record_extending_shipped_history_acts_and_an_uncovered_major_stays_conservative \
  test_qualification_fixture.ShippedHistory.test_every_chrome_test_module_that_starts_a_chrome_imports_test_engine
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control python3 control/generate.py --check
git diff --check
```

- Final Node: **626/626 pass**, no fail/cancel/skip/todo, **55,586.228194 ms**.
  First full attempt had two qualification-reader failures: the new encoder was eager
  in a double without TextEncoder. Fixed by initializing it only when hashing; focused
  qualification-reader/fingerprint **14/14 pass**, then the full suite above passed.
- Python: **200 tests in 60.411s, OK**; qualification-fixture subset **6 in 0.865s, OK**.
  Its other two tests invoke `test_state_fixes` internally, so they remain for hosted
  CI under the explicit local `test_state_*` ban. No test was changed or marked skipped.
  No `test_fault_surface` or state test ran locally. Synthetic negative efficiency
  tests deliberately print EFFICIENCY MISS lines; they are not browser misses.
- New conservative F4 double: **12,664 bytes** (it is not the real browser measurement).
  Replayed the actual external artifact's **13,349-byte** approval through the base:
  accepted; restoring Country's full options to the same facts gives **56,144 bytes**
  and `asking_input_too_large`. The ordinary F4 double still prints **7,365 bytes**.
  An initial new-double assertion counted a fieldset among affected fields; corrected
  the double to match the native 26-field list, then it passed.
- Generator: **Generated artifacts match definitions**. Changed JavaScript `node --check`
  and Python AST parse: clean. `git diff --check`: exit 0, no output. Instructions remain
  **2,798/2,800**. `.work/` files over 500 MB: **none** (`find .work -type f -size +500M`).


## Failure logs read

Read both previous runs with `gh run view <id> -R Ares-Empire/AresOS --log-failed`,
and all nine failed jobs with
`gh api repos/Ares-Empire/AresOS/actions/jobs/<job>/logs --allow-escape-sequences`.
Scratch: `.work/28a-fix2/`; the failure index is `failure-index.txt` there.

| Run | Failed jobs |
|---|---|
| 44491713756 | latency 135448895527; fixtures 135448895899 / 135448895940; aggregates 135484347611 / 135484347790 |
| 44491718224 | pairs 135448994286 / 135448994331; combines 135477540121 / 135477540288 |

The actual failures are F3's efficiency median, conservative F4's old size
assertion, and the empty taken-page fixture's loss refusal. The aggregate and
combine jobs require the missing successful recheck2 shard. Their checks were
kept intact. Latency details: [LATENCY-FIX2.md](LATENCY-FIX2.md).
