#!/usr/bin/python3
"""Require masks or review for static/generated units, plus live state checks."""
import argparse
import json
import pathlib
import re
import subprocess

PATTERN = re.compile(r"uupd|updat|upgrad|topgrade|bootc.*(fetch|apply)|flatpak|brew|rpm-ostreed-automatic|rebase", re.I)
MASKED = {"masked", "masked-runtime"}


def offenders(units, allowlist):
    return [u for u in units if u["suspicious"] and u["name"] not in allowlist
            and (u["state"] not in MASKED
                 or u.get('active_state') in ('active', 'activating', 'reloading', 'deactivating')
                 or u.get('sub_state') == 'running')]


def live_states(command):
    # List output is one snapshot. Do not chase transient objects/files that
    # may disappear between manager queries; graph inspection is a follow-up.
    files = subprocess.check_output([*command, 'list-unit-files'], text=True)
    states = {fields[0]: fields[1] for line in files.splitlines() if len(fields := line.split()) >= 2}
    loaded = subprocess.check_output([*command, 'list-units', '--all', '--plain'], text=True)
    units = {}
    for line in loaded.splitlines():
        fields = line.split()
        if not fields:
            continue
        assert len(fields) >= 4, f'Invalid live unit row: {line!r}'
        units[fields[0]] = dict(load_state=fields[1], active_state=fields[2], sub_state=fields[3])
    return states, units


def unit_directories(root, scope):
    directories = [root / prefix / 'systemd' / scope for prefix in ('usr/lib', 'usr/local/lib', 'etc', 'run')]
    runtime = root / ('run/systemd' if scope == 'system' else 'run/user/1000/systemd')
    directories.extend(runtime / name for name in ('generator.early', 'generator', 'generator.late'))
    return directories


def inventory(root=pathlib.Path('/'), live=False):
    result = []
    for scope in ("system", "user"):
        args = ["systemctl", f"--root={root}", "--no-pager", "--no-legend"]
        if scope == "user":
            args.append("--global")
        output = subprocess.check_output([*args, "list-unit-files"], text=True)
        states = {fields[0]: fields[1] for line in output.splitlines() if len(fields := line.split()) >= 2}
        running = {}
        directories = unit_directories(root, scope)
        if live:
            assert root == pathlib.Path('/'), 'Live inventory must use the running guest root'
            command = ['systemctl', '--no-pager', '--no-legend']
            if scope == 'user':
                # Ares is the only desktop account. Missing manager/bus is a
                # failed check, never a reason to silently skip the user audit.
                command = ['runuser', '-u', 'ares', '--', 'env', 'XDG_RUNTIME_DIR=/run/user/1000',
                           'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus', *command, '--user']
            manager_states, running = live_states(command)
            states.update(manager_states)
            for name, values in running.items():
                states.setdefault(name, 'transient')
                if values['load_state'] == 'masked':
                    states[name] = 'masked'
            # Generated fragments are stable boot output, unlike transient
            # manager files. Inspect them directly without activation traversal.
            for directory in directories:
                if directory.name.startswith('generator') and directory.is_dir():
                    for path in directory.iterdir():
                        if path.is_file() or path.is_symlink():
                            states.setdefault(path.name, 'generated')
        for name, state in sorted(states.items()):
            fragments = []
            sources = []
            names = [name]
            if '@' in name and '@.' not in name:
                names.append(name.split('@', 1)[0] + '@.' + name.rsplit('.', 1)[1])
            for directory in directories:
                for definition in names:
                    path = directory / definition
                    if path.is_file() and not path.is_symlink():
                        sources.append(str(path))
                    sources.extend(str(dropin) for dropin in sorted(directory.glob(definition + '.d/*.conf')))
            for source in sources:
                fragments.append(pathlib.Path(source).read_text(errors='replace'))
            suspicious = bool(PATTERN.search(name + "\n" + "\n".join(fragments)))
            commands = [line for fragment in fragments for line in fragment.splitlines() if line.startswith('Exec')]
            values = running.get(name, {})
            result.append(dict(scope=scope, name=name, state=state, suspicious=suspicious, commands=commands,
                               active_state=values.get('active_state'), load_state=values.get('load_state'),
                               sub_state=values.get('sub_state'), sources=sources))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument('--live', action='store_true', help='Also require system and ares manager state snapshots')
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
