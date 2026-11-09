"""Production-facing test driver; never imported by expectation modules."""
from contextlib import contextmanager, ExitStack
from email.parser import BytesParser
import copy
import time
from unittest.mock import patch

from .records import decode, canonical
from .model import Oracle
from .compare import compare_views
from storage_faults import outside_faults


class Driver:
    def __init__(self, scenario):
        self.scenario = scenario
        self.oracle = Oracle()
        self.record = self.snapshot()
        self.errors = []

    def snapshot(self):
        f = self.scenario.fixture
        with outside_faults():
            self.record = decode(f.root / 'state', f.engine.store.evidence_dir)
        if hasattr(self, 'alias_callback'):
            self.alias_callback(self.record)
        return self.record

    def identities(self, folder):
        f = self.scenario.fixture
        return [dict(account='box', folder=folder, uidvalidity=f.imap.validities[folder], uid=uid,
                     message_id=str(BytesParser().parsebytes(raw, headersonly=True).get('Message-ID', '')))
                for uid, raw in f.imap.boxes.get(folder, {}).items()]

    @contextmanager
    def observe(self, faults=None, delivered=True):
        s, f, oracle = self.scenario, self.scenario.fixture, self.oracle
        oracle.call(s.action, s.args, time.time(), {'mode': faults.mode, 'at': faults.fail_at,
                    'cleanup': faults.cleanup_at} if faults else {})
        # Command logs are memory-only. Reading their context cannot itself hit
        # an injected write or make an owner warning appear in production.
        uid, listing, select = f.imap.uid, f.imap.list, f.imap.select
        def listed(*args, **kwargs):
            answer = listing(*args, **kwargs)
            oracle.server('LIST', 'box', roles=f.imap.roles)
            record = self.snapshot()
            for key, row in record.rows.items():
                if not key.startswith(('mail:filing:', 'mail:rename:')) or row.get('state') not in {'started', 'partial'}:
                    continue
                target = row.get('target')
                if target not in f.imap.roles:
                    continue
                observed = [flag.lstrip('\\').title() for name, flags in f.imap.roles.items()
                            if target == name or target.startswith(name + '/') for flag in flags
                            if flag.lower() in {'\\trash', '\\drafts', '\\sent', '\\junk', '\\archive'}]
                acted = any(e['command'] in {'MOVE', 'COPY', 'RENAME'} and e['accepted'] for e in oracle.servers)
                recovering = row.get('check_open') or s.action in {'control_pending', 'control_log', 'mail_filing_notices'}
                if (acted and observed) or recovering:
                    oracle.server('WARNING', 'box', target, roles=f.imap.roles, source=key,
                        kind='rename' if key.startswith('mail:rename:') else 'filing',
                        evidence={'role': 'Trash' if 'Trash' in observed else 'Drafts' if 'Drafts' in observed else 'ordinary'})
            return answer
        def selected(*args, **kwargs):
            answer = select(*args, **kwargs)
            oracle.server('SELECT', 'box', f.imap.selected, self.identities(f.imap.selected), f.imap.roles)
            return answer
        def command(name, *args, **kwargs):
            folder = f.imap.selected
            before = self.identities(folder) if folder else []
            event = oracle.server(name, 'box', folder, before, f.imap.roles, accepted=False, reply='lost', arguments=list(args))
            answer = uid(name, *args, **kwargs)
            event.update(accepted=answer[0] == 'OK', reply='delivered', roles_after=copy.deepcopy(f.imap.roles))
            if name == 'SEARCH' and len(args) >= 4 and args[2] == 'Message-ID':
                mid = args[3].strip('"')
                identities = [r for r in self.identities(folder) if r['message_id'] == mid]
                record = self.snapshot()
                for key, op in record.rows.items():
                    if key.startswith('op:') and '<' + op['id'].replace(':', '.') + '@mail.aresos.invalid>' == mid:
                        oracle.server('SENT', 'box', folder, identities, f.imap.roles, source=key)
            return answer
        rename = getattr(f.imap, 'rename', None)
        def renamed(*args, **kwargs):
            event = oracle.server('RENAME', 'box', f.imap.selected, roles=f.imap.roles, accepted=False, reply='lost', arguments=list(args))
            answer = rename(*args, **kwargs)
            event.update(accepted=answer[0] == 'OK', reply='delivered', roles_after=copy.deepcopy(f.imap.roles))
            return answer
        append = f.mail.append
        def appended(account, folder, raw, flags=None):
            event = oracle.server('APPEND', account['id'], folder, roles=f.imap.roles,
                raw_sha256=__import__('hashlib').sha256(raw).hexdigest(), accepted=False, reply='lost')
            value = append(account, folder, raw, flags)
            event.update(accepted=True, reply='delivered', identities=self.identities(folder))
            return value
        extra = ExitStack()
        for name in ('create', 'delete'):
            original = getattr(f.imap, name, None)
            if original is None:
                continue
            def folder_command(*args, _name=name, _original=original, **kwargs):
                event = oracle.server(_name.upper(), 'box', roles=f.imap.roles, accepted=False, reply='lost', arguments=list(args))
                answer = _original(*args, **kwargs)
                event.update(accepted=answer[0] == 'OK', reply='delivered', roles_after=copy.deepcopy(f.imap.roles))
                return answer
            extra.enter_context(patch.object(f.imap, name, side_effect=folder_command))
        smtp = f.mail.transport.smtp
        @contextmanager
        def smtp_session(account):
            with smtp(account) as connection:
                class LoggedSMTP:
                    def __getattr__(self, name):
                        method = getattr(connection, name)
                        if name not in {'mail', 'rcpt', 'data'}:
                            return method
                        def send(*args, **kwargs):
                            event = oracle.server(name.upper(), account['id'], accepted=False, reply='lost',
                                recipients=[args[0]] if name == 'rcpt' else [])
                            if name == 'data':
                                from .transcript import Transcript
                                event['identities'] = [Transcript.message(args[0])]
                            answer = method(*args, **kwargs)
                            event.update(accepted=200 <= answer[0] < 300, reply='delivered')
                            return answer
                        return send
                yield LoggedSMTP()
        extra.enter_context(patch.object(f.mail.transport, 'smtp', side_effect=smtp_session))
        receiver = f.engine.receiver
        accept = receiver.accept
        def receive(operation_id, recipient, payload):
            event = oracle.server('RECEIVE', 'fixture', identities=[{'operation_id': operation_id}],
                                  recipients=[recipient], accepted=False, reply='lost')
            with outside_faults():
                result = accept(operation_id, recipient, payload)
            event.update(accepted=result == 'accepted', reply='delivered')
            return result
        extra.enter_context(patch.object(receiver, 'accept', side_effect=receive))
        with extra, patch.object(f.imap, 'rename', side_effect=renamed, create=True), patch.object(f.imap, 'uid', side_effect=command), patch.object(f.imap, 'list', side_effect=listed), \
             patch.object(f.imap, 'select', side_effect=selected), patch.object(f.mail, 'append', side_effect=appended):
            yield
        if faults:
            oracle.script[-1]['faults']['trace'] = list(faults.failures)

    def reply(self, reply, delivered=True):
        self.oracle.reply(reply, delivered)

    def compare(self, check=None):
        f = self.scenario.fixture
        def read(action, args):
            with self.observe_view(action, args):
                reply = f.engine.request({'v': 1, 'method': 'call', 'action': action, 'arguments': args})
            self.reply(reply)
            return reply
        compare_views(read, self.oracle, self.snapshot, check or self.oracle.compare)

    @contextmanager
    def observe_view(self, action, args):
        # Reuse the command recorder without claiming this is the original
        # mutation call. Its correlation and delivered reply are independent.
        s = self.scenario
        old = s.action, s.args
        s.action, s.args = action, args
        try:
            with self.observe():
                yield
        finally:
            s.action, s.args = old
