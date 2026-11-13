# 19b stage 2, fixes round 1: oracle independence re-check

**Angle:** only the oracle findings of [`REVIEW-S2-ORACLE.md`](REVIEW-S2-ORACLE.md) (B1–B5, S1–S5 and the
"noticed outside this angle" items), checked against the fix diff `ce718024..68395f03`, plus whether those fixes broke
the code they touch. No fresh hunt. **Reviewed head:** `68395f03` on `pkg/19b-owner-state`. Read-only: the only file
written in the repository is this one. Probes ran in memory from
`/private/tmp/claude-501/-Users-pab/5d5bbd0b-a538-400c-b84f-360fe127662f/scratchpad/oracle-review-2/probes/` (the earlier
reviewer's probes, copied and adapted, plus new ones named below), with the worktree's existing venv and the same
in-memory managed-policy patch. The old-head comparisons ran on a `git archive ce718024 control` copy in that scratch
folder. No containers, no installs, nothing personal touched.

## Every earlier finding

| # | Finding | Status | Evidence (rerun at `68395f03`) |
| --- | --- | --- | --- |
| B1 | Send finishes `done` without its Sent copy | **Fixed** | P1 (`plants.py P1`, flow `send`): baseline 0 differing views, planted **40**. Semantic proofs: `unjustified-stage missing:sent_copy` (stage_claims), `false-completion "Approved local stage missing: sent_copy"` (completion), `unsupported-resolution completion` (transition gate); the expected set keeps the pending item and recovery. Before: NONE. `send_stages` (`effects.py:29`) takes the Sent role from the server-recorded roles and the policy from seed/script. |
| B2 | No script authority for Sent APPEND, draft APPEND, answered STORE | **Fixed** | P2: `R2.STORE ["script.command.flags","script.context.flags"]`, `unjustified-stage answered_flag`, completion refused (41 views). P6: `R2.APPEND ["script.command.destination","script.context.destination"]`, `unjustified-stage sent_copy` (41 views). P7: `R2.APPEND` destination + `unjustified-removal`, draft intent recovery kept (21 views). Destination/flags derived in `context.py:350-359`. Sent bytes vs DATA: `effects.py:73` (`wrong-sent-bytes` plant, Bcc test pass). |
| B3 | Permanent delete complete without `\Deleted` STORE; `marked:` self-justifying | **Fixed** | P4: 40 views; `unjustified-stage marked:<ref>` ×2 (`model.py:1177`), `false-completion "Exact Deleted STORE missing before EXPUNGE"` (`model.py:1705`), completion refused. The sweep fixture now keeps both messages: Source UIDs after P4 `[1..7]` (before the fix the fixture removed them). |
| B4 | Free-change recovery ends on "some effect"; omitted branch unchecked under a fault | **Fixed** | `flag_branch.py`: no fault → `R2.STORE` missing `-FLAGS.SILENT (\Flagged)` + `unjustified-removal`, expected `recovery`; with fault → `unjustified-removal`, expected `recovery` (before: `expected={}`, NONE). `intent_result_proof` requires `complete_plan` (`model.py:1202-1215`, `effects.py:38-71`). |
| B5 | Alteration test has no teeth | **Fixed except (d)** | (a) coherent lies: `perturb.py:284-487` write the lie into events, prepared, projection, compact fences (hash chain rebuilt), and every later `committed_before`, `created_before`, `check_sources`, `commit_observations`; coherent variants count only non-`STRUCTURAL` differences (`perturb.py:583-585`). Coherent `message_count` lie (`coherent.py`) now: expected set unchanged, new `changed-filing-context`, `unapproved-filing-context` (before NONE). (b) nested key deletion: every dict key at every depth (`perturb.py:67`); 805,077 of the alterations. (c) 21 real production plants through the unmodified `Driver`/`Driver.compare` (`owner_state_plants.py`), all caught — but see S-N3 on how the assertion is written. (d) single-validator controls: **only formally met**, see S-N2 and the matrix below. |
| S1 | `unknown`/`partial` reason chosen by production | **Fixed** | P3 (`p3_direct.py`): `unjustified-operation-reason`; the expected set no longer contains production's false "Some recipients refused…" pending item (before: the oracle expected it). `outcome()` (`model.py:1261`) derives state and reason from RCPT/DATA, local effects and faults and replaces a wrong pair. |
| S2 | Rename count from production | **Fixed** | P5: `unapproved-filing-context {"actual":2,"expected":7,"field":"message_count"}`; expected notice `message_count 7` (before 2). Count from the RENAME server event (`model.py:522-524`, `filing_claims` at `model.py:151`). |
| S3 | Version-1 row without `context` passes R2 | **Fixed** | `no_context.py`: send → `R2.DATA`, `R2.APPEND`; delete_trash → `R2.MOVE` ×2; delete_permanent → `R2.STORE`/`R2.EXPUNGE` ×2; unsubscribe → `R2.POST` (before: NONE for the first three). `context.py:110-116`. |
| S4 | Runtime `fixture` label skips reason validation | **Fixed** | `fixture_label.py`: `action='fixture'` → `reason-error=True`, expected reason is the oracle's own "Submission outcome uncertain…" (before: `False`, production's "All good" reason). `unscripted-fixture-event` at `model.py:765`. |
| S5 | Server-log copies of production rows not audited | **Fixed** | `snapshot_mutations` (`perturb.py:231-250`) alters every scalar and key of `committed_before`, `created_before`, `check_sources` and `commit_observations`; `check()` fails if any snapshot field is not altered (`perturb.py:602-604`). Listed in REPORT.md's field-audit table and FORMAT.md. Coherent variants propagate into them (B5 a). |
| S1-4 (a) | Pre-command LIST closing a filing check | Still closed | `s14.py`: `unjustified-check-close`, `unsupported-resolution`, `unverified-destination`; recovery retained. |
| Outside | LOCAL_FLAG not modelled / not swept | **Fixed** | `local.py:50-75` validates reference, revision, requested value and prior context; `local_flag` in `EXTRA`; `local_flag_sweep.py` drove it through all 117 discovered fault points (single, persistent, crash). `false-local-flag` plant caught by `R2.LOCAL_FLAG` + `unjustified-removal`. |
| Outside | Sent-copy bytes not compared with DATA wire bytes | **Fixed** | `sent_bytes_match` (`effects.py:73-84`) in completion and context checks; `wrong-sent-bytes` plant caught; `test_sent_copy_with_approved_bcc_header_matches_the_data_wire` ok. |
| Outside | Fixture EXPUNGE ignores `\Deleted` | **Fixed** | `test_review23_sweep.py:349`; P4 run keeps UIDs 1 and 2; `test_uid_expunge_requires_the_exact_deleted_flag_and_preserves_unnamed_mail` ok. |
| Outside | Clean send baseline carries a duplicate-Sent warning | **Fixed** | `quiet.py`: `send` → 1 Sent copy, 0 reply notices, no non-pending expected facts; `send_duplicate` → 2 copies, 1 notice, `sent_copies` warning; `delete_trash`/`delete_permanent` quiet. (`filing_move` in the sweep fixture is its deliberate role-change warning case; the ordinary quiet move/copy/rename contracts are in `owner_state_cases.py:27`.) |
| Imports | AST test gaps (`builtins.__import__`, bare same-name module) | **Fixed** | Negative controls in `test_expectation_imports_are_standard_library_only`; 116 oracle tests OK. |

