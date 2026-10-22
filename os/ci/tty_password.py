"""Observe a real login password prompt without retaining a revoked TTY fd."""
import errno
import os
import subprocess
import termios
import time


def wait_for_hidden_password(tty='tty3', timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        login = subprocess.run(['pgrep', '-t', tty, '-x', 'login'], capture_output=True)
        if login.returncode not in (0, 1):
            raise RuntimeError(f'Cannot query {tty} login: exit {login.returncode}')
        if login.returncode == 0:
            try:
                # login's vhangup revokes descriptors opened before its TTY
                # takeover. Reopen on every observation, including after EIO.
                fd = os.open('/dev/' + tty, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
                try:
                    hidden = not termios.tcgetattr(fd)[3] & termios.ECHO
                finally:
                    os.close(fd)
                if hidden:
                    print('TTY3_LOGIN_PASSWORD_ECHO_DISABLED')
                    return
            except (OSError, termios.error) as error:
                if error.args[0] != errno.EIO:
                    raise
        time.sleep(0.1)
    raise TimeoutError(f'{tty} login did not request a hidden password')


if __name__ == '__main__':
    wait_for_hidden_password()
