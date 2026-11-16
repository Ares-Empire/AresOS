"""Mutation probes for brief 20-restore-lock-followups, in a disposable copy of control/.

Run from the repo root, as an ordinary user, no container:

    PYTHONDONTWRITEBYTECODE=1 python3 reviews/20-restore-lock-followups/mutations.py [prefix]

Each probe changes one file of a fresh copy under .work/ and runs each test
it names on its own. It counts as rejected only when every one of them fails
on an assertion. Every named test must pass on the unchanged copy first. The results go to
mutations.json beside this file (paths replaced by <copy>).

Why not reviews/20-chrome/mutation-audit.py: its harness runs with only
control and control/chrome_tests on the path, so it cannot import
control/tests' `support` (test_restore_batches) or control/mail_tests. The
Mail-suite tests also need the stand-in repro.py uses: the engine refuses
asking actions without a root-owned managed-settings file, which CI installs
in its container and the laptop must not get.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / '.work/20-restore-lock-followups-mutations'
# The Mail suite's stand-in for /etc/claude-code/managed-settings.json (repro.py).
MAIL = ("import json,sys,unittest;from pathlib import Path;from unittest.mock import patch;"
        "s=json.loads(Path('control/settings/managed-settings.draft.json').read_text());"
        "patch('aresos_control.boundary.Boundary.read',lambda self,path:s).start();"
        "unittest.main(module=None,argv=['probe','-v',*sys.argv[1:]])")
CASES = []


def case(item, file, before, after, *tests):
    CASES.append({'item': item, 'file': file, 'before': before, 'after': after, 'tests': list(tests)})


ORACLE = 'test_owner_state_oracle.OwnerOracle.'
SWEEP = 'mail:test_owner_state_sweep.OwnerStateSweep.'
BATCHES = 'test_restore_batches.RestoreBatches.'
S = 'control/aresos_control/storage.py'
D = 'control/owner_state_oracle/driver.py'
R = 'control/owner_state_oracle/records.py'
C = 'control/owner_state_oracle/compare.py'
W = 'control/mail_tests/test_owner_state_sweep.py'

# Item 1: a confirm that fails at its last disk sync keeps the running store locked.
case('item1-store-unlocks-in-finally', S,
     "        self.write(changes, 'control_restore_confirm',\n"
     "                   'owner confirmed restore; invalidated all earlier approvals', restoring=True)\n"
     "        self.locked = False\n",
     "        try:\n"
     "            self.write(changes, 'control_restore_confirm',\n"
     "                       'owner confirmed restore; invalidated all earlier approvals', restoring=True)\n"
     "        finally:\n"
     "            self.locked = False\n",
     BATCHES + 'test_confirm_whose_last_marker_sync_fails_keeps_the_lock_until_a_restart',
     BATCHES + 'test_confirm_whose_marker_stays_after_a_failed_sync_keeps_the_lock_until_a_restart')
case('item1-rule-removed', D,
     "    return bool(confirms) and bool(confirms[-1].get('faults', {}).get('trace'))\n",
     "    return False\n",
     ORACLE + 'test_interrupted_confirm_holds_until_the_next_restart',
     SWEEP + 'test_confirm_failed_at_its_last_point_keeps_the_lock_until_the_restart')
case('item1-rule-kept-after-restart', D,
     "        self.restart_index = len(self.oracle.script)\n", "",
     ORACLE + 'test_interrupted_confirm_holds_until_the_next_restart',
     SWEEP + 'test_confirm_failed_at_its_last_point_keeps_the_lock_until_the_restart')
case('item1-locked-precondition-dropped', D,
     " and call.get('restore_precondition') is True]\n", "]\n",
     ORACLE + 'test_interrupted_confirm_holds_until_the_next_restart')
case('item1-rule-accumulated', D,
     "        interrupted = interrupted_confirm(self.oracle.script[getattr(self, 'restart_index', 0):])\n",
     "        interrupted = self.record.interrupted_confirm or interrupted_confirm(self.oracle.script[getattr(self, 'restart_index', 0):])\n",
     ORACLE + 'test_interrupted_confirm_holds_until_the_next_restart')
case('item1-captured-record-changed', D,
     "            record = self.record = copy.copy(record)\n", "",
     ORACLE + 'test_interrupted_confirm_holds_until_the_next_restart')
case('item1-term-dropped-from-consistency', R,
     "        if (locked or service_lock(record)) != record.locked:\n",
     "        if (locked or any(seq <= record.startup_sequence for seq in record.unprepared_fences)) != record.locked:\n",
     ORACLE + 'test_interrupted_confirm_is_a_term_of_the_lock')
case('item1-harness-check-removed', W,
     "                raise AssertionError((case, 'A confirm that met a storage fault was answered ok; revisit the '\n",
     "                print((case, 'A confirm that met a storage fault was answered ok; revisit the '\n",
     SWEEP + 'test_harness_refuses_a_confirm_answered_ok_after_a_fault')
# Item 2: a refused read's stand-in page says locked exactly for the lock's refusal.
case('item2-lock-field-dropped', C,
     "                                   'restore_required': code == 'restore_required'})\n", "})\n",
     ORACLE + 'test_refused_read_page_says_locked_only_when_the_lock_refused_it',
     SWEEP + 'test_refused_log_under_the_lock_is_seen_as_locked')
case('item2-every-refusal-locked', C,
     "'restore_required': code == 'restore_required'})\n", "'restore_required': True})\n",
     ORACLE + 'test_refused_read_page_says_locked_only_when_the_lock_refused_it')


def run(test, target):
    if test.startswith('mail:'):
        argv, path = ['python3', '-B', '-c', MAIL, test.removeprefix('mail:')], 'control:control/mail_tests'
    else:
        argv, path = ['python3', '-B', '-m', 'unittest', '-v', test], 'control:control/tests'
    environment = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': path}
    result = subprocess.run(argv, cwd=target, env=environment, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=900)
    return result.returncode != 0, result.stdout


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else ''
    WORK.mkdir(parents=True, exist_ok=True)
    records = []
    with tempfile.TemporaryDirectory(dir=WORK) as temporary:
        target = Path(temporary)
        shutil.copytree(ROOT / 'control', target / 'control', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'test-work'))
        (target / '.work').mkdir()
        baselines = set()
        for row in [row for row in CASES if row['item'].startswith(prefix)]:
            for test in row['tests']:
                if test not in baselines:
                    failed, output = run(test, target)
                    if failed:
                        raise RuntimeError('Baseline failed ' + test + '\n' + output)
                    baselines.add(test)
            path = target / row['file']
            source = path.read_text()
            if source.count(row['before']) != 1:
                raise RuntimeError('Mutation does not apply exactly once ' + row['item'])
            results = {}
            try:
                path.write_text(source.replace(row['before'], row['after']))
                for test in row['tests']:
                    failed, output = run(test, target)
                    caught = failed and ('AssertionError' in output or 'FAIL:' in output)
                    lines = [line for line in output.replace(str(target), '<copy>').replace(str(ROOT), '<repo>').splitlines()
                             if line.startswith(('FAIL:', 'ERROR:', 'AssertionError', 'Ran ', 'FAILED'))]
                    results[test] = {'caught': caught, 'summary': lines}
                    if not caught:
                        raise RuntimeError('Mutation survived ' + row['item'] + ' in ' + test + '\n' + output)
            finally:
                path.write_text(source)
            records.append({'item': row['item'], 'file': row['file'], 'baseline': 'pass', 'rejected': True, 'tests': results})
            print(row['item'], 'REJECTED by', len(results), 'test(s)', flush=True)
    output = Path(__file__).with_name('mutations.json')
    previous = [] if not prefix or not output.exists() else [
        row for row in json.loads(output.read_text()) if not row['item'].startswith(prefix)]
    output.write_text(json.dumps(previous + records, indent=1) + '\n')
    print(f'{len(records)} mutations rejected by every named test; every baseline passed', flush=True)


if __name__ == '__main__':
    main()
