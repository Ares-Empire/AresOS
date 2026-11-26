"""Actual service/engine with an in-memory extension peer; starts no browser."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome import adapter
from aresos_control.chrome.adapter import Chrome
from aresos_control.chrome.bridge import Bridge
from aresos_control.chrome.policy import CORE_GROUPS, HOSTS
from aresos_control.chrome import qualification as q
from aresos_control.chrome.qualification import switches
from aresos_control.definitions import ACTIONS
from aresos_control.engine import Engine
import test_engine
import qualification_fixture
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
        return test_engine.fixture_call(self.engine, verb, args, admin)

    def target(self):
        return test_engine.fixture_target(self.chrome, self.peer)

    def restart_from_image(self, shipped):
        """Start the service again, keeping its store, from an installed image whose shipped copy is shipped."""
        image = qualification_fixture.fixture_runtime(self.root/'image', baseline=shipped)
        self.engine.close()
        with patch.object(adapter, 'RUNTIME', image):
            self.engine = Engine(self.root/'state', self.root/'evidence')
        self.chrome = self.engine.adapters['chrome']
        self.chrome.bridge = self.peer
        self.chrome.read_owner_hosts = lambda: []
        self.assertEqual(self.chrome.qualification.shipped, shipped)

    def connected(self, version):
        """A real Bridge for one connection, so mode() runs maintenance and its refresh as in the service."""
        bridge = Bridge(); bridge.session = 'connection-1'; bridge.version = version
        bridge.call = lambda name, **arguments: {'configured': True}
        self.chrome.bridge = bridge
        self.addCleanup(setattr, self.chrome, 'bridge', self.peer)
        return bridge

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
        self.assert_activation('select', {'role':'combobox','options':[{'value':'b','label':'B','disabled':False}]}, {'value':'b'})

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
                result = self.engine.request({'v': 1, 'method': 'call', 'action': action.name, 'arguments': {}})
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

    def test_failed_forced_refresh_for_an_uncovered_version_is_attempted_once_per_connection(self):
        # Main fix H2: a rate-limited or failing fetch for an uncovered Chrome
        # version is forced once per (connection, version), then held by the
        # daily gate; the service keeps answering and the record stays.
        bridge = Bridge(); bridge.session = 'connection-1'; bridge.version = '158.0.1.0'
        self.chrome.bridge = bridge
        error = urllib.error.HTTPError('https://api.github.com/private', 403, 'rate limit exceeded', {}, io.BytesIO(b'{"message":"private"}'))
        with patch('aresos_control.chrome.uploads.prune'), patch.object(q.urllib.request, 'urlopen', side_effect=error) as transport:
            for _ in range(3):
                self.chrome.maintenance()
            self.assertEqual(transport.call_count, 1)
            bridge.session = 'connection-2'; self.chrome.maintenance(); self.chrome.maintenance()
            self.assertEqual(transport.call_count, 2)
            bridge.version = '158.0.2.0'; self.chrome.maintenance(); self.chrome.maintenance()
            self.assertEqual(transport.call_count, 3)
        self.assertTrue(switches(self.chrome.qualification.record(), self.build, '158.0.2.0')['conservative'])
        self.assertEqual(self.chrome.qualification.record()['entries'], [entry(build=self.build)])
        result = self.engine.store.get('chrome:qualification_fetch')['result']
        self.assertIn('HTTPError', result); self.assertIn('held record retained', result)
        for private in ['private', 'rate limit', 'api.github.com']:
            self.assertNotIn(private, result)
        self.chrome.bridge = self.peer

    def test_o1_a_pending_row_refuses_where_acting_refuses_when_the_shipped_copy_is_ahead(self):
        # The image's shipped copy holds a later patch of this Chrome that
        # failed binding (#79 O1). In the service an image update comes with a
        # restart, which already makes earlier rows stale; here the held record
        # falls behind the shipped copy within one process, so only the
        # qualification check decides the row, and it must match acting.
        passed = entry(build=self.build, run='shipped')
        failed = entry(build=self.build, version='157.0.1.1', run='shipped'); failed['core']['binding'] = False
        shipped = {'format': 1, 'entries': [passed, failed]}
        self.restart_from_image(shipped)
        self.peer.version = '157.0.1.2'
        for name, behind, code in [('held record behind the shipped copy', [passed], 'qualification_failed'),
                                   ('held record diverged from the shipped copy', [entry(build=self.build, run='diverged')], 'qualification_rollback')]:
            with self.subTest(name):
                # Preparation runs while a fetched patch passes again.
                self.set_record(passed, failed, entry(build=self.build, version='157.0.1.2', run='fetched'))
                prepared = self.call('click', self.target()); self.assertTrue(prepared['ok'], prepared)
                approval = prepared['data']['approval']
                self.set_record(*behind)
                rows = {row['operation_id']: row for row in self.engine.pending('chrome')['items']}
                row = rows[approval['operation_id']]
                self.assertEqual((row['validity'], row.get('refusal_code')), ('refused', code), row)
                with self.assertRaises(q.Refused) as refused:
                    self.chrome.mode(acting=True)
                self.assertEqual(refused.exception.code, code)
                submitted = self.call('submit', approval)
                self.assertFalse(submitted['ok']); self.assertEqual(submitted['error']['code'], code)
                self.assertEqual(self.peer.dispatched, [])

    def test_o2_mode_checks_the_record_only_when_it_changed(self):
        self.chrome.mode(acting=True)
        with patch.object(q, 'validate_record', wraps=q.validate_record) as checked:
            self.chrome.mode(acting=True)
            self.assertEqual(checked.call_count, 0)
        self.connected(self.peer.version)
        offline = urllib.error.URLError('offline fixture')
        with patch('aresos_control.chrome.uploads.prune'), patch.object(q.urllib.request, 'urlopen', side_effect=offline) as transport:
            for refresh in ['daily refresh due', 'refresh gated for the day']:
                with self.subTest(refresh):
                    self.assertFalse(self.chrome.mode(acting=True)['conservative'])
                    with patch.object(q, 'validate_record', wraps=q.validate_record) as checked:
                        self.assertFalse(self.chrome.mode(acting=True)['conservative'])
                        self.assertEqual(checked.call_count, 0)
            self.assertEqual(transport.call_count, 1)
            self.set_record(entry(build=self.build), entry(build=self.build, version='157.0.2.0'))
            with patch.object(q, 'validate_record', wraps=q.validate_record) as checked:
                self.chrome.mode(acting=True)
                self.assertEqual(checked.call_count, 1)
                checked.reset_mock()
                self.chrome.mode(acting=True)
                self.assertEqual(checked.call_count, 0)

    def test_steady_requests_do_no_full_qualification_check(self):
        self.assertTrue(self.call('read', {'tab': 1})['ok'])
        with patch.object(q, 'validate_record', wraps=q.validate_record) as checked:
            read = self.call('read', {'tab': 1}); self.assertTrue(read['ok'], read)
            click = self.call('click', self.target()); self.assertTrue(click['ok'], click)
            approval = click['data']['approval']
            self.assertEqual(self.peer.dispatched, [])
            submitted = self.call('submit', approval); self.assertTrue(submitted['ok'], submitted)
            self.assertEqual(checked.call_count, 0)
        self.assertEqual(len(self.peer.dispatched), 1)

    def test_product_callers_do_not_read_qualification_records(self):
        product = ROOT/'control/aresos_control'
        offenders = [str(path.relative_to(ROOT)) for path in product.rglob('*.py')
                     if path != product/'chrome/qualification.py' and 'qualification.record(' in path.read_text()]
        self.assertEqual(offenders, [])

    def test_o2_mode_trusts_the_record_its_own_refresh_accepted(self):
        # An uncovered Chrome forces a refresh inside mode(); a verified record
        # that covers it applies to that same call, not only to the next one.
        self.connected('158.0.1.0')
        fetched = {'format': 1, 'entries': [entry(build=self.build), entry(build=self.build, version='158.0.1.0', channel='beta', run='fetched')]}
        fetched['entries'][1]['adapters']['gmail'] = False
        refresh = self.chrome.qualification.refresh
        unsigned = lambda **arguments: refresh(verifier=lambda path: None, **arguments)
        with patch('aresos_control.chrome.uploads.prune'), patch.object(self.chrome.qualification, 'refresh', side_effect=unsigned), \
                patch.object(q.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(fetched).encode())):
            mode = self.chrome.mode(acting=True)
        self.assertFalse(mode['conservative']); self.assertFalse(mode['adapters']['gmail']); self.assertTrue(mode['adapters']['github'])
        self.assertEqual(self.chrome.qualification.record(), fetched)
        self.assertEqual(self.engine.store.get('chrome:qualification_fetch')['result'], 'Verified record accepted.')

    def test_o2_refresh_says_whether_the_held_record_may_have_changed(self):
        # True once it writes a verified record, even if that write raises;
        # False whenever it stopped before the write (#93 review 1, finding 1).
        fetched = json.dumps({'format': 1, 'entries': [entry(build=self.build), entry(build=self.build, version='158.0.1.0', run='fetched')]}).encode()
        qualification = self.chrome.qualification
        with patch.object(q.urllib.request, 'urlopen', return_value=io.BytesIO(fetched)):
            self.assertIs(qualification.refresh(now=1000, verifier=lambda path: None), True)
        self.assertEqual(qualification.record(), json.loads(fetched))
        # Gated for the day, then a fetch that fails, a signature that fails, and a record that is not append-only.
        self.assertIs(qualification.refresh(now=2000, verifier=lambda path: None), False)
        with patch.object(q.urllib.request, 'urlopen', side_effect=urllib.error.URLError('offline fixture')):
            self.assertIs(qualification.refresh(now=100000, verifier=lambda path: None), False)
        newer = json.dumps({'format': 1, 'entries': [*json.loads(fetched)['entries'], entry(build=self.build, version='158.0.2.0', run='newer')]}).encode()
        unsigned = Mock(side_effect=q.Refused('qualification_invalid', 'Fixture signature refused.'))
        with patch.object(q.urllib.request, 'urlopen', return_value=io.BytesIO(newer)):
            self.assertIs(qualification.refresh(now=200000, verifier=unsigned), False)
        rewritten = json.dumps({'format': 1, 'entries': [entry(build=self.build, run='rewritten')]}).encode()
        with patch.object(q.urllib.request, 'urlopen', return_value=io.BytesIO(rewritten)):
            self.assertIs(qualification.refresh(now=300000, verifier=lambda path: None), False)
        self.assertEqual(qualification.record(), json.loads(fetched))
        self.assertIn('held record retained', self.engine.store.get('chrome:qualification_fetch')['result'])
        # A write of a verified record that fails before its commit: the record
        # stays, but refresh() cannot tell that from a failure after the commit.
        store = self.engine.store
        write = store.write
        def refused_write(changes, *arguments, **keywords):
            if 'chrome:qualification' in changes:
                raise q.Refused('storage_limit', 'Fixture write refused before its commit.')
            return write(changes, *arguments, **keywords)
        with patch.object(q.urllib.request, 'urlopen', return_value=io.BytesIO(newer)), patch.object(store, 'write', side_effect=refused_write):
            self.assertIs(qualification.refresh(now=400000, verifier=lambda path: None), True)
        self.assertEqual(qualification.record(), json.loads(fetched))
        result = store.get('chrome:qualification_fetch')['result']
        self.assertIn('storage_limit', result); self.assertIn('may have been updated', result); self.assertNotIn('Fixture', result)

    def test_o2_mode_refuses_by_a_fetched_record_whose_write_raised_after_its_commit(self):
        # The store flushes deferred notices after a write commits, and a flush
        # can raise (#93 review 1, finding 1). The fetched record is held by
        # then and fails binding for this Chrome, so this very call must
        # refuse, not act on the record maintenance read before the fetch.
        failed = entry(build=self.build, version='157.0.1.1', run='fetched'); failed['core']['binding'] = False
        fetched = {'format': 1, 'entries': [entry(build=self.build), failed]}
        self.connected('157.0.1.2')
        store = self.engine.store
        flush = store.flush_notices
        raised = []
        def flush_after_the_commit():
            if not raised and store.chrome_state.get('chrome:qualification') == fetched:
                raised.append(1)
                raise q.Refused('storage_limit', 'Notice flush failed after the commit.')
            return flush()
        refresh = self.chrome.qualification.refresh
        unsigned = lambda **arguments: refresh(verifier=lambda path: None, **arguments)
        with patch('aresos_control.chrome.uploads.prune'), patch.object(self.chrome.qualification, 'refresh', side_effect=unsigned), \
                patch.object(store, 'flush_notices', side_effect=flush_after_the_commit), \
                patch.object(q.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(fetched).encode())):
            with self.assertRaises(q.Refused) as refused:
                self.chrome.mode(acting=True)
        self.assertEqual(raised, [1])
        self.assertEqual(refused.exception.code, 'qualification_failed')
        self.assertEqual(self.chrome.qualification.record(), fetched)
        result = store.get('chrome:qualification_fetch')['result']
        self.assertIn('storage_limit', result); self.assertNotIn('held record retained', result)
        self.assertNotIn('Notice flush', result)

    def test_installed_build_id_is_used_and_shared_code_new_build_pass_cannot_enable_old_build(self):
        installed = self.root/'runtime'; (installed/'chrome').mkdir(parents=True)
        (installed/'chrome/build-id.json').write_text(json.dumps({'build':'f'*64}))
        with patch('aresos_control.chrome.adapter.RUNTIME', installed):
            chrome = Chrome(self.engine, record={'format':1, 'entries':[]})
        self.assertEqual(chrome.qualification.build, 'f'*64)
        self.set_record(entry(build='e'*64))
        chrome.bridge = self.peer; chrome.read_owner_hosts = lambda: []
        self.assertTrue(chrome.mode()['conservative'])
