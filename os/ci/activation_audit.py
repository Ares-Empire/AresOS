#!/usr/bin/python3
"""Deferred 03f graph-audit prototype; not installed in the release/VM images.

See briefs/03-followup-activation-audit.md. Parser regressions remain runnable.
"""
import argparse
import json
import pathlib
import re
import shlex
import subprocess

PATTERN = re.compile(r"uupd|updat|upgrad|topgrade|bootc.*(fetch|apply)|flatpak|brew|rpm-ostreed-automatic|rebase", re.I)
MASKED = {"masked", "masked-runtime"}
DEPENDENCIES = ('Triggers', 'Wants', 'Requires', 'Requisite', 'BindsTo', 'Upholds')
PROPERTIES = ('Id', 'Names', 'LoadState', 'UnitFileState', 'ActiveState', 'FragmentPath', 'DropInPaths',
              *DEPENDENCIES, 'ExecStart', 'ExecStartPre', 'ExecStartPost', 'ExecStop', 'ExecStopPost', 'ExecReload')


def offenders(units, allowlist):
    return [u for u in units if u["suspicious"] and u["name"] not in allowlist
            and (u["state"] not in MASKED or u.get('active_state') in ('active', 'activating', 'reloading'))]


def live_manager(scope, command):
    files = subprocess.check_output([*command, 'list-unit-files'], text=True)
    states = {fields[0]: fields[1] for line in files.splitlines() if len(fields := line.split()) >= 2}
    loaded = subprocess.check_output([*command, 'list-units', '--all', '--plain'], text=True)
    names = set(states) | {line.split()[0] for line in loaded.splitlines() if line.split()}
    # Uninstantiated templates have no manager object; their on-disk definitions
    # are still audited. Query every loaded instance and activation dependency.
    pending = names - {name for name in names if '@.' in name}
    properties = {}
    while pending:
        batch = sorted(pending)[:100]
        output = subprocess.check_output([*command, 'show', '--all', '--property=' + ','.join(PROPERTIES), '--', *batch], text=True)
        for block in output.strip().split('\n\n'):
            values = dict(line.split('=', 1) for line in block.splitlines() if '=' in line)
            if values.get('Id'):
                properties[values['Id']] = values
                # systemd shell-quotes string vectors, including backslashes
                # that are literal parts of escaped unit names.
                for alias in shlex.split(values.get('Names', '')):
                    properties[alias] = values
        missing = set(batch) - properties.keys()
        assert not missing, f'{scope} manager omitted units: {missing}'
        pending.difference_update(batch)
        for name in batch:
            for key in DEPENDENCIES:
                pending.update(set(shlex.split(properties[name].get(key, ''))) - properties.keys())
    return states, properties


def inventory(root=pathlib.Path('/'), live=False):
    result = []
    for scope in ("system", "user"):
        args = ["systemctl", f"--root={root}", "--no-pager", "--no-legend"]
        if scope == "user":
            args.append("--global")
        output = subprocess.check_output([*args, "list-unit-files"], text=True)
        states = {fields[0]: fields[1] for line in output.splitlines() if len(fields := line.split()) >= 2}
        properties = {}
        if live:
            assert root == pathlib.Path('/'), 'Live inventory must use the running guest root'
            command = ['systemctl', '--no-pager', '--no-legend']
            if scope == 'user':
                # Ares is the only desktop account. Missing manager/bus is a
                # failed check, never a reason to silently skip the user audit.
                command = ['runuser', '-u', 'ares', '--', 'env', 'XDG_RUNTIME_DIR=/run/user/1001',
                           'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus', *command, '--user']
            live_states, properties = live_manager(scope, command)
            states.update(live_states)
            for name, values in properties.items():
                states[name] = values.get('UnitFileState') or states.get(name, 'transient')
                if values.get('LoadState') == 'masked':
                    states[name] = 'masked'
        for name, state in sorted(states.items()):
            fragments = []
            for prefix in ("usr/lib", "etc", "run"):
                path = root / prefix / "systemd" / scope / name
                if path.is_file() and not path.is_symlink():
                    fragments.append(path.read_text(errors="replace"))
                for dropin in sorted(path.parent.glob(name + '.d/*.conf')):
                    fragments.append(dropin.read_text(errors='replace'))
            values = properties.get(name, {})
            sources = ([values['FragmentPath']] if values.get('FragmentPath') else [])
            sources += shlex.split(values.get('DropInPaths', ''))
            for source in sources:
                if source != '/dev/null':
                    fragments.append(pathlib.Path(source).read_text(errors='replace'))
            # Includes commands of transient units with no backing file and
            # the manager's effective commands after drop-in resets.
            fragments.extend(key + '=' + value for key, value in values.items() if key.startswith('Exec'))
            suspicious = bool(PATTERN.search(name + "\n" + "\n".join(fragments)))
            commands = [line for fragment in fragments for line in fragment.splitlines() if line.startswith('Exec')]
            activation = {key: shlex.split(values.get(key, '')) for key in DEPENDENCIES}
            pulled_by = [parent for parent, props in properties.items()
                         if any(name in shlex.split(props.get(key, '')) for key in DEPENDENCIES)]
            result.append(dict(scope=scope, name=name, state=state, suspicious=suspicious, commands=commands,
                               active_state=values.get('ActiveState'), load_state=values.get('LoadState'),
                               sources=sources, activation=activation, pulled_by=pulled_by))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument('--live', action='store_true', help='Require live system and ares user manager inspection')
    args = parser.parse_args()
    allowlist = json.loads(pathlib.Path('/usr/share/aresos/policy/updater-allowlist.json').read_text())
    units = inventory(live=args.live)
    pathlib.Path(args.output).write_text(json.dumps(units, indent=2) + '\n')
    rejected = offenders(units, allowlist)
    if rejected:
        raise SystemExit('Unreviewed unmasked updater(s): ' + json.dumps(rejected))
    print(f'Updater audit passed: {len(units)} system/user units inspected')


if __name__ == '__main__':
    main()
