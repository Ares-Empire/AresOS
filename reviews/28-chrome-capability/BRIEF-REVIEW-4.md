Verdict: NOT READY

# Brief review 4: briefs 28, 28a, 28b and section 6 after the merge of main

Fresh reviewer (Opus), 2026-11-15, on `briefs/28-chrome-capability` at `f8065664`. Scope: what changed since
`42aa0370` (`git diff 42aa0370 HEAD -- briefs/28-chrome-read.md briefs/28a-chrome-act.md
briefs/28b-chrome-his-tabs.md docs/design/CONTROL.md reviews/28-chrome-capability`), checked against main's code
on this branch. Nothing was run in CI. The local checks were plain Python (`instructions_for`, `tools_for`) and
`gh run view` for the two durations.

**Scope fact for the lead.** `42aa0370` isn't a reviewed state. It *introduced* `chrome_take_reload`, and both
READY reviews come before it: `BRIEF-SECURITY-4.md` is at `108d097f`, and `BRIEF-REVIEW-3.md` at `32d63d10` or
earlier. No review on record has looked at `chrome_take_reload`. The changes since build on it: the new taken-tab
refusal sends Claude to it, and item 8 sizes it. So B2 below is in scope through those lines.

## Claims about main that check out

- 30 Chrome tools in `tools_for('chrome')`. `chrome_sites` is owner-only and not among them. 28a's removal list
  (18 tools) plus 7 new tools gives 19, and section 6's table lists those 19 plus `chrome_sites`.
- `prepare_read_typed_fields` takes `{tab}` and returns `PREPARED_RESULT`. `read_typed_fields` takes `APPROVAL`.
  Their descriptions are 361 and 469 characters. The prepare tool's name plus compact input schema is 142 (25 +
  117). The ask rules (`control/settings/ask-rules.json`) are `mcp__chrome__read_typed_fields` and
  `mcp__chrome__submit`.
- `instructions_for('chrome')` is 4,052 characters. `test_fixes_b_server_instructions_fit_the_native_cli_limit` is
  at `test_questions.py:455` and loops over every app in `APPS`.
- `discard_unsaved` (`DISCARD` in `chrome/definitions.py`) is on `navigate`, `close_tab` and every input verb.
  `requireDiscard` runs before an address, back, forward, reload (through `reloadChecked`), `close_tab` and the
  first-input reload (`prepare_control`). Its report names labels and who typed them, and counts playing media
  (`audible` or an element) and uninspected frames. Its advice text and `DISCARD_NOTICE` match what the briefs
  quote.
- `reloadState` (`reader.js:525`) works as 28a item 6 and 28b item 4a describe it. In an unwatched document every
  `typedField`, hidden input and editor counts. In a watched one a field counts when it changed or got input and
  still holds text. `typist` gives "the owner" unless the guard saw only Claude, in this release, with the
  dispatch confirmed.
- `chrome_tabs` rows carry `audible:tab.audible===true` and `muted:tab.mutedInfo?.muted===true`.
- `HOLD_MS = 500` (`policy.py:23`). `collectSteps` waits `POLICY.holdMs+25`.
- `latency-targets.json`: the six ceilings, `samples_per_call` 60, `old_runtime_samples_per_call` 20. The harness
  and test files named in 28 all exist.
- Polkit for "Don't ask again" and read-only off: `confirm.py` (`org.aresos.control.chrome-loosen`, F7).
- `scriptParsed` matches by `params.url` with `isDefault===false` (`background.js:124-126`).
  `pending.retry??=lateReader(tab)` is at line 609. `control_status` carries `installs:installRecord()`, and
  nothing in `aresos_control/` calls it.
- The KNOWN-LIMITS sentence matches `TOOLS-HANDOFF.md` word for word. Main makes the group in the tab's window
  (`createProperties:{windowId:current.windowId}`).
- Runs 43641834739 and 43641839672: 28 jobs each, 40 and 61 minutes.
- The arithmetic: 10,500 + 361 gives 10,900, and 6,300 + 142 gives 6,450. 28b's block is 983 characters (it was
  920), so 10,900 + 983 + about 400 gives 12,300, and 6,450 + about 500 + about 250 gives 7,200.

## Blocking

### B1. 28b item 4: on a taken tab, uninspected frames can still be discarded by flag

*Where:* `briefs/28b-chrome-his-tabs.md`, item 4. The sentence is "Playing media and frames that couldn't be
inspected, alone, may still go with `discard_unsaved`" (lines 292-293). The test line "His typing in a taken tab is
never discarded by flag" is at 644-647.

