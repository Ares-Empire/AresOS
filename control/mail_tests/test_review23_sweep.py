"""Automatically discover and fail every durable write in each approved flow."""
from collections import Counter
from contextlib import closing, contextmanager, ExitStack
import copy
import errno
import json
import os
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from aresos_control.engine import Engine
import test_review_fixes_23 as results23


class DurableWrites:
    """Journal writes/syncs, private-file writes/syncs, and real SQLite commits."""
    def __init__(self, fail_at=None):
        self.fail_at = fail_at
        self.points = []
        self.failed = False

    def hit(self, label):
        self.points.append(label)
        if len(self.points) == self.fail_at:
            self.failed = True
            raise OSError(errno.ENOSPC, 'Synthetic full disk at ' + label)

    @contextmanager
    def wrap(self, store):
        db, journal_write, fsync, fdopen = store.db, store.journal.write, os.fsync, os.fdopen
        sweep = self
        class Database:
            def __getattr__(self, name):
                return getattr(db, name)
            def __enter__(self):
                db.__enter__()
                return self
            def __exit__(self, kind, value, trace):
                if kind is None:
                    try:
                        sweep.hit('sqlite.commit')
                    except OSError as exc:
                        db.__exit__(type(exc), exc, exc.__traceback__)
                        raise
                return db.__exit__(kind, value, trace)
            def commit(self):
                sweep.hit('sqlite.commit')
                return db.commit()
        class Writer:
            def __init__(self, stream):
                self.stream = stream
            def __getattr__(self, name):
                return getattr(self.stream, name)
            def write(self, data):
                sweep.hit('private.write')
                return self.stream.write(data)
        def journal(data):
            sweep.hit('journal.commit' if 'commit' in json.loads(data) else 'journal.record')
            return journal_write(data)
        def sync(fd):
            sweep.hit('journal.sync' if fd == store.journal.fileno() else 'private.sync')
            return fsync(fd)
        @contextmanager
        def opened(fd, mode, *args, **kwargs):
            with fdopen(fd, mode, *args, **kwargs) as stream:
                yield Writer(stream) if mode in {'w', 'wb'} else stream
        with patch.object(store, 'db', Database()), patch.object(store.journal, 'write', side_effect=journal), \
             patch('os.fsync', side_effect=sync), patch('os.fdopen', side_effect=opened):
            yield


