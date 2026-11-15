"""Publisher tests are hermetic: local repository and stubbed GitHub notifications."""
import copy
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

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
            result_fixture = {**entry(), 'groups':{'12':True}}
            (root/'qualification-result.json').write_text(json.dumps(result_fixture))
            (root/'chrome-version.txt').write_text('Google Chrome 157.0.1.0\n')
            identity={**entry(),'repeat':1}
            (root/'matrices.json').write_text('[]')
            def completion(outcome):
                (root/'qualification-complete.json').write_text(json.dumps({'format':1, 'identity':identity, 'outcome':outcome,
                    'digests':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['qualification-result.json','matrices.json']}}))
            completion('success')
            from unittest.mock import patch
            for actual_build,actual_version,passes in [('a'*64,'157.0.1.0',True),('b'*64,'157.0.1.0',False),('a'*64,'157.0.1.1',False)]:
                (root/'chrome-version.txt').write_text('Google Chrome '+actual_version+'\n')
                with self.subTest(build=actual_build,version=actual_version), patch.object(sys,'argv',['qualify.py','pair','--artifacts',str(root),'--runtime-root',str(ROOT)]), patch.dict(qualify.os.environ,QUALIFICATION_PAIR=json.dumps(identity),QUALIFICATION_OUTCOME='success'), patch.object(qualify,'runtime_identity',return_value=actual_build):
                    qualify.main()
                result=json.loads((root/'pair.json').read_text())
                self.assertEqual(all(result['core'].values()),passes);self.assertEqual(all(result['adapters'].values()),passes)
            for outcome in ['failure', 'cancelled', 'skipped', '']:
                with self.subTest(outcome=outcome), patch.object(sys,'argv',['qualify.py','pair','--artifacts',str(root),'--runtime-root',str(ROOT)]), patch.dict(qualify.os.environ,QUALIFICATION_PAIR=json.dumps(identity),QUALIFICATION_OUTCOME=outcome), patch.object(qualify,'runtime_identity',return_value='a'*64):
                    (root/'chrome-version.txt').write_text('Google Chrome 157.0.1.0\n')
                    qualify.main()
                result=json.loads((root/'pair.json').read_text())
                self.assertFalse(any(result['core'].values()));self.assertFalse(any(result['adapters'].values()))
            # A full suite's final aggregate assertion is evidence for each
            # completed group, unlike an interruption or a stale all-pass file.
            result_fixture['adapters']['gmail']=False
            (root/'qualification-result.json').write_text(json.dumps(result_fixture));completion('failure')
            with patch.object(sys,'argv',['qualify.py','pair','--artifacts',str(root),'--runtime-root',str(ROOT)]), patch.dict(qualify.os.environ,QUALIFICATION_PAIR=json.dumps(identity),QUALIFICATION_OUTCOME='failure'), patch.object(qualify,'runtime_identity',return_value='a'*64):
                qualify.main()
            completed=json.loads((root/'pair.json').read_text())
            self.assertTrue(all(completed['core'].values()));self.assertFalse(completed['adapters']['gmail']);self.assertTrue(completed['adapters']['gemini'])
            # Replacing either file after completion invalidates that evidence.
            (root/'matrices.json').write_text('["changed"]')
            self.assertFalse(qualify.completed(root,identity,'failure'))
            completion('failure')
            result_fixture.pop('groups');(root/'qualification-result.json').write_text(json.dumps(result_fixture))
            completion('success')
            with patch.object(sys,'argv',['qualify.py','pair','--artifacts',str(root),'--runtime-root',str(ROOT)]), patch.dict(qualify.os.environ,QUALIFICATION_PAIR=json.dumps(identity),QUALIFICATION_OUTCOME='success'), patch.object(qualify,'runtime_identity',return_value='a'*64):
                qualify.main()
            self.assertFalse(any(json.loads((root/'pair.json').read_text())['core'].values()))

    def test_archived_build_uses_its_own_identity_algorithm(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as temporary:
            root=Path(temporary);script=root/'control/chrome/build.py';script.parent.mkdir(parents=True)
            script.write_text("print('"+'d'*64+"')\n")
            from unittest.mock import patch
            with patch.object(qualify,'build_hash',side_effect=AssertionError('Must not substitute current driver identity')):
                self.assertEqual(qualify.runtime_identity(root),'d'*64)
            script.write_text("print('not a build hash')\n")
            with self.assertRaises(ValueError):qualify.runtime_identity(root)

    def test_writes_to_github_refuse_off_main_while_prepare_and_local_publish_run_anywhere(self):
        # Main fix H4: a pull request or branch run prepares, attests and
        # publishes to a local bare repository; the push to origin and the
        # notifications stay main-only in this guard, not only in the workflow.
        no_git=patch.object(qualify,'git',side_effect=AssertionError('No remote reads before branch guard'))
        no_notify=patch.object(qualify,'notify',side_effect=AssertionError('No GitHub writes'))
        no_publish=patch.object(qualify,'publish',side_effect=AssertionError('No publication'))
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as temporary:
            local=Path(temporary);(local/'plan.json').write_text('{"include":[]}')
            for ref in ['refs/heads/pkg/20-chrome-qual','refs/heads/pkg/20-chrome','refs/pull/1/merge','']:
                environment={'GITHUB_REF':ref,'GITHUB_REPOSITORY':qualify.REPOSITORY,'GITHUB_RUN_ID':'1'}
                for arguments in [['publish','--bundle','bundle.json'],['notify']]:
                    with self.subTest(ref=ref,command=arguments[0]), patch.object(sys,'argv',['qualify.py',*arguments]), patch.dict(qualify.os.environ,environment), no_git, no_notify, no_publish:
                        with self.assertRaises(SystemExit) as refused:qualify.main()
                        self.assertIn('restricted to main',str(refused.exception))
                # prepare reads origin/main and proceeds (the patched git is reached).
                with self.subTest(ref=ref,command='prepare'), patch.object(sys,'argv',['qualify.py','prepare','--artifacts',str(local),'--plan',str(local/'plan.json')]), patch.dict(qualify.os.environ,environment), patch.object(qualify,'aggregate',return_value=[]), no_git, no_notify:
                    with self.assertRaises(AssertionError) as reached:qualify.main()
                    self.assertIn('No remote reads before branch guard',str(reached.exception))
                # publish --remote <existing local directory> proceeds with the attest bundle.
                baseline={'format':1,'entries':[entry()]}
                with self.subTest(ref=ref,command='publish --remote'), patch.object(sys,'argv',['qualify.py','publish','--bundle','bundle.json','--remote',str(local),'--ref',ref or 'refs/pull/1/merge']), patch.dict(qualify.os.environ,environment), patch.object(qualify,'git',return_value=json.dumps(baseline)), patch.object(qualify,'publish') as published, no_notify:
                    qualify.main()
                    self.assertEqual(published.call_args.kwargs,{'remote':str(local.resolve()),'bundle':Path('bundle.json'),'ref':ref or 'refs/pull/1/merge'})
                    self.assertEqual(published.call_args.args[1:],(Path('.work/qualification-candidate.json'),baseline))
                # Never a URL, never a missing directory, never without the bundle.
                for remote in ['https://github.com/'+qualify.REPOSITORY+'.git','file://'+str(local),str(local/'missing'),'git@github.com:'+qualify.REPOSITORY+'.git']:
                    with self.subTest(ref=ref,remote=remote), patch.object(sys,'argv',['qualify.py','publish','--bundle','bundle.json','--remote',remote]), patch.dict(qualify.os.environ,environment), no_git, no_publish:
                        with self.assertRaises(SystemExit):qualify.main()
                with self.subTest(ref=ref,command='publish without bundle'), patch.object(sys,'argv',['qualify.py','publish','--remote',str(local)]), patch.dict(qualify.os.environ,environment), no_git, no_publish:
                    with self.assertRaises(ValueError):qualify.main()
            with patch.object(sys,'argv',['qualify.py','publish','--bundle','bundle.json']), patch.dict(qualify.os.environ,{'GITHUB_REF':'refs/heads/main','GITHUB_REPOSITORY':qualify.REPOSITORY}), no_git, no_publish:
                with self.assertRaises(AssertionError):qualify.main()
            # A real publication to origin verifies the candidate under main's policy only: --ref is refused there.
            with patch.object(sys,'argv',['qualify.py','publish','--bundle','bundle.json','--ref','refs/heads/main']), patch.dict(qualify.os.environ,{'GITHUB_REF':'refs/heads/main','GITHUB_REPOSITORY':qualify.REPOSITORY}), no_git, no_publish:
                with self.assertRaises(SystemExit) as refused:qualify.main()
                self.assertIn('--ref is for --remote',str(refused.exception))
            for command in ['prepare','publish','notify']:
                with self.subTest(repository='foreign',command=command), patch.object(sys,'argv',['qualify.py',command,'--bundle','bundle.json']), patch.dict(qualify.os.environ,{'GITHUB_REF':'refs/heads/main','GITHUB_REPOSITORY':'fixture/repository'}), no_git, no_notify, no_publish:
                    with self.assertRaises(SystemExit):qualify.main()

    def test_held_record_bundle_comes_from_gh_api_with_the_job_login(self):
        # Main fix H2: the CLI verifies a held data-branch record from a
        # bundle list fetched by gh api (the job's token), not the anonymous
        # quota; the response is transport, gh attestation verify is the check.
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as temporary:
            path=Path(temporary)/'record.json';path.write_text(json.dumps({'format':1,'entries':[entry()]}))
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            runner=Mock(return_value=Mock(stdout=json.dumps({'attestations':[{'bundle':{'fixture':1}},{'bundle':{'fixture':'\u00e9'}}]})))
            bundle=qualify.bundle_from_api(path,runner)
            command=runner.call_args.args[0]
            self.assertEqual(command,['gh','api','repos/'+qualify.REPOSITORY+'/attestations/sha256:'+digest+'?per_page=100'])
            self.assertEqual(bundle.read_bytes(),'{"fixture":1}\n{"fixture":"\u00e9"}\n'.encode())
            self.assertEqual(bundle.parent,path.parent);self.assertEqual(bundle.suffix,'.jsonl')
            for stdout in ['{"attestations":[]}','{}','{"attestations":[{"bundle":{"x":"'+'y'*(4*1024*1024)+'"}}]}']:
                with self.subTest(stdout=stdout[:20]), self.assertRaises(Refused):
                    qualify.bundle_from_api(path,Mock(return_value=Mock(stdout=stdout)))
            with patch.object(qualify,'bundle_from_api',return_value=bundle), patch.object(qualify,'verify') as verify:
                qualify.verify_held(path)
            verify.assert_called_once_with(path,bundle=bundle)
            self.assertFalse(bundle.exists())
            self.assertIs(qualify.prepare.__defaults__[0],qualify.verify_held)
            self.assertIs(qualify.publish.__kwdefaults__['held_verifier'],qualify.verify_held)

    def test_plan_takes_one_channel_off_main_and_both_on_main(self):
        metadata='\n\n'.join('Package: google-chrome-'+channel+'\nVersion: '+version+'-1\nFilename: pool/main/g/google-chrome-'+channel+'/google-chrome-'+channel+'_'+version+'-1_amd64.deb\nSHA256: '+'1'*64 for channel,version in [('stable','157.0.1.0'),('beta','158.0.2.0')])
        def git(repo,*arguments,check=True):
            return 'a'*40 if arguments[0]=='rev-parse' else ''
        for channels,expected in [('stable',{'stable'}),('stable,beta',{'stable','beta'}),('beta',{'beta'})]:
            with self.subTest(channels=channels), patch.object(sys,'argv',['qualify.py','plan','--root',str(ROOT),'--channels',channels]), patch.object(qualify.urllib.request,'urlopen',return_value=io.BytesIO(gzip.compress(metadata.encode()))), patch.object(qualify,'git',side_effect=git), patch.object(qualify,'build_hash',return_value='a'*64), patch('sys.stdout',new_callable=io.StringIO) as stdout:
                qualify.main()
            rows=json.loads(stdout.getvalue())['include']
            self.assertEqual({row['channel'] for row in rows},expected);self.assertEqual(len(rows),2*len(expected))
        for channels in ['dev','stable,stable','','stable,beta,dev']:
            with self.subTest(channels=channels), patch.object(sys,'argv',['qualify.py','plan','--root',str(ROOT),'--channels',channels]), patch.object(qualify.urllib.request,'urlopen',side_effect=AssertionError('No fetch for an invalid channel list')):
                with self.assertRaises(ValueError):qualify.main()

    def test_first_publication_cuts_the_data_branch_from_main_and_extends_only_the_shipped_baseline(self):
        # Main fix H3: the first run on main has no data branch. prepare takes
        # the shipped baseline from origin/main plus this run's results, and
        # publish verifies the candidate against the attest step's bundle,
        # cuts the data branch from main and never calls the held verifier.
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as temporary:
            root=Path(temporary)
            def seeded(name,record):
                remote=root/(name+'.git');remote.mkdir();qualify.git(remote,'init','--bare')
                seed=root/name;seed.mkdir();qualify.git(seed,'init','-b','main');(seed/'.work').mkdir()
                path=seed/qualify.RECORD;path.parent.mkdir(parents=True);path.write_text(json.dumps(record))
                qualify.git(seed,'add','.');qualify.git(seed,'-c','user.name=Fixture','-c','user.email=fixture@fixture.test','commit','-m','Fixture baseline')
                qualify.git(seed,'remote','add','origin',str(remote));qualify.git(remote,'fetch',str(seed),'main:main');qualify.git(seed,'fetch','-q','origin')
                return seed,remote
            baseline={'format':1,'entries':[entry()]}
            seed,remote=seeded('first',baseline)
            artifacts=root/'artifacts';plan={'include':[]}
            for repeat in [1,2]:
                (artifacts/str(repeat)).mkdir(parents=True)
                (artifacts/str(repeat)/'pair.json').write_text(json.dumps({**entry(version='158.0.1.0'),'repeat':repeat}))
                plan['include'].append({'build':'a'*64,'version':'158.0.1.0','channel':'stable','repeat':repeat})
            (root/'plan.json').write_text(json.dumps(plan))
            candidate=root/'candidate.json'
            with patch.object(sys,'argv',['qualify.py','prepare','--root',str(seed),'--artifacts',str(artifacts),'--plan',str(root/'plan.json'),'--candidate',str(candidate)]), patch.dict(qualify.os.environ,{'GITHUB_REF':'refs/pull/9/merge','GITHUB_REPOSITORY':qualify.REPOSITORY,'GITHUB_RUN_ID':'77'}), patch.object(qualify,'verify_held',side_effect=AssertionError('Nothing held to verify on the first run')):
                qualify.main()
            expected={'format':1,'entries':[entry(),{**entry(version='158.0.1.0'),'run':'77'}]}
            self.assertEqual(json.loads(candidate.read_text()),expected)
            bundle=root/'bundle.json';bundle.write_text('{"fixture":"attest step bundle"}')
            verifier=Mock();held=Mock(side_effect=AssertionError('No data branch exists to verify'))
            main=qualify.git(remote,'rev-parse','refs/heads/main')
            qualify.publish(seed,candidate,baseline,remote=str(remote),verifier=verifier,bundle=bundle,held_verifier=held,ref='refs/pull/9/merge')
            verifier.assert_called_once_with(candidate,bundle=bundle,ref='refs/pull/9/merge')
            # Without a ref (main's publication) the fresh bundle is verified under the default main policy;
            # the data branch now exists, so the held record is verified too.
            with patch.object(qualify,'verify') as verify:
                qualify.publish(seed,candidate,baseline,remote=str(remote),verifier=verify,bundle=bundle,held_verifier=verify)
            self.assertEqual(verify.call_args_list[0].kwargs,{'bundle':bundle});self.assertEqual(verify.call_count,2)
            self.assertEqual(qualify.git(remote,'rev-parse','refs/heads/main'),main)
            self.assertEqual(json.loads(qualify.git(remote,'show','chrome-qualification:'+qualify.RECORD)),expected)
            self.assertEqual(qualify.git(remote,'rev-parse','chrome-qualification^'),main)
            # Refused: a candidate whose prefix is not the shipped baseline, and
            # a main whose shipped record is not the baseline the run trusts.
            foreign={'format':1,'entries':[entry(run='foreign-baseline')]}
            seed2,remote2=seeded('second',baseline)
            for name,trusted,target in [('candidate does not extend the baseline',foreign,remote2),('main does not hold the trusted baseline',foreign,seeded('third',foreign)[1])]:
                verifier=Mock()
                with self.subTest(name=name), self.assertRaises(Refused):
                    qualify.publish(seed2,candidate,trusted if name.startswith('candidate') else baseline,remote=str(target),verifier=verifier,bundle=bundle,held_verifier=held)
                self.assertEqual(qualify.git(target,'ls-remote','--heads',str(target),'refs/heads/chrome-qualification'),'')
                self.assertEqual(json.loads(qualify.git(target,'show','main:'+qualify.RECORD)),foreign if name.startswith('main') else baseline)

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
            qualify.publish(root,candidate,baseline,remote=str(remote),verifier=verifier,held_verifier=verifier)
            self.assertEqual(verifier.call_count,1)
            self.assertEqual(qualify.git(remote,'rev-parse','refs/heads/main'),main)
            self.assertEqual(json.loads(qualify.git(remote,'show','chrome-qualification:'+qualify.RECORD)),newer)
            verifier.reset_mock();qualify.publish(root,candidate,baseline,remote=str(remote),verifier=verifier,held_verifier=verifier)
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
