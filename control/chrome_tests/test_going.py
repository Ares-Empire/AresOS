"""Brief 28a, item 4: chrome_open and chrome_go through the private entry `Chrome.going`.

A fake extension answers brief 28's `outline` and `page_state`, brief 20's
`facts`, `tab_context`, `open`, `navigate` and `prepare_control`, and keeps a
receiver: every address a tab was sent to (`loads`) and every input (`dispatched`).
A navigation can show up only after some looks at the tab (`delay`), keep its
document (a fragment, a single-page site's history), or never go quiet.
"""
import copy
import hashlib
from pathlib import Path
import re
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome import going, loss
from aresos_control.chrome.references import STALE
from aresos_control.common import Refused, canonical, untrusted
from test_acting_references import Extension, digest
from test_engine import WORK, declared
from test_outline_action import engine_with
from view_fixtures import SITE, frame, node

SESSION = Extension.session
RECEIVER = 'https://receiver.example'
MARKER = 'Kq7Zr2Lm9Xc4Vb8Nw3Ps6Td1Fg5Hj0Ya2Qe7Ru4Io'   # 40 characters: hidden by the public form
DELETE = RECEIVER + '/delete?item=4&token=' + MARKER
UNSUBSCRIBE = RECEIVER + '/unsubscribe?list=7&sig=' + MARKER
DOCS = SITE + '/docs?q=red+shoes&state=' + MARKER
REPORT = {'act': 'navigate', 'fields': [{'description': 'field "Draft"', 'by': 'owner'}],
          'more_fields': 0, 'frames_uninspected': 0, 'media': False}


def sha(address):
    return hashlib.sha256(address.encode()).hexdigest()


def links():
    return [node(1, 'main', fingerprint=digest(1)),
            node(2, 'link', 1, name='Delete', text=['Delete'], href=DELETE, fingerprint=digest(2)),
            node(3, 'link', 1, name='Unsubscribe', text=['Unsubscribe'], href=UNSUBSCRIBE, fingerprint=digest(3)),
            node(4, 'link', 1, name='Docs', text=['Docs'], href=DOCS, fingerprint=digest(4)),
            node(5, 'button', 1, name='Go', text=['Go'], fingerprint=digest(5)),
            node(6, 'link', 1, name='Run', text=['Run'], href='javascript:void(0)', fingerprint=digest(6))]


def arrived_page(url, words='Arrived'):
    return [node(1, 'main', fingerprint=digest(7)), node(2, 'p', 1, text=[words]),
            node(3, 'link', 1, name='Next', text=['Next'], href=SITE + '/next', fingerprint=digest(8))]


