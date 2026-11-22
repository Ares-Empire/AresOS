"""Exercise the installed switch logic against private directories and stub commands."""
from contextlib import contextmanager
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

CONFIG = Path(__file__).resolve().parents[1] / 'config'


class InputSharingTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.switch = self.folder / 'sharing'
        self.helper = runpy.run_path(str(CONFIG / 'usr/libexec/aresos-input-sharing-set'))
        self.state = self.helper['set_switch'].__globals__

        @contextmanager
        def directory(create=False):
            fd = os.open(self.folder, self.helper['DIR_FLAGS'])
            try:
                yield fd
            finally:
                os.close(fd)

        self.enterContext(patch.dict(self.state, switch_directory=directory, trusted=self.trusted))

    def trusted(self, info):
        return info.st_uid == os.getuid() and info.st_mode & 0o022 == 0

    def test_switch_is_atomic_and_status_is_off_by_default(self):
        self.assertFalse(self.helper['sharing_on']())
        self.helper['set_switch']('on')
        self.assertEqual(self.switch.read_bytes(), b'on\n')
        self.assertEqual(self.switch.stat().st_mode & 0o777, 0o644)
        self.assertTrue(self.helper['sharing_on']())
        self.helper['set_switch']('off')
        self.helper['set_switch']('off')
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_neither_verb_writes_an_unsafe_switch(self):
        target = self.folder / 'other'
        target.write_text('on\n')
        for create in (lambda: self.switch.symlink_to(target), lambda: os.mkfifo(self.switch)):
            with self.subTest(create=create):
                create()
                self.assertFalse(self.helper['sharing_on']())
                for verb in ('on', 'off'):
                    with self.assertRaises(PermissionError):
                        self.helper['set_switch'](verb)
                self.switch.unlink()
        self.assertEqual(target.read_text(), 'on\n')

    def test_invalid_arguments_are_refused_before_touching_files(self):
        with (patch('os.geteuid', return_value=0),
              patch.dict(self.state, set_switch=lambda _: self.fail('helper tried to touch the switch'))):
            for args in ([], ['ON'], ['on', 'off'], ['/some/path']):
                with self.subTest(args=args), patch('sys.stderr'):
                    self.assertEqual(self.helper['main'](args), 2)

    def test_off_revokes_after_pkexec_and_on_does_not(self):
        ui = runpy.run_path(str(CONFIG / 'usr/bin/aresos-input-sharing'))
        with patch('subprocess.run') as run:
            run.return_value.returncode = 0
            self.assertEqual(ui['change']('off'), 0)
            self.assertEqual([call.args[0][-1] for call in run.call_args_list], ['off', '--revoke'])
            run.reset_mock()
            self.assertEqual(ui['change']('on'), 0)
            run.assert_called_once_with(['/usr/bin/pkexec', '--disable-internal-agent',
                                         '/usr/libexec/aresos-input-sharing-set', 'on'])
