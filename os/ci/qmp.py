"""Continuously retain QMP events, including those after a command's reply."""
import queue
import threading

from channel import Frames, frame


class QMP:
    def __init__(self, sock):
        self.sock = sock
        self.events = []
        self.responses = queue.Queue()
        self.sequence = 0
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            incoming = Frames(self.sock.recv)
            while True:
                value = incoming.receive()
                if 'event' in value:
                    self.events.append(value)
                elif 'QMP' not in value:
                    self.responses.put(value)
        except Exception as error:
            self.responses.put(error)

    def command(self, execute, arguments=None):
        self.sequence += 1
        self.sock.sendall(frame(dict(execute=execute, arguments=arguments or {}, id=self.sequence)))
        response = self.responses.get(timeout=30)
        if isinstance(response, Exception):
            raise response
        if response.get('id') != self.sequence or 'error' in response:
            raise RuntimeError(response)
        return response['return']


def assert_guest_poweroff(events):
    shutdowns = [event for event in events if event.get('event') == 'SHUTDOWN']
    assert len(shutdowns) == 1, f'Expected one QMP SHUTDOWN: {shutdowns}'
    assert shutdowns[0]['data'] == {'guest': True, 'reason': 'guest-shutdown'}, shutdowns
    assert not any(event.get('event') in ('RESET', 'SUSPEND', 'GUEST_PANICKED') for event in events), events
    return shutdowns[0]
