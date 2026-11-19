"""Package 25, the guardian: the supervisor's state machine with FakeRunner (brief sections 1, 2 and 4).

Step 1 covers section 1: the lifecycle channel's gate, the hello, what counts as saved, one request in flight and
one waiting, and each caller's own deadline. Step 2 covers section 2, the one stop routine, driven as the socket op
`stop` drives it. Step 3 covers 3.2 and 3.3: the session ending under the supervisor (a signal, labwc), `restart`
and `logout`. Step 4 covers 3.4: when the screens go black and when the black screen ends, and the lid block.
Step 5 covers section 4, package 48's leftovers: world folders that are moved aside or named. Every folder a test
makes, moves or reads is in its own temporary home; nothing here starts a process.
"""
import ast
import configparser
import contextlib
import fcntl
import io
import itertools
import json
import os
import pathlib
import re
import shutil
import time
import unittest
from unittest import mock

import test_aresos_desktop as base

desktop, wrapper = base.desktop, base.wrapper
ROOT = base.ROOT
GATE = 'ARESOS_DESKTOP_LIFECYCLE'
DATED = 'AresHub-2026-11-19'


# The keys of desktop.json that release R28's supervisor reads and writes, frozen here: R28 reads the file after a
# rollback (`previous`), so the file stays schema 1 and every later key is optional (brief 2.3).
R28_KEYS = ('schema', 'latched', 'reason', 'detail', 'consecutive', 'failures', 'hub_seen', 'accounted',
            'disposition', 'unresolved')


def r28_load(data):
    """What R28's Persisted.load makes of a desktop.json, key by key (frozen with the list above)."""
    assert isinstance(data, dict) and data.get('schema') == 1
    return dict(latched=bool(data.get('latched')), reason=data.get('reason'), detail=str(data.get('detail', '')),
                consecutive=int(data.get('consecutive', 0)),
                failures=[float(t) for t in data.get('failures', []) if isinstance(t, (int, float))],
                hub_seen=bool(data.get('hub_seen')),
                accounted=data.get('accounted') if isinstance(data.get('accounted'), str) else None,
                disposition=data.get('disposition') if isinstance(data.get('disposition'), dict) else None,
                unresolved=data.get('unresolved') if isinstance(data.get('unresolved'), dict) else None)


class StopRunner(base.FakeRunner):
    """FakeRunner with what a stop needs: systemd's word on a shutdown, and SIGTERM through the watched pidfd."""

    def __init__(self):
        super().__init__()
        self.system = None  # True: the system is stopping; False: clearly not; None: no clear answer
        self.signals = []
        # The session's labwc (3.2): what watching it comes to, each (pid, runtime folder) asked for, and every
        # SIGTERM sent through its pidfd.
        self.labwc = 'watched'
        self.labwc_watches = []
        self.labwc_signals = 0
        # The black screen and the lid block (3.4): each start's limit, whether one is up, and the kill time each
        # stop was given. An error to raise stands for a program that cannot be started.
        self.blacks, self.black_up, self.black_stops, self.black_error = [], False, [], None
        self.lid_blocks, self.lid_up, self.lid_stops, self.lid_error = [], False, [], None
        self.behind_black = []  # for each message window: whether the black screen was up when it opened

    def show_view(self, text):
        self.behind_black.append(self.black_up)
        super().show_view(text)

    def start_black(self, limit):
        if self.black_error is not None:
            raise self.black_error
        self.blacks.append(limit)
        self.black_up = True

    def stop_black(self, kill_at):
        running, self.black_up = self.black_up, False
        if running:
            self.black_stops.append(kill_at)
        return running

    def start_lid_block(self, limit):
        if self.lid_error is not None:
            raise self.lid_error
        self.lid_blocks.append(limit)
        self.lid_up = True

    def stop_lid_block(self, kill_at):
        running, self.lid_up = self.lid_up, False
        if running:
            self.lid_stops.append(kill_at)
        return running

    def system_stopping(self):
        return self.system

    def watch_labwc(self, pid, runtime):
        self.labwc_watches.append((pid, runtime))
        return self.labwc

    def signal_labwc(self):
        self.labwc_signals += 1
        return True

    def signal_jvm(self):
        self.signals.append('SIGTERM')
        return True


class FakePeer:
    """A connection as the supervisor sees it: a PID and a uid, lines it takes (or not), and whether it is closed."""

    def __init__(self, pid, uid=None, takes=True):
        self.pid = pid
        self.uid = os.getuid() if uid is None else uid
        self.takes = takes
        self.sent = []
        self.closed = False

    def send(self, message):
        if self.closed or not self.takes:
            return False
        self.sent.append(message)
        return True

    def close(self):
        self.closed = True


class GuardianBase(base.Base):
    def setUp(self):
        super().setUp()
        self.runner = StopRunner()
        desktop.provision(self.paths, self.lock)
        base.make_world(self.paths, self.lock)

    def game(self):
        """A supervisor whose hub launch runs a game: (supervisor, the game's PID). Each call starts from a session
        with nothing running, so one test can go through several cases."""
        self.runner = StopRunner()
        for path in (self.paths.runtime_file, self.paths.stop_block):
            pathlib.Path(path).unlink(missing_ok=True)
        sup = self.supervisor()
        sup.start()
        pid, _ = self.run_game(sup)
        return sup, pid

    def hello(self, sup, **changes):
        message = {'op': 'lifecycle_hello', 'major': 1, 'minor': 0, 'instance': sup.instance,
                   'nonce': sup.launch.nonce if sup.launch else 'none', 'capabilities': ['save_world']}
        message.update(changes)
        return {key: value for key, value in message.items() if value is not ...}

    def connected(self):
        """(supervisor, game PID, its accepted lifecycle peer)."""
        sup, pid = self.game()
        peer = FakePeer(pid)
        self.assertTrue(sup.on_lifecycle_hello(peer, self.hello(sup)))
        return sup, pid, peer

    def ask(self, sup, reason='manual', wait=None):
        """One caller: the list its result lands in."""
        results = []
        sup.request_save(reason, results.append, wait)
        return results

    @staticmethod
    def saved(ident, world='AresHub', **changes):
        answer = {'op': 'world_saved', 'id': ident, 'ok': True, 'ms': 12, 'world': {'id': world, 'desktop': True}}
        answer.update(changes)
        return answer

    @staticmethod
    def refused(ident, reason):
        return {'op': 'world_saved', 'id': ident, 'ok': False, 'reason': reason}

    def save_deadlines(self, sup):
        """The callers' deadlines the supervisor still waits for."""
        return [at for at, action in sup.pending() if action == sup.save_timed_out]

    def dated_world(self, name=DATED, **changes):
        return base.make_world(self.paths, dict(self.lock, world=name), **changes)


class GateTest(GuardianBase):
    """1.1: only the game gets ARESOS_DESKTOP_LIFECYCLE=1, and only from the supervisor."""

    def test_the_game_gets_the_gate_from_the_supervisor(self):
        sup = self.supervisor()
        sup.start()
        _, env = self.run_game(sup)
        self.assertEqual(env[GATE], '1')
        self.assertEqual(desktop.game_environment('d', 'n' * 32, nvidia=False)[GATE], '1')
        self.assertIn(GATE, wrapper.SUPPLIED)

    def test_prism_the_helper_and_the_windows_never_get_it(self):
        environ = {'HOME': self.paths.home, 'XDG_RUNTIME_DIR': self.paths.runtime, 'PATH': '/usr/bin', GATE: '1'}
        sup = desktop.Supervisor(self.paths, self.lock, self.runner, clock=lambda: self.now[0],
                                 wall=lambda: self.wall[0], nvidia=False, environ=environ)
        sup.start()
        self.run_game(sup)
        (_, prism_env), = self.runner.prisms
        self.assertNotIn(GATE, prism_env)
        for _, _, helper_env in self.runner.helpers:
            self.assertNotIn(GATE, helper_env)
        # The message windows and the covers start from session_environment() too (Runner.show_view, start_cover).
        self.assertNotIn(GATE, desktop.session_environment(environ))
        self.assertIn(GATE, desktop.PRIVATE_ENVIRONMENT)

    def test_the_wrapper_drops_an_inherited_gate(self):
        prism = {'HOME': '/home/owner', GATE: '1', 'INST_ID': 'AresDesktop'}
        self.assertEqual(wrapper.game_environment(prism, {}), {'HOME': '/home/owner', 'INST_ID': 'AresDesktop'})
        self.assertEqual(wrapper.game_environment(dict(prism, **{GATE: '0'}), {GATE: '1'})[GATE], '1')

    def test_the_names_equal_the_mods(self):
        java = (ROOT / 'mod/src/main/java/dev/aresos/shell/LifecycleClient.java').read_text(encoding='utf-8')
        self.assertEqual(re.search(r'String GATE = "(\w+)"', java).group(1), desktop.LIFECYCLE_GATE)
        self.assertEqual(int(re.search(r'int MAJOR = (\d+);', java).group(1)), desktop.LIFECYCLE_MAJOR)
        reasons = re.search(r'REASONS = Set\.of\(([^)]*)\)', java).group(1)
        self.assertEqual(set(re.findall(r'"(\w+)"', reasons)), set(desktop.SAVE_REFUSALS))
        self.assertIn('CAPABILITIES = List.of("save_world")', java)
        self.assertEqual(desktop.LIFECYCLE_GATE, GATE)


class HelloTest(GuardianBase):
    """1.2: who may open the lifecycle channel."""

    def test_the_games_hello_is_accepted_and_status_says_so(self):
        sup, pid = self.game()
        self.assertIs(sup.status()['lifecycle'], False)
        peer = FakePeer(pid)
        self.assertTrue(sup.on_lifecycle_hello(peer, self.hello(sup)))
        self.assertIs(sup.status()['lifecycle'], True)
        self.assertEqual(peer.sent, [])  # no reply: the mod expects none
        self.assertFalse(peer.closed)

    def test_each_way_a_hello_is_refused(self):
        sup, pid = self.game()
        other = pid + 1
        self.runner.processes[other] = (1, other * 7, '')
        cases = {
            'another user': (FakePeer(pid, uid=os.getuid() + 1), {}),
            'another process': (FakePeer(other), {}),
            'another session': (FakePeer(pid), {'instance': 'aresdesktop-000000000000'}),
            'no instance': (FakePeer(pid), {'instance': ...}),
            'a wrong nonce': (FakePeer(pid), {'nonce': 'wrong-nonce-wrong-nonce-wrong-nonce'}),
            'a nonce that is no text': (FakePeer(pid), {'nonce': 7}),
            'a nonce with a broken character': (FakePeer(pid), {'nonce': '\ud800'}),
            'no nonce': (FakePeer(pid), {'nonce': ...}),
            'major 2': (FakePeer(pid), {'major': 2}),
            'major true': (FakePeer(pid), {'major': True}),
            'major 1.0': (FakePeer(pid), {'major': 1.0}),
            'no major': (FakePeer(pid), {'major': ...}),
            'no capabilities': (FakePeer(pid), {'capabilities': ...}),
            'other capabilities': (FakePeer(pid), {'capabilities': ['prepare_stop']}),
            'capabilities as text': (FakePeer(pid), {'capabilities': 'save_world'}),
        }
        desktop.LOG.disabled = False
        self.addCleanup(setattr, desktop.LOG, 'disabled', True)
        for name, (peer, changes) in cases.items():
            with self.subTest(name), self.assertLogs('aresos-desktop', 'WARNING') as logs:
                self.assertFalse(sup.on_lifecycle_hello(peer, self.hello(sup, **changes)))
                self.assertIs(sup.status()['lifecycle'], False)
                self.assertEqual(len(logs.output), 1)  # one log line, never a nonce
                self.assertNotIn(sup.launch.nonce, logs.output[0])
                self.assertNotIn('wrong-nonce', logs.output[0])
                self.assertEqual(self.ask(sup)[0].result, 'no_channel')

    def test_a_hello_before_the_wrapper_reported_the_jvm_is_refused_and_the_next_one_accepted(self):
        sup = self.supervisor()
        sup.start()
        ok, reply = sup.on_jvm_start(self.jvm_request())
        self.assertTrue(ok)
        pid = 4321
        self.runner.processes[pid] = (4320, pid * 7, f'0::/user.slice/aresos.slice/{reply["unit"]}\n')
        self.assertFalse(sup.on_lifecycle_hello(FakePeer(pid), self.hello(sup)))
        self.assertEqual(sup.on_jvm_started(4320, pid, reply['launch']), (True, ''))
        self.assertTrue(sup.on_lifecycle_hello(FakePeer(pid), self.hello(sup)))  # the mod tries again

    def test_a_game_that_is_gone_or_was_replaced_is_refused(self):
        sup, pid = self.game()
        self.runner.processes[pid] = (self.runner.processes[pid][0], 1)  # the PID is another process now
        self.assertFalse(sup.on_lifecycle_hello(FakePeer(pid), self.hello(sup)))
        sup, pid = self.game()
        sup.on_jvm_gone()  # its pidfd fired; the end is not decided yet
        self.assertFalse(sup.on_lifecycle_hello(FakePeer(pid), self.hello(sup)))
        self.assertFalse(desktop.Supervisor.on_lifecycle_hello(self.supervisor(), FakePeer(pid), self.hello(sup)))

    def test_a_newer_hello_replaces_the_older(self):
        sup, pid, old = self.connected()
        first, second = self.ask(sup), self.ask(sup)
        self.assertEqual(old.sent, [{'op': 'save_world', 'id': 1, 'reason': 'manual'}])
        new = FakePeer(pid)
        self.assertTrue(sup.on_lifecycle_hello(new, self.hello(sup)))
        self.assertTrue(old.closed)
        self.assertIs(sup.status()['lifecycle'], True)
        # What went out on the older connection is lost; what waited goes out on the new one.
        self.assertEqual([result.result for result in first], ['lost'])
        self.assertEqual(new.sent, [{'op': 'save_world', 'id': 2, 'reason': 'manual'}])
        sup.on_lifecycle_gone(old)  # the loop reports the closed connection: nothing changes
        self.assertIs(sup.status()['lifecycle'], True)
        # An answer on the older connection is dropped, also with the id now in flight.
        sup.on_lifecycle_message(old, self.saved(2))
        self.assertEqual(second, [])
        sup.on_lifecycle_message(new, self.saved(2))
        self.assertEqual([result.result for result in second], ['saved'])

    def test_the_channel_ends_with_the_game(self):
        sup, pid, peer = self.connected()
        results = self.ask(sup)
        self.end_game(sup, pid, 0)
        self.assertTrue(peer.closed)
        self.assertIs(sup.status()['lifecycle'], False)
        self.assertEqual([result.result for result in results], ['lost'])  # never a save
        self.assertFalse(sup.on_lifecycle_hello(FakePeer(pid), self.hello(sup)))

    def test_a_replacement_supervisor_accepts_the_adopted_games_hello(self):
        first, pid = self.game()
        sup = self.supervisor()
        sup.start()
        self.assertTrue(sup.launch.adopted)
        self.assertFalse(sup.on_lifecycle_hello(FakePeer(pid), self.hello(sup, nonce='n' * 32)))
        peer = FakePeer(pid)
        self.assertTrue(sup.on_lifecycle_hello(peer, self.hello(sup, instance=first.instance,
                                                               nonce=first.launch.nonce)))
        # With a dead helper nothing was reported ready: the locked world is the active one, and it saves.
        results = self.ask(sup, 'shutdown')
        sup.on_lifecycle_message(peer, self.saved(1))
        self.assertEqual((results[0].result, results[0].world), ('saved', 'AresHub'))


