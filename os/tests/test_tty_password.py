import errno
import itertools
import os
import pathlib
import pty
import subprocess
import sys
import termios
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
from tty_password import wait_for_hidden_password


class TtyPasswordTest(unittest.TestCase):
    def setUp(self):
        self.master, self.slave = pty.openpty()
        self.tty = os.ttyname(self.slave).removeprefix('/dev/')
        self.login = patch('tty_password.subprocess.run', return_value=subprocess.CompletedProcess([], 0))
        self.query = self.login.start()
        self.addCleanup(self.login.stop)
        self.addCleanup(os.close, self.master)
        self.addCleanup(os.close, self.slave)

    def echo(self, enabled):
        attributes = termios.tcgetattr(self.slave)
        attributes[3] = attributes[3] | termios.ECHO if enabled else attributes[3] & ~termios.ECHO
        termios.tcsetattr(self.slave, termios.TCSANOW, attributes)

    def test_reopens_after_login_revokes_observation_descriptor(self):
        self.echo(False)
        attributes = termios.tcgetattr
        observations = iter([termios.error(errno.EIO, 'Input/output error'), None])

        def observe(fd):
            error = next(observations)
            if error:
                raise error
            return attributes(fd)

        with patch('tty_password.termios.tcgetattr', side_effect=observe), \
                patch('tty_password.os.open', wraps=os.open) as opened, \
                patch('tty_password.os.close', wraps=os.close) as closed, \
                patch('tty_password.time.sleep'):
            wait_for_hidden_password(self.tty)
        self.assertEqual(opened.call_count, 2)
        self.assertEqual(closed.call_count, 2)
        self.query.assert_called_with(['pgrep', '-t', self.tty, '-x', 'login'], capture_output=True)

    def assert_deadline(self):
        with patch('tty_password.time.monotonic', side_effect=itertools.count(0, 0.1)), \
                patch('tty_password.time.sleep'), self.assertRaises(TimeoutError):
            wait_for_hidden_password(self.tty, timeout=0.3)

    def test_persistent_hangup_still_fails_at_deadline(self):
        with patch('tty_password.termios.tcgetattr', side_effect=termios.error(errno.EIO, 'Input/output error')):
            self.assert_deadline()

    def test_echo_enabled_cannot_pass(self):
        self.echo(True)
        self.assert_deadline()

    def test_hidden_echo_without_login_cannot_pass(self):
        self.echo(False)
        self.query.return_value.returncode = 1
        self.assert_deadline()

    def test_unexpected_terminal_error_is_not_retried(self):
        with patch('tty_password.termios.tcgetattr', side_effect=termios.error(errno.EBADF, 'Bad file descriptor')), \
                self.assertRaises(termios.error):
            wait_for_hidden_password(self.tty)

    def test_failed_login_query_is_not_a_password_prompt(self):
        self.query.return_value.returncode = 2
        with self.assertRaises(RuntimeError):
            wait_for_hidden_password(self.tty)
