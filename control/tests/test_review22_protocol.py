"""Review 14: every changing request waits consistently and preserves uncertainty."""
from contextlib import contextmanager
import socket
import threading
import unittest
from unittest.mock import patch, MagicMock

from aresos_control.common import sha256
from aresos_control.engine import Engine
from aresos_control.protocol import Client, receive, send
from aresos_control.proxy import Proxy
from support import EngineCase


class Timeouts22(EngineCase):
    @contextmanager
    def server(self, delay, transfer=False):
        self.engine.close()
        path = self.root / 'reply.sock'
        listener = socket.socket(socket.AF_UNIX)
        listener.bind(str(path))
        listener.listen()
        errors = []
        def serve():
            service = None
            try:
                service = Engine(self.root / 'state', self.root / 'independent')
                def checkpoint(name):
                    if name == 'sqlite_prepared':
                        threading.Event().wait(delay)
                service.store.checkpoint = checkpoint
                connection, _ = listener.accept()
                with connection:
                    request = receive(connection)
                    try:
                        if transfer:
                            service.transfer(connection, request)
                        else:
                            send(connection, service.request(request))
                    except BrokenPipeError:
                        # The client has already reported unknown. Commit still
                        # completes and is checked through a fresh Engine below.
                        pass
            except BaseException as exc:
                errors.append(exc)
            finally:
                if service:
                    service.close()
        worker = threading.Thread(target=serve, daemon=True)
        worker.start()
        try:
            yield Client(path)
        finally:
            worker.join(timeout=20)
            listener.close()
            path.unlink()
            self.engine = Engine(self.root / 'state', self.root / 'independent')
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])

    def saved_request(self):
        return {'method': 'saved', 'app': 'testapp', 'outcome': {
            'path': '/synthetic/Downloads/synthetic.bin', 'sha256': sha256(b'Synthetic'), 'size': 9}}

    def assert_unknown(self, result, method):
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['error']['code'], 'unknown')
        self.assertIn('outcome is unknown', result['error']['message'])
        self.assertIn('Check', result['error']['message'])
        self.assertIn('Do not repeat', result['error']['message'])
        self.assertEqual(result['data']['state'], 'unknown')
        self.assertEqual(result['data']['request']['method'], method)
        self.assertEqual(len(result['data']['request']['request_sha256']), 64)

    def test_review22_save_held_eleven_seconds_receives_committed_ack(self):
        with self.server(11) as client:
            result = client.request(self.saved_request())
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['data'], {'recorded': True})
        self.assertEqual([e['outcome'] for e in self.engine.store.iter_audit() if e['action'] == 'testapp_file_save'], ['done'])

    def test_review22_save_after_client_timeout_is_unknown_and_committed_log_is_visible(self):
        with self.server(11) as client, patch('aresos_control.protocol.CHANGE_TIMEOUT', 10):
            result = client.request(self.saved_request())
        self.assert_unknown(result, 'saved')
        self.assertIn('control_log', result['error']['message'])
        logs = self.data('control_log', {})['items']
        self.assertEqual([e['outcome'] for e in logs if e['action'] == 'testapp_file_save'], ['done'])

    def test_review22_upload_lost_final_ack_is_unknown_and_import_commits(self):
        raw = b'Synthetic upload'
        file = {'sha256': sha256(raw), 'size': len(raw), 'name': 'synthetic.bin', 'real_path': '/synthetic/synthetic.bin'}
        final_connection, lost_ack = None, False

        def upload_frame(connection, message, **options):
            nonlocal final_connection
            send(connection, message, **options)
            if message == {'end': True, 'offset': len(raw)}:
                final_connection = connection

        def receive_without_final_ack(connection):
            nonlocal lost_ack
            # A short timeout on the whole exchange can expire before the
            # upload starts. Inject loss only after its real end frame was sent.
            if connection is final_connection:
                lost_ack = True
                raise socket.timeout('Synthetic final upload acknowledgement loss')
            return receive(connection)

        with self.server(0.2, transfer=True) as client, \
                patch('aresos_control.protocol.send', side_effect=upload_frame), \
                patch('aresos_control.protocol.receive', side_effect=receive_without_final_ack):
            result = client.upload('testapp', file, raw)
        self.assertTrue(lost_ack, 'The loss must target the final acknowledgement after every upload frame')
        self.assert_unknown(result, 'upload')
        self.assertEqual(result['data']['request']['sha256'], file['sha256'])
        self.assertEqual(self.engine.blobs.read(file['sha256']), raw)
        self.assertEqual([e['outcome'] for e in self.engine.store.iter_audit() if e['action'] == 'testapp_file_import'], ['done'])


