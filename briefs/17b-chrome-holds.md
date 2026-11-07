# 17b: Chrome check, part two: holds that can't leak

**Goal:** settle, with evidence from real runs on GitHub's Linux machines, the points the Chrome design still
depends on: holding that fails closed when control breaks, service workers, long holds, live connections, the
typed-text rule, installing the extension by policy, and the Claude tab group. Same evidence standard as brief 17.
This is a check, not the product: the code may be rough, but it must really run, and the report is the deliverable.

## Background (read first)

- Brief 17's report on this branch: `reviews/17-chrome-check/REPORT.md`, and its code in `control/checks/17-chrome/`.
  This branch starts from brief 17's final head; build on that code.
- The design these answers feed: `git show origin/council/2026-11-07-control-layer:docs/design/CONTROL.md`,
  section 6 (Chrome). Every point marked *17b* there is a question here.
- The plan and the owner's picture, on the same council branch (read with `git show` as above):
  `docs/control/PLAN.md` and `reviews/councils/2026-11-07-control-layer/OWNER-SCOPE.md`.

In short: the tool is our own Manifest V3 extension using `chrome.debugger`, talking to the tool service through a
native messaging host. It holds every request the controlled tab makes at Chrome's request stage, and anything that
sends data waits until the owner approves it through Claude Code's permission prompt, possibly minutes later on his
phone. Brief 17 showed the hold works for ordinary HTTP sends, but a disconnect released a held request, a service
worker's own request was not held, and WebSocket messages pass by. **Only the native-messaging extension route is
in scope now**; the Playwright and consent routes are settled.

## Questions to answer, each with evidence (in this order of priority)

**Q1. Fail closed.** For each way control can end while a request is held, record with the fixture server's own log
whether the held request ever arrives:

1. the native host process dies,
2. the service side closes its socket,
3. the extension's service worker is stopped and restarted,
4. the extension is disabled, reloaded, or updated to a new version through the install route of Q5,
5. the owner presses Cancel on Chrome's debugging bar,
6. DevTools is opened on the tab,
7. the tab is closed,
8. Chrome is closed normally, and Chrome is killed.

Then make the extension fail closed where it can (for example keep the debugger attached and fail held requests
when the native port is lost). For the paths it can't control, test a backstop: for example a `declarativeNetRequest`
session rule the extension adds for the exact held request (tab, method, address) before it reports the hold. Find
out by running whether such a rule still blocks a request that was paused in the DevTools hold and continued by
Chrome on detach, and whether it blocks the release you want. If no backstop holds, test **fail, then repeat**: the
request is failed at once and shown; after approval, the triggering action is done again and exactly one matching
request is let through. Report how often the repeated request matches the first, byte for byte and after ignoring
named volatile fields, on the fixtures and on the public demo form from brief 17 (synthetic data, aborted at the
gate, nothing sent).

**Q2. Service workers.** Fixtures:

1. a page whose `fetch`, XHR and form posts pass through its service worker's fetch handler (the common case),
2. a service worker that sends by itself after a `postMessage`,
3. background sync, if Linux Chrome offers it.

Test through `chrome.debugger`: attaching to the worker's own target (by target id, or with `Target.setAutoAttach`
and child sessions) and holding its requests there; and `Network.setBypassServiceWorker` on the controlled tab. For
each case: held before it leaves, released once, dropped cleanly, and what breaks on the page. Note what
Playwright's documentation says about routing and service workers (cite the version).

**Q3. Long holds.** Hold for 30 seconds, 2 minutes and once for 10 minutes. Does the request still go out exactly once
after release? Does Chrome time a paused request out? What do pages do while waiting: a posted form, `fetch` with
`AbortSignal.timeout(30000)`, XHR with a timeout, and a page that retries by itself after a timeout? A retry must
show up as a second held request, and the tool must never send both by accident.

**Q4. Live connections and the typed-text rule.**

- (a) Per document, can the tool tell that a live connection is open: WebSocket (also one opened **before** the tool
  attached), WebTransport, a WebRTC data channel? Report what can and can't be detected.
