"""Review 8 regressions through parsing, real storage and caller write policy."""
from pathlib import Path
import os
import socket
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from aresos_control import retention
from aresos_control.space import SAFETY_FLOOR
from aresos_control.common import Refused, canonical, digest, sha256
from aresos_control.daemon import Daemon
from aresos_control.engine import Engine
from aresos_control.mail import codec
from aresos_control.proxy import Proxy
import test_review_fixes_12 as round12


class Review16(unittest.TestCase):
    setUp = round12.PlainQuestions12.setUp
    call = round12.PlainQuestions12.call
    data = round12.PlainQuestions12.data
    compose = round12.PlainQuestions12.compose
    reference = round12.PlainQuestions12.reference
    approval = round12.PlainQuestions12.approval

    def restart(self):
        self.engine.close()
        self.engine = Engine(self.root / 'state', self.root / 'evidence')
        self.mail.store = self.engine.store
        self.mail.blobs = self.engine.blobs
        self.mail.check_result = self.engine.check_composition_result
        self.engine.adapters['mail'] = self.mail
        self.assertFalse(self.engine.store.locked)
        self.assertFalse(self.engine.store.write_failed)

    def snapshot(self):
        return ((self.root / 'evidence/operations.jsonl').read_bytes(),
                list(self.engine.store.db.iterdump()),
                {p.name: p.read_bytes() for p in self.engine.blobs.directory.iterdir()})

    def test_review16_nested_mail_refuses_read_search_thread_and_both_forward_styles_then_reads_other_mail(self):
        reference = self.reference()
        self.imap.boxes['Source'][1] = (b'From: sender@mail.invalid\r\nSubject: hostile\r\n'
            b'Message-ID: <question@mail.invalid>\r\nContent-Type: message/rfc822\r\n\r\n'
            + b'Content-Type: message/rfc822\r\n\r\n' * 1200 + b'Content-Type: text/plain\r\n\r\nBody')
        calls = [('read', {'reference': reference}), ('search', {'account': 'box', 'folders': ['Source']}),
                 ('thread', {'reference': reference}), ('attachment_save', {'reference': reference, 'part': 'source'})]
        calls += [('compose', {'account': 'box', 'mode': 'forward', 'reference': reference,
                              'forward_as': mode, 'to': ['peer@mail.invalid']}) for mode in ('inline', 'attachment')]
        for verb, args in calls:
            with self.subTest(verb=verb, args=args):
                result = self.call(verb, args)
                self.assertEqual(result['error']['code'], 'mime_limit', result)
                self.assertIn('"uid":1', result['error']['message'])
                self.assertIn('Source', result['error']['message'])
                self.data('read', {'reference': self.reference(2)})
        self.assertEqual(self.imap.mutations, [])

    def test_review16_parser_part_count_depth_edges_and_implicit_digest_children(self):
        codec.parse(b'Content-Type: message/rfc822\r\n\r\n' * codec.MIME_DEPTH_LIMIT + b'\r\nOK')
        for kind in (b'mixed', b'digest'):
            with self.subTest(kind=kind):
                raw = b'Content-Type: multipart/' + kind + b'; boundary=x\r\n\r\n'
                raw += (b'--x\r\n\r\nContent-Type: text/plain\r\n\r\nBody\r\n' * codec.MIME_PART_LIMIT) + b'--x--\r\n'
                with self.assertRaises(Refused) as error:
                    codec.parse(raw, {'uid': 17})
                self.assertEqual(error.exception.code, 'mime_limit')
                self.assertIn('17', str(error.exception))
        codec.parse(b'Subject: ordinary\r\n\r\nStill works')

    def test_review16_unexpected_request_errors_keep_next_request_and_journal_valid(self):
        for error in (RuntimeError('fixture'), RecursionError(), MemoryError()):
            with self.subTest(error=type(error).__name__):
                before = self.snapshot()
                with patch.object(self.engine, 'dispatch', side_effect=error):
                    result = self.call('read', {'reference': self.reference()})
                self.assertEqual(result['error']['code'], 'internal_error', result)
                self.assertEqual(self.snapshot(), before)
                self.data('read', {'reference': self.reference()})
        self.restart()

    def test_review16_daemon_contains_unexpected_exception_and_serves_next_connection(self):
        for exception in (RuntimeError('fixture'), RecursionError(), MemoryError()):
            with self.subTest(error=type(exception).__name__):
                daemon = Daemon.__new__(Daemon)
                daemon.stopping = False
                daemon.config = {'owner_uid': 123}
                daemon.engine = Mock()
                daemon.engine.request.side_effect = [exception, {'ok': True, 'data': {'next': True}}]
                connections = [Mock(), Mock()]
                for conn in connections:
                    conn.__enter__ = Mock(return_value=conn)
                    conn.__exit__ = Mock(return_value=False)
                    conn.getsockopt.return_value = struct.pack('3i', 1, 123, 123)
                listener = Mock()
                listener.accept.side_effect = [(conn, None) for conn in connections]
                key = SimpleNamespace(fileobj=listener, data='act')
                calls = iter([[(key, None)], [(key, None)]])
                def select(timeout):
                    try:
                        return next(calls)
                    except StopIteration:
                        daemon.stopping = True
                        return []
                daemon.selector = SimpleNamespace(select=select)
                sent = []
                with patch.object(socket, 'SO_PEERCRED', 17, create=True), \
                     patch('aresos_control.daemon.receive', return_value={}), \
                     patch('aresos_control.daemon.send', side_effect=lambda c, r, **kw: sent.append(r)):
                    daemon.serve()
                self.assertEqual(sent[0]['error']['code'], 'internal_error')
                self.assertTrue(sent[1]['data']['next'])

    def test_review16_oversized_composition_has_no_persisted_effect_repeated_or_derived(self):
        before = self.snapshot()
        for _ in range(3):
            result = self.call('compose', {'account': 'box', 'to': ['peer@mail.invalid'], 'text': 'x' * 200000})
            self.assertEqual(result['error']['code'], 'result_too_large', result)
            self.assertEqual(self.snapshot(), before)
        # A refusal after building a quoted body must discard its staged blob too.
        result = self.call('compose', {'account': 'box', 'mode': 'forward', 'reference': self.reference(),
                                      'to': ['peer@mail.invalid'], 'text': 'x' * 200000})
        self.assertEqual(result['error']['code'], 'result_too_large', result)
        self.assertEqual(self.snapshot(), before)
        self.restart()

    def test_review16_composition_count_and_bytes_caps_expire_but_pin_open_operation(self):
        first = self.compose()
        comp = self.mail.composition(first)
        for field, value in [('COMPOSITION_COUNT', 1), ('COMPOSITION_BYTES', retention.size(comp))]:
            with self.subTest(cap=field), patch.object(retention, field, value):
                before = self.snapshot()
                result = self.call('compose', {'account': 'box', 'text': 'another'})
                self.assertEqual(result['error']['code'], 'storage_limit', result)
                self.assertIn(str(value), result['error']['message'])
                self.assertIn('24 hours', result['error']['message'])
                self.assertEqual(self.snapshot(), before)
                self.restart()
        approval = self.approval('send', first)
        with patch('aresos_control.retention.time.time', return_value=comp['created_at'] + retention.TTL + 1):
            # Expire working data without expiring the still-open approval.
            retention.expire(self.engine)
            self.assertIsNotNone(self.engine.store.get('mail:composition:' + comp['id']))
        self.data('operation_cancel', {'operation_id': approval['operation_id']})
        with patch('aresos_control.retention.time.time', return_value=comp['created_at'] + retention.TTL + 1):
            retention.expire(self.engine)
            self.assertIsNone(self.engine.store.get('mail:composition:' + comp['id']))
            with patch.object(retention, 'COMPOSITION_COUNT', 1):
                self.compose()
        self.restart()

    def test_review16_blob_count_and_bytes_caps_cover_import_export_generated_and_wire(self):
        for blob_store in (self.engine.blobs, self.mail.wires):
            for field, value in [('BLOB_COUNT', 1), ('BLOB_BYTES', 4)]:
                with self.subTest(directory=blob_store.directory.name, cap=field), patch.object(retention, field, value):
                    key = blob_store.put(b'base', origin='caller_import')
                    before = {p.name: p.read_bytes() for p in blob_store.directory.iterdir()}
                    for origin in ('caller_import', 'export', 'quoted_mail', 'draft_body', 'draft_html', 'composition_part', 'wire'):
                        with self.assertRaises(Refused) as error:
                            blob_store.put(origin.encode(), origin=origin)
                        self.assertEqual(error.exception.code, 'storage_limit')
                        self.assertEqual({p.name: p.read_bytes() for p in blob_store.directory.iterdir()}, before)
                    blob_store.expire(set(), os.stat(blob_store.directory / key).st_mtime + retention.TTL + 1, retention.TTL)
                    blob_store.put(b'next')
                    blob_store.expire(set(), os.stat(blob_store.directory / sha256(b'next')).st_mtime + retention.TTL + 1, retention.TTL)
        self.restart()

    def test_review16_import_reference_count_and_bytes_cap_before_upload_then_expiry(self):
        blob = {'sha256': sha256(b'one'), 'size': 3, 'name': 'one', 'real_path': '/fixture/one'}
        self.engine.blobs.put(b'one', origin='caller_import')
        self.engine.store.write({'blob:' + digest(blob): blob}, 'fixture', 'Import fixture')
        other = {**blob, 'name': 'two', 'real_path': '/fixture/two'}
        for cap, limit in [('IMPORT_COUNT', 1), ('IMPORT_BYTES', retention.size(blob))]:
            with patch.object(retention, cap, limit):
                before = self.snapshot()
                result = self.engine.request({'v': 1, 'method': 'upload', 'app': 'mail', 'file': other})
                self.assertEqual(result['error']['code'], 'storage_limit', result)
                self.assertEqual(self.snapshot(), before)
        with patch('aresos_control.retention.time.time', return_value=retention.TTL + self.engine.store.retained_at('blob:' + digest(blob)) + 1):
            retention.expire(self.engine)
            with patch.object(retention, 'IMPORT_COUNT', 1):
                self.assertTrue(self.engine.request({'v': 1, 'method': 'upload', 'app': 'mail', 'file': other})['ok'])
        self.restart()

    def test_review16_filing_notice_count_caps_refuse_before_remote_action_then_ack_expiry(self):
        self.engine.store.write({'mail:filing:kept': {'id': 'kept', 'state': 'partial'},
            'notice:kept': {'id': 'kept', 'app': 'mail', 'state': 'partial', 'ack': False,
                            'untrusted_content': {'reason': 'Check preserved messages'}}}, 'fixture', 'Unresolved warning')
        for cap in ('FILING_COUNT', 'NOTICE_COUNT'):
            with patch.object(retention, cap, 1):
                before = self.snapshot()
                result = self.call('move', {'references': [self.reference()], 'target': 'Target'})
                self.assertEqual(result['error']['code'], 'storage_limit', result)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(self.imap.mutations, [])
        self.data('notice_ack', {'operation_id': 'kept'})
        with patch('aresos_control.retention.time.time', return_value=retention.TTL + self.engine.store.retained_at('notice:kept') + 1):
            retention.expire(self.engine)
            self.assertEqual(self.engine.store.items('notice:'), [])
            self.assertEqual(self.engine.store.items('mail:filing:'), [])
            with patch.object(retention, 'FILING_COUNT', 1), patch.object(retention, 'NOTICE_COUNT', 1):
                self.assertEqual(self.data('copy', {'references': [self.reference()], 'target': 'Target'})['state'], 'partial')
        self.restart()

    def test_review16_filing_notice_location_bytes_caps_refuse_before_journal_fence(self):
        for cap, key in [('FILING_BYTES', 'mail:filing:large'), ('FILING_BYTES', 'mail:filing-locations:large:0'),
                         ('NOTICE_BYTES', 'notice:large')]:
            with self.subTest(key=key), patch.object(retention, cap, 100):
                before = self.snapshot()
                with self.assertRaises(Refused) as error:
                    self.engine.store.write({key: {'value': 'x' * 101}}, 'fixture', 'Must refuse')
                self.assertEqual(error.exception.code, 'storage_limit')
                self.assertEqual(self.snapshot(), before)
                self.assertFalse(self.engine.store.write_failed)
                self.restart()

    def test_review16_low_disk_space_refuses_blobs_and_journal_before_fence(self):
        before = self.snapshot()
        with patch('aresos_control.space.shutil.disk_usage', return_value=SimpleNamespace(free=SAFETY_FLOOR + self.engine.store.ledger.held)):
            with self.assertRaises(Refused) as error:
                self.engine.blobs.put(b'new')
            self.assertEqual(error.exception.code, 'storage_limit')
            with self.assertRaises(Refused) as error:
                self.engine.store.write({}, 'fixture', 'No space')
            self.assertEqual(error.exception.code, 'storage_limit')
        self.assertEqual(self.snapshot(), before)
        self.restart()
        self.compose()

    def test_review16_audit_admission_covers_repeated_free_changes_before_fence(self):
        with patch.object(retention, 'HISTORY_BYTES', self.engine.store.history_size()):
            before = self.snapshot()
            result = self.call('compose', {'account': 'box', 'text': 'new'})
            self.assertEqual(result['error']['code'], 'storage_limit', result)
            with self.assertRaises(Refused):
                self.engine.store.write({}, 'fixture', 'No audit bytes past cap')
            self.assertEqual(self.snapshot(), before)
            self.assertFalse(self.engine.store.write_failed)
        self.restart()
        self.compose()


