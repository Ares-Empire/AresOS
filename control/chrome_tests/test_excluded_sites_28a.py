"""The never-list gate's sweep over brief 28a's tool list (brief 28a, item 7; review 5, S5).

Brief 18c-b's control/chrome_tests/test_excluded_sites_placeholder.py (PR #76)
calls every Chrome tool while the owner's excluded-sites list is refused and
fails on a tool that is neither refused nor named. It isn't on this branch's
base, so this package carries the same sweep for its own list: the nineteen
tools, the owner-only chrome_sites and brief 20's replaced tools under their
chrome_old_ names. Each must answer chrome_settings_unavailable before any call
to the browser. When PR #76's test with these entries is on main, this copy
goes, so the sweep lives in one place (review 6, N8).
"""
from contextlib import nullcontext
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome import exclusions
from aresos_control.common import Refused
from aresos_control.definitions import ACTIONS
from test_engine import Engine, OLD_TOOLS, old_tools  # the fixture's own qualification baseline
from test_policy import entry

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / '.work/20-chrome'; WORK.mkdir(parents=True, exist_ok=True)
READ = 'aresos_control.chrome.exclusions.Boundary.read'
# What tmpfiles writes at first boot in brief 18c-b: content the validator refuses.
PLACEHOLDER = {'format': 0, 'hosts': []}


class UnconfiguredChrome:
    """Chrome connected, its extension never configured: it answers only what
    background.js answers before `configure` (ack_steps, queued_steps).
    `bounded` is the real bridge's time bound (brief 28, item 4), which the
    new tools open before their first command; it sends nothing."""
    session = 'placeholder-session'; version = '157.0.1.0'; connection_identity = 'placeholder-connection'; connection = None

    def __init__(self):
        self.calls = []

    def call(self, name, **args):
        self.calls.append(name)
        if name == 'ack_steps': return {'acknowledged': True}
        if name == 'queued_steps': return []
        raise Refused('refused', 'owner-only excluded-sites setting is unavailable')

    def bounded(self, end):
        return nullcontext()

    def close(self): pass


PAGE = 'http://page.invalid/'
REF = 'kqtvm5'
REFERENCE = {'session': UnconfiguredChrome.session, 'tab': 1, 'frame': 0, 'document': 'document-1', 'view': 'view-1', 'element': 'e1'}
TARGET = {'reference': REFERENCE, 'expected': {}}
PREPARED = object()  # replaced by the approval of an operation the test writes into the store

# Every tool that reads or changes a page, with arguments valid for its input.
SWEPT = {
    'chrome_read': {'tab': 1},
    'chrome_tabs': {},
    'chrome_open': {'url': PAGE},
    'chrome_go': {'tab': 1, 'url': PAGE},
    'chrome_do': {'tab': 1, 'steps': [{'do': 'click', 'ref': REF}]},
    'chrome_show': {'tab': 1},
    'chrome_close': {'tabs': [1]},
    'chrome_take': {'tab': 1, 'seen': REF},
    'chrome_release': {'tab': 1},
    'chrome_library': {'kind': 'history'},
    'chrome_upload': {'tab': 1, 'ref': REF, 'path': '/work/fixture.txt'},
    'chrome_prepare_read_typed_fields': {'tab': 1},
    'chrome_read_typed_fields': PREPARED,
    'chrome_submit': PREPARED,
    'chrome_submit_trusted': PREPARED,
    # Owner-only, but it checks an address against the list.
    'chrome_sites readonly': {'command': 'readonly', 'site': PAGE},
    # Brief 20's replaced tools, for as long as the CI-only switch offers them (item 8, step 3 removes them).
    'chrome_old_tabs': {}, 'chrome_old_downloads': {}, 'chrome_old_bookmarks': {}, 'chrome_old_history': {},
    'chrome_old_take_tab': {'tab': 1}, 'chrome_old_release_tab': {'tab': 1}, 'chrome_old_close_tab': {'tab': 1},
    'chrome_old_open': {'url': PAGE},
    'chrome_old_navigate': {'tab': 1, 'url': PAGE},
    'chrome_old_read': {'tab': 1},
    'chrome_old_find': {'tab': 1, 'text': 'word'},
    'chrome_old_read_form': {'tab': 1, 'reference': REFERENCE},
    'chrome_old_wait': {'tab': 1},
    'chrome_old_click': TARGET,
    'chrome_old_fill': {**TARGET, 'text': 'text'},
    'chrome_old_select': {**TARGET, 'value': 'one'},
    'chrome_old_check': {**TARGET, 'checked': True},
    'chrome_old_press': {**TARGET, 'key': 'Enter'},
    'chrome_old_scroll': {**TARGET, 'x': 0, 'y': 10},
    'chrome_old_upload': {**TARGET, 'path': '/work/fixture.txt'},
    'chrome_old_fill_form': {'fields': [{**TARGET, 'text': 'text'}]},
    'chrome_old_dialog': {'tab': 1, 'expected': {}, 'accept': False},
}

