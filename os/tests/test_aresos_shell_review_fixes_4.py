"""Package 30, review fixes 4: the picture signature settles, and three ways a picture stayed missing.

Everything is synthetic, as in review fixes 3: the icon folders, the desktop entries and the converter's answer are the
test's own, and the worker's steps run on the test's thread after each of the helper's ticks. Nothing here opens a
FIFO: its times are moved with utime.
"""
import os
import pathlib
import stat
from unittest import mock

from test_aresos_shell import shell
from test_aresos_shell_icons import BREEZE_INDEX, NORMAL, PNG
from test_aresos_shell_review_fixes_3 import PicturePasses, later


class SignatureBase(PicturePasses):
    def setUp(self):
        super().setUp()
        self.cache.prepare()
        self.pictures = pathlib.Path(self.cache.directory)
        self.outside = self.root / 'outside'
        self.outside.mkdir()

    def link(self, path, target):
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)
        return path

    def settles(self, change=lambda: None):
        """The first tick, then a minute of ticks with change() before each: whether each tick asked for a pass, the
        first tick's warnings and those of all later ticks."""
        with mock.patch.object(shell.LOG, 'warning') as warning:
            passes = self.ticks(1)
            first = [call.args[0] % call.args[1:] for call in warning.call_args_list]
            warning.reset_mock()
            for _ in range(20):
                change()
                passes += self.ticks(1)
            rest = [call.args[0] % call.args[1:] for call in warning.call_args_list]
        return passes, first, rest


