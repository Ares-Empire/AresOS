# Brief 20-restore-lock-followups: the owner oracle's three wrong lock expectations

Lead: `linux-tools`, 2026-11-16. Written by a Claude agent on Fable: it decides store and restore semantics, and each
claim was checked against the code first. Source: `docs/control/TOOLS-HANDOFF.md`, "Restore lock merged", "Yours,
both pre-existing", and `reviews/20-restore-lock/REVIEW-REPIN-3.md`. Evidence, commands and outputs: the findings
in `reviews/20-restore-lock-followups/PROGRESS.md`; the reproduction is `repro.py` there.

**Outcome.** In every item the store is right and the oracle's model is wrong. No production code changes: about
20 lines in `control/owner_state_oracle/`, tests, and one re-pin. Item 3 was not handed over: it is "C2's mirror of
C5" in `KNOWN-GAPS.md`, and it has its own cause.

**Words.** *Single* mode fails one disk call (a fault point) once; *persistent* mode fails it and every later one,
like a full disk. A *commit marker* is the journal line that ends a write; the *head* is the newest write applied
in SQLite.

## The lead's decisions (2026-11-16)

- Items 1, 2 and 3: fix the model, as recommended. The store stays as it is.
- **Item 3 goes in the same package and the same re-pin**, not past the cut line: item 1's rule is what keeps
  points 74 and 75 locked once the decoder says "behind", so the two belong together, and one re-pin costs less
  than two. Build order: items 1 and 2 in one commit, item 3 in the next, with the local sample run after each, so
  the classification can tell their keys apart.
- The findings are in `reviews/20-restore-lock-followups/PROGRESS.md` (not `FINDINGS.md`); `repro.py` stays there
  as evidence.
- **The write latch (`G22-latch`)** goes to the queue as its own package (it changes replies the owner sees).
- Next: a fresh brief review, then one builder on this branch, then a fresh review of the code and a second agent
  that re-checks the re-pin's classification with its own scripts. Brief, build and re-pin go to `main` in one PR.

## Item 1 (C5): a confirm that fails at its last disk sync

**Today.** The restore flow's last fault point is 75, the sync of the final commit marker (`storage.py:562`, from
`_finish`, `storage.py:597`).
- The confirm is answered `storage_limit` and never reaches `self.locked = False` (`storage.py:940-942`). The
  running service keeps the lock and refuses every write until it restarts (`storage.py:565`, `769-777`).
- Single mode: the marker is rolled back (`storage.py:566-567`). The oracle decodes "locked". Both agree.
- Persistent mode: the rollback fails too, so the marker's bytes stay. The oracle decodes "confirmed"
  (`records.py:202-203`); the store says locked. That is C5: 26 keys at `restore/persistent/75/0`, 14 at its pair
  case `restore/single/75/76`.
- A restart ends both modes the same: unlocked, new generation. From point 26 on the confirm's last event is
  staged in SQLite, and startup finishes it (`storage.py:235-240`).

**The store is right.** For the owner both modes are one situation: his confirm failed on a full disk. The model's
two answers differ only in whether the fault injector also failed the rollback. A marker whose sync failed may not
be on the disk, so the service keeps the lock: nothing stale is shown, every app call stays refused, and the
restart settles it from the real bytes.

**Decision: fix the model.** A running service reports the lock it holds: the decoded lock, or it has seen a
`control_restore_confirm` on a locked store meet a storage fault since it started.
**Alternative: change the store** to release the lock when the marker's bytes stayed. Cost: a new branch on the
failure path of a safety mechanism, trusting bytes whose sync failed; new fault sites and changed replies; a
security review. The owner gains nothing: every write stays refused until the restart either way.

**Change.**
- `driver.py`, `snapshot()`, beside the startup rule (line 59): apply the rule, read from the script's fault trace.
  In the sweep every such fault aborts the confirm (140 of 140 cases).
- The record carries it as a field, like `startup_sequence`, so `consistency_errors` (`records.py:79-82`) and the
  perturbation recompute (`perturb.py:483-485`) use one formula. List the field in `RECORD_EXCLUSIONS`.
- It must already hold when the failed confirm's own reply is captured: that reply says locked. A restart ends
  it: one `Driver.restarted()` replaces the attribute pokes at `test_owner_state_sweep.py:227-228`.

**Tests.**
- `control/tests/test_restore_batches.py`, no oracle: the last sync fails, with a working and with a failing
  rollback. Both: `storage_limit`, lock kept, `control_pending` says `restore_required: true`; after a restart
  unlocked with the new generation. Mutation caught: `self.locked = False` moved into a `finally`.
- `control/mail_tests/test_owner_state_sweep.py`: the restore flow's last fault point (from the clean run, not
  hard-coded), persistent, live and crash, and its pair case: no recorded key ends in `.restore-lock` or `.status`,
  none is `recovery-holds`. Mutations caught: the rule removed; the rule kept on after the restart.
- `control/tests/test_owner_state_oracle.py`: a record with the rule on and `locked` false reports
  `unjustified-lock` (mutation caught: the term dropped from `records.py:81`). The alteration suite keeps `slipped=0`.

## Item 2: the log view under the lock

