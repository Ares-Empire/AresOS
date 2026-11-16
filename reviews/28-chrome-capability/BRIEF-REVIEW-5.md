Fresh design and security reviewer (Claude agent, Opus 5.5), 2026-11-16, on `briefs/28-chrome-capability` at
`8a59a373`; range `42aa0370..8a59a373` (briefs 28, 28a, 28b, `docs/design/CONTROL.md` section 6, `ALIGNMENT.md`),
read as a whole, with main's code on this branch; topic 6 also on `origin/pkg/28-chrome` at `9d8d277f`.

# Brief review 5: the Chrome capability briefs

Nothing was run in CI. Local checks: plain Python on main's definitions (sizes below) and reading the extension
code. Security findings are sorted **fix** or **known limit** as `docs/REVIEW.md` defines them.

## Blocking

### B1. A taken tab: work of his that brief 20's check can't see is lost with no question (topic 1) — **fix**

*Where:* `briefs/28b-chrome-his-tabs.md` item 4, "On a tab already taken, the approval comes from the refusal…"
(lines 313-319) and the B1 rule after it; section 6, "In a tab he gave Claude, a flag doesn't discard his typing
either".

*What's wrong:* on a taken tab the check before `chrome_go` and before a `chrome_do` guarded reload is brief 20's
(`requireDiscard` with `reloadState`). It walks the fields present now. It doesn't see:
- a wizard step he finished in the taken tab: he typed, pressed Next, the fields are gone, the data is in the
  script's memory;
- a canvas he drew on, or a file he dropped onto the page's own drop zone.

With nothing found, `requireDiscard` returns and `chrome_go` navigates: no `reload_required`, no flag, no question.
The header's charge ("no path discards his typing in a tab Claude has taken without his answer in Claude Code's
prompt"), section 6's "unknown is not clean", and 28b's Known limits rule ("work of his lost … is never a limit")
all say this can't stand. Item 4 drops item 4a's used mark here for a good reason: Claude's own input sets the
browser's activation. But the guard has records that Claude's input can't set:
- `guard.js` already marks the document itself on every trusted `input` event outside Claude's dispatch
  (`noteTyping(ownDocument, …)`, line 144). `reloadState` reads `gotInput(document)` only for design mode;
- `ownerInput` already tells his trusted pointer and key events from Claude's (`inFlight`);
- 28b's drop-and-paste record, if it is built, is his alone.

*Fix:*
- On a taken tab, the check also counts "he has used this page since Claude took it": the document's owner typing
  mark, a sticky mark for his trusted pointer or key input outside Claude's dispatch, and the drop-and-paste
  record. Each makes `reload_required` with "you have used this page since Claude took it". The flag is refused,
  and the refusal carries the `chrome_take_reload` approval, as for his typing.
- The click mark needs one line in `guard.js`'s isolated part. 28b's paths allow that part "for a passive mode
  only", so widen them by that line.
- Test: in a taken tab he finishes a wizard step with real keys (its fields are removed), and separately draws on
  a canvas; `chrome_go` with and without the flag is refused with an approval, and the page is unchanged.

*Also decide:* "An input after which the page navigates on its own … isn't checked" (line 337). A link click by
Claude in a taken tab where he typed discards his typing, and the tool knows beforehand that a plain `href` link
navigates. Either run the same check before such a click, or write the exception, with its reason (Chrome's
"Leave site?" is his guard), into the header's charge and the Known limits rule. As written, they contradict it.

### B2. Exception 4 hides the option a `select` step will choose (topic 2) — **fix**

