"""CI-only timers around the real service and bridge, without page values."""
import copy
import json
from pathlib import Path
import time

MARKER=Path('/out/latency-marker.json')
OUT=Path('/out/latency-service.jsonl')

def install(daemon):
    active=None
    wire_phases={}
    bridge=daemon.engine.adapters['chrome'].bridge
    original_request=daemon.engine.request
    original_call=bridge.call
    def emit(row):
        with OUT.open('a') as output:output.write(json.dumps(row)+'\n')
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
        active={**marker,'bridge_ms':0} if marker else None
        start=time.perf_counter()
        try:return original_request(value,admin)
        finally:
            if active is not None:
                elapsed=(time.perf_counter()-start)*1000
                emit({'sample':active['sample'],'call':active['call'],'stage':'service_total','milliseconds':elapsed})
                emit({'sample':active['sample'],'call':active['call'],'stage':'service_without_bridge','milliseconds':max(0,elapsed-active['bridge_ms'])})
            active=previous
    daemon.engine.request=request
    event=bridge.on_event
    def on_event(value):
        if value.get('event') in {'latency_stage','latency_reader'}:
            phase=wire_phases.get((value.get('context') or {}).get('wire'))
            if phase:emit({'sample':phase['sample'],'call':phase['call'],**value})
            return
        return event(value)
    bridge.on_event=on_event
