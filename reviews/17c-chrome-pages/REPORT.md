# 17c: Chrome pages

## Answer in five lines

1. **run [R]** Honest fixture calls can wait inside the page, with zero receiver arrivals while held, one after release and none after drop; this improves the waiting experience.
2. **run [R]** This is not a universal send boundary: a deliberately unwrapped live message reaches the receiver, and initial shared/service-worker coverage is incomplete.
3. **run [R]** Shared outboxes require a site guard even for the owner's clicks; protected details and real desktop notification decisions work, and forged decisions are refused.
4. **run [R]** Initiator tracing recognises five of six input chains; the worker chain remains unknown and held. Restored documents start before debugger attachment, although their cooperative sends are held.
5. **assumed — recommendation:** retain fail-then-repeat and refuse input where coverage is unknown; offer in-page waiting only on qualified contexts, with adapters for opaque operations and POST reads.

[R]: https://github.com/Ares-Empire/AresOS/actions/runs/42355697966

## Evidence and limits

**run [R]** Qualification head: `589c53bd31cf4a230424fcc147ead0bf8289c8f3`, branded Google Chrome `157.0.8103.38`, headed under Xvfb/Openbox on GitHub Linux. Artifacts `chrome-check-42355697966-1-{pages,guards,public}` contain version/head/dependency metadata, `check.log`, `summary.json`, the independent fixture `server.jsonl`, `delivery-audit.json`, worker/initiator events and screenshots. Each job finishes with `FINAL_DELIVERY_AUDIT ... PASS` and `ALL 17C CHECKS COMPLETE`. The final independent audits cover **100 page/lifecycle** and **36 guarded-site** case IDs, and also refuse any unregistered receiver delivery. Selected immutable measurements and receiver logs are retained in [records](records/).

