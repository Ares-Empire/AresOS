"""Retained history never makes a read need disk space (final fixes, F1 and step 7).

Every iter_operations shape reads an index in key order: the broad shapes the
primary key over every retained operation, the selective shapes (open states,
legacy notices, open or unacknowledged) the partial index operation_open on k
alone. A sort in a temporary B-tree spills to a temporary file once a few
hundred operations are retained; on a full disk that spill made Mail read,
search and control_pending return storage_limit, where main answers.
"""
import copy
import itertools
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mail_tests'))
import storage_faults
import test_engine
from aresos_control import storage
from aresos_control.mail import codec
from aresos_control.mail.roles import resolve
from aresos_control.mail.transport import folders, quote
from aresos_control.retention import OPEN

RETAINED=1200
# Every combination of iter_operations' filters, including the unfiltered walk.
SHAPES=[dict(app=app,exclude_app=exclude,legacy_open=legacy,states=states,unresolved=pending)
        for app,exclude,legacy,states,pending in itertools.product([None,'mail'],[None,'chrome'],[False,True],[None,OPEN,{'reserved'}],[False,True])]
# The shapes that look only at unresolved operations: the ones a request runs
# every time (states={'reserved'}, states=OPEN, unresolved with or without an
# app filter) and recovery's legacy_open. They must read the partial index.
def selective(shape):return shape['legacy_open'] or shape['states'] is not None or shape['unresolved']
# The header index an earlier build of this branch created; a database it
# touched may still carry it.
OLD_INDEX=("CREATE INDEX IF NOT EXISTS operation_headers ON kv(json_extract(v,'$.app'),"
           "json_extract(v,'$.context_version'),json_extract(v,'$.state')) WHERE substr(k,1,3)='op:'")


class ReadOnlyIMAP:
    """IMAP command substitute for reads; production selection, fetch and parsing run."""
    capabilities=('UIDPLUS','MOVE')
    def __init__(self,count,mid):
        self.raw=(b'From: sender@mail.invalid\r\nTo: owner@mail.invalid\r\nSubject: Retained\r\nMessage-ID: '
                  +mid+b'\r\n\r\nPreserved message\r\n')
        self.mid=str(codec.parse(self.raw)['Message-ID'])
        self.roles={'INBOX':[],'Source':[],'Sent':['\\Sent'],'Drafts':['\\Drafts'],'Trash':['\\Trash']}
        self.boxes={name:{} for name in self.roles}
        self.boxes['Source']={i:self.raw for i in range(1,count+1)}
        self.validities={name:i for i,name in enumerate(self.roles,1)}
        self.selected=None
    def list(self):
        return 'OK',[('('+' '.join(flags)+') "/" '+quote(name)).encode() for name,flags in self.roles.items()]
    def select(self,folder,readonly=True):
        self.selected=codec.unutf7(folder.strip('"'))
        return 'OK',[str(len(self.boxes[self.selected])).encode()]
    def response(self,name):
        return name,[str(self.validities[self.selected]).encode()]
    def uid(self,command,*args):
        box=self.boxes[self.selected]
        if command=='SEARCH':return 'OK',[b' '.join(str(uid).encode() for uid in box)]
        if command=='FETCH':
            uid,query=int(args[0]),args[1];raw=box[uid]
            meta=f'1 (UID {uid} FLAGS () RFC822.SIZE {len(raw)})'.encode()
            return 'OK',[(meta,raw)] if 'BODY.PEEK' in query else [meta]
        raise AssertionError(('Unexpected IMAP command in a read',command,args))


class FullDisk(storage_faults.OSWrites):
    """Every space-allocating file or SQLite write fails; closes still succeed."""
    FAILING={'write','create'}
    def hit(self,label,sqlite=False):
        if storage_faults.EXCLUDED:return 0
        self.points.append(label)
        if label.rsplit('.',1)[-1] in self.FAILING and not label.startswith(self.SPARED):
            self.failed=True;self.failures.append((len(self.points),label,'ENOSPC'))
            if sqlite:return 13  # SQLITE_FULL
            raise OSError(28,'Synthetic full disk at '+label)
        return 0
    SPARED=()


