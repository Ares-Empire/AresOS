"""Round 17: every local managed source is part of asking admission."""
import importlib.util
import json
import os
from pathlib import Path
from subprocess import CompletedProcess
import hashlib
from unittest.mock import patch

from aresos_control import boundary
from aresos_control.common import Refused
from support import ROOT, EngineCase
import test_boundary_exact as previous


class PolicySources(EngineCase):
    def setUp(self):
        super().setUp()
        from boundary_test_support import fixture_boundary
        self.approval = self.reserve()
        config = fixture_boundary(self.root / 'boundary')
        fixture = patch.multiple(boundary, DEFAULT_SETTINGS=config['managed_settings'], DEFAULT_MCP=config['managed_mcp'])
        fixture.start()
        self.addCleanup(fixture.stop)
        self.engine.boundary = boundary.Boundary()
        self.settings = Path(config['managed_settings'])

    assert_refuses_only_asking = previous.ExactBoundary.assert_refuses_only_asking
    def test_review17_drop_in_reproduction_names_file_and_all_entries_refuse(self):
        directory = self.settings.with_name('managed-settings.d')
        directory.mkdir()
        self.engine.boundary.require()
        for name, content in [('99-open.json', json.dumps({'sandbox': {'excludedCommands': ['aresos *']},
                     'permissions': {'allow': ['Bash(aresos *)']}})), ('notes.txt', 'ignored by Claude'),
                     ('.hidden', ''), ('subdirectory', None)]:
            entry = directory / name
            if content is None:
                entry.mkdir()
            else:
                entry.write_text(content)
            try:
                self.assert_refuses_only_asking(name)
            finally:
                entry.rmdir() if content is None else entry.unlink()
        self.engine.boundary.require()
        directory.rmdir()
        self.engine.boundary.require()

    def test_review17_drop_in_symlink_and_unsafe_directory_refuse(self):
        directory = self.settings.with_name('managed-settings.d')
        target = self.settings.with_name('Documents')
        target.mkdir()
        for destination in (target, target / 'missing'):
            directory.symlink_to(destination, target_is_directory=True)
            self.assert_refuses_only_asking('managed-settings.d')
            directory.unlink()
        directory.mkdir()
        for mode in (0o775, 0o757):
            directory.chmod(mode)
            self.assert_refuses_only_asking('writable')
        directory.chmod(0o755)
        real_fstat, inode = os.fstat, directory.stat().st_ino
        def unowned(fd):
            info = real_fstat(fd)
            if info.st_ino == inode:
                fields = list(info)
                fields[4] = 12345
                return os.stat_result(fields)
            return info
        with patch('aresos_control.boundary.os.fstat', unowned):
            self.assert_refuses_only_asking('root')

    def test_review18_private_home_and_remote_cache_are_never_traversed(self):
        remote = self.settings.parent / 'private-owner' / '.claude' / 'remote-settings.json'
        real_open = os.open
        def private(path, *args, **kwargs):
            if str(path) in {'private-owner', str(remote)}:
                raise PermissionError('Owner home is private')
            return real_open(path, *args, **kwargs)
        # The former constant is supplied only to demonstrate the old failure.
        with patch.object(boundary, 'DEFAULT_REMOTE', str(remote), create=True), \
             patch('aresos_control.boundary.os.open', side_effect=private):
            self.engine.boundary.require()
        remote.parent.mkdir(parents=True)
        for symlink in (False, True):
            if symlink:
                remote.symlink_to(remote.with_name('missing'))
            else:
                remote.write_text('{}')
            with patch.object(boundary, 'DEFAULT_REMOTE', str(remote), create=True):
                self.engine.boundary.require()
            remote.unlink()

    def test_review18_launcher_has_no_auth_restriction_and_keeps_boundary_and_canaries(self):
        spec = importlib.util.spec_from_file_location('policy_launcher', ROOT / 'control/boundary/launch.py')
        launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        content = b'Synthetic pinned executable'
        checksum = hashlib.sha256(content).hexdigest()
        def config(path, *args, **kwargs):
            return json.dumps({'seccomp_x64_sha256': checksum} if path.name == 'pins.json'
                              else {'sha256': checksum, 'cli_sha256': checksum})
        with patch.object(launcher.Boundary, 'require'), \
             patch.object(launcher, 'trusted'), \
             patch.object(launcher.Path, 'exists', return_value=False), \
             patch.object(launcher.Path, 'resolve', lambda path: path), \
             patch.object(launcher.Path, 'read_bytes', return_value=content), \
             patch.object(launcher.Path, 'read_text', config), \
             patch.object(launcher.os, 'access', return_value=True), \
             patch.object(launcher.os, 'chdir'), \
             patch.object(launcher.os, 'execve') as execute, \
             patch.object(launcher.subprocess, 'run', return_value=CompletedProcess([], 0, 'SECCOMP_CANARY_OK')) as run:
            launcher.main()
            self.assertEqual(run.call_count, 2)
            self.assertIn('seccomp-canary.py', run.call_args_list[0].args[0][-1])
            self.assertEqual(run.call_args_list[1].args[0][-1], '--native-canary')
            self.assertEqual(execute.call_args.args[1], [str(launcher.CLAUDE), '--setting-sources', ''])
        with patch.object(launcher.Boundary, 'require', side_effect=Refused('boundary_not_installed', 'drop-in')), \
             patch.object(launcher.os, 'execve') as execute:
            with self.assertRaises(Refused):
                launcher.main()
            execute.assert_not_called()
