"""cdp.py: the DevTools pipe of the install proof (brief 18c-b, item 2).

Run: python3 -m unittest discover -s control/chrome/ci/install -p 'test_*.py'
No Chrome here: the other end of the pipe is this test.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cdp


class Peer:
    """Stands in for Chrome: reads NUL-ended commands and answers with what `answer` returns, in the given pieces."""

    def __init__(self, answer):
        (self.reads, self.writes), (chrome_reads, chrome_writes) = cdp.descriptors()
        self.client, self.seen = cdp.Client(self.reads, self.writes), []
        self.chrome_writes = chrome_writes

        def serve():
            buffer = b''
            while True:
                chunk = os.read(chrome_reads, 4096)
                if not chunk:
                    break
                buffer += chunk
                while b'\0' in buffer:
                    body, buffer = buffer.split(b'\0', 1)
                    command = json.loads(body)
                    self.seen.append(command)
                    for piece in answer(command):
                        os.write(chrome_writes, piece)
            os.close(chrome_reads)
        self.thread = threading.Thread(target=serve, daemon=True)
        self.thread.start()

    def close(self):
        self.client.close()
        self.thread.join(5)
        os.close(self.chrome_writes)


def framed(value):
    return json.dumps(value).encode() + b'\0'


class Pipe(unittest.TestCase):
    def peer(self, answer):
        peer = Peer(answer)
        self.addCleanup(peer.close)
        return peer

    def test_the_shell_line_gives_the_program_descriptors_3_and_4(self):
        (reads, writes), chrome = cdp.descriptors()
        self.assertTrue(all(descriptor >= 10 for descriptor in chrome))
        echo = 'import os; os.write(4, os.read(3, 5).upper()); os.close(%d)' % chrome[0]
        process = subprocess.Popen(cdp.command(sys.executable, ['-c', echo], chrome), pass_fds=chrome, stderr=subprocess.PIPE)
        for descriptor in chrome:
            os.close(descriptor)
        os.write(writes, b'hello')
        self.assertEqual(os.read(reads, 5), b'HELLO')
        # The program no longer holds the high numbers: closing one of them there fails.
        self.assertNotEqual(process.wait(10), 0)
        self.assertIn(b'Bad file descriptor', process.stderr.read())
        process.stderr.close()
        os.close(reads)
        os.close(writes)

    def test_an_answer_is_matched_by_its_id_across_pieces_and_events(self):
        def answer(command):
            whole = framed({'method': 'Target.targetCreated', 'params': {}}) + b'not json\0' + framed({'id': command['id'], 'result': {'echo': command}})
            return whole[:7], whole[7:40], whole[40:]
        peer = self.peer(answer)
        first = peer.client.call('Browser.getVersion')
        second = peer.client.call('Runtime.evaluate', {'expression': '1'}, session='S1')
        self.assertEqual(first['echo'], {'id': 1, 'method': 'Browser.getVersion', 'params': {}})
        self.assertEqual(second['echo'], {'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': '1'}, 'sessionId': 'S1'})

    def test_a_refusal_a_silence_and_a_closed_pipe_are_errors(self):
        peer = self.peer(lambda command: [framed({'id': command['id'], 'error': {'code': -32000, 'message': 'Method not available.'}})]
                         if command['method'] == 'Extensions.loadUnpacked' else [])
        with self.assertRaisesRegex(cdp.Error, 'Extensions.loadUnpacked: Method not available.'):
            peer.client.call('Extensions.loadUnpacked', {'path': '/nowhere'})
        with self.assertRaisesRegex(cdp.Error, 'no answer from Chrome in 0.2s'):
            peer.client.call('Browser.getVersion', timeout=0.2)
        os.close(peer.chrome_writes)
        peer.chrome_writes = os.open(os.devnull, os.O_WRONLY)
        with self.assertRaisesRegex(cdp.Error, 'the pipe closed'):
            peer.client.call('Browser.getVersion', timeout=5)

    def test_a_page_is_opened_attached_and_asked(self):
        def answer(command):
            result = {'Target.createTarget': {'targetId': 'T1'}, 'Target.attachToTarget': {'sessionId': 'S1'}}.get(command['method'])
            if result is None:
                expression = command['params']['expression']
                result = ({'exceptionDetails': {'text': 'Uncaught (in promise)', 'exception': {'description': 'Error: cannot be modified by user.'}}}
                          if 'throw' in expression else {'result': {'type': 'string', 'value': 'function'}})
            return [framed({'id': command['id'], 'result': result})]
        peer = self.peer(answer)
        page = peer.client.page('chrome://extensions/')
        self.assertEqual(page.evaluate('typeof chrome.developerPrivate.autoUpdate'), 'function')
        with self.assertRaisesRegex(cdp.Error, 'cannot be modified by user'):
            page.evaluate('throw 1', wait=True)
        self.assertEqual([command.get('sessionId') for command in peer.seen], [None, None, 'S1', 'S1'])
        self.assertEqual(peer.seen[1]['params'], {'targetId': 'T1', 'flatten': True})
        self.assertEqual(peer.seen[3]['params'], {'expression': 'throw 1', 'awaitPromise': True, 'returnByValue': True})


if __name__ == '__main__':
    unittest.main()
