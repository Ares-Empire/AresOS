# Follow-up: qualify the updater activation-graph audit

**Residual from 03h, not a requirement for PR #3.** A later run needs its own
explicit CI budget. Do not start another image/VM run under the exhausted 03h
budget. The integrator-selected fallback is strict static/generated-unit inspection:
every suspicious unit needs a mask or a literal reviewed allowlist entry,
regardless of enablement state; both live managers must also have no unreviewed
suspicious unit active or running.

03h full attempt 2 reached the static normal-policy audit, which correctly
rejected a generated `cockpit-container.service` carrying a container auto-update
label. Its exact mask was added after that final attempt and passes checks-only
CI on `9b29c02`; it has not been rebuilt/booted. A separately authorized full
static verification run is still required for PR #3 acceptance. That outstanding
qualification is separate from the graph work deferred here.

## Problem and retained prototypes

Full 03h attempt 1, run [39742496374](https://github.com/carlsenares/AresOS/actions/runs/39742496374),
built the release/disk and reached labwc. The graph audit failed before canary
rejection because `/run/systemd/transient/dbus-:1.4-org.fedoraproject.SetroubleshootPrivileged@0.service`
disappeared between manager inventory and fragment reading. Silently ignoring
missing arbitrary files is not a justified fix.

- `os/ci/activation_audit.py` preserves the graph implementation; it is not
  installed in either release or VM images. Its existing parser/graph regression
  tests remain in `os/tests/test_audit.py` and still run.
- `os/ci/activation_canaries.py` preserves the original VM regression check.
  The unused `os/ci/overlay/routine.service` and `routine.timer` are its static
  updater/innocently named enabled-timer fixtures. They are not in the test layer.
  The generated-unit fixture remains covered by the current static audit.
- `os/ci/parser-preflight.sh` and `parser_preflight.py` preserve the deferred
  Fedora container probe. It mounts the graph prototype, not the production
  static audit, and is not invoked by either workflow mode. Attempt 1's actual
  configured-release probe passed (801 system / 270 user names). Earlier 03g
  release probes failed to start the user manager; service status/journal
  diagnostics were added in 03h. Any restored release probe stays diagnostic.

## Scope

1. Define an evidence-preserving strategy for disappearing transient units,
   effective commands, aliases, escaped names and fragment/drop-in paths. Distinguish
   normal lifecycle races from unreadable persistent unit data; fail closed on
   unexplained missing evidence. Reproduce the real failure with tests.
2. Qualify both actual Fedora system/user managers before VM integration. Keep
   exact command/stdout pairs, versions and failing-unit status/journal. A
   container must never replace the VM acceptance environment or block it merely
   because container user-manager startup differs from boot.
3. Restore graph traversal of `Triggers`, `Wants`, `Requires`, `Requisite`,
   `BindsTo`, `Upholds`, generated/transient units and loaded instances only after
   the above is reliable. Restore the innocently named timer activation canary
   and its dependency assertions; preserve the real generated-unit canary.
4. Require both fresh VM passes, canary rejection followed by normal-policy
   success, checksum-protected raw exports and release/test-layer isolation.

**Do not weaken:** the static strict rule, masks/allowlist, active/running updater
rejection, recovery, power/input checks, offline journal integrity/boot/logind
proof or its narrowed two-prerequisite contingency, both VM passes, exact pins,
release isolation, quota/runner-only/no-publication rules. No installer or
hardware work is authorized here.

**Acceptance:** a separately budgeted green full run with both fresh VMs, real
activation canary evidence, race regressions, retained raw diagnostics and report.
Do not describe the current static evidence as graph-audit qualification.

**Model:** gpt-6.1-sol, xhigh.