class ReplyPolicy22(unittest.TestCase):
    def test_review22_one_policy_for_calls_saves_uploads_downloads_and_setup(self):
        requests = [{'method': name} for name in ('upload', 'download', 'saved', 'mail_account_add')]
        requests += [{'method': 'call', 'action': 'testapp_prepare_send'}]
        for request in requests:
            with self.subTest(request=request), patch('aresos_control.protocol.socket.socket') as factory:
                with Client('/synthetic/socket').connection(request):
                    pass
                factory.return_value.__enter__.return_value.settimeout.assert_called_once_with(30)

    def test_review22_connection_loss_names_operation_and_setup_never_exposes_password(self):
        requests = [{'method': 'call', 'action': 'testapp_send', 'arguments': {'operation_id': 'synthetic:operation'}},
                    {'method': 'mail_account_add', 'arguments': {'id': 'synthetic'}, 'password': 'synthetic-secret'}]
        for request in requests:
            with self.subTest(method=request['method']), patch('aresos_control.protocol.receive', side_effect=socket.timeout()), \
                 patch('aresos_control.protocol.socket.socket'):
                result = Client('/synthetic/socket').request(request)
            self.assertEqual(result['error']['code'], 'unknown')
            self.assertNotIn('synthetic-secret', str(result))
            if request['method'] == 'call':
                self.assertEqual(result['data']['request']['operation_id'], 'synthetic:operation')
                self.assertIn('operation_status', result['error']['message'])
            else:
                self.assertIn('mail_accounts', result['error']['message'])

    def test_review22_proxy_preserves_unknown_save_ack_and_does_not_cancel_unknown_download(self):
        for verb in ('file_save', 'attachment_save'):
            proxy = Proxy('mail' if verb == 'attachment_save' else 'testapp', {'act_socket': '/synthetic/socket'})
            proxy.client = MagicMock()
            proxy.files = MagicMock()
            proxy.files.limit = 1024
            saved = {'path': '/synthetic/synthetic.bin', 'sha256': sha256(b'x'), 'size': 1}
            proxy.files.save.return_value = saved
            unknown = {'ok': False, 'error': {'code': 'unknown', 'message': 'Request outcome is unknown; check control_log.'},
                       'data': {'state': 'unknown', 'request': {'method': 'saved'}}, 'pending': {}}
            item = {'sha256': saved['sha256'], 'export_id': 'a' * 32, 'name': 'synthetic.bin', 'other_holds': 0}
            proxy.client.call.return_value = {'ok': True, 'data': {'file': item}}
            proxy.client.download.return_value = ({'ok': True, 'data': item}, b'x')
            proxy.client.request.return_value = unknown
            args = {'sha256': saved['sha256'], 'folder': '/synthetic', 'name': 'synthetic.bin'} if verb == 'file_save' else {
                'reference': {'account': 'synthetic', 'folder': 'Source', 'uidvalidity': 1, 'uid': 1, 'message_id': '<synthetic@mail.invalid>'},
                'part': '1', 'folder': '/synthetic', 'name': 'synthetic.bin'}
            with self.subTest(verb=verb):
                result = proxy.call(verb, args)
                self.assertEqual(result['error']['code'], 'unknown', result)
                self.assertEqual(result['data']['state'], 'unknown')
                self.assertEqual(result['data']['saved'], saved)
                if verb == 'attachment_save':
                    proxy.client.request.reset_mock()
                    proxy.client.download.return_value = (unknown, None)
                    self.assertEqual(proxy.call(verb, args), unknown)
                    proxy.client.request.assert_not_called()
