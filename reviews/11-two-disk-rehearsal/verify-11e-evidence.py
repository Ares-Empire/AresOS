"""Verify retained 11e receipts and every reached offline/QMP/firmware gate."""
import base64
import hashlib
import json
import pathlib
import re
import sys
import zipfile

root = pathlib.Path.cwd()
sys.path.insert(0, str(root / 'os/ci'))
from disk_audit import (all_variables, boot_variables, compare_disk, firmware_baseline,
                        nvram_audit, protected_writes)
from firmware_contract import check_source
from installer_webui import validate_keyboard_proof, validate_review
from rehearsal_auth import DIGEST, REFERENCE

records = root / 'os/manifest/ci/11e'
display_sources = {'usr_libexec_livesys_functions', 'usr_libexec_livesys_livesys-late',
                   'usr_libexec_livesys_livesys-main', 'usr_share_anaconda_interactive-defaults.ks'}
credential = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{25,}|\$(?:6|y)\$[^\s\x27\x22<>]{15,})')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def normalized(raw):
    return ('\n'.join(line.rstrip() for line in raw.decode('utf-8').splitlines()).rstrip() + '\n').encode()


def check_archive(path):
    count = 0
    with zipfile.ZipFile(path) as source:
        for name in source.namelist():
            assert not name.endswith('/auth.json') and name != 'auth.json', 'Auth file in evidence'
            assert 'aresos-11d-ghcr/' not in name, 'Credential directory in evidence'
            raw = source.read(name)
            assert not credential.search(raw), 'Unmasked credential pattern in evidence'
            for candidate in re.findall(rb'[A-Za-z0-9+/]{30,}={0,2}', raw):
                try:
                    decoded = base64.b64decode(candidate, validate=True)
                except ValueError:
                    continue
                assert not credential.search(decoded), 'Encoded credential pattern in evidence'
            count += 1
    return count


