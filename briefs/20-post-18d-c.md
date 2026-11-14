# 20, post-18d c: a password revealed before a take

A finding from the security review of linux-tools' brief 28 (astra), relayed by the lead on 2026-11-13. It hasn't
been verified in a browser yet. It goes into `briefs/20-post-18d.md` **after the base-URL fix** (`-b`). The earlier
post-18d briefs stand; where they differ, this brief wins.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## The finding

Taking a tab doesn't reload it (the first input does), and reading works on a taken tab. So between the take and the
first input, the reader reads a document it didn't watch from its start. If the owner revealed a password there
before the take (a "show password" toggle that turned the field into `type=text`, or a removed mask), the reader
has no history for that field and returns its value as ordinary text. `KNOWN-LIMITS.md` doesn't list it.

## Do now

1. **Verify it** in code, and with a probe in the browser fixture: take a tab whose password field was switched to
   `type=text` with a value, then read before any input. Build the probe so it fits whichever of the owner's three
   options below is chosen.
2. **Fix the part every option shares: a field that looks like a credential is never read**, watched or not. That
   covers a `name`, `id`, `autocomplete`, `aria-label`, label text or `placeholder` naming a password, PIN, passcode,
   one-time code or security code, in English and German, plus `-webkit-text-security` masking. Say in the report
   what the branch already does here, extend it, and test each signal with a removal probe.
3. **Hold the rest.** How single-line fields in an unwatched document are read waits on the owner (board #209). His
   options are:
   - ask first: one question per taken tab before reading typed text (the lead's recommendation);
   - hide: show only "filled" or "empty" until the reload;
   - read everything except credential-like fields.
   Build nothing for the choice yet; the lead sends his answer.

## Tab-group handling

Don't change how the extension handles tab groups (today one global Claude group id in `background.js`). Brief 28
turns that id into a per-tab field of the control record. If this brief needs a change there, stop and say so in the
report before pushing it.

The rest of `20-post-18d.md` follows in its order.
