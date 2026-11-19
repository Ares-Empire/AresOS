"""Brief 28a, items 3 and 3a: what an operation shows of its page.

Item 3: every address that leaves the service goes through `public_address`,
in the public form for a question, a description and a result, in the short
form for what the audit log holds (stage texts, the page-step warning). The
payload keeps every full address, and the extension still compares them.

Item 3a: a description shows each list as its chosen options and their
number, and a `select` step's target also the option it will choose; the
payload keeps every option, and the command the bridge gets carries them. F4
(efficiency-fixtures.mjs: 25 fields, a Country list of 200 options) is asked
about once, within 9,000 bytes, where main refused it.

The tests drive the real Bridge against test_field_descriptions' fake native
host, the Engine and the public MCP/CLI text.
"""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome import projection
from aresos_control.common import Refused, canonical, visible
from test_field_descriptions import SESSION, SITE, Host, control, page_frame, target
import test_field_descriptions
import test_engine as fixture

# A sign-in shaped value: 40 characters, letters of both cases and digits.
MARKER = 'mK3vT9qLx2RbW8nZ4pYc7HdJ1sFgA6eU5oNiV0tB'
PAGE = SITE + '/shop?q=red+shoes&code=' + MARKER + '#access_token=' + MARKER
FRAME = 'https://frame.test/reset/' + MARKER + '?session=' + MARKER
ACTION = SITE + '/save?page=2&sig=' + MARKER
LINK = SITE + '/go?v=' + MARKER + '&q=red+shoes'
DIALOG = 'https://user:' + MARKER + '@frame.test/dialog?state=' + MARKER


def options(count, chosen=(), prefix='Country ', value='c'):
    return [{'label': prefix + str(index), 'value': value + str(index), 'selected': index in chosen, 'disabled': False}
            for index in range(count)]


def select(element, label, items, multiple=False):
    chosen = [option['value'] for option in items if option['selected']]
    return control(element, label, type='select-multiple' if multiple else 'select-one', multiple=multiple,
                   value=chosen[0] if chosen else '', options=items)


def f4_fields(filled=6, text='Filled line'):
    """F4's form as the reader's field() gives it in a watched Claude tab."""
    fields = [control('e2', '', name='csrf', type='hidden', hidden=True, value='fixture-csrf'),
              control('e3', '', name='step', type='hidden', hidden=True, value='2'),
              control('e4', '', name='cart', type='hidden', hidden=True, value='fixture-cart')]
    fields += [control('e%d' % (5 + index), 'Line %d' % index, name='line%d' % index,
                       value=('%s %d' % (text, index)) if index < filled else 'Value %d' % index) for index in range(10)]
    fields += [control('e15', 'Born', name='born', type='date', value='2001-02-03'),
               control('e16', 'News', name='news', type='checkbox', checked=True, value='on'),
               control('e17', 'Offers', name='offers', type='checkbox', value='on'),
               control('e18', 'Plan', name='', type='fieldset'),
               control('e19', 'Free', name='plan', type='radio', checked=True, value='free'),
               control('e20', 'Paid', name='plan', type='radio', value='paid'),
               select('e21', 'Country', options(200, chosen=(7,))),
               select('e22', 'Size', [{'label': size, 'value': size, 'selected': size == 'M', 'disabled': False} for size in 'SML']),
               control('e23', 'Email', name='email', type='email', value='not-an-address'),
               control('e24', 'Password', name='password', type='password', password=True),
               control('e25', 'One-time code', name='one_time', password=True),
               control('e26', 'Code', name='code_text', value='Value code'),
               control('e27', 'Nickname', name='nickname', value=''),
               control('e28', 'Age', name='age', type='number', value='30'),
               control('e29', 'Volume', name='volume', type='range', value='40'),
               control('e30', 'Find', name='find', type='search', value=''),
               control('e31', 'Dark', name='dark', type='checkbox', value='on'),
               control('e32', 'Save', name='', type='submit', value='')]
    return fields


def form(fields, action=SITE + '/receive?case=efficiency-f4-run', search=True):
    return {'element': 'e1', 'action': action, 'method': 'post', 'encoding': 'application/x-www-form-urlencoded',
            'target': '', 'browsing_target': '_self', 'search': search, 'fields': fields}


def size(approval):
    """Bytes of the approval as `approval_input` counts them."""
    return len(canonical(approval).encode())


