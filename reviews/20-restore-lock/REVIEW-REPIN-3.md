# Package re-check 3: the re-pin (`065275ff..96bb1a03`, Claude Opus, 2026-11-15)

**SAFE.** Every difference between the previous pin (run 43137420989) and the new pin (capture 43722918063 on `065275ff`, commit `96bb1a03`) falls in the intended classes. The documented numbers hold, and the pin reproduces byte for byte. Nothing tells the owner something untrue outside the restore lock. No Mail or Chrome gap appears or changes except through A, B, E or the lock classes.

Scope: the re-pin only (`KNOWN-GAPS.json`, `KNOWN-GAPS.md`, `PROGRESS.md`). Code up to `065275ff` was reviewed elsewhere. All analysis used my own scripts. I read the builder's scripts only to learn the formats, and compared my alignment with the builder's map afterwards.

## Findings

None that need a fix.

## NOTEs

1. **The proof run is still open.** Dispatch 2 (run 43738332693 on `96bb1a03`) was *queued* when I checked. `KNOWN-GAPS.md` still says "Proof: pending" and `PROGRESS.md` says "PROOF-PENDING". Brief R2 step 6 requires this run to be green, with those placeholders filled in, before merge.
2. **D: "unchanged" is 98 of 100, not 100.** All 100 exhausted read-status gaps of `expiry` and `maintenance` are present at the aligned points, including the 82 (expiry 50, maintenance 32) that the trace capture had lost; 82 is right, not 83. But 2 of the 100 changed their expected set only. Both are C2 keys and are already counted in C2's 308:
   - `expiry/persistent/64→68/0/exhausted/response.control_pending.status`
   - `maintenance/persistent/61→61/0/exhausted/response.control_pending.status`

   Each still observes `storage_limit`, now against `["allowed","journal_incomplete"]` instead of `["restore_required"]`. Only the wording "present unchanged" (PROGRESS.md) and "0 differences" (KNOWN-GAPS.md, row D) is slightly too strong.
