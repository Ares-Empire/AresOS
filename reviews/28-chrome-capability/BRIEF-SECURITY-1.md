Reviewed branch `c299b3e3` against PR 27 at `8b7e799c`, including the owner’s decisions and PR 27’s known limits. I ignored `DRAFT-NOTES.md` and changed no files.

The proposed approval path still binds fresh form, draft, destination and item data. Removing whole-view staleness does **not itself bypass an asking action**. The blockers are the credential exceptions, ambiguous reference identities, destructive batch behaviour and protections around his existing tabs.

1. **FIX — The proposed password exception violates the stated bar.**  
   **Where:** [28b, password marker](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:112), [CONTROL, accepted password leak](/var/home/ares/AresOS-28-chrome-capability/docs/design/CONTROL.md:1075).

   **Scenario:** He reveals a password in a shadow-root field before the reader arrives. Its label is simply “Code”, so neither the document observer nor the password-word fallback identifies it. The design explicitly permits returning its value. Separately, the proposed marker watches `type`, whereas PR 27 also protects historical `autocomplete` and masking-style changes. A text field identified as an OTP only by its name can also escape the check when the document is considered watched from its start.

   **Harm:** Passwords or sign-in codes reach Claude. This cannot be accepted because a screenshot tool would also expose them.

   **Fix:** Preserve all existing password provenance, including autocomplete and masking transitions. Apply recognisable credential-name checks regardless of document age. Where provenance is missing—including previously existing shadow roots—omit uncertain field values before reading them, or hand the page back. Test these cases through every new read and result surface. Remove this entry from “Known limits”.

2. **FIX — URL secrecy applies to the tab list but not consistently to subsequent outputs.**  
   **Where:** [28, read details](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:150), [opening an existing address](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:193), [CONTROL, binding fields](/var/home/ares/AresOS-28-chrome-capability/docs/design/CONTROL.md:794).

   **Scenario:** The list hides `?code=…` or `#access_token=…`, but `chrome_read` returns the page URL, reading a link returns its “full address”, or `chrome_open(tab=…)` returns the copied page’s URL. PR 27’s existing read and binding structures contain full URLs. Thus the promise that Claude never sees the copied address’s query is not implemented by the prescribed unchanged paths. Path-based sign-in links are another uncovered case.

   **Harm:** Authentication tokens or sign-in capabilities enter Claude’s context and potentially logs.

   **Fix:** Specify one public URL projection for every output: reads, details, navigation results, changes, errors, operation descriptions and logs. Keep complete destinations privately for navigation and exact binding. Omit query/fragment values and redact or refuse recognisable credential-bearing paths. Do not weaken destination comparison to accomplish redaction.

3. **FIX — The short-reference namespace cannot enforce its own cross-tab and restart promises.**  
   **Where:** [28, references](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:172).

   **Scenario:** Both tabs independently issue `e5`. A reference from tab A submitted with tab B now resolves to B’s valid `e5`; the service cannot determine that it “belongs to another tab”. Likewise, after a service restart and new reads, an old `e5` can collide with a newly issued one. Attaching the *current* internal session/document identity during resolution does not establish which reference the caller originally saw.

   **Harm:** A stale or misplaced reference can fill or activate a different element. Fresh classification still protects recognised sends, but ordinary inputs can overwrite data or disclose supplied text.

   **Fix:** Give public references an unambiguous tab/session/process namespace, or use globally unique opaque identifiers. Retain explicit rejection across restarts and eviction. Test collisions after new references have been issued, not merely while the restarted table is empty.

4. **FIX — Batches waive the value check precisely when it is needed.**  
   **Where:** [28, batch execution](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:244).

   **Scenario:** All references pass preflight. An early step waits, changes a selection or loads an existing draft into another field. The owner may also type during that interval. A later `fill` checks only role/name and replaces the newly arrived text, because the design permits intervening value changes without establishing their cause.

   **Harm:** Unsaved typing or a loaded draft is overwritten without being shown to Claude. This contradicts CONTROL’s promise that filling never overwrites something unseen.

   **Fix:** Recheck values immediately before each destructive edit. Accept only a specifically expected transition from the batch’s earlier work; otherwise stop and return the changed field. Keep complete comparison data privately even when the displayed value is folded.

   Also make the between-step barrier inspect queued held submissions, dialogs and document identity. PR 27’s asynchronous `held_step` handler records an observation; it does not itself stop a new batch loop. A held step arriving after the previous reply must stop subsequent inputs, including after a `wait`.

5. **FIX — Listing a tab does not bind a later read, take or close to the page selected.**  
   **Where:** [28b, looking in place](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:85), [taking and closing](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:131).

   **Scenario:** Claude correctly selects the university tab from the list. Before its call, the owner navigates that same tab to private correspondence. `chrome_read(tab, request="check my lectures")` now reads the unrelated page. Naming the actual site in the result reveals the mistake only after disclosure. The same race can close or reload a replacement page.

   **Harm:** Unrelated private content reaches Claude, or a different page is disturbed despite correct initial permission interpretation.

   **Fix:** Return a service-issued observation token with the listing and bind subsequent owner-tab operations to the observed session and page identity. Refuse changed targets before extracting content or changing the tab. This needs no extra owner question when the intended tab is unchanged.

   Include the connected profile in that scope. PR 27 accepts one host, but its handshake does not select an owner-approved profile; “whichever extension connected” is not a guarantee that another profile cannot silently become the source after reconnection. Pin the intended profile/connection identity and invalidate observations on changes.

