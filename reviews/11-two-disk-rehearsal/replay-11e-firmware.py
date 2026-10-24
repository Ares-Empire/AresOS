"""Re-evaluate retained firmware stores under the explicit 11e decision."""
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
    ('11d-reverse-order', '11d/probe-3/two-disk/protected-second', 'live-ui-probe'),
):
    directory = root / 'os/manifest/ci' / folder
    stages = (previous, 'probe-windows-without-linux')
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
    audit = nvram_audit(*stores, before_devices=devices[0], after_devices=devices[1])
    expected = 3 if name == '11d-reverse-order' else 2
    assert len(audit['firmware_changes']) == expected
    results.append(dict(name=name, status='passed', inputs=inputs, hardware_context=context, **audit))
    print(name, 'passed;', expected, 'device changes')

destination = root / 'os/manifest/ci/11e'
destination.mkdir(parents=True, exist_ok=True)
(destination / 'firmware-set-replays.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
