"""The static strict rule must reject static and real boot-generated units."""
import json
import pathlib
import subprocess


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def main():
    generated = 'aresos-ci-generated-canary.service'
    static = 'aresos-ci-static-canary.service'
    assert not pathlib.Path('/run/aresos-ci-never-run-updater').exists()
    assert run('systemctl', 'show', static, '--property=UnitFileState', '--value') == 'static'
    assert run('systemctl', 'show', generated, '--property=UnitFileState', '--value') == 'generated'
    fragment = run('systemctl', 'show', generated, '--property=FragmentPath', '--value')
    assert fragment.startswith('/run/systemd/generator/'), fragment
    output = pathlib.Path('/run/aresos-ci-updater-rejections.json')
    result = subprocess.run(['python3', '/usr/libexec/aresos-audit', '--live', '--output', str(output)],
                            capture_output=True, text=True, timeout=120)
    assert result.returncode != 0 and 'Unreviewed unmasked updater(s)' in result.stderr, result
    units = json.loads(output.read_text())
    canaries = [unit for unit in units if unit['scope'] == 'system' and unit['name'] in (static, generated)]
    assert len(canaries) == 2 and all(unit['suspicious'] for unit in canaries), canaries
    assert next(unit for unit in canaries if unit['name'] == static)['state'] == 'static', canaries
    generated_unit = next(unit for unit in canaries if unit['name'] == generated)
    assert generated_unit['state'] == 'generated' and fragment in generated_unit['sources'], canaries
    pathlib.Path('/run/aresos-updater-regressions.json').write_text(json.dumps(dict(
        status='passed', mode='static-strict', audit_exit=result.returncode, canaries=canaries,
        generated_fragment=fragment), indent=2) + '\n')
    # Both canaries have a false condition, so neither can perform an update.
    # Remove the CI fixtures and regenerate before checking the release policy.
    pathlib.Path('/etc/systemd/system/' + static).unlink()
    pathlib.Path('/run/aresos-ci-updater-regressions-done').touch()
    run('systemctl', 'daemon-reload')
    print('ARESOS_UPDATER_STATIC_REGRESSIONS_PASSED')


if __name__ == '__main__':
    main()
