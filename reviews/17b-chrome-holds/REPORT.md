# 17b: Chrome holds

## Answer in five lines

1. **run [R]** Keeping a request paused is unsafe across detach, reload, disable, Cancel and update; adding an exact DNR session rule after the pause does not prevent its release. Fail immediately, then permit one exact replay on qualified actions instead.
2. **run [R]** Attaching directly to the site's worker target holds page-through-worker HTTP, worker-owned HTTP and background sync; bypassing the worker holds page HTTP but changes worker-only behavior.
3. **run [R]/[L]** Ordinary fetch survives 30 seconds, two minutes and ten minutes, then arrives once; page timeouts cancel requests, and a retry is a separate hold.
4. **run [R]** Heap queries find pre-existing WS/RTC/WebTransport objects in the tested realm; Fetch does not pause WS handshakes, and delayed typed-text sends outlive the settle window.
5. **run [R]** Linux force policy installs and updates the extension, hides Chrome's debugger bar and prevents owner UI changes; disabling user-level native hosts selects the system host, and leaving the Claude group drops held traffic.

[R]: https://github.com/Ares-Empire/AresOS/actions/runs/42344844452
[L]: https://github.com/Ares-Empire/AresOS/actions/runs/42343675024

## Evidence and interpretation

**run [R]** Qualification: commit `9b5dd7846e6fccd66ce82f22c8015da5211559a1`, branded Google Chrome `157.0.8103.38`, headed Xvfb/Openbox on GitHub Linux, Chrome's sandbox enabled. The three artifacts are `chrome-check-42344844452-1-{safety,workers-long,live-public}`. Within each artifact, `17-chrome/artifacts/` contains version/head/dependency metadata and `check.log`; `17b-chrome/artifacts/` contains `summary.json`, the independent `server.jsonl`, `delivery-audit.json` and screenshots. Each job ends with `FINAL_DELIVERY_AUDIT ... PASS` and `ALL 17B CHECKS COMPLETE`. Committed [records](records/) retain the measurements and receiver logs; public traffic is reduced to the relevant synthetic submissions, counts and fingerprints, with per-artifact provenance hashes. Chrome version lines have trailing whitespace trimmed; raw stdout remains in CI artifacts. The audits cover 25 safety, 22 worker/timeout and 15 live/text/group case IDs; negative detach deliveries are preserved as findings.

