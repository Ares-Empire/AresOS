"""Versioned page semantics. Incomplete or unfamiliar pages use the generic rules."""
import re
from urllib.parse import urlsplit

from ..common import digest
from .policy import HOSTS, listed, DELETE, PAY

VERSIONS = {name: 2 for name in HOSTS}
KINDS = {
    'gmail_send': {'version': 2, 'scope': 'exact displayed To/Cc/Bcc sets; quote-aware recipients; full current compose', 'trusted': True},
    'gemini_question': {'version': 1, 'scope': 'site and exact signed-in account', 'trusted': True},
    'github_star': {'version': 1, 'scope': 'site, account and exact repository', 'trusted': True},
}

# These are known action/confirmation pairs, never a confirmation learned from the page
# while approval waits. The extension also binds the private opener document and frame.
GITHUB_ACTIONS = {
    'comment': ('github_comment', 'send', None),
    'submit review': ('github_review', 'send', None),
    'approve review': ('github_review', 'send', None),
    'request changes': ('github_review', 'send', None),
    'merge pull request': ('github_merge', 'send', 'Merge pull request {context}?'),
    'close issue': ('github_close', 'send', 'Close issue {context}?'),
    'close pull request': ('github_close', 'send', 'Close pull request {context}?'),
    'delete branch': ('github_delete', 'delete', 'Delete branch {context}?'),
    'delete tag': ('github_delete', 'delete', 'Delete tag {context}?'),
    'delete repository': ('github_delete', 'delete', 'Delete repository {context}?'),
    'save settings': ('github_settings', 'send', 'Save settings for {context}?'),
}
DEEZER_FREE = {'play', 'pause', 'skip', 'next', 'previous', 'seek', 'volume', 'queue',
               'like', 'follow', 'add to playlist', 'add to library'}
DEEZER_REMOVE = {'unlike', 'unfollow', 'remove from playlist', 'remove from favorites',
                 'remove from favourites', 'remove favorite', 'remove favourite', 'delete playlist'}


def recipients(value):
    """Keep displayed identities exact; split only outside quoted names/angle addresses.

    A simple comma split can give different recipient sets the same allow key (a
    quoted display name may itself contain a comma). Ambiguous syntax cannot be trusted.
    """
    parts, start, quoted, escaped, angle = [], 0, False, False, False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
        elif char == '\\' and quoted:
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif not quoted and char == '<':
            if angle:
                return None
            angle = True
        elif not quoted and char == '>':
            if not angle:
                return None
            angle = False
        elif not quoted and not angle and char in ';:':
            return None
        elif not quoted and not angle and char == ',':
            if not value[start:index].strip():
                return None
            parts.append(value[start:index].strip())
            start = index + 1
    if quoted or escaped or angle:
        return None
    if value[start:].strip():
        parts.append(value[start:].strip())
    elif parts:
        return None
    return sorted(set(parts))


