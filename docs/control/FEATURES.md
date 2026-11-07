# Mail and Chrome: every feature, and where it stands

Updated 2026-11-07. The owner's picture is "every app with all of its features" as clean tools
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
| Submit a form, post, send a message, any request that sends | `chrome_submit` | send | first |
| Typing and Enter where the message hold can't be in place | `chrome_submit_input` | send | first, on sites with an adapter; refused elsewhere (reloading the page usually brings the normal hold back) |
| Sends on the owner's trusted sites | `chrome_submit_trusted` | send, free | first, for operations a site adapter recognises; deleting and paying are never free |
| Apps that read through POST (Notion, Google's apps) | site adapter; GraphQL sorted by itself | | first for the owner's usual sites; elsewhere Claude's clicks there ask until an adapter exists |
| Drop what a page wanted to send | `chrome_drop` | change | first |
| Popups and new tabs a page opens | joins the Claude group | | first |
| Sign in to a site | | owner | owner: Claude stops and asks him to sign in; passwords never pass through Claude |
| Pay, order, transfer money | `chrome_submit` | send | first, always asking, never on the trusted list |
| Drag and drop, hover menus | `chrome_drag`, `chrome_hover` | change | later: after the tool-user rounds show where they're needed |
| Canvas editors and maps (text drawn, not in the page structure) | site adapter, or a last-resort picture | | later: per site, as the rounds show |
| Save or print a page as PDF | `chrome_export_pdf` to an allowed folder | change | later |
| Add and remove bookmarks | `chrome_bookmarks` | change | later |
| Windows: move tabs between windows | | | later |
| Site adapters for the owner's usual sites | per site | | after the tool-user rounds; sites from the owner's list |
| Chrome's settings, passwords, extensions; claude.ai | | | never: these could change Claude's own limits or approve its own actions |
| Screenshots as the way to see a page | | | never as the main path (owner); a picture only where a site adapter says it's the last resort |
