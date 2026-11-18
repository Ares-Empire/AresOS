# Chrome read: known limits

**read:** This starts with section 6 of [CONTROL.md](../../docs/design/CONTROL.md#known-limits), as merged
in step 14. Its wording is retained below, followed by the limits found in steps 1–13d and their disposition.
The design spans 28, 28a and 28b: statements about in-place owner-tab reads, the public tool switch, bounded
option descriptions, short-reference actions and universal address filtering describe those later packages.
Package 28 exposes its new read only under the CI switch; brief 20's public tools retain their addresses and
whole-view references. This list is an acceptance record, not a claim that later features shipped here.

## Section 6's standing limits

The list every tool keeps (`docs/REVIEW.md`, "Tools for Claude"): what it is, the harm, and why it is accepted. It
starts from brief 20's re-checks (`reviews/20-chrome/KNOWN-LIMITS.md`, *brief 20*). A limit is for low harm; a flaw
with real harm is fixed instead (owner, 2026-11-11). Each brief's report keeps the list true.

**A page acting on its own**

- **A page that sends on its own isn't held.** After an ordinary, free action (a click on a button without a telling
  label, typing, opening a chat), the page's own scripts, service workers or WebSockets can send what Claude entered
  or did: an autosave, an icon button that posts, typing indicators, read receipts, a send started after the
  500 ms hold. *Harm:* data leaves without a question. *Accepted:* the tool recognises actions before it acts; it
  doesn't intercept traffic (decision 25). The same holds for any browser tool.
- **A hostile page that borrows every step.** A page with a same-site window outside Claude's tabs can take every
  function it needs from that window (building the element, registering the handler, inserting it, dispatching the
  click) and so run a control labelled Delete during Claude's click without a question. The result reports Claude's
  click as dispatched, with what the page did unproven; it never says nothing happened. *Harm:* what that page could
  do anyway: it could call its own server without any click. *Accepted:* only a deliberately hostile page does
  this, and the three possible fixes each break a rule that matters more (they can't see the borrowed call, would
  expose password fields, or would attach to a tab that isn't Claude's).
- **Every click of Claude's counts as a user's click.** The page may then open a popup or write to the clipboard,
  as after his own click. Popups join Claude's tabs. A clipboard write is reported where the tool can see it
  (not through borrowed functions), never read. *Harm:* a page puts text on his clipboard. *Accepted:* withholding
  this would break ordinary clicks; the instructions tell Claude to tell him and never to paste or run clipboard
  contents because a page asked.
- **Between the check and the input** a page script can still change the page. *Harm:* the input lands on a page
  that differs from the question by an instant's change. *Accepted:* the check runs in the extension right before
  the input, which narrows this to an instant; it can't be closed from outside the page.
- **A page can notice the tool.** In a tab Claude controls, a script can detect that some functions are wrapped.
  *Harm:* a site may behave differently or refuse to work there. *Accepted:* it affects only Claude's tabs; nothing
  runs in the page's own world in his other tabs.

**What the tool recognises**

- **The word list is a rule of thumb.** A control that sends without saying so (an icon without a label, another
  word, another language) is free unless an adapter names it; a harmless control with a listed word ("Clear search")
  asks. *Harm:* a missed question, or one too many. *Accepted:* decision 25; the adapters name his usual sites'
  sends exactly, and the tool-user rounds count both kinds.
- **Data can leave through addresses.** Navigating and GET searches are free, so an address Claude writes can carry
  text to a site. *Harm:* as with `WebFetch` or any browser tool. *Accepted:* decision 25.
- **`done` doesn't prove what the site did.** The tool sees the input and the page, not the network. *Harm:* a site
  may have refused what was sent. *Accepted:* results say "as the page shows it", and nothing is ever sent again by
  itself.
- **Text next to Send that keeps changing.** A change adds one more question, showing before and after; a second
  change stops the send, and he sends it himself. Where the smallest area holding Send and the draft is the whole
  page, all its visible text is bound, so live text anywhere on such a page can end the same way. *Harm:* an extra
  question, or a send he does by hand. *Accepted:* it is the bounded price of binding previews; revisited after his
  live tests if his real sites hit it often.
