"""Package 53a: authenticated views, home snapshots and two-screen window behavior."""
import json
import os
import pathlib
import unittest
from unittest import mock

from test_aresos_shell import ALL, Base, Conn, INSTANCE, NONCE, REGISTRY, ROOT, shell

EXAMPLES = ROOT / 'mod/src/test/resources/shell-1.2'
TOKEN = 'A' * 43
WIRE = 'aresos-shell/1.2'
WEB = shell.App('test-web', 'Test Web', argv=('/usr/bin/test-web',), discovered=True,
                app_ids=('org.test.Web',))
GAME = 'aresos-desktop'
NOTEPAD = 'org.kde.kwrite'
TERMINAL = 'aresos.terminal'


def example(name):
    return json.loads((EXAMPLES / f'{name}.json').read_text())


def house(app_id='notepad', **changes):
    return dict({'id': app_id, 'short': 'test', 'group': 'system_tools', 'cells': 'a' * 144}, **changes)


class ViewBase(Base):
    @staticmethod
    def discovery():
        return shell.Discovery(shell.Catalogue(REGISTRY, entry_dirs=(), deployments=(), executable=lambda _: True))

    def start(self, *, tracked=False, token=TOKEN, status=shell.no_status, catalogue=None, windows=None):
        if tracked and windows is None:
            windows = shell.Windows(self.clock)
        registry = (catalogue.apps, catalogue.revision) if catalogue is not None else shell.load_registry(REGISTRY)
        if catalogue is None:
            registry[0][WEB.id] = WEB
        helper = shell.Helper(REGISTRY, INSTANCE, NONCE, self.journal, launcher=self.launcher(), windows=windows,
                              activate=self.activate, clock=self.clock, executable=lambda _: True,
                              registry=registry, status=status, view_token=token, catalogue=catalogue)
        self.addCleanup(helper.watcher.stop)
        return helper

    def call(self, helper, conn, op, request_id='r-1', **fields):
        return self.send(helper, conn, dict(protocol=WIRE, op=op, id=request_id, **fields))

    @staticmethod
    def send(helper, conn, message):
        previous = len(conn.sent)
        helper.receive(conn, json.dumps(message, ensure_ascii=False).encode() + b'\n')
        return next((reply for reply in conn.sent[previous:] if 'ok' in reply), None)

    def desktop(self, helper, minor=2):
        conn = Conn()
        helper.connected(conn)
        reply = self.call(helper, conn, 'hello', major=1, minor=minor, instance=INSTANCE, nonce=NONCE,
                          capabilities=[*ALL, 'apps_changed', 'shell_covered', 'home_changed', 'apps_running'])
        self.assertTrue(reply['ok'], reply)
        return conn

    def view(self, helper, name='laptop-home'):
        conn = Conn()
        helper.connected(conn)
        reply = self.send(helper, conn, dict(example('view-hello-request'), view=name))
        self.assertTrue(reply['ok'], reply)
        self.assertEqual(conn.sent[1]['event'], 'apps_running')
        return conn

    def publish(self, helper, conn, apps, *, revision='17', part=0, last=True, **fields):
        if part == 0:
            fields.setdefault('palette', {'a': '#aabbcc'})
        return self.call(helper, conn, 'publish_home', revision=revision, part=part, last=last, apps=apps, **fields)

    @staticmethod
    def show(windows, handle, app_id, *, active=False, outputs=(), maximized=False, parent=0):
        windows.new(handle)
        windows.app_id(handle, app_id)
        windows.state(handle, active, maximized=maximized)
        windows.parent(handle, parent)
        for output in outputs:
            windows.output(handle, output, True)
        windows.done(handle)


