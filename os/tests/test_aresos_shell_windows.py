"""Package 30 A5: discovered windows and handovers; all processes and compositor traffic are synthetic."""
import itertools
import json
import os
import pathlib
import socket

from test_aresos_shell import (shell, Base, REGISTRY, INSTANCE, NONCE, FakeCompositor,
                               wire_toplevel, wire_state, entry)
from test_aresos_shell_discovery import DiscoveryBase


class IdentityTest(DiscoveryBase):
    def test_candidates_keep_the_required_order_and_remove_repeats(self):
        self.write('org.test.App.desktop', Exec='/usr/bin/tool', StartupWMClass='startup', **{'X-Flatpak': 'flatpak.id'})
        app = self.catalogue()[0]['org-test-app']
        self.assertEqual(app.app_ids, ('startup', 'org.test.App', 'flatpak.id', 'tool'))
        self.assertIsNone(app.instance)  # discovered apps declare neither single nor multi
        self.write('org.test.App.desktop', StartupWMClass='org.test.App')
        self.assertEqual(self.catalogue()[0]['org-test-app'].app_ids, ('org.test.App', 'tool'))

    def test_each_candidate_can_identify_a_window(self):
        self.write('org.test.App.desktop', StartupWMClass='startup', **{'X-Flatpak': 'flatpak.id'})
        apps, _ = self.catalogue()
        windows = shell.Windows()
        windows.set_registry(apps)
        for handle, identity in enumerate(('startup', 'org.test.App', 'flatpak.id', 'tool'), 1):
            windows.new(handle)
            windows.app_id(handle, identity)
            windows.done(handle)
            self.assertEqual(windows.toplevels[handle].owner, 'org-test-app')

    def test_earlier_program_keeps_shared_identities_without_disabling_either(self):
        self.write('first.desktop', folder=0, StartupWMClass='shared')
        self.write('second.desktop', folder=1, StartupWMClass='shared')
        apps, _ = self.catalogue()
        self.assertEqual(apps['first'].app_ids, ('shared', 'first', 'tool'))
        self.assertEqual(apps['second'].app_ids, ('second',))
        self.assertTrue(all(shell.resolve(app, self.executables.__contains__)[2] is None for app in apps.values()))

    def test_all_identities_may_be_lost_without_making_a_program_unavailable(self):
        self.write('tool.desktop', folder=0, StartupWMClass='tool')
        # The reviewed entry reserves the later app's own ID; discovery reserves its other candidates.
        self.write('later.desktop', folder=1, StartupWMClass='tool')
        (self.registry / 'reviewed.json').write_text(json.dumps(
            entry('reviewed', window={'app_ids': ['later'], 'instance': 'multi'})))
        apps, _ = self.catalogue()
        self.assertEqual(apps['later'].app_ids, ())
        self.assertIsNone(shell.resolve(apps['later'], self.executables.__contains__)[2])

    def test_reviewed_and_desktop_identities_always_win_including_unavailable_entries(self):
        for identity in ('aresos.terminal', 'google-chrome', 'org.kde.kwrite', 'aresos-desktop'):
            self.write('clash.desktop', StartupWMClass=identity)
            apps, _ = self.catalogue(REGISTRY)
            self.assertNotIn(identity, apps['clash'].app_ids)
            self.assertTrue(all(app.invalid is None for app in apps.values()))
        for name in ('one', 'two'):
            (self.registry / (name + '.json')).write_text(json.dumps(
                entry(name, window={'app_ids': ['shared'], 'instance': 'multi'})))
        self.write('clash.desktop', StartupWMClass='shared')
        apps, _ = self.catalogue()
        self.assertNotIn('shared', apps['clash'].app_ids)
        self.assertEqual(apps['one'].invalid, 'duplicate_window_identity')
        self.assertEqual(apps['two'].invalid, 'duplicate_window_identity')

    def test_terminal_wrapper_does_not_claim_foot_or_the_programs_normal_identity(self):
        self.write('btop.desktop', Exec='btop', Terminal='true', StartupWMClass='foot')
        apps, _ = self.catalogue(REGISTRY)
        self.assertEqual(apps['btop'].app_ids, ('aresos.app.btop',))
        self.assertEqual(apps['terminal'].app_ids, {'aresos.terminal'})

    def test_identity_changes_change_the_catalogue_revision(self):
        self.write('app.desktop', StartupWMClass='one')
        revision = self.catalogue()[1]
        self.write('app.desktop', StartupWMClass='two')
        self.assertNotEqual(self.catalogue()[1], revision)

    def test_invalid_window_candidates_are_ignored_without_hiding_the_program(self):
        self.write('app.desktop', StartupWMClass='bad identity', **{'X-Flatpak': '../../escape'})
        self.assertEqual(self.catalogue()[0]['app'].app_ids, ('app', 'tool'))


