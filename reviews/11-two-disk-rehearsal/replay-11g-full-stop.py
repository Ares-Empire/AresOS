"""Bind the mandatory keyboard-proof stop to retained source and raw evidence."""
import hashlib
import json
import pathlib
import re
import subprocess

root = pathlib.Path.cwd()
records = root / 'os/manifest/ci/11g'
source = '909fe5a1d54345af550588ea926800930102c168'
full = records / 'full-3/two-disk'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


failure = (full / 'webui-keyboard-proof.txt').read_text(encoding='utf-8')
failure = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', failure)
assert 'AssertionError: Conversion did not restore live settings' in failure
assert 'KEYBOARD_BEFORE_IMPORT' in failure and 'as 1 "de"' in failure
assert not (full / 'webui-keyboard-proof.json').exists()
assert not (full / 'protected-first-install-result.json').exists()
assert not list(full.glob('*pin-stock*')) and not list(full.glob('*stock-pin*'))
probe = records / 'probe-3/two-disk'
for folder in (probe, probe / 'protected-second'):
    keyboard = read(folder / 'webui-keyboard-proof.json')
    assert 'failed to load module mpath' in (folder / 'webui-keyboard-proof.txt').read_text(encoding='utf-8')
    assert keyboard['live_configuration_restored'] and keyboard['module_configuration_unchanged']
    assert keyboard['xlayouts'] == ['de'] and keyboard['resolved_keymap'] == 'de'
    assert re.search(r'^KEYMAP="?de"?$', keyboard['generated_vconsole'], re.M)
assert read(probe / 'probe-result.json')['commit'] == source
counter = read(full / 'protected-first-install-failure-counter.json')
assert counter['failure_path'] and not counter['probe_only'] and counter['vm_paused']
assert counter['status'] == 'recorded' and counter['boot'] == 2
stats, = [s['stats'] for s in read(full / counter['counter']) if s.get('device') == 'protected']
assert stats['wr_bytes'] == stats['wr_operations'] == 0
assert read(full / 'protected-baseline.json') == read(full / 'protected-first-install-protected.json')
diff = read(full / 'protected-first-install-nvram-diff.json')
assert not diff['changes'] and not diff['firmware_changes'] and not diff['linux_position_changes']
assert diff['order_before'] == diff['order_after'] and diff['order_after'][0] == 'Boot0000'
events = read(full / 'protected-first-install-qmp.json')
assert [e['data'] for e in events if e['event'] == 'SHUTDOWN'] == [
    dict(guest=True, reason='guest-shutdown'), dict(guest=False, reason='host-qmp-quit')]
assert any(e['event'] == 'STOP' for e in events)
paths = [full / name for name in ('webui-keyboard-proof.txt', 'protected-first-install-failure-counter.json',
         counter['counter'], 'protected-baseline.json', 'protected-first-install-protected.json',
         'protected-first-install-nvram-diff.json', 'protected-first-install-qmp.json',
         'baseline-firmware-vars.fd', 'protected-first-install-vars.fd')]
paths += [folder / name for folder in (probe, probe / 'protected-second')
          for name in ('webui-keyboard-proof.json', 'webui-keyboard-proof.txt')]
paths += [root / 'reviews/11-two-disk-rehearsal/artifacts' / ('11g-full-3-' + name + '.zip')
          for name in ('two-disk-evidence', 'workflow-logs')]
inputs = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
for name in ('os/ci/installer_webui.py', 'os/ci/two_disk_vm.py', 'os/ci/switch_vm.py'):
    inputs[name] = hashlib.sha256(subprocess.check_output(['git', 'show', source + ':' + name])).hexdigest()
result = dict(status='stopped', qualified=False, run=40066161000, source=source,
    stop_rule='11b: full failure on a probe-covered check; no fourth full dispatch',
    failure='webui-keyboard-proof: Conversion did not restore live settings',
    probe_passed_same_check_both_orders=True, actual_before_after_localed_values='not retained; root cause unverified',
    libbd_mpath_warning='also present in both passing probe orders; causality not established',
    installation_started=False, installed_stock_prepare_reached=False,
    staged_update_observed=None, staged_update_discarded=None,
    actual_failure_counter=counter, protected_writes=dict(bytes=0, operations=0),
    protected_sha256=read(full / 'protected-baseline.json')['sha256'],
    windows_entry_and_order_unchanged=True, firmware_events=0, linux_position_events=0,
    part_a='not qualified', part_b='untested', part_c='pins retained', inputs=inputs)
(records / 'full-stop-analysis.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
print('PROBE-COVERED STOP CONFIRMED: no install; failure counter recorded before QMP quit; zero protected writes.')
