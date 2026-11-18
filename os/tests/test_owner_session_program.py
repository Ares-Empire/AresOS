"""D19: a release's own session program must run; a spare terminal cannot stand in for it."""
import pathlib
import shlex
import unittest
from unittest.mock import patch

import test_owner_update as base

ROOT, owner = base.ROOT, base.owner
DESKTOP = pathlib.Path('/usr/libexec/aresos-desktop')
MISSING = ("The desktop's own program (aresos-desktop) is not running for ares: "
    'the session did not start it, or it gave up after repeated failures. '
    'This is about the running session, not about the tools; nothing was changed')


class SessionProgramTest(unittest.TestCase):
    def test_each_image_requires_exactly_its_own_program_with_and_without_it(self):
        exists = pathlib.Path.exists
        for desktop in (False, True):
            for found in (False, True):
                with self.subTest(desktop=desktop, found=found), base.route(base.pair()) as (tools, host, store):
                    read = host.read
                    expected = 'aresos-desktop' if desktop else 'foot'
                    def process(*command, **options):
                        if command == ('pgrep', '-u', 'ares', '-x', expected):
                            self.assertEqual(options, {'allowed': (0, 1)} if desktop else {})
                            host.trace.append(dict(command=list(command), mutation=False, returncode=0 if found else 1))
                            if not found and not desktop:
                                raise owner.Stop('Read failed: ' + ' '.join(command))
                            return '4242\n' if found else ''
                        return read(*command, **options)
                    with patch.object(pathlib.Path, 'exists', lambda p: desktop if p == DESKTOP else exists(p)), \
                            patch.object(host, 'read', side_effect=process):
                        if found:
                            tools.check()
                        else:
                            with self.assertRaises(owner.Stop) as caught:
                                tools.check()
                            self.assertEqual(str(caught.exception), MISSING if desktop else 'Read failed: pgrep -u ares -x foot')
                    asked = [r['command'][-1] for r in host.trace if r.get('command', [''])[0] == 'pgrep']
                    self.assertEqual(asked, ['labwc', expected])
                    self.assertFalse(host.changes)

    def test_requested_program_is_the_autostart_script_and_fits_pgrep_comm(self):
        autostart = (ROOT / 'os/config/usr/share/aresos/labwc/autostart').read_text()
        commands = [shlex.split(line) for line in autostart.splitlines() if line.startswith('/')]
        self.assertIn(str(DESKTOP), [argv[0] for argv in commands])
        self.assertTrue((ROOT / 'os/config' / DESKTOP.relative_to('/')).read_bytes().startswith(b'#!/usr/bin/python3'))
        self.assertLess(len(DESKTOP.name), 16)


if __name__ == '__main__':
    unittest.main()
