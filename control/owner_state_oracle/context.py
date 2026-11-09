"""Exact pre-command context, decoded from documented records and raw commands."""
from email.utils import getaddresses

ROLES = ('sent', 'drafts', 'trash', 'junk', 'archive')
UID_COMMANDS = {'MOVE', 'COPY', 'STORE', 'EXPUNGE'}
MUTATIONS = UID_COMMANDS | {'DATA', 'APPEND', 'CREATE', 'DELETE', 'RENAME', 'POST', 'RECEIVE', 'CONFIGURE'}


def special_roles(value):
    if not isinstance(value, dict):
        return None
    if 'special' in value:
        return {role: [value['special'][role]] for role in ROLES if value['special'].get(role)}
    if any(role in value for role in ROLES):
        return {role: sorted(v if isinstance(v, list) else [v]) for role, v in value.items() if role in ROLES and v}
    return {role: sorted(name for name, flags in value.items() if isinstance(flags, list) and '\\' + role in [flag.lower() for flag in flags])
            for role in ROLES if any(isinstance(flags, list) and '\\' + role in [flag.lower() for flag in flags] for flags in value.values())}


def special_delimiters(roles, delimiters):
    return {role: [delimiters.get(name, '/') for name in names] for role, names in (special_roles(roles) or {}).items()}


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
    if not refs and mail.get('answered_reference'):
        refs = [mail['answered_reference']]
    roles = row.get('roles_before') or original.get('roles_before')
    account = account or (refs[0].get('account') if refs else None)
    result = {'account': account, 'roles': special_roles(roles), 'identities': [identity(ref) for ref in refs]}
    if isinstance(roles, dict) and roles.get('roots'):
        result['delimiters'] = {role: [root['delimiter']] for role, root in roles['roots'].items() if role in ROLES}
    if key.startswith('mail:filing:'):
        result.update(command=row.get('verb', '').upper(), source=refs[0]['folder'] if refs else None,
                      destination=row.get('target'))
    elif key.startswith('mail:rename:'):
        result.update(command='RENAME', source=row.get('source'), destination=row.get('target'))
    elif command in UID_COMMANDS:
        declared = 'MOVE' if payload.get('mode') == 'trash' else command if payload.get('mode') == 'permanent' and command in {'STORE', 'EXPUNGE'} else 'STORE' if mail.get('answered_reference') else None
        result.update(command=declared, source=refs[0]['folder'] if refs else None)
        if command == 'MOVE' and payload.get('mode') == 'trash':
            result['destination'] = (result['roles'] or {}).get('trash', [None])[0]
        if command == 'STORE' and payload.get('mode') == 'permanent':
            result['flags'] = ['+FLAGS.SILENT', '(\\Deleted)']
        elif command == 'STORE' and mail.get('answered_reference'):
            result['flags'] = ['+FLAGS.SILENT', '(\\Answered)']
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
        if event.get('delimiters') is not None:
            result['delimiters'] = special_delimiters(event.get('roles') or {}, event['delimiters'])
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
    elif command == 'CONFIGURE':
        result.update(source='fixture', destination='receiver/config', arguments=event.get('arguments'))
    return result


def permitted(row, call):
    action = call.get('action')
    arguments = call.get('arguments', {})
    description = arguments.get('description', {})
    if action == 'mail_delete':
        mode = description.get('mode', arguments.get('mode'))
    else:
        mode = row.get('payload', {}).get('mode')
        action = action or row.get('action')
    if action == 'mail_delete':
        return {'MOVE'} if mode == 'trash' else {'STORE', 'EXPUNGE'} if mode == 'permanent' else set()
    if action in {'mail_folder_delete', 'mail_onboarding_folder_probe'}:
        return {'DELETE'}
    if action == 'mail_operation_repair':
        stage = arguments.get('stage')
        return {'APPEND'} if stage == 'sent_copy' else {'STORE'} if stage == 'answered_flag' else set()
    if action == 'mail_unsubscribe' and row.get('payload', {}).get('method') == 'POST':
        return {'POST'}
    if action in {'mail_send', 'mail_unsubscribe'}:
        return {'DATA', 'APPEND', 'STORE'}
    return {'mail_move': {'MOVE'}, 'mail_copy': {'COPY'}, 'mail_folder_rename': {'RENAME'},
            'mail_folder_create': {'CREATE'}, 'mail_draft_save': {'APPEND'}, 'mail_flag': {'STORE'},
            'testapp_send': {'RECEIVE'}, 'testapp_fixture_configure': {'CONFIGURE'}}.get(action)


