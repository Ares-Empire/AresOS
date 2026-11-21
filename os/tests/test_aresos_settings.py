"""Package 320: aresos-settings, the owner's three desktop settings (briefs/320-indicator.md, Decisions 2 and 3).

The program is loaded as a module for most tests, with its path to aresos-level pointed at a recording stand-in. Every
run of the command that can show the plate (`set`) uses level_sandbox: the program at its image path, a stand-in or
the branch's aresos-level, stand-in tools, a scratch HOME and a private bus in a private namespace.
"""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

import level_sandbox as sandbox
from level_sandbox import Sandbox

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROGRAM = ROOT / 'os/config/usr/libexec/aresos-settings'
DEFAULTS = {'indicator-place': 'top', 'indicator-size': 'medium', 'look': 'B'}


def load_program():
    loader = importlib.machinery.SourceFileLoader('aresos_settings', str(PROGRAM))
    spec = importlib.util.spec_from_loader('aresos_settings', loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class SettingsCase(unittest.TestCase):
    def setUp(self):
        self.program = load_program()
        self.folder = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.config = self.folder / 'config'
        self.file = self.config / 'aresos/settings.json'
        self.enterContext(mock.patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.config),
                                                       'HOME': str(self.folder / 'home')}))
        self.shown = self.folder / 'shown.log'
        level = self.folder / 'aresos-level'
        level.write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" >> {self.shown}\n')
        level.chmod(0o755)
        self.program.LEVEL = str(level)

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = self.program.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def get(self):
        code, out, err = self.run_main('get')
        self.assertEqual(code, 0, err)
        return json.loads(out), err

    def shows(self):
        return self.shown.read_text().splitlines() if self.shown.exists() else []


class DefaultsTest(SettingsCase):
    def test_no_file_means_the_defaults_and_writes_nothing(self):
        self.assertEqual(self.get(), (DEFAULTS, ''))
        self.assertFalse(self.config.exists())

    def test_the_defaults_and_choices_are_the_briefs(self):
        self.assertEqual(self.program.DEFAULTS, DEFAULTS)
        self.assertEqual(self.program.CHOICES, {'look': ('A', 'B', 'C'), 'indicator-place': ('top', 'bottom'),
                                                'indicator-size': ('small', 'medium', 'large')})
        self.assertEqual(self.program.path(), self.file)

    def test_xdg_config_home_is_honoured_and_a_relative_one_ignored(self):
        with mock.patch.dict(os.environ, {'XDG_CONFIG_HOME': 'relative/config'}):
            self.assertEqual(self.program.path(), self.folder / 'home/.config/aresos/settings.json')
        with mock.patch.dict(os.environ, {'XDG_CONFIG_HOME': ''}):
            self.assertEqual(self.program.path(), self.folder / 'home/.config/aresos/settings.json')

    def test_a_broken_file_means_the_defaults_and_one_journal_line(self):
        self.file.parent.mkdir(parents=True)
        for content in (b'{not json', b'\xff\xfe', b'[]', b'{"look": "A"}', b'{"version": 2, "look": "A"}',
                        b'{"version": true, "look": "A"}', b' ' * (64 * 1024 + 1)):
            with self.subTest(content=content[:30]):
                self.file.write_bytes(content)
                settings, err = self.get()
                self.assertEqual(settings, DEFAULTS)
                self.assertEqual(len(err.splitlines()), 1, err)
                self.assertIn('using the defaults', err)

    def test_a_bad_value_falls_back_alone_with_one_line_for_all_problems(self):
        self.file.parent.mkdir(parents=True)
        self.file.write_text(json.dumps({'version': 1, 'look': 'A', 'indicator-size': 'huge',
                                         'indicator-place': 3, 'colour': 'red'}))
        settings, err = self.get()
        self.assertEqual(settings, dict(DEFAULTS, look='A'))
        self.assertEqual(len(err.splitlines()), 1, err)
        for word in ('indicator-size', 'huge', 'indicator-place', 'colour'):
            self.assertIn(word, err)

    def test_an_unreadable_file_means_the_defaults(self):
        self.file.mkdir(parents=True)
        settings, err = self.get()
        self.assertEqual(settings, DEFAULTS)
        self.assertIn('cannot read', err)

    def test_load_is_what_the_indicator_imports(self):
        self.assertEqual(self.program.load(), DEFAULTS)
        self.file.parent.mkdir(parents=True)
        self.file.write_text('{"version": 1, "indicator-place": "bottom"}')
        self.assertEqual(self.program.load(), dict(DEFAULTS, **{'indicator-place': 'bottom'}))


