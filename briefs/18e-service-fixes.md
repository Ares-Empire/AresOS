# 18e: Control service fixes from 18c's VM runs

**Goal:** fix what brief 18c's Control VM runs found in the service, its unit and its messages, and build the owner's
answer #254 ("Quiet unless used") into the hooks. Small changes in `control/`; nothing under `os/`.

**Why now:** the image part of 18c (draft PR #58) is green and goes to review on 2026-11-17. These fixes ride into
the same release; 18c's VM pass then proves them under the real systemd (the lead coordinates that, see "Proof").

**Model:** a Claude agent on Opus 5.5. Each item is specified here, including the one new mechanism (item 6), and
the work is close to the existing code. The lead moves it to Fable 5.2 if a round resists.

## Read first

- `control/README.md` ("Hooks", the service), `control/aresos_control/daemon.py` (`serve`), `protocol.py`
  (`Client.connection`, the transport errors), `cli.py` (the `admin` path), `files.py` (`FilePolicy.locate`),
  `hooks.py`, `proxy.py`, `control/packaging/aresos-toold.service` and its pin test `control/tests/test_unit.py`.
- `reviews/18c-image-test/PROGRESS.md` on branch `pkg/18c-image` (read-only: `git show origin/pkg/18c-image:...`):
  "Findings for the lead" of steps 2a, 2b and 2c, and "Check 6 in numbers". The run ids below are from there.
- `briefs/18c-image-test.md`, agreed change 6 (why the unit stays `Type=simple`).

## The fixes

1. **The start-up gap says what it is (18c step 2a).** The unit is `Type=simple`, so it is "active" a moment before
   its sockets exist, and an early call gets "Service connection lost; inspect operation_status with the same id",
   which is wrong: nothing was sent. The unit **stays `Type=simple`** (18c's agreed change 6: a slow or failing start
   must never hold `multi-user.target`; `Type=notify` would). Instead, in the client (`protocol.py`):
   - A failure to **connect** (`ENOENT`, `ECONNREFUSED`; before any byte of the request is sent) is retried for up
     to 3 seconds in short steps. That is safe because nothing was sent.
   - If it still fails, the error says so: the AresOS tool service is not running, nothing was sent, try again later.
     It never suggests `operation_status` (there is no operation). Keep a stable error code that callers and the
     hooks can tell apart from a lost connection (the builder picks the name; say it in the report).
   - A connection lost **after** the request was sent keeps today's handling (`UnknownRequest`, the same-id advice).
   - Applies to every caller of the client: MCP proxies, the CLI, the hooks.
2. **`aresos admin` without sudo (18c step 2a).** Run as the owner, `aresos admin …` fails with a transport error.
   It must say plainly that admin commands need sudo (`sudo aresos admin …`), without touching the admin socket
   and without prompting for any password first.
3. **Idle wake-ups (18c change 14: about 10 wake-ups per second idle; run 43577034725: 10.3/s, 0.75 % of a CPU).**
   `serve` selects with a fixed 0.1 s timeout and runs `expire` and `poll_confirmation` on every pass. Compute the
   timeout from the next real deadline instead: the engine's next expiry, the Chrome maintenance time, and a short
   poll only while a loosening confirmation is actually waiting. Add a small engine method for "next deadline" if
   none exists; don't just lengthen the sleep. Targets: idle with nothing pending, at most one wake-up per second;
   every deadline still met within the precision its tests require today; the Chrome latency gate
   (`control/chrome/ci/latency-targets.json`, same ceilings and sample counts) and the 525 ms hold window unchanged.
4. **A broken service ends `failed` (18c step 2b).** With `ExecStartPre=/usr/bin/false` the unit restarted 41 times
   in 90 s and never reached `failed`: `RestartSec=2` keeps it under systemd's default start limit. Add
   `StartLimitIntervalSec` and `StartLimitBurst` to `[Unit]` so a service failing at every start ends `failed`
   within about 15 seconds, while a single crash of a running service still restarts. Pin both in `test_unit.py`.
   Nothing else in the unit changes (the image check pins the file; 18c updates its pin when it merges main).
5. **The outside-folder refusal names the configured folders (18c step 2b, run 43568250360).** `files.py` says
   "choose Documents, Downloads, Desktop or an owner-configured folder", but the image configures `Downloads` and
   `Documents` only. Build the message from the policy's own folders (shown relative to the home, e.g.
   `~/Downloads`), in a stable order.
