"""Package 40: the world as the home screen.

Step 1: a launch that does not open leaves a line in the helper's log. In the owner's try-out an app "did not open"
and neither log said why. The helper logged only launches it started: an unknown app, an app whose program is missing
and a launch that failed after starting were answered to the game and left no line.

Step 2: the world pauses only while a window hides it (owner, 2026-11-15), per screen: a maximized or fullscreen window
on the world's screen covers it, one on the other screen does not. When the world gets the focus while covered, the
windows that cover it are minimized (orchestrator, 2026-11-15). These tests speak the compositor's side over the
wire, with two screens. Everything here is synthetic, as in test_aresos_shell.

Review fixes 1: package 23b's start-up cover never covers the world and is never minimized; a restored desktop that
is activated again soon after it gave the focus back minimizes nothing; uncovering minimizes only windows known to be
on the world's screen.
"""
import json
import socket
import struct
from unittest import mock

from test_aresos_shell import Base, Conn, FakeCompositor, INSTANCE, NONCE, REGISTRY, ALL, shell
from test_aresos_shell_protocol import example


def lines(warning):
    return [call.args[0] % call.args[1:] for call in warning.call_args_list]


class RefusalLogTest(Base):
    def test_an_unknown_and_an_unavailable_app_are_logged(self):
        helper = self.helper()
        conn = self.connect(helper)
        with mock.patch.object(shell.LOG, 'warning') as warning:
            self.request(helper, conn, 'open_app', 'o-1', app_id='spotify')
            self.request(helper, conn, 'open_app', 'o-2', app_id='browser')
            # A resent request is answered from the journal: one line per launch, not per message.
            self.request(helper, conn, 'open_app', 'o-2', app_id='browser')
        self.assertEqual(lines(warning), ['unknown app ID (7 characters) not opened', 'browser not opened: not_installed'])

    def test_an_unknown_id_is_logged_by_length(self):
        helper = self.helper()
        conn = self.connect(helper)
        with mock.patch.object(shell.LOG, 'warning') as warning:
            self.request(helper, conn, 'open_app', 'o-1', app_id='x\n' * 60)
        (line,) = lines(warning)
        self.assertNotIn('\n', line)
        self.assertLess(len(line), 200)
        self.assertEqual(line, 'unknown app ID (120 characters) not opened')

    def test_a_launch_that_shows_no_window_is_logged(self):
        helper = self.helper(tracked=True)
        conn = self.connect(helper)
        self.assertEqual(self.request(helper, conn, 'open_app', 'o-1', app_id='notepad')['state'], 'starting')
        with mock.patch.object(shell.LOG, 'warning') as warning:
            self.now[0] += shell.WINDOW_TIMEOUT + 0.1
            helper.tick()
        self.assertEqual(lines(warning), ['notepad failed after starting: no matching window appeared'])


MAXIMIZED, MINIMIZED, ACTIVATED, FULLSCREEN = 0, 1, 2, 3
DESKTOP, APP, SMALL, OTHER, COVER = 0xff000001, 0xff000002, 0xff000003, 0xff000004, 0xff000005


def message(object_id, opcode, payload=b''):
    return FakeCompositor.message(object_id, opcode, payload)


def word(value):
    return struct.pack('=I', value)


