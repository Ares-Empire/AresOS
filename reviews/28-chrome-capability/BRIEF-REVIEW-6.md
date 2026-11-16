Fresh design and security reviewer (Claude agent, Opus 5.5), 2026-11-16, on `briefs/28-chrome-capability` at
`41df1378`; range `2dc9977b..41df1378` (the five commits after the merge of main; `0cb51ac6..2dc9977b` changes none
of the briefs, section 6 or this folder). Claims checked against `control/chrome/` and `control/aresos_control/` on
this branch and `origin/pkg/28-chrome` at `5a9e367c`; the sweep against `origin/pkg/18c-b-chrome`.

# Brief review 6: the Chrome capability briefs

Nothing was run in CI. Local checks: main's helpers in plain Python (sizes below) and reading the code. Security
findings are sorted **fix** or **known limit** as `docs/REVIEW.md` defines them.

## Review 5's findings and the judgment calls

| Finding | State |
|---|---|
| B1 | Closed as the lead decided, with three gaps below (S1, S2, S3). |
| B2 | Closed. `choosing` is taken from the binding, the extension refuses unless exactly one enabled option has the value (`reader.js` `select`), and the whole binding is compared before the input, so the option shown is the one selected. One nit on multiple lists (N6). |
| S1, S2, S4, S6, S7 | Closed as decided. |
| S3 | The rule is closed (fail closed, `late`). Its example check doesn't detect the stale pause (S5). |
| S5 | Closed. Every path that reaches the bridge goes through `mode()` or `pending_state` first; the `SWEPT` rule is workable for either merge order (N8). |
| N1 to N8 | Closed. N3's numbers recomputed: `request` 58, `seen` 54, `APPROVAL` 268; 731 − 28 = 703 of 750. Main: 30 tools, 11,080, 5,085 and 4,081, as written. |

- **JC1** (whose press): sound. `ownerInput` does return during a dispatch and keeps nothing (`guard.js` 207-222),
  and the new line can sit before `active()` (306-307). Wording nit N1.
- **JC2** (drop and paste listener): sound; `drop` and `paste` aren't in `watch`'s event list today.
- **JC3** (where the check runs): sound in principle. Its slot must be narrowed (S1), and its "before the question"
  part has no place yet (S4).
- **JC4** (what is checked): sound. The used mark includes his typing (`typed` marks the document), so dropping
  brief 20's field walk loses nothing of his; a frame inside a link is covered by "the whole tab".
- **JC5** (fallback): sound, and it can't loop. After the late document's guarded reload, the next install isn't the
  first one after the re-arm, so it is `document_start`. "Every document after a re-arm" would loop.
- **JC6 to JC9**: sound.

**The central question.** Apart from the named limit, I found one path where Claude can leave or reload over his
work in a taken tab with no question (S2, a frame he used that the page has removed), one wording that excludes
paths the brief means to accept (S3), and a placement that loses the refusal itself (S1). Each is a small change
within the design.

## Should fix

### S1. The check before a leaving step must sit before the tab selection and `reveal` (28b item 4)

*Where:* 28b item 4, "A step that leaves the page", "It sits before `input`'s last facts read"; 28a item 5, "On
screen first".

*Why:* in `input` (`background.js` 1052-1078), three things already sit between arming and the last facts read: the
tab selection (`chrome.tabs.update`, which sets `effectStarted`), 28a's `reveal` (an effectful scroll), and now this
check. If the check runs after either, a refusal in a taken tab that isn't in front comes back to the service as
`unknown: Input may have started; … never retry` (`connect`, the `effectStarted` wrapper), not as
`reload_required`. Claude then gets no approval, the step reads as possibly run, and his tab was brought to the
front. His tabs are often in the background, and 28b item 7 may keep the selection for some input kinds.

*Fix:* place the check right after the frames are armed, before the selection and `reveal`; a refusal there sets
no effect flag. Test: a leaving step in a used taken tab that is in the background ends `reload_required` with an
approval, and the tab he looks at stays in front.

### S2. A frame he used that the page removes takes the used mark with it (28b item 4) — **fix**

*Where:* 28b item 4, "the check also asks every frame's guard whether he has used that document"; "One frame that
says yes makes the tab used".

