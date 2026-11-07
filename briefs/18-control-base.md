# 18: Control layer base: operations, tools, proxy, fake app

**Goal:** build the shared base every AresOS app tool will stand on, and prove it end to end with a fake app, in
containers on GitHub's Linux runners. After this package, adding Mail or Chrome means writing an adapter: the
definitions, the operation log, the honest outcomes, the file transfer, the MCP proxy, the terminal command and the
hooks already exist and are tested.

## Background (read first)

The design is on the council branch; read it with `git show`:

- `git show origin/council/2026-11-07-control-layer:docs/design/CONTROL.md`: **sections 1 to 4 are this package's
  specification**; section 7 says what the base must make possible; section 8 the tests.
- `…:docs/control/PLAN.md` (order of work, who does what) and
  `…:reviews/councils/2026-11-07-control-layer/OWNER-SCOPE.md` (the owner's picture).
- `…:reviews/control-design/2026-11-07-REVIEW.md` and its re-checks (`…RECHECK*.md`): the design review; its
  findings on operations, files, truthful prompts and programs outside the sandbox are why the rules read as they do.
- `…:reviews/control-checks/2026-11-07-permission-prompt.md`: Claude Code's prompt shows a tool's whole input, also
  in skip-permissions mode.

In short: a tool service (`aresos-toold`) runs as its own system user and does the work for every app. Each action is
defined once with its *effect* (read, change, send, delete); from that one definition come the MCP tools Claude
calls, the `aresos` terminal command, a reference page and the list of actions that must ask. Send and delete ask the
owner through Claude Code's own permission prompt, so the prompt must show the truth, and every send or delete is
recorded as an operation before it acts.

## What to build

All product code under `control/`, Python 3 (the version in current Fedora; say which you tested), standard library
plus the official MCP Python SDK, pinned with hashes. No other runtime dependency without a reason in the report.

1. **Action definitions** (design section 3): name, app, effect, input and result JSON schemas, a description
   written for Claude (what it does, when to use it, what it returns, its effect, what to do on each error), and
   owner-only. Generated from them, committed, and checked for drift by a test: the MCP tool list per app, the
   terminal command's `--help`, `docs/control/TOOLS.md`, and the list of send and delete MCP tool names for the
   settings' ask list (`control/settings/ask-rules.json`).
2. **The service `aresos-toold`** (section 2): runs as system user `aresos-tools`; three Unix sockets under
   `/run/aresos-tools/` and no TCP: `act.sock` (the owner's user only, checked by peer credentials; refuses
   owner-only actions), `admin.sock` (root only; the owner reaches it with `sudo aresos admin …`), `chrome.sock`
   (a placeholder for the Chrome bridge: accepts nothing yet). A small, documented request/response protocol.
3. **The operation log** (rule 4.3): durable on disk (say how: for example SQLite with full sync), states
   `reserved → submitting → done | partial | failed | unknown`; operation ids issued by the service, carrying the
   log's generation and bound to the hash of the exact input (the same id and input returns the existing operation,
   the same id with other input is refused); stages recorded per recipient or target; cancelling and expiry only
   while `reserved`; after a restart nothing resumes and `submitting` becomes `unknown`. Beside the log, outside the
   files a backup would copy, a small append-only record of every operation id with its description and state
   changes. A restored older log is refused until the owner confirms with an owner-only command; then the generation
   moves on, ids of earlier generations are refused, and operations the separate record knows but the log doesn't
   are listed as `unknown` with their descriptions. Generic `<app>_operation_status` and a repair hook for adapters;
   an adapter hook for evidence on the far side (for Mail: a Message-ID derived from the operation id, looked for in
   Sent before submitting).
4. **Truthful asking input** (rule 4.1): helpers for adapters to build the service's own description of an
   operation, bind an approval to the state it describes (refuse on any difference at run time), show control and
   direction-changing characters escaped, and refuse an asking input larger than a set limit instead of cutting it.
5. **File transfer on the caller's side** (rule 4.4), in the MCP proxy, running as the owner: reading only from the
   allowed folders in its configuration, never from credential or configuration places (the list in rule 4.4, and
   every dotfile), opened component by component under the allowed folder without following symlinks, regular
   files only, with a size limit, the real path reported; bytes handed to the service, which keeps them as an
   unchangeable blob by sha256 and uses exactly those. Saving: only into allowed folders, safe file names, never
   overwriting, never into configuration or start-up places.