class SavedTest(GuardianBase):
    """1.3: what counts as saved."""

    def test_a_save_is_asked_and_confirmed(self):
        sup, pid, peer = self.connected()
        for ident, reason in enumerate(desktop.SAVE_REASONS, 1):
            results = self.ask(sup, reason)
            self.assertEqual(peer.sent[-1], {'op': 'save_world', 'id': ident, 'reason': reason})  # ids count up
            self.assertEqual(results, [])
            sup.on_lifecycle_message(peer, self.saved(ident))
            self.assertEqual(results, [desktop.SaveResult('saved', 'AresHub', ms=12)])
            self.assertTrue(results[0].saved)
        self.assertEqual(desktop.SAVE_REASONS, ('shutdown', 'backup', 'update', 'manual'))

    def test_without_an_accepted_hello_nothing_is_saved(self):
        sup, pid = self.game()
        self.assertEqual(self.ask(sup), [desktop.SaveResult('no_channel', 'AresHub')])
        self.assertEqual(self.ask(self.supervisor()), [desktop.SaveResult('no_channel', 'AresHub')])

    def test_every_answer_that_is_not_a_save(self):
        cases = {
            'no_world': (self.refused(1, 'no_world'), ('refused', 'no_world')),
            'not_desktop_world': (self.refused(1, 'not_desktop_world'), ('refused', 'not_desktop_world')),
            'server_stopping': (self.refused(1, 'server_stopping'), ('refused', 'server_stopping')),
            'error': (self.refused(1, 'error'), ('refused', 'error')),
            'an unknown refusal': (self.refused(1, 'busy'), ('invalid', None)),
            'a refusal without a reason': ({'op': 'world_saved', 'id': 1, 'ok': False}, ('invalid', None)),
            'no ok': ({'op': 'world_saved', 'id': 1, 'world': {'id': 'AresHub', 'desktop': True}}, ('invalid', None)),
            'ok as text': (self.saved(1, ok='true'), ('invalid', None)),
            'ok as a number': (self.saved(1, ok=1), ('invalid', None)),
            'no world': (dict(self.saved(1), world=None), ('invalid', None)),
            'the world as text': (dict(self.saved(1), world='AresHub'), ('invalid', None)),
            'a world without an id': (dict(self.saved(1), world={'desktop': True}), ('invalid', None)),
            'a world whose id is no text': (dict(self.saved(1), world={'id': 7, 'desktop': True}),
                                            ('invalid', None)),
            'another world': (self.saved(1, world='Other'), ('wrong_world', None)),
            'a world that is no desktop': (dict(self.saved(1), world={'id': 'AresHub', 'desktop': False}),
                                           ('wrong_world', None)),
            'a world without the desktop mark': (dict(self.saved(1), world={'id': 'AresHub'}),
                                                 ('wrong_world', None)),
            'a desktop mark that is no boolean': (dict(self.saved(1), world={'id': 'AresHub', 'desktop': 1}),
                                                  ('wrong_world', None)),
        }
        for name, (answer, expected) in cases.items():
            with self.subTest(name):
                sup, pid, peer = self.connected()
                results = self.ask(sup)
                sup.on_lifecycle_message(peer, answer)
                self.assertEqual([(result.result, result.reason) for result in results], [expected])
                self.assertFalse(results[0].saved)
                self.assertEqual(results[0].world, 'AresHub')
                self.assertFalse(desktop.save_reply(results[0])['ok'])
                self.assertTrue(desktop.save_reply(results[0])['message'].startswith('Not saved: '))

    def test_an_answer_with_a_wrong_id_is_dropped_and_the_request_stays_in_flight(self):
        sup, pid, peer = self.connected()
        results = self.ask(sup)
        for ident in (2, 0, '1', True, 1.0, None, [1]):
            sup.on_lifecycle_message(peer, self.saved(ident))
            self.assertEqual(results, [], ident)
        for line in ({'op': 'save_world', 'id': 1}, {'op': 'lifecycle_hello'}, {'id': 1, 'ok': True}, [], 'text', 7):
            sup.on_lifecycle_message(peer, line)  # after the hello only world_saved is read
            self.assertEqual(results, [])
        sup.on_lifecycle_message(peer, self.saved(1))
        self.assertEqual([result.result for result in results], ['saved'])
        sup.on_lifecycle_message(peer, self.saved(1))  # twice: the second belongs to nothing
        self.assertEqual(len(results), 1)

    def test_an_answer_after_the_active_world_changed_is_not_a_save(self):
        sup, pid, peer = self.connected()
        self.ready(sup)
        self.dated_world()
        results = self.ask(sup)
        self.heartbeat(sup, world=DATED)  # he opened a dated home while the save ran
        self.assertEqual(sup.active_world(), DATED)
        sup.on_lifecycle_message(peer, self.saved(1))
        self.assertEqual([(result.result, result.world) for result in results], [('wrong_world', 'AresHub')])
        # The next request is about the dated home: only an answer that names it is a save.
        results = self.ask(sup)
        sup.on_lifecycle_message(peer, self.saved(2))
        self.assertEqual([(result.result, result.world) for result in results], [('wrong_world', DATED)])
        results = self.ask(sup)
        sup.on_lifecycle_message(peer, self.saved(3, world=DATED))
        self.assertEqual(results, [desktop.SaveResult('saved', DATED, ms=12)])

    def test_only_a_plain_folder_that_passes_the_home_checks_becomes_the_active_world(self):
        sup, pid, peer = self.connected()
        self.assertEqual(sup.active_world(), 'AresHub')  # none reported: the locked world
        self.ready(sup)
        self.assertEqual(sup.launch.active_world, 'AresHub')
        self.dated_world('AresHub-damaged', marker=None)
        outside = self.root / 'outside'
        base.make_world(desktop.Paths(str(outside), self.paths.runtime, self.paths.share), self.lock)
        real = pathlib.Path(outside, '.local/share/aresos/worlds/AresHub')
        os.symlink(real, pathlib.Path(self.paths.worlds, 'AresHub-link'))
        for name in ('AresHub-damaged', 'AresHub-missing', 'AresHub-link', '../AresHub', str(real), '.', '..', '',
                     'AresHub/../AresHub', 'a\0b'):
            with self.subTest(name):
                self.heartbeat(sup, world=name)
                self.assertEqual(sup.active_world(), 'AresHub')
        self.dated_world()
        self.heartbeat(sup, world=DATED)
        self.assertEqual(sup.active_world(), DATED)
        self.heartbeat(sup, ready=False)  # leaving the world does not change what a save is about
        self.assertEqual(sup.active_world(), DATED)
        self.heartbeat(sup)
        self.assertEqual(sup.active_world(), 'AresHub')

    def test_the_reply_names_the_world_and_the_texts(self):
        result = desktop.SaveResult
        texts = {
            result('saved', 'AresHub', ms=3): 'Saved: AresHub is on the disk.',
            result('refused', 'AresHub', reason='no_world'):
                'Not saved: no home is open in Minecraft right now (it is loading, switching homes or closing).',
            result('refused', 'AresHub', reason='not_desktop_world'):
                'Not saved: the world open in Minecraft is not an AresOS home.',
            result('refused', 'AresHub', reason='server_stopping'):
                'Not saved: Minecraft is closing the world right now.',
            result('refused', 'AresHub', reason='error'):
                'Not saved: Minecraft could not write AresHub to the disk; its log says why.',
            result('wrong_world', 'AresHub', detail='Minecraft saved Other, which is not the home AresHub'):
                'Not saved: Minecraft saved Other, which is not the home AresHub.',
            result('timeout', 'AresHub'): 'Not saved: Minecraft did not answer in time.',
            result('lost', 'AresHub'): 'Not saved: the connection to Minecraft closed before it answered.',
            result('no_channel', 'AresHub'): 'Not saved: Minecraft is not running, or has not connected to AresOS yet.',
            result('invalid', 'AresHub', detail='the answer names no world'):
                'Not saved: Minecraft\'s answer could not be used (the answer names no world).',
        }
        for value, text in texts.items():
            self.assertEqual(desktop.save_text(value), text)
            self.assertEqual(desktop.save_reply(value), dict(ok=value.result == 'saved', result=value.result,
                                                             world='AresHub', reason=value.reason, ms=value.ms,
                                                             message=text))
        self.assertEqual(desktop.clip('a\nb\x1b[31m' + 'x' * 100), ('a?b?[31m' + 'x' * 100)[:48])


class JoiningTest(GuardianBase):
    """1.4: one request in flight, one waiting, and each caller's own deadline."""

    def test_five_callers_on_one_request_in_flight_and_one_waiting(self):
        sup, pid, peer = self.connected()
        first = self.ask(sup, 'backup')
        later = [self.ask(sup, 'manual') for _ in range(5)]
        self.assertEqual(peer.sent, [{'op': 'save_world', 'id': 1, 'reason': 'backup'}])  # one in flight
        sup.on_lifecycle_message(peer, self.saved(1))
        self.assertEqual([result.result for result in first], ['saved'])
        self.assertEqual(later, [[]] * 5)  # the first save may have begun before they asked
        self.assertEqual(peer.sent[1:], [{'op': 'save_world', 'id': 2, 'reason': 'manual'}])  # one follow-up
        late = self.ask(sup)  # arrives while the follow-up is in flight: one more, never two
        sup.on_lifecycle_message(peer, self.refused(2, 'error'))
        self.assertEqual([[result.result for result in results] for results in later], [['refused']] * 5)
        self.assertEqual(len(peer.sent), 3)
        sup.on_lifecycle_message(peer, self.saved(3))
        self.assertEqual([result.result for result in late], ['saved'])
        self.assertEqual(self.save_deadlines(sup), [])

    def test_a_late_answer_is_dropped(self):
        sup, pid, peer = self.connected()
        results = self.ask(sup)
        self.assertEqual(self.save_deadlines(sup), [self.now[0] + desktop.SAVE_WAIT])
        self.assertLessEqual(sup.deadline(), desktop.SAVE_WAIT)  # the loop wakes for it
        self.advance(desktop.SAVE_WAIT - 1)
        sup.tick()
        self.assertEqual(results, [])
        self.advance(1)
        sup.tick()
        self.assertEqual(results, [desktop.SaveResult('timeout', 'AresHub')])
        sup.on_lifecycle_message(peer, self.saved(1))  # late: logged and dropped
        self.assertEqual(len(results), 1)
        again = self.ask(sup)
        self.assertEqual(peer.sent[-1]['id'], 2)  # the request nobody waits for was given up
        sup.on_lifecycle_message(peer, self.saved(1))  # the late answer never answers the new request
        self.assertEqual(again, [])
        sup.on_lifecycle_message(peer, self.saved(2))
        self.assertEqual([result.result for result in again], ['saved'])

    def test_each_caller_has_its_own_deadline(self):
        sup, pid, peer = self.connected()
        first = self.ask(sup, wait=10)
        self.advance(5)
        waiting = self.ask(sup, wait=10)
        patient = self.ask(sup, wait=60)
        self.advance(5)
        sup.tick()
        self.assertEqual([result.result for result in first], ['timeout'])
        self.assertEqual((waiting, patient), ([], []))
        # The request in flight has no caller left: the waiting one goes out.
        self.assertEqual([message['id'] for message in peer.sent], [1, 2])
        self.advance(5)
        sup.tick()
        self.assertEqual([result.result for result in waiting], ['timeout'])
        self.assertEqual(patient, [])
        sup.on_lifecycle_message(peer, self.saved(2))
        self.assertEqual([result.result for result in patient], ['saved'])
        self.assertEqual(self.save_deadlines(sup), [])

    def test_a_connection_that_closes_first_is_lost_and_what_waited_has_no_channel(self):
        sup, pid, peer = self.connected()
        first, waiting = self.ask(sup), self.ask(sup)
        sup.on_lifecycle_gone(peer)
        self.assertEqual([result.result for result in first], ['lost'])
        self.assertEqual([result.result for result in waiting], ['no_channel'])
        self.assertIs(sup.status()['lifecycle'], False)
        sup.on_lifecycle_message(peer, self.saved(1))  # nothing in flight any more
        self.assertEqual((len(first), len(waiting)), (1, 1))

    def test_a_peer_that_does_not_take_the_request_is_lost(self):
        sup, pid, peer = self.connected()
        peer.takes = False
        self.assertEqual([result.result for result in self.ask(sup)], ['lost'])
        self.assertIs(sup.status()['lifecycle'], False)

    def test_a_caller_that_fails_does_not_take_the_others_answer(self):
        sup, pid, peer = self.connected()
        first = self.ask(sup)
        results = []
        sup.request_save('manual', lambda result: 1 / 0)
        sup.request_save('manual', results.append)
        sup.on_lifecycle_message(peer, self.saved(1))
        sup.on_lifecycle_message(peer, self.saved(2))
        self.assertEqual([result.result for result in first + results], ['saved', 'saved'])

    def test_a_caller_may_ask_again_from_its_answer(self):
        sup, pid, peer = self.connected()
        results = []

        def again(result):
            results.append(result.result)
            if len(results) < 3:
                sup.request_save('shutdown', again)
        sup.request_save('shutdown', again)
        for ident in (1, 2):
            sup.on_lifecycle_message(peer, self.refused(ident, 'no_world'))
        sup.on_lifecycle_message(peer, self.saved(3))
        self.assertEqual(results, ['refused', 'refused', 'saved'])
        self.assertEqual([message['id'] for message in peer.sent], [1, 2, 3])


class StopBase(GuardianBase):
    """Section 2: one stop routine."""

    def stop(self, sup, kind='stop'):
        """One caller of a stop: the list its reply lands in."""
        replies = []
        sup.request_stop(kind, replies.append)
        return replies

    def record(self):
        return self.stored().get('stop')

    def confirm(self, sup, peer, ident=1):
        """The game answers that the home is saved; the stop goes on to the close."""
        sup.on_lifecycle_message(peer, self.saved(ident))
        sup.tick()

    def next_session(self):
        """The machine went down and came up: no process, and a new runtime folder."""
        self.runner = StopRunner()
        for path in (self.paths.runtime_file, self.paths.stop_block):
            pathlib.Path(path).unlink(missing_ok=True)
        sup = self.supervisor()
        sup.start()
        return sup


