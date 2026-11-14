"""Package 30 A6: drawn icons, hostile sources, and the real sandboxed converter."""
import dataclasses
import hashlib
import os
import pathlib
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zlib
from unittest import mock

from test_aresos_shell import shell, ROOT, REGISTRY, Base

FIXTURES = ROOT / 'os/tests/fixtures/installed-programs'
PNG = (FIXTURES / 'drawn.png').read_bytes()
SVG = (FIXTURES / 'drawn.svg').read_bytes()
# Written for these tests in the form of Breeze's own index.theme (review fixes 3).
BREEZE_INDEX = (FIXTURES / 'breeze-index.theme').read_bytes()


def normalized_fixture():
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data))
    return (shell.PNG_SIGNATURE + chunk(b'IHDR', struct.pack('>IIBBBBB', 128, 128, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(bytes(128 * 513))) + chunk(b'IEND', b''))


NORMAL = normalized_fixture()


def pixels(raw):
    """Read our normalized PNGs without another image decoder; check CRCs and reconstruct scanlines."""
    assert shell.IconCache.normalized(raw)
    offset, compressed, tags = 8, bytearray(), []
    while offset < len(raw):
        length = struct.unpack('>I', raw[offset:offset + 4])[0]
        tag = raw[offset + 4:offset + 8]
        data = raw[offset + 8:offset + 8 + length]
        assert zlib.crc32(tag + data) == struct.unpack('>I', raw[offset + 8 + length:offset + 12 + length])[0]
        tags.append(tag)
        if tag == b'IDAT':
            compressed.extend(data)
        offset += length + 12
    assert tags[0] == b'IHDR' and tags[-1] == b'IEND' and offset == len(raw)
    scanlines = zlib.decompress(compressed)
    assert len(scanlines) == 128 * 513
    rows, previous = [], bytearray(512)
    for y in range(128):
        mode = scanlines[y * 513]
        row = bytearray(scanlines[y * 513 + 1:(y + 1) * 513])
        for x in range(512):
            a, b, c = row[x - 4] if x >= 4 else 0, previous[x], previous[x - 4] if x >= 4 else 0
            if mode == 0:
                prediction = 0
            elif mode == 1:
                prediction = a
            elif mode == 2:
                prediction = b
            elif mode == 3:
                prediction = (a + b) // 2
            elif mode == 4:
                p = a + b - c
                prediction = min((a, b, c), key=lambda n: abs(p - n))
            else:
                raise AssertionError('unknown PNG filter')
            row[x] = (row[x] + prediction) & 255
        rows.append([tuple(row[x:x + 4]) for x in range(0, 512, 4)])
        previous = row
    return rows


class IconBase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        self.folders = [self.root / str(n) for n in range(6)]
        for folder in self.folders:
            folder.mkdir()
        self.cache = shell.IconCache(environ={'HOME': str(self.root), 'XDG_CACHE_HOME': str(self.root / 'cache')},
                                     directories=self.folders)
        self.addCleanup(self.cache.stop)

    def write(self, path, raw=PNG):
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return path

    def themed(self, folder=0, theme='hicolor', size='128x128', name='app.png', raw=PNG, context='apps'):
        return self.write(self.folders[folder] / theme / size / context / name, raw)

    def resolve(self, name='app'):
        return shell.resolve_icon(name, self.folders)

    def index(self, folder=4, raw=BREEZE_INDEX, theme='breeze'):
        return self.write(self.folders[folder] / theme / 'index.theme', raw)

    def breeze(self, directory='apps/48', name='app.svg', raw=SVG, folder=4):
        """A picture where Breeze really keeps it (breeze/apps/48/); the root gets the fixture's index.theme unless it
        has one. Root 4 stands for /usr/share/icons."""
        if not (self.folders[folder] / 'breeze/index.theme').exists():
            self.index(folder)
        return self.write(self.folders[folder] / 'breeze' / directory / name, raw)


class IconLookupTest(IconBase):
    def test_folders_and_cache_default_and_absolute_xdg_override(self):
        self.assertEqual(shell.icon_directories({'HOME': '/test/home'}), (
            '/test/home/.local/share/icons', '/test/home/.local/share/flatpak/exports/share/icons',
            '/var/lib/flatpak/exports/share/icons', '/usr/local/share/icons',
            '/usr/share/icons', '/usr/share/pixmaps'))
        for value in ('', 'relative'):
            self.assertEqual(shell.icon_cache_directory({'HOME': '/test/home', 'XDG_CACHE_HOME': value}),
                             '/test/home/.cache/aresos/icons')
        self.assertEqual(shell.icon_cache_directory({'HOME': '/test/home', 'XDG_CACHE_HOME': '/test/cache'}),
                         '/test/cache/aresos/icons')

    def test_absolute_path_is_kept_as_written_even_outside_icon_folders(self):
        source = self.write(self.root / 'elsewhere.png')
        self.assertEqual(self.resolve(str(source)), str(source))

    def test_name_rejects_slash_dot_dot_nul_and_excessive_length(self):
        for name in ('../app', '../../x', 'app/file', 'app..x', '..', 'x\0y', 'x' * 256, ''):
            with self.subTest(name=name):
                self.assertIsNone(self.resolve(name))

    def test_theme_then_largest_raster_at_most_256_then_scalable(self):
        self.themed(1, size='512x512')
        self.themed(1, size='256x256')
        self.themed(0, size='128x128')
        self.themed(0, size='scalable', name='app.svg', raw=SVG)
        self.breeze('apps/64', 'app.png', PNG)
        self.assertEqual(self.resolve(), str(self.folders[1] / 'hicolor/256x256/apps/app.png'))
        (self.folders[1] / 'hicolor/256x256/apps/app.png').unlink()
        self.assertEqual(self.resolve(), str(self.folders[0] / 'hicolor/128x128/apps/app.png'))
        (self.folders[0] / 'hicolor/128x128/apps/app.png').unlink()
        self.assertEqual(self.resolve(), str(self.folders[0] / 'hicolor/scalable/apps/app.svg'))

    def test_roots_break_ties_and_breeze_is_the_second_theme(self):
        later = self.breeze(folder=5)
        self.assertEqual(self.resolve(), str(later))
        earlier = self.breeze(folder=0)
        self.assertEqual(self.resolve(), str(earlier))
        hicolor = self.themed(5, theme='hicolor', size='16x16')
        self.assertEqual(self.resolve(), str(hicolor))

    def test_flat_and_pixmap_fallback_extension_and_exact_name(self):
        for index in reversed(range(6)):
            target = self.write(self.folders[index] / 'app.png')
            self.assertEqual(self.resolve(), str(target))
            self.assertEqual(self.resolve('app.png'), str(target))
        target = self.write(self.folders[0] / 'vector.svg', SVG)
        self.assertEqual(self.resolve('vector'), str(target))
        self.assertEqual(self.resolve('vector.svg'), str(target))
        target = self.write(self.folders[0] / 'extensionless', PNG)
        self.assertEqual(self.resolve('extensionless'), str(target))

    def test_non_square_zero_and_over_1024_size_folders_are_not_selected(self):
        for size in ('256x128', '0x0', '2048x2048', '12345x12345'):
            self.themed(size=size)
        self.assertIsNone(self.resolve())

    def test_png_folders_over_256_serve_only_when_the_theme_has_nothing_else_the_smallest_first(self):
        huge = self.themed(4, size='1024x1024')
        self.assertEqual(self.resolve(), str(huge))
        large = self.themed(4, size='999x999')
        self.assertEqual(self.resolve(), str(large))
        # An SVG in a sized folder, skipped before review fixes 3, comes before them.
        svg = self.themed(4, size='48x48', name='app.svg', raw=SVG)
        self.assertEqual(self.resolve(), str(svg))
        png = self.themed(4, size='16x16')
        self.assertEqual(self.resolve(), str(png))

    def test_file_and_directory_symlinks_cannot_escape_any_icon_folder(self):
        outside = self.write(self.root / 'outside/app.png')
        (self.folders[0] / 'app.png').symlink_to(outside)
        (self.folders[0] / 'hicolor').symlink_to(self.root / 'outside-theme', target_is_directory=True)
        self.write(self.root / 'outside-theme/256x256/apps/app.png')
        self.assertIsNone(self.resolve())
        target = self.themed(1)
        self.assertEqual(self.resolve(), str(target))

    def test_file_symlink_within_the_same_icon_root_is_supported(self):
        target = self.write(self.folders[0] / 'real.png')
        (self.folders[0] / 'app.png').symlink_to(target)
        self.assertEqual(self.resolve(), str(target))

    def test_desktop_icon_is_internal_and_participates_in_discovery_revision(self):
        entries, registry = self.root / 'entries', self.root / 'registry'
        entries.mkdir()
        registry.mkdir()
        text = '[Desktop Entry]\nType=Application\nName=Drawn\nExec=/usr/bin/tool\nIcon='
        path = entries / 'drawn.desktop'
        path.write_text(text + 'first\n')
        apps, first = shell.load_catalogue(str(registry), entry_dirs=[entries], executable=lambda p: True)
        self.assertEqual(apps['drawn'].icon_name, 'first')
        self.assertIsNone(apps['drawn'].icon)
        path.write_text(text + 'second\n')
        self.assertNotEqual(shell.load_catalogue(str(registry), entry_dirs=[entries], executable=lambda p: True)[1], first)


class IconThemeIndexTest(IconBase):
    """Review fixes 3, point 2: a theme's own index.theme says where its pictures are, as Breeze needs."""

    def test_breeze_pictures_are_found_where_breeze_keeps_them(self):
        terminal = self.breeze(name='utilities-terminal.svg')
        self.assertEqual(self.resolve('utilities-terminal'), str(terminal))
        # The fixed layout alone does not know <context>/<size> folders: the index is what finds it.
        (self.folders[4] / 'breeze/index.theme').unlink()
        self.assertIsNone(self.resolve('utilities-terminal'))

    def test_svgs_come_from_scalable_folders_first_then_sized_ones_largest_first(self):
        scalable = self.breeze('apps/48')
        large = self.breeze('apps/64')
        small = self.breeze('apps/32')
        self.breeze('apps/16')
        self.assertEqual(self.resolve(), str(scalable))
        scalable.unlink()
        self.assertEqual(self.resolve(), str(large))
        large.unlink()
        self.assertEqual(self.resolve(), str(small))

    def test_pngs_by_size_come_before_svgs_whatever_the_folder_type(self):
        svg = self.breeze('apps/48')
        png = self.breeze('apps/32', 'app.png', PNG)
        self.assertEqual(self.resolve(), str(png))
        # A Scalable folder's PNGs rank by its Size too (hicolor's index calls 256x256/apps Scalable).
        larger = self.breeze('places/64', 'app.png', PNG)
        self.assertEqual(self.resolve(), str(larger))
        larger.unlink()
        png.unlink()
        self.assertEqual(self.resolve(), str(svg))

    def test_scaled_folders_and_folders_without_a_usable_size_are_left_out(self):
        self.breeze('apps/32@2x', 'app.png', PNG)
        self.assertIsNone(self.resolve())
        self.breeze('apps/48')
        for group in (b'Size=48\nScale=2', b'Size=48\nScale=0', b'Size=abc', b'Size=+48', b'Size=2048', b''):
            with self.subTest(group=group):
                self.index(raw=b'[Icon Theme]\nDirectories=apps/48\n[apps/48]\nType=Scalable\n' + group + b'\n')
                self.assertIsNone(self.resolve())
        self.index(raw=b'[Icon Theme]\nDirectories=apps/48\n[apps/48]\nType=Scalable\nSize=48\n')
        self.assertIsNotNone(self.resolve())

    def test_a_root_without_an_index_keeps_the_fixed_layout_and_the_first_index_speaks_for_all_roots(self):
        home = self.themed(0, theme='breeze', size='48x48')
        system = self.breeze('apps/48')
        self.assertEqual(self.resolve(), str(home))
        home.unlink()
        self.assertEqual(self.resolve(), str(system))
        # Root 3 comes first and has an index of its own: it speaks for root 4, whose own index lists apps/48.
        self.index(3, b'[Icon Theme]\nDirectories=apps/64\n[apps/64]\nSize=64\nType=Fixed\n')
        self.assertIsNone(self.resolve())
        listed = self.breeze('apps/64')
        self.assertEqual(self.resolve(), str(listed))

    def test_a_broken_or_oversized_index_leaves_the_theme_on_the_fixed_layout_with_one_log_line(self):
        fixed = self.themed(4, theme='breeze', size='48x48', name='other.png')
        self.breeze('apps/48')
        outside = self.write(self.root / 'outside/index.theme', BREEZE_INDEX)
        cases = {
            'huge': BREEZE_INDEX + b'#' * shell.ICON_INDEX_BYTES,
            'endless': b'[Icon Theme]\nDirectories=' + b','.join(
                b'apps/%d' % n for n in range(shell.ICON_INDEX_FOLDERS + 1)) + b'\n',
            'parent folder': b'[Icon Theme]\nDirectories=apps/48,../../outside\n[apps/48]\nSize=48\nType=Scalable\n',
            'absolute folder': b'[Icon Theme]\nDirectories=/outside\n[/outside]\nSize=48\n',
            'NUL': BREEZE_INDEX + b'\0',
            'group header': b'[Icon Theme\nDirectories=apps/48\n',
            'link out of the root': None,
            'FIFO': None,
        }
        for case, raw in cases.items():
            with self.subTest(case=case):
                index = self.folders[4] / 'breeze/index.theme'
                index.unlink()
                if case == 'link out of the root':
                    index.symlink_to(outside)
                elif case == 'FIFO':
                    os.mkfifo(index)
                else:
                    index.write_bytes(raw)
                with mock.patch.object(shell.LOG, 'disabled', False), \
                        self.assertLogs(shell.LOG, 'WARNING') as logs:
                    lookup = shell.IconLookup(self.folders)
                    self.assertIsNone(lookup.resolve('app'))
                    self.assertEqual(lookup.resolve('other'), str(fixed))
                    self.assertIsNone(lookup.resolve('missing'))
                self.assertEqual(len(logs.records), 1, logs.output)
                self.assertIn('fixed layout', logs.output[0])
        # A control: the fixture's own index finds the same picture.
        (self.folders[4] / 'breeze/index.theme').unlink()
        self.index()
        self.assertIsNotNone(self.resolve())

    def test_one_pass_lists_at_most_its_budget_of_folder_entries_and_says_so_once(self):
        for n in range(10):
            self.themed(4, size='48x48', name=f'filler-{n}.png')
        self.breeze('apps/48')
        with mock.patch.object(shell, 'ICON_LOOKUP_ENTRIES', 8), mock.patch.object(shell.LOG, 'disabled', False), \
                self.assertLogs(shell.LOG, 'WARNING') as logs:
            lookup = shell.IconLookup(self.folders)
            # hicolor/ and 48x48/ show one entry each; apps/ shows a seventh entry and is refused unkept.
            self.assertIsNone(lookup.resolve('filler-1'))
            self.assertEqual(lookup.listings[str(self.folders[4] / 'hicolor/48x48/apps')], {})
            self.assertIsNone(lookup.resolve('app'))
        self.assertEqual(len(logs.records), 1, logs.output)
        # A control: the real budget finds both.
        self.assertIsNotNone(self.resolve('filler-1'))
        self.assertIsNotNone(self.resolve())

    def test_a_hostile_index_never_lists_or_opens_anything_outside_the_root(self):
        outside = self.root / 'outside'
        self.write(outside / 'app.svg', SVG)
        self.write(outside / 'deep/app.svg', SVG)
        inside = self.breeze('apps/48', name='other.svg')
        (self.folders[4] / 'breeze/apps/link').symlink_to(outside, target_is_directory=True)
        self.index(raw=b'[Icon Theme]\nDirectories=apps/link,apps/link/deep,apps/48\n[apps/link]\nSize=48\n'
                       b'Type=Scalable\n[apps/link/deep]\nSize=48\nType=Scalable\n[apps/48]\nSize=48\nType=Scalable\n')
        listed, opened, scandir, os_open = [], [], os.scandir, os.open

        def listing(path='.'):
            listed.append(os.readlink(f'/proc/self/fd/{path}') if isinstance(path, int) else os.path.realpath(path))
            return scandir(path)

        def readable(path, flags, *args, **kwargs):
            descriptor = os_open(path, flags, *args, **kwargs)
            if not flags & os.O_PATH:
                opened.append(os.readlink(f'/proc/self/fd/{descriptor}'))
            return descriptor

        with mock.patch.object(shell.os, 'scandir', side_effect=listing), \
                mock.patch.object(shell.os, 'open', side_effect=readable):
            lookup = shell.IconLookup(self.folders)
            self.assertIsNone(lookup.resolve('app'))
            self.assertEqual(lookup.resolve('other'), str(inside))
        self.assertTrue(listed)
        self.assertIn(str(self.folders[4] / 'breeze/index.theme'), opened)
        self.assertEqual([path for path in listed + opened if path.startswith(str(outside))], [])


class IconSniffTest(IconBase):
    def test_only_png_and_svg_are_accepted_independently_of_extension(self):
        self.assertEqual(shell.sniff_icon(PNG), 'png')
        for raw in (SVG, b'<svg/>', b' \n' + SVG, b'\xef\xbb\xbf<?xml version="1.0"?>\n<!-- drawn -->\n' + SVG):
            self.assertEqual(shell.sniff_icon(raw), 'svg')
        for raw in (b'not an image', b'%PDF-1.5', b'GIF89a', b'\xff\xd8\xff', b'\x1f\x8b',
                    b'MVG: push graphic-context', b'<html/>', b'<svgscript/>', b'\0<svg/>', b''):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    shell.sniff_icon(raw)

    def test_png_header_and_pixel_ceiling_are_checked_before_the_converter(self):
        for raw in (shell.PNG_SIGNATURE, PNG[:20], PNG[:12] + b'JUNK' + PNG[16:],
                    PNG[:16] + struct.pack('>II', 4097, 1) + PNG[24:],
                    PNG[:16] + struct.pack('>II', 1, 4097) + PNG[24:],
                    PNG[:16] + struct.pack('>II', 0, 10) + PNG[24:]):
            with self.assertRaises(ValueError):
                shell.sniff_icon(raw)

    def test_xml_dtd_entities_and_an_unbounded_preamble_are_refused(self):
        for raw in (b'<!DOCTYPE svg []>' + SVG, SVG + b'<!ENTITY x "file:///secret">',
                    b'<!doctype svg SYSTEM "https://example.invalid/icon">' + SVG,
                    b'<!--' + b' ' * 4096 + b'-->' + SVG):
            with self.assertRaises(ValueError):
                shell.sniff_icon(raw)

    def test_svg_coder_requires_readable_svg_backed_by_rsvg(self):
        self.assertTrue(shell.librsvg_coder(b'      SVG  SVG       rw+   Scalable Vector Graphics (RSVG 2.62.3)\n'))
        for raw in (b'', b'MSVG* SVG rw+ internal renderer\n', b'RSVG* SVG rw+ Librsvg\n',
                    b'SVG SVG rw+ internal MSVG\n', b'SVG SVG -w+ RSVG\n', b'SVGZ* SVG rw+ RSVG\n'):
            self.assertFalse(shell.librsvg_coder(raw))


class IconConversionTest(IconBase):
    def test_wrong_types_large_files_and_non_regular_sources_never_start_a_converter(self):
        bad = self.write(self.root / 'fake.png', b'not a picture')
        large = self.root / 'large.svg'
        with large.open('wb') as handle:
            handle.truncate(shell.MAX_ICON_BYTES + 1)
        fifo = self.root / 'pipe.png'
        os.mkfifo(fifo)
        with mock.patch.object(self.cache, 'run') as run:
            for path in (bad, large, fifo, self.root):
                with self.assertRaises((ValueError, OSError)):
                    self.cache.convert(str(path))
            for path in ('relative.png', 'x\0y'):
                with self.assertRaises(ValueError):
                    self.cache.convert(path)
            run.assert_not_called()

    def test_source_changed_during_read_is_refused(self):
        source = self.write(self.root / 'source')
        real_fstat = os.fstat
        count = 0

        def changing(fd):
            nonlocal count
            value = real_fstat(fd)
            count += 1
            if count == 2:
                return mock.Mock(st_size=value.st_size + 1, st_mtime_ns=value.st_mtime_ns)
            return value

        with mock.patch.object(shell.os, 'fstat', side_effect=changing), mock.patch.object(self.cache, 'run') as run:
            with self.assertRaises(ValueError):
                self.cache.convert(str(source))
            run.assert_not_called()

    def test_explicit_coders_limits_isolation_and_sanitized_child_environment(self):
        command = self.cache.command('/test/work', 'svg:/input/icon', 'PNG32:-')
        self.assertEqual(command[0], '/usr/bin/bwrap')
        for arg in ('--unshare-all', '--new-session', '--die-with-parent', '--clearenv'):
            self.assertIn(arg, command)
        for resource, value in (('memory', '64MiB'), ('map', '0'), ('disk', '0'), ('time', '2'),
                                ('thread', '1'), ('width', '4096'), ('height', '4096'), ('area', '16MP')):
            self.assertIn(['-limit', resource, value], [command[n:n + 3] for n in range(len(command) - 2)])
        self.assertEqual(command[-2:], ['svg:/input/icon', 'PNG32:-'])
        self.assertNotIn('--share-net', command)
        self.assertNotIn('--ro-bind', command[-2:])
        bindings = [command[n + 1:n + 3] for n, arg in enumerate(command) if arg == '--ro-bind']
        self.assertEqual(bindings, [['/usr/lib64', '/usr/lib64'], ['/usr/bin/magick', '/usr/bin/magick'],
                                    ['/test/work/policy.xml', '/etc/ImageMagick-7/policy.xml'],
                                    ['/test/work/input', '/input/icon']])
        self.assertIn('domain="delegate" rights="none" pattern="*"', shell.ICON_POLICY)
        self.assertIn('domain="coder" rights="none" pattern="*"', shell.ICON_POLICY)

    def test_cache_key_includes_path_size_and_nanosecond_time_and_reuses_output(self):
        source = self.write(self.root / 'source')
        with mock.patch.object(self.cache, 'run', return_value=NORMAL) as run:
            first = self.cache.convert(str(source))
            info = source.stat()
            expected = hashlib.sha256(os.fsencode(source) + b'\0' + str(info.st_size).encode() + b'\0'
                                      + str(info.st_mtime_ns).encode()).hexdigest() + '.png'
            self.assertEqual(pathlib.Path(first).name, expected)
            self.assertEqual(self.cache.convert(str(source)), first)
            self.assertEqual(run.call_count, 1)
            os.utime(source, ns=(info.st_atime_ns, info.st_mtime_ns + 1))
            second = self.cache.convert(str(source))
            self.assertNotEqual(first, second)
            source.write_bytes(PNG + b' ')
            third = self.cache.convert(str(source))
            self.assertNotEqual(second, third)
            other = self.write(self.root / 'other')
            os.utime(other, ns=(info.st_atime_ns, info.st_mtime_ns))
            self.assertNotEqual(first, self.cache.convert(str(other)))

    def test_private_cache_refuses_symlinks(self):
        self.cache.prepare()
        self.assertEqual(stat.S_IMODE(pathlib.Path(self.cache.directory).stat().st_mode), 0o700)
        pathlib.Path(self.cache.directory).rmdir()
        pathlib.Path(self.cache.directory).symlink_to(self.folders[0], target_is_directory=True)
        with self.assertRaises(ValueError):
            self.cache.prepare()
        pathlib.Path(self.cache.directory).unlink()
        pathlib.Path(self.cache.directory).parent.rmdir()
        pathlib.Path(self.cache.directory).parent.symlink_to(self.folders[0], target_is_directory=True)
        with self.assertRaises(ValueError):
            self.cache.prepare()

    def test_false_svg_coder_cannot_fall_back_to_msvg(self):
        source = self.write(self.root / 'vector', SVG)
        with mock.patch.object(self.cache, 'run', return_value=b'SVG SVG rw+ internal MSVG\n') as run:
            with self.assertRaisesRegex(ValueError, 'not librsvg'):
                self.cache.convert(str(source))
            self.assertEqual(run.call_count, 1)
            self.assertIn('identify', run.call_args.args[0])
            self.assertEqual(list(pathlib.Path(self.cache.directory).iterdir()), [])

    def test_converter_failure_and_invalid_output_leave_no_partial_picture_and_do_not_retry(self):
        source = self.write(self.root / 'source')
        for outcome in (OSError('missing converter'), ValueError('failed'), b'junk', PNG):
            self.cache.failed.clear()
            with mock.patch.object(self.cache, 'run', side_effect=outcome if isinstance(outcome, Exception) else None,
                                   return_value=outcome) as run:
                with self.assertRaises((OSError, ValueError)):
                    self.cache.convert(str(source))
                self.assertIsNone(self.cache.convert(str(source)))
                self.assertEqual(run.call_count, 1)
            self.assertEqual(list(pathlib.Path(self.cache.directory).iterdir()), [])

    def test_failed_atomic_replace_cleans_temporary_files(self):
        source = self.write(self.root / 'source')
        with mock.patch.object(self.cache, 'run', return_value=NORMAL), \
                mock.patch.object(shell.os, 'replace', side_effect=OSError('rename failed')):
            with self.assertRaises(OSError):
                self.cache.convert(str(source))
        self.assertEqual(list(pathlib.Path(self.cache.directory).iterdir()), [])

    def test_cache_symlink_wrong_mode_or_broken_header_are_replaced_without_following(self):
        source = self.write(self.root / 'source')
        with mock.patch.object(self.cache, 'run', return_value=NORMAL) as run:
            target = pathlib.Path(self.cache.convert(str(source)))
            outside = self.write(self.root / 'outside', b'keep this file')
            target.unlink()
            target.symlink_to(outside)
            self.cache.convert(str(source))
            self.assertFalse(target.is_symlink())
            self.assertEqual(outside.read_bytes(), b'keep this file')
            target.chmod(0o644)
            self.cache.convert(str(source))
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            target.write_bytes(b'broken cache')
            self.cache.convert(str(source))
            self.assertEqual(run.call_count, 4)

    def test_hanging_and_failed_converter_are_bounded_and_reaped(self):
        source = self.write(self.root / 'source')
        self.cache.timeout = 0.15
        original_popen = subprocess.Popen
        children = []

        def popen(*args, **kwargs):
            child = original_popen(*args, **kwargs)
            children.append(child)
            self.assertEqual(kwargs['env'], {'PATH': '/usr/bin', 'LC_ALL': 'C'})
            self.assertTrue(kwargs['close_fds'])
            self.assertTrue(kwargs['start_new_session'])
            return child

        for script in ('import time; time.sleep(60)', 'raise SystemExit(4)',
                       'import os; os.write(1,b"x" * (2 * 1024 * 1024))'):
            self.cache.failed.clear()
            with mock.patch.object(self.cache, 'command', return_value=[sys.executable, '-c', script]), \
                    mock.patch.object(shell.subprocess, 'Popen', side_effect=popen):
                start = time.monotonic()
                with self.assertRaises((ValueError, subprocess.TimeoutExpired)):
                    self.cache.convert(str(source))
                self.assertLess(time.monotonic() - start, 1.5)
            self.assertIsNotNone(children[-1].returncode)
            self.assertIsNone(self.cache.process)
            self.assertEqual(list(pathlib.Path(self.cache.directory).iterdir()), [])

    def test_timeout_kills_descendants_even_if_the_converter_parent_exits(self):
        marker = self.root / 'child.pid'
        script = ('import os,time; pid=os.fork(); '
                  f'open({str(marker)!r},"w").write(str(pid)) if pid else time.sleep(60)')
        self.cache.timeout = 0.2
        with self.assertRaises(subprocess.TimeoutExpired):
            self.cache.run([sys.executable, '-c', script])
        pid = int(marker.read_text())
        # An init reaper may briefly retain a zombie; it must never be a running child.
        procstat = pathlib.Path(f'/proc/{pid}/stat')
        deadline = time.monotonic() + 1
        while procstat.exists() and procstat.read_text().split()[2] != 'Z' and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(not procstat.exists() or procstat.read_text().split()[2] == 'Z')


class IconAsyncTest(IconBase):
    def app(self, app_id='one', name='first'):
        return shell.App(app_id, app_id.title(), icon_name=name)

    def wait_results(self, count=1):
        deadline = time.monotonic() + 3
        while self.cache.results.qsize() < count and time.monotonic() < deadline:
            time.sleep(0.005)
        self.assertGreaterEqual(self.cache.results.qsize(), count)

    def test_lookup_and_conversion_never_block_request_or_take_and_arrivals_change_revision(self):
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)

        def lookup(*args):
            entered.set()
            release.wait(3)
            return '/source'

        apps = {'one': self.app()}
        with mock.patch.object(shell.IconLookup, 'resolve', side_effect=lookup), \
                mock.patch.object(self.cache, 'convert', return_value='/cache/one.png'):
            start = time.monotonic()
            self.cache.request(apps, 'base')
            self.assertTrue(entered.wait(1))
            current, revision = self.cache.take(apps, 'base')
            self.assertLess(time.monotonic() - start, 0.5)
            self.assertIsNone(current['one'].icon)
            self.assertEqual(revision, 'base')
            release.set()
            self.wait_results()
            current, revision = self.cache.take(current, 'base')
            self.assertEqual(current['one'].icon, '/cache/one.png')
            self.assertNotEqual(revision, 'base')
            self.assertEqual(self.cache.take(current, 'base')[1], revision)

    def test_each_icon_arrives_independently_and_a_failure_only_loses_its_own_icon(self):
        second, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)

        def convert(source):
            if source == '/bad':
                raise ValueError('bad icon')
            if source == '/two':
                second.set()
                release.wait(3)
            return '/cache' + source + '.png'

        apps = {key: self.app(key, '/' + key) for key in ('one', 'two', 'bad')}
        with mock.patch.object(self.cache, 'convert', side_effect=convert):
            self.cache.request(apps, 'base')
            self.assertTrue(second.wait(1))
            current, revision = self.cache.take(apps, 'base')
            self.assertEqual(current['one'].icon, '/cache/one.png')
            self.assertIsNone(current['two'].icon)
            release.set()
            self.wait_results(2)
            current, final = self.cache.take(current, 'base')
            self.assertNotEqual(final, revision)
            self.assertEqual(current['two'].icon, '/cache/two.png')
            self.assertIsNone(current['bad'].icon)

    def test_stale_or_removed_results_cannot_attach_to_a_new_catalogue(self):
        apps = {'one': self.app()}
        self.cache.results.put(('old', 'one', 'first', '/old.png'))
        self.cache.results.put(('new', 'one', 'wrong-name', '/wrong.png'))
        self.cache.results.put(('new', 'removed', 'first', '/removed.png'))
        self.assertEqual(self.cache.take(apps, 'new'), (apps, 'new'))

    def test_pending_work_and_results_are_bounded_and_stop_joins_the_worker(self):
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)

        def convert(source):
            entered.set()
            release.wait(3)
            return '/cache.png'

        with mock.patch.object(self.cache, 'convert', side_effect=convert):
            self.cache.request({'one': self.app(name='/one')}, 'old')
            self.assertTrue(entered.wait(1))
            for i in range(1000):
                self.cache.request({'one': self.app(name='/one')}, str(i))
            self.assertEqual(self.cache.pending.qsize(), 1)
            self.assertEqual(self.cache.pending.queue[0][1], '999')
            release.set()
            self.cache.stop()
        self.assertFalse(self.cache.thread.is_alive())
        self.cache.request({}, 'stopped')

    def test_updated_or_removed_picture_changes_revision_but_failed_missing_picture_does_not(self):
        app = self.app()
        apps = {'one': app}
        self.cache.results.put(('base', 'one', 'first', None))
        self.assertEqual(self.cache.take(apps, 'base'), (apps, 'base'))
        current = {'one': dataclasses.replace(app, icon='/cache/old.png')}
        old = shell.icons_revision(current, 'base')
        self.cache.results.put(('base', 'one', 'first', '/cache/new.png'))
        current, new = self.cache.take(current, 'base')
        self.assertNotEqual(new, old)
        self.cache.results.put(('base', 'one', 'first', None))
        self.assertEqual(self.cache.take(current, 'base'), (apps, 'base'))

    def test_stop_terminates_the_owned_active_converter_and_joins_the_worker(self):
        source = self.write(self.root / 'source')
        with mock.patch.object(self.cache, 'command', return_value=[sys.executable, '-c',
                                                                   'import time; time.sleep(60)']):
            self.cache.request({'one': self.app(name=str(source))}, 'base')
            deadline = time.monotonic() + 2
            while self.cache.process is None and time.monotonic() < deadline:
                time.sleep(0.005)
            process = self.cache.process
            self.assertIsNotNone(process)
            self.cache.stop()
        self.assertIsNotNone(process.returncode)
        self.assertFalse(self.cache.thread.is_alive())

    def test_full_results_queue_never_blocks_the_worker_or_shutdown(self):
        for _ in range(shell.MAX_APPS * 2):
            self.cache.results.put_nowait(('old', 'one', 'first', None))
        finished = threading.Event()

        def convert(source):
            finished.set()
            return '/cache.png'

        with mock.patch.object(self.cache, 'convert', side_effect=convert):
            self.cache.request({'one': self.app(name='/source')}, 'base')
            self.assertTrue(finished.wait(1))
            self.cache.stop()
        self.assertFalse(self.cache.thread.is_alive())
        self.assertEqual(self.cache.results.qsize(), shell.MAX_APPS * 2)


