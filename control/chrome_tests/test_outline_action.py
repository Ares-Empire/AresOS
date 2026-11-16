"""Brief 28, item 6: chrome_outline, the new read behind its test-only switch.

`Switch` starts Python processes of its own, because the catalogue is built
when `aresos_control.definitions` is imported: without the switch the action
exists nowhere (the catalogue, the tool list, the proxy, the command, the
engine, every generated file); with it, it reaches the adapter through the
engine. `Adapter` calls the adapter directly, which works whatever the switch
says, with a fake bridge that answers with the node lists of view_fixtures.py.
"""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.common import RESULT_LIMIT, Refused, canonical, validate
from aresos_control.chrome.adapter import PENDING_DRIFT
from aresos_control.chrome.definitions import OUTLINE, OUTLINE_SWITCH
from aresos_control.engine import Engine
from test_engine import WORK, Browser
from test_policy import entry
from view_fixtures import F3_UNIQUE, f1, f2, f3, f4, frame, node, reply

ROOT = Path(__file__).resolve().parents[2]


def fixture(make=f1, tab=1, **more):
    """A view_fixtures reply as the fake extension session sends it for this tab."""
    return {**make(), 'session': Browser.session, 'tab': tab, **more}


def small(*texts, tab=1):
    return {**reply([node(index + 1, 'p', text=[text]) for index, text in enumerate(texts)]),
            'session': Browser.session, 'tab': tab}


class Outlines(Browser):
    """The extension's three read-only commands of brief 28 on top of test_engine's fake browser."""

    def __init__(self):
        super().__init__()
        self.outlines = {1: fixture()}
        self.tokens = {}
        self.refusals = {}
        self.options = None
        self.calls = []
        self.on_state = None

    def call(self, name, **args):
        tab = args.get('tab')
        if name in {'outline', 'page_state', 'options', 'queued_steps'}:
            self.calls.append((name, tab))
        if tab in self.refusals and name in {'outline', 'page_state'}:
            raise self.refusals[tab]
        if name == 'outline':
            return copy.deepcopy(self.outlines[tab])
        if name == 'page_state':
            if self.on_state:
                self.on_state(sum(1 for call in self.calls if call == ('page_state', tab)))
            if self.outlines[tab].get('dialog'):
                return {'session': self.session, 'tab': tab, 'dialog': True}
            return {'session': self.session, 'tab': tab, 'dialog': False, 'token': self.tokens.get(tab, 'token-1')}
        if name == 'options':
            return {'session': self.session, 'tab': tab, 'frame': args['frame'], 'document': args['document'],
                    'reader': args['reader'], 'options': copy.deepcopy(self.options)}
        return super().call(name, **args)

    def named(self, name):
        return [call for call in self.calls if call[0] == name]


def engine_with(root, browser, record=None):
    """An engine as test_engine.Operations builds it, with this fake browser."""
    engine = Engine(root / 'state', root / 'evidence')
    chrome = engine.adapters['chrome']
    chrome.bridge = browser
    chrome.read_owner_hosts = lambda: []
    if record is None:
        record = {'format': 1, 'entries': [entry(build=chrome.qualification.build)]}
    engine.store.write({'chrome:qualification': record}, 'chrome_test_setup', 'Synthetic qualification, test store only')
    return engine


# --- the switch, in processes of their own ---------------------------------