class StopTest(StopBase):
    def test_a_stop_records_saves_closes_and_waits_for_the_exit_and_the_lock(self):
        sup, pid, peer = self.connected()  # the helper never reported a world (a dead helper): the locked one
        views = len(self.runner.views)
        replies = self.stop(sup)
        self.assertEqual((sup.state, sup.status()['stopping']), ('STOPPING', True))
        self.assertEqual(peer.sent, [{'op': 'save_world', 'id': 1, 'reason': 'shutdown'}])
        record = self.record()  # written before the save was asked
        self.assertEqual((record['open'], record['launch'], record['kind'], record['started'], record['sigterm']),
                         (True, sup.launch.id, 'stop', self.wall[0], False))
        self.assertEqual(self.runner.signals, [])  # nothing is closed before the save is confirmed
        self.confirm(sup, peer)
        self.assertEqual(self.runner.signals, ['SIGTERM'])
        self.assertEqual((self.record()['sigterm'], self.record()['save'], self.record()['open']),
                         (True, 'saved', True))
        self.runner.lock_held = True
        self.end_game(sup, pid, 143)
        self.assertEqual(replies, [])  # Java is gone, but its wrapper still holds the desktop lock
        self.assertEqual(len(self.runner.views), views)  # no message window while the stop runs
        self.runner.lock_held = False
        self.advance(desktop.STOP_LOCK_CHECK)
        sup.tick()
        (reply,) = replies
        self.assertEqual((reply['ok'], reply['result'], reply['save'], reply['close'], reply['recorded']),
                         (True, 'confirmed', 'saved', 'exited', True))
        self.assertEqual(reply['message'], 'Stopped: the home was saved first; Minecraft closed.')
        self.assertEqual((sup.state, sup.reason, sup.stop), ('RECOVERY', 'quit', None))
        stored = self.stored()
        self.assertEqual((stored['stop']['open'], stored['stop']['close'], stored['stop']['status']),
                         (False, 'exited', 143))
        self.assertEqual((stored['accounted'], stored['latched'], stored['consecutive'], stored['failures']),
                         (sup.launch.id, False, 0, []))
        self.assertIsNone(sup.retry_at)

    def test_a_stop_goes_on_at_once_on_a_clock_that_moves_between_two_readings(self):
        # The real clock: tick() reads it, and whatever says "due now" reads it a moment later (the loop test
        # found a stop that waited for its deadline this way).
        sup, pid, peer = self.connected()
        readings = itertools.count()
        sup.clock = lambda: self.now[0] + next(readings) * 1e-6
        replies = self.stop(sup)
        self.assertEqual(len(peer.sent), 1)
        self.confirm(sup, peer)
        self.assertEqual(self.runner.signals, ['SIGTERM'])
        self.end_game(sup, pid, 143)
        self.assertEqual((replies[0]['ok'], sup.stop), (True, None))
        self.assertGreater(sup.deadline(), 1.0)  # and nothing of the stop is left due: the loop sleeps

    def test_every_end_after_a_stop_is_stopped_and_three_in_a_row_never_latch(self):
        for status, close in ((143, 'exited'), (0, 'failed'), (-9, 'failed'), (137, 'failed'), (None, 'failed'),
                              (1, 'failed')):
            sup, pid, peer = self.connected()
            replies = self.stop(sup)
            self.confirm(sup, peer)
            if status is None:  # Java and its wrapper went together: no report, no record
                self.runner.processes.pop(pid)
                sup.on_jvm_gone()
                self.advance(desktop.EXIT_REPORT_WAIT)
                sup.tick()
            else:
                self.end_game(sup, pid, status)
            (reply,) = replies
            self.assertEqual((reply['result'], reply['close'], reply['ok']), ('confirmed', close, close == 'exited'))
            self.assertEqual((sup.state, sup.reason, sup.retry_at), ('RECOVERY', 'quit', None), status)
            stored = self.stored()
            self.assertEqual((stored['latched'], stored['consecutive'], stored['failures'], stored['unresolved']),
                             (False, 0, [], None), status)
            self.assertEqual(self.runner.scopes_asked, [])
            self.assertEqual(len(self.runner.prisms), 1)  # never restarted
            self.advance(desktop.MAX_BACKOFF + 1)
            sup.tick()
            self.assertEqual(len(self.runner.prisms), 1)

    def test_a_plain_stop_whose_save_fails_is_called_off_and_its_window_survives_a_heartbeat(self):
        for answer, why in ((lambda: self.refused(1, 'error'), 'could not write AresHub'),
                            (lambda: self.refused(1, 'not_desktop_world'), 'is not an AresOS home'),
                            (lambda: self.saved(1, DATED), 'which is not the home AresHub'),
                            (lambda: {'op': 'world_saved', 'id': 1, 'ok': 'yes'}, 'could not be used')):
            sup, pid, peer = self.connected()
            self.ready(sup)
            replies = self.stop(sup)
            sup.on_lifecycle_message(peer, answer())
            sup.tick()
            (reply,) = replies
            self.assertEqual((reply['ok'], reply['result'], reply['close']), (False, 'called_off', 'called_off'))
            self.assertTrue(reply['message'].startswith('Not stopped: Minecraft keeps running. Not saved:'))
            self.assertIn(why, reply['message'])
            self.assertEqual(self.runner.signals, [])  # the game keeps running
            self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'save_failed'))
            self.assertIn(why, self.runner.views[-1])
            self.assertEqual((self.record()['open'], self.record()['close']), (False, 'called_off'))
            self.heartbeat(sup)
            self.ready(sup)
            self.advance(desktop.START_TIMEOUT)
            sup.tick()
            self.heartbeat(sup)
            self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'save_failed'))
            # `retry` closes it, and the launch runs on as an ordinary one: its crash is counted.
            self.assertEqual(sup.retry(), (True, 'Minecraft is still running; the recovery state is cleared.'))
            self.assertEqual(sup.state, 'IN_WORLD')
            self.end_game(sup, pid, 1)
            self.assertEqual(self.stored()['consecutive'], 1)
            sup.persisted.reset()
            sup.save()

    def test_a_shutdown_closes_anyway_latches_unsaved_and_the_next_start_says_so(self):
        sup, pid, peer = self.connected()
        views = len(self.runner.views)
        replies = self.stop(sup, 'shutdown')  # systemd gives no clear answer: it stays a shutdown
        self.assertTrue(os.path.exists(self.paths.stop_block))
        sup.on_lifecycle_message(peer, self.refused(1, 'error'))
        sup.tick()
        self.assertEqual(self.runner.signals, ['SIGTERM'])  # it cannot be called off
        self.assertEqual((self.record()['save'], self.record()['sigterm']), ('error', True))
        self.end_game(sup, pid, 143)
        (reply,) = replies
        self.assertEqual((reply['ok'], reply['result'], reply['save'], reply['close']),
                         (False, 'unsaved', 'error', 'exited'))
        self.assertIn('could not be confirmed as saved first', reply['message'])
        # The session is ending: the latch is persisted without a window, and nothing is admitted any more.
        self.assertEqual((sup.state, len(self.runner.views)), ('STOPPING', views))
        stored = self.stored()
        self.assertEqual((stored['latched'], stored['reason'], stored['consecutive']), (True, 'unsaved', 0))
        self.assertFalse(sup.on_jvm_start(self.jvm_request())[0])
        self.assertEqual(sup.retry()[0], False)
        self.heartbeat(sup)
        self.assertEqual((sup.state, len(self.runner.prisms)), ('STOPPING', 1))
        # The next start: one window, the home as it is on the disk, and `retry` clears the latch.
        sup = self.next_session()
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'unsaved'))
        self.assertIn('could not confirm that your home was saved first', self.runner.views[-1])
        self.assertIn('could not write AresHub', self.runner.views[-1])
        self.assertEqual(self.runner.prisms, [])
        self.assertTrue(sup.retry()[0])
        self.assertEqual((sup.state, self.stored()['latched'], len(self.runner.prisms)), ('STARTING', False, 1))

    def test_what_passes_by_itself_is_asked_again_each_second_and_never_means_nothing_to_save(self):
        for kind in ('stop', 'shutdown'):
            sup, pid = self.game()  # no hello yet: the game is loading, or an adopted one is reconnecting
            began = self.now[0]
            replies = self.stop(sup, kind)
            self.advance(1)
            sup.tick()
            self.assertEqual((replies, self.runner.signals), ([], []))
            peer = FakePeer(pid)
            self.assertTrue(sup.on_lifecycle_hello(peer, self.hello(sup)))
            self.advance(1)
            sup.tick()
            self.assertEqual(peer.sent, [{'op': 'save_world', 'id': 1, 'reason': 'shutdown'}])
            sup.on_lifecycle_message(peer, self.refused(1, 'server_stopping'))
            sup.tick()
            self.assertEqual(len(peer.sent), 1)  # not before a second has passed
            answered = 1
            while not replies and not self.runner.signals:
                self.advance(1)
                sup.tick()
                if len(peer.sent) > answered:
                    answered = len(peer.sent)
                    sup.on_lifecycle_message(peer, self.refused(peer.sent[-1]['id'], 'no_world'))
                    sup.tick()
            # Asked each second, and given up at the save deadline: never taken for "nothing to save".
            self.assertEqual(self.now[0] - began, desktop.STOP_SAVE_WAIT - 1)
            self.assertEqual(answered, desktop.STOP_SAVE_WAIT - 2)
            if kind == 'stop':
                self.assertEqual((replies[0]['result'], self.runner.signals), ('called_off', []))
                self.assertIn('no home is open in Minecraft', replies[0]['message'])
            else:
                self.assertEqual((replies, self.runner.signals), ([], ['SIGTERM']))
                self.end_game(sup, pid, 143)
                self.assertEqual((replies[0]['result'], replies[0]['save']), ('unsaved', 'no_world'))
                self.assertEqual(self.stored()['reason'], 'unsaved')

    def test_a_stop_during_new_home_saves_the_new_home(self):
        sup, pid, peer = self.connected()
        self.ready(sup)
        replies = self.stop(sup, 'shutdown')
        sup.on_lifecycle_message(peer, self.refused(1, 'no_world'))  # the game is switching homes
        sup.tick()
        self.dated_world()
        self.ready(sup, DATED)
        self.assertEqual(sup.state, 'STOPPING')  # the new home's report does not end the stop
        self.advance(desktop.STOP_ASK_AGAIN)
        sup.tick()
        self.assertEqual(peer.sent[-1], {'op': 'save_world', 'id': 2, 'reason': 'shutdown'})
        sup.on_lifecycle_message(peer, self.saved(2, DATED))
        sup.tick()
        self.assertEqual((self.runner.signals, self.record()['save']), (['SIGTERM'], 'saved'))
        self.end_game(sup, pid, 143)
        self.assertEqual((replies[0]['result'], self.stored()['latched']), ('confirmed', False))

    def test_nothing_to_save_needs_positive_evidence(self):
        # No world folder at all: the close goes ahead without a save.
        sup, pid, peer = self.connected()
        shutil.rmtree(os.path.join(self.paths.worlds, self.lock['world']))
        replies = self.stop(sup)
        self.assertEqual((peer.sent, self.runner.signals, self.record()['save']), ([], ['SIGTERM'], 'nothing'))
        self.end_game(sup, pid, 143)
        self.assertEqual((replies[0]['ok'], replies[0]['save']), (True, 'nothing'))
        base.make_world(self.paths, self.lock)
        # A worlds folder that cannot be listed is unknown, never empty.
        sup, pid, peer = self.connected()
        with mock.patch.object(desktop.os, 'scandir', side_effect=PermissionError(13, 'Permission denied')):
            self.stop(sup)
        self.assertEqual((len(peer.sent), self.runner.signals), (1, []))
        self.confirm(sup, peer)
        self.end_game(sup, pid, 143)
        # Nothing running: no record, a pending restart is called off, and the quit window shows.
        sup, pid = self.game()
        self.end_game(sup, pid, 1)
        self.assertIsNotNone(sup.retry_at)
        record = self.record()
        replies = self.stop(sup)
        self.assertEqual((replies[0]['ok'], replies[0]['close'], replies[0]['message']),
                         (True, 'none', 'Nothing to stop: Minecraft is not running.'))
        self.assertEqual((self.record(), sup.retry_at, sup.state, sup.reason), (record, None, 'RECOVERY', 'quit'))
        self.advance(desktop.MAX_BACKOFF + 1)
        sup.tick()
        self.assertEqual(len(self.runner.prisms), 1)
        # A game this supervisor cannot see holds the desktop lock: never "nothing is running".
        self.runner.lock_held = True
        replies = self.stop(sup)
        self.assertEqual((replies[0]['ok'], replies[0]['result']), (False, 'called_off'))
        replies = self.stop(sup, 'shutdown')
        self.assertEqual((replies[0]['ok'], replies[0]['result'], replies[0]['close']), (False, 'unsaved', 'failed'))
        self.assertEqual((self.record()['open'], self.record()['launch']), (True, None))
        self.runner.lock_held = False
        sup = self.next_session()
        self.assertEqual((sup.state, sup.reason, self.record()['open']), ('RECOVERY', 'unsaved', False))

    def test_a_launch_in_hand_off_is_waited_for_and_then_closed(self):
        self.runner = StopRunner()
        sup = self.supervisor()
        sup.start()
        ok, start = sup.on_jvm_start(self.jvm_request())  # authorized; its JVM is not reported yet
        self.assertTrue(ok)
        replies = self.stop(sup)
        self.assertEqual((replies, self.runner.signals, self.record()['launch']), ([], [], start['launch']))
        self.assertFalse(sup.on_jvm_start(self.jvm_request())[0])  # no other JVM is authorized meanwhile
        self.runner.processes[5001] = (5000, 5001 * 7, '')
        self.assertEqual(sup.on_jvm_started(5000, 5001, start['launch']), (True, ''))
        sup.tick()
        peer = FakePeer(5001)
        self.assertTrue(sup.on_lifecycle_hello(peer, self.hello(sup)))
        self.advance(desktop.STOP_ASK_AGAIN)
        sup.tick()
        self.confirm(sup, peer)
        self.assertEqual(self.runner.signals, ['SIGTERM'])
        self.end_game(sup, 5001, 143)
        self.assertEqual((replies[0]['ok'], replies[0]['result']), (True, 'confirmed'))
        # A start that never became a game: the wrapper's word that Java never ran is nothing to save.
        self.runner = StopRunner()
        pathlib.Path(self.paths.runtime_file).unlink()
        sup = self.supervisor()
        sup.start()
        ok, start = sup.on_jvm_start(self.jvm_request())
        replies = self.stop(sup, 'shutdown')
        sup.on_jvm_failed(start['launch'], desktop.failed_start({'reason': 'Java could not be started'}))
        sup.tick()
        self.assertEqual((replies[0]['result'], replies[0]['save'], self.stored()['latched']),
                         ('confirmed', 'nothing', False))
        self.assertEqual(self.stored()['consecutive'], 0)

    def test_a_record_that_cannot_be_written(self):
        with mock.patch.object(desktop, 'write_durable', side_effect=OSError(28, 'No space left on device')):
            # A stop that can be called off is, before anything is asked of the game.
            sup, pid, peer = self.connected()
            replies = self.stop(sup)
            self.assertEqual((replies[0]['result'], replies[0]['recorded'], replies[0]['ok']),
                             ('called_off', False, False))
            self.assertEqual((peer.sent, self.runner.signals), ([], []))
            self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'save_failed'))
            self.assertIn('could not be recorded on the disk', self.runner.views[-1])
            # One that cannot goes on, and its reply says so; the launch is still `stopped`.
            sup, pid, peer = self.connected()
            replies = self.stop(sup, 'shutdown')
            self.confirm(sup, peer)
            self.assertEqual(self.runner.signals, ['SIGTERM'])
            self.end_game(sup, pid, 143)
            (reply,) = replies
            self.assertEqual((reply['result'], reply['close'], reply['recorded'], reply['ok']),
                             ('confirmed', 'exited', False, False))
            self.assertTrue(reply['message'].endswith('The stop could not be recorded on the disk.'))
            self.assertEqual((sup.persisted.consecutive, sup.persisted.latched), (0, False))

    def test_at_the_deadline_the_supervisor_stops_waiting_and_never_kills(self):
        for kind in ('stop', 'shutdown'):
            sup, pid, peer = self.connected()
            views = len(self.runner.views)
            replies = self.stop(sup, kind)
            self.advance(2)
            self.confirm(sup, peer)
            self.advance(desktop.STOP_BUDGET - 2.5)
            sup.tick()
            self.assertEqual(replies, [])
            self.advance(0.5)
            sup.tick()
            (reply,) = replies
            self.assertEqual((reply['ok'], reply['result'], reply['close']), (False, 'confirmed', 'overrun'))
            self.assertEqual(self.runner.signals, ['SIGTERM'])  # one SIGTERM, and nothing else, ever
            record = self.record()  # it still names the launch
            self.assertEqual((record['open'], record['launch'], record['close']), (True, sup.launch.id, 'overrun'))
            self.runner.lock_held = True
            if kind == 'stop':
                self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'stuck'))
                self.ready(sup)
                self.heartbeat(sup)
                self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'stuck'))
                self.assertEqual(sup.retry(), (True, 'Minecraft is still running; the recovery state is cleared.'))
            else:
                self.assertEqual((sup.state, len(self.runner.views)), ('STOPPING', views))
                self.assertFalse(sup.retry()[0])
            self.assertEqual(len(self.runner.prisms), 1)  # no second game
            # When it ends at last, however it ends, it is `stopped`.
            self.runner.lock_held = False
            self.end_game(sup, pid, 137)
            stored = self.stored()
            self.assertEqual((stored['stop']['open'], stored['stop']['close'], stored['latched'],
                              stored['consecutive']), (False, 'overrun', False, 0))
            self.assertEqual((sup.state, sup.reason),
                             ('RECOVERY', 'quit') if kind == 'stop' else ('STOPPING', 'session'))
            self.assertEqual(len(self.runner.prisms), 1)

    def test_ops_that_arrive_during_a_stop_join_it(self):
        sup, pid, peer = self.connected()
        first = self.stop(sup)
        deadline = sup.stop.deadline
        self.advance(3)
        second = self.stop(sup)
        saves = []
        sup.ask_save('backup', saves.append)
        self.assertEqual(len(peer.sent), 1)  # no second save
        self.assertEqual(sup.retry(), (False, 'AresOS is stopping Minecraft right now. Type retry again when '
                                              'that is done.'))
        self.assertEqual(sup.on_jvm_start(self.jvm_request()),
                         (False, {'message': 'AresOS is stopping, so Minecraft is not started now.'}))
        third = self.stop(sup, 'shutdown')  # it makes the stop one that cannot be called off
        self.assertEqual((sup.stop.kind, sup.stop.deadline, self.record()['kind']), ('shutdown', deadline, 'shutdown'))
        self.assertTrue(os.path.exists(self.paths.stop_block))
        sup.on_lifecycle_message(peer, self.refused(1, 'error'))
        sup.tick()
        self.assertEqual(self.runner.signals, ['SIGTERM'])
        self.assertEqual((first, second, third, saves), ([], [], [], []))  # every caller hears it at the end
        self.end_game(sup, pid, 143)
        self.assertEqual((len(first), first, first), (1, second, third))
        self.assertEqual((first[0]['kind'], first[0]['result'], first[0]['seconds']), ('shutdown', 'unsaved', 3.0))
        self.assertEqual([(save.result, save.reason) for save in saves], [('refused', 'error')])

    def test_a_shutdown_while_the_system_is_not_stopping_is_a_plain_stop(self):
        for system, kind in ((False, 'stop'), (True, 'shutdown'), (None, 'shutdown')):
            sup, pid, peer = self.connected()
            self.runner.system = system
            self.stop(sup, 'shutdown')
            self.assertEqual((sup.stop.kind, self.record()['kind']), (kind, kind))
            self.assertEqual(os.path.exists(self.paths.stop_block), kind == 'shutdown')
            self.confirm(sup, peer)
            self.end_game(sup, pid, 143)

    def test_a_replacement_supervisor_calls_the_stop_off_or_goes_on_with_it(self):
        # One that can be called off and had not sent SIGTERM: called off, and the game runs on.
        sup, pid, peer = self.connected()
        self.stop(sup)
        second = self.supervisor()
        second.start()
        self.assertEqual((second.stop, second.state, second.launch.jvm_pid), (None, 'STARTING', pid))
        self.assertEqual((self.record()['open'], self.record()['close']), (False, 'called_off'))
        # After SIGTERM it goes on inside what is left of the one deadline, by the record's start.
        sup, pid, peer = self.connected()
        self.stop(sup)
        self.confirm(sup, peer)
        self.advance(20)
        second = self.supervisor()
        second.start()
        self.assertEqual((second.state, second.stop.phase), ('STOPPING', 'close'))
        self.assertAlmostEqual(second.stop.deadline, self.now[0] + desktop.STOP_BUDGET - 20)
        self.assertFalse(second.on_jvm_start(self.jvm_request())[0])
        self.end_game(second, pid, -9)
        stored = self.stored()
        self.assertEqual((stored['stop']['close'], stored['stop']['save'], stored['latched'], stored['consecutive']),
                         ('failed', 'saved', False, 0))
        self.assertEqual((second.state, second.reason, self.runner.signals), ('RECOVERY', 'quit', ['SIGTERM']))
        # A shutdown that had not got its save goes on with the save: the adopted game's hello comes a moment later.
        sup, pid, peer = self.connected()
        self.stop(sup, 'shutdown')
        self.advance(5)
        second = self.supervisor()
        second.start()
        self.assertEqual((second.state, second.stop.kind, second.stop.phase), ('STOPPING', 'shutdown', 'save'))
        second.tick()
        self.assertEqual(self.runner.signals, [])
        peer = FakePeer(pid)
        self.assertTrue(second.on_lifecycle_hello(peer, self.hello(second)))
        self.advance(desktop.STOP_ASK_AGAIN)
        second.tick()
        self.confirm(second, peer)
        self.assertEqual(self.runner.signals, ['SIGTERM'])
        self.end_game(second, pid, 143)
        self.assertEqual((self.record()['save'], self.record()['close'], second.state), ('saved', 'exited', 'STOPPING'))

    def test_the_next_start_closes_a_record_whose_launch_is_gone(self):
        # The machine went down in the middle of the save: `stopped`, never a crash, and `unsaved` is latched.
        sup, pid, peer = self.connected()
        launch = sup.launch.id
        self.stop(sup, 'shutdown')
        sup = self.next_session()
        stored = self.stored()
        self.assertEqual((sup.state, sup.reason, stored['accounted']), ('RECOVERY', 'unsaved', launch))
        self.assertEqual((stored['stop']['open'], stored['consecutive'], stored['failures']), (False, 0, []))
        self.assertTrue(sup.retry()[0])
        # A replacement supervisor in a teardown: the game was ended without any report after a confirmed save.
        sup, pid, peer = self.connected()
        self.stop(sup, 'shutdown')
        self.confirm(sup, peer)
        self.runner.processes.pop(pid)
        views = len(self.runner.views)
        second = self.supervisor()
        second.start()
        stored = self.stored()
        self.assertEqual((second.state, stored['latched'], stored['consecutive'], stored['unresolved']),
                         ('STOPPING', False, 0, None))
        self.assertEqual((stored['stop']['open'], stored['stop']['save'], stored['stop']['close']),
                         (False, 'saved', 'failed'))
        self.assertEqual((len(self.runner.prisms), len(self.runner.views)), (1, views))  # nothing starts or shows
        # A plain stop whose game ended while no supervisor ran: this session waits at the quit window.
        sup, pid, peer = self.connected()
        self.stop(sup)
        self.confirm(sup, peer)
        self.runner.processes.pop(pid)
        second = self.supervisor()
        second.start()
        self.assertEqual((second.state, second.reason, len(self.runner.prisms)), ('RECOVERY', 'quit', 1))

    def test_the_admission_block_is_bound_to_the_session(self):
        sup, pid, peer = self.connected()
        self.stop(sup, 'shutdown')
        block = json.loads(pathlib.Path(self.paths.stop_block).read_text())
        self.assertEqual((block['instance'], block['labwc'], block['kind']), (sup.instance, None, 'shutdown'))
        # The runtime folder outlived the session: the next session has another labwc, so the block does not hold.
        self.runner.processes[77] = (1, 770, '')
        environ = {'HOME': self.paths.home, 'XDG_RUNTIME_DIR': self.paths.runtime, 'LABWC_PID': '77'}
        later = desktop.Supervisor(self.paths, self.lock, self.runner, clock=lambda: self.now[0],
                                   wall=lambda: self.wall[0], nvidia=False, environ=environ)
        later.instance = sup.instance
        self.assertFalse(later.blocked())
        later.block_admission('logout')
        block = json.loads(pathlib.Path(self.paths.stop_block).read_text())
        self.assertEqual((block['labwc'], block['kind']), ([77, 770], 'logout'))
        again = desktop.Supervisor(self.paths, self.lock, self.runner, clock=lambda: self.now[0],
                                   wall=lambda: self.wall[0], nvidia=False, environ=environ)
        again.instance = sup.instance
        self.assertTrue(again.blocked())  # a replacement supervisor of the same session
        self.runner.processes[77] = (1, 771, '')  # the same PID, another process
        again.admission_blocked = False
        self.assertFalse(again.blocked())

    def test_the_new_windows_and_the_new_keys_through_r28s_key_list(self):
        persisted = desktop.Persisted()
        for reason, words in (('save_failed', 'Minecraft keeps running and nothing is lost.'),
                              ('stuck', 'It never ends Minecraft by force'),
                              ('unsaved', 'Your home opens as it is on the disk.')):
            text = desktop.message('RECOVERY', reason, 'Not saved: why.', self.lock, persisted)
            self.assertIn(words, text)
            self.assertNotIn(f'{reason}:', text)
            self.assertIn('retry', text)
        sup, pid, peer = self.connected()
        self.ready(sup)
        self.assertEqual(set(self.stored()), set(R28_KEYS))  # no stop yet: exactly the keys R28 wrote itself

        def through_r28():
            stored = self.stored()
            self.assertEqual(stored['schema'], 1)
            self.assertEqual(set(stored) - set(R28_KEYS), {'stop'})  # the one new key, which R28 never reads
            mine = desktop.Persisted.load(self.paths.state_file)
            self.assertEqual(r28_load(stored), {key: getattr(mine, key) for key in R28_KEYS[1:]})
            return r28_load(stored)

        self.stop(sup, 'shutdown')
        sup.on_lifecycle_message(peer, self.refused(1, 'error'))
        sup.tick()
        self.assertEqual(through_r28()['latched'], False)  # an open record
        self.end_game(sup, pid, 143)
        seen = through_r28()  # closed, with the latch: R28 shows it as a recovery it does not know, and retry clears
        self.assertEqual((seen['latched'], seen['reason']), (True, 'unsaved'))


class SessionBase(StopBase):
    """A session with a labwc of its own, and what the helper said about the app windows."""

    def supervisor(self, nvidia=False):
        return desktop.Supervisor(self.paths, self.lock, self.runner, clock=lambda: self.now[0],
                                  wall=lambda: self.wall[0], nvidia=nvidia,
                                  environ={'HOME': self.paths.home, 'XDG_RUNTIME_DIR': self.paths.runtime,
                                           'LABWC_PID': '77'})

    def session(self, labwc='watched', game=True, windows=0, names=()):
        """A session whose supervisor got LABWC_PID 77: (supervisor, the game's PID, its lifecycle peer). The
        helper reported `windows` app windows (None: it has not said). Each call is a machine of its own: no state
        from an earlier case."""
        self.runner = StopRunner()
        self.runner.labwc = labwc
        for path in (self.paths.runtime_file, self.paths.stop_block, self.paths.state_file):
            pathlib.Path(path).unlink(missing_ok=True)
        sup = self.supervisor()
        sup.start()
        pid = peer = None
        if game:
            pid, _ = self.run_game(sup)
            peer = FakePeer(pid)
            self.assertTrue(sup.on_lifecycle_hello(peer, self.hello(sup)))
            self.ready(sup)
        if windows is not None:
            sup.on_helper_status({'event': 'windows', 'count': windows, 'names': list(names)})
        return sup, pid, peer

    def end(self, sup, why='SIGTERM'):
        """The session ends under the supervisor: the list its `done` lands in. The loop exits once it has one."""
        done = []
        sup.end_session(why, done.append)
        return done

    def close_game(self, sup, pid, peer, status=143, ident=1):
        self.confirm(sup, peer, ident)
        self.end_game(sup, pid, status)


