# 19b stage 2: fold the action context into existing commits (lead decision, 2026-11-10)

Stage 2 stopped at the brief's storage rule (`REPORT.md`, "Stage 2 closing stop"): the permanent journal grew by
+1,412 bytes per Mail send and +1,582 per permanent delete, apparently because each command commits its context in
its own transaction, and every transaction adds a fence and a commit marker. The lead chose one short fold round,
then a new measurement. Read `briefs/19b-owner-state.md`, `briefs/19b-on-mail.md` (the note wins),
`briefs/19b-s2-start.md` and the stage-2 sections of `REPORT.md` first. Everything there still holds.

## What to do

1. **Fold, keeping R2 exact.** Each operation's context must be durable before its first dispatch or mutation.
   Fold context into an existing commit only where that commit already lands before the mutation it covers (for
   example the reservation/submitting transaction, or a stage write that precedes the command). Where no existing
   commit lands in time, keep the separate context commit and name it in the report with the reason. Never commit
   context after a command, and never let a failed commit allow the command.
2. **Crash and failure tests at every write point**, for the folded and the unfolded paths: the context is committed
   before the command reaches the server (server log order against the commit), and a failed commit prevents the
   command. No change to what any tool asks or does, its approval input, `question` text or binding. Old records
   (the frozen pre-stage-2 store) stay readable and behave as before.
3. **Measure again** with the same `STORAGE-S2` harness (same five operations). Report in `REPORT.md` and
   `STORAGE-S2.json` a before/after table: permanent-journal bytes before stage 2 (`fda0d164`), after part B
   (`d87bc02d`) and after the fold, plus the **number of journal records per operation** at each of those three
   points, and the reason for every record the fold could not remove.
4. **Decide by the figures:**
   - If Mail send **and** permanent delete each grow by **under 1 KB** of permanent journal over `fda0d164`, continue
     stage 2 as planned: the Linux full capture (once, after the fold), the strict re-pin of the compact ledger, and
     Control base, Control Mail (every job under 45 minutes, aim about 35) and Control boundary each passing twice on
     the finished head. Then stop; the package lead runs the three stage reviews.
   - If either is still at or over 1 KB, **stop** after committing and pushing the fold and the new table with the
     reason per extra record. Do not run the Linux capture.

## Runs and reviews

Local checks first. Do not run your own stage review. Report the workflow run count.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in this worktree, on branch `pkg/19b-owner-state`. Commit in small steps and push this branch; draft PR
  #26 targets `pkg/19-mail`. Never merge, never push to `main` or `pkg/19-mail`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- No real accounts, addresses, personal names or mail-provider names; tests use synthetic accounts only.
- Never commit the full gap list; the committed ledger stays compact (format 3, under about 1 MB).
- Never rewrite immutable history; stop and report if the fold would need it.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.
- Stop after stage 2. Do not start stage 3.
