"""Stage 1 independent owner-state comparisons at every inherited fault site."""
from collections import Counter
from contextlib import contextmanager
import os
import time
import unittest
from unittest.mock import patch

from aresos_control.engine import Engine
from owner_state_oracle.driver import Driver
from owner_state_oracle.gaps import Gaps
from test_review23_sweep import Scenario
from storage_faults import OSWrites

FLOWS = ('send', 'repair', 'delete_trash', 'delete_permanent', 'unsubscribe_mailto', 'unsubscribe_https',
         'status', 'settlement', 'cancel', 'restore', 'attachment_export', 'testapp_export',
         'password', 'filing_move', 'filing_copy', 'filing_rename', 'expiry', 'maintenance',
         'restart_index', 'restart_tail', 'export_rollback', 'archive')
EXTRA = ('draft_append', 'folder_create', 'folder_delete', 'onboarding', 'flag', 'settings', 'folder_review',
         'testapp_send', 'testapp_delete', 'testapp_config')


class OwnerScenario(Scenario):
    def __init__(self, flow):
        super().__init__('send' if flow in EXTRA else flow)
        if flow not in EXTRA:
            return
        f = self.fixture
        self.flow, self.admin = flow, False
        self.action, self.args = 'mail_accounts', {}
        def create(name):
            name = name.strip('"')
            self.remote['CREATE'] += 1
            f.imap.boxes[name], f.imap.roles[name], f.imap.validities[name] = {}, [], len(f.imap.validities) + 1
            return 'OK', [b'Created']
        def delete(name):
            name = name.strip('"')
            self.remote['DELETE'] += 1
            if f.imap.boxes[name]:
                return 'NO', [b'[CANNOT] Nonempty DELETE forbidden']
            for values in (f.imap.boxes, f.imap.roles, f.imap.validities):
                values.pop(name)
            return 'OK', [b'Deleted']
        self.stack.enter_context(patch.object(f.imap, 'create', side_effect=create, create=True))
        self.stack.enter_context(patch.object(f.imap, 'delete', side_effect=delete, create=True))
        if flow == 'draft_append':
            def draft_append(account, folder, raw, flags=None):
                self.remote['APPEND'] += 1
                uid = max(f.imap.boxes[folder], default=0) + 1
                f.imap.boxes[folder][uid] = raw
                return {'account': account['id'], 'folder': folder, 'uidvalidity': f.imap.validities[folder],
                        'uid': uid, 'message_id': str(__import__('email.parser', fromlist=['BytesParser']).BytesParser().parsebytes(raw)['Message-ID'])}
            self.stack.enter_context(patch.object(f.mail, 'append', side_effect=draft_append))
            self.action, self.args = 'mail_draft_save', f.compose()
        elif flow == 'folder_create':
            self.action, self.args = 'mail_folder_create', {'account': 'box', 'name': 'Created'}
        elif flow == 'folder_delete':
            self.args = f.approval('folder_delete', {'account': 'box', 'folder': 'Target'})
            self.operation_id = self.args['operation_id']
            self.action = 'mail_folder_delete'
        elif flow == 'onboarding':
            self.action, self.args, self.admin = 'mail_account_add', {'id': 'new', 'addresses': ['owner@mail.invalid'],
                'username': 'synthetic', 'imap_host': 'mail.invalid', 'imap_port': 993, 'smtp_host': 'mail.invalid',
                'smtp_port': 465, 'smtp_tls': 'implicit'}, True
            class SMTP:
                esmtp_features = {}
                def has_extn(self, _): return False
                def mail(self, *a, **kw): return 250, b'ok'
                def rcpt(self, *a): return 250, b'ok'
                def data(self, raw):
                    self_remote['DATA'] += 1
                    return 250, b'ok'
            self_remote = self.remote
            @contextmanager
            def smtp(_): yield SMTP()
            self.stack.enter_context(patch.object(f.mail.transport, 'smtp', side_effect=smtp))
            def append(account, folder, raw, flags=None):
                self.remote['APPEND'] += 1
                uid = max(f.imap.boxes[folder], default=0) + 1
                f.imap.boxes[folder][uid] = raw
                return {'account': account['id'], 'folder': folder, 'uidvalidity': f.imap.validities[folder],
                        'uid': uid, 'message_id': str(__import__('email.parser', fromlist=['BytesParser']).BytesParser().parsebytes(raw)['Message-ID'])}
            self.stack.enter_context(patch.object(f.mail, 'append', side_effect=append))
            self.stack.enter_context(patch('aresos_control.mail.onboarding.time.sleep'))
        elif flow == 'flag':
            self.action, self.args = 'mail_flag', {'references': [{'account': 'box', 'folder': 'Source',
                'uidvalidity': f.imap.validities['Source'], 'uid': 1, 'message_id': f.imap.mid}], 'add': ['\\Seen'], 'remove': []}
        elif flow == 'settings':
            self.action, self.args, self.admin = 'mail_account_settings', {'id': 'box', 'format': 'plain'}, True
        elif flow == 'folder_review':
            review = f.engine.request({'v': 1, 'method': 'call', 'action': 'mail_account_folders', 'arguments': {'id': 'box'}}, True)
            self.action, self.args, self.admin = 'mail_account_folders', {'id': 'box', 'roles_hash': review['data']['roles_hash']}, True
        elif flow == 'testapp_config':
            self.action, self.args, self.admin = 'testapp_fixture_configure', {'refuse': [], 'failure': 'none'}, True
        else:
            verb = flow.removeprefix('testapp_')
            arguments = {'account': 'fixture', 'to': ['alpha'], 'cc': [], 'bcc': [], 'subject': 'Synthetic', 'text': 'Exact', 'attachments': []}
            if verb == 'delete':
                listing = f.engine.request({'v': 1, 'method': 'call', 'action': 'testapp_list', 'arguments': {}})['data']
                arguments = {'references': [listing['items'][0]['reference']]}
            approval = f.engine.request({'v': 1, 'method': 'call', 'action': 'testapp_prepare_' + verb, 'arguments': arguments})['data']['approval']
            self.action, self.args, self.operation_id = 'testapp_' + verb, approval, approval['operation_id']

    def call(self):
        if self.flow == 'onboarding':
            return self.fixture.engine.request({'v': 1, 'method': 'mail_account_add', 'arguments': self.args,
                                                'password': 'Synthetic fixture credential'}, True)
        return super().call()


