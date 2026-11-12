import sys,json
import argparse
from contextlib import nullcontext
from unittest.mock import patch
from pathlib import Path
from importlib.machinery import SourceFileLoader
from aresos_control.common import canonical,digest
from aresos_control.archive import archive
from test_owner_state_sweep import OwnerScenario
parser=argparse.ArgumentParser(description='Fixed stage-3 owner facts, one-run archive and tombstone measurement')
parser.add_argument('output',type=Path)
parser.add_argument('--batch-size', type=int, default=1)
parser.add_argument('--recipient-count', type=int, choices=range(1, 101), default=1)
parser.add_argument('--kinds', default='send,move,delete,free_change,send_25mib')
parser.add_argument('--local-policy',action='store_true',help='Use only synthetic managed-policy files under this worktree')
options=parser.parse_args()
policy=SourceFileLoader('local_policy',str(Path(__file__).with_name('STORAGE-S3-LOCAL-POLICY.py'))).load_module() if options.local_policy else None

def sizes(s):
 f=s.fixture
 def size(p):return p.stat().st_size if p.exists() else 0
 projection=getattr(f.engine.store,'owner_projection',None)
 history=list((f.root/'evidence/owner-history').glob('*.bin'))
 archives=list((f.root/'evidence/archives').glob('*.jsonl'))
 return {'journal_bytes':size(f.root/'evidence/operations.jsonl'),
         'sqlite_file_bytes':size(f.root/'state/control.sqlite'),
         'sqlite_event_bytes':sum(len(canonical(e).encode()) for e in f.engine.store.iter_audit()),
         'index_bytes':size(f.root/'evidence/journal-index.sqlite'), 'source_bytes':size(f.root/'evidence/owner-source.bin'),
         'source_records':sum(1 for _ in f.engine.store.owner_source._records(f.engine.store.owner_source.path)) if hasattr(f.engine.store,'owner_source') else 0,
         'projection_bytes':size(f.root/'evidence/owner-state.bin'),
         'projection_records':sum(1 for _ in projection._records(projection.path)) if projection else 0,
         'tombstone_bytes':size(f.root/'evidence/owner-tombstones.bin'),
         'tombstone_records':sum(1 for _ in projection.stones()) if projection and projection.tombstones.exists() else 0,
         'owner_history_bytes':sum(size(p) for p in history),
         'owner_history_records':sum(sum(1 for _ in projection._records(p)) for p in history) if projection else 0,
         'archive_bytes':sum(size(p) for p in archives),
         'all_kept_file_bytes':sum(size(p) for root in ('state','evidence') for p in (f.root/root).rglob('*') if p.is_file()),
         'journal_records':sum('operations' in json.loads(line) for line in (f.root/'evidence/operations.jsonl').read_text().splitlines())}

