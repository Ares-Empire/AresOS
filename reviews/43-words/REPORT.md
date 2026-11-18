# Control for package 43

## Done

PR [#109](https://github.com/Ares-Empire/AresOS/pull/109), branch `control/43-words`, based on `7417c19a`. Fetched origin before inspection. Lead: linux-tools; OS dispatcher belongs to linux-aresos. This implements board #199, package 43 design D12, agreed between those sessions on 2026-11-13 and 2026-11-15.

Implementation commit: `64c34126` — Reserve newest and remove the top-level Control log shortcut. Every commit ends with `Built-by: gpt-6.1-sol`.

Every changed file and its purpose:

| File | Change |
| --- | --- |
| `control/tests/test_reserved_words.py` | Add `newest` to the owner-tools reserved set; remove `log` from Control's top-level words and require its absence in generated help. |
| `control/aresos_control/cli.py` | Remove the shortcut rewrite and its error-message advertisement. `aresos log` exits 2 through the usual parser error; canonical `aresos control log` keeps its existing path. |
| `control/tests/test_cli.py` | New rootless routing regressions: shortcut and unknown word refuse before contacting a service; canonical log preserves arguments and result. |
| `control/tests/test_integration.py` | Use canonical log, assert its successful exit, and assert the former shortcut exits 2. |
| `control/tests/test_owner_state_channels.py` | Use canonical log for every installed-channel audit page. |
| `control/mail_tests/test_review_fixes.py` | Change its embedded CLI subprocess to canonical log. |
| `control/mail_tests/test_review_fixes_7.py` | Change the hostile-summary CLI subprocess to canonical log. |
| `control/mail_tests/test_owner_state_sweep.py` | Update the explanatory command comment; preserve the pinned comparison key. |
| `control/tests/test_owner_state_oracle.py` | Update the explanatory command comment; preserve historical view/key literals. |
| `control/aresos_control/mail/definitions.py` | Update move/copy/rename descriptions that direct callers to the terminal log. |
| `control/generate.py` | Advertise the canonical log command in generated usage. |
| `control/generated/cli-help.txt` | Regenerated canonical log usage. |
| `control/generated/mail-tools.json` | Regenerated move/copy/rename descriptions. |
| `control/README.md` | Update all three command references. |
| `docs/control/TOOLS.md` | Regenerated descriptions from the Mail catalogue. |
| `docs/design/CONTROL.md` | Update four command references in current design guidance. |
| `reviews/43-words/REPORT.md` | This report, verification limits, instruction counts and CI evidence. |

`control/aresos_control/definitions.py`'s `control_log` action, input/result schemas and implementation are unchanged. The oracle's `control/owner_state_oracle/compare.py` comparison label remains `aresos log`; its direct `control_log` call is unchanged. Matching view literals, pinned JSON data and assertions retain those historical keys so this task does not re-pin the oracle.

Searched the repository for the literal shortcut and inspected Python CLI invocations, including the embedded Mail subprocess scripts. The builder found no `aresos log` caller under `os/`, but REVIEW-1 found one: 18c's check 3 (`os/ci/control/actions.py:370`, `cli('ares', 'log')`). The lead changed it to `cli('ares', 'control', 'log')`; an OS image `check_build=control` run on this branch proves the entry-point check. Current owner documentation under `docs/` is updated, except `docs/control/TOOLS-HANDOFF.md`, explicitly left to the lead. Frozen historical briefs, review records and evidence retain the command spelling they recorded; they are not current callers or owner guides.

Instruction counts before → after: server strings use `len(instructions_for(app))` (the generated text files add one final newline); managed CLAUDE.md uses `len(OWNER_INSTRUCTIONS)` exactly as written.

| Instructions | Before | After |
| --- | ---: | ---: |
| Chrome | 4,093 | 4,093 |
| Control | 1,762 | 1,762 |
| Mail | 2,536 | 2,536 |
| Test app | 1,762 | 1,762 |
| Managed `control/settings/CLAUDE.md` | 422 | 422 |

None contains the shortcut, so no server instruction or managed CLAUDE.md change was needed. All server strings remain within 4,096 characters.

## Verified

Commands below ran from `control/` unless stated otherwise, on the laptop's Python 3.14. Local output is under `.work/43-words/` where noted.

- `PYTHONPATH=.:tests python3 -m unittest test_reserved_words test_cli`: `Ran 4 tests`, `OK`.
- `PYTHONPATH=.:tests:mail_tests python3 -m unittest test_owner_state_oracle`: initial attempt printed `Ran 124 tests`, `FAILED (errors=5)` because `.work/` did not exist. Created `.work/43-words/` and repeated the same command: `Ran 124 tests`, `OK` (`owner-oracle.txt`). No assertions changed.
- `PYTHONPATH=.:chrome_tests python3 -m unittest test_questions.Questions.test_fixes_b_server_instructions_fit_the_native_cli_limit`: `Ran 1 test`, `OK`.
- From repository root, `PYTHONPATH=control python3 control/generate.py`: `Generated tools, help, reference and ask rules`.
- From repository root, `PYTHONPATH=control python3 control/generate.py --check`: `Generated artifacts match definitions`.
- From repository root, `git diff --check`: exit 0, no output.
- Parsed the two changed Mail test files with `ast.parse` and compiled their embedded CLI Python strings with `compile`: both printed `compiles`.
- Measured `len(instructions_for(app))` for all apps and `len(OWNER_INSTRUCTIONS)` before and after; counts above.

Hosted Control base output: `Ran 392 tests in 236.047s`, `OK`; it explicitly prints `ok` for both new CLI unit tests and `test_cli_generated_help_admin_and_today_log`, including the installed refusal/canonical-log assertions. Retrieved with `gh run view 44272104067 --log` into `.work/43-words/base-ci.txt`.

All six workflows passed on the first automatic CI round, with no failures or reruns. The table records that round for implementation commit `64c34126`. All runs were watched with `gh run watch <id> --exit-status --interval 60`. No workflows were dispatched.

The report-only commit triggers a second automatic round. Its commit ID and final run IDs/results are recorded in the PR description and completion message: another commit solely to record those IDs would trigger a third round. No further code changes or test reruns are planned after that second round.

| Workflow | Run ID | Result |
| --- | --- | --- |
| Repo privacy | [44272104008](https://github.com/Ares-Empire/AresOS/actions/runs/44272104008) | Success |
| Control base | [44272104067](https://github.com/Ares-Empire/AresOS/actions/runs/44272104067) | Success |
| Control Mail | [44272104028](https://github.com/Ares-Empire/AresOS/actions/runs/44272104028) | Success (all 12 jobs) |
| Control Chrome | [44272104025](https://github.com/Ares-Empire/AresOS/actions/runs/44272104025) | Success (all 28 jobs) |
| Control boundary | [44272104058](https://github.com/Ares-Empire/AresOS/actions/runs/44272104058) | Success |
| Control Chrome qualification | [44272104068](https://github.com/Ares-Empire/AresOS/actions/runs/44272104068) | Success (all 34 jobs) |

## Not verified

- Local Mail attempt: `PYTHONPATH=.:mail_tests:tests python3 -m unittest test_review_fixes test_review_fixes_7 test_owner_state_sweep` printed `Ran 35 tests`, `FAILED (failures=8, errors=20)` (`mail-local.txt`). Twenty setup errors were missing synthetic-server certificate files; eight sweep failures returned `boundary_not_installed` because the disposable container's managed settings are absent. Seven tests passed. Did not install fixture policy or mail servers on the host. CI provides their isolated environment.
- Did not run root-only `test_integration` or `test_owner_state_channels` locally: setup changes ownership and writes the disposable installed prefix and `/run/user` fixtures. The normal Control base workflow covers the integration module. The owner-channel case is explicitly optional in `control/ci/base.py`; its workflow is dispatch-only, and was not dispatched per this task's rule, so that installed-channel case remains unverified here.
- No mod build, client tests, screenshots or real account test: this changes only Control command routing, words and documentation. No human in-game check is needed for this change.

## JUDGMENT-CALL

`log` is **not** added to `RESERVED`: that set describes exactly the owner tools' words (which include `logs`, not `log`) and must match the OS dispatcher in package 43. It is removed from `CLI_WORDS`; help and routing tests enforce removal of the existing shortcut. Reserving it for the owner tools would create a word-set mismatch. Any future served app named `log` needs its own explicit design decision; this task adds none.

## PLAN-GAP

None in the requested implementation. The Mail fixtures and installed root-only checks require CI's disposable environment. Historical oracle labels intentionally remain stable as instructed.

## Open questions

None. No merge performed; the lead owns `TOOLS-HANDOFF.md` and OS integration.

Scratch inventory: no file over 500 MB remains under `.work/`; no large downloads were made. No Gradle process was started, and no Gradle stop command was run.
