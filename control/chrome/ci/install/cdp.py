"""Chrome's DevTools protocol over --remote-debugging-pipe (brief 18c-b, item 2). Test only.

The install proof starts Chrome without any debugging flag. Two questions can
only be put to Chrome's own pages and get a Chrome start of their own with
this pipe:
- case 5 asks chrome://extensions to check every extension for updates at once
  (Chrome 157 has no switch for a short schedule; its own is about five hours);
- case 1 asks what an extension the owner loaded by hand may do to ours.
A pipe and never a port: nothing listens, and only the process that started
Chrome holds the other end.

Chrome reads commands on its descriptor 3 and answers on 4, each one JSON
value followed by a NUL byte. Standard library only.
"""
import fcntl
import json
import os
import threading
import time

FLAG = '--remote-debugging-pipe'


class Error(Exception):
    """Chrome refused a command, an expression threw, or no answer came."""


def descriptors():
    """Two pipes as ((ours to read, ours to write), (Chrome's to read, Chrome's to write)).

    Chrome's two are numbered 10 or higher, so `command`'s shell can copy them
    to 3 and 4 without overwriting one with the other.
    """
    chrome_reads, we_write = os.pipe()
    we_read, chrome_writes = os.pipe()
    high = []
    for descriptor in (chrome_reads, chrome_writes):
        high.append(fcntl.fcntl(descriptor, fcntl.F_DUPFD, 10))
        os.close(descriptor)
    return (we_read, we_write), tuple(high)


def command(program, arguments, chrome):
    """The command that starts `program` with Chrome's two descriptors as 3 and 4 (pass them on with pass_fds)."""
    reads, writes = chrome
    return ['bash', '-c', f'exec "$0" "$@" 3<&{reads} 4>&{writes} {reads}<&- {writes}>&-', program, *arguments]


class Client:
    """Our end of the pipe: one command at a time out, its answer back. Events are not kept."""

    def __init__(self, reads, writes):
        self.reads, self.writes = reads, writes
        self.state = threading.Condition()
        self.replies, self.counter, self.closed = {}, 0, False
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        buffer = b''
        try:
            while True:
                chunk = os.read(self.reads, 65536)
                if not chunk:
                    break
                buffer += chunk
                while b'\0' in buffer:
                    body, buffer = buffer.split(b'\0', 1)
                    try:
                        message = json.loads(body)
                    except ValueError:
                        continue
                    if isinstance(message, dict) and 'id' in message:
                        with self.state:
                            self.replies[message['id']] = message
                            self.state.notify_all()
        except OSError:
            pass
        finally:
            # This thread alone closes the reading end: closed from outside, its number could be
            # given to the next Chrome's pipe while this thread still reads from it.
            os.close(self.reads)
            with self.state:
                self.closed = True
                self.state.notify_all()

    def call(self, method, params=None, session=None, timeout=30):
        with self.state:
            self.counter += 1
            identity = self.counter
        message = {'id': identity, 'method': method, 'params': params or {}}
        if session:
            message['sessionId'] = session
        data = json.dumps(message).encode() + b'\0'
        try:
            while data:
                data = data[os.write(self.writes, data):]
        except OSError as error:
            raise Error(f'{method}: the pipe to Chrome is closed ({error})') from None
        end = time.monotonic() + timeout
        with self.state:
            while identity not in self.replies:
                remaining = end - time.monotonic()
                if self.closed or remaining <= 0:
                    raise Error(f'{method}: no answer from Chrome' + (' (the pipe closed)' if self.closed else f' in {timeout}s'))
                self.state.wait(remaining)
            reply = self.replies.pop(identity)
        if 'error' in reply:
            raise Error(f"{method}: {(reply['error'] or {}).get('message')}")
        return reply.get('result') or {}

    def page(self, url):
        """Open `url` in a tab of its own and attach to it."""
        target = self.call('Target.createTarget', {'url': url})['targetId']
        return Page(self, self.call('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId'])

    def close(self):
        """After Chrome has exited: the reading thread ends at the pipe's end by itself."""
        try:
            os.close(self.writes)
        except OSError:
            pass


class Page:
    def __init__(self, client, session):
        self.client, self.session = client, session

    def evaluate(self, expression, wait=False, timeout=30):
        """The value of a JavaScript expression in the page; `wait` waits for a promise to settle."""
        result = self.client.call('Runtime.evaluate', {'expression': expression, 'awaitPromise': wait, 'returnByValue': True},
                                  self.session, timeout)
        if 'exceptionDetails' in result:
            details = result['exceptionDetails']
            raise Error((details.get('exception') or {}).get('description') or details.get('text') or 'the expression threw')
        return (result.get('result') or {}).get('value')
