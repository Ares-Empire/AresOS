"""Package 322: restart focus attribution, home cursors and launch check capacity."""
import queue
import threading
from unittest import mock

from test_aresos_shell import shell
from test_aresos_shell_views import GAME, NOTEPAD, WEB, ViewBase, house


class RestartFocusTest(ViewBase):
    def restart(self, helper):
        self.active_units = {entry['unit'] for entry in helper.journal.entries.values()}
        return self.start(windows=helper.windows)

    def focus(self, helper, handle):
        for window in helper.windows.toplevels.values():
            helper.windows.state(window.handle, window.handle == handle)
            helper.windows.done(window.handle)
        helper.windows_changed()

    def test_two_adopted_launches_share_presence_without_claiming_focus(self):
        helper = self.start(tracked=True)
        desktop, view = self.desktop(helper), self.view(helper)
        windows = helper.windows
        self.show(windows, 1, GAME)
        game_launch = self.call(helper, desktop, 'open_app', 'game', app_id='notepad')
        self.show(windows, 2, NOTEPAD, active=True)
        helper.windows_changed()
        view_launch = self.call(helper, view, 'open_app', 'view', app_id='notepad')
        self.show(windows, 3, NOTEPAD)
        self.focus(helper, 3)
        self.assertEqual(view.events('app_state')[-1]['state'], 'focused')

        helper = self.restart(helper)
        desktop, view = self.desktop(helper), self.view(helper)
        self.assertEqual(view.events('apps_running')[-1]['apps'], ['notepad'])
        for active in (3, 2, 3):
            self.focus(helper, active)
            for conn, launch in ((desktop, game_launch), (view, view_launch)):
                replay = self.call(helper, conn, 'open_app', launch['request_id'], app_id='notepad')
                self.assertEqual((replay['launch_id'], replay['state']), (launch['launch_id'], 'background'))

        windows.gone(3)
        self.focus(helper, 2)
        self.assertEqual(self.call(helper, view, 'open_app', 'view', app_id='notepad')['state'], 'background')
        self.assertEqual(self.call(helper, desktop, 'open_app', 'game', app_id='notepad')['state'], 'background')
        windows.gone(2)
        helper.windows_changed()
        helper.tick()
        for conn, launch in ((desktop, game_launch), (view, view_launch)):
            self.assertEqual([(e['launch_id'], e['state']) for e in conn.events('app_state')],
                             [(launch['launch_id'], 'closed')])
        self.assertEqual(view.events('apps_running')[-1]['apps'], [])

    def test_two_adopted_launches_remain_ambiguous_with_one_surviving_window(self):
        helper = self.start(tracked=True)
        desktop, view = self.desktop(helper), self.view(helper)
        for conn, handle in ((desktop, 1), (view, 2)):
            self.call(helper, conn, 'open_app', 'old', app_id='notepad')
            self.show(helper.windows, handle, NOTEPAD)
            self.focus(helper, handle)
        helper.windows.gone(1)
        # The old helper stopped before processing the close, so both launches are still open in its journal.
        helper = self.restart(helper)
        for conn in (self.desktop(helper), self.view(helper)):
            self.assertEqual(self.call(helper, conn, 'open_app', 'old', app_id='notepad')['state'], 'background')

    def test_two_windows_make_even_one_adopted_launch_ambiguous_but_a_new_launch_can_focus(self):
        helper = self.start(tracked=True)
        view = self.view(helper)
        old = self.call(helper, view, 'open_app', 'old', app_id='notepad')
        self.show(helper.windows, 1, NOTEPAD, active=True)
        helper.windows_changed()
        self.show(helper.windows, 2, NOTEPAD)
        helper.windows_changed()

        helper = self.restart(helper)
        view = self.view(helper)
        self.assertEqual(self.call(helper, view, 'open_app', 'old', app_id='notepad')['state'], 'background')
        helper.windows.gone(1)
        self.focus(helper, 2)
        self.assertEqual(view.events('app_state'), [])
        new = self.call(helper, view, 'open_app', 'new', app_id='notepad')
        self.show(helper.windows, 3, NOTEPAD)
        self.focus(helper, 3)
        self.assertEqual([(e['launch_id'], e['state']) for e in view.events('app_state')],
                         [(new['launch_id'], 'focused')])
        self.assertEqual(helper.handles['view:laptop-home', 'old'], {2})
        self.assertEqual(self.call(helper, view, 'open_app', 'old', app_id='notepad')['launch_id'], old['launch_id'])

    def test_one_adopted_launch_and_one_window_still_report_focus(self):
        helper = self.start(tracked=True)
        launch = self.call(helper, self.view(helper), 'open_app', 'old', app_id='notepad')
        self.show(helper.windows, 1, NOTEPAD, active=True)
        helper.windows_changed()
        helper = self.restart(helper)
        view = self.view(helper)
        replay = self.call(helper, view, 'open_app', 'old', app_id='notepad')
        self.assertEqual((replay['launch_id'], replay['state']), (launch['launch_id'], 'focused'))
        self.show(helper.windows, 2, GAME)
        self.focus(helper, 2)
        self.focus(helper, 1)
        self.assertEqual([e['state'] for e in view.events('app_state')], ['background', 'focused'])

    def test_discovered_launches_can_still_report_focus_on_either_adopted_window(self):
        helper = self.start(tracked=True)
        desktop, view = self.desktop(helper), self.view(helper)
        for conn in (desktop, view):
            self.call(helper, conn, 'open_app', 'old', app_id=WEB.id)
        self.show(helper.windows, 1, WEB.app_ids[0], active=True)
        self.show(helper.windows, 2, WEB.app_ids[0])
        helper.windows_changed()
        helper = self.restart(helper)
        desktop, view = self.desktop(helper), self.view(helper)
        self.focus(helper, 2)
        for conn in (desktop, view):
            self.assertEqual(self.call(helper, conn, 'open_app', 'old', app_id=WEB.id)['state'], 'focused')


