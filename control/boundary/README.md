# Linux control boundary experiment

Everything here runs in disposable Linux containers on GitHub's Ubuntu 24.04
runners. Do not run the supervisor or installer scripts on an owner's machine.
They create synthetic files at absolute fixture paths inside the container.
The Mac is used only to edit, inspect documentation, and submit CI runs.

`package-lock.json` pins Claude Code **2.1.319**, the published
`@anthropic-ai/sandbox-runtime` **0.0.81**, and their transitive npm dependencies
with integrity hashes. `pins.json` additionally pins the x64 seccomp helper.
The Docker image is x86-64 only. No model, authentication or real account is used.

## Reproduction and its limits

[Anthropic's sandbox documentation](https://code.claude.com/docs/en/sandboxing)
identifies its open-source runtime and Linux bubblewrap/seccomp implementation.
No documented model-free Claude Code command runs one sandboxed Bash command.
The native CLI does not publish its embedded runtime's exact revision. We test
the independently published runtime above through its public `SandboxManager`
API; we do **not** assert its version matches the native CLI's embedded copy.

`configure.py` translates the draft's explicit network and filesystem lists,
expands `~/` for the fixed assistant home, and disables weaker/nested user
namespaces. It does not reproduce Claude Code's private settings resolver,
automatic Read/Edit permission projection, worktree discovery, implicit temp
directories or dynamic policy updates. Read/Edit restrictions are already covered
by the stronger explicit home/work masks in this draft. We prepare `/tmp/claude`
as the assistant's private scratch directory, which Claude normally provides.
An end-to-end model test in the image must compare `/sandbox` Config with this
reproduction before the design is qualified.

Linux write-deny rules cannot exclude recursive patterns like `**/.envrc`.
Consequently, this conservative draft makes the terminal's entire home work tree
read-only, while file tools can write ordinary files there under permission rules.
`configure.py` also creates harmless built-in deny placeholders: SRT 0.0.81 and
bubblewrap 0.8 otherwise attempt to create missing mount destinations after making
the re-exposed work tree read-only. The launcher's effective canary rejects a
broken mount setup. Do not remove the work-tree denial to work around that error.

## Run on a disposable Linux runner

```bash
docker build -f control/boundary/Dockerfile -t aresos-boundary .
mkdir -p evidence/present evidence/absent
for mode in present absent; do
  docker run --rm --network none \
    --security-opt seccomp=unconfined --security-opt apparmor=unconfined \
    --security-opt systempaths=unconfined \
    -e FILTER_MODE="$mode" -v "$PWD/evidence/$mode:/evidence" aresos-boundary
done
bash control/boundary/isolation.sh
```

Ubuntu's `kernel.apparmor_restrict_unprivileged_userns=1` can still transition an
unconfined process into a restrictive profile and prevent bubblewrap configuring
its private loopback device. The workflow records the initial value, temporarily
sets it to 0 on its disposable VM, and restores it in an `always()` step. Docker's
seccomp/AppArmor/proc masks are disabled for the test envelope so the **inner**
runtime can create full user, network, PID, mount and proc namespaces. The inner
sandbox and its optional filter are never weakened; we add no host namespace,
host home, host device, Docker socket or privileged-container access. These are
CI prerequisites, not proposed changes to the AresOS image or the Mac.

## Evidence

`check.py` runs the hostile programs as uid 10001. `stub.py` binds the three
service paths, desktop/session sockets and an abstract socket, plus a loopback
HTTP receiver. It drops to uid 10002 after binding; service state/password files
are uid 10002, mode 0600 inside a mode 0700 directory. Socket permissions are
tools:assistant 0660 for act/chrome and root:root 0600 for admin, inside
tools:assistant 0750 `/run/aresos-tools`. Chrome is a same-user stub, not a native
host authorization implementation (brief 18 owns the real service).

Positive controls prove each listener is alive (root alone connects to admin),
owner secrets are readable outside the sandbox, and startup files are writable.
The sandbox must finish the exact fixed attack count, read a work file and write
scratch space. The supervisor checks every attack result, listener liveness,
zero new arrivals and unchanged SHA-256 hashes. New files, replacement, deletion,
fresh subdirectories and a symlink socket alias are tested too. AF_VSOCK's denial
without a filter can be host unavailability, not policy; the launcher refuses
the unfiltered session regardless. `/dev/uinput` is a synthetic regular file,
hidden by bubblewrap's private `/dev`; no actual input event is generated.

Each mode uses a fresh container. In `absent`, **both architecture helpers are
actually removed**, rather than flipping `allowAllUnixSockets` or faking failure.
The runtime's dependency warning and emitted bwrap command are saved. Missing
helper must not stop the fixed programs from running: this characterizes the
fallback, then separately requires the launcher to refuse it.

`launcher.c` is statically linked, root-owned and never setuid. It preserves the
assistant uid, closes inherited fds >=3, supplies a fixed environment and invokes
isolated Python. `launch.py` checks trusted paths, the helper hash, absence of
installed plugins, and effective EPERM on AF_UNIX and AF_VSOCK through the real
runtime before `execve` of the fixed CLI with `--setting-sources ''`. It accepts
no CLI options or configurable paths. Tests temporarily replace only the
root-owned CLI target with an environment recorder, then restore it. Real
LD_PRELOAD, Node require and Python sitecustomize fixtures prove code would load
without sanitization and remains unexecuted through the launcher. Missing and
corrupt helpers, pre-existing plugins and injected launcher flags must refuse.
No real Claude model session is claimed by these recorder tests.

`settings_checks` tests user/project MCP suppression, blocked additions,
marketplace policy and sideload flags with the actual native CLI, without login.
The key-by-key [comment file](../settings/managed-settings.draft.comments.md)
separates those results from documented behavior and later model tests.

`isolation.sh` starts two containers with distinct root filesystems, homes, users,
PID/network namespaces and `/etc/claude-code` policy. The coding container has no
bind mounts of assistant state or sockets. It proves an intentionally separated
container setup, **not** toolbox/distrobox defaults, which commonly integrate the
host home and desktop. Do not add those integration mounts to this design.

Artifacts contain command outputs, individual hostile results, the stub log,
launcher and settings logs, namespace-policy before value and run/head identity.
`BOUNDARY_OK`, `LAUNCHER_OK`, `SETTINGS_OK` and `ISOLATION_OK` are asserted results.
The workflow has a 30-minute job limit and runs on filtered pushes and PRs.