- (b) Does the request hold see a WebSocket's opening handshake, and can holding it stop the connection cleanly?
- (c) The typed-text rule: text the tool typed into the page is found in outgoing requests as typed, URL-encoded,
  form-encoded, JSON-escaped and base64. Fixtures: autosave after a 5-second pause, an "undo send" delay of 10
  seconds, a GET image carrying the text. Then run the rule on brief 17's three public sites (no login, synthetic text,
  every request that would carry the text aborted at the gate): report false alarms and misses.
- (d) The settle window from the design (no new requests for half a second, at most ten seconds): measure on the
  fixtures and the public sites how often an action's own send starts outside it.

**Q5. Install and the tab group.**

- (a) Install the extension through `ExtensionInstallForcelist` in `/etc/opt/chrome/policies/managed/` with a
  self-hosted update manifest served locally in CI. Does branded Linux Chrome accept it? Can the user disable or
  remove it? Does a new version arrive through the update manifest? Is the debugging bar still shown? Also block
  Claude in Chrome's extension with `ExtensionInstallBlocklist` (find its ID from a primary source).
- (b) Native messaging hosts: with the same host name registered system-wide and in the user's own config folder,
  which one does Chrome start? Test the `NativeMessagingUserLevelHosts` policy set to false. A user-level manifest must
  not be able to replace the system one.
- (c) The Claude tab group: the extension opens tabs in a group named "Claude", moves an existing tab into it, and
  reads and acts only inside it. The owner drags a tab out of the group, or closes the group: control of that tab
  ends cleanly, and anything held follows Q1's fail-closed rule.

## In scope

- Code under `control/checks/17-chrome/` (extend it) or `control/checks/17b-chrome/`, marked as a check, not product
  code.
- `.github/workflows/control-chrome-check.yml`: add this branch to its triggers; same rules as brief 17 (branded
  Chrome stable from Google's package, version printed, headed under a virtual display, 30-minute cap per job,
  artifacts uploaded). Split into jobs if the long holds need it.
- `reviews/17b-chrome-holds/REPORT.md` (format below).

## Out of scope

- Never start, read or touch Chrome, Chromium or any browser profile on this Mac. Every browser run happens on
  GitHub's Linux machines.
- Real accounts, logins on real sites, or sending anything to a real site.
- Anything under `os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, and the design and
  plan files (`docs/design/`, `docs/control/`): proposals for them go in the report.
- The product: the MCP server, the CLI, the tool service.

## Acceptance

- Every claim in the report is marked **run** (workflow run ID and log line or artifact), **read** (source URL and
  version) or **assumed**.
- Every hold and fail-closed case is proven with the fixture server's own log: no arrival while held, exactly one
  after release, none after drop or after control ended.
- The final workflow passes twice on the final head.
- Synthetic data only; no secrets, real addresses or account names.

## Report format (`reviews/17b-chrome-holds/REPORT.md`)

- **Answer in five lines.**
- **Q1 to Q5:** findings with evidence.
- **Changes for the design:** for each *17b* point in `CONTROL.md` section 6, what the design should say now.
- **Risks** and **PLAN-GAP**s.
- **JUDGMENT-CALL:** choices that change how it feels for the owner.
- **Not checked** and why.

## Already decided

- The owner's decisions of 2026-11-07 in `PLAN.md`. Brief 17's rejections stand: no debugging port on the owner's
  profile, Chrome's own sandbox on, Chrome's consent attach rejected.
- Branded Chrome stable is the target.
- A held send must never go out because control broke. A route that can't guarantee that is reported as such, with
  the gap named.

## If unsure

Take the option that keeps the owner's data from leaving without approval, and say so in the report.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook, and the work happens on GitHub's Linux runners).
- Work only in this worktree, on branch `pkg/17b-chrome-holds`. Commit in small steps, push this branch, open a draft
  PR against `main` with `gh pr create --draft`, and say in it that it builds on PR #3. Never merge, never push to
  `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Keep it to about 15 workflow runs; the 10-minute hold runs once, in the final runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: the same exploratory, CI-heavy work as brief 17, which it did well. The frontier
model is kept for the design review running at the same time.
