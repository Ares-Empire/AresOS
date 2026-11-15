"""The owner's excluded-sites list starts as a placeholder that holds Chrome back.

Brief 18c-b, item 1. The image makes the list at first boot from
control/chrome/packaging/aresos-control-chrome.tmpfiles, as content the
service's validator refuses. Until root writes a format 1 list, every Chrome
read and action must answer chrome_settings_unavailable and reach no page.
"""
from pathlib import Path, PurePosixPath
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome import exclusions
from aresos_control.common import Refused, strict_json_loads
from aresos_control.definitions import ACTIONS
from aresos_control.engine import Engine
from test_policy import entry

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / '.work/20-chrome'; WORK.mkdir(parents=True, exist_ok=True)
TMPFILES = ROOT / 'control/chrome/packaging/aresos-control-chrome.tmpfiles'
UNIT = ROOT / 'control/packaging/aresos-toold.service'
PREPARE = ROOT / 'control/chrome/ci/prepare.mjs'
FOLDER = '/var/lib/aresos-control'
READ = 'aresos_control.chrome.exclusions.Boundary.read'
MESSAGE = ('Chrome refuses reads and actions: its owner-only excluded-sites setting is not set up yet, or is missing, '
           'not a valid list, unreadable or unsafe; ask the owner to set it up.')


def tmpfiles_lines():
    return [line.split(None, 6) for line in TMPFILES.read_text().splitlines() if line and not line.startswith('#')]


def placeholder():
    # tmpfiles writes an f line's argument into the new file as it stands.
    return strict_json_loads(tmpfiles_lines()[1][6].encode())


class Placeholder(unittest.TestCase):
    def test_tmpfiles_makes_the_agreed_folder_and_list(self):
        self.assertEqual(tmpfiles_lines(), [
            ['d', FOLDER, '0755', 'root', 'root', '-'],
            ['f', FOLDER + '/chrome-excluded-sites.json', '0640', 'root', 'aresos-tools', '-', '{"format":0,"hosts":[]}'],
        ])
        self.assertEqual(tmpfiles_lines()[1][1], exclusions.SETTING)

    def test_the_placeholder_is_refused_and_an_empty_list_opens_the_tools(self):
        with patch(READ, return_value=placeholder()) as read:
            with self.assertRaises(Refused) as error:
                exclusions.owner_hosts()
            self.assertEqual(read.call_args.args[1], exclusions.SETTING)
        self.assertEqual(error.exception.code, 'chrome_settings_unavailable')
        self.assertEqual(str(error.exception), MESSAGE)
        with patch(READ, return_value=strict_json_loads(b'{"format":1,"hosts":[]}')):
            self.assertEqual(exclusions.owner_hosts(), [])

    def test_the_service_can_read_the_list_and_never_write_it(self):
        unit = {}
        for line in UNIT.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                unit.setdefault(key, []).extend(value.split())
        # The list's group is the service's, so the service can read it.
        self.assertEqual(unit['Group'], [tmpfiles_lines()[1][4]])
        # "Outside ReadWritePaths" only means something while the rest is read-only.
        self.assertEqual(unit['ProtectSystem'], ['strict'])
        writable = [PurePosixPath(path.lstrip('-+')) for path in unit.get('ReadWritePaths', [])]
        writable += [PurePosixPath('/var/lib') / name.split(':')[0] for name in unit.get('StateDirectory', [])]
        self.assertTrue(writable)
        folder = PurePosixPath(FOLDER)
        for path in writable:
            with self.subTest(path=str(path)):
                self.assertFalse(path == folder or path in folder.parents or folder in path.parents,
                                 'The tool service must never be able to write its own excluded-sites list.')