class Screens:
    """The compositor's side of the wire with two screens: the laptop's (LEFT) and an external monitor (RIGHT)."""
    LEFT, RIGHT, MANAGER, SEAT = 20, 21, 7, 8

    def __init__(self, test, windows):
        client_end, self.server_end = socket.socketpair()
        test.addCleanup(client_end.close)
        test.addCleanup(self.server_end.close)
        self.compositor = FakeCompositor(self.server_end)
        self.client = shell.ForeignToplevels(client_end, windows)
        self.compositor.read()  # get_registry
        string = shell.ForeignToplevels.string
        self.client.feed(b''.join(message(self.client.registry, 0, word(name) + string(interface) + word(version))
                                  for name, interface, version in ((self.LEFT, 'wl_output', 4),
                                                                   (self.MANAGER, shell.ForeignToplevels.MANAGER, 3),
                                                                   (self.SEAT, 'wl_seat', 9),
                                                                   (self.RIGHT, 'wl_output', 4))))
        assert self.client.bind()
        self.binds = self.requests()
        self.left, self.right = self.client.outputs[self.LEFT], self.client.outputs[self.RIGHT]

    def requests(self):
        """Everything the helper sent the compositor since the last call."""
        self.server_end.setblocking(False)
        try:
            while True:
                data = self.server_end.recv(65536)
                if not data:
                    break
                self.compositor.buffer += data
        except BlockingIOError:
            pass
        finally:
            self.server_end.setblocking(True)
        sent = []
        while len(self.compositor.buffer) >= 8:
            sent.append(self.compositor.read())
        return sent

    def window(self, handle, app_id, states=(), outputs=()):
        self.client.feed(message(self.client.manager, 0, word(handle)) + message(handle, 1, shell.ForeignToplevels.string(app_id)))
        self.change(handle, states, enter=outputs)

    def change(self, handle, states=None, enter=(), leave=()):
        data = b''.join(message(handle, 2, word(output)) for output in enter)
        data += b''.join(message(handle, 3, word(output)) for output in leave)
        if states is not None:
            data += message(handle, 4, word(4 * len(states)) + b''.join(word(state) for state in states))
        self.client.feed(data + message(handle, 5))

    def close(self, handle):
        self.client.feed(message(handle, 6))

    def unplug(self, name):
        self.client.feed(message(self.client.registry, 1, word(name)))

    def plug(self, name):
        self.client.feed(message(self.client.registry, 0, word(name) + shell.ForeignToplevels.string('wl_output')
                                 + word(4)))


