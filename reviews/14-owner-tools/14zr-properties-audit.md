# 14zr property and journal audit

Requested audit source: systemd258 at `781d9d0789379d1ea1f2ecefb804d41e9c8b6c38`. The actual pinned ISO is
systemd259.9-1.fc44 at `63c0371fa71ae32ba02f05f90658bc40aaa19168`, as established by the retained RPM database.
Both exact versions are archived and hash-bound in
[index.json](../../os/manifest/ci/14/14zr-property-sources/index.json).
No image pin or image file changes. Source fixtures are formatter-derived
with modelled session values, not invented successful VM observations.

| Tool / uses | Verified grammar | Result |
|---|---|---|
| loginctl, owner session identity/facts/start time; harness switch tty checks | [Each `-p` / `--property` extends the literal selector list](https://github.com/systemd/systemd/blob/781d9d0789379d1ea1f2ecefb804d41e9c8b6c38/src/login/loginctl.c#L1572); [exact key filter](https://github.com/systemd/systemd/blob/781d9d0789379d1ea1f2ecefb804d41e9c8b6c38/src/shared/bus-print-properties.c#L371) | Owner uses one option per key for all3 queries. Harness already uses repeated `-p` options or a single property. Comma queries produce empty output in regression fixtures. |
| systemctl, owner paused/deferred states; both stock scripts; activation audit/canaries; overlay; stock hardware setup | [Explicit comma tokenization](https://github.com/systemd/systemd/blob/781d9d0789379d1ea1f2ecefb804d41e9c8b6c38/src/systemctl/systemctl.c#L580) | All comma lists are valid. Single-property `--value`, repeated `-p`, and activation audit's generated comma list are valid; no changes. |
| busctl, owner keyboard plus keyboard/installer/harness observations | [get-property takes positional property arguments and dumps typed values](https://github.com/systemd/systemd/blob/781d9d0789379d1ea1f2ecefb804d41e9c8b6c38/src/busctl/busctl.c#L1896) | No selector option. Retained `s "de"`, `as 1 "de"` and JSON `a{sv}` variant fixtures cover actual consumers. GetAll is a method call with a string interface argument; no comma splitting assumption. |
| localectl, owner set_keyboard and keyboard VM | [set-keymap / set-x11-keymap positional argument counts](https://github.com/systemd/systemd/blob/781d9d0789379d1ea1f2ecefb804d41e9c8b6c38/src/locale/localectl.c#L514) | No property selector option. Empty toggle/model/variant/options are kept as separate arguments. No change. |
| systemd-run, overlay's transient journal watcher | [One property assignment per option](https://github.com/systemd/systemd/blob/781d9d0789379d1ea1f2ecefb804d41e9c8b6c38/src/run/run.c#L501), [forwarded to assignment parser](https://github.com/systemd/systemd/blob/781d9d0789379d1ea1f2ecefb804d41e9c8b6c38/src/run/run.c#L1234) | Repeated NAME=VALUE options are assignments, not show filters. No comma-list selector assumption. |
| rpm-ostree cleanup `-p`; blkid `-p` | Non-systemd switches: pending cleanup and low-level probe respectively | Existing pinned ostree/util-linux audit applies; no property-selection interpretation. |

Key=Value parsing is independent of output order. All requested names must
appear once, with no duplicate, missing, extra, blank or malformed row.
All prior identity, loginuid, physical tty / relay, audit id, session start,
boot id and logind fact comparisons remain mandatory. Real [session D-Bus
properties](https://github.com/systemd/systemd/blob/781d9d0789379d1ea1f2ecefb804d41e9c8b6c38/src/login/logind-session-dbus.c#L981) and
[string/boolean/u64 formatting](https://github.com/systemd/systemd/blob/781d9d0789379d1ea1f2ecefb804d41e9c8b6c38/src/shared/bus-print-properties.c#L19)
give `User=1000`, `Remote=no`, and decimal `TimestampMonotonic=123456789`;
they are not a JSON response or an option-order list. Fixture order follows
the source session property table. The older tests now implement literal
selection rather than returning made-up values for comma-joined names.

## Scoped private journal diagnostics

The owner has no dedicated service unit: its own command result and trace are
already saved by the owner recorder. `logs` now reads only the previous boot's
logind unit, at most200 records, with JSON output. The full-boot read is removed.
This retains power/login diagnostics and the explicit physical-laptop gate.

[The exact unit matcher](https://github.com/systemd/systemd/blob/781d9d0789379d1ea1f2ecefb804d41e9c8b6c38/src/shared/logs-show.c#L1708) admits the unit's
`_SYSTEMD_UNIT`, PID1's `UNIT`, or root daemons' `OBJECT_SYSTEMD_UNIT`, with
optional service coredump matches. None admits unrelated kernel transport
messages: boot certificate messages have none of those unit associations.
The259.9 implementation is also archived and reviewed. Therefore the
conditional decoded-kernel exception is not needed for this bounded query.
The artifact classifier, rules, ignores and workflow are unchanged. A kernel
MESSAGE embedded in journal JSON remains a STOP; a JSON wrapper cannot become
an allowed whole boot-console line by decoding or stripping it. Regressions
cover that refusal for kernel, journal and stdout transports. Q13's four old
escaped plain-journal findings stay unclassified in historical evidence.

## Exhaustive current option inventory

[option-inventory.json](../../os/manifest/ci/14/14zr-property-sources/option-inventory.json)
records every `--property` and standalone `-p` in payload source, release and
CI Python/shell files, excluding only generated copies (bundle equality proves
those exact). These are the audited locations:

- `os/owner-tools/owner.py:53`: `*['--property=' + name for name in names])`
- `os/owner-tools/owner.py:343`: `'--property=LoadState,ActiveState,SubState').splitlines() if '=' in line)`
- `os/owner-tools/owner.py:354`: `'systemctl', '--user', 'show', name, '--property=LoadState,ActiveState').splitlines() if '=' in line)`
- `os/owner-tools/owner.py:366`: `'--property=LoadState,ActiveState,SubState,Result,ConditionResult,ExecMainStatus')),`
- `os/release/pause-stock-updates.sh:38`: `[*command, 'show', name, '--property=LoadState,ActiveState,SubState']).splitlines() if '=' in line)`
- `os/release/pin-stock.sh:38`: `[*command, 'show', name, '--property=LoadState,ActiveState,SubState']).splitlines() if '=' in line)`
- `os/release/pin-stock.sh:233`: `subprocess.run(['rpm-ostree', 'cleanup', '-p'], check=True)`
- `os/ci/activation_audit.py:36`: `output = subprocess.check_output([*command, 'show', '--all', '--property=' + ','.join(PROPERTIES), '--', *batch], text=True)`
- `os/ci/activation_canaries.py:20`: `assert run('systemctl', 'show', static, '--property=UnitFileState', '--value') == 'static'`
- `os/ci/activation_canaries.py:21`: `assert run('systemctl', 'show', generated, '--property=UnitFileState', '--value') == 'generated'`
- `os/ci/activation_canaries.py:22`: `fragment = run('systemctl', 'show', generated, '--property=FragmentPath', '--value')`
- `os/ci/activation_canaries.py:35`: `timer=run('systemctl', 'show', timer, '--property=Triggers,UnitFileState,ActiveState'),`
- `os/ci/install-tools.sh:6`: `mkdir -p "$directory/lists/partial"`
- `os/ci/install-tools.sh:51`: `mkdir -p "$source_directory"`
- `os/ci/overlay/checks.py:46`: `getty = run('systemctl', 'show', 'getty@tty3.service', '-p', 'ActiveState', '-p', 'MainPID')`
- `os/ci/overlay/checks.py:72`: `'--property=DefaultDependencies=no', '--property=IgnoreOnIsolate=yes',`
- `os/ci/overlay/checks.py:73`: `'--property=Type=exec', '--property=StandardOutput=tty',`
- `os/ci/overlay/checks.py:74`: `'--property=TTYPath=/dev/ttyS0', '/usr/bin/journalctl',`
- `os/ci/overlay/updater_regressions.py:15`: `assert run('systemctl', 'show', static, '--property=UnitFileState', '--value') == 'static'`
- `os/ci/overlay/updater_regressions.py:16`: `assert run('systemctl', 'show', generated, '--property=UnitFileState', '--value') == 'generated'`
- `os/ci/overlay/updater_regressions.py:17`: `fragment = run('systemctl', 'show', generated, '--property=FragmentPath', '--value')`
- `os/ci/owner_devices.py:66`: `# The live query selects -o value. Accept the complete real -p output too,`
- `os/ci/owner_devices.py:219`: `blkid=['blkid','-p','-s','PART_ENTRY_UUID','-o','value',target+'p1']`
- `os/ci/owner_vm.py:662`: `mkdir -p /run/owner-probe-stick`
- `os/ci/parser-preflight.sh:24`: `if sudo podman exec "$container" systemctl show basic.target --property=ActiveState --value | grep -qx active; then`
- `os/ci/parser-preflight.sh:29`: `test "$(sudo podman exec "$container" systemctl show basic.target --property=ActiveState --value)" = active`
- `os/ci/publish.sh:20`: `mkdir -p .work`
- `os/ci/stock_probe.py:32`: `mkdir -p "$probe/grub2"`
- `os/ci/switch_vm.py:265`: `self.send("sudo -k; sudo -p 'ARESOS_SUDO_PASSWORD:' -v\n")`
- `os/ci/switch_vm.py:461`: `guest.command('stock-hardware-setup', 'set -e; systemctl is-active bazzite-hardware-setup.service; test "$(systemctl show bazzite-hardware-setup.service -p ExecMainStatus --value)" = 0; journalctl -b -u bazzite-hardware-setup.service --no-pager; rpm-ostree kargs')`
- `os/ci/switch_vm.py:505`: `if test "$(loginctl show-session "$session" -p TTY --value)" = tty3; then`
- `os/ci/switch_vm.py:506`: `loginctl show-session "$session" -p Name -p User -p TTY -p Type -p Active`
