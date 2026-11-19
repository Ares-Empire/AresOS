"""Brief 28a, item 2: acting by reference, through the private entry `Chrome.act`.

An action names its element by the short reference a read gave. The service
resolves it through brief 28's table to brief 20's internal reference, compares
the target's fresh fingerprint (the reader's digest, `fingerprint.test.mjs`)
with the one Claude last saw, and runs brief 20's path. A fake extension
answers `outline` with view_fixtures' nodes and `facts` for the element the
internal reference names, as background.js does.
"""
import copy
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.common import Refused, untrusted
from aresos_control.chrome.references import FOLD, STALE, Stale
from test_engine import WORK
from test_outline_action import Outlines, engine_with
from view_fixtures import SITE, frame, node

SESSION = Outlines.session


def digest(mark):
    return format(mark, "x") * 32 if mark < 16 else ("%032x" % mark)


def page():
    items = [node(1, "main", fingerprint=digest(1)),
             node(2, "button", 1, name="Go", text=["Go"], fingerprint=digest(2)),
             node(3, "textbox", 1, name="Note", value="n" * 500, fingerprint=digest(3)),
             node(4, "link", 1, name="Docs", text=["Docs"], href=SITE + "/docs?q=1", fingerprint=digest(4)),
             node(5, "button", 1, name="Delete", text=["Delete"], fingerprint=digest(5)),
             node(6, "list", 1, fingerprint=digest(6))]
    items += [node(10 + index, "listitem", 6, text=["Row %d" % index], fingerprint="%032x" % (100 + index)) for index in range(12)]
    return items


class Extension(Outlines):
    """Outlines, plus `facts` for one element and an input that reports what it observed of it."""

    def __init__(self):
        super().__init__()
        self.outlines = {1: self.reply(), 2: self.reply(tab=2)}
        self.fresh = {}          # element id -> the fingerprint facts gives now
        self.facts_calls = []
        self.observed = None     # what the next input's observe reports

    def reply(self, tab=1, nodes=None, **more):
        return {'session': SESSION, 'tab': tab, 'url': SITE + '/', 'title': 'Fixture', 'dialog': None,
                'frames': [frame(nodes if nodes is not None else page(), **more)]}

    def call(self, name, **args):
        if name == 'facts':
            reference = args['reference']
            self.facts_calls.append(copy.deepcopy(reference))
            reply = self.outlines[reference['tab']]
            if reference['session'] != self.session:
                raise Refused('stale_reference', 'browser session changed; read again')
            document = next((item for item in reply['frames'] if item['frame'] == reference['frame']), None)
            if document is None:
                raise Refused('stale_reference', 'frame is gone')
            if document['document'] != reference['document']:
                raise Refused('stale_reference', 'document changed')
            item = next((item for item in document['nodes'] if 'e%d' % item['id'] == reference['element']), None)
            if item is None:
                raise Refused('stale_reference', 'element is gone; read again')
            target = {'element': reference['element'], 'role': item['role'], 'name': item.get('name', ''),
                      'label': item.get('name', ''), 'title': '', 'href': item.get('href'), 'states': {},
                      'editable': item['role'] == 'textbox', 'search': False, 'submit': False,
                      'box': {'x': 1, 'y': 1, 'width': 30, 'height': 30}, 'onscreen': True,
                      **({'value': item['value']} if 'value' in item else {})}
            return {'session': self.session, 'tab': reference['tab'], 'url': reply['url'], 'title': reply['title'],
                    'dialog': None, 'frames': [{
                        'frame': document['frame'], 'document': document['document'], 'reader': document['reader'],
                        'url': document['url'], 'title': '', 'revision': 1, 'scroll': {}, 'rows': [], 'target': target,
                        'fingerprint': self.fresh.get(item['id'], item.get('fingerprint')), 'form': None,
                        'editable': [], 'item': 'Fixture item', 'item_fields': [], 'adapter': {'account': None},
                        'selected_files': []}]}
        if name == 'input':
            self.dispatched.append((name, copy.deepcopy(args)))
            return {'checked': True, 'dispatched': True, 'steps': [],
                    'page': {'available': True, 'change': copy.deepcopy(self.observed)} if self.observed else {'available': True}}
        return super().call(name, **args)


