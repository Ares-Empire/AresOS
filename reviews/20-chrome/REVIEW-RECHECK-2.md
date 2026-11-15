At `8627e65e`, both prior findings are **FIXED**. No remaining FIX found in the scoped diff.

1. **FIX — FIXED: GET-search exemption bypassed Pay/Delete.**  
   [guard.js:83](../../control/chrome/extension/guard.js:83) and [guard.js:91](../../control/chrome/extension/guard.js:91) now prioritize explicit cues across activation and submission paths.  
   **Reproduction:** Continue calls `.click()` on Pay/Delete inside a GET search form. Previously its harmful handler ran without a question; it now stays held. Retained receiver evidence shows **0 before approval, 1 after, 1 after repeat** in all four artifacts. Ordinary GET searches—including “Pay for lunch”—remain free.

2. **FIX — FIXED: affected-item binding stopped at shadow boundaries.**  
   [reader.js:20](../../control/chrome/extension/reader.js:20) crosses shadow hosts and closed slots; [reader.js:230](../../control/chrome/extension/reader.js:230) resolves the affected container. Both bindings retain its text and visible fields.  
   **Reproduction:** prepare Delete for Invoice A, then change the surrounding row to Invoice B. Previously the approval could delete B; it now refuses. All eight native-list/ARIA-row, open/closed and slotted variants record zero stale-approval arrivals, then exactly one approved **Invoice B** arrival.

The remaining diff revealed no harmful regression. Confirmation drafts and item quantities stay bound; password exclusions remain intact. Mail and shared runtime files are unchanged, and both retained Mail runs pass.

[REPORT.md:3](./REPORT.md:3) matches the code and retained evidence: Chrome runs `43166895797` and `43167000276` cover both install modes on `495c0b34`, with **82 cases, 224 Python tests and 257 Node tests per artifact**. Auditor hashes, receiver summaries and shared-workflow records agree. Runtime/test/workflow source is unchanged afterward.

[KNOWN-LIMITS.md](./KNOWN-LIMITS.md:1) matches the decided residuals, omits the repaired defects, and conceals no demonstrated remaining FIX within this scope.

Locally, **244 browser-free Node tests and 17 Python policy tests passed**; generated artifacts and runtime hash match. Initial broader attempts hit three sandbox socket failures and five scratch-file failures. No file was created or edited. Raw browser artifacts are absent, so their full audit was checked through retained records, not rerun. No browser, profile, container or GitHub mutation was used.

SAFE