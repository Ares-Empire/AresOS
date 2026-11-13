# 19b stage 3: the last storage round, with a fixed design (lead decision D, 2026-11-11 02:50)

Three stage-3 rounds stopped at the storage rule (`REPORT.md`, the three "Stage 3 … stop" sections; candidates
`STORAGE-S3-CANDIDATE.patch`, `STORAGE-S3-REDESIGN.patch`, `STORAGE-S3-TOMBSTONE.patch`). Each round invented new
bulk, so this brief **fixes the design** rather than leaving it open. This is the last storage round: if it doesn't
pass, stop with the table and don't propose another redesign; the lead takes the table to the owner. Read
`briefs/19b-owner-state.md`, `briefs/19b-on-mail.md` (the note wins), every `briefs/19b-s*.md`, with
`briefs/19b-s3-start.md`, `-s3-redesign.md`, `-s3-tombstone.md` and this file last, and the three stop sections.
Where this file differs from the earlier stage-3 briefs, this file wins.

## 1. Allowed projection record kinds, and no others

- **context** (committed before a mutation);
- **resolution**;
- **check-open** and **check-result**, only for checks that can produce an owner warning (round 27);
- **acknowledgement**;
- **tombstone**.

No readable full-event copy (remove `owner_source.py`'s approach). Warning text is generated from codes plus the
stored facts: identities, folder names, recipient count and recipient hashes, state codes. The facts must survive
SQLite being unreadable; the exact wording needn't (R1 allows memory or SQLite to add wording).

## 2. The archive retires in one run

Any verification the archive needs (for example the Sent-copy re-check) completes and commits **before its cutoff,
as part of the archive run's own record**, never as new records on the operation being retired. Retiring a finished,
acknowledged operation therefore takes exactly one archive run. Needing a second run is a bug, not a measurement
detail; test it.

## 3. Tombstone

- Fields: operation id, final state code, acknowledged warning ids, one chain hash that binds the hash of the
  operation's entry in the existing hash-checked archive export.
- Compact encoding; target **≤ 128 bytes including framing** for an operation with up to two warnings. Report the
  measured size.

## 4. Measurement

- After **one** archive run: permanent bytes per operation = its tombstone + the archive run's own record shared
  across 100 operations. Also report the archive run's record per run.
- While-open bytes as before.
- The same table as before (extra bytes against `7b0e9a05`, both numbers, every kept file counted), with the reason
  for every record.

## 5. Keep what works

The export is re-read before retiring; uncovered history is refused; an older backup can't resurrect an acknowledged
warning or redo finished work; a tampered or missing export entry fails loudly; the live projection is bounded by open
work (1 and 1,001 finished, acknowledged sends leave it the same size); an entry with an unacknowledged warning, an
open check or unresolved work is never retired; the projection agrees with the SQLite view in every flow and every
sweep mode, and the SQLite-read fallback shows every owner-visible fact.

## 6. Decide by the figures

- If send **and** permanent delete are permanently **≤ 1 KB**, carry on through stage 3 to the end without asking:
  everything the brief, `briefs/19b-s3-start.md` (D3, D4), `-s3-redesign.md` and `-s3-tombstone.md` require, including
  the **six restore comparisons, which must pass** (not known gaps), an empty known-gap list, and Control base, Mail
  and boundary each passing twice on the finished head.
- If not, stop after committing and pushing the measurement and the table. Don't propose another redesign.

## Runs and rules

Local first; wait on CI with one blocking shell call per run (`gh run watch <id> --exit-status --interval 60`, or
one loop over the named runs), never polling run status one turn at a time; every Mail job under about 35 minutes;
no own stage review. The "Rules for this run" of `briefs/19b-s3-start.md` apply unchanged. Stop after stage 3.
