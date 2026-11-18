"""Stage 1 independent owner-state comparisons at every inherited fault site."""
from collections import Counter
from ci.mail.tests import flow_partition
from contextlib import contextmanager, ExitStack
import hashlib
import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from aresos_control.engine import Engine
from owner_state_oracle.driver import Driver
from owner_state_oracle.model import Oracle
from owner_state_oracle.gaps import Gaps, owner, BUCKETS, SUITE_BUCKETS
from owner_state_oracle.clock import scripted_calendar, recorded_samples
from owner_state_oracle.identity import scripted_ids, caller_name, caller_directory
from test_review23_sweep import Scenario
from storage_faults import OSWrites

FLOWS = ('send', 'repair', 'delete_trash', 'delete_permanent', 'unsubscribe_mailto', 'unsubscribe_https',
         'status', 'settlement', 'cancel', 'restore', 'attachment_export', 'testapp_export',
         'password', 'filing_move', 'filing_copy', 'filing_rename', 'expiry', 'maintenance',
         'restart_index', 'restart_tail', 'export_rollback', 'archive', 'send_duplicate')
EXTRA = ('draft_append', 'folder_create', 'folder_delete', 'onboarding', 'flag', 'settings', 'folder_review',
         'testapp_send', 'testapp_delete', 'testapp_config', 'local_flag')


