# Brief 28: the design agent's working notes

Written 2026-11-13 by the design agent for `linux-tools`, so that a fresh agent can finish from the files alone.
The lead removes this file once the final message has been read; nothing here is specification. The specification is
`briefs/28-chrome-capability.md`, `briefs/28b-chrome-his-tabs.md` and `docs/design/CONTROL.md` section 6.

## State of the work

| Piece | State |
|---|---|
| `docs/design/CONTROL.md` section 6, rewritten (draft 32) | written, committed; one read-through for coherence still to do |
| `briefs/28-chrome-capability.md` | written, committed |
| `briefs/28b-chrome-his-tabs.md` | to write (the content is settled below) |
| Final message to `linux-tools` | to write (the content is settled below) |

Edits outside section 6, each because a cross-reference would otherwise be false: the status line (draft 32), rule
4.2 (what a Chrome reference is bound to), rule 4.4 (`chrome_library`), section 10 ("Open": the three judgment
calls).

## The split, and why

- **28 first:** reading, references, navigation, batched steps, the smaller tool list, the efficiency test group.
  It stays inside brief 20's control model (Claude's group; his tab only after a take). It needs no owner decision.
- **28b second:** his open tabs. Looking in place without a take, `chrome_take` as one step, the signs he sees, the
  password marker, incognito off, tabs in the background. It changes the extension's control model and waits on
  three judgment calls.
- The tool names and input shapes are final from 28 on. 28b changes behaviour behind `chrome_read`, `chrome_take`
  and `chrome_close`; it adds no tool.

## The tool surface (17 offered to Claude, where brief 20 has 28)

`chrome_tabs`, `chrome_read`, `chrome_open`, `chrome_go`, `chrome_do`, `chrome_upload`, `chrome_show`,
`chrome_close`, `chrome_take`, `chrome_release`, `chrome_library`, and unchanged `chrome_submit`,
`chrome_submit_trusted`, `chrome_drop`, `chrome_operation_status`, `chrome_notices`, `chrome_notice_ack`. Owner-only:
`chrome_sites`. Inputs and results are in brief 28, items 2 to 6.

Choices behind it:

- `chrome_find`, `chrome_read_form` and `chrome_wait` became inputs of `chrome_read` (`find`, `ref`, `until`).
- The nine input tools became steps of `chrome_do`.
- `chrome_upload` stays a tool of its own because the MCP proxy's file branch keys on it (rule 4.4).
- References are short names the service issues (`e12`), with what Claude last saw kept in the service. This
  replaces brief 20's six-field reference plus `expected`, and the binding to the whole view.
- No screenshot tool, no script, no console or network reading, no model inside `find`, no "current tab".
- `chrome_submit` keeps brief 20's result: changing it would change the asking path.
- A `request` field on calls that touch his tabs (28b): the tool can't check it; it is logged and shown to him.

## The three JUDGMENT-CALLs (for the owner, before 28b), word for word