def walk(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def unprojected(state):
    """A description's page facts without item 3b's descriptions and item 3a's list keys."""
    if isinstance(state, dict):
        return {key: unprojected(item) for key, item in state.items()
                if key not in {'description', 'chosen', 'option_count', 'choosing'}}
    if isinstance(state, list):
        return [unprojected(item) for item in state]
    return state


def optionless(state):
    if isinstance(state, dict):
        return {key: optionless(item) for key, item in state.items() if key != 'options'}
    if isinstance(state, list):
        return [optionless(item) for item in state]
    return state


class Pages(Host):
    """The fake host, with an input reply that reports the page, a confirmation and a dialog, as background.js does."""

    def __init__(self):
        super().__init__()
        self.reply = {'checked': True, 'dispatched': True, 'no_change': False, 'steps': [], 'dialog': None,
                      'uncertain_finish': False,
                      'confirmations': [{'kind': 'confirm', 'text': 'Sure?', 'frame_url': FRAME, 'button': 'OK', 'frame': 0}],
                      'page': {'available': True, 'url': PAGE, 'title': 'Shop', 'notices': [],
                               'change': {'element': 'e6', 'element_present': True}}}
        self.queued = []

    def answer(self, command):
        if command['name'] == 'input':
            return {'ok': True, 'data': copy.deepcopy(self.reply)}
        if command['name'] == 'queued_steps':
            return {'ok': True, 'data': copy.deepcopy(self.queued)}
        if command['name'] == 'ack_steps':
            self.queued = [step for step in self.queued if step not in command['steps']]
            return {'ok': True, 'data': {'acknowledged': True}}
        return super().answer(command)


class Projection(unittest.TestCase):
    # The harness of item 3b's tests, without running them again here.
    setUp = test_field_descriptions.Descriptions.setUp
    tearDown = test_field_descriptions.Descriptions.tearDown
    call = test_field_descriptions.Descriptions.call
    public = test_field_descriptions.Descriptions.public
    reference = test_field_descriptions.Descriptions.reference

    def host_page(self, **frame):
        self.host.facts['url'] = PAGE
        self.host.facts['frames'] = [page_frame(url=PAGE, **frame)]

    def operation(self, operation_id):
        return self.engine.store.get('op:' + operation_id)

    def log(self):
        return self.call('control_log')

    def assert_hidden(self, *values):
        for value in values:
            self.assertNotIn(MARKER, json.dumps(value, ensure_ascii=False))

    # Item 3: addresses.

    def addressed_page(self):
        self.host = Pages()
        self.chrome.bridge.connection = self.host
        self.host.facts['url'] = PAGE
        fields = [control('e5', 'Note', value='text'), control('e6', 'Send', type='submit', value='')]
        self.host.facts['frames'] = [page_frame(url=PAGE, effective_url=PAGE, form=form(fields, ACTION, search=False)),
                                     page_frame(3, FRAME, title='Frame', effective_url=FRAME,
                                                editable=[control('e1', 'Message', value='left')])]
        self.host.targets['e6'] = target('e6', 'Send', role='button', editable=False, submit=True, value='')
        self.host.targets['e5'] = target('e5', 'Note', value='text')
        self.host.targets['e7'] = target('e7', 'Docs', role='link', editable=False, href=LINK, browsing_target='_self')

    def test_a_prepared_operation_shows_public_addresses_and_records_short_ones_while_the_payload_keeps_them_whole(self):
        self.addressed_page()
        prepared = self.public(self.call('chrome_click', self.reference('e6')), 'chrome_click')['approval']
        state = prepared['description']['untrusted_content']['page_state']
        self.assert_hidden(prepared)
        # The public form: the ordinary query shows, the sign-in parts are marked.
        self.assertEqual(state['url'], 'fixture.test/shop?q=red+shoes&code=…#access_token=…')
        self.assertEqual(state['form']['action'], 'fixture.test/save?page=2&sig=…')
        self.assertIn('to fixture.test/save?page=2&sig=… (post', prepared['question'])
        self.assertIn('On fixture.test/shop?q=red+shoes&code=…#access_token=…,', prepared['question'])
        operation = self.operation(prepared['operation_id'])
        binding = operation['payload']['binding']
        self.assertEqual([binding['url'], binding['frame_url'], binding['form']['action']], [PAGE, PAGE, ACTION])
        submitted = self.public(self.call('chrome_submit', prepared), 'chrome_submit')
        self.assertEqual(submitted['operation']['state'], 'done')
        [command] = self.host.sent('input')
        self.assertEqual(command['binding'], binding, 'the extension gets and compares every full address')
        stages = self.operation(prepared['operation_id'])['stages']
        texts = [stages['confirmation']['untrusted_content'], stages['page']['untrusted_content']]
        self.assert_hidden(stages, texts, self.log(), self.public(self.call('chrome_operation_status', {'operation_id': prepared['operation_id']}), 'chrome_operation_status'))
        for text in texts:
            self.assertNotIn('red', text, 'a record holds no query')
        # Stage texts are canonical JSON of escaped text: the mark stands where the query and fragment were.
        self.assertRegex(stages['page']['untrusted_content'], r'"url":"fixture\.test/shop\?[^"=&]+#[^"=&]+"')
        self.assertRegex(stages['confirmation']['untrusted_content'], r'"frame_url":"frame\.test/reset/[^"=&/]+\?[^"=&]+"')

    def test_a_link_and_a_send_outside_a_form_show_public_addresses(self):
        self.addressed_page()
        self.host.facts['frames'][0]['form'] = None
        prepared = self.public(self.call('chrome_click', self.reference('e7')), 'chrome_click')
        # A free link: the committed description and the result.
        operation = self.operation(prepared['operation_id'])
        state = operation['approval']['description']['untrusted_content']['page_state']
        self.assertEqual(state['target']['href'], 'fixture.test/go?v=…&q=red+shoes')
        self.assertEqual(operation['payload']['binding']['target']['href'], LINK)
        self.assertEqual(prepared['untrusted_content']['page']['url'], 'fixture.test/shop?q=red+shoes&code=…#access_token=…')
        self.assertIn('red', canonical(prepared), 'a result shows an ordinary query')
        self.assertNotIn('red', canonical(operation['stages']['page']), 'its record does not')
        self.assert_hidden(prepared, operation['approval'], operation['stages'], self.log())
        # A send outside a form: every frame's editable fields with their frame's address.
        self.host.targets['e2'] = target('e2', 'Send', role='button', editable=False)
        asked = self.public(self.call('chrome_click', self.reference('e2')), 'chrome_click')['approval']
        self.assert_hidden(asked)
        state = asked['description']['untrusted_content']['page_state']
        self.assertEqual([item['url'] for item in state['editable']], ['fixture.test/shop?q=red+shoes&code=…#access_token=…', 'frame.test/reset/…?session=…'])
        binding = self.operation(asked['operation_id'])['payload']['binding']
        self.assertEqual([item['url'] for item in binding['editable']], [PAGE, FRAME])

    def test_a_native_dialogs_question_and_the_navigations_description_hide_the_marker(self):
        self.addressed_page()
        native = {'session': SESSION, 'tab': 1, 'control': 'control-1', 'url': PAGE, 'title': 'Shop',
                  'effective_url': DIALOG, 'dialog': {'kind': 'confirm', 'text': 'Delete this?', 'frame': 0, 'frame_url': DIALOG, 'button': 'OK'}}
        answer = self.host.answer
        self.host.answer = lambda command: {'ok': True, 'data': copy.deepcopy(native)} if command['name'] == 'dialog_facts' else answer(command)
        prepared = self.public(self.call('chrome_dialog', {'tab': 1, 'expected': native['dialog'], 'accept': True}), 'chrome_dialog')['approval']
        self.assert_hidden(prepared)
        self.assertEqual(prepared['description']['untrusted_content']['page_state']['dialog']['frame_url'], 'frame.test/dialog?state=…')
        self.assertEqual(self.operation(prepared['operation_id'])['payload']['binding']['dialog']['frame_url'], DIALOG)
        # A navigation's committed description; the payload keeps the address it navigated to.
        self.host.answer = lambda command: ({'ok': True, 'data': {'session': SESSION, 'tab': 1, 'url': PAGE, 'title': 'Shop', 'frames': [{'frame': 0, 'url': PAGE, 'document': 'd'}]}}
                                            if command['name'] == 'tab_context' else
                                            {'ok': True, 'data': {'navigated': True, 'page': {'available': True, 'url': LINK}}}
                                            if command['name'] == 'navigate' else answer(command))
        result = self.public(self.call('chrome_navigate', {'tab': 1, 'url': LINK}), 'chrome_navigate')
        operation = self.operation(result['operation_id'])
        self.assert_hidden(result, operation['approval'], operation['stages'], self.log())
        self.assertEqual(operation['payload']['url'], LINK)
        self.assertEqual(operation['payload']['before']['url'], PAGE)
        self.assertEqual(result['untrusted_content']['page']['url'], 'fixture.test/go?v=…&q=red+shoes')
        self.assertEqual(operation['stages']['page']['page']['url'], 'fixture.test/go?…')

    def test_a_typed_read_question_shows_the_public_form(self):
        self.host.typed['url'] = PAGE
        self.host.typed['frames'][0]['url'] = self.host.typed['frames'][0]['effective_url'] = FRAME
        approval = self.public(self.call('chrome_prepare_read_typed_fields', {'tab': 1}), 'chrome_prepare_read_typed_fields')['approval']
        self.assert_hidden(approval)
        self.assertIn('On fixture.test/shop?q=red+shoes&code=…#access_token=…, tab', approval['question'])
        self.assertIn('frame 0 (frame.test): "Note" (1 of 2)', approval['question'])
        [operation] = [item for _, item in self.engine.store.iter_items('op:')]
        self.assertEqual(operation['payload']['binding']['url'], PAGE)

    def test_the_page_step_warning_holds_no_address(self):
        self.addressed_page()
        self.host.queued = [{'id': 's1', 'kind': 'activation', 'document': 'document-0', 'frame': 0, 'label': 'Docs',
                             'element': 'e7', 'submitter': None, 'cancellable': True}]
        self.assertTrue(self.call('chrome_read', {'tab': 1})['ok'])
        self.assertEqual(self.host.sent('ack_steps')[0]['steps'][0]['id'], 's1')
        log = self.log()
        self.assertIn('chrome_page_step', canonical(log))
        self.assert_hidden(log)
        self.assertNotIn('red', canonical([entry.get('untrusted_content') for entry in log['data']['items']]))

    # Item 3a: lists.

    def f4(self, fields=None, search=True, **frame):
        self.host.facts['frames'] = [page_frame(form=form(fields or f4_fields(), search=search), **frame)]
        self.host.targets['e32'] = target('e32', 'Save', role='button', editable=False, submit=True, value='')

    def assert_lists(self, state, binding):
        """No `options` anywhere; every other key equals the binding's, apart from item 3's addresses and item 3b's words."""
        for item in walk(state):
            self.assertNotIn('options', item)
        self.assertEqual(unprojected(state), visible(projection.addresses(optionless(binding))))

    def test_f4_is_asked_once_within_9000_bytes_and_its_payload_keeps_every_option(self):
        self.f4()
        prepared = self.public(self.call('chrome_click', self.reference('e32')), 'chrome_click')['approval']
        state = prepared['description']['untrusted_content']['page_state']
        country = next(field for field in state['form']['fields'] if field['label'] == 'Country')
        self.assertEqual(country['chosen'], [{'label': 'Country 7', 'value': 'c7', 'selected': True, 'disabled': False}])
        self.assertEqual(country['option_count'], 200)
        self.assertEqual(next(field for field in state['form']['fields'] if field['label'] == 'Size')['option_count'], 3)
        for index in range(6):
            self.assertIn({'description': '"Line %d"' % index, 'value': 'Filled line %d' % index},
                          [{key: field[key] for key in ('description', 'value')} for field in state['form']['fields'] if 'value' in field])
        operation = self.operation(prepared['operation_id'])
        self.assert_lists(state, operation['payload']['binding'])
        measured = size(prepared)
        print('F4 approval: %d bytes, question %d characters' % (measured, len(prepared['question'])))
        self.assertLessEqual(measured, 9000)
        payload_country = next(field for field in operation['payload']['binding']['form']['fields'] if field['label'] == 'Country')
        self.assertEqual(len(payload_country['options']), 200)
        self.public(self.call('chrome_submit', prepared), 'chrome_submit')
        [command] = self.host.sent('input')
        self.assertEqual(command['binding'], operation['payload']['binding'], 'the extension gets every option to compare')

    def test_f4_with_its_options_left_whole_is_refused_as_on_main(self):
        self.f4()
        with patch.object(projection, 'lists', lambda value, choosing=None: value):
            result = self.call('chrome_click', self.reference('e32'))
        self.assertEqual(result['error']['code'], 'asking_input_too_large')
        self.assertEqual(list(self.engine.store.iter_items('op:')), [])

    def test_every_place_a_list_sits_shows_its_chosen_options_and_count(self):
        many = select('e40', 'Toppings', options(5, chosen=(1, 3), prefix='Topping ', value='t'), multiple=True)
        none = select('e41', 'Region', options(4, prefix='Region ', value='r'))
        dialog_list = select('e42', 'Account', options(3, chosen=(2,), prefix='Account ', value='a'))
        self.f4(f4_fields() + [many, none])
        self.host.targets['e32']['page_dialog'] = {'element': 'e44', 'kind': 'dialog', 'text': 'Save?', 'button': 'Save', 'fields': [dialog_list]}
        prepared = self.public(self.call('chrome_click', self.reference('e32')), 'chrome_click')['approval']
        state = prepared['description']['untrusted_content']['page_state']
        fields = {field['label']: field for field in state['form']['fields']}
        self.assertEqual([option['value'] for option in fields['Toppings']['chosen']], ['t1', 't3'])
        self.assertEqual((fields['Region']['chosen'], fields['Region']['option_count']), ([], 4))
        self.assertEqual([option['value'] for option in state['target']['page_dialog']['fields'][0]['chosen']], ['a2'])
        self.assert_lists(state, self.operation(prepared['operation_id'])['payload']['binding'])
        # An affected item's fields.
        self.host.facts['frames'] = [page_frame(item='Unit price 25 Pay', item_fields=[select('e43', 'Quantity', options(9, chosen=(3,), prefix='', value='q'))])]
        self.host.targets['e45'] = target('e45', 'Pay', role='button', editable=False)
        prepared = self.public(self.call('chrome_click', self.reference('e45')), 'chrome_click')['approval']
        state = prepared['description']['untrusted_content']['page_state']
        self.assertEqual(([option['value'] for option in state['item_fields'][0]['chosen']], state['item_fields'][0]['option_count']), (['q3'], 9))
        self.assert_lists(state, self.operation(prepared['operation_id'])['payload']['binding'])
        # The editable fields of a send outside a form.
        self.host.facts['frames'] = [page_frame(editable=[control('e1', 'Message', value='hi'), select('e2', 'Country', options(200, chosen=(7,)))])]
        self.host.targets['e3'] = target('e3', 'Send', role='button', editable=False)
        prepared = self.public(self.call('chrome_click', self.reference('e3')), 'chrome_click')['approval']
        state = prepared['description']['untrusted_content']['page_state']
        self.assertEqual(state['editable'][0]['fields'][1]['option_count'], 200)
        self.assert_lists(state, self.operation(prepared['operation_id'])['payload']['binding'])

    def test_a_select_that_asks_shows_what_it_will_choose_and_a_free_one_commits_it(self):
        self.chrome.bridge.version = '159.0.1.0'  # an unqualified major: every select asks
        for items, value, expected in [([{'label': size, 'value': size.lower(), 'selected': size == 'M', 'disabled': False} for size in 'SML'], 'l', 'L'),
                                       (options(200, chosen=(7,)), 'c12', 'Country 12')]:
            with self.subTest(options=len(items)):
                field = select('e21', 'Country', items)
                self.f4([field if item['element'] == 'e21' else item for item in f4_fields()])
                self.host.targets['e21'] = target('e21', 'Country', role='combobox', editable=False, value=field['value'], options=items)
                prepared = self.public(self.call('chrome_select', {**self.reference('e21'), 'value': value}), 'chrome_select')['approval']
                shown = prepared['description']['untrusted_content']['page_state']['target']
                self.assertEqual([option['label'] for option in shown['choosing']], [expected])
                self.assertEqual(shown['chosen'], [option for option in items if option['selected']])
                self.assertEqual(shown['option_count'], len(items))
                self.assertLessEqual(size(prepared), 9000)
                self.assert_lists(prepared['description']['untrusted_content']['page_state'], self.operation(prepared['operation_id'])['payload']['binding'])
        # A free select's committed description shows `choosing` the same way.
        self.chrome.bridge.version = '157.0.1.0'
        self.host.facts['frames'] = [page_frame()]
        self.host.targets['e9'] = target('e9', 'Size', role='combobox', editable=False, value='m',
                                         options=[{'label': size, 'value': size.lower(), 'selected': size == 'M', 'disabled': False} for size in 'SML'])
        result = self.public(self.call('chrome_select', {**self.reference('e9'), 'value': 's'}), 'chrome_select')
        committed = self.operation(result['operation_id'])['approval']['description']['untrusted_content']['page_state']['target']
        self.assertEqual([option['label'] for option in committed['choosing']], ['S'])
        self.assertEqual(committed['option_count'], 3)
        self.assertNotIn('options', committed)

    # Item 3a: forms that still don't fit.

    def act(self, element):
        """The private step entry (Chrome.act), with the reference resolved to the host's facts."""
        reference = self.reference(element)['reference']
        def acting(tab, ref):
            facts, frame = self.chrome.facts(reference)
            return facts, frame, reference
        with patch.object(self.chrome, 'acting', acting), patch.object(self.chrome.references, 'acted', lambda *args: None):
            return self.chrome.act('click', {'tab': 1, 'ref': 'fixture1'})

    def assert_refused(self, fields, advice, **frame):
        self.f4(fields, search=False, **frame)
        with self.assertRaises(Refused) as caught:
            self.act('e32')
        self.assertEqual(caught.exception.code, 'asking_input_too_large')
        self.assertTrue(str(caught.exception).endswith(' ' + advice), str(caught.exception))
        self.assertTrue(str(caught.exception).startswith('The '), 'the refusal keeps its own sentence first')
        self.assertEqual(list(self.engine.store.iter_items('op:')), [], 'no operation is written')
        self.assertEqual(self.host.sent('input'), [])

    def test_a_form_still_too_large_is_refused_with_chromes_advice(self):
        save = f4_fields()[-1]
        self.assert_refused([control('e%d' % (100 + index), 'Field %d' % index, value='') for index in range(120)] + [save], projection.OWNER)
        self.assert_refused([control('e2', '', name='state', type='hidden', hidden=True, value='h' * 20000), save], projection.OWNER)
        self.assert_refused([select('e3', 'Many', options(250, chosen=range(250), prefix='Option ', value='o'), multiple=True), save], projection.OWNER)
        # A textarea's text also stands in the text next to Send, which the question quotes.
        self.assert_refused([control('e4', 'Text', type='textarea', value='t' * 5000), save], projection.SHORTEN,
                            compose={'element': 'e1', 'whole_page': False, 'text': 'Text ' + 't' * 5000 + ' Save'})
        # F4 itself is prepared through the same entry.
        self.f4()
        self.assertEqual(self.act('e32')['state'], 'reserved')

    def test_a_held_submission_too_large_to_ask_about_stays_stopped_and_is_acknowledged(self):
        self.host = Pages()
        self.chrome.bridge.connection = self.host
        self.f4([control('e%d' % (100 + index), 'Field %d' % index, value='') for index in range(120)] + [f4_fields()[-1]])
        step = {'id': 's1', 'kind': 'native_submit', 'document': 'document-0', 'frame': 0, 'label': 'Save',
                'element': 'e1', 'submitter': 'e32', 'cancellable': True}
        self.host.queued = [step]
        followups = self.chrome.steps([step], 1)
        self.assertEqual(followups, [{'stopped': True, 'code': 'asking_input_too_large',
                                      'reason': followups[0]['reason']}])
        self.assertTrue(followups[0]['reason'].endswith(projection.OWNER))
        self.assertEqual(self.host.sent('ack_steps')[0]['steps'], [step])
        [(key, source)] = [(key, item) for key, item in self.engine.store.iter_items('intent:chrome:')]
        self.assertEqual((source['state'], source['resumable']), ('done', False))
        self.assertEqual([item for _, item in self.engine.store.iter_items('op:')], [])
        self.assertEqual(self.host.sent('resume'), [])
        # The next read meets it again only as done and not resumable: acknowledged, never prepared or resumed.
        self.assertEqual(self.chrome.steps([step], 1), [])
        self.assertEqual(self.host.sent('resume') + self.host.sent('input'), [])
        # A read that meets it returns its normal result.
        self.host.queued = [step]
        self.assertTrue(self.call('chrome_read', {'tab': 1})['ok'])


if __name__ == '__main__':
    unittest.main()
