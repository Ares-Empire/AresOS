"""Package 30, security review 1 (step A): each fix with a test that fails without it."""
import base64
import json
import os
import pathlib
import struct
import sys
import tempfile
import threading
import time
import unittest
import zlib
from unittest import mock

from test_aresos_shell import shell, Base, Conn, REGISTRY, INSTANCE, NONCE, ALL
from test_aresos_shell_icons import IconBase, PNG, SVG, NORMAL


def picture_bomb(side=16000):
    """A small SVG whose embedded 1-bit PNG decodes to side x side pixels (16000: about 1 GB as RGBA)."""
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data))
    rows = zlib.compress(bytes(side * (1 + (side + 7) // 8)), 9)
    png = (shell.PNG_SIGNATURE + chunk(b'IHDR', struct.pack('>IIBBBBB', side, side, 1, 0, 0, 0, 0))
           + chunk(b'IDAT', rows) + chunk(b'IEND', b''))
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><image width="8" height="8" '
            f'href="data:image/png;base64,{base64.b64encode(png).decode()}"/></svg>').encode()


def svg(body, extra=''):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"{extra} '
            f'width="8" height="8">{body}</svg>').encode()


REFUSED = {
    'local image': svg('<image href="#shape" width="8" height="8"/>'),
    'data image': svg('<image xlink:href="data:image/png;base64,iVBORw0KGgo=" width="8" height="8"/>'),
    'file image': svg('<image href="file:///etc/hostname" width="8" height="8"/>'),
    'feImage': svg('<filter id="f"><feImage href="picture.png"/></filter><rect filter="url(#f)"/>'),
    'foreignObject': svg('<foreignObject><div xmlns="http://www.w3.org/1999/xhtml">x</div></foreignObject>'),
    'external use': svg('<use href="other.svg#shape"/>'),
    'data use': svg('<use xlink:href="data:image/svg+xml;base64,PHN2Zy8+#a"/>'),
    'external paint': svg('<rect width="8" height="8" fill="url(other.svg#gradient)"/>'),
    'data paint in style': svg('<rect width="8" height="8" style="fill:url(\'data:image/png;base64,AAAA\')"/>'),
    'css escape': svg('<rect width="8" height="8" fill="u\\72l(picture.png)"/>'),
    'css import': svg('<style>@import url(theme.css);</style><rect width="8" height="8"/>'),
    'css url in style': svg('<style>rect { fill: url(picture.png) }</style><rect width="8" height="8"/>'),
    'stylesheet instruction': b'<?xml-stylesheet href="theme.css"?>' + svg('<rect width="8" height="8"/>'),
    'xinclude': svg('<xi:include href="other.svg" parse="xml"/>', ' xmlns:xi="http://www.w3.org/2001/XInclude"'),
    'external link': svg('<a href="https://example.invalid/"><rect width="8" height="8"/></a>'),
    'unbound prefix': b'<svg xmlns="http://www.w3.org/2000/svg"><x:image/></svg>',
}

ALLOWED = {
    'fixture': SVG,
    'local paint and reuse': svg('<defs><linearGradient id="g"><stop offset="0" stop-color="red"/></linearGradient>'
                                 '<rect id="r" width="4" height="4"/></defs><rect fill="url(#g)" width="8" '
                                 'height="8"/><use href="#r"/><use xlink:href="#r" x="4"/>'),
    'local style': svg('<style>rect { fill: url( "#g" ) }</style><rect width="8" height="8" style="fill:url(#g)"/>'),
    'editor metadata': svg('<metadata><x:path xmlns:x="urn:example">C:\\Users\\icon.svg</x:path></metadata>'
                           '<rect width="8" height="8" x:export-filename="C:\\icons\\app.png"/>',
                           ' xmlns:x="urn:example"'),
}


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
                time.sleep(0.5)
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
            deadline = time.monotonic() + 2.5
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
        # A scan takes over 0.5 seconds; on the loop, every due tick would wait for it.
        self.assertLess(slowest, 0.25)
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
        # Every program counts as installed here: the legacy list carries availability since review fixes 2, and
        # the registry's three programs are not installed on every machine that runs this test (GitHub's runner).
        discovery = shell.Discovery(shell.Catalogue(str(REGISTRY), entry_dirs=self.folders,
                                                    executable=lambda path: True))
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


class ConverterMemoryTest(IconBase):
    """FIX 2: an operating-system memory ceiling for the converter and everything it starts."""

    def test_the_converter_and_everything_it_starts_run_under_an_address_space_limit(self):
        script = ('import json, mmap, os, resource, sys\n'
                  'def probe(who):\n'
                  '    try:\n'
                  f'        mmap.mmap(-1, {2 * shell.ICON_ADDRESS_SPACE})\n'
                  '        mapped = True\n'
                  '    except OSError:\n'
                  '        mapped = False\n'
                  '    limit = resource.getrlimit(resource.RLIMIT_AS)[0]\n'
                  '    os.write(1, (json.dumps([who, limit, mapped]) + "\\n").encode())\n'
                  'pid = os.fork()\n'
                  'if pid == 0:\n'
                  '    probe("child")\n'
                  '    os._exit(0)\n'
                  'os.waitpid(pid, 0)\n'
                  'probe("converter")\n')
        output = self.cache.run([sys.executable, '-c', script])
        rows = sorted(json.loads(line) for line in output.decode().splitlines())
        self.assertEqual(rows, [['child', shell.ICON_ADDRESS_SPACE, False],
                                ['converter', shell.ICON_ADDRESS_SPACE, False]])

    def test_the_limit_is_set_by_prlimit_before_the_sandboxed_converter_starts(self):
        self.cache.bwrap = sys.executable  # any executable: hosted Ubuntu may lack bubblewrap
        sandboxed = self.cache.command('/work', 'png:/input/icon', 'PNG32:-')
        with mock.patch.object(shell.subprocess, 'Popen', side_effect=OSError('stop here')) as popen:
            with self.assertRaises(OSError):
                self.cache.run(sandboxed)
        self.assertEqual(popen.call_args.args[0],
                         ['/usr/bin/prlimit', f'--as={shell.ICON_ADDRESS_SPACE}', '--', *sandboxed])
        self.assertIn('--unshare-all', sandboxed)

    def test_a_small_svg_embedding_a_large_compressed_picture_is_refused_before_conversion(self):
        bomb = picture_bomb()
        self.assertLess(len(bomb), 64 * 1024)
        self.assertEqual(shell.sniff_icon(bomb), 'svg')
        source = self.write(self.root / 'bomb.svg', bomb)
        with mock.patch.object(self.cache, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'image'):
                self.cache.convert(str(source))
            # The refusal is remembered for this version of the file: it is not parsed again every pass.
            self.assertIsNone(self.cache.convert(str(source)))
            run.assert_not_called()

    def test_each_construct_that_refers_to_a_picture_is_refused_before_conversion(self):
        for name, raw in REFUSED.items():
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    shell.drawn_svg(raw)
                source = self.write(self.root / (name.replace(' ', '-') + '.svg'), raw)
                with mock.patch.object(self.cache, 'run') as run:
                    with self.assertRaises(ValueError):
                        self.cache.convert(str(source))
                    run.assert_not_called()

    def test_drawn_shapes_with_local_references_still_convert(self):
        for name, raw in ALLOWED.items():
            with self.subTest(name=name):
                shell.drawn_svg(raw)
                source = self.write(self.root / (name.replace(' ', '-') + '.svg'), raw)
                self.cache.svg_checked = True
                with mock.patch.object(self.cache, 'run', return_value=NORMAL) as run:
                    self.assertIsNotNone(self.cache.convert(str(source)))
                    run.assert_called_once()


class IconBudgetTest(IconBase):
    """FIX 3: a total budget in files and bytes; unused and older pictures are removed."""

    def files(self):
        return sorted(os.listdir(self.cache.directory))

    def test_changing_one_icons_time_a_thousand_times_leaves_one_picture(self):
        source = self.write(self.root / 'source')
        info = source.stat()
        with mock.patch.object(self.cache, 'run', return_value=NORMAL) as run, mock.patch.object(shell.os, 'fsync'):
            for n in range(1000):
                os.utime(source, ns=(info.st_atime_ns, info.st_mtime_ns + n + 1))
                path = self.cache.convert(str(source))
        self.assertEqual(run.call_count, 1000)
        self.assertEqual(self.files(), [os.path.basename(path)])

    def test_pictures_of_programs_no_longer_listed_and_leftovers_are_removed_after_a_complete_pass(self):
        sources = {key: self.write(self.root / key, PNG + key.encode()) for key in ('one', 'two', 'three')}
        apps = {key: shell.App(key, key.title(), icon_name=str(path)) for key, path in sources.items()}
        self.cache.prepare()
        stray = pathlib.Path(self.cache.directory)
        (stray / ('0' * 64 + '.png')).write_bytes(NORMAL)
        (stray / '.icon-interrupted').write_bytes(b'partial')
        (stray / '.convert-interrupted').mkdir()
        (stray / '.convert-interrupted/input').write_bytes(b'copy')
        (stray / 'unrelated.txt').write_bytes(b'not ours')

        def settle(predicate):
            deadline = time.monotonic() + 5
            while not predicate(self.files()) and time.monotonic() < deadline:
                time.sleep(0.01)
            return self.files()

        with mock.patch.object(self.cache, 'run', return_value=NORMAL):
            self.cache.request(apps, 'first')
            # Three pictures made, and the leftovers of an earlier run removed once the pass completed.
            first = settle(lambda names: len(names) == 4 and '.icon-interrupted' not in names
                           and '0' * 64 + '.png' not in names and '.convert-interrupted' not in names)
            current, _ = self.cache.take(apps, 'first')
            self.assertEqual(sorted([os.path.basename(app.icon) for app in current.values()] + ['unrelated.txt']),
                             first)
            self.cache.request({'one': apps['one']}, 'second')
            remaining = settle(lambda names: len(names) == 2)
        self.assertEqual(remaining, sorted([os.path.basename(current['one'].icon), 'unrelated.txt']))

    def test_a_full_cache_keeps_the_fallback_look_and_says_so_once(self):
        sources = [self.write(self.root / f'source{n}', PNG + bytes([n])) for n in range(4)]
        with mock.patch.object(shell, 'ICON_CACHE_FILES', 2), mock.patch.object(shell.LOG, 'disabled', False), \
                mock.patch.object(self.cache, 'run', return_value=NORMAL) as run, \
                self.assertLogs(shell.LOG, level='WARNING') as logs:
            self.assertIsNotNone(self.cache.convert(str(sources[0])))
            self.assertIsNotNone(self.cache.convert(str(sources[1])))
            self.assertIsNone(self.cache.convert(str(sources[2])))
            self.assertIsNone(self.cache.convert(str(sources[3])))
            self.assertEqual(run.call_count, 2)
        self.assertEqual(len(self.files()), 2)
        self.assertEqual(len(logs.output), 1)
        self.assertIn('budget', logs.output[0])
        # Not remembered as a failure: once there is room again, the picture is made.
        os.unlink(os.path.join(self.cache.directory, self.files()[0]))
        with mock.patch.object(shell, 'ICON_CACHE_FILES', 2), mock.patch.object(self.cache, 'run', return_value=NORMAL):
            self.assertIsNotNone(self.cache.convert(str(sources[2])))

    def test_the_byte_budget_is_checked_with_the_real_picture_size_before_writing(self):
        source = self.write(self.root / 'source')
        with mock.patch.object(shell, 'ICON_CACHE_BYTES', len(NORMAL) - 1), \
                mock.patch.object(self.cache, 'run', return_value=NORMAL) as run:
            self.assertIsNone(self.cache.convert(str(source)))
            run.assert_called_once()
        self.assertEqual(self.files(), [])


class IconFolderLinkTest(IconBase):
    """FIX 5: icon theme folders are checked before they are listed; Flatpak icons link into deployments."""

    def test_a_theme_folder_that_links_out_is_never_listed(self):
        outside = self.root.resolve() / 'outside-theme'
        self.write(outside / '256x256/apps/app.png')
        (self.folders[0] / 'hicolor').symlink_to(outside, target_is_directory=True)
        (self.folders[1] / 'breeze').mkdir()
        (self.folders[1] / 'breeze/48x48').symlink_to(outside / '256x256', target_is_directory=True)
        listed, original = [], os.scandir

        def scandir(path='.'):
            listed.append(os.readlink(f'/proc/self/fd/{path}') if isinstance(path, int) else os.path.realpath(path))
            return original(path)

        with mock.patch.object(shell.os, 'scandir', side_effect=scandir):
            self.assertIsNone(self.resolve())
        self.assertTrue(listed)
        self.assertEqual([path for path in listed if path.startswith(str(outside))], [])

    def test_a_flatpak_export_icon_is_found_in_its_deployment_and_converted(self):
        exports = flatpak_layout(self.root / '.local/share/flatpak', 'org.example.App', icon=PNG)
        cache = shell.IconCache(environ={'HOME': str(self.root), 'XDG_CACHE_HOME': str(self.root / 'cache')},
                                directories=[self.folders[0], exports / 'icons'])
        self.addCleanup(cache.stop)
        deployed = (self.root / '.local/share/flatpak/app/org.example.App/current/active/export/share'
                    '/icons/hicolor/128x128/apps/org.example.App.png')
        self.assertEqual(shell.resolve_icon('org.example.App', cache.directories, cache.deployments),
                         os.path.realpath(deployed))
        app = shell.App('example', 'Example', icon_name='org.example.App')
        with mock.patch.object(cache, 'run', return_value=NORMAL):
            cache.request({'example': app}, 'base')
            deadline = time.monotonic() + 5
            while cache.results.empty() and time.monotonic() < deadline:
                time.sleep(0.01)
            current, _ = cache.take({'example': app}, 'base')
        self.assertTrue(os.path.isfile(current['example'].icon))

    def test_a_named_icon_is_read_only_inside_its_folders_but_an_absolute_icon_path_as_written(self):
        outside = self.write(self.root / 'outside.png')
        link = self.folders[0] / 'app.png'
        link.symlink_to(outside)
        with mock.patch.object(self.cache, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'outside'):
                self.cache.convert(str(link), (str(self.folders[0].resolve()),))
            run.assert_not_called()
        with mock.patch.object(self.cache, 'run', return_value=NORMAL):
            self.assertIsNotNone(self.cache.convert(str(link)))


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
