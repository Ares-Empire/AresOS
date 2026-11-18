"""Package 18c, B2 check 7, the guest's side: Mail under the real unit, through the installed entry points only.

The flows are those of control/mail_tests (test_admin, test_read, test_compose, test_outcomes, test_changes), here
against the service the image starts, the fixture servers on the runner (reached as greenmail and dovecot) and the
folders the image created. The owner's commands run as `ares`; root stands in for his `sudo` (onboarding, settings).
The account's values match control/ci/image/mail_fixture.py, which seeds and reads on the runner.
"""
import hashlib
import json
import pathlib
import pwd
import shlex
import subprocess
import time

ACCOUNT = 'ci'
USERNAME = 'ci-owner'
ADDRESS = 'owner@mail.invalid'
RECIPIENTS = {'cli': 'first@mail.invalid', 'attachment': 'second@mail.invalid', 'claude': 'third@mail.invalid'}
SUBJECTS = {'cli': 'Sent from the command line', 'attachment': 'Attachment from Downloads',
            'claude': 'Sent through Claude Code'}
SENT, TRASH = 'Posta', 'Cestino'  # control/ci/mail/dovecot.conf's SPECIAL-USE folders
HOME = pathlib.Path(pwd.getpwnam('ares').pw_dir)
DOWNLOADS = HOME / 'Downloads'
ADMIN_ENV = ['HOME=/root', 'LANG=C.UTF-8', 'PATH=/usr/local/bin:/usr/bin:/usr/sbin', 'TERM=xterm-256color']
ADMIN_SOCKET = '/run/aresos-ci-admin.sock'
ONBOARD = pathlib.Path('/run/aresos-ci-onboard')


def account_arguments():
    return {'id': ACCOUNT, 'addresses': [ADDRESS], 'username': USERNAME, 'imap_host': 'dovecot', 'imap_port': 993,
            'smtp_host': 'greenmail', 'smtp_port': 3465, 'smtp_tls': 'implicit'}


def tmux(*args, input=None):
    return subprocess.run(['env', '-i', *ADMIN_ENV, '/usr/bin/tmux', '-S', ADMIN_SOCKET, *args], input=input,
                          capture_output=True, text=True, timeout=30)


def wait_screen(text, seconds, screens):
    deadline, previous = time.monotonic() + seconds, None
    while True:
        screen = tmux('capture-pane', '-p', '-t', 'admin:0.0').stdout
        if screen != previous:
            screens.append(screen)
            previous = screen
        if text in screen:
            return screen
        assert time.monotonic() < deadline, ('deadline waiting for', text, screen)
        time.sleep(0.2)


def onboard(password):
    """`sudo aresos admin mail account add --input JSON` in a terminal, the password typed at its prompt."""
    ONBOARD.mkdir(mode=0o700, exist_ok=True)
    command = ['/usr/bin/sh', '-c', f'/usr/bin/aresos admin mail account add --input "$1" > {ONBOARD}/stdout '
               f'2> {ONBOARD}/stderr; echo "ONBOARD_EXIT=$?"; exec sleep 3600', 'sh', json.dumps(account_arguments())]
    screens = []
    started = tmux('new-session', '-d', '-s', 'admin', '-x', '120', '-y', '40', shlex.join(command))
    assert started.returncode == 0, started
    try:
        wait_screen('Mail password (service only):', 60, screens)
        # Typed, never on a command line: tmux reads it from stdin into a paste buffer, pastes it into the pane
        # (getpass reads it from the terminal) and deletes the buffer.
        for step in (('load-buffer', '-b', 'aresos-ci', '-'), ('paste-buffer', '-d', '-b', 'aresos-ci', '-t', 'admin:0.0'),
                     ('send-keys', '-t', 'admin:0.0', 'Enter')):
            done = tmux(*step, input=password if step[0] == 'load-buffer' else None)
            assert done.returncode == 0, (step[0], done.returncode, done.stderr[-300:])
        final = wait_screen('ONBOARD_EXIT=', 300, screens)
    finally:
        tmux('kill-server')
    stdout, stderr = (ONBOARD / 'stdout').read_text(), (ONBOARD / 'stderr').read_text()
    for path in ONBOARD.iterdir():
        path.unlink()
    ONBOARD.rmdir()
    result = json.loads(stdout)
    assert 'ONBOARD_EXIT=0' in final and result.get('ok'), (final, stdout[-3000:], stderr[-2000:])
    return dict(result=result, stderr=stderr[-2000:], screens=screens)