class SessionTest(SessionBase):
    """3.2 and 3.3: the session ends under the supervisor (a signal, labwc's end), `logout` and `restart`."""

    # -- 3.2: a signal

    def test_a_signal_runs_the_stop_routine_before_the_supervisor_exits(self):
        sup, pid, peer = self.session()
        self.runner.system = False  # a command's shutdown would be a plain stop now; the session's end is not asked
        views = len(self.runner.views)
        done = self.end(sup)
        self.assertEqual(done, [])  # the supervisor does not exit yet
        self.assertEqual((sup.state, sup.stop.kind, sup.session_over), ('STOPPING', 'shutdown', 'SIGTERM'))
        self.assertEqual(peer.sent, [{'op': 'save_world', 'id': 1, 'reason': 'shutdown'}])
        self.assertTrue(sup.blocked())
        self.assertEqual((self.record()['open'], self.record()['kind']), (True, 'shutdown'))
        # The last seconds of the one deadline are the supervisor's own exit.
        self.assertEqual(sup.stop.deadline, self.now[0] + desktop.STOP_BUDGET - desktop.STOP_EXIT_RESERVE)
        self.assertEqual(sup.exit_by, self.now[0] + desktop.STOP_BUDGET)
        # It cannot be called off: a save that fails closes the game anyway, and the record says unsaved.
        sup.on_lifecycle_message(peer, self.refused(1, 'error'))
        sup.tick()
        self.assertEqual(self.runner.signals, ['SIGTERM'])
        self.end_game(sup, pid, 143)
        (reply,) = done
        self.assertEqual((reply['kind'], reply['result'], reply['close']), ('shutdown', 'unsaved', 'exited'))
        self.assertEqual((sup.state, sup.reason, len(self.runner.views)), ('STOPPING', 'session', views))
        stored = self.stored()
        self.assertEqual((stored['latched'], stored['reason'], stored['stop']['open']), (True, 'unsaved', False))
        self.assertEqual((self.runner.labwc_signals, len(self.runner.prisms)), (0, 1))

    def test_a_signal_that_joins_a_stop_makes_it_final_and_never_extends_it(self):
        sup, pid, peer = self.session()
        replies = self.stop(sup)  # a plain stop: it could be called off
        deadline = sup.stop.deadline
        self.advance(5)
        done = self.end(sup, 'SIGHUP')
        again = self.end(sup, 'SIGTERM')  # a second signal joins too
        self.assertEqual((sup.stop.kind, self.record()['kind'], sup.session_over), ('shutdown', 'shutdown', 'SIGHUP'))
        self.assertEqual(sup.stop.deadline, deadline - desktop.STOP_EXIT_RESERVE)  # the reserve, taken once
        self.assertEqual(sup.exit_by, deadline)
        self.assertEqual(len(peer.sent), 1)  # no second stop, no second save
        sup.on_lifecycle_message(peer, self.refused(1, 'error'))
        sup.tick()
        self.assertEqual((self.runner.signals, replies), (['SIGTERM'], []))  # closed anyway, not called off
        self.end_game(sup, pid, 143)
        (reply,) = replies
        self.assertEqual((reply['kind'], reply['result']), ('shutdown', 'unsaved'))
        self.assertEqual((done, again), (replies, replies))  # every caller hears the one stop's end

    def test_a_signal_with_nothing_running_or_after_an_overrun_ends_at_once(self):
        sup, _, _ = self.session(game=False)  # Prism is up, no Java
        views = len(self.runner.views)
        done = self.end(sup, 'SIGINT')
        self.assertEqual((len(done), sup.stop, sup.state, sup.reason), (1, None, 'STOPPING', 'session'))
        self.assertEqual((done[0]['close'], sup.blocked(), len(self.runner.views)), ('none', True, views))
        self.assertEqual(sup.exit_by, self.now[0] + desktop.STOP_EXIT_RESERVE)
        self.assertIsNone(sup.persisted.stop)  # a stop with nothing running writes no record
        # 2.7: a shutdown stop overran and answered; when the session's signal comes, the supervisor just exits.
        sup, pid, peer = self.session()
        replies = self.stop(sup, 'shutdown')
        self.confirm(sup, peer)
        self.advance(desktop.STOP_BUDGET)
        sup.tick()
        self.assertEqual(replies[0]['close'], 'overrun')
        done = self.end(sup)
        self.assertEqual((done, sup.stop, sup.state, sup.reason), ([None], None, 'STOPPING', 'overrun'))
        self.assertEqual(self.runner.signals, ['SIGTERM'])  # no second SIGTERM, no second deadline
        self.assertEqual((self.record()['open'], self.record()['close']), (True, 'overrun'))

    def test_a_signals_stop_gives_up_early_enough_for_the_supervisors_own_exit(self):
        sup, pid, peer = self.session()
        began = self.now[0]
        done = self.end(sup)
        self.confirm(sup, peer)
        self.advance(desktop.STOP_BUDGET - desktop.STOP_EXIT_RESERVE - 0.1)
        sup.tick()
        self.assertEqual(done, [])
        self.advance(0.1)
        sup.tick()
        (reply,) = done
        self.assertEqual((reply['close'], self.runner.signals), ('overrun', ['SIGTERM']))  # never killed
        # What is left covers the exit's two waits at their shortest: SIGTERM's and SIGKILL's.
        self.assertEqual(sup.exit_by, began + desktop.STOP_BUDGET)
        self.assertGreater(sup.exit_by - self.now[0], desktop.CLEANUP_KILL_WAIT)

    # -- 3.2: labwc

    def test_only_this_sessions_labwc_passes_the_check(self):
        proc = self.root / 'proc'
        mine = f'XDG_RUNTIME_DIR={self.paths.runtime}'

        def process(pid, name, *environ):
            (proc / str(pid)).mkdir(parents=True)
            (proc / str(pid) / 'comm').write_text(name + '\n')
            (proc / str(pid) / 'environ').write_bytes(b''.join(item.encode() + b'\0' for item in environ))

        process(1, 'labwc', 'PATH=/usr/bin', mine)
        process(2, 'labwc', 'XDG_RUNTIME_DIR=/run/user/1001')
        process(3, 'bash', mine)
        process(4, 'labwc', mine + '-other', 'NOTE=' + mine)

        def problem(pid):
            return desktop.labwc_problem(pid, self.paths.runtime, str(proc))

        self.assertIsNone(problem(1))
        self.assertIn('another runtime folder', problem(2))  # the owner's session, seen from a private runtime folder
        self.assertIn('named bash', problem(3))
        self.assertIn('another runtime folder', problem(4))
        with mock.patch.object(desktop.os, 'getuid', return_value=os.getuid() + 1):
            self.assertIn('another user', problem(1))
        with self.assertRaises(ProcessLookupError):
            problem(5)

    def test_a_labwc_with_another_runtime_folder_is_never_watched_or_signalled(self):
        sup, pid, peer = self.session(labwc='that labwc runs on another runtime folder')
        self.assertEqual(self.runner.labwc_watches, [(77, self.paths.runtime)])  # LABWC_PID, and our own folder
        self.assertEqual((sup.labwc_watched, sup.labwc_gone, sup.status()['labwc']), (False, False, False))
        (reply,) = self.stop(sup, 'logout')
        self.assertEqual((reply['ok'], reply['result'], reply['error']), (False, 'refused', 'no_session'))
        self.assertEqual((self.runner.labwc_signals, self.runner.signals, peer.sent, sup.state),
                         (0, [], [], 'IN_WORLD'))
        # Without a LABWC_PID of its own the supervisor asks about no process at all.
        self.runner = StopRunner()
        pathlib.Path(self.paths.runtime_file).unlink()
        plain = base.Base.supervisor(self)
        plain.start()
        self.assertEqual((self.runner.labwc_watches, plain.labwc_watched), ([], False))

    def test_a_supervisor_started_after_its_labwc_ended_starts_nothing_and_stops_what_it_adopts(self):
        sup, _, _ = self.session(labwc='gone', game=False, windows=None)
        self.assertEqual((sup.state, sup.reason, sup.labwc_gone), ('STOPPING', 'session', True))
        self.assertEqual((self.runner.prisms, self.runner.views), ([], []))
        self.assertEqual(len(self.end(sup, 'its labwc had ended')), 1)  # the loop exits at once
        # With a game from before: adopted, stopped (it is asked to save first), and then the supervisor exits.
        first, pid, _ = self.session()
        self.runner.labwc = 'gone'
        later = self.supervisor()
        later.start()
        self.assertEqual((later.launch.jvm_pid, later.labwc_gone), (pid, True))
        done = self.end(later, 'its labwc had ended')
        self.assertEqual((later.stop.kind, done, len(self.runner.prisms)), ('shutdown', [], 1))
        later.tick()  # the adopted game has not said hello to this supervisor yet: asked again in a second
        peer = FakePeer(pid)
        self.assertTrue(later.on_lifecycle_hello(peer, self.hello(later)))
        self.advance(desktop.STOP_ASK_AGAIN)
        later.tick()
        (asked,) = peer.sent
        self.close_game(later, pid, peer, ident=asked['id'])
        (reply,) = done
        self.assertEqual((reply['result'], reply['save'], reply['close']), ('confirmed', 'saved', 'exited'))

    # -- 3.3: logout

    def test_logout_is_refused_while_an_app_window_is_open_or_the_helper_has_not_said(self):
        sup, pid, peer = self.session(windows=2, names=['Mail', 'Files'])
        (reply,) = self.stop(sup, 'logout')
        self.assertEqual((reply['ok'], reply['result'], reply['error'], reply['windows']),
                         (False, 'refused', 'apps_open', ['Mail', 'Files']))
        self.assertEqual(reply['message'], 'Not logged out: 2 apps are still open (Mail, Files). Close them first; '
                                           'nothing was stopped.')
        # It stopped nothing: no save, no signal, no record, no block, and the hub stays.
        self.assertEqual((peer.sent, self.runner.signals, self.runner.labwc_signals), ([], [], 0))
        self.assertEqual((self.record(), sup.blocked(), sup.state, sup.stop), (None, False, 'IN_WORLD', None))
        self.assertEqual(sup.status()['windows'], ['Mail', 'Files'])
        # A count without names, and one that is no number (the helper lost track): unknown counts as open.
        sup.on_helper_status({'event': 'windows', 'count': 1})
        self.assertIn('an app is still open (an app without a name). Close it first',
                      self.stop(sup, 'logout')[0]['message'])
        for count in (None, True, -1, '0'):
            sup.on_helper_status({'event': 'windows', 'count': 0})
            self.assertEqual(sup.app_windows(), [])
            sup.on_helper_status({'event': 'windows', 'count': count})
            self.assertIsNone(sup.app_windows(), count)
            self.assertEqual(self.stop(sup, 'logout')[0]['error'], 'apps_unknown')
        # The helper has not said; and a helper that said zero and then died.
        sup, pid, peer = self.session(windows=None)
        self.assertEqual(self.stop(sup, 'logout')[0]['error'], 'apps_unknown')
        sup, pid, peer = self.session()
        self.assertEqual(sup.app_windows(), [])
        self.runner.helper_alive = False
        sup.on_helper_exit(1)
        self.assertEqual(self.stop(sup, 'logout')[0]['error'], 'apps_unknown')
        sup.restart_helper()  # the new helper has not said yet
        self.assertEqual((self.runner.helper_alive, sup.app_windows()), (True, None))
        self.assertEqual((peer.sent, self.runner.signals, self.runner.labwc_signals), ([], [], 0))

    def test_a_logout_stops_the_game_then_ends_labwc_through_its_pidfd(self):
        sup, pid, peer = self.session()
        views = len(self.runner.views)
        replies = self.stop(sup, 'logout')
        self.assertEqual((sup.stop.kind, sup.blocked(), self.runner.labwc_signals), ('logout', True, 0))
        self.confirm(sup, peer)
        self.assertEqual(self.runner.labwc_signals, 0)  # not before Java is really gone
        self.end_game(sup, pid, 143)
        self.assertEqual((self.runner.labwc_signals, replies, sup.stop.phase, sup.state), (1, [], 'logout', 'STOPPING'))
        sup.tick()
        self.assertEqual(self.runner.labwc_signals, 1)
        # labwc ends: the loop tells the supervisor, and ends the session.
        sup.on_labwc_gone()
        done = self.end(sup, 'labwc ended')
        (reply,) = replies
        self.assertEqual((reply['ok'], reply['logout'], reply['save'], reply['close']),
                         (True, 'exited', 'saved', 'exited'))
        self.assertEqual(reply['message'], 'Logged out: the home was saved first; Minecraft closed.')
        self.assertEqual((done, sup.stop, sup.state, sup.blocked()), (replies, None, 'STOPPING', True))
        # The logout's block became the ending session's: nothing lifts it any more.
        self.assertEqual(json.loads(pathlib.Path(self.paths.stop_block).read_text())['kind'], 'shutdown')
        sup.unblock_admission()
        self.assertTrue(sup.blocked())
        self.assertEqual((len(self.runner.views), len(self.runner.prisms), self.runner.signals),
                         (views, 1, ['SIGTERM']))

    def test_a_logout_with_no_game_running_still_logs_out(self):
        sup, _, _ = self.session(game=False)
        replies = self.stop(sup, 'logout')
        self.assertEqual((self.runner.labwc_signals, replies, sup.stop.phase), (1, [], 'logout'))
        self.assertTrue(sup.blocked())  # written also with nothing running (the lead's fix 2)
        done = self.end(sup, 'SIGTERM')  # the session's signal can come before labwc's end is seen
        (reply,) = replies
        self.assertEqual((reply['ok'], reply['logout'], reply['close']), (True, 'ending', 'none'))
        self.assertEqual(reply['message'], 'Logged out: Minecraft was not running.')
        self.assertEqual((done, self.runner.signals, self.runner.labwc_signals), (replies, [], 1))

    def test_a_logout_that_does_not_go_on_leaves_the_session_and_says_why(self):
        # An app window that appeared during the stop: the count is fresh right before labwc would be signalled.
        sup, pid, peer = self.session()
        replies = self.stop(sup, 'logout')
        sup.on_helper_status({'event': 'windows', 'count': 1, 'names': ['Mail']})
        self.close_game(sup, pid, peer)
        (reply,) = replies
        self.assertEqual((reply['ok'], reply['result'], reply['close'], reply['logout']),
                         (False, 'confirmed', 'exited', 'apps_open'))
        self.assertEqual(reply['message'], 'Stopped: the home was saved first; Minecraft closed. Not logged out: an '
                                           'app is open now (Mail).')
        self.assertEqual((self.runner.labwc_signals, sup.blocked(), sup.state, sup.reason),
                         (0, False, 'RECOVERY', 'quit'))
        # labwc stays: the wait ends at the stop's deadline, the reply says so and the quit window shows.
        sup, pid, peer = self.session()
        replies = self.stop(sup, 'logout')
        began = self.now[0]
        self.close_game(sup, pid, peer)
        self.assertEqual(sup.exit_by, began + desktop.STOP_BUDGET)  # labwc's end would be the supervisor's exit too
        self.advance(desktop.STOP_BUDGET - desktop.STOP_EXIT_RESERVE - 0.1)
        sup.tick()
        self.assertEqual((replies, self.runner.labwc_signals), ([], 1))
        self.advance(0.1)
        sup.tick()
        (reply,) = replies
        self.assertEqual((reply['ok'], reply['logout']), (False, 'stayed'))
        self.assertTrue(reply['message'].endswith('Not logged out: the session did not end within the stop\'s 60 '
                                                  'seconds.'), reply['message'])
        self.assertEqual((self.runner.labwc_signals, sup.blocked(), sup.state, sup.reason, sup.exit_by),
                         (1, False, 'RECOVERY', 'quit', None))
        # Java ended, but not by closing in its own way: not "confirmed and exited", so no logout.
        sup, pid, peer = self.session()
        replies = self.stop(sup, 'logout')
        self.close_game(sup, pid, peer, status=1)
        self.assertEqual((replies[0]['ok'], replies[0]['close'], self.runner.labwc_signals, sup.blocked()),
                         (False, 'failed', 0, False))
        self.assertTrue(replies[0]['message'].endswith(' Not logged out.'), replies[0]['message'])
        # A logout tried after a shutdown's stop never lifts the shutdown's block, whatever labwc does.
        sup, pid, peer = self.session()
        self.stop(sup, 'shutdown')
        self.close_game(sup, pid, peer)
        replies = self.stop(sup, 'logout')
        self.advance(desktop.STOP_BUDGET)
        sup.tick()
        self.assertEqual((replies[0]['logout'], sup.blocked(), sup.state), ('stayed', True, 'STOPPING'))
        self.assertEqual(json.loads(pathlib.Path(self.paths.stop_block).read_text())['kind'], 'shutdown')
        # The save is not confirmed: called off before anything is closed, and its window survives a heartbeat.
        sup, pid, peer = self.session()
        replies = self.stop(sup, 'logout')
        sup.on_lifecycle_message(peer, self.refused(1, 'error'))
        sup.tick()
        self.assertTrue(replies[0]['message'].startswith('Not logged out: Minecraft keeps running. Not saved:'))
        self.assertEqual((self.runner.signals, self.runner.labwc_signals, sup.blocked()), ([], 0, False))
        self.ready(sup)
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'save_failed_logout'))
        self.assertIn('AresOS did not log out, because your home could not be confirmed as saved first.',
                      sup.message())

    # -- 3.3: restart

    def test_a_restart_stops_and_starts_again_under_the_cover_when_no_app_is_open(self):
        sup, pid, peer = self.session()
        instance, launch, covers = sup.instance, sup.launch.id, len(self.runner.covers)
        replies = self.stop(sup, 'restart')
        self.confirm(sup, peer)
        self.assertEqual(len(self.runner.prisms), 1)  # nothing starts before Java is gone and the lock is free
        self.end_game(sup, pid, 143)
        (reply,) = replies
        self.assertEqual((reply['ok'], reply['kind'], reply['result'], reply['close'], reply['restart']),
                         (True, 'restart', 'confirmed', 'exited', 'started'))
        self.assertEqual(reply['message'], 'Stopped: the home was saved first; Minecraft closed. Minecraft is '
                                           'starting again.')
        self.assertEqual((sup.state, sup.instance, sup.blocked()), ('STARTING', instance, False))
        self.assertNotEqual(sup.launch.id, launch)
        self.assertEqual((len(self.runner.prisms), self.runner.covers[covers:], sup.launch.automatic),
                         (2, [True], False))  # as retry does: "Starting again…"
        stored = self.stored()
        self.assertEqual((stored['latched'], stored['consecutive'], stored['stop']['kind'], stored['stop']['close']),
                         (False, 0, 'restart', 'exited'))
        self.run_game(sup)  # the new launch is admitted
        self.assertEqual(sup.app_windows(), None)  # its new helper has not said yet

    def test_a_restart_with_an_app_open_or_unknown_starts_below_it(self):
        for windows in (1, None):
            sup, pid, peer = self.session(windows=windows, names=['Mail'])
            covers = len(self.runner.covers)
            replies = self.stop(sup, 'restart')
            self.close_game(sup, pid, peer)
            self.assertEqual((replies[0]['ok'], replies[0]['restart']), (True, 'started'), windows)
            self.assertEqual((len(self.runner.prisms), len(self.runner.covers), sup.launch.automatic),
                             (2, covers, True))  # as an automatic restart does: no cover over his app
            self.assertEqual(self.runner.helpers[-1][2].get('ARESOS_SHELL_KEEP_FOREGROUND'), '1')

    def test_a_restart_that_cannot_stop_cleanly_starts_no_second_game(self):
        # The save is not confirmed: the game keeps running and the window says so.
        sup, pid, peer = self.session()
        replies = self.stop(sup, 'restart')
        sup.on_lifecycle_message(peer, self.refused(1, 'error'))
        sup.tick()
        self.assertTrue(replies[0]['message'].startswith('Not restarted: Minecraft keeps running. Not saved:'))
        self.assertEqual((sup.state, sup.reason, self.runner.signals, len(self.runner.prisms)),
                         ('RECOVERY', 'save_failed_restart', [], 1))
        self.assertIn('Minecraft was not restarted, because', sup.message())
        self.assertNotIn('restart', replies[0])
        # Java does not close: `stuck`, and nothing is started while it is there.
        sup, pid, peer = self.session()
        replies = self.stop(sup, 'restart')
        self.confirm(sup, peer)
        self.advance(desktop.STOP_BUDGET)
        sup.tick()
        self.assertEqual((replies[0]['ok'], replies[0]['close']), (False, 'overrun'))
        self.assertTrue(replies[0]['message'].endswith(' Minecraft is not started again.'))
        self.assertEqual((sup.state, sup.reason, len(self.runner.prisms)), ('RECOVERY', 'stuck', 1))
        # Java went before the save was confirmed: the latch must be seen first, so nothing starts by itself.
        sup, pid, peer = self.session()
        replies = self.stop(sup, 'restart')
        self.end_game(sup, pid, 137)
        self.assertEqual((replies[0]['ok'], replies[0]['result']), (False, 'unsaved'))
        self.assertEqual((sup.state, sup.reason, len(self.runner.prisms)), ('RECOVERY', 'unsaved', 1))
        # While the session is ending nothing is started.
        sup, pid, peer = self.session()
        self.stop(sup, 'shutdown')
        self.close_game(sup, pid, peer)
        (reply,) = self.stop(sup, 'restart')
        self.assertEqual((reply['ok'], sup.state, len(self.runner.prisms)), (False, 'STOPPING', 1))
        self.assertEqual(reply['message'], 'Nothing to stop: Minecraft is not running. Minecraft is not started '
                                           'again.')

    def test_a_restart_with_nothing_running_starts_as_retry_does_and_never_twice(self):
        sup, pid, peer = self.session()
        self.stop(sup)
        self.close_game(sup, pid, peer)
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'quit'))
        (reply,) = self.stop(sup, 'restart')
        self.assertEqual((reply['ok'], reply['close'], reply['restart']), (True, 'none', 'started'))
        self.assertEqual(reply['message'], 'Nothing to stop: Minecraft is not running. Minecraft is starting again.')
        self.assertEqual((sup.state, len(self.runner.prisms)), ('STARTING', 2))
        # Prism has not handed the game over yet: a second `restart` starts no second Prism.
        (reply,) = self.stop(sup, 'restart')
        self.assertEqual((reply['ok'], reply['restart'], len(self.runner.prisms)), (True, 'starting', 2))
        self.assertTrue(reply['message'].endswith('Minecraft is already starting.'))

    # -- the windows' texts

    def test_the_windows_say_what_was_not_done_and_offer_restart(self):
        for kind, lead in (('stop', 'Minecraft was not stopped'), ('restart', 'Minecraft was not restarted'),
                           ('logout', 'AresOS did not log out')):
            reason = desktop.SAVE_FAILED[kind]
            text = desktop.message('RECOVERY', reason, 'Not saved: why.', self.lock, desktop.Persisted())
            self.assertIn(f'{lead}, because your home could not be confirmed as saved first.\nNot saved: why.\n',
                          text)
            self.assertIn('Minecraft keeps running and nothing is lost.', text)
            self.assertIn(reason, desktop.STICKY)  # it stays until `retry`
        helper = desktop.message('RECOVERY', 'helper', '', self.lock, desktop.Persisted())
        self.assertIn('Type  restart  and press Enter to save your home and start both again.', helper)
        rc = (base.CONFIG / 'usr/share/aresos/desktop-view.bashrc').read_text(encoding='utf-8')
        self.assertIn('restart() { /usr/libexec/aresos-desktop restart; }', rc)
        self.assertNotIn('logout', rc)  # bash's own word; the message window offers retry and restart only
        source = (base.CONFIG / 'usr/libexec/aresos-desktop').read_text(encoding='utf-8')
        self.assertEqual(source.count('pidfd_send_signal('), 2)  # Java's and labwc's watched pidfds, nothing else
        self.assertNotIn("'--exit'", source)  # never `labwc --exit`


