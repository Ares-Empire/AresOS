"""Thread-visible fixture transcript, separate from injected service storage."""
from email.parser import BytesParser
import hashlib
import threading
import time


class Transcript:
    def __init__(self):
        self.events, self.script = [], []
        self.correlation = 0
        self.lock = threading.Lock()

    def begin(self, action, arguments):
        with self.lock:
            self.correlation += 1
            self.script.append({'call': self.correlation, 'action': action, 'arguments': arguments,
                                'clock': time.time(), 'faults': [], 'reply': 'pending'})
        return self.correlation

    def command(self, command, account=None, folder=None, roles=None, **values):
        if account is None and self.script:
            def selected(value):
                if isinstance(value, dict):
                    if isinstance(value.get('account'), str):
                        return value['account']
                    for child in value.values():
                        found = selected(child)
                        if found:
                            return found
                return None
            account = selected(self.script[-1]['arguments'])
        event = dict(call=self.correlation, command=command, account=account, folder=folder,
                     roles=roles, identities=[], attempted=True, accepted=False, reply='lost', **values)
        with self.lock:
            self.events.append(event)
        return event

    @staticmethod
    def message(raw, **identity):
        return {**identity, 'message_id': str(BytesParser().parsebytes(raw, headersonly=True).get('Message-ID', '')),
                'sha256': hashlib.sha256(raw).hexdigest()}


# Tests execute scenario calls serially. Server handlers run in other threads,
# so a ContextVar would drop correlation at precisely the remote boundary.
TRACE = Transcript()
