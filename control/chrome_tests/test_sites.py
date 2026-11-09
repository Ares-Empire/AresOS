"""Plain-Python adapter semantics; no browser, profile, or site connection."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome.policy import HOSTS, FIXED_HOSTS, classify
from aresos_control.chrome.sites import recognize, recipients, KINDS
import test_engine as engine_cases

FIXTURE_HOSTS = {site: [site + '.test'] for site in HOSTS}


def reading(site):
    return {'scope': 'compose-1', 'scope_role': 'dialog' if site == 'gmail' else 'main',
            'account': 'Synthetic account', 'to': 'one@mail.test,two@mail.test',
            'cc': 'copy@mail.test', 'bcc': 'hidden@mail.test', 'subject': 'Synthetic subject',
            'text': 'Full synthetic message\nSecond line', 'chat': 'Synthetic chat',
            'context': 'fixture-repository / branch-1', 'preview': 'Full quoted preview',
            'attachments': [{'label': 'Attachment: fixture.txt', 'text': 'fixture.txt 3 bytes'}],
            'target': 'Send'}


def semantic(site, label='Send', *, key='', verb=None, editable=False, data=None, **kwargs):
    return recognize('https://' + site + '.test/', reading(site) if data is None else data,
                     {'name': label, 'editable': editable}, verb or ('press' if key else 'click'),
                     {'key': key} if key else {}, FIXTURE_HOSTS, **kwargs)


class SiteSemantics(unittest.TestCase):
    def test_shipped_host_lists_and_fixed_list_exactly(self):
        self.assertEqual(HOSTS, {'gmail': ['mail.google.com'], 'whatsapp': ['web.whatsapp.com'],
                                'github': ['github.com'], 'bank': [], 'gemini': ['gemini.google.com'],
                                'deezer': ['www.deezer.com', 'deezer.com']})
        self.assertEqual(FIXED_HOSTS, ['claude.ai', 'console.anthropic.com', 'platform.claude.com'])

    def test_hosts_exact_empty_override_and_disabled_adapters(self):
        for site in HOSTS:
            with self.subTest(site=site):
                self.assertIsNone(semantic(site, enabled={name: False for name in HOSTS}))
                self.assertIsNone(semantic(site, data={}))
                self.assertIsNone(recognize('https://sub.' + site + '.test/', reading(site),
                                          {'name': 'Send'}, 'click', {}, FIXTURE_HOSTS))
        self.assertIsNone(recognize('https://gmail.test/', reading('gmail'), {'name': 'Send'}, 'click', {}, {}))
        self.assertIsNone(recognize('https://[broken', {}, {}, 'click', {}))

    def test_gmail_compose_complete_and_not_a_typing_exemption(self):
        for key, editable in [('', False), ('Enter', False), ('Space', False), ('Ctrl+Enter', True), ('Cmd+Enter', True)]:
            with self.subTest(key=key):
                result = semantic('gmail', key=key, editable=editable)
                self.assertEqual(result['kind'], 'gmail_send')
                self.assertTrue(result['trusted'])
        for field in ['account', 'to', 'cc', 'bcc', 'subject', 'text', 'attachments', 'scope']:
            data = reading('gmail'); data[field] = None
            self.assertIsNone(semantic('gmail', data=data), field)
        self.assertIsNone(semantic('gmail', verb='fill'))
        self.assertIsNone(semantic('gmail', 'Message Body', key='Enter', editable=True))
        self.assertEqual(semantic('gmail', key='#')['effect'], 'delete')
        self.assertFalse(semantic('gmail', key='#')['trusted'])

    def test_exact_recipient_sets_keep_roles_and_quoted_commas(self):
        self.assertEqual(recipients('two@mail.test, one@mail.test;two@mail.test'), ['one@mail.test', 'two@mail.test'])
        self.assertEqual(recipients('"Last, First" <one@mail.test>, two@mail.test'),
                         ['"Last, First" <one@mail.test>', 'two@mail.test'])
        self.assertNotEqual(recipients('"Last, First" <one@mail.test>'), recipients('"Last", First <one@mail.test>'))
        for invalid in ['"Unclosed, one@mail.test', 'One <one@mail.test', 'one@mail.test>', 'one@mail.test,,two@mail.test']:
            self.assertIsNone(recipients(invalid))
            data = reading('gmail'); data['to'] = invalid
            result = semantic('gmail', data=data)
            self.assertEqual(result['effect'], 'send'); self.assertFalse(result['trusted'])
        first = semantic('gmail')['parameters']
        data = reading('gmail'); data['bcc'], data['cc'] = data['cc'], data['bcc']
        self.assertNotEqual(first, semantic('gmail', data=data)['parameters'])

    def test_whatsapp_message_shortcuts_and_no_trusted_kind(self):
        for label, key, editable in [('Send', '', False), ('Type a message', 'Enter', True)]:
            result = semantic('whatsapp', label, key=key, editable=editable)
            self.assertEqual(result['kind'], 'whatsapp_message'); self.assertFalse(result['trusted'])
        for verb, label in [('click', 'Open chat'), ('fill', 'Type a message')]:
            self.assertIsNone(semantic('whatsapp', label, verb=verb))
        for field in ['chat', 'text', 'attachments', 'scope']:
            data = reading('whatsapp'); data[field] = None
            self.assertIsNone(semantic('whatsapp', data=data), field)

    def test_github_actions_and_known_confirmations_are_specific(self):
        # Independent expectations: do not import the production action table.
        cases = [('Comment', 'github_comment', 'send', None),
                 ('Submit review', 'github_review', 'send', None),
                 ('Approve review', 'github_review', 'send', None),
                 ('Request changes', 'github_review', 'send', None),
                 ('Merge pull request', 'github_merge', 'send', 'Merge pull request'),
                 ('Close issue', 'github_close', 'send', 'Close issue'),
                 ('Close pull request', 'github_close', 'send', 'Close pull request'),
                 ('Delete branch', 'github_delete', 'delete', 'Delete branch'),
                 ('Delete tag', 'github_delete', 'delete', 'Delete tag'),
                 ('Delete repository', 'github_delete', 'delete', 'Delete repository'),
                 ('Save settings', 'github_settings', 'send', 'Save settings for')]
        for label, kind, effect, confirmation in cases:
            with self.subTest(label=label):
                result = semantic('github', label)
                self.assertEqual((result['kind'], result['effect']), (kind, effect))
                self.assertFalse(result['trusted'])
                if confirmation:
                    self.assertEqual(result['confirmation'], {'kind': 'confirm', 'text': confirmation + ' fixture-repository / branch-1?',
                                                              'frame_url': 'https://github.test/', 'button': 'OK'})
                else:
                    self.assertNotIn('confirmation', result)
        self.assertIsNone(semantic('github', 'Review settings help'))
        self.assertTrue(semantic('github', 'Star')['trusted'])
        self.assertFalse(semantic('github', 'Unstar')['trusted'])

    def test_gemini_question_and_chat_changes(self):
        for label, key, editable in [('Send', '', False), ('Enter a prompt here', 'Enter', True)]:
            result = semantic('gemini', label, key=key, editable=editable)
            self.assertEqual(result['kind'], 'gemini_question'); self.assertTrue(result['trusted'])
        for label, effect in [('Delete chat', 'delete'), ('Share chat', 'send')]:
            result = semantic('gemini', label)
            self.assertEqual(result['effect'], effect); self.assertFalse(result['trusted'])

    def test_deezer_removals_and_free_playback_cannot_exempt_a_form(self):
        for label in ['Play', 'Pause', 'Skip', 'Next', 'Previous', 'Seek', 'Volume', 'Queue', 'Like', 'Follow', 'Add to playlist', 'Add to library']:
            self.assertEqual(semantic('deezer', label)['effect'], 'change', label)
            self.assertIsNone(semantic('deezer', label, verb='fill'), label)
        for label in ['Unlike', 'Unfollow', 'Remove from playlist', 'Remove from favorites', 'Remove from favourites', 'Delete playlist']:
            self.assertEqual(semantic('deezer', label)['effect'], 'delete', label)
            self.assertFalse(semantic('deezer', label)['trusted'])
        for label, effect in [('Post comment', 'send'), ('Share track', 'send'), ('Share playlist', 'send'), ('Pay', 'pay'), ('Subscribe', 'pay')]:
            self.assertEqual(semantic('deezer', label)['effect'], effect, label)
        target = {'name': 'Play', 'submit': True}
        result = recognize('https://deezer.test/', reading('deezer'), target, 'click', {}, FIXTURE_HOSTS)
        self.assertIsNone(result)
        self.assertEqual(classify('click', {}, {'target': target, 'form': {'method': 'post'}}, adapter=result), 'form')


class SiteOwnerRules(unittest.TestCase):
    # Reuse only the no-browser engine setup/helpers, without inheriting unrelated tests.
    setUp, tearDown = engine_cases.Operations.setUp, engine_cases.Operations.tearDown
    call, target, prepare = engine_cases.Operations.call, engine_cases.Operations.target, engine_cases.Operations.prepare

    def site(self, site, label='Send'):
        self.chrome.hosts = FIXTURE_HOSTS
        self.browser.facts['url'] = 'https://' + site + '.test/'
        frame = self.browser.facts['frames'][0]; frame['url'] = self.browser.facts['url']
        frame['adapter'] = reading(site); frame['adapter']['target'] = label
        frame['target']['name'] = label

    def allow(self, approval):
        self.assertTrue(self.call('submit', approval)['ok'])
        response = self.call('sites', {'command': 'allow', 'operation_id': approval['operation_id']}, True)
        self.assertTrue(response['ok'], response)
        return response['data']['id']

    def test_gmail_each_exact_owner_parameter_and_revocation(self):
        self.site('gmail'); entry = self.allow(self.prepare())
        original = copy.deepcopy(self.browser.facts['frames'][0]['adapter'])
        for field in ['account', 'to', 'cc', 'bcc']:
            with self.subTest(field=field):
                data = copy.deepcopy(original); data[field] = 'changed@mail.test'
                self.browser.facts['frames'][0]['adapter'] = data
                approval = self.prepare(); count = len(self.browser.dispatched)
                self.assertFalse(self.call('submit_trusted', approval)['ok'])
                self.assertEqual(len(self.browser.dispatched), count)
                self.call('drop', {'operation_id': approval['operation_id']})
        self.browser.facts['frames'][0]['adapter'] = original
        original['to'] = 'two@mail.test,one@mail.test'
        self.assertTrue(self.call('submit_trusted', self.prepare())['ok'])
        current = self.prepare()
        with patch.dict(KINDS['gmail_send'], scope='wider synthetic recipient policy'):
            self.assertFalse(self.call('submit_trusted', current)['ok'])
        self.assertTrue(self.call('sites', {'command': 'revoke', 'id': entry}, True)['ok'])
        self.assertFalse(self.call('submit_trusted', current)['ok'])

    def test_gemini_exact_account_owner_parameter(self):
        self.site('gemini'); self.allow(self.prepare())
        self.browser.facts['frames'][0]['adapter']['account'] = 'Changed synthetic identity'
        self.assertFalse(self.call('submit_trusted', self.prepare())['ok'])

    def test_ineligible_actions_cannot_be_allowed(self):
        for site, label in [('whatsapp', 'Send'), ('github', 'Delete branch'), ('gemini', 'Delete chat'),
                            ('gemini', 'Share chat'), ('deezer', 'Unlike'), ('deezer', 'Pay')]:
            self.site(site, label); approval = self.prepare()
            self.assertFalse(self.call('submit_trusted', approval)['ok'])
            self.assertTrue(self.call('submit', approval)['ok'])
            self.assertFalse(self.call('sites', {'command': 'allow', 'operation_id': approval['operation_id']}, True)['ok'])


if __name__ == '__main__':
    unittest.main()
