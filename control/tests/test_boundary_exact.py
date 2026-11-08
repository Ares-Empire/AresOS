"""Exact installed policy, protected ancestors and fixed production file paths."""
import copy
import json
import os
from pathlib import Path
from unittest.mock import patch

from aresos_control import boundary
from aresos_control.boundary_policy import managed_settings, managed_mcp
from support import EngineCase, ROOT
import test_boundary as previous


class ExactBoundary(EngineCase):
    def setUp(self):
        super().setUp()
        from boundary_test_support import fixture_boundary as install_boundary
        self.approval = self.reserve()
        self.config = install_boundary(self.root / 'boundary')
        fixture = patch.multiple(boundary, DEFAULT_SETTINGS=self.config['managed_settings'], DEFAULT_MCP=self.config['managed_mcp'])
        fixture.start()
        self.addCleanup(fixture.stop)
        self.engine.boundary = boundary.Boundary()
        self.settings = Path(self.config['managed_settings'])
        self.mcp = Path(self.config['managed_mcp'])
        self.original = json.loads(self.settings.read_text())

    assert_refuses_only_asking = previous.InstalledBoundary.assert_refuses_only_asking

    def test_review16_review_reproduction_and_every_extra_or_changed_setting_refuses_with_paths(self):
        cases = [({'sandbox': {'excludedCommands': ['aresos *']}, 'permissions': {'allow': ['Bash(aresos *)']}},
                  ['sandbox.excludedCommands', 'permissions.allow']),
                 ({'sandbox': {'filesystem': {'disabled': True}}}, ['sandbox.filesystem.disabled']),
                 ({'permissions': {'allow': ['Bash(echo *)']}}, ['permissions.allow']),
                 ({'sandbox': {'excludedCommands': ['echo *']}}, ['sandbox.excludedCommands']),
                 ({'sandbox': {'filesystem': {'allowWrite': ['/extra']}}}, ['sandbox.filesystem.allowWrite']),
                 ({'hooks': {}}, ['hooks']), ({'futureKey': True}, ['futureKey'])]
        def merge(target, updates):
            for key, value in updates.items():
                if isinstance(value, dict) and key in target:
                    merge(target[key], value)
                else:
                    target[key] = value
        for updates, paths in cases:
            settings = copy.deepcopy(self.original)
            merge(settings, updates)
            self.settings.write_text(json.dumps(settings))
            for path in paths:
                with self.subTest(update=updates, path=path):
                    self.assert_refuses_only_asking(path)
        self.settings.write_text(json.dumps(self.original))
        mcp = managed_mcp()
        mcp['mcpServers']['extra'] = mcp['mcpServers']['mail']
        self.mcp.write_text(json.dumps(mcp))
        self.assert_refuses_only_asking('mcpServers.extra')
        self.mcp.write_text(json.dumps({**managed_mcp(), 'extra': True}))
        self.assert_refuses_only_asking('extra')

    def test_review16_every_policy_leaf_mutation_refuses_and_formatting_order_is_canonical(self):
        def leaves(value, path=()):
            if isinstance(value, dict) and value:
                for key, child in value.items():
                    yield from leaves(child, path + (key,))
            else:
                yield path
        for path in leaves(self.original):
            settings = copy.deepcopy(self.original)
            parent = settings
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = None
            self.settings.write_text(json.dumps(settings))
            with self.subTest(path=path):
                self.assert_refuses_only_asking('.'.join(path))
        self.settings.write_text(json.dumps(self.original, sort_keys=True, indent=4))
        self.mcp.write_text(json.dumps(managed_mcp(), sort_keys=True))
        self.engine.boundary.require()
        self.assertEqual(self.original, managed_settings())
        self.assertEqual(json.loads((ROOT / 'control/settings/managed-mcp.json').read_text()), managed_mcp())
        dockerfile = (ROOT / 'control/boundary/Dockerfile').read_text()
        self.assertIn('cp /etc/claude-code/managed-settings.draft.json /etc/claude-code/managed-settings.json', dockerfile)

    def test_review16_ancestor_owner_group_world_and_symlink_each_refuse(self):
        real_fstat = os.fstat
        parents = [self.settings.parent, self.settings.parent.parent, self.settings.parent.parent.parent]
        for parent in parents:
            inode = parent.stat().st_ino
            for fault in ('owner', 'group', 'world'):
                def faulty(fd):
                    info = real_fstat(fd)
                    values = list(info)
                    if info.st_ino == inode:
                        if fault == 'owner':
                            values[4] = 12345
                        else:
                            values[0] |= 0o020 if fault == 'group' else 0o002
                    return os.stat_result(values)
                with self.subTest(parent=parent, fault=fault), patch('aresos_control.boundary.os.fstat', faulty):
                    self.assert_refuses_only_asking('root' if fault == 'owner' else 'writable')
        parent = self.settings.parent
        moved = parent.with_name('protected-copy')
        parent.rename(moved)
        parent.symlink_to(moved, target_is_directory=True)
        try:
            self.assert_refuses_only_asking('managed-settings.json')
        finally:
            parent.unlink()
            moved.rename(parent)

    def test_review16_service_configuration_cannot_supply_fixture_paths(self):
        from aresos_control.daemon import Daemon
        with self.assertRaises(TypeError):
            boundary.Boundary({'managed_settings': '/fixture', 'managed_mcp': '/fixture'})
        # Daemon passes no configuration-derived boundary paths to Engine.
        with patch('aresos_control.daemon.Engine', side_effect=RuntimeError('stop before sockets')) as factory:
            with self.assertRaises(RuntimeError):
                Daemon({'owner_uid': os.geteuid() + 1, 'state_dir': '/unused', 'evidence_dir': '/unused',
                        'managed_settings': '/fixture', 'managed_mcp': '/fixture'})
            self.assertNotIn('boundary_config', factory.call_args.kwargs)
            self.assertEqual(len(factory.call_args.args), 5)

    def test_review16_root_fixture_uses_protected_container_prefix_and_reuses_path(self):
        from boundary_test_support import fixture_boundary, _FIXTURES
        logical = str(self.root / 'new-identity')
        protected = str(self.root / 'simulated-container-fixture')
        with patch('boundary_test_support.os.geteuid', return_value=0), \
             patch('boundary_test_support.Path.mkdir'), \
             patch('boundary_test_support.tempfile.mkdtemp', return_value=protected) as temporary, \
             patch('boundary_test_support.install_boundary', return_value={'fixture': True}) as install:
            self.assertEqual(fixture_boundary(logical), {'fixture': True})
            fixture_boundary(logical)
            self.assertEqual(temporary.call_count, 1)
            self.assertEqual(temporary.call_args.kwargs['dir'], Path('/etc/claude-code/fixtures'))
            self.assertEqual(install.call_args.args, (Path(protected),))
        _FIXTURES.pop(logical)

    def test_review16_generated_source_locks_present_and_no_managed_hooks_file_is_loaded(self):
        settings = managed_settings()
        for key in ('allowManagedMcpServersOnly', 'allowManagedPermissionRulesOnly', 'allowManagedHooksOnly'):
            self.assertTrue(settings[key])
        self.assertTrue(settings['sandbox']['filesystem']['allowManagedReadPathsOnly'])
        self.assertTrue(settings['sandbox']['network']['allowManagedDomainsOnly'])
        self.assertEqual(settings['allowedMcpServers'], [{'serverCommand': [v['command'], *v['args']]}
                                                        for v in managed_mcp()['mcpServers'].values()])
        # managed-hooks.json is a draft companion, not an independently loaded
        # policy file; adding a hooks key to the installed policy is a difference.
        self.assertNotIn('hooks', settings)