class AuthenticationTest(ViewBase):
    def test_view_leaves_desktop_connection_readiness_window_rules_and_returns_alone(self):
        status = mock.Mock()
        helper = self.start(tracked=True, status=status)
        desktop = self.desktop(helper, minor=1)
        helper.tick()
        helper.discovered_closing[WEB.id] = (self.clock() + shell.HANDOFF, True, 7)
        self.assertIsNone(helper.world)
        with mock.patch.object(helper, 'cancel_returns') as cancel, \
                mock.patch.object(helper.windows, 'set_registry') as set_registry:
            view = self.view(helper)
            cancel.assert_not_called()
            set_registry.assert_not_called()
        self.assertIs(helper.desktop, desktop)
        self.assertFalse(desktop.closing)
        self.assertEqual(helper.window_minor, 1)
        self.assertFalse(helper.windows_pending)
        self.assertEqual(helper.discovered_closing, {WEB.id: (self.clock() + shell.HANDOFF, True, 7)})
        status.assert_called_once_with(event='desktop_connected')
        for op in ('world_ready', 'heartbeat', 'publish_home', 'request_power', 'future_op'):
            reply = self.call(helper, view, op, instance=INSTANCE, nonce=NONCE, ready=True,
                              world={'desktop': True, 'id': 'world'})
            self.assertEqual(reply['error'], 'invalid_state')
        self.assertIsNone(helper.world)
        self.assertIsNone(helper.last_heartbeat)
        status.assert_called_once()
        replacement = self.desktop(helper, minor=2)
        self.assertFalse(view.closing)
        self.assertTrue(desktop.closing)
        self.assertTrue(self.call(helper, replacement, 'world_ready', instance=INSTANCE, nonce=NONCE,
                                  world={'desktop': True, 'id': 'world'})['ok'])
        status.assert_called_with(event='world_ready', world='world')

    def test_role_credentials_and_view_names(self):
        helper = self.start()
        view = example('view-hello-request')
        game = {key: val for key, val in view.items() if key not in {'role', 'view', 'token', 'requires'}}
        game['nonce'] = NONCE
        refusals = [
            (dict(game, instance='wrong'), 'not_authorized'),
            (dict(game, role='view', view='laptop-home'), 'not_authorized'),
            (dict(game, role='other'), 'not_authorized'),
            (dict(view, role='desktop'), 'not_authorized'),
            (dict(view, nonce=None), 'not_authorized'),
            (dict(view, token='ü' * 43), 'not_authorized'),
            (dict(view, view=None), 'malformed'),
            (dict(view, view='x' * 33), 'malformed'),
            (dict(view, minor=1), 'incompatible_version'),
        ]
        for message, error in refusals:
            with self.subTest(error=error, fields=set(message)):
                conn = Conn()
                helper.connected(conn)
                self.assertEqual(self.send(helper, conn, message)['error'], error)
                self.assertTrue(conn.closing)
                self.assertFalse(conn.authenticated)
                self.assertIsNone(helper.desktop)
                self.assertEqual(helper.views, {})
        conn = Conn()
        helper.connected(conn)
        self.assertTrue(self.send(helper, conn, dict(game, role='desktop'))['ok'])
        self.assertIs(helper.desktop, conn)

    def test_missing_empty_malformed_and_wrong_token_have_the_same_wire_refusal(self):
        wrong = example('view-hello-wrong-token-request')
        expected = example('view-hello-wrong-token-reply')
        for token in (None, '', 'malformed-synthetic-value', TOKEN):
            with self.subTest(configured=bool(token)), mock.patch.object(shell.LOG, 'disabled', False), \
                    self.assertLogs(shell.LOG, level='WARNING') as logs:
                helper = self.start(token=token)
                for _ in range(2):
                    conn = Conn()
                    helper.connected(conn)
                    self.assertEqual(self.send(helper, conn, wrong), expected)
                    self.assertTrue(conn.closing)
                malformed = sum('ignoring a malformed ARESOS_VIEW_TOKEN' in line for line in logs.output)
                self.assertEqual(malformed, int(token == 'malformed-synthetic-value'))
                self.assertNotIn('malformed-synthetic-value', '\n'.join(logs.output))
                self.assertNotIn(wrong['token'], '\n'.join(logs.output))

    def test_build_reads_the_token_once_and_children_get_only_public_environment(self):
        env = dict(os.environ, ARESOS_VIEW_TOKEN=TOKEN, ARESOS_LAUNCH_NONCE=NONCE,
                   ARESOS_DESKTOP_INSTANCE=INSTANCE, NOTIFY_SOCKET='/run/fake', WAYLAND_DISPLAY='test-display')
        launcher = shell.ScopeLauncher(popen=self.popen, environ=env)
        with mock.patch.object(shell, 'desktop_directories', return_value=()), \
                mock.patch.object(shell, 'flatpak_deployments', return_value=()):
            helper, _ = shell.build(REGISTRY, INSTANCE, NONCE, self.journal, environ=env, launcher=launcher,
                                    connect=mock.Mock(side_effect=shell.WaylandError('test has no compositor')))
        self.addCleanup(helper.catalogue.stop)
        self.addCleanup(helper.watcher.stop)
        helper.icons.stop()
        helper.icons = None
        helper.executable = lambda _: True
        env['ARESOS_VIEW_TOKEN'] = 'B' * 43
        view = self.view(helper)
        self.assertTrue(self.call(helper, view, 'open_app', app_id='terminal')['ok'])
        app_env = self.popen.call_args.kwargs['env']
        systemctl = mock.Mock(return_value=mock.Mock(returncode=0, stdout=''))
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(shell.query_scopes({'example.scope'}, systemctl), {'example.scope': shell.GONE})
        scope_env = systemctl.call_args.kwargs['env']
        for child in (app_env, scope_env):
            self.assertTrue(set(child).isdisjoint(shell.PRIVATE_ENVIRONMENT))
            self.assertEqual(child['WAYLAND_DISPLAY'], 'test-display')

    def test_same_name_replaces_only_that_view_and_a_fifth_name_is_busy(self):
        helper = self.start()
        desktop = self.desktop(helper)
        first = self.view(helper)
        others = [self.view(helper, f'view-{index}') for index in range(3)]
        refused = Conn()
        helper.connected(refused)
        self.assertEqual(self.send(helper, refused, example('view-hello-busy-request')),
                         example('view-hello-busy-reply'))
        self.assertTrue(refused.closing)
        latest = self.view(helper)
        self.assertTrue(first.closing)
        self.assertIs(helper.views['view:laptop-home'], latest)
        helper.disconnected(first)
        self.assertIs(helper.views['view:laptop-home'], latest)
        self.assertFalse(desktop.closing)
        self.assertTrue(all(not conn.closing for conn in others))


