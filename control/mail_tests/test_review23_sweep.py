"""Automatically discover and fail every durable write in each approved flow."""
from collections import Counter
from contextlib import closing, contextmanager, ExitStack
from itertools import islice
import copy
import errno
import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from aresos_control.engine import Engine
from aresos_control.common import Refused, sha256, storage_refusal
from aresos_control.proxy import Proxy
from response_checks import transport_response
import test_review_fixes_23 as results23


from storage_faults import OSWrites as DurableWrites


class Scenario:
    def __init__(self, flow):
        self.fixture_clock = ExitStack()
        if type(self) is Scenario and flow == 'archive':
            from owner_state_oracle.identity import scripted_ids
            from owner_state_oracle.clock import scripted_calendar
            self.archive_time = 1794225600.0
            self.fixture_clock.enter_context(patch('time.time', side_effect=lambda: self.archive_time))
            self.fixture_clock.enter_context(scripted_calendar())
            self.fixture_clock.enter_context(scripted_ids('inherited-archive'))
        try:
            self._prepare_fixture(flow)
        except BaseException:
            self.fixture_clock.close()
            raise

    def advance_archive_clock(self):
        self.archive_time += 2

    def _prepare_fixture(self, flow):
        self.fixture = f = results23.Results23()
        f.setUp()
        self.stack = ExitStack()
        self.flow, self.remote = flow, Counter()
        self.prior_commands, self.attempted_ids = Counter(), set()
        self.replay_requests = {}
        self.delivered = []
        self.stages, self.copies = {}, {}
        self.install_remote()
        self.approval = None
        self.operation_id = None
        self.admin = False
        if flow == 'fixture':
            self.action, self.args = 'mail_accounts', {}
        elif flow in {'send', 'send_duplicate', 'cancel', 'restore'}:
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
                old = self.seed_send('sent_copy')
                args = {'operation_id': old['id'], 'stage': 'sent_copy'}
                pending = []
                def pending_append(account, folder, raw, flags):
                    self.prior_commands['APPEND'] += 1
                    pending.append(raw)
                    raise OSError('Synthetic timeout after APPEND attempt')
                with patch.object(f.mail, 'append', side_effect=pending_append):
                    repair = f.data('operation_repair', args)['operation']
                self.attempted_ids.add(repair['id'])
                raw = pending[0]
            else:
                old = self.seed_send('sent_copy' if flow == 'repair' else None)
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
        elif flow in {'filing_move', 'filing_copy', 'filing_rename'}:
            self.stack.close()
            self.stack = ExitStack()
            original = f.imap.uid
            def filed(command, *args):
                if command in {'MOVE', 'COPY'}:
                    self.remote[command + ':' + args[0]] += 1
                return original(command, *args)
            self.stack.enter_context(patch.object(f.imap, 'uid', side_effect=filed))
            self.action = 'mail_' + flow.removeprefix('filing_')
            self.args = {'references': [{'account': 'box', 'folder': 'Source',
                'uidvalidity': f.imap.validities['Source'], 'uid': 1, 'message_id': f.imap.mid}], 'target': 'Target'}
            if flow == 'filing_rename':
                self.action = 'mail_folder_rename'
                self.args = {'account': 'box', 'folder': 'Source', 'name': 'Renamed'}
                def rename(source, target):
                    self.remote['RENAME'] += 1
                    f.imap.boxes['Renamed'] = f.imap.boxes.pop('Source')
                    f.imap.roles['Renamed'] = ['\\Trash']
                    f.imap.roles.pop('Source')
                    f.imap.roles['Trash'] = []
                    f.imap.validities['Renamed'] = f.imap.validities.pop('Source')
                    return 'OK', [b'Renamed']
                self.stack.enter_context(patch.object(f.imap, 'rename', side_effect=rename, create=True))
        elif flow == 'archive':
            self.seed_send(None)
            advance = getattr(self, 'advance_archive_clock', None)
            if advance:
                advance()
            cutoff = time.time() - 1
            # Archive real closed rows and events, including VACUUM, rather
            # than an empty no-op export. The restore fence remains intact.
            with f.engine.store.db as db:
                db.execute('UPDATE retained SET created=?', (cutoff - 1,))
                if not advance:
                    for seq, value in db.execute('SELECT seq,value FROM events').fetchall():
                        event = json.loads(value)
                        event['time'] = cutoff - 1
                        db.execute('UPDATE events SET value=? WHERE seq=?', (json.dumps(event), seq))
            self.action, self.args, self.admin = 'control_archive', {'before': cutoff, 'confirm': 'archive finished history'}, True
        elif flow in {'expiry', 'maintenance', 'restart_index', 'restart_tail'}:
            if flow == 'expiry':
                self.approval = f.approval('send', f.compose())
                self.operation_id = self.approval['operation_id']
                self.stack.enter_context(patch('aresos_control.engine.time.time',
                                             return_value=self.approval['description']['expires_at'] + 1))
            elif flow == 'maintenance':
                f.compose()
                self.stack.enter_context(patch('aresos_control.retention.time.time', return_value=time.time() + 86401))
            else:
                from aresos_control.recovery import unfinished
                self.restart_warnings = ({n for _, n, _, _ in unfinished(f.engine.store)},
                    {n['id'] for _, n in f.engine.store.items('notice:') if not n.get('ack')},
                    set(f.engine.store.deferred_notices))
                f.engine.close()
                if flow == 'restart_tail':
                    with open(f.root / 'evidence/operations.jsonl', 'ab') as stream:
                        stream.write(b'Synthetic torn tail')
            self.action, self.args = 'control_pending', {}
        elif flow in {'attachment_export', 'testapp_export', 'export_rollback'}:
            self.export_setup()
        elif flow == 'password':
            self.action, self.args = 'mail_account_add', {
                'id': 'new', 'addresses': ['owner@mail.invalid'], 'username': 'synthetic',
                'imap_host': 'mail.invalid', 'imap_port': 993, 'smtp_host': 'mail.invalid',
                'smtp_port': 465, 'smtp_tls': 'implicit'}
            # Exercise the real owner account-add ingress and password publication,
            # then stop qualification before remote onboarding probes can send.
            class SMTP:
                esmtp_features = {}
            @contextmanager
            def smtp(account):
                yield SMTP()
            self.stack.enter_context(patch.object(f.mail.transport, 'smtp', side_effect=smtp))
            self.stack.enter_context(patch.object(f.imap, 'create', return_value=('NO', [b'Not qualified']), create=True))
        else:
            target = 'mailto:unsubscribe@mail.invalid?subject=Stop&body=Exact' if flow == 'unsubscribe_mailto' else 'https://unsubscribe.mail.invalid/stop'
            raw = f.imap.raw.replace(b'\r\n\r\n', ('\r\nList-Unsubscribe: <' + target + '>\r\nList-Unsubscribe-Post: List-Unsubscribe=One-Click\r\n\r\n').encode())
            f.imap.boxes['Source'][1] = raw
            reference = {'account': 'box', 'folder': 'Source', 'uidvalidity': f.imap.validities['Source'], 'uid': 1, 'message_id': f.imap.mid}
            self.approval = f.approval('unsubscribe', {'reference': reference, 'target': target})
            self.operation_id = self.approval['operation_id']
            self.action, self.args = 'mail_unsubscribe', self.approval
        self.remote.clear()
        if self.approval and self.flow in {'send', 'delete_trash', 'delete_permanent', 'unsubscribe_mailto', 'unsubscribe_https'}:
            self.replay_requests[self.operation_id] = (self.action, copy.deepcopy(self.approval))
        # The torn-tail flow deliberately appends invalid, uncommitted bytes.
        self.committed_before = list(islice(f.engine.store.events, f.engine.store.committed))

    def seed_send(self, failed):
        f = self.fixture
        approval = f.approval('send', f.compose())
        self.replay_requests[approval['operation_id']] = ('mail_send', copy.deepcopy(approval))
        def smtp(operation, composition, raw, stage):
            self.prior_commands['DATA'] += 1
            self.delivered.append(raw)
            if hasattr(self, 'owner_oracle'):
                from email.utils import getaddresses
                from owner_state_oracle.transcript import Transcript
                mail = composition['mail']
                recipients = [address for _, address in getaddresses(mail['to'] + mail['cc'] + mail['bcc'])]
                self.owner_oracle.server('DATA', 'box', identities=[Transcript.message(raw)], recipients=recipients,
                                         accepted=True, fixture_seed=True)
            self.attempted_ids.add(operation['id'])
            stage('smtp_data', 'accepted:250')
            return 'done', 'Synthetic DATA accepted'
        real_local = f.mail.local_stage
        def local(operation, name):
            if name == failed:
                raise Refused('stage_missing', 'Synthetic local failure')
            return real_local(operation, name)
        def seed_append(account, folder, raw, flags):
            self.prior_commands['APPEND'] += 1
            f.imap.boxes[folder][1] = raw
            return {'uid': 1}
        with patch.object(f.mail, 'send_smtp', side_effect=smtp), patch.object(f.mail, 'local_stage', side_effect=local), \
             patch.object(f.mail, 'append', side_effect=seed_append):
            return f.data('send', approval)['operation']

    def export_setup(self):
        f = self.fixture
        from email.message import EmailMessage
        from email.policy import SMTP
        raw = b'Synthetic exported bytes'
        message = EmailMessage()
        message['Message-ID'] = f.imap.mid
        message.set_content('Synthetic message')
        message.add_attachment(raw, maintype='application', subtype='octet-stream', filename='export.bin')
        f.imap.boxes['Source'][1] = message.as_bytes(policy=SMTP)
        caller_root = Path(__file__).resolve().parents[1] / 'test-work'
        caller_root.mkdir(exist_ok=True)
        caller = getattr(self, 'caller_directory', tempfile.TemporaryDirectory)(dir=caller_root)
        f.addCleanup(caller.cleanup)
        home = Path(caller.name)
        folder = home / 'Downloads'
        folder.mkdir()
        app = 'testapp' if self.flow == 'testapp_export' else 'mail'
        self.proxy = Proxy(app, {'act_socket': 'unused', 'home': str(home), 'folders': [str(folder)]})
        class Client:
            def request(self, request):
                return f.engine.request({'v': 1, **request})
            def call(self, name, arguments):
                return self.request({'method': 'call', 'action': name, 'arguments': arguments})
            def download(self, app, key, limit, export_id=None):
                request = {'method': 'download', 'app': app, 'sha256': key}
                if export_id:
                    request['export_id'] = export_id
                result = self.request(request)
                return result, f.engine.blobs.read(key) if result['ok'] else None
        self.proxy.client = Client()
        if self.flow == 'export_rollback':
            save = self.proxy.files.save
            def rollback(*args, **kwargs):
                def fail(name):
                    if name == 'published':
                        raise OSError(errno.ENOSPC, 'Synthetic publication failure')
                return save(*args, checkpoint=fail, **kwargs)
            self.stack.enter_context(patch.object(self.proxy.files, 'save', side_effect=rollback))
        self.action = 'attachment_save' if app == 'mail' else 'file_save'
        self.args = {'folder': str(folder), 'name': 'export.bin'}
        if app == 'mail':
            self.args.update(reference={'account': 'box', 'folder': 'Source',
                'uidvalidity': f.imap.validities['Source'], 'uid': 1, 'message_id': f.imap.mid}, part='1.2')
        else:
            self.args['sha256'] = f.engine.blobs.put(raw, origin='export')
        if not hasattr(os, 'O_TMPFILE'):
            # Only substitute Linux publication primitives on the Mac. All raw
            # writes, fsync and rollback remain production operations under faults.
            original_open, original_link = os.open, os.link
            inode = folder / 'synthetic-inode'
            def unnamed(path, flags, *args, **kwargs):
                if path == '.':
                    return original_open(inode, os.O_CREAT | os.O_RDWR, 0o600)
                return original_open(path, flags, *args, **kwargs)
            def publish(source, target, **kwargs):
                if not str(source).startswith('/proc/self/fd/'):
                    return original_link(source, target, **kwargs)
                original_link(inode, folder / target)
                inode.unlink()
            self.stack.enter_context(patch('os.O_TMPFILE', 1 << 30, create=True))
            self.stack.enter_context(patch('os.open', side_effect=unnamed))
            self.stack.enter_context(patch('os.link', side_effect=publish))
            self.stack.enter_context(patch.object(self.proxy.files, 'directory',
                side_effect=lambda _: os.open(folder, os.O_RDONLY)))
            self.stack.enter_context(patch.object(self.proxy.files, 'real_directory'))

    def install_remote(self):
        f, remote = self.fixture, self.remote
        delivered = self.delivered
        def attempted():
            if self.operation_id is not None:
                self.attempted_ids.add(self.operation_id)
            # Capture the live request's identity in the fixture log, before
            # closing/recovery. Recovered rows never decide expected outcomes.
            for _, operation in f.engine.store.items('op:'):
                if operation.get('repair_of') == self.operation_id and operation['state'] == 'submitting':
                    self.attempted_ids.add(operation['id'])
        class SMTP:
            def has_extn(self, _):
                return False
            def mail(self, *args, **kwargs):
                return 250, b'Synthetic sender accepted'
            def rcpt(self, _):
                return 250, b'Synthetic recipient accepted'
            def data(self, raw):
                attempted()
                remote['DATA'] += 1
                delivered.append(raw)
                return 250, b'Synthetic DATA accepted'
        @contextmanager
        def smtp(account):
            yield SMTP()
        def append(account, folder, raw, flags):
            attempted()
            remote['APPEND'] += 1
            uid = max(f.imap.boxes[folder], default=0) + 1
            f.imap.boxes[folder][uid] = raw
            if self.flow == 'send_duplicate':
                # A separate race scenario retains the inherited delayed-copy
                # warning coverage. Ordinary APPEND has exactly one effect.
                f.imap.boxes[folder][uid + 1] = raw
            self.stages.setdefault(self.operation_id, {})['sent_copy'] = 'done'
            return {'uid': uid}
        class HTTPS:
            def __init__(self, *args, **kwargs):
                pass
            def request(self, method, *args, **kwargs):
                attempted()
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
                attempted()
                remote[command + ':' + str(number)] += 1
                if command == 'MOVE':
                    f.imap.boxes['Trash'][number] = f.imap.boxes[box].pop(number)
                elif command == 'EXPUNGE':
                    if '\\Deleted' in flags.get((box, number), set()):
                        f.imap.boxes[box].pop(number, None)
                else:
                    values = set(args[2].strip('()').split())
                    current = flags.setdefault((box, number), set())
                    if args[1].startswith('+'):
                        current.update(values)
                    elif args[1].startswith('-'):
                        current.difference_update(values)
                    else:
                        flags[box, number] = values
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
        if self.flow in {'expiry', 'maintenance'}:
            try:
                self.fixture.engine.expire()
                return {'ok': True}
            except Exception as exc:
                error = storage_refusal(exc)
                if error is None:
                    raise
                return {'ok': False, 'error': {'code': error.code, 'message': str(error)}}
        if self.flow.startswith('restart_'):
            try:
                self.bind(Engine(self.fixture.root / 'state', self.fixture.root / 'evidence'))
                return {'ok': True}
            except Exception as exc:
                error = storage_refusal(exc)
                if error is None:
                    raise
                return {'ok': False, 'error': {'code': error.code, 'message': str(error)}}
        if 'export' in self.flow:
            return self.proxy.call(self.action, self.args)
        if self.flow == 'password':
            return self.fixture.engine.request({'v': 1, 'method': 'mail_account_add',
                'arguments': self.args, 'password': 'Synthetic test credential'}, admin=True)
        return self.fixture.engine.request({'v': 1, 'method': 'call', 'action': self.action, 'arguments': self.args}, self.admin)

    @contextmanager
    def observed(self):
        f = self.fixture
        stage, observation = f.engine.stage, f.mail.sent_observation
        def seen_stage(operation_id, name, outcome, **kwargs):
            self.stages.setdefault(operation_id, {})[name] = outcome
            return stage(operation_id, name, outcome, **kwargs)
        def seen_copies(op, matches):
            copies = self.copies.setdefault(op['id'], [])
            copies.extend(copy.deepcopy(item) for item in matches if item not in copies)
            return observation(op, matches)
        with patch.object(f.engine, 'stage', side_effect=seen_stage), patch.object(f.mail, 'sent_observation', side_effect=seen_copies):
            yield

    def recover(self, failed=False):
        f = self.fixture
        remote = self.remote.copy()
        prior = self.prior_commands.copy()
        from aresos_control.recovery import unfinished
        if self.flow.startswith('restart_'):
            implied, warnings, deferred = self.restart_warnings
        else:
            implied = {notice_id for _, notice_id, _, _ in unfinished(f.engine.store)}
            warnings = {n['id'] for _, n in f.engine.store.items('notice:') if not n.get('ack')}
            deferred = set(f.engine.store.deferred_notices)
        f.engine.close()
        # The first restart itself hits full disk; no fixture transport may run.
        restart = DurableWrites(1)
        try:
            with restart.wrap():
                self.bind(Engine(f.root / 'state', f.root / 'evidence'))
        except Exception as exc:
            f.assertIsNotNone(storage_refusal(exc), repr(exc))
        f.assertTrue(restart.failed, restart.points)
        f.assertEqual(self.remote, remote)
        f.engine.close()
        self.bind(Engine(f.root / 'state', f.root / 'evidence'))
        if f.engine.store.locked:
            result = f.engine.request({'v': 1, 'method': 'call', 'action': 'control_restore_confirm',
                                      'arguments': {'confirm': 'invalidate earlier approvals'}}, admin=True)
            f.assertTrue(result['ok'], result)
        # Every durable unfinished intent must disclose a warning after crash.
        visible = {n['id'] for _, n in f.engine.store.items('notice:') if not n.get('ack')}
        visible.update(f.engine.store.deferred_notices)
        from aresos_control.recovery import recovery_notices
        visible.update(n['id'] for n in recovery_notices(f.engine.store))
        f.assertTrue(implied <= visible, ('Lost implied warnings', implied - visible))
        f.assertTrue(warnings <= visible, ('Lost durable warnings', warnings - visible))
        # Filing intent identities themselves must already be visible at startup.
        f.assertTrue({n for n in deferred if f.engine.store.get('mail:filing:' + n) or
                      f.engine.store.get('mail:rename:' + n)} <= visible)
        f.assertEqual(f.engine.store.committed, f.engine.store.sequence)
        f.assertFalse(f.engine.store.write_failed)
        f.assertEqual(list(f.engine.store.events)[:len(self.committed_before)], self.committed_before,
                      'Every earlier committed independent record must survive')
        self.assert_duplicate_warnings()
        for operation_id in self.attempted_ids:
            if self.flow == 'archive' and f.engine.store.get('archived:' + operation_id):
                self.assert_archived(operation_id)
                continue
            state = f.data('operation_status', {'operation_id': operation_id})['operation']['state']
            f.assertIn(state, {'unknown', 'partial', 'done'}, (operation_id, prior, remote, state))
            self.assert_completion(operation_id, state)
            if operation_id in self.replay_requests:
                action, approval = self.replay_requests[operation_id]
                f.engine.request({'v': 1, 'method': 'call', 'action': action, 'arguments': approval})
        for operation_id, copies in self.copies.items():
            if len(copies) > 1:
                status = f.data('operation_status', {'operation_id': operation_id})
                f.assertIn(str(len(copies)) + ' copies', status['evidence']['sent_copy_warning'])
        if self.operation_id is not None:
            status = f.data('operation_status', {'operation_id': self.operation_id})
            state = status['operation']['state']
            self.assert_completion(self.operation_id, state)
            if remote:
                # Expected from fixture-side attempted commands, never from kv.
                f.assertIn(state, {'unknown', 'partial', 'done'}, (self.flow, remote, status))
                for _, repair in f.engine.store.items('op:'):
                    if repair.get('repair_of') == self.operation_id and self.flow == 'repair':
                        f.assertIn(repair['state'], {'unknown', 'done'}, repair)
            if not failed:
                expected = {'cancel': 'failed', 'expiry': 'failed', 'restore': 'unknown',
                            'send': 'done', 'send_duplicate': 'done', 'repair': 'done', 'settlement': 'done', 'status': 'done',
                            'delete_trash': 'done', 'delete_permanent': 'done',
                            'unsubscribe_mailto': 'done', 'unsubscribe_https': 'done'}
                f.assertEqual(state, expected[self.flow], (self.flow, status))
            if self.approval and (remote or state != 'reserved') and self.flow != 'expiry':
                self.call()
            if self.flow in {'repair', 'settlement'} and f.imap.boxes['Sent']:
                f.call('operation_repair', self.args)

        f.assertEqual(self.remote, remote, 'Restart/status/replay must never repeat remote work')
        f.assertEqual(self.prior_commands, prior)
        f.assertTrue(all(count <= 1 for count in remote.values()), remote)
        source = 'Renamed' if self.flow == 'filing_rename' and remote else 'Source'
        f.assertIn(7, f.imap.boxes[source], 'Unnamed Deleted mail must survive')
        if remote.get('MOVE:1') or remote.get('EXPUNGE:1'):
            f.assertNotIn(1, f.imap.boxes['Source'])
        if remote.get('APPEND'):
            f.assertEqual(len(f.imap.boxes['Sent']), 2 if self.flow == 'send_duplicate' else 1,
                          'Every independently observed Sent copy must survive')
        if self.flow in {'filing_move', 'filing_copy'} and remote:
            f.assertEqual(f.imap.boxes['Target'][1], f.imap.raw)
            f.assertEqual(1 in f.imap.boxes['Source'], self.flow == 'filing_copy')
        if self.flow == 'maintenance' and not failed:
            f.assertEqual(f.engine.store.items('mail:composition:'), [])
        if self.flow == 'password':
            f.assertFalse((f.engine.store.get('mail:account:new') or {}).get('ready', False))

    def assert_duplicate_warnings(self):
        # The public catalogue may rerun an unresolved read-only check. Status
        # must not recreate the warning before we check its own identity/count.
        f, seen, args = self.fixture, {}, {}
        while True:
            page = f.data('filing_notices', args)
            for notice in page['items']:
                content = notice['untrusted_content']
                if 'operation_id' in content and 'message_count' in content:
                    seen[content['operation_id']] = content
            if not page['cursor']:
                break
            args = {'cursor': page['cursor']}
        for operation_id, copies in self.copies.items():
            if len(copies) > 1:
                f.assertIn(operation_id, seen, ('Lost operation duplicate warning', operation_id, seen))
                f.assertEqual(seen[operation_id]['message_count'], len(copies))
                f.assertIn(str(len(copies)) + ' copies', seen[operation_id]['reason'])

    def assert_completion(self, operation_id, state):
        if state != 'done':
            return
        f = self.fixture
        commands = self.prior_commands + self.remote
        if self.flow.startswith('delete_'):
            # These are the requested fixture identities, never reconstructed
            # from potentially damaged operation/stage records.
            for uid in (1, 2):
                f.assertNotIn(uid, f.imap.boxes['Source'], ('false done', self.flow, uid, commands))
                command = 'MOVE' if self.flow == 'delete_trash' else 'EXPUNGE'
                f.assertEqual(commands[command + ':' + str(uid)], 1, ('false done', uid, commands))
                if self.flow == 'delete_trash':
                    f.assertEqual(f.imap.boxes['Trash'].get(uid), f.imap.raw)
        elif self.flow in {'send', 'repair', 'status', 'settlement', 'unsubscribe_mailto'}:
            f.assertEqual(commands['DATA'], 1, ('false done', self.flow, commands))
            from aresos_control.mail.codec import parse
            # The receiver and Sent must identify THIS delivery, independently
            # of what a damaged/recovered operation claims in its stage map.
            source_id = self.operation_id
            mid = f.mail.message_id(source_id)
            matching_data = [raw for raw in self.delivered if str(parse(raw).get('Message-ID', '')) == mid]
            f.assertEqual(len(matching_data), 1, ('false matching DATA', mid, commands))
            if self.flow != 'unsubscribe_mailto':
                copies = [raw for raw in f.imap.boxes['Sent'].values()
                          if str(parse(raw).get('Message-ID', '')) == mid]
                f.assertTrue(copies, ('false matching Sent copy', mid, commands))
        elif self.flow == 'unsubscribe_https':
            f.assertEqual(commands['POST'], 1, ('false done', commands))

    def assert_archived(self, operation_id):
        f = self.fixture
        f.assertIsNone(f.engine.store.get('op:' + operation_id))
        from aresos_control.common import sha256
        manifests = f.engine.store.items('archive:')
        f.assertTrue(manifests)
        exported = []
        for _, manifest in manifests:
            raw = Path(manifest['path']).read_bytes()
            f.assertEqual(sha256(raw), manifest['sha256'])
            exported.extend(json.loads(line) for line in raw.splitlines())
        f.assertTrue(any(row.get('key') == 'op:' + operation_id and row['value']['state'] == 'done'
                         for row in exported), ('Missing committed archived operation', operation_id))

    def close(self):
        try:
            self.stack.close()
            self.fixture.doCleanups()
        finally:
            self.fixture_clock.close()


