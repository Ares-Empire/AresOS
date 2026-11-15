# Review 1: PR #61, control hooks accept input fields they don't read

Verdict: SAFE

Reviewer: a fresh Claude agent (Opus), not the builder. Reviewed head `d697c45c` against `origin/main`.

## What I checked

- `hooks.py` against `common.validate` / `strict_json_loads` / `WIRE_LIMIT`, `launch.py`, and the managed hook commands
  (`boundary_policy.py:36`, `settings/managed-hooks.json`).
- Anthropic's hooks reference (read 2026-11-14). Every hook gets the common fields: `prompt_id` (missing until the
  first user input), `scratchpad_dir`, `effort` (an object), and `agent_id`/`agent_type` in subagents. `Stop` also gets
  `background_tasks` and `session_crons` (arrays). `stop_hook_active` is "true when Claude Code is already continuing
  as a result of a stop hook". Claude Code allows at most 8 consecutive continuations, and the count resets each time
  Claude calls a tool. A Stop hook that exits 2 sends its stderr to Claude as the reason to continue. Hooks for the
  same event run in parallel.
- Why the field list was closed: it came in with brief 19's review-fixes round 15 (PR #9; `briefs/19-review-fixes-15.md`
  points 3 and 4, `reviews/19-mail/SECURITY-REVIEW-7.md`). That round had two aims: every *service* envelope and
  payload is checked against an explicit schema before dispatch, so nothing unchecked reaches the journal, and every
  ingress gets raw decoder bounds. The PR keeps both. The hook sends the service only `control_pending` with a fixed
  `{}` and never forwards its input. Size, depth, number range, UTF-8 and Unicode scalars, the BOM check and duplicate
  keys at any depth still apply to the whole input, unknown fields included
  (`test_hook_raw_bounds_refuse_before_pending_read`, `test_config_and_hook_refuse_before_daemon_or_pending_call`, whose
  `{"nested":{"x":1,"x":2}}` case now really tests the strict decoder). **Nothing that reason protected is lost.**
- Tests: the requested command, `-k hook -k stop_failure` over `test_ingress_bounds` and `test_strict_json`, runs
  5 tests, all OK. In a scratch copy:
  - Old `hooks.py` from `origin/main` with the new tests: 1 failure, 3 errors, which confirms the PR's claim.
  - Mutation, `is True` changed to a plain truthiness check: 3 failures (`stop_hook_active` `1`, `'true'`, `'yes'`).
  - Mutation, `isinstance(event, dict)` removed: the raw-bounds tests error.
- CI (`gh pr checks 61`, checked once): `hostile` passed; `containers` and `sweep` were still pending. These run the
  changed integration inputs, which need root and containers and can't run here.

## Answers to the questions

**1. Correctness of refusal and acceptance.** The hook still refuses:
- wrong types on the fields it types (exit 2, no service call);
- duplicate keys anywhere, and oversize, too deep, non-finite or out-of-range input (the parser fails, `event` stays
  `None`, exit 2);
- a non-object;
- a missing or mismatched `hook_event_name` (`validate` enum plus the launcher-event check).

It accepts everything the 2.1.319 reference documents: `prompt_id`, `scratchpad_dir`, `effort`, `agent_*`,
`background_tasks`, `session_crons` and `session_title` are all outside `EVENT`, so they are never type-checked.

No unknown field can change behaviour or reach output:
- `output()` reads only `hook_event_name` and `stop_hook_active`.
- `validate` recurses only into known keys, so its error paths name only known keys and never echo values.
- `JSONInputError` has a fixed message.
- The service call is fixed.

An unknown field still counts toward the 6 MiB total, as before. One gap remains, in finding 1: six fields the hook
never reads are still typed.

**2. The quiet `Stop` failure path.** `event` is reliable there:
- It is `None` until strict parsing succeeds, so a parse failure, a duplicate `stop_hook_active` or oversize input
  falls through to exit 2.
- A non-object fails `isinstance` and exits 2.
- `is True` matches only JSON `true`. A `stop_hook_active` that fails validation itself (`1`, `"true"`, `"yes"`) exits
  2, and tests cover this.
- The guard reads the parsed value directly, so the order in which `validate` hits a bad field doesn't matter.

The failure path is now exactly as strict as the normal path. With the service down, the normal path already went
through `Refused`, then `output()`, then `{}` once `stop_hook_active` was truthy. The only case where something seen
before is now unseen is finding 3. Outside it, the model still gets the failure feedback once (as the first block), and
the owner sees one "Stop hook error" instead of nine.

**3. Tests and README.** The tests are meaningful: they fail on the old code and catch both obvious mutations of the
guard. The README matches the code except for one overclaim (finding 2).

