"""Re-evaluate retained firmware stores under the explicit 11f decision."""
import hashlib
import json
import pathlib
import sys

root = pathlib.Path.cwd()
sys.path.insert(0, str(root / 'os/ci'))
from disk_audit import boot_variables, nvram_audit


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


results = []
for name, folder, previous in (
    ('11b-first-order', '11b/probe-11/two-disk', 'baseline-firmware'),
    ('11d-first-order', '11d/probe-3/two-disk', 'live-ui-probe'),
    ('11e-full-install', '11e/full-1/two-disk', 'protected-first-install'),
    ('11d-reverse-order', '11d/probe-3/two-disk/protected-second', 'live-ui-probe'),
):
    directory = root / 'os/manifest/ci' / folder
    stages = (previous, 'after-install-without-linux' if name == '11e-full-install' else 'probe-windows-without-linux')
    inputs = {}
    stores = []
    for stage in stages:
        raw = directory / (stage + '-vars.fd')
        inputs[raw.relative_to(root).as_posix()] = hashlib.sha256(raw.read_bytes()).hexdigest()
        value = boot_variables(raw)
        assert value == read(directory / (stage + '-nvram.json'))
        stores.append(value)
    if name == '11b-first-order':
        historical = read(root / 'os/manifest/ci/11c/probe-11-regression.json')
        devices = [historical['before_devices'], historical['after_devices']]
        context = historical['hardware_context']
    else:
        devices = []
        for stage in stages:
            path = directory / (stage + '-devices.json')
            devices.append(read(path))
            inputs[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        context = 'Original per-boot QMP PCI/SATA record; no label-based attachment inference'
    esp = None
    if name == '11e-full-install':
        path = directory / (previous + '-target-efi.json')
        inputs[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        esp, = [p for p in read(path)['gpt']['partitions'] if p['type_guid'] == 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b']
    audit = nvram_audit(*stores, before_devices=devices[0], after_devices=devices[1], target_esp=esp)
    if name == '11e-full-install':
        assert [(e['option'], e['old_index'], e['new_index']) for e in audit['linux_position_changes']] == [('Boot000A', 0, 1)]
        assert {(e['before_option'], e['after_option']) for e in audit['firmware_changes']} == {('Boot0002', None), ('Boot0004', None)}
    else:
        assert not audit['linux_position_changes']
    expected = 3 if name == '11d-reverse-order' else 2
    assert len(audit['firmware_changes']) == expected
    results.append(dict(name=name, status='passed', inputs=inputs, hardware_context=context, **audit))
    print(name, 'passed;', expected, 'device changes')

destination = root / 'os/manifest/ci/11f'
destination.mkdir(parents=True, exist_ok=True)
(destination / 'firmware-set-replays.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
