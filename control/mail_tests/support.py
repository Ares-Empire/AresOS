from email.message import EmailMessage
import os
from pathlib import Path
import tempfile
import unittest
import uuid

from aresos_control.engine import Engine
from aresos_control.common import canonical
from aresos_control.definitions import BY_NAME
from response_checks import check_responses
from owner_state_oracle.transcript import TRACE
from aresos_control.mail import codec
from aresos_control.mail.transport import folders, select, uids, fetch, ok, quote

check_responses()

WORK = Path(__file__).resolve().parents[2] / '.work' / 'mail-tests'
WORK.mkdir(parents=True, exist_ok=True)
CERT = Path(os.environ.get('MAIL_CERT_DIR', str(WORK / 'certs')))


class MailCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.root = Path(self.temp.name)
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        self.mail = self.engine.adapters['mail']
        self.account = self.add_account('box')
        self.owner = self.account['addresses'][0]
        self.peer = 'Alice <alice@mail.invalid>'

    def tearDown(self):
        self.engine.close()
        self.temp.cleanup()

    def add_account(self, account_id, server='dovecot'):
        username = 'fixture-' + uuid.uuid4().hex
        account = {'id': account_id, 'addresses': [username + '@mail.invalid', 'alias-' + username + '@mail.invalid'],
                   'username': username, 'imap_host': server, 'imap_port': 993 if server == 'dovecot' else 3993,
                   'smtp_host': 'greenmail', 'smtp_port': 3465, 'smtp_tls': 'implicit', 'ca_file': str(CERT / 'tls.crt'),
                   'format': 'plain', 'signature': '', 'ready': True, 'special': {'inbox': 'INBOX'},
                   'capabilities': [], 'smtp_capabilities': [], 'sent_policy': 'client', 'safe_folder_delete': False, 'delimiter': '/'}
        self.mail.transport.store_password(account_id, 'pass')
        with self.mail.transport.imap(account) as conn:
            account['capabilities'] = sorted(conn.capabilities)
            from aresos_control.mail.roles import resolve, optional_roles
            listed = folders(conn)
            if server == 'dovecot':
                account.update(resolve(listed))
            else:
                # Bare GreenMail intentionally lacks required SPECIAL-USE roles;
                # guard/onboarding tests must still be able to seed its raw store.
                inbox = next(f for f in listed if f['name'] == 'INBOX')
                account.update(roots={'inbox': {'folder': 'INBOX', 'delimiter': inbox['delimiter']}},
                               delimiter=inbox['delimiter'], optional=optional_roles(listed))
        with self.mail.transport.smtp(account) as smtp:
            account['smtp_capabilities'] = sorted(smtp.esmtp_features)
        self.engine.store.write({'mail:account:' + account_id: account}, 'fixture_account', 'synthetic account')
        return account

    def call(self, name, args=None, admin=False):
        TRACE.begin('mail_' + name, args or {})
        result = self.engine.request({'v':1, 'method':'call', 'action':'mail_' + name, 'arguments': args or {}}, admin)
        TRACE.script[-1].update(reply='delivered', result=result)
        return result

    def data(self, name, args=None, admin=False):
        result = self.call(name, args, admin)
        self.assertTrue(result['ok'], result)
        from jsonschema import Draft202012Validator
        Draft202012Validator(BY_NAME['mail_' + name].tool()['outputSchema']).validate(result)
        return result['data']

    def fixture(self, folder='INBOX', *, msg=None, sender=None, to=None, subject='Fixture café', text='Unread fixture body', mid=None, headers=None, attachments=None, flags=None):
        if msg is None:
            msg = EmailMessage()
            msg['From'] = sender or self.peer
            msg['To'] = to or self.owner
            msg['Subject'] = subject
            msg['Date'] = 'Sat, 07 Nov 2026 10:00:00 +0000'
            if mid != 'missing':
                msg['Message-ID'] = mid or '<' + uuid.uuid4().hex + '@mail.invalid>'
            for h, value in (headers or {}).items():
                msg[h] = value
            msg.set_content(text)
            for name, content, kind in attachments or []:
                major, minor = kind.split('/')
                msg.add_attachment(content, maintype=major, subtype=minor, filename=name)
        return self.mail.append(self.account, folder, msg.as_bytes(policy=codec.SMTP_POLICY), flags)

    def compose(self, **args):
        return self.data('compose', {'account': self.account['id'], 'to': ['one@mail.invalid'], 'text':'Full authored text', **args})

    def approval(self, **args):
        comp = self.compose(**args)
        return self.data('prepare_send', {k: comp[k] for k in ('composition_id', 'composition_hash')})['approval']

    def send(self, approval):
        return self.data('send', approval)['operation']

    def delete_approval(self, refs, mode='trash'):
        items = [self.mail.named_item(ref) for ref in refs]
        return self.data('prepare_delete', {'items': items, 'mode': mode})['approval']

    def all_flags(self):
        messages, _ = self.mail.snapshot(self.account['id'], list(self.account['special'].values()))
        return {canonical(m['reference']): m['flags'] for m in messages}

    def arrivals(self, recipient, mid):
        account = {**self.account, 'imap_host':'greenmail', 'imap_port':3993, 'username':recipient}
        with self.mail.transport.imap(account) as conn:
            select(conn, 'INBOX')
            result = []
            for uid in uids(conn):
                raw, _ = fetch(conn, uid, self.mail.blobs.limit)
                if str(codec.parse(raw).get('Message-ID')) == mid:
                    result.append(raw)
            return result
