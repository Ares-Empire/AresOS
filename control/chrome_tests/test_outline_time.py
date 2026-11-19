"""Brief 28, item 4: a read ends before its caller gives up.

`Wire` runs the real Bridge over a socket pair, with this test as the
extension at the other end: a command's time on the wire, the bridge's wait of
that time plus half a second, the late reply dropped by its id, the close at
the socket's bound. `Read` runs the adapter, and through `engine.request` the
whole call, with a fake bridge on a fake clock: a command takes the seconds the
test gives it, and one that can't answer in its time is `expired`, as the
extension answers it. The extension's side is in background.test.mjs, and the
real transports in CI (control/chrome/ci/outline-time.mjs).
"""
import contextlib
import json
import math
from pathlib import Path
import re
import select
import selectors
import socket
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.common import Refused
from aresos_control.chrome import adapter as adapter_module
from aresos_control.chrome import bridge as bridge_module
from aresos_control.chrome import deadline as deadline_module
from aresos_control.chrome.bridge import GRACE, Bridge, TimeLeft
from aresos_control.chrome.deadline import CALL, COMMANDS, FIRST_LOOK, LAST_LOOKS, NOT_READ, UNTIL
from aresos_control.daemon import Daemon
from aresos_control.definitions import BY_NAME
from aresos_control.protocol import READ_TIMEOUT
from test_engine import WORK, old_tools
from test_outline_action import Outlines, engine_with, small

ROOT = Path(__file__).resolve().parents[2]


class Times(unittest.TestCase):
    def test_the_seconds_fit_inside_the_call_and_the_clients_wait(self):
        self.assertLess(FIRST_LOOK, UNTIL)
        self.assertLess(UNTIL, COMMANDS)
        self.assertLess(COMMANDS + GRACE, CALL)
        self.assertLess(COMMANDS, LAST_LOOKS)
        # A stuck extension: a look's check is given up GRACE after its end, still before second 8.
        self.assertLess(LAST_LOOKS + GRACE, CALL)
        self.assertLess(CALL, READ_TIMEOUT)

    def test_the_socket_bound_is_the_daemons(self):
        daemon = (ROOT / 'control/aresos_control/daemon.py').read_text()
        self.assertEqual(re.findall(r'connection\.settimeout\((\d+)\)\n\s+self\.selector\.register\(connection', daemon),
                         [str(bridge_module.SOCKET_BOUND)])

    def test_a_nested_bound_keeps_the_earlier_end(self):
        bound = TimeLeft()
        self.assertIsNone(bound.end)
        with bound.bounded(10):
            with bound.bounded(20):
                self.assertEqual(bound.end, 10)
            with bound.bounded(5):
                self.assertEqual(bound.end, 5)
            self.assertEqual(bound.end, 10)
        self.assertIsNone(bound.end)


# --- the bridge on a real socket ------------------------------------------------

