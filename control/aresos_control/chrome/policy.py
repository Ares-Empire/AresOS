"""Chrome policy is service data; the extension receives a generated copy."""
import re
import json
import unicodedata
from bisect import bisect_right
from pathlib import Path
from urllib.parse import urlsplit, unquote

from ..common import Refused

WORD_LIST_VERSION = 3
WORDS = ('send submit post publish reply comment buy pay order book subscribe unsubscribe '
         'delete remove discard clear empty trash senden absenden schicken posten veröffentlichen '
         'antworten kommentieren kaufen bezahlen zahlen bestellen buchen abonnieren abbestellen '
         'löschen entfernen verwerfen leeren Papierkorb').split()
DELETE = set('delete remove discard clear empty trash löschen entfernen verwerfen leeren papierkorb'.split())
PAY = set('buy pay order book subscribe kaufen bezahlen zahlen bestellen buchen abonnieren'.split())
ITEM = {'unsubscribe', 'abbestellen'}
SEND = set('send submit post publish reply comment senden absenden schicken posten veröffentlichen antworten kommentieren'.split())
FIXED_HOSTS = ['claude.ai', 'console.anthropic.com', 'platform.claude.com']
HOSTS = {'gmail': ['mail.google.com'], 'whatsapp': ['web.whatsapp.com'], 'github': ['github.com'],
         'bank': [], 'gemini': ['gemini.google.com'], 'deezer': ['www.deezer.com', 'deezer.com']}
HOLD_MS = 500
CORE_GROUPS = ['classification', 'page_script', 'binding', 'password_exclusion']
CDP_METHODS = ['Input.dispatchMouseEvent', 'Input.dispatchKeyEvent', 'Input.insertText',
               'Page.navigate', 'Page.getNavigationHistory', 'Page.navigateToHistoryEntry', 'Page.reload',
               'Page.enable', 'Page.handleJavaScriptDialog',
               'Runtime.evaluate', 'Runtime.callFunctionOn', 'Runtime.runIfWaitingForDebugger',
               'Debugger.enable', 'Debugger.disable', 'Debugger.setBreakpointByUrl', 'Debugger.resume', 'Target.setAutoAttach', 'Target.detachFromTarget',
               'DOM.describeNode', 'DOM.resolveNode', 'Page.getFrameTree']


# Frozen data keeps service/Chrome Unicode versions and locale from disagreeing.
UNICODE_WORDS=json.loads(Path(__file__).with_name('unicode_words.json').read_text())
WORD_STARTS=[start for start,_ in UNICODE_WORDS['ranges']]

def folded(text):
    return ''.join(UNICODE_WORDS['fold'].get(char,char) for char in unicodedata.normalize('NFC', text))

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


def key_input(value):
    parts = value.split('+')
    name = parts.pop()
    if any(part not in {'Ctrl', 'Cmd', 'Alt', 'Shift'} for part in parts):
        raise Refused('refused', 'Unsupported key modifier.')
    modifiers = sum(bit for part, bit in [('Alt', 1), ('Ctrl', 2), ('Cmd', 4), ('Shift', 8)] if part in parts)
    special = {'Enter': ('Enter', 13, 'Enter'), 'Space': ('Space', 32, ' '), ' ': ('Space', 32, ' '),
               'Delete': ('Delete', 46, 'Delete'), 'Backspace': ('Backspace', 8, 'Backspace'),
               'Tab': ('Tab', 9, 'Tab'), 'Escape': ('Escape', 27, 'Escape'),
               '#': ('Digit3', 51, '#')}
    for key, code in [('ArrowLeft', 37), ('ArrowUp', 38), ('ArrowRight', 39), ('ArrowDown', 40),
                      ('Home', 36), ('End', 35), ('PageUp', 33), ('PageDown', 34)]:
        special[key] = (key, code, key)
    if name == '#': modifiers |= 8
    if name in special: code, vk, key = special[name]
    elif re.fullmatch('[a-zA-Z]', name): code, vk, key = 'Key' + name.upper(), ord(name.upper()), name
    elif re.fullmatch('[0-9]', name): code, vk, key = 'Digit' + name, ord(name), name
    elif re.fullmatch(r'F(?:[1-9]|1\d|2[0-4])', name): code, vk, key = name, 111 + int(name[1:]), name
    else: raise Refused('refused', 'Unsupported key; use an explicit supported key or fill text.')
    result = {'key': key, 'code': code, 'modifiers': modifiers, 'windowsVirtualKeyCode': vk}
    if name == 'Enter': result['text'] = '\r'
    elif key == ' ': result['text'] = ' '
    elif len(key) == 1 and not modifiers & 6: result['text'] = key
    return result


def canonical_key(value):
    key = key_input(value)
    modifiers = key['modifiers'] & (~8 if key['key'] == '#' else 15)
    return ''.join(part + '+' for part, bit in [('Ctrl', 2), ('Cmd', 4), ('Alt', 1), ('Shift', 8)] if modifiers & bit) + ('Space' if key['key'] == ' ' else key['key'])


def explicit_effect(facts):
    target = facts.get('target', {})
    words = listed(' '.join(str(target.get(k, '')) for k in ('name', 'label', 'title', 'value', 'role')) +
                   ' ' + unquote((facts.get('form') or {}).get('action', '')) + ' ' + (target.get('page_dialog') or {}).get('text', ''))
    return 'delete' if words & DELETE else 'pay' if words & PAY else 'item' if words & ITEM else 'send' if words else None


def classify(verb, arguments, facts, *, conservative=False, readonly=False, adapter=None):
    """Every path classifies the control it would activate, never its tool name alone."""
    target = facts.get('target', {})
    key = canonical_key(arguments['key']) if verb == 'press' and arguments.get('key') else ''
    base_key = key_input(key)['key'] if key else ''
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
    if verb == 'press' and base_key in {'Delete', 'Backspace'} and not editable:
        return 'delete'
    evidence = explicit_effect(facts) if activation else None
    if evidence in {'delete', 'pay', 'item'}:
        return evidence
    if adapter and adapter.get('kind') and activation or adapter and adapter.get('shortcut') == key:
        return adapter['effect'] if adapter['effect'] != 'change' else None
    # A confirmation can send a draft outside the button's own form.
    if evidence and target.get('page_dialog'):
        return 'confirmation'
    form = facts.get('form')
    if verb == 'press' and base_key == 'Enter' and editable:
        if form and form.get('search') and form.get('method', '').lower() == 'get':
            return 'form' if conservative else None
        if not search:
            return 'send'
    if not activation:
        return None
    if target.get('href') and not target['href'].startswith('javascript:'):
        allowed_url(target['href'])
    form = facts.get('form')
    submit = target.get('submit') or verb == 'press' and base_key == 'Enter' and editable and form
    if submit:
        if form and form.get('search') and form.get('method','').lower()=='get' and not evidence:
            return 'form' if conservative else None
        return 'form'
    words = listed(' '.join(str(target.get(k, '')) for k in ('name', 'label', 'title', 'value', 'role')) +
                   ' ' + unquote((form or {}).get('action', '')) + ' ' + (target.get('page_dialog') or {}).get('text',''))
    return 'delete' if words & DELETE else 'pay' if words & PAY else 'send' if words else 'activation' if conservative else None
