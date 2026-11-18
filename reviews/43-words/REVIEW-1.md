Codex gpt-6-astra, 2026-11-18. Ran 4 CLI/reserved-word tests and 124 oracle unit tests—all passed; generator `--check`, diff checks, repo-wide searches, refusal/canonical-routing comparisons and an in-memory shortcut mutation check. Read AGENTS.md, report and full diff. `gh pr view 109` could not connect; read the description through GitHub’s connector. Full oracle proof was not run.

1. **SHOULD-FIX — [os/ci/control/actions.py:370](../../os/ci/control/actions.py#L370): missed executable caller.** `answered(cli('ares', 'log'))` still invokes `/usr/bin/aresos log` and requires success. It now exits 2, breaking the image’s `control-entry-points` check. Change it to `cli('ares', 'control', 'log')`. Correct the report’s claim that no OS callers remain ([reviews/43-words/REPORT.md:31](../../reviews/43-words/REPORT.md#L31)).

Otherwise, routing is correct: `log` gets exactly the unknown-word refusal. Canonical arguments, `--input`, `--json`, paging, cursors and restore-lock handling retain their existing paths. `newest` is reserved; `log` is neither reserved nor a top-level word. Restoring the shortcut makes the new regression test fail.

Control/Mail callers, generated help and current command documentation migrated. Managed CLAUDE.md and server instructions contain no shortcut. Remaining references are intentional rejection tests, historical briefs/reviews, oracle labels/assertions/fixtures, and the historical-view mentions in `docs/control/TOOLS-HANDOFF.md:41` and `:214`; see the remaining-reference inventory (`remaining-shortcut-references.txt` in the reviewer's scratch folder `.work/review-43/`, not committed). The OS call above is the remaining active caller.

**No pinned known-gap keys should change**, including `aresos log.*`: [compare.py:325](../../control/owner_state_oracle/compare.py#L325) retains the label and `control_log` action. More precisely, the sweep still calls the engine directly; only its comment changed. The channel test now invokes `control log`. No unrelated changes found.

No tracked changes remain. The pre-existing untracked `reviews/43-words/REVIEW-1.md` was untouched.

CHANGES-NEEDED