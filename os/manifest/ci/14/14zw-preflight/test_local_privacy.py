import contextlib, importlib.util, json, pathlib, subprocess, tempfile, unittest
from unittest.mock import patch

ROOT=pathlib.Path.cwd();WORK=ROOT/'.work/14'
spec=importlib.util.spec_from_file_location('privacy',WORK/'14zw-privacy.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
H='a'*40;R='b'*40

class PrivacyTest(unittest.TestCase):
    def test_standard_stdin_covers_exact_source_and_destination(self):
        self.assertEqual(p.standard_input(H,R),f'refs/heads/pkg/14-owner-tools {H} refs/heads/pkg/14-owner-tools {R}\n')
        for bad in ('','x'*40,H+'\n','0'*39):
            with self.subTest(bad_length=len(bad)),self.assertRaises(AssertionError):p.standard_input(bad,R)

    def test_nonzero_or_skipped_terms_is_not_proof_even_on_green_exit(self):
        for code,stdout,stderr in ((1,'','BLOCKED'),(0,'','WARNING: personal terms check skipped.'),
                                   (0,'PERSONAL   TERMS CHECK SKIPPED','')):
            with self.subTest(code=code),self.assertRaises(AssertionError):
                p.checked_output(subprocess.CompletedProcess([],code,stdout,stderr))
        self.assertTrue(p.checked_output(subprocess.CompletedProcess([],0,'',''))['personal_terms_skipped_warning_absent'])

    def proof(self,log):
        import hashlib
        return dict(status='passed',head=H,remote_before=R,exit_code=0,
            personal_terms_skipped_warning_absent=True,no_verify=False,commits_checked=[H],
            standard_stdin=p.standard_input(H,R),identity={'checker':'fixture'},
            log=dict(sha256=hashlib.sha256(log.read_bytes()).hexdigest(),path=log.relative_to(ROOT).as_posix()))

    def test_changed_head_range_hook_or_log_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=WORK/'14zw') as folder:
            log=pathlib.Path(folder)/'check.log';log.write_text('')
            valid=self.proof(log)
            with patch.object(p,'identity',return_value={'checker':'fixture'}):
                p.verify(valid,H)
                for key,value in (('head',R),('remote_before',H),('exit_code',1),('no_verify',True),
                                  ('commits_checked',[]),('identity',{'checker':'changed'})):
                    with self.subTest(key=key),self.assertRaises(AssertionError):p.verify(dict(valid,**{key:value}),H)
                log.write_text('changed')
                with self.assertRaises(AssertionError):p.verify(valid,H)

    def test_standard_input_round_trips_real_bash_four_fields(self):
        result=subprocess.run([p.BASH,'--noprofile','--norc','-c',
            'read -r local_ref local_sha remote_ref remote_sha extra; test -z "$extra" || exit 1; printf "%s\\n" "$local_ref" "$local_sha" "$remote_ref" "$remote_sha"'],
            input=p.standard_input(H,R),capture_output=True,text=True)
        self.assertEqual(result.returncode,0)
        self.assertEqual(result.stdout.splitlines(),['refs/heads/pkg/14-owner-tools',H,'refs/heads/pkg/14-owner-tools',R])
        self.assertEqual(result.stderr,'')

    def test_failed_privacy_prevents_dispatch_without_github_privacy_lookup(self):
        spec=importlib.util.spec_from_file_location('control',WORK/'14zw-control.py')
        c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
        with patch.object(c,'live_gate'),patch.object(c,'source_gate',return_value=H), \
             patch.object(c,'privacy',side_effect=AssertionError('STOP hook proof')), \
             patch.object(c.guard,'api') as api,patch.object(c.subprocess,'run') as post:
            for mode in ('probe','owner-tools'):
                with self.assertRaisesRegex(AssertionError,'hook proof'):c.dispatch(mode)
            post.assert_not_called();api.assert_not_called()

    def test_private_repository_check_remains_required(self):
        spec=importlib.util.spec_from_file_location('control',WORK/'14zw-control.py')
        c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
        with patch.object(c,'live_gate'),patch.object(c,'source_gate',return_value=H), \
             patch.object(c,'out',return_value=H),patch.object(c.guard,'read_only',return_value=b'{"private":false}'), \
             patch.object(c.local_privacy,'verify') as verify:
            with self.assertRaisesRegex(AssertionError,'not private'):c.privacy()
            verify.assert_not_called()

if __name__=='__main__':unittest.main()