class HomeCursorTest(ViewBase):
    def setUp(self):
        super().setUp()
        self.houses = [house(f'app-{index:03d}', short='🏠' * 64, group='g' * 64, place='p' * 32, slot=8)
                       for index in range(200)]
        self.catalogue = self.discovery()
        self.helper = self.start(catalogue=self.catalogue)
        self.desktop_conn, self.view_conn = self.desktop(self.helper), self.view(self.helper)
        self.apps = {row['id']: shell.App(row['id'], row['short']) for row in self.houses}
        self.catalogue.finished = (self.apps, 'installed', self.catalogue.legacy)
        self.publish_houses('17')

    def publish_houses(self, revision):
        self.assertTrue(self.publish(self.helper, self.desktop_conn, self.houses[:100], revision=revision,
                                     last=False)['ok'])
        self.assertTrue(self.publish(self.helper, self.desktop_conn, self.houses[100:], revision=revision,
                                     part=1)['ok'])

    def get_home(self, **fields):
        return self.call(self.helper, self.view_conn, 'get_home', **fields)

    def assert_two_pages(self, first, expected, revision):
        self.assertRegex(first['next'], r'^p[0-9]{1,3}-[0-9a-f]{24}$')
        second = self.get_home(cursor=first['next'])
        self.assertTrue(second['ok'], second)
        self.assertEqual((first['revision'], second['revision']), (revision, revision))
        self.assertEqual(first['palette'], second['palette'])
        self.assertNotIn('next', second)
        self.assertEqual(first['apps'] + second['apps'], expected)

    def test_unchanged_home_pages_the_same_houses(self):
        first = self.get_home()
        self.assertEqual(self.get_home(), first)
        self.assert_two_pages(first, self.houses, '17')

    def test_uninstall_from_page_one_invalidates_the_cursor_with_the_same_home_revision(self):
        first = self.get_home()
        uninstalled = first['apps'][0]
        self.catalogue.finished = ({key: app for key, app in self.apps.items() if key != uninstalled['id']},
                                   'uninstalled', self.catalogue.legacy)
        stale = self.get_home(cursor=first['next'])
        self.assertEqual((stale['ok'], stale['error']), (False, 'invalid_cursor'))
        self.assert_two_pages(self.get_home(), [row for row in self.houses if row != uninstalled], '17')

    def test_new_revision_invalidates_the_cursor_with_the_same_houses(self):
        first = self.get_home()
        self.publish_houses('18')
        stale = self.get_home(cursor=first['next'])
        self.assertEqual((stale['ok'], stale['error']), (False, 'invalid_cursor'))
        self.assert_two_pages(self.get_home(), self.houses, '18')


