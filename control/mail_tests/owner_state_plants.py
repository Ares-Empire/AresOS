"""Real production regressions, scoped to one unmodified Driver run.

Adapted from the independent review's P1-P7 probes. No expectation helper is
patched while production is recorded or compared.
"""
from contextlib import contextmanager, ExitStack
import copy
from unittest.mock import patch
from aresos_control.mail import adapter as A, filing as F
from aresos_control.storage import Store
from owner_state_oracle.driver import Driver
from owner_state_oracle.gaps import Gaps
from owner_state_oracle.perturb import freeze
from test_owner_state_sweep import OwnerScenario
import test_review_fixes_23 as r23
Mail = A.Mail

_execute, _local_stage, _send_smtp = Mail.execute, Mail.local_stage, Mail.send_smtp


def p1_execute(self, operation, stage):
    def filtered(name, outcome, **kw):
        if name == 'sent_copy':
            return None
        return stage(name, outcome, **kw)
    return _execute(self, operation, filtered)


def p1_local(self, operation, which):
    if which == 'sent_copy':
        return 'done'   # regression: no Sent APPEND, no Sent check
    return _local_stage(self, operation, which)


P1 = [patch.object(Mail, 'execute', p1_execute), patch.object(Mail, 'local_stage', p1_local)]


# P2: reply send marks the replied-to original \Deleted instead of \Answered (coherent context).
_compose = r23.Results23.compose
def reply_compose(self, **args):
    reference = {'account': 'box', 'folder': 'Source', 'uidvalidity': self.imap.validities['Source'], 'uid': 1, 'message_id': self.imap.mid}
    result = self.data('compose', {'account': 'box', 'mode': 'reply', 'reference': reference, 'text': 'one\ntwo\n', **args})
    return {k: result[k] for k in ('composition_id', 'composition_hash')}
REPLY = [patch.object(r23.Results23, 'compose', reply_compose)]
_answered_context = Mail.answered_context


def p2_context(self, operation):
    value = _answered_context(self, operation)
    if value is not None:
        value = {**value, 'flags': ['+FLAGS.SILENT', '(\\Deleted)']}
    return value


def p2_local(self, operation, which):
    if which != 'answered_flag':
        return _local_stage(self, operation, which)
    comp = operation['payload']['composition']
    account = self.account(comp['mail']['account'], ready=False)
    reference = comp['mail']['answered_reference']
    if reference is None:
        return 'not_needed'
    with self.transport.imap(account) as client:
        self.fresh_roles(account, client, names=[reference['folder']])
        self.message(reference, writable=True, client=client)
        value = self.answered_context(operation)
        with A.mutation(self.store, value):
            A.ok(client.uid('STORE', str(reference['uid']), '+FLAGS.SILENT', '(\\Deleted)'), 'Answered flag')
        self.store.checkpoint('mail_answered_flag')
    return 'done'


P2 = [patch.object(Mail, 'answered_context', p2_context), patch.object(Mail, 'local_stage', p2_local)]


# P3: a fully accepted, clean send is reported partial with a false refusal reason.
def p3_smtp(self, operation, comp, raw, stage):
    state, reason = _send_smtp(self, operation, comp, raw, stage)
    if state == 'done':
        return 'partial', 'Some recipients refused; accepted recipients must never be sent again.'
    return state, reason
P3 = [patch.object(Mail, 'send_smtp', p3_smtp)]


# P4: permanent delete skips the \Deleted STORE but still EXPUNGEs and reports done.
@contextmanager
def p4_imap_wrapper():
    original = None
    def install(transport):
        nonlocal original
        original = transport.imap
    yield install


class NoStore:
    def __init__(self, inner):
        self.inner = inner
    def uid(self, command, *args):
        if command == 'STORE' and '(\\Deleted)' in args:
            return 'OK', [b'skipped by planted regression']
        return self.inner.uid(command, *args)
    def __getattr__(self, name):
        return getattr(self.inner, name)


_delete_execute = Mail.execute
def p4_execute(self, operation, stage):
    if operation['action'] != 'mail_delete' or operation['payload'].get('mode') != 'permanent':
        return _delete_execute(self, operation, stage)
    transport_imap = self.transport.imap
    @contextmanager
    def wrapped(account):
        with transport_imap(account) as client:
            yield NoStore(client)
    with patch.object(self.transport, 'imap', side_effect=wrapped):
        return _delete_execute(self, operation, stage)
