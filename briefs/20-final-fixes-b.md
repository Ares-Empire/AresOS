# 20, final fixes b: after the scoped re-check

The scoped re-check of the fix round (`a4143586..b698d68e`) came back like this:
- the package re-check, [REVIEW-RECHECK-FINAL.md](../reviews/20-chrome/REVIEW-RECHECK-FINAL.md) (Opus), found
  **1 FIX**;
- the security re-check, [SECURITY-RECHECK-FINAL.md](../reviews/20-chrome/SECURITY-RECHECK-FINAL.md) (Fable), is
  **SAFE**, with two known limits and six notes.

This brief closes the FIX and folds in what is cheap and safe from both reviews. `20-final-fixes.md` and its rules
still apply. Where they differ, this brief wins.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## G1. A release cancels Claude's earlier typing marks (package FIX-1)

**The bug.** After a release and a retake, a field Claude typed before the release still counts as "typed by
Claude", even when the owner edited it while the tab was his. The report then says "All of it is Claude's own
typing, so it may be discarded without asking", and the owner's edit is lost without a question. This is the normal
hand-back flow: he presses Stop to review Claude's draft and edit it, and later Claude takes the tab back and closes
or navigates it.

The code involved:
- `reader.js:519` (`typist`);
- `guard.js:123-125` and `:508`;
- `background.js:607-609`;
- `reader.test.mjs:656-657`, which pins the bug;
- the comment at `reader.js:558`, which says the opposite.

**Fix.**
- The guard counts releases. Each Claude mark stores the count at the time it was made.
- `typist` counts a field as Claude's only if its mark was made after the latest release. Anything older counts as
  the owner's.
- The cost is one extra question when Claude takes back its own untouched draft. That is accepted.

**Tests.**
- A Node test: Claude types, the tab is released, the owner edits, the tab is retaken. The field is reported as the
  owner's.
- A removal probe.
- Fix the pinned test and the comment.
- Rewrite `KNOWN-LIMITS.md` line 27 so it says what remains.

## G2. A lost finish doesn't leave the field marked as Claude's (security KNOWN LIMIT 2)

When a finish is lost (`dialogPauseFailed`, or `finish_input` failing on an unchanged document), `inFlight` and
`typingTarget` stay set. The owner's later typing into that field is then marked as Claude's until Claude types
there again (`guard.js:128-135`, `background.js:498-510`).

**Fix.** In `reloadState`, a field whose guard is still in flight is not "Claude only". Its typing counts as the
owner's.

**Tests.** A test and a removal probe. Then update `KNOWN-LIMITS.md` line 24 so it states the corner as it now
stands.

## G3. New known-limit line (security KNOWN LIMIT 1)

Claude's own click or submit can make the page navigate a Claude tab, and the discard report doesn't run for that.
Typing the owner did in that tab after its guard was installed can be lost with it. The harm is one owner draft. It
is accepted because a click is what navigates, and cancelling the page's own navigation on every Claude click would
break normal clicks. The owner is at the keyboard and sees the tab he typed in.

Add this line. Fold in the reviewer's NOTE about `fill` over owner text, as the narrower case of the same line.

## G4. Notes worth closing

1. **Index creation order.** The partial index is now created before the held recovery space is loaded, so its small
   space check ignores that space. The old code's comment required the opposite order. Restore that order, or show
   with a test why it doesn't matter. The full-disk open test must still pass.
2. **Index identity.** An existing database recognises `operation_open` by its name only, so a later change to
   `OPEN_OPERATIONS` would silently slow those stores. At open, compare the stored index SQL (`sqlite_master.sql`)
   with the definition built from `OPEN_OPERATIONS`, and recreate the index when they differ.
   - It must stay full-disk tolerant: if it can't be recreated, the reads still work.
   - Add a test and a removal probe.
3. **Credential names.** Add API-key variants (`api key`, `api-key`, `apikey`, `API-Schlüssel`) as whole tokens,
   with tests.
   - Don't add a bare `token`: hidden CSRF fields are commonly named `*_token`, and withholding them would refuse
     ordinary forms. Say so in the word-heuristic line of KNOWN-LIMITS.
4. **Stale removal probe.** The older probe that now hits the copy of its clause inside the index definition, instead
   of its original spot, should target the original spot again.
5. **Cosmetic.** Remove the stray blank line in `KNOWN-LIMITS.md` and the trailing space in the CI log record.

## Runs

**One** batched `control-chrome.yml` run on the fixed head, which must pass every row.
- That leaves 263 of about 280 runs used.
- The final pair comes after the same reviewers re-check this round.
- If the run fails for a cause you then fix, stop and report before a second run. The lead wants to hear before any
  run beyond one per fix round.

## Done when

- G1 to G4 are built, with tests and removal probes.
- The full local preflight is green.
- The one run passes every row and the latency stays under the ceilings.
- REPORT.md has a short "Fixes b" section, and the Handover reads "next: re-check of fixes b, then the final pair".
- KNOWN-LIMITS.md is current.
- Everything is committed and pushed with `[skip ci]`.
