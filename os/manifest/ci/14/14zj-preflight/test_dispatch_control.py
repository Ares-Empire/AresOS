import importlib.util,pathlib,json,datetime,subprocess,unittest,contextlib,io
from unittest.mock import Mock,patch
W=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('control',W/'14zj-control.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
H=c.TARGET;RUN=40600000000;URL='https://github.com/Ares-Empire/AresOS/actions/runs/'+str(RUN)+'\n'
class ControlTest(unittest.TestCase):
 def proof(self,mode):
  plan=c.guard.owner_reservations()
  return dict(reservation_plan=plan,reserved_minutes=plan['before_probe' if mode=='probe' else 'before_qualification'],
    allowance='14',native=dict(sha=H,status='pending' if mode=='probe' else 'passed'),cap=1200,consumed_minutes=647,
    organization_budget=dict(after_reservation=400,checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      paid_overflow=dict(budget_amount=6,prevent_further_usage=True)),dispatch_counts={'probe':18 if mode=='probe' else 19,'owner-tools':7},probe_run=40560134727)
 def boundaries(self,stack,proof,mode,exists=False):
  stack.enter_context(patch.object(c,'source_gate',return_value=H))
  stack.enter_context(patch.object(c,'read',return_value=proof))
  stack.enter_context(patch.object(c,'write'))
  stack.enter_context(patch.object(pathlib.Path,'exists',return_value=exists))
  stack.enter_context(patch.object(c.subprocess,'check_output',return_value=json.dumps(dict(state='OPEN',isDraft=True,headRefOid=H)).encode()))
  stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
 def test_probe_and_qualification_each_post_once_then_use_delayed_direct_confirmation(self):
  for mode in ('probe','owner-tools'):
   with self.subTest(mode=mode),contextlib.ExitStack() as stack:
    self.boundaries(stack,self.proof(mode),mode)
    real=dict(id=RUN,head_sha=H,head_branch=c.BRANCH,event='workflow_dispatch',display_title=c.guard.SETTINGS['titles'][mode],path='.github/workflows/os-image.yml',run_attempt=1,html_url=URL.strip(),status='queued',conclusion=None)
    reads=[]
    def api(path):
     reads.append(path)
     if path.startswith('git/ref/'):return dict(object=dict(sha=H))
     assert path=='actions/runs/'+str(RUN)
     return dict(real,display_title='OS image') if reads.count(path)<5 else real
    stack.enter_context(patch.object(c.guard,'api',side_effect=api))
    post=stack.enter_context(patch.object(c.subprocess,'run',return_value=subprocess.CompletedProcess([],0,URL,'')))
    confirm=c.watcher.confirm
    stack.enter_context(patch.object(c.watcher,'confirm',side_effect=lambda *a:confirm(*a,sleep=Mock())))
    c.dispatch(mode)
    self.assertEqual(post.call_count,1);self.assertEqual(reads.count('actions/runs/'+str(RUN)),5)
    args=['gh','workflow','run','os-image.yml','--repo',c.REPO,'--ref',c.BRANCH,'-f','rehearsal='+mode]
    if mode=='owner-tools':args+=['-f','probe_run=40560134727']
    self.assertEqual(post.call_args.args[0],args);self.assertNotIn(c.guard.RUN_HISTORY_PATH,reads)
 def test_existing_attempt_nonce_refuses_before_post(self):
  with contextlib.ExitStack() as stack:
   self.boundaries(stack,self.proof('probe'),'probe',exists=True)
   stack.enter_context(patch.object(c.guard,'api',return_value=dict(object=dict(sha=H))))
   post=stack.enter_context(patch.object(c.subprocess,'run'))
   with self.assertRaisesRegex(AssertionError,'already attempted'):c.dispatch('probe')
   post.assert_not_called()
 def test_stale_budget_wrong_amount_or_prevention_refuses_before_post(self):
  for defect in ('stale','amount','prevention'):
   proof=self.proof('probe')
   if defect=='stale':proof['organization_budget']['checked_at']=(datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(minutes=6)).isoformat()
   elif defect=='amount':proof['organization_budget']['paid_overflow']['budget_amount']=3
   else:proof['organization_budget']['paid_overflow']['prevent_further_usage']=False
   with self.subTest(defect=defect),contextlib.ExitStack() as stack:
    self.boundaries(stack,proof,'probe');post=stack.enter_context(patch.object(c.subprocess,'run'))
    with self.assertRaises(AssertionError):c.dispatch('probe')
    post.assert_not_called()
 def test_modes_outside_this_round_refuse_before_any_read_or_post(self):
  with patch.object(c,'source_gate') as source,patch.object(c.subprocess,'run') as post:
   for mode in ('full','part-b','keyboard','release-13'):
    with self.assertRaisesRegex(AssertionError,'probe19 and qualification8'):c.dispatch(mode)
   source.assert_not_called();post.assert_not_called()
if __name__=='__main__':unittest.main()
