"""Bind both-order A success and the exact, unmodified Part B selector refusal."""
import ast
import hashlib
import json
import pathlib
import re
import subprocess
import sys

root = pathlib.Path('os/manifest/ci/11k')
full = root / 'full-5'
source = '2524823323888128a114866a2e1888f921e531cc'
inputs = []


def read(path):
    inputs.append(path)
    return json.loads(path.read_text())


sys.path.insert(0, 'os/ci')
from rehearsal_guard import job_minutes
from disk_audit import protected_writes
from keyboard_proof import validate_installed_keyboard

metadata = read(full / 'run.json')
assert metadata['conclusion'] == 'success' and metadata['head_sha'] == source
authorization = read(full / '11c-dispatch-authorization.json')
assert authorization['probe_run'] == '40117290487' and authorization['full_dispatched'] == 5
assert authorization['probe']['commit'] == source and authorization['consumed_minutes'] == 498
assert authorization['reserved_minutes'] == 182 and not authorization['read_retries']
result = read(full / 'two-disk/full-result.json')
assert result == dict(part_a='passed', both_orders=True, installed_keyboard_both_orders=True,
                     part_b='blocked', part_b_evidence='protected-second/grub-promotion.json')
for folder, order in ((full / 'two-disk', 'protected-first'),
                      (full / 'two-disk/protected-second', 'protected-second')):
    keyboard = read(folder / 'installed-keyboard-result.json')
    assert keyboard['root'] == '/' and keyboard['order'] == order
    assert keyboard['context'] == 'first installed stock root shell'
    assert validate_installed_keyboard(read(folder / 'installed-keyboard-files.json'), [])['status'] == 'passed'
    recovery = read(folder / 'result.json')
    assert recovery['status'] == 'passed' and recovery['stock_default_second_boot']
    assert recovery['recovery_admin_logged_out'] and recovery['recovery_admin_tty'] == '/dev/tty3'
    assert recovery['inherited_homebrew_daily_denied'] and recovery['inherited_homebrew_owner_working_all_stages']
    assert recovery['partition_identity_unchanged'] and recovery['stock_greeter_rendered']
    for name in ('first-stock-pin-result.json', 'pin-stock-result.json'):
        pin = read(folder / name)
        assert pin['booted_checksum'] == recovery['retained_stock_checksum']
        assert pin['pinned'] and pin['no_staged'] and not pin['staged_discarded'] and pin['discarded'] is None

reverse = full / 'two-disk/protected-second'
stock = read(reverse / 'result.json')['retained_stock_checksum']
blocked = read(reverse / 'grub-promotion.json')
assert blocked['status'] == 'blocked'
entries = read(reverse / 'b-bls-entries.json')
assert entries == blocked['entries']
matches = [entry for entry in entries if stock in entry['deployment']]
assert len(matches) == 1 and matches[0]['id'] == 'ostree-1'
assert {e['id'] for e in entries} == {'ostree-1', 'ostree-2'}
code = subprocess.check_output(['git', 'show', source + ':os/ci/two_disk_vm.py'])
node = next(n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == 'stock_bls_entry')
scope = {'re': re}
exec(compile(ast.Module(body=[node], type_ignores=[]), source + ':stock_bls_entry', 'exec'), scope)
assert scope['stock_bls_entry'](entries, stock) is None
assert not re.fullmatch(r'ostree-([1-9][0-9]*)-[A-Za-z0-9_.-]+', matches[0]['id'])
assert not (reverse / 'b-recovered-stock-devices.json').exists()
assert not (reverse / 'b-unattended-stock-devices.json').exists()
protected_writes(read(reverse / 'b-unresolved-menu-blockstats.json'))
events = read(reverse / 'b-menu-preparation-qmp.json')
assert any(e.get('event') == 'STOP' for e in events)
assert any(e.get('event') == 'SHUTDOWN' and e.get('data') == dict(guest=True, reason='guest-shutdown') for e in events)
assert not any(e.get('event') == 'SHUTDOWN' and e.get('data', {}).get('reason') == 'host-signal' for e in events)

verification = read(root / 'evidence-verification.json')
assert verification['matching_offline_stages'] == verification['zero_write_records'] == 32
assert not verification['incomplete'] and len(verification['pause_decisions']) == 7
for pause in verification['pause_decisions']:
    decision = pause['decision']
    assert pause['status'] == 'passed' and len(decision['units']) == 14
    assert all((u['ActiveState'], u['SubState']) == ('inactive', 'dead') for u in decision['units'])
    assert all(decision[k] for k in ('units_inactive', 'transaction_idle', 'clients_idle'))
    assert decision['transaction'] is None and not decision['cancel']['ran']
    process, = decision['processes']
    assert process['exe'] == '/usr/bin/rpm-ostree' and process['cmdline'] == ['rpm-ostree', 'start-daemon']
    assert process['cgroup'] == '0::/system.slice/rpm-ostreed.service\n' and process['excluded_as_daemon']

before = read(root / 'before-full-budget.json')
after = read(root / 'after-full-budget.json')
cost = sum(job_minutes(job) for job in read(full / 'jobs.json')['jobs'])
assert cost == 113 and before['consumed_minutes'] == 498
assert after['consumed_minutes'] == 611 == 498 + cost and after['full_dispatched'] == 5
assert after['cap'] == 750 and after['reserved_minutes'] == 14
assert read(full / 'owner-auth-cleanup.json')['removed']
assert read(full / 'private-registry-preflight.json')['owner_token_api_calls'] == 0

for name in ('os/ci/rehearsal_guard.py', 'os/ci/two_disk_vm.py', 'os/ci/stock_probe.py',
             'os/release/pause-stock-updates.sh', 'os/release/pin-stock.sh', 'os/ci/disk_audit.py',
             '.github/workflows/os-image.yml', '.github/workflows/privacy-check.yml', '.gitleaks.toml'):
    path = pathlib.Path(name)
    assert path.read_bytes().replace(b'\r\n', b'\n') == subprocess.check_output(['git', 'show', source + ':' + name])
    inputs.append(path)
analysis = dict(source=source, part_a='passed-both-orders', installed_keyboard='German-both-orders',
                pause_receipts=7, each_selected_units=14, daemon_seen_excluded=7, cancel_commands=0,
                staged_observed_at_pin=False, staged_discarded=False, part_b='blocked-before-menu-selection',
                checksum_matching_stock_entries=1, accepted_by_published_id_rule=0, matching_stock_id='ostree-1',
                blocker='Published selector requires a nonempty OS-name suffix; actual Anaconda BLS IDs are bare. Its not-unique message means zero accepted candidates, not two competing stock entries.',
                runtime_unchanged=True, no_selector_fix=True, no_sixth_full=True,
                measured_minutes=611, full_runs=5,
                inputs=[dict(path=p.as_posix(), sha256=hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()) for p in inputs],
                hash_convention='Git canonical LF text; compare staged/committed blob bytes')
(root / 'full-analysis.json').write_text(json.dumps(analysis, indent=2) + '\n', encoding='utf-8', newline='\n')
print('11k full replay passed: A both orders/German/pause/pin passed; B has one stock match but zero accepted IDs; 611 minutes / 5 full.')
