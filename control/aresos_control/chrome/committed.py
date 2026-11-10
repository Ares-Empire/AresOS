"""Chrome's committed journal read fallback until 19b supplies the shared read path.

Only offsets/flags for current keys are indexed. Values stay on disk. The
append-only journal, including acknowledgement updates, is the authority.
"""
import copy
import json

from ..common import Refused, digest

MAX_KEYS=32768


class Projection:
    def __init__(self, store):
        self.store=store
        self.offset=0
        self.sequence=0
        self.generation=None
        self.hash=''
        self.entries={}
        self.ack_filter=bytearray(8192)
        self.legacy=False
        self.signature=None
        self.record_cache={}

    def bit(self,key):
        return int(digest(key)[:8],16)%(len(self.ack_filter)*8)

    def seen_ack(self,key):
        bit=self.bit(key)
        return bool(self.ack_filter[bit//8] & (1<<(bit%8)))

    def mark_ack(self,key):
        bit=self.bit(key);self.ack_filter[bit//8] |= 1<<(bit%8)

    def committed_records(self, offset=0):
        with open(self.store.evidence_dir/'operations.jsonl','rb') as stream:
            stream.seek(offset)
            pending=None
            while True:
                start=stream.tell();line=stream.readline()
                if not line or not line.endswith(b'\n'):return
                value=json.loads(line)
                if 'commit' not in value:
                    pending=(start,value)
                    continue
                if pending is None or value!={'commit':pending[1]['seq'],'hash':pending[1]['hash']}:
                    raise Refused('evidence_corrupt','Chrome committed owner-state journal is inconsistent; inspect the service.')
                yield pending[0],stream.tell(),pending[1]
                pending=None

    def was_acknowledged(self,key):
        # The filter is only an optimization. A possible hit is verified on disk.
        if not self.seen_ack(key):return False
        for _,_,record in self.committed_records():
            value=record.get('chrome',{}).get(key)
            if isinstance(value,dict) and value.get('ack'):return True
        return False

    def rebuild(self):
        # A historical peak must not prevent later archive tombstones from
        # taking effect. Scan bounded sorted windows through the whole history,
        # retaining only final live keys, never all historical IDs or values.
        sequence=0;previous='';end=0;generation=None;legacy=False
        for _,end,record in self.committed_records():
            if record['seq']!=sequence+1 or record['previous']!=previous or digest({k:v for k,v in record.items() if k!='hash'})!=record['hash']:
                raise Refused('evidence_corrupt','Chrome owner-state history failed its hash chain.')
            sequence=record['seq'];previous=record['hash'];generation=record['generation']
            legacy |= 'chrome' not in record and any(op.get('description',{}).get('action','').startswith('chrome_') for op in record.get('operations',[]))
        def updates(record):
            if 'chrome' not in record:
                for op in record.get('operations',[]):
                    if op.get('description',{}).get('action','').startswith('chrome_'):
                        yield 'op:'+op['id'], None if op['state'] in {'done','failed'} else {'state':'unknown'},op['id']
            for key,value in record.get('chrome',{}).items():yield key,value,None
        entries={};cursor='';self.ack_filter=bytearray(8192)
        while True:
            batch={}
            for start,through,record in self.committed_records():
                if through>end:break
                for key,value,old_id in updates(record):
                    if key<=cursor:continue
                    if key not in batch and len(batch)==32:
                        largest=max(batch)
                        if key>largest:continue
                        del batch[largest]
                    old=batch.get(key,{'entry':None,'ack':False})
                    ack=old['ack'] or isinstance(value,dict) and bool(value.get('ack'))
                    entry=None if value is None else {'offset':start,'time':old['entry']['time'] if old['entry'] else record['time'],
                        'ack':ack,'state':value.get('state') if isinstance(value,dict) else None}
                    if entry is not None and old_id:entry['legacy']=old_id
                    batch[key]={'entry':entry,'ack':ack}
            if not batch:break
            for key,known in batch.items():
                if known['ack']:self.mark_ack(key)
                if known['entry'] is not None:
                    entries[key]=known['entry']
                    if len(entries)>MAX_KEYS:
                        # Leave the old checkpoint intact: a later appended
                        # archive is rescanned and can make this read succeed.
                        raise Refused('owner_state_unavailable','Chrome current owner-state index exceeds its bound; inspect and archive finished history.')
            cursor=max(batch)
        self.entries=entries;self.offset=end;self.sequence=sequence;self.hash=previous;self.generation=generation;self.legacy=legacy

    def sync(self):
        info=(self.store.evidence_dir/'operations.jsonl').stat()
        signature=(info.st_ino,info.st_size,info.st_mtime_ns)
        if signature==self.signature:return
        if info.st_size<self.offset:raise Refused('evidence_corrupt','Committed Chrome owner history was truncated; inspect the independent record.')
        self.record_cache.clear()
        for start,end,record in self.committed_records(self.offset):
            content={key:value for key,value in record.items() if key!='hash'}
            if record['seq']!=self.sequence+1 or record['previous']!=self.hash or digest(content)!=record['hash']:
                raise Refused('evidence_corrupt','Chrome owner-state history failed its hash chain; no cached state is authoritative.')
            for operation in record.get('operations',[]):
                if operation.get('description',{}).get('action','').startswith('chrome_') and 'chrome' not in record:
                    self.legacy=True
                    key='op:'+operation['id']
                    if operation['state'] not in {'done','failed'}:
                        self.entries[key]={'offset':start,'time':record['time'],'ack':False,'state':'unknown','legacy':operation['id']}
                    else:self.entries.pop(key,None)
                    if len(self.entries)>MAX_KEYS:
                        self.rebuild();self.signature=signature;return
            for key,value in record.get('chrome',{}).items():
                if value is None:
                    self.entries.pop(key,None)
                    continue
                previous=self.entries.get(key)
                ack=isinstance(value,dict) and value.get('ack',False)
                if ack:self.mark_ack(key)
                if key.startswith(('notice:','op:')) and not ack:
                    ack=previous['ack'] if previous else self.was_acknowledged(key)
                self.entries[key]={'offset':start,'time':previous['time'] if previous else record['time'],
                    'ack':bool(ack),'state':value.get('state') if isinstance(value,dict) else None}
                if len(self.entries)>MAX_KEYS:
                    self.rebuild();self.signature=signature;return
            self.offset=end;self.sequence=record['seq'];self.hash=record['hash'];self.generation=record['generation']
        self.signature=signature

    def get(self,key,default=None):
        self.sync()
        entry=self.entries.get(key)
        if entry is None:return copy.deepcopy(default)
        record=self.record_cache.get(entry['offset'])
        if record is None:
            with open(self.store.evidence_dir/'operations.jsonl','rb') as stream:
                stream.seek(entry['offset']);record=json.loads(stream.readline())
            if len(json.dumps(record))<=4*1024*1024:
                if len(self.record_cache)>=5:self.record_cache.pop(next(iter(self.record_cache)))
                self.record_cache[entry['offset']]=record
        if digest({key:value for key,value in record.items() if key!='hash'})!=record['hash']:
            raise Refused('evidence_corrupt','Chrome owner-state record changed; inspect the service before proceeding.')
        if entry.get('legacy'):
            known=next(item for item in record['operations'] if item['id']==entry['legacy'])
            return {'id':known['id'],'app':'chrome','state':'unknown','reason':'Older Chrome record lacks a complete owner-state projection; inspect before any further action.','payload':{},'stages':{},'approval':{'description':known['description']}}
        value=copy.deepcopy(record['chrome'][key])
        if key.startswith(('notice:','op:')) and isinstance(value,dict) and entry['ack']:value['ack']=True
        return value

    def historical(self, key, default=None):
        """Last committed value, including retired checks; no side index or file.

        Tombstones retire working data, not an occurrence's identity or ack.
        This slow path is used only when a retired identity is seen again.
        """
        value=default;ack=False;sequence=0;previous=''
        for _,_,record in self.committed_records():
            if record['seq']!=sequence+1 or record['previous']!=previous or digest({k:v for k,v in record.items() if k!='hash'})!=record['hash']:
                raise Refused('evidence_corrupt','Chrome historical receipt failed its hash chain.')
            sequence=record['seq'];previous=record['hash']
            update=record.get('chrome',{}).get(key)
            if update is not None:
                value=copy.deepcopy(update)
                ack |= isinstance(update,dict) and bool(update.get('ack'))
        if ack and isinstance(value,dict):value['ack']=True
        return copy.deepcopy(value)

    def restore_rows(self):
        """Bounded windows over all current Chrome keys, even above MAX_KEYS.

        Restore and archival must remain possible when the fast read index is
        unavailable. Values and tombstones come only from committed history.
        """
        cursor='';sequence=0;previous=''
        for _,_,record in self.committed_records():
            if record['seq']!=sequence+1 or record['previous']!=previous or digest({k:v for k,v in record.items() if k!='hash'})!=record['hash']:
                raise Refused('evidence_corrupt','Chrome restore history failed its hash chain.')
            sequence=record['seq'];previous=record['hash']
        while True:
            batch={}
            for _,_,record in self.committed_records():
                if record['seq']>sequence:break
                for key,value in record.get('chrome',{}).items():
                    if key<=cursor:continue
                    if key not in batch and len(batch)==32:
                        largest=max(batch)
                        if key>largest:continue
                        del batch[largest]
                    old,ack=batch.get(key,(None,False))
                    ack |= isinstance(value,dict) and bool(value.get('ack'))
                    batch[key]=(value,ack)
            if not batch:return
            for key,(value,ack) in sorted(batch.items()):
                value=copy.deepcopy(value)
                if ack and isinstance(value,dict):value['ack']=True
                yield key,value
            cursor=max(batch)

    def rows(self,prefix,state=None):
        self.sync()
        for key in sorted(self.entries):
            if key.startswith(prefix) and (state is None or self.entries[key]['state'] in state):
                yield key,self.get(key),self.entries[key]['time']