**Today.** `control_log` is refused under the lock (`engine.py:575-576`). The owner's `aresos log` prints
`restore_required`, "Older log refused; owner must confirm restore before any app access", and an envelope with
`restore_required: true`. The oracle reads a view's lock from its data page (`compare.py:239-240`). A refused read
has none, and the stand-in page (`compare.py:121`) carries no lock, so the oracle records "not locked".
`control_log`'s data never has the field (`engine.py:600-625`): the check fails at every locked case and passes only
where nothing is locked. 16,383 pinned keys: 15,982 in `crash-locked` (6,375 single-fault cases, 9,514 pair cases,
93 in the restore flow) and 401 in the restore flow's live phases.

**Decision: the store is right, fix the model.** That one reply tells the owner about the lock twice. A refused
read's stand-in page says locked exactly when the refusal is `restore_required` (`compare.py:121`, one field).
`response.control_log.status` still catches a wrong refusal.
**Alternative: answer `control_log` under the lock**, with the field. Cost: it widens the lock's allow-list (a
security review), shows the older database's log as today's, and changes the log's reply at every locked case: a
large re-pin. `control/README.md:176-178` says all app calls are refused.

**Tests.** `test_owner_state_oracle.py`, beside `test_pages_drain_and_cannot_loop`: a `restore_required` refusal
gives a page that says locked, a `storage_limit` refusal one that does not, and an answered page passes through
unchanged. Mutations caught: the field dropped; the field set for every refusal. Sweep: the `crash-locked` case
`cancel`, point 2, persistent, records no `aresos log.restore-lock`.

## Item 3 (the mirror): an unfinished write is not a restore

**Today.** Outside the restore flow the oracle says locked while the store is not: 644 single-fault cases (161
`exhausted`, 483 `live-restored`), 903 pair cases, and the replies those calls built before a crash. 15,030
lock-view keys. The decoder locks when the head *differs* from the last commit marker (`records.py:203`; also
`records.py:79`, `perturb.py:484`). The store locks only when the head is *behind* it (`storage.py:208`,
`control/README.md:176-178`). A head *ahead* is the service's own write that failed at its marker: startup
finishes it (`storage.py:241-250`) and there is nothing to confirm. A census of 21,730 cases (every fault
point of all 34 flows, both modes) agrees: the model says locked and the store does not in 483, each with the head
ahead, and none is locked after a restart.

**Decision: the store is right, fix the model.** The owner needs a restart there, not a confirm. "Behind", not
"differs", at the three places. Item 1's rule then keeps the restore flow's points 74 and 75 locked; today they are
right by accident.
**Alternative: leave it pinned.** Cost: 15,030 known-false keys stay, and item 1 rests on that accident.
**Cut line.** Items 1 and 2 alone only close keys (16,423) and change no other. Item 3 also changes row keys
(below). For the smallest step, item 3 becomes its own package with its own re-pin.

**Tests.** `test_owner_state_oracle.py`, with its `disk()` helper: head ahead decodes unlocked (today locked), head
behind locked, head equal unlocked. Mutations caught: `!=` restored; `<=`. Sweep: `cancel`'s last fault point,
single, live, records no key ending in `.restore-lock`.

## Re-pin (same PR)

No fault site moves and no reply changes. But pinned gaps close, so the strict sweep fails with "Unexpected pass"
until the pin is renewed. Dispatch `control-owner-oracle.yml` on the branch: one capture, then one proof run that
must be green; at most 3 dispatches, about 2.5 h each. First run the findings' local sample (minutes) and
dispatch only if it matches. Classify every difference and add a section to `KNOWN-GAPS.md`, as its last one did.

**Must change.**
- Item 2: the 16,383 `aresos log.restore-lock` keys close.
- Item 1: 26 + 14 keys close (25 lock views, 12 read statuses, 3 `recovery-holds`).
- Item 3, only at cases where the old decoder said locked with the head ahead: the 15,030 lock-view keys close.
  Read statuses and `recovery-holds` close or change their expected set. Row and notice keys close, change or
  appear: the model stops expecting "unknown: restored" rows and expects the last committed rows, while the store
  shows the write it applied. That last disagreement stays pinned; deciding it is out of scope.
- **Afterwards no key in the full list ends in `.restore-lock`** (31,438 today).

**Must not change.** Anything else is drift from another merge: stop and report to the lead.
- Every flow's clean-run point count (capture 43722918063's). No point starts to fail.
- Any key outside those classes. With items 1 and 2 alone, the other 2,605,649 keys stay byte for byte.
- The hidden-rows keys under the lock (M14; brief 20-restore-lock, R1), and the 377 contract, `G22-*` and
  channel keys.

## Out of scope

- Showing other apps' rows, or the log, during the lock: R1's decision stands.
- **The write latch (`G22-latch`, already pinned).** After a failed write the service repeats its first storage
  refusal until it restarts. So after C5 the owner's second confirm says "Disk full … free storage … before
  retrying" even with space free, and no reply names the restart. Worth its own package; it changes replies.

## Rules

- Never merge, never push to `main`, never force-push, never `--no-verify`. Public repo: no personal data,
  repo-relative paths only. Stop processes only by PID. Commits before the capture carry `[skip ci]`.
- Builder: one agent on Opus or Codex `gpt-6.1-sol` (narrow; the trace names every line). Then a fresh reviewer,
  and a second fresh agent that re-checks the re-pin's classification with its own scripts.

**Questions for the owner:** none. These are technical calls, and nothing the owner sees changes.