PROBE = r'''
import contextlib, io, json, sys, tempfile
from pathlib import Path
from unittest.mock import patch
patch('aresos_control.engine.Boundary').start()
from aresos_control.common import canonical
from aresos_control.definitions import BY_NAME, tools_for
from aresos_control.proxy import Proxy
from aresos_control import cli
import test_outline_action as here

def code(run):
    try:
        result = run()
    except SystemExit as exc:
        return 'exit: ' + str(exc)
    except Exception as exc:
        return type(exc).__name__
    if not isinstance(result, dict):
        return result
    return result['error']['code'] if 'error' in result else 'sent ' + result['data']['sent']

class Service:
    """The service's socket as the proxy's client sees it: what reaches it is recorded."""
    sent = []
    def __init__(self, path):
        pass
    def request(self, request):
        return {'ok': True, 'data': {'items': [], 'total': 0, 'cursor': None}}
    def call(self, name, arguments):
        Service.sent.append(name)
        return {'ok': True, 'data': {'sent': name}, 'pending': {}}

patch('aresos_control.proxy.Client', Service).start()
config = {'act_socket': 'unused', 'admin_socket': 'unused'}
out = {'catalogue': 'chrome_outline' in BY_NAME, 'tools': [tool['name'] for tool in tools_for('chrome')].count('outline'),
       'proxy': code(lambda: Proxy('chrome', config).call('outline', {'tab': 1}))}
printed = io.StringIO()
with contextlib.redirect_stdout(printed):
    out['command_exit'] = code(lambda: cli.main(config, ['chrome', 'outline', '--input', '{"tab": 1}']))
out['command'] = code(lambda: json.loads(printed.getvalue()))
out['sent'] = Service.sent
sys.path.insert(0, str(here.ROOT / 'control'))
import generate
out['generate'] = code(lambda: generate.generated() and 'generated')

with tempfile.TemporaryDirectory(dir=here.WORK) as temp:
    browser = here.Outlines()
    # No entry for this build: the version notice is on, in data and in pending.
    engine = here.engine_with(Path(temp), browser, {'format': 1, 'entries': []})
    chrome = engine.adapters['chrome']
    original = engine.pending
    def pending(app=None, args=None, resolve_checks=True):
        result = original(app, args, resolve_checks)
        return {**result, 'padding': 'x' * 30000} if app == 'chrome' else result
    engine.pending = pending
    try:
        result = engine.request({'v': 1, 'method': 'call', 'action': 'chrome_outline',
                                 'arguments': {'tab': 1, 'full': True, 'max': 40000}})
        out['engine'] = {'ok': result['ok'], 'error': result.get('error'), 'bounds': 'bounds' in result,
                         'notice': result.get('pending', {}).get('chrome_version_notice') is not None,
                         'sent': len(canonical(result).encode())}
        if result['ok']:
            measured = chrome.outline_measure(result['data']['version_notice'])(result['data']['reads'])
            out['engine'].update(measured=measured, characters=result['data']['reads'][0]['characters'])
    finally:
        engine.close()
print(json.dumps(out))
'''


def probe(switch):
    environment = {key: value for key, value in os.environ.items() if key != OUTLINE_SWITCH}
    environment.update(PYTHONPATH=os.pathsep.join([str(ROOT / 'control'), str(ROOT / 'control/chrome_tests')]),
                       PYTHONDONTWRITEBYTECODE='1')
    if switch:
        environment[OUTLINE_SWITCH] = '1'
    done = subprocess.run([sys.executable, '-c', PROBE], cwd=ROOT, env=environment, capture_output=True, text=True, timeout=300)
    if done.returncode:
        raise AssertionError(done.stderr[-4000:])
    return json.loads(done.stdout.strip().splitlines()[-1])


