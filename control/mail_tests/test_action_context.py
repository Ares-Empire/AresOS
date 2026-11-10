"""R2 proofs at the command boundary, including refused context commits."""
import copy
import errno
import unittest
from unittest.mock import patch

from aresos_control.common import digest
from aresos_control.engine import Engine
from owner_state_oracle.driver import Driver
from owner_state_oracle.context import bind, differences, MUTATIONS
from test_owner_state_sweep import OwnerScenario


FLOWS = ('send', 'repair', 'delete_trash', 'delete_permanent', 'unsubscribe_mailto',
         'unsubscribe_https', 'filing_move', 'filing_copy', 'filing_rename', 'draft_append',
         'folder_create', 'folder_delete', 'onboarding', 'flag', 'settings', 'folder_review',
         'testapp_send', 'testapp_delete', 'testapp_config')


class ActionContexts(unittest.TestCase):
    def test_rename_rechecks_uidvalidity_on_the_mutation_connection_before_context(self):
        for failed_result in (False, True):
            with self.subTest(failed_result=failed_result):
                scenario = OwnerScenario('filing_rename')
                try:
                    fixture = scenario.fixture
                    safe_folder, write = fixture.mail.safe_folder, fixture.engine.store.write
                    old = fixture.imap.validities['Source']
                    result_writes = []
                    def recreated(*args, **kwargs):
                        source = safe_folder(*args, **kwargs)
                        fixture.imap.validities['Source'] = old + 1
                        fixture.imap.boxes['Source'] = {1: b'Message-ID: <replacement@mail.invalid>\r\n\r\nReplacement'}
                        return source
                    def persisted(changes, action, *args, **kwargs):
                        if action == 'mail_folder_rename' and any(key.startswith('mail:rename:') and row and row['state'] != 'started'
                                                                for key, row in changes.items()):
                            result_writes.append(True)
                            if failed_result:
                                raise OSError(errno.ENOSPC, 'Synthetic result storage failure')
                        return write(changes, action, *args, **kwargs)
                    driver = Driver(scenario)
                    with patch.object(fixture.mail, 'safe_folder', side_effect=recreated), patch.object(fixture.engine.store, 'write', side_effect=persisted), driver.observe():
                        result = scenario.call()
                    driver.reply(result)
                    self.assertFalse(result['ok'], result)
                    self.assertEqual(result['error']['code'], 'stale_reference', result)
                    self.assertEqual(fixture.imap.validities['Source'], old + 1)
                    self.assertNotIn('Renamed', fixture.imap.boxes)
                    self.assertFalse(any(e['command'] == 'RENAME' for e in driver.oracle.servers))
                    self.assertEqual(sum(e['command'] == 'SELECT' and e.get('folder') == 'Source' for e in driver.oracle.servers), 2)
                    self.assertFalse(any(e['command'] == 'FETCH' for e in driver.oracle.servers))
                    self.assertFalse(any(k.startswith('mail:rename:') for k in driver.snapshot().rows))
                    self.assertFalse(result_writes, 'Stale namespace must stop before context or result storage')
                finally:
                    scenario.close()

    def test_healthy_rename_uses_uid_namespace_without_fetching_any_message_body(self):
        nested = b'Message-ID: <nested@mail.invalid>\r\n\r\nbody\r\n'
        for _ in range(45):
            nested = b'Content-Type: message/rfc822\r\n\r\n' + nested
        excessive = (b'Message-ID: <parts@mail.invalid>\r\nContent-Type: multipart/mixed; boundary=p\r\n\r\n' +
                     (b'--p\r\nContent-Type: text/plain\r\n\r\nx\r\n' * 1100) + b'--p--\r\n')
        oversized = b'Message-ID: <large@mail.invalid>\r\n\r\nsmall fixture body'
        for label, raw in (('oversized', oversized), ('nested', nested), ('excessive-parts', excessive)):
            with self.subTest(message=label):
                scenario = OwnerScenario('filing_rename')
                try:
                    fixture = scenario.fixture
                    fixture.imap.boxes['Source'] = {1: raw}
                    roles = copy.deepcopy(fixture.imap.roles)
                    rename = fixture.imap.rename
                    def ordinary(source, target):
                        answer = rename(source, target)
                        fixture.imap.roles = {**roles, 'Renamed': roles['Source']}
                        fixture.imap.roles.pop('Source')
                        return answer
                    uid = fixture.imap.uid
                    fetches = []
                    def no_fetch(command, *args):
                        if command == 'FETCH':
                            fetches.append(args)
                            if label == 'oversized' and 'RFC822.SIZE' in args[1]:
                                size = fixture.mail.wires.limit + 1
                                return 'OK', [f'1 (UID 1 FLAGS () RFC822.SIZE {size})'.encode()]
                        self.assertNotEqual(command, 'FETCH', 'RENAME must never request message metadata or bodies')
                        return uid(command, *args)
                    # The advertised body exceeds the exact pre-existing wire
                    # limit without allocating a large test message.
                    driver = Driver(scenario)
                    with patch.object(fixture.imap, 'rename', side_effect=ordinary), patch.object(fixture.imap, 'uid', side_effect=no_fetch), driver.observe():
                        result = scenario.call()
                    driver.reply(result)
                    self.assertTrue(result['ok'], result)
                    self.assertEqual(result['data']['state'], 'done', result)
                    self.assertFalse(result['pending'].get('notices'))
                    command = next(e for e in driver.oracle.servers if e['command'] == 'RENAME')
                    _, row = bind(command, driver.oracle.script)
                    self.assertEqual(row['context']['identities'], [{'account': 'box', 'folder': 'Source',
                        'uidvalidity': fixture.imap.validities['Renamed'], 'uid': 1}])
                    self.assertFalse(driver.oracle.context_errors())
                    self.assertFalse(any(e['command'] == 'FETCH' for e in driver.oracle.servers))
                    self.assertEqual(sum(e['command'] == 'SELECT' and e.get('folder') == 'Source' for e in driver.oracle.servers), 2,
                                     'Enumeration plus the R2 namespace check; no body reads')
                    self.assertEqual(fetches, [])
                finally:
                    scenario.close()

    def capture(self, flow, fail=None):
        scenario = OwnerScenario(flow)
        self.addCleanup(scenario.close)
        driver = Driver(scenario)
        store, write = scenario.fixture.engine.store, scenario.fixture.engine.store.write
        blocked = []
        def persist(changes, *args, **kwargs):
            contexts = [row['context'] for row in changes.values() if isinstance(row, dict) and 'context' in row]
            if kwargs.get('intent_context'):
                contexts.append(kwargs['intent_context'])
            if fail and any(context.get('command') == fail for context in contexts):
                blocked.append(copy.deepcopy(contexts))
                raise OSError(errno.ENOSPC, 'Synthetic context commit refused')
            return write(changes, *args, **kwargs)
        with patch.object(store, 'write', side_effect=persist), driver.observe():
            reply = scenario.call()
        driver.reply(reply)
        return scenario, driver, reply, blocked

    def test_each_mutation_has_exact_context_committed_before_the_server(self):
        seen = set()
        for flow in FLOWS:
            with self.subTest(flow=flow):
                scenario, driver, reply, _ = self.capture(flow)
                self.assertTrue(reply['ok'], reply)
                for event in driver.oracle.servers:
                    if event['command'] not in MUTATIONS or event.get('fixture_seed'):
                        continue
                    key, row = bind(event, driver.oracle.script)
                    self.assertIsNotNone(row, (flow, event['command']))
                    self.assertEqual(differences(event, driver.oracle.script, driver.oracle.servers)[1], [], (flow, event['command']))
                    self.assertEqual(row['context']['command'], event['command'])
                    self.assertEqual(row['context_version'], 1)
                    self.assertLessEqual(event['created_before'][key], event['before_seq'])
                    if key.startswith(('intent:', 'mail:')):
                        self.assertGreater(event['created_before'][key], event['call_start_seq'])
                    for field in ('account', 'identities', 'source', 'destination', 'roles', 'recipients', 'arguments'):
                        self.assertIn(field, row['context'])
                    seen.add(event['command'])
                self.assertEqual(driver.oracle.context_errors(), set(), flow)
                scenario.close()
        self.assertGreaterEqual(seen, {'DATA', 'APPEND', 'MOVE', 'COPY', 'STORE', 'EXPUNGE', 'CREATE', 'DELETE', 'RENAME', 'POST', 'RECEIVE', 'CONFIGURE', 'LOCAL_STAGE'})

    def test_a_refused_context_commit_prevents_each_mutation_kind(self):
        cases = (('send', 'DATA'), ('send', 'APPEND'), ('delete_trash', 'MOVE'),
                 ('filing_copy', 'COPY'), ('flag', 'STORE'), ('delete_permanent', 'EXPUNGE'),
                 ('folder_create', 'CREATE'), ('folder_delete', 'DELETE'), ('filing_rename', 'RENAME'),
                 ('unsubscribe_https', 'POST'), ('testapp_send', 'RECEIVE'), ('testapp_config', 'CONFIGURE'),
                 ('testapp_delete', 'LOCAL_DELETE'), ('testapp_send', 'LOCAL_STAGE'), ('onboarding', 'CREATE'), ('onboarding', 'APPEND'),
                 ('repair', 'APPEND'))
        for flow, command in cases:
            with self.subTest(flow=flow, command=command):
                scenario, driver, reply, blocked = self.capture(flow, command)
                self.assertTrue(blocked, (flow, command, reply))
                self.assertFalse(any(event['command'] == command for event in driver.oracle.servers), (flow, command))
                if command == 'LOCAL_DELETE':
                    item_ids = [i['reference']['id'] for i in scenario.args['description']['items']]
                    self.assertTrue(all(i in scenario.fixture.engine.store.get('testapp')['items'] for i in item_ids))
                scenario.close()

    def test_free_attempts_have_distinct_identities_and_full_arguments(self):
        scenario = OwnerScenario('folder_create')
        self.addCleanup(scenario.close)
        engine = scenario.fixture.engine
        write = engine.store.write
        def refuse_result(changes, action, summary, *args, **kwargs):
            if summary == 'Mail change completed':
                raise OSError(errno.EIO, 'Synthetic outcome write failure')
            return write(changes, action, summary, *args, **kwargs)
        with patch.object(engine.store, 'write', side_effect=refuse_result):
            scenario.call()
        prior = dict(engine.store.items('intent:'))
        scenario.args = {'account': 'box', 'name': 'Second'}
        scenario.call()
        self.assertEqual(dict(engine.store.items('intent:')), prior)
        self.assertTrue(prior)
        row = next(iter(prior.values()))
        self.assertEqual(row['arguments'], {'account': 'box', 'name': 'Created'})
        self.assertEqual(row['context']['destination'], 'Created')
        self.assertEqual(row['state'], 'started')

    def test_folded_rename_context_stays_out_of_public_audit_content(self):
        scenario, driver, reply, _ = self.capture('filing_rename')
        self.assertTrue(reply['ok'], reply)
        self.assertTrue(any(row.get('context', {}).get('command') == 'RENAME'
            for key, row in scenario.fixture.engine.store.items('mail:rename:')))
        arguments = {'limit': 10}
        found = False
        while True:
            page = scenario.fixture.engine.dispatch('control_log', arguments)
            for entry in page['items']:
                content = entry.get('untrusted_content', {}).get('rename')
                if content is not None:
                    found = True
                    self.assertNotIn('context', content)
                    self.assertNotIn('context_version', content)
            if page['cursor'] is None:
                break
            arguments['cursor'] = page['cursor']
        self.assertTrue(found)

    def test_old_unfinished_context_warns_finished_old_is_quiet_and_new_work_runs(self):
        scenario = OwnerScenario('send')
        self.addCleanup(scenario.close)
        engine = scenario.fixture.engine
        original = engine.store.get('op:' + scenario.operation_id)
        old = {key: value for key, value in original.items() if key not in {'context', 'context_version', 'roles_before'}}
        old.update(id=old['generation'] + ':legacy', state='reserved')
        old['approval'] = {**old['approval'], 'operation_id': old['id']}
        old['input_hash'] = digest(old['approval'])
        done = copy.deepcopy(old)
        done.update(id=old['generation'] + ':finished', state='done')
        done['approval']['operation_id'] = done['id']
        done['input_hash'] = digest(done['approval'])
        engine.store.write({'op:' + old['id']: old, 'op:' + done['id']: done}, 'fixture', 'Old Mail format without context')
        engine.close()
        scenario.bind(Engine(scenario.fixture.root / 'state', scenario.fixture.root / 'evidence'))
        result = scenario.fixture.engine.request({'v': 1, 'method': 'call', 'action': 'control_pending', 'arguments': {}})
        self.assertTrue(result['ok'], result)
        notices = result['data']['notices']
        self.assertTrue(any(n['untrusted_content'].get('intent_key') == 'op:' + old['id'] and 'not yet checked' in n['untrusted_content']['reason'] for n in notices), notices)
        self.assertFalse(any(n['untrusted_content'].get('intent_key') == 'op:' + done['id'] for n in notices))
        self.assertTrue(scenario.call()['ok'])

    def test_a_finished_source_cannot_cover_another_effect(self):
        from aresos_control.action_context import context, mutation
        from aresos_control.common import Refused
        scenario = OwnerScenario('send')
        self.addCleanup(scenario.close)
        self.assertTrue(scenario.call()['ok'])
        value = context(scenario.fixture.engine.store, 'DATA', 'box')
        reached = []
        with self.assertRaises(Refused):
            with mutation(scenario.fixture.engine.store, value, source_key='op:' + scenario.operation_id):
                reached.append(True)
        self.assertEqual(reached, [])

    def test_reuse_requires_identical_durable_context_and_a_writable_store(self):
        from aresos_control.action_context import context, mutation
        from aresos_control.common import Refused
        scenario = OwnerScenario('send')
        self.addCleanup(scenario.close)
        store = scenario.fixture.engine.store
        key = 'op:' + scenario.operation_id
        row = store.get(key)
        value = context(store, 'DATA', 'box', destination='smtp')
        row.update(state='submitting', context=value, context_version=1)
        store.write({key: row}, 'fixture', 'Synthetic existing pre-command commit', scenario.operation_id)
        sequence = store.sequence
        with mutation(store, value, source_key=key):
            pass
        self.assertEqual(store.sequence, sequence)
        changed = {**value, 'destination': 'changed'}
        with patch.object(store, 'write', side_effect=OSError(errno.ENOSPC, 'Synthetic changed-context failure')):
            with self.assertRaises(OSError):
                with mutation(store, changed, source_key=key):
                    self.fail('A refused replacement context entered the effect')
        self.assertEqual(store.get(key)['context'], value)
        store.write_failed = True
        try:
            with self.assertRaises(Refused):
                with mutation(store, value, source_key=key):
                    self.fail('An incomplete transaction entered the effect')
        finally:
            store.write_failed = False

    def test_local_free_flag_is_committed_before_effect_and_refused_commit_blocks_it(self):
        for fail in (False, True):
            scenario = OwnerScenario('fixture')
            self.addCleanup(scenario.close)
            engine = scenario.fixture.engine
            reference = engine.request({'v': 1, 'method': 'call', 'action': 'testapp_list', 'arguments': {'limit': 1}})['data']['items'][0]['reference']
            args = {'reference': reference, 'flagged': True}
            write = engine.store.write
            sequence = engine.store.sequence
            before_effect = []
            def persist(changes, *values, **kwargs):
                initial = kwargs.get('intent_context', {})
                if fail and initial.get('command') == 'LOCAL_FLAG':
                    raise OSError(errno.ENOSPC, 'Synthetic free-flag context failure')
                if 'testapp' in changes:
                    from owner_state_oracle.records import decode
                    record = decode(scenario.fixture.root / 'state', engine.store.evidence_dir)
                    intents = [row for key, row in record.rows.items() if key.startswith('intent:')]
                    self.assertEqual(len(intents), 1)
                    self.assertEqual(intents[0]['context']['arguments'], args)
                    self.assertEqual(intents[0]['context']['identities'], [reference])
                    before_effect.append(True)
                return write(changes, *values, **kwargs)
            with patch.object(engine.store, 'write', side_effect=persist):
                reply = engine.request({'v': 1, 'method': 'call', 'action': 'testapp_flag', 'arguments': args})
            self.assertEqual(reply['ok'], not fail, reply)
            self.assertEqual(before_effect, [] if fail else [True])
            self.assertEqual(engine.store.get('testapp')['items'][reference['id']]['flagged'], not fail)
            if not fail:
                self.assertEqual(engine.store.sequence - sequence, 2)
                self.assertEqual(engine.store.items('intent:'), [])
            scenario.close()

    def test_store_written_by_pre_stage_two_code_opens_and_accepts_new_operations(self):
        import json
        import sqlite3
        import tempfile
        from pathlib import Path
        from support import WORK
        frozen = json.loads((Path(__file__).parent / 'fixtures/19b-legacy-store.json').read_text())
        with tempfile.TemporaryDirectory(dir=WORK) as directory:
            root = Path(directory)
            (root / 'state').mkdir()
            (root / 'evidence').mkdir()
            with sqlite3.connect(root / 'state/control.sqlite') as database:
                database.executescript(frozen['sql'])
            (root / 'evidence/operations.jsonl').write_text(frozen['journal'])
            engine = Engine(root / 'state', root / 'evidence')
            try:
                reply = engine.request({'v': 1, 'method': 'call', 'action': 'control_pending', 'arguments': {}})
                self.assertTrue(reply['ok'], reply)
                notices = reply['data']['notices']
                for source in ('op:' + frozen['unknown'], frozen['intent']):
                    self.assertTrue(any(n['untrusted_content'].get('intent_key') == source and
                        'not yet checked' in n['untrusted_content']['reason'] for n in notices), (source, notices))
                self.assertFalse(any(n['untrusted_content'].get('intent_key') == 'op:' + frozen['done'] for n in notices))
                arguments = {'account': 'fixture', 'to': ['new-fixture-recipient'], 'cc': [], 'bcc': [],
                    'subject': 'Synthetic new operation', 'text': 'Synthetic body', 'attachments': []}
                prepared = engine.request({'v': 1, 'method': 'call', 'action': 'testapp_prepare_send', 'arguments': arguments})
                self.assertTrue(prepared['ok'], prepared)
                sent = engine.request({'v': 1, 'method': 'call', 'action': 'testapp_send', 'arguments': prepared['data']['approval']})
                self.assertTrue(sent['ok'], sent)
                self.assertEqual(sent['data']['operation']['state'], 'done')
            finally:
                engine.close()

    def test_unrelated_ambiguous_optional_roles_use_observed_context_without_changing_the_action(self):
        scenario = OwnerScenario('folder_create')
        self.addCleanup(scenario.close)
        fixture = scenario.fixture
        names = ('Junkä', 'Junk\"two')
        for number, name in enumerate(names, 20):
            fixture.imap.boxes[name] = {}
            fixture.imap.roles[name] = ['\\Junk']
            fixture.imap.validities[name] = number
        # The owner setup predates these unrelated optional roots. Ordinary
        # folder creation is allowed; its context must retain both observations.
        from aresos_control.mail.transport import quote
        def listed():
            return 'OK', [('(' + ' '.join(flags) + ') ' + ('"."' if name == 'Junkä' else '"/"') + ' ' + quote(name)).encode()
                for name, flags in fixture.imap.roles.items()]
        driver = Driver(scenario)
        with patch.object(fixture.imap, 'list', side_effect=listed), driver.observe():
            reply = scenario.call()
        driver.reply(reply)
        self.assertTrue(reply['ok'], reply)
        event = next(e for e in driver.oracle.servers if e['command'] == 'CREATE')
        key, row = bind(event, driver.oracle.script)
        self.assertEqual(row['context']['roles']['junk'], sorted(names))
        self.assertEqual(row['context']['delimiters']['junk'], ['/', '.'])
        self.assertEqual(driver.oracle.context_errors(), set())
        self.assertEqual(row['context']['destination'], 'Created')


