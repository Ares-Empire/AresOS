import contextlib
import io
import hashlib
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import test_stock_prepare as prepare


DAEMON = dict(pid=101, exe='/usr/bin/rpm-ostree',
              cmdline=['rpm-ostree', 'start-daemon'],
              cgroup='0::/system.slice/rpm-ostreed.service\n', excluded_as_daemon=True, excluded_as_system_helper=False)
CLIENT = dict(pid=202, exe='/usr/bin/bootc', cmdline=['bootc', 'upgrade'],
              cgroup='0::/user.slice/session-1.scope\n', excluded_as_daemon=False, excluded_as_system_helper=False)


class StockIdleTest(unittest.TestCase):
    def execute(self, processes, transactions=(None,), stuck_unit=False, legacy=False):
        scope, units, active, calls, read, run = prepare.StockPauseTest().environment()
        if legacy:
            fixture = prepare.ROOT / 'os/tests/fixtures/11i-pause-stock-updates.sh'
            self.assertEqual(hashlib.sha256(fixture.read_bytes()).hexdigest(), 'b7f45a54b0a19b959f848c51fd85e3905ba4d2d5ce2a802765d2ef37a2738ab5')
            source = fixture.read_text()
            exec(compile(source.split("<<'PAUSE_STOCK'\n", 1)[1].split('\nPAUSE_STOCK', 1)[0], '11i-pause', 'exec'), scope)
        pending = iter(transactions)
        last = transactions[-1]
        def output(command, **kwargs):
            if command[0] == 'rpm-ostree':
                return json.dumps(dict(transaction=next(pending, last)))
            if stuck_unit and 'show' in command and 'uupd.service' in command:
                return 'LoadState=masked\nActiveState=active\nSubState=running\n'
            return read(command, **kwargs)
        def command(argv, **kwargs):
            if argv == ['rpm-ostree', 'cancel']:
                calls.append(argv)
                return Mock(returncode=0, stdout='Cancelling transaction: upgrade\nCancelled.\n', stderr='')
            if argv[0] == 'pgrep':
                return Mock(returncode=0 if any(pathlib.Path(p['exe']).name == argv[-1] for p in processes) else 1)
            return run(argv, **kwargs)
        log = io.StringIO()
        error = None
        with patch('subprocess.check_output', side_effect=output), patch('subprocess.run', side_effect=command), \
             patch.dict(scope, deployment_processes=lambda: processes), \
             patch('time.monotonic', side_effect=range(0, 2000, 100)), patch('time.sleep'), contextlib.redirect_stdout(log):
            try:
                scope['pause_stock']()
            except (SystemExit, AssertionError) as caught:
                error = caught
        return log.getvalue(), calls, error

    def receipt(self, text, marker):
        return json.loads(next(line.split(' ', 1)[1] for line in text.splitlines() if line.startswith(marker + ' ')))

    def test_only_realistic_daemon_is_idle_and_same_regression_fails_on_11i(self):
        text, calls, error = self.execute([DAEMON])
        self.assertIsNone(error)
        proof = self.receipt(text, 'ARESOS_STOCK_UPDATERS_PAUSED')['decision']
        self.assertTrue(proof['units_inactive'] and proof['transaction_idle'] and proof['clients_idle'])
        self.assertEqual(proof['processes'], [DAEMON])
        self.assertFalse(proof['cancel']['ran'])
        _, _, old_error = self.execute([DAEMON], legacy=True)
        self.assertIsNotNone(old_error, 'The exact 11i name-only check must fail this daemon-only regression')
        self.assertIn('did not become idle', str(old_error))

    def test_bootc_client_waits_then_stops_naming_process(self):
        text, _, error = self.execute([DAEMON, CLIENT])
        self.assertIsNotNone(error)
        result = self.receipt(text, 'ARESOS_STOCK_PAUSE_STOP')
        self.assertEqual(result['false_predicates'], ['clients_idle'])
        self.assertEqual(result['decision']['processes'][1], CLIENT)

    def test_leftover_transaction_cancelled_once_then_idle_passes(self):
        transaction = ['upgrade', ':1.42', 'unix:path=/run/rpm-ostree/txn']
        text, calls, error = self.execute([DAEMON], (transaction, None))
        self.assertIsNone(error)
        self.assertEqual(calls.count(['rpm-ostree', 'cancel']), 1)
        self.assertEqual(self.receipt(text, 'ARESOS_STOCK_CANCEL_REQUEST')['transaction'], transaction)
        result = self.receipt(text, 'ARESOS_STOCK_UPDATERS_PAUSED')['decision']
        self.assertEqual(result['cancel']['transaction'], transaction)
        self.assertTrue(result['cancel']['ran'])
        self.assertIsNone(result['transaction'])

    def test_persistent_transaction_stops_and_names_it_without_second_cancel(self):
        transaction = ['upgrade', ':1.42', 'unix:path=/run/rpm-ostree/txn']
        text, calls, error = self.execute([DAEMON], (transaction,))
        self.assertIsNotNone(error)
        self.assertEqual(calls.count(['rpm-ostree', 'cancel']), 1)
        result = self.receipt(text, 'ARESOS_STOCK_PAUSE_STOP')
        self.assertEqual(result['false_predicates'], ['transaction_idle'])
        self.assertEqual(result['decision']['transaction'], transaction)

    def test_stuck_unit_stops_naming_unit(self):
        text, _, error = self.execute([DAEMON], stuck_unit=True)
        self.assertIsNotNone(error)
        result = self.receipt(text, 'ARESOS_STOCK_PAUSE_STOP')
        self.assertEqual(result['false_predicates'], ['units_inactive'])
        unit, = [u for u in result['decision']['units'] if u['ActiveState'] == 'active']
        self.assertEqual((unit['name'], unit['SubState']), ('uupd.service', 'running'))

    def test_proc_exe_cmdline_cgroup_not_comm_decides_clients(self):
        scope = {}
        exec(compile(prepare.program(prepare.PAUSE, 'PAUSE_STOCK'), str(prepare.PAUSE), 'exec'), scope)
        with tempfile.TemporaryDirectory(dir=prepare.ROOT / 'os/tests') as directory:
            root = pathlib.Path(directory)
            for row in (DAEMON, CLIENT, dict(DAEMON, pid=303, cgroup='0::/system.slice/rpm-ostreed.service-evil\n'),
                        dict(DAEMON, pid=404, exe='/usr/bin/ostree', cmdline=['ostree', 'admin', 'deploy']),
                        dict(DAEMON, pid=505, cmdline=['rpm-ostree', 'upgrade'])):
                proc = root / str(row['pid'])
                proc.mkdir()
                (proc / 'exe').write_text(row['exe'])
                (proc / 'cmdline').write_bytes(('\0'.join(row['cmdline']) + '\0').encode())
                (proc / 'cgroup').write_text(row['cgroup'])
            with patch.object(pathlib.Path, 'readlink', lambda path: pathlib.PurePosixPath(path.read_text())):
                result = scope['deployment_processes'](root)
        self.assertEqual([p['excluded_as_daemon'] for p in result], [True, False, False, False, False])
        self.assertEqual(result[:2], [DAEMON, CLIENT])


if __name__ == '__main__':
    unittest.main()