def wait_until(probe, seconds=90):
    deadline = time.monotonic() + seconds
    while True:
        value = probe()
        if value:
            return value
        assert time.monotonic() < deadline, 'deadline'
        time.sleep(1)


class Flows:
    def __init__(self, cli, write_as_owner):
        self.cli, self.write_as_owner = cli, write_as_owner
        self.record = {}

    def data(self, *words, value=None, user='ares'):
        result = self.cli(user, *words, value=value)
        assert result['returncode'] == 0 and result['json'] and result['json'].get('ok') is True, \
            (words, result['returncode'], result['stdout'][-3000:], result['stderr'][-2000:])
        return result['json']['data']

    def refusal(self, *words, value=None):
        result = self.cli('ares', *words, value=value)
        assert result['returncode'] != 0 and result['json'] and result['json'].get('ok') is False, result
        return result['json']['error']

    def search(self, subject, folders=None):
        value = {'account': ACCOUNT, 'subject': subject}
        if folders:
            value['folders'] = folders
        return self.data('mail', 'search', value=value)['items']

    def state(self, operation_id):
        return self.data('mail', 'operation_status', value={'operation_id': operation_id})['operation']['state']

    def send(self, composition):
        prepared = self.data('mail', 'prepare_send', value={'composition_id': composition['composition_id'],
                                                            'composition_hash': composition['composition_hash']})
        approval = prepared['approval']
        sent = self.data('mail', 'send', value=approval)
        state = wait_until(lambda: (lambda s: s if s in ('done', 'failed', 'unknown', 'partial') else None)(
            self.state(approval['operation_id'])))
        assert state == 'done', (approval['operation_id'], state, sent)
        return dict(operation_id=approval['operation_id'], question=approval['question'], state=state)

    def compose(self, kind, attachments=()):
        value = {'account': ACCOUNT, 'to': [RECIPIENTS[kind]], 'subject': SUBJECTS[kind],
                 'text': 'Synthetic CI mail, written in full.'}
        if attachments:
            value['attachments'] = list(attachments)
        return self.data('mail', 'compose', value=value)

    def run(self, seeded):
        record = self.record
        # The account the owner onboarded is ready; no password or host appears in what the tools see.
        accounts = self.data('mail', 'accounts')
        mine = [account for account in accounts['accounts'] if account.get('id') == ACCOUNT]
        assert len(mine) == 1 and mine[0]['ready'] is True and mine[0]['sent_policy'] == 'client', accounts
        assert 'password' not in json.dumps(accounts).lower(), 'accounts names a password'
        record['account'] = mine[0]
        # Read: found by search, read, marked untrusted, flags unchanged.
        found = self.search(seeded['read']['subject'])
        assert len(found) == 1 and found[0]['reference']['message_id'] == seeded['read']['message_id'], found
        flags_before = found[0]['flags']
        read = self.data('mail', 'read', value={'reference': found[0]['reference']})
        assert 'untrusted_content' in read and 'Synthetic CI message (read)' in read['untrusted_content']['text'], read
        again = self.search(seeded['read']['subject'])
        assert again[0]['flags'] == flags_before and '\\Seen' not in flags_before, (flags_before, again[0]['flags'])
        record['read'] = dict(reference=found[0]['reference'], flags_before=flags_before, flags_after=again[0]['flags'],
                              untrusted_content_keys=sorted(read['untrusted_content']))
        # Send: compose, prepare_send, send; the operation is done and the Sent copy is in the Sent folder.
        record['send'] = self.send(self.compose('cli'))
        sent_copy = wait_until(lambda: self.search(SUBJECTS['cli'], [SENT]))
        assert len(sent_copy) == 1, sent_copy
        record['send']['sent_copy'] = sent_copy[0]['reference']
        # Delete: prepare_delete and delete move the message to Trash.
        victim = self.search(seeded['delete']['subject'])
        assert len(victim) == 1, victim
        content = victim[0]['untrusted_content']
        prepared = self.data('mail', 'prepare_delete', value={'mode': 'trash', 'items': [dict(
            reference=victim[0]['reference'], **{key: content[key] for key in ('from', 'subject', 'date')})]})
        self.data('mail', 'delete', value=prepared['approval'])
        operation_id = prepared['approval']['operation_id']
        assert wait_until(lambda: self.state(operation_id) in ('done', 'failed', 'unknown') and
                          self.state(operation_id)) == 'done'
        in_trash = wait_until(lambda: self.search(seeded['delete']['subject'], [TRASH]))
        assert len(in_trash) == 1 and not self.search(seeded['delete']['subject'], ['INBOX']), in_trash
        record['delete'] = dict(operation_id=operation_id, trash=in_trash[0]['reference'])
        # Files: the folders exist because the image made them; an attachment from Downloads goes out, a received
        # one is saved there, a file outside the configured folders is refused.
        info = DOWNLOADS.stat()
        assert DOWNLOADS.is_dir() and (info.st_uid, oct(info.st_mode & 0o777)) == (pwd.getpwnam('ares').pw_uid,
                                                                                   '0o700'), info
        record['downloads_before_test'] = dict(mode=oct(info.st_mode & 0o777), uid=info.st_uid,
                                               entries=sorted(path.name for path in DOWNLOADS.iterdir()))
        outgoing = DOWNLOADS / 'outgoing-ci.bin'
        payload = hashlib.sha256(b'aresos-ci-outgoing').digest() * 200
        self.write_as_owner(outgoing, payload)
        record['attachment_out'] = dict(path=str(outgoing), size=len(payload),
                                        sha256=hashlib.sha256(payload).hexdigest(),
                                        **self.send(self.compose('attachment', [{'path': str(outgoing)}])))
        outside = HOME / 'outside-ci.bin'
        self.write_as_owner(outside, payload)
        record['outside_refused'] = self.refusal('mail', 'compose', value={
            'account': ACCOUNT, 'to': [RECIPIENTS['attachment']], 'subject': 'Refused attachment',
            'text': 'Not sent.', 'attachments': [{'path': str(outside)}]})
        outside.unlink()
        carrier = self.search(seeded['attachment']['subject'])
        assert len(carrier) == 1, carrier
        shown = self.data('mail', 'read', value={'reference': carrier[0]['reference']})['untrusted_content']
        attached = [item for item in shown['attachments'] if item['name'] == seeded['attachment']['name']]
        assert len(attached) == 1 and attached[0]['sha256'] == seeded['attachment']['sha256'], shown['attachments']
        saved = self.data('mail', 'attachment_save', value={'reference': carrier[0]['reference'],
                                                             'part': attached[0]['part']})
        paths = [value for value in strings(saved) if value.startswith(str(DOWNLOADS) + '/')]
        assert paths, saved
        target = pathlib.Path(paths[0])
        info = target.stat()
        assert info.st_uid == pwd.getpwnam('ares').pw_uid and \
            hashlib.sha256(target.read_bytes()).hexdigest() == seeded['attachment']['sha256'], (saved, info)
        record['attachment_in'] = dict(saved=saved, path=str(target), uid=info.st_uid, mode=oct(info.st_mode & 0o777),
                                       sha256=seeded['attachment']['sha256'])
        return record


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)
