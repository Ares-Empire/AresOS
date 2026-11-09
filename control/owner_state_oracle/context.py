"""Exact pre-command context, decoded from documented records and raw commands."""
from email.utils import getaddresses

ROLES = ('sent', 'drafts', 'trash', 'junk', 'archive')
UID_COMMANDS = {'MOVE', 'COPY', 'STORE', 'EXPUNGE'}
MUTATIONS = UID_COMMANDS | {'DATA', 'APPEND', 'CREATE', 'DELETE', 'RENAME', 'POST', 'RECEIVE'}


def special_roles(value):
    if not isinstance(value, dict):
        return None
    if 'special' in value:
        return {role: [value['special'][role]] for role in ROLES if value['special'].get(role)}
    if any(role in value for role in ROLES):
        return {role: sorted(v if isinstance(v, list) else [v]) for role, v in value.items() if role in ROLES and v}
    return {role: sorted(name for name, flags in value.items() if isinstance(flags, list) and '\\' + role in [flag.lower() for flag in flags])
            for role in ROLES if any(isinstance(flags, list) and '\\' + role in [flag.lower() for flag in flags] for flags in value.values())}


def identity(value):
    return {key: value[key] for key in ('account', 'folder', 'uidvalidity', 'uid', 'message_id', 'operation_id') if key in value}


def call_for(event, script):
    return next((call for call in script if call['call'] == event['call']), {})


def bind(event, script):
    """A prior attempt, another account or a completed row cannot stand in."""
    rows = event.get('committed_before', {})
    call = call_for(event, script)
    args, action = call.get('arguments', {}), call.get('action', '')
    operation_id = args.get('operation_id')
    start = event.get('call_start_seq', -1)
    created = event.get('created_before', {})
    command = event['command']
    candidates = []
    for key, row in rows.items():
        if not isinstance(row, dict) or row.get('state') not in {'started', 'submitting'}:
            continue
        if key.startswith('op:'):
            own = row.get('id') == operation_id
            repair = action.endswith('_operation_repair') and row.get('repair_of') == operation_id
            internal = operation_id is None and created.get(key, -1) > start
            if own or repair or internal:
                candidates.append((key, row))
        elif key.startswith(('mail:filing:', 'mail:rename:')):
            if created.get(key, -1) <= start or row.get('account') != event.get('account'):
                continue
            target = (event.get('arguments') or ['', ''])[-1].strip('"')
            if row.get('target') == target and ((command == 'RENAME') == key.startswith('mail:rename:')):
                candidates.append((key, row))
        elif key.startswith('intent:') and created.get(key, -1) > start:
            context = row.get('context', {})
            if operation_id is not None and context.get('operation_id') != operation_id:
                continue
            if row.get('action') == action or context.get('command') == command:
                candidates.append((key, row))
    # Current explicit filing/rename identity is stronger than its outer generic
    # change marker. Operation dependencies are followed only from the bound id.
    explicit = [pair for pair in candidates if pair[0].startswith(('mail:filing:', 'mail:rename:'))]
    candidates = explicit or candidates
    if len(candidates) != 1:
        return None, None
    return candidates[0]


