# 19b stage 2 — oracle independence review

**Reviewer angle:** only whether the test oracle's expectations, openings/closings of checks, ends of
obligations and resolutions come from independent inputs (script, server logs, fault trace, decoded commit
order), never from values production wrote. **Reviewed head:** `31eeb030` on `pkg/19b-owner-state`
(stage-2 diff `9eb193f2..31eeb030`, part A `fda0d164`). Read-only; nothing in the repository was changed
except this file. All probes ran in memory from the scratchpad
(`/private/tmp/claude-501/-Users-pab/5d5bbd0b-a538-400c-b84f-360fe127662f/scratchpad/oracle-review/probes/`),
with the worktree's existing venv and an in-memory managed-policy patch (no install, no containers).

**Method.** Besides reading the field-audit and resolution tables against the code, I planted real
production regressions *in memory* (patching `aresos_control.mail.adapter.Mail` / `filing` for one
scenario run, exactly as the sweep fixtures patch their servers), ran the unmodified `Driver` and
`Driver.compare` with a recording `Gaps` checker, and compared the full delta with the unplanted baseline
of the same flow. "Slipped" below means: the plant changes what the owner is told (or what the server
did), and the oracle's complete comparison reports no new difference.

## Blocking

### B1. A send's approved local stages are not required effects: a send that never makes its Sent copy finishes `done` silently

- **Where:** `control/owner_state_oracle/model.py:1311-1319` (`completion_errors`, `mail_send` branch
  requires only one accepted DATA with the approved envelope), `model.py:942-944` (`stage_claims` only
  validates a *claimed* `sent_copy: done`; an absent stage is never required), resolution table
  `resolutions.py:18` / FORMAT.md "completion: every approved effect accepted".
- **Reproduction (plant P1, flow `send`, client Sent policy):** `Mail.execute` wrapped so the
  `sent_copy` stage is never recorded and `Mail.local_stage('sent_copy')` returns `'done'` without
  APPEND or Sent search.

  ```text
  PLANT P1 send skips Sent copy and finishes done flow send
    planted op mail_send state done reason SMTP accepted delivery to every recipient. stages {'answered_flag': 'not_needed', 'message_id': ..., 'rcpt:anna@example.com': 'accepted:250', 'recipient:anna@example.com': 'accepted', 'smtp_data': 'accepted:250'}
    planted mutation commands [('DATA', None)]
    baseline differing views 0 | planted differing views 0
    NEW DIFFERENCES FROM PLANT: NONE  -> plant slipped through the oracle
  ```
- **Why it matters:** production's own rule makes this `partial` ("Missing local stages; repair without
  SMTP"), i.e. approved work the owner must see until repaired. The oracle derives "completion" from DATA
  alone, so a regression that drops the Sent copy (or the answered flag) erases that pending item and every
  view still compares equal. This is REVIEW-S1-3 #1's class (completion narrower than the approval) for the
  local stages.
- **Fix:** derive the full effect plan of a send from the approval plus the account's independently observed
  Sent policy at the call: Sent copy (exact APPEND to the observed Sent role, or a correlated read-only SENT
  match), and the answered flag when `answered_reference` is approved. `completion` must require each;
  `stage_claims` must require every planned stage to be present. Add P1 as a regression test.

### B2. Script authority is missing for the Sent-copy APPEND, the draft APPEND and the answered-flag STORE: coherent context + command can do something else

- **Where:** `control/owner_state_oracle/context.py:241-376` (`script_differences` derives destinations
  and flags only for move/copy/delete/rename/create/folder-delete/`mail_flag`/onboarding; for `mail_send`,
  `mail_unsubscribe`, `mail_operation_repair` and `mail_draft_save` it checks message identity
  (`:355-361`) and `append_flags` (`:364-373`) but never the APPEND destination or the STORE flags);
  `model.py:945-949` (`answered_flag: done` accepts *any* accepted STORE); `model.py:942-944`
  (`sent_copy: done` accepts an APPEND to any folder).