class BlackTest(SessionBase):
    """3.4 (the owner's answer on board #379): the black screen and the lid block."""
    LIMIT = desktop.STOP_BUDGET + desktop.BLACK_EXTRA
    NONE = {'event': 'windows', 'count': 0, 'names': []}

    def logged(self, level):
        """The supervisor's log lines from this level up (the tests keep its logger switched off otherwise)."""
        desktop.LOG.disabled = False
        self.addCleanup(setattr, desktop.LOG, 'disabled', True)
        return self.assertLogs('aresos-desktop', level)

    def test_a_shutdown_a_logout_and_a_restart_go_black_at_their_start_and_a_plain_stop_never(self):
        for kind in ('shutdown', 'logout', 'restart'):
            sup, pid, peer = self.session()
            self.stop(sup, kind)
            self.assertEqual((self.runner.blacks, self.runner.black_up, sup.black, sup.state),
                             ([self.LIMIT], True, True, 'STOPPING'), kind)
            self.assertEqual((self.runner.lid_blocks, self.runner.lid_up), ([self.LIMIT], True), kind)
            status = sup.status()
            self.assertEqual((status['black'], status['lid_block']), (True, True), kind)
            # The save and the close run on behind it: nothing is closed before the save is in.
            self.assertEqual((self.runner.signals, sup.stop.phase), ([], 'save'), kind)
        self.assertEqual(self.LIMIT, 90.0)  # the stop's deadline and half a minute: its own limit (the cover's --limit)
        sup, pid, peer = self.session()
        self.stop(sup)
        self.assertEqual((self.runner.blacks, sup.black, self.runner.lid_blocks), ([], False, [self.LIMIT]))
        # A shutdown that systemd clearly says is none is a plain stop: the quit window, never black.
        sup, pid, peer = self.session()
        self.runner.system = False
        self.stop(sup, 'shutdown')
        self.assertEqual((sup.stop.kind, self.runner.blacks, self.runner.lid_up), ('stop', [], True))

    def test_with_an_app_window_open_or_no_report_the_screens_stay_as_they_are(self):
        for windows in (1, None):
            for kind in ('shutdown', 'restart'):  # a logout is refused then
                sup, pid, peer = self.session(windows=windows, names=['Mail'])
                with self.logged('INFO') as logs:
                    self.stop(sup, kind)
                self.assertEqual((self.runner.blacks, sup.black, self.runner.lid_up), ([], False, True))
                self.assertTrue(any('the screens stay as they are' in line for line in logs.output), logs.output)
        # A helper that is gone tracks nothing: its last count of zero is no count.
        sup, pid, peer = self.session()
        self.runner.helper_alive = False
        self.stop(sup, 'shutdown')
        self.assertEqual(self.runner.blacks, [])
        # Black comes only at the start: an app that closes during the stop does not bring it.
        sup, pid, peer = self.session(windows=1, names=['Mail'])
        self.stop(sup, 'shutdown')
        sup.on_helper_status(self.NONE)
        self.assertEqual((sup.app_windows(), self.runner.blacks), ([], []))

    def test_an_app_window_that_appears_during_the_stop_takes_the_black_screen_away_at_once(self):
        for report in ({'count': 1, 'names': ['Mail']}, {'count': None}, None):
            sup, pid, peer = self.session()
            replies = self.stop(sup, 'shutdown')
            self.assertTrue(self.runner.black_up)
            if report is None:  # the helper ends: nobody can tell any more
                self.runner.helper_alive = False
                sup.on_helper_exit(1)
            else:
                sup.on_helper_status(dict(report, event='windows'))
            kill_at = self.now[0] + desktop.COVER_STOP_WAIT
            self.assertEqual((self.runner.black_up, sup.black, self.runner.black_stops), (False, False, [kill_at]))
            # SIGTERM now and SIGKILL after two seconds if it is still there: never waited for.
            self.assertIn((kill_at, sup.kill_covers), sup.pending())
            # The stop itself goes on, with its lid block.
            self.assertEqual((sup.stop.kind, sup.state, self.runner.lid_up, replies), ('shutdown', 'STOPPING', True, []))
            # It does not come back when that window closes again.
            sup.on_helper_status(self.NONE)
            self.close_game(sup, pid, peer)
            self.assertEqual((len(self.runner.blacks), replies[0]['result'], replies[0]['close']),
                             (1, 'confirmed', 'exited'))

    def test_the_black_screen_ends_before_a_window_that_must_be_seen(self):
        # Called off: the save failed, and the window says so.
        sup, pid, peer = self.session()
        replies = self.stop(sup, 'restart')
        sup.on_lifecycle_message(peer, self.refused(1, 'error'))
        sup.tick()
        self.assertEqual((sup.reason, replies[0]['result']), ('save_failed_restart', 'called_off'))
        self.assertEqual((self.runner.black_up, sup.black, self.runner.lid_up, self.runner.behind_black[-1]),
                         (False, False, False, False))
        self.assertEqual((len(self.runner.black_stops), len(self.runner.lid_stops)), (1, 1))
        # Overrun: Java had its SIGTERM and is still there at the deadline.
        sup, pid, peer = self.session()
        replies = self.stop(sup, 'logout')
        self.confirm(sup, peer)
        self.assertTrue(self.runner.black_up)
        self.advance(desktop.STOP_BUDGET)
        sup.tick()
        self.assertEqual((sup.reason, replies[0]['close']), ('stuck', 'overrun'))
        self.assertEqual((self.runner.black_up, self.runner.lid_up, self.runner.behind_black[-1]), (False, False, False))
        # A logout whose session stays: black while labwc is asked to end, then the quit window.
        sup, pid, peer = self.session()
        replies = self.stop(sup, 'logout')
        self.close_game(sup, pid, peer)
        self.assertEqual((self.runner.labwc_signals, self.runner.black_up, replies), (1, True, []))
        self.advance(desktop.STOP_BUDGET)
        sup.tick()
        self.assertEqual((sup.reason, replies[0]['logout']), ('quit', 'stayed'))
        self.assertEqual((self.runner.black_up, self.runner.lid_up, self.runner.behind_black[-1]), (False, False, False))
        # Java gone before the save was confirmed: the restart ends at the `unsaved` window.
        sup, pid, peer = self.session()
        replies = self.stop(sup, 'restart')
        self.end_game(sup, pid, 1)
        self.assertEqual((sup.reason, replies[0]['result']), ('unsaved', 'unsaved'))
        self.assertEqual((self.runner.black_up, self.runner.lid_up, self.runner.behind_black[-1]), (False, False, False))

    def test_at_a_shutdown_they_stay_until_the_session_is_torn_down(self):
        sup, pid, peer = self.session()
        views = len(self.runner.views)
        replies = self.stop(sup, 'shutdown')
        self.close_game(sup, pid, peer)
        self.assertEqual((replies[0]['result'], replies[0]['close'], sup.state), ('confirmed', 'exited', 'STOPPING'))
        self.assertEqual((self.runner.black_up, sup.black, sup.black_end_at, self.runner.lid_up, sup.lid_held),
                         (True, True, None, True, True))
        self.assertEqual((self.runner.black_stops, self.runner.lid_stops, len(self.runner.views)), ([], [], views))
        self.assertNotIn(sup.hide_black, [action for _, action in sup.pending()])
        # Their own limit ends them, if the session is not torn down after all: nothing is stopped twice.
        sup.on_black_exit(0)
        sup.on_lid_block_exit(0)
        self.assertEqual((sup.black, sup.lid_held, self.runner.black_stops, self.runner.lid_stops),
                         (False, False, [], []))
        # Unsaved and overrun too: a shutdown shows no window, so nothing has to be seen.
        sup, pid, peer = self.session()
        replies = self.stop(sup, 'shutdown')
        self.advance(desktop.STOP_SAVE_WAIT)
        sup.tick()
        self.assertEqual(self.runner.signals, ['SIGTERM'])
        self.advance(desktop.STOP_BUDGET - desktop.STOP_SAVE_WAIT)
        sup.tick()
        self.assertEqual((replies[0]['result'], replies[0]['close'], sup.state), ('unsaved', 'overrun', 'STOPPING'))
        self.assertEqual((self.runner.black_up, self.runner.lid_up), (True, True))
        # A logout that goes through: labwc's end takes the black screen with it, and nothing goes black again.
        sup, pid, peer = self.session()
        replies = self.stop(sup, 'logout')
        self.close_game(sup, pid, peer)
        sup.on_labwc_gone()
        self.assertEqual((self.runner.black_up, sup.black), (False, False))
        self.end(sup, 'labwc ended')
        self.assertEqual((replies[0]['logout'], self.runner.blacks, self.runner.lid_up), ('exited', [self.LIMIT], True))

    def test_a_restart_hands_the_black_screen_over_to_its_startup_cover(self):
        sup, pid, peer = self.session()
        covers = len(self.runner.covers)
        replies = self.stop(sup, 'restart')
        self.close_game(sup, pid, peer)
        self.assertEqual((replies[0]['restart'], sup.state, self.runner.covers[covers:], self.runner.cover_up),
                         ('started', 'STARTING', [True], True))
        # The startup cover has only been started: the black screen stays below it until it is up.
        self.assertEqual((self.runner.black_up, sup.black_end_at), (True, self.now[0] + desktop.BLACK_HANDOVER))
        self.assertEqual((self.runner.lid_up, len(self.runner.lid_stops)), (False, 1))  # the stop has ended
        self.advance(desktop.BLACK_HANDOVER - 0.1)
        sup.tick()
        self.assertTrue(self.runner.black_up)
        self.advance(0.1)
        sup.tick()
        self.assertEqual((self.runner.black_up, sup.black, sup.black_end_at, self.runner.cover_up),
                         (False, False, None, True))
        # A home that is ready sooner is never behind it.
        sup, pid, peer = self.session()
        self.stop(sup, 'restart')
        self.close_game(sup, pid, peer)
        self.run_game(sup)
        self.assertTrue(self.runner.black_up)
        self.ready(sup)
        self.assertEqual((sup.state, self.runner.black_up, sup.black_end_at), ('IN_WORLD', False, None))
        # No startup cover (it did not start): what the start shows must be seen at once.
        sup, pid, peer = self.session()
        self.runner.cover_error = OSError('no cover')
        replies = self.stop(sup, 'restart')
        self.close_game(sup, pid, peer)
        self.assertEqual((replies[0]['restart'], self.runner.black_up, sup.black_end_at), ('started', False, None))

    def test_a_shutdown_that_joins_a_plain_stop_goes_black_then(self):
        sup, pid, peer = self.session()
        self.stop(sup)
        self.assertEqual(self.runner.blacks, [])
        self.stop(sup, 'shutdown')
        self.assertEqual((sup.stop.kind, self.runner.blacks, self.runner.lid_blocks),
                         ('shutdown', [self.LIMIT], [self.LIMIT]))
        # The session's signal joins the same way, and begins a stop of its own the same way.
        sup, pid, peer = self.session()
        self.stop(sup)
        self.end(sup)
        self.assertEqual((sup.stop.kind, self.runner.black_up), ('shutdown', True))
        sup, pid, peer = self.session()
        self.end(sup)
        self.assertEqual((sup.stop.kind, self.runner.black_up, self.runner.lid_up), ('shutdown', True, True))
        # labwc's own end leaves no screen to go black on.
        sup, pid, peer = self.session()
        sup.on_labwc_gone()
        self.end(sup, 'labwc ended')
        self.assertEqual((sup.stop.kind, self.runner.blacks, self.runner.lid_up), ('shutdown', [], True))

    def test_every_stop_holds_the_lid_block_and_lets_go_when_the_session_goes_on(self):
        sup, pid, peer = self.session()
        replies = self.stop(sup)
        self.assertEqual((self.runner.lid_blocks, self.runner.lid_up, self.runner.signals), ([self.LIMIT], True, []))
        self.close_game(sup, pid, peer)
        self.assertEqual((replies[0]['ok'], self.runner.lid_up, self.runner.lid_stops),
                         (True, False, [self.now[0] + desktop.COVER_STOP_WAIT]))
        self.assertIs(sup.status()['lid_block'], False)
        # With nothing running the stop ends at once, and its block with it.
        sup, _, _ = self.session(game=False)
        self.stop(sup)
        self.assertEqual((self.runner.lid_blocks, self.runner.lid_up), ([self.LIMIT], False))
        # A supervisor that replaces one in the middle of a stop holds a block of its own (the first one's went
        # with it); the black screen went too, and no helper has reported to the new one.
        sup, pid, peer = self.session()
        self.stop(sup, 'shutdown')
        second = self.supervisor()
        second.start()
        self.assertEqual((second.stop.kind, second.lid_held, second.black), ('shutdown', True, False))
        self.assertEqual((self.runner.lid_blocks, self.runner.blacks), ([self.LIMIT, self.LIMIT], [self.LIMIT]))

    def test_a_black_screen_or_a_lid_block_that_fails_is_one_log_line_and_changes_nothing_else(self):
        sup, pid, peer = self.session()
        self.runner.black_error = OSError('no cover')
        self.runner.lid_error = OSError('no systemd-inhibit')
        with self.logged('WARNING') as logs:
            replies = self.stop(sup, 'shutdown')
        self.assertEqual(len(logs.output), 2, logs.output)
        self.assertEqual((sup.black, sup.lid_held, sup.stop.kind, sup.stop.phase), (False, False, 'shutdown', 'save'))
        self.close_game(sup, pid, peer)
        self.assertEqual((replies[0]['ok'], replies[0]['result'], replies[0]['close']), (True, 'confirmed', 'exited'))
        self.assertEqual((self.runner.black_stops, self.runner.lid_stops), ([], []))
        # One that ends by itself (logind refused the block, the black screen lost its display): one line each.
        sup, pid, peer = self.session()
        replies = self.stop(sup, 'restart')
        with self.logged('WARNING') as logs:
            sup.on_lid_block_exit(1)
            sup.on_black_exit(1)
        self.assertEqual(len(logs.output), 2, logs.output)
        self.assertEqual((sup.black, sup.lid_held), (False, False))
        self.close_game(sup, pid, peer)
        self.assertEqual((replies[0]['restart'], self.runner.black_stops, self.runner.lid_stops), ('started', [], []))

    def test_hide_cover_takes_the_black_screen_away_too(self):
        sup, pid, peer = self.session()
        self.stop(sup, 'shutdown')
        self.assertEqual(sup.owner_hides_cover(), 'The black screen is gone.')
        self.assertEqual((self.runner.black_up, sup.black, sup.stop.kind), (False, False, 'shutdown'))
        self.assertEqual(sup.owner_hides_cover(), 'No startup cover is up.')


