Reviewed `5bbc4a94` against `2d5802da` and PR 27’s local checkout at `8b7e799c`. No files changed; no browser tests ran. The asking-read tool is a future PR 27 dependency, absent from that checkout.

**The revision closes several concrete defects, but credential disclosure and possible loss of work remain. It also introduces a send-binding gap through unread fields.**

| First review FIX | Status | Concrete reason |
|---|---|---|
| **1. Password provenance** | **Partly** | Existing password, autocomplete and masking protections are retained; credential names apply everywhere; late shadow roots receive protection. However, the narrowed history rule permits automatic disclosure described in decision (a) below. |
| **2. Public URLs** | **Partly** | One projection now covers results, questions, status and logs, while complete destinations remain privately bound. The new projection nevertheless deliberately exposes some authentication capabilities; decision (b). |
| **3. Reference identities** | **Partly** | A process-wide counter fixes cross-tab collisions; connection, document and reader-instance checks fix the ordinary restart/reinstallation cases. Three-letter prefixes remembered for only 100 runs do not establish permanent uniqueness. See the qualified KNOWN LIMIT below. |
| **4. Batch overwrites and barriers** | **Closed** | [Brief 28](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:606) requires fresh, complete fingerprints immediately before each step, updates only the acted-on element from its result, and checks queued submissions, dialogs and document changes between steps and after waits. |
| **5. Owner-tab selection and profile** | **Closed** | [Brief 28b](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:95) pins the profile and invalidates observations on reconnection. Its document/address checks precede reading or changing an owner tab, and page messages address the selected document. |
| **6. Unknown cleanliness** | **Partly** | Changed defaults, editors, canvases, files, frames, loading and owner-origin tabs now receive explicit checks. But work held only in application memory is expressly accepted as disposable, contradicting “unknown is not clean.” |
| **7. Outline injection through roles** | **Closed** | [Brief 28](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:310) specifies validated roles, common quoting across output surfaces, fixed refusal messages and untrusted stale-reference diagnostics. |

**The three subsequent decisions**

**(a) `be90f031`: FIX — the narrow history rule still automatically discloses credentials.**

Where: [history exceptions](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:154), [accepted long-secret disclosure](/var/home/ares/AresOS-28-chrome-capability/docs/design/CONTROL.md:1267).

A settings page has a CSS-masked textarea containing a private key, labelled only “Value.” The owner reveals it before the reader arrives. A routine read now returns the key without asking. The harm is credential disclosure, potentially granting account or signing authority.

“A password field is always a single-line input” describes HTML’s native password input, **not PR 27’s password-kind policy**. Its [reader](/var/home/ares/AresOS-20-chrome-read/control/chrome/extension/reader.js:52) explicitly protects masked textareas and editable areas too. Losing that provenance does not turn the disclosed credential into low-harm page deception.

There is also a narrower error: `email`, `url` and `search` inputs are declared incapable of having been password fields. Their present type proves no such history. For example, a field can have its password type changed to `search`, or lose masking/autocomplete before inspection, while retaining text and an innocuous label. That bypasses both omission and the new asking read.

**Fix:** Do not infer safe history from those current input types. Apply the history restriction to text-bearing inputs, including `search`, `email` and `url`. For multiline/editable fields with unknown provenance, provide a bounded approved-read route or reliable evidence that the field is safe to read automatically. Preserve the unconditional exclusion of recognised credentials. Reading drafts remains a valid capability; automatically exposing previously masked credentials is not a low-harm limit.

**(b) `78003f94`: FIX — the short-token exception retains the harm from FIX 2.**

Where: [public-address rules](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:237), [short-token limit](/var/home/ares/AresOS-28-chrome-capability/docs/design/CONTROL.md:1275).

A bearer sign-in link uses `/r?c=8f3k2j`. Neither its route nor parameter name matches the lists, and the value misses the length threshold. Reading that page or link exposes the capability to Claude and the log. Hiding it in the initial tab list does not prevent the subsequent disclosure.

This is authentication data, not merely a hostile page making an ordinary click look reasonable. The capability request does not require publishing arbitrary URL values: full destinations already remain available internally for navigation.

**Fix:** Keep opaque, unclassified URL values private, while permitting public values where their meaning is established—for example through a site-specific rule. Retain ordinary navigation by reference. Extending the credential-word list or length heuristic alone cannot establish that an otherwise ordinary parameter is safe.

**(c) `5bbc4a94`: KNOWN LIMIT for the owner’s disclosure choice; FIX for the underspecified approval binding.**

The owner expressly chose an asking read. An unrecognisable, previously revealed secret in an **actually listed and approved field** is therefore an informed-disclosure residual under that choice. I would not reject the choice merely because labels cannot identify every secret. Recognised credential fields must remain excluded.

However, [the proposed contract](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:732) does not yet specify enough to establish send-strength binding. “The list of fields differs” must mean the identities and descriptions of the fields—not equality of their displayed labels.

