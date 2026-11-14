# Control service and Mail

This is brief 18's shared Python service, caller-side MCP/CLI and fake adapter,
plus brief 19's IMAP/SMTP Mail adapter. Mail tests use isolated synthetic servers.
Brief 18d implements decision 24: run `claude` normally, as the owner, with his own
settings, login, projects, MCP servers, plugins and skills. Nothing here confines
Claude. Managed ask rules protect calls through Claude Code's permission prompt;
the owner user's direct CLI/socket access remains an accepted route around it.
Packaging remains an image-setup draft; `os/` integration is a separate package.

The current Fedora container is **Fedora 45 x86_64**, pinned by manifest digest in
the workflow; CI tested **Python 3.15.0** and prints its version. The lock supports CPython
3.14 and 3.15. The only direct third-party runtime dependency is the official
**MCP Python SDK 2.3.0**. All its transitive dependencies are pinned with wheel
hashes. The service, CLI, filesystem policy, journal and hooks use the standard
library. Mail additionally uses the already pinned `cryptography` 50.0.2 for
RFC 8058's DKIM check; no new package or lock change is needed. The SDK and its dependencies are used by the MCP proxy and its test client.

Generate artifacts with `python3 control/generate.py`. CI runs
`control/ci/test.sh` **inside a disposable Linux container**; that script installs
packages and a root-owned test prefix there. Do not run it on a desktop host.

## Process and request contract

`aresos-toold` runs as `aresos-tools`. Its only listeners are Unix stream sockets:

| Socket | Accepted peer (Linux `SO_PEERCRED`) | Calls |
| --- | --- | --- |
| `act.sock` | exactly configured owner UID, excluding root/service UID | public actions and caller byte transfers |
| `admin.sock` | root only | owner-only actions, through `sudo aresos admin …` |
| `chrome.sock` | nobody, including root | placeholder, always refuses |

The directory is mode 0711, act mode 0666, admin/chrome mode 0600. The service
cannot chown a socket to another user without privileges, so act's identity gate
is the kernel peer credential, checked before parsing a request. Root still has
the normal machine-administrator powers. A single serialized dispatcher also
serializes reservation, cancellation, expiry and the submission boundary. Invalid
or slow clients get a two-second read deadline; large transfers are capped.

Ordinary connections carry one UTF-8 JSON object terminated by LF and one response,
then close. File transfers exchange multiple acknowledged frames on one connection.
Maximum frame: 6 MiB, protocol `v: 1` on the opening request. No TCP fallback,
pickles, shell execution, path expansion or user-supplied module imports.

```json
{"v":1,"method":"tools","app":"testapp"}
{"v":1,"method":"call","action":"testapp_list","arguments":{"limit":3}}
```

Responses use `{"ok":true,"data":{…},"pending":{…}}` or
`{"ok":false,"error":{"code":"…","message":"…"},"pending":{…}}`.
Model-facing results are capped at 48 KiB. Lists have snapshot-bound cursors and
at most ten entries per page; an invalidated cursor requires a new read. `pending`
contains up to five compact references, a total and a cursor. Full operation
descriptions remain available through operation status, with no approval truncation.
`control_pending` and `control_log` page across all apps. The log includes time,
action, input summary, outcome and operation id. Log dates use the service's
local timezone. Returned app text is marked `untrusted_content`; each MCP server sends the shared
untrusted-data and recovery rules once as initialization `instructions`. Descriptions
keep action-specific guidance and the instruction to copy approvals unchanged.

Three private methods implement file movement for public file actions. Both sides
use raw-byte offsets and chunks of at most **1 MiB**, base64 encoded inside bounded
frames (about 1.34 MiB each). The sender waits for an acknowledgement before the
next frame; pipelining and extra messages are refused.

- Upload opens with `upload {app,file:{sha256,size,name,real_path}}` and waits for
  `data:{ready:true}`. Each `{offset,bytes:<base64>}` receives `data:{offset:<next>}`.
  `{end:true,offset:<total>}` ends the stream. Only after exact size/hash validation
  does the service publish its mode-0400 blob and return `data:{file:…}`. Cut-off,
  incomplete, reordered, oversized or mismatched streams remove their private
  staging file; service startup also removes staging files left by a crash.
