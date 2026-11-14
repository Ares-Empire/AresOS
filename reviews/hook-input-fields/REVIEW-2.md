# Review 2: PR #61, re-check of 8624281b

Verdict: SAFE

Reviewer: the same fresh Claude agent (Opus) as review 1, not the builder. Scope: `git diff d697c45c..8624281b`, which
contains the fixes for review 1's two should-fix findings, and the hook tests.

## What changed and whether it holds

**Finding 1 (unread fields were type-checked) is fixed.** `hooks.py:13-17`: `EVENT` now types only `hook_event_name`
(a string in `Stop` / `UserPromptSubmit`, required) and `stop_hook_active` (a boolean), with
`additionalProperties: True`. Those are the only two fields `main` and `output` read. Nothing else changed:
- `WIRE_LIMIT` is still used for the bounded read.
- `obj` is still used.
- The guard (`is True` on the parsed dict), the strict decoder and the launcher-event check are untouched.

So a later Claude Code that sends `null` or another type for `session_id`, `transcript_path`, `cwd`, `permission_mode`,
`last_assistant_message` or `prompt` no longer breaks a turn. Nothing is lost: those fields were never read, never
echoed, never forwarded, and their per-field length bound only repeated the whole-input bound.

**Finding 2 (README overclaim) is fixed.** `control/README.md:257-266` now says what the code does:
- A hook reads only the two fields and checks their types.
- An unreachable service gives a `block` decision that says so (the `Refused` / `not ok` paths, then
  `service_unavailable`).
- Malformed input or the hook's own failure gives stderr with exit 2.
- Both block a stop once when the input parses and `stop_hook_active` is already true.
- Input that can't be parsed exits 2 at every stop, up to Claude Code's cap.

I checked every branch of `main` against this, and it is accurate. "Already true" correctly means the JSON boolean: a
`stop_hook_active` of `"true"` or `1` still exits 2, and a test shows it. The wrong "service-failure reminder … with
exit 2" phrasing from before this PR is gone too.

**Tests.**
- `test_hook_explicit_payload_schema_refuses_wrong_types` refuses these with exit 2 and no service call:
  - `stop_hook_active` `1` and `"true"`;
  - `hook_event_name` `7`;
  - an unknown event name (`SessionStart`);
  - an event name that doesn't match the launcher;
  - a missing `hook_event_name`.
- `test_hook_accepts_and_ignores_fields_it_does_not_read` now also sends the wrong types for unread fields
  (`session_id: null`, `transcript_path: 7`, `last_assistant_message: ["x"]` on `Stop`, `prompt: null` on
  `UserPromptSubmit`). It still requires one `control_pending` call, the reminder in the output, and no unknown values
  echoed.
- In `test_stop_failure_blocks_once_and_honours_the_continuation_guard`, the "input" break is now an event name that
  doesn't match the launcher, which is still a validation failure with the guard readable.

Runs:
- The requested command (`-k hook -k stop_failure` over `test_ingress_bounds` and `test_strict_json`): 5 tests, OK.
- In a scratch copy, `d697c45c`'s `hooks.py` with the new tests: the accept test fails on both events, so the new
  cases would catch a return of typed unread fields.
- In a scratch copy, the guard mutated from `is True` to plain truthiness: 3 failures, as before.
- `test_operations.test_changes_logged_and_pending_in_every_result_and_hooks` fails here with
  `boundary_not_installed` (no `/etc/claude-code/managed-settings.json`). That's the environment, not this change.

## Findings

No blocking or should-fix findings.

- **Note:** `control/README.md:266` is still 93 characters wide while the section wraps at about 85. Cosmetic.
- **Note (as in review 1, finding 4):** CI on `8624281b` was all pending when I checked once with `gh pr checks 61`
  (`hostile`, `containers`, `sweep`). The integration inputs carrying `prompt_id` are proven only there. Merge once
  they are green.
- Review 1's finding 3 (`stop_hook_active` is set by any Stop hook, so the guard matches the normal path rather than
  "this hook blocked") stands as a note. No change is needed.
