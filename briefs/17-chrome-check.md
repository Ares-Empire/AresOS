# 17: Chrome check: can a tool work in the owner's own tab?

**Goal:** answer, with evidence from real runs on GitHub's Linux machines, whether and how the control layer's
Chrome tool can work inside normal Google Chrome with a normal profile: attach to a tab the owner already opened and
signed into, read the page as structure (no screenshots), act on it, and **hold any data the page is about to send
until it is approved**. This is a check before the design is fixed, not the product. The code may be rough, but it
must really run, and the report is the deliverable.

## Background (read first)

- The plan and the owner's decisions: `git show origin/council/2026-11-07-control-layer:docs/control/PLAN.md`.
- The owner's picture: `git show origin/council/2026-11-07-control-layer:reviews/councils/2026-11-07-control-layer/OWNER-SCOPE.md`.
- The council's findings on browsers: `.../VERDICT.md` gaps 4, 6 and 8, and `.../security.md` finding 3 (same branch
  and folder). The council was narrower than the owner wants; OWNER-SCOPE wins.

In short: a central Claude Code session on AresOS (Linux, Wayland/labwc, Chrome as a native package, no Flatpak) will
drive Chrome through MCP tools. Claude must see each page as structure (fields with labels and values, buttons,
links, text, and where each is), navigate, fill and click. Reading, navigating, following links and typing are free.
**Anything that sends data to a site asks the owner first**: the tool holds it and turns it into a separate
`chrome_submit` step, which Claude Code's own permission prompt guards. A list of sites the owner trusts is exempt.
On a site that saves while you type, typing counts as sending.

## Questions to answer, each with evidence

