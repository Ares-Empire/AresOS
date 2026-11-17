# Classification check: the re-pin of 20-restore-lock-followups (`f31ef5c2`)

Checker: a fresh Claude agent on Opus 5.5, 2026-11-16. I worked read-only on tracked files and did not build this
package. This file is the only one I wrote in the repo, and it is not committed.

**Verdict:** I checked every claim with my own scripts, and every number matches the builder's exactly. No key
outside H changed. Every change at H falls into a class that `KNOWN-GAPS.md` explains. There are two wording nits
and nothing else.

## What I read and ran

- **Read:**
  - `AGENTS.md`;
  - the brief (S2 and N7 in its review section);
  - `BRIEF-REVIEW-1.md` and `PROGRESS.md`;
  - the new section of `reviews/19b-owner-state/KNOWN-GAPS.md`;
  - `control/owner_state_oracle/gaps.py`, for the ledger format only.
- **The two pins:**
  - `git show 590f96bf:` (old) and `git show f31ef5c2:` (new) of `reviews/19b-owner-state/KNOWN-GAPS.json`.
  - The worktree file and `accf2eb0`'s copy are the same bytes as `f31ef5c2`'s.
- **Downloads (read-only):**
  - `gh run download` of runs 43722918063 (the capture behind the old pin), 43893138937 (the capture) and
    43919136534 (the proof), each into its own empty scratch directory.
  - Each run's job logs, through `gh api …/actions/runs/<id>/logs`.
  - I dispatched nothing.
- **My own scripts:**
  - Four small scripts plus short inline queries, kept in a scratch directory outside the repo and not committed.
    All ran under `python3 -I`, with peak memory under 1 GB.
    - `merge.py` merges a run's 53 lists and refuses conflicting shared keys.
    - `pack.py` is my own packer for the format-3 layout.
    - `classify.py` and `hdetail.py` sort the differences into classes.
  - I used none of the builder's scripts, which are not in the repo. I did not run `gaps.py`.
- **Not run:**
  - nothing under `os/tests`, and no `test_owner_*` module;
  - no container, no root, no mount;
  - no rpm-ostree, bootc or ostree command.

**Why the CI lists, and how they are tied to the JSON files.**
- The committed pins are compact. Each group holds only its count, three sample keys and a SHA-256, so the two
  JSON files alone cannot support a key-by-key claim.
- I therefore re-packed each run's merged full list with my own packer.
- The old capture's lists give the old pin byte for byte: `ee326914…`, 921,711 bytes, 1,997 groups. The capture's
  lists give the new pin byte for byte: `8b27b116…`.
- So the per-key counts below are counts over exactly the keys whose digests the two committed files hold.

## The claims

| # | Claim | My number | Result |
|---|---|---|---|
| 1 | Outside H, every key byte for byte: 2,512,704, none added | 2,512,704 unchanged; 0 changed, 0 added, 0 closed outside items 1 and 2 | match |
| 2 | H = 1,386 cases (322 single, 161 persistent, 903 pair) and 92,945 keys; S2's set comes from the old pin's lock gaps | 1,386 (322, 161, 903) in 31 flows; 92,945 keys (7,015 `exhausted`, 59,726 `live-restored`, 26,204 `crash-restart`, 0 `crash-locked`) | match |
| 3 | At H: 30,291 close (15,030 lock views), 9,316 change, 725 appear | 30,291 close (15,030 lock views, 3,939 statuses, 1,547 holds, 9,775 rows); 9,316 change; 725 appear; 53,338 unchanged | match |
| 4 | Item 2 closes 16,383; item 1 closes 40 (25 lock views, 12 statuses, 3 holds) | 16,383; 40 = 25 + 12 + 3 | match |
| 5 | `.restore-lock` keys go from 31,438 to 0 | 31,438 → 0 | match |
| 6 | The point counts are equal in all 34 flows | 34 of 34 equal (and equal in the proof) | match |
| 7 | New pin: 2,576,083 keys, 1,930 groups, SHA-256 `8b27b116…` | 2,576,083 keys, 1,930 groups, 892,234 bytes, `8b27b1161505ac19…`; my packer's bytes from the capture and from the proof are both identical to the file | match |
| 8 | N7 (the rows left at H): 6,949 keys at 870 cases | 6,949 keys, 870 cases, 16 flows; every view count in `KNOWN-GAPS.md` equal | match |
| 9 | No key outside H changed; no change at H lacks an explanation | 0 residual outside the classes; every class at H accounted for (below) | match |

