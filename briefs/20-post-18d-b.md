# 20, post-18d b: close the base-URL class, not the case

The lead (2026-11-13) wants the first item of `briefs/20-post-18d.md`, the base-URL FIX, to close its whole class.
`20-post-18d.md` stands; where they differ, this brief wins.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

Every place the tool resolves a destination resolves it against the document's base URL at the moment of the action:
- a link's `href`;
- an `area`'s `href`;
- an SVG `a`'s `href` and `xlink:href`;
- a form's `action`;
- a button's or input's `formaction`;
- the target frame or window (`target`, `formtarget`).

The approval binds the resolved absolute destination. Any change before dispatch re-asks: to the base, to the
attribute, or to the form owner (through `form=`).

Tests: each source above with a base change while the approval waits, a stale approval giving zero receiver
arrivals, and a removal mutation per source.

The rest of `20-post-18d.md` follows in its order.
