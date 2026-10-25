import importlib.machinery
import json
import pathlib
import sys
import types
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = (ROOT / 'os/release/system-keyboard.sh').read_text().split("<<'SYSTEM_KEYBOARD'\n")[1].split('\nSYSTEM_KEYBOARD')[0]
repair = types.ModuleType('repair')
exec(compile(SCRIPT, 'system-keyboard.sh', 'exec'), repair.__dict__)
loader = importlib.machinery.SourceFileLoader('keyboard_session', str(ROOT / 'os/config/usr/libexec/aresos-keyboard'))
session = types.ModuleType(loader.name)
loader.exec_module(session)


class SystemKeyboardTest(unittest.TestCase):
    def test_all_starting_states_preserve_identity_and_unrelated_arguments(self):
        for value in ('de', 'us', 'fr', None, 'de vconsole.keymap=us rd.vconsole.keymap=fr vconsole.keymap_toggle=us'):
            with self.subTest(value=value):
                original = 'root=UUID=abc rw ostree=/ostree/boot.0/test/0'
                if value is not None:
                    original += ' vconsole.keymap=' + value
                corrected = 'root=UUID=abc rw ostree=/ostree/boot.1/test/0'
                state = dict(transaction=None, deployments=[dict(checksum='abc', serial=0, osname='default', booted=True, pinned=False)])
                bootc = dict(status=dict(booted=dict(image=dict(imageDigest='sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151'), ostree=dict(checksum='abc'))))
                answers = [json.dumps(bootc), json.dumps(state), original, json.dumps(state), corrected if value else original]
                with patch.object(repair, 'output', side_effect=answers), patch.object(repair.subprocess, 'run') as run, patch('builtins.print'):
                    repair.fix()
                self.assertEqual(run.call_count, 2 if value else 0)
                if value:
                    self.assertEqual(run.call_args_list[0].args[0], ['ostree', 'admin', 'instutil', 'set-kargs', 'root=UUID=abc', 'rw', 'ostree=/ostree/boot.0/test/0'])

    def test_identity_rejects_duplicates_pending_nonbooted_and_layered(self):
        good = dict(checksum='abc', serial=0, osname='default', booted=True, pinned=False)
        for deployments in ([good, good], [dict(good, staged=True)], [dict(good, booted=False)],
                            [dict(good, **{'requested-base-local-replacements': ['bad']})]):
            with self.subTest(deployments=deployments), self.assertRaises(AssertionError):
                repair.identity(dict(deployments=deployments))

    def test_quoted_arguments_fail_closed(self):
        with self.assertRaises(AssertionError):
            repair.arguments('root=abc foo="two words"')

    def test_owner_block_equals_script(self):
        guide = (ROOT / 'docs/INSTALL.md').read_text()
        self.assertIn('```bash\n' + (ROOT / 'os/release/system-keyboard.sh').read_text().rstrip() + '\n```', guide)

    def test_session_uses_system_layout_variant_options_and_clears_stale_defaults(self):
        for layout, variant, options in (('de', '', ''), ('us', 'intl', 'compose:ralt'), ('de,us', ',intl', 'grp:alt_shift_toggle')):
            props = {'X11' + key: dict(type='s', data=value) for key, value in dict(Layout=layout, Model='pc105', Variant=variant, Options=options).items()}
            env = session.environment(dict(type='a{sv}', data=[props]), dict(PATH='/bin', XKB_DEFAULT_LAYOUT='stale', XKB_DEFAULT_RULES='stale'))
            self.assertEqual(env['XKB_DEFAULT_LAYOUT'], layout)
            self.assertEqual(env['XKB_DEFAULT_VARIANT'], variant)
            self.assertEqual(env['XKB_DEFAULT_OPTIONS'], options)
            self.assertEqual(env['XKB_DEFAULT_MODEL'], 'pc105')
            self.assertNotIn('XKB_DEFAULT_RULES', env)
            props['X11Layout']['data'] = ''
            with self.assertRaises(AssertionError):
                session.environment(dict(type='a{sv}', data=[props]), {})


if __name__ == '__main__':
    unittest.main()