def exercise(flow, number=None, mode='single', cleanup_at=None, gaps=None):
    s = OwnerScenario(flow)
    gaps.aliases = {}
    try:
        d, fault = Driver(s), OSWrites(number, mode=mode, cleanup_at=cleanup_at)
        d.alias_callback = gaps.bind
        gaps.bind(d.record)
        case = f'{flow}/{mode}/{number or 0}/{cleanup_at or 0}'
        with d.observe(fault), fault.wrap(None if flow.startswith('restart_') else s.fixture.engine.store):
            reply = s.call()
        d.reply(reply, delivered=False if number else True)
        points, cleanups = list(fault.points), list(fault.cleanup_points)
        if number is None:
            assert reply['ok'] or flow == 'password' and reply['error']['code'] == 'server_refused' or flow == 'export_rollback' and reply['error']['code'] == 'storage_limit', (flow, reply)
            assert points, ('Flow did not reach a durable boundary', flow)
        if number is not None:
            assert fault.failed, (case, points)
        if flow.startswith('restart_') and number is not None and not reply['ok']:
            s.bind(Engine(s.fixture.root / 'state', s.fixture.root / 'evidence'))
        if mode == 'persistent':
            exhaustion = OSWrites(1, mode='persistent')
            with exhaustion.wrap(s.fixture.engine.store):
                d.compare(gaps.checker(case + '/exhausted'))
        # Assert positives before ANY status read; compare the passive view first.
        d.compare(gaps.checker(case + '/live-restored'))
        s.fixture.engine.close()
        s.bind(Engine(s.fixture.root / 'state', s.fixture.root / 'evidence'))
        if s.fixture.engine.store.locked:
            s.fixture.engine.request({'v': 1, 'method': 'call', 'action': 'control_restore_confirm',
                'arguments': {'confirm': 'invalidate earlier approvals'}}, True)
        d.compare(gaps.checker(case + '/crash-restart'))
        return points, cleanups
    finally:
        s.close()


class OwnerStateSweep(unittest.TestCase):
    def test_all_flows_all_storage_modes_independent_views(self):
        gaps, counts = Gaps(recording=True), Counter()
        shard, shards = int(os.environ.get('MAIL_SWEEP_SHARD', '0')), int(os.environ.get('MAIL_SWEEP_SHARDS', '1'))
        for index, flow in enumerate(FLOWS + EXTRA):
            if index % shards != shard:
                continue
            started = time.monotonic()
            points, _ = exercise(flow, gaps=gaps)
            counts['clean'] += 1
            for number, label in enumerate(points, 1):
                if label.endswith('.close'):
                    continue
                for mode in ('single', 'persistent'):
                    with self.subTest(flow=flow, point=number, mode=mode):
                        _, cleanups = exercise(flow, number, mode, gaps=gaps)
                        counts[mode] += 1
                    if mode == 'single':
                        for cleanup_at, _, _ in cleanups:
                            if cleanup_at > number:
                                with self.subTest(flow=flow, point=number, cleanup=cleanup_at):
                                    exercise(flow, number, cleanup_at=cleanup_at, gaps=gaps)
                                    counts['pairs'] += 1
            print(f'Owner oracle flow={flow} points={len(points)} elapsed={time.monotonic()-started:.3f}s', flush=True)
        import base64, gzip, json
        print('OWNER-GAP-DISCOVERY:' + base64.b64encode(gzip.compress(json.dumps(gaps.entries, sort_keys=True).encode())).decode(), flush=True)
        relevant = {key for key in gaps.entries if key.split('/')[0] in (FLOWS + EXTRA)[shard::shards]}
        self.assertEqual(gaps.seen, set())
        print(f'Owner oracle shard={shard}/{shards} modes={dict(counts)} strict expected failures={len(gaps.seen)}', flush=True)
