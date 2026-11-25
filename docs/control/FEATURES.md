# Mail and Chrome: every feature, and where it stands

Updated 2026-11-08. The owner's picture is "every app with all of its features" as clean tools
([`OWNER-SCOPE.md`](../../reviews/councils/2026-11-07-control-layer/OWNER-SCOPE.md)). This list makes that concrete
for the first two apps, so nothing is left out without saying so. Each feature has a tool and a test, or a plain
reason why it waits. The owner adds to it and decides what can wait; nothing moves to *later* or *never* without
being written here.

- **first:** in the first release, with a test, and each one a task in the tool-user rounds.
- **later:** planned; why it waits is given.
- **owner:** the owner does it himself, by design.
- **never:** not offered to Claude, with the reason.

Effects: read, change, send (asks), delete (asks). Tools are in
[`docs/design/CONTROL.md`](../design/CONTROL.md) sections 5 and 6.

## Mail

| Feature | Tool | Effect | State |
|---|---|---|---|
| Accounts, addresses, capabilities, special folders | `mail_accounts` | read | first |
| Add an account, set or change its password | `aresos admin mail account …` | owner | owner: passwords never pass through Claude |
| Folders with counts | `mail_folders` | read | first |
| Create, rename a folder | `mail_folder_create`, `mail_folder_rename` | change | first |
| Delete a folder (empty, without subfolders; its mails deleted first) | `mail_folder_delete` | delete | first where the server refuses deleting a folder that holds mail (checked at onboarding); elsewhere the owner deletes the empty folder in his mail program |
| Search by sender, recipient, subject, text, dates, flags, attachments | `mail_search` | read | first |
| Read a mail: headers, text, HTML as readable text, attachments list | `mail_read` | read | first |
| Read the raw source of a mail | `mail_read` (part `source`) | read | first |
| Whole conversation across folders | `mail_thread` | read | first |
| Save an attachment, or a whole mail as `.eml`, to an allowed folder | `mail_attachment_save` | change | first |
| Write a new mail; reply; reply all; forward (inline or as attachment) | `mail_compose`, then `mail_send` | change, then send | first |
| "Don't ask again" for mails to an exact set of recipients (for example to himself) | a free send action checking the owner-only list | send, free | first (decision 15); every other mail asks |
| Formatted mail (bold, lists, links) and plain mail | `mail_compose` | change | first; the default is the owner's habit |
| Signature | `mail_compose` from the account's configuration | change | first; text from the owner |
| Attach local files, or attachments of other mails | `mail_compose` | change | first |
| Save, update and delete drafts; send a draft | `mail_draft_save`, `mail_delete`; `mail_compose` from the draft, then `mail_send` | change, delete, send | first |
| Move and copy between folders (not to Trash) | `mail_move`, `mail_copy` | change | first |
| Mark read and unread, flag, answered, custom keywords | `mail_flag` | change | first |
| Delete to the Trash, or for good; empty the Trash | `mail_delete` | delete | first |
| Mark as junk or not junk | `mail_move` to or from Junk | change | first |
| Status and repair of a send (Sent copy, flag) | `mail_operation_status`, `mail_operation_repair` | read, change | first |
| Unsubscribe through the mail's own unsubscribe header | `mail_unsubscribe` | send | first |
| Read receipts | none | | never sent by Claude unless the owner asks for that mail: a receipt tells the sender the mail was read |
| Several accounts | configuration | | first; works like one |
| Contacts: addresses the owner has written to | `mail_contacts` from mail history | read | first |
| Address book of the provider (CardDAV) | | | later: a Contacts app of its own |
| Calendar invitations: read; accept or decline | `mail_read`; reply needs Calendar | read; send | read first; answering later with a Calendar app |
| Send later at a set time | | | later: needs the service to keep a scheduled operation; the approval would come at scheduling time |
| New mail arrives: Claude is told | IMAP IDLE into the session | read | later: needs a way to wake the central session |
| Server-side filters and vacation reply | | | later: depends on what the provider offers (checked at onboarding) |
| Print or save a mail as PDF | `mail_export_pdf` to an allowed folder | change | later |

## Files

AresOS runs normal Claude Code, as on any OS, plus our tools (decision 24). Claude's own file tools and terminal work
as his own user under the permissions he sets; our tools only add safe saving and exact attaching.