def decode(row, key, rows, command):
    if row is None:
        return {}
    if isinstance(row.get('context'), dict):
        return row['context']
    original = row
    if row.get('repair_of'):
        original = rows.get('op:' + row['repair_of'], {})
    payload = original.get('payload', {})
    mail = payload.get('composition', {}).get('mail', {})
    account = row.get('account') or payload.get('account') or mail.get('account')
    refs = row.get('sources') or [item['reference'] for item in payload.get('items', [])]
    roles = row.get('roles_before') or original.get('roles_before')
    account = account or (refs[0].get('account') if refs else None)
    result = {'account': account, 'roles': special_roles(roles), 'identities': [identity(ref) for ref in refs]}
    if key.startswith('mail:filing:'):
        result.update(command=row.get('verb', '').upper(), source=refs[0]['folder'] if refs else None,
                      destination=row.get('target'))
    elif key.startswith('mail:rename:'):
        result.update(command='RENAME', source=row.get('source'), destination=row.get('target'))
    elif command in UID_COMMANDS:
        result.update(command=command, source=refs[0]['folder'] if refs else None)
        if command == 'MOVE' and payload.get('mode') == 'trash':
            result['destination'] = (result['roles'] or {}).get('trash', [None])[0]
        if command == 'STORE' and payload.get('mode') == 'permanent':
            result['flags'] = ['+FLAGS.SILENT', '(\\Deleted)']
    elif command in {'CREATE', 'DELETE'}:
        result.update(command=command, source=payload.get('folder') if command == 'DELETE' else None,
                      destination=payload.get('folder'))
    elif command in {'DATA', 'APPEND'} and mail:
        mid = '<' + original['id'].replace(':', '.') + '@mail.aresos.invalid>'
        result.update(command=command, identities=[{'message_id': mid}],
                      sha256=original.get('stages', {}).get('sent_wire_sha256' if command == 'APPEND' and original.get('stages', {}).get('sent_wire_sha256') else 'wire_sha256'),
                      recipients=[address for _, address in getaddresses(mail.get('to', []) + mail.get('cc', []) + mail.get('bcc', []))],
                      source=getaddresses([mail.get('from', '')])[0][1] if command == 'DATA' else 'local',
                      destination='smtp' if command == 'DATA' else (result['roles'] or {}).get('sent', [None])[0])
    elif command == 'POST':
        result.update(command='POST', source=payload.get('reference'), destination=payload.get('target'), body=payload.get('body'))
    elif command == 'RECEIVE':
        result.update(command='RECEIVE', account=payload.get('account'), source='fixture', destination='receiver',
                      identities=[{'operation_id': original.get('id')}],
                      recipients=payload.get('to', []) + payload.get('cc', []) + payload.get('bcc', []))
    return result


def required(event, script):
    command, args = event['command'], event.get('arguments', [])
    result = {'command': command, 'account': event.get('account')}
    if result['account'] != 'fixture':
        result['roles'] = special_roles(event.get('roles'))
    if command in UID_COMMANDS:
        uid = int(args[0])
        result.update(source=event.get('folder'), identities=[identity(ref) for ref in event['identities'] if ref.get('uid') == uid])
        if command in {'MOVE', 'COPY'}:
            result['destination'] = args[1].strip('"')
        if command == 'STORE':
            result['flags'] = list(args[1:])
    elif command == 'RENAME':
        result.update(source=args[0].strip('"'), destination=args[1].strip('"'), identities=[identity(ref) for ref in event['identities']])
    elif command in {'CREATE', 'DELETE'}:
        result.update(source=args[0].strip('"') if command == 'DELETE' else None, destination=args[0].strip('"'), identities=[])
    elif command in {'DATA', 'APPEND'}:
        result.update(identities=[{'message_id': ref.get('message_id')} for ref in event['identities']],
                      sha256=event.get('raw_sha256') or (event['identities'][0].get('sha256') if event['identities'] else None),
                      source=event.get('sender') if command == 'DATA' else 'local',
                      destination='smtp' if command == 'DATA' else event.get('folder'))
        if command == 'DATA':
            result['recipients'] = event.get('intended_recipients', event.get('recipients', []))
    elif command == 'POST':
        call = call_for(event, script)
        description = call.get('arguments', {}).get('description', {})
        result.update(source=description.get('reference'), destination=event.get('url'), body=event.get('body'))
    elif command == 'RECEIVE':
        call = call_for(event, script)
        description = call.get('arguments', {}).get('description', {})
        result.update(source='fixture', destination='receiver', identities=event['identities'],
                      recipients=description.get('to', []) + description.get('cc', []) + description.get('bcc', []))
    return result


def differences(event, script):
    key, row = bind(event, script)
    if row is None:
        return key, ['current intent identity']
    wanted = required(event, script)
    actual = decode(row, key, event.get('committed_before', {}), event['command'])
    missing = []
    for field, value in wanted.items():
        found = actual.get(field)
        if field == 'identities':
            if not isinstance(found, list) or any(ref not in found for ref in value):
                missing.append(field)
        elif found != value or value is None and field not in {'source'}:
            missing.append(field)
    return key, sorted(missing)
