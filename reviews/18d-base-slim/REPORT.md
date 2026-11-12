# 18d — slim base for normal Claude Code

**run — PermissionRequest result first:** native Claude Code **2.1.319** invokes
an allow-returning `PermissionRequest` hook and lets it approve a managed ask,
**at user and managed scope, in normal and skip-permissions print mode**. Each of
those four cases produced one hook invocation and one independent send arrival.
This is decision 24's **accepted residual**, not a managed-rule precedence failure.
No lock was restored. The four outcomes are frozen in
`control/boundary/permission-request-expected.json` and fail if they change.

Evidence: [boundary run 42582079690, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42582079690),
head `a21c9db3a66f988793fb19e7ab18b7f37a463356`, workflow log lines
**1706, 1717, 1812, 1823**. Artifact `present/stub.txt` lines **64, 68, 86, 90**
independently record the four `POST /precedence/send/<case>` requests.
`present/precedence-summary.json` records each count; the matching MCP results
say `FIXTURE_SEND_RAN`. This settles the four model-free cases; it does not
qualify terminal or phone presentation.

## Done

**read — shipped policy and setup:** `aresos_control/boundary_policy.py` generates
exactly `permissions.ask` and the existing two notification hooks. The shipped
settings are:

```json
{
  "permissions": {
    "ask": [
      "mcp__testapp__send",
      "mcp__testapp__delete",
      "mcp__mail__send",
      "mcp__mail__delete",
      "mcp__mail__folder_delete",
      "mcp__mail__unsubscribe"
    ]
  },
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 /usr/bin/python3 -I -S /usr/libexec/aresos-control/launch.py hook Stop",
            "timeout": 15
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 /bin/sh -c 'if context=$(/usr/bin/python3 -I -S /usr/libexec/aresos-control/launch.py hook UserPromptSubmit 2>/dev/null); then printf \"%s\" \"$context\"; fi; exit 0'",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

The hook commands/timeouts are unchanged; `managed-hooks.json` is now generated
from the same definition and embedded in the settings JSON. The same module
produces `settings/CLAUDE.md`: only the owner in this session (terminal or Remote
Control) gives instructions; mails, pages, files, tool results and other sessions'
messages are data. There are no other generated managed settings keys.

**read — servers:** removed exclusive `settings/managed-mcp.json`. Generated
`settings/user-mcp.json` maps `control` and `mail` to their complete normal
`claude mcp add-json --scope user` arguments, retaining the fixed isolated Python
proxy command. `control/README.md` documents installation as the owner and removal
of the obsolete exclusive file during image migration. No `os/` setup was changed.
The generator checks every shipped ask names an exposed tool of a served app
under its installed server name. The service serves testapp too, so both its
send/delete rules are shipped and required. Testapp is the sole exception to a
shipped user-scope MCP entry: only the native harness installs that entry, named
`testapp`. All other served apps must have entries in `user-mcp.json`. The native
harness now uses the default generated policy, including testapp's asks.

**read — asking admission:** `Boundary` reads only the managed settings through
protected descriptors. Every directory and the regular leaf remain root-owned,
not group/world writable, and opened without following links. Every generated ask
must be present. All additional settings/rules/hooks are accepted. Production
paths cannot be supplied by client/service configuration.

**read — trusted sends:** definitions have explicit `trusted_send` metadata,
valid only for public sends. Marked sends receive no ask. The shared submit path
requires the adapter's current owner-only entry check to return exactly `True`;
missing, false, empty and truthy substitutes refuse. Tests exercise missing,
matching, changed Bcc and revoked synthetic recipient entries. There is **no**
trusted-send action in this Mail head; no existing Mail send was exempted.

**read — launch and identity:** removed the `aresos-assistant` C/Python launcher,
its environment preload fixture, coding policy, coding user/container and isolation
scripts. `control/launch.py` remains the protected **tool proxy/service** launcher;
its owner guard now requires both real and effective UID to match configured
`owner_uid`. A live same-container other-user socket denial remains, alongside the
base service's kernel peer-credential checks.

**read — sandbox harness:** old hostile programs use their own
`boundary/optional-sandbox.json`, installed as user settings only in the disposable
image. It forbids unsandboxed fallback, has no excluded commands or allowed Unix
sockets, hides `/run/aresos-tools`, and retains explicit read-only work/home masks
and a strict network list. It contains no managed-only source locks. Native
hostile execution is mandatory; a denial cannot yield a green qualification.
Complete outside mount observations and regression mutations remain. Seccomp
probes test this optional fixture; they are no longer a Claude startup gate.
No default containment is shipped.

**read — shared rules:** common recovery/untrusted-data guidance and Mail's roles
rules moved from per-action descriptions into each server's generated MCP
`instructions`, passed by the real SDK at initialization. Approval/question-copy
instructions remain at each asking/preparation action. Results' untrusted marking
and approval binding are unchanged. `docs/control/TOOLS.md` includes the server
instructions. Generation tests reject drift and repeated shared description blocks;
actual SDK initialization is checked for all three app servers.

**read — Chrome integration:** add its actions to `ACTIONS` and register the
adapter. Installed apps, normal user MCP entries and asking rules are discovered
automatically. Add app-wide rules to `instructions_for(app)`; regenerate every
artifact. Public send/delete asks automatically. A future trusted submit must be
explicitly marked, implement the current owner-entry checker and retain Chrome's
own exact-state binding. Existing fixed server names must match their ask names.
Chrome must ship its normal user MCP entry; only testapp is exempt. Every served
app's asking tools require managed asks even if its MCP entry is not installed yet.

## Removed checks and why

**read — each removal implements decision 24; these are no longer tool guarantees:**

| Removed check/policy | Why it no longer protects a tool under this decision |
| --- | --- |
| Exact equality of every installed settings key/value | Tool asking needs its managed ask, not an identical permission mode, sandbox or personal setting. Exact approval hashes and service state remain. |
| Exclusive managed MCP file, exact server commands/list, managed-only server switches | Our servers install at user scope; unrelated MCP servers are wanted. Generated names and tools are checked, with fixed protected proxy commands. |
| Refusal of a nonempty/symlinked managed drop-in folder | Additional root-managed settings are allowed. The required settings file and its own path stay protected; unrelated sources are not walked. |
| Managed-only permission/hook locks | Native tests show managed asks beat lower allows and PreToolUse allows. Personal hooks remain wanted; PermissionRequest approval is the accepted residual above. |
| Plugin registry refusal, marketplace/account/plugin/sideload locks | His plugins/skills are normal Claude Code. They cannot be globally prohibited to add our tools; PreToolUse precedence is tested, PermissionRequest and direct-call residuals accepted. |
| Forced sandbox, working-directory/file-tool blocks, deny list and WebFetch/WebSearch asks | Decision 24 accepts ordinary Claude file/network/program rights. The optional sandbox experiment is separate. Service-private app passwords and exact operation checks remain. |
| Default permission mode and bypass prohibition | The native init event proves bypass mode is active while managed asks still deny the fourteen required sends. |
| Fixed CLI/working directory/environment and `--setting-sources ''` | The owner starts normal `claude` with their setup and sign-in. Scope-specific positive controls show those sources actually load. The tool proxy still isolates its own imports/configuration. |
| Launcher policy walk, hash/canary startup gates and source/plugin suppression tests | There is no launcher containment guarantee. Optional hostile execution and canary evidence remain test-only; suppressed personal integrations are no longer acceptance criteria. |
| Coding user, its policy, MCP failure tests and separate container | One owner session does project and app work. Real other-user socket rejection remains. |
| Remote-settings cache/home or login restriction | The starting Mail boundary already stopped traversing the private home/cache; the starting launcher already allowed sign-in. No such restriction was reintroduced. The source-presence regression now also permits plugins/drop-ins. |

## Verified

**run — local:** `python3 control/generate.py --check` printed
`Generated artifacts match definitions`; `python3 -m unittest discover -s
control/boundary -p test_native.py -v` printed `Ran 11 tests` / `OK`.
AST parsing every `control/**/*.py` printed `Python syntax OK`.
`git diff --check` printed nothing. Local Docker reported its daemon unavailable;
no software was installed or host configuration changed. No Gradle ran.

**run — base:** [42582076609](https://github.com/Ares-Empire/AresOS/actions/runs/42582076609)
on `a21c9db3` passed: `Python 3.15.0` / `Fedora release 45 (Forty Five)`
(lines 205–206), `Generated artifacts match definitions` (269), `Ran 145 tests
in 219.338s` (417), `OK` (419), `Control base suite PASS` (426). This runs the generated-artifact check and the full original and
updated base tests inside pinned Fedora, including protected paths, slim key set,
missing/misnamed asks, extra sources, UID mismatches, trusted-entry checks and the
production SDK initialization.

**run — native boundary:** run **42582079690** passed with **24 named cases**:

| Cases | Observed result | Workflow log lines |
| --- | --- | --- |
| `normal-{none,user,project,local,all,pre_allow,pre_allow_all}` | list arrival 1, send arrival 0 each; both PreToolUse variants invoke the allow hook once | 1623, 1635, 1647, 1659, 1671, 1683, 1695 |
| `skip-{none,user,project,local,all,pre_allow,pre_allow_all}` | same denials/list positives, while init says `bypassPermissions` | 1729, 1741, 1753, 1765, 1777, 1789, 1801 |
| `positive-no-managed-ask-{user,project,local,all,pre_allow}` | list 1, send 1 each; hook variant invokes once | 1566–1610 |
| `positive-skip-no-managed-ask` | list 1, send 1, active bypass mode | 1555 |
| `{normal,skip}-permission-{user,managed}` | hook 1, list 1, send 1 each; accepted residual | 1706, 1717, 1812, 1823 |

`MCP_INSTRUCTIONS_OK` at line **1622** proves full app instructions, descriptions
and schemas reach the actual request. Native 2.1.319 places MCP instructions in an
environment message in `messages`, rather than the top-level `system`; both are
captured in full. Server headings bind each instruction block to its app. No
fallback duplication was needed. No model ran: responses are fixed test-double
SSE events, and every actual call reaches a separate synthetic HTTP receiver.

Native optional sandbox: lines **1137/2068**, 127 routes blocked in each helper
mode, 44 hashes unchanged, zero hostile arrivals, baseline/hostile/socket-state
complete 80-mount trees equal. Standalone: **1535/2466**, 127 attempts each, 42
hashes unchanged, zero arrivals. Helper-absent standalone VSOCK remains one
explicitly **unqualified** route (no qualified endpoint); all other routes are
blocked. Same-container other-user act.sock denial: **1536/2467**, `EACCES`.
The real-service identity check also runs in the base suite.

**run — Mail:** [42582082749, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42582082749)
on `a21c9db3` passed every job. `bash control/ci/mail/run.sh suite` printed
`Ran 145 tests in 197.066s` / `OK` / `Control base suite PASS` (workflow log
400–409), then `Ran 309 tests in 974.047s` / `OK` / `Control Mail suite PASS`
(834–838). The internal network/no-published-ports assertion passed (477).
Each of the four jobs runs `bash control/ci/mail/run.sh sweep` with
`MAIL_SWEEP_SHARDS=4` and its own `MAIL_SWEEP_SHARD` (0–3). Each printed
`Ran 4 tests` / `OK` / `Control Mail suite PASS`: shard 0 at 1466–1470,
shard 1 at 2496–2500, shard 2 at 2887–2891, shard 3 at 1858–1862.
Exact output and fixture-isolation assertions remain in the workflow artifacts.

### Description character totals

**read — measured from definitions before/after this package**, including complete
strings (not token estimates). Starting Mail head is newer than brief's d5a0b24a
measurement, so its actual before total is larger than the brief's approximation.

| App | All action descriptions before → after | Exposed MCP descriptions before → after | Instructions sent once |
| --- | --- | --- | --- |
| control | 10,473 → 2,208 | 6,366 → 1,407 | 1,652 |
| mail (32 actions / 28 MCP) | 97,703 → 20,071 | 86,479 → 18,551 | 2,426 |
| testapp | 26,485 → 3,343 | 24,700 → 3,211 | 1,652 |

Mail's MCP descriptions plus its single instructions block total **20,977**,
versus **86,479** before. The request capture proves all these shared rules arrive
unchanged; the generated description tests ensure none of the shared blocks is
repeated in an individual description.

### Iterations and final-head procedure

**run:** initial base **42581409363** failed only six subcases of the stale UID
diagnostic assertion; the underlying identity refusals worked. Boundary
**42581412329** failed on removed-artifact fixture paths before native tests.
Both were fixed in `8d1cd411`. Initial Mail **42581415737** was cancelled by the
newer run, so it is not passing evidence. Boundary **42581729762** ran both
sandbox modes successfully but failed the incorrect top-level-system instruction
assumption; inspection proved the full text in the environment message. The test
was corrected to actual request structure, retaining exact content/schema checks
and adding per-scope send-positive controls. No mandatory ask assertion was weakened.

The report/review-inclusive final head is pushed once, then each Control workflow
runs and is rerun with `gh run rerun <id>` on that same head. Final IDs, attempts,
head and exact final outputs are recorded in [draft PR #25's validation section](https://github.com/Ares-Empire/AresOS/pull/25)
after the final push, avoiding a report/head self-reference loop. Final acceptance
requires those executions to succeed; earlier source-head runs alone are not enough.

## Not verified

**assumed / separate image checks:** actual user-scope installation/migration on
AresOS, real terminal/phone rendering, Remote Control, real-account behavior,
owner logins/plugins and real laptop performance. No real account or model was
used. The notification hooks in the native harness use an empty-pending stand-in;
the real hooks run in the base/Mail suites. Optional sandbox results concern only
the explicit fixture and pinned runtime, not a default containment guarantee.

## JUDGMENT-CALL

**read:** no new owner decision. PermissionRequest approving a managed ask is the
already accepted decision-24 residual and must go to the lead/owner as a finding.
No attempt was made to prohibit those hooks, restore a lock or confine normal Claude.
The service still cannot establish whether a prompt was answered; the owner's
direct CLI/socket access remains accepted under the same decision.

## PLAN-GAP

**read:** this branch starts from Mail `d3babf1f` by the parallel-start note, not
post-merge main. That head has no owner-only trusted recipient list or trusted send
verb. The explicit metadata/default-deny adapter contract is ready, but a real Mail
free-send feature was not invented or silently exempted. All existing Mail
send/delete tools retain asks.

**read:** PR #25 conflicts with current main, so GitHub does not schedule its
pull-request checks. The parallel-start note forbids merging main until the lead
instructs it. The original round used `workflow_dispatch`; round 1 review fixes
restore path-filtered push checks on this branch. Once main is integrated and PR
checks resume, the `pkg/18d-base-slim` push triggers double runs and can be dropped
at that merge. Boundary retains its push check on main without cancelling runs
on main. After Mail merges, the later package
must merge main, regenerate every artifact, rerun every Control workflow twice and
review the combined head. No branch was merged during this run.

## Review fixes, round 1

**read — finding 1, push checks:** both base and boundary workflows now have a
`pkg/18d-base-slim` push trigger with the same path filter as their PR trigger.
Boundary's main push check is restored; its concurrency guard cancels older runs
only away from main. The branch push checks can be removed when main is integrated
and conflict-free PR checks resume, as described above.

**read — finding 2, native inputs:** boundary uses `control/**` in both push and
PR filters, covering definitions, generated instructions/tools and all existing
boundary/settings inputs.

**read — package lead's testapp gap:** `Engine._initialize_adapters` always
registers testapp, and `Proxy` accepts every app in `APPS`; `service.json` has no
disable switch. The default `asking_rules()` and `managed_settings()` now cover
all of `APPS`. The generated settings and boundary precondition require six asks,
including testapp send/delete. Shipped MCP entries remain exactly control/mail.
The generator rejects missing entries for every other served app, misnamed rules,
unknown server names and owner-only/unexposed tools. All artifacts were regenerated;
only the two policy JSON files changed. The settings comments and both code READMEs
now explain the same split; TOOLS.md contains no ask list and regenerated unchanged.

Regression tests remove each testapp rule while retaining every Mail ask and
verify `boundary_not_installed`, no adapter execution, unchanged fixture state,
reserved approval and no receiver arrival. Separate coverage checks every engine
adapter's public asking tools against the default rules. The native precedence
harness now uses the default policy rather than requesting a special testapp set.

**run — local:** `python3 control/generate.py --check` printed
`Generated artifacts match definitions`. The following command printed
`Ran 7 tests in 1.906s` / `OK`:

```sh
PYTHONPATH=control:control/tests .work/18d-review/venv/bin/python -m unittest -v \
  test_slim_policy.SlimPolicy.test_exact_slim_keys_hooks_and_installed_tool_names \
  test_slim_policy.SlimPolicy.test_every_engine_adapter_asking_tool_has_a_default_rule \
  test_slim_policy.SlimPolicy.test_generator_rejects_misnamed_rules_including_harness_tools \
  test_slim_policy.SlimPolicy.test_generator_rejects_any_missing_server_except_testapp \
  test_slim_policy.SlimPolicy.test_shared_instructions_generated_once_and_approval_text_stays_at_use \
  test_slim_policy.SlimPolicy.test_identity_real_and_effective_must_both_equal_configured_owner \
  test_operations.Generated.test_artifact_drift_effects_ask_rules_and_owner_only_absent
```

`PYTHONPATH=control .work/18d-review/venv/bin/python -m unittest discover -s
control/boundary -p test_native.py -v` printed `Ran 11 tests in 0.008s` / `OK`.
AST parsing every Control Python source printed `Python syntax OK`.
Local YAML assertions confirmed equal push/PR filters, both branch triggers,
`control/**` coverage, and the boundary main concurrency guard, printing
`control-base: push/PR filters and concurrency OK` and the same for boundary.
`git diff --check` printed nothing. Docker again reported
`Cannot connect to the Docker daemon`; the full unmodified root-owned-path,
service-refusal, base, Mail and native suites therefore run on Linux CI, not here.
Only a worktree-local virtual environment was installed; no system software or
host settings changed. Storage audit: `Remaining .work files over 500 MB: []`.

**read/run — targeted reviews:** fresh `gpt-6.1-sol` high and `gpt-6-astra`
security reviews both returned **SAFE**, with no findings on source changes
`e5e89d2d..6744dfe5`. Both independently checked generator and workflow invariants.
Their supplemental missing-rule probes used a mocked policy reader; these are
admission-code checks, not evidence for root-owned filesystem integration.

**Final-head execution accounting:** the round's five-execution procedure is one
push-triggered base run and its same-run rerun (attempts 1/2), one push-triggered
boundary run and its same-run rerun (attempts 1/2), and one Mail dispatch with
`gh workflow run control-mail.yml --ref pkg/18d-base-slim` (attempt 1). Base and
boundary are not manually dispatched. The actual run IDs, attempts, execution
count, head and exact outputs are recorded in draft PR #25 after this report's
single final push, avoiding a report/head self-reference loop. This paragraph
describes the procedure; passing evidence is the completed runs linked in the PR.

## Open questions

No mid-run answer requested. Lead/image setup must arrange installation of the
slim managed settings/CLAUDE.md and normal user MCP entries, and exclude our asking
tools from broad PermissionRequest auto-approval hooks. The four tested allow
hooks demonstrably approve them; no guarantee against that is claimed.

**run — storage audit:** `Remaining .work files over 500 MB: []`. Downloads here
are only CI logs/artifacts; no image/ISO or extracted system layer was downloaded.
All pushes used normal verification, never --no-verify or force-push. No design,
plan, OS, Minecraft, install, owner-state or handoff file was edited.

## Main merge and 19b integration

**read — scope and history (2026-11-12):** followed `briefs/18d-main-merge.md`
on `pkg/18d-base-slim`, starting at its local commit `b828f4e3`. The lead's
`44ee2a84` / `1ec69134` merges were already present and were not redone or
rewritten. Read the three preceding 18d briefs, this report, the 19b report's
opening/Done, Re-scope and Final fix round sections, `DESIGN.md`, CONTROL
section 7 and PLAN's 2026-11-11 08:10 normal-MCP bar. Historical containment and
stage-3 report claims do not override the current slim/stage-2 implementation.

**read — item 1, removed dependencies:** recursively searched the owner oracle,
all base/Mail tests, `control/ci/` and Control workflows for the removed policy
functions/files, exact-policy report, drop-in walk, managed keys, launcher and
coding-user components. No active 19b caller, import, install or assertion
requires them. Oracle `differences` functions are independent command/context
comparisons (`owner_state_oracle/context.py:230`, `driver.py:439`), not the
removed boundary equality report. Remaining drop-in/old-key references test
that additional sources are accepted (`tests/test_policy_sources.py:10`,
`test_boundary_exact.py:29`); attempted client path overrides remain negative
tests (`test_boundary_exact.py:67`). The retained test filename
`test_boundary_exact.py` now tests subset admission, not exact policy equality.

**read — item 1, CI and selection:** `ci/setup.sh:11` installs only the slim
managed settings and CLAUDE.md, with the protected proxy launcher retained at
`control/launch.py`; `ci/test.sh:6` calls the current base selector.
`ci/base.py:7` selects the two optional installed-channel/ledger cases separately.
`ci/mail/run.sh:21` uses this same setup/base suite before disconnecting egress,
then runs `ci/mail/tests.py:57`'s disjoint required/optional selections. The
optional workflow (`.github/workflows/control-owner-oracle.yml:19`, `:38`,
`:66`, `:96`) uses those same scripts for its ledger, alterations and full
fault sweeps. No removed MCP file or coding step is installed. Selection tests
remain intact; the new admission module is discovered by required base CI.
No CI selection or existing asking assertion was weakened.

**read/run — item 2, every asking action:** these are the complete public,
nontrusted send/delete set on the combined head; each appears in both generated
policy files (`settings/managed-settings.draft.json:4`, `settings/ask-rules.json:4`):

| Action | Effect | Required managed ask |
| --- | --- | --- |
| testapp_send | send | mcp__testapp__send |
| testapp_delete | delete | mcp__testapp__delete |
| mail_send | send | mcp__mail__send |
| mail_delete | delete | mcp__mail__delete |
| mail_folder_delete | delete | mcp__mail__folder_delete |
| mail_unsubscribe | send | mcp__mail__unsubscribe |

`boundary_policy.py:20` defaults to all served apps, including testapp;
`boundary.py:54` requires every rule on each reserve/submit. No Mail action is
marked trusted. The generator previously checked only that rules named exposed
tools, so removing one (or replacing send with another valid exposed verb)
could escape its own validation. Fixed `control/generate.py:46` to compare
**both** policy artifacts independently against the asking actions. New tests
at `tests/test_slim_policy.py:61` remove each of six rules from either artifact;
`:71` renames send to an exposed read tool. Existing misnamed/unexposed-rule
and missing-server tests remain. This validates generated artifacts; installed
settings still permit additional keys/rules/hooks as decision 24 requires.

**read/run — item 3, admission before R2:** `engine.py:163` checks the boundary
before preparation or reservation writes. `engine.py:209` checks it before
loading/submitting the operation; its trusted guard at `:225` precedes
revalidation, submission-context creation and the submitting write (`:250`).
`action_context.py:32` still commits/rechecks the current context before its
mutation yield (`:56`). No engine change was needed. Added
`tests/test_admission_context.py:40`: each missing/misnamed ask rejects both
send/delete preparations and submissions, with no adapter preparation,
revalidation, context creation, execution or Store.write. Full rows/audit,
exact reserved approvals, empty stages and independent receiver evidence stay
unchanged. `:73` repeats these checks for a missing trusted-entry checker and
a revoked owner-only entry. Both tests restart the actual Store/Engine,
confirm unchanged records, no context/submission claim and no unfinished
recovery candidate (`recovery.py:14`). Only Boundary.read is replaced in these
portable tests; the real root-owned/nonsymlink path checks remain in Linux CI.
Existing trusted-entry success/mismatch/revocation tests remain unchanged.

**read/run — item 4, shared instructions:** `definitions.py:52`'s common
error/recovery guidance does not contradict the cursor helper's changed-token
restart (`paging.py:21`) or invalid-cursor `stale_reference` refusal. Mail's
SPECIAL-USE/untrusted-data block (`mail/definitions.py:61`) is unchanged.
`mail_filing_notices` retains its changed-catalogue first-page restart and
invalid-cursor rules in its description (`mail/definitions.py:112`), and
approval/question-copy text remains on each asking/preparation action.
The restore-limit sentence stays on restore_confirm (`definitions.py:100`).
Extended `test_slim_policy.py:78` to pin those 19b descriptions as well as the
existing checks for exactly one instructions block and none repeated in any
description. No instruction or description needed editing. Existing native
request capture continues to require complete instructions/descriptions/schemas.

**run — item 5, regeneration and exact character totals:** ran
`python3 control/generate.py` (`Generated tools, help, reference and ask rules`),
then `python3 control/generate.py --check` (`Generated artifacts match definitions`).
Every generated file is unchanged: the merges had regenerated them correctly.
Measured `len(action.description)` / `len(tool['description'])` directly from
`18168c6c` extracted with `git archive` inside this worktree and from the
combined definitions, in separate Python processes. Counts exclude file-ending
newlines and include the instructions string once, as passed at initialization.

| App (exposed tools) | Main descriptions | Combined descriptions | Instructions once | Combined total | All action descriptions, main → combined |
| --- | ---: | ---: | ---: | ---: | ---: |
| control (3) | 6,366 | 1,407 | 1,652 | 3,059 | 10,473 → 2,208 |
| mail (28) | 86,557 | 18,629 | 2,426 | 21,055 | 97,781 → 20,149 |
| testapp (13) | 24,700 | 3,211 | 1,652 | 4,863 | 26,485 → 3,343 |

19b's notice description adds 78 characters to both Mail columns relative to
the pre-merge measurements above; it was preserved. Measurement output is in
`.work/18d-main-merge/descriptions.json`. The first measurement invocation
completed both measurements but omitted PYTHONPATH for its final action-list
print; reran with `PYTHONPATH=control`, successfully printing all six actions.

**run — local verification:** used the existing worktree-only virtualenv,
Python 3.14.6, with `PYTHONDONTWRITEBYTECODE=1` / `-B`:

- `PYTHONPATH=control:control/tests .work/18d-review/venv/bin/python -B -m unittest -v`
  with `test_admission_context`, all SlimPolicy methods except the existing
  installed-settings trusted-send test, and
  `test_operations.Generated.test_artifact_drift_effects_ask_rules_and_owner_only_absent`:
  **11 tests / OK** (`local-policy.txt`; the initial four-test probe also passed).
- Loaded `test_owner_state_oracle`, `test_owner_state_fixes_s2` and
  `test_mail_ci_selection` with unittest and applied `ci.base.select`'s required
  selection: **150 tests / OK** (`local-owner.txt`). The optional installed-channel
  cases were not claimed as local evidence.
- `PYTHONPATH=control .work/18d-review/venv/bin/python -B -m unittest discover -s control/boundary -p test_native.py -v`:
  **11 tests / OK** (`local-native.txt`), testing the evidence validator, not
  executing native Claude on macOS.
- AST-parsed every Control Python source: `Python syntax OK`.
  `bash -n control/ci/test.sh control/ci/setup.sh control/ci/mail/run.sh` and
  `git diff --check` both exited 0 with no output.
- Storage audit: `Remaining .work files over 500 MB: []`. No system software,
  host settings, real account, model, Minecraft or Gradle was used.

**run/read — CI accounting and owner-oracle result location:** the merge-only
head `1ec69134` already had PR runs: base **43152902136** and boundary
**43152902221** passed; Mail **43152902120** was still running at report time.
These are early signals, not final-head acceptance. After committing this
report, push the branch **once**, including `b828f4e3`. Use the resulting PR
base/Mail/boundary runs, await each, then rerun each same ID once; dispatch
`control-owner-oracle.yml --ref pkg/18d-base-slim` once and await all 61 jobs.
The **actual owner-oracle result**, final SHA, run IDs/attempts, exact outputs
and execution count are recorded after the push in [PR #25's final integration
validation](https://github.com/Ares-Empire/AresOS/pull/25), as the brief requires
to avoid a report/head loop. This report makes no claim for an unrun oracle.
Planned accounting is seven final-head executions (three PR attempts, their
three reruns, one manual oracle), plus the three inherited merge-only runs.

**Not verified / PLAN-GAP / JUDGMENT-CALL:** no new design change or owner
decision. The accepted stage-2 disclosure/storage limits in 19b's Re-scope
remain; optional pinned gaps are not a zero-gap guarantee. Real-account,
laptop installation and interactive terminal/phone checks remain outside this
synthetic integration run. No reviewer-written file, design/plan, OS, mod,
install, README, STATE or HANDOFF was edited. No merge, force-push or hook
bypass is authorized. No open question blocks this integration check.
