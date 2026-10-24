import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import zipfile

run, label = sys.argv[1:]
assert run.isdigit() and __import__('re').fullmatch('[a-z0-9-]+', label)

def redact_metadata(value):
    if isinstance(value, dict):
        result = {key: redact_metadata(item) for key, item in value.items()}
        if 'email' in result:
            result['email'] = 'admin@example.com'
            if 'name' in result:
                result['name'] = 'pab'
        return result
    if isinstance(value, list):
        return [redact_metadata(item) for item in value]
    return value

root = pathlib.Path.cwd()
repo = 'repos/Ares-Empire/AresOS/'
def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', repo + path]))
destination = root / 'os/manifest/ci/11c' / label
destination.mkdir(parents=True, exist_ok=True)
for suffix, filename in [('', 'run.json'), ('/jobs?per_page=100', 'jobs.json'), ('/artifacts', 'artifacts.json')]:
    data = api('actions/runs/' + run + suffix)
    (destination / filename).write_text(json.dumps(redact_metadata(data), indent=2) + '\n', encoding='utf-8')
    if suffix == '/artifacts':
        artifacts = data['artifacts']
for artifact in artifacts:
    raw = subprocess.check_output(['gh', 'api', repo + f'actions/artifacts/{artifact["id"]}/zip'])
    digest = hashlib.sha256(raw).hexdigest()
    assert artifact['digest'] == 'sha256:' + digest
    archive = root / 'reviews/11-two-disk-rehearsal/artifacts' / f'11c-{label}-{artifact["name"]}.zip'
    archive.write_bytes(raw)
    with zipfile.ZipFile(archive) as source:
        source.extractall(destination)
    print(label, artifact['name'], len(raw), digest)
for frame in destination.rglob('*.png'):
    relative = str(frame.relative_to(destination)).replace('\\', '-').replace('/', '-')
    shutil.copyfile(frame, root / 'reviews/11-two-disk-rehearsal/screenshots' / f'11c-{label}-{relative}')
logs = subprocess.check_output(['gh', 'api', repo + 'actions/runs/' + run + '/logs'])
archive = root / 'reviews/11-two-disk-rehearsal/artifacts' / f'11c-{label}-workflow-logs.zip'
archive.write_bytes(logs)
(destination / 'workflow-logs.json').write_text(json.dumps(dict(bytes=len(logs), sha256=hashlib.sha256(logs).hexdigest()), indent=2) + '\n')