6. **"Quiet unless used" (owner, #254, 2026-11-14).** While the service is down, a Claude Code session that never
   used the AresOS tools shows nothing; a session that did gets one clear notice. Today every turn of every session
   ends with a four-line "Stop hook error … Service connection lost …" and one extra model reply (18c check 6).
   - **Used** means: in this Claude Code session, a tool result from the service named an operation (an
     `operation_id`, an approval or a reserved request). Plain reads don't count.
   - **Marking:** the MCP proxy (`proxy.py`; one per session, running as the owner) marks the session before it
     returns such a result. The mark is an empty file `/run/user/<uid>/aresos-control/used/<pid>-<start>`, where
     `<pid>` is the proxy's parent process (the Claude Code process) and `<start>` that process's start time (field
     22 of `/proc/<pid>/stat`), so a reused PID never inherits a mark. The folder is created 0700, the file 0600,
     without following links. `/run/user/<uid>` is the owner's tmpfs: marks vanish at logout. Use the uid, not
     `XDG_RUNTIME_DIR`: the managed commands run under `env -i`.
   - **Reading:** the Stop hook, when the service can't be reached (item 1's code or a lost connection), looks for a
     mark of any of its ancestors (walk `/proc/<pid>/stat` up to four levels, stop at PID 1). A mark: block once with
     a notice like "AresOS tools are not running. If you prepared or sent something with them in this session, its
     outcome is unknown: tell the owner, and don't repeat it." No mark: no output, exit 0. If the marks can't be
     read (any error), behave as if marked. `stop_hook_active` keeps its guard. `UserPromptSubmit` stays as today
     (silent on failure).
   - **Before building it**, confirm on Claude Code 2.1.319 that the MCP server's parent and one of the hook's
     ancestors are the same Claude Code process (record both process chains). Where to look: B1's interactive suite
     in `control/boundary/` runs real interactive sessions in the container. If they aren't the same process, stop
     and report (PLAN-GAP) with what you found instead.
   - With the service **up**, nothing changes: the hooks report held or unfinished work as today.

## Proof

- Unit tests for each item, failing on today's code: the connect retry and its message (a socket path that appears
  after a delay; one that never appears; a connection dropped after sending keeps `UnknownRequest`), the admin hint,
  the deadline computation (idle, pending expiry, waiting confirmation), the unit's start limit, the refusal text,
  and item 6 with fake `/proc` trees and marks (marked, unmarked, unreadable, a reused PID with another start time,
  a link where the folder should be).
- The idle loop: measure context switches over 60 s with the service idle in the CI container, before and after
  (18c change 14 measured the same way in the VM; the 18c PROGRESS.md says how).
- Existing suites stay green on their CI (base, boundary, Mail, Chrome including the latency gate). Interactive
  container case for item 6 if the suite can run the real managed hooks; if it can't (B1 used a stand-in), say so.
- **Under systemd:** not in this package. After it merges, 18c's next VM pass takes it in: check 6 then expects no
  notice in a session that never used the tools, one notice in a session that did, the failed state reached without
  the CI drop-in's `Restart=no`, no transport error right after `systemctl start`, and the idle wake-ups. Write what
  those assertions should be into your report so the lead can hand them on.

## Done

All six items with their tests; `control/README.md` and `KNOWN-LIMITS.md` (if a limit changes) say what the code
does; the report (in `reviews/18e-service-fixes/PROGRESS.md`, since a Claude builder can't create `REPORT.md`) with
**read/run/verified** evidence, the process chains of item 6, the idle numbers, JUDGMENT-CALLs and PLAN-GAPs; a pull
request against `main`. Stop there.

## Rules

`AGENTS.md` applies. You are on the owner's laptop: no containers, VMs or root locally, quick unit tests only;
containers and suites run on GitHub. Branch `pkg/18e-service-fixes` in `~/AresOS-18e`. Commit in small steps with a
model trailer, push, open the PR, never merge, never push to `main`, never force-push, never `--no-verify`. No
personal data, real addresses or provider names. Watch runs with `gh run watch <id> --exit-status --interval 120` or
longer, in the background. Work in steps of about 250k tokens: keep PROGRESS.md current (done, left in order, what
the code doesn't show) so a fresh agent can take over.

**Stop and report** if a fix needs a change under `os/`, a change to the unit beyond item 4, or a new dependency;
if item 6's process chains don't match; or if the latency gate moves.
