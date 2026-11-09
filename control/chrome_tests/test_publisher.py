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
        registry={'format':1,'builds':[{'commit':str(i)*40,'build':str(i)*64,'shipped_at':f'2026-11-0{i}T00:00:00Z'} for i in range(1,5)]}
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

    def test_plan_suppresses_only_exact_recorded_pairs_and_rejects_bad_registry(self):
        versions = {channel:{'version':version} for channel,version in [('stable','157.0.1.0'), ('beta','158.0.1.0')]}
        held = {'format':1, 'entries':[entry()]}
        planned = qualify.plan({'format':1,'builds':[]}, versions, held, 'a'*40, 'a'*64)['include']
        self.assertEqual([(row['channel'],row['repeat']) for row in planned], [('beta',1), ('beta',2)])
        shipped = {'commit':'a'*40, 'build':'a'*64, 'shipped_at':'2026-11-09T00:00:00Z'}
        bad = [{'format':1,'builds':[shipped,shipped]}, {'format':1,'builds':[{**shipped,'commit':'short'}]},
               {'format':1,'builds':[{**shipped,'shipped_at':'2026-11-09'}]}, {'format':1,'builds':[{}]}]
        for registry in bad:
            with self.subTest(registry=registry), self.assertRaises(ValueError):
                qualify.plan(registry,versions,held,'a'*40,'a'*64)

    def test_metadata_rejects_missing_duplicate_channels_and_unpinned_packages(self):
        paragraphs = ['Package: google-chrome-'+channel+'\nVersion: '+version+'-1\nFilename: pool/main/g/google-chrome-'+channel+'/google-chrome-'+channel+'_'+version+'-1_amd64.deb\nSHA256: '+'1'*64
                      for channel,version in [('stable','157.0.1.0'), ('beta','158.0.2.0')]]
        good = '\n\n'.join(paragraphs)
        for metadata in [paragraphs[0],good+'\n\n'+paragraphs[0],good.replace('Version: 157.0.1.0-1','Version: 157'),
                         good.replace('pool/main/', '../'),good.replace('SHA256: '+'1'*64,'SHA256: no')]:
            with self.subTest(metadata=metadata), self.assertRaises(ValueError): qualify.packages(metadata)

    def test_aggregation_accounts_for_wholly_missing_jobs_and_requires_two_strict_results(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as temporary:
            root=Path(temporary)
            expected={'include':[{**entry(version=version),'repeat':repeat} for version in ['157.0.1.0','158.0.1.0'] for repeat in [1,2]]}
            for repeat in [1,2]:
                directory=root/str(repeat);directory.mkdir()
                pair={**entry(),'repeat':repeat}
                if repeat==2:pair['core']['binding']=False;pair['adapters']['gmail']=False
                (directory/'pair.json').write_text(json.dumps(pair))
            actual=qualify.aggregate(root,'fixture-run',expected)
            self.assertEqual(len(actual),2)
            self.assertFalse(actual[0]['core']['binding']);self.assertFalse(actual[0]['adapters']['gmail'])
            self.assertTrue(actual[0]['core']['classification']);self.assertTrue(actual[0]['adapters']['gemini'])
            self.assertFalse(any(actual[1]['core'].values()));self.assertFalse(any(actual[1]['adapters'].values()))
            pair['version']='159.0.1.0';(root/'2/pair.json').write_text(json.dumps(pair))
            with self.assertRaises(ValueError):qualify.aggregate(root,'fixture-run',expected)

    def test_pair_result_requires_measured_build_and_exact_browser_version(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as temporary:
            root=Path(temporary)
            (root/'qualification-result.json').write_text(json.dumps(entry()))
            (root/'chrome-version.txt').write_text('Google Chrome 157.0.1.0\n')
            identity={**entry(),'repeat':1}
            from unittest.mock import patch
            for actual_build,actual_version,passes in [('a'*64,'157.0.1.0',True),('b'*64,'157.0.1.0',False),('a'*64,'157.0.1.1',False)]:
                (root/'chrome-version.txt').write_text('Google Chrome '+actual_version+'\n')
                with self.subTest(build=actual_build,version=actual_version), patch.object(sys,'argv',['qualify.py','pair','--artifacts',str(root),'--runtime-root',str(ROOT)]), patch.dict(qualify.os.environ,QUALIFICATION_PAIR=json.dumps(identity)), patch.object(qualify,'build_hash',return_value=actual_build):
                    qualify.main()
                result=json.loads((root/'pair.json').read_text())
                self.assertEqual(all(result['core'].values()),passes);self.assertEqual(all(result['adapters'].values()),passes)

    def test_all_non_main_mutation_commands_refuse_before_git_or_github(self):
        from unittest.mock import patch
        for ref in ['refs/heads/pkg/20-chrome-qual','refs/heads/pkg/20-chrome','refs/pull/1/merge','']:
            for command in ['prepare','publish','notify']:
                with self.subTest(ref=ref,command=command), patch.object(sys,'argv',['qualify.py',command]), patch.dict(qualify.os.environ,{'GITHUB_REF':ref,'GITHUB_REPOSITORY':qualify.REPOSITORY}), patch.object(qualify,'git',side_effect=AssertionError('No remote reads before branch guard')), patch.object(qualify,'notify',side_effect=AssertionError('No GitHub writes')):
                    with self.assertRaises(SystemExit):qualify.main()
        with patch.object(sys,'argv',['qualify.py','publish']), patch.dict(qualify.os.environ,{'GITHUB_REF':'refs/heads/main','GITHUB_REPOSITORY':'fixture/repository'}):
            with self.assertRaises(SystemExit):qualify.main()

    def test_local_repository_publish_only_changes_data_branch_and_verifies_both_subjects(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as temporary:
            root=Path(temporary);(root/'.work').mkdir()
            remote=root/'remote.git';remote.mkdir();qualify.git(remote,'init','--bare')
            seed=root/'seed';seed.mkdir();qualify.git(seed,'init','-b','main')
            path=seed/qualify.RECORD;path.parent.mkdir(parents=True)
            baseline={'format':1,'entries':[entry()]};path.write_text(json.dumps(baseline))
            qualify.git(seed,'add','.')
            qualify.git(seed,'-c','user.name=Fixture','-c','user.email=fixture@fixture.test','commit','-m','Fixture baseline')
            qualify.git(seed,'remote','add','origin',str(remote));qualify.git(remote,'fetch',str(seed),'main:main')
            main=qualify.git(remote,'rev-parse','refs/heads/main')
            candidate=root/'candidate.json';newer={'format':1,'entries':[entry(),entry(version='158.0.1.0')]};candidate.write_text(json.dumps(newer))
            verifier=Mock()
            qualify.publish(root,candidate,baseline,remote=str(remote),verifier=verifier)
            self.assertEqual(verifier.call_count,1)
            self.assertEqual(qualify.git(remote,'rev-parse','refs/heads/main'),main)
            self.assertEqual(json.loads(qualify.git(remote,'show','chrome-qualification:'+qualify.RECORD)),newer)
            verifier.reset_mock();qualify.publish(root,candidate,baseline,remote=str(remote),verifier=verifier)
            self.assertEqual(verifier.call_count,2)
            before=qualify.git(remote,'rev-parse','chrome-qualification')
            # Simulate an unsigned inserted branch entry, then the main workflow's
            # prepare failure -> refusal notification. Neither ref may move.
            qualify.git(seed,'fetch','origin','chrome-qualification');qualify.git(seed,'checkout','-b','chrome-qualification','FETCH_HEAD')
            inserted=copy.deepcopy(newer);inserted['entries'].append(entry(version='159.0.1.0'));path.write_text(json.dumps(inserted))
            qualify.git(seed,'add','.');qualify.git(seed,'-c','user.name=Fixture','-c','user.email=fixture@fixture.test','commit','-m','Unsigned fixture insertion');qualify.git(remote,'fetch',str(seed),'chrome-qualification:chrome-qualification')
            before=qualify.git(remote,'rev-parse','chrome-qualification')
            runner=Mock(return_value=Mock(stdout='[]'))
            try:qualify.prepare(seed,[],baseline,Mock(side_effect=Refused('qualification_invalid','Unsigned fixture')))
            except Refused:qualify.notify(None,False,runner)
            else:self.fail('Unsigned publication accepted')
            self.assertEqual(runner.call_count,1);self.assertIn('issue',runner.call_args.args[0])
            self.assertEqual(qualify.git(remote,'rev-parse','chrome-qualification'),before)
            # A valid signature cannot waive the shipped append-only baseline.
            path.write_text(json.dumps({'format':1,'entries':[]}));runner.reset_mock()
            try:qualify.prepare(seed,[],baseline,Mock())
            except Refused:qualify.notify(None,False,runner)
            else:self.fail('Rollback publication accepted')
            self.assertEqual(runner.call_count,1)
            self.assertEqual(qualify.git(remote,'rev-parse','chrome-qualification'),before)
            self.assertEqual(qualify.git(remote,'rev-parse','main'),main)
