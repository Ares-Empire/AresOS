"""Verify retained 11n receipts and every reached offline/QMP/firmware gate."""
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
                        nvram_audit, protected_writes, automatic_options, ordered_options, check_boot_next, linux_entry)
from firmware_contract import check_source
from installer_webui import validate_keyboard_proof, validate_review
from keyboard_proof import validate_installed_keyboard
from rehearsal_auth import DIGEST, REFERENCE
from grub_bls import stock_bls_entry, confirm_menu_ocr
from switch_vm import booted_digest, booted_reference, inspect_transaction

records = root / 'os/manifest/ci/11n'
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
pause_decisions = []
bootnext_checks = []
guard_histories = []
nonboot_events = []
global_boot = re.compile(r'8be4df61-93ca-11d2-aa0d-00e098032b8c/Boot(?:Order|Next|[0-9A-F]{4})')
historical_nonboot = set()
for path in pathlib.Path('os/manifest/ci/11k').rglob('*-all-variables-diff.json'):
    historical_nonboot.update(key for key in read(path) if not global_boot.fullmatch(key))
assert historical_nonboot == {'605dab50-e046-4300-abb6-3dd810dd8b23/MokTimeout',
    '605dab50-e046-4300-abb6-3dd810dd8b23/SbatLevel', 'eb704011-1402-11d3-8e77-00a0c969723b/MTC',
    'fab7e9e1-39dd-4f2b-8408-e20e906cb6de/HDDP'}


def bootnext_context(folder, stage, devices, store, esp):
    authorization = read(folder / f'boot-{devices["boot"]}-bootnext.json')
    assert read(folder / f'boot-{devices["boot"]}-devices.json') == devices
    assert authorization['for_boot'] == devices['boot'] and authorization['mode'] == devices['mode']
    assert authorization['order'] == devices['order'] and type(authorization['written']) is bool
    prepared = authorization['prepared_store']
    assert prepared['Boot0000'] == store['Boot0000']
    selected = authorization if authorization['written'] else None
    check_boot_next(prepared, authorization=selected, consumed=False, target_esp=esp)
    if selected:
        assert devices['mode'] == 'installed' and authorization['purpose'] != 'stock'
        assert authorization['destination'] != 'Boot0000' and linux_entry(prepared[authorization['destination']], esp)
    else:
        assert authorization['destination'] is None and authorization['value'] is None and 'BootNext' not in prepared
        if devices['mode'] == 'installed':
            assert authorization['purpose'] == 'stock' and linux_entry(prepared[ordered_options(prepared)[0]], esp)
    if devices['mode'].startswith('marker'):
        assert not selected and ordered_options(prepared)[0] == ordered_options(store)[0] == 'Boot0000'
    windows_default = not (stage == 'baseline-firmware' or devices['mode'] == 'live' or
                           stage == 'stock-before-windows' or stage.endswith('-pre-login-reset'))
    computed = check_boot_next(store, authorization=selected, windows_default=windows_default, target_esp=esp)
    assert read(folder / (stage + '-bootnext-audit.json')) == dict(**computed, boot=devices['boot'],
             authorization=f'boot-{devices["boot"]}-bootnext.json', windows_default=windows_default)
    bootnext_checks.append(dict(folder=folder.relative_to(records).as_posix(), stage=stage,
        boot=devices['boot'], purpose=authorization['purpose'], written=authorization['written'],
        destination=authorization['destination'], windows_default=windows_default, **computed))
    return windows_default


