"""Account for actual guard retries without double-counting per-step log copies."""
import hashlib
import json
import pathlib
import re
import zipfile

root = pathlib.Path('os/manifest/ci/11k')
review = pathlib.Path('reviews/11-two-disk-rehearsal')
observations = []
sources = []
failures = []


def retries(text):
    return [json.loads(match.group(1)) for match in
            re.finditer(r'GUARD_READ_RETRY (\{[^\r\n]+\})', text)]


for name in ('initial', 'before-probe', 'before-full', 'after-full'):
    path = review / 'logs/11k' / (name + '-guard.txt')
    if not path.exists():
        continue
    text = path.read_text(encoding='utf-8')
    failures.extend(dict(phase='local-' + name, **json.loads(m.group(1))) for m in
                    re.finditer(r'GUARD_READ_FAILED (\{[^\r\n]+\})', text))
    records = retries(text)
    sources.append(dict(path=path.as_posix(), sha256=hashlib.sha256(
        path.read_bytes().replace(b'\r\n', b'\n')).hexdigest(), retries=len(records)))
    observations.extend(dict(phase='local-' + name, **r) for r in records)

for directory in sorted(p for p in root.iterdir() if p.is_dir() and (p / 'run.json').exists()):
    path = review / 'artifacts' / ('11k-' + directory.name + '-workflow-logs.zip')
    with zipfile.ZipFile(path) as archive:
        # GitHub includes the whole job and each step again. Only whole-job logs
        # establish the retry sequence; copied step files are not extra attempts.
        text = '\n'.join(archive.read(n).decode('utf-8', errors='replace') for n in archive.namelist()
                         if '/' not in n and n.endswith('.txt'))
    records = retries(text)
    failed = [json.loads(m.group(1)) for m in re.finditer(r'GUARD_READ_FAILED (\{[^\r\n]+\})', text)]
    failures.extend(dict(phase='CI-' + directory.name, **r) for r in failed)
    receipt = directory / '11c-dispatch-authorization.json'
    if receipt.exists():
        assert not failed, 'Failed guard cannot also produce a successful authorization'
        assert records == json.loads(receipt.read_text(encoding='utf-8'))['read_retries']
    sources.append(dict(path=path.as_posix(), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        retries=len(records)))
    observations.extend(dict(phase='CI-' + directory.name, **r) for r in records)

for record in observations:
    assert record['status'] == 'connection' or 500 <= record['status'] <= 599
    assert 1 <= record['attempt'] <= 4 and record['next_attempt'] == record['attempt'] + 1
    assert record['wait_seconds'] == (10, 20, 40, 60)[record['attempt'] - 1]
result = dict(retries=len(observations), observations=observations, terminal_failures=failures, sources=sources,
              note='Each row is an actual retry, not a new workflow dispatch; native mocked-test stderr is captured and absent.')
(root / 'retry-observations.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
rows = ['| Guard phase | Path | HTTP status / connection | Failed attempt → next / wait |', '|---|---|---|---|']
for r in observations:
    rows.append(f"| {r['phase']} | `{r['path']}` | {r['status']} | {r['attempt']} → {r['next_attempt']} / {r['wait_seconds']}s |")
(root / 'retry-table.md').write_text('\n'.join(rows) + '\n', encoding='utf-8', newline='\n')
print('Actual guard retries:', len(observations))
