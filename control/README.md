# Control base

This is the shared Python service, caller-side MCP/CLI and fake adapter for brief 18.
It sends only to a local fixture receiver. Mail, Chrome, Claude Code's sandbox and
image integration belong to later briefs. Packaging and managed settings are drafts,
not a deployment or a claim that a Claude session is confined.

The current Fedora container is **Fedora 45 x86_64**, pinned by manifest digest in
the workflow; CI tested **Python 3.15.0** and prints its version. The lock supports CPython
3.14 and 3.15. The only direct third-party runtime dependency is the official
**MCP Python SDK 2.3.0**. All its transitive dependencies are pinned with wheel
hashes. The service, CLI, filesystem policy, journal and hooks use the standard
library. The SDK and its dependencies are used by the MCP proxy and its test client.

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
local timezone. Returned app text is marked `untrusted_content`; descriptions
instruct the caller to treat it as data.

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
returns `approval`, the exact input for send/delete. It includes the operation id,
account, complete recipients (including Bcc), all caller-written text, immutable
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
first stages its complete event in SQLite and commits, then appends and fsyncs a
compact hash-chained record, applies the event and commits SQLite's head, and
finally appends/fsyncs a matching commit marker. Directory entries are fsynced
when created. App work begins only after this sequence completes. On a crash,
recovery finishes only that single staged transaction, never app work. Startup
turns every `submitting` operation into `unknown`. A database behind the independent
committed high-water mark is **locked**, and all app calls/transfers are refused.
A record with an uncommitted tail also locks if its full staged event is missing.

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

After an older backup is detected, only the owner can run:

```sh
sudo aresos admin control restore_confirm --input '{"confirm":"invalidate earlier approvals"}'
```

Confirmation writes a new generation. Missing/newer operations from the independent
record become `unknown`, retaining their short descriptions. Details absent from
the restored main log cannot be reconstructed from the separate record. Earlier-generation ids
can be read and locally repaired but never approved or submitted. Reserved operations
from the restored generation are invalidated. A repair is a new logged operation
pointing at the old one. A missing/corrupt independent record, a torn journal line or
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
file; the hostile-program confinement is brief 18b.

Installed entry points use a fixed `/usr/bin/python3 -I -S`, `/usr/bin/env -i`, a
fixed PATH/LANG, and root-owned code under `/usr/libexec/aresos-control`, vendor
dependencies under `/usr/lib/aresos-control/vendor` and config under
`/etc/aresos-control`. `-S` also blocks `.pth`/`sitecustomize` execution. The launcher
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
or `launch.py hook UserPromptSubmit`. A different `hook_event_name` is malformed.
No transcript, current directory or prompt path from hook input is opened. Input
is read in full, including long prompts and final assistant messages. `Stop` keeps
its explicit service-failure reminder and malformed-input stderr feedback with
exit 2. `UserPromptSubmit` exits 0 with no output on any failure, including unreadable
or malformed input, service failure, and installation/configuration errors, so
it never discards the owner's prompt. Valid prompt input still adds the pending
reminder. Hooks are reminders; service expiry is the safety net during interrupts,
continuation limits and ended turns.

Contract **read**: [Anthropic hooks reference](https://code.claude.com/docs/en/hooks),
2026-11-07. Target **Claude Code 2.1.319**, as recorded in the council branch's
`reviews/control-checks/2026-11-07-permission-prompt.md`. No Claude binary or model
is run by this package. MCP contract **read**:
[official SDK v2.3.0](https://github.com/modelcontextprotocol/python-sdk/tree/v2.3.0).

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
3. `prepare` must build the service's authoritative description and immutable
   payload. Keep all Claude-written content in the approval, and generated material
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