class Switch(unittest.TestCase):
    def test_without_the_switch_the_action_exists_nowhere(self):
        found = probe(False)
        self.assertEqual((found['catalogue'], found['tools']), (False, 0))
        self.assertEqual((found['proxy'], found['command'], found['command_exit']), ('permission_denied', 'permission_denied', 1))
        self.assertEqual(found['sent'], [])  # nothing reached the service's socket
        self.assertEqual(found['generate'], 'generated')
        # The engine refuses it as an action it doesn't know, before any adapter.
        self.assertFalse(found['engine']['ok'])
        self.assertEqual(found['engine']['error'], {'code': 'invalid_input', 'message': 'Unknown action; inspect the tool list.'})

    def test_with_the_switch_it_reaches_the_adapter_through_the_engine(self):
        found = probe(True)
        self.assertEqual((found['catalogue'], found['tools']), (True, 1))
        # The MCP proxy and the aresos command know it and send it on to the service.
        self.assertEqual((found['proxy'], found['command'], found['command_exit']), ('sent chrome_outline', 'sent chrome_outline', 0))
        self.assertEqual(found['sent'], ['chrome_outline', 'chrome_outline'])
        self.assertTrue(found['generate'].startswith('exit: Refused: unset ' + OUTLINE_SWITCH), found['generate'])
        result = found['engine']
        self.assertTrue(result['ok'], result)
        # Measured as sent: the reads, both version notices and a pending part of 30,000 bytes. The page
        # shrank to fit, nothing was shortened afterwards, and the measure is exactly what was sent.
        self.assertTrue(result['notice'])
        self.assertFalse(result['bounds'])
        self.assertEqual(result['measured'], result['sent'])
        self.assertLessEqual(result['sent'], RESULT_LIMIT - PENDING_DRIFT)
        self.assertLess(result['characters'], 20000)

    def test_generate_refuses_to_run_with_the_switch_set(self):
        environment = {**os.environ, OUTLINE_SWITCH: '0', 'PYTHONPATH': str(ROOT / 'control')}
        done = subprocess.run([sys.executable, 'control/generate.py', '--check'], cwd=ROOT, env=environment,
                              capture_output=True, text=True, timeout=120)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('Refused: unset ' + OUTLINE_SWITCH, done.stderr)

    def test_no_generated_file_names_the_action(self):
        tools = json.loads((ROOT / 'control/generated/chrome-tools.json').read_text())
        self.assertNotIn('outline', [tool['name'] for tool in tools])
        files = [*sorted((ROOT / 'control/generated').iterdir()), *sorted((ROOT / 'control/settings').iterdir()),
                 ROOT / 'docs/control/TOOLS.md']
        for path in files:
            text = path.read_text()
            for word in ('chrome_outline', 'chrome outline', 'mcp__chrome__outline', OUTLINE_SWITCH):
                self.assertNotIn(word, text, path)

    def test_the_packaged_entries_cannot_pass_it_on(self):
        start = '/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 /usr/bin/python3 -I -S /usr/libexec/aresos-control/launch.py '
        unit = (ROOT / 'control/packaging/aresos-toold.service').read_text()
        self.assertIn('\nExecStart=' + start + 'service\n', unit)
        self.assertEqual(unit.count('ExecStart'), 1)
        for name, role in (('aresos-toold', 'service'), ('aresos', 'cli'), ('aresos-mcp', 'proxy')):
            lines = (ROOT / 'control/packaging' / name).read_text().splitlines()
            self.assertEqual([line for line in lines if line.startswith('exec ')], ['exec ' + start + role + ('' if role == 'service' else ' "$@"')])
        for path in sorted((ROOT / 'control/packaging').iterdir()):
            text = path.read_text()
            self.assertNotIn(OUTLINE_SWITCH, text, path)
            self.assertNotIn('Environment', text, path)

    def test_the_ci_container_sets_it_for_the_service_and_the_browser_only(self):
        run = (ROOT / 'control/chrome/ci/run.sh').read_text()
        lines = [line for line in run.splitlines() if OUTLINE_SWITCH in line and not line.startswith('#')]
        self.assertEqual(len(lines), 2)
        self.assertIn(OUTLINE_SWITCH + '=1 FIXTURE_LOG_DIR="$FIXTURE_LOG_DIR" python3 control/chrome/ci/service.py', lines[0])
        self.assertTrue(lines[1].startswith('runuser -u owner -- env GITHUB_ACTIONS=true ' + OUTLINE_SWITCH + '=1 dbus-run-session'))
        self.assertLess(run.index(lines[1]), run.index('node control/chrome/ci/browser.mjs'))
        # The generated-file check and the Python tests run without it.
        for command in ('python3 control/generate.py --check', 'python3 -m unittest'):
            self.assertNotIn(OUTLINE_SWITCH, ''.join(line for line in run.splitlines() if command in line))
        self.assertNotIn('export ' + OUTLINE_SWITCH, run)
        dockerfile = (ROOT / 'control/chrome/ci/Dockerfile').read_text()
        self.assertNotIn(OUTLINE_SWITCH, dockerfile)