**JUDGMENT-CALL 1: Claude looking at your open tabs.**
Claude may look at any of your open tabs without asking first, when your request needs that tab ("check my
lectures" and the uni tab is open). Looking doesn't touch the tab: nothing reloads or moves. You see **READ** on
that tab's AresOS button, and the button's list shows which tabs Claude looked at and for which request. Incognito
windows are never seen. Sites on your never-list are never read.
- (a) As described. *Recommended: it is what you asked for, and it leaves your tabs as they are.*
- (b) The same, plus an "ask me first" list of sites (for example your messenger or your bank), where Claude asks
  you in the chat before it looks.
- (c) Claude asks in the chat before it looks at any tab of yours for the first time in a session.

**JUDGMENT-CALL 2: a tab of yours with unsaved typing or playing media.**
To click or type in one of your tabs, Claude takes it, and the tab reloads once. The reload is what lets the tool
catch a page that submits by itself. If you have typed something there, or music is playing, a reload loses it.
- (a) Claude doesn't take such a tab. It tells you what would be lost and reloads only when you say so, or it works
  on a copy of the page in a tab of its own. *Recommended for the first version: it is built and tested, and your
  live test will show how often it gets in the way.*
- (b) Claude works in such a tab without reloading it. Sends, deletes and payments still ask. A page that submits
  by itself right after Claude types may not be caught in that tab. This needs one more build (28c).

**JUDGMENT-CALL 3: Claude closing your tabs.**
- (a) Claude may close a tab of yours when you ask it to ("close the shopping tabs"). It never closes one with
  unsaved typing or playing media, and it tells you which ones it closed. Chrome's "reopen closed tab" brings one
  back. *Recommended.*
- (b) Claude only ever closes tabs it opened itself.

## What was checked in the #27 code (read-only copy at `8b7e799c`), and what is assumed

**Read in the code:**

- `chrome-tools.json`: 28 tools; descriptions 92,366 characters before the slim generator (each repeats a shared
  suffix); names plus input schemas 10,587 characters.
- `adapter.py` `read`: one JSON line per row with a six-field `reference`, `expected` (all facts with the box) and
  `text`; paged at 16,000 characters. `reader.js` `snapshot`: a row's `text` is its whole subtree's text, so
  containers repeat their content.
- `adapter.py` `facts` and `payload`: a reference is refused when the whole view's identity differs, and `expected`
  must equal the element's present facts exactly. So a read is needed between any two actions; `fill_form` works
  around it internally.
- `background.js` `dispatch`: `navigate` returns right after `Page.navigate`, without waiting for the load; `open`
  creates the tab with Chrome's default (`active: true`), so a new Claude tab comes to the front; before every
  click, fill, key and scroll the tab is selected (`chrome.tabs.update(tab, {active: true})`).
- `collection`: `chrome_tabs` returns 5 tabs per call (the base's page limit is 10), fields `tab, window, index,
  active, focused, title, url, controlled, cleanup_pending`; the full address is listed.
- `facts` and `requireTab`: every read needs the tab to be controlled (taken). A take attaches the debugger and
  moves the tab into the Claude group; `restoreTab` puts it back to its window, index and group. The record of the
  original place has no `pinned` field.
- `prepare_control`, `reloadChecked`, `reloadState`: the first input reloads once; changed fields, any rich-text
  editor or playing media give `reload_required`; a document not loaded by GET is refused.
- The hold is 500 ms (`policy.js` `holdMs`). The fixed hosts are three Anthropic hosts; **Aresus isn't among them**,
  and the owner-only excluded-sites setting ships empty.
- `policy.js` `cdpMethods` includes `Runtime.evaluate` and `Runtime.callFunctionOn`; there is no
  `DOM.setFileInputFiles` (a file goes in through the content script).
- The manifest has no `incognito` key and no `cookies` permission.
- `bridge.py` `accept`: a second live native host is refused.
- `changed_compose`: one re-ask with the text before and after, then "ask the owner to send it himself".
- `guard.js`: the default is taken away for `a`, `area`, SVG `a` (also `xlink:href`), `ping`; session rule 2 blocks
  the stand-in address for held tabs.
- The unit's sandbox lines and `test_unit.py`; the snapshot expiry (5 and 30 minutes); the popup UI (Stop, a list
  of controlled popups); the proxy's upload branch (`verb == "upload"`).
- `reviews/20-chrome/REPORT.md` "Measured views": 221,477 characters in 14 pages on the long fixture.

**Assumed, not checked:**

- The sizes after #27 moves onto the slim generator: about 8,000 characters of descriptions plus instructions (my
  estimate from the shared suffix). Brief 28 records the real baseline.
- That Chrome unpins a pinned tab when it is put into a group (28b tests the restore).
- That a policy-installed extension isn't active in incognito unless he turns it on; 28b sets
  `"incognito": "not_allowed"` so it doesn't depend on that.
- That input can land in a tab that isn't selected (28b measures it; brief 20's code says it didn't).
- That a `MutationObserver` in the isolated world sees a field's `type` change with its old value (28b tests it).
- Call counts in the "Brief 20" column of the efficiency table come from reading the code, not from a run.

**Confirm on the #27 merge** (fix round 3 is only locally verified at `8b7e799c`; its Linux runs were pending):

- section 6, "What can't be stopped is never reported as stopped" and test group 2's fallback sentence (the default
  taken away for every link and submit-button kind, the five routes, the all-borrowed row as the only unheld one);
- section 6, "The text next to Send is bound too" and test group 3's sentence (line breaks and indentation count);
- "Known limits": the wording against the final `reviews/20-chrome/KNOWN-LIMITS.md`;
- the clipboard rule living in the Chrome server's instructions (at `8b7e799c` it is still in each description);
- the latency section of `reviews/20-chrome/REPORT.md` and the latency harness under `control/chrome/ci/` (neither
  exists at `8b7e799c`); brief 28 tells the builder to read the paths from the merged tree;
- the sentence that Aresus's host goes into the excluded-sites setting through the image (brief 18c).

## Where #27 and the owner's picture pull apart

1. **Looking at his tab moves it.** Reading needs a take, and a take moves the tab into Claude's group. 28b reads
   in place.
2. **The reload before the first input** loses his typing and stops his music: "fill in the rest of this form" and
   "skip this song" in his own tab both hit it. The rule stays (the hold needs it); it is judgment call 2.
3. **Claude's work comes to the front.** A new Claude tab opens in front, and every input selects Claude's tab in
   its window. In a window he is using, his view flips. 28b measures whether input lands in a background tab.
4. **A password he made visible before the take** is read by the late reader as plain text. 28b adds a passive
   marker and a name check.
5. **A pinned tab of his** probably comes back unpinned after a take. 28b restores the pin.
6. **Aresus isn't on the built fixed list.** The image has to add its host to the excluded-sites setting.

## What should change in files this change doesn't touch

- `docs/control/PLAN.md`: a dated entry for 2026-11-13 (briefs 28 and 28b written, section 6 draft 32); decision
  25's closing parenthesis should name the change of 2026-11-11 and section 6; "Owner questions still open" is no
  longer "none" (the three judgment calls); "Everyday tasks" could gain three Chrome tasks (his tab read in place
  with a look-alike open; a tab with typing; three tabs compared); "Order of work" gains 28 and 28b.
- `STATE.md`: the control layer's "Next" (brief 28 waits on #27's merge; 28b on 28 and the three answers) and the
  open owner decisions.
- `docs/control/TOOLS-HANDOFF.md`: "Decisions to write into CONTROL.md section 6" is done; "New work 1" is written.
- `HANDOFF.md`: where this stopped.
- `docs/control/FEATURES.md`: the builders change the Tool column (brief 28 item 9, brief 28b); a line that only one
  Chrome profile is seen.
- `docs/design/CONTROL.md` section 8, item 4: the tool-user round for "the tab his request clearly needs" (section 6
  already names it under test group 17).
- Board: the three judgment calls as `board ask` items.