- Download opens with `download {app,sha256}` and receives `data:{sha256,size}`.
  The caller requests `{offset}` and receives `data:{offset,bytes:<base64>}` until
  the declared size, then sends `{end:true,offset:<total>}` for completion. The
  proxy checks the complete hash before saving. Transfer bytes never become
  model-facing results; the proxy returns only the saved path, size and hash.
- `saved {app,outcome}` reports the caller's save success/refusal. Export intent
  is logged before bytes leave the service. A caller crash can leave an intent
  without completion; inspect the destination instead of overwriting.

The service never opens a caller path. The default per-file limit is **25 MiB
(26,214,400 bytes)** on both sides, configurable independently as `file_limit` in
`settings/proxy.json` and `settings/service.json`; both limits must permit a file.
Increasing a configured limit does not increase chunk or wire-frame size.

## Operations and backups

Preparation is a change action. It reserves an operation without submitting it and
returns `approval`, the exact input for send/delete. Its first field is a service-written
plain-English `question`, followed by `operation_id` and the complete `description`.
Pass all three unchanged, including the question. Mail questions summarize at most
three recipients per group, attachments and delete targets, then say "and N more";
individual summary names keep up to 80 visible characters (delete subjects 120),
followed by an ellipsis when longer. The send subject remains as written. Questions count
toward the 16 KiB limit and are also bounded to 4,096 visible characters; an overflow
refuses the whole approval before reservation. Full fields follow the question.
The description includes the account, complete recipients (including Bcc), all caller-written text, immutable
attachment metadata and paths, or each exact deletion target's metadata and revision,
plus the approval deadline. Controls, bidi and other format characters are escaped
inside the strings; literal backslashes are doubled to keep escaping unambiguous.
The UTF-8 canonical JSON approval limit is **16 KiB**. Oversize preparation is
refused before reservation; the owner still needs to qualify complete terminal and
phone display at this limit. An MCP proxy cannot prove that a permission prompt
happened: managed Claude Code ask rules provide that gate in the later deployment.

Operation ids are `generation:random-id`. The log stores the exact approval hash,
immutable payload and per-target/stage outcomes. Only the stored payload executes.
Same id and input returns the existing operation; changed input is refused, even
after completion. Runtime revalidation precedes a durable `submitting` transition.
The default approval lifetime is **900 seconds (15 minutes)**, configurable as
`approval_ttl` in `settings/service.json`. Cancellation and expiry act only on
`reserved`. Expiry is polled by the service,
also checked immediately before submission, and drops the operation without sending.
Expired/cancelled notices stay visible until explicitly acknowledged. Partial and
unknown operations remain pending. No restart, status query, repair or hook resubmits.

The main log uses SQLite rollback journaling with `synchronous=FULL`. Each write
first appends and fsyncs its compact hash-chained record, then stages its complete
event in SQLite and commits, applies the event and commits SQLite's head, and
finally appends/fsyncs a matching commit marker. The separate record is durable
before any part of that write commits to SQLite. Directory entries are fsynced
when created. App work begins only after this sequence completes. On a crash,
recovery finishes only a staged transaction whose full event matches the record,
never app work. Startup turns every `submitting` operation into `unknown`. A
database behind the independent committed high-water mark is **locked**, and all
app calls/transfers are refused. A record with an uncommitted tail also locks if
its full staged event is missing. This includes an ordinary power loss between
syncing the record and committing the full event: it cannot be distinguished from
a restore. The owner must run `restore_confirm` below; the operations named by
that record become `unknown` with their short descriptions, even reservations
that were never acknowledged. Nothing is silently dropped or resumed.

Back up the state directory (using SQLite's backup API or with the service stopped)
and immutable blobs. **Never restore, roll back or copy the independent evidence
directory with that backup.** Defaults are `/var/lib/aresos-tools` and the separate
`/var/lib/aresos-operation-evidence`. Its `operations.jsonl` retains only operation
ids, generations, exact input hashes, the service's short descriptions (action,
account, recipients/targets, subject/title), and states with timestamps. Sequence,
format and chain/commit hashes provide the restore fence. Bodies, attachment bytes
and metadata, item contents, detailed stages and full audit events stay in SQLite
or the blob store. `aresos log` reads today's audit events from SQLite. The fake
receiver keeps its separate far-side SQLite fixture in the evidence directory;
production Mail/Chrome will use genuinely remote evidence.

