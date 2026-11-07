"""Short approval introductions; complete facts remain in the description.

Build from raw preparation facts and escape once in shared approval_input().
Summary limits count the eventual visible characters, keeping every escape whole.
"""
from email.utils import getaddresses, parsedate_to_datetime
from urllib.parse import urlsplit

from ..common import visible


def short(value, limit=80):
    used, prefix = 0, []
    for char in value:
        used += len(visible(char))
        if used > limit:
            return ''.join(prefix) + '…'
        prefix.append(char)
    return value


def person(value):
    """A display name never stands alone: a lookalike name ("Mom") must show its real address.

    Only the name is shortened; the address is always shown whole (bounded like a real address).
    """
    pairs = getaddresses([value])
    if len(pairs) == 1 and pairs[0][1]:
        name, address = pairs[0]
        address = short(address, 254)
        return f'{short(name)} <{address}>' if name else address
    return short(value)


def few(values, cut=True):
    shown = [short(value) if cut else value for value in values[:3]]
    if len(values) > 3:
        shown.append(f'{len(values) - 3} more')
    if len(shown) < 2:
        return ''.join(shown)
    return ', '.join(shown[:-1]) + ' and ' + shown[-1]


def day(value):
    try:
        parsed = parsedate_to_datetime(value)
        month = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')[parsed.month - 1]
        return f'{parsed.day} {month}'
    except (ValueError, TypeError, OverflowError):
        return short(value, 40) or 'date unknown'


def question(verb, details, source=None):
    if verb == 'send':
        text = 'Send this mail'
        for key, label in (('to', ' to '), ('cc', ', Cc '), ('bcc', ', hidden copy (Bcc) to ')):
            if details[key]:
                text += label + few([person(v) for v in details[key]], cut=False)
        # The caller's text excludes generated quotes, forwards and the signature.
        lines = len(details['text'].splitlines())
        attachments = details['attachments']
        text += f"; Subject: {details['subject']}; {lines} " + ('line' if lines == 1 else 'lines')
        text += f", {len(attachments)} " + ('attachment' if len(attachments) == 1 else 'attachments')
        if attachments:
            text += ': ' + few([a['name'] for a in attachments])
        quoted = any(p['kind'] == 'quoted_mail' for p in details['generated_parts'])
        if quoted and details.get('answered_reference'):
            text += '; quotes the earlier mail'
        forwards = int(quoted and not details.get('answered_reference')) + sum(
            a.get('source', {}).get('part') == 'source' and bool(a.get('transformation')) for a in attachments)
        if forwards:
            text += f'; forwards {forwards} ' + ('mail' if forwards == 1 else 'mails')
        if any(p['kind'] == 'draft_body' for p in details['generated_parts']):
            text += '; includes saved draft text'
        return text + '?'
    if verb == 'delete':
        items = details['items']
        count = f"{len(items)} " + ('message' if len(items) == 1 else 'messages')
        text = f'Delete {count} for good' if details['mode'] == 'permanent' else f'Move {count} to Trash'
        summaries = [f"from {person(i['from'])}, '{short(i['subject'], 120)}' ({day(i['date'])})" for i in items[:3]]
        if len(items) > 3:
            summaries.append(f'and {len(items) - 3} more')
        return text + ': ' + '; '.join(summaries) + '?'
    if verb == 'folder_delete':
        return f"Delete the empty folder '{details['folder']}'?"
    if verb == 'unsubscribe':
        label = short(str(source.get('List-ID')), 120) if source.get('List-ID') else person(str(source.get('From'))) if source.get('From') else 'this mailing list'
        url = urlsplit(details['target'])
        method = ('sending a mail to ' + few(details['to']) if url.scheme == 'mailto'
                  else 'a one-click web request to ' + url.hostname)
        return f'Unsubscribe from {label} by {method}?'
    if verb == 'onboarding_folder_probe':
        state = 'empty' if details.get('empty') else 'nonempty'
        return f"Test deleting the {state} disposable setup folder '{details['folder']}'?"
    if verb == 'operation_repair':
        stage = {'sent_copy': 'Sent copy', 'answered_flag': 'answered flag'}[details['stage']]
        return f"Repair the {stage} for operation {details['repair_of']} without sending again?"
    raise ValueError('Unsupported Mail question')
