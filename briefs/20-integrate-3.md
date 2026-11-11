# 20, integrate 3: the combined fix round, the snapshot cap, green twice

Part P (page fixes, `df9b3fc5`) and Part S (state fixes, PR #34, green twice on `1418fcde`) are merged on
`pkg/20-chrome` by the package lead (`3b37bd57`, then `7c644c6b`). This short run adds the lead's cap on catalogue
snapshots, notes it, and brings the combined head to green twice before the scoped re-check. The earlier briefs stand;
where they differ, this brief wins. The stop rule is `20-continue-2.md`'s.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## 1. Catalogue snapshots: an absolute cap (lead, 2026-11-10)

The snapshots behind `chrome_downloads`, `chrome_history` and `chrome_bookmarks` (`collection()` in
`control/chrome/extension/background.js`) now stay alive while they are paged (Part S's JUDGMENT-CALL, accepted by
the lead; it doesn't go to the owner). Add an absolute cap: a snapshot expires **5 minutes after its last page
request, or 30 minutes after it was made, whichever comes first**, so a walk that never stops can't keep a stale
snapshot alive. Tests: the idle expiry, the absolute expiry during an active walk, and that an expired walk's result
tells Claude plainly to start the list again. Keep the existing bounds (two retained snapshots, invalid cursors
never renew one).

## 2. Notes in `reviews/20-chrome/STATE-FIXES-REPORT.md`

- The JUDGMENT-CALL is accepted by the lead (2026-11-10) with the absolute cap above; it is now a decided rule.
- The change is Chrome-only (`background.js`); the shared `control/aresos_control/paging.py`, `results.py` and
  `mail/` are untouched, so Mail's behaviour is unchanged and the merge order isn't affected.
- `background.js` belongs to Part P's files; Part S's one-line change there was merged into Part P's equivalent
  renewal (the merge kept Part P's version).

## 3. Green twice on the combined head

On the final head: every generated file regenerated and checked; the full local Python suite (both parts' tests, the
storage sweeps, the process cuts) and the Node suite; both parts' removal-mutation audits; then the whole Chrome set
in both install modes twice, and base, Mail, boundary and qualification twice, with the independent receiver audit.
Update `reviews/20-chrome/REPORT.md` for the combined head: link `STATE-FIXES-REPORT.md`, list every decided rule
of this round (popups, the reload on first act, the owner handoff for a dialog already open, borrowed-realm dialogs
asking, the owner's own Enter as "passes in CI, panel to confirm"), the DevTools commands added for injection, group
12 still deferred to 18d, and the run counts per branch.

## Runs and waiting

- `pkg/20-chrome` may use about **175** runs of `control-chrome.yml` in all; 166 are used. Push this in one batch.
  If it would pass 175, say so in the report and stop.
- Wait on each run with one blocking shell call (`gh run watch <id> --exit-status --interval 60`, or one loop that
  exits when all named runs have finished); no per-turn polling. Read failed jobs' logs only after the wait.
- Don't cancel workflow runs you didn't start.

## Rules for this run

As `briefs/20-continue.md`, "Rules for this run", on branch `pkg/20-chrome`; the draft PR #27 exists. Read the
specification from `origin/main` with `git show` after `git fetch origin main`. Any feature-removing refusal goes into
the report for the lead and the owner, never silently.