*Where:* `briefs/28a-chrome-act.md` item 3a (lines 185-198: "the target when it is a list"), its tests ("a list
that is the target"); section 6, "How an asking action runs" (line 1068: "the options he didn't choose aren't sent
and aren't listed").

*What's wrong:* `payload` builds the binding from the facts before the input, and the description carries
`input: {verb: 'select', value: …}`. With exception 4, the target list shows `chosen`, which is the option selected
**now**, and the option the step will select appears only as its `value`, often an opaque id. Its label is nowhere
in the approval. On `main` he could find that value among the listed options.

So for an asking `select` the approval shows the old option as "chosen" and hides the new one's label. "The
options he didn't choose aren't sent" is false here: the step sends exactly an option he hasn't chosen yet. Select
steps do ask:
- in conservative mode every activation asks (`classify`), and that mode is on after every Chrome update until
  the version is qualified;
- outside it, any select in a form whose action or label carries a send, pay or delete word asks.

The payload and the comparisons are fine; what he sees is not.

*Fix:*
- For a `select` input, the target also shows `choosing`: every option of the binding whose value equals the
  input's value, exactly as the binding holds it. The same goes for `free`'s committed description.
- Tests: an asking select (conservative mode) on a three-option list and on F4's 200-option list. The description
  shows `choosing` with label and value, `chosen` is the old option, and the size stays within the F4 bound.
- Section 6's sentence and its known limit gain the exception.

The rest of exception 4 holds: what a form sends is its chosen options, every option stays bound and compared, and
F4's ≤9,000 bytes is a test ceiling below the base's 16,384 (`ASK_LIMIT` counts the canonical approval:
question, id and description). The ~7,300 estimate checks out: 21,700 − 14,558 + 265.

## Should fix

### S1. The take checks before it attaches, and reloads after (topic 1) — **fix**

*Where:* 28b item 4 points 2 and 3 (line 286) against item 4a ("as the last thing before the reload").

*What's wrong:* point 2 checks in place, and point 3 then attaches, marks and reloads. The attach, the breakpoint
and the group take a few hundred milliseconds, and his typing in that window is lost. The test holds the command
before its check, so it can't see this.

*Fix:* check in place first, so an unclean tab changes nothing. Then attach and mark, and check again as the last
step before `Page.reload`. If the second check fails, undo the attach and the mark (item 4b's restore) and answer
`reload_required` with an approval. `chrome_take_reload`'s re-check on an untaken tab runs at the same point. The
test holds the command after the first check.

### S2. The re-check's new approval must respect the four cases (topic 1)

*Where:* 28b item 4, line 312: "answers `reload_required` again, with the new findings and a new approval".

*What's wrong:* the sentence is unconditional. If a dialog opened, a load started or a frame stopped answering
since the question, there must be no approval.

*Fix:* add "except in the four cases below". Test: a frame that stops answering while the approval waits gives a
refusal with no approval.

### S3. Item 5a's "pause still live": the fallback is not a known limit under the bar (topic 5) — **fix**

*Where:* 28a item 5a, line 480: "If no reliable check exists, keep it as a known limit with that harm".

*What's wrong:* the harm is wider than "skips the guarded reload". An install from the pause writes
`document-start.v1` (`background.js` install path), so the reader treats the document as watched from its start.
Two things then rest on a pause that may be stale:
- the password-history rule: a field made plain before the install would be read;
- the main-world wrappers: a page that kept a native `submit` before they arrived escapes the hold.

`docs/REVIEW.md` makes a password read or an action without its question a "fix", and 28b says neither is ever a
limit. With 28b, a take always reloads, which covers his tabs, but Claude's own tabs stay exposed.

*Fix:* fail closed instead. A document whose install pause can't be shown current counts as `late`, so it gets one
guarded reload. P1's own analysis says only a pause from before a re-arm can be stale, so the cost is one extra
reload after the rare duplicate-breakpoint event. Name the whole harm wherever the limit is discussed.

### S4. Item 5a has no place in 28a's frozen lists (topic 5)

*Where:* 28a "What changes in `background.js`, and nothing else" (line 736: not admission, the debugger methods or
the rest of `input`), "Paths" (`background.js` "only as items 5, 6 and 8 say"), and the security review's list of
places newer than security re-check 2.

*What's wrong:*
- 5a says "where admission is reworked here", but 28a doesn't rework admission; 28b does (items 4 and 4b).
- P3 needs the click's result to carry the popup's admission outcome. PR #77's builder said that threads through
  `dispatch` and the click path.
- The popup's address "follows item 3's rules", which means the public form for a result. For a popup refused
  because it is a fixed-list or never-list page, that shows its path and query, more than `chrome_tabs` shows.
- "Claude can then `take_tab` it" names brief 20's tool.

*Fix:*
- Add both points to the `background.js` list and the paths, or move the pause check to 28b, whose take rewrites
  admission.
- List both points for the security review.
- Give the popup's address in the short form, with the `no` mark where `chrome_tabs` would show it.
- Say `chrome_take`.

### S5. The never-list gate: 28a is silent, and 28b's list misses two of his-tab paths (topic 3)

*Where:* 28a, the whole brief; 28b item 9 (line 587).

*What's wrong:*
- 18c-b's sweep (`test_excluded_sites_placeholder.py`, PR #73, not yet on `main`) fails on every tool it doesn't
  name, "until someone decides". 28a adds and renames 19 tools, plus the test-only `chrome_old_*` names, and says
  nothing about it. Whichever of 28a and 18c-b merges second meets a red test, with no written rule against
  adding new tools to the named exceptions.
- 28b names the take, the take-reload and the in-place reads, but not `chrome_close` of his tab or `chrome_open`
  with `tab`. The sweep calls each tool once with one set of arguments, so a his-tab branch is only covered if a
  case calls it.

The gate itself sits in the service, before any bridge call, so every path that reaches the adapter does hit it.
I found no path around it.

*Fix:*
- 28a: every tool of the new list, the test-only ones included, joins the sweep; the exceptions stay 18c-b's.
- 28b: one sweep case for each branch that names his tab: `chrome_read`, `chrome_prepare_read_typed_fields`,
  `chrome_take`, `chrome_close`, `chrome_open` with `tab`, and `chrome_take_reload` with a stored operation.
- Section 6's group 17 gets the placeholder case.

### S6. The empty list opens the gate with his dashboard open (topic 3, for the lead) — **fix**

*Where:* section 6, line 500 ("an empty one if he has no host to add"), and brief 18c-b's "For his guide" (`main`),
which offers `{"format":1,"hosts":[]}` "with no site to exclude".

*What's wrong:* section 6 says his dashboard can approve Claude's actions and must be on the list first. The guide
he will follow says the empty list is fine. The gate checks only that a list exists, so that one guide line is the
whole protection.

*Fix:* the live-sitting guide and section 6 say that his dashboard's host is always on the list, and that the empty
list is for tests only.

### S7. The late shadow-root rule: keep it, but "late" can be narrowed soundly (topic 6)

*Where:* brief 28 item 1, "History, inside a watched document: a shadow root the reader met late";
`reviews/28-chrome-read/PROGRESS.md` on `pkg/28-chrome`, "Step 7", PLAN-GAP 1.

*Keeping it is right.* The builder's reading is correct. The light-DOM rule rests on the password tracker
watching a field's whole masking history, and `typedBy` is a different, weaker record: it misses autofill and
script-set text, and its view of a root it doesn't watch is retargeted to the host. Option (b) would trade
evidence for a guess.

*The narrower rule.* The premise "causes no change an observer sees" is true for the reader's `MutationObserver`,
but not for the guard:
- in a watched document, `page.js` wraps `attachShadow` (line 124) and reports every new root (`watch_root`)
  through the private relay, synchronously, while the root is still empty;
- the isolated guard already `watch()`es those roots, and `watchReceiver` covers a fresh realm's root once content
  goes in through a wrapped method.

If the reader met a root at that report (`meet`, `observe`, `remember` on the empty root), the tracker would see
its fields' whole masking history: the same basis as the light DOM, with no typing involved. Only roots met any
other way would keep the late rule: roots built and filled entirely through a fresh realm's natives, roots attached
while no guard was linked (a release), and declarative roots. Brief 20's own `review-shadow` fixtures (a root
filled in the same task as `attachShadow`) would then have passed unchanged, which is the point. Today every
prefilled field in a component upgraded after load is unread, and its form can't be sent.

*Fix:* not for package 28's merge. Keep its known-limit line. As a follow-up (28a, or a small package): the hook
(one line in `guard.js`'s isolated part, and `reader.js`) and three tests:
- a component upgraded after load with a prefilled field is read, and its form asks and sends;
- a root built through a fresh realm and filled before the meeting stays unread;
- a field masked and then unmasked inside a root met at attachment stays protected.

## Notes

- **N1** (28b item 4). Say what `chrome_take_reload` returns: the reloaded page's outline, as `chrome_take` does.
  Give it `chrome_take`'s 18-second deadline (28a item 5, "Time"); the base's client waits 30 seconds for a change.
- **N2** (28b item 4). For a tab not yet taken, the question should also say that Claude takes the tab (the Claude
  label and its control), not only that it reloads.
- **N3** (28b item 8). Sizes measured with main's helpers:
  - `request` is 60 characters a tool and `seen` 56; `chrome_take_reload`'s name plus `APPROVAL` is 279.
  - Total 747, against the 750 cap, before the removed `reload` (−27) and any `required` entries (+10 each).
  - Say whether `request` and `seen` are required on `chrome_take`.
- **N4** (section 6, "Actions"). The table has no row for `chrome_take_reload` (change; asks, as a delete).
- **N5** (topic 4). The lead's decision of `434bb567` is right: rule 4.1, and it fails closed. One fix to the
  advice: "Shorten the text you filled" (28a, item 3a) sends Claude to shorten text in vain when a hidden value is
  what is too large. Let the advice name that case.
- **N6** (28b item 4a and the B1 rule). Frames that hold nothing but take no reader count as uninspected: an
  embedded PDF viewer, or another extension's inline frame. A tab with one is never known clean, and once one
  appears in a taken tab, `chrome_go` stops with no approval. Measure it in CI (a PDF fixture, a test extension's
  frame) and add a known limit: he acts himself, or Claude uses a copy.
- **N7** (28b item 4a, line 420). Say that "a frame the record doesn't cover" makes the tab *used* (an approval is
  offered), unlike a frame that doesn't answer. Otherwise every tab older than an extension update could never be
  taken.
- **N8** (28b item 4). `chrome_upload` in 28a has no `discard_unsaved`. Say what its first-input refusal on a taken
  tab carries (the approval, or advice to use `chrome_go` with `to: reload`).

NOT READY
