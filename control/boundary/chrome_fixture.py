"""Only the native Linux precedence fixture uses this synthetic owner record."""
import json
from pathlib import Path
from types import SimpleNamespace
from aresos_control.chrome.adapter import Chrome
from aresos_control.chrome.sites import KINDS
from aresos_control.common import digest

OWNER = Path('/opt/aresos-control/chrome-owner-entry.json')

def operation():
    return {'payload':{'kind':'send','binding':{'frame_url':'https://fixture.test/','target':{'name':'Continue'}},
        'adapter':{'site':'gemini','kind':'gemini_question','trusted':True,'effect':'send',
                   'account':'Synthetic account','parameters':{'text':'Synthetic fixed question'}}}}

def checker():
    adapter=Chrome.__new__(Chrome)
    adapter.mode=lambda **kw:{'conservative':False,'adapters':{'gemini':True}}
    adapter.committed=SimpleNamespace(get=lambda key,default=None:json.loads(OWNER.read_text()).get(key,default))
    return adapter

def owner_entry(mode):
    adapter=checker();op=operation()
    key='chrome:allow:'+adapter.allow_id(op)
    if mode=='other-account':
        op['payload']['adapter']['account']='Other synthetic account';key='chrome:allow:'+adapter.allow_id(op)
    return {} if mode=='missing' else {key:{'kind_hash':digest(KINDS['gemini_question']),'revoked':mode=='revoked'}}

def trusted():
    return checker().require_trusted_send('submit_trusted',operation()) is True