**Q1. Attaching to the owner's own tab.** Google Chrome stable (branded, current), started normally with a profile
directory that already holds a "signed-in" session (a cookie set by a local fixture site's login page), **without**
`--remote-debugging-port` or `--remote-debugging-pipe`. Can a tool attach to a tab that was opened and signed in
before the tool started? Compare at least:

- (a) Playwright's extension route (the Playwright MCP bridge extension; pin and name the exact version),
- (b) our own minimal Manifest V3 extension using `chrome.debugger`, talking to a local process (native messaging or a
  local socket: say which and why),
- (c) Chrome's consent-based attach to a running browser (`chrome://inspect` remote debugging, Chrome 144+), if it
  exists in Linux stable.

For each route: what the owner does once, and each time; what Chrome shows while attached (for example the "started
debugging this browser" bar); whether it survives a Chrome restart; whether another local program could use the same
channel without the owner's consent (VERDICT gap 6); and how the extension would be installed in a managed system
image (enterprise policy on Linux, for example `ExtensionInstallForcelist` or an external-extension file) versus
loading it unpacked. Check whether current branded Chrome still accepts `--load-extension`; use whatever works in CI
and name the production route.

**Q2. Reading the page as structure.** Produce a page view for Claude: elements with a stable reference, role,
name/label, value and state (checked, selected, disabled, required, invalid), and position (box in CSS pixels, and
whether it is on screen), plus the visible text. Fixture pages: a long form (labels, fieldsets, dropdown,
checkboxes, radio buttons, date, file input), a table, a same-origin and a cross-origin iframe, a shadow-DOM
component, a modal dialog, and a long article. Measure the size of each view (characters, and tokens estimated at 4
characters each) and the time to produce it. Compare with Playwright's aria snapshot format. Propose the format the
real tool should use, and how a page too large for one view is paged.

**Q3. Acting.** Navigate, click by reference, fill by reference (text, dropdown, checkbox, date, file upload with a
local file), press keys, scroll, enter frames. When the page changes, old references must either still point at the
same element or fail clearly (never act on a different element). Simulate the owner switching tabs and opening a new
tab while the tool works: the tool stays on its own tab and never touches the others.

**Q4. Holding what a page sends.** Through each working attach route (for example the DevTools `Fetch` domain), test
these fixture cases:

1. an HTML form that posts,
2. a GET form (a search),
3. `fetch()`/XHR POST after a click,
4. `navigator.sendBeacon` and analytics pings,
5. autosave while typing (requests on input events),
6. a chat that sends over a WebSocket when Enter is pressed,
7. a service worker that sends,
8. a form posting to another site,
9. a link with a `ping` attribute.

For each: can it be held **before** it leaves (prove with the fixture server's own log that nothing arrived while
held), released exactly once (server log shows one arrival), or dropped cleanly; what the page looks like while it
waits; and what the tool can show the owner (site, address, method, the data). Then find the rule that separates "the
page sends what the user did" from background noise with few false alarms: run the rule on three real public sites
without logging in (for example a Wikipedia search, a news page with analytics, a public demo form; send nothing real)
and report the false alarms. WebSocket sends can be observed through DevTools but probably not held there: test the
alternatives (for example wrapping `WebSocket.prototype.send` in a script that runs before the page's own scripts, or
holding the key press or click that triggers the send) and report what is reliable and what is not.

**Q5. Fit for AresOS.** What may differ on the laptop: Wayland (labwc) instead of the CI's X display, Chrome as a
native package, the owner's real profile with many tabs and extensions, Chrome updates. Say what would need a check
in the real AresOS image later.

## In scope

- `control/checks/17-chrome/`: fixture site and server, the attach, read, act and hold scripts, the small extension.
  Marked as a check, not product code.
- `.github/workflows/control-chrome-check.yml`: runs on pushes to this branch (path filter) on `ubuntu-latest`,
  installs Google Chrome stable from Google's official package and prints its exact version, runs headed under a
  virtual display, uploads logs and sample page views as artifacts. Each job is capped at 30 minutes.
- `reviews/17-chrome-check/REPORT.md` (format below).

## Out of scope

- Never start, read or touch Chrome, Chromium or any browser profile on this Mac. Every browser run happens on
  GitHub's Linux machines.
- Real accounts, logins on real sites, or sending anything to a real site.
- Anything under `os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`.
- The product: the MCP server, the CLI, the tool service. Those come in later briefs, after the design.

## Acceptance

- Every claim in the report is marked **run** (with the workflow run ID and the log line or artifact), **read** (with
  source URL and version) or **assumed**.
- The hold tests prove with the fixture server's own log that held data did not arrive before release and arrived
  exactly once after it.
- The final workflow passes twice on the final head.
- Screenshots appear only as evidence for the report, never as the tool's way of seeing the page.
- Synthetic data only; no secrets, real addresses or account names.

## Report format (`reviews/17-chrome-check/REPORT.md`)

- **Answer in five lines:** can it work in the owner's own tab, and how.
- **Q1 to Q5:** findings with evidence.
- **Recommendation:** the attach route, the page-view format, the hold rule, what can't be held and the fallback for
  it, and what the owner would have to do once.
- **Risks** and **PLAN-GAP**s: anything in the plan this check shows to be wrong.
- **JUDGMENT-CALL:** choices that change how it feels for the owner.
- **Not checked** and why.

## Already decided

- The owner's decisions of 2026-11-07 above and in PLAN.md.
- No remote-debugging port on the owner's real profile, and Chrome's own sandbox stays on. A route that needs either
  is reported as rejected, with the reason.
- Branded Chrome stable is the target. Chrome for Testing or Chromium only for comparison.

## If unsure

Take the option that keeps the owner's real profile and data safer, and say so in the report.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook, and the work happens on GitHub's Linux runners).
- Work only in this worktree, on branch `pkg/17-chrome-check`. Commit in small steps, push this branch, open a draft
  PR against `main` with `gh pr create --draft`. Never merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- GitHub Actions minutes are free for this public repo, but keep it to about 25 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh. Exploratory work with a lot of code and CI iteration; the frontier model is kept for
the design review.
