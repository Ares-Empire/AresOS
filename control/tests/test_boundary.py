"""Installed policy is required for asking work, including same-UID socket calls."""
import copy
import json
import os
from pathlib import Path
from unittest.mock import patch

from aresos_control.boundary import Boundary, asking_rules, managed_servers
from boundary_test_support import install_boundary
from support import EngineCase, ROOT, message


class InstalledBoundary(EngineCase):
    def setUp(self):
        super().setUp()
        self.approval = self.reserve()
        self.config = install_boundary(self.root / 'boundary')
        self.engine.boundary = Boundary(self.config)
        self.settings = Path(self.config['managed_settings'])
        self.mcp = Path(self.config['managed_mcp'])
        self.original = json.loads(self.settings.read_text())

    def assert_refuses_only_asking(self, reason):
        for action, args in [('testapp_prepare_send', message()), ('testapp_send', self.approval)]:
            result = self.call(action, args)
            self.assertEqual(result['error']['code'], 'boundary_not_installed', result)
            self.assertIn(reason, result['error']['message'])
        self.assertEqual(self.engine.operation(self.approval['operation_id'])['state'], 'reserved')
        self.assertEqual(self.engine.receiver.evidence(self.approval['operation_id'])['arrivals'], [])
        self.data('testapp_list')
        self.configure()

    def test_each_required_setting_missing_and_wrong_refuses_preparation_and_submission(self):
        required = {'sandbox.enabled': True, 'sandbox.failIfUnavailable': True,
                    'sandbox.allowUnsandboxedCommands': False, 'sandbox.network.allowAllUnixSockets': False,
                    'permissions.disableBypassPermissionsMode': 'disable',
                    'allowManagedPermissionRulesOnly': True, 'allowManagedHooksOnly': True,
                    'sandbox.filesystem.denyRead': ['/run/aresos-tools']}
        for path, expected in required.items():
            for missing in (True, False):
                with self.subTest(path=path, missing=missing):
                    settings = copy.deepcopy(self.original)
                    parent = settings
                    parts = path.split('.')
                    for part in parts[:-1]:
                        parent = parent[part]
                    if missing:
                        del parent[parts[-1]]
                    else:
                        parent[parts[-1]] = not expected if type(expected) is bool else [] if type(expected) is list else 'enable'
                    self.settings.write_text(json.dumps(settings))
                    self.assert_refuses_only_asking(path)
        self.settings.write_text(json.dumps(self.original))
        self.engine.boundary.require()

    def test_all_generated_asking_rules_required_and_never_allowed_even_wildcards(self):
        for rule in asking_rules():
            for allowed in (False, True):
                with self.subTest(rule=rule, allowed=allowed):
                    settings = copy.deepcopy(self.original)
                    if allowed:
                        settings['permissions']['allow'].append(rule)
                    else:
                        settings['permissions']['ask'].remove(rule)
                    self.settings.write_text(json.dumps(settings))
                    self.assert_refuses_only_asking(rule)
        settings = copy.deepcopy(self.original)
        settings['permissions']['allow'] = ['mcp__mail__*']
        self.settings.write_text(json.dumps(settings))
        self.assert_refuses_only_asking('permissions.allow')

    def test_both_files_require_root_regular_nonwritable_nonsymlink(self):
        real_fstat = os.fstat
        for path in (self.settings, self.mcp):
            for fault in ('missing', 'owner', 'group', 'world', 'symlink', 'directory'):
                with self.subTest(file=path.name, fault=fault):
                    content = path.read_bytes()
                    try:
                        if fault == 'missing':
                            path.unlink()
                        elif fault in ('group', 'world'):
                            path.chmod(0o664 if fault == 'group' else 0o646)
                        elif fault == 'symlink':
                            target = path.with_suffix('.copy')
                            target.write_bytes(content)
                            path.unlink()
                            path.symlink_to(target)
                        elif fault == 'directory':
                            path.unlink()
                            path.mkdir()
                        if fault == 'owner':
                            inode = path.stat().st_ino
                            def wrong_owner(fd):
                                info = real_fstat(fd)
                                values = list(info)
                                if info.st_ino == inode:
                                    values[4] = 12345
                                return os.stat_result(values)
                            with patch('aresos_control.boundary.os.fstat', wrong_owner):
                                self.assert_refuses_only_asking('owned by root')
                        else:
                            self.assert_refuses_only_asking(path.name)
                    finally:
                        if path.is_dir():
                            path.rmdir()
                        elif path.exists() or path.is_symlink():
                            path.unlink()
                        path.write_bytes(content)
                        path.chmod(0o644)

    def test_exact_managed_servers_and_commands_and_default_paths(self):
        original = json.loads(self.mcp.read_text())
        for fault in ('missing', 'extra', 'command', 'args', 'extra_config'):
            data = copy.deepcopy(original)
            if fault == 'missing':
                del data['mcpServers']['mail']
            elif fault == 'extra':
                data['mcpServers']['rogue'] = data['mcpServers']['mail']
            elif fault == 'command':
                data['mcpServers']['mail']['command'] = '/bin/false'
            elif fault == 'args':
                data['mcpServers']['mail']['args'].append('--other')
            else:
                data['mcpServers']['mail']['env'] = {'EXTRA': '1'}
            with self.subTest(fault=fault):
                self.mcp.write_text(json.dumps(data))
                self.assert_refuses_only_asking('mcpServers')
        from aresos_control import boundary
        defaults = Boundary()
        self.assertEqual(defaults.settings, boundary.DEFAULT_SETTINGS)
        self.assertEqual(defaults.mcp, boundary.DEFAULT_MCP)
        self.assertIsNotNone(Boundary({'managed_settings': '/missing', 'managed_mcp': '/missing'}).reason)

    def test_boundary_image_generated_files_pass_and_restored_policy_enables_submission(self):
        # Match Dockerfile's COPY settings/ and cp of the managed draft verbatim.
        self.assertEqual(self.original, json.loads((ROOT / 'control/settings/managed-settings.draft.json').read_text()))
        self.assertEqual(json.loads(self.mcp.read_text())['mcpServers'], managed_servers())
        self.engine.boundary.require()
        self.settings.unlink()
        self.assert_refuses_only_asking('managed-settings.json')
        self.config = install_boundary(self.root / 'boundary')
        result = self.data('testapp_send', self.approval)
        self.assertEqual(result['operation']['state'], 'done')