class ContextWriteFences(unittest.TestCase):
    def worker(self, flow, mode='discover', occurrence=0, point='none'):
        from pathlib import Path
        import pickle
        import shutil
        import signal
        import subprocess
        import sys
        import tempfile
        from support import WORK
        with tempfile.TemporaryDirectory(dir=WORK) as directory:
            output = Path(directory) / 'capture.pickle'
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('context_worker.py')),
                flow, mode, str(occurrence), point, str(output)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, -signal.SIGKILL if mode == 'crash' else 0, result.stdout + result.stderr)
            capture = pickle.loads(output.read_bytes())
            root = Path(capture['root'])
            try:
                if mode != 'discover':
                    self.assertTrue(capture['reached'], (flow, mode, occurrence, point))
                for event in capture['servers']:
                    if event['command'] not in MUTATIONS or event.get('fixture_seed'):
                        continue
                    self.assertEqual(differences(event, capture['script'], capture['servers'])[1], [],
                        (flow, mode, occurrence, point, event['command']))
                    key, _ = bind(event, capture['script'])
                    if mode == 'crash' or mode == 'failure' and key in capture['blocked_keys']:
                        self.assertLess(event['write_number'], occurrence,
                            ('command reached server after its context write failed/crashed', flow, occurrence, point, event['command']))
                if mode == 'crash':
                    # Real process death, then normal recovery: it may finish a
                    # prepared local commit, but must never replay an effect.
                    engine = Engine(root / 'state', root / 'evidence')
                    try:
                        for table, rows in capture['receiver'].items():
                            self.assertEqual(engine.receiver.db.execute('SELECT * FROM ' + table).fetchall(), rows)
                    finally:
                        engine.close()
            finally:
                if root.exists():
                    shutil.rmtree(root)
            return capture['writes']

    def test_failure_and_real_crash_at_every_write_of_every_mutation_flow(self):
        counts = {}
        for flow in FLOWS + ('local_flag',):
            count = counts[flow] = self.worker(flow)
            self.assertGreater(count, 0, flow)
            for occurrence in range(1, count + 1):
                for mode, point in (('failure', 'before_write'), ('failure', 'journal_appended'),
                                    ('failure', 'sqlite_prepared'), ('failure', 'sqlite_committed'),
                                    ('failure', 'journal_committed'), ('crash', 'journal_appended'),
                                    ('crash', 'sqlite_prepared'), ('crash', 'sqlite_committed'),
                                    ('crash', 'journal_committed')):
                    with self.subTest(flow=flow, write=occurrence, mode=mode, point=point):
                        self.worker(flow, mode, occurrence, point)
        print('R2 write-fence coverage:', counts, flush=True)
