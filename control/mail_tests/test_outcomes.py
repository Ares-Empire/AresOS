import json
import ssl
from unittest.mock import patch

from support import MailCase
from smtp_fixture import SMTPFixture
from aresos_control.common import Refused


class Outcomes(MailCase):
    def use_smtp(self, fixture, sent_policy='client'):
        account = {**self.account, 'smtp_host':'localhost', 'smtp_port':fixture.port, 'sent_policy':sent_policy}
        self.engine.store.write({'mail:account:box':account}, 'fixture', 'scripted TLS submission')

    def test_refused_recipient_is_partial_not_done_and_replay_does_not_submit(self):
        with SMTPFixture(self.root) as smtp:
            self.use_smtp(smtp)
            approval = self.approval(to=['one@mail.invalid','refuse@mail.invalid'], bcc=['hidden@mail.invalid'])
            result = self.send(approval)
            self.assertEqual(result['state'], 'partial', result)
            self.assertEqual(result['stages']['recipient:refuse@mail.invalid'], 'refused')
            self.assertEqual(result['stages']['rcpt:refuse@mail.invalid'], 'refused:550')
            self.assertEqual(smtp.arrivals()[0][0], ['one@mail.invalid','hidden@mail.invalid'])
            self.assertEqual(self.send(approval)['state'], 'partial')
            self.assertEqual(len(smtp.arrivals()), 1)
            self.assertIn(result['id'], json.dumps(self.engine.pending('mail')))

    def test_dropped_final_answer_is_unknown_and_never_retried(self):
        with SMTPFixture(self.root, 'lost_answer') as smtp:
            self.use_smtp(smtp)
            approval = self.approval()
            result = self.send(approval)
            self.assertEqual(result['state'], 'unknown', result)
            self.assertEqual(result['stages']['smtp_data'], 'attempting')
            self.assertEqual(len(smtp.arrivals()),1)
            self.assertEqual(self.send(approval)['state'], 'unknown')
            repair = self.call('operation_repair', {'operation_id':result['id'],'stage':'sent_copy'})
            self.assertFalse(repair['ok'])
            self.assertEqual(repair['error']['code'], 'refused')
            self.assertEqual(len(smtp.arrivals()),1)

    def test_failure_at_each_later_stage_repairs_without_smtp(self):
        for which in ('sent_copy','answered_flag'):
            directory = self.root / which
            directory.mkdir()
            with self.subTest(stage=which), SMTPFixture(directory) as smtp:
                self.use_smtp(smtp)
                ref = self.fixture()
                comp = self.data('compose', {'account':'box','mode':'reply','reference':ref,'text':'Reply'})
                approval = self.data('prepare_send', {k:comp[k] for k in ('composition_id','composition_hash')})['approval']
                original = self.mail.local_stage
                def fail(op, stage):
                    if stage == which:
                        raise Refused('stage_missing','Synthetic pre-stage failure')
                    return original(op,stage)
                with patch.object(self.mail,'local_stage',side_effect=fail):
                    result = self.send(approval)
                self.assertEqual(result['state'],'partial',result)
                self.assertEqual(result['stages'][which],'failed')
                with patch.object(self.mail.transport,'smtp',side_effect=AssertionError('Repair must never reach SMTP')):
                    repaired = self.data('operation_repair', {'operation_id':result['id'],'stage':which})
                    self.assertEqual(repaired['operation']['repair_of'],result['id'])
                    self.assertEqual(repaired['original']['state'],'done',repaired)
                    again = self.data('operation_repair', {'operation_id':result['id'],'stage':which})
                    self.assertEqual(again['operation']['state'],'done')
                self.assertEqual(len(smtp.arrivals()),1)
                self.assertEqual(len(self.data('operation_status', {'operation_id':result['id']})['evidence']['sent']),1)

    def test_server_saves_sent_client_never_appends_duplicate(self):
        def save_sent(raw):
            self.mail.append(self.account,self.account['special']['sent'],raw,'(\\Seen)')
        with SMTPFixture(self.root,on_data=save_sent) as smtp:
            self.use_smtp(smtp, 'server')
            result = self.send(self.approval())
            self.assertEqual(result['state'],'done',result)
            self.assertEqual(len(self.data('operation_status', {'operation_id':result['id']})['evidence']['sent']),1)
            self.data('operation_repair', {'operation_id':result['id'],'stage':'sent_copy'})
            self.assertEqual(len(smtp.arrivals()),1)
            self.assertEqual(len(self.data('operation_status', {'operation_id':result['id']})['evidence']['sent']),1)

    def test_positive_sent_preflight_refuses_before_smtp_and_remains_unknown(self):
        approval = self.approval()
        op = self.engine.operation(approval['operation_id'])
        raw = self.mail.mime(op['payload']['composition'], self.mail.message_id(op['id']))
        self.mail.append(self.account,self.account['special']['sent'],raw)
        with patch.object(self.mail.transport,'smtp',side_effect=AssertionError('No SMTP')):
            result = self.call('send',approval)
        self.assertFalse(result['ok'])
        self.assertEqual(self.engine.operation(op['id'])['state'],'unknown')
        self.assertFalse(self.call('operation_cancel',{'operation_id':op['id']})['ok'])

    def test_expiry_cancel_and_before_data_failure_prove_no_submission(self):
        approval = self.approval()
        self.data('operation_cancel', {'operation_id':approval['operation_id']})
        self.assertEqual(self.send(approval)['state'],'failed')
        self.data('notice_ack', {'operation_id':approval['operation_id']})
        approval = self.approval()
        expires = self.engine.operation(approval['operation_id'])['expires']
        with patch('aresos_control.engine.time.time',return_value=expires + 1):
            result = self.send(approval)
        self.assertEqual(result['state'],'failed')
        with SMTPFixture(self.root, 'before_data') as smtp:
            self.use_smtp(smtp)
            result = self.send(self.approval())
            self.assertEqual(result['state'],'failed',result)
            self.assertEqual(smtp.arrivals(),[])

    def test_tls_hostname_or_untrusted_certificate_fails_before_password_sent(self):
        with SMTPFixture(self.root) as smtp:
            self.use_smtp(smtp)
            account = self.mail.account('box')
            for changes in ({'smtp_host':'127.0.0.1'}, {'ca_file':None}):
                with self.subTest(changes=changes):
                    with patch.object(self.mail.transport,'password', side_effect=AssertionError('TLS must finish before password access')):
                        with self.assertRaises(ssl.SSLCertVerificationError):
                            with self.mail.transport.smtp({**account, **changes}):
                                pass
                self.assertEqual(smtp.auth_count,0)
        with patch.object(self.mail.transport,'password',side_effect=AssertionError('No password before IMAP TLS')):
            with self.assertRaises(ssl.SSLCertVerificationError):
                with self.mail.transport.imap({**self.account, 'imap_host':'badmail', 'imap_port':3993}):
                    pass

    def test_required_starttls_success_and_no_plaintext_auth_fallback(self):
        import smtplib
        with SMTPFixture(self.root,starttls=True) as smtp:
            account = {**self.account,'smtp_host':'localhost','smtp_port':smtp.port,'smtp_tls':'starttls'}
            with self.mail.transport.smtp(account) as connection:
                self.assertIsNotNone(connection.sock.cipher())
            self.assertEqual(smtp.auth_count,1)
            with patch.object(self.mail.transport,'password',side_effect=AssertionError('No password before hostname check')):
                with self.assertRaises(ssl.SSLCertVerificationError):
                    with self.mail.transport.smtp({**account,'smtp_host':'127.0.0.1'}):
                        pass
            self.assertEqual(smtp.auth_count,1)
        with SMTPFixture(self.root,starttls=True,advertise_starttls=False) as smtp:
            account = {**self.account,'smtp_host':'localhost','smtp_port':smtp.port,'smtp_tls':'starttls'}
            with patch.object(self.mail.transport,'password',side_effect=AssertionError('No plaintext password fallback')):
                with self.assertRaises(smtplib.SMTPNotSupportedError):
                    with self.mail.transport.smtp(account):
                        pass
            self.assertEqual(smtp.auth_count,0)