class DiscoveredBase(Base):
    def app(self, app_id='lunarclient', **values):
        fields = dict(Type='Application', Name=app_id.title(), Exec='/usr/bin/' + app_id,
                      StartupWMClass=app_id)
        fields.update(values)
        return shell.discovered_app(app_id + '.desktop', '/test/' + app_id + '.desktop', fields, lambda p: True)

    def start(self, tracked=True, journal=None, windows=None):
        apps, revision = shell.load_registry(REGISTRY)
        apps.update({app_id: self.app(app_id) for app_id in ('lunarclient', 'discord')})
        apps['btop'] = self.app('btop', Terminal='true')
        self.windows = (windows or shell.Windows(clock=self.clock)) if tracked else None
        self.helper_ = shell.Helper(str(REGISTRY), INSTANCE, NONCE, journal or self.journal,
                                    registry=(apps, revision), launcher=self.launcher(), windows=self.windows,
                                    activate=self.activate if tracked else None, clock=self.clock,
                                    executable=lambda path: True)
        self.addCleanup(self.helper_.watcher.stop)
        self.conn = self.connect(self.helper_)
        return self.helper_

    def window(self, handle, identity, active=False, parent=0):
        self.windows.new(handle)
        self.windows.app_id(handle, identity)
        self.windows.parent(handle, parent)
        self.windows.state(handle, active)
        self.windows.done(handle)
        if active:
            self.focus(handle, apply=False)
        self.helper_.windows_changed()

    def focus(self, handle, apply=True):
        for window in list(self.windows.toplevels.values()):
            self.windows.state(window.handle, window.handle == handle)
            self.windows.done(window.handle)
        if apply:
            self.helper_.windows_changed()

    def open(self, app_id='lunarclient', request_id='o-1'):
        return self.request(self.helper_, self.conn, 'open_app', request_id, app_id=app_id)

    def close(self, handle):
        self.windows.gone(handle)
        self.helper_.windows_changed()

    def expire_close(self):
        self.now[0] += shell.HANDOFF + 0.01
        self.helper_.tick()

    def state(self, request_id='o-1'):
        return self.helper_.journal.entries[request_id]['state']