| Feature | Tool | Effect | State |
|---|---|---|---|
| Read, change, create, rename, move and delete files in his home and projects | Claude Code's own file tools and terminal | as in normal Claude Code | first (decisions 17 and 24): as his own user, as on any OS |
| Save a mail attachment | `mail_attachment_save` (rule 4.4) | change | first: into the folder named (`~/Downloads` by default) under a safe name, never over an existing file, never into a hidden folder or a start-up place, without execute bits |
| Chrome's own downloads | Chrome, as normal. `chrome_library` with `kind: downloads` lists them | read | first: Chrome saves them where it always does (decision 25) |
| Attach or upload a local file | `mail_compose`, `chrome_upload` (rule 4.4) | change | first: the question shows the real path and the hash, and exactly those bytes are sent |
| Run terminal commands | Claude Code's terminal | as in normal Claude Code | first, under his permissions; Claude Code's sandbox is an option he can turn on (`sandbox.enabled`, then `autoAllowBashIfSandboxed: true`, decision 17); it keeps commands away from the tool service only with `allowUnsandboxedCommands: false`, no excluded commands, Unix sockets not allowed and the service's socket folder denied for reads, and even then best-effort (CONTROL.md section 7) |
| Start the session with skip-permissions | `claude --dangerously-skip-permissions` | | first (decisions 23 and 24): sends, deletes and submits through our tools still ask (managed ask rules) |

## Coding and project work (decisions 23 and 24)

| Feature | Tool | Effect | State |
|---|---|---|---|
| Work on code in his project folders: edit, build, test, git | Claude Code's file tools and terminal | as in normal Claude Code | first, in the same session as mail and Chrome |
| Install packages and command-line tools | the terminal | as in normal Claude Code | first: his own account installs software normally |
| Pull, push, branches, pull requests, publishing | git and `gh` with his own logins | as in normal Claude Code | first: what asks is set by his own permissions, as on his other machines |
| Work on project folders himself with his own git, editor or file manager | | owner | as on any OS |
| Test a project against its own local server in a browser | a clean throwaway browser started from the terminal (for example Playwright's Chromium) | | first: none of his sign-ins, not his Chrome |
| Check a project on a real site in his Chrome | the Chrome tools | read; sends ask | first, like any site |

## Adding tools (decision 24)

| Feature | Tool | Effect | State |
|---|---|---|---|
| Add an MCP server, a claude.ai connector, a skill or a plugin; remove one | as in normal Claude Code | his choice | first: as on his other machines; decision 22's install-asking path is dropped |
| Use an added tool | its own tools | as in normal Claude Code | first, under his permissions; our managed ask rules cover our own asking tools |
| His own `PermissionRequest` hooks (hooks that answer permission prompts for him, for example a broad auto-approve) | his settings | owner | they must not match our asking tools (the send, delete and submit tools of Mail, Chrome and later apps), so such a hook never answers for him; whether one could approve a managed ask at all is tested in brief 18c |
| Our app servers (Mail, Chrome, later apps) | installed for his user by the image's setup, like any MCP server | | first: their send, delete and submit tools always ask |

## Which tool a site gets, and later tool families (owner, 2026-11-18)

**The route rule.** A site with a real API or command-line tool gets a direct tool (GitHub: `gh`, already there).
Our own Empire apps get API tools (below). Everything else goes through the Chrome tool and its site adapters.

| Feature | Tool | Effect | State |
|---|---|---|---|
| Aresium's API tools | an API tool for Aresium on our server | read; sends ask | later: before or alongside the Minecraft tool (owner, 2026-11-18: "aresium maybe before or simultaneous to minecraft"); we own both sides, so it's a cheap, clean tool |
| Arestemis's and Aresus's API tools | an API tool per app | read; sends ask | later, not a priority (owner: "the rest isnt priority (I use only phone anyways)") |
| Minecraft stage 1: Claude sees where he is and what's around, builds, goes places and runs commands; creative first | through our own Fabric mod (the hub's channel) | change | later: after the Chrome adapters, with `linux-hub`, which owns the mod. His own singleplayer world is enough; not Lunar ("I dont care abt lunar for now") |
| Minecraft stage 2: Claude as a survival player in his world | the stage 1 tool plus a planning loop | change | later: after stage 1 |
| Minecraft stage 3: a Claude player genuinely pro at modern PvP, not just the sword. Owner's list: pearl and wind charge; mace (also mace and axe against shields); water and trident (riptide); crystal; totems (also refilling from the inventory); spear, elytra and mace; sword; shield; blocks; cobwebs; rails; TNT minecarts; TNT and fishing rod. In his words: "I wanna see some form of claude minecraft player a pro at all of that genuinely beating pro pvpers" | kit by kit: each mechanic a coded module with exact physics from the game code (trajectories, explosion, fall and mace damage, totem timing); the mod reads the exact game state every tick (no screen reading); a fast learned policy for movement and combo choice, trained by self-play in a sped-up world (`/tick sprint`, a headless server or a stripped combat simulator); Claude designs the modules and the training, and analyses recorded fights | change | later: research, no rush, after stages 1 and 2. Benchmarks: him first, then pro players who agree, on his own server. Self-play training needs GPU compute, which is spending, so it's the owner's call when we get there. Singleplayer or his own server only: bots get banned on public servers |