- **His own delayed step in a Claude tab asks.** Within the 500 ms after Claude's input the tool can't tell whose
  input started a delayed page step. *Harm:* a question about his own action. *Accepted:* his decision (board
  #138).

**Dialogs**

- **A dialog already open when Claude took the tab** goes back to him. *Harm:* Claude waits for him. *Accepted:*
  Chrome gives no way to know who opened it or to hold what follows.
- **A dialog opened through a borrowed function** always asks, and what the page does after the answer isn't held.
  *Harm:* as "a page that sends on its own". *Accepted:* the question says so, and the answer runs once.

**Reading and his tabs** (*brief 28*, *brief 28a*, *brief 28b*)

Taking a tab from another normal window while a Claude tab group already exists moves the tab into that group's
window, because Chrome keeps a tab group in one window; the extension records the tab's original window and
position and moves it back on release. The harm is that the owner's tab sits in another window while Claude holds
it; it is accepted with the single-group design, and one group per window is a design question for brief 28b.

- **A page that changes what it shows without changing its address.** A read, a take or a close of one of his
  tabs is bound to the document and address the list showed. A page that swaps its content in place (a chat that
  switches conversations) keeps both. *Harm:* Claude reads other content of the same site than the title in the
  list promised. *Accepted:* it is the same page of the same site that his request pointed at, the result shows
  the title as it now is, and nothing in Chrome tells the two states apart.
- **`request` records Claude's reason; it proves nothing.** The tool can't check that a tab is the one his request
  needs. A careless Claude, or one misled by a page's text, can read a tab of his that the request didn't need and
  write a plausible reason. The **READ** sign, the popup list and the log come after the read: they let him see
  it, they don't prevent it. *Harm:* that page's text reaches Claude. *Accepted:* choosing the tab is the agent's
  judgment, as with any tool that reads on his behalf (decision 24), and reading his open tabs is what he asked
  for. What the tool can enforce, it does: the page bound to the list, his never-list, incognito, the password
  rule, and a question before every send. The tool-user round measures how well the instructions hold.
- **Reading a tab that Chrome put to sleep is a visit.** The page is fetched and its scripts start, as when he
  clicks the tab. *Harm:* the site sees the visit, and a page may mark something as read. *Accepted:* visiting the
  page his request needs is what he asked for, and navigation is free (decision 25). The result says that the tab
  was woken. "Leaves no trace" is promised only for a tab that is already loaded, and a tab that wakes with
  restored fields isn't known clean for a later take or close.
- **In his own tabs Claude sees what a form field holds only after asking.** Where the reader hasn't watched a
  page from its start, a field he can type into, single-line or multi-line, shows only whether it is filled
  ("What the extension can and can't do"). *Harm:* a question to him before Claude can read back a name, a
  number, a search or a message he typed into a form in a tab of his. *Accepted:* his decision (2026-11-13, board
  #210: "Ask first"), read by the lead to cover every typed form field; a password he made visible is a field
  that looks like any other, whatever its type is now, and the question shows him which fields are meant before
  any is read. A field named like a credential stays unread even then. What he writes in an editor (an editable
  area) is read without a question. A passive marker that proves each field's history could spare him the
  question later, after his live test. In Claude's own tabs the same hits one case: a filled typed field inside
  a component whose shadow root the reader met late. A form that holds such a field isn't sent by Claude at all,
  also after he approved a read of it: he sends it, or the page is reloaded first.
- **An approved read can still hold a password.** He approves a list of labels, and a password he made visible
  sits in a field whose label says nothing. *Harm:* that password reaches Claude after his own OK. *Accepted:* he
  is asked with the labels in front of him, for the tab he pointed Claude to; the tool can't know more about that
  field than its label, and a field it can recognise as a credential is never offered.
- **A secret in an editable area, unmasked before the reader came, under a label that doesn't name it.** In a
  document the reader didn't watch from its start, an editable area is read unless its name says credential or
  it is masked at that moment. A page that keeps a secret in an editable area, masks it by style, labels it only
  "Value", and that he switched to visible before Claude looked, is read like the text it then is. *Harm:* that
  secret reaches Claude. *Accepted by the owner* (board #216, 2026-11-13: "Read editors without asking", told of
  this risk; the final security check asked for the choice to be his): whole-page editors are editable areas, so
  not reading
  them would stop Claude from reading what he writes; a secret is kept in a form field on nearly every page, and
  every typed form field with unknown history stays unread; such a secret is plain text on his screen at that
  moment, like a key a page prints as text; the name list covers the labelled ones (secret, token, private key,
  recovery phrase, seed).
- **A short sign-in code under an ordinary name is shown.** The public form hides a value whose parameter is named
  like a credential or that looks random and is 20 characters or longer, and in a path what follows a sign-in
  word or looks random. A short code under a plain name (`?c=8f3k2j`), or a short or wordy key in a path, is
  shown on a page Claude reads, as in any browser tool. *Harm:* such a code reaches Claude's context, and a link
  that signs in by that code alone could be used by whoever holds it. *Accepted:* the owner's decision
  (2026-11-13, board #213, "Show link addresses"), taken knowing this. An address has to say which video, search
  or article it is, and the tool can't tell a short code from a page number. The names that sign-ins use are
  covered. The code doesn't reach the log, whose lines hold no query at all, and it isn't in the list of his
  tabs, where his request may have nothing to do with a tab.
- **A harmless long value is hidden too.** A document's id or a playlist's id looks as random as a token. *Harm:*
  Claude can't quote such a link whole; it opens the link by reference, or shows him the tab. *Accepted:* the
  tool can't tell the two apart, and hiding is the safe side.
- **A question may show a destination with a part hidden: he sees less there than the tool binds.** Where a
  form's or a link's address carries a value that looks like a sign-in, the question shows `…` for it, because a
  question reaches Claude too. *Harm:* he approves a destination with a part he can't inspect in the question.
  *Accepted:* the hidden part can't change after his approval: the operation keeps the whole destination, and the
  tool compares it right before the input and refuses a changed one. What the form itself sends is shown in
  full, hidden fields included. Showing that value would put a sign-in token into Claude's context.
- **A question shows a list's chosen option and how many options it has, not the others: he sees less there than
  the tool binds** (*brief 28a*). *Harm:* he can't see in the question which other options the list offered.
  *Accepted:* the form doesn't send them; the chosen option is shown with its label and its value, and so is the
  option a step is about to choose from the list; and no option can change after his approval, listed or not,
  because the operation keeps them all and the tool compares them right before the input. Listing them all made
  a form with a country list impossible to ask about.
- **A large form isn't sent by Claude.** What a form sends is shown whole in the question or the form isn't sent
  (rule 4.1), and an approval holds 16,384 bytes with a question of 4,096 characters. That is about 90 short
  fields, or 45 with 80 characters each, and a text next to Send of about 3,800 characters, or about 900 in a
  script outside ASCII; a long hidden value (a framework's page state) or hundreds of chosen options fill it too.
  *Harm:* he sends such a form himself; the tool says so, and says whether shortening the text Claude filled
  could help; a submission the page starts itself stays stopped.
  *Accepted:* it fails closed, and cutting what he approves would be worse than not asking.
- **A reload on take loses what isn't work:** an open menu, a place in an endless list, a selection. *Harm:* he
  finds his tab reset. *Accepted:* the take rule (owner, 2026-11-11); looking needs no take, and Claude can work on
  a copy of the page in its own tab.
- **A tab older than the extension counts as used.** A tab he has clicked or typed in is never reloaded or closed
  by the tool's own choice, so work a page holds only in its script's memory (an earlier step of a wizard) isn't
  lost without his say. The mark for "clicked or typed" is the browser's own record. Where text dropped in from
  another window, a paste from Chrome's own menu or a dropped file doesn't set it, a small script present from each
  document's start records only that a drop or a paste happened, and a tab with that record counts as used too
  (brief 28b measures which is the case, and fails closed). A document that script didn't watch from its start can't
  be known clean. *Harm:* none to his work; right after the extension is installed or updated, Claude asks before
  it reloads any tab he had open, and keeps those tabs on a close. *Accepted:* it errs on the side of his work.
- **A group of his that held only the taken tab comes back as a new group.** Chrome removes a group when its
  last tab leaves, and the tool makes one with the same name and colour on release. *Harm:* a group he had saved
  or synced isn't linked to the new one. *Accepted:* the tab, its place and the group's look are restored; Chrome
  offers no way to keep an empty group.
- **A tab from one of his groups, or a pinned one, shifts while it is taken.** Chrome allows a tab one group and
  no group among pinned tabs. *Harm:* that tab steps to the edge of his group, or out of the pinned tabs, until
  it is given back. *Accepted:* every other taken tab stays exactly where it is, and a release puts these two
  back.
- **In a taken tab, what the page's own script does after a step can lose what he did there.** Before Claude
  goes elsewhere, reloads, follows a link, or submits or resets a form in a taken tab, the tool looks for his
  typing and for his use of the page since the take, and asks him ("Which tabs Claude works in"). What a script
  does after any other step can't be seen beforehand: a button, a `javascript:` or `#` link, or a link that opens
  a new tab, whose script navigates; a form's other control whose script submits; a script that clears his work
  without navigating. A submission that such a script starts is held and asked as a send, with the form shown,
  only while the hold after Claude's step runs, and never for a GET search form; a later one navigates unasked,
  and the question doesn't name his other work on the page. *Harm:* his typing or other work in that page, in a
  tab Claude is working in. *Accepted* (the lead, 2026-11-16, after reviews 5 and 6): the tool can't know what a
  page's handler will do; the tab is marked as Claude's for as long as it is taken, and giving it back is one
  click; a page that guards its work makes Chrome ask "Leave site?", and that question is his. It is the one loss
  of his work the design accepts.
- **A tab with a frame the reader can't enter isn't taken or navigated by Claude.** An embedded PDF viewer and
  another extension's inline frame take no reader, so the tool can't tell whether they hold something of his (a
  PDF form can). Such a tab is never known clean, and no question is offered for it. Once such a frame appears
  in a taken tab, also one he hasn't used, Claude's link, form and reset steps there are refused too. *Harm:* he
  acts in that tab himself, or Claude works on a copy of the page in its own tab. *Accepted:* it fails closed;
  brief 28b measures which frames this hits, among them an extension's frame that appears when a field is
  focused.
- **An unchanged element can come to mean something else.** A reference is checked on its own element: its name,
  its value, its options, where its link leads. The page around it isn't checked. A button that keeps its name
  while the row around it now shows another item still runs. *Harm:* Claude takes a free step with an older
  picture of what stands next to the control. *Accepted:* a step the tool recognises as a send, a delete or a
  payment still asks, and its question shows and binds the item, the form and the draft as they are then; the
  result of every step says what changed during the call, not what changed before it.
- **Two runs of the service could draw the same letters.** A reference's five letters are random for each run,
  and nothing remembers earlier runs. Two given runs share their letters once in about four million. *Harm:* a
  reference Claude kept from the earlier run could then name another element, where the new run issued the same
  number for the same tab. *Accepted:* it needs a restart of the service while Claude still holds old
  references, that draw, and that number. An action on it still has to match what the service last showed for
  the new element, and a send still asks. A stored record of old letters would only move the gap to a lost or
  restored store, and a short record lets a prefix come back by itself.
- **The outline folds long content.** A control inside a folded part isn't in the first read. *Harm:* an extra
  call (`find`, or a read by `ref`). *Accepted:* it is the point of the budget; what asks is decided when Claude
  acts, on the element itself, never from the outline.
- **Marking page text untrusted doesn't make Claude immune.** A model can still misread or be misled by a page.
  *Harm and acceptance:* the normal MCP level (decision 24); everything a question shows is read and bound by the
  tool itself.

**Around the tool**

- **Fixtures aren't his real sites.** A real site's layout or bot check may need an adapter update or his own
  hand. *Accepted:* the staged check on his laptop after the first boot.
- **Crash tests cover the failures that were modelled.** *Accepted:* an unknown outcome is never repeated by itself.
- **Under decision 24,** a tricked Claude, or another program of his user, could disturb or imitate the native
  host or start Chrome in another way, as with any program of his (section 7).


## Limits found while building package 28

These retain the builders' accepted wording. Overlapping entries deliberately keep the exact statement
the lead reviewed. Source links identify where they were found; the sentences after each block explain its
present disposition. Browser evidence is mapped in [HARNESS-MAP.md](HARNESS-MAP.md); final run evidence is in
[REPORT.md](REPORT.md#verified).

### Reference paging and fold counts — step 1

- **A read can be paged until it has shown 5,000 references.** Then the first of them are dropped, their
  elements get new strings, and the next cursor is refused with "page changed, read again without the cursor" (test `test_a_read_of_more_than_5000_elements_never_returns_a_dropped_reference`). *Harm:* a page
  with more than 5,000 links or controls can't be read to its end with `full` in one chain; parts by `ref` and
  `find` still work. Every reference on a returned page is valid when it is returned.
- **A fold's count can be off by a few characters on such a page:** hidden references that were dropped are
  issued anew, with more digits.
- **Two runs with the same letters:** shown in `test_the_rest_shown_honestly_two_runs_that_draw_the_same_letters`,
  as section 6 lists it.

**read / accepted by the lead:** [step 1](PROGRESS.md#step-1-2026-11-14-claude-agent-on-fable-52-the-service-side-view-module-done)
and brief section 7 keep the 5,000-reference paging ceiling. See
`test_view_references.Bound.test_a_read_of_more_than_5000_elements_never_returns_a_dropped_reference`.
Every returned reference is live at return; use `find` or a smaller subtree after eviction. The counter never
reuses a dropped string. Repeated hidden-reference allocation can change a fold count by a few digits.
The forced equal-prefix case is explicitly a residual probability, not a uniqueness guarantee across processes.

### Conservative address hiding — step 1b

**read / accepted by the lead in brief section 7:** the safer matching rules also hide some ordinary text.
A long sign-in word inside a larger segment (for example reset inside `/presets/list`) hides the rest of the
path; login/signin/confirm and the other long words behave the same way. Mixed-case slugs with a digit can
look like tokens and become `…`; lower-case slugs remain. Credential-like parameter names can also hide an
ordinary keyword or state value. Harm: Claude sees less of an otherwise harmless address, and may need a
reference or the owner's help. Accepted because the rule cannot distinguish those from credentials; later
navigation by hidden-address reference belongs to 28a. See step 1b's “What the two address rules now also hide”
and `test_view_address.py`'s long-token/long-sign-in-word/ordinary-value tables. This is separate from the
owner-accepted short-code limit above.

### Late roots, deep trees and conservative credential names — step 6

- **A prefilled field in a web component isn't read.** A typed field that already holds text when the reader
  first meets its shadow root shows `(filled, not read)` for the life of the document, also when the text is the
  component's own default. *Harm:* Claude can't read or type into it, and can't send a form that holds it; the
  owner can let Claude read it through the asking read, or sends the form himself.
- **A page nested thousands of levels deep can't be read.** The reader's walk overflows and the read fails;
  nothing is returned. Beyond 150 levels the service refuses the reply.
- **A field named like a credential that isn't one is withheld** ("Seed" for a world seed, "Token" for a
  filter): the owner types it himself.

**read / accepted by the lead:** [step 6's decisions and limits](PROGRESS.md#the-leads-decisions-on-step-5s-open-points-2026-11-15),
then step 7's option (a), retained in step 8. The late-root rule follows complete observed masking history;
the asking read can reveal the value once but never permits Claude to send its form. The optional early-root
meeting refinement was not built. Thousands-deep trees fail closed; the service separately refuses depth over
150. A harmless credential-like name costs an owner action, rather than risking a secret. See `outline.test.mjs`,
`reader.test.mjs`, `test_view_nodes.py` and the group 7 late-root case.

### Editable areas, framed reloads and stopped forms — step 12

- **An editable area whose mask was taken off before the reader came, and whose label doesn't name it, is read**
  (section 6 has it; the owner's choice, board #216). Case 1 shows it on purpose. *Harm:* a secret he un-hid in such an
  editor reaches Claude. A `textarea` with the same history is not read.
- **A taken tab whose page holds a frame can't always get its reload from the tool** (brief 20's rule, met here):
  when the extension doesn't know a frame's request method, the reload is refused and Claude is told to open the
  address fresh. *Harm:* Claude can't act in that tab of his; it works in a tab of its own. Nothing is read or sent
  that shouldn't be.
- **A submission the page starts for a form with an unread field stays stopped in that document.** *Harm:* the form
  isn't sent until the owner sends it or the page is loaded again; nothing is sent unasked.

**read / accepted:** the editor behavior is the owner's board #216 choice. The lead accepted step 12's
reload substitute and requested later stopped-form calls; step 13a added both a read and a step in the same
document, with receiver still zero. `unread-matrix.mjs` proves these behaviors in groups 7 and 3.
A single approved read never clears the form refusal. The tool must open a fresh tab when a taken page's
frame method is unknown. No promise of reloading every framed owner page is made.

### Native reply size, process prefix and close cleanup — steps 13a–13b

- **Transport limits are separate from the rendered outline bound.** The native host bounds each individual
  message at **1 MiB**. The extension chunks replies above **512 KiB**; the bridge bounds an assembled reply
  at **32 MiB**; the strict JSON decoder then imposes its **6 MiB** input bound. No production bound changed.
  Compact H1 proves reference eviction, not that every verbose 20,000-node snapshot fits these limits.
- **The five-consonant service prefix remains probabilistic across process runs** (brief 28, item 3). These cases
  compare actual strings; they do not turn the roughly one-in-four-million prefix collision into a proof.
- **The cleanup cannot run on an event the service never receives.** A confirmed tool reply also clears entries;
  if connection loss hides both, entries may remain until the extension session changes or the service restarts.
  The per-tab bound does not bound how many former tabs can remain after lost events. No new stale-reference
  acceptance was found; generic read failures are deliberately not treated as proof of close.

**read / accepted by the lead:** [step 13b](PROGRESS.md#step-13b-2026-11-17-codex-gpt-61-sol-remaining-browser-reads-and-tab-reference-cleanup).
The original 13a finding that close cleanup had no adapter caller was fixed in 13b: current-session release
events and confirmed close/release replies now clear both indexes. Generic failure or a missing list page is
not proof of closure. If both event and reply are lost, the remaining RAM can last until a session change or
service restart; the bound is per tab, not across all former tabs. No stale-reference bypass was found.
`test_outline_action.Adapter` has the named event/reply/failed-close tests; reference restart and retake cases
run in the browser. Compact H1 reaches 20,000 nodes / 80,001 omitted; it does not prove verbose controls fit
the unchanged native-message, assembled-reply and strict-decoder bounds. A refused oversized read is accepted as fail-closed.

### Malformed UTF-16 and option ambiguity — steps 13c–13d

- **A lone surrogate in page text is shown as U+FFFD** (the lead's accepted 13c display limit). The identity of
  that malformed UTF-16 code unit is lost; the other text keeps its existing escaping.
- **Different lone surrogates that both repair to U+FFFD are indistinguishable
  at service-held approval/expected comparisons**. Changing only U+D800 to U+D801 or U+DC00 is accepted there,
  because Claude and the owner saw the same repaired string. Any change visible after repair, including added
  whitespace, still refuses. Valid surrogate pairs and all other characters stay unchanged. This is the lead's
  specified limit, not a change to strict JSON validation.
- Two native option values that collapse to the same repaired value are ambiguous and are refused. The owner
  selects them himself. The page's native option strings remain unchanged.

**read / accepted by the lead:** [step 13c](PROGRESS.md#step-13c-2026-11-18-codex-gpt-61-sol-merged-read-cost-work-and-the-native-unicode-boundary)
records the display decision; [step 13d](PROGRESS.md#step-13d-2026-11-18-codex-gpt-61-sol-approval-comparisons-use-the-repaired-page-representation)
and the step 14 brief accept the comparisons and unique raw-option lookup. Only malformed code-unit identity
is lost. Visible changes, including whitespace, still refuse, and distinct raw options with the same repaired
value refuse as ambiguous. The owner selects those options himself. `native-unicode.test.mjs` and
`service-comparisons.test.mjs` exercise both the repair and the accepted equivalence; the seven removal
mutations fail. Strict JSON validation remains intact.

### Duplicate-label question descriptions — carried to PR #106

**read:** the unchanged asking path writes the same label twice in its question text. Its prepared description
distinguishes the two element identities and swapping them refuses. The case proves identity binding; it does
not demonstrate two distinct human descriptions in the question sentence. Harm: the owner sees two equal labels
without enough distinction in that sentence. The lead explicitly keeps the package 28 asking path and instruction
text unchanged, and assigns the stronger human-description requirement to the 28a/28b revision,
[PR #106](https://github.com/Ares-Empire/AresOS/pull/106). This is tracked work for those builds, not a claim of
completed descriptive coverage. See steps 13b–13d, `outline-asking.mjs`'s duplicate-labelled swap case, and
`test_questions.py` for exact approval echoes. Unlabelled fields already have distinct stable descriptions.

## Findings that were fixed, rather than accepted as limits

- Step 1's separator-split long-token leak: closed by section 7 decision 7 in step 1b; address tests hide it.
- Step 6's shadow fixtures prefilled before meeting: option (a) retains the production withholding rule; fixtures
  now start empty and fill later, preserving their original approval and receiver assertions. The real-site
  prefilled-component limit remains above. The asking read now follows the withheld-field mark.
- Step 13a's missing adapter close cleanup: fixed by 13b, with the lost-event residual above.
- Step 13b's entire H1 read failing at the strict surrogate boundary: transport repair in 13c, then comparison
  consistency in 13d. The old unchanged-title `stale_approval` blocker is closed, not an accepted refusal.
- H1's control named `hidden` masking a native form property: fixed in 13c, with native getter regression.
- Step 13d's child fixture SSE replacing its parent: fixed without changing a hostile string, assertion or
  deadline. All ten asking cases now execute. This was a harness defect, not a product limit.

**assumed / review boundary:** synthetic browser profiles do not prove behavior on the owner's real pages.
The lead's Codex astra package and security reviews remain; deployment waits for 28a and 28b as well.

### Fix round X1 — rejected defects and narrow remaining costs

**read / fixed, not accepted limits:** Presentation roles no longer bypass native field withholding or expose
textarea default text; the legacy generic-role fallback is covered too. Slashes and later question marks in
credential parameter values cannot select route parsing. Failed reads trim every tab to 5,000 references.
File-name and selected-option changes move the state token, wake until and invalidate cursors. Full page and
subtree reads fetch all select options within the existing deadline; a compact option label is cut at 200
characters with the select reference as the route to its complete text. Tests and baseline failures are in
REPORT's X1 table and HARNESS-MAP.

**read / conservative display choice:** An assignment-like fragment whose name also contains a sign-in route
segment is wholly hidden. This can hide a harmless unusual route; it prevents exposing a sign-in path tail as
a parameter name. Ordinary `#/inbox/thread/1` routes remain readable. The X1 request explicitly calls for
ambiguity to fail toward redaction. Full reads with many incomplete selects may exhaust their existing command
deadline and return `not_read`; they never present a 50-option prefix as the complete list. A clipped ordinary
option label takes a field-detail call (and paging if needed) to recover the whole label. No new approval or
asking-path behavior is introduced.
