# Briefs 28, 28a, 28b and section 6 against merged PR #27

Checked on 2026-11-15 against `main` after PR #27 merged (`09cedc84`, final head `d25ccbd3`), with
`docs/control/TOOLS-HANDOFF.md`, "Chrome merged". The briefs were written against `8b7e799c`. Every backticked
name, path and function in the three briefs and section 6 was looked up in main's tree; the ones below changed or
were added. The design itself is unchanged; the open points are listed at the end for the lead.

## What changed on main since `8b7e799c`, and where it went

| Fact on main | Where |
|---|---|
| 30 Chrome tools, not 29: the asking read is two tools, `chrome_prepare_read_typed_fields` (change, input `tab`) and `chrome_read_typed_fields` (read, input: the approval) | 28 (counts, item 5, reading list), 28a (goal line), section 6 ("Actions", efficiency table) |
| The latency harness and gate exist: `control/chrome/ci/latency-*.{sh,mjs,py}`, `latency-targets.json` (ceilings in ms, median / p95: read 35/60, navigate 100/150, click and fill 650/750, asking click 60/100, approval to done 700/850; 60 samples, the old runtime 20) | 28 ("Latency": the "if they aren't" branch dropped), 28 and 28a acceptance rows, section 6 latency bullet |
| The hold: guard window 500 ms (`HOLD_MS`, `holdMs`), the wait after each input 525 ms (`holdMs+25` in `collectSteps`), unchanged | 28 and 28a "What must not change", 28a "Why 20 steps" |
| Claude Code 2.1.319 passes only 4,096 characters of a server's instructions; `test_questions.py` checks every app; Chrome's are 4,052 on main | 28 ("What must not change": 28 adds none), 28a item 7, 28b item 8, section 6 "What every server pays once" |
| `reload_taken_tab` is now `discard_unsaved`, and it also covers navigate (every direction and an address) and `close_tab` on any Claude tab; the report names fields by label, marks whose typing it is, and counts playing media and uninspected frames | 28a item 6 (`chrome_take`), section 6 ("Until brief 28b merges") |
| Brief 20's reload check (`requireDiscard`, `reloadState`, the guard's `typedBy`): in a document the reader didn't watch, every text field counts; in a watched one, a field that differs from its default or got typing since the load | 28a item 6, 28b item 4a and reading list, section 6 ("Which tabs Claude works in") |
| `chrome_tabs` rows carry `audible` and `muted` | 28a item 6 (`sound` is `audible`), section 6 ("His open tabs") |
| The details page asks his password in a polkit dialog for "Don't ask again" and read-only off | section 6 ("Don't ask again") |
| The KNOWN-LIMITS sentence on a tab taken from another window, word for word | 28 ("Report", "Known limits"), section 6 "Known limits"; 28b item 4b says its own group answers it |
| Follow-ups from #27's final reviews: Hardening (`embedderName`) | 28, new item 8 |
| Follow-ups: Retry advice (`requireTab`'s late-reader retry), `control_status`'s `installs` rows | 28b, new item 10 |
| A full `control-chrome.yml` run is about 40 to 60 minutes in 28 jobs (runs 43641834739, 43641839672), not three to four hours | 28 and 28a stop rules |

## Open points the alignment found (decided below)

1. **The asking read's prepare tool has no place in the new list.** 28a keeps `chrome_read_typed_fields` "with its
   name, input and behaviour unchanged" as the eighteenth tool, but its input on main is the approval that
   `chrome_prepare_read_typed_fields` returns. 28a's removal list (item 8, step 3) doesn't name the prepare tool,
   so as written it stays and the list has 19 tools; the 18-tool size budgets don't count it. 28b adds `seen` to
   `chrome_read_typed_fields`, which on main takes no `tab`.
2. **`discard_unsaved` has no home in 28a's tools.** On main, navigate (all directions and an address), `close_tab`
   and a taken tab's first input report unsaved work and need `discard_unsaved: true` to go on. 28a's `chrome_go`
   and `chrome_close` have no such input, and 28a item 7's list of instruction rules doesn't carry main's discard
   rule (ask him before discarding his typing, playing media or uninspected frames). 28b assumes the flag stays for
   Claude's tabs.
3. **4,096 characters.** Main's Chrome instructions use 4,052; 28a's rule list and 28b's 920-character block won't
   fit without taking text out of the instructions or out of them into descriptions.
4. **A `muted` mark.** The new `chrome_tabs` line shows `sound` (Chrome's `audible`, set also while muted) but not
   `muted`, which main's rows now carry.
5. **28b's "known clean" rule versus main's check.** Main counts every text field in a document the reader didn't
   watch from its start; 28b calls an unused tab with an untouched text field known clean. It rests on the "used"
   mark; worth a line in 28b's security review.
6. **Inside 28b, from the lead's 2026-11-14 change (not from #27):** item 8's instruction text still says "pass
   reload only when he agrees", and "the tool list stays at eighteen", while item 4 replaced `reload` by the asking
   tool `chrome_take_reload`.

## The lead's decisions after alignment (2026-11-15)

1. **The asking read stays two tools.** `chrome_prepare_read_typed_fields` returns the approval,
   `chrome_read_typed_fields` takes it, and the managed ask rule stays on `mcp__chrome__read_typed_fields`. 28a ends
   at 19 tools: its removal list keeps both, and its budgets become 10,900 (descriptions plus instructions) and 6,450
   (names plus input schemas), that is the 18-tool budgets plus the prepare tool as main has it (361 and 142
   characters). 28b's `seen` and `request` go on the prepare tool. Written into 28a items 6 to 8, its tests table and
   acceptance, 28b, and section 6.
2. **`discard_unsaved` keeps main's guard.** 28a's `chrome_go` (every direction and an address), `chrome_close` (any
   Claude tab) and `chrome_do` (a taken tab's first-input reload) take it with main's meaning and refusal, and 28a's
   instruction rules carry main's rule (ask him before discarding his typing, playing media or frames that couldn't
   be inspected). 28b's sentence on Claude's own tabs says the same.
3. **Instructions at most 3,800 characters.** They keep only rules that span tools; a rule for one tool moves into
   that tool's description. 28a does the move, measures both, and pins the instructions under 3,800 with a test
   beside the 4,096 check; 28b's block fits within the same 3,800, or its builder stops and reports.
4. **`muted`.** `chrome_tabs` shows `muted` when Chrome's `muted` is true, and `sound` only when `audible` and not
   muted (28a item 6, section 6).
5. **28b's "known clean" rule stays.** Its security review compares it with main's rule for unwatched documents and
   looks for page states where the used mark misses his text (autofill, a drop without activation, restored form
   state).
6. **28b item 8** uses `chrome_take_reload` in place of `reload`. After 28b there are 20 tools (28a's 19 and
   `chrome_take_reload`); its pins become 12,300 and 7,200 (28a's, the block of 983 characters, about 400 for the new
   tool's description, about 500 for the new inputs and about 250 for its name and input). Section 6 counts the
   same, and its managed ask rules gain `chrome_take_reload` with 28b.

## The lead's decisions after review 4 (2026-11-15)

`BRIEF-REVIEW-4.md` (NOT READY: B1, B2; S1 to S10; N1 to N10) found the taken-tab rule of `f8065664` weaker than
the rest of 28b, and `chrome_take_reload`'s input unable to carry its question. No review had looked at
`chrome_take_reload` before (it came with `42aa0370`, after both READY reviews).

1. **B1: nothing of his in a taken tab goes by flag.** On a tab of his that Claude has taken, `discard_unsaved:
   true` is refused when his typing **or a frame that couldn't be inspected** would be lost. Only playing media, and
   typing the report marks as all Claude's (main's rule), still go with the flag. The refusal names
   `chrome_release`; for his typing it also carries the approval for `chrome_take_reload`, and for an uninspected
   frame it carries none, since the asking reload never overrides that. 28b's header, item 4, its never-override
   line, item 4a and the Known limits rule now agree; a test covers the frame case.
2. **B2: `chrome_take_reload` follows main's two-step asking pattern.** The refusal that requires the reload
   (`chrome_take`'s `reload_required`, and the taken-tab refusal of `chrome_go` and `chrome_do`) returns main's
   `APPROVAL`, bound to the tab, its title and short address, its document and what the check found;
   `chrome_take_reload` takes it unchanged under the ask rule `mcp__chrome__take_reload`, and the service refuses
   one that no longer matches the tab (it asks again with a new approval). On a tab already taken, the approval
   comes from that `chrome_go` or `chrome_do` refusal, prepared by brief 20's check on the watched document (which
   marks whose typing it is), not by item 4a's used mark, which Claude's own input sets after the take. Sized at
   about 290 characters for name plus input schema (`read_typed_fields` is 285 on main).
3. **S1: 2,800 for 28a, 1,000 for 28b.** 28a's server instructions at most 2,800 characters in all, the 1,652
   shared by every app included, so 28b has 1,000 left under the 3,800 ceiling. In both briefs, rules that belong to
   one tool go into that tool's description; 28b moves its own (the typed-field prepare tool, `chrome_take`,
   `chrome_close`, `chrome_take_reload`). Tests pin 2,800 after 28a and 3,800 after 28b, beside the 4,096 check. The
   top-level `definitions.py` (the Chrome branch of `instructions_for`) is in both briefs' paths.
4. **S2 to S10 as the review suggests.** S7: 28a changes main's `WITHHELD_FORM` text (in `adapter.py` and
   `background.js`) to name `chrome_go` with `to: reload`, with the tests that pin it, and a test fails on any
   removed tool's name. S8: everything decision 2 adds counts toward the budgets (decision 6 below sets them). S10: after 28b, the rule covers a `chrome_do` step only where the tool's guarded reload
   runs before an input (a document that missed the preload, `needs_reload`, or the PLAN-GAP fallback's first
   input); the first input after a take no longer reloads.
