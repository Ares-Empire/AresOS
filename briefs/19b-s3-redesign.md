# 19b stage 3: projection redesign round (lead decision, 2026-11-11 01:40)

Stage 3 stopped at the storage rule (`REPORT.md`, "Stage 3 — storage gate stop"; `STORAGE-S3.json`): the candidate
projection added 7,944 bytes per send and 3,212 per delete, mostly from one framed record per journal commit
(259 bytes of framing each) plus full owner-row deltas. The lead chose one redesign round. Read
`briefs/19b-owner-state.md`, `briefs/19b-on-mail.md` (the note wins), every `briefs/19b-s*.md`, ending with
`briefs/19b-s3-start.md` (D3, D4 and its notes hold) and this file, plus the stage-3 stop section of `REPORT.md` and
`STORAGE-S3-CANDIDATE.patch` (the withdrawn candidate; reuse what fits).

## The redesign

- **A separate file** beside the independent journal (not inside the permanent journal, which is never trimmed).
- **Records only where owner-visible state changes:** the context before each mutation, resolutions,
  acknowledgements and tombstones, not one record per journal commit. Fold each record into an existing commit that
  lands before the effect, as stage 2 did; add no new transactions.
- **One chain hash per record**, no repeated format, sequence or predecessor fields beyond what integrity needs.
- **Identities, hashes and short state codes only**; no prose, approval text or full contexts (those stay in SQLite
  and the journal).

## Conditions (all required)

1. **Two numbers per operation.** Measure, for send, move, permanent delete, a free change and a 25 MiB send:
   (a) the bytes while the operation is open, and (b) the bytes that stay **permanently** after it finishes and its
   warnings are acknowledged. (b) counts every copy kept anywhere: the permanent journal, the projection file and
   any archive, export or history file that is kept. Archiving that only moves records into another kept file is
   permanent growth. The 1 KB limit applies to (b), measured against `7b0e9a05`.
2. **Archiving really removes.** Test that finished, acknowledged entries leave the projection, and that its size
   depends only on open work (for example: 1,000 finished, acknowledged sends leave it no bigger than one). An entry
   with an unacknowledged warning, an open check or unresolved work is never archived or dropped.
3. **R1 still holds.** Everything the owner must learn stays computable from the committed records plus live
   checks; the projection is only a faster, SQLite-independent read path. Test that the projection's owner-visible
   set agrees with the SQLite view in every flow and every sweep mode (single, persistent, cleanup pairs, crash and
   restart, space restored), and that the SQLite-read fallback (persistent exhaustion with a failed rollback, then
   restart) shows every owner-visible fact from the projection.
4. **Decide by the figures.** If the permanent number (b) is under 1 KB for **both** send and permanent delete,
   continue stage 3 to the end without asking (as `briefs/19b-s3-start.md` and the brief's stage 3 describe: one read
   path, removal of what the projection makes redundant, archive/restore/expiry, D3, D4, an empty known-gap list,
   all Control workflows passing twice). If not, stop after committing and pushing the measurement, with the table
   (both numbers) and the reason for each record.

## Runs

Local first. Wait on CI with one blocking shell call per run (`gh run watch <id> --exit-status --interval 60`, or
one loop over the named runs); never poll run status one turn at a time. Keep every Mail job under about 35
minutes. Do not run your own stage review.

## Rules for this run

The "Rules for this run" of `briefs/19b-s3-start.md` apply unchanged (worktree and branch only, draft PR #26 against
`pkg/19-mail`, never merge or force-push, privacy check without `--no-verify`, no real accounts or provider names,
compact ledger, no change to what a tool asks or does, the stop rules, `Codex-Model: gpt-6.1-sol (xhigh)` trailer).
Stop after stage 3.
