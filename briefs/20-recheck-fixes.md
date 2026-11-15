# 20, re-check fixes: the four FIX findings, owner Enter, KNOWN-LIMITS.md

Two reviewers re-checked `65aca3e6` under the owner's normal-MCP bar (lead, 2026-11-12): `reviews/20-chrome/
SECURITY-RECHECK.md` (astra) and `REVIEW-RECHECK.md` (sol). Every earlier finding is fixed except the four below.
Each finding is classed FIX (real harm) or KNOWN LIMIT (a hostile page making a step look ordinary, low harm). This
run fixes the FIX findings, adds the owner-Enter evidence, and collects the known limits. The earlier briefs stand;
where they differ, this brief wins. The stop rule is `20-continue-2.md`'s.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## The bar (owner and lead, 2026-11-12)

A normal, well-made MCP/CLI tool, safe the way a good MCP is. Every asking action's question stays whole: it shows
the exact content that will be sent, that content is bound, and Claude can't answer, alter or replay it. The reader
never reads passwords. Nothing of ours runs in tabs outside Claude's group, and Chrome stays normal. Proving that no
adversarial page can ever disguise a step is not the bar. In the owner's words, known limits are only for low-harm
edge cases: "if a found flaw / vulnerability is worth fixing we should do it ... preventing Claude doing an obv
malware install or stuff like that." Working in the owner's own open tabs is a separate future brief; don't build it.

## Fix (each with a test that fails without it; browser cases with the receiver's log)

1. **The GET-search exemption bypasses explicit pay or delete labels** (`REVIEW-RECHECK.md` 1). Explicit asking cues
   come before the search exemption, in script activation and in every submission path of the guard. Ordinary GET
   searches stay free. Linux test: a "Pay" submit button in a `role="search"` GET form, activated by a free
   handler's `.click()`; no payment handler runs before its own approval.
2. **The affected item stops at a shadow boundary** (`REVIEW-RECHECK.md` 2). Resolve the smallest affected item
   through composed ancestry, across shadow hosts, and bind its identifying text. Cover open and closed roots, native
   list items and ARIA rows. Test: a changed item while the approval waits is refused.
3. **A send confirmation inside a form omits the outside draft** (`SECURITY-RECHECK.md`, B-6). Bind the complete
   generic draft set for send confirmations whether or not the button belongs to a form, in both the service and the
   extension. Add the form variant to the changed-draft Linux test: zero arrivals on the stale approval.
4. **Native-created shadow roots escape the activation fallback** (`SECURITY-RECHECK.md`, A-3). Don't assume every
   shadow root already has capture. Handle composed events on unregistered roots, and cover roots made through a
   borrowed native `attachShadow` before a non-composed activation can run. Linux tests: both variants. No handler
   runs, and no uncertainty report goes missing.

## Owner Enter

The lead keeps it at "passes in CI, panel to confirm" until a browser variant exists whose Claude-started timer
really fires **while his mark is set**, with independent evidence of that overlap (timestamps from the page and the
receiver's log). His Enter goes at once; the timer's submission is held. Add it. The four removal probes (exact form,
exact submitter, trusted input, mark clearing) already fail as they should; keep them.

## KNOWN-LIMITS.md

Write `reviews/20-chrome/KNOWN-LIMITS.md`, one line each: what, its harm, and why it is accepted. Include every
KNOWN LIMIT of the two re-check reviews that still holds, and section 6's residuals as built. Those are: a page that
sends on its own after an ordinary click, data leaving through addresses, the word list as a rule of thumb, the
instant between check and input, a non-cancellable activation through a fresh-frame function reported as `unknown`,
a read-only preview without an adapter, `done` not proving delivery, an owner's delayed page step inside the window
held and asked, a dialog already open handed to the owner, and a borrowed-realm dialog asked unguarded. The lead
writes them into section 6. Don't list anything this run fixes.

## Green twice

On the final head: the full local Python and Node suites, the removal-mutation audits, then the whole Chrome set in
both install modes twice, plus base, Mail, boundary and qualification twice, with the independent receiver audit.
Update `reviews/20-chrome/REPORT.md` with the fixes, their tests and run IDs, and the owner-Enter evidence.

## Runs and waiting

- `pkg/20-chrome` may use about **215** runs of `control-chrome.yml` in all; 175 are used. Batch your pushes, and
  mark pushes that only add reports `[skip ci]`. If it would pass 215, say so and stop.
- Wait on each run with one blocking shell call; never poll turn by turn. Don't cancel runs you didn't start.

## Rules for this run

As `briefs/20-continue.md`, "Rules for this run", on branch `pkg/20-chrome`; the draft PR #27 exists. Read the
specification from `origin/main` with `git show` after `git fetch origin main`. Any feature-removing refusal goes into
the report for the lead and the owner, never silently.