class DiscoveredLifecycleTest(DiscoveredBase):
    def setUp(self):
        super().setUp()
        self.start()
        self.window(1, 'aresos-desktop', active=True)

    def test_early_clean_exit_waits_for_a_resident_instances_window(self):
        self.open()
        self.helper_.processes['o-1'].code = 0
        self.helper_.tick()
        self.assertEqual(self.state(), 'starting')
        self.scope_pass(self.helper_)  # the short-lived second launch's scope is gone
        self.window(2, 'lunarclient', active=True)
        self.assertEqual(self.state(), 'focused')

    def test_nonzero_early_exit_is_still_a_launch_failure(self):
        self.open()
        self.helper_.processes['o-1'].code = 2
        self.helper_.tick()
        self.assertEqual(self.state(), 'failed')
        self.assertEqual(self.helper_.journal.entries['o-1']['error'], 'launch_failed')

    def test_live_and_unknown_scopes_never_time_out_but_gone_handover_is_bounded(self):
        self.open()
        process = self.helper_.processes['o-1']
        unit = self.helper_.journal.entries['o-1']['unit']
        self.active_units.add(unit)
        for status in ('proxy alive', 'scope alive', 'scope unknown'):
            if status != 'proxy alive':
                process.code = 0
            if status == 'scope unknown':
                self.scope_answer = (1, '')
            self.scope_pass(self.helper_)
            self.now[0] += shell.WINDOW_TIMEOUT + 1
            self.helper_.tick()
            self.assertEqual(self.state(), 'starting', status)
        self.scope_answer = None
        self.active_units.clear()
        self.scope_pass(self.helper_)
        self.now[0] += shell.WINDOW_TIMEOUT + 1
        self.helper_.tick()
        self.assertEqual(self.helper_.journal.entries['o-1']['error'], 'no_window')

    def test_close_means_no_window_even_while_scope_runs_and_second_start_brings_it_back(self):
        self.open('discord')
        process = self.helper_.processes['o-1']
        unit = self.helper_.journal.entries['o-1']['unit']
        self.active_units.add(unit)
        self.window(2, 'discord', active=True)
        self.close(2)
        self.assertEqual(self.activations, [])
        self.expire_close()
        self.assertEqual(self.state(), 'closed')
        self.assertIsNone(process.poll())
        self.assertEqual(self.activations, [1])
        self.assertIn(unit, self.helper_.watched_units())
        self.focus(1)
        second = self.open('discord', 'o-2')
        self.helper_.processes['o-2'].code = 0
        self.helper_.tick()
        self.assertEqual(self.state('o-2'), 'starting')
        self.window(3, 'discord', active=True)
        self.assertEqual(self.state('o-2'), 'focused')
        self.assertNotEqual(second['launch_id'], self.helper_.journal.entries['o-1']['launch_id'])
        self.close(3)
        self.expire_close()
        self.assertEqual(self.state('o-2'), 'closed')
        self.assertEqual(self.activations, [1, 1])

    def test_all_windows_and_dialogs_count_until_the_last_one_closes(self):
        self.open()
        self.window(2, 'lunarclient', active=True)
        self.window(3, 'lunarclient')
        self.window(4, '', active=True, parent=3)
        self.close(2)
        self.close(3)
        self.focus(4)  # the orphan dialog retains its discovered parent even at a later done
        self.assertEqual(self.helper_.handles['o-1'], {4})
        self.assertEqual(self.state(), 'focused')
        self.expire_close()
        self.assertEqual(self.activations, [])
        self.close(4)
        self.expire_close()
        self.assertEqual(self.state(), 'closed')
        self.assertEqual(self.activations, [1])

    def test_background_close_preserves_focus(self):
        self.open()
        self.window(2, 'lunarclient', active=True)
        self.window(3, 'aresos.terminal', active=True)
        self.now[0] += shell.HANDOFF + 1
        self.close(2)
        self.expire_close()
        self.assertEqual(self.state(), 'closed')
        self.assertEqual(self.activations, [])
        self.assertEqual(self.helper_.foreground_app, 'terminal')

    def test_terminal_program_matches_its_private_wrapper(self):
        self.open('btop')
        self.window(2, 'aresos.app.btop', active=True)
        self.assertEqual(self.state(), 'focused')
        self.assertEqual(self.helper_.foreground_app, 'btop')
        self.close(2)
        self.expire_close()
        self.assertEqual(self.activations, [1])

    def test_second_click_can_handover_to_an_already_existing_window(self):
        self.open()
        self.window(2, 'lunarclient', active=True)
        self.now[0] += 1
        self.open(request_id='o-2')
        self.helper_.processes['o-2'].code = 0
        self.helper_.tick()
        self.focus(2)
        self.assertEqual(self.state('o-2'), 'focused')
        self.close(2)
        self.expire_close()
        self.assertEqual([self.state(r) for r in ('o-1', 'o-2')], ['closed', 'closed'])

    def test_clean_handover_without_tracking_settles_instead_of_guessing_a_failure(self):
        helper = self.start(tracked=False, journal=os.path.join(self.folder.name, 'untracked.json'))
        self.open()
        helper.processes['o-1'].code = 0
        helper.tick()
        self.assertEqual(self.state(), 'starting')
        self.assertTrue(helper.journal.entries['o-1']['settled'])


