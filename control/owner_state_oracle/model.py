"""Expectations from calls, server evidence and committed local transitions only."""
from dataclasses import dataclass
from email.utils import getaddresses
import copy
import hashlib
import json
from .records import canonical, fingerprint
from .context import bind as bind_context, differences as context_differences, special_roles, MUTATIONS


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
        self.warning_started = {}
        self.examined_clean = set()
        self.invalid_clean_results = set()
        self.warning_contexts = {}
        self.open_checks = set()

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

    def warning(self, source, kind, evidence, record, context=None):
        """Evidence selects occurrence; disk supplies only the opaque UUID binding.

        Deleting the notice must never delete the expected warning. A new UUID
        cannot excuse unchanged evidence, or hide a warning after acknowledgement.
        """
        if context is not None:
            self.warning_contexts.setdefault(source, copy.deepcopy(context))
        elif source not in self.warning_contexts:
            prepared = next((e['set'][source] for e in record.events if isinstance(e['set'].get(source), dict)), record.rows.get(source, {}))
            self.warning_contexts[source] = copy.deepcopy(prepared)
        self.warning_started.setdefault((source, kind), max(record.committed, default=max((event['seq'] for event in record.events), default=0)))
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
            self.open_checks.add(source)
        elif source in self.open_checks and isinstance(evidence, dict):
            current = record.rows.get(source, {})
            checked = current.get('warning_checks', {}).get(kind, {})
            if checked.get('fingerprint') == expected_fingerprint and not current.get('check_open') and current.get('state') != 'started':
                self.open_checks.discard(source)
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
        previous = {}
        for event in record.events:
            for source, value in event['set'].items():
                if not isinstance(value, dict):
                    continue
                kinds = {kind for kind, checked in value.get('warning_checks', {}).items() if checked.get('warning') is False}
                if value.get('sent_copy_check', {}).get('clean') and value.get('sent_copy_check', {}).get('state') == 'checked':
                    kinds.add('sent_copies')
                for kind in kinds:
                    marker = source, kind, event['seq']
                    if event['seq'] <= self.warning_started.get((source, kind), float('inf')) or marker in self.examined_clean:
                        continue
                    old = previous.get(source, {})
                    changed = event['action'] in {'mail_sent_copy_check', 'mail_filing_check'} or (
                        kind == 'sent_copies' and old.get('sent_copy_check', {}).get('state') == 'open' and value.get('sent_copy_check', {}).get('state') == 'checked') or old.get('warning_checks', {}).get(kind, {}).get('warning') is True
                    if not changed:
                        continue
                    self.examined_clean.add(marker)
                    if self.clean_proof(source, kind, event['seq']):
                        self.last_clean[source, kind] = event['seq']
                        self.epochs[source, kind] = self.epochs.get((source, kind), 0) + 1
                        if kind in {'filing', 'rename'}:
                            self.open_checks.discard(source)
                    else:
                        self.invalid_clean_results.add(Fact(source, 'unverified-clean', detail=kind))
                previous[source] = value
        for key, row in record.rows.items():
            if key.startswith('op:'):
                if app is None or row['app'] == app:
                    if row['state'] in {'reserved', 'submitting', 'partial', 'unknown'} or (row.get('notice') and 'operation:' + row['id'] not in self.acknowledged):
                        facts.add(Fact(key, 'pending', detail=canonical({'state': row['state'], 'reason': 'RESTORED_EVIDENCE' if 'restored' in row.get('reason', '').lower() and any(word in row.get('reason', '').lower() for word in ('newer', 'missing')) else row.get('reason')})))
                if row['state'] in {'submitting', 'unknown', 'partial'} and (app is None or row['app'] == app):
                    facts.add(Fact(key, 'recovery'))
                check = row.get('sent_copy_check', {})
                if row['app'] == 'mail' and (app is None or app == 'mail'):
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
        if record.locked:
            latest, local = {}, {}
            for fence in record.fences:
                for operation in fence.get('operations', []):
                    latest[operation['id']] = (fence['seq'], operation)
            for event in record.events:
                for operation in event['record'].get('operations', []):
                    local[operation['id']] = event['seq']
            for operation_id, (sequence, operation) in latest.items():
                source = 'op:' + operation_id
                if record.rows.get('archived:' + operation_id) == {'seq': sequence}:
                    continue
                row = record.rows.get(source)
                if row is None or local.get(operation_id) != sequence or row.get('state') == 'submitting':
                    facts = {fact for fact in facts if not (fact.source == source and fact.kind == 'pending')}
                    facts.add(Fact(source, 'pending', detail=canonical({'state': 'unknown', 'reason': 'RESTORED_EVIDENCE'})))
                    facts.add(Fact(source, 'recovery'))
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
        # Explicit healthy views must revalidate enrolled Sent identities even
        # if a regression omits the actual SEARCH or loses a working row. The
        # fixture's own mailbox state is independent evidence of what that
        # required read would return; passive envelopes never use it.
        call = self.script[-1] if self.script else {}
        action, arguments = call.get('action'), call.get('arguments', {})
        evidence_view = action in {'control_pending', 'mail_filing_notices'} or action == 'control_log' and 'cursor' not in arguments
        if live and evidence_view:
            states = [e for e in self.servers if e['command'] == 'FIXTURE_STATE']
            if states:
                state = states[-1]
                unavailable = any(e['call'] == state['call'] and e['command'] == 'CONNECT' and not e['accepted'] for e in self.servers)
                refused = call.get('result', {}).get('error', {}).get('code') in {'storage_limit', 'storage_error', 'journal_incomplete'}
                registrations = {}
                for event in record.events:
                    for source, value in event['set'].items():
                        if source.startswith('op:') and value and value.get('app') == 'mail' and value.get('payload', {}).get('composition'):
                            registrations[source] = value
                for source, operation in registrations.items():
                    if 'archived:' + operation['id'] in record.rows:
                        continue
                    account_id = operation.get('payload', {}).get('composition', {}).get('mail', {}).get('account')
                    account = record.rows.get('mail:account:' + str(account_id), {})
                    role_map = state.get('roles') or {}
                    required = account.get('special', {})
                    roles_unresolved = any([name for name, flags in role_map.items() if '\\' + role in [f.lower() for f in flags]] != [required.get(role)] for role in ('sent', 'drafts', 'trash'))
                    if unavailable or refused or roles_unresolved:
                        facts.add(Fact(source, 'unchecked'))
                        continue
                    mid = '<' + operation['id'].replace(':', '.') + '@mail.aresos.invalid>'
                    copies = [{k: v for k, v in ref.items() if k != 'sha256'}
                              for ref in state.get('mailboxes', {}).get(required.get('sent'), []) if ref['message_id'] == mid]
                    if len(copies) > 1:
                        self.detected.add(self.warning(source, 'sent_copies', sorted(copies, key=canonical), record))
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
                if special_roles(roles) == special_roles(before) and not observed and not (mutation['command'] in {'MOVE', 'COPY'} and not mutation.get('copyuid_delivered')):
                    continue
                # Committed context binds this command to its intent identity;
                # its claimed completion cannot suppress observed drift.
                source, context = bind_context(mutation, self.script)
                if source and source.startswith(('mail:filing:', 'mail:rename:')):
                    kind = 'rename' if source.startswith('mail:rename:') else 'filing'
                    unresolved = [kind for kind in ('sent', 'drafts', 'trash') if sum('\\' + kind in [v.lower() for v in flags] for flags in roles.values()) != 1]
                    role = ', '.join(sorted(set(observed))) or 'an ordinary folder'
                    evidence = {'target': target, 'role': role}
                    if kind == 'rename' and target in roles and roles[target]:
                        evidence['role'] = ', '.join(sorted(flag.title() for flag in roles[target] if flag.lower() in {'\\trash', '\\drafts', '\\sent', '\\junk', '\\archive'})) or role
                    if kind == 'filing':
                        evidence.update(locations=self.locations(context, event, mutation), unresolved_roles=unresolved)
                    self.detected.add(self.warning(source, kind, evidence, record, context))
        for event in self.servers[self.processed_server:]:
            if event['command'] == 'WARNING':
                self.detected.add(self.warning(event['source'], event['kind'], event['evidence'], record))
            elif event['command'] == 'SENT' and len(event['identities']) > 1:
                self.detected.add(self.warning(event['source'], 'sent_copies', sorted(event['identities'], key=canonical), record))
        self.processed_server = len(self.servers)
        facts.update(f for f in self.detected if f.occurrence not in self.acknowledged and
                     (app is None or app == 'mail'))
        for fact in list(facts):
            if fact.kind not in {'sent_copies', 'filing', 'rename'}:
                continue
            context = self.warning_contexts.get(fact.source, {})
            meta = {'app': 'mail', 'state': 'partial', 'intent_identity': True, 'preserves_messages': True}
            if fact.kind == 'sent_copies':
                meta.update(operation_identity=True, message_count=json.loads(fact.detail)['count'], reason_family='sent_copies')
            else:
                meta.update(filing_identity=True)
                if fact.kind == 'rename' and 'message_count' in context:
                    meta['message_count'] = context['message_count']
                    names = [context.get('source', ''), context.get('target', '')]
                    meta.update(folders=[name[:64] + ('…' if len(name) > 64 else '') for name in names], folders_more=0, folders_more_text='')
                elif fact.kind == 'filing' and context.get('sources'):
                    names = {context['target']} | {ref['folder'] for ref in context['sources']}
                    evidence_locations = self.location_evidence.get(fact.occurrence, (None, []))[1]
                    names.update(ref['folder'] for item in evidence_locations for ref in item['observed_locations'])
                    meta.update(message_count=len(context['sources']), folders=[name[:64] + ('…' if len(name) > 64 else '') for name in sorted(names)[:3]],
                                folders_more=max(0, len(names) - 3), folders_more_text='and ' + str(len(names) - 3) + ' more' if len(names) > 3 else '')
            facts.add(Fact(fact.source, 'notice-context', fact.occurrence, canonical(meta)))
        for source in self.open_checks:
            facts.add(Fact(source, 'recovery'))
        for source, occurrence in self.open_occurrences.items():
            recovery = Fact(source, 'recovery')
            if recovery in facts and occurrence not in self.acknowledged:
                facts.remove(recovery)
                facts.add(Fact(source, 'recovery', occurrence))
        for fact in list(facts):
            if fact.kind == 'recovery':
                row = record.rows.get(fact.source, self.warning_contexts.get(fact.source, {}))
                app_name = row.get('app', 'mail')
                partial = any(w.occurrence == fact.occurrence and w.kind in {'filing', 'rename'} for w in self.detected) if fact.occurrence else False
                facts.add(Fact(fact.source, 'recovery-context', fact.occurrence, canonical({
                    'app': app_name, 'state': 'partial' if partial else 'unknown', 'intent_identity': True, 'reason_present': True})))
            elif fact.kind == 'unchecked':
                facts.add(Fact(fact.source, 'unchecked-context', detail=canonical({
                    'app': 'mail', 'state': 'unknown', 'operation_identity': True, 'check': 'sent_copies', 'not_yet_checked': True})))
        self.expected_context_facts = {f for f in facts if f.kind == 'notice-context'}
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

    def clean_proof(self, source, kind, sequence):
        for evidence in self.servers:
            call = next((call for call in self.script if call['call'] == evidence['call']), {})
            before = evidence.get('before_seq')
            if not isinstance(before, int) or not before < sequence <= call.get('end_seq', -1):
                continue
            if kind == 'sent_copies':
                if evidence['command'] == 'SENT' and evidence.get('source') == source and len(evidence['identities']) <= 1:
                    return True
            elif evidence['command'] == 'LIST':
                old = next((json.loads(key[2]) for key in self.occurrences if key[0] == source and key[1] == kind), {})
                target, roles = old.get('target'), evidence.get('roles') or {}
                complete = all(len(special_roles(roles).get(role, [])) == 1 for role in ('sent', 'drafts', 'trash'))
                protected = any(target == folder or target and target.startswith(folder + '/') for role in ('trash', 'drafts', 'sent', 'junk', 'archive') for folder in special_roles(roles).get(role, []))
                failed_scan = any(e['call'] == evidence['call'] and e['command'] == 'FETCH' and not e['accepted'] for e in self.servers)
                if target in roles and complete and not protected and not failed_scan:
                    return True
        return False

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
                mail = operation.get('payload', {}).get('composition', {}).get('mail', {})
                recipients = sorted(address for _, address in getaddresses(mail.get('to', []) + mail.get('cc', []) + mail.get('bcc', [])))
                if deliveries and (len(deliveries) != 1 or sorted(deliveries[0].get('recipients', [])) != recipients):
                    errors.add(Fact(key, 'false-completion', detail='Accepted SMTP recipients differ from the full approved envelope'))
                if not deliveries:
                    errors.add(Fact(key, 'false-completion', detail='No matching accepted SMTP DATA'))
            elif action == 'mail_delete':
                payload = operation.get('payload', {})
                command = 'MOVE' if payload.get('mode') == 'trash' else 'EXPUNGE'
                for target in payload.get('items', []):
                    reference = target['reference']
                    attempted = [e for e in self.servers if e['command'] == command and e['accepted'] and
                        e.get('folder') == reference['folder'] and str((e.get('arguments') or [''])[0]) == str(reference['uid'])]
                    if len(attempted) != 1:
                        errors.add(Fact(key, 'false-completion', detail='Exact deletion target not accepted once: ' + str(reference['uid'])))
            elif action == 'testapp_send':
                payload = operation.get('payload', {})
                for recipient in payload.get('to', []) + payload.get('cc', []) + payload.get('bcc', []):
                    accepted = [e for e in self.servers if e['command'] == 'RECEIVE' and e['accepted'] and recipient in e.get('recipients', []) and any(i.get('operation_id') == operation['id'] for i in e['identities'])]
                    if len(accepted) != 1:
                        errors.add(Fact(key, 'false-completion', detail='Receiver did not accept exactly once: ' + recipient))
                for stage in ('sent_copy', 'answered_flag'):
                    if not any(e['command'] == 'LOCAL_STAGE' and e['accepted'] and e['stage'] == stage and any(i.get('operation_id') == operation['id'] for i in e['identities']) for e in self.servers):
                        errors.add(Fact(key, 'false-completion', detail='Receiver stage missing: ' + stage))
            elif action == 'testapp_delete':
                current = record.rows.get('testapp', {}).get('items', {})
                for target in operation.get('payload', {}).get('items', []):
                    if target['reference']['id'] in current:
                        errors.add(Fact(key, 'false-completion', detail='Requested fixture item still exists: ' + target['reference']['id']))
            elif action == 'mail_unsubscribe':
                if not any(e['command'] == 'POST' and e['accepted'] and e.get('reply') == 'delivered' and 200 <= e.get('status', 0) < 300 for e in self.servers):
                    errors.add(Fact(key, 'false-completion', detail='No accepted POST'))
        return errors

    def context_errors(self):
        errors = set()
        for index, event in enumerate(self.servers):
            if event['command'] not in MUTATIONS or event.get('fixture_seed'):
                continue
            _, missing = context_differences(event, self.script)
            if missing:
                errors.add(Fact('command:' + str(index), 'R2.' + event['command'], detail=canonical(missing)))
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