Startup verifies the journal one line at a time and rebuilds the disposable
`journal-index.sqlite` beside it. The index keeps record hashes/offsets and the
latest compact operation evidence on disk, with a 1 MiB SQLite page cache; it is
never trusted across restarts. Its creation asks the shared storage ledger first.
If it cannot fit, startup succeeds without it: asking actions refuse with
`storage_limit`, while cancellation, status and owner restore use streaming
journal reads. This fallback trades extra scans for bounded memory and no index
writes. Historical records and audit pages stream from
disk instead of remaining as Python objects. Retained evidence and startup scan
time still grow with history; the permanent journal is unchanged.

After an older backup is detected, only the owner can run:

```sh
sudo aresos admin control restore_confirm --input '{"confirm":"invalidate earlier approvals"}'
```

Confirmation writes bounded batches (at most 32 operations and a 64 KiB permanent
record), holding a durable restore lock until the final new-generation write.
Its result lists up to 100 unknown IDs and points to `control_pending` for the rest.
Missing/newer operations from the independent
record become `unknown`, retaining their short descriptions. Details absent from
the restored main log cannot be reconstructed from the separate record. Earlier-generation ids
can be read and locally repaired but never approved or submitted. Reserved operations
from the restored generation are invalidated. A repair is a new logged operation
pointing at the old one. Mail keeps at most one unresolved repair per local stage.
Repeating it checks Sent by the original Message-ID or reads the pinned reply's
answered flag: presence settles it done. A negative Sent search settles a repair
failed only on a fresh IMAP connection at least 15 minutes after its attempt ended;
earlier absence stays unknown and names when to try again. Inconclusive checks
write nothing. Every Sent APPEND gets a fresh read-only count afterward; multiple
copies produce a warning in the operation and the existing bounded persistent
notice pages. Nothing is deleted. Permanent evidence retains repair/send/stage
identity and the attempt end time. Missing older identity blocks another repair
instead of guessing. Status remains read-only.

All local durable writers ask one space ledger, including journal/database
transactions, index builds, blobs, passwords, expiry and owner archives/compaction.
A pending approval holds its cancellation budget; an unresolved repair holds its
settlement budget; a detected restore holds its bounded confirmation budget.
Each write leaves all held budgets plus one fixed 4 MiB safety floor. Cancel,
settlement and confirmation spend their own budget and need no second reserve.
Rights release when the approval is submitted, expired or cancelled, the repair
settles, or confirmation finishes. Startup rebuilds these holds from durable
operations and verified permanent evidence. The compactable SQLite audit quota
still separates ordinary-work headroom from recovery and owner maintenance; that
logical quota is independent of physical free-space admission.
A missing/corrupt independent record, a torn journal line or
an inconsistent chain fails closed and needs owner recovery; the restore command
does not silently erase corrupt evidence. This pre-deployment record format is
version 2; the earlier full-event format fails closed and needs owner recovery
rather than automatic migration. There is deliberately no journal rotation
or compaction yet; retaining operation tombstones is essential for safe recovery.

The receiver records every arrival without deduplication so tests cannot hide a
double send. It supports recipient refusal, lost answer, pre-submission failure,
Sent-copy failure and answered-flag failure. `done` means fixture acceptance;
`partial` reports accepted/refused recipients or missing local stages; `unknown`
requires far-side inspection. The Message-ID evidence hook derives identity from
the operation id and checks before submission. Positive preflight evidence is
durably recorded as `unknown` before fetching its details; it cannot subsequently
be cancelled or expired as nothing submitted. Missing evidence proves nothing.

## Caller file policy and launch chain

The root-owned proxy configuration names a home and specific folders beneath it;
defaults are Documents, Downloads and Desktop. Roots themselves and every component
are opened with directory descriptors and `O_NOFOLLOW`, starting at `/`. Original
path strings are checked before normalization. Dot components, traversal, credential,
profile, configuration and startup names are refused. Reads require a regular
single-link file, within the configured limit (default **25 MiB**), check inode
metadata before and after reading,
and report the descriptor's real path. Hard-linked credential aliases are refused.
After import, changing the original has no effect: the service hashes, stores
mode-0400 blobs and verifies their bytes again before use.

