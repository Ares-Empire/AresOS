"""Resolve host tools before sudo; privileged work never searches PATH."""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

NAMES = ('bash', 'python3', 'sudo', 'cosign', 'podman', 'skopeo')


def validate(tools):
    if not isinstance(tools, dict) or set(tools) != set(NAMES):
        raise RuntimeError('STOP: build tool manifest must contain exactly ' + ', '.join(NAMES))
    for name, value in tools.items():
        if not isinstance(value, str) or not pathlib.Path(value).is_absolute():
            raise RuntimeError('STOP: missing or relative executable path for ' + name)
        path = pathlib.Path(value)
        if not path.is_file() or not os.access(path, os.X_OK):
            raise RuntimeError('STOP: missing or non-executable tool path for ' + name + ': ' + value)
    return tools


def resolve():
    tools = {}
    for name in NAMES:
        value = shutil.which(name)
        if value is None:
            raise RuntimeError('STOP: cannot resolve required build tool before credentials: ' + name)
        tools[name] = str(pathlib.Path(value).resolve(strict=True))
    return validate(tools)


def load(path):
    path = pathlib.Path(path)
    if not path.is_absolute() or not path.is_file():
        raise RuntimeError('STOP: absolute existing build tool manifest required')
    return validate(json.loads(path.read_text()))


def build(tools):
    # Validation is deliberately first: even auth_file() must not be reached
    # with an invalid executable, and no fallback to the privileged PATH exists.
    tools = validate(tools)
    assert os.environ['GITHUB_REPOSITORY'] == 'Ares-Empire/AresOS'
    assert os.environ['GITHUB_REF_NAME'] == 'pkg/13-keyboard-layout'
    assert os.environ['REHEARSAL_MODE'] == 'release-13'
    assert 'GHCR_READ_TOKEN' not in os.environ, 'Owner secret must stay in the auth-file creation step'
    release = json.loads(pathlib.Path('os/manifest/releases/06.json').read_text())
    previous = release['reference']
    from rehearsal_auth import auth_file
    auth = auth_file()
    registry = pathlib.Path(os.environ['RUNNER_TEMP']) / 'aresos-13-old-cosign'
    registry.mkdir(mode=0o700)
    try:
        (registry / 'config.json').symlink_to(auth)
        with pathlib.Path('evidence/previous-release-signature.json').open('w') as stream:
            subprocess.run([tools['cosign'], 'verify', '--certificate-identity', release['signature']['identity'],
                '--certificate-oidc-issuer', release['signature']['issuer'], previous], check=True,
                env=dict(os.environ, DOCKER_CONFIG=str(registry)), stdout=stream)
        subprocess.run([tools['podman'], 'pull', '--authfile', str(auth), previous], check=True)
        subprocess.run([tools['podman'], 'build', '--pull=never', '--format=oci', '--build-arg',
            'ARESOS_SOURCE_REVISION=' + os.environ['GITHUB_SHA'], '--tag', 'localhost/aresos:ci',
            '--file', 'os/Containerfile.keyboard', 'os'], check=True)
        import image_diff
        image_diff.main(tools)
        # These executables run inside the exact pinned image, not on the host.
        copy = "import pathlib,shutil; [(shutil.copyfile(p, pathlib.Path('/evidence')/p.name)) for p in pathlib.Path('/usr/share/aresos/manifest').iterdir() if p.is_file()]"
        subprocess.run([tools['podman'], 'run', '--rm', '--network=none', '--read-only',
            '--entrypoint=/usr/bin/python3', '-v', str(pathlib.Path('evidence').resolve()) + ':/evidence',
            'localhost/aresos:ci', '-c', copy], check=True)
        raw = subprocess.check_output([tools['skopeo'], 'inspect', '--raw', 'containers-storage:localhost/aresos:ci'])
        pathlib.Path('evidence/image-oci-manifest.json').write_bytes(raw)
        pathlib.Path('evidence/image-inspect.json').write_bytes(subprocess.check_output(
            [tools['podman'], 'image', 'inspect', 'localhost/aresos:ci']))
        pathlib.Path('evidence/image-digest.txt').write_text(hashlib.sha256(raw).hexdigest() + '  evidence/image-oci-manifest.json\n')
    finally:
        (registry / 'config.json').unlink(missing_ok=True)
        registry.rmdir()


def main():
    mode, manifest, *extra = sys.argv[1:]
    if mode == 'resolve':
        assert not extra
        tools = resolve()
        pathlib.Path(manifest).write_text(json.dumps(tools, indent=2) + '\n')
        print('BUILD_TOOLS_RESOLVED_BEFORE_CREDENTIALS ' + json.dumps(tools, sort_keys=True))
        return
    tools = load(manifest)
    if mode == 'launch':
        assert not extra
        wrapper = pathlib.Path(__file__).with_name('build-keyboard-release.sh').resolve()
        subprocess.run([tools['sudo'], '-E', tools['bash'], str(wrapper), tools['python3'],
                        str(pathlib.Path(manifest).resolve())], check=True)
    elif mode == 'privileged':
        assert extra in ([], ['--check-tools'])
        if extra:
            print('BUILD_TOOLS_VALIDATED_WITHOUT_CREDENTIALS ' + json.dumps(tools, sort_keys=True))
        else:
            build(tools)
    else:
        raise RuntimeError('STOP: unrecognized build tool operation')


if __name__ == '__main__':
    main()