class FullMainDatabase(FullDisk):
    """Every page write to the main database fails while a store opens.

    Opening a connection passes a create flag whether the file exists or not, and
    the disposable journal index is rebuilt at every open, so those stay out of
    the fault; the CREATE INDEX on the existing main database is what fails.
    """
    FAILING={'write'}
    SPARED=('sqlite.index',)


class Recorded:
    """Delegates to the store's connection and keeps each statement it runs."""
    def __init__(self,db):self.db,self.statements=db,[]
    def execute(self,sql,parameters=()):
        self.statements.append((sql,list(parameters)))
        return self.db.execute(sql,parameters)
    def __getattr__(self,name):return getattr(self.db,name)


def retain(store,count,unfinished=True):
    # Completed history about the size of a real completed send (3-4 KB),
    # both apps, plus a few unfinished and legacy rows for the filters. Without
    # them the history is like the CI latency fixture's: every row completed.
    template=next(op for _,op in store.iter_items('op:'))
    template['payload']['retained_history']='Synthetic completed history; nothing submitted. '*70
    for first in range(0,count,48):
        changes={}
        for index in range(first,min(first+48,count)):
            op=copy.deepcopy(template)
            state='unknown' if unfinished and index%97==0 else 'done'
            op.update(id=op['generation']+':retained-'+str(index),app=('mail','chrome')[index%2],state=state)
            if index%193==0:op.pop('context_version',None)
            changes['op:'+op['id']]=op
        store.write(changes,'chrome_full_disk_fixture','Synthetic retained history; not acceptance')


