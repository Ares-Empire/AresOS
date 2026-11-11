"""Selected owner facts, published by existing independent journal commits.

Only context, resolution, warning-check open/result, acknowledgement and
archive tombstones are recorded. Authored content and readable audit events
remain in the original working log and its hash-checked owner exports.
"""
import copy
from contextlib import contextmanager
import base64
import hashlib
import json
import os
import re
from pathlib import Path
import struct
import zlib

from .common import Refused, canonical, cleanup, digest, storage_stream, storage_refusal, visible

MAGIC = b'AO19B4\0\n'
HEADER = struct.Struct('>IQ')
KINDS = ('context', 'resolution', 'check-open', 'check-result', 'acknowledgement', 'tombstone')
STATES = {s: i for i, s in enumerate(('reserved', 'submitting', 'started', 'unknown',
          'partial', 'done', 'failed', 'refused', 'open', 'checked', 'saved'))}
PREFIXES = ('op:', 'intent:', 'export:', 'notice:', 'mail:filing:', 'mail:rename:',
            'mail:filing-locations:', 'mail:account:', 'archived:', 'archive:')
KEYS = {'generation', 'restore_pending'}
FIELDS = {'id', 'generation', 'app', 'action', 'state', 'expires', 'notice', 'ack',
          'context_version', 'repair_of', 'context', 'roles_before', 'check_open',
          'sent_copy_check', 'warning_checks', 'source_key', 'check_kind',
          'evidence_fingerprint', 'created_at', 'onboarded', 'ready', 'qualification',
          'account', 'source', 'destination', 'target', 'references', 'identities',
          'message_count', 'locations', 'roles', 'special', 'stage', 'stages',
          'attempt_ended_at', 'sent_append_started_at', 'sent_append_ended_at',
          'repair_identity_missing', 'untrusted_content', 'reason', 'path', 'sha256',
          'before', 'events', 'operations', 'head', 'checks', 'size', 'created_blob',
          'verb', 'sources', 'records', 'observed_role', 'roles_after', 'unresolved_roles',
          'pages', 'total_messages', 'fragments', 'sent_policy', 'safe_folder_delete'}
TEXT = {'reason', 'question', 'text', 'html', 'subject', 'title', 'password',
        'arguments', 'approval', 'payload', 'summary', 'body', 'raw'}


def selected(key):
    return key in KEYS or key.startswith(PREFIXES)


def facts(value, field=''):
    if isinstance(value, dict):
        return {k: facts(v, k) for k, v in value.items() if k not in TEXT}
    if isinstance(value, list):
        return [facts(v, field) for v in value]
    if field == 'recipients':
        return digest(value)
    return copy.deepcopy(value)


def fact(key, value):
    if value is None or key in KEYS:
        return copy.deepcopy(value)
    row = {k: facts(v, k) for k, v in value.items() if k in FIELDS and k not in TEXT}
    if 'context' in row:
        recipients = value['context'].get('recipients', [])
        row['context']['recipients'] = [digest(r) for r in recipients]
        row['context']['recipient_count'] = len(recipients)
    # Warning/reason strings are not a second readable-event journal. Retain a
    # fingerprint and a state code; the read path supplies conservative wording.
    if 'reason' in value:
        row['reason_code'] = digest(value['reason'])
        reason = value['reason']
        if reason.endswith(' Missing local stages; repair without SMTP.'):
            row['reason_kind'] = 'smtp_partial_local' if reason.startswith('Some recipients refused;') else 'smtp_local'
    if 'folder_delete_reason' in value:
        reason = value['folder_delete_reason']
        row['qualification_code'] = ('qualified' if reason.startswith('Qualified:') else
            'probe_missing' if 'did not survive' in reason else
            'exact_cleanup_failed' if 'Exact probe UID EXPUNGE cleanup failed' in reason else
            'empty_cleanup_failed' if 'Empty probe folder DELETE cleanup failed' in reason else
            'generic_cleaned' if 'Exact probe removed; empty folder retained' in reason else
            'survival_unverified' if 'could not be verified' in reason else 'unqualified')
    if 'stages' in value:
        row['stages'] = {}
        for name,outcome in value['stages'].items():
            key_parts = name.split(':', 1)
            if key_parts[0] in {'rcpt', 'recipient'} and len(key_parts) == 2:
                name = key_parts[0] + ':' + digest(key_parts[1])
            if isinstance(outcome, str) and (name in {'message_id', 'wire_sha256', 'sent_wire_sha256'} or re.fullmatch(r'[a-z0-9_:.-]{1,80}', outcome)):
                row['stages'][name] = outcome
            elif name == 'sent_copy_warning':
                count = re.search(r'Sent contains ([0-9]+) copies', str(outcome))
                row['stages'][name] = {'code': 'sent_copies', 'count': int(count[1]) if count else None}
            else:
                row['stages'][name] = {'code': 'detail', 'hash': digest(outcome)}
    return row