def differences(event, script):
    key, row = bind(event, script)
    if row is None:
        return key, ['current intent identity']
    wanted = required(event, script)
    actual = decode(row, key, event.get('committed_before', {}), event['command'])
    allowed = permitted(row, call_for(event, script))
    missing = ['approved command'] if allowed is not None and event['command'] not in allowed else []
    if event['command'] == 'CONFIGURE' and event.get('arguments') != call_for(event, script).get('arguments'):
        missing.append('command arguments')
    for field, value in wanted.items():
        found = actual.get(field)
        if field == 'identities':
            if not isinstance(found, list) or any(ref not in found for ref in value):
                missing.append(field)
        elif found != value or value is None and field not in {'source'}:
            missing.append(field)
    missing.extend(script_differences(event, script, row, actual))
    return key, sorted(set(missing))


def script_differences(event, script, row, context):
    """A matching context/command pair still needs the scenario's authority."""
    call = call_for(event, script)
    args = call.get('arguments', {})
    description = args.get('description', {})
    if call.get('action') == 'mail_operation_repair':
        original = next((c for c in script if c.get('action') in {'mail_send', 'mail_unsubscribe'} and
            c.get('arguments', {}).get('operation_id') == args.get('operation_id')), {})
        description = original.get('arguments', {}).get('description', description)
    description = {**description, **description.get('untrusted_content', {})}
    action, command = call.get('action'), event['command']
    refs = args.get('references') or [i['reference'] for i in description.get('items', []) if 'reference' in i]
    if not refs and description.get('answered_reference'):
        refs = [description['answered_reference']]
    errors = []
    expected_account = args.get('account') or description.get('account') or (refs[0].get('account') if refs else None)
    if expected_account is not None:
        if event.get('account') != expected_account:
            errors.append('script.command.account')
        if context.get('account') != expected_account:
            errors.append('script.context.account')
    actual = required(event, script)
    if refs and command in UID_COMMANDS:
        selected = actual.get('identities', [])
        if not selected or any(ref not in [identity(v) for v in refs] for ref in selected):
            errors.append('script.command.identities')
        if any(identity(v) not in (context.get('identities') or []) for v in refs):
            errors.append('script.context.identities')
        if any(v not in [identity(ref) for ref in refs] for v in (context.get('identities') or [])):
            errors.append('script.context.unapproved-identities')
    expected = {}
    if action in {'mail_move', 'mail_copy'}:
        expected['destination'] = args.get('target')
    elif action == 'mail_delete':
        mode = description.get('mode', args.get('mode'))
        if mode == 'trash':
            # The script chooses the role; the independent pre-command LIST
            # chooses its name. Neither command nor context chooses the target.
            trash = (special_roles(event.get('roles')) or {}).get('trash', [])
            expected['destination'] = trash[0] if len(trash) == 1 else None
        elif mode == 'permanent' and command == 'STORE':
            expected['flags'] = ['+FLAGS.SILENT', '(\\Deleted)']
    elif action == 'mail_folder_rename':
        expected.update(source=args.get('folder'), destination=args.get('name'))
    elif action == 'mail_folder_create':
        expected.update(source=None, destination=args.get('name'))
    elif action == 'mail_folder_delete':
        expected.update(source=description.get('folder'), destination=description.get('folder'))
    elif action == 'mail_flag' and command == 'STORE':
        operations = flag_operations(args)
        for label, value in (('command', actual), ('context', context)):
            if value.get('flags') not in operations:
                errors.append('script.' + label + '.flags')
    elif action == 'mail_operation_repair':
        stage = args.get('stage')
        if row.get('repair_of') != args.get('operation_id') or row.get('payload', {}).get('stage') != stage:
            errors.append('script.repair-stage')
        if command not in ({'APPEND'} if stage == 'sent_copy' else {'STORE'} if stage == 'answered_flag' else set()):
            errors.append('script.repair-command')
    if command in {'DATA', 'RECEIVE'} and any(k in description for k in ('to', 'cc', 'bcc')):
        expected['recipients'] = [address for _, address in getaddresses(description.get('to', []) + description.get('cc', []) + description.get('bcc', []))] if command == 'DATA' else description.get('to', []) + description.get('cc', []) + description.get('bcc', [])
    if command == 'DATA' and description.get('from'):
        expected['source'] = getaddresses([description['from']])[0][1]
    if command == 'POST':
        if 'target' in description:
            expected['destination'] = description['target']
        expected['body'] = 'List-Unsubscribe=One-Click'
        if 'reference' in description:
            expected['source'] = description['reference']
    if command == 'CONFIGURE':
        expected['arguments'] = args
    for field, value in expected.items():
        if actual.get(field) != value:
            errors.append('script.command.' + field)
        if context.get(field) != value:
            errors.append('script.context.' + field)
    operation_id = args.get('operation_id')
    if operation_id and action in {'mail_send', 'mail_unsubscribe', 'mail_operation_repair'} and command in {'DATA', 'APPEND'}:
        identities = [{'message_id': '<' + operation_id.replace(':', '.') + '@mail.aresos.invalid>'}]
        if actual.get('identities') != identities:
            errors.append('script.command.message-identity')
        if [{k: v for k, v in ref.items() if k == 'message_id'} for ref in (context.get('identities') or [])] != identities:
            errors.append('script.context.message-identity')
    if operation_id and command == 'RECEIVE' and event.get('identities') != [{'operation_id': operation_id}]:
        errors.append('script.command.operation-identity')
    if command == 'APPEND' and 'append_flags' in event:
        flags = '(\\Draft)' if action == 'mail_draft_save' else '(\\Seen)' if action in {'mail_send', 'mail_unsubscribe', 'mail_operation_repair'} else None
        if action == 'mail_account_add' and event.get('folder') in (special_roles(event.get('roles')) or {}).get('sent', []):
            flags = '(\\Seen)'
        if event['append_flags'] != flags:
            errors.append('script.command.append-flags')
        # Legacy send/repair intent actions imply Seen. A new explicit context
        # must spell out its flags rather than borrowing the attempted command.
        if isinstance(row.get('context'), dict) and context.get('append_flags') != flags:
            errors.append('script.context.append-flags')
    if args.get('operation_id') and row.get('approval') is not None and action != 'mail_operation_repair' and row['approval'] != args:
        errors.append('script.approval')
    return errors


def flag_operations(arguments):
    return [[sign + 'FLAGS.SILENT', '(' + ' '.join(arguments[name]) + ')']
            for name, sign in (('add', '+'), ('remove', '-')) if arguments.get(name)]


def missing_flag_commands(script, servers):
    """Checking each attempted command alone cannot detect an omitted branch."""
    result = []
    for call in script:
        if call['action'] != 'mail_flag' or call.get('reply') == 'pending' or call.get('parent') is not None:
            continue
        if not any(e['call'] == call['call'] for e in servers) and 'end_seq' not in call:
            continue
        events = [e for e in servers if e['call'] == call['call'] and e['command'] == 'STORE']
        # A fault or a refused/lost command can legitimately interrupt a batch.
        # It never authorizes an extra command (differences checks those).
        if call.get('faults', {}).get('trace') or any(not e['accepted'] or e['reply'] != 'delivered' for e in events):
            continue
        for ref in call['arguments'].get('references', []):
            for flags in flag_operations(call['arguments']):
                matches = [e for e in events if e.get('account') == ref['account'] and e.get('folder') == ref['folder']
                           and e.get('arguments') == [str(ref['uid']), *flags]]
                if len(matches) != 1:
                    result.append((call['call'], identity(ref), flags))
    return result
