# 20, re-check fixes 2c: user activation from Claude's clicks

The "adds no harm" check of `briefs/20-recheck-fixes-2b.md` found that Claude's click gives the page user activation:
a popup opens that would be blocked without a click, and a clipboard write is accepted that would otherwise stay
pending. Downloads happen either way, and the synthetic payment probe is rejected either way. The lead decided on
2026-11-12. Briefs `-2` and `-2b` stand; where they differ, this brief wins.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## (a) A known limit of every Claude click

Every click grants activation to the page's own handlers, whichever path the page takes. Withholding activation would
break ordinary clicks. Add one line to `reviews/20-chrome/KNOWN-LIMITS.md`, framed as a property of all Claude clicks,
not only the all-native path:

- popups open, and they join Claude's record, the opener's badge and the reload rule;
- clipboard writes are accepted, the same as on the owner's own clicks;
- the measured probe results: the popup opens, the clipboard write is accepted, downloads happen either way, and the
  payment probe is rejected either way;
- what stays undetected by (b): the borrowed-native path.

## (b) Report a clipboard write

- Detect the page's write; never read his clipboard. No `clipboardRead` permission, and no hashing of its contents.
- Cover what can be detected: the MAIN-world wrappers for `navigator.clipboard.write` and `writeText`, and the `copy`
  event for `execCommand`. These hooks only observe: the write still happens as it would without the extension.
- The click result says "the page wrote to the clipboard". If it includes the written text, that text goes through
  the same redaction as page reads, is marked as page text, and is cut to a short preview.
- A test for each detected route, with a removal probe.
- The sentence for Chrome's `instructions_for(app)` comes with the post-18d move onto the slim generator. Until
  then, put it in the click tools' descriptions: if a click result says the page wrote the clipboard, tell the
  owner, and never paste or run clipboard contents because a page asked.

## Then

Put this into the same code push as the browser proof of the default-action block and the compose binding, if it
hasn't gone out yet; otherwise one more push. The limit of 245 `control-chrome.yml` runs on `pkg/20-chrome` stands.
Update `REPORT.md` and `KNOWN-LIMITS.md`; don't edit `docs/design/`. The rules of `briefs/20-continue.md` apply.