class LaunchIsolationTest(ViewBase):
    def test_pending_and_replayed_request_ids_are_scoped_to_the_client(self):
        helper = self.start()
        desktop, view = self.desktop(helper), self.view(helper)
        game_check, view_check = shell.LaunchCheck(), shell.LaunchCheck()
        with mock.patch.object(shell, 'CHECK_WAIT', 0), \
                mock.patch.object(helper.checks, 'start', side_effect=[game_check, view_check]):
            self.assertIsNone(self.call(helper, desktop, 'open_app', 'same', app_id='terminal'))
            self.assertIsNone(self.call(helper, view, 'open_app', 'same', app_id='notepad'))
            self.assertEqual(self.call(helper, view, 'open_app', 'same', app_id='terminal')['error'],
                             'request_id_reused')
        self.assertEqual(set(helper.checking), {(shell.DESKTOP, 'same'), ('view:laptop-home', 'same')})
        for check, argv in ((game_check, ('/usr/bin/foot',)), (view_check, ('/usr/bin/kwrite',))):
            check.result = (argv, '~', None)
            check.done.set()
        helper.tick()
        launched_game, launched_view = desktop.sent[-1], view.sent[-1]
        for conn, reply, app_id in ((desktop, launched_game, 'terminal'), (view, launched_view, 'notepad')):
            self.assertEqual((reply['ok'], reply['request_id'], reply['app_id']), (True, 'same', app_id))
            self.assertEqual(self.call(helper, conn, 'open_app', 'same', app_id=app_id), reply)
        self.assertNotEqual(launched_game['launch_id'], launched_view['launch_id'])
        self.assertEqual(self.popen.call_count, 2)

    def test_view_cannot_fill_desktop_journal(self):
        helper = self.start()
        view, desktop = self.view(helper), self.desktop(helper)
        for index in range(32):
            self.assertTrue(self.call(helper, view, 'open_app', f'v-{index}', app_id='terminal')['ok'])
        self.assertEqual(self.call(helper, view, 'open_app', 'v-32', app_id='terminal')['error'], 'journal_full')
        self.assertTrue(self.call(helper, desktop, 'open_app', 'v-0', app_id='notepad')['ok'])
        self.assertEqual(self.popen.call_count, 33)

    def test_fifth_launching_view_evicts_oldest_history_and_live_processes_keep_their_ids(self):
        helper = self.start()
        desktop = self.desktop(helper)
        self.assertTrue(self.call(helper, desktop, 'open_app', 'same', app_id='notepad')['ok'])
        for name in ('a', 'b', 'c', 'd'):
            conn = self.view(helper, name)
            self.assertTrue(self.call(helper, conn, 'open_app', 'same', app_id='terminal')['ok'])
            helper.disconnected(conn)
        old_process = helper.processes['view:b', 'same']
        again = self.view(helper, 'a')
        original_a = helper.journal.entries['view:a', 'same']['launch_id']
        self.assertEqual(self.call(helper, again, 'open_app', 'same', app_id='terminal')['launch_id'], original_a)
        newest = self.view(helper, 'e')
        self.assertTrue(self.call(helper, newest, 'open_app', 'same', app_id='terminal')['ok'])
        self.assertNotIn(('view:b', 'same'), helper.journal.entries)
        self.assertNotIn(('view:b', 'same'), helper.processes)
        with pathlib.Path(self.journal).open() as handle:
            saved = json.load(handle)
        self.assertEqual(list(saved['view_launches']), ['c', 'd', 'a', 'e'])
        self.assertIn('same', saved['launches'])
        self.active_units = {entry['unit'] for entry in helper.journal.entries.values()}
        restarted = self.start()
        self.assertEqual(set(restarted.journal.entries), set(helper.journal.entries))
        b_again = self.view(helper, 'b')
        new_b = self.call(helper, b_again, 'open_app', 'same', app_id='notepad')
        old_process.code = 2
        helper.tick()
        self.assertEqual(self.call(helper, b_again, 'open_app', 'same', app_id='notepad'), new_b)
        self.assertEqual(b_again.events('app_state'), [])

    def test_app_state_only_reaches_its_client_after_reconnect_and_restart(self):
        helper = self.start(tracked=True)
        desktop, view, unrelated = self.desktop(helper), self.view(helper), self.view(helper, 'another')
        game = self.call(helper, desktop, 'open_app', 'same', app_id='notepad')
        launch = self.call(helper, view, 'open_app', 'same', app_id=WEB.id)
        windows = helper.windows
        self.show(windows, 1, GAME)
        self.show(windows, 2, NOTEPAD)
        self.show(windows, 3, WEB.app_ids[0], active=True)
        helper.windows_changed()
        self.assertEqual([event['launch_id'] for event in view.events('app_state')], [launch['launch_id']])
        self.assertEqual([event['launch_id'] for event in desktop.events('app_state')], [game['launch_id']])
        self.assertEqual(unrelated.events('app_state'), [])

        self.active_units = {entry['unit'] for entry in helper.journal.entries.values()}
        restarted = self.start(windows=windows)
        self.assertEqual(restarted.window_minor, 0)
        self.assertIsNone(windows.toplevels[3].owner)
        reconnected = self.view(restarted)
        other = self.view(restarted, 'another')
        game_conn = self.desktop(restarted, minor=0)
        self.assertEqual(self.call(restarted, reconnected, 'open_app', 'same', app_id=WEB.id)['launch_id'],
                         launch['launch_id'])
        windows.gone(3)
        restarted.windows_changed()
        self.now[0] += shell.HANDOFF + 0.01
        restarted.tick()
        events = reconnected.events('app_state')
        self.assertEqual([(event['request_id'], event['launch_id'], event['state']) for event in events],
                         [('same', launch['launch_id'], 'closed')])
        self.assertEqual(other.events('app_state'), [])
        self.assertEqual(game_conn.events('app_state'), [])

    def test_restart_waits_to_adopt_a_discovered_window_until_the_catalogue_is_complete(self):
        helper = self.start(tracked=True)
        view = self.view(helper)
        launch = self.call(helper, view, 'open_app', 'web', app_id=WEB.id)
        self.show(helper.windows, 3, WEB.app_ids[0], active=True)
        helper.windows_changed()
        self.assertEqual(view.events('app_state')[-1]['state'], 'focused')

        catalogue = self.discovery()
        restarted = self.start(windows=helper.windows, catalogue=catalogue)
        view = self.view(restarted)
        before_scan = self.call(restarted, view, 'open_app', 'web', app_id=WEB.id)
        self.assertEqual((before_scan['launch_id'], before_scan['state']), (launch['launch_id'], 'focused'))
        self.assertEqual(view.events('apps_running')[-1]['apps'], [])
        catalogue.finished = ({**catalogue.apps, WEB.id: WEB}, 'complete', catalogue.legacy)
        restarted.tick()
        self.assertEqual(view.events('apps_running')[-1]['apps'], [WEB.id])
        self.assertEqual(restarted.handles['view:laptop-home', 'web'], {3})
        restarted.windows.gone(3)
        restarted.windows_changed()
        self.now[0] += shell.HANDOFF + 0.01
        restarted.tick()
        self.assertEqual([event['state'] for event in view.events('app_state')], ['closed'])

    def test_restart_with_slow_discovery_preserves_the_window_wait(self):
        helper = self.start(tracked=True)
        launch = self.call(helper, self.view(helper), 'open_app', 'web', app_id=WEB.id)
        catalogue = self.discovery()
        restarted = self.start(tracked=True, catalogue=catalogue)
        view = self.view(restarted)
        self.scope_pass(restarted)
        self.now[0] += shell.WINDOW_TIMEOUT + 0.01
        restarted.tick()
        replay = self.call(restarted, view, 'open_app', 'web', app_id=WEB.id)
        self.assertEqual((replay['launch_id'], replay['state']), (launch['launch_id'], 'starting'))
        self.show(restarted.windows, 3, WEB.app_ids[0], active=True)
        restarted.windows_changed()
        catalogue.finished = ({**catalogue.apps, WEB.id: WEB}, 'complete', catalogue.legacy)
        restarted.tick()
        self.assertEqual([event['state'] for event in view.events('app_state')], ['focused'])