for run in sorted(p for p in records.iterdir() if p.is_dir() and (p / 'run.json').exists()):
    metadata = read(run / 'run.json')
    receipt = read(run / 'workflow-logs.json')
    log = root / 'reviews/11-two-disk-rehearsal/artifacts' / f'11n-{run.name}-workflow-logs.zip'
    assert len(log.read_bytes()) == receipt['bytes']
    assert hashlib.sha256(log.read_bytes()).hexdigest() == receipt['sha256']
    scanned += check_archive(log)
    if (run / '11c-dispatch-authorization.json').exists():
        authorization = read(run / '11c-dispatch-authorization.json')
        history = authorization['history']
        assert history['complete'] and history['snapshot_reads'] == 1
        assert len(history['run_ids']) == len(set(history['run_ids'])) == history['ids_count'] == history['total_count']
        assert history['pages_read'] == len(history['pages']) and 1 <= history['pages_read'] <= history['page_limit'] == 20
        assert metadata['id'] in history['run_ids']
        offset = 0
        for number, page in enumerate(history['pages'], 1):
            batch = history['run_ids'][offset:offset + 100]
            assert page['page'] == number and page['returned'] == len(batch) and page['total_count'] == len(history['run_ids'])
            assert page['ids_sha256'] == hashlib.sha256(json.dumps(batch, separators=(',', ':')).encode()).hexdigest()
            offset += len(batch)
        assert offset == history['total_count']
        guard_histories.append(dict(run=run.name, pages=history['pages_read'], ids=history['ids_count'],
              total_count=history['total_count'], retries=authorization['read_retries']))
    for artifact in read(run / 'artifacts.json')['artifacts']:
        archive = root / 'reviews/11-two-disk-rehearsal/artifacts' / f'11n-{run.name}-{artifact["name"]}.zip'
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
            current_esp = None
            if (folder / (stage + '-target-efi.json')).exists():
                current_esp, = [p for p in read(folder / (stage + '-target-efi.json'))['gpt']['partitions']
                                if p['type_guid'] == 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b']
            windows_default = bootnext_context(folder, stage, devices, store, current_esp)
            if windows_default:
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
                                        windows_first=windows_default)
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
                    old_variables = read(folder / (previous + '-all-variables.json'))
                    new_variables = read(folder / (stage + '-all-variables.json'))
                    raw_diff = {name: dict(before=old_variables.get(name), after=new_variables.get(name))
                                for name in old_variables.keys() | new_variables.keys()
                                if old_variables.get(name) != new_variables.get(name)}
                    assert read(folder / (stage + '-all-variables-diff.json')) == raw_diff
                    nonboot = sorted(key for key in raw_diff if not global_boot.fullmatch(key))
                    assert set(nonboot) <= historical_nonboot, 'PLAN-GAP: new nonboot firmware change; stop/report'
                    nonboot_events.append(dict(run=run.name, stage=stage, keys=nonboot))
                    esp = None
                    if (folder / (stage + '-target-efi.json')).exists():
                        esp, = [p for p in read(folder / (stage + '-target-efi.json'))['gpt']['partitions']
                                if p['type_guid'] == 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b']
                    computed = nvram_audit(read(folder / (previous + '-nvram.json')), store,
                        before_devices=read(folder / (previous + '-devices.json')), after_devices=devices,
                        target_esp=esp, windows_first=windows_default)
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
        assert files['root'] == proof['root'] == '/' and proof['context'] == 'first installed stock root shell'
        devices = read(installed.parent / 'stock-before-windows-devices.json')
        assert devices['mode'] == 'installed' and proof['boot'] == devices['boot'] and proof['order'] == devices['order']
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
        assert proof['stock_idle_source_verified']
        assert proof['idle_source']['daemon_comm'] == 'rpm-ostree'
        assert proof['idle_source']['versions'] == {'rpm-ostree': '2026.3', 'uupd': '1.5.0'}
        assert proof['temporary_grubenv_bare_id']
        assert proof['idle_source']['bootloader_versions'] == {'ostree': '2026.4-1.fc44', 'grub2-common': '2.12-66.fc44'}
    for transcript in run.rglob('*.txt'):
        if transcript.name not in ('first-stock-pause.txt', 'first-stock-pin.txt', 'pin-stock.txt', 'b-pin-stock.txt'):
            continue
        clean = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', transcript.read_text(encoding='utf-8')).replace('\r', '')
        for line in clean.splitlines():
            if not line.startswith(('ARESOS_STOCK_UPDATERS_PAUSED ', 'ARESOS_STOCK_PAUSE_STOP ')):
                continue
            proof = json.loads(line.split(' ', 1)[1])
            decision = proof['decision']
            assert all(k in decision for k in ('units', 'transaction', 'processes', 'cancel', 'units_inactive', 'transaction_idle', 'clients_idle'))
            if proof['status'] == 'passed':
                assert decision['transaction_observed'] and decision['transaction'] is None
                assert all(decision[k] for k in ('units_inactive', 'transaction_idle', 'clients_idle'))
                assert all(u['ActiveState'] in ('inactive', 'failed') and 'SubState' in u for u in decision['units'])
                assert all(p['excluded_as_daemon'] for p in decision['processes'])
                for process in decision['processes']:
                    assert process['pid'] > 0 and process['cmdline']
                    assert pathlib.PurePosixPath(process['exe'].removesuffix(' (deleted)')).name in ('bootc', 'rpm-ostree')
                    groups = [line.split(':', 2)[2] for line in process['cgroup'].splitlines()]
                    excluded = any(g == '/system.slice/rpm-ostreed.service' or
                                   g.startswith('/system.slice/rpm-ostreed.service/') for g in groups)
                    assert process['excluded_as_daemon'] == excluded
            if decision['cancel']['ran']:
                assert decision['cancel']['transaction'] is not None
            pause_decisions.append(dict(run=run.name, path=transcript.relative_to(run).as_posix(), **proof))
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
                                     'owner_auth_read_only', 'signature_verified', 'stock_recipe_probe', 'failure_counter_probe', 'read_only_keyboard_proof', 'installed_keyboard_reader_probe', 'part_b_tools_probe', 'stock_idle_source_verified', 'bootnext_checked', 'bootloader_source_verified'))
        assert metadata['conclusion'] == 'success'
        for folder in (probe.parent, probe.parent / 'protected-second'):
            assert read(folder / 'stock-recipe-probe.json')['real_unit_pause_twice']
            assert read(folder / 'keyboard-reader-probe-result.json')['fixture_only']
            assert read(folder / 'part-b-tool-probe.json')['ocr_executed']
            assert read(folder / 'cached-stock-cli-probe.json')['part_b_cli_help']
            assert read(folder / 'cached-stock-cli-probe.json')['status'] == 'passed'
            counter_proof = read(folder / 'failure-counter-probe-failure-counter.json')
            assert counter_proof['status'] == 'recorded' and counter_proof['vm_paused'] and counter_proof['probe_only']
        qualifications.append(dict(run=run.name, kind='probe', source=metadata['head_sha'], status='passed'))
    for part_b in run.rglob('part-b-result.json'):
        assert metadata['conclusion'] == 'success', 'Part B result requires a successful completed job'
        proof = read(part_b)
        folder = part_b.parent
        assert proof['commit'] == metadata['head_sha'] and proof['order'] == 'protected-second'
        assert proof['part_b'] in ('passed', 'blocked')
        assert all(proof[k] for k in ('installed_keyboard_german', 'first_stock_firmware_default',
            'windows_default_after_first_login_pin', 'unattended_windows_marker', 'detached_windows_marker'))
        assert proof['rollback_and_default_undo_repeated'] is False
        assert proof['part_a_evidence'] == '11k full40119526154; both orders; earlier Windows-first timing'
        required = ['baseline-firmware', 'protected-second-install', 'stock-before-windows',
                    'after-first-login-default-windows', 'after-install-without-linux', 'b-switch', 'b-menu-preparation']
        promotion = read(folder / proof['part_b_evidence'])
        assert promotion['status'] == proof['part_b']
        if proof['part_b'] == 'passed':
            required += ['b-recovered-stock', 'b-unattended-stock']
        for stage in required:
            devices = read(folder / (stage + '-devices.json'))
            assert devices['order'] == 'protected-second'
            assert (folder / (stage + '-protected.json')).exists()
            assert (folder / (stage + '-bootnext-audit.json')).exists()
            if stage != 'baseline-firmware':
                assert (folder / (stage + '-nvram-diff.json')).exists()
        pin = read(folder / 'first-stock-pin-result.json')
        stock = pin['booted_checksum']
        assert read(folder / 'b-pin-stock-result.json')['booted_checksum'] == stock
        assert read(folder / 'installed-keyboard-result.json')['status'] == 'passed'
        restore = read(folder / 'after-first-login-pin-windows-order.json')
        assert restore['status'] == 'passed'
        stock_boot = read(folder / 'stock-before-windows-devices.json')['boot']
        windows_boot = read(folder / 'after-first-login-default-windows-devices.json')['boot']
        assert stock_boot < windows_boot
        stock_authorization = read(folder / f'boot-{stock_boot}-bootnext.json')
        assert not stock_authorization['written'] and stock_authorization['purpose'] == 'stock'
        for stage in ('after-first-login-default-windows', 'after-install-without-linux'):
            devices = read(folder / (stage + '-devices.json'))
            authorization = read(folder / f'boot-{devices["boot"]}-bootnext.json')
            assert not authorization['written']
            marker = (folder / (stage + '-marker.txt')).read_text()
            assert 'ARESOS_WINDOWS_MARKER BootCurrent=0000' in marker
            baseline = read(folder / 'protected-baseline.json')
            assert baseline['gpt']['partitions'][0]['guid'].lower() in marker.lower()
        release = read(run / 'release.json')
        inspect_transaction(read(folder / 'b-switch-inspection.json'), release['reference'], stock)
        ares = read(folder / 'b-aresos-status.json')
        assert booted_reference(ares) == release['reference'] and booted_digest(ares) == release['reference'].split('@')[1]
        order = read(folder / 'b-aresos-order.json')['deployments']
        assert order[0]['booted'] and order[0]['checksum'] != stock
        if proof['part_b'] == 'passed':
            backup = stock_bls_entry(read(folder / 'b-bls-entries.json'), stock, order)
            assert read(folder / 'b-recorded-stock-entry.json') == backup
            attempts = sorted(folder.glob('b-grub-menu-attempt-*-ocr.txt'))
            assert attempts and all(p.with_name(p.name.removesuffix('-ocr.txt') + '.png').exists() for p in attempts)
            if (folder / 'b-grub-selection.json').exists():
                selection = read(folder / 'b-grub-selection.json')
                assert selection == dict(**read(folder / 'b-grub-menu-ocr-proof.json'),
                    keys=['home'] + ['down'] * backup['menu_index'] + ['ret'])
                confirmed = []
                for index, attempt in enumerate(attempts):
                    if index == 0:
                        continue
                    def lines(path):
                        return [re.sub(r'\s+', ' ', line.strip()) for line in path.read_text().splitlines()
                                if re.search(r'Bazzite.*ostree', line, re.I)]
                    if lines(attempt) and lines(attempt) == lines(attempts[index - 1]):
                        confirmed.append(confirm_menu_ocr(attempt.read_text(), backup))
                assert read(folder / 'b-grub-menu-ocr-proof.json') in confirmed
                assert (folder / 'b-grub-recorded-stock-selected.png').exists()
                assert promotion['path'].startswith('QMP Home, Down ')
            else:
                assert promotion['path'].startswith('grub2-reboot fallback after QMP ')
                assert (folder / 'b-one-time-fallback.txt').exists()
                assert 'next_entry=' + backup['id'] in (folder / 'b-one-time-fallback.txt').read_text()
            recovered = read(folder / 'b-recovered-stock-status.json')
            recovered_order = read(folder / 'b-recovered-stock-order.json')['deployments']
            assert recovered['status']['booted']['ostree']['checksum'] == stock
            assert booted_digest(recovered) == release['base'].split('@')[1]
            assert not recovered_order[0]['booted'] and recovered_order[0]['checksum'] != stock
            assert any(d['checksum'] == stock and d.get('booted') for d in recovered_order[1:])
            final = read(folder / 'b-unattended-stock-status.json')
            final_order = read(folder / 'b-unattended-stock-order.json')['deployments']
            assert final['status']['booted']['ostree']['checksum'] == stock and booted_digest(final) == release['base'].split('@')[1]
            assert final_order[0]['checksum'] == stock and final_order[0]['booted']
            assert not final['status'].get('staged') and not final['status'].get('rollbackQueued')
            assert promotion['recorded_stock_checksum'] == stock and promotion['stock_previous_index'] == backup['menu_index']
            assert promotion['stock_now_booted_first'] and promotion['unattended_second_boot']
            assert (folder / 'b-unattended-stock.png').exists()
        else:
            assert promotion['reason']
        qualifications.append(dict(run=run.name, kind='part-b', source=metadata['head_sha'], **proof))
    assert not list(run.rglob('full-result.json')), 'No ordinary full run is allowed in11n'
    print(run.name, metadata['conclusion'])

result = dict(matching_offline_stages=stages, zero_write_records=counters, archived_records_scanned=scanned,
              incomplete=incomplete, firmware_events=events, linux_position_events=linux_events,
              windows_order_actions=order_actions, pause_decisions=pause_decisions, qualifications=qualifications)
result.update(bootnext_checks=bootnext_checks, guard_histories=guard_histories, nonboot_events=nonboot_events)
(records / 'evidence-verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
if incomplete:
    print('Incomplete reached-stage evidence; qualification not established for those stages.')
    sys.exit(1)
print('Retained evidence verified; only explicit result files establish probe/full qualification.')
