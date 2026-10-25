"""Permit a cheaper switch-only retry only for an already-qualified image."""
import json
import os
import pathlib
import re
import subprocess
import sys

# Integrator verified PR12's squash binding on 2026-10-25 (briefs 14e/14g).
# These are reviewed historical facts, not a live API claim.
SQUASH_BINDING = (12, True, '775be05b7f0d6971cbdc8a3bd1aea617fc008c4d',
                  'pkg/13-keyboard-layout', 'main')
assert SQUASH_BINDING == (12, True, '775be05b7f0d6971cbdc8a3bd1aea617fc008c4d',
                          'pkg/13-keyboard-layout', 'main'), 'STOP: reviewed squash binding constants differ'
if subprocess.check_output(['git', 'rev-parse', '--is-shallow-repository']).decode().strip() != 'false':
    sys.exit('STOP: release verification requires full history; shallow repository (checkout fetch-depth: 0)')

run_id = sys.argv[1]
assert run_id.isdigit(), 'A numeric workflow run ID is required'
release = json.loads(pathlib.Path('evidence/release.json').read_text())
source = release['source_commit']
assert re.fullmatch(r'[0-9a-f]{40}', source), source
assert re.fullmatch(r'ghcr\.io/(carlsenares|ares-empire)/aresos@sha256:[0-9a-f]{64}', release['reference'])
assert release['visibility'] == 'private'
assert release['base'] == json.loads(pathlib.Path('os/manifest/base.json').read_text())['reference']
repository = os.environ['GITHUB_REPOSITORY']
assert repository in ('carlsenares/AresOS', 'Ares-Empire/AresOS')
org = release['reference'].startswith('ghcr.io/ares-empire/')
release_repository = 'Ares-Empire/AresOS' if org else 'carlsenares/AresOS'
assert release['run'] == f'https://github.com/{release_repository}/actions/runs/{run_id}'


def api(suffix):
    return json.loads(subprocess.check_output(['gh', 'api', f'repos/{repository}/actions/runs/{run_id}{suffix}']))


run = api('')
assert run['head_sha'] == source and run['path'] == '.github/workflows/os-image.yml', 'Original release run identity differs'
job_listing = api('/jobs?per_page=100')
assert job_listing['total_count'] == len(job_listing['jobs']) <= 100, 'Incomplete release job listing'
jobs = job_listing['jobs']
qualified = [job for job in jobs if job['name'] == 'image' and job['conclusion'] == 'success']
assert len(qualified) == 1, 'Original image build/two-VM/publish job must have succeeded'
if org:
    assert repository == 'Ares-Empire/AresOS'
    assert run['head_branch'] == 'pkg/13-keyboard-layout' and run['event'] == 'workflow_dispatch'
    assert run['display_title'] == 'Package 13 image release' and run['run_attempt'] == 1
    assert release['signature'] == dict(method='cosign keyless',
        identity='https://github.com/Ares-Empire/AresOS/.github/workflows/os-image.yml@refs/heads/pkg/13-keyboard-layout',
        issuer='https://token.actions.githubusercontent.com')
    subprocess.run(['git', 'fetch', '--no-tags', 'origin', source], check=True)
    # Bind the signed source to the retained PR head and reachable squash.
    number, _, merged, _, _ = SQUASH_BINDING
    subprocess.run(['git', 'fetch', '--no-tags', 'origin', f'refs/pull/{number}/head'], check=True)
    subprocess.run(['git', 'merge-base', '--is-ancestor', source, 'FETCH_HEAD'], check=True)
    subprocess.run(['git', 'fetch', '--no-tags', 'origin', merged], check=True)
    subprocess.run(['git', 'merge-base', '--is-ancestor', merged, 'HEAD'], check=True)
    payload = ['os/Containerfile.keyboard', 'os/.containerignore', 'os/packages.lock.json',
               'os/config', 'os/policy', 'os/manifest/base.json', 'os/keys', 'os/tests/audit.py']
    subprocess.run(['git', 'diff', '--exit-code', source, 'HEAD', '--', *payload], check=True)
    subprocess.run(['git', 'diff', '--exit-code', source, merged, '--', *payload], check=True)
    assert release['image_diff']['status'] == 'passed' and release['image_diff']['packages_equal'] and release['image_diff']['units_equal']
    assert release['job_token_read']['status'] == 'passed' and not release['job_token_read']['owner_token_used']
    print(f'Qualified private org release {source}; runtime payload unchanged; testing {release["reference"]}')
    sys.exit(0)
# Original signed image labels and run SHAs stay historical. Fetch only the
# rewritten, reachable main commit; pin its runtime tree to the original source.
rewritten = 'f5bb5d35dac73e95ce2bc6680ae61f20d042f5b7'
assert source == '5578ab21b880091f26bfdc2eda22dd4f304a602b'
subprocess.run(['git', 'fetch', '--no-tags', '--depth=1', 'origin', rewritten], check=True)
# A retry can change the test harness or documentation, never the release's
# runtime payload, package lock, base, policy or verification key.
payload = ['os/Containerfile', 'os/.containerignore', 'os/build.sh', 'os/packages.lock.json',
           'os/config', 'os/policy', 'os/tests/audit.py', 'os/manifest/base.json', 'os/keys']
pinned = [
    ('389ad38b7e11cc132d09510ab3431a306553770d', 'os/.containerignore'),
    ('4b8a122a21cb2b1b0545c3cbde8bdb27ca236ff6', 'os/Containerfile'),
    ('ec6420fcd3dbd2bf2b2060169264a4ad97670a62', 'os/build.sh'),
    ('7ddab5392a26d83f96a59cc5e3737df3fab511d4', 'os/config'),
    ('3724e0c06f4a3acab0811376fb928e47f2d4c11d', 'os/keys'),
    ('27035216a9fd195de36f9408c907a808848186cb', 'os/manifest/base.json'),
    ('089309ef0e197abd494d061bbc740c1e57b623db', 'os/packages.lock.json'),
    ('28504512e84ae8b65559942c33bfe08eae8d9c42', 'os/policy'),
    ('4e16353ea8fd006d0ac03b9be0b1359249b7c140', 'os/tests/audit.py'),
]
for expected, path in pinned:
    assert subprocess.check_output(['git', 'rev-parse', rewritten + ':' + path]).decode().strip() == expected
subprocess.run(['git', 'diff', '--exit-code', rewritten, 'HEAD', '--', *payload], check=True)
print(f'Qualified release source {source}; runtime payload unchanged; testing {release["reference"]}')

if '--registry-preflight' in sys.argv[2:]:
    from rehearsal_auth import preflight
    preflight(release)