## One-time codes, suggested when needed (owner, 2026-11-25)

The owner's idea, written down so it isn't lost; not scoped yet. A phone offers a sign-in code from a fresh SMS or
mail right above the keyboard. Laptops mostly don't (Windows at best offers to copy a code it spots in a
notification), and even phones miss codes that arrive in Gmail and other mail apps. AresOS should do it for every
mail account he has, whichever program or website he reads it in: notice a new mail with a code, and offer the code
at the moment a field asks for one.

| Feature | Tool | Effect | State |
|---|---|---|---|
| Find codes in new mail, in every account | a code watcher in the tool service, on the accounts Mail already holds; it needs the same IMAP IDLE piece as "New mail arrives" under Mail | read | later |
| Chrome: when a code field gets focus (`autocomplete="one-time-code"`, the code words of the credential-word list, a row of single-digit boxes), a small suggestion under the field shows the code, the sender and its age; one click or Tab fills it, every box of a split field included | our Chrome extension | change, on his own click | later: needs our script in his tabs before he uses them, which section 6 of [`CONTROL.md`](../design/CONTROL.md) rules out today ("Nothing of ours watches a tab of his before the first read"), so it is the owner's call |
| Other apps (native and Flatpak): a fresh code shows as a toast; a key types the newest code into the focused field. Later perhaps a suggestion like the iPhone's bar over the keyboard, through an input method (check what labwc supports) | `aresos-toast` ([`HOME-OUTSIDE.md`](../design/HOME-OUTSIDE.md)); today's toast lets clicks pass through, so the action is a key | change, on his own key | later |
| Mail he reads only in a browser (Gmail, Outlook and others on the web) | the account route below | read | later |
| Move the code mail to the Trash once the code is used, as iOS offers | the code watcher, on his own setting | delete | later, optional |
| Codes from SMS | for example an iPhone Shortcuts automation that passes code messages to the laptop through Aresus | | maybe later: an iPhone doesn't share SMS with Linux |

**Mail read in a browser (explored 2026-11-25).** The code arrives at the mail server, not at a program, so the
route that covers every program reads the account:

1. **The account, signed in once in AresOS (the route to build).** The Mail tool already keeps accounts in the tool
   service (`aresos admin mail account …`) and reads them over IMAP. A code watcher there sees every new mail,
   whether he reads it in Chrome, in a mail program or not at all. This is the owner's "sign in centrally" idea,
   without a browser. The gap: Gmail and Outlook.com don't let other programs sign in with the normal password; they
   need a Google or Microsoft sign-in (OAuth) or an app password, and today's Mail tool signs in with a password
   only. A Google and Microsoft sign-in is the main new piece. Their mail APIs (Gmail API, Microsoft Graph) are an
   alternative to IMAP behind the same sign-in.
2. **Our Chrome extension reading an open webmail tab (fallback).** Works for webmail with no IMAP, but only while
   that tab is open, and it watches a tab of his, which needs the same owner's call as the Chrome suggestion above.
3. **A hidden browser signed in to the webmail (last resort).** Works with any site, but it keeps a full sign-in on
   disk, breaks when the site changes its pages, costs memory on a 16 GB laptop, and Google often blocks sign-ins
   from automated browsers. Only for a provider with neither IMAP nor an API.