class SetTest(SettingsCase):
    def test_each_name_and_value_is_saved_alone_and_read_back(self):
        for name, values in self.program.CHOICES.items():
            for value in values:
                with self.subTest(name=name, value=value):
                    self.file.unlink(missing_ok=True)
                    self.assertEqual(self.run_main('set', name, value), (0, '', ''))
                    self.assertEqual(json.loads(self.file.read_text()), {'version': 1, name: value})
                    self.assertEqual(self.get()[0], dict(DEFAULTS, **{name: value}))

    def test_values_accumulate_and_only_place_and_size_show_the_plate(self):
        self.assertEqual(self.run_main('set', 'look', 'A')[0], 0)
        self.assertEqual(self.shows(), [])
        self.assertEqual(self.run_main('set', 'indicator-place', 'bottom')[0], 0)
        self.assertEqual(self.run_main('set', 'indicator-size', 'large')[0], 0)
        self.assertEqual(self.shows(), ['show-volume', 'show-volume'])
        self.assertEqual(json.loads(self.file.read_text()),
                         {'version': 1, 'indicator-place': 'bottom', 'indicator-size': 'large', 'look': 'A'})

    def test_a_bad_name_or_value_is_refused_and_the_file_kept(self):
        self.file.parent.mkdir(parents=True)
        self.file.write_text('{"version": 1, "look": "C"}\n')
        for argv in (('set', 'look', 'D'), ('set', 'look', 'a'), ('set', 'colour', 'red'), ('set', 'look'),
                     ('get', 'look'), (), ('remove', 'look')):
            with self.subTest(argv=argv):
                code, out, err = self.run_main(*argv)
                self.assertEqual(code, 2)
                self.assertIn('usage: aresos-settings', err)
                self.assertEqual(self.file.read_text(), '{"version": 1, "look": "C"}\n')
        self.assertEqual(self.shows(), [])

    def test_a_broken_file_is_replaced_by_the_new_value_with_one_line(self):
        self.file.parent.mkdir(parents=True)
        self.file.write_text('{"version": 1, "look": "Z", "indicator-size": "small"}')
        code, _, err = self.run_main('set', 'indicator-place', 'bottom')
        self.assertEqual(code, 0)
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertEqual(json.loads(self.file.read_text()),
                         {'version': 1, 'indicator-place': 'bottom', 'indicator-size': 'small'})

    def test_the_folder_is_created_when_missing(self):
        self.assertFalse(self.config.exists())
        self.assertEqual(self.run_main('set', 'look', 'C')[0], 0)
        self.assertEqual(sorted(path.name for path in self.file.parent.iterdir()), ['settings.json'])

    def test_a_missing_aresos_level_still_saves(self):
        self.program.LEVEL = str(self.folder / 'missing')
        code, _, err = self.run_main('set', 'indicator-size', 'small')
        self.assertEqual(code, 0)
        self.assertIn('the plate could not be shown', err)
        self.assertEqual(self.get()[0]['indicator-size'], 'small')