def owns_case(case, shard, shards, worker=0, workers=1):
    parts = case.split('/')
    point = int(parts[2])
    if point == 0:
        return True
    # Write transactions repeat syscall patterns. Direct point modulo grouped
    # their expensive rollback/cleanup sites onto the same shard.
    value = int.from_bytes(hashlib.sha256(f'{parts[0]}/{point}'.encode()).digest()[:8])
    return value % shards == shard and (value // shards) % workers == worker


class OwnerScenario(Scenario):
    def advance_archive_clock(self):
        # Age the real commits instead of rewriting their working timestamps
        # away from the independently committed fence.
        self.test_clock += 2

    def __init__(self, flow, point=0, mode='single', cleanup=0, phase='live'):
        try:
            self._initialize(flow, point, mode, cleanup, phase)
        except BaseException:
            try:
                if hasattr(self, 'stack'):
                    self.stack.close()
                if hasattr(self, 'fixture'):
                    self.fixture.doCleanups()
            finally:
                if hasattr(self, 'script_patch'):
                    self.script_patch.stop()
                if hasattr(self, 'clock_patches'):
                    self.clock_patches.close()
            raise

    def _initialize(self, flow, point, mode, cleanup, phase):
        if flow in {'attachment_export', 'testapp_export', 'export_rollback'}:
            name = caller_name(flow, point, mode, cleanup, phase)
            self.caller_directory = lambda **kwargs: caller_directory(name, self.fixture, **kwargs)
        self.test_clock = 1794225600.0
        self.clock_patches = ExitStack()
        self.clock_patches.enter_context(patch('time.time', side_effect=lambda: self.test_clock))
        self.clock_patches.enter_context(scripted_calendar())
        self.clock_patches.enter_context(scripted_ids(flow))
        self.owner_oracle = Oracle()
        request = Engine.request
        def recorded(engine, envelope, *args, **kwargs):
            from storage_faults import ACTIVE
            fault = ACTIVE
            fault_start = len(fault.points) if fault else 0
            self.test_clock += 0.001
            clock = time.time()
            self.owner_oracle.call(envelope.get('action', envelope.get('method')), envelope.get('arguments', {key: value for key, value in envelope.items() if key not in {'v', 'password'}}), clock,
                {'mode': fault.mode, 'at': fault.fail_at, 'cleanup': fault.cleanup_at} if fault else {})
            index = len(self.owner_oracle.script) - 1
            self.owner_oracle.script[index]['parent'] = getattr(self.owner_oracle, 'active_call', None)
            self.owner_oracle.script[index]['request_method'] = envelope.get('method')
            observer = getattr(self.owner_oracle, 'response_observer', None)
            if observer:
                before = observer.__self__.snapshot()
                self.owner_oracle.script[index]['start_seq'] = max(before.committed, default=0)
                self.owner_oracle.script[index]['restore_precondition'] = before.locked
            try:
                with recorded_samples(self.owner_oracle, index):
                    reply = request(engine, envelope, *args, **kwargs)
            except BaseException:
                self.owner_oracle.script[index]['reply'] = 'lost'
                raise
            self.owner_oracle.script[index].update(reply='delivered', result=reply)
            observer = getattr(self.owner_oracle, 'response_observer', None)
            if observer:
                record = observer.__self__.snapshot()
                self.owner_oracle.script[index]['end_seq'] = max(record.committed, default=0)
                self.owner_oracle.script[index]['staged_end_seq'] = max((f['seq'] for f in record.fences), default=0)
                if fault:
                    self.owner_oracle.script[index]['faults']['trace'] = [entry for entry in fault.failures if entry[0] > fault_start]
                    self.owner_oracle.script[index]['faults']['journal'] = [dict(entry) for entry in fault.journal_trace]
                    self.owner_oracle.script[index]['faults']['active_exhaustion'] = fault.mode == 'persistent' and fault.failed
                observer(index, reply)
            return reply
        def scripted(engine, envelope, *args, **kwargs):
            from storage_faults import ACTIVE
            # Healthy requests still supply raw phase evidence (including a
            # later confirm after safe rollback). Never instrument twice.
            if ACTIVE is None and getattr(self.owner_oracle, 'response_observer', None):
                with OSWrites().wrap(engine.store):
                    return recorded(engine, envelope, *args, **kwargs)
            return recorded(engine, envelope, *args, **kwargs)
        self.script_patch = patch.object(Engine, 'request', side_effect=None, autospec=True)
        # Use a real function so Engine's descriptor still binds self.
        self.script_patch = patch.object(Engine, 'request', scripted)
        self.script_patch.start()
        super().__init__('fixture' if flow in EXTRA else flow)
        self.stack.callback(self.script_patch.stop)
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
        elif flow == 'local_flag':
            reference = f.engine.request({'v': 1, 'method': 'call', 'action': 'testapp_list', 'arguments': {'limit': 1}})['data']['items'][0]['reference']
            self.action, self.args = 'testapp_flag', {'reference': reference, 'flagged': True}
        else:
            verb = flow.removeprefix('testapp_')
            arguments = {'account': 'fixture', 'to': ['alpha'], 'cc': [], 'bcc': [], 'subject': 'Synthetic', 'text': 'Exact', 'attachments': []}
            if verb == 'delete':
                listing = f.engine.request({'v': 1, 'method': 'call', 'action': 'testapp_list', 'arguments': {}})['data']
                arguments = {'references': [listing['items'][0]['reference']]}
            approval = f.engine.request({'v': 1, 'method': 'call', 'action': 'testapp_prepare_' + verb, 'arguments': arguments})['data']['approval']
            self.action, self.args, self.operation_id = 'testapp_' + verb, approval, approval['operation_id']

    def close(self):
        try:
            super().close()
        finally:
            self.clock_patches.close()

    def call(self):
        if self.flow == 'onboarding':
            return self.fixture.engine.request({'v': 1, 'method': 'mail_account_add', 'arguments': self.args,
                                                'password': 'Synthetic fixture credential'}, True)
        return super().call()


def exercise(flow, number=None, mode='single', cleanup_at=None, gaps=None, phase='live'):
    s = OwnerScenario(flow, number or 0, mode, cleanup_at or 0, phase)
    gaps.aliases = {}
    try:
        d, fault = Driver(s), OSWrites(number, mode=mode, cleanup_at=cleanup_at)
        d.alias_callback = gaps.bind
        gaps.bind(d.record)
        case = f'{flow}/{mode}/{number or 0}/{cleanup_at or 0}'
        with d.observe(fault), fault.wrap(None if flow.startswith('restart_') else s.fixture.engine.store):
            reply = s.call()
        d.reply(reply, delivered=False if number else True)
        # The oracle keeps a store locked after a confirm met a fault, reading the
        # fault trace only (brief 20-restore-lock-followups, item 1). That holds
        # only while every such fault aborts the confirm.
        for call in d.oracle.script:
            if (call['action'] == 'control_restore_confirm' and call.get('restore_precondition') is True
                    and call.get('faults', {}).get('trace') and call.get('result', {}).get('ok')):
                raise AssertionError((case, 'A confirm that met a storage fault was answered ok; revisit the '
                                      "oracle's rule for an interrupted confirm (driver.interrupted_confirm)", call['faults']['trace']))
        points, cleanups = list(fault.points), list(fault.cleanup_points)
        if number is None:
            assert reply['ok'] or flow == 'password' and reply['error']['code'] == 'server_refused' or flow == 'export_rollback' and reply['error']['code'] == 'storage_limit', (flow, reply)
            assert points, ('Flow did not reach a durable boundary', flow)
        if number is not None:
            assert fault.failed, (case, points)
        if phase == 'crash':
            # Copy the crash bytes BEFORE any view, flush or orderly close.
            # Closing the old handles may roll back; restore the captured bytes
            # so the new Engine sees exactly the injected boundary instead.
            f = s.fixture
            d.restarted()
            with tempfile.TemporaryDirectory(prefix='crash-bytes-', dir=f.root) as temporary:
                saved = __import__('pathlib').Path(temporary)
                for name in ('state', 'evidence'):
                    shutil.copytree(f.root / name, saved / name)
                f.engine.close()
                for name in ('state', 'evidence'):
                    shutil.rmtree(f.root / name)
                    shutil.copytree(saved / name, f.root / name)
            s.bind(Engine(f.root / 'state', f.root / 'evidence'))
            d.started(gaps.checker(case + '/crash-startup'))
            if f.engine.store.locked:
                d.compare(gaps.checker(case + '/crash-locked'))
                f.engine.request({'v': 1, 'method': 'call', 'action': 'control_restore_confirm',
                    'arguments': {'confirm': 'invalidate earlier approvals'}}, True)
            d.compare(gaps.checker(case + '/crash-restart'))
        else:
            if flow.startswith('restart_') and number is not None and not reply['ok']:
                s.bind(Engine(s.fixture.root / 'state', s.fixture.root / 'evidence'))
            if mode == 'persistent':
                # Reads after the fault meet a full disk. Closing a file that
                # was only read cannot fail there (board #185, class D).
                exhaustion = OSWrites(1, mode='persistent', fail_read_only_closes=False)
                with exhaustion.wrap(s.fixture.engine.store):
                    d.compare(gaps.checker(case + '/exhausted'))
            d.compare(gaps.checker(case + '/live-restored'))
        return points, cleanups
    finally:
        s.close()


class OwnerStateSweep(unittest.TestCase):
    def test_startup_replay_proof_precedes_any_automatic_confirm(self):
        # Named mutation target: gaps must appear at startup even if the later
        # sweep confirm repairs the skipped batch completely.
        gaps = Gaps(recording=True)
        proofs = []
        started = Driver.started
        def checked(driver, checker):
            obligation = driver.startup_obligation
            def check(label, expected, actual):
                proofs.append((obligation, label, actual, len(driver.oracle.script)))
                checker(label, expected, actual)
            check.finish = checker.finish
            return started(driver, check)
        with patch.object(Driver, 'started', checked):
            for point in (26, 40, 73):
                for mode in ('single', 'persistent'):
                    exercise('restore', point, mode, gaps=gaps, phase='crash')
        self.assertEqual(len(proofs), 6)
        self.assertTrue(all(obligation is not None and label == 'startup-replay' for obligation, label, _, _ in proofs))
        self.assertEqual([actual for _, _, actual, _ in proofs if actual], [],
                         'startup-replay must finish before any automatic confirm')
        self.assertEqual([key for key in gaps.entries if key.endswith('/startup-replay')], [],
                         'startup-replay must finish before any automatic confirm')

    def test_discovered_staged_restore_interval_and_cleanup_pairs_replay_at_startup(self):
        import json
        points, _ = exercise('restore', gaps=Gaps(recording=True))
        staged, pairs = [], []
        # Discover from crash records, not a hardcoded range of SQL syscall IDs.
        for point in range(1, len(points) + 1):
            scenario = OwnerScenario('restore')
            try:
                driver, fault = Driver(scenario), OSWrites(point)
                with driver.observe(fault), fault.wrap(scenario.fixture.engine.store):
                    result = scenario.call()
                driver.reply(result)
                record = driver.snapshot()
                driver.restarted()
                obligation = driver.startup_obligation
                if obligation:
                    event = json.loads(obligation.event)
                    if record.head[0] < event['seq'] and event['set'].get('generation'):
                        staged.append(point)
                        pairs.extend((point, n) for n, _, _ in fault.cleanup_points if n > point)
            finally:
                scenario.close()
        self.assertTrue(staged)
        self.assertEqual((min(staged), max(staged)), (26, 73))
        gaps = Gaps(recording=True)
        for point in [25, *staged, 74, 75]:
            for mode in ('single', 'persistent'):
                exercise('restore', point, mode, gaps=gaps, phase='crash')
        for point, cleanup in sorted(set(pairs)):
            exercise('restore', point, cleanup_at=cleanup, gaps=gaps, phase='crash')
        self.assertEqual([key for key in gaps.entries if key.endswith(('/startup-replay', '.restore-lock'))], [])
        print('Startup replay interval:', len(staged), 'points;', 2 * (len(staged) + 3),
              'single/persistent cases;', len(set(pairs)), 'cleanup pairs; startup proofs empty', flush=True)

    def test_last_status_committed_lie_is_in_same_comparisons_proof(self):
        scenario = OwnerScenario('send')
        try:
            driver = Driver(scenario)
            with driver.observe():
                reply = scenario.call()
            driver.reply(reply)
            engine = scenario.fixture.engine
            request = engine.request
            def lying_status(envelope, *args, **kwargs):
                result = request(envelope, *args, **kwargs)
                if envelope.get('action') == 'mail_operation_status':
                    key = 'op:' + envelope['arguments']['operation_id']
                    row = engine.store.get(key)
                    row['stages']['message_id'] = '<forged@mail.invalid>'
                    engine.store.write({key: row}, 'fixture', 'Synthetic false status-stage commit')
                return result
            proofs = []
            def check(label, expected, actual):
                if label == 'lifecycle-proof':
                    proofs.append(actual)
            with patch.object(engine, 'request', side_effect=lying_status):
                driver.compare(check)
            self.assertEqual(len(proofs), 1)
            self.assertTrue(any(f.kind == 'unjustified-stage' and f.detail == 'message_id' for f in proofs[0]))
        finally:
            scenario.close()

    def test_constructor_failure_restores_request_and_clock(self):
        import uuid
        request, clock, localtime, nanos, identity = Engine.request, time.time, time.localtime, time.time_ns, uuid.uuid4
        with patch.object(Scenario, '__init__', side_effect=RuntimeError('Synthetic constructor failure')):
            with self.assertRaisesRegex(RuntimeError, 'Synthetic constructor failure'):
                OwnerScenario('send')
        self.assertIs(Engine.request, request)
        self.assertIs(time.time, clock)
        self.assertIs(time.localtime, localtime)
        self.assertIs(time.time_ns, nanos)
        self.assertIs(uuid.uuid4, identity)

    def test_repeated_fault_is_independent_of_ambient_identity_order(self):
        import uuid
        results = []
        for ambient in (1, (1 << 128) - 1):
            gaps = Gaps(recording=True)
            with patch.object(uuid, 'uuid4', return_value=uuid.UUID(int=ambient)) as outside:
                points = exercise('repair', 185, gaps=gaps)
                self.assertIs(uuid.uuid4, outside)
                outside.assert_not_called()
            results.append((points, gaps.entries))
        self.assertEqual(results[0], results[1])

    def test_export_repeated_fault_uses_same_caller_path_and_exact_delta(self):
        results = []
        for _ in range(2):
            gaps = Gaps(recording=True)
            points = exercise('attachment_export', 101, 'persistent', gaps=gaps)
            results.append((points, gaps.entries))
        self.assertEqual(results[0], results[1])

    def test_full_disk_spares_only_closes_of_files_that_were_read(self):
        # Board #185, class D: the exhausted phase must not invent a storage
        # failure where a real full disk has none, nor hide a failing write.
        import errno
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / 'operations.jsonl'
            journal.write_bytes(b'{}\n')
            for spared in (False, True):
                fault = OSWrites(1, mode='persistent', fail_read_only_closes=not spared)
                with fault.wrap():
                    stream = open(journal, 'rb')
                    stream.read()
                    try:
                        stream.close()
                        failed = None
                    except OSError as error:
                        failed = error.errno
                    self.assertTrue(stream.closed)
                self.assertEqual(failed, None if spared else errno.ENOSPC)
                self.assertEqual(fault.points, ['journal.close'])
                self.assertEqual((fault.failed, len(fault.failures)), (not spared, 0 if spared else 1))
            fault = OSWrites(1, mode='persistent', fail_read_only_closes=False)
            with fault.wrap():
                stream = open(journal, 'ab')
                with self.assertRaises(OSError):
                    stream.close()
                with self.assertRaises(OSError):
                    open(Path(directory) / 'new.json', 'w')
            self.assertEqual([label for _, label, _ in fault.failures], ['journal.close', 'file.create'])

    def test_locked_read_records_only_a_write_the_lock_refused(self):
        # Board #185, C2: control_pending is answered during a restore lock;
        # restore_required is permitted only when the read tried to write.
        import sqlite3
        from contextlib import closing
        from aresos_control.common import Refused
        scenario = OwnerScenario('send')
        try:
            f, driver = scenario.fixture, Driver(scenario)
            backup = f.root / 'older.sqlite'
            with closing(sqlite3.connect(backup)) as db:
                f.engine.store.db.backup(db)
            f.engine.store.write({'fixture:later': {'value': 1}}, 'fixture', 'Synthetic later commit')
            f.engine.close()
            (f.root / 'state/control.sqlite').write_bytes(backup.read_bytes())
            scenario.bind(Engine(f.root / 'state', f.root / 'evidence'))
            driver._snapshot_key = None
            self.assertTrue(f.engine.store.locked)
            request = {'v': 1, 'method': 'call', 'action': 'control_pending', 'arguments': {}}
            with driver.observe_view('control_pending', {}):
                reply = f.engine.request(request)
            driver.reply(reply)
            answered = driver.oracle.script[driver.call_index]
            self.assertTrue(reply['ok'], reply)
            self.assertNotIn('lock_refused_write', answered)
            self.assertEqual(driver.oracle.permitted_status(driver.snapshot(), answered), {'allowed'})
            with driver.observe_view('control_pending', {}):
                with self.assertRaises(Refused) as refused:
                    f.engine.store.write({'fixture:during': {'value': 2}}, 'fixture', 'Synthetic write during the lock')
                reply = f.engine.request(request)
            driver.reply(reply)
            self.assertEqual(refused.exception.code, 'restore_required')
            call = driver.oracle.script[driver.call_index]
            self.assertIs(call.get('lock_refused_write'), True)
            self.assertEqual(driver.oracle.permitted_status(driver.snapshot(), call), {'allowed', 'restore_required'})
            self.assertNotIn('lock_refused_write', answered)
            # Another refusal of a write is not the lock's and permits nothing.
            full = Refused('storage_limit', 'Synthetic full disk before the lock check')
            with patch.object(f.engine.store, 'write', side_effect=full), driver.observe_view('control_pending', {}):
                with self.assertRaises(Refused):
                    f.engine.store.write({'fixture:full': {'value': 3}}, 'fixture', 'Synthetic refused write')
                reply = f.engine.request(request)
            driver.reply(reply)
            self.assertNotIn('lock_refused_write', driver.oracle.script[driver.call_index])
        finally:
            scenario.close()

    @staticmethod
    def last_fault_point(flow):
        points, _ = exercise(flow, gaps=Gaps(recording=True))
        return max(number for number, label in enumerate(points, 1) if not label.endswith('.close'))

    def test_confirm_failed_at_its_last_point_keeps_the_lock_until_the_restart(self):
        # Brief 20-restore-lock-followups, item 1: whether or not the commit
        # marker's bytes stayed, the running store keeps its lock, and a restart
        # ends it. The oracle agrees in every phase and every pair case.
        last = self.last_fault_point('restore')
        gaps = Gaps(recording=True)
        for phase in ('live', 'crash'):
            exercise('restore', last, 'persistent', gaps=gaps, phase=phase)
        _, cleanups = exercise('restore', last, gaps=gaps)
        pairs = sorted({number for number, _, _ in cleanups if number > last})
        self.assertTrue(pairs)
        for cleanup_at in pairs:
            for phase in ('live', 'crash'):
                exercise('restore', last, cleanup_at=cleanup_at, gaps=gaps, phase=phase)
        cases = {f'restore/persistent/{last}/0/{phase}' for phase in ('exhausted', 'live-restored', 'crash-restart')}
        cases |= {f'restore/single/{last}/{pair}/{phase}' for pair in pairs for phase in ('live-restored', 'crash-restart')}
        self.assertLessEqual(cases, gaps.executed)
        self.assertEqual([key for key in gaps.entries if key.endswith(('.restore-lock', '.status', '/recovery-holds'))], [])

    def test_harness_refuses_a_confirm_answered_ok_after_a_fault(self):
        # The oracle's rule for an interrupted confirm reads only the fault
        # trace. Were a faulted confirm answered ok, the sweep must stop.
        from aresos_control.common import Refused
        from aresos_control.storage import Store
        original = Store.confirm_restore
        def tolerant(store):
            # A change that tolerates the fault and forgets it, with a bug that
            # keeps the lock: the owner would read "confirmed" and stay locked.
            try:
                return original(store)
            except Refused:
                store.observations = type(store.observations)()
                return {'generation': store.generation, 'unknown': []}
        last = self.last_fault_point('restore')
        with patch.object(Store, 'confirm_restore', tolerant):
            with self.assertRaisesRegex(AssertionError, 'interrupted confirm'):
                exercise('restore', last, gaps=Gaps(recording=True))

    def test_refused_log_under_the_lock_is_seen_as_locked(self):
        # Brief 20-restore-lock-followups, item 2: after a crash the store is
        # locked and refuses `aresos control log` with restore_required, which says so.
        gaps = Gaps(recording=True)
        exercise('cancel', 2, 'persistent', gaps=gaps, phase='crash')
        self.assertIn('cancel/persistent/2/0/crash-locked', gaps.executed)
        self.assertNotIn('cancel/persistent/2/0/crash-locked/aresos log.restore-lock', gaps.entries)

    def test_write_unfinished_at_its_marker_is_not_a_restore(self):
        # Brief 20-restore-lock-followups, item 3: a write that fails at its
        # commit marker leaves the head ahead of the marker. The store is not
        # locked, startup finishes the write, and the oracle agrees.
        last = self.last_fault_point('cancel')
        gaps = Gaps(recording=True)
        exercise('cancel', last, gaps=gaps)
        self.assertIn(f'cancel/single/{last}/0/live-restored', gaps.executed)
        self.assertEqual([key for key in gaps.entries if key.endswith('.restore-lock')], [])

    def test_shards_cover_every_fault_and_keep_its_cleanup_and_crash_cases(self):
        for shards in (1, 2, 4, 12, 24):
            for workers in ((1,) if shards >= 12 else (1, 2, 3)):
                for point in range(1, 102):
                    owners = []
                    for shard in range(shards):
                        for worker in range(workers):
                            cases = [f'flow/{mode}/{point}/{cleanup}/{phase}/view'
                                     for mode in ('single', 'persistent') for cleanup in (0, point + 1)
                                     for phase in ('exhausted', 'live-restored', 'crash-locked', 'crash-restart')]
                            assignment = [owns_case(case, shard, shards, worker, workers) for case in cases]
                            self.assertEqual(len(set(assignment)), 1)
                            if assignment[0]:
                                owners.append((shard, worker))
                    self.assertEqual(len(owners), 1)
                self.assertTrue(all(owns_case('flow/single/0/0/live-restored/view', shard, shards, worker, workers)
                                    for shard in range(shards) for worker in range(workers)))
        for flow in FLOWS + EXTRA:
            count = SUITE_BUCKETS.get(flow, BUCKETS)
            for point in range(1, 21):
                case = f'{flow}/single/{point}/0/live-restored/view'
                self.assertTrue(owns_case(case, int(owner(case)), count, 0, 1))
        self.assertEqual({shard for flow in FLOWS + EXTRA for shard in range(4)
                          if owns_case(f'{flow}/single/1', shard, 4)}, set(range(4)))
        self.assertEqual({shard for point in range(1, 1409, 44) for shard in range(4)
                          if owns_case(f'flow/single/{point}', shard, 4)}, set(range(4)))

    def test_all_flows_all_storage_modes_independent_views(self):
        gaps, counts = Gaps(), Counter()
        shard, shards = int(os.environ.get('MAIL_SWEEP_SHARD', '0')), int(os.environ.get('MAIL_SWEEP_SHARDS', '1'))
        worker, workers = int(os.environ.get('OWNER_SWEEP_WORKER', '0')), int(os.environ.get('OWNER_SWEEP_WORKERS', '1'))
        self.assertGreater(shards, 0)
        self.assertIn(shard, range(shards))
        self.assertGreater(workers, 0)
        self.assertIn(worker, range(workers))
        flows = flow_partition(FLOWS + EXTRA, int(os.environ.get('MAIL_FLOW_GROUP', '0')), int(os.environ.get('MAIL_FLOW_GROUPS', '1')), isolated=('onboarding',))
        for flow in flows:
            started = time.monotonic()
            points, _ = exercise(flow, gaps=gaps)
            counts['clean'] += 1
            for number, label in enumerate(points, 1):
                if label.endswith('.close') or not owns_case(f'{flow}/single/{number}', shard, shards, worker, workers):
                    continue
                for mode in ('single', 'persistent'):
                    with self.subTest(flow=flow, point=number, mode=mode):
                        _, cleanups = exercise(flow, number, mode, gaps=gaps)
                        exercise(flow, number, mode, gaps=gaps, phase='crash')
                        counts[mode] += 1
                        counts['crash'] += 1
                    if mode == 'single':
                        for cleanup_at, _, _ in cleanups:
                            if cleanup_at > number:
                                with self.subTest(flow=flow, point=number, cleanup=cleanup_at):
                                    exercise(flow, number, cleanup_at=cleanup_at, gaps=gaps)
                                    exercise(flow, number, cleanup_at=cleanup_at, gaps=gaps, phase='crash')
                                    counts['pairs'] += 1
            print(f'Owner oracle flow={flow} points={len(points)} elapsed={time.monotonic()-started:.3f}s', flush=True)
        gaps.verify(set(flows), shard, shards, worker, workers)
        print(f'Owner oracle shard={shard}/{shards} worker={worker}/{workers} modes={dict(counts)} strict expected failures={len(gaps.seen)}', flush=True)


class WriteLatchSweep302(unittest.TestCase):
    def test_latch_phases_cleanup_pairs_and_restart(self):
        from owner_state_oracle.records import write_latched
        counts = Counter()
        for flow in ('cancel', 'restore'):
            clean, _ = exercise(flow, gaps=Gaps(recording=True))
            first = clean.index('journal.write') + 1
            marker = max(i for i, label in enumerate(clean, 1) if label == 'journal.write')
            # First fence, index, staging, application, H and final marker.
            main = [i for i, label in enumerate(clean, 1) if label == 'sqlite.main.create']
            sites = (first, first + 1, first + 2, main[0], main[1], main[1] + 6,
                     marker - 1, marker, marker + 1)
            for point in sites:
                _, cleanups = exercise(flow, point, gaps=Gaps(recording=True))
                pairs = sorted({n for n, _, _ in cleanups if n > point})
                variants = [('single', None), ('persistent', None)] + [('single', n) for n in pairs]
                for mode, secondary in variants:
                    with self.subTest(flow=flow, point=point, mode=mode, cleanup=secondary):
                        scenario = OwnerScenario(flow)
                        try:
                            f, driver = scenario.fixture, Driver(scenario)
                            initial = driver.snapshot()
                            fault = OSWrites(point, mode=mode, cleanup_at=secondary)
                            with driver.observe(fault), fault.wrap(f.engine.store):
                                reply = scenario.call()
                            driver.reply(reply)
                            self.assertEqual(reply['error']['code'], 'storage_limit', reply)
                            record = driver.snapshot()
                            history = record.journal_history
                            self.assertTrue(history)
                            self.assertEqual(initial.journal_history, ())
                            self.assertIsNot(initial, record)
                            rollback_sites = {n for n, _, purpose in cleanups if purpose == 'journal truncation'}
                            expected = not (point in (first, first + 1) and mode == 'single' and secondary not in rollback_sites)
                            self.assertEqual(write_latched(record), expected)
                            # A refused retry cannot append or stage a new event.
                            before = (f.root / 'evidence/operations.jsonl').read_bytes()
                            with driver.observe():
                                second = scenario.call()
                            driver.reply(second)
                            if expected:
                                self.assertEqual(second['error']['code'], 'journal_incomplete', second)
                                self.assertEqual((f.root / 'evidence/operations.jsonl').read_bytes(), before)
                            else:
                                self.assertTrue(second['ok'], second)
                                self.assertFalse(write_latched(driver.snapshot()))
                                if flow == 'restore':
                                    self.assertFalse(driver.snapshot().interrupted_confirm)
                                    self.assertFalse(f.engine.store.locked)
                            self.assertEqual(record.journal_history, history)
                            # Freeze the old envelopes before the new service.
                            saved = [(r, r.journal_history) for _, _, r, _ in driver.envelopes]
                            driver.restarted()
                            f.engine.close()
                            scenario.bind(Engine(f.root / 'state', f.root / 'evidence'))
                            self.assertFalse(write_latched(driver.snapshot()))
                            self.assertEqual(driver.snapshot().journal_history, ())
                            for captured, old_history in saved:
                                self.assertEqual(captured.journal_history, old_history)
                            self.assertFalse(scenario.remote, 'No second effect during latch recovery')
                            counts['cases'] += 1
                            counts['cleanup-pairs'] += secondary is not None
                        finally:
                            scenario.close()
        print('302 latch phase/retry/restart cases:', dict(counts), flush=True)

    def test_latch_cases_use_the_same_status_checker_in_every_phase(self):
        gaps = Gaps(recording=True)
        cases = 0
        for flow in ('cancel', 'restore'):
            clean, _ = exercise(flow, gaps=gaps)
            first = clean.index('journal.write') + 1
            marker = max(i for i, label in enumerate(clean, 1) if label == 'journal.write')
            main = [i for i, label in enumerate(clean, 1) if label == 'sqlite.main.create']
            for point in (first, first + 1, first + 2, main[0], main[1], main[1] + 6, marker - 1, marker, marker + 1):
                for mode in ('single', 'persistent'):
                    for phase in ('live', 'crash'):
                        exercise(flow, point, mode, gaps=gaps, phase=phase)
                        cases += 1
                _, cleanups = exercise(flow, point, gaps=gaps)
                for secondary in sorted({n for n, _, _ in cleanups if n > point}):
                    for phase in ('live', 'crash'):
                        exercise(flow, point, cleanup_at=secondary, gaps=gaps, phase=phase)
                        cases += 1
        status = [k for k in gaps.entries if k.endswith('.status')]
        self.assertEqual(status, [])
        self.assertEqual([k for k in gaps.entries if k.endswith('.restore-lock')], [])
        print('302 latch independent-view sweep runs:', cases, 'phases:', len(gaps.executed),
              'other recorded gap keys:', len(gaps.entries), flush=True)