6. **The generic MCP proxy `aresos-mcp <app>`** (section 2): a stdio MCP server that fetches its app's tool list from
   the service and forwards calls over `act.sock`. It must load nothing from a writable place: started with a fixed
   interpreter in isolated mode (`python3 -I`), a fixed environment, its code under a root-owned prefix. Owner-only
   actions are never listed or forwarded.
7. **The terminal command `aresos`**, generated from the definitions, over `act.sock`; `aresos admin …` over
   `admin.sock`; `aresos log` (what was done today, from the operation log).
8. **The two hooks** (rule 4.10): a `Stop` hook that sends Claude back while something is held or unfinished, and a
   `UserPromptSubmit` hook that puts held or unfinished items in front of Claude with the owner's next message, both
   following Claude Code's documented hook input and output (cite the docs page and the Claude Code version). They
   ask the service over `act.sock` with a read action.
9. **A fake app `testapp`** that uses all of the above: read (list items), change (flag an item), send (a message with
   recipients and attachments to a fake receiver that records every arrival, and can be told to accept some
   recipients and refuse others, lose its answer, or fail at each later stage), delete (an exact set of items), and
   its operation status and repair.
10. **Packaging drafts** under `control/packaging/`: the systemd unit, tmpfiles and sysusers entries for the service.
    **Settings drafts** under `control/settings/`: `managed-mcp.json` for the proxy, and the ask list. Marked as
    drafts: the real values come with the owner (design section 7, owner decision 3). Nothing under `os/`.

## Tests (containers on GitHub's Linux runners, no model, no real account)

At least: peer credentials on each socket (the owner's user, another user, root); owner-only actions refused on
`act.sock`; idempotency and refused id reuse; a crash (kill -9) at every step of an operation never sends twice and
leaves the right state after restart; an older log refused, the owner's restore marking recent operations
`unknown`; cancelling and expiry only while `reserved`; partial acceptance gives `partial`; a repair never submits
again; file reading refuses symlinks, traversal, dotfiles and credential places, non-regular files, files over the
limit, and sends the hashed bytes even when the file is replaced afterwards; saving refuses collisions, traversal and
configuration places, also through hard links and when the source or destination is swapped during the transfer;
escaping and the size refusal; the restore path (an older log refused, the owner's confirmation, earlier-generation
ids refused, operations from the separate record listed `unknown`); the proxy loads none of a planted `sitecustomize.py`, `.pth`
file or `PYTHONPATH`; the generated files are in sync; the hooks' output matches Claude Code's documented format.

`.github/workflows/control-base.yml` runs them on pushes to this branch (path filter) and on its pull request.

## Out of scope

- The Mail and Chrome adapters (briefs 19 and 20), the sandbox boundary and hostile programs (brief 18b), anything
  under `os/`, `mod/`, `docs/INSTALL*`, `docs/EMERGENCY.md`, `STATE.md`, `HANDOFF.md`, and the design and plan files
  (proposals go in the report).
- Running Claude Code or any model in CI; real accounts; anything on this Mac outside this worktree.

## Acceptance

- Every rule of design sections 3 and 4 maps to code and a test; the report lists the mapping.
- The workflow passes twice on the final head.
- No secrets, real addresses or account names.

## Report (`reviews/18-control-base/REPORT.md`)

What was built; the rule-to-code-to-test mapping; how to add an adapter (a short guide written for the Mail and Chrome
builders); deviations from the design as **PLAN-GAP**s; **JUDGMENT-CALL**s; what isn't done and why. Mark claims
**run** (workflow run ID), **read** (source and version) or **assumed**.

## Already decided

Design draft 5 (sections 1 to 4) and the owner's decisions in `PLAN.md`. Unix sockets only; owner-only actions only
through `admin.sock`; nothing resumes by itself after a restart; nothing is retried by itself.

## If unsure

Take the option that keeps a send from happening twice or without its approval, and say so in the report.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; builds and tests run on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/18-control-base`. Commit in small steps, push this branch, open a draft
  PR against `main` with `gh pr create --draft`. Never merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- Keep it to about 20 workflow runs.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**Model:** `gpt-6.1-sol`, xhigh: a careful build with many tests; the frontier model reviews the design and the
final security, not the code.
