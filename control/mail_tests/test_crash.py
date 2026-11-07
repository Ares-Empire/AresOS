import json
from contextlib import closing
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from unittest.mock import patch

from support import MailCase, WORK
from smtp_fixture import SMTPFixture
from aresos_control.engine import Engine
from aresos_control.mail.transport import folders, select, uids

WORKER = Path(__file__).with_name('crash_worker.py')


class MailCrashes(MailCase):
    def restart(self):
        self.engine.close()
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        self.mail = self.engine.adapters['mail']

    def crash_case(self, action, checkpoint, occurrence=1, smtp=None):
        actual_action = {"mail_send_reply":"mail_send", "mail_delete_trash":"mail_delete"}.get(action,action)
        # Separate state/evidence per crash; only the fixture mailbox persists externally.
        with tempfile.TemporaryDirectory(dir=WORK) as directory:
            root = Path(directory)
            engine = Engine(root / 'state', root / 'independent')
            engine.adapters['mail'].transport.store_password('box','pass')
            account = dict(self.account)
            if smtp:
                account.update(smtp_host='localhost',smtp_port=smtp.port)
            engine.store.write({'mail:account:box':account},'fixture','synthetic crash account')
            adapter = engine.adapters['mail']
            if action in {'mail_send','mail_send_reply','mail_operation_repair','mail_prepare_send'}:
                comp_args = {'account':'box','to':['one@mail.invalid'],'text':'Crash fixture'}
                if action == 'mail_send_reply':
                    original = self.fixture()
                    comp_args = {'account':'box','mode':'reply','reference':original,'text':'Reply crash'}
                comp = adapter.compose(comp_args)
                approval = {k:comp[k] for k in ('composition_id','composition_hash')} if action == 'mail_prepare_send' else engine.reserve('mail','send',comp)['approval']
                if action == 'mail_operation_repair':
                    saved = adapter.local_stage
                    def fail_sent(op,which):
                        if which == 'sent_copy':
                            from aresos_control.common import Refused
                            raise Refused('stage_missing','Before APPEND')
                        return saved(op,which)
                    with patch.object(adapter,'local_stage',side_effect=fail_sent):
                        result = engine.request({'v':1,'method':'call','action':'mail_send','arguments':approval})
                    self.assertEqual(result['data']['operation']['state'],'partial')
                    approval = {'operation_id':approval['operation_id'],'stage':'sent_copy'}
                if action == 'mail_prepare_send':
                    approval = {k:comp[k] for k in ('composition_id','composition_hash')}
                ref = None
            else:
                # Two named targets plus an unnamed Deleted message exercise every mutation stage.
                refs = [self.fixture(subject='Crash target '+str(i)) for i in range(2)]
                ref = self.fixture(subject='Unnamed survives',flags='(\\Deleted)')
                verb = 'delete'
                approval = engine.reserve('mail',verb,{'items':[adapter.named_item(r) for r in refs],'mode':'trash' if action == 'mail_delete_trash' else 'permanent'})['approval']
            if checkpoint in {'first_marked','first_expunged','first_moved'}:
                checkpoint = {'first_marked':'mail_marked:', 'first_expunged':'mail_expunged:', 'first_moved':'mail_moved:'}[checkpoint] + str(refs[0]['uid'])
            engine.close()
            (root / 'crash.json').write_text(json.dumps({'action':actual_action,'approval':approval,'checkpoint':checkpoint,'occurrence':occurrence}))
            before = len(smtp.arrivals()) if smtp else 0
            child = subprocess.run([sys.executable,str(WORKER),str(root)],capture_output=True,text=True,timeout=30)
            self.assertIn(child.returncode,(0,-9),child.stderr + child.stdout)
            engine = Engine(root / 'state',root / 'independent')
            try:
                if engine.store.locked:
                    self.assertFalse(engine.request({'v':1,'method':'call','action':'mail_accounts','arguments':{}})['ok'])
                    engine.store.confirm_restore()
                if action == 'mail_prepare_send':
                    self.assertEqual(len(smtp.arrivals()),before)
                    self.assertTrue(all(op['state'] in {'reserved','unknown'} for _,op in engine.store.items('op:')))
                    return child.returncode == -9, None
                op = engine.operation(approval['operation_id'])
                # Startup never runs app transports. Explicit replay may run only a still-reserved id once.
                after_restart = len(smtp.arrivals()) if smtp else 0
                self.assertLessEqual(after_restart-before,1)
                reply = engine.request({'v':1,'method':'call','action':actual_action,'arguments':approval})
                engine.request({'v':1,'method':'call','action':actual_action,'arguments':approval})
                if smtp:
                    self.assertLessEqual(len(smtp.arrivals())-before,1)
                elif ref is not None:
                    self.assertEqual(engine.adapters['mail'].message(ref)['reference'],ref)
                if action == 'mail_operation_repair':
                    self.assertLessEqual(len(engine.adapters['mail'].sent_matches(account,adapter.message_id(approval['operation_id']))),1)
                if op['state'] != 'reserved':
                    self.assertEqual(len(smtp.arrivals()) if smtp else 0,after_restart)
                self.assertTrue(reply['ok'] or reply['error']['code'] in {'refused','stale_reference'},reply)
                return child.returncode == -9, json.loads(child.stdout)['counts'] if child.returncode == 0 else None
            finally:
                engine.close()

    def test_kill_every_send_log_write_and_every_remote_stage_never_sends_twice(self):
        cases = 0
        with SMTPFixture(self.root) as smtp:
            for checkpoint in ('journal_appended','sqlite_prepared','sqlite_committed','journal_committed'):
                for occurrence in range(1,35):
                    killed, counts = self.crash_case('mail_send',checkpoint,occurrence,smtp)
                    if not killed:
                        self.assertEqual(counts.get(checkpoint,0),occurrence-1)
                        break
                    cases += 1
                else:
                    self.fail('Crash coverage did not reach the final write')
            for checkpoint in ('submitting','smtp_answer','mail_sent_copy','before_outcome','outcome'):
                killed,_ = self.crash_case('mail_send',checkpoint,1,smtp)
                self.assertTrue(killed,checkpoint)
                cases += 1
        print(f'Mail send kill-9 cases: {cases}; no repeated SMTP DATA')

    def test_kill_every_delete_log_write_and_each_uid_stage_preserves_unnamed(self):
        cases = 0
        for checkpoint in ('journal_appended','sqlite_prepared','sqlite_committed','journal_committed'):
            for occurrence in range(1,20):
                killed,counts = self.crash_case('mail_delete',checkpoint,occurrence)
                if not killed:
                    self.assertEqual(counts.get(checkpoint,0),occurrence-1)
                    break
                cases += 1
            else:
                self.fail('Delete crash coverage missed final write')
        for checkpoint in ('first_marked','first_expunged'):
            killed,_ = self.crash_case('mail_delete',checkpoint)
            self.assertTrue(killed,checkpoint)
            cases += 1
        print(f'Mail delete kill-9 cases: {cases}; unnamed Deleted messages survive')

    def test_trash_move_and_answered_flag_crashes_never_repeat_remote_work(self):
        killed,_ = self.crash_case('mail_delete_trash','first_moved')
        self.assertTrue(killed)
        with SMTPFixture(self.root) as smtp:
            killed,_ = self.crash_case('mail_send_reply','mail_answered_flag',smtp=smtp)
            self.assertTrue(killed)
            self.assertEqual(len(smtp.arrivals()),1)

    def test_reservation_and_every_repair_write_crashes_never_submit_again(self):
        cases = 0
        with SMTPFixture(self.root) as smtp:
            for checkpoint in ('journal_appended','sqlite_prepared','sqlite_committed','journal_committed'):
                killed,_ = self.crash_case('mail_prepare_send',checkpoint,smtp=smtp)
                self.assertTrue(killed)
                cases += 1
                for occurrence in range(1,10):
                    killed,counts = self.crash_case('mail_operation_repair',checkpoint,occurrence,smtp)
                    if not killed:
                        self.assertEqual(counts.get(checkpoint,0),occurrence-1)
                        break
                    cases += 1
                else:
                    self.fail('Repair coverage missed final write')
        print(f'Mail reservation/repair kill-9 cases: {cases}; no SMTP during repair/restart')

    def test_restore_older_sqlite_keeps_lock_until_owner_confirms_and_rejects_old_approval(self):
        with SMTPFixture(self.root) as smtp:
            account = {**self.account,'smtp_host':'localhost','smtp_port':smtp.port}
            self.engine.store.write({'mail:account:box':account},'fixture','SMTP')
            backup = self.root / 'older.sqlite'
            with closing(sqlite3.connect(backup)) as db:
                self.engine.store.db.backup(db)
            approval = self.approval()
            result = self.send(approval)
            self.assertEqual(result['state'],'done',result)
            self.engine.close()
            shutil.copyfile(backup,self.root / 'state/control.sqlite')
            self.engine = Engine(self.root / 'state',self.root / 'independent')
            self.mail = self.engine.adapters['mail']
            self.assertTrue(self.engine.store.locked)
            self.assertFalse(self.call('accounts')['ok'])
            self.assertFalse(self.call('send',approval)['ok'])
            self.engine.store.confirm_restore()
            status = self.data('operation_status',{'operation_id':result['id']})['operation']
            self.assertEqual(status['state'],'unknown')
            self.assertEqual(status['approval']['description']['to'],['one@mail.invalid'])
            self.assertFalse(self.call('send',approval)['ok'])
            self.assertEqual(len(smtp.arrivals()),1)
