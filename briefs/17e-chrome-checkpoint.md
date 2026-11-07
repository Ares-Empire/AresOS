# 17e: Chrome check, part five: a local checkpoint outside Chrome

**Goal:** settle, with evidence from real runs on GitHub's Linux machines, whether a **local checkpoint** (an
intercepting proxy owned by the tool service, outside Chrome) can be the send boundary that Chrome's own blocking
rules could not be, and what it costs. Brief 17d showed that Chrome's rules don't hold: WebSockets opened by shared
and service workers bypass every extension rule, and a different send that matches an approved send's allowance
escapes when control ends while it is paused. The frontier re-check 7 recommends this checkpoint (its option B1) and
lists eleven questions it must answer first. This check answers them. Same evidence standard as briefs 17 to 17d. A
check, not the product: the code may be rough, but it must really run, and the report is the deliverable. The owner
is deciding (board #68) whether he accepts a checkpoint that decrypts his browser traffic on his machine; this
report gives him the costs (robot checks, speed, what breaks) in plain numbers.

## Background (read first)

- The re-check that leads here: `git show origin/council/2026-11-07-control-layer:reviews/control-design/2026-11-07-RECHECK-7.md`
  (**its section C is this brief's question list**; the reasons for each requirement are there). The earlier one:
  `…:reviews/control-design/2026-11-07-RECHECK-6.md`.
- The design as it stands: `git show origin/council/2026-11-07-control-layer:docs/design/CONTROL.md`, section 6
  (draft 9; its floor is what 17d disproved). Owner's picture:
  `…:reviews/councils/2026-11-07-control-layer/OWNER-SCOPE.md`.
- Briefs 17b to 17d, their reports (`reviews/17*-chrome-*/REPORT.md`) and their code under `control/checks/`. This
  branch starts from 17d's final head; build on its runner, extension, fixtures, receiver audit, HTTP/3 receiver,
  file-picker and notification helpers.

## The checkpoint under test

- One fixed proxy set by Chrome policy (`ProxySettings`: fixed servers, no `DIRECT`, `<-loopback>` so localhost and
  link-local aren't bypassed), the local root installed by policy (`CACertificates`), its key readable only by the
  checkpoint's own user. **Plus routing enforced by the OS**, so Chrome's processes can reach nothing but the
  checkpoint even if the proxy setting were ignored. Pick a mechanism that would work for a desktop-launched Chrome
  on a Fedora-based image (for example an nftables match on Chrome's cgroup, or Chrome in its own network
  namespace), show it on the runner, and say why it would carry over.
- It decrypts **from browser start**, continuously; it validates upstream TLS itself.
- It **holds the complete operation** (request line, headers and body; for WebSockets the handshake, each data
  message and a close frame with a payload) from a guarded site, and on approval **forwards exactly that captured
  operation once**, after durably recording the consumption. There are no URL allowances.
- Attribution: a per-tab header added by `declarativeNetRequest` `modifyHeaders` and stripped by the checkpoint is
  supporting evidence only (overwrite it, bind it to the browser and document generation, test forgery and stale
  reuse). Missing or uncertain attribution holds traffic that may be guarded, whatever its destination.
- Use a well-tried intercepting proxy as the base (mitmproxy pinned, or another with a reason) rather than writing
  TLS and HTTP/2 handling by hand. The report recommends what brief 20 should build on, with the evidence.

## Questions (re-check 7, section C; answer each with independent receiver logs and positive controls)

1. **Bypass.** IPv4 and IPv6, localhost and link-local, redirects, page and worker traffic, QUIC, and the checkpoint
   being down. *Pass:* no direct delivery to any receiver; a restored Chrome can't transmit before the persisted
   guards are loaded; with the checkpoint down, browsing fails visibly with no direct fallback.
2. **Connections opened before a guard starts.** Pre-open HTTP/2 connections and page, shared- and service-worker
   WebSockets; start a guard during concurrent traffic. *Pass:* no unapproved operation escapes after the guard
   starts; Claude's input begins only after the checkpoint acknowledges the barrier.
3. **Attribution stays conservative.** Opaque and absent `Origin`, frames of another site, cross-origin hand-offs,
   redirects, forged, stale and missing headers, the extension removed. *Pass:* uncertainty widens what is held or
   refuses input; it never releases anything.
4. **Complete operations are held.** Multipart with a disk file (17d's real file picker), binary bodies, chunked and
   compressed bodies, fragmented WebSocket messages, close reasons, a 25 MiB body. *Pass:* zero operation bytes
   upstream before approval; the approved payload's hash matches at the receiver; incomplete or oversized input
   fails closed and says so.
5. **Approval can't be taken by another request.** Race identical and different bodies, headers, accounts and
   documents against an approved operation. *Pass:* the approval names one captured operation; competitors stay
   held; a changed context needs a new approval.
6. **Every crash point.** Kill the extension, native host, checkpoint and browser before and after the durable
   consumption and during forwarding. *Pass:* zero unapproved arrivals; nothing is replayed on recovery; an
   operation whose outcome is uncertain is reported as unknown.
7. **Cancellation.** `AbortSignal`, an HTTP/2 stream reset, the tab closed, the page's own timeout, an approval that
   comes late. *Pass:* a cancellation seen before forwarding prevents delivery; cancellations the checkpoint can't
   see are listed as unsupported, never guessed.
8. **Other transports.** A working WebTransport peer (17d's HTTP/3 receiver) and WebRTC data channels with a local
   TURN server over TCP and TLS. *Pass:* no unapproved payload arrives; blocked transports show as unavailable to
   the page.
9. **TLS stays sound.** The policy root, HSTS, a pinned destination, an invalid upstream certificate, and Chrome's
   own services (Safe Browsing, component and extension updates; sync and push as far as they can run without an
   account). *Pass:* supported traffic works without certificate errors; an invalid upstream certificate fails;
   no exception made for a Chrome service can carry a page's send.
10. **Guards end only on evidence.** Replay 17d's offline outbox, named-property storage, OPFS, hand-offs and a
    browser restart with the checkpoint in place. *Pass:* positive or incomplete evidence keeps the guard; only a
    resolution shown independently ends it.
11. **What it costs the owner.** On the ten public sites of briefs 17c and 17d (same safety rules: no sign-in,
    nothing typed or submitted), with and without the checkpoint in the same run: pages that load, robot checks and
    blocks, page-load time; the checkpoint's CPU and memory; its TLS and HTTP/2 fingerprint compared with Chrome's
    own (a public fingerprint echo page is fine to load); a synthetic signed-in fixture app with background traffic
    and a live connection, counting what the owner would be asked while a guard is on. Logs contain no cookies,
    passwords or bodies; buffers stay bounded; running out of memory or disk never lets anything through.

## In scope

- Code under `control/checks/17e-chrome/`, marked as a check, not product code.
- `.github/workflows/control-chrome-check.yml`: add this branch to its triggers; same rules as brief 17d (branded
  Chrome stable from Google's package, version printed, headed under a virtual display, at most 30 minutes per job,
  artifacts uploaded, split into jobs as needed). Pin every container and package you add (TURN server, proxy).
- `reviews/17e-chrome-checkpoint/REPORT.md` (format below).

## Out of scope

- Never start, read or touch Chrome, Chromium or any browser profile on this Mac. Every browser run happens on
  GitHub's Linux machines.
- Real accounts, logins on real sites, typing into or sending anything to a real site.
- Anything under `os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, and the design and
  plan files (`docs/design/`, `docs/control/`): proposals go in the report.
- The product: the MCP server, the CLI, the tool service.

## Acceptance

- Every claim in the report is marked **run** (workflow run ID and log line or artifact), **read** (source URL and
  version) or **assumed**.
- Every hold, release, crash and bypass case is proven with the fixture receivers' own logs, with a positive control
  showing the same case delivers when nothing holds it.
- The final workflow passes twice on the final head.
- Synthetic data only; no secrets, real addresses or account names.

## Report format (`reviews/17e-chrome-checkpoint/REPORT.md`)

- **Answer in five lines:** does the checkpoint hold, where doesn't it, and what does it cost the owner?
- **Q1 to Q11:** findings with evidence, each with its pass condition met or not.
- **What the owner would notice:** robot checks, speed, what stops working, what he'd be asked, in plain words.
- **Changes for the design:** what section 6 should say now (the checkpoint replacing the floor; what stays of the
  in-page hold, the extension and the guard), and what brief 20 should build on.
- **Risks** and **PLAN-GAP**s.
- **JUDGMENT-CALL:** choices that change how it feels for the owner.
- **Not checked** and why.

## Already decided

- The owner's decisions of 2026-11-07 in `PLAN.md`, and design draft 9 section 6 except its floor. No debugging
  port, Chrome's own sandbox on, the extension installed by policy without the `management` permission. Claude runs
  as an unprivileged user and can't change root-owned policy.
- A held send must never go out because control broke. Forwarding is at most once; nothing is replayed by itself.

## If unsure

Take the option that keeps the owner's data from leaving without approval, and say so in the report.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook, and the work happens on GitHub's Linux runners).
- Work only in this worktree, on branch `pkg/17e-chrome-checkpoint`. Commit in small steps, push this branch, open a
  draft PR against `main` with `gh pr create --draft`, and say in it that it builds on PRs #3, #4, #7 and #8. Never
  merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Keep it to about 25 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: the same exploratory, CI-heavy Chrome work as briefs 17 to 17d, which it did well.
The checkpoint adds TLS, HTTP/2 and routing work of the same kind.