Saves require a safe ASCII basename, a hash match and an allowed directory. They use
Linux `O_TMPFILE`, then link the pinned anonymous inode into the pinned directory
without overwrite. A collision with any file, symlink or hard link refuses. Directory
identity is checked before and after publication. On failure after publication,
the pinned inode is truncated and fsynced, clearing renamed and hard-linked aliases
too. Cleanup never unlinks a name: Linux has no atomic unlink-if-inode-matches.
The refusal reports the empty inode's device/id, link count, original destination
and current pinned folder; empty entries remain, and other alias locations cannot
be enumerated. If truncation or sync fails, `save_incomplete` explicitly warns that
bytes may remain or survive a storage failure. An unsupported filesystem fails closed. A process running as the
owner can still move or modify a completed download afterward, as it can any owner
file. Decision 24 imposes no confinement; the optional sandbox fixture is tested
separately in `control/boundary/`.

Installed entry points use a fixed `/usr/bin/python3 -I -S`, `/usr/bin/env -i`, a
fixed PATH/LANG, and root-owned code under `/usr/libexec/aresos-control`, vendor
dependencies under `/usr/lib/aresos-control/vendor` and config under
`/usr/share/aresos/control`. `-S` also blocks `.pth`/`sitecustomize` execution. The launcher
checks ownership, mode and symlinks throughout those trees and their ancestors,
then adds only the trusted code/vendor directories to isolated Python's stdlib path.
No environment variable can change config, module path, interpreter or prefix.

## Hooks

`Stop` reads `control_pending` and returns `{"decision":"block","reason":"…"}`
while work is held/unfinished, unless `stop_hook_active` is already true. That guard
allows the owner to receive a report about work that cannot be resolved. The next
`UserPromptSubmit` reads again and returns
`{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"…"}}`.
Each managed launcher names its event independently of input: `launch.py hook Stop`
or `launch.py hook UserPromptSubmit`. The managed prompt command has a fixed shell
guard that emits Python's output only on success and always exits 0, covering
interpreter startup failures before Python code can run. A different
`hook_event_name` is malformed.
No transcript, current directory or prompt path from hook input is opened. Input
is read in full, including long prompts and final assistant messages. A hook reads
only `hook_event_name` and `stop_hook_active` and checks their types; every other
field is accepted and never read, because Claude Code adds and changes input fields
between versions (2.1.319 sends `prompt_id`, which a closed list refused in every
turn; found by brief 18c's VM test). `Stop` reminds when the service can't be reached
(a `block` decision that says so) and reports malformed input or its own failure on
stderr with exit 2. Both block a stop once: when the input parses and
`stop_hook_active` is already true, it ends quietly. Input it can't parse (over the
size limit, not strict JSON) exits 2 at every stop, up to Claude Code's own limit on
blocked stops. `UserPromptSubmit` exits 0 with no output on any failure, including unreadable
or malformed input, service failure, and installation/configuration errors, so
it never discards the owner's prompt. Valid prompt input still adds the pending
reminder. Hooks are reminders; service expiry is the safety net during interrupts,
continuation limits and ended turns.