- **Reproductions:**
  - **P2** (reply send; `Mail.answered_context` and the answered branch of `local_stage` changed to
    `+FLAGS.SILENT (\Deleted)`, context and command agree):
    ```text
    planted op mail_send state done ... 'answered_flag': 'done', 'sent_copy': 'done', 'smtp_data': 'accepted:250'
    planted mutation commands [('DATA', None), ('APPEND', None), ('STORE', ['1', '+FLAGS.SILENT', '(\\Deleted)'])]
    baseline differing views 0 | planted differing views 0
    NEW DIFFERENCES FROM PLANT: NONE  -> plant slipped through the oracle
    ```
  - **P6** (`append_context`/`append_with_context` send the `(\Seen)` Sent copy to `INBOX`):
    `APPEND folders: ['INBOX']`, op `done`, `sent_copy: done`, **no new difference**.
  - **P7** (`mail_draft_save`, `(\Draft)` APPEND sent to `Sent`): `APPEND folders/flags: [('Sent', '(\\Draft)')]`,
    **no new difference**.
- **Why it matters:** the replied-to original is marked deleted, or the owner's Sent/Drafts record lands in
  another folder, while the action reports success and nothing is disclosed. R2's comparison is supposed
  to be "script/approval, committed context and actual command independently" (REVIEW-S1 #2, S1-2 #2);
  here the only authority is context-equals-command.
- **Fix:** in `script_differences`, derive from the script plus the independent pre-command LIST: Sent-copy
  APPEND destination = the unique observed Sent role (or, for repair, the parent's), draft APPEND
  destination = the unique observed Drafts role, answered STORE = exactly `+FLAGS.SILENT (\Answered)` on the
  approved `answered_reference`; check both command and context. Make `stage_claims` use the same derived
  command (folder, UID and flags), not "any accepted APPEND/STORE". Add P2, P6, P7 as tests.

### B3. Permanent deletion is "complete" without the `\Deleted` STORE; the `marked:` stage justifies itself

- **Where:** `model.py:1320-1334` (`mail_delete` permanent completion requires one accepted `UID EXPUNGE`
  per target only), `model.py:916-965` (`stage_claims` has no branch for `marked:*` — any claimed
  "deleted flag set" passes), `context.py:315-316` (flags checked only *if* a STORE happens); compounded by
  the sweep fixture `control/mail_tests/test_review23_sweep.py:339-347`, whose EXPUNGE removes the message
  regardless of `\Deleted`.
- **Reproduction (P4, flow `delete_permanent`):** the IMAP client handed to `Mail.execute` swallows the
  `STORE … (\Deleted)` (returns OK without reaching the server); production still records
  `marked:*: deleted flag set`, EXPUNGEs and finishes.
  ```text
  planted op mail_delete state done reason Exactly named messages deleted; no unnamed UID expunged. stages {'marked:2d78…': 'deleted flag set', 'marked:6df6…': 'deleted flag set', 'target:2d78…': 'expunged', 'target:6df6…': 'expunged'}
  planted mutation commands [('EXPUNGE', ['1']), ('EXPUNGE', ['2'])]
  baseline differing views 0 | planted differing views 0
  NEW DIFFERENCES FROM PLANT: NONE  -> plant slipped through the oracle
  ```
- **Why it matters:** on a real server `UID EXPUNGE` removes only `\Deleted` messages, so the approved
  deletion did not happen while the owner is told it did; and production's own `marked:` claim is accepted
  without a correlated command.
- **Fix:** for permanent mode require, per approved target, an accepted, delivered
  `UID STORE uid +FLAGS.SILENT (\Deleted)` before its accepted `UID EXPUNGE uid` in the same folder; validate
  `marked:*` against that STORE in `stage_claims`. Make the sweep fixture's EXPUNGE honour `\Deleted`
  (otherwise the fixture state cannot reveal the omission either). Add P4 as a test.

### B4. A free change's recovery obligation ends on "some delivered effect"; the omitted-branch check is switched off by any fault

- **Where:** `model.py:967-974` (`intent_result_proof`: if any bound command exists, completion =
  "all bound commands delivered"; it never compares with the scripted effect plan), `context.py:384-403`
  (`missing_flag_commands` skips the whole call when `faults.trace` is non-empty, `:395`), resolution table
  `resolutions.py:29` (`intent_completion` needs only "correlated effect/reply").
- **Reproduction (`probes/flag_branch.py`, in-memory oracle):** `mail_flag` asks `add=[\Seen]`,
  `remove=[\Flagged]`; production sends only `+FLAGS.SILENT (\Seen)` (coherent context) and removes the
  intent. With and without an unrelated storage fault in the call's trace:
  ```text
  fault trace=False: expected={} differences=[('R2.context-before-command', 'R2.STORE', '{"flags":["-FLAGS.SILENT","(\\\\Flagged)"],"missing":{...}}')]
  fault trace=True: expected={} differences=NONE
  ```
- **Why it matters:** the sweep injects a fault into almost every case, so in exactly the modes this package
  exists for, a half-applied free change can drop its recovery notice with no difference. The fault
  excuse is meant to say "an interrupted batch may legitimately stop" — but then the intent must stay open,
  and the oracle never requires that.
- **Fix:** `intent_result_proof` must require the complete scripted effect plan (every reference × every
  requested flag branch, the exact folder for create/rename/delete) accepted and delivered before the
  completion commit; when a fault interrupts the batch, keep the intent obligation (recovery) instead of
  skipping the check. Add both variants above as tests.

### B5. The alteration (perturbation) test has no teeth for the semantic layer; part A's "broken oracle that ignores that field" control is not what was built

Part A item 3 asked for field-level perturbation where "caught" means the difference reaches the sweep's
comparison, a planted real bad production change per field kind, and "a deliberately broken oracle (one that
ignores that field)" that makes the alteration test fail. The field-level enumeration and the forwarding
through `compare_proofs` are done. The rest does not show what it claims:

1. **Every planted fault is caught only by a projection-consistency check, not by the field's validator.**
   The plants are applied to a `fixture_input` row (`test_owner_state_perturb.py:117-124`) and the first
   matching mutation is usually a projection-only edit. Re-running part A's exact selection
   (`probes/planted_analysis.py`):
   ```text
   account          field=rows/intent:field-audit/context/account          caught-by=[('lifecycle-proof', 'changed-decoded-projection')]
   append_flags     field=rows/intent:field-audit/context/append_flags/0   caught-by=[('lifecycle-proof', 'changed-decoded-projection')]
   recipient        field=rows/intent:field-audit/context/recipients/0     caught-by=[('lifecycle-proof', 'changed-decoded-projection')]
   … (11 of 13 identical; dropped sequence adds missing-committed-history; restore marker uncommitted-event/unjustified-restore-transition)
   ```
   `changed-decoded-projection` compares the decoder's `rows` with the decoder's own events; real production
   cannot produce that mismatch. The "removed row" plant removes `generation`, not an obligation source.
   The coherent event versions of these plants would be caught by `changed-fixture-input`, because the
   planted row is itself a scripted fixture input. With `script_differences`, `stage_claims`, `completion_errors`,
   `payload_claims` and `local.errors` all disabled (`probes/planted_broken.py`), all 13 plants are still
   "caught", identically.
2. **The broken-oracle control replaces `compare_proofs` wholesale** (`test_owner_state_perturb.py:166-173`):
   it emits no difference at all and keys on object identity (`value is changed`). That proves `check()` can
   raise, not that the test notices an oracle that ignores one field.
3. **Realistic broken oracles pass the alteration test.** `probes/teeth.py` runs `perturb.check` on four
   real recordings (`send`, `delete_permanent`, `filing_move`, `unsubscribe_https`; 10,913 alterations) with
   one validator removed at a time:
   ```text
   [intact oracle]                                              all four: slipped=0
   [no script authority for context (script_differences -> [])] all four: slipped=0
   [no stage validation (stage_claims no-op)]                    all four: slipped=0
   [no completion validation (completion_errors -> {})]          all four: slipped=0
   [no payload/approval validation (payload_claims no-op)]       all four: slipped=0
   [no filing validation (filing_claims returns row)]            all four: slipped=0
   [no transition gate (transition returns row)]                 all four: slipped=0
   ```
4. **Why:** each mutation edits one copy of a value production writes several times (event, projection,
   compact fence, and the `committed_before` snapshot the driver stored in every later server event). The
   oracle cross-checks those copies (`changed-decoded-projection`, `changed-fenced-operation`,
   `changed-observed-commit`, `changed-fixture-input`), so nearly every expectation-changing alteration is
   "caught" structurally. `probes/catch_kinds.py`: only 24–37 of 1,692–4,942 alterations per scenario change
   the expected set at all, and many of those are caught by structural kinds only (send 9/36, filing_move
   18/24). A real production lie is written coherently into all copies; the test never models that. It also
   never perturbs the server-log snapshots the expectation code reads (`committed_before`, `created_before`,
   `check_sources`, `commit_observations`), and never deletes a nested key (`context`, `stages.<name>`,
   `approval`, …).
5. **A slipping perturbation in the test's own terms** (`probes/coherent.py`, `filing_rename`): the test's
   three single-site mutations of `mail:rename:*/message_count` are "caught" (`changed-decoded-projection`,
   `changed-observed-commit`, or no expected change at all). The same lie written coherently (events,
   projection, every `committed_before` snapshot) changes the expected notice from `"message_count":7` to
   `"message_count":2` with **no new difference**; the RENAME server log shows 7 identities. (B1–B4 and
   S2 are further slips the green test cannot see.)
- **Why it matters:** the brief made this test "how the next review checks the class". As built, it
  cannot distinguish an oracle that validates a field from one that does not, so the class can reopen
  silently (B1–B4 already have).
- **Fix:** (a) add coherent variants: apply each lie to the event, the projection, the matching compact
  fence operation and every later `committed_before`/`check_sources`/`commit_observations` copy; for those,
  count only non-structural differences as caught. (b) add nested key deletion. (c) replace the planted
  faults with real production regressions run through `Driver.compare` (P1–P7 above are ready-made), one
  per field kind, each required to produce a difference. (d) make each broken-oracle control disable the one
  validator for its field (`script_differences`, `stage_claims`, `completion_errors`, `filing_claims`,
  `payload_claims`, `local.errors`, the transition gate) and require the alteration test to fail.

## Should-fix

### S1. `unknown`/`partial` reasons are production's choice from a whitelist, and the expected pending item carries it

- **Where:** `model.py:723-742` (reason accepted if it is any member of a fixed set; on mismatch an error is
  added but `value['reason']` is *not* replaced), `model.py:313` (expected `pending` detail is the row's
  reason), `model.py:588-589` (any bound command justifies `submitting → partial/unknown`).
- **Reproduction (P3, clean `send`, every recipient `accepted:250`):** `send_smtp` returns
  `('partial', 'Some recipients refused; accepted recipients must never be sent again.')`.
  `probes/p3_direct.py` on the recorded result:
  ```text
  P3 oracle-derived expected facts:
      pending {"reason":"Some recipients refused; accepted recipients must never be sent again.","state":"partial"}
  P3 differences reported by compare_proofs (lifecycle/completion/context): NONE
  P3 original reply notices ... pending items: [('partial', 'Some recipients refused; accepted recipients must never be sent again.')]
  ```
  The original reply's envelope matched the oracle. (In the full run later views differed only because
  production's own pending page dropped the item; the oracle flagged that as *missing*, i.e. it demanded
  the false refusal.)
