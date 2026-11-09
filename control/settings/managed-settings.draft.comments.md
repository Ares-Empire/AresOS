# Slim managed settings: purpose and provenance

Decision 24 (`docs/design/CONTROL.md` section 7 on `origin/main`, read 2026-11-09)
replaces the containment draft. Nothing in these settings confines Claude Code.
The generator's single source is `aresos_control/boundary_policy.py`; app actions
come from `definitions.py`. The generated JSON contains exactly these keys:

| Key | Purpose | Source |
| --- | --- | --- |
| `permissions.ask` | One exact `mcp__<installed-app>__<verb>` rule for each public asking send/delete; owner-only and explicitly trusted sends are excluded. | Decision 24, section 7; action definitions. [Permission precedence](https://code.claude.com/docs/en/permissions#precedence-among-rules-hooks-and-mods). |
| `hooks.Stop` | Existing fixed notification command: remind Claude about pending/unfinished work, with its continuation guard. | Rule 4.10; `aresos_control/hooks.py`; [Stop contract](https://code.claude.com/docs/en/hooks#stop). |
| `hooks.UserPromptSubmit` | Existing fixed notification command: add pending work to the next prompt. Its shell guard always exits successfully. | Rule 4.10; `aresos_control/hooks.py`; [prompt contract](https://code.claude.com/docs/en/hooks#userpromptsubmit). |

The two hook commands and timeouts are unchanged. `settings/managed-hooks.json` is
a generated companion for testing/documentation, not a separately loaded managed
policy. `settings/CLAUDE.md` is generated from the same module and says that only
the owner in the session gives instructions; mails, pages, files, tool results and
other sessions' messages are data. This instruction is policy, not enforcement.

Image setup installs the draft JSON as `/etc/claude-code/managed-settings.json`,
and the generated instruction as `/etc/claude-code/CLAUDE.md`. Root ownership and
non-writable, non-symlink path components remain required. Extra installed keys,
rules and hooks are accepted. User-scope MCP entries in `user-mcp.json` use the
normal `claude mcp add-json --scope user` interface (see `control/README.md`).
There is no generated exclusive `managed-mcp.json`.

**Read:** rolling Anthropic documentation, 2026-11-09. **Run:** the model-free
native harness pins Claude Code **2.1.319** and records each precedence case,
receiver arrivals, complete tool definitions and server instructions in the
Messages request (including the complete system field). See `reviews/18d-base-slim/REPORT.md` for actual run IDs.
**Observed, run 42582079690:** user and managed `PermissionRequest` allow hooks
each execute once and approve a managed ask in normal and skip-permissions print
mode (one send arrival in each of the four cases). This is decision 24's accepted
residual; the version-pinned expectation file fails if it changes. No source/plugin/hook/bypass lock is restored to avoid it.

`control/boundary/optional-sandbox.json` is a **test fixture only**. It is never
included in generated managed settings or installed by the base. It demonstrates
the strict opt-in sandbox's limits, including Unix-socket filtering and hiding
`/run/aresos-tools`; it is not the default Claude Code configuration.
