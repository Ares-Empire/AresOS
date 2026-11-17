# Recheck 1: 20-restore-lock-followups, the final round (PR #95, `5dd77095..757cabc2`)

Reviewer: a fresh Claude agent on Opus 5.5, 2026-11-17. I did not build this package or any earlier round of it.
I worked read-only on tracked files; this file is the only one I wrote in the repo.

**Verdict in one line:** the merge is clean, the shared `records.decoded_lock` gives the same lock as the three
inline formulas on every input those callers can receive, nit 1's test catches what it claims, the 14 probes still
fail their tests, the docs say what the code and the runs show, and the proof is green on `305ebcbd`. Four nits,
none of them for this PR.

## Range

- `5dd77095`: merge of main at `d0b91522`.
- `305ebcbd`: the nits (`records.py`, `perturb.py`, `driver.py`, `test_owner_state_oracle.py`, `KNOWN-GAPS.md`,
  `mutations.{py,json}`).
- `757cabc2` (`[skip ci]`): PROGRESS's final-round section and the `KNOWN-GAPS.md` paragraphs on the final proof
  and on the ledger job.

## What I read

`AGENTS.md`; `PROGRESS.md` (final round, and the build section for context); `REVIEW-1.md`;
`CLASSIFICATION-CHECK.md`; `git diff 5dd77095 305ebcbd`; the old formulas via `git show 5dd77095:<path>`; `records.py`
(`decoded_lock`, `consistency_errors`, `decode`); `perturb.py` (`mutations`, `RECORD_EXCLUSIONS`,
`coherent_change`, `check`); the sweep's harness check (`test_owner_state_sweep.py:216-223`); `gaps.verify`;
`storage.py:915-945`; `.github/workflows/control-owner-oracle.yml`.

## What I ran

All of it ran as an ordinary user, with no container, root or mount. I ran no rpm-ostree, bootc or ostree command,
no `os/tests` module, and dispatched no workflow. My scripts and the code copies live in my scratch directory and are
not committed. Every mutation went into a `git archive` export of `305ebcbd` there, never into the worktree. At the end
`git status` was clean.

- From the worktree root, `cd control && PYTHONPATH=.:tests:mail_tests python3 -m unittest test_owner_state_oracle
  test_restore_batches`: **128 OK** (124 + 4) in 42 s.
- The sweep module's 11 unit tests (all but `test_all_flows_all_storage_modes_independent_views`), from the repo root
  with `PYTHONPATH=control:control/mail_tests` and `mutations.py`'s managed-settings stand-in: **11 OK** in 8.8 s.
- In the export, those 11 plus `test_owner_state_quiet`, `_regressions`, `_s2_effects`, `_plants` and `_contracts`:
  **37 OK**.
- `PYTHONDONTWRITEBYTECODE=1 python3 reviews/20-restore-lock-followups/mutations.py`, run in the export so the
  committed `mutations.json` stayed untouched: **14 rejected, every baseline passed** (13 s).
- An exhaustive old-against-new comparison of the lock formulas (2,232,720 inputs), my own probes (table in check 3),
  and two direct `decode` calls (check 2).
- `gh`: `run view 43972005458 --json conclusion,headSha,status,attempt,event,headBranch,workflowName,jobs`; the job
  logs of 43972005458 and 43919136534 (one call each); the commit's check runs (2 pages) and its workflow runs (1).
  That is 6 API calls in all. I did not download the 53 lists.
- One read-only query of board item #337.

## Checks

**1. The merge `5dd77095`: no finding.**
- `git merge-tree --write-tree 798036e0 d0b91522` gives `3c425d86`, which is the merge commit's own tree. So it is a
  plain merge with no conflict resolution and no edits.
- `git diff 5dd77095^1 5dd77095` touches nothing under `control/owner_state_oracle`, `control/mail_tests` or
  `reviews/19b-owner-state`. That covers both pin files, `KNOWN-GAPS.json` and `KNOWN-GAPS.md`.
- Under `control/aresos_control` it brings in exactly the five files PROGRESS names: `boundary_policy.py`, `hooks.py`,
  `usage.py`, `chrome/adapter.py` and `chrome/qualification.py`.