def packed_identity(value):
    """Common hexadecimal identities use bytes; unusual legacy ids stay exact."""
    compact = value.replace(':', '')
    if len(compact) in (32, 64) and all(c in '0123456789abcdef' for c in compact):
        return bytes([1 if ':' in value else 2]) + bytes.fromhex(compact)
    encoded = value.encode()
    if len(encoded) > 255:
        raise Refused('evidence_corrupt', 'Owner identity exceeds its format bound.')
    return b'\0' + bytes([len(encoded)]) + encoded


def packed_ack(source, identity):
    if identity == 'recovery-' + source:
        return b'\x05'
    if identity == source:
        return b'\x06'
    if identity.startswith(source + '-') and len(identity) == len(source) + 33:
        return b'\x07' + bytes.fromhex(identity[-32:])
    base = 'sent-' + digest(source)[:32]
    if identity == base:
        return b'\x03'
    if identity.startswith(base + '-') and len(identity) == len(base) + 33:
        return b'\x04' + bytes.fromhex(identity[-32:])
    common = 0
    while common < min(len(source), len(identity), 255) and source[common] == identity[common]:
        common += 1
    return b'\0' + bytes([common]) + packed_identity(identity[common:])


def unpack_ack(source, data, offset):
    kind = data[offset]
    if kind == 5:
        return 'recovery-' + source, offset + 1
    if kind == 6:
        return source, offset + 1
    if kind == 7:
        return source + '-' + data[offset + 1:offset + 17].hex(), offset + 17
    base = 'sent-' + digest(source)[:32]
    if kind == 3:
        return base, offset + 1
    if kind == 4:
        return base + '-' + data[offset + 1:offset + 17].hex(), offset + 17
    prefix = data[offset + 1]
    suffix, offset = unpack_identity(data, offset + 2)
    return source[:prefix] + suffix, offset


def unpack_identity(data, offset=0):
    kind = data[offset]
    if kind in (1, 2):
        size = 32 if kind == 1 else 16
        value = data[offset + 1:offset + 1 + size].hex()
        return (value[:32] + ':' + value[32:] if kind == 1 else value), offset + size + 1
    size = data[offset + 1]
    return data[offset + 2:offset + 2 + size].decode(), offset + size + 2


def record_kind(event, key, value):
    if value is None or not isinstance(value, dict):
        return 'resolution'
    action = event['action']
    if action.endswith('_notice_ack') and value.get('ack'):
        return 'acknowledgement'
    if action == 'mail_sent_copy_check_open' and key.startswith('op:'):
        return 'check-open'
    if action == 'mail_filing_check_open' and key.startswith(('mail:filing:', 'mail:rename:')):
        return 'check-open'
    if key.startswith(('mail:filing:', 'mail:rename:')) and value.get('state') == 'started' and value.get('context'):
        if key.startswith('mail:rename:') or not any(r.get('destination') for r in value.get('records', [])):
            return 'check-open'
    if key.startswith('intent:archive-'):
        return 'check-open' if value.get('check_open') and value.get('state') == 'started' else 'check-result'
    stage = event.get('untrusted_content', {}).get('stage', '')
    if (key.startswith('op:') and stage == 'smtp_data' and
            (event.get('untrusted_content', {}).get('outcome') == 'attempting' or not value.get('context')) and
            value.get('sent_copy_check', {}).get('state') == 'open'):
        return 'check-open'
    if action in {'mail_sent_copy_check', 'mail_filing_check'} or key.startswith('notice:') and value.get('check_kind'):
        return 'check-result'
    if key.startswith(('mail:filing:', 'mail:rename:')) and value.get('state') in {'done', 'partial'}:
        return 'check-result'
    if stage == 'sent_copy':
        return 'check-result'
    if value.get('state') in {'reserved', 'submitting', 'started'} or event.get('outcome') == 'started':
        return 'context'
    return 'resolution'


