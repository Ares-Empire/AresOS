# 19b stage 3: steering from the package lead (2026-11-11)

Read with `briefs/19b-owner-state.md`, `briefs/19b-on-mail.md` (the note wins) and every `briefs/19b-s*.md`. Stage 2
is closed (reviews `REVIEW-S2*.md`, all SAFE at `7b0e9a05`). Everything in the brief's stage 3 stands; this adds the
decisions and notes stage 3 needs.

## Decisions

- **D3 (G22-evidence), restated.** Reserve the space for an open check's evidence record through `space.py`'s
  reservations **before** the remote evidence is read, so the write that matters can't be refused for lack of space.
  If it still fails (a failing disk, not a full one), the check stays open (round 27) and carries a durable generic
  warning, already committed or computed from the open check ("evidence was seen but couldn't be recorded; check
  Trash"). A less specific warning is acceptable; a lost one is not. The oracle accepts exactly that.
- **D4, a call's own in-flight intent (lead decision, 2026-11-11).** R2 says an intent left `started` is a warning
  until resolved, and the brief says normal use is quiet. A normal save commits its export intent, builds its reply,
  then commits `saved`, so a literal reading would put a recovery notice in every normal save's own reply. Rule: a
  call's own in-flight intent is **not** a warning in that call's own reply **only if the resolving commit (for
  example `saved`) succeeded before the reply is returned**. If that commit fails or can't be confirmed, the same
  reply carries the warning, not a quiet success (round 27's rule). A crash before returning leaves the intent to
  every later view as a warning. In every other view the unresolved intent is a warning as usual. Production and the
  oracle both follow this. Pin both cases in tests: a fault on the resolving commit gives a warning in that call's
  own reply; a crash after the reply is built but before the resolving commit gives a warning in the next view. The
  `attachment_export`, `testapp_export` and `export_rollback` point-0 gaps close this way, not by a notice in normal
  replies.

## Notes for the build

- **The known-gap list ends empty.** Every remaining entry is a production gap for stage 3 (REVIEW-S2-ORACLE-4.md
  lists the fault-free ones with their evidence). Normal use stays quiet in every flow (the point-0 test).
- **Restore.** Remove round 29's restore sentence from the restore result and description once restore re-derives
  free-change checks, warnings and acknowledgements from the projection. Test the restore cases of the lifecycle.
- **Storage stop rule.** Measure with the `STORAGE-S2` harness extended to the projection: permanent journal **and**
  projection bytes and records per operation (send, move, delete, a free change, a 25 MiB send), before (`7b0e9a05`)
  and after. If either grows by more than about 1 KB per operation, stop and report the table with the reason per
  record. Fold projection entries into existing commits where they land before the effect, as stage 2 did.
- **Chrome follows `warnings.py` and `paging.py`.** Keep their public behaviour unless a rule needs a change, and list
  every change in the report (what, why, how Chrome should follow).
- **Oracle nit (optional, REVIEW-S2-ORACLE-4):** choose the `mail_account_add` completion commit by what it must
  contain (`mail:account:<id>` with `onboarded`), not by the absence of intent keys (`model.py:1489–1490`).
- **CI.** Keep every Mail job under about 35 minutes in both passes (rebalance shards by measured cost; never drop
  cases or raise the cap). Wait on CI with one blocking shell call per run (`gh run watch <id> --exit-status
  --interval 60`, or one loop over the named runs); never poll run status one turn at a time.
- Do not run your own stage review; the package lead runs the stage reviews.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/19b-owner-state`. Commit in small steps and push this branch; draft PR
  #26 targets `pkg/19-mail`. Never merge, never push to `main` or `pkg/19-mail`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- No real accounts, addresses, personal names or mail-provider names; tests use synthetic accounts only.
- Never commit the full gap list; the committed ledger stays compact (format 3, under about 1 MB).
- No change to what any tool asks or does, its approval input, `question` text or binding.
- Stop and report if a stage needs immutable history rewritten, a change to what a tool asks or does, or storage
  growth beyond about 1 KB per operation.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.
- Stop after stage 3.
