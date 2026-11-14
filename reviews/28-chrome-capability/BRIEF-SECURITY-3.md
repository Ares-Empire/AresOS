**Two FIXes remain.** Reviewed `8a1112d9..61bedd09`, the earlier security re-check, and PR 27’s checkout at `8b7e799c`. No files changed; no browser tests ran. The forthcoming asking read is a dependency, not verified implementation.

| Re-check point | Status | Concrete reason |
|---|---|---|
| **(a) Unknown field history** | **Partly closed — FIX** | All text-bearing inputs and textareas now withhold values, including late shadow-root fields. The editable-area exception retains the credential-disclosure case below. |
| **(b) Addresses** | **Closed by informed owner choice — KNOWN LIMIT** | Board 213 explicitly accepts an unrecognised short sign-in code reaching Claude. Recognisable sign-in values remain hidden; lists, logs, stages and notices use the short form. I found no widening of that choice. |
| **(c) Asking-read binding** | **Closed in design** | The preparation binds connection, tab, frame documents, reader instances, exact elements and displayed descriptions. Alteration, replacement, relabelling, changed credential eligibility and replay refuse the read. This now covers the same-label replacement scenario. |
| **Remaining fix 6: unknown cleanliness** | **Partly closed — FIX** | Treating every used tab as unknown closes the clicked/typed wizard scenario. The proposed fallback for work arriving without activation still permits data loss. |
| **Unread content in a send** | **Closed in design** | A distinct unknown-history mark causes refusal before preparation, including held submissions and bound drafts outside forms. An approved read does not lift the refusal. Tests cover a field entering the form while approval waits. |
| **Reference run identifier** | **Closed, with KNOWN LIMIT** | Five random consonants replace the three-letter/100-run scheme; the process-wide counter remains. Cross-run uniqueness is now honestly probabilistic. |
| **Earlier fixes 4, 5 and 7** | **Remain closed** | Fresh per-step fingerprints and barriers remain; profile and selected-document binding remain; fixed roles and escaped untrusted output remain. Opening a listed address uses the stored address without reading the subsequently navigated owner tab. |

**FIX 1 — the editable-area exception still automatically discloses credentials.**

[Brief 28:184](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-read.md:184) and [CONTROL:1311](/var/home/ares/AresOS-28-chrome-capability/docs/design/CONTROL.md:1311) expressly permit this sequence: an editable area labelled “Value” contains a masked private key; the owner reveals it before the reader arrives; an ordinary read returns it without asking. The brief even specifies a fixture demonstrating that disclosure.

This is the remaining editable-area portion of finding (a), not a fresh hunt. PR 27’s [password protection](/var/home/ares/AresOS-20-chrome-read/control/chrome/extension/reader.js:52) already includes masked editable areas. Narrowing the exception reduces its frequency, but does not reduce the harm from credential disclosure. The lead’s acceptance is not the owner’s informed exception for addresses.

**Required change:** provide an approved-read route for editable content with unknown provenance, or reliable evidence permitting automatic reading. Keep recognised credentials unconditionally excluded. Reading editors can remain supported through that route. The regression should show that this fixture discloses nothing before approval.

**FIX 2 — failed activation measurements cannot default to accepting lost work.**

[Brief 28b:324](/var/home/ares/AresOS-28-chrome-capability/briefs/28b-chrome-his-tabs.md:324) explicitly directs the builder to record script-only work as a known limit when drop/paste does not set activation. [CONTROL:1341](/var/home/ares/AresOS-28-chrome-capability/docs/design/CONTROL.md:1341) accepts losing that state.

Concrete case: an otherwise untouched page receives dropped text or a file into a custom drop zone, retains the working state only in JavaScript, and has no changed field, editable area or selected file input. If the drop leaves activation false, the proposed check calls it clean and permits automatic reload or close. This requires no hostile page. The standard’s activation-triggering event list does not establish that dropping or pasting necessarily sets the mark. [HTML activation processing](https://html.spec.whatwg.org/multipage/interaction.html#tracking-user-activation)

**Required change:** replace “record it as a known limit” with a fail-closed requirement. If the measurements expose this case, those pages must remain unknown unless additional reliable evidence establishes cleanliness: keep them open; require the existing explicit reload choice for taking them. Pin that behavior with a fixture. I am not claiming the Chrome measurements have already failed; the design’s authorised response to failure is the defect.

The three measurements themselves are **BUILDER-NOTEs**:

- Same-site navigation carrying activation forward is conservative: more tabs remain open.
- Drop/paste/file-drop results determine whether additional protection is required under FIX 2.
- Reads, checks and extension messages must not manufacture activation; the existing stop-and-report instruction is appropriate.

The newer changes do not introduce another design-level FIX:

- **Deadline propagation (`2537ee84`):** [28a:358](/var/home/ares/AresOS-28-chrome-capability/briefs/28a-chrome-act.md:358) preserves the final binding comparison and adds a refusal immediately before dispatch. Expiry releases an armed hold; after dispatch, collection and cleanup continue. Missing replies become `unknown`, never retryable success or “nothing happened.” These rules preserve the question and binding.
  
  **BUILDER-NOTE:** establish the deadline before queue waiting, never restart its budget at dequeue, and ensure timed-out setup cannot resume into dispatch. PR 27 has asynchronous pointer/focus setup and multi-event inputs: identify the actual dispatch boundary, finish an already-started input, and preserve cleanup. Dropping a late reply alone does not cancel its work. The specified delayed-setup and post-dispatch tests must prove these distinctions.

- **Projection before serialisation (`265e8192`) and short stages (`42d1d850`):** [28a:150](/var/home/ares/AresOS-28-chrome-capability/briefs/28a-chrome-act.md:150) now names PR 27’s actual output points. Questions use projected copies; `execute` projects the confirmation/page stage copies before serialisation; payloads and comparisons retain full destinations. This neither weakens destination binding nor changes approval consumption.

  **KNOWN LIMIT:** the owner sees less of a destination than the service binds. That remains acceptable because the hidden destination cannot change under the approval. Shorter stage records do not shorten the approval question itself.

- **Reference collision residual — KNOWN LIMIT:** two particular runs collide with probability about one in 4.08 million. A retained reference could then select another ordinary control if its number and tab also match. Recognised sends still ask. This remains acceptable under the earlier practical assessment. The new element’s fingerprint is not proof of the old reference’s identity.

**Package 28 alone introduces no specified regression below PR 27’s offered behavior.** [Its split contract](/var/home/ares/AresOS-28-chrome-capability/briefs/28-chrome-read.md:582) keeps the new outline behind a test-only switch, preserves the public catalogue and managed rules, retains `reference`/`expected` and whole-view checks, and leaves existing address output unchanged until 28a. Its public changes strengthen field withholding, overwrite protection and submission refusal. The asking-read eligibility adjustment retains its preparation binding.

**BUILDER-NOTE:** compare against merged PR 27, including its forthcoming asking read. Run the binding regressions and stop if they fail, as the brief requires. Existing take-cleanliness gaps persist until 28b; they are not newly introduced by the split, and the stated all-three-packages deployment gate remains necessary.

CHANGES-NEEDED