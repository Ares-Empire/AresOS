"""Independent decoder for AO19B4 owner facts and archive tombstones.

This module describes bytes and publication proofs. It grants no completion or
acknowledgement: model.py still requires script/server corroboration for those.
"""
import base64
import hashlib
import json
import re
from pathlib import Path
import struct
import zlib

from .records import canonical, fingerprint

MAGIC = b'AO19B4\0\n'
KINDS = {'context', 'resolution', 'check-open', 'check-result', 'acknowledgement'}
STATE = ('reserved', 'submitting', 'started', 'unknown', 'partial', 'done', 'failed', 'refused', 'open', 'checked', 'saved')


def stage_codes(stages):
    result = {}
    for name, outcome in stages.items():
        split = name.split(':', 1)
        if len(split) == 2 and split[0] in {'rcpt', 'recipient'}:
            name = split[0] + ':' + fingerprint(split[1])
        if isinstance(outcome, str) and (name in {'message_id', 'wire_sha256', 'sent_wire_sha256'} or re.fullmatch(r'[a-z0-9_:.-]{1,80}', outcome)):
            result[name] = outcome
        elif name == 'sent_copy_warning':
            match = re.search(r'Sent contains ([0-9]+) copies', str(outcome))
            result[name] = {'code': 'sent_copies', 'count': int(match[1]) if match else None}
        else:
            result[name] = {'code': 'detail', 'hash': fingerprint(outcome)}
    return result


FIELDS = set("id generation app action state expires notice ack context_version repair_of context roles_before check_open sent_copy_check warning_checks source_key check_kind evidence_fingerprint created_at onboarded ready qualification account source destination target references identities message_count locations roles special stage stages attempt_ended_at sent_append_started_at sent_append_ended_at repair_identity_missing untrusted_content reason path sha256 before events operations head checks size created_blob verb sources records observed_role roles_after unresolved_roles pages total_messages fragments".split())
OMIT = {'reason', 'question', 'text', 'html', 'subject', 'title', 'password', 'arguments', 'approval', 'payload', 'summary', 'body', 'raw'}
PREFIX = ('op:', 'intent:', 'export:', 'notice:', 'mail:filing:', 'mail:rename:', 'mail:filing-locations:', 'mail:account:', 'archived:', 'archive:')


def selected(key):
    return key in {'generation', 'restore_pending'} or key.startswith(PREFIX)


def strip(value, field=''):
    if isinstance(value, dict):
        return {k: strip(v, k) for k,v in value.items() if k not in OMIT}
    if isinstance(value, list):
        return [strip(v, field) for v in value]
    return fingerprint(value) if field == 'recipients' else value


def fact(key, value):
    if value is None or key in {'generation', 'restore_pending'}:
        return value
    row = {k: strip(v, k) for k,v in value.items() if k in FIELDS and k not in OMIT}
    if 'context' in row:
        recipients = value['context'].get('recipients', [])
        row['context']['recipients'] = [fingerprint(v) for v in recipients]
        row['context']['recipient_count'] = len(recipients)
    if 'reason' in value:
        row['reason_code'] = fingerprint(value['reason'])
        if value['reason'].endswith(' Missing local stages; repair without SMTP.'):
            row['reason_kind'] = 'smtp_partial_local' if value['reason'].startswith('Some recipients refused;') else 'smtp_local'
    if 'stages' in value:
        row['stages'] = stage_codes(value['stages'])
    return row


def publication(changes):
    return base64.b64encode(hashlib.sha256(canonical(changes).encode()).digest()).decode()


def archive_publication(evidence, run, entries):
    header = next(entry for entry in entries if entry.get('format') == 'aresos-history-1')
    closed = [entry['key'] for entry in entries if entry.get('key', '').startswith('op:')]
    manifest = {'path': str(Path(evidence) / 'archives' / run['name']), 'sha256': run['sha256'],
                'before': header['before'], 'events': sum('event' in entry for entry in entries),
                'operations': len(closed), 'head': header['head']['hash']}
    result = {key: None for key in closed}
    result.update({'archived:' + key[3:]: fact('archived:' + key[3:], {'seq': run['seq']}) for key in closed})
    result['archive:' + run['name']] = fact('archive:' + run['name'], manifest)
    check_key = 'intent:archive-' + run['name'][8:-6]
    verified = False
    for entry in entries:
        if check_key in entry.get('event', {}).get('set', {}):
            row = entry['event']['set'][check_key]
            verified = bool(row and not row.get('check_open'))
    if verified:
        result[check_key] = None
    return result