*What's wrong:* in main's own report, a frame that couldn't be inspected is one that "may hold unsaved typing". On
a tab of his, that typing is his. The new sentence lets it go after only a chat OK. Four other places in 28b say
the opposite:
- item 4: `chrome_take_reload`, the managed ask, "never overrides … a frame that doesn't answer the check". So the
  weaker consent (an OK in the chat) can do what the stronger one (Claude Code's prompt) may not;
- item 4a: "Unknown is not clean", and "a frame the record doesn't cover leaves the tab unknown, never clean";
- the header's security charge (lines 26-31): the review is to check "that no path discards his typing in a tab
  Claude has taken without his answer in Claude Code's prompt". This sentence is such a path;
- the Known limits rule: "work of his lost … is never a limit". So it can't be accepted as a limit either.

The test line covers media and Claude's own typing but not this case.

*Why it matters:* the builder will build what the sentence says, and 28b's security review is told to reject it.
That costs a fix round on the package where his own typing is at stake. The case is real but narrow: at the take
every frame answered, and a frame added later doesn't answer.

*Fix:* on a taken tab, frames that couldn't be inspected also refuse `discard_unsaved`. The refusal names
`chrome_release`: he looks at the tab himself, as for `chrome_take_reload`'s four cases. Only playing media alone,
or typing that is all Claude's, goes on with the flag. Add the test case: a taken tab gets a frame that doesn't
answer, `chrome_go` with the flag is refused, and `chrome_take_reload` isn't offered. If the lead keeps the
exception, the header, item 4's never-override line and the Known limits rule must each say so, with the reason.

### B2. 28b item 4 and item 8: `chrome_take_reload`'s input can't carry its question

*Where:* item 4 says "`chrome_take_reload` (input `tab`, `seen`, `request`) … The service prepares it from the
check it just ran and the question shows, first: which tab (title and short address) … what the check found …
The approval is bound to that tab, its document and what the check found". Item 8 sizes it as "about 250 for
`chrome_take_reload`'s name and input (`tab`, `seen`, `request`)". The new refusal sends Claude to it "(which
accepts a tab already taken)".

*What's wrong:* a managed ask holds the call and shows the tool's input. With `tab`, `seen` and `request` as the
input, Claude Code's prompt shows a tab number, a list reference and Claude's own words. It can't show the
title, the short address or the labels the check found, and there is nothing that binds "what the check found".
Main solves this in two steps. A preparing call returns `APPROVAL` (`question`, `operation_id`, `description`),
and the asking call takes it unchanged (`APPROVAL_INSTRUCTION`): `chrome_submit`, `read_typed_fields`. The brief
says "like `chrome_submit`" and also names an input that doesn't fit that pattern. For a tab already taken, it
doesn't say what prepares the question at all.

*Why it matters:* this question is the one protection for his typing in 28b. A builder has to choose between the
stated input (a prompt that shows him nothing) and main's pattern (a different input, size and flow), and no
review has looked at either.

*Fix:*
- `chrome_take`'s `reload_required` returns a prepared approval for the reload. So does the new refusal of
  `discard_unsaved` on a taken tab, or else `chrome_take` on a tab already taken runs the check again and returns
  one. Either way, say which check prepares it on a taken tab: on the watched document after the take, 4a's used
  mark would be set by Claude's own input.
- `chrome_take_reload` takes that approval unchanged (main's `APPROVAL`). `tab`, `seen`, `request` and the
  findings are bound inside the preparation.
- The ask rule is `mcp__chrome__take_reload`.
- Size it like `read_typed_fields`: 285 characters on main for name plus schema, so about 290 instead of 250.
  Item 8 and section 6's 7,200 move with it.

## Should fix

### S1. The 3,800-character budget almost certainly can't hold both packages' text

*Where:* 28a item 7, 28b item 8, section 6 "What every server pays once".

*What's wrong:* 1,652 characters of `instructions_for('chrome')` are `COMMON_INSTRUCTIONS`, which every app
shares and which neither package may change. Only 2,400 of main's 4,052 are Chrome's own. Under 3,800, Chrome's
own text gets at most 2,148 characters. 28b's block takes 983 of those, which leaves 28a about 1,165 for all its
shared rules and brief 28's outline-reading text. That is less than half of main's current Chrome text, while
28a's rule list is longer than main's.

28a doesn't tell its builder to leave room for 28b. 28b says "if it doesn't fit there, stop", but it doesn't say
whether the points of its block that belong to one tool may move into descriptions, as the lead's rule does for
28a. ("Close a tab of his only when he asks" is `chrome_close`'s; "prepare it first" belongs to the typed-field
tools.) A third gap: the top-level `control/aresos_control/definitions.py`, whose `instructions_for` appends the
Chrome text, isn't clearly in 28a's "May change".

*Why it matters:* the likely outcome is a PLAN-GAP stop in 28b, after 28a has merged with instructions that leave
no room.

*Fix:*
- state the common 1,652;
- give 28a a target for Chrome's own text that leaves about 1,000 for 28b (Chrome's part at most about 1,150), or
  let 28b move its one-tool points into those tools' descriptions. That move is budget-neutral, since 12,300
  counts both;
