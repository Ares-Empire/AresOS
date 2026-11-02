"""Real read-only observer against modelled Linux /proc; no local sudo."""
import copy
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import owner_console as vc

TTY = 4 * 256 + 3
PTS = 136 * 256 + 2


def row(pid, ppid, pgrp, session, tty, tpgid, comm, args):
    return dict(pid=pid, ppid=ppid, pgrp=pgrp, session=session, tty=tty,
        tpgid=tpgid, comm=comm, args=args)


def relay():
    return [row(10, 1, 10, 10, TTY, 20, 'bash', ['-bash']),
        row(20, 10, 20, 10, TTY, 20, 'sudo', ['sudo', '-i']),
        row(21, 20, 21, 21, PTS, 22, 'sudo', ['sudo', '-i']),
        row(22, 21, 22, 21, PTS, 22, 'bash', ['-bash'])]


class SudoIdleTest(unittest.TestCase):
    def observe(self, rows):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as folder:
            proc = pathlib.Path(folder)
            for r in rows:
                p = proc / str(r['pid']); p.mkdir()
                fields = ['S', str(r['ppid']), str(r['pgrp']), str(r['session']),
                    str(r['tty']), str(r['tpgid'])] + ['0'] * 13 + ['12345']
                (p / 'stat').write_text(str(r['pid']) + ' (' + r['comm'] + ') ' + ' '.join(fields))
                (p / 'cmdline').write_bytes(b'\0'.join(a.encode() for a in r['args']) + b'\0')
            return vc.foreground_observation(TTY, proc)

    def test_plain_idle_bash_unchanged(self):
        self.assertTrue(self.observe([row(10, 1, 10, 10, TTY, 10, 'bash', ['-bash'])])['ready'])

    def test_exact_sudo_relay_to_idle_pts_bash(self):
        value = self.observe(relay())
        self.assertTrue(value['ready'])
        self.assertEqual([r['pid'] for r in value['foreground_chain']], [20, 21, 22])

    def test_busy_pts_bash_never_ready(self):
        rows = relay()
        rows[2]['tpgid'] = rows[3]['tpgid'] = 23
        rows.append(row(23, 22, 23, 21, PTS, 23, 'sleep', ['sleep', '300']))
        self.assertFalse(self.observe(rows)['ready'])

    def test_background_child_also_refuses(self):
        rows = relay() + [row(23, 22, 23, 21, PTS, 22, 'sleep', ['sleep', '300'])]
        self.assertFalse(self.observe(rows)['ready'])

    def test_unknown_foreground_redacts_argv(self):
        rows = relay(); rows[1].update(comm='python3', args=['python3', 'synthetic-hidden-input'])
        value = self.observe(rows)
        self.assertFalse(value['ready'])
        self.assertNotIn('synthetic-hidden-input', json.dumps(value))
        self.assertEqual(value['foreground_chain'][0]['argv'], ['[redacted]'])

    def test_two_candidates_refuse(self):
        rows = relay() + [row(23, 21, 23, 21, PTS, 22, 'bash', ['-bash'])]
        self.assertFalse(self.observe(rows)['ready'])

    def test_broken_chain_refuses(self):
        for index in (1, 2, 3):
            rows = relay(); del rows[index]
            self.assertFalse(self.observe(rows)['ready'])

    def test_exact_args_pts_session_and_group_links_fail_closed(self):
        for index, key, value in ((1, 'args', ['sudo', '-i', 'evil']),
                (1, 'args', ['sudo', '-i', '']), (2, 'args', ['sudo', '-s']), (3, 'args', ['bash', '-c', 'read']),
                (2, 'session', 10), (2, 'pgrp', 20), (3, 'tty', TTY),
                (3, 'session', 99), (3, 'pgrp', 99), (2, 'tpgid', 21)):
            rows = relay(); rows[index][key] = value
            with self.subTest(index=index, key=key):
                self.assertFalse(self.observe(rows)['ready'])

    def test_multiple_physical_groups_refuse(self):
        rows = relay() + [row(30, 1, 30, 30, TTY, 30, 'bash', ['-bash'])]
        self.assertFalse(self.observe(rows)['ready'])
        # Keep hidden-input detection waiting when the physical mapping cannot
        # be read, just as the original foreground reader did.
        from types import SimpleNamespace
        with patch.object(vc.os, 'fstat', return_value=SimpleNamespace(st_rdev=0)), \
                patch.object(vc.os, 'major', return_value=4, create=True), \
                patch.object(vc.os, 'minor', return_value=3, create=True), \
                patch.object(vc, 'foreground_observation', return_value=dict(ready=False,
                    reason='No unique physical foreground process group', foreground_chain=[])):
            diagnostic = {}
            with self.assertRaises(OSError): vc.foreground_is_shell(123, diagnostic)
            self.assertFalse(diagnostic['ready'])

    def test_changed_chain_cannot_grant_authority(self):
        rows = {r['pid']: dict(r, argv=[a.encode() for a in r.pop('args')], state='S', start='1') for r in copy.deepcopy(relay())}
        changed = copy.deepcopy(rows); changed[22]['tpgid'] = 23
        with patch.object(vc, 'process_snapshot', side_effect=[rows, changed]):
            self.assertFalse(vc.foreground_observation(TTY)['ready'])

    def test_qualification5_retained_observation_reproduces_old_rejection(self):
        fixture = json.loads((ROOT / 'os/tests/fixtures/owner-console/14ze-qualification5.json').read_text())
        self.assertEqual(fixture['run'], 40596167369)
        self.assertFalse(fixture['old_ready'])
        self.assertTrue(fixture['root_cursor_prompt'] and fixture['uart_done_zero'])
        self.assertFalse(vc.interactive_shell([b'sudo', b'-i']))
        self.assertTrue(self.observe(fixture['model_proc'])['ready'])
        self.assertEqual(fixture['process_tree_provenance'], 'model from verified pinned sudo source; PIDs not retained in qualification5')

    def test_account_and_sudo_completion_files_are_separate(self):
        import owner_vm as vm
        from unittest.mock import Mock
        guest = Mock(owner_input_epoch=0)
        from owner_console_shim import execute_echo
        guest.capture_json.side_effect=lambda name,source:execute_echo(source)
        console = vm.Console(guest)
        console.last_hidden=dict(login_timing=dict(within_half_timeout=True))
        with patch.object(console, 'after_hidden') as after, patch.object(console, 'hidden'), patch.object(console, 'send_hidden'), \
                patch.object(console, 'prompt'), patch.object(console, 'select'), \
                patch.object(vm, 'wait_tty'), patch.object(vm, 'type_text'),patch.object(vm.td,'save'), \
                patch.object(vm.owner_login,'Prepared') as prepared:
            prepared.return_value.rpc.return_value=dict(ready=True,echo_matches=True)
            console.login('synthetic-password', 'same-stage')
            console.become_root('synthetic-password', 'same-stage')
        self.assertEqual([c.args[0] for c in after.call_args_list],
            ['same-stage-account-login', 'same-stage-sudo'])

    def test_post_hidden_input_cannot_escape_in_refusal_diagnostics(self):
        rows = relay()
        rows[3]['args'] = ['bash', '-c', 'synthetic-hidden-input']
        value = self.observe(rows)
        self.assertFalse(value['ready'])
        self.assertNotIn('synthetic-hidden-input', json.dumps(value))
        self.assertTrue(value['foreground_chain'][-1]['argv_redacted'])


if __name__ == '__main__': unittest.main()
