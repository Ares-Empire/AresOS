# 20, re-check fixes 2: A-3's last variant, borrowed-native defaults, changed previews

The scoped re-check of `8627e65e` (`reviews/20-chrome/SECURITY-RECHECK-2.md`, `REVIEW-RECHECK-2.md`) left three FIX
findings. The lead decided all three on 2026-11-12, applying the owner's rule that real harm gets fixed and known
limits are only for low harm. Neither fix removes a feature. The earlier briefs stand; where they differ, this brief
wins. The stop rule is `20-continue-2.md`'s.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

Every fix gets a test that fails without it (a removal mutation), and browser cases with the independent receiver's
log: zero arrivals before approval, one after, none more on a repeat.

## 1. A-3, its last variant

A shadow root created and filled through borrowed native functions (`attachShadow`, `appendChild` and the other
insertion routes), followed by a non-composed borrowed-native click, still runs a labelled Delete unasked. Cover it.
Browser variants: native insertion with non-composed events, open and closed roots. No handler runs, and nothing goes
unreported.

## 2. A non-cancellable default through a borrowed native function

Today its default request (a destructive link's address) goes out with no question, and the tool reports
`unknown`. Fix it with a **tab-scoped session `declarativeNetRequest` block** that holds while the hold window is open
in that Claude tab, so the default can't reach its address.

- **Every escape route is covered and tested in the browser fixture:**
  - a `target=_blank` link, or a form that opens a new tab or window (a rule scoped to the source tab doesn't reach
    it);
  - a frame-targeted link (`sub_frame`);
  - `<a ping>` (resource type `ping`);
  - a form submission's default;
  - `<a download>`.
  If a route can't be covered, tell the package lead in the report before calling it a known limit.
- **The owner's own navigation still works.** A click of his in that tab during the window navigates. Use the
  owner-mark mechanism built for his Enter; test it in the browser and with a removal probe.
- **The rule never outlives the window.** Remove it on answer, deny, timeout, tab close, and extension or service
  worker restart, and reconcile leftover session rules at startup. Test the restart case.
- **The result says "stopped" with the reason,** so Claude can retry through the question.

## 3. A read-only preview changed while the approval waits

Bind the compose area's visible text: the smallest area holding both Send and the draft. Never refuse such sends
outright, because that would remove a feature.

- A change re-asks, and the new question shows what changed, not only that something changed.
- Bounded: if the text changes again during the re-ask, stop and tell Claude that the text next to Send keeps
  changing, so the owner can send it himself. No ask loops.
- If that smallest area is the whole page or close to it, say in the report what is bound there.
- Browser fixtures: live text outside the compose area (a ticking timestamp, an autosave line, a counter) never
  re-asks. Live text inside the compose area re-asks once, then stops as above.

## Report and known limits

- Remove both items from `reviews/20-chrome/KNOWN-LIMITS.md` and write the remaining cost there instead: the bounded
  re-ask, and the owner sending it himself when the text keeps changing.
- Update `reviews/20-chrome/REPORT.md` where it accepted these as residuals. Don't edit `docs/design/`; the lead
  updates section 6.

## Runs and waiting

- `pkg/20-chrome` is at about 186 of 215 `control-chrome.yml` runs, and each push starts two (push and pull request).
  Put all three fixes into **one code push**, so its two runs serve the scoped re-check. Mark report-only pushes
  `[skip ci]`. The final pair of runs is kept for the head after the post-18d part. If a second code push is needed,
  that's fine; if the count would pass 215, say so in the report and stop.
- Wait on each run with one blocking shell call; never poll turn by turn. Don't cancel runs you didn't start.

## Rules for this run

As `briefs/20-continue.md`, "Rules for this run", on branch `pkg/20-chrome`; the draft PR #27 exists. Read the
specification from `origin/main` with `git show` after `git fetch origin main`. Any feature-removing refusal goes to
the report for the lead and the owner, never silently.

**Model:** `gpt-6.1-sol` at xhigh, as decided for this round.