5. **Notes.** N1 to N5 and N7 to N10 are done; N6 is decision 7 below.
6. **The budgets: not above the baseline.** 28a keeps "not above the baseline", because making the list smaller is
   the point. Its pins are main's catalogue measured with `tools_for('chrome')` and `instructions_for('chrome')` at
   28a's start: about 9,137 characters for descriptions plus instructions, about 11,080 for names plus input
   schemas. The builder records the exact numbers and pins the final totals; the fixed 11,300 and 6,560 are gone.
   28b's pins are 28a's final measured totals plus at most 1,550 (descriptions plus instructions) and 750 (names
   plus schemas), from the itemised estimates (about 1,450 and 690) with a small margin; first set at 1,300 and 300,
   raised because a cap the builder will certainly hit is no cap. Its builder pins the exact totals.
7. **N6: one tab per flag.** `discard_unsaved` on `chrome_close` applies only when the call closes a single tab. A
   call that names several tabs with the flag is refused, with the advice to close them one at a time. 28a has the
   test; 28b's S9 test follows it.
8. **B1, confirmed:** Claude's own typing may go with the flag; only his typing and uninspected frames are refused
   on his taken tabs.
9. **Effect `delete` for `chrome_take_reload`:** the builder's first choice, with stop-and-report as the fallback.
10. **The next review covers `chrome_take_reload` as a whole.** 28a's 1,148 characters for Chrome's own
    instructions is noted as the most likely place for 28a to stop.

