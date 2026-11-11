"""Expectations from calls, server evidence and committed local transitions only."""
from dataclasses import dataclass
from email.utils import getaddresses
from bisect import bisect_right
import copy
import hashlib
import json
import re
from .records import canonical, fingerprint, visible, restore_intervals, consistency_errors, pending_reason
from .resolutions import RESOLUTIONS, permitted
from .context import bind as bind_context, differences as context_differences, special_roles, special_delimiters, missing_flag_commands, rename_destination, MUTATIONS
from .local import errors as local_errors
from .effects import delivered, send_stages, free_plan, complete_plan, matches, exact_uid, sent_bytes_match, scan_complete


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
        self.operation_notices = {}
        self.stages_examined = set()
        self.commit_fault_points = {}
        self.obligations = {}  # validated open sources; absence never resolves one
        self.resolutions = set()
        self.filing_authority = {}
        self.commit_observations = {}
        self.repair_authority = {}
        self.source_ids = {}
        self.legacy_sources = set()

    def resolve(self, kind, source, sequence=None, validator=None, **proofs):
        if permitted(kind, proofs):
            self.resolutions.add((source, kind, sequence if sequence is not None else getattr(self, 'resolution_sequence', 0)))
            return True
        failure = Fact(source, 'unsupported-resolution', detail=kind)
        if validator:
            self.proof(validator, failure)
        else:
            self.lifecycle_errors.add(failure)
        return False

    def approved(self, operation):
        """Full effects are selected by the caller's approval, never payload.

        An onboarding probe is derived separately from CREATE/APPEND evidence.
        The row supplies only the opaque operation binding.
        """
        cache = getattr(self, '_approved_cache', {})
        identity = operation.get('id')
        if identity in cache:
            return cache[identity]
        calls = [c for c in self.script if c.get('arguments', {}).get('operation_id') == identity
                 and isinstance(c.get('arguments', {}).get('description'), dict)]
        if not calls:
            return None
        args = calls[0]['arguments']
        description = args['description']
        result = {**description, **description.get('untrusted_content', {})}
        cache[identity] = result
        return result

    def bound(self, event):
        cache = getattr(self, '_binding_cache', {})
        marker = id(event), len(self.script), len(self.servers)
        if marker not in cache:
            cache[marker] = bind_context(event, self.script)
        return cache[marker]

    def onboarding_call(self, key):
        """Bind an opaque probe id to its creation inside the account-add call.

        The call authorizes only that account's self-probe. Message identities
        and SMTP transaction membership are checked separately at each effect.
        """
        record = getattr(self, '_effect_record', None)
        if record is None:
            return None
        birth = next((e for e in record.events if isinstance(e['set'].get(key), dict)), None)
        if birth is None:
            return None
        row = birth['set'][key]
        account = row.get('payload', {}).get('composition', {}).get('mail', {}).get('account')
        if row.get('repair_of'):
            return self.onboarding_call('op:' + row['repair_of']) if row.get('action') == 'mail_operation_repair' else None
        if row.get('action') != 'mail_send':
            return None
        return next((c for c in self.calls_at(birth['seq']) if c['action'] == 'mail_account_add'
                     and c['arguments'].get('id') == account), None)

    def operation_events(self, key, sequence):
        """Join delivery, local repair and explicitly recorded fixture effects."""
        operation_id = key.removeprefix('op:')
        mid = '<' + operation_id.replace(':', '.') + '@mail.aresos.invalid>'
        events = []
        for event in self.servers:
            if event.get('before_seq', -1) >= sequence:
                continue
            source, row = self.bound(event)
            if event['command'] == 'RCPT' and event.get('smtp_transaction') is not None:
                # RCPT precedes DATA and has no Message-ID of its own. Join it
                # only to DATA in that exact recorded SMTP transaction.
                data = next((e for e in self.servers if e['command'] == 'DATA' and
                             e['call'] == event['call'] and e.get('account') == event.get('account') and
                             e.get('smtp_transaction') == event['smtp_transaction']), None)
                if data and self.bound(data)[0] == key and any(i.get('message_id') == mid for i in data.get('identities', [])):
                    events.append(event)
                    continue
            if source == key or event.get('source') == key:
                events.append(event)
                continue
            seed = (event.get('fixture_seed') and
                    event.get('before_seq', -1) <= getattr(self, 'seed_sequence', -2) and
                    event['call'] in getattr(self, 'seed_calls', set()) and
                    any(key in e['set'] for e in getattr(self, 'seed_events', [])))
            repair = row and row.get('repair_of') == operation_id
            # Paged reads can log hundreds of unrelated FETCHes. Only a seed
            # or a parent repair can need this additional scripted-call join.
            if not (seed or repair) or not any(ref.get('message_id') == mid for ref in event.get('identities', [])):
                continue
            call = next((c for c in self.script if c['call'] == event['call']), {})
            if call.get('arguments', {}).get('operation_id') == operation_id and (
                    seed and call.get('action') in {'mail_send', 'mail_unsubscribe'} or
                    repair and call.get('action') == 'mail_operation_repair'):
                events.append(event)
            elif repair:
                onboarding = self.onboarding_call(key)
                if onboarding and event['call'] == onboarding['call'] and event.get('account') == onboarding['arguments']['id']:
                    events.append(event)
        return events

    def proof(self, validator, fact):
        self.lifecycle_errors.add(fact)
        if getattr(self, '_trace_validators', False):
            self._validator_proofs.setdefault(validator, set()).add(fact)

    def proofs(self, validator, facts):
        self.lifecycle_errors.update(facts)
        if getattr(self, '_trace_validators', False):
            self._validator_proofs.setdefault(validator, set()).update(facts)

    def calls_at(self, sequence):
        # One replay may ask about the same commit in several validators.
        # The cache is discarded before each lifecycle reconstruction.
        cache = getattr(self, '_calls_cache', None)
        if cache is None:
            return [c for c in self.script if c.get('start_seq', -1) < sequence <= c.get('end_seq', -1)]
        if sequence not in cache:
            cache[sequence] = [c for c in self.script if c.get('start_seq', -1) < sequence <= c.get('end_seq', -1)]
        return cache[sequence]

    def sent_result_commit(self, event, source):
        onboarding = self.onboarding_call(source)
        internal_repair = onboarding and event['action'] == 'mail_operation_repair' and onboarding in self.calls_at(event['seq'])
        return (bool(internal_repair) or event['action'] == 'mail_sent_copy_check' or
                event.get('untrusted_content', {}).get('stage') in {'sent_copy', 'message_id'} or
                event['action'] == 'mail_operation_repair' and any(
                    c['action'] == 'mail_operation_repair' and c['arguments'].get('operation_id') == source.removeprefix('op:') and
                    c['arguments'].get('stage') == 'sent_copy' for c in self.calls_at(event['seq'])))

    @staticmethod
    def testapp_account(reference):
        parts = reference.get('scope', '').split('/')
        return parts[1] if len(parts) == 3 and parts[0] == 'testapp' and parts[2] == 'items' else None

    def probe_payload_claims(self, key, row):
        if row.get('action') != 'mail_onboarding_folder_probe':
            return
        for command in self.servers:
            if command['command'] != 'DELETE' or self.bound(command)[0] != key or 'mailbox_inventory' not in command:
                continue
            call = next((c for c in self.script if c['call'] == command['call']), {})
            if call.get('action') != 'mail_account_add':
                continue
            payload, inventory = row.get('payload', {}), command['mailbox_inventory']
            expected = {'account': call['arguments'].get('id'), 'folder': command['arguments'][0].strip('"'),
                        'empty': not inventory['messages']}
            for field, wanted in expected.items():
                actual = bool(payload.get(field)) if field == 'empty' else payload.get(field)
                if actual != wanted:
                    self.proof('payload_claims', Fact(key, 'unapproved-probe-payload', detail=field))
            if payload.get('empty_state') is not None:
                wanted = {'account': expected['account'], 'folder': expected['folder'],
                          'uidvalidity': inventory['uidvalidity'], 'uids': [ref['uid'] for ref in inventory['messages']]}
                if payload['empty_state'] != wanted:
                    self.proof('payload_claims', Fact(key, 'unapproved-probe-payload', detail='empty_state'))

    def payload_claims(self, key, row):
        cache = getattr(self, '_payload_cache', {})
        signature = key, canonical({field: row.get(field) for field in ('id', 'action', 'payload', 'approval', 'input_hash', 'expires')})
        if signature in cache:
            self.proofs('payload_claims', cache[signature])
            return
        before = set(self.lifecycle_errors)
        self.probe_payload_claims(key, row)
        approved = self.approved(row)
        if approved is None:
            cache[signature] = self.lifecycle_errors - before
            return
        payload = row.get('payload', {})
        mail = payload.get('composition', {}).get('mail', {})
        fields = ('account', 'items', 'mode', 'folder', 'reference', 'target', 'method',
                  'to', 'cc', 'bcc', 'answered_reference', 'from', 'attachments', 'stage',
                  'text', 'html', 'subject', 'format', 'signature', 'in_reply_to', 'references', 'generated_parts')
        source = {**payload, **mail}
        source = {**source, 'account': source.get('account') or source.get('reference', {}).get('account') or
                  next((i.get('reference', {}).get('account') or self.testapp_account(i.get('reference', {}))
                        for i in source.get('items', [])), None)}
        for field in fields:
            if field in approved and visible(source.get(field)) != approved[field]:
                self.proof('payload_claims', Fact(key, 'unapproved-payload', detail=field))
        calls = [c for c in self.script if c.get('arguments', {}).get('operation_id') == row.get('id') and
                 isinstance(c['arguments'].get('description'), dict)]
        if calls and row.get('approval') != calls[0]['arguments']:
            self.proof('payload_claims', Fact(key, 'unapproved-recorded-approval'))
        if row.get('input_hash') and calls and row['input_hash'] != fingerprint(calls[0]['arguments']):
            self.proof('payload_claims', Fact(key, 'unapproved-input-hash'))
        if 'expires_at' in approved and row.get('expires') != approved['expires_at']:
            self.proof('payload_claims', Fact(key, 'unapproved-expiry'))
        composition = payload.get('composition', {})
        for field, name in (('id', 'composition_id'), ('hash', 'composition_hash')):
            if name in approved and composition.get(field) != approved[name]:
                self.proof('payload_claims', Fact(key, 'unapproved-composition', detail=field))
        cache[signature] = self.lifecycle_errors - before

    def filing_claims(self, key, row, event):
        if row is None:
            self.proof('filing_claims', Fact(key, 'missing-check-result', detail=str(event['seq'])))
            return None
        calls = self.calls_at(event['seq'])
        final_write = bool(calls) and all(getattr(self, '_last_source_writes', {}).get((call['call'], key), event['seq']) == event['seq'] for call in calls)
        result_commit = event['action'] == 'mail_filing_check' or (
            event['action'] in {'mail_move', 'mail_copy', 'mail_folder_rename'} and final_write and
            not any(call.get('faults', {}).get('trace') for call in calls))
        if result_commit and (row.get('state') == 'started' or row.get('check_open')):
            kind = 'rename' if key.startswith('mail:rename:') else 'filing'
            if self.result_proof(key, kind, event['seq']):
                self.proof('filing_claims', Fact(key, 'uncommitted-check-result', detail=str(event['seq'])))
        calls = [c for c in self.script if c.get('start_seq', -1) < event['seq'] <= c.get('end_seq', -1)
                 and c['action'] in {'mail_move', 'mail_copy', 'mail_folder_rename'}]
        if calls:
            self.filing_authority.setdefault(key, calls[0])
        call = self.filing_authority.get(key)
        if not call:
            return row
        args = call['arguments']
        wanted = {'account': args.get('account') or next((r.get('account') for r in args.get('references', [])), None),
                  'target': args.get('name') if call['action'] == 'mail_folder_rename' else args.get('target')}
        if call['action'] == 'mail_folder_rename':
            wanted['source'] = args.get('folder')
            evidence = next((e for e in self.servers if e['call'] == call['call'] and e['command'] in {'LIST', 'RENAME'} and
                             e.get('account') == wanted['account']), {})
            wanted['target'] = rename_destination(args, evidence)
            mutations = [e for e in self.servers if e['call'] == call['call'] and e['command'] == 'RENAME'
                         and e.get('account') == wanted['account'] and e.get('folder') == wanted['source']]
            if mutations:
                wanted['message_count'] = len(mutations[0].get('identities', []))
        else:
            wanted.update(sources=args.get('references', []), verb=call['action'].removeprefix('mail_'))
        for field, expected in wanted.items():
            if row.get(field) != expected:
                self.proof('filing_claims', Fact(key, 'unapproved-filing-context', detail=canonical({'field': field, 'expected': expected, 'actual': row.get(field)})))
        if call['action'] != 'mail_folder_rename' and row.get('records') is not None:
            sources = [item.get('source') for item in row['records']]
            if sources != args.get('references', []):
                self.proof('filing_claims', Fact(key, 'unapproved-filing-records', detail=canonical(sources)))
        for item in row.get('records', []):
            source = item.get('source')
            evidence = [ref for e in self.servers if e['call'] == call['call'] and e.get('before_seq', -1) <= event['seq']
                        for ref in e.get('identities', []) if {k: v for k, v in ref.items() if k != 'sha256'} == source and ref.get('sha256')]
            if evidence and item.get('sha256') != evidence[0]['sha256']:
                self.proof('filing_claims', Fact(key, 'unverified-source-hash', detail=canonical(source)))
            effects = [e for e in self.servers if e['command'] in {'MOVE', 'COPY'} and self.bound(e)[0] == key and
                       e.get('before_seq', -1) < event['seq'] and e.get('folder') == source['folder'] and
                       str(e.get('arguments', [''])[0]) == str(source['uid'])]
            if effects and item.get('destination') != effects[-1].get('destination'):
                self.proof('filing_claims', Fact(key, 'unverified-destination', detail=canonical(source)))
        return {**row, **wanted}

    @staticmethod
    def unfinished(key, row):
        return (row.get('state') in {'reserved', 'started', 'submitting', 'unknown', 'partial'} or
                row.get('check_open') or row.get('sent_copy_check', {}).get('state') == 'open' or
                key.startswith(('intent:', 'export:')) or
                key.startswith('mail:account:') and not row.get('onboarded', row.get('ready', False)))

    def obligation_kinds(self, key, row):
        result = set()
        if key.startswith('op:'):
            state = row.get('state')
            if state in {'reserved', 'submitting', 'unknown', 'partial'}:
                result.add('work')
            if state in {'submitting', 'unknown', 'partial'}:
                result.add('operation')
            if state == 'reserved':
                result.add('settle_hold' if row.get('repair_of') else 'cancel_hold')
            elif row.get('repair_of') and state in {'submitting', 'unknown'}:
                result.add('settle_hold')
            if row.get('sent_copy_check', {}).get('state') == 'open':
                result.add('unchecked')
            if key in self.operation_notices and 'operation:' + row['id'] not in self.acknowledged:
                result.add('operation_notice')
        elif key.startswith(('mail:filing:', 'mail:rename:')) and (row.get('state') == 'started' or row.get('check_open')):
            result.add('check')
        elif key.startswith('mail:account:') and not row.get('onboarded', row.get('ready', False)):
            result.add('account')
        elif key.startswith('intent:'):
            result.add('intent')
        elif key.startswith('export:'):
            result.update({'export', 'export_hold'})
        return result

    def retain_obligations(self, record, rows):
        """Presence, rollback and changed flags have no discharge authority."""
        latest = {key: event['seq'] for event in record.events for key in event['set']}
        updated = {}
        for key in sorted(rows.keys() | self.obligations.keys()):
            row = rows.get(key, {})
            if not isinstance(row, dict):
                continue
            kinds = self.obligation_kinds(key, row)
            for kind, (old, since) in sorted(self.obligations.get(key, {}).items(), key=lambda item: (item[0] == 'operation', item[0])):
                if kind in kinds:
                    continue
                ended = any(source == key and sequence >= since and kind in RESOLUTIONS[resolution].ends
                            for source, resolution, sequence in self.resolutions)
                if not ended:
                    self.lifecycle_errors.add(Fact(key, 'narrowed-obligation', detail=kind))
                    # Preserve only the obligation's fields; other independently
                    # validated effects can still advance (e.g. a clean check).
                    fields = {'account': ('onboarded', 'ready'), 'check': ('state', 'check_open'),
                              'unchecked': ('sent_copy_check',), 'operation_notice': ('notice',),
                              'work': ('state', 'reason'), 'operation': ('state', 'reason'),
                              'cancel_hold': ('state',), 'settle_hold': ('state', 'repair_of')}.get(kind)
                    row = {**old, **row} if fields else old
                    if fields:
                        row = {**row, **{field: old[field] for field in fields if field in old}}
                    rows[key] = row
                    kinds.add(kind)
            if kinds:
                previous = self.obligations.get(key, {})
                saved_row = copy.deepcopy(row)
                updated[key] = {kind: (saved_row, previous[kind][1] if kind in previous else latest.get(key, 0)) for kind in sorted(kinds)}
        self.obligations = updated

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
        self._evidence_index = None
        self._filing_mutations_cache = None
        if isinstance(event.get('committed_before'), dict) and isinstance(event.get('before_seq'), int):
            self.commit_observations.setdefault(event['before_seq'], event['committed_before'])
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
            sequence = max(record.committed, default=0)
            if checked.get('fingerprint') == expected_fingerprint and not current.get('check_open') and current.get('state') != 'started' and self.resolve(
                    'check_result', source, sequence=sequence, server_result=self.result_proof(source, kind, sequence), commit_order=bool(sequence)):
                self.open_checks.discard(source)
        if isinstance(evidence, dict) and 'locations' in evidence:
            self.location_evidence[self.occurrences[key]] = (source, copy.deepcopy(evidence['locations']))
        return Fact(source, kind, self.occurrences[key], canonical(detail))

    def generic_evidence(self, record):
        """D3's durable generic occurrences are bound to interrupted episodes.

        An anchored check-open is necessary, and a later opening (or the
        reserved-space fallback result) proves that its result was missing.
        A naked notice flag never supplies that proof.
        """
        from .projection import check_episodes
        episodes, current = check_episodes(record)
        facts = set()
        valid = {}
        for (source, epoch), episode in episodes.items():
            end = episode['end']
            end_row = record.owner_versions.get(end, {}).get(source) or {}
            fallback = end_row.get('sent_copy_check', {}).get('unrecorded') is True
            if episode['ending'] != 'replaced' and not fallback:
                continue
            identity = ('sent-' + fingerprint(source[3:])[:32] if source.startswith('op:')
                        else source.rsplit(':', 1)[-1]) + '-' + format(epoch, '032x')
            valid[source, epoch] = identity
            if identity not in self.acknowledged:
                kind = 'sent_copies' if source.startswith('op:') else 'rename' if source.startswith('mail:rename:') else 'filing'
                facts.add(Fact(source, 'evidence-unrecorded', identity, kind))
        self.generic_episodes = valid
        self.current_episodes = current
        self.check_episodes = episodes
        return facts

    def expected(self, record, live=False, app=None):
        facts = set()
        record = self.lifecycle(record)
        self.bind_occurrences(record)
        self.background_history(record)
        if self.background and 'background-storage' not in self.acknowledged and (app is None or app == 'mail'):
            facts.add(Fact('background:storage', 'background-storage', 'background-storage', self.background['code']))
        previous = {}
        calls = {call['call']: call for call in self.script}
        last_mutations = self.last_filing_mutations()
        for event in record.events:
            for source, value in event['set'].items():
                if not isinstance(value, dict):
                    continue
                kinds = {kind for known, kind in self.warning_started if known == source}
                kinds.update(value.get('warning_checks', {}))
                if value.get('sent_copy_check'):
                    kinds.add('sent_copies')
                for kind in kinds:
                    evidence_index, evidence = self.read_evidence(source, kind, event['seq'], calls, last_mutations)
                    stage = event.get('untrusted_content', {})
                    result_commit = event['action'] == 'mail_filing_check' or (
                        kind == 'sent_copies' and self.sent_result_commit(event, source)) or (
                        kind in {'filing', 'rename'} and event['action'] in {'mail_move', 'mail_copy', 'mail_folder_rename'})
                    clean = result_commit and self.clean_evidence(source, kind, evidence)
                    claimed = value.get('warning_checks', {}).get(kind, {}).get('warning')
                    prior = previous.get(source, {})
                    new_clean_claim = claimed is False and prior.get('warning_checks', {}).get(kind, {}).get('warning') is not False
                    if kind == 'sent_copies' and value.get('sent_copy_check', {}).get('clean') and not prior.get('sent_copy_check', {}).get('clean'):
                        new_clean_claim = True
                    runtime = event['seq'] > getattr(self, 'seed_sequence', 0)
                    if runtime and new_clean_claim and not clean:
                        self.invalid_clean_results.add(Fact(source, 'unverified-clean', detail=kind))
                    if runtime and claimed is True and clean:
                        self.lifecycle_errors.add(Fact(source, 'false-warning-result', detail=kind + ':' + str(event['seq'])))
                    # Raw evidence selects clean epochs; a production boolean
                    # is only a claim compared above. One read/result pair can
                    # advance the epoch only once, even through later stages.
                    marker = source, kind, 'raw', evidence_index
                    if not clean or event['seq'] <= self.warning_started.get((source, kind), float('inf')) or marker in self.examined_clean:
                        continue
                    if self.resolve('clean_check', source, sequence=event['seq'], clean_server_result=True, commit_order=evidence is not None):
                        self.examined_clean.add(marker)
                        self.last_clean[source, kind] = event['seq']
                        self.epochs[source, kind] = self.epochs.get((source, kind), 0) + 1
                        if kind in {'filing', 'rename'}:
                            self.open_checks.discard(source)
                previous[source] = value
        for key, row in record.rows.items():
            if key.startswith('op:'):
                notice = self.operation_notices.get(key)
                if notice and 'operation:' + row['id'] not in self.acknowledged and (app is None or row['app'] == app):
                    kind = 'expired' if notice.get('reason', '').startswith('expired:') else 'cancelled'
                    facts.add(Fact(key, 'operation-notice', row['id'], kind))
                if app is None or row['app'] == app:
                    if row['state'] in {'reserved', 'submitting', 'partial', 'unknown'} or (
                            key in self.operation_notices and 'operation:' + row['id'] not in self.acknowledged):
                        facts.add(Fact(key, 'pending', detail=canonical({'state': row['state'], 'reason': pending_reason(row.get('reason'))})))
                if (row['state'] in {'submitting', 'unknown', 'partial'} or row['state'] == 'reserved' and key in self.legacy_sources) and (app is None or row['app'] == app):
                    facts.add(Fact(key, 'recovery'))
                check = row.get('sent_copy_check', {})
                if row['app'] == 'mail' and (app is None or app == 'mail'):
                    failed_recheck = bool(check) and (bool(record.prepared) or len(record.fences) > max(record.committed, default=0) or live and self.script and bool(self.script[-1].get('faults', {}).get('trace')))
                    if check.get('state') == 'open':
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
        # Independently decoded owner facts survive a rolled-back or unreadable
        # SQLite view. They add obligations; ending one still needs the scripted
        # acknowledgement or result proof below.
        for source, row in record.owner_rows.items():
            if not isinstance(row, dict):
                continue
            if source.startswith('notice:') and row.get('ack'):
                seq = record.owner_sequences[source]
                fence = next((f for f in record.fences if f['seq'] == seq), None)
                if fence is None:
                    self.lifecycle_errors.add(Fact(source, 'missing-owner-fence'))
                    continue
                proof = {'seq': seq, 'time': fence['time']}
                if self.scripted_transition(proof, '_notice_ack', row['id']):
                    self.acknowledged.add(row['id'])
            if source.startswith('op:') and row.get('sent_copy_check', {}).get('state') == 'open' and row.get('app') == 'mail':
                facts.add(Fact(source, 'unchecked'))
            if source not in record.rows and source.startswith(('intent:', 'export:', 'mail:filing:', 'mail:rename:', 'mail:account:')):
                opened = (source.startswith(('intent:', 'export:')) or row.get('state') == 'started' or
                          row.get('check_open') or source.startswith('mail:account:') and not row.get('onboarded', row.get('ready', False)))
                if opened and (app is None or row.get('app', 'mail') == app):
                    facts.add(Fact(source, 'recovery'))
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
        for index, event in enumerate(self.servers[self.processed_server:], self.processed_server):
            if event['command'] != 'LIST':
                continue
            roles = event.get('roles') or {}
            for source, context in record.rows.items():
                if not source.startswith(('mail:filing:', 'mail:rename:')):
                    continue
                opened_here = source in event.get('check_sources', []) and any(
                    check['action'] == 'mail_filing_check_open' and source in check['set'] and
                    check['seq'] <= event.get('before_seq', -1) and
                    any(c['call'] == event['call'] for c in self.calls_at(check['seq'])) for check in record.events)
                if context.get('state') != 'started' and not context.get('check_open') and not opened_here:
                    continue
                mutation_index = last_mutations.get((event['call'], source))
                if source not in event.get('check_sources', []) and (mutation_index is None or index <= mutation_index):
                    continue
                target = context.get('target')
                if not isinstance(target, str) or source.startswith('mail:rename:') and target not in roles:
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
                refused = (bool(call.get('faults', {}).get('trace')) or call.get('faults', {}).get('admission') == 'full' or
                           bool(record.prepared) or len(record.fences) > max(record.committed, default=0))
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
                        if not any(f.source == source and f.kind == 'sent_copies' and
                                   f.occurrence not in self.acknowledged for f in self.detected):
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
                source, context = self.bound(mutation)
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
        for key, row in record.rows.items():
            check = row.get('sent_copy_check', {}) if isinstance(row, dict) else {}
            trace = self.script[-1].get('faults', {}).get('trace', []) if self.script else []
            failed_recheck = bool(check) and (bool(record.prepared) or len(record.fences) > max(record.committed, default=0) or live and bool(trace) or any(point[1] == 'sqlite.main.read' for point in trace))
            if (key.startswith('op:') and row.get('app') == 'mail' and app in (None, 'mail') and failed_recheck and
                    not any(f.source == key and f.kind == 'sent_copies' and f.occurrence not in self.acknowledged for f in self.detected)):
                facts.add(Fact(key, 'unchecked'))
        generic = self.generic_evidence(record)
        if app is None or app == 'mail':
            facts.update(generic)
        for warning in self.detected:
            if warning.occurrence in self.acknowledged or app not in (None, 'mail'):
                continue
            # A warning seen during a check whose result could not be committed
            # is disclosed by its open-check warning and then its durable D3
            # occurrence. Already committed specific evidence is never replaced.
            covered = False
            if warning.occurrence.startswith('uncommitted:'):
                start = self.warning_started.get((warning.source, warning.kind), 0)
                covered = any(source == warning.source and epoch <= start and
                              (episode['end'] is None or start <= episode['end'])
                              for (source, epoch), episode in self.check_episodes.items())
            if not covered:
                facts.add(warning)
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
                    mutations = [e for e in self.servers if e['command'] == 'RENAME' and self.bound(e)[0] == fact.source]
                    meta['message_count'] = len(mutations[0]['identities']) if mutations else context['message_count']
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
                row = record.rows.get(fact.source, record.owner_rows.get(fact.source, self.warning_contexts.get(fact.source, {})))
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
            notice_sources = {**record.owner_rows, **record.rows}
            matches = [n for k, n in notice_sources.items() if k.startswith('notice:') and
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
            if not call.get('start_seq', -1) < event['seq'] <= call.get('end_seq', -1):
                continue
            if 'time' in event and call['clock'] > event['time']:
                continue
            return True
        return False

    def restore_proof(self, event):
        return any(c['action'] == 'control_restore_confirm' and c.get('restore_precondition') is True and
                   c.get('start_seq', -1) < event['seq'] <= c.get('end_seq', -1) for c in self.script)

    def prepared_restore_sequences(self, record):
        # A prepared restore can explain the old backup's holes without
        # granting any completion, acknowledgement or generation transition.
        # The boundary comes from the recorded pre-call head, not its payload.
        explained = set()
        for event in record.prepared:
            if event['action'] != 'control_restore_confirm' or not self.restore_proof(event):
                continue
            for call in self.calls_at(event['seq']):
                head = call.get('restore_working_head')
                start = call.get('start_seq')
                if (call['action'] == 'control_restore_confirm' and call.get('restore_precondition') is True and
                        isinstance(head, int) and isinstance(start, int) and
                        event.get('restore_range') == [head + 1, event['seq'] - 1]):
                    explained.update(seq for seq in record.committed if head < seq <= start)
        return explained

    def result_proof(self, source, kind, sequence):
        _, evidence = self.read_evidence(source, kind, sequence)
        if evidence is None:
            return False
        if kind == 'sent_copies':
            return True
        context = self.warning_contexts.get(source, self.lifecycle_known.get(source, {}))
        if kind == 'rename' and context.get('target') not in (evidence.get('roles') or {}):
            return False
        if kind == 'filing' and context.get('target') not in (evidence.get('roles') or {}):
            # Destination loss is a warning-bearing result, never a clean
            # resolution. The occurrence must survive in the committed prefix.
            rows = {}
            for event in getattr(getattr(self, '_effect_record', None), 'events', []):
                if event['seq'] <= sequence:
                    rows.update(event['set'])
            result = rows.get(source) or {}
            check = result.get('warning_checks', {}).get('filing', {})
            notice = rows.get('notice:' + str(check.get('occurrence_id'))) or {}
            if not (result.get('state') == 'partial' and check.get('warning') and
                    notice.get('source_key') == source and notice.get('check_kind') == 'filing' and
                    notice.get('evidence_fingerprint') == check.get('fingerprint')):
                return False
        mutations = [e for e in self.servers if e['command'] in {'MOVE', 'COPY'} and self.bound(e)[0] == source]
        if kind == 'filing' and (source in evidence.get('check_sources', []) or any(not e.get('copyuid_delivered') for e in mutations)):
            scan = self.scan_result(source, evidence)
            if scan is None or not delivered(scan) or not scan_complete(self.servers, scan) or not scan.get('before_seq', float('inf')) < sequence:
                return False
        roles = special_roles(evidence.get('roles') or {}) or {}
        return all(len(roles.get(role, [])) == 1 for role in ('sent', 'drafts', 'trash')) and not any(
            e['call'] == evidence['call'] and e['command'] == 'FETCH' and not e['accepted'] for e in self.servers)

    def scan_result(self, source, listing):
        start = next((index for index, event in enumerate(self.servers) if event is listing), -1)
        for index in range(len(self.servers) - 1, start, -1):
            event = self.servers[index]
            if event['command'] != 'SCAN_RESULT' or event['call'] != listing['call'] or event.get('account') != listing.get('account'):
                continue
            if source in event.get('check_sources', []):
                return event
            if not event.get('check_sources') and any(self.bound(m)[0] == source and m['call'] == event['call'] and
                    m['command'] in {'MOVE', 'COPY'} for m in self.servers[:event.get('scan_start', index)]):
                return event
        return None

    def transition(self, record, event, key, old, row):
        """Total state machine: every edge that changes work has a proof gate."""
        before, after = old.get('state'), row.get('state')
        if before == after:
            return row
        seed = getattr(self, 'seed_sequence', min((c['start_seq'] for c in self.script if 'start_seq' in c), default=0))
        if event['seq'] <= seed or not old and not self.script:
            return row
        calls = self.calls_at(event['seq'])
        own = [c for c in calls if c.get('arguments', {}).get('operation_id') == row.get('id') or
               c['action'] == 'mail_account_add' or c.get('call') == self.repair_authority.get(key, {}).get('call')]
        ordered = bool(calls)
        commands = [e for e in self.servers if e.get('before_seq', float('inf')) < event['seq'] and
                    self.bound(e)[0] == key and e['command'] in MUTATIONS]
        fault = any(c.get('faults', {}).get('trace') for c in calls)
        negative = any(not e['accepted'] or e['reply'] != 'delivered' for e in commands)
        identity = row.get('id')
        if after == 'reserved' and before is None:
            proof = bool([c for c in calls if '_prepare_' in c['action'] or c['action'] == 'mail_account_add' or c.get('call') == self.repair_authority.get(key, {}).get('call')])
            # Minimal recorded unit fixtures can omit call intervals. No later
            # transition gets this bootstrap allowance.
            proof |= not self.script
            kind, proofs = 'submission', dict(scripted_approval=proof, commit_order=ordered or not self.script)
        elif before == 'reserved' and after == 'submitting':
            kind, proofs = 'submission', dict(scripted_approval=bool(own), commit_order=ordered)
        elif event['action'] == 'control_restore_confirm' and before == 'reserved' and after == 'failed':
            kind, proofs = 'restore_invalidation', dict(scripted_confirmation=self.restore_proof(event),
                prior_reserved=True, no_effect=not commands, commit_order=ordered)
        elif before == 'reserved' and after == 'failed' and any(c['clock'] >= old.get('expires', float('inf')) for c in calls):
            kind, proofs = 'expiry', dict(scripted_clock=any(c['clock'] >= old.get('expires', float('inf')) for c in calls), reserved=True, commit_order=ordered)
        elif before == 'reserved' and after == 'failed' and self.scripted_transition(event, '_operation_cancel', identity):
            kind, proofs = 'cancellation', dict(scripted_identity=self.scripted_transition(event, '_operation_cancel', identity), reserved=True, commit_order=ordered)
        elif event['action'] == 'control_restore_confirm' and after == 'unknown':
            kind, proofs = 'restore', dict(scripted_confirmation=self.scripted_transition(event, 'control_restore_confirm'),
                rollback_interval=self.restore_proof(event) and any(f['seq'] < event['seq'] and any(op.get('id') == identity for op in f.get('operations', [])) for f in record.fences), commit_order=ordered)
        elif after == 'done':
            kind, proofs = 'completion', dict(scripted_approval=bool(own) or self.resolution_proof(record, event, key, row),
                required_effects=self.resolution_proof(record, event, key, row), commit_order=ordered)
        elif after == 'failed' and before == 'unknown' and row.get('repair_of'):
            parent = row['repair_of']
            evidence = [e for e in self.servers if e['command'] == 'SENT' and e.get('source') == 'op:' + parent and
                        e['accepted'] and e['reply'] == 'delivered' and not e['identities'] and e.get('before_seq', float('inf')) < event['seq']]
            kind, proofs = 'settlement', dict(scripted_identity=self.scripted_transition(event, '_operation_repair', parent),
                read_only_evidence=bool(evidence), commit_order=ordered)
        elif after in {'failed', 'refused'}:
            started_here = any(c.get('start_seq', -1) < prior['seq'] < event['seq'] and
                               (prior['set'].get(key) or {}).get('state') == 'submitting'
                               for c in own for prior in record.events)
            no_effect = not any(e['accepted'] or e['reply'] != 'delivered' for e in commands)
            kind, proofs = 'failure', dict(fault_or_negative_reply=bool(
                before in {None, 'reserved', 'submitting'} and started_here and no_effect and (fault or negative)), commit_order=ordered)
        elif after in {'unknown', 'partial'} and before in {None, 'reserved', 'submitting', 'unknown', 'partial', 'done'}:
            kind, proofs = 'uncertainty', dict(attempt_or_fault=bool(commands or fault or negative or self.scripted_transition(event, '_notice_ack', identity)), commit_order=ordered)
        else:
            kind, proofs = 'state:' + str(before) + '->' + str(after), {}
        if not self.resolve(kind, key, validator='transition', **proofs):
            self.proof('transition', Fact(key, 'unjustified-resolution'))
            return {**row, 'state': before or 'unknown', 'reason': old.get('reason', '')}
        if kind in {'expiry', 'cancellation'}:
            expected_reason = 'expired: nothing submitted' if kind == 'expiry' else 'cancelled: nothing submitted'
            if row.get('reason') != expected_reason:
                self.proof('transition', Fact(key, 'unjustified-resolution-reason', detail=kind))
                row = {**row, 'reason': expected_reason}
            self.operation_notices.setdefault(key, copy.deepcopy(row))
        return row

    def lifecycle(self, record):
        self._completion_cache = {}
        self._approved_cache = {}
        self._binding_cache = {}
        sequences = sorted({event['seq'] for event in record.events})
        self._calls_cache = {sequence: [] for sequence in sequences}
        for call in self.script:
            start = bisect_right(sequences, call.get('start_seq', -1))
            end = bisect_right(sequences, call.get('end_seq', -1))
            for sequence in sequences[start:end]:
                self._calls_cache[sequence].append(call)
        self._payload_cache = {}
        self._last_source_writes = {}
        for event in record.events:
            for call in self.calls_at(event['seq']):
                for source in event['set']:
                    self._last_source_writes[call['call'], source] = event['seq']
        self._evidence_index = {}
        self._filing_mutations_cache = None
        for index, server in enumerate(self.servers):
            if server['command'] in {'SENT', 'LIST'}:
                group = server.get('source') if server['command'] == 'SENT' else server.get('account')
                self._evidence_index.setdefault((server['command'], group), []).append((index, server))
        self._effect_record = record
        self.lifecycle_errors.update(Fact(*error[:2], detail=error[2]) for error in consistency_errors(record, self.prepared_restore_sequences(record)))
        legacy_fields = {(key, field) for event in getattr(self, 'seed_events', record.events)
                         if event['seq'] <= getattr(self, 'seed_sequence', 0)
                         for key, value in event['set'].items()
                         if key.startswith('op:') and isinstance(value, dict) and not value.get('context_version')
                         for field in ('action', 'app') if field not in value}
        # Later malformed claims must be reported even if an earlier resolution
        # examines that future record before the ordered reconstruction reaches it.
        for event in record.events:
            for key, value in event['set'].items():
                if key.startswith('op:') and isinstance(value, dict) and value.get('id') != key[3:]:
                    self.lifecycle_errors.add(Fact(key, 'operation-identity', detail=str(event['seq'])))
                if key.startswith('op:') and isinstance(value, dict) and event['seq'] > getattr(self, 'seed_sequence', 0) and self.calls_at(event['seq']) and not any(
                        c['action'] == 'fixture_input' for c in self.calls_at(event['seq'])):
                    for field, kind in (('action', 'unjustified-operation-action'), ('app', 'unjustified-app-scope')):
                        if field not in value and (key, field) not in legacy_fields:
                            self.lifecycle_errors.add(Fact(key, kind, detail=str(event['seq'])))
        prefix = {}
        observed = sorted(self.commit_observations.items())
        rollback = [(start, end) for start, end, seq in restore_intervals(record.events)
                    if self.restore_proof(next(e for e in record.events if e['seq'] == seq))]
        prepared_rollback = self.prepared_restore_sequences(record)
        present = {event['seq'] for event in record.events}
        cursor = 0
        for sequence, snapshot in observed:
            while cursor < len(record.events) and record.events[cursor]['seq'] <= sequence:
                for key, value in record.events[cursor]['set'].items():
                    if value is None:
                        prefix.pop(key, None)
                    else:
                        prefix[key] = value
                cursor += 1
            for key in prefix.keys() | snapshot.keys():
                if prefix.get(key) != snapshot.get(key):
                    if sequence not in present and (sequence in prepared_rollback or any(start <= sequence <= end for start, end in rollback)):
                        continue
                    self.lifecycle_errors.add(Fact(key, 'changed-observed-commit', detail=canonical({
                        'sequence': sequence, 'expected': snapshot.get(key), 'actual': prefix.get(key)})))
        first = {}
        for event in sorted([*getattr(self, 'seed_events', []), *record.events], key=lambda e: e['seq']):
            for key, value in event['set'].items():
                if value is not None:
                    first.setdefault(key, event['seq'])
        for sequence, changes in record.owner_versions.items():
            for key, value in changes.items():
                if value is not None:
                    first[key] = min(first.get(key, sequence), sequence)
        for server in self.servers:
            for key, sequence in server.get('created_before', {}).items():
                rolled_back = any(start <= sequence <= end for start, end in rollback)
                if (first.get(key) != sequence and not rolled_back) or sequence > server.get('before_seq', -1):
                    self.lifecycle_errors.add(Fact(key, 'unverified-source-creation'))
        seed_events = {e['seq']: e for e in getattr(self, 'seed_events', [])}
        for event in record.events:
            seed = event['seq'] <= getattr(self, 'seed_sequence', 0)
            fixture = any(c['action'] == 'fixture_input' for c in self.calls_at(event['seq']))
            if event['action'] == 'fixture' and not (seed or fixture):
                self.lifecycle_errors.add(Fact('sequence:' + str(event['seq']), 'unscripted-fixture-event'))
            if event['seq'] in seed_events and event != seed_events[event['seq']]:
                self.lifecycle_errors.add(Fact('sequence:' + str(event['seq']), 'changed-fixture-input'))
            for call in self.calls_at(event['seq']):
                if call['action'] == 'fixture_input':
                    if event['action'] != 'fixture' or event['set'] != call['arguments']['changes']:
                        self.lifecycle_errors.add(Fact('sequence:' + str(event['seq']), 'changed-fixture-input'))
        for first, last, seq in restore_intervals(record.events):
            event = next(e for e in record.events if e['seq'] == seq)
            self.resolve('restore', 'sequence:' + str(seq),
                scripted_confirmation=self.scripted_transition(event, 'control_restore_confirm'),
                rollback_interval=self.restore_proof(event) and first <= seq and last < seq, commit_order=seq in record.committed)
        changed = {key for event in record.events for key in event['set']}
        rows = {key: value for key, value in record.rows.items() if key not in changed}
        resolved = set()
        for event in record.events:
            fixture_calls = [c for c in self.calls_at(event['seq']) if c['action'] == 'fixture_input']
            fixture = event['seq'] <= getattr(self, 'seed_sequence', 0) or bool(fixture_calls)
            # Explicit fixture data is an independent input. A changed copy in
            # a commit must not become a new source of owner obligations, even
            # when another fixture-consistency defect already exists there.
            inputs = (fixture_calls[0]['arguments']['changes'] if fixture_calls else
                      seed_events.get(event['seq'], {}).get('set', {}))
            changes = {**event['set'], **inputs}
            self.resolution_sequence = event['seq']
            operation_id = event.get('operation_id')
            summary = event.get('summary', '')
            operation_claim = summary in {'submitting', 'done', 'partial', 'unknown', 'failed', 'refused'} or summary.startswith(
                ('reserved ', 'local repair of ', 'stage ', 'approval expired', 'cancelled before submission', 'notice acknowledged')) or event['action'].startswith('mail_sent_copy_')
            if operation_id and operation_claim and 'op:' + operation_id not in event['set']:
                self.stage_claims(event, 'op:' + operation_id, rows.get('op:' + operation_id, {}), None)
            content = event.get('untrusted_content', {})
            for name, prefix in (('filing', 'mail:filing:'), ('rename', 'mail:rename:')):
                claim = content.get(name)
                if isinstance(claim, dict):
                    filing_id = claim.get('filing_id', claim.get('id'))
                    if filing_id and prefix + filing_id not in event['set']:
                        self.filing_claims(prefix + filing_id, None, event)
            if event['action'] in {'mail_move', 'mail_copy', 'mail_folder_rename', 'mail_filing_check'}:
                for notice_key, notice in event['set'].items():
                    source = notice.get('source_key', '') if notice_key.startswith('notice:') and isinstance(notice, dict) else ''
                    if source.startswith(('mail:filing:', 'mail:rename:')) and source not in event['set']:
                        self.filing_claims(source, None, event)
            if event['action'] == 'mail_account_add' and event.get('outcome') == 'done' and summary.startswith('onboarding complete;'):
                for call in self.calls_at(event['seq']):
                    if call['action'] == 'mail_account_add' and call.get('start_seq', -1) < event['seq'] <= call.get('end_seq', -1):
                        account_key = 'mail:account:' + str(call['arguments'].get('id'))
                        if not isinstance(event['set'].get(account_key), dict):
                            self.lifecycle_errors.add(Fact(account_key, 'missing-account-result', detail=str(event['seq'])))
            if event['action'] == 'mail_sent_copy_check' and event.get('operation_id') and 'op:' + event['operation_id'] not in event['set']:
                self.lifecycle_errors.add(Fact('op:' + event['operation_id'], 'missing-check-result'))
            if event['action'] == 'mail_filing_check' and not any(
                    key.startswith(('mail:filing:', 'mail:rename:')) and isinstance(value, dict)
                    for key, value in event['set'].items()):
                self.filing_claims('filing-check', None, event)
            stage = event.get('untrusted_content', {})
            if 'stage' in stage and 'outcome' in stage:
                source = 'op:' + str(event.get('operation_id'))
                row = event['set'].get(source) or {}
                if row.get('stages', {}).get(stage['stage']) != stage['outcome']:
                    self.lifecycle_errors.add(Fact(source, 'changed-stage-event', detail=str(event['seq'])))
            for key, value in changes.items():
                old = rows.get(key, {})
                if not old and event['action'] == 'control_restore_confirm' and self.restore_proof(event):
                    old = self.lifecycle_known.get(key, {})
                input_source = key in inputs and not old
                if key.startswith(('intent:', 'mail:filing:', 'mail:rename:')) and value:
                    identity = key.split(':', 2)[-1] if key.startswith('mail:') else key[7:]
                    allowed = {identity, 'recovery-' + identity} if key.startswith('intent:') else {identity}
                    if value.get('id') not in allowed or old and value.get('id') != old.get('id'):
                        self.lifecycle_errors.add(Fact(key, 'source-identity'))
                        value = {**value, 'id': old.get('id', identity)}
                    if key in self.source_ids and value.get('id') != self.source_ids[key]:
                        self.lifecycle_errors.add(Fact(key, 'source-identity'))
                        value = {**value, 'id': self.source_ids[key]}
                    if key.startswith('mail:') and value.get('app', 'mail') != 'mail':
                        self.lifecycle_errors.add(Fact(key, 'unjustified-app-scope'))
                        value = {**value, 'app': 'mail'}
                if isinstance(value, dict) and value.get('action', '').startswith(('mail_', 'testapp_')):
                    app = value['action'].split('_', 1)[0]
                    if value.get('app', app) != app:
                        self.lifecycle_errors.add(Fact(key, 'unjustified-app-scope'))
                        value = {**value, 'app': app}
                    elif 'app' not in value:
                        value = {**value, 'app': app}
                if key.startswith(('intent:', 'export:')) and value:
                    if old and value.get('app') != old.get('app'):
                        self.lifecycle_errors.add(Fact(key, 'changed-source-scope'))
                        value = {**value, 'app': old.get('app')}
                    if not old:
                        calls = self.calls_at(event['seq'])
                        apps = {c['action'].split('_', 1)[0] for c in calls if c['action'].startswith(('mail_', 'testapp_'))}
                        apps.update(c['arguments']['app'] for c in calls if c['arguments'].get('app') in {'mail', 'testapp'})
                        if len(apps) == 1:
                            expected_app = next(iter(apps))
                            if value.get('app') != expected_app:
                                self.lifecycle_errors.add(Fact(key, 'unjustified-app-scope'))
                                value = {**value, 'app': expected_app}
                if key.startswith('mail:account:') and value and value.get('app', 'mail') != 'mail':
                    self.lifecycle_errors.add(Fact(key, 'unjustified-app-scope'))
                    value = {**value, 'app': 'mail'}
                if key.startswith('mail:account:') and value and value.get('id') != key.removeprefix('mail:account:'):
                    self.lifecycle_errors.add(Fact(key, 'account-identity'))
                if key in {'generation', 'restore_pending'} and value != old:
                    initial = key == 'generation' and event['action'] in {'control_initialize', 'fixture'} and not old
                    if not initial and not self.scripted_transition(event, 'control_restore_confirm'):
                        self.lifecycle_errors.add(Fact(key, 'unjustified-restore-transition'))
                if key.startswith('archived:') and value:
                    if event['action'] != 'control_archive' or value != {'seq': event['seq']} or event['set'].get('op:' + key[9:], 'absent') is not None:
                        self.lifecycle_errors.add(Fact(key, 'unjustified-archive-marker'))
                        continue
                if key.startswith('notice:') and value:
                    warning_notice = value.get('check_kind') in {'filing', 'rename', 'sent_copies'} or str(value.get('source_key', '')).startswith(('op:', 'mail:filing:', 'mail:rename:'))
                    if not fixture and warning_notice:
                        for field in ('source_key', 'check_kind', 'evidence_fingerprint'):
                            if not value.get(field):
                                self.lifecycle_errors.add(Fact(key, 'missing-warning-context', detail=canonical({'sequence': event['seq'], 'field': field})))
                    if value.get('id') != key[7:]:
                        self.lifecycle_errors.add(Fact(key, 'notice-identity'))
                    for field in ('id', 'source_key', 'check_kind', 'evidence_fingerprint', 'created_at'):
                        if field in old and value.get(field) != old[field]:
                            self.lifecycle_errors.add(Fact(key, 'changed-notice-context', detail=field))
                    calls = self.calls_at(event['seq'])
                    if not old and 'created_at' in value and 'time' in event and calls:
                        valid_time = min(c['clock'] for c in calls) * 1_000_000_000 - 1 <= value['created_at'] <= event['time'] * 1_000_000_000 + 1
                        if not valid_time and event['action'] == 'control_restore_confirm' and self.restore_proof(event):
                            from .projection import fact
                            for sequence, publication in record.owner_versions.items():
                                earlier_calls = self.calls_at(sequence)
                                stamp = next((f['time'] for f in record.fences if f['seq'] == sequence), float('-inf'))
                                if (sequence < event['seq'] and publication.get(key) == fact(key, value) and earlier_calls and
                                        min(c['clock'] for c in earlier_calls) * 1_000_000_000 - 1 <= value['created_at'] <= stamp * 1_000_000_000 + 1):
                                    valid_time = True
                                    break
                        if not valid_time:
                            self.lifecycle_errors.add(Fact(key, 'notice-creation-time'))
                if key.startswith('op:') and value:
                    if value.get('id') != key[3:]:
                        self.lifecycle_errors.add(Fact(key, 'operation-identity', detail=str(event['seq'])))
                        value = {**value, 'id': old.get('id', key[3:])}
                    if not fixture and value.get('state') == 'reserved':
                        calls = self.calls_at(event['seq'])
                        deadlines = [clock + c.get('operation_ttl', 900) for c in calls for clock in c.get('clock_samples', [])]
                        valid = type(value.get('expires')) in (int, float) and (old or not deadlines or value['expires'] in deadlines)
                        if not valid:
                            self.lifecycle_errors.add(Fact(key, 'unapproved-expiry'))
                            value = {**value, 'expires': old.get('expires') if type(old.get('expires')) in (int, float) else
                                     deadlines[0] if deadlines else max((c['clock'] for c in calls), default=0) + 900}
                    payload = value.get('payload', {})
                    if any(not isinstance(item, dict) or not isinstance(item.get('reference'), dict) for item in payload.get('items', [])):
                        self.lifecycle_errors.add(Fact(key, 'unapproved-payload', detail='items/reference'))
                        value = {**value, 'payload': old.get('payload', {**payload, 'items': []}),
                                 'state': old.get('state', 'unknown'), 'reason': old.get('reason', 'Submission outcome uncertain; inspect evidence, never retry.')}
                    if not old and not value.get('context_version') and fixture:
                        self.legacy_sources.add(key)
                    if value.get('action', '').endswith('_operation_repair'):
                        candidates = [c for c in self.script if c['action'] == value['action'] and
                                      c.get('start_seq', -1) < event['seq'] <= c.get('end_seq', -1)]
                        if candidates:
                            self.repair_authority.setdefault(key, candidates[0])
                        authority = self.repair_authority.get(key)
                        if authority:
                            args = authority['arguments']
                            if value.get('repair_of') != args.get('operation_id') or value.get('payload') != args:
                                self.lifecycle_errors.add(Fact(key, 'unapproved-repair-context'))
                                value = {**value, 'repair_of': args.get('operation_id'), 'payload': copy.deepcopy(args)}
                    self.payload_claims(key, value)
                    if value.get('state') in {'reserved', 'submitting'} and not fixture:
                        repair = value.get('action', '').endswith('_operation_repair')
                        reason = ('Reserved local repair only.' if repair else 'Awaiting exact approval; nothing submitted.') if value['state'] == 'reserved' else (
                            'Repairing local stage only.' if repair else 'Durably submitting; do not cancel or retry.')
                        if value.get('reason') != reason:
                            self.lifecycle_errors.add(Fact(key, 'unjustified-operation-reason'))
                            value = {**value, 'reason': reason}
                    if value.get('state') in {'unknown', 'partial'} and not fixture:
                        state, reason = ((old['state'], old['reason']) if old.get('state') == value['state'] and old.get('reason') else
                                         self.outcome(value, event))
                        if (value.get('state'), value.get('reason')) != (state, reason):
                            self.lifecycle_errors.add(Fact(key, 'unjustified-operation-reason'))
                            value = {**value, 'state': state, 'reason': reason}
                    if old.get('reason') is not None and old.get('state') == value.get('state') and value.get('reason') != old['reason'] and event['action'] != 'control_restore_confirm':
                        self.lifecycle_errors.add(Fact(key, 'changed-operation-reason'))
                        value = {**value, 'reason': old['reason']}
                    checked = value.get('sent_copy_check', {})
                    prior_check = old.get('sent_copy_check', {})
                    if event['action'] == 'mail_sent_copy_check' and checked.get('unavailable'):
                        opening_seq = max((e['seq'] for e in record.events if e['seq'] < event['seq'] and
                            e['action'] == 'mail_sent_copy_check_open' and key in e['set']), default=0)
                        mid = '<' + key[3:].replace(':', '.') + '@mail.aresos.invalid>'
                        if any(e['command'] == 'SEARCH' and mid in canonical(e.get('arguments', [])) and
                               opening_seq <= e.get('before_seq', -1) < event['seq'] and
                               e['call'] in {c['call'] for c in self.calls_at(event['seq'])} for e in self.servers):
                            self.proof('stage_claims', Fact(key, 'false-unavailable-result'))
                    opening = event['action'] == 'mail_sent_copy_check_open'
                    if opening or old and prior_check.get('state') != 'open' and checked.get('state') == 'open':
                        calls = self.calls_at(event['seq'])
                        planned = any(c['action'] in {'control_pending', 'control_log', 'mail_filing_notices',
                            'mail_operation_status', 'mail_operation_repair', 'mail_notice_ack'} or c['action'] in {'mail_send', 'mail_unsubscribe'} and c.get('arguments', {}).get('operation_id') == value['id'] for c in calls)
                        observed = any(e['command'] == 'SENT' and e.get('source') == key and
                            e['call'] in {c['call'] for c in calls} and e.get('before_seq', -1) >= event['seq'] for e in self.servers)
                        folded = event.get('untrusted_content', {}).get('stage') == 'smtp_data'
                        valid_open = (opening or folded) and (fixture or planned or observed)
                        if not valid_open:
                            self.lifecycle_errors.add(Fact(key, 'unjustified-check-reopen', detail=str(event['seq'])))
                        if opening and checked.get('state') != 'open':
                            self.lifecycle_errors.add(Fact(key, 'missing-check-enrollment', detail=str(event['seq'])))
                        value = {**value, 'sent_copy_check': {**checked, 'state': 'open'} if valid_open else prior_check}
                    if checked and checked.get('state') not in {'open', 'checked'}:
                        self.lifecycle_errors.add(Fact(key, 'invalid-check-state', detail=str(event['seq'])))
                    if checked.get('state') == 'open' and event['action'] == 'mail_sent_copy_check' and self.result_proof(key, 'sent_copies', event['seq']):
                        self.lifecycle_errors.add(Fact(key, 'uncommitted-check-result', detail=str(event['seq'])))
                    if not old and not input_source and event['seq'] > getattr(self, 'seed_sequence', 0):
                        calls = self.calls_at(event['seq'])
                        allowed = set()
                        for call in calls:
                            action = call['action']
                            if '_prepare_' in action:
                                allowed.add(action.replace('_prepare_', '_'))
                            elif action == 'mail_account_add':
                                allowed.update({'mail_send', 'mail_delete', 'mail_onboarding_folder_probe', 'mail_operation_repair'})
                            elif action.endswith('_operation_repair') or call['arguments'].get('operation_id') == value.get('id'):
                                allowed.add(action)
                            elif action == 'control_restore_confirm':
                                allowed.update(op.get('description', {}).get('action') for fence in record.fences
                                               for op in fence.get('operations', []) if op.get('id') == value.get('id'))
                        if calls and value.get('action') not in allowed:
                            self.lifecycle_errors.add(Fact(key, 'unjustified-operation-action'))
                            if len(allowed) == 1:
                                value = {**value, 'action': next(iter(allowed))}
                            apps = {action.split('_', 1)[0] for action in allowed if action}
                            if len(apps) == 1:
                                value = {**value, 'app': apps.pop()}
                    for field in ('id', 'app', 'action', 'payload', 'approval', 'expires', 'repair_of', 'context_version', 'roles_before'):
                        if field in old and value.get(field) != old[field]:
                            self.lifecycle_errors.add(Fact(key, 'changed-operation-context', detail=field))
                            value = {**value, field: old[field]}
                    if not input_source and event['seq'] > getattr(self, 'seed_sequence', 0):
                        self.stage_claims(event, key, old, value)
                        if value.get('state') not in {'reserved', 'submitting', 'unknown', 'partial', 'done', 'failed', 'refused'}:
                            self.lifecycle_errors.add(Fact(key, 'invalid-operation-state'))
                            value = {**value, 'state': old.get('state', 'unknown')}
                        if not old and value.get('state') in {'done', 'failed', 'refused'} and not self.resolution_proof(record, event, key, value):
                            self.lifecycle_errors.add(Fact(key, 'unjustified-resolution'))
                            value = {**value, 'state': 'unknown'}
                    if not input_source:
                        value = self.transition(record, event, key, old, value)
                if key.startswith(('mail:filing:', 'mail:rename:')) and value:
                    if not fixture:
                        for field in ('account', 'source', 'sources', 'target', 'verb', 'message_count'):
                            if field in old and value.get(field) != old[field]:
                                self.lifecycle_errors.add(Fact(key, 'changed-filing-context', detail=canonical({'sequence': event['seq'], 'field': field})))
                                value = {**value, field: old[field]}
                    if old:
                        self.warning_contexts.setdefault(key, copy.deepcopy(old))
                    value = self.filing_claims(key, value, event)
                    if not old and not fixture and value.get('state') != 'started':
                        self.lifecycle_errors.add(Fact(key, 'unsupported-resolution', detail='initial filing result without an open check'))
                        value = {**value, 'state': 'started', 'check_open': True}
                    if value.get('state') not in {'started', 'done', 'partial', 'unknown', 'failed'}:
                        self.lifecycle_errors.add(Fact(key, 'invalid-filing-state', detail=str(event['seq'])))
                    if (not fixture and value.get('state') == 'started' and
                            event['action'] not in {'mail_filing_check', 'mail_filing_check_open'} and
                            event.get('outcome') not in {None, 'started', 'unknown'}):
                        self.lifecycle_errors.add(Fact(key, 'unjustified-filing-start', detail=str(event['seq'])))
                    if old and old.get('state') != 'started' and not old.get('check_open') and value.get('check_open') and event['action'] not in {'mail_filing_check', 'mail_filing_check_open'}:
                        self.lifecycle_errors.add(Fact(key, 'unjustified-check-reopen', detail=str(event['seq'])))
                if key.startswith('mail:account:') and value and event['seq'] > getattr(self, 'seed_sequence', 0):
                    if event['action'] == 'mail_account_add' and event.get('outcome') == 'done' and not value.get('onboarded'):
                        self.lifecycle_errors.add(Fact(key, 'incomplete-onboarding-result', detail=str(event['seq'])))
                    if old.get('onboarded') and not value.get('onboarded'):
                        self.lifecycle_errors.add(Fact(key, 'reversed-onboarding', detail=str(event['seq'])))
                if key.startswith('notice:') and value and value.get('ack') and not old.get('ack'):
                    if self.resolve('acknowledgement', key, scripted_identity=event['action'].endswith('_notice_ack') and self.scripted_transition(event, '_notice_ack', value['id']), commit_order=True):
                        self.acknowledged.add(value['id'])
                    else:
                        self.lifecycle_errors.add(Fact(key, 'unjustified-ack'))
                        value = {**value, 'ack': False}
                if key.startswith('op:') and value and value.get('ack') and not old.get('ack'):
                    if self.resolve('acknowledgement', key, scripted_identity=event['action'].endswith('_notice_ack') and self.scripted_transition(event, '_notice_ack', value['id']), commit_order=True):
                        self.acknowledged.add('operation:' + value['id'])
                    else:
                        self.lifecycle_errors.add(Fact(key, 'unjustified-ack'))
                        value = {**value, 'ack': False}
                if key.startswith(('mail:filing:', 'mail:rename:')) and old and (old.get('state') == 'started' or old.get('check_open')) and value and not (value.get('state') == 'started' or value.get('check_open')):
                    kind = 'rename' if key.startswith('mail:rename:') else 'filing'
                    self.warning_contexts.setdefault(key, copy.deepcopy(old))
                    if not self.resolve('check_result', key, server_result=not event['action'].endswith('_notice_ack') and self.result_proof(key, kind, event['seq']), commit_order=True):
                        self.lifecycle_errors.add(Fact(key, 'unjustified-check-close', detail=str(event['seq'])))
                        value = {**value, 'check_open': True}
                if not fixture and key.startswith('op:') and old.get('sent_copy_check', {}).get('state') == 'open' and value and value.get('sent_copy_check', {}).get('state') != 'open':
                    if not self.resolve('check_result', key, server_result=self.sent_result_commit(event, key) and
                                        value.get('sent_copy_check', {}).get('state') == 'checked' and self.result_proof(key, 'sent_copies', event['seq']), commit_order=True):
                        self.lifecycle_errors.add(Fact(key, 'unjustified-check-close', detail=str(event['seq'])))
                        value = {**value, 'sent_copy_check': old['sent_copy_check']}
                if (key.startswith('mail:account:') and not old.get('onboarded', old.get('ready', False)) and value and
                        value.get('onboarded', value.get('ready', False)) and event['seq'] > getattr(self, 'seed_sequence', 0)):
                    calls = [c for c in self.script if c['action'] == 'mail_account_add' and c['arguments'].get('id') == key.removeprefix('mail:account:')
                             and c.get('start_seq', -1) < event['seq'] <= c.get('end_seq', float('inf'))]
                    if not self.resolve('onboarding_completion', key, scripted_account=event['action'] == 'mail_account_add' and event.get('outcome') == 'done' and bool(calls), commit_order=bool(calls), delivered_probe=any(
                            e['command'] == 'DATA' and e['accepted'] and e['reply'] == 'delivered' and e.get('before_seq', float('inf')) < event['seq'] and e.get('account') == key.removeprefix('mail:account:') and e['call'] in {c['call'] for c in calls} for e in self.servers)):
                        self.lifecycle_errors.add(Fact(key, 'unjustified-onboarding-close'))
                        value = {**value, 'onboarded': False, 'ready': False}
                if key.startswith('op:') and key in self.operation_notices and value and value.get('state') == 'failed':
                    if 'operation:' + value['id'] not in self.acknowledged and not value.get('notice'):
                        self.lifecycle_errors.add(Fact(key, 'lost-operation-notice'))
                        value = {**value, 'notice': True}
                if value is None and key.startswith(('op:', 'mail:filing:', 'mail:rename:', 'intent:', 'export:', 'mail:account:')) and old:
                    unacknowledged = (key in self.operation_notices and 'operation:' + old['id'] not in self.acknowledged) or any(
                        source == key and handle not in self.acknowledged for (source, *_), handle in self.occurrences.items())
                    unresolved = (unacknowledged or old.get('state') in {'reserved', 'started', 'submitting', 'unknown', 'partial'} or old.get('check_open') or
                                  key.startswith(('intent:', 'export:')) or key.startswith('mail:account:') and not old.get('onboarded', old.get('ready', False)))
                    acknowledged_intent = key.startswith('intent:') and self.scripted_transition(event, '_notice_ack', old.get('id'))
                    completed_intent = key.startswith('intent:') and self.intent_result_proof(record, event, key, old)
                    completed_export = key.startswith('export:') and self.export_result_proof(event, key, old)
                    if acknowledged_intent:
                        acknowledged_intent = self.resolve('acknowledgement', key, scripted_identity=True, commit_order=True)
                    if completed_intent:
                        completed_intent = self.resolve('intent_completion', key, scripted_action=True, required_effects=True, commit_order=True)
                    if completed_export:
                        completed_export = self.resolve('export_publication', key, scripted_export=True, publication_or_fault=True, commit_order=True)
                    if not unresolved and event['action'] == 'control_archive':
                        self.resolve('archive', key, scripted_archive=self.scripted_transition(event, 'control_archive'),
                            no_obligation=True, qualified_manifest=any(k.startswith('archive:') and v for k, v in event['set'].items()), commit_order=True)
                    if unresolved and not (acknowledged_intent or completed_intent or completed_export):
                        self.lifecycle_errors.add(Fact(key, 'unjustified-removal'))
                        value = old
                if value is None:
                    rows.pop(key, None)
                    resolved.add(key)
                else:
                    rows[key] = value
        # Read-only synthetic fixtures may give rows directly; real decoded rows
        # always have events. Remember obligations across rollback and restore.
        if not record.events:
            rows = dict(record.rows)
        for key, old in self.lifecycle_known.items():
            if not isinstance(old, dict):
                continue
            required_notice = key in self.operation_notices and 'operation:' + old['id'] not in self.acknowledged
            unresolved = self.unfinished(key, old)
            if key not in rows and key not in resolved and (required_notice or unresolved):
                rows[key] = old
                self.lifecycle_errors.add(Fact(key, 'missing-obligation-source'))
        for call in self.script:
            if call['action'] != 'mail_account_add':
                continue
            account = call['arguments'].get('id')
            key = 'mail:account:' + str(account)
            effects = [e for e in self.servers if e['call'] == call['call'] and e.get('account') == account and
                       e['command'] in MUTATIONS and (e['accepted'] or e['reply'] != 'delivered')]
            if effects and key not in rows:
                self.lifecycle_errors.add(Fact(key, 'missing-obligation-source'))
                rows[key] = {'id': account, 'onboarded': False, 'ready': False}
        self.retain_obligations(record, rows)
        self.lifecycle_known = rows.copy()
        result = copy.copy(record)
        result.rows = rows
        self.validated_input, self.validated_record = record, result
        return result

    def projection(self, record):
        for source, projected in getattr(self, 'envelope_projections', ()):
            if record is source or record is projected:
                return projected
        if record is getattr(self, 'validated_input', None) or record is getattr(self, 'validated_record', None):
            return self.validated_record
        return self.lifecycle(record)

    def resolution_proof(self, record, event, key, row):
        if event['seq'] <= getattr(self, 'seed_sequence', 0):
            return True
        calls = [c for c in self.script if c.get('start_seq', -1) < event['seq'] <= c.get('end_seq', -1)
                 and (c.get('arguments', {}).get('operation_id') == row.get('id') or c['action'] == 'mail_account_add' or c.get('call') == self.repair_authority.get(key, {}).get('call'))]
        commands = [e for e in self.servers if e['command'] in MUTATIONS and e.get('before_seq', -1) < event['seq']
                    and self.bound(e)[0] == key]
        if row.get('state') == 'done':
            candidate = copy.copy(record)
            candidate.rows = {**record.rows, key: row}
            if any(f.source == key for f in self.completion_errors(candidate)):
                return False
            if row.get('action') == 'testapp_delete':
                return bool(calls) and any(e['seq'] < event['seq'] and e.get('operation_id') == row.get('id') and 'testapp' in e['set'] for e in record.events)
            parent = row.get('repair_of', row.get('id'))
            evidence = [e for e in self.servers if e.get('source') == 'op:' + str(parent) and e['command'] == 'SENT'
                        and e['identities'] and e.get('before_seq', -1) < event['seq']]
            return bool(commands or evidence) and bool(calls or evidence)
        return bool(any(c.get('faults', {}).get('trace') for c in calls) or
                    any(not e['accepted'] or e['reply'] != 'delivered' for e in commands))

    def stage_claims(self, commit, key, old, row):
        if row is None:
            self.proof('stage_claims', Fact(key, 'missing-operation-result', detail=str(commit['seq'])))
            return
        if row.get('repair_of') and row.get('state') == 'done' and old.get('state') != 'done':
            parent = 'op:' + row['repair_of']
            if not isinstance(commit['set'].get(parent), dict):
                self.proof('stage_claims', Fact(parent, 'missing-operation-result', detail=str(commit['seq'])))
            else:
                stage = row.get('payload', {}).get('stage')
                if commit['set'][parent].get('stages', {}).get(stage) not in {'done', 'not_needed'}:
                    self.proof('stage_claims', Fact(parent, 'unjustified-stage', detail='repair-parent:' + str(stage)))
        if old.get('stages') == row.get('stages') and (row.get('state') != 'done' or old.get('state') == 'done'):
            return  # No new stage claim or completion claim in a repeated read.
        marker = commit['seq'], key, canonical(row.get('stages', {}))
        if marker in self.stages_examined:
            return
        self.stages_examined.add(marker)
        parent = row.get('repair_of', row.get('id'))
        mid = '<' + str(parent).replace(':', '.') + '@mail.aresos.invalid>'
        payload = row.get('payload', {})
        mail = self.approved(row) or payload.get('composition', {}).get('mail', {})
        refs = [item['reference'] for item in (self.approved(row) or payload).get('items', [])]
        events = self.operation_events('op:' + str(parent), commit['seq'])
        events.extend(e for e in self.servers if e not in events and e.get('before_seq', -1) < commit['seq'] and self.bound(e)[0] == key)
        accepted = lambda command: [e for e in events if e['command'] == command and e['accepted'] and e['reply'] == 'delivered']
        for name, outcome in row.get('stages', {}).items():
            if old.get('stages', {}).get(name) == outcome:
                continue
            proof = True
            if name == 'message_id':
                proof = outcome == mid
            elif name == 'smtp_data' and outcome.startswith('accepted:'):
                proof = bool(accepted('DATA'))
            elif name.startswith(('rcpt:', 'recipient:')) and outcome.startswith(('accepted', 'refused')):
                address = name.split(':', 1)[1]
                candidates = [e for e in events if e['command'] == ('RECEIVE' if row.get('app') == 'testapp' else 'RCPT') and address in e.get('recipients', []) and e['reply'] == 'delivered']
                proof = bool(candidates) and candidates[-1]['accepted'] == outcome.startswith('accepted')
            elif name == 'sent_copy' and outcome == 'done':
                proof = (send_stages(mail, events, self.sent_policy(row))['sent_copy'] if row.get('app') == 'mail' else
                         any(e.get('stage') == name for e in accepted('LOCAL_STAGE')))
            elif name == 'answered_flag' and outcome in {'done', 'not_needed'}:
                if outcome == 'not_needed':
                    proof = not mail.get('answered_reference')
                else:
                    proof = (send_stages(mail, events, self.sent_policy(row))['answered_flag'] if row.get('app') == 'mail' else
                             any(e.get('stage') == name for e in accepted('LOCAL_STAGE')))
            elif name.startswith('marked:'):
                ref = next((ref for ref in refs if fingerprint(ref) == name[7:]), None)
                proof = bool(ref and outcome == 'deleted flag set' and any(exact_uid(e, ref, 'STORE', ['+FLAGS.SILENT', '(\\Deleted)']) for e in accepted('STORE')))
            elif name == 'folder_probe':
                commands = [e for e in events if e['command'] == 'DELETE']
                text = ' '.join(commands[-1].get('response_text', [])) if commands else ''
                qualified = bool(commands and commands[-1].get('response_code') == 'NO' and
                                 re.search(r'NON[- ]?EMPTY|NOT EMPTY|CONTAINS MESSAGES|HOLDS MAIL', text.upper()))
                proof = bool(commands) and (outcome == 'nonempty_refusal') == qualified
            elif name == 'folder' and outcome == 'deleted':
                proof = bool(accepted('DELETE'))
            elif name.startswith('target:') and outcome in {'trashed', 'expunged', 'marked_deleted_not_expunged'}:
                ref = next((ref for ref in refs if fingerprint(ref) == name[7:]), None)
                command = {'trashed': 'MOVE', 'expunged': 'EXPUNGE', 'marked_deleted_not_expunged': 'STORE'}[outcome]
                proof = bool(ref and any(e.get('folder') == ref['folder'] and str(e.get('arguments', [''])[0]) == str(ref['uid']) for e in accepted(command)))
            elif name == 'https_post' and outcome.isdigit():
                proof = any(str(e.get('status')) == outcome for e in accepted('POST'))
            if not proof:
                self.proof('stage_claims', Fact(key, 'unjustified-stage', detail=name))
        if row.get('state') == 'done' and row.get('app') == 'mail' and row.get('action') in {'mail_send', 'mail_unsubscribe'} and payload.get('composition'):
            for name in send_stages(mail, events, self.sent_policy(row)):
                wanted = 'not_needed' if name == 'answered_flag' and not mail.get('answered_reference') else 'done'
                if row.get('stages', {}).get(name) != wanted:
                    self.proof('stage_claims', Fact(key, 'unjustified-stage', detail='missing:' + name))

    def intent_result_proof(self, record, event, key, old):
        if event['seq'] <= getattr(self, 'seed_sequence', 0):
            return event['action'] == old.get('action')
        if event['action'] != old.get('action') or not self.scripted_transition(event, old.get('action', 'impossible')):
            return False
        commands = [e for e in self.servers if self.bound(e)[0] == key and e.get('before_seq', -1) < event['seq']]
        calls = [c for c in self.script if c['action'] == old['action'] and c.get('start_seq', -1) < event['seq'] <= c.get('end_seq', -1)]
        if key.startswith('intent:archive-') and old.get('action') == 'control_archive':
            checks = old.get('checks', {})
            return bool(checks) and all(any(
                e['command'] == 'SENT' and e.get('source') == 'op:' + identity and delivered(e) and
                e['call'] in {c['call'] for c in calls} and e.get('before_seq', -1) < event['seq'] and
                result == {'state': 'checked', 'count': len(e['identities']), 'matches': e['identities']}
                for e in self.servers) for identity, result in checks.items())
        planned = [(c, free_plan(c)) for c in calls if free_plan(c) is not None]
        if planned:
            return any(complete_plan(plan, [e for e in self.servers if e['call'] == c['call'] and
                       e.get('before_seq', -1) < event['seq']]) for c, plan in planned)
        if commands:
            return all(delivered(e) for e in commands if e['command'] in MUTATIONS)
        if old.get('action') == 'testapp_flag':
            return any(self.local_flag_result(record, event, key, old, c) for c in calls)
        if old.get('action') == 'mail_account_folders':
            return any(e['call'] in {c['call'] for c in calls} and e['command'] == 'LIST' and e['accepted'] and e['reply'] == 'delivered'
                       and e.get('account') in {c['arguments'].get('id') for c in calls} and e.get('before_seq', -1) < event['seq'] for e in self.servers)
        if old.get('action') == 'mail_attachment_save':
            inputs = [e for e in self.servers if e['command'] == 'EXPORT_INPUT']
            return any(e['seq'] <= event['seq'] and any(name.startswith('export:') and value and any(
                value.get('sha256') == source['sha256'] and value.get('size') == source['size'] for source in inputs)
                for name, value in e['set'].items()) for e in record.events)
        # Local settings and role review have a decoded effect in this very
        # commit. Missing R2 context is checked separately by local.py.
        return old.get('action') in {'mail_account_settings', 'mail_account_folders'} and any(
            e['seq'] <= event['seq'] and e['action'] == old['action'] and self.scripted_transition(e, old['action']) and
            any(name.startswith('mail:account:') and value for name, value in e['set'].items()) for e in record.events)

    def local_flag_result(self, record, event, key, old, call):
        errors = local_errors(record, self.script, getattr(self, 'seed_sequence', 0), self.servers)
        return not any(source == key and kind == 'R2.LOCAL_FLAG' for source, kind, _ in errors) and any(
            e['seq'] <= event['seq'] and e['seq'] > call.get('start_seq', -1) and e['action'] == 'testapp_flag' and
            'testapp' in e['set'] and e['set'].get(key, 'absent') is None for e in record.events)

    def sent_policy(self, operation):
        approved = self.approved(operation) or operation.get('payload', {}).get('composition', {}).get('mail', {})
        account_id = approved.get('account')
        value = 'client'
        for event in getattr(self, 'seed_events', []):
            account = event.get('set', {}).get('mail:account:' + str(account_id))
            if account:
                value = account.get('sent_policy', value)
        settings = [call for call in self.script if call['action'] == 'mail_account_settings' and
                    call['arguments'].get('id') == account_id and 'sent_policy' in call['arguments']]
        record = getattr(self, '_effect_record', None)
        if record and settings:
            key = 'mail:account:' + str(account_id)
            invalid = local_errors(record, self.script, getattr(self, 'seed_sequence', 0), self.servers)
            starts = [call.get('start_seq', float('inf')) for call in self.script if
                      call.get('arguments', {}).get('operation_id') == operation.get('id') and call['action'] in {'mail_send', 'mail_unsubscribe'}]
            boundary = min(starts, default=float('inf'))
            for call in settings:
                if call.get('end_seq', float('inf')) <= boundary and not any(kind == 'R2.LOCAL_CHANGE' for _, kind, _ in invalid) and any(e['action'] == 'mail_account_settings' and
                        call.get('start_seq', -1) < e['seq'] <= call.get('end_seq', -1) and
                        (e['set'].get(key) or {}).get('sent_policy') == call['arguments']['sent_policy'] for e in record.events):
                    value = call['arguments']['sent_policy']
        return value

    def outcome(self, row, commit):
        """Choose the reason from replies, effects and fault order, not a whitelist."""
        key = 'op:' + row['id']
        calls = [c for c in self.script if c.get('start_seq', -1) < commit['seq'] <= c.get('end_seq', -1)]
        events = self.operation_events(key, commit['seq'])
        fault = any(c.get('faults', {}).get('trace') for c in calls)
        if commit['action'] == 'control_restore_confirm' and self.restore_proof(commit):
            return 'unknown', 'Restored log: independent record has newer or missing evidence. Owner must check.'
        if row['state'] == 'unknown':
            if row.get('repair_of'):
                return 'unknown', ('Local repair storage failed; inspect evidence, never submit.' if fault else
                                   'Local repair uncertain; inspect far-side stage evidence. Never submit.')
            if not calls and row.get('state') == 'unknown':
                return 'unknown', 'Service restarted during submission; inspect evidence, never resubmit.'
            if any(e['command'] == 'SENT' and e.get('source') == key and e.get('identities') and delivered(e) and
                   e.get('before_seq', float('inf')) < commit['seq'] for e in self.servers):
                return 'unknown', 'Far-side submission evidence already exists; inspect evidence, never submit again.'
            return 'unknown', 'Submission outcome uncertain; inspect evidence, never retry.'
        approved = self.approved(row) or row.get('payload', {}).get('composition', {}).get('mail', {})
        if row.get('app') == 'mail' and row.get('payload', {}).get('composition'):
            data = [e for e in events if e['command'] == 'DATA']
            if not data or not delivered(data[-1]):
                return 'unknown', 'Submission outcome uncertain; inspect evidence, never retry.'
            refused = any(e['command'] == 'RCPT' and e['reply'] == 'delivered' and not e['accepted'] and e['call'] == data[-1]['call'] for e in self.servers)
            missing = not all(send_stages(approved, events, self.sent_policy(row)).values())
            reason = ('Some recipients refused; accepted recipients must never be sent again.' if refused else
                      'SMTP accepted delivery to every recipient.')
            return ('partial' if refused or missing else 'done', reason + (' Missing local stages; repair without SMTP.' if missing else ''))
        if row.get('action') == 'mail_delete':
            payload = self.approved(row) or row.get('payload', {})
            refs = [item['reference'] for item in payload.get('items', [])]
            command = 'MOVE' if payload.get('mode') == 'trash' else 'EXPUNGE'
            done = all(any(delivered(e) and e['command'] == command and e.get('folder') == ref['folder'] and
                           str(e.get('arguments', [''])[0]) == str(ref['uid']) for e in events) for ref in refs)
            if refs and done:
                return 'done', 'Exactly named messages deleted; no unnamed UID expunged.'
            return 'partial', 'Server refused an exact target; inspect per-item stages and prepare a new named set only after owner review.'
        if row.get('action') == 'mail_unsubscribe':
            return 'partial', 'Endpoint refused/redirected; no redirect followed, inspect with owner.'
        if row.get('app') == 'testapp':
            stages = [e for e in events if e['command'] == 'LOCAL_STAGE' and not delivered(e)]
            if stages:
                return 'partial', 'Fixture failed ' + stages[0]['stage'] + '; repair this local stage only.'
            return 'partial', 'Some recipients refused; never resubmit this operation.'
        return 'unknown', 'Submission outcome uncertain; inspect evidence, never retry.'

    def export_result_proof(self, event, key, old):
        if not event['action'].endswith('_file_save'):
            return False
        return any(c.get('start_seq', -1) < event['seq'] <= c.get('end_seq', -1) and (
            c['action'] == 'saved' and c['arguments'].get('export_id') == key[7:] and c['arguments'].get('app') == old.get('app') or
            c.get('faults', {}).get('trace') and event.get('outcome') == 'refused') for c in self.script)

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
        identity = record.rows.get(source, {}).get('id') or source
        if source.startswith('intent:'):
            bound = self.source_ids.setdefault(source, identity)
            if identity != bound:
                self.lifecycle_errors.add(Fact(source, 'source-identity'))
            return bound
        return identity

    def background_history(self, record=None):
        if self.background and self.background.get('conditional') and record is not None and not record.owner_rows.get('notice:background-storage'):
            self.background = None
        if self.background:
            return
        for call in self.script:
            faults = call.get('faults', {})
            guard = (record.owner_rows.get('notice:background-storage') or {}) if record else {}
            if ('maintenance_started' in call and (not call['maintenance_started'] or call.get('maintenance_finished'))
                    and not guard.get('check_open')):
                continue
            if faults.get('background') and faults.get('trace'):
                cause = faults['trace'][0]
                self.background = {'code': 'storage_error' if cause[2] == 'EIO' else 'storage_limit', 'call': call['call'], 'clock': call['clock'], 'conditional': bool(call.get('maintenance_finished')) or call.get('maintenance_started') is False}
                return

    def permitted_status(self, record, call):
        # Status is checked even when every catalogue is empty. A handled raw
        # failure may still yield success; only injected causes permit errors.
        if record.locked:
            permitted = {'restore_required'}
            faults = call.get('faults', {})
            if faults.get('trace') or faults.get('active_exhaustion'):
                permitted.add('storage_limit')
                if any(f[2] == 'EIO' for f in faults.get('trace', [])):
                    permitted.add('storage_error')
            return permitted
        allowed = {'allowed'}
        faults = call.get('faults', {})
        if call['action'] == 'testapp_operation_status' and faults.get('read_storage') == 'ENOSPC':
            allowed.add('storage_limit')
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
                         not any(k.startswith('intent:') for k in e['set']) and call.get('start_seq', -1) < e['seq'] <= call.get('end_seq', -1)]
            if not completed:
                continue
            events = [e for e in self.servers if e.get('account') == account_id and e['call'] == call['call']]
            if not events:
                continue
            deliveries = [e for e in events if e['command'] == 'DATA' and e['accepted'] and e['reply'] == 'delivered']
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
                if (setting['action'] == 'mail_account_settings' and account in result and 'sent_policy' in args and
                        'mail:account:' + account in event['set'] and setting.get('start_seq', -1) < event['seq'] <= setting.get('end_seq', -1)):
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
        def outcome(action, predicate, commands, success):
            return self.probe_outcome(events, record, completed_at, action, predicate, commands, success)
        initial = outcome('mail_onboarding_folder_probe', lambda p: p.get('folder') == folder and not p.get('empty'), [probe], 'refused')
        if initial != 'refused':
            return False, 'survival-unverified'
        refs = [ref for e in events if e['command'] == 'APPEND' and e['accepted'] and e.get('folder') == folder for ref in e.get('arrived', [])]
        survived = any(e['command'] == 'FETCH' and e['accepted'] and e['reply'] == 'delivered' and any(ref in e['identities'] for ref in refs) for e in events)
        expunges = [e for e in events if e['command'] == 'EXPUNGE' and any(
            str(ref['uid']) == str(e.get('arguments', [''])[0]) and ref['folder'] == e.get('folder') for ref in refs)]
        cleanup = outcome('mail_delete', lambda p: any(i.get('reference', {}).get('folder') == folder for i in p.get('items', [])), expunges, 'done')
        if not survived or cleanup in {None, 'reserved', 'submitting'}:
            return False, 'survival-unverified'
        expunged = bool(expunges) and all(e['accepted'] and e['reply'] == 'delivered' for e in expunges)
        if cleanup != 'done' or not expunged:
            return False, 'exact-cleanup-failed'
        if not nonempty:
            return False, 'generic-cleaned'
        empty_commands = probes[1:]
        empty = outcome('mail_onboarding_folder_probe', lambda p: p.get('folder') == folder and p.get('empty'), empty_commands, 'done')
        if empty in {None, 'reserved', 'submitting'}:
            return False, 'survival-unverified'
        if empty != 'done' or not all(e['accepted'] and e['reply'] == 'delivered' for e in empty_commands):
            return False, 'empty-cleanup-failed'
        return True, 'qualified'

    def probe_outcome(self, events, record, completed_at, action, predicate, commands, success):
        """A committed state is a claim, not evidence of a failed probe.

        Only faults after the correlated command can explain failure to commit
        its delivered result. Earlier handled faults cannot excuse a later lie.
        """
        candidates = [(e, k, v) for e in record.events if e['seq'] <= completed_at
                      for k, v in e['set'].items() if k.startswith('op:') and v and
                      v.get('action') == action and predicate(v.get('payload', {}))]
        if not candidates:
            if commands:
                self.lifecycle_errors.add(Fact('mail:account:' + str(events[0]['account']), 'missing-probe-result', detail=action))
            return None
        commit, key, row = candidates[-1]
        state = row.get('state')
        if not commands:
            if state not in {None, 'reserved', 'submitting'}:
                self.lifecycle_errors.add(Fact(key, 'unjustified-probe-result', detail=action))
            return state if state in {None, 'reserved', 'submitting'} else None
        last = commands[-1]
        call = next((c for c in self.script if c['call'] == last['call']), {})
        observed_by = self.commit_fault_points.get((last['call'], commit['seq']), float('inf'))
        faults = [f for f in call.get('faults', {}).get('trace', []) if last.get('fault_point', 0) < f[0] <= observed_by]
        ordered = last.get('before_seq', -1) < commit['seq'] <= call.get('end_seq', completed_at)
        if not ordered:
            self.lifecycle_errors.add(Fact(key, 'unjustified-probe-order', detail=action))
        delivered = all(e['reply'] == 'delivered' for e in commands)
        succeeded = delivered and all(e['accepted'] for e in commands)
        expected = success if succeeded or (success == 'refused' and delivered and not last['accepted']) else None
        if state == expected and ordered:
            return state
        if expected is not None and not faults:
            self.lifecycle_errors.add(Fact(key, 'unjustified-probe-result', detail=canonical({'state': state, 'expected': expected, 'ordered': ordered})))
            return expected
        # Failed/lost replies or a later injected write fault can explain an
        # uncertain/failed result, but never a fabricated successful result.
        if state == 'done' and not succeeded:
            self.lifecycle_errors.add(Fact(key, 'unjustified-probe-result', detail='successful result without delivered acceptance'))
            return 'unknown'
        return state

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
        key = 'mail:filing:' + str(context.get('id'))
        authority = self.filing_authority.get(key)
        items = context.get('records', [])
        if authority:
            items = [next((item for item in items if item.get('source') == ref), {'source': ref})
                     for ref in authority['arguments'].get('references', [])]
        for item in items:
            source = item['source']
            # The exact source's bytes were captured before the command. A
            # later LIST (after MOVE) cannot prove the source hash retroactively.
            origin = mutation or next((event for event in self.servers if event['command'] in {'MOVE', 'COPY'} and
                self.bound(event)[0] == key and event.get('folder') == source['folder'] and
                str(event.get('arguments', [''])[0]) == str(source['uid'])), None)
            candidates = list(origin.get('identities', [])) if origin else []
            for event in self.servers:
                if origin or event is listing:
                    break
                if event['command'] == 'FIXTURE_STATE':
                    candidates.extend(ref for refs in event.get('mailboxes', {}).values() for ref in refs)
                    break
            hashes = [ref.get('sha256') for ref in candidates if {k: v for k, v in ref.items() if k != 'sha256'} == source and ref.get('sha256')]
            wanted_hash = hashes[-1] if hashes else None
            if wanted_hash is None or wanted_hash != item.get('sha256'):
                self.lifecycle_errors.add(Fact('mail:filing:' + str(context.get('id')), 'unverified-source-hash', detail=canonical(source)))
            found = [{k: v for k, v in ref.items() if k != 'sha256'}
                     for refs in listing.get('mailboxes', {}).values() for ref in refs
                     if wanted_hash is not None and ref.get('sha256') == wanted_hash]
            scan = self.scan_result(key, listing)
            complete = wanted_hash is not None and scan is not None and bool(delivered(scan)) and scan_complete(self.servers, scan)
            if not complete:
                start = next((i for i, e in enumerate(self.servers) if e is listing), 0)
                observed = {(e['folder'], int(e['arguments'][0])) for e in self.servers[start + 1:]
                            if e['call'] == listing['call'] and e['command'] == 'FETCH' and e['accepted']}
                found = [ref for ref in found if (ref['folder'], ref['uid']) in observed]
            destination = origin.get('destination') if origin else None
            result.append({'source': item['source'], 'last_known_destination': destination,
                           'observed_locations': sorted(found, key=canonical), 'scan_complete': complete})
        return sorted(result, key=canonical)

    def last_filing_mutations(self):
        if getattr(self, '_filing_mutations_cache', None) is not None:
            return self._filing_mutations_cache
        result = {}
        for index, event in enumerate(self.servers):
            if event['command'] in {'MOVE', 'COPY', 'RENAME'}:
                source, _ = self.bound(event)
                result[event['call'], source] = index
        self._filing_mutations_cache = result
        return result

    def read_evidence(self, source, kind, sequence, calls=None, last_mutations=None):
        calls = calls if calls is not None else {c['call']: c for c in self.script}
        last_mutations = last_mutations if last_mutations is not None else self.last_filing_mutations() if kind != 'sent_copies' else {}
        context = self.warning_contexts.get(source, self.lifecycle_known.get(source, {}))
        indexed = getattr(self, '_evidence_index', None)
        candidates = indexed.get(('SENT', source) if kind == 'sent_copies' else ('LIST', context.get('account')), []) if indexed is not None else list(enumerate(self.servers))
        for index, evidence in reversed(candidates):
            call = calls.get(evidence['call'], {})
            before = evidence.get('before_seq')
            if (not isinstance(before, int) or not before < sequence <= call.get('end_seq', -1) or
                    not evidence.get('accepted') or evidence.get('reply') != 'delivered'):
                continue
            if kind == 'sent_copies' and evidence['command'] == 'SENT' and evidence.get('source') == source:
                return index, evidence
            if kind in {'filing', 'rename'} and evidence['command'] == 'LIST' and evidence.get('account') == context.get('account'):
                # A pre-command LIST is admission evidence, never the result
                # of the later filing. Commit outcome labels cannot choose
                # whether the post-command check was clean.
                mutations = [i for (call_id, key), i in last_mutations.items() if key == source]
                enrolled = source in evidence.get('check_sources', [])
                if mutations and index <= max(mutations) or not mutations and not enrolled:
                    continue
                if mutations and evidence['call'] != self.servers[max(mutations)]['call'] and not enrolled:
                    continue
                return index, evidence
        return None, None

    def clean_proof(self, source, kind, sequence):
        _, evidence = self.read_evidence(source, kind, sequence)
        return self.clean_evidence(source, kind, evidence)

    def clean_evidence(self, source, kind, evidence):
        if evidence is None or not evidence['accepted'] or evidence['reply'] != 'delivered':
            return False
        if kind == 'sent_copies':
            return len(evidence['identities']) <= 1
        old = next((json.loads(key[2]) for key in self.occurrences if key[0] == source and key[1] == kind), {})
        target, roles = old.get('target'), evidence.get('roles') or {}
        role_map = special_roles(roles) or {}
        complete = all(len(role_map.get(role, [])) == 1 for role in ('sent', 'drafts', 'trash'))
        protected = any(target == folder or target and (evidence.get('delimiters') or {}).get(folder, '/') and target.startswith(folder + (evidence.get('delimiters') or {}).get(folder, '/')) for role in ('trash', 'drafts', 'sent', 'junk', 'archive') for folder in role_map.get(role, []))
        if kind == 'rename' and any(flag.lower() in {'\\all', '\\flagged', '\\important'} for flag in roles.get(target, [])):
            protected = True
        failed_scan = any(e['call'] == evidence['call'] and e['command'] == 'FETCH' and not e['accepted'] for e in self.servers)
        if kind == 'filing':
            scan = self.scan_result(source, evidence)
            failed_scan |= scan is None or not delivered(scan) or not scan_complete(self.servers, scan)
            failed_scan |= any(e['command'] in {'MOVE', 'COPY'} and self.bound(e)[0] == source and
                               not e.get('copyuid_delivered') for e in self.servers)
        return target in roles and complete and not protected and not failed_scan

    def request_state(self, record, call):
        if record.locked:
            return {Fact('request', 'restore_required')}
        if record.prepared or len(record.fences) > max(record.committed, default=0):
            return {Fact('request', 'journal_incomplete')}
        if call.get('faults', {}).get('admission') == 'full':
            return {Fact('request', 'storage_limit')}
        return {Fact('request', 'allowed')}

    def holds(self, record):
        return self.hold_facts(self.lifecycle(record))

    def hold_facts(self, record):
        keys = set()
        for key, row in record.rows.items():
            if key.startswith(('op:', 'intent:', 'mail:filing:', 'mail:rename:', 'notice:')) and (row.get('check_open') or row.get('sent_copy_check', {}).get('state') == 'open' or key.startswith(('mail:filing:', 'mail:rename:')) and row.get('state') == 'started'):
                keys.add('check:' + key)
            if key.startswith('export:'):
                keys.add(key)
            if key.startswith('op:'):
                if row.get('repair_of') and row['state'] in {'reserved', 'submitting', 'unknown'}:
                    keys.add('settle:' + row['id'])
                elif row['state'] == 'reserved':
                    keys.add('cancel:' + row['id'])
        if record.locked:
            keys.add('restore')
            for fence in record.fences:
                for op in fence['operations']:
                    if 'op:' + op['id'] not in record.rows and 'archived:' + op['id'] not in record.rows and 'archived:' + op['id'] not in record.owner_rows and op.get('description', {}).get('action', '').endswith('_operation_repair'):
                        keys.add('settle:' + op['id'])
        return {Fact(key, 'held') for key in keys}

    def completion_errors(self, record):
        # Replaying later read-only check commits repeatedly asks the same
        # effect question. Cache within this replay only; every altered record
        # and new server event gets a fresh calculation. All field alterations
        # still reach the full shared comparison.
        operations = [(key, {field: row.get(field) for field in ('id', 'app', 'action', 'state', 'payload', 'repair_of')})
                      for key, row in record.rows.items() if key.startswith('op:')]
        for key, operation in record.rows.items():
            if key.startswith('op:') and operation.get('state') == 'done':
                self.payload_claims(key, operation)
        signature = (id(record.events), len(self.servers), len(self.script), canonical(operations), canonical(record.rows.get('testapp')))
        cache = getattr(self, '_completion_cache', {})
        if signature in cache:
            return set(cache[signature])
        errors = set()
        attempts = {}
        for event in self.servers:
            if event['command'] not in MUTATIONS or not event['accepted']:
                continue
            key, _ = self.bound(event)
            arguments = [event.get('url'), event.get('body')] if event['command'] == 'POST' else event.get('arguments')
            call = next((c for c in self.script if c['call'] == event['call']), {})
            signatures = [('intent', key)] if key else []
            signatures.append(('call', event['call']))
            for scope, binding in signatures:
                command_identity = [] if call.get('action') == 'mail_draft_save' else event.get('identities')
                signature = (scope, binding, event['command'], event.get('account'), event.get('folder'),
                             canonical(arguments), canonical(event.get('recipients')), canonical(command_identity),
                             event.get('stage'), event.get('append_flags'))
                attempts.setdefault(signature, []).append(event)
        for signature, events in attempts.items():
            if len(events) > 1:
                source = self.bound(events[0])[0] or 'call:' + str(events[0]['call'])
                errors.add(Fact(source, 'duplicate-effect', detail=signature[0] + ':' + signature[2]))
        for key, operation in record.rows.items():
            if not key.startswith('op:') or operation.get('state') != 'done':
                continue
            action = operation.get('action', '')
            self.payload_claims(key, operation)
            approved = self.approved(operation)
            if action == 'mail_send' or action == 'mail_unsubscribe' and operation.get('payload', {}).get('composition'):
                mid = '<' + operation['id'].replace(':', '.') + '@mail.aresos.invalid>'
                completed = next((e['seq'] for e in record.events if (e['set'].get(key) or {}).get('state') == 'done'), float('inf'))
                events = self.operation_events(key, completed)
                deliveries = [e for e in events if e['command'] == 'DATA' and delivered(e) and any(i.get('message_id') == mid for i in e['identities'])]
                mail = approved if approved is not None else operation.get('payload', {}).get('composition', {}).get('mail', {})
                recipients = sorted(address for _, address in getaddresses(mail.get('to', []) + mail.get('cc', []) + mail.get('bcc', [])))
                if deliveries and (len(deliveries) != 1 or sorted(deliveries[0].get('recipients', [])) != recipients):
                    errors.add(Fact(key, 'false-completion', detail='Accepted SMTP recipients differ from the full approved envelope'))
                if not deliveries:
                    errors.add(Fact(key, 'false-completion', detail='No matching accepted SMTP DATA'))
                for stage, proof in send_stages(mail, events, self.sent_policy(operation)).items():
                    if not proof:
                        errors.add(Fact(key, 'false-completion', detail='Approved local stage missing: ' + stage))
                for append in [e for e in events if e['command'] == 'APPEND']:
                    if deliveries and not sent_bytes_match(append, deliveries[0], mail):
                        errors.add(Fact(key, 'false-completion', detail='Sent APPEND bytes differ from DATA and approved Bcc variant'))
            elif action == 'mail_delete':
                payload = approved if approved is not None else operation.get('payload', {})
                command = 'MOVE' if payload.get('mode') == 'trash' else 'EXPUNGE'
                for target in payload.get('items', []):
                    reference = target['reference']
                    attempted = [e for e in self.servers if e['command'] == command and delivered(e) and
                        e.get('account') == reference.get('account') and e.get('folder') == reference['folder'] and
                        str((e.get('arguments') or [''])[0]) == str(reference['uid']) and
                        any({k: v for k, v in ref.items() if k != 'sha256'} == reference for ref in e.get('identities', []))]
                    if len(attempted) != 1:
                        errors.add(Fact(key, 'false-completion', detail='Exact deletion target not accepted once: ' + str(reference['uid'])))
                    elif command == 'MOVE':
                        roles = (special_roles(attempted[0].get('roles')) or {}).get('trash', [])
                        if len(roles) != 1 or attempted[0].get('arguments', ['', ''])[1].strip('"') != roles[0]:
                            errors.add(Fact(key, 'false-completion', detail='Deletion destination differs from the independently observed Trash role'))
                    elif command == 'EXPUNGE':
                        stop = self.servers.index(attempted[0])
                        marked = [e for e in self.servers[:stop] if delivered(e) and
                                  e['call'] == attempted[0]['call'] and exact_uid(e, reference, 'STORE', ['+FLAGS.SILENT', '(\\Deleted)'])]
                        if len(marked) != 1:
                            errors.add(Fact(key, 'false-completion', detail='Exact Deleted STORE missing before EXPUNGE: ' + str(reference['uid'])))
            elif action == 'mail_folder_delete':
                payload = approved if approved is not None else operation.get('payload', {})
                matches = [e for e in self.servers if e['command'] == 'DELETE' and e['accepted'] and
                           e.get('account') == payload.get('account') and e.get('arguments', [''])[0].strip('"') == payload.get('folder')]
                if len(matches) != 1:
                    errors.add(Fact(key, 'false-completion', detail='Approved folder DELETE not accepted exactly once'))
            elif action == 'mail_operation_repair':
                calls = [c for c in self.script if c['action'] == action and c.get('arguments', {}).get('operation_id') == operation.get('repair_of')]
                authority = self.repair_authority.get(key) or (calls[-1] if calls else None)
                stage = authority['arguments'].get('stage') if authority else None
                if authority is None and self.onboarding_call(key):
                    # Account setup's only internal repair is the Sent copy of
                    # its self-probe; require its exact parent Message-ID below.
                    stage = 'sent_copy'
                command = {'sent_copy': 'APPEND', 'answered_flag': 'STORE'}.get(stage)
                matches = [e for e in self.servers if e['command'] == command and e['accepted'] and
                           e['reply'] == 'delivered' and self.bound(e)[0] == key and
                           (not self.onboarding_call(key) or any(i.get('message_id') == '<' + str(operation.get('repair_of', '')).replace(':', '.') + '@mail.aresos.invalid>' for i in e.get('identities', [])))]
                settled = any(e['command'] == 'SENT' and e.get('source') == 'op:' + str(operation.get('repair_of')) and e['identities'] for e in self.servers)
                if not matches and not (stage == 'sent_copy' and settled):
                    errors.add(Fact(key, 'false-completion', detail='Approved repair stage lacks delivered effect or read-only settlement evidence'))
            elif action == 'testapp_send':
                payload = approved if approved is not None else operation.get('payload', {})
                for recipient in payload.get('to', []) + payload.get('cc', []) + payload.get('bcc', []):
                    accepted = [e for e in self.servers if e['command'] == 'RECEIVE' and e['accepted'] and recipient in e.get('recipients', []) and any(i.get('operation_id') == operation['id'] for i in e['identities'])]
                    if len(accepted) != 1:
                        errors.add(Fact(key, 'false-completion', detail='Receiver did not accept exactly once: ' + recipient))
                for stage in ('sent_copy', 'answered_flag'):
                    if not any(e['command'] == 'LOCAL_STAGE' and e['accepted'] and e['stage'] == stage and any(i.get('operation_id') == operation['id'] for i in e['identities']) for e in self.servers):
                        errors.add(Fact(key, 'false-completion', detail='Receiver stage missing: ' + stage))
            elif action == 'testapp_delete':
                current = record.rows.get('testapp', {}).get('items', {})
                for target in (approved if approved is not None else operation.get('payload', {})).get('items', []):
                    if target['reference']['id'] in current:
                        errors.add(Fact(key, 'false-completion', detail='Requested fixture item still exists: ' + target['reference']['id']))
            elif action == 'mail_unsubscribe':
                completed = next((e['seq'] for e in record.events if (e['set'].get(key) or {}).get('state') == 'done'), float('inf'))
                matches = []
                for command in self.servers:
                    if command['command'] != 'POST' or not command['accepted'] or command.get('reply') != 'delivered' or not 200 <= command.get('status', 0) < 300:
                        continue
                    call = next((c for c in self.script if c['call'] == command['call']), {})
                    if call.get('action') != action or call.get('arguments', {}).get('operation_id') != operation['id']:
                        continue
                    request = call['arguments'].get('description', {})
                    request = {**request, **request.get('untrusted_content', {})}
                    if (request.get('method') != 'POST' or request.get('body') != 'List-Unsubscribe=One-Click' or
                            request.get('target') != command.get('url') or request.get('reference') != (approved or {}).get('reference') or
                            command.get('body') != 'List-Unsubscribe=One-Click' or
                            not call.get('start_seq', -1) <= command.get('before_seq', -1) < completed <= call.get('end_seq', -1)):
                        continue
                    if self.bound(command)[0] == key:
                        matches.append(command)
                if len(matches) != 1:
                    errors.add(Fact(key, 'false-completion', detail='No exact correlated delivered POST before completion'))
        cache[signature] = set(errors)
        return errors

    def context_errors(self):
        errors = set()
        for call, ref, flags in missing_flag_commands(self.script, self.servers, getattr(self, 'validated_record', None)):
            errors.add(Fact('call:' + str(call), 'R2.STORE', detail=canonical({'missing': ref, 'flags': flags})))
        for index, event in enumerate(self.servers):
            if event['command'] not in MUTATIONS or event.get('fixture_seed'):
                continue
            _, missing = context_differences(event, self.script, self.servers, self.legacy_sources)
            if missing:
                errors.add(Fact('command:' + str(index), 'R2.' + event['command'], detail=canonical(missing)))
            if event['command'] == 'APPEND' and event.get('append_flags') == '(\\Seen)':
                mids = {ref.get('message_id') for ref in event.get('identities', [])}
                data = [e for e in self.servers[:index] if e['command'] == 'DATA' and
                        any(ref.get('message_id') in mids for ref in e.get('identities', []))]
                key, row = self.bound(event)
                original = (event.get('committed_before', {}).get('op:' + row['repair_of'], {}) if row and row.get('repair_of') else row) or {}
                if data and not sent_bytes_match(event, data[-1], self.approved(original) or {}):
                    errors.add(Fact('command:' + str(index), 'R2.APPEND', detail='script.command.sent-bytes'))
        if getattr(self, '_trace_validators', False):
            self._validator_proofs.setdefault('script_differences', set()).update(f for f in errors if 'script.' in f.detail)
        return errors

    def local_context_errors(self, record, after_sequence=0):
        errors = {Fact(source, kind, detail=detail) for source, kind, detail in local_errors(record, self.script, after_sequence, self.servers)}
        if getattr(self, '_trace_validators', False):
            self._validator_proofs.setdefault('local.errors', set()).update(errors)
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
