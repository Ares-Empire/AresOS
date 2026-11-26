import json
import pathlib
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

from test_aresos_shell import INSTANCE, NONCE, REGISTRY, ROOT, shell

sys.path.insert(0, str(ROOT / 'os/ci/bench'))
sys.path.insert(0, str(ROOT / 'os/ci'))
import agent
import driver
from channel import Frames, frame


class BenchAgentTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(dir=ROOT / '.work' if (ROOT / '.work').is_dir() else ROOT)
        self.addCleanup(folder.cleanup)
        self.runtime = pathlib.Path(folder.name)
        (self.runtime / 'aresos').mkdir()
        self.identity = self.runtime / 'aresos/desktop-runtime.json'
        self.identity.write_text(json.dumps({'nonce': NONCE, 'instance': INSTANCE}))

    def test_exec_exports_only_the_exit_code_even_if_it_reads_the_nonce(self):
        command = [sys.executable, '-c', 'import sys; print(open(sys.argv[1]).read()); sys.exit(4)', str(self.identity)]
        with patch.object(agent, 'as_desktop', return_value=command):
            self.assertEqual(agent.action({'action': 'exec', 'argv': command}), {'code': 4})

        guest = MagicMock()
        guest.call.return_value = {'code': 0, 'output': NONCE}
        with patch.object(driver, 'EVIDENCE', self.runtime):
            self.assertEqual(driver.run_step(guest, {'kind': 'exec', 'argv': command}, 1, {}), {})
        self.assertFalse(list(self.runtime.glob('001.*')))

    def test_journal_refuses_an_embedded_live_nonce_before_export(self):
        self.assertEqual(agent.journal_output(self.runtime, 'greetd ready'), 'greetd ready')
        with self.assertRaisesRegex(ValueError, 'Credential-shaped'):
            agent.journal_output(self.runtime, f'message{NONCE}suffix')

    def test_authenticated_health_probe_preserves_a_live_desktop(self):
        with patch.object(agent.os, 'execve') as execve:
            agent.start_desktop(self.runtime)
        token_file = self.runtime / agent.VIEW_TOKEN_FILE
        token = token_file.read_text()
        self.assertEqual(token_file.stat().st_mode & 0o777, 0o600)
        self.assertEqual(execve.call_args.args[2]['ARESOS_VIEW_TOKEN'], token)
        helper = shell.Helper(REGISTRY, INSTANCE, NONCE, self.runtime / 'shell-journal.json', view_token=token)
        path = str(self.runtime / 'aresos/shell.sock')
        server = shell.Server(path, helper)
        self.addCleanup(server.close)
        stop = threading.Event()

        def serve():
            while not stop.is_set():
                server.step(timeout=0.02)

        worker = threading.Thread(target=serve, daemon=True)
        worker.start()
        self.addCleanup(worker.join, 3)
        self.addCleanup(stop.set)
        with socket.socket(socket.AF_UNIX) as desktop:
            desktop.settimeout(3)
            desktop.connect(path)
            replies = Frames(desktop.recv)
            desktop.sendall(frame(dict(protocol='aresos-shell/1.2', op='hello', id='desktop-hello',
                                       major=1, minor=2, instance=INSTANCE, nonce=NONCE)))
            self.assertTrue(replies.receive()['ok'])
            original = helper.desktop
            token_file.write_text('X' * 43)
            with self.assertRaisesRegex(ValueError, 'refused'):
                agent.probe_helper(self.runtime)
            token_file.write_text(token)
            self.assertTrue(agent.probe_helper(self.runtime))
            desktop.sendall(frame(dict(protocol='aresos-shell/1.2', op='list_apps', id='still-connected')))
            reply = replies.receive()
            self.assertTrue(reply['ok'])
            self.assertEqual(reply['id'], 'still-connected')
            self.assertIs(helper.desktop, original)


class BenchQemuEnvironmentTest(unittest.TestCase):
    def test_image_tool_and_vm_receive_only_the_explicit_environment(self):
        with patch.dict(driver.os.environ, {'GH_TOKEN': 'synthetic-runner-secret', 'LD_PRELOAD': 'ignored'}), \
                patch.object(driver.subprocess, 'run') as run, patch.object(driver.subprocess, 'Popen') as popen, \
                patch.object(driver.shutil, 'copyfile'), patch.object(driver.Guest, 'connect'), \
                patch.object(driver, 'QMP'), patch.object(driver, 'Frames') as frames:
            frames.return_value.receive.return_value = {'ready': True, 'protocol': 1}
            with tempfile.TemporaryDirectory(dir=ROOT) as folder:
                guest = driver.Guest(pathlib.Path(folder), pathlib.Path(folder) / 'disk.raw')
                guest.boot()
        for command in (run.call_args, popen.call_args):
            self.assertEqual(command.kwargs['env'].keys(), {'PATH', 'LC_ALL'})
            self.assertEqual(command.kwargs['stderr'], subprocess.DEVNULL)