## Findings

### 1. Six fields the hook never reads are still type-checked, so the same kind of failure remains (should fix)

`control/aresos_control/hooks.py:13-18`

The comment says these are "the fields a hook may read". But the hook reads only `hook_event_name` and
`stop_hook_active`. `session_id`, `transcript_path`, `cwd`, `permission_mode`, `last_assistant_message` and `prompt`
are never read, never echoed and never sent anywhere. Their `maxLength: WIRE_LIMIT` adds nothing beyond the
whole-input bound. So the types protect nothing, but each one is a way for this bug to come back.

Concrete case: a Claude Code version (or a 2.1.319 code path the VM test didn't hit) sends
`"last_assistant_message": null` for a turn that ended without text, or `"transcript_path": null` for a session that
isn't persisted. That `Stop` input fails `validate`, so the service is never asked. The model gets
`AresOS hook failed …: hook.last_assistant_message: expected string` and one extra continuation in every such turn,
with no real reminder.

The new guard limits the damage to once per turn, so this is not blocking. Still, it is the class of failure this PR
exists to fix. The README's "fields it doesn't read are accepted and ignored" is also only half true while these keep
their types.

Suggested fix: type only the two fields the hook reads, and keep `additionalProperties: True`:

```python
EVENT = {'type': 'object', 'required': ['hook_event_name'], 'additionalProperties': True, 'properties': {
    'hook_event_name': {'type': 'string', 'enum': ['Stop', 'UserPromptSubmit']},
    'stop_hook_active': {'type': 'boolean'}}}
```

Then change the wrong-types test cases `prompt: []` and `session_id: None` into "accepted and ignored" cases. Also
change the `broken == 'input'` case of `test_stop_failure_blocks_once_and_honours_the_continuation_guard` to a
mismatched `hook_event_name`, so it still breaks the input.

### 2. The README claims more than the guard can do for input it can't parse (should fix, wording)

`control/README.md:262-263`

The README says "a failing hook never holds a turn open until Claude Code's own limit". That holds only when the input
parses as an object and `stop_hook_active` is exactly `true`. If the input doesn't parse, the guard can't be read and
`Stop` still exits 2 on every stop until Claude Code's cap. Two plausible ways that happens:
- Claude Code cuts `background_tasks[].description` / `.command` or `session_crons[].prompt` at 1000 characters (per
  the reference) in UTF-16 code units, splits an emoji, and so sends an escaped lone surrogate, which the strict
  decoder refuses everywhere.
- The input is over 6 MiB.

Keeping that path fail-loud is the right default. Only the sentence overclaims.

Suggested fix: write "when the input parses and `stop_hook_active` is already `true`, it ends quietly, so a failing
hook blocks a stop once". Optionally add a test that unparseable input with `"stop_hook_active":true` still exits 2,
which pins down the intended limit.

While editing: "`Stop` keeps its explicit service-failure reminder … with exit 2" was already slightly wrong before
this PR. The service-failure reminder is a `decision: block` JSON with exit 0; only the failure path exits 2. Also,
line 263 is about 150 characters wide while the rest of the section wraps at about 85.

### 3. The guard is "a stop hook continued", not "this hook blocked" (note, no change needed)

`control/aresos_control/hooks.py:56-59` (and the existing `hooks.py:29`)

`stop_hook_active` turns true when *any* Stop hook continues the turn. Brief 18d dropped `allowManagedHooksOnly`, so
the owner's own Stop hooks and `/goal`'s prompt hook run alongside the AresOS hook. Calling a tool resets Claude
Code's cap counter but not `stop_hook_active`.

Scenario:
1. At the first stop, the AresOS hook succeeds with nothing pending, and the owner's own Stop hook blocks.
2. The model keeps working, and an operation becomes held.
3. At the next stop the AresOS hook fails.

Before this PR, the model would have seen "AresOS hook failed; inspect pending work", up to Claude Code's cap. Now
the turn ends quietly.

This is exactly what the normal path already does in the same turn: with the service healthy and work now held, it
returns `{}`. So the PR makes failures as strict as successes, not weaker than they were by design. The next
`UserPromptSubmit` reminder and service expiry stay the safety net, as the README says. I'm only recording it in case
the guard's design is reconsidered later. A per-turn "AresOS already blocked" marker would need state, and that's out
of scope here.

### 4. The integration-test changes are proven only by CI (note)

`control/tests/test_integration.py:372,414`

The `prompt_id` additions are right and keep the two installed-launcher paths covered. They need the container suite,
which was still pending when I checked. Merge only once `containers` and `sweep` are green. The real proof is the next
`check_build=control` run of `pkg/18c-image`, as the PR says.
