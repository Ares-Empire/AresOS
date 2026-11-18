# Revision after BRIEF-CROSS-5

Documentation revision for `linux-tools`, 2026-11-18. Branch `briefs/28ab-cross-5`, from `main` at `918fba67`.
No product code. All six findings are accepted; the two owner choices below remain open. This is a proposed
build contract, not browser-test evidence or permission to implement an unresolved owner choice.

## What changed per finding

1. **Profile pinning — 28b “1. What Claude sees”; 18c-b “CROSS-5 identity handoff”; CONTROL “How the tool reaches
   Chrome” / “Which tabs Claude works in”.** Separate a durable logical service pin from the disposable extension
   installation id. Recommend owner-confirmed relinking after replacement, with automatic reconnection only for
   the current exact pair. A → B → A keeps the logical pin, accepts each replacement after that confirmation,
   and refuses another profile or a retired pair. No automatic migration based on the image or extension id.
   The sole proposed IndexedDB exception stores that installation id; the storage test stays and forbids other
   data/APIs. Owner question 1 explicitly covers the interruption after updates. Tests/mutations cover both the
   persistent pin and the refusal before relinking; a stand-in hello is not the combined browser proof.

   **Code checked:** main `control/aresos_control/chrome/bridge.py:49` accepts only session/version and remembers
   no profile. `control/chrome/extension/background.js:1137` sends that hello. The original 18c-b “The design,
   as settled” and item 1 require a fresh key and ban storage. Its branch's actual
   `control/chrome_tests/test_extension_stores_nothing.py` confirms that conflict. The branch progress records
   steps 1a–2b as built, including A/B/A installation; that is not evidence of a future service pin.

2. **Held submission loss — 28b “4c. A held submission checks the work its resumption could discard”, item 4's
   exception, frozen-path list and build order; CONTROL “How an asking action runs”, owner-delayed input and
   “Known limits”; ALIGNMENT “After BRIEF-CROSS-5”.** The earlier held-resumption exception is withdrawn. Check
   all forms and frames before preparing and immediately before resuming. Recommend one managed send/loss
   question, with private freshness evidence; no discard flag, no trusted-send bypass and no preliminary reload.
   Changed work fails the old operation and requires a fresh combined question under the original expiry.
   Board #138 stays in taken-tab tests: the same held native submission resumes once after approval, without
   repeating the input that caused it. The two-form test names the unrelated draft's loss; mutations skip the
   preparation/recheck, narrow the check to the submitted form, exempt delayed owner input or reload first.

   **Code checked:** main `adapter.py:788` prepares queued submissions through `payload(hold=…)` and reserves
   them; `adapter.py:659` builds the form payload. `background.js:1039` shares input/resume setup and compares
   bindings at `1043` and `1076`, but has no unrelated-work check on resumption. `adapter.py:833` also needs the
   explicit exclusion of possible-loss operations from trusted sends. `docs/REVIEW.md:40` treats data loss as a
   fix; the prior ALIGNMENT exception was a lead decision, not an owner override of this finding.

3. **Recognised link actions — 28a “4. chrome_open and chrome_go”; 28b “2. Looking in place”; CONTROL “Going to
   pages and acting” / “What is free and what asks”.** A link reference is checked and classified as a click
   before opening anything. If it would ask, opening refuses and names the asking action path. Arbitrary supplied
   URLs, tab-address copies and library entries keep their accepted policy; a refused reference can't fall back
   to it. Delete/Unsubscribe GET fixtures assert zero requests from click and reference-open before approval.
   Removing classification must fail that receiver test.

   **Code checked:** main `adapter.py:659` already classifies a selected target through `recognize`/`classify`;
   `adapter.py:716` free-open creates a tab then navigates it. There is no new `chrome_open(ref=…)` on main yet:
   the gap is in 28a's contract connecting those paths, not an allegation that the unbuilt tool already exists.