class FaultSweep23(unittest.TestCase):
    def test_archive_replays_have_identical_write_traces(self):
        traces = []
        for _ in range(3):
            scenario = Scenario('archive')
            try:
                fault = DurableWrites()
                with scenario.observed(), fault.wrap(scenario.fixture.engine.store):
                    self.assertTrue(scenario.call()['ok'])
                scenario.recover()
                traces.append(fault.points)
            finally:
                scenario.close()
        self.assertTrue(traces[0])
        self.assertEqual(traces[0], traces[1])
        self.assertEqual(traces[0], traces[2])

    def test_review24_recovery_oracle_rejects_attempted_send_returning_to_reserved(self):
        scenario = Scenario('send')
        try:
            self.assertTrue(scenario.call()['ok'])
            self.assertEqual(scenario.remote['DATA'], 1)
            # Model an unsafe recovery regression without changing fixture logs.
            op = scenario.fixture.engine.operation(scenario.operation_id)
            op['state'] = 'reserved'
            with scenario.fixture.engine.store.db as db:
                db.execute('UPDATE kv SET v=? WHERE k=?', (json.dumps(op), 'op:' + scenario.operation_id))
            with self.assertRaises(AssertionError):
                scenario.recover(failed=True)
            self.assertEqual(scenario.remote['DATA'], 1)
        finally:
            scenario.close()

    def test_review25_completion_oracle_rejects_two_message_delete_with_only_move_one(self):
        scenario = Scenario('delete_trash')
        try:
            f = scenario.fixture
            f.imap.boxes['Trash'][1] = f.imap.boxes['Source'].pop(1)
            scenario.remote['MOVE:1'] = 1
            self.assertIn(2, f.imap.boxes['Source'])
            with self.assertRaises(AssertionError):
                scenario.assert_completion(scenario.operation_id, 'done')
        finally:
            scenario.close()

    def assert_result(self, scenario, sweep, result):
        transport_response(result)
        self.assertTrue(sweep.failed, sweep.points)
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
        for key in ('operation', 'original'):
            op = result.get('data', {}).get(key)
            if op:
                scenario.assert_completion(op['id'], op['state'])

    def fault(self, flow, number, mode='single', cleanup_at=None):
        scenario = Scenario(flow)
        try:
            sweep = DurableWrites(number, mode=mode, cleanup_at=cleanup_at)
            with scenario.observed(), sweep.wrap(None if flow.startswith('restart_') else scenario.fixture.engine.store):
                result = scenario.call()
            self.assert_result(scenario, sweep, result)
            cleanups = sweep.cleanup_points[:]
            if cleanup_at is not None:
                self.assertIn((cleanup_at, sweep.points[cleanup_at - 1], 'EIO'), sweep.failures)
            scenario.recover(failed=True)
            return sweep.points, cleanups
        finally:
            scenario.close()

    def test_review23_enospc_at_every_discovered_durable_write(self):
        flows = ('send', 'repair', 'delete_trash', 'delete_permanent', 'unsubscribe_mailto', 'unsubscribe_https',
                 'status', 'settlement', 'cancel', 'restore', 'attachment_export', 'testapp_export',
                 'password', 'filing_move', 'filing_copy', 'filing_rename', 'expiry', 'maintenance',
                 'restart_index', 'restart_tail', 'export_rollback', 'archive', 'send_duplicate')
        mechanisms, counts = Counter(), Counter()
        started = time.monotonic()
        shard = int(os.environ.get('MAIL_SWEEP_SHARD', '0'))
        shards = int(os.environ.get('MAIL_SWEEP_SHARDS', '1'))
        for flow_index, flow in enumerate(flows):
            flow_started = time.monotonic()
            flow_counts = Counter()
            clean = Scenario(flow)
            try:
                sweep = DurableWrites()
                with clean.observed(), sweep.wrap(None if flow.startswith('restart_') else clean.fixture.engine.store):
                    result = clean.call()
                transport_response(result)
                self.assertTrue(result['ok'] or flow == 'password' and result['error']['code'] == 'server_refused'
                                or flow == 'export_rollback' and result['error']['code'] == 'storage_limit', result)
                points = sweep.points
                mechanisms.update(points)
                self.assertGreater(len(points), 0, flow)
                clean.recover()
            finally:
                clean.close()
            if flow_index % shards != shard:
                continue
            print(f'Review26 OS/VFS write points: {flow}={len(points)} {dict(Counter(points))}', flush=True)
            for number, label in enumerate(points, 1):
                if label.endswith('.close'):
                    continue  # Close is a secondary EIO site, not a primary write.
                with self.subTest(flow=flow, point=number, label=label, mode='single'):
                    trace, cleanups = self.fault(flow, number)
                    self.assertEqual(trace[:number], points[:number])
                    flow_counts['single'] += 1
                with self.subTest(flow=flow, point=number, label=label, mode='persistent'):
                    trace, _ = self.fault(flow, number, mode='persistent')
                    self.assertEqual(trace[:number], points[:number])
                    flow_counts['persistent'] += 1
                for cleanup_at, cleanup_label, purpose in cleanups:
                    if cleanup_at <= number:
                        continue
                    with self.subTest(flow=flow, point=number, mode='pair', cleanup=cleanup_at,
                                      cleanup_label=cleanup_label, purpose=purpose):
                        self.fault(flow, number, cleanup_at=cleanup_at)
                        flow_counts['pairs'] += 1
            counts.update(flow_counts)
            print(f'Review26 modes: {flow} {dict(flow_counts)}; elapsed={time.monotonic() - flow_started:.3f}s', flush=True)
        for mechanism in ('journal.write', 'journal.truncate', 'sqlite.main.write', 'sqlite.index.write',
                          'sqlite.main.create', 'sqlite.index.create', 'file.create', 'file.write',
                          'file.link', 'file.rename', 'file.truncate', 'file.fsync', 'file.close', 'sqlite.main.close'):
            self.assertGreater(mechanisms[mechanism], 0, mechanism)
        self.assertGreater(counts['pairs'], 0)
        print(f'Review26 OS/VFS mechanisms: {dict(mechanisms)}; modes={dict(counts)}; '
              f'elapsed={time.monotonic() - started:.3f}s', flush=True)
