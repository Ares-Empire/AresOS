# 20, re-check fixes 3: three FIX findings of the scoped re-check of 8f48c7bc

The scoped re-check of the round in briefs `20-recheck-fixes-2`, `-2b` and `-2c`: the package review
(`reviews/20-chrome/REVIEW-RECHECK-3.md`) is SAFE. The security review (`SECURITY-RECHECK-3.md`) finds three FIX
findings within the decided bar, and confirms that the known-limit lines are accurate. The earlier briefs stand;
where they differ, this brief wins. The stop rule is `20-continue-2.md`'s.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

Every fix gets a test that fails without it (a removal mutation), and browser cases with the independent receiver's
log: zero arrivals before approval, one after, none more on a repeat.

1. **A-3, a listener registered before insertion** (`SECURITY-RECHECK-3.md` 1). The page registers the listener
   through our wrapper on a detached button, then inserts it into a root it built with borrowed natives, then
   dispatches a borrowed-native, non-composed click. The Delete handler runs unasked. This isn't the decided
   all-native exception, because one step goes through our wrapper. Install capture on the detached receiver before
   wrapped listener registration. Browser tests: both orderings, open and closed roots.
2. **Image-map and SVG links stay active while reported as stopped** (`SECURITY-RECHECK-3.md` 2). Neutralise every
   supported native hyperlink type, HTML `area` and SVG `a` (its applicable `href` attributes) included. A result
   must never say "stopped" when the default could still run. Browser tests: navigation, a new context
   (`target=_blank`) and a frame target for each type, with the receiver at zero.
3. **The compose binding drops meaningful whitespace** (`SECURITY-RECHECK-3.md` 3). Keep visible line breaks and
   significant whitespace (`pre`, `white-space: pre*`, `textarea`) in the password-safe compose representation, in the
   question and the binding. Tests: a whitespace-only change re-asks, shows the change, then stops as decided, through
   preparation, the re-ask and final dispatch.

Update `REPORT.md`. `KNOWN-LIMITS.md` stays as it is unless a fix changes a line.

## Runs and waiting

`pkg/20-chrome` is at 209 of about 235 `control-chrome.yml` runs; tell the package lead in the report before
passing 245. Put all three fixes into one code push. Mark report-only pushes `[skip ci]`. Wait with one blocking
shell call per run; never poll turn by turn. Don't cancel runs you didn't start.

## Rules for this run

As `briefs/20-continue.md`, "Rules for this run", on branch `pkg/20-chrome`; the draft PR #27 exists. Don't merge `main`
yet; that is the next brief. Don't edit `docs/design/`. Any feature-removing refusal goes to the report for the lead
and the owner, never silently.

**Model:** `gpt-6.1-sol` at xhigh.
