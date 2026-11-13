# 20, post-18d g: latency ceilings set, and two owner answers

The lead's decisions of 2026-11-13, plus the owner's answer on board #216. The earlier post-18d briefs stand; where
they differ, this brief wins.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## 1. Latency ceilings: set by the lead

The proposed ceilings are accepted as they stand (median/p95):

| Call | Ceiling |
|---|---|
| read | 35/60 ms |
| navigate | 100/150 ms |
| click | 650/750 ms |
| fill | 650/750 ms |
| asking click, up to the question | 60/100 ms |
| approval to done | 700/850 ms |

- Mark `latency-targets.json` as set by the lead (mac-aresos-control, 2026-11-13).
- In `REPORT.md`, say they come from run `43502970342` (4,000 inputs, plain and instrumented profiles), measured
  against the 11-10 baseline `ab7aba92`.
- **The CI check must also catch round 3's slowdown.** Add a removal probe: reintroduce the round-3 cost (in memory
  or in a fixture) and show that the check fails.

## 2. The hold window stays as it is

Leave the 525 ms hold window alone in this package. In `REPORT.md`, record "end the hold window once the page's
queued tasks are done" as an **open idea**, with your measured estimate (about half the time of a click or a fill).
It isn't work for this package; the lead passes it to linux-tools as a capability idea for the owner.

## 3. Editors: accepted by the owner (board #216)

The owner chose "Read editors without asking" (board #216, 2026-11-13). Editable areas stay read in an unwatched
document; nothing in the build changes. In `KNOWN-LIMITS.md`, mark that line as accepted by the owner (board #216,
2026-11-13): a secret he un-hid in such an editor, not labelled as one, would be read. Drop `-f`'s provision to keep
editable areas easy to move under asking.

## 4. Runs

Up to about 280 runs of `control-chrome.yml` on `pkg/20-chrome`. Batch browser evidence where several fixes can
share one run, and keep `[skip ci]` with single runs in between. Never cut the final pair.
