"""Package 30, security review 1 (step A): each fix with a test that fails without it."""
import os
import pathlib
import tempfile
import threading
import time
import unittest
from unittest import mock

from test_aresos_shell import shell, Base, Conn, REGISTRY, INSTANCE, NONCE, ALL


class HardeningBase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name).resolve()
        self.registry = self.root / 'registry'
        self.registry.mkdir()
        self.folders = [self.root / str(n) for n in range(5)]
        for folder in self.folders:
            folder.mkdir()
        self.deployment = self.root / 'flatpak/app'
        self.logging = mock.patch.object(shell.LOG, 'disabled', False)
        self.logging.start()
        self.addCleanup(self.logging.stop)

    def write(self, path, text=None, **values):
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if text is None:
            fields = {'Type': 'Application', 'Name': 'Test Program', 'Exec': '/usr/bin/tool'}
            fields.update(values)
            text = '[Desktop Entry]\n' + ''.join(f'{key}={value}\n' for key, value in fields.items())
        path.write_bytes(text if isinstance(text, bytes) else text.encode())
        return path

    def catalogue(self):
        return shell.Catalogue(str(self.registry), entry_dirs=self.folders, executable=lambda path: True,
                               deployments=[self.deployment])


class DiscoveryBoundsTest(HardeningBase):
    """FIX 1: every entry looked at counts; over a bound the last good catalogue stays, logged once."""

    def test_ten_thousand_hidden_entries_end_the_scan_at_its_bound_and_keep_the_last_good_catalogue(self):
        self.write(self.folders[0] / 'good.desktop')
        catalogue = self.catalogue()
        self.assertTrue(catalogue.refresh(0))
        good = (catalogue.apps, catalogue.revision, catalogue.legacy)
        for n in range(10000):
            (self.folders[0] / f'hidden{n:05}.desktop').write_bytes(b'[Desktop Entry]\nHidden=true\n')
        with mock.patch.object(shell, 'read_desktop_entry', wraps=shell.read_desktop_entry) as reads, \
                mock.patch.object(shell, 'walk_folder', wraps=shell.walk_folder), \
                self.assertLogs(shell.LOG, level='WARNING') as logs:
            self.assertFalse(catalogue.refresh(shell.CATALOGUE_CHECK))
            self.assertFalse(catalogue.refresh(2 * shell.CATALOGUE_CHECK))
        self.assertEqual(reads.call_count, 0)
        self.assertEqual((catalogue.apps, catalogue.revision, catalogue.legacy), good)
        self.assertEqual(len(logs.output), 1)
        self.assertIn(f'more than {shell.SCAN_ENTRIES} folder entries', logs.output[0])
        for path in self.folders[0].glob('hidden*'):
            path.unlink()
        self.write(self.folders[0] / 'after.desktop')
        self.assertTrue(catalogue.refresh(3 * shell.CATALOGUE_CHECK))
        self.assertEqual(set(catalogue.apps), {'good', 'after'})
        self.assertFalse(catalogue.limited)

    def test_hard_links_to_one_large_malformed_entry_are_refused_before_any_is_read(self):
        self.write(self.folders[0] / 'good.desktop')
        catalogue = self.catalogue()
        self.assertTrue(catalogue.refresh(0))
        good = catalogue.apps
        large = self.write(self.root / 'large.desktop',
                           b'[Desktop Entry]\n' + b'no equals sign\n' * (shell.MAX_DESKTOP_ENTRY // 15 - 2))
        self.assertLessEqual(large.stat().st_size, shell.MAX_DESKTOP_ENTRY)
        links = shell.SCAN_BYTES // large.stat().st_size + 8
        for n in range(links):
            os.link(large, self.folders[1] / f'link{n:03}.desktop')
        with mock.patch.object(shell, 'read_desktop_entry', wraps=shell.read_desktop_entry) as reads, \
                self.assertLogs(shell.LOG, level='WARNING') as logs:
            self.assertFalse(catalogue.refresh(shell.CATALOGUE_CHECK))
            self.assertFalse(catalogue.refresh(2 * shell.CATALOGUE_CHECK))
        self.assertEqual(reads.call_count, 0)
        self.assertIs(catalogue.apps, good)
        self.assertEqual(len(logs.output), 1)
        self.assertIn(f'more than {shell.SCAN_BYTES} bytes', logs.output[0])

    def test_bytes_are_counted_as_they_are_read_too(self):
        path = self.write(self.folders[0] / 'good.desktop')
        budget = shell.ScanBudget()
        budget.bytes = shell.SCAN_BYTES - path.stat().st_size + 1
        with mock.patch.object(shell.os, 'read', wraps=os.read) as read:
            with self.assertRaises(shell.ScanLimit):
                shell.read_desktop_entry(path, budget)
        read.assert_not_called()
        self.assertEqual(budget.bytes, shell.SCAN_BYTES + 1)

    def test_folders_depth_and_time_are_bounded(self):
        deep = self.folders[0].joinpath(*['d'] * (shell.SCAN_DEPTH + 2))
        self.write(deep / 'deep.desktop')
        with self.assertRaises(shell.ScanLimit):
            list(shell.desktop_files([self.folders[0]]))
        now = [0.0]
        budget = shell.ScanBudget(clock=lambda: now[0])
        budget.entry()
        now[0] = shell.SCAN_SECONDS + 0.1
        with self.assertRaisesRegex(shell.ScanLimit, 'seconds'):
            budget.entry()
        with self.assertRaisesRegex(shell.ScanLimit, 'seconds'):
            budget.time()

    def test_a_linked_subfolder_is_never_entered_even_if_swapped_in_after_listing(self):
        outside = self.root / 'outside'
        self.write(outside / 'secret.desktop')
        (self.folders[0] / 'sub').mkdir()
        original = os.open

        def swap(path, flags, *args, **kwargs):
            if path == 'sub' and kwargs.get('dir_fd') is not None:
                (self.folders[0] / 'sub').rmdir()
                (self.folders[0] / 'sub').symlink_to(outside, target_is_directory=True)
            return original(path, flags, *args, **kwargs)

        with mock.patch.object(shell.os, 'open', side_effect=swap):
            self.assertEqual(list(shell.desktop_files([self.folders[0]])), [])


class DiscoveryOffTheLoopTest(HardeningBase, Base):
    """FIX 1: production scans run on Discovery's thread; the helper keeps answering meanwhile."""

    def setUp(self):
        HardeningBase.setUp(self)
        Base.setUp(self)
        self.registry = REGISTRY

    def helper_with(self, catalogue):
        icons = mock.Mock()
        icons.take.side_effect = lambda apps, revision: (apps, shell.icons_revision(apps, revision))
        helper = shell.Helper(str(REGISTRY), INSTANCE, NONCE, self.journal, registry=(catalogue.apps,
                              catalogue.revision), catalogue=catalogue, icons=icons, clock=self.clock,
                              executable=lambda path: True, launcher=self.launcher())
        self.addCleanup(helper.watcher.stop)
        return helper, self.connect11(helper)

    def connect11(self, helper):
        conn = Conn()
        helper.connected(conn)
        reply = self.request(helper, conn, 'hello', 'h-1', major=1, minor=1, capabilities=ALL,
                             requires=['list_apps', 'open_app'], instance=INSTANCE, nonce=NONCE)
        self.assertEqual(reply['minor'], 1)
        return conn

    def test_build_scans_on_its_own_thread_and_a_blocked_scan_never_stalls_the_helper(self):
        # build() checks executables for real.
        self.write(self.folders[0] / 'good.desktop', Exec='/usr/bin/true')
        release, entered = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        original = shell.Catalogue.scan
        calls = []

        def scan(catalogue):
            calls.append(threading.current_thread().name)
            if len(calls) > 1:
                entered.set()
                release.wait(10)
            return original(catalogue)

        with mock.patch.object(shell, 'desktop_directories', return_value=tuple(map(str, self.folders))), \
                mock.patch.object(shell, 'IconCache', return_value=mock.Mock(**{
                    'take.side_effect': lambda apps, revision: (apps, shell.icons_revision(apps, revision))})), \
                mock.patch.object(shell.Catalogue, 'scan', scan):
            helper, _ = shell.build(str(REGISTRY), INSTANCE, NONCE, self.journal, launcher=self.launcher(),
                                    clock=self.clock, connect=mock.Mock(side_effect=OSError('no compositor')),
                                    environ={'HOME': str(self.root)})
            self.addCleanup(helper.catalogue.stop)
            self.addCleanup(helper.watcher.stop)
            self.assertIsInstance(helper.catalogue, shell.Discovery)
            self.assertEqual(calls, ['aresos-discovery'])
            self.assertIn('good', helper.apps)
            conn = self.connect11(helper)
            self.write(self.folders[0] / 'later.desktop', Exec='/usr/bin/true')
            self.now[0] += shell.CATALOGUE_CHECK
            helper.tick()
            self.assertTrue(entered.wait(5))
            for _ in range(5):
                start = time.monotonic()
                self.now[0] += shell.CATALOGUE_CHECK
                helper.tick()
                reply = self.request(helper, conn, 'list_apps')
                self.assertLess(time.monotonic() - start, 0.2)
                self.assertTrue(reply['ok'])
            self.assertEqual(len(calls), 2)
            self.assertNotIn('later', helper.apps)
            release.set()
            deadline = time.monotonic() + 5
            while 'later' not in helper.apps and time.monotonic() < deadline:
                time.sleep(0.01)
                helper.tick()
            self.assertIn('later', helper.apps)
            self.assertTrue(all(name == 'aresos-discovery' for name in calls))

    def test_a_folder_that_keeps_changing_is_rescanned_at_most_every_few_seconds_and_never_on_the_loop(self):
        self.write(self.folders[0] / 'good.desktop')
        discovery = shell.Discovery(self.catalogue())
        self.addCleanup(discovery.stop)
        original = shell.Catalogue.scan
        running, overlap, scans = [0], [], []

        def slow_scan(catalogue):
            running[0] += 1
            overlap.append(running[0])
            scans.append(threading.current_thread().name)
            try:
                time.sleep(0.3)
                return original(catalogue)
            finally:
                running[0] -= 1

        stop = threading.Event()
        self.addCleanup(stop.set)

        def churn():
            n = 0
            while not stop.is_set():
                path = self.folders[2] / f'churn{n % 50}.desktop'
                if path.exists():
                    path.unlink()
                else:
                    self.write(path, Name=f'Churn {n}')
                n += 1
                time.sleep(0.001)

        with mock.patch.object(shell.Catalogue, 'scan', slow_scan):
            discovery.start(self.clock())
            helper, conn = self.helper_with(discovery)
            writer = threading.Thread(target=churn)
            writer.start()
            ticks, slowest = 0, 0.0
            deadline = time.monotonic() + 1.5
            while time.monotonic() < deadline:
                self.now[0] += 1.0
                start = time.monotonic()
                helper.tick()
                reply = self.request(helper, conn, 'list_apps')
                slowest = max(slowest, time.monotonic() - start)
                ticks += 1
                self.assertIn('good', {row['id'] for row in reply['apps']})
                time.sleep(0.02)
            stop.set()
            writer.join()
        self.assertLess(slowest, 0.15)
        self.assertEqual(max(overlap), 1)
        self.assertGreaterEqual(len(scans), 3)
        # One request per CATALOGUE_CHECK of helper time at most, and only while no scan runs.
        self.assertLessEqual(len(scans), ticks * 1.0 / shell.CATALOGUE_CHECK + 2)
        self.assertTrue(all(name == 'aresos-discovery' for name in scans))

    def test_a_failing_scan_keeps_the_last_good_catalogue_and_the_helper_answering(self):
        self.write(self.folders[0] / 'good.desktop')
        discovery = shell.Discovery(self.catalogue())
        self.addCleanup(discovery.stop)
        discovery.start(self.clock())
        self.assertIn('good', discovery.apps)
        helper, conn = self.helper_with(discovery)
        with mock.patch.object(shell.Catalogue, 'scan', side_effect=RuntimeError('broken')), \
                self.assertLogs(shell.LOG, level='ERROR') as logs:
            discovery.scanned.clear()
            self.now[0] += shell.CATALOGUE_CHECK
            helper.tick()
            self.assertTrue(discovery.scanned.wait(5))
            helper.tick()
        self.assertIn('scan failed', logs.output[0])
        self.assertIn('good', {row['id'] for row in self.request(helper, conn, 'list_apps')['apps']})

    def test_before_the_first_scan_the_registry_alone_is_in_force_with_the_1_0_revision(self):
        discovery = shell.Discovery(shell.Catalogue(str(REGISTRY), entry_dirs=self.folders))
        apps, revision = shell.load_registry(str(REGISTRY))
        self.assertEqual(set(discovery.apps), set(apps))
        self.assertEqual(discovery.legacy, (apps, revision))
        self.assertIsNone(discovery.thread)


class DesktopLinkTest(HardeningBase):
    """FIX 5: a desktop-file link must resolve inside the application folders or a Flatpak deployment."""

    def test_a_link_to_a_file_outside_is_skipped_with_one_log_line_and_never_read(self):
        outside = self.write(self.root / 'outside/evil.desktop', Name='Evil')
        (self.folders[0] / 'evil.desktop').symlink_to(outside)
        self.write(self.folders[0] / 'good.desktop')
        with mock.patch.object(shell.os, 'fdopen', wraps=os.fdopen) as fdopen, \
                self.assertLogs(shell.LOG, level='WARNING') as logs:
            catalogue = self.catalogue()
            catalogue.refresh(0)
        self.assertEqual(set(catalogue.apps), {'good'})
        self.assertEqual(fdopen.call_count, 1)
        self.assertEqual(len(logs.output), 1)
        self.assertIn('evil.desktop', logs.output[0])
        self.assertIn('outside its folders', logs.output[0])

    def test_links_inside_the_application_folders_are_followed(self):
        target = self.write(self.folders[4] / 'nested/real.program', Name='Linked')
        (self.folders[0] / 'linked.desktop').symlink_to(target)
        catalogue = self.catalogue()
        catalogue.refresh(0)
        self.assertEqual(catalogue.apps['linked'].name, 'Linked')

    def test_realistic_flatpak_export_layout_is_listed(self):
        exports = flatpak_layout(self.deployment.parent, 'org.example.App')
        catalogue = shell.Catalogue(str(self.registry), entry_dirs=[self.folders[0], exports / 'applications'],
                                    executable=lambda path: True, deployments=[self.deployment])
        catalogue.refresh(0)
        app = catalogue.apps['org-example-app']
        self.assertEqual((app.name, app.source, app.exec_name), ('Example', 'flatpak-user', 'org.example.App'))
        self.assertEqual(app.argv, ('/usr/bin/flatpak', 'run', 'org.example.App'))

    def test_the_file_read_is_the_file_checked_even_if_the_link_changes_after_the_check(self):
        inside = self.write(self.folders[0] / 'real.target', b'inside')
        outside = self.write(self.root / 'outside.target', b'outside')
        link = self.folders[0] / 'link.desktop'
        link.symlink_to(inside)
        original = os.readlink

        def readlink(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            if str(path).startswith('/proc/self/fd/'):
                link.unlink()
                link.symlink_to(outside)
            return value

        with mock.patch.object(shell.os, 'readlink', side_effect=readlink):
            descriptor = shell.open_confined(str(link), (str(self.folders[0]),))
        with os.fdopen(descriptor, 'rb') as handle:
            self.assertEqual(handle.read(), b'inside')
        self.assertEqual(os.readlink(link), str(outside))

    def test_a_link_to_a_fifo_or_device_outside_is_refused_without_opening_it(self):
        fifo = self.root / 'outside.fifo'
        os.mkfifo(fifo)
        (self.folders[0] / 'pipe.desktop').symlink_to(fifo)
        (self.folders[0] / 'null.desktop').symlink_to('/dev/null')
        for name in ('pipe.desktop', 'null.desktop'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'outside'):
                shell.open_confined(str(self.folders[0] / name), (str(self.folders[0]),))
        with self.assertRaisesRegex(ValueError, 'regular'):
            shell.open_confined(str(fifo), (str(self.root),))


def flatpak_layout(flatpak, app_id, icon=None):
    """A Flatpak installation as `flatpak install` leaves it: exports link into the active deployment."""
    commit = flatpak / f'app/{app_id}/x86_64/stable/0123456789abcdef'
    commit.mkdir(parents=True)
    (commit.parent / 'active').symlink_to(commit.name)
    (flatpak / f'app/{app_id}/current').symlink_to('x86_64/stable')
    exported = commit / 'export/share'
    (exported / 'applications').mkdir(parents=True)
    (exported / 'applications' / f'{app_id}.desktop').write_text(
        f'[Desktop Entry]\nType=Application\nName=Example\nExec=/usr/bin/flatpak run {app_id}\nIcon={app_id}\n'
        f'X-Flatpak={app_id}\n')
    exports = flatpak / 'exports/share'
    (exports / 'applications').mkdir(parents=True)
    (exports / 'applications' / f'{app_id}.desktop').symlink_to(
        f'../../../app/{app_id}/current/active/export/share/applications/{app_id}.desktop')
    if icon is not None:
        (exported / 'icons/hicolor/128x128/apps').mkdir(parents=True)
        (exported / f'icons/hicolor/128x128/apps/{app_id}.png').write_bytes(icon)
        (exports / 'icons/hicolor/128x128/apps').mkdir(parents=True)
        (exports / f'icons/hicolor/128x128/apps/{app_id}.png').symlink_to(
            f'../../../../../../app/{app_id}/current/active/export/share/icons/hicolor/128x128/apps/{app_id}.png')
    return exports


if __name__ == '__main__':
    unittest.main()