3. **E covers more than the 377 fixed keys.** 5,765 cleanup-free sweep keys at aligned points differ only by alias numbering (`filing_move` 5,724: `notice-head` 4,640, `page` 542, `complete` 542; `repair` 41 `lifecycle-proof`). Under colour refinement over alias and ID tokens, each old/new pair is isomorphic: a consistent renaming, no role change. They sit inside the table's "Unchanged 1,016,218", which is correct. Row E names only the fixed keys.
4. **The C3e / C5 / C1 split at the restore flow's last point.** The table counts only the *persistent* last point (75) as C5 (44 + 2 + 2). The single-mode last point goes to C3e (20 keys, part of the 76 "in the restore flow") and C1 (1 closed `control_pending.restore-lock`, part of the 238). My first split differed, but the sums agree exactly, so this is bookkeeping, not a gap.
5. **Pre-existing, unchanged:** in `crash-locked` the `aresos log.restore-lock` view still says "not locked" (expected `True`, observed `False`) at all 6,375 points outside the restore flow. It is the same at the pin. This is not part of this re-pin; mentioned only so nobody reads C1's 6,375 closed `control_pending.restore-lock` gaps as "every lock view now agrees".
6. **Hygiene outside this commit:** `briefs/20-restore-lock.md` (committed earlier on this branch, not in `96bb1a03`'s diff) has an absolute home path with a username at line 71 (the 19b worktree path). Older briefs on main have similar paths. The lead decides whether to scrub it before the PR, since the repo is public.

## What I checked, and how

`$S` = my scratch directory (path given in my reply). Scripts need about 1–3 GB of memory each. `lib.py` holds the loader and normalisers; `classes.py` holds my class rules. Run them in this order.

**1. Reproduction (item 5).**
- `regen.sh`: the commands from the KNOWN-GAPS.md section, into `$S/.work/`.
  - Merged 53 lists, no conflicts: 2,622,072 keys, all stage 3, zero R2, 1,997 groups.
  - Compact output is **byte-identical** to the committed `KNOWN-GAPS.json`: 921,711 bytes, SHA-256 `ee326914…291e68d`, as documented.
  - My regenerated full list is byte-identical to the builder's `43722918063-full.json`.
- `gh run download 43722918063` into `$S/dl/` (read-only): all 53 `owner-gaps-*.json.gz` are byte-identical to the builder's local capture. Hashes are in `$S/.work/artifact-sha256.txt`.
- The run's head is `065275ff` (workflow_dispatch, attempt 1). Jobs: ledger 1 and alterations 12 succeeded; sweep 24 and onboarding 24 failed, as documented.
- `regen_old.sh`: the old full ledger compacts byte-identically to the previous committed pin (`6bbcb02f…`, 1,966,234 keys, 2,010 groups).
- `numbers.py`:
  - Committed pin: format 3, 1,997 groups, counts sum to 2,622,072, stage 3 only, no R2 row.
  - New pin: 1,155,439 cleanup-free / 1,466,256 pair / 377 fixed keys. Previous pin: 1,052,284 / 913,573 / 377. All as in KNOWN-GAPS.md.
- Hygiene: no added line in `git diff 96bb1a03^ 96bb1a03`, and none of the three files at `96bb1a03`, contains `/Users/`, `/home/`, `/private/`, the username or the owner's name. The only hits are on removed lines: the old PROGRESS.md handover's worktree paths, now gone.

**2. Point alignment (my own).**
- `index.py` turns each full list into a pickle: old, new, and the trace capture as "mid".
- `points.py`: the trace capture and this capture have identical failing point sets in all 32 flows (10,247 points). The pin has 9,822.
- `align_own.py`: `difflib` per flow over cleanup-free signatures, leaving out `crash-locked` and the three lock reads' statuses.
  - 31 flows align with inserts only.
  - My matched pairs and inserted points equal the builder's `map-pin-new.json` exactly in those 31 flows.
- `diff0.py`: the restore flow (all lock-sensitive views dropped) aligns as 67 matches plus 4 inserts (57–60), with the last point 68→75.
  - Interchangeable runs of identical points make the exact pairing within a run arbitrary, and harmless.
  - Writes `align2.json` and `diff0.pkl` (102,631 differing cleanup-free keys).

**3. Full accounting (item 1):** `pairs_own.py`, with class rules in `classes.py`. Every key of both ledgers is placed. **OTHER = 0.**

| Class | Mine | Table |
|---|---|---|
| A | 425 points (each equals a neighbour within 12 points), 43,609 cleanup-free keys, 1,316 pair cases / 51,456 keys (each equals its own single result or a neighbour's pair case) | same |
| B | 15,514 new / 6,080 old pair cases equal to their own single result; 823,611 new keys | same |
| C1 | 6,612, plus 1 at the single-mode last point = 6,613; 238 in restore | same |
| C2 | 353 closed (336 observed `allowed`; 17 restore, observed `storage_limit`), 308 expected set only (all observed `storage_limit`) | same |
| C2r | 51 (restore, exhausted, 17 points × 3 statuses), all closed | same |
| C3 (control_pending rows) | 0: no `control_pending.*` key changed except `restore-lock` | same |
| C3e | 28,739 changed + 66,499 new, all missing-only (table's 66,519 includes the 20 single-mode last-point keys) | same sum |
| C4 | 0: no `notice-continuation` / `advertised.*` key changed; no locked-phase key shows a continuation action | same |
| C5 | persistent last point: 44 missing-only + 2 `control_pending.restore-lock` (expected `False`, observed `True`) + 2 closed statuses | same |
| C-pairs | 1,071 cases / 60,722 keys. Every key that differs from the matched old case is itself C1, C2, C3e or C5, which is stricter than "equal outside the lock views" | same |
| E | 377 / 377 fixed keys equal | same |
| Unchanged | 1,016,218 cleanup-free keys; 14,954 pair cases / 530,467 keys | same |

- Old pair cases: 14,954 + 6,080 + 1,071 = 22,105, so none is lost.
- Key totals close on both sides.
- Outside `crash-locked` and the restore flow, the **only** cleanup-free changes are the 644 C2 status keys: same observation, expected set widened.
- Re-run with a structure-preserving canonical form (`ISO=1 pairs_iso.py`): every equality-based count is identical (unchanged, same pairs, A, B, fixed). Its 344 "OTHER" are an artefact of that form: the 308 C2 keys, the 35 keys in item 4 below, and their one pair case. I checked them separately.

**4. Nothing stale shown during the lock (item 3):** `shown_locked.py`, `subset35.py`, `look35b.py`, `show35.py`.
- I scanned every key of the new ledger in a locked phase (`crash-locked`, and the restore flow's other phases) for a shown, non-count fact.
- Mail rows and notices appear **only** in the envelope of the flow's own faulted call (`envelope.mail_send`, `mail_move`, `mail_copy`, `mail_unsubscribe`, `mail_operation_repair`, `mail_account_add`, and so on). That reply is built before the crash. The `crash-locked` checker only drains it, and runs only while `store.locked`, before the confirm (`test_owner_state_sweep.py`, `exercise`).
- No `control_pending.*`, `passive.*`, `mail catalogue.*`, or envelope of a read made under the lock shows any Mail row or notice.
- The 35 C3e keys that still show a fact (`status/*/…/crash-locked/envelope.mail_operation_status.notice-head`) show it only on page 1 of 4: the flow's own status call, raw-identical to the pin.
  - On pages 2–3 (reads under the lock) the pin showed a stale "unchecked: sent copies not yet checked" Mail notice. The capture shows nothing there.
- R1's code (`engine.py`) hides other apps only when `store.locked`, and the same reply carries `restore_required: locked`.
  - So a hidden Mail notice with no `.restore-lock` gap means the store and the oracle both say locked.
  - This covers the restore flow's new `envelope.control_restore_confirm.notice-head/count` keys at 74 and 75 (`crash-restart`, the faulted confirm's own reply): no `restore-lock` gap there, except the known C5 at 75 persistent.

**5. C2 keeps the disagreement visible (item 2):** `c2check_own.py`, `c2pairs.py`.
- **644 status keys outside the restore flow** (161 `exhausted`, 483 `live-restored` slots): every slot keeps `control_pending.restore-lock`, `passive.restore-lock`, `aresos log.restore-lock` and its envelopes' `restore-lock` gaps. They are unchanged from the pin: expected `True`, observed `False` on all 13,085 pages.
- **Restore flow:** all 17 slots (17 C2 + 51 C2r keys) keep `aresos log.restore-lock` (expected `True`, observed `False`). C1 closes their `control_pending.restore-lock`.
- **Pair cases:** exactly 585 pin keys expect `restore_required` alone, at 360 slots (all `live-restored`, outside the restore flow).
  - Each slot has at least as many capture pair cases with `aresos log.restore-lock`, `control_pending.restore-lock` and `passive.restore-lock` gaps as it had pair cases of each.
  - No capture pair case still expects `restore_required` alone.
  - A 586th pin key mentions `restore_required` only as an *observation*: restore 68→75 pair 69, single, `live-restored`; C5-type.

**6. D (item 4):** `d_check.py`. Pin 100 keys; capture 100 at the same aligned points (98 equal, 2 C2, see NOTE 2); trace capture 18. All observe `storage_limit`. No pair keys exist for these views in either ledger.

**7. E strictness:** `strict_e.py`, `iso_e.py` (see NOTE 3).

Exploration helpers: `explore.py`, `restore_align.py`, `restore_detail.py`, `examples.py`, `restore_cr.py`, `look35.py`, `iso_other.py`. `classify0.py` is my first pass; it has a two-page bug in its C2 test that misfiled 36 keys, which `classes.py` fixes.

## Not checked

- The production code and the oracle change (already reviewed as SAFE).
- The clean-run point counts. The ledger holds only failing points; I checked that the failing point sets equal the trace capture's.
- The name of the failing test in the 48 shards. I checked only the job conclusions.
- The proof run (NOTE 1).
