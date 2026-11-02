import pathlib,importlib.util,unittest,tempfile,subprocess,json
r=pathlib.Path.cwd();s=importlib.util.spec_from_file_location('basic',r/'.work/14/14zv-basic.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class BasicTest(unittest.TestCase):
 def test_no_artifact_still_retains_actual_response_fields_and_logs(self):
  def api(path):
   if path.endswith('/jobs?per_page=100'):return dict(total_count=0,jobs=[])
   if path.endswith('/artifacts?per_page=100'):return dict(total_count=0,artifacts=[])
   return dict(status='completed',run_attempt=1,head_sha='a'*40,head_branch='pkg/14-owner-tools',conclusion='failure')
  with tempfile.TemporaryDirectory(dir=r/'os/tests') as d:
   p=pathlib.Path(d)/'record';v=m.export(7,'a'*40,p,api,lambda path:b'fixture-log-zip')
   self.assertEqual(v['artifacts'],0);self.assertEqual(v['conclusion'],'failure');self.assertTrue((p/'jobs.json').exists())
 def test_wrong_identity_refuses_before_creating_any_record(self):
  with tempfile.TemporaryDirectory(dir=r/'os/tests') as d:
   p=pathlib.Path(d)/'record'
   with self.assertRaises(AssertionError):m.export(7,'a'*40,p,lambda path:dict(status='in_progress',run_attempt=1,head_sha='a'*40),None)
   self.assertFalse(p.exists())
if __name__=='__main__':unittest.main()
