"""Small versioned semantic site adapters. Incomplete readings fall back to generic rules."""
from urllib.parse import urlsplit
from ..common import digest
from .policy import HOSTS, listed, DELETE, PAY

VERSIONS = {name: 1 for name in HOSTS}
KINDS = {
    'gmail_send': {'version': 1, 'scope': 'exact recipients; full current compose', 'trusted': True},
    'gemini_question': {'version': 1, 'scope': 'site and exact signed-in account', 'trusted': True},
    'github_star': {'version': 1, 'scope': 'site, account and exact repository', 'trusted': True},
}


def recognize(url, reading, target, verb, args, hosts=None, enabled=None):
    host = urlsplit(url).hostname
    site = next((name for name, names in (hosts or HOSTS).items() if host in names), None)
    if not site or enabled is not None and not enabled.get(site):
        return None
    label = target.get('name', '').casefold()
    key = args.get('key', '')
    common = {'site': site, 'version': VERSIONS[site], 'account': reading.get('account')}
    result = None
    if site == 'gmail' and reading.get('scope_role') in {'dialog','form'} and all(reading.get(k) is not None for k in ['account','to','cc','bcc','subject','text']):
        if key == '#':
            result = {'kind': 'gmail_delete', 'effect': 'delete', 'shortcut': '#', 'parameters': {}}
        elif label in {'send', 'senden'} or key in {'Ctrl+Enter','Cmd+Enter'}:
            recipients = {k: sorted(set(part.strip() for part in reading[k].split(',') if part.strip())) for k in ['to','cc','bcc']}
            result = {'kind': 'gmail_send', 'effect': 'send', 'parameters': recipients}
    elif site == 'whatsapp' and reading.get('chat') and reading.get('text') is not None and (label in {'send','send message','senden'} or key == 'Enter'):
        result = {'kind':'whatsapp_message','effect':'send','parameters':{'chat':reading['chat']}}
    elif site == 'gemini' and reading.get('account') and reading.get('text') is not None:
        if label in {'send','send message','submit','senden'} or key == 'Enter':
            result = {'kind':'gemini_question','effect':'send','parameters':{}}
        elif any(word in label for word in ['delete','löschen','share','teilen']):
            result = {'kind':'gemini_chat','effect':'delete' if listed(label) & DELETE else 'send','parameters':{}}
    elif site == 'github' and reading.get('account') and reading.get('context'):
        if label in {'star','unstar'}:
            result = {'kind':'github_star','effect':'change' if label == 'star' else 'delete','parameters':{'repository':reading['context']}}
        elif listed(label) or any(word in label for word in ['merge','close','review','settings']):
            result = {'kind':'github_action','effect':'delete' if listed(label) & DELETE else 'pay' if listed(label) & PAY else 'send','parameters':{'context':reading['context'],'action':target['name']}}
            # Known confirmations are exact data, including origin and frame URL.
            if label == 'delete branch':
                result['confirmation'] = {'kind':'confirm','text':'Delete branch ' + reading['context'] + '?','frame_url':url,'button':'OK'}
    elif site == 'deezer':
        free = {'play','pause','skip','next','previous','seek','volume','queue','like','follow','add to playlist','add to library'}
        if label in free:
            result = {'kind':'deezer_library','effect':'change','parameters':{}}
        elif listed(label) or any(word in label for word in ['share','teilen']):
            result = {'kind':'deezer_action','effect':'delete' if listed(label) & DELETE else 'pay' if listed(label) & PAY else 'send','parameters':{}}
    if result is None:
        return None
    result = common | result
    definition = KINDS.get(result['kind'])
    result['kind_hash'] = digest(definition) if definition else None
    result['trusted'] = bool(definition and definition['trusted'] and result['effect'] not in {'delete','pay'} and reading.get('account'))
    return result
