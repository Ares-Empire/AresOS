# 20, post-18d d: the late-reader rule, decided except one case

The lead (2026-11-13) has decided how the reader handles a document it didn't watch from its start: the owner's tab
read in place, or a taken tab before its reload. This matches linux-tools' briefs 28 and 28b. It replaces item 3 of
`briefs/20-post-18d-c.md`; the rest of `-c` stands, and so do the earlier post-18d briefs.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## The rule in an unwatched document

- **`textarea` and editable areas are read.** A password field is always a single-line input.
- **Checkbox, radio, select, date, email, url and search inputs keep their values.**
- **Single-line inputs that can hold typed text** (`text`, `tel`, `number` and unknown types) show only **"filled"**
  or **"empty"** by default.
- **Credential-looking fields are never read anywhere**, watched or not (`-c` item 2: `name`, `id`, `autocomplete`,
  `aria-label`, label text or `placeholder` naming a password, PIN, passcode, one-time or security code, in English
  and German, plus `-webkit-text-security`).

## Still open: board #210

Whether those single-line fields may be read is open with the owner. The options:
- ask first (the lead's recommendation): a separate asking tool such as `chrome_read_typed_fields(tab)` under the
  managed ask rules, whose question lists the field labels without their values;
- only "filled" or "empty";
- read them.

Build the default ("filled" or "empty") now. Keep it easy to plug in either answer: one place decides how a
single-line field in an unwatched document is shown. **Don't build the asking tool** until he answers; the lead sends
it.

## Tests

The revealed-password probe in a taken tab before its reload; each input type above, in watched and unwatched
documents; each credential signal; and removal probes for each.
