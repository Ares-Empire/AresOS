import hashlib
import json
import pathlib
import shlex
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
import keyboard_proof as keyboard
import two_disk_vm as vm


class InstallationTask:
    def run(self):
        get_missing_keyboard_configuration()
        write_vc_configuration()


class KeyboardProofTest(unittest.TestCase):
    def test_proof_only_reads_bus_and_localed_even_with_nonempty_live_options(self):
        wrapper = Mock()
        wrapper.keymap = 'us'
        wrapper.get_layouts_variants.return_value = ['de']
        wrapper.options = ['caps:escape']
        for method in ('set_keymap', 'set_layouts', 'convert_layouts', 'convert_keymap',
                       'set_and_convert_layouts', 'set_and_convert_keymap'):
            getattr(wrapper, method).side_effect = AssertionError('Localed setter reached: ' + method)
        modules = {
            'pyanaconda.modules.localization.installation': types.SimpleNamespace(KeyboardInstallationTask=InstallationTask),
            'pyanaconda.modules.localization.localed': types.SimpleNamespace(LocaledWrapper=lambda: wrapper)}
        digest = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
        values = dict(XLayouts='as 1 "de"', VirtualConsoleKeymap='s ""', LayoutSwitchingOptions='as 0')
        with patch.dict(sys.modules, modules), patch.object(keyboard.pathlib.Path, 'read_text', return_value='unix:path=/fixture'), \
             patch.object(keyboard.subprocess, 'check_output', side_effect=lambda command, **kw: values[command[-1]]) as bus:
            proof = keyboard.read_only_proof(digest)
            self.assertEqual(bus.call_count, 6)
            with self.assertRaisesRegex(AssertionError, 'differs from extracted ISO'):
                keyboard.read_only_proof('0' * 64)
            settings = dict(XLayouts=['de'], VirtualConsoleKeymap='', LayoutSwitchingOptions=[])
            with patch.object(keyboard, 'module_settings', side_effect=[settings, dict(settings, LayoutSwitchingOptions=['caps:escape'])]), self.assertRaisesRegex(AssertionError, 'Proof changed'):
                keyboard.read_only_proof(digest)
        self.assertEqual(proof['live_localed']['options'], ['caps:escape'])
        self.assertTrue(proof['read_only'] and proof['module_configuration_unchanged'])
        self.assertNotIn('live_configuration_restored', proof)
        for method in ('set_keymap', 'set_layouts', 'convert_layouts', 'convert_keymap',
                       'set_and_convert_layouts', 'set_and_convert_keymap'):
            getattr(wrapper, method).assert_not_called()

    def test_wrong_module_layout_or_console_and_changed_switch_options_fail(self):
        settings = dict(XLayouts=['de'], VirtualConsoleKeymap='', LayoutSwitchingOptions=[])
        with patch.object(keyboard.pathlib.Path, 'read_text', return_value='fixture'):
            for wrong in (dict(settings, XLayouts=['us']), dict(settings, VirtualConsoleKeymap='us')):
                with patch.object(keyboard, 'module_settings', return_value=wrong), self.assertRaises(AssertionError):
                    keyboard.read_only_proof('unused')
        # The host validator independently rejects any changed module property.
        from installer_webui import validate_keyboard_proof
        proof = dict(xlayouts=['de'], model_keymap='', layout_switching_options=[], read_only=True,
                     same_installation_resolver=True, module_configuration_unchanged=True,
                     module_before=settings, module_after=dict(settings, LayoutSwitchingOptions=['caps:escape']))
        with self.assertRaises(AssertionError):
            validate_keyboard_proof(proof)

    def test_installed_files_accept_both_console_forms_and_exact_options(self):
        for keymap in ('de', '"de"'):
            for option_line, expected in [('', []), (' Option "XkbOptions" ""\n', []),
                    (' Option "XkbOptions" "grp:alt_shift_toggle,caps:escape"\n', ['grp:alt_shift_toggle', 'caps:escape'])]:
                record = dict(files={'etc/vconsole.conf': 'KEYMAP=' + keymap + '\nFONT="eurlatgr"\n',
                    'etc/X11/xorg.conf.d/00-keyboard.conf': 'Section "InputClass"\n Option "XkbLayout" "de"\n' + option_line + 'EndSection\n'})
                self.assertEqual(keyboard.validate_installed_keyboard(record, expected)['status'], 'passed')

    def test_installed_wrong_console_layout_missing_files_and_options_fail(self):
        files = {'etc/vconsole.conf': 'KEYMAP="de"\n',
                 'etc/X11/xorg.conf.d/00-keyboard.conf': ' Option "XkbLayout" "de"\n'}
        for changed in [dict(files, **{'etc/vconsole.conf': 'KEYMAP=us\n'}),
                        dict(files, **{'etc/X11/xorg.conf.d/00-keyboard.conf': ' Option "XkbLayout" "us"\n'}),
                        dict(files, **{'etc/vconsole.conf': None}),
                        dict(files, **{'etc/X11/xorg.conf.d/00-keyboard.conf': None}),
                        dict(files, **{'etc/X11/xorg.conf.d/00-keyboard.conf': files['etc/X11/xorg.conf.d/00-keyboard.conf'] + ' Option "XkbOptions" "caps:escape"\n'})]:
            with self.assertRaisesRegex(AssertionError, 'PRODUCT FAILURE'):
                keyboard.validate_installed_keyboard(dict(files=changed), [])
        with self.assertRaisesRegex(AssertionError, 'options differ'):
            keyboard.validate_installed_keyboard(dict(files=files), ['caps:escape'])

    def test_same_reader_command_reads_real_fixture_and_reports_missing_file(self):
        with tempfile.TemporaryDirectory(dir=pathlib.Path(__file__).parent) as directory:
            root = pathlib.Path(directory)
            (root / 'etc').mkdir()
            (root / 'etc/vconsole.conf').write_text('KEYMAP=de\n')
            executable, flag, program = shlex.split(vm.keyboard_reader_command(root))
            self.assertEqual((executable, flag), ('python3', '-c'))
            result = json.loads(subprocess.check_output([sys.executable, '-c', program]))
            self.assertEqual(result['files']['etc/vconsole.conf'], 'KEYMAP=de\n')
            self.assertIsNone(result['files']['etc/X11/xorg.conf.d/00-keyboard.conf'])
            with self.assertRaisesRegex(AssertionError, 'file missing'):
                keyboard.validate_installed_keyboard(result, [])
        with self.assertRaisesRegex(AssertionError, 'cannot use the live root'):
            vm.installed_keyboard(types.SimpleNamespace(mode='live'))


if __name__ == '__main__':
    unittest.main()