class Scenario:
    def __init__(self, flow):
        self.fixture = f = results23.Results23()
        f.setUp()
        self.stack = ExitStack()
        self.flow, self.remote = flow, Counter()
        self.stages, self.copies = {}, {}
        self.install_remote()
        self.approval = None
        self.admin = False
        if flow in {'send', 'cancel', 'restore'}:
            if flow == 'restore':
                with closing(sqlite3.connect(f.root / 'backup.sqlite')) as backup:
                    f.engine.store.db.backup(backup)
            self.approval = f.approval('send', f.compose())
            self.operation_id = self.approval['operation_id']
            self.action, self.args = 'mail_send', self.approval
            if flow == 'cancel':
                self.action, self.args = 'mail_operation_cancel', {'operation_id': self.operation_id}
            elif flow == 'restore':
                f.engine.close()
                (f.root / 'state/control.sqlite').write_bytes((f.root / 'backup.sqlite').read_bytes())
                self.bind(Engine(f.root / 'state', f.root / 'evidence'))
                f.assertTrue(f.engine.store.locked)
                self.action, self.args, self.admin = 'control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, True
        elif flow in {'repair', 'status', 'settlement'}:
            if flow == 'settlement':
                old, args, repair, raw, ended = f.pending_append()
            else:
                old = f.send('sent_copy' if flow == 'repair' else None)
                args = {'operation_id': old['id'], 'stage': 'sent_copy'}
                raw = f.mail.wires.read(old['stages']['wire_sha256'])
            self.operation_id = old['id']
            self.action, self.args = 'mail_operation_repair', args
            if flow in {'status', 'settlement'}:
                f.imap.boxes['Sent'].update({1: raw, 2: raw})
            if flow == 'status':
                self.action, self.args = 'mail_operation_status', {'operation_id': old['id']}
        elif flow.startswith('delete_'):
            items = [f.mail.named_item({'account': 'box', 'folder': 'Source', 'uidvalidity': f.imap.validities['Source'],
                                       'uid': uid, 'message_id': f.imap.mid}) for uid in (1, 2)]
            self.approval = f.approval('delete', {'items': items, 'mode': flow.removeprefix('delete_')})
            self.operation_id = self.approval['operation_id']
            self.action, self.args = 'mail_delete', self.approval
        else:
            target = 'mailto:unsubscribe@mail.invalid?subject=Stop&body=Exact' if flow == 'unsubscribe_mailto' else 'https://unsubscribe.mail.invalid/stop'
            raw = f.imap.raw.replace(b'\r\n\r\n', ('\r\nList-Unsubscribe: <' + target + '>\r\nList-Unsubscribe-Post: List-Unsubscribe=One-Click\r\n\r\n').encode())
            f.imap.boxes['Source'][1] = raw
            reference = {'account': 'box', 'folder': 'Source', 'uidvalidity': f.imap.validities['Source'], 'uid': 1, 'message_id': f.imap.mid}
            self.approval = f.approval('unsubscribe', {'reference': reference, 'target': target})
            self.operation_id = self.approval['operation_id']
            self.action, self.args = 'mail_unsubscribe', self.approval
        self.remote.clear()

    def install_remote(self):
        f, remote = self.fixture, self.remote
        class SMTP:
            def has_extn(self, _):
                return False
            def mail(self, *args, **kwargs):
                return 250, b'Synthetic sender accepted'
            def rcpt(self, _):
                return 250, b'Synthetic recipient accepted'
            def data(self, raw):
                remote['DATA'] += 1
                return 250, b'Synthetic DATA accepted'
        @contextmanager
        def smtp(account):
            yield SMTP()
        def append(account, folder, raw, flags):
            remote['APPEND'] += 1
            # The new APPEND and a delayed earlier copy become visible together.
            f.imap.boxes[folder].update({1: raw, 2: raw})
            self.stages.setdefault(self.operation_id, {})['sent_copy'] = 'done'
            return {'uid': 2}
        class HTTPS:
            def __init__(self, *args, **kwargs):
                pass
            def request(self, method, *args, **kwargs):
                f.assertEqual(method, 'POST')
                remote['POST'] += 1
            def getresponse(self):
                return SimpleNamespace(status=200)
            def close(self):
                pass
        original_uid = f.imap.uid
        flags = {('Source', 7): {'\\Deleted'}}
        def uid(command, *args):
            box, number = f.imap.selected, int(args[0]) if command != 'SEARCH' else None
            if command in {'MOVE', 'STORE', 'EXPUNGE'}:
                remote[command + ':' + str(number)] += 1
                if command == 'MOVE':
                    f.imap.boxes['Trash'][number] = f.imap.boxes[box].pop(number)
                elif command == 'EXPUNGE':
                    f.imap.boxes[box].pop(number)
                else:
                    flags.setdefault((box, number), set()).add(args[2].strip('()'))
                return 'OK', [b'Synthetic mutation']
            answer = original_uid(command, *args)
            if command == 'FETCH' and flags.get((box, number)):
                encoded = ' '.join(sorted(flags[(box, number)])).encode()
                answer = (answer[0], [(row[0].replace(b'FLAGS ()', b'FLAGS (' + encoded + b')'), row[1])
                                      if isinstance(row, tuple) else row.replace(b'FLAGS ()', b'FLAGS (' + encoded + b')') for row in answer[1]])
            return answer
        self.stack.enter_context(patch.object(f.mail.transport, 'smtp', side_effect=smtp))
        self.stack.enter_context(patch.object(f.mail, 'append', side_effect=append))
        self.stack.enter_context(patch.object(f.imap, 'uid', side_effect=uid))
        self.stack.enter_context(patch('aresos_control.mail.adapter.http.client.HTTPSConnection', HTTPS))
        self.stack.enter_context(patch('aresos_control.mail.dkim.verify_one_click', return_value={'domain': 'mail.invalid'}))

    def bind(self, engine):
        f = self.fixture
        f.engine = engine
        f.mail.store, f.mail.blobs = engine.store, engine.blobs
        f.mail.wires = engine.adapters['mail'].wires
        f.mail.transport.ledger = engine.store.ledger
        f.mail.check_result = engine.check_composition_result
        engine.adapters['mail'] = f.mail

    def call(self):
        return self.fixture.engine.request({'v': 1, 'method': 'call', 'action': self.action, 'arguments': self.args}, self.admin)

    @contextmanager
    def observed(self):
        f = self.fixture
        stage, observation = f.engine.stage, f.mail.sent_observation
        def seen_stage(operation_id, name, outcome):
            self.stages.setdefault(operation_id, {})[name] = outcome
            return stage(operation_id, name, outcome)
        def seen_copies(op, matches):
            copies = self.copies.setdefault(op['id'], [])
            copies.extend(copy.deepcopy(item) for item in matches if item not in copies)
            return observation(op, matches)
        with patch.object(f.engine, 'stage', side_effect=seen_stage), patch.object(f.mail, 'sent_observation', side_effect=seen_copies):
            yield

    def recover(self):
        f = self.fixture
        remote = self.remote.copy()
        f.engine.close()
        self.bind(Engine(f.root / 'state', f.root / 'evidence'))
        if f.engine.store.locked:
            result = f.engine.request({'v': 1, 'method': 'call', 'action': 'control_restore_confirm',
                                      'arguments': {'confirm': 'invalidate earlier approvals'}}, admin=True)
            f.assertTrue(result['ok'], result)
        status = f.data('operation_status', {'operation_id': self.operation_id})
        op = f.engine.operation(self.operation_id)
        f.assertEqual(status['operation']['state'], op['state'])
        f.assertEqual(status['operation']['stages'], op['stages'])
        f.assertEqual(f.engine.store.committed, f.engine.store.sequence)
        f.assertFalse(f.engine.store.write_failed)
        if op.get('payload', {}).get('composition'):
            f.assertEqual(status['evidence']['sent'], f.mail.sent_matches(f.account, f.mail.message_id(self.operation_id)))
        if self.approval and op['state'] != 'reserved':
            self.call()
        if self.flow in {'repair', 'settlement'} and f.imap.boxes['Sent']:
            f.call('operation_repair', self.args)
        f.assertEqual(self.remote, remote, 'Restart/status/replay must never repeat remote work')
        f.assertTrue(all(count <= 1 for count in remote.values()), remote)
        f.assertIn(7, f.imap.boxes['Source'], 'Unnamed Deleted mail must survive')

    def close(self):
        self.stack.close()
        self.fixture.doCleanups()


