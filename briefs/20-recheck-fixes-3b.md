# 20, re-check fixes 3b: close each class, not just the reported case

The lead (2026-11-13) wants fix round 3 to be the last round for these three classes. Each fix in
`briefs/20-recheck-fixes-3.md` therefore covers the whole class. `-3` stands; where they differ, this brief wins.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

1. **Wrapped and native mixes, the full matrix.** There are four steps: create the root, insert, register the
   listener, dispatch. Each step is wrapped or native, the event composed or not, and the root open or closed.
   - Only the all-native row may be the known limit. Every other row must ask.
   - Generate the full matrix in the unit and probe layer.
   - In the browser, run a representative subset that includes every row where exactly one step is wrapped.
2. **Default neutralisation for every element with activation behaviour in the HTML spec:** `a`, `area`, SVG `a`,
   form submitters (`input type=image` included), and buttons associated with a form through the `form=` attribute.
   Each gets its own test. Anything not covered is never reported "stopped".
3. **The compose binding keeps text as rendered wherever whitespace is significant:** `white-space` values `pre`,
   `pre-wrap`, `pre-line` and `break-spaces`, and the `pre`, `textarea` and `code` elements. Test an
   indentation-only change and a line-break-only change.

Everything else in `-3` stands: one code push if possible, browser cases with the receiver's log, a removal mutation
per fix. The run limit is unchanged: tell the package lead in the report before passing 245.
