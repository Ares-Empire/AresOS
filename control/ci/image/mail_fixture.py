"""Package 18c, B2 check 7, the runner's side: seed mail and read what arrived, against the fixture servers on the
runner's loopback, never through the service.

Dovecot (IMAP, the per-run synthetic password) holds the account's mailbox; GreenMail (SMTP and IMAP, auth disabled)
receives what the service sends. os/ci/control/runner.sh started both and keeps the password and the CA certificate in
$RUNNER_TEMP/aresos-control-fixtures; nothing here prints or returns the password.
"""
from email.message import EmailMessage
from email import policy
from email.parser import BytesParser
from email.utils import make_msgid, formatdate
import hashlib
import imaplib
import os
import pathlib
import ssl

FIXTURES = pathlib.Path(os.environ.get('RUNNER_TEMP', '/tmp')) / 'aresos-control-fixtures'
# The guest's account (control/ci/image/mail_flows.py uses the same values): synthetic names only.
USERNAME = 'ci-owner'
ADDRESS = 'owner@mail.invalid'
SENDER = 'sender@mail.invalid'
SUBJECTS = {'read': 'Seeded for reading', 'attachment': 'Seeded with attachment', 'delete': 'Seeded for deletion'}
ATTACHMENT_NAME = 'seeded-attachment.bin'


def password():
    return (FIXTURES / 'password').read_text()


def context():
    return ssl.create_default_context(cafile=str(FIXTURES / 'certs/tls.crt'))


def attachment_bytes():
    """Fixed, binary, 6 KiB: every byte value occurs, so a lossy transfer shows."""
    return bytes(range(256)) * 24


def message(kind):
    mail = EmailMessage()
    mail['From'] = SENDER
    mail['To'] = ADDRESS
    mail['Subject'] = SUBJECTS[kind]
    mail['Date'] = formatdate(localtime=False)
    mail['Message-ID'] = make_msgid(idstring=f'aresos-ci-{kind}', domain='mail.invalid')
    mail.set_content(f'Synthetic CI message ({kind}).\n')
    if kind == 'attachment':
        mail.add_attachment(attachment_bytes(), maintype='application', subtype='octet-stream',
                            filename=ATTACHMENT_NAME)
    return mail


def dovecot():
    connection = imaplib.IMAP4_SSL('localhost', 993, ssl_context=context())
    connection.login(USERNAME, password())
    return connection


def seed():
    """Three unread messages in the account's INBOX; returns their ids and the attachment's hash."""
    seeded = {}
    connection = dovecot()
    try:
        for kind in SUBJECTS:
            mail = message(kind)
            status, _ = connection.append('INBOX', '', imaplib.Time2Internaldate(None),
                                          mail.as_bytes(policy=policy.SMTP))
            assert status == 'OK', (kind, status)
            seeded[kind] = dict(subject=SUBJECTS[kind], message_id=mail['Message-ID'])
    finally:
        connection.logout()
    data = attachment_bytes()
    seeded['attachment'].update(name=ATTACHMENT_NAME, size=len(data), sha256=hashlib.sha256(data).hexdigest())
    return seeded


def flags(message_id, folder='INBOX'):
    """The message's flags in the account's folder, read by the runner (None when it is not there)."""
    connection = dovecot()
    try:
        status, _ = connection.select(f'"{folder}"', readonly=True)
        assert status == 'OK', (folder, status)
        status, found = connection.uid('SEARCH', None, 'HEADER', 'Message-ID', message_id)
        uids = found[0].split()
        if not uids:
            return None
        status, data = connection.uid('FETCH', uids[0], '(FLAGS)')
        return sorted(flag.decode() for flag in imaplib.ParseFlags(data[0]))
    finally:
        connection.logout()


def arrivals(recipient):
    """Every message GreenMail holds for one recipient: subject, ids and the attachments' hashes."""
    connection = imaplib.IMAP4_SSL('localhost', 3993, ssl_context=context())
    try:
        # GreenMail runs with auth disabled: any password opens the recipient's mailbox.
        connection.login(recipient, 'unused')
        status, _ = connection.select('INBOX', readonly=True)
        assert status == 'OK', status
        status, found = connection.uid('SEARCH', None, 'ALL')
        result = []
        for uid in found[0].split():
            status, data = connection.uid('FETCH', uid, '(RFC822)')
            mail = BytesParser(policy=policy.default).parsebytes(data[0][1])
            attachments = []
            for part in mail.iter_attachments():
                payload = part.get_payload(decode=True) or b''
                attachments.append(dict(name=part.get_filename(), size=len(payload),
                                        sha256=hashlib.sha256(payload).hexdigest()))
            result.append(dict(subject=str(mail['Subject']), message_id=str(mail['Message-ID']),
                               sender=str(mail['From']), to=str(mail['To']), attachments=attachments))
        return result
    finally:
        connection.logout()