class AtomicWriteTest(SettingsCase):
    def setUp(self):
        super().setUp()
        self.file.parent.mkdir(parents=True)
        self.original = '{"version": 1, "look": "A"}\n'
        self.file.write_text(self.original)

    def assert_untouched(self):
        self.assertEqual(self.file.read_text(), self.original)
        self.assertEqual([path.name for path in self.file.parent.iterdir()], ['settings.json'])

    def test_the_new_file_is_written_beside_it_flushed_and_renamed_into_place(self):
        renamed, synced = [], []
        real_replace, real_fsync = os.replace, os.fsync

        def replace(source, target):
            renamed.append((pathlib.Path(source).parent, pathlib.Path(target)))
            self.assertEqual(self.file.read_text(), self.original)
            self.assertTrue(synced)
            return real_replace(source, target)

        with mock.patch.object(self.program.os, 'replace', replace), \
                mock.patch.object(self.program.os, 'fsync', lambda fd: synced.append(fd) or real_fsync(fd)):
            self.assertEqual(self.run_main('set', 'look', 'B')[0], 0)
        self.assertEqual(renamed, [(self.file.parent, self.file)])
        self.assertEqual(json.loads(self.file.read_text()), {'version': 1, 'look': 'B'})

    def test_a_failed_rename_keeps_the_old_file_and_leaves_no_temporary(self):
        with mock.patch.object(self.program.os, 'replace', side_effect=OSError(28, 'No space left on device')):
            code, _, err = self.run_main('set', 'look', 'B')
        self.assertEqual(code, 1)
        self.assertIn('could not save look', err)
        self.assert_untouched()

    def test_a_failure_while_writing_keeps_the_old_file(self):
        with mock.patch.object(self.program.json, 'dump', side_effect=OSError(5, 'Input/output error')):
            self.assertEqual(self.run_main('set', 'indicator-size', 'large')[0], 1)
        self.assert_untouched()
        self.assertEqual(self.shows(), [])


class OwnershipTest(unittest.TestCase):
    def test_no_other_program_reads_the_settings_file(self):
        # The defaults live in aresos-settings alone; everyone else asks it.
        readers = [path.relative_to(ROOT) for path in (ROOT / 'os/config').rglob('*')
                   if path.is_file() and path.name != 'aresos-settings'
                   and b'settings.json' in path.read_bytes()]
        self.assertEqual(readers, [])
        self.assertNotIn('indicator-', (ROOT / 'os/config/usr/libexec/aresos-level').read_text())

    def test_get_runs_as_a_command(self):
        with tempfile.TemporaryDirectory() as home:
            result = subprocess.run([str(PROGRAM), 'get'], capture_output=True, text=True, timeout=30,
                                    env={'HOME': home, 'PATH': '/usr/bin:/bin'})
            self.assertEqual((result.returncode, json.loads(result.stdout), result.stderr), (0, DEFAULTS, ''))
            self.assertEqual(os.listdir(home), [])


class CommandInSandboxTest(unittest.TestCase):
    def setUp(self):
        problem = sandbox.unavailable()
        if problem:
            if os.environ.get('GITHUB_ACTIONS') == 'true':
                self.fail(problem)
            self.skipTest(problem)

    def box(self, **options):
        box = Sandbox(**options)
        self.addCleanup(box.close)
        return box

    def test_set_shows_the_plate_once_through_aresos_level(self):
        box = self.box(level='stand-in')
        result = box.run('S=/usr/libexec/aresos-settings\n'
                         '$S set indicator-size large; echo "rc=$?"; $S set look A; echo "rc=$?"\n'
                         '$S set indicator-place bottom; echo "rc=$?"; $S set look Z; echo "rc=$?"; $S get\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[:4], ['rc=0', 'rc=0', 'rc=0', 'rc=2'])
        self.assertEqual(json.loads(lines[4]), {'indicator-place': 'bottom', 'indicator-size': 'large', 'look': 'A'})
        self.assertEqual((box.state_dir / 'level.log').read_text().splitlines(), ['show-volume', 'show-volume'])
        self.assertEqual(json.loads((box.home / '.config/aresos/settings.json').read_text()),
                         {'version': 1, 'indicator-place': 'bottom', 'indicator-size': 'large', 'look': 'A'})

    def test_set_tells_the_indicator_the_current_volume(self):
        box = self.box(indicator='crash', sink={'volume': 0.55, 'mute': True})
        result = box.run('/usr/libexec/aresos-settings set indicator-place bottom; echo "rc=$?"; settle\n')
        self.assertEqual(result.stdout.split(), ['rc=0'], result.stderr)
        self.assertEqual([row['argv'] for row in box.events('start')], [['1', 'show-volume', '55 muted']])
        self.assertEqual(box.state()['sink'], {'volume': 0.55, 'mute': True})
        self.assertEqual(box.calls(), ['/usr/bin/wpctl get-volume @DEFAULT_AUDIO_SINK@'])


if __name__ == '__main__':
    unittest.main()
