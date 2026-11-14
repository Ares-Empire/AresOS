Reviewed through `5bbc4a94`, against PR 27 at `8b7e799c`. No files modified. Verification was static inspection plus a small Python calculation of table serialization costs; no browser tests ran. The pending asking-read tool is an intended dependency, not a finding.

The 12 original findings:

| # | Status | Reason |
|---|---|---|
| 1 | **Partly** | The process-wide counter, connection identity and reader-instance id fix cross-tab collisions, dropped references and reader reinstalls. The three-letter epoch can still repeat after its entry leaves the last-100-runs record; see N1. |
| 2 | **Fixed** | The fingerprint now retains full destinations, options, values and semantic target data, independently of displayed truncation. The remaining loss of surrounding-page protection is stated accurately. This matches the relevant comparison data in PR 27’s `targetFacts` and `payload`. |
| 3 | **Partly** | Total deadlines and partial results are specified, but PR 27’s blocking bridge and extension dispatcher cannot enforce them within the permitted changes; see N2. |
| 4 | **Fixed** | Oversized lines can continue, cursors bind the query and state token, every page must advance, and allocation measures the escaped envelope across tabs. |
| 5 | **Fixed** | `full` bypasses folds and truncation. The prescribed full read followed by cursors removes the five separate paragraph-tail reads. |
| 6 | **Fixed** | The aggregate token covers frames and live field state; same-document navigation and navigation combined with `until` now have explicit completion rules. The observer prohibition introduced in 28b creates a separate conflict, N5. |
| 7 | **Fixed** | The revision supplies semantic roles, ordered text parts, options/error/title data, detail fetching, fold precedence/counts and synthetic-reference lifecycle. It also closes PR 27’s raw-role interpolation problem. |
| 8 | **Fixed** | Within the lead’s explicitly narrowed field policy, names apply everywhere and filled inputs in shadow roots discovered late remain unread. The new fixture targets the actual discovery gap in PR 27’s observer traversal. |
| 9 | **Fixed** | Per-tab wrapper groups resolve the multiple-window problem. Restoration now records position, pin and group appearance, reconstructs vanished groups, and defines fallback and error reporting. |
| 10 | **Fixed** | The baseline acknowledges PR 27’s missing latency harness, uses its existing wait/form-fill capabilities efficiently, records timings and defines comparison tolerances and a fallback job. |
| 11 | **Fixed** | Test-only `chrome_old_` tools resolve name collisions; catalogue measurements use the new catalogue. Harness maps explicitly authorize the changed staleness, unread-field and take/reload assertions while retaining approval and receiver assertions. |
| 12 | **Fixed** | Select precedence and ambiguity, referenced scrolling, wait/dialog branches, operation identities, uncertainty and partial-result shapes are now defined. These translations fit PR 27’s corresponding paths. |

New findings caused by the revision:

1. **Should-fix — The reference epoch can repeat during normal operation.**  
   **Where:** [28:442](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:442), [CONTROL:1315](/var/home/ares/AresOS-28-chrome-capability/docs/design/CONTROL.md:1315).  
   After enough starts, an earlier prefix leaves the last-100 record and becomes eligible again. Since the numeric counter restarts, an old reference can resolve to a new element **without any lost or restored store**. Section 6’s stated residual requires store loss, and its absolute uniqueness promise is false.  
   **Fix:** Persist a non-repeating generation/counter, or use a sufficiently large random epoch and describe its probabilistic guarantee honestly. Test reuse beyond the retention window.

2. **Blocking — The deadline requires changes the brief prohibits.**  
   **Where:** [28:652](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:652), [28:226](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:226).  
   PR 27’s [bridge read](/var/home/ares/AresOS-20-chrome-read/control/aresos_control/chrome/bridge.py:23) blocks on the socket; the daemon gives that socket a [15-second timeout](/var/home/ares/AresOS-20-chrome-read/control/aresos_control/daemon.py:152). Extension commands execute serially and await frame queries and input setup without the proposed deadline. One query can exceed the entire eight-second read allowance; an input step started near second 12 can continue beyond second 18. Returning early from the service would leave extension work pending. Yet bridge changes and deadline checks throughout dispatch are outside the stated exceptions.  
   **Fix:** Explicitly authorize deadline propagation through the bridge and extension, bounded waits, and an expiry check before dispatch. Define recovery/draining so expired work cannot execute later.

