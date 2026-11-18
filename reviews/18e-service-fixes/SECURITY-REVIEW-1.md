# 18e security review 1

Reviewer: fresh Claude security reviewer (not the builder), Opus 5.5, 2026-11-16. Head `13e9e1e4`, range
`c746075d...HEAD`. Ran on the laptop: `PYTHONPATH=control:control/tests python3 -m unittest
control.tests.test_service_fixes` (34 OK; the MCP stdio case errors only because the SDK isn't installed here),
`control.tests.test_unit`, `control.tests.test_review22_protocol` (8 OK), `control.tests.test_files` (11 OK; one failure
needs `/etc/claude-code`, environment), `control/boundary` `test_interactive.ProcessChains` (3 OK). Throwaway checks
of my own in a scratch folder: `usage` against a fake `/proc` tree with nested sessions and planted FIFOs; the client
against a listener whose backlog is full; `Proxy.call('file_save')` with the service gone before the `saved` report.

## What was checked

- **Connect retry** (`control/aresos_control/protocol.py:68-121`). Only `connect()` is retried, and only on
  `ENOENT`/`ECONNREFUSED`. Each try uses a fresh socket, and the request is sent once, after a connect has succeeded.
  So a retry can't deliver a request twice. A connection lost after connecting still gives `UnknownRequest` or
  `transport_error`. A full backlog (`EAGAIN`) isn't retried: it says "could not be reached … nothing was sent",
  which is true. Another listener can't appear at the path: `/run/aresos-tools` is 0711 and belongs to the service
  user (`control/packaging/aresos-tools.tmpfiles`), and the daemon refuses an unexpected entry at a socket path. The
  owner's user can't create anything there, during a restart or at any other time. The `mail_account_add` password
  doesn't appear in any new error text.
- **Proxy catalogue without the service** (`control/aresos_control/proxy.py:22-34`). The fallback is
  `tools_for(app)`, the same function the service answers `tools` with (`engine.py:775-779`). The owner-only filter
  runs on it as it does on a served catalogue. `Proxy.call` and the service's `dispatch` (`engine.py:535`) still
  refuse owner-only actions on `act.sock`, and the managed ask rules are keyed on tool names, not on the catalogue.
  The fallback doesn't widen anything.
- **Usage marks** (`control/aresos_control/usage.py`). Every step goes through a dir fd. Each folder is opened with
  `O_NOFOLLOW|O_DIRECTORY`, so a FIFO or link in place of a folder fails fast (checked). `/run/user/<uid>` must be
  owned by uid, and the two folders must be owned by uid with no group or other bits. Files are created 0600 with
  `O_NOFOLLOW`, and `unlink` uses the dir fd. The walk starts at the hook's parent, covers four levels, stops at
  PID ≤ 1, and keys marks by pid and start time. Another local user can't read, plant or remove a mark:
  `/run/user/<uid>` is the owner's private tmpfs. The owner's own processes can, which is the accepted level of
  CONTROL.md section 7: they could also call the service directly. A planted mark only adds or removes an
  informational notice, which appears only while the service can't be reached. Hostile content can only add a mark,
  never suppress one: `names_operation` looks at result keys.
- **Admin refusal** (`control/aresos_control/cli.py:36-43`). Before it run only `launch.py`'s root-owned checks and
  config read, the help text, `--help` and argparse. Nothing touches a socket or calls `getpass` first, also for
  `mail account add`. The echoed words go out through `display_json` (`ensure_ascii`), so no terminal escapes get
  through.
- **Stop notice** (`control/aresos_control/hooks.py:21-24, 61-66`). The text is a constant, with no service, mail or
  page text in it. It says "don't repeat it", and `stop_hook_active` still guards it before anything is recorded. It
  can't be turned into an instruction to repeat an action. The `service_unavailable` tool result for a send ("nothing
  was sent. Try again later.") is accurate. A retry asks the owner again, and the operation record runs an id once.
- **Idle loop** (`daemon.py`, `engine.py:224-235`). Approval deadlines are checked at submission (`engine.py:313,
  338`; `chrome/adapter.py:239`), not only by `expire()`. A waiting Chrome confirmation is still polled every 0.1 s,
  and SIGTERM wakes the sleep through the pipe. The start limit fails closed: no action can run while the service is
  `failed`.

## Findings

No **fix** findings.

**Known limits** (low harm; worth a line in the design's limits list, each with a small optional fix):

1. **A nested Claude Code session takes its parent's notice.** `control/aresos_control/usage.py:106-117` (`_session`,
   `LEVELS`).
   - Steps:
     1. Session A uses Mail, so A's process is marked.
     2. A runs `claude -p …` through its Bash tool.
     3. The service goes down.
     4. Session B's Stop hook walks sh → claude B → (bash) → claude A and finds A's mark at level 3 or 4.
     5. B, which never used the tools, gets the notice and writes A's `.told` file.
     6. A's own next stop stays quiet for the whole outage.
   - Checked with a fake `/proc` tree: B's notice is True, then A's is False. The same happens on a scale of one
     process: after `/clear` the new conversation inherits the old one's mark.
   - Harm: one wrong notice in B and a missed one in A. Nothing runs, and the tool results themselves said
     `service_unavailable`.
   - Fix: check only the hook's nearest ancestor that isn't `sh`, `bash`, `dash` or `env`, which is the Claude Code
     process the boundary suite pins, instead of the nearest marked one of four.
2. **A FIFO at a mark or `.told` name blocks.** `control/aresos_control/usage.py:90-92`: `_create` opens
   `O_WRONLY|O_CREAT` without `O_NONBLOCK`.
   - Steps:
     1. A process of the owner runs `mkfifo …/used/<claude pid>-<start>` (or `<…>.told`).
     2. `mark()` blocks. It runs on the MCP proxy's event loop (`proxy.py:227` → `197`), so the whole server stops
        answering, and the tool result (with its operation id) never reaches the session.
     3. `notice()` blocks the Stop hook until its 15 s timeout.
   - Both checked: neither returned within 3 s.
   - This needs a process running as the owner, which is the accepted level, and the operation record still prevents
     a second run.
   - Fix: add `os.O_NONBLOCK` to `_create`, since a FIFO with no reader then fails with `ENXIO`. Optionally, move the
     `names_operation` call inside `note_use`'s `try` (`proxy.py:195`), so nothing in marking can drop a result.
3. **A busy service reads as "not running".** `control/aresos_control/hooks.py:22-24, 61`.
   - Steps:
     1. While the single-threaded service works on a long request (an archive, a slow SMTP server), a hook's connect
        gets `EAGAIN` on a full backlog (checked: `service_unavailable`, "could not be reached (Resource temporarily
        unavailable)"), or its 10 s read times out (`transport_error`).
     2. A marked session hears "AresOS tools are not running", and its once-per-outage notice is used up.
   - Harm: a wrong word in a notice whose advice (tell the owner, don't repeat) is still safe.
   - Fix: word the notice "AresOS tools could not be reached".
4. **A saved file reported as "nothing was sent".** `control/aresos_control/proxy.py:65` and `117`, caught at
   `126-128`.
   - Steps:
     1. `file_save` or `mail_attachment_save` writes the file.
     2. The service stops before the `saved` report.
     3. After 3 s the call answers "The AresOS tool service is not running; nothing was sent. Try again later.", though
        the file is on disk (checked with a stubbed client).
     4. A retry with the same name is refused (never overwrites). A new name gives a second copy, and the export
        hold waits for its expiry.
   - Fix: catch `ServiceUnavailable` around the `saved` report and return the saved path with a note, as the
     `unknown` branch beside it does.

**Hardening note (no finding):** `daemon.py:155-159`. If expiring an overdue reservation kept failing with an error
that is neither a storage refusal nor the journal fence, `timeout()` would return 0 and the loop would spin. Before
this change it slept 0.1 s. I found no such error path, and a small floor for a passed deadline (e.g. 0.05 s) would
cap it.

SAFE
