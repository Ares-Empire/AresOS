"""Expectations from calls, server evidence and committed local transitions only."""
from dataclasses import dataclass
import copy
import hashlib
from .records import canonical


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

    def call(self, action, arguments, clock, faults=()):
        self.call_id += 1
        self.script.append({'call': self.call_id, 'action': action, 'arguments': copy.deepcopy(arguments),
                            'clock': clock, 'faults': copy.deepcopy(faults), 'reply': 'pending'})
        return self.call_id

    def reply(self, value, delivered=True):
        self.script[-1].update(reply='delivered' if delivered else 'lost', result=copy.deepcopy(value))

    def server(self, command, account=None, folder=None, identities=(), roles=None,
               accepted=True, reply='delivered', **extra):
        event = {'call': self.call_id, 'command': command, 'account': account, 'folder': folder,
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
        if key not in self.occurrences:
            matches = [n for k, n in record.rows.items() if k.startswith('notice:') and
                       n.get('source_key') == source and n.get('check_kind') == kind and
                       n['id'] not in self.occurrences.values()]
            self.occurrences[key] = matches[-1]['id'] if matches else 'uncommitted:' + hashlib.sha256(canonical(key).encode()).hexdigest()[:24]
        detail = {'count': len(evidence)} if kind == 'sent_copies' else {'role': evidence.get('role', 'ordinary')}
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
        for key, row in record.rows.items():
            if key.startswith('op:'):
                if app is None or row['app'] == app:
                    if row['state'] in {'reserved', 'submitting', 'partial', 'unknown'} or (row.get('notice') and 'operation:' + row['id'] not in self.acknowledged):
                        facts.add(Fact(key, 'pending', detail=row['state']))
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
        # Every observed warning survives changed evidence/clean/action end,
        # until that occurrence has its own committed acknowledgement.
        for event in self.servers[self.processed_server:]:
            if event['command'] == 'WARNING':
                self.detected.add(self.warning(event['source'], event['kind'], event['evidence'], record))
            elif event['command'] == 'SENT' and len(event['identities']) > 1:
                self.detected.add(self.warning(event['source'], 'sent_copies', sorted(event['identities'], key=canonical), record))
        self.processed_server = len(self.servers)
        facts.update(f for f in self.detected if f.occurrence not in self.acknowledged and
                     (app is None or app == 'mail'))
        return facts

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
