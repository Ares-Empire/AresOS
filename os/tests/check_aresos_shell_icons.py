"""Explicit AresOS converter smoke tests; Ubuntu's unit runner has no ImageMagick 7.

Run: python3 -m unittest discover -s os/tests -p 'check_aresos_shell_icons.py' -v
These checks require the actual Fedora sandbox route. No compositor or GUI is involved.
"""
import os
import pathlib
import socket
import stat
import time
import unittest
from unittest import mock

from test_aresos_shell import shell
from test_aresos_shell_icons import IconBase, FIXTURES, PNG, SVG, pixels


class IconRealRouteTest(IconBase):
    """Run explicitly on AresOS; missing prerequisites fail, with no skips."""

    def test_real_png_and_svg_are_rgba_128_square_aspect_kept_and_transparent(self):
        for filename in ('drawn.png', 'drawn.svg'):
            with self.subTest(filename=filename):
                path = pathlib.Path(self.cache.convert(str(FIXTURES / filename)))
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
                raw = path.read_bytes()
                rows = pixels(raw)
                self.assertTrue(all(p[3] == 0 for row in rows[:32] + rows[96:] for p in row))
                self.assertTrue(all(p[3] == 0 for row in rows for p in row[96:]))
                self.assertGreater(rows[64][8][3], 245)
                self.assertTrue(100 < rows[64][48][3] < 155)
                if filename.endswith('.png'):
                    self.assertGreater(rows[64][8][0], 220)
                    self.assertGreater(rows[64][48][2], 220)
                else:
                    self.assertGreater(rows[64][8][1], 170)
                    self.assertGreater(rows[64][48][0], 240)
                with mock.patch.object(self.cache, 'run', side_effect=AssertionError('must reuse cache')):
                    self.assertEqual(self.cache.convert(str(FIXTURES / filename)), str(path))
        self.assertEqual(len(list(pathlib.Path(self.cache.directory).iterdir())), 2)

    def test_sniffed_coder_handles_misleading_or_magick_special_filenames(self):
        source = self.write(self.root / 'svg:fake[0].jpg', PNG)
        path = self.cache.convert(str(source))
        self.assertGreater(pixels(pathlib.Path(path).read_bytes())[64][8][0], 220)
        source = self.write(self.root / 'png:fake[0].png', SVG)
        path = self.cache.convert(str(source))
        self.assertGreater(pixels(pathlib.Path(path).read_bytes())[64][8][1], 170)

    def test_corrupt_png_and_huge_svg_are_refused_without_a_cache_file(self):
        for name, raw in (('corrupt', PNG[:33]), ('huge', SVG.replace(b'width="8"', b'width="50000"'))):
            with self.subTest(name=name):
                source = self.write(self.root / name, raw)
                with self.assertRaises(ValueError):
                    self.cache.convert(str(source))
        self.assertEqual(list(pathlib.Path(self.cache.directory).iterdir()), [])

    def test_svg_cannot_read_a_neighbor_image_or_reach_a_local_listener(self):
        neighbor = self.write(self.root / 'neighbor.png')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            listener.settimeout(0.05)
            url = 'http://127.0.0.1:' + str(listener.getsockname()[1]) + '/image.png'
            for location in (neighbor.as_uri(), url):
                raw = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                       'width="8" height="4"><image width="8" height="4" '
                       f'xlink:href="{location}"/></svg>').encode()
                source = self.write(self.root / 'external.svg', raw)
                # Security review 1, FIX 2: refused before any converter runs.
                with self.assertRaisesRegex(ValueError, 'image'):
                    self.cache.convert(str(source))
                # The sandbox below still holds should that refusal ever be bypassed.
                self.cache.failed.clear()
                with mock.patch.object(shell, 'drawn_svg'):
                    path = self.cache.convert(str(source))
                self.assertTrue(all(p[3] == 0 for row in pixels(pathlib.Path(path).read_bytes()) for p in row))
            with self.assertRaises(TimeoutError):
                listener.accept()

    def test_embedded_picture_bomb_is_refused_and_capped_even_if_it_got_through(self):
        from test_aresos_shell_hardening import picture_bomb
        source = self.write(self.root / 'bomb.svg', picture_bomb())
        with self.assertRaisesRegex(ValueError, 'image'):
            self.cache.convert(str(source))
        # Bypass the refusal: librsvg would decode about 1 GB; the address-space ceiling stops it.
        self.cache.failed.clear()
        start = time.monotonic()
        with mock.patch.object(shell, 'drawn_svg'), self.assertRaises(ValueError):
            self.cache.convert(str(source))
        self.assertLess(time.monotonic() - start, shell.ICON_TIMEOUT + 1)
        self.assertEqual(list(pathlib.Path(self.cache.directory).iterdir()), [])

    def test_missing_bwrap_never_uses_an_unsandboxed_converter(self):
        self.cache.bwrap = str(self.root / 'missing-bwrap')
        with self.assertRaises(OSError):
            self.cache.convert(str(FIXTURES / 'drawn.png'))
        self.assertEqual(list(pathlib.Path(self.cache.directory).iterdir()), [])

    def test_atomic_publication_has_complete_pixels_and_private_mode_at_rename(self):
        original = os.replace
        renamed = []

        def replace(source, target):
            self.assertFalse(pathlib.Path(target).exists())
            self.assertEqual(stat.S_IMODE(pathlib.Path(source).stat().st_mode), 0o600)
            self.assertGreater(pixels(pathlib.Path(source).read_bytes())[64][8][0], 220)
            renamed.append(target)
            original(source, target)

        with mock.patch.object(shell.os, 'replace', side_effect=replace):
            path = self.cache.convert(str(FIXTURES / 'drawn.png'))
        self.assertEqual(renamed, [path])