class UnclaimedWindowTest(DiscoveredBase):
    def setUp(self):
        super().setUp()
        self.start()
        self.window(1, 'aresos-desktop', active=True)

    def test_new_unclaimed_windows_belong_to_the_only_live_program_and_keep_their_owner(self):
        self.open()
        self.window(2, 'lunarclient', active=True)
        self.window(3, 'java-lunar', active=True)
        self.assertEqual(self.windows.toplevels[3].owner, 'lunarclient')
        self.close(2)
        self.expire_close()
        self.assertEqual(self.activations, [])
        self.assertEqual(self.state(), 'focused')
        self.open('discord', 'o-2')
        self.focus(3)
        self.assertEqual(self.windows.toplevels[3].owner, 'lunarclient')
        self.close(3)
        self.expire_close()
        self.assertEqual(self.activations, [1])

    def test_multiple_scopes_of_the_same_program_are_one_candidate(self):
        self.open()
        self.open(request_id='o-2')
        self.window(2, 'java-lunar', active=True)
        self.assertEqual(self.windows.toplevels[2].owner, 'lunarclient')
        self.assertEqual(self.state(), 'focused')
        self.assertEqual(self.state('o-2'), 'focused')

    def test_unavailable_reviewed_identity_is_reserved_against_inference(self):
        self.open()
        apps = dict(self.helper_.apps)
        apps['broken'] = shell.App('broken', 'Broken', app_ids=frozenset({'reserved'}), invalid='invalid_entry')
        self.windows.set_registry(apps)
        self.window(2, 'reserved')
        self.assertIsNone(self.windows.toplevels[2].owner)
        self.assertEqual(self.state(), 'starting')

    def test_unclaimed_window_waits_for_an_identity_and_explicit_identities_override_inference(self):
        self.open()
        self.window(2, '', active=True)
        self.assertIsNone(self.windows.toplevels[2].owner)
        self.windows.app_id(2, 'java-lunar')
        self.windows.done(2)
        self.helper_.windows_changed()
        self.assertEqual(self.windows.toplevels[2].owner, 'lunarclient')
        self.windows.app_id(2, 'org.kde.kwrite')
        self.windows.done(2)
        self.helper_.windows_changed()
        self.assertEqual(self.windows.toplevels[2].owner, 'notepad')
        self.assertNotIn('o-1', self.helper_.handles)
        self.expire_close()
        self.assertEqual(self.activations, [])

    def test_a_failed_launch_cannot_infer_an_unrelated_window(self):
        self.open()
        self.helper_.processes['o-1'].code = 2
        self.helper_.tick()
        self.window(2, 'java-other')
        self.assertIsNone(self.windows.toplevels[2].owner)
        self.open('discord', 'o-2')
        self.window(3, 'another-other')
        self.assertIsNone(self.windows.toplevels[3].owner)  # the failed launch's scope is still ambiguous

    def test_a_delayed_game_inside_the_existing_handoff_interval_cancels_the_return(self):
        self.open()
        self.window(2, 'lunarclient', active=True)
        self.close(2)
        self.now[0] += shell.HANDOFF / 2
        self.helper_.tick()
        self.assertEqual(self.activations, [])
        self.window(3, 'java-lunar', active=True)
        self.expire_close()
        self.assertEqual(self.state(), 'focused')
        self.assertEqual(self.activations, [])

    def test_preexisting_and_known_windows_are_never_inferred(self):
        self.window(2, 'existing')
        self.now[0] += 1
        self.open()
        self.window(3, 'org.kde.kwrite')
        self.window(4, 'aresos-desktop')
        self.assertIsNone(self.windows.toplevels[2].owner)
        self.assertEqual(self.windows.toplevels[3].owner, 'notepad')
        self.assertEqual(self.windows.toplevels[4].owner, shell.Windows.SHELL)

    def test_two_live_programs_do_not_guess_and_known_windows_still_match(self):
        self.open()
        self.open('discord', 'o-2')
        self.window(2, 'java-lunar')
        self.assertIsNone(self.windows.toplevels[2].owner)
        self.window(3, 'lunarclient', active=True)
        self.assertEqual(self.state(), 'focused')

    def test_an_unresolved_reviewed_launch_also_makes_inference_ambiguous(self):
        self.open()
        self.open('notepad', 'o-2')
        self.window(2, 'java-lunar')
        self.assertIsNone(self.windows.toplevels[2].owner)

    def test_unknown_or_gone_scopes_cannot_claim_a_new_window(self):
        self.open()
        self.helper_.processes['o-1'].code = 0
        self.helper_.tick()
        self.scope_answer = (1, '')
        self.scope_pass(self.helper_)
        self.window(2, 'java-lunar')
        self.assertIsNone(self.windows.toplevels[2].owner)
        self.scope_answer = None
        self.scope_pass(self.helper_)
        self.window(3, 'another-java')
        self.assertIsNone(self.windows.toplevels[3].owner)

    def test_a_confirmed_scope_can_claim_after_the_proxy_exits_and_stops_after_scope_death(self):
        self.open()
        self.helper_.processes['o-1'].code = 0
        self.helper_.tick()
        unit = self.helper_.journal.entries['o-1']['unit']
        self.active_units.add(unit)
        self.scope_pass(self.helper_)
        self.window(2, 'java-lunar', active=True)
        self.assertEqual(self.windows.toplevels[2].owner, 'lunarclient')
        self.active_units.clear()
        self.scope_pass(self.helper_)
        self.window(3, 'another-java')
        self.assertIsNone(self.windows.toplevels[3].owner)
        self.assertEqual(self.state(), 'focused')  # scope death never closes a real window
        self.close(2)
        self.expire_close()
        self.assertEqual(self.state(), 'closed')

    def test_restart_recovers_an_unclaimed_game_window_from_the_live_scope(self):
        self.open()
        unit = self.helper_.journal.entries['o-1']['unit']
        self.window(2, 'lunarclient', active=True)
        self.active_units.add(unit)
        windows = shell.Windows(clock=self.clock)
        windows.new(9)
        windows.app_id(9, 'java-lunar')
        windows.state(9, True)
        windows.done(9)
        helper = self.start(windows=windows)
        self.assertEqual(helper.windows.toplevels[9].owner, 'lunarclient')
        self.assertEqual(helper.handles['o-1'], {9})
        self.assertEqual(self.state(), 'focused')
        self.assertEqual(self.popen.call_count, 1)


