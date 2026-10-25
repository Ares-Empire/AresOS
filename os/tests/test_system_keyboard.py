import importlib.machinery
import copy
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
    def starting(self, count=2):
        fixtures = ROOT / 'os/tests/fixtures/keyboard'
        state = json.loads((fixtures/'stock-two-rpm.json').read_text())
        bootc = json.loads((fixtures/'stock-two-bootc.json').read_text())
        if count == 1:
            state['deployments'] = state['deployments'][:1]
            bootc['status']['rollback'] = None
        return state, bootc

    def test_all_starting_states_preserve_identity_and_unrelated_arguments(self):
        for count, value in ((count, value) for count in (1,2) for value in ('de', 'us', 'fr', None, 'de vconsole.keymap=us rd.vconsole.keymap=fr vconsole.keymap_toggle=us')):
            with self.subTest(value=value, count=count):
                original = 'root=UUID=abc rw ostree=/ostree/boot.0/test/0'
                if value is not None:
                    original += ' vconsole.keymap=' + value
                corrected = 'root=UUID=abc rw ostree=/ostree/boot.1/test/0'
                state, bootc = self.starting(count)
                answers = [json.dumps(bootc), json.dumps(state), original, json.dumps(state), corrected if value else original]
                with patch.object(repair, 'output', side_effect=answers), patch.object(repair.subprocess, 'run') as run, patch('builtins.print'):
                    repair.fix()
                self.assertEqual(run.call_count, 2 if value else 0)
                if value:
                    self.assertEqual(run.call_args_list[0].args[0], ['ostree', 'admin', 'instutil', 'set-kargs', 'root=UUID=abc', 'rw', 'ostree=/ostree/boot.0/test/0'])

    def test_identity_rejects_duplicates_pending_nonbooted_and_layered(self):
        state, _ = self.starting()
        good, old = state['deployments']
        bad = [[], [good, good], [good, old, dict(old, serial=2)], [dict(good, staged=True)],
               [dict(good, booted=False)], [old,good], [dict(good, pinned=True)],
               [good,dict(old,pinned=True)], [good,dict(old,checksum='b'*64)],
               [good,dict(old,**{'container-image-reference':'other:stable'})]]
        for field in ('requested-base-local-replacements','requested-base-remote-replacements','packages','modules'):
            bad.append([good,dict(old,**{field:['bad']})])
        for deployments in bad:
            with self.subTest(deployments=deployments), self.assertRaises(AssertionError):
                repair.identity(dict(deployments=deployments))

    def test_whole_list_changes_fail_even_when_booted_identity_is_unchanged(self):
        for change in ('serial','pinned','removed','reordered'):
            state,bootc=self.starting(); after=copy.deepcopy(state)
            if change=='removed': after['deployments'].pop()
            elif change=='reordered': after['deployments'].reverse()
            else: after['deployments'][1][change] = 7 if change=='serial' else True
            answers=[json.dumps(bootc),json.dumps(state),'rw ostree=/ostree/test vconsole.keymap=us',json.dumps(after)]
            with self.subTest(change=change),patch.object(repair,'output',side_effect=answers),patch.object(repair.subprocess,'run'),self.assertRaises(AssertionError):
                repair.fix()

    def test_retained_11f_staged_update_and_mismatched_bootc_are_refused_before_write(self):
        state,bootc=self.starting()
        original=json.loads((ROOT/'os/manifest/ci/11f/full-2/two-disk/stock-status.json').read_text())
        for field,value in (('staged',original['status']['staged']),('rollbackQueued',True)):
            bad=copy.deepcopy(bootc);bad['status'][field]=value
            with self.subTest(field=field),patch.object(repair,'output',return_value=json.dumps(bad)),patch.object(repair.subprocess,'run') as run,self.assertRaises(AssertionError):
                repair.fix()
            run.assert_not_called()
        for field,value in (('checksum','b'*64),('deploySerial',0),('stateroot','other')):
            bad=copy.deepcopy(bootc);bad['status']['booted']['ostree'][field]=value
            with self.subTest(field=field),patch.object(repair,'output',side_effect=[json.dumps(bad),json.dumps(state)]),patch.object(repair.subprocess,'run') as run,self.assertRaises(AssertionError):
                repair.fix()
            run.assert_not_called()

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
