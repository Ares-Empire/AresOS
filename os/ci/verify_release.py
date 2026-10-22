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
assert release['run'] == f'https://github.com/{repository}/actions/runs/{run_id}'


def api(suffix):
    return json.loads(subprocess.check_output(['gh', 'api', f'repos/{repository}/actions/runs/{run_id}{suffix}']))


run = api('')
assert run['head_sha'] == source and run['path'] == '.github/workflows/os-image.yml', run
jobs = api('/jobs?per_page=100')['jobs']
qualified = [job for job in jobs if job['name'] == 'image' and job['conclusion'] == 'success']
assert len(qualified) == 1, 'Original image build/two-VM/publish job must have succeeded'
subprocess.run(['git', 'fetch', '--no-tags', '--depth=1', 'origin', source], check=True)
# A retry can change the test harness or documentation, never the release's
# runtime payload, package lock, base, policy or verification key.
payload = ['os/Containerfile', 'os/.containerignore', 'os/build.sh', 'os/packages.lock.json',
           'os/config', 'os/policy', 'os/tests/audit.py', 'os/manifest/base.json', 'os/keys']
subprocess.run(['git', 'diff', '--exit-code', source, 'HEAD', '--', *payload], check=True)
print(f'Qualified release source {source}; runtime payload unchanged; testing {release["reference"]}')