class Wire(unittest.TestCase):
    def setUp(self):
        self.bridge = Bridge()
        self.service, self.extension = socket.socketpair()
        self.service.settimeout(bridge_module.SOCKET_BOUND)  # as the daemon sets it
        self.extension.settimeout(5)
        self.bridge.connection = self.service
        self.events = []
        self.bridge.on_event = self.events.append
        self.waiting = b''
        self.threads = []

    def tearDown(self):
        for thread in self.threads:
            thread.join(5)
        self.bridge.close()
        self.service.close()
        self.extension.close()

    def received(self):
        """The next command the extension gets."""
        while b'\n' not in self.waiting:
            self.waiting += self.extension.recv(65536)
        line, self.waiting = self.waiting.split(b'\n', 1)
        return json.loads(line)

    def send(self, value):
        self.extension.sendall(json.dumps(value).encode() + b'\n')

    def answer(self, command, data):
        self.send({'id': command['id'], 'ok': True, 'data': data})

    def serve(self, *steps):
        """The extension in a thread of its own: each step gets the next command."""
        seen = []

        def run():
            for step in steps:
                command = self.received()
                seen.append(command)
                step(command)
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        self.threads.append(thread)
        return seen

    def nothing_sent(self):
        return not select.select([self.extension], [], [], .05)[0] and not self.waiting

    def give_up(self, seconds=.1):
        started = time.monotonic()
        with self.bridge.bounded(time.monotonic() + seconds):
            with self.assertRaises(Refused) as caught:
                self.bridge.call('outline', tab=1)
        self.assertEqual(caught.exception.code, 'expired')
        return time.monotonic() - started

    def test_a_command_inside_the_bound_carries_its_time_left_and_one_outside_none(self):
        seen = self.serve(lambda command: self.answer(command, {'state': 1}), lambda command: self.answer(command, {'read': 1}))
        with self.bridge.bounded(time.monotonic() + 2):
            self.assertEqual(self.bridge.call('page_state', tab=1), {'state': 1})
        self.assertEqual(self.bridge.call('read', tab=1), {'read': 1})
        self.threads[0].join(5)
        timed, plain = seen
        self.assertEqual(set(timed), {'id', 'time_left_ms', 'command'})
        self.assertEqual(timed['command'], {'name': 'page_state', 'tab': 1})
        self.assertIsInstance(timed['time_left_ms'], int)
        self.assertTrue(1800 <= timed['time_left_ms'] <= 2000, timed['time_left_ms'])
        # Brief 20's commands carry no time and are sent as before.
        self.assertEqual(set(plain), {'id', 'command'})

    def test_no_time_left_sends_nothing(self):
        with self.bridge.bounded(time.monotonic() - .001):
            with self.assertRaises(Refused) as caught:
                self.bridge.call('outline', tab=1)
        self.assertEqual(caught.exception.code, 'expired')
        self.assertIn('nothing was sent', str(caught.exception))
        self.assertTrue(self.nothing_sent())
        self.assertEqual(dict(self.bridge.given_up), {})

    def test_a_reply_in_time_comes_through_with_its_events(self):
        def late_but_in_time(command):
            time.sleep(.2)
            self.send({'event': 'released', 'tab': 3})
            self.answer(command, {'outline': 1})
        self.serve(late_but_in_time)
        with self.bridge.bounded(time.monotonic() + 1):
            self.assertEqual(self.bridge.call('outline', tab=1), {'outline': 1})
        self.assertEqual(self.events, [{'event': 'released', 'tab': 3}])
        self.assertEqual(dict(self.bridge.given_up), {})

    def test_the_extensions_expired_answer_is_expired(self):
        self.serve(lambda command: self.send({'id': command['id'], 'ok': False,
                                              'error': 'expired: the time of this command ran out while it waited in the queue; it was not started'}))
        with self.bridge.bounded(time.monotonic() + 1):
            with self.assertRaises(Refused) as caught:
                self.bridge.call('outline', tab=1)
        self.assertEqual(caught.exception.code, 'expired')
        self.assertEqual(dict(self.bridge.given_up), {}, 'an answer is no reply given up on')

    def test_the_extensions_refusal_of_a_malformed_time_is_invalid_input_and_the_next_command_gets_its_own(self):
        # The lead after step 10: the extension refuses a malformed time_left_ms unrun (background.test.mjs).
        refusal = 'invalid_input: time_left_ms must be a whole number of milliseconds, 0 or more; the command was not run'
        self.serve(lambda command: self.send({'id': command['id'], 'ok': False, 'error': refusal}),
                   lambda command: self.answer(command, {'state': 2}))
        with self.bridge.bounded(time.monotonic() + 1):
            with self.assertRaises(Refused) as caught:
                self.bridge.call('outline', tab=1)
            self.assertEqual(self.bridge.call('page_state', tab=1), {'state': 2})
        self.assertEqual((caught.exception.code, str(caught.exception)), ('invalid_input', refusal.partition(': ')[2]))
        self.assertIsNotNone(self.bridge.connection, 'an answer keeps the connection')
        self.assertEqual(dict(self.bridge.given_up), {})

    def test_no_reply_is_given_up_at_its_time_plus_half_a_second(self):
        elapsed = self.give_up(.3)
        self.assertGreaterEqual(elapsed, .3 + GRACE)
        self.assertLess(elapsed, .3 + GRACE + 1.0)
        self.assertIs(self.bridge.connection, self.service, 'giving up leaves the connection open')
        command = self.received()
        self.assertEqual(list(self.bridge.given_up), [command['id']])

    def test_a_late_reply_is_dropped_by_its_id_and_the_next_command_gets_its_own(self):
        import base64
        for chunked in (False, True):
            self.give_up()
            late = self.received()

            def late_then_own(command, late=late, chunked=chunked):
                # The extension's queue answers in order: the late reply, then the next command's.
                if chunked:
                    body = json.dumps({'id': late['id'], 'ok': True, 'data': {'late': 'x' * 100000}}).encode()
                    for offset in range(0, len(body), 65536):
                        self.send({'id': late['id'], 'chunk': {'offset': offset, 'total': len(body),
                                                               'bytes': base64.b64encode(body[offset:offset + 65536]).decode()}})
                else:
                    self.answer(late, {'late': True})
                self.answer(command, {'own': True})
            seen = self.serve(late_then_own)
            self.assertEqual(self.bridge.call('tabs'), {'own': True})
            self.threads[-1].join(5)
            self.assertNotEqual(seen[0]['id'], late['id'])
            self.assertIsNone(self.bridge.given_up[late['id']], 'its reply came')
        # Another unexpected id is still the transport error it was.
        self.serve(lambda command: self.send({'id': 'f' * 32, 'ok': True, 'data': {}}))
        with self.assertRaises(Refused) as caught:
            self.bridge.call('tabs')
        self.assertEqual(caught.exception.code, 'transport_error')

    def test_a_late_reply_read_between_requests_is_dropped_and_never_overdue(self):
        with patch.object(bridge_module, 'SOCKET_BOUND', .4):
            self.give_up()
            late = self.received()
            self.answer(late, {'late': True})
            daemon = Daemon.__new__(Daemon)
            daemon.selector = selectors.DefaultSelector()
            errors = []
            daemon.engine = SimpleNamespace(adapters={'chrome': SimpleNamespace(bridge=self.bridge)}, background_error=errors.append)
            try:
                daemon.drain_chrome_events(self.service)
            finally:
                daemon.selector.close()
            # The service loop hands it to on_event, where a message without an event does nothing.
            self.assertEqual(self.events, [{'id': late['id'], 'ok': True, 'data': {'late': True}}])
            self.assertEqual(errors, [])
            self.assertIsNone(self.bridge.given_up[late['id']])
            time.sleep(.5)  # past the bound it would have had
            self.serve(lambda command: self.answer(command, {'own': True}))
            self.assertEqual(self.bridge.call('tabs'), {'own': True})
            self.assertIs(self.bridge.connection, self.service)

    def closes_at_the_socket_bound(self, bound):
        with patch.object(bridge_module, 'SOCKET_BOUND', 1.0):
            started = time.monotonic()
            self.give_up(.1)
            with self.assertRaises(Refused) as caught:
                with bound():
                    self.bridge.call('tabs')
            elapsed = time.monotonic() - started
        self.assertEqual(caught.exception.code, 'transport_error')
        self.assertIsNone(self.bridge.connection)
        self.assertEqual(dict(self.bridge.given_up), {})
        self.assertGreaterEqual(elapsed, 1.0)
        self.assertLess(elapsed, 3.0, "closed at the bound (1 s here), not at the next command's wait or the socket's 15 s")

    def test_no_reply_at_all_closes_the_connection_at_the_socket_bound(self):
        self.closes_at_the_socket_bound(contextlib.nullcontext)

    def test_no_reply_at_all_closes_it_also_while_a_timed_command_waits(self):
        self.closes_at_the_socket_bound(lambda: self.bridge.bounded(time.monotonic() + 5))

    def test_an_untimed_command_waits_as_before(self):
        def slow(command):
            time.sleep(.8)
            self.answer(command, {'slow': True})
        self.serve(slow)
        self.assertEqual(self.bridge.call('read', tab=1), {'slow': True})