4. **Reload freshness — 28b “4d. Private freshness for every loss approval”, item 4 and Paths; CONTROL “Which
   tabs Claude works in”.** Bind actual field/frame/document/reader identities and monotonic edit generations.
   Later typing, a further canvas stroke or continuation of one already in progress invalidates approval even
   if every displayed loss label stays identical. Frame removal retains evidence; final queries catch delayed
   reports. An unwatched document can ask only with observation proven from before preparation through dispatch;
   missing evidence refuses without approval. Tests record that unread values stay unread. Mutations retain only
   first-use state, compare labels, accept a missing watcher or trust delayed reports.

   **Code checked:** main `reader.js:525` reports labels, typing ownership and media, not an owner-edit
   generation. The old 28b item 4 only required first-use reporting and sticky use. Its general “page changed”
   wording did not define evidence for continued edits. The proposed watcher is additional allowed work, not a
   claim that main already supplies it.

5. **Untrusted loss text — 28a “5b. Loss refusals carry page text only as untrusted content”, inherited reload
   policy, frozen-path exceptions and Paths; 28b item 0 and loss questions; CONTROL loss-report contract.** Keep
   a fixed service-written `reload_required` code/message and carry labels in `untrusted_content.loss`; approvals
   use `description.untrusted_content.loss`. Apply this to bare errors, batched steps, kept tabs, operation status,
   stages and notices. Schemas and transport must preserve the envelope. Hostile labels with instructions and
   serialization delimiters test each surface; interpolation/flattening mutations must fail.

   **Code checked:** main `background.js:671` (`requireDiscard`) interpolates labels into the exception at
   `685`; `reader.js:527` creates those strings. `bridge.py:106` turns the extension error into `Refused` text;
   escaping there supplies no untrusted envelope. The revision explicitly permits the necessary narrow shared
   error-serialization support instead of leaving a frozen-path contradiction.

6. **Section 6 parity — CONTROL “Reading a page” and “Known limits”; 28a item 0 / “CROSS-5 regression
   contracts”.** Copy the mixed-case/digit random-token rule allowing `_` and `-`, and defer to brief 28's full
   address algorithm. State the 5,000-reference cursor ceiling and usable alternatives, including the small
   fold-count effect. Retain separator-token and >5,000-reference tests; removing that token branch or cursor
   reference-text binding must fail them.

   **Checked against the normative brief:** `briefs/28-chrome-read.md:650` adds the separator rule and `:662`
   names the ceiling for section 6. Main still has the old reader; this is synchronization with package 28's
   specified/implemented successor, not a new main-code fix.

## Package 28 changes carried forward

28a item 0, 28b item 0 and CONTROL's “Unicode at the native boundary” require every fresh-side comparison with
service-held page facts to use `wellFormed()` repair. This includes fingerprints, fields/descriptions, both
approved-input comparisons, dialogs and loss bindings. Full private facts still bind. Selecting by a repaired
option value resolves to exactly one native option; collisions refuse. End of control drops tab references,
keeps the counter increasing and ignores old-session cleanup events.

Read `git show origin/pkg/28-chrome:reviews/28-chrome-read/PROGRESS.md` after fetching. At fetched head
`e07a88eb`, that file has steps 13b and 13c, but **no separately headed 13d yet**. The follow-up is already in
code: `42163e2c` repairs fresh comparison facts; `978536d7` resolves repaired select values to native values.
The inspected `background.js` lines are `340` (helper), `1050` (dialog), `1080` (typed read), `1157`/`1190`
(two binding comparisons), `1162` (expected target), `1231` (option resolution), and `1422` (confirmation).
These are branch-specific line numbers. No claim is made that its pending browser runs are green.

**Distinct fields:** 28a “3b. Every field in an asking question is distinguishable” owns the frozen-path change
for step 13b's PLAN-GAP; 28b inherits it. Label plus ordinal and frame context must distinguish every field after
repair/shortening. Identity/order remains bound and values remain unread. Main `adapter.py:381` joins the labels
alone, although `reader.js:266` supplies distinct element ids. The new test asserts the **question sentence**, not
just the ids: two same-labelled fields are distinguishable, and swapping/replacing/reordering refuses. Rendering
labels alone must fail it. F4/approval ceilings are not increased to pay for the descriptions.

**Instructions:** measured on this main: 30 tools, instructions **4,093**, descriptions **5,085**, combined
**9,178** characters. 28a item 7/step 0 moves single-tool rules into descriptions and compacts shared Chrome text
before adding anything, pinning 2,800; 28b item 8 verifies that headroom, then pins 3,800. Existing total budgets
and common instructions remain. No server instruction text was added here.

