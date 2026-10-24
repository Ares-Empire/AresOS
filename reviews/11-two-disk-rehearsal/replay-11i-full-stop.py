"""Bind 11i's installed-stock refusal to original evidence and the tested source."""
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import zipfile

ROOT = pathlib.Path.cwd()
sys.path.insert(0, str(ROOT / 'os/ci'))
from disk_audit import compare_disk, protected_writes
from installer_webui import validate_keyboard_proof
SOURCE = 'f1a237dda5c11cf3e981b97fbf026eef2384ddb1'
RECORDS = ROOT / 'os/manifest/ci/11i'
RUN = RECORDS / 'full-4'
FULL = RUN / 'two-disk'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def clean(path):
    return re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', path.read_text(encoding='utf-8'))


failure = clean(FULL / 'first-stock-pause.txt')
assert 'STOP: stock updaters could not be paused.' in failure
assert 'Updater/deployment transaction did not become idle' in failure
assert "Removed '/etc/systemd/system/timers.target.wants/uupd.timer'." in failure
assert 'ARESOS_STOCK_UPDATERS_PAUSED' not in failure
source = subprocess.check_output(['git', 'show', SOURCE + ':os/release/pause-stock-updates.sh']).decode()
assert 'deadline = time.monotonic() + 300' in source
assert "if inactive and status.get('transaction') is None and all(p.returncode == 1 for p in clients):" in source
assert not list(FULL.glob('installed-keyboard*'))
assert not list(FULL.glob('first-stock-pin*')) and not (FULL / 'first-stock-ready-status.json').exists()
assert not (FULL / 'full-result.json').exists() and not (FULL / 'protected-second').exists()
assert not (FULL / 'part-a-result.json').exists()
install = read(FULL / 'protected-first-install-result.json')
assert install['status'] == 'passed' and install['target'] == 'vdb'
assert (FULL / 'installation-complete.png').exists()
keyboard = read(FULL / 'webui-keyboard-proof.json')
validate_keyboard_proof(keyboard)
assert keyboard['layout_switching_options'] == [] and keyboard['read_only']
assert 'live_configuration_restored' not in keyboard
assert read(RUN / 'run.json')['head_sha'] == SOURCE
assert read(RUN / 'run.json')['conclusion'] == 'failure'
authorization = read(RUN / '11c-dispatch-authorization.json')
assert authorization['probe_run'] == '40103660846'
assert authorization['probe']['commit'] == SOURCE and authorization['probe']['part_b_tools_probe']

baseline = read(FULL / 'protected-baseline.json')
captures = sorted(FULL.glob('*-protected.json'))
assert len(captures) == 4
for capture in captures:
    compare_disk(baseline, read(capture))
counter = read(FULL / 'stock-before-windows-failure-counter.json')
assert counter['failure_path'] and not counter['probe_only'] and counter['vm_paused']
assert counter['status'] == 'recorded' and counter['boot'] == 4
stats = read(FULL / counter['counter'])
protected_writes(stats)
protected, = [item['stats'] for item in stats if item.get('device') == 'protected']
assert protected['wr_bytes'] == protected['wr_operations'] == 0
assert read(FULL / 'stock-before-windows-devices.json')['boot'] == counter['boot']
events = read(FULL / 'stock-before-windows-qmp.json')
stop = next(i for i, event in enumerate(events) if event['event'] == 'STOP')
shutdown = next(i for i, event in enumerate(events) if event['event'] == 'SHUTDOWN')
assert stop < shutdown and events[shutdown]['data'] == dict(guest=False, reason='host-signal')
assert not read(FULL / 'stock-before-windows-nvram-diff.json')['changes']
assert not read(FULL / 'stock-before-windows-nvram-diff.json')['firmware_changes']
assert read(FULL / 'stock-initialization-reboot.json')['count'] == 1
cleanup = read(RUN / 'owner-auth-cleanup.json')
assert cleanup['status'] == 'passed' and cleanup['removed'] and cleanup['outside_workspace']
assert read(RUN / 'private-registry-preflight.json')['owner_token_api_calls'] == 0
assert read(RUN / 'owner-release-pull.json')['owner_token_api_calls'] == 0

paths = [FULL / name for name in ('first-stock-pause.txt', 'webui-keyboard-proof.json',
    'protected-first-install-result.json', 'installation-complete.png', 'protected-baseline.json',
    'stock-before-windows-failure-counter.json', counter['counter'], 'stock-before-windows-qmp.json',
    'stock-before-windows-devices.json', 'stock-before-windows-nvram-diff.json', 'stock-initialization-reboot.json')]
paths += captures
paths += [ROOT / 'reviews/11-two-disk-rehearsal/artifacts' / ('11i-full-4-' + suffix + '.zip')
          for suffix in ('two-disk-evidence', 'workflow-logs')]
inputs = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
for name in ('os/ci/keyboard_proof.py', 'os/ci/installer_webui.py', 'os/ci/two_disk_vm.py',
             'os/ci/switch_vm.py', 'os/ci/rehearsal_guard.py', 'os/ci/stock_probe.py',
             'os/release/pause-stock-updates.sh', 'os/release/pin-stock.sh'):
    inputs[name] = hashlib.sha256(subprocess.check_output(['git', 'show', SOURCE + ':' + name])).hexdigest()
result = dict(status='STOP', qualified=False, run=40105647808, source=SOURCE,
    passing_probe=40103660846, first_installation='passed', first_stock_login='reached after one known initialization reboot',
    failure='first-stock-pause: 300-second idle conjunction did not become true',
    idle_predicates=['all selected units inactive/failed', 'rpm-ostree transaction is null', 'no bootc/rpm-ostree clients'],
    actual_failed_predicate='not exported; cannot distinguish unit, transaction or client from retained output',
    timer_disable_observed=True, installed_keyboard_check='not reached: placed after mandatory first pause',
    installed_stock_pin='not reached', staged_update_observed=None, staged_update_discarded=None,
    part_a='not qualified', reverse_full='not reached', part_b='untested',
    protected_sha256=baseline['sha256'], matching_full_captures=4,
    failure_counter=counter, protected_writes=dict(bytes=0, operations=0),
    failure_shutdown='QMP paused, counter recorded, then host signal; not an orderly guest shutdown',
    no_fifth_full=True, owner_token_api_calls=0, inputs=inputs)
(RECORDS / 'full-stop-analysis.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print('STOCK PAUSE STOP CONFIRMED: first install passed; no installed keyboard/pin/switch result; final paused failure counter zero before host termination.')
