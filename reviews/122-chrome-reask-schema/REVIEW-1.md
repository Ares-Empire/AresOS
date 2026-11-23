## Review of AresOS PR #122 (fix/chrome-reask-schema @ 0eecff25)

Reviewer: a fresh Claude Opus 5.5 agent for the lead linux-tools, 2026-11-19; not the builder.

The fix is right. Both tools can return `approval` and `state` next to `operation`, main's schema rejects that, and the PR now declares exactly those two optional fields while keeping `additionalProperties: false`. No other Chrome or Mail tool returns undeclared fields. I found 4 NITs and nothing that blocks the merge. PR CI was still pending when I looked.

### What I read
- AGENTS.md, the PR body, and `git diff origin/main...0eecff25`: 4 files, +183/−2. The branch is directly on top of current origin/main (dddc7fcc).
- The shared result schemas in `control/aresos_control/definitions.py`: `obj`, `OP_RESULT`, `PREPARED_RESULT`, `RESULT`, and how `Action.tool()` builds `outputSchema`.
- `control/aresos_control/chrome/definitions.py`.
- The re-ask paths in `control/aresos_control/chrome/adapter.py`: `changed_typed_fields`, `changed_destination`, `changed_compose`, `revalidate`, `execute`, `steps`, `call`.
- In `control/aresos_control/engine.py`: `reserve`, `submit` and the dispatch code.
- `control/aresos_control/proxy.py`, which sends the whole envelope as `structured_content`.
- `control/response_checks.py`.
- Mail's definitions, `onboarding.py` and `revalidate`, and testapp's `revalidate`.