Contract **read**: [Anthropic hooks reference](https://code.claude.com/docs/en/hooks),
2026-11-07. Target **Claude Code 2.1.319**, as recorded in the council branch's
`reviews/control-checks/2026-11-07-permission-prompt.md`. No Claude binary or model
is run by this package. MCP contract **read**:
[official SDK v2.3.0](https://github.com/modelcontextprotocol/python-sdk/tree/v2.3.0).

## Slim Claude Code setup (decision 24)

`boundary_policy.py` is the single definition for the generated managed settings:
`permissions.ask` for every served asking tool and the existing `Stop` and
`UserPromptSubmit` notification hooks. No sandbox, deny list, source lock, plugin
lock or forced permission mode is shipped. The generated `settings/CLAUDE.md`
states that only the owner in the session gives instructions; it enforces nothing.
Image setup installs these files root-owned under `/etc/claude-code/` (the draft
settings file becomes `managed-settings.json`). Remove the former exclusive
`managed-mcp.json` during migration; it is no longer an artifact of this package.

Our MCP servers install under the owner's user scope like any other server.
`settings/user-mcp.json` maps each server name to the complete JSON argument for
`claude mcp add-json --scope user`. Brief 18c will ship it read-only as
`/usr/share/aresos/control/user-mcp.json`. The owner runs this in his
own session after installing Claude Code (`~/.local/bin/claude`). It is safe to
repeat: each run removes our entry of the same name, if there is one, and adds it
again from the shipped file.

```sh
python3 - <<'INSTALL'
import json, subprocess
from pathlib import Path
claude = str(Path.home() / '.local/bin/claude')
servers = json.loads(Path('/usr/share/aresos/control/user-mcp.json').read_text())
for name, server in servers.items():
    subprocess.run([claude, 'mcp', 'remove', '--scope', 'user', name],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([claude, 'mcp', 'add-json', '--scope', 'user', name,
                    json.dumps(server)], check=True)
INSTALL
```

Existing unrelated MCP entries are retained; a user-scope entry of his own under
one of our server names (`control`, `mail`, later `chrome`) would be replaced. A
local or project entry of the same name is left alone, and takes precedence over
ours in its folder. Server names must stay stable: `mcp__mail__send` names the
`send` tool on the installed `mail` server.
`testapp` is served by the service, so its send/delete asks are shipped and
required too. Only its MCP entry is omitted from `user-mcp.json`; the harness
installs it at user scope under the name `testapp`. A generator check rejects an
ask that does not name an exposed tool of a served app under its installed server
name. Testapp is the sole exception to requiring a shipped user-scope entry.

Before preparing or submitting asking work, the service reads only the installed
managed settings through root-owned, non-writable, non-symlink path components.
Every generated ask must be present, exactly named. Additional settings, rules,
hooks, drop-ins, caches and plugins are allowed and are never inspected by this
check. This is an installation precondition, not proof a prompt was answered.
`PermissionRequest` hooks and direct service access remain the decision-24
residuals. Broad owner auto-approval hooks must exclude our asking tools. The
native harness records print-mode behavior; interactive hooks remain an 18c gate.

### Adding Chrome or another app

Add definitions to `ACTIONS` and register its adapter; `installed_apps()`,
`user_mcp()`, `asking_rules()` and `managed_settings()` discover it automatically.
Run `python3 control/generate.py` and commit all generated files. App-wide guidance
belongs in `instructions_for(app)`; descriptions retain only action-specific rules.
Every public send/delete asks unless **explicitly** marked `trusted_send=True`.
A trusted send must implement `adapter.require_trusted_send(verb, operation)`:
return exactly `True` only when a current matching owner-only entry authorizes the
entire payload, and recheck on every submission. Missing, false or empty decisions refuse. No existing Mail action is a trusted send on this
branch. The base refuses a marked send without an installed checker. Do not mark
a preparation, read, change, delete or owner-only action trusted. Chrome's future
trusted submit must also preserve its own exact-state binding at execution.

## Adding Mail or Chrome

1. Add action definitions in `definitions.py`: one effect, closed input schema,
   result contract, exact references, and a description explaining use, output and
   recovery. Owner-only actions stay off act/MCP. Generate and commit artifacts;
   every new send/delete must appear in the generated ask list.
2. Implement the `Adapter` contract and register it in `Engine.adapters`. App names
   come from the definitions. Keep platform, provider and browser code in the adapter.
   Its `call` method dispatches its read/change verbs, while every send/delete effect
   goes through the shared submission engine. `TestApp` demonstrates the contract
   and fake far-side fixture.
3. `prepare` must return `(question, description, payload)`: the service's plain-English
   question, authoritative description and immutable payload, from the same facts.
   `question(verb, description)` also provides the introduction for local repairs.
   The base shares this approval format with every adapter, including Chrome.
   Keep all Claude-written content in the approval, and generated material
   by immutable size/hash reference. Reference checks must fail stale. `revalidate`
   must check every approval-relevant fact immediately before submission, with an
   adapter-qualified exclusion strategy for concurrent changes, or refuse.
4. `execute` runs only after durable `submitting`. Record each irreversible target
   and each later stage through `stage()`. Raise `NothingLeft` only with proof nothing
   left; otherwise uncertain exceptions become `unknown`. `evidence` supplies a
   preflight duplicate guard and readable far-side evidence. For Mail derive the
   Message-ID from the id and check Sent; absence never authorizes retry. Chrome must
   retain control of held bytes across the whole release boundary or refuse.
5. `repair` must contain no submit/delete transport path. It repairs only qualified
   local stages, and the engine logs a new operation pointing to the original. Add
   stage-specific repair evidence as needed. Do not turn `unknown` into `done` from
   absence of evidence or a single recipient's receipt.
6. Use the caller file actions/byte protocol, never a path opened by the service.
   Represent a late hold by a reserved operation via `Engine.reserve`; give the
   bridge its own fail-closed expiry and implement `drop` to discard held bytes on
   cancellation/expiry without release. A bridge must also drop on loss of service,
   including restore lockout; `drop` may never submit or unblock a request by sending.
   Return holds and
   incomplete work through the shared pending catalogue so both hooks can find it.
7. Add provider/bridge fixtures, crash checkpoints for every new stage, exact-state
   approval races, read-without-change tests, partial outcomes and restore tests.
   Do not treat this package's socket/import tests as the later sandbox or real-image
   qualification. Phone display, real accounts and final managed policy remain owner
   gates for later packages.


## Mail

The generated [tool reference](../docs/control/TOOLS.md) and
[Mail MCP catalogue](generated/mail-tools.json) are authoritative. The generated user-scope
MCP entry starts the Mail proxy through the same protected Python launch chain as the base.
No account, endpoint or credential is shipped. Public account results expose aliases,
capabilities and SPECIAL-USE folders, never host/login details or passwords.

Owner setup: `sudo aresos admin mail account add --input JSON`. Its input schema is
`mail_account_add` in the generated reference. A real terminal is required; the
password is read with `getpass`, outside argv/history, and travels only over the
root-only admin socket. The service stores it in a service-owned 0700 directory and
0600 regular file. It rejects missing/unreadable/wrong-mode credentials and has no
fallback source. TLS uses a verifying default context, hostname checking and at least
TLS 1.2; SMTP supports implicit TLS or mandatory STARTTLS, IMAP implicit TLS.
Credentials are accessed only after TLS verification.

Onboarding discovers capabilities and SPECIAL-USE roles, probes nonempty DELETE on a
unique throwaway folder with synthetic data, then sends one logged self-probe. Every
probe send/delete has an operation id before it acts. An interrupted setup remains
unready; it is never repeated or resumed automatically. Existing ids are refused for
re-enrollment, so the owner must inspect the retained probes before choosing a new id.
A server Sent copy observed in the bounded probe window establishes server saving.
If none appears, client saving is only a bounded observation: the account remains
unready until the owner confirms with
`sudo aresos admin mail account_settings --input '{"id":"chosen-id","sent_policy":"client"}'`.
The same owner-only action sets `format` and `signature`; defaults are plain and no
signature. It cannot enable an interrupted setup or override the folder-delete guard.
An empty leftover probe folder on an unsafe server is reported for the owner to remove.

`mail_compose` stores a complete immutable composition and returns id/hash plus the
mail description. Nothing is sent. Local `{path:...}` attachments are imported by
the caller proxy using the base's allowed-root policy and 25 MiB per-file limit;
the service opens no caller paths. Existing mail parts are copied by decoded sha256.
`mail_prepare_send` returns a reserved operation's entire approval; `mail_send`
accepts that exact object. Its `operation_id` is the service-issued request id.
All authored text, aliases, To/Cc/Bcc, signature, format, threading, attachment names,
paths, sizes and hashes appear in the approval. Immutable generated quotes/forwards
appear by source reference, size and hash. Controls and bidi characters are visibly
escaped; inputs beyond 16 KiB are refused in full. Approval still expires in 900 seconds.

Replies derive recipients from Reply-To/From, remove owner aliases, and reply to own
sent mail's original To/Cc. Threads use Message-ID/In-Reply-To/References across
non-Trash/Junk folders, keeping duplicate ids and using internal-only ids when missing.
Formatted authored text supports bold, italic, lists, links and quotes; raw HTML stays
literal. Forwarded `.eml` attachments use `application/octet-stream` with their exact
rebuilt bytes from recursive message/MIME header allowlists, removing Bcc and Resent
headers; decoded binary leaves stay byte-exact. Approval binds the transmitted hash.
Drafts are any message with the authored marker, a freshly fetched IMAP `\Draft` flag
in any folder, or a source in SPECIAL-USE Drafts or its subfolders. Their source and
all extracted parts refuse attachment, as do nested marked drafts; use `mode=draft`
or forward inline instead. Their entire inline/reply/draft text appears in approval,
including differing readable HTML, or the approval refuses as too large. Only
`mail_draft_save` writes the marker; outgoing mail and Sent copies are unmarked.
Existing drafts keep their plain/HTML body when `text` is omitted. Draft edits save
new revisions and retain the old revision; deleting it requires a separate named
delete approval. Sending a draft
also retains it. Configured signatures apply to newly authored text; an unchanged draft
already contains its signature and gets no additional one.

Submission records each RCPT answer, final DATA answer, Sent copy and answered flag.
The Message-ID comes from the operation id and is checked in Sent before SMTP.
Absence proves nothing. Lost final answers are unknown, refused recipients partial,
and no outcome is retried automatically. Client-managed Sent copies retain Bcc for
the owner; transmitted headers omit Bcc. Server-managed Sent copying is left to the
server. Exact wire bytes are stored privately for local-stage repair (64 MiB aggregate
encoded-mail cap, independent of the per-file transfer cap). Repair never opens SMTP
or repeats a POST/delete, and requires a durable successful final DATA answer. It
checks Sent for the operation's Message-ID before appending another copy. An unknown
submission without that answer stays for owner inspection even if a Sent copy appears.

Every message reference includes account, folder, UIDVALIDITY, UID and Message-ID.
UIDVALIDITY changes fail as stale, search again. Reads always use BODY.PEEK and do
not fetch remote content or send receipts. Source pages use a reversible Latin-1 byte
mapping; `attachment_save part=source` saves the exact `.eml`. Bodies page at up to 6,000
characters, reduced as needed for the serialized byte cap; list pages default to five (maximum twenty). Cursors bind to query and
folder/message state. CONDSTORE/QRESYNC are enabled when advertised; full metadata/byte
re-reads remain authoritative, including on servers with neither extension. History
scans currently refuse beyond 10,000 messages, and encoded source mails beyond 64 MiB: choose smaller explicit folders or use the owner's mail program.
Search reduces each fetched body to its summary before retaining it; contacts and
thread indexing fetch headers only. This conservative full-scan implementation needs
large-account performance qualification.
Mail-derived headers, addresses, attachment names and text are untrusted data, including
when repeated in a composition; they never authorize an action.

Move/copy destinations must be exact selectable LIST names. Trash and descendants are
refused. Any source in Drafts or its subfolders refuses move/copy before the first
server change, including unmarked owner drafts: send with `mail_compose mode=draft`,
or delete with `mail_delete`, which asks the owner. Ordinary messages may be moved
or copied into Drafts. `mail_flag` cannot add or remove `\Draft`; permitted moves
between ordinary folders preserve it. Delete preparation rechecks every named
sender/subject/date/reference; execution checks the complete set before the first
mutation and each UID at use. Trash uses MOVE;
permanent deletion uses only UID EXPUNGE and requires UIDPLUS. No code calls CLOSE or
broad EXPUNGE, so unnamed messages marked Deleted survive. Folder deletion requires
an empty non-special leaf and an onboarded server guard against nonempty DELETE.
Both pinned upstream fixtures allow nonempty DELETE, so they remain unqualified. A
clearly test-only serialized guard frontend covers the positive concurrent-delivery
path over real GreenMail storage; it is not a production shim or provider qualification.

Unsubscribe accepts only exact List-Unsubscribe choices read from the source mail.
Mailto choices build their exact named mail and follow the normal send operation path.
HTTPS one-click requires the header pair and a full SHA-256 DKIM signature covering
both, checked after approval with system DNS and the already pinned crypto library.
It sends exactly `List-Unsubscribe=One-Click`, with no cookies, GET, redirect or retry.
Unsupported/invalid signatures or DNS failures refuse POST; use a header mailto choice
or the owner's mail program. DKIM uses a conservative subset (RSA or Ed25519,
simple/relaxed, no partial-body signatures), rather than trusting inbound
Authentication-Results text.

Run `bash control/ci/mail/run.sh` only on a disposable GitHub Linux runner. It first
runs the unchanged base installer/suite in pinned Fedora, disconnects that container's
external network, and attaches it with pinned GreenMail and Dovecot to a private
`--internal` network. No ports are published. TLS keys and synthetic mailboxes are
discarded; only test output/server logs are uploaded. The Mail workflow runs on this
branch and its PR; the base workflow still runs independently on the PR.

### Mail round 7: reviewed roles, draft exports and decoded headers

Before moves/copies, deletion, draft save, folder changes, draft decisions and send
preflight, current LIST SPECIAL-USE roles must be complete (Sent, Drafts, Trash,
Junk, Archive), unique and match owner setup. A server role change refuses these
operations. The owner fixes missing/duplicate roles on the server, then runs:

```
sudo aresos admin mail account_folders --input '{"id":"ACCOUNT"}'
sudo aresos admin mail account_folders --input '{"id":"ACCOUNT","roles_hash":"HASH_FROM_REVIEW"}'
```

The first command shows escaped, untrusted folder names and a hash, without
recording changes. The second re-reads and records only the reviewed mapping;
no probe mail or account re-add is needed. Earlier Trash and Drafts folders and
their descendants stay protected after refresh. This does not enable incomplete
onboarding or change the server's folder deletion qualification.

Claude cannot save any draft part or its source through `mail_attachment_save`,
including HTML and binary attachments. The owner saves draft attachments in his
mail program; Claude can compose the draft itself with `mode=draft`. Ordinary
received and sent parts still export their original bytes, after inspection that
refuses nested draft provenance and unsupported structures.

Write outgoing header values as decoded Unicode. Claude-written encoded words,
C0/C1 controls, bidi and invisible formatting characters refuse. Original-mail
subjects and recipients are decoded before storage; derived formatting characters
are escaped in approvals. Display names appear beside their addresses. Independent
validation decodes exact outgoing Subject/From/To/Cc bytes and compares names,
addresses and the complete To/Cc/Bcc SMTP envelope with approval, at compose and
again before DATA. A mismatch fails without submission or replay.

Mail audit summaries use service-written text. External values, recipient stage
keys and caller save paths are structured inside escaped `untrusted_content`;
`control_log` and `aresos log` also mark historical Mail summaries. A mail's
instructions never become instructions from the audit service.

### Mail rounds 9–11: filing warnings and blob exports

Each role root records its own LIST hierarchy separator. Required-role separator
changes need the owner's folder setup review; old Trash and Drafts roots keep their
own separators after refresh. Legacy setups without per-root metadata must use the
same owner setup step; separators are read from each listed root, never INBOX.

Free move/copy requires UIDPLUS. A durable filing intent records source references,
target and per-message progress before acting. After each MOVE/COPY, any role drift
stops the batch with a partial result, a compact warning, filing id and counts,
and the first bounded page of exact COPYUID destinations, observed locations and
scan completeness. Nothing is moved back or deleted; copies
are never expunged. Missing COPYUID is partial even when role names remain stable.
Connection loss during reporting preserves observations so far and records partial.
The newest three compact unacknowledged warnings stay in following Mail results'
pending notices and in `aresos log`, including on later days; a count points to
`mail_filing_notices` to page all remaining warnings. Each warning includes the
filing id, affected-message count and at most three folder names of 64 characters
(with an ellipsis for longer names and "and N more" for additional folders).
Exact references remain stored internally and come from `mail_filing_locations`
with that filing id, following its cursor until null. Pages stay below 12 KiB of
location content. A single oversized per-message record uses ordered JSON
fragments instead: concatenate by message_index/offset, then decode JSON once.
All returned display values escape controls and bidi like audit entries; stored
references keep their exact values. Location pages remain readable after restart
and acknowledgment. `mail_notice_ack` receives
its filing_id as operation_id. This acknowledges the warning only; cleanup requires
ordinary named `mail_delete` approval. It creates no approval operation. An interrupted
intent stays visible in the audit log; restart never resumes filing or tries recovery.
A role that moves to the target and back between the command and the post-check can
escape detection: filing ends done in the intended target, with no protected role at
the end and no message lost.

Folder renames can also move a non-special leaf folder between parents. An exact
new path selects the destination; a bare new last name keeps the current parent.
Special folders and their descendants remain protected. Before RENAME, a durable
intent records source, destination, message count and the observed roles. LIST
checks the new location and roles afterward. A protected ancestor, a special role
assigned by the new name or an unverifiable result returns partial and uses the
same bounded persistent notices above. Nothing is renamed back or deleted.
An interrupted rename intent remains in the audit log and is never replayed.

Shared blobs carry durable origin metadata. Only an explicit owner export can be
saved by any app; internal composition parts, draft bodies, quotes and wire copies
are private even when their hashes appear in results. Caller imports alone do not
grant download rights, and attachment hashes still require caller-import provenance
and metadata. Ordinary non-draft attachment_save explicitly exports original bytes.
Missing legacy origin metadata grants no export/import permission. The testapp
fixture is absent from shipped user-scope MCP entries; its explicit imported-file
export action exists for test configurations only.

Historical operation status always returns the saved approval and stages; a failed
live Sent lookup appears separately as evidence_error. Composition strips surrounding
spaces/tabs from subjects and display names before approval and wire validation.
