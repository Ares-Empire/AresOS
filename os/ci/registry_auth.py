"""Package13 job-token reads; retain the old image's owner-auth contract separately."""
import base64
import hashlib
import json
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys

import rehearsal_auth as legacy

RELEASE = json.loads(pathlib.Path('os/manifest/release.json').read_text())
REFERENCE = RELEASE['reference']
IMAGE, DIGEST = REFERENCE.split('@')
BASELINE_BRANCH = 'pkg/331-release-29'
BASELINE_IMAGE = 'ghcr.io/ares-empire/aresos'
BASELINE_RECORDS = {
    '13': 'b9383166a21fff6ef961f400d94b51a0c5286d154dfe86cfa528f59dcda6fa6d',
    '27': '975da14646648fb39f219f52f232d4b674180a2a892bf3a91069035bdf1ea45e',
    '28': '1738474f8541468854804c02cb02a7ffcbeb5a3b27914ae7b6ceefcd7816b15a',
}
BASELINE_REGISTRY = pathlib.Path('evidence/release-29-baseline-registry.json')
CANDIDATE_REGISTRY = pathlib.Path('evidence/release-29-candidate-registry.json')
R29_BUILD_MODES = ('dry-run-29', 'publish-29')
R29_WALK_MODES = ('release-29-baseline', 'release-29')
R29_IDENTITY = 'https://github.com/Ares-Empire/AresOS/.github/workflows/os-image.yml@refs/heads/' + BASELINE_BRANCH


def require_r29_dispatch(modes):
    expected = dict(GITHUB_ACTIONS='true', GITHUB_EVENT_NAME='workflow_dispatch',
        GITHUB_REPOSITORY='Ares-Empire/AresOS', GITHUB_REF_NAME=BASELINE_BRANCH,
        GITHUB_REF='refs/heads/' + BASELINE_BRANCH)
    assert os.environ.get('REHEARSAL_PACKAGE') == '331' and \
        all(os.environ.get(key) == value for key, value in expected.items()) and \
        os.environ.get('REHEARSAL_MODE') in modes, 'STOP: unauthorized R29 dispatch'
    assert 'GHCR_READ_TOKEN' not in os.environ, 'STOP: R29 only uses the job token'


def r29_context():
    return (os.environ.get('GITHUB_REF_NAME') == BASELINE_BRANCH or os.environ.get('REHEARSAL_PACKAGE') == '331'
            or os.environ.get('REHEARSAL_MODE') in R29_BUILD_MODES + R29_WALK_MODES)


def r29_previous():
    require_r29_dispatch(R29_BUILD_MODES)
    return json.loads(historical_records()['28'])


def r29_candidate():
    require_r29_dispatch(('release-29',))
    candidate = json.loads(pathlib.Path('os/manifest/releases/29.json').read_bytes())
    assert re.fullmatch(re.escape(BASELINE_IMAGE) + r'@sha256:[0-9a-f]{64}', candidate['reference'])
    assert candidate['visibility'] == 'private'
    assert candidate['signature'] == dict(method='cosign keyless', identity=R29_IDENTITY,
                                          issuer='https://token.actions.githubusercontent.com')
    return candidate


def org_release():
    return IMAGE == 'ghcr.io/ares-empire/aresos'