# The tools that answer while the list is refused, each with its reason: brief
# 18c-b's exceptions, unchanged. A tool in neither table fails the sweep.
ANSWER_ANYWAY = {
    'chrome_sites list': "Owner-only; lists his own read-only sites and 'don't ask again' entries from the service's store.",
    'chrome_sites allow': "Owner-only; adds a 'don't ask again' entry to the service's store from a finished operation's record.",
    'chrome_sites revoke': "Owner-only; takes a 'don't ask again' entry back, which only tightens.",
    'chrome_notices': "The service's own warning records; he must be able to read them in any state.",
    'chrome_notice_ack': "Marks one of the service's own warning records as seen.",
    'chrome_operation_status': "The service's own record of an operation.",
    'chrome_drop': 'Cancels prepared work in the store; nothing is dispatched.',
}


def refusal():
    """The refusal the real owner_hosts gives for the placeholder list."""
    with patch(READ, return_value=PLACEHOLDER):
        try:
            exclusions.owner_hosts()
        except Refused as exc:
            return {'code': exc.code, 'message': str(exc)}
    raise AssertionError('the placeholder list was accepted')


class Sweep(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        root = Path(self.temp.name)
        self.mock = patch('aresos_control.engine.Boundary'); self.mock.start()
        old_tools().start()
        self.engine = Engine(root / 'state', root / 'evidence')
        self.chrome = self.engine.adapters['chrome']
        self.bridge = self.chrome.bridge = UnconfiguredChrome()
        record = {'format': 1, 'entries': [entry(build=self.chrome.qualification.build)]}
        self.engine.store.write({'chrome:qualification': record}, 'chrome_test_setup', 'Synthetic qualification, test store only')
        # The adapter keeps the real owner_hosts; the file reads as the placeholder.
        self.read = patch(READ, return_value=PLACEHOLDER).start()

    def tearDown(self):
        patch.stopall(); self.engine.close(); self.temp.cleanup()

    def call(self, name, arguments):
        tool = name.split()[0]
        return self.engine.request({'v': 1, 'method': 'call', 'action': tool, 'arguments': arguments}, admin=tool == 'chrome_sites')

    def prepared(self, verb, payload, state=None):
        """A prepared operation as the engine's own reserve writes it. The
        adapter's prepare reads the page, which the gate never allows, so the
        test supplies what it would have returned."""
        prepare = (verb + ' this synthetic operation?', {'action': 'chrome_' + verb, 'untrusted_content': {}},
                   {'process_session': self.chrome.process_session, **payload})
        with patch.object(self.chrome, 'prepare', return_value=prepare):
            approval = self.engine.reserve('chrome', verb, {})['approval']
        if state:
            operation = self.engine.operation(approval['operation_id'], 'chrome')
            operation['state'] = state
            self.engine.store.write({'op:' + operation['id']: operation}, 'chrome_test_setup', 'Synthetic finished operation')
        return approval

    def asking(self):
        site = {'site': 'gmail', 'kind': 'gmail_send', 'effect': 'send', 'trusted': True, 'kind_hash': 'synthetic', 'account': None, 'parameters': {}}
        binding = {'session': self.bridge.session, 'tab': 1, 'url': PAGE, 'frame_url': PAGE, 'target': {}, 'form': None}
        return {'reference': REFERENCE, 'input': {'verb': 'click'}, 'kind': 'send', 'adapter': site, 'binding': binding}

    def typed(self):
        binding = {'session': self.bridge.session, 'tab': 1, 'url': PAGE, 'title': 'Synthetic', 'frames': []}
        return {'typed_read': True, 'read_connection': self.bridge.connection_identity, 'binding': binding}

    def test_the_two_tables_cover_the_tool_list_exactly(self):
        tools = {action.name for action in ACTIONS if action.app == 'chrome'} | set(OLD_TOOLS)
        named = {name.split()[0] for name in [*SWEPT, *ANSWER_ANYWAY]}
        self.assertEqual(tools - named, set(), 'A Chrome tool is neither refused by the excluded-sites placeholder nor named as '
                         'answering anyway. Decide which (brief 18c-b, item 1) before it ships: a tool that reads or changes a page '
                         'must be refused until the owner has written his list.')
        self.assertEqual(named - tools, set(), 'A swept or named tool is no longer in the tool list.')
        commands = next(action for action in ACTIONS if action.name == 'chrome_sites').input['properties']['command']['enum']
        self.assertEqual({'chrome_sites ' + command for command in commands},
                         {name for name in [*SWEPT, *ANSWER_ANYWAY] if name.startswith('chrome_sites ')})

    def test_every_read_and_action_is_refused_and_reaches_no_page(self):
        expected = refusal()
        self.assertEqual(expected['code'], 'chrome_settings_unavailable')
        for name, arguments in SWEPT.items():
            if arguments is PREPARED:
                arguments = self.prepared('read_typed_fields', self.typed()) if name == 'chrome_read_typed_fields' else self.prepared('submit', self.asking())
            with self.subTest(tool=name):
                result = self.call(name, arguments)
                self.assertFalse(result['ok'], result)
                self.assertEqual(result['error'], expected)
        # The refusals came from the real owner_hosts reading the list's path.
        self.assertEqual({call.args[1] for call in self.read.call_args_list}, {exclusions.SETTING})
        self.assertNotIn('configure', self.bridge.calls)
        self.assertLessEqual(set(self.bridge.calls), {'ack_steps', 'queued_steps'})

    def test_the_named_tools_answer_without_reaching_a_page(self):
        finished = self.prepared('submit', self.asking(), state='done')
        dropped = {'operation_id': self.prepared('submit', self.asking())['operation_id']}
        answers = {}
        def answer(name, arguments):
            with self.subTest(tool=name):
                result = self.call(name, arguments)
                self.assertTrue(result['ok'], result)
                answers[name] = result['data']
        answer('chrome_sites list', {'command': 'list'})
        answer('chrome_sites allow', {'command': 'allow', 'operation_id': finished['operation_id']})
        answer('chrome_sites revoke', {'command': 'revoke', 'id': answers.get('chrome_sites allow', {}).get('id', 'missing')})
        answer('chrome_drop', dropped)
        answer('chrome_operation_status', dropped)
        answer('chrome_notices', {})
        answer('chrome_notice_ack', dropped)
        self.assertEqual(set(answers), set(ANSWER_ANYWAY))
        self.assertNotIn('configure', self.bridge.calls)
        self.assertLessEqual(set(self.bridge.calls), {'ack_steps', 'queued_steps'})


if __name__ == '__main__':
    unittest.main()
