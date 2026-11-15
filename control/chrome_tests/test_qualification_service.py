"""Actual service/engine with an in-memory extension peer; starts no browser."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome.adapter import Chrome, view_identity
from aresos_control.chrome.bridge import Bridge
from aresos_control.chrome.policy import CORE_GROUPS, HOSTS
from aresos_control.definitions import ACTIONS
from aresos_control.engine import Engine
import test_engine
from test_policy import entry

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT/'.work/20-chrome'
WORK.mkdir(parents=True, exist_ok=True)


class Service(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=WORK)
        self.root = Path(self.temporary.name)
        self.boundary = patch('aresos_control.engine.Boundary'); self.boundary.start()
        self.engine = Engine(self.root/'state', self.root/'evidence')
        self.chrome = self.engine.adapters['chrome']
        self.peer = test_engine.Browser()
        self.chrome.bridge = self.peer
        self.chrome.read_owner_hosts = lambda: []
        self.build = self.chrome.qualification.build
        self.set_record(entry(build=self.build))

    def tearDown(self):
        self.engine.close(); self.boundary.stop(); self.temporary.cleanup()

    def set_record(self, *entries):
        self.engine.store.write({'chrome:qualification': {'format': 1, 'entries': list(entries)}}, 'chrome_fixture', 'Synthetic qualification state')

    def call(self, verb, args=None, admin=False):
        return self.engine.request({'v':1, 'method':'call', 'action':'chrome_'+verb, 'arguments':args or {}}, admin)

    def target(self):
        frame = self.peer.facts['frames'][0]
        return {'reference': {'session': self.peer.session, 'tab': 1, 'frame': 0, 'document': frame['document'],
                              'view': view_identity(self.peer.facts), 'element': 'e1'}, 'expected': copy.deepcopy(frame['target'])}

    def gmail(self):
        self.chrome.hosts = {**HOSTS, 'gmail': ['mail.test']}
        facts = self.peer.facts; facts['url'] = 'https://mail.test/'
        frame = facts['frames'][0]; frame['url'] = facts['url']
        frame['adapter'] = {'scope':'compose', 'scope_role':'dialog', 'account':'Fixture account', 'to':'recipient@mail.test',
                            'cc':'', 'bcc':'hidden@mail.test', 'subject':'Fixture', 'text':'Draft', 'attachments':[]}

    def test_failed_adapter_falls_back_to_generic_without_disabling_healthy_adapters(self):
        self.gmail()
        failed = entry(build=self.build); failed['adapters']['gmail'] = False
        self.set_record(failed)
        result = self.call('click', self.target()); self.assertTrue(result['ok'], result)
        approval = result['data']['approval']
        self.assertIsNone(approval['description']['untrusted_content']['page_state']['adapter'])
        self.assertIn('editable', approval['description']['untrusted_content']['page_state'])
        self.assertTrue(self.chrome.mode()['adapters']['gemini'])
        self.assertEqual(self.peer.dispatched, [])
        self.assertTrue(self.call('submit', approval)['ok'])
        self.assertEqual(len(self.peer.dispatched), 1)

    def test_each_failed_core_group_refuses_acting_with_reason_and_password_group_refuses_reads(self):
        for group in CORE_GROUPS:
            failed = entry(build=self.build); failed['core'][group] = False; self.set_record(failed)
            with self.subTest(group=group):
                result = self.call('click', self.target())
                self.assertFalse(result['ok'], result); self.assertEqual(result['error']['code'], 'qualification_failed')
                self.assertIn(group, result['error']['message']); self.assertIn(self.peer.version, result['error']['message'])
                read = self.call('read', {'tab': 1})
                self.assertEqual(read['ok'], group != 'password_exclusion', read)
                self.assertEqual(self.peer.dispatched, [])

    def test_failed_patch_stays_off_on_unrecorded_patch_then_passing_patch_restores(self):
        failed = entry(build=self.build); failed['core']['binding'] = False
        self.set_record(failed); self.peer.version = '157.0.1.1'
        self.assertEqual(self.call('click', self.target())['error']['code'], 'qualification_failed')
        self.set_record(failed, entry(build=self.build, version='157.0.1.2'))
        self.peer.version = '157.0.1.3'
        self.assertTrue(self.call('click', self.target())['ok'])
        self.assertFalse(self.chrome.mode()['conservative'])

    def test_conservative_mail_uses_generic_rules_and_suspends_existing_owner_entry(self):
        self.gmail()
        first = self.call('click', self.target())['data']['approval']
        self.assertTrue(self.call('submit', first)['ok'])
        self.assertTrue(self.call('sites', {'command':'allow', 'operation_id':first['operation_id']}, True)['ok'])
        self.peer.version = '999.0.1.0'; self.peer.dispatched.clear()
        result = self.call('click', self.target()); self.assertTrue(result['ok'], result)
        approval = result['data']['approval']
        state = approval['description']['untrusted_content']['page_state']
        self.assertIsNone(state['adapter']); self.assertIsNotNone(state['editable'])
        self.assertFalse(self.call('submit_trusted', approval)['ok']); self.assertEqual(self.peer.dispatched, [])
        self.assertTrue(self.call('submit', approval)['ok']); self.assertEqual(len(self.peer.dispatched), 1)

    def assert_activation(self, verb, change, extra=None):
        self.peer.version = '999.0.1.0'
        frame = self.peer.facts['frames'][0]
        frame['target'].update(name='Continue', label='Continue', **change)
        result = self.call(verb, {**self.target(), **(extra or {})})
        self.assertTrue(result['ok'], result); self.assertIn('approval', result['data'])
        self.assertEqual(self.peer.dispatched, [])
        approved = result['data']['approval']
        self.assertTrue(self.call('submit', approved)['ok']); self.assertEqual(len(self.peer.dispatched), 1)
        self.assertTrue(self.call('submit', approved)['ok']); self.assertEqual(len(self.peer.dispatched), 1)

    def test_conservative_link_click_asks_then_dispatches_once(self):
        self.assert_activation('click', {'href':'https://link.test/'})

    def test_conservative_tick_asks_then_dispatches_once(self):
        self.assert_activation('check', {'role':'checkbox'}, {'checked':True})

    def test_conservative_list_choice_asks_then_dispatches_once(self):
        self.assert_activation('select', {'role':'combobox'}, {'value':'b'})

    def test_conservative_enter_control_asks_then_dispatches_once(self):
        self.assert_activation('press', {}, {'key':'Enter'})

    def test_conservative_space_control_asks_then_dispatches_once(self):
        self.assert_activation('press', {}, {'key':'Space'})

    def test_conservative_search_form_submission_asks_then_dispatches_once(self):
        self.peer.facts['frames'][0]['form'] = {'action':'https://form.test/', 'method':'get', 'search':True, 'fields':[]}
        self.assert_activation('click', {'submit':True})

    def test_conservative_stopped_form_submission_is_prepared_and_resumes_once(self):
        self.peer.version = '999.0.1.0'
        frame = self.peer.facts['frames'][0]
        frame['form'] = {'element':'form', 'action':'https://form.test/', 'method':'post', 'fields':[]}
        for index, kind in enumerate(['native_submit', 'submit_event']):
            step = {'id':str(index), 'kind':kind, 'frame':0, 'document':frame['document'], 'element':'e1'}
            prepared = self.chrome.steps([step], 1)[0]['approval']
            self.assertEqual(len(self.peer.dispatched), index)
            self.assertTrue(self.call('submit', prepared)['ok'])
            self.assertEqual(len(self.peer.dispatched), index+1)
            self.assertEqual(self.peer.dispatched[-1][0], 'resume')
            self.assertEqual(self.peer.dispatched[-1][1]['input']['kind'], kind)

    def test_conservative_read_scroll_type_and_address_navigation_remain_free(self):
        self.peer.version = '999.0.1.0'
        for verb, args in [('read', {'tab':1}), ('scroll', {**self.target(), 'x':0, 'y':100}),
                           ('fill', {**self.target(), 'text':'Fixture text'}), ('navigate', {'tab':1, 'url':'https://destination.test/'})]:
            with self.subTest(verb=verb):
                result = self.call(verb, args)
                self.assertTrue(result['ok'], result); self.assertNotIn('approval', result['data'])
                self.assertIn('chrome_version_notice', result['pending'])
        self.assertEqual([name for name, _ in self.peer.dispatched], ['input', 'input', 'navigate'])

    def test_conservative_readonly_fill_button_upload_refused_independent_of_adapters(self):
        self.peer.version = '999.0.1.0'
        self.assertTrue(self.call('sites', {'command':'readonly', 'site':'https://fixture.test/', 'enabled':True}, True)['ok'])
        for verb, args in [('fill', {'text':'1'}), ('click', {}), ('upload', {'path':'/fixture/file.txt'})]:
            with self.subTest(verb=verb):
                result = self.call(verb, {**self.target(), **args})
                self.assertFalse(result['ok']); self.assertEqual(result['error']['code'], 'readonly_site')
                self.assertIn('chrome_version_notice', result['pending'])
        self.assertEqual(self.peer.dispatched, [])

    def test_every_public_result_including_invalid_calls_carries_conservative_notice(self):
        self.peer.version = '999.0.1.0'
        for action in [action for action in ACTIONS if action.app == 'chrome']:
            with self.subTest(action=action.name):
                result = self.call(action.verb)
                self.assertIn('not qualified', result['pending']['chrome_version_notice'])

    def test_runtime_connection_refresh_for_uncovered_version_once_and_daily_caller(self):
        bridge = Bridge(); bridge.session = 'connection-1'; bridge.version = self.peer.version
        self.chrome.bridge = bridge
        with patch('aresos_control.chrome.uploads.prune'), patch.object(self.chrome.qualification, 'refresh') as refresh:
            self.chrome.maintenance(); refresh.assert_called_with(force=False)
            bridge.version = '158.0.1.0'; self.chrome.maintenance(); refresh.assert_called_with(force=True)
            self.chrome.maintenance(); refresh.assert_called_with(force=False)
            bridge.session = 'connection-2'; self.chrome.maintenance(); refresh.assert_called_with(force=True)
        self.chrome.bridge = self.peer

    def test_installed_build_id_is_used_and_shared_code_new_build_pass_cannot_enable_old_build(self):
        installed = self.root/'runtime'; (installed/'chrome').mkdir(parents=True)
        (installed/'chrome/build-id.json').write_text(json.dumps({'build':'f'*64}))
        with patch('aresos_control.chrome.adapter.RUNTIME', installed):
            chrome = Chrome(self.engine, record={'format':1, 'entries':[]})
        self.assertEqual(chrome.qualification.build, 'f'*64)
        self.set_record(entry(build='e'*64))
        chrome.bridge = self.peer; chrome.read_owner_hosts = lambda: []
        self.assertTrue(chrome.mode()['conservative'])