class HomeTest(ViewBase):
    def test_bad_parts_discard_only_the_incomplete_revision(self):
        helper = self.start()
        desktop, view = self.desktop(helper), self.view(helper)
        self.assertTrue(self.publish(helper, desktop, [house()])['ok'])
        bad_parts = [
            dict(part=2, revision='18'),
            dict(part=0, revision='18'),
            dict(part=0, revision='19'),
            dict(part=1, revision='19'),
            dict(part=1, revision='18', palette={}),
            dict(part=1, revision='18', apps=[house()]),
            dict(part=1, revision='18', apps=[house('terminal', cells='z' * 144)]),
        ]
        for fields in bad_parts:
            with self.subTest(fields=fields):
                self.assertTrue(self.publish(helper, desktop, [house()], revision='18', last=False)['ok'])
                args = {'apps': [], 'last': True, **fields}
                self.assertEqual(self.call(helper, desktop, 'publish_home', **args)['error'], 'malformed')
                self.assertEqual(self.publish(helper, desktop, [], revision='18', part=1)['error'], 'malformed')
                home = self.call(helper, view, 'get_home')
                self.assertEqual((home['revision'], home['apps']), ('17', [house()]))
        self.assertEqual(len(view.events('home_changed')), 1)

    def test_bounds_and_field_shapes(self):
        helper = self.start()
        desktop, view = self.desktop(helper), self.view(helper)
        for part in range(15):
            self.assertTrue(self.publish(helper, desktop, [], part=part, last=False)['ok'])
        self.assertEqual(self.publish(helper, desktop, [], part=15, last=False)['error'], 'malformed')
        self.assertEqual(self.publish(helper, desktop, [], part=16)['error'], 'malformed')
        for part in range(16):
            self.assertTrue(self.publish(helper, desktop, [], part=part, last=part == 15)['ok'])
        self.assertEqual(self.call(helper, view, 'get_home')['revision'], '17')

        for palette in ([['a', '#aabbcc']], {'é': '#aabbcc'}, {'.': '#aabbcc'}, {'aa': '#aabbcc'},
                        {'a': '#abc'}, {'a': 1}, {str(index): '#aabbcc' for index in range(65)}):
            self.assertEqual(self.publish(helper, desktop, [], palette=palette)['error'], 'malformed')
        self.assertEqual(self.call(helper, desktop, 'publish_home', revision='18', part=0, last=True, apps=[])['error'],
                         'malformed')
        for bad in (dict(short=''), dict(short='x' * 65), dict(short='line\nfeed'), dict(short='c\x7f'),
                    dict(id='INVALID'), dict(group='different group'), dict(group='a' * 65), dict(place=None),
                    dict(place='a' * 33), dict(slot=True), dict(slot=9), dict(cells='a' * 143)):
            self.assertEqual(self.publish(helper, desktop, [house(**bad)])['error'], 'malformed')
        for bad in (dict(revision=''), dict(revision='x' * 129), dict(part=True), dict(last=1)):
            self.assertEqual(self.publish(helper, desktop, [], **bad)['error'], 'malformed')
        apps = [house(f'app-{index}') for index in range(200)]
        self.assertTrue(self.publish(helper, desktop, apps[:100], revision='18', last=False)['ok'])
        self.assertEqual(self.publish(helper, desktop, apps[100:] + [house()], revision='18', part=1)['error'],
                         'malformed')
        self.assertEqual(self.call(helper, view, 'get_home')['revision'], '17')

    def test_home_survives_desktop_reconnection_but_a_partial_publish_does_not(self):
        helper = self.start()
        desktop, view = self.desktop(helper), self.view(helper)
        self.assertTrue(self.publish(helper, desktop, [house()])['ok'])
        self.assertTrue(self.publish(helper, desktop, [house('terminal')], revision='18', last=False)['ok'])
        desktop = self.desktop(helper)
        self.assertEqual(self.publish(helper, desktop, [], revision='18', part=1)['error'], 'malformed')
        self.assertEqual(self.call(helper, view, 'get_home')['apps'], [house()])
        rebooted = self.start()
        self.assertIsNone(self.call(rebooted, self.view(rebooted), 'get_home')['revision'])

    def test_only_complete_catalogue_can_remove_unknown_apps_and_uninstalls(self):
        catalogue = self.discovery()
        helper = self.start(catalogue=catalogue)
        desktop, view = self.desktop(helper), self.view(helper)
        apps = [house(), house(WEB.id), house('not-installed')]
        self.assertTrue(self.publish(helper, desktop, apps)['ok'])
        self.assertEqual(self.call(helper, view, 'get_home')['apps'], sorted(apps, key=lambda app: app['id']))
        complete = dict(catalogue.apps, **{WEB.id: WEB})
        catalogue.finished = (complete, 'complete', catalogue.legacy)
        with mock.patch.object(shell.LOG, 'disabled', False), self.assertLogs(shell.LOG, level='WARNING') as logs:
            self.assertEqual(self.call(helper, view, 'get_home')['apps'], [house(), house(WEB.id)])
        self.assertEqual(len(logs.output), 1)
        self.assertIn('not-installed', logs.output[0])
        self.assertEqual(view.events('apps_changed')[-1]['revision'], 'complete')
        with mock.patch.object(shell.LOG, 'disabled', False), self.assertLogs(shell.LOG, level='WARNING') as logs:
            self.assertTrue(self.publish(helper, desktop, apps + [house('not-installed-2')], revision='18')['ok'])
            self.call(helper, view, 'get_home')
        self.assertEqual(len(logs.output), 1)
        catalogue.finished = ({app_id: app for app_id, app in complete.items() if app_id != WEB.id},
                              'uninstalled', catalogue.legacy)
        self.assertEqual(self.call(helper, view, 'get_home')['apps'], [house()])

    def test_deferred_filter_notifies_views_even_when_catalogue_revision_is_unchanged(self):
        catalogue = self.discovery()
        helper = self.start(catalogue=catalogue)
        desktop, view = self.desktop(helper), self.view(helper)
        self.assertTrue(self.publish(helper, desktop, [house(), house('not-installed')])['ok'])
        self.assertEqual(len(self.call(helper, view, 'get_home')['apps']), 2)
        catalogue.finished = (catalogue.apps, catalogue.revision, catalogue.legacy)
        helper.tick()
        self.assertEqual(view.events('apps_changed'), [])
        self.assertEqual([event['revision'] for event in view.events('home_changed')], ['17', '17'])
        self.assertEqual(self.call(helper, view, 'get_home')['apps'], [house()])

    def test_real_wire_limit_paginates_large_unicode_home_with_palette_on_every_page(self):
        catalogue = self.discovery()
        helper = self.start(catalogue=catalogue)
        desktop, view = self.desktop(helper), self.view(helper)
        apps = [house(f'app-{index:03d}', short='🏠' * 64, group='g' * 64, place='p' * 32, slot=8)
                for index in range(200)]
        palette = {'a': '#123456', 'b': '#ABCDEF'}
        self.assertTrue(self.publish(helper, desktop, apps[:100], last=False, palette=palette)['ok'])
        self.assertTrue(self.publish(helper, desktop, apps[100:], part=1)['ok'])
        received, cursor, page_count = [], None, 0
        while True:
            page = self.call(helper, view, 'get_home', **({'cursor': cursor} if cursor else {}))
            self.assertEqual((page['revision'], page['palette']), ('17', palette))
            wire_size = len(json.dumps(page, ensure_ascii=False, separators=(',', ':')).encode()) + 1
            self.assertLessEqual(wire_size, 64 * 1024)
            page_count += 1
            self.assertLessEqual(page_count, 2)
            received.extend(page['apps'])
            cursor = page.get('next')
            if cursor is None:
                break
        self.assertEqual(page_count, 2)
        self.assertEqual(received, apps)
        self.assertEqual(self.call(helper, view, 'get_home', cursor='bad')['error'], 'invalid_cursor')
        self.assertEqual(self.call(helper, view, 'get_home', cursor=1)['error'], 'malformed')
        self.assertEqual(self.call(helper, desktop, 'get_home')['error'], 'invalid_state')


