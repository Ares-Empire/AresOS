"""Production-facing test driver; never imported by expectation modules."""
from contextlib import contextmanager, ExitStack
from email.parser import BytesParser
import copy
import time
from unittest.mock import patch

from .records import decode, canonical
from .model import Fact, Oracle
from .compare import compare_views, pages
from storage_faults import outside_faults


class Driver:
    def __init__(self, scenario):
        self.scenario = scenario
        self.oracle = getattr(scenario, 'owner_oracle', None) or Oracle()
        self.record = self.snapshot()
        self.errors = []

    def snapshot(self):
        f = self.scenario.fixture
        with outside_faults():
            paths = [f.root / 'state/control.sqlite', f.root / 'state/control.sqlite-journal', f.engine.store.evidence_dir / 'operations.jsonl']
            key = tuple((p.stat().st_size, p.stat().st_mtime_ns) if p.exists() else None for p in paths)
            if key != getattr(self, '_snapshot_key', None):
                self.record = decode(f.root / 'state', f.engine.store.evidence_dir)
                self._snapshot_key = key
        if hasattr(self, 'alias_callback'):
            self.alias_callback(self.record)
        return self.record

    def identities(self, folder):
        f = self.scenario.fixture
        return [dict(account=getattr(self, 'account_id', 'box'), folder=folder, uidvalidity=f.imap.validities[folder], uid=uid,
                     message_id=str(BytesParser().parsebytes(raw, headersonly=True).get('Message-ID', '')),
                     sha256=__import__('hashlib').sha256(raw).hexdigest())
                for uid, raw in f.imap.boxes.get(folder, {}).items()]

    @contextmanager
    def observe(self, faults=None, delivered=True):
        s, f, oracle = self.scenario, self.scenario.fixture, self.oracle
        if not hasattr(s, 'owner_oracle') or getattr(s, 'flow', '') in {'expiry', 'maintenance'} or getattr(s, 'flow', '').startswith('restart_'):
            oracle.call(s.action, s.args, time.time(), {'mode': faults.mode, 'at': faults.fail_at,
                        'cleanup': faults.cleanup_at} if faults else {})
        # Command logs are memory-only. Reading their context cannot itself hit
        # an injected write or make an owner warning appear in production.
        uid, listing, select = f.imap.uid, f.imap.list, f.imap.select
        def listed(*args, **kwargs):
            answer = listing(*args, **kwargs)
            oracle.server('LIST', getattr(self, 'account_id', 'box'), roles=f.imap.roles, mailboxes={name: self.identities(name) for name in f.imap.boxes})
            return answer
        def selected(*args, **kwargs):
            answer = select(*args, **kwargs)
            oracle.server('SELECT', getattr(self, 'account_id', 'box'), f.imap.selected, self.identities(f.imap.selected), f.imap.roles)
            return answer
        def command(name, *args, **kwargs):
            folder = f.imap.selected
            before = self.identities(folder) if folder else []
            event = oracle.server(name, getattr(self, 'account_id', 'box'), folder, before, f.imap.roles, accepted=False, reply='lost', arguments=list(args), committed_before=copy.deepcopy(self.snapshot().rows))
            answer = uid(name, *args, **kwargs)
            event.update(accepted=answer[0] == 'OK', reply='delivered', roles_after=copy.deepcopy(f.imap.roles))
            if name == 'SEARCH' and len(args) >= 4 and args[2] == 'Message-ID':
                mid = args[3].strip('"')
                identities = [{k: v for k, v in r.items() if k != 'sha256'} for r in self.identities(folder) if r['message_id'] == mid]
                record = self.snapshot()
                operation_ids = {row['id'] for key, row in record.rows.items() if key.startswith('op:')}
                operation_ids.update(call['arguments']['operation_id'] for call in oracle.script
                    if isinstance(call.get('arguments'), dict) and isinstance(call['arguments'].get('operation_id'), str))
                for operation_id in operation_ids:
                    if '<' + operation_id.replace(':', '.') + '@mail.aresos.invalid>' == mid:
                        oracle.server('SENT', getattr(self, 'account_id', 'box'), folder, identities, f.imap.roles, source='op:' + operation_id)
            return answer
        response = f.imap.response
        def responded(name):
            answer = response(name)
            if name == 'COPYUID':
                import re
                raw = b' '.join(value for value in answer[1] or [] if value)
                match = re.fullmatch(rb'([1-9]\d*) ([1-9]\d*) ([1-9]\d*)', raw)
                for event in reversed(oracle.servers):
                    if event['command'] in {'MOVE', 'COPY'} and event['call'] == oracle.call_id and 'copyuid_delivered' not in event:
                        event['copyuid_delivered'] = bool(match)
                        if match:
                            ref = next((ref for ref in event['identities'] if ref['uid'] == int(match[2])), {})
                            event['destination'] = {k: v for k, v in ref.items() if k != 'sha256'}
                            event['destination'].update(folder=event['arguments'][1].strip('"'), uidvalidity=int(match[1]), uid=int(match[3]))
                        break
            return answer
        rename = getattr(f.imap, 'rename', None)
        def renamed(*args, **kwargs):
            event = oracle.server('RENAME', getattr(self, 'account_id', 'box'), f.imap.selected, roles=f.imap.roles, accepted=False, reply='lost', arguments=list(args), committed_before=copy.deepcopy(self.snapshot().rows))
            answer = rename(*args, **kwargs)
            event.update(accepted=answer[0] == 'OK', reply='delivered', roles_after=copy.deepcopy(f.imap.roles))
            return answer
        append = f.mail.append
        def appended(account, folder, raw, flags=None):
            event = oracle.server('APPEND', account['id'], folder, roles=f.imap.roles,
                raw_sha256=__import__('hashlib').sha256(raw).hexdigest(), accepted=False, reply='lost',
                committed_before=copy.deepcopy(self.snapshot().rows))
            value = append(account, folder, raw, flags)
            event.update(accepted=True, reply='delivered', identities=self.identities(folder))
            return value
        extra = ExitStack()
        imap = f.mail.transport.imap
        @contextmanager
        def imap_session(account):
            previous = getattr(self, 'account_id', 'box')
            self.account_id = account['id']
            try:
                with imap(account) as client:
                    yield client
            finally:
                self.account_id = previous
        extra.enter_context(patch.object(f.mail.transport, 'imap', side_effect=imap_session))
        for name in ('create', 'delete'):
            original = getattr(f.imap, name, None)
            if original is None:
                continue
            def folder_command(*args, _name=name, _original=original, **kwargs):
                event = oracle.server(_name.upper(), getattr(self, 'account_id', 'box'), roles=f.imap.roles, accepted=False, reply='lost', arguments=list(args), committed_before=copy.deepcopy(self.snapshot().rows))
                answer = _original(*args, **kwargs)
                event.update(accepted=answer[0] == 'OK', reply='delivered', roles_after=copy.deepcopy(f.imap.roles))
                return answer
            extra.enter_context(patch.object(f.imap, name, side_effect=folder_command))
        committed_snapshot = self.snapshot
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
                                recipients=[args[0]] if name == 'rcpt' else [], committed_before=copy.deepcopy(committed_snapshot().rows))
                            if name == 'data':
                                from .transcript import Transcript
                                event['identities'] = [Transcript.message(args[0])]
                            answer = method(*args, **kwargs)
                            event.update(accepted=200 <= answer[0] < 300, reply='delivered')
                            return answer
                        return send
                yield LoggedSMTP()
        extra.enter_context(patch.object(f.mail.transport, 'smtp', side_effect=smtp_session))
        from aresos_control.mail import adapter
        https = adapter.http.client.HTTPSConnection
        class LoggedHTTPS:
            def __init__(connection, *args, **kwargs):
                connection.inner, connection.event = https(*args, **kwargs), None
            def request(connection, method, *args, **kwargs):
                connection.event = oracle.server(method, 'box', accepted=False, reply='lost',
                    arguments=list(args), committed_before=copy.deepcopy(self.snapshot().rows))
                value = connection.inner.request(method, *args, **kwargs)
                connection.event['accepted'] = True
                return value
            def getresponse(connection):
                response = connection.inner.getresponse()
                connection.event.update(reply='delivered', status=response.status)
                return response
            def close(connection):
                return connection.inner.close()
        extra.enter_context(patch.object(adapter.http.client, 'HTTPSConnection', LoggedHTTPS))
        receiver = f.engine.receiver
        accept = receiver.accept
        def receive(operation_id, recipient, payload):
            event = oracle.server('RECEIVE', 'fixture', identities=[{'operation_id': operation_id}],
                                  recipients=[recipient], accepted=False, reply='lost', committed_before=copy.deepcopy(self.snapshot().rows))
            with outside_faults():
                result = accept(operation_id, recipient, payload)
            event.update(accepted=result == 'accepted', reply='delivered')
            return result
        extra.enter_context(patch.object(receiver, 'accept', side_effect=receive))
        with extra, patch.object(f.imap, 'response', side_effect=responded), patch.object(f.imap, 'rename', side_effect=renamed, create=True), patch.object(f.imap, 'uid', side_effect=command), patch.object(f.imap, 'list', side_effect=listed), \
             patch.object(f.imap, 'select', side_effect=selected), patch.object(f.mail, 'append', side_effect=appended):
            yield
        if faults:
            oracle.script[-1]['faults']['trace'] = list(faults.failures)

    def reply(self, reply, delivered=True):
        if not hasattr(self, 'call_reply'):
            self.call_reply = copy.deepcopy(reply)
        self.oracle.reply(reply, delivered)

    def compare(self, check=None):
        f = self.scenario.fixture
        def read(action, args):
            with self.observe_view(action, args):
                reply = f.engine.request({'v': 1, 'method': 'call', 'action': action, 'arguments': args})
            self.reply(reply)
            return reply
        checker = check or self.oracle.compare
        record = self.snapshot()
        if 'export' in getattr(self.scenario, 'flow', ''):
            destination = __import__('pathlib').Path(self.scenario.args['folder']) / self.scenario.args['name']
            with outside_faults():
                raw = destination.read_bytes() if destination.exists() else b''
            assert raw in {b'', b'Synthetic exported bytes'}, ('Caller export corrupted', raw)
            if raw:
                wanted = {Fact('caller', 'published', detail=__import__('hashlib').sha256(raw).hexdigest())}
                reply = getattr(self, 'call_reply', {})
                data = reply.get('data', {})
                saved = data.get('saved', data)
                reported = {Fact('caller', 'published', detail=saved['sha256'])} if 'sha256' in saved else set()
                checker('export-publication', wanted, reported)
        checker('restore-generation', {Fact('generation', 'value', detail=str(record.generation))},
            {Fact('generation', 'value', detail=str(f.engine.store.generation))})
        checker('recovery-holds', self.oracle.holds(record), {Fact(key, 'held') for key in f.engine.store.ledger.holds if key != 'replay'})
        checker('R2.context-before-command', set(), self.oracle.context_errors())
        checker('completion', set(), self.oracle.completion_errors(self.snapshot()))
        compare_views(read, self.oracle, self.snapshot, checker, ordinary='testapp_list' if getattr(self.scenario, 'flow', '').startswith('testapp_') else 'mail_accounts')
        for occurrence, (source, expected) in self.oracle.location_evidence.items():
            actual, fragments, available = [], {}, True
            for page in pages(read, 'mail_filing_locations', {'filing_id': occurrence}):
                if page.get('unavailable'):
                    available = False
                    break
                content = page.get('untrusted_content', {})
                actual.extend(content.get('locations', []))
                for fragment in content.get('fragments', []):
                    value = fragments.setdefault(fragment['message_index'], '')
                    assert len(value) == fragment['offset'], ('Location fragment gap', occurrence, fragment)
                    value += fragment['json']
                    fragments[fragment['message_index']] = value
                    if len(value) == fragment['total_characters']:
                        actual.append(__import__('json').loads(value))
            checker('locations', {Fact(source, 'locations', occurrence, canonical(expected))},
                {Fact(source, 'locations', occurrence, canonical(sorted(actual, key=canonical)))} if available else set())
        if hasattr(checker, 'finish'):
            checker.finish()

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