class Pages(Extension):
    """Tabs that move: brief 20's open and navigate change what outline, facts and page_state show."""

    def __init__(self):
        super().__init__()
        self.serial = 0
        self.outlines, self.states, self.control = {}, {}, {}
        self.show(1, SITE + '/', links())
        self.control[1] = 'epoch-1'
        self.loads = []          # the receiver: (command, tab, address) for every page a tab was sent to
        self.history = {1: [SITE + '/']}
        self.next_tab = 10
        self.delay = 0           # looks at the tab before a navigation shows
        self.queued = []         # (tab, change) waiting for their look
        self.restless = False    # the token moves on every look: the page never goes quiet
        self.needs_reload = set()
        self.report = None       # navigate and prepare_control refuse with it unless discard_unsaved
        self.looks = 0
        self.replace_state = None  # the old document moves to this address in place as the navigation starts

    def show(self, tab, url, nodes, same_document=False):
        """The tab now shows `url`: in a new document, or in the same one (same Chrome document, reader and instance)."""
        self.serial += 1
        old = self.states.get(tab)
        document, reader = (old['document'], old['reader']) if same_document else ('browser-%d' % self.serial, ('d%d' % self.serial, 'r%d' % self.serial))
        self.outlines[tab] = {'session': SESSION, 'tab': tab, 'url': url, 'title': 'Page %d' % self.serial, 'dialog': None,
                              'frames': [frame(nodes, document=reader[0], reader=reader[1], url=url)] if nodes is not None else []}
        self.states[tab] = {'document': document, 'reader': reader, 'address': sha(url), 'ready': nodes is not None,
                            'token': 'token-%d' % self.serial, 'dialog': False}

    def later(self, tab, change):
        if self.delay:
            self.queued.append([self.delay, tab, change])
        else:
            change()

    def call(self, name, **args):
        tab = args.get('tab')
        if name == 'page_state':
            self.looks += 1
            for item in list(self.queued):
                item[0] -= 1
                if item[0] < 0:
                    self.queued.remove(item)
                    item[2]()
            state = self.states[tab]
            if state.get('dialog'):
                return {'session': SESSION, 'tab': tab, 'dialog': True, 'address': state['address']}
            if self.restless:
                state['token'] = 'restless-%d' % self.looks
            return {'session': SESSION, 'tab': tab, 'control': self.control.get(tab), 'queued': False,
                    **{key: state[key] for key in ('document', 'address', 'ready', 'token', 'dialog')}}
        if name == 'outline':
            self.calls.append((name, tab))
            reply = copy.deepcopy(self.outlines[tab])
            reply['needs_reload'] = tab in self.needs_reload
            return reply
        if name == 'tab_context':
            return {'session': SESSION, 'tab': tab, 'url': self.outlines[tab]['url'], 'title': self.outlines[tab]['title'],
                    'control': self.control.get(tab), 'frames': []}
        if name == 'open':
            tab = self.next_tab
            self.next_tab += 1
            self.show(tab, 'about:blank', None)
            self.control[tab] = 'epoch-%d' % tab
            self.history[tab] = []
            self.dispatched.append((name, copy.deepcopy(args)))
            return {'tab': tab, 'session': SESSION, 'group': 5}
        if name == 'navigate':
            self.dispatched.append((name, copy.deepcopy(args)))
            if self.report is not None and args.get('discard_unsaved') is not True:
                raise loss.LossRefused(loss.checked(copy.deepcopy(self.report)))
            if self.replace_state:
                self.states[tab]['address'] = sha(self.replace_state)
            if 'url' in args:
                url = args['url']
                self.loads.append(('navigate', tab, url))
                current = self.outlines[tab]['url']
                fragment = url.split('#')[0] == current.split('#')[0] and url != current and '#' in url
                self.history[tab].append(url)
                self.later(tab, lambda: self.show(tab, url, arrived_page(url), same_document=fragment))
            elif args['direction'] == 'reload':
                url = self.outlines[tab]['url']
                self.loads.append(('reload', tab, url))
                self.later(tab, lambda: self.show(tab, url, arrived_page(url, 'Reloaded')))
            else:
                self.history[tab].pop()
                url = self.history[tab][-1]
                self.loads.append((args['direction'], tab, url))
                self.later(tab, lambda: self.show(tab, url, arrived_page(url, 'Back'), same_document=True))
            return {'navigated': True, 'page': {'available': True}}
        if name == 'loss_report':
            # Read only (background.test.mjs, "28a 6: loss_report"): what prepare_control would refuse with.
            self.calls.append((name, tab))
            if tab not in self.needs_reload:
                return {'reload_due': False}
            report = copy.deepcopy(self.report) if self.report is not None else \
                {'fields': [], 'more_fields': 0, 'frames_uninspected': 0, 'media': False}
            return {'reload_due': True, 'loss': {**report, 'act': 'first_input'}}
        if name == 'prepare_control':
            self.dispatched.append((name, copy.deepcopy(args)))
            if tab not in self.needs_reload:
                return {'ready': True}
            if self.report is not None and args.get('discard_unsaved') is not True:
                raise loss.LossRefused(loss.checked({**copy.deepcopy(self.report), 'act': 'first_input'}))
            self.needs_reload.discard(tab)
            url = self.outlines[tab]['url']
            self.loads.append(('guarded reload', tab, url))
            self.show(tab, url, links())
            return {'reloaded': True, 'message': 'The taken tab reloaded.'}
        return super().call(name, **args)

    def sent(self, *names):
        return [name for name, _ in self.dispatched if not names or name in names]


