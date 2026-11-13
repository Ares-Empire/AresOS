# 28: Chrome capability: reading, references, navigation and batched steps

**Goal:** Claude gets a Chrome tool that costs far less to use than the one brief 20 built, with the same questions
before every send. One read returns a compact outline of the page with short, stable references. One call opens a
page and returns that outline. One call runs several steps and says what changed. One call reads several tabs. The
tool list a session loads shrinks from 28 tools to 17. "Better" is written as budgets and a CI test group measures
them against brief 20's tools on the same fixture pages.

The owner's words (2026-11-11): "I don't just wanna rebuild Claude in Chrome. I wanna make a better tool for AresOS
that's more efficient with readings, navigation, free tab navigation etc."

**This is the first of two packages.** Brief 28 builds the efficient surface inside the control model brief 20 built
(Claude's tab group; one of his tabs only after a take). Brief 28b (`briefs/28b-chrome-his-tabs.md`) then lets Claude
look at his open tabs in place. 28 comes first because it needs no owner decision; 28b waits on 28 and on three
judgment calls.

**Building starts only after PR #27 (brief 20) is merged.** Branch from `main` after that merge and work on top of
it. Paths and line numbers in this brief come from PR #27 at `8b7e799c`; read them again on merged `main`.

**Builder (recommended, the lead confirms at launch):** a Claude agent on Fable 5.2. The work changes a dense,
security-reviewed code base, needs judgment about what a reader should show, and must not be cut off halfway; Codex
is away from about 2026-11-14 to 11-17 and ends on 11-21. **Review** (`docs/REVIEW.md`, "Tools for Claude"): two
fresh reviewers at once, a package review and a security review, Codex while it is available, otherwise Claude on
Opus. This package doesn't touch the asking path, so it needs no Fable reviewer.

## Background (read first)

- `docs/design/CONTROL.md` **section 6 is this package's specification**: "Reading a page", "Going to pages and
  acting", "Actions", "Efficiency, as a tested property", "Known limits" and test groups 14 to 16 under "Tests".
  Sections 3 and 4 are the rules every action follows. Where this brief and section 6 differ, tell the lead in the
  report (PLAN-GAP); don't pick one silently.
- `docs/control/PLAN.md`: decisions 24 and 25 and the entries of 2026-11-11 (the owner's bar and his words).
- `docs/REVIEW.md`, "Tools for Claude": the bar the reviewers use.
- `reviews/20-chrome/REPORT.md` (the newest sections first, "Measured views", and the latency section),
  `reviews/20-chrome/KNOWN-LIMITS.md` and `reviews/20-chrome/TOOL-DESCRIPTIONS.md`.
- `reviews/18d-base-slim/REPORT.md`: how shared rules go once into the server's MCP instructions, and how the
  description sizes are measured.
- The code, before you change it:
  - `control/aresos_control/chrome/adapter.py`: `read`, `facts`, `payload`, `free`, `steps` and `call`;
  - `control/aresos_control/chrome/definitions.py`;
  - `control/chrome/extension/reader.js`: `snapshot`, `targetFacts`, `safeValue`, `password`;
  - `control/chrome/extension/background.js`: `facts`, `collection`, `dispatch`;
  - `control/aresos_control/proxy.py`: the Chrome upload branch;
  - `control/chrome/ci/browser.mjs` (the helpers `rpc`, `call`, `read`, `target`, `nav`) and `ci/verdicts.mjs`.

**Why brief 20's tools cost so much** (read in its code and reports):

- A read returns one JSON line per element with a six-field reference, everything the element holds (`expected`,
  with its box) and its text. A container's text repeats the text of everything inside it. The long fixture (120
  paragraphs, 80 fields, about 57,000 characters of content) comes back as 221,477 characters in 14 calls.
- Every action must send `reference` and `expected` back. A reference is bound to the whole view, so any change on
  the page makes every reference stale, and a full read is needed between any two actions.
- `chrome_open` and `chrome_navigate` return before the page has loaded. Claude then waits and reads.
- A result says what happened to the one element acted on, not what changed on the page.
- `chrome_tabs` returns 5 tabs per call, 10 at most.
- 28 tools, with nine separate tools for the kinds of input.

## Before anything else: record the baseline

Do this first, on merged `main`, before any change to the tools.

1. Add the fixture pages of "Tests, group 16" to the fixture server.
2. Write the scripted tasks of group 16 against **brief 20's tools as they are** and run them in CI.
3. Commit the counts as `control/chrome/ci/efficiency-baseline.json`: calls and returned characters per task; the
   characters of all tool descriptions plus the server instructions; the characters of all tool names plus input
   schemas (compact JSON); the run id. This file is the baseline for every budget. It isn't edited afterwards.

PR #27 adds a latency harness and a CI latency check under `control/chrome/ci/`. Read their exact paths and the
targets from the merged tree and from the latency section of `reviews/20-chrome/REPORT.md`. **Build group 16 into
that harness: one harness, not two.** If the merged tree has none, say so as a PLAN-GAP and put group 16 into a short
job of its own in `control-chrome.yml`.

## What to build

### 1. The reader collects outline nodes (extension, read-only)

A new read-only command of the content script, `outline`, next to `read`. For every readable frame it returns the
document, its revision, address, title, scroll position and page height, and a flat list of nodes in document order:
the reader's element id, the parent's id, the role, the accessible name, and only what applies of: the value, the
states that are set, the link address, a form's method, action and hidden field names, a list's option count and
chosen option, and the element's **own** text (not its descendants').

- **Roles come from a fixed list** (item 2), never from a page's own string. Brief 20's `role` returns a `role`
  attribute verbatim (`reader.js`, `role`), and the outline prints the role outside the quotes, so a page could
  write outline lines with it. For `outline` the reader takes the attribute only when its first word, in lower
  case, is on the list; otherwise it takes the role of the tag (the table in item 2); otherwise the element has no
  role. `targetFacts` keeps brief 20's `role` as it is, because the classification reads it. Names as the reader
  computes them today. Headings carry their level.
