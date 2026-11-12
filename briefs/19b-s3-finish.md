# 19b stage 3: apply the final storage candidate and finish (lead decision, 2026-11-11 04:55)

The final storage round (`reviews/19b-owner-state/STORAGE-S3-FINAL.md`) stopped because a three-recipient send keeps
1,334 permanent bytes per operation (one recipient: 952; delete: 625). The table has gone to the owner, and the lead
recommends accepting it. **Don't wait for that answer.** Apply `STORAGE-S3-FINAL.patch` and finish stage 3 on it.
Nothing merges until the owner answers; if he says no, a storage round follows on top of this work. Read
`briefs/19b-owner-state.md`, `briefs/19b-on-mail.md` (the note wins), every `briefs/19b-s*.md` with
`briefs/19b-s3-final-storage.md` and this file last, and `STORAGE-S3-FINAL.md`.

## What to do

1. **Apply `STORAGE-S3-FINAL.patch`** (the design fixed in `briefs/19b-s3-final-storage.md`: the five record kinds
   plus tombstones, one-run archive, compact tombstones). Keep the storage figures as measured; don't redesign. If
   a fix below changes the per-operation bytes, re-measure with `STORAGE-S3-FINAL-HARNESS.py` and report the new
   table (no stop: the owner decides on the figures).
2. **First-write full-disk gap** (`STORAGE-S3-FIRST-WRITE.py`). This falls under D3; it isn't an owner question.
   Reserve space before the first maintenance journal write, so the background warning is always committed or the
   write never starts. On a failing (not full) disk, keep a committed generic warning. Turn
   `STORAGE-S3-FIRST-WRITE.py` into a regression test that fails today and passes after the fix.
3. **Finish stage 3**, everything the brief and `briefs/19b-s3-start.md`, `-s3-redesign.md`, `-s3-tombstone.md`
   and `-s3-final-storage.md` require:
   - the full every-fault-mode comparison (single, persistent, cleanup pairs, crash and restart, space restored) in
     every flow, with the projection agreeing with the SQLite view and the SQLite-read fallback showing every
     owner-visible fact;
   - the complete restore fault sweep, including the six restore comparisons, which must pass (not known gaps),
     and the 1,000/10,000 restore batch regression;
   - one read path; removal of what the projection makes redundant (in-memory sole carriers, stored refusals,
     startup snapshots); D3 and D4 with their tests;
   - **an empty known-gap list** at the end;
   - all alteration controls and the oracle self-tests passing;
   - Control base, Control Mail (every job under about 35 minutes) and Control boundary each passing twice on the
     finished head.
4. **Report** in `REPORT.md`: what was built and removed, the projection format and fallback reads, the lifecycle as
   built, the final coverage matrix, the removed-test mapping, the storage table, every change to `warnings.py` and
   `paging.py` (what, why, how Chrome follows), JUDGMENT-CALLs and PLAN-GAPs, and the run count. Mark claims run,
   read or assumed.

## Runs and rules

Local first; wait on CI with one blocking shell call per run (`gh run watch <id> --exit-status --interval 60`, or
one loop over the named runs), never polling run status one turn at a time; no own stage review. The "Rules for this
run" of `briefs/19b-s3-start.md` apply, except that the storage stop rule is replaced by item 1 above for this round
(re-measure and report; don't stop). The other stop rules (immutable history rewrite, any change to what a tool asks
or does) still apply. Stop after stage 3.

## Owner decision, 2026-11-11 (board #176)

The owner accepted the storage figures of `STORAGE-S3-FINAL.md` ("Yes, accept"): about 0.95 KB per sent mail kept
permanently, +0.19 KB per extra recipient, 0.6 KB per permanent delete, 0.9 KB per move. The candidate stands. If a
later fix pushes any figure clearly above this table (more than about 10%), report it; otherwise there is no further
storage stop. Record this answer with its date in the stage-3 report.
