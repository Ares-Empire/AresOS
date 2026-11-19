"""Package 25, the guardian: the supervisor's state machine with FakeRunner (brief sections 1, 2 and 4).

Step 1 covers section 1: the lifecycle channel's gate, the hello, what counts as saved, one request in flight and
one waiting, and each caller's own deadline. Step 2 covers section 2, the one stop routine, driven as the socket op
`stop` drives it. Step 3 covers 3.2 and 3.3: the session ending under the supervisor (a signal, labwc), `restart`
and `logout`. Nothing here starts a process.
"""
import itertools
import json
import os
import pathlib
import re
import shutil
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


class SessionTest(StopBase):
    """3.2 and 3.3: the session ends under the supervisor (a signal, labwc's end), `logout` and `restart`."""

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


class CommandTest(unittest.TestCase):
    def test_one_deadline_covers_connecting_and_waiting(self):
        self.assertEqual((desktop.SAVE_WAIT, desktop.COMMAND_WAIT), (60.0, 70.0))
        source = (base.CONFIG / 'usr/libexec/aresos-desktop').read_text(encoding='utf-8')
        self.assertIn("request(paths, {'op': 'save', 'reason': reason}, timeout=COMMAND_WAIT)", source)
        self.assertNotIn('settimeout(2)', source)  # no reply waits for its peer any more


if __name__ == '__main__':
    unittest.main()
