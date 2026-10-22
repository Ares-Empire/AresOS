import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch
from audit import inventory, live_states, offenders

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
from activation_audit import inventory as activation_inventory, live_manager


class UpdaterAuditTest(unittest.TestCase):
    def test_disguised_updater_in_enabled_system_and_user_unit_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            for scope in ('system', 'user'):
                directory = root / 'etc/systemd' / scope
                wants = directory / 'default.target.wants'
                wants.mkdir(parents=True)
                (directory / 'surprise.service').write_text('[Unit]\nDescription=Maintenance\n[Service]\nExecStart=/usr/bin/uupd\n[Install]\nWantedBy=default.target\n')
                (wants / 'surprise.service').symlink_to('../surprise.service')
            rejected = offenders(inventory(root), {})
            self.assertEqual({u['scope'] for u in rejected}, {'system', 'user'})
            self.assertTrue(all(u['name'] == 'surprise.service' for u in rejected))

    def test_reviewed_bookkeeping_and_masked_updater_are_accepted(self):
        units = [dict(name='systemd-update-utmp.service', state='enabled', suspicious=True),
                 dict(name='uupd.timer', state='masked', suspicious=True)]
        self.assertEqual(offenders(units, {'systemd-update-utmp.service': 'utmp only'}), [])

    def test_updater_added_by_dropin_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            directory = root / 'etc/systemd/system'
            user_directory = root / 'etc/systemd/user'
            user_directory.mkdir(parents=True)
            (user_directory / 'ordinary.service').write_text('[Service]\nExecStart=/usr/bin/true\n')
            (directory / 'default.target.wants').mkdir(parents=True)
            (directory / 'ordinary.service').write_text('[Service]\nExecStart=/usr/bin/true\n[Install]\nWantedBy=default.target\n')
            (directory / 'default.target.wants/ordinary.service').symlink_to('../ordinary.service')
            (directory / 'ordinary.service.d').mkdir()
            (directory / 'ordinary.service.d/override.conf').write_text('[Service]\nExecStart=\nExecStart=/usr/bin/uupd\n')
            self.assertEqual([u['name'] for u in offenders(inventory(root), {})], ['ordinary.service'])

    def test_suspicious_units_require_mask_or_review_in_every_state(self):
        for state in ('static', 'disabled', 'indirect', 'generated', 'transient', 'enabled', 'enabled-runtime', 'alias'):
            unit = dict(name='surprise.service', state=state, suspicious=True)
            with self.subTest(state=state):
                self.assertEqual(offenders([unit], {}), [unit])
                self.assertEqual(offenders([unit], {'surprise.service': 'reviewed'}), [])
        self.assertEqual(offenders([dict(name='uupd.service', state='masked-runtime', suspicious=True)], {}), [])
        running = dict(name='uupd.service', state='masked', suspicious=True, active_state='active')
        self.assertEqual(offenders([running], {}), [running])

    def test_masked_but_running_updater_is_rejected_in_every_live_state(self):
        for state in ('active', 'activating', 'reloading', 'deactivating'):
            unit = dict(name='uupd.service', state='masked', suspicious=True, active_state=state)
            with self.subTest(state=state):
                self.assertEqual(offenders([unit], {}), [unit])
        unit = dict(name='uupd.service', state='masked', suspicious=True, active_state='inactive', sub_state='running')
        self.assertEqual(offenders([unit], {}), [unit])

    def test_static_live_inventory_reads_generated_files_and_both_manager_states(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            for scope in ('system', 'user'):
                directory = root / scope
                (directory / 'generator').mkdir(parents=True)
                (directory / 'routine.service').write_text('[Service]\nExecStart=/usr/bin/uupd\n')
                (directory / 'generator/at-boot.service').write_text('[Service]\nExecStart=/usr/bin/bootc upgrade\n')
                (directory / 'uupd.service').write_text('[Service]\nExecStart=/usr/bin/uupd\n')

            def manager(args, **kwargs):
                if 'list-unit-files' in args:
                    return 'routine.service static\nuupd.service masked\n'
                if 'list-units' in args:
                    return ('routine.service loaded inactive dead\nuupd.service masked active running\n'
                            'at-boot.service loaded inactive dead\n'
                            'dbus-:1.4-ordinary@0.service loaded inactive dead\n')
                self.fail(f'Unexpected graph/property query: {args}')

            def directories(guest_root, scope):
                return [root / scope, root / scope / 'generator']

            with patch('audit.unit_directories', side_effect=directories), \
                    patch('audit.subprocess.check_output', side_effect=manager) as calls:
                units = inventory(live=True)
            rejected = offenders(units, {})
            self.assertEqual({(u['scope'], u['name']) for u in rejected},
                             {(scope, name) for scope in ('system', 'user')
                              for name in ('routine.service', 'at-boot.service', 'uupd.service')})
            self.assertTrue(all(u['sources'] for u in rejected))
            self.assertTrue(any('runuser' in call.args[0] and '--user' in call.args[0] for call in calls.call_args_list))

    def test_missing_live_user_manager_is_a_failure(self):
        import subprocess

        def manager(args, **kwargs):
            if 'runuser' in args:
                raise subprocess.CalledProcessError(1, args)
            return ''

        with patch('audit.subprocess.check_output', side_effect=manager):
            with self.assertRaises(subprocess.CalledProcessError):
                inventory(live=True)

    def test_live_state_rows_are_validated(self):
        with patch('audit.subprocess.check_output', side_effect=['', 'ordinary.service loaded\n']):
            with self.assertRaises(AssertionError):
                live_states(['systemctl'])

    def test_generated_cockpit_auto_update_entry_point_requires_its_policy_mask(self):
        name = 'cockpit-container.service'
        policy = pathlib.Path(__file__).resolve().parents[1] / 'policy/masked-system-units.txt'
        self.assertIn(name, policy.read_text().splitlines())
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / 'etc/systemd/system').mkdir(parents=True)
            (root / 'etc/systemd/user').mkdir()
            (root / 'etc/systemd/user/ordinary.service').write_text('[Service]\nExecStart=/usr/bin/true\n')
            (root / 'etc/systemd/system' / name).symlink_to('/dev/null')
            generated = root / 'run/systemd/generator'
            generated.mkdir(parents=True)
            (generated / name).write_text('[Service]\nExecStart=/usr/bin/podman run '
                                          '--label io.containers.autoupdate=registry '
                                          'quay.io/cockpit/ws:latest /container/label-run\n')
            unit = next(u for u in inventory(root) if u['scope'] == 'system' and u['name'] == name)
            self.assertTrue(unit['suspicious'])
            self.assertEqual(unit['state'], 'masked')
            self.assertIn(str(generated / name), unit['sources'])
            self.assertEqual(offenders([unit], {}), [])
            self.assertEqual(offenders([dict(unit, state='generated')], {}), [dict(unit, state='generated')])
            self.assertEqual(offenders([dict(unit, active_state='active')], {}), [dict(unit, active_state='active')])