**run — final-head ledger:** [draft PR #7](https://github.com/Ares-Empire/AresOS/pull/7) records the exact final commit and two successful executions of all three jobs. The report/evidence commit follows [R] and corrects screenshot foregrounding; the PR description is updated after those executions without another commit, avoiding a report/head reference cycle. Earlier failed or cancelled runs in `records/workflow-runs.json` are harness iterations, not final capability evidence. Passing this check reproduces negative findings too; it does not certify the product.

**read — this check's source:** [runner](../../control/checks/17c-chrome/run.mjs), [extension](../../control/checks/17c-chrome/extension/background.js), [wrapper](../../control/checks/17c-chrome/extension/wrap.js), [fixtures](../../control/checks/17c-chrome/fixture.mjs) and [workflow](../../.github/workflows/control-chrome-check.yml). CI runs `npm ci --ignore-scripts --no-audit --no-fund`, installs `aioquic==1.3.0` in a disposable venv, then runs `timeout --kill-after=15s 25m node control/checks/17c-chrome/run.mjs` under `dbus-run-session`, Xvfb, Openbox and Dunst. Every job has a 30-minute cap. The policy-installed extension has no `management` permission; native messaging uses the existing private Unix-socket relay. No debugging port/pipe or `--no-sandbox` is used (`processes.json`, version/head files, sandbox screenshot).

**run — local verification:** `node --check` passed for all ten JavaScript files; deliberately invoking the runner on the Mac returned exit 1 with `Browser runs only on GitHub Linux runners` before browser setup. `git diff --check` passed. No local browser/profile was started, inspected or changed. No Gradle daemon was started. The final `.work/` inventory contains no file over 500 MB.

**read — experimental boundaries:** raw runner RPC, a page-visible queue/test handle, origin-only loopback guards, a fixed owner-tab label and synthetic adapter evidence are deliberate shortcuts. The check is not an MCP service, an input-origin classifier, a Public Suffix List implementation or a same-UID security boundary. Retained state omits the generated public manifest key. Public observations truncate payload previews to 2,000 characters and retained records remove query strings and long opaque path segments; they are not approval descriptions.

## Q1. Holding inside the page

**run [R] — `Q1_HOLD`, `Q1_WRITER` and final receiver audit:**

| Call exercised | Held / released / dropped | Honest page result |
|---|---|---|
| Fetch POST | 0 / 1 / 0 | Promise waits; success after release; AbortError after drop. |
| XHR send | 0 / 1 / 0 | Waiting state; load after release; this prototype gives no error event on drop. |
| Beacon | 0 / 1 / 0 | Returns true while queued; the API has no later completion signal. |
| Form `submit()`, `requestSubmit()`, button/submit event | 0 / 1 / 0 each | Original page stays visible while held; navigation starts only after release. |
| WebSocket send | 0 / 1 / 0 | Connection opens, message waits. |
| RTC data-channel send | 0 / 1 / 0 | Peer receipt is forwarded by the fixture to the HTTP receiver log. |
| WebTransport datagram writer | 0 / 1 / 0 | Independent aioquic receiver records the released datagram. |

**run [R]** The `Q1_HOLD` before/after DOM snapshots preserve the waiting/error/completion states. The qualification run’s early waiting PNGs show the selection tab instead and are excluded from the retained screenshots; the final head corrects foregrounding before capture. Duplicate decisions are refused. AbortSignal expiry, changed form fields and a stale document's queued call are refused with zero arrivals (`Q1_ABORT`, `Q1_CHANGED_FORM`, `Q1_DOCUMENT_ID`). Document IDs prevent an old local call ID from releasing a new document's call. A GET XHR and an unrelated local WritableStream complete without a held call (`Q1_PLAIN_READ_AND_LOCAL_STREAM`). Bodies in the send fixtures are strings/byte arrays; other mutable bodies and stream semantics are not qualified.

**run [R]** Same-origin, cross-origin, initial `about:blank` and `srcdoc` frames each hold, release once and drop without delivery (`Q1_FRAME`, `Q1_CROSS_FRAME`). Main-world `document_start`, `all_frames` and origin fallback are used. These four fixtures do not establish coverage of every sandboxed, opaque or nested frame configuration.

**run [R]** `Q1_END` holds fetch, XHR, beacon, form, WS, RTC and WebTransport calls together, then exercises page reload, debugger detach, the action popup's Stop button, extension reload, policy update, native-host kill, normal Chrome close (UI close, with a SIGTERM fallback if still running), Chrome kill and policy blocking of the extension. All held case IDs remain absent through final shutdown. `Q1_UPDATE_REQUEST` plus a connection as 0.3.1 confirms the update; `Q1_DISABLE_EVIDENCE` confirms the blocked extension really disconnected. This is administrative policy blocking, not an owner disabling a forced extension in Chrome's UI.

**run [R]** Hostile HTTP fixtures restore a saved original, obtain a fresh frame function, restore `XMLHttpRequest.prototype.send`, inspect `toString`, or start a blob worker. Calls caught in the page remain queued; HTTP bypasses fail immediately at the network gate, with zero arrivals (`Q1_HOSTILE_HTTP`). `Q1_FAIL_REPEAT` then approves one exact method/URL/body/header-hash repeat, delivers once and refuses the duplicate. No field is ignored.

**run [R] — counterexample:** `Q1_HOSTILE_LIVE_COUNTEREXAMPLE` deliberately restores the saved native WS send on its prototype and delivers one message without approval. The test handle exposes that native reference intentionally; this does not prove every hidden-closure implementation can be bypassed in the same way. It does prove that the tested network fallback does not catch an unwrapped live message. The requested “every bypass is caught by the network gate” claim is false for this prototype.

**run [R] — worker qualification:** `Q1_WORKER_START` injects before the dedicated worker's first script and holds its fetch; `Q1_DEDICATED_MESSAGE` also releases and drops its later messages with zero/one/zero receiver counts. Shared-worker startup is missed; new service-worker setup reaches the three-second `Runtime.enable` deadline and is resumed for observation, after which its first send arrives. `Q1_REPLACEMENT_SINGLE_ROOT` repeats replacement with only one attaching page and also observes one unheld startup send. `Q1_DIRECT_WORKER` proves zero/one/zero after attaching directly to the already-running shared and service workers. `Q3_SHARED_QUEUE` holds shared-worker outbox work passed between tabs. These are different coverage stages, not interchangeable successes.

**assumed — production consequence:** a setup deadline must refuse the action or keep/terminate the unqualified context, never resume it as this diagnostic probe does. Direct attachment after discovery is too late to justify an early-start guarantee.

**run [R]** The Selenium public demo stays on its original form while held; three synthetic submissions are released only into the aborting gate. Their exposed URL/method/body/header-hash fingerprints match and all are blocked (`Q1_PUBLIC_DEMO`). This qualifies that deterministic demo, not authenticated operations on the ten sites.

## Q2. Which live messages count

**run [R]** `Q2_CHAT`: one ordinary click emits presence, subscription and typing messages; Enter emits the text. Matching only `Synthetic17c` would hold **1 of 4**. Holding every message after acting holds **4 of 4**, all with zero arrivals after drop. The extra three holds are observable cost, not evidence that they are independent of queued Claude effects.

**run [R]** `Q2_PREATTACH` inventories an already-open socket with `Runtime.queryObjects` after reattachment. Its deliberately restored native send still delivers once. Reloading installs the wrapper and the corresponding send is held with zero arrivals.

**assumed — design wording:** inventory establishes that a connection exists, not that every callable reference is wrapped. Until reload and context coverage are qualified, refuse typing, Enter and controls other than plain reading links; use an adapter-backed approved-input path only when account, target and content can be revalidated. This check demonstrates the need; it does not implement that product refusal API.

## Q3. Acting, guarding and the owner's clicks

**run [R]** `Q3_TIMER`: a page-load interval drains an outbox filled by a CDP-dispatched click. The non-text queued deletion is held. Dropping it leaves the durable guard on and cannot satisfy retirement evidence.

**run [R]** `Q3_OWNER_HELD`, `Q3_GENUINE_OWNER`: an actual X click in an ungrouped same-origin owner tab drains the same localStorage queue. Zero arrivals precede the genuine details-page decision; exactly one follows it. `Q3_NOTIFICATION` exercises Dunst's real action menu with X input: Chrome emits `onButtonClicked` button 0 for Send and button 1 for Don't send, producing one and zero arrivals respectively. The [details page](screenshots/owner-details.png) and [notification action menu](screenshots/notification-menu-true.png) preserve the external decision surfaces.

**run [R]** Page messages, the extension's content script, another extension-origin page and an embedded details frame cannot approve the held request; the content script also cannot retire the guard. The exact details URL/extension ID/top-level frame check accepts the genuine owner (`check.forgeryRefused`, including the nonzero-frame sender). Taking the details tab and opening extension/Chrome URLs are refused with `FORBIDDEN_PAGE`. The sandboxed-terminal input boundary belongs to brief 18b and is not tested here.

**run [R]** `Q3_SHARED_QUEUE`: the second tab flushes a shared worker's queue containing the first tab's synthetic effect; direct worker wrapping holds it with zero arrivals. Its worker-target report has no owner-input attribution. The fixture's fixed owner-tab label works for the direct tab flush, not for arbitrary cross-context cause reconstruction.

**run [R]** `Q3_RESTART`: `chrome.storage.local` retains the guard across real Chrome shutdown/restart. The restored `/startup` document's first POST is held by the static content wrapper. Receiver `document` rows and `check.gateReady` timestamps show its first document GET precedes debugger readiness. Therefore persistent storage plus `onStartup` attachment does **not** establish “attached before the first restored request.” `Q3_RESTART_SW` separately activates the installed service worker and records its startup/message sends and held candidates; this does not repair the new/replaced-worker gap.

**run [R]** `Q3_RETIRE` refuses “dropped” as evidence and accepts a synthetic adapter-resolved marker; `Q3_OWNER_RETIRE` exercises the genuine owner's End site guard button. **assumed — limitation:** the marker is a fixture stand-in, not a verifier that an arbitrary site's durable queues are empty. Guard expiry/retirement in the product requires real adapter evidence or the owner; an HTTP rejection is insufficient.

## Q4. Tracing causes

**run [R] — `Q4_CAUSES`, async stack depth 32 with parent stack-ID resolution:**

| Ground-truth input chain | Correctly traced to `action17c` | Classified as the page's own |
|---|---:|---:|
| Synchronous handler | 1/1 | 0 |
| Timer | 1/1 | 0 |
| Promise | 1/1 | 0 |
| Mutation observer | 1/1 | 0 |
| postMessage | 1/1 | 0 |
| Worker message | 0/1, unknown and held | 0 |

**run [R]** The first five use raw fetch into the failing network gate to preserve actual initiator evidence. The worker's cooperative call is captured and later invoked in its own realm, into the denying network gate. The measured initiator belongs to that actual `/receive` send, excluding worker-script downloads; later invocation does not recover its original cross-worker ancestry. A page-load timer draining shared state also has no causal stack back to the click which filled that state (`Q3_TIMER`).

**assumed — interpretation:** 5/6 is a fixture result, not a web-wide accuracy rate. Unknown is conservatively held, so zero “page-owned” classifications is not proof of a complete attribution algorithm. Keep the site-wide post-action rule even if tracing improves. Function-name recognition here is a fixture oracle, never a hostile-page trust signal.

## Q5. Everyday sites

**read — safety configuration:** the public-only manifest installs `public-guard.js` before every frame's scripts. It prevents dedicated/shared workers, service-worker registration, WebTransport and RTC construction and records attempts. DNR blocks new WebSockets and non-GET/HEAD methods; Fetch additionally aborts Fetch/XHR/Ping resources and the synthetic demo query. The page wrapper queues sends. No account is used and no submission is approved to a public receiver. Service-worker bypass is enabled. These restrictions intentionally censor normal behavior.

**run [R]** Each site is observed for 4.5 seconds at rest and three attempts at a selected reading control, separated by 750 ms. Queue counts are bound to the current **main document ID** at each stage, excluding old documents and iframe queues. Tab-wide gate traffic is separate; these main-document counts are a lower bound on all-context activity. Missing controls and bot/error pages are retained. Counts below are this restricted sample, not estimates of normal signed-in traffic or owner prompts per hour; `public-<site>.json` retains both phases, candidate descriptions and constructor attempts.

| Site | Queued calls, rest → after | POST calls after | Reading controls found / 3 | Main-document API attempts | Observation | Verdict (assumed) |
|---|---:|---:|---:|---|---|---|
| github | 3 → 4 | 4 | 2/3 | none observed | Repository/Issues text rendered. | works smoothly |
| wikipedia | 0 → 0 | 0 | 3/3 | none observed | Article and heading links usable. | works smoothly |
| youtube | 2 → 2 | 2 | 1/3 | serviceWorker.register | Description visible; video shows a bot/sign-in check. | needs adapter/qualification* |
| news | 0 → 0 | 0 | 3/3 | none observed | Homepage and article links rendered. | works smoothly |
| amazon | 10 → 12 | 12 | 3/3 | serviceWorker.register | Product and review anchors visible; auxiliary requests queue. | asks often |
| reddit | 0 → 0 | 0 | 0/3 | none observed | Network-security denial; no reading control available. | needs adapter/qualification* |
| stackoverflow | 1 → 1 | 1 | 0/3 | RTCPeerConnection | Security challenge; target answer page unavailable. | needs adapter/qualification* |
| notion | 16 → 16 | 16 | 0/3 | Worker | Only the page shell; cached-page/bootstrap POSTs queue. | needs a site adapter |
| docs | 21 → 22 | 7 | 3/3 | none observed | View menu usable; RPCs and OPTIONS probes queue. | needs a site adapter |
| search | 12 → 6 | 6 | 3/3 | none observed | Result/category pages render; telemetry and opaque RPCs queue. | asks often |

**assumed — verdict limits:** “asks often” describes potential guarded-request burden, not a measured prompt rate; known tracking could instead be dropped. *For the bot-blocked rows this means keep the site unqualified; no adapter bypass of the access check is established. Queue counts can decrease after navigation because they refer to the new current document, not an accumulating session total.

**run [R]** No open live connection was observed in the recorded events under the safety block; attempted constructors/registrations and WS events are recorded, rather than interpreted as normal prevalence. POST and GraphQL counts at the HTTP gate exclude calls already queued in JavaScript or rejected by DNR. `Q5_GRAPHQL_FIXTURE` holds explicit query, persisted query, batch, mutation, inline typed text and typed variables, all with zero arrivals. Only the plain explicit query is an adapter-read candidate; no generic GraphQL parser/exemption is claimed.

**assumed — replay verdict for every row:** a send on that site remains unqualified without a concrete operation/adapter. Reading clicks, anonymous telemetry and a deterministic demo cannot establish exact replay of a real authenticated send, deletion, changing token or multipart upload. The in-page hold often leaves readable content but does not make its headers, cookies or application state immutable. The site verdicts are provisional usability recommendations from this constrained run.

**read — published prevalence, retrieved 2026-11-07:** HTTP Archive's [2025 PWA chapter, figure 11.1](https://almanac.httparchive.org/en/2025/pwa#service-worker), using the [July 2025 dataset](https://almanac.httparchive.org/en/2025/methodology), reports service-worker-controlled pages at about 20% overall (20.5% desktop, 20.0% mobile). The 2021 primary study [WebSocket Adoption and the Landscape of the Real-Time Web](https://theseclab.org/publications/www21.pdf) observed WebSockets on 55,805 sites, 6.3% of its crawl; this historical crawl is not a 2026 estimate. [Hygraph's GraphQL Report 2024](https://hygraph.com/resources/graphql-report-2024) reports 61.7% active GraphQL use among its respondents. That is a community/vendor survey, not a percentage of all websites, and cannot be combined with the crawl percentages.

## Q6. Owner Stop control

**run [R]** Policy pins the extension action. While controlled, the badge is ON and the Claude group is blue. The test opens the **real action popup** with `chrome.action.openPopup`, then uses X input to press Stop. This Chrome build omits both frame ID and document ID from its popup sender; the Stop-only handler checks the extension ID, exact popup URL and a current top-level POPUP context. Details-page approval still requires the tab sender's top-level frame. `Q6_STOP` verifies inactive state, STOP badge, grey group and the `popup Stop` event. Held calls are dropped before debugger detach, and all seven transport/API families remain absent through shutdown in the `end-stop-*` receiver audit. The [real Stop popup](screenshots/stop-before.png) also shows the pinned ON badge. The managed installation does not depend on Chrome's hidden debugger warning bar.

## Changes for the design

**assumed — proposals, covering section 6's 17c dependencies; no design/plan files changed:**

| 17c point | Proposed wording now |
|---|---|
| In-page hold replacing the baseline | Allow cooperative waiting only in qualified contexts. It can be the normal **UI path on those honest fixtures/sites**, while fail-then-repeat remains the HTTP fallback. It cannot replace the baseline as a universal security boundary. |
| Every frame/worker before its scripts | The tested document/frame cases and dedicated/blob workers are promising. New/shared/replaced worker startup and restored first requests are separate gates; refuse action where any remains unqualified. Never resume an unqualified worker merely because setup timed out. |
| Live messages / typed-text-only versus all | After acting, hold all message categories unless an adapter proves a read; the chat fixture would otherwise let three of four messages bypass the text rule. Network Fetch cannot rescue an unwrapped live message. |
| Causes through async chains | Preserve stacks as supporting evidence and keep unknown held. Tracing does not resolve shared-state causality or authorize a page/owner exemption. |
| Guard across tabs, shared queues and restart | Persist the guard, attach every relevant context, and separately qualify startup/replacement/restoration timing. A stored domain list is not an early network barrier. |
| Owner's external decisions | The exact trusted details page and genuine notification buttons work. Validate Chrome's sender identity, full page address and top-level document; do not reject a genuine extension tab merely because it is a tab. |
| Everyday POST reads / GraphQL / adapters | Specify decoder/parser and operation qualification separately from transport holding. Opaque and changing requests still need adapters; keep guarded unknowns visible without silently releasing them. |
| Guard retirement | Drop/expiry does not prove queue cancellation. A real adapter must establish resolution, or the owner ends the guard explicitly. |
| Visible control and Stop | Pin an extension-owned action, badge and Stop control; drop queued work before detaching. Qualify the actual popup, not only its HTML opened as a tab. |

## Risks and PLAN-GAPs

- **run [R] / PLAN-GAP:** the requested universal worker/startup and hostile-live fallback guarantees are not established. A passing observational workflow must not be read as permission to build a tool that assumes them.
- **run [R] / PLAN-GAP:** a shared worker's owner-triggered flush loses owner attribution; sending it through the ordinary tool approval path would not implement the specified owner decision flow.
- **read — code / PLAN-GAP:** an in-page queued function call is not a frozen complete HTTP request. Request bodies, form state, implicit headers/cookies, abort signals, stream backpressure and application retries require explicit contracts. This prototype only partially models those semantics.
- **run [R] / PLAN-GAP:** restored worker reports can be delivered through multiple attached sessions; a product needs target/context/call identity deduplication, not one pending operation per binding event.
- **assumed / PLAN-GAP:** anonymous no-send visits cannot settle signed-in app prevalence or exact replay of real business operations. Blocked POST bootstrap, disabled workers and bot checks bias these measurements downward.

## JUDGMENT-CALL

- **assumed — recommendation:** choose waiting for qualified honest calls, retaining strict HTTP fallback and refusal for unknown live/worker coverage. This feels better than an immediate failure, but broadening eligibility later requires new context/operation evidence.
- **assumed — recommendation:** keep all post-action messages guarded rather than exempting presence/typing by their labels. The fixture cost is four holds instead of one; an adapter can later reduce it with semantic evidence.
- **assumed — recommendation:** keep unresolved site guards until real evidence or the owner's explicit decision. Rejecting a queued request alone must not make later owner clicks silently free.

## Not checked

**assumed — outside this run's qualification:** the real owner profile/accounts, Wayland/labwc desktop notifications, production native-host isolation, sandbox-generated input, Claude Code permission prompts, a full public-suffix site partition, arbitrary authenticated operations and site adapters. WebTransport unidirectional/bidirectional byte streams (the independent receiver here exercises datagrams), arbitrary streaming/multipart bodies, every nested/opaque frame variant and all worker replacement races remain unqualified. XHR drop/timeout and beacon-return semantics need a more complete product contract. Public screenshots and text are evidence only, never the tool's page-reading method.

**read — scope:** no `os/`, `mod/`, install/emergency instructions, STATE/HANDOFF, design or plan file was changed. The branch remains a draft and is not merged.

**read — API scope, Chrome guide retrieved 2026-11-07:** the [WebTransport guide](https://developer.chrome.com/docs/capabilities/web-apis/webtransport) distinguishes datagrams from reliable unidirectional/bidirectional streams. The latter need separate receiver qualification; the datagram result must not be generalized to them.
