"""netlog.py: the scan of Chrome's network log for case 5 (brief 18c-b, item 2).

Run: python3 -m unittest discover -s control/chrome/ci/install -p 'test_*.py'
The logs here are written by the test in the file format of --log-net-log.
"""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import netlog

OURS = 'abcdefghijklmnopabcdefghijklmnop'
PROBE = 'ponmlkjihgfedcbaponmlkjihgfedcba'
ADDRESS = 'http://localhost:18766'
FILE = f'file:///usr/share/aresos/chrome/update.xml?x=id%3D{OURS}%26v%3D1.0.0%26uc'
CHECK = f'{ADDRESS}/probe/update.xml?x=id%3D{PROBE}%26v%3D1.0.0%26uc'


def request(source, url, method='GET', **more):
    return {'params': {'url': url, 'method': method, 'load_flags': 0, **more}, 'phase': 1,
            'source': {'id': source, 'type': 1}, 'time': '1', 'type': 2}


def later(source, url):
    return {'params': {'url': url}, 'phase': 0, 'source': {'id': source, 'type': 1}, 'time': '2', 'type': 3}


def log(*events, tail=']}\n'):
    return '{"constants":{"logEventTypes":{"URL_REQUEST_START_JOB":2}},\n"events": [\n' + ',\n'.join(map(json.dumps, events)) + tail


def kinds(text):
    return [kind for kind, _ in netlog.problems(netlog.scan(text, OURS, PROBE, ADDRESS))]


class Scan(unittest.TestCase):
    def test_file_addresses_and_two_probe_checks_pass(self):
        result = netlog.scan(log(request(1, FILE), request(2, CHECK), later(2, CHECK), request(3, CHECK)), OURS, PROBE, ADDRESS)
        self.assertEqual(netlog.problems(result), [])
        self.assertEqual(result['probe_checks'], 2)
        self.assertEqual(result['hosts'], ['file:', 'localhost'])

    def test_our_id_in_any_other_address_fails(self):
        for url in (f'https://clients2.google.com/service/update2/crx?x=id%3D{OURS}%26uc',
                    f'http://localhost:18766/update.xml?x=id%3D{OURS}', f'https://example.invalid/{OURS}'):
            with self.subTest(url=url):
                self.assertIn('named', kinds(log(request(1, url), request(2, CHECK), request(3, CHECK))))

    def test_our_id_anywhere_else_in_an_event_fails(self):
        event = request(1, 'https://example.invalid/', headers=['X-Extension: ' + OURS])
        self.assertEqual(kinds(log(event, request(2, CHECK), request(3, CHECK))), ['named'])

    def test_a_request_to_the_update_service_fails_without_naming_us(self):
        post = request(1, 'https://update.googleapis.com/service/update2/json', method='POST')
        self.assertEqual(kinds(log(post, request(2, CHECK), request(3, CHECK))), ['update_service'])

    def test_one_probe_check_is_not_enough(self):
        self.assertEqual(kinds(log(request(1, FILE), request(2, CHECK), later(2, CHECK))), ['control'])
        self.assertEqual(kinds(log(request(1, FILE))), ['control'])
        # The probe's ID at another server is not its update check.
        self.assertEqual(kinds(log(request(2, CHECK), request(3, 'http://localhost:9/?x=' + PROBE))), ['control'])

    def test_a_log_cut_off_mid_write_is_still_read(self):
        cut = ',\n{"params":{"url":"https://update.googleapis.com/serv'
        self.assertEqual(kinds(log(request(1, FILE), request(2, CHECK), request(3, CHECK), tail=cut)), [])
        post = request(4, 'https://update.googleapis.com/service/update2/json', method='POST')
        self.assertEqual(kinds(log(post, request(2, CHECK), request(3, CHECK), tail=cut)), ['update_service'])

    def test_a_mention_outside_the_events_fails(self):
        tail = '],\n"polledData": {"extensions": ["' + OURS + '"], "note": "https://update.googleapis.com\\/service\\/update2\\/json"}}\n'
        result = netlog.scan(log(request(2, CHECK), request(3, CHECK), tail=tail), OURS, PROBE, ADDRESS)
        self.assertEqual(result['named_elsewhere'], [netlog.OUTSIDE])
        self.assertEqual(result['update_service'], [netlog.OUTSIDE])


if __name__ == '__main__':
    unittest.main()
