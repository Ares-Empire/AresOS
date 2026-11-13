# 19b stage 1, fixes round 2

**Against:** the sol high fix check [`reviews/19b-owner-state/REVIEW-S1-2.md`](../reviews/19b-owner-state/REVIEW-S1-2.md)
(reviewed `55700bb2..9e6cc9e4`, CHANGES-NEEDED). Read `briefs/19b-owner-state.md`, `briefs/19b-on-mail.md` (the note
wins), `briefs/19b-s1-fixes.md` (its lead decisions D1–D3 and L1 still hold), `REVIEW-S1.md` and `REVIEW-S1-2.md`
first. This round fixes **stage 1 only** (oracle, comparison, ledger). Do not start stage 2. No production change.

## The pattern to close, not just the four cases

Both reviews found the same class: an expectation that a production-written value justifies by itself (a row flag,
a state, a removed row, a missing envelope). Close the class:

- **Field audit.** List every place where the expectation code (`model.py`, `context.py`, `compare.py`, `local.py`,
  `records.py`) reads a value production wrote: committed row fields and flags (`ack`, `notice`, `state`,
  `check_open`, stage outcomes, probe results, ...), the presence or absence of a row, reply fields, envelopes. For
  each, either validate it against the script, the server logs, the injected faults and the independently decoded
  commit order, or derive the obligation independently and treat the production value only as the thing compared.
  Put the complete list in the report as a table (field, where read, how validated, self-test), so the next review
  can check it line by line.
- **Obligations outlive production's own changes.** Once a transition justifies an owner-visible obligation (a
  warning, an expiry notice, a recovery notice, a qualification caveat), only a scripted, committed resolution that
  the evidence supports ends it. A flag flip, a row removal, an archive or a missing reply never does.

## Review findings to fix (numbers from REVIEW-S1-2.md)

1. **Blocking: expiry warnings depend on production flags** (`model.py:132`, `:397`). Derive the expiry-notice
   obligation from the validated expiry transition and keep it until a matching scripted, committed acknowledgement;
   protect it through archive removal. Tests: expired reservation committed with `notice=False`; `notice=True` then
   archive of the unacknowledged expired operation. Both must fail.
2. **Blocking: coherent context and command can violate the script** (`context.py:239`). Derive the permitted
   destination (from the script and independent role evidence) and the complete flag operation (every requested
   add and remove) from the script alone, then validate the context and the command against that. Tests: scripted
   delete-to-Trash with context and MOVE both targeting `Other`; requested `add=["\\Seen"], remove=[]` with context
   and command doing an empty removal. Both must fail.
3. **Should-fix: missing original envelopes escape** (`driver.py:269`). Identify public responses from their
   scripted request type (including the special `mail_account_add` request method), require their envelope, and
   count a missing envelope as a failure; exclude only explicitly named synthetic maintenance results. Test: the
   envelope removed from an original onboarding error reply with an expected live warning must fail.
4. **Should-fix: qualification reasons justify themselves** (`model.py:512`, `:525`). Validate committed probe
   outcomes against the correlated commands, replies, faults and commits before deriving qualification. Test: no
   fault, delivered successful EXPUNGE and empty-folder DELETE, committed cleanup `state="failed"` and a public
   account repeating that false reason must fail.

New production gaps these expose go into the compact ledger as exact entries, as in round 1. A fix must never make
the oracle accept less.

## Verification and report

- Local first (oracle self-tests, focused contracts and regressions, `python3 control/generate.py --check`,
  `git diff --check`), then the Linux capture for the new ledger, then the strict runs.
- At the finished head: Control base, Control Mail (every job within 45 minutes) and Control boundary each pass
  twice. Record run IDs, attempts and log lines.
- Do not run your own stage review; the package lead runs the fresh fix check.
- Add a "Stage 1, fixes round 2" section to `REPORT.md`: per finding the change and its test; the field-audit table;
  the new ledger counts and size and why they changed; the run count. Mark claims run, read or assumed.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/19b-owner-state`. Commit in small steps and push this branch; draft PR
  #26 targets `pkg/19-mail`. Never merge, never push to `main` or `pkg/19-mail`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- No real accounts, addresses, personal names or mail-provider names; tests use synthetic accounts only.
- Never commit the full gap list; the committed ledger stays compact (format 3, under about 1 MB).
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.
- Stop after this round. Do not start stage 2.
