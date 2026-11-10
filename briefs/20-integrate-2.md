# 20, integrate 2: how the owner sees Claude's popups (lead's decision, 2026-11-10)

The integration run found that Chrome hides the extension's action area in popup windows, and added a separate
extension window listing Claude's popups. The lead decided otherwise: **nothing of ours may open a window or take
focus.** This short run replaces that window. The earlier briefs stand; where they differ, this brief wins. The stop
rule is `20-continue-2.md`'s.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## Where it starts

The package lead stopped the integration run while it was building that window, to save runs. Its uncommitted
work is in this worktree: the changes to `control/chrome/extension/background.js`, `popup.html` and `popup.js` are
the unfinished control window (replace them as below); the report draft (`reviews/20-chrome/REPORT.md`) and the
retained evidence under `reviews/20-chrome/records/` and `screenshots/` are its results so far (keep, finish and
commit them). Then also finish what `briefs/20-integrate.md` still asks: everything green twice on the final head,
and the report.

## What to build

It uses section 6's existing signs (the group colour, a badge on the pinned toolbar button, Stop in its popup):
- **Remove the separate control window** and everything that opens or focuses a window of ours.
- **The opener tab's badge** on the pinned toolbar button, in the normal window, marks "Claude controls a popup
  opened from here", distinct from the ordinary control badge.
- **The action popup** (the existing one with Stop) lists each controlled popup, with a Stop for each that ends
  control of that popup at once.
- **Stop for a popup ends control without closing or reloading it**; the popup's page, window type, position, size,
  focus and opener stay unchanged.
- **When the opener tab closes or leaves Claude's group,** control of its popups ends at once and the badge clears.

## Tests (container, with the receiver's log where something could be sent)

- The opener's badge appears while Claude controls a popup and clears when control ends; no window of ours opens and
  focus never moves (compare window lists and the focused window before and after).
- The action popup lists the popup; its Stop ends control at once, the popup stays open with the same document and
  no reload (receiver load count unchanged), and a later Claude input in it is refused.
- Closing the opener tab, and releasing it from the group, each end control of its popups at once and clear the
  badge.
- Every popup test of `briefs/20-integrate.md` part 3 still passes.

## Report

Update `reviews/20-chrome/REPORT.md`: state this as a **decided rule** (lead, 2026-11-10), not a JUDGMENT-CALL, and
remove the control-window JUDGMENT-CALL. Record the run count.

**Runs:** `pkg/20-chrome` may use about **115** runs of `control-chrome.yml` in all; if it would pass that, say so in
the report and stop. Push in one batch where you can.

## Rules for this run

As `briefs/20-continue.md`, "Rules for this run", on branch `pkg/20-chrome`; the draft PR #27 exists.