class Clock:
    """A module's own `time`, moved by its sleeps and by a microsecond for each reading, as a look takes time."""

    def __init__(self):
        self.now, self.slept = time.monotonic(), []

    def monotonic(self):
        self.now += 1e-6
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


class Going(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.mock = patch('aresos_control.engine.Boundary')
        self.mock.start()
        self.browser = Pages()
        self.engine = engine_with(Path(self.temp.name), self.browser)
        self.chrome = declared(self.engine.adapters['chrome'])  # every result as its tool declares it (step 1d)

    def tearDown(self):
        self.engine.close()
        self.mock.stop()
        self.temp.cleanup()

    def read(self, tab=1):
        entry = self.chrome.call('read', {'tab': tab})['reads'][0]
        self.assertNotIn('error', entry, entry)
        return entry['untrusted_content']['outline']

    def ref(self, start, tab=1, text=None):
        text = text if text is not None else self.read(tab)
        return re.search(r'^\s*%s.* ([b-df-hj-np-tv-z]{5}\d+)$' % re.escape(start), text, re.MULTILINE).group(1)

    def refused(self, verb, args, code):
        before = (list(self.browser.dispatched), list(self.browser.loads), self.operations())
        with self.assertRaises(Refused) as caught:
            self.chrome.going(verb, args)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        self.assertEqual((self.browser.dispatched, self.browser.loads, self.operations()), before,
                         'no tab created, no address followed, nothing committed')
        return caught.exception

    def operations(self):
        return sorted(operation['id'] for _, operation in self.engine.store.iter_items('op:'))

    def operation(self, action):
        return [operation for _, operation in self.engine.store.iter_items('op:') if operation['action'] == action]

    def conservative(self):
        mode = self.chrome.mode
        self.chrome.mode = lambda acting=False: {**mode(acting), 'conservative': True}

    # --- a link reference keeps its recognised meaning (CROSS-5 finding 3) ----

    def test_delete_and_unsubscribe_links_refuse_to_open_and_their_click_prepares_then_sends_once(self):
        text = self.read()
        for name in ('Delete', 'Unsubscribe'):
            with self.subTest(name):
                ref = self.ref('link "%s"' % name, text=text)
                exc = self.refused('open', {'ref': ref}, 'refused')
                self.assertEqual(str(exc), going.ASKS)
                self.assertEqual(untrusted(exc), {}, 'the fixed message alone')
                self.refused('open', {'ref': ref, 'tab': 1}, 'refused')
                prepared = self.chrome.act('click', {'tab': 1, 'ref': ref})['approval']
                self.assertEqual(self.browser.sent('input', 'open', 'navigate'), [], 'nothing reaches the receiver before approval')
                submitted = self.engine.request({'v': 1, 'method': 'call', 'action': 'chrome_submit', 'arguments': prepared})
                self.assertTrue(submitted['ok'], submitted)
                self.assertEqual(self.browser.sent('input'), ['input'], 'the approved click is sent once')
                self.engine.request({'v': 1, 'method': 'call', 'action': 'chrome_submit', 'arguments': prepared})
                self.assertEqual(self.browser.sent('input'), ['input'], 'never twice')
                self.browser.dispatched.clear()
        self.assertEqual(self.browser.loads, [], 'no address was ever followed by opening')

    def test_an_ordinary_link_reference_opens_its_full_address_and_returns_the_outline(self):
        docs = self.ref('link "Docs"')
        result = self.chrome.going('open', {'ref': docs})
        self.assertEqual(self.browser.loads, [('navigate', result['tab'], DOCS)], 'the receiver gets the whole address')
        self.assertEqual(self.browser.sent('open', 'navigate'), ['open', 'navigate'])
        self.assertEqual((result['loaded'], result['until_met'], result['cursor']), (True, None, None))
        self.assertEqual(set(result), {'tab', 'loaded', 'until_met', 'characters', 'total', 'cursor', 'untrusted_content', 'version_notice'})
        content = result['untrusted_content']
        self.assertEqual(set(content), {'url', 'title', 'scroll', 'outline', 'dialog'})
        self.assertEqual(content['url'], 'fixture.example/docs?q=red+shoes&state=…')
        self.assertIn('p "Arrived"', content['outline'])
        # The outline's references are ready for the next call.
        nxt = self.ref('link "Next"', text=content['outline'])
        self.assertTrue(self.chrome.act('click', {'tab': result['tab'], 'ref': nxt})['operation_id'])
        [operation] = self.operation('chrome_open')
        self.assertEqual(operation['payload']['url'], DOCS, 'the operation keeps the whole address')
        self.assertNotIn(MARKER, canonical(operation['approval']), 'what it shows is the public form')
        self.assertNotIn(MARKER, canonical(result))

    def test_conservative_mode_refuses_every_link_reference_and_a_supplied_url_still_opens(self):
        text = self.read()
        self.conservative()
        self.refused('open', {'ref': self.ref('link "Docs"', text=text)}, 'refused')
        result = self.chrome.going('open', {'url': DELETE})
        self.assertEqual(self.browser.loads, [('navigate', result['tab'], DELETE)],
                         'an explicit address keeps the free-URL policy: no label is recovered for it')

    def test_a_read_only_site_follows_an_ordinary_link_and_refuses_one_that_would_ask(self):
        text = self.read()
        self.engine.store.write({'chrome:readonly:fixture.example': True}, 'chrome_test_readonly', 'Synthetic read-only restriction')
        self.refused('open', {'ref': self.ref('link "Delete"', text=text)}, 'refused')
        self.chrome.going('open', {'ref': self.ref('link "Docs"', text=text)})
        self.assertEqual([load[2] for load in self.browser.loads], [DOCS])

    def test_a_changed_link_is_stale_with_the_message_alone_and_opens_nothing(self):
        text = self.read()
        docs = self.ref('link "Docs"', text=text)
        self.browser.outlines[1]['frames'][0]['nodes'][3].update(href=SITE + '/elsewhere', fingerprint=digest(40))
        exc = self.refused('open', {'ref': docs}, 'stale_reference')
        self.assertEqual((str(exc), untrusted(exc)), (STALE, {}), 'no present line: Claude reads the element again')
        # Read again: the new address is what opens.
        self.chrome.going('open', {'ref': self.ref('link "Docs"')})
        self.assertEqual([load[2] for load in self.browser.loads], [SITE + '/elsewhere'])

    def test_a_reference_must_be_a_link_of_the_tab_it_names(self):
        text = self.read()
        self.refused('open', {'ref': self.ref('link "Docs"', text=text), 'tab': 2}, 'stale_reference')
        self.refused('open', {'ref': 'zzzzz9'}, 'stale_reference')
        self.assertEqual(str(self.refused('open', {'ref': self.ref('button "Go"', text=text)}, 'invalid_input')), going.NOT_LINK)
        self.assertEqual(str(self.refused('open', {'ref': self.ref('link "Run"', text=text)}, 'invalid_input')), going.NOT_LINK)

    def test_missing_classification_facts_refuse_and_never_fall_back_to_the_address(self):
        docs = self.ref('link "Docs"')
        facts = Extension.call
        def without_adapter(browser, name, **args):
            reply = facts(browser, name, **args)
            if name == 'facts':
                del reply['frames'][0]['adapter']
            return reply
        with patch.object(Extension, 'call', without_adapter):
            self.assertEqual(str(self.refused('open', {'ref': docs}, 'refused')), going.UNCLASSIFIED)

    # --- opening by address and by tab ---------------------------------------

    def test_open_by_url_waits_until_loaded_and_about_blank_needs_no_wait(self):
        self.browser.delay = 2
        result = self.chrome.going('open', {'url': SITE + '/page'})
        self.assertTrue(result['loaded'])
        self.assertIn('p "Arrived"', result['untrusted_content']['outline'])
        blank = self.chrome.going('open', {'url': 'about:blank'})
        self.assertEqual((blank['loaded'], blank['untrusted_content']['outline']), (True, ''))
        self.assertEqual([load[2] for load in self.browser.loads], [SITE + '/page'])

    def test_open_by_tab_takes_a_claude_tabs_present_address_and_his_tab_needs_seen(self):
        self.chrome.going('open', {'tab': 1})
        self.assertEqual([load[2] for load in self.browser.loads], [SITE + '/'])
        self.browser.show(3, SITE + '/his', links())
        self.assertEqual(str(self.refused('open', {'tab': 3}, 'invalid_input')), going.SEEN_NEEDED)
        self.refused('open', {'tab': 3, 'seen': 'qqqqq1'}, 'stale_reference')

    def test_inputs_that_cant_go_together_are_refused_before_anything_runs(self):
        for verb, args in [('open', {}), ('open', {'url': SITE, 'ref': 'kqtvm1'}), ('open', {'url': SITE, 'tab': 1}),
                           ('open', {'url': SITE, 'seen': 'kqtvm1'}), ('open', {'ref': 'kqtvm1', 'seen': 'kqtvm1'}),
                           ('open', {'url': SITE, 'discard_unsaved': True}), ('open', {'url': SITE, 'timeout_ms': 15001}),
                           ('open', {'url': SITE, 'max': 999}), ('open', {'url': SITE, 'until': {'text': 'a', 'gone': 'b'}}),
                           ('go', {'tab': 1}), ('go', {'tab': 1, 'url': SITE, 'to': 'back'}), ('go', {'url': SITE}),
                           ('go', {'tab': 1, 'to': 'up'})]:
            with self.subTest(verb=verb, args=args):
                self.refused(verb, args, 'invalid_input')
        self.refused('open', {'url': 'javascript:alert(1)'}, 'refused')
        self.refused('open', {'url': 'https://claude.ai/chat'}, 'refused')

    # --- chrome_go ------------------------------------------------------------

    def test_go_on_a_tab_outside_claudes_group_answers_take_first(self):
        self.browser.show(3, SITE + '/his', links())
        exc = self.refused('go', {'tab': 3, 'url': SITE + '/next'}, 'take_first')
        self.assertEqual(str(exc), going.TAKE_FIRST)

    def test_go_to_an_address_returns_the_new_documents_outline_once_loaded(self):
        self.browser.delay = 3
        result = self.chrome.going('go', {'tab': 1, 'url': SITE + '/next'})
        self.assertEqual((result['tab'], result['loaded']), (1, True))
        self.assertIn('p "Arrived"', result['untrusted_content']['outline'])
        self.assertEqual(self.browser.loads, [('navigate', 1, SITE + '/next')])
        [operation] = self.operation('chrome_navigate')
        self.assertEqual(operation['state'], 'done')

    def test_loaded_is_seen_once_the_token_was_still_for_quiet_not_a_poll_after_it(self):
        # The new page is there and ready at the first look of the wait, and its token stays.
        clock = Clock()
        with patch.object(going, 'time', clock):
            result = self.chrome.going('go', {'tab': 1, 'url': SITE + '/next'})
        self.assertTrue(result['loaded'])
        self.assertTrue(all(0 < pause <= going.POLL for pause in clock.slept), clock.slept)
        self.assertAlmostEqual(sum(clock.slept), going.QUIET, delta=1e-4)
        # A token that moves at the wait's second look starts the quiet time again from that look.
        # Looks: the call's own before the navigation, then the wait's.
        self.browser.queued.append([2, 1, lambda: self.browser.states[1].update(token='moved')])
        clock = Clock()
        with patch.object(going, 'time', clock):
            result = self.chrome.going('go', {'tab': 1, 'url': SITE + '/third'})
        self.assertTrue(result['loaded'])
        self.assertAlmostEqual(sum(clock.slept), going.POLL + going.QUIET, delta=1e-4)

    def test_a_fragment_and_back_in_a_single_page_site_arrive_without_a_new_document(self):
        document = self.browser.states[1]['document']
        result = self.chrome.going('go', {'tab': 1, 'url': SITE + '/#part'})
        self.assertTrue(result['loaded'])
        self.assertEqual(self.browser.states[1]['document'], document, 'the same document')
        result = self.chrome.going('go', {'tab': 1, 'to': 'back'})
        self.assertTrue(result['loaded'])
        self.assertEqual(self.browser.states[1]['document'], document)

    def test_a_reload_and_the_present_address_count_only_with_a_new_document(self):
        for args, words in (({'to': 'reload'}, 'Reloaded'), ({'url': SITE + '/'}, 'Arrived')):
            with self.subTest(args=args):
                # The old document stays ready and quiet for several looks before the new one comes,
                # and its script moves its own address meanwhile: that isn't the reload's arrival.
                self.browser.delay = 8
                self.browser.replace_state = SITE + '/moved'
                looks = self.browser.looks
                result = self.chrome.going('go', {'tab': 1, **args})
                self.assertTrue(result['loaded'])
                self.assertGreater(self.browser.looks - looks, 8, 'not loaded before the new document was there')
                self.assertIn(words, result['untrusted_content']['outline'])
        # A reload whose document never comes: loaded is false at the timeout, and the outline is as it is.
        self.browser.delay = 10 ** 6
        self.browser.replace_state = None
        before = self.read()
        started = time.monotonic()
        result = self.chrome.going('go', {'tab': 1, 'to': 'reload', 'timeout_ms': 400})
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual((result['loaded'], result['until_met']), (False, None))
        self.assertEqual(result['untrusted_content']['outline'], before, 'what is there at the timeout')

    def test_until_returns_when_the_text_is_there_on_a_page_that_never_goes_quiet(self):
        self.browser.restless = True
        result = self.chrome.going('go', {'tab': 1, 'url': SITE + '/next', 'until': {'text': 'arrived'}})
        self.assertEqual((result['loaded'], result['until_met']), (False, True))
        result = self.chrome.going('go', {'tab': 1, 'url': SITE + '/other', 'until': {'text': 'never there'}, 'timeout_ms': 300})
        self.assertEqual((result['loaded'], result['until_met']), (False, False))
        self.browser.restless = False
        result = self.chrome.going('go', {'tab': 1, 'url': SITE + '/third', 'until': {'gone': 'Delete'}})
        self.assertEqual(result['until_met'], True)

    def test_until_never_counts_before_the_navigation_arrived(self):
        # "Delete" is on the old page; the new one comes after many looks and doesn't hold it.
        self.browser.delay = 10 ** 6
        result = self.chrome.going('go', {'tab': 1, 'url': SITE + '/next', 'until': {'text': 'Delete'}, 'timeout_ms': 300})
        self.assertEqual((result['loaded'], result['until_met']), (False, False))

    def test_the_wait_ends_by_its_second_and_timeout_ms_counts_from_the_start(self):
        self.browser.delay = 10 ** 6
        with patch.object(going, 'WAIT', .3):
            started = time.monotonic()
            result = self.chrome.going('go', {'tab': 1, 'url': SITE + '/next', 'timeout_ms': 15000})
            self.assertLess(time.monotonic() - started, 1.5)
        self.assertFalse(result['loaded'])

    def test_a_dialog_while_waiting_stops_the_wait(self):
        self.browser.delay = 1
        self.browser.queued.append([0, 1, lambda: self.browser.states[1].update(dialog=True)])
        self.browser.outlines[1]['dialog'] = {'kind': 'alert', 'text': 'Hello'}
        result = self.chrome.going('go', {'tab': 1, 'url': SITE + '/next'})
        self.assertFalse(result['loaded'])

    def test_a_command_given_up_on_may_have_run_and_is_never_called_expired(self):
        original = self.browser.call
        def slow(name, **args):
            if name == 'navigate':
                self.browser.dispatched.append((name, args))
                raise Refused('expired', "No answer came in this command's time; it was given up.")
            return original(name, **args)
        self.browser.call = slow
        exc = self.refused_after('go', {'tab': 1, 'url': SITE + '/next'}, 'unknown')
        self.assertEqual(str(exc), going.MAY_HAVE_RUN)
        [operation] = self.operation('chrome_navigate')
        self.assertEqual(operation['state'], 'unknown')

    def refused_after(self, verb, args, code):
        with self.assertRaises(Refused) as caught:
            self.chrome.going(verb, args)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        return caught.exception

    def test_a_page_that_cant_be_read_after_going_is_the_tabs_error_with_its_tab(self):
        original = self.browser.call
        def excluded(name, **args):
            if name == 'outline' and self.browser.loads:
                raise Refused('refused', 'approval/settings pages and non-web addresses belong to the owner')
            return original(name, **args)
        self.browser.call = excluded
        result = self.chrome.going('open', {'url': SITE + '/redirects'})
        self.assertEqual(result['error'], {'code': 'refused', 'message': 'approval/settings pages and non-web addresses belong to the owner'})
        self.assertEqual((result['tab'], result['loaded']), (10, False))

    # --- a taken tab that hasn't had its reload --------------------------------

    def test_go_in_a_taken_tab_with_typing_answers_reload_required_and_leaves_the_page(self):
        self.browser.needs_reload.add(1)
        self.browser.report = REPORT
        exc = self.refused_after('go', {'tab': 1, 'url': SITE + '/next'}, 'reload_required')
        self.assertEqual(str(exc), loss.MESSAGE)
        self.assertEqual(untrusted(exc)['untrusted_content']['loss']['act'], 'first_input')
        self.assertEqual(self.browser.sent('prepare_control', 'navigate'), ['prepare_control'], 'no navigation')
        self.assertEqual(self.browser.loads, [], 'the page is not replaced')
        [operation] = self.operation('chrome_prepare_control')
        self.assertEqual(operation['state'], 'failed')

    def test_go_in_a_taken_tab_without_typing_reloads_under_its_guard_and_then_navigates(self):
        self.browser.needs_reload.add(1)
        result = self.chrome.going('go', {'tab': 1, 'url': SITE + '/next'})
        self.assertTrue(result['loaded'])
        self.assertEqual([load[0] for load in self.browser.loads], ['guarded reload', 'navigate'])
        self.assertEqual(self.browser.dispatched[0], ('prepare_control', {'tab': 1, 'discard_unsaved': False}))
        # With discard_unsaved the flag goes to both, as on main.
        self.browser.needs_reload.add(1)
        self.browser.report = REPORT
        self.chrome.going('go', {'tab': 1, 'url': SITE + '/third', 'discard_unsaved': True})
        self.assertEqual([args.get('discard_unsaved') for name, args in self.browser.dispatched[-2:]], [True, True])

    def test_reload_in_a_taken_tab_is_the_guarded_reload_once(self):
        self.browser.needs_reload.add(1)
        result = self.chrome.going('go', {'tab': 1, 'to': 'reload'})
        self.assertTrue(result['loaded'])
        self.assertEqual([load[0] for load in self.browser.loads], ['guarded reload'])
        self.assertEqual(self.browser.sent('prepare_control', 'navigate'), ['prepare_control'])

    def test_go_in_a_claude_tab_keeps_mains_guard_for_unsaved_work(self):
        self.browser.report = REPORT
        exc = self.refused_after('go', {'tab': 1, 'to': 'back'}, 'reload_required')
        self.assertEqual(untrusted(exc)['untrusted_content']['loss']['fields'], REPORT['fields'])
        self.assertEqual(self.browser.loads, [])
        self.assertEqual(self.browser.sent('prepare_control'), [], 'a Claude tab needs no guarded reload')


if __name__ == '__main__':
    unittest.main()