def require_dispatch():
    if r29_context():
        require_r29_dispatch(R29_BUILD_MODES)
        return
    assert os.environ['GITHUB_EVENT_NAME'] == 'workflow_dispatch'
    assert os.environ['GITHUB_REPOSITORY'] == 'Ares-Empire/AresOS'
    branch = os.environ['GITHUB_REF_NAME']
    assert (branch == 'pkg/13-keyboard-layout' and os.environ['REHEARSAL_MODE'] in ('probe', 'keyboard') or
            branch == 'pkg/14-owner-tools' and os.environ.get('REHEARSAL_PACKAGE') == '14'
            and os.environ['REHEARSAL_MODE'] in ('probe', 'owner-tools') or
            branch == 'pkg/16-staged-release' and os.environ.get('REHEARSAL_PACKAGE') == '16'
            and os.environ['REHEARSAL_MODE'] == 'probe' or
            branch == 'pkg/27-first-update-release' and os.environ.get('REHEARSAL_PACKAGE') == '27'
            and os.environ['REHEARSAL_MODE'] in ('release-27', 'update') or
            branch == 'pkg/42-release-28' and os.environ.get('REHEARSAL_PACKAGE') == '42'
            and os.environ['REHEARSAL_MODE'] in ('publish-28', 'dry-run-28', 'release-28') or
            branch == 'pkg/22c-ways-back-after-update' and os.environ.get('REHEARSAL_PACKAGE') == '22c'
            and os.environ['REHEARSAL_MODE'] in ('reorder-probe', 'ways-back') or
            branch == 'pkg/22d-tools-without-stick' and os.environ.get('REHEARSAL_PACKAGE') == '22d'
            and os.environ['REHEARSAL_MODE'] == 'tools-local')
    assert org_release() and RELEASE['visibility'] == 'private'


def directory():
    workspace = pathlib.Path(os.environ['GITHUB_WORKSPACE']).resolve()
    temporary = pathlib.Path(os.environ['RUNNER_TEMP']).resolve()
    path = temporary / 'aresos-13-job-ghcr'
    assert not temporary.is_relative_to(workspace) and not path.is_symlink()
    assert path.resolve() == path
    return path


def auth_file():
    if r29_context():
        require_r29_dispatch(R29_BUILD_MODES)
        return job_auth_file()
    if not org_release():
        return legacy.auth_file()
    require_dispatch()
    return job_auth_file()


def job_auth_file():
    path = directory() / 'auth.json'
    assert path.is_file() and not path.is_symlink()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600 and path.stat().st_uid == 0
    assert path.parent.stat().st_uid == 0
    return path


def create():
    if r29_context():
        previous = r29_previous()
        write_auth(previous['reference'].split('@')[0])
        print('R29 previous-release job-token auth prepared outside workspace')
        return
    if not org_release():
        return legacy.create()
    require_dispatch()
    write_auth(IMAGE)
    print('Package13 job-token auth prepared outside workspace; owner secret not used')