### What I ran
All runs used PYTHONDONTWRITEBYTECODE=1 and TMPDIR under `.work/review-122/`.
- **Generator and ask rules:** `PYTHONPATH=control python3 control/generate.py --check` printed "Generated artifacts match definitions". `control/settings/ask-rules.json` has the same sha256 as on main. `git diff --check` is clean. The tracked tree is unchanged (`git status` is empty).
- **New test alone:** OK.
- **Mutation** (OP_RESULT restored for both tools, in a `git archive` copy at `.work/review-122/mut`): FAILED, 5 subtests, each "result.data: unknown fields are refused". That matches the PR's claim. The trusted send with `boundary=True` also fails when run on its own (see NIT 3).
- **Which paths the test drives:** I wrapped the adapter's three re-ask methods and recorded who called them. There were 10 calls, and `changed_destination`, `changed_compose` and `changed_typed_fields` were each reached from both `revalidate` (the service's recheck) and `execute` (the extension's final check). No re-ask dispatched anything.
- **The four modules** (`test_questions test_policy test_engine test_qualification_fixture`): branch 93 OK, main 92 OK. There were no `boundary_not_installed` failures in these modules.
- **Independent check with jsonschema Draft 2020-12:** I ran `response_checks.VALIDATORS` against every `Engine.request` reply.
  - The same four modules on main: 20 mismatches, all `chrome_submit` "('approval', 'state' were unexpected)".
  - The same four modules on the branch: 0 mismatches in about 330 checked replies across 17 Chrome tools.
  - 8 more modules on the branch, also 0 mismatches: `test_sites`, `test_unit`, `test_exclusions`, `test_owner_confirm`, `test_state_fixes`, `test_committed`, `test_full_disk_reads`, `test_restore_lock`, `test_bridge`.
  - I left out `test_storage` and `test_fault_surface`. Their sweeps start separate Python processes that my script could not check; I stopped those runs by PID and none are left running.

### The checks the brief asked for
1. **The claim is true.** The adapter's `changed_destination` ([adapter.py:540](../../control/aresos_control/chrome/adapter.py#L540)) and `changed_compose` ([adapter.py:553](../../control/aresos_control/chrome/adapter.py#L553)) add `engine.reserve(...)`, which returns exactly `{approval, state: 'reserved'}`.
   - These replies reach the caller in two ways: `engine.submit` returns the `revalidate` replacement as it is ([engine.py:356-358](../../control/aresos_control/engine.py#L356)), or adds it after a `NothingLeft` stop ([engine.py:403](../../control/aresos_control/engine.py#L403)).
   - `chrome_submit_trusted` goes through the same `engine.submit` path ([adapter.py:895-907](../../control/aresos_control/chrome/adapter.py#L895)).
   - Main declared only `{operation}`, so those replies were outside its schema.
2. **The declaration is exact enough.** `REASK_RESULT` ([chrome/definitions.py:12](../../control/aresos_control/chrome/definitions.py#L12)) requires `operation`, makes `approval` and `state` optional, and keeps `additionalProperties: false`. Only `submit` and `submit_trusted` change; `drop` stays `OP_RESULT`. Nothing besides the generated schema docs reads `Action.result`, so behaviour, replies and ask rules are unchanged.
3. **No other tool is outside its schema.** Every place a `reserve(` result is merged into a reply:
   - [adapter.py:418](../../control/aresos_control/chrome/adapter.py#L418) feeds `read_typed_fields`, which declares an open object.
   - [adapter.py:818](../../control/aresos_control/chrome/adapter.py#L818) (`steps`) feeds the free actions' `followups`, which are open objects. `execute` throws that return value away.
   - [adapter.py:953](../../control/aresos_control/chrome/adapter.py#L953) feeds the asking actions (click and the others), which are open objects.
   - `prepare_read_typed_fields` returns `reserve` unchanged, which is exactly `PREPARED_RESULT`.
   - Mail only uses `reserve(...)["approval"]` internally during onboarding, and Mail's and testapp's `revalidate` return nothing. Neither merges a fresh approval into a reply.
4. **The new test is real.** It drives the real adapter and engine with the existing test fakes, validates the whole reply with `common.validate` against each tool's `outputSchema`, and fails with the old schema.
5. **Test runs:** reported above.

### Findings
1. **NIT:** [chrome/definitions.py:12](../../control/aresos_control/chrome/definitions.py#L12) makes `approval` and `state` optional separately, but the adapter always returns both or neither. A stricter form would be `{'anyOf': [OP_RESULT, obj({**OP_RESULT['properties'], **PREPARED_RESULT['properties']})]}`. `anyOf` is allowed by `generate.py`'s `schema_check`, and `mail_notice_ack` already uses it ([mail/definitions.py:119](../../control/aresos_control/mail/definitions.py#L119)). The current form is harmless because it accepts every real reply.
2. **NIT, follow-up:** the Chrome tests never install `response_checks.check_responses` ([control/response_checks.py](../../control/response_checks.py)), which `control/tests` and `mail_tests` use. That is why 20 existing re-ask replies went unchecked on main. Installing it, for example in `test_engine.Operations`, would check every Chrome reply against its schema; on this branch the schema part would pass. One catch: its wire round-trip assert would trip on an existing tuple in `chrome_read` `data.document` (`test_taken_read_preserves_document_and_first_input_commits_reload_before_staling`, the same on main). It encodes to the same JSON, so it is harmless.
3. **NIT:** in [test_questions.py](../../control/chrome_tests/test_questions.py) the trusted-send subtest runs both boundary cases inside one `subTest`. Under the mutation, the first failure hides the `boundary=True` case. I checked separately that it fails on its own. This only affects how failures are reported.
4. **NIT, already on main, not caused by this PR:** at the extension's final check, if preparing the fresh question refuses, the operation is recorded as `unknown` even though nothing was dispatched.
   - Example: the target link changed to `file:///…`. The `Refused` escapes `execute`'s handler ([adapter.py:616-631](../../control/aresos_control/chrome/adapter.py#L616)) and reaches the general `except Exception` ([engine.py:390-393](../../control/aresos_control/engine.py#L390)).
   - At the service's recheck, the same case returns ok=false with the operation `failed`.
   - My scratch probe (`.work/review-122/probe_disallowed.py`, not committed) gave identical results on main and the branch, with 0 dispatches. It is conservative, since it tells Claude never to retry; at most a known limit.

SAFE
