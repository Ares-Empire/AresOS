"""Verify retained 11i receipts and every reached offline/QMP/firmware gate."""
import base64
import hashlib
import json
import pathlib
import re
import struct
import sys
import zipfile

root = pathlib.Path.cwd()
sys.path.insert(0, str(root / 'os/ci'))
from disk_audit import (all_variables, boot_variables, compare_disk, firmware_baseline,
                        nvram_audit, protected_writes, automatic_options, ordered_options)
from firmware_contract import check_source
from installer_webui import validate_keyboard_proof, validate_review
from keyboard_proof import validate_installed_keyboard
from rehearsal_auth import DIGEST, REFERENCE

records = root / 'os/manifest/ci/11i'
display_sources = {'usr_libexec_livesys_functions', 'usr_libexec_livesys_livesys-late',
                   'usr_libexec_livesys_livesys-main', 'usr_share_anaconda_interactive-defaults.ks'}
# crypt hashes are ASCII. Excluding whitespace alone mistakes compressed PNG
# bytes after an accidental "$6$" for a password hash; binary token scans stay on.
credential = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{25,}|\$(?:6|y)\$[./A-Za-z0-9$=]{15,})')


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
linux_events = []
incomplete = []
qualifications = []
order_actions = []
for run in sorted(p for p in records.iterdir() if p.is_dir() and (p / 'run.json').exists()):
    metadata = read(run / 'run.json')
    receipt = read(run / 'workflow-logs.json')
    log = root / 'reviews/11-two-disk-rehearsal/artifacts' / f'11i-{run.name}-workflow-logs.zip'
    assert len(log.read_bytes()) == receipt['bytes']
    assert hashlib.sha256(log.read_bytes()).hexdigest() == receipt['sha256']
    scanned += check_archive(log)
    for artifact in read(run / 'artifacts.json')['artifacts']:
        archive = root / 'reviews/11-two-disk-rehearsal/artifacts' / f'11i-{run.name}-{artifact["name"]}.zip'
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
                    failure = dict(stage=capture.relative_to(records).as_posix(), reason='No accepted NVRAM diff')
                    predecessors = [p for p in folder.glob('*-devices.json') if not p.name.startswith('boot-')
                                    and read(p)['boot'] == devices['boot'] - 1]
                    if len(predecessors) == 1:
                        previous = predecessors[0].name.removesuffix('-devices.json')
                        before = read(folder / (previous + '-nvram.json'))
                        previous_devices = read(predecessors[0])
                        target_path = folder / (previous + '-target-efi.json')
                        esp = None
                        if target_path.exists():
                            esp, = [p for p in read(target_path)['gpt']['partitions']
                                    if p['type_guid'] == 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b']
                        try:
                            nvram_audit(before, store, before_devices=previous_devices,
                                        after_devices=devices, target_esp=esp,
                                        windows_first=devices['mode'] != 'live')
                        except AssertionError as error:
                            failure['reason'] = str(error)
                        else:
                            raise AssertionError('Missing accepted diff for a passing stage')
                        auto_before = automatic_options(before, previous_devices)
                        auto_after = automatic_options(store, devices)
                        changes = {name: dict(before=before.get(name), after=store.get(name))
                                   for name in sorted(before.keys() | store.keys()) if before.get(name) != store.get(name)}
                        paths = [folder / (s + suffix) for s in (previous, stage)
                                 for suffix in ('-vars.fd', '-devices.json')]
                        analysis = dict(status='failed', qualified=False, error=failure['reason'],
                            before_stage=previous, after_stage=stage, raw_changes=changes,
                            firmware_before=auto_before, firmware_after=auto_after,
                            order_before=ordered_options(before), order_after=ordered_options(store),
                            non_auto_before=[n for n in ordered_options(before) if n not in auto_before],
                            non_auto_after=[n for n in ordered_options(store) if n not in auto_after],
                            windows_entry_identical=before['Boot0000'] == store['Boot0000'],
                            windows_first_after=ordered_options(store)[0] == 'Boot0000',
                            target_efi=read(target_path) if target_path.exists() else None,
                            before_devices=previous_devices, after_devices=devices,
                            inputs={p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
                        (records / 'full-stop-analysis.json').write_text(json.dumps(analysis, indent=2) + '\n', encoding='utf-8')
                    incomplete.append(failure)
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
                    linux_events.extend(dict(run=run.name, folder=folder.relative_to(run).as_posix(), stage=stage,
                        order_before=computed['order_before'], order_after=computed['order_after'], **event)
                        for event in computed['linux_position_changes'])
            counter_stage = stage.removeprefix('switch-sequence-')
            if counter_stage.endswith('-pre-login-reset'):
                counter_stage = 'pre-login-reset'
            # Part B audits the recovered-stock session after its promotion reboot.
            # The final counter uses the actual reboot command's stage name.
            if stage == 'b-recovered-stock' and not (folder / (counter_stage + '-blockstats.json')).exists():
                counter_stage = 'b-promote-recorded-stock'
            if stage == 'b-menu-preparation' and (folder / 'b-unresolved-menu-blockstats.json').exists():
                counter_stage = 'b-unresolved-menu'
            counter = folder / (counter_stage + '-blockstats.json')
            failure_receipt = folder / (counter_stage + '-failure-counter.json')
            final = True
            if failure_receipt.exists():
                failure = read(failure_receipt)
                assert failure['failure_path'] and not failure['probe_only']
                assert failure['boot'] == devices['boot']
                assert failure['counter'] == counter.name
                final = failure['status'] == 'recorded' and failure['vm_paused']
                if not final:
                    incomplete.append(dict(stage=capture.relative_to(records).as_posix(),
                        reason='Failure-path final counter unavailable or VM pause unconfirmed',
                        intermediate_counter_retained=counter.exists()))
            if counter.exists():
                protected_writes(read(counter))
                if final:
                    counters += 1
            else:
                incomplete.append(dict(stage=capture.relative_to(records).as_posix(), reason='No final write counter'))
            stages += 1
    for review in run.rglob('review-proof.json'):
        proof = read(review)
        validate_review(proof['tables'], proof['protected'], proof['target'])
    for keyboard in run.rglob('webui-keyboard-proof.json'):
        validate_keyboard_proof(read(keyboard))
    receipt = read(run / 'installer/localization-source.json') if (run / 'installer/localization-source.json').exists() else None
    for keyboard in run.rglob('webui-keyboard-proof.json'):
        proof = read(keyboard)
        expected, = [item['sha256'] for item in receipt['sources'] if item['path'].endswith('/installation.py')]
        assert proof['installation_source_sha256'] == expected
        interface, = [item['sha256'] for item in receipt['sources'] if item['path'].endswith('/localization_interface.py')]
        assert proof['interface_source_sha256'] == interface and proof['switch_options_property'] == 'LayoutSwitchOptions'
    for installed in run.rglob('installed-keyboard-result.json'):
        proof = read(installed)
        choices = read(installed.parent / 'webui-keyboard-proof.json')
        files = read(installed.parent / 'installed-keyboard-files.json')
        computed = validate_installed_keyboard(files, choices['layout_switching_options'])
        assert files['root'] == '/' and proof['context'] == 'first installed stock root shell'
        assert all(proof[key] == value for key, value in computed.items())
    for fixture in run.rglob('keyboard-reader-probe-result.json'):
        proof = read(fixture)
        assert proof['fixture_only'] and proof['installed'] is False
        validate_installed_keyboard(read(fixture.parent / 'keyboard-reader-probe-files.json'), proof['expected_options'])
    for action in run.rglob('*-windows-order.json'):
        proof = read(action)
        before, after = proof['before'], proof['after']
        order = ordered_options(before)
        expected = ['Boot0000'] + [n for n in order if n != 'Boot0000']
        raw = struct.pack('<' + 'H' * len(expected), *(int(n[4:], 16) for n in expected)).hex()
        assert proof['status'] == 'passed'
        assert after == dict(before, BootOrder=dict(before['BootOrder'], hex=raw))
        order_actions.append(dict(run=run.name, path=action.relative_to(run).as_posix(),
                                  before=order, after=ordered_options(after)))
    for probe_receipt in run.rglob('failure-counter-probe-failure-counter.json'):
        proof = read(probe_receipt)
        assert proof['status'] == 'recorded' and proof['failure_path'] and proof['probe_only'] and proof['vm_paused']
        protected_writes(read(probe_receipt.parent / proof['counter']))
    for cached in run.rglob('cached-stock-cli-probe.json'):
        proof = read(cached)
        assert proof['status'] == 'passed' and proof['digest'] == read(run / 'release.json')['base'].split('@', 1)[1]
        assert proof['pull'] == 'never' and proof['network'] == 'none' and proof['read_only']
        assert not proof['owner_credentials_mounted']
    for recipe in run.rglob('stock-recipe-probe.json'):
        proof = read(recipe)
        assert proof['status'] == 'passed' and proof['tools_and_help'] and proof['real_unit_pause_twice']
    for pin in run.rglob('*pin-stock-result.json'):
        proof = read(pin)
        assert proof['status'] == 'passed' and proof['pinned'] and proof['no_staged']
        assert proof['booted_digest'] == 'sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151'
        assert proof['staged_discarded'] == (proof['discarded'] is not None)
        if proof['discarded']:
            assert 'ghcr.io/ublue-os/bazzite-nvidia-open' in proof['discarded']['reference']
    for pin in run.rglob('first-stock-pin-result.json'):
        proof = read(pin)
        assert proof['status'] == 'passed' and proof['pinned'] and proof['no_staged']
        state = read(pin.parent / 'first-stock-ready-status.json')['status']
        assert state['booted']['ostree']['checksum'] == proof['booted_checksum']
        assert state['booted']['image']['imageDigest'] == proof['booted_digest']
        assert state['booted']['pinned'] and not state.get('staged')
    for probe in run.rglob('probe-result.json'):
        proof = read(probe)
        assert proof['status'] == 'passed' and proof['installed'] is False and proof['commit'] == metadata['head_sha']
        assert proof['firmware_rule'] == '11f-linux-position'
        assert all(proof[k] for k in ('both_orders', 'review_validated', 'detached_windows', 'target_reset',
                                     'owner_auth_read_only', 'signature_verified', 'stock_recipe_probe', 'failure_counter_probe', 'read_only_keyboard_proof', 'installed_keyboard_reader_probe'))
        assert metadata['conclusion'] == 'success'
        for folder in (probe.parent, probe.parent / 'protected-second'):
            assert read(folder / 'stock-recipe-probe.json')['real_unit_pause_twice']
            assert read(folder / 'keyboard-reader-probe-result.json')['fixture_only']
            assert read(folder / 'cached-stock-cli-probe.json')['status'] == 'passed'
            counter_proof = read(folder / 'failure-counter-probe-failure-counter.json')
            assert counter_proof['status'] == 'recorded' and counter_proof['vm_paused'] and counter_proof['probe_only']
        qualifications.append(dict(run=run.name, kind='probe', source=metadata['head_sha'], status='passed'))
    for full in run.rglob('full-result.json'):
        proof = read(full)
        assert proof['part_a'] == 'passed' and proof['both_orders'] and proof['installed_keyboard_both_orders']
        assert proof['part_b'] in ('passed', 'blocked')
        folders = [full.parent, full.parent / 'protected-second']
        for folder, order in zip(folders, ('protected-first', 'protected-second')):
            required = ['baseline-firmware', order + '-install', 'stock-before-windows', 'after-install-without-linux',
                        *('switch-sequence-' + s for s in ('stock', 'aresos', 'rollback', 'persistent-stock')),
                        'before-undo-windows', 'after-undo-default-windows', 'after-undo-without-linux']
            for stage in required:
                assert (folder / (stage + '-protected.json')).exists(), (order, stage)
                if stage != 'baseline-firmware':
                    assert (folder / (stage + '-nvram-diff.json')).exists(), (order, stage)
            for stage in ('after-install', 'undo'):
                assert read(folder / (stage + '-windows-order.json'))['status'] == 'passed'
            assert read(folder / 'result.json')['status'] == 'passed'
            assert read(folder / 'installed-keyboard-result.json')['status'] == 'passed'
            for pin_name in ('first-stock-pin-result.json', 'pin-stock-result.json'):
                assert read(folder / pin_name)['booted_checksum'] == read(folder / 'result.json')['retained_stock_checksum']
            for stage in ('after-install-without-linux', 'before-undo-windows',
                          'after-undo-default-windows', 'after-undo-without-linux'):
                marker = (folder / (stage + '-marker.txt')).read_text()
                assert 'ARESOS_WINDOWS_MARKER BootCurrent=0000' in marker
                assert protected['gpt']['partitions'][0]['guid'].lower() in marker.lower()
        promotion = read(full.parent / proof['part_b_evidence'])
        assert promotion['status'] == proof['part_b']
        if proof['part_b'] == 'passed':
            assert promotion['stock_now_booted_first'] and promotion['unattended_second_boot']
            for stage in ('b-switch', 'b-menu-preparation', 'b-recovered-stock', 'b-unattended-stock'):
                assert (folders[1] / (stage + '-nvram-diff.json')).exists(), stage
        qualifications.append(dict(run=run.name, kind='full', source=metadata['head_sha'], **proof))
    print(run.name, metadata['conclusion'])

result = dict(matching_offline_stages=stages, zero_write_records=counters, archived_records_scanned=scanned,
              incomplete=incomplete, firmware_events=events, linux_position_events=linux_events,
              windows_order_actions=order_actions, qualifications=qualifications)
(records / 'evidence-verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
if incomplete:
    print('Incomplete reached-stage evidence; qualification not established for those stages.')
    sys.exit(1)
print('Retained evidence verified; only explicit result files establish probe/full qualification.')