class HomeBase(StopBase):
    """Section 4, package 48's leftovers. A test starts with no home at all and makes the folders it needs, all of
    them in its own temporary home."""
    OLD = 'AresHub-2026-11-19_10-00-00-000'
    NEW = 'AresHub-new-2026-11-19_10-00-00-250'

    def setUp(self):
        base.Base.setUp(self)  # not GuardianBase's: it makes the home
        self.runner = StopRunner()
        desktop.provision(self.paths, self.lock)
        self.worlds = pathlib.Path(self.paths.worlds)

    def world(self, name='AresHub', **changes):
        return base.make_world(self.paths, dict(self.lock, world=name), **changes)

    def listing(self):
        """Every entry under the worlds folder with its inode and, for a file, its size. A move keeps every inode,
        and nothing may ever vanish or change. Links are listed, never followed."""
        found = []
        for folder, folders, files in os.walk(self.worlds, followlinks=False):
            for name in folders + files:
                path = pathlib.Path(folder, name)
                entry = path.lstat()
                found.append((str(path.relative_to(self.worlds)), entry.st_ino,
                              entry.st_size if path.is_file() and not path.is_symlink() else None))
        return sorted(found)

    @staticmethod
    def renamed(listing, old, new):
        """What a listing must be after the one folder `old` was renamed to `new`: nothing else differs."""
        return sorted((new + name[len(old):] if name == old or name.startswith(old + '/') else name, *rest)
                      for name, *rest in listing)

    def logged(self, level):
        desktop.LOG.disabled = False
        self.addCleanup(setattr, desktop.LOG, 'disabled', True)
        return self.assertLogs('aresos-desktop', level)

    @contextlib.contextmanager
    def lock_held(self):
        """The desktop lock held as a game's wrapper holds it, by a descriptor of the test's own."""
        os.makedirs(self.paths.run_dir, exist_ok=True)
        fd = os.open(self.paths.jvm_lock, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(fd)

    def setup_game(self):
        """A first start with no home and no state yet: (the supervisor, the PID of its setup launch's game)."""
        self.runner = StopRunner()
        for path in (self.paths.runtime_file, self.paths.stop_block, self.paths.state_file):
            pathlib.Path(path).unlink(missing_ok=True)
        sup = self.supervisor()
        sup.start()
        self.assertEqual((sup.state, sup.reason), ('SETUP', 'setup'))
        pid, _ = self.run_game(sup)
        self.assertEqual(sup.launch.mode, 'setup')
        return sup, pid

    def missing(self):
        """His home was there once and is gone: the supervisor at its `world_missing` window."""
        desktop.Persisted(hub_seen=True).save(self.paths.state_file)
        sup = self.next_session()
        self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('RECOVERY', 'world_missing', True))
        return sup


class FirstHomeTest(HomeBase):
    """4.1: the first home died while it was made."""
    UNFINISHED = r'AresHub-unfinished-[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{3}'

    def died_while_made(self, heartbeat=True):
        """The home's folder appears during a setup launch that started without one, and the game dies before the
        home is finished: (the supervisor, the half-made folder)."""
        sup, pid = self.setup_game()
        self.assertIsNone(sup.persisted.first_home)
        half = self.world(provisioned=None)  # the hub build never finished
        if heartbeat:
            self.heartbeat(sup, ready=False)
        self.end_game(sup, pid, 1)
        self.assertEqual((sup.state, sup.reason), ('SETUP', 'setup_crashed'))
        return sup, half

    def unfinished(self):
        """A later session's start at the `setup_unfinished` window: (the supervisor, the half-made folder)."""
        _, half = self.died_while_made()
        sup = self.next_session()
        self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('SETUP', 'setup_unfinished', False))
        return sup, half

    def test_a_first_home_that_died_while_it_was_made_is_moved_aside_by_retry_and_setup_starts_again(self):
        sup, half = self.died_while_made()
        found = half.lstat()
        self.assertEqual(self.stored()['first_home'], {'launch': sup.launch.id, 'device': found.st_dev,
                                                       'inode': found.st_ino, 'seen': self.wall[0]})
        before, prisms, views = self.listing(), len(self.runner.prisms), len(self.runner.views)
        self.assertEqual(sup.retry(), (True, 'State: SETUP'))  # a later start: it only says what it found
        self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('SETUP', 'setup_unfinished', False))
        self.assertEqual((len(self.runner.prisms), self.listing()), (prisms, before))  # nothing started or moved
        self.assertEqual(len(self.runner.views), views + 1)
        text = self.runner.views[-1]
        self.assertEqual(text, sup.status()['message'])
        for words in ('AresOS: your first home was not finished', 'this folder is only half made:',
                      '  ~/.local/share/aresos/worlds/AresHub\n',
                      '(the hub build has no completion record (aresos-home.provisioned))',
                      'Type  retry  and press Enter: AresOS moves that folder aside, as\n'
                      'AresHub-unfinished-<date> beside it (nothing is deleted), and makes your home again.'):
            self.assertIn(words, text)
        self.assertNotIn('damaged', text)
        self.assertNotIn('backup', text)
        self.assertLessEqual(max(len(line) for line in text.splitlines()), 104)  # the window's width
        name = desktop.dated_names('AresHub-unfinished-', self.wall[0])[0]
        self.assertRegex(name, rf'\A{self.UNFINISHED}\Z')
        self.assertEqual(sup.retry(), (True, f'Moved the unfinished home to {name} (nothing was deleted). '
                                             'State: SETUP'))
        self.assertEqual(self.listing(), self.renamed(before, 'AresHub', name))  # every file, by its inode
        self.assertFalse(os.path.lexists(self.worlds / 'AresHub'))
        self.assertEqual((sup.state, sup.reason), ('SETUP', 'setup'))
        self.assertEqual(len(self.runner.prisms), prisms + 1)  # setup starts again
        self.assertNotIn('--world', self.runner.prisms[-1][0])
        self.assertNotIn('first_home', self.stored())
        self.assertIsNone(desktop.dated_home(name, 'AresHub'))  # never offered as a home, never a leftover
        self.assertEqual(sup.status()['leftovers'], [])

    def test_the_folder_is_looked_for_at_the_launchs_end_and_the_record_survives_a_reboot_and_r28(self):
        sup, half = self.died_while_made(heartbeat=False)  # it appeared after the last heartbeat
        self.assertEqual(self.stored()['first_home']['inode'], half.lstat().st_ino)
        stored = self.stored()
        self.assertEqual(stored['schema'], 1)
        self.assertEqual(set(stored) - set(R28_KEYS), {'first_home'})  # the one new key, which R28 never reads
        mine = desktop.Persisted.load(self.paths.state_file)
        self.assertEqual(r28_load(stored), {key: getattr(mine, key) for key in R28_KEYS[1:]})
        self.assertEqual(mine.first_home, stored['first_home'])
        before = self.listing()
        sup = self.next_session()
        self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('SETUP', 'setup_unfinished', False))
        self.assertEqual((self.runner.prisms, self.listing()), ([], before))
        self.assertFalse(self.stored()['latched'])
        # Prism started by hand gets no game either, and still nothing is latched.
        ok, reply = sup.on_jvm_start(self.jvm_request())
        self.assertEqual((ok, reply), (False, {'message': 'Your first home was not finished; the AresOS window '
                                                          'says what to do.'}))
        self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('SETUP', 'setup_unfinished', False))
        # `restart` starts nothing and moves nothing: only the window's `retry` moves the folder.
        self.stop(sup, 'restart')
        sup.tick()
        self.assertEqual((sup.state, sup.reason, self.runner.prisms, self.listing()),
                         ('SETUP', 'setup_unfinished', [], before))

    def test_a_replacement_supervisor_goes_on_looking(self):
        first, pid = self.setup_game()
        sup = self.supervisor()
        sup.start()  # the game still runs: adopted, with the runtime file's word that it is a setup launch
        self.assertEqual((sup.launch.adopted, sup.launch.mode, sup.launch.id), (True, 'setup', first.launch.id))
        half = self.world(level=None)
        self.heartbeat(sup, ready=False)
        self.assertEqual(self.stored()['first_home']['inode'], half.lstat().st_ino)
        self.end_game(sup, pid, 137)
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'killed'))  # a kill stays a kill
        self.assertEqual(self.next_session().reason, 'killed')

    def test_every_other_damaged_world_stays_exactly_as_today(self):
        def damaged(sup, before):
            self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('RECOVERY', 'world_damaged', True))
            self.assertIn('Restore it from a backup', self.runner.views[-1])
            sup.retry()  # moves nothing, starts nothing
            self.assertEqual((sup.state, sup.reason, self.runner.prisms, self.listing()),
                             ('RECOVERY', 'world_damaged', [], before))

        with self.subTest('a half-made home the supervisor never saw appear'):
            half = self.world(provisioned=None)
            damaged(self.next_session(), self.listing())
            half.rename(self.worlds / 'kept-1')
        with self.subTest('a home that was seen ready once'):
            sup, half = self.died_while_made()
            sup.persisted.hub_seen = True
            sup.save()
            damaged(self.next_session(), self.listing())
            half.rename(self.worlds / 'kept-2')
        with self.subTest('another folder under the home\'s name'):
            sup, half = self.died_while_made()
            half.rename(self.worlds / 'kept-3')
            self.world(marker=None)  # not the folder that was seen: another inode
            damaged(self.next_session(), self.listing())
            (self.worlds / 'AresHub').rename(self.worlds / 'kept-4')
        with self.subTest('a link under the home\'s name'):
            sup, half = self.died_while_made()
            half.rename(self.worlds / 'kept-5')
            os.symlink(self.worlds / 'kept-5', self.worlds / 'AresHub')
            damaged(self.next_session(), self.listing())

    def test_a_start_that_finds_the_first_home_sound_forgets_it_so_later_damage_is_damage(self):
        sup, half = self.died_while_made()
        (half / 'aresos-home.provisioned').write_text('complete\n')  # it was finished after all
        sup = self.next_session()
        self.assertEqual(sup.state, 'STARTING')
        self.assertIn('--world', self.runner.prisms[-1][0])
        self.assertNotIn('first_home', self.stored())
        (half / 'data/aresos/desktop.dat').write_bytes(b'not a marker')  # damage, with hub_seen still false
        before = self.listing()
        sup = self.next_session()
        self.assertEqual((sup.state, sup.reason, sup.persisted.latched), ('RECOVERY', 'world_damaged', True))
        sup.retry()
        self.assertEqual(self.listing(), before)

    def test_a_first_home_that_was_finished_and_seen_ready_is_forgotten(self):
        sup, pid = self.setup_game()
        home = self.world()
        self.heartbeat(sup, ready=False)
        self.assertEqual(self.stored()['first_home']['inode'], home.lstat().st_ino)
        self.ready(sup)
        stored = self.stored()
        self.assertEqual((stored['hub_seen'], 'first_home' in stored, sup.state), (True, False, 'IN_WORLD'))

    def test_retry_moves_nothing_while_the_lock_is_held_the_rename_fails_or_the_folder_changed(self):
        sup, half = self.unfinished()
        before = self.listing()
        with self.lock_held():  # a game this supervisor cannot see
            ok, text = sup.retry()
        self.assertEqual((ok, text), (False, 'The unfinished home was not moved: A Minecraft that AresOS cannot '
                                             'see holds the desktop lock. Close it first. Nothing is changed. '
                                             'Type retry to try again.'))
        self.assertEqual((sup.state, sup.reason, self.runner.prisms, self.listing()),
                         ('SETUP', 'setup_unfinished', [], before))
        with mock.patch.object(desktop, 'rename_noreplace', side_effect=OSError(22, 'Invalid argument')):
            ok, text = sup.retry()
        self.assertEqual((ok, 'could not be moved ([Errno 22] Invalid argument)' in text), (False, True))
        self.assertEqual((sup.state, sup.reason, self.runner.prisms, self.listing()),
                         ('SETUP', 'setup_unfinished', [], before))
        self.assertIn('first_home', self.stored())
        # He put a sound home there himself: nothing is moved, and the start decides anew.
        half.rename(self.worlds / 'kept-by-him')
        self.world()
        before = self.listing()
        self.assertEqual(sup.retry(), (True, 'State: STARTING'))
        self.assertEqual(self.listing(), before)
        self.assertIn('--world', self.runner.prisms[-1][0])

    def test_a_name_that_is_taken_gets_a_suffix_and_what_has_it_is_never_replaced(self):
        sup, half = self.unfinished()
        names = desktop.dated_names('AresHub-unfinished-', self.wall[0])
        self.assertEqual(names[1:3], [names[0] + '-1', names[0] + '-2'])  # as HomeSwap.datedName counts
        (self.worlds / names[0]).mkdir()  # an empty folder: os.rename would have replaced it
        (self.worlds / names[1]).write_text('his')
        before = self.listing()
        self.assertEqual(sup.retry(), (True, f'Moved the unfinished home to {names[2]} (nothing was deleted). '
                                             'State: SETUP'))
        self.assertEqual(self.listing(), self.renamed(before, 'AresHub', names[2]))
        self.assertEqual(((self.worlds / names[1]).read_text(), list((self.worlds / names[0]).iterdir())),
                         ('his', []))