6. **FIX — `reload_state` is not sufficient evidence that taking or closing loses no work.**  
   **Where:** [28b, take and close checks](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:135), [PR 27’s detector](/var/home/ares/AresOS-20-chrome-read/control/chrome/extension/reader.js:412).

   **Scenario:** A page updates an input’s `defaultValue` to match its current value while keeping the draft only in application memory. The detector reports clean. A canvas editor has no ordinary editable field at all. A form submission or upload may also be underway while the current document still looks like a clean GET page.

   **Harm:** Automatic reload or close loses work or interrupts an ongoing operation. Reopening a tab does not establish restoration of application memory.

   **Fix:** Treat unknown cleanliness as unknown, not clean. Use reliable edit history or adapter evidence where available; otherwise preserve the tab and offer the owner the explicit destructive choice already contemplated for taking. Keep unsupported editor state, unreadable frames, pending navigation/submission and unresolved dialogs out of automatic close/reload. Recheck immediately before the destructive operation.

   The rule must follow **owner-origin tabs after taking**, rather than treating group membership as ownership. Tests should include these cases, not just native fields differing from their defaults.

7. **FIX — Page-controlled roles can forge outline structure.**  
   **Where:** [28, outline grammar and escaping](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:104), [PR 27’s role reader](/var/home/ares/AresOS-20-chrome-read/control/chrome/extension/reader.js:194).

   **Scenario:** The reader returns an arbitrary `role` attribute verbatim. The new grammar places that value outside quotes, while its escaping rule protects names and values. A role containing newlines and apparent controls/references can therefore manufacture outline lines.

   **Harm:** A page can misrepresent the association between displayed controls and genuine references, steering ordinary input toward another element. The surrounding untrusted marker helps, but does not repair corrupted tool-generated structure.

   **Fix:** Render roles from a validated vocabulary, with a safe fallback. Escape every page-derived fragment in expanded tables, ancestor paths and change reports too. Specify that stale-reference diagnostics containing the current line remain inside `untrusted_content`. Add malicious-role and diagnostic tests alongside H1.

8. **KNOWN LIMIT — An unchanged DOM element can acquire a different meaning.**  
   **Where:** [CONTROL, per-element checks](/var/home/ares/AresOS-28-chrome-capability/docs/design/CONTROL.md:623).

   **Scenario:** A page retains the same “Open” node and name while replacing its link destination or surrounding row. The reference remains valid.

   **Harm:** Claude can follow a different ordinary link or act with outdated surrounding context.

   **Why acceptable:** Under the owner’s bar, this is an ordinary-looking step misleading the agent. Fresh classification still catches recognised asking actions, and the retained approval binding covers the current affected item, form and draft. This does **not** justify accepting credential disclosure or the overwrite cases above. Comparing the resolved link destination would cheaply narrow this limit without restoring whole-view binding.

9. **KNOWN LIMIT — `request` records Claude’s explanation; it does not prove permission.**  
   **Where:** [CONTROL, request interpretation](/var/home/ares/AresOS-28-chrome-capability/docs/design/CONTROL.md:505).

   **Scenario:** Untrusted page text persuades Claude to read another tab and supply a plausible `request`.

   **Harm:** An unrelated page’s text can reach Claude. The badge and log provide accountability after the read, not prevention.

   **Why acceptable at the normal-MCP boundary:** Semantic task interpretation ultimately belongs to the agent; demanding a perfect intent verifier would exceed the stated bar. The site-based selection instructions, ambiguity question and adversarial tool-user round are appropriate. However, present this honestly as an agent limitation, never as protection supplied by the required string. Deterministic target changes, exclusions and credential handling remain enforceable FIX items.

   Folded, found and `until` content belongs under the same untrusted envelope. The proposed normal result shape does this correctly; expansion must never promote page text into instructions.

10. **KNOWN LIMIT — Reading a sleeping tab is a visit, not a passive observation.**  
    **Where:** [28b, sleeping tabs](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:102).

    **Scenario:** Reading wakes a discarded page, causing network requests and startup scripts.

    **Harm:** The site learns of a visit; ordinary page-side effects such as read receipts can occur.

    **Why acceptable:** Visiting the clearly relevant page fits the owner’s requested capability and decision 25’s ordinary navigation limit. But it must be disclosed before claiming that reading causes no reload or observable request. The “leaves no trace” test applies only to an already loaded page. Unknown form-restoration behaviour must not be silently treated as this harmless exception.

The three owner choices need these corrections:

- **Choice 1:** **(a) is the right recommendation**, consistent with his existing instruction. Its explanation must disclose that `request` is not verified and that sleeping tabs load. Do not imply the badge prevents a mistaken read.
- **Choice 2:** **(a) is the right recommendation after FIX 6.** “Built and tested” currently overstates the dirty-state guarantee. State that copying an address also does not copy an unsaved draft. Option (b)’s reduced submission protection is described reasonably.
- **Choice 3:** **(a) is reasonable after FIX 6**, with explicit instructions that owner tabs are closed only when he requests closing them. Remove any implication that “reopen closed tab” guarantees recovery of work.

The incognito prohibition and fixed/owner never-list checks are appropriate as specified. The passive reader adds no intended page-to-service command route; preserve that separation when removing its dependency on the guard.

This was a source/design review. No browser tests ran; an attempted browser-free probe could not run because Node was unavailable.

CHANGES-NEEDED