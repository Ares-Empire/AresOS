"""CI-only timers around the real service and bridge, without page values."""
import copy
import json
import os
from pathlib import Path
import time

from aresos_control import storage as storage_module

MARKER=Path('/out/latency-marker.json')
OUT=Path('/out/latency-service.jsonl')
STORE_STAGES={'store_write_ms':0.0,'fsync_ms':0.0,'fsync_count':0,'sqlite_commit_count':0}
# What the sqlite3 module sends when it commits a transaction.
COMMITS=('COMMIT','END')

class TimedOS:
    """The storage module's os: its fsync calls are timed into the marked sample."""
    def __init__(self,account):self.account=account
    def __getattr__(self,name):return getattr(os,name)
    def fsync(self,fd):
        start=time.perf_counter()
        try:return os.fsync(fd)
        finally:self.account('fsync',(time.perf_counter()-start)*1000)

def install(daemon):
    active=None
    wire_phases={}
    bridge=daemon.engine.adapters['chrome'].bridge
    original_request=daemon.engine.request
    original_call=bridge.call
    def emit(row):
        with OUT.open('a') as output:output.write(json.dumps(row)+'\n')
    # Storage stages (main fix H5): the store's synchronous writes and the
    # journal's fsyncs, summed per marked sample so a tail is attributable
    # from the artifact. Work outside a marked sample is not counted.
    def account(kind,milliseconds):
        if active is None:return
        if kind=='fsync':active['fsync_ms']+=milliseconds;active['fsync_count']+=1
        else:active['store_write_ms']+=milliseconds
    store=daemon.engine.store
    original_write=store.write
    def write(*arguments,**keywords):
        start=time.perf_counter()
        try:return original_write(*arguments,**keywords)
        finally:account('store_write',(time.perf_counter()-start)*1000)
    store.write=write
    storage_module.os=TimedOS(account)
    # SQLite commits (brief 20-ci-noise). control.sqlite runs synchronous=FULL,
    # so each commit syncs the disk inside SQLite, where TimedOS can't see it.
    # The trace callback sees every COMMIT statement on the store's connection
    # and only counts it, so the product behaves as without the probe. With the
    # store on a tmpfs these counts, not the timings, catch an added disk sync.
    def traced(statement):
        if active is not None and statement.lstrip().upper().startswith(COMMITS):active['sqlite_commit_count']+=1
    store.db.set_trace_callback(traced)
    class Wire:
        def __init__(self,connection):self.connection=connection
        def __getattr__(self,name):return getattr(self.connection,name)
        def sendall(self,data):
            message=json.loads(data)
            if 'id' in message:wire_phases[message['id']]=dict(active) if active else None
            return self.connection.sendall(data)
    def call(name,**arguments):
        if bridge.connection is not None and not isinstance(bridge.connection,Wire):bridge.connection=Wire(bridge.connection)
        start=time.perf_counter()
        try:return original_call(name,**arguments)
        finally:
            elapsed=(time.perf_counter()-start)*1000
            if active is not None:
                active['bridge_ms']+=elapsed
                emit({'sample':active['sample'],'call':active['call'],'stage':'bridge_round_trip','command':name,'milliseconds':elapsed})
    bridge.call=call
    def request(value,admin=False):
        nonlocal active
        seed=Path('/out/latency-history-seed.json')
        if seed.exists():
            count=json.loads(seed.read_text())['count'];assert count in {1000,4000}
            seed.unlink()
            # Disposable timing input only: copy a real completed free-input
            # shape, never claim a receiver effect or qualification verdict.
            store=daemon.engine.store
            template=next(op for _,op in store.iter_items('op:') if op['app']=='chrome' and op['state']=='done' and op['action']=='chrome_click' and not op['payload'].get('kind'))
            for start in range(0,count,32):
                changes={}
                for index in range(start,min(start+32,count)):
                    operation=copy.deepcopy(template)
                    operation.update(id=store.generation+':latency-history-'+str(index),reason='Synthetic completed timing history; no input dispatched')
                    changes['op:'+operation['id']]=operation
                store.write(changes,'chrome_latency_fixture','Synthetic completed timing history; not acceptance')
            emit({'stage':'history_fixture','count':count,'journal_bytes':store.journal.seek(0,2)})
        previous=active
        try:marker=json.loads(MARKER.read_text())
        except FileNotFoundError:marker=None
        active={**marker,'bridge_ms':0,**STORE_STAGES} if marker else None
        start=time.perf_counter()
        try:return original_request(value,admin)
        finally:
            if active is not None:
                elapsed=(time.perf_counter()-start)*1000
                emit({'sample':active['sample'],'call':active['call'],'stage':'service_total','milliseconds':elapsed})
                emit({'sample':active['sample'],'call':active['call'],'stage':'service_without_bridge','milliseconds':max(0,elapsed-active['bridge_ms'])})
                emit({'sample':active['sample'],'call':active['call'],'stage':'store_write','milliseconds':active['store_write_ms']})
                emit({'sample':active['sample'],'call':active['call'],'stage':'journal_fsync','milliseconds':active['fsync_ms'],'count':active['fsync_count']})
                # A count, not a timing: the summary keeps it out of the stage percentiles.
                emit({'sample':active['sample'],'call':active['call'],'stage':'sqlite_commit','count':active['sqlite_commit_count']})
            active=previous
    daemon.engine.request=request
    original_expire=daemon.engine.expire
    def marker():
        try:return json.loads(MARKER.read_text())
        except FileNotFoundError:return None
    def expire():
        before=marker();start=time.perf_counter()
        try:return original_expire()
        finally:
            after=marker()
            if before and before==after:
                emit({**before,'stage':'daemon_expiry_inside_sample','milliseconds':(time.perf_counter()-start)*1000})
    daemon.engine.expire=expire
    event=bridge.on_event
    def on_event(value):
        if value.get('event') in {'latency_stage','latency_reader'}:
            phase=wire_phases.get((value.get('context') or {}).get('wire'))
            if phase:emit({'sample':phase['sample'],'call':phase['call'],**value})
            return
        return event(value)
    bridge.on_event=on_event
