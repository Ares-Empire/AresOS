"""Round 17: every local managed source is part of asking admission."""
import importlib.util
import json
import os
from pathlib import Path
from subprocess import CompletedProcess
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

    def test_review17_remote_cache_and_any_symlink_refuse(self):
        remote = self.settings.parent / 'personal' / 'remote-settings.json'
        remote.parent.mkdir()
        with patch.object(boundary, 'DEFAULT_REMOTE', str(remote)):
            self.engine.boundary.require()
            remote.write_text('{}')
            self.assert_refuses_only_asking('remote-settings.json')
            remote.unlink()
            remote.symlink_to(remote.with_name('missing'))
            self.assert_refuses_only_asking('remote-settings.json')
            remote.unlink()
            remote.parent.rmdir()
            remote.parent.symlink_to(self.settings.parent, target_is_directory=True)
            self.assert_refuses_only_asking('remote-settings.json')

    def test_review17_launcher_refuses_unknown_or_remote_eligible_authentication(self):
        spec = importlib.util.spec_from_file_location('policy_launcher', ROOT / 'control/boundary/launch.py')
        launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        for status in ({'loggedIn': False}, *[{'loggedIn': True, 'authMethod': 'claude.ai',
                                             'subscriptionType': plan} for plan in ('pro', 'max', 'ultra')]):
            with patch.object(launcher.subprocess, 'run', return_value=CompletedProcess([], 0, json.dumps(status))):
                launcher.personal_login()
        for status in ({}, {'loggedIn': True}, *[{'loggedIn': True, 'authMethod': 'claude.ai',
                                'subscriptionType': plan} for plan in ('team', 'enterprise', 'unknown')],
                       {'loggedIn': True, 'authMethod': 'api_key', 'subscriptionType': 'pro'}):
            with patch.object(launcher.subprocess, 'run', return_value=CompletedProcess([], 0, json.dumps(status))):
                with self.assertRaisesRegex(ValueError, 'remote policy'):
                    launcher.personal_login()
        with patch.object(launcher.Boundary, 'require', side_effect=Refused('boundary_not_installed', 'drop-in')), \
             patch.object(launcher.os, 'execve') as execute:
            with self.assertRaises(Refused):
                launcher.main()
            execute.assert_not_called()
