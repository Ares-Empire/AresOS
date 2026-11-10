# 19b stage 2, fixes round 2

**Against** three scoped re-checks of fix round 1 (`ce718024..68395f03`), all CHANGES-NEEDED:
[`REVIEW-S2-ORACLE-2.md`](../reviews/19b-owner-state/REVIEW-S2-ORACLE-2.md) (Claude, oracle independence),
[`REVIEW-S2-2.md`](../reviews/19b-owner-state/REVIEW-S2-2.md) (sol high) and
[`REVIEW-S2-ASTRA-2.md`](../reviews/19b-owner-state/REVIEW-S2-ASTRA-2.md) (astra xhigh). Read all three in full, and
`briefs/19b-owner-state.md`, `briefs/19b-on-mail.md` (the note wins) and every `briefs/19b-s*.md`; all earlier rules
hold (R2 exact and folded, zero journal growth, compact ledger, structure S). Most round-1 findings are confirmed
fixed; fix only what is listed here, oracle items first. Do not start stage 3.

## 1. Oracle (REVIEW-S2-ORACLE-2)

- **N1, blocking: the oracle now refuses correct completions in fault-free flows, and the pin records them as
  stage-3 gaps.** `testapp_send` 0 → 35 keys, `repair` 2 → 41, `settlement` 2 → 41, `status` 1 → 2. Causes: the
  multiplicity signature (`model.py:1643–1660`) omits a LOCAL_STAGE event's `stage`, and `mail_send` completion
  (`model.py:1669–1678`) never binds a fixture-seeded DATA (`fixture_seed=True`, no `committed_before`). Add `stage`
  (and any other recorded discriminator) to the signature; accept a fixture-recorded seed DATA with the matching
  Message-ID and scripted seed call as delivery evidence for that operation's completion, `send_stages` and
  `outcome()`. Add fault-free `testapp_send`, `repair`, `settlement` and `status` to the quiet contracts
  (`owner_state_cases.py:27`), so an oracle-side difference in normal use fails directly instead of entering the
  pin. Then re-pin, and in the report list every fault-free group whose count changed and why.
- **S-N2, should-fix: single-validator controls.** Replace the provenance-only "broken" half: for each validator,
  a production plant whose `Driver.compare` delta against the plant-free baseline is non-empty with the validator
  and empty with it removed. Where overlapping validators make that impossible on this corpus, say so plainly in
  `REPORT.md` and `FORMAT.md` ("redundant with X and Y on this corpus"), and explain that an oracle ignoring a field
  can't be seen by the alteration test, only by plants. Fix the two alteration-test slips the reviewer measured:
  with `stage_claims` removed, coherent removal of an operation's terminal row slips (9/17 recordings); with
  `filing_claims` removed, coherent removal of a filing result row slips (3/17). Those must be caught by another
  validator or reported as caught only by the one named.
- **S-N3, should-fix: plant assertions must be relative.** Record each plant's flow once without the plant and
  require new views or new semantic facts relative to that baseline (`test_owner_state_plants.py:38–40`).

## 2. Oracle (REVIEW-S2-2, sol)

- **Blocking: an incomplete scan can authorise closing a check** (`driver.py:324`, `model.py:608`). A `BODY.PEEK[]`
  FETCH returning `('OK', [])` is recorded as `SCAN_RESULT accepted=True`. Record and validate the actual FETCH
  results (matching UID and body literal) before declaring a scan complete; require that evidence for closure; add
  the false-completion regression.

## 3. Production and oracle (REVIEW-S2-ASTRA-2, astra)

- **Blocking, production: RENAME lost its UIDVALIDITY recheck** (`mail/filing.py:74`). Removing body reads also
  removed the metadata-only UIDVALIDITY check on the mutation connection, so a folder recreated between enumeration
  and RENAME gets renamed while the committed context names the old UIDVALIDITY (R2 broken). Restore a metadata-only
  UIDVALIDITY check on the mutation connection before committing context; keep body fetching and MIME parsing
  removed. Tests: folder recreated between enumeration and RENAME, with successful storage and with failed result
  storage; RENAME's server reads stay no more than before stage 2 apart from that named check.
- **Should-fix, oracle: the destination-presence gate is RENAME-only** (`model.py:605`). For filing, a correlated
  complete scan plus a committed warning closes the check even when the destination is gone. Add that positive case
  beside the absent-destination RENAME negative case.

## Verification and report

- Local first; then the Linux capture once, the strict re-pin, and Control base, Control Mail (every job under 45
  minutes) and Control boundary each passing twice on the finished head. Rerun the STORAGE-S2 table (zero growth).
- **Waiting on CI:** wait with one blocking shell call per run, for example
  `gh run watch <id> --exit-status --interval 60`, or one shell loop over the named runs. Never poll `gh run view`
  one turn at a time; every turn re-sends the long context and costs allowance.
- Do not run your own review; the package lead reruns the three reviewers, scoped to these findings.
- Add a "Stage 2, fixes round 2" section to `REPORT.md`: per item the change and its test or plant, the validator
  table as it now stands, the fault-free group changes, the ledger counts and size, the storage table, the run
  count. Mark claims run, read or assumed.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/19b-owner-state`. Commit in small steps and push this branch; draft PR
  #26 targets `pkg/19-mail`. Never merge, never push to `main` or `pkg/19-mail`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- No real accounts, addresses, personal names or mail-provider names; tests use synthetic accounts only.
- Never commit the full gap list; the committed ledger stays compact (format 3, under about 1 MB).
- No change to what any tool asks or does, its approval input, `question` text or binding.
- Never rewrite immutable history; stop and report if a fix would need it, or if journal growth per operation
  would exceed about 1 KB.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.
- Stop after this round. Do not start stage 3.