**run [L]** The one ten-minute experiment is run 42343675024 at `68bfaec829fc103248d9336a23814f3d748325e2`. Its `Q3_LONG long-600000` case passed (600,005 ms, one arrival), but the workflow failed its final audit: a rejected background-sync retry remained paused and leaked on browser shutdown. The final check code, qualified by [R], adds immediate failure of exact rejected repeats and a natural five-minute retry regression; the ordinary long-fetch experiment itself was not repeated. The failed long run is retained with its mismatching receiver audit; it is not called a passing workflow. Final-head verification is recorded in [draft PR #4](https://github.com/Ares-Empire/AresOS/pull/4) after the evidence/report commit: two fresh executions of all three jobs, without repeating the ten-minute experiment. Only report/records change after [R], following the report/final-head split used by brief 17; report-only changes do not change the browser experiment. The final PR verification record identifies exact heads and attempts. [Earlier workflow runs](records/workflow-runs.json) include failed harness iterations and superseded/cancelled runs; they are not evidence for final capability claims.

**read — check at `9b5dd7846e6fccd66ce82f22c8015da5211559a1`** [Runner](../../control/checks/17b-chrome/run.mjs), [extension](../../control/checks/17b-chrome/extension/background.js), [fixtures](../../control/checks/17b-chrome/fixture.mjs), [WebTransport receiver](../../control/checks/17b-chrome/webtransport.py) and [workflow](../../.github/workflows/control-chrome-check.yml) are feasibility code. Raw RPC and fixture-specific classification are intentional; this is no MCP server, tool service or permission-prompt integration. A passing workflow reproduces counterexamples as well as positive capabilities, and does not certify a universal send boundary.

**run [R]** Commands in CI: `npm ci --ignore-scripts --no-audit --no-fund`, a disposable venv with `aioquic==1.3.0`, and `timeout --kill-after=15s 25m node control/checks/17b-chrome/run.mjs` under `dbus-run-session`, Xvfb and Openbox. `CHECK_PHASE` selects the three jobs; `LONG_HOLD=true` adds the ten-minute case only in workers-long. The actual Chrome process arguments contain neither a debugging-port/pipe switch nor `--no-sandbox`; `ss` finds no Chrome TCP listener (`processes.json`, `sandbox-status.png`). Browser execution is guarded against non-GitHub/non-Linux hosts. All profiles, requests, files and input values are disposable fixtures; public submissions are aborted. No real account is used.

## Q1. Fail closed

**run [R] — receiver counts below are deliveries after control ends, with zero before the triggering event.** Find each `q1-*` case in `server.jsonl`, `summary.json` and the per-case held/after snapshots. The final audit rechecks for late arrivals after Chrome exits.

| Control-ending event | Arrivals | Meaning / evidence |
|---|---:|---|
| Host killed | 0 | `Q1_host-dies`: native-port loss fails pending requests without detaching. |
| Service socket closed | 0 | `Q1_service-socket`: same fail-closed path. |
| Extension renderer/worker killed and restarted | 0 | `Q1_WORKER_STOP_DELIVERY`, `Q1_STOP_WORKER`; recovery detail below. |
| Forced extension disables itself through its test API | 1 | `Q1_policy-disable`; owner UI prohibition does not prohibit a policy extension's own management API. |
| Forced extension removal attempted | 0 | `Q1_policy-uninstall`: rejected, so control did not end. |
| Reload | 1, including with DNR | `Q1_reload`, `Q1_reload_DNR`. |
| Policy update 0.2.0 → 0.2.1 | 1 | `Q1_policy-update`, `Q5_UPDATED`; update manifest and CRX downloads are in the receiver log. |
| Owner Cancel, non-forced installation | 1, including with DNR | `Q1_cancel`, `Q1_cancel_DNR`; actual button click and `canceled_by_user` event. The managed install has no bar. |
| Non-forced disable / uninstall | 1 each | `Q1_nonforced-disable`, `Q1_nonforced-uninstall`. |
| DevTools opened | 0 | `Q1_devtools`, `Q1_devtools_DNR`: in this managed configuration DevTools coexists with the attachment; no detach event occurred. |
| Tab closed | 0 | `Q1_tab-close`. |
| Chrome window closed normally / browser and children killed (page request) | 0 each | `Q1_chrome-normal`, `Q1_chrome-kill`; browser ends before the driver closes its socket. |

**run [L]** A worker-owned automatic sync retry is an additional shutdown counterexample: it paused again after about five minutes, then arrived when Chrome closed (`sw-sync-false`, the failed long-run audit). The page-request close cases above therefore do not establish safe closure for worker-owned holds.

**run [R]** DNR was installed and acknowledged before reporting the hold, matching the exact tab, POST method and escaped full URL. It blocked a *new* matching request (`Q1_DNR_NEW_REQUEST`, count unchanged), proving the rule was functional, but did not block a request already paused in Fetch and resumed on detach. Removing the rule for explicit approval allowed one delivery; explicit drop delivered none (`Q1_DNR_APPROVED`, `Q1_DNR_DROP`). This backstop fails the required guarantee.

**run [R]** Killing the extension renderer also stops its service worker. Chrome kept the browser-owned debugger attached; the restarted worker read saved hold metadata from `storage.session`, failed the old interception, and recovered its own attachment (`check.recoveredDrop`, `check.recoveredAttachment` inside `Q1_STOP_WORKER`). There were zero arrivals before or after recovery. This crash behavior differs from an explicit reload/update, which detaches and releases.

**read — Chrome 157.0.8103.38** [Debugger client implementation](https://github.com/chromium/chromium/blob/157.0.8103.38/chrome/browser/extensions/api/debugger/debugger_api.cc) keeps debugger state in the browser and has worker keepalive support. [Management API implementation](https://github.com/chromium/chromium/blob/157.0.8103.38/extensions/browser/api/management/management_api.cc) distinguishes extension-originated settings changes from user changes and forbids policy-controlled uninstallation. The test's `management` permission is for lifecycle probes; a product should not expose this RPC or permission.

**run [R]** Fail-then-repeat fails the original request immediately. One approval matches method, full URL, text body and a SHA-256 of the sorted request-stage header map; the allowance is consumed before continuing. No volatile field is ignored by the enforcement rule. The original failed request remains absent after detach (`Q1_REPEAT_DETACH`); a second identical replay cannot reuse permission. `Q1_REPEAT` records:

| Fixture | Repeats compared with first | Exact matches | Matches ignoring named fields | Approved / duplicate delivery |
|---|---:|---:|---:|---|
| Fetch, XHR, POST form (each) | 2 | 2/2 | 2/2, no fields ignored | 1 / 0 |
| JSON with changing nonce | 2 | 0/2 | 2/2 ignoring `nonce` | 0 / 0; changed replay refused |
| Selenium public demo GET form | 2 | 2/2 | 2/2, no fields ignored | All three attempts aborted; nothing approved |

**run [R]** The driver recreates the fixture page and restores its field values before replays; Selenium trials also reload/refill between failed submissions. That recovery is part of the measured scenario, not evidence that arbitrary sites preserve an action after failure.

**run [R]** “Exact” here means the browser-exposed request contents, including header-map hash, not TCP/TLS wire serialization. Public demo comparisons include its complete query and header hash. **assumed — implication:** replay can serve deterministic/qualified actions, not arbitrary applications: tokens, timestamps, multipart boundaries, client-side state and failed-navigation behavior can change. Ignoring a field for measurement does not authorize changing it after approval. Never replay after an uncertain actual delivery.

## Q2. Service workers

**run [R]** Chrome's `chrome.debugger.getTargets()` reports these service workers as type `worker`; matching by the fixture worker URL and attaching with `targetId` succeeded (`targets.json`, `Q2_WORKER_ATTACH`). No Playwright bridge or consent connection is involved.

| Case | While held / released / dropped | Evidence |
|---|---|---|
| Page fetch, XHR and POST form through worker fetch handler | 0 / 1 / 0 each | `Q2_PAGE_SW`, `sw-page-*` receiver cases and source target in preview. |
| Worker sends after `postMessage` | 0 / 1 / 0 | `Q2_OWN_SW`, `sw-own-*`. |
| Background sync | 0 / 1 / 0 | `Q2_SYNC`, `sw-sync-*`; API available in this Linux Chrome. |
| Page fetch, XHR and POST form with bypass enabled | 0 / 1 / 0 each | `Q2_BYPASS`, `bypass-*`. |

**run [R]** Failed fetch reports a TypeError; failed XHR reports an error; form failure/release state is captured with its page URL/title/text. **read — fixture at `9b5dd784`** The worker also contains sent/failed page feedback, which is not separately asserted for its own sends.

**run [R]** Bypass changes behavior: a worker-only resource returns `worker-only fixture response` with the worker and `not provided without worker` (404) under bypass (`Q2_BYPASS_BREAK`). Bypass is not a transparent switch for offline/cache-backed applications.

**run [L]** Background sync retried a rejected request after about five minutes; the original interceptor held that retry, and shutdown released it. **read — final extension** Exact method/URL/body/header-hash repeats of explicit drops now fail immediately and are recorded as rejected candidates, rather than becoming another live pause. Owner-approved exact replay remains a separate single-use path. **run [R]** `Q2_NATURAL_RETRY` waits for Chrome's real retry, observed it after 300,003 ms, checks it failed with no remaining pause, and preserves the original zero-arrival assertion through shutdown.

**read — Playwright v1.65.0** The [service-worker guide](https://github.com/microsoft/playwright/blob/v1.65.0/docs/src/service-workers-js-python.md) distinguishes frame-owned events from worker-owned requests: context routing can route the worker's outgoing request, not the page-side request already handled by the worker. It also documents an unroutable worker-main-script update limitation. The [network guide at v1.65.0](https://github.com/microsoft/playwright/blob/v1.65.0/docs/src/network.md) recommends blocking service workers when ordinary routing misses traffic. Brief 17 used page routing; that negative result is not a claim that context routing can never handle workers.

**read — Chrome 157/MV3 storage API, checked 2026-11-07:** [session storage](https://developer.chrome.com/docs/extensions/reference/api/storage#storage_areas) clears on disable, reload, update and browser restart. **run [L]** Rejecting HTTP did not revoke the site’s queued sync intent. **assumed — unresolved boundary:** session-scoped repeat denial is not permanent cancellation of an application queue. A durable/autonomous worker path still needs approval before enqueueing or a qualified adapter; the check does not establish safety after extension removal or a later browser restart.

**assumed — qualification limit:** an already-running worker target being attachable does not establish race-free startup/replacement interception or attribution to one controlled tab. A worker can serve multiple clients, including owner tabs outside Claude. This check does not qualify those cases or offline-triggered background-sync retries after a browser restart. `Target.setAutoAttach` was unnecessary for the tested direct attachment and is not claimed as verified.

## Q3. Long holds and page timeouts

**run [R]/[L]** `Q3_LONG`, `Q3_CANCELED`, `Q3_RETRY`, `Q3_PAGE_STATES` and `Q3_FORM`, independently audited against the receiver:

| Case | Observed duration / page result | Arrivals |
|---|---|---:|
| Ordinary fetch | 30,006 ms, then done | 1 |
| Ordinary fetch | 120,003 ms, then done | 1 |
| Ordinary fetch, one long qualification | 600,005 ms, then done | 1 |
| POST form | Pending for at least 30 seconds, then completes | 1 |
| Fetch `AbortSignal.timeout(30000)` | TimeoutError; later continuation has invalid interception ID | 0 |
| XHR timeout 30 seconds | Timeout; later continuation has invalid interception ID | 0 |
| Explicit page timer retries after first attempt times out | Two request identities; first cancelled, second approved; first cancellation independently observed in `Network.loadingFailed` | Only attempt 2, once |

**run [R]/[L]** The fixture receiver has no arrival before each release. The surviving requests show no Chrome timeout at the measured durations. The form screenshots show its pending and completed page. **assumed — limit:** these observations establish neither an unlimited browser pause nor an application's willingness to wait. A cancelled request cannot be revived, and retrying is a new approval candidate. Internet transport loss after release remains “unknown, do not retry,” not an exactly-once transaction guarantee.

## Q4. Live connections, typed text and settling

**run [R]** A WebSocket handshake reached the receiver with no `Fetch.requestPaused` for `/socket` (`Q4_WS_HANDSHAKE`). Holding it through Fetch did not exist as an option. Network events identify a newly created WebSocket and its handshake; after reattach, an idle existing connection has no creation event, although later frames are observable (`Q4_WS_PREATTACH`). WebTransport exposes creation/establishment events when enabled early, but no recreation event on reattach; its independent QUIC receiver records datagrams on both sides of attachment. WebRTC data messages arrive at the other local peer without the watched network events; `Media.enable` is unavailable through this debugger route.

**run [R]** `Runtime.queryObjects` provides a separate inventory: query each native prototype in the current document's normal realm and inspect its instances, then release the debugger handles. On reattach *before new data*: one open WebSocket, two open RTC data channels, and one ready/not-closed WebTransport were found (`Q4_*_IDLE_INVENTORY`). This uses prototypes, not fixture-specific object names. **assumed — limit:** this is not proof of absence across every iframe, isolated realm, worker or hostile prototype replacement. It also does not bind future connections atomically to an input action. A product needs realm/target coverage and a conservative unknown state.

**run [R]** Five encodings—literal, URL, form, JSON-string escaping and UTF-8 base64—were found in all ten delayed fixture requests: one per encoding after five seconds and ten seconds. These are single-input timer models of autosave and an undo-send defer interval; Undo UI/cancellation itself is not exercised. The GET image carrier also matched. Every positive case was failed with zero receiver arrivals; an unrelated-text negative also had zero typed matches (`Q4_TYPED*`, final audit). Request-start timestamps measure settling at about 500 ms after each isolated input. All ten delayed sends begin outside that settle window. The ten-second maximum is a cap on waiting for busy pages, not a promise to catch sends after an earlier quiet gap.

**run [R] — public sites, synthetic text, no login:**

| Site | Typed carriers / missed expected forms / load false positives | Sends outside that action's settle window |
|---|---|---|
| Wikipedia | 1 / 0 / 0 | 0/1 |
| BBC News | 0 / not measured / 0; input + Enter produced no carrier | No observed carrier |
| Selenium demo | 3 / 0 / 0 | 0/3 |

**run [R]** `Q4_PUBLIC_*` and reduced public records retain expected fields, observed carrier requests, independent abort decisions, per-action settle windows and demo replay fingerprints. Each replay has its own action window; a later deliberately repeated action is not counted as the first action's delayed send. Public safety is stricter than the candidate rule: non-read/Fetch/XHR/Ping traffic is aborted on load, all new HTTP requests are aborted once typing starts, new sockets are DNR-blocked, WebTransport/RTC constructors are disabled for these public checks, and the tab bypasses service workers. The guard is separate from typed-text matching.

**assumed — limit:** zero observed false positives is not a semantic accuracy rate over all website traffic. No carrier means no measured recall denominator. These fixtures do not qualify compressed/encrypted text, splitting, custom-header carriers, custom/base64url encodings, uploads or hostile attempts to undo JavaScript guards. The public safety restrictions can suppress site behavior; results apply to this guarded run.

## Q5. Policy, native hosts and the Claude group

**run [R]** A local HTTP update manifest and signed CRX installed through `/etc/opt/chrome/policies/managed/aresos-17b.json`, using `ExtensionInstallForcelist`. `getSelf()` reports `installType: admin`, `mayDisable: false`; an owner UI toggle attempt leaves it enabled, and uninstall is rejected. A policy update downloaded the new CRX and connected as 0.2.1. The debugger bar is absent under force policy and present under a fresh non-forced install (`policy-debug-bar.png`, `policy-user-disable-refused.png`, `before-cancel-false.png`).

**read — Chrome 157.0.8103.38** [Debugger implementation](https://github.com/chromium/chromium/blob/157.0.8103.38/chrome/browser/extensions/api/debugger/debugger_api.cc) explicitly suppresses that warning for policy-installed extensions. **assumed — owner consequence:** the design needs its own visible control/stop affordance; it cannot rely on Chrome's Cancel bar in the managed deployment.

**read — Anthropic primary documentation, checked 2026-11-07** [Chrome integration](https://code.claude.com/docs/en/chrome) links directly to the [official extension listing](https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn), ID `fcoeoabgfenejglbffodgkkbkcdhcgfn` (listing version 1.0.105). **run [R]** `ExtensionInstallBlocklist` contains that ID; Chrome's Web Store shows the administrator block and disables installation (`claude-blocklisted.png`). No Claude account or extension login was used.

**run [R]** With both manifests registered, the user-level host runs first. With `NativeMessagingUserLevelHosts: false`, the system host runs instead (`Q5_HOST_DEFAULT`, `Q5_HOST_POLICY_FALSE`, `host-starts.txt`). Registration covers the explicit dev user-data root as well as the XDG default directory. **read — Chrome 157 policy** [NativeMessagingUserLevelHosts](https://github.com/chromium/chromium/blob/157.0.8103.38/components/policy/resources/templates/policy_definitions/NativeMessaging/NativeMessagingUserLevelHosts.yaml) describes that restriction. **assumed — production limit:** the image must also protect the system manifest and executable; this check deliberately points at runner-owned test scripts and does not establish a same-UID security boundary.

**run [R]** Taking an existing tab creates/moves it into a group titled Claude; opening a new tab places it in that same group (`Q5_GROUP_OPEN`). The headed test physically drags the original tab past the ungrouped tab, verifies its group ID became -1, and drops both simultaneous holds before detaching (`group-before-drag.png`, `group-after-drag.png`). A read outside the group returns `OUTSIDE_CLAUDE_GROUP`; its held POST never arrives (`Q5_GROUP_OUT`). Closing the group's tabs also delivers nothing (`Q5_GROUP_CLOSE`). All-tab title/URL listing remains allowed as the design requests.

## Changes for the design

**assumed — proposals from the run/read evidence above; no design or plan files were edited:**

| Section 6 dependency / 17b point | What it should say now |
|---|---|
| Image-managed install | Branded Linux Chrome accepts the local signed update route; qualify packaging/signing and immutable paths in the real image. |
| Owner-visible debugging bar / Cancel | Force policy suppresses the bar. Add an extension-owned visible control indicator and release action. Do not describe managed Chrome as showing Cancel. |
| Fail closed | Host/socket loss can drop while attached, but no tested post-pause DNR backstop prevents detach/reload/update release. Use fail-then-repeat for qualified operations; do not expose an unsafe paused request as a durable approval token. |
| Exact approval after repeat | Compare complete exposed request contents, consume one allowance, reject changed payloads/headers, and never ignore volatile fields automatically. Some sites will need adapters or approved input instead. |
| Service-worker exception | Direct worker-target interception works for the tested fixtures, including sync. Bypass covers page traffic but breaks worker behavior. Startup races, replacement, shared-worker ownership and durable queues remain qualification work; rejecting an HTTP attempt is not revoking an enqueued send. |
| Phone-length approvals | Chrome can preserve ordinary requests through the measured ten minutes, but application timeouts cannot be extended. Under fail-then-repeat, approval waits on a captured failed candidate rather than a live socket. |
| Live connections | Fetch cannot hold the WS handshake or live messages. Network events plus per-realm heap inventory improve detection, including pre-existing fixture connections; incomplete inventory means unknown. Keep input approvals/qualified adapters for live paths. |
| Typed-text rule | Keep watching for the entire controlled document lifetime and preserve a clear encoding/coverage contract. The action settle window alone misses all delayed fixture sends. |
| Native-host lookup | Set `NativeMessagingUserLevelHosts` false and protect the system registration and executable. A system manifest alone does not establish precedence. |
| Claude group | Enforce group ID membership on every operation and fail pending requests before detaching when membership ends. A name alone is not an authorization boundary. |

## Risks and PLAN-GAPs

- **run [L] / PLAN-GAP:** background-sync rejection schedules later attempts. A final audit shorter than that backoff missed a shutdown leak; the final regression waits for the natural retry.

- **run [R] / PLAN-GAP:** “Hold every request before it leaves” cannot be inferred from successful HTTP pauses: detach paths release them, WS handshakes bypass Fetch, and target/realm coverage is incomplete.
- **run [R] / PLAN-GAP:** the design's managed installation and its promised Chrome Cancel bar are incompatible in this Chrome version.
- **run [R] / PLAN-GAP:** a short settle window does not bound a page's own delayed sends; failed-candidate replay may also change page state.
- **assumed:** worker-target interception can affect other clients of the same worker. The check proves request holding, not per-tab attribution or race-free coverage of newly installed/restarted site workers.
- **assumed:** request fingerprints and receiver counts do not provide remote transaction deduplication. Approval grants need document identity, expiry and crash/reconnect rules in the eventual service; this raw check RPC is not that service.

## JUDGMENT-CALL

- **assumed — recommended:** choose fail-then-repeat over preserving live pauses for owner approval. It avoids the proven resume-on-detach leak, but can show a browser error or make a site's draft/token change. A qualified adapter may cost additional engineering per site. Returning to paused holds requires a new proven enforcement boundary.
- **assumed — recommended:** reject changed replays, including volatile fields, rather than silently normalizing them. The rejected alternative feels smoother but changes what the owner's approval authorizes. An exception must be explicit, site-specific and reviewable.
- **assumed — recommended:** surface unknown connection/worker coverage and worker-bypass behavior honestly. Do not equate a clean network event list with an idle page. Managed installation also needs an owner-visible stop control because Chrome's bar is suppressed.

## Not checked and why

- **assumed — scope:** real accounts, the owner's profile, real submissions, a real Claude Code permission prompt, production service isolation and the AresOS image were excluded by the brief. Browser runs happened only in CI.
- **run [R] — bounded coverage:** BBC produced no typed-text carrier in the exercised search input/Enter path; there is no measured recall claim for that site.
- **assumed — remaining qualification:** service-worker startup races/shared clients, all iframe/isolated-world heaps, hostile prototype changes and indefinite pauses were not covered by these fixtures. Worker termination here is a real renderer kill; graceful idle suspension with an active debugger/native port is not separately qualified.
- **read — scope:** Minecraft/Gradle requirements do not apply to this brief; no Gradle daemon was started.

**run [R] — selected screenshots:** [sandbox](screenshots/sandbox-status.png), [managed UI](screenshots/policy-user-disable-refused.png), [Claude blocked](screenshots/claude-blocklisted.png), [Cancel before](screenshots/before-cancel-false.png), [Cancel after](screenshots/after-cancel-false.png), [tab before drag](screenshots/group-before-drag.png), [tab after drag](screenshots/group-after-drag.png), [form held](screenshots/long-form-held.png), [form released](screenshots/long-form-released.png).
