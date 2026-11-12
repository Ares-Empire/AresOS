# 19b stage 3: archive tombstones (lead decision C, 2026-11-11 02:30)

The redesign round stopped at the storage rule (`REPORT.md`, "Stage 3 — projection redesign round: storage stop";
`STORAGE-S3-REDESIGN.patch`): the live projection stays bounded, but archiving moved each operation's full projection
history into a kept `owner-history/` file, so the permanent growth was 2,751 bytes per send and 1,249 per permanent
delete. Read `briefs/19b-owner-state.md`, `briefs/19b-on-mail.md` (the note wins), every `briefs/19b-s*.md`, with
`briefs/19b-s3-start.md`, `briefs/19b-s3-redesign.md` and this file last, plus both stage-3 stop sections of
`REPORT.md` and the redesign patch (reuse what fits). Everything in the redesign brief holds except what this file
changes.

## The change

On archive, replace an operation's retired projection history with **one tombstone**: the operation's identity, its
final state code, the identities of its acknowledged warnings, and a chain hash that also binds the hash of that
operation's entry in the existing hash-checked archive export, so the tombstone points at the full record there.

## Conditions (all required)

1. **Archive only after the export is confirmed.** Retire an operation's history to a tombstone only after its full
   history is durably in the hash-checked archive export, verified by re-reading it. If the export can't be
   confirmed, keep the full history.
2. **Tests:**
   - restoring an older backup can't bring back an acknowledged warning or redo finished work;
   - a tampered or missing export entry makes the tombstone check fail loudly;
   - the live projection stays bounded by open work (as in the redesign round: 1 and 1,001 finished, acknowledged
     sends leave it the same size), and an entry with an unacknowledged warning, an open check or unresolved work is
     never archived.
3. **Measure and decide.** Report the same two-column table as the redesign round ((a) extra bytes while open,
   (b) extra permanent bytes after finish and archive, counting every kept file), against `7b0e9a05`, with the
   reason for every record. If (b) is under 1 KB for **both** send and permanent delete, carry on through stage 3
   to the end without asking, including the **restore reconciliation of the six failing comparisons** in the restore
   flow: those must pass and must not be recorded as known gaps. All of stage 3's requirements from the brief,
   `briefs/19b-s3-start.md` and `briefs/19b-s3-redesign.md` (R1 agreement in every flow and sweep mode, the SQLite-read
   fallback, one read path, removal of what the projection makes redundant, D3, D4, an empty known-gap list, all
   Control workflows passing twice) apply.
4. **If (b) is still at or over 1 KB** for send or permanent delete, stop after committing and pushing the
   measurement and the table.

## Runs and rules

As in `briefs/19b-s3-redesign.md` and `briefs/19b-s3-start.md`: local first; wait on CI with one blocking shell call
per run, never polling run status one turn at a time; every Mail job under about 35 minutes; no own stage review;
the "Rules for this run" of `briefs/19b-s3-start.md` apply unchanged. Stop after stage 3.
