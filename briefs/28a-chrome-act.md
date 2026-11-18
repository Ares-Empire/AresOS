# 28a: Chrome acting: the new tool list, short references, navigation and batched steps

**Goal:** Claude gets the efficient Chrome tool. Brief 28 built the new read behind an internal action. This
package makes it what Claude is offered and builds the rest around it, with the same questions before every send.
An action names its element by the short reference a read gave, and by nothing else. One call opens a page and
returns its outline. One call runs several steps and says what changed. The tool list a session loads shrinks from
30 tools to 19. "Better" is written as budgets, and a CI test group measures them against brief 20's tools on the
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
Earlier owner decisions stand. BRIEF-CROSS-5's two owner questions are answered: board #353 chose one
send/loss question; board #355 chose "Yes/no in the session (recommended)" after board #354 asked about updates
(2026-11-18; `reviews/28-chrome-capability/REVISION-CROSS-5.md`, Owner answers).
Revision 3 assigns committed profile admission, restore connection retirement and the in-session managed ask
to **28b step 2**, replacing Revision 2's profile password dialog. They add no tool or instruction work to 28a;
its contracts and order stay here.

**Building starts only after brief 28 is merged** (and with it PR #27). Branch from `main` after that merge. Paths
and line numbers in this brief come from PR #27 at `8b7e799c`; read them again on merged `main`. PR #27 merged as
`09cedc84` (final head `d25ccbd3`); the names and facts in this brief were checked against it on 2026-11-15
(`reviews/28-chrome-capability/ALIGNMENT.md`).

**Builder:** Codex gpt-6.1-sol, in the bounded steps of item 8, one builder at a time; the lead is `linux-tools`.
The work changes a dense, security-reviewed code base. **Review** (`docs/REVIEW.md`, "Tools
for Claude"): two fresh reviewers at once, a package review and a security review, Codex while it is available,
otherwise Claude. The six narrow exceptions in "What must not change" include distinct field descriptions
(item 3b) and structured loss refusals (item 5b), added after BRIEF-CROSS-5. Its security review is high-stakes:
Fable 5.2, or Codex's frontier model while it is available. The
package review runs on Opus or Codex's workhorse.

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
- `docs/control/TOOLS-HANDOFF.md`, "Chrome merged": what PR #27's merge left for these packages.
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

### 0. The package 28 contract inherited here

Read `reviews/28-chrome-read/PROGRESS.md`, steps 13b to 13d on the merged package 28 head. The revision was
checked against `origin/pkg/28-chrome` at `e07a88eb`: its progress file has 13b/13c, while commits `42163e2c`
and `978536d7` already implement the follow-up comparisons and option resolution. Recheck the final merge.

- Page strings crossing the native-host boundary are `wellFormed()`: lone surrogates become U+FFFD, valid pairs
  stay unchanged. Every comparison of service-held facts with fresh extension facts repairs the **fresh side**
  the same way, including both approved-input comparisons, dialogs and asking reads. New fingerprints hash
  that representation too, in `outline`, `facts` and `observe`. This is neither Unicode normalization nor
  address redaction: full addresses, complete field facts and every option still bind. Never skip a comparison
  to admit malformed text, and never repair the page itself. Raw-to-raw checks wholly inside the reader stay raw.
- Selecting by a repaired option value must resolve to exactly one enabled native option; zero or several
  matches refuse. Keep package 28's resolution back to the native value at dispatch. Repair can make two raw
  values equal; it is not permission to choose the first.
- A current-session end of control, or confirmed close/release, drops that tab's references without resetting
  the counter. Keep this on all renamed tools, including Stop, detach and controlled-child release. An old
  session event or a refused close does not discard current references. A new take issues new references.
- Item 3b, built in **28a**, closes 13b's duplicate-label PLAN-GAP in the frozen asking path; 28b inherits it.
- Brief 28 items 2 and 7 are normative for the complete random-token rule (including `_` and `-`) and the
  5,000-reference paging limit. Item 8's first step carries their tests forward, including the mutations below.

Tests and reviewer mutations for these inherited rules are in "CROSS-5 regression contracts" below.

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
  before it serialises them. These are item 3's changes inside `execute`; item 5b separately preserves loss
  details as untrusted data through errors/status. `Engine.stage`'s storage behavior isn't changed.
- **`steps`** writes its page-step warning (`chrome_page_step`) to the log with addresses in the short form.

For this address projection the payload isn't touched, and no comparison reads a projected text. Show these
lines in the report.

Claude uses an address it can't see whole by reference: a link's `ref`, his tab's number, a library entry's `ref`
(items 4 and 6). So a `…` never blocks a navigation.

### 3a. A list's options in a description (service)

**Why.** On `main` a form that holds a long list can't be sent at all (found by package 28's baseline, run
43698395453; `reviews/20-chrome/KNOWN-LIMITS.md`, last entry). `prepare` puts the whole binding into the approval's
description, the binding holds every option of every list in the form (`field` in `reader.js`), and the base refuses
an approval above 16,384 bytes (`ASK_LIMIT`, `approval_input` in `common.py`). The 200 options of F4's Country list
alone are 14,380 bytes. So the click on Save, and Enter in a field, end in `asking_input_too_large`. Nothing is sent,
but Claude can't send F4, or any form with a country list.

**The rule.** In a description, a field that has options shows `chosen` and `option_count` in place of `options`:

```
{"element": "e20", "name": "country", "label": "Country", "type": "select-one", "value": "c7", …,
 "chosen": [{"label": "Country 7", "value": "c7", "selected": true, "disabled": false}], "option_count": 200}
```

- `chosen` holds the selected options, each exactly as the binding holds it. A multiple-choice list shows every
  chosen option, and a list with none chosen shows `[]`. `option_count` is the number of options in the binding.
- It holds wherever a description carries a field's facts (read on `d1a87959`): the form's fields, the target when
  it is a list, a page dialog's fields, the editable fields of a send outside a form, and an affected item's fields.
- Every list is written this way, whatever its length, so a description has one form.
- **A step that chooses from a list shows what it will choose** (review 5, B2; the lead, 2026-11-16). `chosen` is
  what is selected now, and the payload carries the step as `input: {verb: 'select', value: …}`. So for a `select`
  input the target also shows `choosing`: every option of the binding whose value equals the input's `value`,
  each exactly as the binding holds it. Normally that is one, because the extension refuses the step unless
  exactly one enabled option has that value:

  ```
  "chosen": [{"label": "Country 7", "value": "c7", "selected": true, "disabled": false}], "option_count": 200,
  "choosing": [{"label": "Country 12", "value": "c12", "selected": false, "disabled": false}]
  ```

  The step replaces the choice, it doesn't add to it: the extension sets the list's value, which leaves only that
  option chosen, also on a multiple-choice list, whose other chosen options it unselects (review 6, N6). So
  `chosen` is what is chosen now, and `choosing` is all that is chosen after the step.
  Without it the approval would call the old option chosen and show the new one only as a value, often an opaque
  id. Such steps do ask (`classify` in `policy.py`): every `select` in conservative mode, on a Chrome major that
  isn't qualified yet, and elsewhere any `select` in a form whose action or label carries a send, pay or delete
  word. `free`'s committed description shows `choosing` the same way.
- One function does it, on the copy that item 3 makes for the addresses. `prepare` takes the description and the
  question from that copy, and `free` takes the description it commits from it.

**Nothing else is summarised or cut.** Rule 4.1 of `CONTROL.md` stands: what an action sends is shown whole, or it
isn't sent. Field names, labels and values (hidden fields included), the chosen options and the text next to Send
stay as on `main`. The options he didn't choose can go from the description because the form doesn't send them;
the one a `select` step is about to choose is shown as `choosing`.

**What is bound and compared doesn't change.** The operation's payload keeps the whole `binding` with every option.
`command` sends it to the extension as on `main`, and `input` compares the whole binding twice before an approved
input (`background.js`: before the frames are armed, and again at the input boundary). A page that adds, removes,
renames or re-values an option while the approval waits is refused (`stale_approval`), also when that option is one
the description doesn't list. `binding`, `question`, `revalidate`, `command`, `execute` and the extension aren't
changed **for this list projection**: `question` never read the options. Item 3b separately adds description
identity/order facts and item 0 requires the inherited repaired comparisons. No digest is added: the payload
holds the list itself.

**Sizes.** Bytes of canonical JSON after escaping, as `approval_input` counts them. Worked through on main's code
(`d1a87959`) for F4's page, not yet measured in a run; measure them and give them in the report.

- F4 on `main`: about 21,700 bytes, refused. With the rule: about 7,300, with a question of about 460 characters.
- A single-choice list costs about 265 bytes with its chosen option, whatever its length (F4's Country: 14,558
  before). So lists can't fill an approval any more, unless hundreds of their options are chosen and sent. A
  `select` step's `choosing` adds about 90 bytes, once, on the target.
- A plain field costs about 145 bytes plus its name, its label and its value. A character costs 1 byte, a quote
  or a backslash 2, a character outside ASCII 6. A label and a textarea's text each count three times: in the
  field, and in the text next to Send, which the description holds and the question quotes.
- What fits, then: about 90 fields with short labels and empty values, about 60 with 40 characters of label and
  value each, about 45 with 80; a text next to Send of about 3,800 characters (the question's own bound of 4,096),
  or about 900 in a script outside ASCII.
- **The worst case is still a refusal, as on `main`.** A form that sends more than fits (more fields, a longer
  text, a long hidden value such as a framework's page state, a multiple-choice list with hundreds of options
  chosen) is refused by the base's check, which doesn't change, and neither do `ASK_LIMIT` and `QUESTION_LIMIT`.
  Nothing is reserved and nothing is sent. This stays a known limit (section 6, "A large form isn't sent by
  Claude").

**A form that still doesn't fit, said clearly.** `chrome_do` reports that step as `refused` with the code
`asking_input_too_large`. Its message is the refusal's own sentence and then one of Chrome's two fixed pieces of
advice (review 5, N5: shortening doesn't help when a hidden value is what is too large):

- when the same approval would fit with the values of its typed fields and the text next to Send left empty:
  "Shorten the text you filled, or ask the owner to send it himself; nothing is cut to make it fit.";
- otherwise the size comes from what Claude can't shorten (a long hidden value, the number of fields, hundreds of
  chosen options): "This form sends more than a question can show, whatever you fill in; ask the owner to send it
  himself; nothing is cut to make it fit."

The service measures that on a copy, with the base's own count, only to choose the sentence. Nothing is prepared
from the copy.

**When the page itself starts such a submission** (a held step), `steps` prepares it through the same `prepare`.
On `main` that refusal leaves `steps` as an error, the step is never acknowledged, and every later read of the tab
fails the same way (read on `d1a87959`: `read` calls `steps` and doesn't catch it; check it). Here `steps` treats
this one refusal as it treats a step whose document changed: the submission stays stopped and is never resumed, the
step is recorded as done and not resumable, it is acknowledged to the extension, and it comes back as a stopped
step whose reason is the same sentence and advice. The call that met it returns its normal result, with the step
in `untrusted_content.stopped`.

The entry in `reviews/20-chrome/KNOWN-LIMITS.md` is the lead's to close at the merge. Say in the report what a run
showed for F4.

### 3b. Every field in an asking question is distinguishable

**Decision and why (package 28 step 13b).** Bound element ids prevent a swap, but two occurrences of the same
label don't tell him which field he is allowing. 28a changes this frozen asking path; 28b reuses it in place.

Give every field mentioned in a question or its content fields a human description that distinguishes it within
that question, including unnamed fields and labels made equal by item 0's repair or display shortening. Use the
label plus its position among equally labelled fields in document order (for example, "Note, 1 of 2"), and a
frame description/position when necessary. A nearby heading may help but never substitutes for a unique ordinal
when headings collide. No raw element id alone counts as a human description. Never read a withheld value to
make the description. Keep full names and sent values where the existing question requires them; don't cut them
to fund this addition. If the complete question exceeds the existing limits, refuse.

The reader supplies the non-value identity/order facts. The service derives descriptions once from that bound
list for `prepare`/`question` and the committed description in `free`, including the asking-read branch and all
field locations of item 3a. Keep element, frame, document and reader identities; bind the description's source
facts and ordering, compare them again before any approved value read/input, and ask afresh when they change.
Both service and extension use item 0's repaired representation. This permits a narrow addition to `binding`,
the typed-field preparation and their revalidation; it never replaces identity binding with label matching.
Reload questions added in 28b use this same description rule, with no values.

**Test:** two fields labelled "Note" have distinct descriptions in the actual asking sentence and content
fields, not merely distinct ids. Approving an unchanged list reads exactly those two fields once; swapping,
replacing or reordering them while it waits reads nothing and asks again. Repeat across two identically titled
frames, for unnamed fields, and for two labels that repair to the same text. Check a send's field descriptions
as well. **Mutation:** render labels alone; the question-description test must fail even though the identity-swap
test still passes. Separately omit identity/order revalidation; the swap/reorder case must fail.

### 4. `chrome_open` and `chrome_go` (effect change)

**`chrome_open`** input: exactly one of `url`; `tab` (open the address that tab shows; with `seen` when the tab is
his, item 6); `ref` (open the address behind a link's or a library entry's reference; `tab` may accompany a link's
reference and must then be its tab). Also `until`, `timeout_ms` (0 to 15,000, default 8,000) and `max` (default
4,000).

**`chrome_go`** input: `tab`, and exactly one of `url` or `to` (`back`, `forward`, `reload`); `until`, `timeout_ms`,
`max` as above; `discard_unsaved` (boolean, as on `main`).

Result of both:

```
{"tab": 431, "loaded": true, "until_met": true, "characters": 2210, "total": 2210, "cursor": null,
 "untrusted_content": {"url": "…", "title": "…", "scroll": "0/1800", "outline": "…", "dialog": null},
 "version_notice": null}
```

- Both use brief 20's `open` and `navigate` commands and rules unchanged (web addresses only, the fixed list, the
  refusal of form-loaded history entries, the guarded reload, and brief 20's check for unsaved work). Then the
  service waits until the page is loaded as defined below (a new document, or a new address in the same document;
  ready; quiet), or until `until` is met, or until the timeout. `loaded` and `until_met` say which.
- `chrome_open` with `tab` or `ref`: the service takes the full address from its own record (the list Claude named
  with `seen`, the tab's present address for a Claude tab, or the reference table). Claude only ever saw the
  public form. The rules of "Where Claude may go" apply to it.
- **A link reference keeps its recognised meaning (CROSS-5 finding 3).** Resolve and fingerprint-check it, then
  classify a click on its fresh target facts with the same policy, adapter, read-only and qualification rules as
  `chrome_do`. If that activation would ask, `chrome_open(ref=…)` refuses with a fixed `refused` message directing
  Claude to `chrome_do`'s asking click path. It creates no tab, follows no address and sends no request. Failed
  or missing classification facts refuse too. This read/check must not call an acting `payload` branch that
  takes or reloads the source tab. 28b applies it to references read in his tabs without a take as well.
  A free reference opens the full bound address only while those fresh facts still match; a changed target is
  stale. A library reference has no selected page control to classify. Explicit `url` and `tab` inputs retain
  the separately accepted free-URL policy: this fix does not classify arbitrary URL strings or recover a label
  from history. A reference must never fall back to that route after its classification refuses.
  **Test:** visible Delete and Unsubscribe links with GET receiver endpoints, including a hidden token in the
  destination: opening either reference refuses; clicking it prepares; neither sends a request before approval;
  the approved click sends once. Also test ordinary links, conservative mode, stale hrefs, and a supplied URL
  as the explicit policy control. **Mutation:** bypass classification in reference-open; this receiver test fails.
- The outline is the same as `chrome_read`'s, with references ready for the next call.
- **`chrome_go` keeps main's guard for unsaved work** (the lead, 2026-11-15). Every direction and an address first
  runs brief 20's check (`requireDiscard`): unsaved typing (by field label, marked as typed by the owner or by
  Claude), playing media and frames that couldn't be inspected come back as `reload_required`, and nothing is done
  until the call is repeated with `discard_unsaved: true`. The discard policy is main's `chrome_navigate`'s;
  item 5b replaces the unsafe text shape of its refusal, and `reload` still never reloads a form-loaded
  document.

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
the bound of the change report); `discard_unsaved` (boolean, for the first-input reload of a taken tab or of a
popup, as on `main`).

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
  screen. Other permitted changes are listed in "What must not change"; this reveal applies to dispatched input,
  not a held submission's native resumption.
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
| `refused` | a rule refused it: a read-only site, a password field, a form that holds a field the tool may not read, an option that doesn't exist, an address that isn't allowed, a form or a text too large to ask about whole (item 3a); `code` and `message` say which | no |
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
   outline attached; a tab with unsaved typing or playing media answers `reload_required` as on `main`, and Claude
   repeats the call with `discard_unsaved: true` (after his OK in the chat where main's rule asks for it) or calls
   `chrome_take` with `reload: true` (item 6) (the lead, 2026-11-15).

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
- **Why 20 steps and not 32:** brief 20 waits out its hold after every input (`collectSteps`, 525 ms: the 500 ms
  `holdMs` and 25 ms), and reads the page's facts before it. About a dozen input steps fit in one call.
- **A caller that goes away** changes nothing about this: the list ends at its deadline at the latest, each step
  that ran is its own committed operation (in the log and in `chrome_operation_status`), a prepared step stays
  prepared until it expires, and nothing runs later.

### 5a. Two points left by brief 20-popup-race (lead, 2026-11-15)

PR #77 (`635872e2`, `reviews/20-popup-race/REPORT.md`) left these to this brief. This package doesn't rework
admission (brief 28b does, its items 4 and 4b), so each point is a narrow change of its own: both are in the list
"What changes in `background.js`", in the paths, and among the places the security review looks at first (the
lead, 2026-11-16, after review 5, S4).

- **A popup the click opened, named when it isn't under control (its P3).** Today a click's popup is admitted by
  `onCreatedNavigationTarget` → `createdTarget`, after the dispatch or beside it. If admission fails or is
  refused, Claude learns of the popup only through `tabs` (`controlled:false`).
  - Now the step's result names it: `popup: {tab, controlled: false}`, with the popup's address in the short form
    (item 3) and the `no` mark where `chrome_tabs` would show it: no more than the tab list shows. Nothing of its
    content is included. Claude can then `chrome_take` it, unless it is marked `no`.
  - The step waits for the outcome only within its existing hold after the dispatch (item 5's "nothing is cut
    short"); no new wait. A popup whose admission hasn't decided by then is named `controlled: "pending"`.
  - A popup that was admitted is named `controlled: true`, as today's result allows.
  - Correlate by the opener (`sourceTabId` and frame) and the step's dispatch window. A popup that can't be tied to
    this step isn't named; it stays in `tabs`.
  - The outcome travels from `createdTarget` to the step that was dispatched, through `dispatch`'s result. That
    is the one change in the click path; nothing about when or whether an input is dispatched changes.
  - Admission's fail-closed rules don't change.
  - Tests: refused, failed, pending, admitted, and two popups from one click; a popup that shows a fixed-list
    page is named with `no`, and its address shows no query.
- **"Pause still live" before installing (its security NOTE 1).** Chrome delivers the pause event and the command
  reply by two paths, ordered in practice but not by contract. A stale pause delayed past two round trips would
  count a document that already ran as `document_start`. The whole harm (review 5, S3): the install from a pause
  marks the document as watched from its start (`document-start.v1`), and two rules rest on that mark. The
  password-history rule would read a field he made plain before the install. The page script's wrappers would
  arrive after a page kept a native `submit`, which then escapes the hold. For an owner tab taken during a
  cross-process navigation it also skips the guarded reload. A password read and an action without its question
  are never limits (`docs/REVIEW.md`), so this fails closed:
  - Before installing from a pause, check that the pause itself still holds. A check that shows only that the
    document is current doesn't qualify (review 6, S5): the stale pause comes from the document that is still
    current. The re-arm's `Debugger.disable` (`background.js`, the duplicate-breakpoint branch) resumed it, the
    document ran, and its delayed `Debugger.paused` carries the same breakpoint id, because the re-armed
    breakpoint keeps it. Its loader and execution context are the current ones, so comparing them passes it.
  - **A pause that can't be shown to still hold counts the document as not watched from its start** (the lead,
    2026-11-16). It is recorded as `late` and doesn't get the `document-start.v1` mark, so its typed fields show
    `(filled, not read)` and it gets the guarded reload before any input.
  - If no check that proves the pause still holds can be built, the same holds for the first document a session
    installs from a pause after its breakpoint was re-armed. PR #77's analysis says only a pause from before a
    re-arm can be stale, so the cost is one more guarded reload after the rare duplicate-breakpoint event. It
    can't loop: after that document's guarded reload, the next install isn't the first one after the re-arm, so
    it is `document_start`. Say in the report which was built, and why no stale pause gets past it. This is not a
    known limit.
  - Don't give the re-armed breakpoint a new id: Chrome's browser-side store keeps the old one (the report's
    reason).
  - Tests, in the Node doubles: a pause shown to still hold installs as `document_start`; one that isn't, and the first
    one after a re-arm where no check exists, installs as `late`, its document reports `needs_reload`, and a typed
    field in it is `(filled, not read)`. A stale pause from the current document after a re-arm installs as
    `late`, also where a check exists. After the late install's guarded reload, the next install from a pause is
    `document_start` (review 6, N4).

### 5b. Loss refusals carry page text only as untrusted content

**Decision and why (CROSS-5 finding 5).** Keep the inherited reload/unsaved-work policy, not main's interpolation
of field labels into `requireDiscard`'s exception. Escaping a label doesn't make an ordinary error untrusted.

The extension returns a structured, bounded loss report with a fixed reason code; the bridge preserves it as
data, and the service chooses a fixed code/message from its own literals. For `reload_required` use
"This action may discard work. Nothing was done; inspect the loss report." No page-derived string goes into
`message`, an operation's `reason`, a stage's prose or a notice's prose. Numeric counts and service-enumerated
reasons may accompany it. Labels, titles and addresses belong in `untrusted_content.loss`, with item 3's address
forms and brief 28's escaping. Field descriptions use item 3b; never include a field's value in a loss report.

Cover **bare errors and batched steps**, `chrome_go`, `chrome_take`, `chrome_upload`, first-input reloads and
`chrome_close`'s kept entries. A batched loss report carries its step index under `untrusted_content.loss` so it
can't be mistaken for another step's loss; each kept tab has its own untrusted loss report. The error, step and
kept-entry schemas must declare those shapes. Preserve the report through bridge, adapter, engine/public error
serialization and MCP/CLI envelopes; a missing or malformed report still refuses with the fixed message and
never falls back to an arbitrary extension exception. Add only the narrow shared error-envelope support if
needed; keep other apps' errors unchanged. 28b reuses this shape for loss refusals and
`description.untrusted_content.loss` for its questions, with quoted page descriptions in the question itself.

**Test:** a label containing instructions, quotes, braces, a newline and serialization delimiters in a bare
reload error, a refusal after an earlier batched step ran, a kept tab, and the stored operation/status result.
Assert fixed code/message, valid declared schemas, no marker in trusted prose, and the complete escaped label
only inside the untrusted loss data; the receiver and document stay unchanged. **Mutation:** restore main's
`fields.join` interpolation, or flatten the report into `Refused.message`; these envelope tests must fail.

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
  `pinned`, `sound` (Chrome's `audible` and not `muted`), `muted` (Chrome's `muted`; both flags are on brief 20's
  rows on merged `main`; the lead, 2026-11-15), `asleep`, `popup`, `no` (never readable: the fixed list, his
  never-list, not a web page) and `look` (a read-only site); the title, quoted and cut at 80 characters; the address
  in the short form (item 3), cut at 60 characters.
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
- **`chrome_close`** (change; input: `tabs`, 1 to 20; `discard_unsaved`). Closes tabs that are `claude`. In this
  package every other tab is refused, **a taken tab included** ("this is the owner's tab; release it"). Brief 20's
  `chrome_close_tab` closes any tab in the group, a taken one too: its check reports unsaved work first, but a repeat
  with `discard_unsaved: true` closes a taken tab of his. That ends here.
  The result lists `closed` and, with the reason, `kept`. **Main's guard stays** (the lead, 2026-11-15): every Claude
  tab first goes through brief 20's check, and one with unsaved typing, playing media or a frame that couldn't be
  inspected is kept, with main's `reload_required` report as its reason, until the call is repeated with
  `discard_unsaved: true`. **The flag applies only to a call that closes a single tab** (the lead, 2026-11-15, after
  review 4, N6): a call that names several tabs with `discard_unsaved: true` is refused before anything closes
  (`invalid_input`, "close tabs with unsaved work one at a time"), so one OK never covers a tab whose report he
  didn't see.
- **`chrome_take`** (change; input: `tab`, `seen`, `reload`) and **`chrome_release`** (change; input: `tab`). In
  this package they are brief 20's `take_tab` and `release_tab`, with one difference:
  the explicit reload has one home. `chrome_take` without `reload` takes the tab and keeps its page, and its result
  says whether a reload is still due and what it would lose. `chrome_take` with `reload: true` also does that
  reload now (brief 20's `prepare_control` with its explicit repeat, `discard_unsaved: true` on merged `main`) and
  returns the outline. No other tool has a `reload` input; `discard_unsaved` stays main's flag on `chrome_go`,
  `chrome_close` and `chrome_do`. `reload: true` discards what the flag discards, so `chrome_take`'s description says
  that it follows the same rule: his OK in the chat first when the report lists his typing, playing media or frames
  that couldn't be inspected.
  - **`chrome_go` in a taken tab that hasn't had its reload.** On `main`, `navigate` there runs brief 20's check
    (`requireDiscard`) and then navigates, without the guarded reload. Here it first goes through `prepare_control`,
    as a first input does: `reload_required` when brief 20's check finds typing, an editor or playing media,
    otherwise the guarded reload, and then the navigation.
  - **Brief 20's discard policy before that reload is unchanged; item 5b changes its report.** On merged `main`
    it is `requireDiscard` in
    `background.js` with `reloadState` in `reader.js`: in a document the reader didn't watch from its start every
    text field, textarea and hidden input counts; in a watched one a field counts when it differs from its default or
    got typing since the load and still holds text; an editor counts once it got input (always, where that isn't
    known); playing media counts (an element, or Chrome's `audible`), and so does a frame that doesn't answer. It
    still doesn't see work kept in a canvas, a wizard's finished steps or a form on its way to the server, and it
    doesn't know whether he used the page. Brief 28b replaces it (its item 4a). Say so in `KNOWN-LIMITS.md`; briefs
    28 and 28a must not reach his laptop without 28b.
- **`chrome_library`** (read; input: `kind`, one of `downloads`, `bookmarks`, `history`; `text`; `cursor`; `limit`).
  The three brief 20 tools merged, with their snapshot paging. Two differences: every address is in the short form
  (item 3), and every entry carries a reference (from brief 28's table) that `chrome_open` takes as `ref`. The
  service keeps the full address under that reference for as long as the snapshot lives.
- **`chrome_read_typed_fields`** (an asking read, under the managed ask rules). The owner, 2026-11-13 (board
  #210): "Ask first." Brief 20 built this tool, and brief 28 says what it is, how its approval is bound to a
  prepared read, and which fields it may read (brief 28, item 5). **This package keeps its read policy and adds
  item 3b's distinct descriptions.** Keep its name unless it collides with one here.

  What this package does with it, and nothing more:
  - **main's two tools stay** (the lead, 2026-11-15): `chrome_prepare_read_typed_fields` takes the tab and returns
    the approval, whose question lists the fields, and `chrome_read_typed_fields` takes that approval unchanged.
    They are the eighteenth and nineteenth tools of the new list, with their names, inputs and read policy
    unchanged; item 3b changes their field descriptions.
    The managed ask rule stays on `mcp__chrome__read_typed_fields` alone, and it is part of the generated rules that
    must not change by a byte;
  - in its result each field is named by its label and by its short reference in place of brief 20's reference
    object, and each value sits in `untrusted_content`, quoted by brief 28's escaping rule;
  - an address in its question is in the public form (item 3);
  - a normal read tells Claude that it exists for a tab (`typed_fields`, brief 28), and the instructions say when
    to use it: only when his request needs what such a field holds;
  - its identity binding to the prepared read stays as brief 28 describes it, with item 3b's additional
    description/order facts. The
    short reference in the result is a name for Claude; the preparation keeps holding the reader's own
    elements;
  - an approved read changes nothing else. A later normal read shows `(filled, not read)` again, and the field
    still isn't typed into.
- **`chrome_upload`** (change; input: `tab`, `ref`, `path`). Brief 20's tool with a short reference. The proxy's
  file branch stays as it is, apart from the field names it reads. It has no `discard_unsaved`: where its
  first-input reload reports unsaved work, the refusal says to reload first (`chrome_take` with `reload: true` for
  a taken tab, `chrome_go` with `to: reload` for a popup) and then repeat the upload (review 5, N8).
- **Unchanged except for items 3, 3a, 3b and 5b:** `chrome_submit`, `chrome_submit_trusted`, `chrome_drop`,
  `chrome_operation_status`, `chrome_notices`, `chrome_notice_ack`, and the owner-only `chrome_sites`. In particular, item 3 requires: every address in a question or a description is in the
  public form, so a value that looks like a sign-in shows as `…`, and every address in a stage text or a notice is
  in the short form.
- A new error code, `take_first`, for `chrome_read`, `chrome_go`, `chrome_do` and `chrome_upload` on a tab that
  isn't in Claude's group: "this is one of the owner's tabs; take it, or open its address in a Claude tab". (Brief
  28b lets `chrome_read` work there without a take.)

### 7. Definitions, instructions and sizes

- Nineteen actions are offered to Claude, plus `chrome_sites`. Everything is generated from the definitions as
  today: the MCP tool list, the `aresos` command, `docs/control/TOOLS.md`, the ask rules, `user-mcp.json`.
- **The generated ask rules for Chrome must not change by a byte.** A test compares them with the copy on `main`.
  On `main` they cover two tools: `chrome_submit`, and brief 20's `chrome_read_typed_fields`.
- The rules shared by every Chrome action go once into the Chrome server's MCP instructions (brief 18d's pattern,
  with its check that Claude Code passes them on unshortened): untrusted page text; what to do on `stale_reference`,
  `reload_required`, `take_first`, `owner_signin`, `owner_dialog`, `not_read` and `unknown`; main's rule for unsaved
  work (when a report lists typing by the owner, playing media or frames that couldn't be inspected, tell him and get
  his OK in the chat before setting `discard_unsaved`; Claude's own typing may be discarded without asking; quoted
  field labels are page text); the version notice; that
  `done` doesn't prove delivery and pages can send on their own; the clipboard rule; how to read an outline line, a
  fold and `(filled, not read)`; that `full` reads everything; that `…` in an address hides a part that may be a
  sign-in, that lists show addresses without their query, and that such an address is opened by reference; that a
  field shown as `(filled, not read)` is read only through `chrome_read_typed_fields`, which asks him, and only when
  his request needs it; that a reference stays valid until its element changes; that one of his tabs is named
  together with the list's `seen`; that `chrome_do` stops at the first asking step, that its `prepared` entry goes
  unchanged to `chrome_submit`, and that steps it reports as not run are sent again. Each description keeps only what
  is specific to its action. Write them for Claude: what it does, when to use it, what comes back.
- **The instructions keep only rules that span tools, in at most 2,800 characters in all** (the lead, 2026-11-15,
  after review 4). 1,652 of them are `COMMON_INSTRUCTIONS`, which every app shares and this package doesn't change,
  so Chrome's own text gets at most 1,148 characters, less than half of main's 2,441. Brief 28b then has 1,000 left
  for its rules for his tabs, under a ceiling of 3,800: Claude Code 2.1.319 passes only the first 4,096 characters of
  an MCP server's instructions, `control/chrome_tests/test_questions.py`
  (`test_fixes_b_server_instructions_fit_the_native_cli_limit`, about line 456) fails any app above that, and 3,800
  leaves a margin. On merged `main` the Chrome server's instructions are 4,093 characters at this revision
  (4,081 after PR #77; 4,052
  before it). **A rule in the list above that belongs to one tool goes into that tool's description, not the
  instructions** (for example
  `chrome_do`'s rules for asking steps and steps not run, or what `reload: true` does on `chrome_take`); this package
  does the move. Before adding any instruction text, move single-tool rules into descriptions and compact the
  shared Chrome rules; retain all safety meaning. This revision supplies no new instruction text. Measure both
  early: the instructions against 2,800, and the whole tool list against the sizes
  below. Add a test that pins the Chrome instructions at most 2,800 characters, beside the existing 4,096 check for
  every app; brief 28b moves that pin to 3,800. If the rules still can't fit, stop and tell the lead (PLAN-GAP).
- **Sizes** (measured as brief 18d measured Mail's), for nineteen tools: **not above the baseline** (the lead,
  2026-11-15, after review 4: making the list smaller is the point). The baseline is main's catalogue measured with
  `tools_for('chrome')` and `instructions_for('chrome')` at this package's start: all descriptions plus the
  instructions (about 9,178 characters on main after PR #77: 5,085 and 4,093), and all names plus input schemas as
  compact JSON (about 11,080). Record the exact numbers in the baseline file and in the report. The new list must
  stay within both, with everything this package adds counted in: `chrome_prepare_read_typed_fields`, and
  `discard_unsaved` on `chrome_go`, `chrome_close` and `chrome_do` with main's rule for unsaved work (review 4, S8).
  A test pins the final exact totals; a change that grows them fails until the pin is changed on purpose. Brief 28b
  starts from those totals.
- Put the final descriptions and instructions, exactly as generated, into
  `reviews/28a-chrome-act/TOOL-DESCRIPTIONS.md`.
- **The never-list gate's sweep** (review 5, S5; the lead, 2026-11-16). Brief 18c-b's test
  `control/chrome_tests/test_excluded_sites_placeholder.py` calls every Chrome tool with the never-list's
  placeholder in, and fails on a tool that is neither refused nor named. The gate sits in the service before any
  call to the bridge, and the new tools must stay behind it.
  - **The rule:** every PR that adds a Chrome tool adds it to that test's swept list (`SWEPT`) in the same PR,
    with arguments valid for its input and the gate's refusal expected: `chrome_settings_unavailable`, before any
    call to the browser. Never to the named exceptions (`ANSWER_ANYWAY`), which stay brief 18c-b's.
  - Here that is every tool of the new list that isn't already one of those exceptions, and the `chrome_old_`
    names for as long as they exist. The entries of the tools step 3 removes go with them.
  - Whichever of this package and brief 18c-b's (PR #76) merges second does it when it takes `main`. If the test
    isn't on `main` when you build, add the same sweep to this package's own tests and list the entries in the
    report, so that PR #76 adds them. That copy goes once PR #76's test with these entries is on `main`, so the
    sweep lives in one place (review 6, N8).

### 8. The order of the change

Restructure in steps that keep everything working. Each numbered stage may be several small commits; record
commands, evidence and the next step in `PROGRESS.md` for a fresh gpt-6.1-sol builder.

0. **Foundation, three bounded steps:** 0a records the exact merged-package-28 baseline, checks its plain
   tests, Unicode comparisons, reference cleanup and instruction size, then makes room under item 7 with the old
   catalogue still working. 0b builds item 5b's structured errors, schema/transport tests and mutations. 0c builds
   item 3b's distinct descriptions, identity/order tests and mutations. These are explicit frozen-path exceptions.
1. **New implementation, then catalogue switch:** build behind private helpers, with the old public catalogue
   working until 1d; no temporary extra public tool names.
   - **1a:** reader fingerprints/reveal and service reference resolution, with the new binding/Unicode cases.
   - **1b:** address/list projections and the navigation/smaller-tool implementations (items 3, 3a, 4, 6),
     including reference-open classification, with targeted tests through private entry points.
   - **1c:** batched execution, deadlines, change reports and item 5a, tested with fake bridges and Node doubles.
   - **1d:** wire the new definitions and switch the catalogue, regenerate and pin the complete sizes. Four names
     overlap with different inputs (`chrome_tabs`, `chrome_read`, `chrome_open`, `chrome_upload`), so only now
     expose the new catalogue. Brief 28's internal read becomes `chrome_read`. Brief 20's tools remain callable
     as `chrome_old_…` only with brief 28's CI-only switch (never enabled in the image). Run groups 14–16 and
     the old groups through their old helpers, and the side-by-side latency run (group 16). The public catalogue
     and generated files must agree at every commit; private helpers need not be offered to Claude to be tested.
2. Move the CI harness to the new tools **in its helper functions only**. Before you start, list in
   `reviews/28a-chrome-act/HARNESS-MAP.md` every helper you change, and every test that builds a `reference`,
   an `expected` or a `view` by hand (the staleness and mismatch cases), with its new form. A test may change how
   it reaches the tool. It never changes what it asserts about the receiver's log, the question, the binding or the
   outcome. Item 3b's deliberate question-description change and item 5b's error envelope are mapped
   explicitly: old safety/receiver assertions stay, with new distinct-description/untrusted-envelope assertions.
   A test of the old "any change makes every reference stale" rule becomes a test of item 2's rule, named
   in the map. The assertions that brief 28's field rules changed are in brief 28's map already; don't change
   them again.
3. Remove brief 20's replaced tools (`chrome_find`, `chrome_read_form`, `chrome_wait`, `chrome_click`,
   `chrome_fill`, `chrome_fill_form`, `chrome_select`, `chrome_check`, `chrome_press`, `chrome_scroll`,
   `chrome_dialog`, `chrome_navigate`, `chrome_take_tab`, `chrome_release_tab`, `chrome_close_tab`,
   `chrome_downloads`, `chrome_bookmarks`, `chrome_history`; `chrome_prepare_read_typed_fields` and
   `chrome_read_typed_fields` stay, item 6), the test-only switch with its `chrome_old_` names,
   the reader's `read` rows that nothing uses any more, and the old paging of `chrome_tabs`. Every refusal,
   description and instruction that names a removed tool then names its replacement (review 4, S7). Main's
   `WITHHELD_FORM` (`adapter.py`, and its copy in `background.js`) says "reload the tab first with chrome_navigate
   direction=reload": it names `chrome_go` with `to: reload`, and the tests that pin the old text
   (`test_questions.py`, about lines 471 and 476, and line 446 for the instructions) change with it. A test scans
   the descriptions, the instructions and the refusal texts in `adapter.py` and `background.js` and fails on any
   removed tool's name. Regenerate. Pin the sizes.
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
  credential-like fields and its new question when a field was added, replaced or relabelled. **Six narrow
  exceptions, each named where it is specified, and nothing beyond them:**
  1. `prepare` and `question` write addresses in the public form, and `execute` writes its two stage texts with
     addresses in the short form, while the payload and every comparison keep the full address (item 3);
  2. `input` brings its target on screen inside the armed hold before brief 20's own hit test (item 5);
  3. `input` checks its command's time once, right before the dispatch, and dispatches nothing when it is up
     (item 5, "Time");
  4. `prepare` writes a list into the description as its chosen options and their number, and for a `select`
     step the option it will choose, while the payload and every comparison keep every option (item 3a).
  5. Item 3b adds distinguishable field descriptions and their identity/order facts to the existing preparation
     and comparisons, including the asking read; it reads no extra value and never drops an existing binding.
  6. Item 5b replaces page-bearing reload error strings with structured loss data and fixed service prose,
     including the bridge and public error envelope. It changes no discard policy.
  Item 0's repaired-fact comparisons and reference cleanup are inherited requirements throughout. Item 4's
  reference-open classification refuses before navigation; it adds no new asking execution path.
  What asks never becomes less, and every existing bound fact stays compared.
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
  too. **These places are newer than that review,** and this package's security review looks at them first:
  - *The time check in `input`* (it came with package re-check 2, N2). It can only stop a dispatch, never start
    or change one.
  - *A list's options in a description* (item 3a; it came with package 28's baseline, 2026-11-15). Only the
    description changes, as for the addresses. The payload and both comparisons in `input` keep every option, so
    an option can't change after his approval, listed or not. He no longer sees the options he didn't choose;
    the form doesn't send them, and what it does send is shown whole or the form is refused. The one option that
    isn't chosen yet and matters, the one a `select` step will choose, is shown as `choosing` (review 5, B2).
    That reduced visibility is a known limit (section 6). With it, `steps` keeps a held submission that is too
    large to ask about stopped for good and acknowledges it; it never resumes one.
  - *The popup named in a step's result* (item 5a; review 5, S4). It carries the popup's tab number, its
    admission outcome, and its address in the short form with the `no` mark: no more than `chrome_tabs` shows of
    that tab, and nothing of its content. It changes nothing about when an input is dispatched or whether a
    popup is admitted.
  - *The pause check before an install* (item 5a; review 5, S3). It can only make a document count as not
    watched from its start, which reads less and reloads once more. It never makes one count as watched.
  - *Distinct field descriptions and structured loss errors* (items 3b and 5b): human-readable uniqueness must
    survive repair and truncation; labels must stay untrusted in bare errors and stored results too.
  - *Link-reference opening* (item 4): the recognised-action check runs before any open/navigation request.
- **Brief 28's field rules and its read:** the password rule with its two additions, the outline format, the
  reference table and its run letters, the read's deadline. Nothing in them is relaxed or reshaped here.
- **The hold:** `guard.js`, `page.js`, the 500 ms window (`HOLD_MS` in `policy.py`, `holdMs` in the extension) and
  the 525 ms wait after each input in `collectSteps` (`background.js`), the default block, the owner's own Enter,
  the three kinds of dialog.
- The extension still uses no DOM snapshot, no accessibility tree and no form serialisation. No new DevTools
  method. No new permission in the manifest.
- **Where Claude may go:** the schemes, the fixed list, the owner-only excluded-sites setting, read-only sites.
- **The take rules:** a reload before the first input, unsaved typing and playing media reported first, no reload
  of a form-loaded page. Popups as brief 20 built them, apart from item 5a's two points.
- **The qualification record:** its format, `qualification.py`, `qualify.py`, the publishing workflow. The build
  hash changes because the code does; nothing else.
- **The service unit's sandbox lines** (`control/packaging/aresos-toold.service`; `test_unit.py` pins them).
- **Mail, the base and `os/`.** Change the base only where Chrome needs a helper that belongs there, and say why in
  the report.

**What changes in `background.js`, and nothing else:** a `show` command for `chrome_show`; a `tabs` reply that
holds every tab at once with the fields item 6 needs; the check of `seen` in `take` (item 6); two additions to
`input` (item 5: "on screen first", and the check of the command's time right before the dispatch); item 5a's
two points (the popup's admission outcome carried from `createdTarget` into the step's result through `dispatch`,
and the pause check before an install from a pause); item 3b's field-description facts and comparisons; item
5b's structured loss refusal; and the text of `WITHHELD_FORM` (item 8, step 3). Not the
rest of `input`, not the execution policy of `resume`, `dialog`, `prepare_control` or `release`, the rest of
admission, the debugger methods
or the session rules.

## Tests

No model, no real site, no real account. Fixture pages only. **Browser tests run only in containers on GitHub's
Linux runners, through the control-chrome workflows. Never start, read or touch the owner's Chrome or any browser
profile on the machine you run on; locally run only plain Python and Node tests that start no browser.**

Every new rule gets a test that fails without it.

**CROSS-5 regression contracts.** Run the targeted test with the named mutation, require failure, restore the
source and require the test green. Put exact commands/results in the report. Browser counterparts stay in CI.

| Rule | Test and evidence | Reviewer mutation caught by that test |
|---|---|---|
| Repaired Unicode (item 0) | Unchanged lone-surrogate title/label/option/dialog passes preparation and execution with U+FFFD; valid pairs stay exact. A changed repaired fact refuses; unchanged `outline`/`facts`/`observe` fingerprints agree. Exercise asking reads and both input boundaries. | Remove fresh-side `wellFormed` at each comparison in turn, or hash raw facts in one command: unchanged malformed-text case fails. Remove a comparison entirely: changed-fact case fails. |
| Native option resolution | One native option whose value needs repair selects exactly that option; two raw values with the same repair refuse with no input. | Choose the first repaired match: ambiguous-option case fails. |
| Control ends | Release, Stop, detach and parent/child release drop both reference indexes; old reference refuses after a take; counter increases. Old-session event and refused close retain current entries. | Remove cleanup from each event/reply path in turn: lifecycle case fails. |
| Finding 6: address parity | Inherited address tests hide a 20+ mixed-case/digit token split by `_` and `-`, retain a lowercase slug, and agree on public/short forms. | Remove the mixed-case separator rule: token case fails. |
| Finding 6: paging limit | Inherited >5,000-reference fixture refuses the old cursor after eviction, never returns a dropped ref as valid, and still permits `find`/subtree reads. | Stop binding cursors to returned reference text, or reuse an evicted ref: paging/identity case fails. |
| Distinct fields; findings 3 and 5 | The question, receiver and envelope tests in items 3b, 4 and 5b, including real public serialization. | Run each mutation named in those items; a test of ids alone is not the distinct-question test. |

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
  hold no marker and the stage texts no query at all, while the payload still holds every full address;
- a list's options in a description (item 3a), with facts shaped like F4's:
  - a prepared click on Save shows the Country list as its chosen option and `option_count` 200, without
    `options`. The same holds for a multiple-choice list with two options chosen, a list with none chosen, a list
    that is the target, one in a page dialog, one among the editable fields of a send outside a form and one among
    an item's fields. A free step's committed description has the same form;
  - **a `select` step that asks** (conservative mode; review 5, B2), on a three-option list and on F4's Country
    list, also when the step named the option by its label: the target shows `choosing` with the label and value
    of the option the step will select, `chosen` still shows the option selected now, and F4's approval stays
    within 9,000 bytes. A free `select`'s committed description shows `choosing` too;
  - every other key of the description equals the binding's, apart from item 3's addresses and item 3b's field
    descriptions. The operation's
    payload holds the binding with all 200 options, and the command the bridge gets on `chrome_submit` carries
    that binding whole;
  - F4's approval is at most 9,000 bytes, and the same facts with the options left whole are refused, which is
    what fails without the rule;
  - still refused, with no operation written: a form of 120 short fields, a hidden value of 20,000 characters, a
    multiple-choice list with 250 options all chosen, and a textarea of 5,000 characters. `chrome_do` gives each
    as a `refused` step with the code `asking_input_too_large` and the message with Chrome's advice: to shorten
    the text for the textarea, and for the other three that the owner sends it himself (review 5, N5);
  - a queued submission of such a form, met by a read and met between two steps of a list: the call returns its
    normal result with the step in `stopped`, nothing is resumed, the step is acknowledged, and the next read
    doesn't meet it again.

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
- **a form with a long list is asked once and sent** (item 3a), on F4: six fills and the click on Save in one
  `chrome_do` end `prepared`. The description shows each filled value, and the Country list as `Country 7` with
  its value and `option_count` 200. The receiver has nothing before `chrome_submit`, the form once after it, with
  the six values and `c7`, and nothing more on a repeat. Enter in a field of F4 is prepared the same way;
- **an asking `select` shows what it will choose** (item 3a): in conservative mode a `select` on F4's Country
  list ends `prepared`. Its description shows `choosing` as the new option with its label and value, and `chosen`
  as the option selected before. After `chrome_submit` the list holds the new option, once;
- **options swapped after approval are refused.** While F4's approval waits, the page changes one thing, in four
  runs: it renames an option he didn't choose; it gives one another value; it removes one and adds another, so
  the count stays 200; it changes the chosen option's value under the same label. Each time `chrome_submit` ends
  with nothing sent, the receiver has nothing, and that approval never runs. After each of the first three, a new
  preparation shows the same chosen option and count as the old one: the comparison covers what the description
  doesn't list. These cases join the `binding` group;
- **a form too large to ask about still isn't sent:** on a fixture form of 120 fields, and on one whose textarea
  holds 5,000 characters, the click on Send ends `refused` with `asking_input_too_large` and Chrome's advice (to
  shorten only for the textarea). No operation is reserved and the receiver has nothing. When the page's own
  script submits the 120-field form after a free click, the submission stays stopped, the result names it in
  `stopped`, and a `chrome_read` of that tab right after works;
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
- **one tab per flag:** `chrome_close` with `discard_unsaved: true` and two Claude tabs, one holding typing, is
  refused with the advice to close them one at a time, and both stay open; the same call with only the tab that
  holds typing closes it;
- **a taken tab stays his:** `chrome_close` on a taken tab is refused and the tab stays open; `chrome_go` in a
  taken tab that holds typing answers `reload_required` and the page isn't replaced; in a taken tab without typing
  it reloads under brief 20's guard and then navigates;
- the conservative mode (an unqualified Chrome major) asks for the same inputs through `chrome_do` as brief 20's
  tools did;
- **the marks of `chrome_tabs`:** a tab that plays sound shows `sound`; muted while it plays, it shows `muted` and
  not `sound`.

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
| F4: fill 6 fields and send the form: `chrome_open` of the form's page, `chrome_do` with six fills and the click, `chrome_submit` | 2 calls and `chrome_submit`; one question, whose approval is at most 9,000 bytes (item 3a); the receiver has it once. The baseline for this row is brief 20's refusal (below) |
| F7: three result pages, one click each, the titles collected: from an outline in hand, three `chrome_do` calls of one click, each returning the next page | 3 calls |
| Compare three open tabs: `chrome_read` with `tabs` | 1 call |
| List 25 open tabs (titles of about 30 characters): `chrome_tabs` | 1 call, at most 3,500 characters |
| F5: a free click that changes part of the page: from an outline in hand, one `chrome_do` | 1 call, at most 2,500 characters, every changed line named (`more_changes` is 0) |
| Descriptions plus instructions (19 tools) | not above main's, measured at the start (about 9,178); the final total pinned |
| The server instructions alone | at most 2,800 characters, the shared 1,652 included (and every app within 4,096) |
| Names plus input schemas (19 tools) | not above main's, measured at the start (about 11,080); the final total pinned |
| Latency (the comparison in one run, below) | the first read of F1, a free click with its report, and F4's six fills and click up to the question are each at most 1.10 times brief 20's median plus 50 ms; PR #27's latency gate (`latency-targets.json`) stays within its ceilings |

**Latency: old and new in one run.** Runners differ, so old and new tools are timed in **one run**. At step 1 of
"The order of the change", while both tool sets exist, one job runs each timed task with brief 20's tools (under
their `chrome_old_` names) and with the new ones, five times each after a warm-up, and compares the medians: the
first read of F1, as brief 28 timed it, now through `chrome_read`; a free click with its change report, against
brief 20's click and the read or find after it; and F4's six fills and the click on Save, up to the question. The
new tools pass at no more than 1.10 times the old median plus 50 ms. That run's id and numbers go into the report
and into the baseline file.

After brief 20's tools are removed, the check that stays compares each task with the new tools'
own median of that run and fails above 1.5 times. This runs inside PR #27's latency harness (brief 28,
"Latency"), as brief 28's baseline does. Fewer calls don't prove a faster tool: a step of `chrome_do` still makes
brief 20's full facts read. The timings are what shows it, and the report gives them beside the call counts.

**The form is timed up to the question.** On `main` brief 20 has no send to time: its click on Save is refused
when the approval is prepared (item 3a), and brief 28's baseline records that refusal. At step 1 both tool sets
run through the same `prepare`, which has item 3a's rule by then, so brief 20's click on Save is prepared too.
Both sides are timed over the same work, with the read or the outline and the button's reference in hand before
the clock starts, until the click on Save has come back prepared:

- brief 20's side: `chrome_old_fill_form` with the six fields, then `chrome_old_click` on Save;
- the new side: one `chrome_do` with the six fills and the click.

A side whose click comes back any other way fails the run, and the receiver has nothing from either side.
`chrome_submit` isn't part of this comparison: it is the same code on both sides, and PR #27's gate times it
("approval to done"). If the new side misses the bound, report the numbers (stop rule) and leave the span as it
is.

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
  has for its inputs. The approval for the click is about 7,300 bytes of the 16,384 an approval may have
  (item 3a), so the `chrome_do` result is about 9,000 characters. The row bounds the approval alone, at 9,000 bytes.
- **F4's baseline is a refusal.** Brief 28's baseline file records brief 20's F4 task with the outcome `refused`:
  a read, `chrome_fill_form`, a find and the click, which `main` refuses. For this row "not worse than the
  baseline" means the outcome and the calls: the new tools end `done`, in the calls the row names. Characters
  aren't compared for it, because brief 20 never returned this form's approval.

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
- Anything in the asking path or the hold beyond the six exceptions named in "What must not change". That
  includes showing less of what a form sends (a cut value, a field left out) and a larger `ASK_LIMIT`.
- **A shorter hold after each input: possible later, not now.** Most of a click or a fill is brief 20's fixed
  hold of about half a second after the input, in which a submission the page starts is stopped (measured on PR
  #27, run 43502970342: a free click 587 ms at the median, a plain read 21 ms). Ending that window when the page's
  queued tasks are done, instead of after a fixed time, would about halve a click and a fill and so a step list.
  It changes the safety window itself, so it is a package of its own with its own security review, weighed after
  his live test shows whether the speed matters. Record in the report what a list of 20 steps costs today.
- A change to brief 28's read, its field rules or its reference table, beyond the fields this brief adds to
  them.
- Screenshots (owner, 2026-11-13, board #202: "Text only first"), coordinates, hover, drag, console or network
  reading, running script text, a search that needs a model, loops or conditions in a step list, steps across
  tabs, a richer result for `chrome_submit` (section 6, "Left out on purpose").
- Any real site or account. The image (`os/`). Running Claude Code with a model.

## Paths

**May change:** `control/aresos_control/chrome/adapter.py`, `definitions.py`, the view module and new modules
beside them; `control/aresos_control/chrome/bridge.py` (the reply wait for an input, item 5, "Time", and
structured loss errors, item 5b);
`control/chrome/extension/reader.js` (the fingerprint function, the reveal, the instance id in `facts`, item 3b's non-value description facts and item 5b's structured loss fields) and
`background.js` (only as items 0, 3b, 4, 5, 5a, 5b, 6 and 8 say); `control/aresos_control/definitions.py` (only the Chrome branch
of `instructions_for`, which appends the Chrome text; `COMMON_INSTRUCTIONS` and every other app stay byte-identical);
`control/aresos_control/proxy.py` (the Chrome upload branch's field names); narrow shared error serialization/schema support only if item 5b requires it; the generated files;
`control/chrome_tests/`, `control/chrome/ci/`; `.github/workflows/control-chrome.yml` (not the qualification
workflow); `docs/control/TOOLS.md`, `docs/control/FEATURES.md` (item 9), `control/README.md`;
`reviews/28a-chrome-act/`.

**Must not touch:** `os/`, `mod/`, `docs/design/`, `docs/control/PLAN.md`, `docs/control/TOOLS-HANDOFF.md`,
`STATE.md`, `HANDOFF.md`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `briefs/`; `control/aresos_control/mail/`,
`control/mail_tests/`, `control/boundary/`, `control/checks/`, `control/packaging/`; `reviews/20-chrome/`,
`reviews/28-chrome-capability/`, `reviews/28-chrome-read/` and every other package's `reviews/` folder;
`control/chrome/ci/efficiency-baseline.json` except to add the side-by-side timings; in the Chrome code
`guard.js`, `page.js`, `policy.js`, `manifest.json`, `policy.py`, `sites.py`, `qualification.py`, `committed.py`,
`uploads.py`, `qualify.py`.

## Acceptance

- The nineteen tools exist with the inputs and results above; brief 20's replaced tools, the internal action and
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
- what changed in `adapter.py`'s `payload` and `facts`, line by line; the lines of the six exceptions (the
  projected addresses in `prepare`, `question` and `execute`; the reveal in `input`; the time check in `input`;
  the lists in a description, with F4's approval in bytes as a run measured it; the distinct field descriptions;
  the structured loss errors); and a statement that nothing
  else in the asking path changed, with the diff command that shows it;
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
- The places covered by security re-check 2 keep its guarantees, with the explicit later exceptions ("What must
  not change").
- A form that holds a field withheld for unknown history isn't sent by Claude, through `chrome_do` either, and
  an approved asking read doesn't lift that (brief 28, item 1).
- The asking read's approval is bound to a prepared read; PR #27 built it, and this package keeps that guarantee
  while adding distinguishable descriptions (items 3b and 6).
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
- A description shows a list's chosen options and their number, not the options he didn't choose, while the
  binding keeps and compares them all; what a form sends stays shown whole, and a form too large for that still
  isn't sent (item 3a; after package 28's baseline, 2026-11-15). A `select` step also shows the option it will
  choose (the lead, 2026-11-16, after review 5).

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
  beyond the six exceptions named in "What must not change". If F4's approval doesn't fit with items 3a and 3b,
  stop: don't cut a value, drop a field or raise a limit.
- Stop if a binding case of the asking read fails through the new list.
- Stop if any test would need a real site or a real account.
- A full `control-chrome.yml` run takes about 40 to 60 minutes in 28 parallel jobs (PR #27's final pair on
  `d25ccbd3`: runs 43641834739 and 43641839672). Develop against the browser-free tests and the short job. Plan
  about 10 full runs; tell the lead in the report before passing 14. Wait on each run with one
  blocking call; never poll turn by turn. Mark report-only pushes `[skip ci]`.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not.
- Work only in your worktree, on branch `pkg/28a-chrome-act`, from `main` after brief 28's merge. Commit in small
  steps, push this branch, open a draft PR against `main`. Never merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- On the laptop: one test suite at a time, `pkg28a-` names for scripts and `/tmp` paths, and check free memory
  first.
- Name your model in a commit trailer.