def recognize(url, reading, target, verb, args, hosts=None, enabled=None):
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or '').encode('idna').decode('ascii').lower().rstrip('.')
    except (ValueError, UnicodeError):
        return None
    site = next((name for name, names in (HOSTS if hosts is None else hosts).items() if host in names), None)
    if not site or site not in VERSIONS or enabled is not None and not enabled.get(site):
        return None
    if not isinstance(reading, dict) or not isinstance(target, dict):
        return None
    label = target.get('name', '').casefold().strip()
    label_words = set(re.findall(r'\w+', label))
    key = args.get('key', '') if verb == 'press' else ''
    activation = verb == 'click' or verb == 'press' and key in {'Enter', 'Space', ' '}
    editing = target.get('editable', False)
    # The reader's scope selector includes <main>, whose implicit role is currently
    # reported as generic. A nonempty scope still proves it selected a known container.
    scoped = bool(reading.get('scope')) and reading.get('scope_role') in {'dialog', 'form', 'region', 'main', 'generic'}
    account = isinstance(reading.get('account'), str) and bool(reading['account'].strip())
    text = isinstance(reading.get('text'), str) and isinstance(reading.get('attachments'), list)
    common = {'site': site, 'version': VERSIONS[site], 'account': reading.get('account')}
    result = None
    eligible = True
    if site == 'gmail':
        # Gmail's delete shortcut is also active on selected messages outside compose.
        if key == '#' and scoped and account and (not editing or reading.get('scope_role') in {'dialog', 'form'}):
            result = {'kind': 'gmail_delete', 'effect': 'delete', 'shortcut': '#', 'parameters': {}}
        elif scoped and reading.get('scope_role') in {'dialog', 'form'} and account and text and all(
                isinstance(reading.get(field), str) for field in ['to', 'cc', 'bcc', 'subject']):
            if activation and not editing and label in {'send', 'senden'} or editing and key in {'Ctrl+Enter', 'Cmd+Enter'}:
                exact = {field: recipients(reading[field]) for field in ['to', 'cc', 'bcc']}
                eligible = all(value is not None for value in exact.values()) and any(exact.values())
                result = {'kind': 'gmail_send', 'effect': 'send', 'parameters': exact}
    elif site == 'whatsapp' and scoped and reading.get('chat') and text:
        if activation and not editing and label in {'send', 'send message', 'senden'} or editing and key == 'Enter':
            result = {'kind': 'whatsapp_message', 'effect': 'send', 'parameters': {'chat': reading['chat']}}
    elif site == 'gemini' and scoped and account:
        if text and (activation and not editing and label in {'send', 'send message', 'submit', 'senden'} or editing and key == 'Enter'):
            result = {'kind': 'gemini_question', 'effect': 'send', 'parameters': {}}
        elif activation and not editing and label_words & {'delete', 'löschen', 'share', 'teilen'}:
            result = {'kind': 'gemini_chat', 'effect': 'delete' if listed(label) & DELETE else 'send', 'parameters': {}}
    elif site == 'github' and scoped and account and reading.get('context') and activation and not editing:
        if label in {'star', 'unstar'} or 'unstar' in label_words:
            result = {'kind': 'github_star', 'effect': 'change' if label == 'star' else 'delete',
                      'parameters': {'repository': reading['context']}}
        elif label in GITHUB_ACTIONS:
            kind, effect, confirmation = GITHUB_ACTIONS[label]
            if kind not in {'github_comment', 'github_review'} or text:
                result = {'kind': kind, 'effect': effect, 'parameters': {'context': reading['context'], 'action': target['name']}}
                if confirmation:
                    result['confirmation'] = {'kind': 'confirm', 'text': confirmation.format(context=reading['context']),
                                              'frame_url': url, 'button': 'OK'}
        elif listed(label) or label_words & {'merge', 'close', 'review', 'settings'} and 'help' not in label_words:
            # Keep sends such as “Squash and merge” guarded even when their exact
            # dialog sequence isn't one of the fixed plans above.
            words = listed(label)
            result = {'kind': 'github_action', 'effect': 'delete' if words & DELETE else 'pay' if words & PAY else 'send',
                      'parameters': {'context': reading['context'], 'action': target['name']}}
    elif site == 'deezer' and scoped and activation and not editing:
        if label in DEEZER_FREE and not target.get('submit'):
            result = {'kind': 'deezer_library', 'effect': 'change', 'parameters': {}}
        elif label in DEEZER_REMOVE or listed(label) or label_words & {'share', 'teilen', 'unlike', 'unfollow'}:
            words = listed(label)
            result = {'kind': 'deezer_action', 'effect': 'delete' if label in DEEZER_REMOVE or label_words & {'unlike', 'unfollow'} or words & DELETE else 'pay' if words & PAY else 'send', 'parameters': {}}
    if result is None:
        return None
    result = common | result
    definition = KINDS.get(result['kind'])
    result['kind_hash'] = digest(definition) if definition else None
    result['trusted'] = bool(eligible and definition and definition['trusted'] and result['effect'] not in {'delete', 'pay'} and account)
    return result