- **Why:** a refusal reason and an extra pending item in normal use are justified by production's own
  row; the owner can be told recipients were refused when none were (or the reverse family on a real
  refusal). Same class as REVIEW-S1-2 #4.
- **Fix:** derive the expected state/reason family from the RCPT/DATA replies, the local-stage results and
  the fault trace (the same way reserved/submitting reasons are fixed), and replace a wrong reason in the
  retained projection, as `:716-722` already does.

### S2. The rename warning's message count comes from production's row ("compared" with itself)

- **Where:** `model.py:455-456` (`meta['message_count'] = context['message_count']`), with the context taken
  from the production row captured in `committed_before` (`model.py:427,437`, `226-230`). Field-audit row
  "Filing/rename … `message_count`" (round 2) says it derives from "bound context and raw evidence"; it
  derives from the bound context only.
- **Reproduction (P5, `filing_rename`):** `filing.rename_folder` receives a `uids` list whose `len()` is 2
  (iteration still visits all 7), so production records and discloses 2.
  ```text
  planted rename message_count 2 RENAME server identities [7]
  baseline differing views 10 | planted differing views 10
  NEW DIFFERENCES FROM PLANT: NONE  -> plant slipped through the oracle
  P5 oracle-derived expected: notice-context {... "message_count":2 ...}   (baseline: 7)
  ```