def write_auth(image):
    token = os.environ.get('GH_TOKEN', '')
    assert token, 'STOP: job token missing; no owner-token fallback'
    directory().mkdir(mode=0o700)
    value = base64.b64encode((os.environ['GITHUB_ACTOR'] + ':' + token).encode()).decode()
    fd = os.open(directory() / 'auth.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump({'auths': {image: {'auth': value}}}, stream)


def require_private_package():
    metadata = subprocess.run(['gh', 'api', 'orgs/Ares-Empire/packages/container/aresos'],
                              capture_output=True, text=True, timeout=90)
    assert metadata.returncode == 0 and json.loads(metadata.stdout)['visibility'] == 'private', \
        'STOP: org package visibility could not be verified as private'


def preflight():
    if r29_context():
        previous = r29_previous()
        require_private_package()
        inspect_digest(previous['reference'])
        return
    if not org_release():
        return legacy.preflight()
    require_dispatch()
    require_private_package()
    result = subprocess.run(['skopeo', 'inspect', '--authfile', str(auth_file()), '--format', '{{.Digest}}',
        'docker://' + REFERENCE], capture_output=True, text=True, timeout=90)
    passed = result.returncode == 0 and result.stdout.strip() == DIGEST
    proof = dict(status='passed' if passed else 'blocked', reference=REFERENCE,
        registry_digest=DIGEST if passed else None, secret='GITHUB_TOKEN', auth_kind='job-token',
        owner_token_api_calls=0, owner_token_used=False, visibility_verified=True, visibility='private')
    pathlib.Path('evidence/private-registry-preflight.json').write_text(json.dumps(proof, indent=2) + '\n')
    assert passed, 'STOP: job token cannot read pinned org release; no credential fallback'


def pull():
    assert not r29_context(), 'STOP: R29 pulls its previous release through build_tools'
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
    if r29_context():
        require_r29_dispatch(R29_BUILD_MODES)
    elif not org_release():
        return legacy.cleanup()
    remove_auth()
    pathlib.Path('evidence').mkdir(exist_ok=True)
    pathlib.Path('evidence/owner-auth-cleanup.json').write_text(json.dumps(dict(status='passed',
        secret='GITHUB_TOKEN', removed=True, outside_workspace=True, owner_token_used=False)) + '\n')


def remove_auth():
    path = directory()
    if path.exists():
        assert set(p.name for p in path.iterdir()) <= {'auth.json', 'config.json'}
        config = path / 'config.json'
        if config.exists() or config.is_symlink():
            assert config.is_symlink() and config.readlink() == pathlib.Path('auth.json')
            config.unlink()
        (path / 'auth.json').unlink(missing_ok=True)
        path.rmdir()


guest_mount_command = legacy.guest_mount_command


def cosign_path(cosign):
    tool = pathlib.Path(cosign)
    assert tool.is_absolute() and tool.is_file() and os.access(tool, os.X_OK), 'Resolve cosign before sudo'
    return tool


def verify_signature(tool, release):
    result = subprocess.run([str(tool), 'verify', '--certificate-identity', release['signature']['identity'],
        '--certificate-oidc-issuer', release['signature']['issuer'], release['reference']],
        env=dict(os.environ, DOCKER_CONFIG=str(directory())), capture_output=True, timeout=180)
    assert result.returncode == 0, 'STOP: exact private release signature failed; no credential fallback'
    return result.stdout


def signature(cosign):
    require_dispatch()
    assert os.environ['GITHUB_REF_NAME'] in ('pkg/14-owner-tools','pkg/16-staged-release','pkg/27-first-update-release',
                                             'pkg/22c-ways-back-after-update','pkg/22d-tools-without-stick','pkg/42-release-28')
    assert os.environ['GITHUB_REF_NAME'] != 'pkg/42-release-28' or os.environ['REHEARSAL_MODE'] == 'release-28'
    tool = cosign_path(cosign)
    config = directory() / 'config.json'
    assert not config.exists() and not config.is_symlink()
    config.symlink_to('auth.json')
    verified = verify_signature(tool, RELEASE)
    pathlib.Path('evidence/private-release-signatures.json').write_bytes(verified)
    pathlib.Path('evidence/private-release-signature-proof.json').write_text(json.dumps(dict(status='passed',
        reference=REFERENCE, identity=RELEASE['signature']['identity'], issuer=RELEASE['signature']['issuer'],
        sha=os.environ['GITHUB_SHA'], context='native host; guest NIC remains link-down',
        signature_sha256=hashlib.sha256(verified).hexdigest())) + '\n')


def require_baseline_dispatch():
    require_r29_dispatch(R29_WALK_MODES)


def baseline_run():
    return dict(commit=os.environ['GITHUB_SHA'], run_id=os.environ['GITHUB_RUN_ID'],
                attempt=os.environ['GITHUB_RUN_ATTEMPT'])


def check_baseline_run(run):
    assert re.fullmatch('[0-9a-f]{40}', run['commit']), 'STOP: invalid baseline head'
    assert re.fullmatch('[1-9][0-9]*', run['run_id']) and run['attempt'] == '1', 'STOP: invalid baseline run'


def historical_records():
    records = {}
    for version, expected in BASELINE_RECORDS.items():
        raw = pathlib.Path(f'os/manifest/releases/{version}.json').read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected, f'STOP: immutable R{version} record differs'
        records[version] = raw
    return records


def historical_row(version, release):
    return dict(version=version, record_sha256=BASELINE_RECORDS[version], reference=release['reference'],
                source_commit=release['source_commit'], identity=release['signature']['identity'],
                issuer=release['signature']['issuer'], registry_digest=release['reference'].split('@')[1])


def inspect_digest(reference):
    digest = reference.split('@')[1]
    read = subprocess.run(['skopeo', 'inspect', '--authfile', str(job_auth_file()), '--format', '{{.Digest}}',
                           'docker://' + reference], capture_output=True, text=True, timeout=90)
    assert read.returncode == 0 and read.stdout.strip() == digest, 'STOP: job token cannot read exact digest ' + reference


def signed_digest(tool, release):
    inspect_digest(release['reference'])
    signature = verify_signature(tool, release)
    assert signature, 'STOP: no signature output for ' + release['reference']
    return hashlib.sha256(signature).hexdigest()


def candidate_row(release):
    return dict(reference=release['reference'], source_commit=release['source_commit'],
                identity=release['signature']['identity'], issuer=release['signature']['issuer'])


def baseline_preflight(cosign):
    require_baseline_dispatch()
    BASELINE_REGISTRY.unlink(missing_ok=True)
    CANDIDATE_REGISTRY.unlink(missing_ok=True)
    run, tool = baseline_run(), cosign_path(cosign)
    check_baseline_run(run)
    records = historical_records()
    assert not directory().exists(), 'STOP: the baseline requires a fresh job-token directory'
    rows = []
    candidate = r29_candidate() if os.environ['REHEARSAL_MODE'] == 'release-29' else None
    try:
        write_auth(BASELINE_IMAGE)
        require_private_package()
        job_auth_file().with_name('config.json').symlink_to('auth.json')
        for version, raw in records.items():
            release = json.loads(raw)
            rows.append(dict(historical_row(version, release), signature_sha256=signed_digest(tool, release)))
        if candidate is not None:
            candidate_proof = dict(candidate_row(candidate), signature_sha256=signed_digest(tool, candidate))
    finally:
        remove_auth()
    BASELINE_REGISTRY.parent.mkdir(exist_ok=True)
    common = dict(status='passed', **run, visibility='private', auth_kind='job-token', owner_token_used=False)
    BASELINE_REGISTRY.write_text(json.dumps(dict(common, targets=rows), indent=2) + '\n')
    if candidate is not None:
        CANDIDATE_REGISTRY.write_text(json.dumps(dict(common, **candidate_proof), indent=2) + '\n')


def check_candidate_registry(proof, release, run):
    check_baseline_run(run)
    signed = proof['signature_sha256']
    assert re.fullmatch('[0-9a-f]{64}', signed) and proof == dict(status='passed', **run, visibility='private',
        auth_kind='job-token', owner_token_used=False, **candidate_row(release), signature_sha256=signed), \
        'STOP: missing same-run R29 candidate registry proof'


def check_baseline_registry(proof, records, run):
    check_baseline_run(run)
    assert proof['status'] == 'passed' and all(proof.get(key) == value for key, value in run.items()), \
        'STOP: missing same-run historical registry proof'
    assert proof['visibility'] == 'private' and proof['auth_kind'] == 'job-token' and proof['owner_token_used'] is False
    rows = proof['targets']
    assert len(rows) == len(records), 'STOP: incomplete historical registry proof'
    for (version, raw), row in zip(records.items(), rows):
        signed = row['signature_sha256']
        assert re.fullmatch('[0-9a-f]{64}', signed) and row == dict(historical_row(version, json.loads(raw)),
            signature_sha256=signed), f'STOP: historical R{version} registry proof differs'
    return proof

if __name__ == '__main__':
    if sys.argv[1] in ('signature', 'baseline'):
        {'signature': signature, 'baseline': baseline_preflight}[sys.argv[1]](sys.argv[2])
    else:
        {'create': create, 'preflight': preflight, 'pull': pull, 'cleanup': cleanup}[sys.argv[1]]()
