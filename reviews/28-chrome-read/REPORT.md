# Package 28: Chrome read

**Status:** Fix round X1 is implemented and locally green; hosted double validation is pending.
PR #72 remains draft. The final code/run evidence for X1 is recorded below; step 14's runs are historical.

## Fix round X1 (2026-11-18, Codex gpt-6-astra)

**Done / read:** Started at `e5493c1e`, with reviewed code `659e7164`. Fetched origin first.
Main is `7417c19a`; `git diff --name-only HEAD...origin/main` has no overlap with this round's
changed paths, so **no main merge**. PR #72 stays draft on `pkg/28-chrome`.
Commits: `955f10e5` (reader withholding/state and Node regressions), `14064439` (fragment filtering,
reference cleanup, complete option reads and Python regressions), `427cd1e0` (X1 evidence), and
`52891587` (explicit route commitment and question-mark-in-name regression; final code head).
The closing evidence commit changes only review documents. Every new commit has
`Built-by: gpt-6-astra` as its final line.

| Finding | Fix and regression (repo-relative file:line) | Actual baseline failure on `659e7164` |
|---|---|---|
| Security blocker 1: presentational textarea | Native controls retain their safe description path; textarea default text never enters the outline's generic walker. `control/chrome_tests/fix-x1.test.mjs:14` tests both roles, watched/unwatched/late-root histories, every typed-input kind, credential-protected nontext controls, select/button/editor, and outline/full/find through `Engine.request`, including typed-field counts and throwing getters. | Six history cases fail because default text reaches the service result; protected-credential cases already pass. |
| Security blocker 2: fragment slash | Only an explicit leading `/route?query` selects route parsing; every other assignment fragment stays parameter-filtered. Slashes in any value cannot change that; ordinary `#/inbox/thread/1` and route queries remain readable. `control/chrome_tests/test_fix_x1.py:17` independently lists every brief credential name, all slash positions and the review examples. | Credential values survive in the public address, including `otp` beside `next=/home` and the initial portion of `access_token=fixture/part`. |
| Security should-fix 3: leaked references | `Chrome.outline` trims every requested tab in `finally`, after success or any failure, including cursor validation, envelope fitting and measurement. `control/chrome_tests/test_fix_x1.py:60` repeats four failure modes three times through `Engine.request` on 6,000 controls and checks both indexes. | Each failure mode retains 6,001 → 12,002 → 18,003 references. Fixed: at most 5,000 after every call. |
| Package should-fix 1: field state | File-state digest includes the ordered filenames. The existing selected-option bits remain. `control/chrome_tests/fix-x1.test.mjs:41` independently tests token, until and cursor for same-count file replacement and selection changes, with actual reader snapshots fed to the service. | All three file tests fail: equal digest, until false, cursor accepted. Selection already passes on the baseline; replacing its digest with a constant in scratch now fails **all three** tests (the review's surviving mutation is killed). |
| Package should-fix 2: full options | Full page/subtree reads fetch every incomplete list in their scope before rendering, under the existing tab/command deadline; ordinary form-detail limits remain. `control/chrome_tests/test_fix_x1.py:116`, `:119`, `:122`, `:141`: F4's page/form full reads reconstruct all 200 options across max-1,000 pages, stay within 48 KiB/7 seconds, scope requests to the form, and return not_read on options expiry. | Page and form return only 50 labels; no options command runs, so deadline/scope checks fail too. |
| Package should-fix 3: long label | Ordinary option labels use the normal 200-character quoted-text budget and omitted count. A cut line carries the select's reference, whose detail pages return every full label. `control/chrome_tests/test_fix_x1.py:160`. | The 10,000-character label has no 200-character cut/9,800 omitted marker. |
| Withholding sibling: legacy generic role | `snapshot` no longer copies native control child text into a generic fallback name after safeValue withheld the field. `control/chrome_tests/reader.test.mjs:929` starts with a real textarea-kind double, then other typed controls, a throwing value getter, and checks retained filled status and asking-field count. | `role=generic` leaks the textarea's default marker into its name. |
| Address sibling: later question mark | The same parameter commitment prevents `?` after a credential value from starting route-query parsing, and preserves credential filtering when `?` belongs to the name (`otp?x`); ambiguous assignment-like sign-in routes are conservatively hidden. `control/chrome_tests/test_fix_x1.py:41` and the sign-in-route checks at `:38`. | Three `#otp=fixture-value?.../home` variants and `#otp?x=fixture-value&next=/home` expose the value. Existing sign-in route hiding remains covered. |

**Sibling search / read:** Inspected `ownPassword`, credential signals, `safeValue`, `name`, all text walkers,
outline role/description dispatch, legacy snapshot/compose/adapter reads, and address site/path/query/fragment
routing. Found the two siblings above. No additional withholding bypass or later-character parser switch was
found. The accepted ordinary-name short-code and unmasked-editor choices are unchanged. No approval, asking,
input, binding or hold behavior changed beyond the specified withholding fixes.

**NITs / read:** Cursor refusal now says exactly `page changed, read again without the cursor`;
`test_view_paging.py:121` and `test_view_references.py:205` pin it. The inherited shared form refusal stays
verbatim: main's `test_questions.py:471` / `:476` and `background.test.mjs:1223` pin its reload instructions.
This is an explicit exception to the brief's fixed form sentence, as permitted in the X1 request.
KNOWN-LIMITS separates the native message/chunk/assembly/decoder bounds. The old report now distinguishes
nine identical named functions from the two unchanged dispatched typed-read branches.

**Verified / run:** All baseline source was extracted with `git archive 659e7164` under
`.work/x1/baseline/`, with only the new tests/helper copied in. Nothing under `.work/` is committed.
The tests descend from `.work/security-28/pkg28-reader-probe.mjs`, `pkg28-late-root-probe.mjs`,
`pkg28-service-probe.py` and `.work/review-28/probe-reader.mjs`; the shared DOM helper was moved from the
existing outline suite without changing that suite's assertions.

- Baseline: `.work/x1/baseline-node.log`: **18 tests, 9 pass / 9 fail**; sibling reader: **1 fail**;
  `.work/x1/baseline-python.log`: **8 tests, 160 failing subcases**, no errors. The select constant mutation:
  `.work/x1/select-mutation.log`: **3 tests, 3 fail**. Baseline reader restored afterward.
- `.work/step13a/node-v22.15.0-linux-x64/bin/node --test control/chrome_tests/*.test.mjs`:
  **567 tests, 567 pass**, 0 failed/cancelled/skipped/todo, 32,649.956651 ms (`.work/x1/final-node-suite.log`).
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_outline_action test_view_references test_view_paging test_view_hostile test_questions test_efficiency test_credentials test_bridge test_fix_x1 test_view_address test_view_nodes test_view_outline test_view_budgets test_outline_time`:
  **281 tests in 32.930s, OK** (`.work/x1/final-python-suite.log`). EFFICIENCY MISS lines are the unchanged negative test.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control python3 control/generate.py --check`:
  **Generated artifacts match definitions**. Chrome instructions: **4,093 / 4,096 characters**.
- AST comparison against `origin/main`: nine named functions identical, plus the typed-read branch inside
  `prepare` and the typed-read branch inside `call`, separately, identical (`.work/x1/asking-ast.log`).
- `git diff --check`: clean. No `.work/` file exceeds 500 MB. No local browser or owner profile, Gradle, OS tool,
  system installation, mount, desktop window/input or process-name stopping used.

**Verification corrections / run:** The first long-label baseline probe hit StopIteration because its
10,000-character line started on the next page; max 40,000 exposes the entire baseline line and gives the
intended failed cut assertion. The first Engine-test import hit a circular import; importing the shared
Action definition first fixed the harness. Neither is counted as product evidence. Two brief local suite
overlaps occurred while collecting asynchronous results; the final results above are actual completed runs.

**Runs:** Round 1 on `427cd1e0`: Control Chrome `44297668466`, qualification `44297668419`,
both watched with `--interval 60`, then cancelled as superseded. Before completion, final review of the parser
found the question-mark-in-name sibling; its extended baseline fails and the correction passes **27 tests in
1.969s, OK** (`test_fix_x1 test_view_address`, `.work/x1/address-followup.log`). After normal cancellation,
queued always-run cleanup jobs kept the obsolete runs open and blocked qualification's concurrency group;
GitHub's force-cancel endpoint closed those two exact run IDs. Neither cancelled run is green evidence.

Final code head: `5289158712b40a6b71ceae74266ba40920caf7d7`. Round 2 validates it, then round 3 reruns
both entire green runs on that same head. All watches use `gh run watch <id> --exit-status --interval 60`.

| Workflow | Run ID | Attempt | CI round | Result |
|---|---|---|---|---|
| Control Chrome | `44298565749` | 1 | 2 | success; 28/28 jobs |
| Control Chrome qualification | `44298565614` | 1 | 2 | success; 34/34 jobs |
| Control Chrome | `44298565749` | 2 | 3 | success; 28/28 jobs (whole-run rerun) |
| Control Chrome qualification | `44298565614` | 2 | 3 | success; 34/34 jobs (whole-run rerun) |

No workflow dispatch, force push, approval bypass, ready marking or merge.

**JUDGMENT-CALL:** Ambiguous assignment-like sign-in routes hide the whole fragment rather than guessing that
part of a credential is a route name. Ordinary routes remain readable; reversing this would require changing
one parsing branch and its regression. This is the requested fail-toward-redaction choice. A cut option line
uses its existing select reference (whole field detail), avoiding a new option-reference identity format.

**PLAN-GAP:** The shared inherited form sentence is the main-pinned exception above. Selected-option hashing
already existed; the missing protection was regression coverage, now demonstrated by the killed mutation.
**Not verified:** Owner-profile/manual use; this round uses synthetic fixtures only.
**Left:** A fresh Codex astra recheck of both reviews, then the lead's merge. PR #72 remains draft.


## Done

**read:** Package 28 builds the compact Chrome read behind `ARESOS_TEST_CHROME_OUTLINE=1`, preserving
brief 20's public tools. It adds safe node collection, service rendering, short read references, folds,
whole-text paging, `find`, `until`, several-tab reads, bounded transport deadlines and efficiency gates.
The credential/history rules and unread-form refusal apply to the existing tools as well. The lead accepts
step 13d's repaired comparisons and unique raw-option lookup. Build history, including all failures and
superseded handoffs, remains in [PROGRESS.md](PROGRESS.md).

**read:** Step 14 merges main, freezes one measured latency comparison and writes this report,
[HARNESS-MAP.md](HARNESS-MAP.md) and [KNOWN-LIMITS.md](KNOWN-LIMITS.md). No authored runtime or test code,
workflow, tool description or instruction text changes in this step. The existing
[draft PR #72](https://github.com/Ares-Empire/AresOS/pull/72) remains on `pkg/28-chrome`, unmerged and draft.

### Files and behavior built in steps 1–13d

| Area | What was built / source |
|---|---|
| `control/aresos_control/chrome/nodes.py`, `view.py` | validated node tree; fixed roles/states, own-text order, one escaping rule, folds and exact counts, table/list/form/detail reads, literal find and paths, whole-text cursors and 48 KiB result fitting |
| `control/aresos_control/chrome/references.py` | five random consonants once per service run, one increasing counter across tabs, identities bound to session/frame/document/reader/element, newest 5,000 returned refs per tab, no string reuse, close/release cleanup |
| `control/aresos_control/chrome/address.py` | public and short address forms: no userinfo, credential/opaque values hidden, ordinary queries retained, percent encoding, length bound |
| `control/aresos_control/chrome/credentials.py`, `control/chrome/extension/reader.js` | versioned credential-name rules; late-root history withholding; unread inputs never filled; outline/options/page_state collection; fixed roles, integer node ids, node/omission cap |
| `control/aresos_control/chrome/adapter.py`, `definitions.py` | test-only action and input checks, several independent tab results, options expansion, state-based waits, measured envelope, per-tab and whole-call refusals, current-session close/release cleanup |
| `control/aresos_control/chrome/deadline.py`, `bridge.py`, `control/aresos_control/engine.py` | request-wide read clock before pending checks; time-left on commands, equal remaining time shares, late reply drain by id, unchanged socket bound, unchecked pending validity |
| `control/chrome/extension/background.js` | three read commands and bounded queue/frame waits, script embedder identity check, common native UTF-16 repair boundary and repaired fresh-fact comparisons, unique raw option resolution |
| `control/chrome/ci/` | synthetic F1–F7/H1/address/unread/asking fixtures; exact named browser cases; stored outlines and provenance; full boundary/getter recordings; time transports; paired efficiency probe using brief 20's tools well |
| `control/chrome_tests/` | renderer/reference/address/hostile/paging/credential/deadline/switch tests, native decoder and comparison regressions, named removal mutations, independent inventory/completeness tests |
| `control/chrome/ci/efficiency-baseline.json` | original eleven-task baseline frozen from run 43705060936; step 14 adds exactly one package-28 comparison, without editing any other frozen field |

### Main merge and commits

**read:** `git fetch origin`, then `git merge --no-commit origin/main` (ordinary `git merge` with its commit
held for inspection) merged main `774d7954` into starting head `4153801d`. Git printed
`Automatic merge went well; stopped before committing as requested`. There were **no conflicts and no
manual resolutions**. Main contributes PR #58 (`beb42ec8`, Control tools in the image), PR #97 (`4737bb69`,
idle-loop timing tests), and handoffs. The merge carries 54 paths, 11,610 insertions and 58 deletions.
`git diff --exit-code f282553b^1 f282553b -- control/chrome control/chrome_tests control/aresos_control/chrome control/generated`
returns 0: no Chrome package change from the merge. Main's image/service-user and timing changes are retained.

| Step 14 commit | Contents |
|---|---|
| `f282553ba631b189383ee5d1591f7544528ce918` | standalone merge of main; normal push, no CI skip |
| `659e71647096c52914ae0fbeeb2e6f3ee21dbace` | baseline comparison, harness map, known limits, report and short step-14 history; normal push, no CI skip; final validation head |
| report-only commit containing this final table | only `reviews/28-chrome-read/REPORT.md`; `[skip ci]`; no runtime, test, baseline, map or history change |

Every step 14 commit ends with `Built-by: gpt-6.1-sol`. The last commit changes **only this report**;
the four final executions validate the preceding final validation head. No force push, no bypassed privacy
hook, no PR merge/readiness change, no workflow dispatch and no failed-only rerun.

### Reader rules: inherited versus added

**read:** The merged reader already tracked watched-from-start documents, typed input/textarea eligibility,
filled/empty withholding for unknown history, persistent password/mask history, ordinary nontext values,
editable-area text, a per-install reader instance, and the older credential expressions. The merged asking
read already bound connection, tab, frames, readers, elements, exact question/list and one call; the merged
adapter/background already refused forms with withheld text. See step 5's “What the merged reader already
does of item 1”, and the source locations below.

**read:** Package 28 adds the versioned credential words for typed fields (hidden form tokens remain ordinary),
keeps filled typed fields unread for the life of a late-met shadow root, makes the asking read eligibility
follow that same mark, and uses those existing refusals for the stricter field set. The optional early-root
meeting refinement was not built. It adds new outline collection rather than changing brief 20's reference
or expected-state shapes. The exact old/new harness consequences are listed in HARNESS-MAP.

| Rule | Source, final code lines |
|---|---|
| Credential rule / six signals | [reader.js:151](../../control/chrome/extension/reader.js#L151) |
| Late-root history mark | [reader.js:173](../../control/chrome/extension/reader.js#L173) |
| safeValue / unknownHistory | [reader.js:289](../../control/chrome/extension/reader.js#L289) |
| Asking eligibility follows the field mark | [reader.js:320](../../control/chrome/extension/reader.js#L320) |
| Unread input refusal | [reader.js:857](../../control/chrome/extension/reader.js#L857) |
| Native hidden getter | [reader.js:35](../../control/chrome/extension/reader.js#L35) |
| Refusal helper / fixed tool text | [adapter.py:68](../../control/aresos_control/chrome/adapter.py#L68) |
| payload refuses before binding/prepare/reload | [adapter.py:887](../../control/aresos_control/chrome/adapter.py#L887) |
| steps routes held submissions through payload before reserve | [adapter.py:1029](../../control/aresos_control/chrome/adapter.py#L1029) |
| Request clock before pending resolution | [engine.py:753](../../control/aresos_control/engine.py#L753) |
| Bridge bounded context | [bridge.py:35](../../control/aresos_control/chrome/bridge.py#L35) |
| Bridge reply drain | [bridge.py:58](../../control/aresos_control/chrome/bridge.py#L58) |
| Bridge timed call | [bridge.py:129](../../control/aresos_control/chrome/bridge.py#L129) |
| Extension dispatch / deadline | [background.js:1010](../../control/chrome/extension/background.js#L1010) |
| Embedder identity | [background.js:152](../../control/chrome/extension/background.js#L152) |
| Native representation and common boundary | [background.js:340](../../control/chrome/extension/background.js#L340) |

**read / checked locally:** AST comparison with merged `origin/main` finds `binding`, `prepare`, `question`,
`revalidate`, `changed_compose`, `execute`, `command`, `trusted`, `typed_binding`
identical in `adapter.py` (nine named functions). Separately, the dispatched `prepare_read_typed_fields`
branch inside `prepare` and `read_typed_fields` branch inside `call` are unchanged. Inspection command:
`git diff origin/main -- control/aresos_control/chrome/adapter.py`; compare those named AST function bodies
(ignoring source locations), or read the diff hunks: no body of an asking-path function changes.
`git diff --exit-code origin/main -- control/generated control/aresos_control/chrome/sites.py control/aresos_control/chrome/policy.py control/chrome/extension/policy.js control/chrome/extension/guard.js control/chrome/extension/page.js`
returns 0. Generated ask rules, public tool schemas/descriptions and instructions match main byte for byte.
The background's fresh-fact comparisons are the explicitly accepted step-13d change; they repair copies to
what the service/owner saw and still refuse visible or identity changes. No broad normalization was added.

## Verified

### Local commands on the merge

**run:** These were run from the repository root, sequential suites, after checking available memory
(8,721 MiB). Portable Node already existed under `.work/step13a/`; no install/download was needed.

| Command | Actual result |
|---|---|
| `.work/step13a/node-v22.15.0-linux-x64/bin/node --test control/chrome_tests/*.test.mjs` | 548 tests / 548 pass / 0 fail / 0 cancelled / 0 skipped / 0 todo; 32,561.287 ms |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_outline_action test_view_references test_view_paging test_view_hostile test_questions test_efficiency test_credentials test_bridge` | `Ran 150 tests in 21.300s`, `OK`; synthetic EFFICIENCY MISS lines are the expected negative summary test |
| `PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/.work/step14/pkg28-tmp" PYTHONPATH=control:control/chrome_tests python3 -m unittest test_efficiency` after the comparison append | `Ran 17 tests in 0.011s`, `OK`; expected synthetic MISS lines again |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control python3 control/generate.py --check` | `Generated artifacts match definitions` |
| `instructions_for('chrome')` length assertion | `Chrome server instructions: 4093 characters` |
| Chrome/generated merge-diff check and asking-function AST comparison above | exit 0 / nine named functions IDENTICAL; two dispatched branches unchanged |
| Step 14 authored-file whitespace, relative link, inventory and baseline-preservation audit | exit 0; all 36 new browser names map exactly once, Python names and repo-relative links resolve, frozen baseline preserved and the single comparison equals the green summary |
| Pre-push privacy hook / workflow shell check | both normal code/doc pushes accepted by the privacy hook; local workflow shell exits 0: `No file holds a home path with a real user name.`; merge and final-head Repo privacy workflows are green |

**run / not green:** a raw `git diff --cached --check` before the merge commit reported Markdown hard-break
whitespace in review files carried directly from main; checking the branch against main also found the
existing blank final line in `control/chrome_tests/outline.test.mjs`. These were not authored here and were
left intact. The first staged-document check also caught one extra blank line at REPORT.md's end; it was
removed before committing. Step 14's own changed files pass the final staged diff check. No Gradle or Minecraft check
applies to this Chrome-only brief; no OS test suite or owner module was run.

### Hosted runs and final-head double green

**run:** Every run was watched with `gh run watch <id> --exit-status --interval 60`, with one watcher per
run. Round 1 is the merge pair. Round 2 is the baseline/documents final-head pair. Round 3 is a whole rerun
of each round-2 run with `gh run rerun <id>`, without `--failed`. A GitHub whole-run rerun retains its database
run ID and increments `run_attempt`: the four final executions therefore have two distinct run IDs and four
run/attempt identities. Both attempts must be green on the same final validation head.

| Round / head | Workflow | Run ID / attempt | Result |
|---|---|---|---|
| 1 / `f282553b` | Control Chrome | [44226934670](https://github.com/Ares-Empire/AresOS/actions/runs/44226934670) / 1 | **success, 28/28 jobs**; both cores, both latency profiles and both aggregates pass |
| 1 / `f282553b` | Control Chrome qualification | [44226934711](https://github.com/Ares-Empire/AresOS/actions/runs/44226934711) / 1 | **success, 34/34 jobs**; both independent pairs, both combines and publish verification pass |
| 2 / `659e71647096c52914ae0fbeeb2e6f3ee21dbace` | Control Chrome | [44255375396](https://github.com/Ares-Empire/AresOS/actions/runs/44255375396) / 1 | **success, 28/28 jobs** |
| 2 / `659e71647096c52914ae0fbeeb2e6f3ee21dbace` | Control Chrome qualification | [44255375583](https://github.com/Ares-Empire/AresOS/actions/runs/44255375583) / 1 | **success, 34/34 jobs** |
| 3 / `659e71647096c52914ae0fbeeb2e6f3ee21dbace` | Control Chrome | [44255375396](https://github.com/Ares-Empire/AresOS/actions/runs/44255375396) / 2 (whole run) | **success, 28/28 jobs** |
| 3 / `659e71647096c52914ae0fbeeb2e6f3ee21dbace` | Control Chrome qualification | [44255375583](https://github.com/Ares-Empire/AresOS/actions/runs/44255375583) / 2 (whole run) | **success, 34/34 jobs** |

**run:** Merge-head regression workflows were also watched at 60 seconds and completed successfully:

| Head | Workflow | Run ID | Result |
|---|---|---|---|
| `f282553b` | Control base | [44226934824](https://github.com/Ares-Empire/AresOS/actions/runs/44226934824) | success |
| `f282553b` | Control boundary | [44226934684](https://github.com/Ares-Empire/AresOS/actions/runs/44226934684) | success |
| `f282553b` | Control Mail | [44226934661](https://github.com/Ares-Empire/AresOS/actions/runs/44226934661) | success |
| `f282553b` | Repo privacy | [44226934706](https://github.com/Ares-Empire/AresOS/actions/runs/44226934706) | success |

**run:** Final-head regression workflows also completed successfully, each watched with `--interval 60`:

| Head | Workflow | Run ID | Result |
|---|---|---|---|
| `659e7164` | Control base | [44255375419](https://github.com/Ares-Empire/AresOS/actions/runs/44255375419) | success |
| `659e7164` | Control boundary | [44255375477](https://github.com/Ares-Empire/AresOS/actions/runs/44255375477) | success |
| `659e7164` | Control Mail | [44255375414](https://github.com/Ares-Empire/AresOS/actions/runs/44255375414) | success |
| `659e7164` | Repo privacy | [44255375563](https://github.com/Ares-Empire/AresOS/actions/runs/44255375563) | success |


**run:** Downloaded completed-job logs confirm all 36 new mandatory case names end in `PASS` exactly once in every core below: merged main, then both final-head attempts. Each log also identifies `BROWSER_SHARD: core`. Line numbers are in `gh run view <run> --attempt <attempt> --job <job> --log` output. The completion line follows the named cases. The five Control Chrome time lines are four required checks plus their overall PASS; qualification excludes those time-only checks.

| Run / attempt | Core job | 36 named PASS lines, first–last | Shard complete line | Time PASS lines |
|---|---|---|---|---|
| 44226934670 / 1 | [134545688862](https://github.com/Ares-Empire/AresOS/actions/runs/44226934670/job/134545688862) | 5600–5637 | 5639 | 5517, 5518, 5519, 5520, 5521 |
| 44226934670 / 1 | [134545688930](https://github.com/Ares-Empire/AresOS/actions/runs/44226934670/job/134545688930) | 5576–5613 | 5615 | 5493, 5494, 5495, 5496, 5497 |
| 44226934711 / 1 | [134600716138](https://github.com/Ares-Empire/AresOS/actions/runs/44226934711/job/134600716138) | 5706–5743 | 5745 | not in qualification |
| 44226934711 / 1 | [134600716154](https://github.com/Ares-Empire/AresOS/actions/runs/44226934711/job/134600716154) | 5704–5741 | 5743 | not in qualification |
| 44255375396 / 1 | [134640845895](https://github.com/Ares-Empire/AresOS/actions/runs/44255375396/job/134640845895) | 5584–5621 | 5623 | 5501, 5502, 5503, 5504, 5505 |
| 44255375396 / 1 | [134640845842](https://github.com/Ares-Empire/AresOS/actions/runs/44255375396/job/134640845842) | 5603–5640 | 5642 | 5520, 5521, 5522, 5523, 5524 |
| 44255375583 / 1 | [134635838744](https://github.com/Ares-Empire/AresOS/actions/runs/44255375583/job/134635838744) | 5729–5766 | 5768 | not in qualification |
| 44255375583 / 1 | [134635838789](https://github.com/Ares-Empire/AresOS/actions/runs/44255375583/job/134635838789) | 5728–5765 | 5767 | not in qualification |
| 44255375396 / 2 | [134697517555](https://github.com/Ares-Empire/AresOS/actions/runs/44255375396/job/134697517555) | 5584–5621 | 5623 | 5501, 5502, 5503, 5504, 5505 |
| 44255375396 / 2 | [134697517762](https://github.com/Ares-Empire/AresOS/actions/runs/44255375396/job/134697517762) | 5584–5621 | 5623 | 5501, 5502, 5503, 5504, 5505 |
| 44255375583 / 2 | [134698337037](https://github.com/Ares-Empire/AresOS/actions/runs/44255375583/job/134698337037) | 5727–5764 | 5766 | not in qualification |
| 44255375583 / 2 | [134698337449](https://github.com/Ares-Empire/AresOS/actions/runs/44255375583/job/134698337449) | 5767–5804 | 5806 | not in qualification |

**run:** No CI job failed in these three rounds, and no flaky-job retry was needed. `gh run rerun 44255375583` printed `failed to rerun: HTTP 502: Server Error`; a single `gh run view 44255375583 --json databaseId,headSha,status,attempt,conclusion` read-back confirmed attempt 2 queued on the correct head. The request was accepted and was not sent again. The Chrome rerun request exited 0. A parallel `gh run view 44255375396 --attempt 1 --job 134640845895 --log` download printed `failed to get run log: opening cache entry: zip: not a valid zip file`; fetching that log with isolated repo-local `XDG_CACHE_HOME` and `TMPDIR` exited 0. These were API/download responses, not test failures. All later job-log downloads used isolated repo-local caches, and no extra workflow was dispatched.


**read / historical:** Step 13d's final code pair, 44207652690 / 44207652784 on `e07a88eb`, already passed
28/28 and 34/34 jobs, with every H1, stored-outline, asking and unread case passing in all four cores.
That earlier pair is provenance, not final-head double-green evidence. Earlier binding tests were built
against merged PR #27; their exact merged-main sequence and failure history is in steps 6–13d. This report
does not claim a separate pristine-main run that was not executed.

### Frozen baseline and measured read rows

**run / historical:** Original baseline run [43705060936](https://github.com/Ares-Empire/AresOS/actions/runs/43705060936),
head `86cac83db6a6d7fbe23fa03116c73e20ef37a27a`, one warm-up then five measured runs, hosted x64
ubuntu24 runner (4 vCPUs, AMD EPYC 7763, 16,760,344,576 bytes memory), portable Node v22.23.5 and the exact
Chrome package recorded in the JSON. Original sizes: 30 tools, 5,085 description characters, 4,052 server
instruction characters, 9,137 combined, 11,080 tool-name/schema characters. These frozen values are retained;
merged main now has **4,093 instruction characters**, 9,178 combined, unchanged in this package. The brief's
4,081 figure describes an earlier main. No instruction text was added by this step or by package 28.

**run:** Side-by-side measurement from merge run 44226934670 attempt 1 (efficiency artifact), one warm-up and five runs each.

| Task | Frozen old calls / chars / median ms | New calls / chars (max) / median ms | Same-run old ms / allowed new ms | Budget calls / chars |
|---|---|---|---|---|
| `outline_f1_first_read` | 1 / 17,840 / 74.6 | 1 / 3,955 (4,003) / 40.9 | 69.8 / 126.8 | 1 / 6000 |
| `outline_f1_everything` | 14 / 252,427 / 998.6 | 2 / 60,682 (60,763) / 74.9 | 867.4 / 1004.1 | 3 / 75000 |
| `outline_f1_fields` | 2 / 17,910 / 160.3 | 1 / 5,115 (5,141) / 29.7 | 143.8 / 208.2 | 1 / 6000 |
| `outline_f2_table` | 53 / 992,014 / 12338.5 | 1 / 23,121 (23,121) / 64.1 | 11217.5 / 12389.3 | 1 / 23600 |
| `outline_f3_find_link` | 1 / 1,870 / 80.7 | 1 / 450 (450) / 42.0 | 74.9 / 132.4 | 1 / 800 |
| `outline_three_tabs` | 3 / 55,301 / 430.5 | 1 / 4,995 (4,995) / 123.7 | 387.9 / 476.7 | 1 / baseline only |

All six rows pass; no read_row_misses. Frozen acting rows remain in the JSON for 28a.


F4's old outcome is `asking_input_too_large`, a refusal, not a delivered form. The lead accepted that
baseline: four calls and 23,953 characters through refusal, median 5,210.1 ms. The 28a comparison must say
what its old side did, and cannot invent an old send timing. Setup/initial reads named “after the first read”
are outside each task's count and clock, exactly as the brief and `efficiency-summary.py` specify.

### Latency entry and unchanged ceilings

**run:** The one `latency_comparisons` entry is copied exactly from `efficiency-summary.py`'s
`latency_comparison` in `chrome-efficiency-44226934670-1/efficiency-measured.json`: run **44226934670**,
recorded SHA **`d90ff73ab56dbfec3c6946e5971d41e46ce06e82`**, branch head `f282553ba631b189383ee5d1591f7544528ce918`.
The SHA is the workflow's `GITHUB_SHA` (PR merge tree when applicable); the branch head identifies the
reviewed commit. The frozen baseline's original run/sha and all eleven tasks remain byte-value identical.

- Old `chrome_read`: **69.8 ms**, samples `[69.2, 65.3, 71.7, 69.8, 71.0]`.
- New `chrome_outline`: **40.9 ms**, samples `[39.9, 40.9, 43.5, 40.4, 41.4]`.
- Ceiling: **126.8 ms** = rounded 1.10 × old median + 50 ms; **PASS**, with
  85.9 ms headroom. One warm-up is excluded; five runs measured.

The comparison is measured before the documents/baseline commit so it can be frozen in that commit, as
step 14 explicitly directs. The final validation head has the identical runtime/test code and is tested twice.
No older comparison was added, and the entry is not replaced by a later runner's numbers.


The paired existing latency gate remains unchanged. Each profile tests fresh, history-1,000 and history-4,000
with 60 current-runtime samples and 20 old-runtime samples per call; allowances use the paired old runner's
slowdown against the frozen reference, floored at 1. A median/p95 ceiling miss or paired regression fails.
The disk-sync-count gate also remains. Nominal ceilings in milliseconds:

| Read | Navigate | Free click | Fill | Asking click | Approval to done |
|---|---|---|---|---|---|
| 35 / 60 | 100 / 150 | 650 / 750 | 650 / 750 | 60 / 100 | 700 / 850 |

**run:** The uploaded current/paired summaries were rechecked locally with the unchanged `latency-check.py`, frozen reference and targets: plain and audit both return `passed: true`, `failures: []`, `sync_failures: []`. Maximum observed client median / p95 over the three history phases (ms):

| Call | Nominal ceiling median / p95 | Plain maximum median / p95 | Audit maximum median / p95 |
|---|---|---|---|
| `read` | 35 / 60 | 23.10 / 23.97 | 19.46 / 20.08 |
| `navigate` | 100 / 150 | 54.44 / 58.05 | 43.16 / 45.50 |
| `free_click` | 650 / 750 | 582.65 / 586.62 | 572.44 / 577.36 |
| `fill` | 650 / 750 | 575.68 / 577.23 | 563.23 / 579.25 |
| `asking_click` | 60 / 100 | 30.34 / 31.73 | 24.81 / 25.66 |
| `approval_to_done` | 700 / 850 | 586.91 / 588.73 | 577.35 / 579.04 |

All these maxima also fit the unscaled ceilings. The actual gate still checks every phase, uses paired runner factors (plain 1.023–1.059; audit below 1, floored to 1), reference regression and sync counts. This is the existing public-tool latency gate; F1's internal-outline comparison above is a separate group-16 measurement.

Reproduction: run `python3 control/chrome/ci/latency-check.py` with `.work/step14/merge-latency-<profile>-current/latency-summary.json`, `.work/step14/merge-latency-<profile>-old/latency-summary.json`, `control/chrome/ci/latency-reference.json`, and `control/chrome/ci/latency-targets.json`, once for `plain`, then once for `audit`. Both exact four-input invocations were run sequentially; both exit 0. Artifacts: `chrome-efficiency-44226934670-1` (id 14395736529), current/old plain (14396080980 / 14396250590), current/old audit (14394718668 / 14394768647). ZIPs were deleted after extracting the selected records.


### Returned fixture outlines

**read / run provenance:** The five stored browser outlines below come from run 44106253829 attempt 1,
artifact `control-chrome-44106253829-1-policy-core`, code `7d352d7b`, named calls in
`control/chrome/ci/outline-expected/source.json`. Final runs compare them character for character after
normalizing reference identity only. Long fixtures are shown by their first 40 lines. F2 table and F4 detail
formats are covered by named tests; F5 and later F7 navigation budgets belong to 28a.

**F1** (48 lines; first 40 shown): [f1.txt](../../control/chrome/ci/outline-expected/f1.txt).

```text
p "Paragraph 0 readable article text readable article text readable article text readable article text readable article text readable article text readable article text readable article text readable art"…+251 REF1
p "Paragraph 1 readable article text readable article text readable article text readable article text readable article text readable article text readable article text readable article text readable art"…+251 REF2
p "Paragraph 2 readable article text readable article text readable article text readable article text readable article text readable article text readable article text readable article text readable art"…+251 REF3
p "Paragraph 3 readable article text readable article text readable article text readable article text readable article text readable article text readable article text readable article text readable art"…+251 REF4
p "Paragraph 4 readable article text readable article text readable article text readable article text readable article text readable article text readable article text readable article text readable art"…+251 REF5
… 115 more (52,569 characters) REF6
form → GET http://fixture.test:8765/?… REF7
  textbox "Field 0" = "Synthetic value 0" REF8
  textbox "Field 1" = "Synthetic value 1" REF9
  textbox "Field 2" = "Synthetic value 2" REF10
  textbox "Field 3" = "Synthetic value 3" REF11
  textbox "Field 4" = "Synthetic value 4" REF12
  textbox "Field 5" = "Synthetic value 5" REF13
  textbox "Field 6" = "Synthetic value 6" REF14
  textbox "Field 7" = "Synthetic value 7" REF15
  textbox "Field 8" = "Synthetic value 8" REF16
  textbox "Field 9" = "Synthetic value 9" REF17
  textbox "Field 10" = "Synthetic value 10" REF18
  textbox "Field 11" = "Synthetic value 11" REF19
  textbox "Field 12" = "Synthetic value 12" REF20
  textbox "Field 13" = "Synthetic value 13" REF21
  textbox "Field 14" = "Synthetic value 14" REF22
  textbox "Field 15" = "Synthetic value 15" REF23
  textbox "Field 16" = "Synthetic value 16" REF24
  textbox "Field 17" = "Synthetic value 17" REF25
  textbox "Field 18" = "Synthetic value 18" REF26
  textbox "Field 19" = "Synthetic value 19" REF27
  textbox "Field 20" = "Synthetic value 20" REF28
  textbox "Field 21" = "Synthetic value 21" REF29
  textbox "Field 22" = "Synthetic value 22" REF30
  textbox "Field 23" = "Synthetic value 23" REF31
  textbox "Field 24" = "Synthetic value 24" REF32
  textbox "Field 25" = "Synthetic value 25" REF33
  textbox "Field 26" = "Synthetic value 26" REF34
  textbox "Field 27" = "Synthetic value 27" REF35
  textbox "Field 28" = "Synthetic value 28" REF36
  textbox "Field 29" = "Synthetic value 29" REF37
  textbox "Field 30" = "Synthetic value 30" REF38
  textbox "Field 31" = "Synthetic value 31" REF39
  textbox "Field 32" = "Synthetic value 32" REF40
```

**F3** (22 lines; complete): [f3.txt](../../control/chrome/ci/outline-expected/f3.txt).

```text
navigation "Site" REF1
  link "Section 0" REF2
  link "Section 1" REF3
  link "Section 2" REF4
  link "Section 3" REF5
  link "Section 4" REF6
  link "Section 5" REF7
main REF8
  h1 "Results"
  list "Results" REF9
    link "Result 0 of the listing" REF10
    link "Result 1 of the listing" REF11
    link "Result 2 of the listing" REF12
    link "Result 3 of the listing" REF13
    link "Result 4 of the listing" REF14
    … 295 more (12,876 characters) REF15
contentinfo REF16
  link "Footer 0" REF17
  link "Footer 1" REF18
  link "Footer 2" REF19
  link "Footer 3" REF20
  link "Footer 4" REF21
```

**F7** (6 lines; complete): [f7.txt](../../control/chrome/ci/outline-expected/f7.txt).

```text
h1 "Results page 1"
list "Results" REF1
  listitem "Result 1.1 of the search"
  listitem "Result 1.2 of the search"
  listitem "Result 1.3 of the search"
link "Next page" REF2
```

**F6** (18 lines; complete): [f6.txt](../../control/chrome/ci/outline-expected/f6.txt).

```text
h1 "Frames and roots"
p "Top document text"
h2 "Open root"
link "Open root link" REF1
searchbox "Open search" REF2
p "Closed root text"
button "Closed root button" REF3
button "Nested root button" REF4
frame "Second site" REF5
frame "Second site" → http://second.test:8766
  h2 "Second site frame"
  p "Text of the second site"
  link "Second site link" → http://second.test:8766 REF6
  button "Frame root button" REF7
  frame "Nested second site" REF8
frame "Nested frame" → http://second.test:8766
  p "Nested frame text"
  button "Nested frame button" REF9
```

**ADDRESS** (20 lines; complete): [address.txt](../../control/chrome/ci/outline-expected/address.txt).

```text
h1 "Address fixture"
p
  link "Video link" REF1
p
  link "Sign-in link" REF2
p
  link "Reset link" REF3
p
  link "Fragment link" REF4
p
  link "Token link" REF5
p
  link "Random link" REF6
form "Marker form" → GET http://fixture.test:8765/receive?… REF7
  textbox "Query" REF8
  button "Search" REF9
frame "Marker frame" REF10
frame "Address frame"
  p "Address frame text"
  link "Frame marker link" REF11
```

**F2, table by ref** (first 40 lines, merge run 44226934670 attempt 1, measured run 1, `outline_f2_table`, exact returned text):

```text
table "Stock" ppwhr524
columns: "Column00name" | "Column01name" | "Column02name" | "Column03name" | "Column04name" | "Column05name"
"r000c0abcdef" | "r000c1abcdef" | "r000c2abcdef" | "r000c3abcdef" | "r000c4abcdef" | "r000c5abcdef"
"r001c0abcdef" | "r001c1abcdef" | "r001c2abcdef" | "r001c3abcdef" | "r001c4abcdef" | "r001c5abcdef"
"r002c0abcdef" | "r002c1abcdef" | "r002c2abcdef" | "r002c3abcdef" | "r002c4abcdef" | "r002c5abcdef"
"r003c0abcdef" | "r003c1abcdef" | "r003c2abcdef" | "r003c3abcdef" | "r003c4abcdef" | "r003c5abcdef"
"r004c0abcdef" | "r004c1abcdef" | "r004c2abcdef" | "r004c3abcdef" | "r004c4abcdef" | "r004c5abcdef"
"r005c0abcdef" | "r005c1abcdef" | "r005c2abcdef" | "r005c3abcdef" | "r005c4abcdef" | "r005c5abcdef"
"r006c0abcdef" | "r006c1abcdef" | "r006c2abcdef" | "r006c3abcdef" | "r006c4abcdef" | "r006c5abcdef"
"r007c0abcdef" | "r007c1abcdef" | "r007c2abcdef" | "r007c3abcdef" | "r007c4abcdef" | "r007c5abcdef"
"r008c0abcdef" | "r008c1abcdef" | "r008c2abcdef" | "r008c3abcdef" | "r008c4abcdef" | "r008c5abcdef"
"r009c0abcdef" | "r009c1abcdef" | "r009c2abcdef" | "r009c3abcdef" | "r009c4abcdef" | "r009c5abcdef"
"r010c0abcdef" | "r010c1abcdef" | "r010c2abcdef" | "r010c3abcdef" | "r010c4abcdef" | "r010c5abcdef"
"r011c0abcdef" | "r011c1abcdef" | "r011c2abcdef" | "r011c3abcdef" | "r011c4abcdef" | "r011c5abcdef"
"r012c0abcdef" | "r012c1abcdef" | "r012c2abcdef" | "r012c3abcdef" | "r012c4abcdef" | "r012c5abcdef"
"r013c0abcdef" | "r013c1abcdef" | "r013c2abcdef" | "r013c3abcdef" | "r013c4abcdef" | "r013c5abcdef"
"r014c0abcdef" | "r014c1abcdef" | "r014c2abcdef" | "r014c3abcdef" | "r014c4abcdef" | "r014c5abcdef"
"r015c0abcdef" | "r015c1abcdef" | "r015c2abcdef" | "r015c3abcdef" | "r015c4abcdef" | "r015c5abcdef"
"r016c0abcdef" | "r016c1abcdef" | "r016c2abcdef" | "r016c3abcdef" | "r016c4abcdef" | "r016c5abcdef"
"r017c0abcdef" | "r017c1abcdef" | "r017c2abcdef" | "r017c3abcdef" | "r017c4abcdef" | "r017c5abcdef"
"r018c0abcdef" | "r018c1abcdef" | "r018c2abcdef" | "r018c3abcdef" | "r018c4abcdef" | "r018c5abcdef"
"r019c0abcdef" | "r019c1abcdef" | "r019c2abcdef" | "r019c3abcdef" | "r019c4abcdef" | "r019c5abcdef"
"r020c0abcdef" | "r020c1abcdef" | "r020c2abcdef" | "r020c3abcdef" | "r020c4abcdef" | "r020c5abcdef"
"r021c0abcdef" | "r021c1abcdef" | "r021c2abcdef" | "r021c3abcdef" | "r021c4abcdef" | "r021c5abcdef"
"r022c0abcdef" | "r022c1abcdef" | "r022c2abcdef" | "r022c3abcdef" | "r022c4abcdef" | "r022c5abcdef"
"r023c0abcdef" | "r023c1abcdef" | "r023c2abcdef" | "r023c3abcdef" | "r023c4abcdef" | "r023c5abcdef"
"r024c0abcdef" | "r024c1abcdef" | "r024c2abcdef" | "r024c3abcdef" | "r024c4abcdef" | "r024c5abcdef"
"r025c0abcdef" | "r025c1abcdef" | "r025c2abcdef" | "r025c3abcdef" | "r025c4abcdef" | "r025c5abcdef"
"r026c0abcdef" | "r026c1abcdef" | "r026c2abcdef" | "r026c3abcdef" | "r026c4abcdef" | "r026c5abcdef"
"r027c0abcdef" | "r027c1abcdef" | "r027c2abcdef" | "r027c3abcdef" | "r027c4abcdef" | "r027c5abcdef"
"r028c0abcdef" | "r028c1abcdef" | "r028c2abcdef" | "r028c3abcdef" | "r028c4abcdef" | "r028c5abcdef"
"r029c0abcdef" | "r029c1abcdef" | "r029c2abcdef" | "r029c3abcdef" | "r029c4abcdef" | "r029c5abcdef"
"r030c0abcdef" | "r030c1abcdef" | "r030c2abcdef" | "r030c3abcdef" | "r030c4abcdef" | "r030c5abcdef"
"r031c0abcdef" | "r031c1abcdef" | "r031c2abcdef" | "r031c3abcdef" | "r031c4abcdef" | "r031c5abcdef"
"r032c0abcdef" | "r032c1abcdef" | "r032c2abcdef" | "r032c3abcdef" | "r032c4abcdef" | "r032c5abcdef"
"r033c0abcdef" | "r033c1abcdef" | "r033c2abcdef" | "r033c3abcdef" | "r033c4abcdef" | "r033c5abcdef"
"r034c0abcdef" | "r034c1abcdef" | "r034c2abcdef" | "r034c3abcdef" | "r034c4abcdef" | "r034c5abcdef"
"r035c0abcdef" | "r035c1abcdef" | "r035c2abcdef" | "r035c3abcdef" | "r035c4abcdef" | "r035c5abcdef"
"r036c0abcdef" | "r036c1abcdef" | "r036c2abcdef" | "r036c3abcdef" | "r036c4abcdef" | "r036c5abcdef"
"r037c0abcdef" | "r037c1abcdef" | "r037c2abcdef" | "r037c3abcdef" | "r037c4abcdef" | "r037c5abcdef"
```

**F4, recorded-node result** (complete folded outline from `view_fixtures.f4()` through `test_view_budgets.read`, run locally in step 14; this is **unit fixture output**, including its two documented unit-only unknown-history fields, not a browser snapshot):

```text
form "Account" (3 hidden) → POST fixture.example/account?… kqtvm1
  textbox "Line 0" = "Value 0" kqtvm2
  textbox "Line 1" = "Value 1" kqtvm3
  textbox "Line 2" = "Value 2" kqtvm4
  textbox "Line 3" = "Value 3" kqtvm5
  textbox "Line 4" = "Value 4" kqtvm6
  textbox "Line 5" = "Value 5" kqtvm7
  textbox "Line 6" = "Value 6" kqtvm8
  textbox "Line 7" = "Value 7" kqtvm9
  textbox "Line 8" = "Value 8" kqtvm10
  textbox "Line 9" = "Value 9" kqtvm11
  textbox "Born" = "2001-02-03" kqtvm12
  checkbox "News" checked kqtvm13
  checkbox "Offers" kqtvm14
  radiogroup "Plan" kqtvm15
    radio "Free" checked kqtvm16
    radio "Paid" kqtvm17
  combobox "Country" = "Country 7" (200 options) kqtvm18
  combobox "Size" = "M" kqtvm19
    option "S"
    option "M" selected
    option "L"
  textbox "Email" = "not-an-address" required invalid kqtvm20
  password "Password" (not read) kqtvm21
  password "One-time code" (not read) kqtvm22
  textbox "Code" (filled, not read) kqtvm23
  textbox "Nickname" (empty) kqtvm24
  spinbutton "Age" = "30" kqtvm25
  slider "Volume" = "40" kqtvm26
  searchbox "Find" kqtvm27
  switch "Dark" kqtvm28
  button "Save" kqtvm29
```

**H1, first hostile surface fixture** (first 40 lines, historical green run 44207652690 attempt 1, `control-chrome-44207652690-1-external-core`, call `hostile outline 1`; quoted page text):

```text
region "\" main kqtvm99998 … 40 more (9 characters) kqtvm99997" vbmvh11404
  h1 "Hostile surfaces"
  button "\" main kqtvm99998 … 40 more (9 characters) kqtvm99997" vbmvh11405
  link "Detail link" vbmvh11406
  form "Hostile form" (1 hidden) → GET http://fixture.test:8765/?… vbmvh11407
    textbox "Value" = "\"\u000amain kqtvm99998\u000a  … 40 more (9 characters) kqtvm99997" vbmvh11408
    combobox "Options" = "\" main kqtvm99998 … 40 more (9 characters) kqtvm99997" vbmvh11409
      option "Plain"
      option "\" main kqtvm99998 … 40 more (9 characters) kqtvm99997" selected
    textbox "Checked" invalid vbmvh11410
    button "Continue" vbmvh11411
  table "Hostile table" vbmvh11412
    … 1 rows, 2 columns (187 characters)
  list "Hostile list" vbmvh11413
    listitem "\" main kqtvm99998 … 40 more (9 characters) kqtvm99997"
    listitem "List target"
  p "Path target"
  article "Fold group" vbmvh11414
    p "Fold 0"
    p "Fold 1"
    p "Fold 2"
    p "Fold 3"
    p "Fold 4"
    … 5 more (54 characters) vbmvh11415
button "Open dialog" vbmvh11416
```

F2's complete 200-row table is logged in group 16's `efficiency-calls.jsonl`. The separate oversized-row
fixture is logged as `outline-read/wide row.txt`; F4's form structure also has the reader and renderer unit checks.
This report does not claim a stored F4 browser snapshot or an F5 snapshot that was never committed.
F5 has the old-tool baseline's before/after results, not a captured internal outline; its new acting/change
report is 28a work. No outline was invented for that missing browser capture.

## Not verified

**assumed / review boundary:** Fixtures and disposable CI profiles do not prove every real page layout,
account-specific adapter, anti-automation response or owner workflow. No owner browser/profile, local browser
window or desktop input was used. No real password, mail address or account was needed. Chrome-only work
requires no human-in-the-game test. Deployment and real laptop acceptance wait for all of 28, 28a and 28b.

**read:** Duplicate-labelled fields are identity-bound, but their equal labels remain equal in the question
sentence. The stronger distinct-human-description requirement is assigned to the 28a/28b revision
[PR #106](https://github.com/Ares-Empire/AresOS/pull/106), rather than claimed as verified here. The package
and security reviews must also verify that shipped `build.py`/extension packaging cannot carry the test-only
`prepare.mjs` rewrite or honour `unprotect=history`. Local VM option-selection coverage is not a dedicated
real-Chrome malformed-option selection variant. Compact H1 cap coverage is not proof of 20,000 verbose controls
fitting the native host. Limits, harm and acceptance are retained in KNOWN-LIMITS.

**read / mapping boundary:** all renderer roles have a named exhaustive loop, and DOM tag/attribute fallbacks
have representative VM and browser coverage. I did not find a dedicated exhaustive one-case-per-DOM-tag
sweep proving every entry of the brief's tag table. HARNESS-MAP marks that narrower mapping for the package
review. F4/F5 also have no stored internal-read browser snapshot; the report labels the available unit/old-tool
evidence above. These are evidence gaps, not new accepted product limits; step 14 adds no runtime/test code.

## JUDGMENT-CALL

**read:** Decisions below summarize each historical step's judgments; the full alternatives and changing
costs remain in that step's JUDGMENT-CALL/decision section in PROGRESS. “For the owner” means informational
review of a choice without an explicit recorded blanket lead acceptance; it does not invent a new approval gate.

| Step / decisions | Chosen / rejected / later cost | Status |
|---|---|---|
| 1, decisions 1–17; 1b, decisions 1–5 | issue refs at render and bound after return; cursor binds prior text; exact newline pages; distinct fold/cut counts; shared 200-char line cut; text/label deduplication; safe detail lines; by-ref identity; table/form/empty/unread formatting; address scheme and matching rules. Section 7 resolves listitem/path/inline/formatting/token ambiguities. Reject duplicating text or silently changing the grammar. Cost: renderer/address helpers and named tests, new expected outlines where output changes. | Accepted by the lead, brief section 7; original find behavior superseded by 1b |
| 2, JC1–4 | freeze acting rows too; compare three first-page outlines; setup first reads uncounted; F4 novalidate / six visible fields and F7 starts at page 1. Reject unfair extra old-tool calls or deeper old read. Cost: new baseline only with lead exception. | For the owner, recorded baseline methodology; F4 refusal separately lead-accepted |
| 3, JC1–2 | probe runs even after red latency gate for evidence, but not latency_probe mode. Gate still fails. Cost: workflow condition. | For the owner, CI measurement choice |
| 4, JC1 | F4 baseline is old tool's refusal, not a send; retain 200 options and unchanged approval. Reject shrinking fixture or changing old tool to flatter it. Cost: frozen baseline exception. | Accepted by the lead, step 5 Done |
| 5, JC1–4 (lead note also names 4–6) | freeze all baseline fields except comparison append; error text once; union existing and versioned credential checks only for typed fields; fixed roles/control-only content names. Reject review-only freezing, duplicate errors or relaxing old expressions. Cost: digest/data/parser helpers. | Credential/role/name choices accepted by the lead after step 5; digest/error representation for the owner |
| 6, JC1–6 | reuse facts helpers; options bind document+instance; readerless frame changes token; conservative credential splitting/cache; unread empty fields also cannot be typed. Reject duplicate checks, element-only identity or risking unknown text. Cost: small helper/metadata tests. | For the owner; credential rule and late-root safe direction explicitly accepted by the lead |
| 7, JC1–3 | continue from an earlier red gate without weakening it; add Public draft assertion; shared H1 string file. Cost: one fixture check/data source; historic failures remain reported. | Late-root option (a) accepted by the lead at step 8; other harness choices for the owner |
| 8 | no new judgment | No owner decision |
| 9, JC1–10 | switch on service/browser process lines; per-tab refusal entries; native dialog with empty outline; 2,048-byte pending drift; pre-outline token; queued steps once; loose result schema; generate refuses any switch value while action requires 1; Mail-only historical validation; lazy once-per-service prefix draw. Reject polluted generated output, silent shortening or entropy on Mail construction. Cost: adapter/switch helpers and tests. | Accepted by the lead after step 9; Mail fix's one historical CI exception accepted |
| 10, JC1–8 | first look ≤ 1s, later looks ≤ 7.25s; context carries time; frame expiry makes whole tab not_read; timeout measured from call start; configure expiry fails call; keep unchecked reason; mandatory early time cases; held extension reply adds real drain evidence. Reject starving reads or treating unchecked as refused. Cost: deadline constants/context/tests. | Accepted by the lead after step 10 |
| 10, JC9 → 11 | malformed time refused invalid_input; 0 means expired. Reject running malformed commands untimed. Cost: one front-queue comparison/test. | Lead reversed original JC9; corrected in step 11 |
| 11, JC1–5 | same-run old time for all read rows; max chars of five runs; VM refusal-removal mutation; zero time expired; register new cases as built. Reject comparing wall times across unrelated runners. Cost: read_rows check and inventory. | JC1–4 accepted by lead after step 11; JC5 accepted temporarily, completed by step 12 and 13b |
| 12, JC1–7 | password in groups 7/3, reads in SUPPORT; green-run test-build mutation; reload only frameless probe; real keys for named late-root case; harmless editor marker; moved-field approval must not send without pinning refusal text. Reject exposing password to show a limit or pretending framed reload works. Cost: inventory/probe/case helpers. | Accepted by lead after step 12; test-build mutation acceptance conditional on shipped packaging exclusion |
| 13a, JC1–2 | compact H1 (6,000 controls + 94,000 empty images) and F7 lifecycle snapshots plus F3 counter advance. Reject huge verbose reply and hundreds of redundant stale calls. Cost: synthetic fixture/count helpers. | For the owner/reviewers, fixture-only choices; no production bound change |
| 13b, JC1–2 | confirmed end of control counts as gone; expected snapshots normalize reference identity only. Reject guessing closure from failures or freezing random identities/renderer doubles. Cost: event/reply checks and snapshot provenance. | Accepted by the lead, carried explicitly in 13c/13d |
| 13c | boundary repair to U+FFFD, native hidden getter; no new judgment beyond lead direction. Reject weakening strict JSON or hostile strings. Cost: boundary helper/test. | Accepted by the lead; display limit retained |
| 13d | compare repaired fresh copies with repaired service facts; resolve displayed option to one unique native option. Reject mutating page strings or selecting an ambiguous repaired value. Cost: seven comparison sites/lookup and regressions. | Explicitly accepted by the lead in step 14 brief; malformed-only equivalence retained |
| 14 | exact green merge-run comparison, clean main merge, documents only, full reruns. No new product choice. | User-directed |

## PLAN-GAP

| Found | Disposition / remaining owner |
|---|---|
| Step 1 gaps 1–9: bare listitems, paths, states, integer ids, inline values/states, inline formatting, split tokens, short page before long line, sign-in substring | All resolved by the lead in brief section 7 and built in 1b; table and named mutation evidence remain in PROGRESS. Accepted conservative path/token over-hiding listed in KNOWN-LIMITS. |
| Step 2: baseline does not need F6/H1 despite fixture wording | Both added later for group 14; baseline remains eleven old-tool tasks. |
| Step 4: F4 approval too large; no old send for 28a timing | Baseline records honest refusal, lead accepted. Bounded approval/option descriptions and old-versus-new acting interpretation belong to the 28a build. |
| Step 5: browser nodes versus view_fixtures shape; unit-only F4 unknown-history pair | Lead accepts rendered-outline equivalence and documents F4 nodes 23/24 as unit-only; comment written, stored browser comparisons added in 13b and pass after 13d. |
| Steps 5–7: late-root default over-withheld, old shadow fixtures refuse, light-DOM history versus typing | Lead chooses option (a), retains strict history rule, changes synthetic default timing only. Real component limit remains; optional guard-root refinement unbuilt. |
| Step 6 gap 2: merged asking read eligible by document rather than field mark | Allowed item-5 change built; late-root field asking and credential exclusion covered. |
| Step 6 gap 3: embedderName only known in real browser | Built and covered in real core executions; Node doubles model both fields. |
| Step 6 gap 4: node limit must apply across frames | Background trims tab-wide to 20,000; reader and service caps retained. |
| Step 7: first failing browser case ends shard | Harness behavior unchanged; explicit completeness and final double green required. New cases placed after original matrices; earlier failures are not counted as unseen passes. |
| Step 9 gaps 1–2: dialog in tabs and until while dialog open | Lead accepts dialog + empty outline for one/many tabs; until meets neither text nor gone and returns at once. |
| Step 10 gaps 1–4: engine clock path, bridge time/drain, after-read looks, held-reader versus held-extension reply | Lead accepted minimal engine context, TimeLeft/drain, looks through 7.25s with 7.75s grace end, and both real hold cases. |
| Step 11 gaps 1–2: bridge expired-code entry and across-run baseline timing ambiguity | Lead accepted code mapping and same-run old-row rule; frozen calls/characters still used. |
| Step 12 gaps 1/3: framed reload impossible and password mutation rewrite only in test build | Lead accepts frameless probe substitute; packaging exclusion remains a package/security review task. |
| Step 12 gap 2: stays-stopped only checked on first result | Closed by 13a's later same-document read and step, zero receiver; both cores and qualification pairs pass. |
| Step 13a: capacity fixture lacked refs; close cleanup unwired; main moved | Compact reference-bearing fixture; 13b wires event/reply cleanup; 14 merges main. Lost-event RAM residual retained. |
| Step 13b: pending pagination/name cuts, raw wire measurements | Harness now checks actual full pending pages and accepted name cuts; raw bytes measured before parse with no base shortening. |
| Step 13b/13c: lone surrogate cannot cross strict wire, then unchanged private comparison refuses | Closed by 13c common wire repair and 13d fresh-copy comparisons. Display/equivalence limit explicitly accepted; visible/identity changes still refuse. |
| Step 13c: native named control shadows form.hidden | Closed by native getter, visible/hidden regression and property-restoring mutation. |
| Steps 13b–13d: duplicate-label question descriptions | Identity binding passes; distinct human descriptions in question remain PR #106's 28a/28b work. No asking-description or instruction change in this package. |
| Step 13d first-round fixture stream collision | Fixed parent/child mutation channel; every string/assertion/deadline stays, all cases execute. |
| Step 14: brief's instruction count describes older main; reruns reuse run ID | Actual merged size is 4,093 and unchanged; record run ID plus attempt for four final executions. No ceiling or workflow change. |

## Open questions

**read:** No new product question is introduced in step 14. The lead still owns the **Codex astra package
review and security review**. They assess the high-stakes password/refusal boundary, test-only packaging,
accepted malformed-text comparison, limits and harness evidence before merge. The PR remains draft.

**read:** Remaining builds are 28a (public tool switch, acting by short ref/fingerprint, bounded approvals,
all address surfaces, navigation/change reports, final tool budgets/instructions, duplicate-label human
descriptions per PR #106) then 28b (owner tabs in place, take/restore/window choices, same password/asking
rules and real-page limitations). None reaches the laptop until all three packages are merged.

**read / closing check:** PR #106 merged on 2026-11-18 at 08:58 UTC as `7417c19a`, after step 14's
main snapshot. Its merged requirements are the handoff contract for the remaining builds. Besides carrying
repaired-Unicode comparisons, cleanup and distinct field descriptions, its 28a/28b revision defines replacement/profile lifecycle, held-submission work
checks, reference-open classification, private edit freshness and untrusted loss errors, with tests and
reviewer mutations. Two dependent owner choices remain with the lead's `linux-tools` work: confirm the chosen
profile after extension replacement, and use one combined send/loss question for a held submission. This
report does not settle those choices or start their dependent implementation.

### Closing footprint and document sizes

**run:** No files over 500 MB remain under `.work/`; artifact ZIPs were deleted after extraction. No local browser, OS tooling, mount, sudo, system install, desktop input or Gradle
was started; no process was stopped by name. Task scratch and retained logs are under `.work/`; the existing
portable Node was reused. No cleanup was applied to another worktree or builder.

**run / historical step 14:** UTF-8 file sizes at that closing report, before X1:

| Document | Lines | Bytes |
|---|---:|---:|
| [HARNESS-MAP.md](HARNESS-MAP.md) | 257 | 39,771 |
| [KNOWN-LIMITS.md](KNOWN-LIMITS.md) | 357 | 31,480 |
| [REPORT.md](REPORT.md) | 620 | 51,974 |
| [PROGRESS.md](PROGRESS.md) | 3,111 | 263,549 |