class OwnerProjection:
    def __init__(self, store):
        self.store = store
        self.path = store.evidence_dir / 'owner-state.bin'
        self.tombstones = store.evidence_dir / 'owner-tombstones.bin'
        self.previous = bytes(32)
        self._recover_tail()

    @contextmanager
    def read(self, path):
        stream = open(path, 'rb')
        try:
            yield stream
        finally:
            try:
                stream.close()
            except OSError as exc:
                # Verified bytes remain evidence when closing a read-only fd
                # fails. Report that storage cause without discarding facts.
                if storage_refusal(exc) is None:
                    raise
                self.store.observations.storage(exc)

    def journal_records(self):
        previous, count, committed = '', 0, 0
        with self.read(self.store.journal.name) as stream:
            for line in stream:
                if not line.endswith(b'\n'):
                    break
                record = json.loads(line)
                if 'commit' in record:
                    if record != {'commit': count, 'hash': previous}:
                        raise Refused('evidence_corrupt', 'Independent owner commit marker is damaged.')
                    committed = count
                    continue
                count += 1
                body = {k:v for k,v in record.items() if k != 'hash'}
                if record['seq'] != count or record['previous'] != previous or digest(body) != record['hash']:
                    raise Refused('evidence_corrupt', 'Independent owner publication chain is damaged.')
                previous = record['hash']
                yield record
        if committed < self.store.committed:
            raise Refused('evidence_corrupt', 'Independent owner publication history is missing.')

    def fence(self, seq):
        return next(r for r in self.journal_records() if r['seq'] == seq)

    def _fences(self):
        for record in self.journal_records():
            yield record['seq'], bytes.fromhex(record['hash']), record

    def _records(self, path, repair=False):
        with (storage_stream(open(path, 'r+b')) if repair else self.read(path)) as stream:
            if stream.read(len(MAGIC)) != MAGIC:
                raise Refused('evidence_corrupt', 'Owner projection format is damaged.')
            previous, last = bytes(32), 0
            fences = iter(self._fences())
            fence = next(fences, None)
            while True:
                offset = stream.tell()
                header = stream.read(HEADER.size)
                if not header:
                    return
                if len(header) != HEADER.size:
                    if repair:
                        stream.truncate(offset)
                        os.fsync(stream.fileno())
                    return
                length, seq = HEADER.unpack(header)
                if length > 16 * 1024 * 1024 or seq < last:
                    raise Refused('evidence_corrupt', 'Owner projection record bound/order is damaged.')
                payload, claimed = stream.read(length), stream.read(32)
                while fence and fence[0] < seq:
                    fence = next(fences, None)
                if len(payload) != length or len(claimed) != 32 or fence is None or fence[0] != seq:
                    if repair and seq > self.store.committed:
                        stream.truncate(offset)
                        os.fsync(stream.fileno())
                        return
                    if seq > self.store.committed:
                        return
                    raise Refused('evidence_corrupt', 'Owner projection has no complete journal fence.')
                expected = hashlib.sha256(previous + header + payload + fence[1]).digest()
                if claimed != expected:
                    raise Refused('evidence_corrupt', 'Owner projection chain is damaged.')
                try:
                    data = json.loads(zlib.decompress(payload))
                    record = fence[2]
                    if record.get('owner') and record['owner'] != self.publication_hash(data):
                        original = self.archived_event(seq)
                        full = {k: {'kind': record_kind(original, k, v), 'facts': fact(k, v)} for k,v in original['set'].items() if selected(k)} if original else {}
                        if (not original or record['owner'] != self.publication_hash(full) or
                                any(k not in full or row != full[k] for k,row in data.items())):
                            raise ValueError('owner publication hash')
                    if any(v['kind'] not in KINDS[:-1] for v in data.values()):
                        raise ValueError('record kind')
                except (ValueError, KeyError, TypeError, zlib.error) as exc:
                    raise Refused('evidence_corrupt', 'Owner projection payload is damaged.') from exc
                previous, last = claimed, seq
                yield seq, data, claimed, HEADER.size + length + 32

    def _recover_tail(self):
        self.previous = bytes(32)
        if not self.path.exists():
            if any(r.get('owner') for r in self.journal_records()):
                raise Refused('evidence_corrupt', 'Committed owner projection file is missing; owner recovery required.')
            self.store.ledger.admit(65536)
            self._new(self.path)
        for _, _, chain, _ in self._records(self.path, repair=True):
            self.previous = chain

    def _new(self, path):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with storage_stream(os.fdopen(fd, 'wb')) as stream:
            stream.write(MAGIC)
            stream.flush()
            os.fsync(stream.fileno())
        from .storage import sync_directory
        sync_directory(path.parent)

    def _append(self, path, seq, data, previous, fence=None):
        payload = zlib.compress(canonical(data).encode(), 9)
        header = HEADER.pack(len(payload), seq)
        if fence is None:
            fence = self.fence(seq)['hash']
        chain = hashlib.sha256(previous + header + payload + bytes.fromhex(fence)).digest()
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
        with storage_stream(os.fdopen(fd, 'ab', buffering=0)) as stream:
            encoded = header + payload + chain
            if stream.write(encoded) != len(encoded):
                raise OSError(28, 'Short owner projection write')
            os.fsync(stream.fileno())
        return chain

    @staticmethod
    def publication_hash(data):
        payload = {k: {'kind': row.get('kind', 'resolution'), 'facts': row['facts']} for k,row in data.items()}
        return base64.b64encode(hashlib.sha256(canonical(payload).encode()).digest()).decode()

    def archived_event(self, seq):
        seen = set()
        for run, _, _, _ in self.stones():
            if run['name'] in seen:
                continue
            seen.add(run['name'])
            for entry in self._export(run['name'], run['sha256']):
                if entry.get('event', {}).get('seq') == seq:
                    event = entry['event']
                    if event['record'] != self.fence(seq):
                        raise Refused('evidence_corrupt', 'Owner archive fence differs.')
                    return event
        return None

    @staticmethod
    def same(key, detailed, projected):
        return fact(key, detailed) == projected

    def changes(self, event):
        data = {}
        previous_rows = {}
        if event.get('restoring'):
            wanted = {key for key in event['set'] if selected(key)}
            # A restore batch has at most 32 source identities. Reconstruct
            # that bounded set together instead of rescanning once per key.
            for _, changes in self.records():
                previous_rows.update((key, value) for key, value in changes.items() if key in wanted)
        for key, value in event['set'].items():
            if not selected(key):
                continue
            old = self.store.get(key)
            new = fact(key, value)
            previous = previous_rows.get(key) if event.get('restoring') else fact(key, old)
            if new == previous and not (event['action'] in {'mail_sent_copy_check_open', 'mail_filing_check_open'} and key.startswith(('op:', 'mail:filing:', 'mail:rename:'))):
                continue
            kind = record_kind(event, key, value)
            data[key] = {'kind': kind, 'facts': new}
        if data:
            for key,value in event['set'].items():
                if selected(key) and key not in data:
                    data[key] = {'kind': record_kind(event, key, value), 'facts': fact(key,value)}
        return data

    def prepare(self, event, data=None):
        data = self.changes(event) if data is None else data
        if data:
            self.previous = self._append(self.path, event['seq'], data, self.previous, event['record']['hash'])

    def seed(self):
        if self.path.stat().st_size == len(MAGIC) and self.store.committed:
            if any(r.get('owner') for r in self.journal_records()):
                raise Refused('evidence_corrupt', 'Committed owner projection history is missing; owner recovery required.')
            data = {k: {'kind': 'context' if isinstance(v, dict) and v.get('context') else 'resolution',
                        'facts': fact(k, v)} for k, v in self.store.iter_items('') if selected(k)}
            self.store.ledger.admit(len(canonical(data).encode()) * 3 + 65536)
            if data:
                self.previous = self._append(self.path, self.store.committed, data, self.previous)

    def records(self):
        seen = set()
        for seq, data, _, _ in self._records(self.path):
            if seq <= self.store.committed:
                seen.add(seq)
                yield seq, {key: row['facts'] for key, row in data.items()}
        runs = {}
        for run, _, _, _ in self.stones():
            runs[run['name']] = run
        missing = {r['seq'] for r in self.journal_records() if r.get('owner') and r['seq'] <= self.store.committed} - seen
        for run in runs.values():
            missing.discard(run['seq'])
            for entry in self._export(run['name'], run['sha256']):
                if 'event' in entry:
                    event = entry['event']
                    fence = self.fence(event['seq'])
                    if event['record'] != fence:
                        raise Refused('evidence_corrupt', 'Owner export differs from the independent fence.')
                    missing.discard(event['seq'])
        if missing:
            raise Refused('evidence_corrupt', 'Committed owner projection history is missing; owner recovery required.')
        yield from self.retired()

    def iter_items(self, prefix=''):
        cursor = ''
        while True:
            batch = {}
            for _, changes in self.records():
                for key, value in changes.items():
                    if key <= cursor or not key.startswith(prefix):
                        continue
                    if key not in batch and len(batch) == 32:
                        largest = max(batch)
                        if key > largest:
                            continue
                        del batch[largest]
                    batch[key] = value
            if not batch:
                return
            for key in sorted(batch):
                if batch[key] is not None:
                    yield key, batch[key]
            cursor = max(batch)

    def open_epoch(self, key):
        epoch = None
        for seq, data, _, _ in self._records(self.path):
            if seq > self.store.committed or key not in data:
                continue
            row = data[key]
            value = row['facts'] or {}
            if row['kind'] == 'check-open':
                epoch = seq
            if row['kind'] == 'check-result' or key.startswith('op:') and value.get('sent_copy_check', {}).get('state') != 'open':
                epoch = None
        return epoch

    def audit(self):
        # The independent fence still proves each commit's existence and exact
        # operation identities. Owner facts supply its structured source data;
        # SQLite-only audit prose is explicitly replaced by generated wording.
        active = iter(self._records(self.path))
        current = next(active, None)
        for fence in self.journal_records():
            seq = fence['seq']
            if seq > self.store.committed:
                break
            while current and current[0] < seq:
                current = next(active, None)
            sources = {k: row['facts'] for k,row in current[1].items()} if current and current[0] == seq else {}
            yield {'seq': seq, 'time': fence['time'], 'action': 'control_owner_state',
                   'summary': 'Committed owner facts; SQLite audit detail is unavailable.',
                   'outcome': 'done', 'operation_id': None,
                   'untrusted_content': visible({'operations': [op['id'] for op in fence['operations']],
                                         'sources': sources}), 'set': sources}

    def _export(self, name, checksum):
        if Path(name).name != name:
            raise Refused('evidence_corrupt', 'Owner tombstone export identity is damaged.')
        path = self.store.evidence_dir / 'archives' / name
        actual = hashlib.sha256()
        try:
            with self.read(path) as stream:
                for block in iter(lambda: stream.read(65536), b''):
                    actual.update(block)
            if actual.hexdigest() != checksum:
                raise ValueError('archive checksum')
            with self.read(path) as stream:
                for line in stream:
                    yield json.loads(line)
        except (OSError, ValueError) as exc:
            raise Refused('evidence_corrupt', 'Owner tombstone archive is missing or damaged.') from exc

    def _archive_rows(self, name, checksum):
        rows, entries, coverage = {}, {}, {}
        for entry in self._export(name, checksum):
            if 'event' in entry:
                for key, value in entry['event']['set'].items():
                    rows[key], entries[key] = value, entry
                    coverage.setdefault(key, set()).add(entry['event']['seq'])
            elif 'key' in entry:
                rows[entry['key']], entries[entry['key']] = entry['value'], entry
        return rows, entries, coverage

    def verify_publication(self, run):
        header, event_count, closed, verified = None, 0, [], False
        check_key = 'intent:archive-' + run['name'][8:-6]
        for entry in self._export(run['name'], run['sha256']):
            if entry.get('format') == 'aresos-history-1':
                header = entry
            elif 'event' in entry:
                event_count += 1
                if check_key in entry['event']['set']:
                    row = entry['event']['set'][check_key]
                    verified = bool(row and not row.get('check_open'))
            elif entry.get('key', '').startswith('op:'):
                closed.append(entry['key'])
        if header is None:
            raise Refused('evidence_corrupt', 'Owner archive header is missing.')
        manifest = {'path': str(self.store.evidence_dir / 'archives' / run['name']),
                    'sha256': run['sha256'], 'before': header['before'],
                    'events': event_count, 'operations': len(closed), 'head': header['head']['hash']}
        data = {key: {'facts': None} for key in closed}
        data.update({'archived:' + key[3:]: {'facts': fact('archived:' + key[3:], {'seq': run['seq']})}
                     for key in closed})
        data['archive:' + run['name']] = {'facts': fact('archive:' + run['name'], manifest)}
        if verified:
            data[check_key] = {'facts': None}
        fence = self.fence(run['seq'])
        if fence.get('owner') and fence['owner'] != self.publication_hash(data):
            raise Refused('evidence_corrupt', 'Archive publication has uncovered owner facts.')

    def stones(self, path=None):
        path = path or self.tombstones
        if not path.exists():
            return
        with self.read(path) as stream:
            if stream.read(len(MAGIC)) != MAGIC:
                raise Refused('evidence_corrupt', 'Owner tombstone format is damaged.')
            previous, run, entries = bytes(32), None, {}
            while header := stream.read(2):
                try:
                    if len(header) != 2:
                        raise ValueError('length')
                    length = int.from_bytes(header, 'big')
                    body, chain = stream.read(length), stream.read(32)
                    if len(body) != length or len(chain) != 32:
                        raise ValueError('incomplete tombstone')
                    if body[0] == 1:  # Archive run's shared resolution record.
                        run = json.loads(body[1:])
                        self.verify_publication(run)
                        rows, entries, _ = self._archive_rows(run['name'], run['sha256'])
                        binding = bytes.fromhex(self.fence(run['seq'])['hash'])
                        stone = None
                    elif body[0] == 5 and run is not None:
                        source, offset = unpack_identity(body, 2)
                        key = ('op:', 'intent:', 'mail:filing:', 'mail:rename:', 'notice:')[body[1]] + source
                        state, count = body[offset:offset + 2]
                        offset += 2
                        if count == 255:
                            count = int.from_bytes(body[offset:offset + 2], 'big')
                            offset += 2
                        acknowledgements = []
                        for _ in range(count):
                            identity, offset = unpack_ack(source, body, offset)
                            acknowledgements.append(identity)
                        if offset != len(body) or key not in entries:
                            raise ValueError('uncovered tombstone')
                        binding = bytes.fromhex(digest(entries[key]))
                        value = rows[key]
                        if value is not None and STATES.get(value.get('state'), 5) != state:
                            raise ValueError('final state')
                        for identity in acknowledgements:
                            implicit = key.startswith('op:') and identity == source and value and value.get('notice') and value.get('ack')
                            if not implicit and not (rows.get('notice:' + identity) or {}).get('ack'):
                                raise ValueError('acknowledgement')
                        stone = {'key': key, 'state': state, 'ack': acknowledgements, 'value': value, 'rows': rows}
                    else:
                        raise ValueError('record kind')
                    expected = hashlib.sha256(previous + header + body + binding).digest()
                    if chain != expected:
                        raise ValueError('chain')
                    previous = chain
                except (ValueError, KeyError, IndexError, TypeError) as exc:
                    raise Refused('evidence_corrupt', 'Owner tombstone entry is damaged or missing from its export.') from exc
                yield run, stone, chain, len(body) + 34

    def retired(self, full=False):
        for run, stone, _, _ in self.stones():
            if stone is None:
                continue
            key, value = stone['key'], stone['value']
            changes = {key: None if key.startswith('op:') else value}
            if key.startswith('op:'):
                changes['archived:' + key[3:]] = {'seq': run['seq']}
            for identity in stone['ack']:
                if 'notice:' + identity in stone['rows']:
                    changes['notice:' + identity] = stone['rows']['notice:' + identity]
            yield run['seq'], changes if full else {k: fact(k, v) for k, v in changes.items()}

    def compact(self):
        active = list(self._records(self.path))
        required = {}
        for seq, data, _, _ in active:
            if seq > self.store.committed:
                raise Refused('journal_incomplete', 'Unpublished owner facts cannot be retired.')
            for key in data:
                required.setdefault(key, set()).add(seq)
        notices = self.store.items('notice:')
        available = {}
        for key, manifest in self.store.items('archive:'):
            name = key[8:]
            rows, entries, coverage = self._archive_rows(name, manifest['sha256'])
            for source in required:
                if not source.startswith(('op:', 'intent:', 'mail:filing:', 'mail:rename:', 'notice:')) or source not in rows:
                    continue
                value = rows[source]
                current = self.store.get(source)
                archived = source.startswith('op:') and current is None and self.store.get('archived:' + source[3:])
                covered = coverage.get(source, set()) | ({archived['seq']} if archived else set())
                verification_key = 'intent:archive-' + name[8:-6]
                if source == verification_key and current is None:
                    covered.add(self.store.committed)
                if not required[source] <= covered:
                    continue
                if current is not None and (value != current or current.get('check_open') or
                        current.get('sent_copy_check', {}).get('state') == 'open' or
                        current.get('state') in {'started', 'reserved', 'submitting', 'partial', 'unknown'} or
                        current.get('notice') and not current.get('ack') or source.startswith('notice:') and not current.get('ack')):
                    continue
                if any(not n.get('ack') and (n.get('source_key') == source or
                        n.get('untrusted_content', {}).get('operation_id') == source[3:]) for _, n in notices):
                    continue
                available[source] = (name, manifest, rows, entries)
        if not available:
            return
        existing = {stone['key'] for _, stone, _, _ in self.stones() if stone}
        retired_keys = set(available)
        for source, (name, _, _, _) in available.items():
            retired_keys.add('archive:' + name)
            if source.startswith('op:'):
                retired_keys.add('archived:' + source[3:])
        groups = {}
        for source, record in available.items():
            if source not in existing and not source.startswith('intent:archive-'):
                groups.setdefault(record[0], []).append(source)
        temporary = self.path.with_suffix('.partial')
        stone_temp = self.tombstones.with_suffix('.partial')
        self.store.ledger.admit(self.path.stat().st_size * 3 + (self.tombstones.stat().st_size if self.tombstones.exists() else 0) + 65536)
        from .storage import sync_directory
        try:
            self._new(stone_temp)
            if self.tombstones.exists():
                stone_temp.write_bytes(self.tombstones.read_bytes())
            previous = bytes(32)
            for _, _, chain, _ in self.stones(stone_temp):
                previous = chain
            with storage_stream(open(stone_temp, 'ab', buffering=0)) as stream:
                def emit(body, binding):
                    nonlocal previous
                    header = len(body).to_bytes(2, 'big')
                    previous = hashlib.sha256(previous + header + body + binding).digest()
                    encoded = header + body + previous
                    if stream.write(encoded) != len(encoded):
                        raise OSError(28, 'Short owner tombstone write')
                for name, sources in groups.items():
                    _, manifest, rows, entries = available[sources[0]]
                    run = {'name': name, 'sha256': manifest['sha256'], 'seq': self.store.committed}
                    emit(b'\1' + canonical(run).encode(), bytes.fromhex(self.fence(self.store.committed)['hash']))
                    associated = {}
                    for source in sources:
                        associated[source] = [n['id'] for _, n in notices if n.get('ack') and (n.get('source_key') == source or n.get('untrusted_content', {}).get('intent_key') == source or source.startswith('op:') and n.get('untrusted_content', {}).get('operation_id') == source[3:]) and 'notice:' + n['id'] in rows]
                    children = {'notice:' + n for ids in associated.values() for n in ids}
                    for source in sorted(set(sources) - children):
                        prefix, identity = next((p, source[len(p):]) for p in ('op:', 'intent:', 'mail:filing:', 'mail:rename:', 'notice:') if source.startswith(p))
                        kind = ('op:', 'intent:', 'mail:filing:', 'mail:rename:', 'notice:').index(prefix)
                        value = rows[source]
                        state = STATES.get((value or {}).get('state'), 5)
                        acks = list(associated[source])
                        if prefix == 'op:' and value and value.get('notice') and value.get('ack'):
                            acks.append(identity)
                        if prefix == 'notice:' and value and value.get('ack'):
                            acks = [value['id']]
                        count = bytes([len(acks)]) if len(acks) < 255 else b'\xff' + len(acks).to_bytes(2, 'big')
                        body = bytes([5, kind]) + packed_identity(identity) + bytes([state]) + count
                        for ack in sorted(acks):
                            body += packed_ack(identity, ack)
                        emit(body, bytes.fromhex(digest(entries[source])))
                os.fsync(stream.fileno())
            list(self.stones(stone_temp))
            os.replace(stone_temp, self.tombstones)
            sync_directory(self.store.evidence_dir)
            self._new(temporary)
            previous = bytes(32)
            for seq, data, _, _ in active:
                live = {k: v for k, v in data.items() if k not in retired_keys}
                if live:
                    previous = self._append(temporary, seq, live, previous)
            os.replace(temporary, self.path)
            sync_directory(self.store.evidence_dir)
            self.previous = previous
        finally:
            with cleanup('owner projection retirement temporary cleanup'):
                temporary.unlink(missing_ok=True)
                stone_temp.unlink(missing_ok=True)
