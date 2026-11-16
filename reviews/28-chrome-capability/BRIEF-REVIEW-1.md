Reviewed against PR 27 at `8b7e799c`. No files modified.

Replacing the old catalogue is reasonable: keeping `chrome_submit` and its managed ask rule preserves that approval route. The problems below concern reference protections, executable contracts, and acceptance requirements.

1. **Blocking — Short references cannot provide the promised identity checks.**  
   **Where:** [28, item 3](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:174); CONTROL §6 “References”.  
   Both tabs can issue `e1`. Supplying tab B with tab A’s `e1` therefore resolves B’s element instead of detecting another tab’s reference. Restarting the service can likewise reissue an old string. PR 27 carries the session and tab explicitly. Reader reinstalls also need consideration: its element counter restarts while its privacy document id can survive.  
   **Fix:** Give references a namespace unique across tabs and service/Chrome epochs; include reader-instance/control identity where necessary. Test collisions after both tabs have issued references, and after restart **and reissuance**, not merely against an empty registry.

2. **Should-fix — The new check removes more protection than whole-page invalidation.**  
   **Where:** [28, stale-reference rules](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:179); CONTROL lines 635–639 and 1082–1084.  
   PR 27 compares the complete expected target, including `href`, title, options and states. The replacement checks only role/name, plus value for fill/select. A link can retain its name while changing destination and still run. Fresh classification and approval binding protect recognised asking actions; they do not restore the old check for free actions. Also, the change report starts immediately before the call, so it does not reveal changes since Claude’s previous read.  
   **Fix:** Retain an explicit semantic fingerprint of the target while excluding geometry and unrelated page state. Store full comparison data separately from the truncated displayed line. State the remaining protection loss accurately and test changed destinations/options with unchanged names.

3. **Blocking — Valid batches exceed the existing caller timeouts.**  
   **Where:** [28, `chrome_do`](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:216).  
   Thirty-two eight-second waits alone permit 256 seconds. PR 27’s protocol client times out changing calls after 30 seconds; the browser harness times out after 20. Ordinary input processing adds further time. The caller can receive an uncertain timeout while the service continues executing later steps.  
   **Fix:** Specify a total batch deadline and how remaining steps are reported, or explicitly permit coordinated timeout changes. Test through the real proxy/CLI transport, including disconnect behaviour, rather than only a fake bridge.

4. **Blocking — Paging has no progress rule for an oversized line.**  
   **Where:** [28, detail reads and paging](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:151).  
   A full text/name read can contain 100,000 characters, while `max` cannot exceed 40,000 and cuts must occur at line ends. A long field value or table row has the same problem. Returning no complete line cannot advance the cursor; returning it violates the bounds. Five tabs also need a defined allocation of the shared 48 KiB envelope.  
   **Fix:** Define continuation within oversized logical lines, cursor binding to the query/ref, and allocation across tabs. Measure the actual escaped JSON envelope, including metadata and pending operations. Require every nonterminal page to advance.

5. **Blocking — F1 cannot meet the four-call “everything” budget.**  
   **Where:** [28, folding rules](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:121) and [efficiency table](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:431).  
   PR 27’s F1 paragraphs exceed 200 characters. The first five paragraphs remain visible but individually truncated; the other 115 become a separate neighbour fold. Reading those first five tails by their individual references already requires five additional calls, before reading the neighbour/form folds.  
   **Fix:** Provide a way to expand a containing subtree or several references together, or revise the budget. Write the exact permitted call sequence before freezing acceptance.