- **The password rule comes first, and it gets two additions** (section 6, "What the extension can and can't do").
  The exclusion check runs before every value or text read, in every frame and shadow root; a password-kind field
  yields its label and the kind, nothing else. The additions are built into the reader's own functions, so every
  reader of a page gets them: `outline`, brief 20's `read` and `facts`, the binding and the question.
  - **Names** (in `password`, the one exclusion function). A field a person types into (not `type="hidden"`) is a
    password-kind field when its `name`, `id`, label, placeholder, `aria-label` or `autocomplete` holds a
    credential word. This holds in every document, whatever the field's type and however long the reader has
    watched. The words are in the definitions, versioned like the send-word list: password, passwort, kennwort,
    passcode, passphrase, pwd, pin, otp, totp, tan, mtan, 2fa, mfa, secret, token, cvv, cvc; and `code` only next to
    one of verification, verify, security, sms, login, auth, einmal, bestätigung, sicherheit ("verification code",
    "Einmalcode"). They match as whole words and as parts of a name (`user_password`, `otpCode`), never inside
    another word (`shipping` is not `pin`). Such a field is handled exactly like `type="password"`: not read, not
    typed into by Claude, bound by its presence only. Keep the words in a new module beside `policy.py`, with a
    copy inside `reader.js` that a test compares with the definitions; `policy.py` and `policy.js` stay untouched,
    so the send-word classification can't change by accident.
  - **History** (in the value and text readers, `safeValue` and `editableText`). The reader returns what a text
    field or an editable area holds only in a document it has watched since before the page's scripts ran (brief
    20's preload: Claude's own tabs, and a taken tab after its reload). In every other document (a taken tab
    before its reload, a frame the preload missed) every text-like `input`, every `textarea` and every editable
    area is `(not read)`, and the reader doesn't touch its value or text. Ticks, radio choices and a list's chosen
    option are still returned. Why: there the reader can't know whether a field was a password field before it
    arrived, and a password he made visible looks like any other text. The reader knows which case it is from how
    it was installed, never from anything a page can set; when it can't tell, the document counts as not watched.
    `reload_state` keeps comparing a field with its default inside the content script; only its counts leave.
- Left out: scripts, styles, hidden elements, elements behind an open modal dialog, frames of the fixed list.
  Frames of other sites and open and closed shadow roots are included, as today.
- No box, no computed style beyond what the checks above need. The command must be cheaper than `read` on the same
  page (the latency budget below).
- At most 20,000 nodes per tab. Beyond that the reply says how many were left out.

A second read-only command, `page_state`, is the one cheap question the service asks about a tab. The background
script answers it from every readable frame's reader and from what it knows itself:

- `token`: one opaque string that changes whenever what a read returns could have changed. Per readable frame the
  reader gives its document and instance, its count of DOM changes (brief 20's `revision`), a digest of its
  address, and a digest of the live state of its fields: for each `input`, `textarea` and `select` the tick, the
  chosen option and the value, and for a password-kind or unread field only that it is there. The background
  script joins these with each frame's id and Chrome document id. Brief 20's `revision` alone isn't enough: typing
  into a field changes no DOM node, and a change in a frame doesn't move the top document's count;
- `document`, the top frame's Chrome document id, and `address`, a digest of the tab's full address;
- `ready`: whether the top document's `readyState` is `complete`;
- `dialog`: whether a native dialog is open, and `queued`: whether page steps are queued (brief 20's
  `queued_steps`). While a dialog is open the readers can't answer; the reply then holds `dialog: true` and no
  token.

The service uses it to wait, to bind a cursor (item 2) and to look at the tab between the steps of a list (item 5).
It never polls with full reads.

**Waiting, defined once** (for `until`, for a cursor, for "loaded" and for the change report):

- **Quiet:** the token hasn't changed for 150 ms.
- **`until`:** the service asks `page_state` every 100 ms and reads the outline again only when the token moved.
  `text` is met when the text is in the page as `find` would find it (literal, without regard to case, folded
  parts and frames included); `gone` is met when it isn't.
- **Loaded,** for `chrome_open`, `chrome_go`, `chrome_take` and a step that navigates: the navigation has arrived,
  and the page is `ready` and quiet. **Arrived** means one of two things. The tab shows a new top document (another
  Chrome document id than before the call). Or, for a navigation inside the same document (a fragment, or a
  history entry of a single-page site), the tab's address has changed while the document stayed. A reload, and a
  `url` equal to the present address, need a new document.
- **`until` together with a navigation** replaces "ready and quiet", never "arrived". The call returns as soon as
  the navigation has arrived and the text condition holds, which is what helps on pages that never go quiet.
  `until_met` and `loaded` are reported separately; `loaded` says whether the page was also ready and quiet then.
- At the timeout the call returns what is there, with `loaded: false` or `until_met: false`.

`background.js` gets these two commands, a `show` command for `chrome_show`, and a `tabs` reply that holds every
tab at once with the fields item 6 needs. **Nothing else in `background.js` changes in this package:** not `input`,
`resume`, `dialog`, `prepare_control`, `take`, `release`, the debugger methods or the session rules.

### 2. The outline, and `chrome_read` (service)

The service renders the nodes; the reader only collects. Put the rendering and the references in a module of their
own (for example `control/aresos_control/chrome/view.py`), tested without a browser against recorded node lists.

**Addresses: one public form** (section 6, "Reading a page"). One function in the service, `public_address`, turns
an address into the only form that may leave the service. It returns:

- the site: the host in lower case and ASCII, with the port when it isn't the scheme's default, and `http://` in
  front when the address isn't `https`; never a user name or a password;
- the path as the browser gives it, with two cuts. After a segment that holds a sign-in word (reset, verify,
  confirm, activate, magic, token, invite, auth, oauth, sso, saml, login, signin, logon, callback, password,
  passwort, otp; as a whole word or a part of the segment), everything that follows is one `…`. And a segment that
  looks like a random value is `…`: it holds a run of 20 or more letters and digits with at least one of each, or
  it is 24 or more hex digits once its hyphens are taken out;
- `?…` when the address has a query and `#…` when it has a fragment: never a name or a value from either;
- nothing but letters, digits and `. - _ ~ / % :` besides those marks. Everything else is percent-encoded, so an
  address can't break an outline line.

Everything that leaves the service toward Claude, toward his question or toward the log carries addresses in this
form and no other:

- reads: the `url` of a page, a link's and a form's target, detail reads, `find`, change reports;
- `chrome_tabs` and `chrome_library` (bookmarks, history, and where a download came from);
- the results and error messages of every tool, the notices;
- a prepared operation's question and description, and what `chrome_operation_status` returns;
- what the service writes to its audit log (`aresos log`).

Full addresses stay inside the service and the extension: in the reference table, in an operation's payload
(`binding`, `reference`) and in the commands to the extension. **Nothing about comparing changes:** the extension
still compares the full destination right before an approved input. To build this, `prepare`, `question`, `free`
and `stage` in `adapter.py` take their description, question and stage texts from a copy in which each address
went through `public_address` (`url`, `frame_url`, `effective_url`, `form.action`, `target.href`,
`editable[].url`, a dialog's `frame_url`, and the `url` the extension reports after an input). The payload isn't
touched. This is the one change this package makes inside those functions; show its lines in the report.

Claude uses an address it can't see by reference: a link's `ref`, his tab's number, a library entry's `ref` (items
4 and 6).

**The outline format** (normative; section 6 shows an example):

```
line    = indent role [" " name] [" = " value] {" " state} [" → " target] [" " ref]
indent  = two spaces per level of depth
role    = one word from the role list below, nothing else
name    = the accessible name or own text, in double quotes
value   = a field's value in double quotes; the words (not read) instead for "password" and for a field whose
          history the reader doesn't know (item 1)
state   = checked | selected | disabled | required | invalid | expanded | collapsed | current | readonly
target  = for a link that leaves the page's site: its site; for a form: its method, site and path
ref     = three letters and a number, for example kqt5 (item 3)
```

- **The role list.** Landmarks: `main`, `navigation`, `banner`, `contentinfo`, `complementary`, `region`, `search`,
  `form`. Structure: `article`, `group`, `list`, `listitem`, `table`, `row`, `cell`, `columnheader`, `rowheader`,
  `figure`, `img`, `separator`, `toolbar`, `dialog`, `alertdialog`, `alert`, `status`, `tooltip`, `progressbar`,
  `frame`. Text: `h1` to `h6`, `p`, `text`. Controls: `link`, `button`, `textbox`, `searchbox`, `combobox`,
  `listbox`, `option`, `checkbox`, `radio`, `radiogroup`, `switch`, `slider`, `spinbutton`, `tab`, `tablist`,
  `tabpanel`, `menu`, `menubar`, `menuitem`, `menuitemcheckbox`, `menuitemradio`, `tree`, `treeitem`, `grid`,
  `gridcell`, `password`. The list is in the definitions; the reader and the renderer both check against it, and
  the renderer treats a word that isn't on it as no role.
- **The role of a tag,** when the `role` attribute gives none from the list (brief 20 maps `table`, `ul`, `ol` and
  `main` to `generic`, which the outline can't use): `main` is `main`; `nav` is `navigation`; `header` and `footer`
  directly under `body` are `banner` and `contentinfo`; `aside` is `complementary`; a `section` with a name is
  `region`; `form` is `form`; `article` is `article`; `fieldset` and `details` are `group`; `ul`, `ol`, `dl` and
  `menu` are `list`; `li`, `dt` and `dd` are `listitem`; `table`, `tr`, `td` are `table`, `row`, `cell`; `th` is
  `columnheader`, or `rowheader` with `scope="row"`; `figure` is `figure`; an `img` with an `alt` text is `img`;
  `hr` is `separator`; `dialog` is `dialog`; `iframe` is `frame`; `h1` to `h6` and `role="heading"` with a level
  are `h1` to `h6`; `p`, `blockquote` and `pre` are `p`; an `a` with an address is `link`; `button` and `summary`
  are `button`; an `input` goes by its type (`checkbox`, `radio`, `range` as `slider`, `number` as `spinbutton`,
  `search` as `searchbox`, the button types as `button`, a password-kind field as `password`, `hidden` none, every
  other as `textbox`); `textarea` and an editable area are `textbox`; `select` is `combobox`, or `listbox` when it
  shows several rows; `option` is `option`; `progress` and `meter` are `progressbar`; any other element with text
  of its own is `text`. `role="presentation"` and `role="none"` give no role.
- **One escaping rule for everything a page wrote.** Names, texts, values, option labels, titles, error texts,
  table cells and column headers, the names in a `find` hit's path, hidden field names, a dialog's text and tab
  titles appear only inside double quotes, and only after one function, `quoted`: the base's `visible()` (control
  and direction-changing characters, line breaks, backslash), then `"` as `\"`. Outside quotes a line holds only
  what the tool wrote: indentation, a role word, state words, numbers, references, public-form addresses and the
  marks `=`, `→`, `·`, `|`, `[`, `]`, `(`, `)` and `…`. This holds for the outline, for every `ref` form (tables
  and forms included), for `find`, for the change report and for the present line of a stale reference.
- **A refusal never carries page text in its message.** The message is the tool's own fixed sentence. Where the
  element's present line is given (a stale reference), it sits in `untrusted_content`, rendered and escaped like
  any outline line: in that read's entry beside its `error` for `chrome_read`, and in `untrusted_content.now` for
  `chrome_do`. `chrome_open` and `chrome_upload` give the message alone, and Claude reads the element again.
- Text appears once, on the deepest element that owns it. A label whose text is its field's name gets no line of
  its own. An element without a role, a name or own text gets no line, and its children move up a level.
- A name or value can never start a new line or end its quotes (the escaping rule above).
- **Folds** (each says what it hides):
  - a name, a text or a value longer than 200 characters is cut and ends in `…+N`, N being the characters left
    out; the element's reference reads it whole;
  - of more than 8 neighbours with the same role, the first 5 are shown, then `… N more (C characters) kqt17`; that
    reference reads exactly the neighbours left out, and nothing can act on it;
  - a table is its line and `… R rows, C columns (N characters)`; the table's reference reads it;
  - a list of more than 12 options is `(N options)` on the field's line, with the chosen one as the value;
  - a form shows its first 40 fields, then a fold like the one for neighbours; hidden fields are `(N hidden)` on
    the form's line.
- A reference is put on every element that can be acted on, and on every element that can be read by itself: a
  form, table, list, landmark, dialog, article or frame, and anything cut or folded.

**`chrome_read`** (effect read).

Input: `tab` (integer), or `tabs` (2 to 5 integers; then only `max` and `request` may accompany it); `ref`; `full`
(boolean); `find` (1 to 200 characters); `role` (with `find`); `until` (an object with `text` or `gone`, each up to
200 characters);
`timeout_ms` (0 to 6,000, default 3,000, with `until`); `max` (1,000 to 40,000; default 6,000, or 3,000 per tab with
`tabs`); `cursor`; `request` (up to 200 characters; unused until brief 28b, accepted and ignored now).

Result:

```
{"reads": [{"tab": 412, "whose": "claude", "characters": 4211, "total": 18840, "cursor": null,
            "mid_line": false, "until_met": true,
            "untrusted_content": {"url": "…", "title": "…", "scroll": "0/3200", "outline": "…", "dialog": null}},
           {"tab": 413, "error": {"code": "refused", "message": "…"}}],
 "version_notice": null}
```

- No `ref`, no `find`: the outline with its folds.
- `ref`: that element with **one level unfolded**, in the form that fits its role: its own name, text and value
  whole, and its direct content complete (every row, item, field or hidden neighbour). Below that level the fold
  rules apply again. A table: a first line `columns: A | B | C`, then one
  line per row with the cells separated by ` | `, and controls inside a cell as `[link "Open" kqt31]`. A list: its
  items. A form: every field as an outline line with its options (up to 50 per field, more by the field's own
  `ref`), `required`, the field's error text, the hidden fields by name, the buttons, and the form's target. A text:
  in full. A single link or control: everything known about it (its address in the public form, the title, all
  options).
- `full`: **no fold and no cut** below the starting point: the whole page without `ref`, the element and
  everything under it with `ref`. This is how Claude reads all of something in a few calls, paged by `max` and
  `cursor`.
- Everything a read returns from the page sits in `untrusted_content`, also what `ref`, `find` and `until` bring.
  Outside it are only the tool's own numbers and flags.
- `find`: up to 20 hits per page. Each hit is the element's outline line, then ` · in ` and the path of named
  ancestors (at most 80 characters); a hit inside a longer text adds 60 characters either side of it. Literal, no
  regard to case, over names, labels, values that may be read, and text; folded parts and frames included; inside
  `ref` when both are given. `role` keeps only that role.
- `until`: as item 1 defines waiting; the result carries `until_met`.
- `tabs`: each tab is read by itself. A tab that can't be read (not in Claude's group, the fixed list, a dialog)
  gets its `error`; the others are returned.
- **Paging.** `max` bounds the characters of `outline` in one result; `total` is the length of the whole text of
  this query, and `characters` what this result holds.
  - A page ends at the last line end that fits. If not even one whole line fits (a text of 100,000 characters
    read in full, a long value, a wide table row), the page ends after `max` characters inside that line, never
    inside an escape, and says `"mid_line": true`; the next page goes on in the same line.
  - **Every page that isn't the last holds at least one character more than was returned before it,** so paging
    always advances and always ends.
  - The `cursor` names the position, the state token (item 1) and the query (`ref`, `find`, `role`, `full`). With
    another token it fails with `stale_reference`, "page changed, read again without the cursor". With another
    query it fails with `invalid_input`.
  - **The envelope.** The base bounds a result at 48 KiB of JSON (`RESULT_LIMIT`), written in ASCII: a character
    outside ASCII costs 6 bytes, and each quote and line break of the outline costs 2. The service measures the
    result as it will be sent, with its header fields, the notice of pending operations and the version notice,
    and ends the page earlier when it wouldn't fit. It never relies on the base's last-step shortening.
  - **Several tabs.** With `tabs`, each tab gets `max` characters (3,000 unless Claude says otherwise) and an equal
    share of the bytes the envelope leaves after the fixed parts. A share a tab doesn't use isn't passed on. Each
    tab's entry has its own `cursor`, to go on with in a call for that tab alone.
- A native dialog that is open is returned as `dialog` (kind, text), with an empty outline, as today.
- The checks of today's `read` stay: the fixed list on the top document and on every frame, the qualification
  mode, the queued page steps (`reconcile_checks`, `steps`).

### 3. References (service)

- **A reference is three letters and a number, for example `kqt5`.** The service issues it, and no string is ever
  issued for two things:
  - **The letters name this run of the service.** The service draws them at random when its process starts (three
    consonants, so they spell nothing). It writes the letters of its last 100 runs to its store and never draws one
    of those again. If the store can't be read or written it still draws at random, and reading goes on.
  - **The number comes from one counter for the whole process, across all tabs.** It only counts up. It isn't reset
    when Chrome restarts or reconnects, when a tab closes or when entries are dropped. Tab A and tab B can never
    both hold `kqt5`.
  - The same live element (same connection, tab, frame, document, reader instance and reader id) gets the same
    reference in every read and result.
- **Per reference the service keeps** the extension connection it was issued under (the `session` of the
  extension's hello), the tab, the frame, the document, the reader instance, the reader's element id, and **the
  line it last showed Claude** for that element. It keeps the newest 5,000 per tab, in memory only. A dropped
  entry is gone for good: its string is never issued again, so an old reference can't come to mean a new element.
- **The reader instance.** Brief 20's reader numbers its elements from `e1` each time it is installed, while its
  document id survives a release and a new take of the same page. So `(document, e5)` can name two elements over
  time. The reader therefore draws a random instance id at each install and returns it with `outline`, `read` and
  `facts` (one new field of `snapshot`); the table keeps it, and a different instance means the reference is stale.
- Every action resolves its reference to brief 20's internal reference (session, tab, frame, document, element; no
  `view`) and then runs brief 20's path unchanged. It is refused with `stale_reference` when:
  - the reference isn't in the table: invented, dropped, or issued by another run of the service;
  - it was issued for another tab than the one the call names;
  - it was issued under another connection (Chrome or the extension restarted or reconnected; the service empties
    the table then and the counter goes on);
  - the document, the reader instance or the element is gone or is another one;
  - **the element's fingerprint differs** from the one Claude last saw.
  The refusal carries the element's present line, and that counts as shown, so a repeated call can pass.
- **The fingerprint.** Brief 20 made the caller send back everything the element had shown (`expected`) and
  compared all of it, its place on the screen included. The service now keeps that comparison itself, per
  reference, as a digest of what the element means:
  - it is brief 20's element facts (`targetFacts`) without the `box`, without `onscreen`, and without the states
    `disabled`, `required` and `invalid`;
  - so it holds the role, the name, the label and the title; a link's destination, resolved and in full; whether
    the element submits a form, is editable or is a search field; the page dialog it belongs to; whether it is
    ticked, selected or expanded; a list's options; and the whole value (for a password-kind or unread field only
    that it is one);
  - it is taken from the full facts, not from the line. A name or value the outline showed cut, and a link's
    address that the line doesn't show at all, are compared whole;
  - it moves only when a result shows Claude that element again (a read, a `find` hit, a `~` line of a change
    report, the present line of a refusal), or when a step of Claude's own has acted on that element (item 5).
  Left out on purpose: where the element sits, and three states that don't change what it means. A control that
  became enabled is still the control Claude meant, and a disabled one does nothing when clicked.