## After package 28's baseline, 2026-11-15

Brief 28a gets a fourth narrow exception in the asking path: its new item 3a, "A list's options in a description".
Written by a Claude agent on Fable 5.2, because it changes what the owner's send approval describes. No review has
seen it yet; the next one looks at it first.

**The finding** (package 28's baseline, run 43698395453; `reviews/28-chrome-read/PROGRESS.md`, "Step 4"; now the last
entry of `reviews/20-chrome/KNOWN-LIMITS.md` on `main`). Brief 20's tools can't send fixture F4: the click on Save
ends in `asking_input_too_large`, nothing reserved, nothing sent. Read again on `main` at `d1a87959`, and it holds:

- `prepare` (`adapter.py`) puts the payload's whole `binding` into the description as `page_state`;
- `binding()` carries `frame['form']`, and `field()` (`reader.js`) lists every option of a list, in the form's
  fields, the target, a page dialog's fields, a send's editable fields and an item's fields;
- `approval_input` (`common.py`) refuses an approval above `ASK_LIMIT`, 16,384 bytes of canonical JSON;
- F4's 200 options are 14,380 bytes, and its whole approval about 21,700. Enter in a field builds the same binding;
- the comparison before an approved input is on the payload, never on the description: `command` sends
  `payload['binding']`, and `input` (`background.js`) compares the whole binding twice.

**The conflict.** 28a's F4 row asks for one question and one arrival, while "What must not change" froze `prepare`
and what the description holds. Its timing of "filling 6 fields and sending the form" had no old send to time.

**What changed in 28a.**

1. **Item 3a and exception 4.** In a description a list shows `chosen` (its selected options, as the binding holds
   them) and `option_count`, in place of `options`: for every list, wherever a field's facts appear, in `prepare`
   and in `free`, by one function on the copy item 3 already makes for the addresses. The payload, `command`,
   `binding`, `question` and the extension aren't touched, so every option is still compared and a swapped option
   is refused, listed or not. `ASK_LIMIT` and `QUESTION_LIMIT` stay.
2. **Nothing a form sends is cut.** Values, hidden fields, chosen options and the text next to Send stay whole
   (rule 4.1). A form that sends more than fits is still refused: about 90 short fields, about 45 with 80
   characters each, a text of about 3,800 characters, or about 900 outside ASCII. `chrome_do` reports it as a
   `refused` step with the refusal's sentence and a fixed piece of advice.