- name the top-level `definitions.py` in 28a's paths;
- or settle on another number now.

### S2. Section 6 doesn't record the new taken-tab rule, and one line there is now wrong

*Where:* `docs/design/CONTROL.md` line 643: "brief 28b replaces that flag by `chrome_take_reload`". Also the
`chrome_go` row of the Actions table, and the 28b test summary around line 1640.

*What's wrong:* after `f8065664`, the flag stays on a taken tab for media and for Claude's own typing, and is
refused only for his typing. Section 6, the design record, mentions neither half.

*Fix:* add one sentence under "Acting takes the tab" (or "Until brief 28b merges") and one test line, matching
28b item 4 as amended by B1.

### S3. Stale claims about main in 28a item 6 and section 6

*Where:*
- 28a `chrome_close`: "Brief 20's `chrome_close_tab` closes any tab in the group, a taken one too, without
  looking at what it holds". Main runs `requireDiscard` first (`background.js:982`), and the same bullet now says
  "Main's guard stays".
- 28a `chrome_go` in a taken tab: "would replace his page without any check in brief 20". Main's `navigate` runs
  `requireDiscard` for an address, back, forward and reload (lines 984-992).
- Section 6, line 649: "Brief 28a already stops two things brief 20 allowed: closing a taken tab, and navigating
  one before its reload without that check". Only the first is still new. What 28a adds for the second is the
  guarded reload before the navigation.

*Fix:* reword the three lines to what main does now.

### S4. 28b item 3, "Ask first": the typed-field read still takes `seen` and `request`

*Where:* line 222, "it takes `seen` and `request` like every call on one of his tabs", where "it" is
`chrome_read_typed_fields`.

*What's wrong:* item 2 now says that `chrome_prepare_read_typed_fields` takes them and `chrome_read_typed_fields`
"takes no `seen`". Item 8's size line agrees with item 2.

*Fix:* "the prepare tool takes `seen` and `request`; the read is held to what its approval binds".

### S5. 28b, end of "Tests": the ask rules can't stay byte-identical to main's

*Where:* line 737, "the Chrome ask rules byte-identical to `main`'s".

*What's wrong:* 28b adds the managed ask `chrome_take_reload` (item 4, the header, section 6's "Brief 28b adds a
third"), so the rules gain a line. The line dates from before `42aa0370`. It is the same kind of 2026-11-14
leftover as alignment point 6, which the alignment didn't catch.

*Fix:* "the Chrome ask rules are main's plus `mcp__chrome__take_reload`, and nothing else changes".

### S6. Brief 28's paths don't allow its new item 8

*Where:* brief 28 "Paths": "`background.js` (only as items 1 and 4 say)".

*What's wrong:* item 8 changes the `scriptParsed` branch of `background.js` and adds a test, but the paths don't
allow it.

*Fix:* "items 1, 4 and 8".

### S7. Main's refusal text names `chrome_navigate`, which 28a removes

*Where:* `WITHHELD_FORM` in `control/aresos_control/chrome/adapter.py:26` and in `background.js:770` says "reload
the tab first with chrome_navigate direction=reload". `test_questions.py` asserts that text.

*What's wrong:* 28a step 3 removes `chrome_navigate` but says nothing about this text. The tests that pin the old
name would still pass with it left in, so Claude would be pointed at a tool that doesn't exist.

*Fix:* in 28a step 3, every refusal and description that names a removed tool names its replacement
(`chrome_go` with `to: reload`), with a test that no description, instruction or refusal text names a removed
tool.

### S8. 28a's sizes don't count the lead's decision 2

*Where:* 28a item 7 and its budget table (10,900 and 6,450).

