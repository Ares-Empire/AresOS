"""Expectations from calls, server evidence and committed local transitions only."""
from dataclasses import dataclass
from email.utils import getaddresses
import copy
import hashlib
import json
import re
from .records import canonical, fingerprint
from .context import bind as bind_context, differences as context_differences, special_roles, special_delimiters, MUTATIONS
from .local import errors as local_errors


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
        self.lifecycle_errors = set()
        self.lifecycle_known = {}
        self.background = None
        self.semantic_occurrences = {}
        self.qualification_observed = {}

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
                 'accepted': accepted, 'reply': reply, 'delimiters': copy.deepcopy(getattr(self, 'delimiters', None)), **copy.deepcopy(extra)}
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
        self.semantic_occurrences.setdefault(key, 'semantic:' + hashlib.sha256(canonical(key).encode()).hexdigest()[:24])
        if key not in self.occurrences:
            self.occurrences[key] = 'uncommitted:' + self.semantic_occurrences[key].split(':', 1)[1]
        self.bind_occurrences(record)
        role = evidence.get('role', '') if isinstance(evidence, dict) else ''
        names = sorted(set(re.findall(r'(?<![A-Za-z])(Sent|Drafts|Trash|Junk|Archive|All|Flagged|Important)(?![A-Za-z])', role)))
        detail = {'count': len(evidence)} if kind == 'sent_copies' else {'role': ', '.join(names) if names else 'unverified' if 'unverified' in role else 'ordinary'}
        if isinstance(evidence, dict) and (evidence.get('unresolved_roles') or any(not row.get('scan_complete', True) for row in evidence.get('locations', []))):
            self.open_occurrences[source] = self.occurrences[key]
            self.open_checks.add(source)
        elif source in self.open_checks and isinstance(evidence, dict):
            current = record.rows.get(source, {})
            checked = current.get('warning_checks', {}).get(kind, {})
            if checked.get('fingerprint') == expected_fingerprint and not current.get('check_open') and current.get('state') != 'started' and self.result_proof(source, kind, max(record.committed, default=0)):
                self.open_checks.discard(source)
        if isinstance(evidence, dict) and 'locations' in evidence:
            self.location_evidence[self.occurrences[key]] = (source, copy.deepcopy(evidence['locations']))
        return Fact(source, kind, self.occurrences[key], canonical(detail))

    def expected(self, record, live=False, app=None):
        facts = set()
        record = self.lifecycle(record)
        self.bind_occurrences(record)
        self.background_history()
        if self.background and 'background-storage' not in self.acknowledged and (app is None or app == 'mail'):
            facts.add(Fact('background:storage', 'background-storage', 'background-storage', self.background['code']))
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
                    failed_recheck = live and bool(check) and self.script and bool(self.script[-1].get('faults', {}).get('trace'))
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
                            if target == folder or (event.get('delimiters') or {}).get(folder, '/') and target.startswith(folder + (event.get('delimiters') or {}).get(folder, '/')) for flag in flags
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
                refused = bool(call.get('faults', {}).get('trace')) or call.get('faults', {}).get('admission') == 'full'
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
                            if target == folder or target and (event.get('delimiters') or {}).get(folder, '/') and target.startswith(folder + (event.get('delimiters') or {}).get(folder, '/'))
                            for flag in flags if flag.lower() in {'\\trash', '\\drafts', '\\sent', '\\junk', '\\archive'}]
                if mutation['command'] == 'RENAME':
                    observed += [flag.lstrip('\\').title() for flag in roles.get(target, []) if flag.lower() in {'\\all', '\\flagged', '\\important'}]
                if special_roles(roles) == special_roles(before) and special_delimiters(roles, event.get('delimiters') or {}) == special_delimiters(before, mutation.get('delimiters') or {}) and not observed and not (mutation['command'] in {'MOVE', 'COPY'} and not mutation.get('copyuid_delivered')):
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
                        evidence['role'] = ', '.join(sorted(flag.title() for flag in roles[target] if flag.lower() in {'\\trash', '\\drafts', '\\sent', '\\junk', '\\archive', '\\all', '\\flagged', '\\important'})) or role
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
        for fact in list(facts):
            if fact.kind in {'recovery', 'unchecked'}:
                identity = self.public_handle(record, fact)
                facts.add(Fact(fact.source, fact.kind + '-handle', identity))
        self.expected_context_facts = {f for f in facts if f.kind == 'notice-context'}
        return facts


    def bind_occurrences(self, record):
        for key, old in list(self.occurrences.items()):
            if not old.startswith('uncommitted:'):
                continue
            source, kind, encoded, epoch = key
            evidence = json.loads(encoded)
            wanted = fingerprint(sorted({canonical(ref) for ref in evidence}) if kind == 'sent_copies' else evidence)
            matches = [n for k, n in record.rows.items() if k.startswith('notice:') and
                n.get('source_key') == source and n.get('check_kind') == kind and
                (n.get('evidence_fingerprint') == wanted or 'evidence_fingerprint' not in n) and
                n['id'] not in self.occurrences.values()]
            if not matches:
                continue
            new = matches[-1]['id']
            self.occurrences[key] = new
            rebound = {Fact(f.source, f.kind, new if f.occurrence == old else f.occurrence, f.detail) for f in self.detected}
            self.detected.clear()
            self.detected.update(rebound)
            if old in self.location_evidence:
                self.location_evidence[new] = self.location_evidence.pop(old)
            self.open_occurrences = {source: new if value == old else value for source, value in self.open_occurrences.items()}

    def scripted_transition(self, event, suffix, identity=None):
        for call in self.script:
            if not call['action'].endswith(suffix):
                continue
            if identity is not None and call.get('arguments', {}).get('operation_id') != identity:
                continue
            if not call.get('start_seq', -1) < event['seq'] <= call.get('end_seq', float('inf')):
                continue
            if 'time' in event and call['clock'] > event['time']:
                continue
            return True
        return False

    def result_proof(self, source, kind, sequence):
        for evidence in self.servers:
            call = next((c for c in self.script if c['call'] == evidence['call']), {})
            if not evidence.get('before_seq', float('inf')) < sequence <= call.get('end_seq', -1):
                continue
            if kind == 'sent_copies' and evidence['command'] == 'SENT' and evidence.get('source') == source:
                return True
            if kind in {'filing', 'rename'} and evidence['command'] == 'LIST':
                context = self.warning_contexts.get(source, self.lifecycle_known.get(source, {}))
                if evidence.get('account') not in {None, context.get('account')}:
                    continue
                roles = special_roles(evidence.get('roles') or {}) or {}
                if all(len(roles.get(role, [])) == 1 for role in ('sent', 'drafts', 'trash')) and not any(e['call'] == evidence['call'] and e['command'] == 'FETCH' and not e['accepted'] for e in self.servers):
                    return True
        return False

    def lifecycle(self, record):
        changed = {key for event in record.events for key in event['set']}
        rows = {key: value for key, value in record.rows.items() if key not in changed}
        for event in record.events:
            for key, value in event['set'].items():
                old = rows.get(key, self.lifecycle_known.get(key, {}))
                if key.startswith('notice:') and value and value.get('ack') and not old.get('ack'):
                    if self.scripted_transition(event, '_notice_ack', value['id']):
                        self.acknowledged.add(value['id'])
                    else:
                        self.lifecycle_errors.add(Fact(key, 'unjustified-ack'))
                        value = {**value, 'ack': False}
                if key.startswith('op:') and value and value.get('ack') and not old.get('ack'):
                    if self.scripted_transition(event, '_notice_ack', value['id']):
                        self.acknowledged.add('operation:' + value['id'])
                    else:
                        self.lifecycle_errors.add(Fact(key, 'unjustified-ack'))
                        value = {**value, 'ack': False}
                if key.startswith(('mail:filing:', 'mail:rename:')) and old and (old.get('state') == 'started' or old.get('check_open')) and value and not (value.get('state') == 'started' or value.get('check_open')):
                    kind = 'rename' if key.startswith('mail:rename:') else 'filing'
                    self.warning_contexts.setdefault(key, copy.deepcopy(old))
                    if event['action'].endswith('_notice_ack') or not self.result_proof(key, kind, event['seq']):
                        self.lifecycle_errors.add(Fact(key, 'unjustified-check-close'))
                        value = {**value, 'check_open': True}
                if key.startswith('op:') and old.get('sent_copy_check', {}).get('state') == 'open' and value and value.get('sent_copy_check', {}).get('state') != 'open':
                    if event['action'].endswith('_notice_ack') or not self.result_proof(key, 'sent_copies', event['seq']):
                        self.lifecycle_errors.add(Fact(key, 'unjustified-check-close'))
                        value = {**value, 'sent_copy_check': old['sent_copy_check']}
                if key.startswith('op:') and old.get('state') == 'reserved' and value and value.get('state') in {'failed', 'done'}:
                    expiry = value.get('reason', '').startswith('expired:') and any(c['clock'] >= old.get('expires', float('inf')) for c in self.script)
                    cancel = value.get('reason', '').startswith('cancelled:') and self.scripted_transition(event, '_operation_cancel', old['id'])
                    if not (expiry or cancel):
                        self.lifecycle_errors.add(Fact(key, 'unjustified-resolution'))
                        value = old
                if value is None and key.startswith(('op:', 'mail:filing:', 'mail:rename:', 'intent:', 'export:')) and old:
                    unresolved = old.get('state') in {'reserved', 'started', 'submitting', 'unknown', 'partial'} or old.get('check_open') or key.startswith(('intent:', 'export:'))
                    acknowledged_intent = key.startswith('intent:') and self.scripted_transition(event, '_notice_ack', old.get('id'))
                    completed_intent = key.startswith('intent:') and event['action'] == old.get('action') and self.scripted_transition(event, old.get('action', 'impossible'))
                    completed_export = key.startswith('export:') and event['action'].endswith('_file_save') and any(c['action'] in {'saved', 'testapp_file_save', 'mail_file_save'} for c in self.script)
                    if unresolved and not (acknowledged_intent or completed_intent or completed_export):
                        self.lifecycle_errors.add(Fact(key, 'unjustified-removal'))
                        value = old
                if value is None:
                    rows.pop(key, None)
                else:
                    rows[key] = value
        # Read-only synthetic fixtures may give rows directly; real decoded rows
        # always have events. Remember obligations across rollback and restore.
        if not record.events:
            rows = dict(record.rows)
        for key, old in self.lifecycle_known.items():
            if key not in rows and key.startswith('op:') and old.get('state') in {'reserved', 'submitting', 'unknown', 'partial'}:
                rows[key] = old
        self.lifecycle_known.update(rows)
        result = copy.copy(record)
        result.rows = rows
        return result

    def public_handle(self, record, fact):
        if fact.occurrence:
            return fact.occurrence
        source = fact.source
        if fact.kind == 'unchecked':
            return 'sent-check-' + fingerprint(source.removeprefix('op:'))[:32]
        if source.startswith(('op:', 'export:')):
            return 'recovery-' + source.split(':', 1)[1]
        if source.startswith(('mail:filing:', 'mail:rename:')):
            identity = record.rows.get(source, {}).get('id', source.rsplit(':', 1)[1])
            return 'check-' + fingerprint(source)[:32] if identity in self.acknowledged else identity
        if source.startswith(('mail:account:', 'legacy-intent:')):
            return 'recovery-' + fingerprint(source)[:32]
        return record.rows.get(source, {}).get('id', source)

    def background_history(self):
        if self.background:
            return
        for call in self.script:
            faults = call.get('faults', {})
            if faults.get('background') and faults.get('trace'):
                cause = faults['trace'][0]
                self.background = {'code': 'storage_error' if cause[2] == 'EIO' else 'storage_limit', 'call': call['call'], 'clock': call['clock']}
                return

    def permitted_status(self, record, call):
        # Status is checked even when every catalogue is empty. A handled raw
        # failure may still yield success; only injected causes permit errors.
        if record.locked:
            return {'restore_required'}
        allowed = {'allowed'}
        faults = call.get('faults', {})
        if faults.get('admission') == 'full':
            return {'storage_limit'}
        if faults.get('trace') or faults.get('active_exhaustion'):
            allowed.add('storage_limit')
            if any(f[2] == 'EIO' for f in faults.get('trace', [])):
                allowed.add('storage_error')
        if record.prepared or len(record.fences) > max(record.committed, default=0):
            allowed.add('journal_incomplete')
        if any(e['call'] == call.get('call') and not e['accepted'] and e['command'] in {'CONNECT', 'FETCH', 'LIST', 'SEARCH'} for e in self.servers):
            allowed.add('transport_error')
        return allowed

    def qualification(self, record):
        for call in self.script:
            if call['action'] != 'mail_account_add':
                continue
            account_id = call['arguments'].get('id')
            if account_id in self.qualification_observed:
                continue
            completed = [e['seq'] for e in record.events if e['action'] == 'mail_account_add' and e.get('outcome') == 'done' and
                'mail:account:' + str(account_id) in e['set']]
            if not completed:
                continue
            events = [e for e in self.servers if e.get('account') == account_id and e['call'] == call['call']]
            if not events:
                continue
            deliveries = [e for e in events if e['command'] == 'DATA' and e['accepted']]
            probes = [e for e in events if e['command'] == 'DELETE']
            delivery_index = next((i for i, e in enumerate(events) if e['command'] == 'DATA'), len(events))
            repair_index = next((i for i, e in enumerate(events) if i > delivery_index and e['command'] == 'APPEND'), len(events))
            searches = [e for e in events[delivery_index:repair_index] if e['command'] == 'SENT']
            policy = 'server' if searches and searches[-1]['identities'] else 'client'
            ready = bool(deliveries) and policy == 'server'
            safe, reason = self.probe_qualification(events, record, min(completed))
            self.qualification_observed[account_id] = {'ready': ready, 'sent_policy': policy,
                'safe_folder_delete': safe, 'folder_delete_reason': reason}
        result = copy.deepcopy(self.qualification_observed)
        for event in record.events:
            if event['action'] != 'mail_account_settings':
                continue
            for setting in self.script:
                args = setting.get('arguments', {})
                account = args.get('id')
                if setting['action'] == 'mail_account_settings' and account in result and 'sent_policy' in args and self.scripted_transition(event, 'mail_account_settings'):
                    result[account].update(sent_policy=args['sent_policy'], ready=True)
        return result

    def probe_qualification(self, events, record, completed_at):
        probes = [e for e in events if e['command'] == 'DELETE']
        if not probes or probes[0].get('reply') != 'delivered':
            return False, 'survival-unverified'
        probe = probes[0]
        folder = (probe.get('arguments') or [''])[0].strip('"')
        # The response code alone is insufficient: CANNOT is generic unless
        # the server explicitly says that nonempty deletion is forbidden.
        text = ' '.join(str(v) for v in probe.get('response_text', [])).upper()
        codes = re.findall(r'\[([A-Z0-9-]+)(?:[^\]]*)\]', text)
        nonempty = probe.get('response_code') == 'NO' and all(code == 'CANNOT' for code in codes) and bool(re.search(r'NON[- ]?EMPTY|NOT EMPTY|CONTAINS MESSAGES|HOLDS MAIL', text))
        if probe['accepted']:
            return False, 'probe-missing'
        operations = [v for e in record.events if e['seq'] <= completed_at for k, v in e['set'].items() if k.startswith('op:') and v]
        def outcome(action, predicate):
            matching = [v for v in operations if v.get('action') == action and predicate(v.get('payload', {}))]
            return matching[-1] if matching else {}
        initial = outcome('mail_onboarding_folder_probe', lambda p: p.get('folder') == folder and not p.get('empty'))
        if initial.get('state') != 'refused':
            return False, 'survival-unverified'
        refs = [ref for e in events if e['command'] == 'APPEND' and e['accepted'] and e.get('folder') == folder for ref in e.get('arrived', [])]
        survived = any(e['command'] == 'FETCH' and e['accepted'] and any(ref in e['identities'] for ref in refs) for e in events)
        cleanup = outcome('mail_delete', lambda p: any(i.get('reference', {}).get('folder') == folder for i in p.get('items', [])))
        if not survived or cleanup.get('state') in {None, 'reserved', 'submitting'}:
            return False, 'survival-unverified'
        expunged = any(e['command'] == 'EXPUNGE' and e['accepted'] and any(str(ref['uid']) == str(e.get('arguments', [''])[0]) and ref['folder'] == e.get('folder') for ref in refs) for e in events)
        if cleanup.get('state') != 'done' or not expunged:
            return False, 'exact-cleanup-failed'
        if not nonempty:
            return False, 'generic-cleaned'
        empty = outcome('mail_onboarding_folder_probe', lambda p: p.get('folder') == folder and p.get('empty'))
        if empty.get('state') in {None, 'reserved', 'submitting'}:
            return False, 'survival-unverified'
        if empty.get('state') != 'done' or not probes[-1]['accepted']:
            return False, 'empty-cleanup-failed'
        return True, 'qualified'

    def qualification_facts(self, reply, record, actual=False):
        if not actual:
            return {Fact('mail:account:' + account, 'qualification', detail=canonical(value)) for account, value in self.qualification(record).items()}
        data = reply.get('data', {})
        accounts = data.get('accounts', [data['account']] if 'account' in data else [])
        result = set()
        for account in accounts:
            if account.get('id') not in self.qualification(record):
                continue
            reason = account.get('folder_delete_reason', '')
            family = ('qualified' if reason.startswith('Qualified:') else
                'probe-missing' if 'did not survive' in reason else
                'exact-cleanup-failed' if 'Exact probe UID EXPUNGE cleanup failed' in reason else
                'empty-cleanup-failed' if 'Empty probe folder DELETE cleanup failed' in reason else
                'generic-cleaned' if 'Exact probe removed; empty folder retained' in reason else
                'survival-unverified' if 'could not be verified' in reason else 'unexplained')
            result.add(Fact('mail:account:' + account['id'], 'qualification', detail=canonical({
                **{field: account.get(field) for field in ('ready', 'sent_policy', 'safe_folder_delete')}, 'folder_delete_reason': family})))
        return result

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
                protected = any(target == folder or target and (evidence.get('delimiters') or {}).get(folder, '/') and target.startswith(folder + (evidence.get('delimiters') or {}).get(folder, '/')) for role in ('trash', 'drafts', 'sent', 'junk', 'archive') for folder in special_roles(roles).get(role, []))
                if kind == 'rename' and any(flag.lower() in {'\\all', '\\flagged', '\\important'} for flag in roles.get(target, [])):
                    protected = True
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
        record = self.lifecycle(record)
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

    def local_context_errors(self, record, after_sequence=0):
        return {Fact(source, kind, detail=detail) for source, kind, detail in local_errors(record, self.script, after_sequence, self.servers)}

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