P4 = [patch.object(Mail, 'execute', p4_execute)]


# P5: rename records and discloses a wrong message count (2 instead of 7), coherently.
class WrongLen(list):
    def __len__(self):
        return 2
_rename = F.rename_folder
def p5_rename(mail, account, client, source, target, roles_before):
    return _rename(mail, account, client, {**source, 'uids': WrongLen(source['uids'])}, target, roles_before)
P5 = [patch.object(F, 'rename_folder', p5_rename)]


# P6: the Sent copy is APPENDed to INBOX instead of the Sent role (context and command agree).
_append_context, _append_with_context = Mail.append_context, Mail.append_with_context
def p6_context(self, account, folder, raw, flags=None, recipients=()):
    return _append_context(self, account, 'INBOX' if flags == '(\\Seen)' else folder, raw, flags, recipients)
def p6_append(self, account, folder, raw, flags=None, recipients=()):
    return _append_with_context(self, account, 'INBOX' if flags == '(\\Seen)' else folder, raw, flags, recipients)
P6 = [patch.object(Mail, 'append_context', p6_context), patch.object(Mail, 'append_with_context', p6_append)]

# P7: a saved draft is APPENDed to Sent instead of the Drafts role (context and command agree).
def p7_context(self, account, folder, raw, flags=None, recipients=()):
    return _append_context(self, account, 'Sent' if flags == '(\\Draft)' else folder, raw, flags, recipients)
def p7_append(self, account, folder, raw, flags=None, recipients=()):
    return _append_with_context(self, account, 'Sent' if flags == '(\\Draft)' else folder, raw, flags, recipients)
P7 = [patch.object(Mail, 'append_context', p7_context), patch.object(Mail, 'append_with_context', p7_append)]



def record(flow, patches=(), compare=True):
    with ExitStack() as stack:
        for factory in patches:
            stack.enter_context(factory())
        scenario = OwnerScenario(flow)
        try:
            driver = Driver(scenario)
            with driver.observe():
                reply = scenario.call()
            driver.reply(reply)
            oracle, decoded = freeze(driver.oracle), copy.deepcopy(driver.snapshot())
            registry = Gaps(recording=True)
            if compare:
                checker = registry.checker('plant')
                driver.compare(checker)
                checker.finish()
            return oracle, decoded, registry.entries
        finally:
            scenario.close()


def copies(patches):
    # mock.patch objects are reusable context managers; fresh factories keep
    # overlapping baseline/plant/control runs independent.
    return tuple(lambda p=p: p for p in patches)


PLANTS = {
    'missing-sent-copy': ('send', copies(P1)),
    'wrong-answered-flags': ('send', copies(REPLY + P2)),
    'false-recipient-refusal': ('send', copies(P3)),
    'missing-deleted-store': ('delete_permanent', copies(P4)),
    'false-rename-count': ('filing_rename', copies(P5)),
    'wrong-sent-destination': ('send', copies(P6)),
    'wrong-draft-destination': ('draft_append', copies(P7)),
}


def write_lie(change):
    original = Store.write
    def persist(store, changes, action, *args, **kwargs):
        change(changes, action, kwargs)
        return original(store, changes, action, *args, **kwargs)
    return lambda: patch.object(Store, 'write', persist)


def narrow_payload(changes, action, kwargs):
    for key, row in changes.items():
        if key.startswith('op:') and row and row.get('state') == 'submitting' and row.get('action') == 'mail_delete':
            row['payload']['items'] = row['payload']['items'][:1]


def false_transition(changes, action, kwargs):
    for key, row in changes.items():
        if key.startswith('op:') and row and row.get('state') == 'done' and row.get('action') == 'mail_send':
            row.update(state='reserved', reason='Awaiting exact approval; nothing submitted.')


def false_local_flag(changes, action, kwargs):
    if action == 'testapp_flag' and 'testapp' in changes:
        for item in changes['testapp']['items'].values():
            item['flagged'] = False


PLANTS.update({
    'narrow-payload': ('delete_permanent', (write_lie(narrow_payload),)),
    'false-transition': ('send', (write_lie(false_transition),)),
    'false-local-flag': ('local_flag', (write_lie(false_local_flag),)),
})