class WindowViewsTest(ViewBase):
    def test_apps_running_uses_all_windows_with_no_desktop_a_legacy_desktop_and_after_restart(self):
        helper = self.start(tracked=True)
        windows = helper.windows
        view = self.view(helper)
        self.assertEqual(view.events('apps_running')[-1]['apps'], [])
        self.show(windows, 1, WEB.app_ids[0])
        self.show(windows, 2, NOTEPAD)
        helper.windows_changed()
        self.show(windows, 3, WEB.app_ids[0], parent=1)
        helper.windows_changed()
        helper.tick()
        self.assertEqual([event['apps'] for event in view.events('apps_running')], [[], ['notepad', WEB.id]])
        self.assertIsNone(windows.toplevels[1].owner)
        desktop = self.desktop(helper, minor=0)
        helper.tick()
        self.assertIsNone(windows.toplevels[1].owner)
        self.assertEqual(len(view.events('apps_running')), 2)
        windows.gone(1)
        windows.gone(3)
        helper.windows_changed()
        helper.tick()
        self.assertEqual(view.events('apps_running')[-1]['apps'], ['notepad'])
        self.show(windows, 1, WEB.app_ids[0])
        self.show(windows, 3, '', parent=1)
        helper.windows_changed()
        helper.tick()
        self.assertIsNone(windows.toplevels[3].owner)
        self.assertEqual(view.events('apps_running')[-1]['apps'], ['notepad', WEB.id])
        later = self.view(helper, 'later')
        self.assertEqual(later.events('apps_running')[-1]['apps'], ['notepad', WEB.id])

        restarted = self.start(windows=windows)
        reconnected = self.view(restarted)
        self.assertEqual(reconnected.events('apps_running')[-1]['apps'], ['notepad', WEB.id])
        windows.gone(1)
        restarted.windows_changed()
        restarted.tick()
        self.assertEqual(len(reconnected.events('apps_running')), 1)
        windows.gone(3)
        restarted.windows_changed()
        restarted.tick()
        self.assertEqual(reconnected.events('apps_running')[-1]['apps'], ['notepad'])
        self.assertEqual(desktop.events('apps_running'), [])

    def test_without_window_tracking_running_event_is_sent_once(self):
        helper = self.start()
        view = self.view(helper)
        self.assertEqual(view.events(), [example('apps-running-empty-event')])
        self.call(helper, view, 'open_app', app_id='terminal')
        helper.tick()
        self.assertEqual(view.events('apps_running'), [example('apps-running-empty-event')])

    def test_view_window_observation_does_not_retain_an_uninstalled_desktop_owner(self):
        for view_launch in (False, True):
            with self.subTest(view_launch=view_launch):
                catalogue = self.discovery()
                starters = catalogue.apps
                catalogue.finished = ({**starters, WEB.id: WEB}, 'complete', catalogue.legacy)
                catalogue.refresh(self.clock())
                helper = self.start(tracked=True, catalogue=catalogue)
                self.desktop(helper, minor=0)
                view = self.view(helper)
                if view_launch:
                    self.assertTrue(self.call(helper, view, 'open_app', 'web', app_id=WEB.id)['ok'])
                self.show(helper.windows, 1, WEB.app_ids[0], active=True)
                helper.windows_changed()
                helper.tick()
                self.assertEqual(view.events('apps_running')[-1]['apps'], [WEB.id])
                catalogue.finished = (starters, 'uninstalled', catalogue.legacy)
                helper.tick()
                self.assertEqual(view.events('apps_running')[-1]['apps'], [])
                self.desktop(helper, minor=1)
                helper.tick()
                self.assertIsNone(helper.windows.toplevels[1].owner)
                if view_launch:
                    helper.windows.gone(1)
                    helper.windows_changed()
                    self.now[0] += shell.HANDOFF + 0.01
                    helper.tick()
                    self.assertEqual([e['state'] for e in view.events('app_state')], ['focused', 'closed'])

    def test_last_window_output_controls_return_for_reviewed_and_discovered_apps(self):
        for app_id in (NOTEPAD, WEB.app_ids[0]):
            for outputs, view_connected, move, returns in (
                    ((2,), True, False, False),
                    ((1,), True, False, True),
                    ((), True, False, True),
                    ((2,), False, False, True),
                    ((1,), True, True, False)):
                with self.subTest(app_id=app_id, outputs=outputs, view=view_connected, moved=move):
                    self.activations.clear()
                    helper = self.start(tracked=True)
                    desktop = self.desktop(helper, minor=1)
                    view = self.view(helper) if view_connected else None
                    windows = helper.windows
                    self.show(windows, 1, GAME, active=True, outputs=(1,))
                    helper.windows_changed()
                    windows.state(1, False)
                    windows.done(1)
                    self.show(windows, 2, app_id, active=True, outputs=outputs, maximized=True)
                    helper.windows_changed()
                    if move:
                        windows.output(2, 1, False)
                        windows.output(2, 2, True)
                        windows.done(2)
                        helper.windows_changed()
                    windows.gone(2)
                    helper.windows_changed()
                    self.now[0] += shell.HANDOFF + 0.01
                    helper.tick()
                    focus = [event['reason'] for event in desktop.events('shell_focus')]
                    self.assertEqual(self.activations, [1] if returns else [])
                    self.assertEqual(focus, ['app_activated', 'app_closed'] if returns else ['app_activated'])
                    if view is not None:
                        self.assertEqual(view.events('shell_focus'), [])
                        self.assertEqual(view.events('shell_covered'), [])
                    if not returns:
                        windows.state(1, True)
                        windows.done(1)
                        helper.windows_changed()
                        self.assertEqual(desktop.events('shell_focus')[-1]['reason'], 'desktop_activated')
                        self.assertEqual(self.activations, [])

    def test_focus_uses_last_window_closed_in_a_batch(self):
        helper = self.start(tracked=True)
        desktop = self.desktop(helper)
        self.view(helper)
        windows = helper.windows
        self.show(windows, 1, GAME, outputs=(1,))
        self.show(windows, 2, NOTEPAD, active=True, outputs=(1,))
        self.show(windows, 3, NOTEPAD, outputs=(2,))
        helper.windows_changed()
        windows.gone(2)
        windows.gone(3)
        helper.windows_changed()
        self.assertEqual(self.activations, [])
        self.assertEqual([event['reason'] for event in desktop.events('shell_focus')], ['app_activated'])


