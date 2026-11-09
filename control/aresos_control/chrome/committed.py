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
            for key,value in record.get('chrome',{}).items():
                if value is None:
                    self.entries.pop(key,None)
                    continue
                previous=self.entries.get(key)
                ack=isinstance(value,dict) and value.get('ack',False)
                if ack:self.mark_ack(key)
                if key.startswith('notice:') and not ack:
                    ack=previous['ack'] if previous else self.was_acknowledged(key)
                self.entries[key]={'offset':start,'time':previous['time'] if previous else record['time'],
                    'ack':bool(ack),'state':value.get('state') if isinstance(value,dict) else None}
                if len(self.entries)>MAX_KEYS:
                    raise Refused('owner_state_unavailable','Chrome current owner-state index exceeds its bound; inspect and archive finished history.')
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
        if key.startswith('notice:') and isinstance(value,dict):value['ack']=entry['ack']
        return value

    def rows(self,prefix,state=None):
        self.sync()
        for key in sorted(self.entries):
            if key.startswith(prefix) and (state is None or self.entries[key]['state'] in state):
                yield key,self.get(key),self.entries[key]['time']