class UseHomeTest(HomeBase):
    """4.2: one way to move a home, and `aresos-desktop use-home <folder>`."""
    MOVED = ' is your home AresHub now (the folder was renamed; nothing was deleted). Type retry.'

    def test_use_home_makes_a_dated_home_the_home_and_retry_opens_it(self):
        for name in (self.OLD, self.NEW, self.OLD + '-2'):
            with self.subTest(name):
                self.world(name)
                sup = self.missing()
                before = self.listing()
                self.assertEqual(sup.use_home(name), (True, name + self.MOVED))
                self.assertEqual(self.listing(), self.renamed(before, name, 'AresHub'))
                self.assertEqual((sup.reason, self.runner.prisms), ('world_missing', []))  # nothing starts by itself
                self.assertEqual(sup.retry(), (True, 'State: STARTING'))
                self.assertIn('--world', self.runner.prisms[-1][0])
                (self.worlds / 'AresHub').rename(self.worlds / f'kept-{name}')

    def test_only_a_dated_home_that_passes_the_checks_and_only_while_no_home_exists(self):
        self.world(self.OLD)
        self.world('AresHub-unfinished-2026-11-19_10-00-00-000')
        self.world('Other')
        sup = self.missing()
        before = self.listing()
        for name in ('AresHub', 'Other', 'AresHub-unfinished-2026-11-19_10-00-00-000', '../' + self.OLD,
                     self.OLD + '/', str(self.worlds / self.OLD), 'AresHub-2026-11-19', self.OLD + '-0',
                     self.OLD + 'x', self.OLD.replace('2026', '२०२६'), '', '.', None, 7, [self.OLD]):
            with self.subTest(name):
                self.assertEqual(sup.use_home(name), (False, 'Not moved: use-home takes the name of a dated home in '
                                 '~/.local/share/aresos/worlds: AresHub-<date> or AresHub-new-<date>.'))
        self.assertEqual(sup.use_home(self.NEW), (False, f'Not moved: There is no folder {self.NEW} in '
                                                         '~/.local/share/aresos/worlds.'))
        damaged = 'AresHub-2026-11-20_10-00-00-000'
        self.world(damaged, home=None)
        self.assertEqual(sup.use_home(damaged), (False, f'Not moved: {damaged} does not pass AresOS\'s checks of a '
                                                 'home (the saved Nether home (data/aresos/nether_home.dat) is '
                                                 'missing).'))
        link = 'AresHub-2026-11-21_10-00-00-000'
        os.symlink(self.worlds / self.OLD, self.worlds / link)
        self.assertEqual(sup.use_home(link), (False, f'Not moved: {link} is not a folder.'))
        before = self.listing()
        for what, make, remove in (('a home', self.world, lambda: (self.worlds / 'AresHub').rename(
                                        self.worlds / 'kept')),
                                   ('an empty folder', (self.worlds / 'AresHub').mkdir,
                                    (self.worlds / 'AresHub').rmdir),
                                   ('a file', (self.worlds / 'AresHub').touch, (self.worlds / 'AresHub').unlink),
                                   ('a link to nothing', lambda: os.symlink('nowhere', self.worlds / 'AresHub'),
                                    (self.worlds / 'AresHub').unlink)):
            with self.subTest(what):
                make()  # the test's own stand-in, taken away again below
                there = self.listing()
                self.assertEqual(sup.use_home(self.OLD), (False, 'Not moved: AresHub exists. use-home only fills '
                                 'the place of a missing home and never replaces one.'))
                self.assertEqual(self.listing(), there)
                remove()
        self.assertEqual(sup.use_home(self.OLD), (True, self.OLD + self.MOVED))

    def test_no_home_is_moved_while_a_game_starts_runs_or_is_being_stopped(self):
        starting = 'Not moved: Minecraft is starting right now. Try again once it runs or has closed.'
        self.world(self.OLD)
        before = self.listing()
        sup = self.next_session()  # no home was ever seen: setup, and Prism is up
        self.assertEqual((sup.state, len(self.runner.prisms)), ('SETUP', 1))
        self.assertEqual(sup.use_home(self.OLD), (False, starting))
        self.assertTrue(sup.on_jvm_start(self.jvm_request())[0])
        self.assertTrue(sup.in_handoff())
        self.assertEqual(sup.use_home(self.OLD), (False, starting))
        sup, pid = self.setup_game()
        self.assertEqual(sup.use_home(self.OLD), (False, 'Not moved: Minecraft is running. Stop it first '
                                                         '(aresos-desktop stop), then try again.'))
        self.runner.processes.pop(pid)  # gone, but its end is not accounted for yet
        sup.on_jvm_gone()
        self.assertEqual(sup.use_home(self.OLD)[0], False)
        sup, pid = self.setup_game()
        self.stop(sup)
        self.assertIsNotNone(sup.stop)
        self.assertEqual(sup.use_home(self.OLD), (False, 'Not moved: AresOS is stopping Minecraft right now. Try '
                                                         'again when that is done.'))
        self.assertEqual(self.listing(), before)
        sup, pid = self.setup_game()
        self.end_game(sup, pid, 0)  # the game is gone and accounted for
        self.assertEqual(sup.use_home(self.OLD), (True, self.OLD + self.MOVED))

    def test_no_home_is_moved_once_the_session_is_ending_or_while_the_lock_is_held_or_unknown(self):
        self.world(self.OLD)
        before = self.listing()
        sup = self.missing()
        with self.lock_held():
            self.assertEqual(sup.use_home(self.OLD), (False, 'Not moved: A Minecraft that AresOS cannot see holds '
                                                             'the desktop lock. Close it first.'))
        with mock.patch.object(desktop, 'take_desktop_lock', side_effect=PermissionError(13, 'Permission denied')):
            self.assertEqual(sup.use_home(self.OLD), (False, 'Not moved: AresOS cannot tell whether Minecraft is '
                             'running (the desktop lock: [Errno 13] Permission denied).'))
        self.stop(sup, 'shutdown')
        sup.tick()
        self.assertEqual((sup.stop, sup.blocked()), (None, True))
        self.assertEqual(sup.use_home(self.OLD), (False, 'Not moved: AresOS is shutting down or logging out.'))
        self.assertEqual(self.listing(), before)

    def test_the_lock_is_held_from_the_checks_to_the_rename_and_free_again_afterwards(self):
        self.world(self.OLD)
        sup = self.missing()
        seen = []

        def proof(found):
            seen.append(desktop.take_desktop_lock(self.paths))  # what a wrapper that starts right now would get
            return None

        self.assertEqual(sup.move_home(self.OLD, ['AresHub'], proof), ('AresHub', ''))
        self.assertEqual(seen, [None])
        for outcome in (sup.move_home('AresHub', [self.OLD], lambda found: 'no'),
                        sup.move_home('none', [self.OLD], lambda found: None)):
            self.assertIsNone(outcome[0])
            fd = desktop.take_desktop_lock(self.paths)  # free again after a refusal too
            self.assertIsNotNone(fd)
            os.close(fd)

    def test_a_name_that_is_taken_is_never_replaced_whatever_the_checks_said(self):
        old = self.world(self.OLD)
        sup = self.missing()
        (self.worlds / 'AresHub').mkdir()  # it appeared after the checks: os.rename would replace an empty folder
        before = self.listing()
        self.assertEqual(sup.move_home(self.OLD, ['AresHub'], lambda found: None),
                         (None, 'AresHub exists already.'))
        self.assertEqual(self.listing(), before)
        (self.worlds / 'AresHub').rmdir()

        def swap(found):  # another folder took the name while it was checked
            old.rename(self.worlds / 'aside')
            self.world(self.OLD)
            return None

        self.assertEqual(sup.move_home(self.OLD, ['AresHub'], swap),
                         (None, f'{self.OLD} changed while it was checked.'))
        self.assertFalse(os.path.lexists(self.worlds / 'AresHub'))
        for source, target in (('../' + self.OLD, 'AresHub'), (self.OLD, '../AresHub'), (self.OLD, 'a/b'),
                               (self.OLD, '..'), ('', 'AresHub')):
            self.assertEqual(sup.move_home(source, [target], lambda found: None),
                             (None, 'A home is one folder inside the worlds folder.'))

    def test_the_rename_itself_refuses_a_target_that_exists(self):
        folder = os.open(self.worlds, os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(os.close, folder)
        (self.worlds / 'a').mkdir()
        (self.worlds / 'a/keep').write_text('a')
        (self.worlds / 'b').mkdir()
        (self.worlds / 'f').write_text('f')
        for target in ('b', 'f', 'a'):
            with self.assertRaises(FileExistsError):
                desktop.rename_noreplace(folder, 'a', target)
        with self.assertRaises(FileNotFoundError):
            desktop.rename_noreplace(folder, 'none', 'c')
        desktop.rename_noreplace(folder, 'a', 'c')
        self.assertEqual(((self.worlds / 'c/keep').read_text(), list((self.worlds / 'b').iterdir()),
                          (self.worlds / 'f').read_text(), (self.worlds / 'a').exists()), ('a', [], 'f', False))

    def test_one_function_moves_a_world_folder_and_nothing_deletes_one(self):
        source = (base.CONFIG / 'usr/libexec/aresos-desktop').read_text(encoding='utf-8')
        callers = {}
        for function in ast.walk(ast.parse(source)):
            if isinstance(function, ast.FunctionDef):
                for node in ast.walk(function):
                    if isinstance(node, ast.Call):
                        name = getattr(node.func, 'id', getattr(node.func, 'attr', None))
                        callers.setdefault(name, set()).add(function.name)
        self.assertEqual(callers['rename_noreplace'], {'move_home'})
        self.assertEqual(callers['move_home'], {'move_unfinished', 'use_home'})
        self.assertEqual(callers['renameat2'], {'rename_noreplace'})
        self.assertEqual(desktop.RENAME_NOREPLACE, 1)
        # Every other call that renames or removes anything, as before this package: the instance's staging copy,
        # `reset-instance` (the instance, and its link to the worlds), and the supervisor's own small files.
        self.assertEqual(re.findall(r'os\.rename\((.*?)\)', source), ['staging, target', 'root, aside'])
        self.assertEqual(re.findall(r'os\.replace\((.*?)\)', source), ['temporary, path'])
        self.assertEqual(re.findall(r'shutil\.\w+\((.*?)\)', source), ['staging'])
        # Step 7 added one: the shutdown guard's fallback record, removed once the start has applied it.
        self.assertEqual(re.findall(r'os\.(?:unlink|remove)\((.*?)\)', source),
                         ['temporary', 'self.paths.guard_file', 'self.paths.stop_block', 'path', 'self.paths.socket',
                          'saves'])
        for call in ('os.rmdir(', 'os.removedirs(', 'os.renames(', '.rmtree(self', '.unlink()', '.rmdir()',
                     'os.truncate(', 'os.system('):
            self.assertNotIn(call, source)


class MissingHomeTest(HomeBase):
    """4.3: `world_missing` says where the home is."""

    def test_the_names_and_the_date_pattern_equal_homeswaps(self):
        swap = (ROOT / 'mod/src/main/java/dev/aresos/world/HomeSwap.java').read_text(encoding='utf-8')
        nether = (ROOT / 'mod/src/main/java/dev/aresos/world/NetherHome.java').read_text(encoding='utf-8')
        self.assertEqual(re.search(r'String SAVE_FOLDER = "([^"]+)";', nether).group(1), base.LOCK['world'])
        self.assertEqual(re.search(r'String ARCHIVE_PREFIX = NetherHome\.SAVE_FOLDER \+ "([^"]+)";', swap).group(1),
                         desktop.HOME_ARCHIVE)
        self.assertEqual(re.search(r'String STAGING_PREFIX = NetherHome\.SAVE_FOLDER \+ "([^"]+)";', swap).group(1),
                         desktop.HOME_STAGING)
        pattern = re.search(r'DATE = DateTimeFormatter\.ofPattern\("([^"]+)"\);', swap).group(1)
        self.assertEqual(re.sub('[A-Za-z]+', lambda run: f'[0-9]{{{len(run.group())}}}', pattern),
                         desktop.HOME_DATE)
        # Its -1, -2 suffix: counted from 1 behind the dated name, without leading zeros.
        self.assertIn('for (int suffix = 1; Files.exists(target, LinkOption.NOFOLLOW_LINKS); suffix++) '
                      'target = saves.resolve(name + "-" + suffix);', swap)
        # The supervisor's own dated names are written the same way.
        python = {'yyyy': '%Y', 'MM': '%m', 'dd': '%d', 'HH': '%H', 'mm': '%M', 'ss': '%S', 'SSS': '250'}
        at = 1_800_000_000.25
        stamp = desktop.time.strftime(re.sub('[A-Za-z]+', lambda run: python[run.group()], pattern),
                                      desktop.time.localtime(at))
        self.assertEqual(desktop.dated_names('AresHub-', at)[:3],
                         [f'AresHub-{stamp}', f'AresHub-{stamp}-1', f'AresHub-{stamp}-2'])
        for name, kind in ((f'AresHub-{stamp}', 'archive'), (f'AresHub-{stamp}-1', 'archive'),
                           (f'AresHub-{stamp}-12', 'archive'), (f'AresHub-new-{stamp}', 'staging'),
                           (f'AresHub-new-{stamp}-3', 'staging'), (f'AresHub-unfinished-{stamp}', None),
                           (f'AresHub-{stamp}-0', None), (f'AresHub-{stamp}-01', None), (f'AresHub-{stamp}-', None),
                           (f'AresHub-{stamp[:-4]}', None), (f'AresHub-new-new-{stamp}', None),
                           (f'aresHub-{stamp}', None), (f'AresHub{stamp}', None), (f'AresHub-{stamp}\n', None),
                           ('AresHub', None), ('AresHub-', None), ('AresHub-new-', None)):
            with self.subTest(name):
                found = desktop.dated_home(name, 'AresHub')
                self.assertEqual(found and found[0], kind)

    def test_world_missing_names_the_newest_dated_home_and_the_new_home_that_pass_the_checks(self):
        newest, new = 'AresHub-2026-11-18_08-00-00-000-2', 'AresHub-new-2026-11-19_08-00-01-000'
        self.world('AresHub-2026-11-17_08-00-00-000')
        self.world('AresHub-2026-11-18_08-00-00-000')
        self.world('AresHub-2026-11-18_08-00-00-000-1')
        self.world(newest)  # the same moment, taken three times: the highest suffix is the newest
        self.world('AresHub-2026-11-19_08-00-00-000', home=None)  # newer, but no home
        os.symlink(self.worlds / newest, self.worlds / 'AresHub-2026-11-20_08-00-00-000')  # a link is no home
        self.world('AresHub-new-2026-11-18_08-00-00-000')
        self.world(new)
        self.world('AresHub-new-2026-11-19_09-00-00-000', provisioned=None)  # never finished
        self.world('AresHub-unfinished-2026-11-21_08-00-00-000')
        self.world('AresHub-backup')
        before = self.listing()
        sup = self.missing()
        text = self.runner.views[-1]
        self.assertEqual(text, sup.status()['message'])
        self.assertEqual(text, (
            'AresOS: recovery\n\n'
            'Your hub world is missing: ~/.local/share/aresos/worlds/AresHub\n'
            'AresOS opened it before and never creates a replacement by itself.\n\n'
            'In the same folder AresOS found (it moves nothing by itself):\n\n'
            'The newest home under a dated name that passes its checks, most likely the home you had:\n'
            f'  {newest}\n'
            'To make it your home again (the folder is renamed, nothing else changes):\n'
            f'  aresos-desktop use-home {newest}\n'
            'then  retry\n\n'
            'A new home that was still being made, and is complete:\n'
            f'  {new}\n'
            'To make that one your home instead:\n'
            f'  aresos-desktop use-home {new}\n'
            'then  retry\n\n'
            'Or put the folder back (from a backup), then type  retry  and press enter to try again.\n'
            'To start a new hub instead:  aresos-desktop forget-hub  then  retry\n'))
        self.assertLessEqual(max(len(line) for line in text.splitlines()), 104)
        self.assertLessEqual(len(text.splitlines()), 30)  # the window's 32 rows, with its prompt
        self.assertEqual(sup.found_homes(), (newest, new))
        sup.retry()
        self.assertEqual((sup.reason, self.runner.prisms, self.listing()), ('world_missing', [], before))
        # The window's line works as written, and the other home is then only a leftover.
        self.assertTrue(sup.use_home(newest)[0])
        self.assertEqual(sup.retry(), (True, 'State: STARTING'))

    def test_world_missing_with_one_of_them_or_none(self):
        sup = self.missing()
        self.assertEqual(self.runner.views[-1], (
            'AresOS: recovery\n\n'
            'Your hub world is missing: ~/.local/share/aresos/worlds/AresHub\n'
            'AresOS opened it before and never creates a replacement by itself.\n\n'
            'Put the folder back (from a backup), then type  retry  and press enter to try again.\n'
            'To start a new hub instead:  aresos-desktop forget-hub  then  retry\n'))  # as before this package
        self.world(self.NEW)
        self.world(self.OLD, level=None)
        text = self.missing().message()
        self.assertIn('In the same folder AresOS found (it moves nothing by itself):\n\n'
                      'A new home that was still being made, and is complete:\n'
                      f'  {self.NEW}\nTo make it your home:\n  aresos-desktop use-home {self.NEW}\nthen  retry\n\n'
                      'Or put the folder back', text)
        self.assertEqual(text.count('use-home'), 1)
        self.assertNotIn(self.OLD, text)
        # More dated folders than are ever read: the newest are read, and the folder is only listed.
        for day in range(desktop.HOMES_CHECKED + 4):
            self.world(f'AresHub-2026-12-{day + 1:02d}_08-00-00-000', marker=None)
        with mock.patch.object(desktop, 'check_world', wraps=desktop.check_world) as checks:
            self.assertEqual(self.missing().found_homes(), (None, self.NEW))
        self.assertLessEqual(checks.call_count, 2 * (desktop.HOMES_CHECKED + 2))


class DatedHomeReadyTest(HomeBase):
    """4.4: a dated home reported ready."""

    def test_a_dated_home_reported_ready_is_checked_becomes_the_active_world_and_sets_hub_seen(self):
        self.world(self.OLD)
        sup, pid = self.setup_game()  # no AresHub, and no home was ever seen
        self.ready(sup, self.OLD)
        self.assertEqual((sup.state, sup.launch.ready, sup.active_world()), ('IN_WORLD', True, self.OLD))
        self.assertTrue(self.stored()['hub_seen'])
        self.end_game(sup, pid, 0)
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'quit'))
        prisms = len(self.runner.prisms)
        sup = self.next_session()  # never a silent new setup beside his old home
        self.assertEqual((sup.state, sup.reason, self.runner.prisms), ('RECOVERY', 'world_missing', []))
        self.assertIn(f'  aresos-desktop use-home {self.OLD}\n', self.runner.views[-1])
        self.assertEqual(prisms, 1)

    def test_a_world_that_is_damaged_missing_or_outside_is_never_declared_ready(self):
        self.world()
        self.world('AresHub-damaged', marker=None)
        outside = self.root / 'outside'
        base.make_world(desktop.Paths(str(outside), self.paths.runtime, self.paths.share), self.lock)
        real = pathlib.Path(outside, '.local/share/aresos/worlds/AresHub')
        os.symlink(real, self.worlds / 'AresHub-link')
        names = ('AresHub-damaged', 'AresHub-missing', 'AresHub-link', '../AresHub', str(real), '.', '..', '',
                 'AresHub/../AresHub', 'a\0b')
        sup, pid = self.game()
        sup.persisted.hub_seen = False
        with self.logged('ERROR') as logs:
            for name in names:
                with self.subTest(name):
                    self.heartbeat(sup, world=name)
                    self.heartbeat(sup, world=name)
                    self.assertEqual((sup.state, sup.launch.ready, sup.launch.ever_ready, sup.healthy_since),
                                     ('STARTING', False, False, None))
                    self.assertEqual((sup.persisted.latched, sup.persisted.hub_seen, self.runner.views),
                                     (False, False, []))
        self.assertEqual(len(logs.output), len(names))  # each said once, not at every heartbeat
        self.assertIn('the world AresHub-damaged reported ready, but it is damaged (the AresOS desktop marker '
                      '(data/aresos/desktop.dat) is missing); it is not declared ready', logs.output[0])
        # From a ready home straight to one that is not: no longer in a world, and the home stays what a save is
        # about. Back in the home it is ready again.
        self.ready(sup)
        self.assertEqual((sup.state, sup.active_world()), ('IN_WORLD', 'AresHub'))
        with self.logged('ERROR'):
            self.heartbeat(sup, world='AresHub-damaged')
        self.assertEqual((sup.state, sup.launch.ready, sup.active_world(), sup.persisted.latched),
                         ('STARTING', False, 'AresHub', False))
        self.heartbeat(sup)
        self.assertEqual((sup.state, sup.launch.ready), ('IN_WORLD', True))

    def test_the_home_is_checked_again_when_it_becomes_the_ready_world_after_another(self):
        home = self.world()
        self.world(self.OLD)
        sup, pid = self.game()
        self.ready(sup, self.OLD)
        self.assertEqual((sup.state, sup.active_world()), ('IN_WORLD', self.OLD))
        with mock.patch.object(desktop, 'check_world', wraps=desktop.check_world) as checks:
            for _ in range(5):
                self.heartbeat(sup, world=self.OLD)
        self.assertEqual(checks.call_count, 0)  # checked when it became the ready world, not at every heartbeat
        (home / 'data/aresos/nether_home.dat').write_bytes(b'cut off')
        self.heartbeat(sup)  # straight from the dated home to the home, with no "not ready" in between
        self.assertEqual((sup.state, sup.reason, sup.persisted.latched, sup.launch.ready),
                         ('RECOVERY', 'world_damaged', True, False))


class LeftoversTest(HomeBase):
    """4.5: `AresHub-new-<date>` leftovers are counted and listed, never deleted."""

    def test_leftovers_are_logged_once_at_start_listed_by_status_and_never_touched(self):
        older, newer = 'AresHub-new-2026-11-18_08-00-00-000', 'AresHub-new-2026-11-19_08-00-00-000-1'
        self.world()
        half = self.world(older, provisioned=None)
        self.world(newer)  # may be the home he just made
        (half / 'region').mkdir()
        (half / 'region/r.0.0.mca').write_bytes(b'x' * 300_000)
        os.symlink(self.root / 'share', half / 'link')  # never followed
        before = self.listing()
        with self.logged('INFO') as logs:
            sup = self.next_session()
        lines = [line for line in logs.output if 'never became the home' in line]
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].endswith(f'2 new homes that never became the home are in the worlds folder '
                                          f'(0.3 MB: {newer}, {older}); AresOS never deletes them'), lines[0])
        self.assertEqual(sup.status()['leftovers'], [newer, older])
        self.assertEqual(sup.state, 'STARTING')  # the home opens as ever
        pid, _ = self.run_game(sup)
        self.ready(sup)
        self.stop(sup, 'shutdown')
        sup.tick()
        self.end_game(sup, pid, 143)
        sup = self.next_session()
        sup.retry()
        self.assertEqual(self.listing(), before)
        self.assertEqual(desktop.folder_size(str(half), limit=0), (0, False))  # past the limit: "at least"
        self.assertEqual(desktop.folder_size(str(self.worlds / 'none')), (0, False))

    def test_one_leftover_and_none(self):
        self.world()
        with self.logged('INFO') as logs:
            sup = self.next_session()
        self.assertEqual([line for line in logs.output if 'never became the home' in line], [])
        self.assertEqual(sup.status()['leftovers'], [])
        self.world(self.NEW)
        with self.logged('INFO') as logs:
            sup = self.next_session()
        self.assertEqual(len([line for line in logs.output if '1 new home that never became the home is in the '
                              'worlds folder (0.0 MB: ' + self.NEW in line]), 1)