6. **Should-fix — The proposed revision signal cannot support the waiting contract.**  
   **Where:** [28, `page_state`](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:92), `until`, and navigation completion.  
   PR 27’s revision comes from DOM mutations. Changing an input’s live value need not produce one, and a frame can change without changing the top document’s revision. Polling only that revision can miss a condition or leave a cursor valid over changed output. Requiring a new top document also makes successful fragment/history navigation time out; CDP explicitly supports [same-document navigation](https://chromedevtools.github.io/devtools-protocol/tot/Page/).  
   **Fix:** Define a lightweight aggregate state token covering readable frames and relevant live state. Define completion for same-document navigation and whether `until` supplements or replaces load completion. Test both cases.

7. **Should-fix — The collector contract is insufficient for the required renderer.**  
   **Where:** [28, items 1–2](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:77).  
   “Roles … today” does not supply the proposed structure: PR 27 maps native `TABLE`, `UL`, `OL` and `MAIN` to `generic`. The specified node fields omit option lists, error text and titles required by detail reads. Fold precedence, synthetic fold identity and character counts are undefined. A single “own text” string also loses order around inline children. Finally, PR 27 returns raw `role` attributes: inserting those unquoted permits forged outline lines despite escaping names.  
   **Fix:** Specify the node schema and permitted detail-fetch path, semantic role mapping, ordered text representation, fold precedence/count units, and synthetic-reference lifecycle. Normalise roles to recognised tokens and apply an explicit escaping contract to table/detail output.

8. **Blocking — The password fallback uses document coverage where it needs field/root coverage.**  
   **Where:** [28b, password marker](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:117); CONTROL lines 441–446 and 1075–1078.  
   The brief identifies shadow-root fields as potentially unseen by the marker, but enables name checking only “in a document the reader didn’t watch from its start”. A document-start marker can miss a shadow-root field’s password-to-text transition even when that field is clearly labelled Password. The documented residual only accepts fields without identifying hints, and the proposed test simulates an old document rather than this case.  
   **Fix:** Track coverage per root/field, or apply the name fallback wherever history is unobserved. Add a post-extension-load shadow-root fixture with an identifying label and a transition before first read.

9. **Should-fix — Restoring his tab requires more than recording its pin.**  
   **Where:** [28b, taking/releasing](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:145) and its exclusion of moving tabs between windows.  
   PR 27 records a group id and uses one global Claude group. Taking the last tab from his group can destroy that group; Chrome [removes groups when they become empty](https://developer.chrome.com/docs/extensions/reference/api/tabGroups). Restoring the old id cannot recreate it. Groups belong to windows, so taking tabs from multiple windows also needs an explicit policy consistent with the movement exclusion.  
   **Fix:** Define group reconstruction, window handling and fallback when the original window/group disappears. Test a sole-tab group and takes from two windows. Keep ordinary-tab identity and restoration separate from any background-input experiment.

10. **Should-fix — The baseline and latency requirements rely on inaccurate PR 27 claims.**  
    **Where:** [28, baseline instructions](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:58); CONTROL efficiency table.  
    At the supplied head there is no latency harness/check or report section containing latency targets. The fallback creates a job but leaves the latency acceptance criteria undefined, and the baseline file does not record timings. Some call-cost claims also overstate PR 27: `wait` already returns a read, `fill_form` already batches fields, and unchanged actions do not universally require another full read.  
    **Fix:** Correct these statements. Benchmark efficient existing call sequences, record latency samples and methodology before replacement, and define aggregation/tolerance. The new surface reduces public tool count, but still invokes expensive full facts internally; caller-call counts alone do not establish faster execution.

11. **Should-fix — The migration instructions and unchanged-test requirements conflict.**  
    **Where:** [28, migration order](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:334); [28b, inherited tests](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:268); CONTROL groups 1–13.  
    Stage 2 requires new tools beside old tools, including incompatible versions of the same names, while groups 14–16 must pass—including final catalogue-size budgets. More concretely, PR 27’s `matrices.mjs:80–84` asserts that taking never reloads and the first input triggers the reload. Brief 28b deliberately changes that behaviour, so retaining every assertion is impossible.  
    **Fix:** Define an internal migration switch or test-only legacy adapter. Apply catalogue budgets after removal. Explicitly map authorised behaviour-test changes for 28b while retaining receiver counts, binding and approval assertions.

12. **Should-fix — Several action adaptations and outcomes still need normative definitions.**  
    **Where:** [28, step table and execution rules](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:219).  
    PR 27’s select accepts an exact option **value**, whereas the new step also accepts labels; ambiguity and precedence are unspecified. Page scrolling without a reference has no defined target, while the unchanged dispatcher requires one and hit-tests its centre. The instruction that every step follows `payload` cannot literally cover wait/dialog. Results do not define operation identities for completed steps, failure shapes, or the mapping of PR 27’s uncertain free-operation outcomes.  
    **Fix:** Specify these translations and result variants, including errors after partial execution. Give wait/dialog explicit branches and define page-scroll targeting without bypassing the existing input safeguards.

CHANGES-NEEDED