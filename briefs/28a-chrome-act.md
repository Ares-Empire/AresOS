# 28a: Chrome acting: the new tool list, short references, navigation and batched steps

**Goal:** Claude gets the efficient Chrome tool. Brief 28 built the new read behind an internal action. This
package makes it what Claude is offered and builds the rest around it, with the same questions before every send.
An action names its element by the short reference a read gave, and by nothing else. One call opens a page and
returns its outline. One call runs several steps and says what changed. The tool list a session loads shrinks from
29 tools to 18. "Better" is written as budgets, and a CI test group measures them against brief 20's tools on the
same fixture pages.

The owner's words (2026-11-11): "I don't just wanna rebuild Claude in Chrome. I wanna make a better tool for AresOS
that's more efficient with readings, navigation, free tab navigation etc."

**Three packages, in this order.** The lead split the first design of brief 28 on 2026-11-13, as package re-check 2
advised (`reviews/28-chrome-capability/` holds the design's reviews):

1. **28** (`briefs/28-chrome-read.md`): the baseline, the shared rules for fields and addresses, and the new read.
2. **28a, this brief:** the new tool list and everything that acts. It waits for 28, and so for PR #27.
3. **28b** (`briefs/28b-chrome-his-tabs.md`): Claude looks at his open tabs in place. It waits for this one.

Each package leaves `main` working and is reviewed by itself. **None of the three reaches the owner's laptop before
all three are merged:** this package still keeps brief 20's check before a taken tab's reload, which 28b replaces.
The owner has answered every question of all three ("Already decided" at the end).

**Building starts only after brief 28 is merged** (and with it PR #27). Branch from `main` after that merge. Paths
and line numbers in this brief come from PR #27 at `8b7e799c`; read them again on merged `main`.

**Builder (recommended, the lead confirms at launch):** a Claude agent on Fable 5.2. The work changes a dense,
security-reviewed code base, replaces the tool list and the way every action names its element, and must not be cut
off halfway; Codex is away from about 2026-11-14 to 11-17 and ends on 11-21. **Review** (`docs/REVIEW.md`, "Tools
for Claude"): two fresh reviewers at once, a package review and a security review, Codex while it is available,
otherwise Claude. This is the package that reaches into the asking path itself, in four narrow places: the form of
addresses in a question and in a stage text (item 3), the reveal before an input and the time check before its
dispatch (item 5), and the asking read's place in the new list (item 6). So its security review is high-stakes:
Fable 5.2, or Codex's frontier model while it is available. The package review runs on Opus or Codex's workhorse.

## Background (read first)

- `docs/design/CONTROL.md` **section 6 is this package's specification**: "Reading a page" (references and
  addresses), "Going to pages and acting", "Actions", "Efficiency, as a tested property", "Known limits" and test
  groups 14 to 16 under "Tests". Sections 3 and 4 are the rules every action follows. Where this brief and section
  6 differ, tell the lead in the report (PLAN-GAP); don't pick one silently.
- `briefs/28-chrome-read.md` and `reviews/28-chrome-read/REPORT.md`: the read you build on, its outline format,
  its reference table, its field rules, its deadline mechanism, the fixtures and the committed baseline. This
  brief doesn't repeat them. "Why brief 20's tools cost so much" is there too.
- `docs/control/PLAN.md`: decisions 24 and 25 and the entries of 2026-11-11 (the owner's bar and his words).
- `docs/REVIEW.md`, "Tools for Claude": the bar the reviewers use.
- `reviews/28-chrome-capability/BRIEF-SECURITY-2.md` and `BRIEF-REVIEW-2.md`: the design's last reviews. Where
  this brief names "security re-check 2" or "package re-check 2", that is the file.
- `reviews/20-chrome/REPORT.md`, `reviews/20-chrome/KNOWN-LIMITS.md` and `reviews/20-chrome/TOOL-DESCRIPTIONS.md`.
- `reviews/18d-base-slim/REPORT.md`: how shared rules go once into the server's MCP instructions, and how the
  description sizes are measured.
- The code, before you change it:
  - `control/aresos_control/chrome/adapter.py`: `read`, `facts`, `payload`, `prepare`, `question`, `execute`,
    `free`, `steps` and `call`; `control/aresos_control/engine.py`: `stage`, to read only;
  - `control/aresos_control/chrome/definitions.py`, and the view module brief 28 added;
  - `control/aresos_control/chrome/bridge.py` as brief 28 left it;
  - `control/chrome/extension/reader.js`: `snapshot`, `targetFacts`, `safeValue`, `password`, `observe`;
  - `control/chrome/extension/background.js`: `facts`, `collection`, `dispatch`, `input`, `pointer`,
    `collectSteps`;
  - `control/aresos_control/proxy.py`: the Chrome upload branch;
  - `control/chrome/ci/browser.mjs` (the helpers `rpc`, `call`, `read`, `target`, `nav`) and `ci/verdicts.mjs`.

## What to build

### 1. The new read becomes `chrome_read`

Brief 28 built the read and offered it only as the internal action `chrome_outline`. Here it becomes the public
`chrome_read`, with brief 28's input, result, outline format, paging and deadline unchanged. Three things are new
around it:

- a tab that isn't in Claude's group answers `take_first` (item 6);
- every reference it issues can now be acted on (item 2);
- the instructions tell Claude how to read an outline (item 7).

The internal action goes when the list is switched (item 8).

### 2. Acting by reference: the fingerprint (service and reader)

Brief 28 issues a reference, five letters and a number such as `kqtvm5`, and keeps for it the connection, the tab,
the frame, the document, the reader instance, the element and the line it last showed Claude. This package lets
an action name its element by that reference.

- **Every action resolves its reference** through brief 28's table to brief 20's internal reference (session, tab,
  frame, document, element; no `view`) and then runs brief 20's path unchanged. For that the reader returns its
  instance id with `facts` too (brief 28 added it to `outline`). An action is refused with `stale_reference` when:
  - the reference isn't in the table: invented, dropped, or issued by another run of the service;
  - it was issued for another tab than the one the call names;
  - it was issued under another connection (Chrome or the extension restarted or reconnected; the service empties
    the table then and the counter goes on);
  - the document, the reader instance or the element is gone or is another one;
  - **the element's fingerprint differs** from the one Claude last saw.
  The refusal carries the element's present line, and that counts as shown, so a repeated call can pass. The
  line sits in `untrusted_content`, rendered and escaped like any outline line: in `untrusted_content.now` for
  `chrome_do`. `chrome_open` and `chrome_upload` give the message alone, and Claude reads the element again. The
  message is the tool's own fixed sentence and never carries page text (brief 28). A fold's reference names a
  run of children, not an element, so no step accepts it.
- **The fingerprint.** Brief 20 made the caller send back everything the element had shown (`expected`) and
  compared all of it, its place on the screen included. The service now keeps that comparison itself, per
  reference, as a digest of what the element means:
  - it covers what brief 20's `expected` covered, without the `box`, without `onscreen`, and without the states
    `disabled`, `required` and `invalid`: the role, the name, the label and the title; a link's destination,
    resolved and in full; whether the element submits a form, is editable or is a search field; the page dialog
    it sits in; whether it is ticked, selected or expanded; a list's options (label, value, chosen); and the whole
    value (for a password-kind or unread field only that it is one);
  - **one function of the reader computes it,** and three commands return its short digest: `outline` for every
    node (one more field of brief 28's node), `facts` for the target, and `observe` (the reader's report after
    an input) for the element acted on. The read and the check before an action can't drift apart that way, and
    the service only stores and compares digests. The function reads nothing the password rule keeps out;
  - it is taken from the element, not from the line. A name or value the outline showed cut, and a link's address
    that the line doesn't show at all, are compared whole;
  - it moves only when a result shows Claude that element again (a read, a `find` hit, a `~` line of a change
    report, the present line of a refusal), or when a step of Claude's own has acted on that element (item 5).
  Left out on purpose: where the element sits, and three states that don't change what it means. A control that
  became enabled is still the control Claude meant, and a disabled one does nothing when clicked.
- **What is no longer checked, said plainly:** anything outside the element. Brief 20 refused an action when
  anything on the page had changed since the read. Now a free step runs although the text around a button or a
  neighbouring field changed. An asking step still shows and binds the form, the draft and the affected item. The
  change report covers the call itself, not the time between Claude's last read and the call.
- This replaces two things in `adapter.py`: the comparison of the caller's `expected` in `payload` (now against
  the stored fingerprint), and the comparison of `view` in `facts` (gone). The extension's own checks stay
  (session, tab, document, element, the hit test before a click), and so does everything that follows in
  `payload`.
- No tool input carries `reference`, `expected` or `view` objects any more.

### 3. Addresses on every surface (service)

Brief 28 built the one function that writes an address, `public_address`, with its two forms, and used it in the
new read. The owner decided the rule on 2026-11-13 (board #213, "Show link addresses"): on a page Claude reads it
sees link addresses with their query, and only what looks like a sign-in is hidden. Here the function goes in
front of everything else that leaves the service. No other code writes an address.

**The short form** (the site and the path, with `?…` and `#…` for a query and a fragment) is used in two kinds
of place.

- **Lists,** where Claude is shown pages his request may have nothing to do with: the list of `chrome_tabs`; the
  entries of `chrome_library` (bookmarks, history, and where a download came from); the `closed` and `kept` lists
  of `chrome_close`; and with brief 28b the popup lines that name one of his tabs.
- **Records,** because a record needs no query value (owner, 2026-11-13, board #213): everything the service writes
  to its audit log (`aresos log`), and the texts that the log holds, which are an operation's stage texts and a
  notice's text. Brief 20 writes one stage text to the operation and to the log (`Engine.stage`), so it is written
  once, in the short form. The stages that `chrome_submit` and `chrome_operation_status` return therefore show
  an address without its query; Claude reads the tab when it needs more.

**The public form is used everywhere else** that leaves the service toward Claude or toward his question:

- reads: the `url` of a page, a link's and a form's target, detail reads, `find`, change reports;
- the results and error messages of every other tool;
- a prepared operation's question and description, also as `chrome_operation_status` returns them.

Full addresses stay inside the service and the extension: in the reference table, in an operation's payload
(`binding`, `reference`) and in the commands to the extension. **Nothing about comparing changes:** the extension
still compares the full destination right before an approved input. To build this (package re-check 2, N9:
PR #27's adapter has no `stage` method, and its stage texts are made in `execute`):

- **`prepare` and `question`** take the description and the question from a copy in which each address went
  through `public_address`, in the public form: `url`, `frame_url`, `effective_url`, `form.action`,
  `target.href`, `editable[].url` and a dialog's `frame_url`.
- **`free`** does the same for the description it commits and for what it returns, and writes its `page` stage
  with addresses in the short form.
- **`execute`** serialises the extension's raw reply into the stage callback (`stage('confirmation', …)` and
  `stage('page', …)`), and `Engine.stage` stores that text on the operation and writes it to the audit log. So
  `execute` builds those two texts from a copy of the reply in which each address (the `url` the extension
  reports after an input, a frame's and a dialog's address) went through `public_address` in the short form,
  before it serialises them. Those two lines are the one change inside `execute`. `Engine.stage` isn't changed.
- **`steps`** writes its page-step warning (`chrome_page_step`) to the log with addresses in the short form.

The payload isn't touched anywhere, and no comparison reads a projected text. Show these lines in the report.

Claude uses an address it can't see whole by reference: a link's `ref`, his tab's number, a library entry's `ref`
(items 4 and 6). So a `…` never blocks a navigation.

### 4. `chrome_open` and `chrome_go` (effect change)

**`chrome_open`** input: exactly one of `url`; `tab` (open the address that tab shows; with `seen` when the tab is
his, item 6); `ref` (open the address behind a link's or a library entry's reference; `tab` may accompany a link's
reference and must then be its tab). Also `until`, `timeout_ms` (0 to 15,000, default 8,000) and `max` (default
4,000).

**`chrome_go`** input: `tab`, and exactly one of `url` or `to` (`back`, `forward`, `reload`); `until`, `timeout_ms`,
`max` as above.

Result of both:

```
{"tab": 431, "loaded": true, "until_met": true, "characters": 2210, "total": 2210, "cursor": null,
 "untrusted_content": {"url": "…", "title": "…", "scroll": "0/1800", "outline": "…", "dialog": null},
 "version_notice": null}
```

- Both use brief 20's `open` and `navigate` commands and rules unchanged (web addresses only, the fixed list, the
  refusal of form-loaded history entries, the guarded reload). Then the service waits until the page is loaded as
  defined below (a new document, or a new address in the same document; ready; quiet), or until `until` is
  met, or until the timeout. `loaded` and `until_met` say which.
- `chrome_open` with `tab` or `ref`: the service takes the full address from its own record (the list Claude named
  with `seen`, the tab's present address for a Claude tab, or the reference table). Claude only ever saw the
  public form. The rules of "Where Claude may go" apply to it.
- The outline is the same as `chrome_read`'s, with references ready for the next call.

**"Loaded", defined once** (for `chrome_open`, `chrome_go`, `chrome_take` and a step that navigates), on brief 28's
state token and its "quiet" (the token unchanged for 150 ms):

- **Loaded:** the navigation has arrived, and the page is `ready` and quiet. **Arrived** means one of two things.
  The tab shows a new top document (another Chrome document id than before the call). Or, for a navigation inside
  the same document (a fragment, or a history entry of a single-page site), the tab's address has changed while
  the document stayed. A reload, and a `url` equal to the present address, need a new document.
- **`until` together with a navigation** replaces "ready and quiet", never "arrived". The call returns as soon as
  the navigation has arrived and the text condition holds, which is what helps on pages that never go quiet.
  `until_met` and `loaded` are reported separately; `loaded` says whether the page was also ready and quiet then.
- At the timeout the call returns what is there, with `loaded: false` or `until_met: false`.

### 5. `chrome_do` (effect change)

Input: `tab`; `steps`, 1 to 20 objects, each with `do` and what that step needs; `max` (500 to 8,000, default 2,000:
the bound of the change report).

| `do` | Needs | Is brief 20's |
|---|---|---|
| `click` | `ref` | `chrome_click` |
| `fill` | `ref`, `text` (up to 20,000 characters; line breaks go in as text) | `chrome_fill` |
| `select` | `ref`, `value` (an option's value, or its label) | `chrome_select` |
| `check` | `ref`, `checked` | `chrome_check` |
| `press` | `ref`, `key` | `chrome_press` |
| `scroll` | `ref`, `y` (pixels, negative is up) | `chrome_scroll` |
| `dialog` | `accept`, `text` (optional, for a prompt) | `chrome_dialog` |
| `wait` | `until`, `timeout_ms` (0 to 8,000) | `chrome_wait` |

What each step is, exactly:

- **`click`, `fill`, `check`, `press`, `scroll`:** brief 20's verb through `payload`, with the reference resolved by
  item 2.
- **On screen first.** Brief 20's click needs its target on screen: `pointer` in `background.js` refuses when the
  element's centre isn't hit, and brief 20's reads gave Claude the boxes to scroll by. The outline has no boxes.
  So `input` gets one addition. After the frames are armed and before its last facts read, a target that isn't on
  screen is scrolled into view by the reader (a new content command, `reveal`: to the centre, at once). This
  happens inside the armed hold, so what the page does on that scroll is held like after any input, and the hit
  test that follows is brief 20's. It applies to an approved input too, because a prepared click may wait off
  screen. Nothing else in `input` changes.
- **`select`:** the service matches `value` against the options in the fresh facts. First as an option's value,
  exactly. If no option has that value, as an option's label, exactly after trimming and joining runs of spaces.
  No match, a disabled option, or a label that several options carry: the step is `refused` ("no such option",
  "that option is disabled", "several options carry this label; pass the value"). The extension always gets brief
  20's exact value.
- **`scroll`:** `ref` is required. The element is brought on screen and the wheel then turns by `y` pixels at it,
  as brief 20 scrolls. To scroll the page, Claude names any element of it. There is no scroll without an element:
  brief 20's dispatcher hit-tests its target before every input, and that stays.
- **`wait`:** not an input, and not through `payload`. The service waits as brief 28 defines, for `until`, at most
  `timeout_ms`. Its outcome is `done` when the condition was met and `timeout` when not; a `timeout` stops the
  list.
- **`dialog`:** brief 20's `dialog` branch of `call` (its own facts, classification and payload), not `payload`.
  What brief 20's caller sent as `expected` is now the dialog the service last showed Claude for that tab (its
  kind, its text, the frame's site); another dialog is `stale`.

Result:

```
{"tab": 431,
 "steps": [{"do": "fill", "ref": "kqtvm8", "outcome": "done", "operation_id": "…"},
           {"do": "click", "ref": "kqtvm10", "outcome": "prepared"}],
 "not_run": 0, "deadline": false,
 "prepared": [{"approval": {"question": "…", "operation_id": "…", "description": {}}, "state": "reserved"}],
 "unknown": [],
 "loaded": null,
 "untrusted_content": {"url": "…", "title": "…", "changed": "…", "more_changes": 0, "outline": null,
                       "dialog": null, "clipboard": null, "stopped": [], "now": null},
 "version_notice": null}
```

**Each entry of `steps`** holds `do`, the step's `ref` if it has one, an `outcome`, and where they apply
`operation_id`, `code` and `message` (the tool's own words, never page text):

| `outcome` | Meaning | Was anything dispatched? |
|---|---|---|
| `done` | the input ran once, or the wait was met | yes (a wait: no) |
| `unchanged` | the element was already as asked, for example a box already ticked | no |
| `prepared` | the step asks; its approval is in `prepared` | no |
| `stale` | item 2 refused the reference; the element's present line is in `untrusted_content.now` | no |
| `refused` | a rule refused it: a read-only site, a password field, a form that holds a field the tool may not read, an option that doesn't exist, an address that isn't allowed; `code` and `message` say which | no |
| `timeout` | a `wait` wasn't met | no |
| `unknown` | it may have run; its `operation_id` is also in `unknown` | maybe |

- Every step that was dispatched, and every `unknown` one, carries the `operation_id` of brief 20's committed
  operation, for `chrome_operation_status`.
- **`unknown` is brief 20's uncertainty, one to one:** an activation that may have happened
  (`activation_unknown`), a dialog that opened while the page was handling the input, a handler whose end couldn't
  be confirmed (`uncertain_finish`), a cleanup still pending, and a connection cut after the input was sent. It is
  never retried.
- **A list never ends in a bare error once a step was dispatched.** The call returns its normal result, with the
  entries so far and the failing step's entry. A bare error comes only when nothing ran: invalid input, a tab
  that isn't Claude's (`take_first`), Chrome not connected, a core group that failed qualification.
- `not_run` counts the steps after the last entry. `deadline` says whether the time ran out ("Time" below).

How it runs:

1. **Check first.** Resolve every reference and apply item 2's rule before the first step. If one fails, nothing has
   run: the result holds one entry, for that step, and `not_run` counts all the others.
2. **Run in order, and check each step again right before it runs.** Each step goes through brief 20's path for
   that verb: `payload` (fresh facts, classification, binding), then `free` (dispatch once) or `engine.reserve`
   (prepare). Every free step is still committed as its own operation before its input, as today. On the fresh
   facts `payload` has just read, item 2's rule is applied again **in full, the value included**: what the element
   shows must be what Claude last saw.
   - One thing only moves "last saw" inside a list: after a step of this list has itself acted on an element (a
     fill, a select, a check, a key in a field), the service takes that element's fingerprint from the step's own
     reply (`observe`). So `fill` and then Enter on the same field passes.
   - A step on any other element whose name, value, tick or options changed since Claude saw it ends `stale`,
     whatever changed it: the page's reaction to an earlier step, a draft the page loaded, his own typing. Nothing
     is dispatched for that step, the list stops, and the result carries the element's present line. A list never
     overwrites text Claude hasn't seen.
3. **Look at the tab before the next step.** Before every step after the first, and again after every `wait`, the
   service asks `page_state`. The list stops before the next step when:
   - the top document isn't the one the list started on;
   - a native dialog is open;
   - a page step is queued. It then goes through brief 20's `steps`, exactly as a read handles it: a held
     submission is prepared and comes back in `prepared`, a stopped activation in `stopped`, one that may have
     happened in `unknown`.
   Brief 20's `held_step` event only records what the extension saw (`event` and `observe_step` in `adapter.py`);
   it stops nothing by itself. A page step can arrive after the reply to the step that caused it, so the loop has
   to ask.
4. **Stop** after the first step whose outcome isn't `done` or `unchanged`, and also after a step that:
   - was prepared (`prepared`): the result carries the base's prepared result, to pass unchanged to `chrome_submit`;
   - made the page start a submission or activation that the page script stopped (`stopped`; a held submission is in
     `prepared`, a stopped activation is described in `untrusted_content.stopped`);
   - opened a native dialog, or loaded a new top document;
   - ended `unknown` (its operation id is in `unknown`), `stale` or `refused`.
   `not_run` counts the steps after it. Nothing is retried, and no step runs twice, also when Chrome, the host or
   the service stops in the middle.
5. **Report.** Take the outline nodes before the first step and again after the last one that ran, once the page has
   gone quiet (at most 1,500 ms), or, after a navigation, once it is loaded (item 4; within the call's deadline,
   see "Time" below).
   `changed` lists what differs by element: a line starting `+ ` for a new element, `~ ` for one whose line changed
   (the new line), `- ` for one that is gone; new elements are shown under their new parent. At most `max`
   characters; `more_changes` counts the rest. After a new top document, `outline` holds the new page's outline
   (at most 4,000 characters) and `changed` is empty.
6. The clipboard notice, the dialog facts, a taken tab's first-input reload and the version notice come back as
   brief 20 returns them. For the reload: a clean tab reloads, and the result is `stale` for that step with the new
   outline attached; a tab with unsaved typing or playing media answers `reload_required` and names `chrome_take`
   with `reload: true` (item 6).

`dialog`: the service compares the open dialog with the one it last showed Claude for that tab, as it compares
references; brief 20's rules for the three kinds of dialog are unchanged.

**Time: every call ends before its caller gives up.** The base's client waits 10 seconds for a read and 30 for a
change (`READ_TIMEOUT` and `CHANGE_TIMEOUT` in `protocol.py`), and the CI harness waits 20. A caller that times out
doesn't know what ran, while the service would go on. So every tool has one deadline, measured in the service from
the start of the call, and no timeout is raised. Brief 28 built the read's 8 seconds and the way a deadline
reaches the extension: each command carries the time it has left, the extension starts no command whose time is up
and bounds its waits by it, the bridge stops waiting shortly after, and a late reply is dropped by its id. This
package puts the tools that act on the same mechanism:

- **`chrome_open`, `chrome_go`, `chrome_take`: 18 seconds in all,** with `timeout_ms` at most 15,000. The outline
  read that ends the call has to answer by second 17.
- **`chrome_do`: 18 seconds in all. No input is dispatched after second 12:** the service starts no step after
  it, and every input command carries the time left to it. A `wait` ends at second 12 at the latest; one that is
  cut off there has the outcome `timeout`. The reply to the last input is in by second 14. The report's waiting
  ends at second 16 at the latest, also for a new page, which is then returned as far as it has loaded
  (`loaded: false`), and its outline read has to answer by second 17. Steps that weren't dispatched are counted
  in `not_run`, and the result says `"deadline": true`. Their references stay good, so Claude sends them in the
  next call.
- **What an input adds to brief 28's mechanism, and nothing more** (package re-check 2, N2):
  - **A third check of the time, as the last thing before an input is dispatched,** after the arming, the reveal
    and the last comparison. Brief 28's two checks hold too: at the front of the queue, and in every wait for a
    frame, for the reader or for an input's setup. In each case the answer is `expired`, and **`expired` always
    means that nothing was dispatched**; a hold that was armed is released as after a refusal.
  - **After the dispatch nothing is cut short.** The hold, the collection of page steps and the cleanup run as
    in brief 20, a little over half a second with their own bounds. So the cut-off governs the dispatch, not the
    start of a step and not its end.
  - **The bridge waits for an input's reply until the command's time is up plus 2 seconds** (half a second for a
    read-only command, as in brief 28). Without a reply an input's outcome is `unknown`, as after a cut
    connection, and it is never retried.
  - A step whose input was answered `expired` counts in `not_run` like a step that never started, and its
    committed operation is closed as not dispatched.
  This adds one check in `input`, right before the dispatch. Nothing else: no cancelling of an input that is
  running, no second queue, no commands side by side, and no change to what `input` compares or in what order.
- **Why 20 steps and not 32:** brief 20 waits out its hold after every input (`collectSteps`, a little over half a
  second), and reads the page's facts before it. About a dozen input steps fit in one call.
- **A caller that goes away** changes nothing about this: the list ends at its deadline at the latest, each step
  that ran is its own committed operation (in the log and in `chrome_operation_status`), a prepared step stays
  prepared until it expires, and nothing runs later.

### 6. The smaller tools

- **`chrome_tabs`** (read; input: `cursor`). Every tab of every normal window in one result; a cursor only beyond
  200 tabs. The list is text in `untrusted_content.list`:

  ```
  window 3 (in front)
    412 his * "Uni portal: timetable" uni.example/timetable
    413 his pinned sound "Radio" radio.example/live
    group Claude
      431 claude "Docs" docs.example/guide/start
      408 taken "Shop: basket" shop.example/basket
  window 5
    440 his asleep "Car: listing 4411" cars.example/listing/4411
    441 his no "Claude" claude.ai/chat
  ```

  **Whose a tab is follows from who opened it, not from the group it sits in.** `claude`: Claude opened it with
  `chrome_open`, or a tab under Claude's control opened it. `his`: every other tab, also one he dragged into
  Claude's group. `taken`: one of his, under Claude's control for now. A taken tab stays his: closing it or
  reloading it follows the rules for his tabs.

  Per tab: Chrome's tab number; whose (`claude`, `his`, `taken`); the marks `*` (the tab showing in its window),
  `pinned`, `sound`, `asleep`, `popup`, `no` (never readable: the fixed list, his never-list, not a web page) and
  `look` (a read-only site); the title, quoted and cut at 80 characters; the address in the short form (item 3),
  cut at 60 characters.
- **The list binds what follows** (section 6, "Which tabs Claude works in"). The result of `chrome_tabs` carries
  `seen`, a reference (from brief 28's table) for this list. For every tab in it the service keeps what it showed
  Claude: the tab, its top document (Chrome's document id) and its full address; for a tab asleep, the address
  alone. It keeps the last 8 lists, in memory, and drops them all when the connection to Chrome changes.
  - A call that names **one of his tabs** by its number must pass the `seen` of the list Claude chose it from. In
    this package that is `chrome_take` and `chrome_open` with `tab`. Without it: `invalid_input`, "list the tabs
    and pass seen". With a `seen` the service doesn't know (dropped, or from before a restart): `stale_reference`,
    "list the tabs again".
  - `chrome_take`: the extension checks first, in the same command and before it attaches, moves, reads or changes
    anything, that the tab still shows that document at that address. If not: `stale_reference`, "this tab shows
    another page than the list did; list the tabs again". A tab that was asleep is checked by its address.
  - `chrome_open` with `tab` opens the address the list showed, taken from the service's record. It doesn't matter
    where the tab has gone since.
  - Claude's own tabs and a taken tab need no `seen`.
- **`chrome_show`** (change; input: `tab`). Makes the tab the one showing in its window and brings that window to
  the front. For him: to look, to sign in, to answer a dialog. Refused for nothing but an unknown tab.
- **`chrome_close`** (change; input: `tabs`, 1 to 20). Closes tabs that are `claude`. In this package every other tab is
  refused, **a taken tab included** ("this is the owner's tab; release it"). Brief 20's `chrome_close_tab` closes any
  tab in the group, a taken one too, without looking at what it holds: that ends here. The result lists `closed` and,
  with the reason, `kept`.
- **`chrome_take`** (change; input: `tab`, `seen`, `reload`) and **`chrome_release`** (change; input: `tab`). In
  this package they are brief 20's `take_tab` and `release_tab`, with one difference:
  the explicit reload has one home. `chrome_take` without `reload` takes the tab and keeps its page, and its result
  says whether a reload is still due and what it would lose. `chrome_take` with `reload: true` also does that
  reload now (brief 20's `prepare_control` with its explicit repeat) and returns the outline. No other tool has a
  `reload` input.
  - **`chrome_go` in a taken tab that hasn't had its reload** would replace his page without any check in brief
    20. Here it first goes through `prepare_control`, as a first input does: `reload_required` when brief 20's
    check finds typing, an editor or playing media, otherwise the guarded reload, and then the navigation.
  - **Brief 20's check before that reload is unchanged in this package.** It calls a tab clean when no field
    differs from its default, which many pages defeat by copying his typing into the default. Brief 28b replaces
    it (its item 4a). Say so in `KNOWN-LIMITS.md`; briefs 28 and 28a must not reach his laptop without 28b.
- **`chrome_library`** (read; input: `kind`, one of `downloads`, `bookmarks`, `history`; `text`; `cursor`; `limit`). The
  three brief 20 tools merged, with their snapshot paging. Two differences: every address is in the short form
  (item 3), and every entry carries a reference (from brief 28's table) that `chrome_open` takes as `ref`. The
  service keeps the full address under that reference for as long as the snapshot lives.
- **`chrome_read_typed_fields`** (an asking read, under the managed ask rules). The owner, 2026-11-13 (board
  #210): "Ask first." Brief 20 built this tool, and brief 28 says what it is, how its approval is bound to a
  prepared read, and which fields it may read (brief 28, item 5). **This package keeps it rather than redesigns
  it.** Keep its name unless it collides with one here.

  What this package does with it, and nothing more:
  - it is the eighteenth tool of the new list, with its name, input and behaviour unchanged, and its ask rule is
    part of the generated rules that must not change by a byte;
  - in its result each field is named by its label and by its short reference in place of brief 20's reference
    object, and each value sits in `untrusted_content`, quoted by brief 28's escaping rule;
  - an address in its question is in the public form (item 3);
  - a normal read tells Claude that it exists for a tab (`typed_fields`, brief 28), and the instructions say when
    to use it: only when his request needs what such a field holds;
  - its approval's binding to the prepared read stays exactly as brief 28 describes it and PR #27 built it. The
    short reference in the result is a name for Claude; the preparation keeps holding the reader's own
    elements;
  - an approved read changes nothing else. A later normal read shows `(filled, not read)` again, and the field
    still isn't typed into.
- **`chrome_upload`** (change; input: `tab`, `ref`, `path`). Brief 20's tool with a short reference. The proxy's
  file branch stays as it is, apart from the field names it reads.
- **Unchanged in name, input, result and behaviour:** `chrome_submit`, `chrome_submit_trusted`, `chrome_drop`,
  `chrome_operation_status`, `chrome_notices`, `chrome_notice_ack`, and the owner-only `chrome_sites`. The one
  thing that differs in what they return is item 3's: every address in a question or a description is in the
  public form, so a value that looks like a sign-in shows as `…`, and every address in a stage text or a notice is
  in the short form.
- A new error code, `take_first`, for `chrome_read`, `chrome_go`, `chrome_do` and `chrome_upload` on a tab that
  isn't in Claude's group: "this is one of the owner's tabs; take it, or open its address in a Claude tab". (Brief
  28b lets `chrome_read` work there without a take.)

### 7. Definitions, instructions and sizes

- Eighteen actions are offered to Claude, plus `chrome_sites`. Everything is generated from the definitions as
  today: the MCP tool list, the `aresos` command, `docs/control/TOOLS.md`, the ask rules, `user-mcp.json`.
- **The generated ask rules for Chrome must not change by a byte.** A test compares them with the copy on `main`.
  On `main` they cover two tools: `chrome_submit`, and brief 20's `chrome_read_typed_fields`.
- The rules shared by every Chrome action go once into the Chrome server's MCP instructions (brief 18d's pattern, with
  its check that Claude Code passes them on unshortened): untrusted page text; what to do on `stale_reference`,
  `reload_required`, `take_first`, `owner_signin`, `owner_dialog`, `not_read` and `unknown`; the version notice; that
  `done` doesn't prove delivery and pages can send on their own; the clipboard rule; how to read an outline line, a fold
  and `(filled, not read)`; that `full` reads everything; that `…` in an address hides a part that may be a sign-in,
  that lists show addresses without their query, and that such an address is opened by reference; that a field shown as
  `(filled, not read)` is read only through `chrome_read_typed_fields`, which asks him, and only when his request needs
  it; that a reference stays valid until its element changes; that one of his tabs is named together with the list's
  `seen`; that `chrome_do` stops at the first asking step, that its `prepared` entry goes unchanged to `chrome_submit`,
  and that steps it reports as not run are sent again. Each description keeps only what is specific to its action. Write
  them for Claude: what it does, when to use it, what comes back.
- **Sizes** (measured as brief 18d measured Mail's), for eighteen tools: all descriptions plus the instructions at most
  10,500 characters and not above the baseline; all names plus input schemas at most 6,300 characters. A test pins the
  exact totals; a change that grows them fails until the pin is changed on purpose.
- Put the final descriptions and instructions, exactly as generated, into
  `reviews/28a-chrome-act/TOOL-DESCRIPTIONS.md`.

### 8. The order of the change

Restructure in steps that keep everything working:

1. Add the new commands and the new tools. Four names exist in both tool sets with different inputs
   (`chrome_tabs`, `chrome_read`, `chrome_open`, `chrome_upload`), so the two can't simply stand side by side.
   **From this step on the catalogue is the new one:** the definitions, every generated file and the size pins.
   Brief 28's internal action is now `chrome_read` and is gone under its old name. Brief 20's tools stay callable
   under their names with the prefix `chrome_old_`, only when the service is started with brief 28's test-only
   switch: the environment variable that the CI container sets and the image never does (brief 28's test pins
   that the packaged unit doesn't set it). Unit tests and groups 14 to 16 pass, group 16's size rows included,
   because they measure the generated catalogue. Brief 20's groups pass unchanged through the old tools. The
   side-by-side latency run happens here (group 16).
2. Move the CI harness to the new tools **in its helper functions only**. Before you start, list in
   `reviews/28a-chrome-act/HARNESS-MAP.md` every helper you change, and every test that builds a `reference`,
   an `expected` or a `view` by hand (the staleness and mismatch cases), with its new form. A test may change how
   it reaches the tool. It never changes what it asserts about the receiver's log, the question, the binding or the
   outcome. A test of the old "any change makes every reference stale" rule becomes a test of item 2's rule, named
   in the map. The assertions that brief 28's field rules changed are in brief 28's map already; don't change
   them again.
3. Remove brief 20's replaced tools (`chrome_find`, `chrome_read_form`, `chrome_wait`, `chrome_click`,
   `chrome_fill`, `chrome_fill_form`, `chrome_select`, `chrome_check`, `chrome_press`, `chrome_scroll`,
   `chrome_dialog`, `chrome_navigate`, `chrome_take_tab`, `chrome_release_tab`, `chrome_close_tab`,
   `chrome_downloads`, `chrome_bookmarks`, `chrome_history`), the test-only switch with its `chrome_old_` names,
   the reader's `read` rows that nothing uses any more, and the old paging of `chrome_tabs`. Regenerate. Pin the
   sizes.
4. The full Chrome suite twice on the final head, with the base, Mail, boundary and qualification workflows.

### 9. The documents that list tools

- `docs/control/TOOLS.md` is generated.
- `docs/control/FEATURES.md`, Chrome table and the Chrome rows under "Files": change the **Tool** column to the new
  names, add rows for what is new (several tabs in one read, steps in one call, bringing a tab to the front), and
  change no **State** cell. List the changed rows in the report.
- `control/README.md`: the Chrome part.

## What must not change

- **The asking path:** the classification rules and the word list (`policy.py`, `policy.js`); `binding`, `prepare`,
  `question`, `revalidate`, `changed_compose`, `execute`, `command` and `trusted` in `adapter.py`; the adapters
  (`sites.py`); `chrome_submit`, `chrome_submit_trusted`, `chrome_drop`, `chrome_operation_status` and the notices;
  the 15-minute deadline; one approval, one run. Brief 20's asking read belongs to it too: `chrome_read_typed_fields`
  with its question, its binding to the prepared read, its one approval for one call, its refusal of
  credential-like fields and its new question when a field was added, replaced or relabelled. **Three narrow
  exceptions, each named where it is specified, and nothing beyond them:**
  1. `prepare` and `question` write addresses in the public form, and `execute` writes its two stage texts with
     addresses in the short form, while the payload and every comparison keep the full address (item 3);
  2. `input` brings its target on screen inside the armed hold before brief 20's own hit test (item 5);
  3. `input` checks its command's time once, right before the dispatch, and dispatches nothing when it is up
     (item 5, "Time").
  What asks, what is bound, and what is compared before an approved input don't change.
- **The places where this package touches the asking path stay as security re-check 2 judged them**
  (`reviews/28-chrome-capability/BRIEF-SECURITY-2.md`). Build each exactly so, and show its lines in the report:
  - *Public addresses in a question.* Only the description changes. The payload and the last comparison keep the
    whole destination. He can't inspect a hidden part in the question, and it can't change after his approval;
    that reduced visibility is a known limit (section 6).
  - *The reveal inside `input`.* It runs after the frames are armed and before the last facts read, the binding
    comparison and the hit test, so brief 20's last comparison stays the deciding one, and a scroll alone uses up
    no approved submission.
  - *The asking read in the new tool list.* It keeps its own managed ask rule, which opens no way around a
    send's question. Its own strength is the binding to the prepared read, which PR #27 built and brief 28
    tested.
  The fourth place it judged, the password additions, is brief 28's and is on `main` when this package starts:
  a form that holds a field withheld for unknown history is refused, not asked. That stays, through `chrome_do`
  too.
- **Brief 28's field rules and its read:** the password rule with its two additions, the outline format, the
  reference table and its run letters, the read's deadline. Nothing in them is relaxed or reshaped here.
- **The hold:** `guard.js`, `page.js`, the 500 ms window, the default block, the owner's own Enter, the three kinds
  of dialog.
- The extension still uses no DOM snapshot, no accessibility tree and no form serialisation. No new DevTools
  method. No new permission in the manifest.
- **Where Claude may go:** the schemes, the fixed list, the owner-only excluded-sites setting, read-only sites.
- **The take rules:** a reload before the first input, unsaved typing and playing media reported first, no reload
  of a form-loaded page. Popups as brief 20 built them.
- **The qualification record:** its format, `qualification.py`, `qualify.py`, the publishing workflow. The build
  hash changes because the code does; nothing else.
- **The service unit's sandbox lines** (`control/packaging/aresos-toold.service`; `test_unit.py` pins them).
- **Mail, the base and `os/`.** Change the base only where Chrome needs a helper that belongs there, and say why in
  the report.

**What changes in `background.js`, and nothing else:** a `show` command for `chrome_show`; a `tabs` reply that
holds every tab at once with the fields item 6 needs; the check of `seen` in `take` (item 6); and two additions to
`input` (item 5: "on screen first", and the check of the command's time right before the dispatch). Not the rest
of `input`, not `resume`, `dialog`, `prepare_control`, `release`, the debugger methods or the session rules.

## Tests

No model, no real site, no real account. Fixture pages only. **Browser tests run only in containers on GitHub's
Linux runners, through the control-chrome workflows. Never start, read or touch the owner's Chrome or any browser
profile on the machine you run on; locally run only plain Python and Node tests that start no browser.**

Every new rule gets a test that fails without it.

**Without a browser** (Python and Node). Brief 28's tests stay and pass. Added here:

- the `chrome_do` loop with a fake bridge: the check before the first step; the check before each step on fresh
  facts, with the value compared whole; a queued page step, a dialog and a new document found between two steps
  and after a `wait`; every stop, `not_run`, the deadline, nothing twice after an interruption at each point;
- an input's deadline below the service (item 5, "Time"). The bridge with a fake socket: an input without a
  reply is `unknown` after its time and 2 seconds, and a reply that comes later is dropped. The extension in the
  Node doubles: an input whose time runs out during its setup dispatches nothing, answers `expired` and releases
  its hold; one whose time runs out after the dispatch finishes as before;
- the change report;
- the reader's fingerprint function in the Node VM doubles that `reader.test.mjs` uses, with the password
  fixtures: `outline`, `facts` and `observe` give the same digest for the same element, and the digest of an
  unread field doesn't change with its value;
- the reference table for an action: every stale case of item 2, the fingerprint included, and that a refusal's
  present line counts as shown;
- the addresses of an operation (item 3): for a prepared and for a free operation whose page, form, link and
  frame addresses carry a marker value, the question, the description, both stage texts and the page-step warning
  hold no marker and the stage texts no query at all, while the payload still holds every full address.

**Passwords, in group 14 and in `password_exclusion`.** Brief 28's fixtures and cases stay and run through the
new list. Group 7's recording runs over every output this package adds: the change report after a "show password"
click, the results of `chrome_open`, `chrome_go`, `chrome_take` and `chrome_do`, and a prepared operation's
question for a form that holds such a field. The password is in none of them, in nothing the extension received or
sent, and in no log line. **A form with an unread field isn't sent** (brief 28, item 1) through `chrome_do`
either: the click on its Send button and Enter in its field end `refused` with the tool's own message, a
submission the page starts stays stopped, and the receiver has nothing.

**Group 14, reading and references** (browser): brief 28's cases pass through `chrome_read`. Added here, on brief
28's fixtures (F1 to F7 and H1):

- **Hostile text** comes back quoted and escaped in a change report and in the present line of a stale reference
  in `chrome_do` (`untrusted_content.now`), like everywhere in brief 28. A stale reference's message holds nothing
  from the page.
- **Loaded.** `chrome_go` to a fragment of the same page, and Back inside a single-page fixture, return
  `loaded: true` without a new document; a reload doesn't count as loaded before the new document is there.
  `until` on a page that never goes quiet returns when the text is there, with `loaded: false`.
- **References across tabs and restarts, for an action:** tab A's reference is refused when a `chrome_do` names
  tab B; after a restart of Chrome and after a restart of the service every reference from before is refused for
  an action as it is for a read.

**The fingerprint, in group 14.** Each of these is refused with `stale_reference` and the element's present line:
a link that keeps its name while its destination changes (once the path, once only the query); a list whose
options change while its name and chosen option stay; a box the page ticked; a menu button the page expanded; a
field whose value changed in a part the outline had cut. Each of these still runs: a button that became enabled; a
field that became `required` or `invalid`; an element that moved on the screen. And the limit, shown honestly: a
button without a destination keeps its name while the row around it shows another item; the free click runs, and
the report lists the case under known limits.

**The asking read, in group 14.** Brief 20's and brief 28's tests for it pass through the new list, the binding
cases included. Added on the new surface, with the taken, not yet reloaded tab:

- `chrome_read` shows the typed fields as `(filled, not read)` and counts them in `typed_fields`;
- **approved:** the result holds exactly the fields the question listed, each with its label, its short reference
  and its value inside `untrusted_content`; a value shaped like an outline line or an instruction comes back
  quoted and escaped;
- an address in the question is in the public form: the marker of the address fixture is not in it;
- the short reference of a returned field works for a later read by `ref`, which shows `(filled, not read)`
  again, and a `fill` on it is still refused;
- **the ask can't be skipped,** as for `chrome_submit` (group 12): an allow rule for the tool, and
  skip-permissions mode, still ask.

**Addresses, in group 14.** Fixture pages carry one marker value in every place a sign-in travels: under the
parameter names `code`, `access_token`, `sig` and `session`; as a random-looking value of 40 characters under an
ordinary name; the same in the fragment; as a user name and password; and as a 40-character path segment after
`/reset/`. They carry it in the page's own address, in link targets, in form actions, in a frame's address, in a
redirect's target, and in history, bookmark and download entries.

- The marker appears in no result of any tool, in no error message, in no question or description, in nothing
  `chrome_operation_status` or `chrome_notices` returns and in no line of the audit log.
- **An ordinary query is shown:** `?v=` with an 11-character id, `?q=red+shoes` and `?page=2` are in a read's `url`
  and in a link's detail read, as they are, next to a hidden `…` for the marker in the same address.
- **Lists show none of it:** the same addresses in `chrome_tabs` and `chrome_library` end in `?…`.
- **Records show none of it:** after a free click and after an approved send on a page whose address carries
  `?q=red+shoes`, no line of the audit log, no stage text and no notice holds `red` or anything else of a query or
  a fragment; each such address ends in `?…`.
- `chrome_open` with `ref` (a link, a library entry) and with `tab` still reaches the full address: the fixture
  receiver logs the whole query.
- Group 3's binding still refuses a destination whose query changed while the approval waited, also when the
  changed value is one the question shows as `…`.

**Group 15, going and acting in one call** (browser): as section 6 lists it. In addition:

- **time, through the real transports** (the `aresos` command and the MCP proxy, not a fake bridge). The cut-off
  governs the dispatch of an input, and the tests assert exactly that: the fixture stamps every input event it
  receives, and none is later than 12.5 seconds after the test sent the call (12 seconds, and half a second for
  the way from the test to the service).
  - **Staged waits carry a list across the cut-off.** A fixture page shows the texts "stage 1", "stage 2" and so
    on, one every 3.5 seconds. The list has 20 steps: a `wait` for the next stage (`timeout_ms` 8,000), then a
    fill, in turn. Expected: the waits for stages 1 to 3 are `done` and their three fills are counted by the
    fixture; the wait for stage 4, which is due at second 14, ends at second 12 as `timeout`; the fourth fill
    isn't dispatched; the result arrives within 18 seconds with `deadline: true` and `not_run` counting the
    rest; and the fixture counts no further input in the 10 seconds after the result. A single `wait` that
    isn't met is a different case and stays in "the steps as defined" below.
  - **Many inputs.** A list of 20 fills on F4 returns within 18 seconds. The fills that ran are `done`, the
    fixture counts exactly those, and the rest are in `not_run`.
  - **An input held back at the boundary.** A test build of the extension holds back one frame's answer during
    the setup of a fill that the service started at about second 11, until second 13. Expected: that fill is
    never dispatched, although its step had started; it counts in `not_run`; its committed operation says that
    nothing was dispatched; the fixture has no input event for it, then or later.
  - **Reads.** Brief 28's two cases (an `until` that never comes; five tabs of which one doesn't answer) pass
    through `chrome_read`.
  - **Nothing runs later, and the connection stays good.** After each case above the next call on the same
    connection gets its own answer, and a reply the test build releases late changes nothing.
  - **A caller killed in the middle of a list:** no input later than the bound above, every step that ran is in
    the log as its own operation, and the next call works;
- every asking case of group 1 runs through `chrome_do` once the harness has moved, with the receiver's log as
  evidence: nothing before approval, one arrival after, none on a repeat;
- a list whose third step asks: the fixture counts the first two inputs, no input from steps three to five, and
  after `chrome_submit` exactly the third;
- **on screen first:** a click, a fill and a tick on elements 10,000 pixels below the fold, and on one inside a
  scrolled inner box, each land (the fixture counts them). A page that submits a form from its `scroll` handler
  when that scroll comes: the submission is held and asked, with group 2's evidence. An approved click on a Send
  button that sits off screen when `chrome_submit` runs is dispatched once;
- **the steps as defined:** `select` by an option's value, by its label, by a label two options share (refused),
  by a disabled and by a missing option (refused); `scroll` without `ref` is invalid input; a `wait` that isn't
  met stops the list as `timeout`; a `dialog` step on another dialog than the one last shown is `stale`. Every
  outcome of the table appears once with its shape. A list that fails at its third step after two inputs returns
  a normal result with two operation ids, which `chrome_operation_status` knows;
- **nothing unseen is overwritten:** a list whose first step makes the page put a draft into another field, and
  whose second step fills that field: the second step is `stale`, the field still holds the draft, and the result
  shows the field's present line. The same when the owner types into that field with real keys while the first
  step runs. The same for a value of 5,000 characters that the outline showed cut, after its last character
  changed. A `fill` and then Enter on the same field passes without a read in between;
- **the look between steps:** a submission that the page starts while handling step one and that reaches the
  service only after step one's reply, and one that arrives during a `wait`: the next step doesn't run, the
  fixture counts no further input, and the held submission is in `prepared`. A dialog that opens during a `wait`,
  and a new top document that loads during a `wait`, stop the list the same way;
- a control inside a folded part of the outline, found with `find` and labelled Delete, still asks;
- the read-only fixture site refuses every acting step and still allows `wait` and scrolling;
- **the list binds:** `chrome_take` and `chrome_open` with one of his tabs are refused without `seen`. The owner
  then navigates the listed tab, once to a new document and once to a new address inside the same document:
  `chrome_take` is refused with `stale_reference`, the new page's fixture records no message from the reader, and
  the tab isn't attached, moved or reloaded. `chrome_open` with `tab` still opens the address the list showed. With
  the tab unchanged both work without any further question. A `seen` older than 8 lists, and one from before a
  restart of Chrome or the service, are refused;
- **a taken tab stays his:** `chrome_close` on a taken tab is refused and the tab stays open; `chrome_go` in a
  taken tab that holds typing answers `reload_required` and the page isn't replaced; in a taken tab without typing
  it reloads under brief 20's guard and then navigates;
- the conservative mode (an unqualified Chrome major) asks for the same inputs through `chrome_do` as brief 20's
  tools did.

**Group 16, efficiency** (browser, in the latency harness): the scripted tasks below, each run against the baseline
file brief 28 committed. The read rows are brief 28's, measured again here through `chrome_read`. **Each row names
the exact calls it allows; the test makes those calls and no others.** If a budget can't be met with them, the
budget or the tool changes, in the brief, before the build goes on (stop rule): the test is never bent to fit.
Characters are counted on the whole result as Claude receives it (the JSON text of the tool result), for the
baseline and for the new tools alike. The build fails when a budget is exceeded or when a number is worse than the
baseline.

| Task | Budget |
|---|---|
| F1: the first read: `chrome_read` with the tab | 1 call, the whole outline, at most 6,000 characters |
| F1: everything: `chrome_read` with `full` and `max` 40,000, then the same call with each `cursor` it returns | at most 3 calls, at most 75,000 characters in all |
| F1: the 80 fields with their values: after the first read, `chrome_read` with the form's `ref` | 1 further call, at most 6,000 characters |
| F2: the whole table: after the first read, `chrome_read` with the table's `ref` and `max` 40,000 | 1 further call, at most the cells' own text plus 7 characters for each cell plus 800: 23,600 characters for this fixture |
| F3: find the one link with the unique name: `chrome_read` with `find` and `role` | 1 call, at most 800 characters |
| Open a fixture page and return one fact from it: `chrome_open` with `url` | 1 call |
| F4: fill 6 fields and send the form: `chrome_open` of the form's page, `chrome_do` with six fills and the click, `chrome_submit` | 2 calls and `chrome_submit`; one question; the receiver has it once |
| F7: three result pages, one click each, the titles collected: from an outline in hand, three `chrome_do` calls of one click, each returning the next page | 3 calls |
| Compare three open tabs: `chrome_read` with `tabs` | 1 call |
| List 25 open tabs (titles of about 30 characters): `chrome_tabs` | 1 call, at most 3,500 characters |
| F5: a free click that changes part of the page: from an outline in hand, one `chrome_do` | 1 call, at most 2,500 characters, every changed line named (`more_changes` is 0) |
| Descriptions plus instructions (18 tools) | at most 10,500 characters, and not above the baseline |
| Names plus input schemas (18 tools) | at most 6,300 characters |
| Latency (the comparison in one run, below) | the first read of F1, a free click with its report, and the 6-field form are each at most 1.10 times brief 20's median plus 50 ms; a latency check PR #27 brings stays within its targets |

**Latency: old and new in one run.** Runners differ, so old and new tools are timed in **one run**. At step 1 of
"The order of the change", while both tool sets exist, one job runs each timed task with brief 20's tools (under
their `chrome_old_` names) and with the new ones, five times each after a warm-up, and compares the medians: the
first read of F1, as brief 28 timed it, now through `chrome_read`; a free click with its change report, against
brief 20's click and the read or find after it; filling 6 fields and sending the form. The new tools pass at no
more than 1.10 times the old median plus 50 ms. That run's id and numbers go into the report and into the
baseline file. After brief 20's tools are removed, the check that stays compares each task with the new tools'
own median of that run and fails above 1.5 times. Where PR #27 brought a latency harness, this runs inside it,
as brief 28's baseline does. Fewer calls don't prove a faster tool: a step of `chrome_do` still makes brief 20's
full facts read. The timings are what shows it, and the report gives them beside the call counts.

**The rows add up** (package re-check 2, N3). Every budget counts the JSON text of the result, so each quote
of the outline costs 2 characters, each line break 2, and each `…`, `→`, `·` and `›` 6. A read's result has about
310 characters around its outline, and a `chrome_do` result about 450. Worked through for the fixtures as they
are defined above:

- The read rows (F1 three times, F2, F3) are worked through in brief 28 and were measured there: about 3,900,
  61,500, 4,950, 23,050 and 420 characters as sent, against 6,000, 75,000, 6,000, 23,600 and 800. F2's call passes
  `max` 40,000 because the table's outline is about 20,100 characters, and every cell stays quoted.
- 25 tabs: a line is at most about 120 characters with a ten-digit tab number, a title of 30 and an address at
  its cut of 60: about 3,200 as sent. The budget is 3,500.
- F5: at most 13 changed lines of at most 80 characters are about 1,050 characters of outline, about 1,650 as
  sent with the result around them. The budget is 2,500, and the default `max` of 2,000 doesn't cut the report.
- F4, six fills and a click: all 25 fields and the button are in the 4,000 characters `chrome_open` returns,
  because a form's fields follow the form's own fold rule. Seven steps take about 5 seconds of the 12 a list
  has for its inputs.

If the built tool misses one of these by more than its fixture explains, the budget or the tool changes in the
brief (stop rule); the fixture isn't made smaller to fit.

**Brief 20's groups 1 to 13** pass twice on the final head, through the new tools, in both install modes. Register
the new browser cases in the named inventory (`ci/verdicts.mjs`) the way brief 20's FEATURE and VIEW cases are
registered, beside the cases brief 28 registered. The password cases join the `password_exclusion` group. Cases
that prove an asking step asks join `classification` or `binding`. Group 16 is a CI check only and never part of a
verdict. Don't add a core group and don't change the record's format. Say in the report which case went where.

The base's, 18d's and Mail's suites still pass, and the generated artifacts are in sync.

## Out of scope

- His open tabs in place, the **READ** sign, the popup list, incognito, tabs in the background: brief 28b.
- Anything in the asking path or the hold beyond the three exceptions named in "What must not change".
- A change to brief 28's read, its field rules or its reference table, beyond the fields this brief adds to
  them.
- Screenshots (owner, 2026-11-13, board #202: "Text only first"), coordinates, hover, drag, console or network
  reading, running script text, a search that needs a model, loops or conditions in a step list, steps across
  tabs, a richer result for `chrome_submit` (section 6, "Left out on purpose").
- Any real site or account. The image (`os/`). Running Claude Code with a model.

## Paths

**May change:** `control/aresos_control/chrome/adapter.py`, `definitions.py`, the view module and new modules
beside them; `control/aresos_control/chrome/bridge.py` (only the reply wait for an input, item 5, "Time");
`control/chrome/extension/reader.js` (the fingerprint function, the reveal, the instance id in `facts`) and
`background.js` (only as items 5 and 6 say); `control/aresos_control/proxy.py` (the Chrome upload branch's field
names); the generated files; `control/chrome_tests/`, `control/chrome/ci/`;
`.github/workflows/control-chrome.yml` (not the qualification workflow); `docs/control/TOOLS.md`,
`docs/control/FEATURES.md` (item 9), `control/README.md`; `reviews/28a-chrome-act/`.

**Must not touch:** `os/`, `mod/`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/TOOLS-HANDOFF.md`,
`STATE.md`, `HANDOFF.md`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `briefs/`; `control/aresos_control/mail/`,
`control/mail_tests/`, `control/boundary/`, `control/checks/`, `control/packaging/`; `reviews/20-chrome/`,
`reviews/28-chrome-capability/`, `reviews/28-chrome-read/` and every other package's `reviews/` folder;
`control/chrome/ci/efficiency-baseline.json` except to add the side-by-side timings; in the Chrome code
`guard.js`, `page.js`, `policy.js`, `manifest.json`, `policy.py`, `sites.py`, `qualification.py`, `committed.py`,
`uploads.py`, `qualify.py`.

## Acceptance

- The eighteen tools exist with the inputs and results above; brief 20's replaced tools, the internal action and
  the test-only switch are gone.
- Groups 14, 15 and 16 pass, and groups 1 to 13 pass twice on the final head through the new tools.
- Every budget holds against the committed baseline.
- The generated Chrome ask rules are byte-identical to `main`'s.
- `HARNESS-MAP.md` accounts for every changed helper and every rewritten staleness test.
- No secrets, real addresses, account names, provider names or real sites.

## Report (`reviews/28a-chrome-act/REPORT.md`)

AGENTS.md's format (Done, Verified, Not verified, JUDGMENT-CALL, PLAN-GAP, Open questions), and in it:

- the baseline and the measured numbers side by side, per task, with run ids;
- the tool descriptions and instructions as Claude will read them, with anything you are unsure reads well;
- what changed in `adapter.py`'s `payload` and `facts`, line by line; the lines of the three exceptions (the
  projected addresses in `prepare`, `question` and `execute`; the reveal in `input`; the time check in `input`);
  and a statement that nothing else in the asking path changed, with the diff command that shows it;
- for the asking read: that its binding cases still pass through the new list, with the run id. The brief claims
  nothing about that binding; the report says what a run showed;
- the harness map and the inventory mapping;
- every claim marked **run** (workflow run id and log line), **read** (file and line) or **assumed**.

**Known limits.** Keep `reviews/28a-chrome-act/KNOWN-LIMITS.md`: start from section 6's "Known limits" and brief
28's file, and for every line you add, change or find untrue give what it is, the harm and why it is acceptable or
not. The lead moves the result into section 6. A flaw with real harm (an action without its question, a password
or sign-in code read, data loss, his normal use broken) is never a limit: fix it or stop.

## JUDGMENT-CALLs

No open JUDGMENT-CALL.

**Already decided by the owner** (his words; `docs/control/PLAN.md` and the board):

- 2026-11-11: capability before more hardening. "I don't just wanna rebuild Claude in Chrome. I wanna make a
  better tool for AresOS that's more efficient with readings, navigation, free tab navigation etc."
- 2026-11-11: the bar. Safe the way a good MCP or CLI is; a flaw with real harm is fixed, and a known limit is for
  low harm. A password or a sign-in code reaching Claude is never a limit.
- 2026-11-13 (board #202): "Text only first." Pages are read as text; no screenshots in these packages.
- 2026-11-13 (board #210): "Ask first." A typed field whose history the reader doesn't know is read only after he
  was asked: brief 20's `chrome_read_typed_fields`, kept here as it is built.
- 2026-11-13 (board #213, "Show link addresses"): Claude sees link addresses with their query on the pages it
  reads, with what looks like a sign-in hidden by brief 28's rule. He chose this knowing that a short sign-in code
  in a link can slip through. Lists keep the short form, and so does everything the service writes to its log.
- 2026-11-13 (board #201): "Yes, when I ask", for closing his tabs. That is brief 28b's; in this package
  `chrome_close` closes only Claude's own tabs.

**Already decided by the lead** (2026-11-13, on the design's second reviews; a builder doesn't reopen them):

- The design is built as three packages, 28, 28a and 28b, in that order, and none reaches the laptop before all
  three are merged.
- The four places where the design touches the asking path stay as security re-check 2 judged them ("What must
  not change").
- A form that holds a field withheld for unknown history isn't sent by Claude, through `chrome_do` either, and
  an approved asking read doesn't lift that (brief 28, item 1).
- The asking read's approval is bound to a prepared read; PR #27 built it, and this package keeps it (item 6).
- A deadline reaches the extension by the time each command carries. For an input that adds one check right
  before the dispatch, a bounded wait in the bridge and the dropping of a late reply, and nothing more (item 5,
  "Time"; package re-check 2, N2).
- Budgets are counted on the result as sent, each row with the calls it names; a table's cells stay quoted
  (group 16; N3).
- `chrome_open` with `tab` opens the address the list showed, wherever the tab has gone since (item 6; N4).

**Decided here, and the lead's to defend:**

- A reference is checked on its own element, by a fingerprint the service keeps, not on the whole view (item 2;
  section 6 gives the reasons and names what is no longer checked).
- The tool list is replaced, not kept beside the new one: one surface to describe, test and review.
- The library is listed in the short form like the tabs, and an operation's stage texts and notices are written
  in the short form because the log holds the same texts (item 3). Both are choices made here and easy to turn.
- `request` isn't an input in this package. An input that is accepted and ignored is dead weight, and it suggests
  a check that doesn't exist. Brief 28b adds it where it means something, and the size pins move then.
- A list holds at most 20 steps and ends at its deadline (item 5, "Time").

Anything you meet that changes how Chrome feels for the owner goes into the report as a JUDGMENT-CALL with what you
chose, what you rejected, why, and what changing it later costs. Likely candidates: a wait that is too short or too
long on real-looking pages; a change report that says too little to go on without a read; an address whose hidden
part Claude turns out to need.

## If unsure

Take the option that keeps a send from going without its question or going twice, that never returns a password,
and that never says something happened or was stopped when the tool can't know. Then the option that returns
fewer characters. Say what you chose in the report.

## Stop rules

- Stop and report, rather than weaken a rule, if a budget can only be met by leaving out something Claude needs to
  act safely, if a budget can't be met with the calls its row names, or if the asking path would have to change
  beyond the three exceptions named in "What must not change".
- Stop if a binding case of the asking read fails through the new list.
- Stop if any test would need a real site or a real account.
- The full `control-chrome.yml` suite takes three to four hours a run. Develop against the browser-free tests and
  the short job. Plan about 10 full runs; tell the lead in the report before passing 14. Wait on each run with one
  blocking call; never poll turn by turn. Mark report-only pushes `[skip ci]`.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in your worktree, on branch `pkg/28a-chrome-act`, from `main` after brief 28's merge. Commit in small
  steps, push this branch, open a draft PR against `main`. Never merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- On the laptop: one test suite at a time, `pkg28a-` names for scripts and `/tmp` paths, and check free memory
  first.
- Name your model in a commit trailer.