# --- the read and the whole call, on a fake clock --------------------------------

class Clock:
    def __init__(self):
        self.now = 5000.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += max(0.0, seconds)

    @staticmethod
    def time():
        return time.time()


NEVER = math.inf


class Timed(Outlines):
    """Outlines on the clock. A command costs `costs[(name, tab)]`, `costs[name]` or .01 seconds; a
    list is used up one value a call, a function gets the clock. With time, the bridge sends nothing once it is up, and a
    command that costs more than its time left is answered `expired` at its end, as the extension
    answers it. Without time, a command that never answers ends at the socket's bound, as PR #27's."""

    def __init__(self, clock):
        super().__init__()
        self.clock, self.costs, self.sent, self.unsent = clock, {}, [], []

    def cost(self, name, tab):
        value = self.costs.get((name, tab), self.costs.get(name, .01))
        if callable(value):
            return value(self.clock.now)
        return value.pop(0) if isinstance(value, list) else value

    def call(self, name, **args):
        tab = args.get('tab', (args.get('reference') or {}).get('tab'))
        left = None if self.end is None else self.end - self.clock.now
        if left is not None and left <= 0:
            self.unsent.append((name, tab))
            raise Refused('expired', 'Time ran out before this command was sent; nothing was sent.')
        self.sent.append((name, tab, left, self.clock.now))
        cost = self.cost(name, tab)
        if left is not None and cost >= left:
            self.clock.now = self.end
            raise Refused('expired', 'the time of this command ran out before it finished')
        if cost == NEVER:
            self.clock.now += bridge_module.SOCKET_BOUND
            raise Refused('transport_error', 'Chrome connection was cut off.')
        self.clock.now += cost
        return super().call(name, **args)

    def named(self, name):
        return [row for row in self.sent if row[0] == name]


