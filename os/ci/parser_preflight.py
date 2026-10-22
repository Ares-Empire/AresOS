"""Exercise the release audit against its real Fedora system and user managers."""
import gzip
import importlib.machinery
import importlib.util
import json
import pathlib
import subprocess


def main():
    loader = importlib.machinery.SourceFileLoader('audit', '/usr/libexec/aresos-audit')
    spec = importlib.util.spec_from_loader(loader.name, loader)
    audit = importlib.util.module_from_spec(spec)
    loader.exec_module(audit)
    evidence = pathlib.Path('/evidence')
    version = subprocess.check_output(['systemctl', '--version'], text=True)
    (evidence / 'fedora-systemd-version.txt').write_text(version)
    print(version, end='')

    escaped = r'aresos-parser\x2dprobe.service'
    alias = 'aresos-parser-alias.service'
    target = 'aresos-parser-probe.target'
    user = ['runuser', '-u', 'ares', '--', 'env', 'XDG_RUNTIME_DIR=/run/user/1001',
            'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus', 'systemctl', '--user']
    for scope, command in (('system', ['systemctl']), ('user', user)):
        directory = pathlib.Path('/run/systemd') / scope
        directory.mkdir(parents=True, exist_ok=True)
        (directory / escaped).write_text('[Service]\nExecStart=/usr/bin/true\n')
        (directory / alias).symlink_to(escaped)
        (directory / target).write_text(f'[Unit]\nWants={escaped}\n')
        dropins = directory / (escaped + '.d')
        dropins.mkdir()
        (dropins / 'with spaces.conf').write_text('[Unit]\nDescription=Parser preflight\n')
        subprocess.run([*command, 'daemon-reload'], check=True)

    # Keep each exact response, including shell quoting, rather than reconstruct
    # fixtures from the already parsed inventory. Close it even on parse failure.
    check_output = subprocess.check_output
    with gzip.open(evidence / 'fedora-systemctl-transcript.jsonl.gz', 'wt') as transcript:
        def capture(args, **kwargs):
            output = check_output(args, **kwargs)
            transcript.write(json.dumps(dict(command=args, stdout=output)) + '\n')
            transcript.flush()
            return output

        audit.subprocess.check_output = capture
        units = audit.inventory(live=True)

    summary = dict(status='passed', scopes={})
    for scope in ('system', 'user'):
        scoped = {unit['name']: unit for unit in units if unit['scope'] == scope}
        probe = scoped[escaped]
        assert probe['load_state'] == 'loaded', probe
        assert target in probe['pulled_by'], probe
        assert escaped in scoped[target]['activation']['Wants'], scoped[target]
        assert scoped[alias]['load_state'] == 'loaded', scoped[alias]
        source = f'/run/systemd/{scope}/{escaped}.d/with spaces.conf'
        assert source in probe['sources'], probe
        if scope == 'system':
            assert scoped['-.mount']['load_state'] == 'loaded', scoped.get('-.mount')
        summary['scopes'][scope] = dict(unit_names=len(scoped), probe=probe, alias=scoped[alias])
        print(f'Fedora parser preflight passed: {scope}: {len(scoped)} unit names; escaped name, alias, dependency and spaced drop-in preserved')
    (evidence / 'fedora-parser-preflight.json').write_text(json.dumps(summary, indent=2) + '\n')


if __name__ == '__main__':
    main()