class GuardTest(SessionBase):
    """3.1: the shutdown guard. Armed first; the unit and its order; the guard's command and its fallback record."""

    UNITS = base.CONFIG / 'usr/lib/systemd/system'

    def held_lock(self):
        """The desktop lock, held as a game's wrapper holds it, until the test ends."""
        fd = desktop.take_desktop_lock(self.paths)
        self.assertIsNotNone(fd)
        self.addCleanup(os.close, fd)
        return fd

    def command(self, answers, **numbers):
        """The guard's command with the supervisor's answers in turn (a dict, or an error to raise; the last one
        repeats): (exit code, stdout, stderr, how often it asked, the fallback record or None)."""
        asked = []

        def request(paths, message, timeout=None):
            self.assertEqual(message, {'op': 'stop', 'reason': 'shutdown'})
            asked.append(timeout)
            answer = answers[min(len(asked), len(answers)) - 1]
            if isinstance(answer, Exception):
                raise answer
            return answer
        out, err = io.StringIO(), io.StringIO()
        patches = [mock.patch.object(desktop, 'request', request),
                   *(mock.patch.object(desktop, name, value) for name, value in numbers.items())]
        with contextlib.ExitStack() as stack, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            for patch in patches:
                stack.enter_context(patch)
            code = desktop.guard_command(self.paths)
        try:
            record = json.loads(pathlib.Path(self.paths.guard_file).read_text())
        except FileNotFoundError:
            record = None
        return code, out.getvalue(), err.getvalue(), asked, record

    # -- armed first

    def test_no_game_is_started_or_authorized_unless_the_guard_is_active(self):
        self.runner.guard = (False, 'inactive')
        sup = self.supervisor()
        sup.start()
        self.assertEqual((sup.state, sup.reason, sup.detail), ('RECOVERY', 'guard', 'inactive'))
        self.assertEqual((self.runner.prisms, sup.persisted.latched), ([], False))
        self.assertIn('aresos-guardian.service: inactive', self.runner.views[-1])
        self.assertIn('Type  retry  and press Enter to try again.', self.runner.views[-1])
        # A game started from Prism by hand passes the same gate.
        ok, reply = sup.on_jvm_start(self.jvm_request())
        self.assertEqual((ok, sup.reason), (False, 'guard'))
        self.assertIn('Minecraft is not', reply['message'])
        # The window is no latch, and a heartbeat or the start timeout must not close it (2.9).
        self.assertIn('guard', desktop.STICKY)
        self.assertTrue(sup.held())
        self.advance(desktop.START_TIMEOUT + 1)
        sup.tick()
        self.assertEqual((sup.state, sup.reason), ('RECOVERY', 'guard'))
        # `retry` asks again: still not active, then active.
        self.runner.guard = (False, 'failed')
        self.assertTrue(sup.retry()[0])
        self.assertEqual((sup.reason, sup.detail, self.runner.prisms), ('guard', 'failed', []))
        self.runner.guard = (True, 'active')
        self.assertTrue(sup.retry()[0])
        self.assertEqual((sup.state, len(self.runner.prisms)), ('STARTING', 1))
        pid, _ = self.run_game(sup)
        # A guard that goes away later stops nothing that runs; only the next start is refused.
        self.runner.guard = (False, 'inactive')
        sup.tick()
        self.assertEqual((sup.state, sup.launch.jvm_pid), ('STARTING', pid))
        self.assertEqual(self.runner.signals, [])

    def test_systemd_s_word_decides_and_only_active_counts(self):
        runner = desktop.Runner(self.paths, None)
        script = self.root / 'systemctl'
        for text, expected in (('echo active', (True, 'active')), ('echo inactive; exit 3', (False, 'inactive')),
                               ('echo failed; exit 3', (False, 'failed')),
                               ('exit 1', (False, 'systemd gave no answer')),
                               ('sleep 5', (False, 'systemd did not answer within 0 s'))):
            script.write_text(f'#!/bin/sh\ntest "$1 $2" = "is-active aresos-guardian.service" || exit 9\n{text}\n')
            script.chmod(0o755)
            with mock.patch.object(desktop, 'SYSTEMCTL', str(script)), \
                    mock.patch.object(desktop, 'GUARD_STATE_WAIT', 0.3 if 'sleep' in text else 2.0):
                self.assertEqual(runner.guard_active(), expected, text)
        # A guard that is just starting is asked again inside the same wait: active then, or still not.
        script.write_text(f'#!/bin/sh\nif test -e {self.root}/asked; then echo active; else : > {self.root}/asked; '
                          'echo activating; fi\n')
        with mock.patch.object(desktop, 'SYSTEMCTL', str(script)):
            self.assertEqual(runner.guard_active(), (True, 'active'))
        script.write_text('#!/bin/sh\necho activating\n')
        with mock.patch.object(desktop, 'SYSTEMCTL', str(script)), mock.patch.object(desktop, 'GUARD_STATE_WAIT', 0.5):
            began = time.monotonic()
            self.assertEqual(runner.guard_active(), (False, 'activating'))
            self.assertLess(time.monotonic() - began, 1.5)
        with mock.patch.object(desktop, 'SYSTEMCTL', str(self.root / 'missing')):
            active, state = runner.guard_active()
        self.assertEqual((active, state.startswith('systemd could not be asked')), (False, True))
        self.assertEqual((desktop.GUARD_UNIT, desktop.GUARD_STATE_WAIT), ('aresos-guardian.service', 2.0))

    # -- the unit

    def test_the_unit_is_ordered_after_everything_that_must_outlive_the_save(self):
        unit = configparser.ConfigParser(interpolation=None, strict=True)
        unit.optionxform = str
        self.assertTrue(unit.read(self.UNITS / 'aresos-guardian.service'))
        self.assertEqual({section: dict(unit[section]) for section in unit.sections()}, {
            'Unit': {'Description': 'AresOS guardian: save the Minecraft home before the system stops',
                     'Documentation': 'file:/usr/libexec/aresos-desktop',
                     'Wants': 'polkit.service',
                     'After': 'greetd.service user@1001.service user-runtime-dir@1001.service polkit.service getty@tty3.service',
                     'RequiresMountsFor': '/var/home/ares'},
            'Service': {'Type': 'oneshot', 'RemainAfterExit': 'yes', 'User': 'ares',
                        'Environment': 'XDG_RUNTIME_DIR=/run/user/1001', 'ExecStart': '/usr/bin/true',
                        'ExecStop': '/usr/libexec/aresos-desktop stop --reason shutdown', 'TimeoutStopSec': '85'},
            'Install': {'WantedBy': 'graphical.target'}})
        # The lead's fix 1: the supervisor's stop, the command's wait for it, one recovery attempt, and room for the
        # fallback record, all inside the unit's limit; the worst case to power-off adds the game scope's limit.
        self.assertEqual((desktop.STOP_BUDGET, desktop.GUARD_REPLY_WAIT, desktop.GUARD_RECOVERY_WAIT), (60.0, 62.0, 10.0))
        limit = float(unit['Service']['TimeoutStopSec'])
        self.assertGreaterEqual(limit - desktop.GUARD_REPLY_WAIT - desktop.GUARD_RECOVERY_WAIT, 10.0)
        self.assertEqual((desktop.GAME_STOP_TIMEOUT, desktop.game_scope('abc')[-2]), ('15s', '--property=TimeoutStopSec=15s'))
        # Every login session is ordered before the guard, beside the memory drop-in, which is unchanged.
        drop_in = [line for line in (self.UNITS / 'session-.scope.d/50-aresos-guardian.conf').read_text().splitlines()
                   if line and not line.startswith('#')]
        self.assertEqual(drop_in, ['[Unit]', 'Before=aresos-guardian.service'])
        self.assertTrue((self.UNITS / 'session-.scope.d/50-aresos-recovery.conf').is_file())
        # Enabled in the image; the supervisor asks about the same unit; the command is the guard's.
        build = (base.CONFIG.parent / 'build.sh').read_text()
        self.assertIn('\nsystemctl enable aresos-guardian.service\n', build)
        self.assertEqual(unit['Service']['ExecStop'].split()[0], desktop.SELF)
        with mock.patch.object(desktop, 'guard_command', lambda paths: 41), \
                mock.patch.object(desktop, 'stop_command', lambda paths, word, reason=None: 42), \
                mock.patch.dict(os.environ, {'HOME': self.paths.home, 'XDG_RUNTIME_DIR': self.paths.runtime}):
            self.assertEqual(desktop.main(unit['Service']['ExecStop'].split()[1:]), 41)
            self.assertEqual([desktop.main(words) for words in (['stop'], ['stop', '--reason', 'manual'],
                                                                 ['restart'], ['logout'])], [42] * 4)

    # -- the guard's command

    def test_the_command_passes_the_supervisors_answer_on(self):
        done = {'ok': True, 'result': 'confirmed', 'recorded': True, 'message': 'Stopped: the home was saved first; '
                                                                              'Minecraft closed.'}
        self.assertEqual(self.command([done]), (0, done['message'] + '\n', '', [desktop.GUARD_REPLY_WAIT], None))
        unsaved = {'ok': False, 'result': 'unsaved', 'recorded': True, 'message': 'Not a confirmed stop: …'}
        self.held_lock()  # an overrun: the game is still there, and the supervisor's own record says so
        self.assertEqual(self.command([unsaved]), (1, '', unsaved['message'] + '\n', [62.0], None))

    def test_no_session_and_no_game_are_positive_evidence_and_end_at_once(self):
        gone = desktop.Paths(self.paths.home, str(self.root / 'no-runtime'), self.paths.share)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(desktop.guard_command(gone), 0)  # it never asks: there is no socket to ask
        self.assertEqual(out.getvalue(), 'Nothing to stop: no AresOS session is running.\n')
        # No supervisor answers and nobody holds the lock: no game runs. No ten seconds of waiting at a shutdown.
        code, out, err, asked, record = self.command([ConnectionRefusedError('refused')])
        self.assertEqual((code, err, asked, record), (0, '', [62.0], None))
        self.assertIn('did not answer (refused), and no Minecraft holds the desktop lock', out)
        self.assertEqual(desktop.desktop_lock_state(self.paths), 'free')  # the guard let go of the lock again

    def test_no_answer_while_a_game_may_be_writing_is_one_recovery_attempt_and_then_the_fallback_record(self):
        pathlib.Path(self.paths.run_dir).mkdir(parents=True, exist_ok=True)
        pathlib.Path(self.paths.runtime_file).write_text(json.dumps({'launch': 'abc123', 'nonce': 'never-copied'}))
        self.held_lock()
        began = time.monotonic()
        code, out, err, asked, record = self.command([TimeoutError('no reply within 62 s'), FileNotFoundError(2, 'gone')],
                                                     GUARD_RECOVERY_WAIT=0.5, GUARD_ASK_AGAIN=0.2)
        self.assertLess(time.monotonic() - began, 3)
        self.assertEqual((code, out, asked[0]), (1, '', 62.0))
        self.assertTrue(3 <= len(asked) <= 5 and all(0 < wait <= 0.5 for wait in asked[1:]), asked)
        self.assertIn('did not answer', err)
        self.assertIn('Minecraft is still running. The next start of AresOS says so.', err)
        self.assertEqual({key: record[key] for key in ('schema', 'why', 'lock', 'save', 'launch')},
                         {'schema': 1, 'why': 'no_answer', 'lock': 'held', 'save': None, 'launch': 'abc123'})
        self.assertEqual(sorted(record), ['launch', 'lock', 'save', 'schema', 'why', 'written'])  # never the nonce
        self.assertEqual(os.stat(self.paths.guard_file).st_mode & 0o777, 0o600)
        # A new supervisor that answers inside the recovery attempt: its answer counts, and no record is written.
        os.unlink(self.paths.guard_file)
        done = {'ok': True, 'result': 'confirmed', 'recorded': True, 'message': 'Stopped.'}
        code, out, err, asked, record = self.command([ConnectionRefusedError('refused'), ConnectionRefusedError('refused'),
                                                      done], GUARD_RECOVERY_WAIT=2.0, GUARD_ASK_AGAIN=0.1)
        self.assertEqual((code, out, err, len(asked), record), (0, 'Stopped.\n', '', 3, None))

    def test_a_lock_nobody_can_read_is_unknown_and_never_free(self):
        pathlib.Path(self.paths.run_dir).mkdir(parents=True, exist_ok=True)
        os.mkdir(self.paths.jvm_lock)  # the lock cannot be opened: nobody can tell
        self.assertTrue(desktop.desktop_lock_state(self.paths).startswith('unknown: '))
        code, out, err, asked, record = self.command([ConnectionRefusedError('refused')],
                                                     GUARD_RECOVERY_WAIT=0.3, GUARD_ASK_AGAIN=0.1)
        self.assertEqual((code, out, record['why'], record['lock'], record['launch']),
                         (1, '', 'no_answer', 'unknown', None))
        self.assertIn('nobody can tell whether Minecraft is still running', err)

    def test_a_stop_the_supervisor_could_not_record_takes_the_fallback_path(self):
        unsaved = {'ok': False, 'result': 'unsaved', 'save': 'timeout', 'close': 'exited', 'recorded': False,
                   'message': 'Not a confirmed stop: … The stop could not be recorded on the disk.'}
        code, out, err, asked, record = self.command([unsaved])
        self.assertEqual((code, out, len(asked)), (1, '', 1))  # it answered: nothing is asked again
        self.assertEqual((record['why'], record['lock'], record['save']), ('unrecorded', 'free', 'timeout'))
        self.assertTrue(err.startswith(unsaved['message'] + ' The next start of AresOS says so.'))
        os.unlink(self.paths.guard_file)
        # Saved and closed: only the supervisor's record is missing. Exit 1 as its answer says, and nothing to add.
        saved = dict(unsaved, result='confirmed', save='saved')
        self.assertEqual(self.command([saved])[::4], (1, None))
        # Saved, but the game is still there: the record carries the supervisor's word that the home was saved.
        self.held_lock()
        record = self.command([saved])[4]
        self.assertEqual((record['why'], record['lock'], record['save']), ('unrecorded', 'held', 'saved'))
        # A state folder that cannot be written: said, and still exit 1.
        os.unlink(self.paths.guard_file)
        with mock.patch.object(desktop, 'write_durable', mock.Mock(side_effect=OSError(28, 'No space left'))):
            code, out, err, asked, record = self.command([unsaved])
        self.assertEqual((code, record), (1, None))
        self.assertIn('That could not be recorded either', err)

    # -- the next supervisor applies the fallback once

    def fallback(self, **record):
        os.makedirs(self.paths.state_dir, exist_ok=True)
        pathlib.Path(self.paths.guard_file).write_text(json.dumps(dict(schema=1, **record)))

    def test_the_next_start_latches_unsaved_from_the_fallback_record_once(self):
        for record, detail in (
                (dict(why='no_answer', lock='held', launch='abc123', save=None), desktop.GUARD_FALLBACK['held']),
                (dict(why='no_answer', lock='unknown', launch=None, save=None), desktop.GUARD_FALLBACK['unknown']),
                (dict(why='unrecorded', lock='free', launch='abc123', save='timeout'),
                 'The stop could not be recorded on the disk.')):
            with self.subTest(record):
                pathlib.Path(self.paths.state_file).unlink(missing_ok=True)
                self.fallback(**record)
                sup = self.next_session()
                self.assertEqual((sup.state, sup.reason, sup.detail), ('RECOVERY', 'unsaved', detail))
                self.assertEqual((self.stored()['latched'], self.stored()['reason']), (True, 'unsaved'))
                self.assertIn(detail, self.runner.views[-1])
                self.assertEqual((self.runner.prisms, os.path.exists(self.paths.guard_file)), ([], False))
                # Once: `retry` clears the latch, and the next start says nothing more.
                self.assertTrue(sup.retry()[0])
                self.assertEqual(len(self.runner.prisms), 1)
                again = self.next_session()
                self.assertEqual((again.persisted.latched, again.state), (False, 'STARTING'))
        # A record that cannot be read was still written by a guard that had no answer.
        pathlib.Path(self.paths.state_file).unlink(missing_ok=True)
        os.makedirs(self.paths.state_dir, exist_ok=True)
        pathlib.Path(self.paths.guard_file).write_text('{"schema": 1, "why"')
        sup = self.next_session()
        self.assertEqual((sup.reason, sup.detail, os.path.exists(self.paths.guard_file)),
                         ('unsaved', desktop.GUARD_FALLBACK['unknown'], False))

    def next_session(self):
        self.runner = StopRunner()
        for path in (self.paths.runtime_file, self.paths.stop_block):
            pathlib.Path(path).unlink(missing_ok=True)
        sup = self.supervisor()
        sup.start()
        return sup

    def test_the_supervisors_own_word_that_the_home_was_saved_stands(self):
        # Its own stop record of that launch says saved: the guard merely got no answer in time.
        sup, pid, peer = self.session()
        replies = []
        sup.request_stop('shutdown', replies.append)
        self.close_game(sup, pid, peer)
        self.assertEqual((replies[0]['result'], self.stored()['stop']['save']), ('confirmed', 'saved'))
        self.fallback(why='no_answer', lock='held', launch=self.stored()['stop']['launch'], save=None)
        sup = self.next_session()
        self.assertEqual((sup.persisted.latched, os.path.exists(self.paths.guard_file)), (False, False))
        # Another launch's record does not speak for this one.
        self.fallback(why='no_answer', lock='held', launch='another', save=None)
        self.assertEqual(self.next_session().reason, 'unsaved')
        # The answer the guard passed on (the supervisor could not write its own record).
        pathlib.Path(self.paths.state_file).unlink()
        self.fallback(why='unrecorded', lock='held', launch='abc123', save='saved')
        sup = self.next_session()
        self.assertEqual((sup.persisted.latched, os.path.exists(self.paths.guard_file)), (False, False))

    def test_a_supervisor_that_adopts_the_game_leaves_the_record_for_the_start_that_finds_none(self):
        sup, pid, peer = self.session()
        self.fallback(why='no_answer', lock='held', launch=sup.launch.id, save=None)
        runner, self.runner = self.runner, StopRunner()
        self.runner.processes = dict(runner.processes)
        replacement = self.supervisor()
        replacement.start()
        self.assertTrue(replacement.launch.adopted)
        self.assertEqual((replacement.persisted.latched, os.path.exists(self.paths.guard_file)), (False, True))
        self.assertEqual(self.next_session().reason, 'unsaved')

    # -- linux-aresos's read checklist, 1: the black screen never outlives its stop

    def test_a_save_that_hangs_takes_the_black_screen_away_when_the_stop_is_called_off(self):
        for kind, window in (('restart', 'save_failed_restart'), ('logout', 'save_failed_logout')):
            with self.subTest(kind):
                sup, pid, peer = self.session()
                replies = []
                sup.request_stop(kind, replies.append)
                self.assertEqual((self.runner.black_up, self.runner.lid_up, replies), (True, True, []))
                self.advance(desktop.STOP_SAVE_WAIT - 1)
                sup.tick()
                self.assertEqual((self.runner.black_up, replies), (True, []))  # the game never answers
                self.advance(1)
                sup.tick()
                self.assertEqual((replies[0]['result'], sup.state, sup.reason), ('called_off', 'RECOVERY', window))
                self.assertEqual((self.runner.black_up, sup.black, self.runner.lid_up, self.runner.behind_black[-1]),
                                 (False, False, False, False))
                self.assertEqual((self.runner.signals, sup.launch.jvm_pid), ([], pid))  # the game keeps running
                # The black screen's own limit is past every stop: it can never stay when a supervisor dies.
                self.assertEqual(self.runner.blacks, [desktop.STOP_BUDGET + desktop.BLACK_EXTRA])


class CommandTest(unittest.TestCase):
    def test_use_home_takes_one_folder_and_no_other_command_takes_one(self):
        for words in (['use-home'], ['status', 'AresHub-2026-11-19_10-00-00-000'], ['use-home', 'a', 'b']):
            with self.subTest(words), self.assertRaises(SystemExit) as stopped:
                with contextlib.redirect_stderr(io.StringIO()):
                    desktop.main(words)
            self.assertEqual(stopped.exception.code, 2)
        source = (base.CONFIG / 'usr/libexec/aresos-desktop').read_text(encoding='utf-8')
        self.assertIn("request(paths, {'op': 'use_home', 'folder': folder.rstrip('/')})", source)

    def test_one_deadline_covers_connecting_and_waiting(self):
        self.assertEqual((desktop.SAVE_WAIT, desktop.COMMAND_WAIT), (60.0, 70.0))
        source = (base.CONFIG / 'usr/libexec/aresos-desktop').read_text(encoding='utf-8')
        self.assertIn("request(paths, {'op': 'save', 'reason': reason}, timeout=COMMAND_WAIT)", source)
        self.assertNotIn('settimeout(2)', source)  # no reply waits for its peer any more


if __name__ == '__main__':
    unittest.main()
