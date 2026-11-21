"""Bound every FIFO open/write; never wait indefinitely while holding the shared game lock."""
import errno
import os
from pathlib import Path
import select
import stat
import sys
import time


class Writer:
    def __init__(self, rig, timeout=1):
        self.timeout = timeout
        deadline = time.monotonic() + timeout
        while True:
            try:
                self.fd = os.open(Path(rig)/'vin', os.O_WRONLY | os.O_NONBLOCK)
                break
            except OSError as error:
                if error.errno not in (errno.ENXIO, errno.ENOENT) or time.monotonic() >= deadline:
                    raise
                time.sleep(.005)
        if not stat.S_ISFIFO(os.fstat(self.fd).st_mode):
            self.close()
            raise ValueError('input target is not a FIFO')

    def send(self, command):
        data = (command + '\n').encode()
        if '\n' in command or len(data) > os.fpathconf(self.fd, 'PC_PIPE_BUF'):
            raise ValueError('one atomic input command required')
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                if os.write(self.fd, data) != len(data):
                    raise RuntimeError('incomplete input command')
                return
            except BlockingIOError:
                left = deadline - time.monotonic()
                if left <= 0 or not select.select([], [self.fd], [], left)[1]:
                    raise TimeoutError('input reader stopped draining commands')

    def close(self):
        os.close(self.fd)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


if __name__ == '__main__':
    with Writer(sys.argv[1]) as writer:
        writer.send(' '.join(sys.argv[2:]))
