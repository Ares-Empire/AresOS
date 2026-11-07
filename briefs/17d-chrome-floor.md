# 17d: Chrome check, part four: Chrome's own blocking rules as the floor

**Goal:** settle, with evidence from real runs on GitHub's Linux machines, the Chrome facts that design draft 9 rests
on (the points marked *17d* in section 6), before the Chrome tool is built. The frontier re-check of draft 8 found
that a request Chrome has paused can slip out if control ends in the instant before the tool fails it, that Chrome
updates and starts service workers by itself, that a site guard could end while an offline app still holds Claude's
work, and that the bytes of uploads can't be compared at the network stage. Draft 9's answer is a **floor**: Chrome's
own blocking rules (`declarativeNetRequest`) block every request that isn't plain reading, and every new live
connection, on guarded sites and in Claude tabs, before the request starts and without the extension's code running.
This check finds out whether that floor really holds, where it doesn't, and what it costs. Same evidence standard as
briefs 17 to 17c. A check, not the product: the code may be rough, but it must really run, and the report is the
deliverable.

## Background (read first)

- The design: `git show origin/council/2026-11-07-control-layer:docs/design/CONTROL.md`, section 6 (draft 9), and the
  re-check that led to it: `…:reviews/control-design/2026-11-07-RECHECK-6.md`.
- Briefs 17b and 17c, their reports (`reviews/17b-chrome-holds/REPORT.md` on `origin/pkg/17b-chrome-holds`,
  `reviews/17c-chrome-pages/REPORT.md` on this branch) and their code under `control/checks/`. This branch starts
  from 17c's final head; build on its runner, extension, fixtures and receiver audit.

## Questions to answer, each with evidence (in this order of priority)

**Q1. The floor acts before the request stage.** With the floor's rules in place (dynamic rules matched by the
requesting site for a guarded site, session rules for a Claude tab; methods other than GET and HEAD, plus WebSocket
and WebTransport handshakes) and the tool's request-stage gate also enabled: does a request the rules block ever
reach the request stage, and does ending control at any moment (debugger detach, extension reload, update, policy
blocking, the extension's worker crashing, native host loss, Chrome closed or killed) ever let a blocked request out?
Prove with the fixture server's own log: zero arrivals. Include form posts (top-level navigation), `fetch`, XHR,
beacons, link pings, cross-site destinations from the guarded site, and frames of another site inside a Claude tab.

**Q2. Browser start.** With a guarded site in the dynamic rules and Chrome restarted (normal close, and killed): a
restored tab whose page sends a POST as its very first act, a restored page sending to another site, and requests
of workers without a tab. Zero arrivals before the tool has attached; say exactly when the rules apply relative to
the first request.

**Q3. Workers Chrome starts or updates by itself.** On a guarded site, with no page attached where possible: a
service worker update triggered by navigation and by `registration.update()`, a replaced worker, a worker started by
a background sync firing, by a navigation, and by a push if it can be triggered without the tool's own debugger; a
new shared worker. Each sends a POST and opens a WebSocket in its first lines. Zero arrivals and zero opened
connections. Also: does a WebSocket handshake from a worker carry no tab id, so an allowance for reached tabs never
covers it?

**Q4. The one-time allowance.** An approved send passes through a higher-priority allow rule for exactly that address
and method from that tab or site, removed at its first match; the gate then checks body and page-set headers. Show:
exactly one arrival; a second identical request refused; a different body to the same address failed by the gate;
whether the allowance survives extension reload, update, policy blocking and a worker crash (it must not), and
whether the extension removes leftovers at its own start. Measure the window between adding the allowance and its
match, and what happens to a different-body request in that window when control ends inside it (the instant draft 9
names): how long, how reproducible, and any way to close it.

**Q5. What the tool can see of a request the floor blocked,** and what the page wrap can freeze: JSON, form-encoded,
multipart with a file, a 1 MB and a 25 MB body, and a streaming body. For each: complete bytes or not (through the
debugger's network events and through the wrap), and the size limits. Missing bytes must be reported as missing,
never as an empty body.

**Q6. Evidence that nothing of Claude's was left behind.** Which of these writes Chrome reports to the debugger, from
pages and from workers, and how fast: web storage, IndexedDB, Cache Storage, cookies set by a script, the origin's
private file system, background sync and periodic sync registrations, service worker registrations; and which hand-
offs it reports at all (broadcast channel, `postMessage` to another window or a worker, a shared worker's port).
Where Chrome reports nothing, can the page script see it? A fixture offline app that records a deletion in IndexedDB
after Claude's click, makes no request, and sends it later from another tab: the evidence must show the write.

**Q7. How it feels with the floor on.** On a guarded fixture site with the floor and the tool attached: the owner's
own send held in the page, put to him on the notification and released once through an allowance; the page's own
background posts blocked and listed; a new WebSocket from a reached tab opens and its messages are held by the wrap;
one from a shared or service worker is refused. On the public sites of brief 17c (same safety rules: no sign-in,
nothing submitted): what breaks visibly when the floor is on for that site, at rest and after a few reading clicks.

**Q8. Account changes while a send waits.** What the tool can see (cookies of the site, the page's signed-in name)
to refuse a release after a sign-out and sign-in as someone else between hold and release, on a fixture.

## In scope

- Code under `control/checks/17d-chrome/` (or extend `control/checks/17c-chrome/`), marked as a check, not product
  code.
- `.github/workflows/control-chrome-check.yml`: add this branch to its triggers; same rules as brief 17c (branded
  Chrome stable from Google's package, version printed, headed under a virtual display, at most 30 minutes per job,
  artifacts uploaded, split into jobs as needed).
- `reviews/17d-chrome-floor/REPORT.md` (format below).

## Out of scope

- Never start, read or touch Chrome, Chromium or any browser profile on this Mac. Every browser run happens on
  GitHub's Linux machines.
- Real accounts, logins on real sites, or sending anything to a real site.
- Anything under `os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, and the design and
  plan files (`docs/design/`, `docs/control/`): proposals go in the report.
- The product: the MCP server, the CLI, the tool service.

## Acceptance

- Every claim in the report is marked **run** (workflow run ID and log line or artifact), **read** (source URL and
  version) or **assumed**.
- Every blocking and allowance case is proven with the fixture server's own log.
- The final workflow passes twice on the final head.
- Synthetic data only; no secrets, real addresses or account names.

## Report format (`reviews/17d-chrome-floor/REPORT.md`)

- **Answer in five lines:** does the floor hold, and where doesn't it?
- **Q1 to Q8:** findings with evidence.
- **Changes for the design:** for each *17d* point in `CONTROL.md` section 6, what the design should say now.
- **Risks** and **PLAN-GAP**s.
- **JUDGMENT-CALL:** choices that change how it feels for the owner.
- **Not checked** and why.

## Already decided

- The owner's decisions of 2026-11-07 in `PLAN.md`, and design draft 9 section 6. No debugging port, Chrome's own
  sandbox on, the extension installed by policy without the `management` permission.
- A held send must never go out because control broke.

## If unsure

Take the option that keeps the owner's data from leaving without approval, and say so in the report.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook, and the work happens on GitHub's Linux runners).
- Work only in this worktree, on branch `pkg/17d-chrome-floor`. Commit in small steps, push this branch, open a draft
  PR against `main` with `gh pr create --draft`, and say in it that it builds on PRs #3, #4 and #7. Never merge, never
  push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Keep it to about 20 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: the same exploratory, CI-heavy Chrome work as briefs 17 to 17c, which it did well.
