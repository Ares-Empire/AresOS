# Package 43 progress

Latest: step 4's guides, card and equality checks are built from `1a4d783f`;
see "Step 4" below. Nothing committed; the lead commits and refreshes the
waiting bindings. Calls 1 and 2's wording still needs the owner's OK before
step 6. The two intentional integration failures remain (Control's `newest`
reservation and the moved wrapper's release-diff rule). Step 3 is reviewed
SAFE and its check build passed, as recorded below. Earlier steps are historical.

Step 1 is implemented in the worktree on `pkg/43-aresos-command`, based on
`7dd5588c`. The final test results and the one commit-dependent failure are below. Nothing is committed or pushed;
the lead commits, as requested. No owner-tool entry, root operation, dispatch,
deployment command, window or Gradle build ran on the laptop.

## Done

- Before the first change, the required
  `grep -c 'VM REHEARSAL PASSED; NOT ON THE LAPTOP' docs/INSTALL-STATUS.md`
  printed `0` (exit 1 means no matches). The status-row gate passed.
- **D18:** `at` resolves its path and changes to `/`; all four child starts in
  `owner.py` use `cwd='/'`; all seven embedded Python starts in the six payload
  release scripts and the generated `pin_step` start use `python3 -I -`.
  `test_owner_cwd.py` separates the three protections, includes the live planted
  module control, checks both Host methods, and scans the syntax trees of both
  `owner.py` and `media.py` (REVIEW-3 N5).
- **D19:** `check` still requires labwc, then asks only for the running image's
  own session program: `aresos-desktop` when its image file exists, otherwise
  `foot`. An absent keeper gets the design's exact session-specific STOP.
  `test_owner_session_program.py` covers both images, present/absent programs,
  the autostart name and the process-name length limit.
- **`newest`:** D2 rows 0–10, including row 5's own refusal; D3's guard after
  both staging preflights; D4's callbacks after read-only preflights. It uses
  one chosen inner word and its unchanged journal. The initial survey's notes
  print once before its own lines and move from `notes` to `said`; PASS and STOP
  records carry `chosen` and `said`. The new numbered text follows section 5,
  including all three forward wordings, both later-install endings, row 3's
  removal/settings facts, and `latest installed version` when N differs from T.
  `test_owner_newest.py` covers the rows, timing, allowed failures after an
  announcement, failed-update ordering, journal behavior, and both record paths.
- **Release numbers:** current release records 06, 13 and 27 have their own
  numbers; history entries are numbered 13 and 27; the target remains R27.
  Incoming histories require positive integer numbers and target agreement;
  duplicate numbers, absent/invalid numbers and conflicts refuse before any
  installation change. Installed old histories may omit numbers: the existing
  exact-reference, identity, daily-account and append-only comparison still
  applies, and existing numbers cannot change or disappear. Retired bytes are
  preserved. `test_owner_release_numbers.py` includes an unnumbered three-release
  history and both naming fallbacks; the unknown-name fallback does not widen
  the deployment survey.
- **Tools version 6**, above R28's planned version 5. Ran
  `python3 os/owner-tools/bundle.py --refresh`; the current fingerprint is
  `2f939db96d99de448c07fa68bec11475ffeccb1a21376fc30b2a2895dd528245`.
  The payload was generated, never edited by hand. All generated commands and
  pins in OWNER-TOOLS.md, INSTALL.md and EMERGENCY.md moved together. The 22d
  status row keeps the historical fingerprint as eight characters `dcbc375f`;
  it still describes the actual v4 laptop install. Its test follows that pin.
- `commands.json` has `newest`; INSTALL.md has its single full-command sentence;
  `pending-rebind.json` lists it under `unwalked_commands`. The existing CLI
  dispatch fixture includes its stand-in. Version/history fixtures and their
  compatibility assertions follow the new metadata without changing historical
  bundles. The command test's `Path.glob` shim now forwards Python 3.14's
  `case_sensitive`/`recurse_symlinks` keywords; no assertion was removed.
- **REVIEW-3 N6:** D4's closing sentence now says a refusal by a check that could
  have run before the announcement. DESIGN.md's change log also records the
  lead's PLAN-GAP 1 decision.
- Ran `PYTHONDONTWRITEBYTECODE=1 python3 reviews/27-first-update-release/rebind.py pending '43 step 1: isolated root steps, session check, newest and numbered release metadata; tools v6 payload and pins'` after the last bound-file changes.
  It printed `pending: 37 bound files differ from the active bindings, 0 removed`.

## Left (in order)

1. **Next merge of main:** package 42 step 5 adds the real published
   `os/manifest/releases/28.json`, its history entry and the R28 target. At 43's
   next merge add `number` 28 to that entry and record, then refresh the payload
   and every pin again, per binding rule 1. Never merge the payload by hand and
   never invent a stand-in R28 record. Recheck the status-row gate before any
   tools/guide change if R28's rehearsal has closed the window.
2. **Step 2:** implemented and locally verified below. The lead still needs
   the hosted full-model/checks run on the committed head; this builder did
   not dispatch it.
3. **Step 3:** image implementation and tests are built below, including
   **REVIEW-3 N1**'s plain-Bazzite `keep-stock` refusal and full console command.
   Resolve the two integration PLAN-GAPs, then the lead runs the check build.
4. **Step 4:** guides, card and equality checks built; **REVIEW-3 N4 and N7**
   addressed in the Step 4 section below. The owner still needs to approve
   calls 1 and 2's proposed lists, the other tools lines and D19's keeper line
   before step 6. No tools text changed in this step; the payload and pins
   remain unchanged. The lead must refresh the waiting list for the four
   changed bound files before the binding check can pass.
5. **Step 5:** independent review of steps 1–4 (the step 1 Astra review follows
   this handoff).
6. **Step 5a:** the three generated bridge lines (`newest`, `reboot`, `check`),
   tests, guides, pins and independent review. Same status-row gate.
7. **Step 6:** harness/workflow/budget/local walk/host-walk receipt, hosted checks
   and full model on the same head, VM rehearsal including bridge windows,
   then rebind and record the result. Requires published R28 and settled words.
8. **Step 7:** pass the dispatcher rehearsal stages and diff note to R29's brief.

## Verified

All module commands use
`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p '<module>.py'`,
one module at a time. Final results:

| Module | Printed result |
|---|---|
| `test_owner_commands.py` | `Ran 6 tests`, `OK` |
| `test_owner_bootstrap.py` | `Ran 13 tests`, `OK` |
| `test_owner_equality.py` | `Ran 11 tests`, `FAILED (failures=1)`; 10 pass, HEAD/checkout comparison needs the lead's commit |
| `test_owner_path.py` | `Ran 48 tests`, `OK` |
| `test_owner_sources.py` | `Ran 13 tests`, `OK` |
| `test_checkout_sources.py` | `Ran 8 tests`, `OK` |
| `test_ways_back_probe.py` | `Ran 57 tests`, `OK` |
| `test_owner_cwd.py` (new) | `Ran 6 tests`, `OK` |
| `test_owner_session_program.py` (new) | `Ran 2 tests`, `OK` |
| `test_owner_newest.py` (new) | `Ran 19 tests`, `OK` |
| `test_owner_release_numbers.py` (new) | `Ran 7 tests`, `OK` |
| `test_owner_tools.py` | `Ran 13 tests`, `OK` |
| `test_owner_entry.py` | `Ran 3 tests`, `OK` |
| `test_ways_back_compatibility.py` | `Ran 21 tests`, `OK` |

The source module also printed the successful v2/v3 recovery checks at 21 cuts
for each versioned installation and 22 for each unversioned installation, for
both stick and folder routes. The historical compatibility module printed that
all 13 historical shapes were accepted with no deployment mutation.

Safe single tests from `test_owner_update` ran separately, each with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=os/tests python3 -m unittest test_owner_update.<name>`;
each printed `Ran 1 test` and `OK`:

- `HistoryTest.test_reviewed_history_ends_with_the_pinned_release_and_r13_is_not_wheel`
- `HistoryTest.test_every_release_declares_exactly_one_account_rule_and_history_stays_strict`
- `HistoryTest.test_installed_history_must_be_a_prefix_and_legacy_tools_are_only_the_15f_bundle`
- `AccountRuleTest.test_each_release_requires_exactly_its_own_wheel_rule`
- `ToolsUpdateTest.test_newer_bundle_over_history_tools_extends_the_installed_history`
- `UpdateCommandTest.test_update_verifies_then_stages_keeping_running_release_and_pinned_stock`
- `UpdateCommandTest.test_forward_selects_the_destination_without_network_where_update_only_names_it`

Earlier runs, superseded by the final results above: `test_owner_commands` had
5 Python 3.14 shim errors; `test_owner_bootstrap` had 2 failures while the payload
needed its second refresh; `test_owner_entry` had 1 missing-PASS failure, and its
missing `newest` stand-in caused 14 `test_owner_path` errors and 1 equality error.
`test_owner_newest` initially had 2 failures/1 error in the new fixtures, then a
wrong expected busy-refusal text in an added case; the final 19 tests pass.
`test_owner_sources` first had 180 obsolete v4 expectation failures, then 8
old-incoming-bundle refusal-text failures; its final 13 tests pass with strict
number validation. `test_ways_back_compatibility` had 53 failures/13 errors from
its new-tools fixture still using the unnumbered old history; that fixture is
now numbered while the exact old bundle stays unchanged, and all 21 tests pass.
No test was skipped, deleted, or weakened. The old-bundle refusal assertion now
requires the exact earlier missing-number refusal; downgrade behavior for
numbered incoming bundles is still covered.

`git diff --check` passed. The refresh's last output was
`PASS bundle manifest SHA256 2f939db96d99de448c07fa68bec11475ffeccb1a21376fc30b2a2895dd528245`.
Final read-only checks printed `PASS payload equals sources`, `PASS OWNER-TOOLS.md lines 1 and 3`,
and `PASS newest command and unwalked entry`; the fingerprint was unchanged.
The final status-row grep again printed `0`; `.work files: 0` and `.work over 500 MB: []`.
Git HEAD remains `7dd5588c`, with only the intended worktree changes and no temporary test files.


## What the code does not show / not verified

- **Commit-dependent check:** the tools-local walk in `test_owner_equality`
  intentionally compares commands from the checkout with the payload of Git
  HEAD. This worktree's HEAD still holds v4; the working tree holds v6. Its
  `STOP: commands.json is not this head's` needs the lead's commit and rerun,
  then the hosted check. Its assertion is unchanged.
- The full OS suite and the whole `test_owner_update` module run hosted only;
  no `test_inherited_homebrew`, `test_sysusers`, or whole-suite discovery ran.
  Only safe individual tests from `test_owner_update` are permitted locally.
- The v6 bundle is not rehearsed, installed or announced for laptop use.
  VM proof belongs to step 6, image checks to step 3, and the dispatcher/bridge
  routes to their later steps. Nothing here proves a real hub session, a real
  password window, a signature/network operation or an update on the laptop.
- The proposed tools lines still need the owner's final wording before step 6.
  The generated bridge and image dispatcher have not been built in this step.
- The source-binding checks left empty scratch directories under `.work/14/source-checkouts`; `.work/` contains 0 files and no files over 500 MB.

## PLAN-GAPs and JUDGMENT-CALLs

**PLAN-GAP 1 — resolved by the lead (2026-11-17).** The first builder stopped
because section 5 named R28's published record but main had only R13 and R27.
The lead directed step 1 to build now against those existing records and keep
R27 as target. Package 42 publishes R28 later; 43 numbers it at the next merge
and refreshes/pins again. The compatibility test covers an older unnumbered
history ending in a third release, as the future v5 laptop bundle will. No R28
record was invented. The merge task is first under Left and the decision is in
DESIGN.md's change log.

No new design gap or JUDGMENT-CALL. The commit-dependent test is an environment
limit of the requested uncommitted handoff, not a change to the agreed design.

## REVIEW-5 fixes (2026-11-17)

Both findings are fixed on `pkg/43-aresos-command`, starting from `1d3dd2a8`.
Nothing was committed or pushed; the lead commits this handoff.

- **Announcement order:** `os/release/update.sh:48` has a read-only `--check`
  mode after its finalizer and system/user updater policy checks, before any
  unmask or reload. `os/owner-tools/owner.py:1942` runs that mode before
  `newest` announces an install or retry. The ordinary staging invocation
  retains every check against changes during signature verification; the
  direct `update` word keeps its existing behavior.
- **Closing instruction:** `owner.py:1756` derives the later-install sentence
  from the chosen operation's own validated state. `forward` passes that state
  to the closing callback (`owner.py:2093`), including when its destination
  already starts next. The outer survey's installed/running facts no longer
  decide the sentence after a forward.
- **Regressions:** `os/tests/test_owner_newest.py:29` runs the actual shell
  preflight with fixture unit files, the real policy lists, and command stubs,
  rather than the staging-command extraction in the older model. At `:337`,
  four real-shell refusal cases (system updater, user updater, finalizer file,
  finalizer link), each for a fresh install and an interrupted retry, prove
  no announcement, verification, new intent or deployment change occurs.
  At `:294`, four survey-change cases include REVIEW-5's exact R21-running,
  stock-next, tools-R30 case where unbooted R13 becomes R30; its inverse and
  both already-first paths also check the closing instruction.
- Ran `python3 os/owner-tools/bundle.py --refresh`. It printed
  `PASS bundle manifest SHA256 f66fd69442857b911b81775bbc2efb3edf53648b391615b38234b2ddcea9d135`.
  Tools remain version 6. The payload is generated from its sources; every
  active pin in `docs/OWNER-TOOLS.md`, `docs/INSTALL.md`, `docs/EMERGENCY.md`
  and the regenerated `os/owner-tools/commands.json` moved together. The
  historical 22d status-row pin stays unchanged.
- Ran `PYTHONDONTWRITEBYTECODE=1 python3 reviews/27-first-update-release/rebind.py pending "43 step 1: REVIEW-5 fixes"`.
  It printed `pending: 37 bound files differ from the active bindings, 0 removed`.
  Before editing, the status-row gate printed `0` (no matching row).

All requested modules ran one at a time with
`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p '<module>.py'`:

| Module | Printed result |
|---|---|
| `test_owner_newest.py` | `Ran 21 tests`, `OK` |
| `test_owner_commands.py` | `Ran 6 tests`, `OK` |
| `test_owner_bootstrap.py` | `Ran 13 tests`, `OK` |
| `test_owner_path.py` | `Ran 48 tests`, `OK` |
| `test_owner_sources.py` | `Ran 13 tests`, `OK` |
| `test_checkout_sources.py` | `Ran 8 tests`, `OK` |
| `test_ways_back_probe.py` | `Ran 57 tests`, `OK` |
| `test_owner_release_numbers.py` | `Ran 7 tests`, `OK` |
| `test_owner_cwd.py` | `Ran 6 tests`, `OK` |
| `test_owner_tools.py` | `Ran 13 tests`, `OK` |
| `test_ways_back_compatibility.py` | `Ran 21 tests`, `OK` |

The source checks also printed the successful v2/v3 recovery results at 21
cuts for each versioned installation and 22 for each unversioned installation,
on both source routes. Compatibility printed
`B8: 13/13 historical shapes accepted; before-first-switch title text equal`
and reported no deployment mutation.

Two safe individual tests for the affected direct words ran separately with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=os/tests python3 -m unittest test_owner_update.<name>`;
each printed `Ran 1 test` and `OK`:

- `UpdateCommandTest.test_update_verifies_then_stages_keeping_running_release_and_pinned_stock`
- `UpdateCommandTest.test_forward_selects_the_destination_without_network_where_update_only_names_it`

`test_owner_equality` was not run: its checkout/HEAD comparison can pass only
after the lead commits the refreshed payload and commands. Its assertions are
unchanged. No prohibited module, whole suite, hosted dispatch, real installed
tools entry or real deployment command ran. All machine changes were fixtures;
there was no sudo, window or change to the laptop's system state.

Final checks: `git diff --check` passed; the payload/source check printed
`PASS payload equals sources; fingerprint f66fd69442857b911b81775bbc2efb3edf53648b391615b38234b2ddcea9d135`.
`.work files: 0`; `.work over 500 MB: []`. No new PLAN-GAP or JUDGMENT-CALL.
The next-merge R28 task and the later steps above remain with the lead.

## Step 2: model (2026-11-17)

Built from clean HEAD `5611afd2b68aa10589cfbd9fbbb9c92298f2bc45`, after
REVIEW-5 and REVIEW-6. No commit, push, dispatch, installed tools entry, privileged
operation or deployment command ran. The owner tools, release scripts, payload,
fingerprint pins and workflow are unchanged. No owner-tool defect has been found.

- `os/tests/ways_back_ledger.py`: independent `choose(s)` for D2 rows 0–10,
  chosen-word metadata and `newest` transitions. It resolves the survey before
  acting, preserves the failed-update hold for this run alone, allows only
  recording an already staged update from an older running release, refuses
  its unstaged retry, and distinguishes a pending return from applied
  `keep-stock`. `newest` is last in both existing command loops. Seeds,
  state reduction, memoization and the slice budget are unchanged.
- `os/tests/test_ways_back_model.py`: calls the real `Tools.newest`, supplies
  the synthetic release's matching number, compares the independently chosen
  word, and judges I1–I4 before comparing the actual state with the ledger.
  I1 checks newly staged deployments and actual staging calls. I2 checks
  STOPs and output, exempting only observed title lines with multiplicity.
  I3 uses output snapshots before intent, staging and reorder; it also checks
  a completed staging's record. I4 checks change/cut versus refusal, `Nothing`
  after an announcement, and false forward announcements. After REVIEW-7 it
  also independently matches the printed operation and release number to the
  observed staging, reorder or record completion (or durable intent at a cut),
  without using the chosen word. The stock-only prepared fixture now has coherent rpm/bootc
  observations, so D2 row 1 reaches its own refusal.
- `os/tests/ways_back_host.py`: output observation immediately before
  set-default, staging and sync; support for the read-only update preflight.
  Shell policy remains a fixed passing environment input here; step 1's
  real-shell tests cover its refusals. No new primitive or VM replay is added;
  22c's rehearsal `WORDS` and capture replay remain unchanged.
- `os/tests/test_ways_back_newest.py`: table rows, all chosen cut phases,
  the three forward wordings, completed staging on an older release,
  failed-update and failed-reorder resolution, `check` consuming the notice,
  pending returns, `keep-stock`, a survey-record cut before choice,
  breadth-first prefix equality and cached/uncached execution with each /etc.
  In-memory tools mutations must fail named I1, I2, I3 and I4 assertions;
  an unrelated exception does not count as a revert proof. I3 tests the
  primitive separately from the intent, and I4 also rejects a forward
  announcement mislabeled as the chosen `update`.
- `os/tests/test_ways_back_reverts.py`: repaired the old update-to-reorder
  mutation's source anchor after step 1 inserted its guard. The mutation and
  both guarding assertions are retained.

### Measurements and verification

Every command selects one module, with bytecode disabled:
`PYTHONDONTWRITEBYTECODE=1 [ARESOS_MODEL_SCOPE=<scope>] python3 -m unittest discover -s os/tests -p '<module>.py'`.
The scope variable is set only for `test_ways_back_model.py`. Logs are small,
ignored local files in `.work/43-model/`.

**Execution mistake:** short focused, revert, compatibility and path module runs
overlapped the full baseline. This violated the requested one-module-at-a-time
rule. The baseline exploration finished, but its time includes that overlap;
it is not an isolated performance comparison. All runs after that baseline
have been sequential. No two heavy explorations ran together.

| Model run | Processed | Discovered | Steps/edges | Exploration time | Module result |
|---|---:|---:|---:|---:|---|
| Before, slice | 120,000 | 173,130 | 3,185,862 | 153.243 s | 26 tests, OK, 171.690 s |
| Before, full | 967,215 | 967,215 | 26,519,328 | 978.648 s | 26 tests, OK, 1000.995 s; queue exhausted |
| After, first slice measurement | 120,000 | 173,130 | 3,433,044 | 173.664 s | 26 tests, one failure in the old edge-count pin, 197.390 s |
| After, first full measurement | 967,215 | 967,215 | 28,687,626 | 1070.733 s | 26 tests, one failure in the old edge-count pin, 1095.831 s; queue exhausted |
| After, final full verification | 967,215 | 967,215 | 28,687,626 | 1022.399 s | 26 tests, OK, 1044.752 s; queue exhausted |
| After, final slice verification | 120,000 | 173,130 | 3,433,044 | 163.085 s | 26 tests, OK, 184.251 s |
| REVIEW-7 fix, slice | 120,000 | 173,130 | 3,433,044 | 177.959 s | 26 tests, OK, 202.580 s |
| REVIEW-7 fix, full | 967,215 | 967,215 | 28,687,626 | 1050.983 s | 26 tests, OK, 1073.593 s; queue exhausted |

The first updated slice completed every invariant and actual execution;
only its final old edge-count pin failed. The pin now includes exactly the
247,182 added `newest` edges: 81,046 PASS, 38,954 STOP and 127,182 cuts.
The full exploration adds exactly 2,168,298 edges: 756,453 PASS, 210,762 STOP
and 1,201,083 cuts. It exhausted the same 967,215 states, and every earlier
command's edge counts and all outcome counts match the baseline. Its only
failure was also the final old edge-count pin. Both numeric pins are now
updated, and both final scope runs pass. The final full model took 17.040
minutes locally, within the unchanged 35-minute hosted limit. A hosted time
is still needed; the baseline overlap prevents an isolated speed comparison.

After the last model/test source change, ran
`PYTHONDONTWRITEBYTECODE=1 python3 reviews/27-first-update-release/rebind.py pending "43 step 2: independent newest choice, model driver and I1-I4 revert proofs"`.
It printed `pending: 37 bound files differ from the active bindings, 0 removed`.
The changed model/test sources are not in the active bindings; the 37 existing
waiting rows remain, and the step 2 note is added. No payload refresh is needed.

Earlier successful module runs (overlapped the full baseline):

| Module | Printed result |
|---|---|
| `test_ways_back_newest.py` | 17 tests, OK, 1.770 s |
| `test_ways_back_reverts.py` | 20 tests, OK, 6.160 s |
| `test_ways_back_compatibility.py` | 21 tests, OK, 28.660 s |
| `test_owner_path.py` | 48 tests, OK, 1.957 s |

Final module verification, all sequential and on the final code:

| Module | Printed result |
|---|---|
| `test_ways_back_model.py`, full | 26 tests, OK, 1044.752 s |
| `test_ways_back_model.py`, slice | 26 tests, OK, 184.251 s |
| `test_ways_back_newest.py` | 17 tests, OK, 1.832 s |
| `test_ways_back_reverts.py` | 20 tests, OK, 6.715 s |
| `test_ways_back_compatibility.py` | 21 tests, OK, 29.948 s |
| `test_owner_path.py` | 48 tests, OK, 1.741 s |
| `test_checkout_sources.py` | 8 tests, OK, 1.099 s |

Compatibility again printed `B8: 13/13 historical shapes accepted;
before-first-switch title text equal`, with no deployment mutation, and the
successful v2 settle checks at 21/22 pre-publication cuts. All final commands
exited 0. No test was skipped.

Earlier focused runs had two failures, then one failure, among 16 tests:
the invalid-journal fixture initially described a valid order; the stock-only
prepared fixture had inconsistent bootc slots; and a driver's diagnostic
evaluated an invalid journal's outcome before checking which command it was.
All three were test/model fixture issues and are fixed. The first old-revert
run had one failure among 20 tests because its source anchor no longer matched
step 1; its final 20 tests pass. No assertion was weakened, removed or skipped.

Final read-only checks: `git diff --check` passed;
`git diff --exit-code -- os/owner-tools os/release .github/workflows` exited 0.
The worktree has only the intended five model/test files, this progress log
and the pending-rebind note. `.work files: 15`; `.work over 500 MB: []`.
No Gradle daemon was started. No new PLAN-GAP or JUDGMENT-CALL.

### REVIEW-7 I4 fix (2026-11-17)

- `os/tests/test_ways_back_model.py:421`: I4 derives staging, reorder or
  record completion and its exact target from the observed deployment list
  and journal writes. An intent cut uses the saved intent before its primitive
  can run. It parses each announcement independently and matches both the
  operation and the target's fixture release number, including the separate
  download line. Neither the tools' chosen word nor the ledger result supplies
  these expectations. Existing I1–I3 and I4's refusal, no-change, pending and
  `Nothing` checks remain.
- `os/tests/test_ways_back_newest.py:263`: added REVIEW-7's exact in-memory
  `announce_forward = announce_update` mutation in the older-running danger
  state beside the reverse-direction proof. It must fail the named
  `I4: announced operation/target differs from observed change` assertion.
  Further mutations prove wrong release numbers fail for staging, retry,
  reorder and completion across all cut phases; staging and recording the
  same release cannot substitute for each other; and a wrong download target
  fails even with a correct first line.

All requested modules ran sequentially, with
`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p '<module>.py'`.
Only the model module additionally set `ARESOS_MODEL_SCOPE`, first `slice`,
then `full`. The measurements above are these runs' printed results; states,
steps, outcome counts and command-edge counts are unchanged. Logs are
`.work/43-model/review7-*.log`.

| Module | Printed result |
|---|---|
| `test_ways_back_newest.py` | 21 tests, OK, 2.588 s |
| `test_ways_back_reverts.py` | 20 tests, OK, 21.905 s |
| `test_ways_back_model.py`, slice | 26 tests, OK, 202.580 s |
| `test_ways_back_model.py`, full | 26 tests, OK, 1073.593 s |
| `test_checkout_sources.py` | 8 tests, OK, 1.244 s |

All commands exited 0; no tests were skipped. Only the two model/test files
and this log changed. None is in the active source bindings, so no rebind was
needed. No owner tools changed, no worktree commit or dispatch ran, and no
privileged or real deployment operation ran. The hosted verification remains with the
lead. No new PLAN-GAP or JUDGMENT-CALL.

Final read-only checks: `git diff --check` passed;
`git diff --exit-code -- os/owner-tools/ os/release/ .github/workflows/`
exited 0. Compared both scopes' printed outcome and command-edge counts with
their prior final logs: all match. `.work files: 20`; `.work over 500 MB: []`.

### Still with the lead

Commit these changes, then run the hosted full-model job and checks on that
same committed head. No hosted result is claimed here, and this builder was
explicitly forbidden to dispatch. The workflow's 35-minute full-model limit
is unchanged. If the hosted model outgrows it, follow lead decision/open point
9: split the job, never the exploration; this step does not change the workflow.
The later package steps, VM run and next-merge R28 metadata task above remain.

## Step 3 (2026-11-18)

Built against `07cce64b`, after the lead's merge of main and PR #58
(18c Part A, squash `beb42ec8`). Nothing committed or pushed: the lead commits.
No file under `os/owner-tools/`, `os/release/`, `docs/` or `control/` changed.
No sudo, workflow dispatch, deployment command, rebind, window or Gradle build ran.

### Done

- `os/config/usr/bin/aresos`: executable Python dispatcher with the specified
  `-ISB` shebang, one table for all 18 tools words, pure `plan()` and exec in
  `main()`. The nine offered words use D7's exact sudo/bash form; `update` maps
  only to `newest`. D11's environment is built from fixed values, the caller's
  account entry and the five screen variables. Root/no-session instructions
  name the safe full console command. Refusals print one stderr line, status 2,
  with `nothing ran`; extra arguments never reach sudo. **REVIEW-3 N1**:
  `keep-stock` says it works only on plain Bazzite, at the recovery console,
  typed by the owner, and gives `sudo /var/lib/ares/at keep-stock`.
- `os/config/usr/libexec/aresos-askpass`: executable, exactly D9's two lines,
  with `timeout --foreground -k 10 600` and quoted `"$@"`.
- `os/build.sh`: only the install-map entry moves, from `/usr/bin/aresos` to
  `/usr/libexec/aresos-control/cli`. The wrapper bytes come unchanged from
  `control/packaging/aresos`; the generated `control.json` records the new path,
  source, mode and hash. The old path is no longer in Control's file record.
  Control's source wrapper, including its existing header comment, is untouched.
- `os/tests/test_control_image.py`: moved the map pin; added a real
  `control-tree` install over an existing dispatcher. It proves the dispatcher
  survives unchanged and the wrapper's bytes, mode, hash and source are recorded.
  All #58 assertions remain, including exact complete file/folder/link sets.
- `os/tests/test_aresos_command.py`: exact argv/environment and refusal cases,
  labels against the imported 16 ksshaskpass patterns, all three word sets,
  no generated `at update`/`at forward` instruction, root/no-session behavior,
  argument rejection, Control handover and missing-Control usage. A child runs
  real `main()` and execs a harmless stand-in, proving stdin stays a terminal,
  arguments and a caller environment value survive, and the directory stays.
  Askpass tests pin its two lines and expand its actual exec line's arguments
  through a harmless Bash function; no timeout, sudo or GUI helper starts.
- `os/tests/test_aresos_command_diff.py`: a real `control-tree` plus the two
  executable config sources is fed to `release_diff.Classifier.classify()`.
  Root ownership is represented in the temporary inventory; config discovery
  represents the new files after the lead's commit. Both config files classify
  as `config`; altered bytes, ownership, mode or type remain unexplained.
  The moved `cli` is required to classify too, and currently fails (below).
- `os/ci/image-checks.sh`: checks both new files as regular, executable,
  root:root 0755 and no links, the exact helper and dispatcher shebang,
  executable timeout/ksshaskpass and ksshaskpass RPM version **6.7.5**. As `ares`,
  a refused desktop word and an offered word without a desktop must return the
  exact safe instructions and status 2. Existing Control help handover checks
  remain unchanged.
- `.gitignore`: a narrow exception exposes this new dispatcher to Git; the
  existing `bin/` output rule otherwise hid it. Both new image files are 0755
  in the worktree; the lead must preserve the executable bits when committing.

### Verified

Each final module command was exactly
`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p '<module>.py'`,
one module at a time. No tests were skipped, deleted or weakened.

| Module | Printed result |
|---|---|
| `test_aresos_command.py` | `Ran 14 tests`, `FAILED (failures=1)`; only the three-set equality fails, missing Control's `newest` |
| `test_aresos_command_diff.py` | `Ran 2 tests`, `FAILED (failures=1)`; only `/usr/libexec/aresos-control/cli` is unexplained |
| `test_control_image.py` | `Ran 16 tests`, `OK` |
| `test_control_vm.py` | `Ran 62 tests`, `FAILED (errors=1)`; socket creation in `test_check_2_sees_a_listening_socket_and_an_unconnected_udp_one` raises `PermissionError: [Errno 1] Operation not permitted` |
| `test_aresos_desktop.py` | `Ran 189 tests in 68.979s`, `FAILED (errors=42)`; LoopTest/WrapperTest socket binds are denied with the same `PermissionError`; ResourceWarnings also printed |
| `test_owner_path.py` | `Ran 48 tests`, `OK` |
| `test_checkout_sources.py` | `Ran 8 tests`, `OK` |
| `test_release27.py` | `Ran 41 tests`, `OK` |
| `test_owner_capabilities.py` | `Ran 6 tests`, `OK` |

Earlier probe: the first command-module run also failed because `/bin/sh`
refuses defining a function called `exec` in POSIX mode. The harmless test
probe now uses Bash; the pinned production helper is unchanged. One initial
diff-module run misspelled the bytecode environment variable; the exact command
above reran it with the same one failure, and its generated bytecode was removed.

`bash -n os/build.sh os/ci/image-checks.sh`,
`sh -n os/config/usr/libexec/aresos-askpass` and `git diff --check` all exited 0
without output. The protected-tree diff printed nothing. `.work files: 20`;
`.work over 500 MB: []`. No download or screenshot was made.

### PLAN-GAPs and left (in order)

1. **D12's Control changes are absent from the merged #58 tree.**
   `control/tests/test_reserved_words.py` has 17 reserved words, missing
   `newest`; the tools and dispatcher each have the same 18. The strict new
   equality test stays red until the Control-side change lands. The same
   coordination still needs the integration caller (currently
   `control/tests/test_integration.py:388`) moved to `cli`: `control-tree`
   intentionally installs no dispatcher. Control's top-level `log` alias and
   original wrapper header also remain. The help-line choice is the lead's.
   Those are D12's `linux-tools` work, not changes allowed in this run; no
   Control test or source was changed to conceal this dependency.
2. **D16's existing-diff-rule premise does not hold on this base.**
   `release_diff.py` has no Control rule and never reads `control.json`.
   Its config rule correctly explains `/usr/bin/aresos` and the askpass helper,
   but cannot explain `/usr/libexec/aresos-control/cli`. A manifest entry alone
   cannot change that. The new diff test deliberately requires all three and
   fails for `cli`. The lead must resolve the rule/design gap before R29;
   no broad rule or duplicate wrapper source was added here. R29 must have
   **zero unexplained files**, including the wrapper and Control's changed
   manifest. This run does not establish a complete release-image diff.
3. Lead: after resolving those integration gaps, commit (including executable
   bits), run any required rebind, rerun the two strict new modules, and run the
   check build below. The sandbox socket errors need an environment where those
   modules can bind sockets; their assertions are unchanged.
4. Continue the earlier ordered list: step 4's guide/card/equality work and
   settled owner wording; review; step 5a's reviewed bridge; step 6's hosted
   checks/full model and tools VM rehearsal; step 7's R29 handover. The R28
   metadata merge task and status-row gate remain with their owning steps.

### What the code does not show; the lead's check build

No image was built or booted in this run. The lead's single throwaway,
never-published **`check_build=build`** on this branch must show:

- The new image checks actually run and pass: both files' installed owner,
  mode and no-link checks, safe refusal/status checks, helper bytes and the
  ksshaskpass 6.7.5 pin. Unit tests and checks-only runs do not run these checks.
- Control's wrapper appears only at `cli`, matches its source and record, and
  `/usr/bin/aresos` remains the dispatcher. Existing root/ares `aresos --help`
  comparisons prove the handover against the installed Control, and the
  checkout-to-`control.json` and vendor checks still pass unchanged.
- The normal check-build evidence reaches `IMAGE_CHECKS_PASSED`,
  `CHECK_BUILD_PASSED` and `CHECK_BUILD_VM_PASSED`, including its one normal VM
  boot, active-session polkit and console-keymap checks. This is image proof;
  neither this build nor its normal VM pass qualifies 43's changed owner tools.

**22d's `os/ci/tools_local.py` does not fit this VM pass unchanged or without
its own harness.** Its `helpers_of` finds only a direct child of sudo running
`/usr/bin/ksshaskpass`; D9 inserts `timeout` as that child. `Walk.window()` also
requires the generated bootstrap fingerprint label and direct-parent relation,
not D8's fixed image label. Its caller/state/walk require the installed-tools
rehearsal's guest, serial-console interface and stand-in Git origin. The normal
`os/ci/vm.py` uses fixed virtio-channel checks and lacks that walk interface.
No window-driver/harness expansion was made as part of step 3.

Therefore **D9 and D11 rest on step 0's approved laptop try until R29's
rehearsal**. No completed try or its result is recorded here; the lead still
needs that evidence. Local tests do not prove window appearance, title, no
keyring, actual Cancel, authentication, post-window ticket refusal, toolkit
behavior with D11's environment, or D9's real ten-minute expiry.

R29's rehearsal must retain section 7's five dispatcher stages: Control help
and no-window refusal; check label/screenshot, Cancel then authentication and
no cached sudo ticket; up-to-date update; unattended ten-minute timeout; and
previous/update/reboot from a marker folder with the R28 bridge return. Staging
through the dispatcher remains R30's rehearsal obligation. Step 4 still adds
the guide/TABLE equality test, and final labels remain subject to the owner's
wording decision before step 6.

No new JUDGMENT-CALL: the implementation follows D20 with REVIEW-3 N1 and the
proposed D8 labels. The two integration gaps above are not reported green.

### The lead on step 3's PLAN-GAPs (2026-11-18)

- **Gap 1 (Control's side of D12):** sent to `linux-tools` on 2026-11-18 02:15. `newest` in `RESERVED` and the
  dropped top-level `log` shortcut land on `main` (they ride R28 with Control); the integration test's caller
  (`cli`) and the wrapper's header comment land on this branch with the install-map move, never on `main` first.
  `test_aresos_command`'s three-set test is red until `newest` is in `RESERVED`; that is the test working.
- **Gap 2 (no Control rule in `release_diff.py`):** R28 step 2 (`pkg/42-release-28`, running) adds Control's rules.
  At this branch's merge of `main` after R28 (Left, item 1), Control's wrapper rule moves to
  `/usr/libexec/aresos-control/cli` and `test_aresos_command_diff` must pass. It stays red until then, deliberately.
- **Decision 7's help line:** no line in Control's help naming the OS words for now; the guide card (step 4) names
  them.
- Local, outside the sandbox: `test_control_vm` 62 OK and `test_control_image` 16 OK (the sandbox's socket errors
  were environmental); `test_aresos_command` 14 (1 failure, gap 1); `test_aresos_command_diff` 2 (1 failure, gap 2).

## REVIEW-9 fixes (2026-11-18)

Built from clean `01733209` (the review record after `6e2b03d4`). Nothing is
committed or pushed; the lead commits. The excluded trees (`control/`,
`os/owner-tools/`, `os/release/`, `docs/`) are unchanged. No sudo, dispatch,
deployment command, rebind, window or Gradle command ran.

- **Installed bytes and metadata — `os/ci/check-image.sh:11`:** copy the two
  installed files into an evidence tar archive before running image checks.
  Its Python check compares `/usr/bin/aresos` and `/usr/libexec/aresos-askpass`
  byte for byte with this checkout's `os/config` sources, requires both source
  and installed files to be regular and 0755, and requires installed numeric
  owner/group 0:0. Keeping tar metadata avoids losing ownership when extracting
  as the runner. Symlinks and hard links fail. The archive and the
  `ARESOS_COMMAND_FROM_CHECKOUT` result stay under `evidence/image/`.
- **Refusal execution — `os/ci/image-checks.sh:811`:** both refusal probes run
  the installed dispatcher with an audit hook that rejects exec, spawn, shell
  and fork attempts before they execute. The exact existing stderr/status
  checks remain. Xtrace is disabled around the function probes so its own
  trace cannot contaminate captured stderr.
- **Exact hand-over — `os/config/usr/bin/aresos:74`:** `main()` supplies
  `plan()` the process's original `/proc/self/environ`, rather than Python's
  coerced environment. Filesystem decoding preserves arbitrary environment
  bytes through `execve`. The shebang stays `-ISB`; the sole new read is the
  kernel's original environment, as requested by this review fix.
- **Regressions — `os/tests/test_control_image.py:275`:** execute the new
  checkout-comparison heredoc on fixture archives. REVIEW-9's exact offered
  branch mutation (`update` mapping to inner `update`) fails with
  `usr/bin/aresos: bytes differ from checkout`. Changed bytes, either owner,
  mode (including setuid), symlinks and hard links fail for either file. At
  `:318`, execute the refusal heredoc on both paths and prove attempted sudo,
  Control, shell and subprocess starts are observed and blocked. The complete
  surrounding Bash refusal block also runs with a stand-in for `runuser` and
  the fixture dispatcher, including xtrace and exact output/status checks.
- **Locale regression — `os/tests/test_aresos_command.py:220`:** execute a copy
  of the real dispatcher through its real shebang, changing only Control's
  destination to `/usr/bin/env -0`. Compare the entire emitted byte stream
  under `env -i`, `env -i LANG=C`, explicit C locale variables, and values
  containing non-UTF-8 bytes, equals signs, spaces and an empty value. No
  second Python interpreter can mask the hand-over by coercing its input.
  Unit `main()` fixtures at `:152` now supply the original-environment reader.

Each requested module ran separately with exactly
`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p '<module>.py'`:

| Module | Printed result |
|---|---|
| `test_aresos_command.py` | `Ran 15 tests in 0.164s`, `FAILED (failures=1)`; 14 pass, only Control's deliberately missing `newest` |
| `test_aresos_command_diff.py` | `Ran 2 tests in 0.146s`, `FAILED (failures=1)`; only the deliberately absent Control wrapper diff rule |
| `test_control_image.py` | `Ran 18 tests in 5.492s`, `OK` |
| `test_owner_path.py` | `Ran 48 tests in 1.778s`, `OK` |

An earlier `test_control_image.py` run also passed all 18 tests in 5.355s,
before the surrounding Bash-block coverage was added. No test was skipped,
deleted or weakened. No environmental temporary-file or socket error occurred.
`bash -n os/ci/check-image.sh os/ci/image-checks.sh` and `git diff --check`
exited 0 without output. The excluded-tree diff also exited 0 without output.
`.work files over 500 MB: []`; no download or screenshot was made.

**Not verified:** no image build or container/image execution ran. The lead's
check build must run the new export/comparison and refusal probes against the
installed files; local tests exercise their actual check code with fixtures.
The two integration failures remain exactly the lead's documented gaps above.
No new PLAN-GAP, JUDGMENT-CALL or open question.

## REVIEW-10 fixes (2026-11-18)

Built from clean `928c145d`, which records REVIEW-10 of `6662c152`.
Nothing is committed or pushed; the lead commits. The excluded trees
(`control/`, `os/owner-tools/`, `os/release/`, `docs/`) are unchanged.
No sudo, owner-tool dispatch, deployment command, rebind, window or Gradle
command ran.

- **Duplicate environment names — `os/config/usr/bin/aresos:74`:** the
  original-environment reader now keeps the first entry for each name, matching
  `os.environ` and glibc's `getenv`. It still reads `/proc/self/environ` and
  filesystem-decodes the original values, without Python's startup locale
  coercion. The comment explicitly says that a mapping hand-over collapses
  duplicates to the first entry; it does not preserve duplicate entries.
- **Raw-exec regression — `os/tests/test_aresos_command.py:237`:** libc's
  `execve` supplies `DISPLAY=` followed by `DISPLAY=:2`, plus `LANG=C` and
  duplicate non-UTF-8 values. A copy of the real dispatcher runs through its
  real shebang. `check` must refuse with the exact existing line and status 2;
  Control's stand-in (`/usr/bin/env -0`) must receive only the first values,
  with no added `LC_CTYPE`. The fixture forces an ordinary account even in
  root CI and replaces sudo with `/usr/bin/false` so a broken refusal is safe.
- **Caught audit exceptions — `os/ci/image-checks.sh:812`:** the shell creates
  and owns an attempt file and gives the audited interpreter a write descriptor.
  The hook writes each process event before raising. After the interpreter
  exits, any recorded attempt forces status 1, even if the dispatcher caught
  the exception and returned its normal refusal. The shell prints the record
  and removes the temporary file. Existing exact refusal/status checks remain.
- **Caught-attempt mutations — `os/tests/test_control_image.py:372`:** run
  the complete Bash refusal block with a stand-in for `runuser`. For each of
  its two refusal paths, inject REVIEW-10's `try/except Exception: pass` around
  sudo exec, Control exec, posix-spawn, shell, fork, forkpty and subprocess
  attempts. All 14 mutations must fail the block, report the event and omit
  its PASS marker. The existing uncaught-attempt coverage still runs using
  an inherited attempt descriptor.

Each module ran separately with exactly
`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p '<module>.py'`.
Before changing production code, the new command regression failed alongside
the intentional word-set failure (`Ran 16 tests in 0.221s`,
`FAILED (failures=2)`). The image module's new mutation test failed all 14
subcases (`Ran 19 tests in 6.332s`, `FAILED (failures=14)`): the old complete
Bash block incorrectly exited 0 and printed PASS after each caught attempt.

Final results after both fixes:

| Module | Printed result |
|---|---|
| `test_aresos_command.py` | `Ran 16 tests in 0.259s`, `FAILED (failures=1)`; 15 pass, only the intentional missing Control `newest` reservation |
| `test_aresos_command_diff.py` | `Ran 2 tests in 0.150s`, `FAILED (failures=1)`; only the intentional absent `cli` diff rule |
| `test_control_image.py` | `Ran 19 tests in 6.150s`, `OK` |
| `test_owner_path.py` | `Ran 48 tests in 1.724s`, `OK` |

No test was skipped, deleted or weakened. No environmental temporary-file or
socket error occurred. `bash -n os/ci/image-checks.sh`, `git diff --check`
and `git diff --exit-code -- control/ os/owner-tools/ os/release/ docs/`
exited 0 without output. `.work files over 500 MB: []`; no download or
screenshot was made.

**Not verified:** no image build or container/image execution ran. The lead's
check build still needs to exercise the installed files and the real `runuser`
descriptor hand-off; local tests exercise the actual refusal block with its
stand-in. The two intentional integration PLAN-GAPs above remain unchanged.
No new PLAN-GAP, JUDGMENT-CALL or open question.

### Step 3 reviewed (2026-11-18)

REVIEW-9 (one should-fix, one note) and REVIEW-10 (two should-fix) are fixed; **REVIEW-11 SAFE** on `a93c07a5`.
Check build 44212704741 on `82bd71bd` (before the fixes): IMAGE_CHECKS_PASSED, CHECK_BUILD_PASSED,
CHECK_BUILD_VM_PASSED, CONSOLE_KEYMAP_PASSED, Control 74 files. Check build 44215602914 on the reviewed head `b9452705` (run because the fixes
changed `check-image.sh` and `image-checks.sh`) passed: ARESOS_COMMAND_FROM_CHECKOUT, IMAGE_CHECKS_PASSED,
CHECK_BUILD_PASSED, CHECK_BUILD_VM_PASSED, CONSOLE_KEYMAP_PASSED. The two red tests still wait for `linux-tools`' `newest` in
Control's RESERVED and for R28's Control rule (lead's note above).

## Step 4 (2026-11-18)

Built from clean `1a4d783f` on `pkg/43-aresos-command`. Nothing committed or
pushed; the lead commits. Before reading or changing the guides,
`rg -n 'NOT ON THE LAPTOP' docs/INSTALL-STATUS.md` printed nothing (no matches).
The status-row gate passed. No owner-tool entry, sudo, workflow dispatch,
deployment command, rebind, window or Gradle command ran.

### Done

- `docs/INSTALL.md`: the new AresOS 29 terminal box follows 22d's routine box.
  It holds all nine commands and exact window lines, the three password
  conditions and the window's limit, the automatic ten-minute close, every
  section 5 outcome and the interrupted-older-update STOP. The two console
  outcome boxes are named where their lines follow. It explains console-word
  translation, tools before a release, the offline tools-version comparison,
  announcements, failed updates, separate restart approval, stale titles,
  both rollback rules, login/network and lock refusals, keeper failure,
  title posts and STOP/export. The routine box's opening and final handoffs
  now point to the next box on AresOS 29; its generated lines are unchanged.
  The first-session check proof names the session's own program.
- The console boxes retain their rules and command bytes. Only the Windows
  box's obsolete position wording changed; the single full newest-command
  sentence moved into the new box. A comparison of the console portion
  against HEAD, normalising just those two changes, passed.
- `docs/EMERGENCY.md`: availability near the top, desktop check/previous under
  the existing failed-update branches, the once-only warning and Help rule,
  and the aresos STOP/export route. The card keeps the same 16 headings and
  symptom layout (102 lines before, 103 after); no new section or table.
- `docs/INSTALL-STATUS.md`: the aresos route is explicitly OPEN until R29's
  dispatcher rehearsal. It distinguishes image/unit checks, package 43's
  future tools VM proof and R29's future dispatcher proof. No tools rehearsal
  receipt was invented. `os/README.md` adds the command, dispatch and proof
  paragraph.
- `os/tests/test_aresos_command.py`: the new test compares the complete guide
  window table, including order, full commands, labels and row count, with
  every offered TABLE row. Extra/refused/duplicate rows cannot hide in a dict.
- `os/tests/test_owner_equality.py`: inline commands also accept exactly the
  offered desktop invocations, read as data from TABLE, without a second
  word list or any dispatcher execution. They still reject shorthand, extra
  arguments, a sudo prefix and refused desktop aliases. Bare aresos remains
  a descriptive program name. Bundle-command and bootstrap equality rules
  remain intact. `test_owner_path.py` pins the new box position and the new
  N4/N7 card text; its existing console-order and recovery assertions remain.

### N4 and N7

**REVIEW-3 N4:** both guide and card say that after **was not applied** the next
update can repeat immediately, but an older running AresOS goes forward to
the newest installed AresOS first. The first owner word, usually check, shows
the warning once. Only an update that is itself first pauses without changing
anything. Every repeat remains Help's decision, never a run to see what it says.

**REVIEW-3 N7:** chose to name the keeper's never-started/give-up case explicitly
inside the card's existing **Any other result** branch, with Help allowed to
ask for aresos title. Otherwise a true session failure could look like broken
tools, and the owner would have no obvious route to the running/next-start
facts. Rejected leaving this implicit under **Any other result** for that
reason. No new branch or automatic title after a STOP: Help decides, and the
normal STOP/export rule still applies. This is reversible guide wording, with
one test pin to update later; no tools behavior changed.

### Tools, bridge and bindings

No tools text or bytes changed. The dispatcher/helper, `control/`, release
scripts, payload, commands.json, history, pending-rebind.json and
`docs/OWNER-TOOLS.md` are unchanged. Checked commands.json's newest entry is
the exact full console command. Tools version 6 and fingerprint
`f66fd69442857b911b81775bbc2efb3edf53648b391615b38234b2ddcea9d135`
still match OWNER-TOOLS.md. No payload generation or fingerprint pin refresh
was needed or run.

The R28 bridge is only a marked HTML placeholder in INSTALL.md before the
Windows-side box. Step 5a fills it with its three generated lines and their
own fingerprint labels; none was generated or added here. The placeholder
records the announcement, Help and Restart now? rules that step 5a must carry.
Until then the visible guide keeps AresOS before 29 on the console route.

Changed bound files, all already on the waiting list with older hashes:

- `docs/INSTALL.md`
- `docs/EMERGENCY.md`
- `os/tests/test_owner_equality.py`
- `os/tests/test_owner_path.py`

The other changed files are unbound. Per this run's instruction, no rebind
ran and the waiting list was not edited by hand. The lead must refresh those
four rows; the binding check correctly refuses their stale hashes meanwhile.

### Verified

Every module ran alone with exactly
`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p '<module>.py'`.

| Module | Result |
|---|---|
| `test_owner_equality.py` | `Ran 12 tests`, `OK` |
| `test_owner_path.py` | `Ran 48 tests`, `OK` |
| `test_aresos_command.py` | `Ran 17 tests`, `FAILED (failures=1)`; only the intentional three-word-set failure: Control lacks newest. The new guide-table test passes |
| `test_owner_newest.py` | `Ran 21 tests`, `OK` |
| `test_owner_release_numbers.py` | `Ran 7 tests`, `OK` |
| `test_release27.py` | `Ran 41 tests`, `OK` |
| `test_checkout_sources.py` | `Ran 8 tests`, `FAILED (failures=1)`; exactly the four changed bound files listed above have stale waiting hashes |
| `test_aresos_command_diff.py` | `Ran 2 tests`, `FAILED (failures=1)`; only the intentional missing rule for `/usr/libexec/aresos-control/cli` |

The first owner-path run had two failures: the old eleven-box count and the
old exact **Any other result** sentence. Its pins now require twelve boxes,
the unchanged console ordering, and the explicit new N4/N7 instructions; the
rerun passed. No assertion was weakened, skipped or deleted. No temporary-file
or socket error occurred. The equality module was repeated after the final
guide additions; final results above are for the finished text.

`git diff --check` passed without output. The protected-tree diff printed
nothing. Read-only checks printed PASS for the unchanged console boxes, newest
entry and fingerprint. `.work files over 500 MB: []`. No download or screenshot
was made. No live password window, phone reading/page layout, reboot, real
update, new tools VM rehearsal or dispatcher rehearsal was tested in this step.

### Owner wording still pending; show before step 6

These are locations, not another copy of either proposed list:

- **Call 1:** INSTALL.md's **Command / Line in the window** table, lines
  288–298. All nine prefix-free proposed labels are together and held equal
  to TABLE. Their list still awaits the owner's OK.
- **Call 2:** the first five rows of **What the tools say**, lines 311–315,
  are the five proposed answers to him, in the proposed order. The remaining
  rows through line 325 and their second-column sentences hold every other
  update/return/ready line, removal and settings fact, tools-version limit,
  and both later-install endings. Show those too; settle them with call 2.
- **D19:** show the exact existing keeper STOP in
  `os/owner-tools/owner.py:2161` (the full sentence is also in DESIGN.md,
  section 1a), together with INSTALL.md:335's session/Help explanation and
  EMERGENCY.md:25's explicit Help/title branch. It remains to be settled with
  call 2, not as a separate owner call. No tools wording was changed here.
- At the try, also show the three password conditions and their limit
  (INSTALL.md:300), the failed-update rule (329), **Restart now?** and its
  separate window (331), both rollback rules and the exact sentence Claude
  says before plain Bazzite (333), and the STOP/export rule (335). These
  implement the owner's settled answers and the lead's D20/D21 decisions;
  they do not reopen calls 4, 5 or 8.

### Left (in order) / PLAN-GAPs

1. Lead: refresh the four waiting hashes and commit this step; Astra review
   follows. Rerun the binding module after refresh. No new PLAN-GAP from the
   guide work; do not call the branch green with its current binding failure.
2. Keep the top-level merge-of-main task: real R28 record/number/target, payload
   and every pin, with the status-row gate rechecked. The two existing
   integration PLAN-GAPs remain with Control/R28; do not weaken their tests.
3. Step 5: independent review of steps 1–4. Settle the wording above before
   step 6; until then it stays explicitly proposed.
4. Step 5a: build and review the R28 bridge, replacing only the marked
   placeholder and refreshing any generated pins it needs.
5. Step 6: same-head hosted checks/full model, tools VM rehearsal including
   bridge windows, then rebind and record real evidence. No rehearsal claim
   was added here. Step 7 hands the dispatcher stages to R29; its route stays
   OPEN until R29's rehearsal. Live/phone proof remains with those steps.

### Step 4 reviewed (2026-11-18)

REVIEW-12 (Astra, on `ee738d1d`): two should-fix in docs/EMERGENCY.md, fixed by the lead in `c9ce1a25` (the routine
STOP card names the two refusals that are not a STOP; the was-not-applied warning sits inside its branch; both
pinned in test_owner_path). **REVIEW-13 SAFE.** Open: the card's literal one-page fit on paper and on his phone is
unverified (it grew by about 45 words); look at it on the phone with the owner before step 6. Calls 1 and 2's
wording still waits for his OK (the report of step 4 lists every sentence he should see).

**Next:** step 5 (an independent review of steps 1–4 together), then step 5a (the bridge's three generated lines),
then step 6 (needs published R28 and settled words).