def identity(data, offset):
    kind = data[offset]
    if kind in (1, 2):
        length = 32 if kind == 1 else 16
        value = data[offset + 1:offset + length + 1].hex()
        return (value[:32] + ':' + value[32:] if kind == 1 else value), offset + length + 1
    if kind != 0:
        raise ValueError('Unknown owner identity encoding')
    length = data[offset + 1]
    return data[offset + 2:offset + length + 2].decode(), offset + length + 2


def acknowledgement(source, body, offset):
    kind = body[offset]
    if kind == 5:
        return 'recovery-' + source, offset + 1
    if kind == 6:
        return source, offset + 1
    if kind == 7:
        return source + '-' + body[offset + 1:offset + 17].hex(), offset + 17
    base = 'sent-' + fingerprint(source)[:32]
    if kind == 3:
        return base, offset + 1
    if kind == 4:
        return base + '-' + body[offset + 1:offset + 17].hex(), offset + 17
    if kind != 0:
        raise ValueError('Unknown acknowledgement encoding')
    prefix = body[offset + 1]
    tail, after = identity(body, offset + 2)
    return source[:prefix] + tail, after


def export(evidence, run):
    name = run['name']
    if Path(name).name != name:
        raise ValueError('Nonlocal owner export')
    raw = (Path(evidence) / 'archives' / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != run['sha256']:
        raise ValueError('Owner export hash mismatch')
    return [json.loads(line) for line in raw.splitlines()]


def decode(evidence, fences, committed):
    """Return selected facts, per-key sequences, and qualified full history."""
    fences = {row['seq']: row for row in fences}
    versions, history, runs, covered = [], {}, {}, set()
    path = Path(evidence) / 'owner-tombstones.bin'
    if path.exists():
        raw = path.read_bytes()
        if not raw.startswith(MAGIC):
            raise ValueError('Owner tombstone magic')
        offset, previous, run, rows, entries = len(MAGIC), bytes(32), None, {}, {}
        while offset < len(raw):
            header = raw[offset:offset + 2]
            if len(header) != 2:
                raise ValueError('Torn owner tombstone')
            size = int.from_bytes(header, 'big')
            body = raw[offset + 2:offset + 2 + size]
            chain = raw[offset + 2 + size:offset + 34 + size]
            if len(body) != size or len(chain) != 32:
                raise ValueError('Torn owner tombstone')
            if body[0] == 1:
                run = json.loads(body[1:])
                if run['seq'] not in committed:
                    raise ValueError('Unpublished owner archive run')
                rows, entries = {}, {}
                runs[run['name']] = run
                covered.add(run['seq'])
                archive_entries = export(evidence, run)
                if fences[run['seq']].get('owner') not in (None, publication(archive_publication(evidence, run, archive_entries))):
                    raise ValueError('Uncovered archive publication')
                for entry in archive_entries:
                    if 'event' in entry:
                        event = entry['event']
                        if event['record'] != fences[event['seq']]:
                            raise ValueError('Owner export fence mismatch')
                        if event['seq'] in committed:
                            history[event['seq']] = event
                            covered.add(event['seq'])
                            for key, value in event['set'].items():
                                rows[key], entries[key] = value, entry
                    elif 'key' in entry:
                        rows[entry['key']], entries[entry['key']] = entry['value'], entry
                binding = bytes.fromhex(fences[run['seq']]['hash'])
            elif body[0] == 5 and run is not None:
                prefix = ('op:', 'intent:', 'mail:filing:', 'mail:rename:', 'notice:')[body[1]]
                source, after = identity(body, 2)
                key = prefix + source
                state, count = body[after:after + 2]
                after += 2
                if count == 255:
                    count = int.from_bytes(body[after:after + 2], 'big')
                    after += 2
                acks = []
                for _ in range(count):
                    value, after = acknowledgement(source, body, after)
                    acks.append(value)
                if after != len(body) or key not in entries:
                    raise ValueError('Tombstone has no full export entry')
                value = rows[key]
                if value is not None and STATE[state] != value.get('state', 'done'):
                    raise ValueError('Tombstone state mismatch')
                changes = {key: None if prefix == 'op:' else value}
                if prefix == 'op:':
                    changes['archived:' + source] = {'seq': run['seq']}
                for ack in acks:
                    notice = rows.get('notice:' + ack)
                    implicit = prefix == 'op:' and ack == source and value and value.get('notice') and value.get('ack')
                    if not implicit and (notice is None or not notice.get('ack')):
                        raise ValueError('Unconfirmed owner acknowledgement')
                    if notice is not None:
                        changes['notice:' + ack] = notice
                versions.append((run['seq'], changes, True))
                binding = bytes.fromhex(fingerprint(entries[key]))
            else:
                raise ValueError('Unexpected tombstone record kind')
            expected = hashlib.sha256(previous + header + body + binding).digest()
            if chain != expected:
                raise ValueError('Owner tombstone chain mismatch')
            previous, offset = chain, offset + 34 + size
    path = Path(evidence) / 'owner-state.bin'
    if path.exists():
        raw = path.read_bytes()
        if not raw.startswith(MAGIC):
            raise ValueError('Owner projection magic')
        offset, previous, last = len(MAGIC), bytes(32), 0
        while offset < len(raw):
            if len(raw) - offset < 12:
                break
            header = raw[offset:offset + 12]
            size, seq = struct.unpack('>IQ', header)
            if size > 16 * 1024 * 1024 or seq < last:
                raise ValueError('Owner projection bound/order')
            if seq not in fences or len(raw) - offset < 44 + size:
                if seq in committed:
                    raise ValueError('Committed projection is torn')
                break
            payload, chain = raw[offset + 12:offset + 12 + size], raw[offset + 12 + size:offset + 44 + size]
            expected = hashlib.sha256(previous + header + payload + bytes.fromhex(fences[seq]['hash'])).digest()
            if chain != expected:
                raise ValueError('Owner projection chain mismatch')
            data = json.loads(zlib.decompress(payload))
            if any(set(row) != {'kind', 'facts'} or row['kind'] not in KINDS for row in data.values()):
                raise ValueError('Unexpected owner projection kind/fields')
            # The chain verifies the file bytes. The independent fence anchors
            # the complete source set; retirement may retain a covered subset.
            facts = {k: row['facts'] for k, row in data.items()}
            tag = base64.b64encode(hashlib.sha256(canonical(facts).encode()).digest()).decode()
            if fences[seq].get('owner') not in (None, tag):
                original = history.get(seq)
                full_facts = {k: fact(k,v) for k,v in original['set'].items() if selected(k)} if original else {}
                if (not original or publication(full_facts) != fences[seq]['owner'] or
                        any(k not in full_facts or value != full_facts[k] for k,value in facts.items())):
                    raise ValueError('Owner publication hash mismatch')
            if seq in committed:
                covered.add(seq)
                versions.append((seq, facts, False))
            previous, last, offset = chain, seq, offset + 44 + size
    missing = {seq for seq, record in fences.items() if seq in committed and record.get('owner')} - covered
    if missing:
        raise ValueError('Missing committed owner projection records')
    rows, sequences, full = {}, {}, set()
    for seq, changes, complete in sorted(versions, key=lambda row: row[0]):
        for key, value in changes.items():
            if value is None:
                rows.pop(key, None)
            else:
                rows[key] = value
            sequences[key] = seq
            if complete:
                full.add(key)
    return rows, sequences, history, full, {seq: changes for seq,changes,complete in versions if not complete}, [[seq, changes] for seq,changes,complete in versions if complete]
