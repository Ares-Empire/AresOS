Two **FIX** findings remain at `65aca3e6`. The nine original package-review reproductions are fixed, but the changed guard and reader still have these gaps.

1. **FIX — the GET-search exemption bypasses explicit payment/deletion labels.**  
   [guard.js:83](../../control/chrome/extension/guard.js:83), [guard.js:117](../../control/chrome/extension/guard.js:117), [guard.js:146](../../control/chrome/extension/guard.js:146).

   `asks()` returns early for a search-form submitter, before inspecting its explicit label. Submission paths independently grant the same exemption. The service’s corrected classification would ask for a direct click on “Pay”, but the page guard lets a script activate it during Claude’s free input.

   **Reproduction:** put a submit button labelled **Pay** inside a GET form marked `role="search"`. Its click handler posts to a payment receiver. Have an ordinary “Continue” handler call `payButton.click()`, then invoke Continue through the tool.

   A browser-free probe using the actual guard and wrapper fixture produced:

   ```json
   {"nativeArrivals":["payment-handler"],"held":[]}
   ```

   The payment handler runs without its question. This is explicit payment evidence being bypassed, rather than an unrecognisable action.

   **Fix:** make explicit asking cues take precedence over the search exemption throughout script activation and submission handling. Preserve ordinary GET searches. Add Linux receiver tests proving no payment/deletion handler runs before its separate approval.

2. **FIX — an affected-item binding stops at a shadow boundary.**  
   [reader.js:216](../../control/chrome/extension/reader.js:216), [background.js:654](../../control/chrome/extension/background.js:654).

   The expanded selector fixes ordinary ARIA rows, but `Element.closest()` cannot cross a shadow root. A Delete button inside a web component therefore misses the surrounding list item or row. Its approval can contain only “Delete” and remain valid when the visible affected item changes.

   **Reproduction:** render:

   ```text
   li: “Invoice A”
     custom element
       shadow root
         button: “Delete”
   ```

   Prepare Delete, then update the same row/component to represent Invoice B while approval waits.

   Executing the actual reader functions against DOM doubles returned `"Delete"` both before and after. A separate dispatcher probe accepted the identical binding and dispatched input for Invoice B:

   ```json
   {"sameBinding":true,"affectedItemInApproval":"Delete","received":["Invoice B"],"dispatched":true}
   ```

   This can delete a different item after an ordinary component update.

   **Fix:** resolve the smallest affected item through composed ancestry, crossing shadow hosts, and bind its identifying text. Cover open and closed roots, native list items and ARIA rows, with changed-item refusal tests.

The earlier findings have these dispositions:

| Earlier finding | Status | Evidence |
|---|---|---|
| 1. Delayed native-dialog continuation | **FIXED** | [background.js:418](../../control/chrome/extension/background.js:418) establishes return-boundary protection. The ordinary-dialog matrix covers Claude, owner and independent task origins. Borrowed-native dialogs follow the explicitly decided asking/unguarded rule. |
| 2. Inherited-origin frames omitted | **FIXED** | [background.js:619](../../control/chrome/extension/background.js:619) authenticates and includes blank/srcdoc frames; binding and arming include them. Dedicated editor and submission cases are retained. |
| 3. Modified deletion keys | **FIXED** | [policy.py:74](../../control/aresos_control/chrome/policy.py:74) canonicalises keys; classification and dispatch compare the same tuple. Modified-key regressions pass. |
| 4. Adapter overrides explicit pay/delete cues | **FIXED** | [policy.py:133](../../control/aresos_control/chrome/policy.py:133) prioritises explicit effects; [adapter.py:620](../../control/aresos_control/chrome/adapter.py:620) independently rejects forbidden trusted operations. The separate guard gap is finding 1 above. |
| 5. ARIA item/row binding | **FIXED** | [reader.js:216](../../control/chrome/extension/reader.js:216) includes the requested roles and named sections; mutation cases cover them. The additional shadow-boundary gap is finding 2 above. |
| 6. Unmarked audit summaries | **FIXED** | [engine.py:261](../../control/aresos_control/engine.py:261) structures stages under `untrusted_content`; historical Chrome summaries are protected when read. S12 exercises status, evidence, logs and error envelopes. |
| 7. Stock acting observations | **FIXED** | [background.js:677](../../control/chrome/extension/background.js:677) collects bounded observations or explicitly reports their unavailability. The actual-notice regression passes. |
| 8. Unbounded recipient/name sentence | **FIXED** | [adapter.py:283](../../control/aresos_control/chrome/adapter.py:283) supplies exact overflow counts and positional long-name descriptions while retaining full values below. Boundary regressions are present. |
| 9. Incomplete cross-site password matrix | **FIXED** | [password-fixtures.mjs:1](../../control/chrome/ci/password-fixtures.mjs:1) shares the complete fixture across origins; [matrices.mjs:295](../../control/chrome/ci/matrices.mjs:295) exercises reading, form reading, preparation and approval with ingress scanning. |

Verification and report checks:

- **Locally run:** 212 focused Node tests passed; 16 Python policy tests passed. Generated artifacts match definitions. The runtime hash matches the report: `74741aa57ecbd62922500cbb600426719ef5141d35efd3b7750c1b13683a6269`.
- The four retained final audit records match the current **80-case inventory**, report counts, verdicts and auditor-source hashes. They record 220 Python tests, 243 Node tests, 1,219 page plus 139 adapter receiver sequences per artifact, and no password sentinel or forbidden Runtime value events.
- Raw final browser artifacts are absent from this checkout, so I checked retained records rather than independently rerunning their full audit. Storage-writing suites were not rerun.
- All **29 first Chrome feature rows** retain tool/path and named-test coverage. Group **12** is the only deferred group, explicitly false until 18d. Owner Enter retains its decided “passes in CI, panel to confirm” status.
- The combined diff since `d3babf1f` stays within the allowed paths. Runtime/test/workflow source is unchanged since the recorded acceptance source `0ae4ac41`. Tool descriptions accurately disclose the decided dialog and reload rules.
- Runtime/generated diff whitespace checks pass; the full review range flags trailing whitespace in retained pre-fix test output only.

No files were edited, no browser/profile or container was accessed, and nothing was pushed or posted to GitHub.

CHANGES-NEEDED