class ActivationAuditPrototypeTest(unittest.TestCase):
    """Keep the deferred graph/parser regressions running, outside VM acceptance."""

    def test_live_static_updater_activated_by_innocent_timer_and_generated_updater_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary)
            static = directory / 'routine.service'
            static.write_text('[Service]\nExecStart=/usr/bin/uupd\n')
            generated = directory / 'at-boot.service'
            generated.write_text('[Service]\nExecStart=/usr/bin/bootc upgrade\n')

            def manager(args, **kwargs):
                if 'list-unit-files' in args:
                    return 'routine.timer enabled\nroutine.service static\nat-boot.service generated\n'
                if 'list-units' in args:
                    return 'routine.timer loaded active waiting\nat-boot.service loaded inactive dead\n'
                if 'show' in args:
                    return ('Id=routine.timer\nUnitFileState=enabled\nActiveState=active\nTriggers=routine.service\n\n'
                            f'Id=routine.service\nUnitFileState=static\nFragmentPath={static}\n\n'
                            f'Id=at-boot.service\nUnitFileState=generated\nFragmentPath={generated}\n')
                self.fail(args)

            with patch('activation_audit.subprocess.check_output', side_effect=manager) as command:
                units = activation_inventory(live=True)
            rejected = offenders(units, {})
            self.assertEqual({(u['scope'], u['name']) for u in rejected},
                             {(scope, name) for scope in ('system', 'user')
                              for name in ('routine.service', 'at-boot.service')})
            self.assertTrue(all(u['pulled_by'] == ['routine.timer'] for u in rejected if u['name'] == 'routine.service'))
            self.assertTrue(any('runuser' in call.args[0] and '--user' in call.args[0] for call in command.call_args_list))

    def test_live_dependencies_and_transient_commands_are_inspected(self):
        def manager(args, **kwargs):
            if 'list-unit-files' in args:
                return 'routine.target enabled\n'
            if 'list-units' in args:
                return 'routine.target loaded active active\n'
            if 'show' in args and 'routine.target' in args:
                return 'Id=routine.target\nUnitFileState=enabled\nWants=dynamic.service\n'
            if 'show' in args and 'dynamic.service' in args:
                return 'Id=dynamic.service\nActiveState=inactive\nExecStart={ path=/usr/bin/uupd ; }\n'
            self.fail(args)
        with patch('activation_audit.subprocess.check_output', side_effect=manager):
            rejected = offenders(activation_inventory(live=True), {})
        self.assertEqual(len(rejected), 2)
        self.assertTrue(all(u['name'] == 'dynamic.service' and u['pulled_by'] == ['routine.target'] for u in rejected))

    def test_live_root_units_are_arguments_and_aliases_are_preserved(self):
        def manager(args, **kwargs):
            if 'list-unit-files' in args:
                return 'default.target alias\nordinary.target enabled\n'
            if 'list-units' in args:
                return '-.mount loaded active mounted\n'
            self.assertIn('show', args)
            self.assertEqual(args[args.index('--') + 1:], ['-.mount', 'default.target', 'ordinary.target'])
            return ('Id=-.mount\nNames=-.mount\nActiveState=active\n\n'
                    'Id=ordinary.target\nNames=ordinary.target default.target\nUnitFileState=enabled\n')
        with patch('activation_audit.subprocess.check_output', side_effect=manager):
            _, units = live_manager('system', ['systemctl'])
        self.assertEqual(units['-.mount']['ActiveState'], 'active')
        self.assertIs(units['default.target'], units['ordinary.target'])

    def test_quoted_escaped_manager_names_and_dependencies_are_round_tripped(self):
        name = r'system-dbus\x2d:1.4\x2dorg.fedoraproject.SetroubleshootPrivileged.slice'
        encoded = json.dumps(name)

        def manager(args, **kwargs):
            if 'list-unit-files' in args:
                return 'ordinary.target enabled\n'
            if 'list-units' in args:
                return 'ordinary.target loaded active active\n'
            if 'ordinary.target' in args:
                return f'Id=ordinary.target\nNames=ordinary.target\nWants={encoded}\n'
            # The user-manager command also has runuser's own separator.
            self.assertEqual(args[args.index('--', args.index('show')) + 1:], [name])
            return f'Id={name}\nNames={encoded}\nActiveState=active\n'

        with patch('activation_audit.subprocess.check_output', side_effect=manager):
            units = activation_inventory(live=True)
        slices = [unit for unit in units if unit['name'] == name]
        self.assertEqual(len(slices), 2)
        self.assertTrue(all(unit['pulled_by'] == ['ordinary.target'] for unit in slices))
        self.assertTrue(all(unit['activation']['Wants'] == [name] for unit in units if unit['name'] == 'ordinary.target'))

    def test_quoted_live_dropin_path_is_inspected(self):
        with tempfile.TemporaryDirectory() as temporary:
            dropin = pathlib.Path(temporary) / 'override with spaces.conf'
            dropin.write_text('[Service]\nExecStart=/usr/bin/uupd\n')

            def manager(args, **kwargs):
                if 'list-unit-files' in args:
                    return 'ordinary.service static\n'
                if 'list-units' in args:
                    return 'ordinary.service loaded inactive dead\n'
                return ('Id=ordinary.service\nNames=ordinary.service\nUnitFileState=static\n'
                        f'DropInPaths={json.dumps(str(dropin))}\n')

            with patch('activation_audit.subprocess.check_output', side_effect=manager):
                rejected = offenders(activation_inventory(live=True), {})
            self.assertEqual({unit['scope'] for unit in rejected}, {'system', 'user'})
            self.assertTrue(all(unit['sources'] == [str(dropin)] for unit in rejected))


if __name__ == '__main__':
    unittest.main()
