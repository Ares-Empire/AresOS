"""The per-request operation queries stay at the index's speed with history (step 7).

Final fixes F1 turned the three shapes every Chrome request runs (_expire,
retention.expire, _pending) into scans over every retained operation; at 4,000
operations each took 12-14 ms and the latency ceilings failed (run 43566651314).
The partial index operation_open brings them back under about a millisecond.
No browser: the bridge is the test fixture's, so a request's time here is the
service's own, as the latency profile's service_total stage measures it.
"""
import json
import statistics
import time
import unittest

import test_engine
from aresos_control import storage
from aresos_control.retention import OPEN
from test_full_disk_reads import Recorded, retain

# The shapes a request runs, by caller.
PER_REQUEST={'expire':dict(states={'reserved'}),'retention_expire':dict(states=OPEN),'pending':dict(exclude_app='chrome',unresolved=True),
             'unresolved_sent_checks':dict(app='mail',unresolved=True),'recovery_notices':dict(legacy_open=True)}


def unresolved(op):
    # The Python reading of the index expression, for the scan baseline.
    state=op.get('state')
    return (not isinstance(state,str) or state[:1] in ('[','{') or state in OPEN or bool(op.get('notice')) and not op.get('ack')
            or (op.get('sent_copy_check') or {}).get('state')=='open')
HISTORIES=(1000,4000)
# Bounds generous enough for a slow runner: the median of several repeats must
# stay well under a scan of the same rows measured in the same process, and
# under an absolute ceiling far above the index's measured 0.02-0.05 ms.
SCAN_FRACTION=0.25
ABSOLUTE_MS=5.0
# A Chrome read's service time with 4,000 operations must stay under the lead's
# client-side read ceiling (35 ms median), which includes the bridge and the client.
READ_SERVICE_MS=35.0


def median_ms(call,repeats):
    times=[]
    for _ in range(repeats):
        start=time.perf_counter();call();times.append((time.perf_counter()-start)*1000)
    return statistics.median(times)


class OpenIndexTiming(unittest.TestCase):
    def history(self,count):
        fixture=test_engine.Operations();fixture.setUp();self.addCleanup(fixture.tearDown)
        target=fixture.browser.facts['frames'][0]['target'];target['name']=target['label']='Continue'
        self.assertTrue(fixture.call('click',fixture.target())['ok'])
        # Completed rows only, as the CI latency fixture retains them. (An
        # unfinished Chrome row costs the committed projection a canonical hash
        # on every pending view, whatever the history size.)
        retain(fixture.engine.store,count,unfinished=False)
        return fixture

    def shape_sql(self,store,shape):
        recorded=Recorded(store.db);original=store.db;store.db=recorded
        try:list(store.iter_operations(**shape))
        finally:store.db=original
        (sql,parameters),=[row for row in recorded.statements if row[0].startswith('SELECT k,v FROM kv')]
        self.assertIn(' AND '+storage.OPEN_OPERATIONS,sql)
        return sql,parameters

    def test_the_per_request_shapes_read_the_index_at_1000_and_4000_operations(self):
        record={}
        for count in HISTORIES:
            fixture=self.history(count);store=fixture.engine.store
            self.assertGreaterEqual(sum(1 for _ in store.iter_items('op:')),count)
            for name,shape in PER_REQUEST.items():
                sql,parameters=self.shape_sql(store,shape)
                scan_sql=sql.replace(' AND '+storage.OPEN_OPERATIONS,'',1)
                run=lambda statement:[json.loads(v) for _,v in store.db.execute(statement,parameters)]
                self.assertEqual(run(sql),[op for op in run(scan_sql) if unresolved(op)],'the index term only narrows to unresolved rows')
                indexed=median_ms(lambda:run(sql),9);scan=median_ms(lambda:run(scan_sql),5)
                record[f'{count}:{name}']={'indexed_ms':round(indexed,3),'scan_ms':round(scan,3)}
                with self.subTest(count=count,shape=name):
                    self.assertLess(indexed,ABSOLUTE_MS,record)
                    self.assertLess(indexed,scan*SCAN_FRACTION,record)
            # The service side of a Chrome read and of the pending view, as the
            # latency profile times engine.request.
            read=median_ms(lambda:self.assertTrue(fixture.call('read',{'tab':1})['ok']),7)
            pending=median_ms(lambda:fixture.engine.pending(),7)
            record[f'{count}:chrome_read_service']={'median_ms':round(read,2)}
            record[f'{count}:engine_pending']={'median_ms':round(pending,2)}
            with self.subTest(count=count,call='chrome_read'):
                self.assertLess(read,READ_SERVICE_MS,record)
        print('\nstep7-timing '+json.dumps(record,sort_keys=True))


if __name__=='__main__':
    unittest.main()