class DiscoveredSplitReadTest(DiscoveredBase):
    DESKTOP, LAUNCHER, GAME, TERMINAL = 0xff000001, 0xff000002, 0xff000003, 0xff000004

    def run_split(self, stream, split, with_game=False):
        helper = self.start(journal=os.path.join(self.folder.name, 'replay.json'))
        client, server = socket.socketpair()
        try:
            wayland = shell.ForeignToplevels(client, self.windows)
            wayland.kinds.update({50: 'manager', 60: 'seat'})
            wayland.seat = 60
            wayland.feed(wire_toplevel(self.DESKTOP, 'aresos-desktop', True)
                         + wire_toplevel(self.TERMINAL, 'aresos.terminal', False))
            helper.windows_changed()
            self.open()
            wayland.feed(wire_state(self.DESKTOP, False) + wire_toplevel(self.LAUNCHER, 'lunarclient', True))
            helper.windows_changed()
            if with_game:
                wayland.feed(wire_state(self.LAUNCHER, False) + wire_toplevel(self.GAME, 'java-lunar', True))
                helper.windows_changed()
            before = len(self.conn.events('shell_focus'))
            for chunk in (stream[:split], stream[split:]):
                wayland.feed(chunk)
                helper.windows_changed()
            return helper, before
        finally:
            # feed() only sends release/activation messages; no compositor or reader thread is needed.
            client.close()
            server.close()

    def reset_replay(self):
        self.helper_.watcher.stop()
        pathlib.Path(self.helper_.journal.path).unlink()
        self.activations.clear()
        self.now[0] = 100.0

    def test_lunar_launcher_to_java_handover_in_both_orders_at_every_byte_split(self):
        closed = FakeCompositor.message(self.LAUNCHER, 6)
        game = wire_toplevel(self.GAME, 'java-lunar', True)
        orders = {'game first': wire_state(self.LAUNCHER, False) + game + closed,
                  'launcher closes first': closed + game}
        for order, stream in orders.items():
            for split in range(len(stream) + 1):
                with self.subTest(order=order, split=split):
                    helper, before = self.run_split(stream, split)
                    self.expire_close()
                    self.assertEqual(self.activations, [])
                    self.assertEqual(self.state(), 'focused')
                    self.assertEqual(helper.handles['o-1'], {self.GAME})
                    self.assertEqual(self.conn.events('shell_focus')[before:], [])
                    self.close(self.GAME)
                    self.expire_close()
                    self.assertEqual(self.state(), 'closed')
                    self.assertEqual(self.activations, [self.DESKTOP])
                self.reset_replay()

    def test_last_close_and_compositor_refocus_in_both_orders_at_every_byte_split(self):
        closed = FakeCompositor.message(self.LAUNCHER, 6)
        refocus = wire_state(self.TERMINAL, True)
        orders = {'refocus first': wire_state(self.LAUNCHER, False) + refocus + closed,
                  'close first': closed + refocus}
        for order, stream in orders.items():
            for split in range(len(stream) + 1):
                with self.subTest(order=order, split=split):
                    _, before = self.run_split(stream, split)
                    self.expire_close()
                    focus = [(e['focus'], e['reason'], e.get('app_id'))
                             for e in self.conn.events('shell_focus')[before:]]
                    self.assertEqual(focus, [('foreground', 'app_closed', 'lunarclient')])
                    self.assertEqual(self.activations, [self.DESKTOP])
                    self.assertEqual(self.state(), 'closed')
                self.reset_replay()

    def test_both_lunar_windows_close_and_refocus_in_every_order_and_byte_split(self):
        changes = (FakeCompositor.message(self.LAUNCHER, 6), FakeCompositor.message(self.GAME, 6),
                   wire_state(self.GAME, False) + wire_state(self.TERMINAL, True))
        for order in itertools.permutations(range(3)):
            stream = b''.join(changes[i] for i in order)
            for split in range(len(stream) + 1):
                with self.subTest(order=order, split=split):
                    _, before = self.run_split(stream, split, with_game=True)
                    self.expire_close()
                    focus = [(e['focus'], e['reason'], e.get('app_id'))
                             for e in self.conn.events('shell_focus')[before:]]
                    self.assertEqual(focus, [('foreground', 'app_closed', 'lunarclient')])
                    self.assertEqual(self.activations, [self.DESKTOP])
                    self.assertEqual(self.state(), 'closed')
                self.reset_replay()
