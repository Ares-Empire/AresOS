"""Current SPECIAL-USE roles, never inferred from mailbox names."""
from ..common import Refused

ROLES = {'\\Sent': 'sent', '\\Drafts': 'drafts', '\\Trash': 'trash',
         '\\Junk': 'junk', '\\Archive': 'archive'}
REQUIRED = ('inbox', 'sent', 'drafts', 'trash')
OPTIONAL = ('junk', 'archive')
SETUP = 'Owner must run sudo aresos admin mail account_folders --input \'{"id":"ACCOUNT"}\', review the roles, then repeat with the returned roles_hash to record them.'


def root(account, role):
    # Old setups did not record per-root separators. Never guess their namespace.
    return account.get('roots', {}).get(role, {'folder': account['special'].get(role), 'delimiter': None})


def optional_roles(listed):
    return {role: sorted([{'folder': f['name'], 'delimiter': f['delimiter'],
                          'selectable': not any(v.casefold() == '\\noselect' for v in f['flags'])}
                         for f in listed if ('\\' + role).casefold() in {v.casefold() for v in f['flags']}],
                        key=lambda f: f['folder']) for role in OPTIONAL}


def recorded_optional(account):
    # Accounts recorded before optional-role metadata still have exact folder roots.
    return account.get('optional', {role: ([{'folder': account['special'][role],
                                          'delimiter': account.get('delimiter'), 'selectable': True}]
                                        if account['special'].get(role) else []) for role in OPTIONAL})


def optional_status(recorded, current):
    result = {}
    for role in OPTIONAL:
        entries = current[role]
        valid = not entries or (len(entries) == 1 and entries[0]['selectable'])
        result[role] = {'status': ('present' if entries else 'absent')
                        if valid and entries == recorded[role] else 'needs_setup',
                        'folder': entries[0]['folder'] if len(entries) == 1 and valid else None,
                        'current_folders': entries, 'recorded_folders': recorded[role]}
    return result


def check_optional(account, current, names=(), needed=()):
    recorded = recorded_optional(account)
    for role, state in optional_status(recorded, current).items():
        if role in needed and state['status'] == 'absent':
            raise Refused('special_folder_missing', role.title() + ' role is missing. The owner can mark that folder in his mail server\'s settings, then run the setup step. ' + SETUP)
        roots = current[role] + recorded[role]
        affected = any(name == v['folder'] or (v['delimiter'] and name.startswith(v['folder'] + v['delimiter']))
                       for name in names for v in roots)
        if state['status'] == 'needs_setup' and (affected or role in needed):
            raise Refused('special_folders_changed', role.title() + ' role is duplicated, unselectable or changed since setup; this action touches an affected folder. The owner must fix the role in his mail server\'s settings, then run the setup step. ' + SETUP)


def resolve(listed):
    special = {'inbox': 'INBOX'}
    roots = {}
    optional = optional_roles(listed)
    for flag, role in ROLES.items():
        if role in OPTIONAL:
            entries = optional[role]
            special[role] = entries[0]['folder'] if len(entries) == 1 and entries[0]['selectable'] else None
            continue
        matches = [f for f in listed if flag.casefold() in {v.casefold() for v in f['flags']}]
        if len(matches) != 1 or any(v.casefold() == '\\noselect' for v in matches[0]['flags']):
            raise Refused('special_folders_changed', 'SPECIAL-USE roles are missing, ambiguous or unselectable. Configure the server roles first. ' + SETUP)
        special[role] = matches[0]['name']
        roots[role] = {'folder': matches[0]['name'], 'delimiter': matches[0]['delimiter']}
    inbox = [f for f in listed if f['name'].casefold() == 'inbox']
    if len(inbox) != 1 or any(v.casefold() == '\\noselect' for v in inbox[0]['flags']):
        raise Refused('special_folders_changed', 'INBOX is missing or ambiguous. ' + SETUP)
    roots['inbox'] = {'folder': inbox[0]['name'], 'delimiter': inbox[0]['delimiter']}
    for role in OPTIONAL:
        if special[role]:
            roots[role] = {k: optional[role][0][k] for k in ('folder', 'delimiter')}
    return {'special': special, 'roots': roots, 'optional': optional, 'delimiter': inbox[0]['delimiter']}
