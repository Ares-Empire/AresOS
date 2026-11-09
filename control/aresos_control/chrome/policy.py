"""Chrome policy is service data; the extension receives a generated copy."""
import re
import json
from bisect import bisect_right
from pathlib import Path
from urllib.parse import urlsplit, unquote

from ..common import Refused

WORD_LIST_VERSION = 2
WORDS = ('send submit post publish reply comment buy pay order book subscribe unsubscribe '
         'delete remove discard clear empty trash senden absenden schicken posten veröffentlichen '
         'antworten kommentieren kaufen bezahlen zahlen bestellen buchen abonnieren abbestellen '
         'löschen entfernen verwerfen leeren Papierkorb').split()
DELETE = set('delete remove discard clear empty trash löschen entfernen verwerfen leeren papierkorb'.split())
PAY = set('buy pay order book subscribe kaufen bezahlen zahlen bestellen buchen abonnieren'.split())
SEND = set('send submit post publish reply comment senden absenden schicken posten veröffentlichen antworten kommentieren'.split())
FIXED_HOSTS = ['claude.ai', 'console.anthropic.com', 'platform.claude.com']
HOSTS = {'gmail': ['mail.google.com'], 'whatsapp': ['web.whatsapp.com'], 'github': ['github.com'],
         'bank': [], 'gemini': ['gemini.google.com'], 'deezer': ['www.deezer.com', 'deezer.com']}
HOLD_MS = 500
CORE_GROUPS = ['classification', 'page_script', 'binding', 'password_exclusion']
CDP_METHODS = ['Input.dispatchMouseEvent', 'Input.dispatchKeyEvent', 'Input.insertText',
               'Page.navigate', 'Page.getNavigationHistory', 'Page.navigateToHistoryEntry', 'Page.reload',
               'Page.enable', 'Page.handleJavaScriptDialog']


# Frozen data keeps service/Chrome Unicode versions and locale from disagreeing.
UNICODE_WORDS=json.loads(Path(__file__).with_name('unicode_words.json').read_text())
WORD_STARTS=[start for start,_ in UNICODE_WORDS['ranges']]

def folded(text):
    return ''.join(UNICODE_WORDS['fold'].get(char,char) for char in text)

def listed(text):
    matches=set();word=''
    for char in folded(text):
        point=ord(char);index=bisect_right(WORD_STARTS,point)-1
        if index>=0 and point<=UNICODE_WORDS['ranges'][index][1]:word+=char
        else:
            if word in WORD_SET:matches.add(word)
            word=''
    if word in WORD_SET:matches.add(word)
    return matches

WORD_SET={folded(word) for word in WORDS}


def hostname(address):
    return (urlsplit(address).hostname or '').encode('idna').decode('ascii').rstrip('.').lower()


def allowed_url(address, extra_hosts=()):
    if address == 'about:blank':
        return address
    try:
        parsed = urlsplit(address)
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError()
        host_name = hostname(address)
        if any(host_name == host or host_name.endswith('.' + host) for host in [*FIXED_HOSTS, *extra_hosts]):
            raise ValueError()
        parsed.port
    except (ValueError, AttributeError, UnicodeError) as exc:
        raise Refused('refused', 'Only web addresses and about:blank are allowed; approval and settings pages belong to the owner.') from exc
    return address


def classify(verb, arguments, facts, *, conservative=False, readonly=False, adapter=None):
    """Every path classifies the control it would activate, never its tool name alone."""
    target = facts.get('target', {})
    key = arguments.get('key', '')
    editable = target.get('editable', False)
    search = target.get('search', False)
    activation = verb in {'click', 'check', 'select'} or verb == 'press' and key.split('+')[-1] in {'Enter', 'Space', ' '}
    if readonly and not (verb == 'scroll' or verb == 'click' and target.get('href') and not target['href'].startswith('javascript:')):
        raise Refused('readonly_site', 'This site is owner-marked read-only: read, scroll or follow a web link; do not fill, upload or activate buttons.')
    if target.get('password') and verb in {'fill', 'fill_form', 'press'}:
        raise Refused('owner_signin', 'Password fields are never read or filled. Ask the owner to sign in, then read again.')
    if verb == 'upload':
        return 'upload'
    if verb == 'dialog' and arguments.get('accept'):
        if conservative:return 'activation'
        words = listed(facts.get('dialog', {}).get('text', '') + ' ' + facts.get('dialog', {}).get('button', ''))
        return 'delete' if words & DELETE else 'pay' if words & PAY else 'confirmation' if words else None
    if verb == 'press' and key in {'Delete', 'Backspace'} and not editable:
        return 'delete'
    if adapter and adapter.get('kind') and activation or adapter and adapter.get('shortcut') == key:
        return adapter['effect'] if adapter['effect'] != 'change' else None
    if verb == 'press' and key.split('+')[-1] == 'Enter' and editable and not search:
        return 'send'
    if not activation:
        return None
    if target.get('href') and not target['href'].startswith('javascript:'):
        allowed_url(target['href'])
    form = facts.get('form')
    submit = target.get('submit') or verb == 'press' and key == 'Enter' and editable and form
    if submit:
        if form and form.get('search') and form.get('method','').lower()=='get':
            return 'form' if conservative else None
        return 'form'
    words = listed(' '.join(str(target.get(k, '')) for k in ('name', 'label', 'title', 'value', 'role')) +
                   ' ' + unquote((form or {}).get('action', '')) + ' ' + (target.get('page_dialog') or {}).get('text',''))
    if target.get('page_dialog') and target.get('name','').casefold() in {'ok','yes','confirm','continue','ja','bestätigen','weiter'} and words:
        return 'delete' if words & DELETE else 'pay' if words & PAY else 'confirmation'
    return 'delete' if words & DELETE else 'pay' if words & PAY else 'send' if words else 'activation' if conservative else None
