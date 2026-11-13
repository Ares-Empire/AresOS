import sys,json
import argparse
from contextlib import nullcontext
from unittest.mock import patch
from pathlib import Path
from importlib.machinery import SourceFileLoader
from aresos_control.common import canonical,digest
from test_owner_state_sweep import OwnerScenario
parser=argparse.ArgumentParser(description='Five-operation STORAGE-S2 harness, extended to the stopped stage-3 candidate')
parser.add_argument('output',type=Path)
parser.add_argument('--local-policy',action='store_true',help='Use only synthetic managed-policy files under this worktree')
options=parser.parse_args()
policy=SourceFileLoader('local_policy',str(Path(__file__).with_name('STORAGE-S3-LOCAL-POLICY.py'))).load_module() if options.local_policy else None

def sizes(s):
 f=s.fixture
 def size(p):return p.stat().st_size if p.exists() else 0
 return {'journal_bytes':size(f.root/'evidence/operations.jsonl'),
         'sqlite_file_bytes':size(f.root/'state/control.sqlite'),
         'sqlite_event_bytes':sum(len(canonical(e).encode()) for e in f.engine.store.iter_audit()),
         'index_bytes':size(f.root/'evidence/journal-index.sqlite'), 'projection_bytes':size(f.root/'evidence/owner-state.jsonl'),
         'projection_records':sum(1 for line in (f.root/'evidence/owner-state.jsonl').read_bytes().splitlines()) if (f.root/'evidence/owner-state.jsonl').exists() else 0,
         'journal_records':sum('operations' in json.loads(line) for line in (f.root/'evidence/operations.jsonl').read_text().splitlines())}

result={}
with policy.local_policy() if policy else nullcontext():
 for kind in ('send','move','delete','free_change','send_25mib'):
  s=OwnerScenario('fixture')
  try:
   f=s.fixture
   def create(name):
    name=name.strip('"');f.imap.boxes[name]={};f.imap.roles[name]=[];f.imap.validities[name]=len(f.imap.validities)+1
    return 'OK',[b'Created']
   s.stack.enter_context(patch.object(f.imap,'create',side_effect=create,create=True))
   def append(account,folder,raw,flags=None):
    uid=max(f.imap.boxes[folder],default=0)+1;f.imap.boxes[folder][uid]=raw
    return {'account':account['id'],'folder':folder,'uidvalidity':f.imap.validities[folder],'uid':uid}
   s.stack.enter_context(patch.object(f.mail,'append',side_effect=append))
   original_uid=f.imap.uid
   def uid(command,*args):
    if command in {'MOVE','COPY'}:
     number,target=int(args[0]),args[1].strip('"');destination=max(f.imap.boxes[target],default=0)+1
     f.imap.boxes[target][destination]=f.imap.boxes[f.imap.selected][number]
     if command=='MOVE':del f.imap.boxes[f.imap.selected][number]
     f.imap.copyuid=f'{f.imap.validities[target]} {number} {destination}'.encode()
     return 'OK',[b'Filed']
    return original_uid(command,*args)
   s.stack.enter_context(patch.object(f.imap,'uid',side_effect=uid))
   attachment=None
   if kind=='send_25mib':
    raw=b'x'*(25*1024*1024)
    attachment={'sha256':f.engine.blobs.put(raw,origin='caller_import'),'size':len(raw),'name':'fixture.bin',
       'real_path':'/synthetic/fixture.bin','last_changed':'2026-11-09T12:00:00+00:00'}
    f.engine.store.write({'blob:'+digest(attachment):attachment},'fixture','Synthetic caller import')
    del raw
   ref={'account':'box','folder':'Source','uidvalidity':f.imap.validities['Source'],'uid':1,'message_id':f.imap.mid}
   before=sizes(s)
   if kind in {'send','send_25mib'}:
    comp=f.compose(to=['one@mail.invalid'],text='Synthetic body',**({'attachments':[attachment]} if attachment else {}))
    s.args=f.approval('send',comp);s.operation_id=s.args['operation_id'];s.action='mail_send'
   elif kind=='move':s.action,s.args='mail_move',{'references':[ref],'target':'Target'}
   elif kind=='delete':
    s.args=f.approval('delete',{'items':[f.mail.named_item(ref)],'mode':'permanent'})
    s.operation_id=s.args['operation_id'];s.action='mail_delete'
   else:s.action,s.args='mail_folder_create',{'account':'box','name':'Created'}
   print('measuring',kind,flush=True)
   reply={'ok':True,'data':f.engine.dispatch(s.action,s.args)}
   after=sizes(s)
   result[kind]={key:after[key]-before[key] for key in before}
   result[kind]['outcome']=reply['data'].get('state',reply['data'].get('operation',{}).get('state','done'))
   entries=[]
   projection=getattr(f.engine.store,'owner_projection',None)
   if projection:
    frames=list(projection.frames())
    lines=projection.path.read_bytes().splitlines(keepends=True)
    for line,(frame,data) in zip(lines,frames):
     if frame['seq']<=f.engine.store.sequence-result[kind]['journal_records']:continue
     entries.append({'seq':frame['seq'],'bytes':len(line),'audit':data['audit'],
       'patch_keys':sorted(data['changes']), 'compressed_delta_bytes':len(frame['delta']),
       'framing_bytes':len(line)-len(frame['delta'])})
   result[kind]['projection_detail']=entries
  finally:s.close()
options.output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps(result,sort_keys=True))