Concrete scenario: the question lists one field labelled “Value.” Before approval completes, that node is replaced by another identically labelled field, or its iframe navigates while the top page remains unchanged. Comparing labels and the top-level `seen` token would pass, disclosing a field the owner did not approve.

**Fix:** Specify a service-issued, immutable read preparation binding the connection, tab, frame documents, reader instances, exact element identities and displayed labels/descriptions. Verify the service-generated question and manifest as strictly as the send input; consume approval once; reject replacement, relabelling, frame navigation and changed credential eligibility before extracting values. Values themselves need not be read to prepare this manifest.

Add tests for same-label replacement, duplicate/unlabelled fields, iframe navigation, altered question/manifest and replay—not only adding a field. The declared managed ask rule, allow-rule resistance and skip-permissions tests are appropriate, but do not substitute for this binding. Deferring the implementation to PR 27 is reasonable; claiming it is already verified is not.

**Remaining FIX 6: memory-only work is still work.**

Where: [cleanliness criteria](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:224), [accepted memory-only loss](/var/home/ares/AresOS-28-chrome-capability/docs/design/CONTROL.md:1293).

The owner completes the first step of a wizard. Its draft remains in JavaScript memory; the next step displays empty fields, with no canvas, editor, media or unload handler. The specified detector calls this used page clean and permits automatic reload or close, destroying the earlier draft.

“Pages that care ask ‘Leave site?’” is not evidence that work is saved. The owner’s permission to close tabs expressly retains the no-lost-work condition.

**Fix:** Treat a used page with unaccounted-for application state as unknown unless an adapter or other reliable evidence establishes cleanliness. Keep it open on close; use the existing explicit destructive choice for taking. Add a wizard fixture whose prior-step draft exists only in memory.

**The four asking-path touchpoints**

| Touchpoint | Effect on PR 27’s question or binding |
|---|---|
| **Public addresses in the question** | **No comparison weakening as specified.** Only the public description changes; the payload and final comparison retain complete destinations. Reduced owner visibility is an explicit **KNOWN LIMIT**: a hidden destination component cannot be inspected in the prompt, but cannot change after approval. The disclosure defect in decision (b) remains separate. |
| **Scroll into view inside `input`** | **No weakening found in the specified placement.** It runs after arming and before the final facts/binding comparison and hit test. PR 27’s [final comparison](/var/home/ares/AresOS-20-chrome-read/control/chrome/extension/background.js:937) therefore remains decisive. Its [submission allowance](/var/home/ares/AresOS-20-chrome-read/control/chrome/extension/guard.js:198) requires the approved input, so merely scrolling does not consume that allowance. |
| **Password additions** | **Yes: a new FIX is required for ordinary unread fields**, detailed below. Stricter secrecy can remove content from the existing send question and comparison. |
| **Keeping the asking read in the new catalogue** | Preserving its separate managed ask rule introduces no send bypass. Its own approval strength remains subject to the manifest-binding FIX above and the future PR 27 implementation. |

**New FIX — ordinary unread fields can be submitted without their content being shown or bound.**

Where: [history protection and its reach into bindings](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:136), [late shadow-root fields](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:176).

A component attaches a shadow root containing a form. Before discovery, an ordinary single-line message field acquires a draft. The new rule permanently marks it unread. Typing into that field is refused, but clicking the form’s Send button is not.

PR 27’s [form facts](/var/home/ares/AresOS-20-chrome-read/control/chrome/extension/reader.js:201) feed `safeValue` into the form and its [approval binding](/var/home/ares/AresOS-20-chrome-read/control/aresos_control/chrome/adapter.py:30). With the new rule, the ordinary draft’s value disappears from both. The form can consequently submit content absent from the question; changing one nonempty draft to another can also escape comparison.

**Harm:** A recognised send has a question, but that question no longer describes and binds its actual ordinary content.

**Fix:** Distinguish known password fields from ordinary fields withheld for unknown history. Refuse a recognised submission when relevant ordinary content cannot be shown and bound; hand it to the owner unless a specifically designed approved-read-and-bind flow can cover it. Do not silently extend the password-presence exception to every unread field. Test the late-shadow form and a value change while approval waits.

**Reference residual: KNOWN LIMIT, with a documentation correction.**

At [brief 28’s reference allocator](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-capability.md:440), an old prefix can recur after lost history **or after more than 100 runs even with an intact store**. A retained reference could then resolve to another ordinary control. Recognised sends still receive fresh approval binding.

I accept this as a rare stale-reference limit under the practical MCP bar, rather than making it another blocking round. But the current claim that recurrence requires a lost store is inaccurate, and “no string is ever issued for two things” overstates the guarantee. A substantially larger run identifier would remove the practical concern cheaply.

The first review’s three existing KNOWN LIMITs—changed surrounding meaning, agent interpretation of `request`, and waking a sleeping tab—remain acceptable. I found no reason in this revision to reopen untouched areas.

CHANGES-NEEDED