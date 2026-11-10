"""Questions use service recognition, with exact page attachments and content."""
import copy
import unittest
import test_engine
from test_sites import reading


class Questions(unittest.TestCase):
    setUp = test_engine.Operations.setUp
    tearDown = test_engine.Operations.tearDown
    call = test_engine.Operations.call
    target = test_engine.Operations.target
    prepare = test_engine.Operations.prepare

    def page(self, site):
        self.chrome.hosts = {site: [site + '.test']}
        facts = self.browser.facts
        facts['url'] = facts['frames'][0]['url'] = 'https://' + site + '.test/'
        facts['frames'][0]['adapter'] = copy.deepcopy(reading(site))

    def test_gemini_question_names_the_service_action_and_full_text(self):
        self.page('gemini')
        question = self.prepare()['question']
        self.assertIn('Gemini: ask a question', question)
        self.assertIn('Full synthetic message\\u000aSecond line', question)

    def test_gmail_question_names_count_names_sizes_and_all_mail_roles(self):
        self.page('gmail')
        question = self.prepare()['question']
        for text in ['Gmail: send a mail', 'Synthetic account', 'one@mail.test,two@mail.test',
                     'Cc', 'copy@mail.test', 'hidden Bcc', 'hidden@mail.test', 'Synthetic subject',
                     'characters', '1 attachment', 'fixture.txt', '3 bytes']:
            self.assertIn(text, question)

    def test_gmail_shortcut_names_deletion_and_page_cannot_choose_the_semantics(self):
        self.page('gmail')
        self.browser.facts['frames'][0]['target']['name'] = 'Selected message'
        result = self.call('press', {**self.target(), 'key': '#'})
        self.assertTrue(result['ok'], result)
        self.assertIn('Gmail: delete the selected message', result['data']['approval']['question'])
        self.page('fixture')
        self.browser.facts['frames'][0]['adapter']['kind'] = 'gemini_question'
        self.browser.facts['frames'][0]['target']['name'] = 'Send'
        self.assertNotIn('Gemini: ask a question', self.prepare()['question'])
