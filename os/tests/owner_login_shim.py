"""Prepared-login transport stand-in; predicates/counter math run unchanged."""
import base64
import hashlib
import json
import shlex
from unittest.mock import patch

import owner_hidden
import owner_login
from owner_console_shim import execute_hidden
from test_owner_reliable_typing import execute_guard


def frame(value):
    raw=json.dumps(value).encode()
    return ('\nARESOS_EXPORT_START\n'+base64.encodebytes(raw).decode()+'ARESOS_EXPORT_END\n'
        +'ARESOS_EXPORT_SHA256 '+hashlib.sha256(raw).hexdigest()+'  guest.json\n')


class LoginShim:
    def __init__(self,guest,tty):
        self.guest,self.tty=guest,tty
        self.ticket=dict(status='ready',path='/run/ares-input-fixture1',pid=77,device='/dev/input/event5',counts_only=True)
        self.reader=None;self.baseline=None;self.audit=None

    def call(self,action,argument=None):
        g=self.guest
        if action=='init':
            self.tty=argument
            g.key_counts=dict(press=0,release=0,repeat=0,syn_dropped=0)
            return dict(status='ready',timeout_seconds=60,half_budget_seconds=30,ticket=self.ticket,
                counters_started_before_username=True,observers_prepared=True)
        if action=='begin':return dict(ready=True,fresh_getty=True)
        if action=='echo':return dict(ready=True,echo_matches=True,value_recorded=False)
        if action=='ready':
            value,rows,shape=execute_hidden(owner_hidden.source(self.tty,dict(kind='login'),prompt='Password:'),facts=True)
            assert value['ready'];self.reader=value['reader'];return value
        if action=='arm':
            self.baseline=dict(g.key_counts)
            value=self.call('guard');value['baseline']=self.baseline;return value
        if action in ('guard','enter'):
            value=execute_guard(owner_hidden.guard_source(self.tty,dict(kind='login'),self.reader))
            value.update(remaining_seconds=29,elapsed_seconds=1,timeout_seconds=60,reader_changed=False)
            if action=='enter':
                counts={k:g.key_counts[k]-self.baseline[k] for k in g.key_counts}
                self.audit=dict(counts_only=True,complete=True,value_recorded=False,codes_recorded=False,
                    counts=dict(hidden=counts,non_hidden=dict.fromkeys(counts,0),unknown=dict.fromkeys(counts,0)))
                value['exposure']=self.audit
            return value
        if action=='sample':return self.counter()
        if action=='entered':return dict(within_half_timeout=True,elapsed_seconds=1,timeout_seconds=60,half_budget_seconds=30,value_recorded=False,counters_started_before_username=True)
        if action=='finish':
            result=self.counter();result['exposure']=self.audit or dict(counts_only=True,complete=True,counts={k:dict(press=0,release=0,repeat=0,syn_dropped=0) for k in ('hidden','non_hidden','unknown')})
            g.key_counts=None;return result
        if action=='cleanup':return dict(status='cleaned')
        if action=='clear':
            g.key_counts=dict(press=0,release=0,repeat=0,syn_dropped=0)
            return dict(ready=True,vkill=21)
        if action=='cleared':
            assert g.key_counts['press']==g.key_counts['release']==2
            return dict(ready=True,vkill=21,line_kill_events=4)
        if action=='fresh':
            assert g.key_counts['press']==g.key_counts['release']==4
            g.key_counts=None
            return dict(ready=True,fresh_login_prompt=True,line_kill_events=4,public_eof_events=4)
        raise AssertionError('Unmodelled prepared login action: '+action)

    def counter(self):
        return dict(status='passed',counts_only=True,complete=True,keys_released=True,
            counts=dict(self.guest.key_counts),autorepeat=dict(delay_ms=250,period_ms=33),
            codes_recorded=False,values_recorded=False)


def command(guest,source):
    words=shlex.split(source)
    assert words[:2]==['python3','-B'] and words[2].startswith('/run/ares-login-') and words[2].endswith('/observer.py')
    action,digest=words[3:5];assert len(digest)==64
    root=words[2].rsplit('/',1)[0]
    if not hasattr(guest,'login_shims'):guest.login_shims={}
    if action=='init':guest.login_shims[root]=LoginShim(guest,words[5])
    value=guest.login_shims[root].call(action,words[5] if len(words)>5 else None)
    return frame(value)
