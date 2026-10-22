import copy
import json
import pathlib
import unittest
from unittest.mock import patch


class DefaultStockTest(unittest.TestCase):
    def run_script(self, boot_index=1, corrupt=None, transaction_fails=False):
        checksum = 'a' * 64
        digest = 'sha256:' + 'b' * 64
        source = (pathlib.Path(__file__).resolve().parents[1] / 'release/default-stock.sh').read_text()
        source = source.split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
        source = source.replace('@STOCK_CHECKSUM@', checksum).replace('@BASE_DIGEST@', digest)
        stock = dict(ostree=dict(checksum=checksum), image=dict(imageDigest=digest,
                     image=dict(image='ghcr.io/ublue-os/bazzite-nvidia-open:stable')))
        status = {'status': dict(booted=stock)}
        deployments = [dict(checksum='c' * 64, booted=False), dict(checksum=checksum, booted=True)]
        if boot_index == 0:
            deployments.reverse()
        if corrupt:
            corrupt(status, deployments)
        after = copy.deepcopy(sorted(deployments, key=lambda d: not d.get('booted')))
        outputs = [json.dumps(status), json.dumps(dict(deployments=deployments)), json.dumps(dict(deployments=after))]
        with patch('subprocess.check_output', side_effect=outputs), patch('subprocess.run') as run:
            if transaction_fails:
                import subprocess
                run.side_effect = subprocess.CalledProcessError(1, ['ostree'])
            try:
                exec(compile(source, 'default-stock.sh', 'exec'), {})
            except Exception:
                self.last_calls = run.call_args_list
                raise
            return run.call_args_list

    def test_resolves_booted_stock_index_and_handles_already_default(self):
        for index in (0, 1):
            with self.subTest(index=index):
                calls = self.run_script(index)
                self.assertEqual(calls[0].args[0], ['ostree', 'admin', 'set-default', str(index)])
                self.assertEqual(calls[0].kwargs, {'check': True})

    def test_wrong_identity_or_staged_update_never_changes_default(self):
        cases = [lambda s, d: s['status']['booted']['ostree'].update(checksum='wrong'),
                 lambda s, d: s['status']['booted']['image'].update(imageDigest='wrong'),
                 lambda s, d: s['status']['booted']['image']['image'].update(image='wrong:stable'),
                 lambda s, d: d[0].update(staged=True),
                 lambda s, d: d[0].update(booted=True),
                 lambda s, d: d[1].update(checksum='wrong')]
        for corrupt in cases:
            with self.subTest(corrupt=corrupt), self.assertRaises(AssertionError):
                self.run_script(corrupt=corrupt)
            self.assertEqual(self.last_calls, [])

    def test_failed_transaction_stops_before_success_check(self):
        import subprocess
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_script(transaction_fails=True)
