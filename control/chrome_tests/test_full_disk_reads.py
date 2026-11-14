"""Retained history never makes a read need disk space (final fixes, F1).

Every iter_operations shape reads the primary-key range in key order. A sort in
a temporary B-tree spills to a temporary file once a few hundred operations are
retained; on a full disk that spill made Mail read, search and control_pending
return storage_limit, where main answers.
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
from aresos_control.mail import codec
from aresos_control.mail.roles import resolve
from aresos_control.mail.transport import folders, quote
from aresos_control.retention import OPEN

RETAINED=1200
# Every combination of iter_operations' filters, including the unfiltered walk.
SHAPES=[dict(app=app,exclude_app=exclude,legacy_open=legacy,states=states)
        for app,exclude,legacy,states in itertools.product([None,'mail'],[None,'chrome'],[False,True],[None,OPEN])]
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
    def hit(self,label,sqlite=False):
        if storage_faults.EXCLUDED:return 0
        self.points.append(label)
        if label.rsplit('.',1)[-1] in {'write','create'}:
            self.failed=True;self.failures.append((len(self.points),label,'ENOSPC'))
            if sqlite:return 13  # SQLITE_FULL
            raise OSError(28,'Synthetic full disk at '+label)
        return 0


class Recorded:
    """Delegates to the store's connection and keeps each statement it runs."""
    def __init__(self,db):self.db,self.statements=db,[]
    def execute(self,sql,parameters=()):
        self.statements.append((sql,list(parameters)))
        return self.db.execute(sql,parameters)
    def __getattr__(self,name):return getattr(self.db,name)


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
        # Completed history about the size of a real completed send (3-4 KB),
        # both apps, plus a few unfinished and legacy rows for the filters.
        template=next(op for _,op in self.store.iter_items('op:'))
        template['payload']['retained_history']='Synthetic completed history; nothing submitted. '*70
        for first in range(0,RETAINED,48):
            changes={}
            for index in range(first,min(first+48,RETAINED)):
                op=copy.deepcopy(template)
                state='unknown' if index%97==0 else 'done'
                op.update(id=op['generation']+':retained-'+str(index),app=('mail','chrome')[index%2],state=state)
                if index%193==0:op.pop('context_version',None)
                changes['op:'+op['id']]=op
            self.store.write(changes,'chrome_full_disk_fixture','Synthetic retained history; not acceptance')
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
            result[repr(sorted((k,v if not isinstance(v,set) else sorted(v)) for k,v in shape.items()))]=plan
        return result

    def assert_key_order(self,stage):
        for shape,plan in self.plans().items():
            with self.subTest(stage=stage,shape=shape):
                self.assertFalse([step for step in plan if 'TEMP B-TREE' in step],plan)
                self.assertTrue([step for step in plan if 'sqlite_autoindex_kv_1' in step],plan)

    def test_every_operation_query_shape_reads_in_key_order_without_a_sort(self):
        self.assertEqual(len(SHAPES),16)
        self.assert_key_order('fresh')
        self.store.db.execute(OLD_INDEX);self.store.db.commit()
        self.assert_key_order('old index left behind')
        self.store.db.execute('ANALYZE');self.store.db.commit()
        self.assert_key_order('old index, analyzed')
        self.store.db.execute('DROP INDEX operation_headers');self.store.db.execute('ANALYZE');self.store.db.commit()
        self.assert_key_order('analyzed')

    def test_store_creates_no_operation_header_index(self):
        names={row[0] for row in self.store.db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        self.assertNotIn('operation_headers',names)

    def request(self,action,arguments):
        return self.engine.request({'v':1,'method':'call','action':action,'arguments':arguments})

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