Method for each claim, in two lines:

1. **Outside H.** I loaded both merged lists as key → canonical detail (`sort_keys`, compact). For every key in
   their union outside H, I compared the two strings. Anything not in item 1 or item 2 went to a residual list,
   and that list is empty.
2. **H.** I applied S2's predicate to the old list: a case outside `restore` with `passive.restore-lock` or
   `control_pending.restore-lock` in `exhausted` or `live-restored`, where every failure is missing
   `locked=True` and extra `locked=False`. The loose predicate (any such key) gives the same 1,386 cases.
3. **At H.** Each key at an H case is closed, changed, appeared or unchanged. I sorted the views into four
   classes: a view ending in `restore-lock`, `recovery-holds`, `response.*.status`, and the rest (rows and
   notices).
4. **Items 1 and 2.**
   - Item 1 is the lock, status and hold keys closed at `restore/persistent/75/0` (16, 8, 2) and
     `restore/single/75/76` (9, 4, 1). The other keys at those cases are unchanged, and 75 is the restore flow's
     highest pinned point in both lists.
   - Item 2 is every closed `aresos log.restore-lock` key outside H, each with expected `True` and observed
     `False`:
     - 15,982 in `crash-locked`: 6,375 single and 9,514 pair outside `restore`, plus 42 and 51 in it;
     - 69 in the restore flow's `exhausted` phase;
     - 332 in its `live-restored` phase (139 and 193).
5. **`.restore-lock`.** I counted the keys whose view ends in `restore-lock` in each full list. The 31,438 are
   16,383 (item 2) + 25 (item 1) + 15,030 (item 3).
6. **Point counts.**
   - Source: every `Owner oracle flow=… points=…` line in the job logs of runs 43722918063, 43893138937 and
     43919136534.
   - In each run there is one value per flow, 34 flows. The three sets are identical (for example `restore` 76,
     `cancel` 70, `onboarding` 2,610).
7. **New pin.** I took `sha256sum` and the group sums of the committed file. My packer then rebuilt the file from
   the capture's lists and from the proof's lists, and both are byte-identical to it.
   - The two runs' merged full lists are also identical, line for line.
8. **N7.**
   - Definition: at H, row and notice keys that changed beyond alias numbers (`#\d+` normalised), plus the keys
     that appeared.
   - Result: 6,224 + 725. By view: `pending-head` 3,719, `notice-head` 995, `notice-count` 901, `page` 433,
     `complete` 433, `pending-total` 339, `total` 129.
   - The example the section gives, `onboarding/persistent/1439/0/exhausted/mail catalogue.total`, is in the new
     list: the model expects 1 and the store shows 2.
9. **Every class at H.** I checked each class's deltas: which side changed, which pages, which facts, and which
   phase and envelope. The details follow.

## Every class at H, checked

- **Lock views:** all 15,030 closed. None changed and none is left.
  - 12,048 `live-restored`, 1,412 `exhausted`, 1,570 `crash-restart`.
  - The `crash-restart` keys are all envelopes.
- **Read statuses:** 3,939 closed and 1,936 changed. Nothing appeared, and 620 are unchanged.
  - 157 changed by alias numbers only, each a consistent one-to-one renaming.
  - In the other 1,779, the expected set went from `["restore_required"]` to `["allowed","journal_incomplete"]`.
    Each kept the same number of calls and gained no new failing page. On every page it kept, the observed facts
    are unchanged.
  - 627 of the 1,779 dropped pages, and every dropped page had observed `allowed`. That is "their pages observed
    `allowed` now pass".
- **`recovery-holds`:** 1,547 closed, one per H case in `live-restored` (1,386) and one per persistent case in
  `exhausted` (161).
  - The 274 unchanged are all in `crash-restart`. They concern cancel, settle and export holds, not the restore.