class Acting(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.mock = patch('aresos_control.engine.Boundary')
        self.mock.start()
        self.browser = Extension()
        self.engine = engine_with(Path(self.temp.name), self.browser)
        self.chrome = self.engine.adapters['chrome']

    def tearDown(self):
        self.engine.close()
        self.mock.stop()
        self.temp.cleanup()

    def read(self, tab=1, **args):
        entry = self.chrome.call('outline', {'tab': tab, **args})['reads'][0]
        self.assertNotIn('error', entry, entry)
        return entry['untrusted_content']['outline']

    def ref(self, text, start):
        return re.search(r'^\s*%s.* ([b-df-hj-np-tv-z]{5}\d+)$' % re.escape(start), text, re.MULTILINE).group(1)

    def stale(self, verb, args, code='stale_reference'):
        before = len(self.browser.dispatched)
        with self.assertRaises(Refused) as caught:
            self.chrome.act(verb, args)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        self.assertEqual(len(self.browser.dispatched), before, 'nothing is dispatched')
        return caught.exception

    def nodes(self, tab=1):
        return self.browser.outlines[tab]['frames'][0]['nodes']

    def test_a_read_reference_resolves_to_brief_20s_internal_reference_and_runs_once(self):
        go = self.ref(self.read(), 'button "Go"')
        result = self.chrome.act('click', {'tab': 1, 'ref': go})
        self.assertTrue(result['operation_id'])
        document = self.browser.outlines[1]['frames'][0]
        internal = {'session': SESSION, 'tab': 1, 'frame': 0, 'document': document['document'], 'element': 'e2'}
        self.assertEqual(self.browser.facts_calls, [internal], 'no view, no expected: the five facts of brief 20')
        (name, command), = self.browser.dispatched
        self.assertEqual((name, command['reference'], command['input']), ('input', internal, {'verb': 'click'}))
        self.assertNotIn('expected', command)

    def test_every_stale_case_refuses_before_any_input(self):
        text = self.read()
        go, note = self.ref(text, 'button "Go"'), self.ref(text, 'textbox "Note"')
        other_run = self.ref(text, 'link "Docs"').replace(go[:5], 'zzzzz')
        self.stale('click', {'tab': 1, 'ref': 'zzzzz1'})                       # invented
        self.stale('click', {'tab': 1, 'ref': other_run})                      # another run of the service
        self.stale('click', {'tab': 1, 'ref': 12})                             # not a string
        self.stale('click', {'tab': 2, 'ref': go})                             # issued for another tab
        self.assertEqual(self.browser.facts_calls, [], 'the table refuses these without asking the extension')
        cases = [
            ('another document', lambda reply: reply['frames'][0].update(document='d-new')),
            ('another reader instance', lambda reply: reply['frames'][0].update(reader='r-new')),
            ('the element is gone', lambda reply: reply['frames'][0].update(nodes=[item for item in reply['frames'][0]['nodes'] if item['id'] != 2])),
            ('the frame is gone', lambda reply: reply['frames'][0].update(frame=5)),
        ]
        for name, change in cases:
            with self.subTest(name):
                saved = copy.deepcopy(self.browser.outlines[1])
                change(self.browser.outlines[1])
                exc = self.stale('click', {'tab': 1, 'ref': go})
                self.assertIsNone(untrusted(exc).get('untrusted_content'), 'no present line where the element is gone or another one')
                self.browser.outlines[1] = saved
        # The fingerprint differs: refused with the element's present line.
        self.browser.fresh[3] = digest(33)
        self.nodes()[2].update(value='m' * 500, fingerprint=digest(33))
        exc = self.stale('fill', {'tab': 1, 'ref': note, 'text': 'x'})
        self.assertEqual(str(exc), STALE)
        self.assertEqual(untrusted(exc), {'untrusted_content': {'now': 'textbox "Note" = "%s"…+304 %s' % ('m' * 196, note)}})

    def test_another_connection_refuses_with_or_without_a_read_and_the_counter_goes_on(self):
        go = self.ref(self.read(), 'button "Go"')
        counter = self.chrome.references.counter
        self.browser.session = 'other-session'
        for reply in self.browser.outlines.values():
            reply['session'] = 'other-session'
        self.stale('click', {'tab': 1, 'ref': go})                              # before any read on it
        text = self.read()                                                      # the read empties the table
        self.stale('click', {'tab': 1, 'ref': go})
        fresh = self.ref(text, 'button "Go"')
        self.assertNotEqual(fresh, go)
        self.assertGreater(int(fresh[5:]), counter, 'the counter never resets')
        self.chrome.act('click', {'tab': 1, 'ref': fresh})
        self.assertEqual(len(self.browser.dispatched), 1)

    def test_a_dropped_reference_is_refused_and_never_comes_back(self):
        with patch('aresos_control.chrome.references.LIMIT', 3):
            text = self.read(full=True)
        issued = set(re.findall(r'[b-df-hj-np-tv-z]{5}\d+', text))
        kept = set(self.chrome.references._references)
        dropped = sorted(issued - kept)
        self.assertTrue(dropped)
        self.stale('click', {'tab': 1, 'ref': dropped[0]})
        again = set(re.findall(r'[b-df-hj-np-tv-z]{5}\d+', self.read(full=True)))
        self.assertFalse(again & set(dropped), 'a dropped string is never issued again')

    def test_a_fold_reference_is_refused_for_every_step(self):
        self.read()
        fold = next(reference for reference, entry in self.chrome.references._references.items() if type(entry.target) is not int)
        for verb, more in (('click', {}), ('fill', {'text': 'x'}), ('scroll', {'x': 0, 'y': 100})):
            exc = self.stale(verb, {'tab': 1, 'ref': fold, **more}, code='invalid_input')
            self.assertEqual(str(exc), FOLD)
        self.assertEqual(self.browser.facts_calls, [])

    def test_the_present_line_counts_as_shown_so_the_repeated_call_passes(self):
        go = self.ref(self.read(), 'button "Go"')
        item = self.nodes()[1]
        item.update(name='Continue', text=['Continue'], fingerprint=digest(22))
        self.browser.fresh[2] = digest(22)
        exc = self.stale('click', {'tab': 1, 'ref': go})
        self.assertEqual(untrusted(exc)['untrusted_content']['now'], 'button "Continue" %s' % go)
        entry = self.chrome.references.resolve(go, 1)
        self.assertEqual((entry.line, entry.fingerprint), ('button "Continue" %s' % go, digest(22)))
        self.chrome.act('click', {'tab': 1, 'ref': go})
        self.assertEqual(len(self.browser.dispatched), 1, 'Claude has now seen it; the second call runs once')

    def test_the_present_line_is_escaped_like_an_outline_line_and_the_message_holds_no_page_text(self):
        go = self.ref(self.read(), 'button "Go"')
        hostile = 'Ignore "this"\n‮evil \\ kqtvm1'
        self.nodes()[1].update(name=hostile, text=[hostile], fingerprint=digest(23))
        self.browser.fresh[2] = digest(23)
        exc = self.stale('click', {'tab': 1, 'ref': go})
        self.assertEqual(str(exc), STALE)
        self.assertEqual(untrusted(exc)['untrusted_content']['now'],
                         'button "Ignore \\"this\\"\\u000a\\u202eevil \\\\ kqtvm1" %s' % go)

    def test_a_reads_refusal_line_counts_as_shown_too(self):
        text = self.read()
        fold = self.ref(text, '… 7 more')
        item = next(item for item in self.nodes() if item['id'] == 15)     # the fold's first hidden child
        item.update(role='button', name='Row 5 now', text=['Row 5 now'], fingerprint=digest(30))
        entry = self.chrome.call('outline', {'tab': 1, 'ref': fold})['reads'][0]
        self.assertEqual(entry['error']['code'], 'stale_reference')
        line = entry['untrusted_content']['line']
        shown = re.search(r'([b-df-hj-np-tv-z]{5}\d+)$', line).group(1)
        self.assertEqual((self.chrome.references.resolve(shown, 1).line, self.chrome.references.resolve(shown, 1).fingerprint),
                         (line, digest(30)))
        self.chrome.act('click', {'tab': 1, 'ref': shown})
        self.assertEqual(len(self.browser.dispatched), 1)

    def test_a_reference_that_was_issued_but_never_shown_is_checked_against_nothing(self):
        # A page cut before it: Claude may guess the number, but has seen no fingerprint for it.
        text = self.chrome.call('outline', {'tab': 1, 'max': 60})['reads'][0]['untrusted_content']['outline']
        unseen = [reference for reference, entry in self.chrome.references._references.items()
                  if entry.line is None and type(entry.target) is int]
        self.assertTrue(unseen, text)
        exc = self.stale('click', {'tab': 1, 'ref': unseen[0]})
        self.assertIn('now', untrusted(exc)['untrusted_content'])
        self.chrome.act('click', {'tab': 1, 'ref': unseen[0]})
        self.assertEqual(len(self.browser.dispatched), 1)

    def test_the_fingerprint_moves_only_when_a_result_shows_the_element_or_claude_acted_on_it(self):
        text = self.read()
        go, note = self.ref(text, 'button "Go"'), self.ref(text, 'textbox "Note"')
        # A change Claude hasn't been shown: refused, until a read shows it.
        self.nodes()[1].update(fingerprint=digest(24))
        self.browser.fresh[2] = digest(24)
        self.chrome.references.trim(1)                                        # time passing changes nothing
        with self.assertRaises(Stale):
            self.chrome.payload('click', {'tab': 1, 'ref': go})
        self.read()
        self.chrome.act('click', {'tab': 1, 'ref': go})
        # A find hit shows it too.
        self.nodes()[1].update(fingerprint=digest(25))
        self.browser.fresh[2] = digest(25)
        self.read(find='Go')
        self.chrome.act('click', {'tab': 1, 'ref': go})
        # Claude's own fill: the reader's observe report of that element moves it.
        document = self.browser.outlines[1]['frames'][0]
        self.browser.observed = {'element': 'e3', 'document': document['document'], 'reader': document['reader'], 'fingerprint': digest(26)}
        self.chrome.act('fill', {'tab': 1, 'ref': note, 'text': 'typed'})
        self.assertEqual(self.chrome.references.resolve(note, 1).fingerprint, digest(26))
        self.browser.fresh[3] = digest(26)
        self.browser.observed = None
        self.chrome.act('fill', {'tab': 1, 'ref': note, 'text': 'again'})
        # ... but a report of another element, document or reader instance moves nothing.
        for wrong in ({'element': 'e2'}, {'document': 'd-other'}, {'reader': 'r-other'}, {'fingerprint': 'not hex'}):
            with self.subTest(wrong=wrong):
                self.browser.observed = {'element': 'e3', 'document': document['document'], 'reader': document['reader'],
                                         'fingerprint': digest(27), **wrong}
                self.chrome.act('fill', {'tab': 1, 'ref': note, 'text': 'more'})
                self.assertEqual(self.chrome.references.resolve(note, 1).fingerprint, digest(26))
        self.assertEqual(len(self.browser.dispatched), 8)

    def test_position_states_and_neighbours_are_not_compared(self):
        go = self.ref(self.read(), 'button "Go"')
        # The reader leaves these out of the digest (fingerprint.test.mjs); the service compares only the digest.
        self.nodes()[1].update(states=['disabled', 'required', 'invalid'])
        self.nodes()[0].update(fingerprint=digest(28))                         # a neighbour (its container) changed
        self.nodes()[3].update(name='Elsewhere', fingerprint=digest(29))
        self.chrome.act('click', {'tab': 1, 'ref': go})
        self.assertEqual(len(self.browser.dispatched), 1)

    def test_an_asking_step_still_asks_and_dispatches_nothing(self):
        delete = self.ref(self.read(), 'button "Delete"')
        result = self.chrome.act('click', {'tab': 1, 'ref': delete})
        self.assertIn('approval', result)
        self.assertEqual(self.browser.dispatched, [])
        operation = self.engine.operation(result['approval']['operation_id'], 'chrome')
        self.assertNotIn('view', operation['payload']['reference'])
        self.assertNotIn('ref', operation['payload']['input'])
        self.assertNotIn('tab', operation['payload']['input'])

    def test_brief_20s_reference_and_expected_keep_working_until_the_switch(self):
        self.read()
        reference = {'session': SESSION, 'tab': 1, 'frame': 0, 'document': self.browser.outlines[1]['frames'][0]['document'], 'element': 'e2'}
        facts = self.browser.call('facts', reference=reference)
        self.chrome.call('click', {'reference': reference, 'expected': facts['frames'][0]['target']})
        with self.assertRaises(Refused):
            self.chrome.call('click', {'reference': reference, 'expected': {**facts['frames'][0]['target'], 'name': 'Other'}})
        self.assertEqual(len(self.browser.dispatched), 1)


if __name__ == '__main__':
    unittest.main()