*What's wrong:* the new budgets add only the prepare tool. The same decisions put `discard_unsaved` on
`chrome_go`, `chrome_close` and `chrome_do` (37 characters of schema each, about 110 in all). They also add main's
unsaved-work rule (280 characters as `DISCARD_NOTICE`) and the guard's mention in three descriptions. None of that
was in the 18-tool targets.

*Fix:* either say these come out of the existing margin, or raise the pins by about 110 and 400 (for example
6,560 and 11,300), with 28b's pins and section 6 moving with them.

### S9. 28b, closing his tabs: no test that the flag can't close a kept tab of his

*Where:* 28b item 5 and "Tests".

*What's wrong:* `chrome_close` now has `discard_unsaved` (28a). Item 5 says "There is no input that closes a kept
tab", but no test pins that against the flag.

*Fix:* add one sentence (the flag is for Claude's tabs and doesn't override item 4a for his) and a test. A call
that names a Claude tab with Claude's typing and an untaken tab of his that isn't known clean, with
`discard_unsaved: true`, closes the Claude tab and keeps his, with its reason.

### S10. 28b, the `chrome_do` half of the new rule: when does it apply?

*Where:* item 4 and the test line at 644-647.

*What's wrong:* after 28b the take does the reload, and "the first input after a take doesn't reload again". A
`chrome_do` step reaches the discard check on a taken tab only when a document missed the preload
(`needs_reload`), or in the PLAN-GAP fallback where the reload stays at the first input. The test line, "a
`chrome_do` step, with `discard_unsaved: true`, [is] refused", doesn't say how to build that state. One reading
is "refuse the flag on any step while his typing is there".

*Fix:* name the state (a frame added after the take that missed the preload), or say that on a taken tab the flag
is refused outright while the report lists his typing.

## Notes

- **N1** (28a item 5.6 and item 7). `chrome_take` with `reload: true` discards the same things as the flag (it is
  `prepare_control` with `discard_unsaved: true`). Main's ask rule ("get his OK in the chat before setting
  `discard_unsaved`") is attached only to the flag. Add "`reload: true` follows the same rule" to `chrome_take`'s
  description. 28a never reaches the laptop without 28b, so the harm is bounded.
- **N2** (28b item 8). The first paragraph says the instructions "must stay within 4,096"; the paragraph after the
  block says 3,800. Use 3,800 in both.
- **N3** (28a item 6, 28b item 2, section 6 table). "`chrome_prepare_read_typed_fields` names the tab and the
  fields" reads like a fields input. Its input is `tab` only; its question lists the fields. Brief 28 states this
  correctly.
- **N4** (28a "Tests"). There is no line for the new marks: a muted tab that plays shows `muted` and not `sound`.
- **N5** (28a item 5). `chrome_do`'s `discard_unsaved` is "for a taken tab's first-input reload". On main and in
  28b item 5 it also covers a popup's first-input reload.
- **N6** (28a `chrome_close`). One flag now covers up to 20 tabs, and `requireDiscard` skips the check whenever
  the flag is set. So a repeated call can discard a Claude tab that was never reported. Main closes one tab per
  call. Consider letting the flag cover only tabs that the previous result kept with `reload_required`.
- **N7** (28 "Latency"). "A median or a p95 over its ceiling fails" is a fair summary. `latency-check.py` also
  scales the ceilings by the paired runner slowdown and checks against the frozen reference.
- **N8** (28b item 8). "About 500" for inputs whose itemised sum is about 400. The old text called the 100 a
  margin; now it isn't explained.
- **N9** (the new rule). `requireDiscard` returns at once when the flag is set, so on a taken tab the check has to
  run anyway to know whose typing it is: say so. The refusal should also tell Claude to repeat its `chrome_go`
  after an approved `chrome_take_reload`, since the reload alone doesn't navigate.
- **N10** (28b item 8, or the descriptions). Main's rule has Claude ask him in the chat before setting the flag.
  On a taken tab with his typing that OK is wasted, because the call is refused and he is asked again in the
  prompt. One clause in `chrome_go`'s and `chrome_do`'s descriptions would avoid the double question.

## What I'd need to call it READY

- B1: a decision on uninspected frames on a taken tab, written into item 4, the test line and the header.
- B2: `chrome_take_reload` takes a prepared approval (or the brief says another way the question reaches the
  prompt), with what prepares it on a tab already taken, and its size.
- S1 to S10 are small text changes. S1 and S2 are worth doing before 28a starts.
