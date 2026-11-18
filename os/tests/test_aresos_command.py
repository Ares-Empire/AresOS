"""Package 43: pure dispatch decisions and harmless exec/terminal probes; no sudo runs."""
import ast
import contextlib
import importlib.machinery
import io
import json
import os
import pathlib
import pty
import pwd
import re
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

from test_owner_bootstrap import KSSHASKPASS_PROMPTS

ROOT = pathlib.Path(__file__).resolve().parents[2]
DISPATCHER = ROOT / 'os/config/usr/bin/aresos'
ASKPASS = ROOT / 'os/config/usr/libexec/aresos-askpass'
loader = importlib.machinery.SourceFileLoader('aresos_command', str(DISPATCHER))
command = types.ModuleType(loader.name)
sys.modules[loader.name] = command
loader.exec_module(command)

OWNER = pwd.struct_passwd(('owner', 'x', 1001, 1001, '', '/var/home/owner', '/bin/bash'))
ADMIN = pwd.struct_passwd(('root', 'x', 0, 0, '', '/root', '/bin/bash'))
LABELS = {
    'update': 'Update to the newest version',
    'previous': 'Go back to the previous version at the next restart',
    'rollback': 'Go back to plain Bazzite at the next restart',
    'check': 'Check the system',
    'title': 'Show what starts next',
    'records': 'Read disk records',
    'logs': 'Save the log of the last start',
    'export': 'Export records',
    'reboot': 'Restart',
}
REFUSED = {
    **{word: 'use aresos update here, it goes forward by itself when a newer AresOS is installed'
       for word in ('forward', 'newest')},
    **{word: f'this works only at the recovery console, typed by you: sudo /var/lib/ares/at {word}'
       for word in ('layout', 'login')},
    'keep-stock': 'this works only on plain Bazzite, at the recovery console, typed by you: '
                  'sudo /var/lib/ares/at keep-stock',
    **{word: 'this belongs to installing AresOS from plain Bazzite, at the recovery console; see docs/INSTALL.md'
       for word in ('install', 'prepare', 'verify', 'switch')},
}
SCREEN = {'WAYLAND_DISPLAY': 'wayland-1', 'DISPLAY': ':2', 'XDG_RUNTIME_DIR': '/run/user/1001',
          'XDG_SESSION_TYPE': 'wayland', 'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/run/user/1001/bus'}
DIRTY = dict(SCREEN, PATH='/tmp/bin', LANG='de_DE.UTF-8', LC_ALL='de_DE.UTF-8', HOME='/tmp/home',
             USER='other', LOGNAME='other', SUDO_ASKPASS='/tmp/helper', SSH_ASKPASS_PROMPT='confirm',
             PYTHONPATH='/tmp', PYTHONSTARTUP='/tmp/start', BASH_ENV='/tmp/env', LD_PRELOAD='/tmp/lib.so',
             QT_PLUGIN_PATH='/tmp/plugins', XAUTHORITY='/tmp/auth', UNRELATED='kept by Control only')


