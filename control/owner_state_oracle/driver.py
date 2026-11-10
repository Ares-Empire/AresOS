"""Production-facing test driver; never imported by expectation modules."""
from contextlib import contextmanager, ExitStack
from email.parser import BytesParser
import copy
import time
import sqlite3
from unittest.mock import patch

from .records import decode, canonical
from .model import Fact, Oracle
from .context import MUTATIONS
from .compare import compare_views, pages, compare_envelope, compare_status, compare_proofs
from .responses import read_response
from .transcript import folder_name


@contextmanager
def outside_faults():
    # Base-container response-capture self-tests need no SQLite VFS injector.
    from storage_faults import outside_faults as scope
    with scope():
        yield


class Driver:
    def __init__(self, scenario):
        self.scenario = scenario
        self.oracle = getattr(scenario, 'owner_oracle', None) or Oracle()
        self.record = self.snapshot()
        if not hasattr(self.oracle, 'seed_sequence'):
            # Fixture setup precedes the faulted script. Its explicitly seeded
            # history is input; subsequent transitions need recorded evidence.
            self.oracle.seed_sequence = max(self.record.committed, default=0)
            self.oracle.seed_events = copy.deepcopy(self.record.events)
        self.context_start_sequence = max(self.record.committed, default=0)
        self.startup_sequence = max((fence['seq'] for fence in self.record.fences), default=0)
        self.record.startup_sequence = self.startup_sequence
        self.record.locked |= any(seq <= self.startup_sequence for seq in self.record.unprepared_fences)
        # Establish starting obligations before the first action can restore or
        # remove their rows. Reading the first reply is already too late.
        self.oracle.expected(self.record)
        self.errors = []
        self.envelopes = []
        self.envelopes_seen = set()
        self.oracle.response_observer = self.capture_response

    def snapshot(self):
        from storage_faults import ACTIVE
        f = self.scenario.fixture
        with outside_faults():
            paths = [f.root / 'state/control.sqlite', f.root / 'state/control.sqlite-journal', f.engine.store.evidence_dir / 'operations.jsonl']
            key = tuple((p.stat().st_size, p.stat().st_mtime_ns) if p.exists() else None for p in paths)
            if key != getattr(self, '_snapshot_key', None):
                self.record = decode(f.root / 'state', f.engine.store.evidence_dir)
                self._snapshot_key = key
            self.record.locked |= any(seq <= getattr(self, 'startup_sequence', 0) for seq in self.record.unprepared_fences)
            self.record.startup_sequence = getattr(self, 'startup_sequence', 0)
            active = getattr(self.oracle, 'active_call', None)
            if ACTIVE is not None and active is not None:
                point = len(ACTIVE.points)
                for event in self.record.events:
                    marker = active, event['seq']
                    self.oracle.commit_fault_points[marker] = min(point, self.oracle.commit_fault_points.get(marker, point))
        if hasattr(self, 'alias_callback'):
            self.alias_callback(self.record)
        return self.record

    def fixture_input(self, changes, summary):
        """Record a test's explicit legacy/interrupted input before writing it."""
        self.oracle.call('fixture_input', {'changes': changes}, time.time())
        index = len(self.oracle.script) - 1
        self.oracle.script[index]['start_seq'] = max(self.snapshot().committed, default=0)
        result = self.scenario.fixture.engine.store.write(changes, 'fixture', summary)
        self.oracle.script[index].update(end_seq=max(self.snapshot().committed, default=0), reply='delivered')
        return result

    def precommit(self):
        from storage_faults import ACTIVE
        record = self.snapshot()
        created = {}
        for event in record.events:
            for key, value in event['set'].items():
                if value is not None:
                    created.setdefault(key, event['seq'])
        return dict(committed_before=copy.deepcopy(record.rows), created_before=created,
                    call_start_seq=getattr(self.oracle, 'active_start_seq', 0), before_seq=max(record.committed, default=0),
                    fault_point=len(ACTIVE.points) if ACTIVE else 0)

    def identities(self, folder, account_id=None):
        f = self.scenario.fixture
        return [dict(account=account_id or getattr(self, 'account_id', 'box'), folder=folder, uidvalidity=f.imap.validities[folder], uid=uid,
                     message_id=str(BytesParser().parsebytes(raw, headersonly=True).get('Message-ID', '')),
                     sha256=__import__('hashlib').sha256(raw).hexdigest())
                for uid, raw in f.imap.boxes.get(folder, {}).items()]

    @contextmanager
    def observe(self, faults=None, delivered=True):
        s, f, oracle = self.scenario, self.scenario.fixture, self.oracle
        from storage_faults import ACTIVE
        faults = faults or ACTIVE
        previous_call = getattr(oracle, 'active_call', None)
        previous_start = getattr(oracle, 'active_start_seq', 0)
        before = self.snapshot()
        oracle.active_start_seq = max(before.committed, default=0)
        oracle.call(s.action, s.args, time.time(), {'mode': faults.mode, 'at': faults.fail_at,
                    'cleanup': faults.cleanup_at, 'background': getattr(s, 'flow', '') in {'expiry', 'maintenance'}} if faults else {})
        self.call_index = len(oracle.script) - 1
        oracle.script[self.call_index]['start_seq'] = oracle.active_start_seq
        oracle.script[self.call_index]['restore_precondition'] = before.locked
        # These four results are made by Scenario.call, not a public request.
        oracle.script[self.call_index]['synthetic_result'] = s.flow if getattr(s, 'flow', '') in {
            'expiry', 'maintenance', 'restart_index', 'restart_tail'} else None
        oracle.active_call = oracle.call_id
        oracle.delimiters = {name: getattr(f.imap, 'separators', {}).get(name, '/') for name in f.imap.roles}
        if s.action != 'control_log' or 'cursor' not in s.args:
            oracle.server('FIXTURE_STATE', 'box', roles=f.imap.roles, mailboxes={name: self.identities(name) for name in f.imap.boxes})
        if 'export' in getattr(s, 'flow', ''):
            # This is the fixture's source byte string, before production has
            # encoded, published or reported its export.
            raw = b'Synthetic exported bytes'
            oracle.server('EXPORT_INPUT', size=len(raw), sha256=__import__('hashlib').sha256(raw).hexdigest())
        # Command logs are memory-only. Reading their context cannot itself hit
        # an injected write or make an owner warning appear in production.
        uid, listing, select = f.imap.uid, f.imap.list, f.imap.select
        def listed(*args, **kwargs):
            answer = listing(*args, **kwargs)
            import re, json
            for raw in answer[1]:
                match = re.match(rb'\([^)]*\) (NIL|"[^"]*") (.*)', raw)
                if match:
                    name = folder_name(match[2])
                    oracle.delimiters[name] = None if match[1] == b'NIL' else json.loads(match[1])
            oracle.server('LIST', getattr(self, 'account_id', 'box'), before_seq=max(self.snapshot().committed, default=0), check_sources=[self.checking_source] if getattr(self, 'checking_source', None) else [], roles=f.imap.roles, mailboxes={name: self.identities(name) for name in f.imap.boxes})
            return answer
        def selected(*args, **kwargs):
            answer = select(*args, **kwargs)
            oracle.server('SELECT', getattr(self, 'account_id', 'box'), f.imap.selected, self.identities(f.imap.selected), f.imap.roles)
            return answer
        def command(name, *args, **kwargs):
            folder = f.imap.selected
            before = self.identities(folder) if folder else []
            event = oracle.server(name, getattr(self, 'account_id', 'box'), folder, before, f.imap.roles, accepted=False, reply='lost', arguments=list(args), **self.precommit())
            answer = uid(name, *args, **kwargs)
            event.update(accepted=answer[0] == 'OK', reply='delivered', roles_after=copy.deepcopy(f.imap.roles), response_code=answer[0], response_text=[v.decode(errors='replace') if isinstance(v, bytes) else v for v in answer[1] or []])
            if name == 'SEARCH' and len(args) >= 4 and args[2] == 'Message-ID':
                mid = args[3].strip('"')
                identities = [{k: v for k, v in r.items() if k != 'sha256'} for r in self.identities(folder) if r['message_id'] == mid]
                record = self.snapshot()
                operation_ids = {row['id'] for key, row in record.rows.items() if key.startswith('op:')}
                operation_ids.update(call['arguments']['operation_id'] for call in oracle.script
                    if isinstance(call.get('arguments'), dict) and isinstance(call['arguments'].get('operation_id'), str))
                for operation_id in operation_ids:
                    if '<' + operation_id.replace(':', '.') + '@mail.aresos.invalid>' == mid:
                        oracle.server('SENT', getattr(self, 'account_id', 'box'), folder, identities, f.imap.roles, source='op:' + operation_id, before_seq=max(record.committed, default=0))
            return answer
        response = f.imap.response
        def responded(name):
            answer = response(name)
            if name == 'COPYUID':
                import re
                raw = b' '.join(value for value in answer[1] or [] if value)
                match = re.fullmatch(rb'([1-9]\d*) ([1-9]\d*) ([1-9]\d*)', raw)
                for event in reversed(oracle.servers):
                    if event['command'] in {'MOVE', 'COPY'} and event['call'] == (getattr(oracle, 'active_call', None) or oracle.call_id) and 'copyuid_delivered' not in event:
                        event['copyuid_delivered'] = bool(match and int(match[2]) == int(event['arguments'][0]))
                        if event['copyuid_delivered']:
                            ref = next((ref for ref in event['identities'] if ref['uid'] == int(match[2])), {})
                            event['destination'] = {k: v for k, v in ref.items() if k != 'sha256'}
                            event['destination'].update(folder=event['arguments'][1].strip('"'), uidvalidity=int(match[1]), uid=int(match[3]))
                        break
            return answer
        rename = getattr(f.imap, 'rename', None)
        def renamed(*args, **kwargs):
            event = oracle.server('RENAME', getattr(self, 'account_id', 'box'), args[0].strip(chr(34)), self.identities(args[0].strip(chr(34))), roles=f.imap.roles, accepted=False, reply='lost', arguments=list(args), **self.precommit())
            answer = rename(*args, **kwargs)
            event.update(accepted=answer[0] == 'OK', reply='delivered', roles_after=copy.deepcopy(f.imap.roles), response_code=answer[0], response_text=[v.decode(errors='replace') if isinstance(v, bytes) else v for v in answer[1] or []])
            return answer
        append = f.mail.append
        def appended(account, folder, raw, flags=None):
            event = oracle.server('APPEND', account['id'], folder, roles=f.imap.roles,
                identities=[__import__('owner_state_oracle.transcript', fromlist=['Transcript']).Transcript.message(raw)], raw_sha256=__import__('hashlib').sha256(raw).hexdigest(), accepted=False, reply='lost',
                append_flags=flags, raw_hex=raw.hex(), **self.precommit())
            value = append(account, folder, raw, flags)
            event.update(accepted=True, reply='delivered', arrived=self.identities(folder, account['id']))
            return value
        extra = ExitStack()
        imap = f.mail.transport.imap
        @contextmanager
        def imap_session(account):
            previous = getattr(self, 'account_id', 'box')
            self.account_id = account['id']
            try:
                event = oracle.server('CONNECT', account['id'], accepted=False, reply='lost')
                with imap(account) as client:
                    event.update(accepted=True, reply='delivered')
                    yield client
            finally:
                self.account_id = previous
        extra.enter_context(patch.object(f.mail.transport, 'imap', side_effect=imap_session))
        for name in ('create', 'delete'):
            original = getattr(f.imap, name, None)
            if original is None:
                continue
            def folder_command(*args, _name=name, _original=original, **kwargs):
                event = oracle.server(_name.upper(), getattr(self, 'account_id', 'box'), roles=f.imap.roles, accepted=False, reply='lost', arguments=list(args), **self.precommit())
                answer = _original(*args, **kwargs)
                event.update(accepted=answer[0] == 'OK', reply='delivered', roles_after=copy.deepcopy(f.imap.roles), response_code=answer[0], response_text=[v.decode(errors='replace') if isinstance(v, bytes) else v for v in answer[1] or []])
                return answer
            extra.enter_context(patch.object(f.imap, name, side_effect=folder_command))
        committed_snapshot = self.snapshot
        before_context = self.precommit
        smtp = f.mail.transport.smtp
        @contextmanager
        def smtp_session(account):
            with smtp(account) as connection:
                accepted_recipients, intended_recipients, sender = [], [], [None]
                class LoggedSMTP:
                    def __getattr__(self, name):
                        method = getattr(connection, name)
                        if name not in {'mail', 'rcpt', 'data'}:
                            return method
                        def send(*args, **kwargs):
                            event = oracle.server(name.upper(), account['id'], roles=f.imap.roles, sender=sender[0], intended_recipients=list(intended_recipients), accepted=False, reply='lost',
                                recipients=[args[0]] if name == 'rcpt' else list(accepted_recipients) if name == 'data' else [], **before_context())
                            if name == 'data':
                                from .transcript import Transcript
                                event['identities'] = [Transcript.message(args[0])]
                                event['raw_hex'] = args[0].hex()
                            if name == 'rcpt':
                                intended_recipients.append(args[0])
                            if name == 'mail':
                                sender[0] = args[0]
                            answer = method(*args, **kwargs)
                            event.update(accepted=200 <= answer[0] < 300, reply='delivered', response_code=answer[0])
                            if name == 'rcpt' and event['accepted']:
                                accepted_recipients.append(args[0])
                            return answer
                        return send
                yield LoggedSMTP()
        extra.enter_context(patch.object(f.mail.transport, 'smtp', side_effect=smtp_session))
        from aresos_control.mail import adapter
        https = adapter.http.client.HTTPSConnection
        class LoggedHTTPS:
            def __init__(connection, *args, **kwargs):
                connection.inner, connection.event = https(*args, **kwargs), None
                connection.host = args[0]
                connection.port = args[1] if len(args) > 1 else kwargs.get('port', 443)
            def request(connection, method, *args, **kwargs):
                body = kwargs.get('body', args[1] if len(args) > 1 else None)
                if isinstance(body, bytes):
                    body = body.decode()
                connection.event = oracle.server(method, 'box', roles=f.imap.roles, accepted=False, reply='lost',
                    url='https://' + connection.host + (':' + str(connection.port) if connection.port != 443 else '') + (args[0] if args else '/'), body=body,
                    arguments=list(args), **self.precommit())
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
        configure = receiver.configure
        def configured(arguments):
            event = oracle.server('CONFIGURE', 'fixture', arguments=arguments,
                accepted=False, reply='lost', **self.precommit())
            result = configure(arguments)
            event.update(accepted=True, reply='delivered')
            return result
        extra.enter_context(patch.object(receiver, 'configure', side_effect=configured))
        accept = receiver.accept
        receiving = [None]
        checkpoint = receiver.checkpoint
        def received_checkpoint(name):
            if name.startswith('receiver_arrival:') and receiving[0] is not None:
                receiving[0]['accepted'] = True
            return checkpoint(name)
        extra.enter_context(patch.object(receiver, 'checkpoint', side_effect=received_checkpoint))
        def receive(operation_id, recipient, payload):
            event = oracle.server('RECEIVE', 'fixture', identities=[{'operation_id': operation_id}],
                                  recipients=[recipient], accepted=False, reply='lost', **self.precommit())
            receiving[0] = event
            try:
                with outside_faults():
                    result = accept(operation_id, recipient, payload)
            finally:
                receiving[0] = None
            event.update(accepted=result == 'accepted', reply='delivered')
            return result
        extra.enter_context(patch.object(receiver, 'accept', side_effect=receive))
        local_stage = receiver.local_stage
        def receiver_stage(operation_id, stage):
            event = oracle.server('LOCAL_STAGE', 'fixture', identities=[{'operation_id': operation_id}], stage=stage, accepted=False, reply='lost', **self.precommit())
            result = local_stage(operation_id, stage)
            event.update(accepted=True, reply='delivered')
            return result
        extra.enter_context(patch.object(receiver, 'local_stage', side_effect=receiver_stage))
        from aresos_control.mail import filing
        resolve_checks, get, scan = filing.resolve_checks, f.engine.store.get, filing.locations
        self.checking_source = None
        checking = [False]
        def checking_get(key, *args, **kwargs):
            if checking[0] and key.startswith(('mail:filing:', 'mail:rename:')):
                self.checking_source = key
            return get(key, *args, **kwargs)
        def checked(mail):
            previous, previous_source = checking[0], self.checking_source
            checking[0] = True
            try:
                return resolve_checks(mail)
            finally:
                checking[0], self.checking_source = previous, previous_source
        def scanned(mail, account, records):
            start = len(oracle.servers)
            expected = {name: self.identities(name, account['id']) for name in f.imap.boxes
                        if '\\Noselect' not in f.imap.roles.get(name, [])}
            result = scan(mail, account, records)
            events = oracle.servers[start:]
            complete = all(any(e['command'] == 'SELECT' and e.get('folder') == name and e['accepted'] and e['reply'] == 'delivered' for e in events)
                and all(any(e['command'] == 'FETCH' and e.get('folder') == name and e.get('arguments', [None])[0] == str(ref['uid']) and e['accepted'] and e['reply'] == 'delivered' for e in events)
                        for ref in refs) for name, refs in expected.items())
            oracle.server('SCAN_RESULT', account['id'], accepted=complete, before_seq=max(self.snapshot().committed, default=0),
                          check_sources=[self.checking_source] if self.checking_source else [], scan_start=start)
            return result
        extra.enter_context(patch.object(filing, 'resolve_checks', side_effect=checked))
        extra.enter_context(patch.object(f.engine.store, 'get', side_effect=checking_get))
        extra.enter_context(patch.object(filing, 'locations', side_effect=scanned))
        with extra, patch.object(f.imap, 'response', side_effect=responded), patch.object(f.imap, 'rename', side_effect=renamed, create=True), patch.object(f.imap, 'uid', side_effect=command), patch.object(f.imap, 'list', side_effect=listed), \
             patch.object(f.imap, 'select', side_effect=selected), patch.object(f.mail, 'append', side_effect=appended):
            yield
        oracle.script[self.call_index]['end_seq'] = max(self.snapshot().committed, default=0)
        if faults:
            oracle.script[self.call_index]['faults']['trace'] = list(faults.failures)
            oracle.script[self.call_index]['faults']['active_exhaustion'] = faults.mode == 'persistent' and faults.failed
        oracle.active_call = previous_call
        oracle.active_start_seq = previous_start

    def reply(self, reply, delivered=True):
        if not hasattr(self, 'call_reply'):
            self.call_reply = copy.deepcopy(reply)
        self.oracle.script[self.call_index].update(reply='delivered' if delivered else 'lost', result=copy.deepcopy(reply))
        self.capture_response(self.call_index, reply)

    def capture_response(self, index, reply):
        call = self.oracle.script[index]
        if call['call'] in self.envelopes_seen or call.get('synthetic_result') in {
                'expiry', 'maintenance', 'restart_index', 'restart_tail'}:
            return
        self.envelopes_seen.add(call['call'])
        record = self.snapshot()
        active = getattr(self.oracle, 'active_call', None)
        for pending in self.oracle.script:
            if pending['call'] == active:
                pending['end_seq'] = max(record.committed, default=0)
        expected = self.oracle.expected(record)
        self.envelopes.append((copy.deepcopy(call), copy.deepcopy(reply), record, expected))

    def drain_envelopes(self, checker):
        envelopes, self.envelopes = self.envelopes, []
        for call, reply, record, expected in envelopes:
            action = call['action']
            # An early refusal can precede app routing and is all-app scoped.
            app = action.split('_', 1)[0] if action.startswith(('mail_', 'testapp_')) else None
            if not reply.get('ok') and reply.get('error', {}).get('code') in {'journal_incomplete', 'storage_limit', 'storage_error'}:
                app = None
            compare_envelope('envelope.' + action, reply, record, self.oracle, expected, checker, app)
            if action == 'mail_accounts' or action in {'mail_account_add', 'mail_account_settings'}:
                checker('qualification.' + action, self.oracle.qualification_facts(reply, record), self.oracle.qualification_facts(reply, record, actual=True))
                if action == 'mail_account_add' and reply.get('ok') and self.oracle.qualification(record):
                    caveat = any(not q['ready'] and q['sent_policy'] == 'client' for q in self.oracle.qualification(record).values())
                    checker('qualification.sent-caveat', {Fact('qualification', 'bounded-client-caveat')} if caveat else set(),
                        {Fact('qualification', 'bounded-client-caveat')} if 'bounded window' in reply.get('data', {}).get('notice', '') and 'unready' in reply['data']['notice'] else set())

    def compare(self, check=None):
        f = self.scenario.fixture
        def read(action, args):
            boundary = len(self.oracle.servers)
            before = self.snapshot()
            known_events = {event['seq'] for event in [*before.events, *before.prepared]}
            with self.observe_view(action, args):
                reply, schema_errors = read_response(lambda: f.engine.request({'v': 1, 'method': 'call', 'action': action, 'arguments': args}))
            self.reply(reply)
            self.drain_envelopes(checker)
            call = self.oracle.script[self.call_index]
            compare_status(reply, self.oracle, self.snapshot(), call, checker, 'response.' + action)
            checker('response-schema.' + action, set(),
                {Fact('response:' + action, 'schema', detail=error) for error in schema_errors})
            assert not any(event['command'] in MUTATIONS for event in self.oracle.servers[boundary:]), ('Read attempted a mutation', action)
            after = self.snapshot()
            assert not any(event['seq'] not in known_events and event['action'] in {'testapp_delete', 'mail_account_settings', 'mail_account_folders'}
                and any(key == 'testapp' or key.startswith('mail:account:') for key in event['set'])
                for event in [*after.events, *after.prepared]), ('Read committed a local mutation', action)
            return reply
        checker = check or self.oracle.compare
        record = self.snapshot()
        self.drain_envelopes(checker)
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
        try:
            actual_generation = {Fact('generation', 'matches' if f.engine.store.generation == record.generation else 'mismatch')}
        except (OSError, sqlite3.Error) as error:
            actual_generation = {Fact('generation', 'unavailable', detail=type(error).__name__)}
        checker('restore-generation', {Fact('generation', 'matches')}, actual_generation)
        checker('recovery-holds', self.oracle.holds(record), {Fact(key, 'held') for key in f.engine.store.ledger.holds if key != 'replay'})
        checker('R2.context-before-command', set(), self.oracle.context_errors() | self.oracle.local_context_errors(record, self.context_start_sequence))
        compare_views(read, self.oracle, self.snapshot, checker, ordinary='testapp_list' if getattr(self.scenario, 'flow', '').startswith('testapp_') else 'mail_accounts')
        # Only after warning preservation has been checked on every view may
        # operation_status fetch evidence. Its committed approval/stages must be
        # exposed exactly, including recipients bound in the approval.
        for key, operation in list(self.snapshot().rows.items()):
            if not key.startswith('op:'):
                continue
            result = read(operation['app'] + '_operation_status', {'operation_id': operation['id']})
            committed = self.snapshot().rows.get(key, operation)
            actual = result.get('data', {}).get('operation', {})
            for field in ('approval', 'stages', 'state'):
                wanted = committed.get(field)
                got = actual.get(field)
                def differences(left, right, path=''):
                    if isinstance(left, dict) and isinstance(right, dict):
                        return [child for name in sorted(left.keys() | right.keys()) for child in
                            differences(left.get(name), right.get(name), path + '/' + (name.split(':', 1)[0] + ':*' if ':' in name else name))]
                    if isinstance(left, list) and isinstance(right, list):
                        return [child for index in range(max(len(left), len(right))) for child in
                            differences(left[index] if index < len(left) else None, right[index] if index < len(right) else None, path + '/' + str(index))]
                    return [] if left == right else [path or '/']
                checker('operation-' + field, {Fact(key, field, detail='committed')},
                    {Fact(key, field, detail='committed')} if actual and wanted == got else
                    {Fact(key, field + '.mismatch', detail=canonical(differences(wanted, got)))} if actual else set())
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
        # Status/location reads can commit a result too. Their proof failures
        # belong to this comparison, including the very last response.
        compare_proofs(self.oracle, self.snapshot(), checker, context=False)
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
