"""Unchanged session facts, modelled /proc, and a real unprivileged pts."""
import contextlib
import copy
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_owner_tools as common

ROOT, owner = common.ROOT, common.owner
TTY3, TTY4, PTS = 1027, 1028, 34818


class Model:
    def __init__(self, tty='tty3', name='/dev/pts/2', pts=PTS):
        self.tty, self.name, self.pts = tty, name, pts
        self.scope, self.audit, self.loginuid = '7', '7', '1000'
        self.cgroup = '0::/user.slice/user-1000.slice/session-7.scope\n'
        self.rows = {
            40: dict(ppid=22, session=21, tty=pts, comm='python3', exe='/usr/bin/python3'),
            22: dict(ppid=21, session=21, tty=pts, comm='bash', exe='/usr/bin/bash'),
            21: dict(ppid=20, session=21, tty=pts, comm='sudo', exe='/usr/bin/sudo'),
            20: dict(ppid=10, session=10, tty=TTY3 if tty == 'tty3' else TTY4, comm='sudo', exe='/usr/bin/sudo')}
        self.facts = dict(Service='login', Type='tty', Remote='no', Name='ares-recovery', User='1000')
        self.identity = dict(Id='7', TTY=tty, Audit='7', Scope='session-7.scope')
        self.listed = [dict(session='7', user='ares-recovery', uid=1000, tty=tty)]
        self.calls, self.mutations = [], []
        self.started = '123456789'
        self.missing = set()

    def json(self, *args):
        self.calls.append(args)
        assert args == ('loginctl', 'list-sessions', '--json=short')
        return self.listed

    def read(self, *args):
        self.calls.append(args)
        assert args[:3] == ('loginctl', 'show-session', '7')
        if '--value' in args: return self.started + '\n'
        fields = self.identity if args[-1] == '--property=Id,TTY,Audit,Scope' else self.facts
        return ''.join(k + '=' + v + '\n' for k, v in fields.items())

    def mutate(self, *args):
        self.mutations.append(args)
        raise AssertionError('No mutation allowed')

    @contextlib.contextmanager
    def install(self, real_stdin=False):
        original = pathlib.Path.read_text
        def read(path, *a, **kw):
            name = str(path)
            if name in self.missing: raise FileNotFoundError(name)
            if name == '/proc/self/loginuid': return self.loginuid + '\n'
            if name == '/proc/self/cgroup': return self.cgroup
            if name == '/proc/self/sessionid': return self.audit + '\n'
            if name == '/proc/sys/kernel/random/boot_id': return '11111111-1111-4111-8111-111111111111\n'
            if name.startswith('/proc/') and name.endswith('/stat'):
                pid = int(path.parent.name)
                if pid not in self.rows: raise FileNotFoundError(name)
                row = self.rows[pid]
                fields = ['S', str(row['ppid']), str(pid), str(row['session']), str(row['tty']), str(pid)] + ['0'] * 13 + ['1234']
                return str(pid) + ' (' + row['comm'] + ') ' + ' '.join(fields)
            return original(path, *a, **kw)
        def readlink(name): return self.rows[int(pathlib.Path(name).parent.name)]['exe']
        with contextlib.ExitStack() as stack:
            if not real_stdin:
                stack.enter_context(patch.object(owner.sys.stdin, 'isatty', return_value=True))
                stack.enter_context(patch.object(owner.os, 'ttyname', return_value=self.name))
            stack.enter_context(patch.object(pathlib.Path, 'read_text', side_effect=read, autospec=True))
            stack.enter_context(patch.object(owner.os, 'readlink', side_effect=readlink))
            stack.enter_context(patch.object(owner.os, 'getpid', return_value=40))
            stack.enter_context(patch.object(owner, 'terminal_number', side_effect=lambda name:
                self.pts if name == self.name else TTY3 if name == '/dev/tty3' else TTY4))
            tool = object.__new__(owner.Tools); tool.host = self
            yield tool