class PlanTest(unittest.TestCase):
    def test_each_offered_word_has_exactly_the_rehearsed_command_and_clean_environment(self):
        expected_env = dict(SCREEN, PATH='/usr/bin:/bin', LANG='C.UTF-8', HOME=OWNER.pw_dir,
                            USER=OWNER.pw_name, LOGNAME=OWNER.pw_name,
                            SUDO_ASKPASS='/usr/libexec/aresos-askpass', SSH_ASKPASS_PROMPT='')
        for word, label in LABELS.items():
            with self.subTest(word=word):
                result = command.plan([word], DIRTY, OWNER)
                inner = 'newest' if word == 'update' else word
                self.assertEqual(result, command.Exec('/usr/bin/sudo',
                    ('/usr/bin/sudo', '-k', '-A', '-p', label, '/usr/bin/bash', '-c', f'/var/lib/ares/at {inner}'),
                    expected_env))
        self.assertEqual(DIRTY['PATH'], '/tmp/bin', 'plan must not change the caller environment')

    def test_display_variants_and_only_variables_that_were_set_are_passed(self):
        for display in ({'DISPLAY': ':2'}, {'WAYLAND_DISPLAY': 'wayland-1'},
                        {'WAYLAND_DISPLAY': 'wayland-1', 'DISPLAY': ''}):
            with self.subTest(display=display):
                result = command.plan(['check'], display, OWNER)
                self.assertIsInstance(result, command.Exec)
                self.assertEqual({key: value for key, value in result.environ.items() if key in SCREEN}, display)

    def test_every_refused_word_says_where_it_works_and_nothing_runs(self):
        for word, reason in REFUSED.items():
            for account in (OWNER, ADMIN):
                for environ in ({}, DIRTY):
                    with self.subTest(word=word, uid=account.pw_uid, environ=bool(environ)):
                        self.assertEqual(command.plan([word], environ, account),
                                         command.Refusal(f'aresos {word}: {reason}; nothing ran', 2))

    def test_offered_words_take_no_arguments_including_options_and_shell_text(self):
        for word in LABELS:
            for extra in (['--help'], ['; true'], ['one', 'two']):
                with self.subTest(word=word, extra=extra):
                    self.assertEqual(command.plan([word, *extra], DIRTY, OWNER),
                                     command.Refusal(f'aresos {word}: takes no further words; nothing ran', 2))

    def test_root_and_no_desktop_name_only_the_safe_console_command(self):
        for word in LABELS:
            for account, environ in ((ADMIN, DIRTY), (OWNER, {}), (OWNER, {'DISPLAY': '', 'WAYLAND_DISPLAY': ''})):
                with self.subTest(word=word, uid=account.pw_uid, environ=bool(environ)):
                    inner = 'newest' if word == 'update' else word
                    self.assertEqual(command.plan([word], environ, account), command.Refusal(
                        f'aresos {word}: this works at the recovery console, typed by you: '
                        f'sudo /var/lib/ares/at {inner}; nothing ran', 2))

    def test_no_printable_or_executed_command_reaches_inner_update_or_forward(self):
        for word in command.TABLE:
            for argv in ([word], [word, '--help']):
                for account in (OWNER, ADMIN):
                    for environ in (DIRTY, {}):
                        result = command.plan(argv, environ, account)
                        strings = result.argv if isinstance(result, command.Exec) else (result.line,)
                        for value in strings:
                            self.assertNotIn('at update', value)
                            self.assertNotIn('at forward', value)

    def test_labels_are_distinct_plain_and_never_remembered_prompts(self):
        offered = {word: row[1] for word, row in command.TABLE.items() if isinstance(row, tuple)}
        self.assertEqual(offered, LABELS)
        self.assertEqual(len(set(offered.values())), 9)
        self.assertEqual(len(KSSHASKPASS_PROMPTS), 16)
        for label in offered.values():
            self.assertRegex(label, r'^[A-Za-z0-9 ,]+$')
            self.assertLess(len(label), 70)
            for pattern in KSSHASKPASS_PROMPTS:
                self.assertIsNone(re.search(pattern, label), (label, pattern))

    def test_guide_window_table_equals_every_offered_command_and_label(self):
        guide = (ROOT / 'docs/INSTALL.md').read_text()
        box = guide.split("- [ ] **From Claude's terminal, on AresOS 29 or later:**", 1)[1]
        box = box.split('- [ ] **Windows side**', 1)[0]
        table = box.split('| Command | Line in the window |\n|---|---|\n', 1)[1].split('\n\n', 1)[0]
        rows = [[cell.strip() for cell in line.strip('|').split('|')] for line in table.splitlines()]
        self.assertEqual(rows, [[f'`aresos {word}`', row[1]] for word, row in command.TABLE.items()
                                if isinstance(row, tuple)])

    def test_control_receives_all_other_argv_and_the_whole_environment_even_as_root(self):
        for argv in ([], ['--help'], ['admin', 'mail', 'account', 'add'], ['testapp', 'list'],
                     ['control', 'log'], ['unknown', '--strange', 'with spaces', ''], ['CHECK']):
            for account in (OWNER, ADMIN):
                for environ in (DIRTY, {}):
                    with self.subTest(argv=argv, uid=account.pw_uid):
                        self.assertEqual(command.plan(argv, environ, account), command.Exec(
                            '/usr/libexec/aresos-control/cli', ('/usr/libexec/aresos-control/cli', *argv), environ))

    def test_the_three_word_sets_are_equal_without_importing_or_running_the_tools(self):
        tools = ast.parse((ROOT / 'os/owner-tools/owner.py').read_text())
        main = next(node for node in tools.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
        known = next(node.value for node in main.body if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == 'known' for target in node.targets))
        control = ast.parse((ROOT / 'control/tests/test_reserved_words.py').read_text())
        reserved = next(node.value for node in control.body if isinstance(node, ast.Assign)
                        and any(isinstance(target, ast.Name) and target.id == 'RESERVED' for target in node.targets))
        self.assertEqual(set(command.TABLE), ast.literal_eval(known))
        self.assertEqual(set(command.TABLE), set(ast.literal_eval(reserved.args[0])),
                         'Control must reserve every tools word, including newest (D12; Control-side change)')


