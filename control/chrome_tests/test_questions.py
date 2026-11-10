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

    def test_p22_delete_question_names_the_action_key_item_and_bound_title(self):
        facts=self.browser.facts
        facts['title']='Document library'
        facts['frames'][0]['target']['name']='Quarterly report'
        facts['frames'][0]['item']='Quarterly report'
        result=self.call('press', {**self.target(),'key':'Shift+Delete'})
        self.assertTrue(result['ok'], result)
        approval=result['data']['approval']
        for value in ["delete 'Quarterly report'", 'Shift+Delete', 'Document library']:
            self.assertIn(value, approval['question'])
        self.assertEqual(approval['description']['untrusted_content']['page_state']['title'],'Document library')

    def test_p22_many_recipients_and_long_names_are_bounded_without_losing_full_values(self):
        self.page('gmail')
        reading=self.browser.facts['frames'][0]['adapter']
        reading['to']=','.join(f'person{number:02d}@mail.test' for number in range(30))
        reading['bcc']=','.join(f'hidden{number:02d}@mail.test' for number in range(25))
        reading['attachments']=[{'label':'A'*240,'text':'3 bytes'}]
        approval=self.prepare()
        self.assertIn('and 21 more',approval['question'])
        self.assertIn('and 16 more',approval['question'])
        self.assertIn('attachment 1, a 240-character name',approval['question'])
        bound=approval['description']['untrusted_content']['page_state']['adapter']
        self.assertEqual(bound['to'],reading['to']);self.assertEqual(bound['bcc'],reading['bcc'])
        self.assertEqual(bound['attachments'][0]['label'],'A'*240)

    def test_p11_confirmation_binds_a_sibling_draft(self):
        from aresos_control.chrome.adapter import binding
        frame=self.browser.facts['frames'][0]
        frame['target'].update(name='OK',page_dialog={'kind':'dialog','text':'Send this message?'})
        approval=self.prepare();state=approval['description']['untrusted_content']['page_state']
        self.assertIsNotNone(state['editable'])
        before=copy.deepcopy(binding(self.browser.facts,{'frame':0},'confirmation',None))
        frame['editable'][0]['value']='Changed draft'
        self.assertNotEqual(before,binding(self.browser.facts,{'frame':0},'confirmation',None))

    def test_p9_trusted_predicate_independently_forbids_explicit_deletion_payment_and_whatsapp(self):
        from aresos_control.common import digest
        from aresos_control.chrome.sites import KINDS
        self.page('gemini');approval=self.prepare()
        operation=self.engine.operation(approval['operation_id'],'chrome')
        self.engine.store.write({'chrome:allow:'+self.chrome.allow_id(operation):{'kind_hash':digest(KINDS['gemini_question'])}},'chrome_test_setup','Synthetic owner entry')
        self.assertTrue(self.chrome.trusted(operation))
        for title in ['Pay', 'Delete']:
            changed=copy.deepcopy(operation);changed['payload']['binding']['target']['title']=title
            self.assertFalse(self.chrome.trusted(changed))
        for effect in ['pay','delete']:
            changed=copy.deepcopy(operation);changed['payload']['kind']=effect
            self.assertFalse(self.chrome.trusted(changed))
        changed=copy.deepcopy(operation);changed['payload']['adapter']['site']='whatsapp'
        self.assertFalse(self.chrome.trusted(changed))
