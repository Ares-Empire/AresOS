"""Real loopback HTTP failures, ordinary repo files; no ISO/network dependency."""
import contextlib
import hashlib
import http.server
import json
import pathlib
import socket
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'os/ci'))
import installer_inspect as iso

BODY = bytes(range(256)) * 256
STEP = 1024


@contextlib.contextmanager
def server(behavior, checksum=None):
    requests = []
    state = {'checksum': checksum or hashlib.sha256(BODY).hexdigest()}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path == '/CHECKSUM':
                data = (state['checksum'] + '  live.iso\n').encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            assert self.path == '/live.iso'
            value = self.headers.get('Range')
            offset = int(value.removeprefix('bytes=').removesuffix('-')) if value else 0
            requests.append(value)
            reply = behavior(len(requests), offset)
            if reply is None:
                self.connection.shutdown(socket.SHUT_RDWR)
                self.close_connection = True
                return
            status, headers, data = reply
            self.send_response(status)
            for name, value in headers:
                self.send_header(name, value)
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(data)
            self.wfile.flush()
            self.close_connection = True

    host = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=lambda: host.serve_forever(poll_interval=0.01), daemon=True)
    worker.start()
    try:
        yield 'http://127.0.0.1:' + str(host.server_port), requests, state
    finally:
        host.shutdown()
        host.server_close()
        worker.join(2)
        assert not worker.is_alive()


def reply(offset, *, short=False, ignore=False, body=BODY, length=True):
    start = 0 if ignore else offset
    headers = [('Content-Length', str(len(body)-start))] if length else []
    if start:
        headers.append(('Content-Range', f'bytes {start}-{len(body)-1}/{len(body)}'))
    data = body[start:]
    return (206 if start else 200, headers, data[:STEP] if short else data)


class IsoResumeTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT/'os/tests')
        self.addCleanup(temporary.cleanup)
        self.folder = pathlib.Path(temporary.name)
        self.work, self.evidence = self.folder/'work', self.folder/'evidence'
        self.work.mkdir()
        self.evidence.mkdir()
        for name, value in (('WORK', self.work), ('EVIDENCE', self.evidence)):
            setting = patch.object(iso, name, value)
            setting.start()
            self.addCleanup(setting.stop)
        sleeper = patch.object(iso.time, 'sleep')
        self.sleep = sleeper.start()
        self.addCleanup(sleeper.stop)

    def live(self, url):
        return dict(sha256=hashlib.sha256(BODY).hexdigest(), filename='live.iso',
                    url=url+'/live.iso', checksum_source=url+'/CHECKSUM', bytes=len(BODY))

    def transfer(self, url):
        live = self.live(url)
        return iso.download_iso(live, iso.official_checksum(live))

    def record(self):
        return json.loads((self.evidence/'iso-download.json').read_text())

    def test_drop_once_then_exact_range_resumes_and_hashes_the_complete_file(self):
        with server(lambda n, offset: reply(offset, short=n == 1)) as (url, calls, _):
            result = self.transfer(url)
        self.assertEqual(calls, [None, f'bytes={STEP}-'])
        self.assertEqual((self.work/'live.iso').read_bytes(), BODY)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['downloaded_sha256'], result['official_sha256'])
        self.assertEqual([(r['offset'], r['status'], r['bytes']) for r in result['attempts']],
                         [(0, 200, STEP), (STEP, 206, len(BODY)-STEP)])
        self.assertEqual(self.record(), result)

    def test_connection_error_before_headers_retries_from_zero_and_records_it(self):
        with server(lambda n, offset: None if n == 1 else reply(offset)) as (url, calls, _):
            result = self.transfer(url)
        self.assertEqual(calls, [None, 'bytes=0-'])
        self.assertEqual(result['attempts'][0]['status'], None)
        self.assertEqual(result['attempts'][0]['outcome'], 'connection-error')
        self.assertEqual(result['attempts'][0]['bytes'], 0)
        self.assertEqual(result['status'], 'passed')

    def test_ignored_range_restarts_file_and_hash_in_the_same_attempt_budget(self):
        with server(lambda n, offset: reply(offset, short=n == 1, ignore=n > 1)) as (url, calls, _):
            result = self.transfer(url)
        self.assertEqual(calls, [None, f'bytes={STEP}-'])
        self.assertEqual((self.work/'live.iso').read_bytes(), BODY)
        self.assertEqual(result['attempts'][1]['applied_offset'], 0)
        self.assertTrue(result['attempts'][1]['restarted'])
        self.assertEqual(result['attempts'][1]['bytes'], len(BODY))

    def test_empty_ignored_range_resets_received_total_and_the_next_request(self):
        def behavior(n, offset):
            status, headers, data = reply(offset, short=n == 1, ignore=n == 2)
            return status, headers, b'' if n == 2 else data
        with server(behavior) as (url, calls, _):
            result = self.transfer(url)
        self.assertEqual(calls, [None, f'bytes={STEP}-', 'bytes=0-'])
        self.assertEqual(result['attempts'][1]['received_total'], 0)
        self.assertEqual(result['status'], 'passed')

    def test_always_drops_stops_after_six_including_ignored_range_restarts(self):
        for ignore in (False, True):
            with self.subTest(ignore=ignore), server(lambda n, offset: reply(offset, short=True, ignore=ignore)) as (url, calls, _):
                with self.assertRaisesRegex(IOError, 'exhausted 6 attempts'):
                    self.transfer(url)
            observed = self.record()
            self.assertEqual(len(calls), 6)
            self.assertEqual(len(observed['attempts']), 6)
            self.assertEqual(observed['status'], 'stopped')
            self.assertEqual(observed['bytes'], STEP if ignore else 6*STEP)
        self.assertEqual([c.args[0] for c in self.sleep.call_args_list], [1, 2, 3, 4, 5]*2)

    def test_wrong_content_range_stops_before_appending_or_a_third_request(self):
        for content_range in (f'bytes {STEP+1}-{len(BODY)-1}/{len(BODY)}',
                              f'bytes {STEP}-{len(BODY)-1}/{len(BODY)+1}',
                              f'bytes {STEP}-{STEP-1}/{len(BODY)}',
                              f'bytes {STEP}-{len(BODY)-1}/*', None):
            def behavior(n, offset):
                if n == 1:
                    return reply(offset, short=True)
                headers = [('Content-Length', str(len(BODY)-offset))]
                if content_range is not None:
                    headers.append(('Content-Range', content_range))
                return 206, headers, BODY[offset:]
            with self.subTest(content_range=content_range), server(behavior) as (url, calls, _):
                with self.assertRaisesRegex(iso.DownloadProtocolError, 'Content-Range'):
                    self.transfer(url)
            self.assertEqual(len(calls), 2)
            self.assertEqual((self.work/'live.iso').read_bytes(), BODY[:STEP])
            self.assertEqual(self.record()['attempts'][-1]['outcome'], 'stopped')

    def test_duplicate_or_incorrect_length_stops_without_download_retry(self):
        for headers in ([('Content-Length', str(len(BODY)-1))],
                        [('Content-Length', str(len(BODY)))]*2):
            with self.subTest(headers=headers), server(lambda n, offset: (200, headers, b'')) as (url, calls, _):
                with self.assertRaises(iso.DownloadProtocolError):
                    self.transfer(url)
            self.assertEqual(len(calls), 1)
            self.assertEqual(self.record()['bytes'], 0)
            self.assertEqual(self.record()['status'], 'stopped')

    def test_missing_length_can_complete_but_an_oversized_body_stops(self):
        with server(lambda n, offset: reply(offset, length=False)) as (url, _, _):
            self.assertEqual(self.transfer(url)['status'], 'passed')
        with server(lambda n, offset: reply(offset, length=False, body=BODY+b'x')) as (url, calls, _):
            with self.assertRaisesRegex(iso.DownloadProtocolError, 'exceeds'):
                self.transfer(url)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.record()['status'], 'stopped')

    def test_changed_file_between_ranges_stops_on_final_pin_hash(self):
        with server(lambda n, offset: reply(offset, short=n == 1, body=BODY if n == 1 else b'x'*len(BODY))) as (url, calls, _):
            with self.assertRaisesRegex(AssertionError, 'Downloaded ISO differs'):
                self.transfer(url)
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.record()['bytes'], len(BODY))
        self.assertEqual(self.record()['status'], 'stopped')

    def test_fresh_official_checksum_and_direct_validation_never_accept_a_mismatch(self):
        with server(lambda n, offset: reply(offset)) as (url, calls, state):
            live = self.live(url)
            self.assertEqual(iso.official_checksum(live), live['sha256'])
            state['checksum'] = 'b'*64
            with self.assertRaisesRegex(AssertionError, 'Official checksum changed'):
                iso.official_checksum(live)
            with self.assertRaisesRegex(AssertionError, 'Official checksum changed'):
                iso.download_iso(live, 'b'*64)
        self.assertEqual(calls, [])
        self.assertEqual(self.record()['attempts'], [])
        with self.assertRaisesRegex(AssertionError, 'Official checksum changed'):
            iso.validate_download(dict(bytes=len(BODY), downloaded_sha256=live['sha256'], official_sha256='b'*64), live)

    def test_http_refusal_is_recorded_and_does_not_retry_credentials_or_status(self):
        with server(lambda n, offset: (403, [('Content-Length', '0')], b'')) as (url, calls, _):
            with self.assertRaisesRegex(iso.DownloadProtocolError, 'HTTP error 403'):
                self.transfer(url)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.record()['attempts'][0]['status'], 403)
        self.assertEqual(self.record()['status'], 'stopped')

    def test_missing_or_invalid_size_pin_refuses_before_any_request(self):
        with server(lambda n, offset: reply(offset)) as (url, calls, _):
            for value in (None, True, -1, 0, '65536'):
                with self.subTest(value=value), self.assertRaisesRegex(AssertionError, 'pinned ISO size'):
                    iso.download_iso(dict(self.live(url), bytes=value), self.live(url)['sha256'])
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
