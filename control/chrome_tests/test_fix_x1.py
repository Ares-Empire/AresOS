"""X1 regressions based on SECURITY-REVIEW-1 and REVIEW-1 scratch probes."""
import re
import time
import unittest
from unittest.mock import patch
from aresos_control.definitions import Action
from aresos_control.chrome.definitions import OUTLINE

from aresos_control.chrome.address import public_address
from aresos_control.chrome import view
from aresos_control.common import Refused, canonical
import test_outline_action as support
from view_fixtures import f4, node, reply


class Addresses(unittest.TestCase):
    def test_credential_fragments_keep_filtering_with_slashes_before_inside_and_after_values(self):
        # This independent list is the brief's list, not the implementation's.
        names = 'token code key secret signature sig password passwd pwd auth session sid otp ticket state nonce jwt access_token id_token refresh_token api_key client_secret sessionToken'.split()
        for name in names:
            for fragment in (f'next=/home&{name}=fixture-value', f'{name}=/fixture-value',
                             f'{name}=fixture/value', f'{name}=fixture-value/',
                             f'{name}=fixture-value&next=/home', f'{name}=fixture-value?next=/home'):
                with self.subTest(fragment=fragment):
                    shown = public_address('https://fixture.test/#' + fragment)
                    self.assertNotIn('fixture-value', shown)
                    self.assertNotIn('fixture/value', shown)
                    self.assertIn(name + '=…', shown)
        self.assertEqual(public_address('https://fixture.test/#otp=739281&next=/home'),
                         'fixture.test/#otp=…&next=/home')
        self.assertEqual(public_address('https://fixture.test/#access_token=fixture/part'),
                         'fixture.test/#access_token=…')
        self.assertEqual(public_address('https://fixture.test/#/inbox/thread/1'),
                         'fixture.test/#/inbox/thread/1')
        self.assertEqual(public_address('https://fixture.test/#/inbox/thread/1?otp=fixture/part&page=2'),
                         'fixture.test/#/inbox/thread/1?otp=…&page=2')

        for route in ('/reset/fixture-value=tail', 'inbox/login/fixture-value=tail'):
            self.assertNotIn('fixture-value', public_address('https://fixture.test/#' + route))

    def test_question_mark_after_credential_value_never_switches_to_route_parsing(self):
        for tail in ('?q=/home', '?/home', '?q=/home&view=list'):
            with self.subTest(tail=tail):
                self.assertNotIn('fixture-value', public_address('https://fixture.test/#otp=fixture-value' + tail))


