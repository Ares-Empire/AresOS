# Native Claude Code checks and optional sandbox experiment

Everything here runs in disposable Linux containers on GitHub's Ubuntu 24.04
runners. Do not run the supervisor on an owner's machine: it creates synthetic
absolute paths and test users. Nothing here confines the owner's Claude Code.
There is no `aresos-assistant` launcher, coding user, exclusive MCP policy, source
walk, plugin restriction, or login restriction. Start `claude` normally.

`package-lock.json` pins native Claude Code **2.1.319**, published sandbox runtime
**0.0.81**, and transitive dependencies with integrity hashes; `pins.json` pins
the x64 seccomp helper. The image is x86-64 only. No model or real account runs.
`native.py` provides fixed streaming Messages responses from a loopback test
double. It records every request's complete `system`, tools and messages, plus
returned tool results. Root temporarily adds only synthetic loopback auth and,
for sandbox tests, the two exact fixed Bash grants. It restores settings on exit.
The production notification commands are installed with an empty-pending hook
stand-in in this container only; full hooks run in the base/Mail suites.

## Managed-ask precedence

`precedence.py` installs testapp and Mail fixtures using the real
`claude mcp add-json --scope user` command. The generated slim policy includes
testapp's asks because the service serves it; only its MCP entry is harness-only.
Claude runs with its normal user, project and local
settings sources; skip cases assert `system/init.permissionMode=bypassPermissions`.
The fixed Messages response calls both `mcp__testapp__list` and
`mcp__testapp__send`. The independent `stub.py` HTTP listener logs each actual
arrival by case and verb. An initial no-managed-ask send must arrive, proving the
send path works. Each managed-ask case must let list arrive and keep send away.
Tests cover user/project/local/all allow rules and a user PreToolUse allow hook,
in normal and skip modes. Hook markers prove the PreToolUse hook actually ran.
User and managed PermissionRequest hooks are configured in both modes; their
invocation counts and receiver arrivals are recorded and compared against a
version-pinned outcome file. **Observed on 2.1.319:** all four hooks run and approve
the send, each with exactly one receiver arrival. This is decision 24's accepted
residual, and the test fails if it changes. This is a print-mode result; terminal
and phone presentation remain separate image checks.

The Messages request must contain both app servers' entire instructions in the
request (2.1.319 places them in its environment message), plus each complete tool
description/input schema. Shared rules are
not repeated in descriptions; asking descriptions still say to copy the question
and approval unchanged. Any shortening fails the test and needs an explicit
fallback decision. `precedence-summary.json` and receiver `stub.txt` are retained.

## Strict optional sandbox fixture

`optional-sandbox.json` contains the previous explicit home/work filesystem masks
and strict sandbox controls as an **opt-in test fixture**, loaded as user settings.
It contains no source locks or managed-only switches. It forbids unsandboxed
fallback, has no excluded commands or permitted Unix sockets, and hides the
service's socket directory. Its deliberately read-only work tree and network
allowlist demonstrate stronger optional settings; they are never shipped defaults.
`configure.py` derives the standalone runtime's explicit network/filesystem subset
from that fixture. This is not Claude Code's private settings resolver.

`check.py` and `hostile.py` keep the prior native and standalone attack coverage:
Unix/abstract/VM sockets, direct/proxied network, credential reads, startup and
configuration writes/unlinks/replacements, symlink aliases and fresh directories.
Live positive controls precede attacks. Allowed-host mutation controls must expose
the identical harness's two open HTTP/CONNECT routes. Native and standalone runs
must preserve protected file hashes and produce zero hostile receiver arrivals.
Outside observation checks network/mount namespaces, dropped capabilities,
seccomp filter counts, complete canonical mount trees and effective path access.
The regression mutations for mount reparenting and covered writable mounts remain.

The helper-present and helper-absent runs remain distinct. Native 2.1.319 uses its
embedded multicall seccomp stage; planted external helpers must never run.
Standalone VSOCK without a helper remains explicitly unqualified (no live host
endpoint). Seccomp probes here measure the optional fixture, not a startup gate.
The other-user check runs in the **same container** against the live act.sock,
which the owner already reached. The base suite also checks real service kernel
peer credentials; no separate coding container or coding policy remains.

## Reproduce on a disposable Linux runner

```sh
docker build -f control/boundary/Dockerfile -t aresos-boundary .
mkdir -p evidence/present evidence/absent
for mode in present absent; do
  docker run --rm --network none --cap-add SYS_PTRACE \
    --security-opt seccomp=unconfined --security-opt apparmor=unconfined \
    --security-opt systempaths=unconfined \
    -e FILTER_MODE="$mode" -v "$PWD/evidence/$mode:/evidence" aresos-boundary
done
```

The workflow temporarily permits unprivileged namespaces on its disposable VM and
restores that policy in an `always()` step. Docker's outer seccomp/AppArmor/proc
masks are disabled so the inner sandbox can be measured; no host namespace, home,
device or Docker socket is shared. Only the root outside observer uses SYS_PTRACE;
attacks remain unprivileged with no effective capabilities. These are runner
prerequisites, never instructions to change the Mac or AresOS image.

Artifacts include exact commands, exit codes, stdout/stderr, receiver logs,
request/response captures, settings snapshots, mount observations, hashes and
named precedence results. `.github/workflows/control-boundary.yml` runs once per
matching PR push or manual dispatch; rerun the same run to verify twice on one
head. See `reviews/18d-base-slim/REPORT.md` for executed results and limitations.
