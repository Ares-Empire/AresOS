import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import zipfile

run, label = sys.argv[1:]
root = pathlib.Path.cwd()
repo = 'repos/carlsenares/AresOS/'
def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', repo + path]))
destination = root / 'os/manifest/ci/11b' / label
destination.mkdir(parents=True, exist_ok=True)
for suffix, filename in [('', 'run.json'), ('/jobs?per_page=100', 'jobs.json'), ('/artifacts', 'artifacts.json')]:
    data = api('actions/runs/' + run + suffix)
    (destination / filename).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    if suffix == '/artifacts':
        artifacts = data['artifacts']
for artifact in artifacts:
    raw = subprocess.check_output(['gh', 'api', repo + f'actions/artifacts/{artifact["id"]}/zip'])
    digest = hashlib.sha256(raw).hexdigest()
    assert artifact['digest'] == 'sha256:' + digest
    archive = root / 'reviews/11-two-disk-rehearsal/artifacts' / f'11b-{label}-{artifact["name"]}.zip'
    archive.write_bytes(raw)
    with zipfile.ZipFile(archive) as source:
        source.extractall(destination)
    print(label, artifact['name'], len(raw), digest)
for frame in destination.rglob('*.png'):
    relative = str(frame.relative_to(destination)).replace('\\', '-').replace('/', '-')
    shutil.copyfile(frame, root / 'reviews/11-two-disk-rehearsal/screenshots' / f'11b-{label}-{relative}')
logs = subprocess.check_output(['gh', 'api', repo + 'actions/runs/' + run + '/logs'])
archive = root / 'reviews/11-two-disk-rehearsal/artifacts' / f'11b-{label}-workflow-logs.zip'
archive.write_bytes(logs)
(destination / 'workflow-logs.json').write_text(json.dumps(dict(bytes=len(logs), sha256=hashlib.sha256(logs).hexdigest()), indent=2) + '\n')