result={}
with policy.local_policy() if policy else nullcontext():
 for kind in options.kinds.split(','):
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
   before_seq=f.engine.store.sequence
   peak=None
   checkpoint=f.engine.store.checkpoint
   def measured_checkpoint(label):
    global peak
    checkpoint(label)
    if label=='sqlite_prepared':
     store=f.engine.store
     live=any(row.get('state') in {'reserved','submitting','unknown','partial','started'} or row.get('check_open')
       for prefix in ('op:','intent:','mail:filing:','mail:rename:','export:') for _,row in store.iter_items(prefix))
     if live:
      observed=sizes(s)
      if peak is None or observed['all_kept_file_bytes']>peak['all_kept_file_bytes']:
       peak=observed
   f.engine.store.checkpoint=measured_checkpoint
   source_raw=f.imap.boxes['Source'][1]
   print('measuring',kind,'batch',options.batch_size,flush=True)
   operation_ids=[]
   for number in range(options.batch_size):
    if number:
     f.imap.boxes['Source'][number+1]=next(iter(f.imap.boxes['Sent'].values()), b'') if kind=='send' else source_raw
     ref={**ref,'uid':number+1}
    if kind in {'send','send_25mib'}:
     recipients = ['one@mail.invalid'] if options.recipient_count==1 else [str(i)+'@mail.invalid' for i in range(options.recipient_count)]
     comp=f.compose(to=recipients,text='Synthetic body',**({'attachments':[attachment]} if attachment and number==0 else {}))
     s.args=f.approval('send',comp);s.operation_id=s.args['operation_id'];s.action='mail_send'
    elif kind=='move':s.action,s.args='mail_move',{'references':[ref],'target':'Target'}
    elif kind=='delete':
     s.args=f.approval('delete',{'items':[f.mail.named_item(ref)],'mode':'permanent'})
     s.operation_id=s.args['operation_id'];s.action='mail_delete'
    else:s.action,s.args='mail_folder_create',{'account':'box','name':'Created'}
    reply={'ok':True,'data':f.engine.dispatch(s.action,s.args)}
    if s.operation_id:operation_ids.append(s.operation_id)
   f.engine.store.checkpoint=checkpoint
   after=sizes(s)
   assert peak is not None,('No committed-open-source checkpoint measured',kind)
   result[kind]={'before':before,'open':after,
      'while_open_peak':peak,
      'while_open_peak_delta':{key:peak[key]-before[key] for key in before},
      'open_delta':{key:after[key]-before[key] for key in before}}
   result[kind]['outcome']=reply['data'].get('state',reply['data'].get('operation',{}).get('state','done'))
   entries=[]
   projection=getattr(f.engine.store,'owner_projection',None)
   if projection:
    events={event['seq']:event for event in f.engine.store.iter_audit()}
    for seq,data,chain,length in projection._records(projection.path):
     if seq<=f.engine.store.sequence-result[kind]['open_delta']['journal_records']:continue
     event=events[seq]
     entries.append({'seq':seq,'bytes':length,'action':event['action'],'summary':event['summary'],
       'fields':{key:sorted(patch) if patch is not None else None for key,patch in data.items()},
       'compressed_delta_bytes':length-44,'framing_bytes':44})
   result[kind]['projection_detail']=entries
   source=getattr(f.engine.store,'owner_source',None)
   result[kind]['source_detail']=[{'seq':seq,'bytes':length,'action':event['action'], 'summary':event['summary'], 'keys':sorted(event['set'])} for seq,event,_,length in source._records(source.path) if seq>before_seq] if source else []
   # No pending or notice read is allowed to recreate evidence before this
   # storage sample. The clean fixtures must already be resolved and quiet.
   store=f.engine.store
   assert not any(not n.get('ack') for _,n in store.items('notice:'))
   s.advance_archive_clock()
   manifest=archive(store,s.test_clock-0.5,f.mail)
   finished=sizes(s)
   result[kind]['finished']=finished
   result[kind]['finished_delta']={key:finished[key]-before[key] for key in before}
   if projection:
    events={event['seq']:event for event in store.iter_audit()}
    # Ordinary full-history exports retain the other (now compacted) events.
    from owner_state_oracle.records import decode
    events.update({event['seq']:event for event in decode(f.root/'state',f.root/'evidence').events})
    result[kind]['retained_projection_detail']=[{'seq':seq,'bytes':length,'action':events[seq]['action'],
       'summary':events[seq]['summary'],
       'fields':{key:sorted(patch) if patch is not None else None for key,patch in data.items()}}
       for path in [] for seq,data,chain,length in projection._records(path)
       if seq>before_seq]
   result[kind]['retained_live_projection_detail']=[{'seq':seq,'bytes':length,'action':events[seq]['action'], 'summary':events[seq]['summary'], 'fields':{key:sorted(patch) if patch is not None else None for key,patch in data.items()}} for seq,data,_,length in projection._records(projection.path) if seq>before_seq] if projection else []
   source=getattr(store,'owner_source',None)
   result[kind]['retained_source_detail']=[{'seq':seq,'bytes':length,'action':event['action'], 'summary':event['summary'], 'keys':sorted(event['set'])} for seq,event,_,length in source._records(source.path) if seq>before_seq] if source else []
   result[kind]['tombstone_detail']=[{'seq':run['seq'],'bytes':length,'archive':run['name'], 'kind':'tombstone' if stone else 'resolution', 'key':stone['key'] if stone else None} for run,stone,_,length in projection.stones()] if projection and projection.tombstones.exists() else []
   result[kind]['batch_size']=options.batch_size
   result[kind]['recipient_count']=options.recipient_count if kind in {'send','send_25mib'} else None
   result[kind]['workload'] = ('one 25 MiB attachment send plus ' + str(options.batch_size-1) + ' ordinary sends'
      if kind=='send_25mib' else str(options.batch_size) + ' ' + kind + ' operations')
   result[kind]['archive']={key:manifest[key] for key in ('events','operations','independent_record_retained')}
   from owner_state_oracle.records import decode
   history = decode(f.root/'state',f.root/'evidence')
   result[kind]['archive_run_detail']=[{'seq':event['seq'],'summary':event['summary'],
      'full_event_bytes':len(canonical(event).encode()),
      'journal_with_marker_bytes':len(canonical(event['record']).encode())+1+
         len(canonical({'commit':event['seq'],'hash':event['record']['hash']}).encode())+1,
      'keys':sorted(event['set'])}
      for event in history.events if event['seq']>before_seq and event['action']=='control_archive']
   for identity in operation_ids:
    assert store.get('op:'+identity) is None,('Operation did not archive in ONE run',kind, identity)
   result[kind]['kept_files']=[{'path':str(p.relative_to(f.root)),'bytes':p.stat().st_size}
      for root in ('state','evidence') for p in sorted((f.root/root).rglob('*')) if p.is_file()]
  finally:s.close()
options.output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps(result,sort_keys=True))