**Rules carried from the control design.** A code is a credential:

- Codes go from the tool service to his screen only, never to Claude, its tools or its session. The reader never
  reads a code field and Claude never types a code (section 6 of [`CONTROL.md`](../design/CONTROL.md)); filling
  stays his own click or key, never an action on `act.sock`.
- Offer only fresh codes (a few minutes old) and show the sender. In Chrome, offer a code only where its sender
  matches the site, and keep it out of the page until his click, so a look-alike site can neither be offered a
  bank's code nor read it from the suggestion; phones do this with domain-bound codes (`@example.com #123456`).
- Type the code rather than copy it: the clipboard is open to every program of his, Claude Code's terminal
  included. Where copying is the only way, clear the clipboard soon after.
- Open question: Claude can already read a code mail through `mail_read` and `mail_search`, while a sign-in code
  reaching Claude is never an accepted limit (section 6 of [`CONTROL.md`](../design/CONTROL.md), owner,
  2026-11-11). Whether the Mail tool should hide codes from Claude, and how, is open; it matters with or without
  this feature.
- Codes are found by local rules (the usual formats, English and German wording). Mail text never goes to an outside
  AI for this.
- The suggestion and the toast use AresOS's own look.

## Chrome

The light tool (decision 25): our extension in his normal Chrome, no proxy and no certificate. It asks before
anything that clearly sends; a page that sends on its own after an ordinary action isn't held, the same as with Claude
in Chrome ([`CONTROL.md`](../design/CONTROL.md) section 6).

