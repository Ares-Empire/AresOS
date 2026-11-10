"""Effect plans selected by scripted arguments and independent server evidence."""
from email.parser import BytesParser
from email.utils import getaddresses
import re
from .context import identity, special_roles, flag_operations


def description(call):
    value = call.get('arguments', {}).get('description', {})
    return {**value, **value.get('untrusted_content', {})}


def delivered(event):
    return event.get('accepted') and event.get('reply') == 'delivered'


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
        return [{'command': 'RENAME', 'account': args.get('account'), 'arguments': [args.get('folder'), args.get('name')]}]
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
