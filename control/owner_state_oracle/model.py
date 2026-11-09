"""Expectations from calls, server evidence and committed local transitions only."""
from dataclasses import dataclass
import copy
import hashlib
from .records import canonical, fingerprint


@dataclass(frozen=True, order=True)
class Fact:
    source: str
    kind: str
    occurrence: str = ''
    detail: str = ''


class Oracle:
    def __init__(self):
        self.script = []
        self.servers = []
        self.occurrences = {}  # (source, kind, evidence, clean epoch) -> stable id
        self.epochs = {}
        self.last_clean = {}
        self.acknowledged = set()
        self.detected = set()
        self.call_id = 0
        self.processed_server = 0
        self.location_evidence = {}
        self.open_occurrences = {}

    def call(self, action, arguments, clock, faults=None):
        self.call_id += 1
        self.script.append({'call': self.call_id, 'action': action, 'arguments': copy.deepcopy(arguments),
                            'clock': clock, 'faults': copy.deepcopy(faults or {}), 'reply': 'pending'})
        return self.call_id

    def reply(self, value, delivered=True):
        self.script[-1].update(reply='delivered' if delivered else 'lost', result=copy.deepcopy(value))

    def server(self, command, account=None, folder=None, identities=(), roles=None,
               accepted=True, reply='delivered', **extra):
        event = {'call': getattr(self, 'active_call', None) or self.call_id, 'command': command, 'account': account, 'folder': folder,
                 'identities': copy.deepcopy(list(identities)), 'roles': copy.deepcopy(roles),
                 'accepted': accepted, 'reply': reply, **copy.deepcopy(extra)}
        self.servers.append(event)
        return event

    def warning(self, source, kind, evidence, record):
        """Evidence selects occurrence; disk supplies only the opaque UUID binding.

        Deleting the notice must never delete the expected warning. A new UUID
        cannot excuse unchanged evidence, or hide a warning after acknowledgement.
        """
        encoded = canonical(evidence)
        key = (source, kind, encoded, self.epochs.get((source, kind), 0))
        expected_fingerprint = fingerprint(sorted({canonical(ref) for ref in evidence}) if kind == 'sent_copies' else evidence)
        if key not in self.occurrences:
            matches = [n for k, n in record.rows.items() if k.startswith('notice:') and
                       n.get('source_key') == source and n.get('check_kind') == kind and
                       (n.get('evidence_fingerprint') == expected_fingerprint or 'evidence_fingerprint' not in n) and
                       n['id'] not in self.occurrences.values()]
            self.occurrences[key] = matches[-1]['id'] if matches else 'uncommitted:' + hashlib.sha256(canonical(key).encode()).hexdigest()[:24]
        role = evidence.get('role', '') if isinstance(evidence, dict) else ''
        detail = {'count': len(evidence)} if kind == 'sent_copies' else {'role': 'Trash' if 'Trash' in role else 'Drafts' if 'Drafts' in role else 'ordinary'}
        if isinstance(evidence, dict) and (evidence.get('unresolved_roles') or any(not row.get('scan_complete', True) for row in evidence.get('locations', []))):
            self.open_occurrences[source] = self.occurrences[key]
        if isinstance(evidence, dict) and 'locations' in evidence:
            self.location_evidence[self.occurrences[key]] = (source, copy.deepcopy(evidence['locations']))
        return Fact(source, kind, self.occurrences[key], canonical(detail))

    def expected(self, record, live=False, app=None):
        facts = set()
        # Acks are transitions, never a notice-table filter. A restore cannot
        # roll back an acknowledgement already witnessed by this oracle.
        for event in record.events:
            for key, value in event['set'].items():
                if key.startswith('notice:') and value and value.get('ack'):
                    self.acknowledged.add(value['id'])
            if event['action'].endswith('_notice_ack'):
                for key, value in event['set'].items():
                    if key.startswith('op:') and value and value.get('ack'):
                        self.acknowledged.add('operation:' + value['id'])
        for event in record.events:
            for source, value in event['set'].items():
                if not isinstance(value, dict):
                    continue
                for kind, checked in value.get('warning_checks', {}).items():
                    if checked.get('warning') is False and event['seq'] > self.last_clean.get((source, kind), 0):
                        self.last_clean[source, kind] = event['seq']
                        self.epochs[source, kind] = self.epochs.get((source, kind), 0) + 1
        for key, row in record.rows.items():
            if key.startswith('op:'):
                if app is None or row['app'] == app:
                    if row['state'] in {'reserved', 'submitting', 'partial', 'unknown'} or (row.get('notice') and 'operation:' + row['id'] not in self.acknowledged):
                        facts.add(Fact(key, 'pending', detail=canonical({'state': row['state'], 'reason': row.get('reason')})))
                if row['state'] in {'submitting', 'unknown', 'partial'} and (app is None or row['app'] == app):
                    facts.add(Fact(key, 'recovery'))
                check = row.get('sent_copy_check', {})
                if row['app'] == 'mail' and (app is None or app == 'mail'):
                    clean_seq = max((e['seq'] for e in record.events if (e['set'].get(key) or {}).get('sent_copy_check', {}).get('clean')), default=0)
                    if clean_seq > self.last_clean.get((key, 'sent_copies'), 0):
                        self.last_clean[key, 'sent_copies'] = clean_seq
                        self.epochs[key, 'sent_copies'] = self.epochs.get((key, 'sent_copies'), 0) + 1
                    failed_recheck = live and bool(check) and self.script and self.script[-1].get('result', {}).get('error', {}).get('code') in {'storage_limit', 'storage_error', 'journal_incomplete'}
                    if (check.get('state') == 'open' or failed_recheck) and not any(f.source == key and f.kind == 'sent_copies' and f.occurrence not in self.acknowledged for f in self.detected):
                        facts.add(Fact(key, 'unchecked'))
            elif key.startswith(('mail:filing:', 'mail:rename:', 'intent:', 'export:', 'mail:account:')):
                row_app = row.get('app', 'mail')
                if app is not None and row_app != app:
                    continue
                open_check = (key.startswith(('mail:filing:', 'mail:rename:')) and (row.get('state') == 'started' or row.get('check_open')))
                unfinished = (open_check or key.startswith(('intent:', 'export:')) or
                    key.startswith('mail:account:') and not row.get('onboarded', row.get('ready', False)))
                if unfinished:
                    facts.add(Fact(key, 'recovery'))
        # Recover raw LIST evidence for committed, unresolved checks too. Check
        # completion is a local committed fact; the role observation is remote.
        for event in self.servers[self.processed_server:]:
            if event['command'] != 'LIST':
                continue
            roles = event.get('roles') or {}
            for source, context in record.rows.items():
                if not source.startswith(('mail:filing:', 'mail:rename:')):
                    continue
                if context.get('state') != 'started' and not context.get('check_open'):
                    continue
                target = context.get('target')
                if target not in roles:
                    continue
                observed = [flag.lstrip('\\').title() for folder, flags in roles.items()
                            if target == folder or target.startswith(folder + '/') for flag in flags
                            if flag.lower() in {'\\trash', '\\drafts', '\\sent', '\\junk', '\\archive'}]
                role = ', '.join(sorted(set(observed))) or 'an ordinary folder'
                unresolved = [kind for kind in ('sent', 'drafts', 'trash') if sum('\\' + kind in [v.lower() for v in flags] for flags in roles.values()) != 1]
                evidence = {'target': target, 'role': role, 'unresolved_roles': unresolved}
                if source.startswith('mail:filing:'):
                    evidence['locations'] = self.locations(context, event)
                self.detected.add(self.warning(source, 'rename' if source.startswith('mail:rename:') else 'filing', evidence, record))
        # Every observed warning survives changed evidence/clean/action end,
        # until that occurrence has its own committed acknowledgement.
        # Interpret raw server commands and LIST replies here. The driver may
        # not pre-classify warning evidence using production outcomes/checks.
        for index, event in enumerate(self.servers):
            if index < self.processed_server or event['command'] != 'LIST':
                continue
            mutations = [m for m in self.servers[:index] if m['call'] == event['call'] and
                         m['command'] in {'MOVE', 'COPY', 'RENAME'} and m['accepted']]
            for mutation in mutations[-1:]:
                args = mutation.get('arguments', [])
                target = args[1].strip('"') if len(args) > 1 else None
                roles = event.get('roles') or {}
                before = mutation.get('roles') or {}
                observed = [flag.lstrip('\\').title() for folder, flags in roles.items()
                            if target == folder or target and target.startswith(folder + '/')
                            for flag in flags if flag.lower() in {'\\trash', '\\drafts', '\\sent', '\\junk', '\\archive'}]
                if roles == before and not observed and not (mutation['command'] in {'MOVE', 'COPY'} and not mutation.get('copyuid_delivered')):
                    continue
                # Committed context binds this command to its intent identity;
                # its claimed completion cannot suppress observed drift.
                for source, context in mutation.get('committed_before', {}).items():
                    if not source.startswith(('mail:filing:', 'mail:rename:')) or context.get('target') != target:
                        continue
                    kind = 'rename' if source.startswith('mail:rename:') else 'filing'
                    unresolved = [kind for kind in ('sent', 'drafts', 'trash') if sum('\\' + kind in [v.lower() for v in flags] for flags in roles.values()) != 1]
                    role = ', '.join(sorted(set(observed))) or 'an ordinary folder'
                    evidence = {'target': target, 'role': role}
                    if kind == 'rename' and target in roles and roles[target]:
                        evidence['role'] = ', '.join(sorted(flag.title() for flag in roles[target] if flag.lower() in {'\\trash', '\\drafts', '\\sent', '\\junk', '\\archive'})) or role
                    if kind == 'filing':
                        evidence.update(locations=self.locations(context, event, mutation), unresolved_roles=unresolved)
                    self.detected.add(self.warning(source, kind, evidence, record))
        for event in self.servers[self.processed_server:]:
            if event['command'] == 'WARNING':
                self.detected.add(self.warning(event['source'], event['kind'], event['evidence'], record))
            elif event['command'] == 'SENT' and len(event['identities']) > 1:
                self.detected.add(self.warning(event['source'], 'sent_copies', sorted(event['identities'], key=canonical), record))
        self.processed_server = len(self.servers)
        facts.update(f for f in self.detected if f.occurrence not in self.acknowledged and
                     (app is None or app == 'mail'))
        for source, occurrence in self.open_occurrences.items():
            recovery = Fact(source, 'recovery')
            if recovery in facts and occurrence not in self.acknowledged:
                facts.remove(recovery)
                facts.add(Fact(source, 'recovery', occurrence))
        return facts


    def locations(self, context, listing, mutation=None):
        result = []
        for item in context.get('records', []):
            found = [{k: v for k, v in ref.items() if k != 'sha256'}
                     for refs in listing.get('mailboxes', {}).values() for ref in refs
                     if ref.get('sha256') == item['sha256']]
            scan_complete = not any(e['call'] == listing['call'] and e['command'] == 'FETCH' and not e['accepted'] for e in self.servers)
            if not scan_complete:
                start = next((i for i, e in enumerate(self.servers) if e is listing), 0)
                observed = {(e['folder'], int(e['arguments'][0])) for e in self.servers[start + 1:]
                            if e['call'] == listing['call'] and e['command'] == 'FETCH' and e['accepted']}
                found = [ref for ref in found if (ref['folder'], ref['uid']) in observed]
            destination = item.get('destination')
            if mutation and mutation.get('destination') and str(item['source']['uid']) == str(mutation.get('arguments', [''])[0]):
                destination = mutation['destination']
            result.append({'source': item['source'], 'last_known_destination': destination,
                           'observed_locations': sorted(found, key=canonical), 'scan_complete': scan_complete})
        return sorted(result, key=canonical)

    def request_state(self, record, call):
        if record.locked:
            return {Fact('request', 'restore_required')}
        if record.prepared or len(record.fences) > max(record.committed, default=0):
            return {Fact('request', 'journal_incomplete')}
        if call.get('faults', {}).get('admission') == 'full':
            return {Fact('request', 'storage_limit')}
        return {Fact('request', 'allowed')}

    def holds(self, record):
        keys = set()
        for key, row in record.rows.items():
            if key.startswith('export:'):
                keys.add(key)
            if key.startswith('op:'):
                if row.get('repair_of') and row['state'] in {'reserved', 'submitting', 'unknown'}:
                    keys.add('settle:' + row['id'])
                elif row['state'] == 'reserved':
                    keys.add('cancel:' + row['id'])
        if record.locked:
            keys.add('restore')
        return {Fact(key, 'held') for key in keys}

    def completion_errors(self, record):
        errors = set()
        for key, operation in record.rows.items():
            if not key.startswith('op:') or operation.get('state') != 'done':
                continue
            action = operation.get('action', '')
            if action == 'mail_send' or action == 'mail_unsubscribe' and operation.get('payload', {}).get('composition'):
                mid = '<' + operation['id'].replace(':', '.') + '@mail.aresos.invalid>'
                deliveries = [e for e in self.servers if e['command'] == 'DATA' and e['accepted'] and any(i.get('message_id') == mid for i in e['identities'])]
                if not deliveries:
                    errors.add(Fact(key, 'false-completion', detail='No matching accepted SMTP DATA'))
            elif action == 'mail_unsubscribe':
                if not any(e['command'] == 'POST' and e['accepted'] for e in self.servers):
                    errors.add(Fact(key, 'false-completion', detail='No accepted POST'))
        return errors

    def context_errors(self):
        errors = set()
        mutations = {'DATA', 'APPEND', 'MOVE', 'COPY', 'STORE', 'EXPUNGE', 'CREATE', 'DELETE', 'RENAME', 'POST', 'RECEIVE'}
        for index, event in enumerate(self.servers):
            if event['command'] not in mutations or event.get('fixture_seed'):
                continue
            rows = event.get('committed_before', {})
            candidates = [v for k, v in rows.items() if k.startswith(('op:', 'intent:', 'mail:filing:', 'mail:rename:')) and isinstance(v, dict)]
            command = event['command']
            missing = set()
            if not candidates:
                missing.add('intent identity')
            encoded = canonical(candidates)
            account = event.get('account')
            if account and canonical(account) not in encoded:
                missing.add('account')
            if command in {'APPEND', 'CREATE', 'DELETE', 'RENAME', 'MOVE', 'COPY'}:
                target = event.get('folder') if command == 'APPEND' else (event.get('arguments') or [''])[-1].strip('"')
                if target and canonical(target) not in encoded:
                    missing.add('destination')
            if command == 'APPEND' and event.get('raw_sha256') and event['raw_sha256'] not in encoded:
                # Approved Sent copies also bind their immutable Message-ID and
                # wire hash. Generic draft/probe identities have neither today.
                identities = event.get('identities', [])
                if not identities or not any(i.get('message_id') and i['message_id'] in encoded for i in identities):
                    missing.add('message identity')
            if command in {'MOVE', 'COPY', 'RENAME'} and not any('roles_before' in c for c in candidates):
                missing.add('preparation roles')
            if command in {'DATA', 'RECEIVE'}:
                for recipient in event.get('recipients', []):
                    if canonical(recipient) not in encoded:
                        missing.add('recipients')
            if missing:
                errors.add(Fact('command:' + str(index), 'R2.' + command, detail=canonical(sorted(missing))))
        return errors

    def require_context(self, command, committed_before):
        """R2 order assertion uses the exact command's context, never latest kv."""
        context = command['context']
        rows = committed_before.rows
        required = {'account', 'identities', 'source', 'destination', 'roles', 'recipients'}
        assert required <= context.keys(), ('R2 incomplete server log', command)
        assert any(value.get('context') == context for value in rows.values() if isinstance(value, dict)), ('R2 context not committed before command', command)

    def compare(self, view, expected, actual):
        missing, extra = expected - actual, actual - expected
        assert not missing and not extra, (view, 'missing', sorted(missing), 'extra', sorted(extra))