## Blocking

### N1. The fix round made the oracle refuse correct completions in four fault-free flows, and the pin records them as stage-3 production gaps

- **Where:** `control/owner_state_oracle/model.py:1643-1660` (new multiplicity check: the signature is command,
  account, folder, arguments, recipients, identities, and omits a LOCAL_STAGE event's `stage`) and
  `model.py:1669-1678` (new `mail_send` completion: DATA must be bound to the operation through committed context or
  `source`; a seed send's DATA is recorded by the fixture with `fixture_seed=True` and no `committed_before`,
  `test_review23_sweep.py:206-207`, so it is never bound). Both are part of the B1/2d fixes.
- **Reproduction (`baseline_any.py`, fault-free flows, same probe on both heads):**

  ```text
  flow             old ce718024                          new 68395f03
  testapp_send     0 differing views                     35 views; duplicate-effect call:LOCAL_STAGE / intent:LOCAL_STAGE,
                                                         unjustified-resolution, unsupported-resolution completion
  repair           2 views (unjustified-operation-reason) 41 views; false-completion "No matching accepted SMTP DATA",
                                                         unjustified-check-close, unverified-clean, unsupported-resolution
  settlement       2 views                               41 views; false-completion "No matching accepted SMTP DATA", ...
  status           1 view                                2 views; false-completion "Approved local stage missing: sent_copy",
                                                         "No matching accepted SMTP DATA"
  ```

  `local_stage.py` shows the two testapp events are different effects, each once:
  `LOCAL_STAGE stage= sent_copy` and `LOCAL_STAGE stage= answered_flag`, and
  `completion_errors → ['call:LOCAL_STAGE', 'intent:LOCAL_STAGE']`. The repair seed DATA is
  `('DATA', fixture_seed=True, before_seq=None, committed_before=False)`.
- **It is pinned.** The fault-free point-0 groups in `KNOWN-GAPS.json` changed exactly by these counts:
  `testapp_send` shared groups M06 9 + M14 26 = **35 keys, none before**; `repair` 2 → **41**; `settlement` 2 → **41**;
  `status` 1 → **2** (samples such as `repair/single/0/0/live-restored/completion`,
  `testapp_send/single/0/0/live-restored/control_pending.notice-head`). All are labelled stage 3.
- **Why it matters:** the oracle now expects a recovery notice and a pending item for a clean test-app send and for a
  correctly repaired or settled mail send; production rightly shows nothing. The brief's rule is "nothing extra in
  normal use", and the ledger is meant to list production gaps that stage 3 closes. These keys are oracle defects that
  stage 3 cannot close by changing production (the only production change that would "pass" them is showing a false
  notice), and while pinned, these flows compare production against a wrong expectation. REPORT.md attributes the
  pin change to new flows and "stronger retained-obligation checks" and does not mention fault-free regressions.
- **Fix:** add `event.get('stage')` (and any other recorded discriminator) to the multiplicity signature; accept a
  fixture-recorded seed DATA (`fixture_seed=True`, matching Message-ID and the scripted seed call) as delivery evidence
  for that operation's completion, `send_stages` and `outcome()`. Add fault-free `testapp_send`, `repair`,
  `settlement` and `status` to the quiet contracts (`owner_state_cases.py:27`) so a new oracle-side difference in
  normal use fails directly instead of entering the pin, then re-pin.

## Should-fix

### S-N2. B5 (d): disabling one validator does not make the alteration test fail for four of the seven; the repo's controls cannot fail to "reject"

- **Where:** `control/mail_tests/test_owner_state_plants.py:13-21, 24-29, 46-51`. Each control patches one validator
  to a no-op and asserts that `require_plant` raises "Validator missed production plant". `require_plant` looks only
  for facts in `proofs[validator]`, which a no-op can never fill, so this assertion passes by construction. It
  shows the intact validator catches its own plant (useful), not that the alteration test or the comparison notices a
  missing validator. REPORT.md's table ("Disabling only this validator: Plant assertion fails (required)") and
  FORMAT.md ("Each must make its own plant assertion fail, even if another validator also rejects the regression")
  describe exactly this. The brief asked for "the alteration test must then fail".
- **Alteration test, one validator removed (`teeth2.py`: 17 fault-free recordings, 226,372 alterations each; `teeth_faulted.py`: 8 faulted sweep recordings of the corpus, 123,754 alterations each):**

  | Validator removed | Fault-free recordings | Faulted recordings |
  | --- | --- | --- |
  | none (intact) | 0 slips | 0 slips |
  | `script_differences` | 0 slips | 0 slips |
  | `stage_claims` | **slips in 9/17** (first: coherent removal of the op's terminal row, e.g. `coherent/17/op:…/`) | not run (already shown) |
  | `completion_errors` | 0 slips | 0 slips |
  | `payload_claims` | 0 slips | 0 slips |
  | `filing_claims` | **slips in 3/17** (`filing_move`, `filing_copy`, `filing_rename`: coherent removal of the result row) | not run (already shown) |
  | transition gate | 0 slips | **slips in 1/8** (`delete_permanent` crash: coherent change at `coherent/7/op:…/`; the expected "Service restarted during submission" pending item changes) |
  | `local.errors` | 0 slips (including the `local_flag` recording) | not run (no LOCAL_FLAG in these) |

- **Plant level, one validator removed (`controls.py`, Driver.compare deltas against the plant-free baseline):**
  `local.errors` → `false-local-flag` produces **0** new views (the plant slips entirely); `filing_claims` →
  `false-rename-count` still differs in 10 views (expected count 7 comes from the RENAME event); transition →
  `false-transition` still differs in 4 views; `script_differences`, `stage_claims`, `completion_errors`,
  `payload_claims` → their plants are still caught by other validators (40–41 views).
- **Why it matters:** this is the original B5 question ("can the test tell an oracle that validates a field from one
  that does not?"). For `stage_claims`, `filing_claims` and the transition gate it now can. For `script_differences`,
  `completion_errors` and `payload_claims`, nothing in the alteration test or the plant comparison fails when the
  validator is removed (other validators catch their plants); only the provenance assertion does. For `local.errors`
  the plant comparison would fail (its plant slips completely), but no test checks that. Part of this
  is structural and should be said plainly: an oracle that ignores a field produces no change in its expected set, so
  the alteration test (which needs an expectation change to demand a difference) can never see it, and it never alters
  server commands, so it cannot need `script_differences`. Those validators can only be tested by plants.
- **Fix:** replace the provenance-only broken half with a comparison-level control: for each validator, a production
  plant whose `Driver.compare` delta against the plant-free baseline is non-empty with the validator and empty with
  it removed (`false-local-flag` already is one). Where no such plant exists because other validators overlap, say
  so in REPORT.md and FORMAT.md ("redundant with X and Y on this corpus") instead of "disabling it makes the test
  fail".

### S-N3. Plant assertions are not relative to the plant-free run, so some cannot fail

- **Where:** `test_owner_state_plants.py:38-40`: `assertTrue(deltas)` and "any non-structural difference" are
  checked on the planted run alone.
- **Reproduction (`vacuous.py`):** `wrong-recipient` runs on `testapp_send`, whose clean run already has 35 entries
  and non-structural facts (N1): both assertions would pass with no plant at all. The plant is in fact caught
  (`R2.RECEIVE` recipients, `false-completion "Receiver did not accept exactly once: alpha"`), but the test does not
  show it. The same holds for `missing-repair-parent-result` on `repair` (41 baseline entries), which is saved only by
  its extra `missing-operation-result` assertion, and for the `deltas` assertion of `false-rename-count`
  (`filing_rename` has 10 baseline entries).
- **Fix:** record each plant's flow once without the plant and require new views or new semantic facts relative to
  that baseline.

## What I ran

- Oracle self-tests, exactly as specified:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests .work/venv/bin/python -m unittest discover -s control/tests -p 'test_owner_state_oracle.py'`
  → `Ran 116 tests in 0.228s`, `OK`. Same with `-p 'test_owner_state_fixes_s2.py'` → `Ran 24 tests in 0.008s`, `OK`.
- `test_owner_state_s2_effects test_owner_state_plants` through my runner (policy patched in memory, temp files in the
  scratch folder, children via the existing `.work/19b-s2/child-policy` shim) → `Ran 7 tests in 2.416s`, `OK`.
- Alteration test, four local shards, the REPORT.md command shape (`OWNER_PERTURB_SHARD=0..3 OWNER_PERTURB_SHARDS=4 …
  test_owner_state_perturb`, recording mode, my runner instead of `.work/19b-s2/local.py` so temp files stay out of
  the repo): each shard first printed `Owner real production field controls=13 caught through Driver.compare` and the
  seven `Owner validator=… broken_rejected=1` lines, then:
  `scenarios=24 total=500770 slipped=0` / `Ran 1 test in 1247.625s` / `OK`;
  `scenarios=24 total=669952 slipped=0` / `Ran 1 test in 1919.871s` / `OK`;
  `scenarios=23 total=538757 slipped=0` / `Ran 1 test in 1253.812s` / `OK`;
  `scenarios=23 total=295565 slipped=0` / `Ran 1 test in 492.808s` / `OK`.
  Together: 94 recordings, 2,005,044 alterations, 257,524 coherent, 14,904 owner-set changes, zero slipped. Every
  per-validator own-catch and owner-set-change count equals REPORT.md's table exactly (for example `stage_claims`
  50,082 / 1,415, `transition` 12,134 / 3,588, `local.errors` 1,544 / 1,170). The total is 1,350 above REPORT.md's
  2,003,694, all in non-coherent alterations that change no expectation; I take this to be my policy shim differing
  from `.work/local-linux-policy.py` (assumed, not traced).
- Rename count fallback (`rename_norename.py`): with the RENAME never sent and a coherent count lie, no expected fact
  carries a count, so the `context['message_count']` fallback at `model.py:524` is not reachable that way.
- Probes (all in `probes/`): `plants.py P1–P7`, `plants_proofs.py`, `flag_branch.py`, `fixture_label.py`,
  `no_context.py`, `p3_direct.py`, `coherent.py`, `s14.py`, `quiet.py`, `local_flag_sweep.py`, and new for this round
  `teeth2.py`, `teeth_faulted.py`, `controls.py`, `vacuous.py`, `plant_baselines.py`, `baseline_detail.py`,
  `baseline_any.py` (both heads), `local_stage.py`. `planted_analysis.py`/`planted_broken.py` target part A's
  fixture-row plants, which this round replaced with production plants; `controls.py` is their replacement.
- Not run: containers, the Linux sweep, CI workflows, the strict pin check. The repository's own fixtures create
  temporary stores under the git-ignored `control/test-work/` and `.work/mail-tests/` regardless of `TMPDIR`; my runs
  created and removed entries there. No tracked file changed.

CHANGES-NEEDED
