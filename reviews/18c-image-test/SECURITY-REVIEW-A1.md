# 18c image part: security review A1

Reviewer: fresh security reviewer, not the builder (Claude agent) · Model: Claude Opus 5.5 · Date: 2026-11-16 ·
Head: `84f45c28` · Range: `13e9e1e4...HEAD` (PR #69 / 18e excluded; its code is read only where this PR installs it
into every session) · Ran, all local and unprivileged: `unittest` for `os/tests/test_control_image.py` (9 OK) and
`os/tests/test_control_vm.py` (24 OK), `control/tests` `test_reserved_words test_service_user test_unit` (6 OK);
`bash os/build.sh control-tree os control <scratch>` (74 files) and a read of the map it makes;
`systemd-analyze security --offline=yes` on the unit; the managed hooks (`aresos_control.hooks.main`) against a
stand-in `act.sock` (a reserved operation of another session, and a non-owner refusal); `systemd-tmpfiles --create
--root=<scratch>` with the folders file over a linked `Downloads`; a read-only look for UID/GID 250 in the target
laptop's passwd/group files; Claude Code's permissions and permission-modes pages (auto mode). No containers, VMs,
root or CI runs.

## What was checked, and holds

- **Install** (`os/build.sh:51-299`, `os/Containerfile`): every Control file is written fresh (`target()` refuses an
  existing path), root:root, files 0644/0755, folders 0755, no links in the trees; vendored paths reset to 0755/0644
  (pip's umask can't leave anything writable). `image-checks.sh` holds every recorded path and every parent to root,
  no group/world write, no link, recorded mode and SHA-256, and nothing unrecorded under the four Control folders;
  `check-image.sh` holds the record to the checkout's own `control-tree`. Wheels: pip with `--require-hashes
  --only-binary=:all:` under `env -i`/`-I`, then the report's set must equal `requirements.lock` and each wheel's hash
  one of its pins; checked-hash bytecode only. Self-checks run after the record, so a stray write by them shows up as
  "not recorded". Config in `/usr/share/aresos/control` follows the image, derived from `aresos.conf`.
- **Launch chain:** every command, hook and MCP entry is an absolute root-owned path under `env -i` and
  `python3 -I -S`; no cwd, user site, `.pth` or environment reaches it; `launch.py` re-checks its trees on every start.
  A non-owner can't start a fake service (`/run/aresos-tools` is 0711 `aresos-tools`; `Daemon` refuses the owner's
  UID) or impersonate a socket.
- **Service:** own user, no capabilities, `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`,
  `PrivateDevices`, `UMask=0077`, Unix sockets with peer-UID checks before any read (`daemon.py:127-130`). Check 8's
  password scan (one file, 0600 in 0700, not in the journal, home, `/tmp` or evidence) is sound.
- **`/etc/claude-code`:** only `permissions.ask` and two hooks; no allow rule, mode, env, `apiKeyHelper` or
  `managed-mcp.json`, so nothing weakens a session's own prompts. Hook failures don't block: `UserPromptSubmit` is
  swallowed, a launcher failure exits 1, an internal Stop failure blocks at most once per turn (`stop_hook_active`).
  A stale or edited `/etc` copy fails closed: the service refuses asking work (`boundary_not_installed`, check 4).
- **sysusers/tmpfiles:** sysusers runs before tmpfiles, the service after both; 250 is outside Fedora's static block,
  far from the dynamic frontier, and unused on the target laptop today; the state folders are plain `d` (re-owned
  each boot), his folders `:`-prefixed and created after the home's own tmpfiles line. tmpfiles does not follow a
  linked `Downloads` (ran: "already exists and is not a directory", target untouched). Rollback to release 27 leaves
  `/var/lib/aresos-tools` owned by an unused 250, root-only; its `/etc` has no ask rules but also no Control code, so
  the user-scope MCP entries can't start.
- **VM test:** the Control layer, CA, hosts line and Claude Code binary exist only in `localhost/aresos:control`
  (`.containerignore` keeps `ci/` out of releases; image-checks proves no fixture traces); the only unit change is a
  `/run` drop-in in check 6, removed again; no shipped code reads a test switch (the launcher clears the environment).

## Findings

### Fix

**F1. The managed hooks put one session's held work into every Claude Code session on the laptop.**
Where: `os/build.sh:99` installs the hooks for every session; `control/aresos_control/hooks.py:31-37` and `:51-57`
read the global `control_pending` and block any session's stop on it, with no usage check (the outage path at
`:61-66` has one); `engine.py:250` (an expired reservation stays pending with a notice until acknowledged);
`definitions.py:37-41` (`operation_status` returns the full approval).
Steps: (1) in session A Claude prepares a mail; the owner answers "No" (it stays `reserved`, then `failed` with a
notice). (2) Every other session of his (builders, reviewers, leads, headless runs) now gets the pending list on each
prompt and its Stop blocked once per turn: one extra model request per turn, per session, until some session
acknowledges it (ran: the stand-in socket gives `{"decision":"block",...}` to a session with no usage mark). (3) Each
of them is told "Resolve, cancel reserved work...": `mail_operation_cancel` and `mail_notice_ack` are free, so an
unrelated session can cancel his pending approval or acknowledge an outcome notice he never saw; and one with a shell
can read the approval with `operation_status` and run `aresos mail send` with it, no ask. That is decision 24's
residual, but here our own hook triggers it, not hostile content. Check 6 measured only "nothing pending" and
"service down", and the owner's yes (change 10) is asked with "an ordinary Claude Code turn costs nothing extra"
(`PROGRESS.md:710`), which this case contradicts; it also runs against his "quiet unless used" (#254).
Fix: give pending and notice reminders the same gate as outages (only a session with a usage mark), and replace
"Resolve" with "don't complete or resend it; tell the owner"; add a check-6 turn where another session holds a
reserved operation. The code is `hooks.py` (outside this PR's allowed paths), so the lead routes it; the minimum
before merge is that the owner's yes states this behavior and its cost.

### Known limits

- **K1. Auto mode is not tested.** Claude Code's built-in interactive mode is auto (`control/boundary/README.md:118`;
  `REPORT.md:84`), which is what his sessions use; B1 and B2 force `--permission-mode default` or skip-permissions.
  Anthropic documents that explicit ask rules force a prompt in every mode, including auto, so the harm is a
  regression only. Add one auto-mode case (no extra rule, answer "Yes"; and with a user `PermissionRequest` hook) to
  B1 before the release.
- **K2. A non-owner session gets a Stop block every turn.** `daemon.py:129` answers root or another user with
  `permission_denied`; `hooks.py:56` turns any not-ok answer into `service_unavailable`, so `output()` blocks (ran).
  Root sessions are rare here (Claude Code lives in his home). Fix later: treat `permission_denied` as quiet.
- **K3. The managed `CLAUDE.md` says other sessions' messages are never instructions** (`control/settings/CLAUDE.md:1`),
  in every session, including agents briefed and corrected by a lead session. Policy text only; name it in the
  owner's question (change 10 mentions only "two managed hooks"), or narrow it to app content.
- **K4. Unit hardening is partial** (offline exposure ~5.0; `control/packaging/aresos-toold.service:9-25`). The
  service parses untrusted mail and reaches any address, including localhost. Without capabilities most gaps are
  moot; worth adding in a follow-up, each with a VM pass: `RestrictNamespaces=yes`, `SystemCallFilter=@system-service`,
  `SystemCallArchitectures=native`, `LockPersonality`, `RestrictRealtime`, `RestrictSUIDSGID`, `ProtectKernelTunables`,
  `ProtectKernelModules`, `ProtectKernelLogs`, `ProtectControlGroups`, `ProtectClock`, `ProtectHostname`, `PrivateIPC`,
  `RemoveIPC`, `LimitCORE=0`. Not `ProtectProc=invisible` or `PrivateUsers` (peer start times and UIDs need them off).
- **K5. testapp ships** (`aresos_control/testapp.py`, `generated/testapp-*`, its two ask rules): served on
  `act.sock`, no network, a local SQLite receiver, `fixture_configure` admin-only. By design (the VM test uses it);
  low harm.
- **K6. The release job runs none of the Control checks:** `check-image.sh` is called only by `check-build.sh:54`.
  The next release package must run image-checks' Control section and the record-to-checkout check on the release
  image, beside extending `release_diff.py` (PLAN-GAP 2).
- **K7. The service is single-threaded** (`daemon.py:136`): while a long send runs, every session's hooks wait up to
  `READ_TIMEOUT` 10 s (`protocol.py:12`) per prompt and turn end, then go quiet. Bounded and rare.
- **K8. A taken 250 would quietly become another number** at the first boot of the update; only the rehearsal's
  `release_checks.py` sees it. Free on the laptop today.

CHANGES-NEEDED