class FullDiskReads(unittest.TestCase):
    def setUp(self):
        self.fixture=test_engine.Operations();self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.engine=self.fixture.engine;self.store=self.engine.store
        target=self.fixture.browser.facts['frames'][0]['target']
        target['name']=target['label']='Continue'
        self.assertTrue(self.fixture.call('click',self.fixture.target())['ok'])
        self.imap=ReadOnlyIMAP(40,b'<full-disk@mail.invalid>')
        mail=self.engine.adapters['mail']
        imap=self.imap
        class Session:
            def __enter__(self):return imap
            def __exit__(self,*exc):return False
        patcher=patch.object(mail.transport,'imap',lambda account:Session())
        patcher.start();self.addCleanup(patcher.stop)
        account={'id':'box','addresses':['owner@example.com'],'ready':True,'capabilities':list(imap.capabilities),
                 'smtp_capabilities':[],'sent_policy':'client','safe_folder_delete':True,'format':'plain','signature':'',
                 **resolve(folders(imap))}
        self.store.write({'mail:account:box':account},'fixture','Synthetic Mail account, test store only')
        self.retain()

    def retain(self):
        retain(self.store,RETAINED)
        self.assertGreaterEqual(sum(1 for _ in self.store.iter_items('op:')),RETAINED)

    def plans(self):
        result={}
        for shape in SHAPES:
            recorded=Recorded(self.store.db);original=self.store.db
            self.store.db=recorded
            try:rows=list(self.store.iter_operations(**shape))
            finally:self.store.db=original
            expected=[(k,v) for k,v in self.store.iter_items('op:') if
                      (shape['app'] is None or v.get('app')==shape['app']) and
                      (shape['exclude_app'] is None or v.get('app')!=shape['exclude_app'])]
            # The SQL filters only narrow candidates; callers re-check them.
            self.assertTrue(set(k for k,_ in expected)>=set(k for k,_ in rows),shape)
            self.assertEqual([k for k,_ in rows],sorted(k for k,_ in rows),shape)
            (sql,parameters),=[row for row in recorded.statements if row[0].startswith('SELECT k,v FROM kv')]
            plan=[row[-1] for row in original.execute('EXPLAIN QUERY PLAN '+sql,parameters)]
            result[repr(dict(sorted((k,v if not isinstance(v,set) else set(v)) for k,v in shape.items())))]=(plan,sql)
        return result

    def assert_key_order(self,stage):
        for shape,(plan,sql) in self.plans().items():
            with self.subTest(stage=stage,shape=shape):
                self.assertFalse([step for step in plan if 'TEMP B-TREE' in step],plan)
                index='operation_open' if selective(eval(shape)) else 'sqlite_autoindex_kv_1'
                self.assertEqual([step for step in plan if step.startswith('SEARCH kv USING INDEX '+index+' (k>? AND k<?)')],plan,plan)
                self.assertEqual(storage.OPEN_OPERATIONS in sql,selective(eval(shape)),sql)

    def test_every_operation_query_shape_reads_in_key_order_without_a_sort(self):
        self.assertEqual(len(SHAPES),48)
        self.assert_key_order('fresh')
        self.store.db.execute(OLD_INDEX);self.store.db.commit()
        self.assert_key_order('old index left behind')
        self.store.db.execute('ANALYZE');self.store.db.commit()
        self.assert_key_order('old index, analyzed')
        self.store.db.execute('DROP INDEX operation_headers');self.store.db.execute('ANALYZE');self.store.db.commit()
        self.assert_key_order('analyzed')

    def indexes(self,store=None):
        return {row[0]:row[1] for row in (store or self.store).db.execute("SELECT name,sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")}

    def test_store_creates_no_operation_header_index(self):
        names=self.indexes()
        self.assertNotIn('operation_headers',names)
        self.assertEqual(set(names),{'operation_open'})

    def test_the_index_where_and_every_selective_query_come_from_the_one_definition(self):
        # One constant is the partial index's WHERE and each selective shape's
        # extra term; the planner needs the two identical. It names exactly the
        # open states retention knows, so changing either side alone shows here.
        self.assertEqual(self.indexes()['operation_open'],storage.OPEN_INDEX)
        self.assertTrue(storage.OPEN_INDEX.endswith(" WHERE substr(k,1,3)='op:' AND "+storage.OPEN_OPERATIONS))
        self.assertEqual(storage.OPEN_OPERATIONS.count('json_extract(v,'),6)
        self.assertIn("'$.sent_copy_check.state')='open'",storage.OPEN_OPERATIONS)
        quoted=storage.OPEN_OPERATIONS.split(' IN (',1)[1].split(')',1)[0]
        self.assertEqual({name.strip("'") for name in quoted.split(',')},OPEN)
        for shape,(plan,sql) in self.plans().items():
            with self.subTest(shape=shape):
                self.assertEqual(sql.count(storage.OPEN_OPERATIONS),1 if selective(eval(shape)) else 0,sql)

    def in_index(self,key):
        # INDEXED BY refuses the query unless the index serves it, so this reads
        # the index itself, never the table.
        return bool(self.store.db.execute("SELECT 1 FROM kv INDEXED BY operation_open WHERE substr(k,1,3)='op:' AND "
                                          +storage.OPEN_OPERATIONS+" AND k=?",(key,)).fetchone())

    def test_an_operation_is_in_the_index_while_open_or_unacknowledged_and_leaves_it_after(self):
        template=next(op for _,op in self.store.iter_items('op:'))
        def put(label,**fields):
            op=copy.deepcopy(template);op.pop('notice',None);op.pop('ack',None)
            op.update(id=op['generation']+':'+label,**fields)
            key='op:'+op['id'];self.store.write({key:op},'chrome_full_disk_fixture','Synthetic membership row; no input');return key,op
        for state in sorted(OPEN):
            key,op=put('open-'+state,state=state);self.assertTrue(self.in_index(key),state)
            op['state']='done';self.store.write({key:op},'chrome_full_disk_fixture','Synthetic finish');self.assertFalse(self.in_index(key),state)
        key,op=put('notice',state='failed',notice=True,ack=False);self.assertTrue(self.in_index(key))
        op['ack']=True;self.store.write({key:op},'chrome_full_disk_fixture','Synthetic acknowledgement');self.assertFalse(self.in_index(key))
        key,_=put('done-no-notice',state='done');self.assertFalse(self.in_index(key))
        key,_=put('done-notice-missing-ack',state='done',notice=True);self.assertTrue(self.in_index(key))
        # Malformed state headers stay candidates, as the states filter keeps them.
        for label,state in [('number',7),('list',['reserved']),('object',{'state':'reserved'}),('null',None)]:
            key,_=put('malformed-'+label,state=state);self.assertTrue(self.in_index(key),label)
        key,_=put('text-closed',state='failed');self.assertFalse(self.in_index(key))
        key,op=put('sent-check',state='done',sent_copy_check={'state':'open'});self.assertTrue(self.in_index(key))
        op['sent_copy_check']={'state':'checked','count':1,'clean':True};self.store.write({key:op},'chrome_full_disk_fixture','Synthetic check');self.assertFalse(self.in_index(key))
        # Every row the index holds is one the selective shapes return, and the
        # per-request shapes return exactly their rows.
        indexed={k for k,in self.store.db.execute("SELECT k FROM kv INDEXED BY operation_open WHERE substr(k,1,3)='op:' AND "+storage.OPEN_OPERATIONS)}
        self.assertEqual({k for k,_ in self.store.iter_operations(unresolved=True)},indexed)
        rows=dict(self.store.iter_items('op:'))
        self.assertEqual({k for k,op in self.store.iter_operations(states=OPEN) if isinstance(op.get('state'),str) and op['state'] in OPEN},
                         {k for k,op in rows.items() if isinstance(op.get('state'),str) and op['state'] in OPEN})
        self.assertEqual({k for k,op in self.store.iter_operations(unresolved=True) if op.get('notice') and not op.get('ack')},
                         {k for k,op in rows.items() if op.get('notice') and not op.get('ack')})
        self.assertEqual({k for k,op in self.store.iter_operations(app='mail',unresolved=True) if op.get('sent_copy_check',{}).get('state')=='open'},
                         {k for k,op in rows.items() if op['app']=='mail' and op.get('sent_copy_check',{}).get('state')=='open'})

    def test_a_store_without_the_index_opens_and_reads_on_a_full_disk_and_gets_it_later(self):
        # A store an earlier build left without the index (or one that lost it)
        # opens on a full disk: the index can't be added, every shape still
        # answers the same rows in key order, and the next open with space adds it.
        state,evidence=self.store.state_dir,self.store.evidence_dir
        expected={repr(shape):list(self.store.iter_operations(**shape)) for shape in SHAPES}
        self.store.db.execute('DROP INDEX operation_open');self.store.db.commit()
        self.engine.close()
        disk=FullMainDatabase()
        with disk.wrap():
            try:reopened=storage.Store(state,evidence)
            except Exception as exc:self.fail('A store without the index must open on a full disk: %r'%(exc,))
        try:
            self.assertNotIn('operation_open',self.indexes(reopened))
            self.assertIn('sqlite.main.write',[label for _,label,_ in disk.failures])
            self.assertIsNotNone(reopened.observations.error)
            for shape in SHAPES:
                with self.subTest(shape=shape):
                    recorded=Recorded(reopened.db);reopened.db=recorded
                    try:rows=list(reopened.iter_operations(**shape))
                    finally:reopened.db=recorded.db
                    self.assertEqual(rows,expected[repr(shape)])
                    (sql,parameters),=[row for row in recorded.statements if row[0].startswith('SELECT k,v FROM kv')]
                    plan=[row[-1] for row in reopened.db.execute('EXPLAIN QUERY PLAN '+sql,parameters)]
                    self.assertEqual(plan,['SEARCH kv USING INDEX sqlite_autoindex_kv_1 (k>? AND k<?)'],plan)
        finally:reopened.close()
        reopened=storage.Store(state,evidence)
        try:
            self.assertEqual(self.indexes(reopened).get('operation_open'),storage.OPEN_INDEX)
            self.assertIsNone(reopened.observations.error)
            for shape in SHAPES:self.assertEqual(list(reopened.iter_operations(**shape)),expected[repr(shape)],shape)
        finally:reopened.close()

    def test_the_index_is_added_after_recovery_and_spends_only_unheld_space(self):
        # Fixes b, G4.1: optional speed indexes may spend only unheld space,
        # after every prepared recovery and reservation has been rebuilt. The
        # index's admission must see a reservation's held cancellation space.
        template=next(op for _,op in self.store.iter_items('op:'))
        op=copy.deepcopy(template);op.pop('notice',None);op.pop('ack',None);op.update(id=op['generation']+':held',state='reserved')
        self.store.write({'op:'+op['id']:op},'chrome_full_disk_fixture','Synthetic reservation; no input')
        state,evidence=self.store.state_dir,self.store.evidence_dir
        self.store.db.execute('DROP INDEX operation_open');self.store.db.commit()
        self.engine.close()
        seen=[];original=storage.Store._index_open_operations
        def spy(store):
            seen.append(dict(store.ledger.holds));return original(store)
        with patch.object(storage.Store,'_index_open_operations',spy):
            reopened=storage.Store(state,evidence)
        try:
            self.assertEqual(len(seen),1)
            self.assertIn('cancel:'+op['id'],seen[0],'the reservation is held before the index admits its cost')
            self.assertEqual(seen[0],reopened.ledger.holds,'nothing reconstructed after the index changes the holds')
            self.assertEqual(self.indexes(reopened).get('operation_open'),storage.OPEN_INDEX)
        finally:reopened.close()

    def test_an_index_from_another_definition_is_replaced_at_open_and_a_full_disk_only_defers_it(self):
        # Fixes b, G4.2: the index is known by its whole definition. One built
        # from an older OPEN_OPERATIONS no longer matches the queries' term, so
        # the planner skips it and every selective shape walks the history. The
        # next open replaces it; on a full disk the store still opens and reads
        # the same rows, and the open after that replaces it.
        state,evidence=self.store.state_dir,self.store.evidence_dir
        expected={repr(shape):list(self.store.iter_operations(**shape)) for shape in SHAPES}
        older=storage.OPEN_INDEX.replace("'$.sent_copy_check.state')='open'","'$.sent_copy_check.state')='pending'")
        self.assertNotEqual(older,storage.OPEN_INDEX)
        self.store.db.execute('DROP INDEX operation_open');self.store.db.execute(older);self.store.db.commit()
        stale=[shape for shape,(plan,sql) in self.plans().items() if selective(eval(shape)) and any('operation_open' in step for step in plan)]
        self.assertEqual(stale,[],'the planner skips an index whose WHERE the queries no longer carry')
        self.engine.close()
        disk=FullMainDatabase()
        with disk.wrap():
            try:reopened=storage.Store(state,evidence)
            except Exception as exc:self.fail('A store with an older index must open on a full disk: %r'%(exc,))
        try:
            self.assertEqual(self.indexes(reopened).get('operation_open'),older,'a full disk leaves the old index in place')
            self.assertIn('sqlite.main.write',[label for _,label,_ in disk.failures])
            self.assertIsNotNone(reopened.observations.error)
            for shape in SHAPES:self.assertEqual(list(reopened.iter_operations(**shape)),expected[repr(shape)],shape)
        finally:reopened.close()
        reopened=storage.Store(state,evidence)
        try:
            self.assertEqual(self.indexes(reopened).get('operation_open'),storage.OPEN_INDEX)
            self.assertIsNone(reopened.observations.error)
            self.store=reopened;self.assert_key_order('replaced at open')
            for shape in SHAPES:self.assertEqual(list(reopened.iter_operations(**shape)),expected[repr(shape)],shape)
        finally:reopened.close()

    def test_a_rebuild_that_fails_after_its_drop_keeps_the_old_index(self):
        # The security re-check of fixes b: Python's sqlite3 opens no
        # transaction before DDL, so a DROP on its own commits at once. When the
        # CREATE after it then fails (a nearly full disk: the DROP frees pages,
        # the build needs more), the store would have no index until the next
        # open. Drop and rebuild are one transaction, so the old index stays.
        import sqlite3
        expected={repr(shape):list(self.store.iter_operations(**shape)) for shape in SHAPES}
        older=storage.OPEN_INDEX.replace("'$.sent_copy_check.state')='open'","'$.sent_copy_check.state')='pending'")
        self.assertNotEqual(older,storage.OPEN_INDEX)
        self.store.db.execute('DROP INDEX operation_open');self.store.db.execute(older);self.store.db.commit()
        class FullAtCreate(Recorded):
            def execute(self,sql,parameters=()):
                if sql==storage.OPEN_INDEX:
                    self.statements.append((sql,list(parameters)))
                    error=sqlite3.OperationalError('database or disk is full');error.sqlite_errorcode=sqlite3.SQLITE_FULL
                    raise error
                return super().execute(sql,parameters)
        connection=self.store.db;self.store.db=FullAtCreate(connection)
        try:self.store._index_open_operations()
        finally:statements=[sql for sql,_ in self.store.db.statements];self.store.db=connection
        self.assertEqual(statements[-2:],['DROP INDEX operation_open',storage.OPEN_INDEX],'the drop ran and the rebuild failed')
        self.assertFalse(connection.in_transaction)
        self.assertEqual(self.indexes().get('operation_open'),older,'a failed rebuild keeps the old index')
        self.assertIsNotNone(self.store.observations.error)
        for shape in SHAPES:self.assertEqual(list(self.store.iter_operations(**shape)),expected[repr(shape)],shape)
        self.store._index_open_operations()
        self.assertEqual(self.indexes().get('operation_open'),storage.OPEN_INDEX,'the next try replaces it')

    def request(self,action,arguments):
        return self.engine.request({'v':1,'method':'call','action':action,'arguments':arguments})

    def test_a_chrome_request_and_the_expiry_sweep_run_no_broad_operation_scan(self):
        # Every operation query on a Chrome request's path (_pending and the
        # notice rows behind it, _expire, retention.expire) carries the index
        # term: a read, a reservation and the expiry sweep never walk the whole
        # history. (control_pending still does, on purpose: resolving Mail's
        # sent-copy checks reads every Mail send, as on main.)
        recorded=Recorded(self.store.db);original=self.store.db;self.store.db=recorded
        try:
            self.assertTrue(self.fixture.call('read',{'tab':1})['ok'])
            self.assertTrue(self.engine.pending(resolve_checks=False))
            self.engine.expire()
        finally:self.store.db=original
        scans=[sql for sql,parameters in recorded.statements if sql.startswith('SELECT k,v FROM kv WHERE k>=')
               and (sql.startswith("SELECT k,v FROM kv WHERE k>='op:'") or parameters[:1]==['op:'])]
        self.assertGreaterEqual(len(scans),3)
        self.assertEqual([sql for sql in scans if storage.OPEN_OPERATIONS not in sql],[])

    def test_mail_read_search_and_pending_answer_on_a_full_disk_with_retained_history(self):
        reference={'account':'box','folder':'Source','uidvalidity':self.imap.validities['Source'],'uid':1,'message_id':self.imap.mid}
        calls=[('mail_read',{'reference':reference}),
               ('mail_search',{'account':'box','folders':['Source'],'limit':20}),
               ('control_pending',{})]
        expected={action:self.request(action,arguments) for action,arguments in calls}
        for action,result in expected.items():self.assertTrue(result['ok'],(action,result))
        for action,arguments in calls:
            with self.subTest(action=action):
                disk=FullDisk()
                with disk.wrap(self.store):
                    result=self.request(action,arguments)
                self.store.write_failed=False
                self.assertTrue(result['ok'],(action,result.get('error'),disk.failures[:1]))
                self.assertEqual(disk.failures,[],'A read needed disk space')
                self.assertEqual(result['data'],expected[action]['data'])