class MainTest(unittest.TestCase):
    def invoke(self, argv, account=OWNER, environ=DIRTY, error=None):
        stderr = io.StringIO()
        with mock.patch.object(sys, 'argv', ['aresos', *argv]), \
                mock.patch.object(command.pwd, 'getpwuid', return_value=account) as lookup, \
                mock.patch.object(command, 'original_environment', return_value=environ), \
                mock.patch.object(command.os, 'execve', side_effect=error) as execute, \
                contextlib.redirect_stderr(stderr):
            status = command.main()
        lookup.assert_called_once_with(os.getuid())
        return status, stderr.getvalue(), execute

    def test_main_execs_the_plan_without_starting_a_child_or_changing_directory(self):
        expected = command.plan(['check'], DIRTY, OWNER)
        here = os.getcwd()
        _, stderr, execute = self.invoke(['check'])
        execute.assert_called_once_with(expected.path, expected.argv, expected.environ)
        self.assertEqual(stderr, '')
        self.assertEqual(os.getcwd(), here)
        tree = ast.parse(DISPATCHER.read_text())
        imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imports |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        self.assertNotIn('subprocess', imports)
        self.assertEqual(DISPATCHER.read_text().splitlines()[0], '#!/usr/bin/python3 -ISB')

    def test_main_refuses_on_stderr_without_exec(self):
        for word in REFUSED:
            status, stderr, execute = self.invoke([word])
            self.assertEqual((status, stderr), (2, f'aresos {word}: {REFUSED[word]}; nothing ran\n'))
            execute.assert_not_called()
        status, stderr, execute = self.invoke(['update'], environ={})
        self.assertEqual(status, 2)
        self.assertIn('sudo /var/lib/ares/at newest', stderr)
        execute.assert_not_called()

    def test_missing_control_prints_the_nine_offered_words_and_exits_two(self):
        for argv in ([], ['--help'], ['unknown']):
            status, stderr, execute = self.invoke(argv, error=FileNotFoundError())
            self.assertEqual(status, 2)
            self.assertEqual(stderr, 'aresos: choose ' + ', '.join(LABELS) +
                             '; Control is not installed; nothing ran\n')
            self.assertEqual(execute.call_args.args[0], '/usr/libexec/aresos-control/cli')
        with self.assertRaises(FileNotFoundError):
            self.invoke(['check'], error=FileNotFoundError())

    def test_real_main_handover_keeps_terminal_arguments_environment_and_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            target = root / 'cli'
            target.write_text('#!' + sys.executable + '\nimport json, os, sys\nprint(json.dumps(dict('
                              'terminal=os.isatty(0), argv=sys.argv[1:], env=os.environ.get("HANDOVER_MARKER"), '
                              'cwd=os.getcwd())))\n')
            target.chmod(0o755)
            code = ('import importlib.machinery, sys, types\n'
                    f'loader = importlib.machinery.SourceFileLoader("dispatch", {str(DISPATCHER)!r})\n'
                    'm = types.ModuleType(loader.name); sys.modules[loader.name] = m; loader.exec_module(m)\n'
                    f'm.CONTROL = {str(target)!r}\nraise SystemExit(m.main())\n')
            master, slave = pty.openpty()
            try:
                argv = ['admin', 'mail', 'account', 'add', 'with spaces', '', '--literal=$x']
                result = subprocess.run([sys.executable, '-I', '-B', '-c', code, *argv], stdin=slave,
                                        capture_output=True, text=True, timeout=15, cwd=root,
                                        env=dict(os.environ, HANDOVER_MARKER='unchanged'))
            finally:
                os.close(master)
                os.close(slave)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), dict(terminal=True, argv=argv, env='unchanged', cwd=str(root)))

    def test_real_shebang_handover_preserves_empty_and_c_locale_environments_exactly(self):
        with tempfile.TemporaryDirectory() as folder:
            dispatcher = pathlib.Path(folder) / 'aresos'
            # Only the destination changes: env prints the exec's bytes without another Python startup.
            source = DISPATCHER.read_text()
            self.assertEqual(source.count(f'CONTROL = {command.CONTROL!r}'), 1)
            dispatcher.write_text(source.replace(f'CONTROL = {command.CONTROL!r}', "CONTROL = '/usr/bin/env'"))
            dispatcher.chmod(0o755)
            for environment in ([], [b'LANG=C'], [b'LANG=C', b'RAW=\xff=with spaces', b'EMPTY='],
                                [b'LC_ALL=C', b'LC_CTYPE=C']):
                with self.subTest(environment=environment):
                    result = subprocess.run(['/usr/bin/env', '-i', *environment, str(dispatcher), '-0'],
                                            capture_output=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, b'')
                    self.assertEqual(result.stdout, b''.join(entry + b'\0' for entry in environment))

    def test_raw_execve_duplicate_names_keep_first_for_refusal_and_control_handover(self):
        # subprocess's environment mapping cannot express duplicate names; libc execve can.
        launch = '''
import ctypes, os, sys
libc = ctypes.CDLL(None, use_errno=True)
vector = ctypes.POINTER(ctypes.c_char_p)
libc.execve.argtypes = (ctypes.c_char_p, vector, vector)
libc.execve.restype = ctypes.c_int
argv = [os.fsencode(word) for word in sys.argv[1:]]
environment = [b'DISPLAY=', b'DISPLAY=:2', b'LANG=C', b'RAW=\\xff=with spaces', b'RAW=last']
libc.execve(argv[0], (ctypes.c_char_p * (len(argv) + 1))(*argv, None),
            (ctypes.c_char_p * (len(environment) + 1))(*environment, None))
error = ctypes.get_errno()
raise OSError(error, os.strerror(error))
'''
        with tempfile.TemporaryDirectory() as folder:
            dispatcher = pathlib.Path(folder) / 'aresos'
            source = DISPATCHER.read_text()
            # Force an ordinary account even in root CI; a broken refusal must never reach sudo.
            source = source.replace('pwd.getpwuid(os.getuid())', f'pwd.struct_passwd({tuple(OWNER)!r})')
            source = source.replace("'/usr/bin/sudo'", "'/usr/bin/false'")
            source = source.replace(f'CONTROL = {command.CONTROL!r}', "CONTROL = '/usr/bin/env'")
            dispatcher.write_text(source)
            dispatcher.chmod(0o755)
            result = subprocess.run([sys.executable, '-ISB', '-c', launch, str(dispatcher), 'check'],
                                    capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(result.stdout, b'')
            self.assertEqual(result.stderr, b'aresos check: this works at the recovery console, typed by you: '
                             b'sudo /var/lib/ares/at check; nothing ran\n')
            result = subprocess.run([sys.executable, '-ISB', '-c', launch, str(dispatcher), '-0'],
                                    capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, b'')
            self.assertEqual(result.stdout, b'DISPLAY=\0LANG=C\0RAW=\xff=with spaces\0')


class AskpassTest(unittest.TestCase):
    def test_helper_is_the_two_line_timeout_exec_with_unchanged_arguments(self):
        self.assertEqual(ASKPASS.read_text(), '#!/bin/sh\n'
                         'exec /usr/bin/timeout --foreground -k 10 600 /usr/bin/ksshaskpass "$@"\n')
        for path in (ASKPASS, DISPATCHER):
            self.assertFalse(path.is_symlink())
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o755)
        # Bash can intercept exec with a function; the pinned POSIX helper line still expands its real "$@".
        args = ['Check the system', 'one argument with spaces', '', '$(false)']
        probe = ('exec() { printf "<%s>\\n" "$@"; }\n' + ASKPASS.read_text().split('\n', 1)[1])
        result = subprocess.run(['/bin/bash', '-c', probe, 'askpass', *args], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [f'<{word}>' for word in
                         ['/usr/bin/timeout', '--foreground', '-k', '10', '600', '/usr/bin/ksshaskpass', *args]])


if __name__ == '__main__':
    unittest.main()