class CheckReserveTest(ViewBase):
    def setUp(self):
        super().setUp()
        catalogue = self.discovery()
        self.helper = self.start(catalogue=catalogue)
        self.desktop_conn = self.desktop(self.helper)
        self.programs = [f'test-app-{index}' for index in range(shell.MAX_CHECKS + 1)]
        apps = {app_id: shell.App(app_id, app_id, argv=(f'/usr/bin/{app_id}',)) for app_id in self.programs}
        catalogue.finished = (apps, 'tested', catalogue.legacy)
        self.helper.tick()
        self.started_checks = queue.Queue()
        self.releases = {app_id: threading.Event() for app_id in self.programs}
        self.workers = []
        self.enterContext(mock.patch.object(shell, 'launch_check', side_effect=self.blocked_check))
        self.enterContext(mock.patch.object(shell, 'CHECK_WAIT', 0))
        self.addCleanup(self.release_checks)

    def blocked_check(self, app, _executable, _working_directory):
        worker = threading.current_thread()
        self.workers.append(worker)
        self.started_checks.put(app.id)
        self.releases[app.id].wait()
        return app.argv, app.working_directory, None

    def release_checks(self):
        checks = list(self.helper.checks.running.values())
        for release in self.releases.values():
            release.set()
        for check in checks:
            self.assertTrue(check.done.wait(5))
        for worker in self.workers:
            worker.join(5)
            self.assertFalse(worker.is_alive())

    def open_app(self, conn, index, request_id=None):
        app_id = self.programs[index]
        return self.call(self.helper, conn, 'open_app', request_id or app_id, app_id=app_id)

    def start_check(self, conn, index):
        self.assertIsNone(self.open_app(conn, index))
        self.assertEqual(self.started_checks.get(timeout=5), self.programs[index])

    def assert_busy(self, conn, index):
        answer = self.open_app(conn, index)
        self.assertIsNotNone(answer, 'a refused launch must answer immediately')
        self.assertEqual((answer['ok'], answer['state'], answer['error'], answer['reason']),
                         (False, 'failed', 'unavailable', 'checks_busy'))

    def test_views_share_three_slots_and_the_desktop_can_open_in_the_fourth(self):
        views = [self.view(self.helper, f'view-{index}') for index in range(shell.MAX_CHECKS)]
        for index, view in enumerate(views[:-1]):
            self.start_check(view, index)
        self.assert_busy(views[-1], -2)
        self.start_check(self.desktop_conn, -1)
        self.assertEqual(sum(worker.is_alive() for worker in self.workers), shell.MAX_CHECKS)

        # A full pool still accepts joins from either role, in either direction.
        self.assertIsNone(self.open_app(views[-1], -1, 'join-desktop'))
        self.assertIsNone(self.open_app(self.desktop_conn, 0, 'join-view'))
        self.assertIs(self.helper.checking[views[-1].client, 'join-desktop']['check'],
                      self.helper.checking[self.desktop_conn.client, self.programs[-1]]['check'])
        self.assertIs(self.helper.checking[self.desktop_conn.client, 'join-view']['check'],
                      self.helper.checking[views[0].client, self.programs[0]]['check'])
        self.assertEqual(len(self.helper.checks.running), shell.MAX_CHECKS)

        desktop_check = self.helper.checking[self.desktop_conn.client, self.programs[-1]]['check']
        self.releases[self.programs[-1]].set()
        self.assertTrue(desktop_check.done.wait(5))
        self.helper.tick()
        for conn, request_id in ((self.desktop_conn, self.programs[-1]), (views[-1], 'join-desktop')):
            answer = next(message for message in conn.sent if message.get('id') == request_id)
            self.assertEqual((answer['ok'], answer['state']), (True, 'starting'))
        self.assertEqual(len(self.helper.checks.running), shell.MAX_CHECKS - 1)

    def test_desktop_can_fill_all_four_slots(self):
        for index in range(shell.MAX_CHECKS):
            self.start_check(self.desktop_conn, index)
        self.assert_busy(self.desktop_conn, -1)
        self.assertEqual(sum(worker.is_alive() for worker in self.workers), shell.MAX_CHECKS)
        self.assertEqual(len(self.helper.checks.running), shell.MAX_CHECKS)

    def test_joining_a_desktop_check_does_not_spend_a_view_slot(self):
        view = self.view(self.helper)
        self.start_check(self.desktop_conn, 0)
        self.assertIsNone(self.open_app(view, 0, 'join-desktop'))
        for index in range(1, shell.MAX_CHECKS):
            self.start_check(view, index)
        self.assertEqual(len(self.helper.checks.running), shell.MAX_CHECKS)