class ContractExamplesTest(ViewBase):
    def test_every_example_matches_the_helper(self):
        read = set()

        def fixture(stem):
            read.add(stem + '.json')
            return example(stem)

        def request(conn, stem, reply=None):
            received = self.send(helper, conn, fixture(stem + '-request'))
            self.assertEqual(received, fixture(reply or stem + '-reply'))

        helper = self.start(tracked=True)
        helper.cursor_key = bytes(32)
        desktop = self.desktop(helper)
        view = Conn()
        helper.connected(view)
        request(view, 'view-hello')
        self.assertEqual(view.events(), [fixture('apps-running-empty-event')])
        for refusal in ('wrong-token', 'wrong-instance', 'both-secrets', 'no-role', 'bad-name'):
            peer = Conn()
            helper.connected(peer)
            request(peer, 'view-hello-' + refusal)
            self.assertTrue(peer.closing)
        for name in ('one', 'two', 'three'):
            self.view(helper, name)
        peer = Conn()
        helper.connected(peer)
        request(peer, 'view-hello-busy')
        request(view, 'get-home', 'get-home-empty-reply')
        request(desktop, 'publish-home')
        self.assertEqual(view.events('home_changed'), [fixture('home-changed-event')])
        request(view, 'get-home')
        request(desktop, 'publish-home-part-0')
        request(view, 'get-home')
        request(desktop, 'publish-home-part-1')
        self.assertEqual([event['revision'] for event in view.events('home_changed')], ['17', '18'])
        with mock.patch.object(shell, 'MAX_MESSAGE', 520):
            request(view, 'get-home', 'get-home-first-page-reply')
            request(view, 'get-home-next', 'get-home-last-page-reply')

        helper = self.start(tracked=True)
        view = self.view(helper)
        self.show(helper.windows, 2, TERMINAL)
        self.show(helper.windows, 1, NOTEPAD)
        helper.windows_changed()
        helper.tick()
        self.assertEqual(view.events('apps_running')[-1], fixture('apps-running-event'))

        # Package 53d: Super's search over the world and open_app's screen hint.
        helper = self.start(tracked=True)
        desktop = Conn()
        helper.connected(desktop)
        request(desktop, 'desktop-hello')
        self.show(helper.windows, 1, GAME, active=True, outputs=(1,))
        helper.windows_changed()
        self.assertTrue(self.call(helper, desktop, 'world_ready', instance=INSTANCE, nonce=NONCE,
                                  world={'desktop': True, 'id': 'world'})['ok'])
        helper.search()
        self.assertEqual(desktop.events(), [fixture('shell-search-event')])
        with mock.patch.object(shell.secrets, 'token_hex', return_value='0123456789abcdef'):
            request(desktop, 'open-app-world')
        request(desktop, 'open-app-bad-screen')
        self.assertEqual(read, {path.name for path in EXAMPLES.glob('*.json')})


if __name__ == '__main__':
    unittest.main()