class CoveredTest(Base):
    """The helper tells the game when a window hides the world, per screen, and uncovers it when it gets the focus."""

    def start(self, keep_foreground=False, before=None):
        self.windows = shell.Windows(clock=self.clock)
        self.screens = Screens(self, self.windows)
        if before is not None:
            before()
        helper = shell.Helper(str(REGISTRY), INSTANCE, NONCE, self.journal, launcher=self.launcher(),
                              windows=self.windows, activate=self.screens.client.activate,
                              minimize=self.screens.client.minimize, clock=self.clock,
                              executable=lambda path: True, keep_foreground=keep_foreground)
        self.addCleanup(helper.watcher.stop)
        self.helper_ = helper
        return helper

    def hello(self, minor=1, capabilities=ALL + ['shell_covered']):
        conn = Conn()
        self.helper_.connected(conn)
        reply = self.request(self.helper_, conn, 'hello', 'h-1', major=1, minor=minor, capabilities=capabilities,
                             requires=['list_apps', 'open_app'], instance=INSTANCE, nonce=NONCE)
        self.assertTrue(reply['ok'], reply)
        return conn

    def changed(self):
        self.helper_.windows_changed()

    @staticmethod
    def covered(conn):
        return [event['covered'] for event in conn.events('shell_covered')]

    def minimized(self):
        return [handle for handle, opcode, _ in self.screens.requests() if opcode == 2]

    def test_a_new_desktop_gets_existing_app_focus_after_hello_and_on_reconnect(self):
        self.start()
        self.screens.window(DESKTOP, 'aresos-desktop', [MAXIMIZED], [self.screens.left])
        self.screens.window(APP, 'org.kde.kwrite', [ACTIVATED], [self.screens.left])
        self.changed()  # no desktop connection exists yet
        self.assertEqual(self.helper_.shell, 'background')
        conn = self.hello()
        self.assertEqual(conn.events('shell_focus'), [], 'hello must be answered before the snapshot')
        self.helper_.tick()
        events = conn.events('shell_focus')
        self.assertEqual([(e['focus'], e['reason']) for e in events], [('background', 'app_activated')])
        self.assertEqual(events[0]['app_id'], 'notepad')
        self.helper_.tick()
        self.assertEqual(len(conn.events('shell_focus')), 1, 'unchanged focus must not be repeated')
        again = self.hello()
        self.helper_.tick()
        self.assertEqual([e['focus'] for e in again.events('shell_focus')], ['background'])
        self.assertEqual(len(conn.events('shell_focus')), 1, 'the old connection gets no new snapshot')

    def test_initial_app_focus_respects_capability_and_legacy_negotiation(self):
        self.start()
        self.screens.window(DESKTOP, 'aresos-desktop', [MAXIMIZED], [self.screens.left])
        self.screens.window(OTHER, 'org.test.other', [ACTIVATED], [self.screens.left])
        self.changed()
        quiet = self.hello(capabilities=[c for c in ALL if c != 'shell_focus'])
        self.helper_.tick()
        self.assertEqual(quiet.events('shell_focus'), [])
        legacy = self.hello(minor=0)
        self.helper_.tick()
        self.assertEqual([(e['focus'], e['reason']) for e in legacy.events('shell_focus')],
                         [('background', 'other_window')])

    def test_binds_every_screen_before_the_manager_and_follows_screens_plugged_in_and_out(self):
        self.start()
        binds = [payload for object_id, opcode, payload in self.screens.binds]
        self.assertEqual([interface for payload in binds for interface in (b'wl_output', b'wl_seat',
                                                                             shell.ForeignToplevels.MANAGER.encode())
                          if interface in payload], [b'wl_output', b'wl_output', shell.ForeignToplevels.MANAGER.encode(),
                                                     b'wl_seat'])
        self.screens.window(DESKTOP, 'aresos-desktop', [MAXIMIZED, ACTIVATED], [self.screens.right])
        self.assertEqual(self.windows.toplevels[DESKTOP].outputs, {self.screens.right})
        self.screens.unplug(Screens.RIGHT)
        self.assertEqual(self.windows.toplevels[DESKTOP].outputs, frozenset())
        self.screens.plug(30)
        (bind,) = self.screens.requests()
        self.assertIn(b'wl_output', bind[2])
        self.assertIn(30, self.screens.client.outputs)
        self.assertFalse(self.screens.client.minimize(12345))

    def test_only_a_maximized_or_fullscreen_window_that_is_not_minimized_covers_the_world(self):
        self.start()
        conn = self.hello()
        left = [self.screens.left]
        self.screens.window(DESKTOP, 'aresos-desktop', [MAXIMIZED], left)
        self.screens.window(APP, 'org.kde.kwrite', [ACTIVATED], left)
        self.changed()
        self.helper_.tick()
        self.assertEqual(self.covered(conn), [], 'a small window in front must leave the world running')
        for states in ([MAXIMIZED, ACTIVATED], [MAXIMIZED, MINIMIZED], [MAXIMIZED, ACTIVATED], [ACTIVATED],
                       [FULLSCREEN, ACTIVATED]):
            self.screens.change(APP, states)
            self.changed()
        self.screens.close(APP)
        self.changed()
        self.assertEqual(self.covered(conn), [True, False, True, False, True, False])
        first = conn.events('shell_covered')[0]
        self.assertEqual(first, dict(example('shell-covered-event'), id=first['id']))

    def test_a_window_on_the_other_screen_never_covers_the_world(self):
        self.start()
        conn = self.hello()
        screens = self.screens
        # The owner's set-up (2026-11-15): the world on the external monitor, apps on either screen.
        screens.window(DESKTOP, 'aresos-desktop', [MAXIMIZED], [screens.right])
        screens.window(APP, 'org.kde.kwrite', [MAXIMIZED, ACTIVATED], [screens.left])
        self.changed()
        self.assertEqual(self.covered(conn), [])
        screens.change(APP, leave=[screens.left], enter=[screens.right])  # moved to the world's screen
        self.changed()
        screens.change(APP, enter=[screens.left])  # across both: still over the world
        self.changed()
        screens.change(APP, leave=[screens.right])
        self.changed()
        self.assertEqual(self.covered(conn), [True, False])
        # The monitor is unplugged: until the compositor says where the world went, it counts as on every screen.
        screens.unplug(Screens.RIGHT)
        self.changed()
        screens.change(DESKTOP, enter=[screens.left])
        self.changed()
        self.assertEqual(self.covered(conn), [True, False, True])

    def test_covered_is_told_after_hello_only_to_a_one_one_desktop_that_offered_it(self):
        self.start()
        quiet = self.hello(capabilities=ALL)
        self.screens.window(DESKTOP, 'aresos-desktop', [MAXIMIZED], [self.screens.left])
        self.screens.window(APP, 'org.kde.kwrite', [MAXIMIZED, ACTIVATED], [self.screens.left])
        self.changed()
        self.assertEqual(quiet.events('shell_covered'), [])
        old = self.hello(minor=0)
        self.assertNotIn('shell_covered', old.sent[0]['capabilities'])
        self.helper_.tick()
        self.assertEqual(old.events('shell_covered'), [])
        conn = self.hello()
        self.assertIn('shell_covered', conn.sent[0]['capabilities'])
        self.assertEqual(self.covered(conn), [], 'nothing may come before the hello reply is read')
        self.helper_.tick()
        self.assertEqual(self.covered(conn), [True])
        again = self.hello()  # the game reconnects: it starts uncovered, so it is told again
        self.helper_.tick()
        self.assertEqual(self.covered(again), [True])
        self.screens.change(APP, [MAXIMIZED, MINIMIZED])
        self.changed()
        fresh = self.hello()
        self.helper_.tick()
        self.assertEqual((self.covered(again), self.covered(fresh)), ([True, False], []))

    def test_the_world_getting_the_focus_minimizes_only_what_covers_it_on_its_screen(self):
        self.start()
        conn = self.hello()
        screens = self.screens
        screens.window(DESKTOP, 'aresos-desktop', [MAXIMIZED], [screens.right])
        screens.window(OTHER, 'org.test.other', [MAXIMIZED], [screens.left])
        screens.window(SMALL, 'aresos.terminal', [], [screens.right])
        screens.window(APP, 'org.kde.kwrite', [MAXIMIZED, ACTIVATED], [screens.right])
        self.changed()
        self.assertEqual((self.covered(conn), self.minimized()), ([True], []))
        # Alt+Tab to the world while the maximized app hides it.
        screens.change(APP, [MAXIMIZED])
        screens.change(DESKTOP, [MAXIMIZED, ACTIVATED])
        self.changed()
        self.assertEqual(self.minimized(), [APP])
        screens.change(APP, [MAXIMIZED, MINIMIZED])
        self.changed()
        self.assertEqual(self.covered(conn), [True, False])
        # Back to the app: the compositor brings it back, the world is covered again and nothing is minimized.
        screens.change(DESKTOP, [MAXIMIZED])
        screens.change(APP, [MAXIMIZED, ACTIVATED])
        self.changed()
        self.assertEqual((self.covered(conn), self.minimized()), ([True, False, True], []))
        # A maximized Terminal opened over the app and closed again returns to the world (step 1's rule); the app
        # behind it is minimized once the world has the focus, so the world shows.
        screens.close(OTHER)
        screens.close(SMALL)
        self.request(self.helper_, conn, 'open_app', 'o-1', app_id='terminal')
        terminal = APP + 10
        screens.window(terminal, 'aresos.terminal', [MAXIMIZED, ACTIVATED], [screens.right])
        screens.change(APP, [MAXIMIZED])
        self.changed()
        screens.close(terminal)
        self.changed()
        self.assertEqual([(h, op) for h, op, _ in screens.requests() if op != 7], [(DESKTOP, 4)])
        screens.change(DESKTOP, [MAXIMIZED, ACTIVATED])
        self.changed()
        self.assertEqual(self.minimized(), [APP])
        screens.change(APP, [MAXIMIZED, MINIMIZED])
        self.changed()
        self.assertEqual(self.covered(conn), [True, False, True, False])

    def test_a_restored_desktop_stays_below_the_window_in_front_and_minimizes_nothing(self):
        self.start(keep_foreground=True)
        conn = self.hello()
        screens = self.screens
        screens.window(APP, 'org.kde.kwrite', [MAXIMIZED, ACTIVATED], [screens.left])
        self.changed()
        # The supervisor restarted the game: its new window takes the focus as it appears.
        screens.change(APP, [MAXIMIZED])
        screens.window(DESKTOP, 'aresos-desktop', [MAXIMIZED, ACTIVATED], [screens.left])
        self.changed()
        self.assertEqual([(h, op) for h, op, _ in screens.requests()], [(APP, 4)])
        self.assertEqual(self.covered(conn), [True])

    def test_a_helper_starting_under_a_covered_world_minimizes_nothing(self):
        def before():
            self.screens.window(DESKTOP, 'aresos-desktop', [MAXIMIZED, ACTIVATED], [self.screens.left])
            self.screens.window(APP, 'org.kde.kwrite', [MAXIMIZED], [self.screens.left])
        self.start(before=before)
        conn = self.hello()
        self.helper_.tick()
        self.assertEqual((self.covered(conn), self.minimized()), ([True], []))

    def test_the_start_up_cover_never_covers_the_world_and_is_never_minimized(self):
        self.start()
        conn = self.hello()
        screens = self.screens
        # Package 23b: the cover is up, fullscreen and on top, while the game starts. The game's window maps under
        # it and labwc activates it with the cover as the window before.
        screens.window(COVER, 'aresos.cover', [FULLSCREEN, ACTIVATED], [screens.left])
        self.changed()
        screens.change(COVER, [FULLSCREEN])
        screens.window(DESKTOP, 'aresos-desktop', [MAXIMIZED, ACTIVATED], [screens.left])
        self.changed()
        # The cover comes to the front again and the world gets the focus once more: still nothing.
        screens.change(DESKTOP, [MAXIMIZED])
        screens.change(COVER, [FULLSCREEN, ACTIVATED])
        self.changed()
        screens.change(COVER, [FULLSCREEN])
        screens.change(DESKTOP, [MAXIMIZED, ACTIVATED])
        self.changed()
        self.helper_.tick()
        self.assertEqual((self.covered(conn), self.minimized()), ([], []))

    def test_a_restored_desktop_activated_again_right_after_the_hand_back_minimizes_nothing(self):
        self.start(keep_foreground=True)
        conn = self.hello()
        screens = self.screens
        screens.window(APP, 'org.kde.kwrite', [MAXIMIZED, ACTIVATED], [screens.left])
        self.changed()
        # The supervisor restarted the game: its new window takes the focus as it appears and gives it back.
        screens.change(APP, [MAXIMIZED])
        screens.window(DESKTOP, 'aresos-desktop', [MAXIMIZED, ACTIVATED], [screens.left])
        self.changed()
        self.assertEqual([(h, op) for h, op, _ in screens.requests()], [(APP, 4)])
        screens.change(DESKTOP, [MAXIMIZED])
        screens.change(APP, [MAXIMIZED, ACTIVATED])
        self.changed()
        # Half a second later the game's window is activated again (GLFW's focus-on-show request, review 1,
        # finding 2): the app he works in stays.
        self.now[0] += 0.5
        screens.change(APP, [MAXIMIZED])
        screens.change(DESKTOP, [MAXIMIZED, ACTIVATED])
        self.changed()
        self.assertEqual(self.minimized(), [])
        self.assertEqual(self.covered(conn), [True])
        # Later he goes to the app and back to the world himself: the world is uncovered as usual.
        screens.change(DESKTOP, [MAXIMIZED])
        screens.change(APP, [MAXIMIZED, ACTIVATED])
        self.changed()
        self.now[0] += shell.KEEP_WINDOW
        screens.change(APP, [MAXIMIZED])
        screens.change(DESKTOP, [MAXIMIZED, ACTIVATED])
        self.changed()
        self.assertEqual(self.minimized(), [APP])

    def test_uncovering_minimizes_only_windows_known_to_be_on_the_worlds_screen(self):
        self.start()
        conn = self.hello()
        screens = self.screens
        screens.window(DESKTOP, 'aresos-desktop', [MAXIMIZED], [screens.right])
        # labwc has not said yet which screen this window is on: it covers the world for the pause
        # (JUDGMENT-CALL 7)...
        screens.window(APP, 'org.kde.kwrite', [MAXIMIZED, ACTIVATED])
        self.changed()
        self.assertEqual(self.covered(conn), [True])
        # ...but the world getting the focus does not minimize it: it may be on the other screen (review 1,
        # finding 4).
        screens.change(APP, [MAXIMIZED])
        screens.change(DESKTOP, [MAXIMIZED, ACTIVATED])
        self.changed()
        self.assertEqual(self.minimized(), [])
        # Once labwc names the world's screen for it, the next activation of the world minimizes it.
        screens.change(DESKTOP, [MAXIMIZED])
        screens.change(APP, [MAXIMIZED, ACTIVATED], enter=[screens.right])
        self.changed()
        screens.change(APP, [MAXIMIZED])
        screens.change(DESKTOP, [MAXIMIZED, ACTIVATED])
        self.changed()
        self.assertEqual(self.minimized(), [APP])
        screens.change(APP, [MAXIMIZED, MINIMIZED])
        self.changed()
        self.assertEqual(self.covered(conn), [True, False])
        # A world whose screen is not known (its monitor was just unplugged) minimizes nothing either.
        screens.unplug(Screens.RIGHT)
        screens.change(DESKTOP, [MAXIMIZED])
        screens.change(APP, [MAXIMIZED, ACTIVATED], enter=[screens.left])
        self.changed()
        screens.change(APP, [MAXIMIZED])
        screens.change(DESKTOP, [MAXIMIZED, ACTIVATED])
        self.changed()
        self.assertEqual(self.minimized(), [])
        self.assertEqual(self.covered(conn), [True, False, True])
