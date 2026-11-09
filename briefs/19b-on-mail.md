# 19b, on the Mail branch

**Lead decision, 2026-11-09.** Mail's security review 22 (`reviews/19-mail/SECURITY-REVIEW-22.md`) found three more
blocking points, in the classes this package closes by construction. Following the rule agreed with `mac-capacity`
and the owner's approval of 19b (board #126), Mail's review loop stops after round 29, and 19b is built now on top of
the Mail branch. This note changes only **where 19b starts, where it merges, and what it must also pass**.
Everything else in `briefs/19b-owner-state.md` stands. Where they differ, this note wins.

## Where it starts and merges

- Branch `pkg/19b-owner-state` starts from the head of the Mail branch `pkg/19-mail` (`d3babf1f`, plus this note and
  review 22). Files the brief says to read "on `main`" are read on this branch.
- Open the draft PR against `pkg/19-mail`, not `main`: `gh pr create --draft --base pkg/19-mail`. When 19b's reviews
  say SAFE, the lead merges it into `pkg/19-mail`. Mail's PR #9 then merges to `main` after a final security review of
  the combined head.
- Brief 18d (`pkg/18d-base-slim`) and brief 20 (`pkg/20-chrome`) are being built at the same time, from `d3babf1f`.
  Don't touch their branches. They merge after Mail, and the later one integrates. Chrome uses Mail round 29's
  `warnings.py` and `paging.py`. Keep their public behaviour unless a rule needs a change, and list every change in
  the report, so Chrome can follow.

## What it must also pass

- **Every blocking case of Mail's security reviews 20, 21 and 22** is a named regression test and an oracle case:
  - review 20: a refused reopen of a clean duplicate check, then archive;
  - review 21: an acknowledged RENAME check expiring, and paging past changed warnings;
  - review 22: a live RENAME dropping the observed Trash role while Drafts is unresolved; a refused recovery-result
    write discarding new warning evidence before it changes again; a transient journal ENOSPC before any bytes,
    after which `ensure_writable` keeps refusing a healthy disk.

  Stage 1's known-gap list starts with review 22's three cases.
- **Review 22's should-fix:** paging descriptions say what is built (a changed catalogue returns `page_changed` with a
  restarted first page), not `stale_reference`.
- **Restore:** this package closes the limit recorded in Mail round 29. After a restore, free-change checks, warnings
  and acknowledgements are re-derived from the projection. Remove round 29's restore sentence from the restore
  result and description once it is no longer true, and test the restore cases of the warning lifecycle.
- **Mail's suites and the full fault sweep** (all modes and shards) still pass. Mail's workflows run on this branch's
  pushes.
