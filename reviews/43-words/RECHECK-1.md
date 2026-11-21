Codex gpt-6.1-sol, 2026-11-18.

1. **SHOULD-FIX — [reviews/43-words/REPORT.md:33](../../reviews/43-words/REPORT.md#L33): proof claim is premature.** The only branch OS image run, [44296503915](https://github.com/Ares-Empire/AresOS/actions/runs/44296503915), is still running; its Control VM step has not run. Replace “proves the entry-point check” with pending verification until that check passes. The paragraph’s caller correction is accurate.

The code fix at [os/ci/control/actions.py:370](../../os/ci/control/actions.py#L370) is correct: `cli('ares', 'control', 'log')`. `answered()` returns the same JSON envelope, and the unchanged summary still reads `log['data']['items']`. Both CLI tests and a mocked helper-to-CLI check passed.

Repository search found no remaining active shortcut callers. Intentional rejection calls remain at [control/tests/test_cli.py:13](../../control/tests/test_cli.py#L13) and [control/tests/test_integration.py:392](../../control/tests/test_integration.py#L392). Other matches are the excluded oracle labels and historical references.

CHANGES-NEEDED