- **Rows and notices:** 9,775 closed, 7,380 changed, 725 appeared.
  - 1,156 of the changes are alias-only and consistent.
  - The 725 new keys are all counts: `notice-count` 329, `pending-total` 303, `total` 93.
  - What the closed and the beyond-alias changed keys expected in the old pin:
    - "unknown" rows with `RESTORED_EVIDENCE`, in 5,121 of the closed keys and 4,417 of all changed keys;
    - recovery notices with state `unknown`;
    - counts higher than the store showed.
- **No lock expectation is left at H.** None of the 63,379 keys at H in the new pin mentions `restore:#`,
  `RESTORED_EVIDENCE` or `restore_required`.
- **`crash-restart` at H.**
  - Views read after the restart (`mail catalogue`, `passive`, `control_pending`, `aresos log`) changed only by
    alias numbers: 288 keys.
  - Every change beyond alias numbers or new key in this phase (460 + 84 = 544) is the faulted call's own reply
    envelope, built before the crash. Examples: `envelope.mail_account_add` 208, `envelope.control_archive` 80,
    `envelope.mail_operation_repair` 72.
  - That is the running store showing its applied write, as N7 says.
  - No key at H is in `crash-locked`, before or after.

## Further checks (all equal)

- **The 53 lists of each run** merge without a conflicting shared key (495 identical shared occurrences).
- **Key totals:**
  - 1,136,793 cleanup-free keys, 1,438,913 pair keys and 377 fixed keys (old: 1,155,439, 1,466,256 and 377);
  - all 377 fixed keys are byte for byte the same.
- **Failing points and cases:**
  - failing points: 10,247 by (flow, point) and 20,239 by (flow, mode, point), the same sets in both lists;
  - cases with keys: 53,066, the same set;
  - the 544,801 other `crash-locked` keys and the restore flow's 22,915 other keys are byte for byte the same,
    with no new key in either.
- **The JSON files alone:**
  - 1,341 groups are identical (714,143 keys), 67 groups closed entirely (572 keys), 589 changed, and none is new;
  - every group with owner `suite` is identical.
- **Alteration shards:** 110 scenario lines per run, totalling 2,080,049 alterations with `slipped=0`, in all
  three runs.
- **The capture's failures:** all 48 sweep and onboarding shards fail only
  `test_all_flows_all_storage_modes_independent_views`.
- **Lineage:**
  - The old pin (`ee326914…`) is the same at the branch base `5d717142` and on `origin/main`.
  - `git diff 5d717142 f31ef5c2 -- control ':!control/owner_state_oracle' ':!control/tests' ':!control/mail_tests'`
    shows only `control/chrome/qualification.json`.

## Findings

No BLOCKER and no FIX.

- **NIT 1. N7's explanation doesn't mention the 544 `crash-restart` keys** (`KNOWN-GAPS.md`, "Named class").
  - The section says the running store "shows the write it applied before its commit marker failed". But 544 of
    the class's 6,949 keys are in the `crash-restart` phase.
  - They are the faulted call's own reply envelope, built before the crash, so the explanation holds. Views read
    after the restart changed only by alias numbers.
  - The section doesn't say this, and a reader may think the restarted store disagrees.
  - Fix: one half-sentence.
- **NIT 2. "The 544,801 other `crash-locked` keys (the hidden rows under the lock, M14 …)" reads narrower than it
  is** (`KNOWN-GAPS.md`, "What must not change").
  - They are 544,611 row and notice keys plus 190 `recovery-holds` keys.
  - Their groups span 11 matrix rows: 385,786 in M14 groups, 115,815 in M06, 29,678 in M12/C05/M14, and the rest.
  - The count and the byte-for-byte claim are right. Only the label is loose.

**Limit.** The ledger holds only deltas, not the store's state. For N7, I checked the shape of each change: which
side changed, which phase and envelope, and that no lock facts are left. I did not judge, key by key, whether the
model or the store is right. That is the open decision N7 names.

CONFIRMED