class CiInstall(unittest.TestCase):
    """CI writes the list where the runtime under test reads it, never at a path of its own.

    The latency pair runs this harness over an older runtime as well, whose exclusions.py read the list from
    /etc. With the path written into prepare.mjs that leg's tools answered chrome_settings_unavailable and the
    extension never counted as connected (run 43705955018).
    """
    OLD = '/etc/aresos/control/chrome-excluded-sites.json'

    def prepare(self):
        return PREPARE.read_text()

    def ask(self, tree):
        # The exact command prepare.mjs runs, against the given control/ tree.
        found = re.findall(r"execFileSync\('python3',\[('-B','-c','[^']+')\]", self.prepare())
        self.assertEqual(len(found), 1)
        args = [part.strip("'") for part in found[0].split("','")]
        with tempfile.TemporaryDirectory() as folder:
            done = subprocess.run(['python3', *args], cwd=folder, capture_output=True, text=True, timeout=60,
                                  env={'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'PYTHONPATH': str(tree)})
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.strip()

    def guard(self, path):
        pattern = re.search(r"if\(!/(.+)/\.test\(excludedSites\)\)throw", self.prepare()).group(1)
        return re.fullmatch(pattern, path) is not None

    def test_prepare_names_no_path_for_the_list(self):
        text = self.prepare()
        for literal in ['/var/lib/aresos-control', '/etc/aresos/control', 'chrome-excluded-sites.json\'']:
            self.assertNotIn(literal, text)
        self.assertIn("fs.writeFileSync(excludedSites,JSON.stringify({format:1,hosts:['approval.test']}),{mode:0o640});", text)
        self.assertIn('fs.chownSync(excludedSites,0,1001);', text)

    def test_the_current_runtime_gets_the_list_at_its_own_path(self):
        self.assertEqual(self.ask(ROOT / 'control'), exclusions.SETTING)
        self.assertTrue(self.guard(exclusions.SETTING))

    def test_an_older_runtime_gets_the_list_where_it_reads_it(self):
        source = ROOT / 'control/aresos_control'
        with tempfile.TemporaryDirectory() as folder:
            tree = Path(folder)
            shutil.copytree(source, tree / 'aresos_control', ignore=shutil.ignore_patterns('__pycache__'))
            module = tree / 'aresos_control/chrome/exclusions.py'
            text = module.read_text()
            line = "SETTING = '" + exclusions.SETTING + "'"
            self.assertEqual(text.count(line), 1)
            module.write_text(text.replace(line, "SETTING = '" + self.OLD + "'"))
            self.assertEqual(self.ask(tree), self.OLD)
        self.assertTrue(self.guard(self.OLD))
        self.assertFalse(self.guard('chrome-excluded-sites.json'))
        self.assertFalse(self.guard('/var/lib/aresos-control/other.json'))


class UnconfiguredChrome:
    """Chrome connected, its extension never configured: it answers only what
    background.js answers before `configure` (ack_steps, queued_steps)."""
    session = 'placeholder-session'; version = '157.0.1.0'; connection_identity = 'placeholder-connection'; connection = None

    def __init__(self):
        self.calls = []

    def call(self, name, **args):
        self.calls.append(name)
        if name == 'ack_steps': return {'acknowledged': True}
        if name == 'queued_steps': return []
        raise Refused('refused', 'owner-only excluded-sites setting is unavailable')

    def close(self): pass


PAGE = 'http://page.invalid/'
REFERENCE = {'session': UnconfiguredChrome.session, 'tab': 1, 'frame': 0, 'document': 'document-1', 'view': 'view-1', 'element': 'e1'}
TARGET = {'reference': REFERENCE, 'expected': {}}
PREPARED = object()  # replaced by the approval of an operation the test writes into the store

# Every tool that reads or changes a page, with arguments valid for its input.
SWEPT = {
    'chrome_prepare_read_typed_fields': {'tab': 1},
    'chrome_read_typed_fields': PREPARED,
    'chrome_tabs': {}, 'chrome_downloads': {}, 'chrome_bookmarks': {}, 'chrome_history': {},
    'chrome_take_tab': {'tab': 1}, 'chrome_release_tab': {'tab': 1}, 'chrome_close_tab': {'tab': 1},
    'chrome_open': {'url': PAGE},
    'chrome_navigate': {'tab': 1, 'url': PAGE},
    'chrome_read': {'tab': 1},
    'chrome_find': {'tab': 1, 'text': 'word'},
    'chrome_read_form': {'tab': 1, 'reference': REFERENCE},
    'chrome_wait': {'tab': 1},
    'chrome_click': TARGET,
    'chrome_fill': {**TARGET, 'text': 'text'},
    'chrome_select': {**TARGET, 'value': 'one'},
    'chrome_check': {**TARGET, 'checked': True},
    'chrome_press': {**TARGET, 'key': 'Enter'},
    'chrome_scroll': {**TARGET, 'x': 0, 'y': 10},
    'chrome_upload': {**TARGET, 'path': '/work/fixture.txt'},
    'chrome_fill_form': {'fields': [{**TARGET, 'text': 'text'}]},
    'chrome_dialog': {'tab': 1, 'expected': {}, 'accept': False},
    'chrome_submit': PREPARED,
    'chrome_submit_trusted': PREPARED,
    # Owner-only, but it checks an address against the list.
    'chrome_sites readonly': {'command': 'readonly', 'site': PAGE},
}

# The tools that answer while the list is refused, each with its reason. A
# tool that is in neither table fails the sweep until someone decides.
ANSWER_ANYWAY = {
    'chrome_sites list': "Owner-only; lists his own read-only sites and 'don't ask again' entries from the service's store.",
    'chrome_sites allow': "Owner-only; adds a 'don't ask again' entry to the service's store from a finished operation's record.",
    'chrome_sites revoke': "Owner-only; takes a 'don't ask again' entry back, which only tightens.",
    'chrome_notices': "The service's own warning records; he must be able to read them in any state.",
    'chrome_notice_ack': "Marks one of the service's own warning records as seen.",
    'chrome_operation_status': "The service's own record of an operation.",
    'chrome_drop': 'Cancels prepared work in the store; nothing is dispatched.',
}


class Sweep(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        root = Path(self.temp.name)
        self.mock = patch('aresos_control.engine.Boundary'); self.mock.start()
        self.engine = Engine(root / 'state', root / 'evidence')
        self.chrome = self.engine.adapters['chrome']
        self.bridge = self.chrome.bridge = UnconfiguredChrome()
        record = {'format': 1, 'entries': [entry(build=self.chrome.qualification.build)]}
        self.engine.store.write({'chrome:qualification': record}, 'chrome_test_setup', 'Synthetic qualification, test store only')
        # The adapter keeps the real owner_hosts; the file reads as tmpfiles made it.
        self.read = patch(READ, return_value=placeholder()).start()

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
        tools = {action.name for action in ACTIONS if action.app == 'chrome'}
        named = {name.split()[0] for name in [*SWEPT, *ANSWER_ANYWAY]}
        self.assertEqual(tools - named, set(), 'A Chrome tool is neither refused by the excluded-sites placeholder nor named as '
                         'answering anyway. Decide which (brief 18c-b, item 1) before it ships: a tool that reads or changes a page '
                         'must be refused until the owner has written his list.')
        self.assertEqual(named - tools, set(), 'A swept or named tool is no longer in the tool list.')
        commands = next(action for action in ACTIONS if action.name == 'chrome_sites').input['properties']['command']['enum']
        self.assertEqual({'chrome_sites ' + command for command in commands},
                         {name for name in [*SWEPT, *ANSWER_ANYWAY] if name.startswith('chrome_sites ')})

    def test_every_read_and_action_is_refused_and_reaches_no_page(self):
        for name, arguments in SWEPT.items():
            if arguments is PREPARED:
                arguments = self.prepared('read_typed_fields', self.typed()) if name == 'chrome_read_typed_fields' else self.prepared('submit', self.asking())
            with self.subTest(tool=name):
                result = self.call(name, arguments)
                self.assertFalse(result['ok'], result)
                self.assertEqual(result['error'], {'code': 'chrome_settings_unavailable', 'message': MESSAGE})
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
