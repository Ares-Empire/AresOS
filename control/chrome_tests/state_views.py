"""Compare each public Chrome state surface with the scenario/receiver oracle."""
import time
from chrome_oracle import history,expectations,compare,compare_validity


class StateViews:
    def begin_views(self,flow):
        self.script=[{'kind':'scenario','flow':flow}]
        self.receiver_log=[]
        self.view_counts={'persistent':0,'space_restored':0,'restart':0,'unavailable':0}

    def scenario_step(self,step):
        self.script.append({'kind':'step','session':self.browser.session,'tab':1,'step':dict(step)})

    def watch_receiver(self,authorized):
        original=self.browser.call
        def receive(name,**args):
            if name in {'input','resume','dialog'}:
                record=history(self.root/'evidence')
                operation=record['rows'].get('op:'+args['operation'],{})
                self.receiver_log.append({'operation':args['operation'],'authorized':authorized,
                    'committed_submitting':operation.get('state')=='submitting'})
            return original(name,**args)
        self.browser.call=receive

    def expected_views(self):
        return expectations(self.script,self.receiver_log,history(self.root/'evidence'))

    def compare_views(self,phase):
        before=list(self.browser.dispatched)
        self.expected_views()  # Assert triggers before a status/evidence read.
        for action in ['chrome_notices','control_pending','control_log','passive']:
            cursor=None;warnings=set();pending={}
            while True:
                request=({'v':1,'method':'tools','app':'chrome'} if action=='passive' else
                    {'v':1,'method':'call','action':action,'arguments':{'cursor':cursor} if cursor else {}})
                result=self.engine.request(request)
                expected=self.expected_views()
                data=result.get('data',{})
                if not result['ok']:
                    # A read failure must be explicit. An unavailable result is
                    # recorded separately, never counted as an equality pass.
                    self.assertIn(result['error']['code'],{'storage_limit','storage_error','journal_incomplete','restore_required','owner_state_unavailable'})
                    self.assertTrue(result.get('pending',{}).get('unavailable') or result['error']['code'] in {'restore_required','journal_incomplete','storage_limit','storage_error'})
                    self.view_counts['unavailable']+=1;break
                if action=='chrome_notices':
                    warnings.update(item['operation_id'] for item in data['items'])
                    cursor=data['cursor']
                elif action=='control_pending':
                    if data.get('unavailable'):
                        self.view_counts['unavailable']+=1;break
                    pending.update({item['operation_id']:item['state'] for item in data['items'] if item['app']=='chrome'})
                    record=history(self.root/'evidence')
                    for item in data['items']:
                        if item['app']=='chrome' and item['state']=='reserved':
                            compare_validity(record['rows']['op:'+item['operation_id']],item['validity'],{
                                'generation':record['records'][-1]['generation'],'now':time.time(),
                                'process_session':self.chrome.process_session,'session':self.browser.session,
                                'documents':{frame['frame']:frame['document'] for frame in self.browser.facts['frames']}})
                    warnings.update(item['operation_id'] for item in data.get('notices',[]) if item['app']=='chrome')
                    cursor=data['cursor']
                else:
                    view=result['pending'] if action=='passive' else data
                    if view.get('unavailable'):
                        self.view_counts['unavailable']+=1;break
                    warnings.update(item['operation_id'] for item in view.get('notices',[]) if item['app']=='chrome')
                    cursor=data.get('cursor') if action=='control_log' else None
                if not cursor:
                    compare(expected,warnings=warnings,pending=pending if action=='control_pending' else None)
                    self.view_counts[phase]+=1;break
        states={}
        for identifier in self.expected_views()['operations']:
            result=self.engine.request({'v':1,'method':'call','action':'chrome_operation_status','arguments':{'operation_id':identifier}})
            if result['ok']:states[identifier]=result['data']['operation']['state']
            else:
                self.assertIn(result['error']['code'],{'storage_limit','storage_error','journal_incomplete','restore_required','owner_state_unavailable'})
                self.view_counts['unavailable']+=1
        if len(states)==len(self.expected_views()['operations']):
            self.assertEqual(states,self.expected_views()['operations']);self.view_counts[phase]+=1
        self.assertEqual(self.browser.dispatched,before,'An owner-state read replayed input')
