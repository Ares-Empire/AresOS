import copy,importlib.util,json,pathlib,unittest
from unittest.mock import Mock
W=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('watch',W/'14za_watcher.py');watch=importlib.util.module_from_spec(spec);spec.loader.exec_module(watch)
REPO='Ares-Empire/AresOS';HEAD='2fb695cdb419d67b51a76d91727668b33df82ecd';URL='https://github.com/'+REPO+'/actions/runs/40560134727\n'
real=json.loads((W/'run-40560134727/run.json').read_text())

class WatchTest(unittest.TestCase):
 def confirm(self,values,output=URL):
  api=Mock(side_effect=values);record=Mock();sleep=Mock()
  result=watch.confirm(output,REPO,HEAD,'pkg/14-owner-tools','Two-disk rehearsal (probe)',api,record,sleep)
  return result,api,record,sleep
 def test_real_retained_probe_identity_does_not_read_history(self):
  result,api,record,sleep=self.confirm([real]);self.assertEqual(result['id'],40560134727)
  api.assert_called_once_with('actions/runs/40560134727');sleep.assert_not_called();self.assertEqual(record.call_args.args[0]['status'],'confirmed')
 def test_delayed_display_fields_outlast_old_eight_second_window(self):
  pending=copy.deepcopy(real);pending['display_title']='OS image';pending['head_branch']=None
  result,api,record,sleep=self.confirm([pending]*4+[real]);self.assertEqual(result['id'],real['id']);self.assertEqual(api.call_count,5)
  self.assertEqual([x.args[0] for x in sleep.call_args_list],[1,2,4,8]);self.assertEqual(len(record.call_args.args[0]['observations']),5)
 def test_every_wrong_identity_field_refuses_with_all_observations(self):
  for key in watch.FIELDS:
   value=copy.deepcopy(real);value[key]=2 if key in ('id','run_attempt') else 'wrong'
   api=Mock(return_value=value);record=Mock();sleep=Mock()
   with self.subTest(key=key),self.assertRaisesRegex(AssertionError,'six reads'):
    watch.confirm(URL,REPO,HEAD,'pkg/14-owner-tools','Two-disk rehearsal (probe)',api,record,sleep)
   self.assertEqual(api.call_count,6);self.assertEqual(len(record.call_args.args[0]['observations']),6);self.assertEqual(record.call_args.args[0]['status'],'stopped')
 def test_ambiguous_or_foreign_url_refuses_without_api(self):
  for output in ('',URL+URL,URL.replace('github.com','example.com'),URL.replace(REPO,'other/repo'),URL.replace('40560134727','0')):
   api=Mock()
   with self.subTest(output=output),self.assertRaisesRegex(AssertionError,'canonical run URL'):
    watch.confirm(output,REPO,HEAD,'pkg/14-owner-tools','Two-disk rehearsal (probe)',api,Mock(),Mock())
   api.assert_not_called()
 def test_http_auth_or_transport_failure_is_not_multiplied_by_polling(self):
  api=Mock(side_effect=RuntimeError('read-only policy exhausted'));record=Mock()
  with self.assertRaises(RuntimeError):watch.confirm(URL,REPO,HEAD,'pkg/14-owner-tools','Two-disk rehearsal (probe)',api,record,Mock())
  self.assertEqual(api.call_count,1);record.assert_not_called()
 def test_terminal_failure_is_retained_and_never_becomes_success(self):
  value=dict(real,status='completed',conclusion='failure');result,api,record,sleep=self.confirm([value])
  self.assertEqual(result['conclusion'],'failure');self.assertEqual(record.call_args.args[0]['observations'][0]['conclusion'],'failure')
 def test_old_list_predicate_matches_current_retained_probe(self):
  listing=[real];matches=[r for r in listing if r['head_sha']==HEAD and r['event']=='workflow_dispatch' and r['display_title']=='Two-disk rehearsal (probe)'];self.assertEqual(len(matches),1)

if __name__=='__main__':unittest.main()