class FaultSweep23(unittest.TestCase):
    def test_review23_enospc_at_every_discovered_durable_write(self):
        flows = ('send', 'repair', 'delete_trash', 'delete_permanent', 'unsubscribe_mailto', 'unsubscribe_https',
                 'status', 'settlement', 'cancel', 'restore')
        for flow in flows:
            clean = Scenario(flow)
            try:
                sweep = DurableWrites()
                with clean.observed(), sweep.wrap(clean.fixture.engine.store):
                    result = clean.call()
                self.assertTrue(result['ok'], result)
                points = sweep.points
                self.assertGreater(len(points), 0, flow)
                clean.recover()
            finally:
                clean.close()
            print(f'Review23 durable write points: {flow}={len(points)} {dict(Counter(points))}', flush=True)
            for number, label in enumerate(points, 1):
                with self.subTest(flow=flow, point=number, label=label):
                    scenario = Scenario(flow)
                    try:
                        sweep = DurableWrites(number)
                        with scenario.observed(), sweep.wrap(scenario.fixture.engine.store):
                            result = scenario.call()
                        self.assertTrue(sweep.failed, sweep.points)
                        self.assertEqual(sweep.points[:number], points[:number])
                        self.assertFalse(result['ok'], result)
                        self.assertEqual(result['error']['code'], 'storage_limit', result)
                        self.assertIn('Disk full', result['error']['message'])
                        observed = result.get('observations', {})
                        for operation_id, stages in scenario.stages.items():
                            for name, outcome in stages.items():
                                self.assertEqual(observed['stages'][operation_id][name], outcome)
                        for operation_id, copies in scenario.copies.items():
                            self.assertEqual(observed['evidence'][operation_id]['sent'], copies)
                            if len(copies) > 1:
                                self.assertIn('2 copies', observed['evidence'][operation_id]['sent_copy_warning'])
                        scenario.recover()
                    finally:
                        scenario.close()
