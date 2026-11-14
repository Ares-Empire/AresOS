# 20, post-18d e: the owner chose "ask first" (board #210)

The owner answered board #210 with "Ask first" (relayed by the lead, 2026-11-13). Build the asking tool in post-18d,
on the slim generator. This replaces `briefs/20-post-18d-d.md`'s "don't build the asking tool". The rest of `-d`
stands, and so do the earlier post-18d briefs.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## `chrome_read_typed_fields(tab)`

- **A separate asking tool,** declared as an asking action in `ACTIONS`, so the generator puts it in the managed ask
  rules and the user MCP entry like send and delete. Not an option of `chrome_read`: ask rules match tool names only.
- **Scope:** only single-line typed fields (`text`, `tel`, `number`, unknown types) in a document the reader didn't
  watch from its start. In a watched document the normal read shows them anyway; after the reload the normal rules
  apply.
- **The question** names the tab (site and title) and lists the fields it will read by label, with a stable
  description for unlabelled ones (position or nearby text). It never shows values.
- **Credential-looking fields are never included,** approved or not.
- **One approval covers one call.** Values in the result go through the normal redaction and are marked as page
  text. Without approval, or when denied, the normal read keeps "filled" or "empty".
- **A field list that changes** between the question and the read (fields added or relabelled) refuses and re-asks.
  It's the same binding idea as the compose area.
- **One sentence in `instructions_for('chrome')`:** to read what the owner typed in a taken tab before its reload,
  use this tool, and only when the task needs it.

## Tests (in the browser, with removal probes)

- Approve: the values arrive once.
- Deny: only "filled" or "empty".
- The revealed-password probe: a credential-labelled `type=text` field is never included, even when approved.
- An unlabelled field appears in the question by its description.
- A field-list change re-asks.
- A removal probe for each.

Order: the base-URL fix, then `-c` and `-d` with this tool, then the rest of `20-post-18d.md`.
