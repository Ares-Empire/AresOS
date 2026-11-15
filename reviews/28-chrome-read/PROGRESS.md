# 28 Chrome read: progress

Builder steps keep this file; the last step turns it into the report. Newest state first.

## Step 6 (2026-11-15, Claude agent on Fable 5.2): the background's three commands, the credential words, item 8, the typing refusal, the late shadow root. Pushed, not yet read in CI

Fable because the reader runs inside the extension on hostile pages. Step 5's "Part B", items 2 to 5. **None of this
step's JavaScript has run** (no Node on the laptop): the three runs below are its first. Group 14's F6 and H1
fixtures were not started (budget).

### Done

- **`background.js`: `outline`, `options`, `page_state`** (`aa81726b`), tests in `background.test.mjs` (7 tests).
  - `outline` → `outlineView(tab)`: `facts(tab,null,'outline')`, so every check of a read applies (control, the
    dialog, the fixed list per frame, the late reader, the pinned private document, the inherited origin). Reply:
    `{session, tab, control, url, title, effective_url?, needs_reload, uncovered, dialog: null | {kind, text},
    frames}`; a frame is `{frame, parent, browser_document, effective_url, document, reader, watched, origin, url,
    title, scroll, height, omitted, nodes}`. The top document stands first. A `frame` node keeps its `frame` only
    when that frame's outline is in the reply (never the top frame, never its own). 20,000 nodes a tab: each reader
    is sent what is left (`limit`), and counts the rest in `omitted`.
  - `options` (`{tab, frame, document, reader, element}`) → `{session, tab, frame, document, reader, options}`. Only
    a document an outline has read is asked (`privacyDocuments`), and the reader refuses another document or reader
    instance (`stale_reference`): a number names an element only for the instance that gave it.
  - `page_state` (`{tab}`) → `{session, tab, control, queued, address, dialog: false, document, ready, token}`;
    with a dialog open `{…, dialog: true}` and no `token`, `document` or `ready`. `token` is a sha256 over each
    readable frame's `[frame id, Chrome document id, reader document, reader instance, revision, address digest,
    fields digest]`; `address` is a sha256 of the tab's address.
  - `facts()`'s third argument names the one command every frame is asked (`true` stays brief 20's typed-field
    list). Its guard check, reader parameters and document pin became `requireGuard`, `readerBinding` and
    `pinDocument`, which the new commands share. Nothing of `input`, `resume`, `dialog`, `take`, `release` changed.
  - `reader.js`: `outline` takes `limit`; `options` needs `document` and `reader`; `page_state` returns `origin`.
- **The credential words** (`40d1c650`): `control/aresos_control/chrome/credentials.py` (the brief's list as data,
  `CREDENTIAL_WORDS_VERSION = 1`), the copy in `reader.js` (`credentialNames`, one line of JSON),
  `test_credentials.py` (4 tests: the copy equals the definitions; version 1 is the brief's list), and five tests
  in `reader.test.mjs`. As the lead decided: the merged expressions stay, either list makes a field password-kind,
  the new list counts only for a field a person types into.
- **Item 8** (`1ca29fd3`): `Debugger.scriptParsed` takes a script for one of ours only when `params.url` **and**
  `params.embedderName` are its extension address. The doubles' events carry the name; one new test.
- **Typing into a field that isn't read** (`421888cd`): the reader's `focus` (every `fill` and key goes through
  it) refuses a typed field of unknown history with `owner_signin`. `unknownHistory()` is the one predicate.
- **The shadow root met late** (`85eeffba`, its own commit): `privacy.metRoots`, `privacy.lateFields`, `meet(root)`
  called where `roots()` and `remember()` find a shadow root. `safeValue`, the asking read's list (`typedFields`)
  and `focus` follow `unknownHistory()`. Two tests in `outline.test.mjs`.

### Runs (pull_request; not watched, not read)

| Head | Holds | Control Chrome | Qualification | Boundary | Base | Mail |
|---|---|---|---|---|---|---|
| `2c8d2332` (step 5) | | 43712993037: **success** (the latency audit job passed on its second attempt) | 43712993128 (was still running) | success | success | success |
| `40d1c650` | the three commands, the credential words | 43722368284 | cancelled by the next push | cancelled | cancelled | cancelled |
| `421888cd` | + item 8, the typing refusal | 43722522475 | cancelled by the next push | 43722522498 | 43722522518 | 43722522535 |
| `85eeffba` | + the late shadow root | 43722792150 | 43722792135 | 43722792144 | 43722792161 | 43722792156 |

Seven full `control-chrome` runs so far for this package (the brief plans about six and wants the lead told
before nine).

### The lead's decisions on step 5's open points (2026-11-15)

- JUDGMENT-CALL 3, the credential words: as advised (built, above).
- JUDGMENT-CALLs 4, 5, 6: accepted.
- Group 16's node lists: the browser fixtures must match `view_fixtures.py` **as the rendered outline** (the
  browser's extra `text` node around a `<label>`-wrapped field is accepted); the tests compare rendered outlines.
- `f4()`'s nodes 23 and 24 stay unit-test-only (a document is either watched or not); the fixture's comment must
  say so (not written yet: it belongs with group 16's browser comparison).
- The late shadow root leaving a component's prefilled default `(filled, not read)` for good: accepted as the safe
  direction, a known-limit line. **But see PLAN-GAP 1 below: it also refuses brief 20's own shadow-root forms.**
- Deep nesting overflowing the reader's recursion: accepted, fails closed, a known-limit line.

### Left, in order

1. **Read the three runs**, oldest first, so a failure is found in the commit that caused it. Expect JavaScript
   errors in my tests or doubles; fix the cause. A red "Require lead ceilings" is the gate's own result (stop and
   report). What I expect from each:
   - 43722368284: the fixtures jobs' `node --test` (`background.test.mjs`, `outline.test.mjs`, `reader.test.mjs`)
     and `test_credentials.py` in the python shards. The browser groups should be as on `2c8d2332`: nothing in
     the browser calls the new commands yet, and no fixture field carries one of the new words.
   - 43722522475: item 8 in a real browser for the first time. If Chrome's `embedderName` for a content script or
     an injected file isn't the file's extension address, **every** browser job fails at admission (no context is
     learned). Then: read `browser-boundary.jsonl` of one job for the `Debugger.scriptParsed` events' real
     `embedderName`, and fix the comparison; the unit test stays.
   - 43722792150: **I expect red browser jobs here, from the late-root rule** (PLAN-GAP 1): GROUP 7
     (`matrices.mjs`, "all password kinds across open closed and cross-site roots": the forms of `Submit top 1`,
     `top 2`, `cross 1`, `cross 2` stand in shadow roots and hold the prefilled plain textarea "Safe draft", so
     their click is refused with brief 20's withheld-form message), and `review-matrices.mjs`'s `review-shadow-*`
     cases (a root attached in a click handler, `<input name="draft" value="Saved">`, a held submission whose
     resume is then refused). The run gives the exact list.
2. **The lead decides PLAN-GAP 1** before any harness test is changed.
3. Group 14's F6 and H1 fixtures (not started).
4. Then step 1b's list from item 3: the adapter (`chrome_outline` behind the test-only switch), time, groups 14
   and 16 in CI, the harness map, the known limits, the report.

### What the adapter gets (for the next step)

- `bridge.call('outline', tab=…)`: `nodes.View(reply)` takes it as it is. Check the fixed list on `reply['url']`
  and each frame's `effective_url`, as `read` does. `uncovered` lists frames that weren't read (`eligible: false`:
  the fixed list; `true`: no reader). **When the top document wasn't read, `frames[0]` is a child frame**
  (`frames[0]['frame'] != 0`); `nodes.View.top` assumes the first one is the top document.
- `bridge.call('options', tab=…, frame=…, document=…, reader=…, element=<number>)`: `nodes.options(reply['options'])`.
- `bridge.call('page_state', tab=…)`: poll this, never a read. A frame whose reader doesn't answer is part of the
  token as "no reader" (the token moves when it arrives); lost private history refuses, as a read does.

### What the code doesn't show

- **The credential words, how they match** (`namesCredential` in `reader.js`). A name is cut into parts at
  anything but a letter or digit, at a change from lower to upper case (`otpCode`) and at the end of an acronym
  (`OTPCode`, `mTAN`). A part counts with its trailing digits dropped (`PIN2`, `cvv2`; `2fa` stays). A paired word
  (`code`, `key`, `phrase`) counts beside a companion as a neighbour **in either order** (`SMS code`,
  `Code (SMS)`), or written as one word with the companion first and the `s` German puts between them
  (`Einmalcode`, `Sicherheitscode`, `apikey`). `ä ö ü ß` are folded (`bestaetigungs_code`). The same six places as
  the merged check (`name`, `id`, `autocomplete`, `aria-label`, `placeholder`, the labels and `aria-labelledby`).
  I ported both checks to Python (not committed) and ran every expectation of the new Node tests through it.
- **"A field a person types into"** is an `input` of any type but `hidden`, a `textarea`, an editable area; not a
  `select` or a `button`. So a checkbox labelled "Remember this token" is password-kind, as a checkbox labelled
  "PIN" already was under the merged expressions.
- **A field's verdict is kept** (`credentialVerdicts`, a WeakMap) while its kind and its name strings are the
  same. A read asks `credentialLike` many times a field, and the second list would have doubled that work
  (the latency gate reads F1's 80 fields). The key is the exact strings, so a renamed or retyped field is judged
  again (tested).
- **A typed field labelled "Seed" or "Token" is withheld** whatever it is for (a world seed, a filter token):
  the brief's bare words.
- **The typing refusal covers a typed field of unknown history whether filled or empty.** The brief names the
  filled one. An empty one exists only in a document that isn't watched, where brief 20 already refuses input
  until the guarded reload.
- **The late root, when a root is "met":** in the reader's sweep after any change it sees (`remember`), or in a
  read (`roots`), whichever comes first; a root met in a read is observed from then on. A field named or masked
  like a password is skipped there (it is protected anyway, and its state is never copied). The marks live in
  `privacy`, so they outlive a release and retake of the same document.
- **`page_state` pins a document's private identity** like a read does (`pinDocument`), so a later reader of the
  same document with another identity is refused.
- **Item 8 asks for both names.** A script with the browser's name under another `url` isn't taken either.

### Local checks

```
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_credentials test_efficiency
Ran 17 tests
OK
```

No JavaScript ran. Every edit was an exact, counted replacement; the brackets of the four edited JavaScript files
balance as they did before.

### JUDGMENT-CALLs (technical; for the lead)

1. **`facts()` shares three small functions with the new commands** instead of the new commands copying its
   checks. Same behaviour for brief 20's reads; a later fix to a check reaches all three. Rejected: copies.
2. **`options` is bound to the reader's document and instance, and only a document an outline pinned is asked.**
   Rejected: the element number alone (after a reinstall it names another element).
3. **`page_state` with a frame that has no reader:** part of the token, no error. Rejected: refusing, which would
   end every wait on a page with one slow frame.
4. **The matching rules of the credential words** (above): digits, acronyms, either order, the linking `s`.
   Each makes the rule stricter than "whole words and parts of a name" read narrowly.
5. **The verdict cache touches brief 20's `credentialLike`.** Same verdicts; the alternative was a slower read.
6. **The typing refusal for an empty unread field too** (above).

### PLAN-GAPs

1. **The late-root rule, built as worded, refuses brief 20's own shadow-root forms.** A component's root is
   always met after it was filled (the observers run after the script), so every prefilled typed field in a
   shadow root is `(filled, not read)`, and exception 4 then stops Claude from sending its form: GROUP 7's four
   shadow-root forms and the `review-shadow` cases (see "Left", 1). GROUP 7 is a core group. Two ways:
   - **(a) keep the rule, change the harness** (HARNESS-MAP): those fixtures start their plain field empty and
     fill it in a later task, or the tests expect the refusal. Real sites keep the cost: a web component with a
     prefilled field (a search box with a default, an edit form) can't be read or sent by Claude without asking.
   - **(b) narrow the rule with the guard's typing record:** a filled typed field at the first meeting is unread
     only when the guard saw typing into it since the document's start, or can't vouch for that (`guard.typedBy`,
     `typingGap`; the reload report already relies on them). That is the brief's own reason ("he can type into
     its field and make it plain"), it leaves brief 20's groups as they are and removes the known limit. What it
     gives up: text a page script copied into such a field from a typed one.
   My advice: (b), after a security look, because (a) withholds far more than the harm the rule names. Not built:
   it relaxes the rule as worded, so it is the lead's call.
2. **The merged asking read chose its fields by the document** (`watched ? [] : …`), so it left out the late-root
   field. Changed to the reader's mark, the one change item 5 allows.
3. **Item 8 can't be checked without a browser.** I expect `embedderName` to be the file's extension address for
   a registered content script and for `scripting.executeScript` with `files`; run 43722522475 shows it.
4. **The tab's node limit needed the background:** the reader limits a document, the service a tab, so three
   frames of 10,000 nodes would have been refused whole by `nodes.View`.

### For `HARNESS-MAP.md` (the last step writes the file)

- `reader.test.mjs`, "fixes b G4.3 API and key words alone, and token names, stay ordinary fields": the names
  `Token`, `csrf_token`, `authenticity_token`, `_token` on a **typed** field are withheld now (exception 1). The
  test keeps the other names; "brief 28 a typed field named token is withheld, and a hidden field named so stays
  an ordinary field" holds the four, and shows them ordinary on a hidden field.
- `background.test.mjs`: every `Debugger.scriptParsed` double of one of the extension's files carries
  `embedderName` (item 8; no exception, the doubles follow the browser).
- Pending PLAN-GAP 1: GROUP 7 and `review-shadow` (exceptions 2 and 4).

### For `KNOWN-LIMITS.md` (added to step 1's list below)

- **A prefilled field in a web component isn't read.** A typed field that already holds text when the reader
  first meets its shadow root shows `(filled, not read)` for the life of the document, also when the text is the
  component's own default. *Harm:* Claude can't read or type into it, and can't send a form that holds it; the
  owner can let Claude read it through the asking read, or sends the form himself. (Open: PLAN-GAP 1.)
- **A page nested thousands of levels deep can't be read.** The reader's walk overflows and the read fails;
  nothing is returned. Beyond 150 levels the service refuses the reply.
- **A field named like a credential that isn't one is withheld** ("Seed" for a world seed, "Token" for a
  filter): the owner types it himself.

## Step 5 (2026-11-15, Claude agent on Fable 5.2): the baseline committed; the reader's three commands in `reader.js`. Stopped at the budget

Fable because the reader runs inside the extension on hostile pages. Stopped at the step's token budget with the
reader half done: **nothing of this step's JavaScript has run yet** (no Node on the laptop); run 43712993037 is its
first run and was not read.

### Done

- **Part A, the baseline** (`525aa67f`): `control/chrome/ci/efficiency-baseline.json` is run 43705060936's
  `efficiency-measured.json` byte for byte (`cmp`; artifact `chrome-efficiency-43705060936-1`). F4's row is brief
  20's refusal, the lead's decision. `test_efficiency.EfficiencyBaselineTest` (4 tests): every task of `TASKS`
  (read from the probe's source text, 11 tasks) with the same row, plan and outcome, the recorded tools follow the
  plan, only F4 is `refused`, and a sha256 of everything but `latency_comparisons` (the one part that may still
  grow). `efficiency.test.mjs` got the same comparison against the imported `TASKS`.
- **Part B, `reader.js`** (`2c8d2332`), three read-only content commands:
  - `outline`: one document's reply as `nodes.Document` takes it (`document`, `reader`, `watched`, `origin`, `url`,
    `title`, `scroll`, `height`, `omitted`, `nodes`). Ids are the number of the reader's own element id (`e12` is
    12, decision 4). Roles only from the list or the tag table. Own text as runs, a child's id where it stands;
    formatting tags and elements of other namespaces add their text to the run they stand in (decision 6).
    The password check (`password()`) comes before anything of an element is read; a password-kind field is a
    leaf `{role: "password", name, unread: true}`. Values go through `safeValue` (the history rule): `unread`
    with `filled`. A native `select`: `option_count`, `chosen`, the first 50 `options`, no option nodes.
    Scripts, styles, the head, hidden elements and everything outside an open modal are left out. 20,000 nodes.
  - `options` (`{element: <number>}`): every option of one native `select`; anything else, a password-kind
    field included, is `stale_reference`.
  - `page_state`: the reader's part of the token: `document`, `reader`, `revision`, a sha256 of the address, a
    sha256 of the fields' live state (a readable value; ticks; chosen options; for an unread field only filled
    or empty; for a password field only that it is there), `ready`.
  - Tests: `control/chrome_tests/outline.test.mjs` (7 tests, a tree of DOM doubles in a VM; a protected value's
    getter throws). `run.sh` runs every `*.test.mjs`, so nothing was wired.

### Runs (pull_request, not watched, not read)

| Head | Control Chrome | Qualification | Boundary | Base | Mail |
|---|---|---|---|---|---|
| `525aa67f` (baseline) | 43712012619 | | | | |
| `2c8d2332` (reader) | 43712993037 | 43712993128 | 43712993103 | 43712993081 | 43712993061 |

### Left, in order

1. **Read run 43712993037**: the fixtures jobs' `node --test` (`outline.test.mjs`, the new test in
   `efficiency.test.mjs`) and brief 20's own reader tests (`safeValue` and `name` gained a defaulted parameter;
   nothing else of them changed). Expect JavaScript errors in my doubles or expectations; fix the cause. The
   latency gate is untouched by this step; a red "Require lead ceilings" is its own result (stop and report).
2. **`background.js`: the three commands** (not started; `background.js` is unchanged). What I read of it:
   - `outline`: `facts(tab, reference, typedOnly)` already does every check a read needs (control, the dialog,
     the fixed list per frame, the late reader, `privacyDocuments`, the inherited origin, which needs the
     `origin` my reply carries). Let its third argument name the content command (`'typed_fields'` today,
     `'outline'` new) and dispatch `outline` beside `typed_fields` (about line 922). Drop a node's `frame` when
     that frame isn't among the readable ones; map brief 20's dialog object to `{kind, text}` (or do it in the
     adapter). Frames: `{frame, document, reader, watched, url, title, scroll, height, omitted, nodes}`.
   - `options`: one frame's `content(tab, frame, 'options', {element})` behind the same frame checks.
   - `page_state`: per readable frame the reader's reply joined with the frame id and Chrome's document id;
     `document`, `address`, `ready`, `dialog`, `queued`; with a dialog open no token.
   - Tests in `background.test.mjs`.
3. **The credential words module** (not started): the words beside `policy.py`, a copy in `reader.js`, a test
   that compares them. See JUDGMENT-CALL 3 for what the merged reader already has.
4. **The shadow root met late** (not started): see "What the code doesn't show".
5. **Item 8** (`embedderName` in `Debugger.scriptParsed`) and the reader-side refusal of typing into an unread
   field (`focus` refuses only a password field today).
6. Group 14's F6 and H1 fixtures (not started), then step 1b's list from item 3: the adapter, time, groups 14 and
   16 in CI.

### What the merged reader already does of item 1 (read, not changed)

- **History:** `watched` (from the document-start mark), and `safeValue` returns `unknown_history` with
  `value_status` filled or empty for a typed field in a document that isn't watched; `typedField` is the one
  predicate. The outline uses exactly this.
- **Names:** `credentialLike` in `ownPassword`, with its own word list as two regular expressions (stems and
  whole tokens, English and German). It has no bare `token`, on purpose (hidden CSRF fields named `*_token`).
- **The reader instance:** `readerInstance`, drawn at each install; `outline` and `page_state` return it.
- **A form with a withheld field isn't sent:** `adapter.py` line 31 and `background.js` line 775
  (`WITHHELD_FORM`). Not checked further here.

### What the code doesn't show

- **The fixtures' node lists and the browser's differ in two harmless ways.** F1's and F4's fields stand inside
  `<label>` elements, so the reader sends a `text` node around each (`["Line 0 ", 3]`, the run with its space);
  `view_fixtures.f4()` has the fields directly under the form. I checked in Python that both forms render to the
  same outline character for character (F1 normal and `full`, F4 `full`). Group 16 should compare outlines, not
  node lists.
- **`f4()`'s nodes 23 and 24 can't come from one page:** it has readable fields and two fields of unknown history
  side by side. In Claude's own tab F4's `Code` and `Nickname` are read; in a document that isn't watched no
  typed field is. Only the late shadow root could mix them, and F4 has none.
- **A field's error text stands once:** an element that `aria-errormessage` or `aria-describedby` of an invalid
  field points to gets no node and adds no text (`f4()` has it only as the field's `error`).
- **The outline leaves nothing in brief 20's `trace`:** it reads values with `safeValue(element, false)` and
  resets the trace list to its length at entry (`name()` of a button input reads through the traced path).
- **Names:** `name(element, fromContent)`: the outline names only controls by their content (link, button,
  checkbox, radio, switch, tab, the menu items, option, treeitem). Brief 20's rule, which names every element
  with a `role` attribute by its whole text, would put a page's text into the name of `<div role="main">`.
  Brief 20's own callers pass nothing and get the old rule.
- **A `role` attribute can't claim** `password`, `frame`, `text`, `p` or `h1` to `h6`: the reader gives those
  itself. `role="password"` on a container would make `nodes.View` refuse the whole reply.
- **Depth:** `visit` and `emit` recurse; a page nested thousands of levels deep overflows the stack and its
  read fails (closed). Brief 20's `text()` recurses the same way.
- **The late shadow root, as I would build it:** `privacy.metRoots` and `privacy.lateFields` (weak sets, kept
  across a reinstall); `meet(root)` where `roots()` and `remember()` find a shadow root: a typed field in it
  that is already filled goes into `lateFields`; `safeValue` treats `lateFields.has(element)` like `!watched`.
  It changes brief 20's reads of prefilled fields in components (exception 2), so brief 20's shadow-root tests
  will need the harness map. Its own commit, so a red run can be told apart.

### Local checks

```
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_efficiency
Ran 13 tests in 0.008s
OK
```

No JavaScript ran. The new block's brackets balance (counted with a script); that is all.

### JUDGMENT-CALLs (technical; for the lead)

1. **The baseline's digest test.** Any edit of the frozen numbers fails a test; adding to `latency_comparisons`
   doesn't. Rejected: trusting review alone. Changing it: one line.
2. **The error text once** (above). Rejected: sending it as text too, which `f4()` doesn't show and which says
   the same sentence twice.
3. **The credential words, not built, because it needs a decision first.** The brief's list has bare `token`,
   `seed`, `mnemonic` and the `key`/`phrase` pairs; the merged list leaves `token` out for hidden fields. My
   advice: keep the merged expressions, add the brief's list as data (Python module and reader copy), let either
   one make a field password-kind, and apply the new list only to fields a person types into (not
   `type="hidden"`), as the brief words it. Only stricter, and no CSRF field is withheld.
4. **Roles a page can't claim** and **names by content only for controls** (above): both keep page text out of
   places the tool writes.

### PLAN-GAPs

- Group 16's "the browser fixtures must give the node lists of `view_fixtures.py`" can hold only for the
  rendered outline (labels, spaces), and not for `f4()`'s two unknown-history fields.
- The brief's late-shadow-root rule also covers a component whose template prefills a field (a default value):
  it is filled when its root is first met, so it stays `(filled, not read)`. Built as worded, that is the cost.

## Step 4 (2026-11-15, Claude agent on Opus 5.5): run 43698395453's F4 failure. Fixed, new run started

Step 3's "Left" item 1. No reader, adapter or tool change; the latency gate, `latency-targets.json`, the sample
counts and the pair loop are untouched (that run's "Require lead ceilings" step was green).

### The cause (run 43698395453, artifact `chrome-efficiency-43698395453-1`)

Everything was green but the new step; the probe stopped in F4's warm-up with `Error: F4 received once: undefined`.
That message hid the real failure. `efficiency-calls.jsonl` shows F4's calls `read`, `fill_form` (6 fields,
`remaining` 0), `find` "Save" (found, `submit: true`), then `click` on Save answered
`{"ok":false,"error":{"code":"asking_input_too_large","message":"The whole approval exceeds 16384 bytes; prepare a
smaller operation. Nothing was reserved."}}`. The task's own assertion threw, and the receiver check in `after`,
run in `finally`, threw its own error over it (`efficiency-tasks.jsonl`: tools `read,fill_form,find,click`, no
`submit`; `receiver.jsonl` holds only group 1's compose send).

Why: brief 20's `chrome_submit` approval puts the whole binding in its description (`adapter.py` `prepare`:
`untrusted_content.page_state`), and the binding carries the form's facts (`binding()` → `frame['form']`), where
`reader.js` `field()` lists every option of a select. F4's Country has 200 options, as brief 28 and
`view_fixtures.py` define it: those options alone are 14,380 bytes of canonical JSON, against `ASK_LIMIT` 16 KiB
(`common.py` `approval_input`). So **brief 20's tools can't send F4 at all**: pressing Enter in a field builds the
same binding. The fake service in `efficiency.test.mjs` had answered the click with an approval, which is why the
fixtures jobs were green.

### The fix (`c99cf22a`)

Two mistakes, both in the probe (the check was wrong, not the tools or the fixture):
- **F4's row records what brief 20 does:** plan `read, fill_form, find, find*, click`; the click must end in
  `asking_input_too_large` (any other result, success included, fails the task); `after` checks the receiver got
  nothing. `call(action,args,{refusal})` marks such a call `expected_refusal` in the record.
  `efficiency-summary.py` accepts a failed call only with that mark and that code, requires every measured run to
  end the same way, and gives each task `outcome` (`done` or `refused`) and `refusals`.
- **A failed run is reported as itself:** `after` still runs after a failed run (cleanup), but its error is only
  logged then, so the run's error is what the step prints.
- Tests: `efficiency.test.mjs`'s fake now refuses F4's Save as brief 20 does and has no `submit`; a new test checks
  that F4 fails when the click succeeds, when the receiver got something, and that a failing `fill_form` is
  reported over a failing `after` (this run's case). `test_efficiency.py` checks the summary's refusal handling
  (accepted, wrong code, unexpected, one run ending differently).

### The other tasks, read again for the same mistake

The warm-up passed for `f1_first_read`, `f1_everything` (14 reads), `f1_fields`, `f2_table` (53 reads, 12.2 s),
`f3_find_link` and `open_fact` (its `after` closed the tab). For the tasks that never ran I checked each assumption
the fake makes against brief 20's code: F7's "Next page" is a link with an `href`, and F5's "Refresh rows" a
`type=button` outside any form; neither name holds a word of `policy.py`'s DELETE/PAY/ITEM/SEND lists and the
mode isn't conservative (the same run's `chrome-latency-…-current-plain` `tool.jsonl`: 180 "Continue" clicks
answered without an approval), so both clicks are free; F5's handler only changes
text, so it produces no page step and no `followups`; `wait` returns `condition_met`, `untrusted_content.title`
and `tree` (open_fact's record); `chrome_tabs`'s `limit` maximum is 10 (`definitions.py` `PAGE`), its reply is
`items`/`cursor` over every Chrome tab, and the probe opens tabs until 25 are listed; `navigate` with
`discard_unsaved: true` returns before the unsaved check, so F4's filled fields don't stop the next task. Nothing
else changed. The JavaScript still hasn't run outside CI (no Node on the laptop); I read it twice.

### The run (head `c99cf22a`, pull_request), not watched

| Workflow | Run id |
|---|---|
| Control Chrome | 43705060936 |
| Control Chrome qualification | 43705060865 |
| Control boundary | 43705060858 |
| Control base | 43705060866 |
| Control Mail | 43705060879 |

### Left, in order

1. Read run 43705060936: the latency job's plain leg ("Efficiency tasks with brief 20's tools", artifact
   `chrome-efficiency-43705060936-1`) and the fixtures jobs (`node --test`, including the new test). Fix what
   fails, as before; a red "Require lead ceilings" is the gate's own result (stop and report).
2. **The lead confirms F4's row (JUDGMENT-CALL below) before the baseline is committed**, since the file is frozen
   afterwards.
3. Commit the green run's `efficiency-measured.json` as `control/chrome/ci/efficiency-baseline.json`, and a test
   that it holds every task of `TASKS` with the same plan and outcome.
4. Then step 1b's list: the reader, the adapter, time, groups 14 and 16 in CI.

### Local checks

```
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_efficiency
Ran 9 tests in 0.007s
OK
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_efficiency test_latency
Ran 43 tests in 5.111s
OK
```

### JUDGMENT-CALL (technical; for the lead)

1. **F4's baseline row is brief 20's refusal**, not a send: 4 calls, the characters up to and including the
   refusal, outcome `refused`. Brief 28 asks for brief 20's tools "as they are, used as well as they allow", and
   they allow no send of F4. Rejected: a Country list of 50 options (brief 28 fixes 200, and brief 28a says the
   fixture isn't made smaller to fit); changing what brief 20's approval carries (a tool change in the baseline
   step, and approval content is security-relevant). Changing it later: a fixture or tool change before the
   baseline is committed costs one more run; afterwards the frozen file would need the lead's exception.

### PLAN-GAPs (for brief 28a)

- **F4's send will hit the same limit.** Brief 28a's F4 row expects `chrome_do` (six fills and the click), then
  `chrome_submit`, "one question; the receiver has it once". If the new tools' approval still carries brief 20's
  binding with every option of every select, the click is refused exactly as here. 28a needs a bounded form
  description in the approval (for example the chosen option and the option count, as the new read shows them),
  or the row can't pass.
- **28a's old-against-new timing of "filling 6 fields and sending the form"** has no old send to time: brief 20's
  side is the six fills and a refused click.

## Step 3 (2026-11-15, Claude agent on Opus 5.5): main merged, the probe wired in, draft PR open. Runs started

Step 2's "Left, in order" items 1 to 3. No reader, adapter or tool change; the latency gate is unchanged.

### Done

- **Main merged** (`d23a5e00`, a merge commit, no conflicts): #68 (`bdc16064`) is in, with its `--tmpfs /scratch`.
- **`latency-pair.sh`** (`dceafc94`): the docker command is one function, `latency_container <revision> <out>
  [extra options]`, which the pair loop and the probe both call. The loop is otherwise as it was; with a stubbed
  `docker` the pair's arguments are byte for byte main's. New mode `latency-pair.sh efficiency` (no argument, or
  `pair`, is the old loop; anything else exits 64): requires `LATENCY_PRIVACY=plain` and the image
  `aresos-latency-current` the pair built, runs it once more with `-e EFFICIENCY_PROBE=true -e ImageOS -e
  ImageVersion -e RUNNER_ENVIRONMENT -e RUNNER_ARCH` into `.work/latency-out/efficiency`, then
  `efficiency-summary.py` writes `efficiency-measured.json` there.
- **`control-chrome.yml`, latency job** (`9cd255ac`): the pair step got `id: pair`; a new step "Efficiency tasks
  with brief 20's tools" right after "Require lead ceilings", `if: !cancelled() && !inputs.latency_probe &&
  matrix.privacy == 'plain' && steps.pair.outcome == 'success'`; an upload of `.work/latency-out/efficiency/` as
  `chrome-efficiency-<run>-<attempt>`, `if: always() && matrix.privacy == 'plain'`, 14 days.
- **Tests:** `test_efficiency.EfficiencyWiringTest` (2 tests) pins one `docker run` in the script, both modes'
  calls, the probe's options before the mount, the step's place after the gate, its condition, and the upload.
  Both fail against the files before this step (one failure, one error) and pass now.
- **Draft PR #72** (https://github.com/Ares-Empire/AresOS/pull/72), "Package 28: Chrome read (in progress)".

### The runs (head `9cd255ac`, pull_request), not watched

| Workflow | Run id |
|---|---|
| Control Chrome (the latency job's plain leg makes `efficiency-measured.json`; the fixtures jobs run `efficiency.test.mjs`) | 43698395453 |
| Control Chrome qualification | 43698395347 |
| Control boundary | 43698395354 |
| Control base | 43698395362 |
| Control Mail | 43698395365 |

Read them with `gh run view <id> --json jobs` (no watching; if you must, `--interval 120`). The baseline is in the
artifact `chrome-efficiency-43698395453-1` (`efficiency-measured.json`, plus every call's whole result in
`efficiency-calls.jsonl`, `browser.txt` for a failing task). This is the first run of `efficiency.test.mjs`, the
fixtures and the probe: JavaScript errors are likely and are fixed in the next step.

### Left, in order

1. Read run 43698395453: the latency job's plain leg ("Efficiency tasks with brief 20's tools") and the fixtures
   jobs (`node --test`). Fix what fails; a red "Require lead ceilings" is the latency gate's own result and is not
   fixed by touching the ceilings, samples or `latency-targets.json` (stop and report instead).
2. Commit the green run's `efficiency-measured.json` as `control/chrome/ci/efficiency-baseline.json` (it carries
   the run id, the runner and the sizes), and a test that it holds every task of `TASKS` with the same plan. It is
   edited afterwards only to add `latency_comparisons` (brief 28's F1 comparison, brief 28a's).
3. Then step 1b's list: the reader, the adapter, time, groups 14 and 16 in CI.

### What the code doesn't show

- **When the probe runs:** also after a red latency gate (the pair built the image, so the counts are still
  worth having, and the gate's own step stays red), never after a cancel, a failed pair or in a `latency_probe`
  dispatch (that dispatch is "paired call histories only"). The audit leg neither runs nor uploads it.
- **The probe's container is a latency container:** `LATENCY_PROBE=true` (from the shared function) means `run.sh`
  skips its in-container unit tests, puts the service's logs on `/scratch`, and `prepare.mjs` adds the latency
  timing wrappers to the reader and background, as for the samples. The wrappers time and send side messages;
  they don't change a result, so the counted characters are the tools' own. The timings carry the same small
  overhead as the latency samples, which suits the later side-by-side comparison in the same container.
- **On a failing task** `run.sh` stops before copying `service.txt` and `browser-boundary.jsonl` from `/scratch`,
  so those two are missing then; `efficiency-calls.jsonl`, `efficiency-tasks.jsonl` and `browser.txt` are written
  to `/out` directly and are uploaded.
- **Time:** the pair took about 13 minutes on a recent green run (43687610984); the probe's container is one more
  build-free run of the same image under the same 50-minute `timeout`, inside the job's 120 minutes.
- **Pushes start nothing on this branch** (no workflow pushes on `pkg/28-chrome`); the pull request does. A
  commit whose subject holds `[skip ci]`, or one touching only `reviews/28-chrome-read/`, starts no run.

### Local checks

```
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_efficiency
Ran 8 tests in 0.008s
OK
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_efficiency test_latency test_qualification
Ran 73 tests in 7.038s
OK
```

`test_latency` holds the text check of #68's docker options; `test_qualification` parses both workflows' steps and
conditions (no ref marker in the new condition). `bash -n` passes; with `GITHUB_ACTIONS=true` an unknown mode exits
64 and `efficiency` with `LATENCY_PRIVACY=audit` exits 1 before any docker call. No Node on the laptop, so no
JavaScript ran here.

### JUDGMENT-CALLs (technical; for the lead)

1. **The probe also runs after a red gate** (see above). The alternative, running it only after a green gate,
   would lose the baseline to a slow runner without making anything safer: the gate's step is red either way.
2. **Not in a `latency_probe` dispatch**, so that mode stays the pair alone, as its description says.

## Step 2 (2026-11-15, Claude agent on Opus 5.5): the baseline. Built, not yet run in CI

**Stopped as told:** PR #68 (`mac-aresos-control`, green main) was still open at 06:29 UTC after a three-hour wait,
and it changes `latency-pair.sh`, `run.sh` and `control-chrome.yml`, where the probe still has to be wired in. No
`control-chrome` run used (0 of 6); no draft PR opened yet, because opening it starts a run on red main.

Brief 28, "Before anything else", and group 16's first half: the fixtures, the scripted tasks with brief 20's
tools, and `control/chrome/ci/efficiency-baseline.json` from a CI run. No reader, adapter or tool change.

### Built

- `control/chrome/ci/efficiency-fixtures.mjs`, served by `fixture.mjs` as `/?case=efficiency-<name>`: F1 (the
  same body as brief 20's long page, `case=matrix&mode=long`; a test compares them as served), F2, F3 and F4 as
  `view_fixtures.py`'s node lists describe them, F5 (a free click changing 8 lines; `mode=load` loads the next
  document), F7 (result pages with a "Next page" link) and the pages of "list 25 tabs" (titles of 29 characters).
  F6 and H1 are group 14's alone and are left to the reader step.
- `control/chrome/ci/efficiency-probe.mjs`: the tasks, each with the exact calls it may make (`plan`), run once
  as a warm-up and five times measured, every call's whole result recorded. Setup calls (navigation, the "first
  read" a row starts after, opening the tabs) are neither counted nor timed.
- `control/chrome/ci/efficiency-summary.py`: characters as the MCP proxy hands a result to Claude
  (`display_json(bound_result(result))`, `proxy.serve`), calls and tools equal in every measured run or it
  fails, wall time the median of the five, the catalogue's sizes (`tools_for`/`instructions_for`).
- `browser.mjs` runs the probe instead of the latency samples when `EFFICIENCY_PROBE=true` (one line).
- Tests: `control/chrome_tests/efficiency.test.mjs` (fixtures as served, the tasks against a fake service:
  every task makes exactly its plan) and `test_efficiency.py` (the counting).

### The tasks (brief 20's tools, used as well as they allow)

| Task | Calls |
|---|---|
| `f1_first_read` | `read` |
| `f1_everything` | `read`, then `read` with each cursor |
| `f1_fields` (after the first read) | `find` "Field 0" (with cursors until the field's row), `read_form` with its reference |
| `f2_table` (after the first read) | `read` with each cursor the first read left |
| `f3_find_link` | `find` the unique name (with cursors until the link's row; brief 20's find has no `role`) |
| `open_fact` | `open` F7 page 1, `wait` for its heading (`timeout_ms` 8000) |
| `f4_fill_send` | `read`, `fill_form` (6 fields), `find` "Save", `click`, `submit` |
| `f7_three_pages` (page 1's read in hand) | `click` "Next page", `wait` for the next heading; three times |
| `f5_free_click` (its read in hand) | `click` "Refresh rows", `read` |
| `three_tabs` (F1, F2, F3 open) | `read` each tab once |
| `list_25_tabs` | `tabs` with `limit` 10 and its cursors |

### Left, in order

1. When PR #68 has merged: `git merge origin/main` (a merge commit).
2. Wire the probe into the latency harness (files #68 touches, so only after the merge):
   - `latency-pair.sh`: after the loop, when `LATENCY_PRIVACY` is `plain`, run the image `aresos-latency-current`
     once more with the loop's docker options (as merged, with #68's `--tmpfs /scratch`) plus
     `-e EFFICIENCY_PROBE=true -e LATENCY_BASELINE=current -e ImageOS -e ImageVersion -e RUNNER_ENVIRONMENT
     -e RUNNER_ARCH`, writing to `.work/latency-out/efficiency`, then
     `python3 control/chrome/ci/efficiency-summary.py .work/latency-out/efficiency`. Put the docker command in one
     shell function both use, so the options can't drift. My advice: make it a mode of the script
     (`latency-pair.sh efficiency`) and a separate step after "Require lead ceilings", so a failing task can't hide
     the latency gate's result.
   - `control-chrome.yml`, latency job: that step (`matrix.privacy == 'plain'`) and an upload of
     `.work/latency-out/efficiency/` as `chrome-efficiency-<run>-<attempt>`.
3. Open the draft PR (`pkg/28-chrome` to `main`, "Package 28: Chrome read (in progress)"); its first run checks
   `efficiency.test.mjs` (the fixtures jobs run `node --test`) and produces `efficiency-measured.json`.
4. Commit that file as `control/chrome/ci/efficiency-baseline.json` (it carries the run id, the runner and the
   sizes), and a test that it holds every task of `TASKS` with the same plan. It is edited afterwards only to add
   `latency_comparisons` (brief 28's F1 comparison, brief 28a's).
5. Then step 1b's list: the reader, the adapter, time, groups 14 and 16 in CI.

### What the code doesn't show

- **The run's place.** The probe runs in its own container of the current runtime in the latency job's plain leg:
  the same image, `browser.mjs` and runner as the latency samples (one harness), no audit recording, and a fresh
  service, so the latency gate's "fresh" phase is untouched by the tasks' history. The later side-by-side timing
  (brief 28: F1's first read, old and new) belongs in the same container run.
- **Characters** are the median of the five measured runs; they differ by a few characters between runs as
  reference ids grow. Every run's total and the median per call are kept.
- **Sizes** measured locally on this head (they come again from the CI run): 30 tools, descriptions 5,085 plus
  instructions 4,052 = 9,137; names plus input schemas 11,080 (each tool's name plus its schema as compact JSON;
  the method brief 28a's numbers match).
- **Local checks:** `PYTHONPATH=control:control/chrome_tests python3 -m unittest test_efficiency`: 6 tests OK.
  The laptop has no Node or other JavaScript runtime, so `efficiency.test.mjs` and the JavaScript files have not
  run yet (read twice by hand); the first CI run is their first run.

### JUDGMENT-CALLs (technical; for the lead)

1. **The baseline also holds brief 28a's acting rows** (open and a fact, F4's six fields and send, F7's three pages,
   F5's free click, 25 tabs). Brief 28's own table names only the read rows, but brief 28a fails a number "worse than
   the baseline" for every row, and the file is frozen after this step. Brief 28b's row (his tab) isn't measured:
   its acceptance asks only for two calls and an untouched tab.
2. **"Compare three open tabs" is one `read` per tab** (its first page), not each tab paged to its end as the design
   table's middle column says. The new read's `tabs` returns one outline per tab, not every page, so the first page
   is the fair counterpart, and it is the smaller baseline, which flatters nothing.
3. **"After the first read"**: that read is setup, neither counted nor timed, as the new rows count "1 further
   call". F1's fields are `find` plus `read_form` (2 calls), better than the design's "inside the 14 pages".
4. **F4** has `novalidate`, so the invalid Email with its error text doesn't stop the send; the task fills Line 0 to
   Line 5, which are on the read's first page. **F7** serves any page number; the task starts with page 1's read
   in hand and its three clicks reach pages 2, 3 and 4.

### PLAN-GAPs

- Group 14's fixture list says this package adds F1 to F7 and H1 "because the baseline needs them". The baseline
  needs F1 to F5 and F7; F6 (frames, shadow roots) and H1 (hostile text) are group 14's alone and are left to the
  reader step.


## Step 1b (2026-11-14, Claude agent on Opus 5.5): the lead's decisions in the view module. Done.

Section 7 of the brief ("The lead's decisions after step 1") built into the view module. Only files that step 1
added were edited; nothing of PR #27's. Pure Python, no browser.

### The decisions as built, and the tests that pin them

Each new or changed test below was run against the module as it was before its decision (a copy outside the
repository, from `git show`): every one of them fails there and passes now.

| # | Decision | Built in | Pinned by |
|---|---|---|---|
| 1 | A list item with one element and nothing of its own gets no line; the element moves up a level | `view._bare_item`, used in `_arrange` | `test_view_outline`: `test_a_list_item_that_holds_one_element_alone_gives_its_place_to_it`, `test_elements_moved_up_from_list_items_fold_as_neighbours`, `test_the_example_page_character_for_character` (section 6's example now has no `listitem` lines); `test_view_budgets`: `test_f3_read_in_full`, `test_compare_three_open_tabs_is_one_call` |
| 2 | A `find` path names the named ancestors and, also unnamed, `main`, `navigation`, `banner`, `contentinfo`, `complementary`, `form`, `dialog`, `table`; at most 80 characters | `view.PATH_ROLES`, `_path` | `test_the_path_names_the_landmarks_also_without_a_name` (each of the eight, and twelve roles that stay out); `test_a_hit_is_the_elements_line_and_the_path_of_named_ancestors` (`· in main › list "Results"`, `· in contentinfo`), `test_role_keeps_only_that_role_and_must_be_one`, `test_folded_parts_frames_values_and_cells_are_searched`; `test_f3_the_one_link_with_the_unique_name` |
| 3 | Nine states | nothing to build: `nodes.STATES` holds the nine | `test_states_stand_in_one_order_after_the_value` (all nine, in order) |
| 4 | Node ids are positive integers | nothing to build: already the contract; now also written in `nodes.py`'s docstring | `test_view_nodes.test_a_node_and_its_place` (`0`, `-1`, `"e5"`, `True`, `1.5`, `None` refused) |
| 5 | An inline part carries its value and the states that are set, in the line's order, before the reference | `view._inline`, with `_unread` and `_states` split out of `_marks`; `_fit` | `test_an_inline_part_carries_its_value_and_states_before_its_reference` (sentence and table cell; checkbox, textbox, link, the unread forms), `test_an_inline_parts_value_counts_toward_the_cut`; `Unread.test_the_outline_a_form_by_reference_and_full` (`[password "OTP" (not read) kqtvm9]`) |
| 6 | Inline formatting is text: runs in order, only links and controls between them; `find` and `until` match the joined text, each inline part with its name | `view._ordered` (joins runs side by side), `_joined`, `_match`; the contract in `nodes.py`'s docstring and in "What the reader's `outline` must deliver" below | `test_inline_formatting_is_text_of_its_parent`, `test_find_and_until_match_across_an_inline_part_by_its_name` |
| 7 | A run of 20 or more letters, digits, `-` and `_` with a digit, an upper- and a lower-case letter looks random | `address._TOKEN_RUN`, `looks_random` | `test_view_address.test_a_long_token_with_separators_looks_random_and_a_slug_does_not`: a 43-character base64url token with `-` and `_` under `?ordinary=` (hidden; the old rule's runs are each under 20), a lower-case slug with dashes and digits (shown), `dQw4w9WgXcQ` (shown), a UUID (hidden), the edges |
| 8 | A page that ends before a line longer than `max` may hold only the short line; it always advances | nothing to build | `test_view_paging.test_a_line_that_does_not_fit_is_continued_inside_it` (the first page is `short\n` alone) |
| 9 | A sign-in word of five letters or more counts anywhere inside a segment; `auth`, `sso`, `saml`, `otp` only as a part of their own | `address.SIGN_IN_INSIDE`, `sign_in_segment` | `test_a_long_sign_in_word_counts_inside_a_segment` (`/resetpassword/abc12` hidden after; each long word inside a segment, in upper case, percent-encoded), `test_a_short_sign_in_word_counts_only_as_a_part_of_its_own` (`/classroom/maths/` and `/author/jane-doe` shown, `/auth/xyz` hidden after) |

**The hostile tests** cover what the decisions join or move: the hostile page gained a list item that holds one
hostile link (moved up, decision 1), an inline field with a hostile value and two states in a sentence and an
inline checkbox with a hostile name and a state in a table cell (decision 5), runs side by side with a hostile one
among them and a hit across a link in a long hostile text (decision 6; two `find` reads more, 27 reads a page). Every
read is still its harmless twin outside the quotes. The path pattern of that test now allows a landmark's role
alone (decision 2).

### What I decided where section 7 left room

1. **Decision 1:** an item with a **name**, a **value** or a **state** (`listitem current` in a breadcrumb) keeps
   its line too, so nothing it says is lost. An item's white space alone isn't text. A role-less wrapper inside
   the item gives way first, so `<li><div><a>` moves the link up. An item whose one element is a `text` element
   (`<li><div>Apples</div></li>`) gives way to it as well: `text "Apples"` stands in the list. With decision 6
   `<li><b>Apples</b></li>` is the item's own text and keeps `listitem "Apples"`.
2. **Decision 2:** `grid` isn't on the list, so an unnamed grid isn't named (the list is taken as written).
3. **Decision 5:** the form of a value that isn't read (`(not read)`, `(filled, not read)`, `(empty)`) is what the
   grammar puts in the value's place, so an inline part carries it; without it an inline field typed into would
   look empty. A link's target (`→ other.example`) and the counts `(N options)` aren't carried: the decision
   names the value and the states. **The value counts toward the 200-character cut with the name**, and a part is
   kept or left out whole, so a long inline value can't make a line long: it moves the part to the element's
   reference, as for a long name.
4. **Decision 6:** the joined text is cut into **stretches at children with a line of their own** (an `h3` between
   two runs), so "Before  after" isn't found across a heading. A control's value isn't part of the joined text
   (the decision names the name). **A word inside an inline part's name is now two hits**: the sentence (its joined
   text holds the word) and the link itself (`find="timetable"` returns the `p` and the `link`). That is what the
   rule gives; the reader of the hits sees both lines, each with its reference.
5. **A bug of step 1 fixed on the way:** a path that didn't fit whole got its leading `…` after the 80 characters
   were counted, so nine bare `dialog`s made 82. The mark now counts toward the 80 (pinned in
   `test_the_path_names_the_landmarks_also_without_a_name`).

### What the two address rules now also hide (the safe direction, for the lead to know)

Measured with `public_address`; Claude still opens such a link by its reference.

- Decision 9, a long word inside another word: `/presets/list` (holds *reset*), `/designing-apps/part-2`
  (*signin*), `/blogindex/2026` (*login*), `/tokens/list`, `/magical/place`, `/invites/42`, `/confirmation/x`: the
  rest of the path after that segment is `…`. Step 1's tests expected `/tokens/list` and `/magical/place` shown;
  they now expect them hidden, as the decision says.
- Decision 7: a slug in mixed case with a digit is a token: `/Some-Product-Name-2026` and
  `/sort_by_price_2026_Desc_Order` are `…`. A lower-case slug stays.

### Budgets (brief 28, "Group 16"; fixtures as node lists; characters of the JSON text of the result)

| Row | Budget | Brief's worked numbers (outline / as sent) | Step 1 (calls, outline, as sent) | Step 1b (calls, outline, as sent) |
|---|---|---|---|---|
| F1, the first read | 1 call, 6,000 | about 3,300 / 3,900 | 1 call, 3,258 / 3,833 | 1 call, 3,258 / 3,833 |
| F1, everything (`full`, `max` 40,000, cursors) | 3 calls, 75,000 | about 60,100 / 61,500, 2 pages | 2 calls, 59,020 / 60,462 | 2 calls, 59,020 / 60,462 |
| F1, the 80 fields (form by `ref`) | 1 further call, 6,000 | about 4,250 / 4,950 | 1 call, 4,176 / 4,899 | 1 call, 4,176 / 4,899 |
| F2, the whole table (`ref`, `max` 40,000) | 1 further call, 23,600 | about 20,100 / 23,050 | 1 call, 20,129 / 23,066 | 1 call, 20,129 / 23,066 |
| F3, the one link (`find` and `role`) | 1 call, 800 | about 100 / 420 | 1 call, 56 / 385 | 1 call, 63 / 397 (the path gained `main ›`) |
| Three tabs (F1, F2, F3) with `tabs` | 1 call | | 1 call, 4,945 as sent | 1 call, 4,865 as sent |
| F3 read in full (`full`, `max` 40,000; no budget row) | | | 1 call, 18,484 / | 1 call, 13,984 / 15,253 |

Every row is met. F3 read in full is 4,500 characters smaller, the cost section 7 named for decision 1 (a
`listitem` line and two spaces of indentation for each of 300 items). A result still has 318 characters around
its outline. No stop rule was hit.

### What I ran and what it printed

```
$ cd /var/home/ares/AresOS-28-chrome-read
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_view_address \
    test_view_nodes test_view_references test_view_outline test_view_paging test_view_hostile test_view_budgets
...........................................................................................................................................
----------------------------------------------------------------------
Ran 139 tests in 3.725s

OK
```

139 tests (step 1: 129): address 19, nodes 13, references 20, outline 47, paging 23, hostile 9, budgets 8. No
other suite, no browser. No literal direction-changing or line-separator character in any file of the view
module (checked with `grep -P`). The token-shaped test value of decision 7 is built at run time with `made()`.

### Left, in order (the next steps)

1. The baseline ("Before anything else"): fixtures of group 16 on the fixture server, the scripted tasks with
   brief 20's tools, `efficiency-baseline.json` from a CI run. Needs PR #27 merged.
2. **The reader** (after PR #27 merges): `outline`, `options` and `page_state` in `reader.js` and `background.js`,
   with item 1's password additions, the credential words module, the reader instance; Node tests in the VM
   doubles. It sends exactly "What the reader's `outline` must deliver" below: integer ids (decision 4), and
   inline formatting as text runs with only links and controls between them (decision 6). The browser fixtures of
   group 16 must give the node lists of `view_fixtures.py`.
3. The adapter: `chrome_outline` behind the test-only switch, `until` (with `view.contains`, which now matches
   joined text), `tabs`, the refusal in `payload` and `steps` (exception 4), using the functions of step 1.
4. Time: the deadline through `Bridge.call` and `dispatch`.
5. Browser groups 14 and 16 in CI, the latency comparison, the harness map, the known limits and the report.

### Commits of step 1b

- `7a62d0f6` Chrome read: a token with separators looks random; long sign-in words count inside a segment (7, 9)
- `df969714` Chrome read: a list item that holds one element alone gets no line (1)
- `47d5cec3` Chrome read: a find hit's path names the landmarks also without a name (2)
- `d5b41153` Chrome read: an inline part carries its value and its states (5)
- `9c46dbe6` Chrome read: inline formatting is text, and find reads across a link (6)
- this file

## Step 1 (2026-11-14, Claude agent on Fable 5.2): the service-side view module. Done.

Pure Python, standard library only, no browser, no extension code, no wiring. **New files only**; no existing
file was edited (the branch is cut from PR #27 at `524173c4`, which still moves).

### Done

| File | What it is |
|---|---|
| `control/aresos_control/chrome/address.py` | `public_address(address, short=False)`, `site_of`, `looks_random`, `credential_name`, `sign_in_segment`: brief 28 item 2's public and short form of an address. |
| `control/aresos_control/chrome/nodes.py` | The input contract: `View(reply)` checks the reader's `outline` reply and builds the tree; `options(list)` checks the reply of the `options` command; `Malformed` for anything else. The role list and the state list live here. |
| `control/aresos_control/chrome/references.py` | `References`: the run letters, the one counter, per-tab entries, the bound of 5,000, `Stale` (the refusal with the tool's own sentence and, where there is one, the element's present line). |
| `control/aresos_control/chrome/view.py` | `quoted`, the renderer (`render`), `find`, `contains`, the pages (`cut`, cursors), the result entries and the 48 KiB bound (`Reading`, `Failure`, `fit`), `typed_fields`, `header`, `present_line`, `fingerprint`. |
| `control/chrome_tests/view_fixtures.py` | F1, F2, F3 and F4 as node lists, and small helpers. |
| `control/chrome_tests/test_view_address.py` | 17 tests: the address table in both forms. |
| `control/chrome_tests/test_view_nodes.py` | 13 tests: the contract, each malformed reply, the bounds. |
| `control/chrome_tests/test_view_references.py` | 20 tests: letters, counter, bound, every stale case, 300 runs, two runs with the same letters, the fingerprint apart from the line. |
| `control/chrome_tests/test_view_outline.py` | 40 tests: stored outlines character for character, every role, folds and their order, counts against `full`, reads by reference, `full`, `find`, the unread forms. |
| `control/chrome_tests/test_view_paging.py` | 23 tests: `cut`, cursors, 100,000 characters, a wide row, a long value, 48 KiB with non-ASCII text and quotes, five tabs. |
| `control/chrome_tests/test_view_hostile.py` | 9 tests: H1's hostile strings in every place, hostile roles, addresses with a marker, the refusal. |
| `control/chrome_tests/test_view_budgets.py` | 7 tests: brief 28's read rows on F1, F2 and F3. |

**Which workflow picks the tests up:** `.github/workflows/control-chrome.yml`, job `python-shards`. It runs
`control/chrome/ci/python-shard.py`, which loads every `control/chrome_tests/test_*.py` in four shards, and
`merge-python.py` requires every such module to have run. Nothing in a workflow has to change. With today's file
list the seven modules land in shards 2, 3, 0, 1, 2, 3, 0. They start no browser and no service and take under 5
seconds together. The branch push triggers no workflow (checked: `control-chrome.yml` runs on pushes to
`pkg/20-chrome*` and `main` and on pull requests only). No pull request was opened.

**The build hash changes** (`control/chrome/build.py` hashes every file under `aresos_control/`), as the brief says
it will. Nothing else of the qualification record is touched.

### What the adapter will call (next step)

```python
from aresos_control.chrome import nodes, view
from aresos_control.chrome.references import References, Stale

references = References()            # once per service process; draws the five letters; no store
references.close(tab)                # when a tab closes (entries dropped; the counter goes on)

shown = nodes.View(reply)            # raises nodes.Malformed (a ValueError); message holds no page text
every = nodes.options(reply)         # the `options` command's reply, for render(options=...)

text = view.render(shown, references, ref=None, full=False, find=None, role=None, options=None)
        # -> view.Text (.text: the whole text of the query; .marks)
        # raises Stale (code stale_reference; .line = present line or None)
        #        Refused("invalid_input") for a role that isn't on the list
        # calls references.connect(shown.session) itself: another session empties the table

query = view.asked(ref=None, find=None, role=None, full=False)
reading = view.Reading(shown, text, token, query, cursor=None, limit=6000, whose="claude", until_met=None)
        # token: page_state's token. Raises Refused("invalid_input") for a cursor of another query or a
        # malformed one, Refused("stale_reference", "The page changed; read again without the cursor.")
failure = view.Failure(tab, error)   # a tab that couldn't be read; error is a Refused or a Stale

reads = view.fit([reading_or_failure, ...], measure, references)
        # measure(reads) -> bytes of the complete result as sent, with these entries in it: the adapter's
        # closure over ok/data/version_notice/pending. Raises Refused("result_too_large") when the fixed
        # parts leave under 64 bytes a tab. Calls references.returned() for what each page showed.

view.contains(shown, words)          # for `until`: as find would find it; issues no reference
view.typed_fields(shown)             # already inside each entry
view.present_line(shown, references, node)   # for brief 28a's stale refusals
view.fingerprint(node)               # stored per shown reference, in Entry.fingerprint; no action uses it yet
address.public_address(address, short=False)
```

The adapter still has to do, around these: the tab checks of today's `read` (group, fixed list on the top
document and every frame, qualification mode, queued page steps), `until` with `page_state` polling and
`contains`, the deadlines, `tabs` (one `Reading` or `Failure` per tab, `limit` 3,000 by default), schema limits
(`find` 1 to 200 characters, `max` 1,000 to 40,000), and `whose`.

### What the reader's `outline` must deliver (next step; updated in step 1b for decisions 4 and 6)

The reply of one tab, as `nodes.View` accepts it. Keys the view doesn't use are ignored at the top and at the
frame level; a node is strict. `nodes.py`'s module docstring says the same.

```
{"session": str, "tab": int, "url": str, "title": str,
 "dialog": null | {"kind": str, "text": str},        # with a dialog: "frames": []
 "frames": [                                          # the top document first
   {"frame": int, "document": str, "reader": str,    # reader = the instance id drawn at each install
    "watched": bool, "url": str, "title": str, "scroll": int, "height": int, "omitted": int,
    "nodes": [node, ...]}]}                           # document order: a parent before its children

node: {"id": int >= 1, "parent": id | null, "role": str | null, "name": str,
       "text": [str | child id, ...], "value": str, "unread": true, "filled": bool, "error": str,
       "states": [state, ...], "href": str, "method": str, "action": str, "hidden": [str, ...],
       "option_count": int, "chosen": str, "options": [{"label", "value", "chosen", "disabled"}, ...],
       "title": str, "frame": int}                    # every key but id is optional; no other key
```

Rules the contract enforces (each refused with `Malformed` and tested):

- ids are positive integers (section 7, decision 4), unique in a frame; `parent` is an earlier node; `text`
  names only the node's own children, each once. The reader sends numbers and accepts them back (`options`,
  brief 28a's commands): a string id couldn't be told from a run of text.
- `unread` or role `password`: no `value`, no `text`, no `chosen`, no `options`, **and no child nodes**. `filled`
  only with `unread`. So a field that is kept out is a leaf that carries its label and nothing of its content.
- `states` only from the nine; `frame` only on role `frame`; each frame named at most once, never the top frame,
  never inside itself.
- at most 20,000 nodes a tab; at most 150 levels of nesting, frames included (the renderer recurses).

Rules the renderer relies on and can't check:

- **Text as displayed.** Runs come with white space collapsed as the page shows it and trimmed at the element's
  outer edges (`pre` keeps its breaks). The renderer prints a run as delivered; it only joins runs that stand
  next to each other, drops runs of nothing but space and trims inside table cells.
- **Inline formatting is text, not structure** (section 7, decision 6). `text` is the element's own text in the
  order of the page: text runs, with an inline part's id between two runs where it stands. An element without a
  role of its own from the list (`b`, `strong`, `i`, `em`, `code`, `span`, `small`, `mark`, `abbr`, `sub`, `sup`,
  `time`, `u`, `s`, `q`, `cite`, `kbd` and the like) **gets no node**: its text joins the run it stands in, at
  its place, with white space collapsed across its edges. What it holds that has a node (a link, a control) is a
  child of the nearest element that has a node, named in that element's `text` where it stands. Only links and
  controls stand between runs. Example: `<p>Order <b>confirmed</b> today, see <i>the <a>timetable</a></i>.</p>`
  is one node `{"id": 11, "role": "p", "text": ["Order confirmed today, see the ", 12, "."]}` and the link
  `{"id": 12, "parent": 11, "role": "link", "name": "timetable", ...}`. Runs side by side (`["Order ",
  "confirmed", " today"]`) read the same, so the reader may send the formatting's text as runs of its own. An
  element with a role from the list (`<span role="button">`) is a node as before, and any other element with text
  of its own (a `div`) is `text`.
- When an element has own text, `text` lists **every** child that has a node at its place, also a leading or
  trailing one. Children that `text` doesn't name are placed after the listed parts.
- `chosen` is the label of the chosen option; a list field's line shows it as the value. A native `select` sends
  `options` (first 50) and no `option` child nodes.
- A readable child frame is named by the `frame` node of its `iframe` element (`chrome.runtime.getFrameId`). A
  frame no node names is printed after the page as a `frame` line of its own.
- A role is delivered only from the list. The service treats anything else as no role (name or text then makes
  it `text`).

### Decisions the code doesn't show

1. **References are issued when a line is rendered, marked as shown when their page is returned, and the bound is
   applied only after that** (`References.returned`). Reason: a fold's count is the length of a `full` read of it,
   so the hidden elements get their references while counting; with a plain "newest 5,000" a page with many
   links would drop the references of the lines it is about to return. When a tab is over 5,000, entries that
   were never on a returned page go first (oldest first), then the entries shown longest ago; showing an
   element again counts as new. A dropped string is never issued again.
2. **A cursor binds the text returned so far**, besides the query and the state token: it holds a digest of the
   text before its position. Same token but another text (an element got a new reference after its old one was
   dropped) is refused as `stale_reference`, instead of going on at a wrong place. What comes after the cursor
   may differ.
3. **Pages join to the text exactly.** A page that ends at a line end includes the line break; `characters` of
   all pages add up to `total`.
4. **The fold count and the cut count measure different things.** `(N characters)` counts outline characters
   (escaped, as a `full` read returns them). `…+N` and the limit of 200 count characters of the page's own text
   before escaping. Numbers above 999 are written with commas, as in the brief's examples.
5. **The cut** (fold 5): name, runs, inline children's names and the value share the 200 characters, in that
   order; the mark `…+N` stands right after the last quoted piece, outside the quotes; everything after it
   (later runs, inline children, the value) is counted in N and left to the element's reference. Tool-written
   parts (the unread forms, states, target, reference) still follow.
6. **Text once.** When an element's name already says its plain text (own runs and children that are nothing
   but text, compared without white space), that text gets no line: `link "Open file"`, `button "Next week"`.
   A name that isn't the text keeps both: `button "Close" "×"`.
7. **A label** is recognised without a marker from the reader: an element with role `text` or none, no name,
   whose plain text equals the name of a field among its own children or its siblings. It gets no line and its
   field moves up.
8. **Detail lines.** The brief defines `columns:`. In the same style a read by reference adds `address:` (public
   form of a link's or a frame's address), `title:`, `error:` (a field's error text; also in `full`) and, for a
   form, `hidden:` with the names. An option is `option "Label"`, with ` = "value"` in the field's own read when
   the value differs, and `selected`/`disabled`. Options beyond those sent along are one line `… N more`.
9. **A read by reference always shows that reference** on its first line, also for a paragraph that normally
   has none.
10. **A table's rows are indented like the table's line**, so "not indented" holds for the table by reference;
    inside a `full` page read they stand under the table at the same depth. `grid` is read as a table too. The
    first row is the `columns:` line when all its cells are column headers; R doesn't count it.
11. **A form's 40 fields** are the first 40 fields of its subtree in the order of the page, wherever they stand
    (also inside a folded table). The fold line stands where the 41st would, or at the form's end when that
    place isn't rendered. Of nested forms only the outermost counts.
12. **Empty values aren't printed** (`textbox "Email"`, not `= ""`). `(empty)` is only for an unread typed
    field.
13. **Unread forms.** Role `password` always prints `(not read)`, also when the node says `filled`. Any other
    role with `unread`: `(filled, not read)`, `(empty)`, or `(not read)` when `filled` is absent (a field kept
    out by its name).
14. **What isn't a web address** shows its scheme at most: `mailto:…`, `javascript:…`, `…`.
15. **The header's `title` and a dialog's text** go through the base's `visible()`; they are JSON fields, not
    parts of a line, so they get no quotes of their own.
16. **A sign-in word in a path** matches as a part of the segment (split at separators, a change of case and
    digits) or as two neighbouring parts joined (`sign-in`, `log-in`). **A credential name** matches as a part,
    or as the start or end of a part (`apikey`, `sessionid`), as the brief says; so `?keyword=`, `?author=` and
    `?state=` are hidden too.
17. ~~`find` matches each element on its own name, its own text (runs joined) and its readable value. A match
    that spans an inline child (`See the <a>timetable</a>`) isn't found.~~ Replaced in step 1b by section 7's
    decision 6: the joined text with each inline part's name, in stretches between children with lines of their
    own.

### PLAN-GAPs (the brief taken in each; the lead decides)

All nine were decided in the brief's section 7 (2026-11-14) and built in step 1b; see its table. Kept here as
step 1 found them.

1. **Bare `listitem` lines.** Section 6's example shows links directly under `list`; the brief's rule gives every
   element with a role a line. Taken: the brief. Cost on F3 read in full: 4,500 of 18,484 characters (a
   `listitem` line and two more spaces for each of 300 items). Proposal: an element with a role but no name,
   text, value, state or reference, and exactly one child line, gets no line.
2. **The path of a `find` hit.** The brief: named ancestors only. Section 6's example (`main › list "Week 46"`)
   shows an unnamed `main`. Taken: the brief.
3. **States.** Section 6's sentence lists seven; the brief's grammar lists nine (`collapsed`, `readonly`). Taken:
   the brief's nine.
4. **Node ids.** Brief 20's reader ids are strings (`e12`); item 1's example writes a child in `text` as a
   number. A string id couldn't be told from a run of text, so the contract takes positive integers. The reader
   has to send numbers and accept them back (`options`, and brief 28a's commands).
5. **An inline part shows no value and no state** (the grammar: `[role "name" ref]`). A checkbox in a table cell
   or a sentence doesn't show `checked`; the element's own reference reads it. Built as the grammar says.
6. **Inline formatting elements.** By the tag table a `<b>` or `<span>` with text is a `text` node, so
   `<p>Order <b>confirmed</b> today</p>` prints as three lines and `find`/`until` can't match "Order
   confirmed". Not built here. Recommended before the reader is written: phrasing elements without a role get no
   node, and their text belongs to the parent's run.
7. **A long token broken by `-` or `_` is shown under an ordinary name.** "Looks random" needs a run of 20
   letters and digits. A 43-character base64url token such as `dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk`
   has runs of 12, 17 and 12, so `?ordinary=<it>` is shown whole (checked). Under a credential name it is
   hidden. This is more than the "short sign-in code" the owner accepted; the rule is built as the brief words
   it and the case is reported, not widened silently (counting `-` and `_` into the run would hide every slug).
   One possible rule: a run of 20 or more of letters, digits, `-` and `_` that holds a digit and both an upper
   and a lower case letter.
8. **A page that ends before a line longer than `max` can be nearly empty.** "A page ends at the last line end
   that fits": a short line followed by a line of 30,000 characters gives a first page with the short line
   only. Built as specified; it always advances.
9. **One word in a sign-in path** (`/resetpassword/abc12`) isn't a sign-in segment under decision 16; the brief
   says "as a whole word or a part of the segment". If "part" was meant as "anywhere inside", `/author/…` and
   `/assortment/…` would be cut too.

### Known limits found (for `KNOWN-LIMITS.md`, which the last step writes)

- **A read can be paged until it has shown 5,000 references.** Then the first of them are dropped, their
  elements get new strings, and the next cursor is refused with "The page changed; read again without the
  cursor." (test `test_a_read_of_more_than_5000_elements_never_returns_a_dropped_reference`). *Harm:* a page
  with more than 5,000 links or controls can't be read to its end with `full` in one chain; parts by `ref` and
  `find` still work. Every reference on a returned page is valid when it is returned.
- **A fold's count can be off by a few characters on such a page:** hidden references that were dropped are
  issued anew, with more digits.
- **Two runs with the same letters:** shown in `test_the_rest_shown_honestly_two_runs_that_draw_the_same_letters`,
  as section 6 lists it.
- ~~PLAN-GAP 7 above, if the lead accepts it as a limit.~~ Closed by section 7's decision 7 (step 1b): a token
  broken by `-` and `_` is hidden now. What stays is the limit the owner accepted (board #213): a short sign-in
  code, and a token in lower case or without a digit.

### Budgets

Step 1's numbers stand in the table of step 1b, beside the new ones. Every row is met. A result has 318
characters around its outline (the brief: about 310). The envelope used is `{"ok": true, "data": {"reads": [...], "version_notice": null}, "pending": {"items": [], "total": 0, "cursor":
null}}`; the browser step measures the real one. No stop rule was hit.

### What I ran and what it printed

```
$ cd /var/home/ares/AresOS-28-chrome-read
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_view_address \
    test_view_nodes test_view_references test_view_outline test_view_paging test_view_hostile test_view_budgets
.................................................................................................................................
----------------------------------------------------------------------
Ran 129 tests in 3.705s

OK
```

Python 3.14.8 on the laptop; the sources parse as Python 3.12 (CI's version) and use nothing newer. No other
suite, no container and no browser was run.

**Tests that fail when the rule is removed.** Each rule below was broken in a copy of the module outside the
repository (never committed) and the seven test modules were run against it:

| Broken variant | Result | Failing modules |
|---|---|---|
| unchanged | OK | |
| `quoted()` no longer escapes the quote | 14 failures, 1 error | hostile, outline, paging |
| `quoted()` no longer calls `visible()` | 68 failures, 1 error | hostile, outline, paging |
| a role outside the list is kept | 19 failures | hostile, nodes, outline |
| an unread field may carry a value | 1 failure | nodes |
| the user name stays in the site | 11 failures | address, hostile, outline |
| credential names aren't hidden | 38 failures | address, outline |
| a sign-in word in the path hides nothing | 23 failures | address, outline |
| nothing looks random | 14 failures | address, hostile |
| the threshold is 30, not 20 | 1 failure | address |
| nothing is percent-encoded | 2 failures | address, hostile |
| the short form shows the query | 8 failures | address, outline |
| a fragment is shown as it is | 12 failures | address, hostile |
| a page may end inside an escape | 2 failures | paging |
| the bytes as sent don't end a page | 8 failures | paging |
| a reference of another tab resolves | 5 failures | references |
| another connection keeps the table | 3 failures | references |
| a table doesn't fold | 6 failures | budgets, outline |

(Failures count sub-tests.) The main hostile test compares every kind of read of a page that holds a hostile
string in every place with the same read of a twin page holding harmless text of the same length: with the
quoted strings emptied, the two texts are equal.

### Notes

- The pre-push check (gitleaks) blocked the first push: two made-up test values looked like a JWT and an API key.
  They are now built at run time from a digest (`made()` in `test_view_address.py`); the commit was amended
  before anything was pushed. Nothing was bypassed.
- Commits `fcd22ee9` and `de6306c1` hold three test lines with a literal direction-changing or line-separator
  character in a string; `2ed6854c` replaced them with `\u` escapes. The module sources never held any.
- Nothing is left in `.work/`.

### Left, in order (the next steps)

Superseded by step 1b's list above.

### Commits of step 1

- `fcd22ee9` Chrome read: the public and the short form of an address
- `794cc7a4` Chrome read: the node list's contract and the reference table
- `de6306c1` Chrome read: the outline renderer, reads by reference, full and find
- `2ed6854c` Chrome read: pages, cursors and the 48 KiB bound, tested
- `c19b838f` Chrome read: hostile pages and the read budgets as tests
- this file
