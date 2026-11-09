"""Order local effects against prior committed context, never the working rows."""
from .context import special_roles
from .records import canonical, fingerprint


def protected_roots(before, after, evidence):
    old, new = before.get('protected_special', {}), after.get('protected_special', {})
    for role in ('trash', 'drafts'):
        expected = []
        for remembered in old.get(role, []):
            value = dict(remembered)
            if 'roots' not in before:
                if not evidence or value['folder'] not in evidence.get('roles', {}):
                    return False
                value['delimiter'] = (evidence.get('delimiters') or {}).get(value['folder'])
            expected.append(value)
        for account in (before, after):
            folder = account.get('special', {}).get(role)
            if not folder:
                continue
            value = account.get('roots', {}).get(role)
            if value is None:
                if not evidence or folder not in evidence.get('roles', {}):
                    return False
                value = {'folder': folder, 'delimiter': (evidence.get('delimiters') or {}).get(folder)}
            expected.append(value)
        if {canonical(value) for value in expected} != {canonical(value) for value in new.get(role, [])}:
            return False
    return {key: value for key, value in old.items() if key not in {'trash', 'drafts'}} == {
        key: value for key, value in new.items() if key not in {'trash', 'drafts'}}


def errors(record, script, after_sequence=0, servers=()):
    rows, created, result, removals = {}, {}, [], {}
    committed = {event['seq'] for event in record.events}
    for event in sorted([*record.events, *record.prepared], key=lambda value: value['seq']):
        action, changes = event['action'], event['set']
        fields = set()
        source = 'event:' + str(event['seq'])
        local_delete = action == 'testapp_delete' and 'testapp' in changes
        account_keys = [key for key in changes if key.startswith('mail:account:')]
        local_account = action in {'mail_account_settings', 'mail_account_folders'} and account_keys
        if event['seq'] > after_sequence and (local_delete or local_account):
            calls = [call for call in script if call['action'] == action and call['clock'] <= event['time']]
            call = calls[-1] if calls else {}
            arguments = call.get('arguments', {})
            if not call:
                fields.add('scripted call')
            if local_delete:
                operation_id = event.get('operation_id')
                source = 'op:' + operation_id if operation_id else source
                operation = rows.get(source, {})
                if operation.get('state') != 'submitting' or operation.get('action') != action or operation.get('app') != 'testapp':
                    fields.add('prior submitting operation')
                if arguments.get('operation_id') != operation_id or operation.get('approval') != arguments:
                    fields.add('scripted approval')
                targets = arguments.get('description', {}).get('items', [])
                if not targets or operation.get('payload', {}).get('items') != targets:
                    fields.add('exact target references')
                approved = {item['reference']['id']: item for item in targets}
                before, after = rows.get('testapp', {}), changes.get('testapp') or {}
                old_items, new_items = before.get('items', {}), after.get('items', {})
                removed = old_items.keys() - new_items.keys()
                removals.setdefault(operation_id, set()).update(removed)
                if not removed or not removed <= approved.keys() or len(approved) != len(targets):
                    fields.add('unapproved deletion')
                for item_id in removed & approved.keys():
                    item = old_items[item_id]
                    reference = {'scope': 'testapp/fixture/items', 'epoch': before.get('epoch'),
                                 'id': item_id, 'revision': item['revision']}
                    if approved[item_id] != {'reference': reference, **{key: item[key] for key in ('sender', 'subject', 'date')}}:
                        fields.add('exact target references')
                if new_items != {key: value for key, value in old_items.items() if key not in removed} or {key: value for key, value in before.items() if key != 'items'} != {key: value for key, value in after.items() if key != 'items'}:
                    fields.add('surviving items changed')
                kind = 'R2.LOCAL_DELETE'
            else:
                key = 'mail:account:' + str(arguments.get('id'))
                before, after = rows.get(key, {}), changes.get(key) or {}
                intents = [(name, value) for name, value in rows.items() if name.startswith('intent:')
                    and value.get('action') == action and value.get('state') == 'started'
                    and created[name][1] >= call.get('clock', float('inf'))]
                if len(intents) != 1:
                    fields.add('current intent identity')
                    context = {}
                else:
                    source, intent = intents[0]
                    context = intent.get('context', {})
                for field, expected in {'account': arguments.get('id'), 'arguments': arguments, 'roles': special_roles(before)}.items():
                    if field not in context or context[field] != expected:
                        fields.add(field)
                if account_keys != [key]:
                    fields.add('effect account')
                if action == 'mail_account_settings':
                    wanted = {**before, **{name: arguments[name] for name in ('format', 'signature', 'sent_policy') if name in arguments}}
                    if 'sent_policy' in arguments:
                        wanted['ready'] = True
                    if after != wanted:
                        fields.add('effect arguments')
                else:
                    role_fields = ('special', 'roots', 'optional', 'delimiter')
                    if fingerprint({name: after.get(name) for name in role_fields}) != arguments.get('roles_hash'):
                        fields.add('effect arguments')
                    allowed = {*role_fields, 'protected_special'}
                    if {name: value for name, value in before.items() if name not in allowed} != {name: value for name, value in after.items() if name not in allowed}:
                        fields.add('effect arguments')
                    calls = {call.get('call'), call.get('parent')}
                    evidence = next((value for value in reversed(servers) if value['command'] == 'LIST'
                        and value['call'] in calls and value.get('account') == arguments.get('id')
                        and value.get('before_seq', 0) < event['seq']), None)
                    if not protected_roots(before, after, evidence):
                        fields.add('protected roots')
                kind = 'R2.LOCAL_CHANGE'
            if fields:
                result.append((source, kind, canonical(sorted(fields))))
        if event['seq'] > after_sequence and action == 'testapp_delete':
            for key, operation in changes.items():
                if not key.startswith('op:') or not operation or operation.get('state') != 'done':
                    continue
                calls = [call for call in script if call['action'] == action and call['clock'] <= event['time']
                         and call['arguments'].get('operation_id') == operation['id']]
                targets = calls[-1]['arguments'].get('description', {}).get('items', []) if calls else []
                approved = {item['reference']['id'] for item in targets}
                if not targets or removals.get(operation['id'], set()) != approved:
                    result.append((key, 'R2.LOCAL_DELETE', canonical(['complete approved removals'])))
        if event['seq'] in committed:
            for key, value in changes.items():
                if value is None:
                    rows.pop(key, None)
                else:
                    created.setdefault(key, (event['seq'], event['time']))
                    rows[key] = value
    return result
