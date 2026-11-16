"""Publisher tests are hermetic: local repository and stubbed GitHub notifications."""
import copy
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
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
from workflow_steps import StepRunner

METADATA='\n\n'.join('Package: google-chrome-'+channel+'\nVersion: '+version+'-1\nFilename: pool/main/g/google-chrome-'+channel+'/google-chrome-'+channel+'_'+version+'-1_amd64.deb\nSHA256: '+'1'*64 for channel,version in [('stable','157.0.1.0'),('beta','158.0.2.0')])


def commit(repository,message):
    qualify.git(repository,'add','.');qualify.git(repository,'-c','user.name=Fixture','-c','user.email=fixture@fixture.test','commit','-q','-m',message)


def compact(record):
    # The bytes main's publish writes to the data branch.
    return json.dumps(record,separators=(',',':'))+'\n'


def origin_with(root,baseline,held=None):
    """A local stand-in for origin: main ships baseline; the data branch, when given, holds held as main wrote it."""
    origin=root/'origin';origin.mkdir();qualify.git(origin,'init','-q','-b','main')
    path=origin/qualify.RECORD;path.parent.mkdir(parents=True);path.write_text(json.dumps(baseline))
    (origin/'control/chrome/builds.json').write_text('{"format":1,"builds":[]}');commit(origin,'Fixture baseline')
    if held is not None:
        qualify.git(origin,'checkout','-q','-b',qualify.DATA_BRANCH);path.write_text(compact(held));commit(origin,'Fixture data branch');qualify.git(origin,'checkout','-q','main')
    return origin


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
        runner=Mock(return_value=Mock(stdout=''))
        qualify.notify(None,False,runner);self.assertEqual(runner.call_count,2)
        self.assertEqual(runner.call_args.args[0][:3],['gh','issue','create'])
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as temporary:
            path=Path(temporary)/'record.json';failed=entry();failed['core']['binding']=False
            path.write_text(json.dumps({'format':1,'entries':[failed]}));runner.reset_mock()
            with patch.dict(qualify.os.environ,GITHUB_RUN_ID='fixture'):qualify.notify(path,True,runner)
            # Failing groups and the shipped-copy update: one issue each, never a pull request.
            self.assertEqual([call.args[0][1:3] for call in runner.call_args_list][1::2],[['issue','create']]*2)
            self.assertEqual([call.args[0][1] for call in runner.call_args_list],['api','issue']*2)
            self.assertTrue(any('binding' in argument for call in runner.call_args_list for argument in call.args[0]))

    def test_notify_keeps_one_open_issue_per_title_and_shows_gh_errors(self):
        # The repository doesn't let workflows create pull requests (main run 43696892949), and
        # the daily runs must not pile up duplicates: one open issue per title, a comment only
        # for new text, and gh's own error text in the log when a write is refused. The
        # repository is public, so only the workflow's own issues and comments count.
        title='Chrome qualification publication refused'
        bot={'user':'github-actions[bot]','type':'Bot'}
        stranger={'user':'someone','type':'User'}
        def recording(listed=(),comments=()):
            calls=[]
            def run(command,**options):
                calls.append(command[1:])
                if command[1]=='api' and command[3].endswith('/comments'):
                    return Mock(stdout=''.join(json.dumps(row)+'\n' for row in comments))
                if command[1]=='api':
                    self.assertIn('creator=github-actions%5Bbot%5D',command[3])
                    return Mock(stdout=''.join(json.dumps(row)+'\n' for row in listed))
                return Mock(stdout='')
            return run,calls
        def issue(number,issue_title,body='older',author=bot,pull=False):
            return {'number':number,'title':issue_title,'body':body,'pull':pull,**author}
        with patch.dict(qualify.os.environ,GITHUB_RUN_ID='7'):
            run,calls=recording();qualify.notify(None,False,run)
            body=calls[-1][calls[-1].index('--body')+1]
            self.assertEqual(calls[-1][:2],['issue','create']);self.assertIn('/actions/runs/7',body)
            listed=[issue(9,title),issue(5,title),issue(3,'Other'),issue(2,title,author=stranger),issue(1,title,pull=True)]
            for first,comments,commented in [(body,[],False),('older',[{'body':body,**bot}],False),
                                             ('older',[{'body':'other',**bot}],True),('older',[{'body':body,**stranger}],True)]:
                with self.subTest(first=first,comments=comments):
                    listed[1]['body']=first
                    run,calls=recording(listed,comments);qualify.notify(None,False,run)
                    self.assertNotIn(['issue','create'],[call[:2] for call in calls])
                    self.assertTrue(calls[1][2].endswith('/issues/5/comments'))
                    self.assertEqual(['issue','comment','5'] in [call[:3] for call in calls],commented)
            # A same-title issue someone else opened, or a pull request, is never the workflow's issue.
            for others in [[issue(3,'Other')],[issue(2,title,body=body,author=stranger)],[issue(1,title,body=body,pull=True)]]:
                with self.subTest(others=others):
                    run,calls=recording(others);qualify.notify(None,False,run)
                    self.assertEqual(calls[-1][:2],['issue','create'])
        def refused(command,**options):
            raise subprocess.CalledProcessError(1,command,stderr='HTTP 403: Resource not accessible by integration\n')
        try:qualify.notify(None,False,refused)
        except BaseException as error:caught=error
        else:caught=None
        self.assertIsInstance(caught,SystemExit)
        self.assertTrue(str(caught).startswith('gh api '))
        self.assertIn('failed: HTTP 403: Resource not accessible by integration',str(caught))

    def test_failing_groups_issue_names_only_this_run_s_entries(self):
        # The record is append-only: an old build's all-false entry (issue #74) must not be
        # reported again by every later run. The shipped-copy issue still lists every entry.
        failing='Chrome qualification has failing groups';shipped='Update shipped Chrome qualification record'
        bot={'user':'github-actions[bot]','type':'Bot'}
        earlier=entry(build='b'*64,channel='beta',version='159.0.1.0',run='41');earlier['core']['binding']=False
        current=entry(version='157.0.2.0',run='42');current['adapters']['gmail']=False
        passing=entry(version='157.0.3.0',run='42')
        def recording(listed=()):
            calls=[]
            def run(command,**options):
                calls.append(command[1:])
                if command[1]=='api' and not command[3].endswith('/comments'):
                    return Mock(stdout=''.join(json.dumps(row)+'\n' for row in listed))
                return Mock(stdout='')
            return run,calls
        def bodies(calls,title):
            return [call[call.index('--body')+1] for call in calls if call[:2]==['issue','create'] and call[call.index('--title')+1]==title]
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as temporary:
            path=Path(temporary)/'record.json'
            path.write_text(json.dumps({'format':1,'entries':[earlier,current,passing]}))
            with patch.dict(qualify.os.environ,GITHUB_RUN_ID='42'):
                run,calls=recording();qualify.notify(path,True,run)
            [body]=bodies(calls,failing)
            self.assertIn(current['build']+' stable 157.0.2.0: gmail',body)
            self.assertNotIn(earlier['build'],body);self.assertNotIn('binding',body);self.assertNotIn('157.0.3.0',body)
            [listing]=bodies(calls,shipped)
            for held in [earlier,current,passing]:self.assertIn(held['build'][:12]+' '+held['channel']+' '+held['version'],listing)
            # No failing entry from this run: no new failing-groups issue and no comment on the
            # open one, even though the record still holds the earlier run's failure.
            path.write_text(json.dumps({'format':1,'entries':[earlier,passing]}))
            listed=[{'number':11,'title':failing,'body':'older','pull':False,**bot},{'number':12,'title':shipped,'body':'older','pull':False,**bot}]
            with patch.dict(qualify.os.environ,GITHUB_RUN_ID='42'):
                run,calls=recording(listed);qualify.notify(path,True,run)
            self.assertEqual(bodies(calls,failing),[])
            self.assertNotIn(['issue','comment','11'],[call[:3] for call in calls])
            self.assertFalse(any(call[0]=='api' and call[3].endswith('/issues/11/comments') for call in calls))
            self.assertIn(['issue','comment','12'],[call[:3] for call in calls])
            # Without a run ID notify can't tell this run's entries apart: it refuses before
            # any GitHub call rather than report the whole record.
            path.write_text(json.dumps({'format':1,'entries':[earlier,current]}))
            for missing in [None,'']:
                with self.subTest(run_id=missing), patch.dict(qualify.os.environ,GITHUB_RUN_ID='unset'):
                    if missing is None:del qualify.os.environ['GITHUB_RUN_ID']
                    else:qualify.os.environ['GITHUB_RUN_ID']=missing
                    run,calls=recording()
                    with self.assertRaises(SystemExit) as refusal:qualify.notify(path,True,run)
                    self.assertIn('GITHUB_RUN_ID',str(refusal.exception));self.assertEqual(calls,[])

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
            # Real `chrome --version` lines (main run 43696892949): stable ends in a space and
            # beta in its channel word. The version is the token after the name, never the
            # last word, which turned every passing beta pair into an all-false entry.
            for text,passes in [('Google Chrome 157.0.1.0 \n',True),('Google Chrome 157.0.1.0 beta\n',True),
                                ('Google Chrome beta\n',False),('Chromium 157.0.1.0\n',False),
                                ('Google Chrome 157.0.1\n',False),('Google Chrome 157.0.1.0 beta extra\n',False),('',False)]:
                (root/'chrome-version.txt').write_text(text)
                with self.subTest(version_text=text), patch.object(sys,'argv',['qualify.py','pair','--artifacts',str(root),'--runtime-root',str(ROOT)]), patch.dict(qualify.os.environ,QUALIFICATION_PAIR=json.dumps(identity),QUALIFICATION_OUTCOME='success'), patch.object(qualify,'runtime_identity',return_value='a'*64):
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
            # Main's publication fetches the held bundles itself (verify_held); the file is the token-free pull-request step's.
            with patch.object(sys,'argv',['qualify.py','publish','--bundle','bundle.json','--held-bundle','held.jsonl']), patch.dict(qualify.os.environ,{'GITHUB_REF':'refs/heads/main','GITHUB_REPOSITORY':qualify.REPOSITORY}), no_git, no_publish:
                with self.assertRaises(SystemExit) as refused:qualify.main()
                self.assertIn('--held-bundle is for --remote',str(refused.exception))
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
            # Review F2: for a digest it lists nothing for, the API answers 404
            # and gh exits 1 (check=True raises): the same refusal as an empty
            # list. Any other gh failure propagates unchanged.
            def gh(stderr):
                return Mock(side_effect=subprocess.CalledProcessError(1,['gh','api'],'{"message":"Not Found","status":"404"}',stderr))
            try:qualify.bundle_from_api(path,gh('gh: Not Found (HTTP 404)\n'))
            except Exception as error:caught=error
            else:caught=None
            self.assertIsInstance(caught,Refused,'a 404 must refuse like an empty list')
            self.assertEqual((caught.code,str(caught)),('qualification_invalid',qualify.NOT_LISTED))
            for stderr in ['gh: Server Error (HTTP 502)\n','error connecting to api.github.com\n','gh: Not Found (HTTP 4040)\n']:
                with self.subTest(stderr=stderr), self.assertRaises(subprocess.CalledProcessError):
                    qualify.bundle_from_api(path,gh(stderr))
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
            runner=Mock(return_value=Mock(stdout=''))
            try:qualify.prepare(seed,[],baseline,Mock(side_effect=Refused('qualification_invalid','Unsigned fixture')))
            except Refused:qualify.notify(None,False,runner)
            else:self.fail('Unsigned publication accepted')
            self.assertEqual(runner.call_count,2);self.assertEqual(runner.call_args.args[0][:3],['gh','issue','create'])
            self.assertEqual(qualify.git(remote,'rev-parse','chrome-qualification'),before)
            # A valid signature cannot waive the shipped append-only baseline.
            path.write_text(json.dumps({'format':1,'entries':[]}));runner.reset_mock()
            try:qualify.prepare(seed,[],baseline,Mock())
            except Refused:qualify.notify(None,False,runner)
            else:self.fail('Rollback publication accepted')
            self.assertEqual(runner.call_count,2)
            self.assertEqual(qualify.git(remote,'rev-parse','chrome-qualification'),before)
            self.assertEqual(qualify.git(remote,'rev-parse','main'),main)

    def test_off_main_the_plan_qualifies_the_head_build_again_while_main_skips_what_is_held(self):
        # Review F1 (brief 20 main fix): build.py hashes only the installed
        # runtime, so a pull request that changes only the test driver, ci/,
        # qualify.py or the workflows keeps main's build hash. Off main the head
        # build is qualified again even when the held record covers it; main
        # skips every held pair exactly as before; shipped builds stay skipped.
        versions={channel:{'version':version} for channel,version in [('stable','157.0.1.0'),('beta','158.0.1.0')]}
        shipped={'commit':'2'*40,'build':'2'*64,'shipped_at':'2026-11-09T00:00:00Z'}
        held={'format':1,'entries':[entry(),entry(build='2'*64)]}
        for requalify,expected in [(False,[('a'*64,'beta'),('2'*64,'beta')]),(True,[('a'*64,'stable'),('a'*64,'beta'),('2'*64,'beta')])]:
            with self.subTest(requalify_head=requalify):
                rows=qualify.plan({'format':1,'builds':[shipped]},versions,held,'a'*40,'a'*64,requalify_head=requalify)['include']
                self.assertEqual([(row['build'],row['channel']) for row in rows],[key for key in expected for _ in [1,2]])
                self.assertEqual([row['repeat'] for row in rows],[1,2]*len(expected))
        # The CLI decides by the run's ref, against a data branch that holds the head build on stable.
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as temporary:
            root=Path(temporary)
            origin=origin_with(root,{'format':1,'entries':[]},{'format':1,'entries':[entry()]})
            checkout=root/'clone';qualify.git(root,'clone','-q',str(origin),str(checkout))
            for ref,rows in [('refs/heads/main',[]),('refs/pull/9/merge',[('a'*64,'157.0.1.0','stable',1),('a'*64,'157.0.1.0','stable',2)]),('refs/heads/pkg/20-main-fix',[('a'*64,'157.0.1.0','stable',1),('a'*64,'157.0.1.0','stable',2)])]:
                with self.subTest(ref=ref), patch.object(sys,'argv',['qualify.py','plan','--root',str(checkout),'--channels','stable']), patch.dict(qualify.os.environ,{'GITHUB_REF':ref}), patch.object(qualify.urllib.request,'urlopen',return_value=io.BytesIO(gzip.compress(METADATA.encode()))), patch.object(qualify,'build_hash',return_value='a'*64), patch.object(qualify,'verify_held') as verified, patch('sys.stdout',new_callable=io.StringIO) as stdout:
                    qualify.main()
                    self.assertEqual(verified.call_count,1)
                    self.assertEqual([(row['build'],row['version'],row['channel'],row['repeat']) for row in json.loads(stdout.getvalue())['include']],rows)

    def repeat(self,held,pair,ref):
        """Run the real prepare CLI on ref against a local origin whose data branch holds held.

        This run qualified the held stable pair again with the verdict pair
        and a new beta pair with every group passing. Returns the candidate's
        text (None when none was written), the printed lines and the error
        prepare raised, if any.
        """
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/20-chrome') as temporary:
            root=Path(temporary)
            origin=origin_with(root,{'format':1,'entries':[]},held)
            checkout=root/'clone';qualify.git(root,'clone','-q',str(origin),str(checkout));(checkout/'.work').mkdir()
            new=entry(version='158.0.1.0',channel='beta')
            plan=root/'plan.json';plan.write_text(json.dumps({'include':[{**item,'repeat':repeat} for item in [entry(),new] for repeat in [1,2]]}))
            artifacts=root/'artifacts'
            for name,item in [('stable',pair),('beta',new)]:
                for repeat in [1,2]:
                    (artifacts/name/str(repeat)).mkdir(parents=True);(artifacts/name/str(repeat)/'pair.json').write_text(json.dumps({**item,'repeat':repeat}))
            bundles=root/'held.bundles.jsonl';bundles.write_text('{}\n')
            candidate=root/'candidate.json';error=None
            with patch.object(sys,'argv',['qualify.py','prepare','--root',str(checkout),'--artifacts',str(artifacts),'--plan',str(plan),'--candidate',str(candidate)]), patch.dict(qualify.os.environ,{'GITHUB_REF':ref,'GITHUB_REPOSITORY':qualify.REPOSITORY,'GITHUB_RUN_ID':'9001'}), patch.object(qualify,'bundle_from_api',return_value=bundles) as fetched, patch.object(qualify,'verify') as verified, patch('sys.stdout',new_callable=io.StringIO) as stdout:
                try:qualify.main()
                except ValueError as raised:error=raised
            # The held record was verified from its bundle list, main policy, before anything else.
            self.assertEqual(fetched.call_count,1);self.assertEqual(verified.call_args.kwargs,{'bundle':bundles})
            return (candidate.read_text() if candidate.exists() else None),stdout.getvalue().splitlines(),error

    def test_off_main_an_identical_repeat_is_skipped_and_never_carries_main_s_bytes(self):
        # Review F1: the pull request's re-qualification of a held pair adds
        # nothing when it agrees. Off main the candidate is indented, never
        # main's bytes, so the pull request's attestation never joins the real
        # record's listing; main writes compact as before.
        held={'format':1,'entries':[entry()]}
        expected={'format':1,'entries':[entry(),entry(version='158.0.1.0',channel='beta',run='9001')]}
        for ref,serialized in [('refs/pull/9/merge',qualify.serialized(expected,False)),('refs/heads/main',compact(expected))]:
            with self.subTest(ref=ref):
                candidate,lines,error=self.repeat(held,entry(run='9001'),ref)
                self.assertIsNone(error);self.assertEqual(candidate,serialized);self.assertEqual(json.loads(candidate),expected)
                self.assertFalse([line for line in lines if line.startswith('::warning::')])
        self.assertNotEqual(qualify.serialized(expected,False),compact(expected))

    def test_off_main_a_worse_repeat_fails_the_pull_request_and_writes_no_candidate(self):
        # Review F3: a group the held record passes and this run fails is a
        # regression. The pull request fails and nothing is attested, adapter
        # groups as much as core ones.
        for kind,name in [('core','binding'),('adapters','github')]:
            worse=entry(run='9001');worse[kind][name]=False
            with self.subTest(group=kind+'.'+name):
                candidate,lines,error=self.repeat({'format':1,'entries':[entry()]},worse,'refs/pull/9/merge')
                self.assertIsInstance(error,ValueError);self.assertIn('Conflicting repeat',str(error));self.assertIn(kind+'.'+name,str(error))
                self.assertIsNone(candidate);self.assertFalse([line for line in lines if line.startswith('::warning::')])

    def test_off_main_a_better_repeat_warns_keeps_the_held_entry_and_the_rest_proceeds(self):
        # Review F3: main records a whole pair all-false when one shard fails,
        # and that entry never changes. A later pull request on the same build
        # that passes those groups (a test or CI fix, the record-update pull
        # request) warns, keeps the held entry and goes on with its new pairs.
        failed=entry(run='main-run');failed['core']=dict.fromkeys(failed['core'],False);failed['adapters']=dict.fromkeys(failed['adapters'],False)
        partly=entry(run='main-run');partly['core']['binding']=False;partly['adapters']['github']=False
        for name,held_entry in [('all-false',failed),('two groups failed',partly)]:
            held={'format':1,'entries':[held_entry]}
            expected={'format':1,'entries':[held_entry,entry(version='158.0.1.0',channel='beta',run='9001')]}
            with self.subTest(held=name):
                candidate,lines,error=self.repeat(held,entry(run='9001'),'refs/pull/9/merge')
                self.assertIsNone(error)
                self.assertEqual(json.loads(candidate),expected);self.assertEqual(candidate,qualify.serialized(expected,False))
                warnings=[line for line in lines if line.startswith('::warning::')]
                self.assertEqual(len(warnings),1)
                better=[kind+'.'+group for kind in ['core','adapters'] for group,passed in held_entry[kind].items() if not passed]
                self.assertIn('passes '+', '.join(better)+' for build '+'a'*12,warnings[0]);self.assertIn('held entry stays',warnings[0])
                # Only the groups this run improved are named.
                for passed in [kind+'.'+group for kind in ['core','adapters'] for group,value in held_entry[kind].items() if value]:
                    self.assertNotIn(passed,warnings[0])

    def test_off_main_a_mixed_repeat_fails_the_pull_request(self):
        # Review F3: better in some groups, worse in one is still a regression.
        held_entry=entry(run='main-run');held_entry['core']['binding']=False;held_entry['core']['page_script']=False
        mixed=entry(run='9001');mixed['adapters']['github']=False
        candidate,lines,error=self.repeat({'format':1,'entries':[held_entry]},mixed,'refs/pull/9/merge')
        self.assertIsInstance(error,ValueError);self.assertIn('adapters.github',str(error));self.assertNotIn('core.binding',str(error))
        self.assertIsNone(candidate);self.assertFalse([line for line in lines if line.startswith('::warning::')])

    def test_on_main_any_conflicting_repeat_raises(self):
        # Main never publishes a pair twice with two verdicts, whichever way they differ.
        failed=entry(run='main-run');failed['core']['binding']=False
        worse=entry(run='9001');worse['adapters']['github']=False
        for name,held_entry,pair in [('better',failed,entry(run='9001')),('worse',entry(run='main-run'),worse)]:
            with self.subTest(name):
                candidate,lines,error=self.repeat({'format':1,'entries':[held_entry]},pair,'refs/heads/main')
                self.assertIsInstance(error,ValueError)
                self.assertEqual(str(error),'Conflicting repeat for an immutable qualification pair; publish nothing')
                self.assertIsNone(candidate);self.assertFalse([line for line in lines if line.startswith('::warning::')])


