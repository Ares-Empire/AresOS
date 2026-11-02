"""Three physical profiles stay distinct; XKB alone splits layout/variant."""
import hashlib
import json
import pathlib
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
import owner_vm as vm
import keyboard_vm as kb


class LayoutAdapterTest(unittest.TestCase):
    def test_plain_us_runs_the_same_real_public_typing_chain_for_ascii(self):
        class Guest:
            owner_layout = 'us'
            owner_input_epoch = 0
            keys = vm.Guest.keys
            monitor = Mock()
            command = Mock()
            screenshot = Mock()
            capture_json = Mock(return_value=dict(XKB_DEFAULT_LAYOUT='us', XKB_DEFAULT_VARIANT=''))
        guest = Guest()
        console = Mock(root=True)
        previous = kb.TEXT, kb.type_text, kb.physical_keys
        with patch.object(vm, 'TEXT', 'yz-/!'), patch.object(vm.time, 'sleep'), patch.object(vm.td, 'save') as saved:
            vm.public_typing(guest, 'plain-us-helper', 'us', console, foot=True)
        expected = [['y'], ['z'], ['minus'], ['slash'], ['shift', '1'], ['ret']]
        events = [[key['data'] for key in call.args[1]['keys']] for call in guest.monitor.command.call_args_list]
        self.assertEqual(sum(events[i:i + len(expected)] == expected for i in range(len(events))), 2)
        self.assertEqual([call.args[1]['layout'] for call in saved.call_args_list], ['us', 'us'])
        self.assertTrue(all(call.args[1]['hold-time'] == 30 for call in guest.monitor.command.call_args_list))
        self.assertEqual((kb.TEXT, kb.type_text, kb.physical_keys), previous)
        with patch.object(vm.time, 'sleep'), patch.object(vm.td, 'save'):
            with self.assertRaisesRegex(AssertionError, 'Unknown or untypeable'):
                vm.public_typing(guest, 'plain-us-umlaut-refusal', 'us', console)
        self.assertEqual((kb.TEXT, kb.type_text, kb.physical_keys), previous)

    def test_x11_profiles_and_loaded_map_admit_international_without_a_fallback(self):
        for profile, expected in (('de', ('de', '')), ('us', ('us', '')), ('us-intl', ('us', 'intl'))):
            self.assertEqual(kb.x11_profile(profile), expected)
            letters = ('z', 'y') if profile == 'de' else ('y', 'z')
            kb.loaded_map('keycode 21 = +' + letters[0] + '\nkeycode 44 = +' + letters[1] + '\n', profile)
        for bad in ('', 'fr', 'US', None):
            with self.assertRaisesRegex(AssertionError, 'Unknown physical layout'):
                kb.x11_profile(bad)

    def test_international_dumpkeys_fixture_is_bound_and_checked_as_international(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        index = json.loads((root / 'os/tests/fixtures/owner-tools/layout-adapter-sources.json').read_text())
        for row in index['fixtures']:
            value = (root / row['path']).read_bytes()
            self.assertEqual(hashlib.sha256(value).hexdigest(), row['sha256'])
            kb.loaded_map(json.loads(value), 'us-intl')

    def test_foot_refuses_wrong_international_variant_before_any_typing(self):
        for env in (dict(XKB_DEFAULT_LAYOUT='us'), dict(XKB_DEFAULT_LAYOUT='us', XKB_DEFAULT_VARIANT=''),
                    dict(XKB_DEFAULT_LAYOUT='us-intl', XKB_DEFAULT_VARIANT='intl'),
                    dict(XKB_DEFAULT_LAYOUT='de', XKB_DEFAULT_VARIANT='intl')):
            guest = Mock()
            guest.capture_json.return_value = env
            with self.subTest(env=env), patch.object(kb, 'physical_input') as typed:
                with self.assertRaises(AssertionError):
                    kb.foot(guest, 'aresos-intl', 'us-intl')
                typed.assert_not_called()

    def test_only_an_omitted_profile_uses_the_guest_profile(self):
        guest = Mock(owner_layout='us-intl', owner_input_epoch=0)
        vm.type_text(guest, 'ü')
        guest.keys.assert_called_once_with(['alt_r', 'y'])
        guest.keys.reset_mock()
        for bad in ('', 'fr', False):
            with self.subTest(profile=bad), self.assertRaisesRegex(AssertionError, 'Unknown physical layout'):
                vm.type_text(guest, 'y', bad)
        guest.keys.assert_not_called()
        with self.assertRaisesRegex(AssertionError, 'Unknown or untypeable'):
            vm.type_text(guest, 'ü', 'us')
        guest.keys.assert_not_called()


if __name__ == '__main__':
    unittest.main()
