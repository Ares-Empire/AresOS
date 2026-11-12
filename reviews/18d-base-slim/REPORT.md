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

## Main merge fixes, round 1

**Done / mechanism:** followed `briefs/18d-main-merge-fixes.md` from local
`42506c5d`, retaining local review commit `14a2ff43`. The fault harness, rather
than production storage, allowed clean discovery and fault replay to use
different timestamp lengths. Reproduced this deterministically before changing
the fixture: run `send_duplicate` with the same scripted UUID sequence and
fixed clocks **1794225600.0** / **1794225600.1234567** (12 / 18 JSON characters).
Both clean calls succeed, both recover, and both have **908** local write
points, but their traces first differ at zero-based index **361**:
`sqlite.main.fsync` versus `sqlite.main.write`, with no fault injected. The sixth
transaction ends at point **410** / **411**, and its database has **21** / **22**
pages. Later transactions converge again; equal mechanism totals do not imply
equal fault positions. This demonstrates the reported pre-fault page-boundary
failure mechanism, without relying on a rare failing rerun or claiming the
historical wall-clock samples were recorded.

**Done / source audit:** checked each ambient clock/random source used by the
inherited flows:

- `storage.py` embeds the float clock in journal records and prepared events,
  retained-row dates, repair/APPEND restart timestamps; `engine.py` uses it for
  approval expiry and repair completion; Mail uses it for composition creation
  and `sent_append_started_at` / `sent_append_ended_at`. JSON float widths vary.
- `engine.py`, `warnings.py` and `mail/filing.py` store nanosecond notice dates.
  Implicit `localtime()` also controls the engine's daily-history selection;
  outgoing MIME Date follows the effective clock. The existing scripted
  calendar supplies implicit local time and nanoseconds from that same clock.
- Generation/composition/operation/repair/filing/intent/export/archive IDs and
  observation tokens come from `uuid.uuid4()`: hex IDs always have 32 digits
  (generation-prefixed operation IDs have 65 characters). Their widths do not
  vary, but their values can change recovery ordering. Reuse the existing
  per-flow scripted UUID generator.
- Temporary paths have fixed-width names; generated MIME boundaries have
  fixed-width random digits and their hashes have fixed widths. They do not
  explain variable JSON lengths here. The inherited export flows do not import
  file modification metadata; that separate import path explicitly formats
  microseconds. Filesystem timestamps are not substituted by this fix.

**Done / fix:** `control/mail_tests/test_review23_sweep.py` now scripts clock,
calendar and UUIDs for every direct `Scenario`, with seed `inherited-<flow>`.
The 22 previously uncontrolled flows use **1794225600.1234567**, preserving
realistic timestamp precision: a diagnostic using `.0` lost one discovered
`repair` page write; full precision preserved its **345** points. Archive keeps
its existing `.0` clock, `inherited-archive` seed and deterministic two-second
advance. Expiry and maintenance retain their existing expiry-plus-one-second
and plus-86401-second clock steps. Scripts cover setup, execution, faults and
recovery, and close afterward. The `type(self) is Scenario` guard leaves the
owner oracle's independent clock/ID script unchanged. No production code changed.

**Done / required regressions:** added a two-clock SQLite trace test and a
three-clean-replay comparison for **each of all 23 flows**. The latter installs
failing ambient time/UUID functions outside each fixture: accidentally dropping
either script fails every run, even when ambient float lengths happen to agree.
All three traces must match exactly; every replay also runs the existing
recovery/completion checks. Both tests are in the inherited module already
selected by every required Mail sweep job. The existing archive regression and
every fault/prefix/recovery assertion remain. AST comparison of the old/new
entire sweep method, after hoisting the identical tuple to shared `FLOWS`,
printed `Sweep invariant OK: same 23 flows, all fault modes, cleanup pairs and
assertions unchanged`. No selection or workflow changed.

**Verified / local:** used Python 3.14.6 in the existing worktree virtualenv,
with `-B` and `PYTHONPATH=control:control/mail_tests`:

- `python3 control/generate.py --check`: `Generated artifacts match definitions`.
- Unmodified unittest invocation of the two new tests: `Ran 2 tests` /
  `FAILED (failures=15)`, with `boundary_not_installed` at macOS's `/etc` symlink.
  No protected host path or system setting was changed.
- With only `Boundary.read` returning generated `managed_settings()`, both new
  tests plus the existing archive/completion/recovery regressions: **5 tests /
  OK**. The mechanism test prints `Clock precision changes SQLite trace at index
  300: sqlite.main.fsync vs sqlite.main.write; points=[788, 788]` (SQLite-main
  events only); all 23 flows print `replays=3` and pass exact trace equality.
- Full inherited sweep with that same explicitly local policy-read stub:
  **all four shards pass**, each `Ran 7 tests` / `OK` (483.538 / 361.264 /
  445.754 / 186.519 seconds). The wrapper runs the unmodified
  `test_review23_sweep` and `test_review24_io` modules with
  `MAIL_SWEEP_SHARDS=4` and shards 0–3. Logs: `local-sweep-{0,1,2,3}.txt`;
  the wrapper is `local_sweep.py`.
- `PYTHONPATH=control:control/tests .work/18d-review/venv/bin/python -B -m unittest
  -v test_mail_ci_selection`: **6 tests / OK**. All Control Python sources
  AST-parse (`Python syntax OK`); `git diff --check` exits 0 without output.
