import json
import os
import stat
from unittest.mock import patch

from support import MailCase, CERT
from smtp_fixture import SMTPFixture
from aresos_control.mail.transport import context


class AccountAdmin(MailCase):
    def account_args(self, account_id):
        return {'id':account_id,'addresses':['owner-' + account_id + '@mail.invalid'], 'username':'setup-' + account_id,
                'imap_host':'dovecot','imap_port':993,'smtp_host':'greenmail','smtp_port':3465,'smtp_tls':'implicit'}

    def test_owner_only_admin_setup_tls_special_use_private_password_and_sent_confirmation(self):
        args = self.account_args('onboarded')
        # The ordinary act path cannot request account/password setup, even with a secret field.
        result = self.engine.request({'v':1,'method':'mail_account_add','arguments':args,'password':'pass'})
        self.assertFalse(result['ok'])
        self.assertIsNone(self.engine.store.get('mail:account:onboarded'))
        self.assertFalse(self.call('account_add',args)['ok'])
        original = context
        with patch('aresos_control.mail.transport.context',side_effect=lambda a: original({**a,'ca_file':str(CERT / 'tls.crt')})):
            result = self.engine.request({'v':1,'method':'mail_account_add','arguments':args,'password':'pass'},admin=True)
        self.assertTrue(result['ok'],result)
        account = result['data']['account']
        self.assertEqual(account['special']['sent'],'Posta')
        self.assertEqual(account['special']['trash'],'Cestino')
        self.assertFalse(account['safe_folder_delete'])
        self.assertEqual(account['sent_policy'],'client')
        self.assertFalse(account['ready'])
        self.assertIsNone(self.mail.onboarding_id)
        self.assertFalse(self.call('search',{'account':'onboarded'})['ok'])
        confirmed = self.data('account_settings',{'id':'onboarded','sent_policy':'client','signature':'Owner words','format':'formatted'},admin=True)
        self.assertTrue(confirmed['account']['ready'])
        private = self.engine.store.state_dir / 'mail-passwords'
        for file in private.iterdir():
            self.assertEqual(stat.S_IMODE(file.stat().st_mode),0o600)
            self.assertEqual(file.stat().st_uid,os.geteuid())
        self.assertEqual(stat.S_IMODE(private.stat().st_mode),0o700)
        journal = (self.engine.store.evidence_dir / 'operations.jsonl').read_text()
        self.assertNotIn('"password"',journal)
        for event in self.engine.store.audit():
            self.assertNotIn('"password"',json.dumps(event))
        self.assertFalse(self.engine.request({'v':1,'method':'mail_account_add','arguments':args,'password':'pass'},admin=True)['ok'])

    def test_interrupted_setup_stays_unready_and_cannot_be_enabled_or_repeated(self):
        args = self.account_args('interrupted')
        original = context
        with patch('aresos_control.mail.transport.context',side_effect=lambda a: original({**a,'ca_file':str(CERT / 'tls.crt')})):
            with patch.object(self.mail.transport,'smtp',side_effect=OSError('Synthetic connection failure')):
                result = self.engine.request({'v':1,'method':'mail_account_add','arguments':args,'password':'pass'},admin=True)
        self.assertFalse(result['ok'])
        self.assertFalse(self.mail.account('interrupted',ready=False)['ready'])
        self.assertIsNone(self.mail.onboarding_id)
        self.assertFalse(self.call('account_settings',{'id':'interrupted','sent_policy':'client'},admin=True)['ok'])
        self.assertFalse(self.call('search',{'account':'interrupted'})['ok'])

    def test_missing_private_password_no_other_source_and_no_special_use_guess(self):
        from aresos_control.common import digest
        path = self.mail.transport.password_dir / digest('box')
        path.unlink()
        self.assertEqual(self.call('search',{'account':'box'})['error']['code'],'account_password')
        self.mail.transport.store_password('box','pass')
        path.chmod(0o644)
        self.assertEqual(self.call('search',{'account':'box'})['error']['code'],'account_password')
        args = self.account_args('no-special') | {'imap_host':'greenmail','imap_port':3993}
        with patch('aresos_control.mail.transport.context',side_effect=lambda a: context({**a,'ca_file':str(CERT / 'tls.crt')})):
            result = self.engine.request({'v':1,'method':'mail_account_add','arguments':args,'password':'pass'},admin=True)
        self.assertFalse(result['ok'])
        self.assertEqual(result['error']['code'],'unsupported_server')
        self.assertEqual(self.mail.account('no-special',ready=False)['special'],{'inbox':'INBOX'})

    def test_catalogue_ask_list_and_admin_secrets_absent_from_mcp(self):
        from aresos_control.definitions import ACTIONS,tools_for
        from pathlib import Path
        names = {t['name'] for t in tools_for('mail')}
        self.assertNotIn('account_add',names)
        self.assertNotIn('account_settings',names)
        self.assertNotIn('onboarding_folder_probe',names)
        rules = json.loads((Path(__file__).resolve().parents[1] / 'settings/ask-rules.json').read_text())['permissions']['ask']
        for action in ACTIONS:
            if action.app == 'mail' and action.effect in {'send','delete'} and not action.owner_only:
                self.assertIn('mcp__mail__' + action.verb,rules)
        for tool in tools_for('mail'):
            self.assertNotIn('"password"',json.dumps(tool['inputSchema']))
