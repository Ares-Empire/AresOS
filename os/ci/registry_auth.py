"""Package13 job-token reads; retain the old image's owner-auth contract separately."""
import base64
import hashlib
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys

import rehearsal_auth as legacy

RELEASE = json.loads(pathlib.Path('os/manifest/release.json').read_text())
REFERENCE = RELEASE['reference']
IMAGE, DIGEST = REFERENCE.split('@')


def org_release():
    return IMAGE == 'ghcr.io/ares-empire/aresos'


def require_dispatch():
    assert os.environ['GITHUB_EVENT_NAME'] == 'workflow_dispatch'
    assert os.environ['GITHUB_REPOSITORY'] == 'Ares-Empire/AresOS'
    branch = os.environ['GITHUB_REF_NAME']
    assert (branch == 'pkg/13-keyboard-layout' and os.environ['REHEARSAL_MODE'] in ('probe', 'keyboard') or
            branch == 'pkg/14-owner-tools' and os.environ.get('REHEARSAL_PACKAGE') == '14'
            and os.environ['REHEARSAL_MODE'] in ('probe', 'owner-tools'))
    assert org_release() and RELEASE['visibility'] == 'private'


def directory():
    workspace = pathlib.Path(os.environ['GITHUB_WORKSPACE']).resolve()
    temporary = pathlib.Path(os.environ['RUNNER_TEMP']).resolve()
    path = temporary / 'aresos-13-job-ghcr'
    assert not temporary.is_relative_to(workspace) and not path.is_symlink()
    assert path.resolve() == path
    return path


def auth_file():
    if not org_release():
        return legacy.auth_file()
    require_dispatch()
    path = directory() / 'auth.json'
    assert path.is_file() and not path.is_symlink()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600 and path.stat().st_uid == 0
    assert path.parent.stat().st_uid == 0
    return path


def create():
    if not org_release():
        return legacy.create()
    require_dispatch()
    token = os.environ.get('GH_TOKEN', '')
    assert token, 'STOP: job token missing; no owner-token fallback'
    directory().mkdir(mode=0o700)
    value = base64.b64encode((os.environ['GITHUB_ACTOR'] + ':' + token).encode()).decode()
    fd = os.open(directory() / 'auth.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump({'auths': {IMAGE: {'auth': value}}}, stream)
    print('Package13 job-token auth prepared outside workspace; owner secret not used')


def preflight():
    if not org_release():
        return legacy.preflight()
    require_dispatch()
    metadata = json.loads(subprocess.check_output(['gh', 'api',
        'orgs/Ares-Empire/packages/container/aresos']))
    assert metadata['visibility'] == 'private', 'STOP: org package is not private'
    result = subprocess.run(['skopeo', 'inspect', '--authfile', str(auth_file()), '--format', '{{.Digest}}',
        'docker://' + REFERENCE], capture_output=True, text=True, timeout=90)
    passed = result.returncode == 0 and result.stdout.strip() == DIGEST
    proof = dict(status='passed' if passed else 'blocked', reference=REFERENCE,
        registry_digest=DIGEST if passed else None, secret='GITHUB_TOKEN', auth_kind='job-token',
        owner_token_api_calls=0, owner_token_used=False, visibility_verified=True, visibility='private')
    pathlib.Path('evidence/private-registry-preflight.json').write_text(json.dumps(proof, indent=2) + '\n')
    assert passed, 'STOP: job token cannot read pinned org release; no credential fallback'


def pull():
    if not org_release():
        return legacy.pull()
    require_dispatch()
    target = pathlib.Path(os.environ['GITHUB_WORKSPACE']).resolve() / '.work/13-release-oci'
    assert not target.exists()
    result = subprocess.run(['skopeo', 'copy', '--src-authfile', str(auth_file()), '--preserve-digests',
        'docker://' + REFERENCE, 'oci:' + str(target) + ':pinned'], capture_output=True, timeout=480)
    assert result.returncode == 0, 'STOP: pinned org layer read failed'
    raw = subprocess.check_output(['skopeo', 'inspect', '--raw', 'oci:' + str(target) + ':pinned'])
    assert 'sha256:' + hashlib.sha256(raw).hexdigest() == DIGEST
    shutil.rmtree(target)
    pathlib.Path('evidence/owner-release-pull.json').write_text(json.dumps(dict(status='passed',
        reference=REFERENCE, secret='GITHUB_TOKEN', owner_token_api_calls=0, owner_token_used=False,
        preserved_digest=True, credential_file_copied=False, local_copy_removed=True)) + '\n')


def cleanup():
    if not org_release():
        return legacy.cleanup()
    path = directory()
    if path.exists():
        assert set(p.name for p in path.iterdir()) <= {'auth.json', 'config.json'}
        config = path / 'config.json'
        if config.exists() or config.is_symlink():
            assert config.is_symlink() and config.readlink() == pathlib.Path('auth.json')
            config.unlink()
        (path / 'auth.json').unlink(missing_ok=True)
        path.rmdir()
    pathlib.Path('evidence').mkdir(exist_ok=True)
    pathlib.Path('evidence/owner-auth-cleanup.json').write_text(json.dumps(dict(status='passed',
        secret='GITHUB_TOKEN', removed=True, outside_workspace=True, owner_token_used=False)) + '\n')


guest_mount_command = legacy.guest_mount_command


def signature(cosign):
    require_dispatch()
    assert os.environ['GITHUB_REF_NAME'] == 'pkg/14-owner-tools'
    tool = pathlib.Path(cosign)
    assert tool.is_absolute() and tool.is_file() and os.access(tool, os.X_OK), 'Resolve cosign before sudo'
    config = directory() / 'config.json'
    assert not config.exists() and not config.is_symlink()
    config.symlink_to('auth.json')
    result = subprocess.run([str(tool), 'verify', '--certificate-identity', RELEASE['signature']['identity'],
        '--certificate-oidc-issuer', RELEASE['signature']['issuer'], REFERENCE],
        env=dict(os.environ, DOCKER_CONFIG=str(directory())), capture_output=True, timeout=180)
    assert result.returncode == 0, 'STOP: exact private release signature failed; no credential fallback'
    pathlib.Path('evidence/private-release-signatures.json').write_bytes(result.stdout)
    pathlib.Path('evidence/private-release-signature-proof.json').write_text(json.dumps(dict(status='passed',
        reference=REFERENCE, identity=RELEASE['signature']['identity'], issuer=RELEASE['signature']['issuer'],
        sha=os.environ['GITHUB_SHA'], context='native host; guest NIC remains link-down',
        signature_sha256=hashlib.sha256(result.stdout).hexdigest())) + '\n')

if __name__ == '__main__':
    if sys.argv[1] == 'signature':
        signature(sys.argv[2])
    else:
        {'create': create, 'preflight': preflight, 'pull': pull, 'cleanup': cleanup}[sys.argv[1]]()