- With the same policy-read stub, the other direct-Scenario consumer,
  `test_review26_sweep`: **3 tests / OK** (`Ran 3 tests in 7.980s`), including
  live admission recovery, cleanup EIO precedence and unrelated-Sent rejection.

**Verified / coverage accounting:** prior Linux Mail attempt 2
`43153748879` has **23 flows, 6,640 points, 6,302 single + 6,302 persistent +
15,915 cleanup-pair cases = 28,519 fault cases**. On this Mac with only the
policy-read stub, before/after discovery both total **23 flows / 6,516 points**;
full final sweeps execute **6,259 single + 6,259 persistent + 15,979 cleanup-pair
cases = 28,497 cases**, with no failure. These local totals are not compared
numerically to Linux acceptance: the stub removes policy closes, Mac publication
adds an unlink, and SQLite archive/VACUUM I/O differs by platform. The Linux
before/after comparison remains required.
The final Linux counts, exact tested SHA, workflow run IDs and both attempts
are recorded in [PR #25](https://github.com/Ares-Empire/AresOS/pull/25) after the
single final push, avoiding another commit/push that would invalidate the
tested head. Acceptance requires all three required workflows twice and all
eight Mail jobs in both attempts; a passing rerun alone is not acceptance.
Required sweep test count increases from **5 to 7** per job.

**Not verified / PLAN-GAP / JUDGMENT-CALL:** local stubbed traces are storage
diagnostics, not installed-policy or Linux acceptance. Real accounts, interactive
owner use and laptop installation remain outside this run. No new owner-facing
behavior or difficult-to-reverse decision. The optional oracle and
`reviews/19b-owner-state/KNOWN-GAPS.json` are unchanged; its existing strict-pin
migration PLAN-GAP remains. Pin SHA-256 is still
`6bbcb02fb83c750e33ef370b694c13eb59c33a82c04b1540038ed99995e05ea2`.
No oracle run is requested. No forbidden file was edited; no merge, force-push,
hook bypass, system installation or host change. No Gradle ran. Storage audit:
`Remaining .work files over 500 MB: []`. No open question blocks this fix.

**Execution accounting:** the final-head procedure is exactly six executions:
the three automatic PR runs and one `gh run rerun <id>` of each same run. Actual
IDs, attempts, results and execution count are recorded in PR #25 after the
push. Local verification logs and scripts are under
`.work/18d-main-merge-fixes/`.

## Main merge fixes, round 2

**Done:** followed `briefs/18d-main-merge-fixes-2.md` from local `59def857`.
No production code changed. `control/mail_tests/sweep_scripts.py` contains the
independent ambient-source guard and six fixture scripts;
`control/mail_tests/test_review23_sweep.py` installs them for every direct
`Scenario`, including discovery, all fault modes, recovery and cleanup. The
owner-oracle subclass retains its independent scripts. Constructor failures
restore patches and registered fixture cleanups too.

**Sources found (production paths relative to `control/aresos_control/`):**

| Source | File and line; use in the inherited flows |
| --- | --- |
| Float wall clock | `storage.py:207,246,248,591,645`; retained dates, journal events and restart dates. `engine.py:157,172,176,219,242,346,392,424`; expiry and quiet periods. `mail/adapter.py:520,967,972,985`; compositions and APPEND dates. `retention.py:74`, `archive.py:16`; retention/cutoff. Fixture reads: `control/mail_tests/test_review23_sweep.py:149,168` (archive cutoff, maintenance advance); its `:164` expiry patch uses the fixed approval deadline. |
| Nanosecond clock | `warnings.py:36`, `mail/filing.py:413`, `engine.py:138`; notice occurrences, filing warnings and fault-only background-maintenance warnings. |
| Calendar conversion | `engine.py:289` uses **explicit** `gmtime(retry)` and `strftime(..., tuple)`. `engine.py:455,461` has implicit `localtime()` in the history route, which no inherited flow calls. No inherited clean/fault replay reads implicit `localtime`, `gmtime` or `strftime`; these now stay forbidden, with no replacement script. |
| Implicit email date | `mail/adapter.py:529` calls its imported `formatdate(localtime=False)` alias. Python 3.14 `email/utils.py:239` otherwise supplies the current clock. Both the module function and the imported alias are guarded/scripted. |
| UUIDs | `storage.py:240,546,761`, `engine.py:175,387`, `warnings.py:34`, `mail/adapter.py:520,1351`, `mail/filing.py:72,338`, `mail/onboarding.py:90,99`, `testapp.py:71`, `results.py:129`, `exports.py:14`, `archive.py:86`; generation, operation, occurrence, composition, intent, filing, observation, export and archive identities. UUID4 is read; UUID1 is not. |
| MIME randomness | `control/mail_tests/test_review23_sweep.py:252` serializes the attachment fixture; Python 3.14 `email/generator.py:384` calls `random.randrange` for its boundary. All three export fixtures read this source, including testapp export's shared setup. |
| Temporary names | `control/mail_tests/test_review_fixes_12.py:23` and `control/mail_tests/test_review23_sweep.py:255` construct `TemporaryDirectory`; Python 3.14 `tempfile.py:154` consumes an ambient private Random instance. All flows read temporary names. |
| Other candidate sources | `mail/dkim.py:80` uses `secrets.randbelow`, but the inherited HTTPS fixture stubs DKIM verification (`test_review23_sweep.py:390`). `files.py:120` converts explicit filesystem metadata, but these flows export rather than import files. `mail/adapter.py:227` converts an explicit message date. No flow reads `datetime.now/utcnow/today`, `date.today`, UUID1, `secrets`, `os.urandom` directly, or `email.utils.make_msgid`; no scripts are needed for them. `MemoryIMAP` uses a literal Message-ID (`test_review_fixes_11.py:22`, `test_review_fixes_12.py:29`); outgoing Message-IDs derive from the scripted operation ID (`mail/adapter.py:581`). |

The fixture alias chain is `Results23` → `Duplicates22` → `LateDuplicates21`
→ `Recovery19` → `Recovery18` → `Recovery17` → `PlainQuestions12`. Its setup,
compose, approval and restart methods were read, as were the service clock,
calendar, random, SQL and email call sites. No SQL ambient clock/random
expression was found. The old fixture calendar reads are `control/owner_state_oracle/clock.py:27,29`;
its seeded UUID generator is `control/owner_state_oracle/identity.py:13,14`.
The new fixture scripts use only explicit seeds and the effective scripted clock
(`sweep_scripts.py:102,108,126,133,141`). Monotonic timing in the sweep
(`test_review23_sweep.py:816,820,858,865`) measures elapsed duration;
it does not feed stored values, ordering or fault positions.

**Guard and scripts:** ambient `time.time/time_ns`, implicit/None calendar
arguments, `datetime.now/utcnow/today`, `date.today`, UUID1/4 (also 6/7/8 where
available), random-module APIs, unseeded `Random`, `SystemRandom`, secrets APIs,
`os.urandom`, tempfile candidate names, `make_msgid` and implicit `formatdate`
raise `AmbientRead`. It derives from `BaseException` so production's normal
exception-to-response/recovery handlers cannot swallow a fixture leak. Explicit
calendar inputs and seeded private generators remain valid; 27 direct negative
probes and positive explicit-input controls exercise the guard, including
production's cached datetime/date/email aliases.

The original full-precision float clock and `inherited-<flow>` UUID seed remain.
Implicit email dates now pass that clock explicitly. MIME boundaries use a
private seeded generator and keep the library's padded boundary width. Temporary
names keep eight characters and replay the same sequence within a worker; a PID
salt isolates concurrent workers sharing local directories. These two formerly
ambient random sources are now scripted even though their widths were fixed.
The former `scripted_calendar()` nanosecond behavior is a separate script;
unused implicit local-calendar reads are blocked instead of supplied.

**Mutation checks:** the required inherited module discovers actual script
consumers through setup/call/recovery, then disables each component alone and
requires the exact corresponding `AmbientRead` source. For nanoseconds not used
in a clean replay, it searches actual single-fault points (journal writes first,
then every other primary point) before concluding that a flow does not read it.
This also finds the background warning at fault point 1 in expiry/maintenance.
All **91 missing-component checks pass**:

- Float clock, UUIDs, temporary names: **23 flows each**.
- Calendar/email dates: **11** — send, repair, unsubscribe_mailto, status,
  settlement, cancel, restore, expiry, maintenance, archive, send_duplicate.
- Nanoseconds: **8** — status, settlement, filing_move, filing_copy,
  filing_rename, send_duplicate, plus expiry and maintenance under fault.
- MIME boundary: **3** — attachment_export, testapp_export, export_rollback.

All 23 flows also replay cleanly three times with exact write-trace equality.
An AST comparison prints `Sweep invariant OK: same 23 flows, fault/recovery
methods, modes, cleanup pairs and assertions unchanged`: the complete sweep,
`fault`, `assert_result`, recovery, completion and duplicate-warning methods
are unchanged. No test selection or workflow changed. Required sweep jobs now
run **10 tests** (the previous seven plus three new guard/order tests).

**Lifecycle regression:** the retained uncommitted change correctly identified
tied notice timestamps. Round 1's calendar derived nanoseconds from an unchanging
float clock, letting UUID tie order place the generic interrupted-change warning
before the later Trash occurrence. The new nanosecond component retains and
extends the proposed fix to **every** flow, including archive: each read is at
least the previous value plus one and follows any forward effective-clock jump.
A nested 90,000-second expiry clock followed by restoration still leaves the
next notice strictly newer. The fixed float clock, explicit expiry/maintenance
advances and archive's two-second step are unchanged. No assertion was weakened.

Searched every test module for `Scenario`, `test_review23_sweep` and the shared
scripts. Checked all direct users and the subclass/indirect users:

- `test_review23_sweep`: ordering/recovery, duplicate evidence, explicit expiry,
  maintenance retention and archive cutoff; full fault sweep and regressions run.
- `test_review26_sweep`: live admission recovery and archive/expiry, plus completion
  and cleanup precedence; all three tests run twice.
- `test_review27_checks`: notice selection, failed filing result/restart and
  warning identity; all tests run twice.
- `test_review28_filing`: unresolved-role/location checks and acknowledgement;
  all four tests run twice.
- `test_review29_lifecycle`: newest-occurrence order, identity, acknowledgement,
  expiry/retention and archive behavior; all tests run twice, including the
  originally failing method.
- `test_owner_state_regressions`: the three required aliases run twice, including
  `test_review21_acknowledged_rename_expiry`; all six named tests also pass in
  a separate complete module run.
- `test_owner_state_sweep`: reviewed the independent advancing-clock subclass;
  its five required fixture/isolation tests run twice. Its optional exhaustive
  strict-pin sweep is unchanged and was not run.
- `test_owner_state_perturb`: reviewed its constructor wrapper and replay of the
  same named regressions; the local alteration module result is recorded below.
  No optional oracle workflow is requested or dispatched.

**Linux before/after counts:** downloaded the Linux job logs, rather than
substituting Mac diagnostics. Before is Mail **43153748879, attempt 2**, source
`9bcacd84`; round 1 is **43162099390, attempt 1**, source `8bfe75ec`. All four
round-1 sweep jobs pass; the two container failures are the same lifecycle
method and its inherited regression alias. The following per-flow values are
identical in both Linux runs. `S`, `P`, `C` mean single, persistent and cleanup-pair
cases. Final-head values and their comparison against every row are recorded
in [PR #25's final validation](https://github.com/Ares-Empire/AresOS/pull/25)
after the one final push, alongside both attempts and the exact tested SHA;
this avoids a report commit/push invalidating that tested head.

| Flow | Before points | Round-1 points | Before S / P / C | Round-1 S / P / C |
| --- | ---: | ---: | --- | --- |
| send | 830 | 830 | 797 / 797 / 1567 | 797 / 797 / 1567 |
| repair | 345 | 345 | 334 / 334 / 632 | 334 / 334 / 632 |
| delete_trash | 265 | 265 | 253 / 253 / 475 | 253 / 253 / 475 |
| delete_permanent | 395 | 395 | 379 / 379 / 711 | 379 / 379 / 711 |
| unsubscribe_mailto | 832 | 832 | 799 / 799 / 1573 | 799 / 799 / 1573 |
| unsubscribe_https | 329 | 329 | 315 / 315 / 590 | 315 / 315 / 590 |
| status | 147 | 147 | 143 / 143 / 272 | 143 / 143 / 272 |
| settlement | 148 | 148 | 144 / 144 / 275 | 144 / 144 / 275 |
| cancel | 65 | 65 | 63 / 63 / 118 | 63 / 63 / 118 |
| restore | 68 | 68 | 66 / 66 / 122 | 66 / 66 / 122 |
| attachment_export | 277 | 277 | 242 / 242 / 1593 | 242 / 242 / 1593 |
| testapp_export | 144 | 144 | 117 / 117 / 534 | 117 / 117 / 534 |
| password | 129 | 129 | 119 / 119 / 226 | 119 / 119 / 226 |
| filing_move | 350 | 350 | 338 / 338 / 650 | 338 / 338 / 650 |
| filing_copy | 351 | 351 | 339 / 339 / 654 | 339 / 339 / 654 |
| filing_rename | 227 | 227 | 219 / 219 / 419 | 219 / 219 / 419 |
| expiry | 65 | 65 | 63 / 63 / 111 | 63 / 63 / 111 |
| maintenance | 62 | 62 | 60 / 60 / 108 | 60 / 60 / 108 |
| restart_index | 31 | 31 | 20 / 20 / 62 | 20 / 20 / 62 |
| restart_tail | 33 | 33 | 22 / 22 / 68 | 22 / 22 / 68 |
| export_rollback | 277 | 277 | 246 / 246 / 1765 | 246 / 246 / 1765 |
| archive | 360 | 360 | 347 / 347 / 1670 | 347 / 347 / 1670 |
| send_duplicate | 912 | 912 | 877 / 877 / 1720 | 877 / 877 / 1720 |
| **Total** | **6,642** | **6,642** | **6,302 / 6,302 / 15,915** | **6,302 / 6,302 / 15,915** |

Both runs execute **28,519 fault cases**. No per-flow point or single,
persistent or pair count drops. Their mechanism summary totals **6,640** rather
than the per-flow sum **6,642**: the summary copies the counter before recovery,
whereas each restart flow's retained trace gains one delayed `journal.close`
when recovery closes a Raw handle created in the discovery scope
(`storage_faults.py:164`). The two extra close events are skipped as primary
faults by the unchanged sweep. This explains the totals without hiding any
case or changing instrumentation.

**Verified / local:** commands used Python 3.14.6 from the existing
`.work/18d-review/venv/bin/python`, with `-B` and
`PYTHONPATH=control:control/mail_tests`, unless stated otherwise. Reproduction
wrappers and exact logs are in `.work/18d-main-merge-fixes-2/`:

- `python3 control/generate.py --check`: `Generated artifacts match definitions`.
- Native `python -B -m unittest -v
  test_review23_sweep.FaultSweep23.test_inherited_replays_have_identical_write_traces`:
  `Ran 1 test` / `FAILED (failures=14)`, each stopped at
  `boundary_not_installed` because macOS `/etc` is a symlink. No protected host
  path or setting was changed. The following local storage diagnostics replace
  only `Boundary.read` with generated `managed_settings()`; CI remains the
  evidence for the real installed-policy path.
- `local_tests.py` with the three new tests, three-replay comparison, two-clock
  mechanism regression, archive regression, recovery/completion counterexamples
  and `test_review24_io`: **9 tests / OK** (`239.572s`), log
  `local-guard-final.txt`. Mutation output lists all 91 omissions and actual
  consuming flows; the two background-maintenance messages are intentional
  fault witnesses. The precision probe still prints index **300**,
  `sqlite.main.fsync vs sqlite.main.write; points=[788, 788]`.
- `MAIL_SWEEP_SHARDS=4 MAIL_SWEEP_SHARD=N ... local_tests.py
  test_review23_sweep.FaultSweep23.test_review23_enospc_at_every_discovered_durable_write`
  for N=0–3: **all four pass**, `Ran 1 test` / `OK`, in
  **515.112 / 386.419 / 475.521 / 266.087s**. Logs:
  `local-sweep-{0,1,2,3}.txt`. Totals are **23 flows, 6,518 per-flow points,
  6,259 single + 6,259 persistent + 15,979 pairs = 28,497 fault cases**.
  The pre-recovery mechanism summary is 6,516 (the same two delayed closes).
  These match round 1's Mac coverage; they are not compared numerically to Linux
  because the policy stub, Linux publication primitives and SQLite/VACUUM differ.
- `local_consumers.py`: the six consumer modules' required cases, using the
  repository's `select_cases(..., 'suite')`, pass **twice**, **41 tests / OK**
  in **3.930 / 6.829s**. Exact test names/results are in
  `local-consumers-{1,2}.txt`. No optional exhaustive owner sweep was selected.
- `local_tests.py test_owner_state_regressions`: the complete module,
  **6 tests / OK**, `0.871s`, including all three additional named regressions.
- `PYTHONPATH=control:control/tests python -B -m unittest -v
  test_mail_ci_selection`: **6 tests / OK**, `0.097s`.
- Control Python sources AST-parse (`Python syntax OK`); the sweep invariant
  comparison above passes; `git diff --check` exits 0 without output.
- `OWNER_PERTURB_SHARDS=4 OWNER_PERTURB_SHARD=N ... local_tests.py
  test_owner_state_perturb` for N=0–3: **all four pass**, one test each,
  **1326.895 / 1112.669 / 1246.068 / 1132.209s**. The union covers **98 recorded cases / 110
  partitions / 2,081,423 alterations**; all parts are present and all report
  `slipped=0`. One regression label represents two separate Driver recordings.
  Logs: `local-perturb-{0,1,2,3}.txt`. The first local attempt stopped at
  `ModuleNotFoundError: No module named 'cryptography'`; installed only the
  repository-pinned `cryptography==50.0.2`, `cffi==2.1.1`, `pycparser==3.12`
  into the existing worktree virtualenv with `--no-cache-dir` and binary wheels.
  An unsharded restart was intentionally interrupted (exit 130) before running
  the complete existing four-shard partition; it is not counted as a passing
  test. No test/partition/assertion was edited or excluded.

**Final-head CI / execution accounting:** after this report commit, push the
branch once, including the local brief/reviews commit and the fixture fix.
Require Control base, Control Mail (all eight jobs) and Control boundary to
pass, then `gh run rerun <id>` of each same run once. The actual final SHA,
three run IDs, both attempts, exact outputs and final per-flow Linux count
comparison live in [PR #25](https://github.com/Ares-Empire/AresOS/pull/25),
with local manifests/logs under `.work/18d-main-merge-fixes-2/`. Six final-head
executions; no optional owner-oracle workflow. No post-CI source/report push
is planned, so acceptance covers the exact reported head.

**Not verified / PLAN-GAP / JUDGMENT-CALL / open questions:** no new production
behavior, owner decision or blocking question. Local policy-read substitution
is diagnostic evidence; real installed-policy acceptance comes from Linux CI.
Real accounts, interactive owner use and laptop installation remain outside
this run. The existing optional-oracle strict-pin migration limit remains;
no oracle pin, design/plan, README/STATE/HANDOFF, OS/mod/install, or reviewer-
authored file was edited. No merge, force-push, hook bypass, system installation,
host setting or disk change. No Gradle ran. Storage audit before the report:
`Remaining .work files over 500 MB: []`.

## Main merge fixes, round 3

**Done:** fixes the two FIX findings in `PACKAGE-REVIEW-5.md`, with changes
confined to `control/mail_tests/sweep_scripts.py`,
`control/mail_tests/test_review23_sweep.py` and the one Scenario-backed clock
jump in `test_review29_lifecycle.py`. No production, oracle, selection,
workflow, design/plan or reviewer-authored file changes.

`Chronology` owns one integer nanosecond counter per inherited Scenario. Each
ambient time read advances it by **10,000 ns**; float seconds are derived from
that integer. This step exceeds floating-point rounding at the fixture epoch
and remains far below approval/quiet-period deadlines. Explicit archive ageing
adds two seconds, expiry advances past `expires_at`, and maintenance adds
86,401 seconds. A temporary jump leaves the chronology at its advanced position
when its scope ends; subsequent float, nanosecond and calendar reads keep
advancing there. The Scenario-backed lifecycle expiry uses this same seam.
The owner-oracle subclass retains its independent existing clock/ID script.

Calendar wrappers cover implicit `localtime`, `gmtime`, `strftime`,
`email.utils.formatdate` and its adapter alias, `datetime.now/utcnow/today` and
`date.today`, including the preimported service aliases. Implicit calendar
views use UTC so replay values do not depend on the worker's timezone. Explicit
calendar inputs do not read or advance the current clock. UUIDs, MIME
boundaries and eight-character PID-isolated temporary names remain scripted.

The timestamp seam preserves real stat metadata (inode, size, owner, mode,
link count). Only time attributes, including tuple positions and
`os.path.getmtime/getctime`, need chronology provenance. `Blobs.put_stream`
runs unchanged, then registers the published data/origin inodes, including
survivors of failed publication/cleanup, with their logical creation time.
Time-attribute reads advance the chronology while returning that immutable
file's recorded age. A native modification-time fingerprint validates the
registration; kernel timestamps never become service values. Recovery may
unlink an old upload hardlink and thereby change ctime without changing the
blob's modification age. The registration therefore follows inode and native
mtime, rather than rejecting that legitimate hardlink cleanup.

The independent Driver's three snapshot-cache paths (main SQLite database,
its rollback journal and the operations log) receive a fresh logical revision
on each timestamp read. This forces real decoding even after same-size writes;
it never freezes a cached snapshot. Other unregistered or modified file
objects fail. No expiry unlink, sync, write, SQLite I/O or fault site is stubbed.

**Source audit (production is read-only):**

| Source | Production locations | Fixture treatment |
| --- | --- | --- |
| Float time | `storage.py:207,246,248,591,645`; `engine.py:157,172,176,219,242,346,392,424`; `retention.py:74`; `archive.py:16`; `mail/adapter.py:520,967,972,985`; `mail/dkim.py:177` | One chronology; DKIM network path not consumed by these remote fixtures |
| Nanoseconds | `engine.py:138`; `warnings.py:36`; `mail/filing.py:413` | Same integer chronology |
| Float-backed recovery notice time | `recovery.py:94,100,106` (retained creation to nanoseconds) | Retained float comes from the same advancing chronology |
| Implicit calendar / explicit conversions | `engine.py:455,461,289`; `mail/adapter.py:529,223,227`; `files.py:120`; `mail/codec.py:414`; `mail/questions.py:51` | Script implicit reads; allow explicit supplied times/dates |
| Blob age | `blobs.py:142`, reached by `retention.py:123` | Registered immutable file age from chronology |
| Import metadata / stability | `files.py:113,120` | Guard timestamp attributes; inherited flows export rather than import caller files, so no ambient import timestamp is allowed |
| Oracle snapshot invalidation | `owner_state_oracle/driver.py:55` | Three explicit paths get chronology revisions when a Driver reuses Scenario |

No other service `st_mtime`, `st_ctime`, `getmtime` or `getctime` consumer was
found. Other stat/fstat calls inspect real size, mode, ownership, inode or link
count. The round-2 UUID audit remains applicable: `storage.py`, `engine.py`,
`testapp.py`, `exports.py`, `results.py`, `warnings.py`, and
`mail/{adapter,filing,onboarding}.py` use `uuid4`; transport/blob staging uses
`tempfile.mkstemp`; stdlib MIME serialization uses `random.randrange`.
`mail/dkim.py:80` has unused-in-these-flows DNS randomness. No inherited flow
uses `make_msgid`, `uuid1`, unseeded private RNG, `secrets` or `os.urandom`.
The exact audit is saved in `.work/18d-main-merge-fixes-3/source-audit.txt`.

**Guard and mutation checks:** the independent outer guard raises
`AmbientRead` (a BaseException, with an independent rejection ledger so a
cleanup finally cannot hide it) for unscripted float/nanosecond time; implicit local/gmtime,
strftime/ctime/asctime; realtime clock_gettime variants; datetime/date current
time; all stat/lstat/fstat time attributes and tuple positions; UUID/random/
secrets/OS entropy; implicit email dates/message IDs; and tempfile names.
Explicit dates, explicit calendar conversions, seeded private RNGs and real
non-time stat fields remain usable. Monotonic timing measures test duration
only and never feeds service state.

Clean replay mutations close one actual component patch at a time, exposing
the guard underneath, independently in setup, call and recovery. **145**
consuming phase/component combinations reject omission: clock 57,
nanoseconds 6, formatdate 14, timestamps 3, IDs 33, MIME 3, paths 29.
Implicit localtime/gmtime/strftime/datetime/date are not consumed by these
healthy flows; the per-flow chronology-view test nevertheless verifies their
single-step reads and each omitted wrapper for all 23 flows.

The complete sweep records source consumption separately during each faulted
call and its recovery. Whenever it discovers a new flow/component/phase in
single, persistent or cleanup-pair mode, it replays that actual witness with
only that component removed, and requires `AmbientRead`. No primary point,
mode, cleanup enumeration, trace-prefix comparison or recovery assertion was
removed. The original full-sweep loops and 12 protected assertion/recovery
methods are AST-identical to the starting head.

**Ordering and expiry regressions:** for every flow the ordering test drives
production `warnings.check_result`, retained intent writes, `recover_intents`
and the real paginated `notice_page`. It creates a checked warning, a later
recovery source and another checked warning; repeats them across a 90,000-second
jump; and creates recovery/checked warnings after the jump scope exits. All
eight timestamps must strictly increase, and every page together must return
the exact newest-first order. The separate chronology-view test verifies all
clock/calendar interfaces, rejects unknown/modified file timestamps, and
requires real blob expiry unlinks and directory fsync after an explicit TTL
jump. The original constant-clock precision counterexample remains isolated
and still demonstrates the SQLite page-boundary mechanism.

**Verified / local:** commands use Python 3.14.6 from the pre-existing
`.work/18d-review/venv/bin/python`, `-B` and
`PYTHONPATH=control:control/mail_tests`, unless stated otherwise. Reproduction
wrappers and exact stdout/stderr are under `.work/18d-main-merge-fixes-3/`.

- `python3 control/generate.py --check`: `Generated artifacts match definitions`.
- Native `python -B -m unittest -v
  test_review23_sweep.FaultSweep23.test_inherited_guard_rejects_ambient_sources`:
  **1 test / OK**, `0.001s`, `local-native-guard.txt`.
- Native three-replay test: **FAILED (failures=14)** at
  `boundary_not_installed` because macOS `/etc` is a symlink. No host policy was
  changed. The following local storage diagnostics substitute only
  `Boundary.read` with generated `managed_settings()`; Linux CI is the evidence
  for the real settings path.
- `local_focused.py`: **11 tests / OK**, `4.899s`,
  `local-focused-final.txt`: ambient guard, clean omissions, three-replay
  determinism for all 23 flows, production ordering, chronology/file-age probes,
  archive determinism, precision mechanism, recovery/completion counterexamples
  and real SQLite main/index VFS faults. The precision probe still prints
  index **300**, `sqlite.main.fsync vs sqlite.main.write; points=[788, 788]`.
- `local_tests.py` with ordering plus the complete lifecycle module, repeated
  three times in one invocation: **36 tests / OK**, `4.790s`,
  `local-order-lifecycle-repeated.txt`.
- `local_consumers.py`: the six Scenario consumer modules' required selection
  passes twice: **41 tests / OK**, `3.410 / 6.193s`,
  `local-consumers-{1,2}.txt`. Modules: `test_review26_sweep`,
  `test_review27_checks`, `test_review28_filing`, `test_review29_lifecycle`,
  `test_owner_state_regressions`, `test_owner_state_sweep`. The complete
  `test_owner_state_regressions` also passes: **6 tests / OK**, `0.361s`,
  `local-regressions.txt`, including the three optional named regressions.
  After the rejection-latch fix, the required consumers pass again (**41 /
  OK**, `7.138s`) and the complete named regressions plus three more
  ordering/lifecycle passes are **42 / OK**, `5.623s`,
  `local-regressions-lifecycle-final.txt`.
- `PYTHONPATH=control:control/tests python -B -m unittest -v
  test_mail_ci_selection`: **6 tests / OK**, `0.201s`, `local-selection.txt`.
  Required sweep selection now includes all **12** tests (two added).
- AST invariants: `12 protected methods unchanged; FLOWS and all full-sweep
  loops unchanged`. No production or forbidden paths changed. Python syntax
  and `git diff --check` pass.

The first local prototype ordering check correctly failed when it attempted
writes in the restore-locked/closed restart fixture before completing that
flow's startup action. The test now calls the production action first.
The first full-sweep attempt exposed the overly strict native ctime
fingerprint on upload-hardlink cleanup; all four diagnostic shards were
stopped, the provenance key was corrected, and the complete sweep restarted.
The optional named-regression module also exposed the Driver snapshot cache's
native timestamp reads; the explicit logical revision seam above fixed that
fixture integration. These are harness fixes, with all original assertions
retained; failed/stopped prototype logs are not passing evidence.
The next full sweep passed three shards but failed three nanosecond omission
checks at send_duplicate's point 551 (single/persistent/cleanup pair). Its
production `sent_copy` finally calls `require_storage`, which can replace the
guard's BaseException with the existing storage refusal. The guard now latches
all rejected reads and raises again at scope exit. A dedicated displaced-error
regression and all three actual point-551 mutations pass; the complete sweep
was restarted on that guard. Production storage-error preservation is unchanged.


- Full sweep on the strengthened guard: `MAIL_SWEEP_SHARDS=4
  MAIL_SWEEP_SHARD=N ... local_tests.py
  test_review23_sweep.FaultSweep23.test_review23_enospc_at_every_discovered_durable_write`
  for N=0–3: **all four / OK**, **447.509 / 322.776 / 400.601 / 180.161s**,
  `local-sweep-{0,1,2,3}.txt`. **23 flows; 6,518 per-flow points; 6,259 single,
  6,259 persistent and 15,979 cleanup-pair cases (28,497 fault cases)**.
  All per-flow counts match round 2's Mac baseline exactly. **306 actual
  fault/recovery omitted-component witnesses** reject: single, persistent and
  cleanup-pair modes, including nanoseconds replaced by a storage finally.
  Linux counts are recorded separately below; Mac counts are not used as
  installed-policy or Linux publication/VACUUM evidence.

**Count table and final Linux acceptance addendum:** the saved before and
round-1 Linux attempts independently agree in every row. This table records
that acceptance floor and the round-3 Mac run; the observed final Linux
attempt-1/attempt-2 columns and all eight job durations per attempt are
recorded in [PR #25](https://github.com/Ares-Empire/AresOS/pull/25) after
the single final push. Keeping post-push evidence there preserves the exact
twice-tested head rather than creating a new report commit/push. The local
machine-readable final ledger is
`.work/18d-main-merge-fixes-3/FINAL-VERIFICATION.json`.

| Flow | Before = round-1 Linux points | Linux S / P / C | Round-3 Mac points | Mac S / P / C |
| --- | ---: | --- | ---: | --- |
| delete_permanent | 395 | 379 / 379 / 711 | 391 | 379 / 379 / 711 |
| settlement | 148 | 144 / 144 / 275 | 148 | 144 / 144 / 275 |
| testapp_export | 144 | 117 / 117 / 534 | 128 | 118 / 118 / 598 |
| filing_rename | 227 | 219 / 219 / 419 | 227 | 219 / 219 / 419 |
| restart_tail | 33 | 22 / 22 / 68 | 29 | 22 / 22 / 68 |
| delete_trash | 265 | 253 / 253 / 475 | 261 | 253 / 253 / 475 |
| status | 147 | 143 / 143 / 272 | 147 | 143 / 143 / 272 |
| attachment_export | 277 | 242 / 242 / 1593 | 261 | 243 / 243 / 1662 |
| filing_copy | 351 | 339 / 339 / 654 | 351 | 339 / 339 / 654 |
| restart_index | 31 | 20 / 20 / 62 | 27 | 20 / 20 / 62 |
| send_duplicate | 912 | 877 / 877 / 1720 | 908 | 877 / 877 / 1720 |
| send | 830 | 797 / 797 / 1567 | 826 | 797 / 797 / 1567 |
| unsubscribe_mailto | 832 | 799 / 799 / 1573 | 828 | 799 / 799 / 1573 |
| cancel | 65 | 63 / 63 / 118 | 65 | 63 / 63 / 118 |
| password | 129 | 119 / 119 / 226 | 125 | 119 / 119 / 226 |
| expiry | 65 | 63 / 63 / 111 | 65 | 63 / 63 / 111 |
| export_rollback | 277 | 246 / 246 / 1765 | 267 | 247 / 247 / 1834 |
| repair | 345 | 334 / 334 / 632 | 345 | 334 / 334 / 632 |
| unsubscribe_https | 329 | 315 / 315 / 590 | 325 | 315 / 315 / 590 |
| restore | 68 | 66 / 66 / 122 | 68 | 66 / 66 / 122 |
| filing_move | 350 | 338 / 338 / 650 | 350 | 338 / 338 / 650 |
| maintenance | 62 | 60 / 60 / 108 | 62 | 60 / 60 / 108 |
| archive | 360 | 347 / 347 / 1670 | 314 | 301 / 301 / 1532 |
| **Total** | **6,642** | **6,302 / 6,302 / 15,915** | **6,518** | **6,259 / 6,259 / 15,979** |

Linux acceptance requires no drop in any per-flow column in either final
attempt. The two delayed restart `journal.close` events explain the two-point
difference between per-flow totals and the pre-recovery mechanism summary,
as in round 2. No close is promoted to a primary fault site.

**Every required Mail job has a 35-minute limit:** `containers (0–3)` and
`sweep (0–3)`. The final addendum records the whole-job duration of each of
these eight jobs independently in attempts 1 and 2, checked against 35:00.
The final report manifest verifies all 23 flows and each mode against both
Linux baselines, identical counts across attempts, all eight Mail jobs
passing per attempt, and the exact final source SHA.


- `OWNER_PERTURB_SHARDS=4 OWNER_PERTURB_SHARD=N ... local_tests.py
  test_owner_state_perturb` for N=0–3: **all four / OK**,
  **1573.373 / 1356.250 / 1483.389 / 1370.508s**. **98 recordings / 110
  partitions / 2,081,423 alterations**, all `slipped=0`; same corpus and counts
  as round 2. One printed regression label represents two separate Driver
  recordings. These long-running workers loaded the chronology revision before
  the latch-only follow-up; the affected complete named regressions and
  lifecycle consumers were rerun with that final guard, as recorded above.
  No oracle/evaluator/expectation/pin was edited. Logs:
  `local-perturb-{0,1,2,3}.txt`; aggregate check: `FINAL-LOCAL.json`.

**Final-head CI / execution accounting:** commit this report locally, then
push exactly once, including the local brief/reviews commit `3615e4a4` and the
two fixture commits. Require Control base, all eight Control Mail jobs, and
Control boundary to pass; request exactly one whole-run `gh run rerun <id>`
for each same run. No optional oracle workflow. The final source SHA, run IDs,
both attempts, all 23 observed Linux count rows and all sixteen Mail job
durations are the post-push acceptance addendum in
[PR #25](https://github.com/Ares-Empire/AresOS/pull/25), with exact logs and
`FINAL-VERIFICATION.json` under `.work/18d-main-merge-fixes-3/`. No post-CI
source/report push is planned; those results must cover this exact head.

**Not verified:** real accounts, interactive owner use and laptop installation
remain outside this fixture-only run. Local policy-read substitution is only
diagnostic; real managed-policy/ownership checks require the Linux workflows.

**JUDGMENT-CALL:** none affecting product behavior or an owner decision. UTC
calendar views, a 10-microsecond step and logical inode age are reversible
fixture choices; no real user clock, timestamp or timezone is changed.

**PLAN-GAP / open questions:** no new production defect or blocking question.
The pre-existing optional owner-oracle strict-pin migration limit remains
unchanged. Post-push CI counts/durations live in the PR acceptance addendum so
recording them cannot invalidate the sole final push's tested head. No merge,
force-push, hook bypass, system installation, host-setting or disk changes;
no Gradle ran. The closing storage audit printed
`Remaining .work files over 500 MB: []`.