**2. `decoded_lock` against the three formulas it replaced: no finding (one nit, finding 1).**
- **Exhaustive comparison.** I copied the three old expressions verbatim from `5dd77095` and compared each with the
  new helper as its caller now calls it. The inputs:
  - `restore_pending` absent, `None`, `False`, `True`, `0`, `1`, `''` or `'x'`;
  - zero to three fences, with sequences 0 to 3 (duplicates allowed), hashes `a` or `b`, or no hash;
  - `committed` any subset of {1..4} with up to three members;
  - `head` `None`, or a pair of sequence 0 to 5 and hash `a`, `b`, `''` or `None`.
- **Result** (the helper always returns a `bool`):
  - `consistency_errors`: no difference at all, duplicates and hashless fences included. Its "exact semantics" claim
    holds.
  - `decode`: the only difference is a fence without a hash at the head's sequence, where the old code raised
    `KeyError` and the new one does not. The values never differed.
  - The recompute: the only difference is duplicate sequences (the old code took the first fence, the new one takes
    the last).
- **Claim 1: a hashless fence cannot reach the lock in `decode`.** True. `decode` reads `value['hash']` in its
  hash-chain check (`records.py:178`) before a fence enters the map. On real journals, a first fence without a hash
  and a second fence without one both raise `KeyError: 'hash'` there. That is the hash-chain line, though not its
  `ValueError` message.
- **Claim 2: two fences with one sequence cannot occur.** True. `decode` refuses them: a duplicated sequence 1 raised
  `ValueError: Nonconsecutive independent record` (`records.py:180-181`). `coherent_change` rebuilds a fence only as
  `{**fence, ...}` or `dict(fence)`, so `seq` is kept. Its other inputs are decoded records, or hand-built test
  records with unique sequences (`test_owner_state_fixes_s2.py:177-185`).
- I found two more on-paper differences, both unreachable (finding 1).

**3. Nit 1's test fails without the recompute's interrupted-confirm term: no finding (one nit, finding 2).** These
are my own probes, separate from `mutations.py`:

| Probe (in the export) | `test_interrupted_confirm_is_a_term_of_the_lock` |
|---|---|
| ` or service_lock(changed)` dropped | FAIL, subtest `recompute=True, interrupted=True`: `False is not True` |
| cut to the startup rule, written differently from the builder's (`bool(unprepared_fences and min(...) <= startup_sequence)`) | FAIL, the same subtest |
| `service_lock` loses `or record.interrupted_confirm` | FAIL, subtests `interrupted=True, locked=False` and `locked=True` |

The test's input, `history(2, 2, 2)`, decodes unlocked with no unprepared fences. So only the interrupted-confirm term
can make the recompute say locked, and the test does exercise that term.

**4. `mutations.py`: no finding.**
- There are 14 probes: 8 for item 1, 2 for item 2, 2 for item 3 (`decoded-lock-differs`, `behind-or-equal`) and 2 for
  the recompute term.
- All are rejected with the same failing tests and assertion lines as the committed `mutations.json`. Only the
  timings differ.
- `item3-decoded-lock-differs` fails the oracle test (`head='ahead'`) and the sweep test (`cancel/single/69/…`).
- **Do the replaced per-caller probes still have cover?** I put an `!=`-style lock back at one caller at a time,
  bypassing the helper (`consistency_errors`, `decode` and the recompute, each on its own).
  `test_only_a_head_behind_the_last_marker_is_a_restore` fails each time at `head='ahead'`:
  - `consistency_errors`: `unjustified-lock unexpectedly found`;
  - `decode`: `(3, 2, True) != (3, 2, False)`;
  - the recompute: `True is not False`.
- So the test still checks every caller, and the one helper probe covers the shared rule. Together they cover what
  the old three probes did.

**5. Docstring and `KNOWN-GAPS.md`: no finding.**
- `driver.interrupted_confirm` now says what the harness asserts: no faulted confirm on a locked store is answered
  `ok` (`test_owner_state_sweep.py:219-223`). A confirm that released its lock and then failed shows as a lock gap
  through the lock-view comparisons, which is REVIEW-1's wording.
- The other `crash-locked` keys: 544,611 + 190 = 544,801 in 11 matrix rows, and the M14 hidden rows are among the row
  keys. This matches CLASSIFICATION-CHECK nit 2.
- N7's 544 `crash-restart` keys are the failed call's own reply, built before the crash, and the views read after the
  restart changed only by alias numbers. This matches CLASSIFICATION-CHECK nit 1 and its section on `crash-restart`
  at H.
