Codex gpt-6-astra, 2026-11-17. Ran `PYTHONPATH=.:tests python3 -m unittest test_service_fixes.IdleLoop` twice from `control/`: both failed with nine setup errors because the sandbox denies Unix socket binding. Scratch runs using REVIEW-1’s inert pipe listeners passed 9/9 twice. Reran all ten mutations: nine killed; conditional 250 ms sleep survived as expected.

| REVIEW-1 finding | Closed? | Where / evidence |
|---|---|---|
| 1 — SHOULD-FIX: missing independent lateness bound | **Yes** | [test_service_fixes.py:420](../../control/tests/test_service_fixes.py#L420), [test_service_fixes.py:442](../../control/tests/test_service_fixes.py#L442). A 250 ms margin fails both: approximately `0.252 > 0.012` and `0.650 > 0.41`. |
| 2 — NIT: real monotonic idle budget | **No; accepted limitation** | [test_service_fixes.py:443](../../control/tests/test_service_fixes.py#L443). Truthfully documented in PR section 1 and [REPORT.md:48](../../reviews/control-idle-loop-timing/REPORT.md#L48). |

The bounds fit their fixtures: correct timeouts are approximately 7 ms and 405 ms, each leaving 5 ms of slack. They cap requested lateness at 10 ms independently of the product constant; exact formula assertions remain. The conditional-sleep survivor correctly reflects the documented exclusion of real elapsed-time responsiveness ([REPORT.md:40](../../reviews/control-idle-loop-timing/REPORT.md#L40)).

`51b38ff8..9a77450f` changes only these assertions/comments and adds the report. The live PR description otherwise matches its saved predecessor, including attribution and session link.

GitHub CLI could not connect; the connector supplied the [first-attempt log](https://github.com/Ares-Empire/AresOS/actions/runs/44149204377/job/134272538966). Its 11 mount-tree differences contain **only device-number changes**. The comparison at [native.py:252](../../control/boundary/native.py#L252) and its build inputs are unchanged by this PR: an unrelated harness failure.

No new findings. No tracked changes, commits or pushes; pre-existing untracked file untouched. Scratch evidence: `.work/recheck-97/`. No files over 500 MB in `.work/`.

SAFE