- **Fix:** expected count = number of identities in the source folder in the RENAME server event (or the
  scripted references for filing, as already done); compare the committed `message_count` against it.

### S3. The sweep's R2 check accepts a new-format operation that commits no context at all

- **Where:** `context.py:100-149` — `decode` uses `row['context']` only if present, otherwise synthesizes a
  context from payload/stages/`roles_before` for *any* row, including `context_version: 1` rows.
- **Reproduction (`probes/no_context.py`):** `context` removed from every pre-command snapshot and the
  record of real recordings (all rows have `context_version == 1`):
  ```text
  send               context removed from 6 pre-command snapshots ...; mutation commands ['APPEND', 'DATA']; R2 context_errors -> NONE
  delete_trash       context removed from 10 ...; ['MOVE']; R2 context_errors -> NONE
  delete_permanent   context removed from 12 ...; ['EXPUNGE', 'STORE']; R2 context_errors -> NONE
  unsubscribe_https  context removed from 1 ...; ['POST']; R2 context_errors -> [R2.POST account …]
  ```
- **Why:** only the clean-flow direct test (`test_action_context.py:52-56`) checks that the stage-2 context
  exists; in every faulted sweep mode a regression that stops writing it (or writes it after the command
  while the legacy fields happen to exist) is invisible. Stage 2's new field is trusted to be present
  without the oracle requiring it.