class IconCompatibilityTest(Base):
    def test_original_client_still_gets_exact_registry_shape_and_no_icon_metadata(self):
        helper = self.helper()
        conn = self.connect(helper)
        apps, revision = shell.load_registry(str(REGISTRY))
        helper.apps = {key: dataclasses.replace(app, icon_name='secret', icon='/private/icon.png')
                       for key, app in apps.items()}
        response = self.request(helper, conn, 'list_apps')
        self.assertEqual(response['revision'], revision)
        self.assertEqual({a['id'] for a in response['apps']}, {'browser', 'terminal', 'notepad'})
        for app in response['apps']:
            self.assertEqual(set(app), {'id', 'name', 'available', 'reason'})
        self.assertEqual(response['protocol'], 'aresos-shell/1.0')
        self.assertEqual(shell.MINOR, 1)

    def test_release_converter_check_is_separate_and_rejects_internal_svg(self):
        script = (ROOT / 'os/ci/image-checks.sh').read_text()
        block = script.split('# --- Package 30:')[1].split('set +x')[0]
        self.assertIn('test -x /usr/bin/magick', block)
        self.assertIn('test -x /usr/bin/bwrap', block)
        python = block.split("<<'PY'\n")[1].split('\nPY\n')[0]
        for valid in (True, False):
            formats = b'PNG* PNG rw- Portable\nSVG SVG rw+ Scalable (RSVG 2.62.3)\n' if valid else \
                b'PNG* PNG rw- Portable\nSVG SVG rw+ internal MSVG\n'
            with mock.patch.object(subprocess, 'run', return_value=mock.Mock(stdout=formats)):
                if valid:
                    with mock.patch('builtins.print'):
                        exec(python, {})
                else:
                    with self.assertRaises(AssertionError):
                        exec(python, {})
