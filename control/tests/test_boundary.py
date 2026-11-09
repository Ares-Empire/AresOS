"""Installed policy is required for asking work, including same-UID socket calls."""
import copy
import json
import os
from pathlib import Path
from unittest.mock import patch

from aresos_control.boundary import Boundary, asking_rules
from boundary_test_support import fixture_boundary as install_boundary
from support import EngineCase, ROOT, message


class InstalledBoundary(EngineCase):
    def setUp(self):
        super().setUp()
        self.approval = self.reserve()
        self.config = install_boundary(self.root / 'boundary')
        boundary_patch = patch.multiple('aresos_control.boundary', DEFAULT_SETTINGS=self.config['managed_settings'])
        boundary_patch.start()
        self.addCleanup(boundary_patch.stop)
        self.engine.boundary = Boundary()
        self.settings = Path(self.config['managed_settings'])
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

    def test_each_generated_ask_rule_missing_or_misnamed_refuses(self):
        for rule in asking_rules():
            for replacement in (None, rule + '_wrong'):
                with self.subTest(rule=rule, replacement=replacement):
                    settings = copy.deepcopy(self.original)
                    settings['permissions']['ask'].remove(rule)
                    if replacement:
                        settings['permissions']['ask'].append(replacement)
                    self.settings.write_text(json.dumps(settings))
                    self.assert_refuses_only_asking(rule)
        self.settings.write_text(json.dumps(self.original))
        self.engine.boundary.require()

    def test_invalid_ask_shapes_refuse_without_dispatch(self):
        for settings in ([], {}, {'permissions': None}, {'permissions': {'ask': '*'}},
                         {'permissions': {'ask': [None]}}):
            with self.subTest(settings=settings):
                self.settings.write_text(json.dumps(settings))
                self.assert_refuses_only_asking('permissions.ask')

    def test_settings_require_root_regular_nonwritable_nonsymlink(self):
        real_fstat = os.fstat
        for path in (self.settings,):
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

    def test_default_paths_cannot_be_configured_by_a_client(self):
        from aresos_control import boundary
        self.assertEqual(Boundary().settings, boundary.DEFAULT_SETTINGS)
        with self.assertRaises(TypeError):
            Boundary({'managed_settings': '/missing'})

    def test_boundary_image_generated_files_pass_and_restored_policy_enables_submission(self):
        # Match Dockerfile's COPY settings/ and cp of the managed draft verbatim.
        self.assertEqual(self.original, json.loads((ROOT / 'control/settings/managed-settings.draft.json').read_text()))
        self.engine.boundary.require()
        self.settings.unlink()
        self.assert_refuses_only_asking('managed-settings.json')
        self.config = install_boundary(self.root / 'boundary')
        result = self.data('testapp_send', self.approval)
        self.assertEqual(result['operation']['state'], 'done')
