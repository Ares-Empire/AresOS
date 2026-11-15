# 20, re-check fixes 2b: the lead's decisions on the stop and the two notes

The build of `briefs/20-recheck-fixes-2.md` stopped on A-3's last variant (`REPORT.md`, "PLAN-GAP — stop-rule
blocker"). The lead decided on 2026-11-12. `20-recheck-fixes-2.md` stands; where they differ, this brief wins.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## A-3's last variant is a KNOWN LIMIT

Every step goes through natives borrowed from another tab's realm. Only a deliberately hostile page takes that path,
and such a page could call `fetch('/delete')` without any click of Claude's. So it belongs to the accepted class "a
page sends on its own".

- `reviews/20-chrome/KNOWN-LIMITS.md` states it plainly:
  - what the page must do: a same-origin window outside Claude's tabs, and every step through borrowed natives;
  - what happens: a labelled Delete runs unasked;
  - why the tool adds no harm;
  - the three fixes rejected, each with its reason: breakpoints can't see the borrowed call; DOM breakpoints break
    the password rule; attaching the donor tab breaks "only Claude's tabs".
- Keep the PLAN-GAP section in `REPORT.md`, marked as decided by the lead.
- **Check "adds no harm" yourself:** does Claude's click give the page anything on this path it couldn't get alone,
  above all user activation (popups, downloads, payment sheets, clipboard writes)? If it does, cover that part (for
  example, the default-action block already stops downloads and new windows during the hold window), or name it in
  the report for the lead.
- **The result must not say the step did nothing when the tool can't know.** If the existing `unknown` or after-click
  reporting covers this path, show it in a test. If not, say so in `KNOWN-LIMITS.md`.

## The two notes are accepted

- A narrow DNR rule plus synchronous neutralisation of the default, instead of a catch-all block. The condition is
  that the browser runs prove all five escape routes, the owner's own clicks and approved submissions.
- A compose area that is the whole body binds all visible body text. Add a line to `KNOWN-LIMITS.md`: pages whose
  compose area is the whole body and that have live text there can end in "send it yourself". This is revisited
  after the owner's live tests if his real sites hit it often.

## Then

One code push that proves both fixes in the browser, both install modes, receiver 0/1/1, and every named case. The
budget is up to about 235 `control-chrome.yml` runs on `pkg/20-chrome`; say so in the report before passing 245. Mark
report-only pushes `[skip ci]`. Wait with one blocking call per run. Update `REPORT.md` and `KNOWN-LIMITS.md`.
Don't edit `docs/design/`; the lead updates section 6. The rules of `briefs/20-continue.md` apply.