# --- the adapter, with a fake bridge -------------------------------------------

class Adapter(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.mock = patch('aresos_control.engine.Boundary')
        self.mock.start()
        self.browser = Outlines()
        self.engine = engine_with(Path(self.temp.name), self.browser)
        self.chrome = self.engine.adapters['chrome']

    def tearDown(self):
        self.engine.close()
        self.mock.stop()
        self.temp.cleanup()

    def read(self, **args):
        return self.chrome.call('outline', args)

    def outline(self, **args):
        reads = self.read(**args)['reads']
        self.assertEqual(len(reads), 1)
        self.assertNotIn('error', reads[0], reads[0])
        return reads[0]

    def refused(self, code, **args):
        with self.assertRaises(Refused) as caught:
            self.read(**args)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        return caught.exception

    def reference(self, text, start):
        return re.search(r'^\s*%s.* ([b-df-hj-np-tv-z]{5}\d+)$' % re.escape(start), text, re.MULTILINE).group(1)

    def test_one_tab_read_in_the_view_modules_order(self):
        result = self.read(tab=1)
        self.assertEqual(set(result), {'reads', 'version_notice'})
        read = result['reads'][0]
        self.assertEqual(set(read), {'tab', 'whose', 'characters', 'total', 'cursor', 'mid_line', 'typed_fields', 'untrusted_content'})
        self.assertEqual((read['tab'], read['whose'], read['cursor'], read['mid_line'], read['typed_fields']), (1, 'claude', None, False, 0))
        content = read['untrusted_content']
        self.assertEqual((content['url'], content['title'], content['scroll'], content['dialog']),
                         ('fixture.example/long', 'Long', '0/3200', None))  # the public form
        lines = content['outline'].split('\n')
        self.assertEqual(len(lines), 5 + 1 + 1 + 40 + 1)  # as test_view_budgets reads F1 first
        self.assertEqual(read['characters'], read['total'])
        # The token comes just before the outline; the queued steps after it, as brief 20's read.
        self.assertEqual(self.browser.calls, [('page_state', 1), ('outline', 1), ('queued_steps', 1)])

    def test_the_table_is_made_at_the_first_read_and_kept(self):
        # Building an engine reads no system randomness: the Mail sweeps reject every such read there.
        def refuse(*args, **kwargs):
            raise AssertionError('system randomness read while the engine was built')
        with patch('random.SystemRandom.getrandbits', refuse), patch('random.SystemRandom.random', refuse):
            other = engine_with(Path(self.temp.name) / 'other', Outlines())
        other.close()
        self.assertIsNone(self.chrome._references)
        self.outline(tab=1)
        table = self.chrome._references
        self.assertIsNotNone(table)
        self.outline(tab=1)
        self.assertIs(self.chrome.references, table)

    def test_references_live_as_long_as_the_adapter(self):
        self.browser.outlines[1] = fixture(f2)
        first = self.outline(tab=1)['untrusted_content']['outline']
        table = self.reference(first, 'table "Stock"')
        self.assertEqual(self.outline(tab=1)['untrusted_content']['outline'], first)
        rows = self.outline(tab=1, ref=table, max=40000)['untrusted_content']['outline'].split('\n')
        self.assertTrue(rows[1].startswith('columns: "Column00name" | '))
        self.assertEqual(len(rows), 2 + 200)
        # Another tab, another reference for an element of the same ids.
        self.browser.outlines[2] = fixture(f2, tab=2)
        self.assertNotIn(table, re.findall(r'\b[a-z]{5}\d+\b', self.outline(tab=2)['untrusted_content']['outline']))

    def test_a_stale_reference_is_its_tabs_entry(self):
        self.browser.outlines[1] = fixture(f2)
        table = self.reference(self.outline(tab=1)['untrusted_content']['outline'], 'table "Stock"')
        for args in ({'ref': 'zzzzz1'}, {'ref': table, 'find': 'r001'}):
            with self.subTest(args=args):
                if args['ref'] == table:
                    self.browser.outlines[1]['frames'][0]['reader'] = 'r-new'  # a new reader instance
                read = self.read(tab=1, **args)['reads'][0]
                self.assertEqual(read['error']['code'], 'stale_reference')
                self.assertNotIn('outline', read.get('untrusted_content', {}))
        # A fold whose first hidden child is another kind of element now: the refusal
        # carries that element's present line, apart from the message.
        self.browser.outlines[1] = fixture(f3)
        fold = self.reference(self.outline(tab=1)['untrusted_content']['outline'], '… 295 more')
        changed = fixture(f3)
        first = next(item for item in changed['frames'][0]['nodes'] if item['id'] == 31)  # Result 5's link
        first['role'] = 'button'
        del first['href']
        self.browser.outlines[1] = changed
        read = self.read(tab=1, ref=fold)['reads'][0]
        self.assertEqual(read['error']['code'], 'stale_reference')
        self.assertNotIn('Result', read['error']['message'])
        self.assertTrue(read['untrusted_content']['line'].startswith('button "Result 5 of the listing" '), read)

    def test_the_checks_of_brief_20s_read(self):
        # Every frame's address, not only the top document's.
        self.browser.outlines[1] = fixture(f1, frames=[frame([node(1, 'p', text=['Top'])]),
                                                       frame([node(1, 'p', text=['Inner'])], frame=4, document='d4', reader='r4',
                                                             url='about:blank', effective_url='https://claude.ai/settings')])
        self.assertEqual(self.read(tab=1)['reads'][0]['error']['code'], 'refused')
        self.chrome.read_owner_hosts = lambda: ['fixture.example']
        self.browser.outlines[1] = fixture()
        read = self.read(tab=1)['reads'][0]
        self.assertEqual((read['error']['code'], 'untrusted_content' in read), ('refused', False))
        self.chrome.read_owner_hosts = lambda: []
        # The qualification mode refuses the whole call.
        record = {'format': 1, 'entries': [entry(build=self.chrome.qualification.build,
                                                  core={**entry()['core'], 'password_exclusion': False})]}
        self.engine.store.write({'chrome:qualification': record}, 'chrome_test_setup', 'Synthetic failed group')
        self.refused('qualification_failed', tab=1)

    def test_the_queued_steps_run_as_in_brief_20s_read(self):
        held = []
        self.browser.calls.clear()
        original = self.chrome.steps
        self.chrome.steps = lambda steps, tab: held.append((steps, tab)) or original(steps, tab)
        self.outline(tab=1)
        self.assertEqual(held, [([], 1)])
        # Not while a dialog is open: the readers can't answer.
        self.browser.outlines[1] = {**small(), 'frames': [], 'dialog': {'kind': 'alert', 'text': 'Line\nbreak "quoted"'}}
        read = self.outline(tab=1, until={'text': 'anything'}, timeout_ms=2000)
        self.assertEqual(held, [([], 1)])
        self.assertEqual((read['untrusted_content']['outline'], read['until_met']), ('', False))
        self.assertEqual(read['untrusted_content']['dialog'], {'kind': 'alert', 'text': 'Line\\u000abreak "quoted"'})

    def test_the_cross_field_rules(self):
        for args in ({}, {'tab': 1, 'tabs': [1, 2]}, {'tabs': [1, 2], 'ref': 'kqtvm1'}, {'tabs': [1, 2], 'until': {'text': 'x'}},
                     {'tabs': [1, 1]}, {'tab': 1, 'role': 'link'}, {'tab': 1, 'find': 'x', 'role': 'heading'},
                     {'tab': 1, 'timeout_ms': 100}):
            with self.subTest(args=args):
                self.refused('invalid_input', **args)
        self.assertEqual(self.browser.calls, [])
        # What the schema says itself.
        for args in ({'tab': 1, 'until': {'text': 'a', 'gone': 'b'}}, {'tab': 1, 'until': {}}, {'tabs': [1]},
                     {'tabs': [1, 2, 3, 4, 5, 6]}, {'tab': 1, 'max': 999}, {'tab': 1, 'max': 40001},
                     {'tab': 1, 'find': 'x' * 201}, {'tab': 1, 'until': {'text': 'x'}, 'timeout_ms': 6001}, {'tab': 1, 'extra': 1}):
            with self.subTest(args=args), self.assertRaises(Refused):
                validate(args, OUTLINE)
        for args in ({'tab': 1, 'until': {'gone': 'b'}, 'timeout_ms': 0}, {'tabs': [1, 2, 3, 4, 5], 'max': 1000},
                     {'tab': 1, 'ref': 'kqtvm1', 'full': True, 'find': 'x', 'role': 'link', 'cursor': 'c', 'max': 40000}):
            validate(args, OUTLINE)

    def test_until_reads_again_only_when_the_token_moved(self):
        self.browser.outlines[1] = small('Loading')

        def later(count):
            if count == 3:
                self.browser.outlines[1] = small('Loading', 'Done at last')
                self.browser.tokens[1] = 'token-2'
        self.browser.on_state = later
        read = self.outline(tab=1, until={'text': 'DONE at'})
        self.assertTrue(read['until_met'])
        self.assertIn('p "Done at last"', read['untrusted_content']['outline'])
        self.assertEqual(len(self.browser.named('outline')), 2)
        self.assertEqual(len(self.browser.named('page_state')), 4)  # before each outline, and two polls between

    def test_until_gone(self):
        self.browser.outlines[1] = small('Spinner', 'Results')
        self.browser.on_state = lambda count: count == 2 and (self.browser.outlines.update({1: small('Results')}),
                                                               self.browser.tokens.update({1: 'token-2'}))
        read = self.outline(tab=1, until={'gone': 'spinner'})
        self.assertTrue(read['until_met'])
        self.assertNotIn('Spinner', read['untrusted_content']['outline'])

    def test_until_returns_what_is_there_at_its_timeout(self):
        self.browser.outlines[1] = small('Loading')
        started = time.monotonic()
        read = self.outline(tab=1, until={'text': 'never'}, timeout_ms=300)
        elapsed = time.monotonic() - started
        self.assertFalse(read['until_met'])
        self.assertEqual(read['untrusted_content']['outline'], 'p "Loading"')
        self.assertGreaterEqual(elapsed, .3)
        self.assertLess(elapsed, 2)
        self.assertEqual(len(self.browser.named('outline')), 1)  # the token never moved
        self.assertGreaterEqual(len(self.browser.named('page_state')), 3)
        self.assertNotIn('until_met', self.outline(tab=1))
        self.assertTrue(self.outline(tab=1, until={'text': 'loading'}, timeout_ms=0)['until_met'])

    def test_several_tabs_each_by_itself(self):
        self.browser.outlines.update({2: fixture(f2, tab=2), 3: fixture(f3, tab=3)})
        self.browser.refusals[2] = Refused('refused', 'This tab is not in the Claude group.')
        result = self.read(tabs=[1, 2, 3])
        self.assertEqual([read['tab'] for read in result['reads']], [1, 2, 3])
        first, second, third = result['reads']
        self.assertEqual(second, {'tab': 2, 'error': {'code': 'refused', 'message': 'This tab is not in the Claude group.'}})
        self.assertTrue(all(read['characters'] <= 3000 for read in (first, third)))
        self.assertIsNotNone(first['cursor'])  # F1 goes on with its own cursor, in a call for that tab alone
        self.assertIn('…', self.outline(tab=1, cursor=first['cursor'])['untrusted_content']['outline'])
        self.assertLessEqual(len(self.read(tabs=[1, 3], max=1000)['reads'][0]['untrusted_content']['outline']), 1000)

    def test_pages_by_cursor(self):
        whole = self.outline(tab=1)['untrusted_content']['outline']
        pages, cursor = [], None
        while True:
            read = self.outline(tab=1, max=1000, **({'cursor': cursor} if cursor else {}))
            pages.append(read['untrusted_content']['outline'])
            cursor = read['cursor']
            if cursor is None:
                break
        self.assertEqual(''.join(pages), whole)
        self.assertGreater(len(pages), 3)
        cursor = self.outline(tab=1, max=1000)['cursor']
        # Another query refuses the call; another state token makes the page stale.
        self.refused('invalid_input', tab=1, max=1000, cursor=cursor, full=True)
        self.browser.tokens[1] = 'token-2'
        self.assertEqual(self.read(tab=1, max=1000, cursor=cursor)['reads'][0]['error']['code'], 'stale_reference')

    def test_a_list_field_by_ref_brings_all_its_options(self):
        self.browser.outlines[1] = fixture(f4)
        country = self.reference(self.outline(tab=1)['untrusted_content']['outline'], 'combobox "Country"')
        self.browser.options = [{'label': 'Country %d' % index, 'value': 'c%d' % index, 'chosen': index == 7} for index in range(200)]
        self.browser.calls.clear()
        text = self.outline(tab=1, ref=country, max=40000)['untrusted_content']['outline']
        self.assertEqual(text.count('option "Country '), 200)
        self.assertIn(('options', 1), self.browser.calls)
        # A field with all its options in the outline needs no further command.
        size = self.reference(self.outline(tab=1)['untrusted_content']['outline'], 'combobox "Size"')
        self.browser.calls.clear()
        self.outline(tab=1, ref=size)
        self.assertNotIn(('options', 1), self.browser.calls)
        # An answer for another document is stale.
        original = self.browser.call
        self.browser.call = lambda name, **args: {**original(name, **args), 'document': 'other'} if name == 'options' else original(name, **args)
        self.assertEqual(self.read(tab=1, ref=country)['reads'][0]['error']['code'], 'stale_reference')

    def test_a_reply_of_the_wrong_shape_shows_nothing(self):
        broken = fixture(f3)
        broken['frames'][0]['nodes'][0]['box'] = {'x': 1}
        self.browser.outlines[1] = broken
        error = self.refused('transport_error', tab=1)
        self.assertIn("a node holds a key that isn't part of the outline", str(error))
        self.browser.outlines[1] = fixture(f3, tab=7)
        self.refused('transport_error', tab=1)
        self.browser.outlines[1] = fixture(f3, session='another-session')
        self.refused('transport_error', tab=1)

    def test_find_with_role_inside_the_adapter(self):
        self.browser.outlines[1] = fixture(f3)
        read = self.outline(tab=1, find=F3_UNIQUE.lower(), role='link')
        self.assertEqual(read['untrusted_content']['outline'].count('\n'), 0)
        self.assertTrue(read['untrusted_content']['outline'].startswith('link "Quarterly zebra report"'))

    def test_the_measure_counts_the_pending_part(self):
        wide = self.outline(tab=1, full=True, max=40000)['characters']
        original = self.engine.pending
        self.engine.pending = lambda app=None, args=None, resolve_checks=True: {**original(app, args, resolve_checks), 'padding': 'x' * 30000}
        result = self.read(tab=1, full=True, max=40000)
        narrow = result['reads'][0]['characters']
        self.assertLess(narrow, wide - 20000)
        sent = {'ok': True, 'data': result, 'pending': self.engine.pending('chrome', resolve_checks=False)}
        self.assertLessEqual(len(canonical(sent).encode()), RESULT_LIMIT - PENDING_DRIFT)
        self.assertEqual(self.chrome.outline_measure(result['version_notice'])(result['reads']), len(canonical(sent).encode()))
        # When the pending part leaves no room for a page, the call says so instead of sending less.
        self.engine.pending = lambda app=None, args=None, resolve_checks=True: {**original(app, args, resolve_checks), 'padding': 'x' * 48000}
        self.refused('result_too_large', tab=1)


if __name__ == '__main__':
    unittest.main()
