"""Protected policy paths and subset admission after decision 24."""
import copy
import json
import os
from pathlib import Path
from unittest.mock import patch

from aresos_control import boundary
from aresos_control.boundary_policy import managed_settings
from support import EngineCase, ROOT
import test_boundary as previous


class ExactBoundary(EngineCase):
    def setUp(self):
        super().setUp()
        from boundary_test_support import fixture_boundary as install_boundary
        self.approval = self.reserve()
        self.config = install_boundary(self.root / 'boundary')
        fixture = patch.multiple(boundary, DEFAULT_SETTINGS=self.config['managed_settings'])
        fixture.start()
        self.addCleanup(fixture.stop)
        self.engine.boundary = boundary.Boundary()
        self.settings = Path(self.config['managed_settings'])
        self.original = json.loads(self.settings.read_text())

    assert_refuses_only_asking = previous.InstalledBoundary.assert_refuses_only_asking

    def test_additional_rules_hooks_and_settings_do_not_block_tools(self):
        settings = copy.deepcopy(self.original)
        settings.update({'futureKey': True, 'sandbox': {'enabled': False, 'excludedCommands': ['aresos *']},
                         'allowedMcpServers': [{'serverName': 'personal'}]})
        settings['permissions'].update({'allow': ['mcp__mail__*'], 'defaultMode': 'bypassPermissions'})
        settings['permissions']['ask'] += ['Bash', 'WebSearch']
        settings['hooks']['PermissionRequest'] = [{'hooks': [{'type': 'command', 'command': 'true'}]}]
        self.settings.write_text(json.dumps(settings, sort_keys=True, indent=4))
        self.engine.boundary.require()
        self.assertEqual(self.data('testapp_send', self.approval)['operation']['state'], 'done')

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