class SessionTest(unittest.TestCase):
    def check(self, model, ready):
        before = copy.deepcopy(model.rows)
        with model.install() as tool:
            if ready:
                value = tool.session()
                self.assertEqual(value, dict(tty=model.tty, session='7', started_us=123456789,
                    boot='11111111-1111-4111-8111-111111111111'))
            else:
                with self.assertRaises(owner.Stop): tool.session()
        self.assertEqual(model.mutations, [])
        self.assertEqual(model.rows, before)

    def test_direct_tty3_and_tty4(self):
        for tty in ('tty3', 'tty4'): self.check(Model(tty, '/dev/' + tty), True)
        model = Model()
        with model.install() as tool, patch.object(owner.sys.stdin, 'isatty', return_value=False):
            with self.assertRaisesRegex(owner.Stop, owner.PHYSICAL_LOGIN): tool.session()
        self.assertEqual(model.calls, [])

    def test_sudo_pty_tty3_and_fresh_tty4(self):
        for tty in ('tty3', 'tty4'): self.check(Model(tty), True)
        model = Model(); model.rows[40]['exe'] = '/usr/bin/python3.14'
        self.check(model, True)

    def test_qualification5_sudo_monitor_bash_shape(self):
        fixture = json.loads((ROOT/'os/tests/fixtures/owner-console/14ze-qualification5.json').read_text())
        self.assertEqual(fixture['run'], 40596167369)
        model = Model()
        for row in fixture['model_proc']:
            if row['pid'] in model.rows:
                self.assertEqual(row['ppid'], model.rows[row['pid']]['ppid'])
                self.assertEqual(row['tty'], model.rows[row['pid']]['tty'])
        self.check(model, True)

    def test_graphical_konsole_and_remote_sshd(self):
        for executable, facts in (('konsole', dict(Type='wayland')),
                ('sshd', dict(Remote='yes', Service='sshd'))):
            model = Model(); model.rows[22].update(comm=executable, exe='/usr/bin/' + executable)
            model.facts.update(facts); self.check(model, False)

    def test_tmux_screen_terminal_emulator_and_unknown_inside_local_sudo(self):
        for executable in ('tmux', 'screen', 'konsole', 'sshd', 'foot', 'unknown'):
            model = Model(); model.rows[22].update(comm=executable, exe='/usr/bin/' + executable)
            self.check(model, False)

    def test_missing_duplicate_and_mismatched_cgroup_session(self):
        for cgroup in ('0::/user.slice/user-1000.slice\n', '', 'not-cgroup',
                '0::/session-7.scope/session-8.scope\n', '0::/session-8.scope\n',
                '0::/session-7.scope\n1:cpu:/session-7.scope\n'):
            model = Model(); model.cgroup = cgroup; self.check(model, False)

    def test_missing_unset_or_inconsistent_audit_and_loginuid(self):
        for value in ('', '4294967295', '-1', '8', 'not-numeric'):
            model = Model(); model.audit = value; self.check(model, False)
        for file in ('/proc/self/sessionid', '/proc/self/cgroup'):
            model = Model(); model.missing.add(file); self.check(model, False)
        model = Model(); model.loginuid = '2000'; self.check(model, False)

    def test_every_logind_fact_remains_mandatory(self):
        for key, value in (('Service', 'sudo'), ('Type', 'wayland'), ('Remote', 'yes'),
                ('Name', 'ares'), ('User', '2000')):
            model = Model(); model.facts[key] = value; self.check(model, False)
        for key in ('Id', 'Scope', 'Audit', 'TTY'):
            model = Model(); model.identity[key] = 'wrong'; self.check(model, False)
        for started in ('', 'bad'):
            model = Model(); model.started = started; self.check(model, False)

    def test_tty_session_and_list_identity_mismatch_or_duplicate(self):
        for change in ('tty', 'uid', 'user', 'session', 'duplicate'):
            model = Model()
            if change == 'duplicate': model.listed *= 2
            else: model.listed[0][change] = 2000 if change == 'uid' else 'wrong'
            self.check(model, False)
        self.check(Model('tty3', '/dev/tty4'), False)

    def test_broken_cycle_unknown_missing_monitor_and_wrong_controlling_tty(self):
        for change in ('missing', 'cycle', 'monitor', 'session', 'comm', 'terminal', 'sudo', 'pipe'):
            model = Model()
            if change == 'missing': del model.rows[21]
            elif change == 'cycle': model.rows[22]['ppid'] = 40
            elif change == 'monitor': model.rows[21]['session'] = 9
            elif change == 'session': model.rows[40]['session'] = 9
            elif change == 'comm': model.rows[22]['comm'] = 'konsole'
            elif change == 'terminal': model.rows[22]['tty'] = PTS + 1
            elif change == 'sudo': model.rows[20]['exe'] = '/tmp/sudo'
            else: model.name = '/dev/null'
            self.check(model, False)

    def test_nested_sudo_pts_refuses_under_the_briefs_single_pts_rule(self):
        # Pinned sudo allocates a second pts when a sudo command is typed
        # inside the sudo -i shell. This documents the unresolved guide case.
        model = Model()
        model.name, model.pts = '/dev/pts/3', PTS + 1
        model.rows[40].update(ppid=31, session=31, tty=PTS + 1)
        model.rows[31] = dict(ppid=30, session=31, tty=PTS + 1, comm='sudo', exe='/usr/bin/sudo')
        model.rows[30] = dict(ppid=22, session=21, tty=PTS, comm='sudo', exe='/usr/bin/sudo')
        self.check(model, False)

    def test_real_unprivileged_pts_uses_real_stdin_with_modelled_session_facts(self):
        if os.name != 'posix': self.skipTest('Real PTY execution runs in existing WSL/native Linux')
        import pty
        master, slave = pty.openpty()
        try:
            process = subprocess.run([sys.executable, str(pathlib.Path(__file__)), '--real-pts'],
                stdin=slave, capture_output=True, text=True, timeout=15)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertFalse(process.stderr)
            value = json.loads(process.stdout)
            self.assertTrue(value['real_stdin_tty'] and value['real_stdin_pts'])
            self.assertEqual(value['tty'], 'tty3')
            self.assertEqual(value['mutations'], 0)
        finally: os.close(master); os.close(slave)


if __name__ == '__main__':
    if sys.argv[1:] == ['--real-pts']:
        name = os.ttyname(0)
        pts = owner.terminal_number(name)
        model = Model(name=name, pts=pts)
        model.rows[40].update(exe=os.readlink('/proc/self/exe'),
            comm=pathlib.Path('/proc/self/comm').read_text().strip())
        with model.install(real_stdin=True) as tool: result = tool.session()
        print(json.dumps(dict(tty=result['tty'], real_stdin_tty=sys.stdin.isatty(),
            real_stdin_pts=name.startswith('/dev/pts/'), mutations=len(model.mutations),
            proc_and_logind='explicit stand-ins; stdin is real unprivileged pts')))
    else: unittest.main()
