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

    def test_local_free_flag_is_committed_before_effect_and_refused_commit_blocks_it(self):
        for fail in (False, True):
            scenario = OwnerScenario('fixture')
            self.addCleanup(scenario.close)
            engine = scenario.fixture.engine
            reference = engine.request({'v': 1, 'method': 'call', 'action': 'testapp_list', 'arguments': {'limit': 1}})['data']['items'][0]['reference']
            args = {'reference': reference, 'flagged': True}
            write = engine.store.write
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