3. **Sizes** (worked through on main's code, not measured in a run; the builder measures): F4 about 7,300 bytes
   with the rule; a single-choice list about 265 bytes whatever its length; a plain field about 145 bytes plus its
   texts.
4. **Tests added:** without a browser, the description's form in every place a list appears, the payload and the
   command still whole, F4 within 9,000 bytes and refused without the rule, four forms that are still refused, and
   a queued submission of such a form. In group 15: F4 asked once and sent; four option swaps after approval
   refused (three of them invisible in the description); a form too large still not sent.
5. **The F4 row and the timing.** The row bounds the approval at 9,000 bytes, and its baseline is brief 20's
   refusal, compared by outcome and calls. The old-against-new timing is "six fills and the click up to the
   question": `chrome_old_fill_form` and `chrome_old_click`, against one `chrome_do`, each until the click on Save
   comes back prepared. In that run both tool sets share `prepare`, so with item 3a brief 20's click is prepared
   too; the refusal is what `main` and brief 28's baseline show. `chrome_submit` is the same code on both sides
   and stays outside the span.
6. **The lists that name the exceptions** now say four: the header, "What must not change", the places the
   security review judges (two are newer than security re-check 2: the time check and this one), "Out of scope",
   the report and the stop rules.

**Also found, and specified in item 3a.** When the page itself starts a submission of a form that is too large
(a held step), `steps` gets the same refusal from `prepare` and doesn't catch it. `read` calls `steps`, so on `main`
every later read of that tab fails with `asking_input_too_large` until the document goes. Nothing is sent. In 28a
`steps` records such a step as stopped and not resumable, acknowledges it, and the call returns normally.

**Considered and left out.**

- *A digest of the options in the description.* The payload keeps the list itself and is what gets compared; a
  digest would add bytes he can't read and no check.
- *Keeping short lists whole.* One form for every list is easier to test and to review. No test on `main` that
  reads `page_state` reads a list's options (they read the tab, address, title, adapter, editable fields, compose
  text and an item field's value).
- *Cutting long values, leaving fields out, or dropping a field's flags that are false.* The first two hide what
  he approves. The third doubles the room and still leaves a limit, while every form's description reads
  differently.
- *A larger `ASK_LIMIT`.* Not needed for F4, and the limit is the base's, shared with Mail.
- *Chrome's own size check in `prepare`.* It would need a second limit beside the base's; the advice is added
  where `chrome_do` and `steps` report the refusal.

**Section 6** says the same: "How an asking action runs" (what the content fields show of a list, and that the
comparison covers every option), the efficiency table's form row and the latency line, two known limits ("A question
shows a list's chosen option…" and "A large form isn't sent by Claude"), and a line in test group 15.

**For the lead.** Two limits of `main` that this note only names: a text of more than about 900 characters in a
script outside ASCII can't be sent through a form (each character is 6 bytes after escaping and counts three times),
and a form with a long hidden value, such as a framework's page state, can't be sent at all. Showing a hidden value
cut would let such forms through and would reduce what he can inspect; that is a decision, not part of this change.

**Lead's decision on the hidden-value question (2026-11-15, `linux-tools`):** a form with a long hidden value (a
framework's page state) stays refused, as the known limit says. Hidden values are not shown cut in the question:
the owner would see less of what is sent, and the refusal fails closed (he sends it himself). Revisit only if live
use shows real sites hitting it. Non-ASCII text's size cost stays a known limit for the same reason.

## After review 5 (lead, 2026-11-16)

`BRIEF-REVIEW-5.md` (NOT READY: B1, B2; S1 to S7; N1 to N8) read the briefs at `8a59a373`. The lead (`linux-tools`)
decided each finding. A Claude agent on Fable 5.2 wrote the decisions into the briefs and checked each claim against
the code: the extension and the service on this branch, and `origin/pkg/28-chrome` at `8ae7e8b0`. `main` (`937a1868`)
was merged into this branch first, because brief 18c-b (S6) and PR #77's code reached `main` after the branch was
cut. The merge changes none of the three briefs, section 6 or this folder.

| Finding | Decision | Where it went |
|---|---|---|
| **B1** In a taken tab, work of his that brief 20's check can't see was lost with no question | The review's fix. "Used since the take" counts his typing, his clicks and keys (told apart from Claude's in `guard.js`), and drops and pastes. When it is set, `chrome_go` and a `chrome_do` reload refuse the plain call and the flag, and carry the `chrome_take_reload` approval. A step that follows a link or submits a form is checked first and asks the same way. A navigation that a page's own script starts from another element is a known limit. | 28b: header; "Already decided by the lead"; item 4 ("On a tab already taken", "A taken tab he has used since the take", "`discard_unsaved: true` is refused", "A step that leaves the page", "What the tool can't see beforehand"); "What must not change"; tests "Used since the take"; Paths (`guard.js`); "Known limits". Section 6: "Which tabs Claude works in" ("Nor a page he has used"), `chrome_go`'s row, "Until brief 28b merges", the known limit "In a taken tab, a navigation that the page's own script starts" (it replaces "What he types into a taken tab can be lost"), test group 17. |
| **B2** A `select` step's approval hid the option it would choose | `choosing`: the options of the binding whose value equals the input's value, as bound. Every option stays bound and compared. | 28a: item 3a (rule, sizes); exception 4; the security review's places; tests without a browser and in group 15; "Decided here". Section 6: "How an asking action runs" (the content fields), the known limit on a list's options, test group 15. |
| **S1** The take checked before it attached and reloaded after | The check runs again as the last thing before the reload; a tab that is no longer clean gets its attach and mark undone. `chrome_take_reload` on a tab not yet taken does the same. | 28b: item 4, point 3 and the `chrome_take_reload` bullet; the "Taking" tests. Section 6: "Before the tool reloads or closes one of his tabs". |
| **S2** The re-check's new approval ignored the four never-offered cases | In those four cases the re-check's refusal carries no approval. | 28b: item 4, the `chrome_take_reload` bullet and its "Tests" paragraph. Section 6: "Whatever could be lost is reported first". |
| **S3** A stale install pause was allowed to stay a known limit | Fail closed: a pause that can't be shown current counts the document as not watched from its start (`late`). | 28a: item 5a (the whole harm, the rule, the fallback, tests); the security review's places. |
| **S4** Item 5a had no place in 28a's frozen lists | 5a stays in 28a. Both points are in the `background.js` list, the paths and the security review's places. The popup's address is in the short form with the `no` mark. `take_tab` is `chrome_take`. | 28a: item 5a; "What must not change" (the take rules, the security review's places); "What changes in `background.js`"; Paths. |
| **S5** The never-list gate's sweep: 28a silent, 28b missing two paths | One rule in both briefs: a PR that adds a Chrome tool adds it to brief 18c-b's sweep (`SWEPT`) in the same PR, with the gate's refusal expected, never to the named exceptions; whichever merges second does it when it takes `main`. 28b's list gains `chrome_close` of his tab and `chrome_open` with `tab`. | 28a: item 7, "The never-list gate's sweep". 28b: item 9, last bullet; test "The never-list's placeholder". Section 6: test group 17. |
| **S6** The guide let an empty list open the gate with his dashboard open | His dashboard's host goes on the list first; the list is empty only when he has no site to exclude. The format lines stay. | `briefs/18c-b-chrome-image.md`: "What the owner will see" and "For his guide". Section 6: "Where Claude may go". |
| **S7** The late shadow-root rule | It stays for package 28 (PR #72). The narrowing is permitted in brief 28, not required. Follow-up below. | 28: item 1 ("A permitted refinement"), "What must not change" (the hold), Paths. |
| **N1** | `chrome_take_reload` returns the reloaded page's outline, as `chrome_take` does, within 18 seconds. | 28b: item 4, the `chrome_take_reload` bullet; item 8 (its description point). |
| **N2** | The question for a tab not yet taken says that Claude takes it. | 28b: item 4. Section 6: "Whatever could be lost is reported first". |
| **N3** | Recounted; numbers below. | 28b: item 8. |
| **N4** | A row for `chrome_take_reload`. | Section 6: "Actions". |
| **N5** (topic 4) | Two fixed pieces of advice: "Shorten the text you filled" only when the approval would fit with the typed text left empty. | 28a: item 3a ("A form that still doesn't fit"); tests. Section 6: the known limit "A large form isn't sent by Claude". |
| **N6** | A known limit, with a measurement for the builder. | 28b: item 4a ("Frames that take no reader"); tests; Report. Section 6: "Known limits". |
| **N7** | A frame the drop-and-paste record doesn't cover makes the tab used: an approval is offered. | 28b: item 4a. |
| **N8** | `chrome_upload`'s refusal carries the approval for his typing or use, names `chrome_release` for a frame, and otherwise says to reload with `chrome_go`. | 28b: item 4 ("Which `chrome_do` steps that covers"). 28a: item 6, `chrome_upload`. |

**The schema sizes (N3),** counted with main's helpers on this branch, as compact JSON, each property with the comma
that joins it:

- `request` (`string(200)`): 58 characters a tool, 290 for five tools;
- `seen` (a two-digit length limit): 54 a tool, 162 for the three tools that didn't have it;
- `chrome_take_reload`: 279, its name as the catalogue counts it (`take_reload`, 11) and `APPROVAL` (268);
- together 731; `chrome_take` loses `reload` (28), which leaves **703 of the 750**. The review's 747 used 60 and 56
  a property;
- `seen` and `request` stay optional in every schema, `chrome_take`'s too (JUDGMENT-CALL 6). Required on
  `chrome_take` they would add 17: 720;
- main's catalogue today: 30 tools, 11,080 for names plus schemas, 5,085 for descriptions, and 4,081 for the
  instructions, which were 4,052 before PR #77. Briefs 28 and 28a and section 6 now say 4,081 and 9,166.

**Follow-up for package 28 (S7).** The reader can meet a shadow root at `attachShadow`, while it is still empty.
In a watched document `page.js` already wraps `attachShadow` and reports each new root to the isolated guard
(`watch_root`, read on this branch), and the guard watches it. Met there, a root's fields have their whole masking
history in front of the password tracker, as in the light DOM. Only roots met any other way stay late: built and
filled through a fresh realm's natives, attached while no guard was linked, or declarative. The work is one line in
`guard.js`'s isolated part and the meeting in `reader.js`, with the three tests brief 28 now names. Until it is
built, every prefilled field in a component upgraded after the load is unread, and its form can't be sent by
Claude.

**JUDGMENT-CALLs for the lead.** Each is where a decision met the code and the safer reading was taken.

1. **B1, whose press it was.** The decision names `ownerInput`'s test. `ownerInput` runs only while a hold is
   active, keeps nothing, and drops every event while a dispatch of Claude's is in flight; a lost finish leaves
   that state set. So the brief's line sits beside `typed` in `captureInput`, counts `pointerdown`, `mousedown` and
   `keydown`, and follows `typed`'s rule during a dispatch: a press on Claude's target is Claude's, every other is
   his. A `click` counts only outside a dispatch (an assistive tool's activation has no press), and the up events
   never: otherwise Claude's own Enter and Tab would mark a page as his. *Cost:* a step of Claude's that lands
   off its target asks once too often; a test shows that none of Claude's step kinds does. *Rejected:*
   `ownerInput`'s plain test, which misses his press during a dispatch.
2. **B1, more than one line in `guard.js`.** A file dropped onto a page fires no `input` event, and the browser's
   own mark is no help in a taken tab. Where item 4a's record isn't built, the guard needs one passive listener for
   `drop` and `paste` beside its `copy` listener. 28b's paths allow that and the one statement, nothing else.
3. **B1, where the check before a leaving step runs.** In the extension's `input`, before the last facts read, so
   it can only refuse and brief 20's last comparison stays last. That opens `input` in 28b for a second thing
   (after item 7's tab selection). It also runs when an approved operation of such a step is dispatched, and
   before an asking step's question. *Rejected:* a check command sent before `input`, which leaves `input` alone
   but leaves a gap, and misses what he does while a send's question waits. A submission the page starts and the
   tool holds is not checked: it is the page's own navigation (the known limit), it has its own question, and
   checking it would stop his own delayed step in a taken tab (board #138) from ever being resumed.
4. **B1, what a leaving step is checked for.** The used mark and a frame that doesn't answer, across the whole
   tab; for a click or an activating key on a link (or an element inside one) and for every form submission. Not
   brief 20's field walk: a field that a page's script changed would then ask at every link, and again after
   every approved reload. The decision said "navigating the top document"; a link inside a frame replaces a
   document he may have used too. *What he will notice:* a form he corrected himself in a taken tab is one he
   sends himself, or he approves a reload that empties it. *For the tests:* an older case in which the owner acts
   in a taken tab before Claude's link or submit runs in a Claude tab instead, assertions unchanged (28b, "Moved,
   not changed").
5. **S3, the fallback.** If no reliable "pause still current" check can be built, the first document a session
   installs from a pause after a re-arm counts as `late`. "Every document after a re-arm" would reload such a tab
   for ever.
6. **N3, `seen` and `request` optional on `chrome_take`.** 28a's item 5a lets Claude take a popup of its own that
   isn't under control, which needs neither. The service refuses a call on one of his tabs without them.
7. **N5, two pieces of advice, not one.** The service measures once more on a copy to choose the sentence. One
   reworded sentence would be simpler, and would still send Claude to shorten text in vain.
8. **N6, the wording.** The decision calls them frames that can't hold work. A PDF form can hold his typing, so
   the brief says the tool can't tell, and no frame kind is exempted without the lead's OK.
9. **S7, `guard.js` in brief 28.** The narrowing can't be built without one line there (the relay calls the
   guard's own `watch`, which the reader can't hook). Brief 28's paths allow that one line for the refinement only.

## After review 6 (lead, 2026-11-16)

`BRIEF-REVIEW-6.md` (READY: S1 to S5 should-fix, N1 to N8) read the briefs at `41df1378`. The lead (`linux-tools`)
decided each finding. A Claude agent on Opus 5.5 wrote the decisions into the briefs on `8fc34061` and checked each
claim against the code on this branch: `background.js` (`input`, `content`, `connect`, the re-arm), `guard.js`
(`typed`, `ownerInput`, `captureInput`, `control`, `search`), `reader.js` (`reloadState`, `select`), and the
service's `payload`, `execute` and the engine's replacement path; the sweep against `origin/pkg/18c-b-chrome`.

| Finding | Decision | Where it went |
|---|---|---|
| **S1** The check before a leaving step could land after the tab selection and `reveal` | It runs right after the loop that arms the frames, before the tab selection and 28a's `reveal`, which both set `effectStarted`. A refusal there carries the approval, never reaches the service as `unknown: Input may have started`, and his tab isn't brought to the front. | 28b: item 4, "Where it sits in `input`"; "What must not change"; test "a step that leaves the page" (a taken tab in the background). |
| **S2** (fix) A frame he used that the page removes took the used mark with it | "Used" is sticky per tab in the extension, as security re-check 4 requires for drops. The guard reports a document's first mark of his once, through the reader; the extension keeps the tab used until an approved `chrome_take_reload` or a new top document; the check reads that flag as well as asking the frames. | 28b: item 4 ("The answer is sticky in the extension"; "A step that leaves the page"); "What must not change" (`guard.js`); Paths (`guard.js`: one more call); test "the mark stays when its frame goes". Section 6: "Nor a page he has used"; test group 17. |
| **S3** (known limit, and a fix) The limit was worded more narrowly than what item 4 leaves unchecked | The limit names the accepted paths: a button, a `javascript:` or `#` link, or a link that opens a new tab, whose handler navigates; a form's other control whose handler submits; a page script that clears his work without navigating. Reset controls join the checked kinds. Section 6's "held and asked" holds only within the hold after Claude's step, and never for a GET search form. | 28b: header; "Already decided by the lead"; item 4 (the three kinds; "What the tool can't see beforehand"); "Moved, not changed"; "Known limits". Section 6: "Nor a page he has used"; the known limit "In a taken tab, what the page's own script does after a step"; test group 17. |
| **S4** The check before an asking step's question, and `chrome_submit`'s refusal, had no place | On a taken tab the `facts` reply carries the used result, and `payload` refuses a leaving step that would ask before `engine.reserve`, with the approval. `chrome_submit` returns its operation `failed` with `reload_required`, nothing sent, and the `chrome_take_reload` approval in `reload_approval`, through main's replacement path (`NothingLeft` with `replacement`), so the engine doesn't change. Both are allowed in "What must not change". | 28b: item 4 (two bullets, and `chrome_do`'s entry); "What must not change"; tests. |
| **S5** (fix) Item 5a's example check passed the stale pause | The example is dropped. Only a check that proves the pause itself still holds qualifies; otherwise the first install from a pause after a re-arm counts as `late`, which can't loop (JC5). | 28a: item 5a (the rule, why the example fails, the fallback, tests). |
| **N1** | "Used" is a record of its own beside the typing marks, never one of them, and never `typed`'s containment test: a press is Claude's only on the target or inside it (for a key, also in the editing host around it). | 28b: item 4; Paths; tests (his press on the body during a dispatch; Claude's click in a design-mode frame isn't typing). |
| **N2** | A `<label>` resolves to its `control`; `area` and SVG `a` are links; Enter in a `textarea` isn't a submit. | 28b: item 4 (the kinds); tests. |
| **N3** | `main` has no such measurement: its key tests in `control/chrome/ci/` send the owner's keys through `xdotool`, never through DevTools. 28b measures F5, Ctrl+R, Alt+ArrowLeft and Ctrl+W sent as steps in a taken tab, and refuses there any that acts. | 28b: item 4 ("Keys Chrome may act on itself"); tests; Report. |
| **N4** | The five tests. | 28b tests: a paste; a frame not watched from its start; an asking send refused before anything is reserved; the removed frame. 28a item 5a: a late install, then `document_start` after its guarded reload. |
| **N5** | A frame that takes no reader also stops link, form and reset steps in a taken tab he hasn't used; the measurement adds an extension's frame that appears when a field is focused. | 28b: item 4a ("Frames that take no reader"); item 4; tests. Section 6: the known limit on such frames. |
| **N6** | A `select` step replaces the choice: after it only `choosing` is chosen, also on a multiple-choice list. The optional question line stays as on `main`. | 28a: item 3a. |
| **N7** | In the PLAN-GAP fallback, the first input's reload runs item 4a's check. | 28b: item 4 ("Which `chrome_do` steps that covers"). |
| **N8** | His-tab sweep entries get keys of their own (`'chrome_read his tab'`); a brief's own copy of the sweep goes once PR #76's test with its entries is on `main`. | 28b: item 9. 28a: item 7. |

**Choices made in writing, within the decisions.** No decision proved wrong against the code, so there are no new
judgment calls. Three choices are worth naming:

- *The field's name.* `reload_approval` in `chrome_submit`'s result, because `approval` there already means a new
  question for `chrome_submit` (main's replacement after a changed destination). `chrome_do`'s step entry uses the
  same name, so Claude meets one name for one thing. `chrome_go`'s and `chrome_take`'s refusals keep `approval`,
  which nothing else uses there. The instructions' "a reload_required with an approval" covers both, so their size
  doesn't change.
- *What S4 changes on `main`.* `execute` re-raises a `reload_required` it doesn't expect, and the engine records any
  such error as `unknown` ("Submission outcome uncertain"). So the mapping in `execute` is needed, not optional; the
  brief says so.
- *S3's wording.* The review's sentence that a step's own effect in the page, such as Claude's fill over a field,
  follows the asking rules went in too, so that the limit isn't read as covering Claude's own steps; and a link
  that opens a new tab is named among the accepted paths, since item 4 already lets it run.

## After review 6's recheck (lead, 2026-11-16)

The recheck of `1028ec49` said READY with three nits; the lead made them directly:
- **R1:** 28b item 4's `chrome_take_reload` bullet now names both fields: `approval` for `chrome_take` and
  `chrome_go`, `reload_approval` for a `chrome_do` step and `chrome_submit`.
- **R2:** `reload_approval` (and main's `approval` and `state` on the replacement path) are declared in
  `chrome_submit`'s and `chrome_do`'s output schemas, with a test that `chrome_submit`'s result validates against
  its schema.
- **R3:** 28a item 5a's rule and its first test say "shown to still hold", not "shown current".

PR #48 merges on this READY; Codex's `gpt-6-astra` cross-reviews the merged briefs (Tue 2026-11-17), and its
findings go to the 28a and 28b builds.

## After BRIEF-CROSS-5

Revision for the lead `linux-tools`, 2026-11-18, against `main` at `918fba67`, package 28 at `e07a88eb`
and 18c-b's step-2b record at `c4514015`. The earlier entries remain history; the held-submission exception in
review 5's JUDGMENT-CALL 3 and review 6's S3 is superseded here, including the READY recorded after the recheck.
Owner questions below are recommendations for his decision, not decisions attributed to him.

- **1 — Profile continuity:** keep the logical service pin through A → B → A; recommend explicit owner relink after each extension replacement, with only an installation id exempted from 18c-b's storage ban; reject every unapproved/retired pair and other profile; owner question 1 stays open (28b item 1; 18c-b's CROSS-5 handoff).
- **2 — Held submissions:** resumption is controllable and loss is a fix; check whole-tab work at preparation and resumption; recommend one send/loss question, no preliminary reload, retaining board #138 in taken tabs; owner question 2 stays open (28b item 4c; CONTROL's loss limit narrowed).
- **3 — Link references:** classify fresh control facts before reference-open; asking controls refuse and point to the asking click; explicit URL/tab-address/library policy stays separate (28a item 4).
- **4 — Reload freshness:** bind field/frame/document/reader identities and every later owner-edit generation, not merely sticky use; missing continuous observation refuses without approval, values stay unread (28b item 4d).
- **5 — Loss reports:** fixed service code/message, page details only in untrusted loss data across bare, batched and stored results; approvals use the untrusted description (28a item 5b; 28b item 0).
- **6 — Section 6 parity:** incorporate the mixed-case/digit token rule with `_`/`-`, defer to brief 28's full address algorithm, and list the 5,000-reference paging ceiling with harm and alternatives (CONTROL; 28a inherited regressions).
- **Package 28 inheritance:** preserve repaired fresh-side comparisons, unique native option resolution and end-of-control reference cleanup on all new paths; no claim that the in-flight branch is fully verified (28a/28b item 0).
- **Distinct fields:** 28a item 3b changes the frozen asking-description path; every field is distinguishable after repair/shortening with identity/order still bound; 28b inherits it, including loss questions.
- **Instruction budget and steps:** measured 4,093 instructions plus 5,085 descriptions = 9,178; 28a compacts before additions and pins 2,800, 28b verifies headroom then pins 3,800; no new instruction text in this revision; both have bounded gpt-6.1-sol build steps and named test/mutation pairs.

The detailed changes, code evidence, owner options and 18c-b remaining-step handoff are in
[`REVISION-CROSS-5.md`](REVISION-CROSS-5.md). No finding is rejected. No product code or workflow was run/changed
by this revision; the builder tests described above remain implementation work.

Revision 2 after `RECHECK-CROSS-5.md`, from `d175acdd`; `linux-tools` remains the lead:

- **Pin restore authority:** only committed `store.chrome_state`; locked current-pair hellos are quarantined, every admitted connection closes before recovery reopens the gate, and missing restored state never enrolls (28b item 1/step 2; CONTROL §6).
- **Restore regression/mutations:** P → backup → switch Q → restore P database, attempts before/after confirmation, P never serves Q and Q must reconnect; disposable lookup and omitted recovery closure/revalidation each fail that regression (28b Tests).
- **Profile confirmation recommendation:** helper button plus F7's uncached password dialog, no typed IDs or administrator command; the owner checks the Chrome picker name supplied at setup, and no/cancel/timeout leaves the pin unchanged and candidate refused; authorization is not proof against copied state (owner question 1 remains open).
- **Dialog ownership:** 28b step 2 builds the candidate channel, name UI and bound polkit lifecycle; 18c-b 3a already installs the action, with 4/4b and 5/C7 proving the real-session dialog before shipping; failure still stops for the lead.
- **18c-b handoff:** at `91ad33d6`, next is **3a fix** for the PEM scan's root-home link to boot-created `var/roothome`; keep the two-image-round stop and require the lead's disposition before any further image run or 3b.
- **Unchanged:** findings 2–6 stay closed as specifications, owner question 2 stays word for word, and Unicode/cleanup, distinct descriptions, 28a's 2,800 then 28b's 3,800 caps and step order remain.