class PullRequestPublish(unittest.TestCase):
    """Review F1 and security NOTE 4: the pull-request publish steps of the workflow, run as written, offline.

    The read-only step fetches the held record's bundle list with the token;
    the publish step holds none, seeds its local bare remote with origin's main
    and, when it exists, origin's data branch, and verifies the held record from
    that list under main's policy before appending.
    """
    WORKFLOW=ROOT/'.github/workflows/control-chrome-qualification.yml'
    READ="Fetch the held record's attestations for the pull-request publish (read only)"
    PUBLISH='Verify the new attestation then publish to a local bare remote (pull-request mode)'
    BASELINE={'format':1,'entries':[entry()]}
    HELD={'format':1,'entries':[entry(),entry(version='158.0.1.0',run='main-run')]}

    def setUp(self):
        self.directory=Path(tempfile.mkdtemp(dir=ROOT/'.work/20-chrome'));self.addCleanup(shutil.rmtree,self.directory)
        self.runner=StepRunner(self.directory/'tools',self.WORKFLOW)
        self.environment={'GITHUB_REPOSITORY':qualify.REPOSITORY,'GITHUB_REF':'refs/pull/9/merge'}

    def checkout(self,held,candidate):
        # The publish job's checkout (fetch-depth 0): origin's branches as
        # remote-tracking refs, this tree, and the files earlier steps left.
        origin=origin_with(self.directory,self.BASELINE,held)
        checkout=self.directory/'checkout';checkout.mkdir();qualify.git(checkout,'init','-q','-b','pull-request')
        qualify.git(checkout,'fetch','-q',str(origin),'+refs/heads/*:refs/remotes/origin/*')
        (checkout/'control').symlink_to(ROOT/'control',target_is_directory=True);(checkout/'.work').mkdir()
        (checkout/'.work/qualification-candidate.json').write_text(qualify.serialized(candidate,False))
        bundle=checkout/'.work/attest-bundle.json';bundle.write_text('{"fixture":"attest step bundle"}')
        return checkout,bundle

    def read(self,checkout,api=()):
        return self.runner.run(self.READ,checkout,environment=self.environment,api=api)

    def publish(self,checkout,bundle):
        return self.runner.run(self.PUBLISH,checkout,expressions={'${{ steps.attest.outputs.bundle-path }}':str(bundle)},environment=self.environment)

    def verifications(self):
        return [call for call in self.runner.gh_calls() if call['argv'][:2]==['attestation','verify']]

    def assert_policy(self,call,subject,ref,bundle):
        argv=call['argv']
        self.assertEqual(call['subject_sha256'],hashlib.sha256(subject).hexdigest())
        self.assertEqual(argv[argv.index('--source-ref')+1],ref);self.assertTrue(argv[argv.index('--bundle')+1].endswith(bundle),argv)
        self.assertEqual(argv[argv.index('--signer-workflow')+1],qualify.REPOSITORY+'/'+qualify.WORKFLOW);self.assertIn('--deny-self-hosted-runners',argv)

    def test_without_a_data_branch_the_publish_cuts_it_from_main_and_verifies_only_the_fresh_bundle(self):
        candidate={'format':1,'entries':[*self.BASELINE['entries'],entry(version='158.0.1.0',run='9001')]}
        checkout,bundle=self.checkout(None,candidate)
        result=self.read(checkout)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('first-record path',result.stdout)
        self.assertEqual(self.runner.gh_calls(),[]);self.assertFalse((checkout/'.work/held-bundles.jsonl').exists())
        result=self.publish(checkout,bundle)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertIn('reached only the local bare remote',result.stdout)
        calls=self.runner.gh_calls();verified=self.verifications()
        self.assertEqual(len(verified),1);self.assert_policy(verified[0],(checkout/'.work/qualification-candidate.json').read_bytes(),'refs/pull/9/merge',str(bundle))
        self.assertFalse(any(call['argv'][:1]==['api'] or call['token'] for call in calls))
        remote=checkout/'.work/publish-remote.git'
        self.assertEqual(qualify.git(remote,'rev-parse','chrome-qualification^'),qualify.git(checkout,'rev-parse','refs/remotes/origin/main'))
        self.assertEqual(json.loads(qualify.git(remote,'show','chrome-qualification:'+qualify.RECORD)),candidate)

    def test_with_a_data_branch_the_held_record_is_verified_from_the_read_steps_list_under_main_policy_then_appended(self):
        # A new pair, and an identical repeat (F1): both take publish()'s
        # second-run path: held record verified, candidate appended to it.
        listing={'attestations':[{'bundle':{'fixture':'held'}},{'bundle':{'fixture':'other'}}]}
        for name,candidate in [('new pair',{'format':1,'entries':[*self.HELD['entries'],entry(version='159.0.1.0',run='9001')]}),('identical repeat',self.HELD)]:
            with self.subTest(name):
                shutil.rmtree(self.directory/'origin',ignore_errors=True);shutil.rmtree(self.directory/'checkout',ignore_errors=True)
                checkout,bundle=self.checkout(self.HELD,candidate)
                result=self.read(checkout,api=[{'stdout':json.dumps(listing)}])
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                held=compact(self.HELD).encode()
                self.assertEqual([call['argv'] for call in self.runner.gh_calls()],[['api','repos/'+qualify.REPOSITORY+'/attestations/sha256:'+hashlib.sha256(held).hexdigest()+'?per_page=100']])
                self.assertTrue(self.runner.gh_calls()[0]['token'])
                self.assertEqual((checkout/'.work/held-bundles.jsonl').read_text(),'{"fixture":"held"}\n{"fixture":"other"}\n')
                result=self.publish(checkout,bundle)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                calls=self.runner.gh_calls();verified=self.verifications()
                self.assertEqual(len(verified),2)
                self.assert_policy(verified[0],(checkout/'.work/qualification-candidate.json').read_bytes(),'refs/pull/9/merge',str(bundle))
                self.assert_policy(verified[1],held,'refs/heads/main','.work/held-bundles.jsonl')
                self.assertFalse(any(call['argv'][:1]==['api'] or call['token'] for call in calls))
                remote=checkout/'.work/publish-remote.git'
                self.assertEqual(qualify.git(remote,'rev-parse','chrome-qualification^'),qualify.git(checkout,'rev-parse','refs/remotes/origin/chrome-qualification'))
                self.assertEqual(json.loads(qualify.git(remote,'show','chrome-qualification:'+qualify.RECORD)),candidate)
                self.assertEqual(qualify.git(remote,'rev-parse','main'),qualify.git(checkout,'rev-parse','refs/remotes/origin/main'))

    def test_a_held_record_without_a_listing_or_a_bundle_list_refuses_and_nothing_moves(self):
        candidate={'format':1,'entries':[*self.HELD['entries'],entry(version='159.0.1.0',run='9001')]}
        checkout,bundle=self.checkout(self.HELD,candidate)
        result=self.read(checkout,api=[{'stdout':'{"message":"Not Found","status":"404"}','stderr':'gh: Not Found (HTTP 404)\n','code':1}])
        self.assertNotEqual(result.returncode,0);self.assertIn(qualify.NOT_LISTED,result.stderr)
        self.assertFalse((checkout/'.work/held-bundles.jsonl').exists())
        result=self.publish(checkout,bundle)
        self.assertNotEqual(result.returncode,0);self.assertIn('no bundle list was fetched',result.stderr)
        self.assertFalse(any(call['argv'][:1]==['api'] for call in self.runner.gh_calls()))
        remote=checkout/'.work/publish-remote.git'
        self.assertEqual(qualify.git(remote,'rev-parse','chrome-qualification'),qualify.git(checkout,'rev-parse','refs/remotes/origin/chrome-qualification'))
