# 17d: Chrome's blocking floor

## Answer in five lines

1. **run [R]** The correctly scoped HTTP floor blocks before Fetch interception, including top-level forms, cross-site destinations, foreign frames and restored first-script POSTs.
2. **run [R]** It is not a worker WebSocket floor: shared/service-worker handshakes and messages reach the receiver even under a global WebSocket block.
3. **run [R]** A URL/method allowance is not an atomic one-use body permission: wrong bytes escape on detach during Fetch, including after the allowance is removed; an unreached worker can consume a site allowance.
4. **run [R]** Allowances survive reload, update and worker crash without explicit cleanup; startup cleanup works after it runs, while policy blocking removes the extension's floor altogether.
5. **run [R] / assumed** Complete body capture and some storage observations work, but the measured gaps prevent treating draft 9 as a fail-closed send boundary or sufficient evidence for automatic guard retirement.

[R]: https://github.com/Ares-Empire/AresOS/actions/runs/42362681610

## Evidence, commands and scope

**run [R]** Primary qualification: commit `4f34936b90e9891f5abe2f1f30a6f019b4f85712`, Google Chrome `157.0.8103.38`, five headed GitHub Linux jobs: `floor`, `workers`, `allowances`, `storage`, `public`. Artifacts are `chrome-check-42362681610-1-<phase>`; common metadata is in `17-chrome/artifacts/`, measurements in `17d-chrome/artifacts/`. The retained [records](records/) preserve summaries, independent server logs, final receiver audits, provenance and selected screenshots. `extension-events.jsonl` and full check stdout remain in the workflow artifacts. Every case name below identifies a console line and a summary entry. A successful check reproduces negative findings; it does **not** certify the design's safety.

**run [R]** Commands: the existing workflow installs Google's official stable `.deb`, prints `google-chrome-stable --version`, runs `npm ci --ignore-scripts --no-audit --no-fund`, installs pinned `aioquic==1.3.0` in a disposable venv, and executes `timeout --kill-after=15s 25m node control/checks/17d-chrome/run.mjs` under D-Bus, Xvfb, Openbox and Dunst. Each job has a 30-minute limit. `FINAL_DELIVERY_AUDIT {"status":"PASS",...}` and `ALL 17D CHECKS COMPLETE <phase>` are the final success markers. Receiver counts are rechecked after Chrome exits, including late deliveries and unregistered case IDs. HTTP bodies are audited by byte length and SHA-256; WebSocket opens and messages are separate receiver rows; the HTTP/3 receiver records CONNECT headers.

**read — check source at [R]'s head** The [runner](../../control/checks/17d-chrome/run.mjs) reuses 17c's signed CRX policy installation/native framing, fixture audit and X helpers, with 17b's HTTP/3 receiver. It refuses browser execution unless both Linux and `GITHUB_ACTIONS=true` apply, before importing browser helpers. Process arguments are saved and checked for forbidden debugging-port/pipe and sandbox-disabling flags; the manifest has no `management` permission. All browser profiles and files are disposable Linux fixtures. No Mac browser/profile, real account, real submission, OS/mod/design/plan file was used or changed. The cumulative draft [PR #8](https://github.com/Ares-Empire/AresOS/pull/8) builds on PRs #3, #4 and #7.

**run — local verification** `node --check` over every new `.mjs`/`.js` file and `git diff --check` exited 0 with no output. [local-checks.txt](records/local-checks.txt) records the commands. No Gradle was run. Normal pushes used the repository's hooks without `--no-verify`. No local `.work/` file exceeds 500 MB; [local-work-inventory.json](records/local-work-inventory.json) records that inventory.