- **What is no longer checked, said plainly:** anything outside the element. Brief 20 refused an action when
  anything on the page had changed since the read. Now a free step runs although the text around a button or a
  neighbouring field changed. An asking step still shows and binds the form, the draft and the affected item. The
  change report covers the call itself, not the time between Claude's last read and the call.
- This replaces two things in `adapter.py`: the comparison of the caller's `expected` in `payload` (now against
  the stored fingerprint), and the comparison of `view` in `facts` (gone). The extension's own checks stay (session, tab, document, element, the hit test
  before a click), and so does everything that follows in `payload`.
- No tool input carries `reference`, `expected` or `view` objects any more.

### 4. `chrome_open` and `chrome_go` (effect change)

**`chrome_open`** input: exactly one of `url`; `tab` (open the address that tab shows; with `seen` when the tab is
his, item 6); `ref` (open the address behind a link's or a library entry's reference; `tab` may accompany a link's
reference and must then be its tab).
Also `until`, `timeout_ms` (0 to 15,000, default 8,000) and `max` (default 4,000).
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
  item 1 defines it (a new document, or a new address in the same document; ready; quiet), or until `until` is
  met, or until the timeout. `loaded` and `until_met` say which.
- `chrome_open` with `tab` or `ref`: the service takes the full address from its own record (the list Claude named
  with `seen`, the tab's present address for a Claude tab, or the reference table). Claude only ever saw the
  public form. The rules of "Where Claude may go" apply to it.
- The outline is the same as `chrome_read`'s, with references ready for the next call.

### 5. `chrome_do` (effect change)

Input: `tab`; `steps`, 1 to 20 objects, each with `do` and what that step needs; `max` (500 to 8,000, default 2,000:
the bound of the change report).

| `do` | Needs | Is brief 20's |
|---|---|---|
| `click` | `ref` | `chrome_click` |
| `fill` | `ref`, `text` (up to 20,000 characters; line breaks go in as text) | `chrome_fill` |
| `select` | `ref`, `value` (an option's label or value) | `chrome_select` |
| `check` | `ref`, `checked` | `chrome_check` |
| `press` | `ref`, `key` | `chrome_press` |
| `scroll` | `ref` (optional: the page), `y` (pixels, negative is up) | `chrome_scroll` |
| `dialog` | `accept`, `text` (optional, for a prompt) | `chrome_dialog` |
| `wait` | `until`, `timeout_ms` (0 to 8,000) | `chrome_wait` |

Result:

```
{"tab": 431,
 "steps": [{"do": "fill", "ref": "kqt8", "outcome": "done"}, {"do": "click", "ref": "kqt10", "outcome": "prepared"}],
 "not_run": 0,
 "prepared": [{"approval": {"question": "…", "operation_id": "…", "description": {}}, "state": "reserved"}],
 "unknown": [],
 "loaded": null,
 "untrusted_content": {"url": "…", "title": "…", "changed": "…", "more_changes": 0, "outline": null,
                       "dialog": null, "clipboard": null, "stopped": [], "now": null},
 "version_notice": null}
```

How it runs:

1. **Check first.** Resolve every reference and apply item 3's rule before the first step. If one fails, nothing has
   run, and the result names the step.
2. **Run in order, and check each step again right before it runs.** Each step goes through brief 20's path for
   that verb: `payload` (fresh facts, classification, binding), then `free` (dispatch once) or `engine.reserve`
   (prepare). Every free step is still committed as its own operation before its input, as today. On the fresh
   facts `payload` has just read, item 3's rule is applied again **in full, the value included**: what the element
   shows must be what Claude last saw.
   - One thing only moves "last saw" inside a list: after a step of this list has itself acted on an element (a
     fill, a select, a check, a key in a field), the service records that element as the extension reports it right
     after the step. So `fill` and then Enter on the same field passes.
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
   gone quiet (item 1; at most 1,500 ms), or, after a navigation, once it is loaded (within the call's deadline,
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
the start of the call, and no timeout is raised:

- **`chrome_read`: 8 seconds in all.** `until` waits at most 6. With `tabs`, a tab whose turn hasn't come by second
  6 gets the error `not_read`, "time ran out; read this tab by itself", and the others are returned.
- **`chrome_open`, `chrome_go`, `chrome_take`: 18 seconds in all,** with `timeout_ms` at most 15,000.
- **`chrome_do`: 18 seconds in all.** No step starts after second 12. A `wait` ends at second 12 at the latest. The
  report's waiting ends at second 16 at the latest, also for a new page, which is then returned as far as it has
  loaded (`loaded: false`). Steps that weren't started are counted in `not_run`, and the result says
  `"deadline": true`. Their references stay good, so Claude sends them in the next call.
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
  `look` (a read-only site); the title, quoted and cut at 80 characters; the address in the public form (item 2),
  cut at 60 characters.
- **The list binds what follows** (section 6, "Which tabs Claude works in"). The result of `chrome_tabs` carries
  `seen`, a reference (item 3) for this list. For every tab in it the service keeps what it showed Claude: the tab,
  its top document (Chrome's document id) and its full address; for a tab asleep, the address alone. It keeps the
  last 8 lists, in memory, and drops them all when the connection to Chrome changes.
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
- **`chrome_close`** (change; input: `tabs`, 1 to 20; `request`, accepted and ignored now). Closes tabs that are
  `claude`. In this package every other tab is refused, **a taken tab included** ("this is the owner's tab;
  release it"). Brief 20's `chrome_close_tab` closes any tab in the group, a taken one too, without looking at
  what it holds: that ends here. The result lists `closed` and, with the reason, `kept`.
- **`chrome_take`** (change; input: `tab`, `seen`, `reload`, `request` accepted and ignored now) and **`chrome_release`**
  (change; input: `tab`). In this package they are brief 20's `take_tab` and `release_tab`, with one difference:
  the explicit reload has one home. `chrome_take` without `reload` takes the tab and keeps its page, and its result
  says whether a reload is still due and what it would lose. `chrome_take` with `reload: true` also does that
  reload now (brief 20's `prepare_control` with its explicit repeat) and returns the outline. No other tool has a
  `reload` input.
  - **`chrome_go` in a taken tab that hasn't had its reload** would replace his page without any check in brief
    20. Here it first goes through `prepare_control`, as a first input does: `reload_required` when brief 20's
    check finds typing, an editor or playing media, otherwise the guarded reload, and then the navigation.
  - **Brief 20's check before that reload is unchanged in this package.** It calls a tab clean when no field
    differs from its default, which many pages defeat by copying his typing into the default. Brief 28b replaces
    it (its item 4a). Say so in `KNOWN-LIMITS.md`; brief 28 must not reach his laptop without 28b.
- **`chrome_library`** (read; input: `kind`, one of `downloads`, `bookmarks`, `history`; `text`; `cursor`; `limit`).
  The three brief 20 tools merged, with their snapshot paging. Two differences: every address is in the public
  form, and every entry carries a reference (item 3) that `chrome_open` takes as `ref`. The service keeps the full
  address under that reference for as long as the snapshot lives.
- **`chrome_upload`** (change; input: `tab`, `ref`, `path`). Brief 20's tool with a short reference. The proxy's
  file branch stays as it is, apart from the field names it reads.
- **Unchanged in name, input, result and behaviour:** `chrome_submit`, `chrome_submit_trusted`, `chrome_drop`,
  `chrome_operation_status`, `chrome_notices`, `chrome_notice_ack`, and the owner-only `chrome_sites`.
- A new error code, `take_first`, for `chrome_read`, `chrome_go`, `chrome_do` and `chrome_upload` on a tab that
  isn't in Claude's group: "this is one of the owner's tabs; take it, or open its address in a Claude tab". (Brief
  28b lets `chrome_read` work there without a take.)

### 7. Definitions, instructions and sizes

- Seventeen actions are offered to Claude, plus `chrome_sites`. Everything is generated from the definitions as
  today: the MCP tool list, the `aresos` command, `docs/control/TOOLS.md`, the ask rules, `user-mcp.json`.
- **The generated ask rules for Chrome must not change by a byte.** A test compares them with the copy on `main`.
- The rules shared by every Chrome action go once into the Chrome server's MCP instructions (brief 18d's pattern,
  with its check that Claude Code passes them on unshortened): untrusted page text; what to do on
  `stale_reference`, `reload_required`, `take_first`, `owner_signin`, `owner_dialog` and `unknown`; the version
  notice; that `done` doesn't prove delivery and pages can send on their own; the clipboard rule; how to read an
  outline line and a fold; that a reference stays valid until its element changes; that `chrome_do` stops at the
  first asking step and its `prepared` entry goes unchanged to `chrome_submit`. Each description keeps only what is
  specific to its action. Write them for Claude: what it does, when to use it, what comes back.
- **Sizes** (measured as brief 18d measured Mail's): all descriptions plus the instructions at most 10,000
  characters and not above the baseline; all names plus input schemas at most 6,000 characters. A test pins the
  exact totals; a change that grows them fails until the pin is changed on purpose.
- Put the final descriptions and instructions, exactly as generated, into
  `reviews/28-chrome-capability/TOOL-DESCRIPTIONS.md`.

### 8. The order of the change

Restructure in steps that keep everything working:

1. The baseline (above).
2. Add the new commands, the view module and the new tools **next to** brief 20's tools. Unit tests and groups 14
   to 16 pass. Brief 20's groups pass unchanged through the old names.
3. Move the CI harness to the new tools **in its helper functions only**. Before you start, list in
   `reviews/28-chrome-capability/HARNESS-MAP.md` every helper you change, and every test that builds a `reference`,
   an `expected` or a `view` by hand (the staleness and mismatch cases), with its new form. A test may change how
   it reaches the tool. It never changes what it asserts about the receiver's log, the question, the binding or the
   outcome. A test of the old "any change makes every reference stale" rule becomes a test of item 3's rule, named
   in the map. A brief 20 test that reads a text field's value in a taken tab before its reload now gets
   `(not read)` (item 1, history): list each one in the map.
4. Remove brief 20's replaced tools (`chrome_find`, `chrome_read_form`, `chrome_wait`, `chrome_click`,
   `chrome_fill`, `chrome_fill_form`, `chrome_select`, `chrome_check`, `chrome_press`, `chrome_scroll`,
   `chrome_dialog`, `chrome_navigate`, `chrome_take_tab`, `chrome_release_tab`, `chrome_close_tab`,
   `chrome_downloads`, `chrome_bookmarks`, `chrome_history`), the reader's `read` rows that nothing uses any more,
   and the old paging of `chrome_tabs`. Regenerate. Pin the sizes.
5. The full Chrome suite twice on the final head, with the base, Mail, boundary and qualification workflows.

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
  the 15-minute deadline; one approval, one run.
- **The hold:** `guard.js`, `page.js`, the 500 ms window, the default block, the owner's own Enter, the three kinds
  of dialog.
- **The reader's password rule only gets stricter** (item 1's two additions); nothing in it is relaxed. The
  extension still uses no DOM snapshot, no accessibility tree and no form serialisation. No new DevTools method. No
  new permission in the manifest.
- **Where Claude may go:** the schemes, the fixed list, the owner-only excluded-sites setting, read-only sites.
- **The take rules:** a reload before the first input, unsaved typing and playing media reported first, no reload
  of a form-loaded page. Popups as brief 20 built them.
- **The qualification record:** its format, `qualification.py`, `qualify.py`, the publishing workflow. The build
  hash changes because the code does; nothing else.
- **The service unit's sandbox lines** (`control/packaging/aresos-toold.service`; `test_unit.py` pins them).
- **Mail, the base and `os/`.** Change the base only where Chrome needs a helper that belongs there, and say why in
  the report.

## Tests

No model, no real site, no real account. Fixture pages only. **Browser tests run only in containers on GitHub's
Linux runners, through the control-chrome workflows. Never start, read or touch the owner's Chrome or any browser
profile on the machine you run on; locally run only plain Python and Node tests that start no browser.**

Every new rule gets a test that fails without it.

**Without a browser** (Python and Node): the outline renderer against recorded node lists (every fold, every
escape, depth, the `ref` forms, `find`, the cut at `max` and at 48 KiB with non-ASCII text); the reference table
(same element same reference; one counter for all tabs; no string issued twice, also after entries were dropped at
the 5,000 bound and after the table was emptied; every stale case of item 3; a new reader instance in the same
document; the letters differ from those of the last 100 runs, and are still drawn when the store fails); the
`public_address` against a table (a user name and password, ports, a non-ASCII host, `http`, queries, fragments,
each sign-in word, random-looking segments such as a UUID, 40 hex digits, a 43-character token and a JWT, segments
that stay such as a slug with digits, a numeric id and an 11-character id, and characters such as `|`, `[`, quotes,
spaces and line breaks); the `chrome_do` loop with a fake bridge (the check before the first step; the check before each step on fresh facts,
with the value compared whole; a queued page step, a dialog and a new document found between two steps and after
a `wait`; every stop, `not_run`, nothing twice after an interruption at each point); the change report; the reader's `outline` command in the Node VM doubles that
`reader.test.mjs` uses, with the password fixtures; the credential words (each word, as a whole word and as a name
part, in each of the six places; `shipping`, `postal code` and `pinned` don't match).

**Passwords, in group 14 and in `password_exclusion`.** Group 7's fixtures and recording run over every new output.
Added cases, each with group 7's known password and a label that says nothing ("Code"):

- **A field made plain before the reader arrived** (a taken tab before its reload): once by `type` changed from
  `password` to `text`, once by a removed `autocomplete="current-password"`, once by a removed mask (as a style and
  as a class); each in the page, in an open and a closed shadow root and in a frame from another site.
- **A sign-in code known only by its name** (`name="otp"`, a label "Verification code", no `autocomplete`), in a
  document watched from its start and in one that wasn't.
- Every surface reads them: the outline, a form by `ref`, `find` for the password itself, several tabs, `until`,
  the change report, the results of `chrome_open`, `chrome_go` and `chrome_take`, and a prepared operation's
  question for a form that holds such a field.
- Expected: the fields are `(not read)` or `password … (not read)`; the recording shows that the content script
  read none of these values, and the password is in nothing the extension received or sent, in no result and in no
  log line. A plain text typed into a `textarea` of the not yet reloaded tab is `(not read)` too. After the tab's
  reload a plain, unnamed text field of that page is read, and the named ones still aren't.

**Group 14, reading and references** (browser): as section 6 lists it. Fixtures:

- F1, brief 20's long page (120 paragraphs, 80 fields);
- F2, a table of 200 rows and 6 columns of text (cells of 12 characters or more), and a small second table with a
  link and a checkbox in each row;
- F3, a listing of 300 links in a list, with navigation and footer link groups;
- F4, a form of 25 fields: text, a date, checkboxes, radios, a list of 200 options, a required field with an error
  text, three hidden fields, each kind of password field from group 7;
- F5, a page that changes part of itself on a click (rows replaced, a status line, one element renamed, one removed)
  and a page that loads a new document on a click;
- F6, a page with frames from a second fixture site and open and closed shadow roots;
- H1, hostile text: names and paragraphs shaped like outline lines, references (`kqt5`), folds (`… 40 more`),
  instructions to Claude, quotes, line breaks and direction-changing characters; a page of 100,000 elements; a name
  of 100,000 characters.
  - **Hostile roles:** a `role` attribute that holds a line break and a whole outline line with a reference; one
    that holds `button" kqt5`; one of 10,000 characters; one in capitals with spaces around it. Each line shows a
    role from the list or the tag's role, and nothing else of the attribute.
  - **Hostile text everywhere:** the same strings as a name, a value, an option label, a cell, a column header, a
    title, an error text and an ancestor's name come back quoted and escaped in the outline, in a table, a list
    and a form read by `ref`, in a `find` hit with its path, in a change report, and in the present line of a
    stale reference. A stale reference's message holds nothing from the page.

Small fixtures are compared with stored expected outlines, character for character.

**Paging, in group 14 and without a browser.** A text of 100,000 characters read by `ref` with `max` 1,000 comes
back whole over its pages, each page longer than nothing and marked `mid_line` until the last; the pages joined
equal the text. The same for a table row wider than `max` and for a value of 20,000 characters read in full. A
page of text outside ASCII (6 bytes a character) and one made of quotes stay inside 48 KiB as sent, measured on the
real result with a pending operation and the version notice present, and still advance. Five tabs of such text:
each gets its share, each has its cursor, and the whole result fits. A cursor used with another `ref`, `find` or
`full` is refused. `full` on F1 returns every paragraph whole and every field, with no fold and no `…+N`.

**The state token and waiting, in group 14.** Typing into a field, which changes no DOM node, moves the token. A
change inside a frame moves it. An unchanged page keeps it over 100 polls. `until` is met by a text that appears
only as a field's value, and by one that appears inside a frame. A cursor is refused after a field's value
changed. `chrome_go` to a fragment of the same page, and Back inside a single-page fixture, return `loaded: true`
without a new document; a reload doesn't count as loaded before the new document is there. `until` on a page that
never goes quiet returns when the text is there, with `loaded: false`.

**The fingerprint, in group 14.** Each of these is refused with `stale_reference` and the element's present line:
a link that keeps its name while its destination changes (once the path, once only the query); a list whose
options change while its name and chosen option stay; a box the page ticked; a menu button the page expanded; a
field whose value changed in a part the outline had cut. Each of these still runs: a button that became enabled; a
field that became `required` or `invalid`; an element that moved on the screen. And the limit, shown honestly: a
button without a destination keeps its name while the row around it shows another item; the free click runs, and
the report lists the case under known limits.

**References that can't collide, in group 14.** Each case first makes sure that new references exist, so a refusal
isn't just an empty table:

- Two tabs show the same fixture and both are read: no reference string appears in both outlines, and each of tab
  A's references is refused when the call names tab B.
- Chrome is restarted (and, separately, only the extension's connection is cut), the same pages are opened and
  read again: every reference from before is refused, and none of the new strings equals an old one.
- The service is restarted, the same tabs are read again: every reference from before is refused although the new
  counter has passed the old numbers.
- More than 5,000 elements are read in one tab: a reference dropped from the table is refused, and its string
  isn't issued again.
- A tab is released and taken again without a reload in between: a reference from before is refused, although
  the document id and the reader's element id are the same.

**Addresses, in group 14.** Fixture pages carry one marker value in the query, in the fragment, as a user name and
password, and as a 40-character path segment after `/reset/`: in the page's own address, in link targets, in form
actions, in a frame's address, in a redirect's target, and in history, bookmark and download entries.

- The marker appears in no result of any tool, in no error message, in no question or description, in nothing
  `chrome_operation_status` or `chrome_notices` returns and in no line of the audit log.
- `chrome_open` with `ref` (a link, a library entry) and with `tab` still reaches the full address: the fixture
  receiver logs the query.
- Group 3's binding still refuses a destination whose query changed while the approval waited.

**Group 15, going and acting in one call** (browser): as section 6 lists it. In addition:

- **time, through the real transports** (the `aresos` command and the MCP proxy, not a fake bridge): a list of 20
  `wait` steps of 8 seconds returns a normal result within 20 seconds, with `deadline` and `not_run`; a list of 20
  fills on F4 returns within 20 seconds with the fills that ran and the rest counted; a `chrome_read` with `until`
  on a text that never comes returns within 10 seconds; five tabs of which one is slow return four outlines and
  one `not_read`. A caller killed in the middle of a list: the fixture counts no input later than 12 seconds after
  the call began, every step that ran is in the log as its own operation, and the next call works;
- every asking case of group 1 runs through `chrome_do` once the harness has moved, with the receiver's log as
  evidence: nothing before approval, one arrival after, none on a repeat;
- a list whose third step asks: the fixture counts the first two inputs, no input from steps three to five, and
  after `chrome_submit` exactly the third;
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
- the conservative mode (an unqualified Chrome major) asks for the same inputs through `chrome_do` as brief 20's
  tools did.

**Group 16, efficiency** (browser, in the latency harness): the scripted tasks below, each run against the baseline
file. **Each row names the exact calls it allows; the test makes those calls and no others.** If a budget can't
be met with them, the budget or the tool changes, in the brief, before the build goes on (stop rule): the test
is never bent to fit. Characters are counted on the whole result as Claude receives it (the JSON text of the tool result), for the
baseline and for the new tools alike. The build fails when a budget is exceeded or when a number is worse than the
baseline.

| Task | Budget |
|---|---|
| F1: the first read: `chrome_read` with the tab | 1 call, the whole outline, at most 6,000 characters |
| F1: everything: `chrome_read` with `full` and `max` 40,000, then the same call with each `cursor` it returns | at most 3 calls, at most 75,000 characters in all |
| F1: the 80 fields with their values: after the first read, `chrome_read` with the form's `ref` | 1 further call, at most 6,000 characters |
| F2: the whole table: after the first read, `chrome_read` with the table's `ref` and `max` 20,000 | 1 further call, at most 1.3 times the cells' own text |
| F3: find one named link: `chrome_read` with `find` and `role` | 1 call, at most 800 characters |
| Open a fixture page and return one fact from it | 1 call |
| F4: fill 6 fields and send the form | 2 calls and `chrome_submit`; one question; the receiver has it once |
| Three result pages, one click each, the titles collected | 3 calls |
| Compare three open tabs | 1 call |
| List 25 open tabs (titles of about 30 characters) | 1 call, at most 3,500 characters |
| F5: a free click that changes part of the page | 1 call, at most 2,500 characters, the change named |
| Descriptions plus instructions | at most 10,000 characters, and not above the baseline |
| Names plus input schemas | at most 6,000 characters |
| Latency | PR #27's latency check stays within its targets; an outline read of F1 is no slower than one page of the old read at the baseline; a single click with its change report is faster than the baseline's click plus read |

**Brief 20's groups 1 to 13** pass twice on the final head, through the new tools, in both install modes. Register
the new browser cases in the named inventory (`ci/verdicts.mjs`) the way brief 20's FEATURE and VIEW cases are
registered. The password cases join the `password_exclusion` group. Cases that prove an asking step asks join
`classification` or `binding`. Group 16 is a CI check only and never part of a verdict. Don't add a core group and
don't change the record's format. Say in the report which case went where.

The base's, 18d's and Mail's suites still pass, and the generated artifacts are in sync.

## Out of scope

- His open tabs in place, the **READ** sign, the popup list, incognito, tabs in the background: brief 28b.
- Anything in the asking path or the hold ("What must not change").
- Screenshots, coordinates, hover, drag, console or network reading, running script text, a search that needs a
  model, loops or conditions in a step list, steps across tabs, a richer result for `chrome_submit` (section 6,
  "Left out on purpose").
- Any real site or account. The image (`os/`). Running Claude Code with a model.

## Paths

**May change:** `control/aresos_control/chrome/adapter.py`, `definitions.py` and new modules beside them;
`control/chrome/extension/reader.js` and `background.js` (only as item 1 says); `control/aresos_control/proxy.py`
(the Chrome upload branch's field names); the generated files; `control/chrome_tests/`, `control/chrome/ci/`;
`.github/workflows/control-chrome.yml` (not the qualification workflow); `docs/control/TOOLS.md`,
`docs/control/FEATURES.md` (item 9),
`control/README.md`; `reviews/28-chrome-capability/`.

**Must not touch:** `os/`, `mod/`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/TOOLS-HANDOFF.md`,
`STATE.md`, `HANDOFF.md`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `briefs/`; `control/aresos_control/mail/`,
`control/mail_tests/`, `control/boundary/`, `control/checks/`, `control/packaging/`; `reviews/20-chrome/` and every
other package's `reviews/` folder; in the Chrome code `guard.js`, `page.js`, `policy.js`, `manifest.json`,
`policy.py`, `sites.py`, `qualification.py`, `committed.py`, `uploads.py`, `qualify.py`.

## Acceptance

- The seventeen tools exist with the inputs and results above; brief 20's replaced tools are gone.
- Groups 14, 15 and 16 pass, and groups 1 to 13 pass twice on the final head.
- Every budget holds against the committed baseline.
- The generated Chrome ask rules are byte-identical to `main`'s.
- `HARNESS-MAP.md` accounts for every changed helper and every rewritten staleness test.
- No secrets, real addresses, account names, provider names or real sites.

## Report (`reviews/28-chrome-capability/REPORT.md`)

AGENTS.md's format (Done, Verified, Not verified, JUDGMENT-CALL, PLAN-GAP, Open questions), and in it:

- the baseline and the measured numbers side by side, per task, with run ids;
- the outline of each fixture as returned (short ones in full, long ones by their first 40 lines);
- the tool descriptions and instructions as Claude will read them, with anything you are unsure reads well;
- what changed in `adapter.py`'s `payload` and `facts`, line by line, and a statement that nothing else in the
  asking path changed, with the diff command that shows it;
- the harness map and the inventory mapping;
- every claim marked **run** (workflow run id and log line), **read** (file and line) or **assumed**.

**Known limits.** Keep `reviews/28-chrome-capability/KNOWN-LIMITS.md`: start from section 6's "Known limits", and
for every line you add, change or find untrue give what it is, the harm and why it is acceptable or not. The lead
moves the result into section 6. A flaw with real harm (an action without its question, a password read, data
loss, his normal use broken) is never a limit: fix it or stop.

## JUDGMENT-CALLs

None is open for the owner before this package starts. Decided here, and the lead's to defend:

- A reference is checked on its own element, by a fingerprint the service keeps, not on the whole view (item 3;
  section 6 gives the reasons and names what is no longer checked).
- The tool list is replaced, not kept beside the new one: one surface to describe, test and review.

Anything you meet that changes how Chrome feels for the owner goes into the report as a JUDGMENT-CALL with what you
chose, what you rejected, why, and what changing it later costs. Likely candidates: a fold that hides something
Claude nearly always needs; a wait that is too short or too long on real-looking pages.

## If unsure

Take the option that keeps a send from going without its question or going twice, that never returns a password,
and that never says something happened or was stopped when the tool can't know. Then the option that returns
fewer characters. Say what you chose in the report.

## Stop rules

- Stop and report, rather than weaken a rule, if a budget can only be met by leaving out something Claude needs to
  act safely, or if the asking path would have to change.
- Stop if any test would need a real site or a real account.
- The full `control-chrome.yml` suite takes three to four hours a run. Develop against the browser-free tests and
  the short job. Plan about 10 full runs; tell the lead in the report before passing 14. Wait on each run with one
  blocking call; never poll turn by turn. Mark report-only pushes `[skip ci]`.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in your worktree, on branch `pkg/28-chrome-capability`, from `main` after PR #27's merge. Commit in
  small steps, push this branch, open a draft PR against `main`. Never merge, never push to `main`, never
  force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- On the laptop: one test suite at a time, `pkg28-` names for scripts and `/tmp` paths, and check free memory first.
- Name your model in a commit trailer.
