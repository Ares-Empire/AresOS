"""Publisher tests are hermetic: local repository and stubbed GitHub notifications."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'control/chrome'))
spec=importlib.util.spec_from_file_location('chrome_qualify',ROOT/'control/chrome/qualify.py')
qualify=importlib.util.module_from_spec(spec);spec.loader.exec_module(qualify)
from test_policy import entry
from aresos_control.common import Refused


class Publisher(unittest.TestCase):
    def test_lookup_both_channels_and_newest_three_builds_twice(self):
        metadata='\n\n'.join('Package: google-chrome-'+channel+'\nVersion: '+version+'-1\nFilename: pool/main/g/google-chrome-'+channel+'/google-chrome-'+channel+'_'+version+'-1_amd64.deb\nSHA256: '+'1'*64 for channel,version in [('stable','157.0.1.0'),('beta','158.0.2.0')])
        versions=qualify.packages(metadata)
        self.assertTrue(versions['stable']['package_url'].endswith('157.0.1.0-1_amd64.deb'))
        self.assertEqual(versions['stable']['package_sha256'],'1'*64)
        with self.assertRaises(ValueError):qualify.packages(metadata.replace('SHA256:', 'Missing:'))
        registry={'format':1,'builds':[{'commit':str(i)*40,'build':str(i)*64,'shipped_at':str(i)} for i in range(1,5)]}
        matrix=qualify.plan(registry,versions,{'format':1,'entries':[]},'a'*40,'a'*64)['include']
        self.assertEqual(len(matrix),16)
        self.assertEqual({item['build'] for item in matrix},{'a'*64,'4'*64,'3'*64,'2'*64})
        self.assertEqual({item['repeat'] for item in matrix},{1,2})

    def test_publisher_verifies_existing_before_append_and_never_signs_inserted_entry(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as temporary:
            root=Path(temporary);qualify.git(root,'init')
            path=root/qualify.RECORD;path.parent.mkdir(parents=True)
            held={'format':1,'entries':[entry()]};path.write_text(json.dumps(held))
            verifier=Mock()
            candidate=qualify.prepare(root,[entry(version='158.0.1.0')],held,verifier)
            verifier.assert_called_once_with(path);self.assertEqual(candidate['entries'][:1],held['entries'])
            # An inserted branch entry without its own valid attestation is never blessed by the next run.
            altered=copy.deepcopy(candidate);path.write_text(json.dumps(altered))
            verifier=Mock(side_effect=Refused('qualification_invalid','fixture unsigned entry'))
            with self.assertRaises(Refused):qualify.prepare(root,[entry(version='159.0.1.0')],held,verifier)
            self.assertEqual(json.loads(path.read_text()),altered)
            rollback={'format':1,'entries':[]};path.write_text(json.dumps(rollback))
            with self.assertRaises(Refused):qualify.prepare(root,[],held,Mock())

    def test_an_unmerged_baseline_update_does_not_block_a_new_pair(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as temporary:
            root=Path(temporary);path=root/qualify.RECORD;path.parent.mkdir(parents=True)
            published={'format':1,'entries':[entry(),entry(version='158.0.1.0',channel='beta')]}
            baseline={'format':1,'entries':[entry()]};path.write_text(json.dumps(published))
            repeated=entry(version='158.0.1.0',channel='beta');repeated['run']='next-run'
            result=qualify.prepare(root,[repeated,entry(version='158.0.2.0',channel='beta')],baseline,Mock())
            self.assertEqual(len(result['entries']),3);self.assertEqual(result['entries'][:2],published['entries'])
            repeated['core']['binding']=False
            with self.assertRaises(ValueError):qualify.prepare(root,[repeated],baseline,Mock())

    def test_real_remote_mutations_refuse_on_this_branch_and_notifications_are_stubs(self):
        result=subprocess.run([sys.executable,str(ROOT/'control/chrome/qualify.py'),'publish'],cwd=ROOT,capture_output=True,text=True,env={'GITHUB_REF':'refs/heads/pkg/20-chrome','GITHUB_REPOSITORY':qualify.REPOSITORY})
        self.assertNotEqual(result.returncode,0);self.assertIn('restricted',result.stderr)
        runner=Mock(return_value=Mock(stdout='[]'))
        qualify.notify(None,False,runner);self.assertEqual(runner.call_count,1)
        self.assertIn('issue',runner.call_args.args[0])
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as temporary:
            path=Path(temporary)/'record.json';failed=entry();failed['core']['binding']=False
            path.write_text(json.dumps({'format':1,'entries':[failed]}));runner.reset_mock()
            qualify.notify(path,True,runner)
            self.assertEqual(runner.call_count,3)
            self.assertTrue(any('binding' in argument for call in runner.call_args_list for argument in call.args[0]))

    def test_missing_repeat_or_missing_group_never_qualifies(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as temporary:
            root=Path(temporary);pair={**entry(),'repeat':1}
            (root/'pair.json').write_text(json.dumps(pair))
            result=qualify.aggregate(root,'fixture-run')[0]
            self.assertFalse(any(result['core'].values()));self.assertFalse(any(result['adapters'].values()))
