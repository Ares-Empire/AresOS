"""Literal loginctl selectors and source-format Key=Value refusal cases."""
import json
import pathlib
import unittest
from unittest.mock import patch

from test_owner_session import Model
from test_owner_tools import ROOT, owner


class PropertiesTest(unittest.TestCase):
    def test_source_format_selectors_and_order(self):
        fixture = json.loads((ROOT/'os/tests/fixtures/owner-tools/systemd-properties.json').read_text())
        model = Model()
        # Exact literal selector matching from loginctl258/259, not a helper
        # that accidentally expands commas and masks the old owner bug.
        for case in fixture['loginctl']:
            with self.subTest(case=case['options']):
                self.assertEqual(model.read('loginctl', 'show-session', '7', *case['options']), case['stdout'])
        model.calls.clear()
        with model.install() as tools:
            self.assertEqual(tools.session()['session'], '7')
        calls = [args for args in model.calls if args[:2] == ('loginctl', 'show-session')]
        self.assertTrue(all(',' not in opt for call in calls for opt in call[3:]))
        self.assertIn(('loginctl','show-session','7','--property=Service','--property=Type',
            '--property=Remote','--property=Name','--property=User'), calls)
        self.assertEqual(model.mutations, [])

    def test_each_property_exactly_once_malformed_missing_duplicate_extra_refuse(self):
        for names in (('Id','TTY','Audit','Scope'), ('Service','Type','Remote','Name','User'), ('TimestampMonotonic',)):
            model = Model()
            good = model.read('loginctl','show-session','7', *['--property='+n for n in names])
            lines = good.splitlines()
            bad = ['', '\n'.join(lines[:-1])+'\n', good+lines[0]+'\n',
                good+'Unexpected=1\n', good+'malformed\n', good+'\n',
                good.replace('=', ':', 1)]
            for output in bad:
                with self.subTest(names=names, output=output), patch.object(model,'read',return_value=output):
                    with self.assertRaisesRegex(owner.Stop, 'property refusal'):
                        owner.login_properties(model, '7', names, 'property refusal')
            self.assertEqual(model.mutations, [])

    def test_real_session_refuses_duplicate_fact_even_when_value_matches(self):
        model = Model(); original = model.read
        def read(*args):
            output = original(*args)
            return output+'Service=login\n' if '--property=Service' in args else output
        with model.install() as tools, patch.object(model,'read',side_effect=read):
            with self.assertRaisesRegex(owner.Stop, 'local physical recovery login'): tools.session()
        self.assertEqual(model.mutations, [])

    def test_journal_is_bounded_logind_json_only(self):
        model = Model(); tools = object.__new__(owner.Tools); tools.host=model
        with patch.object(model,'read',return_value='') as read:
            result = tools.logs()
        read.assert_called_once_with('journalctl','-b','-1','-u','systemd-logind.service',
            '--lines=200','--output=json','--no-pager')
        self.assertIn('200',result[0]); self.assertEqual(model.mutations, [])

    def test_source_bound_real_tool_formats(self):
        import hashlib
        import zipfile
        source = ROOT/'os/manifest/ci/14/14zr-property-sources'
        index = json.loads((source/'index.json').read_text())
        archive = source/index['archive']['path']
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), index['archive']['sha256'])
        with zipfile.ZipFile(archive) as files:
            for row in index['sources']:
                self.assertEqual(hashlib.sha256(files.read(row['path'])).hexdigest(), row['sha256'])
            for tag in ('v258','v259.9'):
                def text(name): return files.read(tag+'__'+name.replace('/','_')).decode()
                self.assertIn('strv_extend(&arg_property, optarg)',text('src/login/loginctl.c'))
                self.assertIn('extract_first_word(&p, &prop, ",", 0)',text('src/systemctl/systemctl.c'))
                self.assertIn('strv_contains(filter, name)',text('src/shared/bus-print-properties.c'))
                self.assertIn('get-property SERVICE OBJECT INTERFACE PROPERTY...',text('src/busctl/busctl.c'))
                # The unit selector's three normal origins have no kernel
                # transport arm. Do not widen the artifact class on a guess.
                unit = text('src/shared/logs-show.c').split('int add_matches_for_unit_full(',1)[1].split('int add_matches_for_user_unit_full(',1)[0]
                for field in ('_SYSTEMD_UNIT','UNIT','OBJECT_SYSTEMD_UNIT'):
                    self.assertIn('"'+field+'"',unit)
                self.assertNotIn('"_TRANSPORT", "kernel"',unit)

    def test_journal_json_is_not_silently_an_allowed_boot_console(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('artifact_class',ROOT/'reviews/14-owner-tools/classify-artifacts.py')
        classifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(classifier)
        for transport in ('kernel','journal','stdout'):
            row=dict(_TRANSPORT=transport,MESSAGE="Loaded X.509 cert 'test key: "+'a'*40+"'")
            with self.assertRaisesRegex(AssertionError,'STOP:'):
                classifier.kernel_line(json.dumps(row))


if __name__ == '__main__': unittest.main()