- Board item #337 exists. It is open, topic `tools`, and its text names N7, PR 95, the 6,949 keys and "queue item 17".
- The ledger paragraph's `--init` explanation matches `.github/workflows/control-owner-oracle.yml:24-26`.
- PROGRESS's path-order note checks out: `control/tests/support.py` and `control/mail_tests/support.py` both exist,
  and only the first defines `EngineCase`, which `test_restore_batches.py:14` imports.

**6. Proof run 43972005458: no finding.**
- `gh run view`: `conclusion: success`, `headSha: 305ebcbd…`, attempt 1, `workflow_dispatch` on
  `briefs/20-restore-lock-followups`.
- All **61 of 61 jobs passed**: ledger 1, sweep 24, onboarding 24, alterations 12. Since all 61 ran, `ledger_only`
  was false.
- From its logs:
  - All 34 flows' clean-run point counts equal 43919136534's (`restore` 76, `cancel` 70, `onboarding` 2,610).
  - The alteration jobs log 110 scenario lines with 2,080,049 alterations, all `slipped=0`.
  - The ledger's `test_paged_committed_pending_through_every_installed_channel` and
    `test_every_pinned_gap_belongs_to_an_executed_suite` are `ok`. The first was `ERROR` in 43919136534.
- `gaps.verify` compares every owned group in both directions (`Unlisted gap`, `Unexpected pass`, `Known gap
  changed`). So the green strict shards are themselves the check against the pin.
- PROGRESS's "49 of 49" PR checks counts check *names*. The commit has 77 PR job runs from 6 workflows under 49
  distinct names, because the long Chrome qualification names are truncated. All 77 succeeded.

## Findings

1. **nit: two more inputs where the old and new lock formulas differ, both unreachable. No action.**
   - (a) **Evaluation order.** The old `consistency_errors` and the old recompute unpacked `head` before they checked
     `restore_pending` and the fences. The helper unpacks it only when both checks pass. A head that is not a pair
     (for example `(1,)`) therefore raised `ValueError` before; now it returns `True` when `restore_pending` is set, or
     `False` when there are no fences.
   - (b) **The recompute's fence map.** The recompute now builds the map over every fence. A fence without `seq`
     after the head's match now raises, where the old `next(...)` stopped at the match.
   - **Why neither can occur:**
     - `head` is only ever `SELECT seq,hash … fetchone()` (a pair or `None`), `coherent_change`'s own pair, or a test's
       pair.
     - `RECORD_EXCLUSIONS` keeps the alteration suite off `head`, and `snapshot_mutations` doesn't touch it.
     - Decoded fences always carry `seq`, and the recompute only sees those.
2. **nit: the recompute itself is not pinned by any unit test.** Nit 1's subtest sets the input lock to the value it
   expects (`record.interrupted_confirm = record.locked = interrupted`), and the item-3 test also feeds `decode`'s
   correct lock. So neither can tell a recompute from a copy.
   - Replacing the assignment `changed.locked = decoded_lock(...) or service_lock(changed)` with `pass` passes the
     oracle module (124), `test_owner_state_fixes_s2` (26) and the 37 Mail tests.
   - This was already so before this round, and today it moves no key. Coherent changes keep the head hash in step,
     and the corpus has no restore scenario (REVIEW-1 finding 1).
   - When this test is next touched, giving the recompute subtest the opposite input lock (`record.locked = not
     interrupted`) would pin it.
3. **nit: `decoded_lock`'s other terms have no unit test.** In the export, each of these passes the oracle module
   (124) and the 37 Mail tests:
   - dropping the `restore_pending` term;
   - dropping the head-hash comparison;
   - making a missing head unlocked.

   The three inline formulas had the same gap, so nothing was lost here. Now that the formula is one function, a
   table test of it would pin every term in about 10 lines. `restore_pending` is written only by restores of more than
   32 changes (`storage.py:925`, `:933`). I did not check whether any sweep case reaches one, or a store with fences
   and no head row.
4. **nit (wording only): PROGRESS's "49 of 49" counts check names, not job runs.** There are 77 runs, all green.
   Nothing to change unless the count is reused somewhere that matters.

## Not checked

- The local sample (`restore`/`cancel` points, byte-identical 1,048 entries with and without the nits): not re-run.
  Check 2's comparison and the green strict proof cover the same ground.
- The byte-for-byte reproduction of the pin from the 53 lists: not re-downloaded (see check 6 for why the green
  strict shards suffice).
- The alteration suite locally.

SAFE