## Questions for the owner

1. **After an update or rollback replaces Chrome's helper, should you confirm once which Chrome profile Claude
   reconnects to?**
   **Why it matters:** the tools wait for you, but another profile cannot silently become the one Claude reads.
   **Options:** confirm the chosen profile after each replacement; or make reconnection automatic, which needs
   a separate reviewed design and delays this part of the build.
   **Recommendation:** confirm after replacement. It keeps the tested image rollback behavior and needs no
   permanent signing secret. Normal Chrome/service restarts need no confirmation. The same logical profile pin
   survives; you authorize its new helper identity. This is a real change from 18c-b's “without another step”.

2. **If a delayed form send could discard another draft or drawing on the page, should one question let you
   approve both the send and that loss?**
   **Why it matters:** approving a form send alone doesn't tell you that another draft will disappear.
   **Options:** one question naming the send and possible loss; or always stop when other work may be lost,
   leaving you to save the work or send the form yourself.
   **Recommendation:** one combined question. It preserves your delayed submissions (board #138). No reload
   happens first. Refusal sends nothing, and further work while the question waits requires a fresh question.

Neither answer is inferred from this revision or from the earlier READY. `linux-tools` records the choices
before their dependent implementation steps; unrelated image/read work can continue.

## What 18c-b must now do differently

The new handoff names every remaining step; completed steps 1a–2b are not replayed. **3a** installs as planned
but records the pending identity dependency and keeps the storage ban until the approved narrow exception lands.
**3b** is unchanged. **4/4b** uses a synthetic real pin when 28b is available, without bypassing first-use gates.
**5** extends case 3/C4 to pin continuity, refusal before relink, owner-confirmed acceptance, retired pairs and
another profile; if 28b merges later, its PR owns the combined container proof and `linux-tools` assigns the
VM/release confirmation to the image builder before shipping. **6** separates installation evidence
from pin evidence and adds the chosen owner step to the guide/release handoff. No permanent signing key,
profile-file installation or automatic enrollment is added to the image.

## Disagreements and limits of this revision

No disagreement with any CROSS-5 finding. The earlier review 6 acceptance of held-resumption loss is superseded
because that operation is now controlled. The remaining unheld script-effect policy is not widened or reopened.

The identity recommendation deliberately requires human authorization of continuity; it does **not** claim an
automatic technical proof across a destroyed extension store. If the owner chooses automatic continuity, that
option needs a new concrete design and tests before implementation; simply accepting replacement ids or keeping
a signing key without proving rollback is not an alternative implementation of this brief.

## Verified / not verified

- **Run:** `git fetch origin` first, exit 0 with no output; starting branch `briefs/28ab-cross-5`, clean, main
  `918fba67`. Read the requested briefs, cross-review, alignment (including review 6's recheck), design and review
  bar; compared their claims with main code and the two in-flight branch records above.
- **Run:** `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control python3` importing `instructions_for` and `tools_for`:
  printed `Chrome instructions: 4093`, `Descriptions: 5085`, `Descriptions plus instructions: 9178`, `Tools: 30`.
- **Run:** `git diff --check`: exit 0, no output.
- **Run:** `PYTHONDONTWRITEBYTECODE=1 python3 .work/cross5/check_docs.py`: exit 0, printed:

  ```text
  PASS: exactly six requested Markdown files; no product changes
  PASS: CONTROL changes confined to section 6
  PASS: existing server instruction block unchanged
  PASS: ALIGNMENT adds one section; prior decision history retained
  PASS: no accidental replacement characters or personal home paths
  PASS: .work files over 500 MB: none
  ```

  The scratch check compares the diff's paths with the six requested files, CONTROL outside section 6 and the
  existing instruction quote with `918fba67`, verifies the append-only alignment and scans the worktree's `.work/`.
- **Large artifacts left:** none over 500 MB in `.work/`; no downloads or extracted images made.
- **Not run:** product unit suites, reviewer mutations, browser/VM tests, mod builds or workflows. These edits
  specify future tests; they cannot establish implementation correctness. No product source or generated file
  changes. No owner browser/profile, desktop input, system installation, mount or boot command used.
- **Open questions:** the two owner choices above; final implementation proofs belong to the package builders.
