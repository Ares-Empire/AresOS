"""Recheck retained 11d receipts, raw stores, per-stage exemptions and gates."""
import hashlib
import json
import pathlib
import re
import sys
import zipfile

root = pathlib.Path.cwd()
sys.path.insert(0, str(root / 'os/ci'))
from disk_audit import (compare_disk, protected_writes, compare_nvram, boot_variables,
                        all_variables, firmware_baseline)
from firmware_contract import check_source
from rehearsal_auth import REFERENCE, DIGEST
from installer_webui import validate_review, validate_keyboard_proof

records = root / 'os/manifest/ci/11d'
display_sources = {'usr_libexec_livesys_functions', 'usr_libexec_livesys_livesys-late',
                   'usr_libexec_livesys_livesys-main', 'usr_share_anaconda_interactive-defaults.ks'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def normalize(raw):
    return ('\n'.join(line.rstrip() for line in raw.decode('utf-8').splitlines()).rstrip() + '\n').encode()


stages = counters = scanned = 0
exemptions = []
missing = []
unreached_baselines = []
credential = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{25,}|\$(?:6|y)\$[^\s\x27\x22<>]{15,})')
for run in sorted(p for p in records.iterdir() if p.is_dir() and (p / 'run.json').exists()):
    metadata = read(run / 'run.json')
    receipt = read(run / 'workflow-logs.json')
    log_zip = root / 'reviews/11-two-disk-rehearsal/artifacts' / f'11d-{run.name}-workflow-logs.zip'
    assert len(log_zip.read_bytes()) == receipt['bytes']
    assert hashlib.sha256(log_zip.read_bytes()).hexdigest() == receipt['sha256']
    archives = [log_zip]
    for artifact in read(run / 'artifacts.json')['artifacts']:
        archive = root / 'reviews/11-two-disk-rehearsal/artifacts' / f'11d-{run.name}-{artifact["name"]}.zip'
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == artifact['digest'].split(':')[1]
        archives.append(archive)
        with zipfile.ZipFile(archive) as source:
            for name in source.namelist():
                if name.endswith('/') or name == 'installer/squashfs-files.txt' and not (run / name).exists():
                    continue
                actual, original = (run / name).read_bytes(), source.read(name)
                if pathlib.Path(name).suffix == '.txt' or pathlib.Path(name).name in display_sources:
                    assert normalize(actual) == normalize(original), (run.name, name)
                else:
                    assert actual == original, (run.name, name)
    for archive in archives:
        with zipfile.ZipFile(archive) as source:
            for name in source.namelist():
                raw = source.read(name)
                try:
                    raw.decode('utf-8')
                except UnicodeDecodeError:
                    continue
                assert not credential.search(raw), 'Unmasked credential pattern in archived evidence'
                scanned += 1
    if (run / 'firmware-contract-source.txt').exists():
        check_source((run / 'firmware-contract-source.txt').read_text(encoding='utf-8'))
    manifest = run / 'private-registry-preflight.json'
    if manifest.exists():
        value = read(manifest)
        assert value['reference'] == REFERENCE and value['secret'] == 'GHCR_READ_TOKEN'
        assert value['owner_token_api_calls'] == 0
        if value['status'] == 'passed':
            assert value['registry_digest'] == DIGEST
        cleanup = read(run / 'owner-auth-cleanup.json')
        assert cleanup['status'] == 'passed' and cleanup['removed'] and cleanup['outside_workspace']
    pull = run / 'owner-release-pull.json'
    if pull.exists():
        value = read(pull)
        assert value['reference'] == REFERENCE and value['status'] == 'passed'
        assert value['preserved_digest'] and not value['credential_file_copied'] and value['local_copy_removed']
    for signature in run.rglob('*-release-signature-proof.json'):
        value = read(signature)
        assert value['status'] == 'passed' and value['reference'] == REFERENCE
        assert value['identity'] == read(run / 'release.json')['signature']['identity']
    for baseline in run.rglob('protected-baseline.json'):
        folder = baseline.parent
        protected = read(baseline)
        if not (folder / 'baseline-firmware-nvram.json').exists():
            unreached_baselines.append(str(folder.relative_to(records)))
            assert metadata['conclusion'] != 'success', 'Successful run missing firmware baseline'
            continue
        baseline_nvram = read(folder / 'baseline-firmware-nvram.json')
        assert baseline_nvram['Boot0000'] == boot_variables(folder / 'pre-firmware-vars.fd')['Boot0000']
        ownership = firmware_baseline(baseline_nvram, read(folder / 'baseline-firmware-devices.json'))
        assert ownership == read(folder / 'baseline-firmware-firmware-ownership.json')['baseline']
        for capture in sorted(folder.glob('*-protected.json')):
            stage = capture.name.removesuffix('-protected.json')
            compare_disk(protected, read(capture))
            nvram = read(folder / (stage + '-nvram.json'))
            assert boot_variables(folder / (stage + '-vars.fd')) == nvram
            assert all_variables(folder / (stage + '-vars.fd')) == read(folder / (stage + '-all-variables.json'))
            assert nvram['Boot0000'] == baseline_nvram['Boot0000']
            diff_path = folder / (stage + '-nvram-diff.json')
            if diff_path.exists():
                diff = read(diff_path)
                previous = diff['from_stage']
                target = folder / (stage + '-target-efi.json')
                esp = None
                if target.exists():
                    esp, = [p for p in read(target)['gpt']['partitions'] if p['type_guid'] == 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b']
                observed = compare_nvram(read(folder / (previous + '-nvram.json')), nvram,
                    before_devices=read(folder / (previous + '-devices.json')),
                    after_devices=read(folder / (stage + '-devices.json')), target_esp=esp)
                assert observed == diff['changes']
                allowed = {n: c['firmware_owned'] for n, c in observed.items() if 'firmware_owned' in c}
                assert allowed == diff['exemptions']
                for name, change in allowed.items():
                    exemptions.append(dict(run=run.name, order=folder.name, stage=stage, option=name, **change))
            else:
                assert stage == 'baseline-firmware', 'Missing per-stage NVRAM diff'
            counter_stage = stage.removeprefix('switch-sequence-')
            if counter_stage.endswith('-pre-login-reset'):
                counter_stage = 'pre-login-reset'
            counter = folder / (counter_stage + '-blockstats.json')
            if counter.exists():
                protected_writes(read(counter))
                counters += 1
            else:
                missing.append(str(capture.relative_to(records)))
            stages += 1
    for proof in run.rglob('probe-result.json'):
        value = read(proof)
        assert value['status'] == 'passed' and value['installed'] is False
        assert value['commit'] == metadata['head_sha']
        assert all(value[key] for key in ('both_orders', 'review_validated', 'detached_windows', 'target_reset'))
    for review in run.rglob('review-proof.json'):
        value = read(review)
        validate_review(value['tables'], value['protected'], value['target'])
    for keyboard in run.rglob('webui-keyboard-proof.json'):
        validate_keyboard_proof(read(keyboard))
    print(run.name, metadata['conclusion'])
result = dict(matching_offline_stages=stages, zero_write_records=counters,
              missing_counters=missing, unreached_baselines=unreached_baselines, exemptions=exemptions, archived_text_credential_checks=scanned)
(records / 'evidence-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
assert not missing, 'Missing counters are not zero-write evidence'
print('Evidence consistency verified; only explicit probe/full result files establish qualification.')
