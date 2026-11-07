# 17c: Chrome check, part three: holding in the page, guarded sites, everyday sites

**Goal:** settle, with evidence from real runs on GitHub's Linux machines, the last Chrome questions before the
Chrome tool is built (the points marked *17c* in the design). Most important: can a send be held **inside the page**,
so that an honest page simply waits for the owner's approval and nothing can leak when the extension stops; and how
do everyday sites behave under the design's rules. Same evidence standard as briefs 17 and 17b. A check, not the
product: the code may be rough, but it must really run, and the report is the deliverable.

## Background (read first)

- Briefs 17 and 17b and their reports on this branch (`reviews/17-chrome-check/REPORT.md`,
  `reviews/17b-chrome-holds/REPORT.md`) and their code under `control/checks/`. This branch starts from 17b's final
  head; build on that code.
- The design: `git show origin/council/2026-11-07-control-layer:docs/design/CONTROL.md`, section 6 (draft 7). Its
  rules: nothing Claude caused or entered leaves without approval; once Claude has acted on a page, everything it
  sends that isn't plain reading is held; sites Claude acted on are *guarded* across tabs, workers and restarts; the
  owner's own sends on a guarded site are confirmed by him on a desktop notification and the extension's own details
  page, never inside the page; the baseline hold is "fail, then repeat".
- The design reviews on the same branch (`reviews/control-design/2026-11-07-*.md`): RECHECK-3 lists conditions this
  check carries (startup and restored-tab traffic, shared queues, the owner's click flushing Claude's queue, guard
  retirement only on evidence).

## Questions to answer, each with evidence (in this order of priority)

**Q1. Holding inside the page.** Wrap the page's own send functions before any page script runs, in every document,
every frame (including `about:blank` and `srcdoc` frames a script creates) and every worker (dedicated, shared,
service; caught before their first script): `fetch`, `XMLHttpRequest.send`, `navigator.sendBeacon`, form submission
(the submit event and `submit()`/`requestSubmit()`), `WebSocket.send`, `RTCDataChannel.send`, WebTransport writers.
A held call creates no request until approval; release performs exactly that call once. Prove with the fixture
server's own log:

- while held: zero arrivals; after release: exactly one; after drop: none;
- when control ends while a call is held (reload, update, disable, detach, the Stop button, host loss, Chrome
  closed): none;
- on a hostile fixture page that tries to get around the wrap (an original function taken from a fresh frame, a
  worker from a blob address, tampering with prototypes, checking `toString`): every send it manages is caught by
  the network-level gate (fail, then repeat) with zero arrivals before approval;
- what honest fixture pages and the public demo form from brief 17 show while a call is held (aborted, nothing sent).

**Q2. Which live-connection messages count as sends.** A chat fixture that sends presence, typing and subscription
messages on ordinary clicks, and the message itself on Enter. Count what would be held under (a) only messages
carrying Claude's typed text, (b) every message after Claude acted on the page. A tab taken from the owner with a
connection opened before the tool attached (17b's inventory finds it): show that reloading brings the wrap in, and
what the tool must refuse until then.

**Q3. Acting, guarding and the owner's own clicks.** Fixtures:

1. a timer the page set when it loaded flushes a queue that Claude's click filled (must be held);
2. the owner's own click in another tab of the same site flushes Claude's queue: held, and put to the owner through
   `chrome.notifications` buttons and the extension's own details page;
3. forged decisions from the page, a content script and another extension page are refused; the genuine owner's
   decision works;
4. taking or opening an extension page or a Chrome page is refused;
5. the guard list kept in `chrome.storage.local` survives a browser restart, and the guard attaches before the first
   request of restored tabs and of the site's service worker;
6. the guard ends only on evidence or by the owner.

**Q4. Tracing causes.** Follow each request's initiator, including asynchronous chains (timers, promises, mutation
observers, `postMessage`, workers), back to the input Claude dispatched. On fixtures for each kind: how often a
request is attributed correctly, and never a request of Claude's attributed to the page.

**Q5. Everyday sites.** Without logging in and submitting nothing (every request that would send is aborted at the
gate): ten public sites. Use the owner's list in the section below if it is filled in; otherwise a public GitHub
repository page, Wikipedia, YouTube, a news site, an Amazon product page, Reddit, Stack Overflow, a public Notion
page, a public Google Docs document and Google search. For each: at rest and after a few reading clicks (a tab, an
expand button, the next page): open live connections, service workers, reading through POST (and GraphQL), how much
background traffic the hold-after-acting rule would hold, whether the page still works with the in-page hold, and
whether a send there would repeat exactly under fail-then-repeat. Add published statistics (for example the HTTP
Archive's Web Almanac) on how common service workers, WebSockets and GraphQL are, with sources and dates. Verdict per
site: works smoothly / asks often / needs a site adapter.

**Q6. The owner's stop control.** The extension's badge, the group's colour and the popup's Stop button: Stop fails
everything held, then ends control; nothing is sent.

## The owner's usual sites

(Filled in by the lead before launch if the owner has named them; otherwise use the list in Q5.)

## In scope

- Code under `control/checks/17c-chrome/` (or extend `control/checks/17b-chrome/`), marked as a check, not product
  code.
- `.github/workflows/control-chrome-check.yml`: add this branch to its triggers; same rules as brief 17b (branded
  Chrome stable from Google's package, version printed, headed under a virtual display, at most 30 minutes per job,
  artifacts uploaded, split into jobs as needed).
- `reviews/17c-chrome-pages/REPORT.md` (format below).

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
- Every hold case is proven with the fixture server's own log: none while held, exactly one after release, none after
  drop or after control ended.
- The final workflow passes twice on the final head.
- Synthetic data only; no secrets, real addresses or account names.

## Report format (`reviews/17c-chrome-pages/REPORT.md`)

- **Answer in five lines.**
- **Q1 to Q6:** findings with evidence.
- **Changes for the design:** for each *17c* point in `CONTROL.md` section 6, what the design should say now, and
  whether the in-page hold can replace fail-then-repeat as the normal path on honest sites.
- **Risks** and **PLAN-GAP**s.
- **JUDGMENT-CALL:** choices that change how it feels for the owner.
- **Not checked** and why.

## Already decided

- The owner's decisions of 2026-11-07 in `PLAN.md`, and design draft 7 section 6. No debugging port, Chrome's own
  sandbox on, the extension installed by policy without the `management` permission.
- A held send must never go out because control broke.

## If unsure

Take the option that keeps the owner's data from leaving without approval, and say so in the report.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook, and the work happens on GitHub's Linux runners).
- Work only in this worktree, on branch `pkg/17c-chrome-pages`. Commit in small steps, push this branch, open a draft
  PR against `main` with `gh pr create --draft`, and say in it that it builds on PRs #3 and #4. Never merge, never
  push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Keep it to about 20 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: the same exploratory, CI-heavy work as briefs 17 and 17b, which it did well.
