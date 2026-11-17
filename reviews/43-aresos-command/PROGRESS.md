# Package 43 progress

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
2. **Step 2:** ledger `choose`, model driver and I1–I4; measure the full model
   before/after and run it hosted. No ledger/driver change or full-model result
   is claimed in step 1.
3. **Step 3:** dispatcher, askpass helper, Control bindings/tests, three word
   sets, image checks/diff rules, then a check build. Carry **REVIEW-3 N1** here:
   `keep-stock` gets the plain-Bazzite refusal with its full console command.
4. **Step 4:** guide box/card, equality tests, the owner's final wording and
   D19's keeper-failure wording; refresh payload and pins again if tools text
   changes. Carry **REVIEW-3 N4** here: after `was not applied`, an older running
   AresOS goes forward first. Carry **REVIEW-3 N7** here: decide whether the card
   names the keeper's give-up case and the Help/title route explicitly. Recheck
   the status-row gate first. D19's existing labwc/foot guide sentence belongs
   to this step with its other guide changes.
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