- **Fix:** use the legacy decoder only for rows without `context_version` that were part of the frozen
  seed/legacy fixture; for `context_version: 1` rows require `context` and report its absence as R2.

### S4. A runtime event that production labels `fixture` bypasses reason validation

- **Where:** `model.py:716` and `:723` (`event['action'] != 'fixture'`), `:702` (legacy marking). FORMAT.md
  says arbitrary production `fixture` events are not inputs; only events inside a scripted `fixture_input`
  interval are compared (`:624-627`).
- **Reproduction (`probes/fixture_label.py`):**
  ```text
  runtime event action='mail_send': expected pending=['{"reason":"All good: nothing to check.","state":"unknown"}'] reason-error=True
  runtime event action='fixture':   expected pending=['{"reason":"All good: nothing to check.","state":"unknown"}'] reason-error=False
  ```
- **Fix:** exempt only seed events and events inside a scripted `fixture_input` interval; report any other
  post-seed `fixture` event as a lifecycle difference.

### S5. The field audit omits the production rows embedded in the server log

Expectation code reads production-written rows that the driver copies into server events and that neither
the field-audit tables nor the alteration test cover: `committed_before` row content (binding by `state`,
`id`, `repair_of`, `account`, `target`, `context.operation_id`, `context.command` in `context.py:60-97`;
warning contexts and their `message_count`/`sources`/`target` in `model.py:226-230,427,437`; snapshot
consistency in `model.py:216-217`), `created_before`, and LIST `check_sources` = the keys of production's
rows (`driver.py:133`), which enrol a check for later-call evidence (`model.py:1250-1253`). I did not find a
false closure through `check_sources` (closing still needs correlated post-mutation LIST evidence and a
result proof), but each of these must be listed with its validation and be part of the perturbation set
(B5 fix a).

## REVIEW-S1-4's three findings

- **(a) Pre-command LIST closing a filing check — closed.** `read_evidence` (`model.py:1245-1255`) skips
  every LIST at or before the bound mutation. `StageTwoPartA.test_pre_move_list_and_undelivered_results_never_close_filing`
  passes. On a real recorded `filing_move` (`probes/s14.py`), where the pre-MOVE LIST is already *enrolled*
  (`check_sources` lists the filing row), I removed all post-MOVE LISTs, set `copyuid_delivered=False` and
  committed `done/check_open=False`:
  `differences: [('lifecycle-proof', 'unjustified-check-close', True), ('lifecycle-proof', 'unsupported-resolution', True), ('lifecycle-proof', 'unverified-destination', True)]`,
  `recovery retained for the filing: True`.
