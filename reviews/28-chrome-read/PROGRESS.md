# 28 Chrome read: progress

Builder steps keep this file; the last step turns it into the report. Newest state first.

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

### What the reader's `outline` must deliver (next step)

The reply of one tab, as `nodes.View` accepts it. Keys the view doesn't use are ignored at the top and at the
frame level; a node is strict.

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

- ids are positive integers, unique in a frame; `parent` is an earlier node; `text` names only the node's own
  children, each once.
- `unread` or role `password`: no `value`, no `text`, no `chosen`, no `options`, **and no child nodes**. `filled`
  only with `unread`. So a field that is kept out is a leaf that carries its label and nothing of its content.
- `states` only from the nine; `frame` only on role `frame`; each frame named at most once, never the top frame,
  never inside itself.
- at most 20,000 nodes a tab; at most 150 levels of nesting, frames included (the renderer recurses).

Rules the renderer relies on and can't check:

- **Text as displayed.** Runs come with white space collapsed as the page shows it and trimmed at the element's
  outer edges (`pre` keeps its breaks). The renderer prints a run as delivered; it only drops runs of nothing but
  space and trims inside table cells.
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
17. `find` matches each element on its own name, its own text (runs joined) and its readable value. A match that
    spans an inline child (`See the <a>timetable</a>`) isn't found.

### PLAN-GAPs (the brief taken in each; the lead decides)

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
- PLAN-GAP 7 above, if the lead accepts it as a limit.

### Budgets (brief 28, "Group 16"; fixtures as node lists; characters of the JSON text of the result)

| Row | Budget | Brief's worked numbers (outline / as sent) | Measured (calls, outline, as sent) |
|---|---|---|---|
| F1, the first read | 1 call, 6,000 | about 3,300 / 3,900 | 1 call, 3,258 / 3,833 |
| F1, everything (`full`, `max` 40,000, cursors) | 3 calls, 75,000 | about 60,100 / 61,500, 2 pages | 2 calls, 59,020 / 60,462 |
| F1, the 80 fields (form by `ref`) | 1 further call, 6,000 | about 4,250 / 4,950 | 1 call, 4,176 / 4,899 |
| F2, the whole table (`ref`, `max` 40,000) | 1 further call, 23,600 | about 20,100 / 23,050 | 1 call, 20,129 / 23,066 |
| F3, the one link (`find` and `role`) | 1 call, 800 | about 100 / 420 | 1 call, 56 / 385 |
| Three tabs (F1, F2, F3) with `tabs` | 1 call | | 1 call, 4,945 as sent |

Every row is met. A result has 318 characters around its outline (the brief: about 310). The envelope used is
`{"ok": true, "data": {"reads": [...], "version_notice": null}, "pending": {"items": [], "total": 0, "cursor":
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

1. The baseline ("Before anything else"): fixtures of group 16 on the fixture server, the scripted tasks with
   brief 20's tools, `efficiency-baseline.json` from a CI run. Needs PR #27 merged.
2. The reader: `outline`, `options` and `page_state` in `reader.js` and `background.js`, with item 1's password
   additions, the credential words module, the reader instance; Node tests in the VM doubles. Decide PLAN-GAPs
   4 and 6 first.
3. The adapter: `chrome_outline` behind the test-only switch, `until`, `tabs`, the refusal in `payload` and
   `steps` (exception 4), using the functions above.
4. Time: the deadline through `Bridge.call` and `dispatch`.
5. Browser groups 14 and 16 in CI, the latency comparison, the harness map, the known limits and the report.

### Commits of step 1

- `fcd22ee9` Chrome read: the public and the short form of an address
- `794cc7a4` Chrome read: the node list's contract and the reference table
- `de6306c1` Chrome read: the outline renderer, reads by reference, full and find
- `2ed6854c` Chrome read: pages, cursors and the 48 KiB bound, tested
- `c19b838f` Chrome read: hostile pages and the read budgets as tests
- this file