class Read(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.clock = Clock()
        self.patches = [patch('aresos_control.engine.Boundary'), patch.object(adapter_module, 'time', self.clock),
                        patch.object(deadline_module, 'time', self.clock), old_tools()]
        for item in self.patches:
            item.start()
        self.browser = Timed(self.clock)
        for tab in range(1, 6):
            self.browser.outlines[tab] = small('Tab %d text' % tab, tab=tab)
        self.engine = engine_with(Path(self.temp.name), self.browser)
        self.chrome = self.engine.adapters['chrome']
        # The excluded sites are configured already, so no read starts with `configure`.
        self.chrome._configured_exclusions = (self.browser.session, [])
        self.start = self.clock.now

    def tearDown(self):
        self.engine.close()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def read(self, **args):
        return self.chrome.call('read', args)

    def request(self, action, **args):
        return self.engine.request({'v': 1, 'method': 'call', 'action': action, 'arguments': args})

    def seconds(self, at=None):
        return round((self.clock.now if at is None else at) - self.start, 6)

    def lefts(self, name=None, tab=None):
        """The time left each command carried, in seconds, or None."""
        return [None if left is None else round(left, 6) for sent, at, left, _ in self.browser.sent
                if (name is None or sent == name) and (tab is None or at == tab)]

    def prepare(self):
        """A reserved approval, prepared by brief 20's click (no clock: its commands carry no time)."""
        frame = self.browser.facts['frames'][0]
        target = {'reference': {'session': self.browser.session, 'tab': 1, 'frame': 0, 'document': frame['document'],
                                'view': adapter_module.view_identity(self.browser.facts), 'element': 'e1'},
                  'expected': dict(frame['target'])}
        result = self.request('chrome_old_click', **target)
        self.assertTrue(result['ok'], result)
        self.assertTrue(all(row[2] is None for row in self.browser.sent))
        self.browser.sent.clear()
        self.start = self.clock.now
        return result['data']['approval']['operation_id']

    def test_every_command_of_one_tab_carries_the_time_to_second_seven(self):
        read = self.read(tab=1)['reads'][0]
        self.assertNotIn('error', read)
        self.assertEqual([row[0] for row in self.browser.sent], ['page_state', 'outline', 'queued_steps'])
        self.assertEqual(self.lefts(), [COMMANDS, COMMANDS - .01, COMMANDS - .02])
        self.assertIsNone(self.chrome.deadline, 'the clock closes with the call')
        self.assertIsNone(self.browser.end)

    def test_a_tab_whose_reader_never_answers_is_not_read_at_second_seven(self):
        self.browser.costs[('outline', 1)] = NEVER
        result = self.read(tab=1)
        self.assertEqual(result['reads'], [{'tab': 1, 'error': {'code': 'not_read', 'message': NOT_READ}}])
        self.assertEqual(self.seconds(), COMMANDS)

    def test_five_tabs_share_the_time_left_and_a_slow_first_costs_only_its_share(self):
        self.browser.costs[('page_state', 1)] = NEVER
        result = self.read(tabs=[1, 2, 3, 4, 5])
        reads = result['reads']
        self.assertEqual(reads[0], {'tab': 1, 'error': {'code': 'not_read', 'message': NOT_READ}})
        for index in range(1, 5):
            self.assertIn('Tab %d text' % (index + 1), reads[index]['untrusted_content']['outline'])
        # Each tab's share is an equal part of what is left to second 7 when its turn comes:
        # 1.4 for the first of five; the second gets 1.4 again; then what the second didn't use passes on.
        firsts = [self.lefts('page_state', tab)[0] for tab in range(1, 6)]
        expected, now = [], 0.0
        for index, used in enumerate([NEVER, .03, .03, .03, .03]):
            share = (COMMANDS - now) / (5 - index)
            expected.append(round(share, 6))
            now += share if used == NEVER else used
        self.assertEqual(firsts, expected)
        self.assertEqual(firsts[0], 1.4)
        self.assertGreater(firsts[2], firsts[1])
        self.assertEqual(self.seconds(), round(1.4 + 4 * .03, 6), 'the slow tab cost its share, no more')

    def test_until_counts_from_the_start_of_the_call_and_never_waits_past_second_six(self):
        self.browser.outlines[1] = small('Loading', tab=1)
        self.browser.costs['outline'] = .5  # the read before the wait takes half a second
        read = self.read(tab=1, until={'text': 'never'}, timeout_ms=2000)['reads'][0]
        self.assertFalse(read['until_met'])
        polls = self.browser.named('page_state')[1:]
        self.assertTrue(polls)
        self.assertLessEqual(self.seconds(polls[-1][3]), 2.0)
        self.assertLess(self.seconds(), 2.05, 'the wait ended 2 seconds after the call began, not after the read')
        # Called directly, the adapter sees no schema: a longer timeout still ends at second 6.
        self.clock.now += 100
        self.start = self.clock.now
        self.browser.sent.clear()
        read = self.read(tab=1, until={'text': 'never'}, timeout_ms=9000)['reads'][0]
        self.assertFalse(read['until_met'])
        self.assertLess(self.seconds(), UNTIL + .05)
        self.assertGreaterEqual(self.seconds(), UNTIL)

    def test_a_malformed_time_refused_by_the_extension_fails_the_whole_call(self):
        # A fault on the service's side (the lead after step 10): no tab entry hides it, unlike not_read.
        def malformed(now):
            raise Refused('invalid_input', 'time_left_ms must be a whole number of milliseconds, 0 or more; the command was not run')
        self.browser.costs[('outline', 2)] = malformed
        with self.assertRaises(Refused) as caught:
            self.read(tabs=[1, 2, 3])
        self.assertEqual(caught.exception.code, 'invalid_input')
        self.assertEqual([row[1] for row in self.browser.named('outline')], [1, 2])

    def test_a_poll_that_runs_out_makes_the_tab_not_read(self):
        self.browser.outlines[1] = small('Loading', tab=1)
        self.browser.costs[('page_state', 1)] = [.01, .01, NEVER]
        result = self.read(tab=1, until={'text': 'never'}, timeout_ms=6000)
        self.assertEqual(result['reads'], [{'tab': 1, 'error': {'code': 'not_read', 'message': NOT_READ}}])
        self.assertEqual(self.seconds(), COMMANDS)

    def test_the_settings_command_running_out_fails_the_call_as_not_read(self):
        self.chrome._configured_exclusions = None
        self.browser.costs['configure'] = NEVER
        with self.assertRaises(Refused) as caught:
            self.read(tabs=[1, 2])
        self.assertEqual((caught.exception.code, str(caught.exception)), ('not_read', NOT_READ))
        self.assertEqual(self.seconds(), COMMANDS)

    def test_brief_20s_read_carries_no_time_with_an_approval_outstanding(self):
        self.prepare()
        self.browser.costs['validity'] = 1.5
        result = self.request('chrome_old_read', tab=1)
        self.assertTrue(result['ok'], result)
        self.assertTrue(self.browser.named('validity'))
        self.assertTrue(all(row[2] is None for row in self.browser.sent), self.browser.sent)
        self.assertEqual([row['validity'] for row in result['pending']['items']], ['current'])

    def test_brief_28s_internal_name_is_gone_and_opens_no_clock(self):
        # Brief 28a, item 8 step 1d: the read is chrome_read; chrome_outline exists nowhere, switch or not.
        self.assertNotIn('chrome_outline', BY_NAME)
        self.prepare()
        result = self.request('chrome_outline', tab=1)
        self.assertEqual(result['error']['code'], 'invalid_input')
        self.assertTrue(self.browser.named('validity'))
        self.assertTrue(all(row[2] is None for row in self.browser.sent), self.browser.sent)


class Call(Read):
    """The whole call through engine.request, as chrome_read."""

    def test_an_approval_whose_check_never_answers_is_unchecked_and_the_call_ends_in_time(self):
        operation = self.prepare()
        self.browser.costs['validity'] = NEVER
        result = self.request('chrome_read', tab=1)
        self.assertTrue(result['ok'], result)
        self.assertNotIn('error', result['data']['reads'][0])
        row = next(item for item in result['pending']['items'] if item['operation_id'] == operation)
        self.assertEqual((row['state'], row['validity'], row['reason']), ('reserved', 'unchecked', 'Awaiting exact approval; nothing submitted.'))
        self.assertNotIn('refusal_code', row)
        # The clock starts before the engine's first look, which checks by second 1; no later look asks again.
        self.assertEqual(self.lefts('validity'), [FIRST_LOOK])
        self.assertEqual(self.browser.sent[0][0], 'validity')
        self.assertLess(self.seconds(), CALL)
        self.assertEqual(self.seconds(), round(FIRST_LOOK + .03, 6))
        self.assertIsNone(self.chrome.deadline)
        # The next call checks it again, from its own start.
        self.browser.costs['validity'] = .01
        result = self.request('chrome_read', tab=1)
        row = next(item for item in result['pending']['items'] if item['operation_id'] == operation)
        self.assertEqual(row['validity'], 'current')

    def test_a_check_that_runs_out_after_the_read_is_unchecked_never_refused(self):
        operation = self.prepare()
        # It answers in the first look (which, as ordered_page walks the rows twice, asks twice),
        # and never once the read has begun.
        self.browser.costs['validity'] = lambda now: NEVER if self.chrome.deadline.reading else .01
        result = self.request('chrome_read', tab=1)
        self.assertTrue(result['ok'], result)
        row = next(item for item in result['pending']['items'] if item['operation_id'] == operation)
        self.assertEqual(row['validity'], 'unchecked')
        asked, read = self.browser.named('validity'), self.browser.named('page_state')[0][3]
        first = [row for row in asked if row[3] < read]
        later = [row for row in asked if row[3] > read]
        self.assertEqual(round(first[0][2], 6), FIRST_LOOK)
        # The read's own measure looks after its commands, with the time to second 7.25, once.
        self.assertEqual(len(later), 1, "the engine's look doesn't ask again")
        self.assertEqual(round(later[0][2] + self.seconds(later[0][3]), 6), LAST_LOOKS)
        self.assertGreater(later[0][3], self.browser.named('queued_steps')[0][3])
        self.assertEqual(self.seconds(), LAST_LOOKS)
        self.assertLess(self.seconds() + GRACE, CALL)

    def test_a_refusal_in_a_look_stays_a_refusal(self):
        operation = self.prepare()
        self.browser.facts['frames'][0]['document'] = 'another-document'
        result = self.request('chrome_read', tab=1)
        row = next(item for item in result['pending']['items'] if item['operation_id'] == operation)
        self.assertEqual((row['validity'], row['refusal_code']), ('refused', 'stale_approval'))

    def test_an_invalid_input_closes_the_clock_too(self):
        self.prepare()
        result = self.request('chrome_read', tab=1, tabs=[1, 2])
        self.assertEqual(result['error']['code'], 'invalid_input')
        self.assertIsNone(self.chrome.deadline)
        self.assertTrue(all(left is not None and left <= FIRST_LOOK for left in self.lefts('validity')))

    def test_five_tabs_through_the_engine_end_inside_the_deadline(self):
        for tab in range(1, 6):
            self.browser.costs[('outline', tab)] = 1.0
        self.browser.costs[('outline', 3)] = NEVER
        result = self.request('chrome_read', tabs=[1, 2, 3, 4, 5])
        self.assertTrue(result['ok'], result)
        self.assertEqual([read.get('error', {}).get('code') for read in result['data']['reads']], [None, None, 'not_read', None, None])
        self.assertLessEqual(self.seconds(), COMMANDS)


if __name__ == '__main__':
    unittest.main()
