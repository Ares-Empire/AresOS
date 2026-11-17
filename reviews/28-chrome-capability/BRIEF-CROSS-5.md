The briefs are **not ready for the 28a/28b builds as written**. I found one definite cross-package build conflict, two approval-policy gaps, and two contracts that need tightening.

I reviewed `e98c92b9`, recorded my findings before reading the three specified Claude reviews, and changed no files. This is a design review; I did not run browser tests.

1. **Blocking · fix — Profile pinning breaks across image updates.**

   **Where:** [28b, item 1](/briefs/28b-chrome-his-tabs.md#L143), against [18c-b, installation design and storage pin](/briefs/18c-b-chrome-image.md#L118).

   28b requires a random profile ID stored in the extension’s IndexedDB, permanently pinned by the service. But 18c-b generates a new extension identity for every image, explicitly says extension storage is lost on replacement, and requires a test rejecting any IndexedDB use.

   Following both briefs therefore fails the storage test. Removing that test leaves a normal image update generating a different profile ID: the service rejects the owner’s unchanged Chrome profile as another profile. This contradicts the image’s update/rollback design.

   **Fix:** Amend the identity lifecycle before building 28b. Specify how the same profile proves continuity across extension replacement without allowing a different profile to claim the existing pin. Reconcile 18c-b’s storage prohibition explicitly; it requires an owner decision. Test image A → B → A with the same profile accepted and a different profile refused. Automatically accepting each replacement ID would defeat the protection.

2. **Blocking · fix — Resuming a held submission knowingly bypasses the check for lost work.**

   **Where:** [28b, item 4, script exception](/briefs/28b-chrome-his-tabs.md#L458), [CONTROL §6, accepted data-loss limit](/docs/design/CONTROL.md#L1442), and [ALIGNMENT, held-submission decision](/reviews/28-chrome-capability/ALIGNMENT.md#L265).

   Consider a taken tab containing an owner-written draft. Claude changes an ordinary list whose handler submits another form. The guard holds that submission and asks about its form. Resuming it can navigate away and destroy the unrelated draft; the question explicitly need not describe that loss.

   Before the handler runs, its effect may be unpredictable. **After the tool holds the submission, the pending navigation is known and execution is under the tool’s control.** Treating its resumption as an unknowable script effect is therefore too broad.

   This is an intentional, consistently documented exception—not a missed ALIGNMENT edit. However, [the review bar](/docs/REVIEW.md#L34) classifies data loss as **fix**, and reserves known limits for disguised ordinary steps with low harm. The supplied decision is the lead’s acceptance, not an explicit owner override of this finding.

   **Fix:** Check for owner work when preparing and resuming held submissions in taken tabs. If navigation would discard it, refuse or obtain approval that explicitly includes the loss. Preserve board #138’s delayed owner submission through an explicitly defined path; it does not justify exempting every held submission. Add a test with two unrelated forms and owner work outside the submitted form.

3. **Blocking · fix — Opening a link reference can bypass its recognized destructive meaning.**

   **Where:** [28a, item 4, `chrome_open(ref=…)`](/briefs/28a-chrome-act.md#L273), against [CONTROL §6, free navigation and recognized controls](/docs/design/CONTROL.md#L911).

   A reference can identify a link visibly labelled **Delete** or **Unsubscribe**, with an ordinary GET endpoint behind it. `chrome_do` activation must classify that control and ask. `chrome_open(ref=…)` instead resolves its full address and uses the existing free-open rules. Those rules do not require classification of the referenced control.

   The same recognized operation can thus reach the server without its question simply by opening the reference. No disguised label or page script is necessary. This is particularly consequential where the reference retains an actionable token hidden by the public address formatter.

   Free navigation to arbitrary supplied URLs is an explicit existing policy. The unresolved distinction here is that the new reference route already knows which labelled control Claude selected, then discards that information.

   **Fix:** Specify that link-reference opening preserves the recognized-action check. The smallest implementation can refuse references whose activation requires approval and direct Claude to the asking action path. Test that clicking and opening the same Delete/Unsubscribe reference cannot produce a request before approval. Clarify the boundary with the separately accepted arbitrary-URL policy.

4. **Should-fix · fix — Reload approval freshness lacks a defined edit generation.**

   **Where:** [28b, item 4, reload binding and sticky used mark](/briefs/28b-chrome-his-tabs.md#L302).

   The approval binds the document and “what the check found.” The specified findings contain field labels, typing ownership, media state and a sticky used flag. The extension receives the first owner-use notification once.

   Those facts can remain identical while the owner continues typing into an already-dirty field, makes another canvas stroke, or replaces work in a same-labelled field. A check comparing only the specified findings can therefore accept an earlier approval despite intervening work. The broad instruction to reject a changed page does not define how these changes are detected.

   **Fix:** Define the private freshness binding: affected field/frame identities and an owner-edit generation that advances after subsequent edits, not merely the first use. Keep unread values unread. Specify the fail-closed behavior where an unwatched document cannot supply that evidence. Test continued typing in the same field and additional canvas work while the approval waits.

5. **Should-fix · fix — Inherited reload errors can put page text outside the untrusted envelope.**

   **Where:** [28a, item 5, step messages](/briefs/28a-chrome-act.md#L375) and [inherited reload refusal](/briefs/28a-chrome-act.md#L440); 28b’s corresponding loss reports.

   Step `message` must contain “the tool’s own words, never page text,” but reload refusals must retain main’s behavior. Main’s [`requireDiscard`](/control/chrome/extension/background.js#L671) interpolates page-controlled field labels directly into the exception message.

   A builder preserving that refusal can put hostile label text in an ordinary error or step message. Quoting or shortening a label does not identify it as untrusted content. The briefs need to resolve this inheritance conflict explicitly.

   **Fix:** Give reload refusals a fixed service-written code/message and put page-derived loss details under `untrusted_content`; use the corresponding untrusted description field in approvals. Define this for bare errors as well as batched steps. Test labels containing instructions and serialization delimiters.

6. **Nit · documentation — Section 6 has not absorbed all of brief 28’s final rules.**

   **Where:** [CONTROL §6, “one test everywhere”](/docs/design/CONTROL.md#L809), against [28, item 7](/briefs/28-chrome-read.md#L650).

   CONTROL’s random-token definition omits brief 28’s additional mixed-case/digit rule permitting `_` and `-`. Brief 28 also explicitly identifies the 5,000-reference paging ceiling as a known limit “for section 6,” but that limit is not incorporated there.

   **Fix:** Synchronize section 6 or make it explicitly defer to the complete normative rules. Otherwise builders and reviewers have different definitions of address redaction and complete paged reading.

The other requested checks are substantially settled in the final text:

- **List approvals:** `chosen` retains every selected option; `choosing` describes the entire resulting selection, including replacement on a multiple-choice list. Every option remains in the private binding and both comparisons. I found no remaining projection mismatch in that specified behavior.
- **Approval sizes:** 9,000 bytes is F4’s fixture ceiling; 16,384 bytes is the hard canonical-JSON approval limit. They do not conflict. Oversized hidden values remain refused, consistent with `434bb567`; exception 4 does not authorize cutting them.
- **Placeholder gate:** The final sweep requirements expressly cover the renamed/test-only tools and 28b’s individual own-tab branches, including stored reload execution. I found no missing branch in that specified coverage.
- **Late shadow roots:** A field already filled when first encountered remains unread for the document’s life. The optional empty-root attachment hook supplies earlier observation; it does not authorize retrospectively trusting a filled field. A one-off approved read does not make that field normally readable or sendable.
- **Popups and dialogs:** The final text addresses admission uncertainty and leaves before-unload decisions to the owner. I found no additional specification-level bypass there. Browser behavior and the required tests remain implementation evidence to obtain.

### Where I differ from Claude’s reviews

I agree that review 5’s list-choice and placeholder-gate findings are addressed, and that security review 4’s drop/paste requirement must remain fail-closed.

My substantive disagreement is with review 6’s acceptance of the expanded script-loss exception: **a held submission’s resumption is a controllable navigation, and loss of unrelated owner work is a fix under the stated bar**.

The profile-storage conflict, link-reference classification gap, reload freshness contract and inherited untrusted error text are additional findings absent from the three specified reviews. Consequently, I do not share review 6’s final readiness verdict.

NOT READY