class Adapter(unittest.TestCase):
    setUp = support.Adapter.setUp
    tearDown = support.Adapter.tearDown
    read = support.Adapter.read
    outline = support.Adapter.outline
    reference = support.Adapter.reference

    def test_failing_reads_keep_6000_control_reference_table_bounded(self):
        for failure in ('header', 'cursor', 'wrong-query', 'measure'):
            self.chrome.references.close(1)
            for attempt in range(3):
                with self.subTest(failure=failure, attempt=attempt):
                    raw = support.fixture(lambda: reply([node(i+1, 'button', name='Go') for i in range(6000)]))
                    raw['frames'][0]['document'] = f'{failure}-{attempt}'
                    if failure == 'header':
                        raw['title'] = 'T' * 100000
                    self.browser.outlines[1] = raw
                    args = {'tab': 1}
                    if failure in ('cursor', 'wrong-query'):
                        query = view.asked(full=failure == 'wrong-query')
                        args['cursor'] = '1.' + view._stamp(query) + '.' + '0'*16
                    original = self.chrome.outline_measure
                    if failure == 'measure':
                        def broken(_notice):
                            raise Refused('transport_error', 'Synthetic measure failure')
                        self.chrome.outline_measure = broken
                    try:
                        with patch.dict('aresos_control.engine.BY_NAME', {'chrome_outline': Action('chrome','outline','read',OUTLINE,'X1 internal regression')}):
                            result = self.engine.request({'v':1,'method':'call','action':'chrome_outline','arguments':args})
                        if failure == 'cursor':
                            self.assertTrue(result['ok'], result)
                            self.assertEqual(result['data']['reads'][0]['error']['code'], 'stale_reference')
                        else:
                            self.assertFalse(result['ok'], result)
                            self.assertEqual(result['error']['code'], {'header':'result_too_large','wrong-query':'invalid_input','measure':'transport_error'}[failure])
                    finally:
                        self.chrome.outline_measure = original
                    self.assertLessEqual(len(self.chrome.references._tabs[1]), 5000)
                    self.assertEqual(len(self.chrome.references._references), len(self.chrome.references._tabs[1]))

    def full_options(self, by_form):
        self.browser.outlines[1] = support.fixture(f4)
        self.browser.options = [{'label': 'Country %d' % i, 'value': 'c%d' % i, 'chosen': i==7} for i in range(200)]
        args = {'tab':1, 'full':True, 'max':1000}
        if by_form:
            args['ref'] = self.reference(self.outline(tab=1)['untrusted_content']['outline'], 'form')
        chunks=[]; started=time.monotonic()
        for _ in range(20):
            result=self.outline(**args)
            chunks.append(result['untrusted_content']['outline'])
            self.assertLess(len(canonical(result).encode()), 48*1024)
            if result['cursor'] is None:
                break
            args['cursor']=result['cursor']
        else:
            self.fail('paging did not finish')
        self.assertLess(time.monotonic()-started, 7)
        text=''.join(chunks)
        self.assertEqual(re.findall(r'option "Country (\d+)"', text), [str(i) for i in range(200)])
        self.assertNotIn('150 more',text)
        self.assertGreater(len(chunks),1)
        self.assertTrue(self.browser.named('options'))

    def test_page_full_reads_all_200_f4_options_through_pages(self):
        self.full_options(False)

    def test_form_full_reads_all_200_f4_options_through_pages(self):
        self.full_options(True)

    def test_full_options_share_the_read_deadline_and_expiry_returns_not_read(self):
        self.browser.outlines[1] = support.fixture(f4)
        original = self.browser.call
        deadlines = []
        def call(name, **args):
            if name in ('outline', 'options'):
                deadlines.append((name, self.browser.end))
            if name == 'options':
                self.assertIsNotNone(self.browser.end)
                self.assertLessEqual(self.browser.end-time.monotonic(), 7)
                raise Refused('expired', 'Synthetic options timeout')
            return original(name, **args)
        self.browser.call = call
        result = self.read(tab=1, full=True)
        self.assertIn('error',result['reads'][0])
        self.assertEqual(result['reads'][0]['error']['code'], 'not_read')
        self.assertEqual([name for name, _ in deadlines], ['outline','options'])
        self.assertEqual(deadlines[0][1], deadlines[1][1])

    def test_form_full_fetches_only_options_in_its_subtree(self):
        raw = support.fixture(f4)
        raw['frames'][0]['nodes'].append(node(30, 'combobox', name='Outside', option_count=300))
        self.browser.outlines[1] = raw
        form = self.reference(self.outline(tab=1)['untrusted_content']['outline'], 'form')
        original = self.browser.call
        fetched = []
        def call(name, **args):
            if name == 'options':
                fetched.append(args['element'])
                self.assertEqual(args['element'],18)
            return original(name, **args)
        self.browser.call = call
        self.browser.options = [{'label':f'Country {i}'} for i in range(200)]
        text = self.outline(tab=1,ref=form,full=True,max=40000)['untrusted_content']['outline']
        self.assertEqual(fetched,[18])
        self.assertEqual(text.count('option "Country '),200)
        self.assertNotIn('Outside',text)

    def test_ordinary_long_option_is_cut_with_reference_to_whole_label(self):
        label='L'*10000
        self.browser.outlines[1]=support.fixture(lambda: reply([node(1,'combobox',name='Choice',chosen='Small',
            options=[{'label':'Small','chosen':True},{'label':label}])]))
        read=self.outline(tab=1,max=40000)
        text=read['untrusted_content']['outline']
        option=next(line for line in text.splitlines() if 'option "LL' in line)
        self.assertIn('"'+'L'*200+'"…+9,800',option)
        self.assertLess(len(option),250)
        reference=re.search(r'([b-df-hj-np-tv-z]{5}\d+)$',option).group(1)
        args={'tab':1,'ref':reference,'max':1000};chunks=[]
        for _ in range(20):
            result=self.outline(**args);chunks.append(result['untrusted_content']['outline'])
            if result['cursor'] is None:break
            args['cursor']=result['cursor']
        self.assertIn('option "'+label+'"',''.join(chunks))


if __name__ == '__main__':
    unittest.main()
