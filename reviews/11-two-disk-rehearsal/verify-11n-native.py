"""Prove the entire native suite passed on the source before any VM probe."""
import hashlib
import json
import pathlib
import re
import zipfile

root = pathlib.Path('os/manifest/ci/11n')
run = root / 'native-1'
metadata = json.loads((run / 'run.json').read_text())
assert metadata['id'] == 40136982269 and metadata['head_sha'] == '46dc2dd1f62d3a3d4d8051e3ac3b06eb30db4760'
assert metadata['conclusion'] == 'success' and metadata['status'] == 'completed'
assert metadata['display_title'] == 'OS regressions only (no VM)' and metadata['run_attempt'] == 1
jobs = json.loads((run / 'jobs.json').read_text())['jobs']
job, = [j for j in jobs if j['conclusion'] != 'skipped']
assert job['name'] == 'Regression checks only (no image build or VM)' and job['conclusion'] == 'success'
assert all(j['conclusion'] == 'skipped' for j in jobs if j != job)
assert all(s['conclusion'] == 'success' for s in job['steps'])
path = pathlib.Path('reviews/11-two-disk-rehearsal/artifacts/11n-native-1-workflow-logs.zip')
assert hashlib.sha256(path.read_bytes()).hexdigest() == json.loads((run / 'workflow-logs.json').read_text())['sha256']
with zipfile.ZipFile(path) as archive:
    name, = [n for n in archive.namelist() if '/' in n and '_Run regression and syntax checks' in n]
    text = archive.read(name).decode('utf-8-sig')
assert 'Ran 201 tests in 3.621s' in text and re.search(r'Z OK\r?$', text, re.M)
assert not re.search(r'Z (?:FAIL|ERROR):|Z FAILED \(', text)
passed = re.findall(r'Z test_[^\n]+ \(([^)]+)\) \.\.\. ok\r?$', text, re.M)
assert len(passed) == len(set(passed)) == 201
local = json.loads((root / 'local-tests.json').read_text())
assert set(local['wsl_unavailable']) <= set(passed)
assert 'test_shell_assertions.ShellAssertionTest.test_install_transactions_stop_on_failure_and_never_include_the_reboot' in passed
assert 'test_shell_assertions.ShellAssertionTest.test_owner_switch_prerequisites_stop_before_the_transaction' in passed
result = dict(status='passed', run=metadata['id'], source=metadata['head_sha'], native_tests=201,
              seconds=3.621, all_local_limitations_covered=True, no_vm=True, no_owner_token=True,
              all_tests=passed, job_started=job['started_at'], job_completed=job['completed_at'],
              workflow_logs_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
(root / 'native-proof.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
print('Native source46dc2dd: complete201 tests/3.621s/OK; every local limitation covered; other jobs skipped, no VM/token. Syntax and native job passed before probe.')
