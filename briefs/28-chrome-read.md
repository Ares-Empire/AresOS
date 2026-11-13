# 28: Chrome reading: the baseline, the shared rules and the new read

**Goal:** the first of three packages that give Claude a Chrome tool which costs far less to use than the one brief
20 built, with the same questions before every send. This package records what brief 20's tools cost. It builds the
two rules that everything later shares: how a field's value is kept out, and how an address is written. And it
builds the new read: a compact outline of a page with short references, folds, paging, `find`, `until` and several
tabs in one call. **What Claude is offered doesn't change here,** except four stricter field rules that fix real
harm ("What must not change"). The new read runs through an internal action and CI. PR #27's tool list, and its way
of acting by `reference` and `expected`, keep working untouched.

The owner's words (2026-11-11): "I don't just wanna rebuild Claude in Chrome. I wanna make a better tool for AresOS
that's more efficient with readings, navigation, free tab navigation etc."

**Three packages, in this order.** The lead split the first design of brief 28 on 2026-11-13, as package re-check 2
advised (`reviews/28-chrome-capability/` holds the design's reviews):

1. **28, this brief:** the baseline, the shared rules and the new read. It waits for PR #27 (brief 20).
2. **28a** (`briefs/28a-chrome-act.md`): the new tool list, acting by short reference, `chrome_open`, `chrome_go`,
   `chrome_do`, the smaller tools, the harness migration and the final budgets. It waits for 28.
3. **28b** (`briefs/28b-chrome-his-tabs.md`): Claude looks at his open tabs in place. It waits for 28a.

Each package leaves `main` working and is reviewed by itself. **None of the three reaches the owner's laptop before
all three are merged:** 28 and 28a keep brief 20's check before a taken tab's reload, which 28b replaces. The owner
has answered every question of all three ("Already decided" at the end).

**Building starts only after PR #27 (brief 20) is merged.** Branch from `main` after that merge and work on top of
it. Paths and line numbers in this brief come from PR #27 at `8b7e799c`; read them again on merged `main`.

**Builder (recommended, the lead confirms at launch):** a Claude agent on Fable 5.2. The work is inside a dense,
security-reviewed reader, needs judgment about what an outline should show, and must not be cut off halfway; Codex
is away from about 2026-11-14 to 11-17 and ends on 11-21. **Review** (`docs/REVIEW.md`, "Tools for Claude"): two
fresh reviewers at once, a package review and a security review, Codex while it is available, otherwise Claude.
This package makes the password rule stricter and puts a refusal in front of the asking path (item 1), so its
security review is one of the high-stakes ones: Fable 5.2, or Codex's frontier model while it is available. The
package review runs on Opus or Codex's workhorse.

## Background (read first)

- `docs/design/CONTROL.md` **section 6 is this package's specification**: "What the extension can and can't do"
  (the password rule), "Reading a page", "Efficiency, as a tested property", "Known limits" and test groups 14 and
  16 under "Tests". Sections 3 and 4 are the rules every action follows. Where this brief and section 6 differ,
  tell the lead in the report (PLAN-GAP); don't pick one silently.
- `docs/control/PLAN.md`: decisions 24 and 25 and the entries of 2026-11-11 (the owner's bar and his words).
- `docs/REVIEW.md`, "Tools for Claude": the bar the reviewers use.
- `reviews/28-chrome-capability/BRIEF-SECURITY-2.md` and `BRIEF-REVIEW-2.md`: the design's last reviews. This
  brief works their findings in; where it names one ("security re-check 2", "package re-check 2"), that is the
  file.
- `reviews/20-chrome/REPORT.md` (the newest sections first, "Measured views", and a latency section if the merged
  tree has one), `reviews/20-chrome/KNOWN-LIMITS.md` and `reviews/20-chrome/TOOL-DESCRIPTIONS.md`.
- The code, before you change it:
  - `control/aresos_control/chrome/adapter.py`: `read`, `facts`, `payload`, `steps` and `call`;
  - `control/aresos_control/chrome/bridge.py`: `Bridge.call` and `read`;
  - `control/aresos_control/chrome/definitions.py`;
  - `control/chrome/extension/reader.js`: `snapshot`, `targetFacts`, `field`, `formFacts`, `safeValue`,
    `password`, `ownPassword`;
  - `control/chrome/extension/background.js`: `facts`, `collection`, `dispatch` and its queue (`serial`);
  - `control/chrome/ci/browser.mjs` (the helpers `rpc`, `call`, `read`, `target`, `nav`) and `ci/verdicts.mjs`;
  - PR #27's asking read, `chrome_read_typed_fields`, wherever the merged tree has it.

**Why brief 20's tools cost so much** (read in its code and reports):

- A read returns one JSON line per element with a six-field reference, everything the element holds (`expected`,
  with its box) and its text. A container's text repeats the text of everything inside it. The long fixture (120
  paragraphs, 80 fields, about 57,000 characters of content) comes back as 221,477 characters in 14 calls.
- Every action must send `reference` and `expected` back. A reference is bound to the whole view. After an action
  that changes the page, and most do, every reference from before is stale, and the next action needs a new read
  or `chrome_find` first. `chrome_fill_form` is the exception: it fills up to 32 fields in one call and refreshes
  the view between them itself.
- `chrome_open` and `chrome_navigate` return before the page has loaded. Claude then calls `chrome_wait`, which
  waits and returns the read: two calls where one would do.
- A result says what happened to the one element acted on, not what changed on the page.
- `chrome_tabs` returns 5 tabs per call, 10 at most.
- 28 tools at `8b7e799c`, with nine separate tools for the kinds of input; 29 once PR #27 has added its asking
  read for typed fields (item 5), which stays.

These are the costs of brief 20's tools **used well**, and the baseline measures them that way.

## Before anything else: record the baseline

Do this first, on merged `main`, before any change to the tools.

1. Add the fixture pages of "Tests, group 16" to the fixture server.
2. Write the scripted tasks of group 16 against **brief 20's tools as they are, used as well as they allow:**
   `chrome_wait` where a wait and a read are wanted, `chrome_fill_form` for several fields, `chrome_find` where one
   element is wanted, the largest `limit` for a list. A baseline made by using the old tools badly proves nothing.
   Run them in CI.
3. Commit the counts as `control/chrome/ci/efficiency-baseline.json`: calls and returned characters per task; the
   wall time of each task, from its first call to its last result, as the median of 5 runs after one warm-up run,
   with the runner's type; the characters of all tool descriptions plus the server instructions; the characters of
   all tool names plus input schemas (compact JSON); the run id. This file is the baseline for every budget, in
   this package and in briefs 28a and 28b. It isn't edited afterwards, except to add the timings of the
   side-by-side runs (below, and brief 28a's).

**Latency.** PR #27 at `8b7e799c` has no latency harness, no CI latency check and no latency section in its
report. The Chrome lead says they come with the part of PR #27 that follows brief 18d, under `control/chrome/ci/`.
Read the merged tree.

- **If they are there:** build group 16's timing into that harness (one harness, not two), keep its targets green,
  and add the comparison below to it.
- **If they aren't:** group 16 times its tasks itself, as step 3 says, in a short job of its own in
  `control-chrome.yml`. Say so in the report (PLAN-GAP). The latency acceptance is then the comparison below and
  nothing else.
- **The comparison, the same in both cases.** Runners differ, so old and new are timed in **one run**. In this
  package that is one task: the first read of F1, with brief 20's `chrome_read` and with the new read (item 6's
  internal action), five times each after a warm-up, medians compared. The new read passes at no more than 1.10
  times the old median plus 50 ms. That run's id and numbers go into the report and into the baseline file. Brief
  28a times the two acting tasks the same way, while both tool sets exist.
- Fewer characters don't prove a faster read. The timings are what shows it, and the report gives them beside the
  counts.

## What to build

### 1. The reader collects outline nodes (extension, read-only)

A new read-only command of the content script, `outline`, next to `read`. For every readable frame it returns the
frame, the document, the reader instance (item 3), whether the reader has watched the document from its start, the
address, the title, the scroll position and page height, how many nodes were left out, and `nodes`, a flat list in
document order. **A node holds, and nothing else:**

- `id`, the reader's element id, and `parent`, the id of the nearest ancestor that has a node;
- `role`, from the role list (item 2), with the level for a heading;
- `name`: the accessible name, whole;
- `text`: the element's own text **in order**, as a list of parts: a string for each run of its own text, and the
  id of a child node where that child stands between two runs. `<p>See the <a>timetable</a> for week 46.</p>`
  gives `["See the ", 12, " for week 46."]`. One joined string would lose where the link stands;
- for a field: `value`; or `unread` when the password rule keeps it out, with `filled` (true or false) where the
  history rule allows that much; and `error`, the text its
  `aria-errormessage` or `aria-describedby` points to while `aria-invalid` is true;
- `states`: only those that are set;
- for a link: `href`, resolved and in full (the service keeps it and shows the public form);
- for a form: `method`, `action` and the names of its hidden fields;
- for a `combobox` or `listbox`: the number of options, the chosen option's label, and the first 50 options
  (label, value, chosen, disabled). A read of that field by its own `ref` fetches all of them with a third
  read-only command, `options`, for one element;
- `title`, when the element has one that differs from its name; for a `frame`, the child frame's id.

The node never holds its descendants' text, a box or a style.

- **Roles come from a fixed list** (item 2), never from a page's own string. Brief 20's `role` returns a `role`
  attribute verbatim (`reader.js`, `role`), and the outline prints the role outside the quotes, so a page could
  write outline lines with it. For `outline` the reader takes the attribute only when its first word, in lower
  case, is on the list; otherwise it takes the role of the tag (the table in item 2); otherwise the element has no
  role. `targetFacts` keeps brief 20's `role` as it is, because the classification reads it. Names as the reader
  computes them today. Headings carry their level.
- **The password rule comes first, and it gets two additions** (section 6, "What the extension can and can't do").
  The exclusion check runs before every value or text read, in every frame and shadow root; a password-kind field
  yields its label and the kind, nothing else. The additions are built into the reader's own functions, so every
  reader of a page gets them: `outline`, brief 20's `read` and `facts`, the binding and the question. That is
  why they change what brief 20's tools return and accept already in this package; "What must not change" lists
  the four effects. **Read the merged reader first.** PR #27 builds the asking read before it merges, and with it
  the withholding that read depends on. What the merged reader already does of the rules below, keep and cover
  with this package's tests. What it doesn't do, add. Say in the report which was which.
  - **Names** (in `password`, the one exclusion function). A field a person types into (not `type="hidden"`) is a
    password-kind field when its `name`, `id`, label, placeholder, `aria-label` or `autocomplete` holds a
    credential word. **This rule stands above every other and wins everywhere:** in every document, however long
    the reader has watched, and whatever the element is: an `input` of any type, a `textarea`, an editable area.
    The words are in the definitions, versioned like the send-word list: password, passwort, kennwort, passcode,
    passphrase, pwd, pin, otp, totp, tan, mtan, 2fa, mfa, secret, token, seed, mnemonic, cvv, cvc; `code` only next
    to one of verification, verify, security, sms, login, auth, recovery, backup, card, einmal, bestätigung,
    sicherheit ("verification code", "card security code", "Einmalcode"); `key` only next to one of private, api,
    secret, access, recovery, signing; `phrase` only next to one of recovery, seed, secret. They match as whole
    words and as parts of a name (`user_password`, `otpCode`), never inside
    another word (`shipping` is not `pin`). Such a field is handled exactly like `type="password"`: not read, not
    typed into by Claude, bound by its presence only. Keep the words in a new module beside `policy.py`, with a
    copy inside `reader.js` that a test compares with the definitions; `policy.py` and `policy.js` stay untouched,
    so the send-word classification can't change by accident.
  - **History** (in the value reader, `safeValue`). In a document the reader has watched since before the page's
    scripts ran (brief 20's preload: Claude's own tabs, and a taken tab after its reload), brief 20's rule knows
    every field's past. In every other document (a taken tab before its reload, a frame the preload missed, and
    with brief 28b each of his tabs read in place) it can't know whether a field was a password field before the
    reader arrived, and a password he made visible looks like any other text. **A field's present type proves
    nothing about its past** (security re-check 2, finding (a); the lead's decision, 2026-11-13). A password field
    can have been switched to `search` or `email` as easily as to `text`, and brief 20's own rule protects a
    masked `textarea` too (`ownPassword` in `reader.js`). So in such a document:
    - **a typed field returns no value.** A typed field is every `<input>` that can hold typed text, whatever its
      type (`text`, `search`, `email`, `url`, `tel`, `number`, no type, and every type the next point doesn't
      name), and every `<textarea>`. The reader says only whether it is filled: `(filled, not read)` or
      `(empty)`. It looks at the value's length inside the content script and keeps, traces and returns nothing
      else of it. The way to such a value is to ask him: brief 20's asking read, `chrome_read_typed_fields`
      (item 5), which covers single-line and multi-line form fields alike;
    - **kinds whose value isn't typed text keep it:** `checkbox`, `radio`, `range`, `color`, the date and time
      kinds (`date`, `time`, `datetime-local`, `month`, `week`), and a `select`. The browser itself forces these
      values into a fixed shape, so none of them can still hold a password;
    - **an editable area (`contenteditable`) is read.** Whole-page editors are editable areas, and what he writes
      in one must be readable. What that leaves is the one written known limit: a secret in an editable area
      whose mask was taken off before the reader came and whose label doesn't name it (section 6);
    - **above all of it:** a field named like a credential is never read (the name rule), and a field that is
      masked right now is never read (brief 20's rule), whatever element it is.
    The reader knows which case a document is from how it was installed, never from anything a page can set; when
    it can't tell, the document counts as not watched. `reload_state` keeps comparing a field with its default
    inside the content script; only its counts leave.
  - **History, inside a watched document: a shadow root the reader met late.** Brief 20's observer learns of a
    shadow root only at the next change it sees in a tree it already watches. A component that attaches its root
    to an element that is already in the page (a custom element upgraded after the load) causes no such change.
    He can type into its field and make it plain before the reader has met that root at all. So when the reader
    first meets a shadow root, a typed field in it (an `input` that can hold typed text, or a `textarea`) that
    **already holds text** has no known history: it is `(filled, not read)` for the life of the document. An
    empty one is watched from then on.
  - **A field whose value isn't read is not typed into either.** A `fill` or a key on a field that is
    `(filled, not read)` is refused like one on a password field (`owner_signin`), because it would overwrite what
    Claude can't see.
  - **A form that holds such a field is not sent by Claude** (security re-check 2, the new fix; the lead's
    decision, 2026-11-13). Brief 20's form facts take each field's value from `safeValue` (`field` and
    `formFacts` in `reader.js`), and the binding and the question are made from those facts (`binding` in
    `adapter.py`). A field withheld for unknown history has no value there. A question about its form wouldn't
    show what is sent, and it couldn't notice one draft replaced by another. So:
    - the reader marks a field withheld for unknown history as exactly that, apart from a password-kind field.
      A known password field keeps brief 20's rule: named by its label, bound by its presence;
    - a step the service recognises as a send, a delete, a payment or a form submission is **refused before any
      question** when the binding it would need holds a field with that mark: a field of the form being
      submitted, or, for a send outside a form, a field of the draft brief 20 binds. A submission that the page
      starts and the tool holds is treated the same way: it isn't prepared, it stays stopped, and it is reported
      with this reason;
    - the code is `refused` and the message is the tool's own: "this form holds a field the tool may not read;
      the owner sends it himself, or the page is reloaded first (for one of his tabs: take it with a reload)";
    - **an approved asking read doesn't lift it.** That read shows Claude a value once. It doesn't make the
      field readable for a binding;
    - a free step isn't touched: a GET search form has no question that could be wrong.
- Left out: scripts, styles, hidden elements, elements behind an open modal dialog, frames of the fixed list.
  Frames of other sites and open and closed shadow roots are included, as today.
- No box, no computed style beyond what the checks above need. The command must be cheaper than `read` on the same
  page (the latency comparison above).
- At most 20,000 nodes per tab. Beyond that the reply says how many were left out.

A second read-only command, `page_state`, is the one cheap question the service asks about a tab. The background
script answers it from every readable frame's reader and from what it knows itself:

- `token`: one opaque string that changes whenever what a read returns could have changed. Per readable frame the
  reader gives its document and instance, its count of DOM changes (brief 20's `revision`), a digest of its
  address, and a digest of the live state of its fields: for each `input`, `textarea` and `select` the tick, the
  chosen option and the value, and for a field whose value isn't read only what the outline shows of it (that
  it is there, or whether it is filled). The background
  script joins these with each frame's id and Chrome document id. Brief 20's `revision` alone isn't enough: typing
  into a field changes no DOM node, and a change in a frame doesn't move the top document's count;
- `document`, the top frame's Chrome document id, and `address`, a digest of the tab's full address;
- `ready`: whether the top document's `readyState` is `complete`;
- `dialog`: whether a native dialog is open, and `queued`: whether page steps are queued (brief 20's
  `queued_steps`). While a dialog is open the readers can't answer; the reply then holds `dialog: true` and no
  token.

The service uses it to wait and to bind a cursor (item 2), and brief 28a uses it to look at the tab between the
steps of a list. It never polls with full reads.

**Waiting, defined once** (for `until` and for a cursor here; brief 28a adds "loaded" and the change report on
the same token):

- **Quiet:** the token hasn't changed for 150 ms.
- **`until`:** the service asks `page_state` every 100 ms and reads the outline again only when the token moved.
  `text` is met when the text is in the page as `find` would find it (literal, without regard to case, folded
  parts and frames included); `gone` is met when it isn't.
- At the timeout the call returns what is there, with `until_met: false`.

`background.js` gets these three read-only commands (`outline`, `options`, `page_state`) and the time checks of its
queue and its waits (item 4). **Nothing else in `background.js` changes in this package:** not `input`, not
`resume`, `dialog`, `take`, `prepare_control`, `release`, the debugger methods or the session rules.

### 2. The outline, the addresses and the new read (service)

The service renders the nodes; the reader only collects. Put the rendering and the references in a module of their
own (for example `control/aresos_control/chrome/view.py`), tested without a browser against recorded node lists.

**A word on names.** Where this brief writes `chrome_read` with the inputs below, it means the new read. In this
package it is reachable only as the internal action `chrome_outline` (item 6). What Claude is offered under the
name `chrome_read` stays brief 20's tool until brief 28a switches the list.

**Addresses: a public form, and a short form for lists and records** (section 6, "Reading a page"). One function in
the service, `public_address`, writes an address that leaves the service; once brief 28a is merged, no other code
does. **The owner decided this on 2026-11-13 (board #213, "Show link addresses"):** on a page Claude reads, it sees
link addresses with their query, as in any browser tool, and only what looks like a sign-in is hidden by the rule
below. He chose this knowing that a short sign-in code in a link can slip through; that is a known limit (section 6),
not a finding to reopen.

**The public form** holds:

- the site: the host in lower case and ASCII, with the port when it isn't the scheme's default, and `http://` in
  front when the address isn't `https`; **never a user name or a password**;
- the path as the browser gives it, with two cuts. After a segment that holds a sign-in word (reset, verify,
  confirm, activate, magic, token, invite, auth, oauth, sso, saml, login, signin, logon, callback, password,
  passwort, otp; as a whole word or a part of the segment), everything that follows is one `…`. And a segment that
  **looks random** is `…`;
- the query, parameter by parameter, names shown. A value is replaced by `…` when:
  - **its name is a credential name.** The name, split into parts at `_`, `-`, `.`, brackets and a change of case,
    has one of these words as a part: token, code, key, secret, signature, sig, password, passwd, pwd, auth,
    session, sid, otp, ticket, state, nonce, jwt. So `access_token`, `id_token`, `refresh_token`, `api_key`,
    `client_secret` and `sessionToken` match. A name written as one word (`apikey`, `sessionid`, `authtoken`)
    matches when it begins or ends with one of the words; or
  - **the value looks random,** tested after percent-decoding.
  A parameter without `=` is a value without a name. A name that itself looks random is `…` too;
- the fragment, treated the same way: like a query when it holds `=` (`#access_token=…&state=…`), like a path when
  it holds `/` (a single-page site's route), and otherwise shown unless it looks random;
- at most 300 characters, the rest counted as `…+N`; and nothing but letters, digits and
  `. - _ ~ / % : ? & = + # ; ,` besides the `…` marks. Everything else is percent-encoded, so an address can't
  break an outline line.

**Looks random** means one thing everywhere: a run of 20 or more letters and digits with at least one letter and
one digit in it, or 24 or more hex digits once the hyphens are taken out. An 11-character video id, a page
number, search words and a slug with a year in it stay. A session token, a sign-in code, a UUID and a JWT don't.

**The short form** is the public form with the query and the fragment reduced to the marks `?…` and `#…`: the
site and the path, nothing else. It is for lists, where Claude is shown pages his request may have nothing to do
with, and for records, because a record needs no query value (owner, 2026-11-13, board #213).

**In this package the function is built with both forms and tested as a function, and the new read uses the
public form:** the `url` of a page, a link's and a form's target, detail reads and `find`. Brief 20's tools keep
writing addresses as PR #27 writes them. They compare the `expected` a caller sends back with what the reader
shows, so their results can't be rewritten under them, and nothing reaches his laptop before the list is
switched. Brief 28a puts the function in front of every other surface: the lists, the questions, the stage texts,
the notices and the log (its item 3).

Full addresses stay inside the service and the extension: in the reference table and in the commands to the
extension. Claude uses an address it can't see whole by reference. Brief 28a builds that: `chrome_open` takes a
link's `ref`, his tab's number or a library entry's `ref`. So a `…` never blocks a navigation.

**The outline format** (normative; section 6 shows an example):

```
line    = indent role {" " part} [" = " value] {" " state} [" → " target] [" " ref]
indent  = two spaces per level of depth
role    = one word from the role list below, nothing else
part    = quoted | "[" role " " quoted [" " ref] "]"
quoted  = the accessible name, or a run of own text, in double quotes
value   = a field's value in double quotes; (not read) instead for "password"; (filled, not read) or (empty)
          instead for a typed field whose history the reader doesn't know (item 1)
state   = checked | selected | disabled | required | invalid | expanded | collapsed | current | readonly
target  = for a link that leaves the page's site: its site; for a form: its method, site and path
ref     = five letters and a number, for example kqtvm5 (item 3)
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
  marks `=`, `→`, `·`, `›`, `|`, `[`, `]`, `(`, `)` and `…`. This holds for the outline, for every `ref` form (tables
  and forms included), for `find`, for the change report and for the present line of a stale reference.
- **A refusal never carries page text in its message.** The message is the tool's own fixed sentence. Where the
  element's present line is given (a stale reference), it sits in `untrusted_content`, rendered and escaped like
  any outline line: in that read's entry beside its `error`. Brief 28a says where the tools that act put it.
- Text appears once, on the deepest element that owns it. A label whose text is its field's name gets no line of
  its own. An element without a role, a name or own text gets no line, and its children move up a level.
- **Text keeps its order.** A line's quoted runs and its inline children alternate as they stand in the page. A
  child stands inline, in square brackets, when it is a link or a control with nothing below it and its parent has
  text of its own: `p "See the " [link "timetable" kqtvm12] " for week 46."`. Every other child gets its own line,
  one level deeper, in document order; where the parent's own text runs between such children, each run is a
  `text` line in its place. Brackets outside quotes are always the tool's: a page's text is only ever inside
  quotes.
- A name or value can never start a new line or end its quotes (the escaping rule above).
- **Folds** (each says what it hides):
  - a name, a text or a value longer than 200 characters is cut and ends in `…+N`, N being the characters left
    out; the element's reference reads it whole;
  - of more than 8 neighbours with the same role, the first 5 are shown, then `… N more (C characters) kqtvm17`; that
    reference reads exactly the neighbours left out, and nothing can act on it;
  - a table is its line and `… R rows, C columns (N characters)`; the table's reference reads it;
  - a list of more than 12 options is `(N options)` on the field's line, with the chosen one as the value;
  - a form shows its first 40 fields, then a fold like the one for neighbours; hidden fields are `(N hidden)` on
    the form's line.
- **The order of folding,** from the top of the tree down: (1) a table folds whole; (2) inside a form, the fields
  after the 40th fold into one line; (3) among the children of one parent, a run of more than 8 children in a row
  with the same role shows its first 5 and folds the rest, except a form's fields, which follow (2) alone; (4) a
  list field with more than 12 options shows its count; (5) on every line that is shown, the name, each text run
  and the value are cut so that the line's quoted text has at most 200 characters, with inline children after the
  cut left to the element's own `ref`. What sits inside a folded part isn't rendered, so it has no folds of its
  own until it is read.
- **What the numbers count:** characters of outline text. The number in a fold line is the length of what a read
  of that fold returns with `full`, before any cut by `max`. `…+N` is the number of characters left out of that
  line's text. R and C of a table are its rows and its widest row's cells.
- **A fold's reference** stands for "the children of this parent from this child on, with this role". The table
  entry (item 3) holds the parent, the first hidden child and the role. The same fold keeps its reference across
  reads for as long as that parent and that child live. A read of it returns those children as they are then. It
  is stale when the parent or that child is gone. Nothing can act on it. A folded table and a cut text
  need no reference of their own: the table's or the element's reference reads them.
- A reference is put on every element that can be acted on, and on every element that can be read by itself: a
  form, table, list, landmark, dialog, article or frame, and anything cut or folded.

**`chrome_read`** (effect read).

Input: `tab` (integer), or `tabs` (2 to 5 integers; then only `max` may accompany it); `ref`; `full` (boolean);
`find` (1 to 200 characters); `role` (with `find`); `until` (an object with `text` or `gone`, each up to 200
characters); `timeout_ms` (0 to 6,000, default 3,000, with `until`); `max` (1,000 to 40,000; default 6,000, or
3,000 per tab with `tabs`); `cursor`.

Result:

```
{"reads": [{"tab": 412, "whose": "claude", "characters": 4211, "total": 18840, "cursor": null,
            "mid_line": false, "until_met": true, "typed_fields": 0,
            "untrusted_content": {"url": "…", "title": "…", "scroll": "0/3200", "outline": "…", "dialog": null}},
           {"tab": 413, "error": {"code": "refused", "message": "…"}}],
 "version_notice": null}
```

- No `ref`, no `find`: the outline with its folds.
- `ref`: that element with **one level unfolded**, in the form that fits its role: its own name, text and value whole,
  and its direct content complete (every row, item, field or hidden neighbour). Below that level the fold rules apply
  again. A table: the table's own line, then a line `columns: "A" | "B" | "C"`, then one line per row, not indented,
  with each cell in quotes and the cells separated by ` | `, and controls inside a cell as `[link "Open" kqtvm31]`.
  A list: its items. A form: every field as an outline line with its
  options (up to 50 per field, more by the field's own `ref`), `required`, the field's error text, the hidden fields by
  name, the buttons, and the form's target. A text: in full. A single link or control: everything known about it (its
  address in the public form, the title, all options).
- `typed_fields`: how many fields of this tab the read shows as `(filled, not read)` and the asking read could
  return once he agrees (item 5). It is the tool's own number, outside `untrusted_content`. Credential-like
  fields aren't counted. A normal read never returns those values, with any input.
- `full`: **no fold and no cut** below the starting point: the whole page without `ref`, the element and
  everything under it with `ref`. This is how Claude reads all of something in a few calls, paged by `max` and
  `cursor`.
- Everything a read returns from the page sits in `untrusted_content`, also what `ref`, `find` and `until` bring.
  Outside it are only the tool's own numbers and flags.
- `find`: up to 20 hits per page. Each hit is the element's outline line, then ` · in ` and the path of named ancestors,
  outermost first, each as its role and quoted name, joined by ` › ` (at most 80 characters); a hit inside a longer text
  adds 60 characters either side of it. Literal, no regard to case, over names, labels, values that may be read, and
  text; folded parts and frames included; inside `ref` when both are given. `role` keeps only that role.
- `until`: as item 1 defines waiting; the result carries `until_met`.
- `tabs`: each tab is read by itself. A tab that can't be read (not in Claude's group, the fixed list, a dialog,
  no answer in its share of the time, item 4) gets its `error`; the others are returned.
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

### 3. References, as far as reads need them (service)

This package issues references and resolves them for reads. Acting on one, and the fingerprint that guards it,
are brief 28a's (its item 2).

- **A reference is five letters and a number, for example `kqtvm5`.** The service issues it:
  - **The letters name this run of the service.** The service draws them from the system's random source when its
    process starts: five consonants, so they spell nothing, one of about four million combinations (21 to the
    fifth). Nothing about earlier runs is stored or remembered, so the rule doesn't depend on the store.
  - **The number comes from one counter for the whole process, across all tabs.** It only counts up. It isn't reset
    when Chrome restarts or reconnects, when a tab closes or when entries are dropped. Tab A and tab B can never
    both hold `kqtvm5`.
  - The same live element (same connection, tab, frame, document, reader instance and reader id) gets the same
    reference in every read and result.
  - **What this guarantees, said honestly** (package re-check 2, N1, and the security re-check's residual). Within
    one run no string is ever issued for two things: the counter sees to that. Between two runs the letters
    differ by chance, not by proof: two given runs share them once in about four million. So a reference from an
    earlier run is unknown to the new one in practice. If the letters did repeat, the old reference would resolve
    only where the new run issued that same number for that same tab; an action on it would still have to match
    the fingerprint the service holds for the new element (brief 28a), and a send would still ask. Section 6
    lists this under known limits. An earlier draft drew three letters and remembered the last 100 runs; after
    the 101st run a prefix could come back with the store intact, so that record is gone.
- **Per reference the service keeps** the extension connection it was issued under (the `session` of the
  extension's hello), the tab, the frame, the document, the reader instance, the reader's element id, and **the
  line it last showed Claude** for that element. It keeps the newest 5,000 per tab, in memory only. A dropped
  entry is gone for good: its string is never issued again, so an old reference can't come to mean a new element.
- **The reader instance.** Brief 20's reader numbers its elements from `e1` each time it is installed, while its
  document id survives a release and a new take of the same page. So `(document, e5)` can name two elements over
  time. The reader therefore draws a random instance id at each install and returns it with `outline`; the table
  keeps it, and a different instance means the reference is stale. Brief 20's `read` and `facts` replies don't
  change in this package; brief 28a adds the id to `facts`, where acting needs it.
- **A read by `ref` is refused with `stale_reference` when:**
  - the reference isn't in the table: invented, dropped, or issued by another run of the service;
  - it was issued for another tab than the one the call names;
  - it was issued under another connection (Chrome or the extension restarted or reconnected; the service empties
    the table then and the counter goes on);
  - the document, the reader instance or the element is gone or is another one.
  Where the element still exists, the refusal carries its present line. An element that only changed is read as
  it is now: a read can't overwrite anything, so it needs no fingerprint.
- No brief 20 action accepts a short reference in this package, and no brief 20 result carries one.

### 4. Time: a read ends before its caller gives up

The base's client waits 10 seconds for a read and 30 for a change (`READ_TIMEOUT` and `CHANGE_TIMEOUT` in
`protocol.py`), and the CI harness waits 20. A caller that times out doesn't know what ran, while the service
would go on. So every new tool has one deadline, measured in the service from the start of the call, and no
timeout is raised. This package builds the read's deadline and the way a deadline reaches the extension. Brief
28a adds the deadlines of the tools that act, on the same mechanism.

The deadline covers the whole call, not only the new read inside the adapter. The engine looks at pending
operations before it dispatches and again when it builds the response, and a reserved Chrome operation asks the
extension whether it is still valid (`Chrome.pending_state`, through the bridge) at both points. Start the call's
time budget before that first look and carry it through the response. A validity that couldn't be checked in time
is reported as unchecked, never as a refused approval, and the pending warnings stay. Test it through the real
transport: a read with an approval outstanding whose frame doesn't answer still ends inside its deadline.

- **The read: 8 seconds in all.** `until` waits at most 6, and every command of a read has to answer by
  second 7. A read that didn't gets the error `not_read`, "time ran out; read this tab by itself". With `tabs`,
  each tab gets an equal share of the time left to second 7 when its turn comes: with five tabs 1.4 seconds each
  at first, and time a tab doesn't use passes on. A tab that hasn't answered within its share gets `not_read`,
  and the others are returned.
- **The deadline reaches the bridge and the extension, and nothing more changes for it** (package re-check 2,
  N2). In PR #27 `Bridge.call` blocks until the reply comes, bounded only by the socket's 15 seconds (`bridge.py`,
  `daemon.py`). The extension runs its commands one after another and waits for frames without a bound (`serial`
  and `dispatch` in `background.js`). A deadline kept in the service alone would answer Claude while the
  extension still held work that runs later. So, exactly this:
  - **Every command of the new read carries the time it has left,** in milliseconds, set by the service from the
    points above. A command without it runs as PR #27 runs it, so brief 20's tools are untouched.
  - **The extension checks the time at two points.** When a command reaches the front of its queue: one whose
    time is up isn't started. And inside a command: every wait for a frame or for the reader is bounded by the
    time left. In each case the answer is `expired`. (Brief 28a adds the third point, right before an input is
    dispatched.)
  - **The bridge waits for a reply until the command's time is up plus half a second,** and no longer. Without a
    reply the command is given up, and the read answers `not_read`.
  - **Draining.** A reply that arrives for a command the bridge gave up on is read and dropped by its id. It is
    never taken for the next command's reply (PR #27 treats an unexpected id as a transport error). The next
    command is sent as usual, and given-up work can't run later, because the extension checks every queued
    command's time when it reaches the front. If the reply still hasn't come when the socket's own 15 seconds
    pass, the connection is closed as PR #27 closes it today.
  This touches `Bridge.call` and the queue and the waits of `dispatch`. Nothing else: no second queue, no
  commands side by side, and nothing in `input`.

### 5. The asking read stays as PR #27 built it

`chrome_read_typed_fields` is an asking read, under the managed ask rules. The owner, 2026-11-13 (board #210):
"Ask first." **Brief 20 builds this tool before it merges, and this package keeps it rather than redesigns it.**
Read its exact name, inputs and flow from the merged tree. What it is, as brief 20 builds it:

- it reads the typed fields a normal read shows only as `(filled, not read)`. **Eligibility follows the field,
  not the document: a typed field whose history the reader doesn't know** (item 1). That is every `input` that
  can hold typed text and every `textarea` in a document the reader didn't watch from its start, and one that
  already held text when the reader first met its shadow root in a watched document;
- its question names the tab and lists the labels of the fields it will read, with a stable description for a
  field without a label, and never a value;
- credential-like fields are never included, also when he approves: the name rule and brief 20's password rule
  stand above the approval;
- one approval covers one call. A refusal leaves `(filled, not read)` and `(empty)` as they were;
- **the approval is bound to a prepared read, as strictly as a send is bound to its input** (security re-check
  2, finding (c)). PR #27 implements this binding; this package and brief 28b must keep it, and neither brief
  claims that it is verified. As it has to be:
  - the service prepares the read before it asks. The preparation holds the connection to Chrome, the tab,
    each frame's document and reader instance, the exact identity of every field it will read (the reader's
    element in that frame, not its label), and the label or description shown for each. No value is read to
    prepare it;
  - the service generates the question from that preparation and, when the approval comes back, verifies the
    question and the preparation as strictly as it verifies a send's input. An altered question or list
    doesn't run;
  - the approval is used once;
  - right before any value is read, the preparation is compared with the page. A field replaced by another
    one, also by one with the same label; a field whose label or description changed; a frame that navigated;
    a field that has become credential-like (by its name, its type, its `autocomplete` or a mask): each
    refuses the whole read. No value is read, and Claude asks again;
  - so "the list of fields differs" means the fields' identities and descriptions, never their labels alone;
- the values come back marked as page text.

**What this package does with it, and nothing more:**

- it stays in the tool list exactly as PR #27 merged it: its name, its input, its result, its question and its
  ask rule, which is part of the generated rules that must not change by a byte;
- the fields it may read are those of this package: a taken tab before its reload, a frame the preload missed,
  and a shadow root met late. Brief 28b lets the tool work on his tabs read in place. The reader's own mark
  "withheld for unknown history" (item 1) is what makes a field eligible, so there is one rule, not a second
  list. If the merged tool decides eligibility by the document instead and so leaves out the late-root field,
  report it (PLAN-GAP) and make it use the mark; **that is the one change this package may make inside the
  asking read;**
- the binding above is PR #27's to build. This package runs the tests for it ("Tests"). If one fails on merged
  `main`, stop and tell the lead: the fix belongs to the asking read's owner, and nothing here builds on a
  binding that doesn't hold;
- the new read tells how many such fields a tab has (`typed_fields`, item 2). Brief 28a gives the tool its
  place in the new list, with short references in its result.

### 6. The internal action, and its test-only switch

The new read has to be reachable for CI, and for nobody else, in this package.

- The service registers one more action, `chrome_outline`, with exactly the input and the result of item 2's
  read, **only when it is started with a test-only switch:** an environment variable that the CI container sets
  and the image never does. One test pins that the packaged unit doesn't set it. Another pins that without it the
  action doesn't exist: not in the MCP tool list, not in the `aresos` command, not in any generated file.
- It goes through the same entry as every action (the `aresos` command and the MCP proxy), so the tests reach it
  through the real transports.
- It reads the tabs brief 20's `chrome_read` reads, under the same checks: a tab in Claude's group, the fixed
  list, the qualification mode, the queued page steps. Every other tab is refused as brief 20 refuses it.
- Its references work for further reads through it: a part by `ref`, a fold, `find` inside a part.
- Brief 28a turns this action into the public `chrome_read`, uses the switch once more for its side-by-side run,
  and then removes it.

## What must not change

- **What Claude is offered.** The tool list, every tool's name, input, result shape and description, the server
  instructions, and every generated file (`docs/control/TOOLS.md`, the ask rules, `user-mcp.json`) with its size
  stay byte-identical to `main` after PR #27. A test compares them. Brief 20's actions keep taking `reference`
  and `expected`, keep their whole-view check, and keep showing addresses as PR #27 shows them. Brief 20's groups
  1 to 13 pass through brief 20's tools.
- **Four exceptions, each a fix of real harm, each making a rule stricter, and nothing beyond them** (item 1).
  They live in the reader's own functions, so brief 20's tools get them in this package:
  1. a field named like a credential is read by no tool and typed into by none (the name rule);
  2. a typed field whose history the reader doesn't know shows only filled or empty, wherever merged PR #27
     doesn't already do that (the history rule, and the shadow root met late);
  3. a field whose value isn't read isn't typed into;
  4. a form that holds a field withheld for unknown history isn't sent by Claude.
  A harness test that asserted the old behaviour changes how it asserts, and `HARNESS-MAP.md` lists each one
  ("Tests").
- **The asking path:** the classification rules and the word list (`policy.py`, `policy.js`); `binding`, `prepare`,
  `question`, `revalidate`, `changed_compose`, `execute`, `command` and `trusted` in `adapter.py`; the adapters
  (`sites.py`); `chrome_submit`, `chrome_submit_trusted`, `chrome_drop`, `chrome_operation_status` and the notices;
  the 15-minute deadline; one approval, one run. **Nothing inside those functions changes in this package.** The
  refusal of exception 4 stands in front of them: `payload` and `steps` refuse before `prepare` is reached. Brief
  20's asking read belongs to the asking path too: `chrome_read_typed_fields` with its question, its binding to
  the prepared read, its one approval for one call, its refusal of credential-like fields and its new question
  when a field was added, replaced or relabelled. The one change allowed inside it is item 5's.
- **Security re-check 2 judged the place where this package touches the asking path, and it stays as judged**
  (`reviews/28-chrome-capability/BRIEF-SECURITY-2.md`, "Password additions"). Stricter secrecy takes content out
  of a send's question and comparison. That is why a form holding a field withheld for unknown history is
  refused, not asked (exception 4). A known password field keeps brief 20's rule. Show the lines in the report.
  The other three places it judged (addresses in a question, the reveal inside `input`, the asking read in the
  new tool list) are brief 28a's.
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

**Without a browser** (Python and Node):

- the outline renderer against recorded node lists: every fold, the order of folding, each fold's count against a
  `full` read of it, text with inline links in its order, every role of the tag table, every escape, depth, the
  `ref` forms, `find`, the cut at `max` and at 48 KiB with non-ASCII text;
- the reference table: same element same reference; one counter for all tabs; no string issued twice, also after
  entries were dropped at the 5,000 bound and after the table was emptied; every stale case of item 3 for a
  read; a new reader instance in the same document. The letters: five consonants from the system's random source, drawn
  once per process, with nothing read from or written to the store. **Beyond the old window:** 300 runs in a
  row, more than the 100 an earlier draft remembered, each issue references for the same tabs, and no reference
  of any earlier run resolves in any later one. The test puts a seeded generator in place of the random source,
  with a seed under which no two runs draw the same letters, so it is deterministic. **The rest, shown
  honestly:** two runs forced to draw the same letters; an old reference then resolves only where the new run
  issued that number for that tab, and the report lists the case under known limits;
- `public_address` against a table, in both forms: a user name and password, ports, a non-ASCII host, `http`; each
  sign-in word in a path; each credential name as a parameter, alone, as a part (`access_token`, `apiKey`) and
  written as one word (`sessionid`); values that look random (a UUID, 40 hex digits, a 43-character token, a JWT,
  one hidden behind percent-encoding) in a path, a query and a fragment; what must stay (`?v=` with an
  11-character id, `?q=` with words, `?page=2`, a slug with a year, a numeric id, a plain `#section-2`); a
  fragment that is a query and one that is a route; a parameter without `=`; the 300-character cut; and
  characters such as `|`, `[`, quotes, spaces and line breaks. The short form of each shows `?…` and `#…` and
  nothing of either;
- the read's deadline below the service (item 4). The bridge with a fake socket: a reply that comes after the
  bridge gave up is dropped and the next command gets its own reply; no reply at all closes the connection at the
  socket's bound; a read command without a reply is `not_read`. The extension's queue in the Node doubles: a
  command whose time is up at the front isn't started; a frame that never answers ends a read at its time with
  `expired`; a command without a time runs as before; with five tabs, a slow first one costs only its share;
- the reader's `outline` command in the Node VM doubles that `reader.test.mjs` uses, with the password fixtures:
  no node holds a value the password rule keeps out, in any of its fields;
- the refusal in front of the asking path (item 1), with a fake bridge: facts whose form holds a field marked as
  withheld for unknown history are refused in `payload` before `prepare`, for a click on a submit button, for
  Enter in a field and for a held submission in `steps`; the same facts with a password-kind field in its place
  are prepared as before;
- that nothing Claude is offered moved: the generated tool list, descriptions, instructions, ask rules and
  `user-mcp.json` are byte-identical to `main`'s, and the internal action is absent without the switch;
- the credential words: each word, as a whole word and as a name part, in each of the six places; `shipping`,
  `postal code` and `pinned` don't match.

**Passwords, in group 14 and in `password_exclusion`.** Group 7's fixtures and recording run over every output of
the new read, and again over brief 20's `chrome_read`, `chrome_find`, `chrome_read_form` and questions, which
share the reader's functions.
Added cases, each with group 7's known password and a label that says nothing ("Code"):

- **A field made plain before the reader arrived** (a taken tab before its reload): by `type` changed from
  `password` to `text`, and also to `search`, to `email` and to `url`; once by a removed
  `autocomplete="current-password"`; once by a removed mask (as a style and as a class), on an `input` and on a
  `textarea`; each in the page, in an open and a closed shadow root and in a frame from another site.
- **A sign-in code known only by its name** (`name="otp"`, a label "Verification code", no `autocomplete`), in a
  document watched from its start and in one that wasn't.
- **A shadow root met late, in a document watched from its start:** a custom element is upgraded after the load
  and attaches its root without any change the observer sees; the owner types the password with real keys and
  switches the field to plain text before the first read. Once with the label "Password" (kept out by its name),
  once with the label "Code" (kept out because it held text when the reader first met its root). In the same
  root, a field that was empty at that first meeting is read afterwards, and a `fill` on the unread one is
  refused. A `textarea` in that root that held text at the first meeting is unread in the same way.
- **What a document the reader didn't watch from its start shows** (the same taken, not yet reloaded tab): a
  draft he typed into an editable area is read whole; a `text`, a `search`, an `email`, a `url`, a `tel` and a
  `number` field, an `input` of an unknown type and a `textarea` show `(filled, not read)` or `(empty)` and never
  their values; a date field, a ticked box, a radio choice, a range, a colour and a chosen option keep their
  values.
- **The name rule wins there too:** an editable area labelled "Password", a `textarea` named `secret_value`, one
  labelled "Recovery phrase" and one labelled "Private key" are not read, in a watched document and in one that
  wasn't. An editable area and a `textarea` that are masked right now aren't read either.
- **The limit, shown honestly:** an editable area that was masked by a style, is labelled "Value", and was
  unmasked before the reader arrived is read. The report lists the case under known limits. A `textarea` with the
  same history isn't read: it shows `(filled, not read)`.
- **A form with an unread field isn't sent** (item 1), through brief 20's `chrome_click` and `chrome_press`, with
  the fixture receiver's log as evidence:
  - the late shadow root holds a form with the field that held text at the first meeting, a second field and a
    Send button. A click on Send, Enter in the second field, and a submission the page starts from a click
    handler: each is refused, or stays stopped, with the tool's own message; there is no question, and the
    receiver has nothing;
  - after an approved asking read of that field, the same click is still refused;
  - the same form with group 7's known password field in place of the unread one still asks and sends once, as
    before;
  - **a value change while an approval waits.** No approval can wait for such a form, and the test shows both
    sides of that. After the refusal the owner changes the unread field's text, and no operation exists that
    `chrome_submit` could run. And a form that was prepared while all its fields were readable, into which the
    page then moves the late root's filled field while the approval waits, is refused by `chrome_submit` (brief
    20's comparison: the form's fields differ), with the receiver at zero.
- Every surface of this package reads them: the outline, a form by `ref`, `find` for the password itself,
  several tabs, `until`; and of brief 20's tools a read, a find, a form read and a prepared operation's question
  for a form that holds such a field. Brief 28a runs the same fixtures over the tools it adds.
- Expected: the password fields are `(filled, not read)` or `password … (not read)`; the recording shows that the
  content script kept and sent none of these values, and the password is in nothing the extension received or
  sent, in no result and in no log line. After the tab's reload a plain, unnamed text field of that page is read,
  and the named ones still aren't.

**Group 14, reading and references** (browser), as far as section 6 marks it *brief 28*, through the internal
action. Fixtures (this package adds all of them, because the baseline needs them; F5 and F7 are used by brief
28a's tools):

- F1, brief 20's long page (120 paragraphs, 80 fields);
- F2, a table of 200 rows and 6 columns of text with a header row, each cell exactly 12 letters and digits (the
  budget row is computed from this size), and a small second table with a link and a checkbox in each row;
- F3, a listing of 300 links in a list, with navigation and footer link groups; one link has a name that no
  other link's name contains;
- F4, a form of 25 fields: text, a date, checkboxes, radios, a list of 200 options, a required field with an error
  text, three hidden fields, each kind of password field from group 7;
- F5, a page that changes part of itself on a click (5 rows replaced, a status line, one element renamed, one
  removed: at most 13 changed lines of at most 80 characters) and a page that loads a new document on a click;
- F6, a page with frames from a second fixture site and open and closed shadow roots;
- F7, three result pages, each with a title of its own and a link to the next. Each page's outline, that link
  included, fits the 4,000 characters a step returns for a new page;
- H1, hostile text: names and paragraphs shaped like outline lines, references (`kqtvm5`), folds (`… 40 more`),
  instructions to Claude, quotes, line breaks and direction-changing characters; a page of 100,000 elements; a name
  of 100,000 characters.
  - **Hostile roles:** a `role` attribute that holds a line break and a whole outline line with a reference; one
    that holds `button" kqtvm5`; one of 10,000 characters; one in capitals with spaces around it. Each line shows a
    role from the list or the tag's role, and nothing else of the attribute.
  - **Hostile text everywhere:** the same strings as a name, a value, an option label, a cell, a column header, a
    title, an error text and an ancestor's name come back quoted and escaped in the outline, in a table, a list
    and a form read by `ref`, in a `find` hit with its path, and in the present line of a stale reference. A
    stale reference's message holds nothing from the page. (Brief 28a adds the change report.)

Small fixtures are compared with stored expected outlines, character for character.

**Paging, in group 14 and without a browser.** A text of 100,000 characters read by `ref` with `max` 1,000 comes back
whole over its pages, each page holding at least one character and marked `mid_line` until the last; the pages joined
equal the text. The same for a table row wider than `max` and for a value of 20,000 characters read in full. A page of
text outside ASCII (6 bytes a character) and one made of quotes stay inside 48 KiB as sent, measured on the real result
with a pending operation and the version notice present, and still advance. Five tabs of such text: each gets its share,
each has its cursor, and the whole result fits. A cursor used with another `ref`, `find` or `full` is refused. `full` on
F1 returns every paragraph whole and every field, with no fold and no `…+N`.

**The state token and waiting, in group 14.** Typing into a field, which changes no DOM node, moves the token. A
change inside a frame moves it. An unchanged page keeps it over 100 polls. `until` is met by a text that appears
only as a field's value, and by one that appears inside a frame. A cursor is refused after a field's value
changed. `until` on a page that never goes quiet returns when the text is there. (The "loaded" cases of
`chrome_go` are brief 28a's.)

**References that can't collide, in group 14.** Each case first makes sure that new references exist, so a refusal
isn't just an empty table:

- Two tabs show the same fixture and both are read: no reference string appears in both outlines, and each of tab
  A's references is refused when a read by `ref` names tab B.
- Chrome is restarted (and, separately, only the extension's connection is cut), the same pages are opened and
  read again: every reference from before is refused, and none of the new strings equals an old one.
- The service is restarted, the same tabs are read again: every reference from before is refused although the new
  counter has passed the old numbers.
- More than 5,000 elements are read in one tab: a reference dropped from the table is refused, and its string
  isn't issued again.
- A tab is released and taken again without a reload in between: a reference from before is refused, although
  the document id and the reader's element id are the same.

**The asking read, in group 14.** PR #27 brings tests for its tool; they pass unchanged. These cases run on the
tool as PR #27 merged it, with the taken, not yet reloaded tab. Where PR #27 doesn't already have one of them,
this package adds it:

- the new read shows the typed fields (a `text`, a `search` and an `email` input, and a `textarea`) as
  `(filled, not read)`, returns none of their values with any input (`ref`, `full`, `find` for a value), and
  counts them in `typed_fields`; brief 20's `chrome_read` returns none of those values either;
- **approved:** the result holds exactly the fields the question listed, with their values as page text;
- **a credential-named field is absent though he approved:** a field named `otp`, one labelled "Password" that is
  plain text, and one masked right now are in neither the question nor the result, and the recording shows their
  values in nothing the extension kept or sent;
- **a field added after the question asks again:** nothing is read, and the new question lists the new field;
- **the binding** (security re-check 2, finding (c)), each case with the recording showing that no value was
  read:
  - a field replaced, while the approval waits, by another field with the same label;
  - two fields with the same label, and two without any label: the question tells them apart by their stable
    descriptions, and swapping the two while the approval waits refuses the read;
  - a frame that holds a listed field navigates while the approval waits, and the top document stays;
  - a listed field becomes credential-like while the approval waits (its type set to `password`; a mask added);
  - the question or the field list is altered between the question and the approval;
  - an approval used a second time (a replay);
- **a shadow root met late, in a Claude tab** (item 1's fixture): the typed field that held text when the reader
  first met its root shows `(filled, not read)` and is counted in `typed_fields`; the asking read lists it and,
  approved, returns it; the field named like a credential in the same root is in neither;
- **refused:** nothing is read, and the next normal read still shows `(filled, not read)` and `(empty)`;
- **one approval, one call:** a second call asks again;
- **the ask can't be skipped,** as for `chrome_submit` (group 12): an allow rule for the tool, and
  skip-permissions mode, still ask.

**Addresses, in group 14.** Fixture pages carry one marker value in every place a sign-in travels: under the
parameter names `code`, `access_token`, `sig` and `session`; as a random-looking value of 40 characters under an
ordinary name; the same in the fragment; as a user name and password; and as a 40-character path segment after
`/reset/`. They carry it in the page's own address, in link targets, in form actions and in a frame's address.

- The marker appears in no result of the new read: not in a page's `url`, a link's or a form's target, a detail
  read or a `find` hit.
- **An ordinary query is shown:** `?v=` with an 11-character id, `?q=red+shoes` and `?page=2` are in a read's `url`
  and in a link's detail read, as they are, next to a hidden `…` for the marker in the same address.
- Brief 28a runs the same fixture over every other surface: the lists, the questions, the stage texts, the
  notices and the log.

**Time, in group 14, through the real transports** (the `aresos` command and the MCP proxy, not a fake bridge):

- a read with `until` on a text that never comes returns within 8 seconds with `until_met: false`;
- five tabs of which one doesn't answer (a test build of the extension holds its reader's reply back) return four
  outlines and one `not_read`, within 8 seconds;
- after each case the next call on the same connection gets its own answer, and the reply the test build
  releases late changes nothing;
- brief 20's tools, whose commands carry no time, behave as before: their groups pass unchanged.

**Group 16, efficiency: the baseline and the read rows.** The baseline of "Before anything else" is this group's
first half. The second half measures the rows that need only the new read, through the internal action, so a
budget that can't be met stops the work here and not in brief 28a. **Each row names the exact calls it allows;
the test makes those calls and no others.** Characters are counted on the whole result as Claude receives it (the
JSON text of the tool result), for the baseline and for the new read alike. The build fails when a budget is
exceeded or when a number is worse than the baseline. Brief 28a's table holds the same rows with the same
numbers, measured again on the public tools, and adds the rows of the tools that act.

| Task | Budget |
|---|---|
| F1: the first read: the read with the tab | 1 call, the whole outline, at most 6,000 characters |
| F1: everything: the read with `full` and `max` 40,000, then the same call with each `cursor` it returns | at most 3 calls, at most 75,000 characters in all |
| F1: the 80 fields with their values: after the first read, the read with the form's `ref` | 1 further call, at most 6,000 characters |
| F2: the whole table: after the first read, the read with the table's `ref` and `max` 40,000 | 1 further call, at most the cells' own text plus 7 characters for each cell plus 800: 23,600 characters for this fixture |
| F3: find the one link with the unique name: the read with `find` and `role` | 1 call, at most 800 characters |
| Compare three open tabs: the read with `tabs` | 1 call |
| Latency ("Before anything else", the comparison in one run) | the first read of F1 is at most 1.10 times brief 20's median plus 50 ms; a latency check PR #27 brings stays within its targets |

**The rows add up** (package re-check 2, N3). Every budget counts the JSON text of the result, so each quote
of the outline costs 2 characters, each line break 2, and each `…`, `→`, `·` and `›` 6. A read's result has about
310 characters around its outline. Worked through for the fixtures as they are defined above:

- F1, first read: 5 paragraphs cut at 200 characters, a fold line, the form's first 40 fields and a fold line:
  about 3,300 characters of outline, about 3,900 as sent. The budget is 6,000.
- F1, everything: about 60,100 characters of outline. `max` 40,000 makes that 2 pages, each inside 48 KiB as
  sent (a full page is about 40,300 bytes), about 61,500 characters in all. The budget is 3 calls and 75,000.
- F1, the form by `ref`: 80 field lines, about 4,250 characters of outline, about 4,950 as sent. The budget is
  6,000, and the default `max` of 6,000 holds the outline in one page.
- F2: 1,200 cells of 12 characters are 14,400 characters. Each row's line adds 12 quotes, 5 separators of 3
  characters and a line break: 100 characters of outline a row, 113 as sent. With the table's line and the
  header that is about 20,100 characters of outline, which is why the call passes `max` 40,000 and not 20,000,
  and about 23,050 as sent. The budget is 14,400 + 7 × 1,200 + 800 = 23,600. Quoting every cell stays: it is
  what keeps a cell from forging a line.
- F3: one hit with its path is about 100 characters of outline, about 420 as sent. The budget is 800.

If the built read misses one of these by more than its fixture explains, the budget or the read changes in the
brief (stop rule); the fixture isn't made smaller to fit.

**Brief 20's groups 1 to 13** pass twice on the final head, through brief 20's tools, in both install modes.
`reviews/28-chrome-read/HARNESS-MAP.md` lists every test whose assertion the four exceptions change, old and new
side by side, and nothing else changes in the harness:

- a test that reads a typed field's value in a taken tab before its reload now gets the reader's "filled, not
  read" for an `input` or a `textarea`, where merged PR #27 doesn't already assert that;
- a test that reads or fills a field named like a credential now gets a password-kind field;
- a test that sends a form holding a field withheld for unknown history now gets the refusal. For exactly those
  cases the consequences change with it and are listed in the map: no question is asked and the receiver has no
  arrival.

In every case that stays permitted, a test never changes what it asserts about the receiver's log, a question, a
binding or an approval.

Register the new browser cases in the named inventory (`ci/verdicts.mjs`) the way brief 20's FEATURE and VIEW
cases are registered. The password cases join the `password_exclusion` group, and the cases of the refused form
join `binding`. Group 16 is a CI check only and never part of a verdict. Don't add a core group and don't change
the record's format. Say in the report which case went where.

The base's, 18d's and Mail's suites still pass, and the generated artifacts are in sync: unchanged.

## Out of scope

- The new tool list, acting by short reference, the fingerprint, `chrome_open`, `chrome_go`, `chrome_do`, the
  smaller tools, addresses on brief 20's surfaces and in questions, the harness migration and the final budgets:
  brief 28a.
- His open tabs in place, the **READ** sign, the popup list, incognito, tabs in the background: brief 28b.
- Anything in the asking path or the hold beyond the refusal in front of it and item 5's one change.
- Screenshots (owner, 2026-11-13, board #202: "Text only first"), coordinates, console or network reading, running
  script text, a search that needs a model (section 6, "Left out on purpose").
- Any real site or account. The image (`os/`). Running Claude Code with a model.

## Paths

**May change:** `control/aresos_control/chrome/adapter.py` (the internal read's entry, and the refusal in `payload`
and `steps`), new modules beside it (the view module, the credential words); `definitions.py` only as far as the
internal action needs, with every generated file unchanged; `control/aresos_control/chrome/bridge.py` (only the
reply wait and the draining of item 4); `control/chrome/extension/reader.js` (items 1 and 3) and `background.js`
(only as items 1 and 4 say); `control/chrome_tests/`, `control/chrome/ci/`;
`.github/workflows/control-chrome.yml` (not the qualification workflow); `reviews/28-chrome-read/`.

**Must not touch:** the generated files (`docs/control/TOOLS.md`, the ask rules, `user-mcp.json`), which must come
out byte-identical; `os/`, `mod/`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/TOOLS-HANDOFF.md`,
`docs/control/FEATURES.md`, `STATE.md`, `HANDOFF.md`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `briefs/`;
`control/aresos_control/mail/`, `control/mail_tests/`, `control/boundary/`, `control/checks/`,
`control/packaging/`; `reviews/20-chrome/`, `reviews/28-chrome-capability/` and every other package's `reviews/`
folder; in the Chrome code `guard.js`, `page.js`, `policy.js`,
`manifest.json`, `policy.py`, `sites.py`, `qualification.py`, `committed.py`, `uploads.py`, `qualify.py`.

## Acceptance

- The baseline file is committed, from a CI run, with brief 20's tools used as well as they allow.
- The new read exists as the internal action with the inputs and results above, and is absent without the
  switch.
- Group 14's parts of this brief pass, the password cases with the recording on, and the read rows of group 16
  hold against the baseline.
- The generated tool list, descriptions, instructions, ask rules and sizes are byte-identical to `main`'s.
- Groups 1 to 13 pass twice on the final head through brief 20's tools, with only the assertions the harness map
  lists changed.
- The four exceptions hold in brief 20's tools: the tests of "Passwords" show each.
- No secrets, real addresses, account names, provider names or real sites.

## Report (`reviews/28-chrome-read/REPORT.md`)

AGENTS.md's format (Done, Verified, Not verified, JUDGMENT-CALL, PLAN-GAP, Open questions), and in it:

- the baseline and the measured read rows side by side, per task, with run ids and timings;
- the outline of each fixture as returned (short ones in full, long ones by their first 40 lines);
- what the merged reader already did of item 1's rules and what this package added, with files and lines;
- the lines of the refusal in `payload` and `steps`, the lines of the two password additions in `reader.js`, the
  lines in `bridge.py` and in `dispatch`, and a statement that nothing inside the asking path's functions
  changed, with the diff command that shows it;
- for the asking read: whether each binding case passed on merged `main`, with the run id, or which failed. The
  brief claims nothing about that binding; the report says what a run showed;
- the harness map and the inventory mapping;
- every claim marked **run** (workflow run id and log line), **read** (file and line) or **assumed**.

**Known limits.** Keep `reviews/28-chrome-read/KNOWN-LIMITS.md`: start from section 6's "Known limits", and for
every line you add, change or find untrue give what it is, the harm and why it is acceptable or not. The lead
moves the result into section 6. A flaw with real harm (an action without its question, a password or sign-in
code read, data loss, his normal use broken) is never a limit: fix it or stop.

## JUDGMENT-CALLs

No open JUDGMENT-CALL.

**Already decided by the owner** (his words; `docs/control/PLAN.md` and the board):

- 2026-11-11: capability before more hardening. "I don't just wanna rebuild Claude in Chrome. I wanna make a
  better tool for AresOS that's more efficient with readings, navigation, free tab navigation etc."
- 2026-11-11: the bar. Safe the way a good MCP or CLI is; a flaw with real harm is fixed, and a known limit is for
  low harm. A password or a sign-in code reaching Claude is never a limit.
- 2026-11-13 (board #202): "Text only first." Pages are read as text; no screenshots in these packages.
- 2026-11-13 (board #210): "Ask first." Where the reader can't know a typed field's history, a normal read
  shows only whether the field is filled, and its value is read only after he was asked: brief 20's
  `chrome_read_typed_fields`, kept here as it is built.
- 2026-11-13 (board #213, "Show link addresses"): Claude sees link addresses with their query on the pages it
  reads. A value that looks like a sign-in stays hidden by item 2's rule: a credential-named parameter, a long
  random-looking value, what follows a sign-in word in a path, and never a user name. The security re-check asked
  for every unclassified value to be hidden; he chose otherwise, knowing that a short sign-in code in a link can
  slip through. Lists keep the short form, and so does everything the service writes to its log.

**Already decided by the lead** (2026-11-13, on the design's second reviews; a builder doesn't reopen them):

- The design is built as three packages, 28, 28a and 28b, in that order, and none reaches the laptop before all
  three are merged.
- "Ask first" covers single-line and multi-line form fields alike, because a field's present type proves nothing
  about its past. Every typed form field with unknown history shows only filled or empty. Editable areas stay
  read; what that leaves is section 6's known limit about a secret in an editable area (item 1; security
  re-check 2, finding (a)).
- The asking read's approval is bound to a prepared read; PR #27 builds that binding and these packages keep it
  (item 5; finding (c)).
- A form that holds a field withheld for unknown history isn't sent by Claude, and an approved asking read
  doesn't lift that (item 1; the re-check's new fix).
- A reference's run letters are five random consonants, with the guarantee described as it is (item 3; package
  re-check 2, N1).
- A read's deadline reaches the bridge and the extension by the time each command carries, and by nothing more
  (item 4; N2).

**Decided here, and the lead's to defend:**

- The new read is built behind an internal action first, so the list Claude is offered is switched once, in
  brief 28a, together with the way of acting.
- Brief 20's tools keep their addresses until that switch; the address function is built and tested here.
- A fold's and a table's shape, the role list and the numbers of the outline format (item 2).

Anything you meet that changes how Chrome feels for the owner goes into the report as a JUDGMENT-CALL with what you
chose, what you rejected, why, and what changing it later costs. Likely candidates: a fold that hides something
Claude nearly always needs; a wait that is too short or too long on real-looking pages; an address whose hidden
part Claude turns out to need.

## If unsure

Take the option that never returns a password and that never says something happened when the tool can't know.
Then the option that changes nothing Claude is offered. Then the option that returns fewer characters. Say what
you chose in the report.

## Stop rules

- Stop and report, rather than weaken a rule, if a read budget can only be met by leaving out something Claude
  needs to act safely, or can't be met with the calls its row names.
- Stop if the tool list, a generated file or a brief 20 result would have to change beyond the four exceptions,
  or if anything inside the asking path's functions would have to change.
- Stop if a binding case of the asking read fails on merged `main` (item 5).
- Stop if any test would need a real site or a real account.
- The full `control-chrome.yml` suite takes three to four hours a run. Develop against the browser-free tests and
  the short job. Plan about 6 full runs; tell the lead in the report before passing 9. Wait on each run with one
  blocking call; never poll turn by turn. Mark report-only pushes `[skip ci]`.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in your worktree, on branch `pkg/28-chrome-read`, from `main` after PR #27's merge. Commit in small
  steps, push this branch, open a draft PR against `main`. Never merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- On the laptop: one test suite at a time, `pkg28-` names for scripts and `/tmp` paths, and check free memory first.
- Name your model in a commit trailer.
