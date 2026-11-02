"""Execute the real local dispatch wrapper with every external boundary stubbed."""
import importlib.util,pathlib,json,datetime,subprocess,unittest,contextlib,io
from unittest.mock import Mock,patch
W=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('control',W/'14za-control.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
H=c.TARGET;RUN=40600000000;URL='https://github.com/Ares-Empire/AresOS/actions/runs/'+str(RUN)+'\n'
class ControlTest(unittest.TestCase):
 def test_one_post_and_delayed_direct_confirmation_never_reads_history_or_reposts(self):
  plan=c.guard.owner_reservations();proof=dict(reservation_plan=plan,reserved_minutes=160,allowance='14',native=dict(sha=H,status='passed'),cap=800,consumed_minutes=573,organization_budget=dict(after_reservation=200,checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat()),dispatch_counts={'probe':14,'owner-tools':3},probe_run=40560134727)
  run=dict(id=RUN,head_sha=H,head_branch=c.BRANCH,event='workflow_dispatch',display_title=c.guard.SETTINGS['titles']['owner-tools'],path='.github/workflows/os-image.yml',run_attempt=1,html_url=URL.strip(),status='queued',conclusion=None)
  pending=dict(run,display_title='OS image');reads=[]
  def api(path):
   reads.append(path)
   if path.startswith('git/ref/'):return dict(object=dict(sha=H))
   assert path=='actions/runs/'+str(RUN),path
   return pending if reads.count(path)<5 else run
  confirm=c.watcher.confirm
  with patch.object(c,'source_gate',return_value=H),patch.object(c,'read',return_value=proof),patch.object(c,'write') as write,patch.object(c.guard,'api',side_effect=api),patch.object(c.subprocess,'check_output',return_value=json.dumps(dict(state='OPEN',isDraft=True,headRefOid=H)).encode()),patch.object(c.subprocess,'run',return_value=subprocess.CompletedProcess([],0,URL,'')) as post,patch.object(c.watcher,'confirm',side_effect=lambda *a:confirm(*a,sleep=Mock())),contextlib.redirect_stdout(io.StringIO()):
   c.dispatch('owner-tools')
  self.assertEqual(post.call_count,1)
  self.assertEqual(post.call_args.args[0],['gh','workflow','run','os-image.yml','--repo',c.REPO,'--ref',c.BRANCH,'-f','rehearsal=owner-tools','-f','probe_run=40560134727'])
  self.assertNotIn(c.guard.RUN_HISTORY_PATH,reads);self.assertEqual(reads.count('actions/runs/'+str(RUN)),5)
  self.assertEqual(write.call_args.args,('14za-owner-tools-run.json',run))
 def test_other_dispatch_mode_refused_before_any_post(self):
  with patch.object(c.subprocess,'run') as post,self.assertRaisesRegex(AssertionError,'qualification4'):c.dispatch('probe')
  post.assert_not_called()
if __name__=='__main__':unittest.main()