class CallerWrites16(unittest.TestCase):
    def test_review16_every_caller_write_refuses_all_claude_and_shell_startup_paths(self):
        home = '/home/fixture'
        forbidden = ['.claude/settings.json', '.claude/hooks/run', '.claude.json', 'Documents/project/.claude/settings.json',
                     'Documents/project/.claude/settings.local.json', 'Documents/project/.mcp.json',
                     '.bashrc', '.bash_profile', '.bash_login', '.profile', '.zshrc', '.zprofile', '.zshenv']
        for app, verb in [('testapp', 'file_save'), ('mail', 'file_save'), ('mail', 'attachment_save')]:
            proxy = Proxy(app, {'act_socket': '/unused', 'home': home, 'folders': [home + '/Documents']})
            proxy.client = Mock()
            proxy.client.download.return_value = ({'ok': True}, b'data')
            proxy.client.request.return_value = {'ok': True, 'data': {}}
            proxy.client.call.side_effect = lambda name, args: ({'data': {}} if name == 'control_pending' else
                {'ok': True, 'data': {'file': {'sha256': sha256(b'data'), 'name': 'attachment'}}, 'pending': {}})
            for target in forbidden:
                with self.subTest(app=app, verb=verb, target=target):
                    folder, name = (Path(home) / target).parent, Path(target).name
                    args = {'folder': str(folder), 'name': name}
                    if verb == 'file_save':
                        args['sha256'] = sha256(b'data')
                    else:
                        args.update(reference={'account': 'box', 'folder': 'INBOX', 'uidvalidity': 1, 'uid': 1,
                                               'message_id': '<fixture@mail.invalid>'}, part='source')
                    result = proxy.call(verb, args)
                    self.assertFalse(result['ok'], result)
                    self.assertEqual(result['error']['code'], 'permission_denied' if (app, verb) == ('mail', 'file_save') else 'file_refused', result)
