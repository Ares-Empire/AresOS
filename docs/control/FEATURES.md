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
| Save a mail attachment or a download | `mail_attachment_save`, `chrome_downloads` (rule 4.4) | change | first: into the folder named (`~/Downloads` by default) under a safe name, never over an existing file, never into a hidden folder or a start-up place, without execute bits |
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

## Chrome

| Feature | Tool | Effect | State |
|---|---|---|---|
| List tabs with titles and addresses | `chrome_tabs` | read | first |
| Take one of the owner's tabs into the Claude group; give it back | `chrome_take_tab`, `chrome_release_tab` | change | first |
| Open a page in a new Claude tab; close a Claude tab | `chrome_open`, `chrome_close_tab` | change | first |
| Open a new site, or an address Claude composed | `chrome_open_site` | send | first (rule depends on the owner's data-leaving answer) |
| Back, forward, reload, go to an address | `chrome_navigate` | change | first |
| Read the page as structure with positions; paged; text search | `chrome_read`, `chrome_find` | read | first |
| Read one form with all its options | `chrome_read_form` | read | first |
| Frames from other sites, shadow DOM, dialogs on the page | `chrome_read` | read | first |
| Click, type, choose from lists, tick boxes, press keys, scroll | `chrome_click`, `chrome_fill`, `chrome_select`, `chrome_check`, `chrome_press`, `chrome_scroll` | change | first |
| Fill a whole form in one call | `chrome_fill_form` | change | first |
| Page dialogs (alert, confirm, prompt) | `chrome_dialog` | change | first |
| Upload a local file | `chrome_upload` | change | first |
| Downloads: list, save into an allowed folder | `chrome_downloads` | read, change | first |
| Bookmarks and history: find addresses | `chrome_bookmarks`, `chrome_history` | read | first |
| Submit a form, post, send a message, any request that sends | `chrome_submit` | send | first: the send waits at the checkpoint outside Chrome, and only the approved captured send goes, at most once (a crash while sending can leave it not sent or sent in part: `unknown`, never repeated) |
| Typing and Enter on chat sites (messages on a live connection) | `chrome_fill`, `chrome_press`, then `chrome_submit` | change, then send | first: the message waits at the checkpoint, also on connections opened before Claude started; chats that encrypt in the page (WhatsApp Web) need an adapter for a readable description; there each message asks usually once (sometimes a second time for late frames), as one approval of the bounded set of encrypted frames captured from the start of composing until shortly after Send, described "as the page shows it" (weaker than a verified send: the page's display is trusted; decision 16) |
| Click a control that may delete data kept only in the browser (labelled delete, remove, discard, clear, empty or trash, in English or German; Delete or Backspace outside plain text editing, also on an object selected in an editable area) | `chrome_click_destructive` | delete | first: asks before the click; with a qualified adapter, one bounded advance approval per operation; an unlabelled control that deletes such data stays free (decision 14, the gap accepted) |
| "Don't ask again" for a kind of action | `chrome_submit_trusted` | send, free | first, for kinds a site adapter recognises by validating the complete operation ("Deezer: add to playlist"), set and revoked only by the owner; never for unrecognised sends, deleting or paying, and never on WhatsApp Web (the checkpoint can't read its encrypted messages); for mail see Mail (decision 15); an adapter update that widens a kind asks him again |
| See and revoke "don't ask again" entries | `chrome_sites`; the extension's details page | owner | owner: Claude can't write the list |
| Searches on the owner's usual sites | `chrome_fill`, `chrome_press` | send, free | first: free there (decision 7; the list of usual sites is the owner's); elsewhere a search carrying Claude's text asks |
| Apps that read through POST (Gemini, Gmail, Notion, Google's apps, GraphQL sites) | site adapter | | first for the owner's usual sites (17c: Notion and Google Docs need one); a GraphQL `query` is not reading by itself; elsewhere Claude's clicks there ask until an adapter exists |
| Drop what a page wanted to send | `chrome_drop` | change | first |
| End a site's guard (it ends by itself only where a site adapter shows nothing of Claude's is left; the owner's own sends there are checked until then) | `chrome_end_guard`, or one click on the extension's notice when Claude is done there | send (asks) | first |
| Switch the checkpoint to pass-through after a fault (Claude's Chrome tools off until it's back) | `chrome_checkpoint` (`sudo aresos admin chrome checkpoint …`) | owner | owner: only when no guard holds leftovers, or after he has seen them |
| Calls in Chrome (voice, video, screen sharing to a peer) | `chrome_end_call` (asks) | owner | owner: work only while no guard is on and Claude isn't acting; Claude acts during a call only after his answer to `chrome_end_call`, which ends every call in Chrome (unless a `PermissionRequest` hook answers it: unknown until 18c, the accepted residual if it can) |
| Sites that need WebRTC data channels; sites that need WebTransport | | | WebRTC: refused while a guard is on, works otherwise; WebTransport: doesn't work through the checkpoint at all (Chrome refuses it with a proxy) |
| Popups and new tabs a page opens | joins the Claude group | | first |
| Sign in to a site | | owner | owner: Claude stops and asks him to sign in; passwords never pass through Claude |
| Pay, order, transfer money | `chrome_submit` | send | first, always asking (decision 15) |
| Drag and drop, hover menus | `chrome_drag`, `chrome_hover` | change | later: after the tool-user rounds show where they're needed |
| Canvas editors and maps (text drawn, not in the page structure) | site adapter, or a last-resort picture | | later: per site, as the rounds show |
| Save or print a page as PDF | `chrome_export_pdf` to an allowed folder | change | later |
| Add and remove bookmarks | `chrome_bookmarks` | change | later |
| Windows: move tabs between windows | | | later |
| Site adapters for the owner's usual sites | per site | | first: WhatsApp Web, Gemini, Gmail, Deezer (decision 9); more after the tool-user rounds |
| Gmail in Chrome: send a mail | `chrome_submit` through the Gmail adapter | send | first, asking, the approval reading like a mail; "don't ask again" bound to an exact recipient set, validated in the captured send (decision 15) |
| Chrome's settings, passwords, extensions; claude.ai | | | never: these could change Claude's own limits or approve its own actions |
| Screenshots as the way to see a page | | | never as the main path (owner); a picture only where a site adapter says it's the last resort |