stages = counters = scanned = 0
events = []
incomplete = []
qualifications = []
for run in sorted(p for p in records.iterdir() if p.is_dir() and (p / 'run.json').exists()):
    metadata = read(run / 'run.json')
    receipt = read(run / 'workflow-logs.json')
    log = root / 'reviews/11-two-disk-rehearsal/artifacts' / f'11e-{run.name}-workflow-logs.zip'
    assert len(log.read_bytes()) == receipt['bytes']
    assert hashlib.sha256(log.read_bytes()).hexdigest() == receipt['sha256']
    scanned += check_archive(log)
    for artifact in read(run / 'artifacts.json')['artifacts']:
        archive = root / 'reviews/11-two-disk-rehearsal/artifacts' / f'11e-{run.name}-{artifact["name"]}.zip'
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == artifact['digest'].split(':')[1]
        scanned += check_archive(archive)
        with zipfile.ZipFile(archive) as source:
            for name in source.namelist():
                if name.endswith('/') or name == 'installer/squashfs-files.txt' and not (run / name).exists():
                    continue
                actual, original = (run / name).read_bytes(), source.read(name)
                if pathlib.Path(name).suffix == '.txt' or pathlib.Path(name).name in display_sources:
                    assert normalized(actual) == normalized(original), (run.name, name)
                else:
                    assert actual == original, (run.name, name)
    if (run / 'firmware-contract-source.txt').exists():
        check_source((run / 'firmware-contract-source.txt').read_text(encoding='utf-8'))
    if (run / 'private-registry-preflight.json').exists():
        manifest = read(run / 'private-registry-preflight.json')
        assert manifest['status'] == 'passed' and manifest['reference'] == REFERENCE and manifest['registry_digest'] == DIGEST
        assert manifest['secret'] == 'GHCR_READ_TOKEN' and manifest['owner_token_api_calls'] == 0
        assert not manifest['visibility_verified']
        cleanup = read(run / 'owner-auth-cleanup.json')
        assert cleanup['status'] == 'passed' and cleanup['removed'] and cleanup['outside_workspace']
        pull = read(run / 'owner-release-pull.json')
        assert pull['status'] == 'passed' and pull['reference'] == REFERENCE and pull['owner_token_api_calls'] == 0
        assert pull['preserved_digest'] and not pull['credential_file_copied'] and pull['local_copy_removed']
    for signature in run.rglob('*-release-signature-proof.json'):
        proof = read(signature)
        assert proof['status'] == 'passed' and proof['reference'] == REFERENCE
        release = read(run / 'release.json')
        assert proof['identity'] == release['signature']['identity'] and proof['issuer'] == release['signature']['issuer']
    for baseline in run.rglob('protected-baseline.json'):
        folder = baseline.parent
        protected = read(baseline)
        if not (folder / 'baseline-firmware-nvram.json').exists():
            incomplete.append(dict(stage=folder.relative_to(records).as_posix(), reason='Firmware baseline not reached'))
            continue
        initial = read(folder / 'baseline-firmware-nvram.json')
        assert initial['Boot0000'] == boot_variables(folder / 'pre-firmware-vars.fd')['Boot0000']
        assert firmware_baseline(initial, read(folder / 'baseline-firmware-devices.json')) == read(folder / 'baseline-firmware-firmware-ownership.json')['baseline']
        for capture in sorted(folder.glob('*-protected.json')):
            stage = capture.name.removesuffix('-protected.json')
            compare_disk(protected, read(capture))
            store = read(folder / (stage + '-nvram.json'))
            assert boot_variables(folder / (stage + '-vars.fd')) == store
            assert all_variables(folder / (stage + '-vars.fd')) == read(folder / (stage + '-all-variables.json'))
            assert store['Boot0000'] == initial['Boot0000']
            devices = read(folder / (stage + '-devices.json'))
            if devices['mode'] != 'live':
                assert bytes.fromhex(store['BootOrder']['hex'])[:2] == bytes(2), 'Windows not first'
            diff_path = folder / (stage + '-nvram-diff.json')
            if stage != 'baseline-firmware':
                if not diff_path.exists():
                    incomplete.append(dict(stage=capture.relative_to(records).as_posix(), reason='No accepted NVRAM diff'))
                else:
                    diff = read(diff_path)
                    previous = diff['from_stage']
                    esp = None
                    if (folder / (stage + '-target-efi.json')).exists():
                        esp, = [p for p in read(folder / (stage + '-target-efi.json'))['gpt']['partitions']
                                if p['type_guid'] == 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b']
                    computed = nvram_audit(read(folder / (previous + '-nvram.json')), store,
                        before_devices=read(folder / (previous + '-devices.json')), after_devices=devices,
                        target_esp=esp, windows_first=devices['mode'] != 'live')
                    assert diff == dict(from_stage=previous, **computed), (run.name, stage)
                    events.extend(dict(run=run.name, folder=folder.relative_to(run).as_posix(), stage=stage, **event)
                                  for event in computed['firmware_changes'])
            counter_stage = stage.removeprefix('switch-sequence-')
            if counter_stage.endswith('-pre-login-reset'):
                counter_stage = 'pre-login-reset'
            counter = folder / (counter_stage + '-blockstats.json')
            if counter.exists():
                protected_writes(read(counter))
                counters += 1
            else:
                incomplete.append(dict(stage=capture.relative_to(records).as_posix(), reason='No final write counter'))
            stages += 1
    for review in run.rglob('review-proof.json'):
        proof = read(review)
        validate_review(proof['tables'], proof['protected'], proof['target'])
    for keyboard in run.rglob('webui-keyboard-proof.json'):
        validate_keyboard_proof(read(keyboard))
    for probe in run.rglob('probe-result.json'):
        proof = read(probe)
        assert proof['status'] == 'passed' and proof['installed'] is False and proof['commit'] == metadata['head_sha']
        assert proof['firmware_rule'] == '11e-device-set'
        assert all(proof[k] for k in ('both_orders', 'review_validated', 'detached_windows', 'target_reset',
                                     'owner_auth_read_only', 'signature_verified'))
        assert metadata['conclusion'] == 'success'
        qualifications.append(dict(run=run.name, kind='probe', source=metadata['head_sha'], status='passed'))
    for full in run.rglob('full-result.json'):
        proof = read(full)
        assert proof['part_a'] == 'passed' and proof['both_orders']
        assert proof['part_b'] in ('passed', 'blocked')
        qualifications.append(dict(run=run.name, kind='full', source=metadata['head_sha'], **proof))
    print(run.name, metadata['conclusion'])

result = dict(matching_offline_stages=stages, zero_write_records=counters, archived_records_scanned=scanned,
              incomplete=incomplete, firmware_events=events, qualifications=qualifications)
(records / 'evidence-verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
if incomplete:
    print('Incomplete reached-stage evidence; qualification not established for those stages.')
    sys.exit(1)
print('Retained evidence verified; only explicit result files establish probe/full qualification.')
