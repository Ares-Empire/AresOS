"""Permit a cheaper switch-only retry only for an already-qualified image."""
import json
import os
import pathlib
import re
import subprocess
import sys

run_id = sys.argv[1]
assert run_id.isdigit(), 'A numeric workflow run ID is required'
release = json.loads(pathlib.Path('evidence/release.json').read_text())
source = release['source_commit']
assert re.fullmatch(r'[0-9a-f]{40}', source), source
assert re.fullmatch(r'ghcr\.io/carlsenares/aresos@sha256:[0-9a-f]{64}', release['reference'])
assert release['visibility'] == 'private'
assert release['base'] == json.loads(pathlib.Path('os/manifest/base.json').read_text())['reference']
repository = os.environ['GITHUB_REPOSITORY']
assert repository in ('carlsenares/AresOS', 'Ares-Empire/AresOS')
assert release['run'] == f'https://github.com/carlsenares/AresOS/actions/runs/{run_id}'


def api(suffix):
    return json.loads(subprocess.check_output(['gh', 'api', f'repos/{repository}/actions/runs/{run_id}{suffix}']))


run = api('')
assert run['head_sha'] == source and run['path'] == '.github/workflows/os-image.yml', 'Original release run identity differs'
jobs = api('/jobs?per_page=100')['jobs']
qualified = [job for job in jobs if job['name'] == 'image' and job['conclusion'] == 'success']
assert len(qualified) == 1, 'Original image build/two-VM/publish job must have succeeded'
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