class SettledSignatureTest(SignatureBase):
    """FIX 1: what a pass refused (a link out of its root, a FIFO) is kept by the links that lead there, never by what
    they lead to; so a pass that changes nothing outside its own picture cache leaves a signature that equals the next
    idle check's, and replacing a refused link is still seen."""

    def test_an_index_linked_to_the_picture_cache_asks_for_one_pass_and_warns_once(self):
        # The review's scenario: the home folder's hicolor index is a link onto the helper's own picture cache.
        self.link(self.folders[0] / 'hicolor/index.theme', self.pictures)

        def conversion(command):
            # A real conversion changes the cache folder after the coarse clock's step; the stand-in says so.
            later(self.pictures)
            return NORMAL

        self.cache.run.side_effect = conversion
        passes, first, rest = self.settles()
        self.assertEqual(passes, [True] + [False] * 20)
        self.assertEqual(len(first), 1, first)
        self.assertIn('fixed layout', first[0])
        self.assertEqual(rest, [])
        # The ordinary picture in the fixed layout.
        self.assertTrue(os.path.isfile(self.icon('one')))

    def test_changing_the_picture_cache_asks_for_no_pass_whatever_leads_into_it(self):
        """The property, for every kind of path a pass looks at: with links into the cache and its parent from an
        index, a theme folder, the way to an index's folder, a picture and a pixmap, and an absolute Icon= naming the
        cache, changing the cache as passes do asks for no pass."""
        aresos = self.pictures.parent
        self.link(self.folders[0] / 'hicolor/index.theme', self.pictures)
        self.link(self.folders[1] / 'breeze', self.pictures)
        self.link(self.folders[3] / 'hicolor', aresos)
        self.link(self.folders[4] / 'breeze/places', aresos)  # the fixture's index lists places/64
        self.link(self.folders[4] / 'hicolor/48x48/apps/app-two.png', self.pictures / 'app-two.png')
        self.link(self.folders[5] / 'app-two.png', self.pictures)
        self.desktop('three', str(self.pictures))
        count = [0]

        def change():
            count[0] += 1
            for folder in (self.pictures, aresos):
                os.chmod(folder, 0o700)
            work = self.pictures / '.convert-check'
            work.mkdir()
            work.rmdir()
            (self.pictures / 'app-two.png').write_bytes(b'%d' % count[0])
            for path in (self.pictures / 'app-two.png', self.pictures, aresos):
                later(path)

        passes, first, rest = self.settles(change)
        self.assertEqual(passes, [True] + [False] * 20)
        self.assertEqual(len(first), 1, first)
        self.assertEqual(rest, [])
        self.assertTrue(os.path.isfile(self.icon('one')))
        self.assertIsNone(self.icon('two'))
        self.assertIsNone(self.icon('three'))

    def test_refused_links_onto_things_that_change_on_every_tick_ask_for_no_pass(self):
        log, busy = self.outside / 'log', self.outside / 'busy'
        log.write_bytes(b'0')
        busy.mkdir()
        self.link(self.folders[0] / 'hicolor/index.theme', log)
        self.link(self.folders[1] / 'hicolor', busy)
        # Not a link: an index that is a FIFO is refused for its kind; its times change as when it is written.
        fifo = self.folders[0] / 'breeze/index.theme'
        fifo.parent.mkdir()
        os.mkfifo(fifo)
        count = [0]

        def change():
            count[0] += 1
            log.write_bytes(b'%d' % count[0])
            (busy / str(count[0])).touch()
            for path in (log, busy, fifo):
                later(path)

        passes, first, rest = self.settles(change)
        self.assertEqual(passes, [True] + [False] * 20)
        self.assertEqual(len(first), 2, first)
        self.assertEqual(rest, [])
        self.assertTrue(os.path.isfile(self.icon('one')))

    def test_replacing_a_refused_index_link_by_a_good_index_asks_for_exactly_one_pass(self):
        (self.outside / 'index.theme').write_bytes(BREEZE_INDEX)
        index = self.link(self.folders[0] / 'breeze/index.theme', self.outside / 'index.theme')
        self.breeze('apps/32', 'app-two.png', PNG)
        self.ticks(2)
        # The first breeze index is refused: the whole theme keeps the fixed layout.
        self.assertIsNone(self.icon('two'))
        good = index.with_name('.index.theme')
        good.write_bytes(BREEZE_INDEX)
        os.replace(good, index)
        self.assertEqual(self.ticks(10), [True] + [False] * 9)
        self.assertTrue(os.path.isfile(self.icon('two')))

    def test_replacing_a_refused_link_on_the_way_to_an_index_folder_asks_for_exactly_one_pass(self):
        # R4's index lists extra/link/deep; extra/link leads out of the root, and the pass never lists extra/ itself.
        self.index(4, BREEZE_INDEX.replace(b'Directories=', b'Directories=extra/link/deep,')
                   + b'[extra/link/deep]\nSize=64\nType=Fixed\n')
        self.write(self.outside / 'deep/app-two.png')
        link = self.link(self.folders[4] / 'breeze/extra/link', self.outside)
        self.ticks(2)
        self.assertIsNone(self.icon('two'))
        real = link.with_name('.real')
        self.write(real / 'deep/app-two.png')
        link.unlink()
        real.rename(link)
        self.assertEqual(self.ticks(10), [True] + [False] * 9)
        self.assertTrue(os.path.isfile(self.icon('two')))

    def test_a_cached_picture_leaves_the_cache_folder_as_it_is(self):
        made = self.cache.convert(str(self.picture))
        with mock.patch.object(shell.os, 'chmod') as chmod:
            self.assertEqual(self.cache.convert(str(self.picture)), made)
        chmod.assert_not_called()
        # A control: a changed mode is still set back.
        os.chmod(self.pictures, 0o755)
        self.assertEqual(self.cache.convert(str(self.picture)), made)
        self.assertEqual(stat.S_IMODE(os.stat(self.pictures).st_mode), 0o700)

    def test_a_pass_for_another_reason_does_not_repeat_the_warning_for_an_unchanged_index(self):
        index = self.link(self.folders[0] / 'hicolor/index.theme', self.pictures)
        with mock.patch.object(shell.LOG, 'warning') as warning:
            self.assertEqual(self.ticks(2), [True, False])
            self.assertEqual(warning.call_count, 1)
            # A new picture asks for a pass; the index is as it was.
            later(self.themed(4, size='48x48', name='app-two.png').parent)
            self.assertEqual(self.ticks(5), [True] + [False] * 4)
            self.assertTrue(os.path.isfile(self.icon('two')))
            self.assertEqual(warning.call_count, 1)
            # Another link out of the root in its place: one warning about that one.
            index.unlink()
            index.symlink_to(self.outside)
            self.assertEqual(self.ticks(5), [True] + [False] * 4)
            self.assertEqual(warning.call_count, 2)