**read — verification bookkeeping** The code/evidence run above precedes this report commit. Two complete executions on the **final head**, identified by exact SHA, run IDs/attempts and job results, are recorded in [draft PR #8](https://github.com/Ares-Empire/AresOS/pull/8). Updating that PR's verification text does not change the tested head. Earlier failed harness runs and automatically cancelled pending runs are retained in [workflow-runs.json](records/workflow-runs.json); they are not silently counted as passing qualification.

## Q1. Does the floor precede the request gate?

**run [R] — `Q1_BLOCK`, `Q1_FOREIGN_FRAME`, floor receiver audit:** with both dynamic initiator rules and the request-stage gate installed, fetch, XHR, beacons, link pings, top-level form POSTs and page WebSockets each have zero receiver arrivals. Same-site and cross-site destinations are tested. There are **zero `Fetch.requestPaused` candidates** for these blocked requests. Chrome still reports `Network.requestWillBeSent` and a blocked failure for HTTP attempts; that event is not evidence of network delivery. A foreign `localhost` frame inside the selected `127.0.0.1` tab executes its POST under the session tab rule and has zero arrivals; the script-execution result proves the foreign frame actually ran.

**read — rule definition, Chrome DNR reference retrieved 2026-11-07** [DNR conditions](https://developer.chrome.com/docs/extensions/reference/api/declarativeNetRequest#type-RuleCondition) omit `main_frame` by default. An empty excluded-resource list also failed to include it in the initial experiment. The final method rules explicitly list every current resource type, including `main_frame`; methods exclude only GET and HEAD. The live rule explicitly includes `websocket` and `webtransport`. Omitting navigation coverage would make a form result depend on the gate instead of the floor.

**run [R] — `Q1_END`:** raw POSTs immediately before, and scheduled 600 ms after, debugger detach, extension reload/update, extension-renderer kill, native-host kill, normal window close and browser/process kill have zero arrivals. The rules remain installed while attached. These tests use a parked gate mode, so a request reaching Fetch could not be hidden by an immediate fail. The initial POST never reaches that gate. The scheduled request cannot execute once its browser is gone; it is not presented as a surviving-page test after browser death.

**run [R] — counterexample, `Q1_POLICY_UNLOADED`:** after administrative policy blocking actually disconnects the extension, navigating a fresh fixture page produces **one same-site and one cross-site POST arrival**. This proves loss of the floor, rather than merely inspecting an empty extension rule list. The pre-block producers stayed blocked; the fresh post-block producers did not. The forced-install policy prevents ordinary owner UI removal, not an administrator removing the policy protection. After this destructive probe the runner uses a fresh synthetic profile; it makes no rule-survival claim about that new installation.

**run [R] — `Q1_WEBTRANSPORT` in workers:** the real HTTP/3 receiver accepts the positive page handshake once, then records zero page handshakes with the floor installed. Shared and service-worker WebTransport constructors are present, report `WebTransportError` under the floor, and produce zero HTTP/3 handshakes; their CONNECT events carry `tabId=-1`. This page result does not repair the worker WebSocket counterexample in Q3, nor establish every transport/lifecycle permutation.

## Q2. Browser start and restored first acts

**run [R] — `Q2_BEFORE_ATTACH`, `Q2_RESTART`, `Q2_RESTORED_WORKER`:** dynamic site rules remain after normal close and process kill. The restored `/startup` document's **first inline script** immediately POSTs to its own site and `localhost`, then sends a permitted GET marker. Both POST receiver counts remain zero. The server's new document row and `startup-executed` marker must appear **before any debugger attachment**; the runner fails if restoration never executes. These markers and the later `check.ready` timestamps establish the ordering, not just rule persistence in extension storage.

**run [R] — `Q2_RESTORE_UI`:** after a kill, this build requires the native Chrome **Restore** button in the crash bubble. The runner accepts that button through X before attaching and waits for the restored script marker. This qualifies the first requests of a genuinely restored tab; it does not claim that killed Chrome automatically restores every tab without the owner accepting restoration. A seven-second pre-kill wait lets Chrome checkpoint the synthetic session. Normal-close restoration needs no debugger to initiate it.

**run [R]** The worker phase restores an installed service worker and a page it controls, before attachment. Its first POSTs remain absent, with worker attempt markers and WebSocket deliveries distinguishing execution from inactivity. This qualifies the dynamic rule's coverage of these no-tab HTTP requests. Session tab rules are not the restart protection; the dynamic site rules are.

**assumed — limit:** finite runs establish the observed first-script ordering on this Chrome/Linux build, not a universal proof about every startup path, opaque origin or future Chrome version. Do not erase the persistent rule during attachment or replace it with an asynchronous `onStartup` handler.

## Q3. Browser-started and replaced workers

**run [R] — worker summary/server log:** the initial service worker, explicit `registration.update()` replacement, navigation-triggered update/replacement, navigation waking a dormant worker, real background sync after the worker has become dormant, and a new shared worker execute their own initial POST/WebSocket code. `Q3_IDLE_TARGETS` and `Q3_SYNC_IDLE_TARGETS` record the worker absent before the relevant trigger; `Q3_SYNC_NO_PAGE_DEBUGGER` requires a real sync marker. There is no debugger-dispatched sync event and no early worker auto-attach. Navigation/update script-download rows, per-version attempt markers and receiver events distinguish an update fetch from actual new script execution. All guarded worker POSTs have zero arrivals.

**run [R] — counterexample:** each executed initial/event send opens a WebSocket and delivers its synthetic message. This happens under the initiator floor, with a tab-only higher-priority WS allowance, and under the separate **global** WebSocket blocking rule (`Q3_GLOBAL_SOCKET_BLOCK`). The check now asserts these counterexamples as well as zero HTTP arrivals; it does not remove the receiver evidence to call them successes. `worker-control-v3-first` supplies the three-row positive control: POST, socket open, message.

**read — Chrome 157.0.8103.38** [`ChromeContentBrowserClient::WillInterceptWebSocket` / `CreateWebSocket`](https://github.com/chromium/chromium/blob/157.0.8103.38/chrome/browser/chrome_content_browser_client.cc#L6526) return without extension proxying when no frame exists, with an explicit TODO for that case. **assumed — inference:** this explains the no-frame worker WS results. The extension receives no corresponding worker handshake event to label `tabId=-1`; it is incorrect to report a measured WS tab ID. The workers' **HTTP** `webRequest` events do carry `tabId=-1`. A tab-scoped allowance does not account for the WS leak: the same leak occurs with no allowance and with a global block.

**run [R]** `Q1_WEBTRANSPORT` records zero shared/service-worker HTTP/3 handshakes, both constructors present, `WebTransportError` results and intercepted CONNECT events with `tabId=-1`. This contrasts with the unobserved/unblocked worker WS handshakes; a missing constructor was not counted as a block.

**run [R] — not checked:** real push delivery cannot be generated without a push subscription/FCM setup in this no-account fixture. `Q3_PUSH` records that limitation. A debugger-injected push would not satisfy the requested independent trigger and was not substituted.

## Q4. One-time allowances and the failure window

**run [R] — `Q4_ONCE`, `Q4_SECOND`, `Q4_COMPETING`, `Q4_BODY_MISMATCH`, `Q4_HEADER_MISMATCH`:** a higher-priority session allow rule binds the escaped full URL, HTTP method and tab (or explicit site scope). The first observed matching `webRequest` removes it; the Fetch gate also removes it before answering and atomically consumes its in-memory approval before the asynchronous approval comparison. Approved bytes and the page-set `X-Check` header reach the receiver once. A sequential duplicate and two competing identical requests leave the total at one. A different body or changed page-set header reaches the gate but is failed, with zero receiver arrivals. `Q4_SITE_SCOPE` separately exercises initiator scope. A different target cannot consume the exact-target permission.

**run [R] — `Q4_UNREACHED_SITE_ALLOWANCE`:** an unreached shared worker sends different bytes to the approved site-scoped URL/method. Its POST arrives once without a Fetch body check, alongside its separate WS open/message. Removing the rule at the first observed request does not undo that request. This is not a qualified replay path: a broad site allowance needs coverage of every competing producer, not merely attachment to the originating page.

**run [R] — `Q4_RACE`, 24 deterministic trials:** the fixture sends the wrong body after add-to-send delays of 0, 25, 100 and 500 ms, three trials each, with and without an explicit revocation after the Fetch pause. Each trial waits at the exact named gate instant, detaches, and delivers **one wrong-body POST**. Revoking the allowance before detaching does not save an already-admitted request. The first-match sidecar is asynchronous JavaScript, not an atomic rule counter. The server's actual body/hash is preserved for every trial.

**run [R]** `Q4_NATURAL_WINDOW` records `allowAdded.before/after`, Fetch entry, first-match removal, gate answer and receiver times. [metrics.json](records/metrics.json) gives the measured add-to-gate and gate-answer intervals: **2 ms** from acknowledged addition to reported gate entry, and **2 ms** from there to the reported answer in the natural trial. These are extension-side millisecond timestamps, not exact browser-internal pause boundaries. The race trials deliberately wait 150 ms after issuing the request, confirm it reached Fetch, then detach; their 24/24 result is **not** a measured probability for a naturally timed OS failure. The 500 ms pre-send trial also shows that an unconsumed allowance can remain available that long.

**run [R] — `Q4_LIFETIME`, `Q4_LEFTOVER_RECEIVER`:** without startup cleanup, the session allowance remains through extension reload, actual manifest-version update and extension-renderer crash. With cleanup enabled, startup snapshots show it present before cleanup and absent afterwards; the subsequent receiver probe is blocked. Dynamic floor rules remain in those same-profile cases. Policy blocking unloads the floor; the fresh-page POSTs arrive regardless of the cleanup preference (`Q4_POLICY_UNLOADED`). Continuation after policy removal uses a fresh profile and is explicitly marked `sameProfile:false`, so its empty rules are not evidence of revocation in the original profile.

**read — Chrome DNR reference, retrieved 2026-11-07** [Rule actions and conditions](https://developer.chrome.com/docs/extensions/reference/api/declarativeNetRequest#type-RuleAction) provide URL/method/context allowances, not body hashes or atomic hit counts. **assumed — consequence:** prompt comparison and cleanup shorten exposure but do not close this window. A timer, removing the rule after matching, and startup cleanup cannot revoke a decision Chrome already made. No complete generic closure was demonstrated; refuse this path or redesign the boundary before relying on “never sends when control breaks.” A qualified adapter still needs an actual fail-closed transport path, not just a clearer description.

## Q5. Body bytes: floor observations versus frozen copies

**run [R] — `Q5_BODY`, `Q5_LARGE_EVENT_LIMIT`, `Q5_FROZEN_RECEIVER`:** the ordinary Network configuration is `maxPostDataSize=65,536`; a separate trial raises it to 32 MiB. Missing data is stored as `missing:true`, never `null`/empty-body equality. The wrapper serializes an immutable Request body before reporting its length/hash. Its releases in this section deliberately use a **synthetic gate-passthrough oracle** to test the copy against receiver bytes; they do not qualify multipart/large-body replay through an exact gate.

| Body | Network event at 64 KiB | `getRequestPostData` in this run | Wrapper / independent receiver |
|---|---|---|---|
| JSON, 32 bytes | Complete bytes/hash | Complete | Same 32 bytes/hash |
| Form encoded, 24 bytes | Complete bytes/hash | Complete | Same 24 bytes/hash |
| Multipart with actual disk file | Body omitted | Only 289 bytes of framing/fields; known disk-file marker absent | Full 94,497 bytes, including the 94,208-byte file; later FormData mutation does not change the receiver hash |
| 1 MiB | Body omitted from event | Complete 1 MiB | Full immutable copy and matching receiver hash |
| 25 MiB | Body omitted from event | Missing: `No post data available for the request` | Full 26,214,400-byte copy and matching receiver hash |
| Streaming body | No complete byte body | Missing | Refused as `UNFREEZABLE_STREAM`; zero arrivals |

**run [R]** Raising the event limit to 32 MiB exposes the full 1 MiB and 25 MiB ASCII bodies, verified against known SHA-256 values; `getRequestPostData` still misses the 25 MiB body in this configuration. This is a configurable event limit and a measured missing-data case, not a universal 25 MiB Chrome hard limit. Larger bodies, arbitrary encodings, Request-input streams and unbounded buffering were not qualified. No stream was silently treated as an empty send.

**run [R]** The disk-backed upload is created only on the Linux runner and selected in Chrome's real native file picker with the debugger detached; the tool reattaches before the multipart tests. The receiver's permitted change marker and a [selection screenshot](screenshots/synthetic-file-selected.png) prove the file was selected before reattachment. Direct `DOM.setFileInputFiles` was refused as `Not allowed` in an earlier failed harness run; the check does not add filesystem access to the extension. The final multipart record marks whether the known disk-file bytes occur in Chrome's exposed body; the wrapper's complete length/hash must equal the receiver after release. In-memory File bodies from the earlier experiment are not substituted for this disk-file case.

**read — Chrome protocol revision `b0d96c6`, retrieved 2026-11-07** [`Network.Request` / `getRequestPostData`](https://raw.githubusercontent.com/ChromeDevTools/devtools-protocol/b0d96c6cdf39e5583e67a3762b2815a33154455b/pdl/domains/Network.pdl) document optional body data and omitted multipart file content. **assumed — design change:** make bounded complete-byte capture an explicit eligibility check. A readable request header or an available partial multipart string cannot authorize exact-body replay. Keeping bytes in the page proves neither immutable cookies nor complete network-stage visibility.

## Q6. Stored work and handoffs

**run [R] — `Q6_SUBSCRIBE_*`, `Q6_PAGE_WRITE`, `Q6_WORKER_WRITE`:** IndexedDB and Cache Storage tracking works through `chrome.debugger` from page and directly attached worker targets. DOMStorage, ServiceWorker and BackgroundService domain commands return `-32601 ... wasn't found` through this extension transport. A normal DevTools protocol catalog containing those domains does not make them available to this extension.

| Operation exercised | Debugger observation within the 1-second sample | Cooperative script observation |
|---|---|---|
| local/session storage `setItem` | None; DOMStorage domain unavailable | Wrapped call recorded |
| Named-property web-storage assignment | None | The prototype misses it; readback proves the value was stored |
| IndexedDB `put` | `Storage.indexedDBContentUpdated`, database/store named | Wrapped call recorded |
| Cache `put` | `Storage.cacheStorageContentUpdated` | Wrapped call recorded |
| Script cookie / service-worker CookieStore | No write event in the subscribed domains | Setter / `cookieStore.set` recorded |
| OPFS asynchronous file write | No write event observed | `getDirectory`, `createWritable`, `write` recorded |
| Service-worker registration | ServiceWorker domain unavailable | Registration call recorded |
| Background-sync registration, page and service worker | BackgroundService domain unavailable | `sync.register` recorded |
| Periodic-sync registration | Permission denied; no successful registration qualified | Attempt recorded, including rejection |
| Broadcast channel | No handoff event observed | `postMessage` recorded |
| Another window, dedicated-worker message | No handoff event observed | Receiver window / worker call recorded |
| Shared worker's port / SW client message | No handoff event observed | Port / client call recorded |

**run [R]** [metrics.json](records/metrics.json) retains the exact operation-to-browser-event and operation-to-script-report latencies. Measured content notifications take **6–8 ms from the page** and **3–5 ms in the worker sample**; script reports take **1–25 ms for page operations** and **0–5 ms for worker operations**; negative entries mean no event during the one-second observation interval, not a timing guarantee. Web storage is unavailable in workers. CookieStore is unavailable in the shared worker but succeeds in the service worker; sync/periodic-sync and client APIs are similarly classified by their actual results, not counted as missed writes when the API itself is unavailable. Multiple subscribed targets receive duplicate storage notifications; deduplication remains product work.

**run [R] — `Q6_OFFLINE_OUTBOX`:** a trusted fixture click writes `{delete:42}` into the IndexedDB outbox and makes no receiver request. Chrome reports the outbox write. A second tab later reads that record and attempts to send it; the floor blocks it with zero receiver arrivals. The evidence includes the write before the later send, not merely an empty pending-request list. The earlier named-property case is a deliberate observer counterexample, not permission to retire a guard after silence.

**read — Chrome debugger reference retrieved 2026-11-07** [Restricted domains](https://developer.chrome.com/docs/extensions/reference/api/debugger#restricted-domains) include Storage but omit DOMStorage, ServiceWorker and BackgroundService. **assumed — consequence:** the design must name the extension transport's actual capabilities. A positive event establishes that something was stored, not its cause, content, later cancellation or that all other stores stayed untouched. Cooperative prototype patches miss named-property writes and saved native references. Absence of these events alone is insufficient for automatic guard retirement.

## Q7. Owner experience and public reading

**run [R] — `Q7_OWNER_NOTIFICATION`:** an actual X click on the fixture's owner button leaves fetch waiting in the page with zero receiver arrivals. The real Dunst notification action menu's Send action releases it through an allowance, producing one matching body/hash arrival. Duplicate release is refused. [owner-waiting.png](screenshots/owner-waiting.png) and [notification-menu.png](screenshots/notification-menu.png) preserve the waiting page and external decision surface. This is the harness's owner decision, not an MCP or Claude Code permission-prompt implementation.

**run [R] — `Q7_BACKGROUND`, `Q7_LIVE_HELD`, `Q7_WORKER_LIVE`:** the page's raw background POST is blocked and appears in the extension's recorded background events. A newly allowed reached-tab WebSocket opens, and 17c's cooperative send wrapper holds its message with zero message arrivals. Shared/service-worker sockets still open and send one message each; this requested refusal is a demonstrated failure, not a completed feature.

**run [R] — `Q7_PUBLIC`, ten `public-*.json` artifacts/screenshots:** the same ten anonymous public destinations as 17c are observed for 4.5 seconds at rest, followed by three attempts at a reading control. No form is submitted and nothing is typed. The site initiator floor is installed before navigation; an additional global non-GET/HEAD/live block supplements the public constructor refusals. Public document-start safety code disables workers, SW registration, WebTransport and RTC construction. The reading GETs themselves are permitted. This is therefore a stricter no-send sample, not an estimate of ordinary signed-in behavior.

**run [R]** [public-sites.json](records/public-sites.json) preserves at-rest/after-click text lengths/fingerprints, controls found, constructor restrictions and blocked non-reading counts. Original text is in the workflow artifacts; screenshots were inspected directly. Counts cover profile-observed non-reading error events in unequal short windows, not attributed owner actions or a prompt rate. The visible observations below are provisional and retain bot/error pages rather than pretending those sites were measured normally:

| Site | Reading controls / 3 | Blocked events, rest / after | Visible observation |
|---|---:|---:|---|
| github | 3/3 | 4 / 9 | Repository and Issues list render; reading control works. |
| wikipedia | 3/3 | 4 / 0 | Article and History anchor render. |
| youtube | 3/3 | 6 / 1 | Description expands; video remains behind a bot/sign-in check. |
| news | 3/3 | 20 / 53 | Homepage and regional news page render despite background failures. |
| amazon | 3/3 | 20 / 6 | Product/review anchor renders; background traffic is blocked. |
| reddit | 0/3 | 8 / 0 | Network-security denial; no reading control. |
| stackoverflow | 0/3 | 5 / 1 | Security challenge; no answer-page control. |
| notion | 0/3 | 41 / 0 | Blank shell; no sidebar control. |
| docs | 3/3 | 17 / 1 | Document content and menus render with a persistent connection warning. |
| search | 3/3 | 28 / 40 | Search results and News category render; background failures continue. |

**run [R]** The red notification overlay in the public screenshots belongs to the earlier loopback WebSocket fixture and remains on screen during these visits.

**assumed — interpretation:** telemetry failures alone need not become owner prompts; adapters may classify reads and known tracking may be dropped. Bootstrap/RPC POSTs can leave an app shell or a partially functioning menu. Bot checks, missing controls and forced-off worker features prevent attributing every visible failure solely to DNR. No authenticated send, public-site replay, signed-in notification burden or ordinary-day prompt rate is qualified here.

## Q8. Account changes while waiting

**run [R] — `Q8_ACCOUNT_CHANGE`:** the fixture signs in as synthetic A, holds a deletion, then uses its sign-out and sign-in-as-B controls. The fixture server sets an HttpOnly session cookie and the page displays the new label. `Network.getCookies` sees the HttpOnly cookie; Runtime sees the label. The release compares both with the hold snapshot, refuses `ACCOUNT_CHANGED` before adding an allowance, and the receiver remains at zero. Server session rows and before/after snapshots preserve the actual transition.

**assumed — limit:** a page-displayed name is untrusted, cookies are a session fingerprint rather than proof of a human identity, and snapshot equality alone cannot detect an intervening change that returns to the same values. This supports conservative refusal on an observed change, not arbitrary account binding on real sites.

## Changes for the design

**assumed — proposals for every section-6 dependency marked 17d; design/plan files remain untouched:**

| Draft 9 point | What it should say now |
|---|---|
| Floor before request stage | Qualified HTTP/page-connection cases block before Fetch. Explicit resource-type coverage must include navigations. Renderer Network events still describe blocked attempts. |
| Every worker, including Chrome-started/replaced workers | HTTP POST floor works for the measured independent starts, updates, navigation and real sync. **Worker WebSockets bypass the extension proxy entirely in Chrome 157.** Refuse acting where those paths remain possible, or replace the boundary. |
| Reached-tab live allowance versus worker without a tab | HTTP worker requests expose `tabId=-1`; worker WS handshakes are not exposed at all. A tab allowance cannot provide the proposed worker refusal. Keep WT API/receiver qualification separate. |
| Restored first request / dynamic rules across restart | The measured restored inline POSTs and worker HTTP are blocked before debugger readiness. Killed Chrome's native Restore decision is part of the tested path. Preserve the dynamic floor throughout attachment. |
| Floor survives control ending | It survives the tested debugger/native/worker failures while the extension remains enabled. Administrative policy blocking removes it. An extension alone cannot promise protection while disabled. |
| Allowance disappears at first match and on reload/update/crash | It is an asynchronously removed rule, not an atomic single-use permission. Explicit startup cleanup is required and only proves removal after it runs. Persisting allowances and the admitted-request detach race remain counterexamples. |
| Gate compares approved body and page-set headers | Works for the qualified complete synthetic bodies in attached contexts. Broad site allowance plus an unreached competing worker is unsafe. No null/partial-byte match and no assumed header/account exemption. |
| Complete body/file bytes or refuse | The wrapper can freeze the measured finite bodies, including a real disk file and 25 MiB. Network event limits are configurable; file omission/large-body missing data must remain explicit. Refuse streams/unbounded or otherwise unqualified inputs. |
| Evidence nothing of Claude's was stored/passed | Storage domain provides useful IDB/cache evidence; many APIs need script observations or a different transport. Named-property storage already escapes this prototype's patch. Silence cannot prove a clean site. |
| Automatic guard retirement / fail closed | Neither universal sending protection nor complete negative storage evidence is established. Keep unresolved/unknown sites guarded until real adapter evidence or the owner's decision; don't claim the automatic condition was implemented by this check. |

## Risks and PLAN-GAPs

- **run [R] / PLAN-GAP:** draft 9's universal worker-live floor and allowance-lifetime premises are false for this configuration. A green evidence workflow must not unblock a product that relies on them.
- **run [R] / PLAN-GAP:** administrative extension removal is outside an extension's independent enforcement power. The policy probe proves actual outbound delivery after removal, even though the owner normally cannot click Disable.
- **run [R] / PLAN-GAP:** storage tracking reports effects, not complete causal provenance; named properties and unwrapped handoffs defeat the proposed negative inference. An empty request queue is not a resolved offline outbox.
- **read — harness / assumed risk:** raw native RPC, fixture host matching, exposed originals, cooperative reports, synthetic account comparison and direct worker attachment are check mechanisms, not product authorization. A hostile page can forge reports, keep native references or encode data into allowed GETs. These tests grant no hostile-page input guarantee.
- **run [R] / PLAN-GAP:** public safety restrictions censor normal offline/live/bootstrap behavior. No adapter can be called qualified from these anonymous reading visits alone.
- **assumed:** extension startup cleanup, bounded buffering, every page-set header, context/account revalidation, exception-path allowance cleanup and target deduplication all need product contracts. None closes an already-admitted Fetch request's detach behavior.

## JUDGMENT-CALL

- **assumed — recommendation:** refuse sending/acting through unqualified worker/live or fail-then-repeat paths rather than accept these demonstrated escapes. This reduces eligible sites; reversing it requires new enforceable coverage, not a shorter timeout.
- **assumed — recommendation:** keep a guard when storage/handoff evidence is positive **or incomplete**. This can increase owner notifications; an adapter or explicit owner end remains the reversible escape. The check does not silently change the design's product policy.
- **assumed — check choice:** finite bodies are copied before holding, and init streaming bodies are refused. No general memory limit is proposed from a 25 MiB success; production needs a bounded policy and user-visible refusal rather than unbounded reads.

## Not checked and why

**run [R] / assumed — qualification limits:** real push requires independent infrastructure absent here; periodic sync is permission denied. Every possible body size, transport/lifecycle permutation, nested/opaque frame, named-property storage interception, saved native storage reference, OPFS synchronous access, Request-input stream, encoding, full PSL partition and arbitrary worker handoff remains unqualified. The measured negative observer case is retained explicitly. No real profile, account, business operation, site adapter, Linux desktop outside this X11 fixture, production host isolation or Claude Code prompt was tested. Q8 is a synthetic account lifecycle, not an identity-provider integration.
