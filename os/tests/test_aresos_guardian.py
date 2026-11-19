"""Package 25, the guardian: the supervisor's state machine with FakeRunner (brief sections 1, 2 and 4).

Step 1 covers section 1: the lifecycle channel's gate, the hello, what counts as saved, one request in flight and
one waiting, and each caller's own deadline. Nothing here starts a process.
"""
import json
import os
import pathlib
import re
import unittest

import test_aresos_desktop as base

desktop, wrapper = base.desktop, base.wrapper
ROOT = base.ROOT
GATE = 'ARESOS_DESKTOP_LIFECYCLE'
DATED = 'AresHub-2026-11-19'


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
        desktop.provision(self.paths, self.lock)
        base.make_world(self.paths, self.lock)

    def game(self):
        """A supervisor whose hub launch runs a game: (supervisor, the game's PID). Each call starts from a session
        with nothing running, so one test can go through several cases."""
        self.runner = base.FakeRunner()
        pathlib.Path(self.paths.runtime_file).unlink(missing_ok=True)
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


class CommandTest(unittest.TestCase):
    def test_one_deadline_covers_connecting_and_waiting(self):
        self.assertEqual((desktop.SAVE_WAIT, desktop.COMMAND_WAIT), (60.0, 70.0))
        source = (base.CONFIG / 'usr/libexec/aresos-desktop').read_text(encoding='utf-8')
        self.assertIn("request(paths, {'op': 'save', 'reason': reason}, timeout=COMMAND_WAIT)", source)
        self.assertNotIn('settimeout(2)', source)  # no reply waits for its peer any more


if __name__ == '__main__':
    unittest.main()