- **(b) Another operation's POST justifying an unsubscribe — closed.** `completion_errors`
  (`model.py:1365-1384`) needs this operation's call, the exact approved request, a delivered 2xx and the
  read/command/commit interval, bound to this key; `stage_claims`' `https_post` is likewise bound.
  `test_another_unsubscribe_post_cannot_resolve_this_operation` (200 then 500) passes and keeps recovery
  for the second operation.
- **(c) Alteration test skipping list entries and `append_flags` — closed as stated, but see B5.** Every
  list scalar is mutated independently plus a list-level change, `append_flags` included; the field set is
  derived from each decoded record and an unperturbed field fails (`test_field_audit_includes_each_list_scalar_and_append_flags`,
  `test_record_audit_fails_if_a_new_field_is_not_perturbed`, both pass). The teeth requirement of part A is
  not met.

## Imports and call paths (item 4)

No path found. `model`, `context`, `compare`, `local`, `records`, `resolutions`, `gaps`, `perturb` import
only the standard library and each other; none imports `driver`, `responses`, `transcript`, `clock`,
`storage_faults`, `response_checks` or `aresos_control`, directly or transitively. The objects the
expectation code receives from the driver are plain decoded data (deep-copied rows, server events,
script); `response_observer`/`alias_callback` are never called from expectation code. The AST test
(`test_expectation_imports_are_standard_library_only`) would catch a direct or relative production
import. Minor gaps in the test only: it bans `__import__` solely as a bare-name call (not
`builtins.__import__`/`getattr`), and its allowlist is bare top-level names, so `import records` would pass
if a same-named module ever appeared on `sys.path`.

## What I ran

- Oracle self-tests: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/mail_tests .work/venv/bin/python -m unittest discover -s control/tests -p 'test_owner_state_oracle.py'`
  → `Ran 116 tests in 0.239s`, `OK`. Part A class alone (`-v test_owner_state_oracle.StageTwoPartA`) →
  `Ran 8 tests in 0.028s`, `OK`.
- Strict focused set (my runner patches only the managed-policy read in memory, puts temp files in the
  scratchpad and turns off `.work/` artifact writes; children use the worktree's existing
  `.work/19b-s2/child-policy` shim): `STRICT_GAPS=1 … test_owner_state_contracts test_owner_state_regressions test_action_context`
  → `Ran 18 tests in 172.147s`, `OK`.
- Alteration test, four local shards (`OWNER_PERTURB_SHARDS=4`): see the result below.
- Probes (all in `probes/`): `plants.py` P1–P7, `p3_direct.py`, `teeth.py`, `catch_kinds.py`,
  `planted_analysis.py`, `planted_broken.py`, `coherent.py`, `no_context.py`, `fixture_label.py`,
  `flag_branch.py`, `s14.py`. Outputs quoted above.
- Not run: containers, the Linux sweep, the CI workflows.

**Alteration test result (local, four shards, `OWNER_PERTURB_SHARD=0..3 OWNER_PERTURB_SHARDS=4 … test_owner_state_perturb`):**
every shard printed `Owner planted field faults=13 caught by comparison; broken oracles rejected=13`,
then `scenarios=17` with `slipped=0` (totals 87,703 / 108,704 / 92,934 / 59,075 = **348,416** over 68
scenarios, matching the CI figure), `Ran 1 test in 232.037s / 311.368s / 325.946s / 162.725s`, `OK`. The test
is green on the reviewed head; B5 explains why green does not establish what it is meant to.

The repository's own fixtures create their temporary stores under the git-ignored `control/test-work/` and
`.work/mail-tests/` regardless of `TMPDIR`; my runs created and removed entries there. No tracked file
changed.

## Noticed outside this angle

- `testapp_flag` (stage 2's new free LOCAL_FLAG intent) is never driven by the owner sweep and is not an
  oracle mutation kind; only `test_local_free_flag_is_committed_before_effect_and_refused_commit_blocks_it`
  checks its context.
- The Sent-copy APPEND's bytes are compared with the context's `sha256` but not with the DATA wire bytes
  (or the Bcc variant); a different Sent body with a coherent context would pass.
- The sweep fixture's EXPUNGE ignores `\Deleted` (B3); the fixture's APPEND writes two copies, so the clean
  `send` baseline always carries a duplicate-Sent warning.

CHANGES-NEEDED
