"""Dispatch-only, runner-temporary credentials for the one pinned release."""
import base64
import hashlib
import json
import os
import pathlib
import stat
import subprocess
import sys

IMAGE = 'ghcr.io/carlsenares/aresos'
DIGEST = 'sha256:362af9b7d2a5573363d2cc441505dd076603d1d96c1b5c01af55589db2b6c402'
REFERENCE = IMAGE + '@' + DIGEST
DIRECTORY = 'aresos-11d-ghcr'


def auth_directory():
    workspace = pathlib.Path(os.environ['GITHUB_WORKSPACE']).resolve()
    temporary = pathlib.Path(os.environ['RUNNER_TEMP']).resolve()
    directory = temporary / DIRECTORY
    assert not temporary.is_relative_to(workspace), 'Refuse credentials inside the workspace'
    assert not directory.is_symlink() and directory.resolve() == directory, 'Refuse redirected credential directory'
    return directory


def require_dispatch():
    assert os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch', 'Owner auth requires workflow_dispatch'
    assert os.environ.get('REHEARSAL_MODE') in ('probe', 'full'), 'Owner auth requires probe or full'


def create():
    require_dispatch()
    token = os.environ.get('GHCR_READ_TOKEN', '')
    if not token:
        raise RuntimeError('BLOCKED: GHCR_READ_TOKEN is missing; no fallback permitted')
    directory = auth_directory()
    directory.mkdir(mode=0o700)
    path = directory / 'auth.json'
    # Package-scoped credentials cannot be selected for other GHCR packages.
    value = base64.b64encode(('carlsenares:' + token).encode()).decode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump({'auths': {IMAGE: {'auth': value}}}, stream)
    print('GHCR_READ_TOKEN auth file created under RUNNER_TEMP, mode 0600, pinned package only')


def auth_file():
    require_dispatch()
    path = auth_directory() / 'auth.json'
    assert path.is_file() and not path.is_symlink(), 'BLOCKED: runner-temporary auth file missing'
    assert stat.S_IMODE(path.stat().st_mode) == 0o600, 'Unsafe credential file mode'
    return path


def preflight(release=None):
    require_dispatch()
    release = release or json.loads(pathlib.Path('os/manifest/release.json').read_text())
    assert release['reference'] == REFERENCE, 'Refuse any other image or digest'
    path = auth_file()
    # Neither a library error nor command tracing may export credentials. Only
    # the validated digest and a fixed failure reason cross into evidence.
    result = subprocess.run(['skopeo', 'inspect', '--authfile', str(path), '--format', '{{.Digest}}',
                             'docker://' + REFERENCE], capture_output=True, text=True, timeout=90)
    passed = result.returncode == 0 and result.stdout.strip() == DIGEST
    proof = dict(status='passed' if passed else 'blocked', reference=REFERENCE,
                 secret='GHCR_READ_TOKEN', scope='read:packages; pinned image only; expires after 30 days',
                 username='carlsenares', auth_file='RUNNER_TEMP/' + DIRECTORY + '/auth.json',
                 auth_mode='0600', layers_pulled=False, owner_token_api_calls=0,
                 visibility_verified=False, visibility_metadata='not possible with org job token; no owner API query',
                 registry_digest=DIGEST if passed else None)
    if not passed:
        proof['reason'] = 'Pinned manifest read failed or returned a different digest; no fallback permitted'
    pathlib.Path('evidence/private-registry-preflight.json').write_text(json.dumps(proof, indent=2) + '\n')
    if not passed:
        raise RuntimeError('BLOCKED: GHCR_READ_TOKEN could not resolve the exact pinned manifest; no fallback permitted')
    print('Pinned private manifest digest verified with GHCR_READ_TOKEN; no layers pulled')


def pull():
    require_dispatch()
    release = json.loads(pathlib.Path('os/manifest/release.json').read_text())
    assert release['reference'] == REFERENCE, 'Refuse any other image or digest'
    destination = pathlib.Path(os.environ['GITHUB_WORKSPACE']) / '.work/11d-release-oci'
    result = subprocess.run(['skopeo', 'copy', '--src-authfile', str(auth_file()), '--preserve-digests',
        'docker://' + REFERENCE, 'oci:' + str(destination) + ':pinned'], capture_output=True, timeout=480)
    if result.returncode:
        raise RuntimeError('BLOCKED: pinned layer pull with GHCR_READ_TOKEN failed; no fallback permitted')
    raw = subprocess.check_output(['skopeo', 'inspect', '--raw', 'oci:' + str(destination) + ':pinned'])
    assert 'sha256:' + hashlib.sha256(raw).hexdigest() == DIGEST, 'Pinned local OCI manifest digest differs'
    pathlib.Path('evidence/owner-release-pull.json').write_text(json.dumps(dict(status='passed',
        reference=REFERENCE, secret='GHCR_READ_TOKEN', owner_token_api_calls=0,
        preserved_digest=True, credential_file_copied=False)) + '\n')
    print('Pinned release layers pulled with GHCR_READ_TOKEN; exact manifest digest preserved')


def cleanup():
    directory = auth_directory()
    path = directory / 'auth.json'
    if directory.exists():
        assert set(p.name for p in directory.iterdir()) <= {'auth.json'}, 'Unexpected credential-directory contents'
        path.unlink(missing_ok=True)
        directory.rmdir()
    assert not path.exists() and not directory.exists()
    pathlib.Path('evidence').mkdir(exist_ok=True)
    pathlib.Path('evidence/owner-auth-cleanup.json').write_text(json.dumps(dict(
        status='passed', secret='GHCR_READ_TOKEN', removed=True, outside_workspace=True)) + '\n')
    print('Runner-temporary GHCR_READ_TOKEN auth file removed')


def guest_mount_command():
    # Only a mount tag and paths traverse the serial console. The host file is
    # exported read-only; no credential bytes enter a command or the guest disk.
    return '''set -e
modprobe 9pnet_virtio
install -d -m 0700 /run/aresos-owner-auth
if ! mountpoint -q /run/aresos-owner-auth; then
    mount -t 9p -o trans=virtio,version=9p2000.L,ro,cache=none aresos-owner-auth /run/aresos-owner-auth
fi
test "$(findmnt -n -o FSTYPE /run/aresos-owner-auth)" = 9p
findmnt -n -o OPTIONS /run/aresos-owner-auth | tr , '\\n' | grep -qx ro
test "$(stat -c %a /run/aresos-owner-auth/auth.json)" = 600
test -r /run/aresos-owner-auth/auth.json
install -d -m 0700 /etc/ostree
test ! -e /etc/ostree/auth.json || test -L /etc/ostree/auth.json
ln -sfn /run/aresos-owner-auth/auth.json /etc/ostree/auth.json
echo OWNER_AUTH_READ_ONLY_RUNNER_TEMP_SHARE_READY
'''


if __name__ == '__main__':
    {'create': create, 'preflight': preflight, 'pull': pull, 'cleanup': cleanup}[sys.argv[1]]()
