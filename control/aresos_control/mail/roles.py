"""Current SPECIAL-USE roles, never inferred from mailbox names."""
from ..common import Refused

ROLES = {'\\Sent': 'sent', '\\Drafts': 'drafts', '\\Trash': 'trash',
         '\\Junk': 'junk', '\\Archive': 'archive'}
SETUP = 'Owner must run sudo aresos admin mail account_folders --input \'{"id":"ACCOUNT"}\', review the roles, then repeat with the returned roles_hash to record them.'


def resolve(listed):
    special = {'inbox': 'INBOX'}
    for flag, role in ROLES.items():
        matches = [f for f in listed if flag.casefold() in {v.casefold() for v in f['flags']}]
        if len(matches) != 1 or any(v.casefold() == '\\noselect' for v in matches[0]['flags']):
            raise Refused('special_folders_changed', 'SPECIAL-USE roles are missing, ambiguous or unselectable. Configure the server roles first. ' + SETUP)
        special[role] = matches[0]['name']
    inbox = [f for f in listed if f['name'].casefold() == 'inbox']
    if len(inbox) != 1 or any(v.casefold() == '\\noselect' for v in inbox[0]['flags']):
        raise Refused('special_folders_changed', 'INBOX is missing or ambiguous. ' + SETUP)
    return {'special': special, 'delimiter': inbox[0]['delimiter']}