3. **Blocking — F2’s revised exact call sequence cannot meet its budget.**  
   **Where:** [table format](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:395), [fixture](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:923), [budget](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:1070).  
   With 200 × 6 cells of 12 ASCII characters, cell text totals 14,400 characters. Quoting every cell and using the required separators already consumes essentially 20,000 outline characters before the column header. My minimal example measured **20,072 outline characters and 22,686 as a JSON string**, before the response envelope. The allowed total is **18,720**. Longer cells worsen the one-call `max: 20,000` constraint.  
   **Fix:** Revise both the call sequence and overhead allowance together—for example, allow cursor pages and a measured additive formatting/envelope allowance. Keep mandatory quoting.

4. **Should-fix — Opening a listed tab’s address has contradictory navigation rules.**  
   **Where:** [28:707](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:707), [28b:114](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:114), [CONTROL:538](/var/home/ares/AresOS-28-chrome-capability/docs/design/CONTROL.md:538).  
   Brief 28 explicitly opens the saved address regardless of subsequent navigation; its group-15 test requires success. Brief 28b and section 6 require refusal after navigation, and group 17 tests that refusal. The inherited groups therefore cannot all retain their assertions.  
   **Fix:** Choose one rule across the documents. If 28b intentionally changes the behavior, state that transition and authorize the corresponding group-15 assertion change.

5. **Should-fix — “No observer” conflicts with the inherited reader and state token.**  
   **Where:** [28b:184](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:184), [28:194](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:194).  
   Brief 28b prohibits any observer in his tabs while retaining the same reader, waiting and cursor rules. PR 27’s [reader observers](/var/home/ares/AresOS-20-chrome-read/control/chrome/extension/reader.js:43) supply mutation revisions and remembered protection. Removing them leaves the specified token unable to detect ordinary text changes through its DOM-change count.  
   **Fix:** Distinguish the removed always-installed marker from passive observers installed with an on-demand reader, and explicitly permit the latter—or specify a replacement token mechanism.

6. **Should-fix — The deadline test does not force the deadline to be exercised.**  
   **Where:** [28:1016](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:1016).  
   Twenty eight-second waits are insufficiently specified: an unmet first condition stops the list after eight seconds under the new timeout rule; immediately satisfied conditions need not reach the deadline. Also, “no step starts after second 12” does not establish the test’s stronger claim that no input occurs after second 12.  
   **Fix:** Specify staged conditions that carry execution across the cutoff, plus a deliberately delayed input boundary. Align the assertion with whether the cutoff governs step start or actual dispatch.

7. **Should-fix — The asking read omits the late-shadow-root case.**  
   **Where:** [28:176](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:176), [28:736](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:736), [CONTROL:1255](/var/home/ares/AresOS-28-chrome-capability/docs/design/CONTROL.md:1255).  
   A filled input in a late-discovered root is unread inside an otherwise watched document. Section 6 places it under the asking-read behavior, but brief 28 restricts that tool to unwatched documents and lists only those document cases.  
   **Fix:** Define eligibility by the field’s unknown history, including late roots. Require this case in the merged PR 27 contract and test it through the asking tool.

8. **Should-fix — Explicit reload disagrees with the unanswering-frame test.**  
   **Where:** [28b:218](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:218), [28b:433](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:433).  
   The normative rule permits explicit reload of an unknown-clean tab except for three named conditions. An unanswering frame is not one of them, but the test requires it to remain refused even with `reload: true`.  
   **Fix:** Add unreadable frame coverage to the non-overridable conditions, or explicitly authorize the alternative and update the test.

9. **Should-fix — Address projection names the wrong stage insertion point.**  
   **Where:** [28:284](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:284), [protected functions](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:830).  
   There is no `stage` method in PR 27’s Chrome adapter. [Its `execute` method](/var/home/ares/AresOS-20-chrome-read/control/aresos_control/chrome/adapter.py:461) serializes the raw reply into the stage callback; [Engine.stage](/var/home/ares/AresOS-20-chrome-read/control/aresos_control/engine.py:261) stores and audits it. Sanitizing questions and free-operation output does not cover approved-operation stages. The exception names a nonexistent method while protecting `execute`.  
   **Fix:** Explicitly authorize projection before stage serialization, or name a Chrome-specific stage helper in the engine. Preserve full addresses in payloads and comparisons.

I would **split brief 28**. A clean first package is the baseline, shared privacy/address projection, and read-only outline/state/rendering/paging foundations, exercised through internal CI commands while PR 27’s public catalogue and action-reference contract remain working. A second package should switch the catalogue and references together with navigation, batching, reveal, harness migration and final budgets. That gives each package a coherent implementation and review boundary.

CHANGES-NEEDED