*Why:* the mark lives in each frame's guard and is read at check time. He types an address into an embedded
widget's frame and confirms; the widget hands it to the page and the page removes the frame (or the frame moves to
a new document). His keys never reached the top document, so its guard says no, and the frame is gone. `chrome_go`,
a link or a form step then runs with no question and his entry is lost. That is a path the tool can see
beforehand, and it isn't the named limit. Security confirmation 4 already required the drop record to be "sticky in
the extension and [not to] go away when a child frame is removed or replaced"; the new mark doesn't follow it.

*Fix:* the guard reports the first mark of his in a document to the extension once (through the reader, as
`reader.report` does), and the extension keeps a per-tab "used" flag until an approved `chrome_take_reload` or a new
top document. The check reads that flag as well as asking the frames. That is one more call in `guard.js`'s
isolated part; widen 28b's paths by it. Test: he types and confirms in a child frame that the page then removes;
`chrome_go` and a link step are refused with an approval.

### S3. The limit is worded more narrowly than what item 4 leaves unchecked (28b header, Known limits; section 6) — **known limit**, plus one **fix**

*Where:* 28b header ("an element that is neither a link nor a form's control") and "Known limits" ("One loss is a
limit, and only this one … neither a link nor a form's control"); section 6, known limit "In a taken tab, a
navigation that the page's own script starts".

*Why:*
- Item 4 checks only a link to another document and a form submission. A `javascript:` or `#` link whose handler
  sets the address (common), a link that opens a new tab, and a form's other controls (a list whose `change`
  submits, a field whose input navigates) are unchecked, yet the wording says they are not the limit. Under "only
  this one" a builder who meets them must "fix it or stop", and can't fix them.
- Losses inside the page aren't named at all: a page script that clears his work after a step without
  navigating, and a reset control. A reset control is visible beforehand (`type=reset`) and empties every field
  he typed in its form.
- Section 6 says a submission such a script starts "is held and asked as a send". Only while the hold runs after
  Claude's step, and never for a GET search form (`search()` lets it through in `submit`). Later or search-form
  submissions navigate unasked.

*Fix:* word the limit as "what the page's own script does after a step the tool doesn't check (anything but
following a link to another document or submitting a form)", navigation or not, in the header, "Already decided
by the lead", "Known limits" and section 6. Say that a step's own visible effect in the page, such as Claude's fill
over a field, follows the asking rules as in Claude's tabs. Add a reset control to the checked kinds. In section 6,
qualify "held and asked" as above.

### S4. The check before an asking step's question, and `chrome_submit`'s refusal, have no place (28b item 4)

*Where:* 28b item 4, "A step of Claude's that asks is checked before its question is prepared as well"; tests, "A
send that was prepared before he used the page is refused the same way when `chrome_submit` runs"; "What must not
change", "The asking path … exactly as briefs 28 and 28a list them".

*Why:*
- An asking step is prepared by the service (`payload` → `classify` → `engine.reserve`) from a `facts` reply. No
  `input` command runs, so "in the same `input` command" can't cover it. The brief doesn't say which reply carries
  the used result or where the service refuses, and "What must not change" freezes the asking path.
- 28a keeps `chrome_submit`'s result unchanged, and `Refused` carries only a code and a message, so "refused the
  same way" (with an approval) has no field to go in.

*Fix:*
- For a taken tab, the `facts` reply carries the tab's used result, and `payload` refuses a leaving step that
  would ask, before `reserve`, with the approval. List both among the permitted changes.
- Say what `chrome_submit` returns here: the operation failed with `reload_required`, and either the approval in
  its result (a named field) or advice to call `chrome_go` (`to: reload`), which prepares one.

Neither changes safety: the check at dispatch holds either way.

### S5. Item 5a's example check passes the stale pause it is meant to catch (28a item 5a) — **fix**

*Where:* 28a item 5a, "for example the paused frame's loader or execution context against the target's current one".

*Why:* the stale pause is from the document that is still current. `Debugger.disable` in the re-arm
(`background.js` 104-113) resumed it, it ran, and its delayed `Debugger.paused` carries the same breakpoint id
(the re-armed one keeps it). Its context and loader are the current ones, so that comparison says "current" and the
install marks a document that already ran as `document_start`. A builder who builds the example and calls it
reliable skips the fallback.

