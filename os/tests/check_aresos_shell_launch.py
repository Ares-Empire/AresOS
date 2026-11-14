"""Explicit AresOS check of the real launch route; hosted Ubuntu has no user manager for systemd-run --user.

Run: python3 -m unittest discover -s os/tests -p 'check_aresos_shell_launch.py' -v
Security review 1, FIX 4: the parsed Exec words reach the program unchanged through the real
`systemd-run --user --scope` command. The stand-in program only writes its arguments and its cgroup
to a private file and exits; it opens no window, and no session display variable is passed to it.
Package 30b: a reviewed hint's start settings reach the program through the same route. Its stand-in
writes its environment to a private file and exits; it is never Lunar Client.
"""
import json
import os
import pathlib
import secrets
import subprocess
import tempfile
import unittest
from unittest import mock

from test_aresos_shell import shell

LITERAL = '${HOME}'


class LaunchBase(unittest.TestCase):
    def launch(self, launcher):
        unit_id = secrets.token_hex(8)
        process = launcher.spawn(self.app, self.argv, self.directory, unit_id)
        unit = launcher.unit(self.app, unit_id)
        try:
            self.assertEqual(process.wait(timeout=30), 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            # The scope ends with the stand-in (--collect); stop it by the name we hold if it did not.
            subprocess.run([shell.SYSTEMCTL, '--user', 'stop', unit], capture_output=True, timeout=30)
        return json.loads(self.output.read_text()), unit


class RealLaunchRouteTest(LaunchBase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name)
        self.output = self.root / 'arguments.json'
        standin = self.root / 'stand-in'
        standin.write_text('#!/usr/bin/python3\nimport json, sys\n'
                           'cgroup = open("/proc/self/cgroup").read()\n'
                           f'open({str(self.output)!r}, "w").write(json.dumps({{"argv": sys.argv[1:], '
                           '"cgroup": cgroup}))\n')
        standin.chmod(0o700)
        entries, registry = self.root / 'applications', self.root / 'registry'
        entries.mkdir()
        registry.mkdir()
        # String escape \\ then Exec quoting \$ give the literal word ${HOME}; %c is Name, %i is --icon Icon.
        (entries / 'org.aresos.LiteralCheck.desktop').write_text(
            '[Desktop Entry]\nType=Application\nName=${HOME}\nIcon=${HOME}\n'
            f'Exec={standin} "\\\\${{HOME}}" %c %i\n')
        apps, _ = shell.load_catalogue(str(registry), entry_dirs=[entries], executable=shell.executable_file)
        self.app = apps['org-aresos-literalcheck']
        argv, self.directory, reason = shell.resolve(self.app)
        self.assertIsNone(reason)
        self.assertEqual(argv[1:], [LITERAL, LITERAL, '--icon', LITERAL])
        self.argv = argv
        # Only what systemd-run needs to reach the user manager; HOME is distinctive so expansion would show.
        self.environ = {key: os.environ[key] for key in ('XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS', 'PATH')
                        if key in os.environ}
        self.environ['HOME'] = str(self.root / 'expanded-home')
        (self.root / 'expanded-home').mkdir()

    def test_literal_dollar_words_from_exec_name_and_icon_arrive_unchanged(self):
        launcher = shell.ScopeLauncher(environ=self.environ)
        command = launcher.command(self.app, self.argv, 'check')
        self.assertEqual(command[command.index('--') - 1], '--expand-environment=no')
        result, unit = self.launch(launcher)
        self.assertEqual(result['argv'], [LITERAL, LITERAL, '--icon', LITERAL])
        self.assertIn(f'/app.slice/{unit}', result['cgroup'])

    def test_control_the_same_route_without_the_flag_is_expanded_by_systemd(self):
        # Proves the check above can fail: systemd-run's default changes these words.
        original = shell.ScopeLauncher.command

        def without_flag(launcher, app, argv, launch_id):
            return [part for part in original(launcher, app, argv, launch_id) if part != '--expand-environment=no']

        with mock.patch.object(shell.ScopeLauncher, 'command', without_flag):
            result, _ = self.launch(shell.ScopeLauncher(environ=self.environ))
        self.assertEqual(result['argv'], [self.environ['HOME']] * 2 + ['--icon', self.environ['HOME']])


class HintedLaunchRouteTest(LaunchBase):
    """Package 30b: a stand-in desktop entry and its hint, both in this test's own folders."""

    HINT = {'schema': 1, 'desktop_id': 'org.aresos.HintedCheck.desktop', 'gpu': 'discrete',
            'environment': {'SDL_VIDEO_DRIVER': 'wayland'}}

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name)
        entries, hints = self.root / 'applications', self.root / 'registry' / shell.HINTS
        entries.mkdir()
        hints.mkdir(parents=True)
        # Two programs, each its own stand-in (one shared file name would make both window identities clash).
        for name in ('Hinted', 'Plain'):
            standin = self.root / f'stand-in-{name.lower()}'
            standin.write_text('#!/usr/bin/python3\nimport json, os\n'
                               f'open({str(self.root / name.lower())!r} + ".json", "w")'
                               '.write(json.dumps(dict(os.environ)))\n')
            standin.chmod(0o700)
            (entries / f'org.aresos.{name}Check.desktop').write_text(
                f'[Desktop Entry]\nType=Application\nName={name} check\nExec={standin}\n')
        (hints / 'hinted.json').write_text(json.dumps(self.HINT))
        self.apps, _ = shell.load_catalogue(str(self.root / 'registry'), entry_dirs=[entries],
                                            executable=shell.executable_file)
        # Only what systemd-run needs, the session's own SDL choice, and a GPU key every start drops.
        self.environ = {key: os.environ[key] for key in ('XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS', 'PATH')
                        if key in os.environ}
        self.environ.update(HOME=str(self.root), SDL_VIDEO_DRIVER='x11', DRI_PRIME='inherited')

    def start(self, name):
        self.app = self.apps[f'org-aresos-{name}check']
        self.argv, self.directory, reason = shell.resolve(self.app)
        self.assertIsNone(reason)
        self.output = self.root / f'{name}.json'
        return self.launch(shell.ScopeLauncher(environ=self.environ))[0]

    def test_the_hints_values_arrive_and_the_nvidia_values_where_there_is_a_card(self):
        environment = self.start('hinted')
        self.assertEqual(environment['SDL_VIDEO_DRIVER'], 'wayland')
        nvidia = {key: environment.get(key) for key in shell.NVIDIA_OFFLOAD}
        # The laptop has an NVIDIA card (the report shows nvidia_present()); a machine without one gets none.
        self.assertEqual(nvidia, shell.NVIDIA_OFFLOAD if shell.nvidia_present() else dict.fromkeys(nvidia))
        self.assertNotIn('DRI_PRIME', environment)

    def test_control_a_program_without_a_hint_gets_the_sessions_values_only(self):
        # Proves the stand-in reports what it was given: the session's SDL choice arrives unchanged here.
        environment = self.start('plain')
        self.assertEqual(environment['SDL_VIDEO_DRIVER'], 'x11')
        self.assertFalse(set(shell.GPU_KEYS) & set(environment))


if __name__ == '__main__':
    unittest.main()
