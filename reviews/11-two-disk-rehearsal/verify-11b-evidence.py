import hashlib
import json
import pathlib
import re
import sys
import zipfile

root = pathlib.Path.cwd()
sys.path.insert(0, str(root / 'os/ci'))
from disk_audit import compare_disk, protected_writes, compare_nvram, boot_variables, all_variables
from installer_webui import validate_review, validate_keyboard_proof

records = root / 'os/manifest/ci/11b'
display_sources = {'usr_libexec_livesys_functions', 'usr_libexec_livesys_livesys-late',
                   'usr_libexec_livesys_livesys-main', 'usr_share_anaconda_interactive-defaults.ks'}


def normalized_text(raw):
    return ('\n'.join(line.rstrip() for line in raw.decode('utf-8').splitlines()).rstrip() + '\n').encode('utf-8')


nvram_failures = []
total_snapshots = total_counters = total_missing = 0
for run in sorted(path for path in records.iterdir() if path.is_dir()):
    metadata = json.loads((run / 'run.json').read_text())
    artifacts = json.loads((run / 'artifacts.json').read_text())['artifacts']
    receipt = json.loads((run / 'workflow-logs.json').read_text())
    log_archive = root / 'reviews/11-two-disk-rehearsal/artifacts' / f'11b-{run.name}-workflow-logs.zip'
    assert len(log_archive.read_bytes()) == receipt['bytes']
    assert hashlib.sha256(log_archive.read_bytes()).hexdigest() == receipt['sha256']
    for item in artifacts:
        archive = root / 'reviews/11-two-disk-rehearsal/artifacts' / f'11b-{run.name}-{item["name"]}.zip'
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == item['digest'].split(':')[1]
        with zipfile.ZipFile(archive) as source:
            for name in source.namelist():
                if name.endswith('/'):
                    continue
                observed = run / name
                # The repeated 33 MB inventory is retained in each verified
                # original archive; expanding it is optional for reviewers.
                if name == 'installer/squashfs-files.txt' and not observed.exists():
                    continue
                if observed.suffix == '.txt' or observed.name in display_sources:
                    assert normalized_text(observed.read_bytes()) == normalized_text(source.read(name)), (run.name, name)
                else:
                    assert observed.read_bytes() == source.read(name), (run.name, name)
    snapshots = counters = 0
    missing = []
    for baseline in run.rglob('protected-baseline.json'):
        folder = baseline.parent
        before = json.loads(baseline.read_text())
        firmware = json.loads((folder / 'baseline-firmware-nvram.json').read_text())
        for state in folder.glob('*-protected.json'):
            compare_disk(before, json.loads(state.read_text()))
            snapshots += 1
            stage = state.name.removesuffix('-protected.json')
            nvram = json.loads((folder / (stage + '-nvram.json')).read_text())
            try:
                compare_nvram(firmware, nvram)
            except AssertionError as error:
                failure = dict(run=run.name, stage=stage, error=str(error))
                nvram_failures.append(failure)
                print('STRICT NVRAM AUDIT FAILED:', json.dumps(failure))
            assert boot_variables(folder / (stage + '-vars.fd')) == nvram
            assert all_variables(folder / (stage + '-vars.fd')) == json.loads((folder / (stage + '-all-variables.json')).read_text())
            stats = folder / (stage + '-blockstats.json')
            if stats.exists():
                protected_writes(json.loads(stats.read_text()))
                counters += 1
            else:
                missing.append(str(state.relative_to(run)))
        print(run.name, 'protected SHA256', before['sha256'])
    for proof in run.rglob('probe-result.json'):
        value = json.loads(proof.read_text())
        assert value.get('installed') is False
        if value['status'] == 'passed':
            assert value['both_orders'] and value['review_validated'] and not missing
            assert value['detached_windows'] and value['target_reset']
            assert value['commit'] == metadata['head_sha']
        print(run.name, 'probe status', value['status'])
    for review in run.rglob('review-proof.json'):
        value = json.loads(review.read_text())
        validate_review(value['tables'], value['protected'], value['target'])
    for keyboard in run.rglob('webui-keyboard-proof.json'):
        validate_keyboard_proof(json.loads(keyboard.read_text()))
    print(run.name, metadata['conclusion'], 'matching offline stages', snapshots, 'zero-write counter records', counters,
          'stages without final counter record', len(missing))
    total_snapshots += snapshots
    total_counters += counters
    total_missing += len(missing)

pattern = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{25,}|\$(?:6|y)\$[^\s\x27\x22<>]{15,})')
scanned = 0
for path in records.rglob('*'):
    if path.is_file() and path.suffix in ('.txt', '.json', '.ks'):
        if path.name == 'squashfs-files.txt':
            continue
        assert not pattern.search(path.read_bytes()), 'Potential unmasked credential in ' + str(path)
        scanned += 1
print('Credential-pattern scan passed:', scanned, 'expanded evidence files')
archived_scanned = 0
for archive in (root / 'reviews/11-two-disk-rehearsal/artifacts').glob('11b-*.zip'):
    with zipfile.ZipFile(archive) as source:
        for name in source.namelist():
            if name.endswith('/'):
                continue
            raw = source.read(name)
            try:
                raw.decode('utf-8')
            except UnicodeDecodeError:
                continue
            assert not pattern.search(raw), 'Potential unmasked archived credential in ' + str(archive) + ' / ' + name
            archived_scanned += 1
print('Raw archived UTF-8 credential-pattern scans passed:', archived_scanned)
print('Byte/layout equality and counter records are reported separately; failed/missing stages are not qualification.')
print('Total matching offline stages:', total_snapshots, 'zero-write records:', total_counters,
      'missing final counter records:', total_missing, 'strict NVRAM failures:', len(nvram_failures))
if nvram_failures:
    print('REHEARSAL NOT QUALIFIED: the original strict NVRAM predicate still fails.')
    raise SystemExit(1)
