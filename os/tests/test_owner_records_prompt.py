"""Q15 must refuse a historical prompt after the USB keyboard disconnects."""
import contextlib
import json
import pathlib
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import test_owner_console as model
from test_owner_sudo_idle import relay, row, PTS


def retained_shape():
    value = json.loads((ROOT / 'os/tests/fixtures/owner-console/14zt-q15-shape.json').read_text())
    rows, cols, x, y = value['geometry']
    assert [rows, cols, x, y] == [50, 160, 0, 49]
    lines = [value['rows'].get(str(i), '').encode('ascii') for i in range(rows)]
    assert all(len(line) <= cols for line in lines)
    return bytes([rows, cols, x, y]) + b''.join(
        bytes([char, value['attribute']]) for line in lines for char in line.ljust(cols))


def stopped_prompt(raw, stage, tty='tty3', profile='de', rows=None):
    """Run the unchanged real wait/observer with an ineffective physical Enter.

    The private exact-VCSA replay also calls this function. Only count/geometry
    receipts leave its temporary directory; no raw screen data is returned.
    """
    guest = model.Guest()
    guest.raw, guest.owner_layout = raw, profile
    if rows is None:
        rows = relay()
        for entry in rows:
            if entry['tty'] == 1027: entry['tty'] = 1024 + int(tty[-1])
    guest.proc_rows = rows
    clock = model.Clock()
    commands = []
    capture = guest.capture_json
    def captured(name, source):
        commands.append((name, source))
        return capture(name, source)
    guest.capture_json = captured
    with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as directory, contextlib.ExitStack() as stack:
        target = pathlib.Path(directory)
        stack.enter_context(patch.object(model.vm.td, 'EVIDENCE', target))
        stack.enter_context(patch.object(model.vc.time, 'monotonic', clock.monotonic))
        stack.enter_context(patch.object(model.vc.time, 'sleep', clock.sleep))
        console = model.vm.Console(guest, tty)
        try: console.prompt(stage)
        except AssertionError as error: reason = str(error)
        else: raise AssertionError('Disconnected-keyboard history prompt was accepted')
        assert console.completed_epoch is None
        events = sorted((json.loads(p.read_text()) for p in target.glob('*-resync-*.json')),
                        key=lambda event: event['attempt'])
        retained = sorted(target.glob('*-timeout-*.vcsa'))
        assert retained and all(p.read_bytes() == raw for p in retained)
        snapshots = [p for p in retained if re.fullmatch(re.escape(stage) + r'-wait-\d+-timeout-\d+\.vcsa', p.name)]
        # These public fields exclude the screen's raw base64 and all text rows.
        observations = [dict(attempt=e['attempt'],enter_sent=e['enter_sent'],
            observer_ready=e['observer']['ready'],before_cursor_empty=e['before_cursor_line']=='',
            after_cursor_empty=e['after_cursor_line']=='',ready=e.get('ready',False)) for e in events]
    return dict(stage=stage,tty=tty,profile=profile,reason=reason,
        physical_keys=guest.pressed,resyncs=observations,raw_timeouts=len(snapshots),observer_timeouts=len(retained)-len(snapshots),
        completion_granted=False,commands=commands)


REMAINING = (
    ('layout-intl-proof-ready', 'tty4', 'us-intl'),
    ('layout-intl-finish-ready', 'tty3', 'us-intl'),
    ('layout-de-begin-ready', 'tty3', 'us-intl'),
    ('layout-back-de-proof-ready', 'tty4', 'de'),
    ('layout-de-finish-ready', 'tty3', 'de'),
    ('owner-rollback-ready', 'tty3', 'de'),
    ('owner-keep-stock-ready', 'tty3', 'de'),
    ('default-stock-logout-ready', 'tty3', 'de'),
)


class RecordsPromptTest(unittest.TestCase):
    def test_history_rows_are_not_a_changed_cursor_prompt(self):
        raw = retained_shape()
        full, line = model.vc.screen(raw)
        self.assertEqual(line, '')
        rows = full.split('\n')
        self.assertEqual(rows[23], 'root@bazzite:~# sudo /var/lib/ares/at title')
        self.assertEqual(rows[33], 'root@bazzite:~# sudo /var/lib/ares/at records')
        self.assertEqual(rows[34], 'PASS records')
        self.assertTrue(rows[45].startswith(model.PROMPT.decode() + '['))
        self.assertIn('HC died; cleaning up', rows[47])
        self.assertIn('USB disconnect', rows[48])
        self.assertFalse(any(re.search(r'[$#]$', value) for value in rows))

    def assert_dead(self, value):
        self.assertEqual(value['reason'], 'Physical console readiness deadline')
        self.assertEqual(value['physical_keys'], [['ret'], ['ret']])
        self.assertEqual(value['raw_timeouts'], 3)
        self.assertEqual(value['observer_timeouts'], 0)
        self.assertFalse(value['completion_granted'])
        self.assertEqual([v['attempt'] for v in value['resyncs']], [1, 2])
        self.assertTrue(all(v['observer_ready'] and v['enter_sent'] and
            v['before_cursor_empty'] and v['after_cursor_empty'] and not v['ready']
            for v in value['resyncs']))

    def test_idle_relay_and_two_ineffective_enters_never_accept_history(self):
        self.assert_dead(stopped_prompt(retained_shape(), 'corrected-stock-records-completed'))

    def test_every_remaining_shell_wait_stops_on_the_same_dead_keyboard_shape(self):
        for stage, tty, profile in REMAINING:
            with self.subTest(stage=stage,tty=tty,profile=profile):
                self.assert_dead(stopped_prompt(retained_shape(), stage, tty, profile))

    def test_busy_relay_never_receives_enter_despite_visible_history(self):
        rows = relay()
        rows[2]['tpgid'] = rows[3]['tpgid'] = 23
        rows.append(row(23, 22, 23, 21, PTS, 23, 'sleep', ['sleep', '300']))
        result = stopped_prompt(retained_shape(), 'busy-with-q15-history', rows=rows)
        self.assertEqual(result['reason'], 'Physical console idle observer refused')
        self.assertEqual(result['physical_keys'], [])
        self.assertEqual(result['raw_timeouts'], 1)
        self.assertEqual(result['observer_timeouts'], 1)
        self.assertFalse(result['resyncs'][0]['enter_sent'])


if __name__ == '__main__': unittest.main()
