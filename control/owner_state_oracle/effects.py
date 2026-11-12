"""Effect plans selected by scripted arguments and independent server evidence."""
from email.parser import BytesParser
from email.utils import getaddresses
import hashlib
import re
from .context import identity, special_roles, flag_operations, rename_destination


def description(call):
    value = call.get('arguments', {}).get('description', {})
    return {**value, **value.get('untrusted_content', {})}


def delivered(event):
    return event.get('accepted') and event.get('reply') == 'delivered'


def body_fetched(event, reference):
    if not (event['command'] == 'FETCH' and delivered(event) and
            event.get('folder') == reference['folder'] and
            event.get('arguments') == [str(reference['uid']), '(UID FLAGS BODY.PEEK[])']):
        return False
    for row in event.get('fetch_result', []):
        if not isinstance(row, dict) or 'literal_hex' not in row:
            continue
        metadata, literal = bytes.fromhex(row['metadata_hex']), bytes.fromhex(row['literal_hex'])
        if re.search(rb'\bUID ' + str(reference['uid']).encode() + rb'\b', metadata) and (
                not reference.get('sha256') or hashlib.sha256(literal).hexdigest() == reference['sha256']):
            return True
    return False


def scan_complete(servers, result):
    """A scan is complete only if the wire replies contain every message body."""
    start = result.get('scan_start')
    if not isinstance(start, int) or start < 0:
        return False
    stop = next((i for i, event in enumerate(servers) if event is result), len(servers))
    events = [e for e in servers[start:stop] if e['call'] == result['call'] and e.get('account') == result.get('account')]
    listing = next((e for e in events if e['command'] == 'LIST' and delivered(e)), None)
    if listing is None or not isinstance(listing.get('roles'), dict):
        return False
    for name, flags in (listing.get('roles') or {}).items():
        if any(flag.lower() == '\\noselect' for flag in flags):
            continue
        searches = [e for e in events if e['command'] == 'SEARCH' and e.get('folder') == name and
                    e.get('arguments') == [None, 'ALL'] and delivered(e)]
        if not searches:
            return False
        search = searches[-1]
        index = next(i for i, e in enumerate(events) if e is search)
        if not any(e['command'] == 'SELECT' and e.get('folder') == name and delivered(e) for e in events[:index]):
            return False
        # LIST establishes names/roles only. Mail can arrive before SEARCH;
        # the recorder captures the independent inventory at each command.
        refs = search.get('identities')
        if not isinstance(refs, list):
            return False
        values = search.get('response_text', [])
        if len(values) != 1 or not isinstance(values[0], str) or not all(part.isdigit() for part in values[0].split()):
            return False
        if sorted(map(int, values[0].split())) != sorted(ref['uid'] for ref in refs):
            return False
        if not all(any(body_fetched(e, ref) for e in events[index + 1:]) for ref in refs):
            return False
    return True


def exact_uid(event, reference, command, flags=None):
    return (event['command'] == command and event.get('account') == reference.get('account') and
            event.get('folder') == reference.get('folder') and
            event.get('arguments') == [str(reference.get('uid')), *(flags or [])] and
            identity(reference) in [identity(ref) for ref in event.get('identities', [])])


def role_append(event, role, flags):
    names = (special_roles(event.get('roles')) or {}).get(role, [])
    return event['command'] == 'APPEND' and len(names) == 1 and event.get('folder') == names[0] and event.get('append_flags') == flags


def send_stages(approved, events, policy='client'):
    sent = any(delivered(e) and (role_append(e, 'sent', '(\\Seen)') and policy == 'client' or
               e['command'] == 'SENT' and e.get('identities') and
               e.get('folder') in (special_roles(e.get('roles')) or {}).get('sent', [])) for e in events)
    ref = approved.get('answered_reference')
    answered = not ref or any(delivered(e) and exact_uid(e, ref, 'STORE', ['+FLAGS.SILENT', '(\\Answered)']) for e in events)
    return {'sent_copy': sent, 'answered_flag': answered}


def free_plan(call):
    args, action = call.get('arguments', {}), call.get('action')
    if action == 'mail_flag':
        return [{'command': 'STORE', 'reference': ref, 'flags': flags}
                for ref in args.get('references', []) for flags in flag_operations(args)]
    if action == 'mail_draft_save':
        return [{'command': 'APPEND', 'account': args.get('account'), 'role': 'drafts', 'flags': '(\\Draft)'}]
    if action == 'mail_folder_create':
        return [{'command': 'CREATE', 'account': args.get('account'), 'arguments': [args.get('name')]}]
    if action == 'mail_folder_rename':
        return [{'command': 'RENAME', 'account': args.get('account'), 'rename': args}]
    if action == 'mail_folder_delete':
        approved = description(call)
        return [{'command': 'DELETE', 'account': approved.get('account'), 'arguments': [approved.get('folder')]}]
    return None


def matches(effect, event):
    if event['command'] != effect['command']:
        return False
    if 'reference' in effect:
        return exact_uid(event, effect['reference'], effect['command'], effect['flags'])
    if effect.get('account') and event.get('account') != effect['account']:
        return False
    if 'role' in effect:
        return role_append(event, effect['role'], effect['flags'])
    if 'rename' in effect:
        return [arg.strip('"') for arg in event.get('arguments', [])] == [effect['rename'].get('folder'), rename_destination(effect['rename'], event)]
    return [arg.strip('"') for arg in event.get('arguments', [])] == effect.get('arguments')


def complete_plan(plan, events):
    return plan is not None and all(sum(delivered(e) and matches(effect, e) for e in events) == 1 for effect in plan)


def sent_bytes_match(append, data, approved):
    if not append.get('raw_hex') or not data.get('raw_hex'):
        return True  # Legacy unit inputs predate raw byte recording.
    sent, wire = bytes.fromhex(append['raw_hex']), bytes.fromhex(data['raw_hex'])
    if sent == wire:
        return True
    header, separator, body = sent.partition(b'\r\n\r\n')
    parsed = BytesParser().parsebytes(header + separator, headersonly=True)
    bcc = [address for _, address in getaddresses(parsed.get_all('Bcc', []))]
    expected = [address for _, address in getaddresses(approved.get('bcc', []))]
    stripped = re.sub(rb'(?im)^Bcc:[^\r\n]*(?:\r\n[ \t][^\r\n]*)*\r\n', b'', header + b'\r\n')
    return bool(expected) and bcc == expected and stripped + b'\r\n' + body == wire