| Feature | Tool | Effect | State |
|---|---|---|---|
| List tabs with titles and addresses | `chrome_tabs` | read | first |
| Bring a tab and its window to the front, for the owner to look, sign in or answer a dialog | `chrome_show` | change | first |
| Take one of the owner's tabs into the Claude group; give it back | `chrome_take`, `chrome_release` | change | first |
| Open a page in a new Claude tab; close a Claude tab | `chrome_open`, `chrome_close` | change | first |
| Back, forward, reload, go to any web address (his, from a page, or one Claude wrote) | `chrome_go`; `chrome_open` with a link's `ref` | change | first, free (decision 25; data in an address isn't held); only `https:`, `http:` and `about:blank`, never `javascript:`, `data:`, `file:`, `chrome:` or app schemes |
| Read the page as structure with positions; paged; text search | `chrome_read` (`find` for text search, `until` to wait for text) | read | first; text read by the extension's own script, never screenshots; password fields excluded before anything is read |
| Read one form with all its options | `chrome_read` with the form's `ref` | read | first |
| Frames from other sites, shadow DOM, dialogs on the page | `chrome_read` | read | first |
| Read up to five tabs in one call, to compare them | `chrome_read` (`tabs`) | read | first |
| Click, type, choose from lists, tick boxes, press keys, scroll | `chrome_do` (steps `click`, `fill`, `select`, `check`, `press`, `scroll`) | change | first, free, except the asking cases below, which are prepared instead of run; every input is classified by what it would activate (a click, Enter or Space on a focused control, a key, filling, choosing, ticking) |
| Fill a whole form in one call | `chrome_do` | change | first |
| Several steps in one call (click, type, choose, tick, press, scroll, answer a dialog, wait), with what they changed | `chrome_do` | change | first: each step as its own action would run it; the call stops at the first step that asks |
| Searches on any site (a search form sent as an address) | `chrome_do` | change | first, free |
| Submit a form (a submit button, Enter in a form's field, a submission the page's script starts while handling Claude's click, key, filling, choosing or ticking) | `chrome_do`, then `chrome_submit` | send | first: asks before it runs; the question shows the site, the button, the destination and every field as the page shows it; it runs only if the page still shows that, checked right before the input; a stopped submission resumes once, as the same kind of submission, without repeating Claude's input |
| Click a control labelled send, post, publish, reply, comment, buy, pay, order, book, subscribe, delete, remove, discard, clear, empty or trash (and the German words) | `chrome_do`, then `chrome_submit` | send or delete | first: asks before the click |
| Enter, Ctrl+Enter or Cmd+Enter in a message or compose field | `chrome_do` (`press`, or `fill` for line breaks), then `chrome_submit` | send | first: asks; line breaks in Claude's text go in through `chrome_do`'s `fill` step, never as Enter |
| Delete or Backspace outside text editing (on a selected item, card or object) | `chrome_do` (`press`), then `chrome_submit` | delete | first: asks (decision 14) |
| A control without a label that deletes something kept only in the browser | `chrome_do` (`click`) | change | free (decision 14, the gap accepted) |
| The page's own script activating a send, buy or delete control while handling Claude's input | | | stopped before delivery and reported to Claude, never resumed; if the action is wanted, Claude acts on the control itself, which asks |
| A page that sends on its own after an ordinary action (autosave, an icon button that posts, typing indicators, read receipts) | | | not held, as with Claude in Chrome (decision 25) |
| Page dialogs (alert, confirm, prompt) | `chrome_do` (`dialog`) | change | first; accepting a confirmation with a listed word asks on its own, unless the approved operation named exactly that confirmation in advance (an adapter) |
| Upload a local file | `chrome_upload`, then `chrome_submit` | send | first: asks; the question shows the path and the hash, and the field gets exactly that copy |
| Downloads: list them and where Chrome saved them | `chrome_library` (`kind: downloads`) | read | first; Chrome downloads as normal |
| Bookmarks and history: find addresses | `chrome_library` (`kind: bookmarks` or `history`) | read | first |
| Drop a prepared operation | `chrome_drop` | change | first |
| "Don't ask again" for a kind of action | `chrome_submit_trusted` | send, free | first, for kinds a site adapter names ("GitHub: star"), bound to site, account and parameters and checked against the page; set and revoked only by the owner; never for deleting or paying, and WhatsApp messages ask each time (decisions 15 and 16); for mail see Mail |
| See and revoke "don't ask again" entries; mark sites read-only | `chrome_sites`; the extension's details page | owner | owner: Claude can't write these lists |
| Popups and new tabs a page opens | joins the Claude group | | first |
| Sign in to a site | | owner | owner: Claude stops and asks him to sign in; password values are never read and passwords never pass through Claude |
| Pay, order, transfer money | `chrome_do`, then `chrome_submit` | send | first, always asking (decision 15) |
| Stop Claude in Chrome at once | the Stop button in the extension's popup | owner | first: ends control, sends nothing |
| Calls, Safe Browsing, his own extensions, Chrome's updates | | | work as normal: Chrome isn't changed |
| Drag and drop, hover menus | `chrome_drag`, `chrome_hover` | change | later: after the tool-user rounds show where they're needed |
| Canvas editors and maps (text drawn, not in the page structure) | site adapter, or a last-resort picture | | later: per site, as the rounds show |
| Save or print a page as PDF | `chrome_export_pdf` to an allowed folder | change | later |
| Add and remove bookmarks | | change | later |
| Windows: move tabs between windows | | | later |
| Site adapters | per site | | first: Gmail, WhatsApp Web, GitHub, his bank (read-only), Gemini and Deezer (decisions 9 and 25) |
| Gmail in Chrome: send a mail | `chrome_submit` through the Gmail adapter | send | first, asking, the question reading like a mail (To, Cc, Bcc, subject, text, attachments from the compose); "don't ask again" bound to an exact recipient set, compared with the compose at the moment of sending (decision 15) |
| WhatsApp Web: send a message | `chrome_submit` through the WhatsApp adapter | send | first, asking per message with the chat and the text as the page shows them (decision 16); opening a chat and typing are free |
| His bank's pages | the read-only rule | read | first: reading, scrolling and links only; filling, buttons and uploads refused |
| Gemini: ask a question | `chrome_submit` through the Gemini adapter | send | first: asks with the text as the page shows it; he can set "don't ask again" for it per account (decisions 7 and 15); deleting or sharing a chat always asks |
| Deezer: playback and library | the ordinary actions through the Deezer adapter | change | first: play, pause, skip, seek, volume, queue, like, follow and add to a playlist are free; removing or deleting asks (decision 15); posting, sharing or paying asks |
| Chrome's settings, passwords, extensions; claude.ai and Remote Control; the Anthropic console; Aresus | | | never in a Claude tab: these could change Claude's own limits or approve its own actions |
| Cookies, saved passwords, browser storage | | | never: the extension doesn't read them |
| Screenshots as the way to see a page | | | never as the main path (owner); a picture only where a site adapter says it's the last resort |
