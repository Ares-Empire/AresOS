Reviewed through `eae82d45`, including the commit that arrived during this check, against PR 27’s checkout at `8b7e799c`. No files modified. Verification was static code tracing and Python serialization arithmetic; no browser tests ran. The pending asking-read implementation remains an intended dependency.

| Finding | Status | Reason |
|---|---|---|
| **N1** | **Fixed** | Five random consonants give **4,084,101** combinations. The process-wide counter prevents reuse within a run; cross-run collisions are now described honestly and tested deterministically, including a forced collision. |
| **N2** | **Fixed, with BUILDER-NOTE below** | The briefs now authorize bridge time limits, late-reply draining, queue expiry, bounded extension waits and the final input check. This addresses PR 27’s blocking `Bridge.read`, unexpected-ID rejection and serial dispatcher. Package 28 builds the shared mechanism; 28a adds input handling. |
| **N3** | **Fixed** | The revised F2 allowance and `max: 40,000` accommodate quoting and JSON escaping. The other revised worked examples also fit; calculations below. |
| **N4** | **Partly — BLOCKS-BUILD** | Both briefs and section 6’s behavioral rules now open the saved address. Section 6’s group-15 test still requires refusal after navigation. |
| **N5** | **Fixed** | The reader installed by an in-place read explicitly retains its passive observers. This matches PR 27’s revision and password-history tracking. The latest drop/paste exception needs the wording cleanup noted below. |
| **N6** | **Fixed** | Staged waits necessarily cross the cutoff: stages arrive at 3.5, 7, 10.5 and 14 seconds. The fourth wait expires at 12 seconds. A separate delayed-setup test checks actual dispatch, and later observation checks for abandoned work. |
| **N7** | **Fixed in the specification** | Eligibility follows the field’s unknown-history mark, including late shadow roots. Package 28 expressly permits correcting document-only eligibility and requires an approved asking-read test for that case. Its pending PR 27 binding cannot yet be verified in the supplied checkout. |
| **N8** | **Fixed** | An unanswering frame is explicitly non-overridable, including with `reload: true`; the test agrees. |
| **N9** | **Fixed** | 28a now names the actual insertion points: `execute`’s confirmation/page serialization, `free`’s page stage and `steps`’ warning. These match PR 27’s adapter and `Engine.stage`; full payloads and comparisons remain intact. |

The independently recomputed sizes support N3’s fix. These are serialization models, not measurements of the unbuilt renderer:

| Read | Outline characters | Escaped content plus modeled envelope | Budget |
|---|---:|---:|---:|
| F1 first outline | 3,297 | 3,864 | 6,000 |
| F1 full, two pages | 60,196 | 61,581 | 75,000; up to 3 calls |
| F1 form | 4,254 | 4,969 | 6,000 |
| F2 table | 20,121 | 23,044 | 23,600 |

For F2, each data row is **100 outline characters**, including its newline, and **113 characters after JSON escaping**. Thus 200 rows cost 22,600 escaped characters before the header, table line and envelope. The revised allowance is correctly **14,400 + 7 × 1,200 + 800 = 23,600**. The table fits one `max: 40,000` result and the 48 KiB bound.

Representative calculations also put 25 ordinary tab lines around 3,050 characters and F5’s bounded change report around 1,670. F4’s call sequence exposes the fields before filling them, and F7 now has its own fixture rather than borrowing the oversized listing. Actual envelope sizes, catalogue totals and latency still need the specified CI measurements.

**The split is workable.** Package 28 can be built and merged independently after PR 27 merges: `chrome_outline` is test-only; the public catalogue and generated files remain unchanged; old actions retain `reference`, `expected` and whole-view checks. Deferring projection of old results avoids breaking their expected-state comparisons. The four field exceptions are explicitly shared changes.

Its tests exercise the additions through both real transports: outline rendering, detail reads, paging, state, waiting, references, address projection and deadlines. It also measures the read budgets before handing them to 28a. Package 28a receives the reference identities, reader instance, state token, renderer, address function, field rules, deadline mechanism, fixtures and baseline it needs; it expressly adds fingerprints and switches the catalogue and action contract together. Package 28b owns in-place access and the replacement take/close rules. I found no feature responsibility lost between the three packages.

The remaining points are:

1. **BLOCKS-BUILD — N4’s contradictory group-15 assertion remains.**  
   **Where:** [CONTROL.md:1577](/var/home/ares/AresOS-28-chrome-capability/docs/design/CONTROL.md:1577), versus [28a:416](/var/home/ares/AresOS-28-chrome-capability/briefs/28a-chrome-act.md:416) and [28b:149](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:149).  
   **Why:** Group 15 still says a take **and opening the tab’s address** are refused when the tab moves on. Group 17 and both briefs require opening the address saved in `seen`. A builder cannot satisfy both assertions, and the briefs prohibit silently choosing between them.  
   **Fix:** Make group 15 require stale refusal for `chrome_take`, while `chrome_open` opens the saved address regardless of subsequent navigation.

2. **BUILDER-NOTE — The deadline must include pending-approval projection.**  
   **Where:** [28:499](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-read.md:499); PR 27’s [Engine.request](/var/home/ares/AresOS-20-chrome-read/control/aresos_control/engine.py:674), [response envelope](/var/home/ares/AresOS-20-chrome-read/control/aresos_control/engine.py:804) and [Chrome.pending_state](/var/home/ares/AresOS-20-chrome-read/control/aresos_control/chrome/adapter.py:127).  
   **Why:** The engine projects pending operations before dispatch and again when constructing the response. A reserved Chrome operation invokes `Bridge.call('validity', …)` even with `resolve_checks=False`. Starting the timer only inside the new adapter read would leave those waits outside it.  
   **Fix:** Use the permitted base helper to establish the request’s budget before the initial projection and carry it through response construction. Preserve pending warnings and distinguish an unchecked validity from a refused approval. Add a real-transport deadline case with an outstanding approval whose frame does not answer. This implements the already specified whole-call bound; it requires no new product decision.

3. **BUILDER-NOTE — The latest drop/paste fallback needs an exception in the earlier watcher prohibition.**  
   **Where:** [28b:222](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:222), versus [28b:327](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:327) and its manifest exception.  
   **Why:** `eae82d45` conditionally authorizes passive listeners from document start, while the earlier paragraph still says nothing observes a tab before a read. The specific new exception makes implementation possible, but the absolute wording is now false.  
   **Fix:** Qualify that paragraph with the narrowly defined drop/paste record. Keep it separate from password-history evidence and the on-demand reader.

4. **BUILDER-NOTE — Apply the new refusal exception consistently in the harness map.**  
   **Where:** [28:883](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-read.md:883).  
   **Why:** The brief authorizes changing a formerly successful unread-field submission into a refusal, then says receiver/question assertions never change. An affected case necessarily changes to no question and zero arrivals.  
   **Fix:** Record those exact consequential changes under exception 4; preserve the original approval and receiver assertions for cases that remain permitted.

Apart from the group-15 contradiction and these implementation/wording notes, the three briefs and section 6 agree on the revised package boundaries and decided behavior.

CHANGES-NEEDED