*Fix:* drop the example. A check qualifies only if it proves that the pause itself still holds, not that the
document is current. With the allowed methods, one candidate is a `Debugger.resume` at the end of the install that
fails when nothing is paused, with the document downgraded to `late` before it counts as ready. Otherwise the
fallback is the rule: the first document a session installs from a pause after a re-arm counts as `late`. The tests
gain "a stale pause from the current document after a re-arm installs as `late`".

## Nits

- **N1** (28b item 4, "his clicks and keys"; JC1). "Follows `typed`'s rule … the element that dispatch aimed at,
  or inside it" contradicts itself: `typed` uses `field.contains(typingTarget)`, which would make his press on any
  ancestor, even `body`, Claude's. Write it as "the pressed element is the target or inside it, and for a key the
  editing host around it". Also keep "used" as a record of his own beside the typing marks. `reloadState` reads
  any mark on the document as design-mode input (`reader.js` 534-536), so Claude's clicks in a design-mode frame
  would start being reported as typing.
- **N2** (28b item 4, the two kinds). Resolve a `<label>` to its `control`: a label for a submit button or a link
  activates it natively, and the guard's `control()` doesn't resolve labels. Name `area` and SVG `a` as links.
  Enter in a `textarea` doesn't submit; checking it only asks too often.
- **N3** (28b item 4 and its charge). Main's `keyboard()` passes F1-F24 and Ctrl or Alt with letters and arrows. The
  charge assumes keys sent through DevTools never trigger Chrome's own reload, back or close (F5, Ctrl+R,
  Alt+ArrowLeft, Ctrl+W). Measure that once in CI in a taken tab, and refuse such keys there if any of them acts.
  This exists on `main` already.
- **N4** (28b tests). Add: a paste in a taken tab (only a drop is tested); a frame not watched from its start making
  a taken tab used; an asking send after he used the page, refused before any operation is reserved (S4); and S2's
  removed frame. To 28a's 5a tests add the late install followed by a `document_start` one after its guarded
  reload, which pins JC5's no-loop.
- **N5** (28b item 4a, "Frames that take no reader"; section 6's matching limit). With the new check, such a frame
  also stops every link and form step in a taken tab he hasn't used ("A frame that doesn't answer refuses the step
  with no approval"). Section 6 says only "taken or navigated". Say so, and measure an extension's frame that
  appears when a field is focused.
- **N6** (28a item 3a, B2). On a multiple list, `element.value = v` leaves only that option chosen, but `chosen`
  (several) beside `choosing` (one) reads like an addition. Say in the target that the step leaves only `choosing`
  chosen, or refuse `select` on a multiple list. Optional, and on `main` already: the question line for a select
  reads "activate 'Country' to <form action>", which sounds like a send.
- **N7** (28b item 4, "Which `chrome_do` steps that covers"). In the PLAN-GAP fallback, where the reload stays at the
  first input, the pre-take document isn't watched from its start. B1's rule then makes every such tab used, and
  the first input always asks. Say that the first input's reload in that fallback runs item 4a's check.
- **N8** (28a item 7, 28b item 9, the sweep). `SWEPT` is keyed by tool name and `call` uses `name.split()[0]`, so
  his-tab entries need keys like `'chrome_read his tab'`. Because the gate runs before any bridge call, they differ
  from the existing entries only by their arguments (`request`, `seen`), which is what they test. A copy of the
  sweep kept in 28a's own tests goes once PR #76's test is on `main`.

## Budgets, lists and tests

- Schema: no input is added by this round; 703 of 750 stands (720 with `seen` and `request` required on
  `chrome_take`). Instructions: unchanged; the `chrome_take_reload` description grew by about 20 characters, inside
  the 1,550.
- 28b's paths and "What must not change" allow the `guard.js` lines B1 needs. S2 adds one call and S4 one service
  change; both lists need them.
- Briefs, section 6 and ALIGNMENT agree on B1, B2, S1-S7 and N1-N8, apart from S3's wording. The test lists match
  the items, apart from N4.

The should-fix items are text changes without new design. S5 belongs in 28a before it starts; S1 to S4 belong in 28b
before it starts. A check of those edits suffices; no further full round is needed.

READY
