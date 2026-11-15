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
